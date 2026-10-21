# หลักฐาน CORE-001: `sochron.timebase`

Contract: `docs/contracts/CORE-001-timebase.md` (เจ้าของอนุมัติ 2026-10-21) · Branch `feat/CORE-001-timebase` · ไฟล์นี้ถูกเพิ่มใน commit เดียวกับ implementation (ดู `git log` ของ branch)

## สรุปสำหรับเจ้าของ

| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 raw ↔ UTC round trip | **PASS** | `test_ac01_raw_utc_milliseconds_and_fixed_round_trips`: ค่าจริงจาก SPIKE-001 (`1792525992` / msc `…035`) → `2026-10-20 19:53:12.035+00:00` และกลับมาเท่าเดิม · 23 ค่าคงที่ตั้งแต่ 2000-01-01 ถึง 2099-12-31 23:59:59 · กฎสมมติ offset ±7200 |
| AC-02 หน้าต่าง New York ข้าม DST | **PASS** | `test_ac02_new_york_window_across_both_dst_changes`: 32 แถวรอบ 08 มี.ค. และ 01 พ.ย. 2026 รวมขอบ 02:59:59 / 03:00:00 / 15:59:59 / 16:00:00 และนาทีที่ซ้ำตอน fall-back |
| AC-03 วันเทรดแบบไทย | **PASS** | `test_ac03_bangkok_calendar_day_changes_at_1700_utc`: 16:59:59 UTC → 20 ต.ค., 17:00:00 UTC → 21 ต.ค. |
| AC-04 จัดแท่ง M1 → M15 | **PASS** | `test_ac04_m1_and_tick_alignment_to_m15`: M1 15 แท่ง, tick, ขอบ 19:45/20:00, ทุก timeframe ทั้ง 19 ค่า, กฎ offset 61 วินาที, timeframe 7 และ 1441 → `BadTimeframe` |
| AC-05 ปฏิเสธ input ที่ไม่ถูกต้อง | **PASS** | `test_ac05_reject_unknown_naive_out_of_range_and_mismatched_input`: `UnknownTimeRule`, `NaiveDatetime` ×4 ฟังก์ชัน, `RawTimeOutOfRange` ×4 ค่า ×2 ฟังก์ชัน, `RawTimeMismatch` ×2 |
| AC-06 จำแนก offset โดยไม่แก้กฎ | **PASS** | `test_ac06_classify_offsets_without_mutating_time_rules`: 10 ชุดตัวอย่าง (ok / shifted ±2 h / unknown) และ `RULES`, `TimeRule`, `EntryWindow`, `OffsetClass` แก้ค่าไม่ได้ (`FrozenInstanceError`) |
| AC-07 ขอบเขต import, ไม่มีนาฬิกา/I/O, red-flags | **PASS** | `test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io` (AST) ผ่าน · red-flag scan: กลุ่ม secret และ order/account mutation ว่าง (ดูตาราง checks) |

ทั้ง 7 ข้อผ่านพร้อมกันในรันเดียว: **19 passed, 0 skipped** (acceptance 6, architecture 1, unit 12) ที่ `5546da0` · หลังแก้ตาม Codex review r1 (F1–F3): **22 passed, 0 skipped** (unit 15) ที่ `0b8475d` 08:44:41 · หลังแก้ตาม r2 (F4–F5): **24 passed, 0 skipped** (unit 17) ที่ `0e80263` 08:57:20 · Codex r3 (19:15) ยืนยัน 24 passed และปิด F4–F5 ไม่มี finding ค้าง

## สิ่งที่ส่งมอบ

| ไฟล์ | หน้าที่ |
|------|---------|
| `src/sochron/timebase/rules.py` | `TimeRule` (frozen) และ `RULES` แบบอ่านอย่างเดียว มีรายการเดียวคือ `Exness-MT5Trial14` offset 0, build 6274, หลักฐาน SPIKE-001 · `rule_for` ปฏิเสธ server ที่ไม่มีกฎ |
| `src/sochron/timebase/convert.py` | `to_utc`, `to_raw` (เลขจำนวนเต็มล้วน ไม่ใช้ float), `to_zone`, `bar_open`, `TIMEFRAMES_MINUTES`, ช่วง raw ที่รับ `[946684800, 4102444800)` |
| `src/sochron/timebase/sessions.py` | `EntryWindow`, `NY_ENTRY_WINDOW` (03:00–15:59 America/New_York), `in_entry_window` (ความละเอียดนาที), `bangkok_date` |
| `src/sochron/timebase/offset.py` | `OffsetClass`, `classify_offset` (รายงานอย่างเดียว ไม่มีเส้นทางแก้กฎ) |
| `src/sochron/timebase/errors.py` | `TimebaseError(ValueError)` และ 5 ชนิดย่อยตาม contract |
| `src/sochron/__init__.py`, `src/sochron/core/__init__.py` | docstring เท่านั้น (ตาม review tests-r1 F3) |
| `tests/unit/timebase/test_timebase_unit.py` | unit tests ของผู้ทำ 17 ข้อ (ขอบช่วง raw, float/bool ถูกปฏิเสธ, to_raw จาก zone อื่น, bar_open idempotent ทุก timeframe, กฎ offset ไม่ใช่ 0, ตัวอย่าง offset จริงจาก SPIKE-001, regression ของ review r1: ชั่วโมงร่วมที่ tolerance กว้าง, NaN/inf → unknown, วินาทีในขอบ window, และของ r2: ค่า finite ขนาดสุดขีดไม่ raise, ชั่วโมงเกิน 2^53 ยังนับถูก) |
| `pyproject.toml`, `uv.lock` | environment ตาม D-012 (commit `3da18d1`) |

