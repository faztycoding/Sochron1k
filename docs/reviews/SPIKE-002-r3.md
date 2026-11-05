# Review SPIKE-002 round 3 · head 5d494ac · re-check of r2 at e077fa6 · reviewer Claude Code, fresh headless session (Opus 5.5, 2026-11-05 +07)

Scope: a narrow re-check before the owner's VPS run. I looked only at the r2 findings F8–F10 (`docs/reviews/SPIKE-002-r2.md`, which reviewed e077fa6),
the three commits that answer them (`git diff e077fa6..5d494ac`: dd82371 probe and tests, 36dcb22 runbook, 5d494ac handoff and the saved r2 file),
and any new defect those commits introduced. I read them against contract `docs/contracts/SPIKE-002-vps-remeasure.md` v1.2 (taken as given)
and treated the handoff's "Findings response (review r2 …)" and "Next" sections as claims to verify. I am not the implementer and not the r1 or r2 reviewer.
The owner approved this extra session on 2026-11-05 ("อนุมัติตาม recommended"), because the probe changed after r2 and the hash handed over for the VPS run must be a reviewed one.

I wrote one file: this review, left uncommitted. I did not edit the probe, tests, contract, runbook or handoff, and I staged, committed, pushed and applied nothing.
My scripts, copies, mutant trees and scratch clones are in
`C:/Users/MSI/AppData/Local/Temp/claude/1b3092fce926b7a9/2f7d524d-58e3-439d-8b20-276b764876d5/scratchpad/r3/`:
`behaviour_r3.py`, `mutants_r3.py`, `src_e077fa6/`, `src_5d494ac/`, `mut/`, `git_single/`, `git_shallow/`, `git_full/`, `gitconfig-isolated`, `mypy-cache/`.
The copies match the commits by SHA-256: 5d494ac probe `2002ffd5…2ca5`, tests `e00fded9…6fe2`; e077fa6 probe `55f4545a…d6e8`, tests `82f3a849…64ce` (the values r2 recorded).
No MetaTrader5 package was installed, no terminal or broker was contacted, the probe was never run for real, nothing used the network, and no credential store was opened.

**Result:** F8, F9 and F10 are closed. There is 1 new finding, Low (F11): the F8 allowlist matches its second message by suffix,
so an "unrecognized arguments" message whose last typed token ends with the words "expected one argument" is shown with the login.
Only a constructed input triggers it, and the runbook command cannot produce it.

**Fit for the VPS run at 5d494ac: yes.** The probe, tests and runbook steps 0–4 keep the contract's read-only and refusal rules, every realistic argument typo refuses with exit 2 and no echo, and F11 does not affect the run. Three conditions apply: ENV-001 passes and the Authorization table is filled; Claude pushes the branch first (it is not pushed now); and the hash handed over is 5d494ac or a later commit that leaves `spikes/SPIKE-002/` and the runbook unchanged. The probe must be blob `2b74fc92230c59f7d3ba66b796b855631ab1300a`, SHA-256 `2002ffd515d72c91ac2cf385361ea70acd965cb37a05f5577b217b1be9382ca5`. That value replaces r2's `55f4545a…`, which belongs to the e077fa6 probe.

## Round-2 findings

