from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sochron1k.journal import (
    BrokerEvidenceConflict,
    IdempotencyConflict,
    Journal,
    ManagementConflict,
)
from sochron1k.models import (
    BrokerDeal,
    CommandState,
    ManagementIntent,
    ManagementOperation,
    ManagementSnapshot,
    RiskState,
)
from sochron1k.service import ExecutionService, RiskDenied
from sochron1k.simulator import ManagementBehavior, SimulatorAdapter, SimulatorBehavior


def management_intent(
    observed_at: datetime,
    *,
    operation: ManagementOperation,
    command_id: str,
    idempotency_key: str,
    reason: str = "owner_request",
) -> ManagementIntent:
    return ManagementIntent(
        command_id=command_id,
        idempotency_key=idempotency_key,
        account_ref="demo-account-1",
        experiment_id="exp-pa01-v1",
        target_command_id="cmd-00000001",
        symbol="XAUUSD",
        operation=operation,
        reason=reason,
        expires_at=observed_at + timedelta(seconds=30),
    )


def ready_service(
    tmp_path, account, policy, intent, observed_at, *, behavior=SimulatorBehavior.FILL
):
    journal = Journal(tmp_path / "commands.sqlite3")
    state = RiskState(
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        bangkok_day=observed_at.date(),
        daily_baseline=Decimal("100000"),
        experiment_baseline=Decimal("100000"),
        updated_at=observed_at,
    )
    journal.save_risk_state(state)
    adapter = SimulatorAdapter(behavior=behavior, account=account, symbol=intent.symbol)
    service = ExecutionService(journal, adapter)
    service.startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=adapter.executor_id,
        now=observed_at,
    )
    return service, state


def open_trade(service, policy, account, contract, market, intent, risk, observed_at):
    return service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )


def manage(service, policy, account, intent, observed_at):
    return service.manage(policy=policy, account=account, intent=intent, now=observed_at)


def test_close_is_durable_and_final_audit_uses_confirmed_exit(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    opened = open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    assert opened.state is CommandState.FILLED
    service.adapter.close_profit = Decimal("120")
    service.adapter.close_commission = Decimal("-5")
    service.adapter.close_swap = Decimal("-2")
    service.adapter.close_fee = Decimal("-1")
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-close-1",
        idempotency_key="manage-close-idem-1",
        reason="strategy_exit",
    )

    result = manage(service, policy, account, close, observed_at)

    assert result.state is CommandState.CLOSED and result.volume == opened.volume
    assert service.adapter.manage_count == 1
    counts = service.journal.counts()
    assert counts["management_commands"] == counts["management_attempts"] == 1
    assert counts["management_deals"] == 1 and counts["exposure_slots"] == 0
    audit = service.journal.final_trade_audit(intent.command_id)
    assert audit.entry_volume == audit.closed_volume == opened.volume
    assert audit.cancelled_volume == Decimal("0")
    assert audit.gross_profit == Decimal("120")
    assert audit.commission == Decimal("-5")
    assert audit.swap == Decimal("-2") and audit.fee == Decimal("-1")
    assert audit.net_pnl == Decimal("112") and audit.close_reason == "strategy_exit"


def test_partial_entry_must_cancel_remainder_before_close(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(
        tmp_path, account, policy, intent, observed_at, behavior=SimulatorBehavior.PARTIAL_FILL
    )
    opened = open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    assert opened.state is CommandState.PARTIALLY_FILLED
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-close-too-soon",
        idempotency_key="manage-close-too-soon",
    )
    with pytest.raises(RiskDenied, match="PENDING_CANCEL_REQUIRED"):
        manage(service, policy, account, close, observed_at)
    assert service.adapter.manage_count == service.journal.counts()["management_commands"] == 0

    cancel = management_intent(
        observed_at,
        operation=ManagementOperation.CANCEL,
        command_id="manage-cancel-1",
        idempotency_key="manage-cancel-idem-1",
        reason="risk_halt",
    )
    cancelled = manage(service, policy, account, cancel, observed_at)
    assert cancelled.state is CommandState.CANCELLED
    assert service.journal.command(intent.command_id)["state"] == CommandState.FILLED
    assert service.journal.counts()["exposure_slots"] == 1

    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-close-1",
        idempotency_key="manage-close-idem-1",
        reason="risk_halt",
    )
    closed = manage(service, policy, account, close, observed_at)
    assert closed.state is CommandState.CLOSED and closed.volume == opened.volume / 2
    audit = service.journal.final_trade_audit(intent.command_id)
    assert (
        audit.requested_volume,
        audit.entry_volume,
        audit.cancelled_volume,
        audit.closed_volume,
    ) == (
        opened.volume,
        opened.volume / 2,
        opened.volume / 2,
        opened.volume / 2,
    )


