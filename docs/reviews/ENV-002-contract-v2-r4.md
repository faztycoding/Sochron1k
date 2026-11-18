# Review ENV-002 contract v2.3 round 4 (ENV-002 v2.3 draft, D-023)

- **Base:** review r3 at `75948ff`, on contract v2.2.
- **Head:** `4f3c5cc` on `chore/ENV-002-macos-research-host`.
- **Reviewers, all read-only:**
  - Lens A, a fresh-context Claude session: closure of the 14 r3 findings, and the F25 redesign against the locked tests.
  - Lens B, a fresh-context Claude session: the whole document, read as test author, owner and attacker.
  - This session, which consolidated both lenses and ran the refutation pass.
- **Date:** 2026-11-18.

**Label: binding contract review.**
- The owner confirmed decision (ซ) on 2026-11-18 at 11:2x (contract :509, :571; PROGRESS.md:5). Under (ซ), fresh Claude sessions are the contract reviewers of v2.x.
- F51 does not dispute that confirmation, because (ซ) was one of the four questions put to him (:566).
- The session that wrote v2.3 did not review it.
- This review does not claim that the separation is secure.
- It is not an approval. Under contract :575, Claude records (จ) only after a review says "Ready … yes", and this review says no.

**Ready for the owner's approval: no.** Reasons:
1. No High finding is open.
2. Two Medium findings are open, both new in this round:
   - **F49:** the `.colima` case (:402) says the audit hook sees no `os.scandir` under a folder that the home walk (:267) must list. This is text the locked tests will be written from. The case dates from v2.2, and r3 missed it.
   - **F50:** two kinds of planted code load before the reviewed source: ignored bytecode in the repo, and edits to the uv-managed interpreter. Both survive the `.venv` rebuild, and `git status --short` shows neither. A wrong PASS is possible, and (ญ) names only `.pth`. The owner must choose a fix.
3. Of the 14 r3 findings, 12 are closed (F25 included) and 2 are closed in part:
   - F36: its closing commit added residual 15 without a threat-table row.
   - F48: `apps:` has no form for an app folder that cannot be listed, and `wine: unreadable` lists no reasons.
4. Six new findings are Low (F51–F56). F51 needs the owner's answer before any review can say "yes":
   - Under :575, a "yes" leads Claude to record (จ).
   - Approving (จ) now would approve two contradictory gates for the locked-checker diff.
5. Five Low findings decide a test input or an expected result. Fix them before the locked tests are written: F48, F52, F53, F54, F55. F36 and F56 concern what the owner reads; fix them in the same pass.
6. **Budget:** :593 allows at most 5 contract-review rounds, and r4 is the 4th. After the owner answers F50 and F51 and the text is edited, a closure check of the ten open IDs is enough. It would be the last round the budget allows.

**Findings open: 10 (0 High, 2 Medium, 8 Low).**

**Refutation pass:** lens A had 6 entries and lens B had 8. Of the 14, 11 are confirmed, 3 confirmed in part, and 0 refuted. The severities below are the consolidated ones:
- The `.colima` case is Medium; lens A said Low.
- The approval-gate record is Low with an owner decision; lens B said Medium.

**How to read the references:**
- "contract :NN" is `/Users/faztycoding/Documents/GitHub/Sochron1k/docs/contracts/ENV-002-research-host-separation.md` at `4f3c5cc` (612 lines).
- "DECISIONS:NN" is `/Users/faztycoding/Documents/GitHub/Sochron1k/DECISIONS.md` at the same commit.
- "handoff:NN" is `docs/handoff/ENV-002.md`.
- "envkit:NN", "test_ac02:NN" and "test_ac05:NN" are files in `tests/acceptance/ENV-002/`.
- "A-Fn" and "B-Fn" are the entries of lens A and lens B. Both lenses numbered from F49, so their IDs collide; the IDs in this file replace both sets.
- "Probe" is a read-only command run by this session on this Mac (arm64, CPython 3.12.15, uv 0.13.5), with bytecode writing off. `git status --short` was empty before and after every probe.

**How it was verified:**
- This session read in full: the skill file, r3, the contract at `4f3c5cc`, and both lens files. It also read D-023 (DECISIONS:259–277).
- It re-opened every line quoted in each lens entry and in the r3 re-check table. All quotes matched.

**Corrections to the lens material:**
- **F36 and F48 of r3 are closed in part, not closed (lens A).** Their closing commits claim "the same residuals" (`7a1c6ea`) and "every form" (`4eb3147`). Neither claim holds.
- **The `.colima` case is Medium, not Low (lens A).** Lens A's own impact statement, "the test fails against a correct implementation", is the example given in the Medium definition.
- **The approval-gate record is Low, not Medium (lens B).** It changes no verdict, test result or AC. The owner decision attached to it does not raise its severity.
- **Lens B's :412 part holds only for a test over the real `collect`.** The case names "การค้น home", so a test that calls `find_terminal_paths_darwin` directly passes.
- **Lens B's proof of fix for F50 fails today.** It expects `git status --short --ignored` to print only `!! .venv/`. Today it also lists `.mypy_cache/` and 31 `__pycache__/` folders, and `docs/proposals/` is ignored as well (`.gitignore`:10).
- **Whether (ฌ) was put to the owner cannot be checked.** The chat is not in the repository.

No URL was fetched.

## Re-check of r3 findings

