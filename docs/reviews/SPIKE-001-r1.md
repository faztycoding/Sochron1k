# Review SPIKE-001 round 1 · base 0916776 · head 00a7bc7 · reviewer Codex (headless, 2026-10-21 +07)

Reviewed contract v1.1 and the complete requested diff:
`git diff 0916776..HEAD -- spikes docs/evidence docs/contracts/SPIKE-001-mt5-connectivity-time.md`.
Full reviewed head: `00a7bc7ef8349b06cae2d39830ca4c78cb16d142`.
The working tree and index were clean at entry. Two read-only sub-reviews independently checked
the probe and the evidence; their observations were checked against the files before inclusion.
Only this review file was written. No staging, commit, push, probe execution, or terminal connection.

Result: five confirmed findings (four Medium, one Low). The account-first/read-only behavior is
supported, and the requested offline tests pass. The history survey and acceptance summary need
correction before these results can be treated as complete evidence for D-001. This is a review,
not approval or a claim of CI verification.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `spikes/SPIKE-001/probe.py:266`, `:274`; `docs/evidence/SPIKE-001.md:99` | Gap pairs are formed separately inside each monthly request. The previous month's final bar is discarded. Intervals of 120–300 seconds also enter no reported category. Run 3 reports 14 long gaps, 56 medium gaps and one other gap, but these are an incomplete census. | Put a final bar at 2026-07-31 20:59 UTC in July and a first bar at 2026-08-02 22:00 UTC in August. Neither monthly list contains that pair; its 49 h 01 min gap is omitted. Within a month, `[t, t+120]` is also omitted. | AC-06 can report an apparently complete gap summary while losing weekend outages, cross-month defects and short missing-bar intervals. The stored summaries do not contain enough boundary detail to repair the totals independently. | Carry the previous nonempty interval's last timestamp into the next comparison, including across empty months. Account for every interval longer than one M1 bar, with an explicit short-gap category. Until recomputed, label the old totals incomplete. | Add fixtures for the split-month weekend, an empty intervening month and 2–5 minute intervals. Each must appear exactly once; preserve existing gap categories and the out-of-range regression. These are proposed regressions, not tests executed in this review. |
| F2 | Medium | confirmed | `spikes/SPIKE-001/probe.py:294`, `:314`, caller `:282`; `docs/evidence/SPIKE-001.md:97`, `:121` | The search observes only one mid-month weekday hour, then labels the answer `first_month_with_ticks`. Even contiguous history beginning January 20 gives an empty January 15 sample and a positive February 16 sample, incorrectly identifying February. The lower search year is derived from M1 availability, which does not establish a tick-history bound. Run 1 reports June first with May empty; run 3 reports February first with 16,656 ticks in May. | History starts after the sampled hour; an earlier month is not sampled; or M1 retention is shorter than tick retention. | Neither the first available tick day required by AC-06 nor even the first available month is established. February is an observed positive sample, not proof of an eight-month historical boundary. | Report the earliest positive sampled interval, the sampled negative intervals, and the true first available day as UNKNOWN. If exact depth is needed, use a separately bounded search and refine the boundary; do not derive the tick lower bound from M1. Retain the earlier contradictory observations. | A synthetic history starting January 20 must not claim February as the true start. Test ticks older than the earliest M1 year. Revised evidence must distinguish sampled availability from actual earliest history. |
| F3 | Medium | confirmed | `spikes/SPIKE-001/probe.py:177`, `:259`, `:298` | Both range helpers collapse `None` into empty data. Monthly history does not retain errors for those calls; tick search treats the error as a negative binary-search observation. MetaQuotes documents `None` as an error, distinct from a successful empty result (references below). | Have a range call return `None` with a timeout/IPC error, then let later requests succeed. The month is counted as absent or the tick lower bound advances, and `run()` still returns exit 0. | A retrieval failure can become a false retention boundary or a false empty-history claim. The May zero-to-positive change between runs cannot be diagnosed because per-probe errors were not preserved; it does not itself prove an error occurred. | Preserve request interval, success/empty/error status and a sanitized error for each failed request. Mark affected depth conclusions UNKNOWN; never use an errored request as evidence of absence. No automatic retry or terminal operation is required to make the report truthful. | Separate fake `None` and successful-empty responses for bars and ticks. Assert that only the latter counts as no data and that any failed boundary request prevents a definitive first-history conclusion. |
| F4 | Medium | confirmed | `docs/evidence/SPIKE-001.md:13`; `spikes/SPIKE-001/results/run3-20261021T0301.json:54` | AC-03 explicitly includes trade sessions. All three JSON files contain only an explanation that the Python API does not expose them. The summary nevertheless labels AC-03 PASS with an exception. Observed bar gaps are not recorded authoritative trade sessions. | Consume the owner summary as acceptance evidence for the full symbol specification. | A required part of AC-03 is missing despite the PASS label. This matters to subsequent session/time rules. | Mark overall AC-03 UNKNOWN/incomplete and retain the supported numerical fields separately. Obtain sessions through a separately authorized evidence source if the criterion is to be completed; this review does not authorize a new connection or amend the contract. | Every required AC-03 field has cited evidence before full PASS, or the summary consistently leaves the missing sessions UNKNOWN. |
| F5 | Low | confirmed | `docs/evidence/SPIKE-001.md:56`, `:79`, `:84` | The prose generalizes the daily break to exactly one hour. Run 3 lines 139–141 instead show March 5 at 21:55 with a 70-minute open-to-open gap; lines 249–251 show April 1 at 20:55 with an 80-minute gap. The next bar opens are 23:05 and 22:15, respectively. | Interpret the typical M5 pattern as an exact daily session schedule. | The summary hides observed exceptions of 5 and 15 minutes beyond the usual 65-minute open-to-open gap. It can encourage treating a data gap as an established market closure. The broad US-DST interpretation is unaffected. | Describe the one-hour pause as the typical pattern inferred at M5 resolution, list these exceptions, and leave their causes UNKNOWN. Do not infer exact trading permissions from missing bars. | Recompute next-bar times from each stored `break_after_bar_as_if_utc` and `gap_minutes`; the report must retain both exceptions without claiming their causes were measured. |

