# Review CORE-005-tests round 1 · base main · head 764cfe4 + applied D-006 patch (uncommitted) · reviewer Claude Code (fresh session 57bd07af, tests reviewer under the role swap)

Scope: the three locked test files that `docs/proposals/CORE-005-tests.patch` adds or changes:
`tests/acceptance/CORE-005/test_data_bars.py`, `tests/golden/CORE-005/bars_cases.py` and
`tests/architecture/test_imports.py`. The test author was a fresh Claude session (handoff `docs/handoff/CORE-005.md`);
the implementer session applied the patch and did not commit it. I reviewed the tests against
`docs/contracts/CORE-005-data-bars.md` v1 (approved 2026-10-23 15:0x with D1–D4), H001 sections 2–3,
`docs/evidence/SPIKE-001.md` and the `sochron.timebase` public API. This is the owner's role swap (contract Status
line, D4): I am neither the test author nor the implementer. No implementation of CORE-005 exists. This file is
the only file I wrote in the repository. Nothing is staged, nothing was pushed, and the locked files were neither
copied nor edited. All times are UTC on 2026-10-23 (02:3x–02:5x +07 on 2026-10-24).

Verdict: **Ready to commit red: no.** F1 (High) makes two AC-03 cases fail for any implementation, so AC-07 can
never go green. A one-line key fix is needed first. Everything else holds:
- the hashes and the red state match the handoff exactly;
- the golden tables are correct (independent recomputation, 0 mismatches);
- the architecture change keeps all 14 old asserts AST-identical;
- a scratch reference written from the contract passes the other 43 acceptance tests and the AC-06 checker.

Recommendation: one new D-006 patch from a fresh test-author session that fixes F1. The same patch should also take
F2, and F3 once the owner has answered open question 5. F4, F5, F7, F8 and F11 are cheap to add in that patch;
every proposed row below was checked against the reference and against the mutant it should catch. F6 corrects
a number in the handoff. F9, F10 and F12 need owner decisions.

