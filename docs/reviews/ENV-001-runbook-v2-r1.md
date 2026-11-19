# Review ENV-001 runbook (macOS, contract v2.2) round 1 · base 57e2d1c · head 96f9656 · reviewer Claude Code, fresh subagent session (fresh-eyes-reviewer), session 4 of 4

File: `docs/reviews/ENV-001-runbook-v2-r1.md` · date 2026-11-18 · branch `chore/ENV-001-vps-acquisition-host`.

**Scope.**
- This round reviews the owner-side steps of `docs/runbooks/ENV-001-vps.md` at `96f9656`.
- The oracle is the contract section "v2.0: ขั้นฝั่งเครื่องเจ้าของบน macOS" of `docs/contracts/ENV-001-vps-acquisition-host.md` (v2.2, approved 2026-11-18). This includes the three notes "หลังอนุมัติ v2.2" for r3 F14–F16, which `c7b3a00` added.
- VPS items 2–6 and 9 are checked only for being unchanged since v1.9.
- Line numbers refer to the runbook at `96f9656` unless another file is named.

**Label.**
- **Who:** one fresh Claude session, run as a read-only subagent.
  - It did not write the runbook, the contract or reviews r1–r3.
  - It was given no implementer reasoning.
- **Binding:**
  - Contract lines 326–327 name a fresh Claude session as the v2.x reviewer and say "runbook ฉบับ macOS ตรวจโดย review ของ runbook ก่อนเจ้าของใช้". The owner approved those lines with (ฎ).
  - PROGRESS.md line 5 records the ENV-001 role swap ("คงการสลับบทบาท แม้โควตา Codex กลับมาแล้ว"). No PROGRESS line names ENV-001 v2.x itself.
  - If the owner does not read those records as the binding, this file is a pre-review (Claude subagent).

## How I verified, and the limit of it
**Order:**
1. I read the contract's v2.0 section first: AC-03 and AC-04 (v2.0), the "runbook ฉบับ macOS" list, the negative cases, the residual risks, Verification and Budget.
2. Then reviews r1–r3.
3. Then the whole runbook at `96f9656`, and the v1.9 runbook at `57e2d1c`.
4. Then, from branch `chore/ENV-002-macos-research-host`, using `git show` only:
   - D-021 item 3 (a);
   - D-023 items 5 and 6;
   - the ENV-002 v2.6 contract (C1–C10, decisions (ค) and (ช), line 20);
   - the ENV-002 runbook, items 3 and 6.
5. I wrote the findings before looking at the handoff. After that I looked only at the handoff's log.

**Diffs:**
- `git diff 57e2d1c..HEAD`.
- `diff` of §1, §§2–6 and §9, extracted from both versions.
- A word diff of `c7b3a00`.

**Runs on this Mac (macOS 26.6.2 arm64, zsh 5.9):**
- man pages for each command.
- The exact §7.1 loop and the §7.2 line, with `VPS=127.0.0.1`. Port 7000 is open (a system listener) and port 9 is closed.
- `nc` with four text forms of 127.0.0.1.
- `nc -v` output piped and on a pty (`script -q /dev/null`), for a number and for `-4 localhost`.
- zsh expansion tests on fake strings.
- `zsh -f -n` on all 17 Mac command lines.
- `find … -print0 … xargs -0 shasum -a 256` and `ls -A` on scratch folders.
- The history settings in the system zsh files.
- `bash scripts/controls/red-flags.sh 57e2d1c` and `… main`.
- The AC-06 patterns over the runbook.

**Limits:**
- **No network.** No `curl` to the internet. `nc` ran only to 127.0.0.1, so there was no IPv6 run, no remote host and no timeout path.
- **No app, no VPS.** Windows App is not installed. There is no VPS or Windows machine, so I read the PowerShell lines for syntax and for being read-only.
- **The KB5040437 build number is the implementer's claim.** The implementer took it from the Microsoft Support page title "July 9, 2024—KB5040437 (OS Build 20348.2582)". I could not open that page.
- **pytest was not run** (see Not checked).

