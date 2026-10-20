---
name: second-opinion
description: Fresh-eyes debugging for Sochron1k when the implementing agent is stuck (3 attempts without new evidence). Starts only from the checkpoint, the reproduction steps and the real error, never the previous attempts. Reproduces the problem, ranks falsifiable hypotheses, runs the smallest probes, and reports a proven cause or UNKNOWN. Use for "second opinion", "ติดแล้ว ช่วยดูใหม่", "ช่วยหาสาเหตุ", or when a PROGRESS.md checkpoint says the task is stuck. Claude's second-opinion subagent follows this file too.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P29; ch.11"
---

# Second opinion from a checkpoint

You get only the problem, not the story of failed attempts, so you form your own hypotheses
instead of inheriting the first agent's blind spots.

## Inputs
The checkpoint section of PROGRESS.md, the reproduction steps, and the real error output. If
someone pastes the history of attempts, set it aside until after step 3.

## Procedure
1. Reproduce it yourself. Report whether you see the same result (same error, same revision, same environment).
2. Write 3 falsifiable hypotheses ranked by likelihood. For each, give the smallest probe that would refute it.
3. Run the probes and eliminate hypotheses with evidence. Separate application defects from
   environment problems (Python or uv version, MT5 terminal state, broker server time, file locks).
4. If you propose a fix, make it in a separate worktree or a branch `second-opinion/<TASK-ID>`.
   Never modify the main working tree. The original implementer reviews your fix in that round.

## Output
- The proven cause (with the probe output), or UNKNOWN plus the list of eliminated hypotheses and the next probe.
- If you have a fix: the branch or worktree, the change, and a reproduction that fails before and passes after.
