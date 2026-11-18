# Review ENV-002 contract v2.2 round 3 (ENV-002 v2.2 draft, D-023)

Base: contract v2.1 at `db6e021` plus review r2 at `a9b3644` · head `e7cbc38` on `chore/ENV-002-macos-research-host` ·
reviewer: three fresh-context Claude reviewer sessions (read-only; lenses: closure of the eight Medium findings of r2,
closure of the 19 Low findings with every DECISIONS.md edit, whole document), one independent refutation pass per lens,
consolidated by a further read-only Claude session · 2026-11-18

**Label: contract review by fresh Claude sessions** under the role swap recorded in PROGRESS.md:5 on 2026-11-18. The
contract leaves that swap for the owner to confirm (decision (ซ), contract :465), and nothing in PROGRESS.md records
that the owner has switched the binding. Until he confirms it, this file may be read as a pre-review (Claude
subagent). The session that wrote v2.2 did not review it. This review does not claim that the separation is secure.
The task is High and the owner's own approval is still required.

**Ready for the owner's approval: no.** Reasons:
1. No High finding is open, and r2 left none.
2. Seven of the eight Medium findings of r2 are closed (F4, F7, F9, F10, F12, F14, F27).
3. One Medium finding is open: F25, closed in part. The fix for it (`9e80e9b`) keeps the summary behind
   `host_lines()` in a module-level variable with no stated lifetime, so the case "`collect` replaced" at contract
   :382 depends on test order in the single pytest process that AC-07 requires. The same text names no source for
   the `roots:` line, the `wine:` line or the token.
4. F25 changes text the locked tests will be written from, so it comes before approval.
5. Thirteen Low findings are open and listed below. Eight of them should be fixed in the same pass, before the
   tests are written, because they decide a test input or an expected result: F28, F30, F32, F33, F43, F44, F45, F48.
   The other five (F36, F41, F42, F46, F47) concern what the owner reads and what the evidence will contain; fix them
   before the owner reads the contract for approval.

**Findings open: 14 = 0 High, 1 Medium, 13 Low.** Of the 27 findings r2 left open, 20 are closed, 7 are closed in
part and none is fully open. Seven findings are new (F42–F48).
Refutation pass over the 40 lens entries: 36 confirmed, 4 confirmed in part, 0 refuted, no closure found wrong.
Severities below are the corrected ones. Where the refutation pass did not uphold part of an entry, the section says so.

How to read the references:
- "contract :NN" is `/Users/faztycoding/Documents/GitHub/Sochron1k/docs/contracts/ENV-002-research-host-separation.md`
  at `e7cbc38`; "DECISIONS:NN" is `/Users/faztycoding/Documents/GitHub/Sochron1k/DECISIONS.md` at the same commit;
  "envcheck:NN" is `src/sochron/app/envcheck.py`; "test_imports:NN" is `tests/architecture/test_imports.py`;
  "test_ac02:NN", "test_ac05:NN" and "envkit:NN" are files of `tests/acceptance/ENV-002/`.
- "Probe" is a read-only shell or `uv run --offline python -I` run on this Mac (arm64, CPython 3.12.15) by a lens and
  repeated by its refutation pass. Probes marked "(consolidation)" were repeated by the consolidating session.
- Source ids: M = closure of the Medium findings, L = closure of the Low findings, W = whole document; the number is
  the entry index in that lens.

How it was verified: each lens read the contract at `e7cbc38` in full against the code, the locked tests,
DECISIONS.md and the v2.2 diff, and ran read-only probes. The consolidating session read the whole contract (545
lines) and re-opened every line quoted in F25 and in each Low finding. All quotes matched. Corrections to the lens
material:
- The handoff does not repeat the predicted `tools:` line; `docs/handoff/ENV-002.md`:528 says only that `.colima` is
  on this Mac (F42).
- The clause "เท่ากับ `metaquotes`" is at contract :258, not :257 (F28).
- The two lenses rated the non-lifetime part of F25 differently (Low and Medium). It is kept as one Medium finding
  because the lifetime part alone meets the definition.

No URL was fetched.

## Re-check of r2 findings

