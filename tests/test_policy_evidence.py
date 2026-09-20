from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sochron1k.execution_bridge import (
    ExecutionBridgeSettings,
    ExecutionInventoryFrame,
    ExecutionPollingBridge,
)
from sochron1k.executor import ExecutorInventory
from sochron1k.main import create_app
from sochron1k.models import AccountSnapshot, BrokerSnapshot, TradeMode
from sochron1k.policy_evidence import (
    NewsGateFrame,
    PolicyEvidenceWriter,
    PolicyWriterSettings,
    load_policy_writer_settings,
)
from sochron1k.telemetry import BridgeSettings, DemoIdentity, TelemetryBridge, TelemetryFrame
from sochron_worker.news_gate import CalendarGateway, NewsGateCollector, NewsGateUnavailable
from sochron_worker.news_gate_config import NewsGateConfig
from sochron_worker.pa01_source import PolicyFileSource

D = Decimal
ARCHIVE_ID = UUID("22222222-3333-4444-8555-666666666666")


@dataclass
class Clock:
    utc: datetime = datetime(2026, 9, 20, 0, 0, 0, tzinfo=UTC)
    ticks: float = 100.0

    def now(self) -> datetime:
        return self.utc

    def monotonic(self) -> float:
        return self.ticks

    def advance(self, seconds: float) -> None:
        self.utc += timedelta(seconds=seconds)
        self.ticks += seconds


@pytest.fixture
def identity() -> DemoIdentity:
    return DemoIdentity(
        executor_id="policy-fixture-executor",
        account_ref="123456789",
        server="Synthetic-Demo",
        currency="USD",
        margin_mode="retail_hedging",
        symbol="XAUUSD.fixture",
    )


@pytest.fixture
def private_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    return directory.resolve()


def writer_settings(private_directory: Path, identity: DemoIdentity) -> PolicyWriterSettings:
    return PolicyWriterSettings(
        identity=identity,
        archive_id=ARCHIVE_ID,
        output_file=private_directory / "policy.json",
        news_gate_file=private_directory / "news.json",
    )


def bridge_settings(identity: DemoIdentity) -> BridgeSettings:
    return BridgeSettings(
        identity=identity,
        token=SecretStr(secrets.token_urlsafe(32)),
        broker_utc_offset_seconds=7_200,
    )


def execution_settings(identity: DemoIdentity) -> ExecutionBridgeSettings:
    return ExecutionBridgeSettings(
        identity=identity,
        token=SecretStr(secrets.token_urlsafe(32)),
        magic_number=910001,
    )


def telemetry_frame(
    bridge: TelemetryBridge,
    clock: Clock,
    *,
    protocol: str = "sochron.telemetry.v2",
    sequence: int = 1,
) -> TelemetryFrame:
    values = {
        "protocol": protocol,
        "source": "mt5-ea-sampled",
        "boot_id": bridge.boot_id,
        "sequence": sequence,
        "identity": bridge.settings.identity,
        "trade_mode": "demo",
        "terminal_build": 1,
        "terminal_connected": True,
        "account_trade_allowed": True,
        "observed_at": clock.utc,
        "tick_time_server_msc": int(clock.utc.timestamp() * 1000) + 7_200_000,
        "broker_utc_offset_seconds": 7_200,
        "equity": D("1000.00"),
        "balance": D("1000.00"),
        "free_margin": D("1000.00"),
        "bid": D("2500.00"),
        "ask": D("2500.20"),
        "contract": {
            "symbol": bridge.settings.identity.symbol,
            "digits": 2,
            "tick_size": D("0.01"),
            "volume_min": D("0.01"),
            "volume_max": D("100"),
            "volume_step": D("0.01"),
            "stops_level_points": 10,
            "freeze_level_points": 0,
            "filling_modes": ["fok", "ioc"],
        },
    }
    if protocol == "sochron.telemetry.v2":
        values.update(
            market_open=True,
            market_source="mt5-symbol-trade-session",
        )
    return TelemetryFrame.model_validate(values)


