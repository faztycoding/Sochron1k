# Review ENV-002-tests-v2 round 1 · base 4a5897e + applied, uncommitted docs/proposals/ENV-002-v2-tests.patch · reviewer Claude Code, fresh subagent session (fresh-eyes-reviewer), tests reviewer under the role swap (ซ)

**Scope**
- The patch is `docs/proposals/ENV-002-v2-tests.patch` (SHA-256 `3cbb6b57…3725`). It is applied but not committed on `chore/ENV-002-macos-research-host` at `4a5897e`, in `/Users/faztycoding/Documents/GitHub/Sochron1k`.
- It holds six new files in `tests/acceptance/ENV-002/` and one change to the locked `tests/architecture/test_imports.py`.
- The oracle is contract v2.6 (`docs/contracts/ENV-002-research-host-separation.md`). `src/sochron/app/envcheck.py` is still the v1.9 reader.

**Binding.** The contract's Invariants (:416) and Budget (:657) give the tests-reviewer role to a fresh Claude session under (ซ). This is therefore the tests review of record, not a pre-review.

## How I verified, and the limit of it

**Order I kept**
1. The whole contract at HEAD.
2. Every line of the six new files, the `test_imports.py` diff, `envkit.py` and `synthetic.py`.
3. My first round of findings (F1–F3).
4. Only then the handoff. It added F4, F5 and the answers to Q1–Q11.

**What I did not read:** `docs/handoff/ENV-002.md`, chat logs, and the test author's `prompt.md` and `run.json`. I read the v1.9 `envcheck.py` only to explain the red failures.

**Checks run (command → result → commit → time)**
- `PYTHONTZPATH="" ~/.local/bin/uv run --offline --locked --no-build pytest tests -q -p no:cacheprovider`
  → 194 failed, 3705 passed in 13.61 s. The FAILED set equals the implementer's `redrun-v2tests.txt` line for line.
  → 4a5897e + applied patch → 2026-11-18 18:50 +07
- Failure messages in that run → 181 say "not implemented" (168 AC-02, 13 AC-05). The other 13, all in `test_ac02_darwin_evaluate.py`, are AssertionErrors → same → 18:5x
- The six new files plus `test_imports.py::test_ac06_env002_envcheck_admits_only_the_darwin_libsystem_forms`, with `-v` → 194 failed, 13 passed. The 13 are the five dataless or iCloud cases, the seven symlink cases and the AC-06 self-test → same → 18:5x
- `pytest tests/architecture` → 23 passed → same → 18:5x
- `bash scripts/controls/red-flags.sh main` → "Pattern groups with hits: 0". The script does not scan untracked files, so I applied its eight patterns to the six new files by hand: 0 hits → same → 18:5x
- `git apply -R --check docs/proposals/ENV-002-v2-tests.patch` (standalone) → exit 0, no output → same → 18:5x
- `wc -c`, `wc -l`, `shasum -a 256` and `git hash-object --no-filters` of the seven files, the patch's size and line count, and `git rev-parse HEAD:tests/architecture/test_imports.py` → every value equals handoff §2 (table under "Checked", a) → same → 18:5x
- `git status --short --untracked-files=all`, `git diff --stat`, `git diff --cached --stat`
  → only `M tests/architecture/test_imports.py` (142 lines added, 1 removed), plus the six untracked test files and the handoff. Nothing staged. Same before and after my runs.
- Probe of the AC-06 checker on 30 sample sources. It loads `test_imports.py` by path and calls `_inspect_envcheck_source` → `probe_ac06.out` → 18:5x
- Probe comparing the HEAD checker with the applied one on 6 sources. The HEAD version is read from `git show`, so no copy is written → `probe_ac06_head.out` → 19:0x
- Mutation probe: a pytest plugin loaded with `-p probe_mutants`, run with `PYTHONDONTWRITEBYTECODE=1` and `--basetemp` inside my scratchpad. Six evaluate mutants and three checker mutants → `probe_mutants_evaluate.out`, `probe_mutants_overbroad.out`, `probe_mutants_checker.out` → 19:0x
- `/sbin/mount` (read-only) → 12 mounts, used in F2 → 19:0x