Detector note (N6): the post-run locked-path detector fired once, after this session's first hashing command
(19:32:45Z). It listed exactly `uncommitted M tests/architecture/test_imports.py`,
`uncommitted A tests/acceptance/CORE-005/test_data_bars.py` and `uncommitted A tests/golden/CORE-005/bars_cases.py`.
These are the target files of the applied `docs/proposals/` patch and nothing else. The same command had just
produced all six SHA256 and blob values, and all six equal the handoff (below), so I continued as CLAUDE.md
allows. It did not fire again. No hook or deny rule blocked anything.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | High | confirmed | `tests/acceptance/CORE-005/test_data_bars.py:317`, `:323` (helper `:73`, `:87`) | Two `_DEFECT_CASES` rows, "ohlc_inconsistent: open above high" and "open equal to high and close equal to low are inside [low, high]", pass the override key `"open"`. `_series` passes it to `_m1(**overrides)`, but that parameter is named `open_` (`:73`). Against my scratch reference (19:43:51Z) both rows fail with `TypeError: _m1() got an unexpected keyword argument 'open'` before any code under test runs; the other 43 tests pass. The current red run hides the bug, because every test first fails at `_api` ("Bar not implemented"). | Any implementation, including a correct one. | 2 of the 45 acceptance tests can never pass. AC-07 ("ผ่านทั้งหมด skipped 0") is unreachable, and so is the handoff's projected "837 passed" (`docs/handoff/CORE-005.md:57`); the implementer may not edit the locked file. The open > high branch of `ohlc_inconsistent` is also never exercised (see F5). | `{5: {"open_": "4000.400"}}` at `:317` and `{5: {"open_": "4000.300", "close": "3999.900"}}` at `:323`. Alternatively, rename the parameter to `open` in `_m1` (`:73`, `:80`) and keep the positional call at `:233`. | My own script `broken_cases.py` (19:47Z) builds the same ten bars and applies the intended override. It gives `ohlc_inconsistent` STOP at 13:05 and day STOP for the first row, and no defect with day PASS for the second, which equals both expected rows. With the fix, the reference should pass 45 of 45. I did not run that, because the locked file may not be copied or edited. |
| F2 | Medium | confirmed | `test_data_bars.py:216-217` | AC-01 expects `FrozenInstanceError` from `bar.extra = 1`. Probe `probe_frozen_slots.py` on CPython 3.12.15, the project and CI interpreter: `@dataclass(frozen=True, slots=True)` raises `TypeError: super(type, obj): obj must be an instance or subtype of type` for a new attribute, while setting or deleting a field gives `FrozenInstanceError`. `@dataclass(frozen=True)` with a hand-written `__slots__` gives `FrozenInstanceError`. My reference with `slots=True` failed AC-01 at exactly `:217` (19:42:55Z) and passed once switched to a hand-written `__slots__`. | The literal reading of contract `:38` "Bar (frozen dataclass, slots)" on the pinned interpreter. | AC-01 rejects the most direct implementation of the contract's own wording. The implementer has to find a CPython quirk and work around it. AC-01 asks that "`Bar` แก้ค่าหลังสร้างไม่ได้" (cannot be changed after construction), not for a specific exception class when a non-field name is set. | At `:216` only: `with pytest.raises((AttributeError, TypeError)):` (`FrozenInstanceError` is an `AttributeError`). Keep `FrozenInstanceError` for field set and delete, and keep the `__dict__` check at `:218`. | A `slots=True` Bar then passes AC-01; the hand-written-slots Bar still does. |
| F3 | Medium | confirmed | `test_data_bars.py:565-569` (weekend rows `:520-530`); `docs/handoff/CORE-005.md:94-97`, `:123-124`, `:220` | The AC-04 gap test asserts `dict(report.days)` equals exactly the UTC days that hold bars. In the four weekend rows the span contains a Saturday without bars, so the test requires that Saturday to be absent from `report.days`. The handoff says the opposite: convention 4 "the tests do not say whether a Saturday inside a span appears in `days`", open question 5 "Not asserted either way", and line 220 "asserted exactly only where the key set is unambiguous". Variant run (19:44Z): reporting an in-span Saturday as PASS fails exactly these 4 rows and nothing else. | An implementation that reads the contract goal at `:19`, "ทุกวัน (UTC) ได้สถานะ PASS / WARN / UNKNOWN / STOP" ("every UTC day gets a status"), as every day of the span. | A question put to the owner is already decided inside a locked test, and the handoff tells the owner and the implementer that it is still open. | The owner answers question 5. If the answer is "absent": state it in the acceptance docstring's convention list and correct convention 4, question 5 and line 220 of the handoff. If the answer is "either": at `:569`, compare only the days that hold bars, and allow an extra key only for a Saturday or Sunday with status PASS. | With "absent", the test and the handoff agree. With "either", the Saturday variant passes. |
| F4 | Low | confirmed | `test_data_bars.py:222-289`, `:576-618` | Every `aggregate` call uses the measured rule (offset 0). The shifted-rule tests (`:375-397`, `:680-689`) call only `validate_m1`. Variant `AGGREGATE_IGNORES_RULE` (M15 `time_utc` = epoch + raw seconds) fails only the 2 F1 rows (19:44Z), so the tests do not catch it. | `datetime.fromtimestamp(raw, UTC)` or similar inside `aggregate`. | The invariant "ทุกการแปลงเวลาไปผ่าน `timebase`" ("every time conversion goes through `timebase`") and the AC-02 bar open time "(raw และ UTC)" (raw and UTC) are untested for any rule whose offset is not 0. The bug would stay hidden until a second server's rule exists. | In the AC-05 shifted block, after `moved`: `result = aggregate(ahead, 15, shifted, moved)`. Assert one bar with `time_raw == _raw("2026-03-10T00:30")`, `time_utc == datetime(2026, 3, 9, 22, 30, tzinfo=UTC)`, `m1_count == 5` and flags `{"incomplete"}`. (Add `snapshot.aggregate` to the `_api` call.) | `fix_checks.py` (19:50:12Z): the row holds on the reference and fails under the mutant (time_utc 2026-03-10 00:30). |
| F5 | Low | confirmed | `test_data_bars.py:313-329`; `tests/golden/CORE-005/bars_cases.py:155` | `ohlc_inconsistent` is exercised for high < low, close < low (AC-03) and close > high (golden 14:56). Open > high appears only in the F1-broken row, and open < low appears nowhere. `non_positive_price` is exercised only through `low`. Variants `OHLC_SKIPS_OPEN_BELOW_LOW` and `NON_POSITIVE_CHECKS_LOW_ONLY` pass every runnable test (19:44Z). | An implementation that checks `open <= high` but not `open >= low`, or only `low <= 0`. | Part of contract `:60` goes untested: "open/close นอก [low, high]" (open or close outside [low, high]) and "ราคาไม่เป็นบวก" (non-positive price). For a consistent bar, `low <= 0` covers the rest. An inconsistent bar with `high` 0 would lose its `non_positive_price` defect. | Two `_DEFECT_CASES` rows: "open below low", `{5: {"open_": "3999.800"}}` → `(("ohlc_inconsistent", "STOP", _MIDDLE),)`, `_STOP`; and "high is zero", `{5: {"high": "0"}}` → `ohlc_inconsistent` and `non_positive_price`, both STOP at `_MIDDLE`, `_STOP`. | `fix_checks.py` (19:50:12Z): the reference gives exactly these defects; the first row catches `OHLC_SKIPS_OPEN_BELOW_LOW` and the second catches `NON_POSITIVE_CHECKS_LOW_ONLY`. |
| F6 | Low | confirmed | `docs/handoff/CORE-005.md:88-90` | The handoff tells the owner: "63–65-minute breaks pass, 66-minute and longer breaks are WARN under D3 = 5". SPIKE-001 measures breaks open-to-open from the 16:57 New York bar (`SPIKE-001.md:102`). A break of G minutes then leaves 2 + (G − 63) = G − 61 in-session missing minutes, so 66 minutes leaves 5, which is not a defect. The locked row at `test_data_bars.py:514-516` (20:57 → 22:03 UTC, a 66-minute break) expects no defect. `typical_day.py` (19:48:16Z): 63, 64, 65 and 66 minutes give no defect; 67, 68 and 79 give `unexpected_gap`. | The owner reads convention 2 to decide question 7. | The owner-facing number is off by one. No test is affected. | "63–66-minute breaks pass; 67-minute and longer breaks are WARN". Also "first bar 18:00–18:05 NY" for 63–68 minutes. | The text then matches `:514-519` and the simulation. |
| F7 | Low | confirmed | `test_data_bars.py:166` | `assert Bar(*(valid[name] for name in _FIELDS)) == bar` requires positional construction. Variant `kw_only` (`@dataclass(frozen=True, kw_only=True)` with the same slots) fails AC-01 only on this line (19:44Z). The contract lists the fields; it does not ask for positional construction. | An implementer who makes the ten-field type keyword-only, so that open, high, low and close cannot be mixed up by position. | Rejects a safer design that the contract allows. | Delete `:166`. Field order and keyword construction are already asserted at `:159-164`. | The kw_only variant then passes AC-01. |
| F8 | Low | confirmed | `test_data_bars.py:462` | `type(start_day) is int and type(end_day) is int` rejects `calendar.FRIDAY` and `calendar.SUNDAY`. On 3.12 these are members of the `calendar.Day` IntEnum and equal 4 and 6 (probe, 19:43Z). Variant `intenum_weekend` fails only this test. The contract (`:52`) types the field as `(weekday, time)` without naming a type. Convention 7 fixes the numbering, and `:463-464` already assert it. | `H001_CLOSURES` written with the stdlib weekday names. | An over-constraint on the type of a constant. | Delete `:462`, or require `isinstance(x, int) and not isinstance(x, bool)`. | The variant then passes. |
| F9 | Low | question | `test_data_bars.py:118` (also `:11-12`, `:339`, `:647`) | `_check_report` ties `time_raw is None` to `empty_weekday` in both directions. Contract invariant `:68` says "ข้อมูลเสียทุกแบบมีรหัสและเวลาใน report" (every kind of bad data has a code and a time in the report), and AC-03 asks for "เวลาที่ถูกต้องของความผิดปกตินั้น" (the correct time of that anomaly). `Defect.time_raw` is `int \| None` (`:51`). Variant `EMPTY_WEEKDAY_TIME_IS_DAY_START` (time_raw = raw of 00:00 UTC of the empty day) fails the AC-03 empty_weekday row and AC-05 (19:44Z). | An implementer who gives the empty day a time, as the invariant suggests. | With `None`, the defect itself does not say which day is empty; only `detail` or `report.days` does. | The owner confirms convention 4. If a time is preferred, expect `to_raw(00:00 UTC of that day, rule)` (or accept either), and keep `None` illegal for every other code. | – |
| F10 | Low | question | `tests/architecture/test_imports.py:619-638` (walk at `:622-626`) | The AC-06 walk covers `src/sochron/core` and `src/sochron/data/snapshot` only. `src/sochron/data/__init__.py` is an allowed file (contract `:30`) and runs on every `import sochron.data.snapshot`. `ac06_mutations.py` (19:45:06Z) appended `import random` plus `SEED = open("x").read()`, and separately `from . import acquire`, to that file: the AC-06 test still passes. AC-06 names only the two packages, so this is a question. | The data package `__init__` imports `acquire` or does I/O at import. | The research host could reach `data.acquire` through `sochron.data` without AC-06 noticing. Architecture section 6.1: the research host must have no `data.acquire`. | Also inspect `src/sochron/data/__init__.py` with `_inspect_data_snapshot_source(source, "sochron.data.snapshot", "sochron.data")`. `fix_checks.py` (19:50:12Z) shows what that rule does: a docstring-only file and `from .snapshot import …` pass; `from . import acquire`, `import random` and `open(...)` are reported. `from . import snapshot` is also reported, so the file stays import-free apart from `from .snapshot import …`. | Both mutations are then reported. |
| F11 | Low | question | `test_data_bars.py:441-447` | `aggregate([element], 15, rule, empty)` pairs a one-element list with the report of `[]` (`m1_bars` 0). Variant `REPORT_COUNT_CHECK_FIRST` fails this test: aggregate raises `ValueError` when `report.m1_bars != len(bars)`, and it checks this before the element types (19:44Z). The contract does not say whether type checks or consistency checks come first. | An implementer who checks the report against the bars first. | Pins a check order that the contract does not state. | Use a report of matching length: `aggregate([element], 15, rule, validate_m1(bars[:1], rule, H001_CLOSURES, 5))`. | The variant then passes. |
| F12 | Low | question | contract `:56`, `:64`; `test_data_bars.py:15-16`; handoff convention 9 (`:107-108`) | `aggregate(bars, timeframe, rule, report)` receives no calendar, yet its flag rule needs one: "`incomplete` ถ้า `m1_count < timeframe` และช่องที่ขาดไม่อยู่ในช่วงปิดตามปฏิทิน" (`incomplete` when `m1_count < timeframe` and the missing minutes are not in a calendar closure). `ValidationReport` has no calendar field either. The tests avoid the clause on purpose (convention 9: no M1 inside a closure), so variant `INCOMPLETE_IGNORES_CLOSURES` passes everything. My reference needed an extra `calendar` field on `ValidationReport`, with `compare=False`. | Implementation choice: a hidden field, an H001 default, or ignoring closures. | The clause is untested, and the three choices look the same to the tests. With H001 and M15 they disagree only for an M1 inside a closure. | Owner or contract decision. Either carry the calendar (a `ValidationReport` field, or an `aggregate` argument), or state that `incomplete` = `m1_count < timeframe` whenever the calendar's boundaries fall on the slot boundaries. Then add one row with an M1 inside a closure. Example: a single M1 at 21:30 UTC on an EDT weekday is not `incomplete` under the first option. | – |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status
Coverage per AC. "FAIL (red, as intended)" is the expected state before implementation. The gaps refer to the
findings above.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | FAIL (red, as intended) | `test_ac01_…` fails with "AC-01: sochron.core.Bar not implemented". Coverage: a frozen slots dataclass with the ten fields in contract order; exact read-back types; spread None; every `TIMEFRAMES_MINUTES` value; zero volume; an exponent-form Decimal; inconsistent, zero or negative prices and a negative spread all construct. Per field it rejects float, bool, str, a str subclass, cross types, int/Decimal/datetime subclasses, `date` and None with `TypeError`; a naive `time_utc` with `TypeError` or `ValueError`; NaN, sNaN and ±Infinity with `ValueError`; timeframes 0, 7, 13, 25, −15 and 1441 with `ValueError`; plus immutability and no `__dict__`. Every clause has a test. Gaps: F2, F7. Note: `core` may not import `timebase` (module map `core` row "–", and the CORE-001 AC-07 test already enforces it), so `Bar` must hold its own copy of the timeframe set. AC-01 catches a missing member but not an extra one, such as 45. A unit test comparing the two sets would close that. |
| AC-02 | FAIL (red, as intended) | Same failure (AC-02). Coverage: 148 golden M1 rows → 11 M15 rows with exact OHLC (Decimal), last-M1 spread (254, None, −3), volume sum, `m1_count`, raw and UTC open, `timeframe == 15` and exact flags (`incomplete` at 13:30 and 15:00). The empty 14:15 slot is not produced. The counts sum to 148, the input is untouched, repeat and tuple input give the same result, and the result types are frozen. Discrimination: the D1 alternatives max, median and first spread fail (variant `SPREAD_IS_MAX` fails AC-02); `close = max(close)` fails on 14:56; high and low peaks sit first, last and in the middle. One weak spot: opens rise within every slot, so `open = min(opens)` would pass. That bug is implausible, so no finding. Gap: F4. |
| AC-03 | FAIL (red, as intended) | Same failure (AC-03, 21 tests). Coverage: every minimum code with its severity and `time_raw`; the exact defect multiset and day map; the input untouched before and after; `m1_bars == len`; two defects on one bar; defects on different bars; a single bar; empty input; `time_rule_mismatch` judged under the validating rule; the argument-type matrix for both functions. Gaps: F1 (two rows can never pass), F5, F9, F11. |
| AC-04 | FAIL (red, as intended) | Same failure (AC-04, 21 tests). Coverage: (ก) the daily break on EST, first-EDT, EDT and first-EST weekdays; the old UTC break hours after each change are flagged; break + 5 passes and break + 6 is flagged. (ข) Weekends around both changes plus an ordinary one; weekend + 6 is flagged. (ค) exactly `max_gap_minutes`; (ง) one minute more; also `max_gap_minutes` 2 and 0, and UTC midnight. The `H001_CLOSURES` values are checked, and the calendar argument is used (zone and times). M15 flags around the closures and gaps are checked. I recomputed all 15 New York facts with zoneinfo. Gaps: F3, F8, F12. |
| AC-05 | FAIL (red, as intended) | Same failure (AC-05). Coverage: a Mon–Fri week with Wednesday absent gives PASS, WARN, UNKNOWN, STOP (STOP beats WARN) and WARN (two WARNs); a read-only `days`; a frozen report; two STOP codes plus a WARN on one day; UTC day keys under a rule 2 h ahead. STOP > UNKNOWN and UNKNOWN > WARN cannot be reached with the minimum codes (open question 6). |
| AC-06 | FAIL (red, as intended) | `test_ac06_core_and_data_snapshot_…` fails loudly with "AC-06: …\src\sochron\data\snapshot does not exist; implementation missing"; both self-tests pass. On my scratch tree the compliant reference passes. The open, `Path.read_bytes`, `time.time`, random, `data.acquire`, broker, `MetaTrader5`, socket and core→timebase mutations are all reported. This matches the verification row's "ใส่ `open(...)`/`time.time()` … ต้องถูกจับ" (insert `open(...)`/`time.time()` … must be caught). Gap: F10. |
| AC-07 | FAIL (red, as intended) | Whole suite: 46 failed, 791 passed, 0 skipped, as the handoff projects. It cannot reach green until F1 is fixed. |