| ID | Sev | Status | Commit | Evidence | Remaining |
|----|-----|--------|--------|----------|-----------|
| F8 | Low | **closed** for every realistic input (see F11 for a constructed one) | dd82371 | **Code:** `_ArgumentParser.error` (`probe.py:88-93`) shows argparse's text only when it starts with "the following arguments are required" or ends with "expected one argument", and gives a fixed text otherwise. The parser is built with `add_help=False` (`:105`). **Behaviour** (`behaviour_r3.py`, Python 3.12.15, the D-022 pin, 35 inputs, old e077fa6 vs new 5d494ac): `--help=<login>`, `--he=<login>` and `--=<login>` echoed the login on e077fa6 and give `REFUSED (exit 2): arguments: not accepted (values not shown); use the runbook command` on 5d494ac. `--help`, `-h`, `GOOD + --help` and `-h<login>` raised `SystemExit(0)` with usage on stdout on e077fa6, and now exit 2 with no stdout. Realistic typos (a stray login, `-<login>`, `-- <login>`, `--account`/`--password`, unquoted `--clock-sync`, `--login`/`--l=` abbreviations, `--valid=`, `-s<login>`, `---server`) all exit 2 without the login. Every refusal made 0 MetaTrader5 import tries; only the good argument list tried once (exit 3 here, no package), the same as e077fa6. **Tests:** the 4 new cases (`test_probe.py:338-341`) fail on the e077fa6 probe (4 failed, 64 passed: `argv3`–`argv6`), which matches the handoff's "failed 4/4 before", and the e077fa6 tests pass on the 5d494ac probe (64 passed), so no earlier test was weakened. **Mutants:** R1 (`add_help` back) 1 failed, R4 (pass "unrecognized") 5 failed, R5 (pass "ambiguous") 1 failed, R6 (pass everything) 6 failed, R7 (no `error` override) 13 failed, R8 (help back and its message passed) 3 failed. | The allowlist's suffix match: F11. R2 (always hide) and R3 (`in` instead of `endswith`) survive. Both fail closed for every input except F11's. |
| F9 | Low (question) | **closed** | 36dcb22 | Runbook step 3 (`runbook:32`) is `git fetch origin spike/SPIKE-002-vps-remeasure`. I tested scratch clones of the local repository with an isolated config (`GIT_CONFIG_NOSYSTEM=1`, empty `GIT_CONFIG_GLOBAL`, `GIT_TERMINAL_PROMPT=0`) on Git 2.46.1. **Single-branch clone** (refspec `+refs/heads/main:refs/remotes/origin/main`): the old `git fetch origin` still leaves `git switch --detach 5d494ac` failing (`fatal: invalid reference: 5d494ac`, exit 128, HEAD `1c5c5f8`). The new fetch prints `* branch spike/SPIKE-002-vps-remeasure -> FETCH_HEAD` (exit 0); then `HEAD is now at 5d494ac …`, rev-parse `5d494ac`, `git status --short` empty, probe SHA-256 `2002ffd5…`, and `git switch main` exit 0. **Depth-1 clone** (`is-shallow-repository` true, 1 commit): the same, and the ancestor `36dcb22` is also reachable after the fetch, which matters if Claude hands over a hash below the branch tip. **Full clone:** works. **Mistyped branch name:** `fatal: couldn't find remote ref …`, exit 128, HEAD stays on `main`, so the rev-parse check stops the owner. | r2's optional "ask for all output of step 3" was not taken. A failed fetch (for example, the branch not pushed yet) reaches Claude as a hash mismatch without its `fatal:` line. This fails safe at the cost of one round trip. On single-branch and shallow clones, `git switch main` after the run prints Git's "you are leaving N commits behind … git branch <new-branch-name> 5d494ac" advice. It is harmless and comes after the evidence is sent, but the runbook's "หลังเสร็จ" does not mention it. An optional one-line note would fix that. |
| F10 | Low | **closed** | 5d494ac | **Checks table** (`handoff:17-22`): it has a row per r1-fix range with a time, and rows for the final code head `36dcb22` (spike tests 68 passed 19:41:36, suite 3355 passed and 0 skipped 19:41:36–19:42:01, red flags 0 groups 19:42, bundled mypy 1.15 no issues 19:42:09). The times fit the commit times: dd82371 19:41:21, 36dcb22 19:41:25, 5d494ac 19:42:39, and r1 fixes d654016–e077fa6 19:03:06–19:24:02, inside "19:0x–19:2x". The row "the commit after 36dcb22 changes this handoff and the r2 review file only" is true (`git diff --stat 36dcb22..5d494ac`). I reproduced 68 / 3355 / 0 groups / mypy no issues at 5d494ac, whose code is the same as 36dcb22's. **"Next"** (`handoff:91-95`) lists the push (D-006) and the hash hand-over before the run. | Item 1 ("re-check F8–F10 at the evidence review …") is now superseded by this round, which the owner approved for before the run. "Next" names no reference hash for the probe; use the blob and SHA-256 in the "Fit" line above. |

