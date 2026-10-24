# CORE-005 test-author handoff (acceptance, golden and architecture tests, red)

Date: 2026-10-23, 08:1x–08:4x UTC (15:1x–15:4x Asia/Bangkok); times in tables are UTC.
Role: Claude Code (fresh session) in the Codex test-author role, under the owner's role swap
(contract Status line and D4, 2026-10-23 15:0x; Codex out of quota until 2026-10-28 19:41). Not the
implementer and not the reviewer of CORE-005.
Contract: `docs/contracts/CORE-005-data-bars.md` v1, Tier Standard, approved by the owner 2026-10-23 15:0x
(D1 spread of the last M1, D2 closure calendar [A], D3 `max_gap_minutes` = 5 [A], D4 role swap).
Inputs read: AGENTS.md, CLAUDE.md, the contract, `docs/architecture.md` sections 7–9, H001 sections 2–3,
`docs/evidence/SPIKE-001.md`, `.agents/skills/write-acceptance-tests/SKILL.md` (as a plain procedure),
HANDBOOK-CORE sections 4, 11 and 15, the public API of `src/sochron/timebase` (`__init__.py`, `convert.py`,
`rules.py`, `sessions.py`, `errors.py`), the locked tests of CORE-001/002/003 and `tests/architecture/test_imports.py`
for style, `scripts/controls/red-flags.sh` (patterns only) and `docs/handoff/FIX-001.md` (patch procedure only).
`src/sochron/core/__init__.py` is the empty CORE-001 docstring module; no `src/sochron/data` exists. No
implementation of CORE-005 was read, because none exists.
Worktree: `C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k-wt-core005`, branch `feat/CORE-005-data-bars`,
HEAD `764cfe4b0fb7e20cf82bd5d0254330bf70929b95` (origin/main `6bd9ef8` plus the approved contracts). The main
checkout was not touched.

Deliverables of this run. Nothing was applied, staged, committed or pushed:
- `docs/proposals/CORE-005-tests.patch` (ignored by `.gitignore:10`; the D-006 patch)
- this file (untracked; the implementer commits it)

## The patch

