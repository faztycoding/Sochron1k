# Review CORE-004-tests round 1 · base main (`origin/main` 6bd9ef8; merge-base and HEAD 82a7f3e) · head 82a7f3e + applied `CORE-004-tests.patch` (uncommitted) · reviewer Claude Code (fresh session, reviewer under the role swap; D-006 post-apply review)

Scope: the one locked file added by `docs/proposals/CORE-004-tests.patch`, which a fresh Claude session wrote as
test author under the owner's role swap (PROGRESS.md, PLAN-001 entry; Codex is out of quota until 2026-10-28
19:41). I reviewed it against contract v1 (`docs/contracts/CORE-004-costs-hardening.md`, Tier Standard, approved
2026-10-22 23:4x), the CORE-002 API and error table (`docs/contracts/CORE-002-costs.md`), the handoff
(`docs/handoff/CORE-004.md`), the current `src/sochron/costs` (read only; identical to `origin/main`) and the risk
precedent (`src/sochron/risk/policy.py`, `tests/acceptance/CORE-003/test_risk_acceptance.py`). I am neither the
test author nor the implementer. I edited, staged and committed nothing except this file. Scratch evidence is
under `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\a422d323-5873-478f-bad7-34371c36a774\scratchpad\`
(`red-full.xml`/`.log`, `ref\` reference oracle, `mut\` trees, `probe\`, `tools\`). All times are 2026-10-23, +07:00.

**Ready to commit red: yes.** The applied file is byte-exact (SHA256 and Git blob match the handoff), the patch
reverses cleanly, and it is the only locked-path change. The red run reproduces the handoff exactly: 1808 failed,
949 passed, 2 deselected. Every failing group fails because current costs accept or mishandle the hostile input,
never because of a fixture error. The 160 new passes are the unchanged-behaviour rows plus explained coincidences.
The tests can be satisfied: a scratch reference implementation built on the risk pattern passes all 1970 rows
(2.48 s). All 22 plausible wrong fixes are caught: 21 by ordinary rows, and M22 only by the watchdog row,
which ends the process loudly (M09 and M14 trip the watchdog as well). The slowest timed rejection in the green
state is 3.3 ms against the 1.000 s bound.

Three findings, none in the way of the red commit. F1 (Medium, question) is a contract and scope conflict
outside the locked file: AC-01 forces an existing **unit** test of `sochron.risk` to fail, while AC-05 forbids
editing it and `tests/unit/risk/**` is not an allowed file. The owner must decide. F2 and F3 (Low) are coverage
gaps: three one-change mutants pass all 1970 rows. A 16-row scratch probe of the proposed fixes catches all three
and fails 16/16 on the current code.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | question | `tests/unit/risk/test_risk_unit.py:252` (outside the locked file); contract `:24-27` (scope, allowed files, exclusions), `:33` (row 1), `:48` (AC-01), `:52` (AC-05); locked rows `test_ac01_decimal_subclass_rejected_in_every_slot[CostModel.volume_step-*]` (`tests/acceptance/CORE-004/test_costs_hardening.py:353`, `:359-374`) | The unit test (commit `fd50946`, on main) builds `step_model = replace(H001_COSTS, volume_step=_Lots("0.01"))` **outside** `pytest.raises`, where `_Lots` is a `Decimal` subclass (`:207-209`). I ran the whole suite in place against the scratch reference implementation (exact types everywhere, as AC-01 requires): **1 failed, 2758 passed in 8.53s**. The only failure is this line: `TypeError: volume_step must be exactly Decimal, not _Lots` from `CostModel.__post_init__`. | Any implementation that meets AC-01, i.e. a `Decimal` subclass in a `CostModel` field raises `TypeError` at construction. The locked rows above require exactly that, for `_PlainDecimal` and for subclasses that lie about their methods. | AC-01 and AC-05 cannot both pass as written. AC-05 says "unit tests ทั้งหมดผ่านโดยไม่แก้ tests เดิม", and the allowed files cover only `tests/unit/costs/**`. The exclusions sentence "`sochron.risk` (ยกเว้นถ้า test ของ risk ต้องตามการเปลี่ยนนี้ ซึ่งไม่ควรเกิด)" foresaw exactly this case. The locked file is not at fault. The implementer will hit this as soon as the suite turns green, so an owner decision is needed before step 3 of the plan finishes. | Owner chooses one. (a) Recommended: amend the scope so the implementer may change `tests/unit/risk/test_risk_unit.py:252-254`, keeping its intent (risk's `require_model` refuses a subclass in a model field). Set the subclass after construction with `object.__setattr__` on a `replace(H001_COSTS)` copy, as the CORE-003 locked tests do. (b) Narrow AC-01 so construction may accept model-field subclasses. Not recommended: it contradicts contract row 1 and the locked rows. | (a): rerun `uv run --offline pytest tests -q -p no:cacheprovider` on the implementation: 0 failed, 0 skipped, and `test_subclasses_of_value_types_are_refused` still raises `TypeError` from `size_position` for the planted subclass. |
| F2 | Low | confirmed | `tests/acceptance/CORE-004/test_costs_hardening.py:758` (CostBreakdown size slots leave out `total`), `:776-784` (`_breakdown_with` sets `total` to the same oversized value as the component); contract `:33` ("รวม field ของ … `CostBreakdown`"), `:36` ("ทุกตำแหน่ง"), `:51` (AC-04 "ในแต่ละช่อง") | Two one-change mutants of the reference, run in place against the locked file. `S01_breakdown_bounds_total_only` bounds only `total` and `stress_factor`: **1970 passed**, exit 0. `S02_breakdown_bounds_components_only` bounds every field except `total`: **1970 passed**, exit 0 (both ≈18:2x). Each component row oversizes the component **and** `total`, so a bound on either one satisfies the row. `total` is never oversized on its own. | An implementation that bounds `total` but not the four components (or the reverse). | AC-04's per-slot bound on `CostBreakdown` is not enforced field by field. A `CostBreakdown` can then hold a 1,001-digit `spread`, `commission`, `slippage` or `swap` (S01), or a 1,001-digit `total` (S02), and still pass the locked suite. Exposure is small: costs builds breakdowns from bounded inputs, so only direct construction by a caller reaches it. Each row also carries two oversized fields, against the one-defect principle of CORE-002 `:100`. | Test author, in a follow-up patch. (a) In `_breakdown_with`, set `total` to the ordered sum of the components in a precision-28 `ROUND_HALF_EVEN` context (the CORE-002 rule), not to `value`. That total is in bound for the coefficient, trailing-zero and negative-adjusted shapes (the negative-adjusted sum underflows to 0, which equals the ordered sum). Keep `total = value` only for `positive_adjusted`, whose sum overflows the context. (b) Add the slot `("CostBreakdown", "total", "CostsError")` for `trailing_zero_coefficient` only, with honest components and `total = "1.68760" + "0" * 995` (1,001 digits, numerically equal to the sum). | Scratch probe `probe\test_probe_proposed_rows.py` (my own file; ≈18:28): the reference passes 16/16. S01 fails all 12 component rows (4 fields × 3 shapes), S02 fails the `total` row, and the current code fails 16/16 (red for the contract reason, with no coincidental pass). |
| F3 | Low | confirmed | `tests/acceptance/CORE-004/test_costs_hardening.py:733` (`_OVERSIZED["volume_step"]` positive-adjusted entry is `None`), `:719-722` (comment); handoff `docs/handoff/CORE-004.md:140-141` ("… positive exponent for `volume_min`/`volume_step` … are left out, as CORE-003 did"); `tests/acceptance/CORE-003/test_risk_acceptance.py:784-793` | Mutant `S03_step_positive_exponent_unbounded` skips the size bound for a `volume_step` whose adjusted exponent is above +1,100,000 (the negative side and every other field stay bounded): **1970 passed**, exit 0. CORE-003 *does* test `model.volume_step` at `1E+1100001`. It leaves out only positive `volume_min` and negative `volume_max` (`:788-792`), so "as CORE-003 did" does not hold for `volume_step`. `CostModel(volume_step=1E+1100001)` is a single-defect fixture, because the constructor never sees lots. At use, the handoff's own Q2 reading (model validated before the arguments are compared, `:137-139`) means the honest lots 0.02 is never checked against that step. | An implementation whose `volume_step` bound misses the positive side. | 10 AC-04 cases (construction plus 9 callables) that the contract asks for ("ในแต่ละช่อง") are absent. A one-sided per-field bound is a narrow mutant, so the impact is limited to regression strength. | Test author: set the fourth entry of `_OVERSIZED["volume_step"]` to `"1E+1100001"`, with the expected error `CostsError` at construction and at use, consistent with Q2. On the current code these rows fail without hanging (the grid check builds `10**1100001` once per check, below the 10 s join). | Same probe: rows `test_f3_volume_step_positive_adjusted_at_construction` and `…_at_use[check_volume, round_trip_cost]` pass on the reference, fail 3/3 on S03, and fail on the current code (0.35 s total). |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

Status of the task against the **current** costs code with the applied tests (the intended red state), and the
coverage verdict for each AC. This is test-patch evidence. No implementation exists yet, and this review does
not replace the implementation review, CI or the owner's decision.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | FAIL (intended red) | 559 rows fail: subclasses are accepted (`DID NOT RAISE TypeError`) or the lying methods leak into domain errors, `InvalidOperation` or a changed caller context. Coverage is complete for every position in contract row 1 (below). Mutants M01, M16–M19 and M21 are caught. Q4/Q5 accepted. |
| AC-02 | FAIL (intended red) | Custom-Mapping copies traverse 3 times and store the second read. Int and str-subclass keys reach the key-set check. Coverage complete. Mutants M02, M03 and M06 are caught; the dict/proxy/non-Mapping rows pass today as unchanged behaviour. |
| AC-03 | FAIL (intended red) | No use-time revalidation (770 of 845 matrix rows plus the 18 key, 36 hook and 16 read-once rows fail). Coverage: 13 uses × 65 single-field defects, plus key, read-first and read-once rows. Mutants M04, M05, M11–M14 and M20 are caught. Q2/Q3 accepted. |
| AC-04 | FAIL (intended red) | 363 of 394 oversized rows fail (accepted, or a `decimal.Overflow`). The two watchdog rows kill the process at 20 s. Edges (1,000 digits, ±1,100,000, zero with any exponent) pass today. Mutants M07–M10 and M22 are caught. Gaps: F2 and F3. Q1/Q6 accepted. |
| AC-05 | PASS today; UNKNOWN for the task | The 789 existing tests pass beside the new file, and `test_ac05_h001_values_and_honest_results_are_unchanged` passes. F1: no implementation that meets AC-01 can also pass the existing unit test without an owner decision. |
| AC-06 | FAIL (intended red) | 35 rows fail with `ValueError: Exceeds the limit (4300 digits)` or because nothing is revalidated at use. The 7 passes are explained (Decimal message, messages without the value, `stress()` re-running `__post_init__`). Mutants M15 and M04/M05 are caught. Q7 accepted. |

## Coverage per AC (clause → rows that fail if the clause is not implemented)

- **AC-01 / row 1.** Decimal slots (`:349-374`): lots × 7 callables, points, factor, money, r, 9 `CostModel` fields
  at construction and at use × 9 callables, 6 `CostBreakdown` fields, each with a plain subclass and subclasses
  lying about `as_integer_ratio`, `is_finite` and `==`/order. Int slots (`:377-395`): points, 3 spread slots, 3
  sides, 4 night slots, factor, 3 model int fields at construction and at use, each with a plain subclass and
  `_Count(-1)`. Str slots (`:398-412`): side × 2, symbol at construction and at use, Provenance source, note and
  status, plus `_Name`/`_Stranger` impersonation (`:415-421`). Date: plain, never-equal, `datetime` (`:424-428`).
  Exact `CostModel` at every model-taking callable (`:431-436`). Subclass constructors (`:439-443`). Exact
  `Provenance` values give `BadProvenance` (`:597-606`). No position in the CORE-002 API block is missing. `bool`
  cannot be subclassed (probe: `type 'bool' is not an acceptable base type`), so no row is needed (Q5).
- **AC-02 / row 2.** dict, proxy, custom Mapping and proxied custom Mapping: one traversal, each key once,
  `MappingProxyType` of an independent copy (`:518-536`). Non-Mapping gives `TypeError` (`:539-547`). Non-exact-str
  keys give `TypeError` before any other provenance check, including the missing-key combination and an
  equality-recording key (`:559-583`).
- **AC-03 / row 3 and the invariant `:42`.** 13 uses × 65 defects, with the construction error as the oracle
  (`:650-711`). Keys at use (`:586-594`). Provenance read before the other fields, through a hook that spoils a
  field during the read (`:629-643`). One read per use, and `stress()` returns the validated snapshot (`:609-626`).
- **AC-04 / row 4.** 1,001 digits in two shapes (self-checked, `:769-773`), adjusted ±1,100,001 in every
  domain-compatible slot, the exact slot error and < 1.000 s (`:787-841`). Rejection before rational conversion
  (`:850-861`). Accepted edges: 1,000 digits (`:901-941`), ±1,100,000 (`:952-983`), zero with any exponent
  (`:989-1019`). Gaps: `CostBreakdown.total` and component isolation (F2), `volume_step` positive (F3).
- **AC-05.** `test_ac05_…` (`:1026-1056`) plus the locked CORE-002/003 suites. Blocked by F1 at the task level.
- **AC-06 / row 5.** `-(10**5000)` in every count, spread, factor and model int slot at construction and at use
  (`:1063-1079`), and `10**5000` for `triple_nights`/`triple_swap_weekday` (`:1082-1091`).
- **Negative cases `:45`.** Every listed case has a row: lying subclasses, `StrSubclass("measured")`, a Mapping
  changing between reads, `volume_step` 0/−1 after construction, lots `1E-999999999`, the extreme zero, and
  nights `-10**5000`.

## Author's interpretations (handoff `:129-157`)

- **Q1** (`CostBreakdown` fields bounded with exact `CostsError`): accept. Contract row 1 names `CostBreakdown`
  fields, and the base class is the only error that fits. The fixture design is F2.
- **Q2** (model validated before arguments, 33 cases): accept. AC-03 asks for "error เดียวกับตอนสร้าง". Lots 0.02
  is only "wrong" relative to the corrupted model, so the model is the single defect. Risk's `require_model` does
  the same. Mutant M14 is caught by 13 rows plus a watchdog kill. The "as CORE-003 did" remark is wrong for
  `volume_step`: F3.
- **Q3** (read once and first at use; `stress()` from the snapshot): accept. It is the invariant `:42` and the
  CORE-003 v1.6 pattern. M11, M12 and M13 are caught.
- **Q4** (subclass constructors refused; `CostBreakdown` subclasses not covered): accept. AC-01 names only
  `CostModel` and `Provenance`, and `CostBreakdown` is never an input.
- **Q5** (no bool-subclass row): accept (probe above).
- **Q6** (edge factor not asserted through `stress()`): accept. CORE-002 arithmetic computes the product in a
  precision-28 context whose exponent range is far smaller than ±1,100,000, so `stress()` cannot return a model
  for either edge factor. AC-04's "รับได้" at the edge therefore cannot hold for `factor` in `stress()`; it holds
  for the stored `CostBreakdown.stress_factor` and model `stress_factor` (rows `:952-983`). My direct probe of
  `stress()` with both edge factors was BLOCKED (see Blocks). This assessment rests on the CORE-002 context
  definition and the test author's statement. Optional for the owner: one contract phrase that the edge applies
  where CORE-002 arithmetic stays in range.
- **Q7** (in-domain huge ints not tested): accept. The contract bounds Decimals only.

## Checked, nothing found (and how)

### Blocks and the post-run detector (CLAUDE.md, N6)
- After my first read-only command (`wc -l …; git status --short; git branch --show-current; git rev-parse HEAD`,
  ≈18:0x), `check-locked-after.mjs` listed exactly `uncommitted A tests/acceptance/CORE-004/test_costs_hardening.py`.
  That is the only target of the patch the implementer had applied before this session. Under CLAUDE.md I verified
  the expected SHA256 and blob (all match, below) and continued. The detector did not fire again.
- guard-bash blocked one command (≈18:29): `uv run --project <repo> --offline --no-sync python -B -c "<probe of
  stress() with factors 1E-1100000 and 1E+1100000>"` run from my scratch trees `ref\` and `mut\H0_current\`, with
  the message "Blocked by .claude/hooks/guard-bash.mjs: inline python code running inside a protected folder. Run
  it from the project root or a task folder." I stopped that step and did not reshape or rerun it. The Q6 probe is
  recorded as BLOCKED. Nobody was available to ask in this session.
- No locked file was copied or edited. Mutation and reference runs execute the repository's test file in place,
  from a scratch working directory whose `pytest.ini` sets `pythonpath = src`. The file's `_api` prepends
  `cwd/src`, so the scratch tree is the code under test. That this worked is visible in the results: the reference
  turns 1808 failures into 1970 passes, and the watchdog tracebacks name the scratch `charges.py`.

### Hashes and patch state (item 1)
- `sha256sum`: patch `fc768869a88eff70b568c12f0a06b258c13fe08a4ecef73f3e13ec730102fe5e`, file
  `0d75e147b710036f093471303c51ac16038cad26115db27d57e1c5d8304d8e01`. `git hash-object --path=…` and `--no-filters`:
  both `e74213c204a0db1d9392430ed698133ce137d029`. All equal the handoff (`:23`, `:30`). File: 1,091 lines,
  48,063 bytes, ASCII only (non-ASCII byte count 0, by `tr`), 0 CR, 0 tabs, exactly one final newline. That closes
  the byte check the test author recorded as BLOCKED.
- `git apply -R --check docs/proposals/CORE-004-tests.patch`, standalone: exit 0, no output.
- `git status --short --untracked-files=all`: exactly `?? docs/handoff/CORE-004.md` and
  `?? tests/acceptance/CORE-004/test_costs_hardening.py`. `git diff --stat HEAD` and `git diff --cached` are empty.
  `git check-ignore -v`: the patch (`.gitignore:10`) and `tests/acceptance/CORE-004/__pycache__/` (`.gitignore:19`,
  bytecode from earlier runs) are ignored. So the only locked-path change is the new file.
- `git diff --stat origin/main -- src/sochron/costs`: empty. `origin/main` is now `6bd9ef8` (FIX-001 merged).
  HEAD `82a7f3e` is its ancestor.

### Quality (item 3)
- **Wrong-reason passes.** `_reject` (`:156-159`) and the timed harness (`:826`) require the exact error type. A
  `TypeError` from a bad keyword is excluded: the same `_calls` keyword sets succeed in
  `test_ac05_…` (all 10 callables) and in the AC-03 construction oracle, which expects domain errors. NaN and lying
  comparisons produce `InvalidOperation` or `ValueError`, never `TypeError`, so a sloppy implementation cannot
  pass the subclass rows by accident (red-run failure kinds above). `stress({})` raises a natural `TypeError`
  inside `dataclasses.replace`, but the subclass-instance case in the same test still requires an exact type check.
- **Asserts that are always true.** None found. Each self-check (`_assert_oversized`, digit counts at `:904`,
  `:922`, `:932`, the `effects == []` after building the fixture at `:571`, `hook.calls >= 1`) guards a fixture
  premise, and mutants M06, M08 and M13 show the paired assertions can fail.
- **Over-constraint.** Exact error types match the names in the contract table. Read-once, provenance-first and
  caller-context-unchanged (flags included) are contract invariants (`:41-42`). The two-defect shapes `_FiniteDecimal("NaN")`,
  `_RatioDecimal("0.125")` and `_Count(-1)` expect `TypeError`. AC-01 explicitly lists subclasses that lie about
  their methods, and a lie only matters when the value is otherwise wrong, so I accept these rows (unlike
  CORE-003-tests-r4 F2, the order is stated). No message text and no internal name is pinned. Only the public
  API is imported (`NAMES`, `:27-32`).
- **Nondeterminism.** The hook keys use `str.__hash__` (randomized); dict probing calls `__eq__` only on a full
  hash match, which never happens between distinct field names. The only clock is `perf_counter` in the harness.
  The `api` fixture proves `H001_COSTS` is untouched after every row (it passes on the reference).
- **Timing harness (`:787-828`).** It is the CORE-003 tests-r3/r4 harness unchanged: `perf_counter` around the
  public call only, daemon worker, `join(timeout=10)`, `faulthandler.dump_traceback_later(20, exit=True)` armed
  and cancelled in `finally` inside `capsys.disabled()`, exact type, then `elapsed < 1.000`, then the caller-context
  check. pyproject sets no `faulthandler_timeout`, so the cancel cannot clear a pytest timer.
  Slower runner: under the reference all 403 timed calls finish in at most **0.0033 s**. Ordinary
  rows have over 300× headroom; scheduling noise cannot reach 1 s.
  A hang fails loudly. When the worker holds the GIL in a C call, the main thread cannot return from `join`. The
  watchdog fires at 20 s, prints both stacks, and the process exits 1 with no pytest summary. Observed on the
  current code (`charges.py:90` and `:91`, 18:24:08–18:24:49) and on mutants M14, M22 and M09. A pure-Python
  hang releases the GIL, so `join` returns at 10 s and the row fails with "still alive". The cost of a kill is
  that CI loses the per-test summary for that run, though the job still fails with a traceback (CORE-003
  precedent). CI timing itself is not checked (see Not checked).

### Red run (item 4)
`timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider -k "not huge_on_grid_lots and not extreme_exponent_volume_step" --tb=line -rA --junitxml=<scratch>`
(18:07:58–18:08:12): **1808 failed, 949 passed, 2 deselected in 13.66s**, exit 1. No failure outside CORE-004;
789 = 949 − 160 existing tests pass. The 639 warnings come only from my `--junitxml` flag (`record_property is
incompatible with junit_family 'xunit2'`). Per-function counts equal the handoff table exactly. Failure kinds:
`DID NOT RAISE` (TypeError, CostsError, BadStress, BadProvenance), `InvalidOperation`/`ValueError`/`OverflowError`/
`ZeroDivisionError`/`AttributeError` from unvalidated values reaching arithmetic, `BadVolume`/`BadPoints` where
the model error is due, iteration counts of 0 or 3 instead of 1, oversized values returned or `decimal.Overflow`,
and `ValueError: Exceeds the limit (4300 digits)`. None is a fixture, name, import or key error in the test code.
The 160 passes:
- unchanged behaviour (47): Mapping type rows (7), dict/proxy copy rows (2), `unknowns` read-once (2),
  extreme-exponent lots (7), 1,000-digit edges (10), adjusted edges (15), zero (3), AC-05 (1);
- coincidences (113), all named in the handoff: 75 AC-03 rows (60 via `stress()`'s `replace` re-running
  `__post_init__`; 15 where `CostBreakdown` rejects NaN or an int `stress_factor`, or `_points` rejects `True`),
  31 AC-04 rows (21 lots outside range or off grid; 2 factors underflowing to 0; 8 `CostBreakdown` ordered-sum
  mismatches), 7 AC-06 rows.
None of these rows can never fail: every edge group failed under at least one mutant (M07, M08, M10, M03), and
the coincidental rows each sit next to a row of the same slot that fails today.
The two deselected rows, run alone (`timeout -k 10 120 uv run --offline pytest tests/acceptance/CORE-004 -q -p no:cacheprovider -k <name>`):
`Timeout (0:00:20)!` in `charges.py:90 _on_grid` and `charges.py:91 _on_grid`, exit 1 each, as the handoff says.

### Satisfiability (reference oracle; supports F1)
`scratch\ref\src\sochron\costs\{model,charges}.py` is a hardened costs package written in scratch for this
review only and handed to nobody: exact types, `finite_bounded` with the risk constants, provenance read first
and once, and validation once per public call. Run in place: CORE-004 file **1970 passed in 2.48s**. Whole suite
**1 failed, 2758 passed in 8.53s**. The failure is F1. All CORE-002 and CORE-003 locked rows pass, so the new
tests do not conflict with any locked test.

### Mutation spot-check (item 5)
Each tree is `scratch\ref\src` with one change made by `tools\mutants.mjs` (each pattern must match exactly
once). Command per tree, from the tree: `timeout -k 10 300 uv run --project <repo> --offline --no-sync pytest -c pytest.ini --rootdir . -q -p no:cacheprovider --tb=no -rf <repo>/tests/acceptance/CORE-004/test_costs_hardening.py`
(≈18:17–18:24).

| Mutant (one plausible wrong fix) | Result | Rows that catch it |
|---|---|---|
| M01 lots accepts a `Decimal` subclass (isinstance) | 28 failed | AC-01 decimal, lots × 7 × 4 |
| M02 validates one read of the Mapping, stores a second read | 2 failed | AC-02 copy (mapping, proxied) |
| M03 Mapping traversed twice (key set, then copy) | 20 failed | AC-02 copy (2), use read-once (18) |
| M04 use-time check covers types and size but no domain rule or key set | 309 failed | AC-03 matrix 252, hook 32, AC-06 25 |
| M05 use-time check skips the `triple_swap_weekday` range | 33 failed | AC-03 matrix 24, AC-06 9 |
| M06 key check `isinstance(key, str)` | 25 failed | AC-02 keys 3, AC-03 keys 9, matrix 13 |
| M07 adjusted bound `>=` instead of `>` | 15 failed | AC-04 adjusted edges |
| M08 digit bound 999 | 10 failed | AC-04 1,000-digit edges |
| M09 digit bound ignores trailing zeros | killed by watchdog; without the 2 watchdog rows 106 failed | all `trailing_zero_coefficient` rows; 30M-digit row |
| M10 zero refused by the exponent bound | 3 failed | AC-04 zero rows |
| M11 `stress()` rereads the container through `replace` | 2 failed | use read-once (stress) |
| M12 `round_trip_cost` calls the public charges (several reads) | 2 failed | use read-once (round_trip_cost) |
| M13 provenance read after the other fields | 32 failed | AC-03 read-first hook rows |
| M14 `check_volume` compares lots before re-validating the model | killed by watchdog (`_on_grid`, 18:21:51–18:22:14); without the 2 watchdog rows 17 failed | volume_step `1E-999999999` at use; AC-03 matrix 13; AC-01 4 |
| M15 `BadSides` message formats the int | 3 failed | AC-06 sides |
| M16 `CostModel` subclass constructible (refused only at use) | 1 failed | subclass constructors |
| M17 `status` keeps the CORE-002 membership test | 3 failed | AC-01 str status, impersonation |
| M18 `as_of` refuses only `datetime` | 2 failed | AC-01 date (plain, never-equal) |
| M19 counts accept an int subclass | 14 failed | AC-01 int (sides, nights) |
| M20 `unknowns` reads provenance once but checks no field | 146 failed | AC-01/03/04/06 `unknowns` rows |
| M21 provenance values `isinstance(Provenance)` | 16 failed | AC-01/02 values 3, AC-03 matrix 13 |
| M22 rational grid test before the size bound | killed by watchdog (`_on_grid`, 18:23:37–18:23:58); the other 1968 rows pass | 30M-digit on-grid lots (the only guard) |
| S01 `CostBreakdown` bounds only `total`/`stress_factor` | **1970 passed** | none: F2 |
| S02 `CostBreakdown` bounds all but `total` | **1970 passed** | none: F2 |
| S03 `volume_step` positive exponent unbounded | **1970 passed** | none: F3 |

### Red flags (item 6)
`bash scripts/controls/red-flags.sh origin/main` (≈18:25): exit 0, merge-base `82a7f3e`, changed files none,
deleted or renamed tests none, untracked (not scanned) `docs/handoff/CORE-004.md` and the new test file, control
files touched none, **0 pattern groups with hits**. The script skips untracked files, so I applied its eight
pattern groups to the new file by hand with `grep -cE`. There is 1 hit: "Type checks disabled" at `:313`, the
docstring "… accept it as any valid value", which matches the TypeScript `as any` pattern. It is prose, not a
disabled check. After the red commit the scan will report it, and this is its explanation. The other groups
(skip/only/xfail, lint, placeholder/mock, swallowed errors, secrets, destructive commands, order/account
mutation) have 0 hits. The `except BaseException` at `:800` transports the exception to the test thread and does
not swallow it.

## Not checked (and why)
- **`stress()` with the edge factors** (Q6): BLOCKED by guard-bash, as above.
- **CI timing and OS.** I did not read `.github/workflows/` (locked; not needed). Timing headroom was measured
  on this machine only. 64-bit decimal limits were confirmed here (`MAX_EMAX 999999999999999999`); the extreme
  zero rows need them.
- **Provenance records changed after construction** (for example `object.__setattr__` on a record's `status`).
  AC-03 covers `CostModel` fields, and the construction rule for values is "exactly `Provenance`", so the tests
  match the contract. Re-validating each record's fields at use would be a contract addition for the owner,
  not a test defect.
- **In-domain huge ints and in-bound slow grids** (for example `volume_step 1E-1100000` at use). The contract
  bounds only rejection time (Q7; CORE-003 F10 precedent).
- **The implementation.** None exists. My reference oracle is scratch-only evidence that the tests can be
  satisfied; it is not a proposal for `src/`.
- **`node scripts/controls/check-locked-paths.mjs`**, CI, the owner demo, merge and deploy (not requested). No
  terminal, broker, account or network action took place.

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `wc -l …; git status --short; git branch --show-current; git rev-parse HEAD` | PASS; detector fired once (see Blocks) | 82a7f3e + applied patch | ≈18:0x |
| `sha256sum` × 2; `git hash-object --path=…`; `git hash-object --no-filters`; `wc -lc` | PASS: all equal the handoff | same | ≈18:0x |
| `git apply -R --check docs/proposals/CORE-004-tests.patch` (standalone) | PASS: exit 0, no output | same | ≈18:0x |
| `git status --short --untracked-files=all --ignored`; `git diff --stat HEAD`; `git diff --stat origin/main -- src/sochron/costs` | PASS: two untracked paths only; no tracked change; costs identical | same | ≈18:0x |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider -k "not huge_on_grid_lots and not extreme_exponent_volume_step" --tb=line -rA --junitxml=<scratch>` | FAIL as intended: 1808 failed, 949 passed, 2 deselected | same | 18:07:58–18:08:12 |
| `node tools/group.mjs red-full.xml …` (per-function grouping) | counts equal the handoff table | — | ≈18:09 |
| reference oracle: CORE-004 file in place; whole `tests/` in place | 1970 passed; 1 failed (F1), 2758 passed | scratch ref | ≈18:1x |
| 25 mutant runs (table) | 22 wrong fixes caught (21 by ordinary rows, M22 only by the watchdog); 3 survivors (F2, F3) | scratch mut | ≈18:17–18:24 |
| each watchdog row alone on the current code, `timeout -k 10 120` | FAIL as intended: `Timeout (0:00:20)!`, exit 1 each | 82a7f3e + applied patch | 18:24:08–18:24:49 |
| `bash scripts/controls/red-flags.sh origin/main`; manual `grep -cE` of its 8 groups; byte counts | PASS execution, 0 groups; 1 prose hit by hand (`:313`); ASCII, 0 CR | same | ≈18:25 |
| `uv run --offline --no-sync python -B -c` (bool subclass, decimal limits; repo root) | bool not subclassable; 64-bit limits | — | ≈18:26 |
| reference timing, `-rP -k "oversized or extreme_exponent or huge_on_grid"` | 403 timed calls, slowest 0.0033 s | scratch ref | ≈18:27 |
| scratch probe of the proposed F2/F3 rows on ref, S01, S02, S03, current code | 16/16 pass; 12, 1, 3 fail; 16/16 fail | scratch | ≈18:28 |
| inline `python -c` probe of `stress()` edge factors from a scratch tree | BLOCKED by guard-bash (stopped, not rerun) | — | ≈18:29 |

Delivery: review artifact written, unstaged. The applied test file is **verified byte-exact and fit to commit
red**. CORE-004 itself is not implemented, verified, merged or deployed. Next action: the implementer commits the
test file and the handoff red (`test(costs): acceptance tests for CORE-004`, `Refs: CORE-004`) with this review.
The owner decides F1 before implementation finishes (recommended: let the implementer change
`tests/unit/risk/test_risk_unit.py:252-254`). F2 and F3 go to a follow-up test-author patch, which can come after
the red commit and before the implementation review.

Ready to commit red: yes

Findings open: 3
