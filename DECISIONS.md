# DECISIONS — Sochron1k

Decision log แบบย่อ (Handbook ภาคผนวก G) · สถานะที่ใช้: proposed · accepted · superseded · rejected
เปลี่ยนสถานะเป็น accepted ได้เฉพาะเมื่อเจ้าของตัดสิน agent เขียนได้แค่ proposed

## D-001 สถาปัตยกรรมเริ่มต้น: Python modular monolith + `MetaTrader5` บน Windows, วิจัยก่อน — 2026-10-18 — proposed
Context: เริ่มใหม่ทั้งหมด เครื่องพัฒนาเป็น Windows ซึ่งใช้แพ็กเกจ `MetaTrader5` ได้โดยตรง (wheel cp310–cp314) ผลลัพธ์ของโปรเจกต์คือหลักฐานว่ามี edge (บท 34) รอบก่อนยังไม่เคยใช้ข้อมูลจริง
Decision: แอป Python 3.12 ตัวเดียว (uv) แบ่ง module ตาม `docs/architecture.md`; `broker/mt5` เป็นจุดเดียวที่ import MetaTrader5; strategy เป็น pure function ที่ใช้ร่วมกันระหว่าง backtest และ Demo; journal เป็น SQLite; dataset เป็น Parquet snapshot; ยังไม่มี web/DB server/Docker; ลำดับงาน BOOT-001 → SPIKE-001 → SLICE-R1 → SLICE-E1 → OPS-1
Why: strategy ชุดเดียวทำได้ตรงที่สุด ทดสอบได้มากที่สุด ชิ้นส่วนน้อยที่สุดสำหรับเจ้าของคนเดียว และ AI ทำงานกับ Python ได้แม่น
Rejected: (B) MQL5 EA + bridge: สองภาษา, protocol ซับซ้อน, เสี่ยงมี strategy สองชุด; เหตุผลเดิมคือพัฒนาบน macOS ซึ่งไม่มีแล้ว · (C) MQL5 ล้วน: เครื่องมือวิจัยอ่อน, optimizer ชวน overfit, ทดสอบอัตโนมัติยาก
Consequences: runner ต้องอยู่บน Windows ที่มี terminal; CI (Linux) ทดสอบส่วน MT5 จริงไม่ได้ จึงต้องมี evidence จากเครื่อง Windows; Python ต้อง ≤ 3.14 จนกว่า MetaTrader5 จะออก wheel ใหม่
Review when: ต้องย้ายไป host ที่ไม่ใช่ Windows · `MetaTrader5` หยุดดูแลหรือเปลี่ยนแบบไม่เข้ากัน · ต้องการ logic ฝั่ง terminal ที่ทำงานต่อได้แม้ Python ล่ม · latency ที่ต้องการต่ำกว่าที่ polling ทำได้
Before accepting (ลำดับที่เดินได้จริง แก้ตาม review F5):
1. เจ้าของอนุมัติ contract SPIKE-001 และผล `$dependency-admission` ของ `MetaTrader5` สำหรับใช้ใน spike เท่านั้น
2. รัน SPIKE-001 ได้เลยโดยไม่ต้องรอ D-001 เพราะ spike คือหลักฐานที่ D-001 ต้องใช้ spike ใช้ environment uv ชั่วคราว (`uv run --with`) และไม่เพิ่ม dependency ให้โปรเจกต์
3. Codex ทำ `$adversarial-design-review` โหมด architecture โดยใช้หลักฐาน SPIKE-001
4. เจ้าของรับหรือปฏิเสธ D-001 ถ้าผล U1–U3 ขัดกับข้อเสนอ ให้กลับไปที่ `/architecture-options`

## D-002 Tool binding: Claude Code ทำ, Codex เขียน test และตรวจ, เจ้าของอนุมัติ — 2026-10-18 — proposed
Context: Handbook v5 กำหนด binding ค่าเริ่มต้นเป็น Claude Code + Codex ใน VS Code ซึ่งทั้งสองติดตั้งอยู่แล้ว (Claude Code 2.1.301, Codex IDE 26.1007.21434)
Decision: Claude Code = planner + implementer · Codex = test author + reviewer (chat ใหม่ต่อ task, review แบบ read-only) · CI = verifier · เจ้าของ = approver คนเดียว · งาน Lite ใช้ Claude Code ตัวเดียวพร้อม red-flag scan ได้
Why: ผู้ทำ ผู้เขียน test และผู้ตรวจไม่ใช่ session เดียวกัน (หลัก 9) และสองผู้ผลิตช่วยลดจุดบอดที่ซ้ำกัน
Consequences: ทุก task ระดับ Standard ขึ้นไปต้องมี Codex review และงาน High ต้องให้ Codex เขียน test ก่อน; subagents ของ Claude เป็นแค่ pre-review
Review when: quota ของเครื่องมือหนึ่งหมด (สลับทั้งชุดชั่วคราวและบันทึกใน PROGRESS.md) · Failure library แสดงว่าเครื่องมือหนึ่งพลาดงานประเภทเดิมซ้ำ

