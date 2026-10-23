# หลักฐาน CORE-004: `sochron.costs` ปฏิเสธ input ผิดแบบเดียวกับ `sochron.risk`

Contract: `docs/contracts/CORE-004-costs-hardening.md` v1.2 (Tier Standard; เจ้าของอนุมัติ 2026-10-22 23:4x, v1.1 18:3x, v1.2 ตอบระหว่าง 19:2x–20:1x) · Branch `fix/CORE-004-costs-hardening` (ต่อจาก FIX-001 ที่ merge แล้ว) · การสลับบทบาท: ผู้เขียน tests 2 session และผู้ตรวจ 2 session เป็น Claude session ใหม่ คนละ session กับผู้ทำ (Codex หมดโควตาถึง 2026-10-28 19:41) · รายละเอียด tests: `docs/handoff/CORE-004.md`

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 subclass ทุกตำแหน่ง → `TypeError` | **PASS** | tests ล็อก AC-01 (559 แถว) เขียว · ก่อนแก้ล้มทั้งหมด |
| AC-02 provenance อ่านครั้งเดียว เก็บเป็นสำเนา, key ต้องเป็น `str` พอดี | **PASS** | tests ล็อก AC-02 เขียว (เดิม custom Mapping ถูกอ่าน 3 รอบ) |
| AC-03 model ที่ถูกแก้หลังสร้าง → error เดียวกับตอนสร้างทุกฟังก์ชัน | **PASS** | tests ล็อก AC-03 เขียว: `-k ac03` เก็บได้ 917 แถว รวม 18 แถวของ `test_ac02_ac03_*` (นับเฉพาะ `test_ac03_*` = 899; เดิมเขียน 840 ผิด, review r2 F8) · ทุกแถวของ AC: `-k ac01` 559, `ac02` 41, `ac04` 454, `ac05` 1, `ac06` 42 จาก 1,993 |
| AC-04 Decimal เกินเพดาน → error ของช่องนั้นภายใน 1 วินาที, ค่าที่ขอบรับได้ | **PASS** | tests ล็อก AC-04 รวมรอบ 2 (F2 ทีละ field ของ `CostBreakdown`, F3 `volume_step` เลขชี้กำลังบวก) เขียว · การปฏิเสธที่ช้าที่สุดราว 3.5 ms · 2 tests ที่เคยค้างจนถูก watchdog ฆ่าตอนนี้ผ่านในไม่กี่ ms |
| AC-05 ผลของ input ที่ถูกต้องไม่เปลี่ยน, tests เดิมผ่าน | **PASS** | suite **2788 passed**, skipped 0 · `git diff origin/main` ของ tests ล็อก CORE-002/003 ว่าง · ผู้ตรวจ r1 เทียบโค้ดเก่ากับใหม่บน model สุ่ม 3,000 ชุด × caller context 3 แบบ × 11 ฟังก์ชัน: ผล, ชนิด error และ context ของผู้เรียกตรงกันทุกหลัก · แก้ unit test ของ risk 3 บรรทัดตามที่เจ้าของอนุมัติ (v1.1 F1) |
| AC-06 int ยักษ์ผิดโดเมน → error ของช่องนั้น ไม่ใช่ `ValueError` | **PASS** | tests ล็อก AC-06 เขียว · ข้อความ error ไม่ format ค่า int อีก |

