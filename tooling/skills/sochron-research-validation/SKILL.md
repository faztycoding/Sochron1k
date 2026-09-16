---
name: sochron-research-validation
description: Build or audit Sochron1k PA01, SMC and ICT research, market features, backtests, temporal splits, execution-cost models and news-AI evaluations. Use for reproducible strategy evidence, not live execution or promises of returns.
metadata:
  version: "1.0.0"
---

# Sochron1k research validation

Read the current research contract and blueprint sections 06-12 and 15-17 before implementing strategy rules. `docs/product.md` and `docs/architecture.md` identify stage and data ownership. Reuse the provided PDF skill/extractor when available to inspect the exact source section; if unavailable, do not reconstruct detailed PA/SMC/ICT rules from memory or a skill name.

## Reproducible experiment

Record code hash, strategy/parameter version, data/feed hash, timezone semantics, costs, decision horizon, split intervals and seed where applicable. Keep Engineering Demo resets separate from Research Experiment outcomes. A halted research run remains in the record; a new experiment does not erase it.

Start with PA01 and AI disabled, as specified in the blueprint. SMC01, ICT01, OB variants and news filters are separate candidates. One active strategy owns the signal per account. Do not sum correlated indicators into invented independent votes or choose retrospectively between simultaneous strategies.

## Data available at the decision

- Preserve event time, received time and `available_at`. A closed bar is usable only when complete and available. Exclude the forming bar from confirmation logic.
- Pivots requiring two right bars become available after those bars close. Store `formed_at` and `confirmed_at`; tests must prove no earlier signal appears.
- Join higher-timeframe features as of their availability, not their candle start. Preserve gaps and label sampled ticks; do not invent intermediate prices or assume one-second snapshots establish intrabar order.
- Simulate next-tick entry and actual bid/ask direction. Limit touched is not necessarily filled. Respect setup expiry, drift, spread and volume constraints.
- If OHLC permits both SL and TP in the same bar without tick ordering, label `AMBIGUOUS` and report sensitivity; do not select the profitable path or silently drop ambiguous cases.
- Use historical news revisions known at `received_at`; current model summaries of revised news are not historical evidence. Respect Europe/London and America/New_York DST for ICT windows and Asia/Bangkok for daily risk.
- Order Flow remains disabled without entitlement and feed provenance. Broker tick volume is activity proxy data, not global traded volume.

## Evaluation

Split chronologically into train/tune/test; purge labels whose horizons cross boundaries and apply an embargo appropriate to the horizon. Fit normalization and probability calibration on training data only. Preserve a final holdout, use walk-forward checks where appropriate, and record every candidate rather than cherry-picking the best run.

Aggregate partial deals to one setup-to-flat trade outcome. Include commissions, fees, swap, spread and slippage without double counting charges already included in deal PnL. Rejected commands and WAIT are not wins/losses. Report counterfactuals separately from fills.

Report sample size, net expectancy, profit factor with zero-denominator handling, equity-based maximum drawdown including open exposure, uncertainty and cost sensitivity. The blueprint's 200 closed trades is a process minimum for considering promotion, not a statistical guarantee. Account for serial dependence with an appropriate block method when evaluating uncertainty. No profit or win-rate threshold overrides execution and risk gates.

News-AI evaluation must check allowed source IDs, output schema, expiry, latency and token-cost budget. Include malicious news requesting risk changes and invalid/missing-source fixtures. AI has no halt-release or promotion authority; AI-required candidates WAIT on unavailable analysis while the AI-disabled baseline follows its own contract.

## Useful verification scenarios

- Future pivot/right-bar data appended to a dataset cannot change decisions at earlier cutoffs.
- Altering a later news revision cannot change an earlier historical decision.
- A setup touching both stop and target without tick ordering is retained as ambiguous.
- Partial exits plus fees/swap reconcile to the broker's setup outcome.
- Crossing DST changes UTC session windows correctly without shifting the local definition.
- A holdout cannot enter tuning or scaler fitting; features respect `available_at`.

Use notebooks for exploration and testable Python modules for repeatable calculations. Run targeted pytest checks, reference indicator parity fixtures and deterministic replay before claiming an implementation verified. Promotion requires versioned evidence, Demo shadow evaluation and the owner's existing or new authorization for that specific version. Report insufficient evidence plainly and keep the candidate experimental.
