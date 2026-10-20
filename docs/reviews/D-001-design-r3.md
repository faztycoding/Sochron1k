# Review D-001 design round 3 · base main · head 7e11c0f · reviewer Codex, fresh headless session

Reviewed 2026-10-21 +07 on `chore/D-001-architecture-revision`.
Exact head: `7e11c0fd68f0cc3833ad394c12635954123e86fd`.
Scope: r2 F3 proof of fix and F1/F2 regression check; latest-commit base
`c156c3a`, r2-reviewed head `fc38bc3`. The owner's request supplies this
document-only scope; no separate D-001 implementation contract is present.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 — CLOSED (document level) | High | confirmed | `docs/architecture.md:112`, `:119`, `:123`, `:204`, `:209`, `:248`; `DECISIONS.md:12` | Architecture is unchanged from `fc38bc3`; ADR boundary clauses remain intact. | Research retaining terminal/holdout access. | Host separation, interim prohibition and ENV-1 remain mandatory. | None for this recheck. | Re-read boundary/import rules and compared the delta; no regression. Runtime isolation still requires ENV-1. |
| F2 — CLOSED (document level) | Medium | confirmed | `docs/architecture.md:163`, `:176`, `:183`, `:187`, `:189`, `:301`; `DECISIONS.md:19` | Immutable scope, checkpoints, state binding, zero-send cases and race disclosure are unchanged. SPEC `:75` also requires execution scope. | Wrong account/server, expired scope, reconnect/restart. | No authorization boundary is relaxed. | None for this recheck. | Re-read scope rules and compared the delta; no regression. Runtime proof remains an E1 requirement. |
| F3 — CLOSED | Low | confirmed | `SPEC.md:52`, `:73`, `:74`, `:75`, `:104`; `DECISIONS.md:8` | Holdout and acquisition/execution target are Windows VPS; interim research is prohibited; sequence now places ENV-1 before R1. | Contracts drafted from the summaries. | Summaries now agree with architecture section 6.1. | None. | Applied r2's reading test against architecture `:108` through `:126`: no same-host research permission, undecided target or missing pre-R1 ENV-1. Cutoff and budget remain TBD at SPEC `:52`, `:65`, `:90`, `:92`. |

Severity on closed rows is the original finding severity, not an open defect.

## AC status

These are review criteria, not newly invented contract AC IDs.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| r2 F3 proof of fix | PASS | SPEC sections 5/8/10 and D-001 sequence match section 6.1; cutoff/budget remain TBD. |
| F1/F2 remain closed | PASS | Document-level controls unchanged; independently checked by a read-only sub-reviewer and confirmed by the primary reviewer. |
| Change scope | PASS | HEAD changes only SPEC sections 5/8/10 and DECISIONS phase sequence: two files, six insertions, four deletions. Since `fc38bc3`, only the committed r2 report is additionally present. |
| ENV-1 / E1 runtime proof | UNKNOWN | No isolation or execution tests in this document review. |

## Checked, nothing found (and how)

- Read the complete `git show HEAD` and r2 proof. SPEC section 8's adjacent
  interim prohibition prevents its research-host summary from authorizing
  research while the terminal remains local. Section 10 records the same gate
  and Q-10 cost without claiming deployment or setting a budget.
- Compared against architecture section 6.1 and the retained F1/F2 clauses.
  Architecture is byte-for-byte unchanged from the r2-reviewed commit.
  No code, dependencies, tests, controls or other decision text changed in HEAD.
- No new finding within this recheck. Existing r2 phase-gate conditions remain
  applicable; D-001 is still proposed (`DECISIONS.md:6`).

Checks below ran on `7e11c0f`, 2026-10-21; times are +07.

| Command | Result | Commit | Time |
|---|---|---|---|
| `git show HEAD`; `git diff --name-status fc38bc3..HEAD` | PASS: only the scoped changes and intervening r2 report. | `7e11c0f` | 06:51–06:52 |
| `git diff --check HEAD^ HEAD` | PASS: no whitespace diagnostics. | `7e11c0f` | 06:52:16 |
| `git diff --exit-code fc38bc3 HEAD -- docs/architecture.md` | PASS: exit 0, no difference. | `7e11c0f` | 06:52:16 |
| `bash scripts/controls/red-flags.sh main` | PASS execution: one hit group, existing fake/stub helpers in `spikes/SPIKE-001/test_probe.py`. Local main is stale at `0916776`; these are outside this fix. | `7e11c0f` | 06:52:05 |
| `bash scripts/controls/red-flags.sh HEAD^` | PASS: zero hit groups for the F3 delta. | `7e11c0f` | 06:52:16 |
| `node scripts/controls/check-locked-paths.mjs main` | PASS: no locked/append-only violation. | `7e11c0f` | 06:52:04 |
| `node scripts/controls/check-locked-paths.mjs HEAD^` | PASS: three paths including this report; no violation. | `7e11c0f` + report | 06:52:52 |
| `git diff --exit-code 3817f36 HEAD -- spikes/SPIKE-001/test_probe.py` | PASS: flagged test helpers unchanged since the merged SPIKE base. | `7e11c0f` | 06:52:52 |
| `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD` | PASS: only r3 untracked; no tracked/staged changes; HEAD unchanged. | `7e11c0f` + report | 06:52:52 |
| `git diff --no-index --check -- /dev/null docs/reviews/D-001-design-r3.md` | No whitespace diagnostics; exit 1 is the new-file difference in no-index mode. | `7e11c0f` + report | 06:52:52 |

## Not checked (and why)

- Runtime isolation, sentinel, broker connection, orders, backtests and E1
  negative cases: outside the authorized wording recheck. SPIKE AC-04 remains
  UNKNOWN as carried by r2; it was not rerun.
- Control self-tests and external CI: SKIPPED; no control/code change or fresh
  CI verification. Red-flag results cover tracked changes, not this new report.
- `rg --files docs/contracts` was BLOCKED (`rg` unavailable); PowerShell
  enumeration and UTF-8 reads completed document inspection without config changes.

## Decision advice

**F1, F2 and F3 are CLOSED at document level; no open finding in this scope.**
Recommend owner acceptance of the revised D-001 proposal with the existing
ENV-1/R1/E1 gates intact. This is advice, not ADR acceptance or runtime approval.
Before research, ENV-1 must prove isolation; implementation still needs approved
contracts and dependency admission, and Demo execution needs its own authorized
scope and E1 evidence. Cutoff and budget remain owner decisions (TBD).

Delivery: review report implemented; design remains proposed, runtime unverified.
Only this report is written, left unstaged/uncommitted for Claude. Per the explicit
one-file scope, no PROGRESS/handoff edit, stage, commit or push was performed.
