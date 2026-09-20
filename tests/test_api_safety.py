from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sochron1k.chart import ChartSettings
from sochron1k.execution_bridge import ExecutionBridgeSettings
from sochron1k.main import create_app
from sochron1k.owner_auth import OwnerAuthSettings
from sochron1k.telemetry import BridgeSettings, DemoIdentity

IDENTITY = DemoIdentity(
    executor_id="synthetic-executor",
    account_ref="123456789",
    server="Synthetic-Demo",
    currency="USD",
    margin_mode="retail_hedging",
    symbol="XAUUSD.fixture",
)


@pytest.mark.anyio
@pytest.mark.parametrize("requested_mode", ["demo", "live"])
async def test_ac08_health_is_demo_only_and_never_claims_execution_ready(
    monkeypatch, requested_mode: str
) -> None:
    monkeypatch.setenv("TRADING_MODE", requested_mode)
    monkeypatch.setenv("AUTO_TRADING_ENABLED", "true")
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sochron1k-api",
        "version": "0.1.0",
        "trading_mode": "demo",
        "auto_trading_enabled": False,
        "execution_ready": False,
    }


@pytest.mark.anyio
async def test_ui_connection_map_is_redacted_and_truthful_when_unconfigured() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        response = await client.get("/ui/connections")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["demo_only"] is True
    assert body["auto_trading_enabled"] is False
    assert body["execution_ready"] is False
    nodes = {node["id"]: node for node in body["connections"]}
    assert list(nodes) == [
        "core_api",
        "demo_readiness",
        "owner_auth",
        "market_telemetry",
        "native_chart",
        "bar_history",
        "execution_evidence",
        "operational_alerts",
        "signals",
        "statistics",
    ]
    assert nodes["core_api"]["runtime"] == "connected"
    assert nodes["demo_readiness"] == {
        "id": "demo_readiness",
        "implementation": "available",
        "runtime": "connected",
        "current_routes": [
            "/api/ui/demo-readiness",
            "/api/owner/target-evidence",
        ],
        "required_route": None,
        "sources": [
            "owner_decisions",
            "runtime_gates",
            "target_evidence_snapshot",
        ],
    }
    for key in ("owner_auth", "market_telemetry", "native_chart", "bar_history"):
        assert nodes[key]["runtime"] == "awaiting_configuration"
    assert nodes["execution_evidence"] == {
        "id": "execution_evidence",
        "implementation": "available",
        "runtime": "awaiting_configuration",
        "current_routes": [
            "/api/executor/v1/status",
            "/api/owner/execution",
            "/api/internal/v1/demo-round-trip/status",
        ],
        "required_route": None,
        "sources": [
            "mt5_execution",
            "local_execution_journal",
            "bounded_demo_round_trip_admission",
        ],
    }
    assert nodes["operational_alerts"] == {
        "id": "operational_alerts",
        "implementation": "partial",
        "runtime": "awaiting_configuration",
        "current_routes": [
            "/api/owner/alerts",
            "/api/owner/alerts/{condition_id}/acknowledge",
            "/api/owner/alerts/{condition_id}/resolve",
            "/api/owner/api-budget",
        ],
        "required_route": "configured receipt-capable alert destination",
        "sources": [
            "telemetry_status",
            "execution_status",
            "execution_journal",
            "bar_history",
            "policy_status",
            "alert_lifecycle",
            "api_budget_snapshot",
            "alert_delivery_outbox",
        ],
    }
    assert nodes["signals"] == {
        "id": "signals",
        "implementation": "available",
        "runtime": "awaiting_configuration",
        "current_routes": ["/api/policy/v1/status", "/api/owner/signals"],
        "required_route": None,
        "sources": ["mt5_policy_evidence", "news_gate", "supabase_signals"],
    }
    assert nodes["statistics"] == {
        "id": "statistics",
        "implementation": "available",
        "runtime": "awaiting_configuration",
        "current_routes": ["/api/owner/statistics"],
        "required_route": None,
        "sources": ["supabase_evaluations"],
    }
    text = response.text.lower()
    for forbidden in ("token", "password", "owner_id", "account_ref", "supabase_url"):
        assert forbidden not in text


@pytest.mark.anyio
async def test_ui_connection_map_separates_configured_from_connected() -> None:
    telemetry = BridgeSettings(
        identity=IDENTITY,
        token=SecretStr("a" * 43),
        broker_utc_offset_seconds=0,
    )
    owner = OwnerAuthSettings(
        supabase_url="https://auth.fixture.invalid",
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )
    execution = ExecutionBridgeSettings(
        identity=IDENTITY,
        token=SecretStr("b" * 43),
        magic_number=910001,
    )
    app = create_app(
        bridge_settings=telemetry,
        owner_auth_settings=owner,
        chart_settings=ChartSettings(
            offset_valid_from_server_s=1,
            offset_valid_until_server_s=4_102_444_800,
        ),
        execution_bridge_settings=execution,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        nodes = {
            node["id"]: node for node in (await client.get("/ui/connections")).json()["connections"]
        }
    assert nodes["owner_auth"]["runtime"] == "configured"
    assert nodes["market_telemetry"]["runtime"] == "awaiting_source"
    assert nodes["native_chart"]["runtime"] == "awaiting_source"
    assert nodes["bar_history"]["runtime"] == "awaiting_configuration"
    assert nodes["execution_evidence"]["runtime"] == "awaiting_source"
    assert nodes["operational_alerts"]["runtime"] == "awaiting_source"
    assert nodes["signals"]["runtime"] == "awaiting_configuration"
    assert nodes["statistics"]["runtime"] == "awaiting_source"
