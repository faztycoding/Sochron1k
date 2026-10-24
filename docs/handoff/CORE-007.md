# Handoff CORE-007 · contract v1.4 · base commit b7256cd (branch feat/CORE-007-backtest)

<!-- Facts only. No persuasion. The reviewer reads this AFTER writing the first round of findings. -->

Test-author handoff (tests r1). Author: a fresh Claude Code session acting as test author under the
role swap of contract D7 (Codex out of quota until 2026-10-28 19:41). This session wrote no
implementation, read no implementation of CORE-007 (none exists) and no implementer notes, and
staged, committed and pushed nothing. Written 2026-10-24 (UTC 03:5x).

## Deliverable

One D-006 patch, never applied by this session:
`docs/proposals/CORE-007-tests.patch` · 2020 lines · 127756 bytes ·
SHA256 `da45cb55e14fa97883510f72a5c7dd0d13b115ea4ce0c299cdc34ba103c815db`.
`docs/proposals/` is ignored by `.gitignore` line 10, so the patch is a local file, not a commit.

| Path after apply | Change | Lines (numstat) | Expected SHA256 | Expected Git blob |
|---|---|---|---|---|
| tests/acceptance/CORE-007/test_backtest.py | new | +1100 | `9388804e2acaf2f055c5a5b90f1e360eec28064822f6341a9b75ccafab776a32` | `9ef4a60c59cc5f1bad49895479b99eacf98c6d2a` |
| tests/golden/CORE-007/backtest_cases.py | new | +669 | `6e3b98512f2f15e7908d4fa56f51910bf339cdb387d6419f2ed3c91e3cbaee46` | `9af29004164cdadb1d623c85097b334d4fe4f015` |
| tests/architecture/test_imports.py | changed | +232 −0 | `299661bc8c1257db92ac431d40927954de1b79803419102a5a1d1339257f76bb` | `6250f24262810997e59e23c90378a580720b3143` |

Base of the changed file: `tests/architecture/test_imports.py` at HEAD b7256cd, blob
`504c88a6c4e9af40b288f1665fc15639485d654d`, SHA256
`e0f1cc4f8ebdc4ef7c46280f8edd4f2087b60f7b4b3397566eff94265493cca4` (the worktree file had the same
blob). Each expected blob was computed twice, `git hash-object --no-filters` and
`git hash-object --path=<path>` (through `*.py text eol=lf`): equal for all three, so the files
are LF only. Each file ends with one newline. The two new-file sections of the patch, stripped
of their `+`, give exactly the SHA256 values above.

## Implementer apply steps (CLAUDE.md, D-006)

1. On `feat/CORE-007-backtest` with these three paths as at b7256cd, run each as its own command:
   `git apply --check docs/proposals/CORE-007-tests.patch`, then
   `git apply docs/proposals/CORE-007-tests.patch`.
2. The post-run detector must report exactly the three paths above. Verify every SHA256
   (`sha256sum`) and Git blob (`git hash-object`) against the table. Any mismatch, missing hash or
   other report: stop and ask the owner (N6).
3. Optional, standalone: `git apply -R --check docs/proposals/CORE-007-tests.patch`.
4. Run `uv run --offline pytest tests -q -p no:cacheprovider` (under an outer timeout). Expected
   red: 3179 tests, 86 failed, 3093 passed (the 3093 tests of today all pass; the 85 new acceptance
   tests and the new AC-06 test fail because `sochron.backtest` does not exist).
5. Fresh-session review of the applied tests (tests review r1), then commit the red tests:
   `test(core-007): acceptance tests for CORE-007` with `Refs: CORE-007`.

## Checks run (command → result → commit → time UTC)

- `uv run --offline pytest tests -q -p no:cacheprovider` (repo root) → PASS, 3093 passed in 13.75 s
  → b7256cd → 2026-10-24T03:45:55Z. Every existing test passes before the patch.
- Red: `uv run --offline --no-sync python -I -B <scratch>/runner.py <repo> none repo -- <scratch
  copies of the three files> --tb=no` from the repo root → 86 failed, 15 passed → b7256cd →
  03:46Z and again after the last edit (same numbers). The 15 passing tests are the existing
  tests of the changed architecture file.
- Green on a contract-only reference (see Satisfiability) → 85 passed (acceptance + golden) and
  16 passed (architecture) → b7256cd → 03:46Z and again after the last edit.
- Golden cross-check with exact fractions (`check_golden.py`, no sochron import) → 0 differences.
- AST comparison of the architecture file (`ast_compare.py`) → 0 differences (below).
- `git apply --check docs/proposals/CORE-007-tests.patch` (standalone) → exit 0, no output.
- `git apply --numstat docs/proposals/CORE-007-tests.patch` → 1100/0, 669/0, 232/0.
- Environment: Windows 11, Git Bash, Python 3.12.15, pytest 9.1.1, every run under `timeout`.

## Red: why each group fails

