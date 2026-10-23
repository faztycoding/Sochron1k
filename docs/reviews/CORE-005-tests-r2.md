# Review CORE-005-tests round 2 · base main · head f9504f8 + applied D-006 patches r1 and r2 (uncommitted) · reviewer Claude Code (fresh session 25327c31, tests reviewer round 2 under the role swap)

Scope: the three locked test files after `docs/proposals/CORE-005-tests.patch` (round 1) and
`docs/proposals/CORE-005-tests-r2.patch` (round 2) were applied:
`tests/acceptance/CORE-005/test_data_bars.py`, `tests/golden/CORE-005/bars_cases.py` and
`tests/architecture/test_imports.py`. I reviewed them against `docs/contracts/CORE-005-data-bars.md` v1.1 (the "v1.1"
block, approved by the owner 2026-10-24 03:0x), the round-1 review `docs/reviews/CORE-005-tests-r1.md` (F1–F12) and
the round-2 section of `docs/handoff/CORE-005.md`. This is the owner's role swap (contract Status line; Codex is out
of quota until 2026-10-28 19:41). I am not the implementer, not a test author and not the round-1 tests reviewer.
No implementation of CORE-005 exists. This file is the only file I wrote in the repository. Nothing is staged,
nothing was pushed, and the locked files were read in place: never copied, never edited. All times are UTC on
2026-10-23 (03:4x–04:0x Asia/Bangkok on 2026-10-24).

Verdict: **Ready to commit red: yes.** All twelve round-1 findings are closed:
- The hashes, the reverse check and the red state match the handoff exactly.
- My own contract-only reference passes all 55 acceptance tests and all 13 architecture tests (whole suite: 849
  passed, 0 skipped), with every `sochron` module proven loaded from scratch.
- 32 wrong implementations are each caught, and 7 contract-allowed controls pass.
- Every round-1 assert is AST-identical apart from the six intended changes. Every HEAD architecture assert is
  identical.

One new finding: F13 (Low, question). Two lines of the contract's interface block still contradict v1.1 item 1. The
tests follow v1.1, so F13 does not block the red commit; it is for the owner to tidy the contract text.

Detector note (N6): the post-run locked-path detector fired once, after this session's first command (20:43:43Z,
read-only: `git rev-parse`, `git status`, `sha256sum`, `git hash-object`, `wc`). It listed exactly
`uncommitted M tests/architecture/test_imports.py`, `uncommitted A tests/acceptance/CORE-005/test_data_bars.py` and
`uncommitted A tests/golden/CORE-005/bars_cases.py`. Those are the target files of the applied `docs/proposals/`
patches and nothing else. The same command had printed all three SHA256 and blob values, and all equal the handoff
(below), so I continued as CLAUDE.md allows. It did not fire again. No hook or deny rule blocked anything.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F13 | Low | question | `docs/contracts/CORE-005-data-bars.md:45-46` (against `:65`) | The interface block still reads `m1_count: int # M1 = 1; แท่งที่ประกอบ = จำนวน M1 ในแท่ง (1..timeframe)` (an aggregated bar holds 1..timeframe M1, `:45`) and "ตรวจตอนสร้างเฉพาะชนิดและความเป็น finite เท่านั้น" (construction checks only types and finiteness, `:46`). v1.1 item 1 (`:65`) adds `ValueError` for `tick_volume < 0`, `m1_count < 1` and a non-UTC offset, and says "ไม่มีเพดานบนของ `m1_count`" (no upper bound on `m1_count`). `git show HEAD -- docs/contracts/CORE-005-data-bars.md` shows that v1.1 changed `:54` and AC-06 but left `:45-46` as they were. The locked tests follow v1.1: mutant `M1_COUNT_UPPER_BOUND` fails 2 tests; `NO_TICK_VOLUME_FLOOR`, `NO_M1_COUNT_FLOOR` and `ACCEPTS_NON_UTC_OFFSET` fail 1 each (table below). | The implementer, or a later reader (CORE-006, R1), reads the interface block rather than the v1.1 block. | The contract states two rules for one field. An implementer who follows `:45` adds a cap and gets two red tests in files they may not edit. A later consumer may treat `m1_count == timeframe` as "complete", although a duplicate M1 can make it 16 for M15 (the `incomplete` and `duplicate_time` flags are the signal). | The owner amends `:45` to, for example, `m1_count: int # >= 1, no upper bound (v1.1 item 1)`, and `:46` to name the v1.1 refusals. No test changes. | The interface block and the v1.1 block agree, and the suite result is unchanged. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## Round-1 findings (re-review)

