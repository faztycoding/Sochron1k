# Review SPIKE-001 round 2 · base main · head 82077e1 · reviewer Codex (headless, 2026-10-21 +07)

Rechecked F1–F5 from `docs/reviews/SPIKE-001-r1.md` against contract v1.1, each
requested fix commit (`git show 6b65c81`, `7d0b1b6`, `c6d84fd`, `1b6bdb5`,
`c7ad6d7`, `82077e1`), the complete current probe/tests, the evidence report and
round 4 JSON. Full reviewed head: `82077e1b3d03e97dc44e328ea5772ab0322b03a6`.
The re-review delta is `00a7bc7..82077e1`; the task base and `origin/main` resolve
to `0916776`, while local `main` is still `951ee98`. Older bootstrap changes in
the local-main comparison are not new spike findings.

Result: **F1, F2, F4 and F5 CLOSED; F3 OPEN; new F6 OPEN (Medium).** The exact
requested offline test command passed 19 tests. Round 4 supplies the missing
M1 DST observations, and its depth/count arithmetic is internally consistent.
Error-path proof and the claim of complete, usable M1 from 2017 remain deficient.
Finding closure does not mean every AC passes: AC-03 and AC-04 remain UNKNOWN.
The literal AC-07 scan also has the previously observed local-main false positive,
although the task-base mutation scan is empty.

Two read-only sub-reviews examined the code and evidence independently; the
findings below were checked against the files and calculations. Only this review
file is written. No probe invocation, terminal connection, staging, commit or push
was performed. This is a review, not approval or a claim of CI verification.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 — CLOSED | Medium | confirmed | `spikes/SPIKE-001/probe.py:204`, `:219`, `:297`; `spikes/SPIKE-001/test_probe.py:168` | `7d0b1b6` partitions every interval above 60 seconds into exactly one bucket. The monthly caller carries `prev_last` across successful empty months, adds each boundary once, and resets continuity on an error. Round 4 contains all five buckets; their sums match the report. | Cross-month gaps, empty intervening months and short missing-bar intervals. | The original silent omissions are corrected. | None for the original algorithm defect. Retain the test coverage limitations below. | Diff + passing bucket/carry regression + static confirmation of the monthly caller establish the behavior. The exact split-month weekend/empty-month regression matrix requested in r1 is not fully present; closure does not claim that matrix ran. |
| F2 — CLOSED | Medium | confirmed | `spikes/SPIKE-001/probe.py:321`, `:330`, `:342`; `spikes/SPIKE-001/test_probe.py:151`; `spikes/SPIKE-001/results/run4-20261021T0316.json:499` | `c6d84fd` obtains the first returned tick from a fixed 2005-01-01 bound, independently of M1. The January 20 regression returns January 20 while the supplementary month search returns February. Round 4 records 2026-01-01 23:05:00 and zero ticks in the preceding request; its supplementary January sample is positive. | History begins after the sampled mid-month hour, or ticks predate the M1-derived bound. | The primary first-tick result no longer comes from the unreliable month search. | None for this sampling defect; retain the bounded-result wording and address the separate error path under F3. | Diff + passing January 20 regression + round 4 confirm the primary fix. The constant lower bound removes M1 coupling by inspection. This proves the earliest tick returned for the request beginning 2005-01-01, not independently certified global server retention or continuous tick coverage. |
| F3 — OPEN | Medium | confirmed | `spikes/SPIKE-001/probe.py:299`, `:304`, `:314`, `:338`, `:341`; `spikes/SPIKE-001/test_probe.py:136` | `6b65c81` distinguishes errors from empty responses, but an errored earlier M1 month followed by a successful month still emits a definite `m1_first_month_with_data`. The new preceding-day tick request in `c6d84fd` converts failure to `ticks_in_day_before_first = null` without recording its error or marking the boundary check UNKNOWN; supplementary calls then run. | An early M1 request fails and later requests succeed; or the first-tick request succeeds but its preceding-day check fails. | The report can still present an unqualified depth boundary after an incomplete search/check, and the tick failure diagnostic is lost. A successful round 4 cannot prove these negative paths. | Separate earliest observed data from boundary/completeness status. Mark conclusions affected by failed requests UNKNOWN, and preserve the failed request bounds and sanitized error immediately. | **Not met.** Add mixed-success/error caller regressions: failed earlier M1 month followed by data; successful first tick followed by failed preceding-day request and successful later samples. Assert retained diagnostics, UNKNOWN affected conclusions, and distinct successful-empty behavior. Static counterexamples are detailed below; they were not executed. |
| F4 — CLOSED | Medium | confirmed | `docs/evidence/SPIKE-001.md:13`, `:57`, `:61`; `spikes/SPIKE-001/results/run4-20261021T0316.json:54` | `82077e1` consistently marks full AC-03 UNKNOWN and explicitly distinguishes observed bar gaps from authoritative trade sessions. JSON still contains only the unavailable-session explanation. | Reading the full-symbol-spec acceptance status. | Missing sessions are no longer hidden behind PASS. | None for this reporting defect; completing AC-03 still needs the missing evidence. | The allowed r1 resolution was a truthful UNKNOWN status. Summary, detailed section and follow-up agree; numerical fields remain supported. |
| F5 — CLOSED | Low | confirmed | `docs/evidence/SPIKE-001.md:88`, `:92`, `:94`, `:98`; `spikes/SPIKE-001/results/run4-20261021T0316.json:126`, `:222` | `c7ad6d7` replaces the exact-one-hour assertion with measured M1 open-to-open gaps and retains both exceptional dates: March 5, 21:57 + 68 min = 23:05; April 1, 20:57 + 79 min = 22:16. | Treating a typical pause as an exact session schedule. | The original exception-hiding and exact-duration claim are corrected. | None for the original defect. Causes of the exceptional gaps remain unmeasured. | Diff + recomputation from round 4 confirm both exceptions. Earlier M5 observations remain in run 3 (70 and 80 minutes; next opens 23:05 and 22:15); the new M1 result is not silently presented as the same-resolution observation. |
| F6 — OPEN | Medium | confirmed | `docs/evidence/SPIKE-001.md:16`, `:108`, `:138`, `:145`; `spikes/SPIKE-001/results/run4-20261021T0316.json:315`, `:319` | Introduced by `1b6bdb5`: the report claims full M1 and usable research data start in 2017. That year contains only 238,054 bars and 1,118 gaps of 15 min–3 h, compared with 347,537 bars and 205 such gaps in 2018. Annual summaries do not establish the date at which sufficiently complete M1 begins. | Using the report's proposed 2017 cutoff in the next data contract or research dataset. | A substantially anomalous year can be admitted as complete without investigating its coverage; the evidence overstates what the spike establishes. | Describe denser observations from 2017, explicitly retain its anomalous coverage, and leave the start of research-suitable M1 UNKNOWN pending finer data-quality evidence. Do not substitute an unmeasured 2018 cutoff. | Every summary and follow-up must distinguish first observed data, density and validated completeness. A claim of completeness needs evidence at the relevant time resolution; merely removing the unsupported claim can close this finding without another terminal run. |