| AC | Tests | Fails now because |
|---|---|---|
| AC-01 | 3 | `_api` → `pytest.fail("AC-01: sochron.backtest not implemented (No module named 'sochron.backtest')")` |
| AC-02 | 43 (32 fill cases, 1 fixture coverage check, 8 run scenarios, hostile context, duck typing) | same message, AC-02 |
| AC-03 | 19 | same message, AC-03 |
| AC-04 | 9 (8 holding periods, 1 stress) | same message, AC-04 |
| AC-05 | 11 (3 cut scenarios, 8 run ↔ simulate_trade scenarios) | same message, AC-05 |
| AC-06 | 1 | the checker self-tests pass, then `AC-06: <repo>\src\sochron\backtest does not exist; implementation missing` |

No test fails on a syntax, import or fixture error of its own.

## Test inventory (what each test proves)

| AC | Test | Proves |
|---|---|---|
| AC-01 | test_ac01_h001_example_long_and_short_through_simulate_trade | The H001 example long and short: every contract number (nights 1, triple 0, gross 34.40, costs, net, r, stop_price) as exact Decimal with exact types |
| AC-01 | test_ac01_r_is_net_over_the_formula_r_not_the_actual_risk | D8: with actual_risk 24 the r stays 32.7124 / 25 = 1.308496 and actual_risk is kept |
| AC-01 | test_ac01_values_do_not_depend_on_the_caller_decimal_context | A hostile caller context (prec 4, ROUND_UP, Inexact/Rounded traps) changes nothing and is left as it was |
| AC-02 | test_ac02_fill_table_case[32 cases] | Every fill-table row on both sides: gap (low < open < stop and the short mirror), gap made by the spread, touch (and touch exactly at the stop), stop in the entry M1, stop_distance = and < s*p, signal exit (exit M1's low/high not checked), exit open beyond / equal to the stop = stop + ambiguous at the open, stop before exit_index, end of data, spread None at entry, exit, stop M1 and last M1; the M1 before entry_index is not read |
| AC-02 | test_ac02_fill_cases_cover_every_row_on_both_sides | The golden table holds each outcome for both sides |
| AC-02 | test_ac02_run_with_the_real_decide_matches_the_hand_computed_scenario[8] | run with the real decide: R (stop inside bar 105 then the opposite entry at 106, decide skips, sizer skip, entry at the second-to-last bar, exit open beyond the stop, end of data), long-only, exit at the second-to-last bar, data_flags at both ends and not before or after, next_open_utc = the next existing bar (gap and no-gap) |
| AC-02 | test_ac02_run_does_not_depend_on_the_caller_decimal_context | Scenario R under a hostile context |
| AC-02 | test_ac02_run_takes_m15_bars_by_duck_typing | A test-local frozen dataclass with .bar/.flags gives the same Result as AggregatedBar |
| AC-03 | test_ac03_public_types_versions_and_shapes | BACKTEST_VERSION, BacktestError ⊂ ValueError, Side, Sizer, field names and order, frozen instances, one equity point when nothing trades, strategy_version |
| AC-03 | test_ac03_sized_lots_checks_its_fields | SizedLots: valid shapes; BacktestError for risk_money ≤ 0, actual_risk with no lots, actual_risk ≤ 0, empty reason, non-finite Decimals; TypeError for wrong types and subclasses |
| AC-03 | test_ac03_rollover_checks_zone_and_wall_time | Rollover: unknown zone and seconds/tzinfo → BacktestError; wrong types → TypeError |
| AC-03 | test_ac03_run_refuses_every_input_mismatch | Every item of "Input และการตรวจ" for run → BacktestError (empty inputs, equity ≤ 0 or non-finite, M1/M15 timeframe and order, M1 outside every M15, M15 without M1, time_utc ≠ to_utc, bad sides) |
| AC-03 | test_ac03_run_refuses_stop_level_m1 | Negative spread, inconsistent OHLC (5 forms), non-positive prices (3 forms) at three positions → BacktestError |
| AC-03 | test_ac03_run_refuses_wrong_types | Generators, AggregatedBar or Bar subclass among M1, M15 without .bar, wrong .bar/.flags, None and wrong objects for params, model, rule, rollover (subclass too), sides, equity → TypeError |
| AC-03 | test_ac03_simulate_trade_refuses_bad_indexes_and_values_before_any_fill | Index bounds, side, stop_distance, risk_money, actual_risk, non-finite Decimals → BacktestError |
| AC-03 | test_ac03_simulate_trade_refuses_stop_level_m1_it_reads | STOP-level M1, timeframe 5 and non-increasing time on the entry M1, an M1 before the exit, the exit M1 and the last M1, both sides → BacktestError |
| AC-03 | test_ac03_simulate_trade_refuses_wrong_types_and_lots_off_the_grid | Wrong types → TypeError (risk_money missing or positional too); lots 0.015, 0.001, 200.01 → exactly costs.BadVolume |
| AC-03 | test_ac03_sizer_sizes_reach_the_trade | Four sizes (0.01, 0.37, 1.00, 200): lots, risk_money, actual_risk reach the Trade; costs scale; r = net / risk_money |
| AC-03 | test_ac03_sizer_without_lots_is_a_skip_with_its_reason | lots None → Skip(time of bar t, (reason,)), no trade |
| AC-03 | test_ac03_sizer_lots_refused_by_costs_raise_bad_volume_unwrapped | lots 0.015, 0, 0.001, 200.01, −0.01 → exactly BadVolume |
| AC-03 | test_ac03_sizer_errors_reach_the_caller_unchanged | SizedLots errors raised inside the sizer and a sizer's own exception reach the caller as the same object |
| AC-03 | test_ac03_sizer_result_of_the_wrong_type_is_a_type_error | None, tuple, Decimal, SizedLots subclass, a non-callable sizer → TypeError |
| AC-03 | test_ac03_exhausted_equity_skips_every_later_entry_without_sizing[2] | Equity exactly 0 and below 0: Skip "equity_exhausted" for every later entry, no sizer call, decide skips kept |
| AC-03 | test_ac03_sizer_sees_equity_after_each_trade_and_positions_never_overlap[3] | Sizer calls get the equity after the previous trade; exit before the next entry; equity points format |
| AC-04 | test_ac04_nights_and_triple_nights_of_a_holding_period[8] | The four contract periods (1,0), (5,1), (2,1), (1,0) across the end of daylight time, plus entry/exit exactly at a rollover, one minute either side, the weekend, a short |
| AC-04 | test_ac04_double_costs_keep_prices_and_gross_and_double_every_charge | stress(model, 2) on 9 trades and 2 models: prices, stop_price, gross equal, every charge exactly 2x; the AC-01 long at 2x by hand |
| AC-05 | test_ac05_cutting_after_a_close_keeps_every_earlier_trade_skip_and_equity_point[3] | For each trade k, the cut run gives exactly trades 1..k, the Skips before u and equity points 0..k |
| AC-05 | test_ac05_every_run_trade_equals_simulate_trade_of_its_entry_and_exit[8] | Each run trade equals simulate_trade under the mapping; entries and strategy exits are at the first M1 of their bar; data_flags from t to u |
| AC-06 | test_ac06_core007_backtest_imports_only_core_timebase_strategy_costs_and_listed_stdlib | Checker self-tests (exact findings, grants for backtest only, every FIX-001/CORE-001 rule kept), then the package scan |

## Satisfiability

A minimal contract-only reference of `sochron.backtest` was written in the session scratchpad
(never in the repository) and loaded first: a runner under `uv run --offline --no-sync python -I
-B` imports `sochron` from `<repo>/src`, inserts the scratch directory at the front of
`sochron.__path__`, runs pytest with the repository's pyproject (`-c`, `--rootdir`) and prints
every loaded sochron module's file. Result: 85 passed; `sochron.backtest` came from the scratch
reference and every other module (`sochron`, `core`, `costs`, `timebase`, `strategy`,
`data.snapshot` and their submodules) from `<repo>/src`. The architecture test scans
`Path.cwd()/src`, so for it the runner changed directory (inside the process, the shell stayed at
the repo root) to a scratch copy of `<repo>/src` plus the reference: 16 passed.

## Mutants (each changes the reference only; acceptance + golden: 85 tests)

| Mutant | Result |
|---|---|
| touch checked before gap | 5 failed |
| spread counted twice (gross from the ask on the paying side) | 60 failed |
| gross times the stress factor | 1 failed (AC-04 stress) |
| R divided by the actual risk | 20 failed |
| nights: a rollover at the entry counted (entry ≤ T) | 1 failed (boundary case) |
| nights: a rollover at the exit missed (T < exit) | 1 failed (boundary case) |
| SL check skips the entry M1 (simulate_trade and run) | 7 failed |
| decide sees the position before the stop of bar t | 5 failed |
| next_open_utc = bar t + 15 minutes | 1 failed (R_gap) |
| data_flags skip the decision bar / skip the exit bar | 6 failed / 6 failed |
| decide skips dropped when long-only | 2 failed |
| no equity-exhausted check | 3 failed |
| gross computed in the caller's context | 2 failed |
| no STOP-level M1 checks | 2 failed |
| exit open beyond the stop called "signal" | 9 failed |
| short gap without the spread | 2 failed |
| end of data at the last open | 4 failed |
| missing spread read as 0 | 9 failed |
| rollover read in UTC | 3 failed |
| sizer result not type-checked | 1 failed |
| SizedLots accepts risk_money 0 | 2 failed |
| Rollover accepts unknown zones | 1 failed |
| M1 time_utc not checked against the rule | 1 failed |
| Architecture (16 tests, scratch src copy): imports zoneinfo · calls astimezone · imports sochron.data.snapshot · imports sochron.risk · a float literal · datetime.now | 1 failed each, with the offending line reported |

## AST comparison (tests/architecture/test_imports.py)

Against `git show HEAD:tests/architecture/test_imports.py`: HEAD has 64 top-level statements, the
new file 75. The 63 statements after the docstring are identical by `ast.dump` and in the same
order; the module docstring only grew at its end (5 lines on CORE-007). Added at the end:
`_BACKTEST_GRANTS`, `_BACKTEST_STDLIB`, `_IMPORT_FINDING`, `_BACKTEST_ADDED`,
`_granted_to_backtest`, `_inspect_backtest_source`, `_inspect_as_backtest`, `_BACKTEST_FORBIDDEN`,
`_BACKTEST_ALLOWED`, `_BACKTEST_GRANTS_ELSEWHERE` and
`test_ac06_core007_backtest_imports_only_core_timebase_strategy_costs_and_listed_stdlib`. The 15
existing tests are kept in order, and `_allowed_import` is untouched: the backtest checker drops
only the "forbidden import" findings of sochron.timebase, sochron.strategy and sochron.costs from
the unchanged snapshot checker and adds its own findings.

## Conventions fixed where the contract leaves room

1. SizedLots, Rollover, Trade, Skip, Result are frozen dataclasses with the contract's field names
   in the contract's order. Sizer is `Callable[[Decimal, Decimal], SizedLots]` (a forward
   reference to SizedLots is accepted).