## Findings
| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|---|---|---|---|---|---|---|---|---|
| F17 | Medium | confirmed | ENV-001-vps.md:208, 211–216 | Line 208 stops the owner when a T-test fails ("ช่องทางนี้ยังไม่อนุมัติ และต้องตัดสินใหม่"), but no step closes the channel. Line 213 does not make the copy wait for T2 and T3. The closing order (214–219) comes only after the copy | T2 or T3 fails at first use (Windows App folder redirection is unverified) and the owner stops, as told | The VPS stays at `fDisableCdm` = 0 and `data/transfer` stays redirected read-write. The next connection opens the research data folder to the host that holds the holdout | Send a failed T1–T3 to 6.1–6.3 at once, and make the copy wait for T2 and T3 (text below) | §10 has a failure path that ends at `fDisableCdm` = 1 with no folder in any PC entry |
| F18 | Low | confirmed | ENV-001-vps.md:134, 150, 152, 170 | Line 134 says every §7 line is masked, but the `curl` lines print the hotspot address in full. Line 170 asks for every printed line. Only line 154 says not to paste the address | The owner copies the whole §7.2 window | The hotspot address reaches the chat, which AC-03 (2) forbids | Line 170: send only the lines that start with `port` or `exit`, not the `curl` lines | The send list names the `curl` lines as not sent |
| F19 | Low | confirmed | ENV-001-vps.md:218, 220 | `find ~/…/data/transfer` prints absolute paths, so every line carries the macOS account name (scratch run) | The owner pastes the list as asked | The account name reaches the chat and the acquisition-host evidence in a public repo. AC-06's patterns do not look for it | `cd` into the folder and run `find .` (command below) | The line prints `./<file>` |
| F20 | Low | confirmed from the text | ENV-001-vps.md:8, 102, 118, 219 | C9 (line 8) covers only the moment before RDP opens. Seven "ส่งให้ Claude" steps follow RDP work, including the round trip from line 102 to line 109. No line says to disconnect before Claude, Codex or VS Code opens again. C8 is not checked during ENV-001 | The owner opens Claude while the RDP window is still open | An agent runs beside an open RDP window. This is the exposure that ENV-002 (ค) removes (contract line 324) | Header rule: disconnect RDP and log out of the console before agent apps open again. Line 219: host_report, then disconnect, then envcheck | The rule is in the header, and line 219 has that order |
| F21 | Low | confirmed | ENV-001-vps.md:36, 139, 158, 164, 168, 170 | No step says where to find the VPS IPv6 address. There is no command for the hotspot IPv6 test or for the hotspot check of a refused port. F16's repeat on the hotspot exists only through line 140. Nothing says to send the VPS page as text | A non-programmer reaches §7.3 or a refused port | Stuck or improvised steps, which risk an unmasked line or a screenshot. No AC can pass wrongly | Four one-line instructions (below) | Each step has a command or an explicit instruction |
| F22 | Low | confirmed | ENV-001-vps.md:209, 210, 213, 218 | No step creates `data/transfer` (`data/` is gitignored and untracked). `.DS_Store` breaks the "empty" check and the manifest match. T2 has no method. T3's report ends in FAIL, and line 118 says to fix every FAIL | First use of §10 | False FAILs and stuck steps. All of them fail safe | `mkdir -p`, a `.DS_Store` rule, a T2 command and a T3 note (below) | The four points are in §10 |
| F23 | Low | confirmed | ENV-001-vps.md:25, 34 | "C1" leaves out ENV-002 C1's "และรายการ PC ไม่ผูก credential". On macOS 26.6.2, Keychain Access is not in Utilities | The owner checks only the Settings list, or cannot find the app | A credential bound to a PC entry goes unchecked until ENV-002's C1 | Add the clause and a Spotlight hint | Line 25 has both |
| F24 | Low | question | ENV-001-vps.md:23, 179, 196 | "(ข้อความเท่านั้น)" is a VPS policy, not a client option. "ไม่ติ๊กอุปกรณ์ใด" may include Clipboard. Line 179 does not say "only this folder", but line 210 does | The owner unticks Clipboard; or the app pre-fills a folder (unknown) | The file control and the text test fail for client reasons. A wider folder is offered to the VPS during the test | Clipboard wording; "เพิ่มเฉพาะ" on line 179 | The wording is in lines 23, 179 and 196 |
| F25 | Low | confirmed | ENV-001-vps.md:3, 73 | The diff of §§2–6 shows two changes: §2.3 (allowed) and §3, which adds "OS Build 20348.2582". Line 3 says items 2–6 and 9 are unchanged | A reader relies on line 3 | No change in behaviour; the header is inexact | Remove the number from §3 (line 189 already has it), or name the exceptions in line 3 | The diff shows only the allowed change, or line 3 names both |
| F26 | Low | question | ENV-001-vps.md:144, 148, 158 | The `VPS=` lines are saved to `~/.zsh_history` and `~/.zsh_sessions` (`/etc/zshrc` lines 16–18, `/etc/zshrc_Apple_Terminal` line 102) | Normal use of §7 | Agent processes can read the VPS address after C9 ends | `read -r 'VPS?IP ของ VPS: '` | No `VPS=` line holds a real address |

