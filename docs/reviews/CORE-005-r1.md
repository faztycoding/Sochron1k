# Review CORE-005 round 1 · base main (`origin/main` `b7e0dd2`) · head `02b7c98` · reviewer Claude Code (Opus 5.5), fresh session, role swap (Codex out of quota until 2026-10-28 19:41)

Scope: `git diff origin/main...HEAD` (merge base `b7e0dd2`; the CORE-004 files that came in with merge `d97bd1f` are
not reviewed). Contract `docs/contracts/CORE-005-data-bars.md` v1.2 with the v1.1 items. Reviewed 2026-10-24
06:15–06:35 +07 on Windows 11, Git Bash, CPython 3.12 through `uv run --offline`. Probes ran from scratch scripts
outside the repository; nothing under `src/` or `tests/` was edited or copied. The commands for F1–F6 are under
"Reproduction".

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `src/sochron/data/snapshot/validate.py:117-123` | Reproduction F1 uses two overlapping download chunks: 03-10 23:45..03-11 00:13, then 03-10 23:59..03-11 00:29. `validate_m1` reports a single defect, `time_not_increasing` at 03-10 23:59, and `days` = `{2026-03-10: STOP, 2026-03-11: PASS}`. The 14 repeated M1 at 03-11 00:00..00:13 get no defect. In `aggregate`, the 00:00 M15 bar has `m1_count` 29, `tick_volume` 203 (105 without the copies) and flags `{}`. Second case: after a step back to 12:59, one repeat of 13:05 carries high 4010.000. The 13:00 M15 bar then has high 4010.000, `m1_count` 15 and flags `{}`, even though 13:14 is missing in session. Cause: both order checks compare a bar only with the bar just before it in input order (`:119`, `:121`). A repeat that follows a smaller time therefore counts as increasing. | Any input where a time repeats after a backward step, not next to its first copy. Concatenated overlapping downloads and merged files produce exactly this. | Breaks invariant `:75` (every defect has a code and a time; nothing is swallowed) and v1.1 item 5 (`aggregate` relies on the report's defects). The repeated M1 carry no code. The day that holds them can be PASS. Their M15 bar counts volume twice and can take its OHLC from a copy, with empty flags. A strategy that skips by flags or day status (goal `:20`, CORE-006) would trade on these bars. The owner accepted tests-r1 recommendation 4 ("STOP codes already make H001 skip that day"); that assumption does not hold here. | In `validate_m1`, keep the set of `time_raw` seen so far. Report `duplicate_time` (STOP) at every bar whose time was already seen, and leave the adjacent-equal case as it is (one defect, convention 5). A step back onto a seen time then carries both codes; the owner may prefer one (contract wording). Lower-memory alternative: compare with the running maximum instead of the previous bar. Reading the locked rows, none repeats a time non-adjacently, so the set version keeps them as they are (not run: that would need copies of locked files). | A unit test on the F1 series: `duplicate_time` at each of 03-11 00:00..00:13, `days` `{03-10: STOP, 03-11: STOP}`, the 00:00 M15 bar flagged `duplicate_time`. Full suite green. |
| F2 | Low | question | `src/sochron/data/snapshot/aggregate.py:22-23` | Reproduction F2: 13:00..13:13 plus a second 13:13 gives one M15 bar with `m1_count` 15 and flags `{duplicate_time}`, but no `incomplete`, although 13:14 is in session and missing. `_incomplete` returns False whenever `len(members) >= timeframe`. When the repeat is not reported (F1), the same bar has flags `{}`. | Duplicates, or an extra non-aligned M1, in a slot that also misses an in-session minute. | This follows the literal D1 rule (`:71`, "`incomplete` ถ้า `m1_count < timeframe` …"). tests-r2 (`CORE-005-tests-r2.md:71-73`) noted the case and relied on `duplicate_time` (STOP) being present; F1 shows it is not always present. A consumer that checks only `incomplete` for H001's "bar missing in the lookback" rule misses the bar. | Owner decides the wording: judge by distinct minutes present (`len(present) < timeframe` and a missing minute in session). Optionally add a flag when `len(members) > len(present)`. The locked v1.1 row (16 members, all 15 minutes present) keeps its expected flags `{duplicate_time}`. | A unit test on the F2 series expecting `{duplicate_time, incomplete}`. Suite green. |
| F3 | Low | question | `src/sochron/data/snapshot/aggregate.py:41-42`, `model.py:91-102` | Reproduction F3: a report made from 10 clean M1, used to aggregate 10 M1 with spread −1, gives flags `{incomplete}` only, with no `negative_spread`. The same report used under a rule with offset 7200 gives a bar at 11:00 UTC with no `time_rule_mismatch` flag, although every M1 was built under offset 0. The only binding is `report.m1_bars == len(bars)`. `ValidationReport` does not record its rule. | A report from another series of the same length (after filtering or reloading), or from another `TimeRule`. | Flags describe other data, silently. This is a caller error, hence Low. | Contract change by the owner: add `rule: TimeRule` to `ValidationReport` and refuse `rule != report.rule` (ValueError). For a same-length series, store and check a cheap fingerprint (first and last `time_raw`, or a hash of all of them). Or state the precondition in the contract. | Unit tests: other rule → ValueError; other series → ValueError. |
| F4 | Low | question | `src/sochron/data/snapshot/model.py:23-31`, `:61-77`, `:91-102`; `validate.py:51-52` | Reproduction F4: `ValidationReport((), {}, 1, None)` makes `aggregate` raise `AttributeError: 'NoneType' object has no attribute 'zone'`, not TypeError. `m1_bars=True` is accepted for one bar. `ClosureCalendar(daily_break=(time(17,0,59), time(18,0,1)))` is accepted, and `in_closure` treats 17:00:00 as closed because `_clock_minutes` drops the seconds. `Defect` and `ValidationReport` have no `__post_init__`. | A hand-built report or defect, or a calendar boundary with seconds. | Contract `:34` (wrong type, bool included → TypeError) is not applied to two public types. A configured calendar value is changed without notice. Only hand-built values reach this. | Exact-type checks in `Defect.__post_init__` and `ValidationReport.__post_init__` (TypeError). ValueError for calendar times whose second or microsecond is not 0. | Unit tests for each case. |
| F5 | Low | question | `src/sochron/data/snapshot/validate.py:28-37` | Reproduction F5: an M1 `Bar` with `m1_count` 7 constructs, and `validate_m1` reports no defect, day PASS. The contract says `m1_count: int # M1 = 1` (`:45`). | M1 input whose `m1_count` is not 1. | No effect on numbers today, because `aggregate` counts members rather than reading `m1_count`. A contract value is unenforced. | `require_bars` refuses a timeframe-1 bar whose `m1_count` is not 1 (ValueError). Do not put the check in `Bar`: `aggregate(..., 1, ...)` legitimately builds an M1 with `m1_count` 2 from an adjacent duplicate (probe: `[(1, 2, ['duplicate_time'])]`). | A unit test. |
| F6 | Low | confirmed | `src/sochron/data/snapshot/validate.py:68-79`, `:124` | Reproduction F6: 40 M1 alternating between 2024-01-02 and 2024-07-02 take 0.00 s with `max_gap_minutes` 5 and 11.05 s with 10**6 (15.21 s in an earlier run). `in_closure` costs about 3.0 µs per call (200,000 calls timed). The gap walk calls it once per missing minute until the count exceeds the limit. On sorted data the walk is bounded by the span: 250,000 M1 took 2.04 s with 10**6 and 1.18 s with 5. | Unsorted input together with a large `max_gap_minutes`; the argument has no upper bound. | Cost is about forward steps × min(gap, limit + closure minutes). With D3 = 5 it is linear. Low. | Skip the walk when the whole gap, `(t2 − t1)/60 − 1`, is ≤ `max_gap_minutes`, since it cannot exceed the limit. And/or count in-session minutes by calendar intervals instead of one minute at a time. | The F6 reproduction runs under 0.1 s with 10**6. Suite unchanged. |
| F7 | Low | confirmed | `docs/contracts/CORE-004-costs-hardening.md:4`, `docs/evidence/CORE-004.md:53-66`, `docs/contracts/CORE-006-strategy-h001.md` (new) | `git diff --name-status origin/main...HEAD` lists these three files. The allowed files (`:30`) do not include them, and the "files" section of `docs/evidence/CORE-005.md` (`:16-21`) does not list them. The commit bodies of `02b7c98` (Refs CORE-005, CORE-004) and `764cfe4` (PLAN-002, Refs CORE-005, CORE-006) explain them. | Opening the PR from this branch. | Docs only: the PR carries CORE-004 bookkeeping and the CORE-006 contract (handbook F06). | Name the three files and the reason in the PR body and in the evidence "files" section (AGENTS.md completion report item 4), or the owner accepts them. | The PR body and the evidence list them. |
| F8 | Low | confirmed | `tests/unit/snapshot/test_snapshot_unit.py:71-83`; contract `:106`; `docs/evidence/CORE-005.md:42` | `test_fifty_thousand_m1_validate_and_aggregate_quickly` builds 50,000 minutes, of which 34,380 are M1 bars (counted with the test's own filter). The contract plan (`:106`) says the unit test times 500,000 synthetic bars. The 500,000 figures in the evidence and in the test comment come from `perf_core005.py`, a scratch script that is not in the repository, so a third party cannot rerun that row. My own script gives the same order: 500,000 M1 validate in 1.93–3.31 s and aggregate in 0.60–0.89 s, depending on GC and process state. | Reading the test name or the evidence row. | A mild over-claim in a test name, and one evidence row that cannot be rerun. | Rename the test (for example `test_about_34k_m1_…`) or build 50,000 bars. In the evidence, state that the plan's 500,000-bar unit test became a scratch measurement, why (suite time), and what the script does. | The renamed test passes, and the evidence row says this. |
| F9 | Low | question | `.gitignore:37-40` | Rule reading only, because my `git check-ignore` run was BLOCKED (see "Not checked"). `!src/sochron/data/**/*.py` is the last rule that matches any `*.py` under `src/sochron/data/`. It therefore also re-includes names that earlier rules ignore: `.env.*` (`:3`) matches a file named `.env.py`. Data written out as Python (for example `rates_2024.py`) would also be tracked. Verified by command: `git ls-files src/sochron/data` shows only the five source files; `git status --ignored --short src/sochron/data` shows only the two `__pycache__/` directories; `git ls-files \| grep -iE '\.(parquet\|csv\|sqlite\|db)$'` finds nothing. Rules after the block (`journal/`, `*.parquet`, `*.sqlite`, `holdout/`, …) still win for the paths they match. | A credentials-named or data file saved as `.py` under `src/sochron/data/`. | Only contrived paths. Low. | Owner decision (`.gitignore` is a control file): add `src/sochron/data/**/.*` after line 40 so dot-files stay ignored. Optionally add a CI size check for files under `src/sochron/data/`. | `git check-ignore -v --no-index` on such a path names the new rule; the owner runs it, since my run was blocked. |

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | The 2 locked AC-01 tests pass (the 70-test CORE-005 subset passed, 0.45 s). In the code, `core/__init__.py:44-65` checks exact types, finiteness, the timeframe set, `tick_volume >= 0`, `m1_count >= 1` and a zero UTC offset, and sets no upper bound. F5 concerns an M1-only rule that the AC does not cover. |
| AC-02 | PASS | The golden, offset and v1.1 duplicate/out-of-order tests pass. The golden file is unchanged (blob `6f46d72c…`). 148 M1 → 11 M15, matching `bars_cases.py:38`, `:222-247`. As written (strictly increasing input plus one adjacent duplicate), the AC holds. F1 and F2 concern input shapes it does not cover. |
| AC-03 | PASS | All 26 AC-03 tests pass, and each code is traced in `validate.py:82-97`, `:119-128` and `:140`. The input is untouched (the tests compare snapshots; the code copies to a tuple). F1 shows a duplicate that gets no code. The AC gives one anomaly at a time, so its text still passes, but invariant `:75` does not. |
| AC-04 | PASS | The 23 AC-04 tests pass, covering both DST changes, the `max_gap_minutes` edges, `report.calendar` and off-grid closures. |
| AC-05 | PASS | The AC-05 test passes; the precedence is `_RANK` at `validate.py:23`, `:131-132` and `:141`. F1 can leave a day with hidden duplicates at PASS; the AC's mixed-defect input does not cover that. |
| AC-06 | PASS | `tests/architecture`: 13 passed, 0.37 s. I ran 58 planted mutants through the locked checker functions (on strings; nothing written to the repository): 56 were caught. The 2 misses are float in `data/__init__.py`, which v1.1 item 4 leaves outside the float ban. The contract's `open(...)` and `time.time()` mutations are caught in all 5 files. |
| AC-07 | UNKNOWN | Locally PASS: `uv run --offline pytest tests -q -p no:cacheprovider` → `2870 passed in 9.87s`, no skips, at `02b7c98`, 2026-10-23T23:16:51Z–23:17:02Z (06:16–06:17 +07). The CI `python-tests` job has not run, because there is no PR yet. |

## Checked, nothing found (and how)
- **Diff and controls.** `git diff --name-status origin/main...HEAD` (21 files): no `pyproject.toml` or `uv.lock` change and no deleted tests. Locked files are unchanged since red. Acceptance blob `f3273a15…`, SHA256 `ec99d21b…`; architecture blob `1319cce4…`, SHA256 `2d3d05d3…`; golden blob `6f46d72c…`. These equal the handoff and tests-r2 values (`git rev-parse HEAD:<path>`, `git hash-object`, `sha256sum`). `6bd9ef8` is an ancestor of HEAD (`git merge-base --is-ancestor`). `src/sochron/core/__init__.py` was last committed by the owner as `7fd6fe1`. Its message, "f", has no type, scope or Refs (AGENTS.md "Git"); I recorded this, not as a finding, because the commit is the owner's.
- **Interface rows.**
  - Field order and types of `Bar`; frozen and slots. `core.TIMEFRAMES_MINUTES` equals the timebase set, enforced by a unit test.
  - The `Severity` and `DayStatus` Literals.
  - The `Defect` fields, and `ClosureCalendar` with its checks: weekday 0..6, naive times, and an unknown zone refused through `timebase.to_zone`.
  - `H001_CLOSURES`: `America/New_York`, 17:00–18:00, `(4, 17:00)` → `(6, 18:00)`, provenance "assumed [A] …".
  - `ValidationReport` with `calendar`, and `days` as a `mappingproxy` over a fresh, sorted dict.
  - `aggregate` returns a tuple in open-time order.
- **D1 rule** (`aggregate.py:44-70`): open from the first M1, high max, low min, close from the last M1, `tick_volume` summed, `spread` from the last M1 (None kept), `m1_count` = number of members. Empty slots are not created. Flags are the defect codes grouped by `bar_open(defect.time_raw)` plus `incomplete`. Members are sorted stably by `time_raw`.
- **v1.1 items 1–5**: each traced in the code and in a passing locked test.
- **Wrapping calendars.**
  - A weekend from Sunday 22:00 to Monday 01:00 (UTC zone) gives closed = False / True / True / False at Sun 21:59 / Sun 22:00 / Mon 00:59 / Mon 01:00.
  - A daily break from 23:30 to 00:30: covered by the implementer's unit test.
  - `start == end` windows are empty (Fri 17:00 is not closed).
- **DST gaps and overlaps.** A 02:00–03:00 New York break does not occur on 2026-03-08 and occurs once on 11-01. A 01:00–02:00 break is closed for 120 minutes on 11-01. This is wall-time behaviour through zoneinfo. H001's weekend covers both Sunday transitions, so H001 is not affected.
- **`empty_weekday` at month and year ends.** 2026-12-31, 2027-01-01 and 2027-01-04 are UNKNOWN; 2026-03-02 is UNKNOWN. Saturdays and Sundays are not keys.
- **Other timeframes.** One EDT week of in-session M1 gives 115 H1 bars and 6 D1 bars, none flagged. D1 counts: Sun 120, Mon–Thu 1380, Fri 1260.
- **Raw time out of timebase's range.** `Bar(time_raw=0, …)` constructs. `validate_m1` raises `RawTimeOutOfRange` (a ValueError), and `aggregate` refuses the report before reaching `bar_open`. Both are loud. The owner accepted tests-r1 recommendation 1, "leave the raw range to timebase" (`CORE-005-tests-r1.md:95`).
- **Non-minute-aligned bars and the gap counter.** The counter floors to the minute before counting, so a 13:05:30 bar is followed by a count from 13:06. Under a rule with a 30 s offset, every bar is `not_minute_aligned`, because alignment is judged on UTC.
- **Time conversion only through timebase.** `grep -nE 'utcoffset|timestamp|ZoneInfo|astimezone|tzinfo|offset_seconds|3600|86400|datetime\.now|utcnow|// 60|\* 60'` over `core` and `data` finds only `to_utc`, `to_zone` and `bar_open` calls. The rest is wall-clock minute arithmetic after `to_zone` and a raw minute index inside a slot (`aggregate.py:24`). No offset is computed by hand.
- **Mutation and shared state.** `require_bars` copies the input to a tuple, and the bars are frozen. `_RANK` is read-only, `H001_CLOSURES` is frozen, and reports are built from local dicts. Two calls on the same input give equal results (locked tests).
- **Error types.** A generator, dict or str as `bars` → TypeError. M15 bars passed to `validate_m1` → ValueError. Every other wrong argument is covered by the locked AC-03 type test.
- **`src/sochron/data/__init__.py`**: a docstring only, and it passes the locked package-init checker.
- **Performance.** Fresh-process scaling, GC on, at 250k / 500k / 1M / 2.5M M1: `validate_m1` 0.75 / 1.93 / 6.81 / 16.63 s and `aggregate` M15 0.19 / 0.85 / 1.76 / 4.61 s. Within one process, slices of a 1M series run at a flat 6.2–7.2 µs per bar, so the growth from 3 to 7 µs per bar comes from the larger heap, not from the algorithm. Gaps of two weeks and three months, weekends, and months without bars add no super-linear term (500,000 M1 with three holes: validate 3.31 s, aggregate 0.89 s, 77 defects). A nearly-closed calendar with 2 bars 60 days apart takes 0.17 s. The one super-linear case is F6.
- **Evidence numbers.** `2870 passed` reproduced (9.87 s against the 10.03 s stated). 148 M1 → 11 M15 matches the golden file. 2855 + 15 unit tests (core 2, snapshot 13) = 2870. The 500,000 timing is reproduced in order of magnitude (F8 covers whether it can be rerun). Evidence `:52` says "breaks of 67 minutes or more" and `model.py:82` says "66+ minute breaks". They agree once read as time difference against missing minutes: 16:57 → 18:04 is a 67-minute difference with 66 minutes missing, 6 of them in session, so WARN. AC-07 is reported as "PASS ในเครื่อง · CI รอ PR", which does not over-claim.
- **Red flags.** `bash scripts/controls/red-flags.sh origin/main` → exit 0 with 1 pattern group (Lint disabled). All 4 hits are the word "noqa" in prose: `docs/evidence/CORE-005.md` ×1, `docs/handoff/CORE-005.md` ×2, `docs/reviews/CORE-005-tests-r1.md` ×1. None is in code. "Control files touched": `.gitignore` plus the three locked test files, which came in through the D-006 patches, so the owner's label is needed.

## Reproduction (F1–F6)
Save the following as a file outside the repository and run `uv run --offline python -I <file>` from the repository
root. Output at `02b7c98`, 2026-10-23T23:28Z:
`F1 [('time_not_increasing', '03-10 23:59')] {'2026-03-10': 'STOP', '2026-03-11': 'PASS'}` ·
`F1 [('03-10 23:45', 16, 112, ['time_not_increasing']), ('03-11 00:00', 29, 203, []), ('03-11 00:15', 15, 105, [])]` ·
`F1/F2 [... ('03-10 13:00', 15, 105, [])] high of 13:00 = 4010.000` · `F2 [('03-10 13:00', 15, 105, ['duplicate_time'])]` ·
`F3 [('03-10 13:00', 10, 70, ['incomplete'])]` and `[('03-10 11:00', 10, 70, ['incomplete'])]` ·
`F4 AttributeError 'NoneType' object has no attribute 'zone'`, `[('03-10 13:00', 1, 7, ['incomplete'])]`, `True` ·
`F5 [] {2026-03-10: 'PASS'}` · `F6 … max_gap 5: 0.00 s`, `… max_gap 1000000: 11.05 s`.

```python
import sys; sys.path.insert(0, "src")  # run from the repository root
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from time import perf_counter
from sochron.core import Bar
from sochron.data.snapshot import H001_CLOSURES, ClosureCalendar, ValidationReport, aggregate, validate_m1
from sochron.data.snapshot.validate import in_closure
from sochron.timebase import rule_for, to_utc

R = rule_for("Exness-MT5Trial14"); P = Decimal("4000.000")
def m1(t, rule=R, **kw):
    raw = int(t.timestamp()); return replace(Bar(raw, to_utc(raw, rule), 1, P, P, P, P, 240, 7, 1), **kw)
def run(t, n, rule=R): return [m1(t + timedelta(minutes=k), rule) for k in range(n)]
def utc(*a): return datetime(*a, tzinfo=UTC)
def show(res): return [(a.bar.time_utc.strftime("%m-%d %H:%M"), a.bar.m1_count, a.bar.tick_volume, sorted(a.flags)) for a in res]

# F1: overlapping download chunks; chunk 1 ends 03-11 00:13, chunk 2 restarts at 03-10 23:59.
bars = run(utc(2026, 3, 10, 23, 45), 29) + run(utc(2026, 3, 10, 23, 59), 31)
rep = validate_m1(bars, R, H001_CLOSURES, 5)
print("F1", [(d.code, to_utc(d.time_raw, R).strftime("%m-%d %H:%M")) for d in rep.defects], {str(k): v for k, v in rep.days.items()})
print("F1", show(aggregate(bars, 15, R, rep)))
# F1/F2: one non-adjacent repeat with a spiked high hides both the spike and a missing in-session minute.
bars = run(utc(2026, 3, 10, 13, 0), 14) + [m1(utc(2026, 3, 10, 12, 59)), m1(utc(2026, 3, 10, 13, 5), high=Decimal("4010.000"))]
rep = validate_m1(bars, R, H001_CLOSURES, 5)
res = aggregate(bars, 15, R, rep)
print("F1/F2", show(res), "high of 13:00 =", res[1].bar.high)
# F2: adjacent duplicate pads a slot that misses 13:14 (in session).
bars = run(utc(2026, 3, 10, 13, 0), 14) + [m1(utc(2026, 3, 10, 13, 13))]
print("F2", show(aggregate(bars, 15, R, validate_m1(bars, R, H001_CLOSURES, 5))))
# F3: a report of other bars of the same length, and of another rule, is accepted.
clean = run(utc(2026, 3, 10, 13, 0), 10)
dirty = [replace(b, spread=-1) for b in clean]
rep = validate_m1(clean, R, H001_CLOSURES, 5)
print("F3", show(aggregate(dirty, 15, R, rep)))
shifted = replace(R, server="synthetic", offset_seconds=7200, version="t")
print("F3", show(aggregate(clean, 15, shifted, rep)), "(no time_rule_mismatch flag; bars were made under offset 0)")
# F4: value types the functions trust.
for report in (ValidationReport((), {}, 1, None), ValidationReport((), {}, True, H001_CLOSURES)):
    try:
        print("F4", show(aggregate([m1(utc(2026, 3, 10, 13, 7))], 15, R, report)))
    except Exception as error:
        print("F4", type(error).__name__, error)
secs = ClosureCalendar(zone="UTC", daily_break=(time(17, 0, 59), time(18, 0, 1)), weekend=H001_CLOSURES.weekend, provenance="t")
print("F4 17:00:00 closed under a 17:00:59 break:", in_closure(utc(2026, 3, 10, 17, 0), secs))
# F5: an M1 bar that says it holds 7 M1.
odd = m1(utc(2026, 3, 10, 13, 0), m1_count=7)
print("F5", [d.code for d in validate_m1([odd], R, H001_CLOSURES, 5).defects], dict(validate_m1([odd], R, H001_CLOSURES, 5).days))
# F6: unsorted input with a large max_gap_minutes walks every missing minute.
early = run(utc(2024, 1, 2, 13, 0), 20); late = run(utc(2024, 7, 2, 13, 0), 20)
mixed = [b for pair in zip(early, late) for b in pair]
for gap in (5, 10**6):
    began = perf_counter(); validate_m1(mixed, R, H001_CLOSURES, gap); print(f"F6 40 alternating bars, max_gap {gap}: {perf_counter() - began:.2f} s")
```

## Not checked (and why)
- **`git check-ignore -v -n --no-index` on probe paths under `src/sochron/data/`: BLOCKED.** guard-bash refused the
  command with "Blocked by .claude/hooks/guard-bash.mjs: the command references a .env file. Agents never read
  credentials; use .env.example for variable names." One of the probe paths was a dot-env name under
  `src/sochron/data/`. Per CLAUDE.md I stopped that step and did not rerun a reworded command. The `.gitignore`
  claims above (F9, and the parquet/csv/pyc/root `data/` rules) therefore rest on reading the rules, plus
  `git ls-files` and `git status --ignored` on what exists. The evidence row at `docs/evidence/CORE-005.md:40` is
  not re-verified by command.
- **Locked tests against a fixed copy of the code.** Not run, because it would need copies of locked files. That
  the F1 and F2 fixes keep the locked rows green is based on reading the rows.
- **CI on Linux.** There is no PR run yet.
- **Real market data.** Forbidden before ENV-1.
- **The evidence claim that `7fd6fe1` matches the implementer's draft byte for byte.** The draft is not available
  to me.
- **Behaviour under other tzdata versions.** Only the pinned `tzdata==2026.5` environment was used.

Ready for PR: no. F1 (Medium) breaks the contract's no-silent-defect invariant on a realistic input shape.
Findings open: 9 (F1 Medium confirmed; F6, F7, F8 Low confirmed; F2, F3, F4, F5, F9 Low questions for the owner).
