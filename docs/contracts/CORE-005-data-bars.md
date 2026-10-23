# TASK CORE-005 — `core.Bar` + `data.snapshot`: ตรวจคุณภาพแท่ง M1 และประกอบ M15 แบบ pure

Version v1.3 (v1.2 และ v1.3 ดูบรรทัด Status · v1 ร่าง 2026-10-23 15:0x → v1.1 2026-10-24 03:0x: เจ้าของรับข้อเสนอของ `docs/reviews/CORE-005-tests-r1.md` ทั้งหมด = tests รอบ 2 แก้ F1–F5, F7, F8, F11 · contract ข้อ (1)–(5) ในหัวข้อ "v1.1" ข้างล่าง · คำถาม 7 คง D2 ให้ R1 วัดจริง) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 7 (data flow: timebase → data snapshot + validation report), ข้อ 8 แถว `core` และ `data.snapshot`, ข้อ 10 แถว 2 (SLICE-R1: snapshot → validation) · H001 ข้อ 2 (M15 สร้างจาก M1), ข้อ 3 (Invalidation: แท่งใน lookback ขาดหาย, ช่วงที่ validation ให้ STOP) · Tier **Standard** · Branch `feat/CORE-005-data-bars`
Status: **implemented and verified locally; reviews ปิดครบ 2026-10-24 (r1 ตอบครบ, r2 subagent: Ready for PR, F10/F11 แก้แล้ว); รอ PR (label) → CI → merge** · v1.3 (เจ้าของ 2026-10-24 ~06:3x ตาม review r1): (F2) `incomplete` ตัดสินจากนาทีในเวลาตลาดเปิดที่ไม่มี M1 ไม่ใช่จากจำนวน M1 (M1 ซ้ำไม่เติมนาทีที่ขาด) · (F4) เวลาในปฏิทินต้องตรงนาที (มีวินาที → `ValueError`) · (F5) แท่ง M1 ที่ `m1_count` ไม่ใช่ 1 → `ValueError` · (F9) `.gitignore` กัน dotfile ทุกไฟล์ใต้ `src/sochron/data/` · ข้อจำกัดที่รับไว้: (F3) `aggregate` ไม่ตรวจว่า report ทำจากแท่งชุดเดียวกันหรือกฎเวลาเดียวกัน นอกจากจำนวนแท่ง ผู้เรียกต้องส่ง report ของแท่งชุดนั้น · (F6) ข้อมูลที่เรียงผิดกับ `max_gap_minutes` ที่ใหญ่มากอาจช้า (นับทีละนาที) ไม่เกิดกับค่า 5 ของ H001 · (F4 ส่วนที่เหลือ) `Defect` และ `ValidationReport` ไม่ตรวจตอนสร้าง เพราะสร้างโดย `validate_m1` เท่านั้น · v1.2 (เจ้าของ 2026-10-24 ~06:0x): `.gitignore` ยกเว้นเฉพาะไฟล์ `.py` ใต้ `src/sochron/data/` เพราะกฎ `data/` ของข้อมูลตลาดจับโฟลเดอร์ source นี้ด้วย · unit tests ของ snapshot อยู่ที่ `tests/unit/snapshot/` แทน `tests/unit/data/` ด้วยเหตุผลเดียวกัน (ผู้ทำเลือกเพื่อไม่แก้ `.gitignore` เกินที่เจ้าของอนุมัติ) · v1.1 approved by owner 2026-10-24 03:0x · เดิม: approved by owner 2026-10-23 15:0x (acceptance AC-01–AC-07 และทางที่แนะนำทุกข้อ: D1 spread ของ M1 แท่งสุดท้าย · D2 ปฏิทินช่วงปิด [A] 17:00–18:00 NY และศุกร์ 17:00 → อาทิตย์ 18:00 NY · D3 `max_gap_minutes` = 5 [A] · D4 ผู้เขียน tests และผู้ตรวจ = Claude session ใหม่ตามการสลับบทบาท คนละ session กับผู้ทำเสมอ)
Hypothesis (research tasks): ไม่ใช่งานวิจัย แต่ให้บริการ H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`) · ไม่มีการดึงหรืออ่านข้อมูลตลาดจริง (ห้ามก่อน ENV-1) · tests ใช้ข้อมูลสังเคราะห์เท่านั้น

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no — โค้ด pure ไม่เชื่อมต่ออะไร
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no — ไม่มีข้อมูลตลาดจริง ไม่มีไฟล์
- Q4 schema change or deletion of real data: no — นิยามชนิด `Bar` ใหม่ ยังไม่มีข้อมูลที่เก็บไว้
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อก (acceptance, golden, architecture) เข้า repo ผ่าน patch ตาม D-006 เหมือน CORE-002/003

เป็น Standard เพราะทุกผล backtest ของ R1 ขึ้นกับแท่งที่ถูกต้อง: ถ้าประกอบ M15 ผิดหรือซ่อนข้อมูลเสียเงียบๆ ทุกตัวเลขต่อจากนี้ผิดตาม

## Goal / user outcome (Thai)
มีชนิดแท่งราคากลางหนึ่งแบบ (`sochron.core.Bar`) และฟังก์ชัน pure ใน `sochron.data.snapshot` ที่:
- **ตรวจแท่ง M1 แล้วรายงานความผิดปกติ โดยไม่ซ่อมเงียบ:** เวลาถอยหลังหรือซ้ำ, เวลาไม่ตรงนาที, OHLC ขัดกันเอง, ราคาไม่เป็นบวก, spread ติดลบหรือว่าง, และช่องว่างที่ไม่ใช่ช่วงตลาดปิดตามปฏิทินที่กำหนด · ทุกวัน (UTC) ได้สถานะ PASS / WARN / UNKNOWN / STOP
- **ประกอบแท่ง M15 จาก M1 ด้วยโค้ดใน repo** (H001 ข้อ 2) โดยแท่ง M15 บอกได้ว่ามี M1 กี่แท่งและมีป้ายความผิดปกติอะไรติดมา เพื่อให้ strategy ข้ามไม้ตามกฎ Invalidation ของ H001 ได้
- เก็บทั้งเวลาดิบของ MT5 และเวลา UTC ที่แปลงผ่าน `timebase` ตาม AGENTS.md ("Store UTC plus the raw MT5 timestamp")
- ยังไม่มีการอ่านไฟล์ Parquet หรือ manifest (ต้องมี admission ของ `pyarrow` ก่อน → contract ของ SLICE-R1) งานนี้ทำเฉพาะส่วนที่เป็น pure function บน list ของแท่ง

## Current behavior and evidence (revision)
ที่ main `6bd9ef8`: `src/sochron/core/__init__.py` ว่าง · ไม่มีแพ็กเกจ `data` · `sochron.timebase` มี `to_utc(raw, rule)`, `bar_open(raw, timeframe_minutes, rule)`, `TIMEFRAMES_MINUTES`, `NY_ENTRY_WINDOW`, `rule_for(server)` (CORE-001) · SPIKE-001 (`docs/evidence/SPIKE-001.md`): ฟิลด์ของ `copy_rates_range` คือ `time, open, high, low, close, tick_volume, spread, real_volume` · offset ต่อ UTC = 0 บน `Exness-MT5Trial14` (กลไก UNKNOWN) · เห็นช่วงพักตลาดใกล้ 17:00 NY · เวลาทำการของ `XAUUSDm` ด้าน timezone ยัง UNKNOWN (SPIKE-001 AC-03)

## Scope
- In scope: `sochron.core.Bar` · แพ็กเกจ `sochron.data` กับโมดูล `sochron.data.snapshot` (เฉพาะฟังก์ชัน pure ด้านล่าง) · unit tests ของผู้ทำ · acceptance, golden และการขยาย architecture test ให้ครอบ `sochron.core` และ `sochron.data.snapshot` (ห้าม I/O, นาฬิกา, สุ่ม, `MetaTrader5`, `broker`, `data.acquire`) โดยผู้เขียน tests ผ่าน patch D-006 · หลักฐาน · handoff
- Exclusions: อ่าน/เขียน Parquet, manifest, SHA256 ของไฟล์ (ต้องมี dependency → SLICE-R1) · `data.acquire` และการเชื่อม MT5 · การเลือกช่วงข้อมูลที่ใช้วิจัย (R1) · การซ่อมหรือเติมแท่งที่หายไป (ห้ามตามกฎ) · tick data · timeframe อื่นนอกจาก M15 (API รับ timeframe แต่ acceptance ครอบ 15 เท่านั้น)
- Allowed files/modules: `src/sochron/core/**`, `src/sochron/data/__init__.py`, `src/sochron/data/snapshot/**`, `tests/unit/core/**`, `tests/unit/data/**` (ใช้จริง `tests/unit/snapshot/**`, v1.2), `.gitignore` เฉพาะข้อยกเว้น `.py` ของ `src/sochron/data/` (v1.2), `docs/evidence/CORE-005.md`, `docs/handoff/CORE-005.md`, `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch: `tests/acceptance/CORE-005/**`, `tests/golden/CORE-005/**`, `tests/architecture/**`
- Must not touch: `src/sochron/timebase/**`, `src/sochron/costs/**`, `src/sochron/risk/**`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`, `docs/hypotheses/**`, `research/**`, `pyproject.toml`, `uv.lock`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests · ราคาเป็น `decimal.Decimal` (bid ตามที่ MT5 ให้), points และจำนวนเป็น `int` · ชนิดผิด (รวม `float`, `bool`, subclass) → `TypeError` · ไม่มี I/O ไม่อ่านนาฬิกา

```text
sochron.core
  Bar (frozen dataclass, slots):
    time_raw: int             # เวลาเปิดแท่งดิบจาก MT5 (Unix seconds ตามกฎของ server)
    time_utc: datetime        # aware UTC, ต้องเท่ากับ timebase.to_utc(time_raw, rule)
    timeframe: int            # นาที, อยู่ใน timebase.TIMEFRAMES_MINUTES
    open, high, low, close: Decimal   # bid, finite
    spread: int | None        # points, None = MT5 ไม่ให้ค่า
    tick_volume: int          # >= 0
    m1_count: int             # M1 = 1; แท่งที่ประกอบ = จำนวน M1 ที่อ่าน (>= 1, ไม่มีเพดานบน, v1.1)
  ตรวจตอนสร้าง: ชนิด, ความเป็น finite, timeframe อยู่ในชุด และ (v1.1) tick_volume >= 0, m1_count >= 1, time_utc เป็น UTC · ความขัดกันของ OHLC และ spread ติดลบไม่ raise (เพื่อให้รายงานได้) (review tests-r2 F13)

sochron.data.snapshot
  Severity = Literal["WARN", "UNKNOWN", "STOP"]
  DayStatus = Literal["PASS", "WARN", "UNKNOWN", "STOP"]
  Defect (frozen): code: str, severity: Severity, time_raw: int | None, detail: str
  ClosureCalendar (frozen): zone: str, daily_break: tuple[time, time], weekend: tuple[(weekday, time), (weekday, time)], provenance
  H001_CLOSURES: ClosureCalendar          # ค่า [A] ตาม D2
  ValidationReport (frozen): defects: tuple[Defect, ...], days: Mapping[date, DayStatus] (read-only), m1_bars: int, calendar: ClosureCalendar (v1.1)
  validate_m1(bars: Sequence[Bar], rule: TimeRule, calendar: ClosureCalendar, max_gap_minutes: int) -> ValidationReport
  aggregate(bars: Sequence[Bar], timeframe: int, rule: TimeRule, report: ValidationReport) -> tuple[AggregatedBar, ...]
  AggregatedBar (frozen): bar: Bar, flags: frozenset[str]   # flags มาจาก defect ของ M1 ภายในแท่งและช่องว่างที่ไม่คาด
```

รหัส defect (ขั้นต่ำ): `time_not_increasing` (STOP), `duplicate_time` (STOP), `not_minute_aligned` (STOP), `time_rule_mismatch` (STOP: `time_utc` ไม่ตรง `to_utc`), `ohlc_inconsistent` (STOP: high < low, open/close นอก [low, high]), `non_positive_price` (STOP), `negative_spread` (STOP), `missing_spread` (WARN), `unexpected_gap` (WARN: ช่องว่างใน session ที่ยาวเกิน `max_gap_minutes` และไม่อยู่ในช่วงปิดตามปฏิทิน), `empty_weekday` (UNKNOWN: วันธรรมดาที่ไม่มีแท่งเลย อาจเป็นวันหยุด)

กติกาสถานะรายวัน (วัน UTC): มี STOP อย่างน้อยหนึ่ง → STOP · ไม่มี STOP แต่มี UNKNOWN → UNKNOWN · มีแต่ WARN → WARN · ไม่มี defect → PASS

**v1.1 (เจ้าของ 2026-10-24 03:0x, ตาม review tests-r1):**
1. `Bar` ปฏิเสธเพิ่ม (`ValueError`): `tick_volume < 0`, `m1_count < 1`, และ `time_utc` ที่ aware แต่ offset ไม่ใช่ 0 (ต้องเป็น UTC) · **ไม่มีเพดานบนของ `m1_count`** (ผู้ทำปรับจากข้อเสนอ "1..timeframe": M1 ที่ซ้ำเวลาในข้อมูลโบรกเกอร์ซึ่งเป็น defect STOP อยู่แล้วทำให้ `aggregate` นับเกิน timeframe ได้จริง ถ้าตั้งเพดาน `aggregate` จะพังทั้งชุดเพราะแท่งซ้ำแท่งเดียว)
2. `validate_m1` ปฏิเสธ `max_gap_minutes < 0` ด้วย `ValueError`
3. `ValidationReport` มี field `calendar: ClosureCalendar` (ปฏิทินที่ใช้ตรวจ) และ `aggregate` ใช้ field นี้ตัดสิน `incomplete` ตามกติกาข้างล่าง (review F12)
4. AC-06 ครอบ `src/sochron/data/__init__.py` ด้วย (review F10) และห้าม `float` (ชื่อและ literal) ใน `sochron.data.snapshot` แบบเดียวกับ costs/risk (คำถาม 8)
5. `empty_weekday` ไม่มีเวลา (`time_raw` = None; วันที่อยู่ใน `days` และ `detail`) ซึ่งเป็นข้อยกเว้นเดียวของ invariant "มีรหัสและเวลา" (review F9) · วันเสาร์/อาทิตย์ที่ไม่มีแท่งไม่อยู่ใน `report.days` (review F3, คำถาม 5) · `aggregate` ไม่ปฏิเสธ input ที่ไม่เรียงหรือซ้ำ: จัดกลุ่มตาม `bar_open` เรียงในแท่งตาม `time_raw` แบบ stable และพึ่ง defect ใน report (คำถาม 4)

กติกาประกอบแท่ง (D1): จัดกลุ่ม M1 ตาม `timebase.bar_open(time_raw, timeframe, rule)` · open = open ของ M1 แรก, high = max, low = min, close = close ของ M1 สุดท้าย, tick_volume = ผลรวม, `spread` = spread ของ M1 สุดท้าย (None ถ้าแท่งสุดท้ายไม่มีค่า), `m1_count` = จำนวน M1 · ช่องเวลา M15 ที่ไม่มี M1 เลยไม่สร้างแท่ง (ไม่เติม) · flags ของแท่ง = รหัส defect ของ M1 ในแท่ง + `incomplete` ถ้ามีนาทีของแท่งที่ไม่มี M1 และนาทีนั้นอยู่ในเวลาตลาดเปิดตามปฏิทินของ report (v1.3, review r1 F2: M1 ซ้ำไม่เติมนาทีที่ขาด; เดิม "m1_count < timeframe")

## Invariants
- input ไม่ถูกแก้: `validate_m1` และ `aggregate` ไม่เปลี่ยน list หรือแท่งที่รับมา และไม่ลบ/เติม/ซ่อมแท่งใด
- ข้อมูลเสียทุกแบบมีรหัสและเวลาใน report ไม่มีการกลืนเงียบ (ยกเว้น `empty_weekday` ที่ไม่มีแท่งให้อ้างเวลา: วันที่อยู่ใน `days` และ `detail`, v1.1)
- ผลขึ้นกับ input เท่านั้น (เรียกซ้ำได้ผลเดิม) · ไม่ใช้ float ในราคา
- ทุกการแปลงเวลาไปผ่าน `timebase` (ไม่คำนวณ offset เอง)
- import ได้เฉพาะ `core` และ `timebase` ตาม module map

## Negative cases
แท่งเวลาถอยหลัง · เวลาซ้ำ · เวลาไม่ตรงนาที · `time_utc` ไม่ตรงกฎ · high < low · close นอกช่วง · ราคา 0 หรือติดลบ · spread ติดลบ · spread ว่าง · list ว่าง · แท่งเดียว · ช่องว่างตรงขอบ `max_gap_minutes` พอดี (ไม่ใช่ defect) และเกินหนึ่งนาที (defect) · ช่องว่างข้ามช่วงพักรายวันหรือสุดสัปดาห์ · วันเปลี่ยน DST ของ New York (มีนาคมและพฤศจิกายน) ที่ช่วงพักเลื่อนตามเวลา NY · ชนิดผิดทุกช่อง (float, bool, str subclass, Decimal NaN/Infinity)

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given ค่าแต่ละช่องของ `Bar` ทั้งถูกและผิดชนิด (float, bool, subclass, NaN/Infinity, timeframe นอกชุด) When สร้าง `Bar` Then ค่าถูกต้องสร้างได้และอ่านค่ากลับได้ตรง · ค่าผิดได้ `TypeError` หรือ `ValueError` ตามตารางใน tests · `Bar` แก้ค่าหลังสร้างไม่ได้
- AC-02 Given M1 สังเคราะห์ 3 ชั่วโมงที่คำนวณคำตอบด้วยมือไว้ (golden) รวมแท่ง M15 ที่มี M1 ไม่ครบ When `aggregate(..., 15, ...)` Then OHLC, tick_volume, spread (ของ M1 สุดท้าย), m1_count, เวลาเปิดแท่ง (raw และ UTC) และ flag `incomplete` ตรง golden ทุกแท่ง · ช่อง M15 ที่ไม่มี M1 ไม่ถูกสร้าง
- AC-03 Given แท่ง M1 ที่ใส่ความผิดปกติทีละแบบตามรายการรหัส defect When `validate_m1` Then report มีรหัส, severity และเวลาที่ถูกต้องของความผิดปกตินั้น · input ไม่ถูกแก้ (เทียบ copy ก่อนและหลัง) · แท่งไม่ถูกลบหรือเติม
- AC-04 Given ช่องว่างใน M1 ที่ (ก) อยู่ในช่วงพักรายวัน (ข) ข้ามสุดสัปดาห์ (ค) อยู่ใน session ยาวเท่า `max_gap_minutes` พอดี (ง) ยาวเกินหนึ่งนาที รวมวันเปลี่ยน DST ของ NY When `validate_m1` Then (ก)–(ค) ไม่เป็น defect และ (ง) เป็น `unexpected_gap` (WARN) · แท่ง M15 ที่มีช่องว่างแบบ (ง) ได้ flag
- AC-05 Given ชุดวันที่มี defect ผสมกัน When อ่าน `report.days` Then สถานะแต่ละวันเป็นไปตามกติกา STOP > UNKNOWN > WARN > PASS และวันธรรมดาที่ไม่มีแท่งได้ UNKNOWN
- AC-06 Given source ของ `sochron.core`, `sochron.data` (`__init__.py`, v1.1) และ `sochron.data.snapshot` When รัน architecture test Then ไม่มี I/O, นาฬิกา, สุ่ม, `MetaTrader5`, network, `float` ใน snapshot (v1.1) และไม่ import `broker`, `data.acquire`, `execution`, `journal`, `research` (import ได้เฉพาะ `core`, `timebase` และ stdlib ที่ไม่ใช่ side effect)
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมด skipped 0 และ CI `python-tests` เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–05 | test author (acceptance + golden ที่คำนวณด้วยมือ) | `uv run --offline pytest tests/acceptance/CORE-005 tests/golden/CORE-005 -q -p no:cacheprovider` | L2 |
| 06 | test author (patch ของ architecture test) + reviewer | `uv run --offline pytest tests/architecture -q -p no:cacheprovider` + mutation: ใส่ `open(...)`/`time.time()` ลงสำเนาโมดูลแล้วต้องถูกจับ | L2 |
| 07 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยงหลัก: (ก) ปฏิทินช่วงปิดตลาดผิด → ช่องว่างจริงถูกมองเป็นช่วงปิด (ซ่อนข้อมูลเสีย) หรือกลับกัน (ข้ามไม้มากเกิน) จึงเป็นค่า [A] ที่ติดป้ายที่มาและต้องยืนยันด้วยข้อมูลจริงใน R1 (ข) นิยาม spread ของ M15 (D1) มีผลกับ spread filter ของ H001 จึงให้เจ้าของเลือก

## Plan, dependencies and unknowns (P06)
1. Understanding: สร้างชนิดแท่งกลางและฟังก์ชันตรวจ/ประกอบแท่งแบบ pure ที่รายงานข้อมูลเสียโดยไม่ซ่อม · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่าต้องอ่านไฟล์ — ไม่ (ข) คิดว่าควรเติมแท่งที่หายด้วยราคาก่อนหน้า — ห้าม (ค) คิดว่าช่องว่างทุกช่องคือข้อมูลเสีย — ช่วงปิดตลาดไม่ใช่
2. Files / reuse: `timebase.to_utc`, `bar_open`, `TIMEFRAMES_MINUTES`, `TimeRule`; รูปแบบการตรวจชนิดแบบ exact จาก `costs`/`risk`
3. Steps: (1) เจ้าของอนุมัติ → (2) ผู้เขียน tests เขียน patch (acceptance + golden + architecture) → (3) Claude apply ตาม D-006 + fresh review → commit red → (4) implement + unit tests → (5) review → PR (label เพราะ tests ล็อก) → merge
4. Risks: ดูข้างบน · ประสิทธิภาพ: ข้อมูลจริง 2018–2024 ราว 2.5 ล้านแท่ง M1 ต้องประมวลได้ในเวลาที่รับได้ → unit test วัดเวลาบนข้อมูลสังเคราะห์ 500,000 แท่ง (ไม่ใช่ acceptance)
5. Decisions needed from the owner:
   - **D1 spread ของแท่ง M15:** (แนะนำ) spread ของ M1 แท่งสุดท้าย = สภาพตอนปิดแท่ง t ซึ่งเป็นข้อมูลที่มี ณ เวลาตัดสินใจ · ทางอื่น: ค่าสูงสุดในแท่ง (เข้มกว่า) หรือ median
   - **D2 ปฏิทินช่วงปิดตลาด [A]:** (แนะนำ) zone `America/New_York`, พักรายวัน 17:00–18:00 NY, สุดสัปดาห์ ศุกร์ 17:00 → อาทิตย์ 18:00 NY · ที่มา: SPIKE-001 เห็นช่วงพักใกล้ 17:00 NY และเวลาทำการทองทั่วไป · สถานะ assumed จนกว่า R1 วัดจากข้อมูลจริง
   - **D3 `max_gap_minutes` [A]:** (แนะนำ) 5 นาที · ช่องว่างใน session ที่ยาวกว่านี้เป็น WARN (ทองมีสภาพคล่องสูง ช่องว่าง 1–5 นาทีอาจเกิดได้จริงช่วงเงียบ)
   - **D4 ผู้เขียน tests และผู้ตรวจ:** (แนะนำ) Claude session ใหม่ตามการสลับบทบาทเหมือน CORE-004 · ทางอื่น: รอ Codex หลัง 2026-10-28 19:41

## Authorization (filled by the owner)
- เจ้าของอนุมัติ 2026-10-23 15:0x · ผู้เขียน tests (Claude session ใหม่): patch ของ `tests/acceptance/CORE-005/**`, `tests/golden/CORE-005/**`, `tests/architecture/**` · Claude: implement ตาม scope, apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1–2 sessions · headless session ไม่เกิน 5 (tests, fresh review ของ tests, implementation review ×2, สำรอง) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง · checkpoint ใน PROGRESS หลังแต่ละขั้น

## DoR status / missing items / next action
ครบ: module map, timebase API, ฟิลด์ MT5 จาก SPIKE-001, กฎ H001, การอนุมัติและ D1–D4 · next: ผู้เขียน tests เขียน patch

## Done scope
merge แล้ว, suite เขียวใน CI
