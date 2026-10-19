# H<nnn> — <short name>
สถานะ: ยังไม่พิสูจน์ (UNPROVEN)

Registered <YYYY-MM-DD> by <owner> · registration commit: (the commit that adds this file)
<!-- After commit this file is immutable (hook + CI). A changed idea becomes H<nnn+1>.
     Results go to the registry and to a separate result note, never into this file. -->

## 1. Mechanism (why should this edge exist? who loses to us?)

## 2. Market and scope
- Symbol (broker quote name):
- Timeframe(s):
- Sessions / hours (time-module convention, UTC + broker offset):
- Research period:

## 3. Rules (two people must decide the same bar identically)
- Entry:
- Stop loss:
- Take profit / exit:
- Time exit:
- Position size:
- Invalidation:
- Worked example on a concrete bar sequence:

## 4. Parameters and variant budget
| Parameter | Allowed range | Default |
|-----------|---------------|---------|
- Maximum number of variants to try:

## 5. Data contract
- Source and snapshot ID / build method:
- Train period:
- Validation period:
- Holdout cutoff date and custodian (never inside the research checkout):

## 6. Costs
- Spread (from real bid/ask), commission, slippage, swap:
- Stress test: all costs × 2

## 7. Baselines
- Random entry: N runs, symmetric size and holding time
- Other simple baseline:

## 8. Fail conditions (numeric, evaluated on the holdout)
- Minimum independent trades:
- Minimum net expectancy after costs:
- Maximum drawdown:
- Robustness: parameter ± <x>% must not collapse the result
- Versus random-entry distribution:

## 9. Decision rule
Go / Stop / Insufficient data, as defined in docs/HANDBOOK-CORE.md §15.
