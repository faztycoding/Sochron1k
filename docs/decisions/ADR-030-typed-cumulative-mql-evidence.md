# ADR-030: typed cumulative MQL execution evidence

- Status: Accepted
- Date: 2026-09-20

## Context

The MQL protocol can parse a command and encode rejection/uncertainty, but cannot
yet encode the cumulative broker snapshots required by the API journal. A mutation
EA without that boundary could place an order and then be unable to report enough
evidence to distinguish filled, partial, protected, cancelled or closed state.
Passing arbitrary JSON fragments into an inventory encoder would move validation
outside the reviewed codec and make restart evidence difficult to audit.

## Decision

Use typed MQL structures for deal, entry snapshot, management snapshot and
rejection evidence. Pure encoders validate bounded identifiers, finite decimals,
UTC time, volume conservation and operation-specific relationships before emitting
the exact Python schema. Inventory is bounded to the project's existing one active
entry and one active management command rather than a generic unbounded JSON list.

Apply the MQL safe-identifier alphabet to Python dispatch fields so the API cannot
expose a command that its only supported MQL parser must reject.

## Consequences

The future EA has one reviewed way to report cumulative evidence after callbacks,
restart or response loss. The codec remains independently source-testable and has
no broker authority. The one-entry/one-management bound intentionally matches the
durable journal invariant; widening concurrency requires a new protocol decision.
