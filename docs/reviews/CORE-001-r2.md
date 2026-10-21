# Review CORE-001 round 2 · base 5546da0 · head c751610 · reviewer Codex, fresh headless review session

Scope: approved `docs/contracts/CORE-001-timebase.md`, review r1, the complete
`git diff 5546da0..HEAD`, and the handoff's findings response. This is a bounded
re-review of F1-F3 and their surrounding impact, not a new audit of unchanged code.
The owner explicitly authorized this report as the only write. No questions,
implementation/test edits, staging, commit, push, or approval were performed.

**Result: F1, F2 and F3 closed for their original reported defects/question.
Two new Low regressions, F4 and F5, remain open.** The common-hour helper is therefore
not correct across the entire finite-input domain, despite fixing F1's reproduction.
AC-06 remains FAIL for those new cases. The requested suite passes all 22 tests.

- Reviewed head: `c751610fa1e259acfc886e0f5de7e0942dc9c01a` on `feat/CORE-001-timebase`.
- Re-review base: `5546da044aa88fc0a1d8a08b5771b8ec04d7865c`.
- Scan base: `origin/main` = `20b7c641b23ecbec2e12f676a85ebf7cfbaa942e`;
  merge-base = `90278b4e7b120454038ecde8bd0d55ccbf5ed5ae`.
- Environment: Windows, Python 3.12.15, uv 0.13.0, pytest 9.1.1, tzdata 2026.5.
- Times below are 2026-10-21, Asia/Bangkok (+07).

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `src/sochron/timebase/offset.py:38`, `:53` | **Closed, original defect.** `[1800.0, 5400.0]`, tolerance 1800 now yields shifted/+1/2; its negative mirror yields shifted/-1/2. All ten locked rows and 3,960 independent boundary cases pass. See F4/F5 for separate new arithmetic regressions. | Samples with different nearest rounded hours nevertheless share one fitting nonzero hour. | Original valid common-hour evidence is now recognized. | Implemented by `5538617`; no additional change for the original reproduction. | Exact new test at `tests/unit/timebase/test_timebase_unit.py:124` fails against actual `5546da0` source loaded in memory and passes at HEAD. |
| F2 | Low | question | `src/sochron/timebase/offset.py:34` | **Closed, question answered consistently.** NaN and either infinity, alone or mixed with finite samples, return unknown/None with the original count. Independently checked 75 cases and unchanged rule snapshots. | Any non-finite sample. | The documented unknown policy is implemented without leaking the former rounding exceptions. | Implemented by `b8c993d`; no different policy required by the contract. | Exact new test at `tests/unit/timebase/test_timebase_unit.py:135` raises ValueError against `5546da0`, then passes at HEAD. |
| F3 | Low | confirmed | `src/sochron/timebase/sessions.py:36` | **Closed.** Instant, start and inclusive end are all reduced to hour/minute. Original reproduction changes False to True; independent bound/DST/zone probes pass. | Seconds or microseconds in either custom-window bound. | Opening minute is now included consistently; NY/DST behavior is preserved. | Implemented by `0b8475d`. | Exact new test at `tests/unit/timebase/test_timebase_unit.py:93` fails on its 03:00 assertion against `5546da0`, then passes all six assertions at HEAD. |
| F4 | Low | confirmed | `src/sochron/timebase/offset.py:53` and `:54` | **New, open.** `classify_offset([1.7e308], 1e307)` raises `OverflowError: cannot convert float infinity to integer`; negative mirror also raises. Both inputs are finite. `5546da0` returned a classification. Reproduction below. | Positive finite tolerance and a finite sample whose sum/difference overflows while forming a bound; the all-near-zero branch is false. | The reporter aborts instead of classifying. Under the documented several-hours policy these cases should be unknown. Low because magnitudes are extreme and there is no execution path. | Make bound formation overflow-safe for finite inputs, preserving the finite contract and ambiguity policy. Do not silently impose an uncontracted magnitude limit. | Add positive/negative finite-extreme regressions expecting unknown with count 1, plus a mixture/count check; demonstrate failure before and passage after, then rerun the suite. |
| F5 | Low | confirmed | `src/sochron/timebase/offset.py:60` | **New, open.** For `h = 2**53`, `x = float(h * 3600)` is exactly h hours. At default tolerance 120, HEAD returns unknown while `5546da0` returns shifted/h/1. The negative mirror also fails. The exact rational interval contains only h. | An integer-hour value beyond the exact consecutive-integer range of binary64 is multiplied by float `HOUR_SECONDS`. | Adjacent integer candidates collapse to the same float, creating false ambiguity and losing a valid unique shift even at default tolerance. Low because the magnitude is extreme. | Preserve integer-hour identity in candidate multiplication/comparison; avoid converting h to float before multiplication. Keep the bound arithmetic consistent with that choice. | Add regressions for both signs at `float((2**53) * 3600)`, default tolerance, expecting shifted with the exact integer h and count 1; use an integer/rational oracle and retain ordinary boundary/ambiguity tests. |

