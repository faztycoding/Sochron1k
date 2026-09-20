# SCN-019 native PA01 aggregation verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`4b829c0ff6ce25ce13b98ad6be263663faac2d98`. The retained package/container
reports record that base revision and `dirty=true`; the delivery report binds the
final commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-019-native-pa01-aggregation.md) pass for the pure
local aggregation boundary. No Supabase source query/write, scheduler, durable
producer journal, feature/signal persistence, hosted service, MT5 operation,
command, risk admission or deployment was run.

## Implemented scope

- Added a packaged `native-pa01-aggregation-v1` pure model and function for one
  bounded immutable `native-v1` archive at an explicit cutoff.
- Added exact native M1 timing/grid/provenance validation, including broker offset
  validity intervals and revalidation of already-instantiated inputs.
- Aggregated only complete five-minute and broker-hour buckets; incomplete/gapped
  buckets are absent and receive no invented price or market-close classification.
- Preserved the latest child availability and stable archive/time identity, plus
  exact child revision, source-dataset and output hashes.
- Strengthened PA01 closed-bar alignment and gap detection to use broker server time
  while retaining exact derived UTC time, including non-whole-hour UTC offsets;
  advanced the parameter/evidence contract to `PA01-v1.0.1` so its hash cannot be
  confused with the earlier UTC-inferred schema.
- Kept order creation and risk admission hard-coded false.

## Acceptance evidence

- **AC-01:** malformed Decimal/time/grid/basis/validity fixtures, duplicate server
  times, forged model copies and mixed archive/symbol/offset/grid rows fail closed.
- **AC-02:** a `+05:30` fixture produces an H1 bar aligned on broker hour and UTC
  half-hour; the strengthened SCN-018 model accepts the exact relationship.
- **AC-03:** one missing minute removes its M5 and H1 buckets. OHLC and aggregate
  availability equal the exact children; no fabricated row is emitted.
- **AC-04:** later availability is excluded and appending future rows leaves the
  earlier complete result, counts and hashes unchanged.
- **AC-05:** replay is byte-model deterministic; a changed valid child retains the
  bucket identity but changes child revision, dataset and output hashes.
- **AC-06:** 720 native M1 fixtures produce bounded 100 M5/12 H1 inputs accepted by
  `evaluate_pa01`; an internal missing minute results in `BLOCK/DATA_GAP`.
- **AC-07:** source guards and behavioral tests verify no filesystem/database/HTTP,
  current-clock, AI, command, risk or executor authority.
- **AC-08:** full local, installed artifact, Compose and exact Linux candidate gates
  pass as recorded below.

## Verification run

- `.venv/bin/python -m pytest -q tests/test_pa01.py
  tests/test_pa01_aggregation.py`: **44 passed** in 0.26s.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **850 tests passed** in 37.65s,
  repository secret scan PASS over 2,541 observed text files on Python 3.14.7.
- `SOCHRON_UV=/tmp/sochron-uv.pLqxNq/venv/bin/uv .venv/bin/python
  scripts/check-worker-package.py`: PASS on uv 0.12.15 for exact wheel/sdist source,
  byte-identical rebuild and clean non-editable installation. Evidence:
  `output/worker-package/1e09a48547cf44c49641b6ed4e224a37/result.json`.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run
  check:compose:local`: PASS with API image
  `sha256:15292a4c2786234d5f2009e0cf9454a76570c62696c2c16a690e9a3a4e320869`,
  web image
  `sha256:cf466e43a4e239c9b19fe8c18806111e740e0459d35af1a9e3acca0f618dd9ed`
  and fixed SQLite 3.53.4 source/linkage admission. Evidence:
  `output/compose/sochron-verify-159346877a28/result.json`.
- `SOCHRON_UV=/tmp/sochron-uv.pLqxNq/venv/bin/uv bash
  scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py
  sochron-verify-159346877a28-api:local`: PASS for the exact candidate-derived image,
  including the new module/tests and **795 passed** Linux-compatible tests. Evidence:
  `output/container-python/sochron-python-a6182c836bd1/result.json`.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`,
  `.venv/bin/ruff check .` and `git diff --check`: PASS.

## Evidence limits and next boundary

The fixtures prove only deterministic local aggregation and PA01 handoff. They do
not prove actual broker candle/indicator parity, a market-session calendar, running
source reads, producer uptime, atomic persistence, historical performance, a
strategy edge, target-host behavior or Demo execution.

`/api/owner/signals` therefore correctly remains `awaiting_source`. The next safe
boundary is a bounded owner/archive source reader plus a durable scheduled producer
that records an immutable feature snapshot and signal atomically, journals UNKNOWN
writes and reconciles by read-back before retry. Evaluation/backtest/OOS evidence
and the owner/MT5/VPS release inputs remain separate unfinished gates.
