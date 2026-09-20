from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.main import create_app
from sochron1k.operational_alerts import KINDS, build_operational_alert_inventory
from sochron1k.owner_auth import OwnerAuthDenied, OwnerAuthSettings

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
NOW = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)


class VerifiedOwner:
    async def verify(self, authorization):
        if authorization != ["Bearer owner-fixture"]:
            raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        return OWNER


def owner_app():
    settings = OwnerAuthSettings(
        supabase_url="https://auth.fixture.invalid",
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )
    app = create_app(owner_auth_settings=settings)
    app.state.owner_verifier = VerifiedOwner()
    return app


@pytest.mark.anyio
async def test_scn032_owner_route_is_read_only_redacted_and_explicitly_partial() -> None:
    app = owner_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        unauthorized = await client.get("/owner/alerts")
        response = await client.get(
            "/owner/alerts", headers={"Authorization": "Bearer owner-fixture"}
        )
        mutation = await client.post(
            "/owner/alerts", headers={"Authorization": "Bearer owner-fixture"}
        )
    assert unauthorized.status_code == 401 and mutation.status_code == 405
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["protocol"] == "sochron.operational-alerts.v1"
    assert body["trading_mode"] == "demo" and body["read_only"] is True
    assert body["auto_trading_enabled"] is False and body["execution_ready"] is False
    assert body["delivery_configured"] is False and body["status"] == "partial"
    assert body["alerts"] == [] and body["truncated"] is False
    assert [item["kind"] for item in body["coverage"]] == list(KINDS)
    assert body["coverage"][-1] == {
        "kind": "api_budget",
        "implementation": "missing",
        "runtime": "awaiting_configuration",
        "api_routes": ["/api/owner/alerts"],
        "sources": ["api_budget"],
    }
    for forbidden in ("password", "account_ref", "server", "filesystem", "token"):
        assert forbidden not in response.text.lower()


def test_scn032_stale_telemetry_derives_alerts_without_delivery_claim() -> None:
    telemetry = SimpleNamespace(
        view=lambda: SimpleNamespace(
            status=SimpleNamespace(state="stale"),
            observation=SimpleNamespace(received_time_utc=NOW),
        )
    )
    execution = SimpleNamespace(status=lambda: SimpleNamespace(state="connected"))
    policy = SimpleNamespace(status=lambda: SimpleNamespace(state="disabled"))

    view = build_operational_alert_inventory(
        telemetry=telemetry,
        execution=execution,
        journal=None,
        history=None,
        policy=policy,
        now=NOW,
    )

    assert view.status == "degraded" and view.delivery_configured is False
    assert [(item.kind, item.source, item.detail_code) for item in view.alerts] == [
        ("bridge_disconnected", "telemetry_bridge", "telemetry_stale"),
        ("stale_price", "telemetry_bridge", "price_or_heartbeat_stale"),
    ]
    assert all(
        item.acknowledged_by is None and item.resolved_at_utc is None
        for item in view.alerts
    )
    assert all(item.observed_at_utc == NOW for item in view.alerts)
    assert len({item.id for item in view.alerts}) == 2