Clauses no test checks, or that a wrong implementation passes:
- `ohlc_inconsistent` for open > high (F1) and open < low (F5).
- `non_positive_price` on open, high or close (F5).
- `aggregate` under a non-zero offset (F4).
- The calendar exception in the `incomplete` rule (F12).
- `src/sochron/data/__init__.py` under AC-06 (F10).
- The UNKNOWN > WARN and STOP > UNKNOWN steps (Q6; unreachable by design).

## Conventions the test author fixed (handoff "Conventions the contract leaves open")
1. Gap length = missing minutes. **Accept.** It matches D3's "ช่องว่าง 1–5 นาที" (gaps of 1–5 minutes) and the
   negative case "ตรงขอบ `max_gap_minutes` พอดี (ไม่ใช่ defect)" (exactly at `max_gap_minutes`: not a defect).
   The open-to-open variant fails 6 rows, as designed.
2. Closure minutes are subtracted. **Accept** as the most literal reading of contract `:60`. F6 corrects the
   handoff's numbers; see Q7 for what this means on real data.
3. `unexpected_gap.time_raw` = the first bar after the gap. **Accept.** It is consistent with the flag rule
   "รหัส defect ของ M1 ในแท่ง" (the defect codes of the M1 bars in the slot). Under H001 alignment, the slot
   before the gap still gets `incomplete` (`:613-616`, golden 13:30), so no information is lost.
