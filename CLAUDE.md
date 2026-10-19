@AGENTS.md

# Claude Code only

- Role here: planner and implementer (see "Agent roles" in AGENTS.md). Never write or change
  locked tests, certify your own work, push, or merge.
- Plan before any multi-file change (plan mode or the `task-contract` skill). Wait for the owner
  when the plan contains a decision that changes the main outcome, or when the task is High.
- The standard loop runs on project skills: /spec-interview, /architecture-options,
  /task-contract, /implement-task, /fix-findings, /debug-with-evidence, /checkpoint,
  /explain-back, /register-hypothesis, /failure-to-control, /verify-agent-setup.
- Subagents do read-only search and fresh-context review only: fresh-eyes-reviewer,
  quant-auditor, security-reviewer, second-opinion. Their output is a pre-review. It does not
  replace the Codex review that Standard+ tasks require unless the owner has switched the
  binding (recorded in PROGRESS.md).
- Locked paths are enforced by deny rules and PreToolUse hooks. When blocked, stop and ask the
  owner. Never route around a block with scripts, interpreters, renames or another tool.
- Before a handoff: commit, then write docs/handoff/<TASK-ID>.md (the `implement-task` skill covers this).
- Environment: Windows 11, shell is Git Bash. There is no system Python; use `uv run`. Node.js is
  available for the control-plane scripts.
