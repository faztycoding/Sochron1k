from __future__ import annotations

import base64
import json
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.main import create_app
from sochron1k.owner_auth import OwnerAuthSettings, OwnerVerifier
from sochron1k.signal_evidence import MAX_SIGNALS, SignalEvidenceReader

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SESSION = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
ORIGIN = "https://signals.fixture.invalid"


def token(*, subject: UUID = OWNER) -> str:
    claims = {
        "sub": str(subject),
        "session_id": SESSION,
        "exp": 2_000,
        "iss": ORIGIN + "/auth/v1",
        "aud": "authenticated",
        "role": "authenticated",
    }
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "e30." + encoded + ".c3ludGhldGlj"


def signal_row(
    *,
    row_id: int = 2,
    signal_id: str = "signal-pa01-0002",
    action: str = "buy",
    owner: UUID = OWNER,
) -> dict:
    return {
        "id": row_id,
        "owner_id": str(owner),
        "signal_id": signal_id,
        "setup_id": "setup-pa01-0002",
        "action": action,
        "formed_at": "2026-09-19T12:00:00+00:00",
        "confirmed_at": "2026-09-19T12:10:00+00:00",
        "expires_at": "2026-09-19T12:10:30+00:00",
        "evidence_ids": ["feature-m5-1205", "pivot-h1-1000"],
        "blocked_reason": None,
        "created_at": "2026-09-19T12:10:01+00:00",
        "experiment": {
            "owner_id": str(owner),
            "experiment_id": "experiment-pa01-v1",
            "status": "demo",
            "policy_version": "risk-v1.1",
            "started_at": "2026-09-01T00:00:00+00:00",
            "ended_at": None,
        },
        "strategy": {
            "owner_id": str(owner),
            "version_id": "PA01-v1",
            "code_hash": "a" * 64,
            "status": "active",
            "data_cutoff": "2026-09-19T12:05:00+00:00",
        },
    }


class Upstream:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = [] if rows is None else rows
        self.calls: list[httpx.Request] = []
        self.signal_response: httpx.Response | None = None
        self.user_id = OWNER

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if request.url.path == "/auth/v1/user":
            return httpx.Response(
                200,
                json={"id": str(self.user_id), "is_anonymous": False, "role": "authenticated"},
            )
        if request.url.path == "/rest/v1/rpc/sochron_session_active":
            return httpx.Response(200, json=True)
        assert request.url.path == "/rest/v1/signals"
        assert request.method == "GET" and request.content == b""
        assert request.headers["apikey"].startswith("sb_publishable_")
        assert request.headers["authorization"].startswith("Bearer ")
        assert request.url.params["order"] == "confirmed_at.desc,id.desc"
        assert request.url.params["limit"] == str(MAX_SIGNALS)
        select = request.url.params["select"]
        assert "owner_id" in select and "strategy_versions" in select and "experiments" in select
        assert all(term not in select for term in ("parameters", "account_ref", "idempotency_key"))
        return self.signal_response or httpx.Response(200, json=self.rows)


@pytest.fixture
def settings() -> OwnerAuthSettings:
    return OwnerAuthSettings(
        supabase_url=ORIGIN,
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )


@pytest.fixture
async def case(settings):
    upstream = Upstream([signal_row()])
    transport = httpx.MockTransport(upstream)
    reader = SignalEvidenceReader(
        settings,
        transport=transport,
        now=lambda: datetime(2026, 9, 19, 12, 11, tzinfo=UTC),
    )
    app = create_app(owner_auth_settings=settings, signal_evidence=reader)
    app.state.owner_verifier = OwnerVerifier(settings, transport=transport, now=lambda: 1_000)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        yield client, upstream


def bearer(value: str | None = None) -> dict[str, str]:
    return {"Authorization": "Bearer " + (token() if value is None else value)}


