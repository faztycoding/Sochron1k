# หลักฐาน CORE-007: backtest (จำลองการเทรด H001 บนแท่ง bid พร้อมต้นทุน, SL ใน M1 และ R-multiple แบบ pure)

Contract: `docs/contracts/CORE-007-backtest.md` v1.5 (Tier Standard; อนุมัติแทนโดย delegation ของเจ้าของ 2026-10-24 ~07:0x "เอา recommanded ทุกอัน", veto ได้ก่อน merge) · Branch `feat/CORE-007-backtest` (แตกจาก `feat/CORE-006-strategy-h001` `b7256cd` ซึ่ง tree เท่ากับ main `6fbed53` หลัง CORE-006 merge) · การสลับบทบาท: ผู้เขียน tests 2 session และผู้ตรวจ tests รอบ 1 เป็น Claude session ใหม่, ผู้ตรวจ tests รอบ 2 เป็น subagent context ใหม่ ทั้งหมดคนละ session กับผู้ทำ · รายละเอียด tests: `docs/handoff/CORE-007.md`

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 ตัวอย่าง H001 ผ่าน `simulate_trade` ได้ตัวเลขตรงทุกค่า (long และ short) | **PASS** | tests ล็อก AC-01 เขียว |
| AC-02 ตาราง fill ทุกแถวทั้งสองฝั่ง และ `run` กับ decide จริงตรงคำตอบที่คำนวณด้วยมือ | **PASS** | 32 + 2 fill cases, 10 run scenarios เขียว |
| AC-03 sizer ปลอม, equity หมด, Rollover ผิด, input ไม่สอดคล้องทุกแบบ, M1 ระดับ STOP → error ตามชนิด | **PASS** | tests ล็อก AC-03 เขียว |
| AC-04 nights/triple ของ 4 ช่วงถือ (+ rollover คนละ zone/เวลา/วัน triple) และต้นทุน 2× พอดี | **PASS** | tests ล็อก AC-04 เขียว |
| AC-05 ตัดข้อมูลที่ขอบแท่งแล้วไม้เดิมไม่เปลี่ยน, ทุกไม้ของ `run` = `simulate_trade` | **PASS** | tests ล็อก AC-05 + unit test บนข้อมูลสุ่มชุดเดียว 9 แบบ (3 variant × 3 ชุด sides; ไม่มี price gap หรือนาทีที่ขาด ซึ่ง golden และ oracle ของ review r1 ครอบไว้) |
| AC-06 pure, import เฉพาะ core/timebase/strategy/costs + stdlib ตามรายการ, ไม่ import/อ้าง `zoneinfo`/`ZoneInfo`, ไม่เรียก astimezone | **PASS** | architecture 17 tests เขียว |
| AC-07 ทั้ง suite ผ่าน skipped 0 | **PASS ในเครื่อง** · CI รอ run ของ PR | `3211 passed` ที่ `32984af` (หลังแก้ review r1) · ครั้งแรก `3206 passed` ที่ `29eacf3` |
| ความเร็ว: M1 500,000 แท่งภายใน 60 วินาที | **PASS** | `run` 3.53 / 3.56 / 3.61 s (V-A/B/C) |

## สิ่งที่ส่งมอบ (ไฟล์)
- `src/sochron/backtest/{__init__,model,trade,engine}.py`
- `tests/unit/backtest/test_backtest_unit.py` (ทุกไม้ของ `run` = `simulate_trade` บนข้อมูลสุ่มชุดเดียว 3 variant × 3 ชุด sides, ความเร็ว 100,000 แท่ง · regression ของ review r1: F1 time_raw นอกช่วงของ timebase, F2 ค่าใหญ่เกินช่วงของ Decimal, F3 SL ที่นาทีสุดท้ายของแท่ง)
- tests ล็อก: `tests/acceptance/CORE-007/test_backtest.py`, `tests/golden/CORE-007/backtest_cases.py`, `tests/architecture/test_imports.py` (patch D-006 2 รอบ)
- `docs/contracts/CORE-007-backtest.md` v1.5 · `docs/handoff/CORE-007.md` · `docs/reviews/CORE-007-tests-r1.md`, `-tests-r2.md` · ไฟล์นี้

