# Review CORE-007 round 2 · head c203051 · reviewer fresh-eyes-reviewer subagent (fresh context), re-check of r1 F1-F4

**Scope.** This round re-checks r1's F1–F4 against the fix diff `git diff 2dd4f1c..c203051`, contract v1.5. It also covers anything those fix commits break or introduce. The diff touches five files:
- `src/sochron/backtest/engine.py`
- `src/sochron/backtest/trade.py`
- `tests/unit/backtest/test_backtest_unit.py`
- `docs/evidence/CORE-007.md`
- `docs/handoff/CORE-007.md`

All five are on the contract's allowed list. `pyproject.toml` and `uv.lock` are unchanged.

**Run conditions.** Everything was run in this context on 2026-10-24 (+07), Windows 11, Git Bash, `uv run --offline` with PYTHONDONTWRITEBYTECODE=1 and `-p no:cacheprovider`. The working tree was clean before and after.

**Scratch files.** All probes and the scratch copies of src are in `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/c7r2/`. That covers `h.py`, `probe_f1.py`, `probe_f2.py`, `probe_f2_run.py`, `probe_ctx.py` and `compare.py`. `pre/src` is the code at 2dd4f1c and `mut/src` is the F3 mutant.

**Label.** The caller applies the label. The contract's D7 records the role swap (a fresh Claude context as reviewer). This round is a subagent, not a headless session.

