# Review CORE-007 contract, round 5 (narrow re-check of r4 F39–F40) · head 869d7db (contract v1.4) · reviewer: pre-review (Claude subagent `fresh-eyes-reviewer`, fresh context, not the r1–r4 reviewer)

Recorded by the implementer from the subagent's final report, unchanged in substance (tables condensed).

Scope: F39, F40 and anything the v1.4 edit contradicts. Commit 869d7db changes contract lines 3, 4, 59, 61, 182, adds map rows 169–170 and `docs/reviews/CORE-007-contract-r4.md` (+7/−5).

## Verdicts
| ID | Verdict | Evidence |
|----|---------|----------|
| F39 | closed | `SizedLots.__post_init__` checks every non-None Decimal field is finite (BacktestError raised while the sizer builds it, passed on per line 32), so a NaN lots in `run` is BacktestError before `check_volume`; in `simulate_trade` line 61 checks lots before any fill. Line 61 now names every Decimal parameter of `run`/`simulate_trade`; CostModel and H001Params finiteness is enforced by their own modules (`costs/model.py:84-85, 142-145`, `charges.py:106-109`; CORE-006 v1.1 ranges). One exception type per path. |
| F40 | closed | Line 182 cites r3 and r4, both exist; quotes r3's "Ready for test authoring: no" exactly; summarises r4 correctly; claims no check that has not happened; the status line counts r1: 15, r2: 19, r3: 6, r4: 2, each matching that file's "Findings open". |

## Contradictions introduced by the edit
None: the SizedLots rule vs the D1 adapter vs `risk/sizing.py` (every SizeDecision has finite fields, so the adapter never breaks the rule); the domain line vs AC-03 (one outcome per case); the DoR line vs the review files; lines 32 and 92 and map rows 169–170.

Non-blocking notes: N1 the DoR gloss of r3 is stricter than r3 but claims no state; N2 `core.Bar` prices are not named in the scope sentence but `core.Bar` rejects non-finite values itself; N3 the costs/strategy errors named in the scope sentence are reachable only by mutating frozen objects, not a CORE-007 input.

AC-03 PASS at contract level; other ACs not re-reviewed (excluded).

Checked, nothing found: `git show 869d7db`; the full v1.4 contract; sizing/policy helpers; costs model and charges; `core.Bar` finiteness; CORE-006 v1.1 ranges; r1–r4 verdicts and counts; red flags: one prose group, nothing from 869d7db.

Not checked: the rest of the contract (excluded); pytest (docs only); CORE-006 implementation (absent); uncommitted CORE-006 files (excluded).

Findings open: 0. The `run` part of AC-02 waits for the CORE-006 implementation, an ordering dependency the contract states.

Ready for test authoring: yes
