# Review BOOT-001 round 7 · applied r7 guard fix (F7, F9, F8 subset)

Repository HEAD `fa42bab`, base `main` (`951ee98`). Reviewed: the uncommitted guard and test
changes the owner applied from `docs/proposals/BOOT-001-r7-controls.patch`. The owner stated this
in the session prompt. Reviewer: Claude Code, a fresh headless session that did not author r7
(Codex wrote it). Date: 2026-10-20 (+07:00).

The applied files match the proposal:

- Patch SHA256 `a95d979d13ef0f1de8d05c0e75e7b964143823abb21ce0abf862106ec3e48602`.
  `git apply -R --check` passes, so the working-tree diff is exactly this patch: two files,
  226 insertions, 23 deletions.
- Guard SHA256 `2986d0e1324d292e4abbf6ecf14f07d5b8abe8b3c73c6f8c26a32303e52fa3c0`, Git blob
  `25c05cb3767a1c809d556c2d4bb763e01bf649ed`.
- Tests SHA256 `0664b0fef1891c49861f6c0b74f4692fd2c12fd1dabfdbd1f007e606a527dfe4`, Git blob
  `f5f144fbf1da31d1ff18cbf83c5424c9ef6e5194`.
- The HEAD versions match r5: guard `cec6c7dc…`, tests `aca04ebd…`. The posthook (`28c6283c…`)
  and settings (`9de3df7d…`) are unchanged.

Scope covers three items:

- F7, judged against the r5 proof of fix.
- F9: the two r5 forms plus the escape rules r7 claims.
- The F8 subset for unresolved branch switches.

Forms outside these claims were probed only to find misses that the 21-form list does not name.

**Result:**

- F7 meets its r5 proof of fix. F9 is closed for its recorded forms. The F8 switch subset works,
  and F8 stays open for Monitor and `case`. The suite passes 54/54.
- r7 introduces one regression (F10, High). Its line-continuation rule also applies inside
  comments, so a comment that ends in a backslash swallows the next line. A `cd` on that line is
  no longer seen, and a locked-path write that HEAD blocked now passes. AC-04 stays FAIL until
  F10 is fixed.