### F17 · Medium · §10 has no failure path: a failed T1, T2 or T3 leaves the channel open
- **Where:** lines 208 and 211–216.
- **Evidence:**
  - Line 208 stops the owner on a failure and gives no further step: "ข้อใดของ T1–T4 ไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ และต้องตัดสินใหม่".
  - Step 4 (line 212) sets `fDisableCdm` to 0.
  - Step 5 (line 213) runs T2 and T3 and then the copy, in one step. The copy does not wait for T2 and T3 to pass.
  - The closing order (lines 214–219) comes after the copy, and no step sends a failed test to it.
  - The contract's closing order (contract lines 314–315) covers only the success path, and so does D-023 item 5. D-023 item 5 says "ข้อใดไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ".
- **Trigger:**
  - T2 fails at first use. This is exactly the event T1–T4 exist to catch: Windows App's folder redirection is unverified (how many shares, their names, what they reach).
  - A failed T3 has the same effect.
  - A failed T1 leaves the policy at 1, but the folder stays in the PC entry.
- **Impact:**
  - The VPS stays at `fDisableCdm` = 0, and the main PC entry keeps redirecting `~/Documents/GitHub/Sochron1k/data/transfer` read-write.
  - Every later connection opens the research host's data folder to the acquisition host, which by then holds the holdout vault (D-021 item 2). The natural next connection is the one the owner makes to investigate the failure.
  - Nothing in step 5 stops a copy after a failed T2.
  - Backstops exist but come late. `host_report.py` reports `drive_redirection` FAIL only when it is next run. T4 runs only on the success path.
- **Why Medium and not Low:**
  - No AC passes wrongly.
  - But a channel across the research/holdout boundary stays open with no written way to close it. That channel is one D-023 has not approved.
  - The trigger is the very outcome the T-tests are designed to find.
- **Minimal fix:**
  - Add one sentence after line 208 (or at steps 3 and 5): "ถ้า T1, T2 หรือ T3 ไม่ผ่าน: ห้ามคัดลอก · ทำข้อ 6.1–6.3 ทันที (เอาโฟลเดอร์ออกจากทุกรายการ PC → เชื่อมแล้วตั้ง `fDisableCdm` เป็น 1 → เชื่อมใหม่และตรวจ T4) แล้วจึงหยุดและส่งผลให้ Claude".
  - In step 5, add: "คัดลอกเฉพาะเมื่อ T2 และ T3 ผ่าน".
- **Proof of fix:**
  - §10 sends every failed T1–T3 to 6.1–6.3, ending at `fDisableCdm` = 1 with no folder in any PC entry.
  - The copy waits for T2 and T3.

### F18 · Low · The §7 send list includes `curl` lines that print full addresses
- **Evidence:**
  - Line 134 says the commands of §7 print masked lines: "พิมพ์บรรทัดที่**ปิดบังที่อยู่แล้ว**".
  - Lines 150 and 152 run `/usr/bin/curl -s https://api.ipify.org; echo`, which prints the hotspot's public IPv4 in full.
  - Line 170 asks for "ทุกบรรทัดที่คำสั่งพิมพ์ (ปิดบังแล้ว)".
  - Only line 154 says not to paste the address.
  - Contract AC-03 (2), line 263: "บันทึกเฉพาะ "ต่างจาก IP บ้าน: ใช่" (ไม่วาง IP)".
- **Impact:**
  - The hotspot address reaches the chat. AC-06's grep would catch it only in committed evidence.
  - The address belongs to the mobile carrier, so it is of low sensitivity. It is still the one value the contract says never to paste.
- **Minimal fix:**
  - Line 170: "ทุกบรรทัดที่ขึ้นต้นด้วย `port` หรือ `exit` (ไม่ส่งบรรทัดที่ `curl` พิมพ์ ซึ่งเป็น IP เต็ม)".
  - Line 134: add "ยกเว้นบรรทัดของ `curl`".

### F19 · Low · The §10 checksum list carries the macOS account name
- **Evidence:**
  - Line 218 prints absolute paths. On scratch files, each line printed `<sha256>  /private/tmp/…/transfer-probe/file one.parquet`.
  - Under `~`, each line therefore starts with `/Users/<macOS account name>/`.
  - Line 220 sends "รายการไฟล์และ SHA-256". Line 208 and D-021 place the results in committed evidence.
  - ENV-002 masks the account name in paths before anything is sent (ENV-002 runbook line 205: "ปิดบังชื่อบัญชีก่อนส่ง").
- **Minimal fix:** `% cd ~/Documents/GitHub/Sochron1k/data/transfer && /usr/bin/find . -type f ! -name .DS_Store -print0 | /usr/bin/xargs -0 /usr/bin/shasum -a 256`. On scratch files this printed `./file one.parquet` and `./sub dir/manifest.json`, and skipped `.DS_Store`.

