# Review CORE-001 round 3 · base origin/main · head bf0d504 · reviewer Codex, fresh headless review session

Scope: re-check F4/F5 from `docs/reviews/CORE-001-r2.md` and their surrounding
impact against the approved `docs/contracts/CORE-001-timebase.md`.
Reviewed the complete `git diff c751610..HEAD -- src tests`, the prior findings,
and the specified r2 response in `docs/handoff/CORE-001.md`.
The owner explicitly authorized this report as the only write. No approval
question is needed, and no code/test/PROGRESS edit, staging, commit or push is authorized.

**Result: F4 closed; F5 closed. No new finding within this re-review scope.**
The requested suite passes **24 tests, zero skipped**. The independent integer
oracle agrees on **16,674 cases**. These are local verification results, not CI
approval or permission to merge.

- Reviewed head: `bf0d504714d6538a3ec0cd03794cf2b6221df161`, branch `feat/CORE-001-timebase`.
- Re-review base: `c751610fa1e259acfc886e0f5de7e0942dc9c01a`; fix: `0e80263`.
- PR/scan base: `origin/main` = local `main` = merge-base =
  `20b7c641b23ecbec2e12f676a85ebf7cfbaa942e`.
- Environment: Windows; uv 0.13.0; Python 3.12.15; pytest 9.1.1; tzdata 2026.5.
- All times below: 2026-10-21, Asia/Bangkok (+07). No remote fetch was performed.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F4 | Low | confirmed | `src/sochron/timebase/offset.py:55`, `:56`, `:57` | **Closed.** Each of `[±1.7e308]` with tolerance `1e307` and `[±1e308]` with `9e307` returns unknown/None/1. All four raised `OverflowError: cannot convert float infinity to integer` on actual `c751610` source loaded in memory. Mixed `[1.7e308, 0.0]` returns unknown/None/2. | Former bound addition/subtraction overflowed despite finite inputs. | Classifier now reports ambiguous or inconsistent evidence without the former exception. | Implemented in `0e80263`: exact rational bounds; no further fix required for this finding. | Exact new test at `tests/unit/timebase/test_timebase_unit.py:147` fails with OverflowError on pre-fix source and passes at HEAD; signed reproductions, extreme inputs, oracle and full suite pass. |
| F5 | Low | confirmed | `src/sochron/timebase/offset.py:15`, `:56`, `:57`, `:58` | **Closed.** `float(±2**53 * 3600)` at default tolerance yields shifted with exact integer hours `±9007199254740992`, count 1; pre-fix code yields unknown. Exact endpoint arithmetic preserves distinct integer hours. | Float multiplication collapsed neighboring integer hours and manufactured ambiguity. | Unique mathematical shifts are retained beyond binary64's consecutive-integer range; genuine ambiguity remains unknown. | Same `0e80263` exact-arithmetic fix; integer `HOUR_SECONDS = 3600`. The shared root cause justifies the single commit. | Exact new test at `tests/unit/timebase/test_timebase_unit.py:156` fails with AssertionError on pre-fix source and passes at HEAD; signed powers through `2**1011`, adjacent floats and residual/tolerance boundaries agree with an integer oracle. |

## AC status

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Current suite reruns `test_ac01_raw_utc_milliseconds_and_fixed_round_trips`: SPIKE tick/milliseconds, 23 fixed round-trip rows and shifted rules. Source and locked tests unchanged. This round does not reopen the fixed-versus-random selection issue recorded in earlier reviews. |
| AC-02 | PASS | Current `test_ac02_new_york_window_across_both_dst_changes` passes 30 locked New York rows covering both 2026 DST transitions and window boundaries; existing F3 unit regression also passes. No session implementation change in this diff. |
| AC-03 | PASS | Current Bangkok acceptance test passes both literal midnight rows and aware-zone conversions. Implementation unchanged. |
| AC-04 | PASS | Current bar acceptance test passes 15 M1 opens, tick edges, all 19 supported timeframes, shifted alignment and invalid-timeframe rejections. Implementation unchanged. |
| AC-05 | PASS | Current rejection test passes unknown server, naive datetime, raw range and millisecond mismatch cases with required errors. Implementation unchanged. |
| AC-06 | PASS | Ten locked offset rows, seven focused F1/ambiguity/zero-priority rows, 75 F2 non-finite cases and unchanged rule snapshots pass. Both new tests demonstrably fail before/pass after; the independent integer oracle passes 16,674 cases and the exact-bound proof below covers finite float arithmetic. |
| AC-07 | PASS | Architecture AST check and complete suite pass: 6 acceptance + 1 architecture + 17 unit tests, zero skipped. Secret and order/account mutation scan groups are empty. New import is stdlib `fractions`; no I/O, clock, MT5 or rule mutation is introduced. Local evidence only. |

