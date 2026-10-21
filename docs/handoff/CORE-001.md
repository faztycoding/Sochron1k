# CORE-001 test-author handoff

Prepared 2026-10-21, Asia/Bangkok (+07), by Codex in the test-author role.
Base/observed HEAD: `ee33524d55bceb227a11b48619804a848c1aa33f` on `feat/CORE-001-timebase` (unchanged).
Contract: `docs/contracts/CORE-001-timebase.md`, owner-approved v1.

## Outcome and delivery boundary

The requested acceptance, golden and architecture files are ready as an additions-only Git patch.
The patch is not applied. No repository test or source file, pyproject, dependency, index, branch
or commit was changed; nothing was staged or pushed. No broker connection was made.
The only repository files written by this run are this handoff and the ignored proposal patch.
The owner's explicit scratch/patch/handoff-only delivery instructions supersede the skill's
normal direct-test-write/commit steps and the general PROGRESS checkpoint requirement.

The source package did not exist when tests were authored, and its implementation, task source
diff, implementer handoffs and reasoning were not read. A supporting read-only agent checked
the contract and test artifacts; that assistance is not the D-006 fresh-session review.
Pre-existing untracked `docs/reviews/CORE-001-dependency-admission.md` was left untouched and unread.

Scratch root: `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/core001-tests`.
Run all delivered tests from the repository root: the acceptance helper adds `cwd/src` to
sys.path and the architecture test inspects `cwd/src`. Golden data loads by file path.
No `__init__.py` is needed: real pytest collection successfully collected all seven tests without one.

## Patch and exact post-apply hashes

Proposal: `docs/proposals/CORE-001-tests.patch` (directly under proposals; gitignored).
Patch SHA256: `d3b534c4cb0b2d89fb5ea96f7e0a7606abc1b2c97d3bb18ad02bab059de67351`.
UTF-8 without BOM, LF endings; exactly three new regular files, mode 100644; no deletions.
Hashes below were computed from scratch bytes; Git blobs came from `git hash-object <file>`
without `-w`, and were independently checked against Git's blob-header SHA1 formula.
No scratch Git repository or staging was used to construct the patch.

| Repository path | Expected SHA256 | Expected Git blob |
|---|---|---|
| `tests/acceptance/CORE-001/test_timebase_acceptance.py` | `d8ab439584d994d734258bfa84670be907dc30468946660965dbc88587ee10b1` | `5b8f9c77ead17f389378a20e6282b984ccafdc7d` |
| `tests/architecture/test_imports.py` | `8db42b818b8eb33e6cb5a029e45165c6c5849f75afdb6bcf93b5dccf1bc7574d` | `6cf0b3974b5c3ddae57f21bea40808439afd8c11` |
| `tests/golden/CORE-001/timebase_cases.py` | `11c9efe9c5e6d0309992d64340dcadb5ada4223914d3afc0a6d09650cb519cfb` | `83004962943cbf9f2bc57515665af0c0ff8859f9` |

`git apply --check docs/proposals/CORE-001-tests.patch` returned exit 0 at 08:13:08 +07.
`git apply --numstat` listed only 213 acceptance, 171 architecture and 265 golden added lines.

## Golden provenance and arithmetic

Expected answers never come from sochron.timebase. Python 3.12.15 with tzdata 2026.5 was verified
before use. The separate scratch `calculate_golden.py` prepares literal tables; `verify_artifacts.py`
independently checks those tables with stdlib datetime/zoneinfo and integer arithmetic, without
creating or importing any implementation. Neither script is included in the patch.

- `SPIKE_TICK`: the contract's raw 1792525992 is 2026-10-20 19:53:12 UTC; msc remainder 35
  gives 35,000 microseconds. `.999` is an additional last-millisecond fixture proving to_raw
  truncates instead of rounding. Synthetic offsets +7200 and -7200 subtract/add two hours.
- `ROUND_TRIP_ROWS`: 23 deliberately fixed, explicitly listed raw integers, no randomness:
  lower endpoint and its next second, 2000 leap day, five-year January points 2005..2095,
  and 2099-12-31 23:59:59 (upper endpoint minus one). The separate script converted the
  explicit UTC instants with stdlib datetime.timestamp; each row records the elapsed seconds.
