# TASK FIX-002 — guard-bash เลิกบล็อกคำสั่งที่ไม่อันตราย (false positives) โดยไม่เปิดช่องใหม่

Version v1 (ร่าง 2026-10-22 23:3x) · Owner เจ้าของ repository · Parent D-007 ("Review when: เริ่มงานแก้ guard รอบถัดไป") · `docs/handoff/BOOT-001.md` และ `docs/reviews/BOOT-001-r5.md`, `-r7.md`, `-r11.md` ("the false-positive task") · Tier **High** · Branch `fix/FIX-002-guard-false-positives`
Status: **approved by owner 2026-10-22 23:4x** (acceptance และแผน · (ก) F26 = คงกฎเดิม (ID ต้องมีขีดก่อนตัวเลข) จึงตัด P10 ออกจาก AC-01/AC-05 · (ข) ผู้เขียน patch = **Codex หลัง 2026-10-28 19:41** · (ค) ทำหลัง OPS-001, FIX-001, CORE-004)
Hypothesis (research tasks): ไม่ใช่งานวิจัย

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: **yes** — guard-bash เป็นด่านสิทธิ์ของ agent
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: **yes** — แก้ `.claude/hooks/guard-bash.mjs` และ `scripts/controls/test-controls.mjs` (path ที่ล็อก)

High: เจ้าของอนุมัติแผน, patch เขียนโดยผู้รับบทที่ไม่ใช่ผู้ทำ (session นี้ไม่เขียนกฎที่ควบคุมตัวเอง), security-reviewer pre-review + review แบบ adversarial, PR ติด label

## Goal / user outcome (Thai)
guard-bash บล็อกคำสั่งที่ไม่อันตรายหลายแบบ ทำให้ agent ต้องหยุดถามเจ้าของบ่อย (กฎ N6) หรือใช้ทางอ้อมที่เจ้าของอนุญาตเป็นกรณีๆ งานนี้ให้ guard ปล่อยคำสั่งในรายการข้างล่างเมื่อพิสูจน์ได้ว่าไม่เขียน path ที่ล็อกและไม่รันโค้ดที่ดาวน์โหลดมา **และยังบล็อกทุกรูปแบบอันตรายที่บล็อกอยู่ตอนนี้** · ข้อไหนที่ guard แยกปลอดภัยกับอันตรายไม่ได้จากข้อความคำสั่ง ให้คงบล็อกและบันทึกทางที่เจ้าของอนุญาตไว้แทน (ไม่ฝืนแก้)

## Current behavior and evidence (revision)
คำสั่งที่ถูกบล็อกจริง (live) หรือจาก review:
| # | ตัวอย่าง | แหล่ง |
|---|---|---|
| P1 | Monitor/Bash `until …; do sleep 5; done; echo "$(date '+%H:%M:%S')"` (`$(...)` → "cannot determine directory scope") | F8, r5/r11 live 2026-10-19 23:44 |
| P2 | `case x in a) echo a;; esac` ("unmatched closing parenthesis") | F8, r5 |
| P3 | `git switch -c <branch>` ในโฟลเดอร์ที่ guard หา scope ไม่เจอ | F8, r5 |
| P4 | `` x=`ls docs | sed 's/\.md$//'` `` (backtick ที่มี backslash) | F16, r7 |
| P5 | heredoc body ที่มีคำคล้าย path หรือคำสั่ง (`cat >> file <<'EOF' … EOF`) | handoff BOOT-001 2026-10-19 |
| P6 | `grep -n 'curl .* \| bash' file` (pattern ที่มีคำว่า curl/bash ถูกอ่านเป็น pipe-to-shell) | PROGRESS process deviations ข้อ 5 |
| P7 | `curl -s URL \| node -e '<code อ่าน JSON จาก stdin>'` (ข้อมูลเข้า stdin ไม่ใช่โค้ด) | 2026-10-21, ทางอ้อมที่อนุญาต: `curl -o` แล้ว `node` แยก |
| P8 | `sed -i 's/…`…`…/…/' PROGRESS.md` (backtick ใน script ของ sed ถูกอ่านเป็น path) บนไฟล์ที่ไม่ล็อก | 2026-10-22 live, ทางอ้อมที่อนุญาต: Edit |
| P9 | `V=/c/…/scratchpad; mkdir "$V/x"` หรือ `> "$V/f"` (ตัวแปรที่กำหนดเป็น literal ในคำสั่งเดียวกัน) | 2026-10-21/22 live, ทางอ้อมที่อนุญาต: path ตัวอักษร |
| P10 | branch `research/H001-…` ถูกปฏิเสธเพราะ ID ไม่มีขีดก่อนตัวเลข | F26 (Low) |
| P11 | `node -e "… readFileSync('AGENTS.md') …"` (อ่านอย่างเดียว แต่ข้อความมีชื่อไฟล์ล็อก) | 2026-10-21 live |
`scripts/controls/test-controls.mjs` มี allow-list และ deny tests ของ guard อยู่แล้ว · D-007: การแก้แบบอ่านข้อความทุกรอบ (r5–r9) เคยเปิดรูปคำสั่งใหม่ที่หลุด จึงต้องมีชุด bypass เดิมเป็นตัวกัน

