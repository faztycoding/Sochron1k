# ADR-040: Bounded Demo round-trip admission

- Status: accepted for local implementation; actual Demo operation pending
- Date: 2026-09-20
- Decision owner: project owner

## Context

The durable `ExecutionService`, authenticated polling bridge and default-off MQL
mutation source existed as separate verified components. The API runtime did not
construct the service or expose any command-admission boundary, so no authorized
path could produce the broker round-trip evidence required by SCN-001/036. Adding
an owner-browser order button or an unattended signal dispatcher would widen
authority before the target compile, broker and recovery gates exist.

## Decision

Add one internal, separately authenticated controller for a single bounded Demo
round trip. Its owner-private configuration binds the deployed source revision,
owner decision revision, exact Demo identity, experiment/signal/strategy, initial
experiment capital and three distinct entry/cancel/close command identifiers. New
entry is time-bounded to at most 24 hours; cancel, close and query-only reconcile
remain available after entry expiry so the authorization cannot strand exposure.

The controller creates the command journal only in a private directory, provisions
the first risk state create-only from fresh empty MT5 inventory, calls the existing
startup admission and delegates all command behavior to `ExecutionService`. It
does not accept broker tickets or managed volume from the caller. The web ingress
continues to block `/api/internal/`, while the redacted connection/readiness maps
show the internal status route as the missing runtime position.

Public `execution_ready`, `auto_trading_enabled`, `release_ready`, round-trip
authorization and unattended readiness remain false. This boundary is a mechanism
for a separately approved target test, not that approval itself.

## Consequences

- Local simulator tests can now prove API-to-service journal ordering, one-entry
  replay, UNKNOWN reconciliation and halt-preserving close behavior.
- A lost or changed private config cannot select another command; a new target
  attempt needs a new reviewed config and API restart.
- Daily rollover, cash-flow evidence, total-halt release into a new experiment and
  unattended signal scheduling remain separate work.
- Actual MetaEditor compilation, loopback transport, broker behavior and recovery
  must still be observed and admitted through SCN-036 before any release decision.
