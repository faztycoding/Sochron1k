from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.alert_lifecycle import AlertLifecycleJournal
from sochron1k.api_budget import (
    ApiBudgetReader,
    ApiBudgetSettings,
    load_api_budget_settings,
)
from sochron1k.main import create_app
from sochron1k.operational_alerts import build_operational_alert_inventory
from sochron1k.owner_auth import OwnerAuthDenied, OwnerAuthSettings

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class VerifiedOwner:
    async def verify(self, authorization):
        if authorization != ["Bearer owner-fixture"]:
            raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        return OWNER


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int = 1) -> None:
        self.value += timedelta(seconds=seconds)


def private_directory(path: Path) -> Path:
    path = path.resolve()
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def settings(snapshot: Path) -> ApiBudgetSettings:
    return ApiBudgetSettings(
        snapshot_file=snapshot.resolve(),
        currency="USD",
        monthly_limit="100.00",
        warning_fraction="0.70",
        critical_fraction="0.85",
        stale_after_seconds=3600,
    )


def snapshot(now: datetime, *, billed: str = "60.00", estimate: str = "5.00") -> dict:
    start = datetime(now.year, now.month, 1, tzinfo=UTC)
    end = datetime(2026, 10, 1, tzinfo=UTC)
    return {
        "protocol": "sochron.api-budget-snapshot.v1",
        "source_id": "synthetic-provider-billing",
        "revision": "fixture-revision-1",
        "period_start_utc": start.isoformat(),
        "period_end_utc": end.isoformat(),
        "observed_at_utc": now.isoformat(),
        "coverage_until_utc": (now - timedelta(seconds=1)).isoformat(),
        "currency": "USD",
        "billed_cost": billed,
        "unbilled_estimate": estimate,
    }


def write_snapshot(path: Path, body: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(body), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def owner_app(reader: ApiBudgetReader, lifecycle: AlertLifecycleJournal | None = None):
    auth = OwnerAuthSettings(
        supabase_url="https://auth.fixture.invalid",
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )
    app = create_app(owner_auth_settings=auth, api_budget=reader, alert_lifecycle=lifecycle)
    app.state.owner_verifier = VerifiedOwner()
    return app


def quiet_source():
    return {
        "telemetry": SimpleNamespace(
            view=lambda: SimpleNamespace(
                status=SimpleNamespace(state="disabled"), observation=None
            )
        ),
        "execution": SimpleNamespace(status=lambda: SimpleNamespace(state="disabled")),
        "journal": None,
        "history": None,
        "policy": SimpleNamespace(status=lambda: SimpleNamespace(state="disabled")),
    }


def test_scn034_disabled_and_configured_without_snapshot_are_truthful(tmp_path: Path) -> None:
    now = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)
    disabled = ApiBudgetReader(None, utc_now=lambda: now).view()
    assert disabled.state == "disabled"
    assert disabled.policy is None and disabled.evidence is None

    directory = private_directory(tmp_path / "budget")
    waiting = ApiBudgetReader(
        settings(directory / "snapshot.json"), utc_now=lambda: now
    ).view()
    assert waiting.state == "awaiting_snapshot"
    assert waiting.policy is not None and waiting.evidence is None
    assert waiting.policy.monthly_limit == Decimal("100.00")


@pytest.mark.parametrize(
    ("billed", "estimate", "state", "remaining", "percent"),
    [
        ("60.00", "5.00", "connected", "35.00", "65.0000"),
        ("65.00", "5.00", "warning", "30.00", "70.0000"),
        ("80.00", "5.00", "critical", "15.00", "85.0000"),
        ("97.00", "3.00", "exhausted", "0", "100.0000"),
        ("110.00", "2.00", "exhausted", "0", "112.0000"),
    ],
)
def test_scn034_exact_thresholds_and_redacted_evidence(
    tmp_path: Path,
    billed: str,
    estimate: str,
    state: str,
    remaining: str,
    percent: str,
) -> None:
    now = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)
    directory = private_directory(tmp_path / state)
    path = directory / "snapshot.json"
    write_snapshot(path, snapshot(now, billed=billed, estimate=estimate))
    view = ApiBudgetReader(settings(path), utc_now=lambda: now).view()
    assert view.state == state and view.evidence is not None
    assert view.evidence.total_cost == Decimal(billed) + Decimal(estimate)
    assert view.evidence.remaining_amount == Decimal(remaining)
    assert view.evidence.usage_percent == Decimal(percent)
    payload = view.model_dump_json()
    assert "synthetic-provider-billing" not in payload
    assert "fixture-revision" not in payload and str(path) not in payload
    assert len(view.evidence.source_ref) == 16


