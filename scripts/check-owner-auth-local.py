#!/usr/bin/env python3
"""SCN-005 real local Auth/RPC evidence, isolated synthetic users, no broker calls."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import secrets
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))
# Do not load an operator's configured bridge or owner while checking fixtures.
os.environ.pop("SOCHRON_BRIDGE_CONFIG_FILE", None)
os.environ.pop("SOCHRON_OWNER_AUTH_CONFIG_FILE", None)
from sochron1k.main import create_app  # noqa: E402
from sochron1k.owner_auth import OwnerAuthSettings, token_claims  # noqa: E402


def require(condition: bool, stage: str) -> None:
    if not condition:
        raise RuntimeError(stage)


def command(args: list[str]) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, "local prerequisite command failed (output suppressed)")
    return result.stdout


async def verify():
    command(["bash", "scripts/supabase-local.sh", "guard"])
    runtime_images = {
        name: command(
            ["docker", "inspect", name, "--format", "{{.Config.Image}} {{.Image}}"]
        ).strip()
        for name in ("supabase_auth_sochron1k", "supabase_rest_sochron1k", "supabase_db_sochron1k")
    }
    require(command(["node", "--version"]).strip() == "v24.21.0", "Node version")
    require(
        command(["npm", "exec", "supabase", "--", "--version"]).strip() == "2.117.0", "CLI version"
    )
    local = json.loads(command(["npm", "exec", "supabase", "--", "status", "-o", "json"]))
    origin = local["API_URL"]
    require(origin == "http://127.0.0.1:54321", "unexpected local API origin")
    public = local["ANON_KEY"]
    # Administrative privilege is fixture-only and never placed in app settings.
    admin = {
        "apikey": local["SERVICE_ROLE_KEY"],
        "Authorization": "Bearer " + local["SERVICE_ROLE_KEY"],
    }
    created = []
    sessions = []
    async with httpx.AsyncClient(
        base_url=origin, timeout=10, trust_env=False, follow_redirects=False
    ) as auth:
        try:
            for index in range(2):
                email = f"scn005-{uuid4().hex}@sochron.test"
                password = secrets.token_urlsafe(32) + "!aA1"
                response = await auth.post(
                    "/auth/v1/admin/users",
                    headers=admin,
                    json={
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {"role": "owner", "owner": True},
                    },
                )
                require(response.status_code in (200, 201), f"create synthetic user {index}")
                user_id = str(UUID(response.json()["id"]))
                created.append(user_id)
                response = await auth.post(
                    "/auth/v1/token?grant_type=password",
                    headers={"apikey": public},
                    json={"email": email, "password": password},
                )
                require(response.status_code == 200, f"sign in synthetic user {index}")
                sessions.append(response.json()["access_token"])
            settings = OwnerAuthSettings(
                supabase_url=origin, public_key=SecretStr(public), owner_id=UUID(created[0])
            )
            app = create_app(owner_auth_settings=settings)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://fixture"
            ) as client:
                owner_header = {"Authorization": "Bearer " + sessions[0]}
                require((await client.get("/owner/session")).status_code == 401, "anonymous denial")
                owner = await client.get("/owner/session", headers=owner_header)
                require(
                    owner.status_code == 200 and owner.json()["owner_id"] == created[0],
                    "real owner verification",
                )
                other = await client.get(
                    "/owner/session",
                    headers={
                        "Authorization": "Bearer " + sessions[1],
                    },
                )
                require(other.status_code == 403, "foreign user with owner metadata denied")
                private = await client.get("/owner/telemetry", headers=owner_header)
                require(
                    private.status_code == 200
                    and private.json()["status"]["execution_ready"] is False
                    and private.headers["cache-control"] == "no-store",
                    "private read",
                )
                foreign_session = token_claims(sessions[1])["session_id"]
                rpc = await auth.post(
                    "/rest/v1/rpc/sochron_session_active",
                    headers={"apikey": public, **owner_header},
                    json={"p_session_id": foreign_session},
                )
                require(rpc.status_code == 200 and rpc.json() is False, "cross-user RPC denial")
                logout = await auth.post(
                    "/auth/v1/logout?scope=local", headers={"apikey": public, **owner_header}
                )
                require(logout.status_code == 204, "real local sign out")
                require(
                    token_claims(sessions[0])["exp"] > time.time(),
                    "revocation test must use an unexpired access token",
                )
                revoked = await client.get("/owner/telemetry", headers=owner_header)
                require(revoked.status_code == 401, "revoked unexpired access token denial")
        finally:
            cleanup_ok = True
            for user_id in created:
                try:
                    response = await auth.delete("/auth/v1/admin/users/" + user_id, headers=admin)
                    cleanup_ok = cleanup_ok and response.status_code in (200, 204)
                except httpx.HTTPError:
                    cleanup_ok = False
            require(cleanup_ok, "synthetic user cleanup failed; inspect local fixture users")
    files = [
        "services/api/src/sochron1k/main.py",
        "supabase/config.toml",
        "supabase/migrations/20260916224038_owner_session_validation.sql",
        "services/api/src/sochron1k/owner_auth.py",
        "services/api/src/sochron1k/owner_api.py",
        "services/api/src/sochron1k/telemetry.py",
        "scripts/check-owner-auth-local.py",
    ]
    print(
        json.dumps(
            {
                "result": "PASS",
                "boundary": "ASGI API + real loopback Supabase Auth and REST RPC",
                "revision": command(["git", "rev-parse", "HEAD"]).strip(),
                "dirty": bool(command(["git", "status", "--porcelain"]).strip()),
                "python": platform.python_version(),
                "node": "24.21.0",
                "supabase_cli": "2.117.0",
                "runtime_images": runtime_images,
                "checks": [
                    "owner",
                    "anonymous denial",
                    "foreign user denial",
                    "private no-store read",
                    "foreign session RPC denial",
                    "logout revocation",
                    "synthetic user cleanup",
                ],
                "sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files
                },
                "mt5": "NOT_RUN",
                "browser": "NOT_RUN",
                "hosted_supabase": "NOT_RUN",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        asyncio.run(verify())
    except Exception as error:
        # Never print upstream bodies, tokens, passwords, or exception request objects.
        print(
            json.dumps(
                {
                    "result": "FAIL",
                    "error_type": type(error).__name__,
                    "stage": str(error)
                    if isinstance(error, RuntimeError)
                    else "local Auth verification failed (details suppressed)",
                }
            )
        )
        sys.exit(1)