| r3 ID | r3 Sev | Status | Commit | Evidence at `4f3c5cc` |
|----|----|----|----|----|
| F25 | Medium | closed | `4eb3147` | :206 `_HOST_SUMMARY` "ค่าตั้งต้นตอน import คือว่าง"; :207 `research_host_report` clears it and records reader, roots and token before `collect`; :212 "ก่อนมีการเรียกใดเลย คืนแค่ `reader:`"; :192 names the source of `wine:`; :169–188 widen the return values; :426 states the follow-up case. The locked fake `collect` takes one argument (test_ac05:72), and the CLI tests read only the exit code, the last line, the item names and the token (test_ac05:220–233). The new text gives rise to F52 and F55. |
| F28 | Low | closed | `dfe8a03` | :301–302 keep the v1.9 MetaQuotes prune and give the reason; :422 is the case. This agrees with test_ac02 `_metaquotes_in_a_data_dir`, which sets `metaquotes_exists` True. |
| F30 | Low | closed | `6c72662` | :351 "(`terminal_paths` None ตามกฎของ r2 F30 → UNKNOWN ของ terminal_install; v2.3, r3 F30)"; :158–159 scope "เสมอ". The class reappears in new text at :194 (F52). |
| F32 | Low (q) | closed | `c931921` | :317–319 narrow the list; :414 has cases at `/System/Volumes/Data/Users/x/mnt` (UNKNOWN) and `/System/Volumes/Preboot` (PASS). Probe: `mount` shows 12 entries, all allowed. The runbook line :458 was not updated (F56). |
| F33 | Low | closed | `ed8c933` | :272–273 state the strict component rule; :279–280 point the Wine-loader rule to it; :406 has a case for each reading. One loader count is undefined (F53). |
| F36 | Low | **partly (Low)** | `7a1c6ea` | Items 13 and 14 were added (:525–527); the Photos Library is in item 5 (:516); row :466 has the vault path; :607 has D-023; :529 and :593 mark the numbers. But the same commit added item 15 (:528), and no row in :464–477 mentions `/System/Volumes`. |
| F41 | Low | closed | `39d7e99` | :563 "ขอบเขตคือบรรทัด `roots:` เท่านั้น … เจ้าของปิดบังชื่อบัญชีก่อน commit"; (d2) at :436 agrees. |
| F42 | Low | closed | `c746c5b` | :287–289 and :45 predict `tools: .colima, .docker`. Probe: those two paths exist and the other five do not. |
| F43 | Low | closed | `648a314` | :249–251 name `wineprefix`, `Bottles` and the level-0 `Program Files*` entries; :424 has the symlink cases. |
| F44 | Low | closed | `ff56184` | :305 gives `MNT_LOCAL` `0x00001000`. Probe: the SDK's `sys/mount.h`:222 agrees. |
| F45 | Low | closed | `eeb80b4` | :418 states the baseline mounts and adds the `/home` case (UNKNOWN). |
| F46 | Low | closed | `c79dabd` | :436 (d2) pins the run to `c97aac6` and records `git rev-parse --short HEAD`. Probe: `c97aac6`'s envcheck has no `reader:` line and no `host_lines`, and the commit is in both ENV-002 branches. |
| F47 | Low | closed | `b720ddb` | :434 and :437 read "เลิกใช้เมื่อ v2.x อนุมัติ"; :598 reads "หรือ v2.x"; :545 and :547 carry notes; :556 adds `.local/share/containers`; DECISIONS:259 cites `-r2.md`. New text of the same class is F56. |
| F48 | Low | **partly (Low)** | `4eb3147` | Every form r3 listed is now at :218–237. But :218 claims "ทุกรูปที่เกิดได้", and `apps:` (:236) has no form for the state in case :426 ("`/Applications` มีอยู่แต่ list ไม่ได้"). `wine: unreadable (<เหตุ>)` (:234) lists no reasons. |

**Totals: 12 closed, 2 closed in part, 0 open.**

## Findings (open and new)

| ID | Sev | Kind | File:line | Finding | Owner decision | Sources |
|----|-----|------|-----------|---------|----------------|---------|
| F49 | Medium | confirmed | contract :402 against :267–269, :195, :215, :238, :200–201; :412 against :291–292; envkit:298–299, :348 | The `.colima` case says the audit hook sees no `os.scandir` under a folder the home walk must list. A locked test written that way fails every correct implementation. | no | A-F51 + B-F49 |
| F50 | Medium | confirmed (rule and read-only probe; not executed) | contract :476, :519, :433, :455, :385; `.gitignore`:19–20 | Ignored bytecode in the repo, or edits to the uv interpreter, load before the reviewed source. Both survive the `.venv` rebuild and are hidden from `git status --short`. Only `.pth` is a named residual. | yes | B-F51 |
| F36 | Low | confirmed | contract :528 against :464–477 | Residual 15, added by the closing commit `7a1c6ea`, has no threat-table row. | no | r3 F36; parts of A-F53 and B-F52 |
| F48 | Low | confirmed | contract :218, :236, :234 against :426, :270–271 | `apps:` has no form for an app folder that exists but cannot be listed; `wine: unreadable` lists no reasons. | no | r3 F48; A-F50 part 5 |
| F51 | Low | confirmed; the (ฌ) part is a question | contract :576, :575, :572, :566 against :15, :397, :498, :506, :537; DECISIONS:264 | The locked-checker diff has two gates and three orders. (จ) is booked as covered by an answer to four other questions. | yes | A-F54 + B-F50 |
| F52 | Low | confirmed | contract :193–194 against :156–159, :402, :424 | When `wine_prefixes` raises inside `collect`, `terminal_paths` becomes None against the F30 rule, and no case covers it. | no | A-F49 + B-F54 |
| F53 | Low | confirmed | contract :176–179, :234, :247 against :406, :414, :420, :424, :426 | Four listed inputs leave one returned element or one part of a line undefined. | no | A-F50 parts 1–4 |
| F54 | Low | confirmed | contract :331–332 against :428; envkit:367–395 | For `.<sentinel name>.icloud` under a data dir, the result of `excluded_period` is not stated. | no | B-F55 |
| F55 | Low | confirmed; part 1 is a question | contract :209–210, :225, :426 against :207, :211, :213–214; test_ac05:72 | Three inputs of `host_lines()` are implicit: direct `collect` calls, the platform of the follow-up case, and the source of `; onedrive:`. | no | A-F52 + B-F56 |
| F56 | Low | confirmed | contract :385, :458, :558, :4, :529, :547–:548, :559, :561–:562, :607, :609; handoff:592–598 | Text superseded by v2.3 or by `4f3c5cc` still reads as current. | no | A-F53 + B-F52 + B-F53 |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