## New findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F11 | Low | confirmed (constructed trigger only) | `spikes/SPIKE-002/probe.py:91`; `docs/handoff/SPIKE-002.md:87` | **Behaviour** (`behaviour_r3.py`, Python 3.12.15): `GOOD + ["123458107", "expected one argument"]` and `GOOD + ["123458107 expected one argument"]` (one quoted token) both give `REFUSED (exit 2): arguments: unrecognized arguments: 123458107 expected one argument`. The e077fa6 probe gave the fixed text for both, so dd82371 narrowly regressed here. **Tests:** adding these 2 inputs to `test_ac01_refusal_never_repeats_what_was_typed` gives 2 failed, 68 passed at 5d494ac (`mut/F11_adversarial_tests_on_new_probe`). **Why only this case:** I read every message argparse 3.12.15 can raise (`Lib/argparse.py`). For this parser (four required one-value options, no type, choices, help or version action), only "unrecognized arguments: <typed tokens>" can end with typed text. "ambiguous option" ends with option names. "ignored explicit argument" can no longer occur, because no option takes zero values. **Untested pass-through:** no test asserts that the two option-name messages are shown, so mutants R2 (always the fixed text) and R3 (`in` for `endswith`) survive with 68 passed. | The owner types extra words after the arguments, and the last one ends with the exact phrase "expected one argument". The runbook command cannot produce this, and a typo is very unlikely to. | In that case only, the full login reaches the line the owner pastes back (contract Q3). The exit code stays 2, nothing reaches the terminal, and the runbook's visual check before pasting (`runbook:53`) still applies. The handoff's F8 sentence, "Only argparse messages made of option names are shown", holds for every input except this one. | Match the second message whole, for example `re.fullmatch(r"argument --[a-z-]+: expected one argument", message)`. Add a test that the two option-name messages are shown, to pin the pass-through. **Recommended timing:** a probe change moves the hash and needs another re-check before the run. Given the trigger, the cheaper path is to leave the probe as it is, record F11 as an accepted Low, and narrow the handoff sentence in the next commit (docs only; the probe blob is unchanged). Do not change the probe after the run, because the PR's probe would then differ from the one that produced the evidence. | Fix sketch (`mut/F11_fix_sketch_with_adversarial_and_option_tests`): 71 passed (68 + the 2 inputs + 1 option-name test). The option-name test passes on 5d494ac (69 passed) and kills R2 (1 failed). |

### Mutants (5d494ac tests unchanged unless named, each in its own tree under `r3/mut/`, pytest run from the tree root)

| Mutant or variant | Result | Killed by / note |
|---|---|---|
| M00 unmutated copy | 68 passed | sanity check (probe SHA-256 `2002ffd5…`) |
| R1 `add_help=False` removed | killed (1 failed) | `…refusal_never_repeats_what_was_typed[argv6]` (`["--help"]`: `SystemExit(0)`) |
| R2 allowlist removed: always the fixed text | **survives** (68 passed) | fails closed; F11 adds a test that kills it |
| R3 `"expected one argument" in message` instead of `endswith` | **survives** (68 passed) | widens only the F11 case |
| R4 "unrecognized arguments" passed through | killed (5 failed) | `[argv0]`–`[argv4]` |
| R5 "ambiguous option" passed through | killed (1 failed) | `[argv5]` (`--=<login>`) |
| R6 every message passed through (F3 and F8 reverted) | killed (6 failed) | `[argv0]`–`[argv5]` |
| R7 no `error` override (argparse prints usage and exits) | killed (13 failed) | 5 bad-argument tests, the fresh-load test, 7 echo tests |
| R8 help back and its "argument -h/--help" message passed through | killed (3 failed) | `[argv3]`, `[argv4]`, `[argv6]` |
| M01 account `trade_allowed` check skipped (r2 regression check) | killed (4 failed) | `…wrong_account…[acct5/acct6]`, `…account_flag_decides…`, `…main_refuses_through_stderr…` |
| M02a MetaTrader5 imported before the argument check (r2 regression check) | killed (14 failed) | 13 bad-argument tests (tries = 1), the fresh-load test |
| M07 M1 search runs past the cutoff (r2 regression check) | killed (4 failed) | the F1 test ×4 |
| e077fa6 probe + 5d494ac tests | 4 failed, 64 passed | `[argv3]`–`[argv6]`: the new F8 cases, as the handoff says |
| 5d494ac probe + e077fa6 tests | 64 passed | no earlier test weakened, no earlier behaviour changed |

