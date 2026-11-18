# Review ENV-002 contract v2.4 round 5 (ENV-002 v2.4 draft, D-023)

- **Base:** review r4 at `ceb3d6a`, on contract v2.3.
- **Head:** `57843c3` on `chore/ENV-002-macos-research-host`; the tree is clean.
- **Reviewer:** one fresh-context Claude session, read-only. It did not write v2.4 or any earlier review.
- **Date:** 2026-11-18.
- **Scope:**
  - Closure check of the ten r4 findings, and new defects in the v2.4 edits.
  - This is the 5th contract-review round, the last one the caps allow (contract :615).

**Label: binding contract review.**
- The owner confirmed decision (ซ) on 2026-11-18 at 11:2x (contract :531, :593; PROGRESS.md under "Current task"). Under (ซ), fresh Claude sessions are the contract reviewers of v2.x.
- This review does not claim that the separation is secure.
- It is not an approval. Under :597, Claude records (จ) only after a review says "Ready … yes", and this review says no.

**Ready for the owner's approval: no.** Reasons:
1. No High finding is open.
2. **All ten r4 findings are closed**, judged against r4's own proposed changes and proofs of fix. r4 left two decisions to the owner (F50 and F51). The author answered both under the 11:2x answer; see "On the 11:2x reading" below.
3. **One Medium finding is open, new in this round: F57.**
   - The F50 closure trusts four things the research identity can change: git's index, git's configuration, the uv binary and the shell. AC-01's check that the code is the reviewed commit trusts the same four. No step checks them.
   - Example: someone edits envcheck, then runs `git update-index --assume-unchanged` on it. The edit survives every runbook step and every R1 start-up check.
   - That is a lasting wrong PASS that is not named. Meanwhile v2.4 tells the owner that this kind of hole is closed (:541).
   - The gap existed before v2.4. Closing it needs more steps, or a new residual that only the owner can accept (:595).
4. **Four new Low findings.**
   - F59 and F60 decide the expected results of locked tests. Fix them before the locked tests are written.
   - F58 is about the R1 start-up checks that F50 handed on, and the `.pth` window in row :498. Fix it before the AC-01 round records the step (4) value.
   - F61 is about what the owner reads. Fix it in the same pass.
5. **Budget:**
   - r5 is the last contract-review round within the caps (:615), and it cannot say "yes".
   - So :597 does not let Claude record (จ). The owner decides the next step (see "Questions for the owner").

**Findings open: 5 (0 High, 1 Medium, 4 Low).**

**On the 11:2x reading (task item 3).**
- **One rule.** The locked-checker patch now has one order and one gate:
  - The order: Claude applies the patch under D-006 and checks its SHA-256 and Git blob. A fresh session reviews the tests. Then commit, then red.
  - The diff is shown to the owner in chat.
  - The only blocking gate is the `owner-approved-control-change` label.
  - The same wording appears at :15 (Q6), :413 (Invariants), :520 (Plan step 2) and :598. The old v2.1 text at :559 is marked as replaced.
  - This matches the D-006 exception in the "Authority" section of AGENTS.md, and the label check in `.github/workflows/control-gate.yml`.
- **The rows that rest on Claude's reading are labelled.** The 11:2x table (:590–598) says which rows rest on Claude's reading of "มึงจัดการทั้งหมดให้เลยกูอนุญาติทั้งหมด", the owner's 11:2x message ("handle all of it for me, I permit all of it"):
  - (ฌ), at :594;
  - recording (จ), at :597, which notes that the answer said "อนุญาติ" ("permit") rather than "อนุมัติ" ("approve"), and that (จ) was not named;
  - the checker gate, at :598.
  - The owner can reverse these before merge (:597; DECISIONS:264).
- **Not a finding, and not a block.** This review does not count the remaining dependence on Claude's reading as a finding, and it does not block "ready".
- **What is left.**
  - Two lines still record as the owner's own answer what the table marks as Claude's reading (F61).
  - Whether the owner was told in chat, as handoff:618–624 says, cannot be checked from the repository.

**How to read the references:**
- "contract :NN" means `/Users/faztycoding/Documents/GitHub/Sochron1k/docs/contracts/ENV-002-research-host-separation.md` at `57843c3` (636 lines).
- "DECISIONS:NN" means `/Users/faztycoding/Documents/GitHub/Sochron1k/DECISIONS.md` at the same commit.
- "handoff:NN" means `/Users/faztycoding/Documents/GitHub/Sochron1k/docs/handoff/ENV-002.md` (657 lines).
- "Probe" means a read-only command run by this session on this Mac (arm64, uv 0.13.5, CPython 3.12.15). Bytecode writing was off wherever Python ran. `git status --short` was empty before and after every probe.

**How it was verified:**
- Read in full: the skill file, r4, and the contract at `57843c3`.
- Read the word-level diff of all 13 commits in `ceb3d6a..57843c3`, the DECISIONS and PROGRESS diffs, and D-023 (DECISIONS:259–277).
- The handoff's findings response (handoff:612–657) was opened only after a first view of each finding had been formed. It changed no status.

