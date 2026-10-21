# DECISIONS — Sochron1k

Decision log แบบย่อ (Handbook ภาคผนวก G) · สถานะที่ใช้: proposed · accepted · superseded · rejected
เปลี่ยนสถานะเป็น accepted ได้เฉพาะเมื่อเจ้าของตัดสิน agent เขียนได้แค่ proposed

## D-001 สถาปัตยกรรมเริ่มต้น: Python modular monolith + `MetaTrader5` บน Windows, วิจัยก่อน — 2026-10-18 — accepted (เจ้าของอนุมัติในแชท Claude 2026-10-21 ราว 06:55 หลัง SPIKE-001 และ review D-001 r1–r3)
Acceptance scope:
- รับสถาปัตยกรรม, ขอบเขตของเครื่อง (ข้อ 6.1), execution scope (ข้อ 7.1) และ phase gates (ข้อ 13a) ตาม `docs/architecture.md` ที่ commit `6495d94`
- ไม่ได้อนุมัติ: ติดตั้ง dependency ของโปรเจกต์ (ต้องผ่าน dependency admission ทีละตัว), เริ่มวิจัยก่อน ENV-1 และส่งคำสั่งใดๆ ก่อนมี contract E1 ที่อนุญาต
- งานแต่ละชิ้นยังต้องมี contract ที่อนุมัติ
Context: เริ่มใหม่ทั้งหมด เครื่องพัฒนาเป็น Windows ซึ่งใช้แพ็กเกจ `MetaTrader5` ได้โดยตรง (wheel cp310–cp314) ผลลัพธ์ของโปรเจกต์คือหลักฐานว่ามี edge (บท 34) รอบก่อนยังไม่เคยใช้ข้อมูลจริง
Decision: แอป Python 3.12 ตัวเดียว (uv) แบ่ง module ตาม `docs/architecture.md`; `broker/mt5` เป็นจุดเดียวที่ import MetaTrader5; strategy เป็น pure function ที่ใช้ร่วมกันระหว่าง backtest และ Demo; journal เป็น SQLite; dataset เป็น Parquet snapshot; ยังไม่มี web/DB server/Docker; ลำดับงาน BOOT-001 → SPIKE-001 → ENV-1 (Windows VPS + synthetic sentinel, ต้องผ่านก่อนวิจัย) → SLICE-R1 → SLICE-E1 → OPS-1
Why: strategy ชุดเดียวทำได้ตรงที่สุด ทดสอบได้มากที่สุด ชิ้นส่วนน้อยที่สุดสำหรับเจ้าของคนเดียว และ AI ทำงานกับ Python ได้แม่น
Rejected: (B) MQL5 EA + bridge: สองภาษา, protocol ซับซ้อน, เสี่ยงมี strategy สองชุด; เหตุผลเดิมคือพัฒนาบน macOS ซึ่งไม่มีแล้ว · (C) MQL5 ล้วน: เครื่องมือวิจัยอ่อน, optimizer ชวน overfit, ทดสอบอัตโนมัติยาก
Consequences: runner ต้องอยู่บน Windows ที่มี terminal; CI (Linux) ทดสอบส่วน MT5 จริงไม่ได้ จึงต้องมี evidence จากเครื่อง Windows; Python ต้อง ≤ 3.14 จนกว่า MetaTrader5 จะออก wheel ใหม่
Environment boundary (review D-001 r1 F1, เจ้าของเลือก 2026-10-21):
- เป้าหมายคือ Windows VPS เป็น acquisition/execution host ถือ terminal, history cache, `data.acquire`, raw captures, journal, holdout และ Demo runner
- เครื่องเจ้าของเป็น research host ที่รับเฉพาะ snapshot ก่อน cutoff (`docs/architecture.md` ข้อ 6.1)
- ระยะนี้ใช้เครื่องเดียวไปก่อน จึงห้ามตัด holdout, ห้าม ingest ข้อมูลวิจัย และห้ามทดลองกลยุทธ์ จนกว่าด่าน ENV-1 (VPS + synthetic sentinel) จะผ่าน
- ค่าใช้จ่าย VPS อยู่ใน Q-10
- การใช้โฟลเดอร์, VM หรือผู้ใช้คนละคนบนเครื่องเดียวแทนการแยกเครื่อง ต้องเป็นการตัดสินเปลี่ยนกฎของเจ้าของแยกต่างหาก

