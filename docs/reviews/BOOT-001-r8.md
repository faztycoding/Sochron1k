# Review BOOT-001 round 8 · applied r8 guard fix (F10)

Repository HEAD `09360db`, base `main` (`951ee98`). Reviewed: the uncommitted guard and test
changes the owner applied from `docs/proposals/BOOT-001-r8-controls.patch`. The owner stated this
in the session prompt. Reviewer: Claude Code, a fresh headless session that did not author r8
(Codex wrote it) and did not propose its approach. Date: 2026-10-20 (+07:00).

The applied files match the proposal:

- Patch SHA256 `20cde61370c60ace51f55b35a2222ace850dfa93c72854bba1babaad92ecf1b6`.
  `git apply -R --check` passes, so the working-tree diff is exactly this patch: two files,
  203 insertions, 7 deletions.
- Guard SHA256 `f3a525c53eb8506771203b5311f14f18f9ffb14824d20e28f64d2d7eafdcb212`, Git blob
  `98ab688b480f4ad0904359d96dbaffe1c0566f13`.
- Tests SHA256 `1daf54a876307b5d710eac5ae3745e0d635360fa35bbf6ce73b606ca333a5d8a`, Git blob
  `ec961f6bbd056365daf293141c5009da4f7794ee`.
- The HEAD versions match r7: guard `2986d0e1…`, tests `0664b0fe…`. The posthook (`28c6283c…`)
  and settings (`9de3df7d…`) are unchanged.

Scope covers two items:

- F10, judged against the r7 proof of fix.
- The comment and parameter boundary rules r8 adds to `splitSegments` and `substitutionEnd`.

F8's remainder and F11 to F17 stay deferred by the owner decision of 2026-10-20. Their recorded
inputs were rerun only to check that r8 does not make them worse.

**Result:**

- F10 meets its r7 proof of fix, and the suite passes 61/61.
- r8 introduces one regression (F18, High). Its comment rule also starts a comment at a `#`
  directly after the `)` of a process substitution. Bash keeps reading the same word there, so
  the rest of the line is hidden from the guard. A locked-path write that HEAD blocked now
  passes. AC-04 stays FAIL until F18 is fixed.
- F19 (Medium) is pre-existing and not made worse: a `$(…)` inside a quoted parameter default
  with nested quotes is never inspected. Codex reported it in the r8 handoff for triage. Bash
  runs that substitution, as an analogue here confirms. The owner places it.