## การตัดสินใจของผู้ทำ
- แบ่งไฟล์: `model.py` (ชนิดข้อมูลและ error), `trade.py` (โค้ด fill และ `simulate_trade`), `engine.py` (`run`) · `run` สร้างทุกไม้ด้วยโค้ด fill ชุดเดียวกับ `simulate_trade` โดยข้ามการตรวจราย M1 ซ้ำ เพราะ `run` ตรวจ M1 ทุกแท่งไว้ก่อนแล้ว
- เวลา T ของ rollover: `datetime.combine(วันที่ของ zone, rollover.at, tzinfo=to_zone(entry).tzinfo)` แล้วเทียบกับ `time_utc` (contract v1.5) · ไล่ทีละวันตั้งแต่วันที่เข้าถึงวันที่ออกตามเวลาของ zone
- `Rollover` ตรวจ zone ด้วย `to_zone` กับเวลาคงที่ · error ของการหา zone (KeyError, ValueError, OSError) แปลงเป็น `BacktestError` โดยไม่ import `zoneinfo`
- `simulate_trade` ตรวจชนิดก่อนค่า แล้วเรียก `costs.check_volume` ก่อน fill ใดๆ (BadVolume ส่งต่อตรงๆ) · ตรวจราย M1 เฉพาะ M1 ที่การ fill อ่าน (v1.5 ข้อ 3)
- `SizedLots` ตรวจตามรายการใน contract พอดี ไม่ปฏิเสธ lots ≤ 0 เอง (ให้ `check_volume` ใน `run` ปฏิเสธ ตาม convention ของ tests)
- stdlib ที่ใช้: collections.abc, dataclasses, datetime, decimal, typing (อยู่ในรายการของ v1.5)

## Checks (2026-10-24, +07, Windows 11, Git Bash, uv 0.13.0, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| ผู้เขียน tests r1 (Claude session ใหม่, headless ที่ 1 จาก 6) | patch `da45cb55…` · 86 tests · reference ใน scratch ผ่าน, mutant 24 + 6 ถูกจับ | b7256cd | 10:0x–10:49 |
| tests r1: `git apply --check` / `git apply` / `git apply -R --check docs/proposals/CORE-007-tests.patch` (แยกคำสั่ง) | PASS · detector 3 ไฟล์ตรง target · SHA256/blob 6 ค่าตรง handoff | a7a0a0f | 10:5x |
| red r1 | 86 failed, 3093 passed | a7a0a0f + r1 | 10:57 |
| tests review r1 (Claude session ใหม่, headless ที่ 2) | ยังไม่พร้อม: F1 Medium (rollover/triple ไม่ถูกทดสอบ), F2–F7 Low · ค่า golden ไม่ผิด | – | 10:5x–11:24 |
| contract v1.5 (F3, F6, คำถามเปิด 1, 3, 5, 6) | commit | 7b70336 | 11:3x |
| ผู้เขียน tests r2 (Claude session ใหม่, headless ที่ 3) | patch `c71fd501…` · +17 tests | 7b70336 + r1 | 11:3x–11:49 |
| tests r2: apply 3 คำสั่งแยก | PASS · detector 3 ไฟล์ตรง target · SHA256/blob 6 ค่าตรง handoff | 7b70336 + r1 | 11:56 |
| red r2 | 103 failed, 3093 passed | 7b70336 + r1 + r2 | 11:56:52 |
| tests re-check r2 (subagent `fresh-eyes-reviewer`) | F1–F7 ปิด · findings open 0 · Ready to commit red: yes | – | 11:5x–12:1x |
| commit red | `e74e298` | – | 12:1x |
| วางโค้ด → `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | **3206 passed in 21.35s** (103 tests ล็อกของ CORE-007 เขียวรอบแรก) | 29eacf3 | 12:18 |
| สคริปต์ scratch: M1 random walk 500,000 แท่ง (seed 20261024), M15 จาก `aggregate`, sizer คงที่ 0.02 lot | `run` V-A 3.53 s (304 ไม้), V-B 3.56 s (252 ไม้), V-C 3.61 s (252 ไม้) · aggregate 0.65–0.94 s | 29eacf3 | 12:19 |
| `bash scripts/controls/red-flags.sh origin/main` | Pattern groups with hits: 0 · control files: tests ล็อก 3 ไฟล์ | 29eacf3 | 12:19 |
| implementation review r1 (Claude session ใหม่, headless ที่ 4 จาก 6) | Ready for PR: yes · Low F1–F4 · oracle อิสระ: 760 runs, 9,000 ไม้, 30,258 กรณีนับคืน, cut sweep ไม่ตรง 0 | a74b9ae | 12:2x–13:00 |
| แก้ F1 → `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | regression ล้มก่อนแก้ (RawTimeOutOfRange) · 3207 passed | e2d5142 | 13:04 |
| แก้ F2 → suite | regression 3 ข้อล้มก่อนแก้ (decimal.Overflow) · 3210 passed | ffcf289 | 13:06 |
| เพิ่ม test F3 → mutant ใน scratch / โค้ดจริง | mutant: 1 failed, 3210 passed · โค้ดจริง: **3211 passed** | 32984af | 13:1x |
| F4 ถ้อยคำ | grep ไม่พบถ้อยคำเดิม | 0b30638 | 13:1x |