## สิ่งที่เปลี่ยน (พฤติกรรม)
- `Provenance` และ `CostModel` รับเฉพาะชนิดพอดี และสร้าง subclass ไม่ได้
- provenance ถูกอ่านครั้งเดียว (หนึ่ง traversal) ก่อน field อื่น เก็บเป็น `MappingProxyType` ของสำเนา
- ทุกฟังก์ชันสาธารณะตรวจ model ซ้ำครั้งเดียวก่อนตรวจ argument · helper ภายในรับค่าที่ตรวจแล้ว · `stress()` สร้างผลจาก snapshot ที่ตรวจแล้ว
- Decimal ทุกช่องติดเพดาน 1,000 หลัก และ |adjusted| ≤ 1,100,000 (ค่าเดียวกับ risk) ตรวจก่อนแปลงเป็นตรรกยะ · int ไม่ติดเพดาน เพราะ contract คุมขนาดเฉพาะ Decimal และ int แปลงตรงโดยไม่ผ่านการแปลงเป็นตรรกยะ (unit test ของผู้ทำ) · แต่ int ในโดเมนที่ใหญ่ระดับล้านหลักยังช้าราว 13–15 วินาทีต่อการเรียก เหมือนบน main ก่อนงานนี้ ซึ่งเจ้าของรับเป็นข้อจำกัด (r1 F5; เดิมเขียนว่า "ไม่ช้า" ผิด, review r2 F8)
- ข้อความ error ไม่พิมพ์ค่าที่อาจใหญ่
- หลัง review r1: อ่าน attribute `provenance` ครั้งเดียวต่อการตรวจ (F1) และตรวจ field ของทุก Provenance record ซ้ำตอนใช้ (F3) · status ที่ไม่ใช่ `str` เป็น `TypeError` (F4 ตามที่เจ้าของรับ)

## สิ่งที่ส่งมอบ (ไฟล์)
- `src/sochron/costs/model.py`, `src/sochron/costs/charges.py`: การตรวจชนิดพอดี, provenance อ่านครั้งเดียว, ตรวจซ้ำตอนใช้, เพดานขนาด Decimal
- `tests/acceptance/CORE-004/test_costs_hardening.py` (ล็อก, ผู้เขียน tests 2 รอบผ่าน patch D-006)
- `tests/unit/costs/test_costs_unit.py`: unit tests ของผู้ทำ (int ไม่ติดเพดาน, snapshot แยกต่อครั้ง, F1, F3/F7)
- `tests/unit/risk/test_risk_unit.py` บรรทัด 252–257: แอบใส่ subclass หลังสร้าง (tests-r1 F1, เจ้าของอนุมัติ)
- `docs/contracts/CORE-004-costs-hardening.md` v1.2 · `docs/handoff/CORE-004.md` · `docs/reviews/CORE-004-tests-r1.md`, `CORE-004-r1.md`, `CORE-004-r2.md` · ไฟล์นี้

## Demo สำหรับเจ้าของ (Git Bash ที่ root ของ repo; เจ้าของเลือก 2026-10-24 ให้ Claude รันให้)
1. ชุดทดสอบทั้งหมด: `uv run --offline pytest tests -q -p no:cacheprovider` → ต้องได้ `2795 passed` และไม่มี skipped
2. ค่าปกติยังได้ผลเดิม (ตัวอย่างไม้ 0.02 lot ถือ 1 คืนของ H001) และรายชื่อค่าที่ยังเป็นสมมติฐาน:
   ```bash
   PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from sochron.costs import H001_COSTS, round_trip_cost, unknowns; print(round_trip_cost('long', D('0.02'), 240, 240, 1, 0, H001_COSTS)); print(unknowns(H001_COSTS))"
   ```
   ผลที่ต้องได้:
   ```text
   CostBreakdown(spread=Decimal('0.48000'), commission=Decimal('0.00'), slippage=Decimal('0.20000'), swap=Decimal('1.007600'), total=Decimal('1.687600'), stress_factor=Decimal('1'))
   ('commission_per_lot_per_side', 'slippage_points_per_side', 'triple_swap_weekday')
   ```
3. input ผิดถูกปฏิเสธทันที (subclass, ตัวเลข 1,001 หลัก, เลขชี้กำลังเกินเพดาน):
   ```bash
   PYTHONPATH=src uv run --offline python -c "from decimal import Decimal as D; from time import perf_counter as t; from sochron.costs import H001_COSTS, check_volume; Sub = type('Sub', (D,), {}); tries = [('subclass', Sub('0.02')), ('1001 digits', D('0.02' + '0' * 1000)), ('exponent', D('1E-1100001'))]
   for name, lots in tries:
       s = t()
       try: check_volume(lots, H001_COSTS)
       except Exception as e: print(name, '->', type(e).__name__, f'{(t() - s) * 1000:.1f} ms')"
   ```
   ผลที่ต้องได้: `subclass -> TypeError`, `1001 digits -> BadVolume`, `exponent -> BadVolume` แต่ละบรรทัดใช้เวลาไม่ถึง 1,000 ms