- By owner decision, five pre-existing Medium gaps (F11 to F15) go to the next guard-fix task.
  Two Low items (F16, F17) are recorded.**

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F7 | High | closed | `.claude/hooks/guard-bash.mjs:73-76`, `:90-95` | `echo \( ; cd .claude ; echo \) ; echo {} > settings.json` returns 2 (HEAD: 0), with the locked-settings reason. `find . \( -name a -o -name b \) -print` returns 0. Odd backslash runs (3, 5), a real group closed after an even run, nested `sh -c` and Monitor all return 2. Escaped parentheses inside a real group return 0, as Bash scopes them. The three permanent F7 tests pass. | – | – | – | Met as worded in r5: "The input above returns 2. `find . \( -name a -o -name b \) -print` and the existing allow-list still return 0. Both are added as permanent tests." |
| F9 | Medium | closed for its recorded forms | `:73-76`, `:173-213`, `:215-229`, `:621-622` | `echo \"; cd .claude; echo {} > settings.json` and `cmd //c "echo {} > AGENTS.md"` return 2 (HEAD: 0 and 0), with the redirect reason. 12 more inputs return 2: escapes, continuations, `//K`, `//s //c`, and a `\u` decoded inside nested `bash -c`. 4 literal-operator inputs return 0. The five permanent F9 tests pass. | – | – | – | r5 set no proof of fix, and the owner chose to fix F9 in this PR. Both r5 inputs now block. Further lexical forms are F12 to F15. |
| F8 | Low | partly fixed, still open | fixed: `:312`, `:402`; open: `:662`, `:667` | `cd "$X" && git switch -c feat/x` returns 0 (HEAD: 2). After an unresolved switch, commit, merge and rebase return 2 with "branch became unknown". A commit before it returns 0. Monitor `while true; do echo $(date); sleep 5; done` and `case x in a) echo a;; esac` still return 2. | Ordinary commands | As in r5 | Monitor and `case` stay in the false-positive task. | Each returns 0 while the F7 and F10 inputs still return 2. |
| F10 | High | confirmed, regression from r7 | `:90-95` (an unquoted backslash-newline is dropped everywhere, comments included); `:83-123` (no comment rule) | Hook input `echo ok # C:\`, newline, `cd .claude; echo {} > settings.json`: HEAD exit 2, applied exit 0, empty stderr. Same result for `echo ok # trailing \`, newline, `cd .claude`, newline, `echo {} > settings.json`. Owner-side Git Bash 5.2.32(1)-release check (relayed, not rerun here), with lines `echo ok # C:\` / `cd inner` / `pwd`: printed `ok`, then `…/esc/inner`. The comment ends at the newline and the next line runs. The control without a comment (`echo ok \` / `cd inner` / `pwd`) printed `ok cd inner`, so outside a comment the lines do join. | A comment ending in a backslash, a `cd` on the next line, then a write | The guard folds the `cd` line into the comment and checks `./settings.json` instead of `.claude/settings.json`. A locked write that HEAD blocked passes (AC-04). The post-run check reports it afterwards; nothing prevents it. | In POSIX syntax, model comments. An unquoted `#` that starts a word runs to the next newline. A word starts at the beginning of input, after unquoted whitespace, or after `;` `&` `\|` `(` `)` or a newline. Inside a comment, backslashes, quotes, parentheses and `$(` have no meaning. Apply this in `splitSegments` and `substitutionEnd`. A `#` inside a word (`a#b`, `$#`, `${#x}`) is unchanged. | Both inputs return 2 with the locked-settings reason. `echo ok # it's fine`, newline, `echo ok > out.txt` returns 0. `echo a#b`, `echo $#` and `echo ${#x}` are unchanged. All are added as permanent tests. |
| F11 | Medium | open, pre-existing; owner: next guard-fix task | `:83-123` (no comment rule) | HEAD 0, applied 0 for each: `echo ok # it's fine`, newline, `echo {} > AGENTS.md`; `echo ok # see "notes`, newline, `echo {} > AGENTS.md`; `# go to docs; cd docs`, newline, `echo {} > .claude/settings.json`. | A quote character or a `cd` inside a comment | A quote in a comment hides every later line. A `cd` in a comment moves the guard's directory, so a write to a root locked file resolves under `docs/`. The post-run check detects both. | The comment rule from F10 is expected to cover these as well. | Each input returns 2. Ordinary commented commands return 0. |
| F12 | Medium | open, pre-existing; owner: next guard-fix task | `:108`, `:198` (`$'` is read as a plain single quote) | HEAD 0, applied 0: `echo $'\''; cd .claude; echo {} > settings.json` and `echo $'\'' > AGENTS.md`. The control `echo $'x' > AGENTS.md` returns 2. | Bash ANSI-C quoting with `\'` | The guard closes the quote at `\'`, then opens a new single quote that hides the rest. | Treat `$'…'` as its own quote, in which a backslash escapes the next character (including `\'`). Alternatively, fail closed on `$'` that contains `\'`. | Both inputs return 2. `printf $'a\tb'` returns 0. |
| F13 | Medium | open, pre-existing; owner: next guard-fix task | `:74`, `:108` (the escape rule is POSIX only; PowerShell's backtick is not modelled) | HEAD 0, applied 0: on the PowerShell tool, ``Write-Output `"; Set-Location .claude; Set-Content settings.json x`` and ``Write-Output `"; Set-Content AGENTS.md x``; on Bash, ``pwsh -Command 'Write-Output `"; Set-Content AGENTS.md x'``. The control without the backtick returns 2. | A backtick-escaped quote in PowerShell | The same class as F9, on the PowerShell tool and in nested `pwsh`. | In PowerShell syntax, a backtick outside single quotes escapes the next character. | All three inputs return 2. |
| F14 | Medium | open, pre-existing; owner: next guard-fix task | `:108` (cmd's `^` is not modelled) | HEAD 0, applied 0: `cmd //c 'echo ^"& echo {} > AGENTS.md'`. | A caret-escaped quote in cmd | The same class as F9, for cmd. | In cmd syntax, treat `^` outside quotes as an escape, or fail closed on `^"`. | The input returns 2. |
| F15 | Medium | open, pre-existing; owner: next guard-fix task | `:125-141` (`substitutionEnd` counts `)` without case, comment or backtick grammar) | HEAD 0, applied 0: `echo "$(case x in *) echo {} > AGENTS.md;; esac)"`; `echo "$(echo ok # )`, newline, `echo {} > AGENTS.md)"`; ``echo "$(echo `printf )`; echo {} > AGENTS.md)"``. | A `)` from a case pattern, a comment or a backtick inside a quoted `$(…)` | The substitution ends early. The rest is treated as quoted text and never analyzed. | Model these forms, or fail closed when a quoted `$(…)` holds an unquoted `case`, `#` or backtick before its closing `)`. | Each input returns 2, and the F9 quoted-substitution tests still pass. |
| F16 | Low | confirmed, new block from r7 | `:163-165` | HEAD 0, applied 2: ``echo `printf 'a\n'` `` and ``x=`ls docs \| sed 's/\.md$//'`; echo $x``. Message: "escaped legacy backtick substitution cannot be inspected reliably". | A backtick substitution that contains any backslash | An intended fail-closed block. Under N6, though, every block stops the session until the owner answers. | False-positive task: implement Bash's backslash rules inside backticks, or keep the block. | Both inputs return 0, while a locked write hidden in backticks still returns 2. |
| F17 | Low | confirmed, pre-existing since r5 | `:317-333`, `:398-405` | Fixture on a feature branch, with main present: `git switch main; git switch -c feat/BOOT-001-r7-probe; git commit -m x` returns 0 before and after. The `-c` target already exists, so Git refuses that switch. Because of the `;`, the commit then runs on main. | A known switch to main, then a failing switch, joined by `;` | A commit on main, which the branch rule exists to stop. It is local and reversible, and no push is involved. | Treat a switch whose success the text cannot guarantee as unknown, the way r7 already treats unresolved switches. That covers a `;` or `\|\|` follow-up and `-c` to an existing branch. | The input returns 2, and `git switch -c feat/new && git commit -m x` still returns 0. |

Also observed, not raised as findings:

- **H-1:** an apostrophe in a heredoc body hides later lines (HEAD 0, applied 0). Heredoc grammar
  has been outside the guard's scope since r5, and it goes with the heredoc false-positive task.
- **C-6:** `echo ok # (note`, newline, `echo ok` returns 2 before and after, a false positive. The
  comment rule from F10 should remove it.
- **Three inputs moved from 2 to 0, correctly:** `(echo \(; cd .claude); echo {} > settings.json`
  and `(cd .claude; echo \)); echo {} > settings.json` keep the `cd` inside a real subshell.
  `printf '%s\n' \> AGENTS.md` prints `>` as an ordinary argument.

## Independent checks

Every guard probe was sent to the hook as JSON on stdin, and no payload command was executed.
F8 inputs ran in a throwaway fixture repository in this session's scratch folder. The guard ran
its own read-only `git rev-parse` calls there. This session executed no shell analogue. F10's
shell behavior comes from the owner-side Git Bash run, relayed by the parent session.

Probe script and evidence (local, gitignored), run from any directory with
`node docs/proposals/BOOT-001-r7-review-probe.mjs <repo-root> <scratch-dir>`:

- The script runs each case against the applied guard in place and against a scratch copy of
  the HEAD guard. The copy differs only in its `rules.mjs` import, which becomes an absolute file
  URL.
- Script SHA256 `97d9dc9d60417e66436aa910eb14454a2e84200464c9ff87a905b76dc1584b4c`.
- Evidence `docs/proposals/BOOT-001-r7-review-evidence.json`, SHA256
  `f866bc365c685d356c8bd17543a04fb5f9c44516b7d738d7395663c391767959`: 101 cases with
  before/after exits and stderr.
- Log `docs/proposals/BOOT-001-r7-review-probe.log`, SHA256
  `ae416537c35468b3371807f358b368198d51fe6a6fcbc72758cd7dfcd9ead1a5`.

| Group | Cases | Expected (applied guard) | Observed |
|-------|-------|--------------------------|----------|
| r2 inputs | 6 | 2 | 2 each; HEAD also 2 |
| r5 scope and attached operands | 12 | 2 | 2 each |
| Normal Bash, PowerShell and Monitor commands, including backslash-heavy `grep`, `sed`, `git log` and a Windows path in double quotes | 17 | 0 | 0 each |
| F7 | 13 | 2 for 8, 0 for 5 | As expected. HEAD returned 0 for four of the deny cases and 2 for two of the allow cases. |
| F9 | 18 | 2 for 14, 0 for 4 | As expected. HEAD returned 0 for 11 of the deny cases. |
| F8 subset (fixture) | 11 | 2 for 6, 0 for 5 | As expected. HEAD returned 2 for three of the allow cases. |
| Controls for observed groups | 2 | 2 | 2 each |
| Observed only (F8 remainder, F10 to F17, H-1, C-6) | 22 | – | See the findings table |

| Command | Result | Tested revision | Time, 2026-10-20 (+07:00) |
|---------|--------|-----------------|---------------------------|
| `sha256sum` of patch, guard, tests, posthook and settings; `git hash-object` of guard and tests | PASS: all match the handoff | `fa42bab` + applied r7 | 11:50:49 |
| `git apply -R --check docs/proposals/BOOT-001-r7-controls.patch` | PASS: the diff equals the patch | same | 11:50:49 |
| `git show HEAD:<file> \| sha256sum` for guard and tests | PASS: matches r5 | `fa42bab` | 11:50:49 |
| `node scripts/controls/test-controls.mjs` | PASS 54/54, fail 0, skipped 0, 24.5 s | `fa42bab` + applied r7 | 11:50:54–11:51:19 |
| Probe, 99 cases | PASS: 0 mismatches on expected cases; F10 observed. An earlier start at 11:58:26 failed inside the probe script (it wrote to its output folder before creating it). The script was fixed and rerun. | same | 11:58:33–11:58:40 |
| Probe, 101 cases (adds the F8 Monitor and `case` remainder); this produced the evidence file | PASS: 0 mismatches on expected cases | same | 12:08:30–12:08:37 |
| Owner-side Git Bash analogue for F10 (relayed) | The comment ends at the newline, and the next line runs | – | 12:05 |
| `git diff --cached --check` | PASS | `fa42bab` + the staged r7 controls and these records | 12:13:11 |
| `bash scripts/controls/red-flags.sh main` | exit 0. The same six explained groups as in r5; both secret groups and the untracked list are empty. Each scanner pattern applied to the 427 staged added lines alone gives 0 hits, so r7 and these records add no hit. | same | 12:13:17–12:13:19 |

Node `v26.12.0`, Windows 11. Session events:

- **Post-run report.** The session's first shell command (`git status`) got the post-run report
  for the two uncommitted locked files. The owner's prompt had confirmed in advance that these were
  the r7 files they applied. Claude continued on that basis and verified the hashes first.
- **WebFetch.** An attempt to read the Bash manual with WebFetch was not permitted in the headless
  session. Claude stopped and asked. The owner chose an owner-side analogue instead.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-04 | FAIL | F10: a locked-path write that HEAD blocked passes the applied guard. F7's proof of fix and F9's recorded forms pass. |
| AC-06 | PASS | `bash scripts/controls/red-flags.sh main` with the r7 files and records staged: exit 0 and the same six explained groups (12:13:17). |
| AC-07 | PASS | In the same scan both secret groups are empty, and the staged additions match no scanner pattern. |
| AC-01/02/03/05/08 | UNKNOWN in this review | No new P25, gate or architecture evidence. |

## Checked, nothing found (and how)

- **Test diff.** It only adds lines: 145 insertions, 0 deletions, in one contiguous block, so the
  original 45 tests and their assertions are unchanged. The nine new tests match r7's claims
  (F7: 3, F9: 5, F8: 1), and the denial tests assert the reason as well as the exit code. The F8
  test uses `tempRepo` with a local identity and removes it in `finally`.
- **POSIX-only gates.** The escape, continuation and `$(` capture rules are gated on POSIX syntax
  (`:74`, `:79`, `:97`, `:187`). PowerShell, cmd and Monitor behave as at HEAD: the r5
  PowerShell/cmd scope cases, normal PowerShell and Monitor commands, and Monitor with escaped
  parentheses.
- **Escapes inside quotes.** Inside double quotes only `$`, `` ` ``, `"`, `\` and newline are
  escapes (`:75`). `"C:\Users\MSI"` keeps its backslashes, and nested `bash -c "… .cla\ude …"`
  decodes once more in the child, as Bash does. Single quotes keep backslashes literal.
- **Redirect tokens.** These now carry an operator flag (`:178`, `:205`, `:221`), so a quoted or
  escaped `>` or `<` is an ordinary word. Real redirects still block in every deny case.
- **cmd flags.** `//c` and `//k` count as cmd flags only when the command is `cmd`, in either
  case (`:621-622`).
- **Unknown branch state.** It lasts for the whole hook invocation and covers child scopes
  (`-C "$X"`, a substitution, nested `bash -c`). Reads after it pass, and a commit before it
  passes. In an unknown directory, `git checkout` was already blocked by the path-writer rule
  (`:421-424`), so the r7 change only affects `git switch`.

## Not checked (and why)

- **Linux.** There is no CI run on a head that contains r7. The owner pushes.
- **Shell execution.** This session executed no shell payload or analogue. Only F10 has runtime
  evidence, from the owner-side run. The behavior behind F11 to F15 and F17 comes from Bash,
  PowerShell, cmd and Git documentation and was not executed. F15's backtick form (S-3) is the
  least certain.
- **Codex verifier.** `BOOT-001-r7-verify.mjs before|after` was not rerun. This review's
  before/after comparison uses its own HEAD-copy probe, and the applied hashes match Codex's
  candidate.
- **Parser coverage.** There is no complete shell-parser review. Heredocs, option clusters and
  the 21-form list stay outside this patch.
- **Live dispatch.** There is no new evidence beyond `8ad0895`. The posthook was not reviewed
  again (its hash is unchanged).

## Handoff

Do not reapply the patch. The applied files are committed in `077c3a1`, with blobs `25c05cb3…`
and `f5f144fb…`, just before this review. Next:

- **Owner:** push when ready. CI on the new head gives Linux evidence for the 54 tests.
- **F10** needs a small guard patch and permanent regressions. Under the current role binding,
  Codex writes it, the owner applies it, and a fresh Claude session reviews it.
- **F11 to F15** go to the next guard-fix task (owner decision, 2026-10-20). The F10 comment rule
  is expected to cover F11's forms as well. F17 goes with them.
- **F8's remainder and F16** go to the planned false-positive task.
- Do not add the `owner-approved-control-change` label while F10 is open.

Delivery: implemented, with local verification on Windows. Not verified by CI, not merged.
