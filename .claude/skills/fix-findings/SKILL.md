---
name: fix-findings
description: Answers a Sochron1k review (docs/reviews/<TASK-ID>-r<n>.md) finding by finding. Each finding is either accepted and fixed with regression evidence, or disputed with evidence. One commit per finding, prefixed with its ID. Does not go beyond the findings, touch locked tests, or close findings itself. Use when a review file exists, when the owner says "แก้ตาม review", "แก้ finding", "fix F1", or after a Codex review round.
argument-hint: "[TASK-ID] [round]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P28; ch.17"
---

# Fix by finding ID

## Procedure
1. Read the review file, the contract and the handoff note. Check you are on the task branch with a clean tree.
2. For every finding ID, decide one of:
   - **accept**: make the minimal fix, add or extend a regression check that fails before the fix
     and passes after (in non-locked test locations; anything needing a locked test is a request
     to the test author), run it, and commit with a message starting with the ID: `F3: <intent>` plus `Refs: <TASK-ID>`.
   - **dispute**: give evidence (a test, a probe output, or the contract clause), and no code change.
3. Questions (findings marked "question") get a factual answer, or are sent to the owner if they need a decision.
4. Do not fix anything beyond the findings. New issues you notice become notes for the owner, not drive-by edits.
5. Update the "Findings response" section of `docs/handoff/<TASK-ID>.md` and commit it.

## Output
| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|

Then tell the owner: the reviewer re-checks only these IDs in the same review flow (the next
round file, `-r<n+1>`). Never declare a finding closed yourself.