2. Exact types: Decimal for prices, distances, lots, money and r; int for times, spread points,
   nights; bool for ambiguous; frozenset of str for data_flags; costs.CostBreakdown for costs;
   Result.equity a tuple of (int, Decimal) tuples; Skip.reasons a tuple of str. trades and skips
   are compared as sequences.
3. TypeError for every wrong type named in the test docstring (generators for m1/m15, subclasses,
   None, set/tuple for frozenset, non-callable sizer, a sizer result that is not SizedLots);
   BacktestError for right types with wrong values, non-finite Decimals included; an unknown zone
   includes "".
4. SizedLots checks exactly the contract's list: lots of 0 or below pass it and run refuses them
   through costs.check_volume (BadVolume).
5. simulate_trade's per-M1 checks are tested only on M1 the call must read (entry M1, an M1 before
   the exit, the exit_index M1, the last M1 of an end of data).
6. No overlap means exit_time_raw < next entry_time_raw.
7. AC-05: u is the M15 bar of the exit M1; the cut run must give exactly trades 1..k; the mapping
   uses exit_index when exit_reason is "signal" or ambiguous is True; entries and strategy exits
   are the first M1 of their M15 bar; data_flags span the bar before the entry bar to u.
8. Nights: entry < T <= exit tested at both edges; stress tested also with commission 3.5 per lot
   per side and short swap −120.5 points.