## AC status

Statuses below describe what is established by the contract and evidence. UNKNOWN does not count
as a proven result. AC-05 explicitly permits an UNKNOWN outcome with reasons, so its M1 limitation
alone is not a requirement to reconnect or repeat the experiment.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | All three JSON files record terminal build 6274, broker/company, authorized server, USD, masked login and Demo mode 0. This is verification of the supplied artifacts, not an independently repeated connection. |
| AC-02 | PASS | The offline suite passes 15/15 overall. Four parametrized refusal cases assert exactly initialize → account_info → shutdown and no other report fields; expiry asserts no calls; initialization failure asserts only initialize and last_error. Static control flow agrees. |
| AC-03 | UNKNOWN | Numerical symbol fields match JSON, but required trade sessions are unavailable; full PASS is unsupported (F4). |
| AC-04 | UNKNOWN | The narrow observation is supported: nine tick-ms offsets span -0.246 to +0.733 s, integer tick seconds agree with the millisecond values, and all nine M1 minute offsets are zero. The requested UTC-versus-server distinction cannot be identified on this GMT+0 server. Windows reports unsynchronized; the experiment measures agreement with the workstation clock, not independently certified UTC accuracy. Preserve the existing limitation at evidence line 21 alongside the headline. |
| AC-05 | UNKNOWN | Both March M1 windows have zero in-range bars after the fix; the reason is documented, satisfying the contract's permitted UNKNOWN reporting path. Supplementary M5 is consistent with a fixed zero offset and New York session timing, but does not fulfill the M1 measurement or independently identify timestamp semantics. Replace the summary's apparent full PASS with this distinction. |
| AC-06 | FAIL | Available bar dates/counts are supported, but the gap totals omit intervals (F1), the first tick day is unmeasured (F2), and API errors can become absence claims (F3). Actual server depth remains UNKNOWN; reporting partial observations is useful but not full acceptance. |
| AC-07 | PASS | The scan against the owner-specified task base `0916776` has no order/account-mutation hit. The required scan against local `main` was also run; its sole mutation hit is the scanner's own pattern from older bootstrap history. That literal scan is not empty and is not silently counted as an empty scan; details below. |

## Checked, nothing found (and how)

- **Read-only and refusal boundary:** inspected the entire probe and test diff. The MT5 calls are
  initialization, account/terminal/version/symbol reads, price-history reads, error reads and
  shutdown. There is no send, check, modify, account login/change, symbol selection or terminal
  setting mutation call. Expiry is checked before initialization; `account_info()` is the first
  terminal data read after initialization, and account validation precedes all other data reads.
  Initialization failure obtains diagnostics only. Account refusals execute shutdown only after
  the check. Tests validate these call sequences; they never require the MetaTrader5 package.
- **Masking of supplied files:** inspected the seven scoped files and searched for filesystem
  paths and account/holder fields. Actual login values in results are masked; no holder name,
  terminal filesystem path or credential was found. `Standard\\Forex\\XAUUSDm` is the symbol's
  market hierarchy, not a local path. Full numeric test accounts are synthetic fixtures, not
  captured account identifiers. Broad mutation-name matches occur only in the contract's
  prohibition text, not executable spike code. No credential store was opened.
