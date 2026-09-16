#!/usr/bin/env python3
"""Compare a synthetic MQL self-test output with the API golden wire fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/fixtures/mt5-telemetry-v1.json"
sys.path.insert(0, str(ROOT / "services/api/src"))

from sochron1k.bridge_api import unique_object  # noqa: E402
from sochron1k.telemetry import MAX_FRAME_BYTES, TelemetryFrame  # noqa: E402


def verify(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(MAX_FRAME_BYTES + 1)
    if len(raw) > MAX_FRAME_BYTES or b"\0" in raw:
        raise ValueError("invalid fixture encoding or size")
    observed = json.loads(raw, object_pairs_hook=unique_object)
    expected = json.loads(GOLDEN.read_bytes())
    if observed != expected:
        raise ValueError("not the exact synthetic fixture")
    TelemetryFrame.model_validate(observed)
    return {
        "result": "PASS",
        "scope": "synthetic wire fixture matches API schema and golden values",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "golden_sha256": hashlib.sha256(GOLDEN.read_bytes()).hexdigest(),
        "input_is_committed_golden": path.resolve() == GOLDEN.resolve(),
        "limits": "Does not attest compiler/self-test execution or any MT5 account",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=GOLDEN)
    args = parser.parse_args()
    try:
        report = verify(args.fixture)
    except OSError, ValueError, RecursionError:
        print("FAIL synthetic wire fixture; contents redacted", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
