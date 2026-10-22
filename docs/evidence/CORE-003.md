# หลักฐาน CORE-003: `sochron.risk`

Contract: `docs/contracts/CORE-003-risk.md` v1.3 (Tier High; เจ้าของอนุมัติแผน, acceptance และทางเลือก (ก)–(ช) 2026-10-22 07:4x หลัง contract reviews r1–r3 · เลือกการเปลี่ยนของ v1.3 08:5x หลัง security pre-review: F6 ด่านรับวันไทย, F3 เพดานตัวเลข, F7 ห้ามในระดับ E1 · Codex contract reviews r4–r5 ปิด F13/F14) · Branch `feat/CORE-003-risk` · ไฟล์นี้อัปเดตใน commit เดียวกับ implementation v1.3

## สรุปสำหรับเจ้าของ

| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 sizing ตาม H001 + ขอบ exact + cap บน grid | **PASS** | `test_ac01_exact_sizing_grid_caps_and_display_context`: 10,000 / SL 12 → 0.02 lots เสี่ยง 24 · cost 10 → 24.2 · equity 100 → 0 · cap 200 · raw 0.02 พอดี · ขอบที่ปัดก่อน floor จะผิด → 0.01 · max 0.025 → 0.02 · ไม่มีจุดบน grid → 0 · v1.3 เพิ่มแถว uncapped เท่ากับจุดสูงสุดบน grid พอดี → `ok` |
| AC-02 หยุดรายวัน 0.75% ปลดเมื่อขึ้นวันไทยใหม่ | **PASS** | `test_ac02_daily_threshold_latch_rollover_and_time_reversal` + v1.3: baseline รายวันกับการทดลองต่างกันในวันเดียว, เกณฑ์ที่ไม่ใช่ค่า H001 (0.01/0.03) |
| AC-03 หยุดการทดลอง 2% restart โดยผู้มีสิทธิ์ คงหยุดรายวัน | **PASS** | `test_ac03_experiment_latch_authorized_restart_and_daily_preservation`, `test_ac03_restart_uses_distinct_daily_baseline` |
| AC-04 gate คำนวณ sizing ใหม่จากคำขอ เทียบเกณฑ์จาก equity ปัจจุบัน และรับวันไทย | **PASS** | `test_ac04_*`: SL ห่าง 20 → `lots_exceed_sized` · equity 9800 → `daily_halt`, `experiment_halt` · v1.3: state วันที่ 22 กับคำขอวันที่ 23 → `stale_state` · วันที่ 21 → `TimeReversal` · ตารางเหตุผลตามวัน 6 แถว |
| AC-05 ห้ามขยายหรือเอา SL ออก | **PASS** | `test_ac05_stop_change_cannot_widen_or_remove` |
| AC-06 ตาราง error, provenance, frozen, ช่วงค่าสุดขีด, เพดานตัวเลข, ชนิดพอดี, ตรวจซ้ำตอนใช้ | **PASS** | `test_ac06_*`: เพดานตัวเลขทุกช่อง (1,000 หลัก, `|adjusted|` 1,100,000) ปฏิเสธ 236 ครั้ง ช้าสุด 0.000366 วินาที · equity `1E-999999999` → `BadEquity` ใน 0.000036 วินาที · subclass ทุกชนิดถูกปฏิเสธ · provenance รับ dict / MappingProxyType / Mapping อื่น อ่านครั้งเดียว · แก้ฟิลด์ของ request/state/policy หลังสร้างแล้วถูกจับตอนใช้ |
| AC-07 ขอบเขต import, ไม่มี float/random/นาฬิกา/I/O, red-flags | **PASS** | `test_ac07_risk_*` (architecture) · red-flag กลุ่ม secret และ order/account mutation ว่าง |

ชุดทดสอบทั้งหมด **651 passed, 0 skipped** ที่ 10:02:46 (CORE-001/002 และ architecture เดิม + acceptance/golden ของ CORE-003 583 ข้อ + unit 22 ข้อ)

## สิ่งที่ส่งมอบ

