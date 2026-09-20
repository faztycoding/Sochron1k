from __future__ import annotations

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = runpy.run_path(str(ROOT / "scripts/check-demo-executor-source.py"))
SOURCES = {name: (ROOT / name).read_text() for name in GUARD["SOURCES"]}
EA = GUARD["SOURCES"][0]
RUNTIME = GUARD["SOURCES"][1]
LEDGER = GUARD["SOURCES"][2]


def changed(name: str, old: str, new: str) -> dict[str, str]:
    mutated = dict(SOURCES)
    mutated[name] = mutated[name].replace(old, new)
    assert mutated[name] != SOURCES[name]
    return mutated


def test_scn028_ac01_ac10_default_off_sources_pass_and_are_secret_scanned():
    assert GUARD["findings"](SOURCES) == []
    scanner = runpy.run_path(str(ROOT / "scripts/check-no-secrets.py"))
    candidates = set(scanner["candidate_files"]())
    assert all(ROOT / name in candidates for name in GUARD["SOURCES"])


@pytest.mark.parametrize("identifier", sorted(GUARD["FORBIDDEN_IDENTIFIERS"]))
def test_scn028_ac01_ac07_guard_rejects_authority_expansion(identifier):
    mutated = dict(SOURCES)
    mutated[EA] += f"\nvoid injected() {{ {identifier}(); }}\n"
    assert GUARD["findings"](mutated)


@pytest.mark.parametrize("identifier", sorted(GUARD["REQUIRED_IDENTIFIERS"]))
def test_scn028_ac02_ac09_guard_detects_removed_boundary(identifier):
    mutated = {
        name: source.replace(identifier, "Removed" + identifier)
        for name, source in SOURCES.items()
    }
    assert mutated != SOURCES
    assert GUARD["findings"](mutated)


def test_scn028_ac01_ac02_guard_detects_config_file_and_include_expansion():
    assert GUARD["findings"](
        changed(EA, "EnableDemoExecution=false", "EnableDemoExecution=true")
    )
    assert GUARD["findings"](
        changed(EA, '#include "ExecutionRuntime.mqh"', '#include <Trade/Trade.mqh>')
    )
    mutated = dict(SOURCES)
    mutated[EA] += '\n#import "external.dll"\n'
    assert GUARD["findings"](mutated)
    mutated = dict(SOURCES)
    mutated[EA] += '\ninput string PrivateToken="";\n'
    assert GUARD["findings"](mutated)
    mutated = dict(SOURCES)
    mutated[EA] += '\ninput string ApiUrl="";\n'
    assert GUARD["findings"](mutated)
    mutated = dict(SOURCES)
    mutated[EA] += '\nvoid injected(){ FileOpen("x",FILE_READ|FILE_BIN); }\n'
    assert GUARD["findings"](mutated)


def test_scn028_ac04_guard_detects_origin_route_and_request_budget_changes():
    assert GUARD["findings"](
        changed(EA, "http://127.0.0.1:8000/executor/v1", "http://0.0.0.0:8000/executor/v1")
    )
    assert GUARD["findings"](changed(EA, '"/commands/next"', '"/commands/all"'))
    assert GUARD["findings"](changed(EA, "SCXE_TIMEOUT_MS=500", "SCXE_TIMEOUT_MS=5000"))
    assert GUARD["findings"](
        changed(EA, "scxe_requests_this_timer>=1", "scxe_requests_this_timer>=2")
    )
    assert GUARD["findings"](
        changed(
            EA,
            "INVENTORY_UNCONFIRMED_RECHALLENGE_PENDING",
            "INVENTORY_UNCONFIRMED",
        )
    )


def test_scn028_ac07_guard_detects_extra_send_and_reordered_journal():
    mutated = dict(SOURCES)
    mutated[EA] += "\nvoid injected(MqlTradeRequest &r,MqlTradeResult &x){ OrderSend(r,x); }\n"
    assert GUARD["findings"](mutated)
    assert GUARD["findings"](
        changed(EA, '"SEND_STARTED",prepared.observed_at', '"SEND_AFTER",prepared.observed_at')
    )
    assert GUARD["findings"](changed(EA, "bool sent=OrderSend", "bool sent=RemovedOrderSend"))


def test_scn028_ac08_trade_callback_is_bounded_to_dirty_flag():
    assert GUARD["findings"](
        changed(
            EA,
            "scxe_reconcile_needed=true;\n  }\n\nvoid OnTimer",
            "scxe_reconcile_needed=true; WebRequest();\n  }\n\nvoid OnTimer",
        )
    )


def test_scn028_ac01_disabled_shutdown_has_no_timer_or_file_side_effect():
    assert GUARD["findings"](
        changed(EA, "if(!EnableDemoExecution) return;", "if(EnableDemoExecution) return;")
    )


def test_scn028_ac01_command_poll_requires_fresh_trading_permission():
    assert GUARD["findings"](
        changed(EA, "if(!ScxeTradingAllowed())", "if(false)")
    )
    assert GUARD["findings"](
        changed(EA, "if(!scxe_inventory_admitted)", "if(false)")
    )


def test_scn028_ac01_ac03_ac06_detects_demo_scan_and_risk_regressions():
    assert GUARD["findings"](
        changed(
            RUNTIME,
            "actual_mode==ACCOUNT_TRADE_MODE_DEMO",
            "actual_mode==actual_mode",
        )
    )
    assert GUARD["findings"](
        changed(
            RUNTIME,
            "total_risk>command.risk_limit || total_risk>hard_risk",
            "total_risk>command.risk_limit",
        )
    )
    assert GUARD["findings"](
        changed(RUNTIME, "SCXE_MAX_RISK_FRACTION 0.0025", "SCXE_MAX_RISK_FRACTION 0.25")
    )
    assert GUARD["findings"](
        changed(
            RUNTIME,
            "command.volume,risk_entry,command.stop_loss",
            "command.volume,entry,command.stop_loss",
        )
    )
    assert GUARD["findings"](
        changed(RUNTIME, "ScxeStableHistory(symbol,magic,since-60)", "true")
    )
    assert GUARD["findings"](
        changed(
            EA,
            "complete=(scan.foreign_orders==0 && scan.foreign_positions==0)",
            "complete=true",
        )
    )


def test_scn028_ac02_ac10_detects_ledger_flush_and_time_regressions():
    assert GUARD["findings"](changed(LEDGER, "FileFlush(handle);", "RemovedFlush(handle);"))
    assert GUARD["findings"](changed(LEDGER, "stored!=line", "false"))
    assert GUARD["findings"](
        changed(
            LEDGER,
            "previous.observed_at!=next.observed_at",
            "previous.observed_at==next.observed_at",
        )
    )
    assert GUARD["findings"](
        changed(EA, "stage,record.observed_at", "stage,ScUtc(TimeGMT())")
    )
    assert GUARD["findings"](
        changed(EA, "record.history_from,record.command_json", "1,record.command_json")
    )
