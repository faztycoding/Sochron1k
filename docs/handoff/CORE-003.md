# CORE-003 test-author handoff

Date: 2026-10-22, Asia/Bangkok (+07:00).
Role: Codex test author; owner-authorized unattended run, no approval requested.
Contract: `docs/contracts/CORE-003-risk.md` v1.2, Tier High, approved 2026-10-22.
Branch: `feat/CORE-003-risk`.
Base HEAD: `4dcfb490775c77a326913ab2cd477cb162c1db31`.

Deliverable: a proposal patch, not applied to the repository working tree.
No staging, commit, Git metadata write, source implementation, dependency change,
external write or PROGRESS update. The explicit two-artifact instruction overrides
the skill's normal direct-test-write/commit and generic checkpoint steps.
This handoff is the checkpoint. No risk implementation was available or read.

## D-006 artifact and application

Regular file: `docs/proposals/CORE-003-tests.patch`.

SHA256: `7227c6bae65fcc85e050e45d15da57da5744276cab9eb60da00c6def4b476660`.

The patch contains exactly:

- Add `tests/acceptance/CORE-003/test_risk_acceptance.py`.
- Add `tests/golden/CORE-003/risk_cases.py`.
- Modify `tests/architecture/test_imports.py`.

The proposal directory is ignored by the repository's existing .gitignore.
The patch is intentionally a local handoff artifact; the applied tests are the
eventual commit contents. This handoff remains unstaged.

**Claude applies via D-006, verifies all hashes below, obtains a fresh-session
review, then commits red.** The supporting read-only oracle/authoring QA in this
run is not the required fresh-session delivery review.

1. Confirm the branch/base and that no conflicting test changes have appeared.
2. Recompute the patch SHA256. Run each Git command below standalone from the
   repository root:
   `git apply --check docs/proposals/CORE-003-tests.patch`
   then `git apply docs/proposals/CORE-003-tests.patch`.
3. Verify the SHA256 of each applied file and its
   `git hash-object --path=<repository-relative-path> <repository-relative-path>`
   against this table. Stop on a mismatch.
4. Obtain a fresh-session review of the contract and proposed test diff. Then
   run `uv run --offline pytest tests -q -p no:cacheprovider` from the repo root
   in Git Bash. Before implementation, expect seven failures and 45 passes.
5. Commit red after the review, using
   `test(risk): acceptance tests for CORE-003` and body `Refs: CORE-003`.
   Continue implementation under the approved contract. The owner's required
   control-change label/CI, security review, later implementation review and
   demo remain separate gates.

Expected **post-apply** bytes, not hashes of diff text:

| Repository-relative file | SHA256 | Git blob |
|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `aed95c1731e0652bef0f0aac9339e56bd55c8a7c3a78c3bdb78db0f81cf37b12` | `b88c9ce052bc2e6e3b4aabe35425ce2aca598417` |
| `tests/golden/CORE-003/risk_cases.py` | `50996b40c857a60f3eb96c6273bf2788ba33c2280f17c53c84ae2b0de8887189` | `49089bf971427a5ea8ae04e02f46a001acd19d3d` |
| `tests/architecture/test_imports.py` | `259ac6d4a9c9b0dfd165f0936b092ca458bde033b453c4ffde3b44787933b195` | `9c18e04813b6970bcc0884de8d4f5db91846d093` |

All three applied files are ASCII/UTF-8 without BOM, LF only, with exactly one
trailing newline. The existing `.gitattributes` declares text/eol=lf for all
three paths. Git blob IDs above were obtained through the repository's
attribute context using `git hash-object --path=<path> --stdin`, without
`-w`, and independently matched the Git blob header plus raw LF bytes.

## Verification and preserved evidence

All checks refer to HEAD `4dcfb490775c77a326913ab2cd477cb162c1db31` plus the named patch where applicable.
Times below are 2026-10-22 +07:00.

| Command or procedure | Result | Commit | Time |
|---|---|---|---|
| Branch/status/HEAD inspection | PASS: expected branch, clean starting tracked worktree/index; risk module absent | 4dcfb49 | not captured (initial preflight) |
| `uv run --offline --no-sync python -B -`, version probe | PASS: CPython 3.12.15, pytest 9.1.1; no environment sync/install | 4dcfb49 | not captured (before drafting) |
| Same uv stdin runner, independent Fraction/Decimal oracle and AST/source validator | PASS: 13 sizing/display rows, 10 threshold rows, both transition sequences, five range rows, positive/negative architecture probes, six AC function names and text format | 4dcfb49 + final patch | 07:59:37 |
| `git apply --check docs/proposals/CORE-003-tests.patch` | PASS, exit 0, no output; standalone, no apply to repository | 4dcfb49 + final patch | 07:59:07-07:59:08 |
| Git apply to pristine HEAD copies under sandbox temp, with original Git attributes context | PASS, exit 0, no output; all applied bytes equal drafts | 4dcfb49 + final patch | 07:59:12, approximate |
| `git hash-object --path=<path> --stdin` and SHA256 of each applied copy | PASS: all three digest pairs above, LF verified | 4dcfb49 + final patch | 07:59:37 |
| `uv run --offline --no-sync python -B -` invoking `pytest.main(["tests", "-q", "-p", "no:cacheprovider"])` after changing cwd to the sandbox-applied snapshot | FAIL (expected red): pytest exit 1, 7 failed, 45 passed, 0 skipped; wrapper exit 0 confirms that expected result | 4dcfb49 + final patch | 07:59:37.211-07:59:37.535 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; two inherited hit groups explained below; no secret/order/account-mutation hits | 4dcfb49 | 07:58, approximate |
| Same uv stdin runner, explicit scan of all three applied proposal files | PASS: zero skipped/focused tests, type/lint suppression, swallowed-error, secret, destructive/bypass or order/account-mutation hits | 4dcfb49 + final patch | 08:00:10 |

The sandbox used the existing uv-managed environment and **copies of 22 tracked files selected from src/, tests/, and the project
config/lock/Python-version/attributes files**, obtained from HEAD. No .git directory was created there.
No implementation or surrogate risk module was created to make tests pass.
The final copy is:

`C:/Users/MSI/AppData/Local/Temp/sochron-core003-i169ap75/final`

Exact sandbox apply command (executed with cwd set to that final copy):

```powershell
git --git-dir='C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/.git' --work-tree='C:/Users/MSI/AppData/Local/Temp/sochron-core003-i169ap75/final' apply --whitespace=error 'C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/docs/proposals/CORE-003-tests.patch'
```

The original .git supplies read-only attributes/config context; apply had no
index/cache/commit option. The working-tree target was only the temp copy.
The complete machine-readable digest/test output is also retained in
`C:/Users/MSI/AppData/Local/Temp/sochron-core003-i169ap75/verification.json`;
the necessary evidence is reproduced here so delivery does not depend on temp
retention.

Captured pytest output from the final patch:

```text
............FFFFFF..F...............................                     [100%]
================================== FAILURES ===================================
____________ test_ac01_exact_sizing_grid_caps_and_display_context _____________
No module named 'sochron.risk'

During handling of the above exception, another exception occurred:
AC-01: sochron.risk not implemented (No module named 'sochron.risk')
_________ test_ac02_daily_threshold_latch_rollover_and_time_reversal __________
No module named 'sochron.risk'

During handling of the above exception, another exception occurred:
AC-02: sochron.risk not implemented (No module named 'sochron.risk')
____ test_ac03_experiment_latch_authorized_restart_and_daily_preservation _____
No module named 'sochron.risk'

During handling of the above exception, another exception occurred:
AC-03: sochron.risk not implemented (No module named 'sochron.risk')
________ test_ac04_entry_recomputes_sizing_and_collects_exact_reasons _________
No module named 'sochron.risk'

During handling of the above exception, another exception occurred:
AC-04: sochron.risk not implemented (No module named 'sochron.risk')
________________ test_ac05_stop_change_cannot_widen_or_remove _________________
No module named 'sochron.risk'

During handling of the above exception, another exception occurred:
AC-05: sochron.risk not implemented (No module named 'sochron.risk')
___________ test_ac06_validation_provenance_immutability_and_range ____________
No module named 'sochron.risk'

During handling of the above exception, another exception occurred:
AC-06: sochron.risk not implemented (No module named 'sochron.risk')
________ test_ac07_risk_import_boundaries_no_clock_io_random_or_float _________

    def test_ac07_risk_import_boundaries_no_clock_io_random_or_float():
        source_root = Path.cwd() / "src"
        directory = source_root / "sochron" / "risk"
>       assert directory.is_dir(), f"AC-07: {directory} does not exist; implementation missing"
E       AssertionError: AC-07: C:\Users\MSI\AppData\Local\Temp\sochron-core003-i169ap75\final\src\sochron\risk does not exist; implementation missing
E       assert False
E        +  where False = is_dir()
E        +    where is_dir = WindowsPath('C:/Users/MSI/AppData/Local/Temp/sochron-core003-i169ap75/final/src/sochron/risk').is_dir

tests\architecture\test_imports.py:234: AssertionError
=========================== short test summary info ===========================
FAILED tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac01_exact_sizing_grid_caps_and_display_context
FAILED tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac02_daily_threshold_latch_rollover_and_time_reversal
FAILED tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac03_experiment_latch_authorized_restart_and_daily_preservation
FAILED tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac04_entry_recomputes_sizing_and_collects_exact_reasons
FAILED tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac05_stop_change_cannot_widen_or_remove
FAILED tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac06_validation_provenance_immutability_and_range
FAILED tests/architecture/test_imports.py::test_ac07_risk_import_boundaries_no_clock_io_random_or_float
7 failed, 45 passed in 0.27s
```

Collection succeeded. AC-01 through AC-06 fail in the intentional API loader,
not on test syntax/import mistakes. AC-07 fails on the absent risk source
directory. Existing timebase/costs/unit/architecture checks account for all
45 passes. This red run does not prove runtime assertions after the loader;
those require the future implementation and independent review.

## Test-to-contract coverage

Paths are relative to the repository. Acceptance function names below are in
`tests/acceptance/CORE-003/test_risk_acceptance.py`.

| AC | Test function | What it proves when implemented | Current status / actual failure |
|---|---|---|---|
| AC-01 | `test_ac01_exact_sizing_grid_caps_and_display_context` | Fresh H001 fixture per row; all specified sizing results, exact numerator/denominator edges, grid cap and explicit no-grid operands, cost budget, default cost=0, stress exclusion, exact safety inequality and single-rounded displays | FAIL: `AC-01: sochron.risk not implemented` |
| AC-02 | `test_ac02_daily_threshold_latch_rollover_and_time_reversal` | Inclusive exact daily limit, recovery latch, first-new-day 9900/9800 rows, baselines and state immutability, custom daily parameter, reversed dates | FAIL: `AC-02: sochron.risk not implemented` |
| AC-03 | `test_ac03_experiment_latch_authorized_restart_and_daily_preservation` | Experiment latch across recovery/days; exact allowlist/reason checks; restart only from an experiment halt; same-day daily latch and baseline retained; new daily crossing during restart; rollover and new experiment budgets | FAIL: `AC-03: sochron.risk not implemented` |
| AC-04 | `test_ac04_entry_recomputes_sizing_and_collects_exact_reasons` | All individual and combined denials, both sides, farther SL20 recomputation, isolated equity100, current-equity9800 thresholds, supplied cost/model and bound policy, exact stop subtraction and threshold neighbors | FAIL: `AC-04: sochron.risk not implemented` |
| AC-05 | `test_ac05_stop_change_cannot_widen_or_remove` | Long/short tightening and equality allowed; widening/removal rejected | FAIL: `AC-05: sochron.risk not implemented` |
| AC-06 | `test_ac06_validation_provenance_immutability_and_range` | Type/domain matrix across constructors/functions, result consistency, validation before denial branches, error hierarchy, exact H001 provenance and unknowns, frozen fields and defensive immutable copy, Overflow/Underflow and exact subnormal acceptance | FAIL: `AC-06: sochron.risk not implemented` |
| AC-07 | `tests/architecture/test_imports.py::test_ac07_risk_import_boundaries_no_clock_io_random_or_float` | Every risk Python module obeys imports/purity and float/random bans; missing package fails | FAIL: `src/sochron/risk does not exist; implementation missing` |