The probe scripts and their outputs are in `/private/tmp/claude-501/-Users-faztycoding-Documents-GitHub-Sochron1k/38a03acd-6822-4cac-ae23-d960d6191884/scratchpad/tests-v2-r1/`.

**Limits**
- **Integrity has no independent anchor.** I checked it against the handoff and patch the implementer handed over. All sessions run under one macOS account and share one scratchpad, and nothing the test author made is committed. The author's stage copies (`…/scratchpad/v2tests/stage/`) hash equal to the applied files; that shows consistency, not independence. This falls in the class of (ญ) 16.
- **No Linux run.** Section (e) is by reading only.
- **No darwin implementation exists.** Satisfiability is by reading. Executed evidence covers only the 13 green items and the checker.
- **One side effect.** The instructed red run refreshed the gitignored `__pycache__` folders under `tests/`, because that command writes bytecode. My probes did not.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | `tests/acceptance/ENV-002/test_ac05_darwin_cli.py:184–198` | The gate test returns on any `ResearchHostError` (:193–195). `require_research_host` raises that error in two situations: when the roots cannot be built, and when the verdict is not PASS (`src/sochron/app/envcheck.py:815–821`). The test uses the real `default_roots`, so `repo` is the real checkout (envcheck.py:782). | A `default_roots` that does not raise for the unreadable folder, for example one that skips it. | The gate then runs `collect` (fakes) and `evaluate` on the real checkout, opening its text files. The test passes whenever that checkout is not PASS. On CI it never is: CI builds `.venv` in the checkout (`.github/workflows/ci.yml:71`), and uv's `.venv/lib64 -> lib` link is UNKNOWN (contract :365). So for this mutant the test passes without checking anything on Linux, and it reads the real machine. No behaviour goes untested: the CLI twin (:161–181, "no `roots:` line") and `test_ac02_darwin_collect.py:435–444` still catch the mutant. | In a new test-author patch, make the cause visible: replace `evaluate` with a recorder that fails the test if called, or spy on `collect` and require no call. | With `default_roots` faked to return `mac.roots(ec)`, the fixed test fails on the Mac and on Linux. With a contract-faithful `default_roots` it passes. |
| F2 | Low | confirmed | `test_ac02_darwin_evaluate.py:235–248`; `test_ac02_darwin_reader.py:131–190` | The owner's Mac has `.venv/bin/python3.12 -> python` (contract :38). `/sbin/mount` on this Mac (2026-11-18) shows `/`, `/dev`, and under `/System/Volumes/`: `Data`, `Data/home`, `Hardware`, `Preboot`, `Update`, `Update/SFR/mnt1`, `Update/mnt1`, `VM`, `iSCPreboot`, `xarts`. Contract :333–337 allows all of them. The tests use only the link names `python`, `python3` and `python3.9 -> another file`, and only the mount points `Data`, `Data/home`, `Preboot` and `Update/mnt1`. | An implementation that excuses only `python` and `python3` (or a one-digit `python3\.[0-9]`), or one that allows a named list of system volumes instead of "everything under `/System/Volumes/` except below `Data/`". | Every new test still passes. The `python3.9` case expects UNKNOWN because of its target, so it cannot tell the name rule apart. AC-01 on the owner's Mac would then come out UNKNOWN, found only in the L4 round. | Add two cases:<br>- on `evaluate`: `.venv/bin/python3.12 -> python -> the running interpreter`, expected not UNKNOWN;<br>- on `classify_mounts`: the measured 12-mount table, expected PASS.<br>Either an additive test-author patch, or, without a new session, the implementer's unit tests in `tests/unit/app/` (contract :49), checked by the work review. | Both cases fail against the two mutants above and pass against a contract-faithful reader. |
| F3 | Low | confirmed (existed before this patch) | `tests/architecture/test_imports.py:2915–2937`, `:2940–2958` (not changed by the patch) | `_inspect_envcheck_source(_synthetic(["import os", "def f():", "    return os.__dict__['system']('id')"]))` returns `[]`. So do `os.__dict__['remove'](path)` and `ctypes.__dict__['CDLL']('libc.so.6').system(b'id')`. The HEAD checker and the applied one give the same result (`probe_ac06_head.out`). Attribute access on a held module is allowed (:2950–2951), and `__dict__` is in no deny set (:2752–2753, :2761–2766). | envcheck code that reaches a denied member through `<module>.__dict__[…]`. | AC-06 says other forms are refused on purpose (contract :459). This form is accepted, so the AC-06 L2 evidence does not cover deliberate evasion. The patch did not introduce it. Exploiting it takes deliberately evasive code, which the work review would see. A fix lies outside the narrow exception: contract :416 says changes outside the darwin ctypes forms go to the owner first. | Owner decision:<br>(a) record it as an accepted limit next to v1.6 Q12; or<br>(b) a separate test-author patch that reports any dunder attribute of a held name as an escape. | Under (b), the three sources each give a finding and every existing row is unchanged. |
| F4 | Low | confirmed | `docs/handoff/ENV-002-v2-tests.md:11–19`, `:180–193` | The handoff predicts that every failing new item fails with "not implemented", and tells the implementer that any other failure is a patch defect to send back. In the red run, 181 items fail with "not implemented". The other 13, in `test_ac02_darwin_evaluate.py`, fail on assertions, because `_ec()` asks only for v1.x names and so they run against v1.9. Each of the 13 fails for a v2.x rule that v1.9 lacks (table in "Checked", b). | Following §1 of the handoff literally. | A correct patch would be sent back, and the record of the red state would be wrong. | No test change. The commit message and PROGRESS use this review's red result. §1's rule is superseded for these 13 items. | The red commit message records 194 failed (181 "not implemented", 13 assertions on v2.x rules) and 13 passed. |
| F5 | Medium | confirmed (process) | Process. `docs/handoff/ENV-002-v2-tests.md:277–304`, `:207`; `.claude/settings.json:19`; `CLAUDE.md:21–22`; `AGENTS.md:102` | (1) The deny rule `Edit(**/tests/acceptance/**)` refused a Write to the author's scratch copy. The author then wrote the same content under flat names in `…/scratchpad/v2tests/stage/`, copied `test_imports.py` there, built the patch with `git diff --no-index`, and rewrote three header lines with the Edit tool (§10.2).<br>(2) After a denial it retried the red run once in another form, which it says the rules forbid (§10.1).<br>(3) It replaced a denied `sed` with diff prefixes and `cat`, and a denied `grep $'\r'` with the Grep tool (§10.3–4).<br>(4) It ran `git apply --check` chained after `cd` (:207), although AGENTS.md lists that check as a standalone command.<br>CLAUDE.md says: "When blocked, stop and ask the owner. Never route around a block with scripts, interpreters, renames or another tool."<br>This project's precedent is to stop:<br>- PROGRESS.md:82 (CORE-002): a deny rule refused `cp` under `tests/acceptance/`, and the agent wrote "หยุด ไม่หาทางอื่น" (stopped, looked for no other way).<br>- `ENV-002-tests-r1.md:13–16, :216–221` and `ENV-002-tests-r2.md:23–25, :185–190`: the reviewers stopped and did not rebuild the files another way. | A headless session without an approval prompt meets a deny rule while doing its assigned job. | The artifact is not harmed. The deny rule protects the repository's locked paths, and those changed only through the D-006 apply. The seven files equal the handoff byte for byte, and so do the stage copies.<br>The harm is to the control record. An owner rule was relaxed on an agent's own judgement, and accepting that silently makes "rename past a deny rule" a precedent.<br>Two smaller points: the author never ran its own tests (write-acceptance-tests step 5); the implementer and this review did. The author's working files, `prompt.md` and `run.json` included, sit in the parent session's scratchpad, where the implementer can read them. | Owner decision; see "F5: recommendation" below. | A PROGRESS (or DECISIONS) entry with the owner's choice. Under option (b), also a new handoff whose block section shows no route-around and whose bytes pass this review's integrity checks. |

