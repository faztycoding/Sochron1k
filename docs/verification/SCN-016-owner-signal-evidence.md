# SCN-016 Owner signal evidence

2026-09-20; base `18cb6dbefc8051b0e7da9f003e5b9a70b230bdfe`, dirty
candidate inputs. The containing commit identifies delivery. macOS 26.6.2 arm64,
Python 3.14.7, Node.js 24.21.0, Supabase CLI 2.117.0, pytest 9.1.1,
Vitest 5.0.1, Playwright 1.63.0 and Chromium 153.0.8010.12.

## Outcome and acceptance status

The authenticated owner workspace now places a read-only signal panel immediately
after the chart and before closed-bar history. Its browser route is
`/api/owner/signals`; the API route is `/owner/signals`. It displays the exact
stored BUY, SELL, WAIT or BLOCK action plus setup/version/experiment evidence,
formed/confirmed/expiry/data-cutoff times in UTC and Bangkok, evidence IDs and
active/expired state. It has no order, promotion, risk, halt-release or Auto
Trading control.

FastAPI performs the existing online owner/session verification, then makes one
bounded GET to the same configured Supabase origin with the verified user's token
and unprivileged project key. Existing forced RLS scopes the joined `signals`,
`experiments`, and `strategy_versions` rows. The API independently verifies all
nested owner IDs, causal timestamps, statuses, hashes, order and uniqueness, then
removes owner UUIDs/internal keys. Empty rows are `awaiting_source`; they are not a
synthetic WAIT.

SCN-016 AC-01 through AC-10 pass for local API/UI, real local Auth/PostgREST/RLS,
synthetic signal evidence and container scope. PA01/SMC01/ICT01 production,
feature parity, strategy promotion, actual MT5, hosted Supabase, deployment and a
Demo round trip remain `NOT RUN`. Public `execution_ready=false` and Auto Trading
remain off.

## Baseline and negative evidence

The acceptance contract and ADR were written before behavior code. Static
inspection of archived base `18cb6db` confirms `owner_api.py` had no `/signals`
route. The existing SCN-014 map therefore identified `/api/owner/signals` as
missing before this increment.

Negative tests cover missing/duplicate/foreign authorization through the shared
owner verifier, owner mismatch at the root and both embedded relations, invalid
formed/confirmed/expiry/data-cutoff ordering, duplicate evidence and signal IDs,
non-hex code hash, action/reason conflicts, wrong ordering, more than 50 rows,
oversized/non-JSON/error upstream responses, extra client fields, unsafe readiness
and malformed collection counts. Earlier displayed rows are cleared on failure.

## Verification

- `.venv/bin/python -m pytest tests/test_signal_evidence.py tests/test_owner_auth.py tests/test_api_safety.py -q`:
  **79 passed** in 5.55s.
- `npx -y -p node@24.21.0 npm run check:web`: typecheck PASS, **12 files /
  166 tests passed**, production build PASS and client-bundle secret scan PASS.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **787 tests passed** in
  36.92s, repository secret scan PASS over 2,153 observed text files on Python
  3.14.7.
- `npx -y -p node@24.21.0 npm run check:db:static` and
  `npm run check:compose:static`: PASS, including secret scan and exact static
  topology/schema guards.
- Guarded `SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k ... npm run check:db:local`:
  PASS after applying all three migrations, schema lint, advisors, **380 pgTAP
  tests**, mutation fixture with exact restored policy and 271 checks, forward
  migration and native concurrency fixtures. Advisor output contained only the
  existing unused-index INFO findings. The local stack was stopped afterwards.
- `SOCHRON_UV=... .venv/bin/python scripts/check-worker-package.py`: PASS for
  byte-identical build, fresh non-editable install and existing recovery/startup
  oracles on uv 0.12.15. Evidence:
  `output/worker-package/818c3455651b4b799e06c0adf50d3bf3/result.json`.
- `bash scripts/with-local-docker.sh ... npm run check:compose:local`: PASS with
  API image `sha256:d01fecb4c88f2d7983c15a84993adcf205d3ca5ba32a66deb44968e4f9ec7cb3`,
  web image `sha256:afc64fe00bfde3bdf65ede1aaf76818a6f8db9c62847a6cd0f7d5ff1bf1786dd`
  and container SQLite 3.53.4 source/linkage admission. Evidence:
  `output/compose/sochron-verify-d20a078fd2d9/result.json`.
- `scripts/check-container-python.py sochron-verify-d20a078fd2d9-api:local`:
  final PASS, **732 tests** in 21.52s against the exact API image. Evidence:
  `output/container-python/sochron-python-1f90ca0b24c1/result.json`.
- `env -u DEBUG ... node scripts/check-owner-browser.mjs`: PASS with real local
  Auth/PostgREST, two generated users, direct RLS row isolation, exact embedded
  signal projection, chart-before-signal-before-history placement, production
  desktop/mobile rendering, 320 px containment, refresh/revocation and fixture
  cleanup. Artifact:
  `output/playwright/scn005-4714dabd-b10b-454c-a72c-746b2c8500fa/result.json`;
  production build SHA-256
  `75ec39ce78f4170754a7d8c141609801e8cbd4f0c1d34e98ed787a7dbec45532`.

The first container-Python run recorded one failure in the pre-existing exhausted
sync-budget recovery audit after 731 passes:
`output/container-python/sochron-python-df32fef614fc/result.json`. Without a code,
test or timeout change, the exact failed case then passed in the same test image,
and the complete verifier rerun above passed. The initial failure is retained and
is not relabelled as a pass.

## Evidence limits and next safe action

The browser fixture proves the reader/RLS/UI boundary, not that a strategy has an
edge or that PA01 rules were calculated. A real Demo source still requires a
versioned producer using only closed, available bars; immutable feature snapshots;
temporal leakage/repaint tests; source/feed hashes; reviewed experiment status; and
promotion evidence. Signal display never bypasses deterministic risk, journal,
executor or MT5 confirmation.

The remaining missing browser API is `/api/owner/statistics`. Its result must be
derived from closed setup-to-flat outcomes with costs, sample size, uncertainty and
explicit insufficient-evidence states, without turning a high win rate into release
authority.