Only contracted public risk names are requested by _api; the only costs
imports in the new acceptance file are H001_COSTS and Provenance. All public
calls under test go through a context guard which compares context object
identity, precision, rounding, exponent settings, traps and flags on success
and error. Hostile caller precision4/ROUND_UP and enabled Inexact/Rounded/
Subnormal traps must not influence the local precision28 rules; caller
Overflow/Underflow traps are disabled to verify local range enforcement.
Display Decimal values are compared numerically, never by string/exponent.

The architecture change adds a risk-only permission for costs and a risk
checker analogous to costs. Every other existing function's AST is identical;
removing the added risk-only branch leaves _allowed_import's original AST.
The original timebase/core/costs test assertions remain intact. Static probes
covered allowed stdlib/core/costs/relative imports and rejected timebase,
MetaTrader5, random, floats, aliased clocks/open, Path I/O, environment/network
access and dynamic imports.

## Golden-table derivations

`tests/golden/CORE-003/risk_cases.py` contains literals with arithmetic comments;
it imports no production module. Fraction was used only for an independent
authoring check and exact invariant assertions, not to generate expected
production outputs at test runtime.

For H001, R=equity/400, per-lot risk=100*distance+cost,
uncapped=floor((R/per)/.01)*.01, cap=floor(volume_max/.01)*.01.
Take the lesser grid quantity, then return zero if it is below volume_min.
Actual risk is exact lots*exact per, rounded once for display.

| Sizing row | R (display) | per (display) | Exact raw lots | Grid floor / cap / final | Actual display |
|---|---|---|---|---|---|
| H00110000/12/0 | 25 | 1200 | 1/48 | .02 / 200 / .02 | 24 |
| H00110000/12/cost10 | 25 | 1210 | 5/242 | .02 / 200 / .02 | 24.2 |
| Equity100 | .25 | 1200 | 1/4800 | 0 / 200 / 0 | 0 |
| Equity100000000, stop.10 | 250000 | 10 | 25000/1 | 25000 / 200 / 200 | 2000 |
| Equity9600, stop12 | 24 | 1200 | 1/50 | .02 / 200 / .02 | 24 |
| Numerator precision edge | 24 | 1200 | 95999999999999999999999999999/4800000000000000000000000000000 | .01 / 200 / .01 | 12 |
| Denominator precision edge | 2 | 100 | 200000000000000000000000000/10000000000000000000000000001 | .01 / 200 / .01 | 1 |
| Max.025, equity10000, stop1 | 25 | 100 | 1/4 | .25 / .02 / .02 | 2 |
| Min.026/max.029, equity10000, stop1, cost0 | 25 | 100 | 1/4 | .25 / .02 / 0 | 0 |
| Equity9600, stop12, cost10 | 24 | 1210 | 12/605 | .01 / 200 / .01 | 12.1 |
| Gate distance20 | 25 | 2000 | 1/80 | .01 / 200 / .01 | 20 |
| Gate equity9800 | 24.5 | 1200 | 49/2400 | .02 / 200 / .02 | 24 |
| Single-rounded actual-risk edge | 25 | 100 | 500000000000000000000000000/2000000000000000000000000001 | .24 / 200 / .24 | 24.00000000000000000000000001 |

The numerator-edge exact R is23.99999999999999999999999999975; displaying24
must not round the decision up to.02 lots. The denominator-edge exact per is
100.00000000000000000000000001; displaying100 must not change the .01
decision. The extra actual-risk edge has exact per
100.00000000000000000000000005 and exact actual
24.000000000000000000000000012. Multiplying its already-rounded per display
would incorrectly return24.

Daily/experiment thresholds at baseline10000 are75/200. The golden table tests
just above, equal to and just below each allowed equity boundary. For
B=10000+1E-26, the daily equality equity is
9925.000000000000000000000000009925 and experiment equality equity is
9800.0000000000000000000000000098; adding1E-30 must remain above the boundary.

New-day first equity9900 gives daily loss0 against74.25, while experiment loss100
is below200. First equity9800 gives daily loss0 against73.5, but experiment
loss200 meets200. Restart at9800 preserves the old daily halt/baseline and
sets experiment budget196; equality is then9604. Restart at10500 sets budget210,
with equality10290. The reachable first-crossing-on-restart sequence is
halt9800 on day22, update10000 on day23, restart9925 on day23: daily becomes
true with baseline10000 while experiment rebases9925 and clears.

Gate isolated100 has loss0 and sized0: only below_min_volume/lots_exceed_sized.
The clear10000 state with current9800 has loss200 and sized.02: exactly both
halt reasons. Combined flags, equity100, request.015 and exposures1 produce
all six applicable reasons in alphabetical order; missing/wrong-side stops
omit the sizing branch but retain every other denial.

Range table: equity4E-999998 and4E-1000024 yield exact R1E-1000000 and1E-1000026,
both accepted. Equity4E-1000025 and4.4E-1000024 yield R1E-1000027 and1.1E-1000026:
Underflow, including the inexact subnormal that rounds to a nonzero value.
Equity4E1000002 yields R1E1000000: Overflow. Extra acceptance rows isolate
per-lot Overflow/Underflow and actual-risk Underflow, and accept exact subnormal
per-lot and actual-risk values. These use CONTEXT's Emin=-999999,
Emax=999999 and Etiny=-1000026, not a blanket exponent-below-Emin rejection.

## Red flags, deliberate exclusions and limits

The repository red-flag scan reports two inherited groups:
existing CORE-002 negative unit-test type suppression comments and documentation
quoting them; lint-suppression keywords appear in existing explanatory documents.
There are no new suppression comments in this proposal. Secret and
order/account-mutation groups are empty, and no existing tests are deleted or
renamed. The root scan does not inspect the ignored proposal itself; a separate
explicit scan of all three applied copies found zero relevant hits.

Deliberately left out:

- Risk implementation, implementation unit tests and any fake replacement
  implementation: this is the pre-implementation test-author task.
- Re-testing malformed fields internal to costs.Provenance: its existing CORE-002
  tests own TypeError/BadProvenance behavior. Risk tests validate provenance
  container, exact keys and Provenance member types without inventing risk APIs.
- Multiple-invalid-input exception priority: expressly unspecified. Negative
  tests alter one argument from a valid fixture; optional None stops are valid.
- Frozen-object identity assumptions, display string/exponent formatting and
  added numerical domain bounds: none is required by v1.2.
- Exhaustive Python security enforcement: the architecture test is the same
  AST-based check style as costs, not a proof against arbitrary dynamic Python.
- Broker/terminal/account integration, credentials, journal recovery,
  authenticated clearance, send binding, data/holdout/backtests and midnight
  valuations: excluded from CORE-003 or future R1/E1 work.
- CI, owner demo, implementation security/mutation/leakage review and positive
  runtime acceptance: no risk implementation exists. These are not passed by
  the expected-red run.
- Root application, staging/commit/push, other documentation and PROGRESS changes:
  explicitly outside this invocation. Locked-path/CI approval is checked later
  for the applied change; inherited branch control deltas are not recertified.

No unresolved contract question prevents authoring these specified tests.
Q-04 remains open by design: literal provenance marks assumptions/unknowns.
R1/E1 still choose cost budgets/research halt usage and implement persistence,
caller ordering and real authorization under their own contracts.

Delivery state: test proposal **implemented**, with patch/hash/oracle checks and
expected-red behavior verified locally. CORE-003 functionality remains
**FAIL (missing implementation)**; not verified, merged or deployed.
Next action: Claude applies via D-006, verifies hashes, obtains a fresh-session
review, then commits red.


## Implementation (Claude Code), 2026-10-22

Order followed: contract approved by the owner (`4dcfb49`, Tier High) → Codex tests applied via D-006, six hashes verified, reverse check passed, fresh-session review `docs/reviews/CORE-003-tests-r1.md` (ready to commit red), committed red at `831fa60` → implementation in the commit that adds `docs/evidence/CORE-003.md`.