| r2 ID | r2 Sev | Status | v2.2 commit | Evidence (one line) |
|----|----|----|----|----|
| F4 | Medium | closed | `7f92780` | contract :173–184: typed raw readers with a failure contract, pure `read_process_paths`/`read_mounts` that raise OSError, `never_listed: tuple[Path, ...]`, both gates in `collect` before any reader; probe: `proc_listallpids` returns the capacity when the buffer is full. |
| F7 | Medium | closed | `01d2a5c` | :366 binds each process case to `read_process_paths`, `collect` or `classify_processes` with a fakeable input and one result; :391 lets AC-02 use them. |
| F9 | Medium | closed | `9d15b44` | :345 R1 calls `envcheck.host_lines()` after PASS and compares four lines in code; :253–256 `tools:` from seven named paths, existence only; :362 two cases. Wrong prediction of the line → F42. |
| F10 | Medium | closed | `e966b01` | :233–234 no v1.8 skip and the Windows helper is not called on darwin; :218–220 OSError for the Wine-chain folders; :380 four cases; :450. Symlink gap → F43. |
| F12 | Medium | closed | `8043876` | :382 holds a case for each of the eight rules r2 listed, the `DYLD_` gate included; :238–239 states the app-folder rule. Order dependence of one case → F25. |
| F14 | Medium | closed | `3b78710` | :413 C9 Quit plus `pgrep -ilf 'claude\|codex\|chatgpt'`; :392, :445 point to C9; probe: `-ilf` accepted, and the pattern matched 4 running agent processes. |
| F15 | Low | closed | `7a4bf24` | :203 slot `[; not allowed: <จุด mount>, …]`; :280 rule; :374 case. |
| F16 | Low | closed | `44955dc` | :422 "`mt5_package` บน darwin ไม่นับเป็นการป้องกัน"; agrees with :43, :415, :476. |
| F17 | Low | closed | `15ffe0b` | DECISIONS:271 cites the "Review when" line; DECISIONS:31 and `docs/architecture.md`:77 (section 5) hold it. |
| F24 | Low | closed | `84c9387` | :462 "v2.x ฉบับล่าสุด … (ตอนนี้ v2.2; High)"; D-023 reads "v2.x"; :450 runbook steps; checklist C1–C10 everywhere. New places of the same class → F47. |
| F25 | Medium | partly (Medium) | `9e80e9b` | `host_lines()` is named and placed (:192–196) and `note:` is `apps:`. Lifetime of its state, sources of `roots:`, `wine:` and the token, and the bound signatures are open. |
| F26 | Low | closed | `f570387` | :283–285 order stated once; :378 five cases on `classify_mounts`; flags at :362, :376; fits envcheck:130–136, :524–531. Under-specified PASS cases → F45. |
| F27 | Medium | closed | `14635de` | :41 records the full-depth, names-only walk of the five roots from Visual Studio Code: 0 refused, 0 dataless. Not repeated by this review (private folders). |
| F28 | Low | partly (Low) | `51f08bf` | :264–267 one sentence per consumer, :431 residual. The new UNKNOWN rule at :266 has no case and does not say whether `<appdata>/MetaQuotes` follows it. |
| F29 | Low | closed | `da93068` | :345 R1 records and compares `roots:` and builds roots only through `default_roots`; :227. |
| F30 | Low | partly (Low) | `0301d59` | :156–158 rule, :167 `(paths, complete)`, :384 three cases. :310 still sets `terminal_paths` = None without the F30 reference; "เสมอ" at :156 overstates. |
| F31 | Low | closed | `3504f15` | :286–287 regrow rule; :176, :179; :384 case. |
| F32 | Low | partly (Low) | `da27b83` | :278–281 allow list with cases at :374. The allowed prefix contains the writable data volume (`/System/Volumes/Data`). |
| F33 | Low | partly (Low) | `7d4cd57` | :230–231 level-0 rule with or without `.app`; :372, :384 cases; :430, :473 residual. The process rule at :240, :246 that refers to it is now ambiguous. |
| F34 | Low | closed | `e6fed8c` | :324–326 two arguments only, four more mutations; :396 binds them. |
| F35 | Low | closed | `2b7963f` | :355 named exception; :389 `rmdir` and `ls -d`. |
| F36 | Low | partly (Low) | `ccdb669` | :430 "เสนอให้รับ", decision (ญ) with 12 items, :542 reading list. (ญ) and the threat table do not list the same residuals; D-023 is not on the reading list. |
| F37 | Low | closed | `e6623b4` | :392 (7)(d2) one Windows run without `--sentinel-file`; envcheck:882–883, :890–891 agree; :494, :510; DECISIONS:264. Missing commit pin → F46. |
| F38 | Low | closed | `074a290` | :465 binding "รอเจ้าของยืนยันตอนอนุมัติ" with a fallback; :466 (ฌ); :498, :511, :542; PROGRESS.md:5 agrees. |
| F39 | Low | closed | `6720acf` | :482 full quote with the cut marked; PROGRESS.md:7 identical. The owner's original message is not in the repository. |
| F40 | Low | closed | `97e0667` | :528 and :512: 5 sessions proposed, drafting counted, 2 used, number waits for the owner. One observation → question 4. |
| F41 | Low | partly (Low) | `1c48e79` | :199–200 count and provider prefix only; :386 case. Answer 9 (:513) promises more than the `roots:` line delivers. |

## Findings (open and new)

| ID | Sev | Kind | File:line | Finding | Owner decision | Sources |
|----|-----|------|-----------|---------|----------------|---------|
| F25 | Medium | confirmed | contract :192–196 against :382, :397; :165–181, :202–207, :211–221, :345; envkit:84–95; test_ac05:84–88; envcheck:807–809 | The state behind `host_lines()` has no lifetime, three lines have no stated source, and the bound signatures cannot carry what the lines print | no | M6, M8, W0 |
| F28 | Low | confirmed | contract :266 against :391, :257–258, :263; envcheck:242, :349; test_ac02:754–771 | The UNKNOWN rule for a folder evaluate skips by name has no case and no statement on `<appdata>/MetaQuotes` | no | L5 |
| F30 | Low | confirmed in part | contract :310, :156 against :177–178, :366 | One older sentence still sets `terminal_paths` to None; "เสมอ" does not hold when `read_process_paths` raises | no | L7 |
| F32 | Low | question | contract :278–281, :414, :429, :508 | The allow list admits every mount point below `/System/Volumes/Data/` | yes (narrow or residual) | L9, W1 |
| F33 | Low | confirmed | contract :240, :246 against :230–231, :171, :362, :368 | "ใต้แอปที่ตรงกฎชื่อข้างบน" has two readings for `classify_processes` now that the rule no longer needs `.app` | no | L10, M10, W3 |
| F36 | Low | confirmed in part | contract :467–479 against :429–431, :309–310; :542, :462; :497, :512, :528 | (ญ) and the threat table do not list the same residuals; D-023 is not on the reading list; the 8 sessions read as decided | yes (accept per item) | L13, W2 |
| F41 | Low | confirmed | contract :513 against :199–200, :386; envcheck:297–303, :549–551 | Answer 9 is not scoped to the `roots:` line; item details of a non-PASS report still print full paths | yes (scope of answer 9) | L18 |
| F42 | Low | confirmed | contract :253–255 | The contract predicts `tools: .colima`; this Mac also has `~/.docker` | no | M9 |
| F43 | Low | confirmed | contract :216, :218–219 against :127, :213, :380 | The symlink clause does not name `wineprefix`, `Bottles` or the `Program Files*` entries | no | M11 |
| F44 | Low | confirmed | contract :169–170, :269, :378 | `classify_mounts` takes integer flags; the value of MNT_LOCAL is nowhere in the contract | no | M12, W3 |
| F45 | Low | confirmed | contract :362, :374, :376 against :278, :282–284, :378 | Mount cases that expect PASS state no `/` baseline and no mount point | no | L19, W3 |
| F46 | Low | confirmed | contract :392 (7)(d2) against :389, :197–200, :62, :493 | The Windows run names no commit; on v2.x code its report carries the Windows profile and OneDrive paths | yes (if v2.x code is run) | L20, M13 |
| F47 | Low | confirmed | contract :390, :393, :533, :495, :497, :506; DECISIONS:259 | Text superseded by v2.2 still reads as current | no | L21 |
| F48 | Low | confirmed in part | contract :199, :202–207, :253–254 against :183, :244, :345, :39 | Forms of the host lines that will occur are not given | no | W3, M6, L18 |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

