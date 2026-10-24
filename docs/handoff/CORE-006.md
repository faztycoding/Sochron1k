# CORE-006 test-author handoff (acceptance, golden and architecture tests, red)

Date: 2026-10-24, about 00:0x-00:46 UTC (07:0x-07:46 Asia/Bangkok); times below are UTC.
Role: Claude Code (fresh session) in the Codex test-author role, under the owner's role swap (contract
Status line and D6; Codex out of quota until 2026-10-28 19:41). Not the implementer and not the reviewer
of CORE-006. The reviewer of these tests must be another fresh session (D6, AGENTS.md "maker and reviewer
are never the same session").
Contract: `docs/contracts/CORE-006-strategy-h001.md` v1, Tier Standard, approved 2026-10-23 15:0x (AC-01 to
AC-07, D1-D5 as recommended, D6 role swap); tests started on the CORE-005 branch by the owner's delegation of
2026-10-24 ~07:0x (Status line).
Inputs read: AGENTS.md, CLAUDE.md, the contract, `docs/hypotheses/H001-m15-momentum-breakout.md` (sections
1-4), `.agents/skills/write-acceptance-tests/SKILL.md` (as a plain procedure), HANDBOOK-CORE sections 4, 11
and 15, `docs/architecture.md` (module map rows, grep only), the public API of `sochron.core` (`Bar`),
`sochron.data.snapshot` (`AggregatedBar`, its flags, `validate_m1` defect codes, `aggregate`) and
`sochron.timebase` (`in_entry_window`, `NY_ENTRY_WINDOW`), the locked tests of CORE-005 and CORE-003 and
`tests/architecture/test_imports.py` for style, the CORE-005 handoff headings (format only),
`.claude/hooks/guard-bash.mjs` (patch rules only) and, after HEAD moved, the lines of
`docs/contracts/CORE-007-backtest.md` that mention `decide` (they agree with the conventions below). No
implementation of CORE-006 exists or was read.
Branch: `feat/CORE-006-strategy-h001` in the main checkout. HEAD was `b2ff122` at the start and
`0c2fb3f56387d7242a3f2c0d7a5b6e3b849b1c9e` at the end: the owner committed `0feef0e`, `eee3566` and
`0c2fb3f` (CORE-007 contract v1.1-v1.3 and its reviews, docs only) during this session. No CORE-006 file,
nothing under `src/` or `tests/` changed (`git diff --quiet b2ff122 HEAD --
docs/contracts/CORE-006-strategy-h001.md tests src`), and the base blob of the architecture file is the same.
Most runs below were made at `eee3566`; the apply check, the suite and the red summary were repeated at
`0c2fb3f` (00:48Z) with the same results.

Deliverables. Nothing was applied, staged, committed or pushed:
- `docs/proposals/CORE-006-tests.patch` (ignored by `.gitignore:10`; the D-006 patch)
- this file (untracked; the implementer commits it)

## The patch

| Item | Value |
|---|---|
| Patch | `docs/proposals/CORE-006-tests.patch` (1482 lines, 87855 bytes, 0 CR, ASCII only) |
| Patch SHA256 | `f43a98c05900d8df483616ad7c97264e515a2b394c36e75f88d1effb692d7558` |
| Built with | three `diff -u` runs in the scratchpad at 00:42:59Z, concatenated: `diff -u --label /dev/null --label b/tests/acceptance/CORE-006/test_strategy_h001.py /dev/null <scratch>`, the same for `b/tests/golden/CORE-006/strategy_cases.py`, and `diff -u --label a/tests/architecture/test_imports.py --label b/tests/architecture/test_imports.py <HEAD copy> <scratch>` |
| Scratch files | `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\df3b9695-b72a-4a4a-985b-19c805b307b6\scratchpad\work\tests\...` at their repository paths; the HEAD copy of the architecture file is `...\scratchpad\oracle\test_imports.base.py` (`git show HEAD:tests/architecture/test_imports.py`) |
| Base (required before apply) | `tests/architecture/test_imports.py` blob `1319cce4f673cd4df1ff73925265788cfbcffca1`, SHA256 `2d3d05d3814cacf7b41dab9f1fd774352b0e7e6a19ca4a2094d3f1c98aa3c3ac`, 1508 lines (the same at `b2ff122`, `eee3566` and `0c2fb3f`) |
| `git apply --check docs/proposals/CORE-006-tests.patch` | PASS: exit 0, no output, one standalone command from the repo root, at `eee3566` (00:43:28-00:43:54Z) and again at `0c2fb3f` (00:48Z). Never applied |
| `git apply --numstat --summary docs/proposals/CORE-006-tests.patch` | `1032 0` acceptance (create), `262 0` golden (create), `161 1` architecture |
| Independent result check | `...\scratchpad\oracle\check_patch_and_ast.py` rebuilds every target from the hunks of the patch in `docs/proposals/` with strict context matching (00:43:28Z): the three results are byte-identical to the scratch files and give the hashes below |
| Shape | 2 new files and 3 hunks in the architecture file: `@@ -11,7 +11,9 @@` (docstring), `@@ -42,6 +44,9 @@` (`_allowed_import`), `@@ -1506,3 +1511,158 @@` (strategy checker, tables and the AC-06 test, appended at the end) |

### Expected values after apply (LF, one trailing newline, no BOM, ASCII)

| File | Lines | Bytes | SHA256 | Git blob (`git hash-object --no-filters`; LF content, so the same as `--path=<repo path>`) |
|---|---|---|---|---|
| `tests/acceptance/CORE-006/test_strategy_h001.py` (new) | 1032 | 58307 | `982d29d13464a7221f703d29f642b67dcb819aeef7047b94a14063b17df0b74c` | `3c7664603f37362fa5805f4cdef6568c447395de` |
| `tests/golden/CORE-006/strategy_cases.py` (new) | 262 | 17094 | `c2330fa365e07df441a66382906cc0ed8a9da1327d3a64c65889a2fe33c7ae39` | `22a0876cff4f8c4c3688377e91dd967853f71aad` |
| `tests/architecture/test_imports.py` (changed) | 1668 | 82419 | `438e2999763097bfbd2831c1fb805a5c77627be8013129742eee980549b704a0` | `6d91a1e27cf20369ef49cc06594f9d9c6c65b18d` |

## Red summary against the current code (HEAD `eee3566`, no `src/sochron/strategy`)

The scratch files were run with pytest from the repository root, so the code under test is the repository's
`src/` (the tests prepend `Path.cwd() / "src"`) and the golden file is found next to the acceptance file:

| Run | Result | Why |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest <scratch acceptance file> <scratch architecture file> -q -p no:cacheprovider --tb=line` (00:43:54Z) | **142 failed, 13 passed in 0.92s**, 0 errors, 0 skipped | 141 acceptance tests: each calls `_api(...)`, which turns the ImportError into `pytest.fail("AC-xx: sochron.strategy not implemented (No module named 'sochron.strategy')")`: AC-01 4, AC-02 16, AC-03 27, AC-04 41, AC-05 51, AC-06 2. Architecture: the new `test_ac06_strategy_import_boundaries_no_io_clock_random_float_or_forbidden_package` fails at its line 1655, `AC-06: <repo>\src\sochron\strategy does not exist; implementation missing`, after its checker self-tests (lines before) passed. The 13 passing tests are the 13 existing architecture tests, unchanged |
| `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider` in the repository, unpatched (00:45:53Z) | **2876 passed in 6.85s**, 0 skipped | the existing suite; `git status --short --untracked-files=all` empty afterwards (the patch is ignored) |

After the apply, before the implementation, the whole suite should give **2876 passed, 142 failed** (3018
collected; the golden file is not a test module). After the implementation: **3018 passed, 0 skipped**.
Logs: `...\scratchpad\oracle\red_final.txt`.

## What the tests check, per AC

| AC | Tests (in `tests/acceptance/CORE-006/test_strategy_h001.py` unless noted) | What they prove |
|---|---|---|
| AC-01 | `test_ac01_params_accept_every_edge_and_keep_exact_values`, `..._out_of_range_or_breaking_a_constraint_raise_strategy_error`, `..._of_a_wrong_type_raise_type_error`, `test_ac01_defaults_match_the_h001_table_for_every_variant` | every edge of H001 section 4 accepted (s = 3f and M = N exactly, all-lower and all-upper sets), one unit beyond refused with StrategyError (int 1, theta 0.01, k 0.1, and a 0.0001 step), s < 3f and M > N refused, NaN/sNaN/Infinity refused, variant outside A/B/C refused; bool, float, int for Decimal, Decimal for int, str, None, Fraction and subclasses give TypeError; StrategyError is a ValueError, not a TypeError; frozen; `Variant` args; `H001_DEFAULTS` keys A/B/C with f16 s64 n20 theta 0.50 N96 M48 k2.0 and exact types |
| AC-02 | `test_ac02_indicators_match_the_hand_computed_golden_rows[S/P/G x A/B/C]`, `test_ac02_golden_rows_hold_under_a_hostile_caller_context[S/P/G]`, `test_ac02_warm_starts_exactly_at_the_d2_threshold_in_every_variant[97/3s-192/N+1-193/3s-99]`; golden `tests/golden/CORE-006/strategy_cases.py` | every field of every row of three hand-computed series (146 rows) in every variant, `IndicatorRow` field names and order, close/spread pass-through, empty lookback_flags, the same results under a caller context of precision 4, ROUND_UP and Inexact/Rounded traps, caller context unchanged; warm flips exactly at max(3s, N+1, M+1, 97, n+1) with each binding term |
| AC-03 | `test_ac03_h001_worked_example_enters_long_in_every_variant_with_stop_12`, `..._mirrored_worked_example_enters_short_...`, `test_ac03_threshold_crossings_and_breakout_edges[23 cases]`, `test_ac03_stop_distance_is_k_times_atr_at_precision_28_half_even`, `test_ac03_constants_and_every_action_carry_the_strategy_version` | the H001 example (TS 1.20 after 0.45, ATR 6.00, HH 4015.00, close 4016.30, 09:45 New York) gives enter_long with stop 12.00 in V-A, V-B and V-C, the mirror gives enter_short; ts = theta, ts[t-1] = theta, close = HH/LL, V-C with ts = 0, V-B ignores TS, V-A ignores Donchian, quiet rows give none; k x ATR rounded half-even at 28 digits (ties to 2 and to 8) also under a hostile caller context; STRATEGY_ID "H001", STRATEGY_VERSION "H001-v1", `Position` args, `Decision` fields, all six actions carry the version. Every decide call in the file also checks the Decision shape, the version and that the caller's context is unchanged |
| AC-04 | `test_ac04_exits_and_holds_in_every_variant[35 cases]`, `test_ac04_exit_and_hold_ignore_the_window_and_every_invalidation[6 blockers]` | V-A exits at ts <= 0 (long) and ts >= 0 (short, D5), including ts = 0 and the worked example's -0.10; V-B/V-C exit at close < LL_M / close > HH_M, equal holds; the opposite signal gives exit, never enter_*; a repeated same-side signal gives hold; ts unknown (ATR 0) never exits V-A (D4) while V-B/V-C Donchian exits still happen; exits and holds are the same outside the window, with the spread filter failing, spread or median unknown, defect flags, or all at once |
| AC-05 | `test_ac05_each_invalidation_alone_skips_with_its_reason[6 signals]`, `test_ac05_atr_zero_skips_a_breakout_and_unknown_ts_makes_a_ts_rule_false`, `test_ac05_several_invalidations_report_every_reason_in_contract_order[8]`, `test_ac05_new_york_window_edges_on_both_2026_dst_changes[28]`, `test_ac05_lookback_flags_cover_bars_t_minus_l_plus_1_to_t_by_variant`, `test_ac05_incomplete_alone_never_fills_lookback_flags`, `test_ac05_spread_unknown_inputs_reach_the_row_spread_and_median`, `test_ac05_known_answer_series_enters_only_on_its_known_bar[5]` | each reason alone for V-A/V-B/V-C long and short (outside_window, spread_filter at 721 > 3 x 240 and 722 > 3 x 240.5, spread_unknown for spread, median or both, data_flag, warmup at t 150 and 191) and the passing edges (720 = 3 x 240, 721 < 721.5, 723 = 3 x 241, 03:00 and 15:45 New York, t = 192); atr_zero for V-B; up to five reasons in contract order; 02:45/03:00/15:45/16:00 on Fri 03-06, Mon 03-09, Fri 10-30, Mon 11-02, plus the change days 03-08 and 11-01 with the non-existent 02:45 and the "wrong offset" traps, checked against `timebase.in_entry_window`; D3 windows of 97 bars (V-A) and 193 bars (V-B/V-C with N = 192) at both edges, every validation defect code, incomplete alone never counts; a missing spread reaches row.spread and makes the median None for exactly the 96 following rows; a 106-bar known-answer series through `indicators` and `decide` enters only on its known bars (V-B/V-C at t = 97 with stop 4.18, V-A at t = 102 with stop 3.8311682) and reacts to flags at t-L+1, t-L and t itself |
| AC-06 | `test_ac06_rows_and_decisions_at_t_ignore_every_bar_after_t`, `test_ac06_indicators_and_decide_are_deterministic_and_leave_inputs_untouched`; `tests/architecture/test_imports.py::test_ac06_strategy_import_boundaries_no_io_clock_random_float_or_forbidden_package` | with `random.Random(20261024)`, 240 random bars (missing spreads, incomplete and defect flags), 6 parameter sets (defaults and a small set, all variants) and 16 fixed plus 6 seeded random cut points: rows up to t and decide at t (flat/long/short, inside/outside the window) are equal whether bars after t are absent, present, or replaced by a different random tail at another price level; decide works on rows cut at t; results repeat and inputs are untouched. The architecture test checks its own checker first (29 forbidden sources with exact findings, granted imports, the timebase grant not leaking to core/costs/risk, every FIX-001/CORE-001 rule table) and then scans `src/sochron/strategy` |
| AC-07 | not a test-author item (suite and CI) | |

### Golden series (`tests/golden/CORE-006/strategy_cases.py`)

Parameters inside H001 section 4 with short alphas (f = 9: alpha 0.2; s = 39: alpha 0.05), N = 48, M = 24,
n = 10 (S, G) or 12 (P). Every EMA value is exact, so it does not depend on how the EMA recurrence is written
(open question 1). ATR and TS round by D1.
- S (12 bars): the EMA seed close[0] (bar 0 opens at 3999.00), TR[0] = high - low, true range with gaps up
  and down, the ATR seed (124 / 10 = 12.4) and two Wilder steps, TS rounded at 28 digits.
- P (14 bars, close constant): ATR seed 13/12 and two steps; per-operation rounding gives
  1.076388888888888888888888888 where rounding once would give ...889 (pins D1 "after each operation").
- G (120 bars, a 21:00-21:45 UTC gap): atr None before t = 9, ATR 0 at t = 9 (ts None, D4), both Donchian
  windows at both edges (bar 10's 4010/3990 leaves hh_m/ll_m at t = 35 and hh_n/ll_n at t = 59), bar t never
  inside its own HH/LL, the 96-bar median with an even count (247.5 + number of big new spreads), warm from
  t = 117, and an active zone with gap TRs and 28-digit TS values.
How the values were made: `...\scratchpad\oracle\compute_golden.py` (D1 Decimal, EMA computed in two forms
under an Inexact trap) and `crosscheck_fraction.py` (exact fractions rounded half-even by hand after each
operation): 0 mismatches on all 146 rows; `verify_golden.py` checks the literal tables against the oracle:
0 mismatches (00:3x). The arithmetic is written out in the golden file's comments.

## Conventions fixed where the contract leaves room (also in the acceptance file's docstring)

1. `StrategyError` is a public name of `sochron.strategy`. `H001Params`, `IndicatorRow` and `Decision` are
   frozen dataclasses whose fields are exactly the contract's names in the contract's order; tests build
   `IndicatorRow` by keyword and compare rows and decisions with `==`.
2. Wrong type is TypeError (float, bool, int for a Decimal field, Decimal for an int field, str, None, every
   subclass); a right type with a value outside H001 section 4 or a variant other than "A"/"B"/"C" is
   StrategyError, non-finite Decimals included. "One unit beyond" = 1 for ints, 0.01 for theta, 0.1 for k.
3. `atr` is None before t = n - 1; `ts` is None when `atr` is None or 0; hh_n/ll_n from t = N, hh_m/ll_m
   from t = M; TR for t >= 1 is the standard true range max(high - low, |high - close[t-1]|,
   |low - close[t-1]|) (H001 says "true range"; D2 writes only TR[0]).
4. `spread_median_96[t]` = mean of the 48th and 49th smallest of spread[t-96 .. t-1]; None while t < 96 or
   while any of those 96 spreads is None.
5. `lookback_flags` = the flags of bars t-L+1 .. t (D3 L per variant) without "incomplete"; empty when those
   bars carry only "incomplete"; whether "incomplete" is listed next to a defect is left open. Every
   validation defect code counts, WARN ones included (D3 "flag of a defect from validation").
6. `warm` = t >= max(3s, N+1, M+1, 97, n+1) for every variant (D2 does not exclude N, M for V-A; D3 does).
   Bars are counted as given, never by clock slots (contract plan item (c)).
7. `Decision`: skip carries every failed reason in the contract order and stop_distance None; enter_* has
   reasons () and stop_distance = k x atr[t]; exit, hold and none have reasons () and stop_distance None;
   spread_unknown replaces spread_filter when spread[t] or spread_median_96[t] is None; flat without an entry
   signal is "none".
8. D1 "context of the module": results never depend on the caller's Decimal context, and the caller's
   context (settings, traps, flags) is unchanged after `indicators` or `decide`.
9. D4: when ts[t-1] is unknown, "TS[t-1] <= theta" is false, so V-A has no crossing at t ("none").
10. The New York window uses `next_open_utc` through `timebase.in_entry_window` (contract); the DST table
    uses the change days themselves and the trading days next to them.

## Open questions (owner or reviewer)

1. **EMA recurrence and its rounding steps are not written.** D2 gives the seed and alpha only, and D1 says
   "round after each operation in the written order". With the defaults (alpha 2/17 and 2/65) the forms
   `alpha*c + (1-alpha)*e` and `e + alpha*(c-e)` differ in the last digits, so two people can still compute
   different TS digits. Recommended: write `EMA_p[t] = alpha * close[t] + (1 - alpha) * EMA_p[t-1]` with
   alpha = 2/(p+1) rounded once in the module context, then a golden case with the defaults can be locked.
   The current golden avoids the question (exact alphas).
2. `atr` before t = n - 1: the contract types `atr` as Decimal; the tests require None (convention 3).
3. A missing spread inside the 96 bars: the tests make the median None (spread_unknown for the next 96
   bars). The alternative, a median of the known spreads, would make the negative case "spread empty in the
   96 bars" a non-event. Please confirm.
4. Practical effect of D3 as approved (no test change proposed): WARN flags (`missing_spread`,
   `unexpected_gap`) block entries for L bars (97 or more, about one trading day), and an M15 bar whose last
   M1 has no spread always carries `missing_spread`, so in real data spread_unknown never comes alone. Worth
   measuring in SLICE-R1's data validation before trusting trade counts.
5. H001's invalidation "inside a period that data validation marks STOP" has no reason code in the contract.
   `data_flag` sees only per-bar flags inside the lookback; a STOP or UNKNOWN day status without a flagged bar
   in the window (for example `empty_weekday`, which has no bar time) is invisible to `strategy`. Is this left
   to CORE-007/SLICE-R1, or should the contract add it?
6. No entry signal during warm-up: "none" or skip("warmup")? Untested (CORE-007 logs skips, so it changes the
   Skip log).
7. V-A/V-C entry when atr[t] = 0: D4's "rules using TS are false" suggests "none", its "entry gets skip with
   atr_zero" suggests skip. Untested. Note that `atr_zero` is reachable only with constructed rows: a Wilder
   ATR of 0 needs every TR since the seed to be 0, and then no breakout or TS signal exists.
8. Wrong argument types for `indicators()`/`decide()`, an unknown position string and t out of range are not
   in the ACs and are untested. `strategy` may not import `sochron.data.snapshot`, so an exact
   `AggregatedBar` type check would need another way.
9. Exits during warm-up are untested (a backtest cannot hold a position then).

## Satisfiability (contract-only scratch reference)

`...\scratchpad\ref\src\sochron\strategy\` (`__init__.py`, `params.py`, `indicators.py`, `h001.py`, written
from the contract only) next to a copy of the committed `src/sochron` tree (`git archive HEAD src`). Runner
`...\scratchpad\ref\run_satisfiability.py`, run from that folder:
`PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline --no-sync --project <repo> python -I -B run_satisfiability.py <repo> <scratch acceptance file> <scratch architecture file>`
(00:44:07Z): **155 passed in 1.34s** (141 acceptance + 14 architecture), exit 0. The runner prints the origin of
every `sochron` module before and after pytest: the 4 `sochron.strategy*` modules come from the scratch
reference, the 13 others from the scratch copy and each is byte-identical (SHA256) to the repository file;
"module origin problems: none". Log: `...\scratchpad\oracle\green_final.txt`.

## Mutation evidence (scratch only)

`...\scratchpad\oracle\mutants.py` copies the reference, applies one textual mutation (each must match exactly
once) and runs the same tests (00:44:19-00:45:47Z): **44 of 44 mutants killed**, 0 survivors. Mutants: HH
includes bar t; EMA seed = open; TR ignores gaps; TR[0] = 0; ATR seed / (n-1); precision 34; ROUND_HALF_UP;
median window includes t; median skips None; spread filter >=; V-A previous < theta; V-B close >= HH; V-A exit
strict; opposite signal reverses; lookback ignores the variant; incomplete counts; warm-up without 97; decide
reads row t+1; indicators read bar t+1; caller's context in indicators; reasons out of order; window at a
fixed EST offset; `import random`; import of `sochron.data.snapshot`; no s >= 3f; isinstance type checks;
theta/k upper edge exclusive; V-C ignores TS; no atr_zero; TS 0 when ATR 0; stop from the previous ATR; alpha
2/p; V-B entry on HH_M; V-B exit on LL_N; low median; decide ignores warm-up; skip without a signal; lookback
excludes bar t; lookback one bar short; decide in the caller's context; median unknown not reported; default k
2.5; V-A short exit on ts > 0; ATR 0 instead of None before the seed. An earlier run found one survivor (EMA
seed = open), because bar 0 of series S opened at its close; bar 0 now opens at 3999.00 (no indicator reads
the open, so no expected value changed). Log: `...\scratchpad\oracle\mutants_final.txt`.

## AST comparison of the architecture file (`...\scratchpad\oracle\check_patch_and_ast.py`, 00:43:28Z)

HEAD (`git show HEAD:tests/architecture/test_imports.py`) against the patched file:
- module docstring: the HEAD text is a prefix of the new text (three sentences appended about CORE-006);
- top-level statements after the docstring: 52 at HEAD, 51 AST-identical, 1 changed: `_allowed_import`,
  which gains exactly one statement, `if package == 'sochron.strategy' and _within(name, 'sochron.timebase'):
  return True`; without it the function is AST-identical to HEAD (the new branch fires only for the strategy
  package, and the new test proves core, costs and risk still may not import timebase);
- appended after them: `_inspect_strategy_source`, `_inspect_as_strategy`, `_STRATEGY_FORBIDDEN`,
  `_STRATEGY_ALLOWED`, `test_ac06_strategy_import_boundaries_no_io_clock_random_float_or_forbidden_package`;
- assert statements: 21 at HEAD, all present unchanged; 4 added; test functions 13 -> 14, none removed.
`_PURE_CHECKERS` and every existing table are untouched; the new test runs those tables through the strategy
checker itself.

## Checks run (command -> result -> commit -> time)

| Command | Result | Commit | Time (UTC) |
|---|---|---|---|
| `git apply --check docs/proposals/CORE-006-tests.patch` (standalone) | PASS, exit 0, no output | `eee3566`, `0c2fb3f` | 00:43:28-00:43:54Z, 00:48Z |
| `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider`, then the red run (`--tb=no`) | PASS 2876 passed; red 142 failed, 13 passed (unchanged) | `0c2fb3f` | 00:48:49-00:48:58Z |
| `git apply --numstat --summary docs/proposals/CORE-006-tests.patch` (standalone rerun, see Blocks) | 2 creates, 1032/262/161+1- | `eee3566` | 00:43-00:44Z |
| red run of the scratch files from the repo root (command above) | FAIL as intended: 142 failed, 13 passed, all failures for the missing module or directory | `eee3566` | 00:43:54Z |
| `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: 2876 passed, 0 skipped | `eee3566` | 00:45:53Z (also 00:29:03Z and 00:40:28Z) |
| satisfiability runner (command above) | PASS: 155 passed, module origins proven | `eee3566` | 00:44:07Z |
| `mutants.py` (44 mutants) | PASS: 44 killed, 0 survivors | `eee3566` | 00:44:19-00:45:47Z |
| `check_patch_and_ast.py` (patch rebuild and AST comparison) | PASS: 3 files byte-identical, AST as above | `eee3566` | 00:43:28Z |
| `compute_golden.py`, `crosscheck_fraction.py`, `verify_golden.py` | PASS: 0 mismatches on 146 rows | `eee3566` | 00:3xZ |
| red-flag patterns of `scripts/controls/red-flags.sh` applied to the 1455 added lines of the patch | 0 hits (skip/only/xfail, type or lint disables, placeholder words, swallowed errors, secrets, destructive commands) | `eee3566` | 00:4xZ |

## Blocks and incidents

- **guard-bash block (00:43-00:44Z):** `date -u ...; git apply --numstat --summary docs/proposals/CORE-006-tests.patch`
  was blocked: "git apply must be one standalone literal command. Run each action separately." Rerun alone under
  the owner's standing "standalone rerun" exception (memory `stop-and-ask-on-every-block`); it is inspect-only.
- Not blocks: a bash heredoc that appended to the scratch architecture file failed with a bash parse error
  ("unexpected EOF while looking for matching `''", no hook involved), so the same text was appended with the
  Edit tool to the scratch file; GNU tar read `C:` as a host name until `--force-local`; the Write tool saved
  scratch files with CRLF, normalized to LF by `...\scratchpad\oracle\to_lf.py` before any run.
- HEAD moved during the session (owner's CORE-007 doc commits, see the top); nothing under CORE-006 changed.
- No post-run detector report was seen (nothing locked was written).

## Not verified

- The tests have not run from their final repository paths (only from the scratch mirror with the same layout)
  and not on the Linux CI runner; after the apply, run them in place.
- CORE-005 is not merged. If `Bar`, `AggregatedBar` or the defect codes change before its merge, merge and
  re-run these tests (contract Status line).
- No fresh-session review of these tests yet.
- Speed on about 170,000 M15 bars is not an acceptance test (the contract gives it to a unit test).

## Implementer's apply steps (Claude, D-006)

1. On `feat/CORE-006-strategy-h001` with a clean tree, check the inputs: `sha256sum docs/proposals/CORE-006-tests.patch`
   = `f43a98c05900d8df483616ad7c97264e515a2b394c36e75f88d1effb692d7558` and
   `git rev-parse HEAD:tests/architecture/test_imports.py` = `1319cce4f673cd4df1ff73925265788cfbcffca1`.
2. `git apply --check docs/proposals/CORE-006-tests.patch` as one standalone command.
3. `git apply docs/proposals/CORE-006-tests.patch` as one standalone command (D-006).
4. The post-run detector should report exactly the three target files. Verify each SHA256 (`sha256sum <path>`) and
   Git blob (`git hash-object --path=<path> <path>`) against the table above. Any mismatch, missing hash or other
   report: stop and ask the owner (N6).
5. `git apply -R --check docs/proposals/CORE-006-tests.patch` as one standalone command should now pass.
6. Run `uv run --offline pytest tests -q -p no:cacheprovider`: expect 2876 passed, 142 failed, every failure
   "sochron.strategy not implemented" or the missing `src/sochron/strategy` directory.
7. Fresh-session review of the applied tests (not this session, not the implementer's session).
8. Commit red: only the three test files and this handoff, `test(strategy): acceptance tests for CORE-006`,
   body `Refs: CORE-006`.
9. Implement `src/sochron/strategy/**` without touching the locked files. From the contract (not from code):
   `strategy` may import only `sochron.core`, `sochron.timebase` and side-effect-free stdlib, so `indicators()`
   reads `.bar` and `.flags` of the items without importing `AggregatedBar`; every Decimal operation, the stop
   distance included, runs in the module's own context; no float names or literals and no `random`.

## Please look hard at (fresh-session reviewer)

- Conventions 3 to 7 and question 3 (spread median with a missing spread), which the contract leaves open.
- The D4 consequence test (ts[t-1] unknown gives "none" in V-A).
- The known-answer series: V-A crosses theta at t = 102 by about 0.004-0.005, which no 28-digit rounding of the
  EMA can move; check the TS path in the comment (computed with exact fractions).
- The DST table for 2026-03-08 (02:45 New York does not exist; 01:45 EST is the last bar before 03:00 EDT).
- One architecture test holds both the checker self-tests and the package scan, so that it fails, rather than
  passes silently, while `src/sochron/strategy` is missing.

## Round 2 patch (tests-r1 F1-F4)

Date: 2026-10-24, about 01:20-01:50 UTC (08:20-08:50 Asia/Bangkok); times below are UTC.
Role: Claude Code, a fresh session in the Codex test-author role for round 2 (owner's role swap, contract Status
line). Not the implementer, not the round-1 test author and not a reviewer of CORE-006. The reviewer of this
patch must be another fresh session (D6). The owner delegated every decision to the recommended option
(2026-10-24); the task fixed F1-F4 as the review proposes, with the F4 stdlib list given exactly.
Inputs read: AGENTS.md, CLAUDE.md, `.agents/skills/write-acceptance-tests/SKILL.md` (as a plain procedure), the
contract (v1 and the v1.1 block), `docs/reviews/CORE-006-tests-r1.md`, the sections above, the three committed
test files, the public API of `sochron.core.Bar`, `sochron.data.snapshot.model.AggregatedBar` and
`sochron.timebase` (`in_entry_window`, `check_aware`), `scripts/controls/red-flags.sh` (its patterns) and
`.claude/hooks/guard-bash.mjs` (its write and inline-code rules). No other session's reference, oracle or
mutant script was read; `src/sochron/strategy` does not exist.
Branch `feat/CORE-006-strategy-h001`, HEAD `a1c5188fd06d40dd50c11f344b3f6675ea581cb0` for the whole session;
`git status --short --untracked-files=all` empty before and after (the patch is ignored by `.gitignore:10`).
Deliverables: `docs/proposals/CORE-006-tests-r2.patch` and this section. Nothing was applied, staged, committed
or pushed. The patch is incremental: it applies on top of the round-1 files committed in `a1c5188`.

### The patch

| Item | Value |
|---|---|
| Patch | `docs/proposals/CORE-006-tests-r2.patch` (655 lines, 41563 bytes, ASCII only, 0 CR) |
| Patch SHA256 | `51ecc15e4affe075152c76655fde79437daa22d3e8860c5697d3b4be9f8ec27d` |
| Built with | three runs from the repo root at 01:43:54Z, concatenated (`>` then `>>` twice): `diff -u --label a/<path> --label b/<path> <path> <scratch>\work\tests\<same path>` for the acceptance, golden and architecture files in that order; each exits 1 (files differ) |
| Scratch | `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\c7266eaa-7f1e-4335-bbb8-6dfa44dc7bae\scratchpad\`: `base\` (`git show HEAD:<path>`), `frag\` (docstring edits and appended sections), `work\tests\...` (the results at repository paths, made by `oracle\build_files.py`), `sat\src\` (`git archive HEAD src` plus the scratch reference), `oracle\` (scripts and logs) |
| Base required before apply | acceptance blob `3c7664603f37362fa5805f4cdef6568c447395de` (SHA256 `982d29d13464a7221f703d29f642b67dcb819aeef7047b94a14063b17df0b74c`), golden blob `22a0876cff4f8c4c3688377e91dd967853f71aad` (`c2330fa365e07df441a66382906cc0ed8a9da1327d3a64c65889a2fe33c7ae39`), architecture blob `6d91a1e27cf20369ef49cc06594f9d9c6c65b18d` (`438e2999763097bfbd2831c1fb805a5c77627be8013129742eee980549b704a0`): the round-1 values. `cmp` shows the working tree byte-identical to `git show HEAD:` for all three |
| `git apply --check docs/proposals/CORE-006-tests-r2.patch` | PASS: exit 0, no output, one standalone command from the repo root (about 01:44Z). Never applied |
| `git apply --numstat --summary docs/proposals/CORE-006-tests-r2.patch` (standalone) | `268 6` acceptance, `178 7` golden, `143 1` architecture; no create, delete or mode line |
| Shape | acceptance `@@ -20,18 +20,23 @@` (docstring) and `@@ -1030,3 +1035,260 @@` (appended section); golden `@@ -3,7 +3,9 @@` and `@@ -15,12 +17,15 @@` (docstring) and `@@ -260,3 +265,169 @@` (series E); architecture `@@ -13,7 +13,8 @@` (docstring) and `@@ -1666,3 +1667,144 @@` (appended checker, tables and test) |
| Independent result check | `oracle\check_patch.py` rebuilds each target from the hunks of the patch in `docs/proposals/`, with strict context and line counts, against the HEAD copies (01:44-01:45Z): all three byte-identical to the scratch files, with the hashes below |

### Expected values after apply (LF, one trailing newline, no BOM, ASCII)

| File | Lines | Bytes | SHA256 | Git blob (`git hash-object --no-filters`; LF content, so the same as `--path=<repo path>`) |
|---|---|---|---|---|
| `tests/acceptance/CORE-006/test_strategy_h001.py` | 1294 | 74142 | `9b9859467ddf15c44f51bfd387afa5db1b1b114b8ae02cf1514a265636c9882a` | `ef61bef67c0e2084ef5b1c6dd7ca0d710f83f494` |
| `tests/golden/CORE-006/strategy_cases.py` | 433 | 28413 | `831ccd8521b0cfe299d6835da3b2940669abee89bf1546ccd6e28f83c41b298d` | `9e9dadf5dd520dd8a9564af7b81010dc4c29d201` |
| `tests/architecture/test_imports.py` | 1810 | 90912 | `e0f1cc4f8ebdc4ef7c46280f8edd4f2087b60f7b4b3397566eff94265493cca4` | `504c88a6c4e9af40b288f1665fc15639485d654d` |

### What each finding gets (all new tests are appended; no existing test changed)

| Finding | New tests (acceptance file unless noted) | What they prove |
|---|---|---|
| F1 | `test_ac02_v11_default_alphas_pin_the_ema_form_and_its_rounding[A/B/C]`; golden `PARAMS_E`, `BARS_E`, `ROWS_E`, `EMA_TRAPS_E` | 26 bars with the defaults (f 16, s 64, n 20, N 96, M 48): every field of every row, `ema_f`/`ema_s` at 28 digits from t = 1 and `ts` from t = 19, under the module context and a hostile caller context. The v1.1 form already differs at t = 1 from e + alpha(c - e), from one rounding per step with exact alpha, and from one rounding per step with 28-digit alpha: both v1.1 sums at t = 1 end in exact ties that half even rounds down (...764 and ...230 against ...765 and ...231 for all three wrong forms). Over the series the wrong forms differ in 24 of 25 EMA_16 rows, 21-25 of 25 EMA_64 rows and all 7 ts rows. The test also asserts that every `EMA_TRAPS_E` value (the wrong forms at t = 1, 2, 19, 25) differs from the golden row, so the case cannot become vacuous |
| F2 item 5 | `test_ac05_v11_no_entry_signal_during_warm_up_is_none_never_skip[15 AC-03 edges without a signal]`, `test_ac05_v11_known_answer_series_gives_none_before_its_first_signal[5 flag cases]` | flat, rows not warm, no entry signal: none at t = 150 and 191, also with each AC-05 invalidation (window, spread filter, spread or median unknown, flags). On the known-answer series, every variant gives none at t = 0..95, and V-A also at t = 96 |
| F2 item 6 | `test_ac05_v11_atr_zero_gives_none_in_v_a_and_v_c_and_skips_a_v_b_breakout` | ts None and ATR 0 give none for: V-C breakout and breakdown; V-A after 0.45, after -0.45, and after 0.30 with a Donchian breakout; V-A with ATR 0 at t and t - 1. V-B breakout and breakdown skip with atr_zero; V-B without a breakout gives none. With every other check failing too: still none, or skip with all five reasons for V-B |
| F2 item 8 | `test_ac04_v11_exit_rules_apply_while_the_rows_are_not_warm[35 AC-04 cases]`, `test_ac04_v11_known_answer_series_exits_before_warm_once_the_indicators_exist` | every AC-04 exit or hold case gives the same action when the rows are not warm (t = 20 and 150). Through `indicators()`: V-A holds while ts is None (t < 9) and exits a long and a short at ts = 0 (t = 9..95); V-B and V-C hold; at t = 96 a short exits (V-B/V-C: close 4002 > HH_24 = 4001; V-A: ts > 0) and a long holds |
| F3 `decide` | `test_ac03_v11_decide_refuses_unknown_positions_t_out_of_range_and_wrong_types` | StrategyError: positions "Long", "LONG", "", "none", "buy", "flat ", " short"; t = -1, -2, -len, -len - 1, len, len + 1. Here rows[-1] is a breakout, so reading it would enter. t = 0 works and reads no row t - 1: a V-A ts 1.20 at t = 0 with rows[-1] at ts 0.45 gives none. TypeError: t True, False, an int subclass, Decimal, float, str, None; position None, 1, True, bytes, a str subclass, a tuple; next_open_utc None, an ISO string, an int, a date, a datetime subclass; params None, a dict, "B", `H001_DEFAULTS`, an `H001Params` subclass; rows None, 5, a dict; row t None, an attribute copy, a tuple |
| F3 `indicators` | `test_ac02_v11_indicators_accept_duck_typed_m15_bars_and_refuse_wrong_types` | on 230 seeded random bars with flags, test-local objects with `.bar`/`.flags` (all of them, or mixed with `AggregatedBar`) give the same rows as `AggregatedBar` in A, B and C. TypeError: a bare `core.Bar`; no `.flags`; no `.bar`; `.bar` None, an attribute copy, a dict or a `Bar` subclass; `.flags` a set, tuple, list, str, None or frozenset subclass; bars None, 5 or a single bar; params None, a dict, "B", `H001_DEFAULTS` or an `H001Params` subclass |
| F4 | `tests/architecture/test_imports.py::test_ac06_r2_strategy_imports_only_listed_stdlib_modules_core_timebase_and_itself`; `_STRATEGY_STDLIB`, `_inspect_strategy_listed_source`, `_inspect_as_listed_strategy`, `_STRATEGY_UNLISTED`, `_STRATEGY_LISTED` | exact findings `line N: forbidden stdlib import X` for: logging (plain, a submodule, from-imported); sqlite3 (plain, aliased); threading; asyncio (also inside a function); shutil; pathlib; three in one statement; `from os import path`; math; zoneinfo; `__future__`; one next to a round-1 finding. No finding for each listed module (plain, aliased, from-imported, inside a function) or for core, timebase and the package itself. On every shared table the new checker keeps every round-1 strategy finding and adds only stdlib-import findings. Then it scans `src/sochron/strategy`, which must exist |

### Decisions where the task or the contract leaves room

1. **F4 is a new checker next to the round-1 one; `_inspect_strategy_source` is unchanged.** Changing that function
   in place would change the exact expected findings of 9 `_STRATEGY_FORBIDDEN` rows: their `time`, `pathlib`, `os`,
   `subprocess`, `socket`, `http.client` and `random` import lines would each gain a finding. It would also make
   `_STRATEGY_ALLOWED` (`import math`) and `_LEGITIMATE_SOURCES` (`sys`, `time`, `zoneinfo`) report findings.
   Existing asserts would then fail or change meaning. Both strategy tests scan the package; the round-2 one is
   strictly stronger. `_allowed_import`, `_PURE_CHECKERS` and every other package's checker are untouched.
2. **The list is exact, as given:** bisect, collections, collections.abc, dataclasses, datetime, decimal, enum,
   functools, itertools, operator, types, typing. `math`, `zoneinfo`, `re`, `sys`, `fractions`, `statistics`,
   `__future__` and every other stdlib module are findings for strategy. Names count in full: `collections.abc` is
   listed, `logging.handlers` and `os` (`from os import path`) are not. `_STRATEGY_ALLOWED` still shows
   `import math` as legitimate for the round-1 checker; the round-2 checker reports it, and one of its rows says
   so. **Implementer:** no `from __future__ import annotations`, `import math` or `zoneinfo` (use
   `sochron.timebase`) in `src/sochron/strategy`.
3. **F3:** a wrong type is TypeError, subclasses included (contract line 35), so a `datetime`, `frozenset`, `Bar` or
   `H001Params` subclass is refused; `rows` must be a sequence (a dict is refused). Only the type of row t is
   tested, because `decide` need not read row t - 1. t = 0 is valid and has no row t - 1 (D4: unknown, so no V-A
   crossing).
4. **F2:** items 5 and 6 are read as "without an entry signal, none, whatever else fails". The invalidations apply
   to an entry (contract rules), as in convention 7.
5. **Item 8 on rows from `indicators()`:** ts is exactly 0 at t = 9..95 of the known series because every close is
   4000.00. Under v1.1 both EMAs stay 4000: for EMA_8, 888.8888888888888888888888888 + 3111.111111111111111111111111
   = 3999.9999999999999999999999998, which rounds to 4000.000000000000000000000000. The wrong EMA forms stay at 4000
   too, so this test does not depend on F1.

### AST comparison against `git show HEAD:` (`oracle\ast_compare.py`, 01:40Z, repeated after the last edit)

- Acceptance: the module docstring changed. 6 lines were replaced by 11: the golden-EMA sentence and the "Left
  untested" paragraph now name v1.1 and tests r2. The 82 HEAD statements after it are AST-identical and in order at
  the start of the file, and 12 statements are appended. Every HEAD assert is unchanged in its function. Test
  functions go from 24 to 32, none removed.
- Golden: the docstring changed. The D2 line gained the v1.1 form, and the "every EMA value is exact" paragraph is
  limited to S, P and G with a series E sentence added. The 18 HEAD statements are identical; 5 are appended
  (`PARAMS_E`, `_E`, `BARS_E`, `ROWS_E`, `EMA_TRAPS_E`). The file has no asserts.
- Architecture: in the docstring, the last line is extended and one line added; the HEAD text without its final
  line break is a prefix. The 57 HEAD statements are identical, 6 are appended, and the 25 HEAD asserts are
  unchanged with 4 added. Test functions go from 14 to 15.
- **Asserts changed: none.** No statement other than the three docstrings changed. No skip, xfail, importorskip
  or placeholder. All three files are ASCII with LF, one trailing newline and no tabs or trailing spaces. The
  longest lines are 113, 103 and 108, the same as at HEAD.

### Red, satisfiability and mutants (command -> result -> commit -> time)

| Check | Result | Commit | Time (UTC) |
|---|---|---|---|
| Red: `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest <scratch acceptance> <scratch architecture> -q -p no:cacheprovider --rootdir <scratch>\work --tb=line` from the repo root (the tests read the repository's `src`, which has no `strategy`) | FAIL as intended: **205 failed, 13 passed** in 0.99 s. 203 acceptance tests fail with "AC-0x: sochron.strategy not implemented (No module named 'sochron.strategy')" (AC-01 4, AC-02 20, AC-03 28, AC-04 77, AC-05 72, AC-06 2). Both strategy scans fail at "...\src\sochron\strategy does not exist; implementation missing" (lines 1656 and 1796), after their checker self-tests passed. The 13 passes are the existing architecture tests. 63 of the failures are round-2 tests and 142 are round 1. The same counts came from `--tb=no -rf` at 01:42:32Z. Logs `oracle\red_final_line.txt`, `oracle\red_final.txt` | `a1c5188` | 01:43:04-01:43:05Z |
| Repository suite, unpatched: `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider` | 142 failed, 2876 passed (the committed red state). Expected after the apply: **2876 passed, 205 failed** (3081 collected). Expected after the implementation: 3081 passed, 0 skipped | `a1c5188` | 01:43:16-01:43:23Z |
| Satisfiability: `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline --no-sync python -I -B oracle\run_sat.py <scratch>\sat <repo> <scratch>\work <acceptance> <architecture> -- --tb=short` | PASS: **218 passed** in 1.95 s (155 round 1 + 63 round 2). "module origin problems: none" before and after pytest: the 4 `sochron.strategy*` modules come from the scratch reference, and the 13 others are byte-identical (SHA256) to the repository's `src`. The round-1 files alone gave 155 passed (about 01:31Z). Log `oracle\green_final.txt` | `a1c5188` | 01:41:20-01:41:22Z |
| Mutants: `oracle\mutants.py` (table below) | PASS: **22 of 22 killed, each only by round-2 tests** (round-1 tests: 0 failures in every run); origins clean in every run. Log `oracle\mutants_final.txt` | `a1c5188` | 01:41:26-01:42:15Z |
| `git apply --check docs/proposals/CORE-006-tests-r2.patch` (standalone) | PASS, exit 0, no output | `a1c5188` | about 01:44Z |
| `oracle\check_patch.py` (rebuild from the hunks) and `sha256sum`, `git hash-object --no-filters` | PASS: 3 files byte-identical; hashes as tabled | `a1c5188` | 01:44-01:45Z |
| Red-flag patterns of `scripts/controls/red-flags.sh` on the added lines of the patch (Grep tool; placeholder words case-insensitive) | 0 hits in every group: skip/only/xfail, type or lint disables, placeholder words, swallowed errors, secrets, secret-like values, destructive commands, client-exposed names, the order/account surface. The filter matches added lines (11 hits for `pytest.raises` as a control) | `a1c5188` | about 01:45Z |

**Reference.** `sat\src\sochron\strategy\` (`__init__.py`, `params.py`, `indicators.py`, `h001.py`) is my own code,
written in this session from the contract and v1.1 only. It imports only listed stdlib modules, `sochron.core` and
`sochron.timebase`.

**Runner.** `run_sat.py` puts `sat\src` first on `sys.path` and imports `sochron` before pytest. It makes `sat` the
cwd, because the tests read `Path.cwd() / "src"`, and runs the scratch test files with `--rootdir` set to the
scratch work folder. No pytest.ini, pyproject.toml, tox.ini or setup.cfg exists above the scratch folder; I checked.

**Golden E.** The values come from `oracle\frac28.py` and `oracle\gen_golden_e.py`. They use exact fractions and
my own half-even rounding to 28 digits after each operation, with no `decimal` module. Before use, the oracle
reproduced known round-1 values: 13/12, the ATR of series P, TS of series S at t = 9, and the four alphas. The
series was chosen by `oracle\search_e.py` (seed 398). The Decimal reference, a second method, reproduces every
row in A, B and C under both contexts, as the satisfiability run shows. The comments in the golden file write out
the t = 1 and t = 2 steps, the ties, the wrong forms at t = 1, the ATR seed and steps, and TS[19].

| Mutant (one textual change to the reference) | Result: failed tests, all round 2 |
|---|---|
| F1 EMA as e + alpha * (c - e) | killed: 3 (`..._default_alphas_...[A/B/C]`) |
| F1 EMA rounded once, exact alpha at precision 90 | killed: 3 (same) |
| F1 EMA rounded once, 28-digit alpha and 1 - alpha | killed: 3 (same) |
| F2 skip(warmup) on warm-up without a signal | killed: 22 (item-5 tests, the known-series none test, the ATR-0 test, the decide t = 0 check) |
| F2 skip(atr_zero) for a flat V-A row at ATR 0 | killed: 1 (ATR-0 test) |
| F2 V-C breakout with ts unknown counts as a signal (skip atr_zero) | killed: 1 (ATR-0 test) |
| F2 exits blocked before warm (hold) | killed: 16 (`..._exit_rules_apply_while_the_rows_are_not_warm[...]`, the known-series exit test) |
| F3 negative t reads rows from the end | killed: 1 (decide errors test) |
| F3 t - 1 wraps to the last row at t = 0 | killed: 1 (same) |
| F3 unknown position accepted (treated as flat) | killed: 1 (same) |
| F3 t of a wrong type accepted (`int(t)`) | killed: 1 (same) |
| F3 next_open_utc type not checked | killed: 1 (same) |
| F3 decide accepts an H001Params subclass (isinstance) | killed: 1 (same) |
| F3 decide accepts rows as a mapping | killed: 1 (same) |
| F3 decide accepts any object as row t | killed: 1 (same) |
| F3 duck typing refused (AggregatedBar by class name) | killed: 1 (duck-typing test) |
| F3 any bar-like `.bar` accepted | killed: 1 (same) |
| F3 a set of flags accepted | killed: 1 (same) |
| F3 indicators accepts an H001Params subclass (isinstance) | killed: 1 (same) |
| F4 an extra `import logging` in strategy | killed: 1 (`test_ac06_r2_...`) |
| F4 an extra `from pathlib import Path` in strategy | killed: 1 (same) |
| F4 an extra `import sqlite3` inside a function | killed: 1 (same) |

The 10 mutants that survived round 1 in review tests-r1 section 6 are all covered: both EMA forms, warm-up skip,
V-C ATR 0, no exit before warm, unknown position, negative t, any bar-like object and a set of flags, duck typing
refused, and t of a wrong type.

### Blocks and incidents

- **guard-bash block (about 01:30Z), a scratch-setup command.** It began with `S="<scratch>"; mkdir -p <literal
  scratch paths> && cp "$S/base/test_strategy_h001.py" "$S/basetree/tests/acceptance/CORE-006/" && ...` and was
  blocked: "Blocked by .claude/hooks/guard-bash.mjs: cp would write $S/basetree/tests/acceptance/CORE-006/ (a path
  that cannot be resolved here (variable or unknown directory)). Ask the owner."
  - Nothing in the command ran.
  - The cause was mine: a shell variable in a cp destination, against this session's rule to use literal paths.
  - I stopped that step and did not retry it in any form. The separate copy of the round-1 tests was only for
    baseline mutant runs, and it is not needed: the round-2 files contain every round-1 test unchanged, so each
    mutant run above already reports its round-1 failures.
  - The `printf '[pytest]\n' > ...` parts of the same command never ran either. Instead, I checked that no pytest
    config exists above the scratch folder and run pytest with `--rootdir` only.
  - The work tree was then built by `oracle\build_files.py`, which takes its paths as arguments and writes only
    under the scratch folder.
  - Owner: please confirm this handling, or say how to redo it.
- Not blocks: a bash heredoc garbled backslashes in a scratch tally script, so the script was written with the
  Write tool instead. `mutants.py` cuts parametrized test ids at the first space when it lists failures; the
  pytest summary counts in the table are exact.
- No post-run detector report was seen, because nothing locked was written.

### Not verified

- The round-2 files have not run from their final repository paths, only from the scratch mirror with the same
  layout. They have not run on the Linux CI runner either. After the apply, run them in place.
- No fresh-session review of round 2 yet.
- The checker is static. `exec("import logging")` and other string-built code are still not seen; `__import__`
  and `importlib.import_module` were already reported. A reviewer may want a separate finding.
- Left untested because the contract is silent: a frozenset of flags holding non-strings, a bar whose timeframe
  is not 15, a naive `next_open_utc`, flag strings that are not validation defect codes. Speed on about 170,000
  bars belongs to a unit test (contract).

### Implementer's apply steps (Claude, D-006)

1. On `feat/CORE-006-strategy-h001` with a clean tree, check the inputs. `sha256sum
   docs/proposals/CORE-006-tests-r2.patch` must be `51ecc15e4affe075152c76655fde79437daa22d3e8860c5697d3b4be9f8ec27d`.
   `git rev-parse HEAD:<path>` must give the three base blobs above: `3c766460...`, `22a0876c...` and `6d91a1e2...`.
2. `git apply --check docs/proposals/CORE-006-tests-r2.patch` as one standalone command.
3. `git apply docs/proposals/CORE-006-tests-r2.patch` as one standalone command (D-006).
4. The post-run detector should report exactly the three target files, modified. Check each SHA256
   (`sha256sum <path>`) and Git blob (`git hash-object --path=<path> <path>`) against the table above. Any mismatch,
   missing hash or other report: stop and ask the owner (N6).
5. `git apply -R --check docs/proposals/CORE-006-tests-r2.patch` as one standalone command should now pass.
6. `PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider` should give 2876
   passed and 205 failed. Every failure must be "sochron.strategy not implemented" or the missing
   `src/sochron/strategy` directory.
7. A fresh-session review of the round-2 tests: not this session, and not the implementer's.
8. Commit red: only the three test files and this handoff. Message `test(strategy): CORE-006 tests r2 for review
   tests-r1 F1-F4`, body `Refs: CORE-006`.
9. Implement within the stdlib list (decision 2). From the contract (not from code): bars are duck-typed, with
   exact type checks on `.bar` and `.flags`; `decide` checks its arguments (types, position, the range of t)
   before it reads a row.

## Findings response (implementation review r1, `docs/reviews/CORE-006-r1.md`)

The implementer (Claude, the planning session) answered every finding by accepting the reviewer's minimal fix, under
the owner's standing delegation of 2026-10-24 ~07:0x ("take the recommended option on every decision", veto before
merge). The fix shapes came from the reviewer, not from this session. Every regression check is in the implementer's
unit tests (`tests/unit/strategy/test_strategy_unit.py`); no locked file changed. Suite 3084 at review → 3093 passed.

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F1 | accept | `6b22b5b` | `negative_theta = theta.copy_negate()` (exact, no context). `pytest -k mirrors` failed before (`enter_short` expected, `none` returned) and passes after; suite 3085 passed |
| F2 | accept | `9338b46` | `decide` raises StrategyError("next_open_utc must be timezone-aware") right after the type check, for every position. `pytest -k naive` failed 6/6 before (flat, long, short × no signal, breakout) and passes after; suite 3091 passed |
| F3 | accept | `7055ea9` | Zero counts are deleted when a bar leaves the lookback; `lookback_flags = frozenset(flags)`. The test counts Counter keys with a subclass patched into the module (no timing): 600 keys before against a bound of L + 1 = 98, passes after. My first bound of L was off by one (bar t joins before bar t − L leaves); corrected before the commit and re-run on the old code (`git stash` of `indicators.py`): 600 > 98, fails. Probe with a new flag on every bar: 2,000 / 4,000 / 8,000 / 16,000 bars → 0.025 / 0.052 / 0.115 / 0.258 s; suite 3092 passed |
| F4 | accept | `52c8680` | New unit test at f = 22, s = 78 checks `ema_f` and `ema_s` row by row. The M2 mutant `keep_f = (f − 1)/(f + 1)` in a scratch copy of `src` (`pytest -c <scratch>/pytest.ini --rootdir . tests`) gives 1 failed (this test), 3092 passed; the real code gives 3093 passed |
| F5 | accept | `6f93f6e` | The tests-r2 F5 limitation is now in PROGRESS.md "Claude ถัดไป" item (ข); the evidence line points there and says the earlier claim was not on record. `grep -c "CORE-006 tests-r2 F5" PROGRESS.md` → 1 |

The reviewer re-checks only these IDs in the next round file (`docs/reviews/CORE-006-r2.md`). The implementer does not
close findings. The headless budget for this task is used up (5 of 5), so the re-check runs as the
`fresh-eyes-reviewer` subagent, a fresh context, the same pattern as CORE-004 r3 and CORE-005 r2.

Re-check r2 (`docs/reviews/CORE-006-r2.md`): F1–F5 closed, Ready for PR: yes, one new Low finding.

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F6 | accept | the `F6:` commit after `42f63bb` | `docs/evidence/CORE-006.md` AC-07 row, unit-test list, tests-r2 F6 line and delivery state now cite 3093 passed at `52c8680` and the r1/r2 reviews; the checks table has a row per fix, the re-check and the push. `PROGRESS.md` current-task line and "Next safe action" updated. `grep -n "3093" docs/evidence/CORE-006.md` → rows found |
