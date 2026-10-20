---
name: adversarial-design-review
description: Attacks a Sochron1k SPEC, risk-tier answer or architecture decision instead of building it. In spec mode it finds ambiguous, contradictory or unmeasurable requirements, missing NFR units, and Q1–Q6 answers that should be "yes". In architecture mode it finds failure modes, hidden costs, irreversibility and ops burden in the chosen option, without proposing a wholesale redesign. Use for "หาช่องโหว่ใน SPEC", "ตรวจ architecture", "challenge D-001", or before the owner accepts a SPEC version or an ADR.
metadata:
  version: "1.0.0"
  source: "Handbook v5 ch.2, ch.5, ch.6 (Codex roles); P04"
---

# Adversarial design review

## Mode: spec (SPEC.md or a contract)
1. List every statement that two people could read differently, or that cannot be measured.
   For each, propose a testable rewrite (number, unit, condition, measurement method).
2. List contradictions between sections (scope vs non-goals, NFR vs architecture, risk values vs strategy needs).
3. Re-answer Q1–Q6 independently (docs/HANDBOOK-CORE.md §3). Any "no" that should be "yes", or
   "unsure", becomes a finding. Unsure counts as yes.
4. Missing owners, missing acceptance authority, assumptions without a review date.

## Mode: architecture (docs/architecture.md, DECISIONS.md D-xxx)
1. The failure modes of the chosen option (MT5 terminal down, broker server time shift, Windows
   reboot, disk full, Python package update, duplicate send, partial fill), and what detects each.
2. Hidden costs: operations for a solo owner, a Windows-only runtime, CI limits, data licensing and storage.
3. What is hard to reverse, and what the cheapest spike would be to de-risk it.
4. Security boundaries that are missing or only enforced by prompts.
5. Whether the option meets ch.34 controls: strategy purity, a single time module, holdout
   separation, the registry, the risk gate before orders.
Do not propose a different architecture wholesale. Attack the chosen one; if it fails, say what
evidence would change the decision.

## Output
Write `docs/reviews/<DOC>-design-r<n>.md` in the cross-agent-review findings format (ID, severity,
location, evidence, impact, minimal change), with "Checked, nothing found" and "Not checked" sections.
