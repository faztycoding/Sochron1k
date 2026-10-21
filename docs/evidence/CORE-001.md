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

ทั้ง 7 ข้อผ่านพร้อมกันในรันเดียว: **19 passed, 0 skipped** (acceptance 6, architecture 1, unit 12)

## สิ่งที่ส่งมอบ

| ไฟล์ | หน้าที่ |
|------|---------|
| `src/sochron/timebase/rules.py` | `TimeRule` (frozen) และ `RULES` แบบอ่านอย่างเดียว มีรายการเดียวคือ `Exness-MT5Trial14` offset 0, build 6274, หลักฐาน SPIKE-001 · `rule_for` ปฏิเสธ server ที่ไม่มีกฎ |
| `src/sochron/timebase/convert.py` | `to_utc`, `to_raw` (เลขจำนวนเต็มล้วน ไม่ใช้ float), `to_zone`, `bar_open`, `TIMEFRAMES_MINUTES`, ช่วง raw ที่รับ `[946684800, 4102444800)` |
| `src/sochron/timebase/sessions.py` | `EntryWindow`, `NY_ENTRY_WINDOW` (03:00–15:59 America/New_York), `in_entry_window` (ความละเอียดนาที), `bangkok_date` |
| `src/sochron/timebase/offset.py` | `OffsetClass`, `classify_offset` (รายงานอย่างเดียว ไม่มีเส้นทางแก้กฎ) |
| `src/sochron/timebase/errors.py` | `TimebaseError(ValueError)` และ 5 ชนิดย่อยตาม contract |
| `src/sochron/__init__.py`, `src/sochron/core/__init__.py` | docstring เท่านั้น (ตาม review tests-r1 F3) |
| `tests/unit/timebase/test_timebase_unit.py` | unit tests ของผู้ทำ 12 ข้อ (ขอบช่วง raw, float/bool ถูกปฏิเสธ, to_raw จาก zone อื่น, bar_open idempotent ทุก timeframe, กฎ offset ไม่ใช่ 0, ตัวอย่าง offset จริงจาก SPIKE-001) |
| `pyproject.toml`, `uv.lock` | environment ตาม D-012 (commit `3da18d1`) |

การตัดสินใจระหว่างทำ:
- การแปลงเวลาใช้เลขจำนวนเต็มกับ `timedelta` ทั้งหมด ไม่ผ่าน `timestamp()` ที่เป็น float เพื่อให้ round trip ตรงทุกค่า
- `check_aware` เป็น public helper ให้โมดูลอื่นใช้ปฏิเสธ naive datetime แบบเดียวกัน
- `bar_open` หาร floor บน "วินาที UTC" แล้วบวก offset กลับ ตามสูตรใน contract (ทดสอบด้วย offset 61 และ 3600)
- ไม่มีการอ่านนาฬิกา ไม่มี I/O และไม่มี `MetaTrader5` ในแพ็กเกจ (AST test + ตรวจด้วยตา)

## Checks (2026-10-21, +07, Windows 11, Python 3.12.15 ผ่าน uv 0.13.0, tzdata 2026e)

| Command | ผล | Commit | เวลา |
|---------|-----|--------|------|
| `uv run pytest tests -q -p no:cacheprovider` ก่อนมีโค้ด | FAIL ตามคาด: 7 failed (module missing) | `85d78bf` tests red + `3da18d1` env | 08:26:32 |
| `uv run python -c "import zoneinfo, tzdata; …"` | PASS: `America/New_York`, tzdata 2026e | `3da18d1` | 08:26:32 |
| `uv run pytest tests -q -p no:cacheprovider` หลังมีโค้ด | **PASS 19 passed, 0 skipped, 0.07 s** | commit ที่เพิ่มไฟล์นี้ | 08:29:35 |
| `git diff --cached --check` | PASS | เดียวกัน | ดู handoff |
| `bash scripts/controls/red-flags.sh origin/main` | ดูผลใน handoff (กลุ่ม secret และ order/account mutation ต้องว่าง) | เดียวกัน | ดู handoff |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL ตามคาด: tests ที่ล็อก 3 ไฟล์ของ Codex ต้องมี label ตอน PR | เดียวกัน | ดู handoff |

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- Linux: ยังไม่มี Python job ใน CI (control change แยก) ผลทั้งหมดมาจาก Windows
- เวลาทำการของ `XAUUSDm` ไม่อยู่ในโมดูลนี้ (AC-03 ของ SPIKE-001 ยัง UNKNOWN ด้าน timezone)
- `to_zone` กับชื่อ zone ที่ไม่มีอยู่ปล่อย `ZoneInfoNotFoundError` ของ stdlib (contract ไม่ได้กำหนด error เฉพาะ)
- ยังไม่ผ่าน Codex cross-agent review ของ implementation (ขั้นถัดไป)

## Finding ของ review tests-r1 (Low ทั้ง 4 ข้อ)
- F1 ค่า round trip เป็นค่าคงที่ 23 ค่าแทนการสุ่ม: รับทราบ ดีกว่าสุ่มเพราะครอบขอบช่วงทั้งสองด้าน
- F2 M1 15 แท่งข้าม 2 แท่ง M15: ทำตามสูตรของ contract และผ่าน
- F3 `src/sochron/__init__.py` ไม่ถูก AST ตรวจ: ไฟล์มีแค่ docstring และขอให้ reviewer ยืนยัน
- F4 ชื่อไฟล์ test ต้องไม่ซ้ำ: unit test ชื่อ `test_timebase_unit.py`