### F5: recommendation — 3. owner decision needed

**Why the owner has to decide**
- CLAUDE.md:21–22 and AGENTS.md:102 are categorical, and this project applies them strictly (PROGRESS.md:82; the Blocks sections of tests-r1 and tests-r2).
- By that standard, step (1) is a route-around: renamed paths and another tool put in place the content the refused write would have held. Step (2) is a retry in another form.
- Neither the implementer nor a reviewer can excuse a breach of an owner rule.

**Why I do not recommend discarding outright**
- Re-making the same bytes adds no assurance about the artifact: they are hash-verified and every line was reviewed here.
- The contract's budget of fresh sessions has no spare left (contract :657). Any re-make needs the owner anyway.

**Options**
- **(a) Recommended. Accept the applied bytes and commit red.** In the same PROGRESS or DECISIONS entry:
  - Rule whether "write the files in a staging folder outside the repository, then build the patch with `git diff --no-index`" is a sanctioned way for a Claude test author to make a D-006 patch. If yes, name it in the next author's brief so no block is met. If no, say what is.
  - Record the red-run retry and the chained `git apply --check` as breaches.
  - Delete `…/scratchpad/v2tests/`; handoff §14 already says it is safe to delete.
- **(b) If the rule stands as written: discard the patch and the stage folder, raise the fresh-session cap by one, and run a new test-author session.**
  - Its brief names an owner-approved way to build the patch before it starts.
  - Fold in F1 and F2.
  - A new tests review follows.