### Arithmetic proof and ambiguity policy

For the actual finite binary-float inputs, `Fraction(x)` and `Fraction(t)`
represent their values exactly. The installed Python 3.12 implementation's
constructor uses `as_integer_ratio()`; its `__ceil__` and `__floor__` use integer
floor division. `HOUR_SECONDS` is integer 3600, so subtraction, addition and
division stay rational. No intermediate bound is converted back to float.
Python integers accommodate bounds beyond the binary64 range. Consequently
neither F4's overflowing float sum nor F5's rounded candidate product remains.

For nonnegative tolerance t, the hours fitting sample x are exactly the integers
between ceil((x-t)/3600) and floor((x+t)/3600), inclusively. Taking the largest
lower bound L and smallest upper bound U therefore gives their exact intersection:
L > U means no fitting hour; L < U means at least two; L = U means exactly one.
The helper returns shifted only in the last case, with a nonzero integer hour.

**L = U = 0 cannot occur after the all-near-zero check.** Once that check fails,
some finite sample satisfies x > t, forcing L >= 1, or x < -t, forcing U <= -1.
Thus zero cannot even belong to the remaining intersection. The explicit
`lowest != 0` guard is harmless; it does not hide a unique valid candidate.
At signed zero tolerance, exact nonzero whole hours shift; other nonzero samples
are unknown and zero samples are ok. At t = 1800, the established all-near-zero
priority and multiple-hour ambiguity policy remain consistent.

For a strictly negative finite tolerance, each real lower endpoint is greater
than its upper endpoint. Its integer lower bound is therefore greater than its
integer upper bound; the common intersection is empty and the classifier returns
unknown. This records arithmetic behavior, without inventing a new input policy.
Non-finite tolerances are outside this proof. Non-finite samples are handled by
the unchanged earlier guard.

Exactness is for the supplied floats, not precision already lost by the caller.
For example, `float((2**60 + 17) * 3600)` equals exactly `2**60 * 3600`, so the
correct returned hour is `2**60`. Conversely, the float constructed from
`(2**53 + 1) * 3600` differs from that integer-hour center by +496 seconds;
its negative mirror differs by -496. Independent checks observed:

| Supplied sample | Tolerance | Result |
|-----------------|-----------|--------|
| `float(±(2**53 + 1) * 3600)` | `495.99999999999994` (next float below 496) | unknown/None/1 |
| same | `496.0` | shifted / exact `±9007199254740993` / 1 |
| same | `496.00000000000006` (next float above 496) | shifted / exact `±9007199254740993` / 1 |
| `float(±2**53 * 3600)` | default 120 | shifted / exact `±9007199254740992` / 1 |

A separate read-only reviewer independently confirmed the finite-input proof,
zero exclusion and ambiguity reasoning; that reviewer ran no tests and wrote no files.

### Independent probes and regression sensitivity

The oracle does not use Fraction or the implementation's ceil/floor intersection.
It scales float integer ratios to a common power-of-two denominator, then checks
the contract's residual inequality using integers. Let q be the integer floor
of the midpoint of the minimum/maximum sample, expressed in hours. The four
candidates q-1, q, q+1, q+2 are enough to distinguish zero, one and several
fitting hours: the feasible interval is symmetric about that midpoint. A singleton
must be at a nearest integer; an interval with multiple integers necessarily
includes at least two of these central candidates. This avoids enumerating
astronomically many hours for a large tolerance.