การตัดสินใจระหว่างทำ:
- การแปลงเวลาใช้เลขจำนวนเต็มกับ `timedelta` ทั้งหมด ไม่ผ่าน `timestamp()` ที่เป็น float เพื่อให้ round trip ตรงทุกค่า
- `check_aware` เป็น public helper ให้โมดูลอื่นใช้ปฏิเสธ naive datetime แบบเดียวกัน
- `bar_open` หาร floor บน "วินาที UTC" แล้วบวก offset กลับ ตามสูตรใน contract (ทดสอบด้วย offset 61 และ 3600)
- ไม่มีการอ่านนาฬิกา ไม่มี I/O และไม่มี `MetaTrader5` ในแพ็กเกจ (AST test + ตรวจด้วยตา)

## Demo สำหรับเจ้าของ (รันเองได้ใน 1 นาที, Git Bash ที่ root ของ repo)

1. ชุดทดสอบทั้งหมด: `uv run --offline pytest tests -q -p no:cacheprovider` → ต้องได้ `24 passed` และไม่มี skipped
2. ใช้งานจริงกับค่า tick ของ SPIKE-001 (`1792525992` / msc `…035`):
   ```bash
   PYTHONPATH=src uv run --offline python -c "from sochron.timebase import rule_for, to_utc, to_raw, in_entry_window, bangkok_date, bar_open, classify_offset; r = rule_for('Exness-MT5Trial14'); dt = to_utc(1792525992, r, msc=1792525992035); print('utc', dt); print('raw back', to_raw(dt, r)); print('in NY window', in_entry_window(dt)); print('bangkok date', bangkok_date(dt)); print('M15 open', bar_open(1792525992, 15, r)); print(classify_offset([-0.246, 0.268, 0.306])); print(classify_offset([7080.0, 7200.0, 7320.0]))"
   ```
   ผลที่ต้องได้ (รันจริง 2026-10-21 19:19:30 บน `bf0d504`):
   ```text
   utc 2026-10-20 19:53:12.035000+00:00
   raw back 1792525992
   in NY window True          # 15:53 เวลา New York (EDT) อยู่ในหน้าต่าง 03:00–15:59
   bangkok date 2026-10-21    # 02:53 เวลาไทยของวันถัดไป
   M15 open 1792525500        # 19:45:00 UTC
   OffsetClass(kind='ok', hours=None, samples=3)
   OffsetClass(kind='shifted', hours=2, samples=3)
   ```
3. ปฏิเสธ server ที่ไม่มีกฎ: `PYTHONPATH=src uv run --offline python -c "from sochron.timebase import rule_for; rule_for('Other-Server')"` → บรรทัดสุดท้ายต้องเป็น `UnknownTimeRule: no measured time rule for server 'Other-Server'; measure it first (a SPIKE contract)`

## Checks (2026-10-21, +07, Windows 11, Python 3.12.15 ผ่าน uv 0.13.0, tzdata 2026e)