- `src/sochron/risk/` = `errors.py`, `policy.py`, `sizing.py`, `halts.py`, `gate.py`, `__init__.py`; `tests/unit/risk/test_risk_unit.py` (16 implementer tests).
- `uv run --offline pytest tests -q -p no:cacheprovider` → 68 passed, 0 skipped at 08:29:05 +07 on the first run in the repository. A read-only dry run of the locked tests against the scratch draft (run from a scratch working directory so the loader's `cwd/src` found the draft; the locked files were read in place, never copied) passed earlier. No locked test was touched after `831fa60`.
- Decisions use `fractions.Fraction` throughout (floor and cap on the grid, minimum, loss thresholds, |entry - stop|), so the caller's Decimal context is never consulted or changed. Display fields are the same quantities computed as exact Decimals in an unbounded context (`MAX_PREC`, `MAX_EMAX`, `MIN_EMIN`, Inexact trapped) and rounded once with `create_decimal` in a copy of `sochron.costs.CONTEXT` with Overflow and Underflow trapped; those two become `RiskError`.
- Performance note: the first draft converted Fractions to Decimal through `Decimal(int)`, which took about 9.5 s per call for exponents near the context limits; the exact-Decimal route takes milliseconds.
- tests-r1 F1-F3 (coverage gaps) are answered by implementer unit tests that kill the named mutations: same-day calls with different daily and experiment baselines, gate states with different baselines and non-H001 loss limits, the cap boundary (uncapped == largest grid point is "ok") and a request at exactly `volume_max`. The owner's Codex chat suggested the policy-limit and `volume_step = 0.02` cases; both are unit tests too. tests-r1 F5 (architecture checker misses `time.localtime`, `os.urandom`, `uuid`, `subprocess`, `sys.stdout`) is inherited from CORE-001 and belongs to the test author; the risk sources use none of them.

Please look hard at (review r1, Tier High: security-reviewer pre-review first, then Codex):
- Any path that lets a caller enter at or beyond a loss threshold, exceed the sized lots, clear a halt without a listed name, widen or remove a stop, or evaluate an experiment with another policy.
- `restart_experiment` checks authorization before the halted check; with two defects the error order is unspecified by the contract.
- `RiskPolicy`, `HaltState` and `CostModel` hold a `MappingProxyType`, so they are not hashable; nothing in the contract asks for hashing.
- Exports `POLICY_FIELDS` beyond the API block (an addition).

## Tests r2 for contract v1.3 (Codex, 2026-10-22)

Owner-authorized unattended test-author amendment on `feat/CORE-003-risk`.
Base HEAD: `fcf77c5e71db0c7b796148b4368146a9799bc526`. This section supersedes the old v1.2
expected-red results above for this proposal only. The skill's normal commit,
PROGRESS update and prohibition on reading handoff notes are overridden by this
run's explicit owner instructions. No implementation source was inspected.

The regular proposal file is `docs/proposals/CORE-003-tests-r2.patch`.
Patch SHA256: `9a5d343ce72dd626152c2bf4394fd052297248c95e2d0da91e11de9fd620d28c`.
It modifies exactly the following two files against current HEAD:

| Repository-relative file | Expected post-apply SHA256 | Expected Git blob |
|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `69cd888f057fbcc1365f41d3aaae448dfccb6caf1b94e945029d120fedfab373` | `6d6630fbb5fe8cb49608bf39d46b5f82539ecc3d` |
| `tests/golden/CORE-003/risk_cases.py` | `68b34aced4943deda4ada60ed2d33872ba03ccebc8736fa29e38b5b64ec2e7c2` | `8a344a1b635239734807707e3f47396636df4f1e` |

The patch is unapplied in the repository. The two locked files and
`tests/architecture/test_imports.py` remain byte-identical to HEAD. Nothing is
staged; no .git write, commit, push, dependency or configuration change occurred.
Only the proposal and this handoff section are repository deliverables. The
proposal remains ignored under the existing docs/proposals rule; this handoff
is the session checkpoint instead of an out-of-scope PROGRESS edit.

**Claude applies via D-006, verifies hashes, obtains a fresh-session review,
then commits.** Check the branch/base and patch SHA256, then execute each command
as a standalone command from the repository root:

```text
git apply --check docs/proposals/CORE-003-tests-r2.patch
git apply docs/proposals/CORE-003-tests-r2.patch
```

After application, compare SHA256 and
`git hash-object --path=<repository-relative-path> <repository-relative-path>`
for both files with the table. Stop on a mismatch. Obtain a fresh-session review
of the contract and test diff before committing red. The read-only authoring QA
in this run does not replace that delivery review. The implementer separately
migrates unit-test callers and implements v1.3; that code is outside this patch.

Verification of expected bytes used 31 tracked HEAD files copied to
`C:/Users/MSI/AppData/Local/Temp/sochron-core003-r2-vj6znskd/applied`.
No .git directory or replacement implementation was created there. The patch
was applied only to those copies using the repository's read-only Git context:

```text
git --git-dir='C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/.git' --work-tree='C:/Users/MSI/AppData/Local/Temp/sochron-core003-r2-vj6znskd/applied' apply --whitespace=error 'C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k/docs/proposals/CORE-003-tests-r2.patch'
```

Both applied copies equal the drafts, contain English ASCII text, no BOM or CR,
and exactly one trailing LF. `git check-attr text eol` reports `text: set` and
`eol: lf` for both paths. Blob IDs used `git hash-object --path=<path> --stdin`
without `-w`, independently checked against the Git blob-header SHA1.

### Changes and acceptance evidence

| AC | What changed and what it proves | Current HEAD evidence |
|---|---|---|
| AC-01 | Retains all sizing/display rows and adds golden cap_equal: equity96000000, distance12, R240000, per1200, uncapped=max_on_grid=200, actual240000, reason ok. Closes tests-r1 F3 cap-label gap. | PASS: original AC-01 test including the new row. |
| AC-02 | Retains all daily tests. Adds day23 baselines10500/10000 with observations10421.26 and10421.25; baselines9900/10000 with9850 and9800. Adds custom daily .01/experiment .03 boundaries. Closes F1 and contributes F2. | PASS for original AC-02. New combined update/gate tests reach their gate call after the update assertions, then FAIL on the old signature. |
| AC-03 | Retains all restart assertions; adds genuinely halted/recovered state with daily10500 versus experiment10000, then restart10421.25 on day23: daily True, daily baseline10500, experiment baseline10421.25/False. Closes F1 restart gap. | PASS: original AC-03 and new distinct-baseline restart test. |
| AC-04 | Migrates all13 positional gate calls plus both generic argument dictionaries to include day. Adds all six round4 temporal rows and the rollover control, full sorted reasons/allowed flags, immutable inputs, stale validation and earlier-day TimeReversal. Adds different gate baselines and non-H001 loss limits (F2), and lots200 at volume_max with only lots_exceed_sized (F3). | FAIL: old HEAD gate lacks day. Positional calls report state must be exactly HaltState, not date; keyword calls report unexpected keyword argument day. |
| AC-05 | Preserves every stop-change assertion; adds exact-type and bound checks through AC-06 matrices. | PASS: original AC-05; numeric-domain additions remain red. |
| AC-06 | Covers every Decimal slot and at-use nested fields, 1000/1001 stored digits including trailing zeros, both adjusted limits and domain-compatible beyond-limit rows, huge-exponent zero, timed rejection, hostile scalar/object subclasses, four consumed model fields, provenance Mapping snapshot/copy/value rules, and request/state mutation before denials. Preserves all old assertions and strengthens display failures to exact RiskError so BadEquity/BadStop cannot mask them. | FAIL as intended: oversized inputs return or raise the wrong error, nested policy validation is missing, and gate calls still have the old signature. Accepted-bound constructors and Mapping cases run; some type-negative gate cases pass solely because the old signature raises TypeError, so those passes do not prove the intended v1.3 validation path. |
| AC-07 | No architecture edits. Existing three architecture tests run unchanged. | PASS for those three checks; FAIL for the AC's all-tests-green criterion. F5 remains a separate follow-up. |

The golden file remains production-independent literal data with hand arithmetic.
Its v1.3 tables include the temporal, distinct-baseline, custom-limit and bound
fixtures. The oracle independently checked all14 sizing rows with Fraction,
the new baseline/limit thresholds and coefficient/exponent representations.
Every inherited golden table/row remains present; an AST multiset comparison
confirmed that every original Assert node remains present. There are no skipped,
expected-failure, focused or weakened tests.

Positive-adjusted violations are omitted only where another valid domain would
be impossible: policy ratios must be below1, and an oversized positive volume_min
cannot remain <= an in-bound volume_max. The negative-adjusted volume_max case
has the inverse min/max problem. Those slots still have both coefficient
violations and the domain-compatible exponent violation. In-bound extremes are
accepted through public constructors/start without requiring expensive rational
calculations or inventing an accepted-input deadline. Original RANGE_ROWS and
all exact-subnormal/Overflow/Underflow expectations remain intact.

### Checks run

All times below are 2026-10-22 +07:00; commit `fcf77c5e71db0c7b796148b4368146a9799bc526`
plus the final proposal unless described as a preliminary draft. No new commit.

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean starting tree/index, expected task branch and base | fcf77c5 | initial preflight, exact time not captured |
| `uv run --offline --no-sync python -B -c` runtime/version probe | PASS: CPython3.12.15, pytest9.1.1, Windows11 build26200 | fcf77c5 | before drafting, exact time not captured |
| `git apply --check docs/proposals/CORE-003-tests-r2.patch` (standalone) | PASS: exit0, no output; patch NOT applied to repository | fcf77c5 | 09:33:56 |
| Git apply command above, with cwd=applied snapshot | PASS: exit0; applied files equal drafts | fcf77c5 | before final test run, approximately09:29 |
| uv stdin independent Fraction/Decimal oracle and AST/format checks | PASS:14 sizing rows, new thresholds/bounds, retained golden rows, AST/ASCII/LF checks | fcf77c5 | approximately09:30 |
| `uv run --offline --no-sync python -B .../run_tests.py safe -k 'not oversized and not positive_adjusted_bound and not extreme_equity_rejection_deadline'` | FAIL as intended on preliminary draft:145 failed,264 passed,204 deselected,0 skipped; no collection errors | fcf77c5 + preliminary draft | before final matrix expansion |
| `uv run --offline --no-sync python -B -` outer-watchdog full-suite invocation of `pytest.main(["tests", "-q", "-p", "no:cacheprovider", "--tb=no", "-rN"])` in applied snapshot | FAIL/incomplete:55-second process deadline; owned child terminated. Timeout logger then hit str/bytes TypeError, so no complete per-case record from this attempt is claimed. Incremental recording was added to the scratch runner. | fcf77c5 | approximately09:29-09:30 |
| `uv run --offline --no-sync python -B .../bounded_run.py remaining -k 'not extreme_equity_rejection_deadline'` -> same pytest.main arguments with the explicit -k selection | FAIL as intended:382 failed,266 passed,1 deselected,0 skipped,38.07s; no collection errors.648 cases completed;236 timed invocations recorded. | fcf77c5 | 09:31:00.530-09:31:38.663 |
| uv stdin assertion-preservation and timing-harness negative controls | PASS: all inherited Assert ASTs retained; harness rejects return, wrong exception, exact1.000s and unfinished daemon; accepts fast expected exception | fcf77c5 | approximately09:33 |
| `git check-attr text eol -- <two paths>`; `git hash-object --path=<path> --stdin`; applied-byte SHA256/blob-header cross-check | PASS: LF attributes and both digest pairs above | fcf77c5 | 09:33:56-09:33:57 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit0; two inherited pattern groups, explained below | fcf77c5 | approximately09:30 |
| `git diff --check`; status/index/HEAD inspection; handoff prefix and scoped-file byte checks | PASS: whitespace clean; only handoff tracked modification plus ignored proposal; index empty; HEAD unchanged; locked/architecture files identical to HEAD | fcf77c5 | 09:37:54 (final format check) |

The full suite was attempted; it did not complete within the outer deadline.
The completed selected run does not count its one deselected test as passed.
`test_ac06_extreme_equity_rejection_deadline` remains in the delivered suite,
using prebuilt Decimal("1E-999999999") and the exact F14 harness. Its isolated
completed result is UNKNOWN: it was not rerun after the full-run process deadline.
No timing criterion was relaxed, no test marked skip/xfail, and no retry-until-pass
was performed. Runtime results above are against current HEAD, not a surrogate.
The scratch runner suppresses source tracebacks to preserve the test-author role.

There was also an initial drafting assertion expecting14 positional substitutions;
AST inspection proved13 and verified every migrated call. An apply_patch scratch
re-open returned Access denied; subsequent authorized temp work used the owning
sandbox process without changing permissions. These are authoring-tool issues,
not application acceptance failures or successful test runs.

### F14 environment and every recorded interval

Reference environment observed: `Windows-11-10.0.26200-SP0; cpython 3.12.15 via uv`;
pytest9.1.1. Imports, Decimal creation, fixture construction and thread startup are
outside the measured interval. Each public invocation runs in a daemon Thread;
`join(timeout=10)` is followed by an explicit alive check, without a later wait.
Every completed interval uses perf_counter immediately around the public call.
The harness requires the exact slot error and elapsed <1.000s; returning is failure.
Environment and elapsed are emitted through pytest record_property and stdout.

There were236 timed invocations in the completed run:235 numeric intervals and
one unfinished call.234 failed and2 passed their assertions. The unfinished
`size_position.model.volume_step.negative_adjusted` worker triggered the required
alive check; its pytest case took28.052s wall time, demonstrating that thread
scheduling/GIL contention can delay the join beyond its nominal timeout. The
55-second outer process deadline protected the authoring run. A numeric interval
is not invented for an unfinished call. The two passing model.contract_size
exponent cases satisfy their observed error/time checks; that alone does not
prove validation happened before rational conversion internally.

Machine-readable logs and the applied snapshot are retained under
`C:/Users/MSI/AppData/Local/Temp/sochron-core003-r2-vj6znskd/`:
`remaining.json`, `remaining.jsonl`, `remaining.events`, `remaining.log`,
`digests.json`. The complete interval record is reproduced below so the evidence
does not depend on temp retention. Names beginning `bound:` refer to
`test_ac06_oversized_decimal_per_slot`; `branch:` refers to
`test_ac06_oversized_at_use_before_early_denials`.

| Timed case | Public-call interval (seconds) | Assertion result |
|---|---|---|
| `bound:size_position.equity.coefficient` | 0.000099700 | FAIL |
| `bound:size_position.equity.trailing_zero_coefficient` | 0.000068200 | FAIL |
| `bound:size_position.equity.negative_adjusted` | 0.153376500 | FAIL |
| `bound:size_position.equity.positive_adjusted` | 0.151482600 | FAIL |
| `bound:start_experiment.equity.coefficient` | 0.000008500 | FAIL |
| `bound:start_experiment.equity.trailing_zero_coefficient` | 0.000007400 | FAIL |
| `bound:start_experiment.equity.negative_adjusted` | 0.000007400 | FAIL |
| `bound:start_experiment.equity.positive_adjusted` | 0.000007300 | FAIL |
| `bound:update_equity.equity.coefficient` | 0.000075200 | FAIL |
| `bound:update_equity.equity.trailing_zero_coefficient` | 0.000064900 | FAIL |
| `bound:update_equity.equity.negative_adjusted` | 0.296149000 | FAIL |
| `bound:update_equity.equity.positive_adjusted` | 0.294323600 | FAIL |
| `bound:restart_experiment.equity.coefficient` | 0.000011900 | FAIL |
| `bound:restart_experiment.equity.trailing_zero_coefficient` | 0.000012600 | FAIL |
| `bound:restart_experiment.equity.negative_adjusted` | 0.000011500 | FAIL |
| `bound:restart_experiment.equity.positive_adjusted` | 0.000008900 | FAIL |
| `bound:check_entry.equity.coefficient` | 0.000002700 | FAIL |
| `bound:check_entry.equity.trailing_zero_coefficient` | 0.000002300 | FAIL |
| `bound:check_entry.equity.negative_adjusted` | 0.000002300 | FAIL |
| `bound:check_entry.equity.positive_adjusted` | 0.000002000 | FAIL |
| `bound:HaltState.day_start_equity.coefficient` | 0.000006200 | FAIL |
| `bound:HaltState.day_start_equity.trailing_zero_coefficient` | 0.000005700 | FAIL |
| `bound:HaltState.day_start_equity.negative_adjusted` | 0.000005700 | FAIL |
| `bound:HaltState.day_start_equity.positive_adjusted` | 0.000005500 | FAIL |
| `bound:HaltState.experiment_start_equity.coefficient` | 0.000003800 | FAIL |
| `bound:HaltState.experiment_start_equity.trailing_zero_coefficient` | 0.000005800 | FAIL |
| `bound:HaltState.experiment_start_equity.negative_adjusted` | 0.000015100 | FAIL |
| `bound:HaltState.experiment_start_equity.positive_adjusted` | 0.000005700 | FAIL |
| `bound:size_position.stop_distance.coefficient` | 0.000083000 | FAIL |
| `bound:size_position.stop_distance.trailing_zero_coefficient` | 0.000069400 | FAIL |
| `bound:size_position.stop_distance.negative_adjusted` | 0.151087800 | FAIL |
| `bound:size_position.stop_distance.positive_adjusted` | 0.150920900 | FAIL |
| `bound:EntryRequest.entry_price.coefficient` | 0.000007000 | FAIL |
| `bound:EntryRequest.entry_price.trailing_zero_coefficient` | 0.000006900 | FAIL |
| `bound:EntryRequest.entry_price.negative_adjusted` | 0.000005400 | FAIL |
| `bound:EntryRequest.entry_price.positive_adjusted` | 0.000005200 | FAIL |
| `bound:EntryRequest.stop_loss.coefficient` | 0.000005600 | FAIL |
| `bound:EntryRequest.stop_loss.trailing_zero_coefficient` | 0.000005800 | FAIL |
| `bound:EntryRequest.stop_loss.negative_adjusted` | 0.000005300 | FAIL |
| `bound:EntryRequest.stop_loss.positive_adjusted` | 0.000005300 | FAIL |
| `bound:check_stop_change.current_stop.coefficient` | 0.000009200 | FAIL |
| `bound:check_stop_change.current_stop.trailing_zero_coefficient` | 0.000009900 | FAIL |
| `bound:check_stop_change.current_stop.negative_adjusted` | 0.000007500 | FAIL |
| `bound:check_stop_change.current_stop.positive_adjusted` | 0.000008900 | FAIL |
| `bound:check_stop_change.new_stop.coefficient` | 0.000010000 | FAIL |
| `bound:check_stop_change.new_stop.trailing_zero_coefficient` | 0.000010600 | FAIL |
| `bound:check_stop_change.new_stop.negative_adjusted` | 0.000008100 | FAIL |
| `bound:check_stop_change.new_stop.positive_adjusted` | 0.000007300 | FAIL |
| `bound:RiskPolicy.risk_per_trade.coefficient` | 0.000014900 | FAIL |
| `bound:RiskPolicy.risk_per_trade.trailing_zero_coefficient` | 0.000015700 | FAIL |
| `bound:RiskPolicy.risk_per_trade.negative_adjusted` | 0.000014700 | FAIL |
| `bound:RiskPolicy.daily_loss_limit.coefficient` | 0.000014600 | FAIL |
| `bound:RiskPolicy.daily_loss_limit.trailing_zero_coefficient` | 0.000013400 | FAIL |
| `bound:RiskPolicy.daily_loss_limit.negative_adjusted` | 0.000015300 | FAIL |
| `bound:RiskPolicy.experiment_loss_limit.coefficient` | 0.000015300 | FAIL |
| `bound:RiskPolicy.experiment_loss_limit.trailing_zero_coefficient` | 0.000015000 | FAIL |
| `bound:RiskPolicy.experiment_loss_limit.negative_adjusted` | 0.000014100 | FAIL |
| `bound:size_position.cost_per_lot.coefficient` | 0.000081200 | FAIL |
| `bound:size_position.cost_per_lot.trailing_zero_coefficient` | 0.000064900 | FAIL |
| `bound:size_position.cost_per_lot.negative_adjusted` | 0.153747100 | FAIL |
| `bound:size_position.cost_per_lot.positive_adjusted` | 0.146173800 | FAIL |
| `bound:check_entry.cost_per_lot.coefficient` | 0.000002300 | FAIL |
| `bound:check_entry.cost_per_lot.trailing_zero_coefficient` | 0.000002400 | FAIL |
| `bound:check_entry.cost_per_lot.negative_adjusted` | 0.000002500 | FAIL |
| `bound:check_entry.cost_per_lot.positive_adjusted` | 0.000002300 | FAIL |
| `bound:EntryRequest.lots.coefficient` | 0.000005800 | FAIL |
| `bound:EntryRequest.lots.trailing_zero_coefficient` | 0.000005300 | FAIL |
| `bound:EntryRequest.lots.negative_adjusted` | 0.000005300 | FAIL |
| `bound:EntryRequest.lots.positive_adjusted` | 0.000005400 | FAIL |
| `bound:SizeDecision.lots.coefficient` | 0.000005800 | FAIL |
| `bound:SizeDecision.lots.trailing_zero_coefficient` | 0.000005700 | FAIL |
| `bound:SizeDecision.lots.negative_adjusted` | 0.000006000 | FAIL |
| `bound:SizeDecision.lots.positive_adjusted` | 0.000005000 | FAIL |
| `bound:SizeDecision.risk_money.coefficient` | 0.000005000 | FAIL |
| `bound:SizeDecision.risk_money.trailing_zero_coefficient` | 0.000005900 | FAIL |
| `bound:SizeDecision.risk_money.negative_adjusted` | 0.000005100 | FAIL |
| `bound:SizeDecision.risk_money.positive_adjusted` | 0.000005000 | FAIL |
| `bound:SizeDecision.risk_per_lot.coefficient` | 0.000005200 | FAIL |
| `bound:SizeDecision.risk_per_lot.trailing_zero_coefficient` | 0.000004900 | FAIL |
| `bound:SizeDecision.risk_per_lot.negative_adjusted` | 0.000003900 | FAIL |
| `bound:SizeDecision.risk_per_lot.positive_adjusted` | 0.000004600 | FAIL |
| `bound:SizeDecision.actual_risk.coefficient` | 0.000004800 | FAIL |
| `bound:SizeDecision.actual_risk.trailing_zero_coefficient` | 0.000005200 | FAIL |
| `bound:SizeDecision.actual_risk.negative_adjusted` | 0.000004900 | FAIL |
| `bound:SizeDecision.actual_risk.positive_adjusted` | 0.000004600 | FAIL |
| `bound:size_position.model.contract_size.coefficient` | 0.000070700 | FAIL |
| `bound:size_position.model.contract_size.trailing_zero_coefficient` | 0.000069900 | FAIL |
| `bound:size_position.model.contract_size.negative_adjusted` | 0.149368000 | PASS |
| `bound:size_position.model.contract_size.positive_adjusted` | 0.144908500 | PASS |
| `bound:size_position.model.volume_min.coefficient` | 0.000065600 | FAIL |
| `bound:size_position.model.volume_min.trailing_zero_coefficient` | 0.000059900 | FAIL |
| `bound:size_position.model.volume_min.negative_adjusted` | 0.142145500 | FAIL |
| `bound:size_position.model.volume_step.coefficient` | 0.000075000 | FAIL |
| `bound:size_position.model.volume_step.trailing_zero_coefficient` | 0.000067600 | FAIL |
| `bound:size_position.model.volume_step.negative_adjusted` | unfinished after join(timeout=10) | FAIL |
| `bound:size_position.model.volume_step.positive_adjusted` | 0.394705900 | FAIL |
| `bound:size_position.model.volume_max.coefficient` | 0.000145200 | FAIL |
| `bound:size_position.model.volume_max.trailing_zero_coefficient` | 0.000121800 | FAIL |
| `bound:size_position.model.volume_max.positive_adjusted` | 0.288414100 | FAIL |
| `bound:check_entry.model.contract_size.coefficient` | 0.000004300 | FAIL |
| `bound:check_entry.model.contract_size.trailing_zero_coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.model.contract_size.negative_adjusted` | 0.000004000 | FAIL |
| `bound:check_entry.model.contract_size.positive_adjusted` | 0.000003900 | FAIL |
| `bound:check_entry.model.volume_min.coefficient` | 0.000003800 | FAIL |
| `bound:check_entry.model.volume_min.trailing_zero_coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.model.volume_min.negative_adjusted` | 0.000004500 | FAIL |
| `bound:check_entry.model.volume_step.coefficient` | 0.000003600 | FAIL |
| `bound:check_entry.model.volume_step.trailing_zero_coefficient` | 0.000004300 | FAIL |
| `bound:check_entry.model.volume_step.negative_adjusted` | 0.000004300 | FAIL |
| `bound:check_entry.model.volume_step.positive_adjusted` | 0.000003800 | FAIL |
| `bound:check_entry.model.volume_max.coefficient` | 0.000004100 | FAIL |
| `bound:check_entry.model.volume_max.trailing_zero_coefficient` | 0.000003900 | FAIL |
| `bound:check_entry.model.volume_max.positive_adjusted` | 0.000003900 | FAIL |
| `bound:check_entry.request.lots.coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.request.lots.trailing_zero_coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.request.lots.negative_adjusted` | 0.000003900 | FAIL |
| `bound:check_entry.request.lots.positive_adjusted` | 0.000003900 | FAIL |
| `bound:check_entry.request.entry_price.coefficient` | 0.000003600 | FAIL |
| `bound:check_entry.request.entry_price.trailing_zero_coefficient` | 0.000003900 | FAIL |
| `bound:check_entry.request.entry_price.negative_adjusted` | 0.000004700 | FAIL |
| `bound:check_entry.request.entry_price.positive_adjusted` | 0.000004300 | FAIL |
| `bound:check_entry.request.stop_loss.coefficient` | 0.000003900 | FAIL |
| `bound:check_entry.request.stop_loss.trailing_zero_coefficient` | 0.000004600 | FAIL |
| `bound:check_entry.request.stop_loss.negative_adjusted` | 0.000003900 | FAIL |
| `bound:check_entry.request.stop_loss.positive_adjusted` | 0.000003600 | FAIL |
| `bound:check_entry.state.day_start_equity.coefficient` | 0.000003900 | FAIL |
| `bound:check_entry.state.day_start_equity.trailing_zero_coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.state.day_start_equity.negative_adjusted` | 0.000003900 | FAIL |
| `bound:check_entry.state.day_start_equity.positive_adjusted` | 0.000003700 | FAIL |
| `bound:check_entry.state.experiment_start_equity.coefficient` | 0.000003800 | FAIL |
| `bound:check_entry.state.experiment_start_equity.trailing_zero_coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.state.experiment_start_equity.negative_adjusted` | 0.000003600 | FAIL |
| `bound:check_entry.state.experiment_start_equity.positive_adjusted` | 0.000003700 | FAIL |
| `bound:update_equity.state.day_start_equity.coefficient` | 0.000173900 | FAIL |
| `bound:update_equity.state.day_start_equity.trailing_zero_coefficient` | 0.000130700 | FAIL |
| `bound:update_equity.state.day_start_equity.negative_adjusted` | 1.267520800 | FAIL |
| `bound:update_equity.state.day_start_equity.positive_adjusted` | 0.522449800 | FAIL |
| `bound:update_equity.state.experiment_start_equity.coefficient` | 0.000206800 | FAIL |
| `bound:update_equity.state.experiment_start_equity.trailing_zero_coefficient` | 0.000156100 | FAIL |
| `bound:update_equity.state.experiment_start_equity.negative_adjusted` | 1.233271800 | FAIL |
| `bound:update_equity.state.experiment_start_equity.positive_adjusted` | 0.498941600 | FAIL |
| `bound:restart_experiment.state.day_start_equity.coefficient` | 0.000017000 | FAIL |
| `bound:restart_experiment.state.day_start_equity.trailing_zero_coefficient` | 0.000017600 | FAIL |
| `bound:restart_experiment.state.day_start_equity.negative_adjusted` | 0.000017300 | FAIL |
| `bound:restart_experiment.state.day_start_equity.positive_adjusted` | 0.000020600 | FAIL |
| `bound:restart_experiment.state.experiment_start_equity.coefficient` | 0.000019600 | FAIL |
| `bound:restart_experiment.state.experiment_start_equity.trailing_zero_coefficient` | 0.000015800 | FAIL |
| `bound:restart_experiment.state.experiment_start_equity.negative_adjusted` | 0.000016000 | FAIL |
| `bound:restart_experiment.state.experiment_start_equity.positive_adjusted` | 0.000016100 | FAIL |
| `bound:HaltState.policy.risk_per_trade.coefficient` | 0.000007300 | FAIL |
| `bound:HaltState.policy.risk_per_trade.trailing_zero_coefficient` | 0.000008300 | FAIL |
| `bound:HaltState.policy.risk_per_trade.negative_adjusted` | 0.000007800 | FAIL |
| `bound:HaltState.policy.daily_loss_limit.coefficient` | 0.000009600 | FAIL |
| `bound:HaltState.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000008200 | FAIL |
| `bound:HaltState.policy.daily_loss_limit.negative_adjusted` | 0.000008300 | FAIL |
| `bound:HaltState.policy.experiment_loss_limit.coefficient` | 0.000009000 | FAIL |
| `bound:HaltState.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000008400 | FAIL |
| `bound:HaltState.policy.experiment_loss_limit.negative_adjusted` | 0.000009900 | FAIL |
| `bound:size_position.policy.risk_per_trade.coefficient` | 0.000136200 | FAIL |
| `bound:size_position.policy.risk_per_trade.trailing_zero_coefficient` | 0.000113600 | FAIL |
| `bound:size_position.policy.risk_per_trade.negative_adjusted` | 0.249680600 | FAIL |
| `bound:size_position.policy.daily_loss_limit.coefficient` | 0.000073500 | FAIL |
| `bound:size_position.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000070200 | FAIL |
| `bound:size_position.policy.daily_loss_limit.negative_adjusted` | 0.000076400 | FAIL |
| `bound:size_position.policy.experiment_loss_limit.coefficient` | 0.000079400 | FAIL |
| `bound:size_position.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000071100 | FAIL |
| `bound:size_position.policy.experiment_loss_limit.negative_adjusted` | 0.000077300 | FAIL |
| `bound:start_experiment.policy.risk_per_trade.coefficient` | 0.000013600 | FAIL |
| `bound:start_experiment.policy.risk_per_trade.trailing_zero_coefficient` | 0.000011100 | FAIL |
| `bound:start_experiment.policy.risk_per_trade.negative_adjusted` | 0.000011400 | FAIL |
| `bound:start_experiment.policy.daily_loss_limit.coefficient` | 0.000013400 | FAIL |
| `bound:start_experiment.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000011100 | FAIL |
| `bound:start_experiment.policy.daily_loss_limit.negative_adjusted` | 0.000012800 | FAIL |
| `bound:start_experiment.policy.experiment_loss_limit.coefficient` | 0.000012600 | FAIL |
| `bound:start_experiment.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000011200 | FAIL |
| `bound:start_experiment.policy.experiment_loss_limit.negative_adjusted` | 0.000012600 | FAIL |
| `bound:unknowns.policy.risk_per_trade.coefficient` | 0.000008300 | FAIL |
| `bound:unknowns.policy.risk_per_trade.trailing_zero_coefficient` | 0.000007900 | FAIL |
| `bound:unknowns.policy.risk_per_trade.negative_adjusted` | 0.000006500 | FAIL |
| `bound:unknowns.policy.daily_loss_limit.coefficient` | 0.000006800 | FAIL |
| `bound:unknowns.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000035700 | FAIL |
| `bound:unknowns.policy.daily_loss_limit.negative_adjusted` | 0.000006500 | FAIL |
| `bound:unknowns.policy.experiment_loss_limit.coefficient` | 0.000006500 | FAIL |
| `bound:unknowns.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000006500 | FAIL |
| `bound:unknowns.policy.experiment_loss_limit.negative_adjusted` | 0.000006100 | FAIL |
| `bound:check_entry.state.policy.risk_per_trade.coefficient` | 0.000004300 | FAIL |
| `bound:check_entry.state.policy.risk_per_trade.trailing_zero_coefficient` | 0.000004000 | FAIL |
| `bound:check_entry.state.policy.risk_per_trade.negative_adjusted` | 0.000004400 | FAIL |
| `bound:check_entry.state.policy.daily_loss_limit.coefficient` | 0.000004100 | FAIL |
| `bound:check_entry.state.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000004200 | FAIL |
| `bound:check_entry.state.policy.daily_loss_limit.negative_adjusted` | 0.000004500 | FAIL |
| `bound:check_entry.state.policy.experiment_loss_limit.coefficient` | 0.000003700 | FAIL |
| `bound:check_entry.state.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000004000 | FAIL |
| `bound:check_entry.state.policy.experiment_loss_limit.negative_adjusted` | 0.000003900 | FAIL |
| `bound:update_equity.state.policy.risk_per_trade.coefficient` | 0.000038400 | FAIL |
| `bound:update_equity.state.policy.risk_per_trade.trailing_zero_coefficient` | 0.000041600 | FAIL |
| `bound:update_equity.state.policy.risk_per_trade.negative_adjusted` | 0.000039600 | FAIL |
| `bound:update_equity.state.policy.daily_loss_limit.coefficient` | 0.000105400 | FAIL |
| `bound:update_equity.state.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000089400 | FAIL |
| `bound:update_equity.state.policy.daily_loss_limit.negative_adjusted` | 0.320434800 | FAIL |
| `bound:update_equity.state.policy.experiment_loss_limit.coefficient` | 0.000106500 | FAIL |
| `bound:update_equity.state.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000099400 | FAIL |
| `bound:update_equity.state.policy.experiment_loss_limit.negative_adjusted` | 0.408447600 | FAIL |
| `bound:restart_experiment.state.policy.risk_per_trade.coefficient` | 0.000018800 | FAIL |
| `bound:restart_experiment.state.policy.risk_per_trade.trailing_zero_coefficient` | 0.000016600 | FAIL |
| `bound:restart_experiment.state.policy.risk_per_trade.negative_adjusted` | 0.000017100 | FAIL |
| `bound:restart_experiment.state.policy.daily_loss_limit.coefficient` | 0.000017200 | FAIL |
| `bound:restart_experiment.state.policy.daily_loss_limit.trailing_zero_coefficient` | 0.000016800 | FAIL |
| `bound:restart_experiment.state.policy.daily_loss_limit.negative_adjusted` | 0.000016400 | FAIL |
| `bound:restart_experiment.state.policy.experiment_loss_limit.coefficient` | 0.000016000 | FAIL |
| `bound:restart_experiment.state.policy.experiment_loss_limit.trailing_zero_coefficient` | 0.000015900 | FAIL |
| `bound:restart_experiment.state.policy.experiment_loss_limit.negative_adjusted` | 0.000016000 | FAIL |
| `branch:request-lots-RiskError-halted` | 0.000004100 | FAIL |
| `branch:request-lots-RiskError-missing_stop` | 0.000004200 | FAIL |
| `branch:request-lots-RiskError-wrong_side_stop` | 0.000004700 | FAIL |
| `branch:request-lots-RiskError-stale` | 0.000004600 | FAIL |
| `branch:request-entry_price-BadStop-halted` | 0.000004800 | FAIL |
| `branch:request-entry_price-BadStop-missing_stop` | 0.000004900 | FAIL |
| `branch:request-entry_price-BadStop-wrong_side_stop` | 0.000004800 | FAIL |
| `branch:request-entry_price-BadStop-stale` | 0.000002400 | FAIL |
| `branch:request-stop_loss-BadStop-halted` | 0.000002400 | FAIL |
| `branch:request-stop_loss-BadStop-missing_stop` | 0.000002400 | FAIL |
| `branch:request-stop_loss-BadStop-wrong_side_stop` | 0.000004600 | FAIL |
| `branch:request-stop_loss-BadStop-stale` | 0.000005100 | FAIL |
| `branch:state-day_start_equity-BadEquity-halted` | 0.000004400 | FAIL |
| `branch:state-day_start_equity-BadEquity-missing_stop` | 0.000004500 | FAIL |
| `branch:state-day_start_equity-BadEquity-wrong_side_stop` | 0.000004800 | FAIL |
| `branch:state-day_start_equity-BadEquity-stale` | 0.000004300 | FAIL |
| `branch:state-experiment_start_equity-BadEquity-halted` | 0.000004500 | FAIL |
| `branch:state-experiment_start_equity-BadEquity-missing_stop` | 0.000004300 | FAIL |
| `branch:state-experiment_start_equity-BadEquity-wrong_side_stop` | 0.000004600 | FAIL |
| `branch:state-experiment_start_equity-BadEquity-stale` | 0.000004400 | FAIL |
| `branch:state-policy.risk_per_trade-BadPolicy-halted` | 0.000004100 | FAIL |
| `branch:state-policy.risk_per_trade-BadPolicy-missing_stop` | 0.000004600 | FAIL |
| `branch:state-policy.risk_per_trade-BadPolicy-wrong_side_stop` | 0.000005400 | FAIL |
| `branch:state-policy.risk_per_trade-BadPolicy-stale` | 0.000004500 | FAIL |

### Red flags, limits and next action

The main-based red-flag scan reports two inherited groups: intentional negative
unit-test type-suppression comments and documentation quoting them; lint-suppression
words in existing documentation. No new suppression was added. Secret and
order/account-mutation groups are empty; no tests are deleted or renamed.
Control-name heuristics list inherited locked files and policy/review filenames.
The scan does not inspect the ignored proposal, so the two applied files were
also explicitly checked for skip/xfail/suppression markers: none. The worker's
BaseException handler transports every error to a failing assertion; it does
not swallow unexpected exceptions.

Not tested or claimed: v1.3 positive runtime acceptance beyond the recorded
passes; a completed isolated extreme-equity case; implementation mutation or
security certification; CI, owner demonstration, merge/deployment; broker,
terminal, account, market data, research or holdout operations. The current old
signature prevents many gate tests from reaching the behavior they will exercise
once v1.3 is implemented. No implementation fix was attempted.

Separate follow-ups retained from round5: tests-r1 F5 architecture-checker gap;
E1 F7 same-account/same-Thai-day start prohibition; L1 authenticated clearer and
policy digest; L2 journal-only state restoration and constructor/replace/setattr
restrictions; L3 real tick/model/exposure/send binding; L4 MT5 current-stop binding;
F6 update_equity before entry and pass the same Thai day. None belongs in this
pure-module test patch. No same-day-history check was added to start_experiment.

Delivery state: test proposal implemented; patch applicability, bytes, oracles
and expected-red behavior verified locally with the limitations above. CORE-003
v1.3 acceptance is FAIL, not verified/merged/deployed. Next action: Claude applies
via D-006, verifies both hash pairs, obtains fresh-session review, then commits.

## Implementation v1.3 (Claude Code), 2026-10-22

Order followed since the first implementation (`ab23325`): security-reviewer pre-review
(`docs/reviews/CORE-003-security-pre-r1.md`, `737632b`) → fixes F1 `e1a095b` (exact types),
F2/F5 `d7a312c` (exact huge lots, provenance read once), F4 `0c00d92` (revalidation at use),
each with a regression that failed before and passed after → owner chose F3 bound, F6 day,
F7 E1-only → contract v1.3 (`07856b9`, `e414246`) → Codex contract reviews r4, r5 (F13, F14
closed, `fcf77c5`) → Codex tests r2 patch applied via D-006 (both hash pairs matched, reverse
check passed), fresh-session review `docs/reviews/CORE-003-tests-r2.md` (ready to commit red),
committed red at `81322d9` → v1.3 implementation in the commit that adds this section.

- `policy.py`: `finite_bounded` (finite, at most 1,000 coefficient digits, non-zero
  `|adjusted()| <= 1_100_000`, checked before any rational conversion, the slot's own error,
  value not echoed); `exact_reduce`; `validate_policy` re-runs every `RiskPolicy` field check
  (the constructor and every use share `_check_policy`), so a policy changed with
  `object.__setattr__` after construction is refused wherever it is used.
- `sizing.py`: `require_policy` = `validate_policy`; every Decimal read is bounded
  (`cost_per_lot` → BadPolicy, the four model fields and SizeDecision fields → RiskError);
  `grid_lots` removes trailing zeros exactly when a huge step count would exceed 1,000 digits.
- `gate.py`: `check_entry(request, equity, day, state, model, cost_per_lot=Decimal("0"))`;
  every argument and every request/state field (nested policy included) is validated before
  any reason is collected; `day < state.day` → TimeReversal, `day > state.day` → reason
  `stale_state`, other reasons evaluated as usual.
- `halts.py`: unchanged; it gets the bound and the policy revalidation through
  `positive_decimal` and `require_policy`.
- `tests/unit/risk/test_risk_unit.py`: 22 tests; the 23 v1.2 `check_entry` call sites go
  through `_gate`, which passes `state.day`; new tests for `stale_state`/TimeReversal and for
  oversized numbers.
- A scratch dry run of the r2 locked tests (read in place from a scratch working directory)
  first failed 151 rows, all on a policy changed after construction (round 5 item 5 and
  tests-r2 F3); `validate_policy` closed them.

Checks (2026-10-22 +07, Windows 11, CPython 3.12.15 via uv):

| Command | Result | Time |
|---|---|---|
| `uv run --offline pytest tests -q -p no:cacheprovider` (under an outer `timeout 300`) | PASS: 651 passed, 0 skipped, 2.68 s, no deselect | 10:02:46 |
| `uv run --offline pytest "tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac06_extreme_equity_rejection_deadline" -q -s -p no:cacheprovider` | PASS: BadEquity after 0.000036 s | 10:03 |
| `-k oversized -s` timing lines | 236 timed rejections, slowest 0.000366 s | 10:03 |
| `bash scripts/controls/red-flags.sh origin/main` | exit 0; 2 groups: one more intentional `type: ignore[arg-type]` (negative unit test passing a str day) plus prose; lint words in prose | 10:04 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL as expected: the 3 Codex-authored locked test files need the PR label | 10:04 |
| `git diff --check`; `git diff 81322d9 -- tests/acceptance tests/golden tests/architecture` | PASS; empty | 10:04 |

Open for the owner (from tests-r2): F1 Medium, the contract's daemon-thread watchdog cannot
stop a regression stuck in one GIL-holding call (the suite then hangs instead of failing;
it never passes falsely); F3 Low, confirm in the contract that a policy changed after
construction is revalidated at every entry point (the implementation already does).
Codex follow-ups: tests-r2 F2, F4-F6; tests-r1 F5 architecture-checker gap.

Please look hard at (Codex cross-agent review, Tier High):
- Any input that reaches `Fraction(...)`, `as_integer_ratio` or a display computation
  without passing `finite_bounded` first.
- Any path where a refusal reason is collected before every argument and field is validated.
- Any way to obtain `allowed=True` for a state not rolled to the request day, at or beyond a
  loss threshold, above the sized lots, or with a widened or missing stop.

## Findings response (Claude Code), review r1

Review `docs/reviews/CORE-003-r1.md` (Codex, HEAD `60dfbfd`, committed `8d4e30b`). One commit per
finding; each regression is an implementer unit test that failed before the fix and passes after.

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F1 Medium | Accept | `1c804a6` | `require_model` re-checks the CostModel construction domain at every use (contract_size, volume_step, volume_min > 0; volume_max >= volume_min) → RiskError. `uv run --offline pytest tests/unit/risk -q -p no:cacheprovider -k corrupted_model` → before: FAIL `DID NOT RAISE RiskError`; after: 1 passed. Covers 7 corrupted models through size_position, the gate, and the gate on a halted state. |
| F2 Medium | Accept | `0bf8311` | `exact_sum` skips zero terms (adding zero changes no exact sum); zero stays valid with any exponent, no new bound. `-k zero_budget` → before: FAIL `MemoryError` at `policy.py:123`; after: 1 passed (`-0`, `0E-999999999999999999`, `-0E-999999999999999999`, `0E+999999999999999999` equal the plain-zero decision; the gate allows). |
| F3 Low | Accept | `b959fea` | The two count messages no longer echo the int; no int bound added, conversion limit untouched. `-k huge_negative` → before: FAIL `ValueError: Exceeds the limit (4300 digits)` at `gate.py:87`; after: 1 passed (construction and use-time; ordinary -1 and 0 keep their errors). |

Full suite after the three fixes: `uv run --offline pytest tests -q -p no:cacheprovider` → 654 passed,
0 skipped (2.68 s). Locked tests untouched since `81322d9`.

Contract v1.4 (`5d939a3`) writes down the owner's tests-r2 choices (F1 faulthandler in the timing
harness, F3 policy revalidation at every use), the model domain from r1 F1, and the Codex budget of
12 runs. For the reviewer's round 2: re-check F1–F3 only, plus whether the code matches the v1.4
table rows.