| Probe group | Cases | Coverage/result |
|-------------|-------|-----------------|
| Ordinary endpoints | 3,450 | Centers -11..11; 10 tolerances: 0, smallest positive float, 1e-300, 1e-10, 120, immediately below/at/above 1800, 3600, 7201. Singletons and all nine pairs of endpoint/adjacent-float values. PASS. |
| Large-hour samples | 1,440 | Exponents 53, 54, 55, 60, 80, 100, 250, 500, 900, 1011; integer deltas -3,-1,0,1,3,17; both signs; tolerances 0,120,1800,3600; singleton and adjacent-float pairs. PASS. |
| Large residual boundaries | 360 | Same 120 signed large centers, tolerance immediately below/at/above exact distance to the nearest integer hour. PASS. |
| Exactly representable large hours | 10 | Both signs of powers 2**53, 2**60, 2**100, 2**500, 2**1011, default 120; exact integer hours returned. PASS. |
| Finite extremes | 336 | Maximum finite magnitude, 1.7e308, 1e308, subnormals, tiny values, signed zero; both signs, singleton/zero/opposite/duplicate mixtures; tolerances through maximum finite float. PASS. |
| Signed/negative tolerance | 70 | -maximum, -1800, -120, -smallest positive float and -0.0 across extreme and ordinary samples. PASS for the mathematical behavior above. |
| Wide common intervals | 8 | Centers -2,-1,+1,+2 hours with tolerance 1e12; exactly touching endpoints give the unique hour, then moving the upper sample by 1 makes the intersection empty. PASS. |
| Seeded binary64 values | 5,000 | `random.Random(3001)`, finite random bit patterns, 1-3 samples with finite nonnegative tolerance. PASS. |
| Seeded residual boundaries | 6,000 | Next 2,000 finite random samples, nearest-hour residual tolerance and adjacent representable tolerances. PASS. |
| **Total** | **16,674** | **Zero mismatches; 8,808 unknown, 3,764 shifted, 4,102 ok.** |

The two **exact added test functions** were extracted from the current test file
with AST and executed against actual `git show c751610:src/sochron/timebase/offset.py`
source loaded only in memory, then against HEAD. `OffsetClass` was rebound with
the old classifier so class identity could not manufacture a failure.
F4 failed with its original OverflowError; F5 failed its shifted assertion.
Both passed at HEAD. Each F4 signed reproduction was also run independently
so the first raised exception did not conceal the other three cases.
All historical modules/probes remained in memory; no checkout or source rewrite occurred.

All ten locked rows were rerun independently:

| Samples | Tolerance | Observed kind / hours / count |
|---------|-----------|--------------------------------|
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

F1 surrounding checks at tolerance 1800: `[1800,5400]` returns shifted/+1;
the negative mirror returns shifted/-1; `[1800,9000]` returns unknown;
`[5400]` and `[-5400]` each return unknown; `[1800]` and `[-1800]` each
return ok. F2: NaN and both infinities across five placements/mixtures and
five finite tolerances (0, smallest positive float, 120, 1800, 1e12) give
75 unknown results with preserved counts. Before/after rule snapshots match.

## Checked, nothing found (and how)

- **Code scope:** `git diff c751610..HEAD -- src tests` changes only
  `src/sochron/timebase/offset.py` and adds the two unit tests. Production
  changes are precisely the Fraction import, integer hour constant, exact
  interval calculation and explanatory docstring. Nothing beyond F4/F5
  changed in that code diff; no existing test was removed or weakened.
- **Locked tests:** `git diff --exit-code 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture`
  exited 0 with empty output. Their original bytes remain intact.
- **Merge:** `git diff --name-status HEAD^1 HEAD` lists only seven documentation
  paths: PROGRESS, SPEC, H001 hypothesis/background, two tooling admission
  reviews and the tooling registry. `git diff --exit-code HEAD^1 HEAD -- src tests pyproject.toml uv.lock`
  is empty. The owner-approved main merge did not change code or dependencies.
  H001/tooling documents are not treated as unrelated F4/F5 implementation edits.
  The PR diff is `git diff origin/main...HEAD`, excluding changes already in main.
- **Dependencies and controls:** no new package, lockfile, configuration, CI or
  locked-path change in the fix. Fraction is stdlib, available in Python 3.12.
  Its installed constructor and integer rounding methods were inspected.
- **Purity/resources:** classifier state is local, duplicate/concurrent calls
  cause no external effects, and no exceptions are swallowed. The helper
  performs two linear scans over bounded-size binary64 rational values;
  work does not scale with the number of fitting hours. Sample-list storage
  remains linear in input length. No workload benchmark was needed to close
  these numerical defects.