All line numbers refer to the current files. "REF" is my own reference implementation. "Mutant" and "control" are
the scratch variants listed under satisfiability below. Each was run against the locked files in place.

| ID | Round-1 sev | Status | Evidence |
|----|-------------|--------|----------|
| F1 | High | **closed** | Both rows now pass the `_m1` parameter name: `{5: {"open_": "4000.400"}}` (`test_data_bars.py:431`) and `{5: {"open_": "4000.300", "close": "3999.900"}}` (`:440`). Labels and expectations are unchanged: the AST diff of `_DEFECT_CASES` shows only the key `open` → `open_` in these two rows. REF passes both. Mutant `OHLC_SKIPS_OPEN_ABOVE_HIGH` fails exactly "ohlc_inconsistent: open above high", so the open > high branch is now exercised. AC-07 is reachable: 849 passed, 0 skipped on REF. |
| F2 | Medium | **closed** | `:227` `with pytest.raises((FrozenInstanceError, TypeError)): bar.extra = 1`. Setting and deleting each field still require `FrozenInstanceError` (`:222-226`), and `__dict__` must be absent (`:229`). REF uses plain `@dataclass(frozen=True, slots=True)` on CPython 3.12.15 and passes AC-01. No weakening: a non-frozen slots class raises a bare `AttributeError` there, which `(FrozenInstanceError, TypeError)` does not catch. |
| F3 | Medium | **closed** | Contract v1.1 item 5 decides it: a bar-less Saturday or Sunday is not a key of `report.days`. The rule is stated in the acceptance docstring (`:18-19`) and the AC-04 comment (`:714-716`). A new row, Fri → Mon with no weekend bar (`:676-679`), was added. In the handoff, convention 4 (`:96-100`), question 5 (`:126-128`) and the look-hard line (`:224-225`) are corrected and marked "Corrected in round 2". Mutant `WEEKEND_DAYS_IN_REPORT_AS_PASS` fails 5 rows: the 4 round-1 weekend rows and the new one. The test and the handoff now agree. |
| F4 | Low | **closed** | New `test_ac02_m15_open_times_raw_and_utc_under_rules_whose_offset_is_not_zero` (`:331-366`). Mutants `AGG_TIME_UTC_IGNORES_RULE` (`datetime.fromtimestamp(slot, UTC)`; it got 2026-03-10 00:30 instead of 2026-03-09 22:30) and `AGG_FLOORS_RAW_SECONDS` (slot floor on raw seconds) each fail exactly this test. |
| F5 | Low | **closed** | New rows: open below low (`:433-435`), and open 0, high 0, close −0.001 (`:447-455`), each giving `ohlc_inconsistent` plus `non_positive_price`. Mutant `OHLC_SKIPS_OPEN_BELOW_LOW` fails 2 rows (open below low, open zero). `NON_POSITIVE_CHECKS_LOW_ONLY` fails 3 (open zero, high zero, close negative). |
| F6 | Low | **closed** | Handoff `:88-93` now says "63–66-minute breaks pass, 67-minute and longer breaks are WARN", "first bar 18:00–18:05 NY", "2–7 in-session minutes" and "G − 61". That matches the locked rows `:659-661` (20:57 → 22:03 UTC, 66 minutes, no defect) and `:662-664` (67 minutes, `unexpected_gap`), both of which REF passes. |
| F7 | Low | **closed** | The positional-construction assert is gone (AST: the one lost check in AC-01, old line 166). Control `CONTROL_KW_ONLY_BAR` (`kw_only=True`) passes 68/68. Field order and keyword construction are still asserted (`:169-174`). |
| F8 | Low | **closed** | `:606-607` `isinstance(weekday, int) and not isinstance(weekday, bool)`; the values are still exact (`:608-609`). Control `CONTROL_INTENUM_WEEKEND` (`calendar.FRIDAY`, `calendar.SUNDAY`) passes 68/68. |
| F9 | Low (question) | **closed** (owner decision) | Contract v1.1 item 5: `empty_weekday` has `time_raw` None. That is the single exception to the invariant at `:75`, which v1.1 also amends. `_check_report` (`:128`) is unchanged and now matches the contract. Mutant `EMPTY_WEEKDAY_HAS_A_TIME` (the raw time of 00:00 UTC of the empty day) fails the AC-03 empty_weekday row and AC-05. |
| F10 | Low (question) | **closed** | `test_imports.py:637-640` adds `_inspect_data_package_source`, which applies the snapshot import rules with current package `sochron.data`. The directory test applies it to `src/sochron/data/__init__.py` when the file exists (`:656-660`), and a new self-test covers it (`:1494-1508`). The 8 `DATA_INIT_*` plants are all reported (table below). The controls (re-export, `import … as`, missing file) pass. |
| F11 | Low (question) | **closed** | `:569` `one = validate_m1(bars[:1], …)` and `:576` `aggregate([element], 15, rule, one)`. Control `CONTROL_REPORT_LENGTH_CHECKED_FIRST` (aggregate refuses a report whose `m1_bars` differs from `len(bars)`, before the element types) passes 68/68. |
| F12 | Low (question) | **closed** | Contract v1.1 item 3 adds `ValidationReport.calendar`, and `aggregate` judges `incomplete` by it. New test `test_ac04_v11_report_carries_its_calendar_and_aggregate_judges_incomplete_by_it` (`:771-817`) uses an off-grid 16:50–18:10 New York break. Mutants `REPORT_HAS_NO_CALENDAR_FIELD`, `AGG_IGNORES_REPORT_CALENDAR_USES_H001` and `AGG_INCOMPLETE_BY_COUNT_ONLY` each fail exactly this test. |