- **(c) Wait for Codex on the Mac.** This is the D-002 default and needs P25 of Codex on the Mac first. It is the slowest path; not recommended.

## Ready to commit red and implement: no

The only blocker is F5, and F5 is the owner's call.

On the tests' own merits the answer is yes:
- There is no High or Medium defect in the tests themselves.
- All 194 red items fail for the right reason.
- The 13 green items are not vacuous: each one fails under at least one wrong implementation (section b).
- One implementation can pass every test at once.
- Every macOS negative case has a test.
- The checker change is as narrow as AC-06 allows.

The other findings do not block red:
- F1 and F2 are additive.
- F3 existed before this patch and is the owner's.
- F4 needs no test change.

If the owner chooses (a), commit the seven files as they are (`test(env-002): …`, `Refs: ENV-002`) and use F4's red numbers. CI still needs the owner's `owner-approved-control-change` label on the PR.

## Findings open: 5

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-01 | UNKNOWN | The owner's L4 round on the Mac; outside a tests review. |
| AC-02 | FAIL (expected red) | 193 new items: 181 fail (168 "not implemented", 13 assertions on v2.x rules) and 12 pass, because v1.9 already does what they check. I judge the tests sound. |
| AC-03 | UNKNOWN | L4. |
| AC-04 | PASS | The locked tests, which this patch does not change, pass in the run. |
| AC-05 | FAIL (expected red) | 13 new items fail with "not implemented"; the v1.x AC-05 items pass. |
| AC-06 | PASS for the checker; UNKNOWN for the darwin source | The new self-test and the existing AC-06 tests pass (23 in `tests/architecture`). The scan of `envcheck.py` with darwin code waits for that code. F3 is open. |
| AC-07 | FAIL (expected) | 194 failed, 3705 passed on the Mac (3692 existing + 13 new green). CI not run. |

## Answers to Q1–Q11

