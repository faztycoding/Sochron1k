# SCN-036: Target evidence admission and UI positions

## Objective

Add a disabled-by-default, query-only admission boundary for normalized target
artifact, bounded Demo round-trip and recovery/observability reports. Bind every
report to one reviewed source revision, private target identity and owner-decision
revision, then show its exact owner API position in the Demo readiness ledger.
Admission means that the configured normalized files were present, intact, current
and internally coherent. It is not release approval or independent proof that the
underlying target event happened.

## Scope

- Read one exact owner-private target-evidence config selected by
  `SOCHRON_TARGET_EVIDENCE_CONFIG_FILE`.
- Validate one atomic manifest plus three bounded normalized report files for
  `target_artifact`, `broker_round_trip` and `recovery_observability`.
- Require stable single-link files, exact SHA-256 bindings, current UTC evidence,
  one source revision, target hash and owner-decision revision across all files.
- Add authenticated `GET /owner/target-evidence` and browser route
  `GET /api/owner/target-evidence` with only redacted provenance and gate states.
- Project admitted/failed/not-run evidence into `GET /ui/demo-readiness` and show
  the exact API position in the existing responsive ledger.

## Out of scope

- Creating target reports, compiling MQL5, connecting MT5, placing or closing an
  order, injecting target faults, sending a real alert or restoring a target backup.
- Accepting arbitrary logs, screenshots or manual pass booleans as normalized
  evidence.
- Signing, uploading, deploying or purchasing infrastructure.
- Granting operational authorization, enabling Auto Trading, releasing a halt or
  producing a positive release verdict.

## Acceptance criteria

### AC-01 — Explicit private configuration

- Missing `SOCHRON_TARGET_EVIDENCE_CONFIG_FILE` yields a disabled view without
  filesystem or network effects.
- The selected config, manifest directory, manifest and report files are canonical,
  owner-owned, owner-private, stable, regular/single-link where applicable and
  bounded. Symlinks, hard links, replacement, public permissions and oversized or
  duplicate-key JSON fail closed.
- Config pins the exact 40-hex source revision, 64-hex target identity hash,
  owner-decision revision, snapshot path and maximum evidence age. No credential,
  account reference, URL or unrestricted target identifier is accepted or exposed.

### AC-02 — Exact manifest and normalized reports

- One manifest uses a fixed ordered list of the three target gates and binds each
  report filename, byte length and SHA-256 digest.
- Every report repeats the exact source/target/decision binding and contains the
  fixed ordered checks for its gate. A completed report pins its verifier SHA-256,
  start/finish UTC times and a digest for every completed check.
- `PASS` requires every fixed check to be `PASS`; `FAIL` requires all checks to be
  completed and at least one `FAIL`; `NOT_RUN` requires no verifier/time/digest
  claim and every check to be `NOT_RUN`.

### AC-03 — Fresh, coherent admission only

- The reader validates manifest/report identity before and after each bounded read,
  recomputes each file digest and rejects a changed directory or file.
- Report times cannot precede the configured decision, exceed manifest production
  time or come from the future. Evidence older than the configured maximum becomes
  `stale`; invalid or unreadable evidence becomes `degraded`.
- A valid snapshot derives only `awaiting_evidence`, `partial`, `admitted` or
  `failed`; it never derives release authorization.

### AC-04 — Redacted owner API

- `GET /owner/target-evidence` requires the existing active owner session and is
  `Cache-Control: no-store`.
- The response contains only safety literals, overall state, source revision,
  16-hex hashes for target/decision/report references, UTC evidence times and fixed
  gate states. It contains no path, filename, raw target ID, decision text, verifier
  content, underlying check digest, credential or account/server identity.
- The route is read-only and has no broker, deployment, filesystem-write or release
  effect.

### AC-05 — Truthful readiness projection

- Without admitted evidence the existing target gates remain `not_run`; stale,
  invalid or failed evidence makes the affected readiness boundary `degraded` or
  `evidence_failed` rather than `PASS`.
- A valid `PASS` report maps only to `evidence_admitted`. Even when all three target
  reports are admitted, `release_ready=false`, `round_trip_authorized=false`,
  `unattended_demo_ready=false` and `auto_trading_enabled=false` remain literals.
- When runtime gates and all target reports are admitted, overall readiness may say
  `awaiting_operational_authorization`; it still cannot authorize an operation.

### AC-06 — Exact UI/API position

- The ledger lists `/api/owner/target-evidence` for artifact and recovery evidence,
  and lists both execution evidence and target admission routes for the broker
  round-trip gate.
- Strict TypeScript parsing accepts only the fixed new states/routes/order and
  rejects true safety flags, unknown evidence states and route/source drift.
- Thai labels distinguish “รับหลักฐานแล้ว”, “หลักฐานไม่ผ่าน”, stale/degraded and
  release authorization. Desktop and 320 CSS pixel layouts remain contained and
  keyboard-readable.

### AC-07 — Operational limits remain explicit

- Base Compose only passes an optional config path to the API; it does not create,
  mount or fabricate target evidence and does not start a target verifier.
- Local synthetic fixtures prove only parsing, binding and projection. Real target
  compile, broker, recovery, alert, backup/restore, burn-in and explicit owner
  authorization remain `NOT RUN`.

## Required evidence

- Focused API/auth/reader tests covering disabled, missing, exact pass, partial,
  fail, stale, future time, binding drift, digest/size mismatch, permissions,
  hardlink, symlink, replacement, duplicate JSON and response redaction.
- Strict UI parser/component tests, production build, browser route placement and
  320px containment.
- Full local Python/web, static Compose/database, installed-package, container and
  secret checks where available.
