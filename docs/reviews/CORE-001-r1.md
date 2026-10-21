# Review CORE-001 round 1 · base origin/main · head 5546da0 · reviewer Codex, fresh headless review session

Review scope: approved `docs/contracts/CORE-001-timebase.md` and the requested
`git diff origin/main..HEAD` on `feat/CORE-001-timebase`. Only this report may be written;
no implementation/test edits, staging, commit, push, or approval are authorized.

The first findings were written on 2026-10-21 at 08:33 +07 **before reading the handoff**,
as required by the review procedure. The handoff was then read in full, including
"Implementation (Claude Code)" and its "Please look hard at" list. F2 is classified as
a question after reconciling the handoff's explicit unspecified-input caveat.

**Result: two confirmed findings (F1 Medium, F3 Low), one Low question (F2).**
The existing suite passes, but it does not exercise F1 or F3. No Critical/High finding.
This report does not approve the task or change its delivery state.

Reviewed head: `5546da044aa88fc0a1d8a08b5771b8ec04d7865c`.
Base snapshot: `origin/main` = `20b7c641b23ecbec2e12f676a85ebf7cfbaa942e`.
Merge-base: `90278b4e7b120454038ecde8bd0d55ccbf5ed5ae`.
Environment: Windows, Python 3.12.15, uv 0.13.0, pytest 9.1.1, tzdata 2026.5.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `src/sochron/timebase/offset.py:35` | `classify_offset([1800.0, 5400.0], 1800.0)` returns `OffsetClass(kind='unknown', hours=None, samples=2)`. The contract's common hour is uniquely `h=1`: both distances from 3600 are exactly 1800; the all-near-zero condition is false. | A caller supplies a permitted custom tolerance of 1800 seconds or more and observations have different nearest rounded hours but share an hour within tolerance. | Valid evidence of a common whole-hour shift is misclassified as unknown. No maximum tolerance is specified in the API contract. | After the existing all-near-zero check, determine whether a common nonzero integer hour satisfies all sample intervals, rather than requiring independently rounded hours to match. Preserve the default-tolerance behavior. | Add a unit regression for this exact case expecting `shifted`, `hours=1`, `samples=2`, plus its negative mirror and existing default-tolerance rows; rerun the suite. |
| F2 | Low | question | `src/sochron/timebase/offset.py:35` | At default tolerance, `[float('nan')]` raises `ValueError: cannot convert float NaN to integer`; `[float('inf')]` and `[float('-inf')]` raise `OverflowError: cannot convert float infinity to integer`. The broad input type is `Sequence[float]`, but the test-author handoff explicitly leaves NaN/infinity behavior unspecified. | A measurement sequence contains a non-finite float. | A caller cannot infer from the current contract whether to handle an exception or an unknown classification. The exceptions are reproduced; a contract violation is not asserted because of that documented ambiguity. | Clarify the finite-input precondition or define an explicit non-finite outcome. If unknown is selected, guard before integer rounding and preserve sample count. This is a contract clarification, not a required invented error policy. | After the intended policy is settled, test NaN, both infinities, and finite/non-finite mixtures, checking the documented outcome and unchanged rules. |
| F3 | Low | confirmed | `src/sochron/timebase/sessions.py:33` | With `EntryWindow('UTC', time(3, 0, 59), time(15, 59, 59))`, `in_entry_window(datetime(2026, 10, 20, 3, 0, 59, tzinfo=UTC), window)` returns `False`. The input is at the inclusive start, and the contract requires minute precision (seconds ignored). | A valid custom window contains seconds or microseconds in its start time. Only the input datetime is reduced to minute precision. | The entire opening minute is incorrectly excluded. The built-in NY window is unaffected because its bounds have zero seconds. | Compare the hour/minute of all three operands consistently, including both window bounds. | Add a regression using the exact inclusive-start case and subsecond bounds, checking the minute before, the start minute, the last minute, and the next minute. |

