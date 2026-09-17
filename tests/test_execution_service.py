from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest
from sochron1k.journal import IdempotencyConflict, Journal
from sochron1k.models import CommandState, RiskState
from sochron1k.service import ExecutionService, RiskDenied
from sochron1k.simulator import SimulatorAdapter, SimulatorBehavior


def submit(service, *, policy, account, contract, market, intent, risk, observed_at):
    # Explicit fixture-only initial experiment provisioning; never a production fallback.
    if service.journal.risk_state(intent.account_ref, intent.experiment_id) is None:
        service.journal.save_risk_state(
            RiskState(
                account_ref=intent.account_ref,
                experiment_id=intent.experiment_id,
                bangkok_day=observed_at.date(),
                daily_baseline=risk.daily_baseline,
                experiment_baseline=risk.experiment_baseline,
                updated_at=observed_at,
            )
        )
    service.adapter.account = account
    service.adapter.symbol = contract.symbol
    service.startup(
        policy=policy, experiment_id=intent.experiment_id, executor_id="simulator", now=observed_at
    )
    return service.submit(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )


def test_ac03_same_request_dispatches_once(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal = Journal(tmp_path / "journal.sqlite3")
    adapter = SimulatorAdapter()
    service = ExecutionService(journal, adapter)
    first = submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    repeated = submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent.model_copy(update={"command_id": "cmd-repeat"}),
        risk=risk,
        observed_at=observed_at,
    )
    assert first.state is CommandState.FILLED
    assert repeated.duplicate
    assert repeated.command_id == intent.command_id
    assert adapter.send_count == 1
    assert journal.counts()["dispatch_attempts"] == 1


def test_ac03_concurrent_duplicate_submissions_dispatch_once(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal = Journal(tmp_path / "journal.sqlite3")
    adapter = SimulatorAdapter()
    service = ExecutionService(journal, adapter)

    def run(command_id: str):
        candidate = intent.model_copy(update={"command_id": command_id})
        return submit(
            service,
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=candidate,
            risk=risk,
            observed_at=observed_at,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, ("cmd-concurrent-a", "cmd-concurrent-b")))

    assert adapter.send_count == 1
    assert journal.counts()["commands"] == 1
    assert sum(result.duplicate for result in results) == 1


def test_ac03_changed_payload_under_same_key_is_conflict(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    service = ExecutionService(Journal(tmp_path / "journal.sqlite3"), SimulatorAdapter())
    submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    changed = intent.model_copy(
        update={"command_id": "cmd-conflict", "take_profit": intent.take_profit + 1}
    )
    with pytest.raises(IdempotencyConflict):
        submit(
            service,
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=changed,
            risk=risk,
            observed_at=observed_at,
        )


def test_ac04_lost_response_becomes_unknown_then_reconciles_without_resend(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal = Journal(tmp_path / "journal.sqlite3")
    adapter = SimulatorAdapter(SimulatorBehavior.ACCEPT_THEN_TIMEOUT)
    service = ExecutionService(journal, adapter)
    submitted = submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    assert submitted.state is CommandState.UNKNOWN
    assert journal.counts()["exposure_slots"] == 1
    reconciled = service.reconcile(intent.command_id)
    assert reconciled.state is CommandState.FILLED
    assert reconciled.protected
    assert adapter.send_count == 1


def test_ac03_journal_failure_prevents_external_send(
    tmp_path, policy, account, contract, market, intent, risk, observed_at, monkeypatch
) -> None:
    journal = Journal(tmp_path / "journal.sqlite3")
    adapter = SimulatorAdapter()
    service = ExecutionService(journal, adapter)

    def fail_reservation(*args, **kwargs):
        del args, kwargs
        raise sqlite3.OperationalError("simulated disk failure")

    monkeypatch.setattr(journal, "reserve", fail_reservation)
    with pytest.raises(sqlite3.OperationalError, match="disk failure"):
        submit(
            service,
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=intent,
            risk=risk,
            observed_at=observed_at,
        )
    assert adapter.send_count == 0


def test_ac05_partial_fill_tracks_identifiers_and_keeps_slot(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal = Journal(tmp_path / "journal.sqlite3")
    service = ExecutionService(journal, SimulatorAdapter(SimulatorBehavior.PARTIAL_FILL))
    result = submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    counts = journal.counts()
    assert result.state is CommandState.PARTIALLY_FILLED
    assert counts["broker_orders"] == 1
    assert counts["broker_deals"] == 1
    assert counts["exposure_slots"] == 1


def test_ac05_duplicate_deal_delivery_is_idempotent(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    journal = Journal(tmp_path / "journal.sqlite3")
    adapter = SimulatorAdapter()
    service = ExecutionService(journal, adapter)
    submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    service.reconcile(intent.command_id)
    assert journal.counts()["broker_deals"] == 1


def test_ac05_rejected_sl_is_never_reported_protected(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    service = ExecutionService(
        Journal(tmp_path / "journal.sqlite3"), SimulatorAdapter(SimulatorBehavior.REJECT_SL)
    )
    result = submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    assert result.state is CommandState.PROTECTION_FAILED
    assert not result.protected
    assert result.reason == "EMERGENCY_CLOSE_REQUIRED"


def test_ac06_restart_recovers_unknown_from_durable_journal(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    path = tmp_path / "journal.sqlite3"
    adapter = SimulatorAdapter(SimulatorBehavior.ACCEPT_THEN_TIMEOUT)
    initial = ExecutionService(Journal(path), adapter)
    result = submit(
        initial,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    assert result.state is CommandState.UNKNOWN

    restarted = ExecutionService(Journal(path), adapter)
    outcomes = restarted.recover()
    assert outcomes == {intent.command_id: CommandState.FILLED}
    assert adapter.send_count == 1


def test_ac06_unreachable_broker_keeps_unknown_after_restart(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    path = tmp_path / "journal.sqlite3"
    adapter = SimulatorAdapter(SimulatorBehavior.ACCEPT_THEN_TIMEOUT)
    service = ExecutionService(Journal(path), adapter)
    submit(
        service,
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        observed_at=observed_at,
    )
    adapter.query_available = False
    outcomes = ExecutionService(Journal(path), adapter).recover()
    assert outcomes[intent.command_id] is CommandState.UNKNOWN
    assert adapter.send_count == 1


def test_ac06_total_halt_persists_and_blocks_after_restart(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
) -> None:
    path = tmp_path / "journal.sqlite3"
    initial = Journal(path)
    initial.save_risk_state(
        RiskState(
            account_ref="demo-account-1",
            experiment_id="exp-pa01-v1",
            bangkok_day=date(2026, 9, 17),
            daily_baseline=Decimal("100000"),
            experiment_baseline=Decimal("100000"),
            daily_halt=True,
            total_halt=True,
            updated_at=observed_at,
        )
    )

    restored = Journal(path).risk_state("demo-account-1", "exp-pa01-v1")
    assert restored is not None
    assert restored.daily_halt
    assert restored.total_halt
    assert restored.experiment_baseline == Decimal("100000")

    adapter = SimulatorAdapter()
    restarted = ExecutionService(Journal(path), adapter)
    with pytest.raises(RiskDenied, match="TOTAL_HALT_ACTIVE"):
        submit(
            restarted,
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=intent,
            risk=risk,
            observed_at=observed_at,
        )
    assert adapter.send_count == 0
