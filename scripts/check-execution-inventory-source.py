#!/usr/bin/env python3
"""Static guard for the read-only MT5 execution inventory observer; not a compiler."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "mt5/ea/SochronExecutionInventory.mq5"
FORBIDDEN = {
    "OrderCheck",
    "OrderSend",
    "OrderSendAsync",
    "MqlTradeRequest",
    "MqlTradeResult",
    "CTrade",
    "PositionOpen",
    "PositionClose",
    "OrderDelete",
    "OrderModify",
    "HistorySelect",
    "HistoryOrderGetTicket",
    "HistoryDealGetTicket",
    "OnTradeTransaction",
    "GlobalVariableSet",
    "GlobalVariableSetOnCondition",
    "SocketCreate",
    "SendMail",
    "SendNotification",
    "SendFTP",
    "FileWrite",
    "FileWriteArray",
    "FileWriteString",
    "FileDelete",
    "FileMove",
    "FILE_WRITE",
    "FILE_COMMON",
    "MQLInfoInteger",
    "MQL_TRADE_ALLOWED",
    "TERMINAL_TRADE_ALLOWED",
}
REQUIRED = {
    "OrdersTotal",
    "OrderGetTicket",
    "OrderGetString",
    "OrderGetInteger",
    "PositionsTotal",
    "PositionGetTicket",
    "PositionGetString",
    "PositionGetInteger",
    "WebRequest",
    "AccountInfoInteger",
    "AccountInfoDouble",
    "AccountInfoString",
}
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*\b')


def findings(source: str) -> list[str]:
    uncommented = re.sub(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
        lambda match: "" if match[0].startswith(("//", "/*")) else match[0],
        source,
    )
    issues: list[str] = []
    if re.search(r"^\s*#\s*import\b", uncommented, re.MULTILINE):
        issues.append("external imports forbidden")
    includes = re.findall(r"^\s*#\s*include\s+(.+)$", uncommented, re.MULTILINE)
    if includes != ['"ExecutionProtocol.mqh"']:
        issues.append("unreviewed include graph")
    identifiers = {
        token for token in TOKEN.findall(source) if re.fullmatch(r"[A-Za-z_]\w*", token)
    }
    for name in sorted(identifiers & FORBIDDEN):
        issues.append(f"forbidden mutation or authority identifier: {name}")
    for name in sorted(REQUIRED - identifiers):
        issues.append(f"missing inventory boundary identifier: {name}")
    if not re.search(
        r"input\s+bool\s+EnableReadOnlyExecutionInventory\s*=\s*false\s*;", source
    ):
        issues.append("inventory observer must default off")
    if re.search(r"input\s+\w+\s+\w*(?:token|password|secret|url)\w*", source, re.IGNORECASE):
        issues.append("credential or URL must not be an EA input")
    if len(re.findall(r"\bFileOpen\s*\(", uncommented)) != 1 or not re.search(
        r"FileOpen\(SCXI_TOKEN_FILE,FILE_READ\|FILE_BIN\)", uncommented
    ):
        issues.append("only the fixed read-only token file is allowed")
    if "sample.algo_trading_allowed=false" not in source:
        issues.append("policy-only observer must hard-code algorithmic trading false")
    requests = re.findall(r'ScxiRequest\("(GET|POST)","([^"]+)"', source)
    if requests != [("GET", "/challenge"), ("POST", "/inventory")]:
        issues.append("only challenge and inventory routes are allowed")
    if "/commands/next" in source or "/outcomes" in source:
        issues.append("command and outcome routes forbidden")
    if "SCXI_API+path" not in source or not re.search(
        r'const\s+string\s+SCXI_API="http://127\.0\.0\.1:8000/executor/v1";', source
    ):
        issues.append("fixed loopback execution origin required")
    return issues


def main() -> int:
    source = (ROOT / SOURCE).read_text()
    issues = findings(source)
    if issues:
        for issue in issues:
            print("FAIL", SOURCE + ":", issue)
        return 1
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    print(
        json.dumps(
            {
                "result": "PASS",
                "scope": "read-only execution inventory static source guard only",
                "source_revision": revision,
                "dirty": dirty,
                "sha256": hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
                "compilation": "NOT RUN",
                "mql_execution": "NOT RUN",
                "account_access": "NOT RUN",
                "broker_operation": "NOT RUN",
                "execution_ready": False,
                "auto_trading_enabled": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