## AC status

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | `test_ac01_raw_utc_milliseconds_and_fixed_round_trips`: SPIKE tick, 23 fixed raw values, 35/999 milliseconds, inverse conversions from aware zones and offsets +/-7200. Fixed rather than random values are the already-recorded tests-r1 F1 issue; no tests were changed here. |
| AC-02 | FAIL | The named NY/DST scenarios pass: 30 golden rows, both 2026 transitions, adjacent days, four window edges and the repeated autumn hour. The associated public custom-window minute-precision requirement fails F3, despite that green test. |
| AC-03 | PASS | Both Bangkok midnight cases and aware-zone conversions pass. |
| AC-04 | PASS | Fifteen M1 opens, tick edges, all 19 timeframes, shifted alignment, and unsupported timeframes pass. |
| AC-05 | PASS | Named unknown-server, naive-datetime, raw-range, and millisecond-mismatch refusals pass. |
| AC-06 | FAIL | All 10 locked offset rows, negative shifts, default/custom tolerance, rule snapshots and frozen-record checks pass. The general common-hour rule fails F1 at a permitted finite custom tolerance. F2 is a question, not the reason for FAIL. |
| AC-07 | PASS | Architecture test and all 19 tests pass; red-flag secret and order/account mutation groups are empty. |

The FAIL entries above concern the linked Inputs/outputs/errors requirements; they do
not claim that the named locked tests failed. The exact suite result is below.

## Checked, nothing found (and how)

- **API and integer arithmetic, apart from F1/F3:** names, argument names and defaults,
  dataclass field names/types, error hierarchy, and the sole measured rule match the
  contract. Raw bounds are inclusive 946684800 and exclusive 4102444800. `msc // 1000`
  is checked before the remainder is converted to microseconds. `to_raw` uses timedelta
  floor division, preserves offset sign, accepts aware non-UTC inputs, and checks its
  raw result range. `bar_open` implements the exact subtract-offset/floor/add-offset
  formula for all 19 timeframes; negative offsets and non-minute offsets are covered
  by independent probes. Inputs are never modified. Unsupported integer timeframes
  raise `BadTimeframe`; raw/msc float and bool rejection adds defensive unit coverage.
- **Awareness and DST:** manual source inspection, the locked golden rows and independent
  probes cover both autumn folds and the spring jump from 01:59:59 to 03:00:00 local,
  UTC and NY-local inputs, Bangkok midnight, and all four datetime-taking APIs rejecting
  naive values. A tzinfo whose `utcoffset()` is None is also rejected. No hand-written
  DST table exists in production; zoneinfo supplies the transitions.
- **Immutability and side effects:** `TimeRule`, `EntryWindow`, and `OffsetClass` are
  frozen dataclasses; `RULES` is a MappingProxyType over a dict with no retained mutable
  alias, and TIMEFRAMES_MINUTES is a frozenset. The classifier only allocates local
  values and a result; it has no path that changes a rule. No source reads a clock,
  calls filesystem/network/env operations, imports MetaTrader5, sends orders, reads
  holdouts, or journals/retries an external action. Timebase imports only stdlib and
  its own modules. Ordinary concurrent/duplicate calls share no mutable operational
  state and cause no external effects. Zoneinfo's normal timezone-data loading is the
  contract-mandated library behavior, not an added application I/O path.
- **tests-r1 F3 resolved for this source:** both `src/sochron/__init__.py` and
  `src/sochron/core/__init__.py` contain exactly one AST expression: a string docstring.
  Neither runs code or imports anything. This was checked structurally as well as by eye.
- **Meaningful unit coverage:** the 12 implementer tests add read-only mapping enforcement,
  rejection of non-integer raw/msc values, microsecond flooring, inverse range rejection
  under a shifted rule, bar idempotence/containment for every timeframe, and daily-bar
  alignment under a nonzero offset. Some endpoint, DST and Bangkok checks overlap the
  locked tests, but the suite is not merely duplicative. The unique unit basename
  avoids tests-r1 F4's collection collision. Neither suite exercises F1/F3.
- **No locked-test weakening:** full byte hashes and Git blobs below match the handoff,
  HEAD and `85d78bf`. The diff from that commit is empty for all three locked directories.
  No skip/xfail/only, removed assertion, altered expected value or test replacement was
  found. Golden fixtures remain independent literals; the implementation does not
  load them. The 15 M1 opens deliberately span 19:53..20:07, covering two M15 bars as
  required by the explicit formula (tests-r1 F2).