def test_management_timeout_after_effect_is_unknown_then_query_only_reconciles(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    service.adapter.management_behavior = ManagementBehavior.ACCEPT_THEN_TIMEOUT
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-close-timeout",
        idempotency_key="manage-close-timeout",
    )

    uncertain = manage(service, policy, account, close, observed_at)
    assert uncertain.state is CommandState.UNKNOWN
    assert service.journal.management_command(close.command_id)["state"] == "unknown"
    assert service.journal.command(intent.command_id)["state"] == "closing"
    assert service.journal.counts()["exposure_slots"] == 1
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        manage(service, policy, account, close, observed_at)

    resolved = service.reconcile_management(close.command_id)
    assert resolved.state is CommandState.CLOSED
    assert service.adapter.manage_count == 1
    assert service.journal.counts()["exposure_slots"] == 0


def test_partial_close_retains_exposure_and_blocks_a_second_management_command(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    opened = open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    service.adapter.management_behavior = ManagementBehavior.PARTIAL_CLOSE
    first = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-partial-close",
        idempotency_key="manage-partial-close",
    )
    result = manage(service, policy, account, first, observed_at)
    assert result.state is CommandState.CLOSING
    assert result.volume == opened.volume
    assert service.journal.counts()["exposure_slots"] == 1

    second = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-second-close",
        idempotency_key="manage-second-close",
    )
    with pytest.raises(ManagementConflict):
        manage(service, policy, account, second, observed_at)


def test_management_idempotency_and_changed_payload_conflict(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-close-once",
        idempotency_key="manage-idempotent",
    )
    first = manage(service, policy, account, close, observed_at)
    duplicate = manage(service, policy, account, close, observed_at)
    assert first.state is duplicate.state is CommandState.CLOSED
    assert duplicate.duplicate and service.adapter.manage_count == 1

    changed = close.model_copy(update={"command_id": "manage-close-changed", "reason": "time_exit"})
    with pytest.raises(IdempotencyConflict):
        manage(service, policy, account, changed, observed_at)
    assert service.adapter.manage_count == 1


@pytest.mark.parametrize(
    ("equity", "daily", "total"),
    [
        (Decimal("99250"), True, False),
        (Decimal("98000"), True, True),
    ],
)
def test_halts_latch_without_blocking_position_management(
    tmp_path,
    policy,
    account,
    contract,
    market,
    intent,
    risk,
    observed_at,
    equity,
    daily,
    total,
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    halted = service.journal.latch_halts(
        intent.account_ref,
        intent.experiment_id,
        equity,
        observed_at + timedelta(seconds=1),
    )
    assert halted.daily_halt is daily and halted.total_halt is total
    updated_account = account.model_copy(
        update={"equity": equity, "checked_at": observed_at + timedelta(seconds=1)}
    )
    service.adapter.account = updated_account

    with pytest.raises(RiskDenied, match="HALT_ACTIVE"):
        service.submit(
            policy=policy,
            account=updated_account,
            contract=contract,
            market=market.model_copy(
                update={
                    "event_time": observed_at + timedelta(milliseconds=950),
                    "received_time": observed_at + timedelta(milliseconds=980),
                }
            ),
            intent=intent.model_copy(
                update={
                    "command_id": "blocked-open",
                    "idempotency_key": "blocked-open",
                    "expires_at": observed_at + timedelta(seconds=31),
                }
            ),
            risk=risk.model_copy(update={"equity": equity}),
            now=observed_at + timedelta(seconds=1),
        )
    service.startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=service.adapter.executor_id,
        now=observed_at + timedelta(seconds=1),
    )

    close = management_intent(
        observed_at + timedelta(seconds=1),
        operation=ManagementOperation.CLOSE,
        command_id="manage-halted-close",
        idempotency_key="manage-halted-close",
        reason="risk_halt",
    )
    assert (
        manage(service, policy, updated_account, close, observed_at + timedelta(seconds=1)).state
        is CommandState.CLOSED
    )
    restored = Journal(service.journal.path).risk_state(intent.account_ref, intent.experiment_id)
    assert restored.daily_halt is daily and restored.total_halt is total