## AC status
PASS here covers only the unit-level evidence named in each row. UNKNOWN does not count as passed.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS (unit) | 68 tests pass. Every bad or missing argument and every refusal exits 2 before any MetaTrader5 import try. `--help` no longer exits 0. Mutants R1, R4–R8, M01 and M02a are killed. F11 concerns the refusal text in a constructed case, and the exit code stays 2. |
| AC-02 | UNKNOWN | The owner's VPS run (L4) is pending, after ENV-001 and the Authorization table (still TBD). |
| AC-03 | UNKNOWN | The VPS run is pending. F6's answer defines the evidence wording. |
| AC-04 | UNKNOWN (unit part PASS) | **Unit part:** the tests pass, and the time code did not change since e077fa6 (`git diff e077fa6..5d494ac` touches only `error` and the parser line). **VPS part:** pending. |
| AC-05 | UNKNOWN (key list and post-cutoff search PASS) | **Unit part:** the exact-key test passes, and M07 is still killed. **VPS part:** pending. |
| AC-06 | UNKNOWN | **Red flags:** 0 groups. **Spike tests:** 68 passed. **Suite:** 3355 passed, 0 skipped. **CI:** not run, because the branch is not pushed (`git branch -r --contains 5d494ac` is empty). |

## Checked, nothing found (and how)
- **Scope:** `git diff --stat e077fa6..5d494ac` touches 5 files: probe, tests, runbook, handoff, and the r2 review in the review channel. Per commit: dd82371 probe and tests only, 36dcb22 one runbook line, 5d494ac handoff and r2 only. Nothing changed in `src/`, `tests/`, `pyproject.toml`, `uv.lock`, `.github/`, `.claude/` or `spikes/SPIKE-001/`. The red-flag scan lists no control files touched, no deleted tests and no untracked files.
- **No path to exit 0 or stdout on a bad argument:** `error` is overridden, and with `add_help=False` the parser has no help or version action, so argparse has nothing left that prints and exits. None of the 35 inputs raised `SystemExit` on 5d494ac, and every refusal left stdout empty.
- **Messages the allowlist shows hold only option names:** "the following arguments are required: …" lists action names, and "argument --x: expected one argument" names the option. I checked both against the 3.12.15 source and in the behaviour run (`--clock-sync` missing; `--server` or `--clock-sync` last without a value).
- **Fails closed under translation:** `gettext.find('messages')` gives `None`, so the messages stay English. If they were ever translated, they would no longer match the allowlist and would get the fixed text.
- **The Python checked is the Python of the run:** the project environment runs CPython 3.12.15, the same version as the D-022 command's `--python 3.12.15`, so the argparse behaviour above is what the VPS will see.
- **The probe's bytes on the VPS:** `.gitattributes` has `*.py text eol=lf` (and `*.md text eol=lf`), so a checkout gives LF even with `core.autocrlf=true`, which the Git for Windows system config sets on this machine. The SHA-256 above is therefore stable, and the commit-hash check plus an empty `git status --short` pin the file anyway.
- **`uv run --no-project` from the repo root:** `pyproject.toml`'s `[tool.uv]` holds only `package = false`, and there is no `uv.toml` or `.python-version`, so nothing in the repo changes how the D-022 packages resolve.
- **Types:** the editor's bundled mypy 1.15.0 reports "no issues" on `probe.py` and `test_probe.py`. It prints two `annotation-unchecked` notes in the test file. The contract does not require a type check.
- **The handoff's claims** in the r2 response and the checks table were verified as recorded under F8–F10. The one exception is F8's "only option-name messages are shown" (F11).