### F25 · Medium · `host_lines()`: no lifetime for its state, no source for three lines, signatures that cannot carry the lines
- **Where:** contract :192–196 against :382 and :397; :165–181, :202–207, :211–221, :285, :345, :380; envkit:84–95; test_ac05:84–88; envcheck:807–809.
- **Closed parts (`9e80e9b`):** the function is named (:192), reads no OS and raises nothing, `main` prints its lines before `render`'s text (:195), the `default_roots` error path is stated (:196), `note:` is renamed `apps:` (:206). The locked CLI tests read the last line, the item names and the token only (test_ac05:226–231), so they still pass.
- **Evidence:**
  - (1) Lifetime.
    - :192 "`collect` บน darwin เก็บสรุปของการอ่านรอบล่าสุดไว้ในตัวแปรระดับโมดูล".
    - :193–194 "เมื่อ reader เป็น darwin แต่ `collect` ไม่ได้รันตัวอ่าน darwin ในโปรเซสนี้ (ถูกแทนใน tests) คืน `reader:`, `roots:`, `processes: not read`, `mounts: not read`".
    - :382 lists both "`host_lines()` หลัง `collect` บน darwin ด้วยตัวอ่านดิบปลอม: … `processes: 3 listed, 2 paths read, 1 skipped, 0 wine loaders`" and "`host_lines()` เมื่อ `collect` ถูกแทน (`processes: not read`, `mounts: not read`)".
    - All tests share one module object: envkit:87 uses `importlib.import_module("sochron.app.envcheck")`, `pyproject.toml` has no xdist or forked mode, and no ENV-002 test reloads the module (consolidation: `grep`).
    - After any darwin `collect` test the condition "ไม่ได้รัน … ในโปรเซสนี้" is false for the rest of the run. The variable has no name and no reset point, so a test cannot clear it.
  - (2) `roots:` must be returned exactly when the darwin `collect` stored nothing (a replaced `collect`; the win32 and none readers, :194). `host_lines()` takes no argument and may not read the OS. The locked CLI tests replace both `collect` and `default_roots` (test_ac05:84–88). No function is named as the one that records the roots, and the result of `host_lines()` before any call is not given.
  - (3) `wine:` comes from the prefix search, which the contract puts in `default_roots` (:211–221), not in `collect`.
    - `ResearchRoots` gains no field (:149), and `find_wine_program_files(home) -> tuple[Path, ...]` (:168) returns neither the prefix count nor the folders looked at.
    - The case :380 "prefix ที่ไม่มี `drive_c` (PASS, `wine: 1 prefixes`)" has an empty `program_files`, so the count cannot be derived from the roots.
    - :382 expects `wine: 0 prefixes; looked at none` "หลัง `collect`", with no `default_roots` call named.
  - (4) The token. :193 has `host_lines()` replace the token, but `collect(roots)` never receives the sentinel (envcheck:807–809). R1 records `roots:` from `host_lines()` (:345).
  - (5) Signatures. :165 "ชื่อและ signature เป็นข้อผูกของ contract", yet none of the bound functions can return what the lines print.
    - `read_process_paths(...) -> tuple[str, ...]` (:177, under "pure" at :173) cannot return the `listed` and `skipped` counts.
    - `classify_mounts` (:169, "pure" at :285) cannot return the `not allowed:` mount points of :203.
    - `find_terminal_paths_darwin` (:167) cannot return the skipped paths of :205.
  - Not upheld from the lens material: the contract does not call `find_terminal_paths_darwin` pure, and the errno of the failure form can travel on the OSError itself.
- **Impact:**
  - An implementation that follows :192–194 literally returns an earlier test's lines in the "`collect` replaced" case, so that case passes alone and fails in the full run AC-07 (:397) requires. pytest order is deterministic, so this is a fixed failure, not flakiness.
  - If the locked test calls `host_lines()` straight after replacing `collect`, no implementation can pass it without a new owner-approved patch to a locked test.
  - For (2)–(5) the test author and the implementer must each guess where the roots, the Wine summary and the token are recorded. A locked test written on one guess fails a correct implementation of the other.
  - No wrong PASS: the lines do not feed the verdict, R1 calls `require_research_host` (which runs `collect`) before `host_lines()`, and R1's comparison is fail-closed.
