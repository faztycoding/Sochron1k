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