No URL was fetched.

## Re-check of r4 findings

| r4 ID | r4 Sev | Status | Commit | Evidence at `57843c3` |
|----|----|----|----|----|
| F49 | Medium | closed | `b06136c` | <ul><li>:418 runs the audit check "ใช้ `collect` ที่แทน `find_terminal_paths_darwin` ด้วยตัวปลอม" ("on `collect` with `find_terminal_paths_darwin` replaced by a fake").</li><li>:418 also states that the real home walk still lists `.colima`, and adds a case `<home>/.colima/x/terminal64.exe` on `find_terminal_paths_darwin` (FAIL).</li><li>:428 runs the `Library`/`.ssh` check "บน `find_terminal_paths_darwin` ที่เรียกตรงโดย `never_listed` = (`<home>/Library`, `<home>/.ssh`)" (on `find_terminal_paths_darwin` called directly, with `never_listed` given).</li><li>The home rule (:282–284) is unchanged.</li><li>With `find_terminal_paths_darwin` replaced, nothing else in `collect` lists `.colima`: `wine_prefixes` looks only at its three sources, `tools:` only checks existence, and `terminal_data` lists only appdata.</li></ul> |
| F50 | Medium | closed (option (a)) | `af09ee1` | <ul><li>The runbook (:472–477) adds the steps of r4's option (a): reinstall the interpreter (1); clean bytecode (2); run `git status --short --ignored --untracked-files=all` and paste the full output into the evidence (3); record a manifest (4); run with `PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1` (5).</li><li>:384, :401, :498 and :541 follow these steps.</li><li>Probes: `--reinstall` exists in uv 0.13.5.</li><li>Probe: on today's tree the step (3) command lists 327 ignored entries (`.mypy_cache` 257, `src` 44, `tests` 25, `scripts` 1). All are under `__pycache__/` or `.mypy_cache/`, and none is under `.venv`. Step (2) removes them all, so the filter prints nothing.</li><li>This closure gives rise to F57 and F58.</li></ul> |
| F36 | Low | closed | `99eec20` | The residual cell of :495, the row that cites the mount allow list, ends "(v2.4, r4 F36) volume ที่ mount ทับ path ของระบบใต้ `/System/Volumes/` นอก `Data` … ((ญ) ข้อ 15)" (a volume mounted over a system path under `/System/Volumes/` outside `Data`; residual 15). |
| F48 | Low | closed | `5ca200a` | <ul><li>:250–251 add "apps: unreadable (<path>, …)[; found: <ชื่อ>, …]" for an `/Applications` or `~/Applications` that exists but cannot be listed.</li><li>:247–248 give the reason of `wine: unreadable`: a `~/` path, then `: `, then the OSError text; a symlink gives `symlink`.</li><li>The example and the words "ข้อความของ OSError" ("the OSError text") disagree (F60).</li></ul> |
| F51 | Low | closed | `0d176bd`, `902864a` | <ul><li>One order and one gate at :15, :413, :520 and :598. :559 marks the v2.1 text as replaced.</li><li>:597 says how (จ) is recorded once a review says yes. It also says the 11:2x answer used "อนุญาติ" and did not name (จ).</li><li>:594 marks (ฌ) "ตีความจากคำตอบรวม" ("read into the blanket answer").</li><li>DECISIONS:264 and PROGRESS record the change.</li><li>:532 and :554 still read as the owner's own answer (F61).</li></ul> |
| F52 | Low | closed | `5ede9cb` | <ul><li>:198–200: "`wine_prefixes` ยก OSError = การค้นไม่ครบ (… `terminal_paths` None เฉพาะเมื่อไม่พบ path อื่นจากกฎใด ตามกฎของ r2 F30 …)". In English: an OSError from `wine_prefixes` is an incomplete search, and `terminal_paths` is None only when no other rule found a path.</li><li>:442 has both cases r4 proposed: UNKNOWN, and FAIL when `MetaTrader 5.app` is present.</li></ul> |
| F53 | Low | closed | `5ede9cb` (parts 1–3), `5ca200a` (part 4) | <ul><li>:178–180: part three of `classify_mounts` holds only allow-list UNKNOWNs; part four is None for an apfs `/` without MNT_LOCAL.</li><li>:183–184: the Wine-loader count and `process_names`.</li><li>:245–246: the source folders, their order, and the `~/` form.</li><li>:442 has one case for each part.</li><li>F53 has no commit of its own. The message of `5ede9cb` says "see the F53 commit", which does not exist; handoff:636 explains this.</li><li>The new `~/.wine` counting rule conflicts with case :440 (F60).</li></ul> |
| F54 | Low | closed | `27994aa` | <ul><li>:347–348: "ข้อยกเว้นนี้เปลี่ยนเฉพาะผลของ `sentinel`: ใต้ repo หรือ data dir ไฟล์นี้ยังทำให้ `excluded_period` เป็น UNKNOWN". In English: the exception changes only the `sentinel` result; under the repo or a data dir the file still makes `excluded_period` UNKNOWN.</li><li>:444 says the same.</li><li>Probe: no locked test contains an `.icloud` file.</li></ul> |
| F55 | Low | closed | `1ac7903` | <ul><li>:215–219: `collect` writes only its six keys, and `research_host_report` alone clears the summary and records reader, roots and token.</li><li>:221: `host_lines()` falls back to `reader_name()`.</li><li>:442: the follow-up case says "test ตั้ง platform เป็น darwin เอง" (the test sets the platform to darwin itself).</li><li>:234 drops the `; onedrive:` form.</li><li>The new rule does not say what happens when the recorded reader is not darwin (F59).</li></ul> |
| F56 | Low | closed | `4d4f8c9`, `af09ee1` | <ul><li>:401 corrects the R1 parenthesis.</li><li>:480 and :580 carry the narrowed mount list.</li><li>:551 points to Budget.</li><li>:569, :570, :581, :583 and :584 note the 11:2x answer.</li><li>:629 adds the 11:2x section to the reading list.</li><li>:633 is the v2.4 DoR line, and :4 is the v2.4 Status.</li><li>handoff:648–657 updates Budget and Next.</li></ul> |

