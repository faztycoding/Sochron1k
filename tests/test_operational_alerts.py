from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.alert_lifecycle import (
    AlertLifecycleJournal,
    AlertLifecycleUnavailable,
    enrich_operational_alert_inventory,
)
from sochron1k.api_budget import ApiBudgetReader
from sochron1k.main import create_app
from sochron1k.operational_alerts import KINDS, OperationalAlert, build_operational_alert_inventory
from sochron1k.owner_auth import OwnerAuthDenied, OwnerAuthSettings

OWNER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
FOREIGN = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
NOW = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int = 1) -> None:
        self.value += timedelta(seconds=seconds)


class VerifiedOwner:
    async def verify(self, authorization):
        if authorization != ["Bearer owner-fixture"]:
            raise OwnerAuthDenied(401, "AUTH_REQUIRED")
        return OWNER


def private_directory(path: Path) -> Path:
    path = path.resolve()
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path


def owner_app(lifecycle: AlertLifecycleJournal | None = None):
    settings = OwnerAuthSettings(
        supabase_url="https://auth.fixture.invalid",
        public_key=SecretStr("sb_publishable_" + "fixture" * 4),
        owner_id=OWNER,
    )
    app = create_app(owner_auth_settings=settings, alert_lifecycle=lifecycle)
    app.state.owner_verifier = VerifiedOwner()
    return app


def stale_telemetry(observed: datetime = NOW):
    return SimpleNamespace(
        view=lambda: SimpleNamespace(
            status=SimpleNamespace(state="stale"),
            observation=SimpleNamespace(received_time_utc=observed),
        )
    )


def connected_telemetry():
    return SimpleNamespace(
        view=lambda: SimpleNamespace(
            status=SimpleNamespace(state="connected"),
            observation=SimpleNamespace(received_time_utc=NOW),
        )
    )


def lifecycle_alert(observed: datetime = NOW) -> OperationalAlert:
    return OperationalAlert(
        id="a" * 24,
        condition_id="b" * 24,
        kind="order_reject",
        severity="warning",
        source="execution_journal",
        source_ref="c" * 16,
        detail_code="entry_rejected",
        observed_at_utc=observed,
        evidence_routes=("/api/owner/execution",),
    )


@pytest.mark.anyio
async def test_scn033_owner_inventory_is_redacted_and_mutations_need_configuration() -> None:
    app = owner_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        unauthorized = await client.get("/owner/alerts")
        response = await client.get(
            "/owner/alerts", headers={"Authorization": "Bearer owner-fixture"}
        )
        bare_mutation = await client.post(
            "/owner/alerts", headers={"Authorization": "Bearer owner-fixture"}
        )
        disabled = await client.post(
            f"/owner/alerts/{'a' * 24}/acknowledge",
            headers={
                "Authorization": "Bearer owner-fixture",
                "Idempotency-Key": str(uuid4()),
            },
        )
    assert unauthorized.status_code == 401 and bare_mutation.status_code == 405
    assert disabled.status_code == 503 and disabled.json()["detail"] == "ALERT_LIFECYCLE_DISABLED"
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["protocol"] == "sochron.operational-alerts.v3"
    assert body["trading_mode"] == "demo" and body["read_only"] is True
    assert body["auto_trading_enabled"] is False and body["execution_ready"] is False
    assert body["delivery_configured"] is False and body["status"] == "partial"
    assert body["lifecycle_runtime"] == "awaiting_configuration"
    assert body["lifecycle_mutations_enabled"] is False
    assert body["api_budget"]["state"] == "disabled"
    assert body["alerts"] == [] and body["truncated"] is False
    assert [item["kind"] for item in body["coverage"]] == list(KINDS)
    assert body["coverage"][-1] == {
        "kind": "api_budget",
        "implementation": "available",
        "runtime": "awaiting_configuration",
        "api_routes": ["/api/owner/alerts", "/api/owner/api-budget"],
        "sources": ["api_budget"],
    }
    for forbidden in ("password", "account_ref", "server", "filesystem", "token"):
        assert forbidden not in response.text.lower()


def test_scn033_stale_telemetry_has_stable_condition_identity_without_delivery_claim() -> None:
    telemetry = stale_telemetry()
    execution = SimpleNamespace(status=lambda: SimpleNamespace(state="connected"))
    policy = SimpleNamespace(status=lambda: SimpleNamespace(state="disabled"))
    first = build_operational_alert_inventory(
        telemetry=telemetry, execution=execution, journal=None, history=None,
        policy=policy, api_budget=ApiBudgetReader(None), now=NOW,
    )
    second = build_operational_alert_inventory(
        telemetry=telemetry, execution=execution, journal=None, history=None,
        policy=policy, api_budget=ApiBudgetReader(None), now=NOW + timedelta(seconds=2),
    )
    assert first.status == "degraded" and first.delivery_configured is False
    assert [(item.kind, item.source, item.detail_code) for item in first.alerts] == [
        ("bridge_disconnected", "telemetry_bridge", "telemetry_stale"),
        ("stale_price", "telemetry_bridge", "price_or_heartbeat_stale"),
    ]
    assert all(
        item.lifecycle_state == "active"
        and item.acknowledged_by is None
        and item.acknowledged_at_utc is None
        and item.resolved_at_utc is None
        for item in first.alerts
    )
    assert [item.condition_id for item in first.alerts] == [
        item.condition_id for item in second.alerts
    ]
    assert len({item.condition_id for item in first.alerts}) == 2


