# Review CORE-008 tests round 2 (re-check) · base origin/main 3af8333 · head 7523407 + `docs/proposals/CORE-008-tests-r2.patch` applied, uncommitted · reviewer Claude Code subagent (Opus 5.5), fresh context, read-only (label: pre-review, Claude subagent)

Scope: the round-2 additions to `tests/acceptance/CORE-008/test_research.py` and `tests/golden/CORE-008/research_cases.py`, judged against contract v1.5 (read in full) and the round-1 findings F1-F6 in `docs/reviews/CORE-008-tests-r1.md`. I did my first pass from the contract and the diff only, before opening `docs/handoff/CORE-008.md`. The hook blocked my attempt to save that pass to a scratch file (see "Blocks"), so no file timestamp proves the order. Reading the handoff afterwards changed none of my findings.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | tests/acceptance/CORE-008/test_research.py:1495-1533 (no `percentile` case runs under a caller context); :2411-2452 (on the F1 test's data every q·n is exact: 1000 × 0.05/0.5/0.95, 4000 × 0.5, 4 × 0.5) | Mutant x4 changes `percentile`'s `with localcontext(CONTEXT):` to `with localcontext():`. It passes all 109 CORE-008 tests. Probe `probe_percentile.py` with a precision-3 ROUND_UP caller context: the reference gives n=2001, q=0.5 → 1000 and n=1001, q=1 → 1000; x4 gives 1009 and `IndexError` | A caller with a low-precision Decimal context calls `percentile` or `random_entry_baseline` | Contract "Inputs" says every Decimal is computed in `costs.CONTEXT`. That is untested for `percentile`, which produces p05/p50/p95 and both median holds (baseline step 8). Found while checking around F1: the F1 test's claim "every BaselineSummary field in CONTEXT" holds only for its own data. Under the default context (prec 28) the rank is the same for any realistic n, hence Low | One AC-03 case: inside `with localcontext() as context: _hostile(context, prec=3)`, `percentile([Decimal(i) for i in range(2001)], Decimal("0.5"))` must equal `Decimal(1000)`, and `_context_state()` must be unchanged | x4 gives 1009, so it fails the case; the reference gives 1000 (probe) |
| F2 | Low | question | Contract runner step 5 (setup lock, line 139) says nothing about how equity is compared; step 4 (line 136) says "แบบ string ของ record". test_research.py:1238-1269 tests the setup lock with equity 20000 only; "1E+4" is tested only against step 4 (:1208-1209). This is the author's open question 2 | Mutant x6: the reference's setup lock compares `record.equity` by value instead of `str(record.equity)` (checks.py:156). It passes 109/109 | A second H001 select with `Decimal("1E+4")` after a first started line with "10000" | Both readings pass every CORE-008 test. Under the value reading the runner accepts that select, the select can become B's base, and the source of the report's setup line (mutant x5, round-1 F3 (b)) becomes visible inside one runner-written file: `equity 1E+4` from the base vs `10000` from the first line. The rerun identity rule depends on the same reading | Owner states the reading at the next contract revision. If it is record strings (consistent with step 4, F19 and evaluate), add one case to test_ac02_the_first_started_line_…: `("equity 1E+4", {"params": other, "equity": Decimal("1E+4")})` → BudgetExceeded, file unchanged | Expected: x6 accepts the line and fails the case; the reference refuses it (checks.py:156 compares `str(record.equity)`) |

Neither finding is a defect in a round-2 test. Both are additive and neither blocks committing red.

## Round-1 findings: closed or open

| r1 ID | Verdict | Test (file:line) | Evidence |
|---|---|---|---|
| F1 | closed | test_ac04_r2_the_baseline_computes_in_the_costs_context_and_leaves_the_caller_context, test_research.py:2411; HOSTILE_PRECISION research_cases.py:851 | Passes on the reference. Mutant (a) is killed: expectancies differ, sizer stop distances differ, mean_r −0.451 vs −0.144796, p05_r −0.475 vs −0.474000, baseline_mean_hold_m1 3.91 vs 3.90025, and the ok line differs. Each block alone is also killed (x1 stop distance, x2 round expectancy, x3 mean_r and mean holds). The remaining gap in `percentile` is new F1 |
| F2 | closed | test_ac06_r2_an_interrupted_stress_and_its_rerun_in_the_stress_row_and_the_budget, :2519; REPORT_RERUN_RECORDS / _RERUN_ROWS / REPORT_RERUN research_cases.py:860-890 | Passes on the reference. (b) shows `2/1` instead of `1/1`; (c) shows `2/63` instead of `3/63`. Each is killed by :2519 and again by :2536 (rerun registry reversed). Golden recomputed by hand from the contract |
| F3 | closed for (a); (b) accepted as residual | test_ac06_r2_records_out_of_seq_order_give_the_same_report, :2536 | (d) is killed: the bullets come out reversed. (b) was not built, and x5 (round-1 M12) survives 109/109. x5 changes nothing on any registry the runner can write, provided the setup lock compares record strings (F2) |
| F4 | closed | test_ac05_r2_evaluate_row_10_fails_when_the_base_has_no_trades, :2476-2485; EVALUATE_CASES_R2 research_cases.py:906 | (e) is killed: row 10 is True, expected False. Rows 1-10, verdict insufficient and screen True recomputed by hand |
| F5 | closed | test_ac05_r2_evaluate_refuses_a_record_of_another_variant_base_or_rollover_zone, :2488 | (f), (g) and (h) are each killed by their own case only ("expected ResearchError, got None"). The fixture checks that the consistent set is accepted and that each case differs in exactly one field |
| F6 | closed | test_ac04_r2_a_variant_exit_time_that_is_no_m1_is_refused_before_the_started_line, :2455 | (i) is killed on both cases (`KeyError(1704789960)`, `KeyError(1704790860)`) plus "the registry changed" on the stop case. The fixture checks that summarize(variant) still equals the base summary |

## Mutants (each in its own copy of the reference; exact-count replacements; tests/acceptance/CORE-008 rounds 1+2, 109 tests, run in place from the repo root; every run loaded all 35 sochron modules from its own copy)

| Mutant | Result | Killed by |
|---|---|---|
| (a) baseline arithmetic in the caller's context (3 blocks) | 1 failed | r2 F1 test |
| (b) report stress column `{started}/1` | 2 failed | r2 F2 and F3 tests |
| (c) report total adds stress ok instead of stress started | 2 failed | r2 F2 and F3 tests |
| (d) report bullets in input order | 1 failed | r2 F3 test |
| (e) row 10 ignores "base has no trades" | 1 failed | r2 F4 test |
| (f) evaluate does not compare variant | 1 failed | r2 F5 test |
| (g) evaluate does not check long_only's base_run_id | 1 failed | r2 F5 test |
| (h) evaluate does not compare rollover_zone | 1 failed | r2 F5 test |
| (i) baseline checks entry times only | 1 failed | r2 F6 test |
| x1 / x2 / x3: one baseline context block each | 1 failed each | r2 F1 test |
| x4 `percentile` rank in the caller's context | 109 passed (survives) | new F1 |
| x5 setup line from the first record of the hypothesis | 109 passed (survives, expected: F3 (b) was not built) | see below |
| x6 setup lock compares equity by value | 109 passed (survives) | new F2 |

None of the nine requested mutants survives. Round-1 tests alone pass every one of them, so each kill comes from a round-2 test.

## Judgement of the author's choices

- **F3 (b) left out: I agree.** The contract fixes the setup at the hypothesis's first started line, and that line is always a select at stress_factor "1", like every base. The Invariant "ภายในไฟล์หนึ่ง setup ของ hypothesis คงที่" excludes registries where the base's setup differs from the first record's. A (b) test would still be contract-faithful (render_report names no refusal for mixed setups, and the reference prints the base's setup). But it would pin behaviour on input the invariants rule out. One caveat: the in-file corner is closed only if the setup lock compares record strings, and the tests do not pin that (x6, F2).
- **Open question 1** (refuse or print the base's setup): the contract already says "จาก record ฐาน (F33)" and lists no refusal for this. Read it as "print the base's setup". No test needed now.
- **Open question 2** (string or value comparison in the setup lock): this is a real gap and the tests leave it open. It becomes F2.
- **Open question 3** (the F1 test relies on merged modules never using the caller's context): I agree. Every Decimal operation on the baseline path runs inside `localcontext(CONTEXT)`: backtest/trade.py:47-153, strategy/indicators.py:109, strategy/h001.py:74 and :120, costs/charges.py. Construction, comparison and `str` of finite Decimals never set the caller's flags, and the reference passes with the caller's context unchanged.
- **Round-2 conventions 1-4 are faithful to the contract:**
  1. render_report has no ordering refusal, and the bullets are sorted by seq.
  2. append_record pairs only ok/failed lines, and runner step 5 accepts a rerun of an identity that has no ok line.
  3. RunRecord must accept these records ("นอกนั้นไม่ตรวจ"), and evaluate's input rules name the variant, the long_only base_run_id and the rollover.
  4. Calling the round-1 function keeps one oracle for both rounds.

## AC status
Status of the tests as evidence for each AC. The ACs themselves stay UNKNOWN until the implementation exists.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Unchanged by round 2; 103 round-1 tests pass on the reference |
| AC-02 | PASS with question | Unchanged; the setup-lock comparison is open (F2) |
| AC-03 | PASS with gap | `percentile`'s CONTEXT is untested (F1) |
| AC-04 | PASS | r1 F1 and F6 closed; mutants (a), x1-x3 and (i) killed |
| AC-05 | PASS | r1 F4 and F5 closed; mutants (e)-(h) killed |
| AC-06 | PASS with residual | r1 F2 and F3 (a) closed; (b) accepted as residual; architecture file passes on the reference (18 passed) |
| AC-07 | UNKNOWN | No implementation or CI run yet |

## Checks run (command → result → commit → time UTC 2026-10-24)

1. `sha256sum` of the patch and both files, `git hash-object` of both files, `git status --porcelain --untracked-files=all`, `git diff --stat` → results:
   - patch `ff1e1ca0…3b581`
   - test_research.py `97ac11c6…a4cac587` / blob `ee1acb15…52`
   - research_cases.py `82bfdec9…36b7e` / blob `0176b20b…80`
   - all equal to the handoff values
   - modified files: only the two test files plus docs/handoff/CORE-008.md (+158 / +88 / +182, 0 deletions)
   - `docs/proposals/` is git-ignored (.gitignore:10)

   → 7523407 + patch → 09:36:35.
2. `git -C <repo> apply -R --check docs/proposals/CORE-008-tests-r2.patch` → **BLOCKED** by the hook (see "Blocks"), not retried → 09:3x.
3. `git show HEAD:<path> | uv run --offline --no-sync python -I -B c8t2/ast_compare.py <path>` for both files. HEAD bytes are an exact byte prefix of the working file in both cases:
   - test_research.py: 146/146 statements identical in place, 7 appended
   - research_cases.py: 106/106 identical in place, 5 appended
   - 0 CR bytes

   → 09:37.
4. Copied the reference with `copy_tree.py`, skipping `__pycache__`. `diff -r -q -x __pycache__ <repo>/src c8t2/ref/src` → differs only in `research/` plus `strategy/h001.py` and `strategy/__init__.py` (the D1 change) → 09:38.
5. `timeout -k 10 900 uv run --offline --no-sync python -I -B c8t2/run_with.py c8t2/ref/src tests/acceptance/CORE-008 tests/golden/CORE-008 -q -p no:cacheprovider -rf` (cwd = repo root) → **109 passed in 10.71 s**; 35 sochron modules, none outside the copy → 09:39:30-09:39:41. The same run with `-k _r2_ -rA` → the 6 round-2 tests PASSED → 09:39:5x.
6. Same command twice more (each process gets a fresh hash seed under `-I`) → 109 passed, 109 passed → 09:44:5x-09:45:38.
7. Architecture file with the cwd at `c8t2/ref` (so it scans the reference) → **18 passed** → 09:45:40.
8. `uv run --offline --no-sync python -I -B c8t2/mutate.py <repo> a b c d e f g h i` → all killed (table above) → 09:40:49-09:42:21. Extras x1-x5 → 09:42:29-09:43:22. `mutate_x6.py` → 109 passed → 09:48:49-09:49:00. Failure messages checked with `--tb=short` → 09:43-09:44.
9. `probe_percentile.py` on the reference and on x4 → values in F1 → 09:44.
10. `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider --tb=line -rf` (repo root) → **110 failed, 3212 passed in 25.10 s**:
    - 105 × "AC-0n: sochron.research not implemented (No module named 'sochron.research')" at test_research.py:117 (99 round 1, 6 round 2)
    - 4 × "sochron.strategy.entry_blockers not implemented" at :124
    - 1 × architecture "…\src\sochron\research does not exist; implementation missing"
    - 0 NameError, KeyError or collection errors

    → 7523407 + patch → 09:45:48-09:46:13.
11. `bash scripts/controls/red-flags.sh origin/main` → 1 group with hits ("Lint disabled"): the three round-1 `# noqa: E731` lines (already explained in r1) and mentions inside docs. Control files touched: the three locked test files → 09:46:32.
12. Appended lines (`git diff -U0`) scanned for noqa/skip/xfail/type-ignore/except/TODO/float/print/clock/env/secret patterns → 0 hits; 0 trailing spaces → 09:47.

## Checked, nothing found (and how)

- **Append-only and scope:** hashes, blobs, byte-prefix and AST comparison (checks 1 and 3). The handoff edit is append-only.
- **Golden values, recomputed by hand from the contract text:**
  - REPORT_RERUN: B select row `1|1|0|0|1/6`; B stress row `2|1|0|1|1/1`; total = select 1 + robustness 0 + stress started 2 = `3/63`; bullets seq 2 (SB) and seq 5 (SBS), counters 0/3/2/1; F38 blank-line layout.
  - EVALUATE_CASES_R2: rows 1-9 as in the round-1 "no trades" case; row 10 `expectancy:none/0.10;max_drawdown:0/25`, False; verdict insufficient; screen True.
  - F1 premises (a stop distance and the mean both move at precision 3) hold, since the test passes on the reference and mutant (a) shifts mean_r from −0.144796 to −0.451.
- **Over-constraint:** an independent contract-only implementation passes all six tests.
  - F3 (a): the locked base is the same whether "first" means first in input or by seq, because every B and C non-select line names the same base.
  - F1's flags check: see open question 3 above.
  - F5's records are accepted by RunRecord.
  - F6: summarize reads no exit time.
- **Passing for the wrong reason:** every killed mutant fails with a message naming the intended clause (quoted in the closure table). Each fixture checks its own premises.
- **Nondeterminism:** three identical reference runs. The real generator is seeded from a content-only run_id, and tmp_path never reaches a record.
- **Red:** every new test fails for the contract reason (check 10).

## Not checked (and why)

- The `git apply -R --check` of the r2 patch: blocked. The equality to the handoff rests on the SHA256, the blobs and the byte-prefix check.
- I wrote no reference of my own. I used the round-1 reviewer's contract-only reference (independent of the round-2 author) and read against the contract only the parts the new tests exercise (baseline, evaluation, report, stats, the setup lock).
- The whole suite against the reference: I ran only CORE-008 and the architecture file. Round 1 reports 3316 passed.
- Linux and CI: Windows only, no push.
- The round-1 author's mutants and round-1 mutants M8-M16, other than their equivalents above.

## Blocks during this review

Both blocks came from `.claude/hooks/guard-bash.mjs` with this message: "Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run each action separately."
1. On `git -C "<repo>" apply -R --check docs/proposals/CORE-008-tests-r2.patch`.
2. On a `cat > c8t2/first-findings.md <<'EOF'` heredoc whose text mentioned that command.

Neither was retried or reshaped.

Ready to commit red: yes

Findings open: 2

Scratch artefacts (all under C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/c8t2/):
- run_with.py
- mutate.py
- mutate_x6.py
- probe_percentile.py
- ast_compare.py
- copy_tree.py
- red-run.txt
- ref/src
- mut/<a…i, x1…x6>/src
