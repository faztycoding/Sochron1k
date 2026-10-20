---
name: architecture-options
description: Proposes 2–3 concrete architecture options for one Sochron1k decision, each with a Mermaid data-flow and trust-boundary diagram, cost, risks, the spike that would prove it, irreversibility and fit for a solo owner. Recommends one and drafts an ADR in DECISIONS.md with status "proposed" for the owner to decide. Use for "เลือก architecture", "ควรใช้อะไรดี", "ADR", technology or boundary choices (storage, runtime host, UI, scheduling), and before any change that is hard to reverse.
argument-hint: "[decision to make]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P04; ch.6"
---

# Architecture options → ADR (owner decides)

Never ask for "the best architecture". Options only mean something against this project's real
constraints: a solo owner, a Windows host running MT5, a research-first product, Standard tier
for Demo, and High tier for anything near real money.

## Procedure
1. Read SPEC.md, docs/architecture.md and DECISIONS.md. State the decision in one sentence, the
   constraints that bind it, and what is already decided (cite D-numbers).
2. Prepare 2–3 options. For each:
   - a Mermaid diagram of components, data flow and trust boundaries
   - monthly cost now and at 10x usage (VPS, data, APIs); "0" when local
   - main risks, and the cheapest spike that would prove or kill the option
   - what is hard to reverse, and lock-in
   - fit for a solo maintainer (ops burden, Windows constraints, CI testability)
   - what must be added if the tier rises (real money → High)
   - fit with the ch.34 controls: strategy purity, one time module, holdout separation, registry, risk gate before orders
3. Avoid complexity beyond the need (F15): no microservices, extra databases or new frameworks
   without a measured reason. Prefer boring, well-documented technology the agents know well.
4. Recommend one option with the reason. Append the ADR to DECISIONS.md:
   `## D-0xx <title> — <date> — proposed`, with Context, Decision, Why, Rejected, Consequences, Review when.
5. Ask the owner to have Codex attack the recommendation first (`$adversarial-design-review`
   architecture mode in a new chat). The owner then accepts or rejects. Change the status only when the owner says so.

## Must not
Change code or dependencies, mark the ADR accepted yourself, or present an unverified capability
as a fact. Unknowns go to a spike.
