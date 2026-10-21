# Review SPIKE-001 round 4 · base 40ce8b9 · head cc36c26 · reviewer Codex (headless, post-merge, 2026-10-21 +07)

Reviewed exactly `git show 1336d9b 1e5b033 cc36c26` against contract v1.1
and r3 F7. `40ce8b9` is the parent of the first reviewed commit; the r3
implementation head was `aaf4a0c`. This is a review of the three requested
commits, not a new review of the complete branch against main.

Workspace HEAD is `3817f367a6fe2f37cc82e5a75a85bb874ea0822a` on
`chore/SPIKE-001-post-merge-review`. Its merge record identifies PR #3,
parents `0916776` and `cc36c26`, and time 2026-10-21 03:38:33 +07.
Local `main` still resolves to `0916776c58b78c34677ffb4ba73a7a0f789ca8ae`.
No ref was changed. The reviewed evidence and checkpoint are identical at
`cc36c26` and workspace HEAD.

Result: **F7 CLOSED; no new confirmed findings in this delta. AC-03 PASS as
of the recorded date is supported as a dated specification record, with the
stated limitations. AC-04 remains UNKNOWN. No other AC was promoted beyond
r3's assessment.** The exact requested offline suite passed 21 tests.

One read-only sub-review independently checked the contract, changed evidence
claims and checkpoint and reached the same assessment. Only this report is
written. These are local review results, not approval or fresh CI evidence.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F7 — CLOSED | Low | confirmed | `docs/evidence/SPIKE-001.md:122`, `:136`, `:155`; `spikes/SPIKE-001/results/run4-20261021T0316.json:319`, `:329` | `1336d9b` replaces the two causal market-break labels with measured gaps and an unknown cause. The aggregate row also states that elapsed bar-open intervals do not prove their cause. The later screenshot commit preserves this correction. | Interpreting 2017's 1,118 intervals as proven market closures. | The unsupported causal attribution is removed; the annual anomaly and UNKNOWN research cutoff remain visible. | None for F7. | Met: diff inspection plus confirmation against unchanged round 4 JSON: 2017 has 238,054 bars / 1,118 gaps, 2018 has 347,537 / 205, and the 15-minute-to-3-hour bucket totals 2,886. Evidence lines 152–157 retain the UNKNOWN research start. No terminal rerun or new test is required for this wording correction; the existing 21 tests pass. |

## AC status

PASS is limited to the recorded observation or executed check below. Unchanged
AC assessments are carried forward from r3, not represented as new broker
measurements. UNKNOWN does not count as passed.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Retained from r3: the unchanged round 4 artifact records the terminal build, broker/server, USD, masked account and Demo mode. No new connection was made. |
| AC-02 | PASS | The exact offline command passed all 21 tests at merged HEAD. Probe and test files are unchanged since r3; no assertion was removed or weakened by these commits. |
| AC-03 | PASS | Limited to recording the specification as of 2026-10-21, approximately 03:31 +07. Existing API fields are supplemented by the attributed owner screenshot transcription of the terminal's XAUUSDm Specification. Timezone, winter and holiday schedules remain unverified, and the original image was not available to this reviewer. Assessment and provenance limits below. |
| AC-04 | UNKNOWN | Unchanged: the GMT+0 server cannot distinguish the two timestamp hypotheses; the workstation synchronization limitation remains. Neither the session table nor this review establishes independently certified UTC. |
| AC-05 | PASS | Retained from r3 within its stated limits: unchanged M1 observations in the US/EU DST windows support the reported seasonal pattern for this server, conditional on AC-04. This does not establish an official annual session calendar. |
| AC-06 | PASS | Retained for first returned dates and the gap census, not completeness or research suitability. F7 changes no measurement; the research start remains UNKNOWN. |
| AC-07 | PASS | The literal `bash scripts/controls/red-flags.sh main` completed with exit 0 and no "Order or account mutation surface" hits. Local main's exact SHA and the one other hit group are recorded below. |

### AC-03 evidence and wording

