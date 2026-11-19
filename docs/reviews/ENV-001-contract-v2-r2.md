# Review ENV-001 contract v2.1 · round 2 (closure check) · base: review r1 at `aad9d75` on v2.0 · head `b0a91fc` · reviewer: one fresh Claude session, read-only · 2026-11-18

File: `docs/reviews/ENV-001-contract-v2-r2.md`.

**Scope:**
- The fixes `aad9d75..b0a91fc` to `docs/contracts/ENV-001-vps-acquisition-host.md`: one file, +60/−21. The fix commits are `4ab5286`, `9c1c633` and `a5b462b`; `b0a91fc` labels the draft.
- Each fix is checked against r1's F1–F9.
- The v2.x AC-03 and AC-04 are checked as they now read.
- Line numbers refer to that file at `b0a91fc` unless another file is named.

**Label.** This is contract review round 2 of ENV-001 v2.x (High tier).
- **Who:** one fresh Claude session, a Claude subagent. It did not write the draft, the fixes or round 1, and did not see their conversations. The caller gave no summary of the implementer's intent.
- **Inputs:**
  - the contract at `b0a91fc`
  - the diffs `aad9d75..b0a91fc` and `9157950..b0a91fc`
  - review r1
  - the v1.9 runbook `docs/runbooks/ENV-001-vps.md`, which is unchanged
  - from branch `chore/ENV-002-macos-research-host`, read with `git show` without touching that working tree: D-021, D-023, ENV-002 contract v2.6 and PROGRESS.md
- **Binding, as recorded:**
  - PROGRESS on this branch (line 5) says the owner kept the role swap for ENV-001: "คงการสลับบทบาท แม้โควตา Codex กลับมาแล้ว".
  - The ENV-002 contract records (ซ), which the owner confirmed on 2026-11-18 at 11:2x.
  - Contract line 318 names a fresh Claude session as the v2.x reviewer, "แบบเดียวกับ ENV-002 (ซ)".
- No PROGRESS line names ENV-001 v2.x itself. If the owner does not read those records as covering this revision, this file is a pre-review (Claude subagent) and does not replace the binding review.

## Verdict
**Not ready for the owner's approval.** One Medium finding is open, and a one-clause text fix closes it.

- **r1 findings:** all nine are closed, judged against r1's own proposed changes and proofs of fix (table below). The v2.1 paragraph matches the text it describes.
- **F10 (Medium, new): the provider layer is judged on paper only.**
  - v2.1 now says `nc` cannot tell the two firewall layers apart (257), so the provider layer rests on (4) alone.
  - (4)'s new pass rule judges the provider's rule list. It does not ask whether that list is in force for this VPS.
  - A correct rule set that is not attached to the VPS, or is switched off, gives the same `nc` results as two layers. AC-03 then passes while the two-layer goal (21) fails.
  - The gap was already in v1.9's AC-03, which had no pass rule at all. v2.1 makes (4) the deciding evidence.
- **F11–F13 (Low):** incomplete text that changes no result under the runbook as written. These may stay open.
- **No other Medium or High:**
  - No v2.1 step contradicts D-023, D-021 item 3 (a) as amended, or ENV-002 v2.6.
  - Every new Mac command that can be run locally behaves as written.
  - AC-01, AC-02 and AC-05–AC-07 are byte-identical to v1.9.
- **Budget:** a round 3 after the fix fits the v2.x budget (324: four fresh sessions; this round is the second).

