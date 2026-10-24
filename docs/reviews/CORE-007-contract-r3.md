# Review CORE-007 contract, round 3 · base main · head eee3566 · reviewer: pre-review (Claude subagent `fresh-eyes-reviewer`, fresh context, not the r1 or r2 reviewer; contract review before tests under the owner's standing delegation of 2026-10-24)

Recorded by the implementer from the subagent's final report, unchanged in substance (tables condensed). Two earlier launches of this round ended with "API Error: 529 Overloaded" (server side) before any output; this is the third launch.

## Verdicts on r2 and still-open r1 findings
r1 F9 closed (simulate_trade, bounds, exit_index mapping, invariant, AC-05) · r1 F14 closed (data_flags span and stale-fill marker) · F16 closed (keyword-only, valid Python; leftovers → F35) · F17 closed · F18 closed (three exit kinds walked through the truncation procedure) · F19, F20, F21 closed · F22 closed (the `run` part of AC-02 needs CORE-006) · F23 closed · F24 closed · F25 closed · F26 closed (contradicts D1 → F33) · F27 closed · F28 closed for `run` (simulate_trade → F34) · F29, F30 closed · F31 closed (r2 IDs sit in rows labelled r1, cosmetic) · F32 closed.

## Hand recomputation
Dates: 2026-03-10 Tuesday, 03-11 Wednesday; DST began 2026-03-08 (13:45 UTC = 09:45 EDT). AC-01 long: nights 1, triple 0; gross 34.40; spread 0.48; commission 0; slippage 0.20; swap 1.0076; total 1.6876; net 32.7124; r 1.308496; stop 4000.90 — all match. AC-01 short: stop 4041.86; gross 34.40; spread 0.48; slippage 0.20; swap 0; total 0.68; net 33.72; r 1.3488 — all match. AC-04: (1,0), (5,1), (2,1); DST case 2026-10-30 (Friday) → 2026-11-02 (Monday): Fri 17:00 EDT = 21:00 UTC counted, Mon 17:00 EST = 22:00 UTC after 21:30 → (1,0), and a fixed EDT offset would give 2, so the case discriminates. Stress ×2: 0.96 / 0 / 0.40 / 2.0152, total 3.3752; stop and gross unchanged. No mismatch.

## New findings
| ID | Sev | Kind | Evidence | Minimal fix |
|----|-----|------|----------|-------------|
| F33 | Medium | confirmed | D1 maps `actual_risk = SizeDecision.actual_risk`, which is 0 for below_min_volume (`sizing.py:54-55, 140`); the SizedLots rule required None or > 0 → an R1 run would abort instead of recording Skip. | D1: lots 0 → `SizedLots(None, risk_money, None, reason)`; lots None ⇒ actual_risk None. |
| F34 | Medium | confirmed | Only `run` rejected STOP-level M1; `simulate_trade` would let a negative spread lower the short's ask (late or missed stop) — the baseline path in CORE-008. | `simulate_trade` applies the same per-M1 checks to every M1 it reads, BacktestError before any fill. |
| F35 | Low | confirmed | Unlisted domain cases: side outside {long, short}, stop_distance ≤ 0, risk_money ≤ 0 in simulate_trade, actual_risk ≤ 0, empty/unknown sides, non-finite Decimals (InvalidOperation). | Each → BacktestError before any fill. |
| F36 | Low | question | Whether Rollover validates in `__post_init__` or at use. | Validate in `__post_init__`; run/simulate_trade require exactly Rollover. |
| F37 | Low | question | A long-only run records `decide` skips of short signals because Decision carries no side. | State that decide's skips are recorded whatever `sides` is. |
| F38 | Low | question | AC-06 allows stdlib `zoneinfo`/`astimezone`, against "all time conversion goes through one time module". | Backtest converts time only through timebase; add to AC-06. |

AC status (contract level): AC-01 PASS, AC-02 PASS/UNKNOWN (the `run` part depends on CORE-006's locked decide), AC-03 FAIL before F33–F36, AC-04 PASS, AC-05 PASS, AC-06 PASS (F38 scope), AC-07 PASS. Seven ACs cover the contract.

Checked, nothing found: the fill table algebra (no double spread, gaps at least as bad as stops, ambiguous exits not optimistic); D4 nights conservative against a UTC-midnight rollover; run ≡ simulate_trade mapping; no look-ahead; the R1 STOP-day cut must be re-validated before aggregate; nominal R consistent with H001's "24 R ≈ 6%"; red flags: one prose group, none from CORE-007 commits.

Not checked: CORE-006 implementation (absent); pytest; external [A] facts (broker rollover, MT5 per-bar spread meaning — if it is the minimum spread, short stops and spread costs come out optimistic); R1 runtime.

Ready for test authoring: no. F33 and F34 each need a one-line contract fix before tests lock; F35–F38 can go in the same edit.
Findings open: 6

## Answers (implementer, 2026-10-24, owner's standing delegation "เอา recommanded ทุกอัน")
All six answered in contract v1.3 with the reviewer's minimal fixes (F34 option 1: simulate_trade validates). The "Answers to contract reviews" table maps each to its section.