| Command | ผล | Commit | เวลา |
|---------|-----|--------|------|
| `uv run pytest tests -q -p no:cacheprovider` ก่อนมีโค้ด | FAIL ตามคาด: 7 failed (module missing) | `85d78bf` tests red + `3da18d1` env | 08:26:32 |
| `uv run python -c "import zoneinfo, tzdata; …"` | PASS: `America/New_York`, tzdata 2026e | `3da18d1` | 08:26:32 |
| `uv run pytest tests -q -p no:cacheprovider` หลังมีโค้ด | **PASS 19 passed, 0 skipped, 0.07 s** | commit ที่เพิ่มไฟล์นี้ | 08:29:35 |
| `git diff --cached --check` | PASS | `5546da0` | 08:31:22 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS exit 0 · 1 กลุ่ม (type-ignore 4 จุดใน unit test เชิงลบ ตั้งใจและอธิบายใน review r1) · กลุ่ม secret และ order/account mutation ว่าง | `5546da0` | 08:31:22 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL ตามคาด: tests ที่ล็อก 3 ไฟล์ของ Codex ต้องมี label ตอน PR | `5546da0` | 08:31:22 |
| Codex review r1: `uv run --offline pytest tests -q -p no:cacheprovider` ในเครื่อง Codex | PASS 19 passed, 0 skipped · hash tests ที่ล็อกตรง handoff และ `85d78bf` | `5546da0` | 08:32:24 |
| regression ของ review r1 ก่อนแก้ `uv run --offline pytest tests/unit/timebase/test_timebase_unit.py -q -p no:cacheprovider -k <F>` | FAIL ตามคาดทั้ง 3 ข้อ (F1 unknown แทน shifted · F2 `ValueError` · F3 นาทีแรกหลุด) | ก่อน `5538617` / `b8c993d` / `0b8475d` | 08:41:18 / 08:43:19 / 08:44:16 |
| `uv run --offline pytest tests -q -p no:cacheprovider` หลังแก้ F1–F3 | **PASS 22 passed, 0 skipped, 0.05 s** | `0b8475d` | 08:44:41 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS exit 0 · 1 กลุ่มเดิม (type-ignore) · กลุ่ม secret และ order/account mutation ว่าง | `0b8475d` | 08:45:34 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL ตามคาด: 3 ไฟล์เดิม ต้องมี label ตอน PR | `0b8475d` | 08:45:34 |
| `git diff --check origin/main..HEAD` · `git diff 85d78bf HEAD -- tests/acceptance tests/golden tests/architecture` | PASS · ว่าง (tests ที่ล็อกไม่ถูกแตะหลัง `85d78bf`) | `0b8475d` | 08:45:34 |
| Codex re-review r2: suite ในเครื่อง Codex | PASS 22 passed, 0 skipped · F1–F3 ปิด · พบ F4/F5 Low ใหม่ | `c751610` | 08:49:21 |
| regression F4/F5 ก่อนแก้ `uv run --offline pytest tests/unit/timebase/test_timebase_unit.py -q -p no:cacheprovider -k "extreme_finite or integer_hour_identity"` | FAIL ตามคาด (F4 `OverflowError` · F5 unknown แทน shifted) | ก่อน `0e80263` | 08:56:12 |
| `uv run --offline pytest tests -q -p no:cacheprovider` หลังแก้ F4/F5 | **PASS 24 passed, 0 skipped, 0.06 s** | `0e80263` | 08:57:20 |
| `bash scripts/controls/red-flags.sh origin/main` · locked diff หลัง `85d78bf` | PASS exit 0 · 1 กลุ่มเดิม (type-ignore) · ว่าง | `0e80263` | 08:57:21 |
| merge `origin/main` เข้า branch (เจ้าของอนุมัติ) แล้ว `uv run --offline pytest tests -q -p no:cacheprovider` · red-flags · `git diff --check origin/main...HEAD` | PASS 24 passed · 1 กลุ่มเดิม · PASS · conflict เฉพาะ PROGRESS.md แก้แล้ว ไม่มีโค้ดเปลี่ยน | `bf0d504` | 09:01:45 |
| Codex re-review r3: suite ในเครื่อง Codex + oracle จำนวนเต็ม 16,674 กรณี (`docs/reviews/CORE-001-r3.md`) | PASS 24 passed, 0 skipped · F4/F5 ปิด · ไม่มี finding ใหม่ · AC-01–07 PASS | `bf0d504` | 19:15:06–19:17:02 |
| Demo สำหรับเจ้าของ ข้อ 2–3 ด้านบน | PASS ผลตรงตามที่บันทึก · `UnknownTimeRule` สำหรับ server ที่ไม่มีกฎ | `bf0d504` | 19:19:30 |

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- Linux: ยังไม่มี Python job ใน CI (control change แยก) ผลทั้งหมดมาจาก Windows
- เวลาทำการของ `XAUUSDm` ไม่อยู่ในโมดูลนี้ (AC-03 ของ SPIKE-001 ยัง UNKNOWN ด้าน timezone)
- `to_zone` กับชื่อ zone ที่ไม่มีอยู่ปล่อย `ZoneInfoNotFoundError` ของ stdlib · `tolerance_seconds` ที่ไม่ finite หรือติดลบยังไม่มีพฤติกรรมกำหนดใน contract (ดู note ใน handoff)
- Codex review ครบ 3 รอบ: r1 พบ F1–F3 → แก้ → r2 ปิด F1–F3 และพบ F4–F5 → แก้ (`0e80263`) → r3 ปิด F4–F5 ไม่มี finding ค้าง · ที่เหลือเป็นมือเจ้าของ: เปิด PR, ติด label, merge
- การตัดสินที่ Claude รับมาตามที่เจ้าของอนุญาต (19:1x "ทำ phase นี้ให้จบ ตัดสินเอง"): คงนโยบาย F2 (NaN/inf → unknown) · tolerance ที่ไม่ finite/ติดลบ และชื่อ zone ที่ไม่มี ไม่เพิ่ม error ใหม่ในรุ่นนี้ บันทึกเป็น follow-up ของ contract timebase ถัดไป