### F20 · Low · Nothing says to close RDP before agent apps open again
- **Evidence:**
  - The header rule (line 8, C9) applies only before RDP or the console opens.
  - Seven "ส่งให้ Claude" steps follow RDP work: lines 36, 102, 118, 131, 197, 205 and 220.
    - At line 102 the owner sends the uv results, waits for Claude to push, then goes back to the VPS with the commit hash (lines 109–117).
    - At line 118 the owner sends DHCP rule names to Claude in the middle of a fix.
  - No line says to disconnect RDP and log out of the console before Claude, Codex or VS Code opens again.
  - Line 219 combines two things in one step: `host_report.py` on the VPS, and envcheck, which runs in VS Code (ENV-002 runbook item 3).
  - Contract line 324: "การป้องกันขณะ RDP เปิดคือ Quit แอปของ agent ก่อน (ENV-002 decision (ค))".
  - ENV-002 v2.6 line 20: "ขณะที่หน้าต่าง RDP เปิดอยู่ โปรเซสของ research identity มองเห็นและส่ง input เข้าหน้าต่างนั้นได้".
  - C8 (no agent app holds Screen Recording or Accessibility) is not in this runbook. ENV-002 checks it only after ENV-001 and SPIKE-002 (ENV-002 runbook line 3).
- **Impact:**
  - An agent may run beside an open RDP window while C8 is still unchecked.
  - During ENV-001 the VPS holds no holdout. Its screen does show the home address (§2.1) and, at §9, the MT5 account.
- **Minimal fix:**
  - Add a header line: "ก่อนเปิด Claude, Codex หรือ VS Code อีกครั้ง (รวมทุก 'ส่งให้ Claude' และ envcheck): ตัดการเชื่อม RDP ทุกหน้าต่างและ logout จาก console ก่อน · ข้อความที่จะส่งให้วางลง TextEdit ก่อนตัดการเชื่อม".
  - The TextEdit step keeps the text across the disconnect; whether the client clipboard keeps it on its own is unverified.
  - Line 219: run host_report, then disconnect, then run envcheck.

### F21 · Low · Four §7 steps lack a command or a source
- (i) **No source for the VPS IPv6 address.** Line 158 has `VPS6='<IPv6 ของ VPS>'`, but the §1.5 command (line 36) selects only `InterfaceAlias, PrefixOrigin`, and no other step reads the address. A provider page often shows a /64 prefix rather than the host address.
- (ii) **No command for the hotspot IPv6 test.**
  - Line 164 asks for 3389 over IPv6 from the hotspot without a command.
  - It names only the first line as its check ("ตรวจด้วยบรรทัดแรก").
  - The contract's F16 note (line 268) also asks for the repeat check there: "และบน hotspot เมื่อทดสอบ IPv6 ที่นั่น". The runbook carries that only through the general rule at line 140.
- (iii) **No command for the refused-port check.** Line 139 lets a refused port pass when "พอร์ตเดียวกันได้ timeout เมื่อทดสอบจาก hotspot". But §7.2 (line 151) tests only 3389.
- (iv) **The VPS page is not said to be text.** Lines 168 and 170 ask for "หน้าของ VPS". The header (line 7) allows text only, and no step says to copy the page as text.
- **Minimal fix:**
  - (i) Say where to read the address: the provider page, or on the VPS the read-only `(Get-NetIPAddress -AddressFamily IPv6 …).IPAddress` with §1.5's filter. Say it must not be pasted in the chat.
  - (ii) "บน hotspot ตั้ง `VPS6=` แล้วรันทั้งสี่บรรทัดของข้อ 3 ซ้ำ: ทุกพอร์ตรวม 3389 exit ไม่ใช่ 0 และตัวควบคุมทั้งสองสำเร็จ".
  - (iii) "บน hotspot ใช้บรรทัด `for` ของข้อ 1 โดยใส่แค่พอร์ตนั้น".
  - (iv) "คัดลอกเป็นข้อความ ไม่ส่ง screenshot".

### F22 · Low · §10 has gaps the owner meets at first use
- (i) **No step creates `data/transfer`.**
  - `data/` is gitignored (`.gitignore:34`).
  - Nothing is tracked under it on either branch: `git ls-files data` and `git ls-tree -r --name-only chore/ENV-002-macos-research-host -- data` are both empty.
  - Neither runbook has a `mkdir` for it.
  - On a missing scratch folder, `/bin/ls -A` printed "No such file or directory" and exited 1. So line 209's "ต้องไม่พิมพ์อะไร" fails, and the folder picker at line 210 has nothing to select.
