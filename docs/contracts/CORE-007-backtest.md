# TASK CORE-007 — `backtest`: จำลองการเทรด H001 บนแท่ง bid พร้อมต้นทุน, SL ใน M1 และ R-multiple แบบ pure

Version v1.4 (v1 ร่าง 2026-10-24 07:xx → v1.1 ตอบ contract review r1 F1–F15 → v1.2 ตอบ r2 F16–F32 → v1.3 ตอบ r3 F33–F38 → v1.4 ตอบ r4 F39–F40 ดูหัวข้อ "Answers to contract reviews") · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 7, 8 (แถว `backtest`), 10 แถว 2 (SLICE-R1) · H001 ข้อ 3, 6, 7, 8 · ต่อจาก CORE-005 (`Bar`, `AggregatedBar`) และ CORE-006 (`indicators`, `decide`) · Tier **Standard** · Branch `feat/CORE-007-backtest`
Status: **approved by delegation 2026-10-24** — เจ้าของสั่งในแชท Claude 2026-10-24 ~07:0x "ทำให้เสร็จทั้งหมดเลย" และ "มึงตัดสินไปเลย… เอา recommanded ทุกอัน" Claude จึงอนุมัติ acceptance และทางที่แนะนำทุกข้อแทน · ค่าทุกค่ามาจาก H001, SPIKE-001, CORE-002/003/005/006 ค่าใหม่ติดป้าย [A] · ผู้ตรวจอิสระอ่าน contract แทนเจ้าของ (r1: 15, r2: 19, r3: 6, r4: 2 findings) ต้องได้ "Ready for test authoring: yes" ก่อนเขียน tests · **เจ้าของ veto หรือแก้ acceptance ได้ทุกเมื่อก่อน merge**
Hypothesis (research tasks): H001 · เขียน simulator เท่านั้น **ไม่รัน backtest กับข้อมูลจริง** (ห้ามก่อน ENV-1 และ SLICE-R1) · tests ใช้ข้อมูลสังเคราะห์

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no — จำลองเท่านั้น ไม่มีเส้นทางส่งคำสั่ง
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อกเข้า repo ผ่าน patch ตาม D-006

เป็น Standard เพราะทุกตัวเลขของ R1 (expectancy, drawdown, การเทียบกับการสุ่ม, ต้นทุน 2×) มาจากโมดูลนี้

## Goal / user outcome (Thai)
มีโมดูล `sochron.backtest` ที่จำลองการเทรดของ H001 บนข้อมูลแท่งที่ตรวจแล้ว แล้วคืนรายการไม้ทุกไม้พร้อมเหตุผล ต้นทุน และ R-multiple:
- ตัดสินใจที่ปิดแท่ง M15 t ด้วย `strategy.decide` แล้วทำคำสั่งที่ราคาเปิดของ M1 แท่งแรกของแท่ง M15 ถัดไป (H001 ข้อ 3)
- กำไรขาดทุนคิดจากราคา bid · spread, slippage, commission และ swap คิดผ่าน `costs.round_trip_cost` ครั้งเดียวต่อไม้
- มีฟังก์ชันระดับไม้ `simulate_trade` ที่ `run` ใช้ และงาน baseline (CORE-008) ใช้ได้ด้วยกติกาเดียวกัน · `run` จำกัดฝั่งได้ (long-only baseline ของ H001 ข้อ 7)
- ต้นทุน 2× ด้วย `costs.stress(model, 2)` ไม่เปลี่ยนราคาและกำไรขาดทุนก่อนต้นทุน
- pure: ไม่มี I/O, นาฬิกา, สุ่ม · ไม่ดูข้อมูลอนาคต · import ตาม module map เดิม