## Status of r1 findings
| r1 ID | Status | Evidence |
|-------|--------|----------|
| F1 | **closed** | **The fix.** `_check_time` (engine.py:41-44) refuses `not RAW_MIN <= time_raw < RAW_MAX_EXCLUSIVE` before `to_utc`. It is used for M15 (:54) and M1 (:61).<br>**Out-of-range values.** I tried time_raw ∈ {0, −1, RAW_MIN−1, RAW_MAX_EXCLUSIVE, 10**30} at m1[0], m1[−1], m15[0] and m15[−1]. All 20 cases gave `BacktestError`. At the last index, values below the previous bar hit the existing order check first, which is also a BacktestError. RAW_MAX_EXCLUSIVE at m1[−1] and m15[−1] gives "time_utc does not match…".<br>**In-range values behave as before.** `_check_time` at RAW_MIN and RAW_MAX_EXCLUSIVE−1 with a matching time_utc raises nothing. `run` on 300 M1 that start exactly at RAW_MIN, and on 300 M1 that end at RAW_MAX_EXCLUSIVE−60, returns a Result. A +3600 mismatch is still a BacktestError.<br>**No other error is converted.** The fix adds no try/except. `to_utc` still runs for in-range values, so any other error passes unchanged. `bar_open` in `_m1_spans` now sees only validated raw times.<br>**Regression test.** It fails on the pre-fix copy with `RawTimeOutOfRange` and passes at HEAD. |
| F2 | **closed** (one sibling path outside the fill code → F5) | **The fix.** `too_large` and the `simulate` wrapper (trade.py:105-115). Wrappers in `_stopped` (engine.py:166-171), `_enter` (:198-201) and `_close` (:215-219).<br>**simulate_trade.** `stop_distance` 1E+1000000 → BacktestError on both sides; 1E+999990 → Trade (control). These also give BacktestError on both sides: M1 prices with 29 digits at E+999999, an exit open of 9E+999999, an M1 spread of 10**1000002.<br>**run, starting equity.** 9.999…E+999999 with 29 digits and 1E+1000000 both give BacktestError. The traceback cause is in `_close`. 9.999…E+999999 with 28 digits gives 12 trades, no error.<br>**run, each wrapper reached.** `_enter`: entry M1 open with 29 digits, cause in `stop_price`. `_stopped`: a short is held and the next M1 has a 29-digit high, cause in `stop_fill`. Long control: the long scan has no arithmetic, so 12 trades, unchanged.<br>**Must pass unchanged, and does.**<br>• A sizer raising `decimal.Overflow` itself → `decimal.Overflow`, unchanged.<br>• A sizer overflowing in its own context → `decimal.Overflow`, unchanged.<br>• A sizer raising `RuntimeError` → unchanged.<br>• `risk_money` 1E+2000000 → `costs.BadR`, unchanged.<br>• `issubclass(OverflowError, decimal.Overflow)` is False, so datetime OverflowErrors are not caught.<br>**Contract consistency.** A finite value too large for the arithmetic is "a value of the right type outside the domain" → BacktestError. One conversion to note: a sizer `risk_money` of 1E-1000000 makes `costs.r_multiple` raise `decimal.Overflow`, which now arrives as BacktestError. `decimal.Overflow` is not a `CostsError` (costs/errors.py: every domain error derives from CostsError), so "costs errors pass unwrapped" still holds.<br>**Caller context.** It stays identical after every overflow path (prec 5, ROUND_DOWN, Emax 99, Inexact trapped).<br>**Regression tests.** They fail 3/3 on the pre-fix copy with `decimal.Overflow`. |
| F3 | **closed** | **Mutant result.** The mutant `range(self.first[t], self.end[t] - 1)` sits in `mut/src`, with a scratch `pytest.ini` (`[pytest]`, `pythonpath = src`). A canary test confirms the scratch engine.py is the one imported. The full suite on the mutant gives **1 failed, 3210 passed**. The one failure is `test_a_stop_in_the_last_minute_of_a_bar_closes_in_that_bar`: `frozenset({'unexpected_gap'}) == frozenset()` fails. The real code gives 3211 passed, and the pre-fix code passes the test too (the code was already right).<br>**Fixture checked by hand.**<br>• Flat bars: TR = H−L = 1.00 (\|H−prevC\| = \|L−prevC\| = 0.50), so ATR = 1.00.<br>• Bar D: H 2003.20, L 1999.50, so TR 3.70 and Wilder (9×1.00+3.70)/10 = 1.27. With k 3.0, stop_distance = 3.810 ✓.<br>• Stop = 2003.00 + 200×0.001 − 3.810 = 1999.390 ✓.<br>• Minutes 0–13 have low 2002.50, above the stop. Minute 14 opens at 2003.00 (no gap) with low 1999.00 → touch, exit at the stop ✓.<br>• D+2 opens at 1999.20: a gap only the mutant reaches.<br>• Bar count: 92 bars from Sun 22:00 to Mon 21:00, then 63 from Mon 22:00 to Tue 13:45, so D = 155 and 158 bars ✓.<br>• The fill is at 14:00 UTC = 10:00 New York (EDT since 2026-03-08).<br>• After the stop, the real code decides flat at D+1: close 2002.00 is below HH_48 2003.20 and above LL_48, so no signal and exactly one trade. The mutant holds at D+1 (close above LL_24 1999.50, no short signal).<br>**No hidden reliance.** Every assumption the fixture needs is asserted: the sizer call (10000, 3.810), 158 bars, bar 156 at 14:00, no aggregate flags. A change in strategy or aggregate would fail loudly rather than let the mutant pass. |
| F4 | **closed** | **Evidence wording.** The AC-05 row and the deliverables line now say one random dataset in 9 configurations (3 variants × 3 side sets), with no price gaps or missing minutes. That matches `_m1`: consecutive minutes (:31), open = previous close (:33/:38), and spread None with probability 0.002 (the "missing spreads" claim holds).<br>**Test comment.** It says the same.<br>**Old wording gone.** `git grep` finds no "9 ชุด" or "gaps from the random walk" (exit 1).<br>**AC-07 row.** "3211 passed at 32984af" is accurate: `32984af..c203051` changes only docs and one test comment, and I measured 3211 at c203051.<br>**Fix rows.** The evidence rows for the fixes (3207 / 3210 / 3211, regressions failing before) match my pre-fix run: 4 failed (F1 ×1, F2 ×3), 112 passed. |