## r1 re-check
| ID | r1 sev | Status at `b0a91fc` | Commit | Evidence |
|---|---|---|---|---|
| F1 | Medium | closed | `4ab5286` | 260–261: "ก่อนอื่น `/usr/bin/curl -s https://api.ipify.org` ต้องได้ IP (พิสูจน์ว่าออกเน็ตได้)", then `/usr/bin/nc` with the message rule of (1) (262). Usage errors "ไม่ใช่ผล" (256). Negative case at 312. All four parts of r1's change are present |
| F2 | Medium | closed (F10 is a separate gap in the same clause) | `4ab5286` | 258–259: "`Connection refused` ผ่านได้เฉพาะเมื่อแสดงที่มาได้ … นอกจากนั้น AC-03 ยังไม่ PASS จนกว่าแก้ที่มา". 268: "เกณฑ์ผ่านของรายการ rule: ผู้ให้บริการอนุญาตเฉพาะ TCP 3389 …". 259 names ENV-002 v2.6 AC-03 (2) |
| F3 | Medium | closed (remainder: F11) | `9c1c633` | 277–280: policy read on the VPS and a `lpstat -p` precondition with a no-printer record. 281–283: Mac → VPS file control. 272–273: tab state "**ระหว่างทดสอบ**". 284: `net view \\tsclient`. 285: C3 state afterwards |
| F4 | Medium | closed | `a5b462b` | 326–327: "ยังไม่เช่า VPS (D-023 ข้อ 6) … เครื่อง Windows เดิมใช้ฉบับ v1.9 ไม่ได้". No text names the Windows machine as a fallback |
| F5 | Low | closed | `4ab5286` | 255: "ปิดบังที่อยู่ในทุกบรรทัดก่อนวาง". (3) reuses "ชุดของ (1)". 264: the criterion is now inline, "เกณฑ์เขียนในข้อนี้เอง", as r1 proposed |
| F6 | Low | closed | `a5b462b` | 303: "คัด D-023 ข้อ 5 มาครบทุกข้อความ". The same item has the condition before opening, T1–T4 under the acquisition-host contract, "ไม่มีทางสำรองแบบ VHD" and the closing order. 242 and 290 replace "ขั้นบน VPS คงเดิม". Line 3's v2.0 history entry still says "ทุกขั้นบน VPS ไม่เปลี่ยน", but that is history |
| F7 | Low | closed (remainder: F12) | `a5b462b` | 291: "ทำ ENV-002 checklist C9 ครบทุกข้อความ", with the browser and profile clause (292–293). 299–300: C2 "ทันที ไม่รอถึงก่อน ENV-1 ผ่าน" |
| F8 | Low | closed | `a5b462b` | 244–245: "ENV-002 **v2.6** บน branch … ไม่ใช่ v1.5". 245–246: merge order and what happens if D-023 is revoked. 7: "D-021 (accepted 2026-10-25; …)" |
| F9 | Low | closed (remainder: F12) | `a5b462b` | 294–296: second session from a duplicated PC entry, checked at first use, else the provider console. The Plan's "กติกาท้ายหัว" (329) covers it, because the runbook keeps this rule among its header rules (runbook line 10) |

**The v2.1 paragraph (336–339).**
- **Consistent with the text:**
  - Q1 is carried out by Recovery (326–327).
  - Q2 is carried out by AC-04 (a): the policy read always, and the printer test when `lpstat -p` shows a queue (276–280).
  - Q3 is carried out by the merge order (245–246).
- **The claim "ไม่มีข้อใดเป็นการรับความเสี่ยงเพิ่ม" holds:**
  - Q1 follows accepted D-023.
  - Q3 is only an ordering.
  - Q2 adds the policy read in every case.
- **Honesty:** the paragraph records the answers as the author's choices under the 11:2x permission. It says they are reversible and leaves (ฎ) to the owner.
- **One precision point:** the 11:2x reply answered ENV-002's r3 questions about six hours before this revision existed (v2.0 `5a3a24f` was committed at 17:28 +0700). Applying that reply here is the author's reading, and the paragraph does not label it as one. ENV-002 v2.4 did label its reading: "ตีความจากคำตอบรวม". Approving (ฎ) confirms these choices; see Question 2.

