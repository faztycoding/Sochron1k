# Review CORE-007 tests round 2 · head 7b70336 + tests r1 + r2 applied · reviewer fresh-eyes-reviewer subagent (fresh context), re-check of tests-r1 F1-F7 and contract v1.5 items 4-6

**Label:** pre-review (Claude subagent).

**Base:** origin/main 6fbed53. Its tree is the same as b7256cd^{tree} (1d7b7827…), and b7256cd is the merge base.

**Head:** 7b70336 (contract v1.5), with both D-006 test patches applied and uncommitted:
- `docs/proposals/CORE-007-tests.patch`
- `docs/proposals/CORE-007-tests-r2.patch` (SHA256 c71fd501…)

**What I read:**
- The contract (`docs/contracts/CORE-007-backtest.md` v1.5).
- `docs/reviews/CORE-007-tests-r1.md`.
- The r2 patch.
- The three locked files, read in place.
- The merged interfaces the tests use.

**How I worked:** read-only. Scratch files live only under `<scratch>` = `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/t2`.

I opened the "Round 2" section of `docs/handoff/CORE-007.md` only after my first pass was complete: findings, reference, mutants, recomputation, append check and red run. It changed nothing below. Its numbers agree with mine.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| — | — | — | — | No new finding in round 2 (F8 not raised) | — | — | — | — |

## Re-check of tests-r1 findings

