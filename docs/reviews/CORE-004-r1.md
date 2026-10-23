# Review CORE-004 round 1 · base main (`origin/main` 6bd9ef8; merge-base 82a7f3e) · head 5f7a382 + applied `CORE-004-tests-r2.patch` (uncommitted) · reviewer Claude Code (fresh session, reviewer under the PLAN-001 role swap)

Scope: the CORE-004 change against `origin/main`. That is commits `594388d` (locked tests, red),
`c55234e` (contract v1.1) and `5f7a382` (implementation), plus the round-2 locked rows, applied and
uncommitted. The FIX-001 and OPS-001 commits on the branch are already merged and are not reviewed here.
Inputs: contract v1.1 (`docs/contracts/CORE-004-costs-hardening.md`), `git diff origin/main...HEAD`, the
working-tree diff of the locked file, `docs/reviews/CORE-004-tests-r1.md`, the CORE-002 contract (API block,
error table) and the risk precedent (`src/sochron/risk/policy.py`, `sizing.py`). I read the handoff only
after my first round of findings. I am not the implementer, not a test author and not the tests-r1 reviewer.
I wrote only this file. I staged, committed and pushed nothing. Scratch evidence is under
`C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\2b4479a6-242f-4854-b879-6b60d639e00a\scratchpad\`:
`tools\` holds the probe scripts, `oldpkg\oldcosts\` holds `git show origin/main:src/sochron/costs/*.py`,
and `mut\` holds the mutant and fix-sketch trees. All times are 2026-10-23, +07:00.

**Part A (round-2 locked rows): ready to commit: yes.** The bytes are exact and the patch reverses
cleanly. The existing tests are unchanged in meaning: the AST matches, and the diff adds lines only. The
23 new rows close tests-r1 F2 and F3. I re-ran the three surviving mutants myself, and each is now caught
by exactly the intended rows. The rows add no constraint beyond the interpretations that tests-r1 accepted.

**Part B (implementation): no blocking defect.** Honest inputs give identical results, digit for digit.
Across 9,000 random models × 11 calls × 3 caller contexts, old and new code agree on every result
(`as_tuple`), every error type and the caller's context state. With a valid model, error precedence is
identical in every function. The suite gives 2784 passed and 0 skipped, and the CORE-002/003 locked tests
are untouched. I found six Low findings. Two are confirmed: F1 (provenance attribute read twice) and F2
(the implementer's evidence package is missing). The other four are questions for the owner: F3
(provenance records are not re-checked at use), F4 (a non-str `status` changes from `BadProvenance` to
`TypeError`), F5 (in-domain huge ints take about 15 s; this predates CORE-004) and F6 (a metaclass
`__name__` can choose the error type of a refusal; the same pattern is in risk).

## Part A: round-2 locked rows (`docs/proposals/CORE-004-tests-r2.patch`)

- **Bytes.** `sha256sum`: patch `6c098f52fca998a355f36783bb22f56111208ba057ae89918d5c8c0cc8cc43b2`, file
  `4d79519faaf67fd0cdc30bb38d329c0db67bd4b04639bf2f8702fc1a432e91f8`. `git hash-object`: blob
  `cc64a0736c9a752a7a75a34e8214a97ef5ccc1c4`. All three equal the handoff (`docs/handoff/CORE-004.md:250`,
  `:256`). `git apply -R --check docs/proposals/CORE-004-tests-r2.patch`, run alone: exit 0, no output.
- **Detector.** After my first read-only command (`git status && git log …`), `check-locked-after.mjs` listed
  exactly `uncommitted M tests/acceptance/CORE-004/test_costs_hardening.py`. That is the only target of the
  patch the brief said was applied. Under CLAUDE.md I verified the expected SHA256 and blob (above) and
  continued. It did not fire again.
- **Existing tests unchanged.** `tools\ast_compare.py` reads HEAD's text from `git show` into memory (no
  copy on disk). All 112 HEAD top-level statements are present, unchanged by `ast.dump` and in order, and
  no HEAD function's AST changed. Ten statements are added: one `ImportFrom` (`Context`, `ROUND_HALF_EVEN`),
  four `Assign` and five `FunctionDef`. None rebinds a HEAD name. The working-tree `git diff` has only `+`
  lines, so comments are unchanged too.
- **F2 closed.** `test_ac04_oversized_breakdown_field_rejected_alone` has 13 rows. Each one oversizes
  exactly one `CostBreakdown` field: `spread`, `commission`, `slippage` or `swap` in three shapes, or
  `total` as a 1,001-digit trailing-zero form of the honest ordered sum. The other components are zero (or
  honest), and `total` is the CORE-002 ordered sum: left to right, each addition rounded at precision 28
  with ROUND_HALF_EVEN. `_within_bound` asserts that every other field is in bound. I ran my own mutants
  from scratch trees (HEAD costs plus one change) against the locked file in place:
  - S01, which bounds only `total` and `stress_factor`: 12 failed, exactly the 12 component rows.
  - S02, which bounds every field except `total`: 1 failed, exactly the `total` row.
  - The unchanged HEAD copy as control: 1993 passed.
- **F3 closed.** `test_ac04_positive_adjusted_volume_step_rejected_fast` has 10 rows: `volume_step =
  1E+1100001` at construction and through all 9 model-taking callables. S03, which skips the bound for a
  positive-exponent `volume_step`, fails exactly these 10 rows.
- **Over-constraint.** None beyond tests-r1. The rows require exactly `CostsError` (Q1) and model-first
  validation at use (Q2), both already accepted. A correct implementation passes whatever order it checks
  in. The component rows are consistent, so an implementation that checks consistency first still reaches
  the bound. The `total` row is numerically equal to the ordered sum. Timing and the caller-context check
  reuse the round-1 harness unchanged.
- **Gaps the round-2 author left out (handoff `:227-242`).** My judgment on each:
  1. Positive-adjusted component rows: acceptable to leave out. No consistent in-bound `total` exists for
     them. A mutant that skips only this bound survives, because the round-1 row also oversizes `total`. In
     production that mutant would turn a direct `CostBreakdown(spread=1E+1100001, total=0)` into a
     `decimal.Overflow` from the sum check. That is a wrong error class, but it is still a refusal, and only
     direct construction by a caller reaches it.
  2. `total` in the other shapes: not a gap. An oversized `total` that is not a trailing-zero form of the
     sum is inconsistent, so `CostsError` follows whether or not `total` is bounded. No result is returned,
     and the error class is the same either way.
  3. Accepted-edge row for `volume_step = 1E+1100000`: optional. Only an over-strict bound on the positive
     step alone escapes. The shared bound function is covered by the round-1 edge rows (mutants M07, M08).
  4. Dependence on the exponent range: no false failure is possible. A correct implementation raises
     `CostsError` at the bound either way, and the contract forbids changing the context.

## Part B findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | `src/sochron/costs/model.py:150-152` (`_check_model`) | The attribute `model.provenance` is read twice: once for `isinstance(…, Mapping)` and once for `dict(…)`. `isinstance` against an ABC runs caller code, because `ABCMeta.__instancecheck__` reads `instance.__class__`, which a planted class may define as a property. Probe `tools\hostile.py` P1 plants a Mapping with `object.__setattr__`. Its `__class__` property replaces `model.provenance` with `list(H001_COSTS.provenance.items())`, a list of pairs. `unknowns(model)` then **returns** `('commission_per_lot_per_side', 'slippage_points_per_side', 'triple_swap_weekday')`, built from that list. The next call on the same model raises `TypeError: provenance must be a Mapping, not list`, as does planting the list directly. | A Mapping planted after construction whose `__class__` lookup swaps the attribute. This is the threat model of AC-03 and `test_ac03_provenance_is_read_before_the_other_fields`, where planted Mapping code changes the model during the read. | For that call, the Mapping rule (contract row 2: "ไม่ใช่ Mapping → TypeError") checks one object while the copy is taken from another. The invariant "อ่าน provenance ครั้งเดียว" (contract `:42`) and the docstring "read first and only once" (`:146`) do not hold for the attribute. The copy still passes every content check (key types, key set, record types), so the result is consistent. Construction is not reachable in practice, because the planted code has no reference to the instance being built. | Read the attribute once: `provenance = model.provenance`, then `isinstance(provenance, Mapping)` and `dict(provenance)`, and use `provenance` in the message. | Scratch sketch `mut\FIX\src\sochron\costs\model.py`. Under P1 the call now copies the object it checked: the planted Mapping's own iteration runs, and no list is accepted. The locked and unit suites (acceptance, golden, unit) against the sketch: **2776 passed**. Regression idea for `tests/unit/costs`: plant the swapper above and assert that no result is computed from the swapped-in list. |
| F2 | Low | confirmed | `docs/handoff/CORE-004.md` (test-author sections only: `:1-186`, `:188-356`); `docs/evidence/CORE-004.md` (absent) | The implementer's evidence package is not in the repository. `.claude/skills/implement-task/SKILL.md:38-46` asks for it before review: a completion report per AC, red-flag explanations, a demo script, and a handoff with the claimed commands, what was not verified, known risks and where to look hard. The contract lists both files as allowed (`:26`). The implementer's claimed result and decisions exist only in the commit message of `5f7a382` ("Suite: 2761 passed, 0 skipped", "Ints stay exact and are not size-bounded") and in this review's brief. | — | AGENTS.md "Handoff only through files and commits" is not met on the implementer's side. Nobody can tell from the repository which checks the implementer ran and when, or that F4 and F5 below were deliberate. This is an F01/F17 risk at the PR. | Before the PR: add an implementer section to the handoff and write `docs/evidence/CORE-004.md`, then commit both. The section covers contract v1.1, the commits, each command with result, commit and time, the decisions (model checked first, snapshot reuse, ints not bounded, message changes, the status and `datetime` refusals, the risk unit-test edit) and what was not verified. | Both files exist at a commit on the branch and include the AGENTS.md completion report. |
| F3 | Low | question | `src/sochron/costs/model.py:181-183` (records checked for exact type only); `:211-214` (`unknowns`), `:208` (`stress` carries the records) | At use, each provenance record is checked only for `type(record) is Provenance`; its fields are not checked again. Probe P2: on a `replace(H001_COSTS)` copy, take a fresh copy of the `commission_per_lot_per_side` record and set its `status` after construction to `_Stranger("assumed")` (a str subclass equal to nothing), to `"bogus"`, or to `None`. In each case `unknowns()` returns `('slippage_points_per_side', 'triple_swap_weekday')`, so the assumed commission disappears, and `stress()` copies the record into its new model. The construction rule refuses all three values (`TypeError`, `BadProvenance`, `TypeError`). tests-r1 listed this under "Not checked" as a possible contract addition. | A Provenance record changed after construction, with the same `object.__setattr__` technique that AC-03 covers for CostModel fields. `replace(H001_COSTS)` shares its record objects with the singleton, so a record changed through a copy also changes `H001_COSTS`. | `unknowns()` is how a research report lists assumed or unknown cost constants. The contract's "Current behavior" quotes this exact concern: a status that hides an assumed value from `unknowns()`. It is closed at construction but still open at use. Reaching it requires in-process mutation of a frozen object. | The owner decides whether AC-03's "same rule as at construction" covers the records. If yes: move the field checks of `Provenance.__post_init__` into one function and call it for each record in `_check_model`. The cost is 11 small checks per call. | The same scratch sketch: P2 now raises each record's construction error (`TypeError` or `BadProvenance`) at every use, and the 2776 locked and unit tests pass. Regression idea: AC-03-style unit rows that change one record field (status subclass, `"bogus"`, `None`; `as_of` a `datetime`; `source` an int) through all 9 model-taking callables. |
| F4 | Low | question | `src/sochron/costs/model.py:112`; `docs/contracts/CORE-002-costs.md:41`, `:98` | CORE-002 specifies "status นอก 4 ค่า → BadProvenance". The new `require_exact(self.status, str, "status")` runs before the membership test, so a non-str status now raises `TypeError`. Probe `tools\precedence.py` (Provenance block, 180 combinations, 6 differ): `status=None` and `status=1` gave `BadProvenance` on origin/main and give `TypeError` at HEAD. The other differing rows involve a `datetime` `as_of`, which AC-01 requires to fail. Contract v1.1 says the CORE-002 API only gains refusals ("เพิ่มเฉพาะการปฏิเสธ") and names only subclasses for the new `TypeError`. No locked test pins the class for `None` or `1`. | `Provenance(..., status=None)`, or any other non-str status. | An input that CORE-002 already refused now raises a different class. A caller that catches `CostsError` around provenance loading would now see an uncaught `TypeError`. The new behaviour matches the rule in `errors.py` ("wrong scalar types raise TypeError") and risk's `SizeDecision.reason` (`require_exact`, then membership). It is also safer: a non-str object with a lying `__hash__`/`__eq__` could otherwise pass the frozenset membership test. | The owner chooses. (a) Recommended: accept the change and record it in the contract (a v1.2 row: non-str status → `TypeError`) and in the handoff. (b) Keep CORE-002's `BadProvenance` for non-str values and refuse only str subclasses with `TypeError`. | (a) The contract row plus one unit test that pins `TypeError` for `status=None`. (b) The same test pinning `BadProvenance`. |
| F5 | Low | question | `src/sochron/costs/charges.py:50-53` (points), `:72-77` and `:138-145` (sides), `:162-175` (nights); `model.py:196-198` (int factor); decision in `5f7a382` and `tests/unit/costs/test_costs_unit.py:169-176` | Ints stay exact and are not size-bounded. That matches contract row 4, which bounds only Decimals (tests-r1 Q7). Because int→Decimal conversion time grows with the square of the digit count, in-domain huge ints are slow. `tools\timing.py` at HEAD, one call each: points `10**200000` took 0.368 s. With `10**1000000`: points 14.087 s; sides 14.522 s; nights 14.418 s, then `decimal.Overflow`; stress factor 15.368 s, then `decimal.Overflow`. This predates CORE-004: origin/main takes 15.036 s for points and 15.156 s for nights, then `decimal.Overflow` (`tools\timing2.py`). A model int field of that size (for example `spread_fallback_points`) costs nothing at construction (0.000 s) and the full time at every use. | A 1,000,000-digit int (about 415 KB) in a count or points slot, or in a model int field. | One call holds the GIL for about 15 s, and two of the slots end in an ArithmeticError that is not a `CostsError`. This is not a regression, and it is outside the contract's bound. It is the same class as risk's accepted in-bound limitation (security pre-review r2 F10, `src/sochron/risk/policy.py:63-67`, E1 obligation L3). The implementer's unit test pins the unbounded behaviour (`10**1500`). | The owner chooses. (a) Recommended for this task: accept it as a recorded limitation with the same E1 obligation, since real inputs come from MT5 `symbol_info` and bar data. (b) A follow-up contract that bounds int size cheaply (`bit_length()`) with each slot's error. | (a) One line in the contract or handoff, and in PROGRESS. (b) With the same probe, every in-domain huge-int call is refused or answered in under 1.000 s. |
| F6 | Low | question | `src/sochron/costs/model.py:64`, `:83`, `:107`, `:111`, `:138`, `:151`, `:157`, `:163`, `:202`; `charges.py:55`, `:61`, `:124` (every `type(…).__name__` in a refusal message); the same pattern in `src/sochron/risk/policy.py:51-54` | Each refusal message reads `type(value).__name__`, which a metaclass can define as a property. Caller code then runs while the `TypeError` is being built, and it can raise any other error instead. Probe P3: `class Sneaky(Decimal, metaclass=NameMeta)`, whose `__name__` raises `BadVolume`. `check_volume(Sneaky("0.02"), H001_COSTS)` raises `BadVolume: caller-chosen error` instead of `TypeError`. A control str subclass with no metaclass gets `TypeError`. | A Decimal, int, str or date subclass, or a CostModel or Provenance subclass, whose metaclass overrides `__name__`. | AC-01's "ไม่มีกรณีไหนคืนค่า" (no case returns a value) still holds: the call fails. Its "Then `TypeError`" does not hold for this subclass shape, because the caller picks the error class. For example, a domain error might be treated as "skip this bar" where a `TypeError` would crash the run. Under scope v1.7 this is arguably caller code on its own object rather than a change to costs internals. Risk shares the pattern, so any fix belongs to both modules. | The owner chooses: accept it as a recorded limitation under scope v1.7, or, in a follow-up for both costs and risk, build the name without the metaclass lookup (`type.__dict__["__name__"].__get__(type(value))`) or drop the type name from these messages. | P3 gives `TypeError`, and one unit row per module covers a metaclass subclass in one slot. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

All at `5f7a382` plus the applied round-2 rows. This is local L2 evidence; CI has not run on this head.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Every AC-01 group in the locked file passes, including the subclasses that lie about their methods, `datetime` as `as_of`, and the subclass constructors. In my own reading, every argument and field of the CORE-002 API goes through `type(x) is …` checks; no `isinstance` is left on a value. F6: a subclass with a hostile metaclass is still refused, but with an error class the caller chooses. |
| AC-02 | PASS | The locked container, key and value rows pass. `dict(m)` performs one traversal and reads each key once, and keys are refused before any comparison runs. At construction, F1 is not reachable in practice. |
| AC-03 | PASS | The locked 13-use × 65-defect matrix passes, along with the read-first, read-once and key-at-use rows. Every CostModel field is checked again in every model-taking call (`_check_model` covers all 14 fields, and every public function calls `validate_model` first). F1 (attribute read twice) and F3 (records not checked again) are the remaining edges. |
| AC-04 | PASS | All 426 timed refusals pass. The slowest took 0.0039 s (`-rP` run). The edges are accepted: 1,000 digits, ±1,100,000, and zero with any exponent. The 23 round-2 rows pass. Worst in-bound grid checks, for information: at most 0.78 s per check, because `round_trip_cost` now runs one grid check instead of four (`tools\timing.py`, `timing2.py`). |
| AC-05 | PASS | `git diff origin/main -- tests/acceptance/CORE-002 tests/golden/CORE-002 tests/acceptance/CORE-003 tests/golden/CORE-003` is empty. The suite gives **2784 passed, 0 skipped**. The differential (`tools\diff_old_new.py`, seed 20261023) covers 3,000 random models × 3 caller contexts (default, hostile, tight with every trap on) × 11 calls, with dict, proxy and custom-Mapping containers and ints up to `10**40`. It found 0 differences in result `as_tuple`, error type or caller-context state. F4 concerns an invalid input, not an honest one. |
| AC-06 | PASS | The locked rows pass for `-(10**5000)` and `10**5000` in every count, spread, factor and model int slot. No refusal message formats an int; the f-strings were audited in my read of `model.py` and `charges.py`. |

## Checked, nothing found (and how)

- **Scope (F06), dependencies (F04, F18), test changes (F02).** `git diff --stat origin/main...HEAD` lists
  the contract, handoff, tests-r1 review, `costs/{model,charges}.py`, the locked CORE-004 file,
  `tests/unit/costs/test_costs_unit.py` (additions only) and `tests/unit/risk/test_risk_unit.py`. All of
  these are allowed. There is no `src/sochron/{timebase,core,risk}`, architecture, `.github`, control or
  lockfile change, and `costs/__init__.py` and `errors.py` are unchanged.
- **The F1 unit-test change (tests-r1 F1) keeps its intent.** The edit replaces line 252 with four lines
  inside the approved block. `tools\f1_origin.py` shows that the `TypeError` comes from risk's own check
  (`risk/sizing.py:127 size_position` → `:74 require_model` → `risk/policy.py:59 require_decimal`), not from
  costs. The `replace(H001_COSTS)` copy leaves the singleton untouched, and honest sizing still returns
  0.02 lots.
- **Risk still works with the new costs.** The CORE-003 acceptance, golden and unit suites pass inside the
  2784. Risk builds `Provenance` with exact `str` and `date` values (`H001_RISK`), and it imports
  `CostModel` and `CONTEXT` only for type and context use.
- **Error precedence with several bad arguments.** `tools\precedence.py` (seed 20261023) used only plain
  types and in-bound values: 3,000 random combinations of 1 to 4 bad arguments per function, 20,000
  CostModel combinations and 180 Provenance combinations. With a valid model, every function has **0**
  differences. Every function difference has a non-CostModel `model`: old code gave `AttributeError` (or a
  later domain error), new code gives `TypeError`, as contract row 1 requires. Every CostModel difference
  (554) involves a non-Mapping or int-key provenance, which is now refused first, as required by the
  read-first invariant and row 2. The Provenance differences are F4 and `datetime`.
- **Model checked first, once, in every public call; helpers take checked values.** Read in
  `charges.py:106-210` and `model.py:193-214`. Between `validate_model` and the arithmetic only exact-type
  checks run on the arguments, so no caller code runs and the fields used are the ones just checked. The
  locked read-once rows prove one traversal per call, including `round_trip_cost`.
- **`stress()` rebuilds from the validated snapshot.** `replace(model, stress_factor=…, provenance=snapshot)`
  does not read the container again, and the new model's `__post_init__` checks every field again.
- **Messages.** After the change, the only values echoed are bounded Decimals (about 1,010 characters at
  most in scientific form) and exact `str` values. No int is echoed.
- **Not exported.** `validate_model`, `bounded_decimal`, `require_exact` and `is_int` are not in
  `sochron.costs.__all__`; `__init__.py` is unchanged from main.
- **Caller context.** Unchanged in the differential under all three contexts, and in every locked
  `_call`/timed row. The module's private `_DIGITS` context keeps a sticky `Rounded` flag after a refusal
  (probe P4). That flag is never read, only `Rounded` is trapped, and risk does the same; it is not the
  caller's context.
- **Speed of honest calls (information).** `tools\overhead.py`, best of 5: `round_trip_cost` 9.7 → 16.0 µs,
  `spread_charge` 1.5 → 8.5 µs and `unknowns` 0.7 → 14.4 µs. This is the cost of checking the model at
  every use.
- **In-bound values that overflow the precision-28 context** (for example points `1E+1100000` with an
  honest `point`) still raise `decimal.Overflow`. That is unchanged CORE-002 behaviour (tests-r1 Q6), and
  old code did the same without any bound.
- **Invariants.** No float, clock, I/O or random use: the 8 architecture tests pass inside the 2784. No
  order path and no MT5 import. Money stays Decimal. The new helpers duplicate risk's rather than import
  it, which the contract plan requires (`:67`: risk depends on costs, not the reverse), so F07 does not
  apply.
- **Red flags.** One pattern group, "Type checks disabled", with three hits, all prose. The phrase "as any
  valid value" appears in the test docstring at `test_costs_hardening.py:314`, and the r1 review and the
  handoff quote it. The control-file list shows the locked CORE-004 test file, which is expected because
  it arrives through a D-006 patch and the PR needs the label. There are no hits in `src/`.

Outside this task's scope, for a later risk task: `src/sochron/risk/sizing.py:67` still says "costs
accepts subclasses", which is no longer true. Risk is a must-not-touch path for CORE-004.

## Not checked (and why)

- **CI on this head.** Nothing was pushed, and pushing is not in this role.
- **Another thread changing the model between `validate_model` and use.** That is in-process hostile code,
  outside scope v1.7.
- **Other platforms, free-threaded CPython, and timing on the CI runner.** All numbers come from this
  machine (Windows 11, CPython 3.12.15 via uv).
- **`node scripts/controls/check-locked-paths.mjs`, `test-controls.mjs`, the owner demo, merge and deploy.**
  Not requested. The locked-path check is expected to fail until the PR carries its label.
- **`.github/workflows/`.** Locked and not needed.
- **Decimal subclasses of `CostBreakdown`.** Out of scope (tests-r1 Q4).
- **A mutation run of the full implementation.** Only S01 to S03 and the fix sketch were run. The tests-r1
  mutation table (M01 to M22) covers the rest of the locked file.

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `git status && git log --oneline -8 && git rev-parse HEAD origin/main` | PASS; the post-run detector named exactly the round-2 patch target (see Part A) | 5f7a382 + r2 | ≈19:0x |
| `sha256sum` (file, patch); `git hash-object` (file) | PASS: all equal the handoff | same | ≈19:0x |
| `cd … && git apply -R --check docs/proposals/CORE-004-tests-r2.patch` | BLOCKED by guard-bash: "git apply must be one standalone literal command. Run each action separately." | same | ≈19:0x |
| `git apply -R --check docs/proposals/CORE-004-tests-r2.patch` (standalone rerun under the owner's standing exception) | PASS: exit 0, no output | same | ≈19:0x |
| `uv run --offline python -I tools\diff_old_new.py 3000` | PASS: 0 mismatches, 0 caller-context changes | old main vs 5f7a382 | ≈19:05 |
| `uv run --offline python -I tools\precedence.py` | 0 differences with a valid model; the others are explained above (F4) | same | ≈19:06 |
| `uv run --offline python -I tools\timing.py`; `tools\timing2.py` (child process per case, 120 s or 180 s cap) | in-bound grids at most 0.78 s; huge ints 14 to 15 s, the same on main (F5) | same | 19:07–19:10 |
| `uv run --offline python -I tools\hostile.py` | P1, P2 and P3 reproduce (F1, F3, F6); P4 harmless | 5f7a382 | ≈19:08 |
| `uv run --offline python -I tools\ast_compare.py` | PASS: 112/112 unchanged and in order, 10 added, no rebinding | 5f7a382 + r2 | ≈19:09 |
| `uv run --offline python -I tools\f1_origin.py` | PASS: refused in `risk/sizing.py:74` | 5f7a382 | ≈19:10 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: **2784 passed in 8.17s**, 0 skipped, exit 0 | 5f7a382 + r2 | 19:11:08–19:11:16 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; 1 prose group (explained above) | same | ≈19:11 |
| Mutant trees `mut\{HEAD,S01,S02,S03}`: `timeout -k 10 600 uv run --project <repo> --offline --no-sync pytest -c pytest.ini --rootdir . -q -p no:cacheprovider --tb=no -rf <repo>/tests/acceptance/CORE-004/test_costs_hardening.py` | HEAD copy 1993 passed; S01 12 failed; S02 1 failed; S03 10 failed (exactly the new rows) | scratch | ≈19:12 |
| `timeout -k 10 600 uv run --offline pytest tests/acceptance/CORE-004 -q -p no:cacheprovider -rP -k "oversized or extreme_exponent or huge_on_grid or positive_adjusted or rejected_alone"` | PASS: 426 timed calls, slowest 0.0039 s | 5f7a382 + r2 | ≈19:13 |
| `uv run --offline python -I tools\overhead.py` | information only (above) | old main vs 5f7a382 | ≈19:13 |
| Fix sketch `mut\FIX`: `tools\hostile.py <FIX src>`; then pytest from `mut\FIX` over `<repo>/tests/acceptance`, `tests/golden` and `tests/unit` | P1 and P2 closed; **2776 passed** | scratch | ≈19:14–19:15 |
| `git status --short --untracked-files=all; git diff --cached --stat` | only the two paths that were already uncommitted; nothing staged | 5f7a382 + r2 | 19:14 |

## Blocks and deviations

- guard-bash blocked one command: `git apply -R --check` chained after `cd … &&`. I reran the same check
  alone, from the repository root, under the owner's standing "standalone rerun" exception (F21). It
  passed. No other block occurred.
- The post-run detector fired once, before anything I changed, and named exactly the round-2 patch target.
  I verified the hashes and continued, as CLAUDE.md allows.
- No locked file was copied or edited. HEAD's text of the locked test was read into memory through
  `git show` for the AST comparison only. The mutant and fix-sketch trees hold only `src/sochron` from
  `git archive HEAD`, and the locked tests ran in place from them.

Findings open: 6
