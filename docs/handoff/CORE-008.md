# Handoff CORE-008 · contract v1.5 · base commit 320c5cd (branch feat/CORE-008-research)

<!-- Facts only. No persuasion. The reviewer reads this AFTER writing the first round of findings. -->

Test-author handoff (tests r1). Author: a fresh Claude Code session acting as test author under the
role swap of contract D15 (Codex out of quota until 2026-10-28 19:41); headless session 1 of the
contract's budget of 6. This session is not the implementer and not a reviewer of CORE-008. It read
AGENTS.md, CLAUDE.md, contract v1.5 in full, H001 sections 3-9, docs/architecture.md section 8, the
merged code it calls (backtest, strategy, costs, timebase, core, data.snapshot), the locked
CORE-007 tests for style and, for the method only, docs/handoff/CORE-007.md. It wrote no
implementation in the repository and staged, committed, pushed and applied nothing. Written
2026-10-24 (UTC 08:2x).

## Deliverable

One D-006 patch, never applied by this session:
`docs/proposals/CORE-008-tests.patch` · 3622 lines · 221077 bytes ·
SHA256 `48d5915f41e6b3d9768d42606608511ece3c97968a85ef71a0739a158c450eb5`.
`docs/proposals/` is ignored by `.gitignore` line 10, so the patch is a local file, not a commit.

| Path after apply | Change | Lines (numstat) | Expected SHA256 | Expected Git blob |
|---|---|---|---|---|
| tests/acceptance/CORE-008/test_research.py | new | +2396 | `9817bb68fb57090f1069c61db3acc87ce2912373a040edcd83f9e69e5c1143a5` | `f1089df2c8fcee26d4b128d4718d87ce2f045f1f` |
| tests/golden/CORE-008/research_cases.py | new | +834 | `f896083d5826d34ae75ecd3dc2b9620c844ee03c7177198debed195322f16fa9` | `a711d15088ce45e4b5fe440e19d96a764c390b87` |
| tests/architecture/test_imports.py | changed | +373 −0 | `c17d17ec9ba9745b9f1ff4723dd68b00547170b5e58eb6b9dc191adb22a6ea93` | `1cc7287da76e876f27603d2c62923951c4b9a4c3` |

Base of the changed file: `tests/architecture/test_imports.py` at HEAD 320c5cd, blob
`6751aadfddc386420632668e83714785432dc4af`, SHA256
`b5964d1e3b91f2e6f78e3b22f82578110c0f55b40ab15debdc7cb5d5c6358d13` (the worktree file has the same
blob). The patch has no `index` lines, so check this base blob before applying. Each expected blob
was computed twice, `git hash-object --no-filters` and `git hash-object --path=<path>` (through
`*.py text eol=lf`): equal for all three, so the files are LF only; each ends with one newline and
has no trailing spaces (0 CR bytes counted with `tr`).

## Implementer apply steps (CLAUDE.md, D-006)

1. On `feat/CORE-008-research` with `tests/architecture/test_imports.py` at blob `6751aadf…` and the
   two new paths absent, run each as its own command:
   `git apply --check docs/proposals/CORE-008-tests.patch`, then
   `git apply docs/proposals/CORE-008-tests.patch`.
2. The post-run detector must report exactly the three paths above. Verify every SHA256
   (`sha256sum`) and Git blob (`git hash-object`) against the table. Any mismatch, missing hash or
   other report: stop and ask the owner (N6).
3. Optional, standalone: `git apply -R --check docs/proposals/CORE-008-tests.patch`.
4. Run `uv run --offline pytest tests -q -p no:cacheprovider` under an outer timeout. Expected red:
   3316 tests, 104 failed, 3212 passed (every test of today passes; the 103 new acceptance tests and
   the new AC-06 architecture test fail because `sochron.research` and
   `sochron.strategy.entry_blockers` do not exist).
5. Fresh-session review of the applied tests (tests review r1, headless 2 of 6), then commit the red
   tests: `test(core-008): acceptance tests for CORE-008` with `Refs: CORE-008`.

