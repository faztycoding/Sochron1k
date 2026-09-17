#!/usr/bin/env python3
"""SCN-008 real local Auth/PostgREST/worker evidence; no hosted target or reset."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
from datetime import UTC, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID, uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ("services/api/src", "services/worker/src", "tests")]
from sochron1k.bar_history import BarHistory  # noqa: E402
from sochron1k.telemetry import TelemetryFrame  # noqa: E402
from sochron_worker.native_source import NativeArchiveSource  # noqa: E402
from test_chart import packet, setup_chart  # noqa: E402
from test_native_source import record_packet  # noqa: E402

ORIGIN = "http://127.0.0.1:54321"
MAXIMUM = "99999999999999.9999999999"
CHECKS: list[str] = []


class VerificationFailure(RuntimeError):
    pass


def require(condition: bool, stage: str) -> None:
    if not condition:
        raise VerificationFailure(stage)


def command(args, *, data=None, timeout=30) -> str:
    result = subprocess.run(
        args, cwd=ROOT, input=data, text=True, capture_output=True, timeout=timeout
    )
    require(result.returncode == 0, "local prerequisite/query failed (details suppressed)")
    return result.stdout.strip()


def sql(query: str) -> str:
    return command(
        [
            "docker",
            "exec",
            "-i",
            "supabase_db_sochron1k",
            "psql",
            "-X",
            "-Atq",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            "postgres",
        ],
        data=query,
    )


def ident(value: str) -> str:
    return "'" + str(UUID(value)) + "'"


def check(stage: str) -> None:
    CHECKS.append(stage)
    print("PASS " + stage, flush=True)


def source_fixture(directory: Path):
    directory.mkdir(mode=0o700)
    setup = setup_chart.__wrapped__()
    _clock, bridge, store, quote = setup
    quote = copy.deepcopy(quote)
    quote["sequence"] = 2
    quote["contract"].update(digits=10, tick_size="1E-10")
    bridge.accept(TelemetryFrame.model_validate(quote))
    archive = BarHistory(directory, bridge.settings, store.settings)
    data = packet(setup)
    data.update(digits=10, tick_size="1E-10")
    for row in data["bars"]:
        row.update(dict.fromkeys(("open", "high", "low", "close"), MAXIMUM))
        row["tick_volume"] = 9007199254740991
    record_packet(setup, archive, data)
    source = NativeArchiveSource(
        directory, UUID(archive.archive_id), bridge.settings.identity, 7200, store.settings
    )
    return setup, archive, source, data


class FaultProxy:
    """Forward real RPC responses, optionally withhold/drop one committed store."""

    def __init__(self):
        self.accepted, self.release = threading.Event(), threading.Event()
        self.hold = True
        self.drop = False
        self.stores = 0
        self.calls = 0
        self.failure = False
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                allowed = (
                    "/rest/v1/rpc/sochron_store_native_m1",
                    "/rest/v1/rpc/sochron_read_native_m1",
                )
                try:
                    require(self.path in allowed, "proxy path denied")
                    proxy.calls += 1
                    size = int(self.headers.get("Content-Length", "0"))
                    require(0 < size <= 262144, "proxy body denied")
                    body = self.rfile.read(size)
                    headers = {
                        name: self.headers[name]
                        for name in ("apikey", "Authorization", "Content-Type")
                        if name in self.headers
                    }
                    headers["Accept-Encoding"] = "identity"
                    with httpx.Client(
                        timeout=10, trust_env=False, follow_redirects=False
                    ) as client:
                        upstream = client.post(ORIGIN + self.path, content=body, headers=headers)
                    if self.path == allowed[0] and upstream.status_code == 200:
                        proxy.stores += 1
                        if proxy.hold:
                            proxy.accepted.set()
                            require(proxy.release.wait(15), "proxy hold expired")
                            proxy.hold = False
                            self.close_connection = True
                            return
                        if proxy.drop:
                            proxy.drop = False
                            self.close_connection = True
                            return
                    self.send_response(upstream.status_code)
                    self.send_header("Content-Type", upstream.headers.get("content-type", ""))
                    self.send_header("Content-Length", str(len(upstream.content)))
                    self.end_headers()
                    self.wfile.write(upstream.content)
                except Exception:
                    proxy.failure = True
                    self.close_connection = True

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def configure(directory, source, owner, origin, key):
    state = directory / "state"
    state.mkdir(mode=0o700)
    key_path = directory / "service-key"
    key_path.write_text(key)
    key_path.chmod(0o600)
    binding = json.loads(source.binding_json)
    data = dict(
        enabled=True,
        source_directory=str(source.directory),
        state_directory=str(state),
        archive_id=source.archive_id,
        identity=binding["identity"],
        offset_seconds=binding["offset"],
        chart=binding["chart"],
        owner_id=owner,
        origin=origin,
        service_key_file=str(key_path),
    )
    path = directory / "worker.json"
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    env = {
        **os.environ,
        "SOCHRON_SYNC_CONFIG_FILE": str(path),
        "PYTHONPATH": os.pathsep.join(
            str(ROOT / p) for p in ("services/api/src", "services/worker/src")
        ),
    }
    return state, env


def worker(env, action="run", *, expected=0):
    args = [sys.executable, "-m", "sochron_worker", action]
    if action == "run":
        args.append("--once")
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    require(result.returncode == expected and not result.stderr, "worker command/exit mismatch")
    values = [json.loads(line) for line in result.stdout.splitlines()]
    require(len(values) == 1, "unexpected worker output")
    require(values[0]["auto_trading_enabled"] is False, "worker must remain nontrading")
    return values[0]


def cleanup(client, admin, users, archives, sessions, public):
    if not users:
        return
    # Exact UUIDs generated/returned for this invocation only; no reset/table-wide delete.
    owners = ",".join(ident(user[0]) for user in users)
    archive_ids = ",".join(ident(value) for value in archives) or "NULL"
    for user_id, email in users:
        reply = client.get("/auth/v1/admin/users/" + user_id, headers=admin)
        require(
            reply.status_code == 200 and reply.json().get("email") == email,
            "fixture ownership confirmation failed",
        )
    require(
        sql(
            f"select count(*) from public.native_bar_archives where owner_id in ({owners}) "
            f"and archive_id not in ({archive_ids});"
        )
        == "0",
        "unowned fixture archive",
    )
    sql(f"""begin; set local statement_timeout='5s';
        set local session_replication_role=replica;
        delete from public.bars where owner_id in ({owners})
          and native_archive_id in ({archive_ids});
        delete from public.native_bar_archives where owner_id in ({owners})
          and archive_id in ({archive_ids});
        commit;""")
    require(
        sql(f"select count(*) from public.bars where owner_id in ({owners});") == "0",
        "unexpected fixture-owner data remains",
    )
    for index, (user_id, _) in enumerate(users):
        if index < len(sessions):
            require(
                client.post(
                    "/auth/v1/logout?scope=global",
                    headers={"apikey": public, "Authorization": "Bearer " + sessions[index]},
                ).status_code
                == 204,
                "fixture session revocation failed",
            )
        require(
            client.delete("/auth/v1/admin/users/" + user_id, headers=admin).status_code
            in (200, 204),
            "fixture user cleanup failed",
        )
    require(
        sql(f"select count(*) from auth.users where id in ({owners});") == "0",
        "fixture user remains",
    )
    check("removed only invocation-owned synthetic rows/users; no database reset")


def verify():
    command(["bash", "scripts/supabase-local.sh", "guard"])
    containers = command(
        ["docker", "ps", "-q", "--filter", "label=com.supabase.cli.project=sochron1k"]
    ).split()
    require(bool(containers), "local Supabase not running")
    for container in containers:
        ports = json.loads(
            command(
                ["docker", "inspect", container, "--format", "{{json .NetworkSettings.Ports}} "]
            )
        )
        require(
            all(
                binding["HostIp"] == "127.0.0.1"
                for values in ports.values()
                for binding in (values or [])
            ),
            "non-loopback published service denied",
        )
    require(command(["node", "--version"]) == "v24.21.0", "pinned Node required")
    require(
        command(["npm", "exec", "supabase", "--", "--version"]) == "2.117.0", "pinned CLI required"
    )
    local = json.loads(command(["npm", "exec", "supabase", "--", "status", "-o", "json"]))
    require(local["API_URL"] == ORIGIN, "only guarded local origin allowed")
    images = {
        name: command(["docker", "inspect", name, "--format", "{{.Config.Image}} {{.Image}}"])
        for name in ("supabase_db_sochron1k", "supabase_rest_sochron1k", "supabase_auth_sochron1k")
    }
    # Never echo status, keys, response/error bodies or fixture account data.
    admin = {"apikey": local["SECRET_KEY"]}
    users, archives, sessions = [], [], []
    proxy, child = None, None
    with httpx.Client(
        base_url=ORIGIN, timeout=10, trust_env=False, follow_redirects=False
    ) as client:
        try:
            for _ in range(2):
                email = "scn008-" + uuid4().hex + "@sochron.test"
                password = secrets.token_urlsafe(32) + "!aA1"
                reply = client.post(
                    "/auth/v1/admin/users",
                    headers=admin,
                    json={"email": email, "password": password, "email_confirm": True},
                )
                require(reply.status_code in (200, 201), "create local synthetic user")
                user_id = str(UUID(reply.json()["id"]))
                users.append((user_id, email))
                reply = client.post(
                    "/auth/v1/token?grant_type=password",
                    headers={"apikey": local["PUBLISHABLE_KEY"]},
                    json={"email": email, "password": password},
                )
                require(reply.status_code == 200, "sign in synthetic owner")
                sessions.append(reply.json()["access_token"])
            with tempfile.TemporaryDirectory(prefix="sochron-sync-http-") as temporary:
                directory = Path(temporary).resolve()
                setup, archive, source, data = source_fixture(directory / "source")
                archives.append(source.archive_id)
                batch = source.read()
                proxy = FaultProxy()
                state, env = configure(
                    directory, source, users[0][0], proxy.origin, local["SECRET_KEY"]
                )
                require(worker(env, "init")["state"] == "INITIALIZED", "CLI init")
                child = subprocess.Popen(
                    [sys.executable, "-m", "sochron_worker", "run", "--once"],
                    cwd=ROOT,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                require(proxy.accepted.wait(10), "real committed store not observed")
                # Hard process loss after a real 200 from PostgREST, before worker ACK.
                child.kill()
                child.communicate(timeout=5)
                require(child.returncode == -9, "worker crash not observed")
                with sqlite3.connect(state / "sync.sqlite3") as db:
                    require(
                        db.execute("select state,attempts from batches").fetchone()
                        == ("UNKNOWN", 1),
                        "crash journal must retain UNKNOWN",
                    )
                    require(
                        db.execute("select receipt from meta").fetchone()[0] == 0,
                        "premature cursor",
                    )
                proxy.release.set()
                require(
                    worker(env)["state"] == "VERIFIED" and proxy.stores == 1,
                    "restart must read back, never send twice",
                )
                check("actual PostgREST commit + SIGKILL + restart read-back without second send")

                owner, other = [
                    dict(apikey=local["PUBLISHABLE_KEY"], Authorization="Bearer " + token)
                    for token in sessions
                ]
                query = (
                    "/rest/v1/bars?select=owner_id,native_payload,available_at&native_archive_id=eq."
                    + source.archive_id
                    + "&order=native_time_server_s.asc"
                )
                reply = client.get(query, headers=owner)
                require(reply.status_code == 200 and len(reply.json()) == 2, "owner native rows")
                stored = reply.json()
                require(
                    {r["native_payload"]["time_server_s"] for r in stored}
                    == {r.cursor.time_server_s for r in batch.rows},
                    "exact row keys",
                )
                original = {r.cursor.time_server_s: json.loads(r.payload) for r in batch.rows}
                require(
                    all(
                        r["native_payload"] == original[r["native_payload"]["time_server_s"]]
                        for r in stored
                    ),
                    "exact payload precision/provenance",
                )
                values = sql(
                    "select open_price::text,tick_volume::text from public.bars "
                    f"where native_archive_id={ident(source.archive_id)} "
                    "order by native_time_server_s;"
                )
                require(
                    len(values.splitlines()) == 2
                    and all(
                        Decimal(row.split("|")[0]) == Decimal(MAXIMUM)
                        and Decimal(row.split("|")[1]) == Decimal(9007199254740991)
                        for row in values.splitlines()
                    ),
                    "independent exact SQL numerics",
                )
                check("exact 24-digit/10-decimal prices, 53-bit volume and original provenance")

                args = dict(
                    p_owner_id=users[0][0],
                    p_archive_id=source.archive_id,
                    p_binding=json.loads(source.binding_json),
                    p_rows=batch.wire_rows(),
                )
                # Matching replay under legacy service key must retain existing availability.
                replay = copy.deepcopy(args)
                for row in replay["p_rows"]:
                    row["available_at"] = datetime.now(UTC).isoformat()
                legacy = {
                    "apikey": local["SERVICE_ROLE_KEY"],
                    "Authorization": "Bearer " + local["SERVICE_ROLE_KEY"],
                }
                require(
                    client.post(
                        "/rest/v1/rpc/sochron_store_native_m1", headers=legacy, json=replay
                    ).status_code
                    == 200,
                    "legacy replay",
                )
                require(
                    client.get(query, headers=owner).json() == stored, "replay changed availability"
                )
                check("modern secret and legacy service-role HTTP authentication; immutable replay")

                for name, payload in (
                    ("sochron_store_native_m1", args),
                    (
                        "sochron_read_native_m1",
                        {
                            "p_owner_id": users[0][0],
                            "p_archive_id": source.archive_id,
                            "p_times": [r.cursor.time_server_s for r in batch.rows],
                        },
                    ),
                ):
                    require(
                        client.post(
                            "/rest/v1/rpc/" + name,
                            headers={"apikey": local["PUBLISHABLE_KEY"]},
                            json=payload,
                        ).status_code
                        in (401, 403),
                        "anonymous privileged RPC allowed",
                    )
                for credentials in (other, {"apikey": local["PUBLISHABLE_KEY"]}):
                    reply = client.get(query, headers=credentials)
                    require(
                        (reply.status_code == 200 and reply.json() == [])
                        or reply.status_code in (401, 403),
                        "foreign/anonymous row disclosure",
                    )
                # Give both owners rows with the same archive UUID, then test both directions.
                second = dict(args, p_owner_id=users[1][0])
                require(
                    client.post(
                        "/rest/v1/rpc/sochron_store_native_m1", headers=admin, json=second
                    ).status_code
                    == 200,
                    "second owner fixture",
                )
                for index, credentials in enumerate((owner, other)):
                    reply = client.get(query, headers=credentials)
                    require(
                        reply.status_code == 200
                        and len(reply.json()) == 2
                        and {r["owner_id"] for r in reply.json()} == {users[index][0]},
                        "owner isolation",
                    )
                    archive_reply = client.get(
                        "/rest/v1/native_bar_archives?select=owner_id,archive_id&archive_id=eq."
                        + source.archive_id,
                        headers=credentials,
                    )
                    require(
                        archive_reply.status_code == 200
                        and archive_reply.json()
                        == [{"owner_id": users[index][0], "archive_id": source.archive_id}],
                        "archive owner isolation",
                    )
                    for method in ("PATCH", "DELETE"):
                        require(
                            client.request(
                                method,
                                "/rest/v1/bars?native_archive_id=eq." + source.archive_id,
                                headers=credentials,
                                json={"source_revision": "denied-fixture"}
                                if method == "PATCH"
                                else None,
                            ).status_code
                            == 403,
                            "browser table mutation allowed",
                        )
                    require(
                        client.post(
                            "/rest/v1/rpc/sochron_store_native_m1", headers=credentials, json=args
                        ).status_code
                        == 403,
                        "browser RPC write allowed",
                    )
                    require(
                        client.post(
                            "/rest/v1/rpc/sochron_read_native_m1",
                            headers=credentials,
                            json={
                                "p_owner_id": users[0][0],
                                "p_archive_id": source.archive_id,
                                "p_times": [r.cursor.time_server_s for r in batch.rows],
                            },
                        ).status_code
                        == 403,
                        "browser privileged read RPC allowed",
                    )
                require(
                    client.delete(
                        "/rest/v1/bars?native_archive_id=eq." + source.archive_id, headers=admin
                    ).status_code
                    == 400,
                    "native deletion must fail",
                )
                require(
                    len(client.get(query, headers=owner).json()) == 2,
                    "denied deletion changed rows",
                )
                check("real Auth owner isolation, anon/browser RPC denial and native delete denial")

                older = copy.deepcopy(data)
                older["sequence"] = 2
                older["bars"].insert(
                    0, dict(older["bars"][0], time_server_s=older["bars"][0]["time_server_s"] - 180)
                )
                record_packet(setup, archive, older)
                proxy.drop = True
                require(
                    worker(env, expected=3)["state"] == "UNKNOWN",
                    "lost HTTP response must be UNKNOWN",
                )
                require(worker(env)["state"] == "VERIFIED", "late backfill reconciliation")
                require(
                    proxy.stores == 2 and len(client.get(query, headers=owner).json()) == 3,
                    "late older bar skipped or duplicated",
                )
                require(
                    any(
                        r["native_payload"]["time_server_s"] == older["bars"][0]["time_server_s"]
                        and r["native_payload"]["first_receipt"] == 2
                        for r in client.get(query, headers=owner).json()
                    ),
                    "late receipt provenance",
                )
                check("later receipt with older candle synchronized after committed response loss")
                calls = proxy.calls
                (directory / "worker.json").chmod(0o644)
                require(
                    worker(env, expected=2)["state"] == "SYNC_CONFIG_INVALID"
                    and proxy.calls == calls,
                    "unsafe config contacted real destination",
                )
                (directory / "worker.json").chmod(0o600)
                check("unsafe private config denied before contacting actual destination")

                # A new source conflicts with a valid preexisting destination payload.
                conflict_dir = directory / "conflict"
                conflict_dir.mkdir(mode=0o700)
                _, _, conflict_source, _ = source_fixture(conflict_dir / "source")
                archives.append(conflict_source.archive_id)
                conflict = conflict_source.read()
                conflict_args = dict(
                    args, p_archive_id=conflict_source.archive_id, p_rows=conflict.wire_rows()
                )
                conflict_args["p_rows"][0]["bar"]["first_receipt"] += 10
                require(
                    client.post(
                        "/rest/v1/rpc/sochron_store_native_m1", headers=admin, json=conflict_args
                    ).status_code
                    == 200,
                    "conflict fixture insert",
                )
                _, conflict_env = configure(
                    conflict_dir, conflict_source, users[0][0], ORIGIN, local["SECRET_KEY"]
                )
                worker(conflict_env, "init")
                require(
                    worker(conflict_env, expected=2)["state"] == "QUARANTINED",
                    "real conflict quarantine",
                )
                require(
                    worker(conflict_env, expected=2)["state"] == "QUARANTINED",
                    "persistent quarantine",
                )
                unchanged = client.post(
                    "/rest/v1/rpc/sochron_read_native_m1",
                    headers=admin,
                    json={
                        "p_owner_id": users[0][0],
                        "p_archive_id": conflict_source.archive_id,
                        "p_times": [r.cursor.time_server_s for r in conflict.rows],
                    },
                )
                require(
                    unchanged.status_code == 200
                    and [r["bar"] for r in unchanged.json()["rows"]]
                    == [r["bar"] for r in conflict_args["p_rows"]],
                    "conflict rewrote stored payload",
                )
                require(not proxy.failure, "fault proxy failed")
                check("actual PostgreSQL payload conflict is persistently quarantined by worker")
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
            if proxy is not None:
                proxy.close()
            cleanup(client, admin, users, archives, sessions, local["PUBLISHABLE_KEY"])
    sources = [
        *sorted((ROOT / "services/worker/src/sochron_worker").glob("*.py")),
        *sorted((ROOT / "services/api/src/sochron1k").glob("*.py")),
        *sorted((ROOT / "supabase/migrations").glob("*.sql")),
        Path(__file__),
        *[
            ROOT / p
            for p in (
                "tests/test_chart.py",
                "tests/test_native_source.py",
                "tests/test_telemetry_bridge.py",
                "tests/fixtures/mt5-telemetry-v1.json",
                "supabase/config.toml",
            )
        ],
    ]
    report = dict(
        result="PASS",
        revision=command(["git", "rev-parse", "HEAD"]),
        dirty=bool(command(["git", "status", "--porcelain"])),
        python=platform.python_version(),
        recorded_at=datetime.now(UTC).isoformat(),
        migrations=sql(
            "select version from supabase_migrations.schema_migrations order by version;"
        ).splitlines(),
        images=images,
        checks=CHECKS,
        sha256={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
        },
        hosted="NOT_RUN",
        mt5="NOT_RUN",
        release="NOT_READY",
    )
    output = ROOT / "output/native-sync-local"
    output.mkdir(parents=True, exist_ok=True)
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        verify()
    except Exception as error:
        report = {
            "result": "FAIL",
            "error_type": type(error).__name__,
            "recorded_at": datetime.now(UTC).isoformat(),
            "checks_completed": CHECKS,
            "stage": str(error)
            if isinstance(error, VerificationFailure)
            else "local verification failed; details suppressed",
        }
        output = ROOT / "output/native-sync-local"
        output.mkdir(parents=True, exist_ok=True)
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        raise SystemExit(1) from None
