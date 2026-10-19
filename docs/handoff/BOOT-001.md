# Handoff BOOT-001 · contract v1 · commit: none (uncommitted; the owner has not asked for a commit)

Base `main` @ `951ee98`. Round-1 review: `docs/reviews/BOOT-001-r1.md`. This note covers the fixes for round 2.

## How the fixes are delivered
Claude cannot edit locked files: deny rules and hooks block it, by design (D-004). Fixes to locked
files are therefore a patch for the owner to review and apply:
- `docs/proposals/BOOT-001-r1-controls.patch` (gitignored), sha256 `80d4aecfff3ff574b8080cd77b085247dd64fa6fd9969b430ac4294d645cb4eb`
- Apply from the repo root, in the owner's own terminal: `git apply docs/proposals/BOOT-001-r1-controls.patch`
- Then run `node scripts/controls/test-controls.mjs`; expected 28 pass, 0 fail.
Fixes to unlocked files (documents) are already in the working tree.

## Claimed passing (command → result)
- Scratch clone r1 (baseline `3225abc` = the reviewed files, plus the patch): `node scripts/controls/test-controls.mjs` → 28 pass, 0 fail (Windows 11, Node v26.12.0, bash 5.2.32)
- The new test file run against the baseline code → 19 pass, 9 fail: exactly the 9 new F-tests, so each fails before its fix
- Patch applied to an untracked mirror of the real repo: `git apply --check` OK, `git apply` OK, 28/28 pass, all 7 files byte-identical to the tested versions
- `bash scripts/controls/red-flags.sh 951ee98` on the fixed tree: "Possible secrets" and "Secret-like value assigned" groups empty

## Not verified
- GitHub: `control-gate.yml` (pull_request_target) has never run; branch protection is not set (owner action)
- Linux behavior of the scripts (no WSL on this machine); the first CI run is the first Linux evidence
- P25 in new sessions of Claude Code and Codex
- The F6 test needs bash; where bash is missing it reports SKIPPED, not PASS

## Files touched
- Patch (locked files): `.claude/hooks/guard-bash.mjs`, `.github/workflows/ci.yml`, `.github/workflows/control-gate.yml` (new), `AGENTS.md`, `scripts/controls/check-locked-paths.mjs`, `scripts/controls/red-flags.sh`, `scripts/controls/test-controls.mjs`
- Working tree (unlocked): `docs/architecture.md`, `DECISIONS.md`, `docs/contracts/SPIKE-001-mt5-connectivity-time.md`, `docs/contracts/BOOT-001-project-bootstrap.md`, `docs/tooling/registry.md`, `docs/tooling/compatibility.md`, `PROGRESS.md`, `README.md`, `.gitignore`, `docs/reviews/BOOT-001-r1.md` (verbatim copy of the review), this file

## Known risks
- guard-bash is still a text-level guard: programs that open files themselves (`python x.py`) are not inspected. CI control-gate is the enforcing layer.
- control-gate cannot judge the PR that introduces it, because main has no gate yet. The owner's review is the gate for BOOT-001.
- The approval label stays on a PR after new commits (N1 below); not fixed in this round.
- `docs/reviews/BOOT-001-r1.md` quotes the Supabase service-role key name verbatim, so it gives one explained red-flag hit once committed (N5).

## Please look hard at
- `control-gate.yml`: pull_request_target safety (base checkout only, PR commits fetched as data, read-only token, no PR code executed)
- `check-locked-paths.mjs`: history mode for merge commits and for uncommitted local changes
- `guard-bash.mjs`: false positives on normal commands (see the allow-list tests) and the bypass classes that remain

## Findings response (round 1)
| ID | Accept/Dispute | Change | Evidence |
|----|----------------|--------|----------|
| F1 | Accept | New `control-gate.yml`: pull_request_target, checks out the base revision only, fetches PR commits as data, runs the base copy of `check-locked-paths.mjs --base <sha> --head <sha>`; `ci.yml` no longer gates; checker gains `--base/--head` mode | Repro in scratch: the PR's tampered verifier exits 0, the base copy exits 1. Tests "F1: the base revision verifier…" and "F1: the locked-path gate judges PRs…" fail on the baseline and pass after |
| F2 | Accept | Checker evaluates every commit in merge-base..head (including merge commits) and, locally, uncommitted edits | Repro: hypothesis edited after its registration commit → baseline exit 0. Four tests (edit after registration, registry rewrite, edit inside a merge commit, uncommitted edit) fail on the baseline and pass after |
| F3 | Accept | Guard resolves the real destination: cd/pushd/Set-Location/subshells; copies into folders (`-t`, `-Destination`, directory targets); redirects and tee; output flags; archive extraction; patch targets (`git apply`, `git am`, `patch`); nested `bash -c`, `$(…)`, backticks; xargs. Tracks branch switches inside the command | Repro: 8 of 9 bypasses exit 0 on the baseline, including both reviewer examples. Two tests (21 Bash blocks, 3 PowerShell blocks, 12 allows; branch switching) fail on the baseline and pass after |
| F4 | Accept | `docs/architecture.md` §2, §7, §8, §12 and `AGENTS.md`: what MT5 timestamps mean is unverified (official Python docs: UTC; MQL5 forum: server time); SPIKE-001 AC-04/AC-05 decide it | Official docs (mt5copyratesfrom_py, mt5copyticksfrom_py): "MetaTrader 5 stores tick and bar open time in UTC time zone (without the shift)" and "Data received from the MetaTrader 5 terminal has UTC time" |
| F5 | Accept | SPIKE-001 no longer waits for D-001 and runs in a throwaway uv environment. Order: approve SPIKE-001 and the MetaTrader5 dependency admission → run SPIKE-001 → Codex adversarial review → owner decides D-001. `AGENTS.md` allows this exception | `DECISIONS.md` D-001, SPIKE-001 status line, `docs/architecture.md` §10 |
| F6 | Accept | `red-flags.sh` splits the two self-matching literals (`'pk_''live_'`, `'service''_role'`); the pattern the scanner uses is unchanged | Test "F6: red-flags reports real-looking secrets…" fails on the baseline (self-hit) and passes after: no self-hit, and the fake key and role in a fixture are still reported |

## New issues noticed (not fixed in this round; the owner decides)
- N1: The approval label persists after new commits, so a later unreviewed control change would pass. Option: remove the label on `synchronize` (needs `pull-requests: write` in the gate job).
- N2: In Codex's PowerShell, `bash` is not on PATH (the review reported BLOCKED). AGENTS.md could add `& "$env:ProgramFiles\Git\bin\bash.exe" scripts/controls/red-flags.sh main`.
- N3: The Codex review ran with danger-full-access and approval "never" (review §6), so `.codex/config.toml` was not in effect. Trust the project and choose workspace-write in the Codex UI; review chats should be read-only.
- N4: Other red-flag groups still match their own definition lines, which adds noise only when the scanner itself changes.
- N5: AC-07 says the secret groups must be empty, while the verbatim review file quotes the service-role key name. Either accept one explained hit, or reword how AC-07 is verified; I did not change the AC after seeing the result.
