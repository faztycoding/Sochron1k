# Review ENV-001 contract v2.2 · round 3 (closure check) · base: review r2 at `6ffd955` on v2.1 · head `ae72752` · reviewer: one fresh Claude session, read-only · 2026-11-18

File: `docs/reviews/ENV-001-contract-v2-r3.md`.

**Scope:**
- This round covers the fixes `6ffd955..ae72752` to `docs/contracts/ENV-001-vps-acquisition-host.md`. That is one file, +22/−9.
  - Fix commits: `75ba240` (F10), `1206bfb` (F11), `f2ac85e` (F12) and `d16f4c5` (F13).
  - `ae72752` labels the v2.2 draft and answers r2's precision point.
- Each fix is judged against r2's own minimal fix and proof of fix.
- The v2.2 edits are checked for new defects:
  - a wrong PASS of AC-03 or AC-04;
  - an AC that cannot be met;
  - a contradiction with D-023, with D-021 item 3 (a) as amended, or with ENV-002 v2.6;
  - a Mac command that does not behave as written.
- Line numbers refer to the contract at `ae72752` unless another file is named.

**Label.** This is contract review round 3 of ENV-001 v2.x (High tier). It is a closure check.
- **Who:** one fresh Claude session, run as a read-only Claude subagent.
  - It did not write the draft, the fixes, or rounds 1–2, and it did not see their conversations.
  - The caller gave file locations and the open IDs. It gave none of the implementer's reasoning.
- **Inputs:**
  - the contract at `ae72752`;
  - the diffs `6ffd955..ae72752` and `9157950..ae72752`;
  - reviews r1 and r2;
  - the v1.9 runbook `docs/runbooks/ENV-001-vps.md`, which is unchanged;
  - from branch `chore/ENV-002-macos-research-host`, read with `git show` without touching that working tree: D-021, D-023, ENV-002 contract v2.6 and PROGRESS.md.
- **Binding, as recorded:**
  - PROGRESS on this branch (line 5) says the owner kept the role swap for ENV-001: "คงการสลับบทบาท แม้โควตา Codex กลับมาแล้ว".
  - PROGRESS on the ENV-002 branch (line 17) records (ซ). The owner confirmed it on 2026-11-18 at 11:2x.
  - Contract lines 326–327 name a fresh Claude session as the v2.x reviewer, "แบบเดียวกับ ENV-002 (ซ)". Approving (ฎ) approves those lines too.
- No PROGRESS line names ENV-001 v2.x itself. If the owner does not read those records as covering this revision, this file is a pre-review (Claude subagent) and does not replace the binding review.

## Verdict
**Ready for the owner's approval. No Medium or higher finding is open.**

- **r2 findings:** F10 (Medium) and F11–F13 (Low) are all closed. Each was judged against r2's own minimal fix and proof of fix (table below).
- **Precision point:** it is now recorded.
  - Lines 347–348 call the use of the 11:2x reply "การตีความของ Claude จากคำตอบรวม".
  - Lines 351–352 say the owner will be asked by name at (ฎ).
- **No new High or Medium finding:**
  - No v2.2 sentence contradicts D-023, D-021 item 3 (a) as amended, or ENV-002 v2.6.
  - The edits add no new Mac command. The checks they add after each test re-run the `nc` and `curl` calls that r2 already checked.
  - The new `nc` rules fail safe. An unexplained message voids the result, and so does a check that fails afterwards. Neither ever counts as a closed port.
  - AC-01, AC-02 and AC-05–AC-07 are byte-identical to v1.9.
- **Three new Low findings, one in each area that F10, F11 and F13 touched:**
  - **F14:** the evidence that the provider rules are in force covers one rule set. It does not cover every set in force on the VPS.
  - **F15:** a v2.1 negative case now contradicts the wider policy read.
  - **F16:** the IPv6 test checks the network only before its ports, not after.
  - Each needs a one-clause fix. They can go into the runbook and be checked by the runbook review, as ENV-002 did with its Low findings F66 and F67 (ENV-002 branch PROGRESS line 5).
  - F14 is the closest to Medium. Its impact is the same as F10's, but its trigger is narrower. Its section explains why it is Low.