- **Q1 — collect gets the application folders only through `_darwin_application_dirs`.** The contract supports this.
  - :166–167 and :185 list the function among those tests may replace.
  - :206–207 requires the application cases on the real `collect` with fakes.
  - :414 allows only temporary folders and fake values for macOS cases.
  - Together these mean `collect` must get both application folders through that function. `outside_reads` (darwinkit.py:295–314) enforces it.
  - No owner decision.
- **Q2 — order of the `cloud storage:` providers.** The contract fixes no order for providers. It fixes one only for mount types (order found) and for `tools:`/`apps:` (contract order), at :230–231. Accepting either order is the faithful reading.
  - It matters only if R1 compares the whole `roots:` line (:404).
  - If it does, fix the order in the SLICE-R1 contract, either sorted or listing order. Not needed now.
- **Q3 — type of `_darwin_home()`.** The contract supports str: its real value is `os.path.expanduser("~")` (:275–276). The implementation must accept str.
- **Q4 — "a folder at level 1 of drive_c/Program Files".** The contract supports `<root>/Vendor`.
  - By the level definition (:80), `<root>/Vendor` holds the level-1 files.
  - Under r2 F10 (:283–284), any unlistable folder under the root makes the search incomplete. So both readings give UNKNOWN.
- **Q5 — items for a root below a dataless ancestor.** The contract supports the tests' choice.
  - :356 maps dataless folders: under the repo or a data dir → holdout_dir, excluded_period and sentinel UNKNOWN; under search dirs → sentinel only.
  - :445 applies this to roots with a dataless ancestor.
  - The v1.9 rule at :128 agrees: an unlistable root is UNKNOWN for every item that searches it.
- **Q6 — which layer builds the `proc_listallpids failed, errno <n>` and `getfsstat failed, errno <n>` reasons.** The contract does not say (:187–193, :241, :245). This is not an owner decision; the implementer picks, records it and unit-tests it.
  - Suggestion: the raw reader raises `OSError(errno, …)` and the pure layer builds the reason from `error.errno`.
  - A fake can then test it, and a later additive case can pin it.
- **Q7 — pid 0 skipped whatever its errno.** The contract supports this. :293 says "ข้ามและนับเฉพาะ pid 0 และโปรเซสที่ proc_pidpath ล้มด้วย ESRCH" (skip and count only pid 0 and processes where proc_pidpath fails with ESRCH), and :191 says the same. pid 0 is a category of its own.
- **Q8 — twelve evaluate cases already pass on v1.9.** Accept as is.
  - Gating them on an unrelated v2 name would make them fail for the wrong reason (write-acceptance-tests steps 4–5).
  - My mutation probes show each one fails under a plausible wrong v2.x evaluate (section b).
  - The plan check "tests ใหม่ล้มก่อนมีโค้ด" (new tests fail before the code exists; :526) holds for every item that tests a new rule.
  - Record the 13 green items in the commit message (see F4).
- **Q9 — the darwin open at import time reported as "Windows-only access at import time".** Accept.
  - :374 asks only for "a finding like the Windows rule" and fixes no wording.
  - The existing message names the right line, and no locked message changes.
  - The text is misleading for libSystem, which is cosmetic. The narrow exception would allow a new constant if the owner wants clearer text.
- **Q10 — `import ctypes as c; c.CDLL(<exact args>)` is admitted.** Accept.
  - The checker resolves aliases the same way for every rule. That same resolution is what makes `import ctypes as c; c.cdll` a finding (test_imports.py:2841–2895, :2930–2931).
  - The alias grants nothing beyond the exact form: same literal, same keyword, the same three functions, the same escape and import-time rules. My probe: `x = ctypes; x.CDLL(...)` is admitted; `from ctypes import CDLL as C` is refused.
  - AC-06 (:459) constrains the call and the literal, not the module's local name.
  - Optional: an additive ALLOWED row that pins this, so a later checker change cannot flip it silently.