### F3 static counterexamples and remaining proof

- **M1:** supply `None` with an IPC timeout for January, a successful February
  response containing bars, and successful empty responses thereafter. The helper
  returns an error; line 299 records it; line 304 still chooses February; line 314
  emits February without an UNKNOWN boundary status. The error list is useful
  partial progress, but does not meet r1's explicit requirement to mark the affected
  depth conclusion UNKNOWN. An error also resets gap continuity, so that summary
  must be identified as partial when errors exist.
- **Ticks:** let `copy_ticks_from` return a tick, the immediately following range
  call return `None`, and subsequent supplementary samples succeed. Lines 338–342
  retain the first observation, emit only a null preceding-day count, and never
  capture that call's `last_error()`. Retaining the observation is appropriate;
  treating the boundary check as complete or losing its diagnostic is not.
- The committed tests check a failing bar helper and all-failing tick requests.
  They do not exercise either mixed-success/error caller path. These are static
  counterexamples derived from the current control flow, not claimed test failures.
  Round 4 has no recorded monthly M1 errors, and its preceding-day tick call returned
  zero, so this finding does **not** allege that round 4 itself experienced those failures.

MetaQuotes documents a date-bounded tick request and `None` on error, with diagnostics
available through `last_error()`. These API contracts support the F2/F3 assessment;
they are not a fresh measurement of pinned package 5.0.6231 or server retention.
[copy_ticks_from](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py),
[copy_ticks_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py).

## AC status

