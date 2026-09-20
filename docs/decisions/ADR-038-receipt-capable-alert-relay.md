# ADR-038: Use a receipt-capable relay for external alert delivery

- Status: accepted for local implementation; target/recipient selection pending
- Date: 2026-09-20
- Contract: SCN-035

## Context

The owner dashboard can derive eight operational alert classes and durably record
local acknowledgement/resolution, but no process sends those facts outside the
application. A generic one-way webhook would make timeout recovery unsafe: neither
the sender nor the UI could distinguish “receiver accepted the message and the
response was lost” from “receiver never stored it.” Retrying blindly could duplicate
notifications while treating any HTTP 2xx as delivered would overstate evidence.

The owner has not selected an email/chat/SMS provider or recipient. Provider
credentials and formatting therefore cannot be embedded in this repository or
inferred from planning examples.

## Decision

Implement a provider-neutral relay boundary rather than a provider-specific sender.
The worker uses one deterministic delivery ID for one redacted alert occurrence and
one configured destination reference. It commits the payload to a private SQLite
outbox before any network request, marks the attempt `UNKNOWN` before `PUT`, and
accepts delivery only after a separate `GET` returns the same payload digest.

The relay contract is:

- `PUT /v1/sochron/notifications/{delivery_id}` — idempotently store the canonical
  notification using a separately scoped bearer token.
- `GET /v1/sochron/notifications/{delivery_id}` — return the retained canonical
  receipt, `404` when definitely absent, or a conflict when a different digest owns
  the ID.

An adapter outside the trading and risk processes may translate that retained event
to an owner-selected email/chat/SMS provider. The adapter and human recipient must be
selected and verified separately. The relay response is evidence of relay retention,
not proof of human reading.

The API exposes current alert facts to the worker through a distinct internal bearer
identity. The web proxy blocks that route. A private normalized status file projects
journal state back to the owner API without giving the API a destination credential.

## Consequences

- Ambiguous writes are reconciled before retry and logical duplicates retain one
  delivery ID.
- The API/browser never receives the relay origin or credential.
- The implementation can be tested locally with a deterministic receiver before an
  external provider or paid resource is chosen.
- A selected provider may require a small adapter or hosted relay. Until its real
  recipient, delivery receipt, retry/escalation behavior and target recovery are
  exercised, external notification and unattended-Demo gates remain incomplete.
