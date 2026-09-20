from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr, ValidationError
from sochron1k.demo_readiness import DemoOwnerDecisions
from sochron1k.demo_round_trip import (
    DemoRoundTripController,
    DemoRoundTripDenied,
    DemoRoundTripManagementRequest,
    DemoRoundTripOpenRequest,
    DemoRoundTripSettings,
    load_demo_round_trip_settings,
)
from sochron1k.execution_bridge import ExecutionBridgeSettings
from sochron1k.journal import RiskStateConflict
from sochron1k.main import create_app
from sochron1k.models import (
    AccountSnapshot,
    CommandState,
    ManagementIntent,
    ManagementOperation,
    RiskState,
    TradeMode,
)
from sochron1k.simulator import SimulatorAdapter, SimulatorBehavior
from sochron1k.telemetry import DemoIdentity

NOW = datetime(2026, 9, 20, 2, 0, tzinfo=UTC)
TOKEN = "r" * 43
IDENTITY = DemoIdentity(
    executor_id="simulator",
    account_ref="demo-account-1",
    server="Demo-Server",
    currency="THB",
    margin_mode="retail_hedging",
    symbol="XAUUSD",
)


def account(at: datetime = NOW, *, equity: str = "100000") -> AccountSnapshot:
    return AccountSnapshot(
        account_ref=IDENTITY.account_ref,
        server=IDENTITY.server,
        currency=IDENTITY.currency,
        margin_mode=IDENTITY.margin_mode,
        trade_mode=TradeMode.DEMO,
        can_trade=True,
        equity=Decimal(equity),
        checked_at=at,
    )


def settings(tmp_path: Path, **updates) -> DemoRoundTripSettings:
    values = dict(
        protocol="sochron.demo-round-trip-config.v1",
        identity=IDENTITY,
        token=SecretStr(TOKEN),
        journal_file=(tmp_path / "round-trip.sqlite3").resolve(),
        source_revision="a" * 40,
        decision_revision="owner-demo-v1",
        experiment_id="exp-pa01-v1",
        signal_id="sig-00000001",
        strategy_version="PA01-v1",
        entry_command_id="round-trip-entry-1",
        cancel_command_id="round-trip-cancel-1",
        close_command_id="round-trip-close-1",
        experiment_baseline=Decimal("100000"),
        minimum_costs_per_lot=Decimal("1"),
        authorized_at_utc=NOW - timedelta(minutes=1),
        entry_authorization_expires_at_utc=NOW + timedelta(minutes=5),
    )
    values.update(updates)
    return DemoRoundTripSettings(**values)


def open_request(base_intent, contract, market, risk, *, at: datetime = NOW):
    request_account = account(at)
    return DemoRoundTripOpenRequest(
        protocol="sochron.demo-round-trip-open.v1",
        account=request_account,
        contract=contract,
        market=market.model_copy(
            update={
                "event_time": at - timedelta(milliseconds=50),
                "received_time": at - timedelta(milliseconds=20),
            }
        ),
        intent=base_intent.model_copy(
            update={
                "command_id": "round-trip-entry-1",
                "account_ref": IDENTITY.account_ref,
                "experiment_id": "exp-pa01-v1",
                "signal_id": "sig-00000001",
                "strategy_version": "PA01-v1",
                "symbol": IDENTITY.symbol,
                "expires_at": at + timedelta(seconds=30),
            }
        ),
        risk=risk.model_copy(
            update={
                "equity": request_account.equity,
                "daily_baseline": Decimal("100000"),
                "experiment_baseline": Decimal("100000"),
                "costs_per_lot": Decimal("1"),
            }
        ),
    )


def management_request(
    operation: ManagementOperation,
    *,
    at: datetime,
    request_account: AccountSnapshot,
) -> DemoRoundTripManagementRequest:
    command_id = (
        "round-trip-cancel-1"
        if operation is ManagementOperation.CANCEL
        else "round-trip-close-1"
    )
    return DemoRoundTripManagementRequest(
        protocol="sochron.demo-round-trip-management.v1",
        account=request_account,
        intent=ManagementIntent(
            command_id=command_id,
            idempotency_key=command_id,
            account_ref=IDENTITY.account_ref,
            experiment_id="exp-pa01-v1",
            target_command_id="round-trip-entry-1",
            symbol=IDENTITY.symbol,
            operation=operation,
            reason="bounded_demo_round_trip",
            expires_at=at + timedelta(seconds=30),
        ),
    )