- **Proposed change:** add under :192–196, choosing one design and naming it:
  1. Lifetime: replace "ในโปรเซสนี้" with "`research_host_report` ล้างสรุปแล้วบันทึก `roots` และ token ของ sentinel ก่อนเรียก `collect` ทุกครั้ง ทุก reader · `collect` ตัวจริงบน darwin ที่ถูกเรียกตรงก็ล้างและบันทึก `roots` เอง · `host_lines()` คืนบรรทัดของการเรียกครั้งล่าสุด · `collect` ที่ถูกแทนจึงให้ `not read` ไม่ว่า test ก่อนหน้าทำอะไร". `research_host_report` already receives both `roots` and `sentinel` (envcheck:807), so no signature changes.
  2. State what `host_lines()` returns before any call (for example `reader:` only), and at :382 say that the "`collect` replaced" case goes through `main` or `research_host_report`.
  3. `wine:`: say which function produces it. One way that makes hand-built roots give the same line: `collect` on darwin repeats the prefix search on `roots.user_profile` through one named function that returns the prefixes, the source folders that exist and the `Program Files*` roots, and `find_wine_program_files` returns its third part.
  4. Either say "pure ในที่นี้ = ไม่เรียก OS; ฟังก์ชันเหล่านี้เขียนส่วนสรุปของตัวเองลงตัวแปรระดับโมดูลเดียวกัน", or widen the return values (counts, skipped paths, `not allowed` mount points).
- **Owner decision:** no.

### F28 · Low · The UNKNOWN rule for a folder evaluate skips by name has no case
- **Where:** contract :266 against :391, :257–258, :263; envcheck:242, :349; test_ac02:754–771.
- **Evidence:**
  - :266 "โฟลเดอร์ที่ evaluate ข้ามด้วยกฎชื่อนี้ทำให้ทุก item ที่ค้น root นั้นเป็น UNKNOWN (ไม่ข้ามเงียบ) เว้นแต่ `terminal_data` เป็น FAIL อยู่แล้ว" appears in no negative case, and AC-02 binds listed cases only (:391).
  - The only related cases (:368 and the locked test_ac02:754–771) set `terminal_data` to FAIL, which is the exception branch.
  - The name rule includes "เท่ากับ `metaquotes`" (:258) while :263 says "กฎของ `<appdata>/MetaQuotes` เทียบแบบเดิมของ v1.9 ไม่เปลี่ยน"; today that folder is pruned without a finding (envcheck:242, :349).
- **Impact:** An implementer can leave the UNKNOWN out with every acceptance test green. It is reachable only with the win32 reader or fake Facts, when a data dir or search dir covers appdata.
- **Proposed change:**
  - Add one case: Facts with `metaquotes_exists=False`, appdata under a covering data dir, a folder `metatrader 5` at level 0 of appdata holding a `.txt` with the token → `holdout_dir`, `excluded_period` and `sentinel` UNKNOWN, folder neither listed nor opened.
  - Add one clause at :266 saying whether `<appdata>/MetaQuotes` follows this rule or keeps the silent v1.9 prune.
- **Owner decision:** no.

### F30 · Low · One older sentence still sets `terminal_paths` to None; "always" overstates
- **Where:** contract :310, :156 against :177–178, :366.
- **Evidence:**
  - :310 still reads "โฟลเดอร์อื่นใต้ home ที่ list ไม่ได้ = รายการ path อ่านไม่ครบ → `terminal_paths` = None (UNKNOWN ของ terminal_install)" with no reference to the F30 rule, while :233 and :239 carry "ตามกฎของ r2 F30".
  - :156 says "path ที่พบอยู่ใน `terminal_paths` เสมอ", but `read_process_paths` returns paths or raises (:177–178; case :366), so a `terminal64.exe` path read before a failing pid is dropped.
  - Not upheld: that a test author has no expected status. UNKNOWN follows from :177, :181 and the collect case at :366.
- **Impact:** Two sentences give different field values for one state. No wrong PASS; cases :372 and :384 fix both outcomes of the path search.
- **Proposed change:**
  - :310 → "→ การค้นไม่ครบ (`terminal_paths` None ตามกฎของ r2 F30)".
  - :156 → add "ใช้กับการค้น path และกฎ Wine loader · เมื่อ `read_process_paths` ยก OSError ไม่มี path ของโปรเซส".
- **Owner decision:** no.

### F32 · Low · question · The allow list admits every mount point below `/System/Volumes/Data/`
- **Where:** contract :278–281, :414, :429, :508.
- **Evidence:**
  - :278–279 allows any "path ใต้ `/System/Volumes/`" and claims to cover a "volume ที่ mount ด้วย `-mountpoint` ที่ใดก็ตาม". :429 lists it as a defence.
  - Probe (consolidation): `mount` shows 12 mounts, among them `/dev/disk3s5 on /System/Volumes/Data (apfs, local, …)` and `map auto_home on /System/Volumes/Data/home (autofs, …)`.
  - Probe (consolidation): `/usr/share/firmlinks` lists `/Users`, `/Volumes` and `/private`; `/System/Volumes/Data/Users/$USER` exists and is writable.
  - Probe (lens): `/bin/realpath /System/Volumes/Data/private/tmp` prints the path unchanged.
  - Not reproduced: no volume was attached, so what the kernel reports in `f_mntonname` for a mount point given in that spelling is unproven.
- **Impact:** If the mount point is reported as passed, a local disk image mounted inside the home folder through the `/System/Volumes/Data/...` spelling passes `network_shares` without admin rights. That is the case answer 4 (:508) was chosen to turn into UNKNOWN. It needs a deliberate option, and the same files copied into `~/Downloads` are already residual (ญ) 3.
- **Proposed change:** one of:
  - Narrow :278: "ใต้ `/System/Volumes/Data/` อนุญาตเฉพาะ `/System/Volumes/Data` เองและ `/System/Volumes/Data/home`", with the case "`apfs` ที่มี MNT_LOCAL ที่ `/System/Volumes/Data/Users/x/mnt` (UNKNOWN)". This fits the 12 measured mounts.
  - Or drop "ที่ใดก็ตาม" at :279 and add the gap to the residual column of :429 and to decision (ญ).
- **Owner decision:** yes (narrow the rule, or accept the residual).