ผลที่ Claude รัน (2026-10-24 02:0x, commit ก่อน F7–F9 + การแก้ใน working tree): ขั้น 1 `2795 passed in 5.93s` · ขั้น 2 ตรงตามที่เขียนทุกตัวอักษร · ขั้น 3 `subclass -> TypeError 0.0 ms`, `1001 digits -> BadVolume 0.0 ms`, `exponent -> BadVolume 0.0 ms`

## Delivery state
implemented และ verified ในเครื่อง (2795 passed) · reviews: tests-r1, r1, r2 (F1–F6 ปิด; F7–F9 ตอบแล้ว รอ subagent ตรวจซ้ำตามที่เจ้าของเลือก) · ยังไม่ merged, ไม่ deployed · CI รอ run ของ PR

## Review r1 (`docs/reviews/CORE-004-r1.md`) และการตอบ
| ID | ผล | การตอบ | Regression |
|----|----|--------|------------|
| F1 Low | ยืนยัน: `_check_model` อ่าน `model.provenance` สองครั้ง object ที่แอบใส่ไว้สลับค่าระหว่าง `isinstance` ได้ | แก้ `f627350` | `test_provenance_attribute_is_read_once_per_check` ล้มก่อน (การเรียกคืนค่า) ผ่านหลัง |
| F2 Low | ยืนยัน: ไม่มีหลักฐานของผู้ทำ | ไฟล์นี้ + หัวข้อ implementer ใน handoff | – |
| F3 Low คำถาม | record ที่ถูกแก้หลังสร้างไม่ถูกตรวจตอนใช้ | เจ้าของ: แก้ → `d33d5da` | `test_provenance_records_are_checked_again_at_use` 3 กรณี ล้มก่อน ผ่านหลัง |
| F4 Low คำถาม | status ที่ไม่ใช่ str ได้ `TypeError` แทน `BadProvenance` | เจ้าของ: รับ เขียนใน contract v1.2 | – |
| F5 Low คำถาม | int ล้านหลักทำให้ช้า ~15 วินาที (มีอยู่แล้วบน main) | เจ้าของ: ข้อจำกัด (contract v1.2) | – |
| F6 Low คำถาม | metaclass ประหลาดเลือกชนิด error ตอนถูกปฏิเสธ | เจ้าของ: ข้อจำกัด (contract v1.2) | – |

หมายเหตุ: commit message ของ `d33d5da` เขียนเวลาที่เจ้าของตอบเป็น "19:2x" ซึ่งไม่แน่นอน เวลาจริงอยู่ระหว่าง 19:2x–20:1x (หลัง commit `0c0a5b0` 19:19 และก่อน `f627350` 20:12)