| r1 ID | r1 Sev | Status | Round-2 change | Evidence (my runs) |
|---|---|---|---|---|
| F1 | Medium | **closed** | `test_backtest.py:1186` with `backtest_cases.py:693` ROLLOVER_CASES: (a) Tokyo 06:00 with triple Monday, (b) NY 23:00, (c) Tokyo 06:00 on a Tokyo Wednesday that is a UTC Tuesday (added) | Mutants of my reference: `rollover_hardcoded` (NY 17:00) → 3 failed (a, b, c). `triple_hardcoded` (Wed) → 1 failed (a). `weekday_utc` → 2 failed (a, c). Each mutant fails 0 round-1 tests. Values recomputed independently and equal (below). |
| F2 | Low | **closed** | `test_backtest.py:1243` and `:1266`. `backtest_cases.py:800` R_first_minutes_missing (the review's case). `:812` R_exit_minute_missing (added, exit side). | Entry and exit M1 found by M15 open time → 4 failed. Entry only → 2 failed. Exit only → 2 failed. `equity_from_m15` → 1 failed (R_first_minutes_missing). Round-1 failures: 0 each. Values recomputed and equal. The fixture `_r2_scenario_data` (`:1121`) asserts that the dropped M1 really open their bars and are absent, and that exactly bars (0, 101) / (103,) are "incomplete". |
| F3 | Low | **closed (by contract)** | Contract v1.5 Invariants (line 98) lists bisect, collections, collections.abc, dataclasses, datetime, decimal, enum, functools, itertools, operator, types, typing. | Same 12 names as `_BACKTEST_STDLIB` (`test_imports.py:1833–1836`). The test is unchanged (AST equal). The r1 proof-of-fix option "the contract line exists" is met. My reference uses only listed modules and passes. |
| F4 | Low | **closed** | `test_backtest.py:1233` with `backtest_cases.py:747` FILL_CASES_R2 (a), (b), as in the review | `ambiguous_entry_spread` → 1 failed (a). `ambiguous_none_zero` → 1 failed (a). Extra mutant `stop_check_none_zero` → (b), plus round-1 "short spread None at the M1 of the stop". Values recomputed and equal. |
| F5 | Low | **closed** | `test_backtest.py:1206` with `backtest_cases.py:741` RAW_SHIFT_CASE | `nights_from_raw` → 1 failed. Recomputed: (0, 0), net 7.00, r 0.28. The mutant reading gives (1, 1). Raw anchors are 1773784860 / 1773871140. |
| F6 | Low | **closed** | `test_imports.py:2062` `_inspect_backtest_zoneinfo_source`, tables `:2082` / `:2118`, test `:2137`. Contract v1.5 "เวลา" item. | Scratch tree with my reference plus `from sochron.timebase.convert import ZoneInfo; … tzinfo=ZoneInfo(zone)`: round-1 AC-06 passes (unchanged by design). Round-2 AC-06 fails with exactly `line 201: forbidden ZoneInfo import` and `line 201: forbidden ZoneInfo reference`. |
| F7 | Low | **closed** | (1) `test_backtest.py:1254` with `backtest_cases.py:825` R_exhausted_long_only. (2) `test_backtest.py:1277`: data_flags {1}, a str-subclass flag, a frozenset subclass. | `equity_before_sides` → 1 failed. `flags_elements_unchecked` → 1 failed. `flags_isinstance` (accepts str subclasses) → 1 failed. Round-1 failures: 0. |

## Contract v1.5 items 4–6
- **Item 4 (sides element type → TypeError):** `test_backtest.py:1302`. `sides_elements_unchecked` → 1 failed; my reference passes.
- **Item 5 (Result.trades / Result.skips are tuple):** `:1326`. `result_lists` → 1 failed.
- **Item 6 (M15 time_utc ≠ to_utc(time_raw, rule) → BacktestError):** `:1344`. `m15_utc_unchecked` → 1 failed. The four cases are bar 1 +1 min, the last bar +60, bar 0 −1 and every bar +60. They use AggregatedBar and a duck type; time_raw is unchanged and time_utc stays UTC.

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | UNKNOWN (red as expected) | No implementation. Round 2 adds nothing here; the round-1 tests are unchanged. |
| AC-02 | UNKNOWN (red as expected) | +4 tests. The r1 gaps F2 and F4 are now covered, with mutant evidence. |
| AC-03 | UNKNOWN (red as expected) | +5 tests: F7 (1) and (2), v1.5 items 4–6. |
| AC-04 | UNKNOWN (red as expected) | +4 tests: F1 (3 cases) and F5. |
| AC-05 | UNKNOWN (red as expected) | +3 tests: the round-1 run ↔ simulate_trade mapping on the three round-2 scenarios. |
| AC-06 | UNKNOWN (red as expected) | +1 test (ZoneInfo). F6 closed; F3 closed by the contract. Both AC-06 tests pass their checker self-tests, then fail loudly because `src/sochron/backtest` is missing. |
| AC-07 | not in these files | Whole suite and CI; belongs to the implementer. |

## Over-constraints (judged against contract v1.5)
My contract-only reference (one module, 405 lines, written before I opened the handoff) passes all 103 CORE-007 tests on the first run, with no change. The suspect tests one by one:

- **AC-06 ZoneInfo checker (`test_imports.py:2062–2075`).**
  - It reports four things:
    - a Name `ZoneInfo`;
    - an Attribute `.ZoneInfo`;
    - a str constant exactly `"ZoneInfo"`;
    - an import alias whose last name segment, or whose `as` name, is `ZoneInfo`.
  - My reference carries the word ZoneInfo in its docstring (line 3) and in a comment (line 6), and builds T as `datetime.combine(day, at, tzinfo=to_zone(entry_utc, zone).tzinfo)`. It passes both AC-06 tests, so docstrings, comments and `to_zone(...).tzinfo` are not flagged.
  - The only possible false positive is a string literal that is exactly "ZoneInfo" (e.g. an f-string part). There is no plausible need for one, and the contract bans naming ZoneInfo at all.
  - **Not an over-constraint.**
- **M15 time_utc test (`:1344`).**
  - M1 membership uses time_raw, which is unchanged, so the only reason left to refuse is v1.5 item 6.
  - The bar-0 case requires checking every M15 bar, not only the bars used as next_open_utc. The contract's list of `run` refusals says exactly that.
  - **Faithful.**
- **sides (`:1302`).**
  - `{"long", 1}` → TypeError requires the element type check before the subset check. v1.5 item 4 makes a non-str element TypeError unconditionally.
  - A str subclass → TypeError follows the general "subclass → TypeError" rule.
  - `{"buy", 1}` is left untested (author's open question 3), which avoids an expectation that depends on hash order. That is correct.
- **data_flags subclasses (`:1277`):** covered by the general subclass rule and round-1 convention 3. **Faithful.**
- **F5 (`:1206`):** relies on `simulate_trade` having no rule and no time_utc check. The contract lists neither. **Faithful today.**
- **F2 scenarios:** the contract says "open ของ M1 แรกของแท่ง M15 ถัดไป" and "(time_raw ของ M1 แรก, equity เริ่มต้น)". **Faithful.**

## Independent recomputation
`<scratch>/runner/recompute.py` uses plain Decimal at 28 digits, zoneinfo directly, my own M1 generation, aggregation and fill arithmetic, and the real `sochron.strategy` decide. It imports neither the tests, the golden file, `sochron.costs` nor any backtest. Every value equals the golden.

- **F1 (a):** nights (1, 1). Swap 15.114, total 18.114, net −8.114, r −0.32456. NY 17:00 or Wednesday gives (1, 0).
- **F1 (b):** nights (0, 0). Total 3.00, net 7.00, r 0.28. NY 17:00 gives (1, 0).
- **F1 (c):** nights (1, 1), the same money as (a).
- **F5:** nights (0, 0), net 7.00, r 0.28. Raw read as UTC gives (1, 1). Raw anchors match.
- **F4 (a):** SL checks at 14:00 and 14:01 do not hit. At the exit M1 the ask open is 4005.020 ≥ 4005.00, so: stop, ambiguous, exit 4004.78, exit spread 240. Gross −47.80; costs 2.40 / 0 / 1.00 / 0 / 3.40; net −51.20; r −2.048. With s = 200 or s = 0 the open is not beyond the stop.
- **F4 (b):** ask open 4000.240 ≥ 4000.22, so a gap at the entry M1, exit 4000.00. Net −3.40, r −0.136.
- **F2:**
  - decide: bar 100 enter_long with stop distance 6.300; bar 101 hold; bar 102 exit.
  - Entry at 12:16, 4002.00, s 240; stop_price 3995.940; lowest low before the exit 3998.20.
  - Exit at 12:45, 3998.60, signal.
  - Gross −10.20; costs 0.72 / 0 / 0.30 / 0 / 1.02; net −11.22; r −0.4488.
  - data_flags {incomplete}; incomplete bars [0, 101].
  - Equity (03-09 11:01, 10000) → (03-10 12:45, 9988.78).

## Satisfiability and mutants
- **Runner:** `<scratch>/runner/run_ref.py`. It puts `<repo>/src` first, imports `sochron`, then inserts `<scratch>/ref/sochron` at the front of `sochron.__path__`. It chdirs to `<scratch>/tree`, which holds a copy of `src` plus my reference, so both AC-06 tests scan the scratch source. It prints every sochron module's file.
- **Origins:** only `sochron.backtest` came from `<scratch>/ref`. `sochron`, `core`, `costs` (charges, errors, model), `data`, `data.snapshot` (aggregate, model, validate), `strategy` (h001, indicators, params) and `timebase` (convert, errors, offset, rules, sessions) all came from `<repo>/src`.
- **Result:** **103 passed** (101 acceptance and golden, plus 2 AC-06). Three more runs in separate processes also gave 103 passed each. Under `-I` each process gets a fresh hash seed.

Mutant results: each mutant is one change to my reference, run on the acceptance and golden tests (101 tests) via `<scratch>/runner/drive.py`, one process per mutant. In every run `sochron.backtest` came from the mutant's directory.

| Mutant | r1 ID / item | Round-1 tests failed | Round-2 tests failed |
|---|---|---|---|
| rollover argument ignored (NY 17:00) | F1 | 0 | 3 (nights a, b, c) |
| triple weekday hard-coded (Wed) | F1 | 0 | 1 (a) |
| Mon–Fri and triple from the UTC weekday of T | F1 | 0 | 2 (a, c) |
| nights from time_raw read as UTC | F5 | 0 | 1 |
| entry and exit M1 by M15 open time | F2 | 0 | 4 |
| entry only / exit only by M15 open time | F2 | 0 / 0 | 2 / 2 |
| first equity point at m15[0] | F2 | 0 | 1 |
| ambiguous decision uses the entry spread | F4 | 0 | 1 (a) |
| ambiguous decision reads None as 0 | F4 | 0 | 1 (a) |
| SL check reads None as 0 (extra) | F4 (b) | 1 | 1 (b) |
| equity check before the sides filter | F7 (1) | 0 | 1 |
| data_flags elements unchecked / str subclass accepted | F7 (2) | 0 / 0 | 1 / 1 |
| sides elements unchecked | v1.5 item 4 | 0 | 1 |
| Result containers as lists | v1.5 item 5 | 0 | 1 |
| M15 time_utc unchecked | v1.5 item 6 | 0 | 1 |
| ZoneInfo from `sochron.timebase.convert` | F6 | 0 of 101; round-1 AC-06 passes | round-2 AC-06 fails (line 201, import and reference) |

## Append-only and integrity
- **Hashes and blobs:** SHA256 and `git hash-object` of the three files equal the expected values:
  - test_imports `b5964d1e…` / `6751aadf…`;
  - test_backtest `05c7cd66…` / `b13bbd19…`;
  - backtest_cases `3b790ada…` / `d1895826…`.
- **Patch shape:** `grep '^-'` on the r2 patch shows only the 3 `--- a/` headers. There are 574 added lines (138 / 272 / 164).
- **Round-1 rebuild:** `<scratch>/runner/append_check.py` rebuilds the round-1 files in memory by removing each hunk's added lines, after checking every context and added line against the current file. It reads in place and writes nothing.
  - The rebuilt blobs are `6250f242` / `9ef4a60c` / `9af29004`, exactly the round-1 blobs recorded in tests-r1 and in the handoff.
  - Top-level statements: 75 → 82, 79 → 92 and 38 → 42. The round-1 statements are equal by `ast.dump`, in order. Each docstring only grew at its end.
  - Added top-level names that rebind a round-1 name: none. There is no global, nonlocal, setattr, globals, exec or eval in the added code.
  - No round-1 test iterates over golden names generically, so the four new golden names change no round-1 test.

## Checks run (command → result → commit → time UTC 2026-10-24)
- `sha256sum` and `git hash-object` of the three files and the patch → all equal to the expected values → 7b70336 + r1 + r2 → 05:0x
- `git apply -R --check docs/proposals/CORE-007-tests-r2.patch`, standalone from the repo root → exit 0, no output → 05:0x
- `uv run --offline --no-sync python -I -B <scratch>/runner/append_check.py <repo> <repo>/docs/proposals/CORE-007-tests-r2.patch` → as above → 05:1x
- `timeout -k 10 600 uv run --offline --no-sync python -I -B <scratch>/runner/run_ref.py <repo> <scratch>/ref <scratch>/tree <repo>/tests/acceptance/CORE-007 <repo>/tests/golden/CORE-007 <both AC-06 node ids>` → 103 passed in 1.68 s; repeated ×3 → 103 passed each → 05:0x, 05:13
- `… drive.py` (18 mutants) → table above → 05:0x
- `… run_ref.py <repo> <scratch>/mut/zoneinfo_from_timebase <scratch>/tree_zi --quiet-modules <both AC-06 node ids>` → 1 failed (r2), 1 passed (r1) → 05:0x
- `… recompute.py <repo>` → every value equal → 05:0x
- `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` → **103 failed, 3093 passed** in 14.13 s → 05:10Z
  - 101 × "AC-0n: sochron.backtest not implemented (No module named 'sochron.backtest')": AC-01 3, AC-02 47, AC-03 24, AC-04 13, AC-05 14.
  - 2 × "AC-06: …\src\sochron\backtest does not exist; implementation missing".
  - 3093 passed is the same count as in r1.
- `bash scripts/controls/red-flags.sh origin/main` → "Pattern groups with hits: 0". The control file touched is tests/architecture/test_imports.py. The two new test files are untracked, so they are listed, not scanned → 05:1x
- Grep with the same patterns over `tests/{acceptance,golden}/CORE-007/*.py` → 0 hits. The three new `except Exception as error:` blocks (`test_backtest.py:1295, 1319, 1368`) record the wrong exception and fail the test, the round-1 pattern → 05:1x
- `node scripts/controls/check-locked-paths.mjs origin/main` → FAIL, as expected: exactly the three patch targets need the owner label → 05:1x
- `git status --porcelain --untracked-files=all` before and after → unchanged (the three paths and the handoff) → 05:13

## Checked, nothing found (and how)
- **Hashes, blobs, reverse apply, append-only, no rebinding:** see "Append-only and integrity".
- **Golden values:** F1 (a), (b), (c), F5, F4 (a), (b) and the F2 scenario recomputed independently, with no difference. R_exit_minute_missing and R_exhausted_long_only were confirmed by my independent reference with the real decide.
- **Satisfiability and over-constraints:** my contract-only reference passed 103/103 on the first run. Each suspect test was judged against v1.5 above.
- **Tests that pass for the wrong reason:**
  - every new test is killed by at least one mutant that kills no round-1 test;
  - the type and value tables run a valid baseline first and record any other exception as a failure;
  - the scenario fixtures assert that the dropped minutes and the incomplete bars are what they claim.
- **Determinism:** 4 reference runs and 18 mutant runs, each in its own process under `-I`. Every test that a mutant does not target passed every time.
- **Nothing broken by round 2:** the red count is 103/3093 with 3093 unchanged since r1, and every failure is for the contract reason.
- **Red flags:** 0 groups in the tracked diff and 0 pattern hits in the untracked test files. No skip or xfail, no type-ignore, no swallowed errors, no secrets.

## Not checked (and why)
- **Platforms and versions:** CI and Linux were not run (read-only review). Only Python 3.12.15 and pytest 9.1.1 were used.
- **Contract v1.5 item 3** (M1 after the close are neither read nor checked): left untested by the contract's own decision ("ไม่มี test ใหม่") and outside this re-check. An implementation that checks the whole range would still pass every test.
- **Dynamic routes to the ZoneInfo class without its name** (e.g. `type(to_zone(…).tzinfo)(zone)`, or `getattr` with a computed string): beyond an AST name check, the same stated limit as FIX-001. The contract's prescribed form gives no reason to use them.
- **The author's open questions 1, 2 and 5** (a binding named ZoneInfo, another zero-offset tzinfo, `at` inside a DST gap): untested by design; I agree none needs a test now.
- **The author's scratch reference and mutants:** not in the repository; I used my own. The handoff's claims agree with my results.
- **The contract's speed row:** belongs to the implementer's unit test and evidence.
- **Cosmetic:** the first lines of the round-1 module docstrings still cite contract v1.4; the appended round-2 paragraphs cite v1.5. Round 2 only appends, so this is left as is.

## Blocks during this session
- **guard-bash block:** it blocked `cd "<repo>" && git apply -R --check docs/proposals/CORE-007-tests-r2.patch` with "Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run each action separately." My mistake: a `cd … &&` prefix. I reran it as the standalone command from the repo root, the form the caller and the block message require (the owner's standing standalone-rerun exception) → exit 0.
- **Heredoc failure (not a hook block):** my first heredoc for the scratch reference failed to parse in bash ("unexpected EOF while looking for matching `''"). I wrote the scratch file again in four smaller heredocs without apostrophes. No repository file was involved.
- **Detector:** no PostToolUse detector report appeared during this session.

## Verdict
All seven tests-r1 findings are closed. Each one has a round-2 test that a plausible wrong implementation fails, and none of those mutants fails any round-1 test. F3 is closed by contract v1.5. Contract v1.5 items 4–6 are tested, and the tests are satisfiable. Round 2 is append-only and changes no round-1 meaning. Every value I recomputed is equal. No test over-constrains a contract-faithful implementation. The red run gives 103 failed, 3093 passed, every failure for the contract reason.

This document is a Claude subagent pre-review. Handoff step 5 asks for a "fresh-session narrow re-check". Whether this pre-review meets that step is for the implementer and the owner to decide (CLAUDE.md).

Ready to commit red: yes
Findings open: 0