### F49 · Medium · The `.colima` case asks for an audit result that the home walk cannot give

**Where:** contract :402 against :267–269, :195, :215, :238, :200–201, :286. Also :412 against :291–292, :241. envkit:298–299, :348.

**Refutation:** the :402 part is confirmed. Lens B's :412 part is confirmed in part.

**Evidence:**
- **The case.** :402 reads "(v2.2, r2 F9) โฟลเดอร์ `.colima` ระดับ 0 ของ home (verdict ไม่เปลี่ยน, `tools: .colima`, และ audit hook ไม่เห็น `os.scandir` ใต้โฟลเดอร์นั้น)".
- **`tools:` exists only after a real `collect`.**
  - :238: "ใน `collect` ที่ถูกเรียกจริง บรรทัด `skipped:`, `apps:`, `tools:` มาจากการค้นของรอบนั้น · เมื่อ `collect` ถูกแทน สามบรรทัดนี้ไม่ถูกพิมพ์".
  - :215 routes `host_lines()` tests through `research_host_report`, `main`, or the real `collect`.
  - :200–201: the collect-level macOS cases "เรียก `collect` จริง … และแทนตัวอ่านดิบ".
- **The real `collect` runs the home walk.**
  - :267–268: "`terminal64.exe` ใต้ home ระดับ 0–3 (ข้าม .git, .venv, node_modules และทุกรายการที่ตรงกฎของ terminal_data · … ไม่เข้า `~/Library` ทั้งโฟลเดอร์ และไม่เข้า `~/.ssh`".
  - `.colima` is skipped neither there nor in `never_listed` (:195).
  - To search levels 1–3 under `.colima`, the walk must call `os.scandir` on `<home>/.colima`.
  - The "ดูการมีอยู่เท่านั้น ไม่ list ข้างใน" rule at :286 governs only the `tools:` line.
- **In the locked kit, "ใต้" includes the folder itself.** envkit:298–299 defines `_under(path, root)` as `path == root or path.startswith(root + sep)`. envkit:348 uses it for the existing "not listed under" check.
- **The conflict is not new.** The case and the `collect`-sourced summary were both in v2.2 (`e7cbc38` :362 and :190–194), and r3 did not raise it. v2.3 :215 and :238 now state the routing explicitly.
- **Lens B's :412 part.** :412 reads "การค้น home ไม่ list `Library` และ `.ssh` (audit hook ไม่เห็น `os.scandir` ใต้สองโฟลเดอร์นั้น)".
  - Over a real `collect` with default-shaped roots, `terminal_data` lists `<home>/Library/Application Support` (:291–292; appdata from :241), so a test over `collect` fails.
  - The case names "การค้น home", so a test that calls `find_terminal_paths_darwin` directly passes. Confirmed in part.

**Impact:**
- A locked test written as :402 reads, with envkit's own `_under` idiom, fails against every implementation that follows :267. Undoing it needs an owner-approved patch to a locked test. r3 rated this class Medium in F25.
- The other way to get a green test is to skip `.colima`, or all seven tool paths, in the home walk. Nobody has decided that. Lens B's example:
  - `~/.wine/drive_c/MT5/terminal64.exe` is at home level 3 and outside `Program Files*`.
  - With `.wine` skipped, it gives PASS, and that is not a named residual.

**Proposed change:**
- At :402, write: "(… `tools: .colima`; การตรวจ audit ใช้ `collect` ที่แทน `find_terminal_paths_darwin` ด้วยตัวปลอม: audit hook ไม่เห็น `os.scandir` ของ `.colima` หรือใต้มัน · การค้น home ตาม :267 ยัง list `.colima` ตามปกติ)". Alternatively, drop the audit clause.
- At :412, write: "บน `find_terminal_paths_darwin` โดย `never_listed` = (`<home>/Library`, `<home>/.ssh`)".

**Proof of fix:** the case names the function it replaces, and :267 is unchanged.

**Owner decision:** no. It becomes yes only if the owner wants the tool folders skipped by the home walk, which would then need a new residual.

### F50 · Medium · Planted bytecode or an edited interpreter is invisible to the `git status` and `.venv` checks; only `.pth` is named

**Where:** contract :476, :519 ((ญ) 7), :433 (AC-01 Given), :455 (runbook), :385 (R1 start-up). Also `.gitignore`:19–20.

**Refutation:** confirmed by rule and by read-only probes. Not executed, because creating a file is outside a read-only review.

**Evidence:**
- **The threat row defends only part of its class.**
  - :476 reads "library หรือโค้ดที่ถูกวางให้ตัวตรวจโหลด | ตัวแปร `DYLD_*`, ไฟล์ library ใน working directory, ไฟล์ `.pth` ใน `.venv` | … สร้าง `.venv` ใหม่ก่อนรอบหลักฐาน | ไฟล์ `.pth` ที่ถูกวางหลังสร้าง `.venv` ใหม่และก่อนรัน ตรวจไม่เจอ (เหมือน v1.9)".
  - (ญ) 7 (:519) names only `.pth`.
  - A grep of the contract finds no residual that mentions `pyc`, `__pycache__`, bytecode, `sitecustomize` or the uv interpreter. The only hit, :38, names the interpreter as a symlink target.
- **Git is the only integrity check of the code.**
  - The AC-01 Given (:433) requires "`git rev-parse --short HEAD` ตรงกับที่ Claude ให้ และ `git status --short` ไม่พิมพ์อะไร".
  - `git status --short` does not list ignored files.
- **Git ignores bytecode.**
  - `.gitignore`:19 is `__pycache__/` and :20 is `*.py[cod]`.
  - Probe: `git check-ignore -v` reports all five hypothetical paths as ignored: `src/sochron/app/__pycache__/envcheck.cpython-312.pyc`, `json.pyc`, `src/json.pyc`, `src/sitecustomize.pyc` and `__pycache__/json.cpython-312.pyc`.