def inventory_frame(
    bridge: ExecutionPollingBridge,
    clock: Clock,
    *,
    snapshots: tuple[BrokerSnapshot, ...] = (),
    sequence: int = 1,
    algo_trading_allowed: bool = True,
) -> ExecutionInventoryFrame:
    account = AccountSnapshot(
        account_ref=bridge.settings.identity.account_ref,
        server=bridge.settings.identity.server,
        currency=bridge.settings.identity.currency,
        margin_mode=bridge.settings.identity.margin_mode,
        trade_mode=TradeMode.DEMO,
        can_trade=True,
        equity=D("1000"),
        checked_at=clock.utc,
    )
    return ExecutionInventoryFrame(
        protocol="sochron.execution.inventory.v1",
        boot_id=bridge.boot_id,
        sequence=sequence,
        identity=bridge.settings.identity,
        trade_mode="demo",
        terminal_build=1,
        terminal_connected=True,
        account_trade_allowed=True,
        algo_trading_allowed=algo_trading_allowed,
        magic_number=bridge.settings.magic_number,
        observed_at=clock.utc,
        inventory=ExecutorInventory(
            executor_id=bridge.settings.identity.executor_id,
            generation="policy-fixture-generation",
            account=account,
            symbol=bridge.settings.identity.symbol,
            observed_at=clock.utc,
            complete=True,
            foreign_orders=0,
            foreign_positions=0,
            snapshots=snapshots,
        ),
    )


def write_news(path: Path, clock: Clock, *, blocked: bool = False) -> None:
    frame = NewsGateFrame(
        protocol="sochron.news-gate.v1",
        source_id="synthetic-calendar",
        revision="fixture-revision-1",
        observed_at_utc=clock.utc,
        coverage_from_utc=clock.utc - timedelta(hours=1),
        coverage_until_utc=clock.utc + timedelta(hours=1),
        complete=True,
        blocked=blocked,
        blocking_event_ids=("event-fixture-1",) if blocked else (),
    )
    path.write_text(json.dumps(frame.model_dump(mode="json"), separators=(",", ":")))
    path.chmod(0o600)


def sources(identity: DemoIdentity, clock: Clock):
    telemetry = TelemetryBridge(
        bridge_settings(identity), utc_now=clock.now, monotonic=clock.monotonic
    )
    execution = ExecutionPollingBridge(
        execution_settings(identity), utc_now=clock.now, monotonic=clock.monotonic
    )
    return telemetry, execution


def test_ac01_disabled_and_private_configuration(monkeypatch, private_directory, identity):
    monkeypatch.delenv("SOCHRON_POLICY_WRITER_CONFIG_FILE", raising=False)
    assert load_policy_writer_settings() is None
    config = private_directory / "writer.json"
    config.write_text('{"enabled":false}')
    config.chmod(0o600)
    monkeypatch.setenv("SOCHRON_POLICY_WRITER_CONFIG_FILE", str(config))
    assert load_policy_writer_settings() is None

    settings = writer_settings(private_directory, identity)
    data = settings.model_dump(mode="json") | {"enabled": True}
    config.write_text(json.dumps(data))
    loaded = load_policy_writer_settings()
    assert loaded == settings

    config.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private policy writer configuration"):
        load_policy_writer_settings()
    config.chmod(0o600)
    alias = private_directory / "writer-link.json"
    alias.symlink_to(config)
    monkeypatch.setenv("SOCHRON_POLICY_WRITER_CONFIG_FILE", str(alias))
    with pytest.raises(RuntimeError, match="Invalid private policy writer configuration"):
        load_policy_writer_settings()


def test_ac02_ac05_writer_requires_v2_then_publishes_worker_compatible_policy(
    private_directory, identity
):
    clock = Clock()
    settings = writer_settings(private_directory, identity)
    writer = PolicyEvidenceWriter(settings, utc_now=clock.now)
    telemetry, execution = sources(identity, clock)
    write_news(settings.news_gate_file, clock)
    telemetry.accept(telemetry_frame(telemetry, clock, protocol="sochron.telemetry.v1"))
    execution.accept_inventory(inventory_frame(execution, clock))
    assert writer.refresh(telemetry, execution) is False
    assert writer.status().state == "awaiting_sources"
    assert writer.status().quote_ready is True
    assert writer.status().market_ready is False
    assert not settings.output_file.exists()

    clock.advance(1)
    telemetry.accept(telemetry_frame(telemetry, clock, sequence=2))
    assert writer.refresh(telemetry, execution) is True
    status = writer.status()
    assert status.state == "ready"
    assert status.output_fresh is True
    assert status.auto_trading_enabled is False
    assert status.execution_ready is False
    policy = PolicyFileSource(settings.output_file).read()
    assert policy.symbol == identity.symbol
    assert policy.feed_id == f"mt5-copyrates:{ARCHIVE_ID}"
    assert policy.spread_price == D("0.20")
    assert policy.market_open is True
    assert policy.price_stale is False
    assert policy.news_blocked is False
    assert policy.has_exposure is False
    assert policy.has_pending is False
    assert policy.ai_enabled is False
    ids = tuple(
        getattr(policy.observations, name).evidence_id
        for name in ("quote", "market", "news", "account")
    )
    assert len(set(ids)) == 4


