---
name: rules-review
description: Weekly review of Sochron1k's AGENTS.md, CLAUDE.md and project skills against the failure library. Proposes deleting rules that prevent nothing, turning repeated failures into mechanisms (tests, hooks, CI), re-running the verified commands, and keeping AGENTS.md short. Proposes a diff only; the owner applies it. Use for "ทบทวน rules", "weekly review", "review AGENTS.md", or after a failure record is added in docs/failures/.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P24; ch.9, ch.27"
---

# Rules and skills review (weekly)

The weakest fix for a failure is a longer prompt. Prefer, in order: design it out → enforce by
permission or policy → detect automatically (test, lint, CI, hook) → checklist → rule text.

## Procedure
1. Read docs/failures/ for the period the owner names (default: the last 7 days), PROGRESS.md and DECISIONS.md.
2. For every rule in AGENTS.md, CLAUDE.md and every SKILL.md: has it prevented anything, or does a
   hook, lint or CI check already enforce it? If it does nothing, propose deleting it.
3. For every failure that happened despite a rule, propose a mechanism higher in the hierarchy,
   plus the regression evidence that would prove it works.
4. Run each command in AGENTS.md "Verified commands" and report PASS, FAIL or BLOCKED with output.
5. Check that the stack versions named in AGENTS.md match the lockfiles and installed tools.
6. Check the size: AGENTS.md should stay within about 2 pages; move details into docs/ or skills.
7. Check docs/tooling/registry.md: every active skill, plugin or MCP server is listed with an
   owner, permissions and a last-verified date.

## Output
A proposed diff (as text, in the chat or `docs/reviews/rules-<date>.md`) with one reason per
change, plus the failures that drove it. Do not edit locked files. The owner applies the change
and labels the PR `owner-approved-control-change`.
