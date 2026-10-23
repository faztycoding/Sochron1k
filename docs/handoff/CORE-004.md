# CORE-004 test-author handoff

Date: 2026-10-23, Asia/Bangkok (+07:00), 15:0x to 15:3x.
Role: test author (Codex role, taken by a fresh Claude Code session under the role swap recorded
in PROGRESS.md, PLAN-001 entry 2026-10-22 23:4x; Codex is out of quota until 2026-10-28 19:41).
Contract: `docs/contracts/CORE-004-costs-hardening.md` v1, Tier Standard, approved 2026-10-22 23:4x.
Branch: `fix/CORE-004-costs-hardening` at `82a7f3e43688328df533f79740d6334a96a48d91`, stacked on
`fix/FIX-001-architecture-side-effects`; `src/sochron/costs` is identical to `origin/main`
`5ca1949c651602f7b7a9a3d75a80326ffc635dda` (`git diff --stat origin/main -- src/sochron/costs` empty).

Deliverable: a proposal patch plus this handoff. Nothing was applied to the repository, staged,
committed or pushed; no source, dependency, configuration or PROGRESS change. The patch is under
the gitignored `docs/proposals/`; this handoff is the only tracked addition and is unstaged.
The current `src/sochron/costs/*.py` was read only to learn the API, as instructed; no unit test
or implementer note of CORE-004 exists yet.

## D-006 artifact and expected bytes

Patch: `docs/proposals/CORE-004-tests.patch` (regular file, 49,402 bytes, unified diff produced by
`git diff --no-index` from the scratch copy, header rewritten by git itself to
`a/tests/acceptance/CORE-004/... b/tests/acceptance/CORE-004/...`).

Patch SHA256: `fc768869a88eff70b568c12f0a06b258c13fe08a4ecef73f3e13ec730102fe5e`

`git apply --numstat` reports exactly one path: `1091 0 tests/acceptance/CORE-004/test_costs_hardening.py`
(a new file; no `tests/golden/CORE-004/` is needed, every literal is inline and self-checked).

| Repository-relative file | Expected post-apply SHA256 | Expected Git blob |
|---|---|---|
| `tests/acceptance/CORE-004/test_costs_hardening.py` | `0d75e147b710036f093471303c51ac16038cad26115db27d57e1c5d8304d8e01` | `e74213c204a0db1d9392430ed698133ce137d029` |

