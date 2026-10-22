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