| ไฟล์ | หน้าที่ |
|------|---------|
| `src/sochron/risk/policy.py` | `RiskPolicy` (frozen; ตรวจชนิดพอดี/โดเมน; provenance อ่านครั้งเดียวแล้วเก็บเป็นสำเนา immutable), `H001_RISK` (ค่าและ provenance literal), `unknowns()`, `validate_policy()` (ตรวจ policy ซ้ำทุกครั้งที่ใช้), `finite_bounded()` (เพดานตัวเลข ตรวจก่อนแปลงเป็นตรรกยะ), helper ของ exact arithmetic และ `display()` |
| `src/sochron/risk/sizing.py` | `SizeDecision`, `size_position()` ตัดสินด้วย `Fraction` (floor, cap บน grid, ขั้นต่ำ) · ค่าแสดงผลคำนวณแบบ exact แล้วปัดครั้งเดียว |
| `src/sochron/risk/halts.py` | `HaltState` (ผูก policy), `start_experiment`, `update_equity`, `restart_experiment` (เฉพาะตอน halt, ผู้มีสิทธิ์ + เหตุผล, คงหยุดรายวัน) |
| `src/sochron/risk/gate.py` | `EntryRequest`, `GateDecision`, `check_entry(request, equity, day, state, model, cost_per_lot)` (ตรวจ input ครบก่อน, `stale_state`, sizing ใหม่จากคำขอ, เกณฑ์จาก equity ปัจจุบัน), `check_stop_change` |
| `src/sochron/risk/errors.py` | `RiskError(ValueError)` และ `BadPolicy`, `BadEquity`, `BadStop`, `BadHaltClear`, `TimeReversal` |
| `tests/unit/risk/test_risk_unit.py` | unit tests ของผู้ทำ 22 ข้อ (รวม regression ของ security pre-review F1/F2/F4/F5 และ v1.3) |

การตัดสินระหว่างทำ:
- ค่าแสดงผลไม่แปลงผ่านจำนวนเต็มขนาดใหญ่ (ร่างแรกใช้ ~9.5 วินาทีต่อครั้งที่เลขชี้กำลังสุดขีด → คำนวณแบบ exact ใน context ไม่จำกัด แล้ว `create_decimal` ครั้งเดียว)
- ข้อความ error ไม่พิมพ์ค่าที่เกินเพดาน เพราะ Python แปลงจำนวนเต็มใหญ่เป็น str ไม่ได้
- security pre-review F1 (subclass), F2 (lots ใหญ่มาก), F4 (แก้ฟิลด์หลังสร้าง), F5 (Mapping เปลี่ยนระหว่างอ่าน) แก้ทีละ commit พร้อม regression ที่ fail ก่อน/pass หลัง (`e1a095b`, `d7a312c`, `0c00d92`)
- v1.3: dry run ของ tests ที่ล็อกชุดใหม่กับร่างพบ 151 แถวที่แก้ฟิลด์ของ policy หลังสร้าง → เพิ่ม `validate_policy` ที่ใช้ร่วมกับ constructor จึงผ่านครบ
- ไม่แตะ `costs`, `timebase`, `core`

## Demo สำหรับเจ้าของ (Tier High: ต้องรันเองก่อน merge, Git Bash ที่ root ของ repo)

1. ชุดทดสอบทั้งหมด: `uv run --offline pytest tests -q -p no:cacheprovider` → ต้องได้ `651 passed` และไม่มี skipped (ใช้เวลาราว 3 วินาที)
2. sizing ของ H001 และ gate (รวมการปฏิเสธ state ที่ยังไม่เลื่อนวัน):
   ```bash
   PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from datetime import date; from sochron.costs import H001_COSTS; from sochron.risk import H001_RISK, size_position, start_experiment, EntryRequest, check_entry; d = date(2026, 10, 22); print(size_position(D('10000'), D('12.00'), H001_COSTS, H001_RISK)); s = start_experiment(D('10000'), d, H001_RISK, 'owner', 'demo'); r = EntryRequest('long', D('0.02'), D('4012.90'), D('4000.90'), 0); print(check_entry(r, D('10000'), d, s, H001_COSTS)); print(check_entry(r, D('9800'), d, s, H001_COSTS)); print(check_entry(r, D('10000'), date(2026, 10, 23), s, H001_COSTS))"
   ```
   ผลที่ต้องได้:
   ```text
   SizeDecision(lots=Decimal('0.02'), risk_money=Decimal('25.0000'), risk_per_lot=Decimal('1200.00'), actual_risk=Decimal('24.0000'), reason='ok')
   GateDecision(allowed=True, reasons=())
   GateDecision(allowed=False, reasons=('daily_halt', 'experiment_halt'))
   GateDecision(allowed=False, reasons=('stale_state',))
   ```
3. agent ปลดการหยุดไม่ได้: `PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from datetime import date; from sochron.risk import H001_RISK, start_experiment; start_experiment(D('10000'), date(2026, 10, 22), H001_RISK, 'claude', 'try')"` → บรรทัดสุดท้ายต้องเป็น `sochron.risk.errors.BadHaltClear: 'claude' is not allowed to start or restart this experiment`

## Checks (2026-10-22, +07, Windows 11, Python 3.12.15 ผ่าน uv 0.13.0)