## Findings open after this round
| ID | Sev | Kind | File:line | Finding |
|---|---|---|---|---|
| F10 | Medium | confirmed from the contract text; provider console designs from general knowledge | 267–269, 257 (Goal 21) | (4) judges the provider's rule list, not whether it is in force for this VPS. An unattached or disabled rule set gives the same `nc` results as two layers |
| F11 | Low | confirmed; client behaviour unverified | 277–278, 281–283 | AC-04's clipboard proof has loose ends: the command omits `fDisableClip`, the fallback drops the Server 2022 patch condition, and the control can leave a Mac file on the clipboard |
| F12 | Low | confirmed from the text order; client prompt unverified | 294–295, 298–300 | The early C2 check runs after the provider account's first connection. The owner's own account and the duplicate entry first connect later, at runbook §1.3 |
| F13 | Low | confirmed | 254–262 | The `nc` message rule covers timeout, refused and usage errors only. Other failures, or a network that breaks after the control, count as closed |

### F10 · Medium · The provider layer is judged on paper, not in force
- **Where:** 267–269, with 257 and Goal line 21.
- **Evidence:**
  - Goal (21) requires two layers, "กั้นสองชั้น (firewall ของผู้ให้บริการ และ firewall ของ Windows)", and says they are "พิสูจน์จากภายนอก".
  - Line 257: "`nc` แยกไม่ได้ว่าชั้นไหนทิ้ง packet".
  - The evidence in (4) is "รายการ rule ของ firewall ผู้ให้บริการ (ปิดบัง IP)". The pass rule (268–269) is "ผู้ให้บริการอนุญาตเฉพาะ TCP 3389 … และปฏิเสธที่เหลือทั้งหมด รวม IPv6".
  - Nothing asks that the rule set be attached to this VPS or switched on:
    - not AC-03;
    - not runbook §1.1 (runbook line 20) or §7.4 (line 139);
    - and the Plan (329) does not rewrite §1.1.
  - r1 F2 (iii) (r1 line 86) already said the outer layer's only evidence is (4). r1's fix judged the list but not whether it is live.
- **Trigger:** the provider's firewall is a rule set that must be attached to a server, or a per-IP firewall with an on/off switch. Both are common designs; I did not check this (no network). The owner writes the right rules but does not attach or enable them.
- **Impact:**
  - After AC-01, Windows drops every port except 3389, and accepts 3389 only from the allowlist. So:
    - from home, the other ports time out;
    - from the hotspot, 3389 times out;
    - the pasted list meets the pass rule.
  - Windows passes no TCP port that the provider should block, so no `nc` test can separate the layers. AC-03 passes with one layer.
  - RDP stays restricted by the Windows layer (AC-01). What is lost is defence in depth, not an open port.
  - It is still a wrong PASS of the stated two-layer goal. It is not named in the threat row (199) or in "ที่เหลือ (v2.0)" (315–316).
- **Minimal fix (either one):**
  - In (4), require evidence that the rule set is in force for this VPS: the provider page that lists the servers it is attached to, or the VPS's firewall page showing it on, with IP and account masked. Add "ผูกกับ VPS นี้และเปิดใช้อยู่" to the pass rule, and add the item to runbook §7.4.
  - Or, if the owner accepts the gap, name "ชั้นนอกพิสูจน์จากหน้าของผู้ให้บริการเท่านั้น" as a residual in the threat row.
- **Proof of fix:** (4)'s evidence and pass rule include the attached and enabled state, or the residual is named and the owner accepts it.