| Item | Value |
|---|---|
| Patch | `docs/proposals/CORE-005-tests.patch` (1133 lines, 62400 bytes, 0 CR, LF only) |
| Patch SHA256 | `42326ce3e842cc15a24177413de5007c908cbb65221726f0b9ba98ebef0e014e` |
| Built with | three `diff -u` runs from the repo root at 08:35:33Z, concatenated: `--label /dev/null --label b/tests/acceptance/CORE-005/test_data_bars.py /dev/null <scratch>`, the same for `b/tests/golden/CORE-005/bars_cases.py`, and `--label a/tests/architecture/test_imports.py --label b/tests/architecture/test_imports.py tests/architecture/test_imports.py <scratch copy>` (each exit 1 = files differ, as expected) |
| Scratch files | under `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k-wt-core005\1ea581f6-7db0-4f8c-adbc-515343c3df46\scratchpad\mirror\tests\...` at their repository paths. The architecture copy began as `git show HEAD:tests/architecture/test_imports.py > <literal scratch path>`; before any edit `git hash-object --path=…` and `--no-filters` both gave `ca7a75af…` (08:30:11Z) |
| Base (required before apply) | `tests/architecture/test_imports.py` blob `ca7a75af7a6db677ed3bd649a5016ba9bc492b37`, SHA256 `0e1d7a218b3d5c2a71f56c68f5b12eb58a02429d9ddd61665eef2ffb58b080d2` (HEAD `764cfe4`; the FIX-001 r3 file). `tests/acceptance/CORE-005/` and `tests/golden/CORE-005/` must not exist |
| `git apply --check docs/proposals/CORE-005-tests.patch` | PASS: exit 0, no output, one standalone command from the repo root, between 08:35:34Z and 08:36:16Z. Never applied to the repository |
| Independent result check | `harness\apply_in_memory.py` applies the patch to HEAD's bytes with strict context matching (08:36:39Z): the three results are byte-identical to the scratch files (`cmp`) and give the SHA256 and blob values below |
| Shape | 2 new files (689 + 262 lines) and 4 hunks in the architecture file: `@@ -7,7 +7,9 @@` (docstring), `@@ -35,6 +37,9 @@` (`_allowed_import`), `@@ -597,6 +602,42 @@` (checker + AC-06 test), `@@ -1238,3 +1279,109 @@` (AC-06 self-tests). Architecture file: 148 lines added, 1 removed (a docstring line that the new sentence extends), 1240 -> 1387 lines; width stays at most 108 (the file's existing maximum), new lines at most 106 |

### Expected values after apply (LF, one trailing newline, no BOM, ASCII)

| File | Lines | Bytes | SHA256 | Git blob (`git hash-object --path=<repo path>`; same with `--no-filters`) |
|---|---|---|---|---|
| `tests/acceptance/CORE-005/test_data_bars.py` (new) | 689 | 33443 | `0ccd3afef0330b7276da1426613b3c5457131f4ea3919816de45b5ef060868df` | `5f8e537394a89739853bf88ca94fb2208f8f8554` |
| `tests/golden/CORE-005/bars_cases.py` (new) | 262 | 17775 | `f44acafed99317a0e117c20b2d12e12c0584d0515d790a01f35dc1dd0586dd59` | `6f46d72c44787fd0ebdd0a7c2a33c0e00cca9f6b` |
| `tests/architecture/test_imports.py` (changed) | 1387 | 65618 | `854815344dcf0450aa7c9feaceb4f19c178009e4661bb4d155853477d627f305` | `c1e8220d68c5b1f67d3c7a5fe7ae6e08a0a40707` |

## Expected red summary against the current code (HEAD `764cfe4`)

Measured on a scratch mirror that places the three files at their repository paths, with pytest run from the
worktree root (`-c pyproject.toml --rootdir .`, so the code under test is the worktree's `src/`):

| Run | Result | Why |
|---|---|---|
| `pytest <mirror>/tests/acceptance/CORE-005 <mirror>/tests/golden/CORE-005 -q -rA` (08:35:10–08:35:11Z) | **45 failed in 0.19s**, 0 passed, 0 errors, 0 collected from the golden directory | Every test calls `_api(...)` first and fails with `AC-0n: sochron.core.Bar not implemented (cannot import name 'Bar' from 'sochron.core')` (`pytest.fail`, `pytrace=False`): AC-01 ×1, AC-02 ×1, AC-03 ×21, AC-04 ×21, AC-05 ×1. `sochron.core` imports (the CORE-001 docstring module) but has no `Bar`; `sochron.data.snapshot` does not exist, which the same helper would report next. No collection error: the test module imports only pytest and stdlib at module level |
| `pytest <mirror>/tests/architecture -q -rA` (08:35:11–08:35:12Z) | **1 failed, 10 passed in 0.37s** | The 8 existing tests pass unchanged. `test_ac06_data_snapshot_checker_reports_forbidden_packages_and_admits_core_timebase_stdlib` and `test_ac06_data_snapshot_checker_keeps_every_fix001_and_core001_rule` are checker self-tests and pass. `test_ac06_core_and_data_snapshot_import_boundaries_no_clock_io_random_or_broker` fails with `AC-06: …\src\sochron\data\snapshot does not exist; implementation missing` (it does not pass silently) |
| `uv run --offline --locked pytest tests -q -p no:cacheprovider` in the repository, unpatched (08:22:04–08:22:08Z) | **789 passed in 3.33s**, 0 skipped; `git status --porcelain --untracked-files=all` empty after the run | Baseline. The patch changes no existing test |

After the apply the whole suite should give **791 passed, 46 failed** (789 + 2 new self-tests pass; 45 acceptance
tests and 1 architecture test fail until the implementation exists). After the implementation: 837 passed, 0 skipped.

Logs: `<scratchpad>\evidence\red-acceptance.log`, `red-architecture.log`, `ast-compare.log`.

## What the tests check, per AC

| AC | Test (file::name) | What it proves | Why it fails now |
|---|---|---|---|
| AC-01 | `test_data_bars.py::test_ac01_bar_exact_types_finiteness_timeframe_set_and_immutability` | `Bar` is a frozen slots dataclass with the ten contract fields in contract order; a valid bar reads back with exact types; `spread=None`, every timeframe of `TIMEFRAMES_MINUTES` with `m1_count` 1 or `timeframe`, `tick_volume=0` and a Decimal exponent form construct; an inconsistent price, a zero or negative price and a negative spread construct (so `validate_m1` can report them); per field, float, bool, str, a str subclass, Decimal-for-int, int-for-Decimal, an int/Decimal/datetime subclass, `date` and `None` raise `TypeError`; a naive datetime raises `TypeError` or `ValueError`; NaN, sNaN and both infinities raise `ValueError`; timeframes 0, 7, 13, 25, -15, 1441 raise `ValueError`; `setattr`, `delattr` and a new attribute raise `FrozenInstanceError`; no `__dict__` | `sochron.core.Bar` missing |
| AC-02 | `::test_ac02_m15_aggregation_matches_the_golden_tables` | 148 synthetic M1 (golden) over 13:00–15:59 UTC on 2026-03-10: the report has exactly the 6 golden defects and day STOP; `aggregate(..., 15, ...)` returns 11 `AggregatedBar` in ascending time with the golden open/high/low/close (Decimal), spread of the last M1 (254, None or -3), tick_volume sum, `m1_count`, `time_raw == bar_open(...)`, `time_utc == to_utc(...)`, `timeframe == 15` and the exact flag set per bar; slot 14:15 is not created; the M15 counts sum to 148; input list untouched (identity, order, every field); the same call repeats identically; a tuple input gives the same result; `AggregatedBar`, `ValidationReport` and `Defect` are frozen | `Bar` missing |
| AC-03 | `::test_ac03_each_defect_code_severity_and_time_with_input_untouched[19 cases]` | one anomaly at a time on a clean 10-bar series: `time_not_increasing`, `duplicate_time`, `not_minute_aligned` (13:05:30), `time_rule_mismatch` (+1 s), `ohlc_inconsistent` ×3 (high<low, open>high, close<low), `non_positive_price` ×2 (low 0, low -0.001), `negative_spread`, `missing_spread`, `unexpected_gap` (6 missing), `empty_weekday` (Wednesday absent between Tuesday and Thursday), two defects on one bar, two bars with one defect each, a single bar, a single bar with a defect, plus two clean controls (clean series; open==high and close==low). Each case fixes the exact multiset of (code, severity, time_raw), the exact day map, `m1_bars == len(input)`, the Defect shape (str code, severity in the three values, int or None time, str detail) and the untouched input, twice | `Bar` missing |
| AC-03 | `::test_ac03_time_rule_mismatch_is_judged_under_the_validating_rule` | bars built with offset 0 and validated under a synthetic `TimeRule` with `offset_seconds=7200` (via `dataclasses.replace`) give ten `time_rule_mismatch` STOP defects and the UTC day under that rule; the same bars rebuilt under the shifted rule are clean | `Bar` missing |
| AC-03 | `::test_ac03_empty_input_and_wrong_argument_types` | empty input: `defects == ()`, `days` empty, `m1_bars == 0`, `aggregate` returns `()`; `max_gap_minutes` and `timeframe` of bool, float, str, str subclass, Decimal, int subclass or None raise `TypeError`; timeframe 0, 7, 13 raise `ValueError`; a rule, calendar or report of the wrong type raises `TypeError`; a non-Bar element (object, int, dict, a `Bar` subclass instance) raises `TypeError` in both functions | `Bar` missing |
| AC-04 | `::test_ac04_h001_closure_calendar_values_and_the_calendar_argument` | `H001_CLOSURES` is a `ClosureCalendar` with zone `America/New_York`, `daily_break == (time(17,0), time(18,0))`, weekend `((4, time(17,0)), (6, time(18,0)))` (Friday, Sunday per `date.weekday()`), a provenance that mentions "assumed", and is frozen; a calendar with a 16:50 break and one with zone UTC change the verdict of the same bars, so the argument (zone and times) is used | `Bar` missing |
| AC-04 | `::test_ac04_gaps_against_the_new_york_calendar_on_both_dst_changes[19 cases]` | (ก) daily break on Thu 2026-03-05 (EST), Mon 2026-03-09 (first EDT weekday), Thu 2026-10-29 (EDT), Mon 2026-11-02 (first EST weekday): no defect; the old UTC break hours after each change (Mon 2026-03-09 22:04->23:05 UTC; Mon 2026-11-02 20:59->21:55 UTC) are `unexpected_gap`; break plus 5 in-session minutes (16:57->18:03 NY) no defect, plus 6 (->18:04) a defect; (ข) weekends around 2026-03-08 (48 h), around 2026-11-01 (50 h) and an ordinary one (49 h): no defect, no `empty_weekday`; weekend plus 6 in-session minutes: a defect; (ค) 5 missing minutes with `max_gap_minutes` 5: no defect; (ง) 6 missing: `unexpected_gap` WARN at the first bar after; `max_gap_minutes` 2 (2 pass, 3 fail) and 0 (consecutive pass, 1 missing fails); consecutive minutes across UTC midnight: no defect. Day map: WARN on the UTC day of a gap, PASS otherwise | `Bar` missing |
| AC-04 | `::test_ac04_m15_bars_around_closures_and_unexpected_gaps` | aggregation around a daily break and a weekend gives two complete unflagged M15 bars and nothing in between; a (ง) gap flags the slot of the first bar after it with `unexpected_gap` and both partial slots with `incomplete`; a (ค) gap gives `incomplete` only; a break-plus-six gap flags the slot after the break; a single M1 gives one `incomplete` bar; M1 counts always sum to the input | `Bar` missing |
| AC-05 | `::test_ac05_day_status_precedence_empty_weekday_and_utc_day_keys` | Mon–Fri 2026-03-09..13 with Wednesday absent: `{Mon: PASS, Tue: WARN, Wed: UNKNOWN, Thu: STOP (STOP beats WARN), Fri: WARN (two WARNs)}` with the exact defect list; `days` is a read-only `Mapping` (item set and delete raise `TypeError`) and the report is frozen; two STOP codes plus a WARN on one day give STOP; under a synthetic rule two hours ahead of UTC the only key is the UTC date (2026-03-09, not the raw date 2026-03-10); `Severity` and `DayStatus` exist | `Bar` missing |
| AC-06 | `test_imports.py::test_ac06_core_and_data_snapshot_import_boundaries_no_clock_io_random_or_broker` | every `.py` under `src/sochron/core` and `src/sochron/data/snapshot` passes `_inspect_source` (CORE-001 + FIX-001 rules: clock, I/O, randomness, process, console, network, `MetaTrader5`, dynamic import) plus a ban on any `random` import; imports limited to stdlib (except `socket`), `sochron.core`, the package itself and, for snapshot only, `sochron.timebase` | `src/sochron/data/snapshot` does not exist (assert, not a silent pass) |
| AC-06 | `::test_ac06_data_snapshot_checker_reports_forbidden_packages_and_admits_core_timebase_stdlib` | the checker reports `sochron.broker` (3 forms), `sochron.data.acquire` (3 forms, relative included), `sochron.execution`, `sochron.journal`, `sochron.research`, `MetaTrader5` (2 forms), numpy, `sochron.costs`, `random` (2 forms), `time.time()` and `Path.read_bytes()` with the exact finding, and admits core, timebase, own-package and listed stdlib imports; `sochron.core` importing timebase is still reported | passes now (self-test) |
| AC-06 | `::test_ac06_data_snapshot_checker_keeps_every_fix001_and_core001_rule` | the snapshot checker reproduces every expectation of the FIX-001 tables (`_forbidden_cases`, `_SCOPED_CASES`, `_LEGITIMATE_SOURCES`, `_BINDING_CASES`, `_ORIGINAL_CASES`); the one CORE-001 finding that depends on package depth ("relative import escapes its package" for `from ... import outside`) resolves inside the deeper package and must be reported as a forbidden import on the same line | passes now (self-test) |
| AC-07 | not a new test | the whole suite and CI; see the expected summaries above | – |

### Conventions the contract leaves open, decided by these tests

The contract says the error table and the detail live in the tests ("ตามตารางใน tests"). The tests fix the
following; each is stated in the acceptance file docstring and the golden file docstring.

1. **Gap length** = number of missing M1 minutes between consecutive bars, `(t2 - t1) / 60 - 1`. With
   `max_gap_minutes` 5, bars at 13:04 and 13:10 (5 missing) are not a defect; 13:04 and 13:11 (6 missing) are. The
   D3 rationale ("ช่องว่าง 1–5 นาทีอาจเกิดได้จริง") reads naturally as missing minutes; SPIKE-001's bins used
   open-to-open distance, which would shift the boundary by one minute.
2. **Closure minutes are subtracted.** A gap is `unexpected_gap` when its in-session minutes exceed
   `max_gap_minutes`. So the 63–68-minute breaks that SPIKE-001 measured (last bar 16:57 NY, first bar 18:00–18:05
   NY) give 2–7 in-session minutes: 63–66-minute breaks pass, 67-minute and longer breaks are WARN under D3 = 5.
   A break of G minutes, open to open from the 16:57 bar, leaves G − 61 in-session minutes; the locked row
   20:57 → 22:03 UTC (66 minutes) is not a defect. (Corrected in round 2, review tests-r1 F6; round 1 said
   "first bar 18:01–18:05", "3–7", "63–65 pass" and "66 and longer WARN".) The owner may want to know this before R1.
3. **`unexpected_gap.time_raw`** = open time of the first bar after the gap. Hence the M15 slot that holds that bar
   carries the `unexpected_gap` flag (golden 14:30 and 15:00), and the day of resumption gets the WARN.
4. **`empty_weekday.time_raw` = None**, for a Monday–Friday UTC date with no bar strictly inside the span of the
   input. Saturday and Sunday without bars are never reported, and they are not keys of `report.days`, even inside
   the span: the AC-04 weekend rows compare the exact key set, so they already required this in round 1, and round 2
   adds a Friday → Monday row with no weekend bar at all. (Corrected in round 2, review tests-r1 F3; contract v1.1
   item 5. Round 1 said here that the tests did not decide it.)
5. **Equal time -> `duplicate_time` only; a smaller time -> `time_not_increasing`** (one defect per anomaly; a
   duplicate is reported once, at that time).
6. **One defect per (bar, code)**; the multiset is compared exactly, so a second identical defect fails.
7. **`ClosureCalendar.weekend` weekdays** follow `datetime.date.weekday()`: Friday 4, Sunday 6. `zone` is the
   IANA string. `provenance` has no fixed type; `"assumed" in str(provenance).lower()` is all that is asserted.
8. **Type errors**: wrong type (float, bool, str, subclass, None) -> `TypeError` in `Bar` and in both functions,
   including a `Bar` subclass instance in the input; non-finite Decimal and a timeframe outside
   `TIMEFRAMES_MINUTES` -> `ValueError` (a `timebase.BadTimeframe` satisfies it). A naive `time_utc` may raise
   either.
9. **`incomplete`** is asserted only with `H001_CLOSURES`, whose boundaries fall on M15 boundaries in UTC, so a
   produced bar is incomplete exactly when it has fewer than 15 M1. No test has an M1 inside a closure.
10. **AC-06**: the checker for `sochron.data.snapshot` is `_inspect_source` plus a ban on `import random` and
    `from random import …` (the costs/risk pattern); the same checker also runs over `sochron.core`, which may still
    import nothing from `sochron` (timebase included). Float names and literals are not banned (not in AC-06).

### Questions the contract does not answer (owner or reviewer)

1. Should `Bar` also validate ranges at construction (`tick_volume >= 0`, `1 <= m1_count <= timeframe`,
   `time_raw` inside `timebase.RAW_MIN..RAW_MAX_EXCLUSIVE`)? The contract says types and finiteness only, so the
   tests do not ask for it.
2. Is an aware non-UTC `time_utc` (same instant, zone Asia/Bangkok) accepted, rejected, or a `time_rule_mismatch`?
   Not tested.
3. Should `validate_m1` reject `max_gap_minutes < 0` (`ValueError`)? Not tested.
4. Should `aggregate` refuse unsorted input or input with duplicates, or rely on the report? Not tested; every
   aggregate input in the tests is strictly increasing.
5. Does a Saturday or Sunday inside the span appear in `report.days` (as PASS), or only days with bars and empty
   weekdays? Answered by the owner in contract v1.1 item 5: it is not a key. (Corrected in round 2, review tests-r1
   F3: round 1 said "not asserted either way", but the AC-04 weekend rows already asserted it.)
6. The UNKNOWN > WARN step of the precedence cannot be exercised with the minimum codes: the only UNKNOWN code is
   for a day without bars, which carries no WARN. Tested: STOP > WARN, WARN only, UNKNOWN only, PASS.
7. Conventions 1–3 above change the WARN rate on real data (see convention 2). Confirm or amend before R1.
8. Should snapshot also be banned from `float` (names and literals) as costs and risk are? The invariant says no
   float in prices; AC-06 does not list it.

## AST comparison of the architecture file (`harness\ast_compare.py`, 08:35:12Z)

- **Asserts.** All **14 of 14** asserts of HEAD are present with an identical `ast.dump` in the same function (3 in
  each AC-07 test, 1 in each of the 5 FIX-001 tests). The amended file has 19 asserts: the 5 added are in the three
  new AC-06 tests (2 in the directory test, 1 and 1 in the self-tests, plus the new per-package assert pair).
- **Functions and classes.** 18 of 19 top-level definitions are AST-identical. The one change is `_allowed_import`,
  which gains two lines: `if package == "sochron.data.snapshot" and _within(name, "sochron.timebase"): return True`,
  placed after the risk->costs branch. For every existing package key it returns what it returned before.
  New: `_inspect_data_snapshot_source`, `test_ac06_core_and_data_snapshot_import_boundaries_no_clock_io_random_or_broker`,
  `_inspect_as_snapshot`, the two AC-06 self-tests.
- **Module level.** 17 of 18 non-function statements unchanged (imports, `_SIDE_EFFECTS`, `_PURE_CHECKERS`, all
  FIX-001 tables). The 18th is the module docstring, extended by one sentence. `_PURE_CHECKERS` is **not**
  extended: the FIX-001 asserts keep iterating the same four packages; the snapshot checker gets the same tables
  through its own self-test instead, so no existing assert changes meaning.
- **Text.** 1 line removed (the docstring line `FIX-001 is still reported.`, now part of a longer sentence),
  148 added.

## Checks run in this session (2026-10-23 UTC)

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git rev-parse HEAD`; `git status --short`; `git ls-files -s`; `git check-attr -a`; `.gitattributes`; `git check-ignore -v docs/proposals/CORE-005-tests.patch` | PASS: clean, `764cfe4`, architecture blob `ca7a75af…`, `text eol=lf`; `.gitignore:10` ignores the patch path; the handoff path is not ignored | 764cfe4 | 08:1x |
| `uv run --offline --locked python -c …` zoneinfo facts: 2026-03-05 21:59Z = 16:59 EST, 2026-03-09 20:59Z = 16:59 EDT, 2026-11-01 23:00Z = 18:00 EST, 2026-11-02 21:59Z = 16:59 EST, 2026-03-10 13:00Z = 1773147600 | PASS (stdlib fact-check of the hand-written tables) | 764cfe4 | 08:2x |
| `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline --locked pytest tests -q -p no:cacheprovider` (repo, unpatched) | PASS: `789 passed in 3.33s`, 0 skipped; working tree still clean | 764cfe4 | 08:22:04–08:22:08 |
| `harness\gen_m1_rows.py` (prints the 148 M1 rows from the documented formula; expected M15 values derived by hand in the golden file) | 148 rows | – | 08:2x |
| `git show HEAD:tests/architecture/test_imports.py > <literal scratch path>`; `git hash-object --path=…` and `--no-filters`; `sha256sum` | PASS: `ca7a75af…` twice; SHA256 `0e1d7a21…` equals the repo file | 764cfe4 | 08:30:11 |
| architecture mirror, first run | 2 failed, 9 passed: the directory test (expected) and my second self-test, whose reuse of `_ORIGINAL_CASES` expected "relative import escapes its package" for `from ... import outside`; at package depth 3 that import resolves to `sochron.outside` and is reported as a forbidden import. Self-test amended to accept a forbidden-import finding on that line (a harness expectation, not a checker change) | 764cfe4 + scratch | 08:31:45 |
| `pytest -c pyproject.toml --rootdir . <mirror>/tests/architecture -q -rA -p no:cacheprovider` (final file) | Expected: `1 failed, 10 passed in 0.37s`; the failure is `AC-06: …\src\sochron\data\snapshot does not exist; implementation missing` | 764cfe4 + scratch | 08:35:11–08:35:12 |
| `pytest -c pyproject.toml --rootdir . <mirror>/tests/acceptance/CORE-005 <mirror>/tests/golden/CORE-005 -q -rA -p no:cacheprovider` | Expected: `45 failed in 0.19s`; all 45 with `sochron.core.Bar not implemented`; 0 collected from the golden directory | 764cfe4 + scratch | 08:35:10–08:35:11 |
| `harness\name_check.py` (syntax, undefined names, CR, BOM, tabs, trailing whitespace, single final newline, skip/xfail/noqa/type-ignore/TODO markers, width) on the three files | PASS: 689 / 262 / 1387 lines, max width 106 / 100 / 108, no problems | – | 08:32:24 |
| `harness\golden_crosscheck.py` (first/last/max/min/sum per slot and the stated defect and flag rules over the literal M1 rows; not an implementation of snapshot) | PASS: 11 of 11 M15 rows, the 6 defects and all flag sets agree with the hand-computed tables | – | 08:32:24 |
| `harness\ast_compare.py` HEAD vs scratch copy | PASS: 14/14 asserts identical; only `_allowed_import` and the docstring changed; 1 line removed | – | 08:35:12 |
| `diff -u --label … > docs/proposals/CORE-005-tests.patch` (×3, the last two with `>>`) | PASS: each exit 1 (files differ); 1133 lines, 62400 bytes, 0 CR | 764cfe4 | 08:35:33 |
| `git apply --check docs/proposals/CORE-005-tests.patch` (standalone) | PASS: exit 0, no output; not applied | 764cfe4 | 08:35:34–08:36:16 |
| `sha256sum`; `git hash-object --path=…` and `--no-filters`; `wc -l -c` of the patch and the three scratch files | PASS: values in the tables above | 764cfe4 | 08:35:33 |
| `harness\apply_in_memory.py` (first run) | Harness error: `Path.read_text(newline=…)` is 3.13-only; replaced by `read_bytes().decode()`; not a patch result | – | 08:36:16 |
| `harness\apply_in_memory.py` docs/proposals/CORE-005-tests.patch . <scratch out>; `cmp` against the scratch files; `git hash-object` | PASS: SHA256 `0ccd3afe…`, `f44acafe…`, `85481534…`; blobs `5f8e5373…`, `6f46d72c…`, `c1e8220d…`; byte-identical | 764cfe4 | 08:36:39–08:36:40 |
| `git status --porcelain --untracked-files=all`; `git hash-object --path=tests/architecture/test_imports.py tests/architecture/test_imports.py` after everything | PASS: only `?? docs/handoff/CORE-005.md` (this file); the locked file is still `ca7a75af…` | 764cfe4 | 08:4x |

No hook or deny rule blocked anything in this session. One command defined an unused shell variable
(`S="placeholder-not-used"`) by mistake; it was not used in any redirect or path.

## Not verified

- The tests against an implementation: none exists. The golden expectations were derived by hand from the contract
  rules and cross-checked with arithmetic over the literal rows only; the AC-03/04/05 expectations rest on the
  conventions listed above and on the zoneinfo fact-check.
- The post-apply suite summary (791 passed, 46 failed) and `git apply -R --check`: both need the apply, which is the
  implementer's step.
- `bash scripts/controls/red-flags.sh main` and `node scripts/controls/check-locked-paths.mjs main` on the patched
  tree: until the apply there is no tracked change to scan. The test files contain none of the scanned markers
  (`name_check.py`), and the "Placeholder or mock" check skips test paths.
- CI on Linux. The tests use only pytest, stdlib and `zoneinfo` with the project's `tzdata`; the 2026 New York DST
  dates come from `tzdata 2026.5`.

## Instructions for the implementer (Claude, D-006)

1. **Confirm the starting state.** Branch `feat/CORE-005-data-bars`; `git status` clean apart from this file;
   `git hash-object --path=tests/architecture/test_imports.py tests/architecture/test_imports.py` =
   `ca7a75af7a6db677ed3bd649a5016ba9bc492b37`; `sha256sum docs/proposals/CORE-005-tests.patch` =
   `42326ce3e842cc15a24177413de5007c908cbb65221726f0b9ba98ebef0e014e`; `tests/acceptance/CORE-005` and
   `tests/golden/CORE-005` do not exist.
2. **Apply.** Each as one standalone command from the repo root: `git apply --check docs/proposals/CORE-005-tests.patch`,
   then `git apply docs/proposals/CORE-005-tests.patch`. The post-run detector must report exactly the three target
   files (`tests/acceptance/CORE-005/test_data_bars.py`, `tests/golden/CORE-005/bars_cases.py`,
   `tests/architecture/test_imports.py`); any other report means stop and ask (N6).
3. **Verify the hashes** against the "Expected values after apply" table: `sha256sum` of each file and
   `git hash-object --path=<repo path> <repo path>` of each. Stop and ask on any mismatch. Then run
   `git apply -R --check docs/proposals/CORE-005-tests.patch` standalone (expected: exit 0).
4. **Run red.** `uv run --offline pytest tests -q -p no:cacheprovider` -> expect `46 failed, 791 passed`, 0 skipped,
   with every acceptance failure saying `sochron.core.Bar not implemented` and the architecture failure naming the
   missing `src/sochron/data/snapshot`. `uv run --offline pytest tests/architecture -q -p no:cacheprovider` ->
   `1 failed, 10 passed`.
5. **Fresh-session review of the tests** against the contract and `git diff main` (D4: a Claude session that is
   neither this one nor the implementer). Findings go to `docs/reviews/CORE-005-tests-r1.md`; a fix comes as a new
   patch from a fresh test-author session, never as a direct edit.
6. **Commit red** (`test(core-005): add acceptance, golden and architecture tests (red)`, body `Refs: CORE-005`),
   including this handoff. Then implement under the contract; never edit the three locked files to make them pass.
   When the suite is green, `bash scripts/controls/red-flags.sh main`, `node scripts/controls/check-locked-paths.mjs main`
   (expected FAIL until the owner's label), evidence, PROGRESS, push under D-006, PR with the template.

## Please look hard at (fresh-session reviewer)

- **Conventions 1–3** (gap length in missing minutes, closure minutes subtracted, gap time at the first bar after).
  They decide the boundary cases and which M15 slot carries `unexpected_gap`. If the owner prefers open-to-open
  distance, the boundary rows in `_GAP_CASES`, the AC-03 gap case, the golden 13:30 slot comment and the two golden
  gaps need a one-minute shift.
- **Exact multiset of defects** (`_defects` vs `_expected`): an implementation that reports a duplicate twice, or a
  duplicate also as `time_not_increasing`, fails by design (convention 5–6).
- **Day-map exactness**: `dict(report.days) == {...}` in AC-03, AC-04 and AC-05 asserts the key set, so a bar-less
  Saturday or Sunday inside a span must be absent (corrected in round 2, review tests-r1 F3; contract v1.1 item 5).
- **`_check_report`** ties `time_raw is None` to `empty_weekday` and vice versa.
- **The AC-01 wrong-type table** includes `None` for every field except `spread`, and `_Int(1)` for `timeframe`
  (value 1 is a valid timeframe, so only an exact type check can refuse it).
- **AC-06 checker**: the only change to shared code is the `_allowed_import` branch; the random ban is in the new
  function. Check that `_SNAPSHOT_FORBIDDEN_IMPORTS` expectations are exact lists, and that the relative-import
  allowance in the second self-test cannot hide a lost rule (it still requires a `forbidden import` finding on the
  same line).
- **Red-flag and locked-path scans** after the apply.

## Round 2 patch (tests-r1 findings, contract v1.1)

Date: 2026-10-23, 20:06–20:4x UTC (2026-10-24 03:06–03:4x Asia/Bangkok); times below are UTC.
Role: a fresh Claude Code session in the Codex test-author role for round 2, under the owner's role swap (contract
Status line; Codex out of quota until 2026-10-28 19:41). Not the implementer, not the round-1 test author, not a
reviewer of CORE-005. It followed `.agents/skills/write-acceptance-tests/SKILL.md` as a plain procedure.
Inputs read: AGENTS.md, CLAUDE.md, HANDBOOK-CORE sections 4, 11 and 15, the contract v1.1 (the "v1.1" block),
`docs/reviews/CORE-005-tests-r1.md`, the round-1 sections of this handoff, H001 sections 2–3, `docs/evidence/SPIKE-001.md`,
the public API of `src/sochron/timebase`, the three applied round-1 files (read in place), `git diff` of the
architecture file, the line patterns of `scripts/controls/red-flags.sh` and `.claude/hooks/check-locked-after.mjs`
(to describe the detector below). No CORE-005 implementation exists, so none was read.
Base: branch `feat/CORE-005-data-bars`, HEAD `f9504f8beeaf8e5625e7f3d30f4e87c4a57f548c`, round 1 applied and
uncommitted (verified below). Written in the repository: `docs/proposals/CORE-005-tests-r2.patch` (ignored by
`.gitignore:10`), the four corrections marked "Corrected in round 2" above (conventions 2 and 4, question 5, the
day-map line) and this section. Nothing applied, staged, committed or pushed. No locked file was edited or copied
with `cp`.

**Outcome: proposal complete.** Against the current repository the amended tests are red for the right reason
(whole suite 56 failed, 793 passed, 0 skipped). Against a contract-only scratch reference, all 55 acceptance tests
and all 13 architecture tests pass, so the whole suite should give **849 passed** after a correct implementation.

### D-006 artifact

| Item | Value |
|---|---|
| Patch | `docs/proposals/CORE-005-tests-r2.patch`: 506 lines, 28265 bytes, 0 CR, LF only |
| Patch SHA256 | `1567e22a445beff49237c0446b1b14ad303a9076a529d62d4879f04b0748346c` |
| Shape (`git apply --numstat`) | two changed files, none added or deleted: acceptance +211/−12 in 11 hunks, architecture +134/−13 in 3 hunks. The golden file is unchanged and not in the patch |
| Built with | two `diff -u --label a/<path> --label b/<path> <path> <literal scratch copy>` runs from the repo root at 20:35:41Z, the first with `>`, the second with `>>` (each exit 1 = files differ) |
| Base (required before apply) | the applied round-1 files: acceptance blob `5f8e537394a89739853bf88ca94fb2208f8f8554` (SHA256 `0ccd3afe…`), architecture blob `c1e8220d68c5b1f67d3c7a5fe7ae6e08a0a40707` (SHA256 `85481534…`), golden blob `6f46d72c44787fd0ebdd0a7c2a33c0e00cca9f6b` (SHA256 `f44acafe…`) |
| Scratch copies | `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\1fd58dca-2b7e-48f7-aed4-6b27414e80f3\scratchpad\mirror\tests\...` at their repository paths. Architecture: `git show HEAD:tests/architecture/test_imports.py > <literal scratch path>` (blob `ca7a75af…`), then the four round-1 hunks re-entered with Edit, giving blob `c1e8220d…` (identical to the applied file) before any round-2 edit. Acceptance and golden: Read, then Write, giving blobs `5f8e5373…` and `6f46d72c…` (identical) before any edit |
| `git apply --check docs/proposals/CORE-005-tests-r2.patch` | PASS: exit 0, no output, one standalone command, on the final bytes between 20:35:41Z and 20:36:08Z (and on a first build between 20:34:01Z and 20:35:05Z). Never applied |
| Independent result check | `tools\apply_in_memory.py` applies every hunk to the current bytes with strict context checks; both results equal the scratch copies byte for byte (20:36:08Z) |

### Expected values after apply (LF, one trailing newline, no BOM, ASCII)

| File | Lines | Bytes | SHA256 | Git blob (`git hash-object --path=<repo path>`; same with `--no-filters`) |
|---|---|---|---|---|
| `tests/acceptance/CORE-005/test_data_bars.py` | 888 | 44950 | `ec99d21b9c29892468a201dde9e84d7b90d272eb22b0b6d42a72fb41dec53d16` | `f3273a154a82dab33fa4b07fcbea52588ac67f0c` |
| `tests/architecture/test_imports.py` | 1508 | 72589 | `2d3d05d3814cacf7b41dab9f1fd774352b0e7e6a19ca4a2094d3f1c98aa3c3ac` | `1319cce4f673cd4df1ff73925265788cfbcffca1` |
| `tests/golden/CORE-005/bars_cases.py` (unchanged) | 262 | 17775 | `f44acafed99317a0e117c20b2d12e12c0584d0515d790a01f35dc1dd0586dd59` | `6f46d72c44787fd0ebdd0a7c2a33c0e00cca9f6b` |

`tools\format_check.py` on the two amended files: no CR, BOM, tab or trailing space; ASCII; syntax OK; maximum width
106 and 108, the files' existing maxima; 0 hits for the red-flag line patterns (skip/only/xfail, type-ignore,
noqa, swallowed errors, secrets, destructive commands, importorskip, TODO, FIXME, placeholder or mock).

### Changes by finding and contract item

| Item | Change | AC |
|---|---|---|
| F1 (High) | The rows "ohlc_inconsistent: open above high" and "open equal to high and close equal to low are inside [low, high]" pass the override key `open_` (the `_m1` parameter) instead of `open`. Labels and expectations are unchanged | AC-03 |
| F2 | `bar.extra = 1` expects `pytest.raises((FrozenInstanceError, TypeError))`. Setting and deleting each field still expect `FrozenInstanceError`, and the `__dict__` check stays | AC-01 |
| F3 | Docstring convention: a bar-less Saturday or Sunday is not a key of `report.days`, even inside the span. New `_GAP_CASES` row: Fri 2026-03-13 20:55–20:59 → Mon 2026-03-16 13:00–13:04 UTC, no weekend bar; 900 in-session minutes give `unexpected_gap` WARN at Monday 13:00, and days are {Fri PASS, Mon WARN}. Comment in the AC-04 gap test. Handoff text corrected above | AC-04 |
| F4 | New `test_ac02_m15_open_times_raw_and_utc_under_rules_whose_offset_is_not_zero`. Rule +7200 s (the AC-05 synthetic server): one bar at raw 2026-03-10 00:30 = 2026-03-09 22:30 UTC, 5 M1, `incomplete`. Rule +600 s: raw 22:38–22:42 on 2026-03-09 gives two slots, raw 22:25 = 22:15 UTC (2 M1) and raw 22:40 = 22:30 UTC (3 M1), both `incomplete`; `time_raw == bar_open(...)` and `time_utc == to_utc(...)` | AC-02 |
| F5 | Four `_DEFECT_CASES` rows: open below low (`ohlc_inconsistent`); open 0, high 0 and close −0.001 (each `ohlc_inconsistent` and `non_positive_price`, STOP at 13:05, day STOP) | AC-03 |
| F6 | Handoff text only (convention 2 above) | – |
| F7 | Removed `assert Bar(*(valid[name] for name in _FIELDS)) == bar` | AC-01 |
| F8 | `type(start_day) is int and type(end_day) is int` became, per weekday, `isinstance(weekday, int) and not isinstance(weekday, bool)`. The exact values (4, 17:00) and (6, 18:00) are still asserted | AC-04 |
| F11 | `aggregate([element], 15, rule, one)` with `one = validate_m1(bars[:1], rule, H001_CLOSURES, 5)`, a report of matching length, instead of the report of `[]` | AC-03 |
| v1.1 item 1 | New `test_ac01_v11_bar_refuses_negative_volume_m1_count_below_one_and_a_non_utc_offset`: `ValueError` for `tick_volume` −1 and −7, `m1_count` 0 and −1, and an aware `time_utc` at the same instant with offset +07:00 (fixed `timezone`), Asia/Bangkok or America/New_York (both via `timebase.to_zone`). `m1_count` 16 and 30 (timeframe 15) and 1441 (timeframe 1440) construct | AC-01 |
| v1.1 items 1 and 5 | New `test_ac02_v11_aggregate_keeps_duplicate_and_out_of_order_m1_and_flags_them`. 13:00–13:14 plus a second 13:14 (close 4000.250, spread 260): `duplicate_time` STOP at 13:14; one M15 bar with `m1_count` 16 > 15, flags {`duplicate_time`}, close 4000.250 and spread 260 from the later copy (stable order by `time_raw`), volume 112. 13:01–13:14 then 13:00: `time_not_increasing` at 13:00; one bar of 15 M1 that opens at the 13:00 open (3999.950) and closes at the 13:14 close (4000.250). The input is untouched in both | AC-02, AC-03 |
| v1.1 item 2 | New `test_ac03_v11_negative_max_gap_minutes_is_refused`: −1 and −5 raise `ValueError` with and without bars; 0 is accepted | AC-03 |
| v1.1 item 3 | New `test_ac04_v11_report_carries_its_calendar_and_aggregate_judges_incomplete_by_it`. A calendar with a 16:50–18:10 New York break (off the M15 grid). `report.calendar` equals the calendar passed (also for empty input) and cannot be set. Bars 20:45–20:49 and 22:10–22:14 UTC on 2026-03-10: no defect, and neither M15 bar is `incomplete`. The same bars under `H001_CLOSURES`: `unexpected_gap` at 22:10, both bars `incomplete`, the 22:00 bar also `unexpected_gap`. Under the off-grid calendar, bars missing 20:49 and 22:12: both `incomplete` | AC-04 |
| v1.1 item 4 | Architecture: `_inspect_data_snapshot_float_source` (the snapshot checks plus the costs/risk float name and literal ban), `_inspect_data_package_source` (`src/sochron/data/__init__.py` under the snapshot package rules, current package `sochron.data`) and `_inspect_core_source`. The AC-06 directory test applies them: core as before, snapshot with the float ban, and `data/__init__.py` when the file exists. Two new self-tests: `test_ac06_v11_snapshot_checker_bans_float_names_and_literals_and_keeps_every_rule` and `test_ac06_v11_data_package_init_checker_reports_acquire_io_random_and_admits_the_snapshot` | AC-06 |
| v1.1 item 5 | `empty_weekday` with `time_raw` None was already asserted in round 1 (no change). Weekend days: F3. Aggregate order: the duplicate and out-of-order rows | – |

### Asserts changed or removed (AST comparison)

`tools\ast_compare.py` compares every assert statement and every `with pytest.raises(...)` block (its context and
body) per module-level definition, as a multiset of `ast.dump` (acceptance 20:37:48Z on the final bytes;
architecture 20:32:59Z, not edited afterwards).

- **Acceptance vs the applied round-1 file:** 131 checks, of which **127 are kept AST-identical** in the same
  function. The 4 not kept are the intended ones: old line 166 removed (F7); old line 216, `FrozenInstanceError`
  widened to `(FrozenInstanceError, TypeError)` (F2); old line 446, the report `empty` replaced by `one` (F11);
  old line 462, the exact-int check replaced by int-not-bool (F8). Assert statements 109 → 141. 38 of 45 module
  definitions are identical and their order is kept; changed are the docstring, the datetime import (adds
  `timezone`), the AC-01 test (F7, F2), `_DEFECT_CASES`, the AC-03 empty-input test (F11), the AC-04 calendar test
  (F8) and `_GAP_CASES`; five tests are new. Table rows: in `_DEFECT_CASES` 17 of 19 rows are identical and the
  other 2 differ only in the key `open` → `open_` (F1), plus 4 new rows; in `_GAP_CASES` 19 of 19 are identical,
  plus 1 new row. One comment in the AC-04 gap test was extended (F3).
- **Architecture vs the applied round-1 file:** 19 of 19 checks identical. 42 of 44 definitions identical; changed
  are the module docstring (one sentence appended) and the AC-06 directory test, whose 3 asserts are identical
  (the loop now takes one checker per package and adds `data/__init__.py`). 9 definitions are new.
  `_allowed_import`, `_inspect_source`, `_inspect_data_snapshot_source`, `_PURE_CHECKERS` and every FIX-001 and
  CORE-001 table are unchanged.
- **Architecture vs HEAD `f9504f8`** (blob `ca7a75af…`): 14 of 14 checks identical; only the docstring and
  `_allowed_import` (both round 1) changed among the old definitions.
- **Golden:** unchanged (blob `6f46d72c…`).

### Red against the current repository (no implementation)

| Command (repo root, `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest …`) | Result | Time |
|---|---|---|
| `<mirror>/tests/acceptance/CORE-005 <mirror>/tests/golden/CORE-005 <mirror>/tests/architecture -q -p no:cacheprovider -c pyproject.toml --rootdir . -rf` | **56 failed, 12 passed** in 0.70s, exit 1, no collection error. Reasons: "AC-01: sochron.core.Bar not implemented" ×2, AC-02 ×3, AC-03 ×26, AC-04 ×23, AC-05 ×1, and "AC-06: …\src\sochron\data\snapshot does not exist; implementation missing" ×1. The 12 passes are the 8 existing architecture tests and the 4 AC-06 self-tests | 20:36:30–20:36:31 |
| `tests --ignore=tests/acceptance/CORE-005 --ignore=tests/golden/CORE-005 --ignore=tests/architecture` plus the three mirror directories, `-q -p no:cacheprovider` | **56 failed, 793 passed** in 5.00s, 0 skipped | 20:36:31–20:36:36 |
| `tests -q -p no:cacheprovider` (repository as it is, round 1 applied) | 46 failed, 791 passed in 4.37s (as in review tests-r1) | 20:36:36–20:36:41 |

So after the apply: `uv run --offline pytest tests -q -p no:cacheprovider` → 56 failed, 793 passed, 0 skipped, and
`uv run --offline pytest tests/architecture -q -p no:cacheprovider` → 1 failed, 12 passed. After a correct
implementation: 849 passed, 0 skipped.

### Satisfiability (contract-only scratch reference)

- **Reference.** `…\scratchpad\ref\sochron\core\__init__.py`, `…\ref\sochron\data\__init__.py` (docstring only) and
  `…\ref\sochron\data\snapshot\__init__.py`, written from the contract v1.1 and the acceptance-file conventions
  only, never in `src/`. Evidence only; do not copy it as the implementation. On purpose it uses
  `@dataclass(frozen=True, slots=True, kw_only=True)` (F2, F7) and checks the report length before the element
  types in `aggregate` (F11). The snapshot has no float and converts time only through `timebase`. Tree:
  `git archive HEAD src | tar -x -C <literal scratch>\tree` (timebase, costs, risk as at HEAD), with the reference
  copied over `core` and `data`.
- **How the reference was the code under test.** `tools\run_ref.py`, launched from the repo root as
  `timeout 600 uv run --offline --no-sync python -I -B run_ref.py <tree> pytest …`. `-I` drops the script directory,
  the cwd and every `PYTHON*` variable from the path. The runner inserts `<tree>\src` at `sys.path[0]` and imports
  `sochron`, `core`, `data`, `data.snapshot`, `timebase`, `costs` and `risk` from it, checking each file, before
  `pytest.main`. The tests' `syspath_prepend(<cwd>/src)` and pytest's `pythonpath` later put the repository's `src`
  first, but a submodule import resolves through the already imported `sochron.__path__`. A session-finish hook
  asserts that every `sochron*` entry of `sys.modules` has its file under `<tree>\src` (otherwise exit 3). Every
  run printed "PROOF OK: 20 sochron modules loaded, all from …\scratchpad\tree\src" and the core, snapshot and
  timebase file paths.
- **Architecture on the reference.** `run_ref.py <tree> arch <test file>` loads the test file by path, changes the
  cwd to the tree (the tests read `Path.cwd() / "src"`) and calls each test function; this is not pytest.

| Run (final bytes) | Result | Time |
|---|---|---|
| Amended acceptance + golden on the reference | **55 passed** in 0.28s, PROOF OK | 20:37:02 |
| Amended architecture, all 13 test functions, cwd = tree | **13 passed**, 0 failed | 20:37:02–20:37:03 |
| Whole suite except `tests/architecture`, with the amended acceptance + golden, on the reference | **836 passed** in 4.01s, 0 skipped, PROOF OK (836 + 13 = 849) | 20:37:03–20:37:07 |
| The round-1 acceptance file (in place) on the same reference | 4 failed, 41 passed: AC-01 at line 166 (keyword-only `Bar`, F7), the two F1 rows (`_m1() got an unexpected keyword argument 'open'`) and the AC-03 empty-input test (report-length check first, F11) | 20:37:07–20:37:32 |

### Mutation evidence (scratch only; `tools\mutants.py run4`, 20:37:07–20:37:32)

Each mutant is a copy of the tree with exact one-time text replacements; earlier runs `run1` to `run3` are kept
and nothing was deleted. "Amended" means the round-2 files; "round 1" means the applied locked files, run in
place. Every pytest run printed PROOF OK.

| Mutant | Amended | Round 1 |
|---|---|---|
| Reference (control) | 55 passed | 4 failed (above) |
| `NO_TICK_VOLUME_FLOOR`, `NO_M1_COUNT_FLOOR`, `ACCEPTS_NON_UTC_OFFSET` | 1 failed each: the v1.1 AC-01 test | the same 4 as the reference (not caught) |
| `M1_COUNT_CAPPED_AT_TIMEFRAME` | 2 failed: the v1.1 AC-01 test and the v1.1 AC-02 test (aggregate raises on the 16-M1 slot) | 4 (not caught) |
| `NEGATIVE_MAX_GAP_ACCEPTED` | 1 failed: the v1.1 AC-03 test | 4 (not caught) |
| `INCOMPLETE_IGNORES_CLOSURES`, `INCOMPLETE_USES_H001_NOT_REPORT_CALENDAR` | 1 failed each: the v1.1 AC-04 test | 4 (not caught) |
| `NO_CALENDAR_FIELD` | 4 failed: golden AC-02, offset AC-02, AC-04 M15 bars, v1.1 AC-04 | 6 |
| `AGGREGATE_TIME_UTC_IGNORES_RULE`, `AGGREGATE_FLOORS_RAW_SECONDS` (F4) | 1 failed each: the offset AC-02 test | 4 (not caught) |
| `OHLC_SKIPS_OPEN_BELOW_LOW` (F5) | 2 failed: open below low, open zero | 4 (not caught) |
| `OHLC_SKIPS_OPEN_ABOVE_HIGH` (F1) | 1 failed: open above high | 4 (that row cannot run) |
| `NON_POSITIVE_CHECKS_LOW_ONLY` (F5) | 3 failed: open zero, high zero, close negative | 4 (not caught) |
| `NO_SORT_WITHIN_SLOT`, `UNSTABLE_SORT_WITHIN_SLOT`, `AGGREGATE_DROPS_DUPLICATES` | 1 failed each: the v1.1 AC-02 test | 4 (not caught) |
| `WEEKEND_DAYS_IN_REPORT_AS_PASS` (F3) | 5 failed: the 4 round-1 weekend rows and the new Friday → Monday row | 8 |
| `CONTROL_INTENUM_WEEKEND` (`calendar.FRIDAY`, `calendar.SUNDAY`; F8) | 55 passed | 5 (adds the AC-04 calendar test) |
| `CONTROL_SLOTS_TRUE_POSITIONAL` (F2) | 55 passed | 4; AC-01 fails at line 217 with `TypeError: super(type, obj): obj must be an instance or subtype of type` |
| `CONTROL_KW_ONLY_HAND_WRITTEN_SLOTS` (F7) | 55 passed | 4; AC-01 fails at line 166 |

AC-06 directory test, cwd = the mutant tree:

| Planted | Amended | Round 1 |
|---|---|---|
| snapshot: `RATE = float("1.5")`; `SPREAD = 0.25` | FAIL: "forbidden float name"; "forbidden float literal" | PASS (not caught) |
| `data/__init__.py`: `open("seed.txt").read()`; `import random`; `from . import acquire`; `import time` and `time.time()` | FAIL: "forbidden clock/I/O call open"; "forbidden random import"; "forbidden import sochron.data"; "forbidden clock/I/O call time.time" | PASS (not caught) |
| snapshot `open(...)`; core `time.time()` | FAIL | FAIL (rules kept) |
| Controls: the reference; `data/__init__.py` with `from .snapshot import aggregate, validate_m1`; core `SCALE = 0.5`; no `data/__init__.py` (namespace package) | PASS | PASS |

### Checks run (all from the repo root; commit `f9504f8` plus the uncommitted round-1 state)

| Command / procedure | Result | Time |
|---|---|---|
| `git rev-parse HEAD`; `git status --porcelain --untracked-files=all`; `ls` | `f9504f8…`; ` M tests/architecture/test_imports.py`, `?? docs/handoff/CORE-005.md`, `?? docs/reviews/CORE-005-tests-r1.md`, the two new test files; unchanged after every later command | 20:06 |
| `sha256sum` and `git hash-object --path=…` / `--no-filters` of the three round-1 files | `0ccd3afe…`, `f44acafe…`, `85481534…`; `5f8e5373…`, `6f46d72c…`, `c1e8220d…`: equal to the round-1 table | 20:06:05 |
| `git show HEAD:tests/architecture/test_imports.py > <literal scratch path>` (×2); `git hash-object`; `sha256sum` | `ca7a75af…`, `0e1d7a21…` | 20:1x |
| Rebuilt round-1 architecture copy; verbatim acceptance and golden copies; `git hash-object --path=…` | `c1e8220d…`, `5f8e5373…`, `6f46d72c…` (identical) | 20:1x–20:2x |
| Reference, amended acceptance + golden (first build) | 55 passed, PROOF OK | 20:27:53–20:27:54 |
| `tools\mutants.py run1` / `run2` / `run3` (run2 stopped at its own replacement check: the decorator text also appears in the reference docstring; fixed in run3) | as in the tables above | 20:30:33–20:32:02 |
| `diff -u … > docs/proposals/CORE-005-tests-r2.patch` (×2, first build) and `git apply --check` (standalone) | PASS | 20:34:01–20:35:05 |
| Docstring line edited to name F3; the patch rebuilt (×2 `diff -u`) | 506 lines, 28265 bytes, 0 CR | 20:35:41 |
| `git apply --check docs/proposals/CORE-005-tests-r2.patch` (standalone) | PASS, exit 0, no output | 20:35:41–20:36:08 |
| `git apply --numstat docs/proposals/CORE-005-tests-r2.patch` (standalone) | +211/−12 acceptance, +134/−13 architecture | 20:35:41–20:36:08 |
| `sha256sum`; `apply_in_memory.py`; `git hash-object --path=…` and `--no-filters`; `format_check.py` | values in the tables above; byte-identical; OK | 20:36:08–20:36:09 |
| Red runs and baseline (table above) | 56 failed / 12 passed; 56 failed / 793 passed; 46 failed / 791 passed | 20:36:30–20:36:41 |
| Reference runs and `mutants.py run4` (tables above) | 55 passed; 13 passed; 836 passed; mutants as tabled | 20:37:02–20:37:32 |
| `ast_compare.py` (acceptance final bytes) | 127 of 131 checks kept; the 4 intended changes | 20:37:48 |

Scratch evidence, all under `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\1fd58dca-2b7e-48f7-aed4-6b27414e80f3\scratchpad\`:
`mirror\` (the amended files), `head\test_imports_head.py`, `ref\` (the reference), `tree\` (HEAD `src` + reference),
`mut\run1` … `mut\run4`, `tools\` (`run_ref.py`, `mutants.py`, `ast_compare.py`, `format_check.py`,
`apply_in_memory.py`) and `evidence\` (`final-red-mirror.log`, `final-red-suite.log`, `mutants-run4.json` and the
earlier logs). Nothing was deleted.

### Blocks and detector reports

- **Post-run detector (N6), 20:06Z**, after this session's first command (read-only: `git rev-parse`, `git status`,
  `ls`). It listed exactly `uncommitted M tests/architecture/test_imports.py`,
  `uncommitted A tests/acceptance/CORE-005/test_data_bars.py` and `uncommitted A tests/golden/CORE-005/bars_cases.py`,
  the targets of the applied round-1 patch. The next command (20:06:05Z) gave six SHA256 and blob values equal to
  the round-1 table, so I continued as CLAUDE.md allows. It did not fire again.
- **guard-bash, between 20:34:01Z and 20:35:05Z (first build):** `Blocked by .claude/hooks/guard-bash.mjs: git apply must be one
  standalone literal command. Run each action separately.` My command chained `git apply --numstat
  docs/proposals/CORE-005-tests-r2.patch` with `sha256sum`, the in-memory apply, `git hash-object` and `git status`,
  against my own instruction to run every `git apply` alone; none of it ran. Under the owner's standing
  "standalone rerun" exception (F21, 2026-10-20) I reran `git apply --numstat …` alone and ran the other read-only
  commands as a separate command without `git apply`.
- No deny rule fired and nothing else was blocked.

### Limits and questions

1. **`data/__init__.py` imports.** It may import only what the snapshot may, plus the snapshot through
   `from .snapshot import …`, `from sochron.data.snapshot import …` or `import sochron.data.snapshot`.
   `from . import snapshot` (and `from sochron.data import snapshot`) is reported as "forbidden import sochron.data":
   the shared checker judges a from-import by its module, and allowing that module would also let
   `from . import acquire` through (review tests-r1 F10). A docstring-only file passes. Owner or reviewer: accept,
   or ask for a finer rule.
2. **A missing `data/__init__.py` is not required.** The directory test checks the file when it exists; a namespace
   package runs no code of its own (control mutant). The contract lists the file as allowed, not as required.
3. The float ban covers the snapshot only, as v1.1 item 4 says; a float in core or `data/__init__.py` is not
   reported (control mutant).
4. The +600-second rule in the F4 test is synthetic (an offset that is not a multiple of 15 minutes). It exists to
   tell "group by `bar_open` under the rule" from a floor on raw seconds. An implementation that refused such a
   `TimeRule` would fail it; the contract gives no ground for refusing a rule.
5. `incomplete`: the tests pin only the two unambiguous cases (every missing minute inside a closure: not
   incomplete; an in-session minute missing: incomplete). No test has an M1 inside a closure.
6. The duplicate row pins stable order by `time_raw` (v1.1 item 5). The out-of-order row uses one slot, so the
   order of `AggregatedBar`s for unsorted input across slots stays unasserted (the contract does not state it).
7. Not changed by this patch: F9 (now contract v1.1 item 5), round-1 question 6 (UNKNOWN > WARN unreachable),
   round-1 question 7 (the 16:45 New York slot is `incomplete` on every trading day; decide before CORE-006 or R1)
   and the known checker limits (`logging`, `sqlite3`).
8. Not run: CI on Linux; the apply itself (the implementer's step); `bash scripts/controls/red-flags.sh main` and
   `node scripts/controls/check-locked-paths.mjs main` on the patched tree (I applied the script's line patterns to
   the two amended files instead: 0 hits); any real implementation.

### Implementer's apply steps (Claude, D-006)

1. **Confirm the starting state.** Branch `feat/CORE-005-data-bars`; HEAD `f9504f8` or a later commit that does not
   touch the three test files; round 1 still applied and uncommitted with the base values in the artifact table
   (`sha256sum` and `git hash-object --path=<path> <path>`); `sha256sum docs/proposals/CORE-005-tests-r2.patch` =
   `1567e22a445beff49237c0446b1b14ad303a9076a529d62d4879f04b0748346c`. Run one read-only command first. If the
   detector then lists the three round-1 files, check them against the round-1 values, as this session did.
2. **Apply.** Each as one standalone command from the repo root:
   `git apply --check docs/proposals/CORE-005-tests-r2.patch`, then `git apply docs/proposals/CORE-005-tests-r2.patch`.
   Expected detector report: exactly `tests/acceptance/CORE-005/test_data_bars.py` and
   `tests/architecture/test_imports.py`. Any other report means stop and ask (N6).
3. **Verify** both changed files against the "Expected values after apply" table (`sha256sum`,
   `git hash-object --path=<path> <path>`) and that the golden file is still `6f46d72c…`; stop on any mismatch.
   Then run `git apply -R --check docs/proposals/CORE-005-tests-r2.patch` standalone (expected exit 0).
4. **Run red.** `uv run --offline pytest tests -q -p no:cacheprovider` → 56 failed, 793 passed, 0 skipped. Every
   acceptance failure says `sochron.core.Bar not implemented`; the architecture failure names the missing
   `src/sochron/data/snapshot`.
5. **Fresh-session review** of the round-2 diff and this section, in a session that is not this one, the
   implementer or the round-1 test author (`docs/reviews/CORE-005-tests-r2.md`). A fix comes as a new patch from a
   fresh test-author session, never as a direct edit.
6. **Then commit red** with `Refs: CORE-005`, implement under the contract without touching the locked files, and
   expect 849 passed, 0 skipped once the implementation is complete.

Delivery state: **proposal written and checked; not applied, committed, merged or deployed.**

## Implementer notes (Claude Code, the CORE-005 implementer)

Commits: red `3605818`, F13 `5993560`, merge main `d97bd1f`, `core.Bar` `7fd6fe1` (committed by the owner from the
implementer's file, byte-identical), `.gitignore` `b54605d` and `b067cda` (F9), implementation `07d2639`, review r1
fixes `e52312a` (F1), `da2ba68` (F2), `61b75ed` (F4), `e9a0875` (F5), `280538b` (F8). Evidence: `docs/evidence/CORE-005.md`.

Decisions, for the re-reviewer:
- `core` imports nothing from `sochron`, so `TIMEFRAMES_MINUTES` is repeated there; a unit test keeps it equal to
  timebase's set.
- Duplicates: every time read is remembered; a repeat anywhere is `duplicate_time`, otherwise a time below the bar just
  before is `time_not_increasing` (one code per bar).
- Gaps: minutes strictly between two increasing bars are walked one by one through `timebase.to_zone`, stopping once
  more than `max_gap_minutes` in-session minutes are found (weekends are walked in full).
- `incomplete`: a minute of the slot with no M1 whose wall time is in session under `report.calendar`.
- Unit tests for snapshot live in `tests/unit/snapshot/` because `.gitignore`'s market-data rule `data/` also hides
  `tests/unit/data/`.

Timing script used for the evidence (run from the repo root as
`uv run --offline --no-sync python -I -B <script> <repo>/src 500000`; result on the reference machine 2026-10-24:
`validate_m1` 3.08 s, `aggregate` 0.91 s, 0 defects; the original scratch run also timed building the 500,000 bars,
2.92 s, which this trimmed copy does not print):

```python
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter

sys.path.insert(0, sys.argv[1])
from sochron.core import Bar
from sochron.data.snapshot import H001_CLOSURES, aggregate, validate_m1
from sochron.timebase import rule_for, to_utc, to_zone

count = int(sys.argv[2])
rule = rule_for("Exness-MT5Trial14")
minute, price, bars = datetime(2024, 1, 1, tzinfo=UTC), Decimal("2000.000"), []
while len(bars) < count:
    local = to_zone(minute, "America/New_York")
    closed = (local.hour == 17 or (local.weekday() == 4 and local.hour >= 17)
              or local.weekday() == 5 or (local.weekday() == 6 and local.hour < 18))
    if not closed:
        raw = int(minute.timestamp())
        bars.append(Bar(raw, to_utc(raw, rule), 1, price, price + Decimal("0.5"), price - Decimal("0.5"), price, 240, 10, 1))
    minute += timedelta(minutes=1)
started = perf_counter()
report = validate_m1(bars, rule, H001_CLOSURES, 5)
print("validate_m1", perf_counter() - started, len(report.defects))
started = perf_counter()
m15 = aggregate(bars, 15, rule, report)
print("aggregate", perf_counter() - started, len(m15))
```

Checks: `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` -> 2875 passed after the r1 fixes.
