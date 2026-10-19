---
name: task-contract
description: Turns a Sochron1k goal, feature, spike or bug into a Task Contract (docs/contracts/<ID>-<slug>.md) with Q1–Q6 tier, scope and allowed files, invariants, negative cases, Given–When–Then acceptance, verification per AC, authorization, budget and recovery, then a short plan, and stops for the owner to approve the acceptance. Use before any implementation, when the owner says "เริ่มงาน", "ทำ feature", "เขียน contract", "แตกงาน", "วางแผน", or when work grows beyond its current contract.
argument-hint: "[goal or TASK-ID]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P05, P06; ch.7; App.D"
---

# Task contract and plan

The acceptance criteria are the owner's main lever: they decide what "done" means before any
code exists, and they stop the criteria from being bent later to match what got built.

## Procedure
1. Context: read AGENTS.md, the relevant SPEC.md sections, docs/architecture.md, DECISIONS.md
   and PROGRESS.md. Search the code for what already exists (targeted search first; F07).
2. Tier: answer Q1–Q6 with one line each (docs/HANDBOOK-CORE.md §3). Unsure means yes. A task
   that changes controls (Q6) is a separate task.
3. ID and branch: pick a prefix (SPIKE, DATA, RES, EXE, OPS, FIX, CHORE) and the next free
   number from docs/contracts/; branch `<feat|fix|chore|spike|research>/<ID>-<slug>`.
4. Write `docs/contracts/<ID>-<slug>.md` from `docs/contracts/_TEMPLATE.md`:
   - goal and acceptance in Thai, in plain words the owner can test by hand; identifiers in English
   - Given–When–Then ACs (AC-01…), each with a verifier and command. Include the negative cases
     that apply: duplicate command, broker timeout or UNKNOWN, stale price, non-Demo account,
     empty or malformed data, DST boundary, restart mid-operation, limit exactly at the boundary.
   - allowed files and excluded areas; invariants; external side effects and who authorizes them
   - budget: time, at most 3 attempts without new evidence, tool cost; recovery and checkpoint
   - split the task if it has more than 7 ACs or touches more than 3 boundaries
   - research tasks name the hypothesis (docs/hypotheses/H<nnn>), which must already be committed
5. Plan (P06), appended to the contract: understanding in 3 lines plus likely misunderstandings;
   files to touch and what will be reused; verifiable steps, each with its check; risks and
   negative cases; decision points for the owner ("none" if there are none).
6. Hand the ACs to the owner in Thai and ask for approval. If the owner cannot picture testing an
   AC by hand, rewrite it. On approval, record `Status: approved by owner <date>` in the contract.
7. Next step, by tier:
   - Lite: implement with `/implement-task <ID>`.
   - Standard or High: the owner opens a new Codex chat on the branch and runs `$write-acceptance-tests <ID>`.
     Commit the contract first so Codex can see it.

## Must not
Write implementation code, install dependencies, or mark the contract approved without the
owner's explicit approval. If an unknown blocks the design, create a SPIKE contract instead of guessing.