- No deferred item got worse. Four recorded inputs improved (F11's three and F15's comment form),
  and the r7 C-6 false positive is gone.**

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F10 | High | closed | `.claude/hooks/guard-bash.mjs:94-99`, `:164-168` (comments end at the physical LF) | Hook input `echo ok # C:\`, newline, `cd .claude; echo {} > settings.json`: HEAD 0, applied 2, with the locked-settings reason. Same for `echo ok # trailing \`, newline, `cd .claude`, newline, `echo {} > settings.json`. `echo ok # it's fine`, newline, `echo ok > out.txt`: 0. `echo a#b`, `echo $#`, `echo ${#x}`: 0 before and after. The same form after a real subshell, `(pwd)# C:\`, newline, `cd .claude; echo {} > settings.json`: HEAD 0, applied 2. Git Bash 5.2.32 analogues in this session's scratch folder: `echo ok # C:\` / `cd ..` / `pwd` printed `ok`, then the parent folder; `(pwd)# C:\` / `cd ..` / `pwd` printed the folder, then its parent. In both, the comment ends at the newline and the next line runs. All are permanent tests (7 groups). | – | – | – | Met as worded in r7: "Both inputs return 2 with the locked-settings reason. `echo ok # it's fine`, newline, `echo ok > out.txt` returns 0. `echo a#b`, `echo $#` and `echo ${#x}` are unchanged. All are added as permanent tests." |
| F18 | High | confirmed, regression from r8 | `:83` (`POSIX_WORD_BREAK` includes `(`, `)`, `<`, `>`); `:139` and `:189` (every unquoted break character sets `wordStart`); `:94`, `:164` (a `#` at `wordStart` starts a comment) | Hook input `echo <(pwd)#; cd .claude; echo {} > settings.json`: HEAD 2 (locked-settings reason), applied 0, empty stderr. Same for `echo >(pwd)#; …`. The control `echo <(pwd) #; …` (space before `#`) returns 0 correctly, because there the `#` does start a comment. Git Bash 5.2.32 analogue in the scratch folder (20:07:37): `echo <(pwd)#; cd ..; pwd` printed `/dev/fd/63#`, then the parent folder. The `#` is part of the word and the commands after it run. The control `echo <(pwd) #; cd ..; pwd` printed only `/dev/fd/63`. | A `#` written directly after the closing `)` of `<(…)` or `>(…)`, then a `cd` and a write on the same line | The guard treats the rest of the line as a comment and never sees the `cd` or the write. A locked-path write that HEAD blocked passes (AC-04). The post-run check reports it afterwards; nothing prevents it. | Model process substitution: when an unquoted `(` directly follows `<` or `>`, its matching `)` keeps `wordStart` false, in both `splitSegments` and `substitutionEnd`. Alternatively, fail closed when an unquoted `#` directly follows any `)`. A `)` that closes a subshell or group must stay a boundary, or F10 returns for `(pwd)# C:\` (see F10 evidence). | Both inputs return 2, with the locked-settings reason if process substitution is modelled. `echo <(pwd) #; cd .claude; echo {} > settings.json` returns 0. `(pwd)# C:\`, newline, `cd .claude; echo {} > settings.json` still returns 2. The F10 tests still pass. All are added as permanent tests. |
| F19 | Medium | open, pre-existing (HEAD 0, applied 0); placement: owner | `:197-224`; `:205-207` toggle quotes with no parameter context | Hook input `echo "${x:-"'"$(echo {} > AGENTS.md)}"`: HEAD 0, applied 0. Same for `echo "${x:-"it's $(cd .claude; echo {} > settings.json)"}"`. Git Bash 5.2.32 analogues (20:09:39): `echo "${r8unset:-"it's $(cd ..; pwd)"}"` printed `it's` and the parent folder; `echo "${r8unset:-"'"$(pwd)}"` printed `'` and the folder. Bash runs the substitution. Codex recorded both inputs in the r8 handoff ("Limits and next action") for triage. | A `$(…)` inside a double-quoted `${…:-…}` default that holds its own quotes and an apostrophe | `substitutions()` reads the inner `"` as closing the outer quote, then the apostrophe as opening a single quote, so the `$(…)` is never analyzed. A locked write inside it passes. The post-run check reports it afterwards. | Give `substitutions()` the parameter quote context r8 added to `splitSegments` and `substitutionEnd`: save the enclosing quote at `${`, restore it at `}`, and keep apostrophes literal under enclosing double quotes. Alternatively, fail closed on a `$(` inside a `${…}` that holds nested quotes. | Both inputs return 2. `echo "${x:-$(git rev-parse HEAD)}"` returns 0. r8's parameter tests still pass. |

Also observed, not raised as findings:

- **Improved by r8, status unchanged by owner decision.** F11's three recorded inputs (C-1, C-2,
  C-5) and F15's comment form (S-2) moved from 0 to 2. The next guard-fix task can close them
  against their own proof of fix. The r7 C-6 false positive (`echo ok # (note`, newline, `echo
  ok`) moved from 2 to 0, as r7 expected.
