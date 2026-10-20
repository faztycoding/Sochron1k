# Compatibility results (P25)

Handbook v5 ภาคผนวก O: ไฟล์ใน repo ไม่ใช่หลักฐานว่าเครื่องมือใช้มันจริง ต้องรัน P25 ทุกครั้งที่ติดตั้งหรืออัปเดตเครื่องมือ หรือแก้ AGENTS.md, settings หรือ hooks
วิธีรัน: Claude Code `/verify-agent-setup` (session ใหม่) · Codex `$verify-agent-setup` (chat ใหม่)

| Date | Tool + version | Step | Result | Evidence |
|------|----------------|------|--------|----------|
| 2026-10-18 | Claude Code 2.1.301 | Hook logic (protect-paths, guard-bash, session-context) and lock rules against fixtures | PASS | `node scripts/controls/test-controls.mjs`: 19/19 pass, uncommitted tree on `chore/BOOT-001-project-bootstrap`. Limit: proves script logic only, not that Claude Code loads the hooks |
| 2026-10-18 | Claude Code 2.1.301 | Settings hot-reload: `.claude/settings.json` took effect in the same session it was written | PASS | The next Bash call was blocked by `guard-bash.mjs` (BOOT-001 session 1) |
| 2026-10-18 | Claude Code 2.1.301 | Deny rule live: Write `tests/acceptance/.p25-probe.txt` | PASS | Tool error: "File is in a directory that is denied by your permission settings"; no file created |
| 2026-10-18 | Claude Code 2.1.301 | guard-bash live: `touch tests/golden/.p25-probe`, `git push --dry-run`, `cat .env` | PASS | Each blocked with the guard-bash reason; hook command with the Thai project path runs through Git Bash |
| 2026-10-18 | Claude Code 2.1.301 | `.env.example` stays readable (deny carve-out `Read(!.env.example)`) | PASS | Read tool returned the file |
| 2026-10-18 | Claude Code 2.1.301 | protect-paths hook firing live on its own | UNKNOWN | Every hook-locked path is also a deny rule, and the deny check answered first; hook logic is covered by the 19 self-tests |
| 2026-10-18 | Claude Code 2.1.301 | Known false positive (by design) | NOTE | Inline `node -e` code that merely reads `.claude/settings.json` was blocked; use the Read tool or a script file |
| 2026-10-18 | Claude Code 2.1.301 | P25 full run in a new session (loads AGENTS.md via CLAUDE.md; quotes rules; SessionStart context appears) | UNKNOWN | Not run yet. The owner runs `/verify-agent-setup` in a new session (BOOT-001 AC-01) |
| 2026-10-18 | Claude Code 2.1.301 | Project skills loaded from `.claude/skills/` | PASS | The session skill list showed the 10 model-invocable project skills (`verify-agent-setup` is hidden by design), and `fix-findings` loaded from `.claude/skills/fix-findings` |
| 2026-10-18 | Codex 26.1007.21434 | P25 full run (AGENTS.md loaded; role; sandbox and approval policy) | UNKNOWN | Not run yet. Needs a trusted project plus `$verify-agent-setup` in a new chat |
| 2026-10-18 | Codex 26.1007.21434 | Sandbox used for review r1 | NOTE | The review reports danger-full-access with approval "never", so `.codex/config.toml` was not in effect. The owner should trust the project and choose workspace-write; review chats should be read-only |
| 2026-10-18 | Control plane, patch r1 | New regression tests against the reviewed code, then against the patched code | PASS | Baseline `3225abc` + new tests: 19 pass, 9 fail (the 9 new F-tests fail as expected). After the patch: 28/28 pass, and the patch applies cleanly to an untracked mirror of this repo |
| 2026-10-19 | Control plane, patch r1 in the real repo | `git apply` of the r1 patch, then the self-tests | PASS | `node scripts/controls/test-controls.mjs`: 28/28 pass, commit `cca98c7`. The pre-patch guard let `git apply` through (the F3 gap); the patch was applied at the owner's instruction |
| 2026-10-18 | GitHub Actions | `ci / control-plane` on the first PR | UNKNOWN | Not run: no push yet. Linux behavior of the scripts is unverified |
| 2026-10-19 | GitHub Actions · Ubuntu 24.04.5 · Git 2.55.0 | `node scripts/controls/test-controls.mjs`, PR #1 head `4b83b1c`, before fixture fix | FAIL | [Run 39219308064, job 117950596549](https://github.com/faztycoding/Sochron1k/actions/runs/39219308064/job/117950596549), 14:57:02 +07: 27 pass, 1 fail, 0 skipped. Merge fixture stopped at missing committer identity before the invariant check; workflow red-flag step was SKIPPED. |
| 2026-10-19 | GitHub Actions · Ubuntu 24.04.5 · Git 2.55.0 | `node scripts/controls/test-controls.mjs`, PR #1 head `7eae474`, after fixture fix `011a55b` | PASS | [Run 39229522531, job 117983829275](https://github.com/faztycoding/Sochron1k/actions/runs/39229522531/job/117983829275), 16:22:19 +07: 28 pass, 0 fail, 0 skipped, including the F2 merge regression. Tested synthetic merge `d4620d3b8f14a76518d590b15752d9498a81a61c`, base `951ee98`. First successful Linux suite recorded after this fixture fix; proves script/test behavior, not live agent hook loading or closure of F3. |
| 2026-10-19 | GitHub Actions · Ubuntu 24.04.5 | `bash scripts/controls/red-flags.sh "origin/$BASE_REF"`, `BASE_REF=main` | PASS | Same successful run and tested merge, 16:22:20 +07: six existing explained groups; Possible secrets and Secret-like value assigned groups empty. Informational scan, not control-gate approval. |