## New findings
| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F5 | Low | confirmed | src/sochron/backtest/engine.py:136 (`rows = indicators(m15, params)`); same kind of call at :176 (`decide(...)`) | **Reproduction** (`probe_f2_run.py`, `compare.py`): `run` on 20,000 random M1. Give M15 bars 0–39 high = 9E+999999 → `decimal.Overflow`, traceback `run → indicators`. Give M15 bars 0–199 spread = 10**1000000 → `decimal.Overflow` in `indicators`. The same result at 2dd4f1c, so this is pre-existing and not introduced by the fix commits.<br>**Why it reaches `run`.** `core.Bar` accepts these values. The backtest checks no magnitude and does not compare M15 OHLC or spread against M1 (v1.5 open question 2).<br>**Contract basis** (the same as r1 F2). "Inputs / outputs / errors" names TypeError, BacktestError, costs errors and sizer exceptions. Strategy errors pass only for H001Params fields (the r4 F39 scope line). `decimal.Overflow` is none of these, and is not even a `StrategyError`.<br>**What the fix commits claim.** The handoff F2 row names exactly the four wrapped places, so this path is not overclaimed. | M15 values within about one order of magnitude of Emax 999999, enough for the TR sum (indicators.py:127/:130) or the spread median (:142) to pass 9.99E+999999 | **Effect:** as r1 F2: a caller catching `ValueError`/`BacktestError` misses it.<br>**Scope:** no wrong number is produced. It is unreachable on real XAU/USD data and in R1, where M15 comes from `aggregate` over checked M1 at prices near 4,000. | Wrap `indicators(...)` (:136) and `decide(...)` (:176) in run with `except Overflow as error: raise too_large(error) from error`. `decide` does the same kind of arithmetic (`k × atr` at h001.py:118, `3 × spread median` at :75); that path was not probed. Alternatives: write into the contract that strategy's arithmetic exceptions pass unwrapped, with a CORE-006 follow-up so strategy raises `StrategyError`. Or accept it as is (Low). | Unit test: `run` with M15 bars 0..39 high 9E+999999 → `BacktestError` (or the contract line) |

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | **Tests:** locked tests unchanged since e74e298 (`git diff --quiet` exit 0), and they pass in the 3211 run at c203051.<br>**Numbers unchanged:** the fix diff changes only exception paths. `compare.py` gives the same SHA256 digest at HEAD and at 2dd4f1c (`9eb11bec…`). It covers 54 runs: 3 datasets with 1% missing spreads and 5% flags, × 3 variants × 3 side sets × the model and its 2× stress. That is 36 trades and 3,132 skips. It also covers 1,200 `simulate_trade` calls on both sides, with and without `exit_index`, 30% of everything under a hostile caller context. |
| AC-02 | PASS | As AC-01. The new F3 test adds a run scenario: stop in the last M1 of bar t, `data_flags` without the next bar's flag. |
| AC-03 | PASS | Locked AC-03 tests pass. F1 and F2 error types now match the contract (probes above). F5 is about magnitude, which is not one of the input checks AC-03 lists. |
| AC-04 | PASS | Locked AC-04 tests pass. The nights code is untouched by the fix diff. |
| AC-05 | PASS | Locked AC-05 tests and the 9 random-data unit cases pass. Digest equal to pre-fix. |
| AC-06 | PASS | `uv run --offline pytest tests/architecture -q -p no:cacheprovider` → 17 passed. The new names are `decimal.Overflow` and `timebase.RAW_MIN`/`RAW_MAX_EXCLUSIVE`, all from allowed modules. |
| AC-07 | PASS locally · CI UNKNOWN | `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` → 3211 passed, 0 skipped, 25.26 s at c203051. There is no PR or CI run yet. |
| Speed row | PASS (not re-measured) | The 500,000-M1 measurement from r1 / the evidence stands: about 3.5 s. The fix adds only try blocks, which cost nothing in CPython 3.12 when nothing is raised. The 100,000-M1 unit test (< 30 s) passes in the suite. |