### Checks run (2026-11-05, +07, head 5d494ac, tree clean)
| Command | Result | Commit | Time |
|---|---|---|---|
| `git rev-parse 5d494ac:spikes/SPIKE-002/probe.py`; `git show … \| sha256sum`; `sha256sum` of the worktree files | probe blob `2b74fc92…`, SHA-256 `2002ffd5…2ca5` (commit = worktree); tests SHA-256 `e00fded9…6fe2` | 5d494ac | 13:57 |
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` | PASS: 68 passed in 0.14s, exit 0 (uv warns that `VIRTUAL_ENV` points to the main checkout's `.venv` and ignores it) | 5d494ac | 13:57:44–13:57:45 |
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: 3355 passed in 25.12s, 0 skipped, exit 0 | 5d494ac | 13:57:48–13:58:14 |
| `bash scripts/controls/red-flags.sh main` (main = 1c5c5f8, merge-base 67bb4df) | PASS: "Pattern groups with hits: 0", exit 0; no control files, no deleted tests, no untracked files | 5d494ac | 13:58:16 |
| `uv run --offline python -I <r3>/behaviour_r3.py <r3>/src_e077fa6/probe.py <r3>/src_5d494ac/probe.py` | 35 inputs. F8's 3 echo inputs and the 4 exit-0 inputs are fixed. 2 constructed inputs echo on 5d494ac only (F11). Import tries: 0 for every refusal. | e077fa6 vs 5d494ac | 13:59:25 |
| `uv run --offline python -I <r3>/mutants_r3.py <r3>/src_5d494ac <r3>/src_e077fa6 <r3>/mut` | M00 68 passed; R1, R4–R8, M01, M02a, M07 killed; R2, R3 survive; cross runs 4 failed / 64 passed; F11 inputs 2 failed; fix sketch 71 passed | 5d494ac (+ e077fa6) | 14:00:30–14:00:42 |
| `git branch -r --contains 5d494ac` | empty: the task branch is not pushed | 5d494ac | 14:01 |
| `git clone --no-local --single-branch --branch main <worktree> <r3>/git_single`, then old and new step 3, then `git switch main` (isolated config, Git 2.46.1) | old fetch: switch fails (exit 128); new fetch: reaches 5d494ac, status empty, probe SHA-256 matches; back to main exit 0 with the "leaving 12 commits behind" advice | 5d494ac | 14:01:19–14:01:28 |
| `git clone --no-local --depth 1 --branch main <worktree> <r3>/git_shallow`, then new step 3, then the ancestor 36dcb22, then `git switch main` | shallow (1 commit); 5d494ac and 36dcb22 both reachable after the fetch; back to main | 5d494ac | 14:01:42 |
| `git clone --no-local --branch main <worktree> <r3>/git_full`, then new step 3, `git switch main`, and a mistyped branch name | works; typo gives `couldn't find remote ref` (exit 128) and HEAD stays on main | 5d494ac | 14:01:52 |
| `PYTHONPATH=<mypy-type-checker-2026.6.0>/bundled/libs uv run --offline python -m mypy --cache-dir <r3>/mypy-cache spikes/SPIKE-002/probe.py` (and `test_probe.py`) | mypy 1.15.0: "Success: no issues found" for each; 2 notes in the tests | 5d494ac | 14:02:32 |

## Not checked (and why)
- **The VPS side of step 3**, because my clones used a local path: a real HTTPS fetch from GitHub, the VPS's Git version (`git switch` needs ≥ 2.23), and Git's dubious-ownership check. r2's note still stands too: if the repository stopped being public, the fetch would prompt for a username, and the runbook does not say "press Ctrl+C and stop" at a prompt. That would fail safe at the rev-parse check.
- **Real terminal behaviour**, as in r1 and r2: the Unlimited `maxbars` value on the VPS build, inclusive `date_to`, the timing of 240 requests, and `symbol_info_tick` on a closed market. The probe's terminal code is unchanged since e077fa6.
- **The D-022 environment:** MetaTrader5 and numpy are not installed here. **CI:** not run, because the branch is not pushed. **OSV:** not repeated (D-022 recorded it on 2026-10-25T09:56Z).
- **PowerShell quoting of the step-3 run command:** the command did not change in these commits, so I did not re-check it.
- **Whether the committed r2 file is word for word what the r2 session wrote:** I cannot check that from the repository. I read it as the record.
- **Delivery state:** this review does not move it. It stays at implemented.

## Follow-ups and next action
1. **Before the run:** fill the Authorization table, push the task branch (D-006), and give the owner 5d494ac or a later commit that leaves `spikes/SPIKE-002/` and the runbook unchanged. The evidence records the probe SHA-256 `2002ffd5…`, not r2's `55f4545a…`.
2. **F11:** recommended handling is to accept it as Low with the handoff sentence narrowed (docs only). Fixing the probe instead means a new hash and another narrow re-check before the run.
3. **Optional runbook notes:** one line saying the "leaving N commits behind" advice after `git switch main` needs no action (F9), and one saying to stop if git asks for a username (r2).
4. **The evidence review after the run** is another headless session beyond the contract's budget of 2 (r1, r2 and now r3 used). Confirm that the 2026-11-05 delegation covers it, or ask the owner.

Ready for PR: no, as expected, because the PR follows the VPS evidence (contract Plan step 5).

Findings open: 1 (F11, Low)