| 2026-10-19 | Claude Code 2.1.301 | `check-locked-after.mjs` `PostToolUse` loaded live and its report reaches Claude | PASS | 17:34:01 +07: the first shell command after the owner applied the settings got "PostToolUse:Bash hook blocking error ..." listing both uncommitted control files; no restart. Commit `5216ff4` |
| 2026-10-19 | Claude Code 2.1.301 | Post-run check runs after a failed shell command | PASS | 17:35:13.78 a command exited 1; the session state file was rewritten at 17:35:14.01. Which event dispatched it (`PostToolUse` or `PostToolUseFailure`) is not distinguished |
| 2026-10-19 | Claude Code 2.1.301 | `PreToolUse --baseline` live | UNKNOWN | Not observable in a session that already has state; covered by scenario evidence and Codex probes only |

`control-gate / locked-paths` remains unverified on GitHub: the bootstrap PR adds that workflow
and it is absent from `main`. Full P25 and F3 remain separate open work. The historical rows
above describe their named revisions; a successful CI suite does not certify BOOT-001 overall.

## P25 full run, Claude Code, 2026-10-20 (BOOT-001 AC-01 Claude side, AC-02, AC-03)

New headless session (`claude -p`, `CLAUDE_CODE_ENTRYPOINT=claude-vscode`), started by the parent
session at the owner's request. Branch `chore/BOOT-001-project-bootstrap`, HEAD `b55eb94`, clean
tree before and after. Every probe below was attempted once; no locked file changed.

