# Review SPIKE-001 round 3 · base main · head aaf4a0c · reviewer Codex (headless, 2026-10-21 +07)

Rechecked the r2 answers with `git show 0347ef3` and `git show aaf4a0c`,
contract v1.1, the complete current probe, tests and evidence report, and the
unchanged round 4 JSON. Reviewed head:
`aaf4a0c3a00312926ac957ab43b3ac05bc19a890`. Local `main` resolves to
`0916776c58b78c34677ffb4ba73a7a0f789ca8ae`; no ref was changed by this review.

Result: **F3 and F6 CLOSED; F1, F2, F4 and F5 remain CLOSED from r2.
New F7 OPEN (Low): two added phrases attribute measured gaps to market breaks
without causal evidence.** AC-06 and AC-07 now PASS within their contract scope.
AC-03 and AC-04 remain UNKNOWN. The exact requested offline suite passed 21 tests.
These are local review results, not approval or evidence of CI/merge completion.

One read-only sub-review independently checked F6 and the evidence arithmetic;
the findings below were confirmed against the files. Only this report is written.
No probe CLI invocation, terminal connection, staging, commit or push was performed.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 — CLOSED (retained) | Medium | confirmed | `spikes/SPIKE-001/probe.py:204`, `:219`, `:297`; `spikes/SPIKE-001/test_probe.py:223` | Gap buckets and cross-month carry are unchanged by these fixes. The existing regression remains in the 21 passing tests; round 4 totals still agree. | Short gaps and cross-month intervals. | Original omission remains corrected, with r2's test-coverage limits retained. | None for the original defect. | r2 closure carried forward; no new full F1 audit claimed. |
| F2 — CLOSED (retained) | Medium | confirmed | `spikes/SPIKE-001/probe.py:325`, `:334`; `spikes/SPIKE-001/test_probe.py:151` | The primary first-tick request still starts at the fixed 2005-01-01 bound, independently of M1. The January 20 regression still passes. | A first tick after the supplementary sample day. | Original sampling defect remains corrected. | None for that defect. | r2 closure retained; the new preceding-day error behavior is assessed under F3. |
| F3 — CLOSED | Medium | confirmed | `spikes/SPIKE-001/probe.py:314`, `:316`, `:343`; `spikes/SPIKE-001/test_probe.py:201`, `:212` | `0347ef3` keeps earliest observations but adds UNKNOWN boundary status for failed earlier M1 requests. A failed preceding-day tick check now retains its from/to bounds and error before supplementary calls, and marks both the count and boundary UNKNOWN. Both new caller regressions pass in this review. | Earlier M1 months fail before later data; or the first-tick request succeeds and the preceding-day request fails before successful supplementary samples. | The two r2 paths no longer present an unqualified boundary or lose the tick failure diagnostic. | None for the two reported paths. | **Met:** diff + passing mixed-success/error caller tests + inspection of the previous source. Previous code has no `m1_first_month_boundary` and returns `None` for the failed tick count, so the new assertions reject it. The implementer's recorded 2-failed/19-passed red run was not independently rerun. Details and limits below. |
| F4 — CLOSED (retained) | Medium | confirmed | `docs/evidence/SPIKE-001.md:13`, `:57`, `:61` | Full AC-03 remains explicitly UNKNOWN; observed gaps are not substituted for authoritative trade sessions. | Reading symbol-spec acceptance. | The original false PASS remains corrected. | None for the reporting defect. | r2 closure retained; the missing sessions still prevent AC-03 PASS. |
| F5 — CLOSED (retained) | Low | confirmed | `docs/evidence/SPIKE-001.md:88`, `:92`, `:94`, `:98` | Measured M1 gaps and the 68-/79-minute exceptions are unchanged. | Treating a typical pause as an exact one-hour schedule. | Original exact-duration overstatement remains corrected. | None for the original defect. | r2 closure retained; no new session measurement claimed. |
| F6 — CLOSED | Medium | confirmed | `docs/evidence/SPIKE-001.md:16`, `:108`, `:138`, `:150` | `aaf4a0c` distinguishes first observed M1, increased annual density and validated completeness. It retains 2017's anomaly: 238,054 bars / 1,118 gaps versus 2018's 347,537 / 205, and explicitly leaves the research start UNKNOWN. No replacement 2018 cutoff is proposed. | Choosing a research start from the spike report. | The unsupported claim of complete, research-suitable M1 from 2017 is removed. | None for the original completeness claim; gap-cause wording is separately F7. | **Met:** summary, depth detail, follow-up and D-001 input no longer authorize a research cutoff. Finer daily/monthly quality evidence is required before SLICE-R1. r2 expressly permitted this correction without another terminal run. |
| F7 — OPEN (new) | Low | confirmed | `docs/evidence/SPIKE-001.md:108`, `:141`; `spikes/SPIKE-001/probe.py:204`, `:225`; `spikes/SPIKE-001/results/run4-20261021T0316.json:319` | The new text calls the 1,118 intervals in 2017 "พักตลาด" (market breaks). The source only classifies elapsed bar-open intervals into `gaps_15m_to_3h`; neither that field nor the annual summary establishes why the intervals occurred. | Interpreting the newly added annual comparison as known market closures. | Readers could attribute missing observations to market operation without evidence. Severity is Low because the report flags the year as anomalous and keeps the research cutoff UNKNOWN. | Call these intervals "ช่องว่าง" (gaps) in both added phrases, leaving their cause unmeasured. | Change the two causal labels, retain the counts/anomaly and UNKNOWN cutoff, and compare against the same JSON. No terminal run is needed. This does not invalidate the numerical AC-06 summary. |