### F33 · Low · The process rule has two readings now that the name rule no longer needs `.app`
- **Where:** contract :240, :246 against :230–231, :171, :362, :368.
- **Evidence:**
  - :240 "path ของ executable อยู่ใต้แอปที่ตรงกฎชื่อข้างบน (ที่ใดก็ได้บนเครื่อง)"; :246 "ไม่อยู่ใต้แอปที่ตรงกฎ".
  - In v2.1 the rule above required "ลงท้าย `.app`" (`a9b3644` :205); `7d4cd57` changed it to "มีหรือไม่มี `.app` ก็ตาม" (:230–231) and left :240 and :246 untouched.
  - `classify_processes(paths: tuple[str, ...])` (:171) sees paths only, and every process case has a `.app` component (:362, :368).
- **Impact:** For a path such as `/Users/x/dev/metatrader-notes/.venv/bin/python` one reading gives FAIL of `terminal_install` and the other PASS; the same choice decides whether a Wine loader there is FAIL or UNKNOWN. No case decides it, so tests and code can differ without a failure. Neither reading adds a PASS that v2.1 did not have.
- **Proposed change:**
  - State the component rule at :240. Under the delegation's own principle (the stricter way), that is "path ที่มี component ใดก็ตามซึ่งชื่อมี `metatrader` (ไม่สนตัวพิมพ์ มีหรือไม่มี `.app`)". Its cost is a FAIL while any process runs from a folder so named.
  - Add one case on `classify_processes` for a component `MetaTrader 5` without `.app`, with its result.
  - If the narrow reading is wanted instead, write "และลงท้าย `.app`" and add that path as a PASS case.
- **Owner decision:** no (the owner may reverse the choice like any delegated answer).

### F36 · Low · (ญ) and the threat table do not list the same residuals; D-023 is not on the reading list
- **Where:** contract :467–479 against :429, :431, :309–310, :43, :415; :542, :462; :497, :512, :528.
- **Evidence:**
  - In the table but in no (ญ) item:
    - :429 "ระหว่างรอ SPIKE-002 เครื่องนั้นยังมี terminal … เป็นคำยืนยันของเจ้าของ โค้ดตรวจไม่ได้" (item 10 at :477 covers only the time after the envcheck round);
    - :431 "agent ที่รันในแอปเดียวกันอ่านโฟลเดอร์เหล่านั้นได้เท่ากับตัวตรวจ".
  - In (ญ) but in no table row: the vault-path half of item 9 (:476; stated only at :43 and :415).
  - In neither: the second skip entry `~/Pictures/Photos Library.photoslibrary` (:310) hides a `terminal64.exe` the same way the Trash does; only the Trash is named (:431, :472).
  - :462 asks the owner to accept D-023, but the reading list at :542 omits it.
  - :512 marks the 5 Claude sessions as a proposal, while :497 and :528 write the 8 fresh sessions as decided.
  - Not upheld from the lens material:
    - "described nowhere": :450 names D-023 item 5 and the ENV-001 revision.
    - "never put to him": :467 and :542 send the owner to the threat table, and :482 says he accepts its residuals on approval.
    - The other-account case is covered as a class by C10 and item 8.
    - The web terminal sits under a v1.x row accepted by decision (ค).
- **Impact:** (ญ) asks the owner to accept or refuse "ทีละข้อ", yet three residuals can only be accepted wholesale. No rule or test result changes.
- **Proposed change:**
  - (ญ) → add "13. ก่อนล้างเครื่อง Windows เดิม: การไม่เปิด agent ของโปรเจกต์บนเครื่องนั้นเป็นคำยืนยันของเจ้าของ" and "14. agent ที่รันใน Visual Studio Code อ่าน Desktop, Documents, Downloads และ iCloud Drive ได้เท่ากับตัวตรวจ (ผลของ decision (ช))".
  - Fold the Photos Library entry into item 5.
  - Add the vault-path sentence to row :422 or :424.
  - :542 → add "D-023 ทั้งฉบับ" to the reading list.
  - :528 → mark the 8 as "เสนอ รอเจ้าของยืนยัน" like the 5, or say in (จ) that approval sets both numbers.
- **Owner decision:** yes (accept per item; the numbers).

### F41 · Low · Answer 9 promises more than the `roots:` line delivers
- **Where:** contract :513 against :199–200, :386; envcheck:297–303, :389, :414, :422, :549–551.
- **Evidence:**
  - Answer 9 (:513) says "ไม่พิมพ์ชื่อเต็ม … ชื่อโฟลเดอร์อาจมีชื่อบัญชี" without scoping it to the `roots:` line.
  - Item details still print the full path of anything unlistable, unreadable or cloud-only under a search dir (envcheck:297–303 and the others), and only the token is replaced (:549–551).
  - The CloudStorage folders stay search dirs (:386).
- **Impact:** A FAIL or UNKNOWN report pasted into evidence can carry the provider account name that answer 9 says is not printed. A PASS report prints no such path.
- **Proposed change:** :513 → "เฉพาะบรรทัด `roots:` · detail ของ item ในรายงานที่ไม่ PASS ยังพิมพ์ path เต็ม: เจ้าของปิดบังก่อน commit" (as AC-03 does for the IP). The form for a count of 0 is under F48.
- **Owner decision:** yes (scope of answer 9).

### F42 · Low · The contract predicts `tools: .colima`, but this Mac also has `~/.docker`
- **Where:** contract :253–255.
- **Evidence:**
  - :254–255 "เครื่องนี้มี `.colima` (วัด 2026-11-18) บรรทัดในหลักฐานของ ENV-002 จึงเป็น `tools: .colima` และเจ้าของยืนยันใน AC-03 ข้อ 4 ว่า VM ของ colima ไม่มี MT5 หรือ Wine".
  - Probe (consolidation; existence test of the seven named paths only, nothing listed or opened): `.colima` present, `.docker` present, the other five absent. By the rule the line is `tools: .colima, .docker`.
