from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sochron1k.alert_delivery_source import (
    AlertDeliveryFact,
    AlertSourceSettings,
    load_alert_source_settings,
)
from sochron1k.alert_delivery_status import AlertDeliveryStatusReader
from sochron1k.main import create_app
from sochron1k.operational_alerts import build_operational_alert_inventory
from sochron_worker.alert_delivery_cli import main as delivery_main
from sochron_worker.alert_delivery_config import (
    AlertDeliveryConfigInvalid,
    load_alert_delivery_config,
)
from sochron_worker.alert_delivery_driver import (
    AlertDeliveryDriver,
    AlertDestinationConflict,
    AlertDestinationUnavailable,
    AlertSendBudgetExhausted,
)
from sochron_worker.alert_delivery_http import HttpAlertDestination, HttpAlertSource
from sochron_worker.alert_delivery_journal import (
    AlertDeliveryJournal,
    AlertDeliveryJournalUnavailable,
    AlertDeliveryReceipt,
)
from sochron_worker.sync_journal import canonical

SOURCE_TOKEN = "source_" + "a" * 43
DESTINATION_TOKEN = "destination_" + "b" * 43
NOW = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)


def private_directory(tmp_path: Path, name: str) -> Path:
    directory = tmp_path / name
    directory.mkdir(mode=0o700)
    return directory.resolve()


def private_file(directory: Path, name: str, content: str) -> Path:
    path = directory / name
    path.touch(mode=0o600)
    path.write_text(content)
    path.chmod(0o600)
    return path.resolve()


def source_settings() -> AlertSourceSettings:
    return AlertSourceSettings(protocol="sochron.alert-source-config.v1", token=SOURCE_TOKEN)


def fact(identifier: str = "1" * 24) -> AlertDeliveryFact:
    return AlertDeliveryFact(
        id=identifier,
        condition_id="2" * 24,
        kind="stale_price",
        severity="critical",
        source="telemetry_bridge",
        source_ref="current",
        detail_code="price_or_heartbeat_stale",
        observed_at_utc=NOW - timedelta(minutes=1),
        evidence_routes=("/api/owner/telemetry",),
    )


class FakeSource:
    origin = "http://127.0.0.1:8123"

    def __init__(self, alerts=None) -> None:
        self.alerts = (fact(),) if alerts is None else alerts
        self.calls = 0

    def read(self):
        from sochron1k.alert_delivery_source import AlertDeliverySourceSnapshot

        self.calls += 1
        return AlertDeliverySourceSnapshot(
            generated_at_utc=NOW, truncated=False, alerts=self.alerts
        )


class FakeDestination:
    origin = "http://127.0.0.1:8124"
    destination_ref = "owner-primary"

    def __init__(self) -> None:
        self.receipts: dict[str, AlertDeliveryReceipt] = {}
        self.store_calls: list[str] = []
        self.fail_store = False
        self.missing = False
        self.conflict = False

    def store(self, intent) -> None:
        self.store_calls.append(intent.delivery_id)
        if self.fail_store:
            raise AlertDestinationUnavailable()
        self.receipts[intent.delivery_id] = AlertDeliveryReceipt(
            protocol="sochron.alert-delivery-receipt.v1",
            delivery_id=intent.delivery_id,
            destination_ref=self.destination_ref,
            payload_sha256=intent.digest,
            accepted_at_utc=NOW,
        )

    def read(self, intent):
        if self.conflict:
            raise AlertDestinationConflict()
        if self.missing:
            return None
        return self.receipts.get(intent.delivery_id)


def journal(directory: Path, *, create: bool = True) -> AlertDeliveryJournal:
    return AlertDeliveryJournal(
        directory,
        source_origin=FakeSource.origin,
        destination_origin=FakeDestination.origin,
        destination_ref=FakeDestination.destination_ref,
        create=create,
        utc_now=lambda: NOW,
    )


