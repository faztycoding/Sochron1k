# SCN-011 Durable position management and halt response

2026-09-20, High assurance, base
`17405ed51e3979e83608476923f89b8d49f14512`. Local simulator implementation
under the full Demo goal; no MT5 account operation, execution endpoint or halt
release is authorized. Extends SCN-001 AC-04/05/06/07 and SCN-010.

## Required outcome

Represent cancel-pending and close-position as separately idempotent, durable
management commands bound to one existing logical entry. Journal each management
intent and attempt before invoking an executor. Apply only complete broker evidence,
retain the parent exposure until all pending and position volume is confirmed gone,
and preserve UNKNOWN after any ambiguous invocation. A risk halt must not prevent
position management, but it must continue to prevent new entries.

MT5 remains authoritative. For a partially filled entry, cancel the pending
remainder before closing the filled position. A cancel request cannot be reported
cancelled until the pending order is confirmed absent; a close request cannot be
reported closed until exit deals and zero remaining position volume are confirmed.
One request may yield multiple unordered transactions, so snapshots are cumulative
and existing tickets/deals cannot disappear or change.

## Local acceptance

- AC-01: Add immutable management intent/evidence models with bounded identifiers,
  aware expiry/observation times, exact Decimal volumes and operation-specific
  validation. Bind every close/cancel to the parent command, account, experiment
  and symbol. Do not accept browser/account-selected broker tickets or volumes.
- AC-02: Add additive WAL journal tables for management commands, transitions,
  attempts, outcomes and exit deals. Reserve idempotency transactionally; a matching
  duplicate returns the recorded operation and a changed payload conflicts. Allow
  at most one nonterminal management command for a parent exposure.
- AC-03: Derive cancel volume from broker-confirmed pending volume and close volume
  from broker-confirmed open position volume. Refuse close while a pending remainder
  exists and refuse cancel when none exists. Keep the parent exposure slot through
  SENT, UNKNOWN and partial close. Release it only after broker-confirmed rejection
  with no fill, full cancellation with no position, expiry with no position, or
  full close.
- AC-04: Recheck explicit startup identity/generation and durable risk scope before
  management dispatch. Halts are allowed for management and remain latched; baseline,
  account, experiment or executor changes deny mutation. Missing journal evidence,
  stale/incomplete inventory or executor mismatch sends nothing.
- AC-05: Reconcile cumulative entry/cancel/close evidence transactionally. Validate
  requested = filled + pending + cancelled, closed <= filled, entry deal sum,
  management completed + remaining, immutable tickets/deals and operation-specific
  terminal states. Invalid/regressing/foreign evidence changes no state.
- AC-06: After adapter invocation, timeout, connection failure, malformed response,
  wrong command/target or any ordinary exception persists the management command as
  UNKNOWN with the parent exposure retained. Query-only reconcile may resolve it;
  it never resends or grants startup admission.
- AC-07: Startup inventories active management commands as well as entries and
  applies exact matching snapshots before admission. Missing or unknown management
  evidence keeps startup closed. Terminal historical snapshots are validated but
  cannot resurrect exposure.
- AC-08: Deterministically latch daily/total halt from current Equity and immutable
  baselines in a transaction. Never clear a halt here. Show that halted state blocks
  open submission while cancel/close remains available after explicit startup.
- AC-09: Produce a local final-trade audit only after full close, including parent
  command, entry/exit tickets, exact volumes, gross profit, commission, swap, fee,
  net PnL and close reason. Partial/unknown/unreconciled state is not a final audit.
- AC-10: Add failing-first duplicate, wrong-target, close-before-cancel, partial
  close, timeout-after-effect, restart/query-only, invalid evidence, concurrent
  management, halt persistence and final-audit fixtures. Extend recovery-domain and
  installed-artifact verification for the new schema. Actual MQL5 ordering, account
  mode, fees and target recovery remain NOT RUN.

## Boundary and sequence

The executor contract will expose a management mutation and query separately from
entry send/query. The simulator may model broker acceptance and response loss, but
it cannot prove MQL5 behavior. Official MQL5 documentation states that
`OrderSend` acceptance does not establish execution, one request can generate
multiple transactions whose arrival order is not guaranteed, pending deletion uses
`TRADE_ACTION_REMOVE`, and a position close is a broker deal whose identifiers
must be reconciled.

No HTTP route, UI control, automatic risk-loop dispatcher, actual EA mutation,
MetaEditor artifact, alert delivery, daily rollover or total-halt release is added
by this increment. Those remain separate required work. Public execution readiness
and Auto Trading remain false.
