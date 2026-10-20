---
name: debug-with-evidence
description: Evidence-driven debugging loop for Sochron1k: observe expected vs actual, build the smallest reproduction before touching code, test falsifiable hypotheses with minimal probes, fix the root cause in scope, and show the repro failing before and passing after. After 3 attempts without new evidence it stops, checkpoints and escalates to a second opinion. Use for bugs, failing tests, "error", "พัง", "ไม่ทำงาน", flaky results, MT5 or broker surprises, and any loop that keeps retrying.
argument-hint: "[symptom or failing test]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P08, P29; ch.11"
---

# Debug with evidence

## Loop (keep an attempt counter in your notes)
1. **Observe**: expected vs actual, the exact error, revision, environment (Python and uv
   versions, MT5 terminal build, broker server, time). Read the real logs; never assume.
2. **Reproduce** before editing: a failing test (non-locked location) or exact repeatable steps.
   For time or market bugs, pin the data slice and the clock.
3. **Hypothesize**: 1–3 falsifiable causes, each with the evidence that supports it.
4. **Probe**: the smallest experiment that can refute each. Separate application defects from
   environment problems (terminal not logged in, server-time offset, DST, file locks, sandbox limits).
5. **Fix** the root cause inside the task scope. Show the reproduction failing before and passing
   after. Add a regression test when it adds meaning.
6. **Record** what was tried and what was learned in your notes or PROGRESS.md.

## Forbidden ways to make it green
Raising timeouts alone, deleting or loosening assertions, editing expected values, catching and
ignoring errors, rerunning until lucky, or changing business logic to dodge an environment problem.

## External side effects
If an operation against the broker or any external system may have happened (timeout after
send), the state is UNKNOWN_EFFECT. Never resend; reconcile against the authoritative system
first. Record the operation ID.

## Stop rule: 3 attempts without new evidence
1. Run `/checkpoint`, including the reproduction and the real error.
2. Escalate: spawn the `second-opinion` subagent with ONLY the checkpoint section, the
   reproduction steps and the real error output. Do not pass the history of attempts. Or ask the
   owner to run `$second-opinion` in a new Codex chat.
3. If the second opinion proposes a fix, you review it; you do not merge it blindly.