@pytest.mark.anyio
async def test_owner_projection_is_bounded_strict_and_redacted(case):
    client, upstream = case
    response = await client.get("/owner/signals", headers=bearer())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "trading_mode": "demo",
        "read_only": True,
        "source": "supabase-signals",
        "read_at_utc": "2026-09-19T12:11:00Z",
        "status": {
            "state": "available",
            "returned_count": 1,
            "limit": 50,
            "auto_trading_enabled": False,
            "execution_ready": False,
        },
        "signals": [
            {
                "signal_id": "signal-pa01-0002",
                "setup_id": "setup-pa01-0002",
                "action": "buy",
                "formed_at_utc": "2026-09-19T12:00:00Z",
                "confirmed_at_utc": "2026-09-19T12:10:00Z",
                "expires_at_utc": "2026-09-19T12:10:30Z",
                "created_at_utc": "2026-09-19T12:10:01Z",
                "evidence_ids": ["feature-m5-1205", "pivot-h1-1000"],
                "blocked_reason": None,
                "experiment": {
                    "experiment_id": "experiment-pa01-v1",
                    "status": "demo",
                    "policy_version": "risk-v1.1",
                },
                "strategy": {
                    "version_id": "PA01-v1",
                    "code_hash": "a" * 64,
                    "status": "active",
                    "data_cutoff_utc": "2026-09-19T12:05:00Z",
                },
            }
        ],
    }
    text = response.text.lower()
    assert all(
        secret not in text
        for secret in (str(OWNER), token().lower(), ORIGIN, "sb_publishable", "parameters")
    )
    assert [request.url.path for request in upstream.calls] == [
        "/auth/v1/user",
        "/rest/v1/rpc/sochron_session_active",
        "/rest/v1/signals",
    ]


@pytest.mark.anyio
async def test_empty_source_is_not_a_synthetic_wait(case):
    client, upstream = case
    upstream.rows = []
    response = await client.get("/owner/signals", headers=bearer())
    assert response.status_code == 200
    assert response.json()["status"] == {
        "state": "awaiting_source",
        "returned_count": 0,
        "limit": 50,
        "auto_trading_enabled": False,
        "execution_ready": False,
    }
    assert response.json()["signals"] == []


@pytest.mark.anyio
async def test_non_owner_is_denied_before_signal_query(case):
    client, upstream = case
    upstream.user_id = OTHER
    response = await client.get("/owner/signals", headers=bearer(token(subject=OTHER)))
    assert response.status_code == 403
    assert response.json() == {"detail": "OWNER_REQUIRED"}
    assert [request.url.path for request in upstream.calls] == ["/auth/v1/user"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda rows: rows[0].update(owner_id=str(OTHER)),
        lambda rows: rows[0]["experiment"].update(owner_id=str(OTHER)),
        lambda rows: rows[0]["strategy"].update(owner_id=str(OTHER)),
        lambda rows: rows[0].update(confirmed_at="2026-09-19T11:59:59+00:00"),
        lambda rows: rows[0].update(expires_at="2026-09-19T12:10:00+00:00"),
        lambda rows: rows[0]["strategy"].update(data_cutoff="2026-09-19T12:10:01+00:00"),
        lambda rows: rows[0].update(evidence_ids=["same", "same"]),
        lambda rows: rows[0]["strategy"].update(code_hash="not-a-hash"),
        lambda rows: rows[0].update(blocked_reason="must not accompany buy"),
    ],
)
async def test_malformed_or_mixed_evidence_fails_closed(case, mutate):
    client, upstream = case
    upstream.rows = [deepcopy(signal_row())]
    mutate(upstream.rows)
    response = await client.get("/owner/signals", headers=bearer())
    assert response.status_code == 503
    assert response.json() == {"detail": "SIGNALS_UNAVAILABLE"}
    assert str(OTHER) not in response.text


@pytest.mark.anyio
async def test_order_duplicates_and_unbounded_rows_fail_closed(case):
    client, upstream = case
    older = signal_row(row_id=1, signal_id="signal-older")
    older.update(confirmed_at="2026-09-19T12:09:00+00:00")
    older.update(expires_at="2026-09-19T12:09:30+00:00")
    older.update(created_at="2026-09-19T12:09:01+00:00")
    older["strategy"]["data_cutoff"] = "2026-09-19T12:08:00+00:00"
    upstream.rows = [older, signal_row()]
    assert (await client.get("/owner/signals", headers=bearer())).status_code == 503
    upstream.rows = [
        signal_row(row_id=index + 1, signal_id=f"signal-{index}") for index in range(51)
    ]
    assert (await client.get("/owner/signals", headers=bearer())).status_code == 503
    upstream.rows = [signal_row(), signal_row()]
    assert (await client.get("/owner/signals", headers=bearer())).status_code == 503


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, text="private upstream detail"),
        httpx.Response(500, text="private upstream detail"),
        httpx.Response(200, text="not json", headers={"content-type": "text/plain"}),
        httpx.Response(
            200,
            content=b"[" + b" " * (256 * 1024) + b"]",
            headers={"content-type": "application/json"},
        ),
    ],
)
async def test_upstream_failures_are_redacted(case, response):
    client, upstream = case
    upstream.signal_response = response
    result = await client.get("/owner/signals", headers=bearer())
    assert result.status_code == 503
    assert result.json() == {"detail": "SIGNALS_UNAVAILABLE"}
    assert "private upstream detail" not in result.text
