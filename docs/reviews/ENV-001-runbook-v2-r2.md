# Review ENV-001 runbook (macOS, contract v2.2) round 2 (closure check of r1 F17–F26) · base 96f9656 · head 157f8a9 · reviewer Claude Code, fresh subagent session (fresh-eyes-reviewer), session 5 (allowed by the owner beyond the budget of 4)

File: `docs/reviews/ENV-001-runbook-v2-r2.md` · date 2026-11-18 · branch `chore/ENV-001-vps-acquisition-host` · worktree clean at `157f8a9` before and after this review.

**Scope.**
- This is a re-review round, per the "Re-review rounds" section of `.agents/skills/cross-agent-review/SKILL.md`. It re-checks only r1's F17–F26 and their surrounding impact.
- **Fix commits:**
  - `7cda4c9`: F17, F19, F22
  - `c35786c`: F20, F25
  - `699809a`: F23, F24
  - `239acf3`: F18, F21, F26
  - `157f8a9` adds the findings response to `docs/handoff/ENV-001.md`.
- **Oracle:** the contract section "v2.0: ขั้นฝั่งเครื่องเจ้าของบน macOS" (v2.2, approved 2026-11-18), with its notes "หลังอนุมัติ v2.2".
- **References** on `chore/ENV-002-macos-research-host` (`9bf1c10`), read with `git show` only:
  - D-021 item 3 (a) and D-023 item 5;
  - the ENV-002 runbook, items 3 and 6;
  - three lines of the ENV-002 v2.6 contract, needed for F22–F24: C1 and C3 (its line 485) and the rule for a missing data dir (its line 92).
- Line numbers refer to `docs/runbooks/ENV-001-vps.md` at `157f8a9` unless another file is named.

**Label.**
- **Who:** one fresh Claude session, run as a read-only subagent. It did not write the runbook, the fixes or r1, and it was given no implementer reasoning.
- **Budget:** the v2.0 budget is 4 fresh sessions (contract line 332), and r1 used the fourth.
  - The caller states that the owner allowed this fifth session on 2026-11-18 ("อนุญาต 1 session").
  - The repository at `157f8a9` does not record that yet. Handoff line 521 says only that the owner decides.
- **Binding:** same as r1.
  - Contract lines 326–327, approved with (ฎ), name a fresh Claude session as the v2.x reviewer.
  - PROGRESS.md line 5 records the ENV-001 role swap. No PROGRESS line names ENV-001 v2.x.
  - If the owner does not read those records as the binding, this file is a pre-review (Claude subagent).

## How I verified, and the limit of it
**Order.**
1. The skill file, r1 in full, and the contract's v2.0 section.
2. Each fix commit (`git show`), and `git diff 96f9656 157f8a9`.
3. The whole runbook at `157f8a9`.
4. The ENV-002-branch references, then `scripts/env/host_report.py` for what T3 and 6.5 read.
5. The probes below.
6. I wrote the closure verdicts and F27–F30, and only then read the handoff's "Findings response (runbook review r1)". It accepts all ten IDs and names the same commits. It changed none of my verdicts.

**Runs on this Mac** (macOS 26.6.2 arm64, zsh 5.9). Every file I created is in the scratch folder `…/scratchpad/env001-runbook-r2/`.
- `/bin/zsh -f -n` on all 22 Mac command lines: every `%` line, line 140's example, `rmdir` and `pgrep`.
- `man` for `find`, `xargs`, `shasum`, `mkdir` and zsh `read`.
- The exact §7.1 loop, the §7.2 line and both `read` forms, against 127.0.0.1 only.
  - Port 7000 is open on this Mac; the runbook's ports are closed.
  - They ran in an interactive zsh: `/bin/zsh -i` on a pty, driven by `/usr/bin/expect`, with `/etc/zshrc` loaded.
  - `ZDOTDIR` pointed `HISTFILE` into the scratch folder; the shell printed `SAVEHIST=1000`.
- Both new `find` forms on scratch folders, and the split `cd`/`find` lines with a fake `HOME`.
- `diff` of §§2–6 and §9 against v1.9 (`57e2d1c`).
- The three AC-06 patterns over the runbook; `bash scripts/controls/red-flags.sh 96f9656` and `… main`.
- `mdls` and `mdfind` for Keychain Access and Passwords.

