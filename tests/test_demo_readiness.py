from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sochron1k.demo_readiness import (
    DemoOwnerDecisions,
    build_demo_readiness,
    load_demo_owner_decisions,
)
from sochron1k.main import create_app


def decisions_dict() -> dict[str, object]:
    return {
        "protocol": "sochron.demo-owner-decisions.v1",
        "decision_revision": "owner-demo-plan-2026-09",
        "recorded_at_utc": "2026-09-20T08:00:00Z",
        "owner_approved": True,
        "broker_name": "Fixture Broker",
        "demo_server": "Fixture-Demo",
        "account_currency": "USD",
        "starting_capital": "10000.00",
        "symbol": "XAUUSD.fixture",
        "account_mode": "retail_hedging",
        "trading_hours_policy_ref": "hours-policy-v1",
        "overnight_policy": "flat",
        "target_executor": "hostinger_wine",
        "target_region": "fixture-region",
        "monthly_budget_thb": "1000.00",
        "alert_destination_ref": "owner-alert-route",
        "halt_release_authority_ref": "named-owner",
        "approved_secret_channel_ref": "private-channel-record",
        "rpo_seconds": 300,
        "rto_seconds": 1800,
        "magic_number": 910001,
    }


def decisions() -> DemoOwnerDecisions:
    return DemoOwnerDecisions.model_validate(decisions_dict())


def write_private_config(tmp_path: Path, body: dict[str, object]) -> Path:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    path = directory / "demo-readiness.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    path.chmod(0o600)
    return path.resolve()


def build(**overrides):
    values = {
        "owner_decisions_recorded": False,
        "owner_auth_configured": False,
        "telemetry_state": "disabled",
        "chart_enabled": False,
        "chart_states": ("disabled",) * 4,
        "history_configured": False,
        "execution_state": "disabled",
        "execution_evidence_state": "awaiting_configuration",
        "signal_configured": False,
        "policy_state": "disabled",
        "statistics_configured": False,
    }
    values.update(overrides)
    return build_demo_readiness(**values)


def test_private_decision_config_is_strict_and_redacts_startup_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_private_config(tmp_path, decisions_dict())
    monkeypatch.setenv("SOCHRON_DEMO_READINESS_CONFIG_FILE", str(path))
    loaded = load_demo_owner_decisions()
    assert loaded is not None
    assert loaded.protocol == "sochron.demo-owner-decisions.v1"

    unsafe = decisions_dict() | {"account_ref": "must-not-be-admitted"}
    path.write_text(json.dumps(unsafe), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(RuntimeError) as error:
        load_demo_owner_decisions()
    assert str(path) not in str(error.value)
    assert "must-not-be-admitted" not in str(error.value)


def test_missing_config_is_safe_and_noncanonical_or_public_config_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SOCHRON_DEMO_READINESS_CONFIG_FILE", raising=False)
    assert load_demo_owner_decisions() is None

    path = write_private_config(tmp_path, decisions_dict())
    path.chmod(0o644)
    monkeypatch.setenv("SOCHRON_DEMO_READINESS_CONFIG_FILE", str(path))
    with pytest.raises(RuntimeError, match="Invalid private Demo readiness configuration"):
        load_demo_owner_decisions()

    symlink = path.parent / "linked-readiness.json"
    symlink.symlink_to(path)
    monkeypatch.setenv("SOCHRON_DEMO_READINESS_CONFIG_FILE", str(symlink))
    with pytest.raises(RuntimeError, match="Invalid private Demo readiness configuration"):
        load_demo_owner_decisions()


def test_oversized_decision_config_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_private_config(tmp_path, decisions_dict())
    path.write_bytes(b"{" + b" " * 16_384 + b"}")
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_DEMO_READINESS_CONFIG_FILE", str(path))
    with pytest.raises(RuntimeError, match="Invalid private Demo readiness configuration"):
        load_demo_owner_decisions()

    path.chmod(0o600)
    relative = os.path.relpath(path, Path.cwd())
    monkeypatch.setenv("SOCHRON_DEMO_READINESS_CONFIG_FILE", relative)
    with pytest.raises(RuntimeError, match="Invalid private Demo readiness configuration"):
        load_demo_owner_decisions()


def test_decision_record_requires_explicit_approval_and_rejects_secret_fields() -> None:
    with pytest.raises(ValidationError):
        DemoOwnerDecisions.model_validate(decisions_dict() | {"owner_approved": False})
    with pytest.raises(ValidationError):
        DemoOwnerDecisions.model_validate(decisions_dict() | {"password": "unsafe"})
    with pytest.raises(ValidationError):
        DemoOwnerDecisions.model_validate(decisions_dict() | {"token": "unsafe"})


@pytest.mark.anyio
async def test_public_readiness_is_fixed_redacted_and_never_release_ready() -> None:
    app = create_app(demo_owner_decisions=decisions())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ui/demo-readiness")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["state"] == "awaiting_runtime"
    assert body["demo_only"] is True
    for key in (
        "auto_trading_enabled",
        "release_ready",
        "round_trip_authorized",
        "unattended_demo_ready",
    ):
        assert body[key] is False
    assert [gate["id"] for gate in body["gates"]] == [
        "owner_decisions",
        "owner_auth",
        "market_data",
        "execution_bridge",
        "policy_research",
        "target_artifact",
        "broker_round_trip",
        "recovery_observability",
        "operational_authorization",
    ]
    assert [gate["state"] for gate in body["gates"]] == [
        "recorded",
        "missing",
        "missing",
        "missing",
        "missing",
        "not_run",
        "not_run",
        "not_run",
        "not_authorized",
    ]
    text = response.text.lower()
    for forbidden in (
        "fixture broker",
        "fixture-demo",
        "xauusd.fixture",
        "owner-demo-plan",
        "private-channel-record",
        "account_ref",
        "password",
        "token",
    ):
        assert forbidden not in text


def test_runtime_state_never_promotes_target_evidence_or_authorization() -> None:
    ready_runtime = build(
        owner_decisions_recorded=True,
        owner_auth_configured=True,
        telemetry_state="connected",
        chart_enabled=True,
        chart_states=("ready",) * 4,
        history_configured=True,
        execution_state="connected",
        execution_evidence_state="connected",
        signal_configured=True,
        policy_state="ready",
        statistics_configured=True,
    )
    states = {gate.id: gate.state for gate in ready_runtime.gates}
    assert states["market_data"] == "connected"
    assert states["execution_bridge"] == "connected"
    assert states["policy_research"] == "awaiting_source"
    assert states["target_artifact"] == "not_run"
    assert states["broker_round_trip"] == "not_run"
    assert states["recovery_observability"] == "not_run"
    assert states["operational_authorization"] == "not_authorized"
    assert ready_runtime.state == "awaiting_runtime"
    assert ready_runtime.release_ready is False

    degraded = build(telemetry_state="rejected")
    assert degraded.state == "degraded"
    assert degraded.gates[2].state == "degraded"
