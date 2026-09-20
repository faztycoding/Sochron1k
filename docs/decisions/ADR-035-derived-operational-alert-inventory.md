# ADR-035: Derive a read-only operational alert inventory before delivery

- Status: accepted
- Date: 2026-09-20

## Context

The owner UI already exposes telemetry, chart/history, execution evidence,
signals, statistics, and Demo readiness. Operationally important states remain
scattered across those read models. The Blueprint also requires a notification
center and named alerts before unattended Demo operation, but this repository has
no approved external destination, provider budget source, or durable
acknowledgement/resolution store.

Treating a UI list as proof that an alert was delivered would be unsafe. Adding a
mutable alert database before ownership, retention, and authorization are agreed
would also enlarge the system boundary prematurely.

## Decision

Add an owner-authenticated, read-only alert inventory derived at request time from
existing authoritative or durable local evidence. Return a fixed coverage ledger
alongside bounded active/retained facts. Keep external delivery, acknowledgement,
resolution, and provider-budget coverage explicitly unconfigured.

Execution facts come from the pinned read-only journal projection; market and
executor connectivity come from in-process bridge states; archive pressure comes
from the pinned bar-history database; policy degradation comes from the policy
writer status. The inventory redacts broker identity and filesystem paths and uses
deterministic hashed IDs.

## Consequences

- The owner gets one truthful place to see what needs attention and where each API
  must be connected.
- The endpoint is not a durable event log. A condition can disappear when its
  source state changes, while retained journal rejections remain visible within
  the bounded projection.
- `acknowledged_by` and `resolved_at_utc` stay null. A later ADR must define durable
  alert lifecycle, authorization, retention, and idempotency before mutation.
- External delivery and API-budget alerts remain release gaps and cannot satisfy
  the target recovery/observability gate.