- **Dependency/environment scope:** project metadata, lock TOML and installed distribution
  metadata independently agree on exactly seven external packages: tzdata 2026.5,
  pytest 9.1.1, colorama 0.4.6, iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0 and
  pygments 2.21.0. The eighth lock record is the virtual local `sochron` project, not
  another dependency. Python is restricted to 3.12; package=false, no build-system,
  virtual="." and pythonpath=["src"] match D-012. No package was added or updated.
- **Scope and base movement:** the requested two-dot diff includes apparent removal of
  H001, its research memo and historical TOOLING reviews, plus SPEC/tool-registry
  reversions. `git diff 90278b4..HEAD` is empty for those paths: they exist only in
  origin/main's later history, not as CORE-001 deletions. No hypothesis was deleted by
  this branch. The red-flag script correctly uses the merge-base. DECISIONS/admission/
  contract/test-review documents outside the literal allowed-files list implement the
  contract's explicit planning/admission workflow; D-012 records owner authorization.
- **Handoff questions:** public `check_aware` is an additive helper within the authorized
  package and changes no contracted name or behavior. Unknown zone names raise
  ZoneInfoNotFoundError, reproduced locally; no custom unknown-zone error is specified.
  Banker's rounding at +/-1800 seconds is harmless at default tolerance (unknown),
  but the same algorithm violates the broader common-hour rule in F1. The two package
  initializers were verified as described above.
- **Failure-pattern checklist F01-F18:** checked per-AC evidence, test preservation,
  production fakes, dependency approval/pins, API usage, scope, duplicate modules,
  swallowed errors, side effects/secrets, destructive/bypass surfaces, embedded text,
  bounded review work, context separation, complexity, evidence-backed findings,
  delivery wording and toolchain drift. No separate finding beyond F1/F3 and question
  F2. No trading/execution/research path is implemented by this task.

### Locked-test identity

Each SHA256 equals the handoff; each Git blob equals the working bytes, HEAD and `85d78bf`.

| File | SHA256 | Git blob |
|------|--------|----------|
| `tests/acceptance/CORE-001/test_timebase_acceptance.py` | `d8ab439584d994d734258bfa84670be907dc30468946660965dbc88587ee10b1` | `5b8f9c77ead17f389378a20e6282b984ccafdc7d` |
| `tests/architecture/test_imports.py` | `8db42b818b8eb33e6cb5a029e45165c6c5849f75afdb6bcf93b5dccf1bc7574d` | `6cf0b3974b5c3ddae57f21bea40808439afd8c11` |
| `tests/golden/CORE-001/timebase_cases.py` | `11c9efe9c5e6d0309992d64340dcadb5ada4223914d3afc0a6d09650cb519cfb` | `83004962943cbf9f2bc57515665af0c0ff8859f9` |

### Red-flag groups

`bash scripts/controls/red-flags.sh origin/main` reported **1 pattern group with hits**:
"Type checks disabled", at `tests/unit/timebase/test_timebase_unit.py:33,43,45,47`.
These four type-ignore comments accompany intentional illegal mapping assignment,
float raw time, bool raw time and float msc in tests that assert rejection. Their
reason is reviewed here; no production type check or runtime assertion is suppressed.

The following nine pattern groups were empty: skipped/focused tests; lint disabled;
placeholder/mock production code; swallowed errors; possible secrets; secret-like
assigned values; destructive/bypass commands; client-exposed secret-like variables;
order/account mutation. Deleted/renamed tests: none. At scan time untracked files: none
(the report was written afterwards and remains untracked, as requested).

The separate control-file list contained `pyproject.toml`, `uv.lock`, and the three
locked tests. D-012 covers the environment files; the locked-path gate still reports
FAIL for the three Codex-authored tests until the owner's PR process supplies its
label. This expected gate result is not reported as a pass or bypassed.

### Commands and exact results

