# TASK SPIKE-001 — MT5 connectivity, time semantics and data depth (read-only)

Version v1.1 · Owner: เจ้าของ repository · Parent: docs/architecture.md §12 (U1–U3) · Tier **Standard** · Branch `spike/SPIKE-001-mt5-time`
Status: **draft** · รอเจ้าของ:
1. อนุมัติ contract นี้
2. อนุมัติผล `$dependency-admission` ใน `docs/reviews/SPIKE-001-dependency-admission.md` ซึ่งเสนอให้:
   - `MetaTrader5` กับ `numpy` เป็น SPIKE FIRST
   - `tzdata`, `pytest` และ transitive อีก 5 ตัว ADMIT เฉพาะใน spike
3. ~~ติดตั้ง MT5 และ login บัญชี Demo~~ เจ้าของทำแล้ว (ดู Authorization)

**ไม่ต้องรอ D-001** เพราะ spike นี้คือหลักฐานที่ใช้ตัดสิน D-001 (แก้ตาม review BOOT-001 F5)
v1.1 (2026-10-21): กรอก Authorization ตามข้อมูลจากเจ้าของ, pin เวอร์ชันครบตามผล dependency admission และใช้ชื่อสัญลักษณ์ `XAUUSDm` ตามที่เจ้าของแจ้ง

## Risk tier (Q1–Q6)
- Q1 no · Q2 no (Demo, อ่านอย่างเดียว) · Q3 no (ไม่ส่งข้อมูลบัญชีออกนอกเครื่อง, ปิดบังเลขบัญชีในหลักฐาน) · Q4 no · Q5 no (ไม่มีการส่งคำสั่ง) · Q6 no
- เป็น Standard เพราะเชื่อมระบบภายนอก (terminal ที่ login บัญชีจริงของโบรกเกอร์)

## Goal / user outcome
พิสูจน์สมมติฐานที่เสี่ยงที่สุดก่อนลงทุนเขียนระบบ: Python บนเครื่องนี้คุยกับ MT5 terminal ได้, รู้ความหมายจริงของเวลาในข้อมูลโบรกเกอร์ และรู้ว่าข้อมูลย้อนหลังของ XAU/USD มีมากพอสำหรับวิจัยหรือไม่

## Scope
- In scope: สคริปต์ spike แบบทิ้งได้ใน `spikes/SPIKE-001/`, รายงานหลักฐานใน `docs/evidence/SPIKE-001.md` · รันใน environment uv ชั่วคราวที่ pin ครบทุกตัว: `uv run --python 3.12 --with MetaTrader5==5.0.6231 --with numpy==2.5.4 --with tzdata==2026.5 python spikes/SPIKE-001/probe.py` ซึ่งไม่สร้าง pyproject.toml หรือ uv.lock · ถ้า import ไม่ผ่าน ให้เก็บ error จริงไว้แล้ว review รุ่นอื่นที่ระบุเฉพาะ ห้ามลดรุ่นหรือคลาย pin เอง
- Exclusions: ห้ามเรียก `order_send`, `order_check` หรือฟังก์ชันที่เปลี่ยนสถานะบัญชี; ห้ามสร้างโค้ดใน `src/`; ห้ามเก็บ snapshot ข้อมูลใน git; ห้ามเพิ่ม dependency ให้โปรเจกต์ (D-001 ยังไม่ได้รับ)
- Allowed files: `spikes/SPIKE-001/**`, `docs/evidence/SPIKE-001.md`, PROGRESS.md

## Invariants
- อ่านอย่างเดียว · ไม่มี credential ในไฟล์ (เจ้าของ login ใน terminal เอง) · เลขบัญชีในหลักฐานต้องถูกปิดบังบางส่วน · ถ้า trade mode ไม่ใช่ Demo สคริปต์หยุดทันที · ไม่สมมติว่า timestamp เป็น UTC หรือเวลา server จนกว่า AC-04 จะได้ผล

## Negative cases
terminal ไม่ได้เปิดหรือไม่ได้ login · บัญชีที่ไม่ใช่ Demo หรือไม่ตรงกับบัญชีที่อนุญาต (server หรือเลข 4 ตัวท้ายต่างจาก Authorization) · ชื่อสัญลักษณ์ไม่ตรง (โบรกเกอร์นี้ใช้ `XAUUSDm` ไม่ใช่ `XAUUSD` หรือ `GOLD`) · ช่วงข้อมูลว่าง · ช่วงเปลี่ยน DST · เลยวันหมดสิทธิ์

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
| 01, 03–06 | สคริปต์ + เจ้าของอ่านรายงาน | `uv run --python 3.12 --with MetaTrader5==5.0.6231 --with numpy==2.5.4 --with tzdata==2026.5 python spikes/SPIKE-001/probe.py` → `docs/evidence/SPIKE-001.md` | L2 + เจ้าของตรวจ |
| 02 | test ที่จำลองค่า trade mode | `uv run --python 3.12 --with pytest==9.1.1 --with colorama==0.4.6 --with iniconfig==2.3.1 --with packaging==26.3 --with pluggy==1.7.0 --with Pygments==2.21.0 pytest spikes/SPIKE-001 -q` | L2 |
| 07 | สคริปต์ | `bash scripts/controls/red-flags.sh main` | L2 |

## Authorization
บัญชีที่เจ้าของระบุ (แจ้งในแชท 2026-10-21 02:43):

| รายการ | ค่า |
|---|---|
| โบรกเกอร์ | Exness |
| Server | `Exness-MT5Trial14` |
| บัญชี | Demo ลงท้าย `8107`, เข้าแบบ Read Only, hedging |
| สัญลักษณ์ | `XAUUSDm` |
| Valid until | **2026-10-28 23:59 +07** (เจ้าของเลือก 2026-10-21) |

ขอบเขต: เชื่อม terminal แบบอ่านอย่างเดียว ห้ามเรียกฟังก์ชันที่ส่งหรือตรวจคำสั่ง

สคริปต์ต้องหยุดถ้า:
- ไม่ใช่ Demo
- server หรือเลข 4 ตัวท้ายไม่ตรงกับตารางนี้
- เลยวันหมดสิทธิ์

เจ้าของ login ใน terminal เอง ไม่มี credential ในไฟล์ใดๆ

สถานะการอนุมัติ: เจ้าของให้ข้อมูลบัญชีและวันหมดสิทธิ์แล้ว แต่ **การเชื่อมต่อด้วยโปรแกรมเริ่มได้ก็ต่อเมื่อเจ้าของอนุมัติ contract นี้และผล dependency admission**

## Budget
1 session · ทดลองไม่เกิน 3 รอบโดยไม่มีหลักฐานใหม่ · ค่าใช้จ่าย 0

## Recovery
ลบ `spikes/SPIKE-001/` ได้ทั้งโฟลเดอร์ ไม่มีผลข้างเคียงกับบัญชี

## Done scope
implementation (หลักฐาน) → ผลใช้ตัดสินรับ D-001 และกำหนด data contract ของ SLICE-R1