- `NY_WINDOW_ROWS`: 30 rows computed with ZoneInfo('America/New_York') in the scratch script,
  including March 7/8/9 and October 31/November 1/2, 2026, four session edge minutes on the
  neighboring days and all existing edge instants on the transition days, both contract
  07:30 examples, and the repeated autumn hour. Each row states UTC, NY local time, EST/EDT
  and inside/outside. EST subtracts 5h; EDT subtracts 4h. March 8 02:59:59 local does not
  exist; its preceding transition point is 06:59:59 UTC = 01:59:59 EST, then 07:00 UTC =
  03:00 EDT. No nonexistent local instant was fabricated. Membership is judged at minute precision.
- `BANGKOK_ROWS`: hand arithmetic adds seven hours: 16:59:59 UTC is same-date 23:59:59;
  17:00:00 UTC is next-date 00:00:00. Independently checked with Asia/Bangkok zoneinfo.
- `M1_TO_M15_ROWS`: raw = 1792525980 + i*60, i=0..14. These are 19:53..20:07 UTC:
  first 7 map to raw 1792525500 (19:45); last 8 map to 1792526400 (20:00). This follows
  the contract's explicit formula; '15 consecutive M1 opens' does not mean one M15 bar.
  Each row shows its raw arithmetic and seconds subtracted. Extra rows cover aligned
  19:45, tick 19:53:12 (minus 492s), 19:59:59 (minus 899s), and exact 20:00 boundary.
- `TIMEFRAME_ROWS`: hand-calculated floors for all 19 allowed timeframes, with UTC midnight
  raw 1792454400 and each row's seconds since midnight. `SHIFTED_BAR` uses synthetic offset
  61s: subtract 61, floor to 900s, add 61 -> 1792525561. This catches ignoring the rule.
- `OFFSET_ROWS`: five AC-06 cases: abs(x)<=120 including both exact boundaries -> ok;
  (7080,7200,7320) differs from 2*3600 by (-120,0,+120) -> shifted(2);
  (0.5,7200,30) has no common hour -> unknown; empty -> unknown, samples=0;
  1800 is half an hour, outside every whole-hour tolerance -> unknown. Five additional
  literal rows check -2 hours, opposing whole hours, just above tolerance, and custom tolerance.

Supporting sources: SPIKE-001 evidence's measured offset zero, build 6274 and measurement period;
architecture section 8; H001's NY 03:00..15:59 window. H001 was absent on this branch, so only
its document at the contract's referenced commit was read with
`git show 0c392a9:docs/hypotheses/H001-m15-momentum-breakout.md`. No market-data ingestion occurred.

## AC mapping and current red status

Acceptance file A = `tests/acceptance/CORE-001/test_timebase_acceptance.py`.
Architecture file B = `tests/architecture/test_imports.py`.

| AC | File::test | What it proves | Current result |
|---|---|---|---|
| AC-01 | A::test_ac01_raw_utc_milliseconds_and_fixed_round_trips | Exact rule metadata, aware UTC, milliseconds, truncation, 23 raw round trips, offset sign | FAIL: sochron.timebase not implemented |
| AC-02 | A::test_ac02_new_york_window_across_both_dst_changes | NY conversion and minute-inclusive session across both DST changes; explicit window argument | FAIL: sochron.timebase not implemented |
| AC-03 | A::test_ac03_bangkok_calendar_day_changes_at_1700_utc | Local date and wall clock cross midnight at 17:00 UTC | FAIL: sochron.timebase not implemented |
| AC-04 | A::test_ac04_m1_and_tick_alignment_to_m15 | 15 M1 opens, tick/boundary, supported timeframes, synthetic offset, BadTimeframe 7/1441 | FAIL: sochron.timebase not implemented |
| AC-05 | A::test_ac05_reject_unknown_naive_out_of_range_and_mismatched_input | Declared error hierarchy, unknown server, all four datetime APIs reject naive, invalid raw and msc | FAIL: sochron.timebase not implemented |
| AC-06 | A::test_ac06_classify_offsets_without_mutating_time_rules | Five cases plus formula edges; sample counts, unchanged rule snapshots and all three frozen dataclasses | FAIL: sochron.timebase not implemented |
| AC-07 | B::test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io | Source existence, AST imports and clock/I/O patterns | FAIL: source directory does not exist |

## Checks (all on the unchanged HEAD above plus uncommitted scratch/proposal artifacts)

