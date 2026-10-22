# หลักฐาน CORE-002: `sochron.costs`

Contract: `docs/contracts/CORE-002-costs.md` v1.2 (อนุมัติโดยมอบอำนาจ 2026-10-21 20:2x · contract reviews r1–r3 ปิด F1–F7) · Branch `feat/CORE-002-costs` · ไฟล์นี้ถูกเพิ่มใน commit เดียวกับ implementation (ดู `git log` ของ branch)

## สรุปสำหรับเจ้าของ

| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 spread, fallback, stress, tick value | **PASS** | `test_ac01_spread_fallback_points_and_decimal_context` (รันใต้ context ของผู้เรียกที่ precision 4 + traps): 0.48 / 0.48 / 0.96 / 0.1 |
| AC-02 slippage, commission, model สมมติ 3.5 USD, sides | **PASS** | `test_ac02_slippage_commission_sides_and_stress`: 0.20 / 0.40 / 0 / 0 · 10.5 → 21.0 เมื่อ stress · sides 0 → 0 |
| AC-03 swap long/short, คืนคิด 3 เท่า, swap บวก | **PASS** | `test_ac03_swap_debits_credits_and_triple_counts`: 1.0076 / 9.0684 / 0 · stress 2.0152 / 18.1368 / 0 · +100 points → −0.20 / −0.40 |
| AC-04 รอบเทรดตัวอย่าง H001 | **PASS** | `test_ac04_round_trip_selection_breakdown_order_and_r`: total 1.6876 = 0.067504 R · sides 0 → 1.4876 · short ใช้ spread แท่งออก 0.68 · stress 3.3752 · ลำดับการบวกตาม context |
| AC-05 ปฏิเสธ input ผิด | **PASS** | `test_ac05_reject_invalid_types_domains_and_zero_branch_bypasses`: `TypeError` (float, bool, str, Decimal ในตำแหน่ง int) และ `CostsError` family ทุกแถวของตาราง "ชนิด โดเมน และ error" รวมตรวจ lots แม้ sides 0 และตรวจ spread ทั้งสองฝั่ง |
| AC-06 provenance 11 keys, unknowns, immutable | **PASS** | `test_ac06_h001_provenance_unknowns_frozen_and_stress_copy`: ค่า/สถานะ/วันที่ทั้ง 11 ฟิลด์ตรงตาราง · unknowns = commission, slippage, triple_swap_weekday · note ของ swap มี UNKNOWN · สำเนา provenance แยกจาก dict ต้นทาง · frozen ทั้ง 3 ชนิด |
| AC-07 ขอบเขต import, ไม่มี float/random, red-flags | **PASS** | `test_ac07_costs_import_boundaries_no_clock_io_random_or_float` (AST: stdlib + `sochron.core` เท่านั้น, ไม่มีชื่อ `float`/float literal/`random`) · red-flags: กลุ่ม secret และ order/account mutation ว่าง (ตาราง checks) |

ทั้ง 7 ข้อผ่านพร้อมกันในรันเดียว: **41 passed, 0 skipped** (CORE-001 เดิม 24 + acceptance 6 + architecture 1 + unit 10) ที่ 21:30:31 หลังแก้จุดเดียวจากรันแรก (40 passed, 1 failed: `spread_points` ต้องรับเฉพาะ `int | None`; Decimal → `TypeError` ตามตาราง)

## สิ่งที่ส่งมอบ

| ไฟล์ | หน้าที่ |
|------|---------|
| `src/sochron/costs/model.py` | `Provenance`, `CostModel` (frozen; ตรวจชนิดและโดเมนทุกฟิลด์ตอนสร้าง; provenance 11 keys เก็บเป็นสำเนา immutable), `stress()`, `unknowns()`, `H001_COSTS`, `CONTEXT` (precision 28, `ROUND_HALF_EVEN`) |
| `src/sochron/costs/charges.py` | `check_volume`, `points_to_money`, `spread_charge`, `slippage_charge`, `commission_charge`, `swap_charge`, `round_trip_cost` (`CostBreakdown`), `r_multiple` · ทุกฟังก์ชันคำนวณใน `localcontext(CONTEXT)` ตามลำดับที่ API block ของ contract เขียน |
| `src/sochron/costs/errors.py` | `CostsError(ValueError)` และ 7 ชนิดย่อย (`BadProvenance`, `BadStress`, `BadVolume`, `BadPoints`, `BadSides`, `BadNights`, `BadR`) |
| `src/sochron/costs/__init__.py` | re-export ตาม API block (เพิ่ม `CONTEXT`, `PROVENANCE_FIELDS`, `STATUSES` เป็นส่วนเสริม) |
| `tests/unit/costs/test_costs_unit.py` | unit tests ของผู้ทำ 10 ข้อ: context ของผู้เรียกไม่กระทบ, การหารปัดที่ 28 หลัก, ไม่มี −0, points มีเครื่องหมายได้แต่ spread ไม่, `check_volume` เทียบเชิงตัวเลขทุก exponent, provenance แยกสำเนาและอ่านอย่างเดียว, `replace()` ตรวจซ้ำ, stress สะสม, unknowns ตาม status, note ของ H001 |