## Findings response (Claude Code), security pre-review r2

Review `docs/reviews/CORE-003-security-pre-r2.md` (security-reviewer subagent, committed `cbf9399`).
No Critical or High finding. Owner decisions 2026-10-22 10:5x for F10, F12, F13.

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F9 Low | Accept | `2798532` | The provenance read is the only caller code validation can run, so it now runs once and first: `_check_policy` snapshots provenance before any other field and `unknowns` uses that snapshot; `validate_state` validates the policy first and pins `state.policy` by identity; `check_entry` validates the state before the request and `size_position` the policy before the model; `restart_experiment` rolls the day with an internal `_roll` instead of re-validating through `update_equity`. `-k caller_code` → before: each of 4 cases failed separately (allowed / plain ValueError / allowed with risk_per_trade 5 / swapped policy returned); after: 1 passed. |
| F10 Low | Accept as a limitation (owner) | `9ad8095` | Comment corrected (refusal of oversized values is fast; in-bound extreme model grids can take tens of seconds). Contract v1.5 `5605ca8` binds it to E1 L3: the model only from MT5 `symbol_info`. No code change. |
| F11 Low | Accept | `b9f0396` | `finite_bounded` checks `|adjusted()|` first, then counts digits in C (`plus()` in a precision-1000 context traps `Rounded` when there are more than 1,000 digits, trailing zeros included). `-k huge_coefficient` ("0." + 3×10⁷ digits, < 0.05 s) → before: FAIL 0.172 s (fix stashed); after: 1 passed. Probes: "0." + 2×10⁸ digits → BadEquity in 0.018 s; a 2×10⁸-digit integer → 0.0001 s. |
| F12 Low (question) | Answered in the contract (owner) | `5605ca8` | v1.5 error-table row: `size_position` raises RiskError when exact lots need more than 1,000 digits; `check_entry` unaffected. Matches current behaviour; no code change. |
| F13 Low (question) | E1 obligation (owner) | `5605ca8` | v1.5 adds E1 obligation L5: baseline equity from the MT5 account equity field, raw value journaled, halt on mismatch or unknown. No change in `sochron.risk`. |

