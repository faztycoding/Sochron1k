# Review CORE-004 round 3 (narrow re-check of F7–F9) · base main (`origin/main` 6bd9ef8, merge-base 82a7f3e) · head aa0feb0 · reviewer: pre-review (Claude subagent `fresh-eyes-reviewer`, fresh context, read-only)

Recorded by the implementer from the subagent's final report, unchanged in substance. The owner chose this narrow
subagent re-check on 2026-10-24 because the contract's headless-session budget (6) was used up.

**Result: F7, F8 and F9 are closed. There is one new Low finding, F10, about how up to date the evidence is.**

Scope: commits `f47a8b8` (F7) and `aa0feb0` (F8, F9), checked against contract v1.2 and the r2 findings. The
reviewer edited, staged, committed and pushed nothing; `git status --porcelain` was empty before and after. Times are
2026-10-24, +07:00.

## r2 findings: verdicts

| ID | Verdict | Evidence |
|----|---------|----------|
| F7 | closed (from reading the code; the mutant run was blocked, see Blocks) | `tests/unit/costs/test_costs_unit.py:226-254`: the three status rows are unchanged; seven rows plant one bad `source`, `note` or `as_of` each (int, None, str subclass, a str date, a `datetime`, a `date` subclass) on a fresh `replace()` of the commission record, after a precondition that the model is valid, and expect `TypeError` from `unknowns`, `stress` and `check_volume`. `_check_provenance` (`model.py:111-120`) checks source, note, as_of, then status, so one planted field trips only its own check. With `model.py:193` reduced to the status check, the seven new rows fail and the three status rows pass; dropping any single field's re-check or switching to `isinstance` is also caught. No test weakened (numstat against 0c0a5b0: 66/1, the 1 deletion is the import line). All 10 rows PASSED at HEAD. |
| F8 | closed | AC-03: `--collect-only -k ac03` gives `917/1993`; per function 18 (`test_ac02_ac03_use_reads_provenance_once`) + 845 + 36 + 18 = 899 `test_ac03_*`, matching the evidence; the other per-AC counts also match. The int sentence now states the accepted F5 limitation, consistent with contract v1.2 and r2's timing (12.978 s at HEAD, 13.852 s on main). |
| F9 | closed (owner chose a short demo that Claude runs) | Demo run exactly as written: step 1 `2795 passed in 8.64s`; step 2 output identical character for character; step 3 `subclass -> TypeError 0.0 ms`, `1001 digits -> BadVolume 0.0 ms`, `exponent -> BadVolume 0.0 ms`. The file list matches the files of the CORE-004 commits in 82a7f3e..aa0feb0 (excluding the FIX-001 docs commit 4ea84b7). The delivery-state line is qualified as local and does not over-claim. |

## New findings

| ID | Sev | Kind | File:line | Evidence | Impact | Minimal fix |
|----|-----|------|-----------|----------|--------|-------------|
| F10 | Low | confirmed | `docs/evidence/CORE-004.md:12`, `:51`, `:72`, `:77-91` | The AC-05 row still said 2788 passed while the suite gives 2795 at aa0feb0; the demo and F7 mutant results named no commit and the mutant claim had no command; the Checks table ended at d33d5da (AGENTS.md: "command -> result -> commit -> time"). | Two different suite totals in the owner summary; the F7 mutant result could not be re-run from the record. The code and claims themselves are correct. | Correct the AC-05 row, and add Checks rows for the F7 regression, the mutant (command and a description of the edit) and the demo at a commit. |

## AC status (at aa0feb0)
`src/`, `tests/acceptance`, `tests/golden` and `tests/architecture` are unchanged since 4ea84b7, so the code r2 reviewed is unchanged.

| AC | Status | Why |
|----|--------|-----|
| AC-01 | PASS | 559 locked rows pass (suite 2795 passed) |
| AC-02 | PASS | 41 `-k ac02` rows pass |
| AC-03 | PASS | 917 `-k ac03` rows pass; the F7 rows cover all four record fields at use |
| AC-04 | PASS | 454 rows pass; demo step 3 refusals take 0.0 ms (not re-timed with `-rP`) |
| AC-05 | PASS | 2795 passed, 0 skipped; demo step 2 is the honest H001 result |
| AC-06 | PASS | 42 rows pass |

## Checked, nothing found
- Red flags: one prose group ("as any valid value"), as in r2; no hits in the F7 rows or the new evidence text.
- Scope: f47a8b8 touches only the costs unit test, aa0feb0 only the evidence and r2 files.

## Not checked (and why)
- Executing the F7 mutant (blocked, below); the verdict rests on reading the code plus the 10 rows passing at HEAD.
- CI, `check-locked-paths.mjs`, `test-controls.mjs`, AC-04 `-rP` timing: not requested.
- PROGRESS.md and the handoff: outside F7–F9; PROGRESS `:5` was stale (2788 passed, "รอ fresh re-review ของ r1 F1/F3", 5 of 6 sessions) and belongs to the next checkpoint.
- Demo step 3 prints only when an exception is raised, so a regression would show as a missing line (observation, not a finding).

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `git status --porcelain` | empty | aa0feb0 | 02:08 |
| `timeout -k 10 300 uv run --offline pytest tests/acceptance/CORE-004 -q -p no:cacheprovider --collect-only -k ac03` | `917/1993 tests collected` | aa0feb0 | 02:09:12 |
| the same with `-k ac01/ac02/ac04/ac05/ac06`, and grouped by function | 559 / 41 / 454 / 1 / 42 | aa0feb0 | ≈02:09 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | 2795 passed in 8.64s, exit 0 | aa0feb0 | 02:09:52–02:10:01 |
| demo steps 2 and 3, as written | as expected | aa0feb0 | ≈02:10 |
| `git diff --stat origin/main...HEAD`; `git log --name-only 82a7f3e..aa0feb0`; `git diff --numstat 0c0a5b0 HEAD -- tests/unit/costs/…`; `git diff --stat 4ea84b7 HEAD -- src tests/acceptance tests/golden tests/architecture` | file list matches; unit test 66/1; src and locked tests empty | aa0feb0 | ≈02:10 |
| `timeout -k 10 300 uv run --offline pytest tests/unit/costs/test_costs_unit.py -v -p no:cacheprovider -k checked_again_at_use` | 10 PASSED | aa0feb0 | 02:10:57 |
| `bash scripts/controls/red-flags.sh main` | exit 0; 1 prose group | aa0feb0 | ≈02:11 |
| `git status --porcelain` | empty (unchanged) | aa0feb0 | 02:11:07 |

## Blocks and deviations
- The mutant setup was blocked: `mkdir -p "$S/head/src" …; cp -r …` gave `Blocked by .claude/hooks/guard-bash.mjs: mkdir would change $S/head/src (a path that cannot be resolved here (variable or unknown directory)). The implementer may not change locked paths; ask the owner.` The reviewer stopped that step, did not reshape the command, and reasoned from the code instead. Nothing was created.

Findings open: 1 (F10 Low; answered in the PR-prep docs commit without another review round, as the reviewer suggested)

Ready for PR: yes
