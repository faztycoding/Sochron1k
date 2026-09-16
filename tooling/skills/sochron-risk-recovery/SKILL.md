---
name: sochron-risk-recovery
description: Implement or verify Sochron1k position sizing, loss limits, SQLite journal, idempotency, persistent halts, crash recovery and fault tests. Applies to deterministic risk and recovery engineering, not strategy recommendations or live trading.
metadata:
  version: "1.0.0"
---

# Sochron1k risk and recovery

Read the repository's current `docs/product.md`, task contract and `docs/risks/risk-register.md`. Use blueprint sections 13-16 and 22-23 for definitions. Product policy governs numeric thresholds; these baseline values describe blueprint v1.1 and must be revisited if the owner explicitly versions that policy.

## Risk semantics

- Risk per trade is 0.25% of latest Equity, daily loss is 0.75% of the Thailand-day starting Equity, and experiment loss is 2% of initial experiment Equity. In fractional calculations use 0.0025, 0.0075 and 0.02. Keep percentage and fraction units explicit at config boundaries.
- Equity includes floating PnL and costs. Daily and experiment floors are anchored to their own baselines, not the equity high-water mark. Report peak drawdown separately. Do not quietly increase the experiment floor after gains.
- Opening budget is bounded by per-trade allowance and remaining daily/experiment headroom, with defined costs and existing reservations accounted for. Stop-distance loss is an estimate under stated fill assumptions; gaps and slippage can exceed it.
- Use broker `OrderCalcProfit` in account currency for the proposed side, volume and entry/SL. Do not convert its account-currency result a second time. Missing conversion data or failed calculation means no entry.
- Use Decimal or explicit scaled integers in Python for money and volume boundaries. In MQL5, check floating-point rounding conservatively. Round volume down to the permitted grid, then recalculate the resulting loss, costs and margin. Reject if minimum volume is too large. Reject invalid/non-finite prices, nonpositive metadata, wrong-side stops and unavailable margin.
- Enforce one logical position or pending entry. Reserve capacity and risk atomically before dispatch. A partial fill and its remaining quantity belong to the same command; do not count that as permission for another entry.
- At or beyond a limit, persist the halt, cancel pending entries and attempt the authorized close while tracking actual results. Stale feed, journal failure and ordinary pause stop entries while existing positions still require management.
- Daily halt may clear only on the next Asia/Bangkok day after health checks and reconciliation. Total halt requires the owner's recorded review and a new experiment; restarting, a config edit, or AI output cannot clear it. Deposits/withdrawals or Demo capital resets invalidate the ongoing experiment assumptions.

## Durable state and recovery

Model idempotency scope as account/experiment/operation plus key and canonical payload fingerprint. A repeated matching request returns the recorded result; changed payload is a conflict. Keep history immutable and put state changes in transactions with uniqueness constraints, not only in application prechecks.

Use SQLite WAL with an explicitly verified durability configuration. Atomically persist command, reservation and outbox intent before dispatch. Design for crash windows before send, during send, after acceptance and before acknowledgment persistence. A database transaction cannot make a remote broker write exactly once.

On startup, lock entries, restore baselines/halts/outstanding commands, verify executor identity, query broker orders/positions/history, and reconcile. Quarantine foreign or unresolved state. Broker query failure keeps reconciliation incomplete. Replaying the outbox blindly is not recovery.

Handle journal disk-full/permission errors without pretending evidence was saved. Management of an existing position must remain available even when storage fails. An entry whose dispatch may already have happened remains uncertain until reconciled. Backups must be consistent with WAL; use SQLite's online backup API or a verified quiescent procedure, then restore to an isolated database and check domain invariants.

## Fault tests

Use real temporary SQLite databases, independent connections/processes where concurrency matters, a controlled clock and an adapter simulator with observable effects. Tests should assert balances/state/adapter effects, not copies of the implementation formula.

Cover at least the scenarios affected by the diff: exact budget boundaries; loss from floating PnL; min-volume rejection; fractional volume steps; non-USD accounts; same-key concurrency and conflicting payload; kill after acceptance before acknowledgment; restart with persistent total halt; Thailand midnight; journal write failure; unreachable broker during reconciliation; SL rejection; partial fill; duplicate deal delivery. Construct one failing reproduction before the fix when practical.

Report the oracle and evidence scope. Formula tests alone do not establish broker compatibility; process-crash tests alone do not establish power-loss durability.

## References

- [OrderCalcProfit account-currency result](https://www.mql5.com/en/docs/trading/ordercalcprofit)
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html)
- [WAL](https://www.sqlite.org/wal.html)
- [SQLite online backup](https://www.sqlite.org/backup.html)
- [pytest](https://docs.pytest.org/en/stable/)
- [Hypothesis](https://hypothesis.readthedocs.io/en/latest/) when property/state-machine tests add coverage