## Scope
- In scope: P1–P10 ตามตัดสินในตาราง Acceptance · test allow/deny ใหม่ใน `test-controls.mjs` · หลักฐาน · handoff · PROGRESS
- Exclusions: backlog ช่องโหว่ของ D-007 (F11–F15, F17, F19–F23) — ไม่แก้และต้องไม่แย่ลง · P11 (`node -e` ที่มีชื่อไฟล์ล็อก): **คงบล็อก** เพราะแยกอ่าน/เขียนจากข้อความไม่ได้อย่างปลอดภัย ทางที่ใช้แทนคือ `sha256sum`/`git hash-object` (บันทึกไว้) · deny rules ใน `.claude/settings.json` (เช่น `cp` จาก path ล็อก) · `check-locked-after.mjs`, `protect-paths`
- Allowed files: `.claude/hooks/guard-bash.mjs`, `scripts/controls/test-controls.mjs` (ผ่าน patch D-006 เท่านั้น), `docs/evidence/FIX-002.md`, `docs/handoff/FIX-002.md`, `docs/proposals/FIX-002-*.patch`, `docs/reviews/FIX-002-*.md`, `PROGRESS.md`, memory ของ Claude (ข้อยกเว้นที่ไม่จำเป็นแล้ว)
- Must not touch: `.claude/settings*.json`, hook อื่น, `.github/**`, `src/**`, `tests/**`, `AGENTS.md`, `CLAUDE.md`

## Inputs / outputs / errors (contract)
guard-bash: exit 0 = อนุญาต, exit 2 = บล็อก (เหมือนเดิม) · ข้อความบล็อกเดิมของรูปแบบที่ยังบล็อกไม่เปลี่ยนความหมาย

## Invariants
- ทุก deny test เดิมยังบล็อก · จำนวน test เดิมไม่ลด · ไม่มี test ถูก skip
- หลักใหม่ทุกข้อปลอดภัยแบบ fail-closed: ถ้าแยกไม่ได้ให้บล็อก
- ผล corpus ของ r5–r11 (input ของ F11–F23) ไม่แย่ลง: input ที่เคยบล็อกยังบล็อก

## Negative cases (ต้องยังบล็อก)
`$(...)` ที่เขียนไฟล์ล็อก (`echo $(date) > AGENTS.md`) · `case` ที่มี redirect เข้าไฟล์ล็อก · `sed -i` บนไฟล์ล็อก (มีหรือไม่มี backtick) · `` x=`echo x > AGENTS.md` `` · heredoc ที่ redirect เข้าไฟล์ล็อก · `curl x | node`, `curl x | node -`, `curl x | bash`, `curl x | node -e "$(cat)"` · `V=AGENTS.md; echo x > "$V"`, `V=.claude; echo x > "$V/settings.json"`, ตัวแปรที่กำหนดนอกคำสั่ง/จาก substitution · `git switch -c` บน main ตามกฎเดิม · push ไป main หรือ branch ที่ไม่ใช่ task branch

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given คำสั่ง P1–P9 ตามตัวอย่าง (และรูปที่ใกล้เคียงที่ปลอดภัย), When ป้อนให้ guard-bash, Then exit 0 · ยกเว้นข้อที่ผู้เขียน patch พิสูจน์ใน handoff ว่าแยกจากรูปอันตรายไม่ได้ (คงบล็อก + เหตุผล + ทางที่ใช้แทน)
- AC-02 Given รูปอันตรายทุกข้อในหัวข้อ Negative cases, When ป้อนให้ guard-bash, Then exit 2
- AC-03 Given `node scripts/controls/test-controls.mjs`, When รัน, Then ผ่านทั้งหมด และจำนวน test ≥ เดิม + test ใหม่ของ AC-01/02
- AC-04 Given corpus ของ input จาก review r5–r11 (F7–F26), When ป้อนให้ guard ก่อนและหลังแก้, Then ไม่มี input ใดเปลี่ยนจากบล็อกเป็นอนุญาต ยกเว้น P1–P10 ที่ตั้งใจ
- AC-05 Given F26 (P10), When เจ้าของเลือก (ดู Plan ข้อ 5), Then push guard รับหรือคงปฏิเสธ ID แบบ `H001` ตามที่เลือก พร้อม test
- AC-06 Given session ใหม่ของ Claude Code บน branch ที่ apply แล้ว, When รันคำสั่ง P1–P9 จริง, Then ไม่ถูกบล็อก (ตรวจ live แบบ P25)

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–03 | patch author + fresh-session reviewer | `node scripts/controls/test-controls.mjs` | L2 |
| 04 | security-reviewer (adversarial) | corpus เดิม + near-miss ใหม่ ก่อน/หลัง | L2 |
| 05 | test | ตามที่เจ้าของเลือก | L2 |
| 06 | Claude session ใหม่ | รันจริง บันทึกใน evidence | L2 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยงหลัก (D-007): การผ่อน parser เปิดรูปคำสั่งที่เขียนไฟล์ล็อกได้ → AC-02/AC-04 + adversarial review · ด่านหลังรัน (`check-locked-after.mjs`), deny rules และ control-gate ยังอยู่เป็นชั้นถัดไป

