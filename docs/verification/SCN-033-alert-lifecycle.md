# SCN-033 durable alert lifecycle verification

## Candidate

- Source revision before commit: `520adab85eaeba876e35831dfbc5755558a31d75`
- Candidate state during verification: dirty working tree containing only the
  scoped lifecycle API/UI, connection-map, tests and documentation changes
- Environment: macOS arm64, Python 3.14.7, SQLite 3.53.1, Node.js 24.21.0,
  uv 0.12.15 and Chromium 153.0.8010.12
- Evidence type: synthetic/local only; no external notification, hosted write,
  MT5 connection, broker action, target deployment or target fault test

## Outcome

SCN-033 AC-01 through AC-06 pass for local and synthetic evidence. The owner can
acknowledge an active alert through one idempotent mutation and resolve the local
workflow only when the contract admits it. The private SQLite record and exact
mutation receipt survive API restart. A continuing stale-price condition is
rejected for resolution; after current telemetry returns, the retained episode is
shown as cleared and can be resolved. A later observation becomes active again.

The strict v2 inventory distinguishes active, acknowledged, cleared, resolved and
unavailable states. The UI keeps UTC and Bangkok display times separate and shows
all read/acknowledge/resolve API locations. External delivery, Auto Trading and
execution readiness remain false. The SCN-031 recovery/observability gate remains
`not_run`.

## Verification run on 2026-09-20

- Targeted Ruff and Python lifecycle/API checks — PASS, 8 tests. Cases include
  owner authorization, missing/duplicate idempotency key, exact replay, key
  conflict, active-condition denial, clear/resolve, restart, recurrence,
  owner isolation, replacement, corruption, clock regression, lock contention,
  private/canonical path denial and bounded-history retention.
- Full local Python suite through `bash scripts/check-scn-001-local.sh` — PASS,
  1,089 tests plus source secret scan over 3,481 text files.
- `npx -y -p node@24.21.0 npm run check:web` — PASS, TypeScript, 204 tests,
  production build, responsive bundle and client-secret scan.
- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS after the guarded
  local Supabase stack was stopped and its generated credential directory removed.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS with Demo-only,
  loopback, hardening and source-secret guards.
- Guarded local Supabase plus `scripts/check-owner-browser.mjs` — PASS against the
  production build: owner/foreign authorization, strict v2 response, three alert
  API positions, durable acknowledgement, no resolve control while active,
  resolution after source recovery, restart retention, logout redaction, token
  refresh and 390px/320px containment. Evidence:
  `output/playwright/scn005-6bf52f87-0f6a-482e-9556-b18e2b66f548/result.json`.
  The stack was stopped afterward.
- Retained desktop and mobile screenshots — visually inspected; PASS for
  Charcoal/Gold hierarchy, distinct lifecycle state, readable API/source rows and
  contained mobile layout.
- Installed worker package verifier — PASS for byte-identical wheel, fresh
  non-editable install and recovery/default-off regressions. Evidence:
  `output/worker-package/5ec8db14eeaf43068a3fda952de729e7/result.json`.
- Worker container verifier — PASS for installed wheel, default-disabled network,
  runtime hardening and UNKNOWN/restart recovery. Evidence:
  `output/worker-container/sochron-worker-f432f4e2b964/result.json`.
- Candidate API Linux image build and Python/SQLite verifier — PASS with pinned
  fixed SQLite source/linkage and the affected Python suite. Evidence:
  `output/container-python/sochron-python-8a28258a3e96/result.json`.

The first final static scan attempt correctly rejected Supabase CLI-generated
credential files while the guarded local stack was running. The stack was stopped,
the generated directory disappeared, and both static scans passed. An earlier
browser attempt found an exact-text assertion that still expected the SCN-032
heading; the verifier was updated to the v2 lifecycle heading and the complete
browser flow then passed three times.

## Acceptance mapping

- AC-01: owner verification, no-store, strict headers, disabled behavior and
  canonical private directory denial pass.
- AC-02: schema/integrity/file-identity checks, WAL/full synchronization, page
  limit, atomic receipt/transition, restart, corruption, lock and clock failures
  pass local tests; target durability is not inferred.
- AC-03: stable redacted condition ID, exact same-key replay, cross-action conflict
  and redacted `acknowledged_by="owner"` pass API and browser tests.
- AC-04: active safety-condition denial, source-complete clear state, guarded
  resolution, immutable rejection-event handling and recurrence pass.
- AC-05: strict parser/component tests, ambiguous client retry with the same key,
  production browser flow, visual inspection and 320px containment pass.
- AC-06: delivery/readiness flags remain false and Demo readiness remains blocked.

## Safety limits

- External delivery, escalation and API-budget source: NOT IMPLEMENTED.
- Lifecycle retention/export, target disk exhaustion and target backup/restore:
  NOT RUN.
- Target restart/network loss and delivered-alert receipts: NOT RUN.
- Broker-side rejected-SL emergency response and Demo round trip: NOT RUN and NOT
  AUTHORIZED.
- Release readiness, Auto Trading and unattended Demo: NOT ESTABLISHED and remain
  off.