| Command | Result | Commit | Time (+07, 2026-10-21) |
|---|---|---|---|
| Pinned uv Python/version probe | PASS: Python 3.12.15, pytest 9.1.1, tzdata 2026.5 | `ee33524` | 08:07:32 |
| Exact requested red command, below | BLOCKED: pytest root collection PermissionError, exit 4 | `ee33524` | 08:10:19-20 |
| Pinned red command plus explicit scratch --rootdir | FAIL as intended: 7 failed, 0 collection errors, 0 skipped, exit 1 | `ee33524` | 08:10:31; final 08:12:48 |
| Pinned uv python calculate_golden.py / verify_artifacts.py | PASS: 3 files compile, all golden rows independently checked; AST 9 permitted + 35 forbidden probes | `ee33524` | 08:12:31 |
| bash scripts/controls/red-flags.sh main | PASS (exit 0): 0 pattern groups; existing AGENTS.md control change listed; untracked excluded | `ee33524` | 08:10:19-20 |
| node scripts/controls/check-locked-paths.mjs main | FAIL: 1 pre-existing AGENTS.md change vs merge-base 45c1ea5 needs owner label | `ee33524` | 08:10:19-20 |
| git apply --check docs/proposals/CORE-001-tests.patch | PASS, exit 0; no apply performed | `ee33524` | 08:13:08 |
| git apply --numstat docs/proposals/CORE-001-tests.patch | PASS: exactly the three intended added paths | `ee33524` | 08:13:08 |

The pinned command prefix used for the scratch helper scripts:
`uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 python <scratch>/<script>.py`.
Full red output was preserved through PowerShell Tee-Object into scratch logs.
The non-ASCII repository path is garbled in pytest's redirected Windows output; the actual
inspected path was the current repository's src/sochron/timebase. No path was changed to hide failure.

### Exact requested command: BLOCKED (retained separately)

```text
uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 pytest "C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/core001-tests/tests" -q -p no:cacheprovider
```

Pytest chose the common ancestor of invocation cwd and scratch arguments as root, then tried
to scan C:/Users/MSI. The sandbox denied that parent-directory read. No permission or config
was changed. This exact command remains BLOCKED; the scoped run below is supplemental evidence.

```text
uv : ERROR: found no collectors for C:\Users\MSI\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\a
e73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests
At line:2 char:1
+ uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama== ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (ERROR: found no...001-tests\tests:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError



=================================== ERRORS ====================================
_____________________________ ERROR collecting . ______________________________
..\..\..\AppData\Local\uv\cache\archive-v0\K-3caiQHBLxfDWPN\Lib\site-packages\_pytest\runner.py:361: in from_call
    result: TResult | None = func()
                             ^^^^^^
..\..\..\AppData\Local\uv\cache\archive-v0\K-3caiQHBLxfDWPN\Lib\site-packages\_pytest\runner.py:406: in collect
    return list(collector.collect())
           ^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\uv\cache\archive-v0\K-3caiQHBLxfDWPN\Lib\site-packages\_pytest\main.py:569: in collect
    for direntry in scandir(self.path):
                    ^^^^^^^^^^^^^^^^^^
..\..\..\AppData\Local\uv\cache\archive-v0\K-3caiQHBLxfDWPN\Lib\site-packages\_pytest\pathlib.py:954: in scandir
    scandir_iter = os.scandir(path)
                   ^^^^^^^^^^^^^^^^
E   PermissionError: [WinError 5] Access is denied: 'C:\\Users\\MSI'
=========================== short test summary info ===========================
ERROR ..\..\.. - PermissionError: [WinError 5] Access is denied: 'C:\\Users\\...
1 error in 0.09s
```

### Scoped red run on the final delivered bytes

Only --rootdir was added to keep collection inside the authorized scratch test tree; cwd
remained the repository root so the tests still targeted the absent repository implementation.

```text
uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 pytest "C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/core001-tests/tests" -q -p no:cacheprovider --rootdir="C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/core001-tests"
```

