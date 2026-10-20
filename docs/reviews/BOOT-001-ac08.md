# Review BOOT-001 round AC-08 · base main · head ed019bb · reviewer Codex headless exec

Contract: `docs/contracts/BOOT-001-project-bootstrap.md` v1.1, AC-08.
Reviewed revision: `ed019bbdcbd864f5a21420bbf8b8b3838f06d89a`.
Base: `main` at `951ee986b853be11f89096c53c6aa94f37316f06`.
Date: 2026-10-20, Asia/Bangkok (+07:00).

Scope: complete reads of SPEC.md, docs/architecture.md and DECISIONS.md, limited to
assumption/unknown labels, unsupported business values and ADR decision status.
All three files are additions in `main...HEAD`, so their complete contents cover the
scoped diff. No source document was changed. The owner authorized this report and
the separate P25 appendix only; this is not an implementation or a full BOOT-001 re-review.
The explicit task recognizes D-003, D-006 and D-007 as recorded owner decisions.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `SPEC.md:52-53` | Holdout retention is specified as `ตลอดอายุการทดลอง` (whole experiment); registry retention as `ตลอดอายุโปรเจกต์` (whole project). Neither Retention cell has `[A]` or `TBD`, nor an owner-decision reference. The `TBD` on line 52 concerns location/custodian, not retention. | A storage/research contract copies these cells as decided policy. | Unconfirmed business retention values can become requirements despite AC-08's explicit labeling rule. | Mark each unconfirmed retention value `[A]`, or leave it `TBD`; retain a definite value only with a recorded owner decision. | Re-read both Retention cells and confirm an applicable marker or owner-decision reference; no new duration may be selected by the agent. |
| F2 | Medium | confirmed | `docs/architecture.md:49` | The cost row states `0 บนเครื่องเจ้าของ`, `0 + เวลาพัฒนา bridge`, and `0`, without `[A]`/`TBD`, units, a defined cost scope or supporting estimate. `SPEC.md:65` still leaves the monthly budget TBD. The document's overall Proposed status does not identify what this zero-cost premise assumes. | The owner compares architecture options for D-001 using the cost row. | An unqualified zero can be read as a known business cost even though included costs have not been established. | Label the estimate `[A]` and specify its scope and exclusions, or leave the cost `TBD`; do not invent replacement amounts. | Every cost cell has an explicit uncertainty marker and defined scope, or a recorded owner-confirmed value. |
| F3 | Low | confirmed | `SPEC.md:81-92`; `docs/architecture.md:192-197` | The unresolved question/assumption tables use `open`, `assumed`, or an unknowns heading, but omit AC-08's prescribed `[A]`/`TBD` markers. These headings already communicate uncertainty; this finding is specifically about the required notation. | Checking the contract's requirement that every unresolved assumption/unknown use `[A]` or `TBD`. | Label completeness cannot be certified even though these rows do not conceal their uncertainty. | Add applicable `[A]`/`TBD` markers per unresolved row or a clear table-level mapping. Preserve recorded owner decisions; do not reopen D-003 merely because SPEC A-02 has a stale `assumed` status. | Re-read each unresolved table row and show which explicit `[A]` or `TBD` marker covers it. |

Finding IDs are local to this AC-08 report, not replacements for F1-F23 in earlier
control reviews. F1/F2 establish missing uncertainty labels and missing attribution;
they do **not** prove that the author fabricated a value.