## Scope
- In scope: แพ็กเกจ `sochron.backtest` (`run`, `simulate_trade`, ชนิดข้อมูล, `BacktestError`) · unit tests · acceptance, golden และการขยาย architecture test ให้ครอบ `sochron.backtest` โดยผู้เขียน tests ผ่าน patch D-006 · หลักฐาน · handoff
- Exclusions: halt ของ risk (D5) · random-entry baseline, ตัวเลือกแท่งที่สุ่มได้ (eligible-bar predicate), สถิติ, registry, รายงาน (CORE-008) · ตัวเชื่อม sizer จริง (ประกอบใน `app`) · การอ่านข้อมูลจริง · หลายสถานะพร้อมกัน · drawdown ระหว่างถือไม้ (D10)
- Allowed files: `src/sochron/backtest/**`, `tests/unit/backtest/**`, `docs/evidence/CORE-007.md`, `docs/handoff/CORE-007.md`, `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch: `tests/acceptance/CORE-007/**`, `tests/golden/CORE-007/**`, `tests/architecture/**`
- Must not touch: `src/sochron/{timebase,core,data,costs,risk,strategy}/**`, `docs/hypotheses/**`, `docs/architecture.md`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `research/**`, `pyproject.toml`, `uv.lock`

## Inputs / outputs / errors (contract)
ตัวเลขเป็น `Decimal` คำนวณใน `sochron.costs.CONTEXT` (precision 28, ROUND_HALF_EVEN) · `stop_price` ไม่ปัด · net = gross − costs.total · tests เทียบด้วยค่า Decimal ไม่เทียบ string · ชนิดผิด (float, bool, subclass) → `TypeError` · ค่าผิดโดเมนของ backtest → `BacktestError` (subclass ของ `ValueError`) · error จาก `costs` (เช่น `BadVolume`) และ exception จาก sizer ส่งต่อโดยไม่ห่อ

```text
sochron.backtest
  BACKTEST_VERSION = "backtest-v1"
  Side = Literal["long", "short"]
  Sizer = Callable[[Decimal, Decimal], SizedLots]           # (equity ณ เวลาเปิดไม้, stop_distance)
  SizedLots (frozen): lots: Decimal | None, risk_money: Decimal, actual_risk: Decimal | None, reason: str
  Rollover (frozen): zone: str, at: time                     # D4 [A]: Rollover("America/New_York", time(17, 0))
  Trade (frozen): side, entry_time_raw, entry_bid, entry_spread_points: int, exit_time_raw, exit_bid,
                  exit_spread_points: int, lots, stop_distance, stop_price,
                  exit_reason: Literal["signal", "stop", "end_of_data"], ambiguous: bool,
                  nights: int, triple_nights: int, costs: CostBreakdown, gross_money, net_money,
                  risk_money, actual_risk: Decimal | None, r: Decimal, data_flags: frozenset[str]
  Skip (frozen): time_raw: int, reasons: tuple[str, ...]
  Result (frozen): trades, skips, equity: tuple[tuple[int, Decimal], ...], backtest_version: str, strategy_version: str
  simulate_trade(m1: Sequence[Bar], entry_index: int, side: Side, stop_distance: Decimal, lots: Decimal,
                 model: CostModel, rollover: Rollover, *, risk_money: Decimal, actual_risk: Decimal | None = None,
                 exit_index: int | None = None, data_flags: frozenset[str] = frozenset()) -> Trade
  run(m1: Sequence[Bar], m15: Sequence[<AggregatedBar-like>], params: H001Params, model: CostModel, sizer: Sizer,
      equity: Decimal, rule: TimeRule, rollover: Rollover, *, sides: frozenset[Side] = frozenset({"long", "short"})) -> Result
```

### Input และการตรวจ
- แท่ง M15 รับแบบ duck typing: `.bar` เป็น `core.Bar` พอดี (timeframe 15) และ `.flags` เป็น `frozenset` ของ `str` · `sochron.backtest` ไม่ import `data.snapshot` · ใน R1 คือผลของ `data.snapshot.aggregate`
- `run` ปฏิเสธด้วย `BacktestError`: `m1` หรือ `m15` ว่าง · equity เริ่ม ≤ 0 · M1 timeframe ≠ 1 หรือเวลาไม่เพิ่มขึ้นเคร่งครัด · M15 timeframe ≠ 15 หรือเวลาไม่เพิ่มขึ้นเคร่งครัด · M1 ที่ไม่อยู่ในแท่ง M15 ใด (`timebase.bar_open(t, 15, rule)`) หรือแท่ง M15 ที่ไม่มี M1 · M1 ที่ `time_utc ≠ to_utc(time_raw, rule)` · M1 ที่มีข้อบกพร่องระดับ STOP ที่ทำให้ fill ผิด: spread ติดลบ, OHLC ขัดกัน, ราคาไม่เป็นบวก (R1 ต้องตัดวัน STOP ก่อนเรียก)
- `Rollover.__post_init__` ตรวจตอนสร้าง (r3 F36): `zone` str พอดีและรู้จัก (zone ที่ไม่รู้จัก → `BacktestError`) · `at` เป็น `time` พอดี ไม่มี tzinfo และตรงนาที (ไม่ใช่ → `BacktestError`; ชนิดผิด → `TypeError`) · `run` และ `simulate_trade` รับเฉพาะ `Rollover` พอดี (`TypeError`)
- `SizedLots.__post_init__`: ชนิดพอดีทุก field (`TypeError`) · Decimal ทุก field ที่ไม่ใช่ None เป็น finite (r4 F39) · `risk_money` > 0 · lots None ⇒ `actual_risk` None · lots มีค่า ⇒ `actual_risk` None หรือ > 0 · `reason` เป็น str ไม่ว่าง (ค่าผิด → `BacktestError` ซึ่งเกิดใน sizer และส่งต่อ) (r3 F33) · `run` หลังได้ SizedLots ที่ lots ไม่ใช่ None: `costs.check_volume(lots, model)` (`BadVolume` ส่งต่อ)
- `simulate_trade` (r3 F34, F35): `0 ≤ entry_index < len(m1)` · `exit_index` None หรือ `entry_index < exit_index < len(m1)` · ใช้การตรวจราย M1 ชุดเดียวกับ `run` (timeframe 1, เวลาเพิ่มขึ้นเคร่งครัด, spread ติดลบ, OHLC ขัดกัน, ราคาไม่เป็นบวก) กับทุก M1 ที่อ่าน ก่อน fill ใดๆ · ไม่ตรง → `BacktestError`
- ค่าโดเมนที่ตรวจก่อน fill ใดๆ ทั้งใน `run` และ `simulate_trade` (r3 F35): side เป็น "long" หรือ "short" · `stop_distance` > 0 · `risk_money` > 0 · `actual_risk` None หรือ > 0 · `sides` เป็น frozenset ไม่ว่างที่เป็นสับเซตของ {"long", "short"} · Decimal ที่เป็น argument ของ `run`/`simulate_trade` (equity, stop_distance, lots, risk_money, actual_risk) เป็น finite · ไม่ตรง → `BacktestError` (ชนิดผิด → `TypeError`) · ขอบเขต (r4 F39): field ของ `CostModel` และ `H001Params` ตรวจโดยโมดูลของมันเอง (error ของ costs/strategy) และ field ของ `SizedLots` ตรวจใน `SizedLots.__post_init__`
- เวลา (r3 F38): `sochron.backtest` แปลงเวลาผ่าน `timebase` เท่านั้น (`to_zone`, `to_utc`, `bar_open`) ไม่ import `zoneinfo` และไม่เรียก `astimezone` เอง

### กติกา fill และ SL — `s` = spread (points) ของ M1 ที่เกิดเหตุการณ์ ถ้า None ใช้ `model.spread_fallback_points` · `p` = `model.point`
| เหตุการณ์ | long | short |
|---|---|---|
| เข้าไม้ที่ open ของ M1 `entry_index` | entry_bid = open · fill_ask = open + s·p · `stop_price` = fill_ask − stop_distance | entry_bid = open · `stop_price` = open + stop_distance (ระดับ ask) |
| ตรวจ SL ในแต่ละ M1 (ตามลำดับเวลา) **ตรวจราคาเปิดก่อน**: (1) gap | open ≤ stop_price → exit_bid = open | open + s·p ≥ stop_price → exit_bid = open |
| (2) แตะกลางแท่ง ถ้าไม่ gap | low ≤ stop_price → exit_bid = stop_price | high + s·p ≥ stop_price → exit_bid = stop_price − s·p |
| ปิดตามสัญญาณที่ open ของ M1 `exit_index` (ถ้า open นั้นเลย SL ตามแถว gap → `stop` + `ambiguous` ราคา open) | exit_bid = open | exit_bid = open |
| ข้อมูลหมด (ไม่มี exit_index และไม่โดน SL) | exit_bid = close ของ M1 สุดท้าย, exit_time = time_raw ของ M1 นั้น | เหมือนกัน |
- M1 ที่เข้าไม้: ตรวจ SL ตามตารางโดยใช้ open ของ M1 นั้นด้วย ดังนั้นถ้า `stop_distance ≤ s·p` ไม้ปิด `stop` ทันทีที่ open ของ M1 เดียวกัน
- SL ตรวจใน M1 `entry_index … exit_index − 1` (มี exit_index) หรือ `entry_index …` จนจบ (ไม่มี)
- `entry_spread_points` / `exit_spread_points` = `s` ที่ใช้จริง (int หลัง fallback) ทุกกรณี
- per-bar spread ของ MT5 ใช้แทน spread ณ จังหวะ high/low เป็นค่า [A]
- `gross_money` = (exit_bid − entry_bid) × contract_size × lots × (+1 long / −1 short) **ไม่คูณ stress_factor**
- `costs` = `round_trip_cost(side, lots, entry_spread_points, exit_spread_points, nights, triple_nights, model)` · `r` = `costs.r_multiple(net_money, risk_money)`
- **R (D8):** `risk_money` = R ตามสูตร H001 (0.25% × equity ณ เปิดไม้) · `actual_risk` เก็บไว้รายงาน · ไม่ใช้ตัวอย่าง "+1.41 R" ของ H001 ที่หารด้วยความเสี่ยงจริงหลังปัด lot

### nights (D4 [A])
nights = จำนวนเวลา T = `rollover.at` ตามเวลา `rollover.zone` บนวันจันทร์–ศุกร์ของ zone นั้น ที่ entry < T ≤ exit โดย entry/exit คือ `time_utc` ของ M1 ที่เข้าและออก · triple_nights = จำนวน T ที่วันของ zone (`weekday()`) ตรง `model.triple_swap_weekday` · การนับอยู่ใน backtest จนกว่ามีหลักฐานเวลา rollover ของโบรกเกอร์ แล้วจึงย้ายไป `timebase` ให้ E1 ใช้ร่วม

### ลำดับเหตุการณ์ต่อแท่ง M15 t ใน `run`
1. ถ้ามีไม้ถืออยู่: ตรวจ SL ทุก M1 ของแท่ง t ตามตาราง · โดน SL → ไม้ปิด `stop` ที่ M1 นั้น
2. ถ้า t ไม่ใช่แท่งสุดท้าย: `decide(rows, t, position, next_open_utc, params)` โดย position คือสถานะหลังข้อ 1 และ `next_open_utc` = `time_utc` ของแท่ง M15 ถัดไปที่มีอยู่จริง · โดน SL ในแท่ง t แล้ว position = flat จึงเข้าไม้ใหม่ (รวมฝั่งตรงข้าม) ที่ t+1 ได้ และไม่มีการปิดซ้ำ
3. `exit` → ปิดที่ open ของ M1 แรกของแท่ง t+1 (หรือ `stop` + ambiguous ถ้า open นั้นเลย SL)
4. `enter_*` ฝั่งที่อยู่ใน `sides` → ถ้า equity ปัจจุบัน ≤ 0: `Skip(time_raw ของแท่ง t, ("equity_exhausted",))` · ไม่เช่นนั้น sizer(equity, stop_distance) · lots None → `Skip(time_raw ของแท่ง t, (reason,))` · ไม่เช่นนั้นเข้าไม้ที่ open ของ M1 แรกของแท่ง t+1 · `enter_*` ฝั่งที่ไม่อยู่ใน `sides` ถือเป็น `none` (ไม่มี Skip)
5. `skip` จาก decide → `Skip(time_raw ของแท่ง t, reasons ของ decide)` บันทึกเสมอไม่ว่า `sides` เป็นอะไร เพราะ `Decision` ไม่บอกฝั่ง (r3 F37) · `none`/`hold` ไม่บันทึก
6. แท่งสุดท้าย: ไม่เรียก decide · ไม้ที่ยังถืออยู่ปิด `end_of_data`
- equity points: (time_raw ของ M1 แรก, equity เริ่มต้น) แล้วหนึ่งจุดต่อการปิดไม้ (exit_time_raw, equity หลัง net) · realized curve
- `data_flags` = union ของ flags ของแท่ง M15 ตั้งแต่แท่งตัดสินใจเข้าไม้ (t) จนถึงแท่งที่มี M1 ของการปิด รวมทั้งสองปลาย · `unexpected_gap` บนแท่งที่ fill คือเครื่องหมาย "fill หลังข้อมูลขาด" ที่ R1 ต้องรายงาน
- `run` สร้างแต่ละไม้ด้วย `simulate_trade` (exit_index = M1 ของการปิดเมื่อปิดตามสัญญาณ, None เมื่อโดน SL กลางทางหรือข้อมูลหมด; data_flags ตามข้างบน)

## Invariants
- ใช้ `strategy.decide` และ `costs` จริง ไม่เขียนกฎหรือสูตรต้นทุนซ้ำ · ถือได้ครั้งละหนึ่งสถานะ
- ไม้ทุกไม้ของ `run` เท่ากับ `simulate_trade` ของจุดเข้า/ออกเดียวกัน
- ไม่มี look-ahead ตามขั้นตอนตัดข้อมูลใน AC-05
- pure, deterministic · import ได้เฉพาะ `core`, `timebase`, `strategy`, `costs` และ stdlib ที่ไม่ใช่ side effect

## Negative cases
gap เลย SL ทั้งสองฝั่ง (low < open < stop) · SL ใน M1 ที่เข้าไม้ · stop_distance ≤ s·p · SL กลางแท่ง t แล้วสัญญาณฝั่งตรงข้ามที่ปิดแท่ง t · exit ที่ open เลย SL · spread ว่างตอนเข้า/ออก/ตรวจ SL · sizer คืน None, lots นอก grid, risk_money ≤ 0 · equity หมด · enter/exit ที่แท่งรองสุดท้าย · ข้อมูลหมดขณะถือ · ถือข้ามคืน/วันพุธ/สุดสัปดาห์/วันเปลี่ยน DST · long-only · M1/M15 ไม่สอดคล้องทุกแบบ · M1 ระดับ STOP · Rollover ผิด · ชนิดผิดทุกช่อง

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given ตัวอย่าง H001 ผ่าน `simulate_trade`: long เข้า M1 2026-03-10 13:45 UTC (อังคาร) bid 4012.66 spread 240, stop_distance 12.00, lots 0.02, risk_money 25, ปิดตามสัญญาณที่ M1 2026-03-11 14:00 UTC (พุธ 10:00 NY) bid 4029.86 spread 240 When คำนวณ Then nights 1, triple 0, gross 34.40, spread 0.48 / commission 0 / slippage 0.20 / swap 1.0076 / total 1.6876, net 32.7124, r 1.308496, stop_price 4000.90 · short เวลาเดียวกัน เข้า bid 4029.86 ปิด bid 4012.66: stop_price 4041.86, gross 34.40, spread 0.48 (ฝั่งปิด), slippage 0.20, swap 0, total 0.68, net 33.72, r 1.3488 (เทียบด้วยค่า Decimal)
- AC-02 Given ผ่าน `simulate_trade`: ทุกแถวของตาราง fill ทั้งสองฝั่ง (gap ที่ low < open < stop, แตะกลางแท่ง, M1 ที่เข้าไม้, stop_distance ≤ s·p, exit ที่ open เลย SL, ข้อมูลหมด, spread None ทุกตำแหน่ง) และผ่าน `run` ด้วย decide จริงบนข้อมูลสังเคราะห์: SL กลางแท่ง t แล้วเข้าฝั่งตรงข้ามที่ t+1, enter/exit ที่แท่งรองสุดท้าย, Skip จาก decide และจาก sizer, data_flags รวมสองปลาย, long-only When คำนวณ Then exit_reason, exit_bid, spread ที่ใช้, เวลา, ambiguous, Skip และ data_flags ตรงคำตอบที่คำนวณด้วยมือ
- AC-03 Given sizer ปลอม (ขนาดต่างๆ, None, lots นอก grid, risk_money ≤ 0, ชนิดผิด), equity ที่หมด, Rollover ผิด, input ไม่สอดคล้องทุกแบบในหัวข้อ "Input และการตรวจ" และ M1 ระดับ STOP When `run`/`simulate_trade` Then ได้ `TypeError`/`BacktestError`/`BadVolume` ตามหัวข้อนั้น · sizer ได้ equity หลังไม้ก่อนหน้า · ไม่เปิดไม้ซ้อน · equity points ตามรูปแบบ · `backtest_version` = "backtest-v1" และ `strategy_version` = `STRATEGY_VERSION`
- AC-04 Given ไม้ผ่าน `simulate_trade` ที่ถือ ศุกร์ 10:00 NY→จันทร์ 10:00 NY, จันทร์ 10:00→จันทร์ถัดไป 10:00, อังคาร 10:00→พฤหัส 10:00 และ ศุกร์ 2026-10-30 14:00 UTC→จันทร์ 2026-11-02 21:30 UTC When คำนวณ Then (nights, triple) = (1,0), (5,1), (2,1), (1,0) · และด้วย lots คงที่ model กับ `stress(model, 2)` ให้ราคา, stop_price และ gross เท่ากัน ต้นทุนทุกส่วนเป็น 2× พอดี
- AC-05 Given ข้อมูลชุดหนึ่งและไม้ k ที่ปิดใน M1 ของแท่ง M15 u When ตัดข้อมูลที่ขอบแท่ง (เก็บแท่ง M15 ถึง u ทั้งแท่งโดยไม่ aggregate ใหม่ และ M1 ในแท่งเหล่านั้น) แล้ว `run` ใหม่ Then ไม้ 1..k ทุก field, Skip ที่ time_raw < open ของ u และ equity points ถึงการปิดไม้ k เหมือนเดิม · และทุกไม้ของ `run` เท่ากับ `simulate_trade` ของจุดเข้า/ออกเดียวกันตามการแมปในลำดับเหตุการณ์
- AC-06 Given source ของ `sochron.backtest` When รัน architecture test Then ไม่มี I/O, นาฬิกา, สุ่ม, float, network, ไม่ import `zoneinfo` และไม่เรียก `astimezone` (แปลงเวลาผ่าน `timebase` เท่านั้น, r3 F38) และ import ได้เฉพาะ `core`, `timebase`, `strategy`, `costs` (ไม่ `data`, `risk`, `broker`, `execution`, `journal`, `research`)
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมด skipped 0 และ CI เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–05 | test author (acceptance + golden ที่คำนวณด้วยมือจาก contract นี้) | `uv run --offline pytest tests/acceptance/CORE-007 tests/golden/CORE-007 -q -p no:cacheprovider` | L2 |
| 06 | test author + reviewer | architecture test + mutation | L2 |
| 07 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |
| ความเร็ว | Claude (unit test/หลักฐาน ไม่ใช่ acceptance) | `run` บน M1 สังเคราะห์ 500,000 แท่ง ภายใน 60 วินาทีบนเครื่องอ้างอิง | L2 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยงหลัก: ผลวิจัยดีเกินจริงจาก fill/ต้นทุน/R ที่ผิด (ปิดด้วยตาราง fill และ golden) · ค่า [A]: เวลา rollover, per-bar spread ณ จังหวะ high/low · ความเสี่ยงของ R1: 63 รัน + 1,000 รันสุ่มต่อ variant บน M1 ~2.5 ล้านแท่ง อาจช้า → วัดในหลักฐานและวางแผนใน CORE-008

## Plan, dependencies and unknowns (P06)
1. Understanding: simulator ที่ต่อ strategy + costs เข้ากับข้อมูลแท่ง · เข้าใจผิดที่เป็นไปได้: คิด spread สองครั้ง · ใช้ risk หรือ data.snapshot · ใส่ halt · ใช้ points_to_money กับ gross · หาร R ด้วยความเสี่ยงจริง · ตรวจแตะกลางแท่งก่อน gap
2. Files / reuse: `strategy.indicators/decide/STRATEGY_VERSION`, `costs.round_trip_cost/r_multiple/stress/check_volume/CONTEXT`, `timebase.to_zone/to_utc/bar_open`
3. Steps: (1) CORE-006 พร้อม (2) contract review จน ready (3) ผู้เขียน tests (4) apply + review → red (5) implement (6) review → PR
4. Decisions (อนุมัติแทนโดย delegation ตามทางที่แนะนำ):
   - **D1 sizing:** ผู้เรียกส่ง `sizer` · ตัวแปลงจาก `risk.size_position`: lots 0 → `SizedLots(lots=None, risk_money=SizeDecision.risk_money, actual_risk=None, reason=SizeDecision.reason)` · lots > 0 → `SizedLots(lots, risk_money, actual_risk=SizeDecision.actual_risk, reason)` (r3 F33) · ประกอบใน `app` ไม่แก้ module map
   - **D2 ราคา:** ตามตาราง fill · gross ไม่คูณ stress
   - **D3 ambiguous:** exit ที่ open เลย SL = `stop` + ambiguous ราคา open
   - **D4 nights [A]:** ตามหัวข้อ nights
   - **D5 halts:** ไม่ใช้ halt ของ risk (วัด edge; ให้ E1 บันทึกว่าผล Demo จะต่างเมื่อ halt ทำงาน)
   - **D6 ข้อมูลหมด:** ปิดที่ close bid ของ M1 สุดท้าย
   - **D7 ผู้เขียน tests และผู้ตรวจ:** Claude session ใหม่ตามการสลับบทบาท · contract review ใช้ subagent
   - **D8 R:** หารด้วย R ตามสูตร
   - **D9 M15 input:** duck typing
   - **D10 drawdown:** realized curve · drawdown ระหว่างถือเป็นข้อจำกัดที่ R1 ต้องรายงาน
   - **D11 sides:** `run` รับ `sides` เพื่อทำ long-only baseline
   - **D12 equity หมด:** ไม่เปิดไม้ใหม่ (Skip `equity_exhausted`) แทนการ raise เพื่อเก็บผลที่วัดได้
   - **D13 STOP data:** `run` ปฏิเสธ M1 ระดับ STOP ที่ทำให้ fill ผิด

## Answers to contract reviews
| Review | Finding | ตอบที่ |
|---|---|---|
| r1 | F1, F24 | AC-01 (ตัวเลขคำนวณด้วยมือ, วันที่, ค่าฝั่ง short) |
| r1 | F2 | "R (D8)" ใต้ตาราง fill, D8 |
| r1 | F3, F26 | D1 · "Input และการตรวจ" (SizedLots) · AC-03 |
| r1 | F4 | "Input และการตรวจ" (duck typing) · AC-06 · D9 |
| r1 | F5, F25 | หัวข้อ nights · AC-04 |
| r1 | F6, F20, F21 | ตาราง fill และบรรทัดใต้ตาราง |
| r1 | F7, F29 | ลำดับเหตุการณ์ข้อ 1–6 · AC-02 |
| r1 | F8 | gross ไม่คูณ stress · AC-04 |
| r1 | F9, F16, F17 | signature ของ `simulate_trade` (keyword-only, data_flags) · "Input และการตรวจ" (ขอบเขต index) · การแมป exit_index ในลำดับเหตุการณ์ · AC-05 |
| r1 | F10 | บรรทัดแรกของ "Inputs / outputs / errors" |
| r1 | F11, F27, F28 | "Input และการตรวจ" · D12, D13 · AC-03 |
| r1 | F12 | equity points · D10 |
| r1 | F13 | ประโยคสุดท้ายของหัวข้อ nights |
| r1 | F14, F18, F19 | data_flags ในลำดับเหตุการณ์ · AC-05 (ขั้นตอนตัดข้อมูล) |
| r1 | F15, F30 | `BACKTEST_VERSION` · AC-02/AC-03 รวมทุกข้อที่เคยไม่มี AC |
| r2 | F22 | AC-01/02/04 ผ่าน `simulate_trade` · AC-02 ส่วน `run` ใช้ decide จริง |
| r2 | F23 | `sides` (D11) · eligible-bar predicate เป็นของ CORE-008 (Exclusions) |
| r2 | F31 | ตารางนี้ |
| r2 | F32 | แถว "ความเร็ว" ใน Verification · Risk |
| r3 | F33 | D1 (ตัวแปลง) · SizedLots ใน "Input และการตรวจ" |
| r3 | F34, F35 | `simulate_trade` และ "ค่าโดเมนที่ตรวจก่อน fill" ใน "Input และการตรวจ" |
| r3 | F36 | `Rollover.__post_init__` ใน "Input และการตรวจ" |
| r3 | F37 | ลำดับเหตุการณ์ข้อ 5 |
| r3 | F38 | "เวลา" ใน "Input และการตรวจ" · AC-06 |
| r4 | F39 | SizedLots (finite) และขอบเขตของ "Decimal ทุกตัว" ใน "Input และการตรวจ" |
| r4 | F40 | DoR status และ Status (นับ findings ทุกรอบ) |

## Authorization (filled by the owner)
- อนุมัติแทนโดย delegation 2026-10-24 (คำสั่งเจ้าของข้างบน) · veto ได้ก่อน merge · ผู้เขียน tests: patch ของ `tests/acceptance/CORE-007/**`, `tests/golden/CORE-007/**`, `tests/architecture/**` · Claude: implement, apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1–2 sessions · headless session ไม่เกิน 6 (tests, tests review, implementation review ×2, สำรอง ×2) · contract review ใช้ subagent · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง

## DoR status / missing items / next action
ครบ: H001, costs, risk, data.snapshot, contract v1.4 · ประวัติการตรวจ: r3 (`docs/reviews/CORE-007-contract-r3.md`) "Ready for test authoring: no" จนกว่าจะแก้ F33–F38 → v1.3 · r4 ตรวจแคบๆ (`docs/reviews/CORE-007-contract-r4.md`) ปิด F33–F38 พบ Low F39, F40 → v1.4 · r5 ตรวจแคบๆ (`docs/reviews/CORE-007-contract-r5.md`) ปิด F39, F40, findings open 0, **"Ready for test authoring: yes"** · (แก้ข้อความเดิมของ v1.3 ที่อ้างการตรวจแคบๆ ก่อนการตรวจนั้นเกิดขึ้น และสรุปผล r3 ผิด, r4 F40) · ขาด: CORE-006 implementation (ส่วน `run` ของ AC-02 ต้องใช้ decide จริง) · next: ผู้เขียน tests หลัง CORE-006 implement

## Done scope
merge แล้ว, suite เขียวใน CI