```text
FFFFFFF                                                                  [100%]
================================== FAILURES ===================================
____________ test_ac01_raw_utc_milliseconds_and_fixed_round_trips _____________
No module named 'sochron'

During handling of the above exception, another exception occurred:
AC-01: sochron.timebase not implemented (No module named 'sochron')
______________ test_ac02_new_york_window_across_both_dst_changes ______________
No module named 'sochron'

During handling of the above exception, another exception occurred:
AC-02: sochron.timebase not implemented (No module named 'sochron')
_____________ test_ac03_bangkok_calendar_day_changes_at_1700_utc ______________
No module named 'sochron'

During handling of the above exception, another exception occurred:
AC-03: sochron.timebase not implemented (No module named 'sochron')
___________________ test_ac04_m1_and_tick_alignment_to_m15 ____________________
No module named 'sochron'

During handling of the above exception, another exception occurred:
AC-04: sochron.timebase not implemented (No module named 'sochron')
______ test_ac05_reject_unknown_naive_out_of_range_and_mismatched_input _______
No module named 'sochron'

During handling of the above exception, another exception occurred:
AC-05: sochron.timebase not implemented (No module named 'sochron')
___________ test_ac06_classify_offsets_without_mutating_time_rules ____________
No module named 'sochron'

During handling of the above exception, another exception occurred:
AC-06: sochron.timebase not implemented (No module named 'sochron')
______ test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io _______

    def test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io():
        source_root = Path.cwd() / "src"
        findings = []
        for package in ("sochron.timebase", "sochron.core"):
            directory = source_root.joinpath(*package.split("."))
>           assert directory.is_dir(), f"AC-07: {directory} does not exist; implementation missing"
E           AssertionError: AC-07: C:\Users\MSI\Desktop\��ਤ��ҧ�\Sochron1k\src\sochron\timebase does not exist; implementation missing
E           assert False
E            +  where False = is_dir()
E            +    where is_dir = WindowsPath('C:/Users/MSI/Desktop/��ਤ��ҧ�/Sochron1k/src/sochron/timebase').is_dir

..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\architecture\test_imports.py:159: AssertionError
=========================== short test summary info ===========================
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\acceptance\CORE-001\test_timebase_acceptance.py::test_ac01_raw_utc_milliseconds_and_fixed_round_trips
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\acceptance\CORE-001\test_timebase_acceptance.py::test_ac02_new_york_window_across_both_dst_changes
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\acceptance\CORE-001\test_timebase_acceptance.py::test_ac03_bangkok_calendar_day_changes_at_1700_utc
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\acceptance\CORE-001\test_timebase_acceptance.py::test_ac04_m1_and_tick_alignment_to_m15
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\acceptance\CORE-001\test_timebase_acceptance.py::test_ac05_reject_unknown_naive_out_of_range_and_mismatched_input
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\acceptance\CORE-001\test_timebase_acceptance.py::test_ac06_classify_offsets_without_mutating_time_rules
FAILED ..\..\..\AppData\Local\Temp\claude\c--Users-MSI-Desktop-------------Sochron1k\ae73a189-359c-4302-bc45-421f865f8f01\scratchpad\core001-tests\tests\architecture\test_imports.py::test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io
7 failed in 0.08s
```

### Control outputs

```text

== Files changed since merge-base with main (45c1ea5) ==
M	AGENTS.md
M	DECISIONS.md
M	PROGRESS.md
M	SPEC.md
M	docs/architecture.md
A	docs/contracts/CORE-001-timebase.md
A	docs/handoff/D-001.md
A	docs/reviews/D-001-agents-r1.md
A	docs/reviews/D-001-design-r1.md
A	docs/reviews/D-001-design-r2.md
A	docs/reviews/D-001-design-r3.md

== Deleted or renamed test files ==
(none)

== Untracked files (not scanned; git add them first) ==
docs/reviews/CORE-001-dependency-admission.md

== Control files touched (need owner review) ==
AGENTS.md

Pattern groups with hits: 0. Every hit needs an explanation; a hit is not automatically wrong.
```

```text
Locked-path check · base main · head working tree · merge-base 45c1ea5 · 12 changed path(s) · 17 commit(s) checked
!! locked      M  AGENTS.md  (agent instruction file)
Result: FAIL: 1 control change(s) need owner approval (PR label "owner-approved-control-change").
Implementers must not change these paths; if the change is intended, the owner reviews it and applies the label.
```

The red-flag script scans the repository diff, not ignored proposal contents or unstaged scratch
tests. Its zero hits must not be interpreted as a content scan of the delivered patch. Candidate
test files were separately parsed, compiled, checked for forbidden skip markers and whitespace,
and inspected during test-author review. Controls must run again after Claude applies/stages tests.

## Architecture scope and contract questions left open

