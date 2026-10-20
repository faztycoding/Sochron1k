@AGENTS.md

# Claude Code only

- Role here: planner and implementer (see "Agent roles" in AGENTS.md). Never write or change
  locked tests directly, certify your own work, or merge. D-006 permits standalone `git apply`
  of regular patch files directly under `docs/proposals/`, and non-force `git push` of the
  current task branch, without asking or an approval prompt. Use a named remote and explicit
  destination: `git push origin HEAD:refs/heads/<current-task-branch>`. Force, deletion, multi-ref,
  main/master and unproved pushes stay blocked. Labels and all other external writes stay with
  the owner. After the initial r9 owner application and fresh-session review, run the live push
  in the owner's session and record the result and CI for that exact pushed head; no prompt is expected.
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
  The post-run detector stays unchanged: only when its report contains exactly the target files
  of the `docs/proposals/` patch just applied, verify every expected applied SHA256 and Git blob
  against its handoff and continue. A hash mismatch, missing expected hash, or any other report
  means stop and ask (N6). For each patch: apply, verify hashes, fresh-session review, then commit.
- Before a handoff: commit, then write docs/handoff/<TASK-ID>.md (the `implement-task` skill covers this).
- Environment: Windows 11, shell is Git Bash. There is no system Python; use `uv run`. Node.js is
  available for the control-plane scripts.
