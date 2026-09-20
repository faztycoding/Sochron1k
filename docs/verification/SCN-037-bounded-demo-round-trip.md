# SCN-037 bounded Demo round-trip admission verification

## Candidate

- Base revision before commit: `1c55fbe0ada4e6c9a37ebbb72a3925dceec29a74`
- Candidate state during verification: dirty working tree containing only the
  scoped SCN-037 controller/API, create-only risk initialization, readiness/UI
  mapping, tests, operations guidance and decision/contract evidence
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0, uv 0.12.15,
  Playwright 1.63.0 and Firefox 155.0
- Evidence type: local/synthetic only; no VPS/Windows target, Docker engine,
  local/hosted Supabase, MetaEditor compile, MT5 terminal, broker operation,
  credential, provider, paid resource or deployment

## Outcome

SCN-037 AC-01 through AC-09 pass for the local implementation and simulator
boundary. The API can now construct the existing `ExecutionService` only when one
owner-private authorization matches the exact deployed source revision, owner
decision, Demo identity, experiment/signal/strategy, risk baseline/cost floor and
fixed entry/cancel/close command identifiers.

The controller initializes risk state create-only from fresh complete empty Demo
inventory, requires explicit startup reconciliation and delegates mutation and
query behavior to the already verified journal/service/bridge. New entry expires;
cancel, close and reconcile remain available so an expiry or halt cannot strand
confirmed exposure. Timeout-after-effect remains `UNKNOWN`, and reconciliation
does not resend.

The web remains query-only. Connection/readiness rows show
`/api/internal/v1/demo-round-trip/status`, while nginx continues to reject browser
`/api/internal/` requests. Public execution readiness, Auto Trading, release
readiness, round-trip authorization and unattended readiness remain false.

## Verification run on 2026-09-20

- Focused Ruff plus SCN-037/readiness/API/target tests — PASS: 24 tests.
- Final `bash scripts/check-scn-001-local.sh` — PASS: Ruff, 1,135 Python tests and
  source secret scan over 4,743 text files.
- `npx -y -p node@24.21.0 npm run check:web` — PASS: TypeScript, 215 tests,
  production build, responsive checks and client-secret scan.
- `bash scripts/check-project-baseline.sh` and
  `python3 scripts/check-agent-skills.py` — PASS; the skill check is integrity
  inventory only.
- `npx -y -p node@24.21.0 npm run check:db:static` and
  `npm run check:compose:static` — PASS. Compose remains Demo-only, non-root,
  read-only and browser ingress still blocks the complete `/api/internal/` prefix.
- Installed package verifier — PASS with pinned uv 0.12.15: byte-identical build,
  fresh non-editable install, inert defaults and recovery/startup/query-only
  execution oracles. Evidence:
  `output/worker-package/23064bc9a67a46f79e673beab29acc14/result.json`.
- Real-browser Firefox inspection at desktop 1280 px and mobile 390 px — PASS:
  both connection/readiness rows display the exact internal status route and
  source, safety banner/Auto Trading-off remain visible, no order control appears,
  and the console contains zero errors. Screenshots:
  `output/playwright/scn037/readiness-desktop.png` and
  `output/playwright/scn037/readiness-mobile.png`.

The first package-verifier invocation stopped before build because uv 0.12.15 was
not on `PATH`; rerunning with the existing pinned absolute executable passed. The
Playwright CLI first requested unavailable Google Chrome; the same installed CLI
workflow passed with pinned Firefox. No test, assertion, timeout or gate was
weakened.

The guarded native-sync verifier stopped before checks because local Supabase was
not running. Docker is absent from this workstation's PATH, so native-sync,
worker-container, candidate Linux-image and Compose runtime verification are
`NOT RUN` for this candidate. Static Compose and database checks passed, but they
do not replace those runtime checks.

## Acceptance mapping

- AC-01: private/canonical config, credential separation, identity/decision/source
  binding, fixed distinct IDs, bounded authorization window and invalid-config
  denial pass.
- AC-02: fresh empty Demo inventory, create-only baseline, exact experiment
  capital, replay, mismatch and halt-preservation tests pass.
- AC-03: explicit startup and unavailable/stale/missing state denial reuse the
  existing inventory/generation/risk reconciliation checks.
- AC-04: exact entry/signal/strategy binding, entry expiry, minimum cost floor,
  deterministic sizing, durable authorization and duplicate replay pass locally.
- AC-05: cancel-before-close, journal-derived volumes/identifiers, expired-entry
  management and close-while-halted pass.
- AC-06: timeout-after-acceptance becomes `UNKNOWN`; query-only reconcile resolves
  without increasing simulator send count.
- AC-07: separate bearer authentication, sync FastAPI handlers, strict Pydantic
  bodies and browser-ingress denial pass.
- AC-08: strict Python/TypeScript connection and readiness contracts plus desktop/
  mobile rendering show the exact API position with every public safety flag false.
- AC-09: focused/full/package/static/browser negative and recovery checks pass;
  missing Docker/target checks remain explicitly unpassed.

## Safety limits and remaining inputs

- MetaEditor compile, artifact identity, exact target host/network and denied-live
  evidence: `NOT RUN`.
- Demo broker account/server/symbol/contract parity, order/deal/position/close and
  broker-side SL confirmation: `NOT RUN` and not authorized.
- Target restart/network loss, journal/storage failure, rejected-SL emergency,
  alert receipt, backup/restore, latency p50/p95 and multi-market-day burn-in:
  `NOT RUN`.
- Daily risk rollover with cash-flow evidence and total-halt release into a new
  experiment remain unimplemented.
- An unattended signal-to-command dispatcher remains unimplemented. This boundary
  authorizes only one separately reviewed test lifecycle.
- The owner must still supply the reviewed target decision record, Demo credentials
  through the approved secret channel, exact deployed revision, separate service
  tokens, fixed experiment/signal/command identifiers, minimum cost assumption and
  explicit authorization before any actual bounded Demo operation.