- **Budget:** this round is session 3 of 4 (line 332: two contract reviewers, one runbook reviewer, one spare). Session 4 is the runbook review. Another contract round would need the owner to widen the budget.

## r2 re-check
| ID | r2 sev | Status at `ae72752` | Commit | Evidence |
|---|---|---|---|---|
| F10 | Medium | closed (remainder: F14) | `75ba240` | 271–272: "rule ชุดนั้น**ผูกกับ VPS เครื่องนี้และเปิดใช้อยู่**: หลักฐานมีหน้าของผู้ให้บริการที่แสดงรายชื่อ server ที่ rule ชุดนั้นผูกอยู่ หรือหน้า firewall ของ VPS ที่แสดงว่าเปิดใช้". Line 309 adds the page to runbook §7.4. All three parts of r2's change are present: the evidence, the pass rule and §7.4 |
| F11 | Low | closed (remainder: F15) | `1206bfb` | 281: "SCClipLevel, fDisableClip`". 287: "บน Server 2022 build ต้องมี cumulative update 2024-07 (KB5040437) ขึ้นไป (ค่า `UBR` …)". 288: "ไฟล์ทดสอบบน Mac และบน VPS ใช้ชื่อต่างกัน" |
| F12 | Low | closed | `f2ac85e` | 306: "ทำการตรวจ C1 และ C2 นี้**อีกครั้งท้ายข้อ 1.3**". 307–308: "ใช้กับ**ทุก**รายการ PC ของ VPS รวมรายการที่ Duplicate … ลบรายการที่ Duplicate … หรือตั้งค่าให้เหมือนรายการหลัก" |
| F13 | Low | closed (remainder: F16) | `d16f4c5` | 256–257: "ข้อความอื่นนอกจาก timeout และ `Connection refused` … ไม่ใช่ผล: ทำซ้ำ". 257–258: "3389 จากบ้านสำเร็จอีกครั้งหลังพอร์ตสุดท้ายของ (1) และ `curl` บน hotspot ได้ IP อีกครั้งหลัง `nc` ของ (2)" |

**Precision point (r2 line 64 and Question 2): recorded in `ae72752`.**
- Lines 347–348 read: "คำตอบ 11:2x ตอบคำถามของ ENV-002 ก่อน revision นี้มีอยู่ (v2.0 commit 17:28): การใช้คำตอบนั้นกับสามข้อนี้เป็น**การตีความของ Claude จากคำตอบรวม**".
- The time is right: `git log -1 5a3a24f` shows 2026-11-18 17:28:10 +0700.
- Lines 351–352 plan to ask the owner for (ฎ) by name, together with the three v2.1 answers.
- Line 279 still records Q2 inline as "คำตัดสินภายใต้คำอนุญาต 11:2x ของเจ้าของ", without the "Claude's reading" label. The record is still honest, because:
  - line 279 claims no decision by the owner;
  - lines 347–348 cover "สามข้อนี้", and Q2 is one of them;
  - the approval question names Q2.

## Findings open after this round
| ID | Sev | Kind | File:line | Finding |
|---|---|---|---|---|
| F14 | Low | confirmed from the contract text; provider designs from general knowledge, not checked | 269–272, 309 | The in-force evidence shows that one rule set is attached. It does not show that no other set is in force on the VPS |
| F15 | Low | confirmed | 321 against 280–282 | The v2.1 negative case "ค่า `fDisable*` ตัวใดไม่เป็น 1 … (FAIL)" now covers `fDisableClip`. Under text-only (ค), (a) prints that value empty |
| F16 | Low | confirmed | 265–268, 256–258 | The IPv6 test (3) checks the network only before its ports. The F13 rule for a repeat check covers (1) and (2) only |

### F14 · Low · The in-force evidence covers one rule set, not all of them
- **Where:** lines 269–272 and 309.
- **Evidence:**
  - Line 272: "`nc` แยกชั้นไม่ได้ ชั้นนอกจึงพิสูจน์ด้วยหลักฐานข้อนี้". So (4) is the only proof of the outer layer.
  - Lines 271–272 accept either "หน้าของผู้ให้บริการที่แสดงรายชื่อ server ที่ rule ชุดนั้นผูกอยู่" or "หน้า firewall ของ VPS ที่แสดงว่าเปิดใช้". Both speak of one set, "rule ชุดนั้น".
  - The first page belongs to the rule set itself. It shows that this set is attached. It does not show which other sets are attached to the same VPS.
  - Line 309 asks runbook §7.4 for the same single set.
