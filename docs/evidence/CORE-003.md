# หลักฐาน CORE-003: `sochron.risk`

Contract: `docs/contracts/CORE-003-risk.md` v1.2 (Tier High; เจ้าของอนุมัติแผน, acceptance และทางเลือก (ก)–(ช) 2026-10-22 07:4x หลัง contract reviews r1–r3) · Branch `feat/CORE-003-risk` · ไฟล์นี้ถูกเพิ่มใน commit เดียวกับ implementation

## สรุปสำหรับเจ้าของ

| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 sizing ตาม H001 + ขอบ exact + cap บน grid | **PASS** | `test_ac01_exact_sizing_grid_caps_and_display_context`: 10,000 / SL 12 → 0.02 lots เสี่ยง 24 · cost 10 → 24.2 · equity 100 → 0 · cap 200 · raw 0.02 พอดี · ขอบที่ปัดก่อน floor จะผิด → 0.01 · max 0.025 → 0.02 · ไม่มีจุดบน grid → 0 |
| AC-02 หยุดรายวัน 0.75% ปลดเมื่อขึ้นวันไทยใหม่ | **PASS** | `test_ac02_daily_threshold_latch_rollover_and_time_reversal` |
| AC-03 หยุดการทดลอง 2% restart โดยผู้มีสิทธิ์ คงหยุดรายวัน | **PASS** | `test_ac03_experiment_latch_authorized_restart_and_daily_preservation` |
| AC-04 gate คำนวณ sizing ใหม่จากคำขอ และเทียบเกณฑ์จาก equity ปัจจุบัน | **PASS** | `test_ac04_entry_recomputes_sizing_and_collects_exact_reasons`: SL ห่าง 20 → `lots_exceed_sized` · equity 9800 → `daily_halt`, `experiment_halt` |
| AC-05 ห้ามขยายหรือเอา SL ออก | **PASS** | `test_ac05_stop_change_cannot_widen_or_remove` |
| AC-06 ตาราง error, provenance literal, frozen, ช่วงค่าสุดขีด | **PASS** | `test_ac06_validation_provenance_immutability_and_range` |
| AC-07 ขอบเขต import, ไม่มี float/random/นาฬิกา/I/O, red-flags | **PASS** | `test_ac07_risk_*` (architecture) · red-flag กลุ่ม secret และ order/account mutation ว่าง |

ทั้ง 7 ข้อผ่านพร้อมกันในรันแรกหลังวางโค้ด: **68 passed, 0 skipped** (CORE-001/002 เดิม 45 + acceptance 6 + architecture 1 + unit 16) ที่ 08:29:05

## สิ่งที่ส่งมอบ

| ไฟล์ | หน้าที่ |
|------|---------|
| `src/sochron/risk/policy.py` | `RiskPolicy` (frozen; ตรวจชนิด/โดเมน; provenance 5 keys เป็นสำเนา immutable), `H001_RISK` (ค่าและ provenance literal ตาม contract), `unknowns()`, helper ของ exact arithmetic และ `display()` (ปัดครั้งเดียวใน `sochron.costs.CONTEXT`, Overflow/Underflow → `RiskError`) |
| `src/sochron/risk/sizing.py` | `SizeDecision`, `size_position()` ตัดสินด้วย `Fraction` (floor, cap บน grid, ขั้นต่ำ) · ค่าแสดงผลคำนวณแบบ exact ด้วย Decimal แล้วปัดครั้งเดียว |
| `src/sochron/risk/halts.py` | `HaltState` (ผูก policy), `start_experiment`, `update_equity` (แยก branch วันเดิม/วันใหม่), `restart_experiment` (เฉพาะตอน halt, ผู้มีสิทธิ์ + เหตุผล, คงหยุดรายวัน) |
| `src/sochron/risk/gate.py` | `EntryRequest`, `GateDecision`, `check_entry` (sizing ใหม่จากคำขอ + เกณฑ์จาก equity ปัจจุบัน + เหตุผลครบ), `check_stop_change` |
| `src/sochron/risk/errors.py` | `RiskError(ValueError)` และ `BadPolicy`, `BadEquity`, `BadStop`, `BadHaltClear`, `TimeReversal` |
| `tests/unit/risk/test_risk_unit.py` | unit tests ของผู้ทำ 16 ข้อ รวมข้อเสนอ coverage ของ review tests-r1 (F1–F3) และแชท Codex ของเจ้าของ (policy ที่ไม่ใช่ค่า H001, volume_step 0.02) |

การตัดสินระหว่างทำ:
- ค่าแสดงผลไม่แปลงผ่านจำนวนเต็มขนาดใหญ่: ร่างแรกใช้ `Decimal(int)` จาก `Fraction` ทำให้กรณีเลขชี้กำลังสุดขีดใช้เวลา ~9.5 วินาทีต่อครั้ง → เปลี่ยนเป็นคำนวณผลคูณ/ผลบวกแบบ exact ใน context ที่ไม่จำกัด precision แล้ว `create_decimal` ครั้งเดียว (unit tests 19 วินาที → 0.3 วินาที)
- ข้อความ error ของช่วงค่าสุดขีดไม่พิมพ์ค่า exact เพราะจำนวนเต็มเกินขีดจำกัดการแปลงเป็น str ของ Python
- gate ใช้ `Fraction` กับ `abs()` ทุกจุด จึงไม่แตะ Decimal context ของผู้เรียก (review tests-r1 F6 ข้อสังเกต)
- ไม่แตะ `costs`, `timebase`, `core`

