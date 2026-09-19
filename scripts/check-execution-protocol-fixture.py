#!/usr/bin/env python3
"""Verify synthetic MQL execution codec output against exact API golden fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api/src"))

from sochron1k.bridge_api import unique_object  # noqa: E402
from sochron1k.execution_bridge import (  # noqa: E402
    MAX_EXECUTION_FRAME_BYTES,
    ExecutionInventoryFrame,
    ExecutionOutcomeFrame,
)

GOLDENS = {
    "inventory": ROOT / "tests/fixtures/mt5-execution-inventory-v1.json",
    "outcome": ROOT / "tests/fixtures/mt5-execution-outcome-v1.json",
}
MODELS = {"inventory": ExecutionInventoryFrame, "outcome": ExecutionOutcomeFrame}
PROTOCOLS = {
    "inventory": "sochron.execution.inventory.v1",
    "outcome": "sochron.execution.outcome.v1",
}


def verify(path: Path, *, kind: str) -> dict:
    if kind not in GOLDENS:
        raise ValueError("unknown fixture kind")
    golden = GOLDENS[kind]
    with path.open("rb") as stream:
        raw = stream.read(MAX_EXECUTION_FRAME_BYTES + 1)
    if len(raw) > MAX_EXECUTION_FRAME_BYTES or b"\0" in raw:
        raise ValueError("invalid fixture encoding or size")
    observed = json.loads(raw, object_pairs_hook=unique_object)
    expected = json.loads(golden.read_bytes(), object_pairs_hook=unique_object)
    if observed != expected:
        raise ValueError("not the exact synthetic fixture")
    MODELS[kind].model_validate(observed)
    return {
        "result": "PASS",
        "scope": "synthetic MQL execution wire fixture matches API schema and golden values",
        "kind": kind,
        "protocol": PROTOCOLS[kind],
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "golden_sha256": hashlib.sha256(golden.read_bytes()).hexdigest(),
        "input_is_committed_golden": path.resolve() == golden.resolve(),
        "limits": "Does not attest compiler/self-test execution, MT5 state or broker operation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(GOLDENS), required=True)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.fixture or GOLDENS[args.kind], kind=args.kind)
    except OSError, ValueError, RecursionError:
        print("FAIL synthetic execution wire fixture; contents redacted", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