Execution scope (review D-001 r1 F2):
- ทุก action ภายนอกต้องอยู่ใน scope ที่แก้ไม่ได้ระหว่างรัน ได้แก่ terminal identity, server, บัญชีที่อนุญาต, Demo, action และสัญลักษณ์ที่อนุญาต และวันหมดอายุ
- ตรวจตอนเริ่ม, ตอน reconnect และก่อนทุก action ถ้าไม่ตรงหรือไม่รู้ให้หยุด
- journal, risk และการ reconcile ผูกกับ scope
- ผู้ส่งคำสั่งต่อ scope มีหนึ่งตัว และใช้ terminal เฉพาะงาน
- การเช็กกับการส่งไม่ใช่ atomic จึงยังมีความเสี่ยงที่ระบุไว้ใน `docs/architecture.md` ข้อ 7.1
- E1 ต้องพิสูจน์ด้วย negative cases ที่มีการส่งคำสั่งเป็นศูนย์
- สิทธิ์อ่านอย่างเดียวของ SPIKE-001 ไม่ใช่สิทธิ์ของ E1
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
Consequences: Claude แก้กติกา, hooks, skills และ test ที่ล็อกไม่ได้ เจ้าของต้องแก้เอง, apply patch ที่รีวิวแล้ว หรือปลดล็อกชั่วคราว · ชั้น CI มีผลจริงเมื่อเจ้าของเปิด branch protection ให้ check `control-gate / locked-paths` เป็น required · PR แรกที่เพิ่ม `control-gate.yml` จะไม่ถูก gate นี้ตัดสิน เพราะ main ยังไม่มี gate การรีวิวของเจ้าของจึงเป็น gate ของ BOOT-001 · label ที่ติดแล้วยังค้างอยู่เมื่อมี commit ใหม่ (N1 ใน `docs/handoff/BOOT-001.md`) ยังไม่ได้แก้ · (แก้ 2026-10-20 ให้ตรงเอกสาร permission-modes ปัจจุบัน) ในโหมด bypassPermissions: ask rules ที่เขียนไว้ชัดเจนยังถาม, deny rules บล็อกทุกโหมด, allow rules ไม่มีผล และ hooks ยังทำงาน
Review when: hook บล็อกงานปกติซ้ำ (false positive) · Claude Code หรือ Codex เปลี่ยน format ของ hook/permission · มี failure ที่หลุดผ่านทั้งสามชั้น

## D-005 Skills และ agents ของโปรเจกต์ — 2026-10-18 — proposed
Context: เจ้าของขอให้หา skills/agents เพื่อให้ทำงานได้เร็วขึ้น Handbook บท 9 ให้รับเข้าเฉพาะที่จำเป็นและตรวจทุกไฟล์ก่อนใช้
Decision: สร้าง skills จาก Prompt Library ของ handbook เอง: 11 ตัวฝั่ง Claude Code (`.claude/skills/`) สำหรับงานวางแผน/ลงมือ, 10 ตัวฝั่ง Codex (`.agents/skills/`) สำหรับงานเขียน test/ตรวจ และ subagents 4 ตัว (`.claude/agents/`) ที่ใช้ขั้นตอนเดียวกับฝั่ง Codex · ยังไม่ติดตั้ง skill/plugin ภายนอก ตัวที่น่าสนใจอยู่ในรายการ candidate ของ `docs/tooling/registry.md` พร้อม trigger
Why: ขั้นตอนตรงกับ handbook ทุกตัว ไม่มี supply-chain risk และไม่มีคำสั่งขัดกัน (เช่น skill ภายนอกที่ให้ implementer เขียน test เอง)
Consequences: ยังไม่ได้ทำ eval อัตโนมัติของ skills (SKIPPED) วัดผลจากการใช้งานจริงและ rules-review รายสัปดาห์แทน
Review when: D-001 ได้รับการยอมรับ (พิจารณา candidate ด้าน Python เช่น pyright-lsp, astral) · skill ไม่ถูกเรียกเมื่อควรถูกเรียก หรือถูกเรียกผิดงาน

