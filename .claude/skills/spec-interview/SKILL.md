---
name: spec-interview
description: Interviews the Sochron1k owner in short rounds to complete SPEC.md (users and journeys, non-goals, data, risk tier Q1–Q6, NFRs with numbers, broker and account facts, risk policy, budget, acceptance authority) without guessing business answers. Unknowns become dated assumptions. Use when SPEC.md has TBD items, before the first task contract, when the owner says "สัมภาษณ์", "เติม SPEC", "ถามผมทีละข้อ", or when scope or risk policy changes.
argument-hint: "[section or topic, optional]"
metadata:
  version: "1.0.0"
  source: "Handbook v5 P03, P01; ch.2, ch.5"
---

# SPEC interview (owner decisions, not agent guesses)

SPEC.md is the one document the owner must read line by line. Everything agents build later
treats it as truth, so every business answer comes from the owner. An agent may only propose
options and safe defaults.

## Procedure
1. Read SPEC.md, DECISIONS.md and PROGRESS.md. List every `TBD`, every assumption marked [A],
   and every open question. Order them by impact: what blocks D-001 or the next contract comes first.
2. Ask in rounds of at most 5 questions (use the AskUserQuestion tool when available; it takes up
   to 4 per call). Write the questions in Thai. For each question:
   - why it matters, in one line (what changes in design or risk)
   - 2–3 likely options with their consequences
   - the safe default to record if the owner answers "ไม่รู้"
3. After each round, update SPEC.md immediately:
   - answers go into their section, with the date
   - an "I don't know" becomes a row in section 9 (assumption, how to verify, review date, status)
   - a change that alters Q1–Q6 re-tiers the work and is noted in section 2 and the change log
4. Domain checklist for Sochron1k (cover what is still open): broker, Demo server, account
   currency and leverage, netting or hedging mode; the exact symbol and its contract spec; which
   machine runs the terminal; risk-per-trade, daily and experiment limits and who may release a
   halt; trading hours and overnight policy; data sources and licensing; history depth; holdout
   cutoff and who keeps it; first hypothesis; monthly budget (tools, VPS, data); kill criteria for
   the project; how the owner wants to be alerted; language of documents.
5. Stop when no TBD blocks the next decision or contract. Show the owner a summary of what changed
   and ask them to certify. Set "Reviewed <date>" only after the owner explicitly confirms.

## Must not
- Invent business values (limits, broker, budget, hypothesis rules) or present assumptions as facts.
- Start contracts or code before the owner certifies the SPEC version that the work depends on.
