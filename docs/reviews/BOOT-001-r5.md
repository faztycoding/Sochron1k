# Review BOOT-001 round 5 · applied r5 guard fix and permanent regressions

Repository HEAD `5d38704`, base `main` (`951ee98`). Reviewed: the uncommitted guard and test
changes the owner applied from `docs/proposals/BOOT-001-r5-controls.patch`. The owner confirmed
in chat that they ran `git apply` of that patch. Reviewer: Claude Code, fresh session, not the
author of r5 (Codex). Date: 2026-10-19 (+07:00).

The applied files match the proposal:

- Patch SHA256 `953019c3c76ca54dec1cbcb029ed81f75d357874fef3b286bfad090913d112b4`.
  `git apply -R --check` passes, so the working-tree diff is exactly this patch.
- Guard SHA256 `cec6c7dc7e44380754cec50b13fe187dfe2150f1b12edf91e6d6edbb4b1679b1`, Git blob
  `cdffa1213b3987db66ab72fbaa75bba127cc1581`.
- Tests SHA256 `aca04ebd8d71527a0487c7c3231e924fd2a2c1fa3ebb892b6467a1618998fafe`, Git blob
  `c80f4886c9012f5df60014cdaae93aac571afc1e`.
- The HEAD versions match the handoff's before-hashes (guard `483c25cd…`, tests `294107ec…`).
  The posthook (`28c6283c…`) and settings (`9de3df7d…`) are unchanged.

Scope: the two F3 classes confirmed in r2 (child-shell directory scope; attached short output
operands), the per-worktree branch state that came with them, and the 17 new tests. The forms the
owner left to the post-run check on 2026-10-19 are not in scope, except where this review found a
miss that list does not name (F9).

**Result: F3's r2 proof of fix is met. The six r2 inputs now all return 2, where HEAD returned
2, 2, 0, 0, 0, 0, and the suite passes 45/45. The new grouping logic introduces one regression
in the same class (F7, High): a `cd` between backslash-escaped parentheses is treated as
subshell-scoped. As a result, a locked-path write that HEAD blocked now passes. AC-04 stays FAIL
until F7 is fixed.**

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F3 | High | closed for the r2 classes | `.claude/hooks/guard-bash.mjs:73-100`, `:448`, `:588-625` | The six r2 inputs return 2 (HEAD: 2, 2, 0, 0, 0, 0). 15 further scope, attached-operand and branch variants return 2. 14 normal Bash, PowerShell and Monitor commands return 0. The four new guard tests pass. | – | – | – | Met as worded in r2: "All three payloads return 2; existing normal-command and F3 regressions continue to pass" and "Attached locked-path output returns 2, while ordinary allowed destinations continue to pass". |
| F7 | High | confirmed, regression from r5 | `.claude/hooks/guard-bash.mjs:85-92` (no backslash escape: `\(` becomes a `(` segment), `:603-612` (cwd restored at `)`) | Hook input `echo \( ; cd .claude ; echo \) ; echo {} > settings.json`: HEAD guard exit 2, applied guard exit 0 with empty stderr. A harmless Git Bash analogue, `echo \( ; cd inner ; echo \) ; pwd`, printed `.../esc/inner`. Escaped parentheses do not scope a `cd`. | A `cd` between escaped parentheses, then a write in the parent | The guard checks `./settings.json` instead of `.claude/settings.json` and allows a locked write that HEAD blocked (AC-04). The post-run check reports it afterwards; nothing prevents it. | For POSIX syntax, have `splitSegments` treat a backslash and the next character as literal, so an escaped `(` or `)` never opens or closes a group. Alternatively, fail closed on `\(` / `\)` outside quotes. | The input above returns 2. `find . \( -name a -o -name b \) -print` and the existing allow-list still return 0. Both are added as permanent tests. |
| F8 | Low | confirmed | `.claude/hooks/guard-bash.mjs:604`, `:609`, `:616`, `:345` | New fail-closed blocks on harmless commands (HEAD 0, applied 2): Monitor `while true; do echo $(date); sleep 5; done` ("cannot determine directory scope"); Bash `case x in a) echo a;; esac` ("unmatched closing parenthesis"); `cd "$X" && git switch -c feat/x` ("cannot determine the repository"). | Ordinary commands | Safe direction, but under N6 every block stops the session until the owner answers. | Add these to the planned false-positive task. Decide Monitor's syntax (probably the Bash tool's shell), recognize `case` patterns, and record an unresolved switch as an unknown branch so that only a later commit is blocked. | Each command returns 0 while the r2 and F7 inputs still return 2. |
| F9 | Medium | question | `.claude/hooks/guard-bash.mjs:382` (`SHELL_FLAG`), `:132-159` (`tokenize` has no escapes) | HEAD and applied both return 0: `cmd //c "echo {} > AGENTS.md"` (the Git Bash spelling of `/c`, so the nested string is never analyzed) and `echo \"; cd .claude; echo {} > settings.json` (the escaped quote swallows the rest). Neither form is in the 21-form list the owner sent to the post-run check (handoff "Round 2 handoff", task 2). | Either form with a locked target | Pre-existing prevention gaps with the same impact as F3. The post-run check detects them after the fact. Medium rather than High because of that layer and the owner's 2026-10-19 decision on unmodelled forms. | Owner decides: either these fall under the 2026-10-19 decision (they go to the follow-up guard task), or they are fixed in this PR. | – |

Also observed and already covered by the owner's decision (option clusters, in the 21-form list):
`bash -lc "echo {} > AGENTS.md"` and `curl -sSoAGENTS.md https://example.invalid/a` return 0
before and after. These are not findings in this round.

## Independent checks