### F3 proof and its limits

- The M1 caller regression produces 12 failed months in 2005, successful empty
  requests thereafter, and observed bars in July 2026. It asserts the observed
  month, UNKNOWN boundary and retained timeout diagnostics, then distinguishes
  the successful-empty prefix with `no failed request before it`.
- The tick caller regression returns a first tick, fails the preceding-day range
  and allows subsequent supplementary samples to succeed. It asserts the retained
  observation, UNKNOWN count/boundary and timeout diagnostic. Its companion call
  distinguishes a successful empty preceding day with count zero.
- Static inspection confirms the saved tick request bounds and immediate error
  capture at lines 343–349, before `month_sample_search` at line 354. The committed
  test does not directly assert those bounds or simulate a changing `last_error`;
  those details are confirmed by inspection, not claimed as separately tested.
- Boundary status is not a completeness certificate. Monthly gap counts remain
  observations of successful requests; any `m1_range_call_errors` makes a future
  affected census partial. Round 4 has no such errors. Its JSON predates the new
  status fields and was not regenerated or presented as a run of `0347ef3`.

## AC status

PASS is limited to the named observation/test. UNKNOWN does not count as passed.
AC-01 and AC-03–05 retain r2's assessments because their evidence and code paths
are unaffected; the terminal was not revisited.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Unchanged round 4 records build 6274, broker/company, authorized server, USD, masked login and Demo mode 0. This remains artifact evidence, not a new connection test. |
| AC-02 | PASS | Exact requested offline command: 21 passed. Existing account/authorization refusal checks remain intact; the two added tests cover F3 without weakening old assertions. |
| AC-03 | UNKNOWN | Required authoritative trade sessions remain missing. Closing the F4 reporting defect does not supply them. |
| AC-04 | UNKNOWN | Existing 12 observations support agreement with the workstation clock at the stated tolerance. The GMT+0 case cannot separate the two time hypotheses, and recorded Windows synchronization remains deficient; no independently certified UTC claim is made here. |
| AC-05 | PASS | r2's conditional assessment is retained: round 4 has M1 in both US/EU windows (19,329 / 17,887 bars, no call errors), supporting the stated unchanged-offset interpretation for this server. This does not resolve AC-04 or establish official sessions. |
| AC-06 | PASS | F3's two negative paths now have passing caller regressions and explicit boundary uncertainty; F6's unsupported cutoff is withdrawn. Round 4 supports first returned M1 on 2014-01-14 and first returned tick on 2026-01-01 23:05 within the fixed search bound, plus the gap census. Recomputed bar/gap totals agree. This meets the requested date/gap report, not continuous coverage, research suitability or global server retention. F7 is a Low causal-label issue; the measured values remain supported. |
| AC-07 | PASS | Independently ran the literal `bash scripts/controls/red-flags.sh main`; exit 0 and no "Order or account mutation surface" hits. Independently confirmed full `main` SHA `0916776c58b78c34677ffb4ba73a7a0f789ca8ae`. The old scanner self-match is absent. |

## Checked, nothing found (and how)

- **Scope and regression:** the two requested commits change only the probe,
  its tests and evidence report. The intervening `32531d5` records r2. No new
  package, lockfile, control/CI change, account operation, retry or strategy code
  appears in the fix delta. Account-first refusal, expiry and shutdown are intact.
  Existing assertions were not deleted or relaxed. No additional code defect was
  confirmed in the surrounding changed paths.
- **Evidence integrity and arithmetic:** round 4 is unchanged since r2; SHA256 is
  `ca81de33cc9e3b17ce86c2275e8fc92ff8cb59e1fc49cf72f7f81c014075146f`.
  Annual bars total 3,343,061, matching the positional count. Gap buckets total
  185 / 26 / 2,886 / 63 / 1,483 (4,643 intervals). Sparse 2014–2016 counts remain
  302 / 312 / 310. Recorded monthly errors are empty and the preceding-day tick
  count is zero. This checks summary consistency, not original capture provenance.