- **Handbook F01-F18 / project invariants:** checked AC evidence, preservation of
  tests, absence of production fakes, APIs/dependencies, task scope, duplicate
  implementation, swallowed errors, controls/secrets/destructive operations,
  embedded instructions, review bounds, independent context, abstraction,
  evidence wording and toolchain drift against this diff. No additional issue
  found within scope. No order/account/risk/strategy/research/holdout path added.

### Red-flag groups

`bash scripts/controls/red-flags.sh origin/main` exited 0 and reported
**one pattern group with hits: Type checks disabled**. Its four existing
`type: ignore` comments are at `tests/unit/timebase/test_timebase_unit.py:32,42,44,46`.
They intentionally exercise assignment to the read-only rule mapping and
rejection of float raw time, bool raw time and float milliseconds. They suppress
static complaints in negative tests, not production checks, and are unchanged by F4/F5.

The other nine groups are empty: Skipped or focused tests; Lint disabled;
Placeholder or mock in production code; Swallowed errors; Possible secrets;
Secret-like value assigned; Destructive or bypass commands; Client-exposed
variable with secret-like name; Order or account mutation surface.

Deleted/renamed tests: none. Untracked files at scan time: none; this report was
created afterwards and is therefore outside that scan. The separate control-file
list contains `pyproject.toml`, `uv.lock`, and the three original locked test
files. These belong to the original PR, not this fix. No owner-controlled label
or locked-path gate is bypassed or claimed passed.

### Commands and exact results

All HEAD commands below target `bf0d504`. A successful historical probe means it
observed the expected pre-fix failure; it does not relabel that behavior as passing.

| Command / procedure | Result | Commit | Time (+07) |
|---------------------|--------|--------|------------|
| `uv run --offline pytest tests -q -p no:cacheprovider` from repository root, process-local `PYTHONDONTWRITEBYTECODE=1` | PASS, exit 0: **24 passed in 0.06s**; zero skipped | `bf0d504` | 19:15:06 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; one group/four explained hits; secret and order/account groups empty | `bf0d504` | 19:15:06 |
| `git diff --exit-code 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture` | PASS, exit 0, empty | `bf0d504` | 19:15:06 |
| `git diff --check c751610..HEAD`; name/status and fix-commit inspection | PASS, no whitespace errors; only the two expected code/test paths | `bf0d504` | 19:15:40 |
| `uv --version`; `uv run --offline --no-sync python -B -` for installed versions and Fraction documentation/source | PASS: uv 0.13.0, Python 3.12.15, pytest 9.1.1, tzdata 2026.5; exact integer-ratio constructor and integer rounding verified | `bf0d504` | 19:15:40–19:17 |
| `uv run --offline --no-sync python -B -`, exact-test/history, signed reproductions, golden/F1/F2/rule-snapshot probe | PASS execution, exit 0. Old behavior: F4 OverflowError, F5 AssertionError. HEAD: both tests PASS; 10 golden, 7 F1, 75 F2 rows PASS | `bf0d504`, old `c751610` in memory | 19:16:08 |
| Same offline Python command, independent scaled-integer oracle/matrices | PASS, exit 0: 16,674 cases; zero mismatches | `bf0d504` | 19:16:41 |
| Same offline Python command, explicit signed 496-second boundary display | PASS, exit 0; below/at/above outputs as recorded | `bf0d504` | 19:17:02 |
| `git diff --name-status HEAD^1 HEAD`; `git diff --exit-code HEAD^1 HEAD -- src tests pyproject.toml uv.lock` | PASS: seven docs-only merge paths; code/tests/dependencies empty, exit 0 | `bf0d504` | 19:17:02 |
| `git status --short`; `git diff --cached --exit-code`; `git diff --exit-code`; head/merge-base lookup; report `Test-Path` | PASS: clean worktree/index, unchanged HEAD, expected merge-base; report did not exist before writing | `bf0d504` | 19:17:02 |
| Initial `rg` lookup, followed by `Select-String -Encoding utf8` / explicit reads | BLOCKED lookup: `rg` not recognized; PASS fallback. No configuration changed | `bf0d504` | session setup, before 19:15 |

### Focused reproduction

