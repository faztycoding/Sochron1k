import os
from datetime import timedelta
from decimal import Decimal

import pytest
from sochron1k.journal import BrokerEvidenceConflict, ExposureConflict, Journal, RiskStateConflict
from sochron1k.models import BrokerDeal, BrokerSnapshot, CommandState, RiskState, TradeMode
from sochron1k.preflight import PreflightDenied
from sochron1k.service import ExecutionService, RiskDenied
from sochron1k.simulator import SimulatorAdapter


def test_new_service_cannot_submit_without_startup(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    adapter = SimulatorAdapter()
    journal = Journal(tmp_path / "commands.sqlite3")
    service = ExecutionService(journal, adapter)
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        service.submit(
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=intent,
            risk=risk,
            now=observed_at,
        )
    assert adapter.send_count == 0
    assert journal.counts()["commands"] == 0


def test_baseline_is_not_optional_in_service(
    tmp_path, policy, account, contract, market, intent, risk, observed_at
):
    # A queued/previous command is not evidence of a restored risk baseline.
    journal = Journal(tmp_path / "commands.sqlite3")
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    adapter = SimulatorAdapter()
    service = ExecutionService(journal, adapter)
    with pytest.raises(RiskDenied):
        service.submit(
            policy=policy,
            account=account,
            contract=contract,
            market=market,
            intent=intent,
            risk=risk,
            now=observed_at,
        )
    assert adapter.send_count == 0
    assert journal.risk_state(intent.account_ref, intent.experiment_id) is None


@pytest.fixture
def ready_case(tmp_path, policy, account, contract, market, intent, risk, observed_at):
    journal = Journal(tmp_path / "journal.sqlite3")
    state = RiskState(
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        bangkok_day=observed_at.date(),
        daily_baseline=risk.daily_baseline,
        experiment_baseline=risk.experiment_baseline,
        updated_at=observed_at,
    )
    journal.save_risk_state(state)
    adapter = SimulatorAdapter(account=account, symbol=contract.symbol)
    service = ExecutionService(journal, adapter)
    args = dict(
        policy=policy,
        account=account,
        contract=contract,
        market=market,
        intent=intent,
        risk=risk,
        now=observed_at,
    )
    startup = dict(
        policy=policy, experiment_id=intent.experiment_id, executor_id="simulator", now=observed_at
    )
    return service, args, startup, state


def snapshot(intent):
    return BrokerSnapshot(
        command_id=intent.command_id,
        order_ticket="order-1",
        position_id="position-1",
        requested_volume=Decimal("0.1"),
        filled_volume=Decimal("0.1"),
        remaining_volume=Decimal("0"),
        stop_loss_confirmed=True,
        deals=(
            BrokerDeal(deal_ticket="deal-1", volume=Decimal("0.1"), price=intent.requested_entry),
        ),
    )


@pytest.mark.parametrize(
    "kind",
    [
        "baseline",
        "old-day",
        "future-risk",
        "unavailable",
        "incomplete",
        "real",
        "contest",
        "account",
        "server",
        "currency",
        "margin_mode",
        "symbol",
        "executor",
        "disabled",
        "stale",
        "future",
        "naive",
        "foreign-orders",
        "foreign-positions",
        "foreign-command",
    ],
)
def test_startup_denies_incomplete_identity_risk_or_inventory(ready_case, kind):
    service, args, startup, state = ready_case
    journal, adapter = service.journal, service.adapter
    if kind == "baseline":
        with journal._connect() as db:
            db.execute("DELETE FROM risk_state")
    elif kind == "old-day":
        journal.save_risk_state(
            state.model_copy(update={"bangkok_day": state.bangkok_day - timedelta(days=1)})
        )
    elif kind == "future-risk":
        journal.save_risk_state(
            state.model_copy(update={"updated_at": args["now"] + timedelta(seconds=1)})
        )
    elif kind in {
        "unavailable",
        "incomplete",
        "foreign-orders",
        "foreign-positions",
        "symbol",
        "executor",
    }:
        name, value = {
            "unavailable": ("query_available", False),
            "incomplete": ("complete", False),
            "foreign-orders": ("foreign_orders", 1),
            "foreign-positions": ("foreign_positions", 1),
            "symbol": ("symbol", "OTHER"),
            "executor": ("executor_id", "other"),
        }[kind]
        setattr(adapter, name, value)
    elif kind == "foreign-command":
        adapter._snapshots["unknown"] = snapshot(args["intent"])
    else:
        field, value = {
            "real": ("trade_mode", TradeMode.REAL),
            "contest": ("trade_mode", TradeMode.CONTEST),
            "account": ("account_ref", "other"),
            "server": ("server", "Other-Demo"),
            "currency": ("currency", "USD"),
            "margin_mode": ("margin_mode", "netting"),
            "disabled": ("can_trade", False),
            "stale": ("checked_at", args["now"] - timedelta(seconds=6)),
            "future": ("checked_at", args["now"] + timedelta(seconds=1)),
            "naive": ("checked_at", args["now"].replace(tzinfo=None)),
        }[kind]
        adapter.account = adapter.account.model_copy(update={field: value})
    reasons = {
        "baseline": "RISK_BASELINE_MISSING",
        "old-day": "RISK_DAY_REVIEW_REQUIRED",
        "future-risk": "RISK_STATE_INVALID_TIME",
        "unavailable": "STARTUP_UNAVAILABLE",
        "incomplete": "EXECUTOR_INVENTORY_INCOMPLETE",
        "real": "NON_DEMO_ACCOUNT",
        "contest": "NON_DEMO_ACCOUNT",
        "disabled": "EXECUTOR_TRADING_DISABLED",
        "stale": "EXECUTOR_INVENTORY_STALE",
        "future": "EXECUTOR_INVENTORY_STALE",
        "naive": "EXECUTOR_INVENTORY_STALE",
        "foreign-orders": "FOREIGN_EXPOSURE",
        "foreign-positions": "FOREIGN_EXPOSURE",
        "foreign-command": "FOREIGN_EXPOSURE",
    }
    with pytest.raises(RiskDenied, match=reasons.get(kind, "EXECUTOR_IDENTITY_MISMATCH")):
        service.startup(**startup)
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        service.submit(**args)
    assert adapter.send_count == 0 and journal.counts()["commands"] == 0


@pytest.mark.parametrize("kind", ["missing", "queued", "unprotected", "halted", "exact"])
def test_restart_reconciles_only_matching_evidence_without_resend(ready_case, kind):
    service, args, startup, state = ready_case
    journal, adapter, intent = service.journal, service.adapter, args["intent"]
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    if kind != "queued":
        journal.begin_dispatch(intent.command_id, "attempt-before-restart")
        journal.transition(intent.command_id, CommandState.UNKNOWN)
    if kind not in {"missing", "queued"}:
        adapter._snapshots[intent.command_id] = snapshot(intent).model_copy(
            update={"stop_loss_confirmed": kind != "unprotected"}
        )
    if kind == "halted":
        state = state.model_copy(update={"daily_halt": True, "total_halt": True})
        journal.save_risk_state(state)
    restarted = ExecutionService(Journal(journal.path), adapter)
    if kind in {"missing", "queued", "unprotected"}:
        with pytest.raises(RiskDenied, match=r"STARTUP_UNRESOLVED|STARTUP_UNPROTECTED"):
            restarted.startup(**startup)
    else:
        report = restarted.startup(**startup)
        assert not report["local_entries_admitted"] and not report["execution_ready"]
        assert journal.command(intent.command_id)["state"] == "filled"
    assert adapter.send_count == 0
    assert journal.risk_state(intent.account_ref, intent.experiment_id) == state
    assert journal.counts()["exposure_slots"] == 1
    assert journal.counts()["dispatch_attempts"] == (0 if kind == "queued" else 1)


@pytest.mark.parametrize(
    "kind", ["generation", "baseline", "query", "policy", "equity", "fork", "journal"]
)
def test_each_submit_rechecks_admission_and_failure_closes_it(ready_case, monkeypatch, kind):
    service, args, startup, _ = ready_case
    assert service.startup(**startup)["local_entries_admitted"]
    if kind == "generation":
        service.adapter.generation = "replacement"
    elif kind == "baseline":
        with service.journal._connect() as db:
            db.execute("DELETE FROM risk_state")
    elif kind == "query":
        service.adapter.query_available = False
    elif kind == "policy":
        args["intent"] = args["intent"].model_copy(update={"experiment_id": "other"})
    elif kind == "equity":
        args["risk"] = args["risk"].model_copy(update={"equity": Decimal("200000")})
    elif kind == "fork":
        monkeypatch.setattr(service, "_pid", -1)
    else:
        original = service.journal.path
        original.rename(original.with_suffix(".retained"))
        Journal(original)
    with pytest.raises(RiskDenied):
        service.submit(**args)
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        service.submit(**args)
    assert service.adapter.send_count == 0


def test_recover_and_new_process_instance_do_not_grant_admission(ready_case):
    service, args, startup, _ = ready_case
    service.startup(**startup)
    assert service.recover() == {}
    for candidate in (service, ExecutionService(service.journal, service.adapter)):
        with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
            candidate.submit(**args)


@pytest.mark.parametrize("stage", ["reserve", "begin_dispatch"])
def test_concurrent_halt_is_checked_in_reservation_and_dispatch_transaction(
    ready_case, monkeypatch, stage
):
    service, args, startup, state = ready_case
    service.startup(**startup)
    original = getattr(service.journal, stage)

    def concurrent_halt(*a, **kw):
        service.journal.save_risk_state(state.model_copy(update={"total_halt": True}))
        return original(*a, **kw)

    monkeypatch.setattr(service.journal, stage, concurrent_halt)
    with pytest.raises(RiskStateConflict):
        service.submit(**args)
    assert service.adapter.send_count == 0
    assert service.journal.counts()["commands"] == (0 if stage == "reserve" else 1)
    assert service.journal.counts()["dispatch_attempts"] == 0
    assert service.journal.risk_state(state.account_ref, state.experiment_id).total_halt


def test_single_account_exposure_cannot_be_bypassed_by_new_experiment(ready_case):
    service, args, _, _ = ready_case
    intent = args["intent"]
    service.journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    changed = intent.model_copy(update={"command_id": "other", "experiment_id": "new-exp"})
    with pytest.raises(ExposureConflict):
        service.journal.reserve(changed, Decimal("0.1"), Decimal("100"))


@pytest.mark.parametrize("operation", ["close", "cancel"])
def test_unimplemented_operations_cannot_fall_through_to_open(ready_case, operation):
    service, args, startup, _ = ready_case
    service.startup(**startup)
    args["intent"] = args["intent"].model_copy(update={"operation": operation})
    with pytest.raises(RiskDenied, match="OPERATION_NOT_IMPLEMENTED"):
        service.submit(**args)
    assert service.adapter.send_count == 0


def test_actual_fork_cannot_reuse_parent_admission(ready_case):
    service, args, startup, _ = ready_case
    service.startup(**startup)
    child = os.fork()
    if child == 0:
        try:
            service.submit(**args)
        except RiskDenied as error:
            os._exit(0 if error.reason == "STARTUP_REQUIRED" else 2)
        os._exit(3)
    assert os.waitpid(child, 0)[1] == 0
    assert service.adapter.send_count == 0


@pytest.mark.parametrize(
    "kind",
    [
        "volume",
        "sum",
        "duplicate",
        "deal-change",
        "deal-omit",
        "position",
        "order",
        "terminal",
        "regression",
    ],
)
def test_invalid_broker_evidence_rolls_back_without_overwriting_history(ready_case, kind):
    service, args, _, _ = ready_case
    journal, intent = service.journal, args["intent"]
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(intent.command_id, "attempt")
    original = snapshot(intent)
    journal.apply_broker_snapshot(original)
    changes = {
        "volume": {"requested_volume": Decimal("0.2")},
        "sum": {"remaining_volume": Decimal("0.01")},
        "duplicate": {"deals": original.deals * 2},
        "deal-change": {"deals": (original.deals[0].model_copy(update={"price": Decimal("1")}),)},
        "deal-omit": {
            "deals": (original.deals[0].model_copy(update={"deal_ticket": "replacement"}),)
        },
        "position": {"position_id": "other"},
        "order": {"order_ticket": "other"},
        "terminal": {"terminal_state": CommandState.CLOSED},
        "regression": {
            "filled_volume": Decimal("0"),
            "remaining_volume": Decimal("0.1"),
            "deals": (),
            "stop_loss_confirmed": False,
        },
    }[kind]
    before = journal.counts()
    with pytest.raises(BrokerEvidenceConflict):
        journal.apply_broker_snapshot(original.model_copy(update=changes))
    assert journal.counts() == before
    with journal._connect() as db:
        assert db.execute("SELECT order_ticket,position_id FROM broker_orders").fetchone()[:] == (
            "order-1",
            "position-1",
        )
        assert db.execute("SELECT price FROM broker_deals").fetchone()[0] == str(
            intent.requested_entry
        )


@pytest.mark.parametrize("field", ["daily_baseline", "experiment_baseline"])
def test_baselines_cannot_change_under_existing_admission(ready_case, field):
    service, args, startup, state = ready_case
    service.startup(**startup)
    service.journal.save_risk_state(state.model_copy(update={field: Decimal("200000")}))
    args["risk"] = args["risk"].model_copy(update={field: Decimal("200000")})
    with pytest.raises(RiskDenied, match="RISK_BASELINE_MISMATCH"):
        service.submit(**args)
    assert service.adapter.send_count == 0


@pytest.mark.parametrize("field", ["daily_halt", "total_halt"])
def test_halt_set_after_admission_still_blocks(ready_case, field):
    service, args, startup, state = ready_case
    service.startup(**startup)
    service.journal.save_risk_state(state.model_copy(update={field: True}))
    with pytest.raises(RiskDenied, match=field.upper() + "_ACTIVE"):
        service.submit(**args)
    assert service.adapter.send_count == 0


@pytest.mark.parametrize("field", ["fingerprint", "exposure", "experiment", "risk-during-query"])
def test_startup_detects_journal_relationship_or_concurrent_risk_change(
    ready_case, field, monkeypatch
):
    service, args, startup, state = ready_case
    journal, intent = service.journal, args["intent"]
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(intent.command_id, "attempt")
    service.adapter._snapshots[intent.command_id] = snapshot(intent)
    if field == "risk-during-query":
        original = service.adapter.inventory

        def changed():
            journal.save_risk_state(state.model_copy(update={"total_halt": True}))
            return original()

        monkeypatch.setattr(service.adapter, "inventory", changed)
    else:
        with journal._connect() as db:
            if field == "fingerprint":
                db.execute("UPDATE commands SET fingerprint='changed'")
            elif field == "exposure":
                db.execute("DELETE FROM exposure_slots")
            else:
                db.execute("UPDATE commands SET experiment_id='other'")
    with pytest.raises(
        RiskDenied,
        match=r"JOURNAL_COMMAND_MISMATCH|JOURNAL_EXPOSURE_MISMATCH|STARTUP_STATE_CHANGED",
    ):
        service.startup(**startup)
    assert service.adapter.send_count == 0


@pytest.mark.parametrize("kind", ["duplicate", "deadline", "stale-after-work", "journal-error"])
def test_startup_bounds_and_fail_closed_errors(ready_case, monkeypatch, kind):
    import sqlite3

    import sochron1k.startup as module

    service, args, startup, _ = ready_case
    if kind == "duplicate":
        service.adapter._snapshots["a"] = snapshot(args["intent"])
        service.adapter._snapshots["b"] = snapshot(args["intent"])
        reason = "EXECUTOR_INVENTORY_CONFLICT"
    elif kind in {"deadline", "stale-after-work"}:
        values = iter([0, 6 if kind == "deadline" else 2])
        monkeypatch.setattr(module.time, "monotonic", lambda: next(values))
        if kind == "stale-after-work":
            service.adapter.account = service.adapter.account.model_copy(
                update={"checked_at": args["now"] - timedelta(seconds=4)}
            )
        reason = "STARTUP_TIMEOUT" if kind == "deadline" else "EXECUTOR_INVENTORY_STALE"
    else:

        def fail(*args):
            raise sqlite3.OperationalError("synthetic journal unavailable")

        monkeypatch.setattr(service.journal, "startup_state", fail)
        reason = "STARTUP_UNAVAILABLE"
    with pytest.raises(RiskDenied, match=reason):
        service.startup(**startup)
    assert service.adapter.send_count == 0


@pytest.mark.parametrize("ticket", ["order", "deal"])
def test_broker_tickets_cannot_be_reassigned_to_another_command(ready_case, ticket):
    service, args, _, _ = ready_case
    journal, intent = service.journal, args["intent"]
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(intent.command_id, "first-attempt")
    journal.apply_broker_snapshot(snapshot(intent))
    other = intent.model_copy(
        update={"command_id": "other-command", "account_ref": "other-account"}
    )
    journal.reserve(other, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(other.command_id, "other-attempt")
    candidate = snapshot(other)
    if ticket == "deal":
        candidate = candidate.model_copy(update={"order_ticket": "other-order"})
    before = journal.counts()
    with pytest.raises(BrokerEvidenceConflict):
        journal.apply_broker_snapshot(candidate)
    assert journal.counts() == before
    assert journal.command(other.command_id)["state"] == "sent"


def test_broker_evidence_cannot_manufacture_dispatch_attempt(ready_case):
    service, args, _, _ = ready_case
    journal, intent = service.journal, args["intent"]
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    with pytest.raises(BrokerEvidenceConflict):
        journal.apply_broker_snapshot(snapshot(intent))
    assert journal.command(intent.command_id)["state"] == "queued"
    assert journal.counts()["dispatch_attempts"] == 0


@pytest.mark.parametrize("kind", ["connection", "wrong-command", "invalid-volume"])
def test_ambiguous_dispatch_requires_new_startup_and_never_claims_fill(
    ready_case, monkeypatch, kind
):
    service, args, startup, _ = ready_case
    service.startup(**startup)

    def unconfirmed(intent, volume, attempt):
        if kind == "connection":
            raise ConnectionError("fixture response loss")
        value = snapshot(intent)
        return value.model_copy(
            update=(
                {"command_id": "another-command"}
                if kind == "wrong-command"
                else {"requested_volume": volume + 1}
            )
        )

    monkeypatch.setattr(service.adapter, "send", unconfirmed)
    result = service.submit(**args)
    assert result.state is CommandState.UNKNOWN and not result.protected
    assert service.journal.command(args["intent"].command_id)["state"] == "unknown"
    assert service.journal.counts()["broker_orders"] == 0
    assert service.journal.counts()["exposure_slots"] == 1
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        service.submit(**args)


def test_reconcile_refuses_snapshot_for_another_requested_command(ready_case, monkeypatch):
    service, args, _, _ = ready_case
    intent, journal = args["intent"], service.journal
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(intent.command_id, "attempt-a")
    other = intent.model_copy(update={"command_id": "other", "account_ref": "other-account"})
    journal.reserve(other, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(other.command_id, "attempt-b")
    monkeypatch.setattr(service.adapter, "query", lambda command_id: snapshot(other))
    before = journal.counts()
    with pytest.raises(BrokerEvidenceConflict):
        service.reconcile(intent.command_id)
    assert journal.counts() == before


@pytest.mark.parametrize("kind", ["expiry", "stale"])
def test_slow_journal_cannot_send_after_preflight_expires(ready_case, monkeypatch, kind):
    import sochron1k.service as module

    service, args, startup, _ = ready_case
    service.startup(**startup)
    clock = [0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    if kind == "expiry":
        args["intent"] = args["intent"].model_copy(
            update={"expires_at": args["now"] + timedelta(seconds=1)}
        )
    original = service.journal.begin_dispatch

    def slow(*a, **kw):
        original(*a, **kw)
        clock[0] = 2 if kind == "expiry" else 6

    monkeypatch.setattr(service.journal, "begin_dispatch", slow)
    with pytest.raises(PreflightDenied) as denied:
        service.submit(**args)
    assert denied.value.code == ("EXPIRED_COMMAND" if kind == "expiry" else "STALE_PRICE")
    assert service.adapter.send_count == 0
    assert service.journal.counts()["dispatch_attempts"] == 1
    assert service.journal.counts()["exposure_slots"] == 1
    with pytest.raises(RiskDenied, match="STARTUP_REQUIRED"):
        service.submit(**args)
