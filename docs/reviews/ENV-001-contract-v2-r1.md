# Review ENV-001 contract v2.0 · round 1 · base `9157950` (v1.9) · head `5a3a24f` · reviewer: one fresh Claude session, read-only · 2026-11-18

File: `docs/reviews/ENV-001-contract-v2-r1.md`. Scope: the section "v2.0: ขั้นฝั่งเครื่องเจ้าของบน macOS" (lines 238–300) and the (v2.0) edits at lines 3, 4, 7, 179 and 180 of `docs/contracts/ENV-001-vps-acquisition-host.md`, branch `chore/ENV-001-vps-acquisition-host`.

**Label.** This is contract review round 1 of ENV-001 v2.0 (High tier). One fresh Claude session did it. That session did not write the draft and did not see the drafting conversation.

Inputs:
- the contract and the diff `9157950..5a3a24f`
- the v1.9 runbook `docs/runbooks/ENV-001-vps.md`
- from branch `chore/ENV-002-macos-research-host`: D-021, D-023, ENV-002 contract v2.6 and PROGRESS.md (read with `git show`; that working tree was not touched)

On the reviewer binding, PROGRESS.md records two things:
- On the ENV-001 branch, the owner kept the role swap for ENV-001: reviewer = fresh Claude session, "คงการสลับบทบาท แม้โควตา Codex กลับมาแล้ว".
- On the ENV-002 branch, the owner confirmed ENV-002 (ซ) on 2026-11-18 11:2x.

No PROGRESS line names ENV-001 v2.0 itself yet. If the owner does not read those records as covering this revision, this file is a pre-review (Claude subagent) and does not replace the binding review.

## Verdict
**Not ready for the owner's approval.** There are four Medium findings. All of them are fixed by text changes, with no code:
- **AC-03:** two clauses can pass for reasons other than a closed VPS.
  - The hotspot test has no control (F1).
  - The contract's reading of `Connection refused` is unreliable and has no pass rule. ENV-002 v2.6 points back to this text for that rule (F2).
- **AC-04:** it can pass because of the Mac rather than the VPS policy (F3). The Mac may have no printer, Windows App's file-clipboard support is unknown, and the in-test redirect state is not recorded.
- **Recovery:** it tells the owner to use v1.9 from the old Windows machine, which accepted D-023 forbids (F4).

The rest does what it says:
- Only the owner-side text changed: one file, lines 3, 4, 7, 179, 180 and the appended section.
- The red-flag scan found 0 hits.
- The VPS steps, `host_report.py`, tests and AC-01, AC-02, AC-05–AC-07 are untouched.
- The `nc` and `smbutil` facts are true on this Mac.
- The v2.0 AC-03 and AC-04 keep every v1.9 clause.

## Findings
Line numbers refer to `docs/contracts/ENV-001-vps-acquisition-host.md` at `5a3a24f` unless another file is named.

| ID | Sev | Kind | File:line | Finding | Owner decision |
|---|---|---|---|---|---|
| F1 | Medium | confirmed | 252-253 | AC-03 (2): the hotspot test has no control. Any `nc` failure counts as the pass, including a hotspot with no data or a tool error | no |
| F2 | Medium | confirmed | 251-252, 255-256 | The reading of `Connection refused` is unreliable and no rule says which explanation passes. By the text's own reading a refused port means an open outer layer, yet AC-03 passes. (4) has no pass rule | no |
| F3 | Medium | confirmed | 258-262 | AC-04 can pass because of the Mac, not the VPS: no printer to redirect, Windows App file-clipboard support unknown, in-test redirect state unrecorded | yes (printer method, Q2) |
| F4 | Medium | confirmed | 293 | Recovery says v1.9 "ยังใช้ได้จากเครื่อง Windows เดิม", which D-023 item 2 path 1 (accepted) forbids. D-023 item 6 also requires this revision before renting | yes (Q1) |
| F5 | Low | confirmed | 250-251, 253-254 | `nc` prints the full VPS address on every line, and AC-03 asks for those lines without saying to mask them. (3) takes its criterion from runbook 7.3, which counts 7 ports | no |
| F6 | Low | confirmed | 262-264, 266, 274-275 | The §10 bullet drops conditions of D-023 item 5 and the v1.9 close-out order. "ขั้นบน VPS คงเดิม" is not exact for §10 | no |
| F7 | Low | confirmed | 267-268, 270-271 | The header rule drops C9's browser clause. §1.2 checks only Windows App's list, so the Keychain check (C2) waits until after SPIKE-002 | no |
| F8 | Low | confirmed | 7, 256, 268, 271, 283, 285, 299 | ENV-002 labels are cited without version or branch, and on this branch ENV-002 is v1.5. No merge-order or D-023-revocation statement. Line 7 still says "D-021 (proposed)" | no (merge order: Q3) |
| F9 | Low | omission confirmed; client behavior is a question | 266-276, 295 | The lockout rule's "second RDP session from home" is a Mac-side step and is missing from the macOS list | no |