- **Q11 — `.app` in `apps:` names, and the path text in `skipped:`.** The contract supports the lenient checks.
  - `apps:` (:253) does not say whether names keep `.app`.
  - `skipped:` (:252) does not fix the path text; only `wine:` requires paths starting with `~/` (:249).
  - `apps:` is one of R1's compared lines (:404), so SLICE-R1 may need to fix its form later.

## Checked, nothing found (and how)

### a. Integrity

| File | Bytes | Lines | SHA-256 | Blob | = handoff §2 |
|---|---|---|---|---|---|
| `tests/acceptance/ENV-002/darwinkit.py` | 18678 | 370 | `6508ca0a…c303` | `21f5d9f3…` | yes |
| `…/test_ac02_darwin_collect.py` | 22004 | 444 | `440f2ce8…b1f6` | `1cf318e9…` | yes |
| `…/test_ac02_darwin_evaluate.py` | 10857 | 256 | `f8c0b604…fec6` | `7d01e4d0…` | yes |
| `…/test_ac02_darwin_host_lines.py` | 17791 | 333 | `6c72aa30…ab80` | `8156f46e…` | yes |
| `…/test_ac02_darwin_reader.py` | 33397 | 602 | `192b9674…8a65` | `8d83250e…` | yes |
| `…/test_ac05_darwin_cli.py` | 10105 | 215 | `bd593c0d…7f8b` | `ca97b3df…` | yes |
| `tests/architecture/test_imports.py` | 209202 | 3581 | `52073db5…dbd9` | `6adc48ad…` (base `33187ab6…` = HEAD) | yes |
| patch | 130608 | 2456 | `3cbb6b57…3725` | – | yes |

- All seven files have 0 CR bytes.
- The patch's `index` lines equal the blobs above.
- `git apply -R --check` exits 0.
- No other tracked file changed. `envkit.py`, `synthetic.py` and the existing ENV-002 test files do not appear in `git status`. The only tracked change is `test_imports.py`, and its only removed line is `if broken:`.

### b. Red run

**The 13 assertion failures fail for the right reason.** v1.9 lacks each rule; none is a test defect.

| # | Item (`test_ac02_darwin_evaluate.py`) | v1.9 result | Rule that makes the difference |
|---|---|---|---|
| 1 | `.notes.txt.icloud` under a data dir | excluded_period PASS, sentinel PASS | v2.1 F6 (:349) |
| 2 | `.<sentinel name>.icloud` in iCloud Drive only | sentinel PASS | :352 (FAIL by rule (2)) |
| 3 | the same name in upper case | sentinel PASS | :349 (ไม่สนตัวพิมพ์, case ignored) and v1.6 Q4 |
| 4 | `.x.json.icloud` in iCloud Drive only | sentinel PASS | :352 (UNKNOWN) |
| 5 | `.<sentinel name>.icloud` under `<repo>/data` | PASS, PASS | :350–351 (r4 F54) |
| 6 | a dataless folder in iCloud Drive | listed, the copy opened, sentinel FAIL | :354–356 |
| 7 | a dataless folder under `<repo>/data` | listed, manifest opened, excluded_period FAIL | :354–356 |
| 8 | a data dir below a dataless ancestor | root stat'ed and listed, excluded_period FAIL | :445 (r2 F12), :355 |
| 9 | a search dir below a dataless ancestor | root stat'ed and listed, sentinel FAIL | :445 |
| 10 | a `metatrader 5` folder in appdata under a data dir | listed, `notes.txt` opened, sentinel FAIL | :441 (r3 F28) |
| 11–13 | `.venv/bin/python` → interpreter; `python3` → `python` → interpreter; through an outside link | holdout_dir, excluded_period, sentinel UNKNOWN | :360–362 (v2.1 F5) |

Rows 8–9 also show v1.9's `_below_terminal` stat of `Cloud/terminal64.exe`. A correct implementation must check dataless ancestors top-down before that probe (:355). That is possible, so the test can be satisfied.

**The 13 green items are not vacuous.** For each one, a probe mutant makes it fail:

| Green item | Mutant that makes it fail |
|---|---|
| dataless `.json` of the sentinel's size in iCloud Drive | evaluate ignores `is_cloud_only` → FAIL and the file is opened |
| dataless `.json` of another size | every cloud-only `.json` in the search dirs is made UNKNOWN regardless of size |
| dataless `.txt` under `<repo>/data` | evaluate ignores `is_cloud_only` → FAIL and the file is opened |
| `.x.png.icloud` | every `.icloud` in the search dirs is made UNKNOWN |
| the Privacy-locked folder | an unlistable folder is skipped silently |
| `python3.9` → other file; copy of the interpreter; broken link; loop; link to a folder; `pip3` | every symlink in `.venv/bin` is excused (all six fail) |
| `<repo>/tools/python` | every `python*` link anywhere under the repo is excused |
| AC-06 self-test | any of three checker mutants: path compared by basename; keywords ignored; any function allowed on the handle |

### c. Contract fidelity

**Every macOS negative case has a test.** I mapped every case of the paragraphs at :421, :423, :425, :427, :429, :431, :433, :435, :437, :439, :441, :443, :445, :447 and :449 to at least one test item. Each test calls or replaces the function its paragraph names:
- `read_process_paths` with both raw readers faked;
- `collect` with `read_process_paths` replaced;
- `classify_mounts` and `classify_processes`;
- `read_mounts` with `_darwin_mounts` faked;
- `wine_prefixes`;
- `find_terminal_paths_darwin` with `never_listed = (<home>/Library, <home>/.ssh)`;
- `collect` with `find_terminal_paths_darwin` faked, for the `.colima` audit;
- `is_cloud_only` with a fake stat;
- `host_lines` through `research_host_report`, and with `_HOST_SUMMARY` replaced by `{}`;
- `evaluate` for r3 F28;
- the CLI and the gate for an unreadable `wineprefix`, `Bottles` or `CloudStorage`.

Missing cases: none.

**No test asks for behaviour a contract-faithful implementation would fail.** These readings are stricter than the literal text; I checked each and accept it:
- the `.colima` check also forbids opens, not only `os.scandir` (consistent with "existence only", :304);
- PASS-named folders in Application Support must stay untouched (":310, list only one level");
- `MetaEditor.app` stays untouched (names only, :281);
- pid 0 is skipped whatever its errno (Q7);
- for an empty pid list, `listed 0 pids` wins over "own pid missing";
- `process_names` keeps each basename's case.

**One implementation can pass all the tests at once.**
- No two new tests contradict each other.
- None contradicts a locked v1.x test. The v1.x AC-05 CLI tests check only the last line, the item names and the token, and they replace `collect`. The v1.x "MetaQuotes inside a `--data-dir`" case keeps the silent skip that r3 F28 (:319–320) allows.

### d. The AC-06 locked checker change

**What it accepts**
- `<ctypes>.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)` in code that runs at call time (a function or lambda body). `<ctypes>` is any name the checker resolves to the module (Q10). Adjacent literals that the parser joins into the same constant are accepted too; they are the same value.
- On the handle: `.proc_listallpids`, `.proc_pidpath` and `.getfsstat`; their attributes such as `argtypes` and `restype`; `getattr(handle, '<one of the three>')`; plain aliases and the walrus form.
- `ctypes.get_errno()` and `ctypes.set_errno()`. Members of `ctypes` outside the deny set were already accepted before v2.x.

**What it refuses (rows and probe)**
- Every mutation the contract names (:379–385).
- `name=` instead of the positional literal, `**kw`, `*args`, a module constant instead of the literal, an f-string.
- `CDLL.__call__`, `cdll.LoadLibrary`, `ctypes.util`.
- The handle passed on, subscripted, returned, or used as a default argument; `__getitem__` and `_handle` on the handle.
- The open at import time or in a class body.
- One name bound to both libSystem and kernel32.
- `WinDLL` with the libSystem literal, `windll.libsystem`, and `from ctypes import CDLL as C`.

