---
name: verify-agent-setup
description: P25 setup check for Codex in Sochron1k. Proves Codex really loads AGENTS.md, knows its role, runs under the expected sandbox and approval policy, and can run the verified commands; then records the result. Use when the owner says "ตรวจการตั้งค่า", "P25", "verify setup", after installing or updating Codex, or after changing AGENTS.md or .codex/config.toml.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P25; App.O"
---

# Verify the Codex setup (P25)

A file existing in the repository does not prove the tool uses it. This check produces evidence.

## Steps (do not edit any other file)
1. Name the instruction files you loaded, and quote 3 rules from the "Agent roles" section of AGENTS.md word for word.
2. State your role in this repository (test author and reviewer) and what that role must not do.
3. Report the sandbox mode and approval policy currently in effect (from `/status` or your
   session settings). The expected project defaults (.codex/config.toml, applied once the project
   is trusted) are `workspace-write` and `on-request`. A review chat should be `read-only`.
4. Run each command under "Verified commands" in AGENTS.md, one by one, and report the real result and output tail.
5. Append a results table to `docs/tooling/compatibility.md` (ask for approval to write that one file):

| Date | Tool + version | Step | Result (PASS/FAIL/UNKNOWN) | Evidence |
|------|----------------|------|----------------------------|----------|

If any step contradicts the expected setup, report FAIL with the evidence. Do not fix the configuration yourself.