- **Impact:** The evidence line will differ from the one the contract states, and the attestation sentence names colima only. No verdict changes; R1 compares against the line AC-01 actually prints.
- **Proposed change:** :254–255 → "เครื่องนี้มี `.colima` และ `.docker` (วัด 2026-11-18) บรรทัดในหลักฐานจึงคาดว่าเป็น `tools: .colima, .docker` (ค่าที่ commit คือค่าที่รอบ AC-01 พิมพ์จริง) และเจ้าของยืนยันใน AC-03 ข้อ 4 ว่า VM ของ colima และ container ของ Docker ไม่มี MT5 หรือ Wine".
- **Owner decision:** no.

### F43 · Low · The symlink clause does not reach `wineprefix`, `Bottles` or the `Program Files*` entries
- **Where:** contract :216, :218–219 against :127, :213, :380.
- **Evidence:**
  - :216 gives the source folders only the "มีอยู่แต่ list ไม่ได้" rule.
  - The symlink clause at :218–219 names `~/.wine`, each prefix folder, `drive_c`, `~/Library/PlayOnMac` and the CrossOver folder.
  - The only symlink case (:380) is a prefix folder.
- **Impact:** With `Bottles` as a symlink three builds are possible and no case decides: follow it, skip it under :127 and give PASS with `wine: 0 prefixes`, or raise. The skip reading is close to the stated residual on relocated bottles (:430, (ญ) 1).
- **Proposed change:** :218 → add `wineprefix`, `Bottles` and the `Program Files*` entries to the list, and add the case "`Bottles` เป็น symlink (`default_roots` ยก OSError)".
- **Owner decision:** no.

### F44 · Low · The value of MNT_LOCAL is nowhere in the contract
- **Where:** contract :169–170, :269, :378.
- **Evidence:**
  - `classify_mounts` takes `flags` as an int (:169–170) and its rules turn on MNT_LOCAL (:269, :282, :284 and the cases), but no value or named constant is given.
  - The `statfs` offsets (:273) and `SF_DATALESS` (:290) are given.
  - Probe (consolidation): `sys/mount.h`:222 `#define MNT_LOCAL 0x00001000`.
  - The tests run on Linux CI, where no header supplies the value.
- **Impact:** The test author must take the flag from outside the contract for every `classify_mounts` input. Most wrong values fail closed.
- **Proposed change:** :269 → add "`MNT_LOCAL` เป็นค่าคงที่ int `0x00001000` ใน envcheck (`sys/mount.h` ของ macOS SDK) แบบเดียวกับ `SF_DATALESS`".
- **Owner decision:** no.

### F45 · Low · Mount cases that expect PASS state no `/` baseline and no mount point
- **Where:** contract :362, :374, :376 against :278, :282–284, :378.
- **Evidence:**
  - A list without `/` is UNKNOWN (:284; case :378), and a mount point outside the allow list is UNKNOWN (:278).
  - :374 "mount `apfs` ที่ `/System/Volumes/Data` (PASS)" and "`devfs` ที่ `/dev` (PASS)" name one mount and no `/`.
  - :376 "`autofs` จาก `map auto_home` ที่ไม่มี MNT_LOCAL (PASS)" and :362 give no mount point for the autofs entry.
  - Probe (consolidation): the real entry is `map auto_home on /System/Volumes/Data/home`.
- **Impact:** Same class as r2 F26: a fixture with the map at `/home` is UNKNOWN by rule and PASS by case. A test that expects PASS there would push the implementer to exempt autofs from the allow list.
- **Proposed change:**
  - Add one sentence before the mount cases: "ทุกกรณี mount ที่คาด PASS ใช้รายการฐาน `/` (`apfs`, MNT_LOCAL) บวก mount ของกรณี · `devfs` อยู่ที่ `/dev` · `autofs` จาก `map auto_home` อยู่ที่ `/System/Volumes/Data/home`".
  - Add the case "`autofs` จาก `map auto_home` ที่ `/home` (UNKNOWN)".
- **Owner decision:** no.

### F46 · Low · The Windows run of AC-03 (7)(d2) names no commit, and envcheck is not on `main`
- **Where:** contract :392 (7)(d2) against :389, :197–200, :62, :493.
- **Evidence:**
  - (d2) gives the command and asks only "วางรายงานทั้งหมดในหลักฐาน"; AC-01 pins its run with `git rev-parse --short HEAD` (:389).
  - `git ls-tree --name-only main src/sochron/` lists no `app` package; `c97aac6` is contained only in the two ENV-002 branches.
  - On v2.x code the `roots:` line is printed on every platform (:197–199) with full paths, and on win32 the search dirs include `%OneDrive%`, `%OneDriveConsumer%`, `%OneDriveCommercial%` (:62).
  - Answer 8 (:493) accepts the macOS account name only.
- **Impact:** On a clone left on `main` the command fails with a visible error. The one machine-made piece of evidence for the old PC is not tied to a commit. If it runs v2.x code, the committed evidence carries the Windows profile path and OneDrive folder names.
- **Proposed change:** (d2) → "ที่ commit `c97aac6` ของ branch `feat/ENV-002-research-host-separation` (โค้ด v1.9: ไม่มีบรรทัด `roots:`) · หลักฐานมีผลของ `git rev-parse --short HEAD` และเวลา". If a v2.x commit is preferred, add at :200 "บน win32 โฟลเดอร์จากตัวแปร `OneDrive*` พิมพ์เป็นจำนวนเท่านั้น" and let the owner extend answer 8 to the Windows account name.
- **Owner decision:** yes, only if v2.x code is run on the old PC.

