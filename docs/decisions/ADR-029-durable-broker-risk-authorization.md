# ADR-029: durable broker-bound risk authorization

- Status: Accepted
- Date: 2026-09-20

## Context

The existing API sizes an entry conservatively but sends only volume, entry and SL
to the executor. A mutation EA can calculate current entry-to-SL loss using
`OrderCalcProfit`, but without the admitted account-currency limit and explicit cost
allowance it cannot decide whether current broker conditions still fit the
authorization. Recomputing daily/experiment state inside MT5 would duplicate the
durable Python risk authority and create divergent baselines.

## Decision

Carry two account-currency decimals on entry dispatches: `risk_limit`, the remaining
risk admitted at sizing time, and `cost_budget`, the cost allowance for the exact
selected volume. Persist them one-to-one with the dispatch attempt in the same
SQLite transaction as the SENT transition. Require them throughout the adapter and
wire; management commands use explicit nulls.

The future EA will calculate absolute current entry-to-SL P/L in account currency
using `OrderCalcProfit` and deny the mutation unless calculated loss plus
`cost_budget <= risk_limit`. It must not increase either value, reinterpret currency
or treat `OrderCheck` success as risk approval.

## Consequences

The broker-bound preflight can detect adverse price drift without owning halt or
baseline policy. Exact authorization is recoverable after API/process failure and
stable on polling replay. The command schema changes before any mutation artifact
exists, avoiding a compatibility path that could omit the fields. Existing local
journals gain an additive authorization table; inconsistent legacy in-flight state
remains unreconciled rather than receiving invented limits.
