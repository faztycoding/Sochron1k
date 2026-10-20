---
name: dependency-admission
description: Evaluates whether a new package, tool, plugin, skill or MCP server may enter Sochron1k, before anything is installed. Checks that it really exists (slopsquatting), who publishes it, maintenance, license, vulnerabilities, install scripts, native binaries, Windows and Python-version support, and whether existing code already covers the need. Use whenever someone proposes "uv add", "pip install", "npm install", a new plugin or skill, or asks "ควรใช้ library ไหน" or "เพิ่ม package".
metadata:
  version: "1.0.0"
  source: "Handbook v5 P17; ch.9, ch.21; F04, F18"
---

# Dependency admission (do not install)

AI assistants sometimes recommend packages that do not exist, and attackers register those
names. Every dependency is code that runs on the owner's machine, the one that can reach a
broker terminal.

## Procedure (network read only; ask for approval if your sandbox blocks it)
1. Exact identity: the official name on the registry (PyPI `https://pypi.org/pypi/<name>/json`,
   npm, or a GitHub repository for skills and plugins). Spelling must match the vendor's own
   docs. Watch for typo-squats and young packages with few releases.
2. Publisher and maintenance: the maintainers, the official vendor if any (for example
   MetaQuotes for `MetaTrader5`), last release date, release cadence, open security issues.
3. License, and compatibility with private use and redistribution.
4. Security: known vulnerabilities (OSV or GitHub advisories), install scripts, native binaries,
   transitive dependency count, network or file access at runtime.
5. Fit: wheels for Windows and the pinned Python version (D-001 proposes 3.12; MetaTrader5 has no
   cp315 wheel), size, and whether the stdlib or an existing dependency already covers the need
   (cost of writing it ourselves).
6. For skills, plugins and MCP servers: read every instruction and script file, list network
   destinations and permissions, and check for instructions that conflict with AGENTS.md (for
   example, the implementer writing its own tests).

## Output
- Decision proposal: ADMIT, REJECT or SPIKE FIRST, with reasons tied to the checks above.
- If ADMIT: the exact version to pin, and a draft entry for DECISIONS.md
  (`## D-0xx Add <name> <version> — <date> — proposed`). For tools, skills or plugins, also a draft
  entry for docs/tooling/registry.md.
- The owner approves. Installation happens later, by the implementer, in a separate step that
  updates the lockfile.