### F11 · Low · AC-04's clipboard proof has three loose ends
- **Where:** 277–278 and 281–283.
- **Evidence:**
  - **(a) Missing value.** The criterion is "`SCClipLevel` เป็น 1 (หรือ `fDisableClip` เป็น 1 ถ้า (ค) เลือกปิด clipboard ทั้งหมด)". The command ends `Select-Object fDisableCdm, fDisableCpm, fDisableCcm, fDisableLPT, fDisablePNPRedir, SCClipLevel` and never prints `fDisableClip`.
  - **(b) Dropped patch condition.**
    - The fallback reads "การป้องกันทิศนี้อยู่ที่ค่า `SCClipLevel` ของ (a) และ AC-01". Both (a) and AC-01 read the same registry value.
    - Runbook line 68 says Server 2022 needs the 2024-07 cumulative update (KB5040437) before it recognises `SCClipLevel`.
    - The `os` item accepts any build 20348 (120).
    - r1's proposal (r1 line 118) ended "rests on AC-01 and the KB check"; v2.1 dropped the KB check.
    - The control also assumes that if Windows App carries files from Mac to VPS, it carries them from VPS to Mac. That is unverified.
  - **(c) Leftover Mac file.** The control puts a Mac file on the Mac clipboard. If the client keeps it when the VPS offers no file format, pasting in Finder pastes the Mac's own file. That looks like a VPS → Mac transfer: a false FAIL, not a wrong PASS. This client behaviour is unverified.
- **Impact:** none on the approved path:
  - (ค) is text-only.
  - Server 2025 is recommended.
  - Runbook §1.4 (line 30) installs every update.

  Off that path, the value can be set but not shown, or set but not honoured.
- **Minimal fix:**
  - Add `fDisableClip` to the `Select-Object` list.
  - In (b)'s fallback, add "and on Server 2022 the build carries the 2024-07 cumulative update or later (`UBR` in `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion`)".
  - Use different test file names on the Mac and on the VPS.
- **Proof of fix:** the command prints every value its criterion names, the fallback names the patch condition, and the two test files have different names.

### F12 · Low · The early credential check comes before the credentials that matter
- **Where:** 298–300 and 294–295.
- **Evidence:**
  - Line 298 places the check in §1.2, "หลังเชื่อมครั้งแรก", and 299–300 adds C2 "ทันที".
  - In runbook §1.3 (lines 22–29), the owner creates their own admin account and opens "session ที่สองด้วยบัญชีใหม่". Only then is the provider's account disabled.
  - So the long-lived password is first typed at §1.3, after the §1.2 check. The account that the §1.2 check covers is disabled later in the same §1.3.
  - Under v2.1 (294–295), that second session uses a duplicated PC entry, so the duplicate's first use is also at §1.3.
  - Several texts name "the" PC entry or card and say nothing about a second one:
    - §1.2's "Ask when required" (298);
    - AC-04 (d) "ตั้งรายการ PC" (285);
    - ENV-002 C1 "รายการ PC ไม่ผูก credential";
    - ENV-002 C3 "การ์ดของ VPS (Edit)";
    - D-023 T4 "รายการ PC ใน Windows App ไม่มีโฟลเดอร์ใน Folders".
- **Trigger:** a password is saved at the §1.3 prompt (whether Windows App offers to save it is unverified), or the duplicate entry keeps a credential or redirect setting that the original no longer has.
- **Impact:**
  - A saved password for the owner's own account stays unchecked through SPIKE-002. That is the window r1 F7 (b) meant to close (r1 line 184).
  - C1 and C2 before ENV-1 still catch a saved password.
  - A second entry's redirect setting is blocked by the VPS policy (AC-01, AC-04 (a)). During §10, T2's single-share check catches it.
  - No gate result changes.
- **Minimal fix:**
  - Run the C1/C2 check after the first connection with the owner's own account (end of §1.3), instead of or as well as after §1.2.
  - Say that §1.2's setting, AC-04 (d), C1 and C3 cover every PC entry of the VPS, or delete the duplicate after the step that needs it.
- **Proof of fix:** the check sits after §1.3, and the text covers every entry or removes the duplicate.

### F13 · Low · The `nc` message rule is not exhaustive
- **Where:** 254–262.
- **Evidence:**
  - Ports pass on "ล้มทั้งหมด (exit ไม่ใช่ 0)" (254–255).
  - The rule names three cases:
    - timeout, which is expected;
    - `Connection refused`, which needs a shown source;
    - usage or option errors, which are not a result (256–259).
  - It does not cover other failures such as `No route to host` or `Network is unreachable` (standard errno text; not reproduced here).
  - (1) has no control after the port list, and (2) runs curl only before `nc` (260–261).