AST checks recursively inspect every Python file in both packages, reject absent/empty source,
check each import alias and resolved relative imports, reject third-party packages/MetaTrader5,
follow ordinary import and assignment aliases with function/class scope isolation, and reject
the named clock/I/O calls, socket imports/uses and os.environ access. Common extra clock/file/env
and urlopen/print paths are covered. Wildcard and dynamic imports are rejected because they
prevent verification of the declared static dependency boundary.

Internal same-package imports are allowed for the contract's explicitly planned __init__/rules/
convert/sessions/offset files. The only other project dependency is sochron.core; core may not
import timebase. This applies architecture section 8 to inter-package dependencies rather than
banning the planned package from importing its own files.

This is not a full Python dataflow or side-effect proof. Reflection/getattr, callbacks, aliases
through containers/factories, complex branch/rebinding/closure behavior and every possible stdlib
I/O API are not exhaustively resolved. Source review remains required. The no-auto-rule-change
check observes every tested classifier path and declared dataclass freezing; it cannot prove all
possible runtime paths. No implementation was available for a green run or implementation mutations.

Unspecified behavior is not guessed: hours for non-shifted OffsetClass results, malformed scalar
types, NaN/infinity or invalid tolerance, invalid zone names and overnight custom windows do not
have extra error contracts imposed here. The chosen raw sample list is fixed and explicit per
the owner's direct instruction; no randomness or new property-testing dependency is used.

## Scratch evidence hashes

These supporting files stay local and are not patch additions:

| Scratch file | SHA256 |
|---|---|
| `calculate_golden.py` | `7559d1bf61c08aa1bd14598a3a92613c5cc35f1b19b037a5a841a73f0edd5a71` |
| `verify_artifacts.py` | `ecd3e0749702e84f7b349f2f954c4866c24b6df07261c8c2b4f2001045cc030c` |
| `create_patch.py` | `31f11a5a7928b678201ba625d02706d10ef621e0f68b3e4db8fb4f6fa3284a0d` |
| `red-run.log` | `72bfcf4eb0490bda416ec44087896e2a4b06ef25aa9c280ea52c0034f3d9c2b7` |
| `red-run-final.log` | `5200283ddddd984aa2a51e69a0a959811b8eb2cdee99a0a3b79fcce669af6fff` |
| `red-flags.log` | `3ae739d60064ddd2332cb690a73b369c3bb998f097b1a7c055a4abb6e7fa3378` |
| `locked-paths.log` | `004f090ae1428f33e89c80046fcaa384473207377ddb5fa567c62e78f3aa3a76` |

## Next action and delivery state

Implemented: test-author artifact only. Patch validity and bounded red evidence verified locally;
CORE-001 behavior is still red, not verified/merged/deployed. Required exact-command evidence is
BLOCKED as above; the existing locked-path gate is FAIL, not a pass or authorization.

Claude: verify the proposal SHA256, apply through D-006, compare every applied file's SHA256
and git hash-object against this handoff, obtain fresh-session review, then stage and commit
the tests under the existing task workflow. Re-run tests and controls on the applied bytes;
implement only after the test handoff is reviewed. The owner retains label/merge authority.

Transcript formatting note: trailing whitespace in copied PowerShell output was removed
from this Markdown only. The hashed scratch log files retain the original output.
The initial final-delivery verifier at 08:14:35 +07 reported FAIL solely on transcript
trailing spaces; it had already verified patch reconstruction and the hashes.

Final delivery check: `uv run --offline --python 3.12 python <scratch>/check_delivery.py`
-> PASS (exit 0) -> `ee33524` + proposal/handoff -> 2026-10-21 08:14:53 +07.
It reconstructed all three patch additions byte-for-byte, checked SHA256 and handoff hash
entries, verified no repository test/source/pyproject was created, confirmed an empty index
and tracked diff, and confirmed HEAD unchanged. `git diff --check` -> PASS -> `ee33524`
-> 08:14:35 +07 (tracked diff empty). No control tests were rerun because control code was unchanged.


## Implementation (Claude Code), 2026-10-21

Order followed: tests committed red (`85d78bf`, fresh-session review `docs/reviews/CORE-001-tests-r1.md`) → D-012 accepted (`e39b0b0`) → environment (`3da18d1`) → implementation in the commit that adds `docs/evidence/CORE-001.md`.

