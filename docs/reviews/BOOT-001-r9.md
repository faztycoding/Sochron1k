# Review BOOT-001 round 9 · applied r9 controls (F18 and revised D-006)

Repository HEAD `c764cda`, base `main` (`951ee98`). Reviewed: the five uncommitted locked files the
owner applied from `docs/proposals/BOOT-001-r9-controls.patch`. The owner stated this in the
session prompt, relayed by the parent Claude Code session. Reviewer: Claude Code, a fresh headless
session (`claude -p`). It did not author r9 (Codex wrote it) and did not propose its approach.
Date: 2026-10-20 (+07:00).

The applied files match the proposal:

- Patch SHA256 `68351d1f623d019b9aa44ed7f005efe519f79d20ad51a42dd3e945269177700c`.
  `git apply -R --check` passes, so the working-tree diff is exactly this patch.
- All five applied files match the handoff ("R9 proposal", "Patch and expected applied files")
  in both SHA256 and Git blob:

  | File | SHA256 | Blob | Diff |
  |------|--------|------|------|
  | `.claude/hooks/guard-bash.mjs` | `cab5ddf3…` | `8fdef64c…` | +86 −10 |
  | `scripts/controls/test-controls.mjs` | `a7ef3e4b…` | `14c58e68…` | +185 −1 |
  | `.claude/settings.json` | `72179bc6…` | `4801a73d…` | +0 −2 |
  | `AGENTS.md` | `e4ae3241…` | `90c2a5b3…` | +14 −5 |
  | `CLAUDE.md` | `b47c048e…` | `dd08b545…` | +11 −1 |

- The HEAD blobs are the r8 guard and tests (`98ab688b…`, `ec961f6b…`) and the earlier settings
  (`01f74bb…`). The posthook (`28c6283c…`) is unchanged.

Scope covers two items:

- F18, judged against the r8 proof of fix, and whether F10 returns.
- The revised D-006: the push and apply exceptions, the single-invocation rule, settings, and
  the AGENTS.md/CLAUDE.md text against DECISIONS.md D-006.

F11 to F17 and F19 stay deferred by owner decision and were not reopened.

**Result:**

- F18 meets its r8 proof of fix. F10 does not return, and the suite passes 69/69 with 0 skipped.
- D-006 behaves as specified in every probed case:
  - The explicit task-branch push and a standalone apply of a `docs/proposals/` patch return 0
    with empty stdout.
  - Force, deletion, multi-ref, main/master, non-task branches and every other probed push
    form return 2.
  - Settings have no push or apply rule in `deny`, `ask` or `allow`. The reset and clean deny
    rules remain.
  - The AGENTS.md and CLAUDE.md hunks match D-006 and the handoff requirements, and change no
    other section.
- New findings: one Medium and three Low. F20 Medium shares F18's root cause but is not a
  regression from r8 (0 before and after). F21 is usability, F22 fails closed, and F23 is
  whitespace. None blocks committing the applied files.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F18 | High | closed | `.claude/hooks/guard-bash.mjs:108-115`, `:178-179`, `:212-213`, `:244-251` (process substitution is a word fragment in all four scanners) | Hook input `echo <(pwd)#; cd .claude; echo {} > settings.json`: HEAD (r8) 0, applied 2, locked-settings reason. Same for `>(pwd)#`. `echo <(pwd) #; …` and `echo >(pwd) #; …`: 0. `(pwd)# C:\`, newline, `cd .claude; echo {} > settings.json`: 2. The six F10 inputs give the same results as HEAD (two 2s with the reason, four 0s). A locked write inside a process substitution still returns 2 (3 of 3). Permanent tests: the two F18 groups at `scripts/controls/test-controls.mjs:1066-1093`; the F10 groups pass in the 69/69 run. Git Bash 5.2.32 analogue in the scratch folder (21:17): `echo <(pwd)#; cd ..; pwd` printed `/dev/fd/63#`, then the parent folder, the same fact r8 recorded. | – | – | – | Met as worded in r8: both inputs return 2 with the locked-settings reason; the spaced form returns 0; `(pwd)# C:\` still returns 2; the F10 tests still pass; all are permanent tests. |
