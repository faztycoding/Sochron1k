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