@pytest.mark.anyio
async def test_ac01_private_alert_source_auth_and_redaction() -> None:
    app = create_app(alert_source_settings=source_settings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        denied = await client.get("/internal/v1/alerts")
        wrong = await client.get("/internal/v1/alerts", headers={"Authorization": "Bearer wrong"})
        response = await client.get(
            "/internal/v1/alerts",
            headers={"Authorization": "Bearer " + SOURCE_TOKEN},
        )
    assert denied.status_code == wrong.status_code == 401
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body == {
        "protocol": "sochron.alert-delivery-source.v1",
        "generated_at_utc": body["generated_at_utc"],
        "truncated": False,
        "alerts": [],
    }
    serialized = response.text
    assert SOURCE_TOKEN not in serialized
    assert all(word not in serialized for word in ("owner_id", "account_ref", "server"))


def test_ac01_alert_source_credential_must_be_separate() -> None:
    from pydantic import SecretStr
    from sochron1k.telemetry import BridgeSettings, DemoIdentity

    bridge = BridgeSettings(
        identity=DemoIdentity(
            executor_id="executor",
            account_ref="demo",
            server="server",
            currency="USD",
            margin_mode="retail_hedging",
            symbol="XAUUSD",
        ),
        token=SecretStr(SOURCE_TOKEN),
        broker_utc_offset_seconds=0,
    )
    with pytest.raises(RuntimeError, match="separate service credential"):
        create_app(bridge_settings=bridge, alert_source_settings=source_settings())


@pytest.mark.parametrize("untrusted", ["public", "hardlink", "symlink", "oversized"])
def test_ac01_untrusted_source_config_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    untrusted: str,
) -> None:
    root = private_directory(tmp_path, untrusted)
    content = json.dumps({"protocol": "sochron.alert-source-config.v1", "token": SOURCE_TOKEN})
    trusted = private_file(root, "trusted.json", content)
    selected = trusted
    if untrusted == "public":
        trusted.chmod(0o644)
    elif untrusted == "hardlink":
        selected = root / "selected.json"
        selected.hardlink_to(trusted)
    elif untrusted == "symlink":
        selected = root / "selected.json"
        selected.symlink_to(trusted)
    else:
        trusted.write_bytes(b"x" * 4097)
        trusted.chmod(0o600)
    monkeypatch.setenv("SOCHRON_ALERT_SOURCE_CONFIG_FILE", str(selected))
    with pytest.raises(RuntimeError, match="Invalid private alert source"):
        load_alert_source_settings()


def test_ac02_config_is_explicit_private_and_credentials_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SOCHRON_ALERT_DELIVERY_CONFIG_FILE", raising=False)
    assert load_alert_delivery_config() is None
    root = private_directory(tmp_path, "config")
    state = private_directory(tmp_path, "state")
    source_config = private_file(
        root,
        "source.json",
        json.dumps({"protocol": "sochron.alert-source-config.v1", "token": SOURCE_TOKEN}),
    )
    destination_token = private_file(root, "destination.token", DESTINATION_TOKEN)
    config = private_file(
        root,
        "delivery.json",
        json.dumps(
            {
                "enabled": True,
                "source_origin": FakeSource.origin,
                "destination_origin": FakeDestination.origin,
                "source_config_file": str(source_config),
                "destination_token_file": str(destination_token),
                "state_directory": str(state),
                "destination_ref": "owner-primary",
                "poll_seconds": 30,
                "max_sends": 3,
            }
        ),
    )
    monkeypatch.setenv("SOCHRON_ALERT_DELIVERY_CONFIG_FILE", str(config))
    loaded = load_alert_delivery_config()
    assert loaded is not None and loaded.credentials() == (SOURCE_TOKEN, DESTINATION_TOKEN)
    destination_token.write_text(SOURCE_TOKEN)
    destination_token.chmod(0o600)
    with pytest.raises(AlertDeliveryConfigInvalid):
        load_alert_delivery_config()