## AC status (contract review: can the AC be met, and can it pass wrongly)
| AC | Status | Why |
|---|---|---|
| AC-03 (v2.0) | can be met · wrong PASS possible | F1 (hotspot clause), F2 (refused ports; the outer firewall layer is never judged) |
| AC-04 (v2.0) | can be met · wrong PASS possible | F3 (the printer clause, possibly the file clause) |
| AC-01, AC-02, AC-05, AC-06, AC-07 | unchanged | the diff touches none of their lines |

## F1 · Medium · AC-03 (2): the hotspot test has no control
- **Where:** lines 252-253.
- **Evidence:**
  - (2) reads: "จากเครือข่ายที่ไม่อยู่ใน allowlist (เช่น Mac ต่อ hotspot ของมือถือ) `nc -vz -G 5 <vps> 3389` ล้ม".
  - It has no rule for the message. (1) has one at line 251: "ผลที่คาดของพอร์ตที่ปิดคือ timeout".
  - It has no check that the Mac is online. (3) has one at line 253: "ตรวจก่อนว่า Mac ออก IPv6 ได้".
  - It uses bare `nc`, where (1) and (3) use `/usr/bin/nc`.
  - ENV-002 v2.6 AC-03 (1) already uses a control for this: "ตัวควบคุม: `nc -vz -G 5 <vps> 3389` สำเร็จ (พิสูจน์ว่า IP ถูกและ Mac ออนไลน์อยู่ …)".
  - On this Mac, `nc` exits 1 for every kind of failure:
    - `/usr/bin/nc -vz -G 2 127.0.0.1 9` prints "nc: connectx to 127.0.0.1 port 9 (tcp) failed: Connection refused", exit 1.
    - `/usr/bin/nc -vz -G 2 127.0.0.1 99999` prints "nc: port range not valid", exit 1.
    - `/usr/bin/nc -vz -Q 2 127.0.0.1 9` prints "nc: invalid option -- Q", exit 1.
- **Impact:** a hotspot with no working data still gives exit 1. So does an `nc` earlier in `PATH` that rejects `-G`. Either way (2) passes, while 3389 may be open to every address. What remains is host_report's Windows scope check (AC-01) and the provider rule list in (4), and (4) has no pass rule (see F2).
- **Proposed change:**
  - In (2), on the hotspot, first run `/usr/bin/curl -s https://api.ipify.org`. Record only "ต่างจาก IP บ้าน: ใช่". This proves the Mac is online and outside the allowlist.
  - Then run `/usr/bin/nc -vz -G 5 <vps> 3389`, and record the message and exit status as in (1).
  - A usage error or option error is not a result.
  - Add the negative case "hotspot ไม่มีเน็ตหรือได้ IP เดียวกับบ้าน".
- **Proof of fix:** (2) has the egress and IP control, the full path to `nc`, and the message rule.

## F2 · Medium · `Connection refused`: wrong reading, no pass rule, and the outer layer is never judged
- **Where:** lines 251-252 (and Negative cases, line 278); lines 255-256 for (4).
- **Evidence:**
  - Lines 251-252: "`Connection refused` ต้องมีคำอธิบาย (แปลว่า packet ถึง VPS แล้วถูกปฏิเสธ: firewall ชั้นนอกไม่ได้กั้นพอร์ตนั้น)".
  - ENV-002 v2.6 AC-03 (2) hands this case to ENV-001: "`Connection refused` ต้องมีคำอธิบายจากฝั่ง ENV-001" (ENV-002 branch, contract line 455). Neither text says which explanation passes.
  - The Goal (line 21) requires "กั้นสองชั้น (firewall ของผู้ให้บริการ และ firewall ของ Windows) … พอร์ตอื่นปิดทั้งหมด".
  - Runbook §1.1 (runbook line 20) sets the provider firewall to "พอร์ตอื่นปิดทั้งหมด".
  - (4) only requires the provider rule list to be "อยู่ในหลักฐาน". It has no pass condition.