## AC status

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Current suite reruns `test_ac01_raw_utc_milliseconds_and_fixed_round_trips`: SPIKE tick, 23 fixed raw values, milliseconds and shifted rules. Source/locked test unchanged. The fixed-versus-random choice remains the already-recorded tests-r1 issue, not reopened here. |
| AC-02 | PASS | Current acceptance test passes all 30 NY golden rows across both 2026 DST changes; F3 regression and independent seconds/microseconds, DST and other-zone probes pass. |
| AC-03 | PASS | Current `test_ac03_bangkok_calendar_day_changes_at_1700_utc` passes both literal midnight rows and aware-zone conversions; implementation unchanged. |
| AC-04 | PASS | Current `test_ac04_m1_and_tick_alignment_to_m15` passes 15 M1 opens, tick edges, all 19 supported timeframes, shifted alignment and invalid timeframes; implementation unchanged. |
| AC-05 | PASS | Current named rejection test passes unknown server, naive datetime, raw range and millisecond mismatch cases; required errors remain unchanged. |
| AC-06 | FAIL | Ten locked rows, F1/F2 regressions and rule immutability pass. F4/F5 violate the associated finite-input classification rule outside those test rows. No offset/tolerance magnitude cap exists in the contract. |
| AC-07 | PASS | Architecture AST test and complete suite pass, 22 passed and zero skipped. Red-flag secret and order/account mutation groups are empty. This is local evidence, not CI approval. |

AC-06 FAIL does not mean a locked test failed: the green suite lacks F4/F5 cases.
No acceptance/golden/architecture test was edited to reach this result.

### Re-review evidence and policy judgments

**F1:** Intersecting fitting-hour intervals fixes independent per-sample rounding.
For moderate finite values the implementation widens the computed integer endpoints
by one, then checks the actual inequality; independent enumeration found no mismatch
in 3,960 pairs around both endpoints, including adjacent representable floats.
Tolerances were 0, the smallest positive float `5e-324`, `1e-300`, `1e-10`, 120,
the floats immediately below/above 1800, exactly 1800, 3600 and 7201; hour centers
were -5 through +5. The oracle enumerated nonzero hours -20 through +20, a complete
range for these inputs, without using computed interval bounds.

At tolerance `1e12`, samples `[3600-1e12, 3600+1e12]` yield shifted/+1;
the negative mirror yields shifted/-1. `[1e12+1]` at that tolerance is ambiguous
and yields unknown. At tolerance `5e-324`, `[3600.0]` yields shifted/+1 while
`[math.nextafter(3600.0, math.inf)]` yields unknown. F4/F5 show why the endpoint
and float-precision reasoning cannot be claimed for arbitrary finite magnitudes.