**Totals: 10 closed, 0 closed in part, 0 open.** Four closures give rise to new findings:
- F50 leads to F57 and F58.
- F55 leads to F59.
- F48 and F53 lead to F60.
- F51 leads to F61.

## Findings (open and new)

| ID | Sev | Kind | File:line | Finding | Owner decision |
|----|-----|------|-----------|---------|----------------|
| F57 | Medium | confirmed (documented git behaviour and read-only probes; not executed) | contract :449, :472–477, :401 against :498, :541, :595 | The runbook and AC-01 trust git's index and config, the uv binary and the shell, which the research identity can change. An edited tracked file hidden by `git update-index --assume-unchanged` passes every step, persists, and is not named. v2.4 says this kind of hole is closed. | yes, if any route is named rather than closed |
| F58 | Low | confirmed (rule and read-only probes) | contract :401, :473, :476, :498 against :541 | Problems with R1's start-up checks from F50: the manifest changes with ordinary use; the checks run inside the process they check; nothing cleans before check (1); and row :498 narrows the accepted `.pth` window. | no |
| F59 | Low | confirmed (rule and a grep of the locked tests) | contract :215–226 against :224, :430, :442, :418 | `host_lines()` does not say whether to print the darwin-only lines when the recorded reader comes from another platform. This gives an order dependence that fails only on CI. | no |
| F60 | Low | confirmed (rule and a probe) | contract :246 against :440; :247–248 | `~/.wine` without `drive_c` conflicts with case :440, and the `wine: unreadable` reason text conflicts with `str(OSError)`. | no |
| F61 | Low | confirmed | contract :532, :554 against :594, :597; PROGRESS.md | Two contract lines, and PROGRESS, record as the owner's answer what the 11:2x table marks as Claude's reading. | no |

**Severity calls:**
- **F57 is Medium, not Low.**
  - Residual 7 covers code planted inside a short window.
  - F57's route needs no timing and lasts through every round and every R1 run.
  - So it is a wrong PASS that is not named, which is the Medium definition.
  - It is the same class r4 rated Medium in F50.
- **F58 is Low.**
  - Parts 1 and 3 fail closed: R1 refuses to run rather than passing.
  - Part 2 changes no outcome, because a `.pth` file in `.venv` already reaches the same result at R1 under accepted residual 7.
  - Part 4 misstates a residual but changes no result.
- **F59 and F60 are Low.**
  - For every reading, some correct implementation passes. Neither finding describes a test that no implementation can pass.
  - This is the class of r4 F53 and r4 F55 part 2.

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

### F57 · Medium · The runbook and AC-01 trust git's index and config, the uv binary and the shell; v2.4 says this kind of hole is closed

**Where:**
- contract :449 (AC-01 Given), :471–477 (runbook), :401 (R1 check (1));
- against :498 (threat row), :541 ((ญ) 7), :595.

**Evidence:**
- **What proves the code is the reviewed commit:**
  - The AC-01 Given (:449) requires "`git rev-parse --short HEAD` ตรงกับที่ Claude ให้ และ `git status --short` ไม่พิมพ์อะไร": HEAD equals the commit Claude gives, and `git status --short` prints nothing.
  - Step (3) (:475) extends this to ignored and untracked files.
  - R1's check (1) (:401) repeats step (3).
  - The `.venv` rebuild (:471), the interpreter reinstall (:473) and the CLI (:477) all run `uv`.