def test_scn034_stale_future_wrong_currency_and_public_snapshot_fail_closed(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)
    directory = private_directory(tmp_path / "fail-closed")
    path = directory / "snapshot.json"

    stale_body = snapshot(now - timedelta(hours=2))
    write_snapshot(path, stale_body)
    reader = ApiBudgetReader(settings(path), utc_now=lambda: now)
    assert reader.view().state == "stale"

    future = snapshot(now + timedelta(seconds=1))
    write_snapshot(path, future)
    assert reader.view().state == "degraded"

    wrong_currency = snapshot(now)
    wrong_currency["currency"] = "THB"
    write_snapshot(path, wrong_currency)
    assert reader.view().state == "degraded"

    write_snapshot(path, snapshot(now))
    path.chmod(0o644)
    assert reader.view().state == "degraded"
    path.chmod(0o600)

    linked = directory / "linked.json"
    os.link(path, linked)
    assert reader.view().state == "degraded"
    linked.unlink()

    path.write_text("x" * 16_385, encoding="utf-8")
    path.chmod(0o600)
    assert reader.view().state == "degraded"

    path.write_text('{"protocol":"a","protocol":"b"}', encoding="utf-8")
    assert reader.view().state == "degraded"

    alias = directory / "alias.json"
    os.symlink(path, alias)
    with pytest.raises(ValueError, match="canonical path"):
        ApiBudgetSettings(
            snapshot_file=alias,
            currency="USD",
            monthly_limit="100.00",
            warning_fraction="0.70",
            critical_fraction="0.85",
            stale_after_seconds=3600,
        )


def test_scn034_private_config_is_exact_and_can_explicitly_disable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = private_directory(tmp_path / "config")
    snapshot_path = directory / "snapshot.json"
    config = directory / "budget.json"
    body = {
        "enabled": True,
        "snapshot_file": str(snapshot_path),
        "currency": "USD",
        "monthly_limit": "100.00",
        "warning_fraction": "0.70",
        "critical_fraction": "0.85",
        "stale_after_seconds": 3600,
    }
    config.write_text(json.dumps(body), encoding="utf-8")
    config.chmod(0o600)
    monkeypatch.setenv("SOCHRON_API_BUDGET_CONFIG_FILE", str(config))
    loaded = load_api_budget_settings()
    assert loaded is not None and loaded.snapshot_file == snapshot_path

    config.write_text('{"enabled":false}', encoding="utf-8")
    assert load_api_budget_settings() is None

    config.write_text('{"enabled":true,"enabled":false}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="Invalid private API budget configuration"):
        load_api_budget_settings()

    body["monthly_limit"] = 100.0
    config.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Invalid private API budget configuration"):
        load_api_budget_settings()


@pytest.mark.anyio
async def test_scn034_owner_view_and_alert_lifecycle_clear_only_after_fresh_recovery(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=5)
    directory = private_directory(tmp_path / "runtime")
    snapshot_path = directory / "snapshot.json"
    write_snapshot(snapshot_path, snapshot(now, billed="80.00", estimate="5.00"))
    reader = ApiBudgetReader(settings(snapshot_path))
    clock = Clock(datetime.now(UTC) + timedelta(seconds=1))
    lifecycle = AlertLifecycleJournal(
        private_directory(tmp_path / "lifecycle"), utc_now=clock
    )
    app = owner_app(reader, lifecycle)
    headers = {"Authorization": "Bearer owner-fixture"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        denied = await client.get("/owner/api-budget")
        budget = await client.get("/owner/api-budget", headers=headers)
        initial = await client.get("/owner/alerts", headers=headers)
        assert denied.status_code == 401
        assert budget.status_code == 200 and budget.headers["cache-control"] == "no-store"
        assert budget.json()["state"] == "critical"
        alert = next(item for item in initial.json()["alerts"] if item["kind"] == "api_budget")
        assert alert["severity"] == "critical" and alert["acknowledge_allowed"] is True

        clock.advance()
        acknowledged = await client.post(
            f"/owner/alerts/{alert['condition_id']}/acknowledge",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert acknowledged.status_code == 200
        clock.advance()
        active_resolution = await client.post(
            f"/owner/alerts/{alert['condition_id']}/resolve",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert active_resolution.status_code == 409

        write_snapshot(snapshot_path, snapshot(now, billed="20.00", estimate="5.00"))
        cleared = await client.get("/owner/alerts", headers=headers)
        cleared_alert = next(
            item for item in cleared.json()["alerts"]
            if item["condition_id"] == alert["condition_id"]
        )
        assert cleared_alert["lifecycle_state"] == "cleared"
        assert cleared_alert["resolve_allowed"] is True
        clock.advance()
        resolved = await client.post(
            f"/owner/alerts/{alert['condition_id']}/resolve",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert resolved.status_code == 200


def test_scn034_alert_inventory_marks_budget_available_and_source_failures(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)
    directory = private_directory(tmp_path / "alerts")
    path = directory / "snapshot.json"
    write_snapshot(path, snapshot(now, billed="65.00", estimate="5.00"))
    source = quiet_source()
    inventory = build_operational_alert_inventory(
        **source, api_budget=ApiBudgetReader(settings(path), utc_now=lambda: now), now=now
    )
    budget_coverage = inventory.coverage[-1]
    assert budget_coverage.implementation == "available"
    assert budget_coverage.runtime == "connected"
    assert budget_coverage.api_routes == (
        "/api/owner/alerts", "/api/owner/api-budget"
    )
    assert [(item.kind, item.detail_code) for item in inventory.alerts] == [
        ("api_budget", "api_budget_warning")
    ]

    path.chmod(0o644)
    degraded = build_operational_alert_inventory(
        **source, api_budget=ApiBudgetReader(settings(path), utc_now=lambda: now), now=now
    )
    assert degraded.status == "degraded"
    assert any(item.detail_code == "api_budget_degraded" for item in degraded.alerts)