## D-006 Claude รัน `git apply` ของ patch ใน `docs/proposals/` และ `git push` ของ branch งานเองโดยไม่ต้องขออนุมัติ — 2026-10-20 — accepted (เจ้าของสั่งในแชท Claude) · implement แล้วใน r9 (`2f2b6ca`) · live push ผ่านแล้ว 2026-10-20 21:24 +07 และ CI ของ head นั้นเขียว
Context: ตาม D-004 และ AGENTS.md เจ้าของต้อง copy คำสั่งไปวางเองทุกครั้งที่ apply patch ไฟล์ล็อกหรือ push · 2026-10-20 guard บล็อก `git apply` ของ r8 ที่เจ้าของสั่งให้ Claude รัน · เจ้าของเลือกให้เปลี่ยนเป็นกดปุ่ม Allow ก่อน แล้วสั่งตามมาว่า "เอากฎ ask ออก ... คำสั่งจากเจ้าของโปรเจค" คือไม่ต้องมีหน้าต่างอนุมัติเลย
Decision: Claude รันสองคำสั่งนี้ได้เองโดยไม่ถามและไม่มีหน้าต่างอนุญาต:
- `git apply` ของไฟล์ patch ใน `docs/proposals/`
- `git push` ไป branch งาน แบบไม่ force

ที่ยังบล็อกเหมือนเดิม (ไม่ต้องให้เจ้าของทำอะไรเพิ่ม):
- force push (`-f`, `--force`, `--force-with-lease`, refspec ที่ขึ้นต้นด้วย `+`)
- push ไป main
- reset --hard และ clean
- การเขียนไฟล์ล็อกด้วยวิธีอื่น
- การอ่าน credential

merge ยังเป็นของเจ้าของเท่านั้น
Implementation: ต้องแก้ไฟล์ล็อก ได้แก่ `.claude/settings.json` (เอา push ออกจาก deny), `guard-bash.mjs`, `test-controls.mjs`, CLAUDE.md และ AGENTS.md · Codex ทำเป็น patch r9 (รวมการแก้ F18 ตามที่เจ้าของเลือก), เจ้าของ apply เป็นครั้งสุดท้ายตามกฎเดิม, แล้ว Claude session ใหม่ตรวจ · รายละเอียดอยู่ใน `docs/handoff/BOOT-001.md` หัวข้อ "Owner decision D-006" และ "D-006 revised: no prompt; F18 in r9"
Risk: ก่อนถึงขั้น merge ไม่มีคนอนุมัติแล้ว ทั้งตอน patch แก้ไฟล์ควบคุม และตอน push ออกนอกเครื่อง · patch ใน `docs/proposals/` เขียนโดย agent และถูกตรวจโดย Claude session ใหม่หลังจาก apply แล้ว ไม่ใช่ก่อน · ด่านที่เหลือก่อน merge คือ CI control-gate และ label ของเจ้าของ · hook ตรวจหลังรันยังรายงานการเปลี่ยนไฟล์ล็อกทุกครั้ง
Supersedes (เมื่อ implement แล้ว): ส่วนของ D-004 ที่ให้ "เจ้าของเป็นคน `git apply` เอง" และ "agent ห้าม push"
Review when: มีการ apply หรือ push ที่เจ้าของไม่ได้ตั้งใจ · patch ที่ apply แล้วถูกพบว่าเปลี่ยนสิ่งที่ไม่ได้อยู่ใน handoff

## D-007 ยอมรับความเสี่ยงที่เหลือของ guard-bash สำหรับ BOOT-001 — 2026-10-20 — accepted (เจ้าของเลือกในแชท Claude)
Context: review r5–r9 พบว่าทุกครั้งที่แก้ guard แบบอ่านข้อความคำสั่ง จะมีรูปคำสั่ง shell แบบใหม่ที่หลุดออกมา · หลัง r9 ไม่มี finding ระดับ High ค้าง · CI `control-plane` เขียวบน head ที่ push (`2f2b6ca`, `77a8139`)
Decision: เจ้าของยอมรับว่า guard-bash ยังไม่บล็อกการเขียนไฟล์ล็อกก่อนเกิดในบางรูปแบบ แล้วปิด BOOT-001 ได้โดยไม่ต้องแก้รูปเหล่านี้ก่อน:
- Medium: F11–F15, F19 และ F20 (ผลต่อ Bash จริงของ F20 ยังพิสูจน์ไม่ครบ)
- Low: F8 ส่วน Monitor/case, F16, F17 และ F21–F23