การตัดสินระหว่างทำ:
- เลขเงินทั้งหมดเป็น `Decimal` ใน context ของโมดูลเองที่สร้างใหม่ (`Context(prec=28, rounding=ROUND_HALF_EVEN)`, ไม่ copy ของผู้เรียก จึงไม่รับ traps ของผู้เรียกมาด้วย) ปัดหลังแต่ละ operation ตามลำดับที่ contract เขียน (contract review F1): ตัวอย่าง 12.345678 ของผู้ตรวจให้ค่าตรงกันทุกหลัก
- `swap_charge` คืน `0 − charge` เพื่อไม่ให้เกิด −0 · `points_to_money` รับ points มีเครื่องหมาย (swap ต้องใช้) แต่ spread/slippage/commission ติดลบถูกปฏิเสธ · `spread_points` ของแท่งเป็น `int | None` เท่านั้น
- ไม่แตะ `core` และ `timebase` · การนับคืนจากเวลาและ PnL เป็นของ contract ถัดไป (rollover ของโบรกเกอร์ยัง UNKNOWN)

## Demo สำหรับเจ้าของ (รันเองได้ใน 1 นาที, Git Bash ที่ root ของ repo)

1. ชุดทดสอบทั้งหมด: `uv run --offline pytest tests -q -p no:cacheprovider` → ต้องได้ `41 passed` และไม่มี skipped
2. worked example ของ H001 ข้อ 3 (lots 0.02, spread 240, ถือ 1 คืน):
   ```bash
   PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from sochron.costs import H001_COSTS, round_trip_cost, r_multiple, stress, unknowns; b = round_trip_cost('long', D('0.02'), 240, 240, 1, 0, H001_COSTS); print(b); print('R', r_multiple(b.total, D('25'))); print('stress x2 total', round_trip_cost('long', D('0.02'), 240, 240, 1, 0, stress(H001_COSTS)).total); print('assumed:', unknowns(H001_COSTS))"
   ```
   ผลที่ต้องได้ (รันจริง 2026-10-21 21:3x บน branch นี้):
   ```text
   CostBreakdown(spread=Decimal('0.48000'), commission=Decimal('0.00'), slippage=Decimal('0.20000'), swap=Decimal('1.007600'), total=Decimal('1.687600'), stress_factor=Decimal('1'))
   R 0.067504
   stress x2 total 3.375200
   assumed: ('commission_per_lot_per_side', 'slippage_points_per_side', 'triple_swap_weekday')
   ```
   (ตรงกับ H001: spread 0.24 USD/oz × 100 × 0.02 = 0.48; swap 503.8 × 0.001 × 100 × 0.02 = 1.0076 ≈ 1.01 ที่ H001 ปัดไว้)
3. ปฏิเสธ volume ที่ไม่ตรง step: `PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from sochron.costs import H001_COSTS, check_volume; check_volume(D('0.015'), H001_COSTS)"` → บรรทัดสุดท้ายต้องเป็น `sochron.costs.errors.BadVolume: lots 0.015 is not a multiple of 0.01`

## Checks (2026-10-21, +07, Windows 11, Python 3.12.15 ผ่าน uv 0.13.0)