Full suite after these fixes: `uv run --offline pytest tests -q -p no:cacheprovider` → 656 passed,
0 skipped. Locked tests untouched since `81322d9`.

## Tests r3 for contract v1.4 (Codex, 2026-10-22)

This requested heading also covers the owner's contract **v1.5** decisions. Base HEAD:
`e510726a244eeea9efb7a3d75272fec4138ab557`, branch `feat/CORE-003-risk`.
The working tree and index were clean at entry. This headless invocation explicitly authorized
reading the listed reviews/handoff, amending the locked tests as a proposal, and testing against
the existing implementation. Those instructions supersede the skill's original red-test-only
and no-handoff restrictions. No implementation source or task source diff was inspected. One
supporting agent checked fixture design read-only; it did not edit files or provide a release review.

**Outcome: proposal complete; disk-applied-copy verification BLOCKED.** The patch was not applied
to the repository. A full-suite run using the proposed test bytes applied in memory passed:
**`723 passed in 3.22s`**, exit 0, no skips or deselections. This is supplemental evidence, not a
claim that the requested ordinary pytest run on patched files on disk was completed.

### D-006 artifact and expected LF bytes

Regular patch: `docs/proposals/CORE-003-tests-r3.patch` (directly in proposals, ignored by Git).
Patch SHA256: `bea1632d3be31e57b6d7561bdbe446b69e9453b6e9a89c5c0de0aa0d729cf7fe`.
It changes only the following two files: acceptance +222/-4; golden +24/-1.

