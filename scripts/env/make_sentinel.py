"""ENV-002 synthetic sentinel, made on the VPS (docs/contracts/ENV-002-research-host-separation.md v1.8).

Run by the owner in the vault folder on the VPS, with no arguments (standard library only; it imports
nothing of sochron):
  python scripts\\env\\make_sentinel.py      (or: uv run --no-project python <repo>\\scripts\\env\\make_sentinel.py)

It writes one file, SENTINEL-ENV002-<first 8 token characters>.json, holding a random token and 60 fake
M1 bars from 2025-01-02T00:00:00Z (inside the excluded period, marked "synthetic"), and prints the six
values Claude commits as docs/evidence/ENV-002-sentinel.json: name, size, sha256, token, vault_path and
created_utc. The owner copies the printed text, never the file. The file is not real market data.
"""

import hashlib
import json
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta

FIRST_BAR = datetime(2025, 1, 2, tzinfo=UTC)
BARS = 60
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def sentinel_document(token: str) -> dict:
    bars = [{"time_utc": (FIRST_BAR + timedelta(minutes=index)).strftime(TIME_FORMAT), "open": "2000.00",
             "high": "2000.50", "low": "1999.50", "close": "2000.25", "spread": 200} for index in range(BARS)]
    return {"synthetic": True, "purpose": "ENV-002 sentinel", "token": token, "bars": bars}


def main() -> int:
    token = secrets.token_hex(16)
    name = f"SENTINEL-ENV002-{token[:8]}.json"
    data = (json.dumps(sentinel_document(token), indent=2) + "\n").encode("ascii")
    with open(name, "xb") as handle:  # never overwrites an earlier sentinel
        handle.write(data)
    values = {
        "name": name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "token": token,
        "vault_path": os.path.abspath(os.getcwd()),
        "created_utc": datetime.now(UTC).strftime(TIME_FORMAT),
    }
    sys.stdout.write(json.dumps(values, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
