# ADR-031: default-off MT5 Demo mutation boundary

- Status: Accepted as a source checkpoint
- Date: 2026-09-20

## Context

The API polling bridge and pure MQL codec define a safe command/evidence wire, but
they cannot mutate or observe a broker account. Adding `OrderSend` without a local
write-ahead record, exact Demo identity, restart reconciliation and cumulative MT5
evidence would allow a lost response or terminal restart to create duplicate or
misreported exposure.

## Decision

Add one separately default-off Expert Advisor for a single exact Demo
account/server/currency/margin-mode/chart-symbol/magic identity. It uses only the
fixed loopback execution origin and a dedicated terminal-local token. A non-shared
lock and bounded append-only ledger are acquired before networking. The ledger
preserves the original mutation time, exact command bytes and exact outcome bytes;
`PREPARED` and flushed `SEND_STARTED` precede the only `OrderSend` call site.

Before an entry, the EA requires an empty stable account scan, a fresh in-session
tick, supported market/SL/filling modes, exact price and volume grids, bounded
spread/deviation, side-correct stops, sufficient margin, and an account-currency
`OrderCalcProfit` loss from the adverse configured deviation plus authorized cost
not exceeding the dispatched risk limit or 0.25% of current MT5 Equity,
conservatively rounded in account currency.
Cancel and close requests bind to the current MT5 order or position.

`OnTradeTransaction` only marks reconciliation dirty. Bounded timer work rereads
current state and history, emits cumulative typed evidence, and journals the exact
outcome before upload. A send return is not a fill; missing or conflicting evidence
is uncertain. Confirmed rejection additionally requires an allowlisted return code
and a fresh no-effect scan. Broker-side protection is true only when the current
position carries the intended SL.

## Consequences

The repository now contains the intended broker mutation boundary, but only as
uncompiled source. Static guards and mutation tests constrain reviewed identifiers,
call-site count, ordering, fixed files/routes and default-off behavior; they cannot
prove MQL syntax, exclusive file semantics, flush durability, callback timing,
broker calculations or actual fills. Those remain selected-host gates, followed by
an explicit owner-authorized bounded Demo open-to-close action. There is no live
account path and Auto Trading remains disabled.
