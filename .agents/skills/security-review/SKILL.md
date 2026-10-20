---
name: security-review
description: Attacker-minded security review for Sochron1k changes that touch credentials, the MT5 terminal or broker connection, order paths, external data or news, AI or agent tooling, dependencies, CI, hooks or permissions. Produces findings with a concrete abuse path and a negative test for each. Use for "security review", "ตรวจความปลอดภัย", any High-tier task, or a diff that touches secrets, auth, MCP, plugins or a new tool. Claude's security-reviewer subagent follows this file too.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P11; ch.14, ch.20, ch.21"
---

# Security review

Think like an attacker who wants to: trade on a live account, steal broker credentials, corrupt
the journal or research evidence, make an agent act on injected instructions, or slip a malicious
dependency or CI change in.

## Setup
Fresh read-only chat. Inputs: the contract (or the system part named by the owner) and the diff or files in scope.

## Procedure
1. Map assets (broker account access and credentials, the order path, the journal, research data,
   the holdout, the registry, the owner's machine, CI), identities (owner, Claude Code, Codex, CI,
   the MT5 terminal, the broker server, data or news providers, AI providers) and trust boundaries
   and entry points. A Mermaid diagram is welcome.
2. Check, as relevant:
   - Secrets in code, logs, fixtures, reports, screenshots or commits; credential handling for the MT5 login.
   - Demo-only enforcement: can any path reach a live account or send an order outside an authorized contract?
   - Injection: shell or path injection (structured args, canonical paths, symlinks), SQL in SQLite, unsafe
     deserialization (for example pickle of downloaded data).
   - Validation of broker, market and news data at the boundary (bid above ask, time reversal, malformed values).
   - Prompt injection through news, data files, issues or tool output, if any AI or agent reads them.
   - Tool privilege: hooks, deny rules, Codex sandbox, MCP or plugin scope; token audience and lifetime.
   - Supply chain: new packages (slopsquatting), unpinned CI actions, workflow permissions, untrusted PR input.
   - Kill switch and stop conditions exist and are reachable; logs redact sensitive values.
3. Map the threats to OWASP Agentic ASI01–ASI10 (docs/HANDBOOK-CORE.md §9) and, if AI is part of
   the product, to the OWASP LLM Top 10.

## Output
Write `docs/reviews/<TASK-ID>-sec-r<n>.md` in the cross-agent-review format. Every finding needs a
concrete abuse path (who does what, through which entry point, with what result) and a negative
test that proves the fix (for example: "a non-Demo trade mode must make send() refuse and log
nothing sensitive"). End with "Not checked in this scope". Never claim the system is secure.

## Must not
Fix code during the review, run anything against a real broker account, or read real credentials.