- **Trigger:** the Mac's network drops, or the upstream breaks, between the control and the last test.
- **Impact:**
  - Those ports print an odd message, or a timeout, and count as closed.
  - AC-01 proves the Windows layer on its own, so no open port hides behind this. The evidence would also show the odd messages.
  - It is still a gap in the rule v2.1 added.
- **Minimal fix:**
  - Add "ข้อความอื่นนอกจาก timeout และ Connection refused ไม่ใช่ผล: ทำซ้ำ".
  - Repeat each control after its test: 3389 from home after the last port, and curl on the hotspot after `nc`.
- **Proof of fix:** both sentences are in AC-03.

## AC status (contract review: can the AC be met, and can it pass wrongly)
| AC | Status | Why |
|---|---|---|
| AC-03 (v2.x) | can be met · wrong PASS possible | F10 (provider rules not in force); F13 is minor |
| AC-04 (v2.x) | can be met · wrong PASS only off the approved path | F11 (b): Server 2022 without the 2024-07 update, with a client that cannot send files |
| AC-01, AC-02, AC-05, AC-06, AC-07 | unchanged | `git diff -U0 9157950..b0a91fc` has hunks only at 3–4, 7, 179–180 and the appended section 237–339 |

## Checked and correct (and how)
- **The change set.**
  - `git diff --stat aad9d75..b0a91fc` shows one file, +60/−21.
  - Per-commit hunks: `4ab5286` touches 251–264; `9c1c633` touches 268–283 and the negative cases; `a5b462b` touches 7, 242–246, 290–308 and 326–327; `b0a91fc` touches 3–4 and 335–339.
  - Every r1 ID has a "(v2.1, r1 F<n>)" tag.
  - `bash scripts/controls/red-flags.sh aad9d75` and `… 9157950` report 0 pattern hits, no control files and no deleted tests.
- **`nc` on this Mac.**
  - `man nc` lists `-G conntimeout` ("TCP connection timeout in seconds"), `-v`, `-z` and `-6`.
  - `/usr/bin/nc -vz -G 2 127.0.0.1 9` prints "nc: connectx to 127.0.0.1 port 9 (tcp) failed: Connection refused" and exits 1.
  - `/usr/bin/nc -vz -G 3 127.0.0.2 9` prints "nc: connectx to 127.0.0.2 port 9 (tcp) failed: Operation timed out", exits 1 and takes 3 s.
    - This probe stays on the Mac: `route -n get` sends 127.0.0.0/8 to `lo0`, and `lo0` holds only 127.0.0.1.
    - So the timeout text at 257 is right, `-G` is honoured, and every message carries the address, as F5 assumed.
  - The examples at 256 are real messages here: port 99999 gives "nc: port range not valid", and `-Q` gives "nc: invalid option -- Q". Both exit 1.
- **Masking (255–256) can be done on this Mac.** In `/bin/zsh -f`, `/usr/bin/nc -vz -G 2 $v 9 2>&1 | /usr/bin/sed …; print ${pipestatus[1]}` printed the masked line and `exit=1`, for IPv4 and for `-6 ::1`.
- **Other commands.**
  - `/usr/bin/curl`, `/usr/bin/lpstat`, `/usr/bin/pgrep` and `/usr/bin/sed` exist.
  - `man lpstat`: `-p` lists the printers.
  - `man pgrep`: `-i`, `-l` and `-f` behave as C9 uses them.
- **F2's rule holds, given AC-01 and Windows' default stealth mode (not measured).**
  - Suppose a port is reset from home but times out from the hotspot.
  - If the reset came from the VPS, the provider layer would have to pass that port from home, and (4) would show that (subject to F10). Otherwise it came from the home path.
- **(2)'s control** proves the Mac is online and on a non-allowlisted address.
  - It cannot rule out a carrier that filters outbound 3389.
  - That alone cannot make AC-03 pass wrongly: AC-01 proves the Windows scope, and (4) covers the provider layer (subject to F10).
