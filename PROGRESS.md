# PROGRESS — Sochron1k
Updated 2026-10-19 by Claude Code · Session 1 (commits split by area)

## Current task
BOOT-001 v1 · State REVIEWING (round 1 ตอบแล้ว รอเจ้าของ apply patch และ Codex review round 2)
Branch `chore/BOOT-001-project-bootstrap` · 12 commits บน `951ee98` (commit นี้คือ checkpoint ตัวสุดท้าย) · ยังไม่ push · Uncommitted: ไม่มี (`docs/proposals/` gitignored)

## Done (with evidence)
- Bootstrap ครบ: Starter Kit, AGENTS.md, CLAUDE.md, controls (deny rules, 3 hooks, CI), skills 21 ตัว, subagents 4 ตัว, templates, SPEC 0.1, architecture (D-001 proposed), DECISIONS D-001..D-005, contracts BOOT-001 และ SPIKE-001
- รอบแรก: `node scripts/controls/test-controls.mjs` → 19/19 PASS; live ใน session: deny rule บล็อก Write ไป `tests/acceptance/`; guard-bash บล็อก `touch tests/golden/...`, `git push --dry-run`, `cat .env`
- Codex review r1 (`docs/reviews/BOOT-001-r1.md`, 6 findings): ตรวจซ้ำในสำเนาแยกแล้วพบจริงทั้ง 6 ข้อ จึงยอมรับทั้งหมด
- แก้ F1–F6 แล้ว ตาราง ID → การแก้ → หลักฐาน อยู่ใน `docs/handoff/BOOT-001.md`
  - ไฟล์ที่ล็อก (F1, F2, F3, F6 และบางส่วนของ F4/F5 ใน AGENTS.md) → patch `docs/proposals/BOOT-001-r1-controls.patch` (sha256 `80d4aecf…cb4eb`) ให้เจ้าของ apply เอง
  - ไฟล์ที่ไม่ล็อก (F4, F5 และคำอธิบาย F1) → แก้ใน working tree แล้ว: architecture, DECISIONS, SPIKE-001, BOOT-001, registry, compatibility
- หลักฐาน regression: test ชุดใหม่บนโค้ดก่อนแก้ (`3225abc`) ได้ 19 ผ่าน / 9 ไม่ผ่าน คือ F-tests ใหม่ทั้ง 9 ข้อ; บนโค้ดหลังแก้ได้ 28/28; patch apply บนสำเนาที่ไฟล์ยังไม่ track ได้ และผลตรงกับไฟล์ที่ทดสอบทุก byte
- 2026-10-19: เจ้าของสั่งแยก commit `09217d2` ("sew") เป็นส่วนๆ → `git reset 951ee98` (mixed ไม่แตะไฟล์) แล้ว commit ใหม่ 12 ก้อนตามหมวด: repo, controls, agents, skills ×2, ci, templates, spec, tooling, boot, handbook, checkpoint · commit เดิมสำรองไว้ที่ ref `refs/backup/BOOT-001-sew` (ไม่ถูก push)
- ตรวจหลังแยก commit (2026-10-19 13:36 +0700): `node scripts/controls/test-controls.mjs` → 19/19 PASS · `bash scripts/controls/red-flags.sh main` → 6 กลุ่ม เหมือนเดิม (N4, N5) · `node scripts/controls/check-locked-paths.mjs main` → FAIL 40 control changes ตามคาด (PR bootstrap ต้องใช้ label ของเจ้าของ)

## Not done yet
- เจ้าของ apply patch r1 (Claude แก้ไฟล์ที่ล็อกเองไม่ได้)
- Codex review round 2 เฉพาะ F1–F6 (`docs/reviews/BOOT-001-r2.md`)
- P25 ใน session ใหม่ของ Claude Code และของ Codex
- CI ยังไม่เคยรันบน GitHub; ต้องตั้ง branch protection ให้ `control-gate / locked-paths` เป็น required
- รอเจ้าของตัดสิน N1–N5 ใน `docs/handoff/BOOT-001.md` (เช่น label ค้างหลังมี commit ใหม่)

## Decisions and assumptions this session
- เสนอ D-001, D-002, D-004, D-005; บันทึก D-003 ตามการกระทำของเจ้าของ · D-004 เปลี่ยนเป็น gate ที่ใช้ตัวตรวจจาก base revision (F1)
- ลำดับใหม่ (F5): อนุมัติ SPIKE-001 → รัน spike ใน uv env ชั่วคราว → Codex adversarial review → ตัดสิน D-001
- ความหมายของเวลาใน MT5 ยังไม่สรุป (F4): เอกสาร Python API ว่า UTC, ฟอรัมว่าเวลา server → SPIKE-001 AC-04/05 วัด
- สมมติฐานภาษา (A-01) และงานรอบก่อนเป็นข้อมูลอ้างอิง (A-02) ยังรอยืนยัน

## Tried and did not work
- `pandoc` และ `python` ไม่มีในเครื่อง → ใช้สคริปต์ Node แปลง .docx
- ตัวอย่าง hook ใน Handbook (Python, เทียบ substring) จะบล็อกไฟล์นอกโปรเจกต์และไม่รองรับ worktree → เขียนใหม่ด้วยการเทียบ path แบบ repo-relative
- `rm -rf "$S"` ใน scratch ถูก guard บล็อก (ตัวแปรที่ยังไม่ขยายถือว่าไม่รู้ปลายทาง) → ใช้โฟลเดอร์ใหม่แทนการลบ
- เกือบเก็บ patch ไว้ใน path ที่ track: patch มีบรรทัดเก่าของ red-flags.sh ที่มี literal คล้าย secret → ย้ายไป `docs/proposals/` ซึ่ง gitignored

## Pending external operations
- none

## Authority and budget left
- Approved: เจ้าของขอให้ตั้งโปรเจกต์ (2026-10-18), ส่ง review r1 มาให้แก้ และสั่ง commit แยกส่วน (2026-10-19) · ไม่มีอนุมัติให้ agent push, merge, เชื่อมโบรกเกอร์ หรือแก้ไฟล์ที่ล็อก (push เป็นของเจ้าของ)

## Next safe action
- เจ้าของ: `git apply docs/proposals/BOOT-001-r1-controls.patch` → `node scripts/controls/test-controls.mjs` (ควรได้ 28/28) → commit เอง
- เจ้าของ: `git push -u origin chore/BOOT-001-project-bootstrap` แล้วเปิด PR ไป `main` (body ตาม `.github/pull_request_template.md`)
- จากนั้นให้ Codex (chat ใหม่, read-only) ตรวจซ้ำเฉพาะ F1–F6 จาก `docs/handoff/BOOT-001.md`
- หลัง merge: ตั้ง branch protection ให้ `control-gate / locked-paths` และ `ci / control-plane` เป็น required
- Waiting for approval: การตัดสิน N1–N5, D-002..D-005, contract SPIKE-001

On resume: re-check git state and every pending external operation first.