## Checks run (command → result → commit → time UTC)

- `uv run --offline pytest tests -q -p no:cacheprovider` (repo root, PYTHONDONTWRITEBYTECODE=1,
  `timeout 900`) → PASS, 3212 passed in 23.89 s → 320c5cd → 2026-10-24T07:17:24Z.
- Red: `timeout 900 uv run --offline --no-sync python -I -B <scratch>/tools/runner.py <scratch>/red tests
  -q --tb=line -rf` from the repo root, where `<scratch>/red` is a copy of the repository's `src`,
  `tests` and `pyproject.toml` plus the three patched files → 104 failed, 3212 passed in 24.69 s →
  320c5cd → 08:19:43Z. All 31 loaded sochron modules came from `<scratch>/red/src` (the repository's
  code, copied).
- Green on a contract-only reference (see Satisfiability): the whole suite → 3316 passed in 34.00 s
  → 08:20:30Z; `tests/acceptance/CORE-008 tests/golden/CORE-008` (the contract's AC-01..05 command)
  → 103 passed.
- Golden cross-check with exact fractions (`check_golden.py`, no sochron import) → 0 differences
  (summaries, percentiles, the ten neighbour tables and their counts).
- Independent canonical encoder (`canon.py`, stdlib json/hashlib only) → reproduces the contract's
  normative run_id, line and line SHA-256; the hand-written golden ok and random_entry lines equal
  its `json.dumps` of the same fields.
- Report text against the contract's literal template (`check_template.py`) → every golden report
  line matches a template line, every fixed template line is present: 0 problems.
- AST comparison of the architecture file (`ast_compare.py`) → 0 differences (below).
- `git apply --check docs/proposals/CORE-008-tests.patch` (standalone) → exit 0, no output.
- `git apply --numstat docs/proposals/CORE-008-tests.patch` → 2396/0, 834/0, 373/0.
- Environment: Windows 11, Git Bash, the project's uv environment (Python 3.12, pytest 9.1.1); every
  pytest run under an outer `timeout`, with PYTHONDONTWRITEBYTECODE=1, `-B` and `-p no:cacheprovider`.

## Red: why each group fails

| AC | Tests | Fails now because |
|---|---|---|
| AC-01 | 12 | `_api` → `pytest.fail("AC-01: sochron.research not implemented (No module named 'sochron.research')")` |
| AC-02 | 13 | same message, AC-02 |
| AC-03 | 22 | same message, AC-03 |
| AC-04 | 6 | same message, AC-04 |
| AC-05 | 42 | same message, AC-05 |
| AC-06 report | 4 | same message, AC-06 |
| AC-06 entry_blockers | 4 | `AC-06: sochron.strategy.entry_blockers not implemented` |
| AC-06 architecture | 1 | the checker self-tests pass, then `AC-06: <repo>\src\sochron\research does not exist; implementation missing` |

No test fails on a syntax, import or fixture error of its own.

## Test inventory (what each test proves)

| AC | Test | Proves |
|---|---|---|
| AC-01 | test_ac01_public_names_versions_errors_and_shapes | RESEARCH_VERSION, HOLDOUT_CUTOFF_UTC, BASELINE_RUNS, the error hierarchy, Purpose, USED_PARAMETERS, dataclass field names (RunRecord without run_id, run_id a property), frozen, the registry module's append_record |
| AC-01 | test_ac01_the_normative_example_has_the_contract_bytes_run_id_and_hash | The normative record: run_id `e358…`, line() bytes exactly the contract's line, 1671 bytes, SHA-256 `f50c…`, the file after append_record |
| AC-01 | test_ac01_append_two_more_records_and_read_back_values_and_types | started + ok (golden line with a Summary) + a new started: seq 1-3, earlier bytes unchanged after each append, read_records equal in value, type and Decimal/datetime representation |
| AC-01 | test_ac01_a_random_entry_ok_line_with_its_baseline_summary | A random_entry ok line with a BaselineSummary equals its golden bytes; seed = int(base[:15], 16); round trip |
| AC-01 | test_ac01_a_missing_or_empty_registry_reads_as_no_records | Missing and empty files read as () and nothing is created |
| AC-01 | test_ac01_a_torn_tail_names_its_byte_offset_and_blocks_append | Bytes after the last LF: ResearchError naming the offset; append refused, file unchanged |
| AC-01 | test_ac01_every_damaged_line_is_refused_with_its_line_number | 22 cases (CR, non-ASCII, broken JSON, empty line, spaces, unsorted keys, escaped letter, seq gap/repeat/not from 1, forged run_id, missing/extra field, wrong JSON type, float, bad status, bad Decimal, bad pairings): ResearchError with the line number; append refused, file unchanged |
| AC-01 | test_ac01_append_refuses_records_that_do_not_continue_the_file | Wrong seq, ok/failed paired with another identity, a second result, a failed line on an ok line, paths not ending in .jsonl (nothing created) |
| AC-01 | test_ac01_wrong_types_are_type_errors_and_write_nothing | str/None path, dict/None record, read_records with str/None: TypeError |
| AC-01 | test_ac01_filesystem_errors_reach_the_caller_unwrapped | Missing directory, a directory as the path: the OSError itself, never ResearchError |
| AC-01 | test_ac01_run_record_checks_every_field_the_contract_lists | 72 constructor cases: every item of the F36 list (value → ResearchError, type → TypeError) |
| AC-01 | test_ac01_dataset_summary_and_baseline_summary_check_themselves | Dataset types and values (naive, +07:00, microseconds, start ≥ end, hex, m1_bars); Summary and BaselineSummary type checks |
| AC-02 | test_ac02_every_purpose_writes_started_then_ok_with_every_field | select, robustness, stress, long_only on a series with one trade: started + ok lines equal to the records the field table derives, summary = summarize(backtest.run(...)), the returned (record, result), every write through the seam |
| AC-02 | test_ac02_an_exception_after_the_started_line_writes_failed_and_raises_the_same_object | Sizer error (non-ASCII message → `???`), KeyboardInterrupt, costs.BadVolume unwrapped, the ok append failing through the seam: started + failed with the exact error text, the same object raised |
| AC-02 | test_ac02_when_the_failed_line_also_fails_the_first_error_is_raised_and_a_rerun_is_accepted | ok and failed appends both fail: the first error is raised, only the started line remains; the rerun is accepted |
| AC-02 | test_ac02_the_holdout_guard_comes_before_every_other_check | M1 at the cutoff (with a wrong Dataset, every other input wrong, no Dataset), an M15 bar at the cutoff without M1, an M1 after it, a Dataset ending 1 s after it: HoldoutRefused, no line; the last minute before the cutoff with a Dataset ending at it is accepted |
| AC-02 | test_ac02_inputs_are_checked_before_any_line | Purposes, stress_factor as record strings ("2.0", "1.0"), code_commit, sizer_label, Dataset count/period, equity, path, select with a base, 14 M1/M15 inconsistencies: ResearchError, no file |
| AC-02 | test_ac02_wrong_types_are_type_errors_before_any_line | 16 wrong types: TypeError, no file |
| AC-02 | test_ac02_the_base_and_every_field_evaluate_compares_must_match_as_record_strings | 22 refusals (missing/unknown/started/failed/H002/other-variant base, non-neighbours incl. k "2.7" and theta "0.45", params, dataset, code_commit, sizer_label, equity incl. 1E+4, rollover, time rule, slippage, a stress record as base): ResearchError; "2.70" and "0.450" accepted |
| AC-02 | test_ac02_the_first_started_line_of_the_hypothesis_fixes_the_setup_of_the_file | Same params with slippage 20, slippage, equity, rollover, code_commit, sizer_label, time rule, provenance: BudgetExceeded; same setup accepted; an H002 line does not fix H001's setup |
| AC-02 | test_ac02_a_rerun_is_refused_after_ok_and_accepted_after_an_interrupted_or_failed_run | Rerun rules for select, robustness, stress, long_only |
| AC-02 | test_ac02_select_counts_six_distinct_params_per_variant | 6 accepted, 7th refused; same params on another dataset and a first A select accepted; H002 lines not counted |
| AC-02 | test_ac02_robustness_counts_fourteen_started_lines_per_variant | 13 interrupted/failed + the 14th accepted, the 15th refused |
| AC-02 | test_ac02_the_total_budget_is_63_summed_over_variants | 62 counted lines; long_only not counted; the 63rd accepted; the 64th (a rerun of an interrupted stress) refused |
| AC-02 | test_ac02_one_base_per_variant_for_every_purpose_but_select | A second base of B refused for robustness, stress, long_only; A keeps its own; an interrupted stress fixes the base |
| AC-03 | test_ac03_summarize_matches_the_hand_computed_summary[6] | No trades; 7 trades (deepest drawdown before a new peak, Bangkok/UTC year edge, tie in the top 5 by representation); 5 trades starting with a loss; 6 equal trades; the sum in trade order at precision 28; a rule with offset 7200 |
| AC-03 | test_ac03_summarize_computes_in_the_costs_context_and_leaves_the_caller_context | A precision-50 caller context changes nothing and is left as it was |
| AC-03 | test_ac03_summarize_refuses_wrong_types | TypeError |
| AC-03 | test_ac03_percentile_is_the_nearest_rank[12], ..._of_a_thousand_values, ..._refuses_bad_inputs | Nearest rank at every edge; empty and q outside (0, 1] → ResearchError; wrong types → TypeError |
| AC-04 | test_ac04_flat_prices_with_a_scripted_random_give_the_hand_computed_baseline | Flat prices, scripted fake random.Random: one generator with seed int(base_run_id[:15], 16), the randrange arguments of every round, every expectancy -0.024, hand BaselineSummary (holds 2/0 and 4/5), 4000 sizer calls (equity 10000, stop 3), lines, seam writes; a second call refused |
| AC-04 | test_ac04_every_scripted_draw_and_trade_follows_the_contract_steps | Wave prices and a variant with signal, stop, ambiguous and end_of_data exits: every randrange argument, every expectancy and hold statistic equals the contract's steps computed here with simulate_trade (sizer None on every 7th call) |
| AC-04 | test_ac04_the_real_generator_is_seeded_from_the_base_and_repeats | Real random.Random: two fresh registries give identical results and bytes, equal to the steps with random.Random(seed); flat prices give -0.024 for every round |
| AC-04 | test_ac04_refusals_before_the_started_line_write_nothing | Holdout (2), model 2x, base mismatches (6), variant not the base's result, M1/M15 inconsistent (2), a variant time that is no M1, types, unknown/started base, no trades, stops only, more trades than eligible bars |
| AC-04 | test_ac04_failures_after_the_started_line_write_failed_and_raise_the_same_object | Pool exhausted, a sizer result that is not SizedLots, KeyboardInterrupt, a failing ok append: started + failed, the same object |
| AC-04 | test_ac04_random_entry_keeps_one_base_per_variant | A second base refused after an ok, after an interrupted robustness, after an interrupted random_entry on the first; a rerun on the first accepted |
| AC-05 | test_ac05_neighbours_match_the_hand_computed_table[10] | Defaults of A/B/C, top and bottom of every range, s = 3f, M = N, exact halves (ROUND_HALF_UP): rows, values, params or None, counts |
| AC-05 | test_ac05_neighbours_compute_in_the_costs_context, ..._refuse_wrong_types | Precision-2 caller context changes nothing; TypeError |
| AC-05 | test_ac05_evaluate_every_row_at_its_threshold[29] | All 10 rows' value/threshold/passed strings at every boundary, missing inputs (F37), 0/50/99/100 trades, invalid neighbours, A/B/C counts, screen at the cutoff and one second before |
| AC-05 | test_ac05_evaluate_refuses_inconsistent_inputs | 30 inconsistent inputs → ResearchError; 3 wrong types → TypeError |
| AC-06 | test_ac06_the_report_with_failed_interrupted_lines_and_three_evaluations | The literal report: 15 registry rows with failed and interrupted counts, budget 7/63, three sections (two screens, one not), setup line, dataset counts, bullets, blank lines |
| AC-06 | test_ac06_the_report_without_any_evaluation | No Evaluation (F38 blank-line rule) and an empty registry |
| AC-06 | test_ac06_the_report_reads_only_the_records_of_its_hypothesis | H001 + H002 in one file: the H001 text is unchanged, the H002 report, an Evaluation on H002's select refused |
| AC-06 | test_ac06_the_report_refuses_bad_keys_and_bases_that_are_not_the_locked_one | Key ≠ variant, key D, unknown base, a started base, another variant's base, a select ok that is not the locked base (F45); wrong types |
| AC-06 | test_ac06_entry_blockers_give_decide_s_skip_reasons_in_every_case | 240 combinations of window, spread, ATR, flags and warm-up: entry_blockers = the contract's reasons in order = decide's skip reasons; empty → decide enters |
| AC-06 | test_ac06_decide_calls_entry_blockers_through_the_h001_module | sochron.strategy.entry_blockers is h001.entry_blockers; a monkeypatched fake changes decide's reasons and lets a cold row enter |
| AC-06 | test_ac06_entry_blockers_refuse_wrong_types_and_naive_times | TypeError for row/time types and subclasses; StrategyError for a naive time |
| AC-06 | test_ac06_invalid_is_gone_and_the_strategy_version_is_unchanged | `_invalid` absent; STRATEGY_VERSION "H001-v1" |
| AC-06 | test_ac06_core008_research_imports_only_its_grants_and_listed_stdlib_and_does_io_only_in_registry | Checker self-tests (exact findings, registry.py modes, grants for research only, every FIX-001/CORE-001 rule kept), then the package scan with registry.py required |

## Satisfiability

A minimal contract-only reference was written in the session scratchpad (never in the repository):
a copy of `<repo>/src` with `sochron/research/` added (model, registry, stats, robustness, checks,
runner, baseline, evaluate, report) and `sochron/strategy/h001.py` changed (D1: `entry_blockers`
replaces `_invalid`, decide calls it through the module name, exported from `sochron.strategy`).
The runner `runner.py` under `uv run --offline --no-sync python -I -B` puts the tree's `src` first on
`sys.path`, asserts `sochron` comes from there, changes directory (inside the process; the shell stays
at the repo root) to that tree so the architecture test scans its `src`, runs pytest with the tree's
pyproject (`-c`, `--rootdir`, `-p no:cacheprovider`) and prints the origin of every loaded sochron
module. Results: whole suite 3316 passed, CORE-008 acceptance + golden 103 passed, architecture 18
passed; 41 of 41 sochron modules from the scratch tree (research, research.registry, strategy,
strategy.h001 and backtest named in the output).

## Mutants (each changes the reference only; CORE-008 acceptance + the architecture file: 121 tests)

| Mutant | Result | Caught by |
|---|---|---|
| percentile by interpolation | 11 failed | percentile cases, AC-04 percentiles |
| drawdown not starting at 0 | 5 failed | summarize five_first_loss, AC-04 (the hand base summary) |
| years in Bangkok time | 3 failed | summarize seven, offset_rule, context test |
| failed or interrupted runs not counted | 2 failed | robustness 14, total 63 |
| re-run allowed after an ok | 1 failed | rerun test |
| identity including run_id | 1 failed | rerun test |
| setup freeze missing | 1 failed | setup test |
| base lock missing for random_entry | 1 failed | AC-04 one base per variant |
| holdout guard after the Dataset checks | 1 failed | holdout test |
| text-mode append (CRLF on Windows) | 26 failed | normative bytes, read-back, architecture registry rule |
| select counted per hypothesis instead of per variant | 1 failed | select budget |
| report not filtered by hypothesis | 1 failed | mixed H001/H002 report |
| evaluate giving go with a missing input | 4 failed | evaluate missing-input cases |
| seed chosen by the caller | 3 failed | AC-04 scripted and real-generator tests |
| module-level random | 3 failed | AC-04 scripted tests, architecture |
| h drawn from every exit (stops included) | 4 failed | AC-04 (randrange arguments, expectancies) |
| eligibility from session and spread only | 4 failed | AC-04 (pool) |
| entry_blockers as a private copy not used by decide | 1 failed | decide-through-the-module test |
| extra: Decimal normalized in the record | 20 failed | AC-01 bytes, report |
| extra: budget total without stress | 1 failed | total 63 |
| extra: neighbours rounded half-even | 1 failed | C_halves |
| extra: random entries see the equity after each trade | 2 failed | AC-04 sizer calls |
| extra: report bullets for failed lines too | 0 failed | equivalent: RunRecord already forbids a summary on a failed line |
| extra: >= replaced by > on expectancy_1x | 27 failed | evaluate boundary cases |

All 18 required mutants are caught. Each replacement had to match exactly once, and the reference
was restored after each run (checked with `diff -r` against the green tree).

## AST comparison (tests/architecture/test_imports.py)

Against `git show HEAD:tests/architecture/test_imports.py` (scratch `ast_compare.py`): HEAD has 82
top-level statements, the new file 100. The 81 statements after the docstring are identical by
`ast.dump` and in the same order; the module docstring only grew at its end (7 lines on CORE-008).
Added at the end: `_RESEARCH_GRANTS`, `_RESEARCH_STDLIB`, `_RESEARCH_RNG_METHODS`,
`_RESEARCH_FILE_CHANGES`, `_RESEARCH_MODES`, `_RESEARCH_IO`, `_RESEARCH_ADDED`, `_granted_to_research`,
`_research_mode`, `_research_allowed_io`, `_inspect_research_source`, `_inspect_as_research`,
`_inspect_as_registry`, `_RESEARCH_FORBIDDEN`, `_RESEARCH_ALLOWED`, `_RESEARCH_REGISTRY_CASES`,
`_RESEARCH_GRANTS_ELSEWHERE` and the test. The 17 existing tests are kept in order (17 → 18) and
`_allowed_import` is untouched: the research checker drops only the "forbidden import" findings of
the four granted packages (and, in registry.py only, the I/O finding of each allowed call on its
line) from the unchanged `_inspect_source` and adds its own findings. The strategy checks pass on the
reference with `entry_blockers` added.

## Conventions fixed where the contract leaves room

1. Dataset, Summary, BaselineSummary, BaselineResult, Neighbour, Check and Evaluation are frozen
   dataclasses with the contract's field names in the contract's order; RunRecord's fields are the
   registry table's names without run_id (any order); run_id is a property, line() returns bytes.
   Tests build every one of them with keyword arguments.
2. Value errors may be ResearchError or a subclass, but never BudgetExceeded or HoldoutRefused
   unless the contract names those. Wrong types are TypeError, including a list where a tuple is
   required, a str registry path and None where a value is required.
3. A torn tail's message contains its byte offset (first byte after the last LF) as a number; a bad
   line's message contains its 1-based line number as a number.
4. run_variant and random_entry_baseline write hypothesis "H001"; setup, budgets and base lock read
   only lines of that hypothesis.
5. Interrupted and failed runs are made with append_record, field for field as the runner writes
   them.
6. M15 bars are AggregatedBar values built in the tests from their M1, 1 to 3 M1 per bar; the M15
   spread of bar 99 (700) differs from its M1 spreads (200): research does not compare them.
7. The fake random.Random has only randrange (n, or 0 and n) and records its seed and every n; the
   seam tests wrap `sochron.research.registry.append_record` and record each status.
8. Decimals are compared by value except where the contract fixes the representation: the record
   line, the report, Check strings, neighbour values (`"0.450"`, `"14"`) and the top-5 tie rule.
9. The report lists every summary bullet by seq, then every baseline bullet by seq.
10. Architecture: randomness means `random.Random(<seed>)` and `.randrange`; module-level random
    functions, an unseeded Random and the other generator methods (`random`, `choice`, `shuffle`,
    `seed`, …) are findings. registry.py may use `open(path, "ab"|"rb")`, `path.open("ab"|"rb")`
    (literal mode, positional or `mode=`) and `path.read_bytes()`; `.unlink`, `.rmdir`,
    `.truncate`, `.rename`, `.touch`, `.mkdir` are findings anywhere in research.

## Open questions (the contract does not say; left as above or untested)

1. Report bullets: grouped (summary bullets, then baseline bullets) as tested, or interleaved by seq?
2. The screen line names "H001" literally; a report for another hypothesis with a screen Evaluation
   is not tested.
3. read_records on a path that is a directory: tested as the OSError passing through, not as "no file".
4. The data_flags of random trades are not observable (BaselineResult returns no trades): untested.
5. "OSError while writing" is tested with open failures (missing directory, a directory as the path),
   not with a write that fails after open (no portable way without patching builtins).
6. Case of the suffix (`registry.JSONL`), `robustness=None` in evaluate, and value checks inside
   Summary/BaselineSummary (only types are tested).
7. docs/architecture.md section 8 lets research import data.snapshot; the contract forbids the whole
   data package, and the tests follow the contract.
8. The speed row of the contract is the implementer's unit test, not here.

## Blocks and failures during this session

- Hook block (reported; the same action was then rerun with literal paths under the owner-granted
  exception recorded in memory, "a variable path to the scratchpad becomes a literal path"): a
  `mkdir`/`cp` with shell variables for the scratch tree →
  `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: mkdir would change $S/red (a path that cannot be resolved here (variable or unknown directory)). The implementer may not change locked paths; ask the owner.`
  The task instructions also require literal paths.
- Permission denial (step stopped, not retried in any form):
  `Permission to use Bash with command cp "<repo>/tests/architecture/test_imports.py" "<scratch>/work/tests/architecture/test_imports.py" && tail -c 200 "<scratch>/work/tests/architecture/test_imports.py" | od -c | tail -4 has been denied.`
  The architecture change was then written in the red scratch tree's byte copy of that file, made
  earlier by an allowed `cp -r` of `tests/`, after checking that its blob equals HEAD's (`6751aadf…`);
  the patch's architecture diff uses the green tree's unmodified copy (same blob) as its base, and
  `git apply --check` against the real file passed.
- Hook block (my error; the commands were rerun one by one under the owner-granted "standalone
  rerun" exception): a final check chained `git apply --numstat` with `git status`, `sha256sum` and
  others →
  `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run each action separately.`
  The standalone `git apply --check` after it passed again (exit 0) and the patch SHA256 was unchanged.
- The tool runner refused a foreground `sleep` and the Monitor tool needed an approval this session
  cannot give; the background wait already running was used instead. Not project hooks.
- Two fixture checks failed on the first green runs and were fixed in the tests (a baseline ok line
  compared byte for byte against hand values, against convention 8; and a wave gap of -5.00 too small
  for any random trade to hit its stop, now -12.00). A third change made the select-budget test give
  A params B never used, so a mutant counting params across variants is caught.

## Not verified

- The patch was not applied (by instruction); the red numbers come from a scratch copy of the
  repository plus the three files, not from a patched tree.
- CI was not run. The reference implementation proves satisfiability only; it is not a deliverable
  and stays in the session scratchpad.

## Findings response (filled after review)
| ID | Accept/Dispute | Commit | Evidence |
|----|----------------|--------|----------|