def test_ac03_derives_exposure_and_pending_from_complete_inventory(private_directory, identity):
    clock = Clock()
    settings = writer_settings(private_directory, identity)
    writer = PolicyEvidenceWriter(settings, utc_now=clock.now)
    telemetry, execution = sources(identity, clock)
    write_news(settings.news_gate_file, clock, blocked=True)
    snapshot = BrokerSnapshot(
        command_id="command-1",
        order_ticket="order-1",
        position_id="position-1",
        requested_volume=D("0.20"),
        filled_volume=D("0.10"),
        remaining_volume=D("0.10"),
        deals=(),
        stop_loss_confirmed=False,
    )
    telemetry.accept(telemetry_frame(telemetry, clock))
    execution.accept_inventory(inventory_frame(execution, clock, snapshots=(snapshot,)))
    assert writer.refresh(telemetry, execution) is True
    policy = PolicyFileSource(settings.output_file).read()
    assert policy.news_blocked is True
    assert policy.has_exposure is True
    assert policy.has_pending is True


def test_scn024_ac05_policy_accepts_read_only_inventory_but_execution_stays_unavailable(
    private_directory, identity
):
    clock = Clock()
    settings = writer_settings(private_directory, identity)
    writer = PolicyEvidenceWriter(settings, utc_now=clock.now)
    telemetry, execution = sources(identity, clock)
    write_news(settings.news_gate_file, clock)
    telemetry.accept(telemetry_frame(telemetry, clock))
    execution.accept_inventory(
        inventory_frame(execution, clock, algo_trading_allowed=False)
    )
    assert execution.status().state == "stale"
    with pytest.raises(ConnectionError, match="inventory is unavailable"):
        execution.inventory()
    assert writer.refresh(telemetry, execution) is True
    policy = PolicyFileSource(settings.output_file).read()
    assert policy.has_exposure is False and policy.has_pending is False
    assert writer.status().execution_ready is False


def test_scn025_ac07_collected_gate_feeds_writer_and_failure_never_clears(
    private_directory, identity
):
    clock = Clock()
    settings = writer_settings(private_directory, identity)
    token = private_directory / "calendar.token"
    token.write_text("n" * 48)
    token.chmod(0o600)
    config = NewsGateConfig(
        origin="https://calendar.example.com",
        credential_file=token,
        output_file=settings.news_gate_file,
        currencies=("USD",),
        impacts=("high",),
        blackout_before_seconds=1_800,
        blackout_after_seconds=1_800,
        poll_seconds=60,
    )
    payload = {
        "protocol": "sochron.calendar-window.v1",
        "source_id": "calendar-fixture",
        "revision": "revision-1",
        "published_at_utc": clock.utc.isoformat(),
        "coverage_from_utc": (clock.utc - timedelta(minutes=30)).isoformat(),
        "coverage_until_utc": (
            clock.utc + timedelta(minutes=30, microseconds=1)
        ).isoformat(),
        "complete": True,
        "events": [
            {
                "event_id": "high-impact-fixture",
                "scheduled_at_utc": clock.utc.isoformat(),
                "currency": "USD",
                "impact": "high",
                "status": "scheduled",
            }
        ],
    }

    def reply(request):
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=httpx.ByteStream(json.dumps(payload).encode()),
        )

    collector = NewsGateCollector(
        config,
        CalendarGateway(config, transport=httpx.MockTransport(reply)),
        utc_now=clock.now,
    )
    assert collector.refresh().blocked is True
    retained = settings.news_gate_file.read_bytes()

    writer = PolicyEvidenceWriter(settings, utc_now=clock.now)
    telemetry, execution = sources(identity, clock)
    telemetry.accept(telemetry_frame(telemetry, clock))
    execution.accept_inventory(inventory_frame(execution, clock))
    assert writer.refresh(telemetry, execution) is True
    assert PolicyFileSource(settings.output_file).read().news_blocked is True

    failed = NewsGateCollector(
        config,
        CalendarGateway(
            config,
            transport=httpx.MockTransport(lambda request: httpx.Response(503)),
        ),
        utc_now=clock.now,
    )
    with pytest.raises(NewsGateUnavailable):
        failed.refresh()
    assert settings.news_gate_file.read_bytes() == retained
    assert writer.refresh(telemetry, execution) is True
    assert PolicyFileSource(settings.output_file).read().news_blocked is True