## Coverage of the contract v1.1 items

Each item has at least one test that fails when the item is not implemented, and no test asks for more than the
item says. Both claims rest on REF, which implements only the contract and passes all 68 tests, and on the controls.

| v1.1 item | Tests | Fails when missing (mutant → failing tests) | Not over-asked (control or REF) |
|-----------|-------|---------------------------------------------|----------------------------------|
| 1. `Bar` refuses `tick_volume < 0`, `m1_count < 1` and an aware non-UTC `time_utc` (`ValueError`); no upper bound on `m1_count` | `test_ac01_v11_…` (`:233-258`); `test_ac02_v11_…` (`:369-403`) | `NO_TICK_VOLUME_FLOOR`, `NO_M1_COUNT_FLOOR`, `ACCEPTS_NON_UTC_OFFSET` → v1.1 AC-01 ("DID NOT RAISE ValueError"). `NON_UTC_OFFSET_AS_TYPEERROR` → v1.1 AC-01 (the item says `ValueError`). `M1_COUNT_UPPER_BOUND` → v1.1 AC-01 and v1.1 AC-02 (`ValueError: m1_count > timeframe` inside `aggregate`) | **m1_count:** only `< 1` must raise. Values 16, 30 and 1441 must construct (`:256-258`), and AC-01 still accepts `m1_count` 1 and `timeframe` for every timeframe (`:180-182`). No test asks for a cap or for `m1_count == 1` on M1 input. |
| 2. `validate_m1` refuses `max_gap_minutes < 0` (`ValueError`) | `test_ac03_v11_negative_max_gap_minutes_is_refused` (`:579-590`) | `NEGATIVE_MAX_GAP_ACCEPTED` → that test | 0 stays valid (`:590`, AC-04 rows `:690-693`) |
| 3. `ValidationReport.calendar`; `aggregate` judges `incomplete` by it | `test_ac04_v11_…` (`:771-817`) | `REPORT_HAS_NO_CALENDAR_FIELD` (`AttributeError: … no attribute 'calendar'`), `AGG_IGNORES_REPORT_CALENDAR_USES_H001`, `AGG_INCOMPLETE_BY_COUNT_ONLY` → that test | **calendar:** the tests need only a readable, frozen field equal (`==`) to the calendar passed, empty input included. No identity, no extra fields, and no direct construction of `ValidationReport` (it is used only in `isinstance`, `:842`). Only the two cases that cannot be read two ways are pinned: every missing minute closed → not incomplete; one in-session minute missing → incomplete. |
| 4. AC-06 covers `src/sochron/data/__init__.py`; `float` names and literals banned in `sochron.data.snapshot` | directory test (`test_imports.py:643-670`); self-tests `:1470-1491`, `:1494-1508` | `FLOAT_NAME_IN_SNAPSHOT` ("line 107: forbidden float name"), `FLOAT_LITERAL_IN_SNAPSHOT` ("line 58: forbidden float literal"). `DATA_INIT_*` ×8: `from . import acquire`, `import sochron.data.acquire`, `import random`, `open(...)`, `time.time()`, `from sochron import broker`, and both `snapshot` spellings in note 1 | **float ban:** applies to the snapshot only. Control `CONTROL_FLOAT_IN_CORE` passes, and the data-package checker adds no float rule, as the item says. **`data/__init__.py` scan:** stdlib (not `socket`), `core`, `timebase` and the snapshot are admitted (controls `CONTROL_DATA_INIT_REEXPORT` and `CONTROL_DATA_INIT_IMPORT_AS` pass). A missing file is allowed (`CONTROL_DATA_INIT_MISSING` passes 68/68). |
| 5. `empty_weekday.time_raw` None; bar-less weekend days not in `days`; `aggregate` keeps unsorted and duplicate input, groups by `bar_open` and orders members stably by `time_raw` | `_check_report` `:128`; the AC-04 rows (incl. `:676-679`); `test_ac02_v11_…` (`:369-403`) | `EMPTY_WEEKDAY_HAS_A_TIME` → AC-03 empty_weekday row and AC-05. `WEEKEND_DAYS_IN_REPORT_AS_PASS` → 5 AC-04 rows. `AGG_REFUSES_UNSORTED_INPUT`, `AGG_KEEPS_INPUT_ORDER_IN_SLOT` (open 4000.000 vs 3999.950), `AGG_UNSTABLE_TIE_ORDER` (close 4000.200 vs 4000.250) and `AGG_DROPS_DUPLICATE_M1` (m1_count 15 vs 16) → v1.1 AC-02 | The duplicate and out-of-order cases each fill all 15 minutes of one slot, so `incomplete` cannot be read two ways there. Slot order across slots for unsorted input is not asserted, and the contract does not state it. |

