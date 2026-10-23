# Review CORE-004 round 2 · base main (`origin/main` 6bd9ef8; merge-base 82a7f3e) · head 4ea84b7 · reviewer Claude Code (fresh session, reviewer under the PLAN-001 role swap)

Scope: the answers to round 1 (`docs/reviews/CORE-004-r1.md`). These are `f627350` (F1), `d33d5da` (F3) and
`eb654d5` (F2 evidence, implementer notes, contract v1.2 with the owner's F3–F6 decisions). I also checked what
those commits could break around them. `4ea84b7` is a FIX-001 post-merge docs commit; I read it only where
PROGRESS describes CORE-004, and it changes no file under `src/` or `tests/` (`git diff --stat d33d5da 4ea84b7 -- src tests`
is empty). I am not the implementer, not a test author, and not an earlier reviewer of this task. I wrote only
this file. I staged, committed and pushed nothing. Scratch evidence is under
`C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\cffff04e-f98d-4109-b057-86eabde696c6\scratchpad\`.
`tools\` holds my probe scripts, `out\` holds their outputs, and `trees\` holds `src/sochron` from `git archive`
of HEAD, 5f7a382 and origin/main. `trees\pre_f1` and `trees\pre_f3` are HEAD with `costs/model.py` replaced by
`git show 0c0a5b0:` and `git show f627350:` (the parents of the two fixes). Every scratch file's `git hash-object`
equals its commit's blob. `trees\mut_status_only` is a mutant (F7). All times are 2026-10-23, +07:00.

**Result.** F1 and F3 are fixed. Each regression test fails on its parent's code and passes now, and my own
probes confirm both fixes. F2, F4, F5 and F6 are recorded as the owner decided. The F3 change alters no honest
result and no error precedence. I compared against origin/main, 5f7a382 and f627350 (seed 20261023). The change
adds about 2 µs per model check and reads provenance no more often. The suite gives **2788 passed**. The code
has no open defect. Three new Low findings remain:
- F7: the F3 regression test pins only `status`. A mutant that re-checks only `status` at use passes every test.
- F8: two statements in `docs/evidence/CORE-004.md` do not match the repository.
- F9 (question): the evidence has no owner demo, no file list and no delivery-state line.

## Round-1 findings: verdicts

| ID | Verdict | Evidence |
|----|---------|----------|
| F1 | **closed** | **Diff.** `model.py:156-161` reads `model.provenance` once into `container`, then runs `isinstance(container, Mapping)` and `dict(container)`. **Regression.** `test_provenance_attribute_is_read_once_per_check` on `trees\pre_f1` (0c0a5b0's model.py): `Failed: DID NOT RAISE TypeError` (`test_costs_unit.py:211`). At HEAD: passed. **My probes** (`tools\probe_f1.py`, run on pre_f1 and on HEAD): **P1a.** A real Mapping is planted; its `__class__` property (read by `isinstance`) swaps the attribute to a list of pairs. Before the fix, the planted Mapping is never iterated and all 9 model-taking callables return results built from the list. At HEAD it is iterated once and the list is never used (only the next call sees it: `TypeError: provenance must be a Mapping, not list`). **P1b.** The swap is to a dict where commission is `measured`. `unknowns()` before the fix omits commission (the swapped-in copy). At HEAD it lists commission (the checked object). **P1c.** Provenance is still read first: a `volume_step` changed during that first read is seen by the check (`0` → `CostsError`; `0.02` → `BadVolume … not a multiple of 0.02`). **P1d.** A counting `CostModel.__getattribute__` shows reads of `provenance` per call going from 2 to 1 for all 9 callables and for construction. `stress()` reads its input once; its new model reads its own once in its constructor check. **P1e.** One traversal per call (`keys` once, 11 distinct `__getitem__`). Note: at HEAD the unit test's `TypeError` comes from `dict()` on the planted non-iterable object, which is the object that was checked. The test separates before from after; P1a and P1b are the direct proof. |
| F2 | **closed** | `docs/evidence/CORE-004.md` and the "Implementer notes" in `docs/handoff/CORE-004.md:358-379` exist at `eb654d5`. Together they give contract v1.2, the commits, each command with its result, commit and time, the decisions (model checked first, snapshot reuse, ints not bounded, messages, F4), the risk unit-test edit, the r1 answers and what was not tested. That is every item in r1's minimal fix. Two statements in it are wrong (**F8**). The parts of the AGENTS.md report format that are still missing (owner demo, files changed, delivery state) are tracked as **F9**, so F2 does not stay open for them. |
| F3 | **closed** | **Diff.** `_check_provenance` (`model.py:111-120`) is the construction rule. It runs from `Provenance.__post_init__` (`:108`) and for every record inside `_check_model` (`:193`). **Regression.** `test_provenance_records_are_checked_again_at_use` (3 rows) on `trees\pre_f3` (f627350's model.py): 3 failed, `DID NOT RAISE` at `:233` (`unknowns`). At HEAD: 3 passed. **My probe** (`tools\probe_f3.py`): 12 record defects, each planted with `object.__setattr__` after construction. They are: status as a str subclass equal to nothing, a plain str subclass, `"bogus"`, `None` and `1`; `as_of` as a `datetime`, a `date` subclass and a str; `source` as `1` and as a str subclass; `note` as `None` and as a str subclass. Each runs through 10 uses: a new `CostModel` built from the fields, plus the 9 callables. At f627350, **0/12** defects give the construction error: every use returns, `unknowns()` drops the assumed commission for status defects, and a new `CostModel` accepts the changed record. At HEAD, **12/12** defects give exactly the construction error at all 10 uses. A record changed through a `replace(H001_COSTS)` copy is shared with the singleton. Before the fix, `unknowns(H001_COSTS)` hid commission; now `H001_COSTS` raises `BadProvenance` at use. I restored the record after the probe. Test coverage of this fix: **F7**. |
| F4 | **closed** (accepted, recorded) | Contract v1.2 `:39` adds a row: a non-`str` status → `TypeError` (CORE-002 gave `BadProvenance`); a `str` outside the 4 values stays `BadProvenance`. The code cites it at `model.py:117`, and the evidence at `:21` and `:29`. Behaviour (`tools\prov_precedence.py`, 240 field combinations): HEAD vs f627350 has 0 differences, so the refactor kept the check order. HEAD vs origin/main has 14 differences: 4 non-str status rows (`TypeError`, was `BadProvenance`) and 10 `datetime` `as_of` rows (required by AC-01). `"bogus"` stays `BadProvenance`. The F3 unit row pins `status=None` → `TypeError` at use, through the same function construction runs. No unit row calls `Provenance(..., status=None)` directly; that is optional. |
| F5 | **closed** (accepted limitation, recorded) | Recorded in contract v1.2 `:66`, evidence `:30` and PROGRESS `:5` ("F5/F6 ข้อจำกัด"). I timed it again (`tools\f5_timing.py`, one child process per case). `points_to_money(10**1000000, 0.02, H001_COSTS)` takes **12.978 s** at HEAD and **13.852 s** on origin/main, so the limitation is unchanged and predates the task. A model with `spread_fallback_points = 10**1000000` costs 0.000 s at construction and 13.336 s at use. The contract's list "(points, sides, nights, factor)" covers this through "points", and its "E1 ต้องตรวจตอนสร้าง" puts the size check on E1 when it builds the model. One statement in the evidence contradicts this limitation: **F8**. |
| F6 | **closed** (accepted limitation, recorded) | Contract v1.2 `:66` records it as the owner decided: a metaclass can choose the error class, the value is always refused, risk shares the pattern, and in-process hostile code is out of scope (CORE-003 v1.7, E1 L2). "Always refused" holds. Every `type(…).__name__` in costs is on a `raise` path (`model.py:64, 83, 107, 116, 160, 166, 172, 212`; `charges.py:55, 61, 124`). The only `except` in costs is `except Rounded` at `model.py:91`, around `_DIGITS.plus` on an exact Decimal. So a metaclass name cannot turn a refusal into a returned value. `_check_provenance` adds no new name lookups beyond those already listed. I did not re-run r1's P3. |

## New findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F7 | Low | confirmed | `tests/unit/costs/test_costs_unit.py:222-238` (the only F3 regression); `src/sochron/costs/model.py:190-193` | The regression plants only `status` values (`"bogus"`, `None`, a str subclass). No locked test plants a record field at use; r1 and tests-r1 both list this. In mutant `trees\mut_status_only`, `_check_provenance(record)` in `_check_model` is replaced by the status check alone. Running `pytest tests/acceptance tests/golden tests/unit` from that tree gives **2781 passed** (2,780 repository tests plus my import guard): the mutant survives. `tools\probe_f3.py` on the mutant gives only **5/12**. The 7 `as_of`, `source` and `note` defects return values at all 10 uses. | A later edit narrows the use-time record check, for example to `status`, the only field `unknowns()` reads. | The contract v1.2 row "ตรวจ record ซ้ำด้วยกติกาเดียวกับตอนสร้าง" could regress for `as_of`, `source` and `note` without any test failing. The code at HEAD is correct (12/12). | In `tests/unit/costs` (an allowed path), add rows to the existing test, or a sibling test, that plant `as_of=datetime(2026, 10, 21)`, `source=1` and `note=None` after construction and expect `TypeError` at use. Use the same three callables, or all 9. | The mutant `trees\mut_status_only` fails the new rows. HEAD passes them. |
| F8 | Low | confirmed | `docs/evidence/CORE-004.md:19`, `:10` | (1) `:19` says ints are not bounded "เพราะแปลงตรงและไม่ช้า (unit test ของผู้ทำ)". That unit test (`test_int_arguments_are_exact_and_not_size_bounded`) uses `10**1500` only. A 1,000,000-digit int takes 12.978 s at HEAD (F5 above). Row F5 of the same file (`:30`) and contract `:66` record about 15 s as an accepted limitation. (2) `:10` says "tests ล็อก AC-03 (840 แถว)". `pytest tests/acceptance/CORE-004 --co` gives 899 AC-03 rows: 845 in `test_ac03_every_use_revalidates_a_changed_field` (13 uses × 65 defects), 36 in `…_read_before_the_other_fields` and 18 in `…_keys_revalidated_at_use`. The other counts I checked are correct: AC-01 has 559 rows, and all 559 fail against origin/main's code (`trees\main`: 559 failed); the total is 1,993 rows (1,970 + 23, as PROGRESS says). | Reading the evidence. | An owner-facing document says in one line that ints are not slow, and in another that million-digit ints take about 15 s. The PR body will be built from these files. The row count is cosmetic, but evidence must be exact (F01/F17). | Edit the two lines. For `:19`: ints are not size-bounded; in-domain million-digit ints take about 13–15 s per call (F5, accepted limitation). For `:10`: 899 AC-03 rows (845 in the matrix). | The two lines match `pytest --co` and the F5 limitation. |
| F9 | Low | question | `docs/evidence/CORE-004.md` (whole file); `.claude/skills/implement-task/SKILL.md:39-43`; precedent `docs/evidence/CORE-002.md:19`, `:34`, `docs/evidence/CORE-003.md:23`, `:41` | The evidence package has no "Demo สำหรับเจ้าของ" section (implement-task evidence item 3: numbered steps with expected results and at least one negative case). It also has no file list ("สิ่งที่ส่งมอบ" in CORE-002/003; AGENTS.md report item 4) and no delivery-state line (report item 7; it appears only in the contract's Status line). r1 F2's proof of fix asked for the AGENTS.md completion report. Items 1–3, 5 and 6 are present, and item 8 is partly present (next action in the handoff). | — | Before merge, the owner has no hands-on way to see the new refusals. Every other piece of evidence exists. | The owner chooses. (a) Add a short Thai demo: one honest `round_trip_cost` result unchanged; a `Decimal` subclass refused with `TypeError`; a record changed after construction refused at use. Also add a file list and a delivery-state line. (b) Waive the demo for this hardening task and record the waiver in the evidence or PROGRESS. | (a) The section exists and its steps run as written. (b) The waiver line exists. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

All results are at `4ea84b7` (code identical to `d33d5da`). This is local L2 evidence; CI has not run on this head.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | The 559 locked AC-01 rows pass in the suite, and all 559 fail against origin/main's costs (`trees\main`), so they test the change. F6 (metaclass name) is an accepted limitation. The new `_check_provenance` uses exact-type checks only. |
| AC-02 | PASS | The locked AC-02 rows pass. P1e: one traversal per call, each key once. F1 is closed: the attribute is read once, and the object copied is the object checked. |
| AC-03 | PASS | The 899 locked AC-03 rows pass. F3 is closed: record fields are checked again at all 10 uses, with the construction error (12/12). Coverage gap of the F3 regression: F7. |
| AC-04 | PASS | 426 timed refusals pass (`-rP` run). The slowest is 0.0049 s (`test_ac04_huge_on_grid_lots_rejected_before_rational_conversion`); every other call is at most 0.000053 s. F3 adds no Decimal handling. |
| AC-05 | PASS | **2788 passed, 0 skipped**. `git diff origin/main -- tests/acceptance/CORE-002 tests/golden/CORE-002 tests/acceptance/CORE-003 tests/golden/CORE-003` is empty (0 bytes). Differential (seed 20261023): 3,000 random honest models × 11 calls × 3 caller contexts give **0** differences in result `as_tuple`, error type or caller-context state against origin/main, 5f7a382 and f627350. |
| AC-06 | PASS | The 42 locked AC-06 rows pass. `_check_provenance` messages name types only and never format a value. |

## Checked, nothing found (and how)

- **Honest results and error precedence after F3.** `tools\diff_run.py`, seed 20261023, run once per tree and
  compared with `tools\compare.py`.
  - Section H: 95,712 call outcomes from 3,000 random models. Containers are dict, `MappingProxyType` or a custom
    Mapping. Model ints reach `10**40`. Lots are on-grid, off-grid, out of range, NaN or Infinity. Contexts are
    default, hostile (prec 3, ROUND_DOWN, Emax 10, no traps) and tight (every trap). 46,488 calls return and
    49,224 raise.
  - Section P: 20,000 cases of 1 to 4 bad plain-typed arguments with a valid model.
  - Section Q: 20,000 cases of 1 to 4 `CostModel` field defects after construction (records untouched), half of
    them with one bad argument.
  - HEAD vs 5f7a382 and HEAD vs f627350: **0** differences in H, P and Q.
  - HEAD vs origin/main: 0 in H and P. Q has 12,502 differences, which is expected: origin/main does not check
    the model at use. In that run origin/main also left the `InvalidOperation` flag set in the thread's default
    context; HEAD does not.
  - With records valid, F3 runs last in `_check_model`, so no earlier error changes. With a record defect, the
    model error now comes before any argument error (probe: `status=None` with lots NaN gives `TypeError`, was
    `BadVolume`). A model field defect still comes before a record defect (`volume_step=0` with
    `status=None` gives `CostsError`). This is the contract's "model first" order.
- **Time cost of F3.** `tools\overhead.py`, best of 7 × 20,000 calls, two rounds, f627350 → HEAD: construction
  7.6 → 9.4 µs, `check_volume` 7.8 → 9.7 µs, `spread_charge` 8.9 → 10.8 µs, `unknowns` 8.5–10.3 → 9.7–9.9 µs.
  `round_trip_cost` (17.8–27.2 µs) and `stress` (17.4–28.1 µs) are noisy on both trees. That is about 2 µs per
  model check. origin/main: `check_volume` 0.5 µs, `round_trip_cost` 10.1 µs.
- **Provenance reads.** F3 iterates the validated `snapshot` (a dict costs owns), never the caller's container:
  P1d gives one attribute read, P1e one traversal. After `dict(container)` returns, no caller code runs in
  `_check_model` or in the use that follows. The remaining checks are exact-type tests, comparisons of exact
  `Decimal`/`int`, and membership of an exact `str` in a frozenset of `str`. So the record fields used are the
  ones just checked. Mutations made by the caller's Mapping during `dict()` happen before the record check, so
  that check sees them.
- **"Provenance first" after F1.** P1c, and the locked `test_ac03_provenance_is_read_before_the_other_fields`
  (36 rows) passes.
- **Scope (F06) and tests (F02).**
  - f627350 and d33d5da touch only `costs/model.py` and `tests/unit/costs/test_costs_unit.py`; eb654d5 touches
    only the contract, the evidence and the handoff. All are allowed files.
  - Unit-test diffs add lines only: 49/0 since 0c0a5b0, and 72/0 against origin/main. The risk unit test is 4/1,
    as approved in v1.1.
  - `tests/acceptance`, `tests/golden` and `tests/architecture` are unchanged since 0c0a5b0.
  - `costs/__init__.py`, `costs/errors.py` and `sochron/{risk,timebase,core}` are unchanged against origin/main.
  - There is no dependency or lockfile change.
- **PROGRESS's CORE-004 entry** (`:5`, `:277`) matches the repository: 1,970 + 23 = 1,993 locked rows (1,993
  collected), 2788 passed, F1 and F3 regressions fail before and pass after (re-run above), F4 accepted, F5 and
  F6 limitations. `docs/proposals/CORE-004-pr-body.md` does not exist yet; PROGRESS lists it as a next step.
- **Contract v1.2 text against the owner's decisions** (r1 recommendations: F3 fix, F4 (a), F5 (a), F6
  limitation): it matches, and it marks acceptance as unchanged. The Status line says "implemented and verified
  locally", qualified as local; CI remains the verifier.
- **Observations, not findings** (in-process changes, out of scope v1.7):
  - A record field deleted with `object.__delattr__` raises `AttributeError` at every use. A deleted `note` falls
    back to the class default `""` and is accepted.
  - A status changed to another valid value (`"assumed"` → `"measured"`) still drops out of `unknowns()`. No
    construction rule can refuse a valid value.
  - Record errors at use do not name the record's key; this affects diagnostics only.
- **Red flags.** `bash scripts/controls/red-flags.sh origin/main` reports one group, "Type checks disabled",
  with five hits. All are prose: "as any valid value" in the locked test docstring, and the evidence, handoff
  and reviews that quote it. There are no hits in `src/` or in the new unit tests. The control-file list shows
  the locked CORE-004 test file, which is expected for a D-006 patch; the PR needs the label.

## Not checked (and why)

- **CI on this head.** Nothing is pushed, and pushing is not in this role.
- **`node scripts/controls/check-locked-paths.mjs`, `test-controls.mjs`, the owner demo, merge and deploy.**
  Not requested. The locked-path check is expected to fail until the PR carries its label.
- **r1's metaclass probe (F6, P3).** I did not re-run it. I checked the accepted text and the raise paths only.
- **Other threads changing a model or record between the check and its use.** In-process hostile code is out of
  scope v1.7.
- **Other platforms, free-threaded CPython, and timing on the CI runner.** All numbers come from this machine
  (Windows 11, CPython 3.12.15 via uv).
- **A full mutation run.** I ran one mutant (F7) only.

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `git status --short --untracked-files=all; git log --oneline -14; git rev-parse HEAD origin/main; git merge-base HEAD origin/main` | clean; HEAD 4ea84b7, origin/main 6bd9ef8, merge-base 82a7f3e | 4ea84b7 | 20:1x |
| `git archive <rev> src/sochron \| tar -x -C <scratch>\trees\<t>`; `git show 0c0a5b0:src/sochron/costs/model.py > …\trees\pre_f1\…\model.py`; same for `f627350:` into `pre_f3`; `git hash-object` vs `git rev-parse <rev>:<path>` | PASS: every scratch file equals its blob | – | 20:1x |
| `timeout -k 10 300 uv run --offline --no-sync pytest -c <tree>\pytest.ini --rootdir <tree> -q -p no:cacheprovider --tb=line -rA <guard> <F1 test> <F3 test>` for pre_f1, pre_f3, head | pre_f1: F1 and F3 fail (4 failed); pre_f3: F1 passes, F3 fails (3 failed); head: 5 passed. The guard proved each run imported its own tree. | scratch | 20:19:03–20:19:15 |
| `uv run --offline --no-sync python -I tools\probe_f1.py trees\{pre_f1,head}\src` | F1 closed (P1a–P1e above) | scratch | 20:20:23 |
| `uv run --offline --no-sync python -I tools\probe_f3.py trees\{pre_f3,head}\src` | 0/12 → 12/12 | scratch | 20:20:54 |
| `python -I tools\diff_run.py trees\{head,r1impl,main,pre_f3}\src out\diff_<t>.txt 20261023 3000 20000`, then `tools\compare.py` | 0 differences in H and P against all three; Q 0 vs 5f7a382 and f627350 (12,502 vs origin/main, expected) | scratch | 20:22:39–20:22:45 |
| `python -I tools\overhead.py trees\{main,r1impl,pre_f3,head}\src` (2 rounds) | about +2 µs per model check (information) | scratch | 20:24:47 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: **2788 passed in 8.71s**, exit 0 | 4ea84b7 | 20:24:54–20:25:04 |
| `git diff origin/main -- tests/acceptance/CORE-002 tests/golden/CORE-002 tests/acceptance/CORE-003 tests/golden/CORE-003` | PASS: empty (0 bytes) | 4ea84b7 | 20:25:07 |
| `bash scripts/controls/red-flags.sh origin/main` | exit 0; 1 prose group (explained above) | 4ea84b7 | 20:25:09 |
| `timeout -k 10 300 uv run --offline pytest tests/acceptance/CORE-004 -q -p no:cacheprovider --co` | 1,993 collected: AC-01 559, AC-02 38, AC-03 899, AC-04 454, AC-05 1, AC-06 42 | 4ea84b7 | ≈20:25 |
| locked file `-k "test_where or test_ac01"` run from `trees\main` | 559 failed, 1 passed (guard) | origin/main costs | 20:25:49 |
| `timeout -k 10 600 uv run --offline pytest tests/acceptance/CORE-004 -q -p no:cacheprovider -rP -k "oversized or extreme_exponent or huge_on_grid or positive_adjusted or rejected_alone"` | PASS: 426 passed; 426 `elapsed=` lines, slowest 0.0049086 s | 4ea84b7 | 20:25:53 |
| `python -I tools\f5_timing.py trees\head\src {points,model_field_construct,model_field_use}`; `trees\main\src points` | 12.978 s; 0.000 s; 13.336 s; main 13.852 s | scratch | ≈20:26–20:27:14 |
| Mutant `trees\mut_status_only`: `timeout -k 10 900 uv run --offline --no-sync pytest -c <tree>\pytest.ini --rootdir <tree> -q -p no:cacheprovider --tb=no -rf <guard> tests/acceptance tests/golden tests/unit`; then `probe_f3.py` on the mutant | **2781 passed** (mutant survives); probe 5/12 | scratch | 20:29:34 |
| `python -I tools\prov_precedence.py trees\{head,pre_f3,main}\src` | head = pre_f3 (0 of 240 differ); vs main 14 (F4 and `datetime`) | scratch | ≈20:30 |
| `git diff --stat d33d5da 4ea84b7 -- src tests`; `git diff --stat 0c0a5b0 HEAD -- tests/acceptance tests/golden tests/architecture`; `git diff --numstat …` | empty; empty; unit tests additive | 4ea84b7 | ≈20:30 |
| `git status --short --untracked-files=all; git diff --cached --stat` (before writing this file) | clean, nothing staged | 4ea84b7 | 20:31:25 |

## Blocks and deviations

- No hook or deny rule blocked any command. The post-run locked-path detector did not fire.
- No locked file was copied or edited. The locked tests ran in place from the repository. The scratch trees
  hold only `src/sochron`, a two-line `pytest.ini` and (in the mutant) one edited scratch copy of
  `costs/model.py`.
- The probes changed `H001_COSTS`'s shared record in memory, in a child process only, and restored it before
  that process exited.

Ready for PR: no. There is no code defect: the code at 4ea84b7 is ready. First F7 (unit rows) and F8 (two doc
lines) need fixing, and F9 needs the owner's choice. A re-check of F7–F9 only is then enough.

Findings open: 3