@pytest.mark.anyio
async def test_scn033_acknowledge_replay_clear_resolve_restart_and_recurrence(
    tmp_path: Path,
) -> None:
    clock = Clock()
    directory = private_directory(tmp_path / "lifecycle")
    journal = AlertLifecycleJournal(directory, utc_now=clock)
    app = owner_app(journal)
    app.state.telemetry_bridge = stale_telemetry()
    headers = {"Authorization": "Bearer owner-fixture"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        initial = await client.get("/owner/alerts", headers=headers)
        stale = next(item for item in initial.json()["alerts"] if item["kind"] == "stale_price")
        assert stale["lifecycle_state"] == "active" and stale["acknowledge_allowed"] is True
        missing_key = await client.post(
            f"/owner/alerts/{stale['condition_id']}/acknowledge", headers=headers
        )
        duplicate_key = await client.post(
            f"/owner/alerts/{stale['condition_id']}/acknowledge",
            headers=[
                ("Authorization", "Bearer owner-fixture"),
                ("Idempotency-Key", str(uuid4())),
                ("Idempotency-Key", str(uuid4())),
            ],
        )
        assert missing_key.status_code == duplicate_key.status_code == 400
        clock.advance()
        key = str(uuid4())
        mutation_headers = {**headers, "Idempotency-Key": key}
        acknowledged = await client.post(
            f"/owner/alerts/{stale['condition_id']}/acknowledge", headers=mutation_headers,
        )
        replay = await client.post(
            f"/owner/alerts/{stale['condition_id']}/acknowledge", headers=mutation_headers,
        )
        assert acknowledged.status_code == replay.status_code == 200
        assert acknowledged.json() == replay.json()
        assert acknowledged.json()["lifecycle_state"] == "acknowledged"
        conflict = await client.post(
            f"/owner/alerts/{stale['condition_id']}/resolve", headers=mutation_headers,
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == "IDEMPOTENCY_CONFLICT"
        still_active = await client.post(
            f"/owner/alerts/{stale['condition_id']}/resolve",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert still_active.status_code == 409
        assert still_active.json()["detail"] == "ALERT_STILL_ACTIVE_OR_SOURCE_INCOMPLETE"
        app.state.telemetry_bridge = connected_telemetry()
        cleared = await client.get("/owner/alerts", headers=headers)
        cleared_alert = next(
            item
            for item in cleared.json()["alerts"]
            if item["condition_id"] == stale["condition_id"]
        )
        assert cleared_alert["lifecycle_state"] == "cleared"
        assert cleared_alert["resolve_allowed"] is True
        idempotency_conflict = await client.post(
            f"/owner/alerts/{stale['condition_id']}/resolve", headers=mutation_headers,
        )
        assert idempotency_conflict.status_code == 409
        assert idempotency_conflict.json()["detail"] == "IDEMPOTENCY_CONFLICT"
        clock.advance()
        resolve_key = str(uuid4())
        resolved = await client.post(
            f"/owner/alerts/{stale['condition_id']}/resolve",
            headers={**headers, "Idempotency-Key": resolve_key},
        )
        assert resolved.status_code == 200 and resolved.json()["lifecycle_state"] == "resolved"
        resolved_replay = await client.post(
            f"/owner/alerts/{stale['condition_id']}/resolve",
            headers={**headers, "Idempotency-Key": resolve_key},
        )
        assert resolved_replay.status_code == 200
        assert resolved_replay.json() == resolved.json()

    restarted = AlertLifecycleJournal(directory, utc_now=clock)
    restarted_app = owner_app(restarted)
    restarted_app.state.telemetry_bridge = connected_telemetry()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=restarted_app), base_url="http://fixture"
    ) as client:
        retained = await client.get("/owner/alerts", headers=headers)
        item = next(
            alert for alert in retained.json()["alerts"]
            if alert["condition_id"] == stale["condition_id"]
        )
        assert item["lifecycle_state"] == "resolved"
        assert item["acknowledged_by"] == "owner"
        assert item["resolved_at_utc"] is not None
        clock.advance(10)
        restarted_app.state.telemetry_bridge = stale_telemetry(clock.value)
        recurrence = await client.get("/owner/alerts", headers=headers)
        recurring = next(
            alert for alert in recurrence.json()["alerts"] if alert["kind"] == "stale_price"
        )
        assert recurring["lifecycle_state"] == "active"
        assert recurring["acknowledge_allowed"] is True
        assert recurring["acknowledged_by"] is None


def test_scn033_rejection_can_resolve_as_workflow_event(tmp_path: Path) -> None:
    clock = Clock()
    journal = AlertLifecycleJournal(
        private_directory(tmp_path / "rejection-lifecycle"), utc_now=clock
    )
    alert = lifecycle_alert(NOW - timedelta(seconds=1))
    clock.advance()
    journal.acknowledge(OWNER, alert, uuid4())
    clock.advance()
    receipt = journal.resolve(OWNER, alert.condition_id, uuid4())
    assert receipt.lifecycle_state == "resolved"
    assert journal.records(FOREIGN) == ()


def test_scn033_private_journal_detects_replacement_corruption_and_clock_regression(
    tmp_path: Path,
) -> None:
    clock = Clock()
    directory = private_directory(tmp_path / "guarded-lifecycle")
    journal = AlertLifecycleJournal(directory, utc_now=clock)
    clock.advance()
    journal.acknowledge(OWNER, lifecycle_alert(NOW), uuid4())
    original = directory / "alerts.sqlite3"
    moved = directory / "retained.sqlite3"
    original.rename(moved)
    original.write_bytes(moved.read_bytes())
    original.chmod(0o600)
    with pytest.raises(AlertLifecycleUnavailable):
        journal.records(OWNER)
    original.unlink()
    moved.rename(original)
    journal = AlertLifecycleJournal(directory, utc_now=clock)
    with sqlite3.connect(original) as db:
        db.execute("UPDATE alert_lifecycle SET snapshot_digest=?", ("0" * 64,))
    with pytest.raises(AlertLifecycleUnavailable):
        journal.records(OWNER)

    clock_directory = private_directory(tmp_path / "clock-lifecycle")
    guarded_clock = Clock()
    clock_journal = AlertLifecycleJournal(clock_directory, utc_now=guarded_clock)
    guarded_clock.advance()
    clock_journal.acknowledge(OWNER, lifecycle_alert(NOW), uuid4())
    guarded_clock.value = NOW
    with pytest.raises(AlertLifecycleUnavailable):
        clock_journal.records(OWNER)


def test_scn033_private_directory_and_locked_write_fail_closed(tmp_path: Path) -> None:
    public = (tmp_path / "public").resolve()
    public.mkdir(mode=0o755)
    with pytest.raises(AlertLifecycleUnavailable):
        AlertLifecycleJournal(public)
    clock = Clock()
    directory = private_directory(tmp_path / "locked")
    journal = AlertLifecycleJournal(directory, utc_now=clock)
    blocker = sqlite3.connect(directory / "alerts.sqlite3", isolation_level=None)
    try:
        blocker.execute("BEGIN IMMEDIATE")
        clock.advance()
        with pytest.raises(AlertLifecycleUnavailable):
            journal.acknowledge(OWNER, lifecycle_alert(NOW), uuid4())
    finally:
        blocker.rollback()
        blocker.close()


def test_scn033_configured_directory_must_be_canonical(tmp_path: Path) -> None:
    directory = private_directory(tmp_path / "canonical")
    alias = directory.parent / "alias"
    os.symlink(directory, alias)
    with pytest.raises(AlertLifecycleUnavailable):
        AlertLifecycleJournal(alias)


def test_scn033_current_condition_is_not_lost_when_history_is_truncated(
    tmp_path: Path,
) -> None:
    clock = Clock()
    journal = AlertLifecycleJournal(
        private_directory(tmp_path / "bounded-history"), utc_now=clock
    )
    first: OperationalAlert | None = None
    for index in range(65):
        alert = OperationalAlert(
            id=f"{index + 100:024x}",
            condition_id=f"{index:024x}",
            kind="order_reject",
            severity="warning",
            source="execution_journal",
            source_ref=f"{index:016x}",
            detail_code="entry_rejected",
            observed_at_utc=NOW,
            evidence_routes=("/api/owner/execution",),
        )
        first = first or alert
        clock.advance()
        journal.acknowledge(OWNER, alert, uuid4())
    assert first is not None
    empty = build_operational_alert_inventory(
        telemetry=SimpleNamespace(
            view=lambda: SimpleNamespace(
                status=SimpleNamespace(state="disabled"), observation=None
            )
        ),
        execution=SimpleNamespace(status=lambda: SimpleNamespace(state="disabled")),
        journal=None,
        history=None,
        policy=SimpleNamespace(status=lambda: SimpleNamespace(state="disabled")),
        api_budget=ApiBudgetReader(None),
        now=clock.value,
    )
    inventory = empty.model_copy(update={"alerts": (first,)})
    enriched = enrich_operational_alert_inventory(inventory, OWNER, journal)
    current = next(
        item for item in enriched.alerts if item.condition_id == first.condition_id
    )
    assert enriched.truncated is True
    assert current.lifecycle_state == "acknowledged"
    assert current.acknowledged_by == "owner"
