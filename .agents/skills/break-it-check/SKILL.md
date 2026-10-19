---
name: break-it-check
description: Mutation-style check proving that Sochron1k's tests really catch a broken invariant. Temporarily breaks 3–5 critical points (risk limits, the Demo-only guard, idempotency, look-ahead and time conversion, stop-loss presence) on a throwaway branch or worktree, runs the tests, records caught or missed, and reverts everything. Use for "break-it", "ลองทำให้พัง", High-tier tasks, or when the owner doubts the tests.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P12; ch.15 technique 5"
---

# Break-it check

If a test still passes after you delete the safety check it protects, that test protects nothing.

## Rules
- Work only on a temporary branch `break/<TASK-ID>`, or in a separate worktree. Never push or merge it.
- Never touch real accounts or data. Use only the existing test commands.

## Procedure
1. Pick 3–5 points that matter for this task, for example:
   - the risk gate (per-trade, daily and experiment limits; reject when the minimum volume exceeds the budget)
   - the Demo-only trade-mode check right before sending
   - idempotency or duplicate-command handling; UNKNOWN on an ambiguous send
   - look-ahead protection (closed-bar only, `available_at`) and the time-module conversion
   - a stop loss is always present and never widened
2. Break one point at a time (delete the check, flip `>` to `>=`, shift by one bar, swap bid and ask).
3. Run the relevant tests after each break and record which test caught it, or that nothing did.
4. Revert everything. Prove the tree is clean: `git status` and `git diff` must both be empty
   before you switch back.

## Output
| Point broken | How | Caught by (test) | Result |
|--------------|-----|------------------|--------|

Then list the tests that are missing, so they can be added to the contract and written by the test author.