| F20 | Medium | open, same root cause as F18, not a regression (HEAD 0, applied 0); placement: owner | `:95`, `:141` (a `#` at `wordStart` after a `)` still starts a comment for other word-internal parentheses) | Hook input `echo @(pwd)#; cd .claude; echo {} > settings.json`: HEAD 0, applied 0. Same for `a=(x)#; cd .claude; echo {} > settings.json`. Bash analogue (21:17, extglob off, which `shopt extglob` shows for this tool's shell): `… && pwd && echo @(pwd)#; cd ..; pwd` is a syntax error, and nothing on the line ran, not even the first `pwd`. With extglob on, and for the array form, Bash behavior was not executed: enabling extglob and assigning an array are outside the owner's cd/pwd/echo allowance. r8 listed these forms under "Not checked". | `#` directly after the `)` of an extglob pattern or a compound array assignment, followed by `cd` and a write | If Bash keeps the `#` in the word, as it does for F18, the guard misses the `cd` and the write. In this shell configuration the extglob form does not run at all. The array form is unproven. The post-run check would report a locked write afterwards. | Treat these parentheses as word fragments like process substitution, or fail closed on an unquoted `#` directly after a `)` that does not close a subshell or group. A subshell `)` must stay a boundary, or F10 returns. | Both inputs return 2. `(pwd)# C:\`, newline, `cd .claude; echo {} > settings.json` still returns 2. `echo <(pwd) #; …` still returns 0. The F10 and F18 tests still pass. Bash evidence for the array form and for extglob on, from an owner-approved analogue. |
| F21 | Low | open, usability (recorded at the owner's request; severity agreed) | `:538-540` (requirement 4 applies to every `git apply`, inspection included) | Hook input `git apply --check docs/proposals/p.patch; echo x` in a fixture: HEAD 0, applied 2. Live in this session: `cd "<repo>" && git apply -R --check docs/proposals/BOOT-001-r9-controls.patch; echo "exit=$?"; date …` was blocked with "git apply must be one standalone literal command" (block 2 below). The same check alone passed. The handoff's earlier verified checks ran in combined forms like this one. | Any `git apply --check`, `--stat`, `--numstat`, `--summary` or `-R --check` combined with `cd`, `;`, `&&`, pipes or redirection | A read-only check that used to pass now blocks. Under N6, every such block stops a headless session until the owner answers. Recorded commands from earlier rounds no longer run as written. | The rule is deliberate (handoff: "This includes ordinary and inspection apply commands, so combining them cannot escape the rule"). Minimal fix is documentation: list `git apply -R --check <patch>` and `git apply --check <patch>` as standalone commands in AGENTS.md "Verified commands" and in future handoffs, and read the exit status in a separate step. | Next handoff and AGENTS.md show inspection checks only in standalone form, and a session following them runs without a block. |
| F22 | Low | open, fails closed | `:476-484` (`realpathSync(projectDir)` keeps the input's spelling; the patch path goes through `locate`, which resolves the on-disk spelling with `realpathSync.native`) | Hook input `git apply docs/proposals/p.patch` in a fixture whose folder is `c--Users-…` on disk: with `CLAUDE_PROJECT_DIR` spelled `C--Users-…` → 2, with the on-disk spelling → 0 (Bash and PowerShell). The real repository with `c:/users/msi/desktop/โปรเจคต่างๆ/sochron1k` → 2; with the spelling Claude Code uses here → 0. `realpathSync` and `realpathSync.native` disagree on that folder name (diagnostic in the scratch folder). The permanent test passes because `os.tmpdir()` already has the on-disk spelling. | `CLAUDE_PROJECT_DIR` or `cwd` differs from the on-disk path only in letter case, which Windows allows | The D-006 apply exception silently does not apply. The command falls back to the locked-path block, so nothing unsafe passes, but a permitted apply stops the session. This session's own scratch path has exactly such a mismatch. | Resolve the project root and the patch path the same way (native realpath on both sides, or a case-insensitive comparison on win32) before comparing them. | A permanent test with a differently cased `projectDir` returns 0 for the direct proposal patch. The junction, nested, missing and outside cases still return 2. |
| F23 | Low | open, whitespace | `scripts/controls/test-controls.mjs:1247` (patch line 371) | `git diff --check` → `scripts/controls/test-controls.mjs:1247: new blank line at EOF.` (exit 2). The file ends with an empty line after the last test. No CI or control script runs a whitespace check (grep of `.github/**` and `scripts/**` for `diff --check` or `whitespace` finds nothing). The owner chose to commit with this issue, and the commit message records it. | – | Cosmetic. `git diff --check` and `git diff --cached --check` on this file fail until it is fixed, so they cannot serve as a clean gate for commits that include it. | Remove the trailing empty line in the next controls patch. | `git diff --check` on that patch reports nothing for this file. |

(In the F18 row, "HEAD" means the committed r8 guard, a scratch copy that differs only in its
`rules.mjs` import.)

Also observed, not raised as findings:

- **Push shorthand.** `git push origin chore/BOOT-001-project-bootstrap` returns 0 in the real
  repository because `remote.origin.push` is unset. The guard allows this by design (handoff
  requirement 2). AGENTS.md and CLAUDE.md tell Claude to use the explicit
  `HEAD:refs/heads/<branch>` form. The text is stricter than the guard, so they do not conflict.
- **Remote identity.** The guard checks that the remote name exists. It does not pin the
  remote's URL. D-006 does not ask for this. Noted for the owner.
- **Who writes proposals.** `docs/proposals/` is not locked, and the exception covers any regular
  file directly in it. D-006 "Risk" accepts this: the patch is reviewed after apply, and the
  remaining gates are the CI control-gate, the owner's label and the post-run check.
- **Stricter than required.** Dry-run (`-n`), `--atomic`, `--prune`, `--tags` and
  `--follow-tags` pushes, `git apply -R <proposal>` and `--3way` all return 2.
- **Records that now lag behind D-006.** DECISIONS.md D-006 still says "ยังไม่ implement". D-004
  still says the owner applies patches and agents never push; D-006 supersedes those parts "เมื่อ
  implement แล้ว". BOOT-001 AC-04 still lists push among the commands the guard must block. The
  owner decides when to update these. This review does not change them.

## Session events and owner answers

- **Post-run report.** The session's first shell command got the post-run report for exactly
  the five r9 target files. The owner's prompt had confirmed that these were the applied r9
  files. Under the amended CLAUDE.md rule, Claude verified every expected SHA256 and blob
  (21:01:57) before continuing.
- **Safety classifier, twice.** One response, after reading the guard source, and one after a
  realpath diagnostic, were stopped by the tool's safety classifier, not by a hook. Their
  withheld content was not reproduced. The review continued with the narrower probe set below:
  recorded inputs, proof-of-fix inputs, the D-006 requirement lists and ordinary commands.
- **Block 1**, guard-bash on `mkdir -p "$S/r9probe" && … node … "$S/r9probe" …`, where `$S`
  is the session scratchpad outside the repository. The command did not run:

  ```text
  PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: mkdir would change $S/r9probe (a path that cannot be resolved here (variable or unknown directory)). The implementer may not change locked paths; ask the owner.
  ```

  Claude stopped and asked. Owner answer, relayed by the parent session under the owner's
  standing permission for terminal commands ("อนุญาติทุกครั้งตลอด"): option 1. Rerun the same
  commands with the literal scratchpad path in place of `$S`. Harmless Bash analogues there are
  allowed (cd, pwd and echo only, no writes). For the rest of this session the same answer
  covers that block class: a guard-bash block on a variable path that points to the scratchpad
  outside the repository, which Claude replaces with the literal path. Any other block still
  means stop and ask.
- **Block 2**, guard-bash on `cd "<repo>" && git apply -R --check docs/proposals/BOOT-001-r9-controls.patch; echo "exit=$?"; date '+%H:%M:%S'`.
  The command did not run:

  ```text
  PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run each action separately.
  ```

  Claude stopped and asked. Owner answer, relayed the same way: option 1. Rerun as the
  standalone command `git apply -R --check docs/proposals/BOOT-001-r9-controls.patch` from the
  repository root, with no cd, `;` or echo, and read the exit status separately. For the rest of
  this session, a guard-bash message that a `git apply` or `git push` must be one standalone
  command is answered by rerunning the same action alone. Any other block still means stop and
  ask. Also record F21. No later block occurred.
- **Live dispatch.** Block 2 is live evidence that the r9 guard enforces requirement 4 in a
  headless session. The standalone inspection then ran with no prompt and no block. No push and
  no non-inspection apply ran in this session.

## Independent checks

Every guard probe was sent to the hook as JSON on stdin, and no payload command was executed.
D-006 cases ran in throwaway fixture repositories in this session's scratch folder. Each fixture
had a task branch, a reserved-domain remote that is never contacted, and patches in and outside
`docs/proposals/`. The guard ran only its own read-only `git rev-parse`, `git remote` and
`git config --get-all` calls there. Two shell analogues ran in Git Bash 5.2.32(1) in the scratch
folder, using only `cd`, `pwd`, `echo` and process substitution of `pwd`. They wrote no files.

Probe scripts and evidence (local, in the gitignored `docs/proposals/`):

- `BOOT-001-r9-review-probe.mjs`, SHA256
  `13182b2ddb765ccac10e1257e9f82e906788f2ae51ac0c9afafe667ce9f75f69`. Usage:
  `node docs/proposals/BOOT-001-r9-review-probe.mjs <repo-root> <scratch-dir> <evidence-json>`.
  It runs each case against the applied guard and against a scratch copy of the HEAD guard. The
  copy differs only in its `rules.mjs` import.
- Evidence `BOOT-001-r9-review-evidence.json`, SHA256
  `2a2b59aa76cd1b75ce1ccdfa6b24ca347dddac659da08967df5464ebb50162c6`: 132 cases with
  before/after exits, stdout and stderr.
- `BOOT-001-r9-review-probe2.mjs`, SHA256
  `47806116cc1f11f24b4ed9145ba4fda46bcbf8defa3641c7355bec0f657445d1`, runs the applied guard
  only, for given project directory, tool and commands. Its log `BOOT-001-r9-review-probe2.log`
  has SHA256 `08fb60a488c750b47b23117641d67eb2a1b83fc540123d4b47096cc176806424` and 11 cases.

| Group | Cases | Expected (applied guard) | Observed |
|-------|-------|--------------------------|----------|
| F18 inputs and proof of fix | 5 | 2 for 3 (locked-settings reason), 0 for 2 | As expected. Both F18 inputs were 0 at HEAD. |
| F10 inputs (r7/r8) | 6 | 2 for 2 (reason), 0 for 4 | As expected, same as HEAD |
| Locked write inside a process substitution | 3 | 2 | 2 each, same as HEAD |
| Normal commands (`diff <(git show …) …`, `cmp <(…) <(…)`, `tee >(wc -l)`, `echo <(cd .claude)#; …` into a non-locked file, quoted `"<(pwd)#"`, `git log --format='%h #%s'`, `"${PWD##*/}"`, trailing comment) | 8 | 0 | 0 each |
| F20 forms (`@(…)#`, `a=(…)#`) | 2 | – | 0 before and after |
| Real repository: the exact live push `git push origin HEAD:refs/heads/chore/BOOT-001-project-bootstrap` | 1 | 0, empty stdout | 0, empty stdout (HEAD 2) |
| Real repository: bare, implicit, `--force`, `HEAD:main`, `+` refspec, `:` deletion, combined with `; echo` | 7 | 2 | 2 each |
| Real repository: shorthand `git push origin <branch>` | 1 | – | 0 (see "Push shorthand") |
| Fixture push allowed: `HEAD`, branch and full-ref sources to `refs/heads/<branch>`, `-u`, PowerShell | 5 | 0, empty stdout | 0 each (HEAD 2) |
| Fixture push flags before and after the refspec: `-f`, `--force`, `--force-with-lease`, `--force-if-includes`, `--mirror`, `--delete`, `-d`, `--all`, `--tags`, `--follow-tags`, `-uf`, `--prune`, `--atomic`, `-n` | 28 | 2 | 2 each |
| Fixture destinations `main`, `master`, `refs/heads/main`, `refs/heads/master`, another task branch, a tag | 6 | 2 | 2 each |
| Fixture push forms: `+`, `:` deletions, two refspecs, implicit destination, bare, unknown remote, URL remote, `-C`, `-c`, `--git-dir`, PowerShell comma list, Monitor | 15 | 2 | 2 each |
| Fixture push not standalone: `;`, `&&`, pipe, redirect, `&`, newline, subshell, `bash -c`, `env`, assignment prefix, `$(…)` | 11 | 2 | 2 each |
| Fixture push config: `remote.origin.mirror`, `push.followTags`, `push.pushOption` set; `remote.origin.push` remapping to `main` with shorthand, then with the explicit form | 5 | 2 for 4, 0 for the explicit form | As expected |
| Fixture with current branch `main`: explicit task push, push to `main`, bare | 3 | 2 | 2 each |
| Fixture apply allowed: direct proposal patch, with `--`, PowerShell | 3 | 0, empty stdout | 2 each with the fixture path spelled `C--`; 0 each with the on-disk spelling `c--` (probe2). This is F22. |
| Fixture apply refused: outside patch, nested, directory, missing, mixed with outside, `-R`, `--3way`, `git am`, `patch -i`, `patch <`, stdin, `;`, `&&`, `bash -c`, subshell, `-C`, Monitor | 17 | 2 | 2 each |
| Fixture inspection: `--check`, `-R --check` alone; `--check` combined with `; echo` | 3 | 0, 0, 2 | As expected. The combined form was 0 at HEAD (F21). |
| Unchanged denials: `git reset --hard`, `git clean -fdx`, `git commit --no-verify` | 3 | 2 | 2 each |
| Real repository (probe2): `git apply` of the r9 patch, `-R --check` of it, the live push | 3 | 0 | 0 each, empty stdout |
| Real repository (probe2): live push with `--force`, `HEAD:main`, `-R --check` with `; echo`; lowercase project path apply | 4 | 2 | 2 each |

| Command | Result | Tested revision | Time, 2026-10-20 (+07:00) |
|---------|--------|-----------------|---------------------------|
| `sha256sum` and `git hash-object` of the five files, the posthook and the patch | PASS: all match the handoff | `c764cda` + applied r9 | 21:01:57 |
| `node scripts/controls/test-controls.mjs` | PASS 69/69, fail 0, skipped 0, 44.2 s | same | 21:07:33–21:08:18 |
| `git diff --check` | FAIL (exit 2): `scripts/controls/test-controls.mjs:1247: new blank line at EOF.` (F23) | same | 21:08 |
| `git diff -U0` of the tests | Exactly one deleted line, the `:680` assertion the handoff lists. One added block of 184 lines (`:1064-1247`): two F18 groups and six D-006 groups | same | 21:08 |
| Probe, 132 cases | 3 mismatches, all positive apply controls, explained by F22 (fixture path spelling). Every other case with an expected exit matches. | same | 21:13:04–21:13:20 |
| Realpath diagnostic (scratch script) | `realpathSync` keeps `C--`, `realpathSync.native` returns `c--` for the same fixture folder | – | 21:14 |
| Probe2 | 11 cases as expected | same | 21:15:16, logged 21:18:03 |
| `git apply -R --check docs/proposals/BOOT-001-r9-controls.patch` (standalone, after block 2) | PASS: no output, exit 0 | same | 21:16 |
| `shopt extglob`; `bash --version` | `off`; 5.2.32(1)-release | – | 21:16:48 |
| Git Bash analogues in the scratch folder | `echo <(pwd)#; cd ..; pwd` printed `/dev/fd/63#`, then the parent. `… echo @(pwd)#; cd ..; pwd` failed with a syntax error, and nothing on the line ran. | – | 21:17 |

The staging, scan and commit checks are listed in the handoff section for this review.

Node `v26.12.0`, Git `2.46.1.windows.1`, Windows 11.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-04 | FAIL as worded | Within the r9 scope, F18 is closed. No probed case regressed against HEAD, normal commands pass, and no High finding is open. Two reasons keep AC-04 from PASS as worded. First, its push clause predates D-006: a task-branch push now passes by owner decision, and the contract text needs the owner's amendment. Second, the deferred Medium forms (F11–F15, F19, F20) still let a locked write through the guard. |
| AC-06 / AC-07 | See the handoff section for this review | The red-flag scan runs after the records are staged. |
| AC-01/02/03/05/08 | UNKNOWN in this review | No new P25, gate or architecture evidence. |

## Checked, nothing found (and how)

- **Test diff.** The only change to existing source is the `:680` assertion
  (`/redirecting output|git push is reserved/` → `/redirecting output|git push/`). The F9 escape
  test there still requires exit 2. The handoff lists this change. All other changes are additions
  in one block after the F6 test. Allowed cases assert empty stdout, so the hook emits no
  allow/ask decision. Fixture cleanup is limited to `os.tmpdir()/sochron-controls-*`.
- **Settings.** Read in full. `deny` keeps every Edit, Read, reset and clean rule and drops only
  `Bash(git push)` and `Bash(git push *)`. `ask` has no git rule. There is no `allow` section and
  no `.claude/settings.local.json`. The hooks block is unchanged.
- **Push grammar against requirement 2.** Every flag in the requirement's list, a `+` refspec,
  explicit main/master destinations, main as the current branch, a detached HEAD (permanent
  test) and every other probed form return 2. Allowed: one named remote, optional leading
  `-u`/`--set-upstream`, and one refspec to `refs/heads/<current task branch>`.
- **Apply against requirement 3.** Only a regular file directly in the real `docs/proposals/`
  gets the exception. Nested, directory, missing, mixed and outside patches, `git am` and
  `patch` keep the locked-path block. Junction cases are covered by the permanent test and were
  not re-probed.
- **Single invocation (requirement 4).** Separators, pipes, redirections, background, newline,
  subshell, group, nested shells, wrappers, assignment prefixes, substitutions and comments all
  return 2, for push, proposal apply, ordinary apply and inspection (F21 covers the usability
  cost). Monitor never gets the exception.
- **Text against D-006.** AGENTS.md changes only "Agent roles", "Authority" and "Git". CLAUDE.md
  changes only "Claude Code only". Each change maps to D-006 or to handoff requirements 5, 6 and 8:
  - the two exceptions without a prompt;
  - force, deletion, multi-ref, main/master and unproved push forms stay blocked;
  - merge, labels and every other external write stay with the owner;
  - other agents do not push;
  - no direct-edit exception;
  - per patch: apply, hash verification, fresh-session review, then commit, with N6 on any
    other report;
  - the live push after this review.

  The text narrows D-006, never widens it: it adds "regular", "directly under", "standalone",
  and a named remote with an explicit destination. The "Never" list and "Verified commands" are
  unchanged.

## Not checked (and why)

- **Linux.** There is no CI run on a head that contains r8 or r9. The parent session pushes after
  this commit.
- **Live push and live proposal apply.** Neither ran in this session. The parent session runs
  the push; whether a prompt appears depends on the runtime permission mode (D-004 note).
- **F20 Bash behavior** with extglob on, and for compound array assignment. Running either needs
  commands outside the cd/pwd/echo allowance.
- **Junction and redirected-proposals cases.** These are covered by the permanent test only.
  The r9 author's 313-case security pre-review was not rerun.
- **Codex verifier.** `BOOT-001-r9-verify.mjs before|after` was not rerun. This review's
  before/after comparison uses its own HEAD-copy probe.
- **Parser coverage.** There is no complete shell-parser review. Heredocs, option clusters and
  the forms deferred to the next guard-fix task stay outside this review.

## Handoff

Do not reapply the patch. The applied files are committed just before this review's records, in
the same commit. Next:

- **Parent session:** run the live D-006 push
  `git push origin HEAD:refs/heads/chore/BOOT-001-project-bootstrap` as a standalone command
  (requirement 8). Record the result, the exact pushed head and CI for that head. If the runtime
  blocks or prompts, stop under N6.
- **F20:** the owner decides its placement. The F11–F19 policy would put it in the next
  guard-fix task.
- **F21, F22, F23 (Low):** next controls patch or false-positive task. F21 needs only
  documentation.
- **Owner:** amend BOOT-001 AC-04's push clause, and update the D-006 and D-004 status text,
  once the live check passes. The `owner-approved-control-change` label stays an owner decision
  after CI is green.

Delivery: implemented, with local verification on Windows. Not verified by CI, not merged.
