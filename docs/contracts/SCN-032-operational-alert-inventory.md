# SCN-032: Owner operational alert inventory

## Objective

Give the authenticated Demo owner one redacted, read-only inventory of operational
conditions that require attention, and show the exact API/source position in the
web UI. This inventory does not send notifications, acknowledge alerts, resolve
alerts, or authorize execution.

## Scope

- Add `GET /owner/alerts` behind the existing owner verifier.
- Derive current or retained alert facts from bounded, validated local sources:
  telemetry status, execution-bridge status, execution journal, policy-writer
  status, and closed-bar archive storage.
- Publish a fixed coverage ledger for these Blueprint alert kinds:
  `order_reject`, `no_sl`, `risk_halt`, `unknown_execution`, `stale_price`,
  `bridge_disconnected`, `storage_limit`, and `api_budget`.
- Render the inventory inside the authenticated owner workspace and add its API
  and sources to `/ui/connections`.
- Keep `acknowledged_by` and `resolved_at_utc` null until a separately specified
  durable mutation service exists.

## Out of scope

- External email, chat, push, SMS, or webhook delivery.
- Alert acknowledgement/resolution mutations or durable notification history.
- Hosted-service writes, broker operations, deployment, or target-host tests.
- Auto Trading, execution readiness, release-gate promotion, or a claim that an
  alert was delivered.

## Acceptance criteria

### AC-01 — Authenticated, read-only and safe by construction

- `GET /owner/alerts` requires the existing owner bearer session and returns
  `Cache-Control: no-store`.
- POST or other mutation methods are absent.
- The response fixes `trading_mode="demo"`, `read_only=true`,
  `auto_trading_enabled=false`, `execution_ready=false`, and
  `delivery_configured=false`.
- It contains no credentials, account reference, server, filesystem path,
  unrestricted token, or raw source payload.

### AC-02 — Fixed, truthful coverage ledger

- The eight required alert kinds appear once and in a deterministic order even
  when all runtime sources are unconfigured.
- Each coverage row names its implementation/runtime state, API evidence route,
  and redacted source identifiers.
- `api_budget` remains `awaiting_configuration` until a bounded provider-cost
  source exists. Missing delivery remains explicit; neither absence is a pass.

### AC-03 — Broker and journal conditions are not fabricated

- Stale/rejected telemetry emits `stale_price` and/or
  `bridge_disconnected` only from bridge status.
- Stale/rejected execution inventory or degraded policy status emits
  `bridge_disconnected` from that source.
- Validated execution-journal evidence emits `unknown_execution`,
  `order_reject`, `no_sl`, and `risk_halt` facts using bounded deterministic
  reads. An open filled volume without broker-confirmed SL is `no_sl`; a fully
  closed position is not.
- A missing journal is `awaiting_configuration`; a replaced, malformed, or
  unavailable configured journal degrades the inventory and exposes no private
  source details.

### AC-04 — Storage warning remains non-destructive

- A configured archive at the 70% or 85% threshold emits `storage_limit` with
  the corresponding safe detail code.
- The read does not delete, compact, rotate, recreate, or modify the archive.
- An unconfigured archive is `awaiting_configuration`; an unreadable archive
  degrades the inventory.

### AC-05 — Deterministic identifiers and UTC evidence

- Alert identifiers are deterministic hashes of safe kind/source/reference/time
  fields and expose no private identifiers.
- Every alert has an aware UTC observation time, severity, kind, source, safe
  detail code, and evidence routes.
- Results are bounded and sorted by severity, observation time, kind, and ID.
  Truncation is reported instead of silently implying a complete inventory.

### AC-06 — Strict UI contract and visible API placement

- The browser parser rejects unknown fields, duplicate/reordered coverage,
  unknown routes/sources, unsafe safety flags, malformed times, or non-null
  acknowledgement/resolution fields.
- The owner UI shows all eight coverage rows while signed out, and active facts
  only after authentication.
- UTC and Asia/Bangkok times are displayed separately. The UI names
  `/api/owner/alerts` and the source positions, and states that external delivery
  and acknowledgement/resolution are not implemented.
- At 320 CSS pixels the panel remains contained and usable without hiding
  evidence behind a clipped horizontal layout.

### AC-07 — No safety or readiness promotion

- `/ui/demo-readiness` recovery/observability remains `not_run`.
- `/health`, `/ui/connections`, and `/owner/alerts` continue to report Auto
  Trading disabled and execution not ready.
- Local synthetic tests are not reported as target alert delivery, Demo broker
  behavior, deployment, or release readiness.

## Verification evidence required

- Focused Python route/model/journal/archive tests, including negative and
  unavailable-source paths.
- Focused web parser/component tests plus the existing web check.
- Existing project baseline, agent-skill, SCN-001 local, database-static,
  Compose-static, package, container, and secret scans when available.
- Production-build browser flow and 320px containment evidence using only local
  synthetic fixtures.
