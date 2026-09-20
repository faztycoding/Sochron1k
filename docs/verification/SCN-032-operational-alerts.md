# SCN-032 operational alert inventory verification

## Candidate

- Source revision before commit: `b3e44d27479fa957d84b9cdf214e58a0a4ff9fc9`
- Candidate state during verification: dirty working tree containing only the
  scoped alert API/UI, connection-map, tests and documentation changes
- Environment: macOS arm64, Python 3.14.7 and Node.js 24.21.0
- Evidence type: synthetic/local only; no notification delivery, hosted write,
  MT5 connection, broker action, target deployment or target fault test

## Outcome

SCN-032 AC-01 through AC-07 pass for local and synthetic evidence. The owner UI
now shows eight fixed alert/source positions and obtains authenticated active
facts from a strict read-only route. The connection map contains the tenth node
for this partial capability. Journal references are redacted hashes; no route
acknowledges, resolves, sends or mutates an alert.

The response and browser keep Demo-only, Auto Trading off, execution not ready and
external delivery false. The SCN-031 recovery/observability gate remains `not_run`.

## Verification run on 2026-09-20

- Targeted Ruff — PASS for changed Python modules and tests.
- Targeted Python alert/evidence/history/Auth/API checks — PASS, 104 tests.
- Targeted TypeScript and component/parser checks — PASS, 46 tests.
- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- `bash scripts/check-scn-001-local.sh` — PASS, 1,083 Python tests and source
  secret scan over 3,340 text files.
- `npx -y -p node@24.21.0 npm run check:web` — PASS, TypeScript check, 197 tests,
  production build, responsive bundle and client-secret scan.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS; unchanged migrations,
  RPC and source-secret guards.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS; unchanged
  Demo-only, loopback and hardening assertions.
- Guarded local Supabase + `scripts/check-owner-browser.mjs` — PASS against the
  production build with Chromium 153.0.8010.12: owner Auth/RLS, ten-node map,
  eight alert coverage rows, strict owner response, missing delivery/budget state,
  foreign-owner denial, logout redaction, token refresh, 390px and 320px
  containment and generated-user cleanup. Evidence:
  `output/playwright/scn005-7d584f13-5b16-4670-9cb9-944a47d1d234/result.json`.
  The local stack was stopped after verification.
- Visual inspection of the retained desktop screenshot and a 390px alert-panel
  crop — PASS for the existing Charcoal/Gold hierarchy, readable source/API rows,
  explicit partial/missing states and absence of order/alert-mutation controls.
- `SOCHRON_UV=... .venv/bin/python scripts/check-worker-package.py` — PASS:
  byte-identical wheel, fresh non-editable install and recovery/default-off
  regressions. Evidence:
  `output/worker-package/30a93ca0559a4edb8f12721c25bd4bbd/result.json`.
- `SOCHRON_UV=... bash scripts/with-local-docker.sh .venv/bin/python
  scripts/check-worker-container.py` — PASS: installed wheel, default-disabled
  networking, runtime hardening and UNKNOWN/restart recovery. Evidence:
  `output/worker-container/sochron-worker-18a6e2f65940/result.json`.

## Acceptance mapping

- AC-01/AC-02: owner verification, no-store, method denial, literal safety flags,
  fixed ordered coverage and missing API-budget tests pass.
- AC-03: synthetic UNKNOWN/rejection, rejected-SL open volume, persistent risk
  halt and stale telemetry derive only their admitted kinds; private identifiers
  are absent.
- AC-04: archive thresholds share the existing non-destructive page-use read and
  have 70%/85% focused tests.
- AC-05: bounded deterministic journal facts, hashed references, UTC times,
  severity ordering and unavailable-source behavior pass focused tests.
- AC-06: the exact browser parser rejects flag, route, reference, field and order
  drift. Component and production-browser checks keep all API locations visible
  and contain the panel at 320px.
- AC-07: safety flags remain false and the existing readiness contract retains
  all target gates as unrun/unauthorized.

## Safety limits

- External delivery, durable acknowledgement/resolution and API-budget source:
  NOT IMPLEMENTED.
- Target restart/network loss, disk exhaustion, backup/restore and alert receipts:
  NOT RUN.
- Broker-side rejected-SL emergency response and Demo round trip: NOT RUN and NOT
  AUTHORIZED.
- Release readiness, Auto Trading and unattended Demo: NOT ESTABLISHED and remain
  off.