PASS below is limited to the specified observation/test. UNKNOWN is not a passed
result, even where the contract permits reporting UNKNOWN. The successful depth
observations are distinguished from the incomplete F3 proof and F6 interpretation.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Round 4 records build 6274, broker/company, authorized server, USD, masked login and Demo mode 0 (`run4` lines 4–25). Connection was not repeated by this reviewer. |
| AC-02 | PASS | Exact requested offline suite: 19 passed. The original four refusal cases still require initialize → account_info → shutdown and no further report fields; expiry and failed initialization retain their negative checks. |
| AC-03 | UNKNOWN | Correct evidence status after F4. Numerical symbol fields match JSON; required authoritative trade sessions remain missing. Closing F4 does not complete AC-03. |
| AC-04 | UNKNOWN | Correct evidence status. Twelve samples span -3.800 to +0.865 seconds; integer tick seconds agree with millisecond timestamps, and all M1 minute offsets are zero. The GMT+0 case cannot distinguish the two API hypotheses, and Windows reports unsynchronized. These observations establish agreement with the workstation clock at the stated tolerance, not exact zero-second error or independently certified UTC. |
| AC-05 | PASS | Round 4 contains actual M1 for both required windows: 19,329 US bars and 17,887 EU bars, both with `call_error: null`. Last pre-break opens shift 21:57 → 20:57 across US DST and stay 20:57 across EU DST. This supports the report's unchanged zero-hour-offset interpretation for this server under the stated New York-session interpretation. It does not resolve AC-04, certify exact session hours, or establish behavior for other brokers. |
| AC-06 | FAIL | The observed dates and counts are supported: first returned M1 2014-01-14; sparse 2014–2016; first returned tick 2026-01-01 23:05 within the fixed search bound; gap totals agree. Full acceptance remains unsupported because F3's required failure-path proof is incomplete and the report overstates complete/usable M1 from 2017 (F6). This is not a rejection of those measured dates or an assertion of hidden errors in round 4. |
| AC-07 | FAIL | Against the contract's literal command `bash scripts/controls/red-flags.sh main`, the mutation group is not empty: it matches the scanner's own regex from older bootstrap history because local main is `951ee98`. The task-base scan against `0916776` (also current `origin/main`) has an empty mutation group and supports the report's scoped no-mutation claim. Unlike r1's task-scoped PASS, this row distinguishes literal command compliance from the successful scoped check. No new mutation path was found and no ref/config was changed. |

## Checked, nothing found (and how)

- **Evidence integrity:** round 4 parses; SHA256 is
  `ca81de33cc9e3b17ce86c2275e8fc92ff8cb59e1fc49cf72f7f81c014075146f`, matching
  the evidence prefix. `git diff --exit-code c6d84fd HEAD -- spikes/SPIKE-001/probe.py
  spikes/SPIKE-001/test_probe.py` is empty, linking the recorded round 4 code to the
  current code. This verifies artifact consistency, not independent capture provenance.
- **Depth arithmetic:** yearly M1 totals sum to 3,343,061, matching the positional
  count. Gap buckets sum to 185 / 26 / 2,886 / 63 / 1,483 (4,643 total). Counts in
  2014, 2015 and 2016 are 302 / 312 / 310; all observed intervals in those yearly
  summaries fall in the at-least-24-hour category, including carried year boundaries.
  These are sparse observations returned for M1, not twelve years of minute coverage.
  No evidence establishes continuous ticks throughout January–October 2026.
- **DST arithmetic:** typical M1 weekend pairs give 49 h 04 min; the US-transition
  pair gives 48 h 06 min, and the EU-transition pair gives 49 h 07 min. Exceptional
  daily next-open times are computed above. Small differences from M5 resolution
  are retained. The conditional DST interpretation is supported without inventing
  authoritative trading permissions.
- **Read-only boundary and scope:** the fix diff adds historical reads and reporting,
  not order/account mutations. Account-first validation, expiry and shutdown control
  flow remain intact. No existing assertion was removed or weakened to accommodate
  a refusal. Return-shape assertions changed with the documented helper return type.
  No dependency, lockfile, CI/control or application-package change occurs in the
  six fix commits. Earlier contract/control history is outside this re-review delta.
- **F01–F18 checklist within this delta:** F01/F08/F17 inform F3 and F6; F02 checked
  through the test diff; F03 hits are test fixtures; F04/F05/F18 have no dependency
  change; F06 scope is as above. No new destructive operation, embedded instruction,
  retry loop, strategy/backtest, holdout access or money/risk calculation was found.
  Supplied account identifiers remain masked; no credential store was read.