| File | Expected post-apply SHA256 (LF) | Expected Git blob |
|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `d362fff230678f01c1705bfada9b5cd6eadf05b232248235c2a42ba237684119` | `2e3d154abce9042f7521393e7a27b24875914bb8` |
| `tests/golden/CORE-003/risk_cases.py` | `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83` | `d4800f296435d10344eb68a468f6ab132e1fbaf2` |

These are **expected** hashes derived twice: from the proposed bytes and from independently
applying the unified hunks in memory to `git show HEAD:<path>` bytes. Every removed/context line
was checked. `git hash-object --path=<path> --stdin` from the repository matched both blobs,
using the repository's attributes context (`*.py text eol=lf`). Both candidate files are ASCII,
contain LF only, and end with exactly one newline. Post-apply hashes of actual patched files on
disk remain BLOCKED; do not describe the table as a completed disk hash verification.

Standalone `git apply --check docs/proposals/CORE-003-tests-r3.patch`: **PASS**, exit 0, no output,
2026-10-22 **10:51:01 +07** (time captured immediately after the command), at the HEAD above.

### Changes by finding and acceptance criterion

| Finding / rule | Change and evidence | AC |
|---|---|---|
| tests-r2 F1 | Arm `faulthandler.dump_traceback_later(20, exit=True)` before `worker.start()`. Always cancel in `finally` after the join attempt. Preserve the daemon worker, `join(timeout=10)`, alive check, exact exception, context preservation, public-call-only timer and strict `< 1.000` limit. | AC-06, AC-07 |
| tests-r2 F2 | Only the restart row replaces an empty `halt_clearers` with `("owner", "owner")`: owner stays authorized, so the isolated defect is BadPolicy. Empty-list coverage at the other entry points remains. | AC-03, AC-06 |
| tests-r2 F3 / v1.4 policy-use row | Keep all existing direct and nested policy revalidation rows. New huge-negative-count rows also exercise every named policy consumer. | AC-06 |
| tests-r2 F4 | Compensate oversized `contract_size` exponents using in-bound distances/prices. Negative exponent gives exact per-lot risk .1; positive exponent gives 10. Both displays are normal, so a missing model bound cannot pass by raising the display-range RiskError. Keep both signs through sizing and gate in the existing timed matrix. Golden comments derive each fixture. | AC-01, AC-04, AC-06 |
| tests-r2 F5 | `_reject` now asserts the exact expected exception type. This tightens the base-RiskError domain, result-consistency, stop-side and use-time rows, and consistently applies the same rule to the other explicitly named exceptions. | AC-05, AC-06 |
| tests-r2 F6 | Add 1,000-digit equity .1 with trailing zeros to the sizing golden rows; add equity 1 with trailing zeros through update/restart; add a 1,000-digit repeating-decimal budget through the gate, with allowed .02 and refused .03 lots. No deadline is imposed on in-bound inputs. | AC-01, AC-02, AC-03, AC-04, AC-06 |
| implementation r1 F1 / v1.4 model domain | Seven mutations on fresh models: contract_size/volume_step/volume_min zero or negative, and volume_max below min. Exact RiskError through sizing and gate, including halted, missing-stop, wrong-side-stop and stale branches (42 rows). | AC-01, AC-04, AC-06 |
| implementation r1 F2 | Positive and negative zero with exponent -999999999999999999 produce the ordinary zero-budget sizing tuple and an allowed gate decision under hostile caller context. | AC-01, AC-04, AC-06 |
| implementation r1 F3 | Construct `-(10**5000)` inside the test body, avoiding pytest ID conversion. Require exact RiskError for request counts and BadPolicy for policy counts, at construction and at use (10 rows). | AC-06 |
| security pre-r2 F9 | Plant a Mapping after construction. Its keys callback changes side, swaps state.policy to an invalid rate5 policy, or sets lots to NaN. Raw and proxy-wrapped Mappings must never yield allowed=True or a non-RiskError exception. A separate restart callback swaps to a valid but different policy on reread; the returned state must retain the original validated policy by identity and preserve daily halt/baseline (8 rows total). | AC-03, AC-04, AC-06 |
| security pre-r2 F11 | Prebuild `Decimal("0." + "7" * 30_000_000)`; adjusted exponent is -1. Require exact BadEquity under the unchanged `< 1.000 s` harness, excluding construction/import/setup. | AC-06 |
| security pre-r2 F12 / v1.5 | Hand-computed step `1 + 1E-999` has 1,000 digits. With equity1E8, distance7 and max200, selected lots=199*step needs 1,002 digits: exact RiskError from sizing. Gate still allows 9*step (1,000 digits) and refuses 200 with both lots_exceed_sized and lots_not_on_grid. | AC-01, AC-04, AC-06 |