- **What v2.4 tells the owner:**
  - The runbook item is titled "โค้ดที่ git ไม่แสดงและการสร้าง `.venv` ใหม่ไม่ลบ" ("code that git does not show and that rebuilding `.venv` does not delete") (:472).
  - (ญ) 7 (:541) says: "ส่วนที่เคยอยู่นอกช่วงนี้ (bytecode ที่วางไว้นานแล้ว, interpreter ที่ถูกแก้) ถูกปิดด้วยขั้นตอนของ runbook และการตรวจของ R1 ไม่ใช่ความเสี่ยงที่รับเพิ่ม". In English: what used to lie outside the window (bytecode planted long ago, an edited interpreter) is closed by the runbook steps and R1's checks, and is not an extra accepted risk.
  - Row :498 names only a `.pth` file or bytecode planted inside the window.
- **Routes that no step sees:**
  - **Index flags.**
    - `git update-index --assume-unchanged <path>` (or `--skip-worktree`) tells git to treat the working-tree file as equal to the index.
    - A modified tracked file, such as `src/sochron/app/envcheck.py`, then appears in no form of `git status`, including step (3)'s form.
    - `git ls-files -v` shows such entries with a lowercase tag or `S`.
    - Probe: `git ls-files -v | grep -vc '^H '` gives 0 today.
  - **`core.fsmonitor`.**
    - Git asks the configured hook which files changed, and runs that hook on every `git status`.
    - Probe: it is unset today.
  - **The uv binary.**
    - `~/.local/bin/uv` is `-rwxr-xr-x faztycoding staff` (probe).
    - The account that agents and R1 run under can replace it.
  - **The shell.**
    - The steps run in the owner's zsh, whose start-up files the same account writes.
    - Probe: in this session's shell, `find` and `grep` are not binaries. They are shell functions from a snapshot file under `~/.claude/shell-snapshots/`.
    - The git, shasum, sort and xargs binaries themselves are root-owned system files (`/usr/bin/git` is Apple Git-157, 2.54.0).
  - A grep of the contract finds none of `assume`, `update-index`, `skip-worktree`, `fsmonitor`, `ls-files`, `.local/bin` or `zshrc`.
