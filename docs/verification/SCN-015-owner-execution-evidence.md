# SCN-015 Owner execution evidence read model

2026-09-20; base `382bb9b996b8f446ec6d93d69f585755d1045376`, dirty
candidate inputs. The containing commit identifies delivery. macOS 26.6.2 arm64,
Python 3.14.7, SQLite 3.53.1 locally, Node.js 24.21.0, pytest 9.1.1,
Vitest 5.0.1, Playwright 1.63.0 and Chromium 153.0.8010.12.

## Outcome and acceptance status

The authenticated owner workspace now includes a read-only execution evidence
panel after chart/history. Its browser route is `/api/owner/execution`; the API
route is `/owner/execution`. It renders journal-confirmed Command, Order, Deal,
Position, cumulative fill/pending/cancel/close volume, rejection and broker-side
SL evidence. `UNKNOWN`, partial fill and unconfirmed SL remain explicit. There is
no order, retry, halt-release or Auto Trading control.

The API defaults to `disabled/not_configured`. An operator may configure only an
existing canonical, private SQLite journal through
`SOCHRON_EXECUTION_JOURNAL_PATH`. The reader pins file identity, opens query-only,
uses immutable mode when no WAL frames exist, disables checkpoint-on-close for
live WAL reads, validates integrity/schema/evidence, bounds the latest projection
to 50 commands, and returns a redacted unavailable view after replacement or
invalid evidence. It never creates a journal or constructs ExecutionService.

SCN-015 AC-01 through AC-09 pass for local API/UI, synthetic journals and
container scope. Actual MT5, MetaEditor, target-host journal sharing, broker-side
SL, hosted Supabase, deployment and a Demo round trip remain `NOT RUN`. Public
`execution_ready=false` and Auto Trading remains off.

## Baseline and negative evidence

The acceptance contract was added to the candidate before behavior code.
Against archived base `382bb9b`, an isolated ASGI request to
`GET /owner/execution` returned `404 {"detail":"Not Found"}`. The first combined
targeted run after implementation passed the new execution tests and failed the
older SCN-014 map expectation because execution had correctly changed from
`partial` to `available`; that expectation was then updated with the exact two
routes.

Negative fixtures cover missing and duplicate authorization, disabled config,
group/world-readable files, symlinks, inode replacement, missing schema, malformed
stored evidence, deterministic 50-command bounds, clean immutable reads and
live-WAL no-checkpoint behavior. Reads preserve database/WAL bytes and metadata;
SQLite shared-memory lock bytes are intentionally excluded because they coordinate
live readers.

## Verification

- `.venv/bin/python -m pytest tests/test_execution_evidence.py tests/test_owner_auth.py tests/test_api_safety.py -q`:
  **72 passed** in 5.64s.
- `npx -y -p node@24.21.0 npm run check:web`: typecheck PASS, **10 files /
  152 tests passed**, production build PASS and client-bundle secret scan PASS.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **770 tests passed** in
  35.23s, repository secret scan PASS over 2,073 observed text files on Python
  3.14.7.
- `SOCHRON_UV=... .venv/bin/python scripts/check-worker-package.py`: PASS for
  byte-identical wheel, fresh non-editable install and existing recovery/startup
  oracles. Evidence:
  `output/worker-package/8bddd1a71a594316b901817a073c39e5/result.json`.
- `bash scripts/with-local-docker.sh ... npm run check:compose:local`: PASS with
  API image `sha256:e19f1b1a260d46f61e0671acad517ae28d3ef8944b2f1964781395ec48b705b0`,
  web image `sha256:0dfe2c59afc740c2a660f212be445c35dc359d14163d42f5fb0537b62027d6a2`
  and container SQLite 3.53.4 source/linkage admission. Evidence:
  `output/compose/sochron-verify-2113395491c4/result.json`.
- `scripts/check-container-python.py sochron-verify-2113395491c4-api:local`:
  PASS for the affected Python suite inside a candidate-derived Linux image.
  Evidence: `output/container-python/sochron-python-a10bcedc9f52/result.json`.
- `env -u DEBUG ... node scripts/check-owner-browser.mjs`: PASS with real local
  Auth/API, synthetic telemetry/OHLC/execution journal, confirmed SL projection,
  two-owner denial, session refresh/revocation, desktop/mobile screenshots and
  320 px containment. Final artifact:
  `output/playwright/scn005-8fa89132-e409-4ef0-83e8-05e64c0a5f7c/result.json`;
  production build SHA-256
  `9ef88ce1ffc4fef089e7f417f4890e63fb2ebc6dfbd9751850d578dac29a6d65`.
- `bash scripts/check-project-baseline.sh`,
  `python3 scripts/check-agent-skills.py`, static Supabase/Compose checks and
  `git diff --check`: PASS.

The initial installed-package invocation stopped before testing because uv 0.12.15
was absent from PATH. A pinned macOS wheel was unpacked into a temporary directory,
its version was verified, and the verifier passed without changing global PATH.
The first container-Python invocation used the image digest as a Dockerfile `FROM`
name and therefore attempted an unauthorized registry pull; rerunning the exact
local image through its tag passed. The first expanded browser attempt stopped at
the owner-login stage with cleanup PASS; the source-bound final rerun above passed.
These prerequisite/invocation failures are not relabelled as product passes.

## Evidence limits and next safe action

The browser screenshots demonstrate layout and strict synthetic evidence only.
They do not prove MT5 facts. To populate this panel on a real Demo target, the
ExecutionService writer and API reader must share the exact admitted private
journal mount, and the MQL5 mutation EA must still be implemented, compiled and
verified against the selected Demo account.

The remaining missing browser APIs are `/api/owner/signals` and
`/api/owner/statistics`. Their sources and evaluation contracts must be built
without allowing strategy or AI output to bypass deterministic risk/execution
gates.
