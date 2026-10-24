# Review CORE-007 contract, round 4 (narrow re-check of r3 F33–F38) · head 812207c (contract byte-identical to 0c2fb3f, v1.3) · reviewer: pre-review (Claude subagent `fresh-eyes-reviewer`, fresh context, not the r1–r3 reviewer)

Recorded by the implementer from the subagent's final report, unchanged in substance (tables condensed).

## Verdicts on r3 findings
| ID | Verdict | Evidence |
|----|---------|----------|
| F33 | closed | D1 maps lots 0 to `SizedLots(None, risk_money, None, reason)`; SizedLots: lots None ⇒ actual_risk None. Checked against `risk/sizing.py` (below_min_volume ⇔ lots 0; risk_money always > 0; actual_risk > 0 when lots > 0; reasons non-empty): every adapter output passes, below-min volume reaches step 4 as a Skip. |
| F34 | closed | `simulate_trade` applies the five per-M1 checks to every M1 it reads, BacktestError before any fill. `run` has two more checks that need `rule`/`m15`; the bracketed list fixes the set, so "ชุดเดียวกับ run" is loose wording, not a contradiction. |
| F35 | closed | The domain list runs before any fill in both functions, so BacktestError precedes the costs errors; AC-03 covers it. Side effect: F39. |
| F36 | closed | Rollover validates in `__post_init__`; a non-Rollover is TypeError in run/simulate_trade; "known zone" can be checked through `timebase.to_zone` without importing zoneinfo (KeyError/ValueError caught and re-raised; not executed). |
| F37 | closed | Step 5 records decide's skips whatever `sides` is; step 4 unchanged; CORE-006 `Decision` has no side (v1.1 does not change that). |
| F38 | closed | Time conversion only through timebase, in AC-06; nights can be built from the tzinfo `to_zone` returns; AC-04 DST case re-checked (1,0). |

## New findings
| ID | Sev | Kind | Line | Evidence | Minimal fix |
|----|-----|------|------|----------|-------------|
| F39 | Low | confirmed | 59, 61 | A non-finite `SizedLots.lots` is BadVolume through `check_volume` (line 59) but "every Decimal finite → BacktestError" (line 61, new in v1.3) also applies before any fill, with no order; "Decimal ทุกตัว" has no stated scope (overlaps CostModel and H001Params). | Name the Decimals line 61 covers and either check finiteness in `SizedLots.__post_init__` (BacktestError) or route NaN lots to BadVolume. |
| F40 | Low | confirmed | 180, 4 | Line 180 (committed in 0c2fb3f before any such check existed) said "การตรวจแคบๆ ยืนยันการแก้ v1.3" and paraphrased r3 as ready, while r3 said "Ready for test authoring: no"; line 4 lacked r3's count. AGENTS.md: never claim a state without evidence. | Cite this review file and its verdict; add the r3 and r4 counts. |

AC status (narrow): AC-03 UNKNOWN (F39); AC-06 PASS; others not re-reviewed.

Checked, nothing found: commit contents (0c2fb3f contract +15/−8 plus r3 file; 812207c CORE-006 contract only); D1 vs sizing.py and policy.py; simulate_trade vs run checks; domain list vs costs errors and AC-03; Rollover vs timebase; steps 4–5 vs sides and Decision; time rule vs nights, plan and invariants; red flags: one prose group, nothing from CORE-007 commits.

Not checked: the rest of the contract (excluded); pytest (docs only); CORE-006 implementation (absent); the untracked `docs/handoff/CORE-006.md` (not part of the commit; another writer may be active); the exact exception ZoneInfo raises for every malformed key.

Findings open: 2 (F39, F40). Next round needs to re-check only F39 and F40.

Ready for test authoring: no

## Answers (implementer, 2026-10-24, owner's standing delegation)
F39: `SizedLots.__post_init__` checks every non-None Decimal field is finite (BacktestError raised inside the sizer and passed on); the domain line names the run/simulate_trade Decimals it covers and leaves CostModel and H001Params to their own modules. F40: the DoR line now cites r3 and r4 with their verdicts, states the correction, and says a check of F39/F40 must report "ready" before tests; the Status line counts every round. Contract v1.4.