## AC status

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-08 | FAIL | F1 and F2 leave substantive retention/cost assumptions unlabelled; F3 records the remaining notation gap. The ADR requirement passes, but it does not resolve these failures. |
| AC-08: every assumption/unknown labelled `[A]` or `TBD` | FAIL | Concrete counterexamples are listed in F1-F3. A draft/proposed document status alone is not the required labeling of individual unconfirmed premises. |
| AC-08: no business value guessed by an agent | UNKNOWN | The supplied documents do not establish owner/source provenance for F1/F2. Lack of provenance is not proof of fabrication, but the universal no-guessing claim cannot be certified. Explicitly labelled inherited risk values remain assumptions, not accepted policy. |
| AC-08: pending ADRs remain proposed unless owner accepted | PASS | D-001, D-002, D-004 and D-005 are proposed at `DECISIONS.md:6,19,31,39`. D-003, D-006 and D-007 are accepted with owner attribution at `DECISIONS.md:26,46,65`, matching the explicit review instruction. |

D-007 does not waive this acceptance work: `DECISIONS.md:76` expressly leaves AC-08
requiring evidence. No agent acceptance, risk waiver or delivery-state transition is implied.

## Checked, nothing found (and how)

- Read all 98 lines of SPEC.md, 203 lines of docs/architecture.md and 77 lines of DECISIONS.md,
  then compared each ADR heading and the assumption/unknown sections against AC-08.
- SPEC.md:10-16 labels the inherited problem, user and intended outcome `[A]`.
  SPEC.md:61-65 marks the stale-tick threshold, risk percentages and position limit
  `[A]`/`TBD`; latency, availability and monthly budget are not assigned guessed numbers.
- Broker/account details, trading hours, overnight policy, the first hypothesis,
  holdout cutoff/location and runner host remain explicitly unresolved in SPEC.md:81-90.
  F3 addresses their prescribed notation, not a claim that they are silently decided.
- Architecture remains Proposed at docs/architecture.md:3; SPEC.md:68 also calls D-001
  proposed. DECISIONS.md:13-17 requires spike evidence, review and an owner decision
  before acceptance. Proposed module/library choices and handbook safeguards were not
  treated as invented business values.
- Architecture U1-U6 explicitly preserve uncertainty about connectivity, timestamp
  semantics, data depth, costs, host uptime and execution behavior. No fixed broker time
  offset was adopted in these documents.
- D-006's explicit supersession at DECISIONS.md:62 was considered when reading D-004's
  historical apply/push policy. The owner-decision exceptions were not misreported as
  unauthorized ADR acceptance.
- A separate read-only Codex review of the contract and target documents corroborated
  F1/F2, the label-only nature of F3, and the ADR inventory. It made no file changes.
  The primary reviewer independently checked every cited location.

Evidence log (command/procedure -> result -> commit -> time, all times +07:00):

| Command or procedure | Result | Commit | Time |
|----------------------|--------|--------|------|
| Numbered UTF-8 reads of the contract and all three target documents; AC-08 comparison | FAIL for AC-08; F1-F3 above | `ed019bb` | 2026-10-20 21:53-21:56 |
| `git diff main...HEAD --numstat -- SPEC.md docs/architecture.md DECISIONS.md` | PASS: 98, 203 and 77 additions respectively; no deletions, complete reads cover the scoped diff | `ed019bb` | 2026-10-20 21:54 |
| PowerShell `Select-String` for `[A]`, `TBD`, proposed/accepted and open/assumed, followed by contextual reads | PASS: located markers and all seven ADR statuses; completeness findings remain above | `ed019bb` | 2026-10-20 21:54 |
| `bash scripts/controls/red-flags.sh main` | PASS: exit 0; six explained hit groups; secret-pattern groups empty | `ed019bb` | 2026-10-20 21:54:09-21:54:10 |
| `node scripts/controls/check-locked-paths.mjs main` | FAIL: exit 1; 42 control changes require owner approval, not an environment failure | `ed019bb` | 2026-10-20 21:54:15-21:54:16 |
| `node scripts/controls/test-controls.mjs` | PASS: exit 0; 69/69, zero skipped | `ed019bb` | 2026-10-20 21:54:20-21:54:59 |

Full command tails, runtime settings, version and explanations of all six scan groups
are appended in `docs/tooling/compatibility.md`, under the Codex headless P25 run.
The scan was made before writing these evidence artifacts; the owner asked Claude to
verify, stage, scan and commit them afterwards.