## ข้อสังเกตสำหรับ R1 (ไม่ใช่ข้อบกพร่องของ backtest)
- บนข้อมูล random walk 500,000 M1 ข้างบน V-C ได้ผลเท่ากับ V-B ทุกค่า · สคริปต์ scratch นับแล้ว: จาก 2,080 แท่งที่ V-B มีสัญญาณขณะ flat ไม่มีแท่งไหนที่ V-C ตัดสินต่างออกไป (ตัวกรอง TS > 0 ไม่เคยทำงาน เพราะ breakout เหนือ HH 96 แท่งมักมาพร้อม EMA16 > EMA64) · R1 ควรรายงานว่าตัวกรองของ V-C ทำงานกี่ครั้งบนข้อมูลจริง เพราะถ้าแทบไม่ทำงาน V-C จะกินงบ variant โดยไม่เพิ่มข้อมูล

## ข้อจำกัดที่รับไว้
- ด่าน architecture เป็นแบบ static: เส้นทางที่ไม่เอ่ยชื่อ `ZoneInfo` (เช่น `type(…tzinfo)(zone)`) มองไม่เห็น เหมือนข้อจำกัดของ FIX-001 · ไม่มีในโค้ด
- ไม่ตรวจว่า OHLC/spread ของ M15 ตรงกับ M1 (คำถามเปิด 2: R1 สร้าง M15 จาก M1 ชุดเดียวกันด้วย `aggregate`) · short-only และ `at` ที่ fold=1 ไม่ได้ทดสอบ
- `simulate_trade` ไม่ตรวจ M1 หลังจุดที่ไม้ปิด (v1.5 ข้อ 3 เพื่อความเร็วของ CORE-008)
- drawdown ระหว่างถือไม้ไม่อยู่ใน equity points (D10) · halt ของ risk ไม่ใช้ (D5)

## Delivery state
implemented และ verified ในเครื่อง (3211 passed at `32984af`; commit หลังจากนั้นเป็นเอกสาร) · tests reviews r1–r2 ปิด · implementation review r1 Ready for PR: yes, F1–F4 แก้แล้ว → re-check r2 · ยังไม่ merged, ไม่ deployed
