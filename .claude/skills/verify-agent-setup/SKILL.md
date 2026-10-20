---
name: verify-agent-setup
description: P25 setup check for Claude Code in Sochron1k. Proves the session loaded AGENTS.md through CLAUDE.md, that the locked-path hook and deny rules really block, that the shell guard blocks git push, and that the verified commands run; then records the results. Run only when the owner asks ("ตรวจการตั้งค่า", "P25", "verify setup"), after a Claude Code update, or after changes to settings, hooks or AGENTS.md.
disable-model-invocation: true
metadata:
  version: "1.0.0"
  source: "Handbook v5 P25; App.O"
---

# Verify the Claude Code setup (P25)

Files in the repository do not prove the tool uses them. Collect evidence instead.

## Steps
1. Name the instruction files loaded in this session, and quote 3 rules from the "Agent roles" section of AGENTS.md word for word.
2. State your role here (planner and implementer) and what the role must not do.
3. Locked-path test: try to create `tests/acceptance/.p25-probe.txt` containing one line, using the Write tool.
   - Expected: blocked by the deny rule or by `.claude/hooks/protect-paths.mjs`. Record the exact message. → PASS
   - If the write succeeds: delete the file immediately, then report FAIL. The hook or settings are not active.
4. Shell-guard test: run `git push --dry-run`. Expected: blocked by the deny rule or by `guard-bash.mjs`. → PASS
5. Run each command under "Verified commands" in AGENTS.md, one by one. Report the real result and the output tail.
6. Report the Claude Code version if visible (the VS Code extension version, or `claude --version`), and the permission mode in use.
7. Append a results table to `docs/tooling/compatibility.md`:

| Date | Tool + version | Step | Result (PASS/FAIL/UNKNOWN) | Evidence |
|------|----------------|------|----------------------------|----------|

Do not modify any other file. If a step fails, report FAIL with the evidence and stop; do not try to fix the configuration yourself.