- Contract v1.1 AC-03 requires recording the symbol's numeric specification and
  trade sessions. It does not require a verified year-round calendar, proven
  session timezone or retention of the screenshot. The report names the source,
  symbol, owner-provided image and approximate capture time at
  `docs/evidence/SPIKE-001.md:59`, and explicitly says the image is not stored.
  This supplies the previously missing recorded sessions without presenting
  observed price-data gaps as the source of the official table.
- Lines 63–66 record Quotes and Trade identically: Sunday 22:01–24:00;
  Monday–Thursday 00:00–20:58 and 22:00–24:00; Friday 00:00–20:58;
  Saturday none. The arithmetic at line 72 is correct: 20:58–22:00 is
  62 minutes. A final M1 opening at 20:57 followed by an opening at or after
  22:00 produces a longer bar-open interval; it does not contradict the
  62-minute specification break. The report retains the observed exceptions
  rather than rewriting them to match the table.
- Line 73 expressly leaves the screenshot's timezone unproved. The reference
  to normal MT5 server-time display is not treated here as proof of this
  capture's timezone. "EDT period" describes the seasonal observation, not a
  claim that the table's displayed clock is America/New_York local time.
- Lines 74–75 are consistent with unchanged round 4 observations: last bars
  at 20:57 in the US daylight-saving period and at 21:57 before the March
  transition. The winter Specification schedule is described as likely
  different, not as measured. Line 159 explicitly reserves timezone, EST and
  holiday verification before SLICE-E1. The summary at line 13 retains both
  the capture-date qualification and the timezone/year-round limitations.
- **Provenance limit:** the original screenshot is absent from this review's
  inputs. I checked the committed transcription and its internal consistency,
  not the pixels, exact capture time or account/server shown in that image.
  The additional swap and margin values at line 68 are likewise attributed to
  that same image, not independently reproduced from it. This is a supported
  report-level PASS, not independent authentication of the source image or
  validation of a schedule suitable for automated execution.

## Checked, nothing found (and how)

- **Other statuses and claims:** only AC-03 changes status in the evidence
  report. `PROGRESS.md:9` repeats r3's PASS assessments for AC-01, AC-02 and
  AC-05–07, qualifies AC-03 by its date/source and explicitly states that Codex
  had not reviewed that addition. Lines 10 and 14 retain AC-04 UNKNOWN and
  the UNKNOWN research start. Lines 7 and 11–15 summarize existing runs,
  tests and observations; no additional experiment or validated research
  cutoff is claimed. The timestamp shorthand remains bounded by the adjacent
  AC-04 uncertainty and the evidence report's workstation-clock limitation.
  No other unsupported changed AC or measurement claim was confirmed.
- **Review chronology:** the checkpoint's "reviewed (Codex r3)" is a historical
  reference, not proof that r3 inspected these later commits. It calls F7 fixed
  in `1336d9b` and separately discloses the unreviewed AC-03 addition. This r4
  supplies the requested later recheck. The checkpoint's pending-PR wording
  predates the merge; it is not current delivery evidence.
- **Scope and F01–F18 checklist:** the three commits change only
  `docs/evidence/SPIKE-001.md` and `PROGRESS.md`, both contract-allowed files.
  Probe, tests, recorded results and contract are unchanged since r3. No new
  dependency, lockfile, control, permission, order path, concurrency/retry
  behavior, error handling or resource-use change appears in this delta.
  No added credential, destructive operation, embedded instruction, holdout
  access or backtest was found. No broader re-audit of unchanged code is claimed.
- **Evidence integrity:** round 4 SHA256 remains
  `ca81de33cc9e3b17ce86c2275e8fc92ff8cb59e1fc49cf72f7f81c014075146f`,
  matching r3. The affected annual values and gap sum were independently
  read/recomputed from that JSON. Original capture provenance and gap causes
  cannot be established by matching this hash.
- **Red flags:** exactly one hit group, "Placeholder or mock in production
  code", from fake/stub fixtures in `spikes/SPIKE-001/test_probe.py`, including
  `FakeTerminal`, `RatesStub` and the history fixture. These are synthetic
  tests in the contract-authorized spike directory. No mutation, deleted or
  renamed test, or touched control-file hit. The literal scan uses local main
  `0916776`, so it covers the merged spike as well as the three reviewed commits;
  it does not silently substitute the narrower review base.

### Checks run