- **Impact:**
  - (i) By the contract's own reading, a refused port means the outer layer does not block that port. Yet (1) still passes (exit is not 0) once the result is "explained", and the explanation can simply be that sentence. The two-layer goal fails while AC-03 passes.
  - (ii) The reading is unreliable. Windows Defender Firewall, in its default stealth mode, does not answer a blocked or unlistened port with a TCP reset. So on a VPS that passed AC-01, a reset more likely comes from a provider firewall that rejects instead of dropping, or from a device on the path. In those cases the outer layer did block, and the owner would chase a hole that is not there.
  - (iii) A timeout cannot show which layer dropped the packet. The home ISP may also drop 139 or 445 before they leave home. So the outer layer's only evidence is (4), which nobody judges.
- **Proposed change:**
  - Replace the parenthetical with a rule:
    - `nc` cannot tell the layers apart, and a timeout is the expected result.
    - A refused port passes only when its source is shown. Either the same port times out from the hotspot (so the reset came from the home path), or (4) denies that port and the provider rejects instead of dropping.
    - Otherwise AC-03 is not PASS until the cause is fixed.
  - Give (4) a pass rule: the provider allows only TCP (and UDP) 3389 from the allowlisted addresses and denies everything else, IPv6 included.
  - Say in the text that ENV-002 v2.6 AC-03 (2) relies on this rule.
- **Proof of fix:** the AC has a decision rule for refused ports and a pass rule in (4).

## F3 · Medium · AC-04 can pass because of the Mac, not the VPS
- **Where:** lines 258-262.
- **(a) Printer.**
  - Evidence: the Given clause says "ขอ printer ในแท็บ Devices & Audio". A Mac with no printer queue has nothing to redirect, so "ไม่มี printer ที่ redirect มาจาก Mac" is true whatever the VPS policy is. v1.9's Windows client usually had something to send, because Windows ships virtual printers such as Microsoft Print to PDF.
  - `host_report` has no printer item (Items, lines 119-150). The printer block (`fDisableCpm`, runbook line 60) is therefore proven only by this clause.
  - Impact: a wrong PASS that the contract does not name.
- **(b) File clipboard.**
  - Evidence: "(ข้อความยังคัดลอกได้ …)" proves that clipboard redirection is on. It does not prove that Windows App on macOS can carry files. Lines 245-247 flag only the menu names as unverified.
  - If the client cannot paste files, "วางไฟล์ไม่ได้" holds even on a VPS that ignores `SCClipLevel`. Runbook line 68 warns: "Server 2022 ต้องมี cumulative update 2024-07 (KB5040437) ขึ้นไป จึงจะรู้จัก `SCClipLevel`".
  - The `clipboard` item (lines 90-93) reads only the policy values, not the behaviour.
- **(c) Folder.**
  - Evidence: only the state after the test is recorded ("บันทึกค่าที่เหลือ"). v1.9 asked the owner to confirm the request made during the test (runbook line 148: "ยืนยันว่าข้อ 1 ติ๊ก Drives ไว้จริง").
  - Impact: an empty `\\tsclient` means something only if the request was really made.
- **(d) State after the test.**
  - Evidence: "เอาโฟลเดอร์และ printer ออก" is not the state ENV-002 C3 requires: "แท็บ Folders ไม่ติ๊ก Redirect folders, แท็บ Devices & Audio ไม่ติ๊กอุปกรณ์ใด, clipboard ตั้งตาม … (ค)".
  - Impact: C3 re-checks this later, so (d) alone changes no result.
- **Proposed change:**
  - (a) Add to Given: "Mac มี printer อย่างน้อยหนึ่งตัว (`lpstat -p` พิมพ์อย่างน้อยหนึ่งบรรทัด)". If the Mac has none, the owner picks one of two (Q2):
    - add a temporary printer queue for the test and remove it afterwards, or
    - record "printer ไม่ได้ทดสอบ" and read the five `fDisable*` values on the VPS with one read-only `Get-ItemProperty`. This is a new VPS step.
  - (b) Before the server-to-client test, paste a test file from Finder into the VPS session. `SCClipLevel` limits only the server-to-client direction.
    - If the file pastes, the client carries files, and the server-to-client failure really tests the VPS.
    - If it does not paste, record that the file test proves nothing about the VPS. The clipboard proof then rests on AC-01 and the KB check.
  - (c) Record the Folders and Devices & Audio state during the test. Use `net view \\tsclient` next to File Explorer, so the result is text, as in T1.
  - (d) After the test, set the C3 state and record it.