ทุกข้อยังเปิดอยู่ และไปอยู่ในงานแก้ guard รอบถัดไป
ด่านที่ยังเหลือ:
- hook ตรวจหลังรันรายงานทุกครั้งที่ไฟล์ล็อกเปลี่ยน (ตรวจพบได้ แต่ย้อนกลับไม่ได้)
- deny rules และ protect-paths กันการใช้ Edit/Write กับไฟล์ล็อก
- CI control-gate กับ label ของเจ้าของก่อน merge มีผลกับ PR ถัดจาก BOOT-001
Not accepted here: การปิด AC ที่ยัง UNKNOWN (AC-01, 02, 03, 08) ยังต้องมีหลักฐานก่อน · AC-05 ตรวจได้หลัง merge ตามตาราง verification ของ contract
Review when: มีการเขียนไฟล์ล็อกที่ hook ตรวจหลังรันจับได้แต่ guard ปล่อยผ่าน · เริ่มงานแก้ guard รอบถัดไป

## D-008 ข้อยกเว้นของ acceptance BOOT-001: ที่มาของค่าใน AC-08 และ P25 ของ Codex — 2026-10-20 — accepted (เจ้าของเลือกในแชท Claude)
Context: Codex แจ้งก่อน merge (22:23) ว่ามีสองเรื่องที่ D-007 ไม่ครอบคลุม
- AC-08 ข้อย่อย "ไม่มีค่าทางธุรกิจที่ agent เดาเอง" ยัง UNKNOWN เพราะพิสูจน์ที่มาของค่าเดิมไม่ได้ (`docs/reviews/BOOT-001-ac08.md`)
- P25 ฝั่ง Codex โดยรวม FAIL เพราะ approval policy ของ `codex exec` เป็น `never` ไม่ใช่ `on-request` และยังไม่ได้ตรวจในแชทของ VS Code (`docs/tooling/compatibility.md`)

Decision:
1. **AC-08:** เจ้าของยอมรับข้อยกเว้นนี้โดยตรง
   - AC-08 ยังเป็น UNKNOWN ไม่เปลี่ยนเป็น PASS
   - ค่าที่เกี่ยวข้องทุกตัวยังติด `[A]` และต้องให้เจ้าของยืนยันก่อน task ที่ใช้ค่านั้นเริ่ม ได้แก่ risk policy (Q-04), stale-tick 5 วินาที, งบและค่าใช้จ่าย (Q-10) และ retention (Q-12)
2. **P25 ของ Codex:** สภาพแวดล้อมที่ใช้งานจริงของ Codex คือ `codex exec` ที่ Claude เรียกตามคำขอของเจ้าของ
   - ค่าที่คาดไว้สำหรับโหมดนี้คือ sandbox `workspace-write` และ approval `never`
   - sandbox ของโหมดนี้เขียน `.git` ไม่ได้ Claude จึงเป็นคนตรวจ, stage, scan และ commit ไฟล์ของ Codex
   - P25 ในแชทของ VS Code ยังเป็น UNKNOWN และต้องรัน `$verify-agent-setup` ในครั้งแรกที่ใช้แชทนั้น
Why: ค่าทุกตัวที่ยังไม่รู้ที่มายังติดป้ายและถูกกั้นด้วยคำถามที่เปิดอยู่ จึงไม่มีค่าไหนถูกใช้เป็นข้อกำหนดโดยไม่มีเจ้าของยืนยัน · โหมด exec ไม่มีคนตอบ approval จึงมีค่า `never` เป็นปกติ
Not accepted here: ไม่มีข้อไหนกลายเป็น PASS · AC-05 ยังต้องพิสูจน์บน PR ถัดไป
Review when: เริ่ม task ที่ใช้ค่า `[A]` เหล่านี้ · เริ่มใช้ Codex ผ่านแชทของ VS Code

## D-009 ใช้ MetaTrader5 5.0.6231 และ NumPy 2.5.4 ใน SPIKE-001 แบบ SPIKE FIRST — 2026-10-21 — accepted (เจ้าของอนุมัติในแชท Claude ราว 02:49)
Decision: ใช้ `MetaTrader5==5.0.6231` คู่กับ `numpy==2.5.4` เฉพาะใน environment ชั่วคราว (`uv run --with`) ของ SPIKE-001 บน Python 3.12 / Windows x64 · ไม่เพิ่ม dependency ให้โปรเจกต์ และไม่มี lockfile
Why: เป็นแพ็กเกจทางการของ MetaQuotes และ pin นี้มี wheel `cp312-cp312-win_amd64` · OSV ไม่พบ advisory ที่ตรงกับเวอร์ชันนี้ ณ เวลาตรวจ (`docs/reviews/SPIKE-001-dependency-admission.md`)
Conditions:
- ต้องพิสูจน์ใน spike ก่อนว่า import ได้, บันทึกเวอร์ชันได้ และอ่านข้อมูลจากบัญชี Demo ได้ เพราะ native ABI และความเข้ากันกับ terminal ยังไม่รู้
- ถ้า import ไม่ผ่าน ให้เก็บ error จริงไว้ แล้ว review รุ่นอื่นแยกต่างหาก ห้ามลดรุ่นหรือคลาย pin เอง
Review when: ผล SPIKE-001 ใช้ตัดสิน D-001 · มี advisory ใหม่ของสองแพ็กเกจนี้