The explicit several-fitting-hours policy is reasonable: the contract does not
choose which h to report in that case, and the handoff documents unknown as a
conservative clarification. `[5400.0]` at tolerance 1800 fits +1 and +2 and returns
unknown. This is not the uniquely fitting `[1800.0, 5400.0]` case. It does not
require another finding or an invented tie-break policy. The all-near-zero rule
still has priority: `[1800.0]` at tolerance 1800 is ok; at default 120 it is unknown.
F5 is distinct from this policy: exactly one mathematical hour fits, but floating
candidate multiplication invents another.

All ten locked offset rows were also executed independently:

| Samples | Tolerance | Observed result (kind / hours / count) |
|---------|-----------|----------------------------------------|
| `(-120, -3.8, 0, 0.865, 120)` | 120 | ok / None / 5 |
| `(7080, 7200, 7320)` | 120 | shifted / 2 / 3 |
| `(0.5, 7200, 30)` | 120 | unknown / None / 3 |
| `()` | 120 | unknown / None / 0 |
| `(1800,)` | 120 | unknown / None / 1 |
| `(-7320, -7200, -7080)` | 120 | shifted / -2 / 3 |
| `(-7200, 7200)` | 120 | unknown / None / 2 |
| `(120.001,)` | 120 | unknown / None / 1 |
| `(-5, 5)` | 5 | ok / None / 2 |
| `(6,)` | 5 | unknown / None / 1 |

**F2:** The finite check occurs after conversion/counting and before zero/hour
classification. It rejects the entire evidence set rather than dropping bad
samples. Three non-finite values, five placements/mixtures, and five finite
tolerances (0, `5e-324`, 120, 1800, `1e12`) produced 75 correct unknown/count
results; before/after `RULES` snapshots matched. The contract's catch-all unknown
and lack of a specified non-finite error are consistent with this answer. The
handoff flags the choice for the owner. No new error policy is demanded here;
non-finite or negative tolerances remain a separate unspecified-input question.

**F3:** A root probe covered 112 combinations of start/end seconds and microseconds
with before/opening/closing/after instants. A separate read-only reviewer checked
2,648 assertions: 1,728 UTC/Bangkok subsecond-bound cases; 864 NY assertions on
March 7/8/9 and October 31/November 1/2 with four boundaries, subsecond instants,
UTC/NY/Bangkok representations, and default/custom bounds; 48 autumn-fold
assertions; six same-minute-window assertions; and two naive-datetime refusals.
The spring jump and both repeated autumn hours remain correct. End-only subsecond
bounds already happened to work before the fix; opening-bound regressions are
what make the added test fail against the old implementation.

**Regression sensitivity:** The exact three added test functions were executed
against pre-fix source obtained with `git show 5546da0:<source-path>`, loaded only
in memory, and then against HEAD. For offset tests, `OffsetClass` was also rebound
to the pre-fix class so a class-identity mismatch could not create a false failure.
F1 failed its first expected shifted assertion; F2 raised the original NaN
ValueError; F3 failed the opening-minute assertion. All three passed with HEAD.

**Drive-by edits:** `5538617` changes only the F1 classifier/helper and adds its
unit regression; `b8c993d` adds only the F2 guard and regression; `0b8475d` changes
only F3's function/docstring and adds its regression. Existing tests are preserved.
The remaining four paths in the complete re-review diff are the r1 report,
handoff, evidence and PROGRESS records. They document this review/fix cycle.
No unrelated production edit, dependency/config/lockfile change, or locked-test
modification was found. F4/F5 are surrounding regressions introduced by F1's helper,
not unrelated scope expansion.

### Reproducing the new findings

Run each snippet from the repository root through a PowerShell single-quoted
here-string piped to `uv run --offline --no-sync python -B -`. No file is written.

F4 (current code raises on the first assertion; run either sign independently):

