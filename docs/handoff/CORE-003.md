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