All times below are 2026-10-21, Asia/Bangkok (+07). Workspace HEAD was
`3817f36`; the reviewed commit endpoint was `cc36c26`.

Exact requested test command:

```text
uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 pytest spikes/SPIKE-001 -q
```

| Command / procedure | Result | Commit | Time (+07) |
|---|---|---|---|
| Exact offline pytest command above | PASS: 21 passed, 1 warning in 0.04 s; exit 0. `PytestCacheWarning`: could not create `.pytest_cache/v/cache/nodeids`, `[WinError 5] Access is denied`. The suite completed; no permission or configuration workaround was attempted. | `3817f36` | 06:28:54–06:28:55 |
| `git show 1336d9b 1e5b033 cc36c26`; UTF-8 contract, r3 and evidence reads | PASS inspection: F7 closed; AC-03's dated record and caveats are consistent with the contract; no other unsupported changed AC claim confirmed. | Three named commits at `3817f36` | 06:28–06:29 |
| `git rev-parse main`; `bash scripts/controls/red-flags.sh main` | PASS: main resolves to `0916776c58b78c34677ffb4ba73a7a0f789ca8ae`; scan exit 0, mutation group empty, one fixture group explained above. | `3817f36` | 06:29:05–06:29:06 |
| `git show -s --format=fuller HEAD` | PASS: local merge record identifies PR #3, parents `0916776` / `cc36c26`, and 03:38:33 +07. No GitHub/CI query made. | `3817f36` | 06:29:05 |
| `git diff --check 1336d9b^ cc36c26`; `git diff --name-only 1336d9b^ cc36c26` | PASS: whitespace exit 0; only evidence and PROGRESS changed. | `40ce8b9..cc36c26` | 06:29:28 |
| `git diff --exit-code aaf4a0c HEAD -- spikes/SPIKE-001 docs/contracts/SPIKE-001-mt5-connectivity-time.md` | PASS: exit 0, empty diff; probe, tests, results and contract unchanged since r3. | `aaf4a0c..3817f36` | 06:29:28 |
| `git diff --exit-code cc36c26 HEAD -- docs/evidence/SPIKE-001.md PROGRESS.md` | PASS: exit 0, empty diff; inspected document lines match the reviewed checkpoint. | `cc36c26..3817f36` | 06:29:28 |
| `Get-FileHash spikes/SPIKE-001/results/run4-20261021T0316.json -Algorithm SHA256`; UTF-8 `ConvertFrom-Json` / `Measure-Object` | PASS: hash agrees with r3; annual affected values, total 2,886 and seasonal M1 observations agree with the changed wording. | `3817f36` | 06:29:05–06:29:28 |
| PowerShell review structure/whitespace check; `git diff --exit-code`; `git diff --cached --exit-code`; `git status --short`; `git rev-parse HEAD`; `git branch --show-current` | PASS: required sections and seven AC rows, no trailing whitespace; tracked/staged diffs empty; only this report untracked. HEAD and task branch unchanged. | `3817f36` + review only | 06:30:34 |

`rg` was unavailable (`CommandNotFoundException`); discovery used PowerShell.
Initial Thai text reads were repeated with explicit UTF-8. Neither the required
test command nor the red-flag scan was blocked.

## Not checked (and why)

- Original screenshot pixels, transcription fidelity and capture provenance:
  the image is not stored in the repository or supplied to this review.
- No terminal connection, probe CLI run, account operation, new market capture,
  clock synchronization check or broker verification. No winter/holiday
  Specification or screenshot timezone confirmation was obtained. Those
  limitations remain open before operational use.
- No raw bar/tick snapshot was available to prove gap causes or research
  completeness. Earlier F1–F6 closures and r3's coverage limits are retained;
  they were not reopened as a fresh full-code audit.
- No remote CI, owner acceptance, deployment or D-001 decision was checked.
  Local git confirms the requested changes were **merged** as `3817f36`;
  this does not turn AC-04 into PASS or certify overall acceptance.
- This review artifact is written locally for Claude to stage/commit. No other
  file, including PROGRESS or handoff, is edited under the owner's explicit
  one-file instruction. No staging, commit or push is performed. Claude can
  use this report as the handoff for the post-merge checkpoint.