9. The caller's Decimal context neither changes results nor is changed.
10. AC-06: backtest may import exactly the strategy stdlib list (bisect, collections,
    collections.abc, dataclasses, datetime, decimal, enum, functools, itertools, operator, types,
    typing); a zoneinfo import anywhere, any `.astimezone` attribute and the string "astimezone"
    are findings.
11. Run scenarios use V-B with f 8, s 32, n 10, theta 0.50, N 48, M 24, k 3.0 (inside H001 section
    4) so every value is exact; M15 bars come from M1 through `sochron.data.snapshot.aggregate`
    with 15 M1 each; the sizer in run tests is a scripted fake.

## Open questions (the contract does not say; left untested)

1. Must simulate_trade reject a STOP-level M1 after the stop (an M1 it never needs)?
2. Must run check that each M15 bar's OHLC and spread agree with its M1?
3. sides holding a non-str element: TypeError or BacktestError?
4. Short-only (`sides={"short"}`) is not named; only the subset rule is tested.
5. Container types of Result.trades and Result.skips.
6. Must the M15 time_utc agree with the rule, as for M1?
7. Rollover.at with fold=1.
8. The stdlib list (convention 10) may be too narrow for the implementer (math, heapq); widening it
   needs a tests revision.

## Blocks and failures during this session

- Hook block (reported, step stopped, not retried or reshaped): an inline `python -c` byte count
  of CR/LF in the scratch copies →
  `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: inline python code references a locked path (tests/acceptance). Use the Read tool to read files; locked paths are owner-only.`
  The LF evidence above comes from the filtered/raw blob comparison done for the expected blobs.
- A Bash heredoc that would have appended the AC-06 section to the scratch copy failed to parse
  (`unexpected EOF while looking for matching '`); nothing was written; the section was added
  with the Edit tool instead. Not a hook block.

## Not verified

- The patch was not applied (by instruction); the post-apply red numbers come from running the
  scratch copies with the repository's pyproject, not from a patched tree.
- CI was not run. Run speed (contract row "ความเร็ว") is the implementer's unit test, not here.
- The reference implementation proves satisfiability only; it is not a deliverable and stays in
  the session scratchpad.

## Findings response (filled after review)
| ID | Accept/Dispute | Commit | Evidence |
|----|----------------|--------|----------|

## Round 2 (tests-r1 F1-F7, contract v1.5)

Test-author handoff (tests r2). Author: a fresh Claude Code session acting as test author for round
2 under the D7 role swap (Codex out of quota until 2026-10-28 19:41). This session is not the
implementer, not the round-1 author and not a reviewer of this task. It read AGENTS.md, CLAUDE.md,
contract v1.5, docs/reviews/CORE-007-tests-r1.md, round 1 of this handoff, the three test files in
place and the merged interfaces it builds inputs with (core, costs, timebase, strategy,
data.snapshot). It wrote no implementation in the repository and staged, committed, pushed and
applied nothing. Written 2026-10-24 (UTC 04:5x) at HEAD 7b70336, round-1 patch applied and
uncommitted.