Every guard probe was sent to the hook as JSON on stdin; no payload command was executed. The
only shell execution was the harmless F7 analogue above, run in a scratch folder with `pwd` and
no write.

Probe script and evidence (local, gitignored), run from any directory:
`node docs/proposals/BOOT-001-r5-review-probe.mjs <repo-root> <scratch-dir>`.

- The script runs each case against the applied guard in place and against a scratch copy of
  the HEAD guard. The copy differs only in its `rules.mjs` import, which becomes an absolute
  file URL.
- Script SHA256 `9495e082b658680fb8bfc87bee42c3d13086576fa3cf648b474772ac6db679f5`.
- Evidence `docs/proposals/BOOT-001-r5-review-evidence.json`, SHA256
  `63ef6e135855e1008f2127f27230ede69d873a1697637ec6c004b7faad7835ba`. It holds 45 cases with
  before/after exits and stderr.

| Group | Cases | Expected (applied guard) | Observed |
|-------|-------|--------------------------|----------|
| r2 inputs (review r2 "Hook-only reproduction") | 6 | 2 each | 2 each. HEAD: 2, 2, 0, 0, 0, 0 |
| Directory scope: `$(...)`, quoted `$(...)`, backticks, `sh -c`, groups, `pushd`/`(popd)`, PowerShell and cmd parentheses | 9 | 2 | 2. Three of them were 0 at HEAD |
| Attached operands: `wget -O…`, `sort -o…`, `curl -o"…"` | 3 | 2 | 2. All 0 at HEAD |
| Branch: switch in a subshell, in a subfolder, then commit | 3 | 2 | 2 |
| Normal commands (Bash, PowerShell, Monitor) | 14 | 0 | 0 |
| Limits (F7, F8, F9 and known option clusters) | 10 | observed only | See the findings table |

| Command | Result | Tested revision | Time, 2026-10-19 (+07:00) |
|---------|--------|-----------------|---------------------------|
| `sha256sum` of patch, guard, tests, posthook, settings; `git hash-object` of guard and tests | PASS: all match the handoff | `5d38704` + applied r5 | 18:18:01 |
| `git apply -R --check docs/proposals/BOOT-001-r5-controls.patch` | PASS: the diff equals the patch | same | 18:18:01 |
| `git show HEAD:<file> \| sha256sum` for guard and tests | PASS: match the handoff's before-hashes | `5d38704` | 18:18:09 |
| `node scripts/controls/test-controls.mjs` | PASS 45/45, fail 0, skipped 0, 25.6 s | `5d38704` + applied r5 | 18:18:09-18:18:35 |
| `node docs/proposals/BOOT-001-r5-review-probe.mjs …` (first 43 cases) | PASS: 0 mismatches on expected cases | same | 18:21:40 |
| Same script, 45 cases including escaped parentheses | PASS on expected cases; F7 observed | same | 18:23:19 |
| Git Bash `echo \( ; cd inner ; echo \) ; pwd` in a scratch folder | Printed `…/esc/inner` | – | 18:24 |

Node `v26.12.0`, Git `2.46.1.windows.1`, Windows 11. Results of the scan and commit steps are in
the handoff section that refers to this review.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-04 | FAIL | F7: a locked-path write that HEAD blocked passes the applied guard. The r2 classes themselves pass. |
| AC-06 | PASS | `bash scripts/controls/red-flags.sh main` with both r5 files staged: exit 0 and six explained groups (18:26:15). |
| AC-07 | PASS | In the same scan both secret groups are empty, and the r5 diff adds no hit. |
| AC-01/02/03/05/08 | UNKNOWN in this review | No new P25, gate or architecture evidence. |

## Checked, nothing found (and how)

- The test diff only adds lines (272 insertions, 0 deletions), so the original 28 tests and
  their assertions are unchanged. The four guard tests include allow-lists. Posthook fixtures use
  their own temporary repositories and point `TMP`/`TEMP`/`TMPDIR` at their own state folder.
  Cleanup asserts that the folder is directly under `os.tmpdir()` with the expected prefix.
- Per-worktree branch state: a switch in a subshell, nested shell or substitution stays visible
  to the parent (correct, because a switch changes the worktree). A switch in another repository
  does not affect the parent. Covered by both the suite and the probes.
- PowerShell and cmd parentheses keep the caller's directory, which matches both shells. Only
  POSIX groups and POSIX substitutions restore cwd.
- The attached-operand rule applies only to the listed single-letter flags, compares case
  exactly (`-O` and `-o` stay distinct), and is not applied to PowerShell cmdlets.
- Unknown-syntax tools (Monitor) fail closed on parentheses and substitutions rather than guess.
  F8 records the usability side.

## Not checked (and why)

- Linux: there is no CI run on a head that contains r5. The owner pushes.
- Codex's `BOOT-001-r5-verify.mjs before|after` was not rerun. This review's before/after
  comparison uses its own HEAD-copy probe.
- No complete shell-parser review. Heredoc, pipelines, option clusters and new command families
  stay outside this patch, as the handoff states. F9 lists two misses outside that list.
- Live dispatch: no new evidence beyond `8ad0895`.
- The posthook itself was reviewed in r3 and r4. Here only its new tests were read and run.

## Handoff

Do not reapply the patch: the applied files are committed with this review. Next:

- Owner: push when ready (CI on the new head gives Linux evidence for the 45 tests).
- F7 needs a small guard patch and a regression test. Under the current role binding, Codex
  writes it, the owner applies it, and a fresh Claude session reviews it.
- The owner answers F9.
- F8 goes to the planned false-positive task.
- Do not add the `owner-approved-control-change` label while F7 is open.

Delivery: implemented, with local verification on Windows. Not verified by CI, not merged.