## D-010 ใช้ tzdata 2026.5 ใน SPIKE-001 — 2026-10-21 — accepted (เจ้าของอนุมัติในแชท Claude ราว 02:49)
Decision: ADMIT `tzdata==2026.5` เฉพาะใน environment ชั่วคราวของ SPIKE-001 เพื่อให้ `zoneinfo` ของ stdlib มีข้อมูล IANA บน Windows · การมีข้อมูล timezone ไม่ได้ตัดสินความหมายของ timestamp ดิบจาก MT5 แทน AC-04
Review when: เริ่มใช้นอก spike

## D-011 ใช้ pytest 9.1.1 และ transitive 5 ตัวใน SPIKE-001 — 2026-10-21 — accepted (เจ้าของอนุมัติในแชท Claude ราว 02:49)
Decision: ADMIT `pytest==9.1.1` พร้อม `colorama==0.4.6`, `iniconfig==2.3.1`, `packaging==26.3`, `pluggy==1.7.0` และ `Pygments==2.21.0` เฉพาะ tests ของ SPIKE-001 · ไม่ใช้ extras · ไม่เพิ่ม dependency หรือ lockfile ให้โปรเจกต์
Why: เวอร์ชัน 9.1.1 พ้นช่วงที่ได้รับผลจาก GHSA-6w46-j5rx-g56g (แก้แล้วใน 9.0.3)
Review when: เลือก test runner ของโปรเจกต์ใน D-001

## D-012 dependency ชุดแรกของโปรเจกต์สำหรับ CORE-001 และ `pyproject.toml`/`uv.lock` ฉบับแรก — 2026-10-21 — accepted (เจ้าของอนุมัติในแชท Claude ราว 08:16 หลังผล admission)
Context: CORE-001 (timebase) เป็นโค้ด Python ชิ้นแรก ต้องมี environment ของโปรเจกต์ · D-010/D-011 อนุมัติแพ็กเกจเฉพาะใน SPIKE-001 จึงใช้แทนไม่ได้ · ผล admission ระดับโปรเจกต์อยู่ใน `docs/reviews/CORE-001-dependency-admission.md` (Codex, ตรวจ PyPI/OSV 2026-10-21 08:02–08:06 +07, ไม่พบ advisory ที่ตรงกับ pin)
Decision: ADMIT 7 pins เข้า `pyproject.toml` (requires-python `>=3.12,<3.13`, src layout) และ `uv.lock`:
- runtime: `tzdata==2026.5` (ข้อมูล IANA ให้ `zoneinfo` บน Windows)
- dev/test: `pytest==9.1.1`, `colorama==0.4.6`, `iniconfig==2.3.1`, `packaging==26.3`, `pluggy==1.7.0`, `Pygments==2.21.0`
Why: ตรงกับที่ contract CORE-001 กำหนด · ทุกตัวมี universal wheel, license เปิด (Apache-2.0, MIT, BSD) และเป็นชุดเดียวกับที่รันผ่านแล้วใน SPIKE-001
Conditions:
- โปรเจกต์เป็น virtual project (`[tool.uv] package = false`) ยังไม่ใช้ build backend จึงไม่มี dependency เวลา build · tests import ผ่าน `pythonpath = ["src"]`
- `hypothesis` (property tests) ไม่รวมในนี้ ถ้า Codex ขอใช้ตาม skill trial ต้องผ่าน admission และตัดสินแยก
- เพิ่ม, ลบ หรือเปลี่ยน pin ใดๆ หลังจากนี้ต้องผ่าน admission และบันทึกใน DECISIONS
- `uv lock` และ `uv sync` ทำครั้งแรกโดย Claude ภายใต้ CORE-001 เท่านั้น
Review when: Python รุ่นใหม่, advisory ใหม่ของแพ็กเกจเหล่านี้ หรือเพิ่มโมดูลที่ต้องใช้แพ็กเกจอื่น (เช่น numpy, pyarrow ใน R1)
