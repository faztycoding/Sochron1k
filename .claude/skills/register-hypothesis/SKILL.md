---
name: register-hypothesis
description: Registers a Sochron1k trading or research hypothesis BEFORE any data is run on it. Interviews the owner until the mechanism, the unambiguous entry, exit and size rules, parameter ranges, variant budget, data and holdout contract, costs, baselines and numeric fail conditions are complete, then writes docs/hypotheses/H<nnn>-<slug>.md marked "ยังไม่พิสูจน์ (UNPROVEN)" and commits it. Use whenever the owner has a strategy idea, mentions PA, SMC, ICT, a setup, an indicator, a "กลยุทธ์ใหม่", "ลองระบบนี้", "backtest ไอเดีย", or before any backtest or experiment.
argument-hint: "[idea name]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P31; ch.34"
---

# Register a hypothesis before touching data

An AI can try hundreds of strategy variants in an hour, and the best of many searches is the most
biased number you can produce. Committing the rules and fail conditions first is what makes a
later result mean anything. Once committed, the file is immutable (enforced by a hook and CI); a
changed idea gets a new H number.

## Interview (Thai, one topic at a time; the owner decides, you make it testable)
1. **Mechanism**: who loses to us and why? What market behavior creates the edge? (Not "the indicator says so".)
2. **Market and scope**: symbol (XAU/USD as quoted by the broker), timeframe(s), sessions, research period.
3. **Rules two people would apply identically**: entry, exit (stop loss, take profit, time exit),
   position size, and what invalidates a setup. Include a worked example on one concrete bar
   sequence. All times state the time module's convention (UTC, with the broker offset recorded).
4. **Parameters**: each tunable parameter with its allowed range, plus the maximum number of variants to try (the variant budget).
5. **Data contract**: source, dataset snapshot ID or how it will be built, train and validation
   periods, the holdout cutoff date and who keeps the holdout (it never lives in the research checkout).
6. **Costs**: spread from real bid/ask, commission, slippage, swap; the re-test at 2x costs.
7. **Baselines**: random-entry with symmetric size and holding time over N runs; any other simple baseline.
8. **Fail conditions (numbers, on the holdout)**: for example minimum net expectancy after costs,
   minimum number of independent trades, a maximum drawdown limit, robustness to ±10% parameter
   changes, and the result relative to the random-entry distribution.
9. **Decision rule**: go, stop or insufficient data, exactly as docs/HANDBOOK-CORE.md §15 defines them.

## Write and commit
- Create `docs/hypotheses/H<nnn>-<slug>.md` from `docs/hypotheses/_TEMPLATE.md` (next free number).
  The first line after the title must be `สถานะ: ยังไม่พิสูจน์ (UNPROVEN)`.
- Commit it alone: `research(hypothesis): register H<nnn> <slug>` with `Refs: H<nnn>`.
- Return the path and the commit hash. Only after this commit may a contract run data on the idea.

## Must not
Run or peek at a backtest before the commit; fill in rules or thresholds the owner did not
decide; edit a committed hypothesis (write H<nnn+1> instead).