- `src/sochron/timebase/` = `errors.py`, `rules.py`, `convert.py`, `sessions.py`, `offset.py`, `__init__.py`; `src/sochron/__init__.py` and `src/sochron/core/__init__.py` hold docstrings only (tests-r1 F3).
- `tests/unit/timebase/test_timebase_unit.py`: 12 implementer tests, unique basename (tests-r1 F4).
- `uv run pytest tests -q -p no:cacheprovider` → 19 passed, 0 skipped at 08:29:35 +07 on the first run after writing the module; no locked test was touched after `85d78bf`.
- Conversions use integer seconds and `timedelta` arithmetic, never `timestamp()`, so every round trip in AC-01 is exact.
- Nothing in the package reads a clock, performs I/O or imports `MetaTrader5` (AC-07 AST test green).

Please look hard at (review r1):
- Whether `check_aware` being public widens the contract's API (it is an addition, not a change).
- `classify_offset` rounding: `round(x / 3600)` uses banker's rounding at exactly ±0.5 h; the contract's cases never land there, say if that matters.
- `to_zone` with an unknown zone name raises the stdlib `ZoneInfoNotFoundError` (a `KeyError`), not a `TimebaseError`.
- `src/sochron/__init__.py` content (tests-r1 F3).

Next: Codex `$cross-agent-review CORE-001` (read-only) → `/fix-findings` → owner opens the PR with the label `owner-approved-control-change` (three locked test files) → merge.


## Findings response (Claude Code), review r1 · 2026-10-21

Review: `docs/reviews/CORE-001-r1.md` (committed `40920d3`). All times +07, Windows, `uv run --offline`.

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F1 | Accept | `5538617` | `uv run --offline pytest tests/unit/timebase/test_timebase_unit.py -q -p no:cacheprovider -k common_hour` → FAIL on `5546da0` (`classify_offset([1800.0, 5400.0], 1800.0)` gave unknown) at 08:41:18 · after the fix `uv run --offline pytest tests -q -p no:cacheprovider` → 20 passed at 08:42:34 |
| F2 | Accept (question answered below) | `b8c993d` | `… -k non_finite` → FAIL before the fix (`ValueError: cannot convert float NaN to integer`, `offset.py:51`) at 08:43:19 · after → 21 passed at 08:43:43 |
| F3 | Accept | `0b8475d` | `… -k window_bounds` → FAIL before the fix (03:00:00 excluded by `start = 03:00:59`) at 08:44:16 · after → 22 passed at 08:44:41 |

F1 implementation: `_common_whole_hour` takes, over all samples, the largest lower bound and the smallest upper bound of the whole hours that fit, then settles the candidates around those bounds with the contract's own inequality `|x − h×3600| ≤ tolerance`, so float division cannot be off by one at a boundary. Exactly one nonzero hour → `shifted`; none or several → `unknown`. The "several" case (for example `[5400.0]` at tolerance 1800 fits +1 h and +2 h equally) is not spelled out by the contract; `unknown` follows the module's never-guess rule and is asserted in the regression so the reviewer sees the choice. At the default tolerance of 120 s at most one hour can fit any sample, so every golden row keeps its result.

F2 answer: the contract defines `ok`, `shifted` and "everything else → unknown"; its error list has no entry for non-finite samples, and the classifier is a reporter that must not abort a measurement run. Non-finite samples (NaN, ±inf, alone or mixed with finite values) therefore return `unknown` with the original sample count, checked before any arithmetic. If the owner prefers a `TimebaseError` instead, that is a contract clarification for the next contract, not a code decision taken here.

Notes for the owner (not findings, nothing changed): a non-finite or negative `tolerance_seconds` is still undefined by the contract (inf → `ok` for finite samples, NaN → `ValueError`, negative → `unknown`); `to_zone` with an unknown zone raises the stdlib `ZoneInfoNotFoundError`. Both sit outside the contract's error list; say if either should become a `TimebaseError` in a later contract. The VS Code mypy diagnostic "Cannot find implementation or library stub for module named sochron.timebase" is editor configuration without `src` on its path, not a test or packaging defect; a `[tool.mypy]` section would be a `pyproject.toml` change that needs approval.

Suite after the three fixes: `uv run --offline pytest tests -q -p no:cacheprovider` → 22 passed, 0 skipped (acceptance 6, architecture 1, unit 15) on `0b8475d` at 08:44:41. `git diff 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture` is empty: locked tests untouched.

Next: Codex `$cross-agent-review CORE-001` round 2 re-checks F1–F3 only and writes `docs/reviews/CORE-001-r2.md`. Findings are closed by the reviewer, not here.