## Plan, dependencies and unknowns (P06)
1. Understanding: ผ่อน guard เฉพาะรูปที่พิสูจน์ได้ว่าปลอดภัย, ทุกอย่างอื่นคงบล็อก · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่าแก้ช่องโหว่ใน D-007 ด้วย — ไม่ (ข) คิดว่าต้องปล่อยทุกข้อ — ไม่ ข้อที่แยกไม่ได้คงบล็อก (ค) คิดว่าแก้ settings — ไม่
2. Files / reuse: `guard-bash.mjs` (`splitSegments`, การตรวจ substitution, `checkTaskPush`), allow/deny tests เดิม
3. Steps: (1) เจ้าของอนุมัติ + เลือก F26 + เลือกผู้เขียน patch → (2) ผู้เขียน patch ทำ `docs/proposals/FIX-002-guard.patch` + corpus ก่อน/หลัง → (3) security-reviewer pre-review ของ patch (ก่อน apply) → (4) Claude apply ตาม D-006 + ตรวจ hash + fresh-session review → commit → (5) AC-06 live ใน session ใหม่ → PR (label) → merge
4. Risks: ดูข้างบน · ถ้า review พบช่องใหม่ให้ตัดรูปนั้นออก (คงบล็อก) แทนการแก้วน
5. Decisions needed from the owner:
   - (ก) F26: รับ ID แบบ `H001` ใน push guard หรือคงกฎ "ต้องมีขีดก่อนตัวเลข" (แนะนำ: **คงกฎ** เพราะมีทางใช้ `H-001` อยู่แล้วและไม่ต้องแตะ push guard)
   - (ข) ผู้เขียน patch: **แนะนำรอ Codex (หลัง 2026-10-28 19:41)** เพราะ guard คุม Claude เอง และประวัติ D-007 ต้องการผู้เขียนที่ไม่ใช่ Claude · ทางเลือก: Claude session ใหม่ตามการสลับบทบาท + security-reviewer pre-review
   - (ค) ลำดับ: ทำงานนี้หลัง OPS-001, FIX-001, CORE-004

## Authorization (filled by the owner)
- เจ้าของอนุมัติ 2026-10-22 23:4x · ผู้เขียน patch (Codex): ตาม (ข) · Claude: apply ตาม D-006, evidence, handoff, PROGRESS, push task branch, live check

## Budget
1–2 sessions · headless session ไม่เกิน 6 (author, pre-review, fresh review, adversarial review, สำรอง ×2) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่ · หยุดทันทีถ้าพบช่องโหว่ใหม่สองรอบติด (ตามบทเรียน D-007)

## Recovery, compensation and checkpoint
revert PR คืน guard เดิม · ไม่มีผลข้างเคียงนอกเครื่อง

## DoR status / missing items / next action
ครบ: รายการ P1–P11 พร้อมแหล่ง, test-controls เดิม · ขาด: การอนุมัติ, (ก)–(ค) · next: เจ้าของอนุมัติ

## Done scope
merge แล้ว, live check ผ่าน, ข้อยกเว้นที่ไม่จำเป็นแล้วใน memory ของ Claude ถูกอัปเดต