### Deliverable

One D-006 patch, never applied by this session:
`docs/proposals/CORE-007-tests-r2.patch` · 613 lines · 40173 bytes ·
SHA256 `c71fd501710a8af41eb7a36b8645be0402cef81c8522baf41be7d534ff71e424`.
`docs/proposals/` is ignored by `.gitignore` line 10, so the patch is a local file. It is three
`diff -u --label a/<path> --label b/<path>` sections, concatenated in this order: architecture,
acceptance, golden. Every hunk only adds lines (`git apply --numstat`: 138/0, 272/0, 164/0).

| Path | Base blob each hunk expects (round 1 applied) | Hunks (base lines) | Lines after | Expected SHA256 after apply | Expected Git blob after apply |
|---|---|---|---|---|---|
| tests/architecture/test_imports.py | `6250f24262810997e59e23c90378a580720b3143` | `-20,6 +20,10` (docstring end), `-2040,3 +2044,137` (end of file) | 2180 | `b5964d1e3b91f2e6f78e3b22f82578110c0f55b40ab15debdc7cb5d5c6358d13` | `6751aadfddc386420632668e83714785432dc4af` |
| tests/acceptance/CORE-007/test_backtest.py | `9ef4a60c59cc5f1bad49895479b99eacf98c6d2a` | `-48,6 +48,18` (docstring end), `-1098,3 +1110,263` (end of file) | 1372 | `05c7cd6622117c42ea28dbf1220e2e49406922a260ae8f11894e2056bdb083f2` | `b13bbd1984b2c93f22ac2d0a429725d03c3a111a` |
| tests/golden/CORE-007/backtest_cases.py | `9af29004164cdadb1d623c85097b334d4fe4f015` | `-36,6 +36,11` (docstring end), `-667,3 +672,162` (end of file) | 833 | `3b790ada48b68206db0ee7730f4e1688a9894e762e507f775d75d6332708c08c` | `d189582699490b254f17783ffa064a2109833858` |

The base files are the round-1 files of the table at the top of this handoff (SHA256 `299661bc…`,
`9388804e…`, `6e3b9851…`), verified by SHA256 and blob at the start of this session. The patch has
no `index` lines, so `git apply` does not compare blobs itself: check the base blobs before
applying. Expected blobs: `git hash-object --no-filters` and `git hash-object --path=<path>`
(`*.py text eol=lf`) agree, so the files are LF only; each ends with one newline. Applying the
patch in memory to byte copies of the three round-1 files gives exactly the round-2 files above
(scratch `apply_check.py`; nothing written).

### Tests added (17: 16 acceptance, 1 architecture)

