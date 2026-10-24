# Review CORE-007 contract, round 2 · base main · head 0feef0e · reviewer: pre-review (Claude subagent `fresh-eyes-reviewer`, fresh context, not the round-1 reviewer; contract review before tests under the owner's standing delegation of 2026-10-24)

Recorded by the implementer from the subagent's final report, unchanged in substance (tables condensed).

## Round-1 verdicts
F1 closed (every AC-01 number recomputed by hand and equal as Decimals; see F24) · F2 closed · F3 closed (validation loose, F26) · F4 closed (duck typing, Rollover, AC-06 forbids `data`; consistent with CORE-006) · F5 closed as a rule (examples and time source, F25) · F6 closed with defects (F20, F21) · F7 closed with defects (F27, F29) · F8 closed · **F9 still open** (F16, F17; F23) · F10 closed (not cited by ID, F31) · F11 closed with residue (F26–F28) · F12 closed · F13 closed · **F14 still open** (F18, F19) · F15 closed (no AC asserts versions, F30).

AC-01 by hand: long gross 34.4000, spread 0.48000, commission 0.00, slippage 0.20000, swap 1.007600, total 1.687600, net 32.712400, r 1.308496, stop 4000.90; short gross 34.4000, spread 0.48000 (exit), slippage 0.20000, swap 0, total 0.68000, net 33.72000, r 1.3488, stop 4041.86 (not stated in v1.1). No numeric mismatch; string forms differ (`1.687600` vs `1.68760`). A Wednesday-night hold would give swap 3.0228, total 3.7028, net 30.6972, r 1.227888.

## New findings
| ID | Sev | Kind | Line | Evidence | Minimal fix |
|----|-----|------|------|----------|-------------|
| F16 | Medium | confirmed | 51–52 | `simulate_trade(..., exit_index=None, risk_money, actual_risk)` puts required parameters after a default (SyntaxError); exit_index meaning, bounds, entry_index rules, actual_risk None and errors undefined. | Keyword-only parameters after `rollover`; one sentence per argument. |
| F17 | Medium | confirmed | 51, 79, 101 | `Trade.data_flags` cannot be reproduced by `simulate_trade` (no flags); the exit_index that reproduces stop or end_of_data trades is unstated. | `data_flags` argument; exit_index mapping per exit_reason. |
| F18 | Medium | confirmed | 79, 101 | AC-05's no-look-ahead clause fails for a correct implementation when truncating inside the bar of an intrabar stop (Skip at that bar disappears; data_flags change on re-aggregation). | Define the truncation procedure and the protected records. |
| F19 | Medium | confirmed | 79 | The data_flags span has two readings at each end; a stale fill after a data gap is visible only on the fill bar's `unexpected_gap`. | Span = entry decision bar through the M15 bar holding the exit M1; name the stale-fill marker. |
| F20 | Medium | confirmed | 44, 58, 62, 65, 98 | Whether `*_spread_points` hold the raw spread or the resolved `s` is unstated. | The `s` actually used, both sides, every exit kind. |
| F21 | Medium | confirmed | 62–63, 75 | Every gap bar also satisfies the intrabar row, so row order would fill a gap at the stop (optimistic); `stop_distance ≤ spread` compares price with points. | Check the open first; write `stop_distance ≤ s·p`. |
| F22 | Medium | question | 88, 97–100, 53 | ACs say "When `run`", which needs data that drives the real `decide` (warm-up, ATR exactly 6.00); CORE-006 is not implemented on the branch. | Assert fills/SL/costs through `simulate_trade`; keep `run` for event order; AC-05 ties them. |
| F23 | Medium | question | 21, 53; H001 §7 | No long-only baseline and no side filter; random entries need the same loop. | `sides` argument on `run`; record where the eligible-bar predicate belongs. |
| F24 | Low | confirmed | 97 | AC-01 has no dates (a Wednesday hold changes swap); short stop/lots/R implied; trailing-digit strings. | Fix the dates; state short values; compare by Decimal value. |
| F25 | Low | confirmed | 82, 100 | Nights use "entry_time/exit_time" but Trade has raw times; `time_utc` vs `to_utc` undefined; examples lack clock times; no DST golden. | Use the M1 `time_utc`; reject mismatches; add times and a DST golden (Fri 2026-10-30 14:00 UTC → Mon 2026-11-02 21:30 UTC = (1,0)). |
| F26 | Low | confirmed | 35, 42, 85, 99 | AC-03 error classes for bad sizer output not pinned. | List each check, its class and when it runs. |
| F27 | Low | confirmed | 43, 85 | equity ≤ 0 after a trade, Rollover validation (unknown zone raises KeyError), empty inputs undefined. | One line each. |
| F28 | Low | confirmed | 85 | STOP-level bars (negative spread, inconsistent OHLC, non-positive price) pass `run`; a negative spread silently delays a short stop. | Reject them in `run` or require R1 to exclude STOP days. |
| F29 | Low | confirmed | 73–74, 98 | "SL inside t then decide gives exit" cannot occur (position is flat). | Reword: SL inside t, then an opposite entry at t+1 is allowed. |
| F30 | Low | confirmed | 39, 50, 76–79, 94 | No AC asserts Skips, equity points, data_flags, versions, spread None, argument validation. | Fold into AC-02 and AC-03. |
| F31 | Low | confirmed | r1:31; contract:3 | The r1 answer note points to a "v1.1 answers" block that does not exist. | Add an F→line map. |
| F32 | Low | question | — | No performance budget for R1's workload (63 runs + 1,000 random runs over ~2.5M M1). | State a budget or record the risk. |

Checked, nothing found: AC-01 arithmetic; no double-counted spread on either side (stop loss = 24.00 + slippage both sides); `stress()` leaves prices and stop_price unchanged; `SizeDecision` mapping consistent with D1; `AggregatedBar` has `.bar` and `.flags`; module map and AC-06 consistent; CORE-006 skip/hold/exit semantics match the event order; the nights examples hold before 17:00 NY; red flags 1 prose group, none from 0feef0e.

Not checked: CORE-006 implementation (absent); pytest (docs only); the F16 SyntaxError was inferred, not executed; broker rollover time and MT5 spread meaning (external, [A]); real R1 runtime.

Ready for test authoring: no
Findings open: 19

## Answers (implementer, 2026-10-24, owner's standing delegation "เอา recommanded ทุกอัน")
All answered in contract v1.2 ("Answers to contract reviews" block maps every finding to its section). F23 takes the reviewer's `sides` option; F27 keeps measured results when equity is exhausted (no new entries) rather than raising; F28 rejects STOP-level bars in `run`. A third contract review checks v1.2 before tests.
