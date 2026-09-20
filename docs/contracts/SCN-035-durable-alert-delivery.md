# SCN-035: Durable provider-neutral alert delivery

## Objective

Add a disabled-by-default delivery boundary for current operational alerts so one
separately authenticated worker can journal a notification before sending it,
reconcile an ambiguous write through a receipt-capable relay, and expose a redacted
delivery status in the owner UI. This contract does not select a recipient or claim
that any real notification has been delivered.

## Scope

- Add one private service-authenticated `GET /internal/v1/alerts` source route that
  returns only bounded, redacted current alert facts.
- Add the installed `sochron-alert-delivery` worker command with explicit private
  configuration, a durable SQLite outbox, bounded retry and query-before-retry.
- Define a provider-neutral HTTPS relay contract using an idempotent delivery ID,
  canonical payload digest and independently readable receipt.
- Publish a normalized private delivery-status snapshot from the journal and embed
  its redacted projection in `GET /owner/alerts`.
- Render the status, pending/unknown counts, last verified receipt and exact API
  positions in the existing notification center.

## Out of scope

- Selecting or provisioning email, SMS, push, chat, webhook or relay infrastructure.
- Storing a destination credential in the API, browser, repository or status file.
- Treating an HTTP success response alone as proof that the recipient saw a message.
- Pager escalation, recipient rotation, quiet hours or provider-specific formatting.
- Hosted deployment, paid resources, MT5 operations, release promotion or enabling
  Auto Trading.

## Acceptance criteria

### AC-01 — Private source identity

- The internal route is disabled without an explicit owner-private token config and
  requires exactly one separately scoped bearer credential when enabled.
- The source credential cannot equal the telemetry or execution credential. The web
  reverse proxy denies `/api/internal/` so browsers cannot reach this service route.
- The exact source response is bounded, uses aware UTC timestamps and contains no
  owner UUID, account/server identity, credential, filesystem path or raw source
  payload.

### AC-02 — Explicit delivery configuration

- Without `SOCHRON_ALERT_DELIVERY_CONFIG_FILE`, the command exits `DISABLED` and
  performs no filesystem or network operation.
- The selected config, source token, destination token and state directory are
  canonical owner-private objects with stable identities. Source and destination
  credentials must differ.
- Configuration pins source origin, destination origin, redacted destination ref,
  poll interval and send budget. Remote origins require HTTPS; loopback HTTP is
  accepted only for local synthetic verification.

### AC-03 — Durable outbox before send

- One private SQLite WAL journal uses full synchronization, a fixed audited schema,
  bounded pages and an exclusive single-writer lock.
- The canonical alert payload and destination binding commit as `PREPARED` before
  any relay request. `begin_send` commits `UNKNOWN` and increments the attempt before
  the external write.
- Alert occurrence and delivery IDs are unique and retained. Database, permission,
  clock, identity or schema failure stops delivery instead of recreating evidence.

### AC-04 — Reconcile before retry

- The worker sends an idempotent `PUT /v1/sochron/notifications/{delivery_id}` and
  validates only a later matching `GET` receipt as `VERIFIED`.
- A timeout, interrupted response or malformed acknowledgement remains `UNKNOWN`.
  The next step performs only receipt reconciliation. A confirmed missing receipt
  returns the intent to `PREPARED`; resend can occur only on a later step with the
  same delivery ID and payload.
- A conflicting receipt or changed source/destination binding becomes
  `QUARANTINED`. Attempts never exceed the configured maximum of five.

### AC-05 — Redacted status and owner UI

- The worker atomically publishes a private normalized status snapshot derived from
  the journal. It contains counts and redacted IDs only, no origin, credential or
  path. The API treats a missing snapshot as `awaiting_worker`, an expired heartbeat
  as `stale`, and malformed/untrusted evidence as `degraded`.
- `GET /owner/alerts` v4 embeds the exact delivery view and sets
  `delivery_configured` coherently. Configuration, pending work, `UNKNOWN` and a
  verified receipt remain distinct states.
- The dashboard shows the delivery API/source location below API Budget and above
  lifecycle events. It remains contained at 320 CSS pixels and never says “sent”
  without a verified receipt.

### AC-06 — Operational limits remain explicit

- The base application and worker Compose paths do not start delivery by default.
- `auto_trading_enabled=false`, `execution_ready=false`, Demo-only behavior and the
  SCN-031 recovery/observability `not_run` gate remain unchanged.
- Local synthetic relay evidence is not a real recipient, target-host recovery,
  alert escalation, deployment or unattended-Demo release result.

## Required evidence

- Focused API/auth/status tests and worker config/journal/driver/HTTP tests covering
  disabled, exact success, duplicate occurrence, timeout, missing read-back, retry,
  conflict, restart, replacement, corruption and send-budget exhaustion.
- Strict web parser/component tests plus production build and 320px containment.
- Full local Python, web, static database/Compose, installed-package, container and
  secret checks where available.