### Verification, limits and exact results

All checks refer to base `e510726a244eeea9efb7a3d75272fec4138ab557` plus the proposal hash above.
Runtime observed through `uv run --offline`: CPython **3.12.15**, pytest **9.1.1**, Windows.

| Command / procedure | Result | Time (2026-10-22 +07) |
|---|---|---|
| `git diff fcf77c5..HEAD -- docs/contracts/CORE-003-risk.md` | PASS; read first, including v1.4 and v1.5 owner decisions | Session start; exact timestamp not captured |
| `git apply --check docs/proposals/CORE-003-tests-r3.patch` (standalone) | PASS; exit 0, no output | 10:51:01 |
| `uv run --offline python -B -` with full-suite in-memory proposal collector; internally `pytest.main(['tests', '-q', '-p', 'no:cacheprovider', '--tb=short'], plugins=[ProposalOverlay()])` | PASS; exact summary `723 passed in 3.22s`, exit 0; 0 skipped/deselected | 10:51:47-10:51:50 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; 2 inherited pattern groups, explained below | Completed by 10:52:38 |
| `git apply --numstat docs/proposals/CORE-003-tests-r3.patch` | PASS; only the two requested files, +222/-4 and +24/-1 | Completed by 10:52:38 |
| `git diff --check` and `git diff --cached --name-only` | PASS; no whitespace errors; index empty | Completed by 10:52:38 |
| `uv run --offline python -B -`: apply hunks in memory, AST/golden integrity, LF/ASCII checks, SHA256, `git hash-object --path=<path> --stdin` | PASS; all 69 original assertions retained (88 now), every original test function retained, every original golden row retained; hashes match table; no disabled tests or placeholders | 10:53:25 |
| Ordinary `uv run --offline pytest tests -q -p no:cacheprovider` against physically patched scratch copies | BLOCKED, not run; see filesystem failure below | Not run |

In-memory suite method: copy 31 tracked HEAD files (`src/`, `tests/`, `.gitattributes`,
`.python-version`, `pyproject.toml`, `uv.lock`) into the scratch `applied` directory; validate every
patch context/removal against HEAD; keep proposed source strings in memory. A public pytest
collection hook returns a `pytest.Module` subclass for only the CORE-003 acceptance module,
compiling those proposed bytes with the scratch path as `__file__`. A scoped `runpy.run_path`
overlay supplies the proposed golden dictionary for only its exact scratch path. All other tests,
including architecture, use the unmodified HEAD copies; current HEAD src is imported normally.
Assertions execute normally (the proposed module has no pytest assertion rewriting). Bytecode and
pytest cache writing are disabled. No production code, pytest config or dependency was changed.

Filesystem failure: the `apply_patch` tool could not read the scratch target and stopped before
editing anything:

```text
apply_patch verification failed: Failed to read file to update
C:\Users\MSI\AppData\Local\Temp\sochron-core003-r3-n_estqmk\amended\tests\acceptance\CORE-003\test_risk_acceptance.py:
Access is denied. (os error 5)
```

No alternate tool was used to edit or apply to that denied target. Proposal construction and
in-memory verification continued within the authorized scope. The scratch baseline/amended/applied
files remain unpatched. The requested disk application, post-apply disk hashes and ordinary full-suite
run on that disk state are therefore BLOCKED, despite the passing supplemental in-memory suite.
`rg` was also unavailable (`The term 'rg' is not recognized`); read-only PowerShell searches supplied
the file discovery. Neither environment failure is counted as passing evidence.

| AC | Status | Evidence scope |
|---|---|---|
| AC-01 | PASS | In-memory suite: sizing golden rows, zero budget and exact-lots overflow/gate agreement |
| AC-02 | PASS | In-memory suite: all existing halt rows plus inclusive-coefficient arithmetic |
| AC-03 | PASS | In-memory suite: restart error isolation, arithmetic edge and validated policy identity |
| AC-04 | PASS | In-memory suite: existing gate rows plus model-domain, callback and F12 decisions |
| AC-05 | PASS | In-memory suite: original stop-change assertions retained; exact error tightening passes |
| AC-06 | PASS | In-memory suite: all old matrices retained and new bound/domain/type rows pass |
| AC-07 | BLOCKED | Full in-memory suite and unchanged architecture tests pass; required ordinary suite on physically patched copies remains unperformed |

No test failed in the executed suite. No module-level v1.4/v1.5 requirement was ambiguous for these
rows. F10 and F13 are explicitly E1 obligations: L3 truthful model sourcing from `symbol_info`, and
L5 terminal equity plus journal binding cannot be verified through these pure APIs. They are not
reported as covered. The 30M-digit F11 sample limits routine memory use; the old linear check may
still meet 1 second at this size. This is a deadline acceptance sample, not proof of detecting every
old F11 regression. The review's 200M-digit reproduction (~1.9 GiB old-path peak) was not repeated.
The watchdog's real process-exit-on-GIL-stall path and historical implementations were not run.

Red flags: the branch-wide scan includes inherited CORE-001/CORE-002/control changes because local
main is behind. The two groups are pre-existing negative-test type suppressions (7 costs, 2 risk)
and documentation quoting them, plus lint-suppression words in documentation. Secret, destructive,
order/account and placeholder groups are empty. The ignored proposal is outside that scanner's
Git diff; its proposed test bytes were checked separately for disabled tests, type/lint suppressions,
placeholders and trailing whitespace, with no hits. The new Mapping is an intentional adversarial
test fixture only. No new production fake, suppression or swallowed unexpected exception is added.

Repository locked-file SHA256 values remain unchanged:
- acceptance: `69cd888f057fbcc1365f41d3aaae448dfccb6caf1b94e945029d120fedfab373`
- golden: `68b34aced4943deda4ada60ed2d33872ba03ccebc8736fa29e38b5b64ec2e7c2`
- architecture: `259ac6d4a9c9b0dfd165f0936b092ca458bde033b453c4ffde3b44787933b195`

Only this append-only handoff and the regular proposal patch were written in the repository.
PROGRESS.md was not changed because this invocation explicitly forbids other files; this section
is the session checkpoint. Everything is unstaged; no commit, push, merge, deployment, terminal,
broker, market-data or credential action occurred.

**Next action (Claude, D-006):** apply the regular proposal patch as a standalone command, verify
both applied SHA256 values and Git blobs above under LF attributes, and run the ordinary full
suite to close the blocked disk evidence. Obtain a fresh-session review of the applied diff and
this handoff, then commit. This authoring session and its supporting fixture check do not replace
that review. Delivery state: **implemented as a proposal; verification incomplete; not applied,
committed, merged or deployed**.

## Application of tests r3 and findings response to review r2 (Claude Code)

Tests r3: patch SHA256 `bea1632d…` matched; standalone `git apply --check` and `git apply`; the
detector listed exactly the two target files; applied SHA256 and blobs matched the table above
(`d362fff2…`/`2e3d154a…`, `04c5e644…`/`d4800f29…`); `git apply -R --check` passed; full suite on disk
723 passed, 0 skipped (10:57); fresh-session review `docs/reviews/CORE-003-tests-r3.md` ready to
commit; committed `c2c365c`. Owner decisions on its findings (11:2x): F1, F3 → Codex patch r4; F2
accepted; F4 → contract v1.6; in-place mutation evidence accepted.

Review `docs/reviews/CORE-003-r2.md` (Codex, HEAD `c2c365c`) was written when the previous session
ended; the owner committed it as `82844d1` (message "ฟ"). It closes r1 F1–F3 and security F11, and
leaves two Low residuals of security F9. One commit per finding:

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F4 Low | Accept | `073ab70` | `_check_policy` requires every provenance key to be exactly `str` right after the single read, before any other field. `uv run --offline pytest tests/unit/risk -q -p no:cacheprovider -k exact_str_before` → before: FAIL `DID NOT RAISE TypeError` (the R4 key set risk_per_trade to 5 and the gate allowed 41.66 lots); after: 1 passed (gate, sizing, unknowns at use; construction with a str-subclass key and an int key). |
| F5 Low | Accept | `d7b45b5` | start/update/restart build the result with `_new_state` from values validated in this call, without a second provenance read; direct `HaltState(...)` still validates. `-k without_reading_the_policy` → before: FAIL `(False, Decimal('0.0001')) == (False, Decimal('0.0075'))`; after: 1 passed (update, restart, start). |

Full suite after both fixes: `uv run --offline pytest tests -q -p no:cacheprovider` → 725 passed,
0 skipped. Contract v1.6 (`a6fde90`) writes the behaviour down. For the reviewer's round 3: re-check
F4 and F5 only, and whether any other caller-code point remains after the first read.

## Tests r4 (Claude test author under the role swap, 2026-10-22)

Role: a fresh Claude Code session acting as the Codex test author under the owner's role swap
(PROGRESS.md, `34097d9`); not the implementer and not the reviewer. It followed
`.agents/skills/write-acceptance-tests/SKILL.md` as a plain procedure. Base HEAD
`34097d9c232a5b8e9dd46efee4a987ceb1307872`, branch `feat/CORE-003-risk`, contract v1.6. Read: the
contract (with `git diff c2c365c..HEAD`), `docs/reviews/CORE-003-tests-r3.md`, `docs/reviews/CORE-003-r2.md`,
the two locked CORE-003 test files and this handoff. Implementation source was not read; HEAD behaviour
was probed black-box only. Locked files were never edited or copied with `cp`: each was read with Read
and written to the session scratchpad with Write. Written in the repository: this section and the
ignored proposal patch. Nothing staged, committed or pushed.

**Outcome: proposal complete; all amended tests pass against HEAD.** Amended acceptance file: **708
passed** (650 kept + 58 new). Full suite with the amended file in place of the locked one: **783
passed**, 0 skipped.

### D-006 artifact and expected LF bytes

Regular patch: `docs/proposals/CORE-003-tests-r4.patch` (ignored by `.gitignore:10`).
Patch SHA256: `9d290dc9ab17b75c0098f51a894f4b50dccc155b2ebf65d3e33b30304285dc27`.
It changes one file: acceptance +260/-27 (`git apply --numstat`). The golden file and
`tests/architecture/` are unchanged and not in the patch.

| File | Expected post-apply SHA256 (LF) | Expected Git blob |
|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `fa1bde04706d177bb13a4da14e00751ff67c85816537e8417932e59d280c94df` | `d2ba11db5958d817c5830fc54a3eda5fa3e7ce35` |
| `tests/golden/CORE-003/risk_cases.py` (unchanged) | `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83` | `d4800f296435d10344eb68a468f6ab132e1fbaf2` |

Derivation: `diff -u` with `a/`/`b/` labels between the locked file and the scratch copy. A scratch
script applied every hunk in memory to the HEAD bytes, checking each context and removed line; the
result equals the scratch copy byte for byte. `git hash-object --path=tests/acceptance/CORE-003/test_risk_acceptance.py
<scratch copy>` gives the blob above, which matches a manual `sha1("blob <len>\0" + bytes)`. The amended
file is ASCII, LF only, with one trailing newline and no trailing spaces. The verbatim scratch copies first matched
the locked files (`d362fff2…`, `04c5e644…`).

Standalone `git apply --check docs/proposals/CORE-003-tests-r4.patch`: **PASS**, exit 0, no output,
completed by **19:43:15 +07** (`date` run right after it), at the HEAD above.

### Changes by finding