All times are 2026-10-21, Asia/Bangkok (+07); all runs target `5546da0`.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| `uv run --offline pytest tests -q -p no:cacheprovider` from repository root, with PYTHONDONTWRITEBYTECODE=1 | PASS, exit 0: **19 passed in 0.05s**, 0 skipped; 6 acceptance + 1 architecture + 12 unit | `5546da0` | 08:32:24 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; 1 pattern group, 4 explained hits; secret and order/account groups empty | `5546da0` | 08:32:24 |
| Inline Python reproductions below via `uv run --offline --no-sync python -B -` | FAIL F1/F3 contract behavior; F2 exception behavior observed; probe process exit 0 | `5546da0` | 08:33:00 |
| `Get-FileHash -Algorithm SHA256`, `git hash-object --no-filters`, `git rev-parse HEAD:<path>` and `git rev-parse 85d78bf:<path>` for the three locked tests | PASS: all match the handoff and each other | `5546da0` | 08:34:15 |
| `git diff --exit-code 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture` | PASS, exit 0, empty diff | `5546da0` | 08:34:15 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL, exit 1: exactly the three locked-test additions require owner PR label; 22 changed paths / 7 commits inspected | `5546da0` | 08:34:15 |
| `git diff --check origin/main..HEAD` | PASS, exit 0, no output | `5546da0` | 08:34:15 |
| `uv --version` | PASS, exit 0: uv 0.13.0 | `5546da0` | 08:34:15 |
| Inline AST/TOML/distribution/zone probes via `uv run --offline --no-sync python -B -` | PASS, exit 0: docstring-only initializers, exact seven pins, virtual project/pythonpath, golden counts, unknown-zone and default half-hour behaviors | `5546da0` | 08:34:16 |
| `git status --short`, `git diff --exit-code`, `git diff --cached --exit-code`, `git rev-parse HEAD`, `git ls-files --others --exclude-standard` | PASS: only this report is untracked; tracked diff and index empty; HEAD unchanged | `5546da0` | 08:36:12 |
| Inline report structure/whitespace check via `uv run --offline --no-sync python -B -` | PASS: all template sections, AC-01..AC-07 rows and no trailing whitespace | `5546da0` | 08:36:12 |

Reproduction inputs (run through the same offline/no-sync Python command with `src`
on sys.path; no files are written):

```python
import sys
sys.path.insert(0, "src")
from datetime import UTC, datetime, time
from sochron.timebase import EntryWindow, classify_offset, in_entry_window

print(classify_offset([1800.0, 5400.0], 1800.0))
# Actual: unknown / None / 2. Required by the common-hour rule: shifted / 1 / 2.

for value in (float("nan"), float("inf"), float("-inf")):
    try:
        print(classify_offset([value]))
    except (ValueError, OverflowError) as error:
        print(type(error).__name__, str(error))
# Actual: ValueError, OverflowError, OverflowError. Intended policy is question F2.

window = EntryWindow("UTC", time(3, 0, 59), time(15, 59, 59))
print(in_entry_window(datetime(2026, 10, 20, 3, 0, 59, tzinfo=UTC), window))
# Actual: False. Required at minute precision, and at the inclusive start: True.
```

## Not checked (and why)

- No Linux run, clean-environment installation, package-registry/vulnerability refresh,
  type checker, or Python CI run. Existing .venv and cache were used offline; dependency
  admission was checked as an authorization record, not repeated. No control-plane
  regression suite was rerun because no control code changed.
- No broker/terminal connection, market-data ingestion, live/Demo execution, strategy,
  costs, risk gate, holdout, or journal/reconciliation behavior: excluded by this contract.
- No exhaustive enumeration of all raw seconds, arbitrary user tzinfo subclasses,
  nonexistent local datetimes fabricated by attaching tzinfo, all IANA zones, or
  unbounded/adversarial input sizes. The AST test is a pattern-based check, not a
  complete proof against arbitrary Python reflection or every stdlib I/O API; actual
  production source was separately reviewed. Frozen dataclasses are the contracted
  mutation barrier, not protection from deliberate object.__setattr__/reflection.
- Malformed scalar types beyond the explicit raw/msc checks, invalid tolerances,
  overnight windows and invalid zone names have no additional invented error policy.
  Non-finite samples are recorded separately as F2. Float timeframe arguments are
  outside the declared integer-input API; no new rejection requirement was invented.
- The interactive `/review` slash command is not exposed in this headless tool
  interface. This was a manual contract/diff review with independent read-only
  arithmetic, test/environment and scope checks; it used the owner's specified
  origin/main two-dot diff, not the skill's generic main baseline.
- No approval, staging, commit, push, label, merge, deployment or PROGRESS edit. Only
  this report is written under the owner's explicit one-file authorization. Findings
  remain open; implementation is not promoted to verified/merged/deployed by this review.
