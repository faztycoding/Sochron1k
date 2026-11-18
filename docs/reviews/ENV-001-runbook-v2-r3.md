# Review ENV-001 runbook (macOS, contract v2.2) round 3 (closure check of r2 F27–F30) · base 157f8a9 · head 7b5b9a8 · reviewer Claude Code, fresh subagent session (fresh-eyes-reviewer), session 6 (allowed by the owner beyond the budget of 4)

File: `docs/reviews/ENV-001-runbook-v2-r3.md` · date 2026-11-18 · branch `chore/ENV-001-vps-acquisition-host`.
- HEAD was `7b5b9a8` before and after this review, and tracked files did not change.
- One ignored folder appeared during the session. Blocks has the details.

**Scope.**
- This is a re-review round, per the "Re-review rounds" section of `.agents/skills/cross-agent-review/SKILL.md`. It re-checks only r2's F27–F30 and their surrounding impact.
- **Fix commits:**
  - `5749c40`: F27
  - `5c26adb`: F28
  - `e725399`: F29
  - `338a7a0`: F30
  - `fe80c9e` is r2 itself, and `7b5b9a8` adds the findings response to `docs/handoff/ENV-001.md`.
- **Oracle:** the contract section "v2.0: ขั้นฝั่งเครื่องเจ้าของบน macOS" (v2.2, approved 2026-11-18), with its notes "หลังอนุมัติ v2.2".
- **References** on `chore/ENV-002-macos-research-host` (`6329d32`), read with `git show` only:
  - D-021 item 3 (a) and D-023 item 5;
  - the ENV-002 runbook, items 3 and 6;
  - PROGRESS.md, for the budget and binding records.
- Line numbers refer to `docs/runbooks/ENV-001-vps.md` at `7b5b9a8` unless another file is named.

**Label.**
- **Who:** one fresh Claude session, run as a read-only subagent.
  - It did not write the runbook, the fixes, r1 or r2.
  - It was given no implementer reasoning: the caller gave commit hashes and the location of the response section only.
- **Budget:** the v2.0 budget is 4 fresh sessions (contract line 332). r1 used the fourth and r2 the fifth, so this is the sixth.
  - The caller states that the owner allowed this session on 2026-11-18 ("อนุญาต 1 session (Recommended)").
  - The repository does not record that yet:
    - the handoff at `7b5b9a8` says "the owner decides";
    - PROGRESS.md on the ENV-002 branch (`6329d32`, line 6) says the closure check "ต้องใช้ session ที่ 6 เกินงบ: รอเจ้าของ".
- **Binding:** same as r1 and r2.
  - Contract lines 326–327 name a fresh Claude session as the v2.x reviewer.
  - PROGRESS.md line 5 records the ENV-001 role swap. No PROGRESS line names ENV-001 v2.x.
  - If the owner does not read those records as the binding, this file is a pre-review (Claude subagent).

## How I verified, and the limit of it
**Order.**
1. The skill file, r2 in full, and the contract's v2.0 section (lines 238–358).
2. Each fix commit (`git show`), then `git diff --stat` and `git diff --word-diff=plain 157f8a9 7b5b9a8` for the runbook.
3. The whole runbook at `7b5b9a8`.
4. The ENV-002-branch references, then `scripts/env/host_report.py` for the value that T4's new read and 6.5 share.
5. The probes below.
6. I wrote the closure verdicts and F31–F32, and only then read the handoff's "Runbook closure check r2 and findings response".
   - It accepts all four IDs and names the same commits.
   - It changed none of my verdicts.

**Runs on this Mac** (macOS 26.6.2 arm64, zsh 5.9). Every file I created is in `…/scratchpad/env001-runbook-r3/`.
- `/bin/zsh -f -n` on the 18 `%` command lines, extracted from the file at `7b5b9a8`: 14 in code blocks, and the inline commands on lines 18, 194 and 197.
- Step 1 and 6.4 exactly as printed, under `env -i HOME=<fake home> /bin/zsh -f`, with the fake home as the current folder (as in a new Terminal window).
  - Six folder states.
  - The `157f8a9` forms run in the same states, for comparison.