def controller(
    tmp_path: Path,
    *,
    now: list[datetime],
    behavior: SimulatorBehavior = SimulatorBehavior.FILL,
) -> tuple[DemoRoundTripController, SimulatorAdapter]:
    adapter = SimulatorAdapter(
        behavior=behavior,
        account=account(now[0]),
        symbol=IDENTITY.symbol,
    )
    return (
        DemoRoundTripController(settings(tmp_path), adapter, utc_now=lambda: now[0]),
        adapter,
    )


def test_private_settings_are_strict_bounded_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    configured = settings(private)
    path = private / "round-trip.json"
    serialized = configured.model_dump(mode="json")
    serialized["token"] = TOKEN
    path.write_text(json.dumps(serialized), encoding="utf-8")
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_DEMO_ROUND_TRIP_CONFIG_FILE", str(path.resolve()))
    assert load_demo_round_trip_settings() == configured

    path.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private Demo round-trip configuration"):
        load_demo_round_trip_settings()
    with pytest.raises(ValidationError):
        settings(
            private,
            entry_authorization_expires_at_utc=NOW + timedelta(hours=25),
        )
    with pytest.raises(ValidationError):
        settings(private, close_command_id="round-trip-entry-1")


def test_create_only_baseline_startup_and_exact_duplicate_entry(
    tmp_path: Path, contract, market, intent, risk
) -> None:
    now = [NOW]
    target, adapter = controller(tmp_path, now=now)
    assert target.status().state == "awaiting_baseline"

    baseline = target.initialize_risk_baseline()
    assert baseline.created and not baseline.daily_halt and not baseline.total_halt
    assert target.initialize_risk_baseline().created is False
    assert target.status().state == "awaiting_startup"
    assert target.startup().local_entries_admitted
    assert target.status().state == "armed"

    request = open_request(intent, contract, market, risk)
    opened = target.open(request)
    assert opened.state is CommandState.FILLED and opened.protected
    assert adapter.send_count == 1
    duplicate = target.open(request)
    assert duplicate.duplicate and duplicate.command_id == request.intent.command_id
    assert adapter.send_count == 1
    assert target.status().state == "entry_recorded"

    changed = request.model_copy(
        update={
            "intent": request.intent.model_copy(update={"signal_id": "foreign-signal"})
        }
    )
    with pytest.raises(DemoRoundTripDenied, match="ENTRY_AUTHORIZATION_MISMATCH"):
        target.open(changed)
    assert adapter.send_count == 1


def test_expired_entry_denied_but_halted_cancel_and_close_remain_available(
    tmp_path: Path, contract, market, intent, risk
) -> None:
    now = [NOW]
    target, adapter = controller(tmp_path, now=now, behavior=SimulatorBehavior.PARTIAL_FILL)
    target.initialize_risk_baseline()
    target.startup()
    opened = target.open(open_request(intent, contract, market, risk))
    assert opened.state is CommandState.PARTIALLY_FILLED

    later = NOW + timedelta(minutes=10)
    now[0] = later
    adapter.account = account(later, equity="99000")
    halted = target.journal.latch_halts(
        IDENTITY.account_ref,
        target.settings.experiment_id,
        adapter.account.equity,
        later,
    )
    assert halted.daily_halt and not halted.total_halt
    target.startup()
    expired = open_request(intent, contract, market, risk, at=later).model_copy(
        update={
            "intent": open_request(intent, contract, market, risk, at=later).intent.model_copy(
                update={"command_id": "round-trip-entry-1"}
            )
        }
    )
    with pytest.raises(DemoRoundTripDenied, match="ENTRY_AUTHORIZATION_EXPIRED"):
        target.open(expired)

    cancel = target.manage(
        management_request(
            ManagementOperation.CANCEL,
            at=later,
            request_account=adapter.account,
        ),
        ManagementOperation.CANCEL,
    )
    assert cancel.state is CommandState.CANCELLED
    close = target.manage(
        management_request(
            ManagementOperation.CLOSE,
            at=later,
            request_account=adapter.account,
        ),
        ManagementOperation.CLOSE,
    )
    assert close.state is CommandState.CLOSED
    assert adapter.send_count == 1 and adapter.manage_count == 2
    persistent = target.journal.risk_state(IDENTITY.account_ref, target.settings.experiment_id)
    assert persistent is not None and persistent.daily_halt
    assert target.status().state == "complete"