Run the following from the repository root inside a PowerShell single-quoted
here-string piped to `uv run --offline --no-sync python -B -`.
It reproduces the actual test sensitivity, the integer oracle and selected
finite-extreme/large-hour/tolerance-boundary checks without writing files.

```python
import ast, pathlib, subprocess, sys, types
sys.path.insert(0, "src")
from sochron.timebase import OffsetClass, classify_offset

def oracle(xs, t):
    ratios = [v.as_integer_ratio() for v in [*xs, t]]
    scale = max(d for _, d in ratios)
    nums = [n * (scale // d) for n, d in ratios]
    ys, width = nums[:-1], nums[-1]
    if not ys:
        return ("unknown", None, 0)
    if all(abs(y) <= width for y in ys):
        return ("ok", None, len(xs))
    step = 3600 * scale
    q = (min(ys) + max(ys)) // (2 * step)
    fit = [h for h in (q-1, q, q+1, q+2)
           if h != 0 and all(abs(y-h*step) <= width for y in ys)]
    return ("shifted", fit[0], len(xs)) if len(fit) == 1 else ("unknown", None, len(xs))

old = types.ModuleType("core001_r3_old")
sys.modules[old.__name__] = old
path = "src/sochron/timebase/offset.py"
exec(compile(subprocess.check_output(
    ["git", "show", "c751610:" + path], text=True), "c751610:" + path, "exec"), old.__dict__)
tree = ast.parse(pathlib.Path("tests/unit/timebase/test_timebase_unit.py").read_text("utf-8"))
for name in ("test_classify_offset_survives_extreme_finite_magnitudes",
             "test_classify_offset_keeps_integer_hour_identity_beyond_float_precision"):
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    for label, fn, cls in (("old", old.classify_offset, old.OffsetClass),
                           ("HEAD", classify_offset, OffsetClass)):
        ns = {"classify_offset": fn, "OffsetClass": cls}
        exec(compile(ast.Module(body=[node], type_ignores=[]), name, "exec"), ns)
        try:
            ns[name]()
        except (OverflowError, AssertionError) as error:
            assert label == "old"
            print(name, label, type(error).__name__, str(error))
        else:
            assert label == "HEAD"
            print(name, label, "PASS")

import math
for sign in (-1, 1):
    cases = [([sign*1.7e308], 1e307), ([sign*1e308], 9e307),
             ([float(sign*2**53*3600)], 120.0)]
    for e in (60, 100, 500, 1011):
        cases.append(([float(sign*2**e*3600)], 120.0))
    x = float(sign*(2**53+1)*3600)
    for t in (math.nextafter(496.0, -math.inf), 496.0,
              math.nextafter(496.0, math.inf)):
        cases.append(([x], t))
    for xs, t in cases:
        got = classify_offset(xs, t)
        assert (got.kind, got.hours, got.samples) == oracle(xs, t)
        print(xs, t, got)
```

## Not checked (and why)

- No fresh audit of unchanged conversion/bar/session/rule implementations;
  their named tests were rerun. F1-F3 were not reopened; classifier regressions
  surrounding F4/F5 were checked as requested.
- No exhaustive enumeration of all floats. Finite float arithmetic is supported
  by the proof above plus the stated probes. Arbitrary non-float inputs, non-finite
  tolerance policy, huge input-sequence resource limits, all IANA zones and
  overnight-window policy are outside this re-review.
- No clean installation, online dependency refresh, type checker, Linux run,
  Python CI result or control-plane regression suite; no dependency/control code
  changed. Used the already-synced environment offline.
- No terminal/broker connection, market-data ingestion, Demo/live execution,
  strategy experiment, holdout, costs/risk gate, journal/reconciliation or deployment.
- Interactive `/review` is unavailable in this headless interface. Performed the
  manual contract/diff review and independent read-only mathematical review instead;
  the owner's explicit re-review and scan bases govern this round.
- No staging, commit, push, labels, merge, approval or PROGRESS update. The explicit
  one-report instruction supersedes the normal checkpoint edit. Only this report
  is written. Delivery remains **implemented**, with successful local re-review;
  this report does not promote task state to verified, merged or deployed.

Remaining action: the implementer can include this report in the normal handoff/PR
flow; the owner retains label/merge authority after the required checks.
F4/F5 require no further code change on the reviewed head.
