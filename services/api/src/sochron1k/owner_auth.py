"""Online Supabase identity and active-session verification for owner-only reads."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import os
import re
import stat
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import Field, SecretStr, field_validator

from .bridge_api import unique_object
from .models import StrictModel

MAX_TOKEN = 8192
MAX_UPSTREAM = 32_768


def token_claims(token: str) -> dict:
    # Syntax/claim extraction only. Authenticity MUST be verified online afterwards.
    if len(token) > MAX_TOKEN or not re.fullmatch(
        r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token
    ):
        raise ValueError("invalid token")
    payload = token.split(".")[1]
    decoded = base64.b64decode(payload + "=" * (-len(payload) % 4), altchars=b"-_", validate=True)
    claims = json.loads(decoded, object_pairs_hook=unique_object)
    if not isinstance(claims, dict):
        raise ValueError("invalid claims")
    return claims


class OwnerAuthSettings(StrictModel):
    supabase_url: str = Field(max_length=256)
    public_key: SecretStr
    owner_id: UUID

    @field_validator("supabase_url")
    @classmethod
    def bounded_origin(cls, value: str) -> str:
        if not value.isascii() or any(
            ord(character) <= 32 or ord(character) == 127 for character in value
        ):
            raise ValueError("invalid origin")
        parsed = urlsplit(value)
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
            or not parsed.hostname
            or parsed.scheme not in ("http", "https")
            or (
                parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            )
        ):
            raise ValueError("use a HTTPS Supabase origin or explicit loopback HTTP origin")
        # Force invalid ports to fail during configuration, not during a request.
        _ = parsed.port
        return value.rstrip("/")

    @field_validator("public_key")
    @classmethod
    def unprivileged_key_only(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]{16,256}", raw):
            return value
        try:
            if token_claims(raw).get("role") == "anon":
                return value
        except ValueError, binascii.Error, RecursionError:
            pass
        raise ValueError("only a publishable or legacy anon key is permitted")


def load_owner_auth_settings() -> OwnerAuthSettings | None:
    configured = os.environ.get("SOCHRON_OWNER_AUTH_CONFIG_FILE")
    if not configured:
        return None
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(Path(configured), flags), "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
            ):
                raise ValueError("private configuration required")
            raw = stream.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("configuration too large")
        return OwnerAuthSettings.model_validate_json(raw)
    except OSError, ValueError:
        raise RuntimeError("Invalid private owner Auth configuration; API not started") from None


class OwnerAuthDenied(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code
        super().__init__(code)


class OwnerVerifier:
    def __init__(
        self,
        settings: OwnerAuthSettings | None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._now = now

    async def _json(self, client: httpx.AsyncClient, method: str, path: str, **kwargs):
        async with client.stream(method, path, **kwargs) as response:
            if response.status_code in (401, 403):
                raise OwnerAuthDenied(401, "AUTH_REQUIRED")
            if response.status_code != 200:
                raise OwnerAuthDenied(503, "AUTH_UNAVAILABLE")
            data = bytearray()
            async for chunk in response.aiter_bytes():
                if len(data) + len(chunk) > MAX_UPSTREAM:
                    raise OwnerAuthDenied(503, "AUTH_UNAVAILABLE")
                data.extend(chunk)
            try:
                return json.loads(data, object_pairs_hook=unique_object)
            except ValueError, RecursionError:
                raise OwnerAuthDenied(503, "AUTH_UNAVAILABLE") from None

    async def verify(self, authorization: list[str]) -> UUID:
        settings = self.settings
        if settings is None:
            raise OwnerAuthDenied(503, "OWNER_AUTH_DISABLED")
        if len(authorization) != 1 or not authorization[0].startswith("Bearer "):
            raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        token = authorization[0][7:]
        try:
            claims = token_claims(token)
            if not isinstance(claims.get("sub"), str) or not isinstance(
                claims.get("session_id"), str
            ):
                raise ValueError("invalid identity claims")
            subject = UUID(claims["sub"])
            session_id = UUID(claims["session_id"])
            expiry = claims["exp"]
            if (
                claims.get("iss") != settings.supabase_url + "/auth/v1"
                or claims.get("aud") != "authenticated"
                or claims.get("role") != "authenticated"
                or type(expiry) is not int
                or expiry <= self._now()
            ):
                raise ValueError("invalid claims")
        except ValueError, TypeError, KeyError, binascii.Error, RecursionError:
            raise OwnerAuthDenied(401, "AUTH_REQUIRED") from None
        headers = {
            "apikey": settings.public_key.get_secret_value(),
            "Authorization": "Bearer " + token,
        }
        try:
            async with (
                asyncio.timeout(5),
                httpx.AsyncClient(
                    base_url=settings.supabase_url,
                    headers=headers,
                    timeout=2,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self._transport,
                ) as client,
            ):
                user = await self._json(client, "GET", "/auth/v1/user")
                if not isinstance(user, dict):
                    raise OwnerAuthDenied(503, "AUTH_UNAVAILABLE")
                if (
                    user.get("id") != str(subject)
                    or user.get("is_anonymous") is not False
                    or user.get("role") != "authenticated"
                ):
                    raise OwnerAuthDenied(401, "AUTH_REQUIRED")
                # Only the Auth-verified ID can satisfy the pinned owner UUID.
                if subject != settings.owner_id:
                    raise OwnerAuthDenied(403, "OWNER_REQUIRED")
                active = await self._json(
                    client,
                    "POST",
                    "/rest/v1/rpc/sochron_session_active",
                    json={"p_session_id": str(session_id)},
                )
                if active is False:
                    raise OwnerAuthDenied(401, "AUTH_REQUIRED")
                if active is not True:
                    raise OwnerAuthDenied(503, "AUTH_UNAVAILABLE")
                if expiry <= self._now():
                    raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        except httpx.HTTPError, TimeoutError:
            raise OwnerAuthDenied(503, "AUTH_UNAVAILABLE") from None
        return subject