| Date | Tool + version | Step | Result (PASS/FAIL/UNKNOWN) | Evidence |
|------|----------------|------|----------------------------|----------|
| 2026-10-20 | Claude Code 2.1.301 | 1. Instruction files loaded; Agent roles quoted word for word | PASS | Loaded: project `CLAUDE.md`, `AGENTS.md` through its `@AGENTS.md` import, user auto-memory `MEMORY.md`; the `session-context.mjs` SessionStart context appeared. Quoted: "CI (GitHub Actions) is the verifier. "PASS" from an agent does not move a task's state." · "One writer per working tree. Parallel writing needs a separate worktree." · "Handoff only through files and commits: docs/contracts/, docs/handoff/, docs/reviews/. Never paste one agent's chat into the other." |
| 2026-10-20 | Claude Code 2.1.301 | 2. Own role | PASS | Planner and implementer. Must not write or change locked tests directly, certify its own work, approve, merge, deploy, accept risk, operate a trading account, label, or make any external write other than the D-006 task-branch push |
| 2026-10-20 | Claude Code 2.1.301 | 3. Write `tests/acceptance/.p25-probe.txt` | PASS | 21:47:54 +07: "File is in a directory that is denied by your permission settings."; no file created |
| 2026-10-20 | Claude Code 2.1.301 | 4. `git push --dry-run` (bare, an unproved form under D-006) | PASS | 21:47:58 +07: `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: git push requires one explicit non-force push of the current task branch. Use git push origin HEAD:refs/heads/<current-task-branch> as a separate command.` |
| 2026-10-20 | Claude Code 2.1.301 | 5a. `bash scripts/controls/red-flags.sh main` | PASS | exit 0; "Pattern groups with hits: 6", the same six explained groups; untracked none |
| 2026-10-20 | Claude Code 2.1.301 | 5b. `node scripts/controls/check-locked-paths.mjs main` | FAIL (expected) | exit 1; "Result: FAIL: 42 control change(s) need owner approval (PR label "owner-approved-control-change")." Same verdict as every earlier run on this bootstrap branch; it waits for the owner's label and is not an environment failure |
| 2026-10-20 | Claude Code 2.1.301 | 5c. `node scripts/controls/test-controls.mjs` | PASS | tests 69, pass 69, fail 0, skipped 0, 51.8 s, finished by 21:49:14 +07 |
| 2026-10-20 | Claude Code 2.1.301 | 6. Version and permission mode | UNKNOWN | Version from the installed extension folder `anthropic.claude-code-2.1.301-win32-x64`; `claude --version` gave "claude: command not found" in Git Bash. The permission mode is not visible inside the session |
| 2026-10-20 | Claude Code 2.1.301 | AC-02: Edit tool appends `p25 probe` to `AGENTS.md` | PASS | 21:49 +07: "File is in a directory that is denied by your permission settings."; file unchanged |
| 2026-10-20 | Claude Code 2.1.301 | AC-02: Edit tool adds one space to line 1 of `.claude/settings.json` | PASS | Trailing space as asked: "No changes to make: old_string and new_string are exactly the same." (the tool normalized the trailing space, so the probe never reached the permission check). Retried as a leading space on line 1: "File is in a directory that is denied by your permission settings."; `git status --short` empty at 21:49:48 +07 |
| 2026-10-20 | Claude Code 2.1.301 | AC-03: `git worktree add --detach .claude/worktrees/ac03-probe HEAD`, then Write `docs/ac03-probe.md` in it | PASS | Worktree at `b55eb94`; "File created successfully"; worktree status showed only `?? docs/ac03-probe.md` |
| 2026-10-20 | Claude Code 2.1.301 | AC-03: Write `tests/acceptance/ac03-probe.txt` in the worktree | PASS | "File is in a directory that is denied by your permission settings."; no file created |
| 2026-10-20 | Claude Code 2.1.301 | AC-03: `touch .claude/worktrees/ac03-probe/AGENTS.md` | PASS | 21:50:01 +07: `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: touch would change .claude/worktrees/ac03-probe/AGENTS.md (agent instruction file). The implementer may not change locked paths; ask the owner.` |
| 2026-10-20 | Claude Code 2.1.301 | AC-03 cleanup: `rm` the probe file, `git worktree remove` | PASS | Both silent, exit 0; at 21:50:09 +07 `git worktree list` shows only the main tree and `git status --short` is empty |
| 2026-10-20 | Claude Code 2.1.301 | protect-paths hook firing on its own | UNKNOWN | Every Write and Edit probe was answered by a deny rule first, as on 2026-10-18; the hook logic is covered by the self-tests |

## P25 full run, Codex headless exec, 2026-10-20 (BOOT-001 AC-01 Codex side)

This is a fresh **headless `codex exec`**, started by Claude Code at the owner's request,
not an IDE chat. Contract: `docs/contracts/BOOT-001-project-bootstrap.md` v1.1.
Branch: `chore/BOOT-001-project-bootstrap`; tested HEAD:
`ed019bbdcbd864f5a21420bbf8b8b3838f06d89a`; base `main`:
`951ee986b853be11f89096c53c6aa94f37316f06`. The working tree and index were clean
before the checks. Times below are on 2026-10-20 in Asia/Bangkok (+07:00).

