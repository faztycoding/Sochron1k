# SCN-035 durable alert-delivery verification

## Candidate

- Base revision before commit: `2627b29ca5b6f492e78a2404eedb16686d5be5d1`
- Candidate state during verification: dirty working tree containing only the
  scoped SCN-035 alert source, outbox/relay worker, API/UI integration, tests and
  documentation
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0, uv 0.12.15 for
  artifact verification, Docker 29.5.2, Playwright 1.63.0 and Chromium
  153.0.8010.12
- Evidence type: local/synthetic only; no relay/provider credential, real recipient,
  hosted write, MT5 operation, paid resource or target deployment

## Outcome

SCN-035 AC-01 through AC-06 pass for local and synthetic evidence. The private
`GET /internal/v1/alerts` route exposes bounded redacted current facts only to one
separate service identity, and browser ingress rejects that namespace. The installed
`sochron-alert-delivery` command is inert without private configuration. When
explicitly configured, it commits an immutable notification before send, persists
`UNKNOWN` before the external write and accepts only a later matching receipt as
`VERIFIED`.

`GET /owner/alerts` v4 embeds the redacted status projection. The production UI
places `External alert delivery` below API Budget and above lifecycle events, showing
the private source position, worker name, destination reference, pending/unknown/
quarantine counts and last verified receipt. It explicitly says that relay retention
is not proof that a human read the notification. Auto Trading and execution readiness
remain false; the SCN-031 recovery/observability gate remains `not_run`.

## Verification run on 2026-09-20

- Focused Ruff and alert/API tests — PASS. The alert-delivery suite has 22 tests
  covering private source authorization/redaction, separate credentials, disabled
  defaults, public permissions, hard links, symlinks, size bounds, exact delivery,
  duplicate occurrence, timeout, restart, query-before-retry, confirmed missing,
  send-budget exhaustion, conflict/quarantine, replacement/corruption, status
  projection and bounded HTTP behavior.
- Full `bash scripts/check-scn-001-local.sh` — PASS: 1,121 tests, Ruff and secret
  scan.
- `npx -y -p node@24.21.0 npm run check:web` — PASS: TypeScript, 211 tests,
  production build, responsive checks and client-secret scan.
- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS, including browser
  denial of `/api/internal/`.
- Guarded local Supabase plus `scripts/check-owner-browser.mjs` — PASS against the
  production build: owner/foreign authorization, strict v4 inventory, configured
  synthetic delivery receipt, redaction, lifecycle behavior, logout/token refresh,
  API restart and 320px containment. Evidence:
  `output/playwright/scn005-d05a1fe7-5d13-4fd0-813a-4f7601057b95/result.json`.
  Desktop/mobile screenshots were visually inspected; the delivery ledger is
  readable, correctly ordered and contained. Fixture cleanup passed and the local
  stack was stopped afterward.
- Isolated Compose build/start/recreate — PASS with non-root/read-only boundaries,
  Demo-only health, private ingress denial and persistent volume identity. Evidence
  is `output/compose/sochron-verify-1f153a0e3363/result.json`.
- Candidate API Linux image plus fixed-SQLite verifier — PASS with 1,056 affected
  tests. Evidence:
  `output/container-python/sochron-python-9b28f02ebef6/result.json`.
- Installed worker package verifier — PASS for byte-identical wheel, fresh
  non-editable install, default-disabled delivery command and existing recovery
  regressions. Evidence:
  `output/worker-package/90a521b6d469467e872390fc0995a980/result.json`.
- Worker container verifier — PASS for installed wheel, default-disabled network,
  private config, exclusive writer and `UNKNOWN`/restart read-back without resend.
  Evidence:
  `output/worker-container/sochron-worker-4c6e6d51cacd/result.json`.

The first browser attempt stopped at prerequisites because guarded local Supabase
was not yet running; it created no fixture. The stack was started through the
loopback-only wrapper and the rerun passed. The first candidate-image Python attempt
used the image SHA directly as a Dockerfile base; BuildKit interpreted it as a
repository name and denied the pull. The exact same local image was resolved to its
immutable local tag and the verifier passed. No assertion, test or safety gate was
weakened.

## Acceptance mapping

- AC-01: default-disabled route, exact private bearer authorization, token isolation,
  source redaction/bounds and browser-ingress denial pass.
- AC-02: exact private worker configuration, canonical objects, origin policy,
  credential separation and inert default pass.
- AC-03: audited single-writer SQLite schema, full synchronization, bounded storage,
  immutable payload/IDs and journal-before-send pass.
- AC-04: `PUT`, independent `GET`, timeout/restart reconciliation, same-ID retry,
  immediate conflict quarantine and maximum-send enforcement pass.
- AC-05: atomic status, missing/stale/degraded distinctions, strict v4 API/browser
  schemas, visual placement, receipt wording and 320px containment pass.
- AC-06: base Compose remains default-off, release flags remain false and local
  evidence is not promoted to target or recipient evidence.

## Safety limits

- Real relay/provider, destination credential, recipient, provider adapter and
  human delivery/read evidence: NOT SELECTED / NOT RUN.
- Target private routing, TLS, disk-full/restart/network-loss exercise, retention,
  escalation and backup/restore within owner-selected RPO/RTO: NOT RUN.
- Runtime billing provider, collector, currency/limit and actual invoice
  reconciliation: NOT SELECTED / NOT RUN.
- MT5 compile, Demo account connection, broker round trip, VPS deployment and burn-in:
  NOT RUN and NOT AUTHORIZED.
- Release readiness, Auto Trading and unattended Demo: NOT ESTABLISHED and remain
  off.