## Finding ของ review r1 (implementation, `docs/reviews/CORE-001-r1.md`)
- F1 Medium (รับ, `5538617`): `classify_offset` ปัดชั่วโมงทีละค่าแยกกัน ทำให้ `[1800, 5400]` ที่ tolerance 1800 ได้ unknown แทน shifted 1 ชั่วโมง → เปลี่ยนเป็นหา "ชั่วโมงเต็มที่เข้ากับทุกค่า": เข้าพอดี 1 ชั่วโมง → shifted, ไม่มีหรือมีหลายชั่วโมง (กำกวม) → unknown · tolerance ปริยาย 120 วินาทีให้ผลเดิมทุกแถว golden
- F2 Low คำถาม (ตอบและแก้, `b8c993d`): NaN/inf เคยทำให้ raise `ValueError`/`OverflowError` → ตอนนี้คืน unknown พร้อมจำนวนตัวอย่างเดิม ตามกฎ "อื่นๆ → unknown" ของ contract · ถ้าเจ้าของต้องการ error เฉพาะ เป็นเรื่องของ contract ถัดไป
- F3 Low (รับ, `0b8475d`): `in_entry_window` ตัดวินาทีเฉพาะฝั่งเวลาที่ถาม ไม่ตัดฝั่งขอบหน้าต่าง → ตัดทั้งสองฝั่งเป็นนาที หน้าต่าง NY ไม่กระทบ
- ทุกข้อมี regression test ที่ fail ก่อนแก้และ pass หลังแก้ (เวลาในตาราง checks) · ผู้ตรวจปิด F1–F3 ใน r2 (`docs/reviews/CORE-001-r2.md`)

## Finding ของ review r2 (helper ที่เขียนตอนแก้ F1)
- F4 Low (รับ, `0e80263`): ค่า finite ขนาดใกล้ขีดจำกัดของ float (เช่น 1.7e308 กับ tolerance 1e307) ทำให้ `x ± tolerance` ล้นเป็น inf แล้ว raise `OverflowError` แทนที่จะจำแนก → ตอนนี้คืน unknown (หลายชั่วโมงเข้าได้ = กำกวม) ตามนโยบายเดิม
- F5 Low (รับ, `0e80263`): ชั่วโมงที่เกิน 2^53 เมื่อคูณ 3600.0 แบบ float จะปัดจนชั่วโมงข้างเคียง "เข้าพอดี" ด้วย ทำให้ shift ที่ถูกต้องกลายเป็น unknown → เปลี่ยนการคำนวณขอบทั้งหมดเป็น `fractions.Fraction` (exact) helper สั้นลงและไม่มีเลข float เหลืออยู่
- รากเดียวกันจึงแก้ใน commit เดียว (ระบุไว้ใน handoff) · ทั้งสองเป็นค่าขนาดสุดขีดที่ไม่เกิดกับการวัดจริง (SPIKE-001 วัดได้ภายใน ±4 วินาที) แต่ contract ไม่จำกัดขนาด input จึงแก้ให้ถูกทั้งโดเมน · regression fail ก่อน/pass หลัง (ตาราง checks) · ปิดโดยผู้ตรวจใน r3

## Finding ของ review tests-r1 (Low ทั้ง 4 ข้อ)
- F1 ค่า round trip เป็นค่าคงที่ 23 ค่าแทนการสุ่ม: รับทราบ ดีกว่าสุ่มเพราะครอบขอบช่วงทั้งสองด้าน
- F2 M1 15 แท่งข้าม 2 แท่ง M15: ทำตามสูตรของ contract และผ่าน
- F3 `src/sochron/__init__.py` ไม่ถูก AST ตรวจ: ไฟล์มีแค่ docstring และขอให้ reviewer ยืนยัน
- F4 ชื่อไฟล์ test ต้องไม่ซ้ำ: unit test ชื่อ `test_timebase_unit.py`
