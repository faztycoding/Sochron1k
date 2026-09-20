# ADR-027: policy-only empty MT5 inventory observer

- Status: Accepted for source checkpoint
- Date: 2026-09-20

## Context

SCN-023 needs authoritative exposure/pending evidence from the execution bridge,
but the repository has only a pure MQL wire codec and no EA that publishes
inventory. Building mutation first would combine account scanning, local
idempotency, broker writes and reconciliation in one unverifiable step.

The existing codec can encode only an empty inventory. Publishing that shape when
orders or positions exist would be false. Requiring MT5 Auto Trading merely to
observe an empty account would also unnecessarily widen authority.

## Decision

Add a separate read-only execution-inventory observer. It uses the existing
authenticated challenge/upload routes but never polls commands. It scans current
orders and positions twice, compares a bounded exact-enumeration fingerprint and emits a
complete empty inventory only when no effect matching the configured symbol/magic
exists. Foreign effects remain counted. Any owned effect makes the frame
incomplete because this source has no historical command mapping.

Hard-code `algo_trading_allowed=false` in the observer wire. Add a narrower API
policy snapshot predicate that accepts fresh, complete, Demo-bound, foreign-free
inventory even when algorithmic trading is disabled. Keep the existing execution
predicate unchanged, so startup admission, command exposure and public execution
readiness remain unavailable.

## Rejected alternatives

- **Emit empty arrays without scanning:** this would invent no-exposure evidence.
- **Mark an owned position as foreign:** it would hide the exact reason history is
  incomplete and break future command reconciliation.
- **Enable terminal Auto Trading for observation:** read-only policy evidence does
  not require mutation permission.
- **Poll and ignore commands:** claiming a dispatch without a durable local ledger
  could strand the API in an ambiguous active state.
- **Infer history from current tickets:** cumulative deals, partial fills and
  broker-side SL confirmation require a separately designed durable mapping.

## Consequences

SCN-023 can obtain real current-empty evidence from a future compiled observer
while the execution bridge correctly stays non-ready. Policy output stops as soon
as a current owned or foreign effect appears. The mutation EA still needs a local
ledger, exclusive lock, cumulative inventory reconstruction, immediate preflight,
uncertain-write recovery and actual Demo verification.