- (ii) **`.DS_Store` breaks two checks.** Finder writes `.DS_Store` into folders it opens. On scratch files, `ls -A` listed it and `find -type f` hashed it. So "ว่าง" (line 209) and "เท่ากับ manifest" (line 218) can fail even when nothing was transferred.
- (iii) **T2 has no method.** Line 213, "จาก share นั้นเข้าไฟล์อื่นของ repo ไม่ได้", gives no command and no share name.
- (iv) **T3's report ends in FAIL.**
  - T3 (line 213) runs `host_report.py` while `fDisableCdm` is 0, so the report ends `HOST REPORT: FAIL` on `drive_redirection`.
  - Line 118 tells the owner to fix every FAIL: "ถ้าเป็น FAIL ทำตามคำแนะนำในคอลัมน์ Detail ทีละข้อแล้วรันใหม่".
  - The owner may then close the policy in the middle of the procedure.
- All four fail safe; none of them opens anything.
- **Minimal fix:**
  - (i) Add `% /bin/mkdir -p ~/Documents/GitHub/Sochron1k/data/transfer` before step 1.
  - (ii) Add "อย่าเปิดโฟลเดอร์นี้ใน Finder · `.DS_Store` ไม่นับ", and use the F19 command.
  - (iii) Give a concrete check, for example: `PS> Get-ChildItem -Force \\tsclient\<ชื่อ share>` shows only what `data/transfer` holds (nothing before the copy), with the share name recorded.
  - (iv) Add "ผลรวมเป็น FAIL ได้เพราะ `drive_redirection` · ดูเฉพาะ item `clipboard`".

### F23 · Low · The §1.2 check is shorter than the C1 it names, and Keychain Access is hard to find
- **The C1 clause.**
  - Line 25 reads "C1 Windows App → Settings → Credentials ไม่มีรายการของ VPS".
  - Contract lines 244–245 say that every "C1" here means ENV-002 v2.6's C1 (ENV-002 contract line 485). That C1 adds "และรายการ PC ไม่ผูก credential".
- **Keychain Access.** On this Mac it is at `/System/Library/CoreServices/Applications/Keychain Access.app`, not in `/Applications/Utilities` (checked with `ls -d`). So it is not where most guides point.
- **Impact:** a credential bound to one entry, such as the duplicate, waits until ENV-002's C1. C2 may be skipped. Both are re-checked before ENV-1 passes.
- **Minimal fix:**
  - Add "และทุกรายการ PC (รวมรายการที่ Duplicate) ไม่ผูก credential" to line 25.
  - Add "เปิด Keychain Access ด้วย Spotlight (⌘Space)".

### F24 · Low · question · Two PC-entry settings depend on unverified Windows App behaviour
- (a) **The clipboard wording.**
  - Lines 23 and 196 say: "แท็บ Devices & Audio: ไม่ติ๊กอุปกรณ์ใด · clipboard ตามที่เลือกใน (ค) (ข้อความเท่านั้น)".
  - The VPS enforces text-only through `SCClipLevel` = 1 (lines 69 and 72).
  - To my knowledge the client has only on or off, and in Microsoft Remote Desktop for Mac, Clipboard was a checkbox inside Devices & Audio. I did not verify this in Windows App.
  - ENV-002 C3 words it differently: "(Disabled หรือค่าที่ใช้ส่งข้อความตาม D-021 ข้อ 4)".
  - If the owner unticks Clipboard as a "device":
    - the Mac → VPS control (line 193) fails for the client's own reason, so the file test "proves nothing";
    - the text test (line 195) fails;
    - the VPS-side proof then rests on the policy read alone.
- (b) **The test folder.**
  - Line 179 adds `~/rdp-redirect-test` but does not say it must be the only folder. Line 210 does say so: "โฟลเดอร์อื่นต้องไม่อยู่ในรายการ".
  - r1's safety argument for this test ("only an empty folder is exposed") assumes it is the only folder.
  - Whether the app pre-fills a folder when Redirect folders is ticked is unknown.
- **Minimal fix:**
  - (a) "Clipboard: เปิด (VPS จำกัดเป็นข้อความเองด้วย `SCClipLevel`) · ปิดเฉพาะเมื่อ (ค) เลือกปิดทั้งหมด".
  - (b) Line 179: "เพิ่มเฉพาะ `~/rdp-redirect-test` · โฟลเดอร์อื่นต้องไม่อยู่ในรายการ".

### F25 · Low · §3 changed, although the header says the VPS items are unchanged
- **Evidence:**
  - A `diff` of §§2–6 between `57e2d1c` and `96f9656` finds two changed lines:
    - §2.3 (line 49) adds "(รายการ PC ที่ Duplicate ไว้)". This change is allowed.
    - §3 (line 73) adds "OS Build 20348.2582" after "KB5040437".
  - §9 is byte-identical.
  - Line 3 says "ขั้นบน VPS (ข้อ 2–6 และ 9) คงตาม v1.9".