### F47 · Low · Text superseded by v2.2 still reads as current
- **Where:** contract :390, :393, :533, :495, :497, :506; DECISIONS:259.
- **Evidence:**
  - :462 says "v2.0 และ v2.1 ไม่ใช่ฉบับที่ขออนุมัติ", yet :390 and :393 retire the Windows ACs "เลิกใช้เมื่อ v2.0 อนุมัติ" and :533 reads "ถ้าเจ้าของไม่รับ D-023 หรือ v2.0".
  - Answer rows 10 and 12 (:495, :497) still describe the `/Volumes/` rule with no v2.2 note, while :278 says the allow list replaces it.
  - :506 says "ดูชื่อระดับ 0 ของ home" while the rule also checks `<home>/.local/share/containers` (:254).
  - DECISIONS:259 cites only r1 as the source of wording changes; v2.2 changed :264, :267, :270–272 for r2 F17, F24 and F37.
- **Impact:** No result changes. The owner is asked to read both answer tables (:542), and row 10 describes a rule that no longer exists.
- **Proposed change:**
  - :390, :393 → "เลิกใช้เมื่อ v2.x อนุมัติ"; :533 → "หรือ v2.x".
  - Rows 10 and 12 → add "(v2.2, r2 F32: แทนด้วยรายการอนุญาตของจุด mount)".
  - :506 → "ดูชื่อระดับ 0 ของ home และ path `.local/share/containers`".
  - DECISIONS:259 → add "และ `-r2.md` (F17, F24, F37)".
- **Owner decision:** no.

### F48 · Low · Forms of the host lines that will occur are not given
- **Where:** contract :199, :202–207, :253–254 against :183, :244, :345, :39.
- **Evidence:**
  - `cloud storage: <n> (…)` (:199) has no form for a count of 0, which is what this Mac will print (:39: CloudStorage is empty), and no form off darwin.
  - `processes: unreadable (<เหตุ>, errno <n>, <n> pids)` (:202) has mandatory errno and pid slots that do not exist for a failed `DYLD_` or arm64 gate (:183), a missing own PID (:244) or a count of 0. No case asserts an unreadable line.
  - `skipped:` has no zero form.
  - It is not said whether the types in `mounts: <n> (<ชนิดที่พบ>)` are de-duplicated or in what order (12 mounts and three types here).
  - The order and spelling of several `tools:` names are not given, and R1 compares `tools:` as text (:345).
- **Impact:** Limited. R1 compares lines made by the same code on both sides, and the only whole-line case (:382) is fully specified. The gap matters where a test asserts a whole line for an unlisted form, and for the `roots:` line of the AC-01 evidence.
- **Proposed change:** :199–207 → add:
  - `cloud storage: 0`;
  - `processes: unreadable (<เหตุ>[, errno <n>][, <n> pids])` with the reason text for each gate;
  - `skipped: 0 folders`;
  - "ชนิดไม่ซ้ำ เรียงตามลำดับที่พบ";
  - "`tools:` เรียงตามลำดับรายการของ contract คั่นด้วย `, `".
- **Owner decision:** no.

## AC status

No AC changed status. Every v2.x AC is UNKNOWN: no v2.x code or test exists, and `a9b3644..e7cbc38` changes documents only.

| AC | Status | Why |
|----|--------|-----|
| AC-01 (macOS) | UNKNOWN | Owner L4 run not done. Probes show the self-checks can pass on this Mac (own PID path, arm64, no `DYLD_`, 12 allowed mounts). The `tools:` line will not match the predicted one (F42) and the `roots:` form for an empty CloudStorage is unstated (F48). |
| AC-02 | UNKNOWN | The seam now lets the macOS cases be written (F4, F7, F12 closed). Still unsettled: the `host_lines()` cases (F25), mount inputs (F44, F45), the process rule (F33), one rule without a case (F28). |
| AC-03 (macOS) | UNKNOWN | Owner steps not done. C9 now proves what it claims (F14 closed). The Windows run (7)(d2) has no commit pin (F46). |
| AC-04 | UNKNOWN for v2.x | Unchanged by v2.2. |
| AC-05 | UNKNOWN for v2.x | By the text, the locked CLI tests still pass with `host_lines()` printed before `render` (test_ac05:226–231). Not run. |
| AC-06 | UNKNOWN | The darwin checker patch does not exist. The accepted call and its mutations are pinned (F34 closed). |
| AC-07 | UNKNOWN | Not run for v2.x. As written, one `host_lines()` case depends on test order in the full run (F25). |

## Checked and correct (and how)

- **Diff scope.** `git diff --stat a9b3644..e7cbc38`: DECISIONS.md, PROGRESS.md, the contract, `docs/handoff/ENV-002.md`. No code, test, lockfile or locked path. `git status --short` was empty before and after; HEAD is `e7cbc38`.
- **Red flags.** `bash scripts/controls/red-flags.sh main` → "Pattern groups with hits: 0" at `e7cbc38`, 2026-11-18 (each lens and the consolidation). The control files it lists are the seven v1.x locked test files already on the branch.
- **F4, F7 closed.**
  - Each part of r2's option (a) is at contract :173–184.
  - `os.uname`, `os.getpid`, `os.environ` and `ctypes.get_errno` are outside `_ENVCHECK_OS_DENIED` and `_ENVCHECK_CTYPES_DENIED` (test_imports:2737–2751), and the checker has no rule on module-level state.
  - Probe: `proc_listallpids` returned 4 and 8 for capacities 4 and 8, and 784 for 4096; the own PID is listed; `proc_pidpath` of it equals `os.path.realpath(sys.executable)`; pid 0 gives errno 3.
- **F9, F10, F12, F14 closed.** Compared line by line with r2's proposed changes.
  - The locked fake for `is_cloud_only` is False for folders (envkit:286–293), so the ancestor check does not change locked results.
  - `grep 'ปิดหน้าต่าง'` finds only :413 and :445, both in the corrected sense.