| Finding / rule | Change | AC |
|---|---|---|
| tests-r3 F1 (owner: fix) | `_HookMapping` runs its action from `keys()`, `__iter__`, `__getitem__` and `__len__`; `keys()` returns `KeysView(self)`. So the Mapping mixins (`items()`, `values()`, `get()`, `__contains__`, `__eq__`) and every copy strategy run it. Counters: `calls` (action runs), `traversals` (`__iter__` calls). Each F9 gate row now also asserts `hook.calls >= 1` and that the attack took effect (`request.side == "buy"`, `state.policy is substituted`, `request.lots.is_nan()`). The restart row still swaps only on a read after the first (`traversals > 1`): HEAD refuses a first-read swap with RiskError, which v1.6 permits, so swapping on every read would contradict the kept expectation. It asserts `calls >= 1` and `traversals >= 1`. Every existing F9 assertion is kept. | AC-03, AC-04, AC-06 |
| tests-r3 F3 (owner: fix) | `_timed_rejection` takes `capsys`, and arm/start/join/cancel run inside `with capsys.disabled():`. Kept: `faulthandler.dump_traceback_later(20, exit=True)` armed before `start`, cancel in `finally`, daemon thread, `join(timeout=10)`, alive check, `perf_counter` around the public call only, strict `< 1.000`. The four timed tests request the `capsys` fixture. | AC-06, AC-07 |
| tests-r3 F2 | Accepted by the owner; no change. The 30M-digit row stays a deadline sample. | — |
| v1.6, review r2 F4 | New `test_ac06_provenance_keys_must_be_exact_str` (32 rows). Keys: a `str` subclass equal to `"risk_per_trade"` whose `__eq__` records the call and lifts `risk_per_trade` to 5 (R4), and an extra int key `1`. Containers: dict and `MappingProxyType`. Paths: construction (`RiskPolicy`) and use in `HaltState`, `size_position`, `start_experiment`, `unknowns`, `check_entry`, `update_equity`, `restart_experiment`. Each row expects exact TypeError, no recorded equality call, and `risk_per_trade` still `.0025`. | AC-06 |
| v1.6, review r2 F5 | New `test_ac02_ac03_second_provenance_read_cannot_change_bound_policy` (6 rows): the hook is planted just before `start_experiment`/`update_equity`/`restart_experiment`, and a second traversal would lower `daily_loss_limit` to `.0001`. The result must hold the same policy object with unchanged H001 values and the honest state (9990: loss 10 < 75; restart keeps day baseline 10000, rebases to 9990). New `test_ac02_ac03_ac04_limit_changed_before_decision_keeps_daily_latch` (4 rows): the lowering lands on the next call's single read, before it decides (v1.6 reads provenance before every other field). Update or restart to 9990 must latch `daily_halted` True (threshold 1 <= loss 10), the recovered update to 10000 keeps the latch, and `check_entry` refuses with `("daily_halt",)`. | AC-02, AC-03, AC-04 |
| v1.6, gate clause | New `test_ac04_ac06_input_changed_during_validation_is_never_allowed` (16 rows). From inside the provenance read, the hook makes the allowed request refusable: lots 41.66, open_exposures 1, stop_loss None, daily or experiment latch True, `day_start_equity` 10200, `state.policy.risk_per_trade` .0001, or `state.day` 23. It must never be allowed: either a RiskError, or the exact reasons for the changed input (a later `state.day` must raise). Each row asserts the hook ran and the change is in place. | AC-04, AC-06 |

Every new row uses fresh `replace(H001_RISK)`/`replace(H001_COSTS)` copies or `_v13_calls`; the H001
singletons are never mutated. The docstring now says v1.6. Integrity (scratch AST script): assertions
88 → 104 with every original assert statement present, `pytest.raises`/`_reject` calls 44 → 45, test
functions 34 → 38 with none removed, every original decorator present. Grep of the amended file for
skip, xfail, importorskip, `.only`, `type: ignore`, noqa, TODO, FIXME, placeholder, pragma, deselect,
tabs, trailing spaces and CR: no hits. A scratch Fraction oracle confirmed the 17 new numeric
expectations (distance 12, sized .02, thresholds 75/1/76.5/200, 41.66 on grid, rate .0001 sizes 0).

### Verification (2026-10-22 +07, CPython 3.12.15 via uv, pytest 9.1.1, Windows)

| Command / procedure | Result | Time |
|---|---|---|
| uv scratch script: black-box probe of HEAD | int key (extra or replacing a name) → TypeError at construction; every public call traverses the provenance once (7 hook calls: `keys`, `__iter__`, 5 lookups), raw and proxy; a first-read `state.policy` swap in restart → RiskError | before 19:37, exact time not captured |
| `timeout 300 uv run --offline pytest <scratch>/tree/tests/acceptance/CORE-003 -q -p no:cacheprovider` (from the repo root; unchanged copy) | PASS, 650 passed in 2.94s | before 19:37 |
| same command, amended copy (`fa1bde04…`) | PASS, **708 passed in 2.83s**, exit 0 | 19:44:08–19:44:12 |
| `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` (repository as is) | PASS, **725 passed in 3.83s**, exit 0 | 19:42:37–19:42:41 |
| `timeout 300 uv run --offline pytest tests <scratch>/tree/tests/acceptance/CORE-003 --ignore=tests/acceptance/CORE-003 -p no:cacheprovider` (rootdir repo, configfile pyproject.toml) | PASS, **783 passed in 4.06s**, exit 0 | 19:42:41–19:42:46 |
| `git apply --check docs/proposals/CORE-003-tests-r4.patch` (standalone) | PASS, exit 0, no output | by 19:43:15 |
| `git apply --numstat …`; in-memory apply; `sha256sum`; `git hash-object --path=…`; `git check-ignore -v`; `git status --short` | PASS: +260/-27 one file; hashes as tabled; ignored; working tree clean before this section | 19:43:15–19:43:28 |

### Mutation evidence (scratch only)

Risk packages came from `git archive <rev> src` into scratch trees. pytest ran with the working directory
set to that tree, as in the tests-r3 review: `uv run --offline --no-sync --project <repo> --directory
<tree> python -B -m pytest <tests> -q -p no:cacheprovider -p <plugin>`. A scratch plugin reported the
loaded `sochron.risk` path every time. The read-path variants shadow `dict` inside `sochron.risk.policy`
(the copy named in tests-r3 F1), so non-dict Mappings are copied by iteration or by `items()`.

| Risk code | Tests | Result | Failure causes |
|---|---|---|---|
| HEAD `34097d9` (control) | amended | 708 passed | — |
| HEAD, iteration copy (3,298 shadowed copies) | amended / locked | 708 passed / **2 failed** | locked: `provenance_callback…[nan_lots-*]` (tests-r3 F1 reproduced) |
| HEAD, `items()` copy (3,298) | amended / locked | 708 passed / **2 failed** | same two locked rows |
| pre-F9 `b9f0396` | amended | **50 failed**, 658 passed | 8 F9 rows (side/policy → allowed True, nan_lots → plain ValueError, restart → substituted .5 policy returned), 32 key rows, 10 F5 rows |
| pre-F9, iteration copy (4,460) | amended | **50 failed**, same set | F9 rows stay non-vacuous on another read path |
| pre-F4 `82844d1` | amended | **42 failed** | 32 key rows (16 int → BadPolicy "extra [1]"; 10 subclass → did not raise; 6 → BadPolicy "got 5" after the key's side effect ran), 10 F5 rows |
| pre-F5 `073ab70` | amended | **10 failed** | 6 bound-value rows (`daily_loss_limit` .0001 != .0075), 4 latch rows (start's own reread lowered the limit) |
| HEAD with a snapshot-then-decide gate wrapper | amended / locked | **BLOCKED, not run** | see "Blocks" |

The 16 gate input-change rows failed on no historical code: pre-F9 code decided on the live, changed
inputs. They guard against a gate that decides on a snapshot taken before the provenance read. The run
that would have shown this was blocked.

### Watchdog probe (tests-r3 F3)

A scratch probe test loads each file's `_timed_rejection` and hangs the worker in one GIL-holding C call
(`sum(range(10**14))`), run with `uv run --offline pytest <probe>::<test> -q -p no:cacheprovider`. Amended
harness: after 20 s, exit 1 with **46 lines** on the terminal, starting `Timeout (0:00:20)!`, with both
thread stacks through the amended file. The main thread was blocked in `worker.start()` inside the
`capsys.disabled()` block (19:41:20–19:41:40; recount 19:42:11–19:42:31). Locked harness: after 20 s,
exit 1 with **0 lines** (19:41:50–19:42:11).

### Blocks

guard-bash blocked the snapshot-then-decide mutation run (about 19:39) with: `Blocked by
.claude/hooks/guard-bash.mjs: redirecting output into C:/Users/MSI/AppData/Local/Temp/claude/C--Users-MSI-Desktop-------------Sochron1k/00501979-976d-4b0e-9168-e8ef94f159c0/scratchpad/mut/snapshot-$(basename
$(dirname $(dirname $(dirname $target)))).log (a path that cannot be resolved here (variable or unknown
directory)). Ask the owner.` It was not retried in any form: no literal path, no rerun without the redirect.
The headless-reviewer literal-path exception names reviewers, and this session's instructions forbid
reworded commands. That evidence is BLOCKED.

### Questions and limits

- Q1 (owner): an int key can never be the only defect. It is always an extra key or replaces a name,
  which the v1.3 table maps to BadPolicy, and the table leaves the order of several defects open. The
  int rows expect TypeError, per the owner's instruction for this patch and the v1.6 exact-str row.
  HEAD checks key types first, for both forms. If the owner prefers the multi-defect rule, these
  16 rows would need to accept BadPolicy as well; this patch does not do that.
- Q2 (owner): the gate input-change rows accept any RiskError subclass as a refusal, as the existing
  policy-swap row does. v1.6 says "error ตามตาราง", but the table names no error for a valid input
  changed during validation.
- `traversals` counts `__iter__` calls. A reread through fixed-name lookups alone would not trigger
  the restart swap or the F5 lowering. v1.6 exact-str keys need a traversal on every read, and HEAD
  makes exactly one per call.
- Not run: CI, the owner demo, the snapshot-gate mutation (BLOCKED). E1 obligations (L1–L5, F7) cannot
  be tested through the pure API.

**Next action (implementer, D-006):** recompute the patch SHA256. Then, each as one standalone command:
`git apply --check docs/proposals/CORE-003-tests-r4.patch`, then `git apply docs/proposals/CORE-003-tests-r4.patch`.
The detector should list exactly `tests/acceptance/CORE-003/test_risk_acceptance.py`. Verify its SHA256
and `git hash-object --path=<path> <path>` against the table above, and stop on a mismatch. Run
`uv run --offline pytest tests -q -p no:cacheprovider` (expected 783 passed, 0 skipped). Obtain a
fresh-session review of the applied diff and this section; that reviewer is not this test-author
session. Then commit with `Refs: CORE-003`. The final implementation review r3 stays separate.
Delivery state: **proposal written and checked; not applied, committed, merged or deployed**.

## Application of tests r4 and findings response to review r3 (Claude Code)

Tests r4 (Claude test author under the role swap): patch SHA256 `9d290dc9…` matched; standalone
`git apply --check` and `git apply`; the detector listed exactly the one target file; applied SHA256
`fa1bde04…` and blob `d2ba11db…` matched; `git apply -R --check` passed; full suite 783 passed, 0
skipped (19:47); a third, separate fresh session reviewed it (`docs/reviews/CORE-003-tests-r4.md`,
ready to commit); committed `a4bb3fe`. tests-r4 F2 answered by the contract sentence `18dcfea`.

Review `docs/reviews/CORE-003-r3.md` (Claude reviewer under the role swap, HEAD `18dcfea`, committed
`6ec0631`) closes r2 F4/F5 and finds F6 (Low) and F7 (Low, question). Owner decisions 20:2x:

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| r3 F6 Low | Closed by owner scope decision | `8992037` | Contract v1.7 scope of protection: hostile in-process code that edits object internals (a planted key in an object `__dict__`) is outside what a pure module can stop, like setting a valid but wrong `risk_per_trade` 0.99; E1 L2 now bans `vars(`/`__dict__` writes, ABC `.register(` and runtime monkeypatching outside `sochron.risk`, journal and tests. No code change. |
| r3 F7 Low (question) | Closed by owner scope decision | `8992037` | Same allocation (process-wide ABC hook). No code change. |
| tests-r4 F1 Low | Unit test (owner) | `fd50946` | `test_every_public_call_reads_provenance_exactly_once`: 7 public calls each read provenance once (one traversal, each key once). Passes at HEAD; with `halts.py` from `073ab70` (before the F5 fix) it fails `assert 2 == 1`. |

Full suite: `uv run --offline pytest tests -q -p no:cacheprovider` → 784 passed, 0 skipped. Locked
tests unchanged since `a4bb3fe`.
