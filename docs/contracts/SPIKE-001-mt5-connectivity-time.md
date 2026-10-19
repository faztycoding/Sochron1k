# TASK SPIKE-001 — MT5 connectivity, time semantics and data depth (read-only)

Version v1 · Owner: เจ้าของ repository · Parent: docs/architecture.md §12 (U1–U3) · Tier **Standard** · Branch `spike/SPIKE-001-mt5-time`
Status: **draft** · รอเจ้าของ (1) อนุมัติ contract นี้ (2) อนุมัติผล `$dependency-admission` ของ `MetaTrader5`, `tzdata` และ `pytest` สำหรับใช้ใน spike เท่านั้น (3) ติดตั้ง MT5 ของโบรกเกอร์และ login บัญชี Demo เอง · **ไม่ต้องรอ D-001** เพราะ spike นี้คือหลักฐานที่ใช้ตัดสิน D-001 (แก้ตาม review BOOT-001 F5)

## Risk tier (Q1–Q6)
- Q1 no · Q2 no (Demo, อ่านอย่างเดียว) · Q3 no (ไม่ส่งข้อมูลบัญชีออกนอกเครื่อง, ปิดบังเลขบัญชีในหลักฐาน) · Q4 no · Q5 no (ไม่มีการส่งคำสั่ง) · Q6 no
- เป็น Standard เพราะเชื่อมระบบภายนอก (terminal ที่ login บัญชีจริงของโบรกเกอร์)

## Goal / user outcome
พิสูจน์สมมติฐานที่เสี่ยงที่สุดก่อนลงทุนเขียนระบบ: Python บนเครื่องนี้คุยกับ MT5 terminal ได้, รู้ความหมายจริงของเวลาในข้อมูลโบรกเกอร์ และรู้ว่าข้อมูลย้อนหลังของ XAU/USD มีมากพอสำหรับวิจัยหรือไม่

## Scope
- In scope: สคริปต์ spike แบบทิ้งได้ใน `spikes/SPIKE-001/`, รายงานหลักฐานใน `docs/evidence/SPIKE-001.md` · รันใน environment uv ชั่วคราว เช่น `uv run --python 3.12 --with MetaTrader5==5.0.6231 --with tzdata python spikes/SPIKE-001/probe.py` ซึ่งไม่สร้าง pyproject.toml หรือ uv.lock
- Exclusions: ห้ามเรียก `order_send`, `order_check` หรือฟังก์ชันที่เปลี่ยนสถานะบัญชี; ห้ามสร้างโค้ดใน `src/`; ห้ามเก็บ snapshot ข้อมูลใน git; ห้ามเพิ่ม dependency ให้โปรเจกต์ (D-001 ยังไม่ได้รับ)
- Allowed files: `spikes/SPIKE-001/**`, `docs/evidence/SPIKE-001.md`, PROGRESS.md

## Invariants
- อ่านอย่างเดียว · ไม่มี credential ในไฟล์ (เจ้าของ login ใน terminal เอง) · เลขบัญชีในหลักฐานต้องถูกปิดบังบางส่วน · ถ้า trade mode ไม่ใช่ Demo สคริปต์หยุดทันที · ไม่สมมติว่า timestamp เป็น UTC หรือเวลา server จนกว่า AC-04 จะได้ผล

## Negative cases
terminal ไม่ได้เปิดหรือไม่ได้ login · บัญชีที่ไม่ใช่ Demo · ชื่อสัญลักษณ์ไม่ตรง (เช่น `XAUUSD` vs `GOLD`) · ช่วงข้อมูลว่าง · ช่วงเปลี่ยน DST

## Acceptance
- AC-01 Given terminal เปิดและ login บัญชี Demo, When รันสคริปต์, Then เชื่อมต่อได้และบันทึก terminal build, ชื่อโบรกเกอร์, server, สกุลเงินบัญชี และ `trade_mode = DEMO` (ปิดบังเลขบัญชี)
- AC-02 Given บัญชีที่ trade mode ไม่ใช่ Demo หรือ terminal ไม่ได้ login, When รันสคริปต์, Then หยุดทันทีพร้อมข้อความ และไม่อ่านข้อมูลอื่นต่อ (ทดสอบด้วยการจำลองค่าใน test)
- AC-03 บันทึก contract spec ของสัญลักษณ์ XAU/USD (digits, point, tick size/value, contract size, volume min/step/max, stops level, filling modes, trade sessions)
- AC-04 บอกได้ว่าค่าเวลาที่ Python API คืนมา (`time` และ `time_msc` ของ tick และเวลาเปิดแท่ง) เป็น UTC ตามเอกสารของ MetaQuotes หรือเลื่อนตามเวลา server ตามรายงานในฟอรัม MQL5 โดยเทียบ tick ล่าสุดกับนาฬิกา UTC ของเครื่อง (บันทึกสถานะ time sync ของ Windows ด้วย) อย่างน้อย 3 ครั้งต่างเวลา พร้อมความคลาดเคลื่อน ถ้าไม่ตรงทั้งสองแบบ ให้รายงาน UNKNOWN พร้อมตัวเลข
- AC-05 จากข้อมูล M1 รอบช่วงเปลี่ยน DST ล่าสุดของ US และ EU สรุปว่าความสัมพันธ์ระหว่างเวลาที่ได้กับ UTC (ตามที่ AC-04 พบ) เปลี่ยนเมื่อไร หรือรายงาน UNKNOWN พร้อมเหตุผล
- AC-06 รายงานวันแรกที่มีข้อมูล M1 และ ticks ของสัญลักษณ์ และสรุปช่องว่างของข้อมูล
- AC-07 red-flag scan กลุ่ม "Order or account mutation surface" ต้องว่าง

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01, 03–06 | สคริปต์ + เจ้าของอ่านรายงาน | `uv run --python 3.12 --with MetaTrader5==5.0.6231 --with tzdata python spikes/SPIKE-001/probe.py` → `docs/evidence/SPIKE-001.md` | L2 + เจ้าของตรวจ |
| 02 | test ที่จำลองค่า trade mode | `uv run --python 3.12 --with pytest pytest spikes/SPIKE-001 -q` | L2 |
| 07 | สคริปต์ | `bash scripts/controls/red-flags.sh main` | L2 |

## Authorization
เจ้าของอนุมัติการเชื่อม terminal แบบอ่านอย่างเดียวกับบัญชี Demo ที่ระบุ: ____ (เจ้าของกรอก) · valid until ____

## Budget
1 session · ทดลองไม่เกิน 3 รอบโดยไม่มีหลักฐานใหม่ · ค่าใช้จ่าย 0

## Recovery
ลบ `spikes/SPIKE-001/` ได้ทั้งโฟลเดอร์ ไม่มีผลข้างเคียงกับบัญชี

## Done scope
implementation (หลักฐาน) → ผลใช้ตัดสินรับ D-001 และกำหนด data contract ของ SLICE-R1