**Unchanged:** only one existing line changed (`if broken:` gained a condition). No existing row or message changed, all 23 architecture tests pass, and `import stat` is still refused.

**Mutants killed:** three checker mutants each make the self-test fail.

**Existing gaps:** F3 (dunder `__dict__` lookups), and a cast to the function-pointer type of an allowed function. Neither was introduced by this patch.

### e. Linux CI

| Item | Finding | Mark |
|---|---|---|
| `st_flags` or `os.chflags` on real files | None. `is_cloud_only` is tested with a fake `os.stat` that returns a SimpleNamespace (reader :94–102); everywhere else, "dataless" means the fake `is_cloud_only`. | confirmed by reading |
| `/var` → `/private/var` | pytest resolves `tmp_path`. The own-process path is `realpath` on both sides (darwinkit :97–99, :200–202). | confirmed by reading |
| APFS case-insensitivity | No test makes two names that differ only by case in one folder. The `WinePrefix` test (reader :469–483) is a hazard for the implementer, not a test defect: an implementation that stats the literal `wineprefix` passes on APFS and fails on ext4; the contract-faithful way (list `PlayOnMac`, compare lower-case) passes on both. AC-07's equal-count rule catches the shortcut. | confirmed by reading |
| real home and real `/Applications` | `_darwin_home` and `_darwin_application_dirs` are replaced (darwinkit :244–245). `outside_reads` audits listings and opens of the real places during `collect`. Stat-only existence checks are not audited, but `tools: none` (host_lines :145–150) would fail on the owner's Mac, which has `.colima` and `.docker`, if the real home were used. | confirmed by reading |
| real libproc and getfsstat | All three raw readers are replaced in every `collect`, host-lines and CLI case. | confirmed by reading |
| `os.uname` or `sys.platform` read at import time | Neither, in any test file. Both are set at call time through `monkeypatch` (darwinkit :235–247). `os.uname_result` exists on Linux. | confirmed by reading |
| file-system listing order | Every comparison of several entries is sorted, set-based, in contract order, or accepts either order. | confirmed by reading |
| other | The errno values used (EACCES, ENOMEM, EPERM, ESRCH, EIO) are equal on Linux and macOS. Names like `ProgramFiles(x86)` are legal POSIX environment variables. A global `sys.platform = "darwin"` touches only stdlib code that reads it at call time (the importlib FileFinder cache), which is harmless. | confirmed by reading |

### f. Test hygiene

- No skip, xfail or `.only` (grep: 0 hits).
- The red-flag patterns, applied by hand to the six new files: 0 hits.
- Fakes live only under `tests/`. No network: `vps.example` appears only as strings.
- Every symlink is made in a builder before `K.recording` starts:
  - `test_ac02_darwin_collect.py:399–420` and :439–441;
  - `test_ac02_darwin_evaluate.py:179–232` and :53–55.
- Results are deterministic.
- The one broad `except Exception` (cli :196) reports the failure; it does not swallow it.
- Reads of the real machine are limited to the running interpreter's metadata and binary, and to the `sys.path` listings that `find_spec` makes. The contract requires both. The one exception is F1's failure path.

## Not checked (and why)

- **A Linux run:** there is no Linux host here.
- **Satisfiability by execution:** no darwin implementation exists. Of the author's 24 behaviour mutants (§9), I executed only the symlink ones (mutant 21) through my own mutants; the rest I checked by reading.
- **Real libproc, getfsstat, the `struct statfs` layout and real dataless flags:** the contract puts these in fakes and unit tests.
- **AC-01 and AC-03:** the owner's L4 rounds.
- **The test author's scratch beyond hashing:** `prompt.md`, `run.json`, `base/` and `part*.patch` were not read.
- **`docs/handoff/ENV-002.md` and chat logs:** not read, as instructed.
- **The implementer's unit tests in `tests/unit/app/`:** out of scope.

## Blocks

None. No hook or permission rule refused any call in this session.
