# SCN-030 PA01 tick-replay backtest verification

## Candidate

- Source revision before commit: `57749cd07cc3700584348f205c052d99ac9df657`
- Candidate state during verification: dirty working tree containing only the
  scoped SCN-030 replay, UI dependency wording and documentation changes
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0 and uv 0.12.15;
  disposable worker-container verification used the repository's pinned Linux
  image
- Evidence type: synthetic/local only; no hosted Supabase write, MT5 connection,
  broker action or non-synthetic market input

## Outcome

AC-01 through AC-12 pass for the retained synthetic fixtures. The installed
offline command reruns the pinned PA01 kernel at every eligible M5 boundary,
resolves executable entry and exit semantics from ordered Bid/Ask ticks, writes a
canonical SCN-029 bundle and performs no default or external work.

This is replay-mechanics evidence, not strategy-performance evidence. Historical
tick/bar acquisition, news/policy coverage, broker contract parity and selected
cost assumptions remain owner inputs. No non-synthetic replay artifact was
supplied, so the Statistics UI correctly remains `awaiting_source`; Auto Trading
remains off.

## Verification run on 2026-09-20

- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- Ruff plus `.venv/bin/python -m pytest -q tests/test_pa01_backtest.py` — PASS,
  19 tests.
- `bash scripts/check-scn-001-local.sh` — PASS, 1,074 Python tests and source
  secret scan.
- `npx -y -p node@24.21.0 npm run check:web` — PASS, type-check, 180 tests,
  production build and responsive bundle scan.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS, unchanged Supabase
  boundary guards and source secret scan.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS.
- Visual inspection of `http://127.0.0.1:5173` in Chrome — PASS for the
  unauthenticated fail-closed view, Statistics placement, `/api/owner/statistics`
  label and the PA01 replay-to-evaluation source chain. The intentionally absent
  local API was displayed as unavailable rather than replaced with fabricated
  data.
- `/Users/faztycoding/.cache/uv/archive-v0/9jK08udG19IeS9M8/bin/uv
  lock --check` — PASS with pinned uv 0.12.15.
- `SOCHRON_UV=/Users/faztycoding/.cache/uv/archive-v0/9jK08udG19IeS9M8/bin/uv
  .venv/bin/python scripts/check-worker-package.py` — PASS: byte-identical
  rebuild, fresh non-editable install, exact new entrypoint and inert no-action
  boundary. Evidence:
  `output/worker-package/bfab0b34fcd044ce888b2772e5cad8c1/result.json`.
- `SOCHRON_UV=/Users/faztycoding/.cache/uv/archive-v0/9jK08udG19IeS9M8/bin/uv
  bash scripts/with-local-docker.sh .venv/bin/python
  scripts/check-worker-container.py` — PASS: clean candidate image, installed
  wheel, runtime hardening and recovery regression. Evidence:
  `output/worker-container/sochron-worker-f233b729b31d/result.json`.

## Acceptance mapping

- AC-01 through AC-04: canonical parsing, exact UTC/decimal evidence, code/source
  hashes, complete boundary schedule, point-in-time bars and calls into the pinned
  PA01 kernel are covered by targeted parser, append-leakage and schedule tests.
- AC-05 through AC-08: BUY/SELL, next-tick fill, drift/expiry rejection,
  TP-first, SL-first, twelve-bar time exit, spread/cost decomposition and per-tick
  open-equity paths are covered by targeted replay/evaluator tests.
- AC-09 and AC-10: window-edge purge, inherited split/embargo validation,
  byte-stable bundle hashing and unchanged SCN-029 evaluation are covered by
  targeted tests and the complete Python regression.
- AC-11: reordered/duplicate/missing ticks, stale policy/H1 evidence, missing
  boundary coverage, OHLC disagreement, understated spread, cost/output overflow,
  private-path denial, create-once conflict and partial-file cleanup fail closed.
- AC-12: complete Python/web regression, secret scans, static database/container
  guards, installed wheel and disposable Linux worker-container checks pass in the
  recorded environment.

## Not run / not established

- Hosted Supabase publication or migration: NOT RUN.
- MT5, broker account, MetaEditor build or Demo order: NOT RUN.
- Non-synthetic historical ticks/bars/policy observations: NOT AVAILABLE and
  therefore NOT RUN.
- Real broker spread, slippage, commission, swap, point-value and volume parity:
  NOT ESTABLISHED.
- Strategy edge, promotion, execution enablement and Auto Trading: NOT AUTHORIZED
  and remain off.
- Release and deployment: NOT READY; this work unit supplies the offline replay
  producer and local evidence only.
