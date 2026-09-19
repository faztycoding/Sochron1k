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
from sochron1k.research_statistics import MAX_EVALUATIONS, ResearchStatisticsReader

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
OTHER = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
SESSION = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
ORIGIN = "https://statistics.fixture.invalid"


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


def evaluation_row(*, row_id: int = 2, owner: UUID = OWNER) -> dict:
    return {
        "id": row_id,
        "owner_id": str(owner),
        "dataset_hash": "d" * 64,
        "split": "walk_forward",
        "metrics": {
            "sample_size": 40,
            "wins": 18,
            "losses": 20,
            "breakeven": 2,
            "net_return_pct": 7.25,
            "expectancy_r": 0.18,
            "expectancy_r_ci95_low": 0.03,
            "expectancy_r_ci95_high": 0.33,
            "max_drawdown_pct": 3.5,
            "profit_factor": 1.24,
        },
        "cost_assumptions": {
            "spread_points": 18,
            "slippage_points": 3,
            "commission_per_lot": 7,
            "swap_included": True,
            "operating_cost_per_trade": 0.12,
            "currency": "USD",
        },
        "data_cutoff": "2026-09-18T23:59:59+00:00",
        "created_at": "2026-09-19T01:00:00+00:00",
        "strategy": {
            "owner_id": str(owner),
            "version_id": "PA01-v1",
            "code_hash": "a" * 64,
            "status": "candidate",
            "data_cutoff": "2026-09-18T23:59:59+00:00",
        },
        "experiment": {
            "owner_id": str(owner),
            "experiment_id": "experiment-pa01-v1",
            "status": "shadow",
            "policy_version": "risk-v1.1",
        },
    }


class Upstream:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = [] if rows is None else rows
        self.calls: list[httpx.Request] = []
        self.evaluation_response: httpx.Response | None = None
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
        assert request.url.path == "/rest/v1/evaluations"
        assert request.method == "GET" and request.content == b""
        assert request.headers["apikey"].startswith("sb_publishable_")
        assert request.headers["authorization"].startswith("Bearer ")
        assert request.url.params["order"] == "created_at.desc,id.desc"
        assert request.url.params["limit"] == str(MAX_EVALUATIONS)
        select = request.url.params["select"]
        assert "owner_id" in select and "strategy_versions" in select and "experiments" in select
        assert all(term not in select for term in ("parameters", "account_ref", "idempotency_key"))
        if self.evaluation_response is not None:
            return self.evaluation_response
        return httpx.Response(200, json=self.rows)


@pytest.fixture
def settings() -> OwnerAuthSettings:
    return OwnerAuthSettings(
        supabase_url=ORIGIN,
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )


@pytest.fixture
async def case(settings):
    upstream = Upstream([evaluation_row()])
    transport = httpx.MockTransport(upstream)
    reader = ResearchStatisticsReader(
        settings,
        transport=transport,
        now=lambda: datetime(2026, 9, 19, 2, 0, tzinfo=UTC),
    )
    app = create_app(owner_auth_settings=settings, research_statistics=reader)
    app.state.owner_verifier = OwnerVerifier(settings, transport=transport, now=lambda: 1_000)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        yield client, upstream


def bearer(value: str | None = None) -> dict[str, str]:
    return {"Authorization": "Bearer " + (token() if value is None else value)}


