# SCN-034 provider-neutral API budget verification

## Candidate

- Base revision before commit: `e803ba1d05d500d7e73dd1b94ee1be3c42d0ec76`
- Candidate state during verification: dirty working tree containing only the
  scoped SCN-034 API-budget reader, alert/UI integration, tests and documentation
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0, uv 0.12.15 for
  artifact verification, Docker 29.5.2, Chromium 153.0.8010.12
- Evidence type: local/synthetic only; no provider credential/API, current bill,
  hosted write, notification destination, MT5 operation or target deployment

## Outcome

SCN-034 AC-01 through AC-06 pass for local and synthetic evidence. An explicitly
configured query-only source validates one owner-private normalized provider-cost
snapshot and reports exact billed, unbilled estimate, total, remaining amount and
owner thresholds at `GET /owner/api-budget`. `GET /owner/alerts` v3 embeds that
coherent view, emits threshold/source-health facts and exposes both browser routes.

The production UI renders a compact budget ledger below alert coverage and above
lifecycle events. It displays the current source state, exact amounts, period,
UTC/Asia-Bangkok coverage time and redacted source reference. The signed-out
coverage map still shows where the provider collector must connect. No provider
collector or external delivery is claimed. Auto Trading and execution readiness
remain false, and the SCN-031 recovery/observability gate remains `not_run`.

## Verification run on 2026-09-20

- Focused Ruff plus Python budget/alert/API checks — PASS. The final focused budget
  suite has 10 tests covering disabled/awaiting, exact warning/critical/exhausted
  boundaries, owner authorization, lifecycle clear/resolve, stale/future/wrong
  currency, public permissions, hard links, symlink paths, oversized/duplicate JSON
  and non-string monetary configuration.
- Full `bash scripts/check-scn-001-local.sh` — PASS: 1,099 tests, Ruff and secret
  scan over 3,614 text files.
- `npx -y -p node@24.21.0 npm run check:web` — PASS: TypeScript, 209 tests,
  production build, responsive bundle and client-secret scan.
- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS.
- Guarded local Supabase plus `scripts/check-owner-browser.mjs` — PASS against the
  production build: owner/foreign authorization, strict v3 inventory, configured
  normalized budget warning, redaction, lifecycle behavior, API restart, logout,
  token refresh and 390px/320px containment. Evidence:
  `output/playwright/scn005-06ecf3a0-ed19-4e1e-bf9d-f976dba17ef8/result.json`.
  Desktop and mobile screenshots were visually inspected; the budget ledger is
  readable, correctly ordered and contained. The local stack was stopped and its
  generated credential directory removed afterward.
- Isolated Compose no-cache build/start/recreate — PASS with non-root/read-only
  boundaries, Demo-only health and persistent volume identity. Evidence:
  `output/compose/sochron-verify-3628e24d15fe/result.json`.
- Candidate API Linux image plus fixed-SQLite verifier — PASS, 1,034 affected tests.
  Evidence: `output/container-python/sochron-python-eff7b9b63eff/result.json`.
- Installed worker package verifier — PASS for byte-identical wheel, fresh
  non-editable install and recovery/default-off regressions. Evidence:
  `output/worker-package/64f19c0ecd4640c28d2fac78d1214c99/result.json`.
- Worker container verifier — PASS for installed wheel, default-disabled network,
  hardening and UNKNOWN/restart recovery. Evidence:
  `output/worker-container/sochron-worker-630a86640fe5/result.json`.

The first worker-package attempt stopped at the expected pinned-tool gate because
the user PATH supplied uv 0.12.17. No check was weakened and no lockfile was changed.
The verifier was rerun with an existing uv 0.12.15 binary and passed; failed-attempt
evidence is retained at
`output/worker-package/993117d9d5554d238b61c19f61ff84dd/result.json`.

## Acceptance mapping

- AC-01: default disabled behavior, exact private config, explicit decimal policy,
  canonical path and permission denial pass.
- AC-02: exact snapshot schema, period/time/currency constraints, bounded read,
  file identity checks and response redaction pass.
- AC-03: awaiting, connected, warning, critical, exhausted, stale and degraded
  derivation plus exact cost/remaining arithmetic pass.
- AC-04: owner route, no-store response, available coverage, threshold alerts,
  source-health facts and guarded lifecycle recovery pass.
- AC-05: strict browser parser, production rendering, UTC/Bangkok display, source
  reference, API location and mobile containment pass.
- AC-06: false delivery/execution flags and remaining external-delivery gap pass.

## Safety limits

- Provider selection, billing credential, collector, actual invoice reconciliation,
  taxes/credits/rate limits and delayed-charge accuracy: NOT IMPLEMENTED / NOT RUN.
- External alert outbox, destination, delivery receipt, retry and escalation: NOT
  IMPLEMENTED / NOT RUN.
- Target snapshot latency, disk/permission fault, backup/restore and operational
  cost review: NOT RUN.
- MT5 compilation, target recovery, broker Demo round trip and burn-in: NOT RUN and
  NOT AUTHORIZED.
- Release readiness, Auto Trading and unattended Demo: NOT ESTABLISHED and remain
  off.
