# TASK CORE-007 — `backtest`: จำลองการเทรด H001 บนแท่ง bid พร้อมต้นทุน, SL ใน M1 และ R-multiple แบบ pure

Version v1.1 (v1 ร่าง 2026-10-24 07:xx → v1.1 08:xx ตอบ `docs/reviews/CORE-007-contract-r1.md` F1–F15 ทั้งหมด) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 7 (backtest: bid/ask fills, ambiguity labels), ข้อ 8 แถว `backtest`, ข้อ 10 แถว 2 (SLICE-R1) · H001 ข้อ 3, 6, 7, 8 · ต่อจาก CORE-005 (`Bar`, `AggregatedBar`) และ CORE-006 (`indicators`, `decide`) · Tier **Standard** · Branch `feat/CORE-007-backtest`
Status: **approved by delegation 2026-10-24** — เจ้าของสั่งในแชท Claude 2026-10-24 ~07:0x "ทำให้เสร็จทั้งหมดเลย" และ "มึงตัดสินไปเลย… เอา recommanded ทุกอัน" Claude จึงอนุมัติ acceptance และทางที่แนะนำทุกข้อแทน · ค่าทุกค่ามาจาก H001, SPIKE-001, CORE-002/003/005/006 ค่าใหม่ติดป้าย [A] · ผู้ตรวจอิสระอ่าน contract แทนเจ้าของ (r1: 15 findings → v1.1) และต้องผ่านอีกรอบก่อนเขียน tests · **เจ้าของ veto หรือแก้ acceptance ได้ทุกเมื่อก่อน merge**
Hypothesis (research tasks): H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`) · เขียน simulator เท่านั้น **ไม่รัน backtest กับข้อมูลจริง** (ห้ามก่อน ENV-1 และ SLICE-R1) · tests ใช้ข้อมูลสังเคราะห์

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no — จำลองเท่านั้น ไม่มีเส้นทางส่งคำสั่ง
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อกเข้า repo ผ่าน patch ตาม D-006

เป็น Standard เพราะทุกตัวเลขของ R1 (expectancy, drawdown, การเทียบกับการสุ่ม, การทดสอบต้นทุน 2×) มาจากโมดูลนี้

## Goal / user outcome (Thai)
มีโมดูล `sochron.backtest` ที่จำลองการเทรดของ H001 บนข้อมูลแท่งที่ตรวจแล้ว แล้วคืนรายการไม้ทุกไม้พร้อมเหตุผล ต้นทุน และ R-multiple โดย:
- ตัดสินใจที่ปิดแท่ง M15 t ด้วย `strategy.decide` แล้วทำคำสั่งที่ราคาเปิดของ M1 แท่งแรกของแท่ง M15 ถัดไป (H001 ข้อ 3)
- กำไรขาดทุนคิดจากราคา bid · spread, slippage, commission และ swap คิดผ่าน `costs.round_trip_cost` ครั้งเดียวต่อไม้
- มีฟังก์ชันระดับไม้ (`simulate_trade`) ที่ `run` ใช้ และงาน random-entry baseline (CORE-008) ใช้ได้ด้วยกติกา fill/SL/ต้นทุนเดียวกัน (F9)
- ทดสอบต้นทุน 2× ได้ด้วย `costs.stress(model, 2)` โดยราคาและกำไรขาดทุนก่อนต้นทุนไม่เปลี่ยน (F8)
- pure: ไม่มี I/O, นาฬิกา, สุ่ม · ไม่ดูข้อมูลอนาคต · import ตาม module map เดิม (ไม่แก้ architecture)

## Current behavior and evidence (revision)
มี `timebase`, `costs` (CORE-002/004), `risk` (CORE-003), `core.Bar` + `data.snapshot` (CORE-005 รอ merge) · `strategy` (CORE-006) กำลังเขียน tests · ไม่มี `backtest` · module map ข้อ 8: `backtest` import ได้เฉพาะ `core, timebase, strategy, costs` · `research` import `risk` ไม่ได้เช่นกัน

## Scope
- In scope: แพ็กเกจ `sochron.backtest` (`run`, `simulate_trade`, ชนิดข้อมูล) · unit tests · acceptance, golden และการขยาย architecture test ให้ครอบ `sochron.backtest` โดยผู้เขียน tests ผ่าน patch D-006 · หลักฐาน · handoff
- Exclusions: halt ของ risk (D5) · random-entry baseline, สถิติ, registry, รายงาน (CORE-008) · ตัวเชื่อม sizer จริง (ประกอบใน `app` ภายหลัง, F3) · การอ่านข้อมูลจริง · หลายสถานะพร้อมกัน · drawdown ระหว่างถือไม้ (F12 ข้อจำกัด)
- Allowed files: `src/sochron/backtest/**`, `tests/unit/backtest/**`, `docs/evidence/CORE-007.md`, `docs/handoff/CORE-007.md`, `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch: `tests/acceptance/CORE-007/**`, `tests/golden/CORE-007/**`, `tests/architecture/**`
- Must not touch: `src/sochron/{timebase,core,data,costs,risk,strategy}/**`, `docs/hypotheses/**`, `docs/architecture.md`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `research/**`, `pyproject.toml`, `uv.lock`

## Inputs / outputs / errors (contract)
ทุกตัวเลขเป็น `Decimal` คำนวณใน `sochron.costs.CONTEXT` (precision 28, ROUND_HALF_EVEN) · `stop_price` ไม่ปัด · ชนิดผิด (float, bool, subclass) → `TypeError` · ค่าผิดโดเมน → `BacktestError` (subclass ของ `ValueError`) · exception จาก sizer และจาก `costs` ส่งต่อโดยไม่ห่อ

```text
sochron.backtest
  BACKTEST_VERSION = "backtest-v1"
  Sizer = Callable[[Decimal, Decimal], SizedLots]          # (equity ณ เวลาเปิดไม้, stop_distance)
  SizedLots (frozen): lots: Decimal | None, risk_money: Decimal, actual_risk: Decimal | None, reason: str
      # lots None = ข้ามไม้ (reason เช่น "below_min_volume") · risk_money = R ตามสูตร (risk_per_trade × equity) > 0
  Rollover (frozen): zone: str, at: time                    # D4 [A]: Rollover("America/New_York", time(17, 0))
  Trade (frozen): side, entry_time_raw, entry_bid, entry_spread_points, exit_time_raw, exit_bid, exit_spread_points,
                  lots, stop_distance, stop_price, exit_reason: Literal["signal", "stop", "end_of_data"], ambiguous: bool,
                  nights: int, triple_nights: int, costs: CostBreakdown, gross_money, net_money,
                  risk_money, actual_risk, r: Decimal, data_flags: frozenset[str]
  Skip (frozen): time_raw: int, reasons: tuple[str, ...]
  Result (frozen): trades: tuple[Trade, ...], skips: tuple[Skip, ...], equity: tuple[tuple[int, Decimal], ...],
                   backtest_version: str, strategy_version: str
  simulate_trade(m1, entry_index, side, stop_distance, lots, model, rollover, exit_index=None,
                 risk_money, actual_risk) -> Trade               # ไม้เดียว: fill, SL, ต้นทุน (F9)
  run(m1: Sequence[Bar], m15: Sequence[<AggregatedBar-like>], params: H001Params, model: CostModel, sizer: Sizer,
      equity: Decimal, rule: TimeRule, rollover: Rollover) -> Result
```
แท่ง M15 รับแบบ duck typing (F4): แต่ละตัวต้องมี `.bar` เป็น `core.Bar` พอดี (timeframe 15) และ `.flags` เป็น `frozenset` ของ `str` · `sochron.backtest` ไม่ import `data.snapshot` (module map เดิม) · ใน R1 คือผลของ `data.snapshot.aggregate`

### กติกา fill และ SL (F6) — `s` = spread (points) ของ M1 ที่เกิดเหตุการณ์ ถ้าเป็น None ใช้ `model.spread_fallback_points` · `p` = `model.point`
| เหตุการณ์ | long | short |
|---|---|---|
| เข้าไม้ที่ open ของ M1 แรกของแท่ง t+1 | entry_bid = open · fill_ask = open + s·p · `stop_price` = fill_ask − stop_distance | entry_bid = open · `stop_price` = open + stop_distance (ระดับ ask) |
| SL แตะกลางแท่ง | bid low ≤ stop_price → exit_bid = stop_price | ask high = high + s·p ≥ stop_price → exit_bid = stop_price − s·p, exit_spread = s |
| แท่งเปิดเลย SL (gap) | open ≤ stop_price → exit_bid = open | open + s·p ≥ stop_price → exit_bid = open |
| ปิดตามสัญญาณที่ open ของ M1 แรกของแท่งถัดไป | exit_bid = open | exit_bid = open |
| ข้อมูลหมด | exit_bid = close ของ M1 สุดท้าย, exit_time = time_raw ของ M1 นั้น, spread ของ M1 นั้น | เหมือนกัน |
- per-bar spread ของ MT5 ใช้แทน spread ณ จังหวะ high/low เป็นค่า [A]
- `gross_money` = (exit_bid − entry_bid) × contract_size × lots × (+1 long / −1 short) **ไม่คูณ stress_factor** (F8)
- `costs` = `round_trip_cost(side, lots, entry_spread_points, exit_spread_points, nights, triple_nights, model)` · `net_money` = gross − costs.total
- `r` = `costs.r_multiple(net_money, risk_money)` โดย risk_money = R ตามสูตร H001 (0.25% × equity ณ เปิดไม้) · `actual_risk` เก็บไว้รายงาน · **ไม่ใช้ตัวอย่าง "+1.41 R" ของ H001 ที่หารด้วยความเสี่ยงจริงหลังปัด lot** (F2)

### ลำดับเหตุการณ์ต่อแท่ง M15 t (F7)
1. ถ้ามีไม้ถืออยู่: ตรวจ SL ทุก M1 ของแท่ง t ตามลำดับเวลา (สำหรับแท่งที่เข้าไม้ เริ่มที่ M1 ที่เข้าไม้ หลังราคาเปิด) · ถ้าโดน SL ไม้ปิด `stop` ที่ M1 นั้น
2. ที่ปิดแท่ง t (ถ้าไม่ใช่แท่งสุดท้าย): เรียก `decide(rows, t, position, next_open_utc, params)` โดย position คือสถานะหลังข้อ 1 (โดน SL ในแท่ง t แล้ว = flat จึงเข้าไม้ใหม่ที่ t+1 ได้) และ `next_open_utc` = `time_utc` ของแท่ง M15 ถัดไปที่มีอยู่จริง
3. `exit` → ปิดที่ open ของ M1 แรกของแท่ง t+1 · ถ้า open นั้นเลย SL ไปแล้ว: ปิด `stop` ราคาเดียวกัน (open) และ `ambiguous=True` (D3) · ไม้ที่โดน SL กลางแท่ง t แล้ว decide ให้ exit ไม่ใช่ ambiguous (ปิดไปแล้ว)
4. `enter_*` → sizer(equity ปัจจุบัน, stop_distance) · lots None → `Skip(time_raw ของแท่ง t, (reason ของ sizer,))` · ไม่เช่นนั้นเข้าไม้ที่ open ของ M1 แรกของแท่ง t+1 · ถ้า stop_distance ≤ spread ทำให้ open เลย SL ทันที ไม้ปิด `stop` ที่ open ของ M1 เดียวกัน (กติกา gap)
5. `skip` จาก decide → `Skip(time_raw ของแท่ง t, reasons ของ decide)` · `none`/`hold` ไม่บันทึก
6. แท่งสุดท้าย: ไม่เรียก decide · ไม้ที่ยังถืออยู่ปิด `end_of_data`
- equity points: จุดแรก (time_raw ของ M1 แรก, equity เริ่มต้น) แล้วหนึ่งจุดต่อการปิดไม้ (exit_time_raw, equity หลัง net) · เป็น realized curve (F12)
- `data_flags` ของไม้ = union ของ flags ของแท่ง M15 ตั้งแต่แท่งที่เข้าจนแท่งที่ปิด (F14)

### nights (D4 [A], F5)
nights = จำนวนเวลา T = `rollover.at` ตามเวลา `rollover.zone` บนวันจันทร์–ศุกร์ของ zone นั้น ที่ entry_time < T ≤ exit_time · triple_nights = จำนวน T ที่วันของ zone ตรง `model.triple_swap_weekday` · ตัวอย่าง: ศุกร์→จันทร์ (1, 0) · จันทร์→จันทร์ถัดไป (5, 1) · อังคาร→พฤหัส (2, 1) · การนับอยู่ใน backtest จนกว่าจะมีหลักฐานเวลา rollover ของโบรกเกอร์ แล้วจึงย้ายไป `timebase` ให้ E1 ใช้ร่วม (F13)

### ความสอดคล้องของ input (F11)
M1 เวลาเพิ่มขึ้นเคร่งครัด, timeframe 1 · M15 เวลาเพิ่มขึ้นเคร่งครัด, timeframe 15 · ทุก M1 อยู่ในแท่ง M15 ที่มีอยู่ (`timebase.bar_open(t, 15, rule)`) และทุกแท่ง M15 มี M1 อย่างน้อยหนึ่ง · ไม่ตรง → `BacktestError` · equity ≤ 0 → `BacktestError` · `SizedLots` ตรวจ: ชนิดพอดี, lots ผ่าน `costs.check_volume`, risk_money > 0

## Invariants
- ใช้ `strategy.decide` และ `costs` จริง ไม่เขียนกฎหรือสูตรต้นทุนซ้ำ · ถือได้ครั้งละหนึ่งสถานะ
- `run` และ `simulate_trade` ให้ไม้เดียวกันเมื่อจุดเข้า/ออกเดียวกัน (F9)
- ไม่มี look-ahead: ไม้, skip และ equity point ก่อนเวลา T ไม่เปลี่ยนเมื่อตัดหรือแก้ข้อมูลหลัง T
- pure, deterministic · import ได้เฉพาะ `core`, `timebase`, `strategy`, `costs` และ stdlib ที่ไม่ใช่ side effect

## Negative cases
gap เลย SL ทั้งสองฝั่ง · SL โดนใน M1 ที่เข้าไม้ · SL กลางแท่ง t แล้ว decide ให้ exit · exit ที่ open เลย SL (ambiguous) · stop_distance ≤ spread · spread ว่าง · sizer คืน None, คืน lots นอก grid · enter/exit ที่แท่งรองสุดท้าย · ข้อมูลหมดขณะถือ · ถือข้ามคืน/วันพุธ/สุดสัปดาห์/วันเปลี่ยน DST · M1/M15 ไม่สอดคล้อง · equity ≤ 0 · ชนิดผิดทุกช่อง

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given ตัวอย่าง H001 ข้อ 3 (long เข้า bid 4012.66 spread 240, stop_distance 12.00, sizer ให้ 0.02 lot R 25, ปิดตามสัญญาณที่ bid 4029.86 spread 240 ถือ 1 คืน) When `run` Then gross 34.40, ต้นทุน spread 0.48 / commission 0 / slippage 0.20 / swap 1.00760 / รวม 1.68760, net 32.71240, r 1.308496, stop_price 4000.90 (F1, F2) · และ short กลับด้าน (เข้า bid 4029.86, ปิด bid 4012.66, spread 240 ทั้งสองข้าง, 1 คืน) gross 34.40, spread 0.48 (ฝั่งปิด), slippage 0.20, swap 0, รวม 0.68000, net 33.72000, r 1.348800
- AC-02 Given ไม้ที่โดน SL แต่ละแบบในตาราง fill (long/short แตะกลางแท่ง, gap, M1 ที่เข้าไม้, stop_distance ≤ spread) และลำดับเหตุการณ์ (SL กลางแท่งแล้ว decide ให้ exit, exit ที่ open เลย SL, enter/exit ที่แท่งรองสุดท้าย, ข้อมูลหมด) When `run` Then exit_reason, exit_bid, exit_spread, เวลา และ ambiguous ตรงคำตอบที่คำนวณด้วยมือ
- AC-03 Given sizer ปลอมที่คืนขนาดต่างๆ, None, lots นอก grid และ input ที่ไม่สอดคล้องหรือผิดชนิด When `run` Then ใช้ lots ตามที่คืน, None → Skip พร้อมเหตุผล, lots ผิด → `BacktestError` หรือ error ของ costs, input ผิด → `BacktestError`/`TypeError` · sizer ได้ equity หลังไม้ก่อนหน้า · ไม่เปิดไม้ซ้อน
- AC-04 Given ไม้ที่ถือ ศุกร์→จันทร์, จันทร์→จันทร์ถัดไป, อังคาร→พฤหัส และข้ามวันเปลี่ยน DST When `run` Then nights/triple_nights = (1,0), (5,1), (2,1) และตามกติกาในวัน DST · และด้วย sizer lots คงที่ model กับ `stress(model, 2)` ให้ราคา, stop_price และ gross เท่ากันทุกไม้ ต้นทุนทุกส่วนเป็น 2× พอดี (F8)
- AC-05 Given ข้อมูลชุดหนึ่ง When ตัดหรือแก้ข้อมูลหลังเวลาปิดของไม้ k Then ไม้ 1..k, skip และ equity point ก่อนเวลานั้นเหมือนเดิม · และ `simulate_trade` ด้วยจุดเข้า/ออกของไม้ใดๆ ใน `run` ให้ Trade เดียวกัน (F9)
- AC-06 Given source ของ `sochron.backtest` When รัน architecture test Then ไม่มี I/O, นาฬิกา, สุ่ม, float, network และ import ได้เฉพาะ `core`, `timebase`, `strategy`, `costs` (ไม่ `data`, `risk`, `broker`, `execution`, `journal`, `research`) (F4)
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมด skipped 0 และ CI เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–05 | test author (acceptance + golden ที่คำนวณด้วยมือจาก contract นี้ ไม่ใช่จาก H001) | `uv run --offline pytest tests/acceptance/CORE-007 tests/golden/CORE-007 -q -p no:cacheprovider` | L2 |
| 06 | test author + reviewer | architecture test + mutation | L2 |
| 07 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยงหลัก: ผลวิจัยดีเกินจริงจาก fill/ต้นทุน/R ที่ผิด (F1, F2, F6, F8 ปิดด้วยตัวเลข golden) · ค่า [A]: เวลา rollover, การใช้ per-bar spread ณ จังหวะ high/low

## Plan, dependencies and unknowns (P06)
1. Understanding: simulator ที่ต่อ strategy + costs เข้ากับข้อมูลแท่ง · เข้าใจผิดที่เป็นไปได้: (ก) คิด spread สองครั้ง (ข) ใช้ risk หรือ data.snapshot ใน backtest (ค) ใส่ halt (ง) ใช้ points_to_money กับ gross (จ) หาร R ด้วยความเสี่ยงจริง
2. Files / reuse: `strategy.indicators/decide/STRATEGY_VERSION`, `costs.round_trip_cost/r_multiple/stress/check_volume/CONTEXT`, `timebase.to_zone/bar_open`
3. Steps: (1) CORE-006 พร้อม (2) contract review รอบ 2 (3) ผู้เขียน tests (4) apply + review → red (5) implement (6) review → PR
4. Decisions (อนุมัติแทนโดย delegation ตามทางที่แนะนำ):
   - **D1 sizing:** ผู้เรียกส่ง `sizer` · ตัวแปลงจาก `risk.size_position` (lots 0 → None พร้อม reason, risk_money = `SizeDecision.risk_money`, actual_risk = `SizeDecision.actual_risk`) ประกอบใน `app` ไม่แก้ module map (F3)
   - **D2 ราคา:** ตามตาราง fill (F6) · gross ไม่คูณ stress (F8)
   - **D3 ambiguous:** exit ที่ open เลย SL = `stop` + ambiguous ราคา open
   - **D4 nights [A]:** ตามหัวข้อ nights (F5)
   - **D5 halts:** ไม่ใช้ halt ของ risk (วัด edge; Demo จะต่างจาก backtest เมื่อ halt ทำงาน ให้ E1 บันทึก)
   - **D6 ข้อมูลหมด:** ปิดที่ close bid ของ M1 สุดท้าย
   - **D7 ผู้เขียน tests และผู้ตรวจ:** Claude session ใหม่ตามการสลับบทบาท
   - **D8 R:** หารด้วย R ตามสูตร ไม่ใช่ความเสี่ยงจริง (F2)
   - **D9 M15 input:** duck typing ไม่ import `data.snapshot` (F4)
   - **D10 drawdown:** realized curve · drawdown ระหว่างถือเป็นข้อจำกัดที่ R1 ต้องรายงาน (F12)

## Authorization (filled by the owner)
- อนุมัติแทนโดย delegation 2026-10-24 (คำสั่งเจ้าของข้างบน) · veto ได้ก่อน merge · ผู้เขียน tests: patch ของ `tests/acceptance/CORE-007/**`, `tests/golden/CORE-007/**`, `tests/architecture/**` · Claude: implement, apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1–2 sessions · headless session ไม่เกิน 6 (tests, tests review, implementation review ×2, สำรอง ×2) · contract review ใช้ subagent · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง

## DoR status / missing items / next action
ครบ: H001, costs, risk, data.snapshot, contract v1.1 · ขาด: CORE-006 implementation, contract review รอบ 2 · next: contract review รอบ 2

## Done scope
merge แล้ว, suite เขียวใน CI
