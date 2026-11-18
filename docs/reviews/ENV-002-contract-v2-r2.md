# Review ENV-002 contract v2.1 round 2 (ENV-002 v2.1 draft, D-023, the D-021 back-reference)

Base: contract v2.0 at `5474cf2` plus review r1 at `aad621a` · head `db6e021` on `chore/ENV-002-macos-research-host` ·
reviewer: four fresh-context Claude reviewer sessions (read-only; lenses: closure of F1–F6, closure of F7–F12,
closure of F13–F24 with every DECISIONS.md edit, whole document), one independent refutation pass per lens,
consolidated by a fifth read-only Claude session · 2026-11-18

**Label: contract review by fresh Claude sessions** under the role swap recorded in PROGRESS.md:5 on 2026-11-18
(the owner's delegated answer 13, contract :428). The session that wrote v2.1 did not review it. This review does
not claim that the separation is secure. The task is High and the owner's own approval is still required. The
binding itself was recorded by the author under the delegation; F38 asks the owner to confirm it, and until he
does he may read this file as a pre-review.

**Ready for the owner's approval: no.** Reasons:
1. No High finding remains. The four High findings of r1 (F1–F4) are answered: F1–F3 are closed, and the mapping
   half of F4 is closed.
2. Eight Medium findings are open. Six are the unfinished parts of r1 findings:
   - the test seam of the darwin process reader (F4, F7);
   - the repeated attestation that R1 cannot obtain and that cannot see command-line VM tools (F9);
   - the reused v1.8 helper that skips every unlistable folder inside a Wine prefix (F10);
   - rules that still have no negative case, including the `DYLD_` gate (F12);
   - the `pgrep` check that prints nothing while the desktop agent apps run (F14).
3. Two Medium findings are new: the darwin CLI lines have no named function and no stated source (F25), and the
   full-depth walk of the search dirs was never measured from Visual Studio Code (F27, a question).
4. All eight change rule text or seams that the locked tests will be written from, so they come before approval.

**Findings open: 27 = 0 High, 8 Medium, 19 Low.** Of the 24 r1 findings, 14 are closed, 10 are closed in part and
none is fully open. 17 findings are new (F25–F41).
Refutation pass over the 54 lens entries: 46 confirmed, 8 confirmed in part, 0 refuted, no closure found wrong.
Severities below are the corrected ones.

How to read the references:
- "contract :NN" is `docs/contracts/ENV-002-research-host-separation.md` at `db6e021`; "DECISIONS:NN" is
  DECISIONS.md at the same commit; "envcheck:NN" is `src/sochron/app/envcheck.py`; "test_imports:NN" is
  `tests/architecture/test_imports.py`; "test_ac02:NN", "test_ac05:NN" and "envkit:NN" are files of
  `tests/acceptance/ENV-002/`; "r1 unit:NN" is `tests/unit/app/test_envcheck_review_r1.py`.
- "Probe" is a read-only shell or `uv run --offline python -I` run on this Mac (arm64, CPython 3.12.15) by a lens
  and repeated by its refutation pass.
- Source ids: A = closure F1–F6, B = closure F7–F12, C = closure F13–F24, W = whole document; the number is the
  entry index in that lens.

How it was verified: each lens read the contract at `db6e021` in full against the code, the locked tests,
DECISIONS.md and the v2.1 diff, and ran read-only probes. The consolidating session re-read the whole contract
(458 lines) and re-opened every line quoted in a Medium finding. The other lines it opened are listed under
"Checked and correct". All quotes matched. Three citations in the lens material were corrected:
- D-023 item 3 is DECISIONS:267, not :264 or :266.
- The handoff reading list is `docs/handoff/ENV-002.md`:506, not :507.
- One lens proposal for F25 was dropped because it would break locked tests (see F25).

No URL was fetched.

## Re-check of r1 findings

| r1 ID | r1 Sev | Status | v2.1 commit | Evidence (one line) |
|----|----|----|----|----|
| F1 | High | closed | `3725880` | contract :148–150: no new field, `reader_name()` and a `reader:` line; envkit:25–33 and test_ac02:140–146 untouched. |
| F2 | High | closed | `a80f1d8` | :247 no `stat` import; :310 names the one checker exception with the diff going to the owner; :405 puts it under decision (จ); DECISIONS:267. Stale lines → F24. |
| F3 | High | closed | `5d3759c` | :270–280 one full-path literal, `DYLD_` gives UNKNOWN, six mutations; probe: the literal loads and the three symbols exist. Mutation gap → F34. |
| F4 | High | partly (Medium) | `e8d8c89` | Mapping :151–159 fits `evaluate` (envcheck:498–531). The raw readers at :168 still have no shape and the F7 rules have no side of the seam. |
| F5 | Medium | closed | `d8e01d1` | :257–262 pins the exception to `st_dev`/`st_ino` of `sys.executable`; probe: the three `.venv/bin` links are the only links and all match. |
| F6 | Medium | closed | `5e511f5` | :245–255 one `is_cloud_only`; probe: the formula gives the locked result for the seven cases of test_ac02:805–813. Two wording points → F12 (7), F24. |
| F7 | Medium | partly (Medium) | `30e01cc` | Rules :212–218, :244 and the control round :332 are in. Six of the nine new cases sit below the seam of :168. |
| F8 | Medium | closed | `e3a7937` | :224–230 lower-case prefix rule (MT4 and MT5), :205 "contains metatrader", cases :321. Follow-up → F28. |
| F9 | Medium | partly (Medium) | `f22a102` | :192–196 Wine roots fixed. The re-attestation of :298 rests on lines `require_research_host` cannot return, and `~/.colima` (:44) is invisible to the note. |
| F10 | Medium | partly (Medium) | `8f4ac02` | Skip list measured (:40, :265–266) and app named (:332, :407). :207 "(helper เดิม)" reuses a walk that skips every refusal (envcheck:577–582). |
| F11 | Medium | closed | `39dcfe2` | :201–203 `_darwin_home()`, no Windows variables, `roots:` line; cases :323. Follow-up → F29. |
| F12 | Medium | partly (Medium) | `a4a8c35` | Every rule r1 listed has a case. Rules added by v2.1 do not: `DYLD_` appears in no case of :313–329. |
| F13 | Medium | closed | `52d5a8e` | :335 (1)(2)(3)(7) name the tool, the evidence and the order; probe: `nc -vz -G 2 127.0.0.1 9` prints the refusal and exits 1. Reason of answer 9 → F37. |
| F14 | Medium | partly (Medium) | `50be103` | Checklist (ก)–(ญ) at :356 is in. Item (ฌ) uses a case-sensitive pattern; :335 and :388 still say "close the window". |
| F15 | Medium | partly (Low) | `dc9fa4f` | Threat row :372, `/Volumes` rule :241, file-list rule are in. The `mounts:` format (:182) has no slot for the mount points :242 says it reports. |
| F16 | Medium | partly (Low) | `afd6321` | The six places r1 named are scoped to the Windows PC. :365 now counts `mt5_package` as a defence on the Mac against :42 and :358. |
| F17 | Medium | partly (Low) | `566abb0` | Back-reference DECISIONS:250, :262, :269 are in. DECISIONS:271 cites "D-001 ข้อ 5", which does not exist. |
| F18 | Low | closed | `7919218` | DECISIONS:269: removal check and tests T1–T4. |
| F19 | Low | closed | `7fbb668` | :233–238, cases :329; `mount` shows `map auto_home` as the only autofs entry. |
| F20 | Low | closed | `ad0f816` | :42, :358, DECISIONS:271. Leftover → F16. |
| F21 | Low | closed | `7f3576b` | :359, taken into the Given of AC-01 (:332, :353). |
| F22 | Low | closed | `f003d82` | :145–147, :398; the named unit test exists at r1 unit:445. |
| F23 | Low | closed | `12ce36e` | :443 sums to 8; PROGRESS.md:5 agrees. Claude-session count → F40. |
| F24 | Low | partly (Low) | `298a00c`, `258efb1` | Most labels fixed. :405 still approves "contract v2.0"; mixed labels in D-023; runbook step numbers; stale lines. |

## Findings (open and new)

| ID | Sev | Kind | File:line | Finding | Owner decision | Sources |
|----|-----|------|-----------|---------|----------------|---------|
| F4 | Medium | confirmed | contract :160–168, :171–173, :235, :275, :319, :334 | Raw readers have no shape or failure contract; gates are not placed relative to the seam | no | A3, W2 |
| F7 | Medium | confirmed | contract :166, :168, :212–215, :319 | Six process cases cannot reach a real rule through the named seam | no | B0 |
| F9 | Medium | confirmed | contract :298, :176, :220–223, :44, :373 | R1 has no call that yields `note:` and `wine:`; the note cannot see command-line VM tools | yes (note scope) | B3, W1 |
| F10 | Medium | confirmed in part | contract :207, :393, :195, :265–266; envcheck:577–582 | "(helper เดิม)" skips unlistable folders inside a Wine prefix; other Wine-chain folders have no rule | no | B4, W4 |
| F12 | Medium | confirmed | contract :275, :254, :205, :208, :217, :224–227 against :313–329, :334 | v2.1 rules without a negative case, among them the `DYLD_` gate | small (one case) | B7, W6, W4 |
| F14 | Medium | confirmed | contract :356 (ฌ), :335, :388 | `pgrep -lf 'claude\|codex'` misses `Claude.app` and `ChatGPT.app`; two lines still say "close the window" | no | C1, W12 |
| F25 | Medium | confirmed | contract :160–161, :175–186, :242, :332; envcheck:860–866, :886 | The darwin CLI lines have no named function, no stated source and no stated layout | no | W0, A6, A7 |
| F27 | Medium | question | contract :40, :198–200, :264, :332 | The full-depth walk of the search dirs was never measured from Visual Studio Code | yes (allow the measurement) | W7, B12 |
| F15 | Low | confirmed | contract :182 against :242 | `mounts:` has no slot for the `/Volumes` mount points | no | C2 |
| F16 | Low | confirmed | contract :365 against :42, :358 | Threat row counts `mt5_package` as a defence on the Mac | no | C3 |
| F17 | Low | confirmed | DECISIONS:271 | "D-001 ข้อ 5" does not exist | no | C4 |
| F24 | Low | confirmed | contract :405, :393, :397, :403, :15, :184, :356; DECISIONS:267, :270, :272 | Version label of the approval item, runbook step numbers, stale lines, reused letters | no | C11, A9, B11 |
| F26 | Low | confirmed | contract :319, :329, :315 against :232, :244, :325, :327; :159 | Mount cases contradict the FAIL rule or omit the flag that decides them | no | B9, C12, W3 |
| F28 | Low | confirmed | contract :226–228, :162, :208, :321, :374; envcheck:885 | The never-listed set has no definition for `load_sentinel`; `never_listed` is untested on default roots | no | B2, B11 |
| F29 | Low | confirmed in part | contract :298–299, :192, :202 | R1 does not record `roots:`; hand-built roots skip the Wine search; who compares is unstated | no | B6, W1 |
| F30 | Low | confirmed | contract :152–154, :211, :217–218, :248–249, :266 | A found FAIL fact is reported as UNKNOWN when the same field is also unreadable | no | B8, W13 |
| F31 | Low | confirmed | contract :244 against :212–213 | The mount reader has no rule against a truncated list | no | B10 |
| F32 | Low | confirmed | contract :241–243, :357, :372 | A volume mounted outside `/Volumes/` passes every rule | yes (rule or residual) | C13 |
| F33 | Low | confirmed | contract :205–206, :208–210, :325, :373 | A `MetaTrader` folder without `.app`, or a bundle below level 0, passes and is not a named residual | yes (rule or residual) | W5, B7 |
| F34 | Low | confirmed in part | contract :278–279, :339 | The mutation list does not pin the keywords of `ctypes.CDLL` | no | A8 |
| F35 | Low | confirmed | contract :308, :332 | The control round contradicts "temporary folders only" and can leave the folders in the Trash | no | B13, W12 |
| F36 | Low | confirmed in part | contract :373, :405–409, :412, :455; handoff :506 | Residuals worded as accepted, no decision line, threat table missing from the owner's reading list | yes (accept per item) | W8 |
| F37 | Low | confirmed | contract :424, :335 (7), :372 | Answer 9 rests on a reason the code contradicts | yes (run or attest) | W9 |
| F38 | Low | confirmed in part | contract :346, :350, :408–409, :428, :453, :455; PROGRESS.md:5 | The binding recorded in PROGRESS is wider than answer 13; (ซ) still reads as open; (ฌ) has no answer | yes (confirm) | W10 |
| F39 | Low | confirmed | contract :412; PROGRESS.md:5 | The owner's delegation is quoted in abridged form inside quotation marks | no | C14 |
| F40 | Low | question | contract :443 | The Claude-session budget of v2.x has no usage count | yes (a number) | C15 |
| F41 | Low | question | contract :179, :200, :203, :423 | `roots:` also prints cloud-storage folder names; answer 8 covers the account name only | yes | W11 |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

### F4 · Medium · Raw readers have no shape or failure contract; the gates are not placed
- **Where:** contract :168, :166, :162, against :160–161, :171–173, :334; :235, :275.
- **Evidence:**
  - :160 "ชื่อและ signature เป็นข้อผูกของ contract", yet :168 gives only "ตัวอ่านดิบ `_darwin_process_paths()` และ `_darwin_mounts()` ที่ tests แทนด้วยตัวปลอม" with no return type or failure contract.
  - :166 `classify_processes(paths)` leaves `paths` untyped.
  - `never_listed` appears only at :162 and is never defined.
  - The arm64 gate ("`os.uname().machine == "arm64"`", :235) and the `DYLD_` gate (:275) are not placed above or below the raw readers.
  - CI is `ubuntu-24.04` (`.github/workflows/ci.yml`:19, :43) and no test fakes `os.uname` today.
- **Impact:** The test author must invent the encodings, which caused the v1.6 question round that r1 F4 cites. A darwin `collect` case written from :334 passes on the Mac and gives UNKNOWN on CI, against AC-07 (:340, same count on both).
- **Proposed change:** Add under :160–168:
  - (a) Recommended, puts every F7 rule above the seam. Raw functions that hold only ctypes calls: `_darwin_list_pids(capacity: int) -> tuple[int, tuple[int, ...]]` (count returned by the call, pids), `_darwin_pid_path(pid: int) -> tuple[str | None, int]` (path, errno), and `_darwin_mounts() -> tuple[tuple[str, str, str, int], ...]`. Each raises OSError when the call fails.
  - A pure `read_process_paths(own_pid: int, own_path: str) -> tuple[str, ...]` holds the regrow loop, the pid 0 and ESRCH skip, the other-errno rule and the own-PID check, and raises OSError when the list is unreadable.
  - (b) Alternative: `_darwin_process_paths() -> tuple[tuple[int, str | None, int], ...]` and `classify_processes(entries, own_pid, own_path)`. The cases "คืน 0" and "เท่าความจุ buffer" are then tested by replacing `envcheck.ctypes.CDLL` with a fake loader.
  - Either way, state: "`never_listed: tuple[Path, ...]`"; "การตรวจ `DYLD_*` และ `os.uname().machine` อยู่ใน `collect` ก่อนเรียกตัวอ่านดิบ · tests ของ collect ตั้ง `envcheck.os.uname` ปลอม"; and which function raises OSError so that `collect` gives None.
- **Owner decision:** no.

### F7 · Medium · Six process cases cannot reach a real rule through the named seam
- **Where:** contract :212–215, :319, against :166, :168, :171–173, :334.
- **Evidence:**
  - The rules need pids, errno values and the buffer capacity: :212–215 "จำนวน pid ที่คืนเท่ากับความจุของ buffer", "ล้มด้วย ESRCH", "ตัวอ่านต้องพบ PID ของตัวเอง (`os.getpid()`)".
  - :319 lists as AC-02 cases: own PID missing, own path differs, ENOMEM, ESRCH, "`proc_listallpids` คืน 0", "จำนวน pid เท่าความจุ buffer".
  - :334 binds them to "`collect` ที่ตั้ง platform เป็น `darwin` พร้อมตัวอ่านดิบปลอม".
  - With the raw reader faked, two cases (returns 0, buffer full) are inside the replaced function. The other four are undefined because `classify_processes(paths)` receives paths only.
  - v1.9 tested this class on Windows in implementer unit tests (r1 unit:219–247), which :172–173 rules out here: "ไม่ใช่ unit test ของ implementer อย่างเดียว เพราะงานนี้ High".
- **Impact:** The self-check that closed r1 F7 (a reader that reads nothing, or a truncated list, must not pass) stays outside every locked test.
- **Proposed change:** The F4 change, plus a mark on each case of :319 naming the function it is asserted on. F7 closes with F4.
- **Owner decision:** no.

### F9 · Medium · R1 cannot obtain the lines it must record; the note cannot see command-line VM tools
- **Where:** contract :298, :176, :148, :220–223, :44, :373; envcheck:812–822.
- **Evidence:**
  - :298 "จุดเริ่มของ R1 เรียก `require_research_host(sentinel=…)` … บันทึกบรรทัด `note:` และ `wine:` ของ envcheck คู่กับ verdict ด้วย".
  - That function returns a Report (envcheck:812–822) and :148 forbids new fields.
  - :176 has the lines printed by `main` "จากฟังก์ชันระดับโมดูลแยก ไม่ผ่าน Facts"; none of those functions is in the binding list :160–168.
  - :44 "มีโฟลเดอร์ `~/.colima`", while the note lists level-0 app names only and :223 says command-line tools are ones "ซึ่ง note นี้ไม่เห็น".
  - The residual at :373 still relies on "คำยืนยันซ้ำของเจ้าของตามบรรทัด `note:`".
- **Impact:** The trigger chosen for delegated answer 6 has no implementable seam, so r1's impact ("a VM installed after ENV-1 is never attested again") stands until SLICE-R1 invents one. For colima, lima, podman and qemu the note never changes, and one of them is already on this Mac.
- **Proposed change:**
  - Name the function of F25 in :298 as what R1 calls after `require_research_host`.
  - Say who compares the lines with the ENV-002 evidence (code or owner).
  - Either extend the note with level-0 names of home that mark such tools (`.colima`, `.lima`, `.docker`, `.orbstack`, `.wine`, `.local/share/containers`; names only, one case), or state in :373 that tools installed by command line never trigger a re-attestation.
- **Owner decision:** yes (extend the note, or accept the stated residual).

### F10 · Medium · "(helper เดิม)" skips unlistable folders inside a Wine prefix
- **Where:** contract :207, :393, :195, against :265–266; envcheck:577–582.
- **Evidence:**
  - :207 "`terminal64.exe` ระดับ 0–2 ใต้ program_files แต่ละตัว (helper เดิม)" and :393 "ใช้ helper ค้น `terminal64.exe` … เดิม".
  - That helper skips every refused folder below its root: envcheck:577–582 `except OSError: if level == 0: raise` then `continue`.
  - :265–266 says "ข้ามได้เฉพาะโฟลเดอร์ที่ list ไม่ได้ซึ่งอยู่ในรายการ … โฟลเดอร์อื่นใต้ home ที่ list ไม่ได้ = … `terminal_paths` = None", and every Wine prefix is under home.
  - :195 gives a result only for `wineprefix` and `Bottles`. A prefix folder, its `drive_c`, `~/.wine`, `~/Library/PlayOnMac` or the CrossOver folder that exists but cannot be listed, or is a symlink, has no stated result. "No Program Files found" is PASS by :192.
  - The cases at :325 cover only folders the home walk reaches.
  - Not upheld: the claim that the text allows calling `find_terminal_paths` with non-empty roots. :162 names the darwin function and the :325 audit-hook case would fail.
- **Impact:** A straight reuse passes every listed case while a mode-000 folder under `drive_c/Program Files`, or an unreadable `drive_c`, hides a terminal and `terminal_install` is PASS. The same user can do that without admin rights, which is the premise r1 F10 rejected for macOS. The added exposure is small: a prefix must already exist in a known place and shows in the `wine:` count.
- **Proposed change:**
  - :207 → add "โฟลเดอร์ที่ list ไม่ได้ใต้ program_files root บน darwin = `terminal_paths` None (ไม่ใช้กฎข้ามของ v1.8)".
  - :195 → "`~/.wine`, โฟลเดอร์ prefix, `drive_c`, `~/Library/PlayOnMac` และ `~/Library/Application Support/CrossOver` ที่มีอยู่แต่ list ไม่ได้ หรือเป็น symlink ทำให้ `default_roots` ยก OSError เช่นกัน".
  - Add cases: an unlistable folder at level 1 of `drive_c/Program Files` (UNKNOWN), an unlistable `drive_c` (OSError), a prefix with no `drive_c` (PASS).
- **Owner decision:** no.

### F12 · Medium · v2.1 rules that still have no negative case
- **Where:** contract :313–329 and :334, against :275, :254, :205, :208, :217, :224–227, :178–183, :252.
- **Evidence:** AC-02 binds only listed cases (:334 "ทุกกรณีของ macOS ในหัวข้อ Negative cases … ให้ผลตามที่เขียนไว้"). Missing:
  1. :275 "`os.environ` มีตัวแปรที่ขึ้นต้นด้วย `DYLD_` = โปรเซสและ mount อ่านไม่ได้". `DYLD_` occurs at :154, :159, :273, :275, :354, :375, :418 and in no case.
  2. :254, a dataless folder under a terminal-search root ("ข้ามและนับในบรรทัด `skipped:`"). :317 covers iCloud Drive and `<repo>/data/` only.
  3. `/Applications` or `~/Applications` missing or unlistable: no rule at :205 and no case. The v1.9 root rule (:135) names other roots; applied here it would make a Mac without `~/Applications` UNKNOWN forever.
  4. The `.git`, `.venv`, `node_modules` skip of the new darwin walk (:208).
  5. A name equal to `metaquotes`, and near misses such as `metaquotes2` (:224–225).
  6. `wineserver` (:217), and `load_sentinel` not opening a file under a terminal_data folder (:226–227).
  7. A root whose ancestor is dataless (:252 forbids a stat below a dataless folder; the check of the root is such a stat).
  8. The lines `reader:`, `processes:`, `mounts:`, `wine:` (:178–183), on which AC-01 rests.
  - :334 names only `evaluate` or `collect`, while cases at :315, :323, :325 need `default_roots` or `main`.
- **Impact:** Each rule can be left out or built wrongly with every acceptance test green. For (1) and (2) the mistake gives PASS. (1) is the fail-closed half of the answer to r1 F3 (High).
- **Proposed change:** Add cases:
  - `DYLD_INSERT_LIBRARIES` set (UNKNOWN of `terminal_install` and `network_shares`, raw readers not called);
  - a dataless folder at level 1 of home (not listed, named in `skipped:`, PASS);
  - `~/Applications` missing (PASS) and `/Applications` unlistable (UNKNOWN), with the rule written at :205;
  - `terminal64.exe` under `<home>/x/.git/` (PASS);
  - `MetaQuotes` (FAIL), `metaquotes2` and `my metatrader` (PASS);
  - `wineserver` (UNKNOWN);
  - `--sentinel-file` under `<appdata>/Metatrader 5/` (not opened);
  - a root with a dataless ancestor (UNKNOWN);
  - the four CLI lines with their counts.
  - In :334 write "`evaluate`, `collect`, `default_roots`, `main` หรือฟังก์ชันระดับโมดูลของตัวอ่าน darwin".
- **Owner decision:** no, except F33 for the folder without `.app`.

### F14 · Medium · The `pgrep` check misses the desktop agent apps; two lines still say "close the window"
- **Where:** contract :356 (ฌ), :335, :388.
- **Evidence:**
  - :356 "Quit แอปของ Claude และ Codex ทุกตัว (ไม่ใช่แค่ปิดหน้าต่าง) แล้ว `pgrep -lf 'claude|codex'` ต้องไม่พิมพ์อะไร".
  - :335 "โดยปิดหน้าต่าง agent ก่อน"; :388 "(ปิดหน้าต่าง agent ก่อน)".
  - Probe: `/Applications` holds `Claude.app`, `ChatGPT.app`, `Visual Studio Code.app` (names only).
  - Probe: the two bundle executable paths piped through `grep -c -E 'claude|codex'` give 0.
  - `man pgrep`: "-i Ignore case distinctions". The refutation pass saw `pgrep -f 'visual studio'` match 0 processes and `pgrep -f 'Visual Studio'` match 19.
  - The Codex tooling here is named `chatgpt`, which the pattern lacks.
  - `man pgrep` -a: pgrep excludes its own ancestors, so a run from inside an agent session does not list that agent.
  - Limit: neither desktop app was running, so the result rests on the bundle paths. The text of (ฌ) is r1's own proposal copied verbatim.
- **Impact:** macOS keeps an app running after its window closes. The owner can truthfully record "pgrep printed nothing" while a desktop agent app runs. This command is the only evidence-producing step for decision (ค), the mitigation of the threat rows at :366 and :376.
- **Proposed change:**
  - (ฌ) → "ก่อนเปิด RDP หรือ console: Quit (⌘Q) Visual Studio Code, Claude, ChatGPT/Codex และทุกแอปที่ agent รันอยู่ แล้วรันใน Terminal.app: `pgrep -ilf 'claude|codex|chatgpt'` ต้องไม่พิมพ์อะไร · เปิด console ใน browser หรือ profile ที่ไม่มี extension ของ Claude หรือ ChatGPT; ถ้ามี ให้รัน pgrep ซ้ำหลังเปิด browser".
  - :335 → "โดย Quit แอปของ agent ตาม checklist ข้อ (ฌ) ก่อน".
  - :388 → "(Quit แอปของ agent ตาม checklist ข้อ (ฌ); บน macOS การปิดหน้าต่างไม่พอ)".
- **Owner decision:** no.

### F25 · Medium · The darwin CLI lines have no named function, source or layout
- **Where:** contract :160–161, :175–186, :242, :332, :150; envcheck:860–866, :886–890; test_ac05:84–88.
- **Evidence:**
  - Names and signatures are binding (:160), and none of :162–168 can return what :181–185 and :242 print (pid counts, errno, skipped folders, wine-loader count, `/Volumes` mount points).
  - :176 says only "`main` พิมพ์เป็นบรรทัดของ CLI จากฟังก์ชันระดับโมดูลแยก ไม่ผ่าน Facts (`render`, Report และ Item ไม่เปลี่ยน".
  - `main` holds a Report only (envcheck:886). `render` returns title, items, an optional `note: {note}` and the last line as one string (envcheck:860–866).
  - :180 puts the new lines "หลังรายการ item ก่อนบรรทัดสุดท้าย" while :150 says "`render` ไม่เปลี่ยน".
  - :185 adds a second line starting with `note:`, and :222 and :298 key the re-attestation on "บรรทัด `note:`".
  - The `default_roots` OSError path prints a fixed text (envcheck:887–889); whether `reader:` precedes it is unstated.
  - The locked CLI tests replace only `collect`, `default_roots` and `is_cloud_only` (test_ac05:84–88) and call `main` on the real platform.
- **Impact:**
  - Implementer and test author must guess between a second OS read in `main` and state kept by `collect`.
  - With a second read, "`paths read` มากกว่า 0" and the mount comparison of AC-01 (:332) do not describe the read that produced the verdict, and the locked AC-05 tests would read the real process list and `/Applications` on the Mac, against :308.
  - With kept state, the lines are undefined when `collect` is a fake.
  - The cases that assert on `skipped:` and `note:` (:315, :325) cannot be written until this is fixed.
  - No wrong PASS: the self-checks sit in the reader.
- **Proposed change:** Add to :175–186:
  - "`collect` บน darwin เก็บสรุปของการอ่านรอบล่าสุดไว้ในตัวแปรระดับโมดูล · `host_lines() -> tuple[str, ...]` คืนบรรทัด `reader:`, `roots:` และบรรทัด darwin ของการอ่านรอบนั้น ไม่อ่าน OS เอง และไม่ยก exception · เมื่อ `collect` ไม่ได้รันตัวอ่าน darwin (ถูกแทนใน tests) คืน `processes: not read`, `mounts: not read`".
  - "`main` พิมพ์ `reader:` และ `roots:` ก่อนข้อความของ `render` และแทรกบรรทัด darwin ก่อนบรรทัดสุดท้าย (`render(report, note)` คง signature และผลเดิม)".
  - "เมื่อ `default_roots` ยก OSError: พิมพ์ `reader:` แล้วข้อความเดิมของ v1.9".
  - Rename the new line to `apps: <ชื่อ หรือ none>` at :185, :220–222, :298, :315.
  - Not carried: one lens proposed that `main` call a new `collect_darwin` directly. That would bypass the fake `collect` of test_ac05:84–88 and fail locked tests on the Mac.
- **Owner decision:** no.

### F27 · Medium · question · The walk of the search dirs was never measured from Visual Studio Code
- **Where:** contract :40, :198–200, :264, :332.
- **Evidence:**
  - The only measurement (:40) is the terminal walk: "การค้น home ระดับ 0–3 แบบดูชื่อโฟลเดอร์เท่านั้น ไม่เข้า `Library`, `.ssh`, `.gnupg`, …", with "`.gnupg` ไม่ได้วัด (ตัววัดไม่เข้า แต่กฎของ contract เข้า)".
  - `evaluate` walks Desktop, Documents, Downloads, iCloud Drive (under `~/Library`, :199) and CloudStorage at every depth.
  - :264 says "ใน repo, data dirs, search_dirs = UNKNOWN" for any folder that cannot be listed, with no skip list.
  - AC-01 allows Files and Folders only, "ไม่มี Full Disk Access" (:332).
  - No reviewer walked those folders (private; a Privacy prompt could be raised). Whether iCloud Drive holds a protected `.Trash` is from memory, not measured.
- **Impact:** One refused folder at any depth makes `sentinel` UNKNOWN on every run. AC-01 then cannot pass without Full Disk Access, which decision (ช) forbids. This is found only at the L4 run, after the tests are locked, which is the v1.8 pattern. Fail-closed, so no wrong PASS.
- **Severity note:** One refutation pass rated this Low and the other Medium. It is kept at Medium because the cost of a late discovery is a contract revision.
- **Proposed change:** Before approval, repeat the 2026-11-18 probe for this walk: names only, full depth, the five search-dir roots and `~/.gnupg`, inside Visual Studio Code. Record the count and refused paths at :40. If a folder is refused, the owner decides per path (clear it, or a named skip entry with the gap added to :374).
- **Owner decision:** yes (allow the measurement; decide any refused path).

### F15 · Low · `mounts:` has no slot for the `/Volumes` mount points
- **Where:** contract :182 against :242; cases :327.
- **Evidence:** :242 "บรรทัด `mounts:` บอกจุด mount ที่เข้ากฎนี้"; the only format is :182 "mounts: <n> (<ชนิดที่พบ>)". :327 asserts a status only.
- **Impact:** A report that turns UNKNOWN because of a disk image does not tell the owner which volume to eject.
- **Proposed change:** :182 → "mounts: <n> (<ชนิดที่พบ>)[; under /Volumes: <จุด mount>, …]" and add the case "บรรทัด `mounts:` มี `/Volumes/USB`".
- **Owner decision:** no.

### F16 · Low · The threat row counts `mt5_package` as a defence on the Mac
- **Where:** contract :365 against :42, :358.
- **Evidence:** :365 "บน Mac … การป้องกันคือ item `terminal_*` และ `mt5_package` ก่อนทุก R1"; :42 "`mt5_package` บน darwin จึงผ่านเสมอ ไม่นับเป็นหลักฐาน". The sentence is r1 F16's proposal copied verbatim; r1 F20 removed the same claim elsewhere.
- **Impact:** The owner accepts the threat table on approval, and this row lists a check that cannot fail on macOS as a defence.
- **Proposed change:** :365 → "การป้องกันคือ item `terminal_*` ก่อนทุก R1 และกฎห้ามติดตั้งของ Invariants (`mt5_package` บน darwin ไม่นับ: F20)".
- **Owner decision:** no.

### F17 · Low · "D-001 ข้อ 5" does not exist
- **Where:** DECISIONS:271.
- **Evidence:** "trigger ของ D-001 ข้อ 5 (host ที่ไม่ใช่ Windows) ไม่ถูกแตะ". D-001's only numbered list is "Before accepting" 1–4; the trigger is its line "Review when: ต้องย้ายไป host ที่ไม่ใช่ Windows" (DECISIONS:31) and `docs/architecture.md`:77, which is in section 5.
- **Impact:** A reader who looks for item 5 of D-001 finds nothing.
- **Proposed change:** → "trigger ของ D-001 (บรรทัด Review when: \"ต้องย้ายไป host ที่ไม่ใช่ Windows\"; `docs/architecture.md` ข้อ 5) ไม่ถูกแตะ เพราะ …".
- **Owner decision:** no.

### F24 · Low · Version label of the approval item, runbook step numbers, stale lines
- **Where:** contract :405, :393, :397, :403, :15, :184, :356/:376; DECISIONS:264, :267, :270, :272.
- **Evidence:**
  - (a) :405 "(จ) อนุมัติ contract v2.0 (High)" while :4 says v2.1. DECISIONS:267 has "ตาม contract v2.1" and "contract ENV-002 v2.0" in one item; :270 "contract v2.0"; :272 "ENV-002 v2.0"; the header :259 says "v2.x".
  - (b) :393 "ข้อ 1 และ 5 บน VPS คงเดิม" against :3 "runbook ข้อ 1 fetch branch `chore/ENV-002-macos-research-host`"; the runbook fetches the feat branch (`docs/runbooks/ENV-002-research-host.md`:15).
  - (b) :393 "ข้อ 2–4 ฉบับ macOS" against DECISIONS:264 "ขั้นเดิมของ runbook ENV-002 ข้อ 2.1–2.2", which are the Windows steps the old PC still needs.
  - (c) :397 "patch ของกรณี macOS และ allow list" against :48 "allow list ของ stdlib ไม่เปลี่ยน".
  - (c) :15 describes the patch as adding rules, while :310 lets it change functions and constants of the locked checker.
  - (c) :403 "ช้าเพราะ `~/Library` ใหญ่" against :209 "ไม่เข้า `~/Library` ทั้งโฟลเดอร์".
  - (c) :184 describes `skipped:` as the F10 folders only, while :254 also counts dataless folders there.
  - (d) The checklist letters (ก)–(ญ) reuse the decision letters (ก)–(ฌ): :356 item (ค) cites "ENV-001 (ค)", :376 "checklist (ก)–(ญ) … decision (ค)".
- **Impact:** The owner approves under an item that names v2.0, the draft in which r1 found four High defects. No result changes.
- **Proposed change:**
  - :405 → "อนุมัติ contract v2.1".
  - DECISIONS:267, :270, :272 → "contract ENV-002 v2.x".
  - :393 → "ข้อ 1 และ 5 บน VPS คงเดิม ยกเว้นชื่อ branch ในข้อ 1 · ขั้นของเครื่อง Windows เดิม (ข้อ 2.1–2.2 เดิม และ AC-03 ข้อ 7) ย้ายไปหัวข้อใหม่ท้าย runbook"; DECISIONS:264 cites that section.
  - :397 → "patch ของกรณี macOS และของตัวตรวจ ctypes ของ envcheck".
  - :15 add "(v2.1, F2) patch ของ v2.x แก้ฟังก์ชันและค่าคงที่ของตัวตรวจ ctypes ที่ล็อกแบบแคบ: เจ้าของอนุมัติ diff ก่อน apply".
  - Delete the `~/Library` clause at :403.
  - :184 → "โฟลเดอร์ที่ข้าม: ในรายการข้ามที่ list ไม่ได้ และโฟลเดอร์ dataless".
  - Number the checklist C1–C10.
- **Owner decision:** no.

### F26 · Low · Mount cases contradict the FAIL rule or omit the deciding flag
- **Where:** contract :319, :329, :315, :159 against :232, :233, :244, :325, :327; envcheck:130–136, :524–531.
- **Evidence:**
  - :319 "`/` ที่ชนิดไม่ใช่ `apfs` หรือไม่มี MNT_LOCAL (UNKNOWN)".
  - :232 fails any "mount ที่ไม่มี flag MNT_LOCAL และชนิดไม่ใช่ autofs"; :325 "mount ชนิด `apfs` ที่ไม่มี MNT_LOCAL (FAIL)"; :327 "(FAIL: กฎ FAIL มาก่อน)"; `_status` gives FAIL over UNKNOWN (envcheck:130–136).
  - So `/` as apfs without MNT_LOCAL, or `/` as nfs, is FAIL by rule and UNKNOWN by case.
  - :329 "`ntfs` หรือ `lifs` (UNKNOWN)" and :315 "ชนิดที่ไม่รู้จัก (UNKNOWN)" give no flag.
  - :315 "มีแต่ `apfs`, `devfs`, `autofs` (PASS)" predates :233 and :244.
  - :159 lists the None cases without the missing `/` or the non-arm64 machine.
- **Impact:** A locked test written from :319 and code written from :232 disagree. Every reading is non-PASS.
- **Proposed change:**
  - State once: "ลำดับต่อ mount: กฎ FAIL → กฎ UNKNOWN · ผลรวม: FAIL ชนะ UNKNOWN".
  - :319 → "รายการ mount ไม่มี `/` (UNKNOWN) · `/` ชนิด `hfs` ที่มี MNT_LOCAL (UNKNOWN) · `/` ชนิด `apfs` ที่ไม่มี MNT_LOCAL (FAIL)".
  - :329 and :315 add "ที่มี MNT_LOCAL".
  - :315 → "มีแต่ `/` ชนิด `apfs`, `devfs` และ `autofs` จาก `map auto_home` (PASS)".
  - :159 add "ไม่พบ `/` ตามกฎ F7 หรือเครื่องไม่ใช่ arm64".
- **Owner decision:** no.

### F28 · Low · The never-listed set has no definition for `load_sentinel`; `never_listed` is untested on default roots
- **Where:** contract :226–228, :156, :162, :208, :321, :374; envcheck:885–886.
- **Evidence:**
  - :226–227 "path จริงที่พบ … คือชุดที่ไม่ถูก list และไม่ถูกเปิด ทั้งในการค้น terminal, ใน evaluate และใน `load_sentinel`".
  - Facts carries only a bool (:156), and `main` calls `load_sentinel(…, appdata=roots.appdata)` before `collect` runs (envcheck:885–886).
  - :228 gives evaluate a second definition by name "บนทุกแพลตฟอร์ม", while the win32 fact stays at `<appdata>/MetaQuotes` only (:142, :230).
  - Matches of terminal_data sit under `~/Library`, which the home walk no longer enters (:209). The `never_listed` parameter therefore does nothing on default roots, and the case at :321 passes through the Library skip alone.
  - The residual at :374 does not say it includes the two cloud search dirs under `~/Library`, or `~/.ssh`.
- **Impact:** Implementer and test author must guess. With the win32 reader, a folder such as `<appdata>\MetaTrader backup` under a covering data dir is skipped by evaluate while `terminal_data` stays PASS. No wrong PASS on the Mac.
- **Proposed change:**
  - One sentence per consumer: the terminal search receives the found paths; evaluate and `load_sentinel` compare the lower-cased name of the level-0 entry of `roots.appdata` with the rule.
  - A folder evaluate skips by the new names adds UNKNOWN to every item that searches that root.
  - :321 add "(appdata อยู่นอก `<home>/Library` ในกรณีนี้)".
  - :374 add "รวม iCloud Drive, `~/Library/CloudStorage` และ `~/.ssh`".
- **Owner decision:** no.

### F29 · Low · R1 does not record `roots:`; hand-built roots skip the Wine search
- **Where:** contract :298–299, :192, :202.
- **Evidence:**
  - :298 records the verdict, `note:` and `wine:` only; the home is checked by the owner in AC-01 alone.
  - Probe: with `HOME=/tmp/elsewhere`, `os.path.expanduser("~")` returns that path.
  - :299 "จุดเริ่มของ R1 สร้าง `ResearchRoots` ชุดเดียว" does not say how. On darwin `program_files=()` is accepted (:192) where Windows gives UNKNOWN.
  - Not upheld: "still records PASS" in the usual case. A home without Downloads, Desktop, Documents or Application Support gives UNKNOWN.
- **Impact:** A hardening gap for the R1 record. A PASS needs an alternate home that already holds the four folders.
- **Proposed change:** :298 add "บันทึกบรรทัด `roots:` ด้วย · home ต่างจากหลักฐานของ ENV-002 = ไม่รัน · R1 สร้าง roots ด้วย `default_roots(extra_data_dirs)` เท่านั้น". :202 add the form of `roots:` when `default_roots` raises.
- **Owner decision:** no.

### F30 · Low · A found FAIL fact is reported as UNKNOWN when the same field is unreadable
- **Where:** contract :152–154, :211, :217–218, :266, :248–249; envcheck:510–513.
- **Evidence:**
  - A running `terminal64.exe` outside a matching app is a FAIL only through `process_names` (:211; envcheck:510–513), which the Wine-loader rule sets to None (:153–154).
  - :266 sets `terminal_paths` to None for an unlistable folder, dropping hits found in the same walk.
  - :248–249 makes `.<ชื่อ sentinel>.icloud` FAIL under a search dir but UNKNOWN under the repo or a data dir.
- **Impact:** No wrong PASS. The test author has no expected status for combined cases, and the owner reads "could not be read" where a terminal was seen.
- **Proposed change:** State "path ที่พบแล้วอยู่ใน `terminal_paths` เสมอ และเมื่อมี path ที่พบ การค้นที่ไม่ครบไม่เปลี่ยนเป็น None · โปรเซสชื่อ `terminal64.exe` ถูกใส่ใน `terminal_paths` ด้วย path เต็ม · `.<ชื่อ sentinel>.icloud` = FAIL ทุกพื้นที่", with one case each (for example "`terminal64.exe` พร้อม `wineserver` (FAIL)").
- **Owner decision:** no.

### F31 · Low · The mount reader has no rule against a truncated list
- **Where:** contract :244 against :212–213.
- **Evidence:** Processes have the regrow rule; mounts have only the `/` check. `man getfsstat`: the buffer is filled "up to the size specified by bufsize". Probe: a one-entry buffer returns 1 and that entry is `/`, apfs, MNT_LOCAL, so :244 is satisfied.
- **Impact:** A short buffer drops later mounts (a share mounted late) and passes. The AC-01 comparison with `mount` catches it once, not at each R1.
- **Proposed change:** :244 add "จำนวน mount ที่คืนเท่ากับความจุของ buffer = ขยายแล้วอ่านใหม่ · บรรทัด `mounts:` บอกจำนวนที่อ่านได้", with a case.
- **Owner decision:** no.

### F32 · Low · A volume mounted outside `/Volumes/` passes every rule
- **Where:** contract :241–243, :357, :372.
- **Evidence:** `man hdiutil`: "-mountpoint path … instead of in /Volumes", "-mountroot path"; `man diskutil`: "mount … [-mountPoint path]". Such a volume is a local type with MNT_LOCAL. The measured set is `/`, `/dev` and `/System/Volumes/*` (:242–243). No image was attached.
- **Impact:** The purpose of answer 10 holds only for the default mount directory. It needs a deliberate option and the check is point-in-time.
- **Proposed change:** Either an allow list ("mount ที่จุด mount ไม่ใช่ `/`, `/dev` หรือใต้ `/System/Volumes/` = UNKNOWN", with a case at `/Users/x/mnt`), or add to the residual column of :372 "volume ที่ mount นอก `/Volumes/` ด้วย `-mountpoint` ตรวจไม่เจอ".
- **Owner decision:** yes.

### F33 · Low · A `MetaTrader` folder without `.app`, or a bundle below level 0, passes
- **Where:** contract :205–206, :208–210, :325, :373.
- **Evidence:** :325 "บน darwin ปล่อยไว้ไม่กำหนดผล". The app rule is level 0 of two folders with `.app`; the home walk matches `terminal64.exe` only. :373 does not name this residual.
- **Impact:** `/Applications/MetaTrader 5/MetaTrader 5.app` or `~/Downloads/MetaTrader 5.app` that was never launched gives PASS on every item. After the first launch `terminal_data` fails, so exposure is small.
- **Proposed change:** "รายการระดับ 0 ของ /Applications หรือ ~/Applications ที่ชื่อมี `metatrader` (มีหรือไม่มี `.app`) = FAIL", and add to :373 "แอป MetaTrader ที่อยู่นอกระดับ 0 ของสองโฟลเดอร์แอปและยังไม่เคยเปิด ตรวจไม่เจอ".
- **Owner decision:** yes (rule or residual).

### F34 · Low · The mutation list does not pin the keywords of `ctypes.CDLL`
- **Where:** contract :278–279, :339; test_imports:2796–2800.
- **Evidence:** The mutations vary only the first argument and the function name. The locked Windows resolver checks only that the first positional argument is a literal (test_imports:2799). Probe: `CDLL.__init__(self, name, mode=4, handle=None, use_errno=False, …)`. Without `use_errno=True`, `ctypes.get_errno()` stays 0. The rule text (:276, :339) already refuses other forms; only the listed mutations are missing.
- **Impact:** A checker written to the listed mutations can accept `handle=` or a call without `use_errno=True`. The second turns the errno rules into a permanent UNKNOWN with no explanation.
- **Proposed change:** Add mutations: the literal without `use_errno=True`, with `use_errno=False`, with `handle=h`, with `mode=m`. At :271 add "ไม่มี argument อื่นนอกจาก literal และ `use_errno=True`".
- **Owner decision:** no.

### F35 · Low · The control round against "temporary folders only", and the Trash
- **Where:** contract :308, :332.
- **Evidence:** :308 "กรณีของ macOS ทดสอบด้วยโฟลเดอร์ชั่วคราวและค่าปลอมเท่านั้น" against :332, where the owner creates two empty folders in the real home. "ลบสองโฟลเดอร์" names no method, and "ล้าง Trash ก่อนรัน" comes earlier.
- **Impact:** By the letter the runbook step breaks an invariant. A Finder delete leaves both folders in the Trash for the PASS run (they are empty, so no rule matches).
- **Proposed change:** :308 add "ยกเว้นรอบควบคุมของ AC-01". :332 → "ลบสองโฟลเดอร์ด้วย `rmdir` (ไม่ลากลง Trash) แล้วตรวจด้วย `ls -d` ว่าไม่มี".
- **Owner decision:** no.

### F36 · Low · Residuals worded as accepted; no decision line; threat table missing from the reading list
- **Where:** contract :373, :405–409, :412, :455; `docs/handoff/ENV-002.md`:506.
- **Evidence:**
  - :373 "**รับไว้ (v2.1, F7):**" in an unapproved draft.
  - v1.x had decision (ค) for residuals (:388); (จ)–(ฌ) have none.
  - :455 "เจ้าของอ่าน AC-01, AC-03 และตารางคำตัดสิน" (same at handoff :506), without the threat table. :412 does say the owner accepts the residuals on approval.
  - The rule sentence at :412 ("เพิ่มได้แค่ UNKNOWN หรือ FAIL ไม่เพิ่ม PASS") does not describe answers 6 (receipts half), 7 (drops `~/Library` from the walk, residual at :374) and 9 (drops a check).
- **Impact:** The owner can approve without reading the residuals that approval accepts.
- **Proposed change:**
  - Add "(ญ) ความเสี่ยงที่เหลือของ v2.x · เจ้าของรับหรือไม่รับทีละข้อ" with each new residual and its threat row.
  - :373 → "**เสนอให้รับ (รอเจ้าของ):**".
  - :455 and handoff :506 add the threat table.
  - Reword :412 to name answers 6, 7 and 9 as ones that drop a check.
- **Owner decision:** yes.

### F37 · Low · Answer 9 rests on a reason the code contradicts
- **Where:** contract :424, :335 (7), :372; envcheck:882–890.
- **Evidence:** :424 "การรันต้องตั้งค่า sentinel บนเครื่องที่กำลังจะล้าง". The CLI runs without a sentinel and prints every item (envcheck:882–883, :890). AC-03 (7)(c)(d) are attestation only, and :372 names only the period before the wipe.
- **Impact:** The owner is told the optional check needs a sentinel set-up; it needs one command. The clean-up of the machine holding the post-cutoff cache rests on attestation without being named as a residual.
- **Proposed change:** Either add to AC-03 (7) one run of `python -m sochron.app.envcheck --role research` on the Windows clone before (e), with `terminal_install`, `terminal_data`, `network_shares` at PASS. Or correct :424 to "งานของเจ้าของน้อยกว่า; หลักฐานของ (c)(d) เป็นคำยืนยันเท่านั้น" and add that sentence to :372.
- **Owner decision:** yes.

### F38 · Low · The recorded binding is wider than answer 13; (ซ) reads as open; (ฌ) has no answer
- **Where:** contract :428, :408–409, :346, :350, :453, :455; PROGRESS.md:5; `docs/HANDBOOK-CORE.md`:124.
- **Evidence:**
  - Row 13 answers the contract reviewer only. PROGRESS.md:5 records "ผู้ตรวจ contract, ผู้เขียน tests และผู้ตรวจ = Claude session ใหม่คนละ session (… Codex บน Mac ยังไม่ผ่าน P25)".
  - (ซ) at :408 still reads "**แนะนำ:** Codex ตาม D-002 ถ้าใช้ได้บน Mac". Its fallback clause is what PROGRESS did, so the text is not contradicted.
  - :453 lists "(จ)–(ฌ)" as missing and :455 only "(จ)". (ฌ) has no row.
  - HANDBOOK-CORE:124: "High also requires Codex-written tests first."
- **Impact:** The maker of a High task recorded who writes its locked tests and reviews it. The owner approving (จ) cannot tell that (ซ) and (ฌ) are settled.
- **Proposed change:**
  - Rewrite (ซ) as the recorded answer for all three roles, "รอเจ้าของยืนยันตอนอนุมัติ; ถ้าไม่ยืนยัน ต้องทำ P25 บน Mac ก่อนขั้นที่ 2".
  - Widen row 13, align :346 and :350, add a row for (ฌ).
  - Write "(จ) และการยืนยัน (ซ)–(ฌ)" at :455.
- **Owner decision:** yes (confirm).

### F39 · Low · The owner's delegation is quoted in abridged form
- **Where:** contract :412; PROGRESS.md:5.
- **Evidence:** The quote begins "อันไหนที่ว่าดีมึงตัดสินใจเองไปเลย". The owner's message as relayed to this review begins "อันไหนที่ว่าดีบอกทีจะได้ทำแล้วก็เอาไหนที่ว่าดีมึงตัดสินใจเองไปเลย …". The clause "บอกทีจะได้ทำแล้วก็เอาไหนที่ว่าดี" is dropped with no mark. The full message is not in the repository.
- **Impact:** This sentence is the only authority for the 13 answers. The meaning used is in the full message, but the record is not verbatim, and the dropped clause asks to be told which items are good.
- **Proposed change:** Quote in full or mark the cut with "…" and "(ตัดคำ)". Add where the owner is told what was chosen (the answer table and :455).
- **Owner decision:** no.

### F40 · Low · question · The Claude-session budget of v2.x has no usage count
- **Where:** contract :443.
- **Evidence:** "งบใหม่ของ v2.0: 2 sessions ของ Claude" with no count. Drafting is committed on two dates (`5474cf2` on 2026-11-17, `cdf555e`…`db6e021` on 2026-11-18), and Plan v2.0 steps 2–7 still hold Claude work.
- **Impact:** If drafting counts, the budget is spent before implementation starts.
- **Proposed change:** State what counts and how many are used; the owner sets the number.
- **Owner decision:** yes.

### F41 · Low · question · `roots:` also prints cloud-storage folder names
- **Where:** contract :179, :200, :203, :423.
- **Evidence:** `roots:` prints the search dirs, which include every level-0 folder of `~/Library/CloudStorage`. Answer 8 covers the macOS account name only. File Provider folders are named after the provider account (from memory; the folder is empty today, :39).
- **Impact:** None today. A provider added later puts its account identifier into committed evidence.
- **Proposed change:** Print those dirs as a count plus provider prefix, or name this content in answer 8.
- **Owner decision:** yes.

## AC status

No AC changed status. Every v2.x AC is UNKNOWN: no v2.x code or test exists, and `aad621a..db6e021` changes
documents only.

| AC | Status | Why |
|----|--------|-----|
| AC-01 (macOS) | UNKNOWN | Owner L4 run not done. As drafted, the `paths read` proof has no stated source (F25) and reachability under Files-and-Folders rights is unmeasured for the search dirs (F27). |
| AC-02 | UNKNOWN | The v1.9 locked cases pass (suite 3692 passed at `db6e021`, run by lens B). The macOS cases cannot be written yet: seam (F4, F7), missing cases (F12), contradicting cases (F26, F30). |
| AC-03 (macOS) | UNKNOWN | Owner steps not done. Item (ฌ) of the checklist does not prove what it claims (F14). |
| AC-04 | UNKNOWN for v2.x | Unchanged by v2.1; the v1.9 tests pass in the suite. |
| AC-05 | UNKNOWN for v2.x | The v1.9 tests pass. Under v2.1 the CLI tests would reach `main`'s new lines on the Mac (F25). |
| AC-06 | UNKNOWN | The darwin checker patch does not exist. The exception is named and put to the owner (F2 closed); mutation gap F34. |
| AC-07 | UNKNOWN | Not run for v2.x. Mac and CI counts can differ unless the arm64 gate is placed (F4). |

## Checked and correct (and how)

- **Diff scope.** `git diff --stat aad621a..db6e021`: DECISIONS.md, PROGRESS.md, the contract, `docs/handoff/ENV-002.md`. No code, test, lockfile or locked path. The DECISIONS hunks sit at :247 (the D-021 line) and :256–274 (D-023). `git status --short` was empty before and after.
- **Red flags.** `bash scripts/controls/red-flags.sh main` → "Pattern groups with hits: 0" at `db6e021`, 2026-11-18. The control files it lists are the seven v1.x locked test files already on the branch.
- **Suite.** `PYTHONTZPATH="" PYTHONDONTWRITEBYTECODE=1 uv run --offline pytest tests -q -p no:cacheprovider` → 3692 passed at `db6e021`, 2026-11-18 (lens B). Lens A's refutation ran the locked `is_cloud_only`, `records_are_frozen` and CLI groups: 15 passed.
- **F1–F3, F5, F6 closed.**
  - Field sets against envkit:25–33 and test_ac02:140–146.
  - No `stat` import against test_imports:3396.
  - Every name the darwin reader needs is outside `_ENVCHECK_OS_DENIED` and `_ENVCHECK_CTYPES_DENIED` (test_imports:2737–2738).
  - Probe: the full-path literal loads; `proc_listallpids`, `proc_pidpath`, `getfsstat` exist; `libproc` and `libc` do not load; `proc_pidpath(0)` gives errno 3; the own-PID path equals `os.path.realpath(sys.executable)`; no `DYLD_` variable under `uv run`.
  - Probe: the symlink exception fits the three real links.
  - Probe: the `is_cloud_only` formula against the seven locked cases and the unit fake.
- **F4 mapping.** Each of the seven fields (contract :151–159) against `_terminal_install`, `_flag`, `_network_shares` (envcheck:498–531): consistent.
- **F8, F11 closed.** No locked fixture places a `metatrader*` or `net.metaquotes.*` folder under appdata. The CLI tests read the last line, item names and token only (test_ac05:117–120, :226–231), so lines before the items break nothing.
- **F13, F18–F23 closed.**
  - `man nc`, `man smbutil`, `nc -vz -G 2 127.0.0.1 9` with and without `-v`.
  - `mount`: 12 mounts, none under `/Volumes`, one autofs from `map auto_home`.
  - `statfs` offsets by field arithmetic.
  - envcheck:853 accepts a Windows absolute vault path on POSIX.
  - The named unit test exists at r1 unit:445.
  - The budget sums to 8.
- **D-023 against the contract.** Option ทาง 1 and the order of AC-03 (7), the file-list rule, the `nc` and `smbutil` commands, the VM wording, the redirect settings and the D-021 back-reference agree, except the labels under F24 and the citation under F17.
- **Nothing is presented as approved at document level.** Contract :3–4 say draft and name v1.9 as the last approved version. D-023 is "proposed" (DECISIONS:259). The D-021 line takes effect only on acceptance (:250). :412 says the delegation is not an approval. The checker exception sits under owner decision (จ) with the diff to the owner before apply (:310, :405). The exception is the wording at :373 (F36).
- **The 13 delegated answers** are all recorded (:414–428) and each is carried into the text; mismatches are in F36–F38.
- **Consolidating session.**
  - Read the skill file, r1 :1–90 and its last 30 lines, the contract at `db6e021` in full, DECISIONS:246–277, PROGRESS.md:5.
  - Read envcheck:126–136, :496–532, :572–602, :808–824, :856–895; test_ac05:80–90, :114–122, :222–234; test_imports:2734–2740, :2796–2802; `ci.yml`:19, :43.
  - Read `docs/handoff/ENV-002.md`:503–509, the runbook :13–17 and :30–35, HANDBOOK-CORE:124, `docs/architecture.md`:77.
  - Re-ran the red-flag scan, the diff stat, the bundle-path `grep` and the `man pgrep` line for F14, and the app names in `/Applications`.
  - The handoff's findings response was opened only after the findings were fixed.

## Not checked (and why)

- **No v2.x code or test exists.** Every closure is judged on the text against the current code and locked tests; the behaviour of the proposed seams on Linux CI and on Windows was reasoned, not run.
- **Private folders.** The home walk of :40 was not repeated and the search dirs (Desktop, Documents, Downloads, iCloud Drive, CloudStorage) were not listed, to search no private folder and raise no Privacy prompt. F27 is therefore a question. Whether the two refusals of :40 come from macOS Privacy or an agent sandbox was not verified.
- **`envcheck` against the real home** was not run, by rule. The statement that locked AC-05 tests would read the real machine under v2.1 is derived from the text and test source.
- **MT5, Wine, VMs.** Nothing that needs them was observed: Wine loader process names, what libproc shows for a terminal under Wine, bundle and container names, CrossOver and PlayOnMac layouts. Coverage inside a known prefix outside `drive_c/Program Files*` is a v2.0 rule not raised in r1 and was not assessed.
- **Servers and other machines.** No command ran against a server; the timeout text of `nc` and the output of `smbutil view -g -N` against filtered ports are unobserved. The VPS, the old Windows PC and Windows App (not installed: menu names, credential storage, `net view \\tsclient`) were not touched.
- **Agent apps.** `Claude.app` and `ChatGPT.app` were not running; F14 rests on bundle paths and on `pgrep` being case-sensitive.
- **System Settings pane names** in the runbook section were not opened.
- **Not reproduced.** Planting a library or setting `DYLD_LIBRARY_PATH`; attaching a disk image at another mount point; an edited `/etc/auto_home`. Each would write files or change the system.
- **No URL fetched** by any session in this round (MetaQuotes, Apple TN3150, Microsoft, CodeWeavers); r1's citations were taken as written. File Provider folder naming is from memory.
- **Credential stores.** The Keychain, Passwords, browser stores and `.env` were never read.
- **Other branches.** The ENV-001 and SPIKE-002 contracts and runbooks, including whether `host_report.py` has a `clipboard` item (T3 of DECISIONS:269).
- **Not run.** `node scripts/controls/check-locked-paths.mjs main` and `node scripts/controls/test-controls.mjs` (the handoff reports the first as failing on the seven v1.x locked files awaiting the owner's label and the second as 74 of 76 on this Mac); mypy. The consolidating session did not rerun the suite.
- **Read in part.** `docs/architecture.md` outside the cited lines, SPEC.md, test_ac02 outside the cited ranges.
- **Not judged.** Whether the owner's delegation covers answer 13 for all three roles is the owner's call (F38).

## Questions for the owner

1. **F27:** may the names-only, full-depth walk of the five search dirs and `~/.gnupg` be run from Visual Studio Code before approval? It may raise a Privacy prompt. If a folder is refused: clear it, or a named skip entry with a stated gap?
2. **F9:** extend the note to level-0 home names of command-line VM and Wine tools (`.colima` is already there), or accept that such tools never trigger a re-attestation?
3. **F33:** should a level-0 entry of `/Applications` or `~/Applications` whose name contains `metatrader` fail with or without `.app` (as Windows does), or stay a named residual?
4. **F32:** an allow list of mount points (`/`, `/dev`, `/System/Volumes/*`), or the residual for volumes mounted elsewhere?
5. **F36:** do you accept each new residual of v2.x (Wine or a VM invisible in every state, a copied MT5 cache outside the repo, the `~/Library` gap, the Trash, the `.pth` window, credential checks with no re-check, the two checks that cannot fail on macOS, the old PC by attestation)?
6. **F37:** one run of the Windows reader without a sentinel on the old PC before its clone is deleted, or attestation only with the corrected reason?
7. **F38:** do you confirm that the test author and both reviewers of v2.x are fresh Claude sessions, or should Codex pass P25 on the Mac first? Is the re-check of F12–F15 of `ef7881e` folded into the implementation review (decision (ฌ))?
8. **F40:** how many Claude sessions may v2.x use, and does contract drafting count?
9. **F41:** may cloud-storage folder names (which can carry an account identifier) appear in committed evidence?

Ready for the owner's approval (ENV-002 v2.1): no (0 High; 8 Medium first: F4, F7, F9, F10, F12, F14, F25, F27; they change the seams and rule text the locked tests will be written from)
Ready for owner decision (D-023): yes on its own text (only Low F17 and F24 remain); its header ties acceptance to contract v2.x, so accept it together with the contract once the Medium findings are closed
Findings open: 27 (0 High · 8 Medium: F4, F7, F9, F10, F12, F14, F25, F27 · 19 Low: F15, F16, F17, F24, F26, F28–F41)