- **Trigger:**
  - The provider applies several firewalls or security groups to one server and allows the union of their rules. AWS security groups work this way. I did not check the budget Windows providers, because I used no network.
  - A set that allows more is still attached. It may be a provider default or a leftover from setup.
  - The owner pastes the set they wrote, plus its page listing the attached servers.
- **Impact:**
  - The pass rule describes the whole provider layer, "ผู้ให้บริการอนุญาตเฉพาะ TCP 3389 … และปฏิเสธที่เหลือทั้งหมด" (270–271). With a wider set attached, that sentence is false, but the evidence does not show it.
  - As with F10, Windows still restricts access (AC-01), so no `nc` test can see the gap.
  - What is lost is the outer layer on the ports the other set opens. That is often 3389 itself.
- **Why Low and not Medium:**
  - This trigger needs two things at once: a provider that combines sets, and a wider set left attached. Runbook §1.1 (runbook line 20) creates only one set.
  - F10's trigger was a set that is not attached or not switched on. That applied to most providers whose firewall must be attached or switched on.
  - If the owner picks a provider that combines sets, the fix should be in the runbook before AC-03 runs.
- **Minimal fix:**
  - In (4) and runbook §7.4, take the in-force evidence from the VPS's side. That is either the VPS page that lists every firewall, rule set or security group applied to it, or the on state of a per-IP firewall.
  - Judge the pass rule on all of them together. Suggested Thai wording: "หน้าของ VPS ที่แสดง rule ทุกชุดที่ใช้กับ VPS นี้ และเกณฑ์ผ่านใช้กับทุกชุดรวมกัน".
- **Proof of fix:** (4) or runbook §7.4 asks for every rule set applied to the VPS.

### F15 · Low · A v2.1 negative case now fails the wider policy read
- **Where:** line 321, against lines 280–282.
- **Evidence:**
  - Commit `1206bfb` added `fDisableClip` to the command at lines 280–281. The command now prints six `fDisable*` values.
  - The criterion still counts five: "ห้าค่า `fDisable*` เป็น 1 และ `SCClipLevel` เป็น 1 (หรือ `fDisableClip` เป็น 1 ถ้า (ค) เลือกปิด clipboard ทั้งหมด)" (281–282).
  - The negative case from `9c1c633` was not changed: "ค่า `fDisable*` ตัวใดไม่เป็น 1 ใน AC-04 (a) (FAIL)" (321). It was written when the command printed exactly the five redirection values.
  - Under text-only (ค), runbook §3 sets `SCClipLevel` (runbook line 64). It names `fDisableClip` only as the alternative (line 68).
  - So `Select-Object` prints `fDisableClip` as empty, and line 321 reads that as a FAIL.
- **Trigger:** the runbook or the evidence review applies line 321 as written.
- **Impact:**
  - The result is a false FAIL, never a wrong PASS. The criterion at lines 281–282 governs.
  - An owner might clear the FAIL by setting `fDisableClip` to 1. That turns the text clipboard off, so the text results of D-021 item 4 must be typed by hand. This is safe, but it is not what (ค) chose.
- **Minimal fix:** at line 321, count only the five redirection values: "ค่าใดในห้าค่า `fDisable*` ของ (a) ไม่เป็น 1 (FAIL) · `fDisableClip` นับเฉพาะเมื่อ (ค) เลือกปิด clipboard ทั้งหมด".
- **Proof of fix:** line 321 names the five values, or it excludes `fDisableClip` under text-only.