Both digests are of the scratch copy the patch was generated from (1,091 lines, 48,063 bytes).
The blob id was computed twice, with `git hash-object --path=tests/acceptance/CORE-004/test_costs_hardening.py`
(the repository's `*.py text eol=lf` attribute applied) and with `--no-filters`; they are equal,
so the file holds no CR byte. The patch's `index 0000000..e74213c` line carries the same blob id,
git warned "LF will be replaced by CRLF the next time Git touches it" for the scratch copy (so it
is LF today), and `git apply --check --whitespace=error` passed (a CR before LF would be a
whitespace error). The file is ASCII (checked by eye; the inline byte check was blocked, see
"Blocks"). It ends with exactly one newline (the diff's last hunk ends without "No newline" marker).

## Standalone checks (repository root, Git Bash)

| Command or procedure | Result | Commit | Time (+07:00) |
|---|---|---|---|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git diff --stat origin/main -- src/sochron/costs` | PASS: clean tree, expected branch and base, costs identical to main | 82a7f3e | 15:0x |
| `uv run --offline --no-sync python -B -c` version probe | PASS: CPython 3.12.15, pytest 9.1.1, uv 0.13.0 | 82a7f3e | 15:0x |
| `uv run --offline --no-sync pytest -c pyproject.toml --rootdir . <scratch>/tests/acceptance/CORE-004 --collect-only -q -p no:cacheprovider` | PASS: 1970 tests collected, no collection error | 82a7f3e + draft | 15:1x |
| Same runner, `-q --tb=line -rA -k "not huge_on_grid_lots and not extreme_exponent_volume_step"` (outer `timeout -k 10 900`) | FAIL as intended: **1808 failed, 160 passed, 2 deselected in 4.52s**, exit 1 | 82a7f3e + final draft | 15:23:17 to 15:23:22 |
| Same runner, `-k "huge_on_grid_lots"` alone (outer `timeout -k 10 120`) | FAIL as intended: no summary; faulthandler `Timeout (0:00:20)!` with the worker in `charges.py:90 _on_grid` (`as_integer_ratio` of a 30M-digit lots), process exit 1 | 82a7f3e + final draft | 15:23:22 to 15:23:43 |
| Same runner, `-k "extreme_exponent_volume_step"` alone (outer `timeout -k 10 120`) | FAIL as intended: faulthandler `Timeout (0:00:20)!` with the worker in `charges.py:91 _on_grid` (`10**999999999` for `volume_step` `1E-999999999`), process exit 1 | 82a7f3e + final draft | 15:23:44 to 15:24:04 |
| `uv run --offline pytest tests -q -p no:cacheprovider` (verified command, untouched repository tree) | PASS: **789 passed in 3.32s**, 0 skipped (the AC-05 baseline) | 82a7f3e | 15:24:05 to 15:24:08 |
| `git diff --no-index -- /dev/null tests/acceptance/CORE-004/test_costs_hardening.py` run with `git -C <scratch tree>`, output redirected to the literal patch path | PASS: patch written, header `new file mode 100644`, `index 0000000..e74213c` | 82a7f3e | 15:24:5x |
| `sha256sum`, `git hash-object --path=...`, `git hash-object --no-filters` on the scratch copy; `sha256sum` and CR count on the patch | PASS: digests above; both blob ids equal; patch has 0 CR bytes | 82a7f3e | 15:25:0x |
| `git apply --check docs/proposals/CORE-004-tests.patch` (standalone) | PASS: exit 0, no output | 82a7f3e | 15:25:1x to 15:25:31 |
| `git apply --check --whitespace=error docs/proposals/CORE-004-tests.patch` (standalone) | PASS: exit 0, no output | 82a7f3e | 15:25:2x |
| `git apply --numstat docs/proposals/CORE-004-tests.patch` (standalone) | PASS: the one path above | 82a7f3e | 15:25:2x |
| Apply the patch inside an empty scratch directory and compare bytes | BLOCKED: guard-bash accepts `git apply` only as the literal standalone repository form; see "Blocks". The `index` line and the apply checks stand in for it | 82a7f3e | 15:25:4x |
| `bash scripts/controls/red-flags.sh main` | PASS execution, exit 0; one inherited "Lint disabled" group (FIX-001 handoff and review prose that lists the forbidden markers); the proposal is ignored and the handoff untracked, so neither was scanned | 82a7f3e | 15:25:0x |

The pytest runs above use the scratch tree (`<scratch>/tests/acceptance/CORE-004/`) as the only
test path, with `-c pyproject.toml --rootdir .` so the repository's `pythonpath = ["src"]` and
`cwd/src` are the code under test. `<scratch>` is
`C:/Users/MSI/AppData/Local/Temp/claude/C--Users-MSI-Desktop-------------Sochron1k/0a579654-fbc1-4766-8dd6-31233a9d8adf/scratchpad/tree`;
the logs `run-final.log`, `run-final-hang-lots.log`, `run-final-hang-step.log` and
`run-baseline-suite.log` sit next to it. Nothing in this handoff depends on them surviving.

## What the implementer does (D-006)

1. Confirm the branch and base, recompute the patch SHA256, then run each of these alone from
   the repository root: `git apply --check docs/proposals/CORE-004-tests.patch`, then
   `git apply docs/proposals/CORE-004-tests.patch`. The post-run detector should name exactly
   `tests/acceptance/CORE-004/test_costs_hardening.py`; anything else means stop (N6).
2. Verify the applied file's SHA256 and `git hash-object --path=<path> <path>` against the table.
   Stop on any mismatch. Then `git apply -R --check docs/proposals/CORE-004-tests.patch` alone.
3. Obtain a fresh-session review of the contract and the applied test diff (the authoring checks
   in this run are not that review), then commit red: `test(costs): acceptance tests for CORE-004`
   with body `Refs: CORE-004`.
4. **Red run before the fix.** Two tests hang the current code inside a C call that holds the GIL
   (`Decimal.as_integer_ratio` on a 30M-digit lots, and `10**999999999` for a tiny `volume_step`),
   so the 20 s faulthandler watchdog ends the whole pytest process with a traceback. Always run
   with an outer `timeout`, and for a complete red summary deselect them:
   `uv run --offline pytest tests -q -p no:cacheprovider -k "not huge_on_grid_lots and not extreme_exponent_volume_step"`.
   Expected on the current code: the 789 existing tests pass, the new file gives 1808 failed and
   160 passed (2 deselected). The two deselected tests, run alone, end in `Timeout (0:00:20)!`.
5. Implement under the contract; after the fix the verified command `uv run --offline pytest tests -q -p no:cacheprovider`
   must be green with 0 skipped (1970 new tests, all under a second each; the watchdog tests
   finish in milliseconds once the bound is checked before any rational conversion).

## Expected red summary and why each group fails

Against `82a7f3e` (costs as merged in CORE-002): 1808 failed, 160 passed, 2 deselected, plus the
two watchdog kills. Every failure is a behaviour the contract changes; none is a syntax, import
or fixture error (the one collection error during authoring, a wrong `ids=` callable, was fixed
before this run; the fixture mistakes found in the first run, 11 tests, were fixed and re-run).

| Test function (count: failed / passed today) | AC | What it proves when green | Why it fails now |
|---|---|---|---|
| `test_ac01_decimal_subclass_rejected_in_every_slot` (428 / 0) | AC-01 | Every Decimal slot (lots x7, points, factor, money, r, 9 CostModel fields at construction and at use through 9 callables, 6 CostBreakdown fields) raises exactly `TypeError` for a plain subclass and for subclasses lying about `as_integer_ratio` (0.125 claimed on-grid; step 0.03), `is_finite` (NaN claimed finite) and `==`/order (equal to everything) | `isinstance` accepts them: the call returns ("DID NOT RAISE TypeError", 673 over AC-01 groups), the lying ratio passes the grid, the NaN raises `decimal.InvalidOperation` in the caller's context (123) or a domain error |
| `test_ac01_int_subclass_rejected_in_every_slot` (84 / 0) | AC-01 | Every int slot (points, spread points x3, sides x3, nights/triple x4, factor, 3 model int fields at construction and at use) raises `TypeError` for a plain subclass and for `_Count(-1)` whose `<`, `>`, `<=`, `>=` say it is in range | `isinstance(int)` accepts; `_Count(-1)` passes the domain checks and the call returns |
| `test_ac01_str_subclass_rejected_in_every_slot` (30 / 0), `test_ac01_hostile_equality_cannot_impersonate_a_valid_value` (1 / 0) | AC-01 | side, symbol (construction and use), Provenance source/note/status raise `TypeError` for a plain `str` subclass and for one equal to every string; `_Name("buy")` cannot pass as a side, `_Name("nonsense")`/`_Stranger("assumed")` cannot pass as a status | membership tests use `==`, so the subclass is accepted (or lands on `CostsError`/`BadProvenance`, the wrong error) |
| `test_ac01_date_subclass_rejected_in_as_of` (3 / 0) | AC-01 | `as_of` refuses a `date` subclass, one never equal to anything, and a `datetime` | `isinstance(date)` accepts all three (datetime is a date subclass) |
| `test_ac01_model_must_be_exactly_costmodel` (9 / 0), `test_ac01_subclass_constructors_are_refused` (1 / 0) | AC-01 | every model-taking callable refuses a CostModel subclass instance and non-models (`{}`, str, 1, True, 1.0, None) with `TypeError`; `DerivedCostModel(...)` and `DerivedProvenance(...)` raise `TypeError` | no type check on `model` (subclass returns; `None` gives `AttributeError`); subclass constructors run `__post_init__` and succeed |
| `test_ac01_ac02_provenance_value_must_be_exactly_provenance` (3 / 0) | AC-01/02 | a Provenance subclass as a provenance value is `BadProvenance` (dict, proxy, custom Mapping); a string value stays `BadProvenance` | `isinstance(Provenance)` accepts the subclass |
| `test_ac02_provenance_container_copied_once_and_frozen` (2 / 2) | AC-02 | dict, `MappingProxyType`, a custom Mapping and a proxied custom Mapping are accepted, read in one traversal with each key read once, stored as a `MappingProxyType` copy that later source changes and `[]=`/`del` cannot touch | the custom Mapping cases fail: construction traverses three times (`set()`, `.items()`, `dict()`) and the second read's garbage is stored ("assert 3 == 1", mappingproxy mismatch); dict and proxy pass today |
| `test_ac02_provenance_container_must_be_a_mapping` (0 / 7) | AC-02 | pairs list, key set, str, int, bool, float, None give exactly `TypeError` through `replace` and the constructor | already CORE-002 behaviour (F3); unchanged |
| `test_ac02_provenance_keys_must_be_exact_str` (9 / 0), `test_ac03_provenance_keys_revalidated_at_use` (18 / 0) | AC-02/03 | an int key, an int key with a key also missing, and a `str`-subclass key give exactly `TypeError` before any other provenance check (the hook key records zero `==` calls); the same at use for all 9 callables | the key set is compared first: int key is `BadProvenance` ("extra [1]"), the subclass key is equal to `"point"` and accepted; at use nothing is read |
| `test_ac02_ac03_use_reads_provenance_once` (16 / 2) | AC-02/03 | at use, every callable reads a model's provenance once (one traversal, each key once) and returns the honest result; `stress()` returns a model carrying the validated snapshot as a `MappingProxyType` | 7 callables never read provenance ("assert 0 == 1"); `stress()` rereads it through `replace`; `unknowns` already reads it once and passes |
| `test_ac03_provenance_is_read_before_the_other_fields` (36 / 0) | AC-03 | a field that goes bad inside the provenance read (volume_step 0, stress_factor 0) is caught with the construction error, for all 9 callables, plain and proxied | fields are not re-validated at use; the hook never even runs for most callables |
| `test_ac03_every_use_revalidates_a_changed_field` (770 / 75) | AC-03 | for 13 uses (9 callables plus the sides=0, sides=0, nights=0 and sides=0 zero paths) and 65 single-field defects (wrong type, NaN/sNaN/Infinity, every domain rule, 9 provenance container defects), the use raises exactly the type the constructor raises for the same defect | no re-validation: the call returns ("DID NOT RAISE", 328 CostsError, 63 BadProvenance, 60 BadStress), or a downstream error of the wrong type (`BadVolume`, `BadPoints`, `ZeroDivisionError`, `ValueError`/`OverflowError` from `as_integer_ratio`, `AttributeError`, `InvalidOperation`). The 75 passes are `stress()` (its `replace` re-runs `__post_init__`) and defects that today's arithmetic happens to turn into the same error type (NaN components rejected by `CostBreakdown`, `slippage_points_per_side=True` rejected by `_points`) |
| `test_ac04_oversized_decimal_rejected_fast_in_every_slot` (363 / 31) | AC-04 | 1,001 stored digits (two shapes, self-checked), adjusted -1,100,001 and +1,100,001 in every Decimal slot raise the slot's error (`BadVolume`, `BadPoints`, `BadStress`, `BadR`, `CostsError`) in under 1.000 s, measured by `perf_counter` around the public call in a daemon thread with the faulthandler watchdog, caller context untouched | the value is accepted ("got None; return is forbidden", 287 CostsError, 35 BadStress, 7 BadVolume, 3 BadR, 3 BadPoints) or the arithmetic raises `decimal.Overflow` (28). The 31 passes are coincidences: lots beyond the range or off the grid already give `BadVolume`; a tiny stress factor underflows to zero and gives `BadStress`; CostBreakdown's ordered-sum check rejects an inconsistent 1,001-digit or underflowing total with `CostsError` |
| `test_ac04_extreme_exponent_lots_rejected_fast` (0 / 7) | AC-04 | lots `1E-999999999` is `BadVolume` within the deadline for all 7 lots callables | already rejected by the range check before any conversion; unchanged |
| `test_ac04_huge_on_grid_lots_rejected_before_rational_conversion` (watchdog kill) | AC-04 | a 30M-digit representation of the on-grid value 0.02 is `BadVolume` within 1.000 s, so the bound is checked before the rational grid test | `check_volume` reaches `_on_grid`, whose `as_integer_ratio` holds the GIL; the 20 s watchdog exits the process |
| `test_ac04_extreme_exponent_volume_step_rejected_fast_at_use` (watchdog kill) | AC-03/04 | a model whose `volume_step` was set to `1E-999999999` after construction is `CostsError` within 1.000 s at use | `_on_grid` computes `10**999999999`; watchdog exit |
| `test_ac04_thousand_digit_model_field_accepted_with_unchanged_results` (0 / 9), `test_ac04_thousand_digit_arguments_accepted_with_unchanged_results` (0 / 1) | AC-04 | the same numbers written with exactly 1,000 stored digits (self-checked) are accepted in every model field, in lots, points, factor, money, r and CostBreakdown, with results equal to the short form; a 1,000-digit step that is not a trailing-zero form (`5**1430 * 10**-1432`, 0.02 on its grid) is accepted | unchanged behaviour; must stay green |
| `test_ac04_adjusted_exponent_edge_accepted_in_model_fields` (0 / 14), `test_ac04_adjusted_exponent_edge_accepted_in_arguments` (0 / 1) | AC-04 | `1E-1100000` and `1E+1100000` are accepted in the domain-compatible model fields (used through `check_volume`/`spread_charge` for the volume bounds), in points paired with a compensating `point`, in money/r paired, and as CostBreakdown.stress_factor | unchanged behaviour; must stay green |
| `test_ac04_zero_with_any_exponent_behaves_like_zero` (0 / 3) | AC-04 | `0E-999999999999999999`, its negative and `0E+999999999999999999` act exactly like `Decimal("0")`: zero results where zero is valid (points, money, commission, both swaps, CostBreakdown) and the zero-domain error where it is not (`BadVolume`, `BadStress`, `BadR`, `CostsError`) | unchanged behaviour; must stay green |
| `test_ac05_h001_values_and_honest_results_are_unchanged` (0 / 1) | AC-05 | every H001_COSTS value, type, provenance key and status; the honest fixture results of all 10 callables; stressed, short, fallback, 7-night, tick-value, 1/3 and nested-stress literals of CORE-002 under a hostile caller context | unchanged behaviour; the locked CORE-002/003 suites (789 passed) are the rest of AC-05 |
| `test_ac06_huge_negative_int_keeps_the_slot_error` (34 / 7), `test_ac06_huge_positive_int_out_of_domain_keeps_the_slot_error` (1 / 0) | AC-06 | `-(10**5000)` in nights/triple_nights (x4), sides (x3), spread points (x3), factor and the 3 model int fields at construction and at use (x27); `10**5000` as triple_nights and triple_swap_weekday: exactly the slot's error, never a `ValueError` | the error messages format the int (`ValueError: Exceeds the limit (4300 digits)`, 11) or the model is not re-validated at use (returns). Passes today: factor (formats a Decimal), the model int fields at construction (messages without the value) and through `stress()` |

Timed harness in this run: 401 public calls completed with the worker alive check satisfied,
slowest 0.571 s (`1E-1100001` as `volume_step` through `round_trip_cost`, four grid checks of
`10**1100001` on the current code), 0 "unfinished after join(timeout=10)"; the two watchdog cases
above ran alone. Environment line printed by every timed test:
`Windows-11-10.0.26200-SP0; cpython 3.12.15 via uv`.

The `api` fixture snapshots `H001_COSTS` before each test and asserts it unchanged afterwards;
every negative test works on `replace(H001_COSTS)` copies, so the singleton is never mutated.

## Interpretations the reviewer should confirm

The contract leaves these to the test author; each is written so the stricter reading is tested.

- Q1 `CostBreakdown` fields are covered by the size bound with `CostsError` ("ทุกตำแหน่ง"; the
  error table names no CostBreakdown error, so the base class is used). Components are tested with
  the other components zero and `total` equal to the oversized component, so the fixture is
  consistent and the only defect is the size.
- Q2 At use, the model is validated before the arguments are compared against it: a model whose
  `volume_max` is 0.005 or `volume_step` is -1 must give `CostsError`, not `BadVolume` for the
  honest lots 0.02 (33 cases). The oversized literals are chosen so that no honest argument moves
  out of its domain; the two combinations that cannot satisfy this (positive exponent for
  `volume_min`/`volume_step`, negative exponent for `volume_max`) are left out, as CORE-003 did.
- Q3 "อ่าน provenance ครั้งเดียว ... และก่อน field อื่น" is tested at use with a `_SnapshotMapping`
  (second read returns garbage) and with a `_HookMapping` that spoils a field during the read;
  `stress()` must build its result from the validated snapshot rather than reread the container.
  Both follow the CORE-003 v1.6 precedent that `sochron.risk` satisfies.
- Q4 Subclass constructors (`DerivedCostModel(...)`, `DerivedProvenance(...)`) must raise
  `TypeError` ("When สร้าง object"). `CostBreakdown` subclasses are not covered (AC-01 names only
  CostModel and Provenance); its fields are.
- Q5 `bool` cannot be subclassed in Python, so the "subclass of bool" wording has no test; bool in
  int slots stays CORE-002's `TypeError`.
- Q6 `stress()` with a factor at the exponent edge (`1E+1100000`) overflows the precision-28
  context; the contract's "accepted" edge is tested where the arithmetic stays in range
  (construction of every field, points paired with `point`, money paired with r, the volume bounds
  through `check_volume`). What happens to in-bound values that overflow the context remains
  CORE-002 behaviour and is not asserted.
- Q7 Huge ints that are in domain (for example `nights = 10**5000`) are not tested; the contract
  bounds Decimals, not ints.

## Blocks encountered (stopped, not routed around)

1. `guard-bash`: an inline `uv run ... python -c` byte check (CR count, trailing newline, ASCII)
   was blocked because the scratch path string contains `tests/acceptance`. The step was dropped;
   the LF evidence above comes from git (`--path` vs `--no-filters` blob equality, the CRLF warning,
   `--whitespace=error`, 0 CR bytes in the patch).
2. `guard-bash`: a log-pairing command was blocked because it redirected into a shell variable
   (`$P`), which the task forbids; the analysis was redone read-only with process substitution.
3. `guard-bash`: `git apply --check ...; echo "exit=$?"` and three sibling compound forms were
   blocked ("git apply must be one standalone literal command"); each was re-run as the literal
   standalone command and passed.
4. `guard-bash`: `git -C <scratch dir> apply <patch>` (apply into an empty scratch directory to
   compare bytes) was blocked by the same rule; that check is recorded as BLOCKED above.

## Not done and limits

- The patch was not applied anywhere; the byte-for-byte proof of the applied file rests on the
  `index` line and the apply checks, not on a scratch application.
- No implementation, unit test, evidence file, PROGRESS entry, commit or push: outside this role.
- The red run proves the tests fail for contract reasons; it cannot prove the assertions that only
  run after a rejection succeeds (green behaviour) until the implementation exists.
- The hostile subclasses, hooks and `object.__setattr__` are test techniques for AC-01 to AC-04;
  they do not claim to protect against malicious code in the same process (contract scope, CORE-003 v1.7).
- Timing is measured on this machine only; the contract names it the reference machine.

Delivery state: test proposal **implemented** and verified red locally; unapplied, unstaged,
uncommitted, not reviewed, not merged. Next action: the implementer applies via D-006, verifies
the hashes, obtains a fresh-session review, then commits red.