- The step 1 line in `zsh -f -i` fed by a pipe, with a `!!` control first.
- `read -r` with one and with two piped lines, using documentation addresses (`2001:db8::/32`).
- `nc -vz` against 127.0.0.1 port 9 (closed), with the host typed as `127.0.0.1` and as `127.1`, then the runbook's mask.

**Limits.**
- No network beyond 127.0.0.1.
- No Windows App, VPS, PowerShell or provider console on this Mac. I read line 211's console step and T4's new PowerShell line by eye.

## Closure of r2 F27–F30
| ID | Status | Diff | Evidence and confirmation |
|---|---|---|---|
| F27 (Low) | **closed** | `5749c40` · lines 210, 211, 226 | **All three parts of r2's proof are present.** **(1) T4 reads the value on both paths.** Line 226 adds `PS> Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' \| Select-Object fDisableCdm` "(PowerShell ธรรมดา; อ่านอย่างเดียว) แสดง 1". The failure path runs T4 too (line 210, "เชื่อมใหม่และตรวจ T4"). The key string is identical in §3 (line 62), §8.3 (183), step 4 (221), 6.2 (225) and T4 (226) (grep). It is also the value that host_report's `drive_redirection` reads first: `rdp_setting` → `policy_first(policy, winstation)` (`scripts/env/host_report.py` lines 63, 170–176, 794–797, 872). **(2) The failure path ends with 6.5.** Line 210: "ทำข้อ 6.1–6.3 แล้วข้อ 6.5 ทันที (… → `host_report.py` และ envcheck; บันทึกผลตามจริง, r2 F27) แล้วจึงหยุดและส่งผลให้ Claude". **(3) A failed 6.2 connection or a failed T4 has a step.** Line 211 is r2's text word for word. **Residual (F31):** line 211's branch writes from the console without reading the value back, and it skips 6.4 and 6.5 |
| F28 (Low) | **closed** | `5c26adb` · lines 216, 218, 229, 231 | **Lines 216 and 229** are r2's commands: `cd ~/Documents/GitHub/Sochron1k/data/transfer && /usr/bin/find …`. **Lines 218 and 231** add "ถ้า `cd` ขึ้น error: หยุด ไม่ส่งผล (r2 F28)". **Parse:** both lines, and the other 16 `%` lines, give rc 0 under `/bin/zsh -f -n`. **Regression run** (fake `HOME`, folder missing): the `157f8a9` two-line 6.4 form printed the `cd` error and then hashed `./Desktop/private notes.txt` and `./Documents/tax return 2025.pdf`. The chained line printed only `cd:1: no such file or directory: …`, with exit 1. With the folder present, both forms printed the same four `./` lines. The full table is below |
| F29 (Low) | **closed** | `e725399` · line 242 | Row 7 is r2's text plus "; r2 F29": "บรรทัดที่ขึ้นต้นด้วย `port` หรือ `exit` (ปิดบังแล้ว; ไม่ส่งบรรทัดของ `curl`; r2 F29), "ต่างจาก IP บ้าน: ใช่", …". "ผลของ hotspot" is gone, so no wording pulls in `curl`'s output. Row 7 names the same lines as 7.5 (line 171); the comparison is below. Contract line 316's "ข้อความและ exit status ทุกพอร์ต" is carried by every `port` line (`port $p exit $code: <message>`, lines 146, 152, 160). **Residual (F32):** the cell's last parenthesis masks only the IP |
| F30 (Low) | **closed** | `338a7a0` · line 156 | **The fix.** Line 156 adds "ที่ `read` วางที่อยู่เดียว บรรทัดเดียว (ถ้าคำสั่งพิมพ์หลายที่อยู่ ใช้ที่อยู่แรก; r2 F30)". That is r2's text, at the place r2 named. It sits in 7.3's lead-in, so it governs line 159 and the hotspot repeat (line 165, "ตอบ `read` ด้วยที่อยู่เดิม"). **Run,** with lines piped into `zsh -f`. With two lines at `read -r VPS6`, `VPS6` held `[2001:db8::1]` and `2001:db8::2` stayed in the input. An interactive shell runs that leftover at the next prompt (r2's pty run). With one line and spaces around it, `VPS6` held `[2001:db8::1]` and nothing was left. **Masking holds for any one-line form.** `nc -v` prints the host as typed (`nc: connectx to 127.1 port 9 (tcp) failed: Connection refused`), and the runbook's mask turned it into `x.x.x.x` |

## Surrounding impact

### F27: the three questions
**Do both paths of item 10 end with `fDisableCdm` read back as 1?** Yes, whenever T4 passes.
- **Success path:** T4 (line 226), then 6.5's host_report (line 232), which reads the same value again.
- **Failure path** (a failed T1, T2 or T3): line 210 runs T4 and then 6.5.
- **After a failed T1:**
  - T4's 1 does not show that the VPS enforces the setting; T1 showed that it did not.
  - There, the client side is what closes the channel, and line 209 makes the channel unapproved. This follows D-023 item 5: "ข้อใดไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ".
- **When T4 fails or 6.2 cannot connect,** line 211 governs instead. That branch ends without a read (F31).

**Does line 211's step leave anything open?**
- **The VPS layer:** possibly. The console write is never read back (F31 (a)).
- **The client layer:** held, not repaired.
  - "ห้ามเชื่อมด้วยรายการ PC ที่ยังมีโฟลเดอร์" forbids reusing the entry. The owner then stops and Claude decides.
  - That is a reasonable holding state when 6.1's edit did not hold.
- **A session that still shows a share at T4:** it ends before any agent app opens.
  - The header rule (line 9) disconnects every RDP window before Claude opens.
  - C9 (line 209) has held since item 10 began.
  - A console login with the same account should also take over that session (line 11's one-session rule). This is not verified.
- **The post-send checks:** none run on this branch, even after a copy (F31 (b)).
- **"T4 ไม่ผ่าน" also covers a failed 6.3 reconnect,** because T4 cannot pass then. This is a matter of reading, not a finding.

**Does the failure path's added 6.5 conflict with the rest of item 10 or the header rules?** No.
- **C9:** the failure path opens nothing that the success path does not open; 6.2 and 6.3 are on both paths.
- **Disconnect before an agent app opens:** line 9 names "ก่อนรัน envcheck ของ ENV-002".
  - 6.5 disconnects RDP before envcheck.
  - Its "(กติกาบนหัวไฟล์)" carries the TextEdit step.
  - envcheck itself first closes every agent session and reopens VS Code without the agent panel (ENV-002 runbook line 51). This is the same on both paths.
- **"เป็น PASS (ข้อ 6)":**
  - §6 tells the owner to fix FAIL items. Line 210's "บันทึกผลตามจริง … แล้วจึงหยุด" makes the failure path record the result and stop instead.
  - After a failed T3, 6.5's `clipboard` item reads the same values T3 read, so "record as is" is the only reachable outcome there.
- **The failure path skips 6.4.** No copy was made. Anything left in `data/transfer` stops the next run at step 1's emptiness check (lines 216–218).

### F28: the chained lines, run on fake homes
The current folder was the fake home in every run. "—" means the case does not apply.

| Folder state | Step 1 (line 215, then 216) | 6.4 (line 229) | `157f8a9` form, same state |
|---|---|---|---|
| `data/transfer` missing | `mkdir -p` creates it, then prints nothing (exit 0) | only the `cd` error, exit 1 | 6.4 hashed `./Desktop/private notes.txt` and `./Documents/tax return 2025.pdf`, exit 0 |
| `data` is a regular file | `mkdir: …/data: Not a directory`, then only `cd:1: not a directory: …` (exit 1 each) | — | step 1 listed `./Desktop`, `./Desktop/private notes.txt`, `./Documents`, … `./Documents/tax return 2025.pdf` |
| `Documents` at mode 000 (stands in for a refused folder) | `mkdir: …/Documents/GitHub: Permission denied`, then only `cd:1: permission denied: …` | only the `cd` error, exit 1 | — |
| `file one.parquet`, `sub dir/x.parquet`, `.hidden`, `manifest.json`, `.DS_Store` at two depths | the five `./` entries, no `.DS_Store` | four `./`-relative hash lines | identical to the new 6.4 |
| empty · `.DS_Store` only | nothing | nothing | — |

- **Precedence:** `|` binds tighter than `&&`, so a failed `cd` skips the whole `find | xargs` pipeline. The rows above show this.
- **Interactive zsh:** run through `zsh -f -i` fed by a pipe.
  - The `!!` control expanded, so history expansion was on.
  - The step 1 line still ran and listed the folder, with no "event not found".
  - `HISTFILE` was unset and `SAVEHIST=0`, so no history file was written.
- **The error lines** carry the absolute path, and so the account name. Lines 218 and 231 say not to send them.

### F29 and F30: row 7, the paste rule, item 7.5 and the masking rules
| What is sent | Item 7.5 (line 171) | Row 7 (line 242) |
|---|---|---|
| masked lines | "ทุกบรรทัดที่ขึ้นต้นด้วย `port` หรือ `exit` (ปิดบังแล้ว) พร้อมเวลา" | the same lines, without "พร้อมเวลา" |
| `curl` | "ไม่ส่งบรรทัดที่ `curl` พิมพ์" | "ไม่ส่งบรรทัดของ `curl`" |
| hotspot | "ต่างจาก IP บ้าน: ใช่" | the same |
| IPv6 | "ผลของข้อ 3 (หรือ "IPv6 ไม่ได้ทดสอบ")" | the same |
| provider evidence | "รายการ rule และหน้าของ VPS ในข้อ 4". In 7.4, the rule list masks the IP, and the VPS page reads "ปิดบัง IP และชื่อบัญชี", as text | "(ปิดบัง IP)" → **F32** |

- **"พร้อมเวลา":** row 7 never had it (it is also absent at `96f9656`), and no contract clause asks for it in row 7. Not a finding.
- **The paste rule and the masks agree.**
  - The rule makes `read` hold exactly one address, and the mask replaces exactly that string.
  - `nc` prints the host as typed (the `127.1` run), so the mask matches whatever form the owner pastes.
- **What the `port`/`exit` rule sends:**
  - Lines that start with `port` or `exit` hold no address, no account name and no `curl` value.
  - The `read` echo starts with the prompt ("IP…" or "IPv6…"), and the shell prompt line starts with the account name. Neither line is sent.

### No step removed
- **The word diff** (`git diff --word-diff=plain 157f8a9 7b5b9a8 -- docs/runbooks/ENV-001-vps.md`) has four hunks. Every change is an insertion, except:
  - `%` → `&&` twice: two lines joined into one, with the same commands;
  - "share และแท็บ" → "share, แท็บ": a comma before T4's new third condition;
  - row 7's first two items, replaced by F29. The removed words were "(ข้อความและ exit status ของทุกพอร์ต, ปิดบังแล้ว)" and "ผลของ hotspot". The `port` lines and "ต่างจาก IP บ้าน: ใช่" carry them.
- **Untouched parts:** §§0–9 are unchanged apart from line 156, and summary rows other than 7 are unchanged.

## New findings
| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|---|---|---|---|---|---|---|---|---|
| F31 | Low | confirmed from the text (contract clause) | ENV-001-vps.md:211 (vs 226, 229–232) | Line 211 ends "ตั้ง `fDisableCdm` เป็น 1 จาก console ของผู้ให้บริการ (PowerShell แบบ Administrator) · หยุดและส่งผลให้ Claude". It has no read-back and no 6.4 or 6.5. Contract lines 293–294 require "การรัน `host_report.py` และตัวตรวจของ ENV-002 ซ้ำหลังส่งทุกครั้ง" | T4's new read shows 0 (6.2's write did not take effect), or 6.2 cannot connect. On the success path, both happen after the copy | (a) The policy can stay at 0 with no step on this branch showing it. (b) After a copy, no file list, host_report or envcheck runs before Claude opens | Read the value back in the console, then 6.4 (after a copy) and 6.5, then stop (text below) | Line 211's branch ends with `fDisableCdm` read back as 1, and with host_report and envcheck results, plus the file list after a copy |
| F32 | Low | confirmed from the text (contract clause) | ENV-001-vps.md:242 (vs 169, 171) | Row 7 masks "rule ของผู้ให้บริการและหน้าของ VPS ที่แสดง rule ทุกชุด (ปิดบัง IP)". Item 7.4 (line 169) and contract line 272 say "ปิดบัง IP และชื่อบัญชี" | The owner sends from the summary table (F29's trigger) | The provider account name shown on the VPS page can reach the chat and the evidence | Row 7's last parenthesis: "(ปิดบัง IP และชื่อบัญชี)" | Row 7's masking matches line 169 and contract line 272 |

### F31 · Low · Line 211's branch writes `fDisableCdm` from the console without reading it back, and skips 6.4 and 6.5
- **Where:** line 211. Compare line 226 (T4's read) and lines 229–232 (6.4 and 6.5).
- **Evidence:**
  - Line 211 sets the value from the console and then says "หยุดและส่งผลให้ Claude". It has no read, no 6.4 and no 6.5.
  - Three sources require the post-send checks:
    - contract lines 293–294: "การรัน `host_report.py` และตัวตรวจของ ENV-002 ซ้ำหลังส่งทุกครั้ง";
    - D-023 item 5: "รัน `host_report.py` และ envcheck ให้ PASS, บันทึกรายการไฟล์และ SHA-256";
    - ENV-002 runbook item 6 (its line 192): "รันข้อ 3 ของ runbook นี้ซ้ำทุกครั้งหลังส่ง".
  - The two main paths meet these. The success path runs 6.4 and 6.5 before item 7's send, and the failure path now runs 6.5 (line 210).
- **Trigger:**
  - T4's new read shows 0. The likeliest cause is the one r2 named for F27: 6.2's write ran in a PowerShell not opened as Administrator.
    - Line 211's console write uses the same command and asks for the same kind of shell, so the same slip can repeat.
  - Or 6.2 cannot connect, for example because the home IP changed during the procedure.
  - On the success path, both cases happen after the copy at step 5.
- **Impact:**
  - **(a)** If the console write also fails, the owner stops with the VPS policy at 0, and no step on this branch shows it.
    - This is r2's F27 impact, one step later.
    - What limits it: the T4 result that the owner sends does show the first failure.
  - **(b)** After a copy, none of the file list, host_report or envcheck runs before "ส่งผลให้ Claude" opens Claude.
    - The same holds on the failure path when T4 also fails, after T2 or T3 had offered the folder read-write.
    - These are the checks the contract requires after every send.
- **Why Low:** it needs a failed 6.2 or a failed T4, and (a) also needs a second failed write.
- **Minimal fix** (line 211): "… ตั้ง `fDisableCdm` เป็น 1 จาก console ของผู้ให้บริการ (PowerShell แบบ Administrator) แล้วอ่านกลับด้วยบรรทัด `Get-ItemProperty` ของ T4 ใน console เดียวกัน (ต้องแสดง 1) · ทำข้อ 6.4 ถ้าคัดลอกแล้ว และข้อ 6.5 (รัน `host_report.py` ใน console ได้; บันทึกผลตามจริง) · หยุดและส่งผลให้ Claude".

### F32 · Low · Summary row 7 masks only the IP on the VPS page; item 7.4 and the contract also mask the account name
- **Evidence:**
  - Row 7 (line 242) ends "rule ของผู้ให้บริการและหน้าของ VPS ที่แสดง rule ทุกชุด (ปิดบัง IP)".
  - Item 7.4 (line 169): "หน้าของ VPS ที่แสดง rule ทุกชุด … ปิดบัง IP และชื่อบัญชี · คัดลอกเป็นข้อความ".
  - 7.5 (line 171) sends "หน้าของ VPS ในข้อ 4", so it carries 7.4's rule.
  - Contract line 272: "(ปิดบัง IP และชื่อบัญชี)".
  - The header (line 7) masks the IP and "เลขบัญชีเต็ม", but not an account name. Nothing else in the file backstops row 7.
  - **History:** the ending dates from `96f9656` (row 7 is at line 229 there). r2's F29 fix text kept it, and `e725399` copied that text.
- **Trigger:** the owner sends from the summary table. r2 accepted this trigger for F29.
- **Impact:** the provider account name shown on that page, often a login e-mail, can reach the chat and the committed evidence. The contract requires it masked.
- **Minimal fix:** row 7's last parenthesis reads "(ปิดบัง IP และชื่อบัญชี)".

## AC status (runbook coverage after the fixes)
| AC | Status | Why |
|---|---|---|
| AC-03 (v2.0) | every clause has a step · no wrong PASS found | This range changes line 156 (the paste rule) and row 7. Remainder: F32, in a summary cell; item 7.4 itself is right |
| AC-04 (v2.0), test steps (§8) | not touched in this range | — |
| AC-04 (v2.0), snapshot procedure (§10) | every element of D-023 item 5 and the contract's closing order has a step on both main paths · both now read `fDisableCdm` back | Remainder: F31, the line 211 branch |
| AC-01, AC-02, AC-05, AC-06, AC-07 | not touched in this range | The diff touches §7.3, §10 and row 7 only |

## Ready for the owner to use the runbook: items 0–9 yes · item 10 yes
**Items 0–9 (the rental, and ENV-001's own AC-03 and AC-04): yes.**
- F29 and F30 are closed.
- F32 is two words in the summary table, and item 7.4 already masks the account name. Fix it before the rental if convenient.

**Item 10: yes.**
- F27 and F28 are closed.
- F31 needs a failed 6.2 or a failed T4. Fix it before item 10's first use, which comes only after ENV-1 passes.
- ENV-002 runbook item 6 (its line 192) already says "ใช้ได้หลัง ENV-1 ผ่านเท่านั้น". Its note that F27–F30 have no closure reviewer goes out of date once this file is saved. Updating it is a follow-up on that branch.

**Budget.** This was the sixth session. Checking F31 and F32 would take another, and that is the owner's call. The fixes are one sentence (F31) and two words (F32).

Findings open: 2 (0 High · 0 Medium · 2 Low: F31, F32). Closed in this round: 4 (r2's F27–F30).

## Checked, nothing found (and how)
**The change set.**
- `git diff --stat 157f8a9 7b5b9a8` lists three files: the runbook (+9/−9), r2 itself, and the handoff (+15).
- Each fix commit touches only the runbook lines its message names. `7b5b9a8` touches only the handoff.
- The handoff's table matches the commits. Its statement that "each fix only adds a step or narrows what is sent" matches the word diff.

**Red flags.**
- `bash scripts/controls/red-flags.sh 157f8a9` reports 0 pattern groups with hits, no deleted tests, no untracked files and no control files.
- `… main` also reports 0 pattern groups. The only control file it lists is v1.x's `tests/acceptance/ENV-001/test_ac02_host_report.py` (D-006), which this range does not touch.

**Commands.**
- All 18 `%` lines parse under `/bin/zsh -f -n`.
- T4's new PowerShell line has the same form as §8.3's read and uses the same key string.

**Line 231's stop.**
- At 6.4, T4 has already read 1 and the folder is out of every PC entry, so stopping there leaves nothing open.
- The stop keeps home-folder names out of the send.
- The likely cause is a mistyped command, which the owner corrects.

**F30's "ใช้ที่อยู่แรก".** It picks the address that `read` already took from a multi-line paste before the fix. The tested address does not change; only the leftover lines stay out of history.

**D-021 item 3 (a) and D-023 item 5.** On both main paths of §10, every element is still present:
- one folder, with Read-only unticked;
- envcheck PASS and an empty folder first;
- T1–T4;
- the closing order;
- host_report and envcheck afterwards;
- the file list with SHA-256.

**The worktree:** HEAD `7b5b9a8`, `git status --porcelain` empty and no stash, before and after.

## Not checked (and why)
**Windows App, PowerShell and the provider console.** None of them is on this Mac, so these are unchecked:
- that T4's read works in a non-elevated shell;
- whether a console login takes over the RDP session;
- whether the provider console can copy text out. This matters for F31's fix: the owner may have to type the value.

**The real macOS privacy prompt for Terminal.app's Documents access.** I stood in for it with mode 000 and with a regular file named `data`. If macOS let `cd` succeed and blocked only reads, `find` would still run only inside `data/transfer`. Either way no home-folder names appear, but this is reasoned, not run.

**IPv6.** No `nc -6` and no remote host.
- The as-typed echo was shown for IPv4 (`127.1`) only.
- For IPv6 it is inferred from the same message format.

**Outside this round's IDs: which IPv6 address is tested.**
- Line 156's filter, inherited from §1.5, does not exclude ULA (`fc00::/7`) or transition addresses. If one of those were listed first, it would be the one tested.
- The IPv6 round cannot tell a wrong address from a closed one, because every port failing is its expected result.
- F30's fix does not change this. The outer layer is still proven by 7.4's rule evidence.

**Also outside this round's IDs:** 6.4 still has no step for a list that differs from the manifest. This is unchanged, as r2 noted.

**Not run:**
- pytest: the diff is documents only, and `uv run` would create `.venv` in the worktree.
- AC-06's three patterns: not re-run, because this range does not touch the VPS steps.

## Blocks
- None. No hook or permission block occurred.
- **Disclosures:**
  - **My mistake.** One `git show … > …` redirect wrote `env002-runbook-ignore.txt` directly in the scratchpad, outside the probe folder.
    - I moved it with `mv -n` to `…/env001-runbook-r3/env002-runbook.txt`. Nothing was deleted.
    - It holds the ENV-002 runbook text from the pushed branch and no secrets.
  - **Probe folder:** `/private/tmp/claude-501/-Users-faztycoding-Documents-GitHub-Sochron1k/38a03acd-6822-4cac-ae23-d960d6191884/scratchpad/env001-runbook-r3/`. It holds:
    - the runbook at `7b5b9a8` and at `157f8a9`;
    - `lines/`, with the extracted `%` lines and their parse results;
    - fake homes `homeA`–`homeF` (`homeB/Documents` was set to mode 000 and restored to 755);
    - an empty `zdot/`;
    - `env002-runbook.txt`.
  - **Reads beyond the caller's list:**
    - PROGRESS.md on the ENV-002 branch, via `git show`, for the budget and binding records;
    - `.claude/settings.json` in the main checkout, read-only, to check its hooks.
  - **Tools beyond the caller's list,** each read-only or limited to the probe folder:
    - `grep`, `sed`, `awk`, `cut`, `stat`, `ls`, `find` and `shasum`;
    - `mkdir`, `mv` and `chmod`, inside the probe folder only;
    - `env -i`, `sw_vers` and `uname`;
    - `zsh -f -i` fed by a pipe;
    - `nc` to 127.0.0.1 only, typed once as `127.1`.
  - **An ignored folder appeared in the worktree during this session.**
    - `scripts/env/.mypy_cache/` (subfolder `3.14`, plus `CACHEDIR.TAG`) was created at 22:39:22 +07.
    - I ran no mypy and nothing that writes into the worktree, and no hook in `.claude/settings.json` runs mypy. Its origin is unknown.
    - Tracked files are unchanged, and I left the folder in place.
  - **Other sessions' folders.** Two scratchpad folders (`chore003-r1`, `work-r6`) changed during this session. None of my commands named them.
  - **Host name.** The interactive zsh prompt printed this Mac's host name; it is not reproduced here.