## Demo สำหรับเจ้าของ (Tier High: ต้องรันเองก่อน merge, Git Bash ที่ root ของ repo)

1. ชุดทดสอบทั้งหมด: `uv run --offline pytest tests -q -p no:cacheprovider` → ต้องได้ `68 passed` และไม่มี skipped
2. sizing ของ H001 และ gate:
   ```bash
   PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from datetime import date; from sochron.costs import H001_COSTS; from sochron.risk import H001_RISK, size_position, start_experiment, EntryRequest, check_entry; print(size_position(D('10000'), D('12.00'), H001_COSTS, H001_RISK)); s = start_experiment(D('10000'), date(2026, 10, 22), H001_RISK, 'owner', 'demo'); r = EntryRequest('long', D('0.02'), D('4012.90'), D('4000.90'), 0); print(check_entry(r, D('10000'), s, H001_COSTS)); print(check_entry(r, D('9800'), s, H001_COSTS))"
   ```
   ผลที่ต้องได้:
   ```text
   SizeDecision(lots=Decimal('0.02'), risk_money=Decimal('25.0000'), risk_per_lot=Decimal('1200.00'), actual_risk=Decimal('24.0000'), reason='ok')
   GateDecision(allowed=True, reasons=())
   GateDecision(allowed=False, reasons=('daily_halt', 'experiment_halt'))
   ```
3. agent ปลดการหยุดไม่ได้: `PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from datetime import date; from sochron.risk import H001_RISK, start_experiment; start_experiment(D('10000'), date(2026, 10, 22), H001_RISK, 'claude', 'try')"` → บรรทัดสุดท้ายต้องเป็น `sochron.risk.errors.BadHaltClear: 'claude' is not allowed to start or restart this experiment`

## Checks (2026-10-22, +07, Windows 11, Python 3.12.15 ผ่าน uv 0.13.0)

| Command | ผล | Commit | เวลา |
|---------|-----|--------|------|
| Codex contract review r1/r2/r3 | F1–F12 → v1.1/v1.2 → r3 ready for test authoring | `d79b3f5`, `01a74f5`, `fae11df` | 07:03–07:42 |
| Codex tests patch `docs/proposals/CORE-003-tests.patch` (SHA256 `7227c6ba…`) → `git apply` standalone → SHA256/blob 3 ไฟล์ตรง handoff → `git apply -R --check` | PASS ทุกค่า | `831fa60` | 08:04:40 |
| fresh-session review `docs/reviews/CORE-003-tests-r1.md` (รวม suite ก่อนมีโค้ด) | ready to commit red · **7 failed (ตามคาด), 45 passed** · coverage F1–F3 Medium/Low, F4–F6 คำถาม | `831fa60` | 08:12:51 |
| แชท Codex ใน VS Code ของเจ้าของตรวจ patch เดียวกัน | ไม่มี finding ที่ขวาง · เสนอ coverage 2 จุด (ทำเป็น unit tests แล้ว) | – | 08:09–08:12 |
| dry-run tests ที่ล็อก (อ่านจากที่เดิม) กับร่างใน scratchpad | acceptance 6 passed, architecture 3 passed | ก่อนวางโค้ด | 08:1x |
| `uv run --offline pytest tests -q -p no:cacheprovider` หลังวางโค้ด | **PASS 68 passed, 0 skipped, 1.94 s** | commit ที่เพิ่มไฟล์นี้ | 08:29:05 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS exit 0 · "Type checks disabled": `type: ignore` 1 จุดใน unit test เชิงลบ (`HaltState(..., 0, False)` จงใจส่ง int แทน bool) + ข้อความเดิมในเอกสาร · "Lint disabled": คำในข้อความเอกสารเดิม · "Control files touched" แสดง `src/sochron/risk/policy.py` เพราะชื่อไฟล์มีคำว่า policy (heuristic ของสคริปต์ ไม่ใช่ path ที่ล็อก; Tier High เจ้าของตรวจอยู่แล้ว) · กลุ่ม secret และ order/account mutation ว่าง | เดียวกัน | 08:29:17 |
| `git diff --check` · `git diff 831fa60 -- tests/acceptance tests/golden tests/architecture` | PASS · ว่าง | เดียวกัน | 08:29:17 |

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- Linux/CI: ยังไม่มี Python job ใน CI ผลทั้งหมดมาจาก Windows
- การยืนยันตัวตนผู้ปลด halt, การบันทึก/กู้ HaltState จาก journal และการผูกผล gate กับคำสั่งจริง เป็นงานของ E1 (ระบุใน contract)
- review tests-r1 F5: architecture checker (สืบจาก CORE-001) ไม่จับ `time.localtime()`, `os.urandom()`, `uuid.uuid4()`, `subprocess`, `sys.stdout.write` → โค้ด risk ไม่ใช้สิ่งเหล่านี้ (ตรวจด้วยตา) · การเสริม checker เป็นงานของ test author (เสนอใน follow-up)
- ยังไม่ผ่าน security-reviewer และ Codex cross-agent review ของ implementation (ขั้นถัดไปตาม Tier High) · เจ้าของยังไม่ได้รัน demo
