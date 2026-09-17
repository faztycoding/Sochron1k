"""Installed-package startup oracle using only generated local fixture inputs."""

import json
import sys
from datetime import datetime
from pathlib import Path

from sochron1k.journal import Journal
from sochron1k.models import (
    AccountSnapshot,
    CommandIntent,
    CommandState,
    ContractSpec,
    MarketSnapshot,
    RiskContext,
    RiskState,
)
from sochron1k.preflight import PreflightPolicy
from sochron1k.service import ExecutionService, RiskDenied
from sochron1k.simulator import SimulatorAdapter, SimulatorBehavior


def denied(call, reason):
    try:
        call()
    except RiskDenied as error:
        assert error.reason == reason
    else:
        raise AssertionError("startup admission was bypassed")


def probe(config_path):
    data = json.loads(config_path.read_text())
    types = dict(
        account=AccountSnapshot,
        contract=ContractSpec,
        market=MarketSnapshot,
        intent=CommandIntent,
        risk=RiskContext,
    )
    args = {key: model.model_validate(data[key]) for key, model in types.items()}
    args.update(policy=PreflightPolicy(**data["policy"]), now=datetime.fromisoformat(data["now"]))
    journal = Journal(config_path.parent / "startup-journal.sqlite3")
    adapter = SimulatorAdapter(
        SimulatorBehavior.ACCEPT_THEN_TIMEOUT,
        account=args["account"],
        symbol=args["contract"].symbol,
    )
    service = ExecutionService(journal, adapter)
    startup = dict(
        policy=args["policy"],
        experiment_id=args["intent"].experiment_id,
        executor_id="simulator",
        now=args["now"],
    )
    denied(lambda: service.submit(**args), "STARTUP_REQUIRED")
    denied(lambda: service.startup(**startup), "RISK_BASELINE_MISSING")
    assert adapter.send_count == journal.counts()["commands"] == 0
    state = RiskState(
        account_ref=args["intent"].account_ref,
        experiment_id=args["intent"].experiment_id,
        bangkok_day=args["now"].date(),
        daily_baseline=args["risk"].daily_baseline,
        experiment_baseline=args["risk"].experiment_baseline,
        updated_at=args["now"],
    )
    journal.save_risk_state(state)
    report = service.startup(**startup)
    assert report["local_entries_admitted"] and report["execution_ready"] is False
    assert report["auto_trading_enabled"] is False
    assert service.submit(**args).state is CommandState.UNKNOWN
    denied(lambda: service.submit(**args), "STARTUP_REQUIRED")
    restarted = ExecutionService(Journal(journal.path), adapter)
    denied(lambda: restarted.submit(**args), "STARTUP_REQUIRED")
    report = restarted.startup(**startup)
    assert not report["local_entries_admitted"]  # confirmed existing exposure remains
    duplicate = restarted.submit(**args)
    assert duplicate.duplicate and duplicate.protected and duplicate.state is CommandState.FILLED
    assert adapter.send_count == journal.counts()["dispatch_attempts"] == 1
    assert journal.counts()["broker_deals"] == journal.counts()["exposure_slots"] == 1
    adapter.generation = "fixture-replacement"
    denied(lambda: restarted.submit(**args), "EXECUTOR_GENERATION_CHANGED")
    state = state.model_copy(update={"daily_halt": True, "total_halt": True})
    journal.save_risk_state(state)
    restarted.startup(**startup)
    denied(lambda: restarted.submit(**args), "TOTAL_HALT_ACTIVE")
    assert journal.risk_state(state.account_ref, state.experiment_id) == state
    assert adapter.send_count == 1
    print(
        json.dumps(
            dict(
                result="PASS",
                scope="installed-simulator",
                sends=1,
                attempts=1,
                deals=1,
                halts_preserved=True,
                execution_ready=False,
                auto_trading_enabled=False,
            )
        )
    )


if __name__ == "__main__":
    probe(Path(sys.argv[1]))