4. `empty_weekday` = None, and days strictly inside the span. **Span rule accepted.** The None part is F9, and the
   day-map claim is F3.
5. Equal time → `duplicate_time` only. **Accept.**
6. One defect per (bar, code). **Accept.** The contract defines one code per kind of anomaly. A variant that
   emits one defect per violated sub-rule fails, as designed.
7. Weekday numbering follows `date.weekday()`. **Accept** the numbering; the type assertion is F8.
8. The type-error table. **Accept**, apart from F2 (the exception for a non-field attribute) and F11 (check
   order).
9. `incomplete` is asserted only with H001. **Accept** for the tests; the contract gap is F12.
10. The AC-06 checker. **Accept.** The new random ban on `core` matches AC-06 ("…สุ่ม", randomness, for both
    packages). The core→timebase ban is not new: it is the CORE-001 rule. Gap: F10.

## Reviewer's view on the author's eight open questions (the owner decides)
1. **`Bar` range checks.** Recommend `ValueError` for `tick_volume < 0` and for `m1_count` outside `1..timeframe`.
   Neither can come from broker data, only from a bug, and today a negative volume has no defect code, so it
   would pass silently (invariant `:68`). Leave the raw range to `timebase`: `to_utc` already refuses it in both
   functions. This is a contract amendment with tests.
