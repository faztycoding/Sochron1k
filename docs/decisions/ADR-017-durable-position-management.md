# ADR-017 Durable position management and halt response

2026-09-20; SCN-011, builds on `17405ed` and ADR-016. Decision: model
cancel-pending and close-position as durable management commands distinct from the
original entry command. This is a local simulator boundary; it does not expose an
HTTP control, operate MT5 or enable Auto Trading.

## Command and evidence boundary

Every management request has its own command ID, idempotency scope, payload
fingerprint, transition history and dispatch attempt. It binds to one existing
entry command and repeats the entry account, experiment and symbol. Requested
volume is derived from durable broker evidence: pending volume for cancel and open
position volume for close. A caller cannot choose a broker ticket or close volume.
Only one nonterminal management command may exist for a target at a time.

The journal records the management command and attempt before adapter invocation.
A partially filled entry must first cancel its pending remainder; only then may its
filled position be closed. The exposure reservation remains through SENT, UNKNOWN
and partial close. It is removed only after validated terminal broker evidence says
there is no pending or open position.

Management is allowed while daily or total halt is latched because a halt must stop
new exposure, not prevent risk reduction. The same exact durable risk record,
account identity, executor generation and startup inventory are still required.
This module can only latch a daily or total halt from Equity and fixed baselines; it
cannot clear one, roll the risk day or create a new experiment.

## Reconciliation and final audit

Broker snapshots are cumulative. Entry and exit deal identity and financial fields
are immutable; ordering is not significant. Completed volume may only increase,
remaining volume may only decrease, and the target entry lifecycle must balance
requested, filled, pending, cancelled and closed volume exactly. Close evidence
needs exit deals and a matching position; cancel evidence cannot contain deals.

Any ordinary exception or malformed/conflicting result after adapter invocation is
ambiguous. The management command becomes UNKNOWN, admission is cleared and no
replacement is sent. Query-only reconciliation may apply later cumulative evidence
but does not grant startup admission. Startup now requires all active management
snapshots as well as entry snapshots and validates their freshness and binding.

A final local trade audit is available only after full broker-confirmed close and
no active exposure/management command. It joins entry and exit identifiers,
volumes, profit, commission, swap and fee using exact Decimal arithmetic and retains
the close reason. It is local evidence, not an MT5 statement.

## Rationale and limitations

MQL5 documents that a successful `OrderSend` return does not establish execution,
one request can generate multiple trade transactions whose arrival order is not
guaranteed, and a pending-order removal uses `TRADE_ACTION_REMOVE`. Therefore a
single synchronous response cannot be the source of truth; order, deal and position
evidence must be reconciled independently. See the official
[OrderSend](https://www.mql5.com/en/docs/trading/ordersend),
[OnTradeTransaction](https://www.mql5.com/en/docs/event_handlers/ontradetransaction)
and [trade request action](https://www.mql5.com/en/docs/constants/tradingconstants/enum_trade_request_actions)
documentation.

The simulator proves journal behavior and failure handling only. Actual MQL5
netting/hedging semantics, symbol contract details, partial close behavior, fees,
terminal restart, exclusive executor ownership and target reconciliation remain
unverified. No automatic halt dispatcher, emergency-close authority, daily
rollover, total-halt release or broker operation is introduced.