A note for the owner, not a finding: under the literal D1 rule (`incomplete` when `m1_count < timeframe`), a slot
with one duplicate M1 and one missing in-session minute counts 15 and is not `incomplete`. It still carries
`duplicate_time` (STOP), so its day is STOP. No test covers that combination, and the contract does not ask for one.

## AC status
"FAIL (red, as intended)" is the expected state before implementation.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | FAIL (red, as intended) | 2 tests fail with "AC-01: sochron.core.Bar not implemented". REF passes both. Round-1 coverage is kept (AST), F2 and F7 are fixed, and the v1.1 item 1 refusals are added. |
| AC-02 | FAIL (red, as intended) | 3 tests fail with the AC-02 message: golden, F4 offsets, v1.1 duplicate and out-of-order. The golden file is unchanged (blob `6f46d72c…`). REF reproduces all 11 M15 rows, the 6 defects and the STOP day from my own aggregation code. That code was written from the contract, so the golden tables and an independent derivation agree. |
| AC-03 | FAIL (red, as intended) | 26 tests fail with the AC-03 message (23 `_DEFECT_CASES` rows, the rule-mismatch test, the empty/argument-type test, v1.1 `max_gap_minutes < 0`). F1, F5 and F11 are fixed; F9 is decided. |
| AC-04 | FAIL (red, as intended) | 23 tests fail with the AC-04 message (20 `_GAP_CASES` rows, the calendar test, the M15 closure test, v1.1 `report.calendar`). F3, F8 and F12 are fixed. |
| AC-05 | FAIL (red, as intended) | 1 test fails with the AC-05 message. Unchanged from round 1 (AST-identical). |
| AC-06 | FAIL (red, as intended) | The directory test fails with "AC-06: …\src\sochron\data\snapshot does not exist; implementation missing" (not a silent pass). The 4 AC-06 self-tests pass. On REF the directory test passes. The contract's verification row (an `open(...)`/`time.time()` mutation must be caught) holds: `SNAPSHOT_OPEN_IN_FUNCTION` and `CORE_TIME_TIME_IN_FUNCTION` are reported (the latter also by the CORE-001 AC-07 test). |
| AC-07 | FAIL (red, as intended) | The whole suite gives 56 failed, 793 passed, 0 skipped. It goes green on REF (849 passed, 0 skipped), so AC-07 is reachable now that F1 is fixed. |

