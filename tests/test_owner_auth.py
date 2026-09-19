"""SCN-005: mocked upstream boundaries, not real Supabase integration evidence."""

from __future__ import annotations

import asyncio
import base64
import json
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sochron1k.main import create_app
from sochron1k.owner_auth import OwnerAuthSettings, OwnerVerifier, load_owner_auth_settings

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SESSION = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
ORIGIN = "https://auth.fixture.invalid"


def token(**updates):
    claims = dict(
        sub=str(OWNER),
        session_id=SESSION,
        exp=2000,
        iss=ORIGIN + "/auth/v1",
        aud="authenticated",
        role="authenticated",
    )
    claims.update(updates)
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "e30." + encoded + ".c3ludGhldGlj"


@pytest.fixture
def settings():
    return OwnerAuthSettings(
        supabase_url=ORIGIN, public_key=SecretStr("sb_publishable_" + "fixture" * 4), owner_id=OWNER
    )


class Upstream:
    def __init__(self):
        self.calls = []
        self.user = dict(id=str(OWNER), is_anonymous=False, role="authenticated")
        self.active = True
        self.failure = None

    def __call__(self, request):
        self.calls.append(request)
        if self.failure:
            if isinstance(self.failure, Exception):
                raise self.failure
            return self.failure
        if request.url.path == "/auth/v1/user":
            assert request.method == "GET"
            return httpx.Response(200, json=self.user)
        assert request.url.path == "/rest/v1/rpc/sochron_session_active"
        assert request.method == "POST"
        assert json.loads(request.content) == {"p_session_id": SESSION}
        return httpx.Response(200, json=self.active)


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
async def client(settings, upstream):
    app = create_app(owner_auth_settings=settings)
    app.state.owner_verifier = OwnerVerifier(
        settings,
        transport=httpx.MockTransport(upstream),
        now=lambda: 1000,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        yield client


def bearer(value=None):
    return {"Authorization": "Bearer " + (token() if value is None else value)}


@pytest.mark.anyio
async def test_ac07_public_config_is_narrow(settings):
    for config in (None, settings):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(owner_auth_settings=config)),
            base_url="http://fixture",
        ) as client:
            response = await client.get("/auth/config")
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            expected = (
                {"enabled": False}
                if config is None
                else {
                    "enabled": True,
                    "supabase_url": ORIGIN,
                    "public_key": settings.public_key.get_secret_value(),
                }
            )
            assert response.json() == expected
            assert str(OWNER) not in response.text


@pytest.mark.anyio
async def test_ac01_disabled():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()), base_url="http://fixture"
    ) as client:
        for path in ("session", "telemetry", "execution", "signals", "statistics"):
            response = await client.get("/owner/" + path, headers=bearer())
            assert response.status_code == 503
            assert response.json() == {"detail": "OWNER_AUTH_DISABLED"}
            assert response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_ac01_owner_verified_each_read(client, upstream, settings):
    for _ in range(2):
        response = await client.get("/owner/session", headers=bearer())
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "owner_id": str(OWNER)}
        assert response.headers["cache-control"] == "no-store"
    assert len(upstream.calls) == 4
    for request in upstream.calls:
        assert request.headers["authorization"] == bearer()["Authorization"]
        assert request.headers["apikey"] == settings.public_key.get_secret_value()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        bearer("bad"),
        bearer("x" * 8193),
        {"Authorization": "Basic fixture"},
        list(bearer().items()) * 2,
    ],
)
async def test_ac01_missing_malformed_duplicate_denied(client, upstream, headers):
    response = await client.get("/owner/telemetry?access_token=" + token(), headers=headers)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert not upstream.calls


@pytest.mark.anyio
@pytest.mark.parametrize(
    "claims",
    [
        {"sub": None},
        {"sub": 1},
        {"sub": []},
        {"sub": "bad"},
        {"session_id": None},
        {"session_id": 1},
        {"session_id": {}},
        {"exp": 1000},
        {"exp": True},
        {"exp": "2000"},
        {"iss": "https://other.invalid/auth/v1"},
        {"aud": "anon"},
        {"role": "service_role"},
        {"role": "anon"},
    ],
)
async def test_ac01_invalid_claims_before_upstream(client, upstream, claims):
    response = await client.get("/owner/session", headers=bearer(token(**claims)))
    assert response.status_code == 401
    assert not upstream.calls


@pytest.mark.anyio
async def test_ac01_forged_metadata_cannot_grant_owner(client, upstream):
    upstream.user.update(id=str(OTHER), user_metadata={"owner_id": str(OWNER), "role": "owner"})
    response = await client.get("/owner/session", headers=bearer(token(sub=str(OTHER))))
    assert response.status_code == 403
    assert response.json() == {"detail": "OWNER_REQUIRED"}
    assert len(upstream.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    "change", [{"id": str(OTHER)}, {"is_anonymous": True}, {"is_anonymous": None}, {"role": "anon"}]
)
async def test_ac01_verified_identity_mismatch_denied(client, upstream, change):
    upstream.user.update(change)
    assert (await client.get("/owner/session", headers=bearer())).status_code == 401
    assert len(upstream.calls) == 1


