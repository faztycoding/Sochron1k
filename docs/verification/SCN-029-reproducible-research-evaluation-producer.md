# SCN-029 reproducible research evaluation producer verification

## Candidate

- Source revision before commit: `1cc8c4eb52c80201389cf9ca34bb57433e840342`
- Candidate state during verification: dirty working tree containing only the
  scoped SCN-029 implementation and documentation changes
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0, Supabase CLI 2.117.0,
  uv 0.12.15, local PostgreSQL 17.6, PostgREST v16.2 and Chromium 153.0.8010.12
- Evidence type: synthetic/local only; no hosted Supabase write and no MT5 action

## Outcome

AC-01 through AC-12 pass for the supplied synthetic fixtures and guarded local
infrastructure. The producer is installed, disabled by default, computes a strict
deterministic envelope, journals before send, reconciles ambiguous writes, and
publishes through an owner-scoped backend-only receiver. The existing statistics
read model and UI render the resulting evaluation without recalculation.

This is implementation evidence, not strategy evidence. No non-synthetic labelled
bundle was supplied, so the Statistics UI correctly remains `awaiting_source` in a
normal empty environment. Strategy edge, representative execution costs, promotion,
Demo broker readiness, hosted deployment and unattended operation remain unproved.

## Verification run on 2026-09-20

- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- Targeted Ruff plus
  `.venv/bin/python -m pytest -q tests/test_research_evaluation_producer.py` —
  PASS, 19 tests.
- `bash scripts/check-scn-001-local.sh` — PASS, 1,055 Python tests plus source
  secret scan.
- `npx -y -p node@24.21.0 npm run check:web` — PASS, type-check, 180 tests,
  production build and responsive bundle scan.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS, migration/RPC guards
  and source secret scan.
- `SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh
  npx -y -p node@24.21.0 npm run check:db:local` — PASS: six migrations applied,
  public/private lint had no schema errors, advisor errors were absent, all 487
  pgTAP assertions passed, RLS mutation detection passed, and all three isolated
  forward-migration/concurrency verifiers passed with observed lock overlap.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 .venv/bin/python
  scripts/check-native-sync-local.py` — PASS against actual local Auth, PostgREST
  and PostgreSQL; synthetic fixtures were removed.
- `env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node
  scripts/check-owner-browser.mjs` — PASS: production UI/API/Auth browser flow,
  owner research evaluation RLS, uncertainty/cost display, panel placement,
  320 px containment, failure recovery and cleanup.
- `SOCHRON_UV=/tmp/sochron-uv.usMfM9/bin/uv .venv/bin/python
  scripts/check-worker-package.py` — PASS: byte-identical rebuild, fresh
  non-editable install and disabled research command. Evidence:
  `output/worker-package/b38c709b78134905ab8c1894c11bcaf7/result.json`.
- `bash scripts/with-local-docker.sh .venv/bin/python
  scripts/check-worker-container.py` — PASS: clean candidate image, installed
  wheel, runtime hardening and restart/UNKNOWN recovery. Evidence:
  `output/worker-container/sochron-worker-cbf894a149c6/result.json`.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS.
- Visual inspection of `http://127.0.0.1:5173` in the in-app browser — PASS for
  the unauthenticated fail-closed state, API connection map, Statistics placement,
  Demo-only badge and Auto Trading off state. The missing local API was visible as
  unavailable rather than replaced with fabricated data.

## Acceptance mapping

- AC-01 through AC-07: strict parser, canonical hashing, temporal/cost/equity
  validation, deterministic bootstrap and SCN-017 compatibility are covered by
  the 19 targeted tests and owner-browser projection.
- AC-08 and AC-11: SQLite state transitions, binding, lock contention, corruption,
  lost response, bounded retry and conflict quarantine are covered by targeted,
  package and container checks.
- AC-09 and AC-10: migration lint, 55 SCN-029 pgTAP assertions, the isolated
  two-session lock-overlap verifier and existing owner-browser/RLS checks pass.
- AC-12: wheel, container, web, local database and regression suites pass in the
  recorded environment.

## Not run / not established

- Hosted Supabase migration or write: NOT RUN.
- MT5, broker account, MetaEditor build or Demo order: NOT RUN.
- Non-synthetic market dataset, setup labeller or raw-bar PA01 backtest: NOT
  AVAILABLE and therefore NOT RUN.
- Strategy promotion, execution enablement and Auto Trading: NOT AUTHORIZED and
  remain off.
- Release and deployment: NOT READY; this work unit supplies the evaluation
  producer and local evidence only.