def test_ac02_cli_is_disabled_without_config(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SOCHRON_ALERT_DELIVERY_CONFIG_FILE", raising=False)
    assert delivery_main(["run", "--once"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "DISABLED",
        "execution_ready": False,
        "auto_trading_enabled": False,
    }


def test_ac03_exact_delivery_duplicate_and_status_projection(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "state")
    source, destination = FakeSource(), FakeDestination()
    with journal(state) as outbox:
        driver = AlertDeliveryDriver(outbox, source, destination, max_sends=3)
        assert driver.step() == "VERIFIED"
        assert driver.step() == "IDLE"
        status = outbox.status()
        assert status.verified == 1 and status.pending is None
        assert destination.store_calls == [status.last_verified_id]
        outbox.publish_status("VERIFIED", heartbeat_seconds=60)
    view = AlertDeliveryStatusReader(state).view(NOW)
    assert view.state == "connected" and view.verified_deliveries == 1
    assert view.last_delivery_ref == destination.store_calls[0]
    assert view.destination_ref == "owner-primary"


def test_ac04_timeout_reconciles_before_retry_and_survives_restart(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "state")
    source, destination = FakeSource(), FakeDestination()
    destination.fail_store = True
    with journal(state) as outbox:
        driver = AlertDeliveryDriver(outbox, source, destination, max_sends=3)
        assert driver.step() == "UNKNOWN"
        pending = outbox.status().pending
        assert pending is not None and pending.attempts == 1
        delivery_id = pending.delivery_id
    destination.fail_store = False
    destination.receipts[delivery_id] = AlertDeliveryReceipt(
        protocol="sochron.alert-delivery-receipt.v1",
        delivery_id=delivery_id,
        destination_ref=destination.destination_ref,
        payload_sha256=pending.digest,
        accepted_at_utc=NOW,
    )
    with journal(state, create=False) as recovered:
        driver = AlertDeliveryDriver(recovered, source, destination, max_sends=3)
        assert driver.step() == "VERIFIED"
        assert destination.store_calls == [delivery_id]


def test_ac04_confirmed_missing_requires_later_resend_and_budget_stops(
    tmp_path: Path,
) -> None:
    state = private_directory(tmp_path, "state")
    source, destination = FakeSource(), FakeDestination()
    destination.fail_store = True
    with journal(state) as outbox:
        driver = AlertDeliveryDriver(outbox, source, destination, max_sends=1)
        assert driver.step() == "UNKNOWN"
        destination.fail_store = False
        destination.missing = True
        assert driver.step() == "PREPARED"
        with pytest.raises(AlertSendBudgetExhausted):
            driver.step()
        assert len(destination.store_calls) == 1


def test_ac04_conflicting_receipt_quarantines_without_resend(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "state")
    source, destination = FakeSource(), FakeDestination()
    destination.fail_store = True
    with journal(state) as outbox:
        driver = AlertDeliveryDriver(outbox, source, destination, max_sends=3)
        assert driver.step() == "UNKNOWN"
        destination.conflict = True
        assert driver.step() == "QUARANTINED"
        assert driver.step() == "QUARANTINED"
        assert outbox.status().quarantined == 1
        assert len(destination.store_calls) == 1


def test_ac03_replacement_and_corruption_fail_closed(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "state")
    outbox = journal(state)
    outbox.close()
    database = state / "alert-delivery.sqlite3"
    replacement = state / "replacement.sqlite3"
    database.rename(replacement)
    database.touch(mode=0o600)
    with pytest.raises(AlertDeliveryJournalUnavailable):
        journal(state, create=False)


def test_ac05_status_missing_stale_and_malformed_are_distinct(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "state")
    reader = AlertDeliveryStatusReader(state)
    assert reader.view(NOW).state == "awaiting_worker"
    with journal(state) as outbox:
        outbox.publish_status("IDLE", heartbeat_seconds=60)
    assert reader.view(NOW).state == "connected"
    assert reader.view(NOW + timedelta(seconds=61)).state == "stale"
    (state / "delivery-status.json").write_text("{}")
    (state / "delivery-status.json").chmod(0o600)
    assert reader.view(NOW).state == "degraded"


@pytest.mark.parametrize("untrusted", ["public", "hardlink", "symlink", "oversized"])
def test_ac05_untrusted_status_fails_closed(tmp_path: Path, untrusted: str) -> None:
    state = private_directory(tmp_path, untrusted)
    with journal(state) as outbox:
        outbox.publish_status("IDLE", heartbeat_seconds=60)
    status = state / "delivery-status.json"
    if untrusted == "public":
        status.chmod(0o644)
    elif untrusted == "hardlink":
        (state / "alias.json").hardlink_to(status)
    elif untrusted == "symlink":
        target = state / "trusted.json"
        status.rename(target)
        status.symlink_to(target)
    else:
        status.write_bytes(b"x" * 8193)
        status.chmod(0o600)
    assert AlertDeliveryStatusReader(state).view(NOW).state == "degraded"


def test_ac05_public_status_directory_stops_api_start(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "public-state")
    state.chmod(0o755)
    with pytest.raises(RuntimeError, match="Invalid private alert delivery"):
        AlertDeliveryStatusReader(state)


def test_ac05_unknown_delivery_is_a_visible_source_health_alert(tmp_path: Path) -> None:
    state = private_directory(tmp_path, "state")
    with journal(state) as outbox:
        intent = outbox.prepare(fact())
        assert intent is not None
        outbox.begin_send(intent.delivery_id)
        outbox.publish_status("UNKNOWN", heartbeat_seconds=60)
    reader = AlertDeliveryStatusReader(state)
    app = create_app(alert_delivery_status=reader)
    inventory = build_operational_alert_inventory(
        telemetry=app.state.telemetry_bridge,
        execution=app.state.execution_bridge,
        journal=None,
        history=None,
        policy=app.state.policy_writer,
        api_budget=app.state.api_budget,
        alert_delivery=reader,
        now=NOW,
    )
    delivery_alert = next(item for item in inventory.alerts if item.source == "alert_delivery")
    assert inventory.status == "degraded" and inventory.delivery_configured is True
    assert inventory.delivery.state == "unknown"
    assert (
        delivery_alert.kind,
        delivery_alert.severity,
        delivery_alert.detail_code,
        delivery_alert.evidence_routes,
    ) == (
        "bridge_disconnected",
        "critical",
        "alert_delivery_unknown",
        ("/api/owner/alerts",),
    )


def test_ac04_bounded_http_source_and_destination() -> None:
    source_payload = {
        "protocol": "sochron.alert-delivery-source.v1",
        "generated_at_utc": NOW.isoformat(),
        "truncated": False,
        "alerts": [fact().model_dump(mode="json")],
    }

    def source_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer " + SOURCE_TOKEN
        return httpx.Response(200, json=source_payload)

    source = HttpAlertSource(
        FakeSource.origin, SOURCE_TOKEN, transport=httpx.MockTransport(source_handler)
    )
    assert source.read().alerts[0].id == fact().id

    notification = fact()
    delivery_id = hashlib.sha256(f"owner-primary\x1f{notification.id}".encode()).hexdigest()[:32]
    from sochron_worker.alert_delivery_journal import AlertNotification, DeliveryIntent

    payload = AlertNotification(
        delivery_id=delivery_id,
        destination_ref="owner-primary",
        alert_id=notification.id,
        condition_id=notification.condition_id,
        kind=notification.kind,
        severity=notification.severity,
        source=notification.source,
        source_ref=notification.source_ref,
        detail_code=notification.detail_code,
        observed_at_utc=notification.observed_at_utc,
        evidence_routes=notification.evidence_routes,
    )
    digest = hashlib.sha256(canonical(payload.model_dump(mode="json")).encode()).hexdigest()
    intent = DeliveryIntent(
        delivery_id, "UNKNOWN", 1, payload, digest, NOW.isoformat(), NOW.isoformat(), None
    )
    calls: list[str] = []

    def destination_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        assert request.headers["authorization"] == "Bearer " + DESTINATION_TOKEN
        assert request.headers["idempotency-key"] == delivery_id
        if request.method == "PUT":
            assert request.content == canonical(payload.model_dump(mode="json")).encode()
            return httpx.Response(204)
        return httpx.Response(
            200,
            json={
                "protocol": "sochron.alert-delivery-receipt.v1",
                "delivery_id": delivery_id,
                "destination_ref": "owner-primary",
                "payload_sha256": digest,
                "accepted_at_utc": NOW.isoformat(),
            },
        )

    destination = HttpAlertDestination(
        FakeDestination.origin,
        "owner-primary",
        DESTINATION_TOKEN,
        transport=httpx.MockTransport(destination_handler),
    )
    destination.store(intent)
    assert destination.read(intent).payload_sha256 == digest
    assert calls == ["PUT", "GET"]


def test_ac04_http_put_conflict_is_not_ambiguous() -> None:
    from sochron_worker.alert_delivery_journal import AlertNotification, DeliveryIntent

    notification = fact()
    delivery_id = hashlib.sha256(f"owner-primary\x1f{notification.id}".encode()).hexdigest()[:32]
    payload = AlertNotification(
        delivery_id=delivery_id,
        destination_ref="owner-primary",
        alert_id=notification.id,
        condition_id=notification.condition_id,
        kind=notification.kind,
        severity=notification.severity,
        source=notification.source,
        source_ref=notification.source_ref,
        detail_code=notification.detail_code,
        observed_at_utc=notification.observed_at_utc,
        evidence_routes=notification.evidence_routes,
    )
    digest = hashlib.sha256(canonical(payload.model_dump(mode="json")).encode()).hexdigest()
    intent = DeliveryIntent(
        delivery_id, "UNKNOWN", 1, payload, digest, NOW.isoformat(), NOW.isoformat(), None
    )
    destination = HttpAlertDestination(
        FakeDestination.origin,
        "owner-primary",
        DESTINATION_TOKEN,
        transport=httpx.MockTransport(lambda _: httpx.Response(409)),
    )
    with pytest.raises(AlertDestinationConflict):
        destination.store(intent)