- **Not shown here:** whether `uv python install --reinstall` deletes files that are not part of the distribution.
  - An example is a planted `lib/python312.zip`, which sits before the stdlib in `sys.path` (r4's `-m site` probe).
  - uv's help says only "Reinstall the requested Python version".
  - Step (4) records whatever the folder holds.

**Impact:**
- **The attack.** A research-identity process edits envcheck so that it prints PASS. The edit can also print FAIL for the two control-round folders, as r4 F50 noted. The process then runs one `git update-index --assume-unchanged`.
- **What follows.**
  - Every runbook step passes, the AC-01 Given holds, and the evidence round reports PASS.
  - R1's check (1) also passes at every later run.
- **Why this is not residual 7.** Unlike residual 7, the attack needs no timing and lasts. It is a wrong PASS that is not named, and v2.4 tells the owner the hole is closed.
- **History.** The gap existed before v2.4. r4 F50 listed two ways to blind git (`.git/info/exclude`, `status.showUntrackedFiles`), and v2.4 closed only those two.

**Proposed change:**
- **Git.** In step (3) and in R1's check (1), add two commands that must print nothing:
  - `git ls-files -v | grep -v '^H '`
  - `git config --show-origin --get-regexp '^core\.fsmonitor$'`
  - Put both outputs in the evidence.
- **Interpreter.** Delete `~/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none` before installing, or cite a source saying that `--reinstall` replaces the whole folder.
- **uv binary and shell.** Do one of these:
  - close them with steps, for example run the steps in `zsh -f` with full tool paths such as `/usr/bin/git`, and reinstall uv from its official installer first; or
  - name them in (ญ) and row :498: "the runbook and R1 use uv, the shell and git's state as they are; a research-identity process that changes them can make every step print what it chooses (not detected)".

**Proof of fix:**
- Step (3) and R1's check (1) list the two git commands.
- Every other route is either closed by a named step, or named in both (ญ) and row :498.

**Owner decision:**
- **Yes, if any route is named rather than closed.** A residual added after 11:2x must be put to the owner again (:595).
- **No, if every route is closed with steps.**

### F58 · Low · R1's start-up checks from F50 cannot work as written, and row :498 narrows the accepted `.pth` window

**Where:** contract :401 (R1 checks (1)–(3)), :473 (step (1)), :476 (step (4)), :498, against :541.

**Evidence:**
1. **The manifest changes with ordinary use.**
   - Step (4) hashes every regular file under the interpreter folder (:476), and R1 must match that value at every run (:401, check (2)).
   - uv 0.13.5 offers `--compile-bytecode`, "Compile Python's standard library to bytecode after installation". So a default install leaves stdlib bytecode to be written at run time.
   - Probe: the stdlib holds 1,092 `.py` files and 162 `.pyc` files.
   - Probe: its `__pycache__` folder was modified at Nov 17 21:44, after the 20:37 install. The tree is writable by the owner's account.
   - CPython writes a missing `.pyc` next to its source whenever bytecode writing is on, which is the default. The AC-07 command on the Mac does not turn it off (:457).
   - So any later run that imports a stdlib module not yet cached changes the manifest, and R1 then refuses to run.
2. **The checks run inside the process they check.**
   - :401 places checks (1) and (2) in R1's launcher, "ก่อนเรียก `require_research_host`" (before `require_research_host` is called). It does not say they run before the Python process starts.
   - Start-up code runs before any in-process check: for example `src/sitecustomize.pyc` through `PYTHONPATH`, or an edited `encodings`. Such code can delete itself, or change what the check reads.
3. **Nothing cleans before check (1).**
   - R1 repeats step (3) but not step (2).
   - Any test run between two R1 runs leaves `__pycache__` folders in `src/` and `tests/` (today: 44 entries under `src/`).
   - So R1 refuses until someone cleans.
4. **Row :498 narrows the accepted `.pth` window.**
   - The row's residual now reads "ไฟล์ `.pth` หรือ bytecode ที่ถูกวางหลังขั้นตรวจก่อนรันและก่อนตัวตรวจทำงาน" ("a `.pth` file or bytecode planted after the pre-run check and before the checker runs").
   - But no pre-run step looks inside `.venv`: step (3) and R1's check (1) both exclude it.
   - So the `.pth` window starts at the last `.venv` rebuild, as (ญ) 7 itself says ("หลังสร้างใหม่และก่อนรัน", after the rebuild and before the run). For R1, the last rebuild is the AC-01 round.

**Impact:**
- Parts 1 and 3 fail closed: R1 refuses rather than passes.
- Part 2 changes no outcome today, because a `.pth` file in `.venv` reaches the same result at R1 under accepted residual 7.
- Part 4 misstates an accepted residual in the table the owner reads.
- No ENV-002 AC and no locked test changes. But the step (4) value recorded in the AC-01 round must be one that R1 can reproduce.

**Proposed change:**
- **Step (1).** Use `uv python install --reinstall --compile-bytecode 3.12.15`, or define a manifest that ordinary runs do not change, and say which.
- **:401.** Say that checks (1) and (2) run before the R1 Python process starts, using git, find and shasum rather than the checked interpreter. Also say whether R1 runs step (2) first.
- **:498.** Give the `.pth` file its own window, as (ญ) 7 does.

**Proof of fix:**
- Step (1) states the bytecode choice.
- :401 says where the checks run.
- Row :498 and (ญ) 7 state the same `.pth` window.

**Owner decision:** no.

**Fix before:** the AC-01 round (because of the step (4) value) and the SLICE-R1 contract. It is not needed before the locked tests.

### F59 · Low · `host_lines()` does not say whether to print the darwin-only lines when the recorded reader comes from another platform

**Where:** contract :215–226 and :236, against case :430, the F52 cases at :442, and :418. Locked tests `test_ac02_research_host_evaluate.py`, `test_ac05_require_research_host.py` and `tests/unit/app/*`.

**Evidence:**
1. **A direct `collect` after a non-darwin `research_host_report`.**
   - Since F55, `collect` writes only its six keys and never the reader (:215–217). A direct call therefore keeps the `reader:` of the previous `research_host_report` (:218).
   - :224 allows `host_lines()` tests on the real `collect` called directly. Two cases read that way:
     - case :430: "หลัง `collect` ที่มี mount `/Volumes/USB`: บรรทัด `mounts:` ของ `host_lines()` …" (after a `collect` with mount `/Volumes/USB`, the `mounts:` line of `host_lines()` …);
     - the F52 case: "บน `collect` …" (on `collect` …).
   - The text does not say whether the darwin-only lines (:236–252) print when the recorded reader is `none` or `win32`.
   - "reader อื่นได้แค่ `reader:` และ `roots:`" (:223: other readers get only `reader:` and `roots:`) can be read as "no".
   - Probe: three v1.9 locked test files call `research_host_report` or `main`, and no test sets `sys.platform`. Under v2.x they record `none` on Linux CI and `darwin` on this Mac.
2. **`main` when `default_roots` raises.**
   - On this path `research_host_report` is never called, so `_HOST_SUMMARY` still holds the previous call's lines.
   - :226 says "พิมพ์ `reader:` แล้วข้อความเดิมของ v1.9" (print `reader:`, then the v1.9 message). It does not say whether the value comes from `reader_name()` or from the stale summary.
   - Case :418 runs this path: `Bottles` cannot be listed, so the CLI gives UNKNOWN with exit 1.
   - This part existed before v2.4.

**Impact:**
- Suppose a locked test is written the way :224 allows, and the implementation decides by the recorded reader.
- That test passes on this Mac and fails on Linux CI, depending on test order. This is the class of r4 F55 part 2.
- No verdict changes.

**Proposed change:**
- **Part 1, one of:**
  - write "บรรทัดเฉพาะ darwin พิมพ์ตาม key ที่ `collect` เขียน ไม่ขึ้นกับ reader ที่บันทึก" (darwin-only lines print according to the keys `collect` wrote, regardless of the recorded reader); or
  - drop the parenthesis at :224, and run case :430 and the F52 cases through `research_host_report`.
- **Part 2:** at :226, say that the error path prints `reader: <reader_name()>` and nothing from `_HOST_SUMMARY`.

**Owner decision:** no. Fix before the locked tests are written.

### F60 · Low · Two forms of the `wine:` line leave an expected value open

**Where:** contract :246 against :440; :247–248.

**Evidence:**
1. **`~/.wine` without `drive_c`.**
   - :246 (new in v2.4) counts `~/.wine` as a prefix only "เมื่อมี `drive_c`" (when it has `drive_c`).
   - Case :440, "prefix ที่ไม่มี `drive_c` (PASS, `wine: 1 prefixes`)" (a prefix without `drive_c`), does not name the source.
   - A PlayOnMac or CrossOver prefix without `drive_c` gives 1.
   - `~/.wine` without `drive_c` gives `wine: 0 prefixes; looked at ~/.wine`.
2. **The reason text of `wine: unreadable`.**
   - :247 says "ข้อความของ OSError" (the OSError text), and the example is `[Errno 13] Permission denied`.
   - Probe: `str()` of an OSError raised by `os.scandir` is `[Errno 2] No such file or directory: '<full path>'`. It ends with the full path, which repeats the folder and includes the account name.
   - The example matches `[Errno <errno>] <strerror>`, not `str()`.

**Impact:** a locked test that checks the whole line, written on one reading, fails against an implementation written on the other. No verdict changes.

**Proposed change:**
- **At :440,** name the source, for example `Library/PlayOnMac/wineprefix/p1` without `drive_c`. Optionally add a case: `~/.wine` without `drive_c` gives `wine: 0 prefixes; looked at ~/.wine`.
- **At :247,** write "`[Errno <errno>] <strerror>` (ไม่ใช่ `str()` ของ OSError ซึ่งมี path เต็ม)", that is, not `str()` of the OSError, which contains the full path.

**Owner decision:** no. Fix before the locked tests are written.

### F61 · Low · Two contract lines still record as the owner's answer what the 11:2x table marks as Claude's reading

**Where:** contract :532, :554 against :594, :597; PROGRESS.md (the 11:2x entry under "Current task").

**Evidence:**
- **(ฌ).** :532 ends "**เจ้าของยืนยันแล้ว 2026-11-18 11:2x**" (the owner confirmed). But :594 says "ตีความจากคำตอบรวม: รายงานในแชทก่อน 11:2x ไม่ได้เอ่ยชื่อ (ฌ)" (read into the blanket answer; the chat report before 11:2x did not name (ฌ)).
- **(จ).** :554 states as fact that the 11:2x answer "ครอบ (จ)" (covers (จ)), and that "เจ้าของยังต้องอนุมัติ (จ) เอง" (the owner must still approve (จ) himself). But :597 says (จ) was not named, that the answer used "อนุญาติ" rather than "อนุมัติ", and that covering (จ) is Claude's reading.
- **PROGRESS.** The 11:2x entry in PROGRESS.md still says "ยืนยัน (ฌ)" ((ฌ) confirmed).
- r4's proposed change named only the table row (:572 then, :594 now), and that is done.

**Impact:** the owner reads two different answers to the same question. No result changes.

**Proposed change:**
- At :532 and in PROGRESS, add "(ตีความจากคำตอบรวม; ดูตารางคำตอบ 11:2x)", meaning "read into the blanket answer; see the 11:2x table".
- At :554, write "ซึ่ง Claude ตีความว่าครอบ (จ)" ("which Claude reads as covering (จ)"), and say how (จ) is approved under :597.

**Owner decision:** no. Fix in the same pass, before (จ) is recorded.

## AC status

No AC changed status. Every v2.x AC is UNKNOWN: no v2.x code or test exists, and `ceb3d6a..57843c3` changes documents only.

| AC | Status | Why |
|----|--------|-----|
| AC-01 (macOS) | UNKNOWN | <ul><li>The owner's L4 run is not done.</li><li>Step (3) was run read-only on today's tree; after step (2) it would print nothing.</li><li>A lasting forged PASS through git's index flags, the uv binary or the shell is possible and not named (F57).</li><li>R1 cannot reproduce the step (4) value after ordinary use (F58).</li></ul> |
| AC-02 | UNKNOWN | <ul><li>No v2.x tests exist.</li><li>F59 and F60 decide expected results.</li><li>A correct implementation can now pass the F49 cases as written.</li></ul> |
| AC-03 (macOS) | UNKNOWN | The owner's steps are not done. v2.4 does not change them. |
| AC-04 | UNKNOWN for v2.x | Unchanged. The v1.9 tests pass: 222 passed, with the architecture tests. |
| AC-05 | UNKNOWN for v2.x | <ul><li>By the text, the locked CLI tests still pass: `main` prints the host lines before `render`, and `host_lines()` falls back to `reader_name()`.</li><li>This rests on r4's reading of test_ac05:220–233, which was not re-read here.</li></ul> |
| AC-06 | UNKNOWN | The darwin checker patch does not exist yet. Its order and gate are now a single rule (F51 closed). |
| AC-07 | UNKNOWN | <ul><li>Not run for v2.x.</li><li>F59 describes a CI-only order dependence that a locked test could pick up.</li></ul> |

## Checked and correct (and how)

| Command or check | Result | Commit | Time |
|---|---|---|---|
| `git status --short` and `git rev-parse --short HEAD`, before and after every probe | Empty; `57843c3` | `57843c3` | 12:3x–12:54 +0700 |
| `git log --oneline ceb3d6a..57843c3`; `git diff --stat ceb3d6a..57843c3` | <ul><li>13 commits.</li><li>4 files: DECISIONS.md (1 line), PROGRESS.md (+2), the contract, the handoff; 122 insertions, 38 deletions.</li><li>No code, test, lockfile or locked path.</li></ul> | `57843c3` | 12:3x +0700 |
| `git show --word-diff=porcelain <commit> -- <contract>` for all 13 commits | Each "(v2.4, r4 Fn)" edit is in the commit that claims it. F53 has no commit of its own (see the re-check table). | — | 12:3x +0700 |
| `uv --version`; `uv python install --help` | <ul><li>uv 0.13.5.</li><li>`-r, --reinstall`: "Reinstall the requested Python version, if it's already installed".</li><li>`--compile-bytecode`: "Compile Python's standard library to bytecode after installation".</li></ul> | — | 12:3x +0700 |
| Step (3), read-only: `git status --short --ignored --untracked-files=all -- . ':(exclude).venv'`, then the step (3) filter over the entries step (2) would not remove | <ul><li>327 entries: `.mypy_cache` 257, `src` 44, `tests` 25, `scripts` 1.</li><li>None under `.venv`.</li><li>For what step (2) leaves, the filter prints nothing.</li></ul> | `57843c3` | 12:3x +0700 |
| `readlink .venv/bin/python`; `find <uv interpreter> -type l`; counts of `.py`, `.pyc` and `__pycache__` in its stdlib; `ls -ld` of the folders | <ul><li>The venv links to the real `bin/python3.12`.</li><li>Symlinks exist only in `bin/`, `lib/pkgconfig` and `share/man`, so step (4)'s `-type f` misses nothing the venv loads.</li><li>Stdlib: 1,092 `.py`, 162 `.pyc`, 22 `__pycache__` folders.</li><li>The stdlib `__pycache__` was modified Nov 17 21:44; the interpreter folder and `lib/python3.12` at 20:37.</li></ul> | — | 12:3x +0700 |
| `printf 'b\0a\0' \| sort -z` | `a b`: `sort -z` works on this macOS | — | 12:3x +0700 |
| `ls -l ~/.local/bin/uv`; `command -v` and `ls -lL` of git, shasum, sort, xargs; `type find grep` | <ul><li>uv is `-rwxr-xr-x faztycoding staff`.</li><li>git (`/usr/bin/git`, Apple Git-157, 2.54.0), shasum, sort and xargs are `root wheel`.</li><li>In this session's shell, `find` and `grep` are functions from `~/.claude/shell-snapshots/…`.</li></ul> | — | 12:4x +0700 |
| `git ls-files -v \| grep -vc '^H '`; `git config --show-origin --get-regexp` for `core.fsmonitor`, `core.excludesfile`, `status.showuntrackedfiles`, `core.hookspath`; `git replace -l` | 0; none set; none | `57843c3` | 12:4x +0700 |
| `grep` of `tests/` for `icloud`, `sys.platform`, and `research_host_report` or `main(` | <ul><li>No `.icloud`.</li><li>No test sets `sys.platform`.</li><li>Three v1.9 files call `research_host_report` or `main`.</li></ul> | `57843c3` | 12:4x +0700 |
| Contract grep for `assume`, `update-index`, `skip-worktree`, `fsmonitor`, `ls-files`, `zshrc`, `.local/bin`, `compile-bytecode`, `sitecustomize` | 0 hits each | `57843c3` | 12:4x +0700 |
| `.github/workflows/control-gate.yml`:1–40 | <ul><li>`pull_request_target`, judged by the base revision.</li><li>`CONTROL_CHANGE_APPROVED` comes from the label `owner-approved-control-change`.</li></ul> | `57843c3` | 12:4x +0700 |
| `bash scripts/controls/red-flags.sh main` | <ul><li>"Pattern groups with hits: 0".</li><li>The control files it lists are the seven v1.x locked test files.</li></ul> | `57843c3` | 12:43 +0700 |
| `PYTHONTZPATH="" PYTHONDONTWRITEBYTECODE=1 uv run --offline --no-sync pytest tests/acceptance/ENV-002 tests/architecture -q -p no:cacheprovider` | <ul><li>222 passed in 1.88 s (v1.9 code).</li><li>The tree is still clean.</li></ul> | `57843c3` | 12:43 +0700 |
| `python -I -c` calling `os.scandir` on a missing path | <ul><li>`str(e)` is "[Errno 2] No such file or directory: '<path>'".</li><li>`strerror` has no path.</li></ul> | — | 12:5x +0700 |

**What was read:**
- **In full:** the skill file, r4, and the contract at `57843c3`.
- **In part:**
  - the per-commit diffs of the contract;
  - the DECISIONS and PROGRESS diffs;
  - D-023 (DECISIONS:259–277);
  - handoff:590–657, opened after the first view of each finding;
  - `.gitignore`;
  - `control-gate.yml`:1–40.

**What was compared:**
- Every r4 proposed change, against the v2.4 text.
- Every statement of the locked-checker order: :15, :413, :506, :520, :559, :598.
- Every record of (ฌ) and (จ): :532, :554, :594, :597, and PROGRESS.
- The `host_lines()` rules (:212–226), against every case that checks a host line: :418, :426, :430, :442, :446, :449.
- The new cases for F49 and F52–F55, against the rules they test.

## Not checked (and why)

- **No v2.x code or tests exist.** Every judgement is made on the text, against today's code and the locked tests.
- **F57 was not demonstrated.**
  - Setting an index flag or a config value writes to `.git`, which is outside a read-only review.
  - The finding rests on git's documented behaviour for `--assume-unchanged`, `--skip-worktree` and `core.fsmonitor`, and on the probes above.
- **Per-file times of the stdlib bytecode.**
  - `find … -exec stat …` was blocked by `.claude/hooks/guard-bash.mjs` ("find would change $L … ask the owner"). It was not retried another way.
  - Part 1 of F58 rests on the folder times, the file counts and uv's `--compile-bytecode` help text.
- **uv's reinstall and cache behaviour.** Three questions were not checked, because each needs a download or a reinstall:
  - whether `--reinstall` removes files that are not part of the distribution;
  - whether `--compile-bytecode` stops all later stdlib writes;
  - whether `uv sync --locked` re-checks cached wheels against `uv.lock`.
- **`docs/proposals/` is not on this Mac yet.**
  - Step (3) was not run with that folder present.
  - The `.patch` files it is expected to hold do not match the step (3) filter.
- **The owner's chat** (the 11:2x answer and the report after r4) is not in the repository.
- **Not run:** the full suite, `check-locked-paths.mjs`, `test-controls.mjs` and mypy. The diff since r4 changes documents only.
- **Not read:** SPEC.md, docs/architecture.md, test_imports.py, the handoff before :590, and envkit beyond the `check_report` and `_under` signatures.
- **Private folders.**
  - None was listed, and envcheck was not run against the real home.
  - Outside the repository, this session looked only at:
    - `~/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none`: file counts, two folder times, symlinks;
    - `~/.local/bin/uv`: `ls -l`;
    - the paths of system tools.
- **Not touched:** MT5, Wine, VMs, containers, the VPS, the broker, the old Windows PC, the Keychain and `.env`.
- **One scratch file.**
  - One probe saved its own output to a session scratch file outside the repository, so it could be counted: `/private/tmp/claude-501/-Users-faztycoding-Documents-GitHub-Sochron1k/38a03acd-6822-4cac-ae23-d960d6191884/scratchpad/step3.txt`.
  - Nothing in the repository or the home folder was created or changed.

## Questions for the owner

1. **F57: the tools the runbook trusts.**
   - The remaining routes are git's index flags, git's fsmonitor setting, the uv binary in `~/.local/bin`, and the shell's start-up files.
   - Should they be closed with more runbook steps, or named as a new residual 16 that you accept?
     - Closing means two git checks that must print nothing, running the steps in `zsh -f` with full tool paths, and reinstalling uv first.
     - Naming means accepting that the runbook and R1 trust those tools as they are.
   - The two git checks are cheap and can be added either way.
   - A residual added after 11:2x needs your answer (:595).
2. **What happens after this round.**
   - r5 was the last contract review within the caps (:615), and it says no, so under :597 Claude cannot record (จ). Choose one:
     - (a) allow one more closure check of F57–F61, which would be fresh session 6 of 12;
     - (b) read the fixes and approve v2.x and D-023 yourself;
     - (c) something else.

Ready for the owner's approval (ENV-002 v2.4): no (0 High; 1 Medium: F57 needs more runbook steps or a residual only you can accept; all ten r4 findings are closed; fix Low F59 and F60 before the locked tests are written, F58 before the AC-01 round, and F61 in the same pass; r5 was the last round within the caps, so the next step is yours)
Ready for owner decision (D-023): no (no finding is against D-023's own text, and option 1 now states how acceptance is recorded (DECISIONS:264); but its header ties acceptance to contract v2.x, which is not ready)
Findings open: 5 (0 High · 1 Medium: F57 · 4 Low: F58, F59, F60, F61)