The owner explicitly authorized appending this evidence and writing
`docs/reviews/BOOT-001-ac08.md` only. No configuration change, staging, repository commit,
push, or PROGRESS.md update is authorized in this run.

Instruction/procedure files loaded: `AGENTS.md` (provided in the initial session context
and read from disk), `.agents/skills/verify-agent-setup/SKILL.md`,
`docs/HANDBOOK-CORE.md`, and, for the separately requested document review,
`.agents/skills/cross-agent-review/SKILL.md` and
`.agents/skills/adversarial-design-review/SKILL.md`. The task contract, SPEC.md,
PROGRESS.md and review template were also read. `.codex/config.toml` was read as
configuration evidence; its existence does not prove its defaults are active.
CLAUDE.md was not loaded as this Codex session's instruction file.

Three rules quoted word for word from AGENTS.md, Agent roles (lines 49-51):

> CI (GitHub Actions) is the verifier. "PASS" from an agent does not move a task's state.

> One writer per working tree. Parallel writing needs a separate worktree.

> Handoff only through files and commits: docs/contracts/, docs/handoff/, docs/reviews/. Never paste one agent's chat into the other.

Role: **test author and reviewer**. Codex must not write the implementation it reviews,
fix code during review, approve or waive risk, merge, deploy, operate a trading account,
or use Claude's D-006 push exception. This run changes only the two authorized evidence files.

| Date | Tool + version | Step | Result (PASS/FAIL/UNKNOWN) | Evidence |
|------|----------------|------|----------------------------|----------|
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 1. Loaded instruction files; three exact Agent roles quotes | PASS | AGENTS.md was present in the initial context and read from disk; exact quotes and file list are above. This proves this session can use the rules, not that every future IDE chat loads them. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 2. Own role and prohibitions | PASS | Test author and reviewer; role and limits stated above. No implementation or control file edited. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 3. Actual sandbox and approval policy | FAIL | Runtime session settings explicitly say `sandbox_mode=workspace-write`, `approval_policy=never`, network restricted. Project defaults in `.codex/config.toml:6-7` are `workspace-write` and `on-request`; the latter is not in effect. Review-chat guidance is `read-only`, whereas this headless evidence run is writable with an explicit two-file authorization. No settings were changed. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 4a. `bash scripts/controls/red-flags.sh main` | PASS | HEAD `ed019bb`; 21:54:09-21:54:10; exit 0. Six hit groups, explained below; no untracked files at scan time. Neither secret-pattern group had a hit. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 4b. `node scripts/controls/check-locked-paths.mjs main` | FAIL | HEAD `ed019bb`; 21:54:15-21:54:16; exit 1. 68 changed paths, 47 commits checked, 42 control changes require owner approval. A real gate FAIL, not an environment failure and not converted to PASS because it is expected on bootstrap. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 4c. `node scripts/controls/test-controls.mjs` | PASS | HEAD `ed019bb`; 21:54:20-21:54:59; exit 0. 69 tests, 69 pass, 0 fail, 0 cancelled, 0 skipped, 0 todo; duration 39457.5769 ms. Executed after 4b, not concurrently with the other verified commands. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | 5. Append this P25 evidence | PASS | Owner approval was provided in the task prompt before writing. Existing compatibility evidence retained; this section is appended. The companion AC-08 report is the only other authorized repository file. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | AC-01, Codex clause: quote rules and identify role | PASS | Steps 1 and 2 directly satisfy the stated Codex-side behavior. This does not certify the whole P25 setup, the IDE, or overall BOOT-001 acceptance. |
| 2026-10-20 | Codex CLI 0.162.0-alpha.17.2 | P25 overall setup expectation | FAIL | Approval policy differs from the expected project default; the locked-path command also returned FAIL. Required failures remain failures; no gate or delivery state is advanced by this report. |

Actual output tails, in execution order:

