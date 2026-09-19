# SCN-017 owner research statistics verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`9ea2b784f2f483c6d4b806751f25a4302a76d833`; the final commit and remote revision
are recorded after this document is committed.

AC-01 through AC-10 in the
[task contract](../contracts/SCN-017-owner-research-statistics.md) pass for the
local read-model scope. The API and browser display only validated existing
evaluation evidence after online owner verification. Empty evaluation data remains
`awaiting_source`. No research producer, hosted write, MT5 operation, strategy
promotion or deployment was run.

## Implemented scope

- Added owner route `/owner/statistics` and browser route
  `/api/owner/statistics` over the existing owner-RLS `evaluations`, embedded
  `strategy_versions` and optional `experiments` relations.
- Bounded one upstream GET to 30 rows/256 KiB, deterministic ordering and strict
  owner, identity, temporal, metric, uncertainty and cost validation.
- Derived win rate from validated outcome counts; exposed sample size, expectancy
  with 95% interval, net return, maximum drawdown, profit factor and every required
  cost assumption without raw JSON or database IDs.
- Added a responsive statistics panel after signal evidence and before bar history,
  plus desktop/mobile navigation and the redacted API connection map.
- Extended the real local browser verifier with two owner-isolated synthetic
  evaluations and exact cleanup.

## Verification

- `.venv/bin/python -m pytest tests/test_research_statistics.py
  tests/test_signal_evidence.py tests/test_owner_auth.py tests/test_api_safety.py -q`:
  **98 passed** in 5.75s.
- `npx -y -p node@24.21.0 npm run check:web`: typecheck PASS, **14 files /
  180 tests passed**, production build PASS and client-bundle secret scan PASS.
- `bash scripts/check-scn-001-local.sh`: prescribed Ruff PASS, **806 tests passed**
  in 37.93s, secret scan PASS over 2,305 observed text files on Python 3.14.7.
- `.venv/bin/ruff check .`: the first broader-than-prescribed run found one existing
  102-character output line in `scripts/check-agent-skills.py`. The line was wrapped
  without changing behavior; the complete rerun passed.
- `npx -y -p node@24.21.0 npm run check:db:static` and
  `npm run check:compose:static`: PASS, including exact static schema/topology and
  secret checks.
- Guarded `SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k ... npm run check:db:local`:
  PASS after three migrations, schema lint, advisors, **380 pgTAP tests**, exact
  restored-policy mutation evidence with 271 checks, forward migration and native
  concurrency fixtures. Advisor output contained only existing unused-index INFO
  findings. The stack was stopped after browser verification.
- `env -u DEBUG ... node scripts/check-owner-browser.mjs`: PASS against real local
  Auth/PostgREST with two generated users, direct evaluation RLS isolation, exact
  metrics/cost projection, chart-before-signal-before-statistics-before-history
  placement, production desktop/mobile rendering, 320 px containment,
  refresh/revocation and fixture cleanup. Artifact:
  `output/playwright/scn005-a6c1a7bb-ac4b-403b-9df8-11e66f43f619/result.json`;
  production build SHA-256
  `916e374cb5f15382a2bf6fd1c740e37e45c2886448779cf6a8ffd07fd96d53a6`.
- Manual visual inspection of that run's production desktop/mobile screenshots:
  PASS; the statistics card remains contained and legible, its four metrics stack
  at mobile width and the fixed navigation exposes Statistics.
- `SOCHRON_UV=... .venv/bin/python scripts/check-worker-package.py`: PASS for the
  byte-identical build, clean non-editable install and existing recovery/startup
  oracles on uv 0.12.15. Evidence:
  `output/worker-package/4d8c45b43b77453696a685c7e0c8e14f/result.json`.
- `bash scripts/with-local-docker.sh ... npm run check:compose:local`: PASS with API
  image `sha256:23be0397c6996a9ce3d945cdc325841ae68c03739a71f561b4139053ed69305e`,
  web image `sha256:4dfe092579ee61076166d25d51dab8af8f8239adc24fdbf43534ff42e9084fb8`
  and container SQLite 3.53.4 source/linkage admission. Evidence:
  `output/compose/sochron-verify-e1687c609947/result.json`.
- `.venv/bin/python scripts/check-container-python.py
  sochron-verify-e1687c609947-api:local`: PASS for the exact candidate-derived API
  image. Evidence:
  `output/container-python/sochron-python-8011bd19431d/result.json`.

## Evidence limits and release state

The synthetic evaluation proves RLS, validation, serialization and UI behavior;
it is not a PA01 result and carries no profitability claim. The research producer,
dataset provenance/licensing, temporal leakage tests, feature parity, cost
calibration and reproducible evaluation remain unimplemented or unverified.
Hosted Supabase, an actual MT5 Demo terminal, MQL5 mutation, VPS deployment and
unattended burn-in are **NOT RUN**. Implementation is complete for SCN-017; overall
Demo release readiness remains **BLOCKED** by those separate gates and required
owner/broker/target inputs.
