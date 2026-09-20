# SCN-030 deterministic PA01 tick-replay backtest

## Task contract

Add an offline, explicit operator that replays the existing PA01 kernel at every
eligible M5 decision boundary, labels accepted setups from ordered Bid/Ask ticks,
and emits the canonical `sochron.research-bundle.v1` consumed by SCN-029. It must
fail closed on incomplete or non-causal evidence and must not create a command,
contact MT5/Supabase, promote a strategy, or enable Auto Trading.

The input is a retained point-in-time research artifact: already closed M5/H1 bars
with their real availability times, ordered ticks with event and received times,
and an explicit policy observation for every evaluated M5 boundary. The operator
does not acquire data or claim that supplied evidence is representative.

## In scope

- Strict canonical JSON input with feed/symbol/code/parameter identity, one
  temporal evaluation window, exact bars, ticks, policy observations, execution
  sizing and fixed cost scenario.
- Re-run `PA01-v1.0.1` at every eligible in-window M5 close. The caller cannot
  submit an action, setup, label or performance metric.
- Use the first received tick after a confirmed BUY/SELL decision and before its
  30-second expiry. Reject an entry whose executable price drift exceeds 0.20 ATR.
- Use Bid for BUY liquidation and Ask for SELL liquidation. The first ordered tick
  to reach SL or TP determines `SL_FIRST`/`TP_FIRST`; otherwise close from the last
  quote known by the twelve-M5-bar horizon and label `TIME_EXIT`.
- Preserve WAIT/BLOCK decisions and expired/drifted entries as excluded records.
  Do not count them as wins or losses.
- Derive one setup-to-flat outcome, exact gross P/L before the configured fixed
  spread/slippage/commission/swap/operating costs, and a per-tick mark-to-market
  equity path while exposure is open.
- Emit one byte-stable SCN-029 bundle, with its dataset hash derived only after all
  labels and equity samples are fixed. Write it atomically with owner-private mode.
- Package an explicit CLI. With no action or invalid evidence it performs no
  external request and produces no partial accepted output.

## Out of scope

- Raw-tick capture from MT5, Parquet retention, feed licensing, data repair or
  conversion of a broker export into the strict replay input.
- SMC01, ICT01, Order Flow, news-AI inference, probability models, optimization or
  tuning.
- Selecting a spread/slippage/cost scenario, deciding position size, inferring
  swap, or claiming the supplied point value matches a broker contract.
- Strategy promotion, active-version changes, risk admission, command creation,
  MT5 execution, hosted writes or deployment.

## Acceptance criteria

- **AC-01 Canonical bounded evidence:** accept one canonical JSON object no larger
  than 64 MiB. Reject floats, duplicate keys, unknown fields, unsafe identifiers,
  duplicate timestamps/IDs, mixed symbol/feed/grid/code identity, non-UTC times,
  Bid above Ask, off-grid prices and more than the bounded bar/tick/sample limits.
- **AC-02 Point-in-time bars:** M5/H1 bars are closed, ordered and supplied with
  `available_at_utc`. PA01 only sees bars available by that decision cutoff.
  Appending a future bar or tick cannot change any earlier decision or label.
- **AC-03 Complete schedule:** evaluate every in-window M5 close whose twelve-bar
  outcome horizon fits wholly inside the evaluation window. Require exactly one
  policy observation bound to each eligible M5 bar; reject missing, extra or
  duplicated boundaries so callers cannot cherry-pick signals.
- **AC-04 Kernel parity:** derive each action by calling the repository's pinned
  `evaluate_pa01`; preserve its setup/decision/parameter hashes and causal times.
  Input contains no caller-authored action or label field.
- **AC-05 Entry semantics:** select the first tick with event time strictly after
  confirmation and availability no earlier than its event. BUY fills at Ask and
  SELL at Bid. Missing next tick, expiry, drift, or invalid stop becomes a named
  rejected record and never a fabricated fill.
- **AC-06 Tick-ordered exit:** compare every subsequent ordered tick through the
  twelve-M5 horizon using the executable liquidation side. TP/SL is determined by
  the first matching tick; same-timestamp or reordered evidence is invalid. If no
  threshold is reached, use the final observed executable quote by the horizon for
  `TIME_EXIT`. Missing horizon coverage fails closed.
- **AC-07 Cost decomposition:** the configured fixed spread must be no smaller than
  the maximum observed tick spread. Gross P/L uses the Bid path and therefore
  excludes spread; SCN-029 deducts the fixed spread, slippage, commission, swap and
  operating cost exactly once. Initial risk uses the executable fill, broker-side
  stop and supplied point value/volume. Costs may make a TP-labelled trade net
  negative; metrics use net P/L rather than the label name.
- **AC-08 Equity path:** one position at most. Include the exact window endpoints,
  at least one open-exposure mark per closed trade, every tick mark while exposed,
  immediate configured costs, and final equity equal to initial equity plus all net
  outcomes. No interpolation or invented tick is allowed.
- **AC-09 Split integrity:** purge decision boundaries whose label horizon crosses
  the window edge; non-train splits retain the prior-development cutoff and embargo
  required by SCN-029. Bars/ticks may precede the window only as warm-up and can
  never become an in-window label.
- **AC-10 Bundle compatibility:** output passes `bundle_dict`, `ResearchBundle`
  validation and `evaluate_bundle` without alteration. Same input and revision
  produce byte-identical output and evaluation fingerprint.
- **AC-11 Failure paths:** malformed/future evidence, bar or tick append leakage,
  schedule omission, stale quote, missing horizon quote, spread understatement,
  overlapping exposure, cost overflow, output-size overflow and output-path failure
  leave no accepted bundle or partial replacement.
- **AC-12 Packaging and regression:** targeted kernel/backtest/evaluator tests,
  complete Python regression, installed-wheel checks, container checks and source
  secret scans pass. Hosted Supabase, MT5 and non-synthetic market-data validation
  remain explicitly `NOT RUN` until separately authorized inputs exist.

## Evidence boundary

A passing SCN-030 run proves deterministic replay mechanics for the supplied
artifact. It does not prove the source bars/ticks are complete, licensed or
representative, that cost/contract assumptions match the selected Demo account,
that PA01 has an edge, or that the candidate is eligible for promotion.