### F16 · Low · The IPv6 test (3) checks the network only before its ports
- **Where:** lines 265–268, with lines 256–258.
- **Evidence:**
  - The F13 rule repeats the checks of (1) and (2) only (257–258).
  - (3) first checks that the Mac can reach IPv6: "ตรวจก่อนว่า Mac ออก IPv6 ได้ด้วย `/usr/bin/nc -6 -vz -G 5 ipv6.google.com 443`" (265).
  - Its expected result is that every port fails, 3389 included (266).
  - So in the usual case no port in (3) succeeds. If the IPv6 path breaks after the first check, the timeouts look the same as closed ports. This is r2's F13 trigger, now on IPv6.
  - "ทดสอบชุดของ (1)" (265) can also be read as including the new home-3389 check from (1). Over IPv6 that check fails unless the home IPv6 address is on the allowlist, so the round would never count.
- **Impact:** none on the gate result.
  - AC-01 also proves the Windows layer for IPv6: every profile blocks by default, and the RDP scope is the address from runbook §2.1.
  - (4) requires the provider to deny IPv6.
- **Minimal fix:** in (3), repeat `/usr/bin/nc -6 -vz -G 5 ipv6.google.com 443` after the last port. Do the same on the hotspot when its IPv6 is tested. Apply the same rule: "ถ้าตัวควบคุมรอบหลังล้ม ผลของรอบนั้นไม่มีผล".
- **Proof of fix:** (3) names its own repeat check after the ports.

## AC status (contract review: can the AC be met, and can it pass wrongly)
| AC | Status | Why |
|---|---|---|
| AC-03 (v2.x) | can be met · wrong PASS only through F14's trigger | F14: a set that allows more is in force beside the one shown. F16 changes no result |
| AC-04 (v2.x) | can be met · false FAIL possible (F15) · wrong PASS only off the approved path | The off-path case needs Server 2022 before the 2024-07 update, together with a client that sends files but cannot receive them. r2 named this assumption that the client behaves the same in both directions. It is still unverified, and the `UBR` condition sits only in the fallback of (b) |
| AC-01, AC-02, AC-05, AC-06, AC-07 | unchanged | `git diff -U0 9157950 ae72752` has hunks only at 3–4, 7, 179–180 and the appended section 237–352 |

## Checked and correct (and how)
- **The change set:**
  - `git diff --stat 6ffd955 ae72752` shows one file, +22/−9.
  - Per-commit hunks (`git diff -U0 <c>^ <c>`), which `git blame` confirms:

    | Commit | Lines |
    |---|---|
    | `75ba240` | 271–272 and 309 |
    | `1206bfb` | 281–282 and 287–289 |
    | `f2ac85e` | 306–308 |
    | `d16f4c5` | 256–258 |
    | `ae72752` | 3–4 and 347–352 |
  - The word diff removes only version labels and one moved backtick. `git diff --check` reports nothing.
  - Every change carries "(v2.2, r2 F<n>)", or "(v2.2, r2)" for the precision point.
- **Red flags:**
  - `bash scripts/controls/red-flags.sh 6ffd955` and `… 9157950` report 0 pattern hits, no control files, and no deleted or renamed tests.
  - `… main` reports 0 pattern hits. Its one control file, `tests/acceptance/ENV-001/test_ac02_host_report.py`, came with v1.x through D-006. v2.x does not touch it.
- **`nc` messages on this Mac:**
  - `/usr/bin/nc -vz -G 2 127.0.0.1 9` printed "nc: connectx to 127.0.0.1 port 9 (tcp) failed: Connection refused" and exited 1. So every failure takes the form "failed: <errno text>".
  - `perl` strerror on this Mac gives:
    - 51 "Network is unreachable"
    - 60 "Operation timed out"
    - 61 "Connection refused"
    - 65 "No route to host"
  - So the examples at line 257 are real messages.
  - `/usr/bin/nc` and `/usr/bin/curl` exist.
- **The new `nc` rules fail safe:**
  - If a port keeps printing another message, it never gets a result. AC-03 then waits for an explanation, just as the F2 rule does for "Connection refused".
  - `sysctl net.inet.tcp.icmp_may_rst` is 1 on this Mac. Under BSD behaviour, an ICMP "administratively prohibited" reply then shows as "Connection refused". A provider that rejects connections therefore falls under the F2 rule, not this one. I did not reproduce this.
  - Read in context, the rule covers failure lines. The 3389 success line is still a result, because (1) itself says "สำเร็จ (exit 0)".
