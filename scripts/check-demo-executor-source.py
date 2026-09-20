#!/usr/bin/env python3
"""Static guard for the default-off MT5 Demo mutation EA; not a compiler."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "mt5/ea/SochronDemoExecutor.mq5",
    "mt5/ea/ExecutionRuntime.mqh",
    "mt5/ea/ExecutionLedger.mqh",
)
EXPECTED_INCLUDES = {
    SOURCES[0]: ['"ExecutionRuntime.mqh"'],
    SOURCES[1]: ['"ExecutionLedger.mqh"'],
    SOURCES[2]: ['"ExecutionProtocol.mqh"'],
}
FORBIDDEN_IDENTIFIERS = {
    "ACCOUNT_TRADE_MODE_CONTEST",
    "ACCOUNT_TRADE_MODE_REAL",
    "CTrade",
    "FILE_COMMON",
    "GlobalVariableSet",
    "GlobalVariableSetOnCondition",
    "OrderDelete",
    "OrderModify",
    "OrderSendAsync",
    "PositionClose",
    "PositionOpen",
    "SendFTP",
    "SendMail",
    "SendNotification",
    "SocketCreate",
    "TRADE_ACTION_MODIFY",
    "TRADE_ACTION_PENDING",
    "TRADE_ACTION_SLTP",
}
REQUIRED_IDENTIFIERS = {
    "ACCOUNT_TRADE_MODE_DEMO",
    "FileFlush",
    "HistoryDealSelect",
    "HistoryDealGetTicket",
    "HistoryDealsTotal",
    "HistoryOrderGetTicket",
    "HistoryOrdersTotal",
    "HistorySelect",
    "MQL_TRADE_ALLOWED",
    "OnTradeTransaction",
    "OrderCalcMargin",
    "OrderCalcProfit",
    "OrderCheck",
    "OrderSend",
    "OrdersTotal",
    "POSITION_SL",
    "PositionsTotal",
    "ScxeStableCurrent",
    "ScxeStableHistory",
    "TERMINAL_TRADE_ALLOWED",
    "TimeTradeServer",
    "WebRequest",
}
REQUIRED_STAGES = {
    "PREPARED",
    "SEND_STARTED",
    "SEND_RETURN",
    "OUTCOME_READY",
    "OUTCOME_ACKED",
    "RECOVERED_INVENTORY",
}
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*\b')


def _without_comments(source: str, *, keep_strings: bool = True) -> str:
    return re.sub(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
        lambda match: (
            ""
            if match[0].startswith(("//", "/*"))
            else (match[0] if keep_strings else '""')
        ),
        source,
    )


def _identifiers(source: str) -> set[str]:
    return {
        token for token in TOKEN.findall(source) if re.fullmatch(r"[A-Za-z_]\w*", token)
    }


def _function_body(source: str, name: str) -> str | None:
    match = re.search(rf"\b(?:bool|void|int|string)\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if match is None:
        return None
    opening = source.find("{", match.start())
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    return None


def findings(sources: dict[str, str]) -> list[str]:
    issues: list[str] = []
    if set(sources) != set(SOURCES):
        return ["source set differs from the reviewed executor boundary"]

    all_source = "\n".join(sources[name] for name in SOURCES)
    all_uncommented = _without_comments(all_source)
    identifiers = _identifiers(all_source)
    for name, source in sources.items():
        uncommented = _without_comments(source)
        if re.search(r"^\s*#\s*import\b", uncommented, re.MULTILINE):
            issues.append(f"{name}: external imports forbidden")
        includes = re.findall(r"^\s*#\s*include\s+(.+)$", uncommented, re.MULTILINE)
        if includes != EXPECTED_INCLUDES[name]:
            issues.append(f"{name}: unreviewed include graph")

    for identifier in sorted(identifiers & FORBIDDEN_IDENTIFIERS):
        issues.append(f"forbidden authority identifier: {identifier}")
    for identifier in sorted(REQUIRED_IDENTIFIERS - identifiers):
        issues.append(f"missing mutation-boundary identifier: {identifier}")
    for stage in sorted(REQUIRED_STAGES):
        if f'"{stage}"' not in all_source:
            issues.append(f"missing durable ledger stage: {stage}")

    ea = sources[SOURCES[0]]
    runtime = sources[SOURCES[1]]
    ledger = sources[SOURCES[2]]
    ea_uncommented = _without_comments(ea)
    ledger_uncommented = _without_comments(ledger)
    if not re.search(r"input\s+bool\s+EnableDemoExecution\s*=\s*false\s*;", ea):
        issues.append("executor must default off")
    if re.search(r"input\s+\w+\s+\w*(?:token|password|secret|url)\w*", ea, re.IGNORECASE):
        issues.append("credential or URL must not be an EA input")
    constants = {
        "SCXE_API": "http://127.0.0.1:8000/executor/v1",
        "SCXE_TOKEN_FILE": "sochron-execution.token",
        "SCXE_LOCK_FILE": "sochron-execution.lock",
        "SCXE_LEDGER_FILE": "sochron-execution-ledger.v1",
    }
    for name, value in constants.items():
        if not re.search(
            rf'const\s+string\s+{name}\s*=\s*"{re.escape(value)}"\s*;', ea
        ):
            issues.append(f"fixed private constant changed: {name}")
    file_opens = re.findall(r"\bFileOpen\s*\(([^;]+)\)", ea_uncommented)
    if len(file_opens) != 3:
        issues.append("only token, lock and ledger files may be opened")
    for expected in (
        r"FileOpen\(SCXE_TOKEN_FILE,FILE_READ\|FILE_BIN\)",
        r"FileOpen\(SCXE_LOCK_FILE,FILE_READ\|FILE_WRITE\|FILE_BIN\)",
        r"FileOpen\(SCXE_LEDGER_FILE,\s*FILE_READ\|FILE_WRITE\|FILE_BIN\|FILE_ANSI\)",
    ):
        if not re.search(expected, ea_uncommented):
            issues.append("fixed non-shared private file mode changed")
    if "FileOpen" in _identifiers(runtime + ledger):
        issues.append("only the EA may open private files")

    if len(re.findall(r"\bOrderSend\s*\(", all_uncommented)) != 1:
        issues.append("executor must contain exactly one OrderSend call site")
    if len(re.findall(r"\bOrderCheck\s*\(", all_uncommented)) != 1:
        issues.append("executor must contain exactly one OrderCheck call site")
    process = _function_body(ea_uncommented, "ScxeProcessCommand")
    if process is None:
        issues.append("missing command mutation function")
    else:
        ordered = (
            "ScxeJournalPrepared",
            "ScxePreflightOpen",
            "OrderCheck",
            '"SEND_STARTED"',
            "ScxeIdentityMatches",
            "ScxeTradingAllowed",
            "OrderSend",
            '"SEND_RETURN"',
        )
        positions = [process.find(item) for item in ordered]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            issues.append("journal/preflight/check/fence/send ordering changed")

    transaction = _function_body(ea_uncommented, "OnTradeTransaction")
    if transaction is None or re.sub(r"\s+", "", transaction) != "scxe_reconcile_needed=true;":
        issues.append("trade callback must only schedule timer reconciliation")
    on_init = _function_body(ea_uncommented, "OnInit")
    if on_init is None or not re.match(
        r"\s*if\s*\(\s*!EnableDemoExecution\s*\)", on_init
    ):
        issues.append("disabled startup must return before all side effects")
    on_deinit = _function_body(ea_uncommented, "OnDeinit")
    if on_deinit is None or not re.match(
        r"\s*if\s*\(\s*!EnableDemoExecution\s*\)\s*return\s*;", on_deinit
    ):
        issues.append("disabled shutdown must return before all side effects")
    on_timer = _function_body(ea_uncommented, "OnTimer")
    if (
        on_timer is None
        or "scxe_inventory_admitted" not in on_timer
        or on_timer.rfind("ScxeTradingAllowed") < 0
        or on_timer.rfind("ScxeTradingAllowed") > on_timer.rfind("ScxePollCommand")
    ):
        issues.append("complete inventory and fresh trading permission must precede polling")

    requests = re.findall(r'ScxeRequest\("(GET|POST)","([^"]+)"', ea)
    if sorted(requests) != sorted(
        [
            ("GET", "/challenge"),
            ("POST", "/inventory"),
            ("GET", "/commands/next"),
            ("POST", "/outcomes"),
        ]
    ):
        issues.append("executor route set changed")
    if not re.search(r"const\s+int\s+SCXE_TIMEOUT_MS\s*=\s*500\s*;", ea):
        issues.append("reviewed synchronous request timeout changed")
    if "scxe_requests_this_timer>=1" not in ea or "EventSetTimer(1)" not in ea:
        issues.append("one-request-per-timer budget changed")
    inventory_upload = _function_body(ea_uncommented, "ScxeUploadInventory")
    if (
        inventory_upload is None
        or "ScxeReconnectLater" not in inventory_upload
        or "INVENTORY_UNCONFIRMED_RECHALLENGE_PENDING" not in inventory_upload
    ):
        issues.append("unconfirmed inventory must rechallenge before rebuilding payload")

    if "actual_mode==ACCOUNT_TRADE_MODE_DEMO" not in runtime:
        issues.append("exact Demo account-mode comparison missing")
    if not all(
        value in runtime
        for value in (
            "actual_login==login",
            "actual_server==server",
            "actual_currency==currency",
            "actual_margin==margin_mode",
            "_Symbol==symbol",
        )
    ):
        issues.append("exact account/server/currency/margin/symbol fence changed")
    if runtime.count("ScxeStableCurrent(") < 5 or runtime.count("ScxeStableHistory(") < 4:
        issues.append("bounded repeated reconciliation scans missing")
    if "complete=(scan.foreign_orders==0 && scan.foreign_positions==0)" not in ea:
        issues.append("foreign account state must make restart inventory incomplete")
    if (
        "#define SCXE_MAX_RISK_FRACTION 0.0025" not in runtime
        or "OrderCalcProfit(type,symbol,command.volume,risk_entry,command.stop_loss" not in runtime
        or "total_risk>command.risk_limit || total_risk>hard_risk" not in runtime
    ):
        issues.append("broker loss plus authorized costs gate missing")
    if (
        not re.search(
            r"scxe_book,stage,record\.observed_at,\s*record\.history_from", ea
        )
        or "previous.observed_at!=next.observed_at" not in ledger
        or "previous.history_from!=next.history_from" not in ledger
    ):
        issues.append("original UTC and trade-server times must survive ledger transitions")
    if not re.search(
        r"FileWriteString\(handle,line\)[\s\S]+FileFlush\(handle\)[\s\S]+book=candidate",
        ledger_uncommented,
    ) or "stored!=line" not in ledger:
        issues.append("append/flush/commit ledger ordering changed")
    return issues


def main() -> int:
    sources = {name: (ROOT / name).read_text() for name in SOURCES}
    issues = findings(sources)
    if issues:
        for issue in issues:
            print("FAIL", issue)
        return 1
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    print(
        json.dumps(
            {
                "result": "PASS",
                "scope": "default-off Demo mutation EA static source guard only",
                "source_revision": revision,
                "dirty": dirty,
                "sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    for name in SOURCES
                },
                "metaeditor_compilation": "NOT RUN",
                "mql_execution": "NOT RUN",
                "exclusive_lock_runtime": "NOT RUN",
                "flush_durability": "NOT RUN",
                "account_access": "NOT RUN",
                "broker_operation": "NOT RUN",
                "demo_round_trip": "NOT RUN",
                "execution_ready": False,
                "auto_trading_enabled": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