@pytest.mark.anyio
async def test_owner_projection_is_versioned_bounded_and_redacted(case):
    client, upstream = case
    response = await client.get("/owner/statistics", headers=bearer())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "trading_mode": "demo",
        "read_only": True,
        "source": "supabase-evaluations",
        "read_at_utc": "2026-09-19T02:00:00Z",
        "status": {
            "state": "available",
            "returned_count": 1,
            "limit": 30,
            "auto_trading_enabled": False,
            "execution_ready": False,
            "promotion_decided": False,
        },
        "evaluations": [
            {
                "dataset_hash": "d" * 64,
                "split": "walk_forward",
                "data_cutoff_utc": "2026-09-18T23:59:59Z",
                "created_at_utc": "2026-09-19T01:00:00Z",
                "metrics": {
                    "sample_size": 40,
                    "wins": 18,
                    "losses": 20,
                    "breakeven": 2,
                    "win_rate_pct": "45.0000",
                    "net_return_pct": "7.25",
                    "expectancy_r": "0.18",
                    "expectancy_r_ci95_low": "0.03",
                    "expectancy_r_ci95_high": "0.33",
                    "max_drawdown_pct": "3.5",
                    "profit_factor": "1.24",
                },
                "cost_assumptions": {
                    "spread_points": "18",
                    "slippage_points": "3",
                    "commission_per_lot": "7",
                    "swap_included": True,
                    "operating_cost_per_trade": "0.12",
                    "currency": "USD",
                },
                "strategy": {
                    "version_id": "PA01-v1",
                    "code_hash": "a" * 64,
                    "status": "candidate",
                    "data_cutoff_utc": "2026-09-18T23:59:59Z",
                },
                "experiment": {
                    "experiment_id": "experiment-pa01-v1",
                    "status": "shadow",
                    "policy_version": "risk-v1.1",
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
        "/rest/v1/evaluations",
    ]


@pytest.mark.anyio
async def test_empty_source_has_no_synthetic_metrics(case):
    client, upstream = case
    upstream.rows = []
    response = await client.get("/owner/statistics", headers=bearer())
    assert response.status_code == 200
    assert response.json()["status"] == {
        "state": "awaiting_source",
        "returned_count": 0,
        "limit": 30,
        "auto_trading_enabled": False,
        "execution_ready": False,
        "promotion_decided": False,
    }
    assert response.json()["evaluations"] == []


@pytest.mark.anyio
async def test_optional_experiment_and_undefined_profit_factor_are_explicit(case):
    client, upstream = case
    row = evaluation_row()
    row["experiment"] = None
    row["metrics"]["profit_factor"] = None
    upstream.rows = [row]
    response = await client.get("/owner/statistics", headers=bearer())
    assert response.status_code == 200
    assert response.json()["evaluations"][0]["experiment"] is None
    assert response.json()["evaluations"][0]["metrics"]["profit_factor"] is None


@pytest.mark.anyio
async def test_non_owner_is_denied_before_evaluation_query(case):
    client, upstream = case
    upstream.user_id = OTHER
    response = await client.get("/owner/statistics", headers=bearer(token(subject=OTHER)))
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
        lambda rows: rows[0]["strategy"].update(data_cutoff="2026-09-19T00:00:00+00:00"),
        lambda rows: rows[0]["metrics"].update(sample_size=39),
        lambda rows: rows[0]["metrics"].update(expectancy_r_ci95_high=0.1),
        lambda rows: rows[0]["metrics"].update(max_drawdown_pct=101),
        lambda rows: rows[0]["metrics"].update(unknown_metric=1),
        lambda rows: rows[0]["cost_assumptions"].pop("spread_points"),
        lambda rows: rows[0].update(dataset_hash="not-a-hash"),
    ],
)
async def test_malformed_or_mixed_evaluation_fails_closed(case, mutate):
    client, upstream = case
    upstream.rows = [deepcopy(evaluation_row())]
    mutate(upstream.rows)
    response = await client.get("/owner/statistics", headers=bearer())
    assert response.status_code == 503
    assert response.json() == {"detail": "STATISTICS_UNAVAILABLE"}
    assert str(OTHER) not in response.text


@pytest.mark.anyio
async def test_order_duplicates_and_unbounded_rows_fail_closed(case):
    client, upstream = case
    older = evaluation_row(row_id=1)
    older["created_at"] = "2026-09-19T00:30:00+00:00"
    upstream.rows = [older, evaluation_row()]
    assert (await client.get("/owner/statistics", headers=bearer())).status_code == 503
    upstream.rows = [evaluation_row(row_id=index + 1) for index in range(31)]
    assert (await client.get("/owner/statistics", headers=bearer())).status_code == 503
    upstream.rows = [evaluation_row(), evaluation_row()]
    assert (await client.get("/owner/statistics", headers=bearer())).status_code == 503
    upstream.rows = [evaluation_row(row_id=3), evaluation_row(row_id=2)]
    assert (await client.get("/owner/statistics", headers=bearer())).status_code == 503


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
    upstream.evaluation_response = response
    result = await client.get("/owner/statistics", headers=bearer())
    assert result.status_code == 503
    assert result.json() == {"detail": "STATISTICS_UNAVAILABLE"}
    assert "private upstream detail" not in result.text