```python
import sys
sys.path.insert(0, "src")
from fractions import Fraction
from sochron.timebase import classify_offset, OffsetClass

for sign in (1, -1):
    x, tolerance = sign * 1.7e308, 1e307
    # Two distinct fitting integer hours prove ambiguity without overflowing bounds.
    hours = [sign * int(v / 3600) for v in (1.65e308, 1.75e308)]
    assert hours[0] != hours[1]
    assert all(abs(Fraction(x) - h * 3600) <= Fraction(tolerance) for h in hours)
    assert classify_offset([x], tolerance) == OffsetClass("unknown", None, 1)
```

The positive case overflows `x + tolerance` at line 54; the negative case overflows
`x - tolerance` at line 53. Both produce the exact exception in F4. Samples
`[1e308]` with tolerance `9e307` and their negative mirror reproduce it too.
The old classifier returns shifted for all four cases; the new ambiguity policy
can legitimately change that result to unknown, but does not justify an exception.

F5 (current code fails the final assertion for either sign):

```python
import math
import sys
sys.path.insert(0, "src")
from fractions import Fraction
from sochron.timebase import classify_offset, OffsetClass

for sign in (1, -1):
    h = sign * 2**53
    x = float(h * 3600)
    assert Fraction(x) == h * 3600
    assert math.ceil((Fraction(x) - 120) / 3600) == h
    assert math.floor((Fraction(x) + 120) / 3600) == h
    # With a float multiplier, the adjacent candidate falsely has distance zero.
    assert abs(Fraction(x) - (h + sign) * 3600) == 3600
    assert abs(x - (h + sign) * 3600.0) == 0.0
    assert classify_offset([x]) == OffsetClass("shifted", h, 1)
```

For positive h, x is `3.242591731706757e19`. Exact arithmetic gives unique common
bounds `[9007199254740992, 9007199254740992]`. Integer multiplication followed by
float subtraction gives the adjacent candidate distance 4096, also outside 120;
the implementation's float multiplication gives zero instead.

## Checked, nothing found (and how)

- Locked tests: `git diff --exit-code 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture`
  exited 0 with no output. The complete re-review diff adds three unit tests and
  removes/weakens none. Current suite has six acceptance, one architecture and
  fifteen unit tests, zero skipped.
- The changed functions retain pure local computation, no clock/MT5/filesystem/
  network/environment access, no mutation of rules, and no mutable operational
  shared state. Duplicate/concurrent calls introduce no external effect. Candidate
  enumeration is bounded by the helper's early ambiguity branch; the finite-input
  arithmetic failures are explicitly recorded above rather than treated as passes.
- Handbook F01-F18 checked against this diff: AC completeness, test preservation,
  production fakes, new APIs/dependencies, scope, duplicate code, swallowed errors,
  controls/secrets/destructive operations, embedded instructions, bounded review,
  context separation, unnecessary abstraction, evidence and delivery wording,
  and toolchain drift. No additional finding within this re-review scope.
- No trading/account/order, strategy/research/holdout, or risk-control path was
  added. The only new import is stdlib `math`; dependency files are unchanged.

### Red-flag groups

`bash scripts/controls/red-flags.sh origin/main` completed with exit 0 and
**one pattern group with hits: Type checks disabled**, four existing comments at
`tests/unit/timebase/test_timebase_unit.py:32,42,44,46`. They intentionally pass
invalid mapping assignment, float raw time, bool raw time, and float milliseconds
to test runtime rejection. They do not suppress a production check and were not
introduced by these fixes. The physical line numbers above come from the current
file, rather than the old report's numbering.

The other nine groups are empty: Skipped or focused tests; Lint disabled;
Placeholder or mock in production code; Swallowed errors; Possible secrets;
Secret-like value assigned; Destructive or bypass commands; Client-exposed
variable with secret-like name; Order or account mutation surface.

Deleted/renamed tests: none. Untracked files at scan time: none (this report was
written afterwards). The separate control-file list contains `pyproject.toml`,
`uv.lock`, and the three locked test files from the original task. None changed
in the re-review diff. The owner-controlled PR/locked-path gate is not bypassed
or claimed passed by this scan.