- **F01–F18 within the re-review delta:** checked truth of completion claims,
  test changes, fake placement, scope, error handling and evidence claims. No
  dependency/toolchain drift, destructive operation, secret addition, embedded
  instruction, holdout access, backtest or money/risk calculation was introduced.
  The remaining reporting issue is F7; original research/time limitations persist.
- **Red-flag hits:** exactly one group, "Placeholder or mock in production code",
  consisting of fake/stub text in `spikes/SPIKE-001/test_probe.py`, including
  `FakeTerminal`, `RatesStub` and the new `HistoryTerminal` fixture. These are
  synthetic tests in the contract-authorized spike directory, not probe data or
  production behavior. No mutation hit, deleted/renamed test or touched control file.

### Checks run

All times are 2026-10-21, Asia/Bangkok (+07), at head `aaf4a0c`.
The exact requested test command was:

```text
uv run --offline --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 --with tzdata==2026.5 pytest spikes/SPIKE-001 -q
```

| Command / procedure | Result | Commit | Time (+07) |
|---|---|---|---|
| Exact offline pytest command above | PASS: 21 passed, 1 warning in 0.03 s. `PytestCacheWarning`: cache creation denied with `[WinError 5] Access is denied`. Tests completed; no permission/config workaround was attempted. | `aaf4a0c` | 03:28:38–03:28:39 |
| `git rev-parse main`; `bash scripts/controls/red-flags.sh main` | PASS: main is `0916776c58b78c34677ffb4ba73a7a0f789ca8ae`; scan exits 0, mutation group empty; one test-fixture group explained above. | `aaf4a0c` | 03:28:38–03:28:40 |
| `git show 0347ef3`; `git show aaf4a0c`; complete touched-file reads | PASS inspection; F3/F6 closure and F7 evidence above. | `aaf4a0c` | 03:28–03:29 |
| `git diff --check 82077e1..HEAD`; `git diff 82077e1..HEAD -- spikes/SPIKE-001/probe.py spikes/SPIKE-001/test_probe.py` | PASS whitespace check and scoped inspection; old tests retained, two caller regressions added. | `aaf4a0c` | 03:29 |
| `git diff --exit-code 82077e1 HEAD -- spikes/SPIKE-001/results docs/contracts/SPIKE-001-mt5-connectivity-time.md` | PASS: empty diff; contract and recorded results unchanged. | `aaf4a0c` | 03:29 |
| `Get-FileHash spikes/SPIKE-001/results/run4-20261021T0316.json -Algorithm SHA256`; UTF-8 `ConvertFrom-Json` / `Measure-Object` | PASS: hash, observed dates, annual counts, gap sums and zero recorded monthly errors agree. | `aaf4a0c` | 03:29 |
| `git show 0347ef3^:spikes/SPIKE-001/probe.py` (focused comparison) | PASS inspection: previous code lacks the M1 boundary field and emits null on failed preceding-day ticks. This is static before-fix confirmation, not a claimed executed red run. | `aaf4a0c` | 03:29:48 |
| PowerShell review structure/whitespace validation; `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD`; `git rev-parse main` | PASS: seven finding rows, seven AC rows and required sections; no trailing whitespace. Only this review is untracked; tracked/staged diffs are empty. HEAD and main remain at the recorded SHAs. | `aaf4a0c` + review only | 03:30:56 |

`rg` was unavailable (`CommandNotFoundException`); discovery used PowerShell.
Initial Thai text reads were repeated with explicit UTF-8. Neither required test
nor scan was blocked, and no environment configuration was changed.

## Not checked (and why)

- No probe CLI execution, terminal connection, account operation or new market
  capture, as instructed. No historical checkout or independently executed
  before-fix suite. Tests use synthetic terminal objects only.
- No raw bar/tick snapshot is available to reconstruct the census, explain gap
  causes or validate a research cutoff. Annual density does not certify complete
  M1 from 2017, 2018 or any other year, nor continuous tick history.
- No independent clock synchronization, authoritative trade-session evidence,
  global retention measurement or cross-broker time validation. AC-03/04 remain
  unresolved; F1/F2's narrower test-coverage limitations recorded in r2 remain.
- No CI, owner acceptance, merge, deployment or D-001 approval was verified.
  Delivery remains **implemented**, with the listed local verification complete
  and overall acceptance incomplete. No PROGRESS.md or separate handoff was
  edited because the owner explicitly limited writes to this report. Claude can
  use it to address F7 and record the checkpoint; no staging/commit/push is done here.
