---
name: leakage-audit
description: Read-only audit of Sochron1k's backtester, research pipeline and data handling for future leakage, unrealistic fills, missing costs, wrong time handling, holdout exposure and unlogged experiments. Each finding needs a test that fails before the fix. Use for "leakage", "look-ahead", "ตรวจ backtest", "ตรวจ backtester", before trusting any research result, and for every change to data, features, the backtest engine, the cost model or the registry. Claude's quant-auditor subagent follows this file too.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P32; ch.34"
---

# Leakage and backtester audit

You did not write this backtester; that is why you are auditing it. Results that look too good
are the main risk in this project.

## Setup
Fresh read-only chat. Inputs: the contract or hypothesis (docs/hypotheses/H*.md), and the code
and diff for data, features, strategy, backtest, costs, research and registry.

## Checklist
1. Future data:
   - shift direction, or using the close of a bar that has not closed yet
   - normalization or calibration fitted on the full sample
   - resampling with labels or closed sides on the wrong edge
   - higher-timeframe features joined at bar start instead of availability time
   - news or calendar joined on the wrong timestamp, or using revisions not yet known
   - pivots or zones used before their confirming bars close
2. Trade simulation:
   - buy at ask, sell at bid; spread taken from real bid/ask
   - entry no earlier than the next tick or bar after the signal
   - when stop loss and take profit fall in the same bar without tick order, label it ambiguous
     and report sensitivity (never pick the profitable path)
   - gaps through stops; partial fills; volume steps and minimums
3. Costs: spread, commission, slippage and swap are all present, nothing is counted twice, and
   results are reported again at 2x costs.
4. Time: every conversion goes through the single time module; raw broker timestamps are kept;
   DST transitions are handled; the trading day is defined explicitly.
5. Holdout and registry:
   - research code cannot read the holdout (paths, config or loaders)
   - every run, failures included, is written automatically to the registry with commit, dataset
     ID, parameters and results
   - the number of variants tried is reported
   - the random-entry baseline is symmetric and has many runs
6. Evidence the owner reads personally: the data validation report (PASS/WARN/UNKNOWN/STOP), the
   golden-test results, and the registry count. Each one exists and is current.

## Output
Write `docs/reviews/<TASK-ID>-quant-r<n>.md` in the cross-agent-review format. Every finding
names file:line and gives a concrete failing test that proves the leak or the mis-simulation.
Clean areas go under "Checked, nothing found (and how)".

## Must not
Fix code, run experiments outside the registry, touch the holdout, or judge whether the
strategy is good. That decision belongs to the owner.
