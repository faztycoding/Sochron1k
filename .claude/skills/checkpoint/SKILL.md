---
name: checkpoint
description: Saves or resumes a Sochron1k session checkpoint in PROGRESS.md, so any person or agent can continue without reading chat history. "save" records state, branch and HEAD, done-with-evidence, not done, decisions, failed attempts, pending external operations, authority and the next safe action. "resume" verifies git and pending operations before acting. Use at session end, before switching tools, when context feels long, or when the owner says "จบ session", "พักก่อน", "ทำต่อ", "continue", "resume".
argument-hint: "save | resume"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P15, P16; ch.10; App.H"
---

# Checkpoint (save or resume)

A new session that starts from a good checkpoint usually works better than an old session that
has decayed. If the owner has to re-explain something twice, the checkpoint or AGENTS.md is missing it.

## save (default)
Update PROGRESS.md using its existing structure (App.H). Write in Thai for the owner, with English identifiers:
- `## Current task`: task ID and version, state (READY, EXECUTING, VERIFYING, REVIEWING, BLOCKED…),
  branch, HEAD short SHA, uncommitted changes (none, or a list).
- `## Done (with evidence)`: each step with command → result → commit.
- `## Not done yet`: each item with why, or what is needed.
- `## Decisions and assumptions this session`: move lasting ones to DECISIONS.md.
- `## Tried and did not work`: so the next session does not repeat it.
- `## Pending external operations`: operation, its ID, last known status. Check these before any retry.
- `## Authority and budget left`: what is approved, until when, attempts or cost left.
- `## Next safe action`: the very next step, and what waits for owner approval.
Never write secrets, account numbers or personal data. Commit PROGRESS.md on the task branch.

## resume
1. Read AGENTS.md, PROGRESS.md and the contract it names.
2. Check git: branch, HEAD and working tree against the checkpoint.
3. Check every pending external operation by its ID before repeating anything.
4. Check that the authority and evidence are still valid (did the code change after the evidence was taken?).
5. Tell the owner in 5 lines (Thai): where we are, what changed, what you will do next, and what needs their approval.
If the state differs from the checkpoint, reconcile first. Never replay writes automatically.