- **The repo root and `src` come before the stdlib.** Probe: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src uv run --offline --no-sync python -m site`, which is the CLI's form, prints sys.path in this order:
  - the repo root;
  - `<repo>/src`;
  - the uv interpreter's `lib/python312.zip`, `lib/python3.12` and `lib-dynload`;
  - `<repo>/.venv/lib/python3.12/site-packages`.
- **Bytecode is loaded.** Probe: `importlib.machinery.BYTECODE_SUFFIXES` is `['.pyc']`, `_imp.is_frozen("json")` is False, and `os` is frozen. Under CPython's import system:
  - a sourceless `json.pyc` in the repo root or in `src/` is imported for envcheck's `import json`;
  - a `__pycache__/envcheck.cpython-312.pyc` whose header carries the source's mtime and size is used instead of the source;
  - `src/sitecustomize.pyc` is imported at start-up through `PYTHONPATH`.
- **The interpreter is outside the rebuild.**
  - `.venv/pyvenv.cfg` has `home = …/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/bin`.
  - That interpreter's `lib/python3.12` and `json/` are `drwxr-xr-x faztycoding staff`.
  - `uv sync --locked` (:455) recreates `.venv` on the same interpreter and does not reinstall it.
- **Git's view can also be blinded.** `.git/info/exclude` and `status.showUntrackedFiles=no` hide even an untracked source file from `git status --short`. Probe: both are empty or unset today.

**Impact:**
- A research-identity process, whether an agent or research code, can plant such a file. Envcheck, R1's in-process gate (:385) and the host lines that R1 compares would then report whatever the planted code chooses.
- The planted code can report FAIL for the two control-round folders, so the control round does not expose it.
- This is the class that :476 names, with a defence that does not reach it, and (ญ) does not name it. A wrong PASS is possible and unnamed, which is Medium.

**Proposed change (one of):**
- **(a) Close it.** Change the runbook (:455), the AC-01 Given (:433) and R1's start-up text (:385):
  - after the `.venv` rebuild, delete every `__pycache__`, `.mypy_cache` and `*.pyc` outside `.venv`;
  - require `git status --short --ignored --untracked-files=all` to list only the expected ignored entries: `.venv/`, plus `docs/proposals/` once it is on this Mac;
  - run with `PYTHONSAFEPATH=1`. This drops the repo root from the path but not `src/`, so the cleaning step is still needed;
  - reinstall or verify the uv-managed interpreter. This needs the network; confirm the flag in this uv's `--help`.
- **(b) Name it.**
  - Extend (ญ) 7 and the residual cell of :476 to "โค้ดที่ git ไม่แสดงและการสร้าง `.venv` ใหม่ไม่ลบ (bytecode ที่ถูก ignore, ไฟล์ของ interpreter ของ uv) ตรวจไม่เจอ".
  - It is added after 11:2x, so the owner must accept it anew (:573).

**Proof of fix:**
- For (a): the AC-01 evidence contains the ignored-files listing.
- For (b): the residual appears in (ญ) and in row :476.

**Owner decision:** yes, choose (a) or (b).

### F36 · Low · (r3, closed in part) Residual 15 has no threat-table row

**Where:** contract :528 against :464–477.

**Evidence:**
- `7a1c6ea` closed r3 F36 under the message "decision (ญ) and the threat table list the same residuals".
- The same commit added (ญ) 15 (:528): "volume ที่ mount ทับ path ของระบบใต้ `/System/Volumes/` นอก `Data` … ตรวจไม่เจอ".
- No row in :464–477 mentions `/System/Volumes`. Row :473 cites the mount allow list as a defence but not this residual.

**Impact:** one accepted residual is missing from the table that the owner reads. No result changes. Item 15 was among the 15 residuals accepted at 11:2x.

**Proposed change:** add item 15 to the residual cell of :473, or add a mount row.

**Owner decision:** no.

### F48 · Low · (r3, closed in part) Two host-line forms are still missing

**Where:** contract :218, :236, :234 against :426 and :270–271.

**Evidence:**
- **The claim.** :218 says the forms are "ทุกรูปที่เกิดได้".
- **`apps:` has no form for an unlistable folder.**
  - The only form is `apps: <ชื่อแอปที่ตรงรายการ, … หรือ none>` (:236).
  - Case :426 has "`/Applications` มีอยู่แต่ list ไม่ได้ (UNKNOWN ของ `terminal_install`)", and :270–271 make that an incomplete search.
  - The line for that state is not given; `none` would claim a search that did not happen.
- **`wine: unreadable` has no reasons.** `wine: unreadable (<เหตุ>)` (:234, :194) lists no reason texts, unlike `processes:` and `mounts:`.

**Impact:** a test that asserts the whole line for these states must guess. No verdict changes.

**Proposed change:** add one of `apps: unreadable (<path>)` or an explicit rule for that state, and the reason forms of `wine: unreadable` (for example the OSError text with its errno).

**Owner decision:** no.

### F51 · Low · Two gates for the locked-checker diff, and a contract approval booked from an answer to other questions

**Where:**
- contract :576, :575, :572 and :510, :566;
- against :15, :397, :498, :506, :532, :537;
- DECISIONS:264 and PROGRESS.md:5.

**Refutation:** confirmed in part.
- The gate contradiction and the (จ) record are confirmed.
- The (ฌ) part is a question, because the chat is not in the repository.
- Lens B's Medium is not upheld.

**Evidence:**
- **What was asked.** :566 lists four questions: round 4, (ซ), the 15 residuals of (ญ), and the budget. The answer was "มึงจัดการทั้งหมดให้เลยกูอนุญาติทั้งหมด".
- **What the record books beyond those four:**
  - :576: "diff ของผู้เขียน tests ที่แก้ตัวตรวจ ctypes ที่ล็อก (Invariants) | อยู่ในการอนุญาตนี้: Claude apply ตาม D-006 หลังผู้ตรวจ tests ว่าพร้อม".
  - :575: "(จ) อนุมัติ contract และรับ D-023 | อยู่ในการอนุญาตนี้ แต่ Claude **บันทึกการอนุมัติก็ต่อเมื่อ contract review รอบใดรอบหนึ่งว่า "Ready for the owner's approval: yes"**".
  - :572 and :510 book (ฌ) as "เจ้าของยืนยัน". (ฌ) is not among the four questions at :566, although r3's question 1 had bundled it with (ซ).
- **What the contract still says, unchanged:**
  - :15: "เจ้าของอนุมัติ diff ก่อน apply (หัวข้อ Invariants)".
  - :397: "ผู้เขียน tests ระบุทุกฟังก์ชันและค่าคงที่ที่แก้พร้อม diff ใน handoff ให้เจ้าของอนุมัติก่อน apply".
  - :537: "เจ้าของยังอนุมัติ diff ของผู้เขียน tests ก่อน apply".
  - (จ) at :506 approves the Invariants exception.
  - :498 gives a third order: "→ Claude apply ตาม D-006 และตรวจ hash → review ของ tests → red". Here the patch is applied before the tests review; :576 puts the tests review first.
  - DECISIONS:264: "เจ้าของยืนยันตอนรับ D-023".
  - PROGRESS.md:5 lists (จ) but not the checker diff.
- **What still protects the merge.** The label gate exists (`.github/workflows/control-gate.yml`:38), so nothing merges unseen.
- **Precedent:**
  - Delegated approvals of this High contract followed owner messages that used "อนุมัติ" (Status :4).
  - "กูอนุญาติ" served as approval authority for CORE-002, a Standard task (`docs/contracts/CORE-002-costs.md`:4).

**Impact:**
- The test author who follows :397 waits for the owner. Claude, following :576, applies the patch.
- What moves is the point at which the owner first sees a change to a locked control in a High task. Under :576 that point is the PR label, inside a branch that already carries seven locked v1.x test files awaiting the same label (red-flag scan).
- Under :575, any review that says "yes" leads to (จ) being recorded, and approving (จ) now would approve both gate texts. So this needs the owner's answer before any review can say "yes".
- No verdict, test result or AC changes, so the finding is Low. The owner decision does not raise it.

**Proposed change:** the owner chooses one option.
- **(a) Keep approval before apply.**
  - At :576: "ไม่อยู่ในการอนุญาตนี้: เจ้าของอนุมัติ diff ใน handoff ก่อน apply (:397)".
  - At :498: "patch → เจ้าของอนุมัติ diff ของตัวตรวจ → Claude apply ตาม D-006 และตรวจ hash → review ของ tests → commit → red".
- **(b) Accept the PR-label gate.** Amend :15, :397 and :537 to say so, align :498, and record the change in PROGRESS.md.
- **In either case:**
  - at :575, say whether a "yes" review is recorded as approval or put to the owner;
  - at :572, cite where (ฌ) was asked, or mark it "ตีความจากคำตอบรวม".

**Owner decision:** yes.

### F52 · Low · `wine_prefixes` raising inside `collect` gives `terminal_paths` None against the F30 rule, with no case

**Where:** contract :192–194 against :156–159, :402, :424 and :426.

**Refutation:** confirmed.

**Evidence:**
- **Rule at :193–194:** "`wine_prefixes` ยก OSError = `terminal_paths` None (UNKNOWN ของ terminal_install) และบรรทัด `wine: unreadable (<เหตุ>)`".
- **Rule at :156:** "path ที่พบอยู่ใน `terminal_paths` เสมอ · `terminal_paths` เป็น None เฉพาะเมื่อการค้นไม่ครบและไม่พบ path ใดเลย". :158 scopes "เสมอ" to the path search and the Wine-loader rule.
- **No case covers it.**
  - Every Wine-chain error case names `default_roots`: once at :402 and four times at :424.
  - No case runs `collect` while `wine_prefixes` raises. The only case with hand-built roots (the last one at :426) is the success path.
- **Trigger:**
  - Either hand-built roots, or the Wine chain changing between `default_roots` and `collect`. With default roots, `default_roots` raises first.
  - Plus a path found by another rule: `MetaTrader 5.app` at level 0, `terminal64.exe` under home, or a matching process.

**Impact:**
- :156 gives FAIL, :194 gives UNKNOWN, and no case decides between them. Both are non-PASS.
- Without a case, an implementation can catch the OSError, print `wine: unreadable` and search `roots.program_files` alone. It would pass every listed case and give PASS for this state.
- R1 builds its roots with `default_roots` only (:385), so through the CLI or R1 this needs a change between the two calls.
- This is r3 F30's class again, in new text from `4eb3147`.

**Proposed change:**
- At :194: "`wine_prefixes` ยก OSError = การค้นไม่ครบ (`terminal_paths` None เฉพาะเมื่อไม่พบ path อื่น ตามกฎของ r2 F30) และบรรทัด `wine: unreadable (<ข้อความของ OSError>)`".
- Add one case on `collect`:
  - hand-built roots with `program_files=()`, and a fake home whose `Library/PlayOnMac/wineprefix` exists but cannot be listed → `terminal_install` UNKNOWN and `wine: unreadable (…)`;
  - the same, with `MetaTrader 5.app` at level 0 of a fake app folder → FAIL.

**Owner decision:** no.

### F53 · Low · Four listed inputs leave one returned element or one part of a line undefined

**Where:** contract :176–179, :234, :243, :247, :279–280, :315–316, :320, :322, :324, against cases :406, :414, :420, :424 and :426.

**Refutation:** confirmed. Lens A's part 5 is under F48.

**Evidence:**
1. **`classify_mounts`, third element.**
   - :176 defines it as "จุด mount ที่ไม่อยู่ในรายการอนุญาต", which means any such point.
   - :320 lists after `not allowed:` only "จุด mount ที่เข้ากฎนี้", and that rule applies "เมื่อไม่เข้ากฎ FAIL" (:315–316).
   - So case :414, "`smbfs` ที่ `/Volumes/share` (FAIL: กฎ FAIL มาก่อน)", can expect `('/Volumes/share',)` or `()`. Its `mounts:` line may or may not end with `; not allowed: /Volumes/share`.
2. **`classify_mounts`, fourth element.**
   - :177 offers "None เมื่อผ่าน, `missing` หรือ `<ชนิด>` เมื่อไม่ใช่ apfs".
   - Case :420, "`/` ชนิด `apfs` ที่ไม่มี MNT_LOCAL (FAIL)", fits none of these. `/` is present and is apfs, yet it fails :322: "ต้องพบ mount ที่ `/` ชนิด `apfs` ที่มี MNT_LOCAL".
   - The `; root:` part of the `mounts:` line is undefined for this case too.
3. **`classify_processes`, third element.**
   - The loader rule at :279–280 excludes a `wine*` executable whose path has a `metatrader` component.
   - For :406's `/Users/x/MetaTrader 5/bin/wine64-preloader`, "จำนวน Wine loader" (:179) is 0 by the rule or 1 by the name. Whether `process_names` is None is open too.
4. **`wine_prefixes`, second element, and the `looked at` part.**
   - :247 names the source folders as "(`wineprefix`, `Bottles`)", while :243 also searches `~/.wine`, which is itself a prefix.
   - The text does not say whether `~/.wine` appears after `looked at`, or whether folders print as full paths, `~` paths or names.
   - Cases :424 and :426 state only `wine: 1 prefixes`.

**Impact:**
- A test that asserts the whole tuple or the whole line for these inputs must guess. A locked test written on one guess fails an implementation written on the other.
- No verdict changes. R1 compares `wine:` only after PASS, and both sides come from the same code.

**Proposed change:** add one clause for each item.
1. At :176: "เฉพาะจุด mount ที่เข้ากฎ UNKNOWN ของรายการอนุญาต (ไม่รวม mount ที่เข้ากฎ FAIL)", or the reverse, stated once.
2. At :177: state the value for an apfs `/` without MNT_LOCAL, for example "None; FAIL อยู่ใน remote_drives".
3. At :179: "นับเฉพาะโปรเซสที่เข้ากฎ Wine loader", and state `process_names` for the :406 case.
4. At :234 and :247: say whether `~/.wine` is a source folder, and how the looked-at folders print.

**Owner decision:** no.

### F54 · Low · `.<sentinel name>.icloud` under a data dir: the `excluded_period` result is unstated

**Where:** contract :331–332 against :428; envkit:367–395.

**Refutation:** confirmed.

**Evidence:**
- **The rule.** :331–332: "ใต้ repo หรือ data dir = UNKNOWN ของ `excluded_period` และ `sentinel` ยกเว้น `.<ชื่อ sentinel>.icloud` ซึ่งเป็น FAIL ของ `sentinel` ตามกฎ (2) ทุกพื้นที่ (r2 F30)".
- **The case.** :428: "`.<ชื่อ sentinel>.icloud` ใต้ `<repo>/data/` (FAIL ของ `sentinel`)".
- **Two readings:**
  - the exception covers the whole clause, so `excluded_period` is PASS;
  - the exception covers only the status of `sentinel`, so `excluded_period` is UNKNOWN.
- **The cited source does not settle it.** r2 F30, which the rule cites, settled only the sentinel status: "`.<ชื่อ sentinel>.icloud` = FAIL ทุกพื้นที่" (`docs/reviews/ENV-002-contract-v2-r2.md`:351).
- **The locked kit encodes the first reading.** envkit's `check_report` expects PASS for every item not named (envkit:368, :395), so `check_report(report, fail=("sentinel",))` is the PASS reading.

**Impact:** a locked test and the code can disagree. The verdict is FAIL either way.

**Proposed change:** name the status of `excluded_period` in :428, and make :331–332 say the same.

**Owner decision:** no.

### F55 · Low · Three inputs of `host_lines()` are left implicit

**Where:** contract :207–215, :225, the follow-up case at :426, :149 and :436 (d2); test_ac05:72.

**Refutation:** confirmed in part. Part 1 is a question: the behaviour is stated, but its mechanism and a case are missing.

**Evidence:**
1. **Direct calls of `collect`.**
   - :209–210: "ถ้าถูกเรียกตรง (ไม่ผ่าน `research_host_report`) ก็ล้างและบันทึก reader กับ `roots` เองก่อน".
   - `collect(roots)` receives only roots, and the locked fake `_Host.collect(self, roots)` (test_ac05:72) takes one argument. So `research_host_report` cannot pass a flag; the signal must live in `_HOST_SUMMARY` or in the roots object.
   - No case covers a direct `collect` call made after a `research_host_report` call that used a replaced `collect`.
   - Two plausible implementations go wrong differently. A marker that is never consumed shows the earlier call's roots. A `collect` that always clears drops the token that `research_host_report` recorded.
2. **The platform of the follow-up case.**
   - :426 reads "`host_lines()` หลัง `research_host_report` ที่แทน `collect` ด้วยตัวปลอม โดยรันต่อจาก test ข้างต้นใน process เดียวกัน (`processes: not read`, `mounts: not read`, `wine: not read`)", and sets no platform.
   - :213–214 give those lines only on darwin: "reader อื่นได้แค่ `reader:` และ `roots:`".
   - monkeypatch restores `sys.platform` after the previous test. Written literally, the test passes on this Mac, which is darwin natively, and fails on Linux CI.
3. **The win32 `; onedrive: <n>` form (:225) has no source.**
   - `host_lines()` reads no OS (:211), `research_host_report` records only reader, roots and token (:207), and `ResearchRoots` gains no field (:149).
   - No case covers the form, and v2.x code never runs on win32 in this task: (d2) uses `c97aac6` (:436).

**Impact:** no listed verdict changes, and no production path is affected. The test author and the implementer must guess, and part 2 produces a failure that appears only in CI.

**Proposed change:**
1. Either state the signal (for example, `research_host_report` records the roots object, a `collect` that receives the same object (`is`) does not clear, and the marker is removed after `collect` returns) and add the case above. Or simplify to: "`collect` ตัวจริงบน darwin เขียนเฉพาะ key ของ processes, mounts, wine, skipped, apps, tools · test ที่ตรวจ `roots:` เรียกผ่าน `research_host_report` หรือ `main`".
2. In the follow-up case at :426, add "ตั้ง platform เป็น darwin".
3. At :225, name the recorder and add one case, or drop the form.

**Owner decision:** no.

### F56 · Low · Text superseded by v2.3 or by `4f3c5cc` still reads as current

**Where:**
- contract rule text: :385, :458, :558;
- contract status and history text: :4, :529, :547, :548, :559, :561, :562, :607, :609;
- handoff:592–598.

**Refutation:** confirmed. Residual 15's missing row is counted under F36.

**Evidence:**
- **Rule text:**
  - :385, "(roots ที่ประกอบเองข้ามการค้น Wine prefix ได้)", contradicts :193, "roots ที่ประกอบเองจึงไม่ข้ามการค้น Wine prefix".
  - :458 is a runbook requirement that Claude copies into the runbook: "`mount` ต้องมีแต่จุด มount `/`, `/dev` และใต้ `/System/Volumes/` (r2 F32)". It predates the narrowing at :317.
  - Answer row 4 at :558 has no v2.3 note.
- **Status and history text written before `4f3c5cc`:**
  - :4: "รอการตรวจซ้ำของ r3 (ถ้าเจ้าของสั่ง)".
  - :529: "Claude 5 และ session ใหม่ 8 เป็นข้อเสนอทั้งสองตัวเลข การอนุมัติ (จ) กำหนดทั้งสองตัว". This contradicts :574 and :593, which record caps of 6 and 12 set under the 11:2x permission.
  - :609: "ข้อ 1, 3, 4 … ยังเป็นของเจ้าของ · … การตรวจซ้ำรอบที่ 4 ต้องให้เจ้าของเพิ่มงบ … · next: เจ้าของตัดสินว่าจะสั่งตรวจซ้ำ r4 หรืออ่านแล้วอนุมัติ".
  - Rows :547 ("(v2.3: ยังเป็นข้อเสนอ รอเจ้าของ)"), :548, :559, :561 and :562 still read as waiting for the owner. They lack the 11:2x note that (ซ), (ฌ) and (ญ) received.
  - The reading list at :607 predates the section at :565–578, which carries commitments.
  - Handoff:592–596 (Budget) and :598: "The owner decides: a re-check of v2.3 (round 4, needs budget), or read and approve v2.3."

**Impact:**
- No result changes, but the owner reads two current answers to the same question.
- The runbook pre-check would pass a mount that envcheck makes UNKNOWN. This fails closed, but it confuses.

**Proposed change:**
- At :385, drop or correct the parenthesis.
- At :458, add "(ใต้ `/System/Volumes/Data/` มีได้แค่ `Data` และ `Data/home`; v2.3, r3 F32)", and the same note at :558.
- At :4 and :609, add a v2.3 DoR line that says what 11:2x settled, what r4 found and the next step. Add :565–578 to the reading list.
- At :529, point to Budget at :593. Add "(ตอบแล้ว 2026-11-18 11:2x)" to rows :547, :548, :559, :561 and :562.
- Update the handoff's Budget and Next.

**Owner decision:** no.

## AC status

No AC changed status. Every v2.x AC is UNKNOWN: no v2.x code or test exists, and `75948ff..4f3c5cc` changes documents only.

| AC | Status | Why |
|----|--------|-----|
| AC-01 (macOS) | UNKNOWN | The owner's L4 run is not done. Measured today: 12 mounts, all inside the narrowed allow list, and the seven `tools:` paths give the predicted `tools: .colima, .docker`. Under F50 a PASS can be forged, and that is not a named residual. |
| AC-02 | UNKNOWN | No v2.x tests exist. F49 is a case no correct implementation passes as written. F48, F52, F53, F54 and F55 decide test inputs or expected results. |
| AC-03 (macOS) | UNKNOWN | The owner's steps are not done. (d2) is pinned to `c97aac6` (F46 closed). |
| AC-04 | UNKNOWN for v2.x | Unchanged by v2.3. The v1.9 tests pass (222 passed, with the architecture tests). |
| AC-05 | UNKNOWN for v2.x | By the text, the locked CLI tests still pass. Host lines print before `render`, and test_ac05:220–233 checks only the exit code, the last line, the item names and the token. Lens A's in-memory probe (22 passed for each reader) was not repeated here. |
| AC-06 | UNKNOWN | The darwin checker patch does not exist, and its approval gate is contradictory (F51). Lens A and r3 report no checker rule on module-level state such as `_HOST_SUMMARY`; this session did not re-read test_imports. |
| AC-07 | UNKNOWN | Not run for v2.x. r3's order dependence is removed by :207 and the case at :426. The follow-up case still needs its platform stated (F55). |

## Checked and correct (and how)

| Command or check | Result | Commit | Time |
|---|---|---|---|
| `git status --short`, before and after every probe | Empty. `git status --short --ignored` was unchanged: `.mypy_cache/`, `.venv/`, 31 `__pycache__/`. | `4f3c5cc` | 12:0x–12:15 +0700 |
| `git diff --stat 75948ff..4f3c5cc`; `git log 75948ff..4f3c5cc` | 4 files: DECISIONS.md (1 line), PROGRESS.md, the contract, the handoff. No code, test, lockfile or locked path. 18 commits; every closure commit in the re-check table exists. | `4f3c5cc` | 12:0x +0700 |
| `bash scripts/controls/red-flags.sh main` | "Pattern groups with hits: 0". The control files it lists are the seven v1.x locked test files. | `4f3c5cc` | 12:09 +0700 |
| `PYTHONTZPATH="" PYTHONDONTWRITEBYTECODE=1 uv run --offline --no-sync pytest tests/acceptance/ENV-002 tests/architecture -q -p no:cacheprovider` | 222 passed in 2.00 s (v1.9 code) | `4f3c5cc` | 12:09 +0700 |
| `git check-ignore -v` on five hypothetical bytecode paths | All five ignored by `.gitignore`:19 or :20 | `4f3c5cc` | 12:0x +0700 |
| `ls -ld` of the uv interpreter's `lib/python3.12`, `json` and `site-packages`; `.venv/pyvenv.cfg` | All `drwxr-xr-x faztycoding staff`; `.venv` points at that interpreter | — | 12:0x +0700 |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src uv run --offline --no-sync python -m site`; `python -I -c` for `BYTECODE_SUFFIXES` and `_imp.is_frozen` | sys.path: repo root, `src`, stdlib zip, stdlib, `lib-dynload`, `.venv` site-packages. `['.pyc']`. `json` not frozen; `os` frozen. | — | 12:0x +0700 |
| `git config --get status.showUntrackedFiles`; `.git/info/exclude` | Unset; no entries | — | 12:0x +0700 |
| `/sbin/mount`; existence of the seven `tools:` paths; the SDK's `sys/mount.h` | 12 mounts, all allowed by :315–319. `.colima` and `.docker` present, the other five absent. `MNT_LOCAL 0x00001000` at :222. | — | 12:0x +0700 |
| `git show c97aac6:src/sochron/app/envcheck.py`; `git branch -a --contains c97aac6` | No `reader:` line and no `host_lines`. The commit is in both ENV-002 branches, local and remote. | — | 12:0x +0700 |
| The contract hunks of `git show 7a1c6ea` and `git show 4eb3147` | `7a1c6ea` adds residual 15; `4eb3147` adds the F48 line forms | — | 12:0x +0700 |