- **Where F12's check sits in the runbook:**
  - Runbook §1.2 (line 21) is the session with the provider's account.
  - §1.3 (lines 22–29) creates the owner's admin account, opens a second session with it, and then disables the built-in account.
  - So "ท้ายข้อ 1.3" comes after the long-lived password is first typed into Windows App.
  - The Plan's list (line 337) names "1.2" but not "1.3". That list is only a summary: it already omits the summary-table bullet (316). The runbook writer follows the bullet at lines 304–308.
  - "C1 และ C2" match ENV-002 v2.6's C1 (Windows App Credentials, PC entry not bound to a credential) and C2 (Passwords and Keychain Access). Both are owner-only, as D-023 item 6 requires.
- **The other parts of F11:**
  - Now that `fDisableClip` is printed, (a) shows every value its criterion names, under either (ค) choice.
  - The `UBR` read is read-only. It fits the "การอ่านและตรวจบน VPS แบบอ่านอย่างเดียว" of lines 242–243.
  - Runbook line 68 states the same KB condition.
  - The distinct-name rule removes r2's false FAIL, provided the owner copies the file made on the VPS. The control copy pasted from the Mac must not be used. The runbook should say which file to copy.
- **The other parts of F10:**
  - Opening the provider console for the new page falls under C9. AC-03 says "ทุกข้อทำหลังทำ ENV-002 checklist ข้อ C9" (272), and the header rule says "ใช้ทุกครั้งที่เปิด RDP หรือ console" (299).
  - The F2 branch that cites (4) (260–261) now rests on a rule set shown to be in force.
- **Against D-023, D-021 item 3 (a) as amended, and ENV-002 v2.6:**
  - "C3 ใช้กับทุกรายการ PC" (307) is consistent with D-023 item 5 T4 ("รายการ PC ใน Windows App ไม่มีโฟลเดอร์ใน Folders"), and stricter.
  - ENV-002 v2.6 AC-03 (2) cites only the "Connection refused" rule (261), and v2.2 did not change that rule. ENV-002's own AC-03 has no rule for other messages and no repeat check. That is a gap in ENV-002's text, not a contradiction.
  - Residual 16 and decision (ค) are cited unchanged (323–324).
  - No v2.2 sentence touches §10 or the snapshot channel.
- **Labels:**
  - Lines 3–4 say v2.2 is an unapproved draft, v1.9 is the last approved version, and the code follows v1.9.
  - Lines 350–351 count r2 as session 2 of 4 and this round as 3 of 4, which matches line 332.

## Not checked (and why)
- **Windows App behaviour:** what Duplicate copies, whether the credential prompt offers to save the password, the file clipboard in either direction (r2's assumption that it behaves the same both ways), and the menu names. The app is not installed.
- **Provider firewall designs (F14):** which budget Windows VPS providers combine several rule sets on one server. This comes from general knowledge only; I used no network.
- **The Server 2022 build that KB5040437 brings:** from memory it is 20348.2582, but I did not verify it. The contract gives no number, so the runbook must, and the runbook review should check it.
- **VPS-side output:** `Get-ItemProperty` with a value the key lacks (expected to print empty, not to fail), the `UBR` read, `Get-Printer` and `net view \\tsclient`. There is no VPS and no Windows here.
- **`nc` against a real remote host, and the ICMP-to-message mapping above:** I contacted no external host.
- **pytest:** no code or tests changed, and `uv run` in the worktree would create `.venv`.
- **`docs/handoff/ENV-001.md`:** I read it only after writing the findings above. It has no v2.x text; its last change is `ae7458a`.

## Questions for the owner
1. **(Precision point, r2 Question 2)** When you approve (ฎ), do you confirm by name the three v2.1 answers that rest on Claude's reading of your 11:2x reply?
   - There is no fallback on the old Windows machine.
   - The VPS policy is always read, and the printer test runs only when the Mac already has a printer.
   - ENV-001's PR merges after ENV-002's.

Ready for the owner's approval (ENV-001 v2.2): yes (no High or Medium open; F10–F13 closed against r2's own fixes; Low findings F14–F16 may stay open and can be fixed in the runbook, checked by the runbook review)
Findings open: 3 (0 High · 0 Medium · 3 Low: F14, F15, F16)