- **Impact:** none on behaviour; the header is inexact.
- **Minimal fix:** either remove the build number from §3, since line 189 already carries "UBR ≥ 2582", or name both exceptions in line 3.

### F26 · Low · question · The real VPS address is saved in zsh history
- **Evidence:**
  - The `VPS='…'` and `VPS6='…'` lines are typed into Terminal.app's interactive zsh.
  - macOS `/etc/zshrc` sets `HISTFILE=${ZDOTDIR:-$HOME}/.zsh_history` and `SAVEHIST=1000` (its lines 16–18).
  - `/etc/zshrc_Apple_Terminal` keeps per-session history under `~/.zsh_sessions` (its line 102).
  - An interactive zsh started with only the system files reported `SAVEHIST=1000`.
- **Impact:**
  - Any process of the same macOS account can read the address, agents included once C9 ends.
  - The runbook's masking keeps the address out of the chat and the evidence, not out of files agents can read.
  - No credential is exposed. The Windows App entry holds the address too; I did not check where.
- **Minimal fix:** replace each assignment with `% read -r 'VPS?IP ของ VPS: '` (and the same for `VPS6`). Text read by `read` is not saved to history. I ran this syntax in zsh 5.9, non-interactively.
- **Whether this is wanted is the owner's call.**

## r3 F14–F16 (fixed in the runbook, as the contract's status line says)
| r3 ID | Status | Evidence |
|---|---|---|
| F14 | closed | Line 168: "**หน้าของ VPS ที่แสดง rule ทุกชุดที่ใช้กับ VPS นี้** (firewall, rule set หรือ security group ทุกตัวที่ผูกอยู่ หรือสถานะเปิดของ firewall ราย IP) … เกณฑ์ผ่านใช้กับ**ทุกชุดรวมกัน**". Line 21 adds the matching setup step: "ผูก rule ชุดนี้กับ VPS เครื่องนี้และเปิดใช้ · ถ้าผู้ให้บริการมี rule ชุดอื่นผูกกับ VPS อยู่แล้ว … ให้ถอดออก" |
| F15 | closed | Line 188: "`fDisableClip` นับเฉพาะเมื่อ (ค) เลือกปิด clipboard ทั้งหมด (ต้องเป็น 1) · ภายใต้ (ค) แบบข้อความ `fDisableClip` ว่างได้ ไม่ใช่ FAIL" |
| F16 | closed for the home run; the hotspot part rests on the general rule only (remainder: F21 (ii)) | Lines 157 and 160 run `nc -6 … ipv6.google.com 443` before and after the loop, and line 162 names them as the controls. The loop (line 159) has 3389 once, so 3389 is not a control. Line 140 applies "ตัวควบคุมทำทั้งก่อนและหลังการทดสอบ" to every sub-item |

## AC status (runbook coverage: does each clause have a step, and can a step pass wrongly)
| AC | Status | Why |
|---|---|---|
| AC-03 (v2.0) | every clause has a step · no wrong PASS found | (1): lines 142–147, with 3389 first and last, masked lines with nc's own exit status, and the message rules at 137–140. (2): lines 148–154, with `curl` before and after. (3): lines 155–165, with the F16 controls. (4): lines 166–169, with the F10 and F14 evidence. CGNAT: lines 17 and 169. C9: line 133. Remainders: F18, F21 |
| AC-04 (v2.0), test steps | every clause has a step · no wrong PASS found | Given: line 179 (one empty folder outside the repo, Printers ticked, tab values recorded). (a): lines 182, 183, 188, 189. `lpstat`: lines 176 and 191. (b): lines 193–194, with distinct file names. Text: line 195. (c): lines 184 and 190. (d): line 196. Remainder: F24 |
| AC-04 (v2.0), snapshot procedure (§10) | every element of D-023 item 5 has a step · not safe when a test fails | One folder and Read-only unticked: line 210. envcheck PASS and an empty folder first: line 209. T1: line 211. T2 and T3 before the copy: line 213. T4 after: lines 217–218. No VHD fallback: line 208. Closing order: lines 214–219. host_report and envcheck afterwards: line 219. Findings: F17 (Medium), F19, F22 |
| AC-01, AC-02, AC-05, AC-06, AC-07 | VPS steps unchanged apart from F25's text | §§4–6 and §9 are byte-identical. §2.3 has the allowed wording. The AC-06 patterns find no hit in the runbook |