## Checked, nothing found (and how)
- **Scope:** per-commit `git show --stat`. e2d5142, ffcf289 and 32984af touch src/backtest plus the unit test. 0b30638 and c203051 touch docs plus one test comment. All are allowed files. No dependency or lockfile change.
- **Locked tests:** `git diff --quiet e74e298 HEAD -- tests/acceptance tests/golden tests/architecture` → exit 0.
- **Red flags:** `bash scripts/controls/red-flags.sh origin/main` → pattern groups with hits: 0. Control files touched: the three locked test files from e74e298, unchanged in this round.
- **Commit format:** the "F<n>: …" subjects carry `Refs: CORE-007`. That matches earlier fix commits on main (9338b46 … b7256cd).
- **Error messages:** `too_large` never echoes the value, only the exception type name, so a huge value cannot inflate the message. This follows the rule in costs. `_check_time`'s message does not echo `time_raw` either; 10**30 was fine.
- **Normal flow:** the wrappers in `_stopped`, `_enter` and `_close` leave normal flow alone. The digest is equal, and the 3211 run is green.
- **Exceptions inside `localcontext(CONTEXT)`:** they restore the caller's context (`probe_ctx.py`: unchanged, and `getcontext()` is still the caller's object).
- **`simulate`'s wrapper also covers `count_nights`:** datetime and zone errors are built-in exceptions, not `decimal.Overflow`, so they are not converted.
- **F1 and `simulate_trade`:** it never converts `time_raw`, and `count_nights` uses `time_utc`. The contract's time_utc check applies to `run` only, so nothing is missing there.
- **Lots:** they are bounded by `check_volume` (volume_max 200). At volume_max, `simulate_trade` returns a Trade on both sides, with no overflow path. `actual_risk` 1E+999999 is never used in arithmetic, so it returns a Trade.

## Not checked (and why)
- **CI and the PR run:** no push or PR yet; those are owner and implementer steps.
- **`decide`'s own overflow path** (`3 × spread median` with M15 spreads ≈ 4×10**999999): the probe needs million-digit ints on every M15 bar. It did not finish within 600 s (`timeout` exit 124, no output). It is listed under F5's fix as the same kind of arithmetic, not as a proven defect.
- **Unpinned paths (probes only, no unit test):** the upper-bound half of F1's check, and the `_enter` and `_stopped` overflow wrappers, are verified by the probes above but not pinned by a unit test. r1's proofs of fix asked only for the time_raw 0 cases, `stop_distance` on both sides, and (implementer's addition) the starting equity. No other mutants were run beyond the F3 one.
- **Custom `Sequence`:** one whose `__getitem__` raises `decimal.Overflow` would be converted inside the wrappers. R1 passes tuples; not probed.
- **Speed:** the 500,000-M1 measurement was not re-run.
- **Platforms:** no Linux, macOS or other Python versions; only this machine.
- **Real data:** forbidden before ENV-1.

## Checks run (command → result → commit → time +07, 2026-10-24)
- `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` → **3211 passed in 25.26s** (0 skipped) → c203051 → 13:12:27–13:12:52
- `timeout -k 10 600 uv run --offline pytest tests/architecture -q -p no:cacheprovider` → 17 passed in 1.00s → c203051 → 13:12:57
- `git diff --quiet e74e298 HEAD -- tests/acceptance tests/golden tests/architecture` → exit 0 → c203051 → 13:12:57
- `bash scripts/controls/red-flags.sh origin/main` → pattern groups with hits: 0 → c203051 → 13:13:00
- **F3 mutant:**
  - Canary → scratch engine imported → 13:14
  - `timeout -k 10 900 uv run --offline pytest -c <scratch>/mut/pytest.ini --rootdir . tests -q -p no:cacheprovider` (from the repo root) → **1 failed, 3210 passed** (the F3 test only) → c203051 + mutant → 13:14:30–13:14:55
- **Pre-fix copy:** `uv run --offline pytest -c <scratch>/pre/pytest.ini --rootdir . tests/unit/backtest tests/acceptance/CORE-007 tests/golden/CORE-007 -q -p no:cacheprovider` → 4 failed (F1 RawTimeOutOfRange ×1, F2 decimal.Overflow ×3), 112 passed → 2dd4f1c src → 13:2x
- **Probes:**
  - `probe_f1.py` → 20/20 out-of-range cases BacktestError; boundaries OK → 13:1x
  - `probe_f2.py` → as in F2 → 13:1x
  - `probe_f2_run.py` → as in F2 and F5 → 13:2x
  - `probe_ctx.py` → caller context unchanged → 13:3x
- `compare.py` under HEAD src and the pre-fix src → identical digest, F5 reproduced on both → 13:2x
- Decide-path probe → BLOCKED by its own 600 s timeout (exit 124), see Not checked → 13:2x–13:3x
- `git status --short` → clean → c203051 → 13:33:16

Ready for PR: yes (all r1 IDs closed; F5 is Low, pre-existing, and produces no wrong number on valid input)

Findings open: 1