def test_ac04_missing_stale_or_malformed_news_never_becomes_clear(private_directory, identity):
    clock = Clock()
    settings = writer_settings(private_directory, identity)
    writer = PolicyEvidenceWriter(settings, utc_now=clock.now)
    telemetry, execution = sources(identity, clock)
    telemetry.accept(telemetry_frame(telemetry, clock))
    execution.accept_inventory(inventory_frame(execution, clock))

    assert writer.refresh(telemetry, execution) is False
    assert writer.status().state == "awaiting_sources"
    settings.news_gate_file.write_text("{}")
    settings.news_gate_file.chmod(0o600)
    assert writer.refresh(telemetry, execution) is False
    assert writer.status().state == "degraded"
    assert not settings.output_file.exists()

    old = Clock(clock.utc - timedelta(seconds=301), clock.ticks)
    write_news(settings.news_gate_file, old)
    assert writer.refresh(telemetry, execution) is False
    assert writer.status().state == "awaiting_sources"
    assert not settings.output_file.exists()


def test_ac06_failed_atomic_replace_retains_complete_previous_file(
    monkeypatch, private_directory, identity
):
    clock = Clock()
    settings = writer_settings(private_directory, identity)
    writer = PolicyEvidenceWriter(settings, utc_now=clock.now)
    telemetry, execution = sources(identity, clock)
    write_news(settings.news_gate_file, clock)
    telemetry.accept(telemetry_frame(telemetry, clock))
    execution.accept_inventory(inventory_frame(execution, clock))
    assert writer.refresh(telemetry, execution) is True
    before = settings.output_file.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("synthetic replacement failure")

    monkeypatch.setattr("sochron1k.policy_evidence.os.replace", fail_replace)
    clock.advance(1)
    telemetry.accept(telemetry_frame(telemetry, clock, sequence=2))
    execution.accept_inventory(inventory_frame(execution, clock, sequence=2))
    assert writer.refresh(telemetry, execution) is False
    assert writer.status().state == "degraded"
    assert settings.output_file.read_bytes() == before
    assert not tuple(private_directory.glob(".*.tmp"))
    PolicyFileSource(settings.output_file).read()


def test_ac06_refuses_symlink_output(private_directory, identity):
    settings = writer_settings(private_directory, identity)
    target = private_directory / "target.json"
    target.write_text("{}")
    target.chmod(0o600)
    settings.output_file.symlink_to(target)
    with pytest.raises(RuntimeError, match="Invalid private policy writer configuration"):
        PolicyEvidenceWriter(settings)


@pytest.mark.anyio
async def test_ac07_status_route_is_redacted_and_background_refreshes(private_directory, identity):
    clock = datetime.now(UTC)
    settings = writer_settings(private_directory, identity)
    telemetry_settings = bridge_settings(identity)
    executor_settings = execution_settings(identity)
    write_news(settings.news_gate_file, Clock(clock))
    app = create_app(
        bridge_settings=telemetry_settings,
        execution_bridge_settings=executor_settings,
        policy_writer_settings=settings,
    )
    telemetry = app.state.telemetry_bridge
    execution = app.state.execution_bridge
    telemetry_payload = telemetry_frame(telemetry, Clock(clock)).model_dump(mode="json")
    inventory_payload = inventory_frame(execution, Clock(clock)).model_dump(mode="json")
    telemetry_auth = {"Authorization": "Bearer " + telemetry_settings.token.get_secret_value()}
    execution_auth = {"Authorization": "Bearer " + executor_settings.token.get_secret_value()}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://fixture"
    ) as client:
        disabled = await client.get("/policy/v1/status")
        assert disabled.json()["state"] == "awaiting_sources"
        assert (
            await client.post("/bridge/v1/snapshot", headers=telemetry_auth, json=telemetry_payload)
        ).status_code == 200
        assert (
            await client.post(
                "/executor/v1/inventory", headers=execution_auth, json=inventory_payload
            )
        ).status_code == 200
        response = await client.get("/policy/v1/status")
        connection = await client.get("/ui/connections")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["state"] == "ready"
    assert response.json()["output_fresh"] is True
    signal = next(item for item in connection.json()["connections"] if item["id"] == "signals")
    assert signal["runtime"] == "awaiting_configuration"
    assert signal["current_routes"] == ["/api/policy/v1/status", "/api/owner/signals"]
    for private in (
        identity.executor_id,
        identity.account_ref,
        identity.server,
        identity.symbol,
        str(settings.output_file),
        str(settings.news_gate_file),
        telemetry_settings.token.get_secret_value(),
        executor_settings.token.get_secret_value(),
    ):
        assert private not in response.text


def test_ac01_writer_rejects_mixed_bridge_identity(private_directory, identity):
    other = identity.model_copy(update={"account_ref": "987654321"})
    with pytest.raises(RuntimeError, match="matching telemetry and execution identities"):
        create_app(
            bridge_settings=bridge_settings(identity),
            execution_bridge_settings=execution_settings(other),
            policy_writer_settings=writer_settings(private_directory, identity),
        )