@pytest.mark.parametrize("stage", ["reserve_management", "begin_management_dispatch"])
def test_concurrent_halt_escalation_cannot_strand_risk_reducing_management(
    tmp_path,
    policy,
    account,
    contract,
    market,
    intent,
    risk,
    observed_at,
    monkeypatch,
    stage,
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id=f"manage-concurrent-halt-{stage}",
        idempotency_key=f"manage-concurrent-halt-{stage}",
        reason="risk_halt",
    )
    original = getattr(service.journal, stage)
    latched = False

    def concurrent_halt(*args, **kwargs):
        nonlocal latched
        if not latched:
            latched = True
            service.journal.latch_halts(
                intent.account_ref,
                intent.experiment_id,
                Decimal("98000"),
                observed_at + timedelta(seconds=1),
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(service.journal, stage, concurrent_halt)
    assert manage(service, policy, account, close, observed_at).state is CommandState.CLOSED
    persistent = service.journal.risk_state(intent.account_ref, intent.experiment_id)
    assert persistent.daily_halt and persistent.total_halt


def test_management_evidence_wrong_target_rolls_back(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, state = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-evidence",
        idempotency_key="manage-evidence",
    )
    reservation = service.journal.reserve_management(close, expected_risk=state)
    service.journal.begin_management_dispatch(
        reservation.command_id, "management-attempt", expected_risk=state
    )
    target = service.journal.broker_snapshot(intent.command_id)
    invalid = ManagementSnapshot(
        command_id=close.command_id,
        target_command_id="foreign-target",
        operation=ManagementOperation.CLOSE,
        broker_order_ticket="close-order",
        position_id=target.position_id,
        requested_volume=target.open_position_volume,
        completed_volume=target.open_position_volume,
        remaining_volume=Decimal("0"),
        deals=(),
        terminal_state=CommandState.CLOSED,
        target=target.model_copy(
            update={
                "closed_volume": target.filled_volume,
                "stop_loss_confirmed": False,
                "terminal_state": CommandState.CLOSED,
            }
        ),
        observed_at=observed_at,
    )
    before = service.journal.counts()
    with pytest.raises(BrokerEvidenceConflict):
        service.journal.apply_management_snapshot(invalid)
    assert service.journal.counts() == before
    assert service.journal.counts()["exposure_slots"] == 1


def test_restart_requires_active_management_inventory_then_reconciles(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    service.adapter.management_behavior = ManagementBehavior.PARTIAL_CLOSE
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-restart",
        idempotency_key="manage-restart",
    )
    assert manage(service, policy, account, close, observed_at).state is CommandState.CLOSING

    snapshot = service.adapter._management_snapshots.pop(close.command_id)
    restarted = ExecutionService(Journal(service.journal.path), service.adapter)
    with pytest.raises(RiskDenied, match="STARTUP_UNRESOLVED"):
        restarted.startup(
            policy=policy,
            experiment_id=intent.experiment_id,
            executor_id=service.adapter.executor_id,
            now=observed_at,
        )
    service.adapter._management_snapshots[close.command_id] = snapshot
    admitted = restarted.startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=service.adapter.executor_id,
        now=observed_at,
    )
    assert not admitted["local_entries_admitted"]
    assert restarted.journal.management_command(close.command_id)["state"] == "closing"


def test_cancel_without_pending_and_close_without_position_are_denied_before_journal(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    cancel = management_intent(
        observed_at,
        operation=ManagementOperation.CANCEL,
        command_id="manage-no-pending",
        idempotency_key="manage-no-pending",
    )
    with pytest.raises(RiskDenied, match="NO_PENDING_ORDER"):
        manage(service, policy, account, cancel, observed_at)
    assert service.journal.counts()["management_commands"] == service.adapter.manage_count == 0

    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-close",
        idempotency_key="manage-close",
    )
    assert manage(service, policy, account, close, observed_at).state is CommandState.CLOSED
    another = close.model_copy(
        update={"command_id": "manage-no-position", "idempotency_key": "manage-no-position"}
    )
    with pytest.raises(RiskDenied, match="NO_OPEN_POSITION"):
        manage(service, policy, account, another, observed_at)


