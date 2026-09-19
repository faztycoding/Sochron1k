# ADR-016 Explicit execution startup admission

2026-09-20; SCN-010, builds on checkpoint `6ee67dc` and SCN-001's local simulator.
Decision: require explicit startup inventory and durable risk admission before
ExecutionService.submit. No HTTP execution route, MT5 send adapter or release
enablement is introduced. The existing owner-authenticated UI remains read-only.

## Inventory and admission

`ExecutorAdapter` defines inventory/send/query. `ExecutorInventory` carries an
explicit executor ID/generation, account identity/mode, symbol, observation time,
completeness, foreign-order/position counts and bounded command snapshots. The
simulator must be configured with an account and symbol independently from a
submitted request. An unconfigured simulator cannot produce an inventory.

Each new service/PID begins without admission. `startup` validates explicit
policy/experiment/executor binding, account Demo mode and trade permission, aware
times in the preceding five seconds, full inventory and zero foreign exposure.
It loads the existing risk state for the current Bangkok day, never synthesizing
baselines or clearing a halt. A single active command must have its matching
reservation, valid payload fingerprint and a matching broker snapshot. Missing
inventory evidence leaves startup denied rather than classifying a send as absent.
The complete set is bounded to 1,000 snapshots and at most one active exposure.

Before admission, validate all inventory snapshots against the journal, including
retained rejected commands: terminal labels alone cannot hide inconsistent fills.
Only active-command evidence is applied, with transactional validation again.
Unprotected fills remain recorded but deny startup. The final read checks unchanged
risk, expected active/reservation IDs and database inode. Startup can reconcile a
halted/occupied account but returns local_entries_admitted=false; all public/runtime
release flags remain execution_ready=false and auto_trading_enabled=false.

`submit` serializes service operations, requires the bound policy/experiment and
generation and queries inventory again. It matches the supplied account/Equity to
the inventory, retains admitted baselines and denies current halts. SQL transactions
recheck the exact expected risk record and its account/experiment at reservation
and begin-dispatch. Exposure admission is account-wide across experiments, using
the existing BEGIN IMMEDIATE reservation transaction; no schema migration is made.
Quote/expiry/account/day checks run again after local journal work before adapter
invocation. Only implemented open commands may enter this path; close/cancel are
explicitly denied rather than silently interpreted as opens.

## Evidence application and unknown outcomes

The journal validates requested=filled+remaining, total deal volume, bounded exact
decimals, identifiers, matching command volume, dispatch evidence, ticket ownership,
immutable existing deal values, nondecreasing fills and terminal-state consistency.
It rejects pre-dispatch states even if an inconsistent attempt row exists. Invalid
evidence rolls back without changing orders/deals/command history. A snapshot for
another command cannot satisfy a send or query. Duplicate deal evidence remains
idempotent; reconciliation events can still append transitions.

Once the adapter was invoked, an exception or malformed/conflicting result is
ambiguous. Clear admission and persist UNKNOWN if storage remains available;
never retry or claim a fill. If storage cannot persist it, propagate failure with
admission closed rather than claim the durable write succeeded. The original
exposure and attempt remain. A failure before adapter invocation can retain SENT
intent/attempt but has no observed send; this conservatively needs reconciliation.
Query-only recover/reconcile never grants startup admission. Forked instances are
denied before acquiring inherited mutexes. PID-local locks do not implement an
external distributed lease or fencing token.

## Bounds and unfinished boundaries

Inventory validation checks a cooperative five-second duration and freshness at
completion; kernel/adapter blocking is not a hard timeout. Inventory.complete,
foreign counts and generation are trusted adapter assertions, not proof from MT5.
A real adapter still needs authenticated exclusive executor ownership, complete
order/position/history collection and broker-side preflight at its own send point.
The inventory may change after collection; a local admission check is not atomic
with broker state or a later halt. Runtime clock input is trusted dependency
injection for synthetic tests, not a browser-selectable timestamp.

Journal is still an internal initializing writer; startup admission is not a full
schema/corruption audit, owner backup activation or independent database permission
boundary. Existing low-level fixture/admin methods are not authorized application
APIs. Durable halt lifecycle/release, cash-flow policy, broker OrderCalcProfit,
close/cancel, target recovery and Demo round trip remain required product work.
No claim is made that this increment completes SCN-001 or the full Demo goal.