## Ready for the owner to use the runbook: yes for items 0–9 · no for item 10 until F17 is fixed
**Items 0–9 (the rental and ENV-001's own AC-03 and AC-04): yes.**
- Every bullet of the contract's macOS list that concerns these items has a step.
- Every clause of AC-03 and AC-04 (v2.0) has a step.
- r3 F14–F16 are closed.
- The masked `nc` lines work on this Mac.
- No High or Medium finding touches these items.
- Worth fixing before the rental, because the owner meets them on the first day: F18, F20 and F23. F21 should be fixed before §7.3 is used.

**Item 10: no.**
- F17: a failed T1–T3 leaves the channel open with no written way to close it.
- Item 10 runs only after ENV-1 passes, so a one-sentence fix can land before then.
- Until F17 is closed, item 6 of the ENV-002 runbook (on the other branch) should keep its "ยังใช้ไม่ได้".

**Budget.** This was session 4 of the 4 that the v2.0 budget allows (contract line 332). A closure check of F17 needs the owner to allow one more fresh session.

Findings open: 10 (0 High · 1 Medium: F17 · 9 Low: F18–F26, of which F24 and F26 are questions)

## Checked, nothing found (and how)
**The change set.**
- `git diff --stat 57e2d1c..HEAD` shows two files.
- `96f9656` touches only the runbook (+98/−49).
- `c7b3a00` adds the three tagged notes. The word diff shows the F16 sentence at line 268, the F14 sentence at line 272, and "(FAIL)" expanded at line 321. Each matches r3's minimal fix.
- `8bc5cea` records the approval.
- Red flags:
  - `red-flags.sh 57e2d1c` and `red-flags.sh main` both report 0 pattern hits and no deleted tests.
  - Against `main`, the one control file listed is v1.x's `tests/acceptance/ENV-001/test_ac02_host_report.py`, which came in through D-006. This revision does not touch it.
- The worktree stayed clean.

**(f) The VPS items.**
- §§4–6 and §9 are byte-identical to v1.9. §2.3 has the allowed wording. The §3 change is F25.
- §1.4 and §1.5 are unchanged.
- §1.1 gained the attach/detach sentence:
  - That is outside the contract's list of items to rewrite.
  - But it is the setup step for r3 F14's evidence.
  - It runs in the provider console before any RDP session exists. The console is the fallback there, so the lock-out rule does not apply.

**(a) The header rules.**
- Line 8 carries ENV-002 C9 in full:
  - the list of apps to quit;
  - `/usr/bin/pgrep -ilf 'claude|codex|chatgpt'` in Terminal.app, which must print nothing;
  - a browser or profile without Claude or ChatGPT extensions;
  - `pgrep` again after the browser opens;
  - "รวมข้อ 0, 1.1 และ 1.5".
- Line 10, the lock-out rule, has:
  - the duplicated PC entry;
  - the note that this is not yet verified in the app;
  - the "ห้ามเปลี่ยน firewall" fallback.

  It is stricter than the contract: the duplicate is both set up like the main entry and deleted after use.

**(a) Items 0, 1.2 and 1.3.**
- Item 0 (line 17) uses `curl -s` or a browser. Only "ตรง/ไม่ตรง" is sent (line 18).
- "Ask when required" and "do not save the password" are set (lines 23–24).
- C1 and C2 run right after the first connection (line 25) and again at the end of 1.3 (line 34).
- The settings cover every PC entry, including the duplicate (lines 10 and 26).
- Summary row 1 records both checks.

**(a) Item 7.**
- The masked lines include nc's own exit status (lines 145, 151, 159).
- Usage and option errors are not results (line 137); neither are other messages (line 138).
- The refused rule (line 139) matches the contract word for word.
- There is a control after the tests at home (3389 is last at line 145) and on the hotspot (line 152).
- IPv6 has the F16 controls (lines 157–162).
- (4) has the F10 and F14 evidence (lines 167–168).
- The CGNAT result is included (line 169). C9 comes first (line 133). Summary row 7 matches.

**(a) Item 8.**
- (a): the command prints six values, including `fDisableClip` (line 182). The criterion counts five values, with F15 (line 188).
- `UBR` ≥ 2582 for build 20348, recorded in every case (lines 183 and 189). This is stricter than the contract, which asks for it only in the fallback of (b).
- `lpstat -p` runs before connecting (line 176), and the no-printer case is recorded (line 191).
- (b): the Mac → VPS control comes first, then VPS → Mac, with different file names. A FAIL is defined by the VPS file's name (lines 193–194).
- (c): `net view \\tsclient` runs beside File Explorer (lines 184 and 190).
- (d): every PC entry goes back to the C3 card state, and the test folder is removed and deleted (line 196).
- The §8.3 commands are read-only: `Get-ItemProperty`, `net view`, `Get-Printer`.
- §8.5 runs whatever the result, so the test settings are always undone.
- r2 F11 (c) and r3's request to name the file to copy are met: the file is `vps-to-mac.txt`.
- Summary row 8 matches.

**(a) Item 10.**
- Every element of D-023 item 5 is present (see the AC table).
- On the success path the closing order matches contract lines 314–315 and puts the policy back to 1 (line 216).
- Its cross-references with ENV-002 runbook items 3 and 6 agree.

**(b) Commands.**
- man pages confirm:
  - `nc` `-v`, `-z`, `-G conntimeout` ("TCP connection timeout in seconds") and `-6`;
  - `curl -s` (silent, no error text, so a failed call prints an empty line);
  - `lpstat -p`, `ls -A`, and `pgrep -f`, `-i`, `-l`;
  - `xargs` ("does not run the utility argument on empty input");
  - `shasum -a 256`, and zsh `print -r` with `--`.
- Runs:
  - The §7.1 loop printed `port 7000 exit 0: Connection to x.x.x.x port 7000 [tcp/afs3-fileserver] succeeded!` and `port 9 exit 1: nc: connectx to x.x.x.x port 9 (tcp) failed: Connection refused`. The §7.2 line behaved the same.
  - All 17 Mac command lines parse under `/bin/zsh -f -n`.
  - The checksum pipeline handled names with spaces and printed nothing on an empty folder.
  - The tools exist at the paths the runbook uses.

**(c) Masking.**
- nc prints the host string exactly as typed, in success and failure lines, for four forms of 127.0.0.1: `127.1`, `127.000.000.001`, `2130706433` and `0x7f.0.0.1`. The mask removed it each time.
- With a single `-v`, no src/dst block appeared, piped or on a pty, for a number or for `-4 localhost`. So the IPv6 control line, which is not masked, prints `ipv6.google.com` and no address.
- In zsh with default options, `${out//$VPS/…}` matches the value literally: a `*` in the value did not glob.
- So the masking holds for any text form the owner types. For IPv6 this is inferred from the shared message path; I did not run IPv6.
- An empty `VPS` garbles the line but leaks nothing.
- No step asks for a password, token or provider account name. The provider page is masked (line 168).

**(d) Safety.**
- The lock-out rule comes before every firewall change and restart: lines 10, 34, 35, 49–55, 75 and 118.
- §2.2 keeps v1.9's order, and line 49 proves a new session before the profile is set to Block.
- Folder redirection appears only at line 179 (the test folder) and line 210 (`data/transfer`). Everywhere else, Redirect folders is unticked (lines 23, 196, 215).

**(e) Can the owner run it.**
- The apps are named correctly: Terminal.app, Windows App from the Mac App Store, Finder, TextEdit, and on the VPS File Explorer and Notepad.
- `/System/Applications/Passwords.app` exists.
- The Windows App menu names are flagged as unverified (line 11), which is accepted.
- KB5040437 → "OS Build 20348.2582" is the implementer's claim from Microsoft Support. My own recollection and r3's agree, but I did not verify it.

**A known limit, not a finding.**
- In §8, an empty `\\tsclient` proves the VPS refused only if Windows App really offered the folder.
- The runbook records the tab values during the test (line 179) and proves the VPS side with the policy read (lines 182 and 188), as AC-04 requires.
- The only client-side control for folders is T2 in §10.

## Not checked (and why)
- **Windows App behaviour.** It is not installed. Unchecked: menu names, Duplicate, the save prompt, the clipboard option layout, file paste in either direction, whether the folder picker writes `.DS_Store`, pre-filled folders, the share name under `\\tsclient`, and whether copied text survives a disconnect.
- **`nc -6` and every remote host.** The rules limited me to 127.0.0.1. IPv6 masking is inferred, and I did not re-run the timeout path (r2 ran it on 127.0.0.2).
- **`curl` to `api.ipify.org`, the KB5040437 build, and provider firewall designs.** No network.
- **`lpstat -p` output on this Mac.** I read the man page only; running it would print the owner's printer names.
- **VPS-side output.** There is no VPS and no Windows machine; I read the PowerShell lines for syntax and for being read-only.
- **pytest.** The diff is documents only, and `uv run` would create `.venv` in the worktree.
- **The handoff.** After writing the findings I looked only at its log. Its last change is `ae7458a` (2026-11-05), and it has 0 lines matching "v2." or "macOS". PROGRESS.md is unchanged since `57e2d1c`.

## Blocks
- None. No hook or permission block occurred.
- **One deviation by me.** A parse-check command redirected stderr to `/tmp/zsh_n_err_ignore`, which created an empty file (0 bytes) outside my allowed scratch folder.
  - Nothing else outside `/private/tmp/claude-501/-Users-faztycoding-Documents-GitHub-Sochron1k/38a03acd-6822-4cac-ae23-d960d6191884/scratchpad/env001-runbook-r1/` was created or changed.
  - I left the file in place; `rm /tmp/zsh_n_err_ignore` removes it.
