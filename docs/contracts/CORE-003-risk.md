# TASK CORE-003 — risk: sizing, halt state และ risk gate แบบ pure (ค่า risk policy เป็น parameter ที่มีที่มา)

Version v1 · Owner เจ้าของ repository · Parent SPEC ข้อ 6 (Risk policy [A]) และ Q-04 · `docs/architecture.md` ข้อ 8 แถว `risk`, ข้อ 9 ("ไม่มีคำสั่งไหนถูกส่งโดยไม่ผ่าน risk gate") และข้อ 13a แถว E1 · AGENTS.md "Trading and research invariants" · Tier **Standard** · Branch `feat/CORE-003-risk`
Status: draft (รอเจ้าของอนุมัติ acceptance 7 ข้อ) · เจ้าของเลือกเมื่อ 2026-10-22 ให้ร่างแบบรับค่าเป็น parameter ติดป้าย assumed ไปก่อน แทนการรอคำตอบ Q-04
Hypothesis (research tasks): ไม่ใช่งานวิจัย แต่ให้บริการ H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`, commit `0c392a9`) ข้อ 3 Position size และ "1 สถานะต่อครั้ง" · ไม่มีการรันข้อมูลตลาด

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no — โค้ด pure ไม่แตะสิทธิ์ ไม่เชื่อมต่ออะไร (การปลด halt ตรวจแค่ชื่อผู้ปลดที่ส่งมา ไม่ใช่ระบบยืนยันตัวตน)
- Q2 real money: no — ไม่มีเส้นทางส่งคำสั่ง; โมดูลนี้ตัดสิน "อนุญาต/ไม่อนุญาต" เท่านั้น
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อกเขียนโดย Codex และเข้า repo ผ่าน patch ใน `docs/proposals/` ตาม D-006 เหมือน CORE-001/002

เป็น Standard เพราะเป็นด่าน risk ที่ AGENTS.md กำหนดว่าต้องเป็นโค้ด deterministic นอกอำนาจ AI และจะอยู่หน้าทุกคำสั่งใน E1 · ถ้า sizing หรือ halt ผิด ทั้ง backtest ของ H001 และ Demo จะเสี่ยงเกินกำหนด

## Goal / user outcome (Thai)
มีโมดูลเดียวชื่อ `sochron.risk` ที่ backtest (R1) และ execution (E1) ใช้ตัดสินเรื่องความเสี่ยงแบบเดียวกัน โดย:
- **คำนวณขนาด lots** ตามสูตรของ H001: `R = risk_per_trade × equity`, `lots = floor_step( R / (ระยะ SL × contract_size + cost_per_lot) )` · ต่ำกว่า volume ขั้นต่ำ → ไม่เปิดไม้ พร้อมเหตุผล `below_min_volume` · เกิน volume สูงสุด → จำกัดที่ค่าสูงสุด · `cost_per_lot` เริ่มต้น 0 ให้ตรงสูตรที่ลงทะเบียนใน H001 และเปิดทางให้ SPEC "รวม cost budget" ใช้ได้ใน contract ที่ต้องการ
- **halt state**: หยุดรายวันเมื่อขาดทุนถึง 0.75% ของ equity ต้นวันไทย (ปลดเองเมื่อขึ้นวันไทยใหม่) และหยุดการทดลองเมื่อขาดทุนถึง 2% ของ equity ตั้งต้น (ไม่ปลดเอง ต้องเริ่มการทดลองใหม่โดยผู้มีสิทธิ์พร้อมเหตุผล)
- **risk gate ก่อนเปิดไม้**: ตอบว่าอนุญาตหรือไม่ พร้อมทุกเหตุผลที่ไม่อนุญาต (halt, มี position หรือ pending ครบจำนวนแล้ว, ไม่มี SL หรือ SL ผิดฝั่ง, lots มากกว่าที่ sizing ให้ หรือไม่ตรง step)
- **gate ของการแก้ SL**: ห้ามขยาย SL และห้ามเอา SL ออก (AGENTS.md: never widen a stop loss) · ขยับเข้าใกล้ราคาได้
- **ค่า policy ทุกตัวเป็น parameter ที่มีที่มา** (`Provenance` เดียวกับ costs) · `H001_RISK` ใช้ค่า [A] จาก SPEC ข้อ 6 ทั้งหมด ติดสถานะ `assumed` จนกว่าเจ้าของตอบ Q-04 · policy แก้ไม่ได้ระหว่างรัน (frozen)
- เงินและ lots เป็น `Decimal` · ไม่มี I/O ไม่อ่านนาฬิกา ไม่ import `MetaTrader5` · วันไทยรับเป็น `date` จากผู้เรียก (คำนวณด้วย `timebase.bangkok_date` ที่ฝั่งผู้เรียก เพราะ module map ให้ `risk` import ได้เฉพาะ `core` และ `costs`)

## Current behavior and evidence (revision)
ที่ `feat/CORE-002-costs` (`47151e8`, รอ merge): มี `sochron.timebase` และ `sochron.costs` · ไม่มีโค้ด risk · ค่า risk อยู่ใน SPEC ข้อ 6 เป็น [A] (0.25% ต่อเทรดรวม cost budget, หยุดรายวัน 0.75% จาก baseline วันไทย, หยุดการทดลอง 2% จากทุนตั้งต้น, position หรือ pending ได้ครั้งละ 1) และ Q-04 ยังเปิด (รวม "ใครปลด halt ได้") · สูตร sizing และ worked example อยู่ใน H001 ข้อ 3 (equity 10,000 → R 25, ระยะ SL 12.00 → 0.02 lots, เสี่ยงจริง 24 USD) · H001 ข้อ 3 ไม่รวมต้นทุนในสูตร sizing ซึ่งต่างจาก SPEC ข้อ 6 ที่เขียนว่า "รวม cost budget" → contract นี้ทำให้ทั้งสองแบบเป็นไปได้ผ่าน `cost_per_lot` และให้ contract ที่ใช้งาน (R1, E1) เป็นผู้เลือก

## Scope
- In scope: แพ็กเกจ `sochron.risk` ตาม API ด้านล่าง · unit tests ของผู้ทำ · acceptance, golden และ architecture tests โดย Codex (ขยาย `tests/architecture/test_imports.py` ให้ครอบ `sochron.risk`) · หลักฐานใน `docs/evidence/CORE-003.md` · handoff
- Exclusions: การส่งหรือแก้คำสั่งจริง (E1) · journal และการบันทึก halt ลงดิสก์ (E1/journal) · การยืนยันตัวตนผู้ปลด halt (โมดูลนี้ตรวจแค่ชื่อที่ส่งมาเทียบ policy) · การคำนวณวันไทยจากเวลา (ผู้เรียกใช้ `timebase`) · การคำนวณ PnL และ equity (ผู้เรียกส่ง equity มา) · การเลือกว่า R1/E1 จะใช้ `cost_per_lot` เท่าไร (อยู่ใน contract นั้น) · การเปลี่ยน policy ระหว่างรัน
- Allowed files/modules: `src/sochron/risk/**`, `tests/unit/risk/**`, `docs/evidence/CORE-003.md`, `docs/handoff/CORE-003.md`, `PROGRESS.md` · โดย Codex ผ่าน patch: `tests/acceptance/CORE-003/**`, `tests/golden/CORE-003/**`, `tests/architecture/**`
- Must not touch: `src/sochron/timebase/**`, `src/sochron/costs/**`, `src/sochron/core/**`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`, `docs/hypotheses/**`, `research/**`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests (เปลี่ยนไม่ได้โดยผู้ทำ) · ทุกฟังก์ชันเป็น pure · เงิน, lots, ราคา และสัดส่วนเป็น `decimal.Decimal` เท่านั้น · จำนวนนับเป็น `int` · ชนิดผิดทุกตำแหน่ง (รวม `float` และ `bool`) → `TypeError` ไม่มีการแปลงค่าอัตโนมัติ · ตัวเลขในข้อความเป็นค่าเชิงคณิตศาสตร์; ใน API และ golden tests สร้างจาก Decimal string เสมอ · การคำนวณใช้ `sochron.costs.CONTEXT` (precision 28, ROUND_HALF_EVEN) ไม่ขึ้นกับ context ของผู้เรียก · **การ floor ของ lots และการเทียบเกณฑ์ขาดทุนต้องแม่นยำแบบตรรกยะ** (ไม่ปัดก่อน floor และไม่ปัดก่อนเทียบ) เพื่อไม่ให้ค่าที่ขอบพอดีพลาดเพราะการปัด

```text
sochron.risk
  RiskPolicy (frozen dataclass):
      risk_per_trade: Decimal            # สัดส่วนของ equity ต่อเทรด, 0 < x < 1
      daily_loss_limit: Decimal          # สัดส่วนของ equity ต้นวันไทย, 0 < x < 1
      experiment_loss_limit: Decimal     # สัดส่วนของ equity ตั้งต้นการทดลอง, 0 < x < 1
      max_open_exposures: int            # จำนวน position + pending order สูงสุด, ≥ 1
      halt_clearers: tuple[str, ...]     # ชื่อผู้มีสิทธิ์เริ่มการทดลองใหม่หลัง experiment halt, ไม่ว่าง, แต่ละชื่อไม่ว่าง
      provenance: Mapping[str, Provenance]   # Provenance จาก sochron.costs · key = 5 ฟิลด์ข้างบนพอดี · เก็บเป็นสำเนา immutable
      → ตรวจตอนสร้าง: ชนิดผิด → TypeError · โดเมนผิด → BadPolicy · provenance ขาด/เกิน key หรือค่าไม่ใช่ Provenance → BadPolicy
  H001_RISK: RiskPolicy        # ค่าและ provenance ตามตารางด้านล่าง
  unknowns(policy: RiskPolicy) -> tuple[str, ...]   # ชื่อฟิลด์ที่ status เป็น assumed หรือ unknown เรียงตามตัวอักษร

  SizeDecision (frozen dataclass): lots: Decimal, risk_money: Decimal, risk_per_lot: Decimal, actual_risk: Decimal, reason: Literal["ok", "below_min_volume", "capped_at_volume_max"]
  size_position(equity: Decimal, stop_distance: Decimal, model: CostModel, policy: RiskPolicy, cost_per_lot: Decimal = Decimal("0")) -> SizeDecision
      # risk_money = policy.risk_per_trade × equity
      # risk_per_lot = stop_distance × model.contract_size + cost_per_lot          (USD ต่อ 1 lot; stop_distance หน่วยราคา USD/oz)
      # raw = risk_money ÷ risk_per_lot (ตรรกยะ) · lots = floor(raw ÷ model.volume_step) × model.volume_step (floor แบบ exact)
      # lots < model.volume_min → lots = Decimal("0"), reason "below_min_volume"
      # lots > model.volume_max → lots = model.volume_max, reason "capped_at_volume_max" · อื่นๆ reason "ok"
      # actual_risk = lots × risk_per_lot
      # equity ≤ 0 → BadEquity · stop_distance ≤ 0 → BadStop · cost_per_lot < 0 → BadPolicy · ค่าไม่ finite → error ตามช่องเดียวกัน
      # model เป็น CostModel ของ sochron.costs (ใช้ contract_size, volume_min/step/max) · ไม่ใช้ stress_factor ของ model

  HaltState (frozen dataclass): day: date, day_start_equity: Decimal, experiment_start_equity: Decimal,
                                daily_halted: bool, experiment_halted: bool
  start_experiment(equity: Decimal, day: date) -> HaltState          # ไม่ halt ทั้งคู่ · baseline ทั้งสองเท่ากับ equity
  update_equity(state: HaltState, equity: Decimal, day: date, policy: RiskPolicy) -> HaltState
      # day < state.day → TimeReversal (ข้อมูลผิดลำดับ: รายงาน ไม่ซ่อม)
      # day > state.day → วันไทยใหม่: day = day, day_start_equity = equity, daily_halted = False (ประเมินใหม่ด้วย equity นี้)
      # daily_halted = daily_halted or (state.day_start_equity − equity) ≥ policy.daily_loss_limit × day_start_equity   (exact, รวมค่าเท่ากับเกณฑ์)
      # experiment_halted = experiment_halted or (experiment_start_equity − equity) ≥ policy.experiment_loss_limit × experiment_start_equity  (ติดค้าง ไม่ปลดเอง)
      # equity ≤ 0 → BadEquity
  restart_experiment(state: HaltState, equity: Decimal, day: date, authorized_by: str, reason: str, policy: RiskPolicy) -> HaltState
      # authorized_by ไม่อยู่ใน policy.halt_clearers → BadHaltClear · reason ว่าง (หลังตัดช่องว่าง) → BadHaltClear
      # day < state.day → TimeReversal · ผล: เหมือน start_experiment(equity, day)
      # ใช้ได้ทั้งตอน halt และไม่ halt (เป็นการเริ่มการทดลองใหม่ที่ต้องมีผู้อนุมัติ)

  EntryRequest (frozen dataclass): side: Literal["long", "short"], lots: Decimal, entry_price: Decimal, stop_loss: Decimal | None, open_exposures: int
  GateDecision (frozen dataclass): allowed: bool, reasons: tuple[str, ...]      # allowed == (reasons == ()) เสมอ; reasons เรียงตามตัวอักษรไม่ซ้ำ
  check_entry(request: EntryRequest, state: HaltState, sized: SizeDecision, model: CostModel, policy: RiskPolicy) -> GateDecision
      # เหตุผลที่เป็นไปได้ (ทุกข้อที่เข้าเงื่อนไข):
      #   "daily_halt" ถ้า state.daily_halted · "experiment_halt" ถ้า state.experiment_halted
      #   "max_exposure" ถ้า request.open_exposures ≥ policy.max_open_exposures
      #   "missing_stop_loss" ถ้า stop_loss is None
      #   "stop_loss_wrong_side" ถ้า long และ stop_loss ≥ entry_price หรือ short และ stop_loss ≤ entry_price
      #   "below_min_volume" ถ้า sized.reason == "below_min_volume"
      #   "lots_exceed_sized" ถ้า request.lots > sized.lots
      #   "lots_not_on_grid" ถ้า request.lots ≤ 0 หรือไม่ผ่าน sochron.costs.check_volume
      # ชนิดผิดใน request → TypeError ตอนสร้าง EntryRequest · open_exposures < 0 หรือ entry_price ≤ 0 หรือ stop_loss ≤ 0 → BadStop/RiskError ตามตาราง
  check_stop_change(side: Literal["long", "short"], current_stop: Decimal, new_stop: Decimal | None) -> GateDecision
      # new_stop is None → ("missing_stop_loss",) · long และ new_stop < current_stop → ("stop_loss_widened",)
      # short และ new_stop > current_stop → ("stop_loss_widened",) · เท่าเดิมหรือขยับเข้าหาราคา → allowed
  errors (ทั้งหมดสืบจาก RiskError(ValueError)): BadPolicy · BadEquity · BadStop · BadHaltClear · TimeReversal
```

ค่าของ `H001_RISK` (ต้องตรงทุกตัว):

| ฟิลด์ | ค่า | provenance (source · as_of · status) |
|---|---|---|
| risk_per_trade | 0.0025 | SPEC ข้อ 6 Risk policy [A] และ H001 ข้อ 3 · 2026-10-21 · assumed (note: Q-04 open) |
| daily_loss_limit | 0.0075 | SPEC ข้อ 6 Risk policy [A] · 2026-10-21 · assumed (note: Q-04 open; baseline = equity ต้นวันไทย) |
| experiment_loss_limit | 0.02 | SPEC ข้อ 6 Risk policy [A] · 2026-10-21 · assumed (note: Q-04 open) |
| max_open_exposures | 1 | SPEC ข้อ 6 "position หรือ pending ได้ครั้งละ 1" [A] และ H001 ข้อ 3 "1 สถานะต่อครั้ง" · 2026-10-21 · assumed |
| halt_clearers | ("owner",) | SPEC Q-04 "ใครปลดล็อก halt ได้" ยังเปิด · 2026-10-22 · unknown (note: ค่าตั้งต้นที่ปลอดภัย: เจ้าของคนเดียว; agent ไม่มีสิทธิ์) |

ดังนั้น `unknowns(H001_RISK) == ("daily_loss_limit", "experiment_loss_limit", "halt_clearers", "max_open_exposures", "risk_per_trade")`

## Invariants
- risk policy เป็น frozen; ไม่มีฟังก์ชันใดแก้ policy หรือ HaltState เดิม (คืนค่าใหม่เสมอ) · ไม่มีเส้นทางเพิ่ม risk_per_trade ตามผลขาดทุน (ห้าม martingale): sizing ขึ้นกับ equity ปัจจุบันและ policy เท่านั้น
- experiment halt ไม่ปลดเองไม่ว่าวันจะเปลี่ยนหรือ equity จะกลับมา · มีทางเดียวคือ `restart_experiment` ที่ต้องมีชื่ออยู่ใน `halt_clearers` และเหตุผลที่ไม่ว่าง · `H001_RISK.halt_clearers` ไม่มี agent ใด
- ไม่มี float ในโค้ดเงิน (AST test: ไม่มีชื่อ `float` หรือ float literal ใน `src/sochron/risk`) · import ได้เฉพาะ stdlib, `sochron.core`, `sochron.costs` · ไม่มี I/O, นาฬิกา, `MetaTrader5`, random
- ตรวจสอบได้ด้วยมือจาก H001 ข้อ 3: `size_position(Decimal("10000"), Decimal("12.00"), H001_COSTS, H001_RISK)` → lots `0.02`, risk_money `25`, risk_per_lot `1200`, actual_risk `24`, reason `ok`
- ไม่มี `.skip`, `xfail` หรือ test ที่อ่อนลงใน tests ที่ล็อก · ไม่มี dependency ใหม่

## Negative cases
- sizing: equity 0 หรือ −1 → `BadEquity` · stop_distance 0 → `BadStop` · cost_per_lot −1 → `BadPolicy` · float ทุกตำแหน่ง → `TypeError` · equity 100 กับ stop 12.00 → R 0.25, raw 0.000208…, lots 0 → `below_min_volume` · equity 100,000,000 กับ stop 0.10 → cap ที่ 200 lots (`capped_at_volume_max`) · ค่าที่ floor พอดีขอบ step (raw = 0.02 พอดี) ต้องได้ 0.02 ไม่ใช่ 0.01
- halt รายวัน: baseline 10,000 · equity 9,925.01 → ยังไม่ halt · 9,925 พอดี (ขาดทุน 75 = 0.75%) → halt · วันไทยถัดไปที่ equity 9,925 → ปลด daily halt, baseline ใหม่ 9,925 · day ย้อนหลัง → `TimeReversal`
- halt การทดลอง: start 10,000 · equity 9,800 พอดี (2%) → halt และคงอยู่ข้ามวันแม้ equity กลับมา 10,500 · `restart_experiment` โดย `"claude"` หรือ `"codex"` หรือ `""` → `BadHaltClear` · โดย `"owner"` แต่ reason `"  "` → `BadHaltClear` · โดย `"owner"` พร้อมเหตุผล → state ใหม่ไม่ halt baseline = equity ที่ส่งมา
- gate: ทุกเหตุผลทีละข้อ และหลายเหตุผลพร้อมกัน (เรียงตามตัวอักษร) · request.lots 0.015 → `lots_not_on_grid` · request.lots 0 → `lots_not_on_grid` · SL เท่าราคาเข้า → `stop_loss_wrong_side`
- แก้ SL: long 4000.90 → 4001.00 อนุญาต · → 4000.00 `stop_loss_widened` · → None `missing_stop_loss` · short กลับทิศ
- policy: risk_per_trade 0 หรือ 1 → `BadPolicy` · max_open_exposures 0 → `BadPolicy` · halt_clearers ว่าง หรือมีชื่อว่าง → `BadPolicy` · provenance ขาด key → `BadPolicy`

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given `H001_COSTS` และ `H001_RISK`, When เรียก `size_position(Decimal("10000"), Decimal("12.00"), H001_COSTS, H001_RISK)`, Then ได้ lots `0.02`, risk_money `25`, risk_per_lot `1200`, actual_risk `24`, reason `"ok"` (ตรง H001 ข้อ 3) · ด้วย `cost_per_lot=Decimal("10")` ได้ risk_per_lot `1210` lots `0.02` actual_risk `24.20` · equity `100` → lots `0` reason `"below_min_volume"` · equity `100000000` stop `0.10` → lots `200` reason `"capped_at_volume_max"` · กรณี raw เท่ากับ 0.02 พอดี (equity `9600`, stop `12.00` → R 24, raw 0.02) ได้ lots `0.02`
- AC-02 Given `start_experiment(Decimal("10000"), date(2026, 10, 22))`, When `update_equity` ด้วย 9925.01 แล้ว 9925 ในวันเดียวกัน แล้ว 9925 ในวันถัดไป, Then daily_halted เป็น False, True, False ตามลำดับ และ day_start_equity ของวันใหม่ = 9925 · `update_equity` ด้วยวันที่ย้อนหลัง → `TimeReversal`
- AC-03 Given การทดลองเริ่มที่ 10000, When equity ลงไป 9800 แล้วกลับเป็น 10500 ในวันถัดไป, Then experiment_halted เป็น True และยังเป็น True หลังกลับขึ้น · `restart_experiment` โดย `"claude"`, `"codex"` หรือ reason ว่าง → `BadHaltClear` · โดย `"owner"` พร้อมเหตุผล → HaltState ใหม่ที่ไม่ halt และ baseline ทั้งสอง = equity ที่ส่งมา
- AC-04 Given HaltState ที่ไม่ halt, sizing ของ AC-01 (0.02 lots) และ EntryRequest long lots 0.02 entry 4012.90 SL 4000.90 open_exposures 0, When `check_entry`, Then allowed True reasons `()` · เปลี่ยนทีละเงื่อนไขได้เหตุผล `daily_halt`, `experiment_halt`, `max_exposure` (open_exposures 1), `missing_stop_loss`, `stop_loss_wrong_side` (SL 4012.90 หรือ 4013.00 สำหรับ long), `lots_exceed_sized` (0.03), `lots_not_on_grid` (0.015 และ 0) · เปลี่ยน sized เป็นผลของ equity 100 (lots 0) ได้ `("below_min_volume", "lots_exceed_sized")` เพราะ request 0.02 > 0 · เมื่อหลายข้อพร้อมกันได้ทุกเหตุผลเรียงตามตัวอักษร และ allowed False
- AC-05 Given position long SL 4000.90 และ short SL 4024.90, When `check_stop_change`, Then long → 4001.00 และ 4000.90 อนุญาต, → 4000.00 ได้ `("stop_loss_widened",)`, → None ได้ `("missing_stop_loss",)` · short → 4024.00 อนุญาต, → 4025.00 ได้ `("stop_loss_widened",)`
- AC-06 Given input ผิดตามหัวข้อ Negative cases, When เรียกฟังก์ชันที่เกี่ยวข้อง, Then raise ชนิดที่ระบุ (`TypeError` สำหรับชนิดผิดรวม float/bool · `BadPolicy`, `BadEquity`, `BadStop`, `BadHaltClear`, `TimeReversal` ซึ่งสืบจาก `RiskError(ValueError)`) · `H001_RISK` มีค่าและ provenance ตามตาราง, `unknowns(H001_RISK)` ตามที่ระบุ, `RiskPolicy`/`HaltState`/`SizeDecision`/`EntryRequest`/`GateDecision` แก้ค่าไม่ได้ (`FrozenInstanceError`) และ provenance เป็นสำเนา immutable
- AC-07 Given โค้ดใน `src/sochron/risk`, When รัน architecture test (AST) และ `bash scripts/controls/red-flags.sh main`, Then import มีแค่ stdlib, `sochron.core`, `sochron.costs` · ไม่มีชื่อ `float`/float literal, นาฬิกา, I/O, `MetaTrader5`, random · red-flag กลุ่ม secret และ order/account mutation ว่าง · `uv run --offline pytest tests -q -p no:cacheprovider` ผ่านทั้งหมด skipped 0 (รวม tests ของ CORE-001/002 เดิม)

## Verification per AC
| AC | Verifier (test author / CI / owner demo) | Command or procedure | Evidence level |
|----|------------------------------------------|----------------------|----------------|
| 01–06 | Codex: acceptance + golden (ตารางคำนวณมือเป็น Decimal string) ใน `tests/acceptance/CORE-003`, `tests/golden/CORE-003` · Claude: unit tests | `uv run --offline pytest tests -q -p no:cacheprovider` บน Windows | L2 · L3 เมื่อมี Python CI job (งานแยก) |
| 07 | Codex: ขยาย `tests/architecture/test_imports.py` ให้ครอบ `sochron.risk` (imports + float ban) | `uv run --offline pytest tests/architecture -q` · `bash scripts/controls/red-flags.sh main` · `node scripts/controls/check-locked-paths.mjs main` | L2 |
| ทั้งหมด | เจ้าของ | demo 3 ขั้นใน `docs/evidence/CORE-003.md`: รัน suite, คำนวณ sizing ของ H001 (0.02 lots, เสี่ยง 24 USD), ลอง restart การทดลองด้วยชื่อ "claude" ต้องถูกปฏิเสธ | เจ้าของตรวจ |

## Risk, data and external side effects
- ไม่มีผลภายนอก ไม่เชื่อมต่อ terminal ไม่ใช้ข้อมูลตลาด ไม่มี dependency ใหม่
- ความเสี่ยงหลัก: floor หรือการเทียบเกณฑ์ที่ขอบพลาดเพราะการปัด → เสี่ยงเกิน R หรือ halt ช้าไปหนึ่งขั้น · ลดด้วย exact arithmetic และ golden ที่ขอบพอดี
- ความเสี่ยงรอง: ค่า [A] ถูกใช้เหมือนค่าที่ยืนยันแล้ว → ลดด้วย provenance และ `unknowns()` ซึ่ง contract ของ R1/E1 ต้องแสดง · ก่อน E1 เจ้าของต้องตอบ Q-04
- การปลด halt ตรวจแค่ชื่อ ไม่ใช่การยืนยันตัวตน → การผูกกับตัวตนจริง (เช่น การยืนยันของเจ้าของใน journal) เป็นงานของ E1

## Plan, dependencies and unknowns (P06)
1. Understanding (3 lines) and likely misunderstandings: โมดูลนี้เป็น "ด่าน" ที่ตัดสินว่าเทรดได้แค่ไหนและเมื่อไรต้องหยุด จากตัวเลขที่ผู้เรียกส่งมา ไม่ใช่ตัวส่งคำสั่งหรือตัวคำนวณ equity · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่า halt รายวันปลดเมื่อ equity ฟื้น — ไม่ใช่ ปลดเมื่อขึ้นวันไทยใหม่เท่านั้น (ข) คิดว่าการทดลองหยุดแล้วเริ่มเองวันถัดไป — ไม่ใช่ ต้อง restart โดยผู้มีสิทธิ์ (ค) คิดว่าค่า 0.25% ยืนยันแล้ว — ยังเป็น [A] (ง) คิดว่า risk คำนวณวันไทยเอง — ไม่ใช่ ผู้เรียกส่ง `date` มา
2. Files to touch / what is reused: ใหม่ทั้งหมดใน `src/sochron/risk/` (`__init__.py`, `errors.py`, `policy.py`, `sizing.py`, `halts.py`, `gate.py`) · reuse จาก `sochron.costs`: `Provenance`, `CostModel`, `H001_COSTS` (ใน tests), `check_volume`, `CONTEXT` · ไม่แก้ `costs`, `timebase`, `core`
3. Steps, each with its check:
   1. เจ้าของอนุมัติ acceptance → Status approved · commit
   2. Codex contract review (adversarial, read-only) ก่อนเขียน tests แบบ CORE-002 → แก้ถ้ามี
   3. Codex `$write-acceptance-tests CORE-003` → patch → Claude apply ตาม D-006 + ตรวจ hash + session ใหม่ตรวจ → commit red
   4. Claude implement + unit tests → `uv run --offline pytest tests -q -p no:cacheprovider` เขียว
   5. evidence + handoff → Codex `$cross-agent-review` → `/fix-findings` จนไม่มี finding ค้าง
   6. เจ้าของเปิด PR (ต้องติด label เพราะแตะ tests ที่ล็อก) หลัง PR ของ chore และ CORE-002 merge แล้ว → CI เขียว → merge
4. Risks and negative cases to test: ตามหัวข้อ Negative cases · property: `actual_risk ≤ risk_money` เสมอเมื่อ reason เป็น "ok" หรือ "capped_at_volume_max"; lots อยู่บน grid เสมอ; HaltState เดิมไม่เปลี่ยน
5. Decisions needed from the owner: (ก) อนุมัติ acceptance 7 ข้อ (ข) sizing ตั้งต้นไม่รวมต้นทุน (`cost_per_lot = 0`) ให้ตรง H001 ที่ลงทะเบียนแล้ว ส่วน "รวม cost budget" ของ SPEC ใช้ได้ผ่าน `cost_per_lot` และให้ contract R1/E1 เลือก (ค) experiment halt ปลดได้ทางเดียวด้วย `restart_experiment` โดยผู้มีสิทธิ์พร้อมเหตุผล และ baseline ใหม่ = equity ตอน restart (ง) baseline ต้นวันไทย = equity แรกที่ผู้เรียกส่งมาในวันนั้น (จ) `halt_clearers` ตั้งต้น = ("owner",) ติดสถานะ unknown จนกว่าตอบ Q-04 · ค่า 0.25% / 0.75% / 2% / 1 คงเป็น assumed

## Authorization (filled by the owner)
- Claude Code / เขียน `src/sochron/risk/**`, `tests/unit/risk/**`, evidence, handoff, PROGRESS / repo นี้ / จนกว่า CORE-003 จะ done — รอเจ้าของกรอก
- Codex / เขียน tests ที่ล็อกเป็น patch ใน `docs/proposals/` / `tests/acceptance/CORE-003`, `tests/golden/CORE-003`, `tests/architecture` / งานนี้ — รอเจ้าของกรอก
- ไม่มีการเชื่อม terminal หรือบัญชีใดๆ ในงานนี้ · ไม่มี dependency ใหม่

## Budget
2 sessions · 3 attempts ต่อ test ที่ล้มโดยไม่มีหลักฐานใหม่ แล้วหยุดขอ second opinion · Codex headless ไม่เกิน 7 รัน (contract review ×2, tests, review ×3, สำรอง) · ไม่มีค่าใช้จ่ายเงิน

## Recovery, compensation and checkpoint
ลบ `src/sochron/risk`, tests ของ CORE-003 แล้วทิ้ง branch ได้ทั้งก้อน ไม่มีผลข้างเคียงนอกเครื่อง · checkpoint ใน PROGRESS.md หลังทุกขั้นที่ผ่าน check

## DoR status / missing items / next action
- ครบ: ค่า [A] ใน SPEC ข้อ 6, สูตร sizing และ worked example ใน H001 ข้อ 3, `sochron.costs` (CORE-002) ให้ `Provenance`/`CostModel`/`check_volume`
- ขาด: การอนุมัติ acceptance จากเจ้าของ · Codex contract review · tests จาก Codex · CORE-002 merge (branch นี้ต่อจาก `feat/CORE-002-costs`)
- next action: เจ้าของอนุมัติ acceptance → Codex contract review → tests

## Done scope
implementation (ทดสอบผ่านบนเครื่อง, review ปิด, merge แล้ว) · ไม่รวมการผูกตัวตนผู้ปลด halt และการบันทึก halt ลงดิสก์ (E1)