- **Mapping to Facts and evaluate.** `classify_processes`, `classify_mounts`, the gates and the F30 rule followed through `_terminal_install` and `_network_shares` (envcheck:498–531): FAIL over UNKNOWN over PASS in every combination read. No path to a wrong PASS was found in the seam.
- **Mount rules as one set** (:268–287), walked against every mount case and against `mount` on this Mac: 12 mounts, at `/`, `/dev` and below `/System/Volumes/` only; one autofs from `map auto_home`. With the rules as written this machine gives PASS for `network_shares` today.
- **Low closures.**
  - F15, F16, F26, F29, F31, F34, F35 against their rule, case and AC lines.
  - F17 against DECISIONS:31 and `docs/architecture.md`:77.
  - F24 against every version label and the runbook steps 2.1–2.2.
  - F37 against envcheck:873, :882–883, :890–891.
  - F38 against PROGRESS.md:5.
  - F39 against PROGRESS.md:7.
  - F40 against :512 and :528.
- **D-023 against the contract.** The whole v2.2 hunk (DECISIONS:261–275) was read; option 1, the order of AC-03 (7) with (d2), and the labels agree. D-023 is "proposed" and tied to contract v2.x (DECISIONS:259).
- **Nothing is presented as approved.** Contract :3–4 say draft; :482 says the delegation is not an approval; the three owner-only answers are marked as waiting (:509, :511, :512); :542 lists them.
- **Wrong-PASS review as an attacker (lens W).** Alternate HOME, Wine or a VM, the Trash and `~/Library`, `.pth` and `DYLD_`, a truncated process or mount list, a portable install in a known prefix. Each is covered by a rule or a named residual, except the mount point below `/System/Volumes/Data` (F32).
- **Consolidating session.**
  - Read the skill file, r2 :1–171 and :440–523, and the contract at `e7cbc38` in full.
  - Read envkit:80–97; test_ac05:80–90, :222–232; envcheck:805–824, :870–895; PROGRESS.md:5–7; DECISIONS:31, :259, :264, :271.
  - Re-ran the diff stat, `git status`, the commit list, the red-flag scan, the `pyproject.toml` and reload `grep` for F25, the existence test of the seven `tools:` paths, `mount`, the `MNT_LOCAL` line of the SDK header, `/usr/share/firmlinks`, and the `/System/Volumes/Data/Users/$USER` test.
  - Did not open the handoff; the lenses opened its findings response only after their first pass, and it changed no finding.

## Not checked (and why)

- **No v2.x code or test exists.** Every closure is judged on the text against the current code and locked tests. The order dependence in F25 is derived from the text and envkit:84–95, not reproduced.
- **The test suite was not run in this round** by any session (r2 recorded 3692 passed at `db6e021`; `e7cbc38` changes documents only, and one lens held back because `uv run` could re-sync `.venv`). `check-locked-paths.mjs`, `test-controls.mjs` and mypy were not run.
- **Private folders.** The F27 walk (contract :41) was not repeated; its counts are the author's. `envcheck` was not run against the real home. No private folder was listed; only the existence of seven named paths under home was tested.
- **F32 is not reproduced.** No disk image was attached, so what the kernel records for a mount point below `/System/Volumes/Data/` is unproven.
- **C9 in practice.** The agent apps were not quit, so "pgrep prints nothing after Quit" is unobserved, as is whether a helper process outlives Quit.
- **MT5, Wine, VMs, containers.** Nothing that needs them was observed: Wine loader names, CrossOver and PlayOnMac layouts, whether `Bottles` is ever a symlink.
- **Servers and other machines.** No server, VPS, broker, old Windows PC or Windows App was touched. No URL was fetched.
- **Credential stores.** The Keychain, `.env` and the contents of `~/.docker` were never read.
- **The owner's original delegation message** is not in the repository; the quote at :482 was compared with PROGRESS.md:7 only.
- **Read in part.** test_ac02, test_imports.py, envkit.py and `tests/unit/app` by search and cited ranges; `docs/architecture.md` at section 6.1 and :65–79. SPEC.md and the ENV-001 and SPIKE-002 contracts were not read.
- **Not judged.** Whether the delegation covers each delegated answer, including running the F27 walk before the owner answered question 1 of r2 (:501 states that the delegation was used).

## Questions for the owner

1. **Binding (decision (ซ), (ฌ)):** do you confirm that the contract reviewer, the test author and the work reviewer of v2.x are fresh Claude sessions, with the re-check of F12–F15 of `ef7881e` folded into the implementation review? If not, this file and r1 and r2 are pre-reviews and Codex must pass P25 on the Mac first.
2. **F32:** narrow the mount allow list below `/System/Volumes/Data/` to the volume itself and `/System/Volumes/Data/home`, or accept a local volume mounted there as a named residual?
3. **F36, decision (ญ):** do you accept each residual, including the three not yet in the list (the old PC before it is wiped, the agent reading the same folders as the checker, the Photos Library skip entry)?
4. **Budget (F36, F40):** do you confirm both numbers, 5 Claude sessions and 8 fresh sessions? The 5 count "2 used" by date; 2026-11-18 had two drafting rounds with review r2 between them. Is that one session or two?
5. **F41, F46:** may a non-PASS report with full folder paths be committed as it is, or do you redact it first? Should the old PC run the v1.9 code at `c97aac6`, or may its report carry the Windows account name and OneDrive folder names?

Ready for the owner's approval (ENV-002 v2.2): no (0 High; 1 Medium first: F25; it changes text the locked tests will be written from; fix Low F28, F30, F32, F33, F43, F44, F45, F48 in the same pass)
Ready for owner decision (D-023): yes on its own text (only the header label under Low F47 remains, and F36 asks that D-023 be on the owner's reading list); its header ties acceptance to contract v2.x, so accept it together with the contract once F25 is closed
Findings open: 14 (0 High · 1 Medium: F25 · 13 Low: F28, F30, F32, F33, F36, F41, F42–F48)