| Command | ผล | Commit | เวลา |
|---------|-----|--------|------|
| Codex contract review r1/r2/r3 (`docs/reviews/CORE-002-contract-r*.md`) | F1–F7 → แก้ใน v1.1/v1.2 → r3: ready for test authoring | `5bce19b`, `c8e3793`, `53f1218` | 20:3x–21:00 |
| Codex tests patch `docs/proposals/CORE-002-tests.patch` (SHA256 `15241d09…`) → `git apply` standalone → SHA256/blob 3 ไฟล์ตรง handoff → `git apply -R --check` | PASS ทุกค่า | `dced669` | 21:17:58 |
| fresh-session review ของ tests (`docs/reviews/CORE-002-tests-r1.md`) รวม `uv run --offline pytest tests -q -p no:cacheprovider` ก่อนมีโค้ด | ready to commit red · **7 failed (ตามคาด), 24 passed** | `dced669` | 21:21:59 |
| `uv run --offline pytest tests -q -p no:cacheprovider` หลังวางโค้ด (รันแรก) | FAIL 1: AC-05 `spread_charge(Decimal("240"))` ต้องเป็น `TypeError` → แก้ `_spread_points` | ก่อน commit implementation | 21:29:21 |
| `uv run --offline pytest tests -q -p no:cacheprovider` หลังแก้ | **PASS 41 passed, 0 skipped, 0.08 s** | commit ที่เพิ่มไฟล์นี้ | 21:30:31 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS exit 0 · 2 กลุ่ม hit: "Type checks disabled" = `type: ignore` ใน unit test เชิงลบ (ตั้งใจ แบบเดียวกับ CORE-001) + ข้อความอ้างถึงใน review/compatibility · "Lint disabled" = คำว่า `noqa` ในข้อความของ review/PROGRESS/evidence ที่อธิบายสิ่งที่ grep หา ไม่ใช่โค้ด · กลุ่ม "Placeholder or mock" เคย hit จากคำว่า placeholders ใน docstring ของ `model.py` → เปลี่ยนคำเป็น assumptions แล้ว (2026-10-22) · กลุ่ม secret และ order/account mutation ว่าง | เดียวกัน | 21:30:3x, 06:1x |
| review r1 (checkpoint ของ Codex) F1–F3 → แก้ทีละ commit · regression fail ก่อน/pass หลัง | `7562246`, `c97befb`, `f7b88f5` · suite **44 passed, 0 skipped** | ดู handoff "Findings response" | 2026-10-22 06:14–06:17 |
| Codex review r2 ฉบับเต็ม (`docs/reviews/CORE-002-r2.md`): ปิด F1–F3, oracle 22,126 ค่า, hash tests ที่ล็อกตรง · พบ F4 Low (context ของผู้เรียกใน `CostBreakdown`) → แก้ | `cec0f4b` · suite **45 passed, 0 skipped** (06:27:55) | ดู handoff "Findings response, review r2" | 2026-10-22 06:19–06:28 |
| `git diff --check` · `git diff dced669 HEAD -- tests/acceptance tests/golden tests/architecture` | PASS · ว่าง (tests ที่ล็อกไม่ถูกแตะหลัง commit red) | เดียวกัน | 21:30:3x |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL ตามคาด: AGENTS.md/CLAUDE.md (จาก chore branch) และ tests ที่ล็อก 3 ไฟล์ของ Codex ต้องมี label ตอน PR | เดียวกัน | 21:30:3x |

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- Linux/CI: ยังไม่มี Python job ใน CI (control change แยก) ผลทั้งหมดมาจาก Windows
- การนับคืน swap และคืนที่คิด 3 เท่าจากเวลาจริง (rollover ของโบรกเกอร์ UNKNOWN) อยู่นอก scope; จำนวนคืนเป็น input
- PnL จากราคาและการเชื่อม journal อยู่ใน contract ถัดไป · swap ย้อนหลัง 2018–2024 เป็น UNKNOWN โดยนิยาม (note ใน provenance)
- การคูณหลายชั้นอาจปัดที่ 28 หลัก (contract v1.2) ไม่กระทบค่าใน acceptance ซึ่งเป็นค่าสั้น
- Codex cross-agent review ครบแล้ว: r1 (checkpoint) F1–F3 → แก้ · r2 ฉบับเต็ม ปิด F1–F3 พบ F4 → แก้ · r3 ปิด F4, findings open 0, AC-01–07 PASS (45 passed) · เจ้าของยังไม่ได้รัน demo เอง

## Finding ของ review tests-r1 (Low question 3 ข้อ)
- F1 architecture test ห้ามชื่อ `float` ทุกรูปแบบ (เข้มกว่าตัวอักษรของ contract) → implementation ใช้ positive type checks (`isinstance(x, Decimal)`, `isinstance(x, int) and not isinstance(x, bool)`) ไม่มีชื่อ `float` ในโค้ด
- F2 golden มีแถวเพิ่มจากตัวอักษรของ AC (แถวปัดเศษ 29 หลัก, fixture `ORDERED_TOTAL`, แถวขอบ) ทุกแถวคำนวณตรงสูตร normative ของ contract → ผ่านทั้งหมด
- F3 AC-01 รันใต้ context ของผู้เรียกที่เปิด traps Inexact/Rounded → โมดูลสร้าง `Context` ใหม่ ไม่ copy ของผู้เรียก จึงไม่ติด trap
