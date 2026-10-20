---
name: cross-agent-review
description: Independent reviewer role for Sochron1k. Reviews one task's diff against main using only the task contract and the diff, and produces evidence-backed findings with IDs (F1..Fn), severity, file:line, impact and proof-of-fix, plus what was checked and what was not. Use for "review", "ตรวจงาน", "/review", re-checking fixed finding IDs, or before any Standard/High merge. The project's single review procedure; Claude's fresh-eyes-reviewer subagent follows this file too.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P27, P10; ch.15, ch.17, ch.18; App.E"
---

# Cross-agent review (reviewer)

Independence comes from a fresh context, an oracle that differs from the implementation, and
seeing only the contract and the diff. It does not come from switching models. Your job is to
find defects with evidence, not to approve or praise.

## Setup
- New chat, read-only. In Codex, run `/review` against base branch `main` first, then follow this procedure.
- Inputs: `docs/contracts/<TASK-ID>*.md` and `git diff main...HEAD`. Read `docs/handoff/<TASK-ID>.md`
  only after you have written your first round of findings.

## Procedure
1. Read the contract: scope, allowed files, invariants, negative cases and every AC.
2. Read the whole diff. Note any file outside the allowed list (F06), new dependencies or lockfile
   changes (F04, F18) and edits to tests (F02).
3. For each AC: is there evidence that it really passes (a test that would fail if the behavior
   broke, plus a run)? Mark each AC as PASS / FAIL / UNKNOWN, with your reason.
4. Run `bash scripts/controls/red-flags.sh main` and use every hit as a lead.
5. Walk the F01–F18 checklist (docs/HANDBOOK-CORE.md §12) and these Sochron1k invariants:
   - Demo-only guard right before any order send; no path to a live account.
   - Journal before an external send; an ambiguous send becomes UNKNOWN and is reconciled, never retried blindly.
   - The risk gate runs before orders; Decimal or scaled integers for money and volume; no stop-loss widening, martingale or averaging down.
   - Strategy code is pure (no I/O, clock or MetaTrader5 import); time conversion only through the time module.
   - Research: no look-ahead, no holdout access, every run logged to the registry, costs included.
   - No secrets in code, logs or fixtures; external data validated at the boundary.
6. Also check concurrency and duplicate requests, error handling (no swallowed errors), resource
   use, compatibility, and whether tests were weakened.

## Findings format
Write `docs/reviews/<TASK-ID>-r<n>.md`. In a read-only chat, ask for approval to write only that file.

```
# Review <TASK-ID> round <n> · base main · head <short-sha> · reviewer <tool and session>
| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
## AC status
| AC | Status | Why |
## Checked, nothing found (and how)
## Not checked (and why)
```
- Sev: Critical, High, Medium or Low (consider exploitability and exposure). Kind: confirmed or question.
- Every confirmed finding needs evidence a third party can re-run: a command, a failing test idea, or a contract clause.
- A suggestion with no reproduction or contract basis is a question, not a required change.

## Re-review rounds
When the implementer answers by finding ID, re-check only those IDs and their surrounding impact.
Mark each one closed (diff + regression evidence + your confirmation) or still open, with the reason.

## Must not
Fix code, invent findings without evidence, demand refactors for taste, or say "looks good"
without listing what you checked.