- **Unchanged deferred items.** F8's remainder (Monitor and `case`), F12 (`$'\''`), F13
  (PowerShell backtick), F14 (cmd caret), F15's `case` and backtick forms, F16, F17 and H-1 give
  the same exit before and after.
- **Arithmetic fails closed.** `(( x = 1 # )); cd .claude; echo {} > settings.json` returns 2
  before and after. With r8 the reason is "unmatched opening parenthesis": the comment rule hides
  the `))`, and the guard refuses the unbalanced group. Bash has no comments inside `(( ))`, so
  this is a false positive at worst.
- **Bash version note (V-1).** `echo ${ cd .claude; }; echo {} > settings.json` returns 0 before
  and after. On the Git Bash here (5.2.32) this is a "bad substitution". Bash 5.3 documents
  `${ command; }` as a command substitution that runs in the current shell, and r8 treats a
  `${…}` body as opaque text. If Git Bash moves to 5.3, this form needs its own rule. This comes
  from documentation; it was not executed.

## Independent checks

Every guard probe was sent to the hook as JSON on stdin, and no payload command was executed.
F8 inputs ran in a throwaway fixture repository in this session's scratch folder. The guard ran
its own read-only `git rev-parse` calls there. Six shell analogues ran in Git Bash 5.2.32(1) in
the scratch folder, using only `cd`, `pwd`, `echo` and process substitution of `pwd`. They wrote
no files.

Probe script and evidence (local, gitignored), run from any directory with
`node docs/proposals/BOOT-001-r8-review-probe.mjs <repo-root> <scratch-dir> <evidence-json>`:

- The script runs each case against the applied guard in place and against a scratch copy of
  the HEAD guard. The copy differs only in its `rules.mjs` import, which becomes an absolute file
  URL. It reuses the r7 review cases and adds groups for ordinary commands with `#` and `${…}`,
  F10, and the boundary checks above.
- Script SHA256 `98a7e1160ba09161c6e9de4a61072076beceab688f20d8729fb97656bff0fd36`.
- Evidence `docs/proposals/BOOT-001-r8-review-evidence.json`, SHA256
  `2ba040267edcdb18faf4929ed7c7438a37a4ea8d9370e4be542d3e4b0ba4880b`: 125 cases with
  before/after exits and stderr.
- Log `docs/proposals/BOOT-001-r8-review-probe.log`, SHA256
  `51c2c89df2b99b9bf5efaab7234eda4ea456fa64aa99450df1954c8dc1d62eba`.

| Group | Cases | Expected (applied guard) | Observed |
|-------|-------|--------------------------|----------|
| r2 inputs | 6 | 2 | 2 each; HEAD also 2 |
| r5 scope and attached operands | 12 | 2 | 2 each |
| Normal Bash, PowerShell and Monitor commands (r7 set) | 17 | 0 | 0 each |
| Normal commands with `#`, comments and `${…}` (`git log --format='%h #%s'`, `grep -n '^#'`, `"${PWD##*/}"`, `"${f%.md}"`, `${1:-default}`, `${#PATH}`, trailing and leading comments, r7 C-6) | 12 | 0 | 0 each; C-6 was 2 at HEAD |
| F7 (r7 cases) | 13 | 2 for 8, 0 for 5 | As expected |
| F9 (r7 cases) | 18 | 2 for 14, 0 for 4 | As expected |
| F8 subset (fixture, r7 cases) | 11 | 2 for 6, 0 for 5 | As expected |
| F10 inputs and proof of fix | 6 | 2 for 2 (locked-settings reason), 0 for 4 | As expected. HEAD returned 0 for both deny cases. |
| Boundary checks | 8 | 2 for 5, 0 for 1, observed 2 | Two mismatches: BD-3 and BD-4 (F18) return 0. Unquoted `${x:-$(…)}` and `` ${x:-`…`} `` still block, and `(pwd)# C:\` moved from 0 to 2. |
| Controls for observed groups | 2 | 2 | 2 each |
| Deferred and pre-existing (F8 remainder, F11 to F17 forms, H-1, F19) | 20 | – | None worse; four moved from 0 to 2 |

| Command | Result | Tested revision | Time, 2026-10-20 (+07:00) |
|---------|--------|-----------------|---------------------------|
| `sha256sum` of patch, guard, tests, posthook and settings; `git hash-object` of guard and tests | PASS: all match the handoff | `09360db` + applied r8 | 19:58:41 |
| `git apply -R --check docs/proposals/BOOT-001-r8-controls.patch` | PASS: the diff equals the patch | same | 19:58:41 |
| `git show HEAD:<file> \| sha256sum` for guard and tests | PASS: matches r7 | `09360db` | 19:58:41 |
| `node scripts/controls/test-controls.mjs` | PASS 61/61, fail 0, skipped 0, 27.7 s | `09360db` + applied r8 | 19:58:47–19:59:15 |
| Probe, 124 cases | FAIL on 2 expected cases (BD-3, BD-4: F18); all others match | same | 20:07:02–20:07:11 |
| Git Bash analogues: process substitution, its space control, F10 base fact | `/dev/fd/63#` then the parent folder; `/dev/fd/63` only; `ok` then the parent folder | – | 20:07:37 onward |
| Probe, 125 cases (adds BD-8); this produced the evidence file | FAIL on the same 2 expected cases; 101 of 103 match | same | 20:09:22–20:09:31 |
| Git Bash analogues: subshell boundary; F19 shapes | Folder then parent; `it's` + parent and `'` + folder | – | 20:09:3x–20:09:39 |
| `node scripts/controls/check-locked-paths.mjs main` | FAIL as expected: 42 bootstrap control changes need the owner's label. Not waived. | same | 20:10:33 |
| `git diff --cached --check` | PASS | `09360db` + the staged r8 controls and these records | 20:12:55 |
| `bash scripts/controls/red-flags.sh main` | exit 0. The same six explained groups as in r7; both secret groups and the untracked list are empty. | same | 20:13:01–20:13:03 |
| Each scanner pattern applied to the 467 staged added lines alone (scratch Node script) | 0 hits for all ten patterns, so r8 and these records add no hit | same | 20:13:36 |

Node `v26.12.0`, Git `2.46.1.windows.1`, Windows 11. Session events:

- **Post-run report.** The session's first shell command (`git status`) got the post-run report
  for the two uncommitted locked files. The owner's prompt had confirmed in advance that these were
  the r8 files they applied. Claude continued on that basis and verified the hashes first.
- **Safety classifier.** One response, after reading the guard source and before any probe, was
  stopped by the tool's safety classifier, not by a hook. Its withheld content was not
  reproduced. The review continued with the narrower probe set above: recorded inputs,
  proof-of-fix inputs, ordinary commands and eight boundary checks.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-04 | FAIL | F18: a locked-path write that HEAD blocked passes the applied guard. F10's proof of fix is met. |
| AC-06 | PASS | `bash scripts/controls/red-flags.sh main` with the r8 files and these records staged: exit 0 and the same six explained groups (20:13:01). |
| AC-07 | PASS | In the same scan both secret groups are empty, and the staged additions match no scanner pattern (20:13:36). |
| AC-01/02/03/05/08 | UNKNOWN in this review | No new P25, gate or architecture evidence. |

## Checked, nothing found (and how)

- **Test diff.** It only adds lines: 143 insertions, 0 deletions, in one contiguous block before
  the F7 tests, so the original 54 tests and their assertions are unchanged. The seven new groups
  match the handoff: comment line endings, inert comment contents, literal hash boundaries,
  logical continuations, nested substitutions, parameter quote contexts and unchanged non-POSIX
  behavior. Denial tests assert the reason as well as the exit code. Each test is labeled hook
  JSON only.
- **POSIX-only gates.** The comment rule, the `${` parameter context and the separator
  suppression inside `${…}` are gated on POSIX syntax (`:94`, `:114`, `:130`, `:133`, `:138`,
  `:164`, `:177`). For PowerShell and Monitor, `substitutionEnd` never raises `braceDepth`, so
  `:186-189` behave as at HEAD. The r5 PowerShell and cmd scope cases, the normal PowerShell and
  Monitor commands and the r8 non-POSIX test give the same results as HEAD.
- **Where a comment can start.** The guard starts a comment only for an unquoted `#` outside
  `${…}`, at the start of input or after one of space, tab, newline, `;`, `&`, `|`, `(`, `)`,
  `<`, `>`. These are Bash's metacharacters. After an escape, a quote, `$(…)`, `${…}`, `{` or `}`,
  the next `#` is literal, which matches Bash or is stricter. A line continuation keeps the state
  it follows. The only mismatch found is F18. In the other direction (the guard reads text that
  Bash treats as a comment), the result is a false positive at worst.
- **Comment end.** The guard skips to the physical LF and then processes that LF as a separator,
  in both functions. A comment without a final newline runs to the end of input. Unterminated
  substitution and parameter forms fail closed with their own reasons.
- **Parameters.** Content inside `${…}` no longer splits into segments. That matches Bash 5.2,
  where the body is one word (see V-1 for 5.3). Nested `$(…)` and backticks inside an unquoted
  `${…}` are still analyzed (BD-1, BD-2 return 2).

## Not checked (and why)

- **Linux.** There is no CI run on a head that contains r7 or r8. The owner pushes.
- **Other word-internal parentheses.** Extglob patterns (`@(…)` and similar, when extglob is on),
  compound array assignment `a=(…)` and `[[ … =~ (…) ]]` share F18's root cause, a `)` that
  Bash does not treat as a word end. They were not probed, and extglob's state in the Claude Code
  shell was not checked. F18's alternative fix (fail closed on `)#`) covers them without
  modelling each one.
- **Bash 5.3.** V-1 comes from documentation only.
- **Codex verifier.** `BOOT-001-r8-verify.mjs before|after` was not rerun. This review's
  before/after comparison uses its own HEAD-copy probe, and the applied hashes match Codex's
  candidate.
- **Parser coverage.** There is no complete shell-parser review. Heredocs, option clusters and
  the forms deferred to the next guard-fix task stay outside this patch.
- **Live dispatch.** There is no new evidence beyond `8ad0895`. The posthook was not reviewed
  again (its hash is unchanged).

## Handoff

Do not reapply the patch. The applied files are committed in `a7e14e7`, with blobs `98ab688b…`
and `ec961f6b…`, just before this review. Next:

- **F18** needs a small guard patch and permanent regressions. Under the current role binding,
  Codex writes it, the owner applies it, and a fresh Claude session reviews it. The D-006 request
  (r9) asks for a patch "on the head that contains the reviewed r8". The owner chooses whether
  the F18 fix comes before r9 or inside it. Recommendation: a separate small patch first, so each
  control change keeps its own fail-before/pass-after and review.
- **F19:** the owner decides its placement. The policy for F11 to F15 would put it in the next
  guard-fix task.
- **F11 to F17** stay deferred (owner decision, 2026-10-20). r8 did not make them worse.
- **Owner:** push when ready. CI on the new head gives Linux evidence for the 61 tests.
- Do not add the `owner-approved-control-change` label while F18 is open.

Delivery: implemented, with local verification on Windows. Not verified by CI, not merged.
