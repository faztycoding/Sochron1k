# SCN-018 PA01 decision kernel

## Task contract

Implement the first pure, deterministic PA01 decision kernel from Blueprint
sections 06-08. It consumes explicit closed M5/H1 bar evidence and an admissibility
context at a UTC cutoff, then returns BUY, SELL, WAIT or BLOCK plus versioned feature
evidence. It performs no network, database, journal, risk-size, order or strategy
promotion action.

This increment is the calculation boundary required by the future strategy
producer. It does not make `/api/owner/signals` leave `awaiting_source`; persistence
and scheduling remain a separate task.

## Versioned PA01-v1 rules

- AI is disabled. M5 is the signal timeframe and H1 supplies structure.
- A swing uses exactly two left and two right bars. The pivot price must be strictly
  greater/less than every comparison value; ties produce no pivot. It is available
  only when the second right bar is closed and available.
- BUY structure requires the latest two confirmed H1 swing highs and lows to be HH
  and HL. SELL requires LH and LL. Incomplete or mixed structure is WAIT.
- Calculations use at most the latest 100 as-of bars per timeframe. At least 60
  contiguous M5 bars and 12 contiguous H1 bars are required; shorter warm-up is
  WAIT and a gap inside the selected window is BLOCK. This fixed warm-up is part
  of `PA01-v1` and cannot change within an evaluation.
- M5 uses EMA20, EMA50, Wilder ATR14 and Wilder ADX14. BUY requires EMA20 > EMA50,
  ADX >= 20, the previous low <= its EMA20 and the latest close > previous high.
  SELL mirrors every comparison.
- ATR seeds at the mean of the first 14 true ranges including the first bar's own
  range. Directional movement starts at zero; the first ADX is the mean of DX at
  indices 13-26. These initialization details are part of `PA01-v1`.
- Proposed stop is beyond the lower/higher of the two setup bars by 0.20 ATR. Stop
  distance measured from confirmation close must remain within 0.50-2.00 ATR.
- Spread must be at most 0.10 ATR. The future entry adapter must use the next tick,
  reject drift beyond 0.20 ATR, expire after 30 seconds, set target from actual fill
  at 2R and time-exit after 12 M5 bars. This kernel records those parameters but
  cannot claim entry, fill, SL or TP.
- Price staleness, market closure, unexplained/data gaps longer than 72 hours, news
  pause, existing exposure or a pending order produce BLOCK. A shorter explicitly
  classified market-close gap is retained without synthesizing bars. A valid but
  absent setup produces WAIT.

## In scope

- Strict positive Decimal OHLC/spread evidence with closed-time and `available_at`.
- As-of filtering: rows available after the cutoff cannot affect the decision.
- Exact interval and identity checks, duplicate/revision rejection and recent M5/H1
  gap detection without filling missing bars.
- Deterministic EMA, Wilder ATR/ADX and delayed H1 pivot features.
- Stable decision/setup/evidence identifiers derived from canonical evidence.
- Symmetric BUY/SELL fixtures plus leakage, repaint, gap, blocker and boundary tests.

## Out of scope

- M1-to-M5/H1 aggregation, Supabase reads/writes, feature/signal persistence,
  durable scheduling, news retrieval, actual spread/feed status integration,
  probability output, backtesting, labels, evaluation statistics or promotion.
- Position sizing, account/contract admission, command creation, MT5 execution,
  hosted writes, deployment or a live-account path.

## Acceptance criteria

- **AC-01 Strict evidence:** malformed, timezone-naive, forming, non-positive, off-grid,
  duplicate, revised, cross-symbol/feed or misaligned bars fail closed before a
  decision is returned.
- **AC-02 No lookahead:** only bars whose close and `available_at` are at or before
  the cutoff participate. Appending arbitrary future/right bars cannot change an
  earlier decision or confirm a pivot early.
- **AC-03 Indicator parity:** EMA20/50 and Wilder ATR14/ADX14 match committed exact
  Decimal reference fixtures, including initialization and zero-range handling.
- **AC-04 Structure timing:** pivots use strict L2/R2 comparisons and expose their
  formed and confirmed times. Fewer than two confirmed highs/lows is WAIT.
- **AC-05 PA01 symmetry:** exact trend, pullback, breakout, ADX and stop-distance
  rules generate BUY/SELL symmetrically; mixed/absent conditions remain WAIT.
- **AC-06 Deterministic blockers:** stale/closed market, recent gaps, news pause,
  spread cap, exposure and pending work produce fixed BLOCK reason codes. No risk
  or execution state can be overridden by the strategy.
- **AC-07 Evidence output:** every decision records strategy/parameter version,
  cutoff, formed/confirmed/expiry times, exact features, source evidence IDs and
  execution parameters without claiming an order or outcome.
- **AC-08 Pure boundary:** static and behavioral tests prove no HTTP, Supabase,
  filesystem mutation, AI, command, executor or random/time-now authority exists.
- **AC-09 Regression gates:** affected Python/package/container checks pass without
  weakening existing assertions.

## Evidence boundary

A passing SCN-018 proves only the deterministic PA01-v1 calculation for committed
fixtures. It does not prove an edge, data-feed parity, indicator parity with a
chosen external library/MT5 implementation, correct aggregation, producer uptime,
cost realism, Demo execution or release readiness. PA01 remains a candidate until
temporal backtests, out-of-sample/shadow evidence and explicit promotion review.