def test_final_audit_rejects_unknown_or_partial_state(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    with pytest.raises(ManagementConflict, match="FINAL_AUDIT_NOT_READY"):
        service.journal.final_trade_audit(intent.command_id)


def test_management_observation_time_cannot_regress(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-observation-time",
        idempotency_key="manage-observation-time",
    )
    assert manage(service, policy, account, close, observed_at).state is CommandState.CLOSED
    snapshot = service.adapter.query_management(close.command_id)
    regressed = snapshot.model_copy(update={"observed_at": observed_at - timedelta(seconds=1)})
    before = service.journal.counts()
    with pytest.raises(BrokerEvidenceConflict):
        service.journal.apply_management_snapshot(regressed)
    assert service.journal.counts() == before


def test_unordered_cumulative_entry_deals_do_not_block_close(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, _ = ready_service(
        tmp_path, account, policy, intent, observed_at, behavior=SimulatorBehavior.PARTIAL_FILL
    )
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    current = service.adapter._snapshots[intent.command_id]
    second = BrokerDeal(
        deal_ticket="aaa-later-arrival",
        volume=current.remaining_volume,
        price=intent.requested_entry,
    )
    cumulative = current.model_copy(
        update={
            "filled_volume": current.requested_volume,
            "remaining_volume": Decimal("0"),
            "deals": (*current.deals, second),
        }
    )
    service.adapter._snapshots[intent.command_id] = cumulative
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id="manage-unordered-entry-deals",
        idempotency_key="manage-unordered-entry-deals",
    )

    assert manage(service, policy, account, close, observed_at).state is CommandState.CLOSED
    assert service.journal.final_trade_audit(intent.command_id).closed_volume == (
        current.requested_volume
    )


@pytest.mark.parametrize("kind", ["malformed", "wrong_target", "journal_failure"])
def test_any_unconfirmed_management_response_is_durable_unknown(
    tmp_path,
    policy,
    account,
    contract,
    market,
    intent,
    risk,
    observed_at,
    monkeypatch,
    kind,
):
    service, _ = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)
    close = management_intent(
        observed_at,
        operation=ManagementOperation.CLOSE,
        command_id=f"manage-unconfirmed-{kind}",
        idempotency_key=f"manage-unconfirmed-{kind}",
    )
    original_manage = service.adapter.manage
    original_apply = service.journal.apply_management_snapshot

    if kind == "malformed":
        monkeypatch.setattr(service.adapter, "manage", lambda *args: None)
    elif kind == "wrong_target":

        def wrong_target(*args):
            snapshot = original_manage(*args)
            return snapshot.model_copy(update={"target_command_id": "foreign-target"})

        monkeypatch.setattr(service.adapter, "manage", wrong_target)
    else:

        def failed_journal(snapshot):
            raise OSError("synthetic durable-write failure")

        monkeypatch.setattr(service.journal, "apply_management_snapshot", failed_journal)

    result = manage(service, policy, account, close, observed_at)
    assert result.state is CommandState.UNKNOWN
    assert service.journal.management_command(close.command_id)["state"] == "unknown"
    assert service.journal.counts()["exposure_slots"] == 1
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        manage(service, policy, account, close, observed_at)

    if kind == "journal_failure":
        monkeypatch.setattr(service.journal, "apply_management_snapshot", original_apply)
        assert service.reconcile_management(close.command_id).state is CommandState.CLOSED


def test_concurrent_management_reservations_leave_one_active_command(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    service, state = ready_service(tmp_path, account, policy, intent, observed_at)
    open_trade(service, policy, account, contract, market, intent, risk, observed_at)

    def reserve(sequence):
        journal = Journal(service.journal.path)
        candidate = management_intent(
            observed_at,
            operation=ManagementOperation.CLOSE,
            command_id=f"concurrent-close-{sequence}",
            idempotency_key=f"concurrent-close-{sequence}",
        )
        try:
            return journal.reserve_management(candidate, expected_risk=state)
        except ManagementConflict as error:
            return error.reason

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, (1, 2)))

    assert sum(not isinstance(result, str) for result in results) == 1
    assert "MANAGEMENT_CONFLICT" in results
    assert service.journal.counts()["management_commands"] == 1