| Command | ผล | Commit | เวลา |
|---------|-----|--------|------|
| Codex contract review r1/r2/r3 | F1–F12 → v1.1/v1.2 → r3 ready for test authoring | `d79b3f5`, `01a74f5`, `fae11df` | 07:03–07:42 |
| Codex tests patch r1 → apply standalone → hash 3 ไฟล์ตรง → `-R --check` → fresh review tests-r1 | PASS · commit red (7 failed ตามคาด, 45 passed) | `831fa60` | 08:04–08:28 |
| implementation v1.2 รอบแรก | 68 passed, 0 skipped | `ab23325` | 08:29:05 |
| security-reviewer pre-review (`docs/reviews/CORE-003-security-pre-r1.md`) | F1–F8 · แก้ F1/F2/F4/F5 (72 passed) · F3/F6/F7 เจ้าของเลือก · F8 ถ้อยคำ | `737632b`–`0c00d92` | 08:3x–08:5x |
| Codex contract review r4/r5 ของ v1.3 | F13/F14 → แก้ → r5 ปิด, ready for test authoring | `e414246`, `fcf77c5` | 09:0x–09:18 |
| Codex tests patch r2 (SHA256 `9a5d343c…`) → `git apply --check` + `git apply` standalone → detector รายงาน 2 ไฟล์ตรง target → SHA256/blob 4 ค่าตรง handoff → `-R --check` | PASS ทุกค่า | `81322d9` | 09:40–09:45 |
| fresh-session review `docs/reviews/CORE-003-tests-r2.md` | ready to commit red · F1 Medium, F3 Low (เจ้าของตัดสิน) · F2, F4–F6 Low (Codex follow-up) | `81322d9` | 09:45–10:00 |
| red state: suite โดย deselect `test_ac06_extreme_equity_rejection_deadline` | **382 failed (ตามคาด ทั้งหมดในไฟล์ acceptance ของ CORE-003), 266 passed, 1 deselected** | `81322d9` | 09:40:37–09:41:17 |
| red state: test ข้างบนเดี่ยวๆ ใต้ `timeout 120` | exit 124 ไม่จบ (v1.2 ไม่มีเพดาน จึงสร้างจำนวนเต็มใหญ่ใน C call เดียวที่ถือ GIL; watchdog 10 วินาทีหยุดไม่ได้ = tests-r2 F1) | `81322d9` | 09:42:46–09:44:46 |
| `uv run --offline pytest tests -q -p no:cacheprovider` หลังวาง v1.3 | **PASS 651 passed, 0 skipped, 2.68 s** (ไม่ deselect) | commit ที่อัปเดตไฟล์นี้ | 10:02:46 |
| test equity `1E-999999999` เดี่ยวๆ (`-s`) | PASS · `BadEquity` ใน 0.000036 วินาที | เดียวกัน | 10:03 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS exit 0 · "Type checks disabled": `type: ignore[arg-type]` 2 จุดใน unit test เชิงลบ (`HaltState(..., 0, False)` และ `check_entry` ที่จงใจส่ง day เป็น str) + ข้อความในเอกสาร · "Lint disabled": คำในข้อความเอกสาร · "Control files touched": tests ที่ล็อก 3 ไฟล์ (มาจาก patch ของ Codex) และ `policy.py`/ชื่อไฟล์ review (heuristic) · กลุ่ม secret และ order/account mutation ว่าง | เดียวกัน | 10:04 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL ตามคาด: tests ที่ล็อก 3 ไฟล์ต้องมี label `owner-approved-control-change` | เดียวกัน | 10:04 |
| `git diff --check` · `git diff 81322d9 -- tests/acceptance tests/golden tests/architecture` | PASS · ว่าง | เดียวกัน | 10:04 |

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- Linux/CI: ยังไม่มี Python job ใน CI ผลทั้งหมดมาจาก Windows
- tests-r2 F1: ถ้าวันหนึ่งเพดานตัวเลขหายไป test เวลาจะทำให้ทั้ง suite ค้างแทนที่จะ fail (ไม่เคยผ่านแบบผิดๆ) · รอเจ้าของเลือกวิธีแก้
- การยืนยันตัวตนผู้ปลด halt, การบันทึก/กู้ HaltState จาก journal, การห้าม start ซ้ำในวันเดียวกัน และการผูกผล gate กับคำสั่งจริง เป็นงานของ E1 (contract ข้อ "ข้อบังคับที่ส่งต่อให้ contract E1")
- review tests-r1 F5: architecture checker ไม่จับ `time.localtime()`, `os.urandom()`, `uuid.uuid4()`, `subprocess`, `sys.stdout.write` → โค้ด risk ไม่ใช้สิ่งเหล่านี้ (ตรวจด้วยตา) · เป็นงาน follow-up ของ test author
- ยังไม่ผ่าน Codex cross-agent review ของ implementation v1.3 · เจ้าของยังไม่ได้รัน demo