def test_ambiguous_entry_is_unknown_then_query_only_reconciles_without_resend(
    tmp_path: Path, contract, market, intent, risk
) -> None:
    now = [NOW]
    target, adapter = controller(
        tmp_path,
        now=now,
        behavior=SimulatorBehavior.ACCEPT_THEN_TIMEOUT,
    )
    target.initialize_risk_baseline()
    target.startup()
    request = open_request(intent, contract, market, risk)
    result = target.open(request)
    assert result.state is CommandState.UNKNOWN
    assert adapter.send_count == 1
    reconciled = target.reconcile(request.intent.command_id)
    assert reconciled.state is CommandState.FILLED and reconciled.protected
    assert adapter.send_count == 1
    with pytest.raises(DemoRoundTripDenied, match="COMMAND_NOT_AUTHORIZED"):
        target.reconcile("foreign-command")


def owner_decisions() -> DemoOwnerDecisions:
    return DemoOwnerDecisions(
        protocol="sochron.demo-owner-decisions.v1",
        decision_revision="owner-demo-v1",
        recorded_at_utc=NOW - timedelta(hours=1),
        owner_approved=True,
        broker_name="Fixture Broker",
        demo_server=IDENTITY.server,
        account_currency=IDENTITY.currency,
        starting_capital=Decimal("100000"),
        symbol=IDENTITY.symbol,
        account_mode="retail_hedging",
        trading_hours_policy_ref="fixture-hours-v1",
        overnight_policy="flat",
        target_executor="hostinger_wine",
        target_region="fixture-region",
        monthly_budget_thb=Decimal("1000"),
        alert_destination_ref="fixture-alert",
        halt_release_authority_ref="fixture-owner",
        approved_secret_channel_ref="fixture-private-channel",
        rpo_seconds=300,
        rto_seconds=1800,
        magic_number=910001,
    )


@pytest.mark.anyio
async def test_internal_api_is_separately_authenticated_and_redacted(tmp_path: Path) -> None:
    configured = settings(tmp_path)
    execution = ExecutionBridgeSettings(
        identity=IDENTITY,
        token=SecretStr("e" * 43),
        magic_number=910001,
    )
    with pytest.raises(RuntimeError, match="exact runtime source revision"):
        create_app(
            execution_bridge_settings=execution,
            demo_owner_decisions=owner_decisions(),
            demo_round_trip_settings=configured,
        )
    app = create_app(
        execution_bridge_settings=execution,
        demo_owner_decisions=owner_decisions(),
        demo_round_trip_settings=configured,
        runtime_source_revision="a" * 40,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status = await client.get("/internal/v1/demo-round-trip/status")
        denied = await client.post("/internal/v1/demo-round-trip/risk-baseline")
        unavailable = await client.post(
            "/internal/v1/demo-round-trip/risk-baseline",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert status.status_code == 200
    assert status.json()["state"] == "awaiting_baseline"
    assert status.json()["auto_trading_enabled"] is False
    assert denied.status_code == 401
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "EXECUTOR_INVENTORY_UNAVAILABLE"}

    with pytest.raises(RuntimeError, match="separate service credential"):
        create_app(
            execution_bridge_settings=execution,
            demo_owner_decisions=owner_decisions(),
            demo_round_trip_settings=configured.model_copy(
                update={"token": execution.token}
            ),
            runtime_source_revision="a" * 40,
        )


def test_initialize_risk_state_never_overwrites_or_clears_halt(tmp_path: Path) -> None:
    now = [NOW]
    target, _ = controller(tmp_path, now=now)
    target.initialize_risk_baseline()
    state = target.journal.risk_state(IDENTITY.account_ref, target.settings.experiment_id)
    assert state is not None
    target.journal.save_risk_state(state.model_copy(update={"daily_halt": True}))
    with pytest.raises(RiskStateConflict):
        target.journal.initialize_risk_state(
            RiskState(
                account_ref=state.account_ref,
                experiment_id=state.experiment_id,
                bangkok_day=state.bangkok_day,
                daily_baseline=Decimal("200000"),
                experiment_baseline=state.experiment_baseline,
                updated_at=state.updated_at,
            )
        )
    assert target.journal.risk_state(state.account_ref, state.experiment_id).daily_halt