- **Proof of fix:** AC-04 has a printer precondition (or its alternative), a client file-clipboard control, and the in-test state in the evidence.

## F4 · Medium · Recovery contradicts accepted D-023
- **Where:** line 293.
- **Evidence:**
  - Line 293: "ถ้าเจ้าของไม่รับ v2.0: ฉบับ v1.9 ยังใช้ได้จากเครื่อง Windows เดิม (ก่อนล้างตาม D-023)".
  - D-023 item 2 path 1 (ENV-002 branch `DECISIONS.md:264`, accepted 2026-11-18 17:2x): "เครื่องนี้ต้องไม่ถูกใช้เชื่อมต่อ VPS หรือ console ของผู้ให้บริการเลยตั้งแต่เช่าจนถึงวันล้าง".
  - D-023 item 6 (`DECISIONS.md:270`): the ENV-001 revision "ต้องเสร็จก่อนเช่า VPS".
  - ENV-002 v2.6 AC-03 (7)(g) has the same condition: "เครื่อง Windows เดิมไม่ถูกใช้เชื่อมต่อ VPS หรือ console ของผู้ให้บริการเลย".
  - v2.0's own line 7: "เครื่องที่เจ้าของใช้ทดสอบจากภายนอกและเปิด RDP ตั้งแต่ v2.0 คือ Mac".
- **Impact:** following Recovery puts the old machine on the VPS and the provider console (mstsc, `Test-NetConnection`, the console). That:
  - breaks an accepted decision,
  - triggers the cleanup in ENV-002 AC-03 (7)(g), and
  - rents the VPS without the revision that D-023 item 6 requires first.
- **Proposed change:** "ถ้าเจ้าของไม่รับ v2.0: ยังไม่เช่า VPS (D-023 ข้อ 6) · แก้เป็น v2.x หรือเจ้าของเปลี่ยน D-023 ข้อ 2 · เครื่อง Windows เดิมใช้ฉบับ v1.9 ไม่ได้ (D-023 ข้อ 2 ทาง 1) · runbook ฉบับ Windows อยู่ใน history ของ git".
- **Proof of fix:** Recovery no longer names the Windows machine as a fallback.

## F5 · Low · `nc` output carries the VPS address; (3) borrows a criterion that counts 7 ports
- **Where:** lines 250-251 and 253-254.
- **Evidence:**
  - (1) requires "หลักฐานมีข้อความและ exit status ของทุกพอร์ต". Only (4) says "ปิดบังก่อนวาง".
  - macOS `nc -v` prints the target address in every line: "nc: connectx to 127.0.0.1 port 9 (tcp) failed: …" in the probe above. `man nc` shows the success form: "Connection to host.example.com 22 port [tcp/ssh] succeeded!".
  - v1.9's command printed no address (runbook line 131: `Select-Object RemotePort, TcpTestSucceeded`).
  - The invariant at line 167 forbids any VPS IP "ใน repo, log หรือหลักฐาน".
  - (3) passes "ตามเกณฑ์เดิมของ runbook ข้อ 7.3", and runbook line 137 says "ทั้ง 7 พอร์ตเป็น False". The port set in (1) now has 8 ports.
- **Impact:**
  - Each run produces 8 lines (16 with IPv6) that carry the address. AC-06's grep catches it in committed evidence, but not in text pasted into the chat.
  - The pass condition for (3) lives in runbook text that v2.0 is about to rewrite.
- **Proposed change:**
  - In (1) and (3), write "ปิดบังที่อยู่ในทุกบรรทัดของ nc ก่อนวาง". The runbook can print a masked line plus `nc`'s own exit status for each port, for example by piping stderr through `/usr/bin/sed` and reading zsh's `${pipestatus[1]}`.
  - Write the criterion of (3) inline: "ทุกพอร์ตของ (1) รวม 3389 ล้ม เว้นแต่ IPv6 ของบ้านอยู่ใน allowlist ทั้งสองชั้น (3389 สำเร็จได้) · ถ้า hotspot ออก IPv6 ได้ 3389 จาก hotspot ต้องล้ม".
