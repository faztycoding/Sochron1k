# SCN-033: Durable owner alert lifecycle

## Objective

Let the authenticated Demo owner acknowledge operational alerts and close only
eligible alert episodes without changing, suppressing, or claiming recovery of the
underlying source. Persist the workflow locally so acknowledgement and resolution
survive API restarts and ambiguous client responses.

## Scope

- Extend `GET /owner/alerts` to a strict v2 inventory with a stable redacted
  `condition_id`, lifecycle state, acknowledgement time and resolution time.
- Add narrowly authorized, idempotent owner mutations:
  `POST /owner/alerts/{condition_id}/acknowledge` and
  `POST /owner/alerts/{condition_id}/resolve`.
- Store lifecycle snapshots and mutation receipts in one explicitly configured,
  owner-private SQLite journal selected by `SOCHRON_ALERT_LIFECYCLE_DIR`.
- Render truthful lifecycle controls and UTC/Asia-Bangkok evidence in the existing
  notification center.

## Out of scope

- Email, chat, SMS, push or webhook delivery and escalation.
- API-provider cost collection or the `api_budget` detector.
- Mutating telemetry, the execution journal, risk state, broker state or MT5.
- Hosted writes, deployment, target-host tests, Auto Trading, release-gate
  promotion or a claim that acknowledging an alert fixed its cause.

## Acceptance criteria

### AC-01 — Owner-only, explicit lifecycle configuration

- Both mutation routes require the existing verified owner bearer session, reject
  duplicate/malformed authorization or idempotency headers, and return
  `Cache-Control: no-store`.
- An unconfigured lifecycle journal keeps the inventory readable with
  `lifecycle_runtime="awaiting_configuration"` and mutations disabled with a
  truthful 503 response.
- A configured path must be an existing canonical absolute directory owned by the
  API user with no group/other permissions. Configuration or startup corruption
  fails closed instead of silently replacing the journal.

### AC-02 — Durable, bounded and recoverable journal

- The journal uses a private regular SQLite file, WAL, `synchronous=FULL`, foreign
  keys, a fixed schema/version, integrity checks and a 32 MiB page limit.
- A lifecycle mutation and its idempotency receipt commit in one immediate
  transaction before the API reports success.
- File/directory replacement, malformed retained data, clock regression, lock or
  write failure returns unavailable and never fabricates acknowledgement or
  resolution.
- Reads and writes are owner-scoped, bounded and exclude credentials, account or
  server identity, raw source payloads and filesystem paths from API responses.

### AC-03 — Stable redacted identity and exact replay

- `condition_id` is a deterministic hash of the safe kind, source, source
  reference and detail code. It remains stable across polling while occurrence
  `id` and `observed_at_utc` retain source-time evidence.
- Every mutation requires one UUID `Idempotency-Key`. Exact replay returns the
  already committed result; reuse for another owner/action/condition conflicts
  without a second transition.
- Acknowledge is admitted only for a currently detected unresolved episode. The
  response records `acknowledged_by="owner"` and an aware UTC time without
  exposing the owner's UUID.

### AC-04 — Resolution cannot hide an active safety condition

- Resolution requires prior acknowledgement.
- `no_sl`, `risk_halt`, `unknown_execution`, `stale_price`,
  `bridge_disconnected`, and `storage_limit` cannot resolve while the detector
  still emits the condition.
- A cleared condition remains visible as `cleared` and may resolve only when its
  applicable source coverage is connected and the relevant bounded projection is
  complete. Missing, degraded, awaiting or truncated evidence rejects resolution.
- `order_reject` is an immutable occurred event rather than a current broker
  state; after acknowledgement it may be resolved while retained by the
  execution journal. Resolution changes only the notification workflow.
- A later episode observed after a prior resolution is shown as a new active,
  unacknowledged episode.

### AC-05 — Strict, usable notification-center UI

- The browser parser accepts only the exact v2 fields, enums, routes, lifecycle
  transitions and safe hashes, rejecting unknown fields or contradictory times.
- Active, acknowledged, cleared and resolved states are visibly distinct. The UI
  offers acknowledge only for an active unacknowledged episode and resolve only
  when the server contract can admit it; ambiguous retries reuse the same
  idempotency key.
- UTC and Asia/Bangkok times remain separate, all API/source positions remain
  visible while signed out, and the panel stays contained at 320 CSS pixels.

### AC-06 — No delivery or readiness promotion

- `delivery_configured=false`, `auto_trading_enabled=false` and
  `execution_ready=false` remain literal response invariants.
- The UI explicitly states that acknowledgement/resolution is a local owner
  workflow and not external delivery or proof that MT5/source recovery occurred.
- `/ui/demo-readiness` recovery/observability remains `not_run`; local synthetic
  lifecycle tests are not target notification, broker, deployment or release
  evidence.

## Verification evidence required

- Focused Python model, route and SQLite tests covering owner denial, duplicate
  headers, replay/conflict, restart, replacement, corruption, clock regression,
  write failure, active-condition denial, cleared-condition admission and
  recurrence.
- Focused web parser/component tests covering strict v2 parsing, successful and
  ambiguous mutation flows, control eligibility, logout redaction and 320px
  containment.
- Existing project baseline, agent-skill, SCN-001 local, web, database-static,
  Compose-static, package, container and secret checks when available.
- Production-build browser evidence with synthetic local sources only.
