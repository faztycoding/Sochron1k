# Review CORE-007 tests round 1 · base main (origin/main 6fbed53, tree = b7256cd) · head a7a0a0f + D-006 patch `da45cb55…` applied, uncommitted · reviewer Claude Code, fresh headless session (tests reviewer under the D7 role swap)

Scope: the three locked files of `docs/proposals/CORE-007-tests.patch` against
`docs/contracts/CORE-007-backtest.md` v1.4 and H001 sections 3, 6, 7, 8. Read-only except this file.
The first list of findings (F1–F5) was written to the session scratchpad before
`docs/handoff/CORE-007.md` was opened; F6, F7 and the mutant evidence for F4 came after, from my own
probes (not from the handoff). The handoff changed none of F1–F5.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | tests/golden/CORE-007/backtest_cases.py:44; tests/acceptance/CORE-007/test_backtest.py:143, :964 | Every call builds its Rollover from the one golden `ROLLOVER` (America/New_York 17:00) and uses a model with `triple_swap_weekday` 2 (the stress test's second model keeps 2). Mutants of my reference `rollover_hardcoded`, `triple_hardcoded`, `weekday_utc` each pass 86/86 | An implementation that ignores `rollover`, ignores `model.triple_swap_weekday`, or takes Mon–Fri/triple from the UTC weekday of T | Contract "nights (D4 [A])" untested on its two inputs. Both are [A] values R1 is to correct (H001 s.6: triple day UNKNOWN, Wednesday assumed; D4 rollover until broker evidence). After a correction such code keeps charging NY 17:00 / Wednesday swap silently; long swap (50.38 USD/lot/night) is the largest cost of multi-night longs and moves expectancy in R | Two simulate_trade cases, values in "Finding details" F1 (a) Asia/Tokyo 06:00 with triple Monday, (b) New York 23:00 | (a) gives (1,1) / net −8.114 on the reference and (1,0) / net 1.962 on all three mutants; (b) gives (0,0) on the reference and (1,0) on `rollover_hardcoded` |
| F2 | Low | confirmed | tests/acceptance/CORE-007/test_backtest.py:195; tests/golden/CORE-007/backtest_cases.py:452 | `_m15` asserts every fixture M15 bar is complete and `run_m1_rows` fills all 15 minutes, so the first M1 of every bar opens at the bar's own time and the first M1 at m15[0]'s time. Mutants `entry_by_bar_time` and `equity_from_m15` pass 86/86 | R1 data with a bar whose first minute is missing (aggregate keeps the slot time as time_raw) | Contract "open ของ M1 แรกของแท่ง M15 ถัดไป" and equity point "(time_raw ของ M1 แรก, …)" not distinguished from the M15 open. Likely failure is loud (KeyError), so Low | One run scenario (values in details): R cut after bar 103 with minute 0 of bars 0 and 101 removed | `entry_by_bar_time` raises KeyError; `equity_from_m15` gives (11:00, 10000) instead of (11:01, 10000) |
| F3 | Low | confirmed | tests/architecture/test_imports.py:1829 | `_BACKTEST_STDLIB` admits 12 modules; any other stdlib import is a finding. Contract Invariants allow "stdlib ที่ไม่ใช่ side effect"; AC-06 names only forbidden categories. My faithful reference plus one line `from __future__ import annotations` (or `import math`) fails AC-06: "line 1: forbidden stdlib import __future__" (85 others pass) | A correct implementation using an unlisted side-effect-free module (`__future__`, math, heapq, abc, contextlib, fractions) | Over-constraint: a contract-faithful implementation fails a locked test (handoff open question 8) | Recommended: contract v1.5 states the explicit list for backtest (as CORE-006 tests r2 F4 did for strategy); no test change. Alternative: tests r2 widens the check | The contract line exists, or the two scratch variants pass AC-06 |
| F4 | Low | confirmed | tests/golden/CORE-007/backtest_cases.py:182–193, :228, :305–317 | AC-02 asks "spread None ทุกตำแหน่ง". No case has spread None on the exit_index M1 of an exit beyond the stop, and the only entry-M1-that-stops case with None is long (whose SL check never uses s). Every short ambiguous case has spread 200 at entry and exit. Mutants `ambiguous_entry_spread`, `ambiguous_none_zero` pass 86/86 | A short whose exit M1 has no spread (or a spread other than the entry's) and opens near the stop | The exit is reported "signal", ambiguous False: the H001 "worse case" stop label and the exit spread are lost in R1 | Two fill cases (values in details) | Both mutants give "signal", ambiguous False on case (a) |
| F5 | Low | confirmed | tests/acceptance/CORE-007/test_backtest.py:139, :156 | Every trade fixture uses the offset-0 rule, so time_raw equals UTC seconds. Mutant `nights_from_raw` (nights from time_raw read as UTC) passes 86/86 | Any measured rule with offset ≠ 0 | Contract: nights use the `time_utc` of the entry and exit M1. Only offset 0 exists today, so Low | One simulate_trade case on M1 with time_raw = UTC + 3600 (values in details) | Reference (0,0) net 7.00; mutant (1,1) net −8.114 |
| F6 | Low | confirmed | tests/architecture/test_imports.py:1828, :1838 | `_granted_to_backtest` drops every finding under `sochron.timebase`, submodules included; the zoneinfo check looks only at imports of the zoneinfo module. A reference variant with `from sochron.timebase.convert import ZoneInfo` and `datetime.combine(day, at, tzinfo=ZoneInfo(zone))` passes AC-06 | An implementer who needs wall time → UTC for the nights rule (timebase offers only to_zone, to_utc, bar_open) and takes ZoneInfo from timebase internals | Contract "เวลา (r3 F38)"/AC-06 "แปลงเวลาผ่าน timebase เท่านั้น … ไม่ import zoneinfo" not enforced on this route | Add a `_BACKTEST_FORBIDDEN` row for that import with an exact finding; report any imported or referenced name `ZoneInfo`. Question for the contract in details | The probe variant fails AC-06 |
| F7 | Low | confirmed | tests/acceptance/CORE-007/test_backtest.py:794–796; tests/golden/CORE-007/backtest_cases.py:607–626 | (1) Step 4: an `enter_*` outside `sides` is "none (ไม่มี Skip)" also when equity ≤ 0; R_exhausted/R_negative use both sides; mutant `equity_before_sides` passes 86/86. (2) simulate_trade `data_flags: frozenset[str]`: only the container is tested; mutant `flags_elements_unchecked` passes 86/86 | sides {"long"} with exhausted equity; `data_flags=frozenset({1})` | (1) Spurious equity_exhausted Skips in the long-only baseline (H001 s.7); (2) a non-str flag reaches Trade.data_flags | (1) R_exhausted with sides ("long",) (values in details); (2) one more TypeError case | `equity_before_sides` adds a 13:15 Skip; the TypeError case fails the second mutant |

## Finding details (hand values, each also produced by my contract-only reference)

Every case below uses H001_COSTS unless stated, lots 0.10, risk_money 25, the AC-04 M1 rows
`NIGHTS_ENTRY` (4000.00, 4000.50, 3999.50, 4000.20, spread 200) and `NIGHTS_EXIT` (4001.00, 4001.20,
4000.80, 4001.10, 200), stop_distance 50.00, exit_index 1, so gross 10.00, spread 2.00, slippage
1.00, and one long night costs 5.038.

- **F1 (a)** `Rollover("Asia/Tokyo", time(6, 0))`, model `replace(H001_COSTS, triple_swap_weekday=0)`,
  long, entry 2026-03-13T14:00Z (Fri 23:00 JST), exit 2026-03-16T14:00Z (Mon 23:00 JST). Candidates:
  Fri 13 06:00 JST = Thu 21:00Z (before entry); Sat and Sun are not Mon–Fri in Tokyo; Mon 16 06:00
  JST = Sun 15 21:00Z counts and is a Monday; Tue 06:00 JST = Mon 21:00Z is after the exit. Nights
  (1, 1), multiplier 3, swap 15.114, total 18.114, net −8.114, r −0.32456. NY 17:00 hard-coded,
  Wednesday hard-coded and a UTC weekday all give (1, 0), net 1.962, r 0.07848.
- **F1 (b)** `Rollover("America/New_York", time(23, 0))`, long, entry 2026-03-17T14:00Z, exit
  2026-03-18T02:30Z (Tue 22:30 EDT): Tue 23:00 EDT = Wed 03:00Z is after the exit. Nights (0, 0),
  total 3.00, net 7.00, r 0.28. NY 17:00 hard-coded gives (1, 0).
- **F2** Scenario R with bars 0..103 (as `R_to_103`) but without the M1 at 2026-03-09T11:00 (minute 0
  of bar 0) and 2026-03-10T12:15 (minute 0 of bar 101). `aggregate` flags bars 0 and 101
  "incomplete" (decide ignores it), and the OHLC of both bars is unchanged (minutes 0–6 equal O).
  Expected: one trade, long, entry 12:16 at 4002.00 with spread 240, stop_price 3995.94, exit 12:45
  at 3998.60 "signal", costs (0.72, 0, 0.30, 0, 1.02), gross −10.20, net −11.22, r −0.4488,
  actual_risk 18.90, data_flags {"incomplete"}; no Skip; equity ((11:01, 10000), (12:45, 9988.78));
  sizer calls ((10000, 6.30),). `_m15`'s completeness assertion needs an opt-out for this case.
- **F4 (a)** short, entry row `_ENTRY`, M1 14:01 (4000.20, 4003.00, 4000.10, 4002.50, 200), M1
  14:02 (4004.78, 4005.00, 4004.60, 4004.90, spread None), exit_index 2, stop_distance 5.00: stop
  4005.00, ask at the exit open 4004.78 + 0.240 = 4005.02 ≥ stop, so "stop", ambiguous True, exit
  4004.78, exit_spread_points 240, gross −47.80, costs (2.40, 0, 1.00, 0, 3.40), net −51.20,
  r −2.048. With the entry's 200 or with 0 the open is 4004.98 / 4004.78 < stop: "signal".
- **F4 (b)** short, entry M1 14:00 (4000.00, 4000.00, 3999.40, 3999.50, spread None), M1 14:01
  (3999.50, 3999.60, 3999.00, 3999.20, 200), stop_distance 0.22, no exit_index: stop_price 4000.22,
  ask at the entry open 4000.24 ≥ stop, gap at the entry M1: exit 4000.00 at 14:00, entry and exit
  spread 240, gross 0, costs (2.40, 0, 1.00, 0, 3.40), net −3.40, r −0.136.
- **F5** A synthetic `TimeRule` with offset_seconds 3600 is not needed by simulate_trade: build the
  two NIGHTS M1 with time_raw = UTC seconds + 3600 and the correct time_utc, entry
  2026-03-17T21:01Z, exit 2026-03-18T20:59Z, long: nights (0, 0), total 3.00, net 7.00, r 0.28.
  Reading time_raw as UTC gives (1, 1), net −8.114.
- **F6 question for the contract:** the nights rule needs T = rollover.at in rollover.zone as an
  instant, and `timebase` (must not be touched) offers no wall time → UTC function. My reference
  builds `datetime.combine(day, at, tzinfo=to_zone(entry_utc, zone).tzinfo)` and compares it with
  UTC instants; AC-06 accepts that. Comparing naive wall times from `to_zone` also works while
  `at` is outside a DST transition. The contract should say which form is meant by "through
  timebase only".
- **F7 (1)** R_exhausted (start 11.22) with sides ("long",): trades (T1,), sizer calls
  ((11.22, 6.30),), equity ((2026-03-09T11:00, 11.22), (2026-03-10T12:45, 0)), skips 12:45
  spread_filter, 13:00 equity_exhausted, 13:45 equity_exhausted, 14:00 spread_filter, 14:15
  equity_exhausted, 14:30 equity_exhausted (the 13:15 Skip of the short signal disappears).
  **F7 (2)** add `"a data flag that is not str": data_flags=frozenset({1})` to the TypeError cases of
  `test_ac03_simulate_trade_refuses_wrong_types_and_lots_off_the_grid`.

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | UNKNOWN (red as expected) | No implementation. Tests complete: every contract number for long and short, D8 with actual_risk 24, hostile Decimal context. Golden recomputed, no mismatch |
| AC-02 | UNKNOWN (red as expected) | Every fill-table row on both sides (32 cases), 8 run scenarios with the real decide, duck typing. Gaps: F2, F4 |
| AC-03 | UNKNOWN (red as expected) | Every item of "Input และการตรวจ" has a case (list below). Gap: F7 |
| AC-04 | UNKNOWN (red as expected) | The four contract periods and four boundaries; stress on 9 trades × 2 models. Gaps: F1, F5 |
| AC-05 | UNKNOWN (red as expected) | Cut at each trade's exit bar for 3 scenarios; run ↔ simulate_trade mapping for 8 scenarios. No gap found |
| AC-06 | UNKNOWN (red as expected) | Checker self-tests pass, package scan fails loudly while `src/sochron/backtest` is missing. Over-constraint F3, gap F6 |
| AC-07 | not in these files | Whole suite and CI, for the implementer |

## Coverage per contract item (would a test fail if the item were not implemented?)
- Fill table, both sides: entry (ask, stop_price, fallback at entry) yes · gap (low < open < stop and
  mirror, gap made by the spread) yes · touch (and equality) yes · entry M1 SL check yes ·
  stop_distance = and < s·p yes · signal exit, exit M1 not checked yes · exit beyond/equal the stop
  = stop + ambiguous yes · end of data yes · spread None: entry, signal exit, stop M1, last M1 yes;
  ambiguous exit M1 and short entry M1 **no (F4)** · entry/exit spread points after fallback yes ·
  gross not × stress yes · r = net / risk_money (D8) yes.
- Input checks: M15 duck typing and its type errors yes · run refusals (empty, equity ≤ 0 and
  non-finite, M1/M15 timeframe and order, M1 outside every M15, M15 without M1, time_utc ≠ to_utc,
  STOP-level M1 at 3 positions) yes · Rollover (zone, tzinfo, seconds, types, exact class) yes ·
  SizedLots (every listed check) yes · lots via check_volume → BadVolume unwrapped yes ·
  simulate_trade index bounds, per-M1 checks on read M1, domain values, non-finite, types yes;
  data_flags element type **no (F7)** · time only through timebase: zoneinfo import and astimezone
  yes; ZoneInfo through timebase internals **no (F6)**.
- Event order: step 1 (stop inside bar 105) yes · step 2 position after step 1 and next existing
  bar (R_gap/R_window) yes · step 3 exit at t+1 incl. ambiguous yes · step 4 equity ≤ 0 (exactly 0
  and below), sizer None, enter outside sides yes; outside sides while exhausted **no (F7)** ·
  step 5 decide skips whatever sides yes · step 6 yes · first M1 of t+1 not at the bar open **no (F2)**.
- Equity points yes (first point time vs m15[0] **no, F2**) · data_flags both ends, not before or
  after yes · nights boundaries, weekend, DST yes; rollover zone/time, triple weekday, zone weekday
  **no (F1)**; time_utc vs time_raw **no (F5)** · AC-05 cut and mapping yes · versions yes.

## Conventions the author fixed, judged against the contract
1. Frozen dataclasses, contract names and order, Sizer form: the contract lists names in order and
   "(frozen)" is a frozen dataclass in this project (Bar, CostBreakdown). Acceptable.
2. Exact field types: match the contract's types; trades/skips containers left open. Acceptable.
3. TypeError rules (int/float/bool for Decimal, subclasses, None, set/tuple for frozenset,
   generators, non-callable sizer, wrong sizer result) and BacktestError for values: match
   "ชนิดผิด → TypeError", the Sequence signature and the data.snapshot/strategy precedent. Acceptable.
4. SizedLots checks exactly the listed items; lots ≤ 0 reach check_volume (BadVolume): matches the
   enumerated list and AC-03. My probe `sizedlots_lots_positive` (adding lots > 0 to SizedLots)
   fails 2 tests; that check is beyond the contract, so this is not an over-constraint, but the
   implementer must not add it.
5. Per-M1 checks only where the M1 must be read: avoids an over-constraint. Acceptable.
6. exit_time_raw < next entry_time_raw: follows from steps 3–4. Acceptable.
7. AC-05 mapping (exit_index for "signal" or ambiguous, else None; data_flags from bar t to u):
   matches "การแมปในลำดับเหตุการณ์". Acceptable.
8. Nights edges, stress with commission 3.5 and short swap −120.5: valid (stress scales every
   component). Acceptable.
9. Caller's Decimal context neither used nor changed: follows "คำนวณใน CONTEXT" and purity.
   Acceptable.
10. Explicit stdlib list: over-constraint, F3.
11. V-B run parameters (f 8, s 32, n 10, θ 0.50, N 48, M 24, k 3.0): inside H001 s.4 (s ≥ 3f, M ≤ N).
    Acceptable.

## Recommendations on the author's open questions
1. STOP-level M1 after the stop in simulate_trade → **contract clarification, then a test**: "M1
   ที่อ่าน" = entry_index … exit_index (or the last M1) whatever the stop; "ก่อน fill ใดๆ" already
   implies a set that cannot depend on the fill. Not blocking: my reference checks the whole range
   and passes, so both readings pass today.
2. M15 OHLC/spread vs its M1 → **leave untested** in CORE-007 (no contract basis; R1 builds M15 with
   aggregate from the same M1). Note it for SLICE-R1 if M15 ever comes from another source.
3. sides with a non-str element → **leave untested**; if the contract is touched for F3, say
   TypeError (as the tests already do for M15 flag elements).
4. Short-only sides → **leave untested** (the subset rule is tested; D11 needs only long-only).
5. Result.trades/skips containers → **contract change when next touched** (tuple, since Result is
   frozen); until then leave untested.
6. M15 time_utc vs the rule → **contract change + test** (Low): `next_open_utc` is the next M15
   bar's time_utc and decides the entry window, so a wrong value changes decisions silently; add
   "M15 time_utc ≠ to_utc(time_raw, rule) → BacktestError" beside the M1 item.
7. Rollover.at with fold=1 → **leave untested** (fold matters only for an `at` inside a DST overlap).
8. Stdlib list → **contract change** (F3).

## Golden recomputation (independent scratch script; imports neither tests, golden nor sochron.costs)
Plain Decimal at precision 28 / ROUND_HALF_EVEN, own fill-table logic, nights with zoneinfo directly,
real `sochron.strategy.indicators`/`decide` on M1 and M15 built by the script (own aggregation):
- AC-01 long and short: every value equal (stop 4000.90 / 4041.86, nights (1,0), gross 34.40,
  costs, net 32.7124 / 33.72, r 1.308496 / 1.3488); 2× long: total 3.3752, net 31.0248, r 1.240992.
- 15 fill cases: long gap, touch (M1 before entry not read), entry-M1 touch, stop_distance = s·p,
  ambiguous beyond, end of data, None at an entry M1 that stops; short gap made by the spread, gap
  at a later M1, entry-M1 touch, stop_distance < s·p, ambiguous equal, None at the stop M1, end of
  data, None at the signal exit: all equal.
- AC-04: the four contract periods and the four extra boundaries: all equal; a fixed 21:00 UTC rule
  gives 2 for the DST case, as the golden says.
- Whole run R, the real decide per bar: 99 none · 100 enter_long 6.30 · 101 hold · 102 exit ·
  103 skip spread_filter · 104 enter_long 7.44777 · 105 (flat after the stop at 13:22) enter_short
  9.042993 · 106 hold · 107 exit · 108 skip spread_filter · 109 enter_long 9.0826877073 (sizer None)
  · 110 enter_long 8.44441893657. Trades T1–T4, skips and equity 10000 → 9988.78 → 9966.13669 →
  9947.65669 → 9948.45669: all equal. Result: **no mismatch**.

## Satisfiability and mutants
My own contract-only `sochron.backtest` (one module in the scratchpad, written before reading the
handoff), loaded first: the runner puts the scratch directory at the front of `sochron.__path__`,
changes directory to the scratch root so AC-06 scans the scratch source, and prints every module's
file: only `sochron.backtest` came from the scratchpad; `sochron`, `core`, `costs`, `timebase`,
`strategy`, `data`, `data.snapshot` and their submodules came from `<repo>/src`. Result: **86
passed** (85 acceptance + AC-06), first run, no change to the reference. Every test is satisfiable
except as F3 describes.

Mutants not in the author's list (acceptance + golden + AC-06, 86 tests):

| Mutant | Result |
|---|---|
| rollover argument ignored (NY 17:00 hard-coded) | 86 passed — gap F1 |
| triple weekday hard-coded to Wednesday | 86 passed — gap F1 |
| Mon–Fri and triple from the UTC weekday of T | 86 passed — gap F1 |
| nights from time_raw read as UTC | 86 passed — gap F5 |
| entry/exit M1 found by the M15 open time | 86 passed — gap F2 |
| first equity point at m15[0].bar.time_raw | 86 passed — gap F2 |
| ambiguous decision with the entry M1's spread | 86 passed — gap F4 |
| ambiguous decision with spread None read as 0 | 86 passed — gap F4 |
| equity check before the sides filter | 86 passed — gap F7 |
| data_flags elements not type-checked | 86 passed — gap F7 |
| every event uses the entry M1's spread | 28 failed |
| long stop_price from the bid (open − stop_distance) | 42 failed |
| run checks `model` only when it trades | 1 failed |
| equity exhausted only below 0 (`< 0`) | 2 failed |
| sizer always given the start equity | 7 failed |
| Skip time of bar t+1 | 14 failed |
| strategy exit beyond the stop treated as a mid-way stop (exit_index None) | 5 failed |
| SizedLots also refuses lots ≤ 0 (beyond the contract's list) | 2 failed (convention 4) |
| AC-06: `from __future__ import annotations` / `import math` added | AC-06 failed — F3 |
| AC-06: `sochron.data.snapshot` imported inside a function | AC-06 failed, line reported |
| AC-06: `ZoneInfo` imported from `sochron.timebase.convert` | AC-06 passed — gap F6 |

## Quality
- Wrong reason: the TypeError/BacktestError tables run on a dataset with no entry, so a lazy check
  cannot pass by accident; each table records any other exception as a failure. Sizer errors are
  checked by identity. No test found that passes for the wrong reason.
- Determinism: no clock, randomness or order-dependent comparison (flags compared as frozensets,
  reasons from decide). The faithful reference ran 5 times in separate processes under random hash
  seeds (`-I` ignores PYTHONHASHSEED), 86 passed each time.
- Implementation details: no private helper, error message or exact container type is relied on;
  field order and positional `Rollover(zone, at)` come from the contract listing and D4.
- AC-06 with the package missing: the checker self-tests pass, then
  `AC-06: …\src\sochron\backtest does not exist; implementation missing` (loud, contract reason).
- AST compare against `git show HEAD:tests/architecture/test_imports.py`: HEAD 64 top-level
  statements, new 75; statements 1–63 after the docstring equal by `ast.dump`, in order; the module
  docstring only grew at its end (the CORE-007 paragraph); 11 statements added at the end; none
  rebinds an existing name.

## Checks run (command → result → commit → time UTC 2026-10-24)
- `sha256sum` of the patch and the three files → all equal to the expected values · `git
  hash-object` → 9ef4a60c…, 9af29004…, 6250f242… equal → a7a0a0f + applied patch → 04:0x
- `git apply -R --check docs/proposals/CORE-007-tests.patch` (standalone, repo root) → exit 0, no
  output → 04:0x
- `node scripts/controls/check-locked-paths.mjs origin/main` → FAIL as expected: exactly
  tests/architecture/test_imports.py (M), tests/acceptance/CORE-007/test_backtest.py (A),
  tests/golden/CORE-007/backtest_cases.py (A) need the owner label → 04:0x
- `git diff --name-only origin/main HEAD` → PROGRESS.md, CORE-006 contract and evidence only;
  `origin/main^{tree}` = `b7256cd^{tree}` = 1d7b7827… → 04:0x
- `timeout 900 uv run --offline pytest tests -q -p no:cacheprovider -rf` → **86 failed, 3093
  passed** in 16.43 s; 85 × "AC-0n: sochron.backtest not implemented (No module named
  'sochron.backtest')" (AC-01 3, AC-02 43, AC-03 19, AC-04 9, AC-05 11) + 1 × the AC-06 message
  above → 04:0x
- `timeout 600 uv run --offline --no-sync python -I -B <scratch>/runner/run_ref.py <repo>
  <scratch>/ref "" tests/acceptance/CORE-007 tests/golden/CORE-007
  tests/architecture/test_imports.py::test_ac06_core007_backtest_imports_only_core_timebase_strategy_costs_and_listed_stdlib`
  → 86 passed (1.1–1.3 s, repeated after every edit of the reference) → 04:0x–04:2x
- `uv run --offline --no-sync python -I -B <scratch>/runner/golden_check.py <repo>` → no mismatch → 04:1x
- `uv run --offline --no-sync python -I -B <scratch>/runner/ast_compare.py <scratch>/head_test_imports.py <repo>/tests/architecture/test_imports.py` → as above → 04:1x
- `bash scripts/controls/red-flags.sh origin/main` → "Pattern groups with hits: 0"; control file
  touched: tests/architecture/test_imports.py; the two new files are untracked and not scanned, so
  I ran the same patterns with Grep over both → 0 hits (the seven `except Exception` lines record
  the wrong exception and fail the test, or re-raise) → 04:1x
- `git status --porcelain --untracked-files=all` before and after every scratch run → unchanged
  (the three patch paths and the handoff) → 04:2x

## Checked, nothing found (and how)
- Hashes, blobs, reverse apply and locked paths: commands above.
- Golden values: independent recomputation above, no mismatch.
- Satisfiability: contract-only reference 86/86, first run.
- Over-constraints other than F3: each author convention judged above; no exact message, private
  helper or container type relied on.
- Red run: 86/3093, every failure for the contract reason.
- Architecture file: AST compare above; no existing table or function changed or rebound.
- Red flags: 0 groups in the tracked diff, 0 pattern hits in the untracked test files; no secrets,
  no skip/xfail, no type-ignore, no swallowed errors; the golden imports only datetime.

## Not checked (and why)
- CI (GitHub Actions) and Linux: not run in this read-only review; the error type of
  `ZoneInfo("")` may differ between platforms, which the implementer must map to BacktestError.
- The contract's speed row (500,000 M1 within 60 s): unit test and evidence of the implementer.
- The author's scratch reference, runner and mutants: not in the repository, only the handoff's
  list; my own were used instead.
- Python other than 3.12.15 / pytest 9.1.1.

## Blocks during this session
- After my first `git status`, the PostToolUse detector (check-locked-after) reported exactly the
  three patch targets (M tests/architecture/test_imports.py, A tests/acceptance/CORE-007/test_backtest.py,
  A tests/golden/CORE-007/backtest_cases.py), applied before this session; every SHA256 and blob was
  verified against the expected values, then I continued (CLAUDE.md, N6 condition met).
- guard-bash blocked `git -C "<repo>" apply -R --check docs/proposals/CORE-007-tests.patch`:
  "Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run
  each action separately." Rerun as `git apply -R --check docs/proposals/CORE-007-tests.patch`
  alone from the repo root (owner's standing standalone-rerun exception, F21).
- guard-bash blocked `S=…; mkdir -p "$S/ref_lazy/src/sochron/backtest" …`: "Blocked by
  .claude/hooks/guard-bash.mjs: mkdir would change $S/ref_lazy/src/sochron/backtest (a path that
  cannot be resolved here (variable or unknown directory)). The implementer may not change locked
  paths; ask the owner." My mistake (a shell variable in mkdir). Rerun with literal scratchpad
  paths (owner's exception for headless reviewers: a variable path to the scratchpad becomes a
  literal path). The separate follow-up command of that step ran on missing directories and did
  nothing.

## Verdict
Ready to commit red: no — nothing in the existing expectations is wrong and every test is
satisfiable, but one contract clause (D4 rollover and triple weekday, F1 Medium) has no test that a
plausible wrong implementation fails, and one test (F3) fails a contract-faithful implementation.
Minimal path: a tests r2 patch adds F1 (required) and preferably F2, F4, F5, F6, F7 (all values
above), and the owner settles F3 by a contract v1.5 line (no test change) or a test change; then a
narrow re-check of those IDs.

Findings open: 7