### Commands and exact results

All commands target `c751610` unless a historical in-memory comparison is stated.
Probe processes exit 0 when they successfully observe an expected pre-fix/new
defect; those behavioral failures remain FAIL, not PASS.

| Command / procedure | Result | Commit | Time (+07) |
|---------------------|--------|--------|------------|
| `uv run --offline pytest tests -q -p no:cacheprovider`, repository root, process-local `PYTHONDONTWRITEBYTECODE=1` | PASS, exit 0: **22 passed in 0.05s**, zero skipped | `c751610` | 08:49:21 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; one group/four explained hits; secret/order groups empty | `c751610` | 08:49:21 |
| `uv run --offline --no-sync python -B -`, root offset/golden/F2/regression probes | PASS: 10 locked rows, 3,960 boundary pairs, 75 non-finite cases, original regression sensitivity; FAIL behavior: four finite-overflow cases. Exit 0 | `c751610`, old `5546da0` in memory | 08:50:00 |
| Same offline Python command, separate read-only F3 probes | PASS: 2,648 assertions; exact regression fails before/passes after; no file writes | `c751610`, old `5546da0` in memory | 08:50:09 |
| Same offline Python command, root rational/new-finding/F3 confirmation | FAIL behavior: F4/F5 both signs; exact integer/rational witnesses confirmed. PASS: F3 sensitivity and 112 bound cases. Exit 0 | `c751610`, old `5546da0` in memory | 08:50:58 |
| `git diff --exit-code 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture` | PASS, exit 0, empty | `c751610` | 08:50:18 |
| `git diff --check 5546da0..HEAD` | PASS, exit 0, no output | `c751610` | 08:50:18 |
| `uv --version`; Python version and installed distribution metadata | PASS: uv 0.13.0, Python 3.12.15, pytest 9.1.1, tzdata 2026.5 | `c751610` | 08:50:00-08:50:18 |
| `git status --short`; `git diff --cached --exit-code`; `git diff --exit-code`; report `Test-Path` before writing | PASS: clean worktree/index, no tracked diff; report did not exist | `c751610` | 08:51:15 |
| Final `git status --short`, tracked/index diffs, `git rev-parse HEAD`, offline Python report structure/whitespace check | PASS: only this report untracked; tracked diff and index empty; HEAD unchanged; all required sections/AC/finding rows present | `c751610` | 08:52:38 |
| Initial `rg` text lookup; fallback `Select-String -Encoding utf8` | BLOCKED lookup: `rg` not recognized; PASS fallback, no configuration changed | `c751610` | 08:48-08:49 |

## Not checked (and why)

- No new audit of unchanged conversion/bar/rule implementation. Their named tests
  were rerun, and r1 findings/evidence were consulted; this round targets F1-F3.
- No exhaustive float-domain proof, arbitrary input sizes/types, all IANA zones,
  overnight-window semantics, or new policy for negative/non-finite tolerances.
  The finite large-value failures above were tested and failed; they are not
  included in this untested category.
- No Linux run, clean installation, online dependency/admission refresh, type
  checker, Python CI run, or control-plane regression suite. No control code or
  dependency changed. The existing synced environment was used offline.
- No terminal/broker connection, market data, Demo/live execution, strategy,
  costs/risk gate, holdout, journal/reconciliation or deployment: outside contract.
- Interactive `/review` is unavailable in this headless tool interface; performed
  the manual contract/diff review with independent read-only probes. The owner's
  specified re-review/scan bases supersede the skill's generic main baseline.
- No staging, commit, push, labels, merge, approval or PROGRESS edit. Only this
  report is written. Delivery remains **implemented**, with local verification
  evidence and open F4/F5; this review does not promote the task to verified,
  merged or deployed. Next action: implementer addresses F4/F5 with failing
  regressions, then an independent re-review checks those IDs.