## Review r2 (`docs/reviews/CORE-004-r2.md`) และการตอบ
r2 ปิด F1–F6 ทั้งหมด (regression ของ F1/F3 ล้มบน commit แม่และผ่านที่ HEAD · เทียบโค้ด 3,000 model สุ่มกับ origin/main, `5f7a382` และ `f627350` ตรงกัน · F3 เพิ่มเวลาราว 2 µs ต่อการตรวจ model) และพบ Low F7–F9:
| ID | การตอบ | หลักฐาน |
|----|--------|---------|
| F7 | เพิ่ม 7 แถวใน `test_provenance_records_are_checked_again_at_use` ให้ครอบ `source`, `note`, `as_of` (ไม่ใช่แค่ `status`) | กับ mutant ที่ตรวจซ้ำเฉพาะ `status` (สำเนาใน scratch, ไม่แตะ `src/`): แถวใหม่ล้ม 7/7 · แถว `status` 3 แถวผ่านตามคาด · กับโค้ดจริง 10/10 ผ่าน |
| F8 | แก้ 2 บรรทัดในไฟล์นี้: จำนวนแถว AC-03 (วัดใหม่ด้วย `--collect-only -k`) และประโยค "int ไม่ช้า" ที่ขัดกับ F5 | ตาราง "สรุปสำหรับเจ้าของ" และ "สิ่งที่เปลี่ยน" |
| F9 | เจ้าของเลือก 2026-10-24: เพิ่ม demo สั้นๆ ให้ Claude รัน + รายการไฟล์ + delivery state | หัวข้อ "สิ่งที่ส่งมอบ", "Demo สำหรับเจ้าของ", "Delivery state" |
การตรวจซ้ำ F7–F9: เจ้าของเลือกให้ subagent `fresh-eyes-reviewer` ตรวจแคบๆ เพราะ headless session ครบงบ 6 ของ contract แล้ว

## Checks (2026-10-23, +07, Windows 11, Git Bash, uv 0.13.0, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| `git apply --check` / `git apply` / `git apply -R --check docs/proposals/CORE-004-tests.patch` (แยกคำสั่ง) | PASS · detector รายงานไฟล์เดียว · SHA256 `0d75e147…` blob `e74213c2…` ตรง handoff | 82a7f3e | 15:29 |
| red: `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider --tb=no -k "not huge_on_grid_lots and not extreme_exponent_volume_step"` | 1808 failed, 949 passed, 2 deselected (ตรง handoff) | 82a7f3e + patch | 15:29:35–49 |
| fresh review tests r1 (`docs/reviews/CORE-004-tests-r1.md`) | ready to commit red · F1 Medium (คำถาม), F2/F3 Low · รอบแรกชนเพดานโควตา 15:50 รันใหม่ 18:05 | – | 18:05–18:33 |
| commit red | `594388d` | – | 18:33 |
| implement → `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | 2759 passed → เพิ่ม unit tests → **2761 passed** | 5f7a382 | 18:36–18:37 |
| tests r2: `git apply --check` / `git apply` / `git apply -R --check docs/proposals/CORE-004-tests-r2.patch` (แยกคำสั่ง) | PASS · detector รายงานไฟล์เดียว · SHA256 `4d79519f…` blob `cc64a073…` ตรง handoff | 5f7a382 | 18:56 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | **2784 passed in 8.50s** | 5f7a382 + r2 | 18:56:27 |
| `bash scripts/controls/red-flags.sh origin/main` | 1 กลุ่ม (Type checks disabled): คำว่า "as any valid value" ใน docstring ของ test ไม่ใช่โค้ด | 5f7a382 + r2 | 18:56 |
| fresh review r1 (`docs/reviews/CORE-004-r1.md`) | Part A tests r2 ready to commit · Part B ไม่มี blocker, Low F1–F6 · `2784 passed` | 5f7a382 + r2 | 18:57–19:19 |
| commit tests r2 | `0c0a5b0` | – | 19:19 |
| F1: regression ล้มก่อนแก้ → แก้ → suite | `1 failed` → `1 passed` → **2785 passed** | f627350 | 20:1x |
| F3: regression ล้มก่อนแก้ → แก้ → suite | `3 failed` → `3 passed` → **2788 passed** | d33d5da | 20:1x |

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- CI บน Linux จนกว่า PR จะรัน · เวลาที่วัดได้มาจากเครื่องนี้ (contract ระบุเป็นเครื่องอ้างอิง)
- ค่าในขอบเพดานที่ยังช้าได้ (เช่น grid ของ `volume_step` 1E-1100000) ยอมรับไว้แบบเดียวกับ risk · E1 ต้องสร้าง model จาก `symbol_info` แล้วตรวจ (CORE-003 E1 L3)
- ไม่กันโค้ดร้ายที่รันใน process เดียวกัน (ขอบเขต CORE-003 v1.7, E1 L2)