- **Proof of fix:** the masking rule and the inline IPv6 criterion are in the AC.

## F6 · Low · The §10 bullet drops parts of D-023 item 5
- **Where:** lines 262-264, 266 and 274-275.
- **Evidence:**
  - Lines 274-275 list "folder redirection … เฉพาะ `<repo>/data/transfer/`, ไม่ติ๊ก Read-only, เอาออกหลังเสร็จ, การทดสอบ T1–T4 ก่อนใช้ครั้งแรก".
  - D-023 item 5 (`DECISIONS.md:269`) also requires the following, and the bullet leaves them out:
    - "ก่อนเปิดช่องทาง: envcheck บน Mac เป็น PASS และ `data/transfer/` ว่าง"
    - "ข้อใดไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ"
    - "ถ้าไม่ได้ต้องตัดสินใหม่", which replaces v1.9's VHD fallback (runbook line 171)
    - the record "บันทึกผลใน contract ของ acquisition host"
  - v1.9 §10.5 (runbook line 165) removes the redirect before the reconnect that closes the policy, because "ตอนนี้ VPS ยังยอมรับไดรฟ์อยู่". The bullet says only "เอาออกหลังเสร็จ".
  - Line 266 says "ขั้นบน VPS คงเดิม". Yet T1, T2 and T4 add `net view \\tsclient` on the VPS, and T3 adds a `host_report.py` run while the policy is open.
- **Impact:**
  - A runbook written from the bullet can miss the checks before the channel opens.
  - It can keep the old VHD fallback.
  - It can reconnect while the folder is still redirected and the policy is still open.
  - A runbook reviewer may treat the VPS-side T-steps as out of scope.
- **Proposed change:**
  - Say that §10 copies D-023 item 5 in full, or list the missing items.
  - State that T1–T4 run at the first real use, under the acquisition-host contract. §10 stays "ใช้หลัง ENV-1 ผ่านเท่านั้น".
  - Remove the folder from the PC entry before the reconnect that closes the policy.
  - Replace "ขั้นบน VPS คงเดิม" with "การตั้งค่าบน VPS คงเดิม · ข้อ 10 เพิ่มการตรวจฝั่ง VPS ของ T1–T4".
- **Proof of fix:** the bullet, or one added sentence, covers these items.

## F7 · Low · The header rule and §1.2 are shorter than C9 and D-023 item 6
- **Where:** lines 267-268 and 270-271.
- **Evidence:**
  - (a) C9 in ENV-002 v2.6 (contract line 485) ends with: "เปิด console ใน browser หรือ profile ที่ไม่มี extension ของ Claude หรือ ChatGPT; ถ้ามี ให้รัน pgrep ซ้ำหลังเปิด browser". Line 268 says only "กฎเดียวกันใช้กับการเปิด console ของผู้ให้บริการใน browser".
  - (b) D-023 item 6 names "รายการ Credentials ใน Windows App และ Keychain Access" for the saved-password check. §1.2 checks only "Windows App → Settings → Credentials". C2, the Keychain check, runs only "ก่อน ENV-1 ผ่าน", which is after SPIKE-002.
- **Impact:**
  - (a) The owner opens the provider console again and again during ENV-001 (§0, §1.1, §1.5). An agent's browser extension runs inside the browser's own processes, so `pgrep` by app name may not list it.
  - (b) A Keychain entry created at the first connection stays unchecked for the whole SPIKE-002 period.
- **Proposed change:**
  - Say "ทำ C9 ครบทุกข้อความ", or copy C9 in full.
  - Add C2 to the §1.2 check after the first connection.
- **Proof of fix:** both appear in the bullets.

## F8 · Low · Cross-branch labels, merge order and a stale line 7
- **Where:** lines 7, 256, 268, 271, 283, 285 and 299.
- **Evidence:**
  - The v2.0 text cites "ENV-002 checklist ข้อ C9", "C1–C3", "ความเสี่ยงที่เหลือข้อ 16", "ENV-002 decision (ค)" and "ENV-002 (ซ)". Line 3 places only D-023 on the other branch.
  - On this branch, `docs/contracts/ENV-002-research-host-separation.md` is "Version v1.5":
    - it has no C-items (grep "C9": 0) and no (ซ);
    - its (ค), at its line 159, says "(ปิดหน้าต่าง agent ก่อน)", which is the rule v2.0 replaces with Quit.
  - Neither this branch's `DECISIONS.md` nor `main`'s has D-023.
  - The D-023 heading says "เจ้าของยกเลิกได้จนถึงก่อน merge". Nothing says what happens to v2.0 in that case, or that v2.0 must merge after ENV-002.
  - Line 7, which v2.0 edited, still says "D-021 (proposed)". D-021 was accepted on 2026-10-25, and D-023 item 5 amends its item 3 (a). The Goal (line 22) and the threat row (line 200) also name D-021 alone.