- **ENV-002 v2.6.**
  - 291–293 match C9: the Quit list, the `pgrep` check, the browser or profile clause, and the re-run after opening the browser.
  - 299 cites C2, which the owner does alone, as D-023 item 6 requires.
  - 285 is the card part of C3. AC-04 does not touch C3's General setting.
  - 257–259 is the rule ENV-002 AC-03 (2) hands over to ENV-001 ("ต้องมีคำอธิบายจากฝั่ง ENV-001").
  - Residual 16 and (ค) are cited correctly (315–316).
- **D-023 and D-021 item 3 (a) as amended.** §10 (303–307) carries all of D-023 item 5:
  - the condition before opening;
  - Read-only unticked;
  - T1–T4 recorded under the acquisition-host contract;
  - "ข้อใดไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ";
  - the manifest, `host_report.py` and envcheck checks.

  Removing the folder before the reconnect that closes the policy is v1.9 §10.5's order, and it stops the folder being redirected again while the policy is open. The runbook must place T1–T3 before the first copy to meet D-023's "ก่อนใช้จริง". Recovery (326–327) follows item 2 path 1 and item 6.
- **F8 facts.**
  - On this branch, `git show b0a91fc:docs/contracts/ENV-002-research-host-separation.md` shows "Version v1.5", and `DECISIONS.md` has 0 matches for D-023.
  - On the ENV-002 branch, D-021 reads "2026-10-25 — accepted" and D-023 reads "accepted 2026-11-18 17:2x by the owner's blanket permission of 2026-11-18 11:2x".
  - ENV-002 v2.6 is "approved by … 11:2x …, recorded 2026-11-18 17:2x".
- **Labels and status.**
  - Lines 3–4 say v2.1 is a draft, v1.9 is the last approved version, and the code follows v1.9.
  - The paragraph counts r1 as "1 จาก 4" of the v2.x budget (324).

## Not checked (and why)
- **Windows App behaviour:** menu names, file paste in either direction, printer redirection, a second session from a duplicated entry, and whether the credential prompt offers to save. The app is not installed.
- **Provider firewall designs (F10):** that common providers keep rule sets that must be attached or enabled. This is general knowledge; I used no network.
- **`nc` against a real remote host:**
  - I contacted no external host, so I did not see how a provider that rejects or drops behaves.
  - I did not check whether the home ISP or the carrier resets port 139 or 445. If both reset the same port and the provider drops it, F2's rule has no passing branch, and AC-03 waits for the owner. That fails safe.
- **Which Server 2022 build carries KB5040437 (F11):** not looked up.
- **`lpstat -p` output on this Mac, and the answer from `api.ipify.org`:** not run. The first is not needed to judge the text; the second needs the network.
- **VPS-side output** of `Get-ItemProperty`, `Get-Printer` and `net view \\tsclient`: there is no VPS.
- **pytest:** no code or tests changed, and `uv run` in the worktree would create `.venv`.
- **`docs/handoff/ENV-001.md`:** read only after writing the findings above. It has no v2.x text; its last change is `ae7458a`.

## Questions for the owner
1. **(F10)** Do you want (4) to require proof that the provider's rules are attached to this VPS and switched on? I recommend this; it is one clause. The alternative is to accept "the provider layer is proven only by the provider's own page" as a named residual.
2. **(v2.1 paragraph)** The author chose the three r1 answers under your 11:2x reply, which answered ENV-002's questions before this revision existed. Approving (ฎ) confirms all three:
   - no fallback on the old Windows machine;
   - the policy read always, plus the printer test only when the Mac already has a printer (no temporary printer queue);
   - ENV-001's PR merges after ENV-002's.

   Do you confirm them?

Ready for the owner's approval (ENV-001 v2.1): no (1 Medium open: F10, a one-clause text fix or a named residual; all nine r1 findings closed)
Findings open: 4 (0 High · 1 Medium: F10 · 3 Low: F11, F12, F13)