@pytest.mark.anyio
async def test_ac02_revoked_session_not_cached(client, upstream):
    assert (await client.get("/owner/session", headers=bearer())).status_code == 200
    upstream.active = False
    response = await client.get("/owner/telemetry", headers=bearer())
    assert response.status_code == 401
    assert len(upstream.calls) == 4


@pytest.mark.anyio
@pytest.mark.parametrize("active", [None, 1, "true", {}, [True]])
async def test_ac02_malformed_rpc_fails_closed(client, upstream, active):
    upstream.active = active
    assert (await client.get("/owner/telemetry", headers=bearer())).status_code == 503


@pytest.mark.anyio
@pytest.mark.parametrize(
    "failure,status",
    [
        (httpx.Response(401, text="private upstream detail"), 401),
        (httpx.Response(403, text="private upstream detail"), 401),
        (httpx.Response(500, text="private upstream detail"), 503),
        (httpx.Response(302, headers={"location": "https://untrusted.invalid"}), 503),
        (httpx.Response(200, content=b"x" * 32769), 503),
        (httpx.Response(200, content=b'{"id":1,"id":2}'), 503),
        (httpx.Response(200, content=b"not-json"), 503),
        (httpx.Response(200, json=[]), 503),
        (httpx.ReadTimeout("private upstream detail"), 503),
        (httpx.ConnectError("private upstream detail"), 503),
    ],
)
async def test_ac05_upstream_errors_redacted(client, upstream, failure, status):
    upstream.failure = failure
    response = await client.get("/owner/telemetry", headers=bearer())
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"
    assert "private" not in response.text
    assert token() not in response.text
    assert len(upstream.calls) == 1


@pytest.mark.anyio
async def test_ac04_owner_telemetry_remains_disabled(client):
    response = await client.get("/owner/telemetry", headers=bearer())
    assert response.status_code == 200
    assert response.json()["observation"] is None
    assert response.json()["status"]["state"] == "disabled"
    assert response.json()["status"]["execution_ready"] is False
    assert response.json()["status"]["auto_trading_enabled"] is False
    assert (await client.post("/owner/telemetry", headers=bearer())).status_code == 405


@pytest.mark.anyio
async def test_ac05_total_deadline_bounds_slow_upstream(settings):
    async def slow(request):
        await asyncio.sleep(30)
        raise AssertionError("deadline did not cancel upstream")

    app = create_app(owner_auth_settings=settings)
    app.state.owner_verifier = OwnerVerifier(
        settings, transport=httpx.MockTransport(slow), now=lambda: 1000
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        response = await client.get("/owner/session", headers=bearer())
        assert response.status_code == 503
        assert response.json() == {"detail": "AUTH_UNAVAILABLE"}


@pytest.mark.anyio
async def test_ac02_expiry_during_verification(settings, upstream):
    times = iter([1000, 2000])
    app = create_app(owner_auth_settings=settings)
    app.state.owner_verifier = OwnerVerifier(
        settings, transport=httpx.MockTransport(upstream), now=lambda: next(times)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        assert (await client.get("/owner/session", headers=bearer())).status_code == 401
        assert len(upstream.calls) == 2


@pytest.mark.parametrize(
    "origin",
    [
        "http://external.invalid",
        "https://user:pass@host.invalid",
        "https://host.invalid/path",
        "https://host.invalid?query=1",
        "https://host.invalid/#fragment",
        "https://host.invalid:bad",
        "https://host.invalid\n",
        "file:///tmp/auth",
    ],
)
def test_ac05_origin_validation(settings, origin):
    with pytest.raises(ValidationError):
        OwnerAuthSettings(**(settings.model_dump() | {"supabase_url": origin}))


@pytest.mark.parametrize("key", ["sb_secret_fixture", token(role="service_role"), "invalid"])
def test_ac01_privileged_key_rejected(settings, key):
    with pytest.raises(ValidationError):
        OwnerAuthSettings(**(settings.model_dump() | {"public_key": key}))


def test_ac01_private_config(settings, tmp_path, monkeypatch):
    monkeypatch.delenv("SOCHRON_OWNER_AUTH_CONFIG_FILE", raising=False)
    assert load_owner_auth_settings() is None
    config = tmp_path / "owner.json"
    raw = settings.model_dump(mode="json")
    raw["public_key"] = settings.public_key.get_secret_value()
    config.write_text(json.dumps(raw))
    config.chmod(0o600)
    monkeypatch.setenv("SOCHRON_OWNER_AUTH_CONFIG_FILE", str(config))
    assert load_owner_auth_settings() == settings
    config.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private owner Auth"):
        load_owner_auth_settings()
    config.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(config)
    monkeypatch.setenv("SOCHRON_OWNER_AUTH_CONFIG_FILE", str(link))
    with pytest.raises(RuntimeError, match="Invalid private owner Auth"):
        load_owner_auth_settings()