## D-003 เริ่มใหม่: งานรอบก่อนเป็นข้อมูลอ้างอิงเท่านั้น — 2026-09-29 — accepted (โดยการกระทำของเจ้าของ, commit `951ee98`)
Context: เจ้าของลบไฟล์ทั้งหมด 415 ไฟล์ของรอบก่อนและเก็บประวัติไว้ใน git เพื่อกู้คืนได้
Decision: โค้ด, contracts, ADRs และ Blueprint v1.1 ของรอบก่อน (`a3b3fbf`) เป็นข้อมูลอ้างอิง ไม่ใช่ข้อกำหนด ไม่มีอะไรถูกนำกลับมาโดยไม่มี task contract ค่าทางธุรกิจจากรอบก่อนใน SPEC.md ติดป้าย [A] จนกว่าเจ้าของยืนยัน
Consequences: ถ้าต้องการชิ้นส่วนเดิม (เช่น ตรรกะ risk sizing) ให้เขียน contract ที่ระบุ commit และไฟล์ต้นทาง แล้วผ่าน review ตามปกติ

## D-004 Control plane: locked paths บังคับสามชั้น — 2026-10-18 — proposed (Q6: เจ้าของต้องรับรอง)
Context: หลัก 6 "บังคับด้วยระบบ ไม่ใช่ด้วยคำขอ" และภาคผนวก O
Decision: (1) deny rules ใน `.claude/settings.json` (2) PreToolUse hooks `protect-paths` / `guard-bash` (Node, รองรับ worktree; guard ตีความปลายทางจริงของคำสั่ง shell ตาม review F3) (3) CI gate `control-gate.yml` (pull_request_target) ที่รัน `check-locked-paths.mjs` ฉบับจาก base revision กับ commits ของ PR โดยไม่รันโค้ดจาก PR ตรวจทุก commit สำหรับไฟล์ append-only และ fail เมื่อไม่มี label `owner-approved-control-change` (review F1, F2) · `ci.yml` รัน self-tests ของ PR เป็นข้อมูลประกอบ ไม่ใช่ gate · Codex ใช้ `workspace-write` + `on-request` (`.codex/config.toml`, มีผลเมื่อ trust โปรเจกต์) · agent ห้าม push/merge
การแก้ไฟล์ที่ล็อก: agent ทำเป็น patch ใน `docs/proposals/` (gitignored) ให้ Codex รีวิว แล้วเจ้าของเป็นคน `git apply` เอง
Why: ไฟล์คำสั่ง (AGENTS.md) เป็นแค่ context ส่วนการบล็อกจริงต้องใช้ hook/permission/CI (Claude Code docs: memory) และ test ที่ล็อกกัน F02
Consequences: Claude แก้กติกา, hooks, skills และ test ที่ล็อกไม่ได้ เจ้าของต้องแก้เอง, apply patch ที่รีวิวแล้ว หรือปลดล็อกชั่วคราว · ชั้น CI มีผลจริงเมื่อเจ้าของเปิด branch protection ให้ check `control-gate / locked-paths` เป็น required · PR แรกที่เพิ่ม `control-gate.yml` จะไม่ถูก gate นี้ตัดสิน เพราะ main ยังไม่มี gate การรีวิวของเจ้าของจึงเป็น gate ของ BOOT-001 · label ที่ติดแล้วยังค้างอยู่เมื่อมี commit ใหม่ (N1 ใน `docs/handoff/BOOT-001.md`) ยังไม่ได้แก้ · โหมด bypassPermissions ทำให้ ask rules ไม่ถาม แต่ deny rules และ hooks ยังบังคับ
Review when: hook บล็อกงานปกติซ้ำ (false positive) · Claude Code หรือ Codex เปลี่ยน format ของ hook/permission · มี failure ที่หลุดผ่านทั้งสามชั้น

## D-005 Skills และ agents ของโปรเจกต์ — 2026-10-18 — proposed
Context: เจ้าของขอให้หา skills/agents เพื่อให้ทำงานได้เร็วขึ้น Handbook บท 9 ให้รับเข้าเฉพาะที่จำเป็นและตรวจทุกไฟล์ก่อนใช้
Decision: สร้าง skills จาก Prompt Library ของ handbook เอง: 11 ตัวฝั่ง Claude Code (`.claude/skills/`) สำหรับงานวางแผน/ลงมือ, 10 ตัวฝั่ง Codex (`.agents/skills/`) สำหรับงานเขียน test/ตรวจ และ subagents 4 ตัว (`.claude/agents/`) ที่ใช้ขั้นตอนเดียวกับฝั่ง Codex · ยังไม่ติดตั้ง skill/plugin ภายนอก ตัวที่น่าสนใจอยู่ในรายการ candidate ของ `docs/tooling/registry.md` พร้อม trigger
Why: ขั้นตอนตรงกับ handbook ทุกตัว ไม่มี supply-chain risk และไม่มีคำสั่งขัดกัน (เช่น skill ภายนอกที่ให้ implementer เขียน test เอง)
Consequences: ยังไม่ได้ทำ eval อัตโนมัติของ skills (SKIPPED) วัดผลจากการใช้งานจริงและ rules-review รายสัปดาห์แทน
Review when: D-001 ได้รับการยอมรับ (พิจารณา candidate ด้าน Python เช่น pyright-lsp, astral) · skill ไม่ถูกเรียกเมื่อควรถูกเรียก หรือถูกเรียกผิดงาน