- **Impact:**
  - A reader on this branch, or on `main` after an out-of-order merge, finds the v1.5 text behind these labels.
  - If D-023 is revoked, nothing says v2.0 lapses.
- **Proposed change:**
  - Add one sentence at the top of the v2.0 section: "ENV-002 = v2.6 บน branch `chore/ENV-002-macos-research-host` (อนุมัติ 2026-11-18 17:2x)".
  - In the DoR or Plan, add: "merge หลัง PR ของ ENV-002 · ถ้าเจ้าของยกเลิก D-023 ก่อน merge v2.0 ตกไป".
  - On line 7, write "D-021 (accepted; ข้อ 3 (a) แก้ฝั่งเครื่องเจ้าของโดย D-023 ข้อ 5)".
- **Proof of fix:** the version and branch are named once, the merge dependency is stated, and line 7 is corrected.

## F9 · Low · The lockout rule's second session is a Mac-side step missing from the list
- **Where:** lines 266-276 and 295.
- **Evidence:**
  - Runbook line 10: "**กฎกันล็อกตัวเอง:** … ให้เปิด RDP session ที่สองจากบ้านให้ได้ก่อนเสมอ และอย่าปิด session แรกจนกว่า session ใหม่จะเข้าได้". The runbook uses this step again at lines 29, 44, 50 and 70.
  - The Plan (line 295) rewrites only "ข้อ 0, 1.2, 7, 8, 10 และกติกาท้ายหัว", and "กติกาท้ายหัว" means the agent rule at line 267.
  - Windows App behaviour is unverified (lines 245-247). To my knowledge its predecessor, Microsoft Remote Desktop for Mac, brought the open session to the front instead of opening a second one. I did not verify this.
- **Impact:** if Windows App behaves the same way, the owner cannot follow the safety rule as written. After a firewall mistake, the only way back in is then the provider console.
- **Proposed change:** add the lockout rule to the macOS list, with the Windows App way to open a second session (for example, a duplicated PC entry). Check it on first use, like the menu names.
- **Proof of fix:** the rule appears in the macOS list and in the Plan.

## Checked and correct (and how)
- **The change is owner-side only.**
  - `git show --stat 5a3a24f` shows one file. The edits are lines 3, 4, 7, 179 and 180, plus the appended section at lines 238–300.
  - `bash scripts/controls/red-flags.sh 9157950` found 0 pattern hits, no control files and no deleted tests.
  - Inputs/outputs, Items, Invariants and AC-01, AC-02, AC-05–AC-07 are byte-identical to v1.9.
- **The Mac facts at lines 244–245 are true.**
  - `sw_vers` shows macOS 26.6.2 (25G83), and `uname -m` shows arm64.
  - `man nc` lists `-4`, `-6`, `-G conntimeout` ("TCP connection timeout in seconds"), `-v` and `-z`.
  - `/usr/bin/nc -z -G 2 127.0.0.1 9` exits 1 with no output. With `-v` it prints the message and still exits 1.
  - `/usr/bin/nc -6 -vz -G 2 ::1 9` behaves the same way.
  - `man smbutil` has `view`, `-N` ("don't prompt for a password") and `-g` ("authorize with guest only"). `-G` is a different flag ("allow guest access"), and ENV-002 correctly uses `-g -N`.
- **AC-03 (v2.0) keeps every v1.9 clause.** These are: hotspot 3389 fails; 3389 open from home and the other ports fail; provider rules masked; CGNAT result; re-test over VPN.
  - It adds port 139, IPv6 in the AC itself, and the C9 precondition.
  - Its port list and its home 3389 control match ENV-002 v2.6 AC-03 (1)–(2).