**What was read:**
- **In full:** the skill file, r3, the contract at `4f3c5cc`, and both lens files.
- **In part:**
  - DECISIONS:255–277 and PROGRESS.md:3–7;
  - envkit:180–310 and :367–397;
  - test_ac05:60–95 and :220–233, and test_ac02:754–771 (by grep);
  - `.github/workflows/control-gate.yml`:1–40 and `docs/contracts/CORE-002-costs.md`:3–4;
  - r2 by grep (`.icloud`), and the contract at `e7cbc38` by grep (`.colima`) and at :190–198;
  - handoff:590–599.

**What was compared:**
- Every lens quote, re-opened at its line.
- Every r3 proposed change, against the v2.3 text.
- **D-023 against the contract:** only its header changed since r3. Option 1, the order of AC-03 (7) and (d2) agree.

## Not checked (and why)

- **No v2.x code or tests exist.** Every judgement is made on the text, against today's code and locked tests.
- **F50 was not demonstrated**, because creating a file is outside a read-only review. It rests on `.gitignore`, `git check-ignore`, the `-m site` printout, the folder permissions, and CPython's documented loading of cached bytecode, sourceless bytecode and `sitecustomize`.
- **Lens A's simulated-v2.3 probe was not repeated**, because it loads a lens-written plugin into pytest. F25's closure is judged on the text and on test_ac05.
- **The full suite, `check-locked-paths.mjs`, `test-controls.mjs` and mypy were not run.** The diff since r3 changes documents only.
- **Private folders:** none was listed, and envcheck was not run against the real home. Only `mount` and the existence of seven home paths were checked.
- **The owner's 11:2x message is not in the repository.** What was asked is known only from :566 and PROGRESS.md:5. Whether "อนุญาติทั้งหมด" covers (จ), the checker diff and (ฌ) is not judged here; that is F51.
- **The handoff** was opened only at :590–599, after the lens findings existed, to verify one quoted line.
- **Not read:** SPEC.md, docs/architecture.md, test_imports.py, and the ENV-001 and SPIKE-002 contracts.
- **Not touched:** MT5, Wine, VMs, containers, the VPS, the broker, the old Windows PC, the Keychain, `.env`, and the contents of `~/.docker`. No URL was fetched.