| Finding / item | Test (file::name) | What it proves |
|---|---|---|
| F1 (required) | test_backtest.py::test_ac04_r2_nights_follow_the_rollover_zone_and_time_and_the_model_triple_weekday [3 cases] | (a) Asia/Tokyo 06:00, triple_swap_weekday 0: (1, 1), swap 15.114, total 18.114, net −8.114, r −0.32456; (b) America/New_York 23:00: (0, 0), total 3.00, net 7.00, r 0.28; (c) added: Asia/Tokyo 06:00 on a Tokyo Wednesday that is a UTC Tuesday: (1, 1). Together: the zone, the wall time, the zone's weekday and the model's triple day are all inputs |
| F5 | ::test_ac04_r2_nights_compare_time_utc_not_time_raw | time_raw = UTC seconds + 3600 with the correct time_utc, 21:01 Tue → 20:59 Wed UTC: (0, 0), net 7.00, r 0.28; the Trade keeps the raw times 1773784860 / 1773871140 |
| F4 | ::test_ac02_r2_fill_case_spread_none_at_an_ambiguous_exit_or_a_short_entry_stop [2 cases] | (a) short, exit_index M1 without spread: s 240 puts the ask open 4005.02 beyond the stop 4005.00: stop + ambiguous at 4004.78, exit spread 240, gross −47.80, total 3.40, net −51.20, r −2.048; (b) short entry M1 without spread, stop_distance 0.22: gap at the entry open, exit 4000.00 at 14:00, spreads 240, gross 0, net −3.40, r −0.136 |
| F2 | ::test_ac02_r2_run_fills_at_the_first_m1_present_in_the_next_bar [2 scenarios] | R_to_103 without minute 0 of bars 0 and 101 (review values): entry 12:16 at 4002.00, stop_price 3995.94, exit 12:45 at 3998.60 signal, costs (0.72, 0, 0.30, 0, 1.02), gross −10.20, net −11.22, r −0.4488, actual_risk 18.90, data_flags {incomplete}, no Skip, equity ((11:01, 10000), (12:45, 9988.78)), sizer calls ((10000, 6.30),). Added exit side: without minute 0 of bar 103, the exit fills at 12:46 and the last equity point is (12:46, 9988.78) |
| F7 (1) | ::test_ac03_r2_long_only_with_exhausted_equity_records_no_skip_for_a_short_entry | R_exhausted (11.22) with sides {long}: trades (T1,), sizer calls ((11.22, 6.30),), equity ((11:00, 11.22), (12:45, 0)), Skips 12:45 spread_filter, 13:00, 13:45 equity_exhausted, 14:00 spread_filter, 14:15, 14:30 equity_exhausted; no 13:15 Skip |
| F2, F7 (1) | ::test_ac05_r2_every_run_trade_equals_simulate_trade_of_its_entry_and_exit [3 scenarios] | the round-1 AC-05 mapping (convention 7) on the three round-2 run scenarios |
| F7 (2) | ::test_ac03_r2_simulate_trade_refuses_data_flags_that_are_not_a_frozenset_of_str | `frozenset({1})` (review) and, added from convention 3, a str-subclass flag and a frozenset subclass → TypeError; `frozenset({"incomplete"})` passes through |
| v1.5 item 4 | ::test_ac03_r2_run_refuses_sides_with_an_element_that_is_not_str | `{1}`, `{b"long"}`, `{str subclass "long"}`, `{"long", 1}` → TypeError; `{"long"}` runs |
| v1.5 item 5 | ::test_ac03_r2_result_trades_and_skips_are_tuples | `type(...) is tuple` for trades and skips, on scenario R and on a run with no entry |
| v1.5 item 6 | ::test_ac03_r2_run_refuses_an_m15_bar_whose_time_utc_is_not_to_utc_of_its_time_raw | AggregatedBar and duck-typed M15 items whose Bar has a UTC time_utc moved by +1 min (bar 1), +60 min (last bar), −1 min (first bar), +60 min (every bar) → BacktestError |
| F6, v1.5 "เวลา" | test_imports.py::test_ac06_r2_core007_backtest_never_names_zoneinfo | new checker `_inspect_backtest_zoneinfo_source` = round-1 backtest checker plus "line N: forbidden ZoneInfo import" (an import statement that brings in a name ZoneInfo from any module, at any relative level, aliased, or another name imported as ZoneInfo) and "line N: forbidden ZoneInfo reference" (a bare name, an attribute `.ZoneInfo`, the string "ZoneInfo"). Self-tests: 12 exact-finding sources (the review's probe `from sochron.timebase.convert import ZoneInfo` + `datetime.combine(day, at, tzinfo=ZoneInfo(zone))`, aliases, the timebase package, a relative import, inside a function, `convert.ZoneInfo`, the full module path, `getattr(convert, "ZoneInfo")`, zoneinfo itself, an annotation, another name imported as ZoneInfo), 3 allowed sources (the contract's `datetime.combine(day, at, tzinfo=to_zone(...).tzinfo)`, the timebase functions, words that only contain ZoneInfo), and on every table the new checker keeps every round-1 backtest finding and adds only ZoneInfo findings; then the package scan |

Not tested, as instructed: contract v1.5 item 3 (M1 after the closing M1 are not read), and no
whole-range check. Conventions 10-13 were appended to the acceptance file's docstring (tuples;
non-str elements of sides and data_flags; M15 time_utc; scenarios with a missing minute 0).

### Values compared with the review

Every round-2 value was recomputed by hand from contract v1.5 and the CORE-002 formulas (Decimal
precision 28, ROUND_HALF_EVEN; every value is exact), written out in the golden comments, and
checked again by an independent scratch script with `fractions.Fraction` and `zoneinfo` directly
(no sochron import): 0 differences. **No value differs from the review**: F1 (a) and (b), F2, F4 (a)
and (b), F5 and F7 (1) are identical to "Finding details" of docs/reviews/CORE-007-tests-r1.md,
including the wrong-reading values (New York 17:00, Wednesday, UTC weekday: (1, 0), net 1.962;
time_raw as UTC: (1, 1), net −8.114). Beyond the review: F1 (c), the exit-side F2 scenario, the
AC-05 mapping on the round-2 scenarios, the two extra F7 (2) cases and the sides and M15 cases of
v1.5 items 4 and 6.

### Red (patch not applied; the three files swapped for their round-2 copies)

`timeout 900 uv run --offline --no-sync python -I -B <scratch>/runner/red.py <repo> <scratch>/r2 --tb=no -rf`
from the repo root (pytest on `<repo>/tests` with the repo's CORE-007 acceptance directory and
architecture file ignored and the two round-2 test files added; the acceptance copy loads the
round-2 golden copy; `-c pyproject.toml --rootdir <repo>`) → **103 failed, 3093 passed** in 9.80 s
→ 7b70336 + round 1 → 2026-10-24T04:50:36Z (first run 04:43:11Z: same numbers, 15.06 s).
`sochron.backtest` was not loaded. The 3093 existing tests pass. Failures: round 1 86 (AC-01 3,
AC-02 43, AC-03 19, AC-04 9, AC-05 11, AC-06 1) and round 2 17 (AC-02 4, AC-03 5, AC-04 4, AC-05 3,
AC-06 1). Every acceptance failure is `AC-0n: sochron.backtest not implemented (No module named
'sochron.backtest')`; both AC-06 tests pass their checker self-tests and fail with `AC-06:
<repo>\src\sochron\backtest does not exist; implementation missing`. After the real apply the tree
should give 3196 tests: 103 failed, 3093 passed.

