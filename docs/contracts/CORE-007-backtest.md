# TASK CORE-007 — `backtest`: จำลองการเทรด H001 บนแท่ง bid พร้อมต้นทุน, SL ใน M1 และ R-multiple แบบ pure

Version v1 (ร่าง 2026-10-24 07:xx) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 7 (backtest: bid/ask fills, ambiguity labels), ข้อ 8 แถว `backtest`, ข้อ 10 แถว 2 (SLICE-R1) · H001 ข้อ 3 (fill ที่ราคาเปิดแท่ง t+1, SL, ambiguous), ข้อ 6 (Costs) · ต่อจาก CORE-005 (`Bar`, `AggregatedBar`) และ CORE-006 (`indicators`, `decide`) · Tier **Standard** · Branch `feat/CORE-007-backtest`
Status: **approved by delegation 2026-10-24 07:xx** — เจ้าของสั่งในแชท Claude 2026-10-24 ~07:0x "ทำให้เสร็จทั้งหมดเลย" และ "มึงตัดสินไปเลย… เอา recommanded ทุกอัน" Claude จึงอนุมัติ acceptance และทางที่แนะนำ D1–D7 แทน · ทุกค่ามาจาก H001, SPIKE-001, CORE-002/003 ที่เจ้าของอนุมัติแล้ว ค่าใหม่ติดป้าย [A] · ผู้ตรวจอิสระอ่าน contract ก่อนเขียน tests · **เจ้าของ veto หรือแก้ acceptance ได้ทุกเมื่อก่อน merge**
Hypothesis (research tasks): H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`) · งานนี้เขียน simulator เท่านั้น **ไม่รัน backtest กับข้อมูลจริง** (ห้ามก่อน ENV-1 และ SLICE-R1) · tests ใช้ข้อมูลสังเคราะห์

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no — จำลองเท่านั้น ไม่มีเส้นทางส่งคำสั่ง
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อกเข้า repo ผ่าน patch ตาม D-006

เป็น Standard เพราะทุกตัวเลขของ R1 (expectancy, drawdown, การเทียบกับการสุ่ม) มาจากโมดูลนี้ ถ้า fill หรือต้นทุนผิด ผลวิจัยผิดทั้งหมด

## Goal / user outcome (Thai)
มีฟังก์ชัน `sochron.backtest.run(...)` ที่จำลองการเทรดของ strategy H001 บนข้อมูลแท่งที่ตรวจแล้ว แล้วคืนรายการไม้ทุกไม้พร้อมเหตุผล:
- ตัดสินใจที่ปิดแท่ง M15 t ด้วย `strategy.decide` แล้วทำคำสั่งที่**ราคาเปิดของ M1 แท่งแรกของแท่ง M15 ถัดไป** (H001 ข้อ 3)
- PnL คิดจากราคา bid · spread, slippage, commission และ swap คิดผ่าน `costs.round_trip_cost` ครั้งเดียวต่อไม้ (spread จ่ายฝั่งที่ซื้อ ตาม CORE-002) จึงไม่นับซ้ำ
- SL วางพร้อมเข้าไม้ และตรวจทุกแท่ง M1 ระหว่างถือ: long โดน SL เมื่อ bid low ≤ SL, short โดน SL เมื่อ ask high (= bid high + spread) ≥ SL · ถ้าแท่งเปิดเลย SL ไปแล้ว (gap) fill ที่ราคาเปิด
- ขนาดไม้มาจากฟังก์ชัน sizing ที่ผู้เรียกส่งเข้ามา (D1) ซึ่งใน R1 คือ `risk.size_position` ของ H001 · ไม้ที่ขนาดต่ำกว่าขั้นต่ำถูกข้ามพร้อมเหตุผล
- ผลต่อไม้มีเงินก่อน/หลังต้นทุน และ R-multiple · มีรายการไม้ที่ถูกข้ามและเหตุผล · equity curve หลังต้นทุน
- ทดสอบต้นทุน 2× ได้ด้วย `costs.stress(model, 2)` โดยไม่ต้องแก้ simulator
- pure: ไม่มี I/O, นาฬิกา, สุ่ม · ไม่ดูข้อมูลอนาคต

## Current behavior and evidence (revision)
ที่ branch นี้: มี `timebase`, `costs` (CORE-002/004), `risk` (CORE-003), `core.Bar` + `data.snapshot` (CORE-005) · `strategy` (CORE-006) กำลังทำ · ยังไม่มี `backtest` · module map ข้อ 8: `backtest` import ได้เฉพาะ `core, timebase, strategy, costs` (ไม่รวม `risk`)

## Scope
- In scope: แพ็กเกจ `sochron.backtest` · unit tests · acceptance, golden และการขยาย architecture test ให้ครอบ `sochron.backtest` (ห้าม I/O, นาฬิกา, สุ่ม, float, `MetaTrader5`, network และห้าม import `risk`, `broker`, `data.acquire`, `execution`, `journal`, `research`) โดยผู้เขียน tests ผ่าน patch D-006 · หลักฐาน · handoff
- Exclusions: halt รายวัน/การทดลองของ risk (เป็นการจัดการความเสี่ยงของ Demo ไม่ใช่การวัด edge; D5) · random-entry baseline, สถิติ, registry และรายงาน (CORE-008) · การอ่านข้อมูลจริง · หลายสถานะพร้อมกัน (H001 ถือได้ครั้งละหนึ่ง)
- Allowed files: `src/sochron/backtest/**`, `tests/unit/backtest/**`, `docs/evidence/CORE-007.md`, `docs/handoff/CORE-007.md`, `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch: `tests/acceptance/CORE-007/**`, `tests/golden/CORE-007/**`, `tests/architecture/**`
- Must not touch: `src/sochron/{timebase,core,data,costs,risk,strategy}/**`, `docs/hypotheses/**`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `research/**`, `pyproject.toml`, `uv.lock`

## Inputs / outputs / errors (contract)
```text
sochron.backtest
  Sizer = Callable[[Decimal, Decimal], SizedLots]      # (equity, stop_distance) -> lots และ R ที่ใช้
  SizedLots (frozen): lots: Decimal | None, risk_money: Decimal, reason: str   # lots None = ข้ามไม้ (เช่น below_min_volume)
  Trade (frozen): side, entry_time_raw, entry_bid, exit_time_raw, exit_bid, lots, stop_distance, stop_price,
                  exit_reason: Literal["signal", "stop", "end_of_data"], ambiguous: bool,
                  nights: int, triple_nights: int, costs: CostBreakdown,
                  gross_money, net_money, risk_money, r: Decimal
  Skip (frozen): time_raw, reasons: tuple[str, ...]      # decide() ให้ skip หรือ sizer ให้ lots None
  Result (frozen): trades: tuple[Trade, ...], skips: tuple[Skip, ...], equity: tuple[(time_raw, Decimal), ...], version: str
  run(m1: Sequence[Bar], m15: Sequence[AggregatedBar], params: H001Params, model: CostModel, sizer: Sizer,
      equity: Decimal, rule: TimeRule, calendar: ClosureCalendar) -> Result
```
กติกา (H001 ข้อ 3, 6 แปลตรงตัว + การตัดสิน D1–D7):
- เข้าไม้: `decide` ที่แท่ง t คืน `enter_*` → fill ที่ open (bid) ของ M1 แท่งแรกของแท่ง M15 t+1 · SL long = fill_ask − stop_distance เมื่อ fill_ask = bid + spread × point · SL short = fill_bid + stop_distance
- ปิดตามสัญญาณ: `decide` คืน `exit` → fill ที่ open ของ M1 แรกของแท่งถัดไป
- SL: ตรวจทุก M1 ตั้งแต่ M1 ที่เข้าไม้ (หลังราคาเปิด) จนก่อนการปิดตามสัญญาณ · fill ที่ระดับ SL หรือที่ราคาเปิดถ้า gap เลย SL
- ambiguous (D3): ถ้า M1 ที่ต้องปิดตามสัญญาณเปิดเลย SL ไปแล้ว นับเป็น `stop` และติด `ambiguous=True` (เลือกทางที่แย่กว่า ตาม H001)
- ต้นทุน: `round_trip_cost(side, lots, entry_spread, exit_spread, nights, triple_nights, model)` · spread ของ fill = spread ของ M1 ที่ fill (None → fallback ของ model)
- nights (D4 [A]): จำนวนครั้งที่ผ่านเวลา 17:00 New York (ต้นช่วงพักรายวันของปฏิทิน) ระหว่างถือ · triple = ครั้งที่ตรงวัน `model.triple_swap_weekday`
- R: `r = net_money / risk_money` ผ่าน `costs.r_multiple`
- ข้อมูลหมด: ปิดที่ราคาปิด (bid) ของ M1 แท่งสุดท้าย `end_of_data`
- equity: เริ่มจาก `equity` และปรับด้วย `net_money` หลังปิดแต่ละไม้ · sizer ได้ equity ณ เวลาเปิดไม้

## Invariants
- ใช้ `strategy.decide` และ `costs` จริง ไม่เขียนกฎหรือสูตรต้นทุนซ้ำ · ถือได้ครั้งละหนึ่งสถานะ
- ไม่มี look-ahead: ไม้ที่ปิดก่อนเวลา T ไม่เปลี่ยนเมื่อตัดข้อมูลหลัง T ทิ้ง
- pure, deterministic, Decimal เท่านั้น · import ตาม module map (ไม่ import `risk`)

## Negative cases
gap เปิดเลย SL ทั้งสองฝั่ง · SL โดนใน M1 ที่เข้าไม้ · สัญญาณปิดกับ SL ในแท่งเดียวกัน · spread ว่าง · sizer คืน None · ข้อมูลหมดขณะถือ · ถือข้ามคืน/ข้ามวันพุธ/ข้ามสุดสัปดาห์ · DST change ระหว่างถือ · m1 ไม่ตรงกับ m15 (เวลาไม่ครอบ) → `ValueError` · ชนิดผิดทุกช่อง

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given ตัวอย่างใน H001 ข้อ 3 (เข้า long bid 4012.66 spread 240 → ซื้อ 4012.90, SL 4000.90, lots 0.02, ปิด bid 4029.86 ถือ 1 คืน) When `run` Then gross, ต้นทุนแต่ละส่วน, net และ R ตรงคำตอบที่คำนวณด้วยมือ (net ก่อน swap = +33.92 ตาม H001) และ short ที่กลับด้านให้ผลสมมาตร
- AC-02 Given ไม้ที่ราคาแตะ SL ใน M1 ต่างๆ (กลางแท่ง, M1 ที่เข้าไม้, gap เลย SL, ฝั่ง short ผ่าน ask) When `run` Then ปิด `stop` ที่ราคาที่กำหนดและเวลา M1 ที่ถูกต้อง · กรณีสัญญาณปิดกับ SL ชนกันได้ `stop` + `ambiguous`
- AC-03 Given sizer ที่คืนขนาดต่างๆ รวม None When `run` Then ใช้ lots ตามที่คืน, ไม้ที่ None ถูกข้ามพร้อมเหตุผล, ไม่เปิดไม้ซ้อน และ sizer ได้ equity หลังไม้ก่อนหน้า
- AC-04 Given ไม้ที่ถือข้ามคืน ข้ามวันพุธ ข้ามสุดสัปดาห์ และข้ามวันเปลี่ยน DST When `run` Then nights/triple_nights ตามกติกา D4 และต้นทุนเท่ากับ `round_trip_cost` · model ที่ stress ×2 ให้ต้นทุนสองเท่าทุกส่วน
- AC-05 Given ข้อมูลชุดหนึ่ง When ตัดหรือแก้ข้อมูลหลังเวลาปิดของไม้ k Then ไม้ 1..k เหมือนเดิมทุกค่า · ผลซ้ำได้เหมือนเดิม
- AC-06 Given source ของ `sochron.backtest` When รัน architecture test Then ไม่มี I/O, นาฬิกา, สุ่ม, float, network และไม่ import `risk`, `broker`, `data.acquire`, `execution`, `journal`, `research`
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมด skipped 0 และ CI เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–05 | test author (acceptance + golden ที่คำนวณด้วยมือ) | `uv run --offline pytest tests/acceptance/CORE-007 tests/golden/CORE-007 -q -p no:cacheprovider` | L2 |
| 06 | test author + reviewer | architecture test + mutation | L2 |
| 07 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |

## Plan, dependencies and unknowns (P06)
1. Understanding: simulator ที่ต่อ strategy + costs เข้ากับข้อมูลแท่ง · เข้าใจผิดที่เป็นไปได้: (ก) คิด spread สองครั้ง (ในราคา ask และใน costs) — ไม่ PnL คิดจาก bid (ข) ใช้ risk ใน backtest โดยตรง — ไม่ ผ่าน sizer (ค) ใส่ halt ของ risk — ไม่ (D5)
2. Files / reuse: `strategy.indicators/decide`, `costs.round_trip_cost/r_multiple/stress`, `timebase.to_zone`, `data.snapshot.ClosureCalendar`
3. Steps: (1) CORE-006 พร้อม (2) ผู้ตรวจอิสระอ่าน contract (3) ผู้เขียน tests (4) apply + review → red (5) implement (6) review → PR
4. Risks: ดูข้างบน
5. Decisions (อนุมัติแทนโดย delegation ตามทางที่แนะนำ):
   - **D1 sizing:** ผู้เรียกส่ง `sizer` เข้ามา (R1 ส่ง `risk.size_position` ของ H001) เพื่อไม่ต้องแก้ module map
   - **D2 ราคา:** PnL จาก bid · ask = bid + spread × point ใช้เฉพาะตรวจ SL ของ short และคำนวณ SL long · spread คิดใน `round_trip_cost` ครั้งเดียว
   - **D3 ambiguous:** ปิดตามสัญญาณที่ open ของ M1 ที่เปิดเลย SL = `stop` + ambiguous
   - **D4 nights [A]:** rollover ที่ 17:00 New York ของปฏิทิน · triple ตาม `model.triple_swap_weekday` · สถานะ assumed จนกว่า R1 ยืนยันเวลา rollover ของโบรกเกอร์
   - **D5 halts:** backtest ไม่ใช้ halt ของ risk (วัด edge ไม่ใช่จัดการเงิน)
   - **D6 ข้อมูลหมด:** ปิดที่ close bid ของ M1 สุดท้าย `end_of_data`
   - **D7 ผู้เขียน tests และผู้ตรวจ:** Claude session ใหม่ตามการสลับบทบาท

## Authorization (filled by the owner)
- อนุมัติแทนโดย delegation 2026-10-24 07:xx (คำสั่งเจ้าของข้างบน) · veto ได้ก่อน merge · ผู้เขียน tests: patch ของ `tests/acceptance/CORE-007/**`, `tests/golden/CORE-007/**`, `tests/architecture/**` · Claude: implement, apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1–2 sessions · headless session ไม่เกิน 6 (contract review, tests, tests review, implementation review ×2, สำรอง) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง

## DoR status / missing items / next action
ครบ: H001, costs, risk, data.snapshot · ขาด: CORE-006 merge หรือพร้อมบน branch, contract review · next: contract review

## Done scope
merge แล้ว, suite เขียวใน CI
