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
| 2026-10-18 | GitHub Actions | `ci / control-plane` on the first PR | UNKNOWN | Not run: no push yet. Linux behavior of the scripts is unverified |