## Not checked (and why)

- External owner chats, the historical Blueprint and the provenance of every inherited
  value: this review uses the requested documents and the owner's explicit identification
  of accepted decisions. It cannot certify authorship intent or invent missing provenance.
- Current broker/package/platform claims, actual business costs and operational behavior:
  no network research, dependency installation, terminal connection or experiment was
  requested. This is a labeling and decision-status review, not SPIKE-001.
- Full architecture fitness, leakage/security audit and acceptance of D-001:
  those require their own scope and spike evidence. No architecture redesign was attempted.
- AC-02 through AC-07 live acceptance, remote CI, branch protection and labels:
  the local P25 commands above do not independently close these criteria.
- IDE configuration loading and live sandbox denial behavior: P25 records the settings
  actually supplied to this headless exec, not proof of a separate IDE session.
- Final staged artifact scan and a new commit: explicitly delegated to Claude by the owner.
  Only this report and the compatibility appendix were written; PROGRESS.md was left
  unchanged under the explicit two-file limit.

## Recheck after fixes

Reviewer: Codex headless exec, fresh recheck requested by the owner via Claude Code.
Reviewed head: `82eab68bda9243e73d308fad02d559e22fcd4950` on
`chore/BOOT-001-project-bootstrap`; working tree was clean before this appendix.
Fix range: `692b5eb^..82eab68` (parent `28f764429b0196eefc4b251df36ba47fbbbaed95`).
Date: 2026-10-20, Asia/Bangkok (+07:00).

This recheck covers the three original findings and their surrounding impact only.
The original report above is preserved. The owner explicitly authorized writing only
this appendix; no other file, index, commit, branch, remote or account was changed.

| Finding | Status | Proof of fix and evidence |
|---------|--------|---------------------------|
| AC08-F1 (local F1) | Closed | `git show 692b5eb` shows the previously unlabelled retention cells gaining `[A]`, an owner-confirmation note and a Q-12 reference. At the reviewed head, `SPEC.md:52-53` still contains exactly the same whole-experiment and whole-project retention values. Q-12 at `SPEC.md:93` is `TBD (open)` and requests an owner decision without selecting a duration. Both cells now meet the stated proof; no new retention value was chosen. |
| AC08-F2 (local F2) | Closed | `git show 0a23ee2` preserves all three original zero amounts and the bridge-development qualifier. Every option's cost cell has `[A]` at `docs/architecture.md:49`. The shared `[A]` scope note at line 52 counts incremental license/service charges assuming the owner's machine, and explicitly excludes VPS, external data, electricity, broker commission/spread and development time except where listed. It says actual numbers have not been estimated and leaves the monthly budget TBD, consistent with `SPEC.md:65,91`. Each cell has an uncertainty marker and a defined scope, satisfying the stated proof without asserting a verified zero total cost. |
| AC08-F3 (local F3) | Closed | `git show 82eab68` adds the status legend at `SPEC.md:79`; Q-01 through Q-12 each have `TBD (open)` at lines 82-93 and A-01 has `[A] assumed` at line 94. A-02 at line 95 now cites the already accepted D-003 (`DECISIONS.md:26-29`), correcting the stale status without making a new decision. The explicit table-level TBD mapping at `docs/architecture.md:192` covers every U1-U6 row at lines 196-201. Each unresolved row is covered by an applicable marker, as the original proof permits. |

Updated AC-08 assessment:

| Sub-check | Status | Evidence |
|-----------|--------|----------|
| AC-08 overall | UNKNOWN | All three confirmed findings are closed and labeling/ADR checks pass; the independent no-agent-guessed-business-value requirement still lacks provenance evidence. UNKNOWN is not PASS and does not authorize closing BOOT-001. |
| Every assumption/unknown labelled `[A]` or `TBD` | PASS | F1-F3 above close the counterexamples from the original document review. The whole three-commit diff changes only the cited documentation and bookkeeping; the pre-fix SPEC/architecture/DECISIONS contents match the original reviewed revision `ed019bb`. Existing labels on inherited problem/outcome and risk values remain at `SPEC.md:10-16,59-65`; all question and unknown rows now have explicit coverage. |
| No business value guessed by an agent | UNKNOWN | The fixes add no owner/source evidence establishing the origin of the inherited retention values or zero-cost assumptions. `[A]` labels and a newly opened Q-12 disclose uncertainty but cannot prove historical provenance. Missing provenance is not evidence of fabrication. The existing attribution to earlier material in `SPEC.md:5-6` does not independently verify every business value. |
| Pending ADRs remain proposed unless owner accepted | PASS | `DECISIONS.md` is unchanged across the fixes. D-001, D-002, D-004 and D-005 remain proposed at lines 6, 19, 31 and 39. D-003, D-006 and D-007 retain the recorded owner acceptance already recognized by the original review at lines 26, 46 and 65. Architecture line 3 and SPEC line 68 still mark D-001 proposed. D-007 line 76 still requires evidence for AC-08. |
| Scope check: these fixes introduce/change no business value | PASS | Individual patches and the combined `692b5eb^..82eab68` diff show only retention labels/owner notes and Q-12, cost labels/scope/exclusions, table legends/status labels and the A-02 correction to existing D-003. The additional SPEC change-log row at line 101 records those label fixes; it is bookkeeping, not a new policy. Retention text, cost amounts, risk percentages, stale-tick threshold, position limit and the TBD budget are unchanged. No code, tests, dependencies, controls or ADR decisions were edited. This narrower PASS does not establish historical provenance. |

Commands and procedures (all dates 2026-10-20, all times +07:00):

| Command or procedure | Result | Commit | Time (+07:00) |
|----------------------|--------|--------|---------------|
| `Get-Content` reads of AGENTS.md, the cross-agent-review skill, this report, BOOT-001 contract and PROGRESS.md; `git status --short --branch`; `git ls-files` discovery | PASS: task/review scope read; correct task branch and clean tree; UTF-8 reads used to correct PowerShell's initial display encoding | `82eab68` | Before 22:00:48; exact setup seconds not captured |
| `rg --files -g AGENTS.md -g '*BOOT-001*' -g 'HANDBOOK-CORE.md' -g 'SPEC.md' -g 'architecture.md' -g 'DECISIONS.md'` | FAIL (discovery tool only): `rg` was not recognized. Used the permitted `git ls-files` / PowerShell fallback; no config changed and review was not blocked | `82eab68` | Before 22:00:48; exact setup seconds not captured |
| `git show --format=fuller --stat --patch 692b5eb` | PASS: full patch read; F1 before/after evidence above | `692b5eb` | 22:00:48 |
| `git show --format=fuller --stat --patch 0a23ee2` | PASS: full patch read; F2 before/after evidence above | `0a23ee2` | 22:00:49 |
| `git show --format=fuller --stat --patch 82eab68` | PASS: full patch read; F3 before/after evidence above | `82eab68` | 22:00:49 |
| `git log -5 --format='%H %s'`; `git status --short --branch` | PASS: three consecutive fix commits follow `28f7644`; HEAD `82eab68`; clean task branch, ahead of tracking ref by four commits | `82eab68` | 22:00:49 |
| Numbered `Get-Content -Encoding UTF8` reads of SPEC.md and DECISIONS.md; contextual architecture rereads of lines 30-60 and 185-207 after the full-read output was truncated | PASS: cited cells, all question/unknown rows, scope note and ADR statuses checked directly | `82eab68` | 22:00:55-22:01:11 |
| `git diff --stat '692b5eb^' 82eab68`; `git diff --unified=3 '692b5eb^' 82eab68 -- SPEC.md docs/architecture.md DECISIONS.md` | PASS: only SPEC.md and docs/architecture.md changed, 23 additions/16 deletions; full combined patch inspected; no DECISIONS change | `28f7644..82eab68` | 22:01:11 |
| `Get-Content -LiteralPath 'scripts/controls/red-flags.sh' -Encoding UTF8 -Raw`; `Select-String` of handbook section 12/F01-F18 | PASS: scanner behavior and failure checklist inspected; scoped fixes contain no code/test/control/dependency changes | `82eab68` | 22:01:11 |
| `git diff --exit-code ed019bb '692b5eb^' -- SPEC.md docs/architecture.md DECISIONS.md` | PASS: exit 0, empty diff; fix parent matches the original review's source documents | `ed019bb..28f7644` | 22:01:27 |
| `git diff --exit-code 82eab68 -- SPEC.md docs/architecture.md DECISIONS.md` | PASS: exit 0, empty diff; reread files match reviewed HEAD | `82eab68` | 22:01:27 |
| `git diff --check '692b5eb^' 82eab68` | PASS: exit 0, no whitespace errors in the fixes | `28f7644..82eab68` | 22:01:27 |
| `bash scripts/controls/red-flags.sh main` | PASS: exit 0; six hit groups explained below; both secret groups empty; no untracked files or deleted/renamed tests | `82eab68` | 22:01:27-22:01:29 |

