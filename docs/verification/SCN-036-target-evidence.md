# SCN-036 normalized target-evidence admission verification

## Candidate

- Base revision before commit: `4c2a3e548d8bdaf9302de438007d26afad42f497`
- Candidate state during verification: dirty working tree containing only the
  scoped SCN-036 reader, readiness/API/UI integration, verifiers, tests and docs
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0, uv 0.12.15, Docker
  29.5.2, Compose 5.5.1, Playwright 1.63.0 and Chromium 153.0.8010.12
- Evidence type: local/synthetic only; no VPS/Windows target, MetaEditor compile,
  MT5 terminal, broker operation, credential, provider, paid resource or deployment

## Outcome

SCN-036 AC-01 through AC-07 pass for local implementation and synthetic evidence.
The disabled-by-default reader admits one exact private manifest and three fixed
normalized reports only after source/target/owner-decision, file identity, byte,
SHA-256, schema, ordered check, UTC and freshness bindings validate. Invalid,
replaced, public, linked, oversized, stale or incoherent files fail closed.

The active-owner-only `GET /owner/target-evidence` route exposes redacted hashes,
times and fixed gate states. The UI shows its browser position as
`/api/owner/target-evidence` in target rows 06-08 and distinguishes
`evidence_admitted` from release approval. Every safety literal remains false:
Auto Trading, release readiness, round-trip authorization and unattended-Demo
readiness are not enabled.

## Verification run on 2026-09-20

- Focused Ruff plus API/Auth/reader tests — PASS: 76 tests. Coverage includes
  disabled/missing, exact admission, partial/fail/stale/future, source/target/time
  drift, digest/size mismatch, private permissions, hard links, symlinks, directory
  replacement, duplicate JSON, owner-decision startup binding and response
  redaction.
- Full `bash scripts/check-scn-001-local.sh` — PASS: 1,129 tests, Ruff and secret
  scan.
- `npx -y -p node@24.21.0 npm run check:web` — PASS: TypeScript, 215 tests,
  production build, responsive checks and client-secret scan.
- `bash scripts/check-project-baseline.sh` and
  `python3 scripts/check-agent-skills.py` — PASS; the skill command is integrity
  inventory only.
- `npx -y -p node@24.21.0 npm run check:db:static` and
  `npm run check:compose:static` — PASS. Compose asserts optional empty target and
  decision config variables, no target verifier service and no added evidence
  mount.
- Guarded local Supabase plus `scripts/check-owner-browser.mjs` — PASS against the
  production build: strict admitted states, exact route placement, active-owner and
  foreign-user behavior, redaction, false safety flags, restart, token refresh,
  cleanup and 320px containment. Evidence:
  `output/playwright/scn005-b3c9a49d-e759-407c-8ca0-36d4927f5b78/result.json`.
  The dedicated desktop/mobile readiness screenshots were visually inspected; all
  nine rows, target routes and warning copy remain readable and contained.
- Guarded native-sync local verifier — PASS: actual local PostgREST commit/restart
  read-back, owner isolation, unsafe-config denial and invocation-owned cleanup.
  Hosted writes and MT5 remained `NOT_RUN`.
- Isolated Compose build/start/recreate — PASS with non-root/read-only boundaries,
  Demo-only health, internal API network, private ingress denial and persistent
  volume identity. Evidence:
  `output/compose/sochron-verify-8e1b91a2fa98/result.json`.
- Candidate API Linux image plus fixed-SQLite verifier — PASS: SQLite 3.53.4
  source/linkage admission and 1,064 affected tests. Evidence:
  `output/container-python/sochron-python-c60aad2911a4/result.json`.
- Installed package verifier — PASS for byte-identical build, fresh non-editable
  install, inert default commands and existing recovery/startup oracles. Evidence:
  `output/worker-package/df3fae66ccc240908d70f63e88389881/result.json`.
- Worker container regression — PASS for installed wheel identity, disabled
  network/defaults, private configuration, exclusive writer and `UNKNOWN` restart
  behavior. Evidence:
  `output/worker-container/sochron-worker-ef520d5436f4/result.json`.

The first candidate-image invocation stopped before building because uv 0.12.15
was not on `PATH`; rerunning with the existing pinned absolute executable passed.
The full, package, image and browser verifiers were rerun after the final binding/
time-drift tests were added. No test, timeout, gate or safety assertion was weakened.

## Acceptance mapping

- AC-01: exact optional private config, canonical/private/single-link file checks,
  size bounds, duplicate-key denial and default-disabled behavior pass.
- AC-02: fixed ordered manifest/reports/checks, digest recomputation and strict
  `PASS`/`FAIL`/`NOT_RUN` coherence pass.
- AC-03: decision/source/target/time/freshness bindings and fail-closed stable reads
  pass; admission never derives release authority.
- AC-04: active-owner authorization, no-store response and path/filename/target/
  decision/check redaction pass.
- AC-05: `evidence_admitted`, `evidence_failed`, `not_run`, stale and degraded
  readiness projection pass while every safety flag remains false.
- AC-06: exact browser routes, strict TypeScript parsing, Thai state labels,
  production UI rendering and 320px containment pass.
- AC-07: base Compose remains inert and unmounted; synthetic fixtures are not
  promoted to target, broker, recovery or release evidence.

## Safety limits

- Actual MetaEditor compile, artifact identity and denied-live target preflight:
  `NOT RUN`.
- MT5 Demo account/server/symbol/contract binding, broker order/deal/position/close
  and broker-side SL confirmation: `NOT RUN` and not authorized.
- Target restart/network-loss, journal/storage failure, rejected-SL emergency,
  alerts, backup/restore, latency p50/p95 and multi-market-day burn-in: `NOT RUN`.
- Real provider/billing collector, relay, recipient, escalation and human delivery:
  not selected / `NOT RUN`.
- Operational authorization, release readiness, Auto Trading and unattended Demo:
  not established and remain off.