2. **Aware non-UTC `time_utc`.** Recommend refusing it at construction with `ValueError`. The field promises
   "aware UTC", and a Bangkok-zoned value would make `time_utc.date()` wrong for consumers. My reference does
   this; no test pins it.
3. **`max_gap_minutes < 0`.** Recommend `ValueError`.
4. **Unsorted or duplicate input to `aggregate`.** Recommend no refusal. Group by `bar_open`, order members by
   `time_raw` (stable), and rely on the report: the STOP codes already make H001 skip that day. An optional test
   could pin it later.
5. **Saturday inside a span.** The tests already require it to be absent (F3). Recommend absent: a day with no
   bars and no expected session has no status. Write it down either way.
6. Agree. Under convention 3 the precedence steps that involve UNKNOWN cannot be reached with the minimum codes.
   The implementer's unit tests can cover the status function directly.
7. **Real-data effect (D2 + conventions 1–3).** On the SPIKE-001 shape, `typical_day.py` (19:48:16Z) gives:
   - **The 16:45 New York M15 slot is `incomplete` on every trading day.** The last bar opens at 16:57
     (`SPIKE-001.md:64`, `:74`; quotes end 20:58 UTC in EDT), and 16:58–16:59 count as in session under D2's
     17:00 break.
   - The 18:00 slot is also `incomplete` whenever the first bar comes after 18:00.
   - Breaks of 67 minutes or more give `unexpected_gap` (WARN). SPIKE-001 saw 68 minutes on 5 Mar and 79 on
     1 Apr, and the 27→29 Mar weekend (22:04 reopen) leaves 6 in-session minutes.

   If CORE-006 treats any flag in the 96-bar lookback as "ข้อมูลแท่งใดใน lookback ขาดหาย" (a bar in the lookback
   is missing; H001 Invalidation), every lookback contains a 16:45 slot and H001 never enters. Decide before
   CORE-006 or R1. Options: start the D2 break at 16:58 New York, or define which flags invalidate an entry
   (for example `unexpected_gap` and STOP days, but not an `incomplete` slot next to a closure). Neither changes
   these tests.
