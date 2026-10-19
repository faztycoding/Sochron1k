---
name: implement-task
description: Implements an approved Sochron1k task contract in small verified, committed steps, then produces the evidence package: per-AC completion report, red-flag scan, a demo script the owner can follow, and a handoff note for the Codex review. Use when the owner says "ลงมือ", "implement", "ทำตาม contract", "เริ่มเขียนโค้ด", after the acceptance tests exist (Standard/High), and when finishing or handing off a task.
argument-hint: "[TASK-ID]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P07, P14, P13, P30; ch.10, ch.11, ch.15"
---

# Implement a task contract

## Preconditions (stop and report BLOCKED if any fails)
- `docs/contracts/<ID>*.md` has `Status: approved by owner`.
- You are on the task branch, not main (`git switch -c <type>/<ID>-<slug>` if needed), and the
  working tree is clean or its changes are understood.
- Standard and High: the acceptance tests from the test author exist under `tests/acceptance/`
  (and `tests/golden/` for quant work), are committed, and currently FAIL. Lite: the contract says no locked tests.
- No other agent is writing to this working tree.

## Procedure
1. State in 3–5 lines: your understanding, the steps, the files you expect to touch, open doubts.
   Proceed unless a doubt changes the main outcome (High: wait for the owner).
2. For each step: search before creating, change only allowed files, run the targeted check,
   then commit `<type>(<scope>): <intent>` with `Refs: <ID>`. One logical step per commit.
3. Never edit, skip or weaken locked tests. If a test looks wrong, write down the evidence and
   ask the owner; the test author fixes tests.
4. Quant and trading code: strategy stays pure; times go through the time module; money uses
   Decimal; experiments run only through the registry runner; any order path checks Demo trade
   mode and journals before sending.
5. Counting attempts: after 3 without new evidence, stop and switch to `/debug-with-evidence`
   (which escalates to the second-opinion subagent).
6. Verify: run every check listed in the contract and the verified commands in AGENTS.md, plus
   `bash scripts/controls/red-flags.sh main`. Keep command, result, commit and time for each.
7. Optional pre-review: spawn the `fresh-eyes-reviewer` subagent (and `quant-auditor` for research
   code) with only the contract path and base branch. Fix what it confirms, then go on.
   This does not replace the Codex review.

## Evidence package (finish)
1. Completion report in the exact AGENTS.md format (Thai prose, English identifiers), with every
   AC as PASS/FAIL/BLOCKED/SKIPPED/UNKNOWN plus evidence. "Not tested" stays separate from "tested and failed".
2. Explain every red-flag hit, one line each.
3. Demo script for the owner (Thai): numbered steps a non-programmer can follow on their own
   machine, the expected result of each step, and at least one negative case.
4. Commit everything, then write `docs/handoff/<ID>.md` from `docs/handoff/_TEMPLATE.md`. Facts
   only: contract version, commit, the claimed-passing commands, what was not verified, files
   touched, known risks, and where the reviewer should look hard. No persuasion. Commit it.
5. Tell the owner the next step: open a NEW Codex chat in read-only mode, run `/review` against
   `main`, then `$cross-agent-review <ID>`.
6. At session end, run `/checkpoint`.

## Must not
Push, merge, claim "verified" when a required check did not run, or describe Demo results as live behavior.