**Limits.**
- No network: no `curl` to the internet, no `nc -6`, no remote host, no timeout path.
- No Windows App, no VPS, and no PowerShell on this Mac. I read the two new PowerShell lines by eye.

## Closure of r1 F17–F26
| ID | Status | Diff | Evidence and confirmation |
|---|---|---|---|
| F17 (Medium) | **closed** | `7cda4c9` · lines 210, 222 | **Line 210:** "ถ้า T1, T2 หรือ T3 ไม่ผ่าน (review F17): ห้ามคัดลอก · ทำข้อ 6.1–6.3 ทันที (เอาโฟลเดอร์ออกจากทุกรายการ PC → เชื่อมแล้วตั้ง `fDisableCdm` เป็น 1 → เชื่อมใหม่และตรวจ T4) แล้วจึงหยุดและส่งผลให้ Claude". **Line 222:** "คัดลอกเฉพาะเมื่อ T2 และ T3 ผ่าน". **Walk-through:** T1 fails at step 3 (policy 1, folder requested); T2 or T3 fails at step 5 (policy 0, folder requested). Every case goes through 6.1 (folder out), 6.2 (`fDisableCdm` set to 1) and 6.3 (T4 checks the Folders tab of every PC entry). Both parts of r1's proof are present. **Residual (F27):** on this path the value 1 is set but never read back, and a failed 6.2 or T4 has no step |
| F18 | **closed** | `239acf3` · lines 135, 171 | **Line 171** sends only lines that start with `port` or `exit`, and names the `curl` lines as never sent. **Line 135** names the `curl` exception. **Run:** in the interactive run every loop line started with `port`. The same rule also keeps out two lines that carry private values: the `read` echo line (the address) and the prompt line (the account name; default `PS1="%n@%m %1~ %# "`, `/etc/zshrc:71`). **Residual (F29):** summary row 7 |
| F19 | **closed** | `7cda4c9` · lines 227–231 | **Run on scratch folders:** the line printed `./file one.parquet`, `./sub dir/x.parquet`, `./.hidden` and `./manifest.json`, with no absolute path. It skipped `.DS_Store` at any depth. Empty and `.DS_Store`-only folders printed nothing. **Residual (F28):** the fix splits r1's `cd … && find …` into two lines |
| F20 | **closed** | `c35786c` · line 9; `7cda4c9` · line 232 | **Header rule:** "ก่อนเปิด Claude, Codex หรือ VS Code อีกครั้ง (ทุกครั้งที่ "ส่งให้ Claude" และก่อนรัน envcheck ของ ENV-002): ตัดการเชื่อม RDP ทุกหน้าต่างและ logout จาก console … ข้อความที่จะส่งให้วางลง TextEdit ไว้ก่อนตัดการเชื่อม". **Line 232:** host_report, then **ตัดการเชื่อม RDP**, then envcheck. **Interactions:** the F17 path ends connected at 6.3 and then sends to Claude, so the header rule closes that session too. envcheck runs in VS Code's terminal (ENV-002 runbook line 43), which the rule covers |
| F21 | **closed** | `239acf3` · lines 140, 156, 165, 169 | **(i) Line 156:** the IPv6 address comes from the provider page (the host address, not the `/64`) or from a read-only `Get-NetIPAddress … .IPAddress` with §1.5's filter; "ห้ามวางในแชท". **(ii) Line 165:** all four lines run again on the hotspot; every port, 3389 included, must exit non-zero, and both controls must succeed. This gives contract line 268's F16 note its own command. **(iii) Line 140:** `curl` before and after, plus item 1's `for` line with only that port. Typed literally with "…", it fails safe (`command not found: …`, exit 127, no `port` line). **(iv) Line 169:** "คัดลอกเป็นข้อความ ไม่ส่ง screenshot". **Residual (F30):** a multi-line paste of (i)'s output at `read` |
| F22 | **closed** | `7cda4c9` · lines 211, 214–218, 222 | **(i)** `mkdir -p` comes before the emptiness check. Running envcheck before `mkdir` is safe: ENV-002 v2.6 counts a missing `<repo>/data` as "ไม่มีไฟล์ให้ตรวจ (ไม่ทำให้ FAIL หรือ UNKNOWN)". **(ii)** Line 211 has the Finder rule, and both `find` forms skip `.DS_Store` (scratch runs). **(iii) T2:** one share with its name recorded, and `Get-ChildItem -Force \\tsclient\<ชื่อ share>` shows only `data/transfer`'s content. **(iv) The T3 note matches the code:** `drive_redirection` is `policy_first(fDisableCdm)` (host_report.py lines 170–176, 671–672, 794–797, 872). host_report reads no share and no `\\tsclient` (0 matches), so T3's report cannot carry Mac paths |
| F23 | **closed** | `699809a` · line 26 | **C1** now reads "…ไม่มีรายการของ VPS และทุกรายการ PC (รวมรายการที่ Duplicate) ไม่ผูก credential". That is ENV-002 v2.6 C1 (its line 485), widened to every entry. **The Spotlight hint is present.** On this Mac, Keychain Access is at `/System/Library/CoreServices/Applications/`, and Spotlight indexes it as "Keychain Access.app" (`mdfind 'kMDItemFSName == "Keychain Access.app"'`). **Note:** Spotlight displays localized names here (`mdls`): Keychain Access is "การเข้าถึงพวงกุญแจ" and Passwords is "รหัสผ่าน" |
| F24 (question) | **closed** (answered with r1's wording) | `699809a` · lines 24, 180, 197 | **(a) Line 24:** "ไม่ติ๊กอุปกรณ์ใด ยกเว้น Clipboard: เปิดไว้ (VPS จำกัดให้เป็นข้อความเท่านั้นเองด้วย `SCClipLevel` …; ปิดเฉพาะเมื่อ (ค) เลือกปิด clipboard ทั้งหมด)". This agrees with ENV-002 C3 ("Disabled หรือค่าที่ใช้ส่งข้อความตาม D-021 ข้อ 4") and with lines 180 and 197. It adds no exposure: the client clipboard was on in `96f9656` too. **(b) Line 180:** "เพิ่มเฉพาะ `~/rdp-redirect-test` (โฟลเดอร์อื่นต้องไม่อยู่ในรายการ)" |
| F25 | **closed** | `c35786c` · lines 3, 74 | **Diff:** I extracted §§2–6 and §9 from `57e2d1c` (v1.9) and from HEAD and ran `diff`. §§2–6 differ in one line, 2.3's "(รายการ PC ที่ Duplicate ไว้)"; §9 is identical (exit 0). **Header:** line 3 names the 2.3 exception. **§3:** line 74 is back to "(KB5040437)", and the build check stays in §8 (line 190, `UBR` ≥ 2582) |
| F26 (question) | **closed** (answered) | `239acf3` · lines 135, 145, 149, 159, 165 | **No assignment lines remain:** grep finds no `VPS=` or `VPS6=` line. **History run:** in the interactive run with `/etc/zshrc`'s history settings, the history file kept all 10 typed command lines and 0 copies of the answer (`/usr/bin/grep -c 127.0.0.1` printed 0). `read` also stripped spaces around the answer (`[127.0.0.1]`). The address stays in the on-screen echo, which is outside the chat and the evidence. **Residual (F30):** a paste of two or more lines at the prompt |

## Surrounding impact

### F17: can anything still leave the channel open?
- **A failed T1, T2 or T3:** yes, it now ends at `fDisableCdm` = 1 with no folder in any PC entry, by instruction (line 210). The copy waits for T2 and T3 (line 222).
- **A failure during the copy:** nothing is left open.
  - Step 5 has no stop instruction for a copy error, so the steps run on to step 6, which closes both layers.
  - A partial copy shows at 6.4, after the channel is closed. It also blocks the next run at step 1's emptiness check, which is safe.
- **A session still connected when a test fails:** it is closed within the path. 6.1 says "ก่อนเชื่อมใหม่", 6.2 ends with a disconnect, and the F20 header rule closes the 6.3 session before Claude opens.
- **A failure during 6.1–6.3:** yes, in narrow cases (F27).
  - On the failure path, nothing reads `fDisableCdm` back. Once the folder is out of the PC entries, T4 cannot see the policy; only 6.5's host_report can, and the failure path stops before 6.5.
  - A 6.2 connection that fails, or a failed T4, has no written step on either path.

### Commands
- **Syntax.** All 22 Mac command lines parse under `/bin/zsh -f -n`. Lines that are new or changed in this range: 140 (the example), 145, 159, 214, 215, 216, 229 and 230.
- **Flags** (man pages on this Mac):
  - `find`: `-mindepth n` ("“-mindepth 1” processes all but the command line arguments"), `! expression`, `-name`, `-type f`, `-print0`.
  - `xargs -0`: NUL separators, "used in concert with the -print0 function". It "does not run the utility argument on empty input".
  - `shasum -a 256`, and `mkdir -p` (no error when the folder exists).
  - zsh `read`: `-r` is raw mode. "If the first argument contains a ‘?’, the remainder of this word is used as a prompt on standard error when the shell is interactive."
- **The masked loop and the `read` form** (interactive zsh, 127.0.0.1):
  - The loop printed 9 lines of the form `port 22 exit 1: nc: connectx to x.x.x.x port 22 (tcp) failed: Connection refused`.
  - A variant with ports 7000 and 9 printed `port 7000 exit 0: Connection to x.x.x.x port 7000 [tcp/afs3-fileserver] succeeded!`.
  - The §7.2 line printed `port 3389 exit 1: …`.
  - No printed line held the address.
  - The `!` in `! -name` was not history-expanded; it was printed and saved literally.
- **The `find` forms** (scratch folders):

  | Folder | Step 1 (`find . -mindepth 1 ! -name .DS_Store`) | 6.4 (`find … -print0 \| xargs -0 shasum -a 256`) |
  |---|---|---|
  | empty | nothing | nothing |
  | `.DS_Store` only | nothing | nothing |
  | files with spaces, a hidden file, a subfolder, `.DS_Store` at two depths | every entry except `.DS_Store` | `./`-relative lines, `.DS_Store` skipped |
  | a subfolder that holds only `.DS_Store` | `./sub` (correctly not empty) | nothing |
- **PowerShell additions,** read by eye: line 156 (`(Get-NetIPAddress …).IPAddress`) and line 222 (`Get-ChildItem -Force \\tsclient\<ชื่อ share>`). Both are read-only.

### Masking
- **Followed as written, no new instruction puts an address, an account name or a secret into the chat or the committed evidence:**
  - The address is typed only at the `read` prompt, and line 135 says not to paste it.
  - Line 156 prints the full IPv6 address on the VPS, with "ห้ามวางในแชท".
  - The `curl` lines are named as never sent (line 171).
  - 6.4 prints `./<file>`.
  - The provider page is masked and sent as text (line 169).
  - No step asks for a password, a token or the provider account name.
- **Three routes remain** when the owner copies more than asked or hits an error:
  - F28: a failed `cd` puts home-folder file names into the 6.4 send.
  - F29: summary row 7 can pull in the hotspot IP.
  - F30: a multi-line paste puts an address into zsh history. This is outside the chat and the evidence.
- **Note, not a finding.** In §§8 and 10 the owner copies output lines, and a prompt line copied with them carries the account name. ENV-002 already accepts the account name in the chat and has Claude mask `/Users/<ชื่อบัญชี>` before commit (ENV-002 runbook line 152). So this follows an existing project rule.

### VPS items 2–6 and 9
- They are as in v1.9 apart from 2.3's duplicated entry, which line 3 now names (F25).
- The `diff` of §§2–6 shows that one line; §9 is identical.

## New findings
| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|---|---|---|---|---|---|---|---|---|
| F27 | Low | confirmed from the text | ENV-001-vps.md:210, 225–226, 232 | The failure path runs only 6.1–6.3. Once 6.1 removes the folder, T4 cannot see `fDisableCdm`. Only 6.5's host_report reads it, and the path stops before 6.5. Neither path has a step for a failed 6.2 connection or a failed T4 | On the failure path: 6.2's write fails unnoticed (a PowerShell not opened as Administrator), or 6.2 cannot connect. On either path: T4 shows a share | The owner may stop with the VPS policy still at 0 and nothing showing it; the client side is closed (T4 shows this). A failed T4 has no written close step. After a failed T2 or T3, envcheck is not re-run | Add a read-only read of `fDisableCdm` to T4. Line 210: run 6.1–6.3, then 6.5. One sentence for a failed 6.2 or T4 (text below) | T4 reads `fDisableCdm` = 1 on both paths. The failure path ends with host_report and envcheck results. §10 names a step for a failed 6.2 connection and a failed T4 |
| F28 | Low | confirmed | ENV-001-vps.md:215–216, 229–230 | `cd` and `find .` are separate lines; r1's fix chained them with `&&`. In a scratch run with a fake `HOME`, after `cd` failed the 6.4 lines hashed `./Desktop/private notes.txt` and `./Documents/tax return 2025.pdf`. The `&&` form printed only the error | `cd` fails: a typo, a missing folder, or Terminal.app was refused access to the Documents folder | `find .` lists or hashes the home tree. At 6.4, that list is what the owner is told to send (line 233). The `cd` error shows the absolute path | `cd … && find …` on both lines (commands below) | With the folder missing, each line prints only the `cd` error and lists nothing |
| F29 | Low | confirmed from the text | ENV-001-vps.md:242 (vs 171) | Summary row 7 still asks for "บรรทัดของ `nc` ทุกบรรทัด … ผลของ hotspot" and does not exclude `curl`; line 171 does | The owner sends from the summary table | The hotspot IP reaches the chat (AC-03 (2), contract line 263: "ไม่วาง IP") | Row 7 carries line 171's rule (text below) | Row 7 names the same lines as 7.5 |
| F30 | Low | confirmed (against F26's accepted aim; no contract clause) | ENV-001-vps.md:156, 159, 165 | At a `read` prompt only the first pasted line is read. In a scratch run, two lines were pasted at `read -r 'VPS6?…'`: `VPS6` held the first, and the second ran as a command (`zsh: command not found: …`) and was saved in history | The VPS has two or more global IPv6 addresses, so line 156 prints two lines. The owner copies both and pastes them at the prompt | An address is saved in `~/.zsh_history`, which F26's fix set out to prevent | Line 156 or 159: "วางที่อยู่เดียว บรรทัดเดียว (ถ้าคำสั่งพิมพ์หลายที่อยู่ ใช้ที่อยู่แรก)" | The `read` steps say to paste a single line |

### F27 · Low · The failure path sets `fDisableCdm` back to 1 but never reads it
- **Where:** line 210 (the failure path), lines 225–226 (6.2 and 6.3) and line 232 (6.5).
- **Evidence:**
  - Line 210 runs "ข้อ 6.1–6.3" and then "หยุดและส่งผลให้ Claude".
  - T4 (line 226) checks `net view \\tsclient` and the Folders tab of every PC entry. After 6.1 no entry requests a folder, so `\\tsclient` is empty whatever `fDisableCdm` holds.
    - r1 recorded the same limit for §8: an empty `\\tsclient` proves the VPS refused only if Windows App really offered the folder.
    - It is also why the contract's AC-04 Given requests a folder (contract lines 274–275).
  - The only step that reads the value is 6.5. There, host_report's `drive_redirection` item is `policy_first(fDisableCdm)` (`scripts/env/host_report.py` lines 170–176, 671–672, 794–797, 872). The failure path stops before 6.5.
  - Neither path has a step for a 6.2 connection that fails, or for a failed T4. Line 209 says only "ข้อใดของ T1–T4 ไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ และต้องตัดสินใหม่".
- **Trigger:**
  - On the failure path, 6.2's write does not take effect. For example, the PowerShell was not opened as Administrator, so the HKLM write fails with an error that a non-programmer can miss.
  - Or 6.2 cannot connect.
  - On either path, T4 shows a share. This needs 6.1 and 6.2 to fail together.
- **Impact:**
  - The owner may stop with the VPS policy still at 0, and no step shows it.
  - The folder is out of every PC entry (T4 shows this), so later connections share nothing. But the VPS layer stays open until host_report runs again, and a later §8 re-test or §10 run starts with only one layer.
  - A failed T4 has no written step to close the channel.
  - After a failed T2 or T3 the Mac folder was redirected read-write, and that path does not re-run envcheck.
- **Why Low:** this is less serious than r1's F17. The likely failure, T2 or T3, now closes both layers; what remains needs an operator slip or two failures together.
- **Minimal fix:**
  1. T4 (6.3) adds the read-only `PS> Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' | Select-Object fDisableCdm`, which must show 1. The success path gains the read too.
  2. Line 210: "ทำข้อ 6.1–6.3 แล้วข้อ 6.5 ทันที (บันทึกผลตามจริง)".
  3. Add: "ถ้าข้อ 6.2 เชื่อมไม่ได้ หรือ T4 ไม่ผ่าน: ห้ามเชื่อมด้วยรายการ PC ที่ยังมีโฟลเดอร์ · ตั้ง `fDisableCdm` เป็น 1 จาก console ของผู้ให้บริการ (PowerShell แบบ Administrator) · หยุดและส่งผลให้ Claude".

### F28 · Low · §10 runs `find .` even when `cd` fails
- **Where:** lines 215–216 (step 1) and 229–230 (6.4).
- **Evidence:**
  - r1's F19 fix was a single line: "`cd ~/Documents/GitHub/Sochron1k/data/transfer && /usr/bin/find . …`". The runbook puts `cd` and `find` on separate lines.
  - I ran both forms with a fake `HOME` in the scratch folder. The repo folder was missing, and the current folder was that home, as in a new Terminal window.
    - The 6.4 lines printed `zsh:cd:1: no such file or directory: <scratch>/fakehome/Documents/GitHub/Sochron1k/data/transfer`, then SHA-256 lines for `./Desktop/private notes.txt` and `./Documents/tax return 2025.pdf`.
    - The step 1 lines listed the same names.
    - The `&&` form printed only the `cd` error, with exit 1.
- **Trigger:** `cd` fails. This happens with a typo, with a missing folder, or when Terminal.app is refused the Documents folder:
  - macOS asks an app for Documents access the first time it touches `~/Documents`.
  - Within the ENV-001 and ENV-002 runbooks, step 1 is Terminal.app's first command under `~/Documents`, because ENV-002 item 3 runs in VS Code's terminal (ENV-002 runbook line 43).
  - Answering "Don't Allow" makes `mkdir -p` fail, and then `cd`.
- **Impact:**
  - **Step 1** lists the home tree and fails its "`find` ต้องไม่พิมพ์อะไร" check. That is safe for the channel, but private file names are then on screen, and the owner may paste them when asking for help.
  - **6.4** hashes the home tree, and the owner is told to send "รายการไฟล์และ SHA-256" (line 233). Home-folder file names would reach the chat and the acquisition-host evidence.
  - **The `cd` error line** carries the account name. The project already masks that before commit (ENV-002 runbook line 152).
- **Minimal fix:** r1's form, plus one instruction.
  - `% cd ~/Documents/GitHub/Sochron1k/data/transfer && /usr/bin/find . -mindepth 1 ! -name .DS_Store`
  - `% cd ~/Documents/GitHub/Sochron1k/data/transfer && /usr/bin/find . -type f ! -name .DS_Store -print0 | /usr/bin/xargs -0 /usr/bin/shasum -a 256`
  - "ถ้า `cd` ขึ้น error: หยุด ไม่ส่งผล"
- **Pre-checked:** both lines parse under `zsh -f -n`.
  - With the folder missing, each printed only the `cd` error (exit 1).
  - With the folder present, they printed the same `./` lines as the runbook's form.

### F29 · Low · Summary row 7 does not carry F18's send rule
- **Evidence:**
  - Line 171: "ทุกบรรทัดที่ขึ้นต้นด้วย `port` หรือ `exit` (ปิดบังแล้ว) … **ไม่ส่งบรรทัดที่ `curl` พิมพ์**".
  - Row 7 of "สรุปสิ่งที่ส่งกลับ" (line 242) still reads "บรรทัดของ `nc` ทุกบรรทัด (…), ผลของ hotspot, …" and does not mention `curl`.
  - Contract line 316 defines row 7 as "ผลของ `nc` (ข้อความและ exit status ทุกพอร์ต)". The `port` lines already carry both.
- **Trigger:** the owner sends from the summary table at the end, and reads "ผลของ hotspot" as the whole hotspot window.
- **Impact:** the hotspot IP reaches the chat. This is F18's impact by a second route.
- **Minimal fix:** row 7 reads: "บรรทัดที่ขึ้นต้นด้วย `port` หรือ `exit` (ปิดบังแล้ว; ไม่ส่งบรรทัดของ `curl`), "ต่างจาก IP บ้าน: ใช่", ผล IPv6 (หรือ "IPv6 ไม่ได้ทดสอบ"), rule ของผู้ให้บริการและหน้าของ VPS ที่แสดง rule ทุกชุด (ปิดบัง IP)".

### F30 · Low · Pasting more than one line at a `read` prompt puts the extra lines into history
- **Evidence:**
  - zsh `read` takes one line. Whatever else was pasted stays in the terminal's input and runs at the next prompt.
  - I sent two lines at `read -r 'VPS6?IPv6 ของ VPS: '` in the interactive shell, as a scratch run.
    - `VPS6` held the first line (`[::1]`).
    - The second ran as a command (`zsh: command not found: probe-second-line-2001-db8`) and was saved in the history file.
  - Line 156's command prints one line per address.
- **Trigger:** the VPS has two or more global IPv6 addresses. The owner copies all of line 156's output and pastes it at the line 159 prompt. The same applies to the line 165 repeat on the hotspot.
- **Impact:** an address lands in `~/.zsh_history`, which F26's fix set out to prevent. Nothing reaches the chat or the evidence.
- **Basis:** F26 was a question, and the implementer accepted it. F30 follows that accepted aim; no contract clause requires it.
- **Minimal fix:** at line 156, or next to each `read` line: "วางที่อยู่เดียว บรรทัดเดียว (ถ้าคำสั่งพิมพ์หลายที่อยู่ ใช้ที่อยู่แรก)".

## AC status (runbook coverage after the fixes)
| AC | Status | Why |
|---|---|---|
| AC-03 (v2.0) | every clause has a step · no wrong PASS found | Coverage as in r1, plus the fixes: the `read` prompts (145, 159), the IPv6 address source (156), the hotspot IPv6 round with both controls (165), the hotspot command for a refused port (140), the provider page as text (169), the send rule (171). Remainders: F29, F30 |
| AC-04 (v2.0), test steps | every clause has a step · no wrong PASS found | Only the Clipboard wording (24, 180, 197) and "เพิ่มเฉพาะ" (180) changed |
| AC-04 (v2.0), snapshot procedure (§10) | every element of D-023 item 5 and the contract's closing order has a step · a failed T1–T3 now closes both layers | New: the failure path (210), the copy gate (222), `mkdir -p` and the emptiness check (214–218), the T2 command and the T3 note (222), host_report, then disconnect, then envcheck (232). Remainders: F27, F28 |
| AC-01, AC-02, AC-05, AC-06, AC-07 | VPS steps unchanged apart from 2.3, which line 3 names | The `diff` of §§2–6 shows one line (2.3); §9 is identical; AC-06's three patterns have 0 hits in the runbook |

## Ready for the owner to use the runbook: items 0–9 yes · item 10 yes
**Items 0–9 (the rental, and ENV-001's own AC-03 and AC-04): yes.**
- r1's F18, F20, F21, F23, F24, F25 and F26 are closed.
- Two Low findings remain in these items: F29 and F30. Each fix is one phrase, and the owner meets both on the first day. They are worth fixing before the rental.

**Item 10: yes.**
- F17 is closed. A failed T1, T2 or T3 now forbids the copy and closes both layers, and the copy waits for T2 and T3. F19 and F22 are closed too.
- Two Low findings remain, both in item 10: F27 and F28. Fix them before item 10's first use. That use comes only after ENV-1 passes, so there is time.
- ENV-002 runbook item 6 (its line 192) says "ยังใช้ไม่ได้" until this closure check passes. That condition is now met. Its other condition, that ENV-1 has passed, still applies.

**Budget.**
- This session was already beyond the budget of 4. Checking the fixes for F27–F30 would take another session; that is the owner's call.
- The fixes are small:
  - F27: two sentences and one read-only line;
  - F28: `&&`, twice;
  - F29: one table cell;
  - F30: one phrase.

Findings open: 4 (0 High · 0 Medium · 4 Low: F27, F28, F29, F30). Closed in this round: 10 (r1's F17–F26).

## Checked, nothing found (and how)
**The change set.**
- `git diff --stat 96f9656 157f8a9` shows three files: the runbook, r1 itself, and the handoff (+21 lines, the response table).
- Each fix commit touches only the items its message names:
  - `7cda4c9`: §10;
  - `c35786c`: the header and §3;
  - `699809a`: §1.2, §8.2 and §8.5;
  - `239acf3`: §7.
- The handoff's table matches the commits.

**Red flags.**
- `red-flags.sh 96f9656` and `… main` both report 0 pattern groups with hits, no deleted tests and no untracked files.
- Control files touched since `96f9656`: none.
- Against `main`, the only control file listed is v1.x's `tests/acceptance/ENV-001/test_ac02_host_report.py` (D-006), which this range does not touch.

**The worktree:** clean at `157f8a9`, with no stash, before and after.

**D-023 item 5 and D-021 item 3 (a).** Every element is still in §10:
- one folder, with Read-only unticked;
- envcheck PASS and an empty folder first;
- T1–T4;
- the closing order;
- host_report and envcheck afterwards;
- the file list with SHA-256.

**The contract's list for the macOS runbook** (lines 296–316): the header rules (C9 and the lock-out rule), items 0, 1.2, 7, 8 and 10, and summary rows 7 and 8 all still have their steps. No fix removed a step.

**Cross-references.**
- ENV-002 runbook item 6 (its line 192) points to item 10 and to this closure check.
- ENV-002 item 3 runs envcheck in VS Code's terminal, so the Terminal.app `cd` in §10 does not change where envcheck runs.

**host_report.** The T3 note and the success path's 6.5 match the code: `drive_redirection` reads the policy value first.

**F24.** "Clipboard: เปิดไว้" adds no exposure. The client clipboard was on in `96f9656` too, and `SCClipLevel` still comes from §3.

## Not checked (and why)
- **Windows App behaviour.** It is not installed, so these are unchecked:
  - whether an edit made while connected applies only at the next connection;
  - the Clipboard control;
  - the share name under `\\tsclient`. If it includes the Mac's computer name, T2's "บันทึกชื่อ share" puts that name into the evidence.
- **PowerShell lines 156 and 222, and the HKLM write error in a non-elevated shell** (F27's trigger). There is no Windows or PowerShell here; I read them by eye.
- **`nc -6`, remote hosts, the timeout path and `curl`.** There was no network. IPv6 masking is still inferred from the shared message path, as in r1.
- **The Spotlight UI.** I checked only its index, with `mdls` and `mdfind`.
- **The macOS Documents-folder prompt for Terminal.app** (F28's trigger). I did not trigger it on purpose; I reproduced the mechanism with a fake `HOME`.
- **Other places the typed address can stay:** Terminal.app's scrollback and saved window state, and the Mac clipboard after a paste. These are outside the chat and the evidence, and outside F26's scope (history). They are the owner's call, like F26.
- **Outside this round's IDs:** 6.4 has no written step for when the list differs from the manifest (an extra or a missing file).
  - This is unchanged since `96f9656`.
  - The backstops are envcheck at 6.5 and the R1 loader's SHA-256 check against the manifest (D-021 item 3 (a)).
- **pytest.** The diff is documents only, and `uv run` would create `.venv` in the worktree.

## Blocks
- None. No hook or permission block occurred.
- **Disclosures:**
  - **The background run.** The first `expect` run took longer than the tool's 120 s limit, because each prompt wait timed out on zsh's bracketed-paste escape. The harness moved the run to the background and wrote its stdout to `/private/tmp/claude-501/-Users-faztycoding-Documents-GitHub-Sochron1k/38a03acd-6822-4cac-ae23-d960d6191884/tasks/b39hy5ma9.output`.
    - That file is outside my scratch folder. The harness created it; it holds a transcript with 127.0.0.1 only.
    - Every file I created is under `/private/tmp/claude-501/-Users-faztycoding-Documents-GitHub-Sochron1k/38a03acd-6822-4cac-ae23-d960d6191884/scratchpad/env001-runbook-r2/`.
  - **Tools beyond the caller's list,** each read-only or limited to the scratch folder:
    - `/usr/bin/script` and `/usr/bin/expect`, to drive zsh on a pty with history in the scratch folder. A first `script` attempt ended before zsh read its input and wrote only scratch files.
    - `mdls` and `mdfind`, for local Spotlight metadata of two system apps.
  - r1's stray file `/tmp/zsh_n_err_ignore` no longer exists.