- **Evidence integrity:** all three JSON files parse. SHA256 values match the report prefixes:
  run 1 `583ebb2253329b2037081eb9fcd85fd20c3de3d63428ea79522c93c9409b5fae`,
  run 2 `70416ef7b2890dd1af333afd53b37e324a738fd217e08571087fac3ea6a4324d`,
  run 3 `b546b714eb77d1df9b6184fa4e79c0a7acf92a5c0ab6eef18deeb0e4a04364ad`.
  Recomputed tick offsets match within 1 ms, explained by truncation of stored `machine_utc` to
  milliseconds. All raw integer tick times equal the whole-second part of `time_msc`.
- **Supplementary M5 interpretation:** before US DST, the last pre-break bar is 21:55 and typical
  reopening 23:00 as-if UTC; after it, these are 20:55 and 22:00. They correspond to 16:55 and
  18:00 New York in both seasons. The March 6–8 weekend shortens to 48.08 h from the usual 49.08 h;
  the EU transition shows no additional shift. These observations support the stated New York
  interpretation conditionally, with the exceptions in F5. The April 2–5 long gap is consistent
  with Good Friday, not proof of a measured broker session. Exness documents GMT+0 and seasonal
  rollover/US-DST behavior; current documentation is corroboration, not a historical capture of
  this account's exact sessions. [Exness timezone](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader),
  [Exness trading hours](https://get.exness.help/hc/en-us/articles/4405235684498-Instrument-trading-hours).
- **Bar limit, out-of-range quirk and fix:** run 1 records an invalid-parameters error for the
  100,000-bar positional request. Run 2 records one July bar inside each requested March M1
  window and the contradictory `2005-01 (first bar 2026-07-10...)` summary. The current helper
  keeps only `[start, end)` and its regression passes; run 3 correctly reports zero March M1
  bars. The half-open filter also avoids double-counting the inclusive API endpoint between
  consecutive months. The observed request error does not establish a universal maxbars rule.
- **Depth numbers:** run 3 positional results match the report: M1 100,002 from July 10 04:02;
  M5 101,303 from May 18, 2025 22:05; H1 57,831 and D1 3,931 from January 14, 2014. Its separate
  monthly survey has 99,999 M1 bars starting July 10 04:05; these are separate requests, not one
  immutable snapshot. `maxbars` changes from 100,000 to 100,000,000, while returned M1 remains
  around 100,000. An old terminal limit/restart requirement is a hypothesis, not a measured
  cause. Returning fewer H1/D1 bars than requested also does not prove server exhaustion.
- **Datetime assumptions:** production range bounds are aware UTC; authorization and startup
  times are aware Bangkok; history receives aware UTC. `time.time()` provides epoch seconds and
  does not require subtracting the local Bangkok offset. The naive `.timestamp()` in the final
  test fixture checks elapsed gaps only; it does not prove UTC labels. `times_in_range()` compares
  raw timestamps directly to UTC epochs, so that filtering assumption is supported for this
  observed zero-offset case, not an arbitrary server. Python's distinction is documented in
  [datetime 3.12](https://docs.python.org/3.12/library/datetime.html#datetime.datetime.timestamp)
  and [time 3.12](https://docs.python.org/3.12/library/time.html#time.time).
- **Clock measurement limits:** wall time is sampled before the tick/API reads, so the measured
  offsets include tick age and call delay. Classification uses only `time_msc`; this review also
  checked the stored tick-second and M1 fields. Nine observations occur in roughly nine minutes,
  with no before/after call timing or independent clock-error bound. No cross-day or universal
  broker-time conclusion was inferred.
- **API semantics:** MetaQuotes documents UTC datetime inputs, inclusive bar-range endpoints,
  terminal chart-history limits and `None` on failure. These support the filter assessment and
  F3, but are not a substitute for measurements of pinned package 5.0.6231. [copy_rates_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py),
  [copy_ticks_range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py).
- **F01–F18 checklist:** F01/F17 are addressed by the AC table and F4; F08 by F3; data completeness
  by F1/F2/F5. No tests were removed, skipped or weakened in the selected diff. Synthetic data
  stay in the spike test file, which the task explicitly permits. No project dependency,
  lockfile, CI/control, application package or trading feature was added in the selected diff.
  No destructive action, embedded instruction execution or unbounded retry was found. There
  is no strategy, backtest, holdout access, order journal or risk-gate implementation to review
  here. The contract change is explicitly included in the owner's review scope.

### Checks run

All times are 2026-10-21, Asia/Bangkok (+07); head is `00a7bc7` throughout.

The exact test command was:

```text
uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 pytest spikes/SPIKE-001 -q
```

| Command / procedure | Result | Commit | Time (+07) |
|---|---|---|---|
| Exact offline pytest command above | PASS: 15 passed, 1 warning in 0.03 s; exit 0. `PytestCacheWarning`: cache creation denied with WinError 5. The warning did not prevent test execution; no cache/config change or retry was made. Local paths from the warning are intentionally omitted from this report. | `00a7bc7` | 03:08–03:09 |
| `bash scripts/controls/red-flags.sh main` | PASS command execution, exit 0; six pattern groups require the explanations below. Merge-base is the stale local `main` at `951ee98`, so this is not the task-only diff. | `00a7bc7` | 03:08–03:09 |
| `bash scripts/controls/red-flags.sh 0916776` | PASS command execution, exit 0; one group (test fakes), no mutation surface, no control files touched. | `00a7bc7` | 03:09 |
| `git diff --check 0916776..HEAD -- spikes docs/evidence docs/contracts/SPIKE-001-mt5-connectivity-time.md` | PASS, exit 0. | `00a7bc7` | 03:09 |
| `Get-FileHash spikes/SPIKE-001/results/*.json -Algorithm SHA256`; UTF-8 `ConvertFrom-Json` inspection and timestamp arithmetic | PASS: all files parse, hashes match and nine timestamp comparisons agree within the stored precision. | `00a7bc7` | 03:09–03:10 |
| `Select-String` on scoped source/evidence for mutation names, account/holder fields and local-path patterns; manual field/call inspection | PASS within the inspected files: only contract prohibition text matched mutation names; no actual unmasked account, holder or filesystem-path disclosure found. | `00a7bc7` | 03:10 |
| PowerShell review structure/whitespace/path validation | Initial checks FAIL from false matches on an HTTPS scheme and its explanatory example. Constraining the drive-letter regex and removing the example resolved them: PASS, required sections present, five findings, seven AC rows, no trailing whitespace or local-path patterns. No project configuration changed. | `00a7bc7` + review only | 03:12–03:13 |
| `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD` | PASS: only this review is untracked; tracked and staged diffs are empty; head unchanged. | `00a7bc7` + review only | 03:12–03:13 |

Red-flag explanations:

- The task-base scan finds only `FakeTerminal`, `RatesStub` and related fake/stub text in
  `test_probe.py`. They are test fixtures for refusals and the observed range bug, not production
  substitutes. No deleted/renamed tests or locked-control changes appear in that scan.
- The local-main scan includes older bootstrap changes. Its skipped-test hit is the existing
  control test's conditional Git Bash availability skip. Type/lint-disable hits are policy text
  and the scanner's regex definitions. Placeholder hits are scanner definitions and synthetic
  control/spike tests. Destructive/bypass hits are deny logic, negative test strings and process
  documentation, not spike operations. Its mutation hit is solely `red-flags.sh` defining its
  own detection expression. The listed control paths belong to that broader bootstrap diff.
  Those hits were not hidden by changing refs or configuration; the task-base scan was additional.
- Scans ran before this review existed. This newly created, intentionally unstaged review is not
  claimed to have been covered by a staged-file scan.

## Not checked (and why)

- No probe command, real terminal connection, account switch, terminal restart, live broker read,
  or real refusal scenario was performed: the owner explicitly prohibited them in this review.
- F1–F3 counterexamples are static, rerunnable test specifications, not newly executed tests.
  No test file was written or changed. The existing suite does not cover those cases.
- No independent UTC clock synchronization, historical session export, tick boundary refinement,
  M1 DST retrieval or full raw-history reconstruction was performed. Exact server retention and
  causes of exceptional gaps remain UNKNOWN. Raw market snapshots are not in the supplied files.
- Error-message redaction under arbitrary failures is not proven: `last_error()` and subprocess
  diagnostic text can be forwarded without sanitization. No sensitive disclosure was found in
  the supplied artifacts, so this is a coverage limitation rather than a claimed actual leak.
- Concurrent invocations, account changes after the initial check, output-file collisions and
  external time changes during a run were not runtime-tested. This is a single-session read-only
  spike; the review does not certify it as a production runner.
- Contents outside the explicitly selected diff were not independently reviewed. The full branch
  additionally changes DECISIONS.md, PROGRESS.md, SPEC.md, BOOT-001 contract/handoff and the
  dependency-admission review. Their presence was noted without expanding this review's scope.
  No SPIKE handoff or implementer chat was used to justify findings.
- `/review` is not an executable slash command in this headless tool interface; the requested
  git diff and manual cross-agent-review procedure were used. No broad control suite or new CI
  run was required for a review-only file. CI, merge and deployment status were not verified.
- PROGRESS.md and handoff files were intentionally left untouched under the owner's single-file
  instruction. Next action: the implementer addresses F1–F5 and corrects the AC summary, then
  requests a fresh review of the fixes. The owner retains acceptance and merge authority.
