# Review CORE-008 tests round 1 · base main (origin/main 3af8333) · head 9f3bc63 + D-006 patch `48d5915f…` applied, uncommitted · reviewer Claude Code (Opus 5.5), fresh session, tests reviewer under the D15 role swap

Scope: the three locked files of `docs/proposals/CORE-008-tests.patch` against
`docs/contracts/CORE-008-research.md` v1.5 (read in full), H001 sections 3-9 and the public API of
`sochron.backtest`, `strategy`, `costs`, `timebase`, `core` and `data.snapshot`. Read-only except this
file. My first list of findings was written to the session scratchpad at 2026-10-24T08:50Z, **before
I opened `docs/handoff/CORE-008.md`**; it named the six gaps F1-F6 below (as suspicions S1-S6). Reading
the handoff afterwards changed none of them. The mutant evidence came after, from 16 mutants of my
own reference that are not in the author's list.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | tests/acceptance/CORE-008/test_research.py:1728-1842 (no AC-04 test sets a caller context; compare :1468 summarize and :1990 neighbours) | Mutant M3 of my reference (the 3 `with localcontext(CONTEXT):` in random_entry_baseline → `with localcontext():`) passes 121/121 (CORE-008 acceptance + architecture file). Probe at a caller context of precision 3, ROUND_UP on the wave series: reference mean_r −0.145504 in both contexts; M3 −0.465 | random_entry_baseline computing stop_distance (k × ATR), a round's expectancy, mean_r or the mean holds in the caller's context | Contract "Inputs" (every Decimal in `costs.CONTEXT`) and baseline steps 7-8 "(ใน CONTEXT)" are untested for the baseline. The default context equals CONTEXT in precision and rounding, so R1 scripts are unaffected unless the caller changes the context | In test_ac04_the_real_generator_… (or the wave test), run one `bench.call` inside `with localcontext() as context: _hostile(context, prec=3)`; assert `_context_state()` is unchanged and the result equals the oracle (computed in CONTEXT) | scratch `probe_context.py`: reference equal under both contexts; M3 unequal (mean_r −0.465, first round −0.463 vs −0.462000) |
| F2 | Low | confirmed | tests/golden/CORE-008/research_cases.py:648-649, :733 (B stress = 1 started + 1 ok), :722-725; test_research.py:2204 | Mutants M1 (stress "งบ" column `{started}/1`) and M2 ("นับงบ" adds stress ok instead of started) each pass 121/121: with one started and one ok line both counts are 1 | render_report using started for the stress column, or ok for the stress part of the total | Contract render_report: stress column = `{ok}/1`; "นับงบ" = … + started of stress (runner step 5: reruns count). After an interrupted stress and its rerun the owner's report would show the wrong budget | One more report case: B select ok, a stress started line left interrupted, its rerun started + ok → expect the row `\| B \| stress \| 2 \| 1 \| 0 \| 1 \| 1/1 \|` and `รวมที่นับงบ: 3/63` | scratch `proof.py` F2: HOLDS on the reference; BROKEN on M1 (row) and on M2 (total) |
| F3 | Low | confirmed | test_research.py:2210, :2219, :2233 (records always passed in seq order); research_cases.py:637-656 (one setup for every H001 record) | Mutant M4 (bullets in input order, no sort by seq) and M12 (setup line from the first H001 record instead of the base) each pass 121/121 | render_report given records out of seq order; or a base whose setup differs from another record of the hypothesis | Contract: bullets "เรียงตาม seq" and the setup line "จาก record ฐาน (F33)" are untested. Low: read_records always returns seq order and the runner keeps one setup per hypothesis and file | (a) `render_report(tuple(reversed(records.values())), evaluations) == REPORT_FULL`; (b) optional: a file whose first H001 line is an A select with equity 5000, the B base at 10000 and an Evaluation on B → the setup line shows `equity 10000` | `proof.py` F3: HOLDS on the reference; (a) BROKEN on M4, (b) BROKEN on M12 |
| F4 | Low | confirmed | research_cases.py:417-423 (the only 0-trade base, "no trades and every optional input missing", also has long_only None) | Mutant M5 (row 10 without "base has no trades") passes 121/121 | A base with 0 trades evaluated with a long-only run that has trades: base drawdown 0 < long-only drawdown makes row 10 pass | Contract row 10 "(ถ้า long-only ไม่มีไม้ หรือ base ไม่มีไม้ = ไม่ผ่าน)". The verdict stays insufficient (row 1), but the report prints row 10 as ผ่าน | Add an EVALUATE_CASES row: base ZERO_SUMMARY, stress/random None, robustness (), long_only kept (EVAL_GO: 100 trades, 0.10, drawdown 25) → verdict insufficient, rows 1-9 as in "no trades and every optional input missing", row 10 `("expectancy:none/0.10;max_drawdown:0/25", "better on one", False)` | `proof.py` F4: HOLDS on the reference; BROKEN on M5 |
| F5 | Low | confirmed | test_research.py:2076-2146 (30 inconsistent inputs, none for these three) | Mutants M6 (variant not compared), M13 (long_only's base_run_id not checked) and M16 (rollover_zone not compared) each pass 121/121 | evaluate given a stress record of another variant, a long-only record of another base, or a record with another rollover zone | Contract evaluate input rules name the variant, "stress, long_only, random_entry และทุก robustness มี base_run_id = run_id ของ base" and the rollover; an evaluate missing one returns a verdict from records that do not belong together. Runner-written registries cannot pair such records (runner step 4), hence Low | Three cases → ResearchError: `replace(stress, variant="A")`, `moved(long_only, "f" * 64)`, `replace(random_entry, rollover_zone="Europe/London")` | `proof.py` F5: HOLDS on the reference; each case BROKEN on its mutant (M6, M13, M16) |
| F6 | Low | confirmed | test_research.py:1854, :1873-1874 (only `entry_time_raw` is shifted) | Mutant M7 (checks only entry times of variant trades) passes 121/121; given a variant whose exit time is no M1 it raises KeyError instead of ResearchError | A variant Result whose `exit_time_raw` is not an M1 of `m1` | Contract baseline step 2 ("entry_time_raw และ exit_time_raw เป็น time_raw ของ M1 ใน m1 ไม่เช่นนั้น ResearchError") is half tested; the failure is loud (KeyError), hence Low | Add to test_ac04_refusals… the case "a variant exit time that is no M1": `replace(bench.variant, trades=(replace(trades[0], exit_time_raw=trades[0].exit_time_raw + 60),) + trades[1:])`; summarize ignores exit times, so the base still matches | `proof.py` F6: HOLDS on the reference (ResearchError, registry unchanged); BROKEN on M7 (KeyError) |

All six are additive coverage gaps. No test is wrong, over-constraining or unsatisfiable, and no golden
value is wrong (details below).

## Checks run (command → result → commit → time UTC 2026-10-24)

1. Hashes: `sha256sum` of the patch and the three files, `git hash-object` of the three files → patch
   `48d5915f…450eb5`; test_research.py `9817bb68…143a5` / blob `f1089df2…f045f1f`; research_cases.py
   `f896083d…16fa9` / `a711d150…0b87`; test_imports.py `c17d17ec…6ea93` / `1cc7287d…a4c3`: all equal
   to the expected values → 9f3bc63 + patch → 08:2x. Re-checked unchanged at 08:58.
   `git apply -R --check docs/proposals/CORE-008-tests.patch` (alone) → exit 0, no output.
   `node scripts/controls/check-locked-paths.mjs origin/main` → exactly the three files (M
   test_imports.py, A test_research.py, A research_cases.py), FAIL by design ("need owner
   approval"). (Local `main` is stale at b7e0dd2 and also lists CORE-005..007; origin/main is the
   real base.) `git diff --name-only HEAD` + untracked → only these three plus docs/handoff/CORE-008.md.
2. Fidelity: clause-by-clause reading (table "Coverage" below) plus 16 mutants.
3. Golden: my own `recompute.py` (imports only `sochron` from `src`, reads the contract file; never the
   tests or golden) and `compare.py` → 404 values compared, all equal by value: the normative line
   (byte-equal to the contract's line, run_id `e3580903…`, 1671 bytes, SHA-256 `f50c0bcb…`, and the
   contract line's own run_id matches its content), OK_RUN_ID `dd5d8f72…`, RANDOM_RUN_ID `af0c3bda…`,
   RANDOM_SEED 996941448488460761, REPORT_RUN_ID_7 `e6b142d3…`, REPORT_SEED 1038946323396661795, all 5
   non-empty summarize cases (every field), the 12 percentile cases and the 1000-value case, all 10
   neighbour tables + RUN_NEIGHBOURS of A/B/C (validity by my own H001 §4 rule, cross-checked against
   H001Params), 24 evaluate cases (every row value/threshold/passed, verdict and screen; boundaries
   0.10, 24, 7/8, P95 equality, year 0, short 0, and every missing-input case incl. 0 and 50 trades),
   the flat round −0.024 (by hand and via `simulate_trade` long/short × exit/end of data), and
   REPORT_FULL byte for byte from the template. The only two differences were representations in my
   own script (`1.00` vs `1`, `0E+1` vs `0` in expectancy_by_year), which the tests compare by value.
4. Quality: AST compare (`ast_compare.py`, HEAD via `git show` on stdin, working file read in place) →
   HEAD 82 statements, new 100; the 81 statements after the docstring are identical and in place, the
   module docstring only grew at its end; 18 statements appended. Determinism and wrong-reason checks:
   see "Checked, nothing found".
5. Red: `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider`
   → **104 failed, 3212 passed in 29.92 s** → 9f3bc63 + patch → 08:32:34-08:33:04. Messages grouped
   (`--tb=short` on CORE-008): 99 × "AC-0n: sochron.research not implemented (No module named
   'sochron.research')" (AC-01 12, AC-02 13, AC-03 22, AC-04 6, AC-05 42, AC-06 4), 4 × "AC-06:
   sochron.strategy.entry_blockers not implemented", and the architecture test passes every checker
   self-test and then fails on "AC-06: …\src\sochron\research does not exist; implementation missing".
   Every failure is for the contract reason; none is a syntax, import or fixture error of the tests.
6. Satisfiability: my own contract-only reference in the scratchpad (a copy of `src` plus
   `sochron/research/` = model, registry, stats, checks, robustness, runner, baseline, evaluation,
   report, and `strategy/h001.py` with `_invalid` → `entry_blockers` (exact types, StrategyError for a
   naive time) called by decide through the module name, exported from `sochron.strategy`). Runner
   `run_against.py` under `uv run --offline --no-sync python -I -B` imports every sochron module from the
   scratch tree first and prints their origins before and after pytest. CORE-008 acceptance → 103
   passed (12.84 s, cwd repo); whole suite with the cwd at the scratch tree (so the architecture test
   scans the reference) → **3316 passed in 47.15 s**; 41 of 41 sochron modules from the scratch tree.
   Two more CORE-008 runs (fresh hash seeds) → 103 passed each (08:57).
7. `bash scripts/controls/red-flags.sh origin/main` → "Pattern groups with hits: 0"; control file
   touched: tests/architecture/test_imports.py (the patch). The script does not scan untracked files, so
   I ran its "all files" patterns over the two new files with Grep: 3 hits of group "Lint disabled",
   `# noqa: E731` at test_research.py:1066, :1779, :1816 (a lambda bound to a name). Explanation: test
   code, style only; CI runs pytest only (no linter, ubuntu-24.04); these are the first `noqa` in
   `tests/`. No other group hits (no skip/xfail, type-ignore, swallowed errors, secrets, destructive
   commands).

## Mutants (mine; none is in the handoff's list). CORE-008 acceptance + architecture file, 121 tests

| Mutant (in my reference) | Result | Caught by / finding |
|---|---|---|
| M1 report stress column = started/1 | 121 passed | survives → F2 |
| M2 report total adds stress ok | 121 passed | survives → F2 |
| M3 baseline arithmetic in the caller's context | 121 passed | survives → F1 |
| M4 report bullets in input order | 121 passed | survives → F3 |
| M5 row 10 ignores "base has no trades" | 121 passed | survives → F4 |
| M6 evaluate does not compare variant | 121 passed | survives → F5 |
| M7 baseline checks only entry times | 121 passed | survives → F6 |
| M8 holdout guard `>` instead of `>=` | 2 failed | holdout test (AC-02), AC-04 refusals |
| M9 M1/M15 checks after the started line | 1 failed | test_ac02_inputs_are_checked_before_any_line |
| M10 failed line only for `Exception` | 1 failed | test_ac02_an_exception_after_the_started_line… (KeyboardInterrupt) |
| M11 baseline hold = planned exit | 2 failed | AC-04 wave and real-generator tests |
| M12 report setup from the first record | 121 passed | survives → F3 (b) |
| M13 evaluate skips long_only's base_run_id | 121 passed | survives → F5 |
| M14 read_records line number 0-based | 1 failed | test_ac01_every_damaged_line… |
| M15 baseline pool shared across rounds | 5 failed | AC-04 (5 tests) |
| M16 evaluate skips rollover_zone | 121 passed | survives → F5 |

Each mutant ran in its own copy of the reference with exact-count replacements (`mutate.py`); for every
run, all 35 loaded sochron modules came from that copy (provenance line printed after pytest). The author's 24 mutants (handoff) were not rerun.

## Coverage of the contract (does a test fail if the clause is not implemented?)

- AC-01 registry: normative bytes/run_id/hash; canonical rules (sort, separators, ASCII, Decimal `str`
  not normalized, datetime format, nested objects, `[year, str]`, null) through three byte-exact lines;
  run_id property and `line()` bytes; every item of the F36 list (72 constructor cases); Dataset,
  Summary, BaselineSummary self-checks; append_record (.jsonl, existing file must read, seq = n+1,
  pairing incl. a second result and a failed line on an ok line, file unchanged, OSError unwrapped);
  read_records (missing/empty, torn tail offset, CR, non-ASCII, broken JSON, three non-canonical forms,
  missing/extra field, JSON type, float, status, bad Decimal, seq gap/repeat/not 1, forged run_id, four
  bad pairings; value and type round trip). **Uncovered:** "write ครั้งเดียว … แล้ว flush" (only the
  "ab"/"rb" mode is pinned, by the architecture test; untestable without patching I/O).
- AC-02 runner: step 1 first (6 refusals incl. every other input wrong, no Dataset, M15-only, Dataset
  end + 1 s; boundary accepted); step 2 (16 types, 17 values, stress_factor as record strings, sides
  via `Result` equality); step 3 (14 CORE-007 inconsistencies incl. the three STOP defects, before any
  line); step 4 (22 refusals, "2.70"/"0.450" accepted); step 5 (base lock, setup lock on 8 fields incl.
  provenance, H002 independent, rerun rules, select 6 per variant keyed by variant + params, same params
  on another dataset, robustness 14, total 63 with reruns counted and long_only not counted); steps 6-8
  (lines field for field, failed on Exception/BaseException/ok-append failure, first error kept when
  the failed append fails, error text, seam). Nothing uncovered.
- AC-03: every Summary field, ties, drawdown from 0, UTC years with an offset rule, trade-order sum at
  precision 28, hostile context, types; percentile nearest rank at every edge, domain, types. Nothing
  uncovered.
- AC-04: steps 1-9 incl. the randrange argument sequence, sizer None, h = 0, h past the end, pool
  exhaustion, SizedLots type, seed, determinism, flat value, second base (3 setups). **Uncovered:**
  CONTEXT for the baseline arithmetic (F1); the exit-time half of step 2 (F6); the `data_flags` of random
  trades (no output depends on them).
- AC-05: neighbours (10 tables, half-up, invalid → None, counts, context, types); evaluate (29 row
  cases, 30 + 3 refusals). **Uncovered:** row 10 with a 0-trade base and a long-only run with trades
  (F4); variant, long_only base, rollover_zone consistency (F5).
- AC-06: report text (registry table with failed/interrupted, budget, three sections, screen and no
  screen, setup line, select dataset count, bullets, owner section, blank-line rules, empty registry,
  no Evaluation), H001/H002 filtering, key and base checks incl. F45 and F47; entry_blockers (240
  combinations = decide's skip reasons, module-level call, types, naive time, `_invalid` gone,
  STRATEGY_VERSION); architecture. **Uncovered:** stress column/total (F2); seq ordering and setup
  source (F3); the screen line for a non-H001 hypothesis (open question 2).

## Conventions of the test author judged against the contract

1. Frozen dataclasses, contract field order, RunRecord fields in any order, run_id property, `line()`
   bytes: the contract's shapes ("(frozen)", field lists, "run_id เป็น property", "line() คืนไบต์").
   Faithful.
2. Error kinds: BudgetExceeded/HoldoutRefused only where the contract names them, TypeError for types
   (list for tuple, str path, None): matches "Inputs" and the Python-type table. Faithful.
3. Byte offset = first byte after the last LF; 1-based line number: the plain reading of "byte offset
   ของบรรทัดนั้น" / "เลขบรรทัด". Faithful (M14 shows the line-number oracle bites).
4. Runner writes hypothesis "H001": the field table says "H001". Faithful.
5. Interrupted/failed runs made with append_record: identity rule of runner step 5. Faithful.
6. M15 as AggregatedBar with an M15 spread unlike its M1: the contract's M1/M15 checks never compare
   values. Faithful.
7. Fake Random with randrange(n) only: the contract writes the calls literally
   (`rng.randrange(len(pool))`, `randrange(2)`, `randrange(len(hs))`). Faithful.
8. Decimals by value except where the contract fixes text. Faithful and lenient. Note: the flat base
   summary is written `-0.024` while summarize gives `-0.02400`; AC-04 relies on the `==` the contract
   writes in baseline step 1, which compares by value.
9. Bullets grouped (summary, then baseline): the template has one line per bullet kind, each "เรียงตาม
   seq". Faithful.
10. Architecture: stdlib list, I/O only in registry.py with "ab"/"rb", `random.Random(seed)` +
    `randrange`, no float names (project convention since CORE-002), no file deletion/truncation
    ("ไม่มีโค้ดที่เขียนทับ ตัด หรือลบ"). `.exists()`/`.is_file()` are not flagged; no module in `src`
    uses `__future__`. Faithful.

No over-constraint found: an independent contract-only implementation passes every test.

## Recommendations on the author's open questions

1. Grouped bullets: keep as tested (template order). Ask for a one-line clarification at the next
   contract revision; no test change.
2. Screen line literally "H001": leave untested. evaluate implements H001 section 8 only, so a screen
   Evaluation of another hypothesis has no defined meaning; if H002 reuses this module, change the
   template to `{hypothesis}` first.
3. A directory as the path → the OSError: agree. A directory is not "a file that does not exist yet",
   and AC-01 says file-system errors pass through. (Windows gives PermissionError, Linux
   IsADirectoryError; both are OSError.)
4. data_flags of random trades: agree to leave them out of acceptance. No output depends on them, and
   observing them would lock a seam on `simulate_trade` that the contract does not define. The
   implementer may cover it in `tests/unit/research`.
5. A write that fails after open: agree; the seam test covers the runner's handling, and patching
   `builtins.open` would constrain how registry.py opens the file.
6. `.JSONL`: leave untested (the contract says ".jsonl"; a case rule would be new). `robustness=None`:
   leave untested (the signature says Sequence; the comment "None/ว่างได้เสมอ" can be read either way).
   Summary/BaselineSummary value checks: correctly untested (the contract asks for type checks only).
7. architecture.md:209 lets research import `data.snapshot`; the contract forbids the whole `data`
   package. Follow the contract (narrower, newer, and architecture.md is outside this task's files).
   Recommend the owner records the difference; loading snapshots for R1 will need either a contract
   change or a loader outside `research`.
8. Speed row: agree, it belongs to the implementer's unit test and evidence.

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Every clause has a failing test without an implementation (red run) and a passing one with a contract-only reference; only single-write/flush is untestable |
| AC-02 | PASS | All runner steps, budgets, setup/base/identity rules and the seam covered; mutants M8-M10 caught |
| AC-03 | PASS | All Summary fields and percentile edges; golden recomputed |
| AC-04 | PASS with gaps | Steps 1-9 covered; F1 (CONTEXT) and F6 (exit times) open |
| AC-05 | PASS with gaps | neighbours and all 10 rows covered; F4 (row 10) and F5 (three consistency rules) open |
| AC-06 | PASS with gaps | Report, entry_blockers and architecture covered; F2 (stress budget) and F3 (seq order, setup source) open |
| AC-07 | UNKNOWN | Needs the implementation and a CI run; with my reference the whole suite passes (3316) |

## Checked, nothing found (and how)

- Patch integrity and scope: hashes, blobs, reverse check, locked-path check against origin/main (above).
- Pre-existing architecture statements unchanged (AST compare above); the new checker keeps every
  CORE-001/FIX-001 finding (its own self-test) and was run on my reference without false positives.
- Golden values: 404 recomputed independently (above).
- Over-constraint search: each convention traced to contract text; the reference passes all 3316.
- Tests passing for the wrong reason: the holdout cases use inputs that would fail step 2 differently
  (a missing guard gives ResearchError, not HoldoutRefused; M8 caught); every runner refusal is checked
  with the file bytes before and after; the seam records each status; fixtures assert their own
  premises before use (FIRST_M1, ELIGIBLE, hs, exit reasons, one trade per purpose, the draws exercise
  stop/signal/end_of_data).
- Nondeterminism: no set or dict order reaches any compared output (data_flags are never serialized;
  provenance and sides are sorted; report counts only); three runs with different hash seeds gave
  identical results; files are LF (`*.py text eol=lf`), CI is ubuntu-24.04 running pytest only;
  filesystem-error tests accept any OSError.
- The architecture test fails loudly while `src/sochron/research` is missing (red message above).
- No new caches: every run used `-B`/PYTHONDONTWRITEBYTECODE and `-p no:cacheprovider`; the existing
  `.pytest_cache` dates from 2026-10-21 and is git-ignored.

## Not checked (and why)

- A Linux run of the tests (CI is ubuntu-24.04); I ran on Windows only. CI not run (no push).
- The author's 24 mutants, which I did not rerun; the handoff reports them caught.
- Evasion of the static architecture checker by dynamic tricks (`getattr`, computed names): same limits
  as the FIX-001 checker, outside this review.
- The contract's speed row (implementer's unit test and evidence).
- AC-07 green with the real implementation (does not exist yet).

Ready to commit red: yes. The six findings are additive Low coverage gaps: no existing expectation is
wrong, and adding the cases later only adds tests. They can follow as an additive tests r2 patch before
the implementation review, or the owner can accept them as residual risk.

Findings open: 6