### Satisfiability

My own contract-only reference of `sochron.backtest` (one module, 377 lines, in the session
scratchpad, written from contract v1.5; I saw no other reference). Runner `run_ref.py` under
`uv run --offline --no-sync python -I -B`: puts `<repo>/src` first, imports `sochron`, inserts the
scratch directory at the front of `sochron.__path__`, imports `sochron.backtest`, changes directory
(inside the process) to the reference root so both AC-06 tests scan the scratch source, runs
pytest with the repo pyproject on the round-2 acceptance copy and the two CORE-007 AC-06 tests, then
prints every sochron module's file. Result: **103 passed** (85 + 16 acceptance and golden, 2 AC-06)
on the first run with no test change, and 5 more runs in separate processes (fresh hash seeds):
103 passed each, last at 04:51:06Z. Origins: only `sochron.backtest` from the scratchpad;
`sochron`, `core`, `costs` (+ charges, errors, model), `data`, `data.snapshot` (+ aggregate, model,
validate), `strategy` (+ h001, indicators, params) and `timebase` (+ convert, errors, offset, rules,
sessions) from `<repo>/src`.

### Mutants (one change to the reference each; 103 tests: round 1 + round 2)

| Mutant | Result | Caught by |
|---|---|---|
| rollover argument ignored (New York 17:00 hard-coded) | 3 failed | r2 nights (a), (b), (c) |
| triple weekday hard-coded to Wednesday | 1 failed | r2 nights (a) |
| Mon-Fri and triple from the UTC weekday of T | 2 failed | r2 nights (a), (c) |
| nights from time_raw read as UTC | 1 failed | r2 time_utc not time_raw |
| entry/exit M1 found by the M15 open time | 4 failed | r2 run fills [2], r2 AC-05 [2] |
| first equity point at m15[0].bar.time_raw | 1 failed | r2 run fills [R_first_minutes_missing] |
| ambiguous decision with the entry M1's spread | 1 failed | r2 fill (a) |
| ambiguous decision with spread None read as 0 | 1 failed | r2 fill (a) |
| equity check before the sides filter | 1 failed | r2 long-only exhausted |
| data_flags elements not type-checked | 1 failed | r2 data_flags |
| `from sochron.timebase.convert import ZoneInfo` for the rollover instant | 1 failed | r2 AC-06: `line 17: forbidden ZoneInfo import`, `line 175: forbidden ZoneInfo reference` (the round-1 AC-06 test passes it) |
| M15 time_utc not checked | 1 failed | r2 M15 time_utc |
| sides elements not type-checked | 1 failed | r2 sides |
| Result.trades and Result.skips as lists | 1 failed | r2 tuples |
| added: zone ignored (New York), rollover.at kept | 1 failed | r2 nights (c) |
| added: zone kept, rollover.at ignored (17:00) | 2 failed | r2 nights (b), (c) |

No round-1 test fails for any of these mutants, so each is caught only by round 2. In every mutant
run the origin check was clean.

### AST comparison against the round-1 working-tree files

Scratch `ast_compare.py` on byte copies of the three working-tree files (same SHA256 as the
round-1 table) and the round-2 files:
- test_backtest.py: 79 → 92 top-level statements; docstring only grew at its end (+939 chars);
  the 78 statements after it identical by `ast.dump` and in order; 13 added at the end
  (`_r2_scenario_data`, `_r2_run`, `_r2_mapping_wrong` and 10 `test_ac0n_r2_*` functions); none
  rebinds a round-1 name. No round-1 helper got a parameter: the round-2 helpers are new.
- backtest_cases.py: 38 → 42; docstring grew at its end (+306 chars); 37 identical; added
  `ROLLOVER_CASES`, `RAW_SHIFT_CASE`, `FILL_CASES_R2`, `SCENARIOS_R2`; none rebinds.
- test_imports.py: 75 → 82; docstring grew at its end (+347 chars); 74 identical; added
  `_ZONEINFO_NAME`, `_ZONEINFO_ADDED`, `_inspect_backtest_zoneinfo_source`,
  `_inspect_as_backtest_zoneinfo`, `_BACKTEST_ZONEINFO_FORBIDDEN`, `_BACKTEST_ZONEINFO_ALLOWED`,
  `test_ac06_r2_core007_backtest_never_names_zoneinfo`; none rebinds. `_inspect_backtest_source`
  and the round-1 AC-06 test are unchanged, so the round-1 test keeps its meaning.

### Findings answered