## Checked, nothing found (and how)
- **Hashes and working tree (task item 1).** Branch `feat/CORE-005-data-bars`, HEAD
  `f9504f8beeaf8e5625e7f3d30f4e87c4a57f548c` (which changes only the contract: `git show --stat HEAD`). At 20:43:43Z:
  - `sha256sum` gave `ec99d21b9c29892468a201dde9e84d7b90d272eb22b0b6d42a72fb41dec53d16` (acceptance),
    `f44acafed99317a0e117c20b2d12e12c0584d0515d790a01f35dc1dd0586dd59` (golden) and
    `2d3d05d3814cacf7b41dab9f1fd774352b0e7e6a19ca4a2094d3f1c98aa3c3ac` (architecture).
  - `git hash-object --path=…` and `--no-filters` both gave `f3273a154a82dab33fa4b07fcbea52588ac67f0c`,
    `6f46d72c44787fd0ebdd0a7c2a33c0e00cca9f6b` and `1319cce4f673cd4df1ff73925265788cfbcffca1`.
  - Lines and bytes: 888/44950, 262/17775 and 1508/72589.
  - Patch SHA256 `1567e22a445beff49237c0446b1b14ad303a9076a529d62d4879f04b0748346c` (round 1:
    `42326ce3…`); `.gitignore:10` ignores both patch files.

  All values equal the handoff. `git apply -R --check docs/proposals/CORE-005-tests-r2.patch`, run alone at
  20:43:4xZ: exit 0, no output. `git status --porcelain --untracked-files=all` lists exactly
  ` M tests/architecture/test_imports.py`, `?? docs/handoff/CORE-005.md`, `?? docs/reviews/CORE-005-tests-r1.md`,
  `?? tests/acceptance/CORE-005/test_data_bars.py` and `?? tests/golden/CORE-005/bars_cases.py`, and stayed so after
  every run below. `node scripts/controls/check-locked-paths.mjs main` (20:56:31Z) lists exactly the three files as
  locked changes ("FAIL: 3 control change(s) need owner approval", expected until the owner's label). So the only
  locked-path changes are those three files.
- **AST comparison (task item 3).** `ast_compare.py` (20:54:01Z) reads the locked files in place. It builds the
  round-1 texts in memory only, and checks them before use:
  - The round-1 acceptance text, from the new-file lines of `CORE-005-tests.patch` and independently by reversing
    `CORE-005-tests-r2.patch` on the current file: both give blob `5f8e5373…`, SHA256 `0ccd3afe…`.
  - The round-1 architecture text, by reversing round 2 on the current file and independently by applying round 1 to
    `git show HEAD:…`: both give `c1e8220d…`, `85481534…`.
  - HEAD: `ca7a75af…`, `0e1d7a21…`.

  It compares every `assert` and every `with pytest.raises(...)` block (context and body) per top-level definition
  as a multiset of `ast.dump`. It also compares the parametrize tables row by row. Results:
  - **Acceptance, round 1 → current:** 131 checks, of which **127 are identical**. The 4 that changed are exactly the
    author's list: F7 (old line 166 removed), F2 (old line 216 widened), F11 (old line 446, `empty` → `one`) and F8
    (old line 462). `_DEFECT_CASES` has 17 of 19 rows identical, and the other 2 differ only in the key
    `open` → `open_` (F1); 4 rows are added. `_GAP_CASES` has 19 of 19 identical, plus 1 added.
  - Every helper is AST-identical, so the kept asserts keep their meaning: `_api`, `_tb`, `_golden`, `_raw`,
    `_minutes`, `_m1`, `_series`, `_snapshot`, `_defects`, `_expected`, `_check_report`, `_aggregated` and the
    subclass fixtures. The only changed definitions are the docstring, the `datetime` import (adds `timezone`), the
    AC-01 test, the AC-03 empty-input test, the AC-04 calendar test and the two tables. Five tests are new, and the
    definition order is kept.
  - **Architecture, round 1 → current:** 19 of 19 checks identical. The changed definitions are the docstring and the
    AC-06 directory test, whose 3 asserts are identical. Its loop now applies the core checker (the same call as
    round 1) and the snapshot checker plus the float ban (a superset of round 1), and adds `data/__init__.py`. 9
    definitions are new; `_allowed_import`, `_inspect_source`, `_inspect_data_snapshot_source`, `_PURE_CHECKERS` and
    every FIX-001/CORE-001 table are unchanged.
  - **Architecture, HEAD → current:** 14 of 14 pre-existing checks identical. Of the old definitions, only the
    docstring and `_allowed_import` changed (both in round 1, already reviewed).
- **Satisfiability (task item 4).** I wrote my own reference from contract v1.1 and the acceptance docstring
  conventions only. I did not read or reuse the author's or the round-1 reviewer's reference.
  - **Reference.** `…\scratchpad\r2\ref\sochron\core\__init__.py` (a plain `@dataclass(frozen=True, slots=True)`,
    positional allowed, its own timeframe set) and `…\ref\sochron\data\snapshot\__init__.py` (no float; every
    conversion through `timebase`: `to_utc`, `bar_open`, `to_zone`). `…\ref\sochron\data\__init__.py` is a
    docstring only.
  - **Tree.** `git archive HEAD src | tar -x` into `…\r2\tree`, with the reference copied over. Every non-core file
    of the tree's `src` is byte-identical to the repository's (`sha256sum`, 17 files).
  - **Runner.** `run_ref.py`, launched from the repo root as `timeout 600 uv run --offline --no-sync python -I -B
    run_ref.py <tree> <repo> <out.json> <test paths>`. It puts `<tree>\src` at `sys.path[0]` and imports `sochron`,
    `sochron.core`, `sochron.data`, `sochron.data.snapshot` and `sochron.timebase`, checking each origin. It then
    changes the cwd to the tree, so every `Path.cwd() / "src"` in the tests, including the architecture walk, is
    the scratch src. It runs `pytest.main` on the locked files in place, with `--rootdir <repo> -c pyproject.toml
    -p no:cacheprovider`. Afterwards it checks that every `sochron*` entry of `sys.modules` lies under
    `<tree>\src`, or it exits 3.
  - **REF results.** Acceptance + golden + architecture (20:51:26–27Z): **68 passed**, "PROOF OK: 10 sochron
    modules loaded, all under …\trees\REF\src". Whole `tests` (20:52:49–54Z): **849 passed in 4.67s, 0 skipped**,
    "PROOF OK: 20 sochron modules". No test failed that a contract-faithful implementation cannot satisfy.
  - **Mutants and controls.** `build.py` (each text replacement must match exactly once) and `drive.py`, which runs
    the runner with the same interpreter and `-I -B` for each tree (20:51:35–20:52:06Z).

  | Variant | Result (of 68, or of 13 for architecture-only) |
  |---------|--------------------------------------------------|
  | `M1_COUNT_UPPER_BOUND` | 2 failed: v1.1 AC-01, v1.1 AC-02 |
  | `NO_TICK_VOLUME_FLOOR`, `NO_M1_COUNT_FLOOR`, `ACCEPTS_NON_UTC_OFFSET`, `NON_UTC_OFFSET_AS_TYPEERROR` | 1 failed each: v1.1 AC-01 |
  | `NEGATIVE_MAX_GAP_ACCEPTED` | 1 failed: v1.1 AC-03 |
  | `AGG_IGNORES_REPORT_CALENDAR_USES_H001`, `AGG_INCOMPLETE_BY_COUNT_ONLY`, `REPORT_HAS_NO_CALENDAR_FIELD` | 1 failed each: v1.1 AC-04 |
  | `WEEKEND_DAYS_IN_REPORT_AS_PASS` | 5 failed: the 5 weekend rows of AC-04 |
  | `EMPTY_WEEKDAY_HAS_A_TIME` | 2 failed: AC-03 empty_weekday row, AC-05 |
  | `AGG_REFUSES_UNSORTED_INPUT`, `AGG_KEEPS_INPUT_ORDER_IN_SLOT`, `AGG_UNSTABLE_TIE_ORDER`, `AGG_DROPS_DUPLICATE_M1` | 1 failed each: v1.1 AC-02 |
  | `AGG_TIME_UTC_IGNORES_RULE`, `AGG_FLOORS_RAW_SECONDS` | 1 failed each: AC-02 offsets (F4) |
  | `OHLC_SKIPS_OPEN_BELOW_LOW` / `OHLC_SKIPS_OPEN_ABOVE_HIGH` / `NON_POSITIVE_CHECKS_LOW_ONLY` | 2 / 1 / 3 failed: the F5 and F1 rows |
  | `FLOAT_NAME_IN_SNAPSHOT`, `FLOAT_LITERAL_IN_SNAPSHOT`, `SNAPSHOT_OPEN_IN_FUNCTION` | 1 failed each: AC-06 directory test |
  | `CORE_TIME_TIME_IN_FUNCTION` | 2 failed: CORE-001 AC-07 and AC-06 |
  | `DATA_INIT_FROM_DOT_IMPORT_SNAPSHOT`, `DATA_INIT_FROM_DATA_IMPORT_SNAPSHOT`, `DATA_INIT_FROM_DOT_IMPORT_ACQUIRE` (architecture only) | 1 failed each: "line 3: forbidden import sochron.data" |
  | `DATA_INIT_IMPORT_ACQUIRE`, `DATA_INIT_RANDOM`, `DATA_INIT_OPEN`, `DATA_INIT_CLOCK`, `DATA_INIT_BROKER` (architecture only) | 1 failed each: "forbidden import sochron.data.acquire", "forbidden random import", "forbidden clock/I/O call open", "line 5: forbidden clock/I/O call time.time", "forbidden import sochron.broker" |
  | Controls `CONTROL_DATA_INIT_REEXPORT`, `CONTROL_DATA_INIT_IMPORT_AS`, `CONTROL_DATA_INIT_MISSING`, `CONTROL_KW_ONLY_BAR`, `CONTROL_INTENUM_WEEKEND`, `CONTROL_REPORT_LENGTH_CHECKED_FIRST`, `CONTROL_FLOAT_IN_CORE` | 68 passed each |

  Every pytest run printed PROOF OK. One harness error, not a test result: in the first pass, four
  architecture-only plants (`…ACQUIRE` ×2, `…OPEN`, `…BROKER`) exited 1 before pytest, because the runner preloads
  `sochron.data` and those plants break that import. I added an `--arch` mode that preloads only `sochron` and
  `sochron.core` (the architecture tests import no `sochron` code), and reran all eight `DATA_INIT_*` plants
  (20:52:34–40Z). The results are in the table.
- **Red run (task item 5).** `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider`
  from the repo root (20:54:15–20Z) gave **56 failed, 793 passed in 4.59s**, exit 1. The same command with `-rfs`
  (20:54:30–35Z) gave 56 failed, 793 passed, no skip and no collection error. Failure reasons, counted from the
  log:
  - "AC-01: sochron.core.Bar not implemented" ×2, AC-02 ×3, AC-03 ×26, AC-04 ×23, AC-05 ×1 (55 in total).
  - "AC-06: …\src\sochron\data\snapshot does not exist; implementation missing" ×1.

  Every failure is in `tests/acceptance/CORE-005` or the AC-06 directory test, and each is for the contract reason
  (the code is missing). The 4 AC-06 self-tests and all older tests pass.
- **The author's two notes (task item 6).**
  1. **`from . import snapshot` in `data/__init__.py` is flagged. Accept.** Confirmed: it and
     `from sochron.data import snapshot` give "forbidden import sochron.data". A docstring-only file,
     `from .snapshot import aggregate, validate_m1` and `import sochron.data.snapshot as snapshot` pass the whole
     suite.
     - Read literally, AC-06 v1.1 allows `data/__init__.py` "import ได้เฉพาะ core, timebase และ stdlib" (only core,
       timebase and stdlib). So flagging `from . import snapshot` does not ask for more than the contract. Admitting
       the snapshot subpackage is a small, safe relaxation, because the snapshot is checked under its own rules.
     - The asymmetry comes from the shared `_inspect_source`. It judges `from X import Y` by `X`, unless `X` is
       exactly `sochron`. Allowing `X = sochron.data` would also let `from . import acquire` through, and refining
       it would mean changing FIX-001 shared code.
     - An equivalent spelling exists, and the failure names the line. Advice for the implementer: keep
       `data/__init__.py` docstring-only, or use `from .snapshot import …`.
  2. **A missing `data/__init__.py` is allowed. Accept.** The contract lists the file as allowed, not required
     (`:30`). With a namespace package, the acceptance imports work and AC-06 passes (`CONTROL_DATA_INIT_MISSING`,
     68/68). A namespace portion runs no code. Because `sochron` is a regular package, `sochron.data` can only be
     found in `sochron.__path__`, a single directory, so no other path entry can merge into it.
- **Red flags (task item 7).** `bash scripts/controls/red-flags.sh origin/main` (20:54:49–50Z), exit 0:
  - Merge-base `6bd9ef8`. Changed: `A docs/contracts/CORE-005-data-bars.md`, `A docs/contracts/CORE-006-strategy-h001.md`
    and `M tests/architecture/test_imports.py`.
  - Deleted or renamed test files: none.
  - Untracked, so not scanned by the script: the handoff, the round-1 review and the two new test files.
  - **Pattern groups with hits: 0.** Control files touched: `tests/architecture/test_imports.py`.

  I then applied the script's own regexes, unchanged, to the two untracked test files: **0 hits** for skipped or
  focused tests, disabled type checks, disabled lint, swallowed errors, possible secrets, secret-like assignments,
  destructive or bypass commands, client-exposed variables, placeholder or mock, and order or account calls. No
  line in the acceptance or architecture file is wider than 108.
- **Merge with the newer main.** `origin/main` moved to `b7e0dd2` (PR #15, CORE-004) after this branch was cut. It
  changes `src/sochron/costs/charges.py` and `model.py` but not `tests/architecture/test_imports.py`
  (`git diff --quiet 6bd9ef8 origin/main -- tests/architecture/test_imports.py`). The round-2 architecture tests
  pass on `git archive origin/main src` with REF copied over: 13 passed, PROOF OK, 20:55:59Z. Merging main later
  therefore neither conflicts in the locked file nor turns the new costs code red under these checkers.
- **Determinism and scope of the new tests.** No clock, random or set-order dependence. The new tests import only
  stdlib, pytest and contract names, plus `timebase.to_zone` and `bar_open`. No assertion checks message text. The
  F4 rule with offset +600 s is synthetic, and the contract gives no ground for refusing it (handoff limit 4).
  `odd` and `shifted` are built with `dataclasses.replace` on the measured rule, as the round-1 tests already did.

## Not checked (and why)
- CI on Linux: not run. The tests use only stdlib, pytest, zoneinfo and the project's tzdata. The CI count on the
  PR merge ref will include PR #15's tests, so "849" applies to this branch alone.
- Real market data: forbidden before ENV-1.
- Performance (500,000 bars): an implementer unit test under the contract, not acceptance.
- The forward `git apply --check` of round 2: the patch is already applied. The reverse check passed.
- The golden file was not recomputed by hand in this round. It is unchanged since round 1 (blob `6f46d72c…`), where it
  was recomputed with 0 mismatches, and REF reproduces it from independent code.
- `incomplete` for an M1 inside a closure, and slot order for unsorted input across slots: not asserted, and not
  stated by the contract (handoff limits 5 and 6).
- The known shared-checker limits (`logging.warning`, `sqlite3.connect`, dynamic `getattr`) were not re-examined.
  They are FIX-001 follow-ups and apply equally to every pure package.
- Process note: the cross-agent-review procedure says to read the handoff only after a first round of findings.
  This is a re-review round, and the task named the handoff as an input, so I read it at the start. The mutants and
  REF were written from the contract and the test docstring, not from the handoff's reference.
- Scratch evidence, all under
  `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\25327c31-a21a-4dca-9008-1b084da51f80\scratchpad\r2\`:
  - `tools\`: `run_ref.py`, `build.py`, `drive.py`, `ast_compare.py`.
  - `ref\`: the reference.
  - `tree\`: HEAD `src`.
  - `trees\`: REF and 39 variants.
  - `trees-main\MAIN`: `origin/main` src + REF.
  - `results\`: one JSON per variant, plus `table.json` and `table-subset.json`.
  - `evidence\`: `ref-direct.json`, `ref-suite.json`, `drive.log`, `drive-arch.log`, `red-suite.log`,
    `ast-compare.json`, `arch-on-origin-main.json`.

  Nothing was deleted.

Ready to commit red: yes

Findings open: 1
