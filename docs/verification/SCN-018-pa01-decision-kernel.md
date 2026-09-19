# SCN-018 PA01 decision kernel verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`13a3924b1528a80384b3c5441564824afe492ccf`; the final commit and remote revision
are recorded after this document is committed.

AC-01 through AC-09 in the
[task contract](../contracts/SCN-018-pa01-decision-kernel.md) pass for the pure local
calculation boundary. No bar aggregation, scheduler, feature/signal persistence,
backtest, hosted service, MT5 operation, risk admission, command or deployment was
run.

## Implemented scope

- Added a packaged `PA01-v1.0.0` pure decision kernel with an exact parameter hash,
  strict Decimal closed-bar/context inputs and stable dataset/setup/decision hashes.
- Added as-of M5/H1 selection, fixed warm-up/window behavior, explicit gap handling,
  EMA20/50, Wilder ATR14/ADX14 and strict delayed L2/R2 pivot evidence.
- Added symmetric PA01 trend/pullback/breakout/stop-distance rules plus deterministic
  stale, closed-market, gap, news, spread, exposure and pending-work blocks.
- Recorded next-tick/drift/SL/2R/time-exit parameters while hard-coding order creation
  and risk admission false.

## Verification

- `.venv/bin/python -m pytest tests/test_pa01.py -q`: **22 passed** in 0.15s.
  Fixtures cover symmetric BUY/SELL, exact indicator seeds, pivot delay, future-row
  non-repainting, warm-up, structure/trend/setup/stop WAIT paths, all BLOCK paths,
  scheduled/unexplained gaps, malformed/revised/cross-identity evidence and the
  no-I/O/AI/execution source boundary.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **828 tests passed** in 37.74s,
  repository secret scan PASS over 2,383 observed text files on Python 3.14.7.
- `SOCHRON_UV=... .venv/bin/python scripts/check-worker-package.py`: PASS for
  byte-identical wheel/sdist rebuild, exact packaged source and the clean installed
  recovery/startup oracles on uv 0.12.15. Evidence:
  `output/worker-package/e774566195514ea4a34944f8bfc41c22/result.json`.
- `bash scripts/with-local-docker.sh ... npm run check:compose:local`: PASS with API
  image `sha256:1e3d6ee5ab0ed8de91dc6c51ef8e5bc7fa9f57e5d4922c8ae255bb2eebe05cca`,
  web image `sha256:bd230d170ec17c4eefe91e5eb2c62edd11a8299924f80ee68c139720be37736c`
  and SQLite 3.53.4 source/linkage admission. Evidence:
  `output/compose/sochron-verify-30cc890103fd/result.json`.
- `.venv/bin/python scripts/check-container-python.py
  sochron-verify-30cc890103fd-api:local`: PASS for the exact candidate-derived image,
  including PA01 tests. Evidence:
  `output/container-python/sochron-python-0aab133a4288/result.json`.

## Evidence limits and next boundary

The indicator checks prove only the committed Sochron initialization and synthetic
Decimal fixtures. External/MT5 indicator parity, real feed/aggregation semantics,
session calendar classification, news integration and data provenance are
**UNKNOWN**. No strategy edge, probability, fill or outcome is implied.

The next implementation boundary is deterministic M1-to-M5/H1 aggregation plus a
durable scheduled producer that atomically records the feature snapshot and signal
through the already owner-scoped schema. Until that exists, `/api/owner/signals`
correctly remains `awaiting_source`. Research backtests, chronological
train/tune/test splits, cost sensitivity and OOS/shadow evidence follow separately.
Overall Demo release readiness remains **BLOCKED**.