| Review finding | Round 2 |
|---|---|
| F1 Medium | ROLLOVER_CASES (a), (b) as the review, (c) added |
| F2 Low | SCENARIOS_R2 R_first_minutes_missing as the review, R_exit_minute_missing added |
| F3 Low | contract v1.5 item 1 (explicit stdlib list); no test change |
| F4 Low | FILL_CASES_R2 (a), (b) as the review |
| F5 Low | RAW_SHIFT_CASE as the review |
| F6 Low | `_inspect_backtest_zoneinfo_source` and test_ac06_r2_core007_backtest_never_names_zoneinfo |
| F7 Low | SCENARIOS_R2 R_exhausted_long_only (1); the data_flags TypeError test (2) |

### Open questions (left untested)

1. The ZoneInfo rule reports imports and references; it does not report a parameter, function or
   keyword-argument name ZoneInfo (a binding, not a use of the class). Should it?
2. The M15 time_utc check is an instant comparison (aware `!=`), so a time_utc with another
   zero-offset tzinfo is equal and accepted; untested either way.
3. sides mixing an unknown str with a non-str element (e.g. `{"buy", 1}`) is untested: the
   contract does not order TypeError against BacktestError, and such a set's iteration order
   depends on the hash seed. `{"long", 1}` (only the non-str element is wrong) is tested.
4. F5 relies on simulate_trade taking no rule and checking no time_utc (the contract lists none
   for it). If the contract ever gives simulate_trade a rule check, that test must be revisited.
5. Rollover.at inside a DST gap (e.g. 02:30 New York on 2026-03-08): `datetime.combine` with the
   zone's tzinfo uses fold 0; untested (as round-1 question 7).

### Implementer apply steps (CLAUDE.md, D-006)

1. On `feat/CORE-007-backtest`, with the three paths holding the round-1 files (blobs in the table
   above), run each as its own command: `git apply --check docs/proposals/CORE-007-tests-r2.patch`,
   then `git apply docs/proposals/CORE-007-tests-r2.patch`.
2. The post-run detector must report exactly the three paths. Verify every SHA256 (`sha256sum`) and
   Git blob (`git hash-object`) against the table of this section. Any mismatch, missing hash or
   other report: stop and ask the owner (N6).
3. Optional, standalone: `git apply -R --check docs/proposals/CORE-007-tests-r2.patch`.
4. `uv run --offline pytest tests -q -p no:cacheprovider` under an outer timeout: expected 3196
   tests, 103 failed, 3093 passed, every failure for the reasons in "Red".
5. A fresh-session narrow re-check of F1-F7 (the review's verdict), then commit the red tests of
   both rounds: `test(core-007): acceptance tests for CORE-007` with `Refs: CORE-007`.

### Checks run (command → result → commit → time UTC 2026-10-24)

- `sha256sum` and `git hash-object` of the three working-tree files → equal to the round-1 table
  → 7b70336 + round 1 → 04:3x
- `uv run --offline --no-sync python -I -B <scratch>/runner/check_golden_r2.py <scratch golden copy>`
  → 0 problems → 04:4x
- Red, satisfiability and mutants: as above (04:43, 04:50, 04:51)
- `uv run … python -I -B <scratch>/runner/ast_compare.py <base copy> <round-2 copy>` for each file →
  exit 0 each → 04:4x
- `git apply --check docs/proposals/CORE-007-tests-r2.patch` (standalone, repo root) → exit 0, no
  output → 04:4x; `git apply --numstat …` → 138/0, 272/0, 164/0
- `uv run … python -I -B <scratch>/runner/apply_check.py …` → the three in-memory results equal the
  round-2 files → 04:5x
- Red-flag patterns of `scripts/controls/red-flags.sh` over the 574 added lines of the patch → 0 hits
  in every group; the 3 `except Exception as error:` lines record the wrong exception and fail the
  test (the round-1 pattern) → 04:5x
- `git status --porcelain --untracked-files=all` before and after every run → unchanged (the three
  round-1 paths and this handoff); the only new file in the repository is the patch (ignored)
- Environment: Windows 11, Git Bash, Python 3.12.15, pytest 9.1.1, every pytest run under `timeout`

### Blocks and failures during this session

- After my first `git status`, the PostToolUse detector (check-locked-after) reported exactly the
  three round-1 targets (`M tests/architecture/test_imports.py`, `A tests/acceptance/CORE-007/test_backtest.py`,
  `A tests/golden/CORE-007/backtest_cases.py`, "protected files changed since the previous check"),
  which were applied before this session. Every SHA256 and blob matched the round-1 table, so I
  continued (CLAUDE.md, N6 condition). No guard-bash block occurred.
- My own mistake, not a hook block: a loop that counted CR bytes with `grep -c $'\r'` inside
  `"$(...)"` counted lines containing "r" instead; recounted with `tr -cd '\r' | wc -c` → 0 in all
  six files.

### Not verified

- The patch was not applied (by instruction); the red and green numbers come from the round-2
  copies run with the repository's pyproject, not from a patched tree.
- CI and Linux were not run; Python other than 3.12 was not run.
- The reference and the mutants prove satisfiability and sensitivity only; they stay in the
  session scratchpad and are not deliverables.
