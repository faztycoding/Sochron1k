---
name: failure-to-control
description: Turns a Sochron1k incident, escaped bug, agent mistake or near miss into a failure record (docs/failures/) and proposes the strongest control that would have caught it, following the hierarchy design → permission/policy → automated test, lint or CI → checklist → rule text last. Use when something went wrong or almost did, when the owner says "บันทึกความผิดพลาด", "ป้องกันไม่ให้เกิดซ้ำ", "postmortem", or during the weekly review.
argument-hint: "[what happened]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P23; ch.18, ch.25, ch.27"
---

# Failure → control

Learning is a mechanism, not a longer prompt. A failure library with no closed actions is not learning.

## Procedure
1. Create `docs/failures/F-<YYYYMMDD>-<slug>.md` from `docs/failures/_TEMPLATE.md`:
   - symptoms, impact, the related task or release, time found, who or what detected it
   - root cause and contributing causes; why the existing controls did not catch it (the detection gap)
   - the matching pattern F01–F18 (docs/HANDBOOK-CORE.md §12), if any
2. Propose prevention at the highest feasible level:
   1) design so it cannot happen; 2) enforce by permission or policy (deny rule, hook, sandbox);
   3) detect automatically (test, lint, CI check, red-flag pattern); 4) checklist step;
   5) a rule in AGENTS.md or a skill (last resort, and only if it can be checked).
3. Define the regression evidence that would prove the control works (for example: a fixture that reproduces the failure is now caught).
4. Name an owner, a deadline and a review date to check the failure is actually rarer.
5. If the control lives in a locked path (hooks, CI, AGENTS.md, skills), write the proposed diff
   into the record and tell the owner. It is a Q6 control change: a separate task, owner approval and the PR label.

Write in Thai for the owner, with English identifiers. Never blame "the AI hallucinated" or
"human error" as the root cause; name the missing control.
