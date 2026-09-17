#!/usr/bin/env python3
"""Source-only guard for the observer. This is NOT a compiler or MQL interpreter."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "mt5/ea/SochronTelemetry.mq5",
    "mt5/ea/TelemetryProtocol.mqh",
    "mt5/ea/SochronTelemetrySelfTest.mq5",
)
FORBIDDEN = {
    "OrderSend",
    "OrderSendAsync",
    "MqlTradeRequest",
    "CTrade",
    "SendMail",
    "SendNotification",
    "SendFTP",
    "SocketCreate",
    "ChartSetSymbolPeriod",
    "ExpertRemove",
}
TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*\b')


def findings(source: str, *, protocol: bool = False, self_test: bool = False) -> list[str]:
    # Comments and string literals cannot introduce callable MQL identifiers.
    uncommented = re.sub(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
        lambda match: "" if match[0].startswith(("//", "/*")) else match[0],
        source,
    )
    issues = []
    if re.search(r"^\s*#\s*import\b", uncommented, re.MULTILINE):
        issues.append("external imports forbidden")
    includes = re.findall(r"^\s*#\s*include\s+(.+)$", uncommented, re.MULTILINE)
    expected = [] if protocol else ['"TelemetryProtocol.mqh"']
    if includes != expected:
        issues.append("unreviewed include graph")
    identifiers = {token for token in TOKEN.findall(source) if re.fullmatch(r"[A-Za-z_]\w*", token)}
    denied = FORBIDDEN | (
        {
            "WebRequest",
            "AccountInfoInteger",
            "AccountInfoDouble",
            "AccountInfoString",
            "SymbolInfoTick",
            "CopyRates",
            "SeriesInfoInteger",
            "SymbolInfoInteger",
            "SymbolInfoDouble",
        }
        if protocol or self_test
        else set()
    )
    if not self_test:
        denied |= {"FILE_WRITE", "FileWrite", "FileWriteArray", "FileWriteString", "FILE_COMMON"}
    for name in sorted(identifiers & denied):
        issues.append(f"forbidden identifier: {name}")
    if not protocol and not self_test:
        if not re.search(r"input\s+bool\s+EnableReadOnlyTelemetry\s*=\s*false\s*;", source):
            issues.append("observer must default off")
        if not re.search(r"input\s+bool\s+EnableReadOnlyCharts\s*=\s*false\s*;", source):
            issues.append("chart observer must default off")
        if re.search(r"input\s+\w+\s+\w*(?:token|password|secret)\w*", source, re.IGNORECASE):
            issues.append("credentials must not be EA inputs")
    return issues


def main() -> int:
    failures = []
    for name in SOURCES:
        source = (ROOT / name).read_text()
        for issue in findings(source, protocol=name.endswith(".mqh"), self_test="SelfTest" in name):
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
                "scope": "static source guard only",
                "source_revision": revision,
                "dirty": dirty,
                "sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES
                },
                "compilation": "NOT RUN",
                "mql_self_test": "NOT RUN",
                "broker_operation": "NOT RUN",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
