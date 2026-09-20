#!/usr/bin/env python3
"""Source-only purity guard for the MQL5 execution codec; not a compiler."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "mt5/ea/ExecutionProtocol.mqh",
    "mt5/ea/SochronExecutionProtocolSelfTest.mq5",
)
FORBIDDEN_PURE = {
    "WebRequest",
    "AccountInfoInteger",
    "AccountInfoDouble",
    "AccountInfoString",
    "TerminalInfoInteger",
    "MQLInfoInteger",
    "SymbolInfoTick",
    "SymbolInfoInteger",
    "SymbolInfoDouble",
    "OrdersTotal",
    "OrderGetTicket",
    "PositionsTotal",
    "PositionGetTicket",
    "HistorySelect",
    "HistoryOrderGetTicket",
    "HistoryDealGetTicket",
    "OrderCheck",
    "OrderSend",
    "OrderSendAsync",
    "MqlTradeRequest",
    "MqlTradeResult",
    "CTrade",
    "GlobalVariableSet",
    "GlobalVariableSetOnCondition",
    "SocketCreate",
    "SendMail",
    "SendNotification",
    "SendFTP",
}
SELF_TEST_OUTPUTS = {
    "SochronExecutionInventorySelfTest.json",
    "SochronExecutionOutcomeSelfTest.json",
}
REQUIRED_TYPED_EVIDENCE = {
    "ScxDealEvidenceJson",
    "ScxBrokerEvidenceJson",
    "ScxManagementEvidenceJson",
    "ScxRejectionEvidenceJson",
    "ScxInventoryEvidenceJson",
    "ScxEntrySnapshotOutcomeJson",
    "ScxManagementSnapshotOutcomeJson",
}
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*\b')


def findings(source: str, *, self_test: bool = False) -> list[str]:
    uncommented = re.sub(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
        lambda match: "" if match[0].startswith(("//", "/*")) else match[0],
        source,
    )
    issues: list[str] = []
    if re.search(r"^\s*#\s*import\b", uncommented, re.MULTILINE):
        issues.append("external imports forbidden")
    includes = re.findall(r"^\s*#\s*include\s+(.+)$", uncommented, re.MULTILINE)
    expected = (
        ['"ExecutionProtocol.mqh"']
        if self_test
        else ['"TelemetryProtocol.mqh"']
    )
    if includes != expected:
        issues.append("unreviewed include graph")
    identifiers = {
        token for token in TOKEN.findall(source) if re.fullmatch(r"[A-Za-z_]\w*", token)
    }
    for name in sorted(identifiers & FORBIDDEN_PURE):
        issues.append(f"forbidden identifier: {name}")
    if not self_test:
        for name in sorted(REQUIRED_TYPED_EVIDENCE - identifiers):
            issues.append(f"missing typed cumulative evidence boundary: {name}")
    file_identifiers = {
        "FileOpen",
        "FileReadArray",
        "FileWrite",
        "FileWriteArray",
        "FileWriteString",
        "FileDelete",
        "FileMove",
        "FILE_COMMON",
    }
    if not self_test:
        for name in sorted(identifiers & file_identifiers):
            issues.append(f"forbidden identifier: {name}")
    else:
        if "FILE_COMMON" in identifiers:
            issues.append("common terminal files forbidden")
        outputs = set(
            re.findall(r'FileOpen\(\s*"([^"]+)"\s*,\s*FILE_WRITE\s*\|\s*FILE_BIN\s*\)', source)
        )
        if outputs != SELF_TEST_OUTPUTS or len(re.findall(r"\bFileOpen\s*\(", source)) != 2:
            issues.append("self-test writes only reviewed synthetic outputs")
        unreviewed_operations = {
            "FileReadArray",
            "FileWrite",
            "FileWriteString",
            "FileDelete",
            "FileMove",
        }
        if identifiers & unreviewed_operations:
            issues.append("unreviewed self-test file operation")
        if re.search(r"input\s+\w+\s+\w*(?:token|password|secret)\w*", source, re.IGNORECASE):
            issues.append("credentials must not be script inputs")
    return issues


def main() -> int:
    failures: list[str] = []
    for name in SOURCES:
        source = (ROOT / name).read_text()
        for issue in findings(source, self_test=name.endswith("SelfTest.mq5")):
            failures.append(f"{name}: {issue}")
    if failures:
        for failure in failures:
            print("FAIL", failure)
        return 1
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    print(
        json.dumps(
            {
                "result": "PASS",
                "scope": "pure execution codec static source guard only",
                "source_revision": revision,
                "dirty": dirty,
                "sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                    for name in SOURCES
                },
                "compilation": "NOT RUN",
                "mql_self_test": "NOT RUN",
                "account_access": "NOT RUN",
                "broker_operation": "NOT RUN",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