The scan covers the whole bootstrap branch relative to main, not only these fixes.
Its six hit groups are unchanged inherited leads: (1) an environment-conditional
skip in control-test code; (2) type-disable spellings in a prohibition and scanner
patterns; (3) lint-disable spellings in scanner patterns; (4) placeholder spellings
in scanner patterns and synthetic scanner fixtures in the control-test script;
(5) destructive/bypass spellings in guard logic, deny settings, test cases and
policy/review documentation; (6) order/account mutation spellings in the scanner's
own pattern. The control-path listing belongs to the existing bootstrap work.
None is introduced by the three fixes. No control test was run in this recheck,
so the conditional skip is not a claim about this session's test execution.

A separate read-only Codex reviewer independently inspected the three patches and
cited rows, corroborating the closures, unchanged business values and provenance
limit. It changed no files; the primary reviewer checked the evidence directly.

Not tested: historical Blueprint/source provenance or external owner chats; real
costs or broker behavior; architecture fitness, full security/leakage review,
control-suite or locked-path gate execution, other ACs, remote CI and live runtime
permissions. These are outside this document-fix recheck; earlier suite results
above were not rerun or promoted to current evidence. No network access, package
installation, terminal connection or trading action was performed.

Delivery: document fixes locally rechecked; overall AC-08 remains UNKNOWN. No
approval, merge or deployment is implied. Claude can inspect and commit this
appendix under the existing handoff; substantiated owner/source provenance is
still needed before the no-guessing sub-check can pass. PROGRESS.md and a separate
handoff file were deliberately not edited under the owner's one-file limit.

Post-append verification (2026-10-20, +07:00):

| Command or procedure | Result | Commit | Time (+07:00) |
|----------------------|--------|--------|---------------|
| `git diff --check`; `git diff --numstat`; `git status --short --branch`; `git diff --cached --exit-code`; `git diff -- docs/reviews/BOOT-001-ac08.md` | PASS: no whitespace errors; only this report modified, with additions and zero deletions; index empty. The inspected main appendix was 74 added lines before this verification record | `82eab68` + working-tree appendix | 22:03 |
| `node -e` read-only comparison using `git show HEAD:docs/reviews/BOOT-001-ac08.md` and the working file, normalizing CRLF to LF, then checking the original text prefix and exactly one appended `## Recheck after fixes` heading | PASS: original report preserved and one recheck section appended | `82eab68` + working-tree appendix | 22:03:19 |