8. **Banning `float` in snapshot.** Recommend yes, as in costs and risk. Prices are Decimal by contract, and the
   check is cheap. It needs an AC-06 amendment; today `float("1.5")` in snapshot passes AC-06 (`ac06_mutations.py`).
   The risk is low either way, because `Bar` refuses float prices.

## Checked, nothing found (and how)
- **Working tree and hashes (task item 1).** Branch `feat/CORE-005-data-bars`, HEAD
  `764cfe4b0fb7e20cf82bd5d0254330bf70929b95`; `main` and `origin/main` are both `6bd9ef8`.
  `git status --porcelain --untracked-files=all` lists exactly ` M tests/architecture/test_imports.py`,
  `?? docs/handoff/CORE-005.md`, `?? tests/acceptance/CORE-005/test_data_bars.py` and
  `?? tests/golden/CORE-005/bars_cases.py`, and was unchanged after every run below. At 19:32:45Z:
  - `sha256sum` gave `0ccd3afef0330b7276da1426613b3c5457131f4ea3919816de45b5ef060868df`,
    `f44acafed99317a0e117c20b2d12e12c0584d0515d790a01f35dc1dd0586dd59` and
    `854815344dcf0450aa7c9feaceb4f19c178009e4661bb4d155853477d627f305`.
  - `git hash-object --path=…` and `--no-filters` both gave `5f8e537394a89739853bf88ca94fb2208f8f8554`,
    `6f46d72c44787fd0ebdd0a7c2a33c0e00cca9f6b` and `c1e8220d68c5b1f67d3c7a5fe7ae6e08a0a40707`.
  - Lines and bytes: 689/33443, 262/17775 and 1387/65618.
  - Patch SHA256 `42326ce3e842cc15a24177413de5007c908cbb65221726f0b9ba98ebef0e014e`.

  All values equal the handoff table. `git apply -R --check docs/proposals/CORE-005-tests.patch`, run alone at
  19:32:59Z: exit 0, no output. `node scripts/controls/check-locked-paths.mjs main` (19:46:03Z) lists exactly the
  three files as locked changes ("FAIL: 3 control change(s) need owner approval", expected until the owner's label).
  The other changed paths are the two contracts (committed) and the handoff, which is not locked.
- **Golden correctness (task item 3).** `golden_recompute.py` (19:40:10Z) reads the golden file as data, through
  `ast.literal_eval` (never imported), and recomputes from the contract rules:
  - It regenerated all 148 M1 rows from the docstring formula. The only difference is the documented 14:56 close
    (4007.210 instead of 4007.115).
  - All 11 M15 rows agree (first open, max high, min low, last close, last spread, volume sum, count, flags).
  - The 6 defects, the STOP day, the absent 14:15 slot and the anchor 1773147600 agree.
  - 15 New York DST facts agree with zoneinfo and the project's tzdata: the EST and EDT breaks on 2026-03-05,
    03-09, 10-29 and 11-02; both weekend edges around 2026-03-08 and 2026-11-01; the ordinary weekend; the AC-05
    18:30 case.

  Result: 0 mismatches. By hand I also checked the 13:30 volume (120 − 4 − 5 − 6 = 105), the 15:00 single-bar
  slot and every DST row's in-session minute count in `_GAP_CASES`. The reference passes all 19 gap rows.
- **Architecture change (task item 4).** I saved `git show HEAD:tests/architecture/test_imports.py` to scratch
  (blob `ca7a75af…`, SHA256 `0e1d7a21…`, both equal the handoff's base). `ast_compare.py` (19:39:30Z):
  - **14 of 14** HEAD asserts are present with an identical `ast.dump` in the same definition. The new file has
    19 asserts; the 5 new ones are in the three AC-06 tests.
  - 30 of 31 named top-level definitions or assignments are identical, and their order is preserved.
  - The only change is in `_allowed_import`: one new `sochron.data.snapshot` → `sochron.timebase` branch, with
    the HEAD statements kept in order. The module docstring is extended; the other 5 module statements are
    unchanged.
  - `_PURE_CHECKERS` is not extended, so the FIX-001 asserts keep their meaning.

  The snapshot self-tests compare `_SNAPSHOT_FORBIDDEN_IMPORTS` as exact lists. The relative-import allowance in
  the second self-test still requires a `forbidden import` finding on the same line, so it cannot hide a lost rule.
- **Red run (task item 5).** `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider`
  from the repo root (19:38:46–19:38:50Z) gave **46 failed, 791 passed in 3.96s**, exit 1, 0 skipped, no
  collection error. Failure reasons, counted: "AC-01: sochron.core.Bar not implemented" ×1, AC-02 ×1, AC-03 ×21,
  AC-04 ×21, AC-05 ×1 (45 in total). The architecture failure is the missing `src\sochron\data\snapshot`.
  `pytest tests/architecture` gives **1 failed, 10 passed in 0.27s**: the 8 existing tests and the 2 new
  self-tests pass. 0 tests are collected from the golden directory. Each failure is for the contract reason.
- **Satisfiability (task item 6).** I wrote a reference from the contract only:
  `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\57bd07af-712b-403d-8418-9feb93c204b6\scratchpad\review\ref\sochron\core\__init__.py`
  and `…\scratchpad\review\ref\sochron\data\snapshot\__init__.py`. It is review evidence only; do not copy it as
  the implementation.
  - `run_ref.py` puts the scratch packages first on `sochron.__path__`. `sochron.timebase` stays the repository's,
    which the script asserts. The script runs `pytest.main` on the two new directories from the repo root under
    `uv run --offline --no-sync python -I -B` and `timeout`.
  - Result (19:43:51Z): **43 passed, 2 failed**. The 2 failures are F1. A `slots=True` Bar also fails AC-01 (F2).
  - 13 variants were run (19:44:07Z). They are listed in F2–F12, and the conventions section lists the ones that
    fail by design.
  - AC-06 (`ac06_mutations.py`, 19:45:06Z) runs the locked directory test function on a src-shaped copy of my
    own reference, from that scratch directory. Compliant → PASS. All the mutations listed under AC-06 → reported.
  - The only test that a contract-faithful implementation cannot satisfy is the pair in F1. AC-01 can be
    satisfied only with a hand-written `__slots__` (F2).
- **Red flags (task item 7).** `bash scripts/controls/red-flags.sh origin/main` (19:45:28Z), exit 0:
  - Changed since merge-base `6bd9ef8`: `A docs/contracts/CORE-005-data-bars.md`,
    `A docs/contracts/CORE-006-strategy-h001.md` and `M tests/architecture/test_imports.py`.
  - Deleted or renamed test files: none.
  - Untracked, so not scanned by the script: the handoff and the two new test files.
  - **Pattern groups with hits: 0.** Control files touched: `tests/architecture/test_imports.py`.

  I then applied the script's own patterns to the two untracked test files with Grep, after checking that the
  path matched them: **0 hits** for skip/only/xfail, type-ignore, noqa/lint, swallowed errors, secrets,
  secret-like assignments, destructive or bypass commands, client-exposed variables, placeholder or mock, and
  order or account calls.
- **Determinism and over-constraints.** No clock, random or set-order dependence. `_snapshot` uses `id()` only
  within one call, `_defects` sorts with a None-safe key, and flags compare as frozensets. No assertion checks
  message text: `detail` is only `type(...) is str`. The tests import only stdlib, pytest and `sochron` names
  from the contract and the merged timebase. The paths rely on running from the repo root, as for every locked
  test.
- **Known, not new.** The `logging.warning(...)` and `sqlite3.connect(...)` mutations in snapshot also pass AC-06
  (`ac06_mutations.py`). These are limits of the shared FIX-001 checker, already recorded as follow-up candidates
  (`docs/handoff/FIX-001.md:203`, `:232`, `:646`). They apply equally to timebase, core, costs and risk, so I
  raised no finding here.

## Not checked (and why)
- I did not run the proposed fixes inside the test file: locked files may not be copied or edited. Instead, the
  rows of F1, F4, F5 and F10 were checked with my own scripts against the reference and its mutants
  (`broken_cases.py`, `fix_checks.py`). F2, F7, F8 and F11 follow from the variant runs.
- CI on Linux: not run. The tests use only stdlib, pytest, zoneinfo and the project's tzdata. The CPython quirk
  in F2 does not depend on the platform, but I did not verify that on Linux.
- Real market data: forbidden before ENV-1. The Q7 numbers are a synthetic simulation of the SPIKE-001 summaries,
  not measurements.
- Performance (500,000 bars): an implementer unit test under the contract, not acceptance.
- The forward `git apply --check`: the patch is already applied. The reverse check passed.
- Scratch evidence, all under
  `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\57bd07af-712b-403d-8418-9feb93c204b6\scratchpad\review\`:
  `tools\` (`ast_compare.py`, `golden_recompute.py`, `run_ref.py`, `probe_frozen_slots.py`, `ac06_mutations.py`,
  `broken_cases.py`, `typical_day.py`, `fix_checks.py`), `ref\` (the reference), `refroot\src\` (a copy of my
  reference used for AC-06) and `head\test_imports_head.py`. Nothing was deleted.

Ready to commit red: no

Findings open: 12