## Questions for the owner

1. **F51: the locked checker and your 11:2x answer.**
   - (a) Do you approve the test author's change to the locked ctypes checker before it is applied, as the Invariants say (:397)? Or is the `owner-approved-control-change` label on the PR enough (:576)?
   - (b) When a contract review says "Ready … yes", should Claude record your approval of v2.x and D-023 under your 11:2x answer (:575), or ask you at that point?
   - (c) Was (ฌ), which folds the re-check of F12–F15 into the work review, part of what you answered at 11:2x? The record lists four questions without it (:566).
2. **F50: planted bytecode.** Do you close it with runbook steps, option (a): clean and check the ignored files, run with `PYTHONSAFEPATH=1`, and reinstall or verify the uv interpreter? Or do you accept it as a new residual 16 of (ญ), option (b)?

Ready for the owner's approval (ENV-002 v2.3): no (0 High; 2 Medium first: F49 changes text the locked tests will be written from, and F50 needs your choice; F51 needs your answer before any review can say yes; fix Low F48, F52, F53, F54 and F55 before the locked tests are written; fix F36 and F56 in the same pass)
Ready for owner decision (D-023): no (no finding is against D-023's own text, but its header ties acceptance to contract v2.x, which is not ready, and how acceptance is recorded, including DECISIONS:264 "เจ้าของยืนยันตอนรับ D-023", waits for your answer to F51)
Findings open: 10 (0 High · 2 Medium: F49, F50 · 8 Low: F36, F48, F51, F52, F53, F54, F55, F56)
