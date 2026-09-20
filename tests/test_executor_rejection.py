from __future__ import annotations

from datetime import UTC, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sochron1k.executor import ExecutorRejected
from sochron1k.journal import BrokerEvidenceConflict, Journal
from sochron1k.models import (
    CommandState,
    ExecutorRejection,
    ManagementIntent,
    ManagementOperation,
    RiskState,
)
from sochron1k.service import ExecutionService
from sochron1k.simulator import ManagementBehavior, SimulatorAdapter, SimulatorBehavior


def rejection(command_id, observed_at, *, operation="open", target_command_id=None, retcode=10006):
    return ExecutorRejection(
        command_id=command_id,
        target_command_id=target_command_id,
        operation=operation,
        retcode=retcode,
        retcode_external=0,
        request_id=7,
        observed_at=observed_at,
    )


def provision(journal, intent, risk, observed_at):
    journal.save_risk_state(
        RiskState(
            account_ref=intent.account_ref,
            experiment_id=intent.experiment_id,
            bangkok_day=observed_at.date(),
            daily_baseline=risk.daily_baseline,
            experiment_baseline=risk.experiment_baseline,
            updated_at=observed_at,
        )
    )


def start(service, policy, account, intent, observed_at):
    service.adapter.account = account
    service.adapter.symbol = intent.symbol
    service.startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=service.adapter.executor_id,
        now=observed_at,
    )


def test_confirmed_entry_rejection_uses_no_fake_broker_identifier(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    journal = Journal(tmp_path / "journal.sqlite3")
    provision(journal, intent, risk, observed_at)
    adapter = SimulatorAdapter(SimulatorBehavior.REJECT)
    service = ExecutionService(journal, adapter)
    start(service, policy, account, intent, observed_at)

    result = service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )

    assert result.state is CommandState.REJECTED
    assert result.reason == "BROKER_REJECTED"
    assert journal.counts()["executor_rejections"] == 1
    assert journal.counts()["broker_orders"] == 0
    assert journal.counts()["exposure_slots"] == 0
    assert service.reconcile(intent.command_id).state is CommandState.REJECTED


def test_confirmed_close_rejection_restores_parent_and_retains_exposure(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    journal = Journal(tmp_path / "journal.sqlite3")
    provision(journal, intent, risk, observed_at)
    adapter = SimulatorAdapter(account=account, symbol=intent.symbol)
    service = ExecutionService(journal, adapter)
    start(service, policy, account, intent, observed_at)
    opened = service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )
    assert opened.state is CommandState.FILLED
    adapter.management_behavior = ManagementBehavior.REJECT
    close = ManagementIntent(
        command_id="manage-rejected-close",
        idempotency_key="manage-rejected-close",
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        target_command_id=intent.command_id,
        symbol=intent.symbol,
        operation=ManagementOperation.CLOSE,
        reason="owner_request",
        expires_at=observed_at + timedelta(seconds=30),
    )

    result = service.manage(policy=policy, account=account, intent=close, now=observed_at)

    assert result.state is CommandState.REJECTED
    assert result.reason == "BROKER_REJECTED"
    assert journal.command(intent.command_id)["state"] == CommandState.FILLED.value
    assert journal.counts()["exposure_slots"] == 1
    assert journal.counts()["management_outcomes"] == 0
    assert service.reconcile_management(close.command_id).state is CommandState.REJECTED


@pytest.mark.parametrize(
    "retcode",
    [10008, 10009, 10010, 10012, 10023, 10025, 10028, 10031, 10036, 10038, 10039, 10041],
)
def test_ambiguous_or_effectful_retcode_cannot_be_confirmed_rejection(observed_at, retcode):
    with pytest.raises(ValidationError):
        rejection("cmd", observed_at, retcode=retcode)


def test_rejection_binding_and_evidence_are_immutable(tmp_path, intent, risk, observed_at):
    journal = Journal(tmp_path / "journal.sqlite3")
    provision(journal, intent, risk, observed_at)
    journal.reserve(intent, Decimal("0.10"), Decimal("100"))
    journal.begin_dispatch(intent.command_id, "attempt-1", Decimal("1000"), Decimal("0"))
    evidence = rejection(intent.command_id, observed_at)
    assert journal.apply_executor_rejection(evidence) is CommandState.REJECTED
    assert journal.apply_executor_rejection(evidence) is CommandState.REJECTED
    with pytest.raises(BrokerEvidenceConflict):
        journal.apply_executor_rejection(evidence.model_copy(update={"request_id": 8}))


def test_executor_rejected_exception_retains_typed_evidence(observed_at):
    evidence = rejection("cmd", observed_at)
    error = ExecutorRejected(evidence)
    assert error.evidence == evidence


