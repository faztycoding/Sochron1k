# SCN-020 atomic PA01 decision receiver

## Task contract

Add the backend-only Supabase boundary that atomically records one immutable PA01
feature snapshot and its linked signal, then independently reads the exact stored
pair for reconciliation. Preserve the existing owner RLS read models and Demo-only
scope. A timed-out or lost response remains UNKNOWN until read-back matches; retry
must be idempotent and a changed payload must conflict.

This increment is the destination required by a future durable strategy producer.
It does not query source bars, schedule PA01, create a command, size risk, call MT5,
change strategy status or make `/api/owner/signals` leave `awaiting_source` by itself.

## Decision record contract

- One backend request identifies an existing owner, `PA01-v1` strategy row and an
  experiment bound to that same owner/strategy. Strategy parameters must pin
  `PA01-v1.0.1`, its exact parameter hash and
  `native-pa01-aggregation-v1`; the experiment must remain draft, shadow or Demo.
- The request contains an exact versioned JSON object with a 64-character lowercase
  decision fingerprint, one M5 feature snapshot and one BUY/SELL/WAIT/BLOCK signal.
  IDs, UTC timestamps, dataset/code identity, features, execution parameters and
  source/aggregation hashes are bounded and validated before insertion.
- Snapshot event time is the M5 decision formation time. Received/available time is
  the evidence confirmation time. The linked signal preserves formed, confirmed
  and expiry times plus the exact bounded evidence-ID set and BLOCK reason semantics.
- Both rows store the same producer revision/fingerprint. The signal carries an
  owner-safe foreign key to its feature snapshot, and one producer snapshot can
  belong to only one signal.
- Producer-marked rows are immutable. Corrections require a new snapshot/signal ID
  and fingerprint; they cannot rewrite historical evidence.

## In scope

- Forward migration extending existing `feature_snapshots` and `signals` without
  replacing owner IDs, RLS policies or existing legacy rows.
- Security-invoker, empty-search-path store/read RPCs with explicit backend-only
  grants and bounded request/response shapes.
- Atomic insert-or-verify semantics, exact duplicate acceptance, changed replay
  conflict and independent read-back.
- Fresh/forward migration, role/RLS, malformed payload, concurrency, rollback and
  lost-response reconciliation fixtures on the guarded local Supabase stack.

## Out of scope

- Source M1 reads, aggregation invocation, policy-context acquisition, scheduling,
  a local SQLite producer journal, HTTP adapter/retry loop or worker enablement.
- Strategy creation/promotion, research evaluation/statistics, risk admission,
  command creation, MT5 execution, hosted writes, deployment or live trading.

## Acceptance criteria

- **AC-01 linked immutable evidence:** producer rows share owner, revision and
  fingerprint; signal-to-snapshot ownership is enforced by a foreign key and unique
  relation. UPDATE/DELETE of producer rows fails, while pre-existing legacy rows
  remain forward compatible.
- **AC-02 strict validation:** reject unknown/missing/oversized fields, invalid UTC,
  hashes, identifiers, action/reason combinations, causal times, malformed evidence
  IDs or a feature payload inconsistent with its signal/snapshot.
- **AC-03 strategy admission:** reject missing/mixed owner, mismatched experiment,
  non-PA01 or incompatible parameter/aggregation identity, future data cutoff and
  halted/closed/archived experiments. The receiver never promotes a strategy.
- **AC-04 atomic idempotency:** snapshot and signal commit together. An exact repeat
  returns the stored identity without another row; a reused ID/fingerprint with any
  changed evidence raises a named conflict and leaves no partial write.
- **AC-05 authorization:** anonymous/authenticated callers cannot invoke either RPC
  or mutate rows. Owner SELECT RLS remains intact; the browser never receives a
  service-role key. Functions are invoker with an empty search path and explicit
  grants only to backend roles.
- **AC-06 UNKNOWN reconciliation:** an independently callable read RPC returns the
  exact linked producer record only for the configured owner/signal. Concurrent
  matching writers converge to one pair; committed-but-lost response can reconcile
  without a second logical decision.
- **AC-07 migration/regression:** static SQL, fresh and forward local migrations,
  pgTAP, advisors and existing owner browser/API reads pass without weakening prior
  RLS or native M1 immutability tests.
- **AC-08 no execution authority:** schema/RPC tests prove this boundary cannot
  create commands, change risk/halt state, contact MT5 or enable Auto Trading.

## Evidence boundary

A passing SCN-020 proves only the local atomic Supabase destination and reconciliation
contract for synthetic fixtures. It does not prove a running producer, remote/hosted
durability, source availability, strategy performance, Demo execution or release
readiness. `/api/owner/signals` remains empty until a separately verified producer
writes through this boundary.
