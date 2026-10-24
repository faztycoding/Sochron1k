# Review CORE-006-tests round 1 · base main · head 812207c (40b6e9b at the end, CORE-007 docs only) + applied D-006 patch (uncommitted) · reviewer Claude Code (fresh session 81ba605a, tests reviewer under the role swap)

Scope: the three locked test files after `docs/proposals/CORE-006-tests.patch` was applied:
`tests/acceptance/CORE-006/test_strategy_h001.py`, `tests/golden/CORE-006/strategy_cases.py` and
`tests/architecture/test_imports.py`. I reviewed them against `docs/contracts/CORE-006-strategy-h001.md` (approved
v1 plus the "v1.1" block at `:53-62`, written after the tests by the owner's delegation), H001 sections 3-4, the
public API of `sochron.core`, `sochron.data.snapshot` and `sochron.timebase`, and `docs/handoff/CORE-006.md`. This is
the owner's role swap (contract Status line; Codex is out of quota until 2026-10-28 19:41). I am not the implementer
and not the test author. No implementation of CORE-006 exists. This file is the only file I wrote in the repository.
Nothing is staged, nothing was pushed, and I read the locked files in place: never copied, never edited. My scratch
files are in `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\81ba605a-b7c4-453a-90f2-73692cd69920\scratchpad\`.
All times are UTC on 2026-10-24 (about 07:51-08:14 Asia/Bangkok).

HEAD moved during this session, from `812207c` to `40b6e9b`, when the owner committed `869d7db` (00:54Z) and
`40b6e9b` (00:58Z). Both are CORE-007 docs only: `docs/contracts/CORE-007-backtest.md` v1.4 and its reviews r4 and
r5. `git diff --quiet 812207c HEAD -- docs/contracts/CORE-006-strategy-h001.md tests src docs/proposals` exits 0,
the base blob of the architecture file is still `1319cce4…`, and the CORE-007 change touches nothing about
`indicators` or `decide` (only CORE-007's own input checks and review history). The findings below hold for both
heads.

Verdict: **Ready to commit red: yes.**
- The hashes and blobs match the handoff, the reverse check passes, and the only locked changes against HEAD are the
  three target files.
- The red run is the expected 142 failed, 2876 passed, and every failure has the contract reason.
- No test contradicts the contract, v1.1 included. My own contract-only reference passes all 142 new tests on the
  first run, with every `sochron` module proven loaded from the right place. All 20 wrong implementations I tried
  are caught.
- 80 golden values checked with an exact-fraction oracle: 0 mismatches.

Four findings stay open: F1 (Medium) and F2-F4 (Low). Each is a missing test, mostly for a v1.1 rule written after
the tests (11 surviving mutants). None needs an existing assertion changed. They can come in a second D-006 patch
(tests r2), best before the implementation starts.

**Detector note (N6).** The post-run locked-path detector fired once, after this session's first command (about
00:51Z, read-only: `git status --short`, `git log`, `git rev-parse`, `git branch`). It listed exactly
`uncommitted M tests/architecture/test_imports.py`, `uncommitted A tests/acceptance/CORE-006/test_strategy_h001.py`
and `uncommitted A tests/golden/CORE-006/strategy_cases.py`. Those are the target files of the applied
`docs/proposals/` patch and nothing else. I then checked all three SHA256 and blob values; every one equals the
handoff (section 1), so I continued as CLAUDE.md allows. It did not fire again.

**Block.** guard-bash blocked one command (00:58Z): `git show HEAD:tests/architecture/test_imports.py | ... uv run
--offline --no-sync python -I -B -c "<docstring prefix check that opened tests/architecture/test_imports.py>"`. The
message was: "Blocked by .claude/hooks/guard-bash.mjs: inline python code references a locked path
(tests/architecture). Use the Read tool to read files; locked paths are owner-only." I stopped that step and did not
retry it in any other form. The docstring evidence below comes from the `git diff HEAD` output I already had. The
scratch scripts that ran before or after this were not blocked: `ast_compare.py`, and `run_ref.py`/`mutants.py`,
which run pytest on the locked files by path. Each takes the locked path as a command-line argument and only reads
it.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `tests/golden/CORE-006/strategy_cases.py:18-23` and `tests/acceptance/CORE-006/test_strategy_h001.py:23-24` (against contract `:54`, v1.1 item 1, and D1 "rounded after each operation") | Every golden EMA is exact: the golden uses f = 9 and s = 39 (alpha 0.2 and 0.05), and my exact-fraction oracle `oracle_fraction.py` prints "EMA exact at 28 digits in every row: True" for S, P and G. No golden row therefore depends on the form of the EMA recurrence or on its rounding steps. Two mutants of my reference pass all 142 new tests: "EMA as e + alpha * (c - e)" and "EMA rounded once per step (alpha exact at precision 90, one rounding to 28 digits)". With the default alphas (2/17, 2/65) these forms do give different values. On the 106 closes of the known-answer series, the v1.1 form `alpha*c + (1-alpha)*e` and `e + alpha*(c - e)` differ in 10 rows of EMA_16, 7 of EMA_64, 5 of EMA_8 and 10 of EMA_32. Once-rounding differs from per-operation rounding in 10 rows of EMA_16. | An implementer writes the common `e + alpha*(c - e)` form, or rounds an EMA step once. | v1.1 item 1, the only rule that fixes the EMA recurrence, is unenforced. Two implementations both pass yet give different `ema_*` and `ts` digits for the same bar. Decisions change only near exact ties, but the contract's stated goal is that two people computing the same bar agree (Goal, `:18`), and AC-02 cites D1-D2. | Add a golden series with the default f = 16 and s = 64. Over about 20-30 bars, pin `ema_f`, `ema_s` and `ts` at 28 digits on rows where the v1.1 form, `e + alpha*(c - e)` and once-rounding all give different digits. Compute the values by hand with exact fractions, rounded half-even after each operation in the v1.1 order: alpha and 1 - alpha once, then multiply, multiply, add. | Both EMA mutants fail. A v1.1-faithful reference still passes. |
| F2 | Low | confirmed | `tests/acceptance/CORE-006/test_strategy_h001.py:31-34` (docstring: "Left untested because the contract does not say") and `:931-933` (for t < 96, "none" or skip with warmup both pass) (against contract `:58`, `:59`, `:61`: v1.1 items 5, 6 and 8) | Three mutants pass all 142 tests: "warm-up without a signal gives skip(warmup)" (v1.1 item 5 requires none); "V-C breakout with ATR 0 gives skip(atr_zero)" (item 6 requires none for V-A and V-C); "no exit before warm" (item 8 requires the exit rules while rows are not warm). No test calls `decide()` flat on a row that is not warm and has no signal while also checking for "none". No flat V-C or V-A row has `ts` None at t; the D4 test at `:716-721` covers only an unknown `ts[t-1]`. Every exit/hold case uses warm rows (T = 200). | v1.1 items 5, 6 or 8 implemented another way. | Item 5: CORE-007's Skip log would get a spurious warmup skip on every warm-up bar. Item 6: reached only with hand-built rows, because a Wilder ATR of 0 needs flat prices. Item 8: on a Demo restart with a short history while a position is open, the variant exit would be suppressed (the SL still protects). | Add cases: flat, warm False, no signal → "none" in A, B and C, and tighten `:932-933` to "none". V-C breakout and breakdown with `ts` None and `atr` 0 → "none"; a V-A row with `ts[t]` None after 0.45 → "none". long and short with warm False and each exit condition → "exit", otherwise "hold". Update the docstring at `:31-34` to name v1.1. | The three mutants fail. |
| F3 | Low | confirmed | `tests/acceptance/CORE-006/test_strategy_h001.py:33` (wrong argument types of `indicators()` and `decide()` left untested) (against contract `:35` and `:60`, v1.1 item 7) | Five mutants pass all 142 tests: unknown position accepted (treated as short); negative t reads rows from the end (`decide(rows, -1, ...)` reads the last row and `rows[-2]`); any object with `.bar`/`.flags`, and a `set` of flags, accepted; duck typing refused (only a class named `AggregatedBar` accepted); a t of the wrong type accepted (`int(t)`). No test passes `indicators()` or `decide()` a wrong-typed or out-of-range argument, and every bar in the file is a real `AggregatedBar`, so the duck typing that v1.1 requires is never exercised. | A caller bug in CORE-007 or the Demo loop (an off-by-one or negative t, a typo in the position). | The call returns a wrong decision silently instead of raising `StrategyError`/`TypeError`. A negative t is a silent look-ahead. An implementation that refuses duck-typed bars would break the caller v1.1 describes, and nothing would show it. | One more test: `decide` with position "Long" or "" → `StrategyError`, None or 1 → `TypeError`; t = -1 and t = len(rows) → `StrategyError`; t True or `Decimal(1)` → `TypeError`; params that are not an `H001Params` → `TypeError`. `indicators` on a test-local frozen object with `.bar` a `core.Bar` and `.flags` a frozenset gives rows equal to those from `AggregatedBar`. `.flags` as a `set`, `.bar` as a `Bar` subclass, or an item without `.bar` → `TypeError`. | The five mutants fail. |
| F4 | Low | confirmed | `tests/architecture/test_imports.py:1520-1529` (`_inspect_strategy_source`) with `:40-41` (every stdlib module except `socket` passes `_allowed_import`) (against AC-06 "ไม่มี I/O, นาฬิกา, สุ่ม, MetaTrader5, network") | I added a probe module `leak.py` to a copy of my reference. It calls `logging.getLogger(...).warning`, `shutil.copyfile`, `os.remove`, `Path(...).unlink()`, `sqlite3.connect`, `smtplib.SMTP`, `ftplib.FTP`, `urllib.request.Request`, `xmlrpc.client.ServerProxy`, `threading.Thread(...).start()`, `asyncio.open_connection` and `exec("import random")`. The strategy architecture test still passes (`leak_out.txt`: 1 passed). The gap is inherited from the shared FIX-001/CORE-001 checker, whose docstring says "not a general proof", so it applies to core, costs, risk and data.snapshot as well. | An implementation that logs, writes files, opens a database or a network connection, or uses threads. | AC-06's "no I/O ... network" is only partly enforced, by an explicit name list. | Owner's choice. (a) For strategy only, accept an explicit stdlib allowlist in `_inspect_strategy_source` and report every other stdlib import. The list would be what `_STRATEGY_ALLOWED` already uses plus a few pure modules: collections, dataclasses, datetime, decimal, types, typing, bisect, math, functools, itertools, operator, enum. (b) Record the limitation as accepted in the contract or the evidence. | (a) The probe fails with one finding per forbidden import, and `_STRATEGY_ALLOWED` and `_LEGITIMATE_SOURCES` still report nothing. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

Status here means: would the locked tests fail if the clause were not implemented? Evidence: the tests that target
the clause, and the mutants of my reference that they kill (section 6).

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | 4 tests. Every H001 section 4 edge is accepted, including s = 3f, M = N, and the all-lower and all-upper sets. One unit beyond is refused with `StrategyError` for every int, for theta (0.01 and 0.0001) and for k (0.1 and 0.0001). Also refused with `StrategyError`: s < 3f, M > N, NaN, sNaN, ±Infinity and bad variants. Wrong types raise `TypeError`: bool, float, int and Decimal swapped, str, None, Fraction and subclasses. `H001_DEFAULTS` has the H001 values with exact types. Killed: isinstance checks, no M <= N, theta/k upper edge exclusive, default k 2.5. |
| AC-02 | PASS (gap F1) | 16 tests: every field of every golden row (S 12, P 14, G 120 bars) in A, B and C; the same results under a hostile caller context (precision 4, ROUND_UP, Inexact/Rounded traps), with the caller's context unchanged; warm at the D2 threshold for each binding term (97, 3s = 192, N + 1 = 193, 3s = 99). Killed: HH/LL include bar t, TR ignores gaps, ATR seed / (n - 1), median of the known spreads, warm ignores N + 1 for V-A. Not killed: both EMA mutants (F1). |
| AC-03 | PASS | 27 tests. The H001 worked example enters long in V-A, V-B and V-C with stop 12.00, and its mirror enters short. 23 threshold and breakout edges. k × ATR rounded to 28 digits half-even, ties going to 2 and to 8, also under a hostile caller context. The constants, `Position`, the `Decision` fields and the version on all six actions. Killed: stop from the previous row's ATR, STRATEGY_VERSION H001-v2, decide in the caller's context, window checked at the open of bar t (24 failures). |
| AC-04 | PASS (gap F2, item 8) | 41 tests: each exit rule of each variant, equality edges, the opposite signal gives exit and never enter_*, the same-side signal gives hold, ts unknown never exits V-A (D4) while the Donchian exits of V-B/V-C still happen, and exits/holds are unaffected by the window and by every invalidation. Killed: opposite signal reverses (13 failures). The clause "an opposite signal is itself an exit" cannot be told apart from the variant exit rule on rows `indicators()` can produce. With N >= M, LL_N <= LL_M, so close < LL_N implies close < LL_M; and a V-A short signal implies TS < 0. The mutant that drops the clause is therefore equivalent there: no change needed, noted for completeness. |
| AC-05 | PASS (gap F2, items 5 and 6) | 51 tests: each reason alone (long and short in each variant), the passing edges (720 = 3 × 240, 721 < 721.5, 723 = 3 × 241, 03:00 and 15:45 New York, t = 192), atr_zero for V-B, up to five reasons in contract order, 28 New York window rows on both 2026 DST changes and the days next to them, D3 windows of 97 and 193 bars at both edges, all nine bar-level defect codes, "incomplete" alone ignored, a missing spread making the median None for exactly the next 96 rows, and the 106-bar known-answer series. Killed: spread filter >=, lookback ignores the variant, lookback excludes bar t, incomplete counts as a defect, unknown ts[t-1] counts as 0, window checked at the open of bar t. |
| AC-06 | PASS (gap F4) | Two acceptance tests: the seeded no-look-ahead property (rows and decisions at t are the same with bars after t absent, present or replaced, for 6 parameter sets, 16 fixed and 6 seeded random cut points, 3 positions and 2 windows; the property is checked to be non-vacuous) and determinism with inputs untouched. One architecture test: it checks its own checker first, then scans `src/sochron/strategy`. Killed: import random. Not killed: the I/O and network probe (F4). |
| AC-07 | UNKNOWN | Not a test-author item. It needs the implementation, the suite and CI. With my reference loaded, the whole suite gives 3017 passed and 1 failed: the strategy scan of the repository's missing `src/sochron/strategy`, failing as designed. |

v1.1 items: 1 → F1. 2 → covered (golden G: `atr` None before t = 9, `ts` None at ATR 0; series S checks TR with gaps).
3 → covered (`test_ac05_spread_unknown_inputs_reach_the_row_spread_and_median`; the "median of the known spreads"
mutant is killed). 4 → enforced upstream, nothing to test in `strategy`. 5 → F2. 6 → the V-B part is covered (`:709-715`); the V-A/V-C part is F2.
7 → F3. 8 → F2. 9 → a note, nothing to test.

## 1. Integrity (commands and results)

| Command | Result | Time |
|---|---|---|
| `sha256sum docs/proposals/CORE-006-tests.patch` and the three files | `f43a98c0…7558`, `982d29d1…b74c`, `c2330fa3…ae39`, `438e2999…04a0`: all equal the handoff and the task | 00:51Z |
| `git hash-object --path=<p> <p>` and `--no-filters` for the three files | `3c766460…95de`, `22a0876c…71aad`, `6d91a1e2…b18d` both ways: equal the handoff | 00:51:57Z |
| `git rev-parse HEAD:tests/architecture/test_imports.py` | `1319cce4f673cd4df1ff73925265788cfbcffca1`: the handoff's base blob | 00:51:57Z |
| `git apply -R --check docs/proposals/CORE-006-tests.patch` (alone) | exit 0, no output | 00:52Z |
| `git status --short --untracked-files=all`; `git diff --stat HEAD` | Only `M tests/architecture/test_imports.py` (161+, 1-), `?? tests/acceptance/CORE-006/test_strategy_h001.py`, `?? tests/golden/CORE-006/strategy_cases.py` and the unlocked `?? docs/handoff/CORE-006.md`. These are the only locked changes against HEAD | 00:52Z |
| `node scripts/controls/check-locked-paths.mjs main` | FAIL (exit 1), as expected: 5 locked paths against main, namely the three CORE-006 files above plus the CORE-005 acceptance and golden files from the stacked base branch (`git diff --stat main...HEAD -- tests/`). The owner's label is needed at PR time | 00:52Z |

## 2. Fidelity: the author's conventions against the contract (handoff "Conventions" 1-10)

I judged each one against the contract, including v1.1. **None contradicts it.** My reference follows v1.1
literally, including the rules the tests leave open, and it passes 142/142.
1. Frozen dataclasses with the contract's field names and order. This is consistent with "(frozen)" and the field
   lists at `:41-50`. `is_dataclass` and `FrozenInstanceError` do pin a dataclass, but that is the project pattern
   (`core.Bar`) and the contract's field lists need `fields()`. Acceptable.
2. The TypeError/StrategyError split (contract `:35`). Non-finite Decimals give StrategyError, and "one unit beyond"
   is 1, 0.01 and 0.1. Consistent.
3. `atr` None before n - 1, `ts` None, and the true range: identical to v1.1 item 2.
4. The 96-bar median: identical to v1.1 item 3.
5. `lookback_flags` without "incomplete", with the window clipped at bar 0 while t < L - 1. Consistent with D3.
   Leaving open whether "incomplete" is listed next to a defect constrains nothing.
6. `warm` uses max(3s, N+1, M+1, 97, n+1) for every variant. This is D2 literally; only D3 excludes N and M for V-A.
7. Decision shape: skip has its reasons and stop None; enter_* has reasons () and stop k × ATR; exit, hold and none
   have reasons () and stop None. Compatible with the contract's types and rules.
8. The caller's context is never used or changed. This is D1 "context of the module".
9. An unknown `ts[t-1]` means V-A has no crossing. This follows D4 and agrees with v1.1 item 6.
10. The window is judged on `next_open_utc` through `timebase.in_entry_window`: the contract's rule.

The docstring at `:31-34` and handoff open questions 1-9 predate v1.1. v1.1 has since answered them; F1-F3 list the
answers that still lack a test.

## 3. Golden correctness

`oracle_fraction.py` imports nothing from the repository and reads no repository file. It rebuilds the three golden
series from the construction rules and computes with exact `Fraction`s, rounding to 28 significant digits
half-even after every operation (D1, with the v1.1 EMA form). It compares **80 values** that I typed from my
reading of the golden file:
- the seeds and Wilder steps of S (ATR 12.4, 11.96, 13.464; TS at t = 9, 10, 11);
- the per-operation ATR of P (1.083…333, 1.076…888 rather than once-rounded …889, and 1.236…814);
- the HH/LL window edges of G (t = 23, 24, 34, 35, 40, 41, 45, 47, 48, 50, 51, 58, 59, 64-67, 75, 81, 91, 96, 99,
  105, 113-115, 118, 119), with bar t never inside its own window;
- the medians (247.5 at 96 up to 260.5 at 119);
- `warm` flipping at 117, and every EMA, ATR and 28-digit TS of t = 112-119, including
  `0.00008506642437267155537470058749`.

Result: **0 mismatches**. In addition:
- My Decimal reference (a second, independent method) matches all 146 rows in all three variants through the locked
  test itself.
- The four warm thresholds of `test_ac02_warm_starts…` recompute to 97, 192, 193 and 99.
- The known-answer comment (`:877-890`) recomputes exactly. ATR[97] = 2.09, HH_48[97] = 4002.50, ATR[102] =
  1.9155841 and stop 3.8311682. TS runs 0.154 (96), 0.343, 0.400, 0.446, 0.477, 0.4951, 0.5041 (102), 0.5056, 0.5013,
  0.4925 (105), so V-A crosses only at t = 102, with margins of 0.0041-0.0056. V-A has no short crossing. V-B
  breaks out at 96 (while not warm) and at 97 only.
- The four non-trivial stop roundings of `test_ac03_stop_distance…` recompute.
- `dst_check.py` (zoneinfo only, not `timebase`): all 32 rows of the New York table and the window constants
  (28 + 4) agree on both the wall time and the inside/outside value, with 0 mismatches. This includes 03-08 06:45Z
  = 01:45 EST and 11-01 07:00Z = 02:00 EST.

## 4. Quality

- **Red for the wrong reason:** none (section 5).
- **Passing for the wrong reason:** none found. Every killed mutant fails in the tests aimed at its clause (examples
  in section 6). The no-look-ahead test ends with `assert {"exit","hold","none"} <= actions and actions &
  {"enter_long","enter_short","skip"}` (`:1010`), so it cannot pass on a series without decisions. `decide(prefix,
  t, …)` on rows cut at t would raise if an implementation read row t + 1.
- **Over-constraints beyond the contract:** none that a contract-faithful implementation trips over. My reference,
  written from the contract before running anything, passed 142/142 on its first run. The conventions in section 2
  are all readings the contract permits. The strictest ones are the frozen-dataclass pin, reasons () on non-skip
  actions, and the caller's flags left unchanged.
- **Nondeterminism:** the seeds are fixed (`Random(20261024)`, `Random(t)` for each tail, `Random(7)`), and the cut
  points are a sorted set of ints. Frozenset comparisons do not depend on order. I ran both AC-06 tests three times,
  each in a new process under `python -I` (so with a random hash seed each time): 2 passed every time.
- **The architecture test fails loudly while `src/sochron/strategy` is missing.** The red run fails at `:1655`
  (`assert directory.is_dir()`, "does not exist; implementation missing") after the checker self-test assert at
  `:1650` has passed. With my reference loaded and cwd at the repository root, the same test fails the same way
  (1 of 3018), and it passes only when the scanned directory exists and is clean.
- **AST comparison with `git show HEAD:tests/architecture/test_imports.py`** (`ast_compare.py`, HEAD read from
  stdin and the working file read in place, 00:58Z):
  - 52 top-level statements after the docstring; 51 are AST-identical. `_allowed_import` gains exactly one
    statement, `if package == 'sochron.strategy' and _within(name, 'sochron.timebase'): return True`, and without
    it is identical to HEAD.
  - 5 statements are appended (`_inspect_strategy_source`, `_inspect_as_strategy`, `_STRATEGY_FORBIDDEN`,
    `_STRATEGY_ALLOWED`, the new test).
  - **All 21 HEAD assert statements are present unchanged in the same functions**, and 4 are added, all in the new
    test.
  - Test functions go from 13 to 14, none removed, and there is no skip, xfail or importorskip.
  - Docstring: `git diff HEAD` shows the last line extended ("…as in costs and risk." + " CORE-006 AC-06 runs the")
    and two lines added. My scripted prefix check of the docstring was blocked (see Block above) and not repeated.
- The new grant cannot leak: the new test checks that core, costs and risk still report `from sochron.timebase
  import to_utc`, and every FIX-001/CORE-001 table (`_forbidden_cases`, `_SCOPED_CASES`, `_LEGITIMATE_SOURCES`,
  `_BINDING_CASES`, `_ORIGINAL_CASES`) runs through the strategy checker.

## 5. Red run

`PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider` (repo root,
00:57:09-00:57:17Z) → exit 1, **142 failed, 2876 passed in 7.34s**, 0 skipped, 0 errors. That is 141 in the CORE-006
acceptance file plus 1 in the architecture file. The 141 acceptance failures are exactly 141 `pytest.fail` messages
"AC-0x: sochron.strategy not implemented (No module named 'sochron.strategy')": AC-01 4, AC-02 16, AC-03 27, AC-04
41, AC-05 51, AC-06 2. The architecture failure is
`test_ac06_strategy_import_boundaries_no_io_clock_random_float_or_forbidden_package` at `:1655` ("…\src\sochron\strategy
does not exist; implementation missing"). The 2876 passes are the existing suite. Log: `red_full.txt`.

## 6. Satisfiability and mutants

**Reference.** `ref/src/sochron/strategy/` (`__init__.py`, `params.py`, `indicators.py`, `h001.py`) is my own code,
written from the contract text only. I have not seen the author's reference. It follows v1.1 in full: the EMA form
of item 1, duck-typed bars, StrategyError for an unknown position or a t out of range, TypeError for wrong argument
types, "none" during warm-up without a signal, "none" for V-A/V-C at ATR 0, and exits while rows are not warm.

**Runner.** `run_ref.py` runs under `uv run --offline --no-sync --project <repo> python -I -B`. It imports `sochron`
from the repository's `src`, puts the scratch package directory first on `sochron.__path__`, runs pytest on the
locked files by path with `-p no:cacheprovider --rootdir=<repo>`, and prints the origin of every `sochron` module
before and after the run. No source file was copied.

| Run | Result |
|---|---|
| New acceptance file plus the strategy architecture test, cwd = reference root (01:01:42Z) | **142 passed in 0.82s**. Origins: the 4 `sochron.strategy*` modules come from the scratch reference, and the 13 others (`sochron`, `core`, `data`, `data.snapshot.*`, `timebase.*`) from the repository's `src`. "module origin problems: none" |
| Whole suite with the reference, cwd = repo root (01:06:23Z) | 3017 passed, 1 failed in 7.30s. The one failure is the strategy scan of the repository's missing directory, failing as designed. Origins: none unexpected |
| Both AC-06 tests ×3 (01:06:4xZ) | 2 passed each time |

**Mutants.** `mutants.py` makes one textual change per copy of the reference; each change must match exactly once.
It runs the same 142 tests through the runner for each (01:10:21-01:10:56Z). Origins were clean in every run.
- Wrong implementations: **20 of 20 caught**.
- v1.1 deviations: 10 of 10 survive (F1-F3).
- The equivalent mutant (AC-04 above) survives.

| Mutant | Result |
|---|---|
| HH/LL include bar t | caught: 9 failed (golden G in each variant, …) |
| median of the known spreads | caught: 1 failed (`test_ac05_spread_unknown_inputs…`) |
| spread filter `>=` | caught: 6 failed |
| opposite signal reverses | caught: 13 failed |
| TR ignores gaps | caught: 8 failed (golden S) |
| lookback ignores the variant | caught: 1 failed |
| decide in the caller's context | caught: 1 failed (hostile stop test) |
| `from random import Random` | caught: 1 failed (architecture) |
| unknown ts[t-1] counts as 0 (D4) | caught: 1 failed |
| ATR seed / (n - 1) | caught: 13 failed |
| D3 lookback excludes bar t | caught: 2 failed |
| warm ignores N + 1 for V-A | caught: 1 failed (`[N+1-193]`) |
| isinstance type checks (bool passes as int) | caught: 1 failed (AC-01 types) |
| no M <= N check | caught: 1 failed |
| upper edge of theta and k exclusive | caught: 2 failed |
| default k 2.5 | caught: 1 failed |
| stop from the previous row's ATR | caught: 5 failed |
| window checked at the open of bar t | caught: 24 failed |
| STRATEGY_VERSION "H001-v2" | caught: 1 failed |
| "incomplete" alone counts as a defect | caught: 2 failed |
| EMA rounded once per step | **survives** (142 passed): F1 |
| EMA as e + alpha × (c - e) | **survives**: F1 |
| warm-up without a signal gives skip(warmup) | **survives**: F2 |
| V-C breakout with ATR 0 gives skip(atr_zero) | **survives**: F2 |
| no exit before warm | **survives**: F2 |
| unknown position accepted | **survives**: F3 |
| negative t reads rows from the end | **survives**: F3 |
| any bar-like object and a set of flags accepted | **survives**: F3 |
| duck typing refused (AggregatedBar by name) | **survives**: F3 |
| t of a wrong type accepted | **survives**: F3 |
| opposite-signal exit clause dropped | survives, equivalent on rows `indicators()` can produce (AC-04 note); no change needed |

I/O probe (F4): `leak/` = the reference + `leak.py`; the strategy architecture test → 1 passed (01:06:08Z).

## 7. Red flags

`bash scripts/controls/red-flags.sh origin/main` (01:07:05Z) → exit 0, **1 pattern group with hits: "Lint
disabled"**. All 6 hits are the word "noqa" in the prose of CORE-005 docs: `docs/evidence/CORE-005.md` ×1,
`docs/handoff/CORE-005.md` ×2 and three CORE-005 review files. None is in code. The other groups were not printed,
which means no hits:
- skipped or focused tests
- type checks disabled
- placeholder or mock in production code
- swallowed errors
- possible secrets
- secret-like values
- destructive or bypass commands
- client-exposed variables with secret-like names
- the order or account mutation surface

"Deleted or renamed test files": none. "Control files touched": `.gitignore`, the CORE-005 acceptance and golden
files, and `tests/architecture/test_imports.py`.

The script does not scan untracked files. It lists `docs/handoff/CORE-006.md` and the two new test files under
"Untracked files (not scanned)". I applied its regexes to those two test files with the Grep tool:
- skip/only/xfail/importorskip, type and lint disables, swallowed errors, bypass commands, order/account names and
  secret names: 0 hits;
- TODO/FIXME/HACK/XXX/placeholder/dummy/fake/mock/stub, case-insensitive: 0 hits;
- non-ASCII or CR in the three files: 0.

The added architecture lines contain `MT5_LOGIN` (`:1577`), but only as an environment variable name inside a
synthetic forbidden source (`os.environ["MT5_LOGIN"]`). There is no value, so it is not a secret.

## Checked, nothing found (and how)

- **Integrity.** Hashes, blobs, the base blob, the reverse check, and that only the three target files are locked
  changes against HEAD (section 1).
- **No contradiction.** No test contradicts the contract or v1.1: the v1.1-faithful reference passes 142/142, and
  each convention was judged in section 2.
- **Golden values.** 80 sampled values, the four warm thresholds, the known-answer path, the stop roundings and the
  DST table were recomputed independently (section 3).
- **Correctness of the tests.** Every killed mutant fails for the clause it targets. The known-answer flag cases
  at t - L + 1, t - L and t itself match D3 (L = 97: bar 1 is inside for t = 97, bar 0 is outside). The default
  `_row` meets no entry rule under the defaults, and the quiet exit and hold expectations hold for it (V-B long:
  4000 > LL_M 3990, so hold).
- **Robustness.** The tests do not depend on the hash seed or the order of sets. The golden file is not collected
  as a test module: 3018 = 2876 + 142.
- **Encoding.** The new files are ASCII with LF only.
- **Ignored files.** `tests/acceptance/CORE-006/__pycache__` was written at 00:50:56Z, 11 s after the apply
  (00:50:45Z) and before this session's first command, and `.pytest_cache` dates from 2026-10-21. Both are
  git-ignored. My runs used `-B`/`PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.
- **Repository unchanged.** `git status` was unchanged by my runs (01:09Z), and the three SHA256 were unchanged after
  the satisfiability run.

## Not checked (and why)

- **Linux CI.** The tests have not run on the CI runner; only Windows runs here. Nothing platform-specific was seen:
  zoneinfo uses the tzdata pin, and `random.Random` with an int seed behaves the same on every platform.
- **Changes in CORE-005.** CORE-005 is not merged. If `Bar`, `AggregatedBar` or the defect codes change before its
  merge, merge them and re-run these tests (contract Status line).
- **Every golden row by hand.** I hand-checked 80 sampled values with exact fractions; the other rows were checked
  only through my Decimal reference, which is a second method but not a hand calculation.
- **Flag strings that are not validation defect codes.** The contract is silent, so there is nothing to hold the
  tests to.
- **Speed on about 170,000 M15 bars.** The contract gives this to a unit test. My naive reference ran the 142 tests
  in 0.8 s.
- **The test author's scratch oracle, reference and mutants.** I did not read them, by design.
- **The docstring prefix check of the architecture file.** It was blocked (see Block). The `git diff HEAD` output is
  the evidence used instead.

Ready to commit red: yes

Findings open: 4