def test_rejection_event_time_is_preserved_in_utc(observed_at):
    bangkok = observed_at.astimezone(timezone(timedelta(hours=7)))
    evidence = rejection("cmd", bangkok)
    assert evidence.observed_at == observed_at
    assert evidence.observed_at.tzinfo is UTC


def test_mismatched_rejection_after_dispatch_becomes_unknown(
    tmp_path, monkeypatch, policy, account, contract, market, intent, risk, observed_at
):
    journal = Journal(tmp_path / "mismatched-rejection.sqlite3")
    provision(journal, intent, risk, observed_at)
    adapter = SimulatorAdapter(account=account, symbol=intent.symbol)
    service = ExecutionService(journal, adapter)
    start(service, policy, account, intent, observed_at)

    def reject_wrong_command(*_args):
        raise ExecutorRejected(rejection("another-command", observed_at))

    monkeypatch.setattr(adapter, "send", reject_wrong_command)
    result = service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )

    assert result.state is CommandState.UNKNOWN
    assert result.reason == "RECONCILIATION_REQUIRED"
    assert journal.counts()["executor_rejections"] == 0
    assert journal.counts()["exposure_slots"] == 1


def test_stale_immediate_rejection_after_dispatch_becomes_unknown(
    tmp_path, monkeypatch, policy, account, contract, market, intent, risk, observed_at
):
    journal = Journal(tmp_path / "stale-rejection.sqlite3")
    provision(journal, intent, risk, observed_at)
    adapter = SimulatorAdapter(account=account, symbol=intent.symbol)
    service = ExecutionService(journal, adapter)
    start(service, policy, account, intent, observed_at)

    def reject_stale(*_args):
        raise ExecutorRejected(rejection(intent.command_id, observed_at - timedelta(minutes=1)))

    monkeypatch.setattr(adapter, "send", reject_stale)
    result = service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )

    assert result.state is CommandState.UNKNOWN
    assert result.reason == "RECONCILIATION_REQUIRED"
    assert journal.counts()["executor_rejections"] == 0
    assert journal.counts()["exposure_slots"] == 1


def test_startup_inventory_can_resolve_unknown_to_confirmed_rejection(
    tmp_path, policy, account, intent, risk, observed_at
):
    journal = Journal(tmp_path / "startup-rejection.sqlite3")
    provision(journal, intent, risk, observed_at)
    journal.reserve(intent, Decimal("0.10"), Decimal("100"))
    journal.begin_dispatch(
        intent.command_id, "attempt-startup", Decimal("1000"), Decimal("0")
    )
    journal.transition(intent.command_id, CommandState.UNKNOWN)
    adapter = SimulatorAdapter(account=account, symbol=intent.symbol)
    adapter._rejections[intent.command_id] = rejection(
        intent.command_id, observed_at - timedelta(hours=1)
    )

    outcome = ExecutionService(journal, adapter).startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=adapter.executor_id,
        now=observed_at,
    )

    assert outcome["state"] == "RECONCILED"
    assert outcome["local_entries_admitted"] is True
    assert journal.command(intent.command_id)["state"] == "rejected"
    assert journal.counts()["exposure_slots"] == 0


def test_startup_inventory_resolves_rejected_close_without_releasing_parent(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    journal = Journal(tmp_path / "startup-close-rejection.sqlite3")
    provision(journal, intent, risk, observed_at)
    adapter = SimulatorAdapter(account=account, symbol=intent.symbol)
    service = ExecutionService(journal, adapter)
    start(service, policy, account, intent, observed_at)
    assert (
        service.submit(
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=intent,
            risk=risk,
            now=observed_at,
        ).state
        is CommandState.FILLED
    )
    close = ManagementIntent(
        command_id="manage-startup-rejected-close",
        idempotency_key="manage-startup-rejected-close",
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        target_command_id=intent.command_id,
        symbol=intent.symbol,
        operation=ManagementOperation.CLOSE,
        reason="owner_request",
        expires_at=observed_at + timedelta(seconds=30),
    )
    state = journal.risk_state(intent.account_ref, intent.experiment_id)
    journal.reserve_management(close, expected_risk=state)
    journal.begin_management_dispatch(
        close.command_id, "attempt-close-startup", expected_risk=state
    )
    journal.transition_management(close.command_id, CommandState.UNKNOWN)
    adapter._rejections[close.command_id] = rejection(
        close.command_id,
        observed_at,
        operation="close",
        target_command_id=intent.command_id,
    )

    outcome = ExecutionService(journal, adapter).startup(
        policy=policy,
        experiment_id=intent.experiment_id,
        executor_id=adapter.executor_id,
        now=observed_at,
    )

    assert outcome["state"] == "RECONCILED"
    assert outcome["local_entries_admitted"] is False
    assert journal.management_command(close.command_id)["state"] == "rejected"
    assert journal.command(intent.command_id)["state"] == "filled"
    assert journal.counts()["exposure_slots"] == 1