- **AC-04 (v2.0) keeps every v1.9 clause.** Requesting one empty folder outside the repo is safer than v1.9's "all drives": if the VPS wrongly accepts, only an empty folder is exposed.
- **The snapshot channel matches D-021 item 3 (a) as amended by D-023 item 5**, apart from the gaps in F6:
  - only `<repo>/data/transfer/`, with Read-only unticked, removed after use;
  - T1–T4 before real use;
  - `host_report.py` and the ENV-002 checker after each transfer.
- **The replacement is clean.** The v1.9 AC-03 and AC-04 stay, each with "แทนข้อนี้เมื่อ v2.0 อนุมัติ". The AC count is still 7, and Verification row "03, 04" fits both versions.
- **The agent rule matches the ENV-002 checklist.**
  - The header rule's command and app list match C9: `pgrep -ilf 'claude|codex|chatgpt'`, and Quit VS Code, Claude and ChatGPT/Codex.
  - The §1.2 menu path matches C1.
- **Cited states are correct.**
  - D-023: accepted 2026-11-18 17:2x (ENV-002 branch `DECISIONS.md:259`).
  - ENV-002 residual item 16: accepted 2026-11-18 (ENV-002 branch PROGRESS: "รับ (ญ) ข้อ 16").
  - ENV-002 v2.6: approved, recorded 2026-11-18 17:2x.
- **The version, status and labels are consistent.**
  - The Version and Status lines say: v2.0 draft; v1.9 is the last approved version and the code follows it; history is intact.
  - Every changed spot is labelled "(v2.0)".
  - Decision label (ฎ) clashes neither with ENV-001's (ก)–(จ) nor with ENV-002's labels up to (ญ).
- **Plan, Budget, Verification, Authorization and DoR (v2.0) are consistent.**
  - Plan step 3, using the runbook at rental, fits D-023 item 6 ("ต้องเสร็จก่อนเช่า VPS").
  - The reviewer is a fresh Claude session.
  - The budget has no code and no tests.
  - Authorization adds the Mac as a target, and the main table's action still applies (no MetaTrader5, no orders).
  - The DoR lists the missing review and approval.
- **ENV-001 rightly does not use `smbutil`.** D-023 item 6 assigns the SMB test to ENV-002 AC-03 (3).

## Not checked (and why)
- **`nc`'s timeout path:** the `Operation timed out` text, and whether `-G 5` is honoured. Testing it needs a host that drops packets, and I contacted no external host.
- **Windows App behaviour:** menu names, file copy over the clipboard, printer redirection, a second session to the same PC, the Read-only box, and `\\tsclient` share names. The app is not installed, and I did not open the cited Microsoft Learn page (no network).
- **Windows Defender Firewall stealth mode (F2):** that it sends no reset for blocked ports. This is Microsoft's documented behaviour as I know it; I did not measure it, since there is no VPS.
- **VPS-side output** of `net view \\tsclient`, `Get-Printer` and `Get-ItemProperty`. There is no VPS.
- **Whether this Mac has a printer queue (F3).** I did not query it; the finding rests on the contract text.
- **That `api.ipify.org` returns IPv4 only.** Not contacted.
- **`host_report.py`, its tests, and AC-01, AC-02, AC-05–AC-07.** The diff does not change them and I did not re-review them. I did not run pytest, because no code changed.
- **`docs/handoff/ENV-001.md`.** I looked at it only after writing the findings, as the procedure requires. A grep for "v2.0" found nothing, and I did not read further.

## Questions for the owner
1. **(F4)** If v2.0 is not approved, do you want any fallback that uses the old Windows machine? D-023 item 2 path 1 forbids connecting it to the VPS or the provider console. The proposed Recovery text has the rental wait for a v2.x instead.
2. **(F3)** For the printer check, which do you prefer?
   - a temporary printer queue on the Mac for the test, removed afterwards;
   - one read-only `Get-ItemProperty` of the redirection policy on the VPS (a new VPS step, outside "VPS steps unchanged"); or
   - recording "printer ไม่ได้ทดสอบ".
3. **(F8)** Will the ENV-002 PR, which carries D-023 and ENV-002 v2.6, merge before the ENV-001 PR? If not, ENV-001 v2.0 in `main` would cite labels that `main` does not have.

Ready for the owner's approval (ENV-001 v2.0): no (4 Medium open: F1, F2, F3, F4; all are text changes)
Findings open: 9 (0 High · 4 Medium: F1, F2, F3, F4 · 5 Low: F5, F6, F7, F8, F9)
