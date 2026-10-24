# Review CORE-006-tests round 2 · base main · head a1c5188 (17a6db7 at the end, docs only) + applied D-006 patch r2 (uncommitted) · reviewer Claude Code (fresh session 1c932969, tests reviewer under the role swap)

Scope: the three locked test files after `docs/proposals/CORE-006-tests-r2.patch` was applied on top of the round-1 files
committed in `a1c5188`:
- `tests/acceptance/CORE-006/test_strategy_h001.py`
- `tests/golden/CORE-006/strategy_cases.py`
- `tests/architecture/test_imports.py`

I reviewed them against `docs/contracts/CORE-006-strategy-h001.md` (v1 and the v1.1 block at `:53-62`), review
`docs/reviews/CORE-006-tests-r1.md` (F1-F4) and the "Round 2 patch" section of `docs/handoff/CORE-006.md`. This is the
owner's role swap. I am not the implementer, not a test author of either round, and not the round-1 reviewer. No
implementation of CORE-006 exists (`src/sochron/strategy` is missing). This file is the only file I wrote in the
repository. Nothing is staged, nothing was pushed, and the locked files were read in place: never copied, never edited.
My scratch files are in
`C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\1c932969-93e8-41be-ab48-da2429858f24\scratchpad\`.
All times are UTC on 2026-10-24 (about 08:50-09:10 Asia/Bangkok).

**Process note.** `.agents/skills/cross-agent-review/SKILL.md` says to read the handoff only after a first round of
findings. The task named the handoff as an input, so I read it at the start. The oracle, the reference, the mutants and
the probes below are my own work from this session. I did not read the scratch files of the round-1 reviewer or of
either test author.

**HEAD moved.** At 02:03:49Z the owner committed `17a6db7` ("docs(core-005): record the merge and CI runs; PROGRESS
checkpoint"). It touches only `PROGRESS.md`, `docs/contracts/CORE-005-data-bars.md` and `docs/evidence/CORE-005.md`.
`git diff --quiet a1c5188 HEAD -- docs/contracts/CORE-006-strategy-h001.md tests src docs/proposals docs/handoff/CORE-006.md`
exits 0, and `git rev-parse HEAD:<path>` still gives the round-1 base blobs `3c766460…`, `22a0876c…` and `6d91a1e2…`.
Everything below holds for both heads. The red-flag scan was repeated at `17a6db7` (section 6).

**CORE-005 merged.** CORE-005 is now on main (PR #16, `419eee3`). The merge base is `b91cff7`, and
`git diff --stat HEAD origin/main -- src tests/acceptance/CORE-005 tests/golden/CORE-005 tests/unit` is empty. So
`Bar`, `AggregatedBar` and the defect codes did not change before the merge, and the contract Status line's "merge it in
and re-check the tests" condition did not trigger.

**Detector note (N6).** The post-run locked-path detector fired once, after this session's first command (01:50:57Z).
That command was read-only: `git rev-parse`, `git status`, `sha256sum`, `git hash-object` and `git rev-parse HEAD:<path>`.
The detector listed exactly `uncommitted M` for the three target files of the applied `docs/proposals/` patch and nothing
else. The same command's output shows all three SHA256 and blob values equal to the handoff (section 1), so I continued
as CLAUDE.md allows. It did not fire again. No guard-bash hook or deny rule blocked anything in this session.

Verdict: **Ready to commit red: yes.**
- Integrity: the hashes, blobs and reverse check match. The only locked changes against HEAD are the three target files.
- Red run: 205 failed and 2876 passed, as expected, and every failure has the contract reason.
- Round 1 unchanged: every round-1 statement and assert is AST-identical. Only the three module docstrings changed.
- F1-F4 are closed.
  - Golden series E recomputes exactly with my own exact-fraction oracle: 260 of 260 values, plus 30 of 30 trap values.
  - My contract-only reference passes all 205 CORE-006 tests on its first version, with module origins proven.
  - All 26 F1-F4 mutants I tried are killed, each by round-2 tests.

Two new Low findings stay open, F5 and F6. Both are missing checks, not wrong ones, and neither blocks the red commit.

## Round-1 findings (re-review)

| ID | r1 Sev | Verdict | Evidence |
|----|--------|---------|----------|
| F1 | Medium | **closed** | See below the table. |
| F2 | Low | **closed** | See below the table. |
| F3 | Low | **closed** | See below the table. |
| F4 | Low | **closed** | See below the table. |

**F1 (closed).**
- Golden series E (`strategy_cases.py:271-433`) uses the defaults f 16, s 64, n 20, N 96 and M 48. Its 26 bars give 25
  EMA steps and ts from t = 19.
- `test_ac02_v11_default_alphas_pin_the_ema_form_and_its_rounding[A/B/C]` (`test_strategy_h001.py:1059`) checks every
  field of every row, under both the module context and a hostile caller context.
- The test also asserts that every `EMA_TRAPS_E` value differs from its golden value, so the case cannot become vacuous.
- My oracle `oracle_e.py` reads `_E`, `PARAMS_E`, `ROWS_E` and `EMA_TRAPS_E` with `ast` only, and computes with Fractions
  rounded half even at 28 digits after each operation in the v1.1 order (section 3). Result: **ROWS_E 260 values, 0
  mismatches**, all 26 rows.
- The three rival forms each fail only `[A/B/C]` of that test (3 failed, 0 round-1 failures):
  - e + alpha(c - e);
  - one rounding per step with exact alpha;
  - one rounding per step with 28-digit alpha.
- A residual case is F6.

**F2 (closed).** Each mutant below is killed by the round-2 tests:

| Mutant | Failures |
|---|---|
| skip(warmup) without a signal | 22 |
| V-C with ts unknown counts as a signal | 1 |
| no exit before warm | 16 |
| a flat row at ATR 0 skips with atr_zero | 4 (1 round-2, 3 round-1) |

- The round-1 assert at `:937-938` (none or skip for t < 96) was not edited. Instead, the new
  `test_ac05_v11_known_answer_series_gives_none_before_its_first_signal` requires "none" for t < 96, and for V-A up to
  t = 96. So the r1 fix is in place without changing a round-1 assert.
- The docstring at `:32-39` now names v1.1.

**F3 (closed).**
- The r1 mutants are all killed: unknown position, negative t, a set of flags, any bar-like `.bar`, duck typing refused,
  and t of a wrong type.
- So are 6 more: t - 1 wrapping at t = 0, a `next_open_utc` subclass, `decide` accepting an `H001Params` subclass, a
  rows mapping, any row object, and `indicators` accepting an `H001Params` subclass.
- That is 12 of 12. Each fails only `test_ac03_v11_decide_refuses_…` (`:1201`) or `test_ac02_v11_indicators_accept_duck_typed_…`
  (`:1245`), with 1 failure per mutant.

**F4 (closed).**
- `_STRATEGY_STDLIB` (`test_imports.py:1678`) is exactly bisect, collections, collections.abc, dataclasses, datetime,
  decimal, enum, functools, itertools, operator, types and typing. `probe_checker.py` prints the loaded set.
- sochron.core, sochron.timebase and the package itself stay granted (the `_STRATEGY_LISTED` row, and my reference).
- The check is local to strategy. `_allowed_import`, `_PURE_CHECKERS`, every other checker and every round-1 table are
  AST-identical to HEAD. The new checker is called only by the new test (Grep).
- The self-test tables pass: the red run fails at `:1796`, after the self-test assert at `:1791`.
- Every planted import I tried is killed, by the round-2 test only: `import logging`, `from pathlib import Path`,
  `import sqlite3` inside a function, `import math`, `from __future__ import annotations`, `from zoneinfo import ZoneInfo`.
- The r1 probe module now gives 11 findings, one per imported module.
- The last clause of r1's proof of fix ("`_STRATEGY_ALLOWED` and `_LEGITIMATE_SOURCES` still report nothing") holds for
  the round-1 checker, which is unchanged and passes with my reference.
- The new checker reports `import math` (`_STRATEGY_ALLOWED`) and the `sys`, `time` and `zoneinfo` imports in
  `_LEGITIMATE_SOURCES`. That is by design: those modules are not on the owner-delegated list (handoff decisions 1-2).
  Its self-test checks that it adds nothing but stdlib-import findings.
- The `exec("import random")` item of r1's probe is still not seen: F5.

## New findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F5 | Low | confirmed | See below the table. | | | | | |
| F6 | Low | confirmed | See below the table. | | | | | |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

**F5: the strategy architecture check does not see code run from strings.**
- **Where:** `tests/architecture/test_imports.py:1684-1698` (`_inspect_strategy_listed_source`) and `:94-100`
  (`direct_io` and `dynamic_imports` do not include `exec`, `eval` or `compile`). Against AC-06: "no I/O, clock, random,
  MetaTrader5, network".
- **Evidence:** in `probe_checker.py`, a source with `exec(code)`, `exec("import logging; …warning('x')")`,
  `eval("len('x')")` and `compile('1', '<s>', 'eval')` gives no finding from the round-1 checker and none from the
  round-2 checker. Adding that source as `dyn.py` to my reference package: both strategy architecture tests pass
  (205 passed). `scripts/controls/red-flags.sh` has no exec, eval or compile pattern (Grep: no matches).
- **Trigger:** strategy code that runs a string, such as `exec("import random")`, or logging or file I/O built from a
  string.
- **Impact:** AC-06 is not enforced against code built from strings, and the `exec("import random")` item of r1's F4
  probe still passes. It is Low: such a call would stand out in a diff review, and the file docstring already says
  "not a general proof".
- **Minimal fix (owner's choice):**
  - (a) Strategy only: in `_inspect_strategy_listed_source`, report one finding per reference to the builtins `exec`,
    `eval` and `compile` (bare name, alias or `builtins.` form), with self-test rows. `import builtins` is already
    reported by the list.
  - (b) Record it as an accepted limitation of the static check, in the contract or the evidence.
- **Proof of fix:** (a) the `dyn.py` probe fails with one finding per call, and my reference still passes. (b) The
  limitation is written down.

**F6: the `1 − α` reading of v1.1 item 1 is pinned only where both readings agree.**
- **Where:** `tests/golden/CORE-006/strategy_cases.py:271-283` (series E uses only f 16 and s 64) and
  `tests/acceptance/CORE-006/test_strategy_h001.py:1059`. Against contract `:54` (v1.1 item 1, "α = 2/(p+1) และ 1 − α
  คำนวณครั้งเดียว") and D1 ("rounded after each operation in the written order").
- **Evidence:**
  - A reference that computes 1 − α as (p − 1)/(p + 1), rounded once, instead of 1 minus the 28-digit α passes all 205
    tests. This is mutant "F1 1 - alpha as (p - 1)/(p + 1)": 205 passed.
  - `one_minus_alpha.py`: the two readings agree at every period the tests use (8, 9, 16, 32, 39, 64). They differ by
    one unit in the 28th digit at 7 of the 82 periods H001 section 4 allows: 22, 36, 37, 43, 50, 62 and 78.
  - `one_minus_alpha_ema.py`: on E's 26 closes, the EMA then differs in 17 to 25 of 25 rows. With p = 62 it differs
    from t = 1.
  - The golden comments (`:279`) already use 1 minus the rounded α.
- **Trigger:** an implementer writes the decay factor directly as (p - 1)/(p + 1).
- **Impact:** two implementations agree at the defaults but disagree in the last EMA and TS digits when a research
  variant uses f = 22 or s in {36, 37, 43, 50, 62, 78}. That works against the contract Goal (`:18`, "two people who
  compute the same bar get the same answer"). Decisions change only near exact ties, so it is Low.
- **Minimal fix:** add a golden case at one of those periods, for example E's bars with s = 62 and f = 16. Pin `ema_s`
  (and `ts` from t = 19) at 28 digits on rows where the two readings differ, computed with 1 − α = 1 minus the 28-digit
  α, then rounded.
- **Proof of fix:** the (p − 1)/(p + 1) mutant fails, and a v1.1-faithful reference still passes.

## AC status

Status here means: would the locked tests fail if the clause were not implemented? The evidence is the tests aimed at
the clause and the mutants of my reference that they kill (section 5).

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | No change in round 2. The 4 round-1 tests are AST-identical and pass with my reference; their mutants are in review tests-r1. |
| AC-02 | PASS (gap F6) | Round 1, plus golden series E for the v1.1 EMA form and rounding (3 EMA mutants killed). Duck-typed bars and type errors for `indicators()` (v1.1 item 7; 4 mutants killed). Gap: the (p − 1)/(p + 1) reading of 1 − α survives (F6). |
| AC-03 | PASS | Round 1, plus `decide` refusing an unknown position, t out of range and every wrong argument type, subclasses included (v1.1 item 7). 8 mutants are killed, including negative t and the wrap of t - 1 at t = 0. |
| AC-04 | PASS | Round 1, plus exits while the rows are not warm (v1.1 item 8), on built rows (35 cases × t = 20 and 150) and on `indicators()` rows of the known-answer series. Mutant "no exit before warm" killed (16 failures). |
| AC-05 | PASS | Round 1, plus "none" without a signal during warm-up, whatever else fails (v1.1 item 5), and the ATR 0 rules (v1.1 item 6): none for V-A/V-C and skip(atr_zero) for a V-B breakout, including with all five reasons. 3 mutants killed. |
| AC-06 | PASS (gap F5) | Round 1, plus the explicit stdlib list for strategy. 7 planted-import variants are killed, and r1's I/O probe now gives 11 findings. Gap: string-built code (F5). |
| AC-07 | UNKNOWN | Not a test-author item: it needs the implementation, the suite and CI. With my reference loaded and cwd at the repo root, the whole suite gives 3079 passed and 2 failed. Both failures are the strategy scans of the repository's missing `src/sochron/strategy`, failing as designed (section 4). |

v1.1 items:
- 1: series E (F1 closed); residual F6.
- 2 and 3: covered in round 1.
- 4: enforced upstream; nothing to test in `strategy`.
- 5, 6 and 8: covered (F2 closed).
- 7: covered (F3 closed).
- 9: a note; nothing to test.

## 1. Integrity (commands and results)

| Command | Result | Time |
|---|---|---|
| `git rev-parse HEAD`; `git status --short --untracked-files=all` | `a1c5188fd06d…`. Only ` M` on the three target files and on the unlocked `docs/handoff/CORE-006.md` | 01:50:57Z |
| `sha256sum` on the patch and the three files | patch `51ecc15e…8ec27d`; acceptance `9b985946…9c882a`; golden `831ccd85…b298d`; architecture `e0f1cc4f…cca4`. All four equal the handoff and the task | 01:50:57Z |
| `git hash-object --path=<p> <p>` and `git hash-object --no-filters` on the three files | `ef61bef6…f494`, `9e9dadf5…d201`, `504c88a6…654d`, the same both ways; equal to the handoff | 01:50:57Z |
| `git rev-parse HEAD:<p>` for the three files | `3c766460…95de`, `22a0876c…71aad`, `6d91a1e2…b18d`: the handoff's required base blobs | 01:50:57Z |
| `git apply -R --check docs/proposals/CORE-006-tests-r2.patch` (alone) | exit 0, no output | about 01:51Z |
| `git diff --numstat HEAD` | acceptance `268 6`, golden `178 7`, architecture `143 1` (equal to the handoff's `--numstat`); handoff `203 0`. No other changed path | 01:51:04Z |
| End of session: `git status`, the four `sha256sum`, `ls src/sochron/strategy` | Unchanged; the strategy directory is still missing; HEAD `17a6db7` (docs only, see the top) | 02:04:11Z |

## 2. Round-1 meaning unchanged (AST comparison)

`ast_cmp.py` reads `git show HEAD:<path>` from stdin and the working file in place by path, so no copy of a locked file
was written. It ran at 01:54:08-01:54:15Z.

| File | HEAD statements after the docstring | Identical, in order, at the start | Appended | Asserts HEAD → new (HEAD asserts changed) | Test functions HEAD → new (removed) | skip/xfail/importorskip |
|---|---|---|---|---|---|---|
| acceptance | 82 | 82 | 12: `_Attrs`, `_DateTime`, `_FrozenSet`, `_NO_SIGNAL`, 8 tests | 85 → 99 (none) | 24 → 32 (none) | none |
| golden | 18 | 18 | 5: `PARAMS_E`, `_E`, `BARS_E`, `ROWS_E`, `EMA_TRAPS_E` | 0 → 0 | 0 → 0 | none |
| architecture | 57 | 57 | 6: `_STRATEGY_STDLIB`, `_inspect_strategy_listed_source`, `_inspect_as_listed_strategy`, `_STRATEGY_UNLISTED`, `_STRATEGY_LISTED`, 1 test | 25 → 29 (none) | 14 → 15 (none) | none |

- No HEAD function changed in any of the three files (46 → 55, 2 → 2 and 77 → 80 functions).
- **Every round-1 assert is unchanged, and no round-1 statement changed.** The only non-appended change in each file is
  its module docstring:
  - Acceptance: 6 lines are replaced by 11. The "golden EMA values are exact" sentence is now limited to S, P and G.
    The "Left untested" paragraph now lists what v1.1 answered and what is still untested.
  - Golden: the D2 line gains the v1.1 form; the "every EMA value is exact" paragraph is limited to S, P and G; one
    series E sentence is added.
  - Architecture: the last line is extended and one line added.
- The new tests reuse the round-1 tables `_ENTRY_EDGES`, `_EXIT_CASES`, `_ALONE`, `_KNOWN_CHANGES` and `_KNOWN_FLAGS`,
  which are AST-identical to HEAD.

## 3. Golden series E (F1)

`oracle_e.py` is my own code. It reads the golden file with `ast.literal_eval` of `PARAMS_E`, `_E`, `ROWS_E` and
`EMA_TRAPS_E` only; it never imports or runs it. It computes with Fractions and my own half-even rounding to 28
significant digits after each operation, with no `decimal` module. The rules:
- α = round(2/(p+1)), then 1 − α = round(1 − α).
- EMA[t] = round(round(α·c) + round((1 − α)·e)).
- TR from the previous close.
- The ATR seed is the per-addition-rounded sum divided by n; then ATR[t] = round(round(round(ATR·19) + TR) / 20).
- TS = round(round(EMA_f − EMA_s) / ATR).

It ran at 01:53:37Z.
- α_16 0.1176470588235294117647058824, 1 − α_16 0.8823529411764705882352941176; α_64 0.03076923076923076923076923077,
  1 − α_64 0.9692307692307692307692307692. These equal the golden comments (`:276-280`).
- t = 1: 470.9458823529411764705882355 + 3530.338235294117647058823529 = 4001.2841176470588235294117645, a tie that rounds
  to …764; for EMA_64, 123.1704615384615384615384615 + 3877.940769230769230769230769 = …2305, a tie that rounds to …230.
  These equal the comment at `:314-326`.
- The first 11 rows (t = 0-10) and t = 19, 20 and 25 were printed and compared, for example:
  - t = 10: EMA_16 4002.488536095313312849411064, EMA_64 4001.506205512971546322602740;
  - t = 19: ATR 2.772, ts 2.015764528692296812833647186;
  - t = 25: ATR 2.8856547001875, ts 2.197563515896883418557795345.
  The TR list equals the comments.
- **All 26 rows × 10 values (EMA_f, EMA_s, ATR, TS, the four Donchian values, the median and warm) = 260 values: 0
  mismatches.** `atr`/`ts` are None for t < 19, the Donchian values and the median are None, and warm is False
  throughout.
- **EMA_TRAPS_E: 30 values, 0 mismatches,** and none equals its golden value. Each rival form, run over the series and
  compared with v1.1 (first difference at t = 1 in every form):

  | Rival form | EMA_16 rows that differ | EMA_64 rows that differ | ts rows that differ |
  |---|---|---|---|
  | e + α(c − e) | 24/25 | 25/25 | 7/7 |
  | one rounding, exact α | 24/25 | 25/25 | 7/7 |
  | one rounding, 28-digit α | 24/25 | 21/25 | 7/7 |

  This confirms the handoff's "24 of 25, 21-25 of 25, all 7".
- `one_minus_alpha.py` and `one_minus_alpha_ema.py` (02:01Z) back F6.

## 4. Satisfiability: my contract-only reference

- **Reference.** `ref\src\sochron\strategy\` holds `__init__.py`, `params.py`, `indicators.py` and `h001.py`, written in
  this session from the contract and v1.1 only:
  - The arithmetic runs in `localcontext(CONTEXT)` (precision 28, ROUND_HALF_EVEN), with the v1.1 EMA as
    `alpha * close + one_minus * previous`.
  - Bars are duck-typed: `.bar` must be exactly a `core.Bar` and `.flags` exactly a frozenset.
  - The type checks are exact `type(x) is …`. `decide` checks its argument types first, then the position value and
    the range of t, then the type of row t.
  - It imports only collections.abc, dataclasses, datetime, decimal, types, typing, `sochron.core` and `sochron.timebase`.
- **Runner.** `run_ref.py` runs under `uv run --offline --no-sync python -I -B` from the repo root:
  - It asserts that the repository has no `src/sochron/strategy`.
  - It imports `sochron` from the repository's `src` and puts the scratch `src/sochron` first on `sochron.__path__`.
  - It runs pytest on the locked files by path, with `-p no:cacheprovider --rootdir=<repo> -c <repo>/pyproject.toml`.
  - It prints and checks the origin of every `sochron` module before and after pytest.
  - It makes the scratch root the cwd, because both strategy scans read `Path.cwd() / "src"`, unless `--cwd=` says
    otherwise.

| Run | Result |
|---|---|
| The two locked CORE-006 files, cwd = the scratch root (01:56:40Z) | 214 passed, 4 failed. The 4 failures are the timebase, costs, risk and core/snapshot scans, which look under the scratch cwd where those packages do not exist (runner artefact). Every CORE-006 test passed |
| The 205 CORE-006 tests: the acceptance file and the two strategy architecture tests (01:56:57Z) | **205 passed in 1.18s.** Origins: the 4 `sochron.strategy*` modules come from the scratch reference, and the 13 others from the repository's `src`. "origin problems: none" before and after |
| The whole suite, cwd = repo root (01:57:05Z) | **3079 passed, 2 failed in 7.22s.** The 2 failures are the strategy scans at `:1656` and `:1796` ("…\src\sochron\strategy does not exist; implementation missing"), as designed. Origins clean: 17 modules before and 27 after |

The reference passed in its first version. No reference code was changed to fit the tests.

## 5. Mutants

`mutants.py` copies the reference for each mutant and makes textual changes (each must match exactly once) or adds a
file. It runs the 205 CORE-006 tests through the same runner (02:00:04-02:00:48Z, origins clean in every run; log
`mutants_out.txt`). Round-2 tests are those named `*_v11_*` and `test_ac06_r2_*`. Result: **26 of 26 F1-F4 mutants are
killed**, 25 of them by round-2 tests only. Two survive: one is F6 and the other is the F5 probe.

| Mutant | Result (failed tests) |
|---|---|
| F1 EMA as e + α(c − e) | killed: 3, all round 2 (`…default_alphas…[A/B/C]`) |
| F1 one rounding per step, exact α (precision 90) | killed: 3, same |
| F1 one rounding per step, 28-digit α | killed: 3, same |
| F1 1 − α as (p − 1)/(p + 1) | **survives** (205 passed): F6 |
| F2 skip(warmup) without a signal | killed: 22, all round 2 (item-5 tests, known-series none, ATR 0, decide at t = 0) |
| F2 V-C breakout with ts unknown is a signal | killed: 1 (ATR 0 test) |
| F2 a flat row at ATR 0 skips with atr_zero in every variant | killed: 4 (1 round 2, 3 round 1) |
| F2 no exit before warm | killed: 16, all round 2 |
| F3 negative t reads rows from the end | killed: 1 (`…decide_refuses…`) |
| F3 t - 1 wraps to the last row at t = 0 | killed: 1, same |
| F3 unknown position accepted as flat | killed: 1, same |
| F3 t of an int subclass or bool accepted | killed: 1, same |
| F3 next_open_utc subclass accepted | killed: 1, same |
| F3 decide accepts an H001Params subclass | killed: 1, same |
| F3 decide accepts rows as a mapping | killed: 1, same |
| F3 decide accepts any row object | killed: 1, same |
| F3 duck typing refused (AggregatedBar by class name) | killed: 1 (`…duck_typed…`) |
| F3 any bar-like `.bar` accepted | killed: 1, same |
| F3 a set of flags accepted | killed: 1, same |
| F3 indicators accepts an H001Params subclass | killed: 1, same |
| F4 `import logging` | killed: 1 (`test_ac06_r2_…`: "line 3: forbidden stdlib import logging") |
| F4 `from pathlib import Path` | killed: 1 ("forbidden stdlib import pathlib") |
| F4 `import sqlite3` inside a function | killed: 1 ("line 59: forbidden stdlib import sqlite3") |
| F4 `import math` | killed: 1 |
| F4 `from __future__ import annotations` | killed: 1 |
| F4 `from zoneinfo import ZoneInfo` | killed: 1 |
| F4 r1's probe module `leak.py` (asyncio, ftplib, logging, os, shutil, smtplib, sqlite3, threading, urllib.request, xmlrpc.client, pathlib) | killed: 1, with 11 findings, one per module |
| F5 probe `dyn.py` (exec, eval, compile of strings) | **survives** (205 passed): F5 |

In every F4 run the round-1 strategy test still passed, which shows that only the round-2 list catches these imports.

`probe_checker.py` (02:04:06Z) loads the architecture module by path and runs both checkers on chosen sources:
- `_STRATEGY_ALLOWED` and `_LEGITIMATE_SOURCES`: round 1 reports nothing. The list adds only `math`, `zoneinfo` (×2),
  `sys` and `time` (×2) stdlib-import findings.
- exec/eval/compile: no finding from either checker.
- `import builtins` and `import importlib`: the list reports them.
- `__import__` and `importlib.import_module`: already reported in round 1.
- `getattr(__builtins__, 'open')`: no finding. This is the documented limitation ("Dynamic access … is not detected").

## 6. Red run and red flags

`PYTHONDONTWRITEBYTECODE=1 timeout 600 uv run --offline pytest tests -q -p no:cacheprovider` (repo root,
02:02:00-02:02:15Z, HEAD `a1c5188`) → exit 1, **205 failed, 2876 passed in 14.80s**. There were 0 errors and 0
skipped. Log: `red_full.txt`.
- **203 failures in the acceptance file**, each with exactly the `pytest.fail` message "AC-0x: sochron.strategy not
  implemented (No module named 'sochron.strategy')": AC-01 4, AC-02 20, AC-03 28, AC-04 77, AC-05 72 and AC-06 2. The
  AC prefix of each failing test name matches its message. 62 are round-2 (`_v11_`) tests.
- **2 failures in the architecture file**: the round-1 and round-2 strategy tests. They fail at `:1656` and `:1796`,
  `assert directory.is_dir()` ("…\src\sochron\strategy does not exist; implementation missing"), after their checker
  self-test asserts (`:1651`, `:1791`) passed.
- No TypeError, AttributeError, NameError, SyntaxError or ImportError lines.
- 63 round-2 and 142 round-1 failures: equal to the handoff's expectation.

`bash scripts/controls/red-flags.sh origin/main` ran at 02:02:33Z (HEAD `a1c5188`) and again at 02:04:24Z (HEAD
`17a6db7`). Both exit 0, merge base `b91cff7`. The script diffs the merge base against the working tree, so the
uncommitted round-2 lines were scanned. 2 pattern groups have hits, both in prose:
- **"Lint disabled":** `docs/reviews/CORE-006-tests-r1.md`. The word "noqa" in that review's own account of CORE-005
  prose.
- **"Destructive or bypass commands":** `docs/handoff/CORE-006.md`. The GNU tar flag `--force-local`, named in the
  round-1 author's incident notes. It is not a command run here.

The other groups were not printed, which means no hits:
- skipped or focused tests, type checks disabled;
- placeholder or mock in production code, swallowed errors;
- possible secrets, secret-like values, client-exposed names;
- the order or account surface.

The rest of the output:
- "Deleted or renamed test files": none.
- "Untracked files": none.
- "Control files touched": the three CORE-006 test files.
- With the Grep tool on the three files: non-ASCII, CR or tab: 0. On the acceptance and golden files:
  skip/only/xfail/importorskip, TODO/FIXME/HACK/XXX, placeholder/dummy/mock/stub, type-ignore and noqa
  (case-insensitive): 0 hits.

## Checked, nothing found (and how)

- **Integrity.** Hashes, blobs, base blobs, the reverse check, and that only the three target files are locked changes
  against HEAD (section 1). Still the same at the end of the session.
- **No contradiction with the contract.**
  - My v1.1-faithful reference passes all 205 tests on its first version.
  - Each round-2 rule traces to a clause:
    - none without a signal, whatever else fails: v1.1 item 5 and convention 4;
    - TypeError for subclasses, a dict as rows and a datetime subclass: contract `:35`;
    - StrategyError for t outside 0 .. len - 1 and for unknown positions: v1.1 item 7;
    - `.bar` exactly a `core.Bar`: v1.1 item 7.
- **Round 1 unchanged in meaning** (section 2). No round-1 assert changed. The r1 F2 fix tightened the
  t < 96 expectation with a new test instead of editing `:937-938`.
- **No vacuous new test.**
  - Series E checks its own traps.
  - The known-answer tests assert `warm` False and `ts` 0 or None where they rely on it.
  - The duck-typing test asserts that flags and a warm row occur.
  - Every new test is killed by at least one plausible mutant (section 5).
- **Arithmetic in the comments.** The t = 1 and t = 2 steps, both ties, the wrong forms at t = 1, the ATR seed and steps
  and TS[19] (`:314-343`) recompute exactly (section 3).
- **The two known-answer claims** ("both EMAs stay 4000 under v1.1, so ts is exactly 0 for t = 9-95") are checked
  through my reference, which passes the asserts `rows[9].ts == 0` and `rows[95].ts == 0`. I also redid the EMA_8 and
  EMA_32 steps at close 4000 by hand: 888.8888888888888888888888888 + 3111.111111111111111111111111 rounds to 4000, and
  242.4242424242424242424242424 + 3757.575757575757575757575758 rounds to 4000.
- **F4's list is exactly the one given and is local to strategy** (section 5 and the Grep for its callers).
  `sys.stdlib_module_names` is the same list on every platform, so the check does not depend on the CI runner's OS.
- **Encoding and red flags** (section 6).
- **Repository unchanged by my runs.** `git status` was the same after each run, the hashes were unchanged at 02:04:11Z,
  and the runs used `-B`/`PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`.

## Not checked (and why)

- **Linux CI.** The tests have not run on the CI runner; only Windows runs here. Nothing platform-specific was seen.
- **Round-1 mutants for AC-01 and for the rest of round 1.** I did not repeat them: the round-1 tests are AST-identical
  to the ones review tests-r1 checked with 20 mutants. My reference passing them is my only new evidence there.
- **Golden rows of S, P and G by hand.** They are unchanged from round 1 and were checked in review tests-r1. Here they
  are checked only through my Decimal reference.
- **The two readings of 1 − α for periods other than those the tests use.** I checked them only arithmetically (F6),
  not through a golden row, because none exists.
- **Untested by the contract's silence** (the acceptance docstring `:37-39`): flag strings that are not validation
  defect codes, non-string flags, a timeframe other than 15, and a naive `next_open_utc`. My reference raises
  StrategyError for a timeframe other than 15, but no test needs it.
- **Speed on about 170,000 M15 bars.** The contract gives this to a unit test. My naive reference ran the 205 tests in
  1.2 s.
- **The scratch files of the test authors and of the round-1 reviewer.** I did not read them, by design.
- **The round-2 author's guard-bash block** (handoff "Blocks and incidents"). It concerns their scratch setup. I did not
  judge their handling; the owner confirms it. The applied files match the handoff's hashes, and my AST comparison is
  independent of their tree.

Ready to commit red: yes

Findings open: 2