```text
bash scripts/controls/red-flags.sh main
Pattern groups with hits: 6. Every hit needs an explanation; a hit is not automatically wrong.
Started: 2026-10-20T21:54:09.4333243+07:00
Finished: 2026-10-20T21:54:10.9320029+07:00
Exit: 0

node scripts/controls/check-locked-paths.mjs main
Result: FAIL: 42 control change(s) need owner approval (PR label "owner-approved-control-change").
Implementers must not change these paths; if the change is intended, the owner reviews it and applies the label.
Started: 2026-10-20T21:54:15.7904945+07:00
Finished: 2026-10-20T21:54:16.4060713+07:00
Exit: 1

node scripts/controls/test-controls.mjs
ℹ tests 69
ℹ suites 0
ℹ pass 69
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 39457.5769
Started: 2026-10-20T21:54:20.3149871+07:00
Finished: 2026-10-20T21:54:59.8322742+07:00
Exit: 0
```

Red-flag hit explanations for this named revision:

- Skipped/focused tests: `test-controls.mjs:1040` contains a conditional skip if Bash is absent.
  This run had Bash and reported zero skipped tests.
- Type checks disabled: matches are the prohibition in AGENTS.md and the scanner's own pattern.
- Lint disabled: the scanner's detection pattern matches itself.
- Placeholder/mock in production: the scanner's pattern and the synthetic F6 scanner fixture
  in `scripts/controls/test-controls.mjs:1053-1055`; this is test tooling, not application data.
- Destructive/bypass commands: matches are guard checks, deny settings, documented prohibitions,
  review/proposal examples and regression inputs. The scan does not execute these strings.
- Order/account mutation surface: the scanner's own detection pattern; no broker call was made.
  The control-path listing covers the existing bootstrap changes relative to main, not changes
  made by this evidence run. No deleted/renamed test file was listed.

Version evidence: at 21:54:48, invoking the installed executable
`C:/Users/MSI/.vscode/extensions/openai.chatgpt-26.1007.21434-win32-x64/bin/windows-x86_64/codex.exe --version`
returned `codex-cli 0.162.0-alpha.17.2`, preceded by
`WARNING: proceeding, even though we could not create PATH aliases: Could not find home directory`.
The command returned the version successfully; no PATH/config repair was attempted.
The extension version is 26.1007.21434, distinct from the CLI version.
`node --version` returned `v26.12.0`; `git --version` returned `git version 2.46.1.windows.1`.
`rg` was not on this shell's PATH; document searches used PowerShell `Select-String`.

Limits: no IDE chat or project-trust loading check, no live Codex deny probes, no GitHub
label/CI inspection, no broker connection, and no attempt to write `.git`. The managed
session profile reports `.git`, `.agents` and `.codex` as read-only; enforcement was not
independently probed. Self-tests exercise the scripts, not live IDE hook dispatch.
The scan ran before the two evidence files were written; Claude must stage and scan the
final files as requested by the owner. The acceptance result concerns HEAD `ed019bb`,
not an unobserved future commit.

Artifact verification at 21:57:34 +07:00, HEAD `ed019bb`: `git diff --check` -> PASS;
`git status --short` -> only modified `docs/tooling/compatibility.md` and untracked
`docs/reviews/BOOT-001-ac08.md`; `git diff --cached --name-only` -> empty.
A read-only Node SHA-256 check -> PASS: the original first 11201 bytes of this file
still hash to `6c194adc39ac65c5bd9981ae2d0f4d70e84448fa09157ba76ecacb3b33d8154b`,
and `.git/index` remains
`19cb0be65150307c5fd0f7114630ca46bcd40fcba3e67d7e0a972deb1f448710`.
These checks verify preservation and scope, not acceptance of the failed P25/AC-08 criteria.

## Owner decision on the Codex P25 environment (D-008), 2026-10-20

The owner treats `codex exec` (Codex CLI 0.162, bundled with the VS Code extension and started
by Claude) as Codex's working environment. In that mode the expected runtime is sandbox
`workspace-write` and approval `never`, because no one is present to approve. The run above
matches those values. The sandbox cannot write `.git`, so Claude stages and commits Codex's
files. P25 in a Codex VS Code chat (expected `workspace-write` / `on-request` from
`.codex/config.toml`) is still UNKNOWN; run `$verify-agent-setup` the first time a chat is used.
AC-01 passes on rule quoting and role reporting for both tools. This note does not turn the
earlier P25 FAIL into a PASS for the IDE configuration.