### Checks run

All times below are 2026-10-21, Asia/Bangkok (+07), at head `82077e1`.

The exact requested test command was:

```text
uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 pytest spikes/SPIKE-001 -q
```

| Command / procedure | Result | Commit | Time (+07) |
|---|---|---|---|
| Exact offline pytest command above | PASS: 19 passed, 1 warning in 0.03 s. `PytestCacheWarning`: could not create cache path, `[WinError 5] Access is denied`. Tests ran; no cache/config workaround or retry was made. Local paths are omitted. | `82077e1` | 03:21:31–03:21:32 |
| `git show` for all six requested commits; full current source/test/evidence/JSON inspection | PASS inspection; finding decisions above. | `82077e1` | 03:21–03:23 |
| `bash scripts/controls/red-flags.sh main` | PASS execution, exit 0; six hit groups. FAIL for the literal empty mutation-group criterion; scanner self-match only. | `82077e1` | 03:21–03:22 |
| `bash scripts/controls/red-flags.sh 0916776` | PASS execution, exit 0; mutation group empty; one fixture-text group. | `82077e1` | 03:22:06–03:22:07 |
| `git diff --check 00a7bc7..HEAD` | PASS, exit 0. | `82077e1` | 03:22 |
| `Get-FileHash spikes/SPIKE-001/results/run4-20261021T0316.json -Algorithm SHA256`; UTF-8 `ConvertFrom-Json`, `Measure-Object` and datetime arithmetic | PASS: digest prefix, bar/gap sums, 12-sample range and exception arithmetic agree with the supplied artifacts. | `82077e1` | 03:22 |
| `git diff --exit-code c6d84fd HEAD -- spikes/SPIKE-001/probe.py spikes/SPIKE-001/test_probe.py` | PASS, exit 0; probe and tests unchanged since the recorded run 4 code revision. | `82077e1` | 03:22 |
| PowerShell review structure/whitespace validation; `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD` | PASS: six finding rows, seven AC rows and required sections; no trailing whitespace; only this review is untracked, tracked/staged diffs empty and HEAD unchanged. | `82077e1` + review only | 03:25:13 |

Red-flag explanations:

- Task-base scan: only `FakeTerminal`, `RatesStub` and related fake/stub text in
  the contract-authorized spike test file. No mutation hit or control-file change.
- Local-main scan: skipped-test text is the existing Git Bash availability check;
  type/lint-disable text is policy/scanner definitions; placeholder text is scanner
  definitions and synthetic tests; destructive/bypass text is deny logic, negative
  cases and documentation. The mutation hit is the scanner regex itself. The many
  listed control files belong to prior bootstrap history. These explain the hits;
  they do not make the literal nonempty scan empty.
- `rg` is unavailable (`CommandNotFoundException`); file discovery used `git
  ls-files` and PowerShell. An initial read used the nonexistent shorthand contract
  filename; the actual `SPIKE-001-mt5-connectivity-time.md` was then located and read.
  Neither discovery failure affected pytest or required changing the environment.

## Not checked (and why)

- No probe execution, terminal connection, account operation or new market-data
  capture, as requested. No independent Windows clock synchronization, historical
  session source, terminal restart/cache diagnosis or server-retention measurement.
- No raw historical bar/tick snapshot is present: annual gap totals cannot be
  recomputed from original bars, or used to locate the exact research-suitable start.
  Gap causes (missing ticks, holidays, early closes or retrieval defects) are not
  established merely by these counts. Do not use those interpretations as validation.
- The F1 regression exercises the helper, not `history_depth` across an empty
  month. Its named first August timestamp is actually July 31 23:59. Static caller
  inspection supports the fix, but a future carry regression could escape this test.
- The F2 test does not assert the `copy_ticks_from` arguments or explicitly simulate
  ticks older than M1. The fixed bound/no-M1-argument implementation was checked
  statically. Supplementary month search still assumes contiguous availability.
- No before-fix checkout or mutation test was run; no code/tests were edited to
  reproduce F3. The proposed F3 negative checks remain unexecuted and are not passes.
- No CI, merge, deployment, owner acceptance or D-001 approval was verified. No
  PROGRESS.md edit or separate handoff was made because the owner authorized only
  this review file; this file is the handoff for Claude to address F3/F6 and record
  the checkpoint. Delivery state remains implemented, with incomplete verification.
