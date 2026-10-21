# TASK CORE-002 — costs: cost model เดียวของระบบ (spread, commission, slippage, swap, stress ×2) พร้อมที่มาของทุกค่า

Version v1.1 (v1 ร่าง 20:2x → v1.1 20:4x แก้ความกำกวมตาม `docs/reviews/CORE-002-contract-r1.md` F1–F7 ก่อนมี tests) · Owner เจ้าของ repository · Parent SPEC J2/J3 (backtest หลังต้นทุน, trade attribution ใน journal) · `docs/architecture.md` ข้อ 8 แถว `costs` และข้อ 13a แถว "R1 data selection" (freeze cost provenance) · Tier **Standard** · Branch `feat/CORE-002-costs`
Status: **approved by delegation 2026-10-21 20:2x** — เจ้าของมอบอำนาจในแชท Claude 2026-10-21 (goal 19:1x "ทำให้เสร็จเฉพาะใน phase ขั้นตอนนี้ แล้วก็มึงตัดสินเลยกูอนุญาติ" และ 19:3x "จัดการเริ่มเลยเอาเต็มระบบส่วนนี้") Claude จึงอนุมัติ acceptance 7 ข้อแทนภายใต้สิทธิ์นั้น · เงื่อนไข: ทุกค่ามาจาก H001 (เจ้าของอนุมัติตัวเลขแล้ว) และ SPIKE-001 ไม่มีค่าธุรกิจใหม่ · Codex ตรวจ contract แบบ adversarial ก่อนเขียน tests (`docs/reviews/CORE-002-contract-r1.md`) · **เจ้าของ veto หรือแก้ acceptance ได้ทุกเมื่อก่อน merge** ถ้าแก้หลังมี tests แล้วเป็น contract รุ่นใหม่ตามกติกาเดิม · v1.1 แก้ความกำกวม F1–F7 ของ contract review r1 ก่อนมี tests (ตัวเลข acceptance เดิมทุกค่า) · รอ Codex re-review r2 ของ F1–F7 ก่อนเขียน tests
Hypothesis (research tasks): ไม่ใช่งานวิจัย แต่ให้บริการ H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`, commit `0c392a9`) ข้อ 6 Costs และข้อ 8 (stress ×2) · ไม่มีการรันข้อมูลตลาด

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no — โค้ด pure ไม่แตะสิทธิ์ ไม่เชื่อมต่ออะไร
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no — ไม่มีข้อมูลตลาด ไม่มีข้อมูลบัญชี
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อก (acceptance, golden, architecture) เขียนโดย Codex และเข้า repo ผ่าน patch ใน `docs/proposals/` ตาม D-006 เหมือน CORE-001 · ไม่แก้ `.github`, hooks, policy

เป็น Standard เพราะเป็นเลขเงินก้อนแรกของระบบ: ถ้าต้นทุนผิด backtest ทุกตัวและ attribution ทุกไม้ผิดตาม (Handbook §15: "profitable backtest is not evidence of an edge" ขึ้นกับต้นทุนที่ถูก)

## Goal / user outcome (Thai)
มีโมดูลเดียวชื่อ `sochron.costs` ที่ backtest (R1) และเส้นทาง trade attribution ของ E1 (ผ่าน `execution`/`backtest` ตาม module map; `journal` เองยัง import ได้เฉพาะ `core` และรับค่าที่คำนวณแล้ว) ใช้คิดต้นทุนต่อไม้แบบเดียวกัน โดย:
- คิด 4 องค์ประกอบเป็นเงิน USD แบบ `Decimal`: spread (จากฟิลด์ `spread` ของแท่งที่ fill, มีค่า fallback), commission, slippage ต่อข้าง และ swap ต่อคืน (รวมคืนที่คิด 3 เท่า) · รวมเป็น `CostBreakdown` และแปลงเป็น R-multiple ได้
- **ทุกค่าใน model มีที่มา (provenance): แหล่ง, วันที่, และสถานะ `measured` / `spec` / `assumed` / `unknown`** ตามด่าน "freeze cost provenance, do not infer historical swaps from today's specification" (review D-001 r1) · รายงานได้ว่าค่าไหนยังเป็นสมมติฐาน
- ทดสอบความทน (stress) ด้วย `×2` กับทุกองค์ประกอบในคำสั่งเดียว ตาม H001 ข้อ 6
- ค่าเริ่มต้นสำหรับ H001 บน `XAUUSDm` (`H001_COSTS`) ตรงกับ H001 ข้อ 6 และ spec ใน `docs/evidence/SPIKE-001.md` ทุกตัว พร้อมที่มา
- ปฏิเสธ input ที่ไม่ปลอดภัยต่อเงิน: float, volume นอก step/ขอบของสัญลักษณ์, จำนวนคืนติดลบ, spread ติดลบ · ไม่มี I/O ไม่อ่านนาฬิกา ไม่ import `MetaTrader5`

## Current behavior and evidence (revision)
ที่ main `b2eb69c`: มีแค่ `sochron.timebase` (CORE-001) · ไม่มีโค้ดเรื่องเงิน · นิยามต้นทุนของ H001 อยู่ใน `docs/hypotheses/H001-m15-momentum-breakout.md` ข้อ 3 (worked example: lots 0.02, swap 1 คืน ≈ 1.01 USD) และข้อ 6 · spec สัญลักษณ์ที่วัดได้อยู่ใน `docs/evidence/SPIKE-001.md` (digits 3, point 0.001, contract 100, volume 0.01–200 step 0.01, spread 240 points ตอนวัด, swap long −503.8 / short 0 points, วันคิด swap 3 เท่า = พุธ จากภาพ Specification) · ตัววิจารณ์แผน 2026-10-21 ชี้ว่า H001 ใช้ swap/spread ของ spec วันนี้กับประวัติ 2018–2024 จึงต้องติดป้ายที่มาและคง UNKNOWN ของ swap ย้อนหลังไว้ให้เห็นในรายงาน

## Scope
- In scope: แพ็กเกจ `sochron.costs` ตาม API ด้านล่าง · unit tests ของผู้ทำ · acceptance, golden และ architecture tests โดย Codex (ขยาย `tests/architecture/test_imports.py` ให้ครอบ `sochron.costs`) · หลักฐานใน `docs/evidence/CORE-002.md` · handoff
- Exclusions: การคำนวณ PnL จากราคา และการส่งค่าต้นทุนเข้า journal (อยู่ใน contract ถัดไปซึ่งต้องเคารพ module map: `backtest` import `costs` ได้, `journal` import ได้เฉพาะ `core` · CORE-002 คืนค่าต้นทุนแบบ pure เท่านั้น ไม่ให้สิทธิ์ import ใหม่แก่โมดูลใด) · การนับจำนวนคืนและคืนที่คิด 3 เท่าจากเวลา (ต้องรู้เวลา rollover ของโบรกเกอร์ซึ่งยัง UNKNOWN; จะเป็นฟังก์ชันใน `timebase` รุ่นถัดไปเมื่อมีหลักฐาน) · margin · currency conversion (บัญชี USD, profit currency USD) · การอ่าน spec จาก MT5 · การเปลี่ยนค่าใน model ระหว่างรัน
- Allowed files/modules: `src/sochron/costs/**`, `tests/unit/costs/**`, `docs/evidence/CORE-002.md`, `docs/handoff/CORE-002.md`, `PROGRESS.md` · โดย Codex ผ่าน patch: `tests/acceptance/CORE-002/**`, `tests/golden/CORE-002/**`, `tests/architecture/**` · `pyproject.toml`/`uv.lock` เฉพาะเมื่อมี admission ใหม่ (ไม่คาดว่าจะมี)
- Must not touch: `src/sochron/timebase/**`, `src/sochron/core/**` (ถ้าต้องมีชนิด Money กลาง ให้เสนอใน contract ถัดไป), `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`, `docs/hypotheses/**`, `research/**`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests (เปลี่ยนไม่ได้โดยผู้ทำ) · ทุกฟังก์ชันเป็น pure · เงินและปริมาณเป็น `decimal.Decimal` เท่านั้น (รับ `int` ได้สำหรับ points, จำนวนคืน, sides และ factor) · ชนิดผิดทุกตำแหน่ง (รวม `float` และ `bool`) → `TypeError` ไม่มีการแปลงค่าอัตโนมัติ · ตัวเลขเงินและ lots ในข้อความและตารางของ contract นี้เป็นค่าเชิงคณิตศาสตร์; ใน API และ golden tests ต้องสร้างจาก Decimal string เสมอ (เช่น `Decimal("0.02")`)

```text
sochron.costs
  Status = Literal["measured", "spec", "assumed", "unknown"]
  Provenance (frozen dataclass): source: str, as_of: date, status: Status, note: str = ""
      → source/note ไม่ใช่ str หรือ as_of ไม่ใช่ date → TypeError · status นอก 4 ค่า → BadProvenance
  CostModel (frozen dataclass):
      symbol: str, point: Decimal, contract_size: Decimal,
      volume_min: Decimal, volume_step: Decimal, volume_max: Decimal,
      spread_fallback_points: int,                 # ใช้เมื่อแท่งไม่มีค่า spread (None)
      commission_per_lot_per_side: Decimal,        # USD ต่อ lot ต่อข้าง
      slippage_points_per_side: int,
      swap_long_points_per_night: Decimal, swap_short_points_per_night: Decimal,   # ตามโบรกเกอร์: ลบ = จ่าย, บวก = ได้รับ
      triple_swap_weekday: int,                    # 0 = Monday … 6 = Sunday
      provenance: Mapping[str, Provenance],        # key = 11 base fields ตามหัวข้อ "provenance keys" เท่านั้น
      stress_factor: Decimal = Decimal("1")        # ค่าที่ได้จาก stress(); ไม่มี provenance
      → ตรวจตอนสร้าง: ชนิดผิด → TypeError · โดเมนผิด → CostsError (stress_factor → BadStress, provenance → BadProvenance) ตามตาราง "ชนิด โดเมน และ error"
      → เก็บ provenance เป็นสำเนา immutable (MappingProxyType ของ dict ใหม่)
  H001_COSTS: CostModel        # XAUUSDm ตาม H001 ข้อ 6 + SPIKE-001 (ค่าและ provenance ตามตารางด้านล่าง)
  stress(model: CostModel, factor: Decimal | int = Decimal("2")) -> CostModel
      # คืน model ใหม่ที่ stress_factor = model.stress_factor × factor; ฟิลด์อื่นและ provenance เท่าเดิม (ใช้ stress ครั้งเดียวต่อ charge ผ่าน stress_factor)
      # factor ชนิดผิด → TypeError · factor ≤ 0 หรือไม่ finite → BadStress
  check_volume(lots: Decimal, model: CostModel) -> Decimal
      # คืน lots เดิมถ้า finite และ volume_min ≤ lots ≤ volume_max และ lots mod volume_step == 0 ไม่งั้น BadVolume · lots ไม่ใช่ Decimal → TypeError
  points_to_money(points: int | Decimal, lots: Decimal, model: CostModel) -> Decimal
      # = points × model.point × model.contract_size × lots × model.stress_factor
      # points มีเครื่องหมายได้ (swap ใช้ค่าลบ) แต่ต้อง finite ไม่งั้น BadPoints · ตรวจ lots ด้วย check_volume เสมอ
  spread_charge(spread_points: int | None, lots: Decimal, model: CostModel) -> Decimal
      # = points_to_money(model.spread_fallback_points if spread_points is None else spread_points, lots, model) · spread_points ลบ → BadPoints
  slippage_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal
      # = points_to_money(model.slippage_points_per_side, lots, model) × sides
  commission_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal
      # = model.commission_per_lot_per_side × lots × sides × model.stress_factor (ตรวจ lots ด้วย check_volume)
  swap_charge(side: Side, lots: Decimal, nights: int, triple_nights: int, model: CostModel) -> Decimal
      # Side = Literal["long", "short"] · points = swap_long_points_per_night ถ้า long, swap_short_points_per_night ถ้า short
      # charge = 0 − points_to_money(points, lots, model) × (nights − triple_nights + 3 × triple_nights)   (บวก = จ่าย, ลบ = ได้รับ; ไม่คืน −0)
      # nights และ triple_nights เป็นจำนวนครั้งที่ถูกคิด swap ซึ่งผู้เรียกนับมาแล้ว (ไม่ใช่วันปฏิทิน) · nights < 0, triple_nights < 0 หรือ triple_nights > nights → BadNights
  CostBreakdown (frozen dataclass): spread: Decimal, commission: Decimal, slippage: Decimal, swap: Decimal, total: Decimal, stress_factor: Decimal
      # total = spread + commission + slippage + swap เสมอ · stress_factor = ค่าของ model ที่ใช้
  round_trip_cost(side: Side, lots: Decimal, entry_spread_points: int | None, exit_spread_points: int | None,
                  nights: int, triple_nights: int, model: CostModel, sides: int = 2) -> CostBreakdown
      # ตรวจ spread ทั้งสองค่า (int หรือ None, ไม่ลบ) ก่อนเลือก · spread คิดครั้งเดียวต่อรอบที่ข้างที่ข้ามจาก bid ไป ask: long ใช้ entry_spread_points, short ใช้ exit_spread_points (ข้อมูลเป็น bid bars) · None เฉพาะฝั่งที่เลือกจึงใช้ fallback
      # sides มีผลเฉพาะ commission และ slippage · คืน CostBreakdown เสมอแม้ sides = 0
  r_multiple(money: Decimal, r: Decimal) -> Decimal
      # money ÷ r ใน local context precision 28 ROUND_HALF_EVEN · ชนิดผิด → TypeError · money ไม่ finite → CostsError · r ≤ 0 หรือไม่ finite → BadR
  unknowns(model: CostModel) -> tuple[str, ...]            # ชื่อฟิลด์ที่ provenance.status เป็น assumed หรือ unknown เรียงตามตัวอักษร
  errors (ทั้งหมดสืบจาก CostsError(ValueError)):
      BadProvenance · BadStress · BadVolume · BadPoints · BadSides · BadNights · BadR
```

### Decimal context (ตอบ contract review r1 F1)
- ทุกฟังก์ชันคำนวณใน `decimal.localcontext()` ที่โมดูลตั้งเอง: precision 28, rounding `ROUND_HALF_EVEN` · ไม่ขึ้นกับและไม่แก้ context ของผู้เรียก · การคูณและบวกของ input ที่รับ (ทศนิยมไม่เกิน 6 หลัก, จำนวนเต็มไม่เกิน 10^9) ไม่สูญเสียหลักเลขที่ precision นี้ · การหารใน `r_multiple` ปัดที่ precision 28: `r_multiple(Decimal("1"), Decimal("3")) == Decimal("0.3333333333333333333333333333")` · ไม่ quantize เป็นสตางค์ (หน้าที่ของผู้แสดงผล)
- golden tests เทียบชนิด `Decimal` และค่าเชิงตัวเลขด้วย `==` ของ Decimal ไม่เทียบ exponent หรือรูปแบบ string (`Decimal("0.20000") == Decimal("0.20")` เป็นจริง)

### ชนิด โดเมน และ error (ตอบ F2)
| Input / โดเมน | ผล |
|---|---|
| argument หรือฟิลด์ชนิด Decimal ได้รับ int, str, bool หรือ float · argument หรือฟิลด์ชนิด int ได้รับ Decimal, str, bool หรือ float (bool ไม่ใช่ int ที่รับ) · points ไม่ใช่ int หรือ Decimal · side ไม่ใช่ str · symbol ไม่ใช่ str | `TypeError` ไม่มีการแปลงค่าอัตโนมัติ |
| side เป็น str อื่นที่ไม่ใช่ `"long"`/`"short"` (เช่น `"buy"`) | `CostsError` |
| lots, factor, points, r ไม่ finite (NaN, Infinity) | `BadVolume`, `BadStress`, `BadPoints`, `BadR` ตามลำดับ |
| money ใน `r_multiple` ไม่ finite | `CostsError` |
| ฟิลด์ model ตอนสร้าง: point, contract_size, volume_step, volume_min ≤ 0 · volume_max < volume_min · commission_per_lot_per_side, spread_fallback_points, slippage_points_per_side ติดลบ · triple_swap_weekday นอก 0–6 · ฟิลด์ Decimal ใดไม่ finite | `CostsError` (stress_factor ≤ 0 หรือไม่ finite → `BadStress`) |
| provenance: key ขาดหรือเกิน, ค่าที่ไม่ใช่ `Provenance`, status นอก 4 ค่า | `BadProvenance` |
| ตรวจ input ก่อนคืนศูนย์หรือก่อนเลือกฝั่ง: ทุก charge function ตรวจ lots ด้วย `check_volume` แม้ sides = 0 · `round_trip_cost` ตรวจ spread ทั้งสองค่า | error ตามแถวข้างบน |
| input ที่ผิดมากกว่าหนึ่งอย่างพร้อมกัน | ไม่กำหนดลำดับ error · acceptance ทดสอบทีละความผิด |

### provenance keys (ตอบ F5)
- provenance มี key ของ 11 base fields ต่อไปนี้เท่านั้น: `point`, `contract_size`, `volume_min`, `volume_step`, `volume_max`, `spread_fallback_points`, `commission_per_lot_per_side`, `slippage_points_per_side`, `swap_long_points_per_night`, `swap_short_points_per_night`, `triple_swap_weekday` · `symbol`, `provenance` และ `stress_factor` ไม่เป็น key · `stress_factor` เป็นค่าที่ได้จากการคูณ factor เริ่มที่ `Decimal("1")` และบันทึกแยกจาก provenance
- `CostModel` เก็บ immutable copy ของ provenance ที่ผู้เรียกส่งมา: แก้ dict ต้นทางภายหลังไม่เปลี่ยน `model.provenance` และแก้สมาชิกของ `model.provenance` ไม่ได้ (mapping proxy ปฏิเสธ, `Provenance` เป็น frozen) · `stress()` คืน model ที่ `provenance == model.provenance`

ค่าของ `H001_COSTS` (ต้องตรงทุกตัว):

| ฟิลด์ | ค่า | provenance (source · as_of · status) |
|---|---|---|
| symbol | `XAUUSDm` | – |
| point / contract_size | 0.001 / 100 | SPIKE-001 symbol_info · 2026-10-21 · measured |
| volume_min / step / max | 0.01 / 0.01 / 200 | SPIKE-001 symbol_info · 2026-10-21 · measured |
| spread_fallback_points | 240 | SPIKE-001 spread ตอนวัด · 2026-10-21 · measured (note: ค่าลอยตัว ใช้เมื่อแท่งไม่มี spread) |
| commission_per_lot_per_side | 0 | H001 ข้อ 6 "บัญชี Standard ของ Exness" · 2026-10-21 · assumed (ต้องยืนยันใน R1) |
| slippage_points_per_side | 50 | H001 ข้อ 6 [A] · 2026-10-21 · assumed |
| swap_long_points_per_night | −503.8 | SPIKE-001 symbol_info swap_long · 2026-10-21 · spec (note: ค่าย้อนหลัง 2018–2024 UNKNOWN) |
| swap_short_points_per_night | 0 | SPIKE-001 symbol_info swap_short · 2026-10-21 · spec (note เดียวกัน) |
| triple_swap_weekday | 2 (Wednesday) | ภาพ Specification ใน SPIKE-001 · 2026-10-21 · assumed [A] |

ดังนั้น `unknowns(H001_COSTS) == ("commission_per_lot_per_side", "slippage_points_per_side", "triple_swap_weekday")` และ note ของ swap ทั้งสองต้องมีคำว่า `UNKNOWN`

## Invariants
- ไม่มี `float` ในการคำนวณเงิน: ไม่มี float literal และไม่เรียก `float(` ใน `src/sochron/costs` (AST test) · ทุกผลลัพธ์เป็น `Decimal` คำนวณใน local context precision 28 `ROUND_HALF_EVEN` ตามหัวข้อ Decimal context · ไม่ quantize ภายในโมดูล
- `costs` import ได้เฉพาะ stdlib และ `sochron.core` (architecture ข้อ 8) · ไม่มี I/O, นาฬิกา, `MetaTrader5`, random
- `CostModel`, `Provenance`, `CostBreakdown` เป็น frozen · `H001_COSTS` เปลี่ยนไม่ได้ · การ stress สร้าง model ใหม่เสมอ ไม่แก้ของเดิม
- ทุก base field ตัวเลข 11 ฟิลด์ของ model มี provenance (หัวข้อ provenance keys); `stress_factor` เป็นค่าที่ได้จากการคูณ ไม่มี provenance · โค้ดไม่มีเส้นทาง "เดา" ค่าเมื่อ input หาย ยกเว้น `spread_fallback_points` ที่ประกาศไว้ชัดและมี provenance
- ความสัมพันธ์ตรวจสอบได้ด้วยมือ: `points_to_money(240, Decimal("0.02"), H001_COSTS) == Decimal("0.48")`; `swap_charge("long", Decimal("0.02"), 1, 0, H001_COSTS) == Decimal("1.00760")` (ค่าจาก H001 worked example ก่อนปัด 1.01); `stress(stress(H001_COSTS)).stress_factor == Decimal("4")`
- ไม่มี `.skip`, `xfail` หรือ test ที่อ่อนลงใน tests ที่ล็อก · ไม่มี dependency ใหม่นอกเหนือจากที่ผ่าน admission (คาดว่าไม่มี)

## Negative cases
- float ใน lots, points, r, factor → `TypeError` ทุกฟังก์ชัน (ไม่แปลงเงียบๆ)
- volume: 0.005 (< min), 0.015 (ไม่ตรง step), 200.01 (> max) → `BadVolume` · 0.01, 0.02, 200 → ผ่าน (ขอบพอดีอยู่ใน)
- spread_points −1 → `BadPoints` · None → ใช้ fallback 240 · 0 → ค่า 0 (spread ศูนย์เป็นค่าที่ถูกต้องของข้อมูล ไม่ใช่ error)
- nights −1, triple_nights −1, triple_nights > nights → `BadNights` · nights 0 → swap 0
- stress factor 0 หรือ −2 → `BadStress` · factor 1 → model ที่เท่ากับเดิมทุกค่า (ยกเว้น stress_factor) · stress ซ้อน (stress(stress(m)) ) → stress_factor 4
- provenance ขาด 1 ฟิลด์ หรือมี key `symbol`/key แปลก → `BadProvenance`
- sides: int ที่ไม่ใช่ bool และ ≥ 0 · มีผลเฉพาะ commission และ slippage (ทั้งคู่เป็น 0 เมื่อ sides = 0) · sides −1 → `BadSides` · sides ชนิดผิด (bool, float) → `TypeError` · `round_trip_cost` คืน `CostBreakdown` เสมอ (AC-04: sides 0 → total 1.48760 เพราะ spread และ swap ยังคิด) · r ≤ 0 → `BadR`
- ไม่ finite: lots `Decimal("NaN")` → `BadVolume` · factor `Decimal("NaN")` → `BadStress` · points `Decimal("Infinity")` → `BadPoints` · r `Decimal("NaN")` → `BadR` · money `Decimal("NaN")` ใน `r_multiple` → `CostsError`
- side `"buy"` → `CostsError` · side `1` (ไม่ใช่ str) → `TypeError` · bool แทน int (`True` เป็น nights หรือ sides) → `TypeError`
- model ผิดโดเมนตอนสร้าง (ด้วย `dataclasses.replace(H001_COSTS, …)`): volume_step `Decimal("0")`, point `Decimal("0")`, volume_max < volume_min, slippage −1, triple_swap_weekday 7 → `CostsError` · stress_factor `Decimal("0")` → `BadStress`
- swap ฝั่ง short ของ H001 = 0 ทุกจำนวนคืน · swap บวก (ได้รับ) ต้องคืนค่า charge ติดลบ (ทดสอบด้วย model สมมติที่ระบุครบใน AC-03) · negative `exit_spread_points` บน long → `BadPoints` แม้ไม่ถูกใช้

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given `H001_COSTS` และ lots `Decimal("0.02")`, When เรียก `spread_charge(240, …)`, `spread_charge(None, …)` และ `spread_charge(240, …, stress(H001_COSTS))`, Then ได้ `Decimal("0.48")`, `Decimal("0.48")` (fallback 240) และ `Decimal("0.96")` USD ตามลำดับ และ `points_to_money(1, Decimal("1"), H001_COSTS) == Decimal("0.1")` (1 point ต่อ 1 lot = tick value 0.1 USD ตาม SPIKE-001) · ทุกค่าเทียบเชิงตัวเลขของ Decimal
- AC-02 Given lots `Decimal("0.02")`, When เรียก `slippage_charge` (sides 2) และ `commission_charge` (sides 2) บน `H001_COSTS` และบน `stress(H001_COSTS)`, Then slippage = `Decimal("0.20")` / `Decimal("0.40")` และ commission = `Decimal("0")` / `Decimal("0")` · model สมมติ = `replace(H001_COSTS, commission_per_lot_per_side=Decimal("3.5"), provenance={**H001_COSTS.provenance, "commission_per_lot_per_side": Provenance("synthetic test fixture", date(2026, 10, 21), "assumed")})` กับ lots `Decimal("1.5")`, sides 2 → commission `Decimal("10.5")` ที่ stress_factor 1 และ `Decimal("21.0")` หลัง `stress(…)` · sides 0 → slippage และ commission เป็น `Decimal("0")` ทั้งสองรุ่น
- AC-03 Given `H001_COSTS` และ lots `Decimal("0.02")`, When เรียก `swap_charge` สำหรับ (`"long"`, nights 1, triple_nights 0), (`"long"`, nights 7, triple_nights 1) และ (`"short"`, nights 7, triple_nights 1), Then ได้ `Decimal("1.00760")`, `Decimal("9.06840")` และ `Decimal("0")` USD · บน `stress(H001_COSTS)` ได้ `Decimal("2.01520")`, `Decimal("18.13680")`, `Decimal("0")` · model สมมติ = `replace(H001_COSTS, swap_long_points_per_night=Decimal("100"), provenance={**H001_COSTS.provenance, "swap_long_points_per_night": Provenance("synthetic test fixture", date(2026, 10, 21), "assumed")})` กับ (`"long"`, lots `Decimal("0.02")`, nights 1, triple_nights 0) → charge `Decimal("-0.20000")` (ได้รับเงิน) และ `Decimal("-0.40000")` หลัง `stress(…)` · nights/triple_nights คือจำนวนครั้งที่ถูกคิดซึ่งผู้เรียกนับมาแล้ว ไม่ใช่วันปฏิทิน
- AC-04 Given worked example ของ H001 ข้อ 3 (side `"long"`, lots `Decimal("0.02")`, entry_spread_points 240, exit_spread_points 240, nights 1, triple_nights 0, sides 2, R = `Decimal("25")`), When เรียก `round_trip_cost` บน `H001_COSTS`, Then ได้ spread `Decimal("0.48")`, commission `Decimal("0")`, slippage `Decimal("0.20")`, swap `Decimal("1.00760")`, total `Decimal("1.68760")`, stress_factor `Decimal("1")` และ `r_multiple(total, Decimal("25")) == Decimal("0.067504")` · เดียวกันแต่ sides 0 → total `Decimal("1.48760")` (spread และ swap ยังคิด) · side `"short"` กับ entry 100 / exit 240 (nights 1, triple_nights 0, sides 2) → spread `Decimal("0.48")` จากแท่งออก, swap `Decimal("0")`, total `Decimal("0.68")` · รอบ long เดิมบน `stress(H001_COSTS)` → total `Decimal("3.37520")`, stress_factor `Decimal("2")`
- AC-05 Given input ผิดตามหัวข้อ Negative cases และตาราง "ชนิด โดเมน และ error", When เรียกฟังก์ชันที่เกี่ยวข้อง, Then แต่ละกรณี raise ชนิดที่ระบุ (`TypeError` สำหรับชนิดผิดรวม float และ bool · `BadVolume` lots 0.005 / 0.015 / 200.01 / NaN · `BadPoints` spread −1 และ points Infinity · `BadNights` nights −1, triple_nights −1, triple_nights > nights · `BadStress` factor 0 / −2 / NaN · `BadProvenance` key ขาด / key เกิน / status ผิด · `BadSides` −1 · `BadR` r 0 และ NaN · `CostsError` side `"buy"`, model volume_step 0, money NaN ใน `r_multiple`) ไม่มีกรณีไหนคืนค่า · กรณีขอบที่ถูกต้อง (lots `Decimal("0.01")` และ `Decimal("200")`; spread 0; nights 0; factor `Decimal("1")`; sides 0) ผ่านด้วยค่าที่ระบุ · negative exit spread บน long → `BadPoints` แม้ไม่ถูกใช้
- AC-06 Given `H001_COSTS`, When อ่าน provenance และเรียก `unknowns`, Then key ของ provenance คือ 11 base fields ตามหัวข้อ provenance keys พอดี (ไม่มี `stress_factor`), ทุก entry มี `as_of = date(2026, 10, 21)` และสถานะตรงตาราง, `unknowns(H001_COSTS) == ("commission_per_lot_per_side", "slippage_points_per_side", "triple_swap_weekday")`, note ของ swap ทั้งสองมีคำว่า `UNKNOWN`, `stress(H001_COSTS).provenance == H001_COSTS.provenance` · สร้าง model จาก dict แล้วแก้ dict ต้นทาง → `model.provenance` ไม่เปลี่ยน · `CostModel`, `Provenance`, `CostBreakdown` แก้ค่าไม่ได้ (`FrozenInstanceError`) และ `model.provenance[...] = …` ถูกปฏิเสธ (`TypeError`)
- AC-07 Given โค้ดใน `src/sochron/costs`, When รัน architecture test (AST) และ `bash scripts/controls/red-flags.sh main`, Then import มีแค่ stdlib และ `sochron.core`, ไม่มี `float` literal หรือ `float(`, ไม่มี `MetaTrader5`/นาฬิกา/I/O · red-flag กลุ่ม secret และ order/account mutation ว่าง · `uv run --offline pytest tests -q -p no:cacheprovider` ผ่านทั้งหมด skipped 0 (รวม tests ของ CORE-001 เดิม)

## Verification per AC
| AC | Verifier (test author / CI / owner demo) | Command or procedure | Evidence level |
|----|------------------------------------------|----------------------|----------------|
| 01–06 | Codex: acceptance + golden (ตารางคำนวณมือเป็น Decimal string) ใน `tests/acceptance/CORE-002`, `tests/golden/CORE-002` · Claude: unit tests | `uv run --offline pytest tests -q -p no:cacheprovider` บน Windows | L2 · L3 เมื่อมี Python CI job (งานแยก) |
| 07 | Codex: ขยาย `tests/architecture/test_imports.py` (AST: imports + float ban สำหรับ `sochron.costs`) · สคริปต์ควบคุม | `uv run --offline pytest tests/architecture -q` · `bash scripts/controls/red-flags.sh main` · `node scripts/controls/check-locked-paths.mjs main` | L2 |
| ทั้งหมด | เจ้าของ | demo 3 ขั้นใน `docs/evidence/CORE-002.md`: รัน suite, คำนวณ worked example ของ H001 ด้วย `round_trip_cost` แล้วเทียบตัวเลขในสมมติฐาน (0.48 / 0.20 / 1.0076), ลอง lots 0.015 ต้องถูกปฏิเสธ | เจ้าของตรวจ |

## Risk, data and external side effects
- ไม่มีผลภายนอก ไม่เชื่อมต่อ terminal ไม่ใช้ข้อมูลตลาด ไม่มี dependency ใหม่ (Decimal/dataclasses เป็น stdlib)
- ความเสี่ยงหลัก: สูตรหรือหน่วยผิด (points ↔ USD, ต่อข้าง ↔ ต่อรอบ, คืน 3 เท่า) → ทุก backtest ผิด · ลดด้วย golden ที่ Codex คำนวณมือจาก worked example ของ H001 และ tick value ที่ SPIKE-001 วัดได้ (0.1 USD/point/lot)
- ความเสี่ยงรอง: ค่า assumed ถูกใช้เหมือนค่าจริง → ลดด้วย provenance ที่บังคับทุกฟิลด์และ `unknowns()` ที่รายงานต้องแสดงใน R1 · swap ย้อนหลังเป็น UNKNOWN โดยนิยาม · R1 ต้องแสดงที่มาและความไม่แน่นอนของ swap ย้อนหลังควบคู่ stress ×2 (ด่าน 13a); metric สำหรับ swap attribution ให้กำหนดใน contract R1 ที่อนุมัติ ไม่ใช่ที่นี่
- ชื่อ API ไม่พอสำหรับ `backtest`/`journal` → เพิ่มใน contract ถัดไป ห้ามเปลี่ยนชื่อเดิมโดยไม่มี contract

## Plan, dependencies and unknowns (P06)
1. Understanding (3 lines) and likely misunderstandings: โมดูลนี้คือ "ราคาของต้นทุน" ไม่ใช่ตัวจำลองการเทรด: รับ lots, points, จำนวนคืน แล้วคืนเงินแบบ Decimal พร้อมที่มาของทุกค่าคงที่ · เข้าใจผิดที่เป็นไปได้: (ก) คิด spread สองครั้ง (เข้า+ออก) — ข้อมูลเป็น bid bars จึงจ่าย spread ครั้งเดียวที่ข้าง buy (ข) ใช้ float เพราะ "แค่คูณกัน" — ห้าม เพราะ 0.1 × 3 ≠ 0.3 ใน float และกฎ AGENTS.md บังคับ Decimal (ค) คิดว่า swap ย้อนหลังรู้แล้ว — ไม่ใช่ เป็นค่า spec วันนี้ ติดป้าย UNKNOWN (ง) นับคืนจากเวลาในโมดูลนี้ — ไม่ใช่ จำนวนคืนเป็น input (rollover UNKNOWN)
2. Files to touch / what is reused: ใหม่ทั้งหมดใน `src/sochron/costs/` (`__init__.py`, `errors.py`, `model.py`, `charges.py`) · reuse แนวทางของ CORE-001: frozen dataclass, `MappingProxyType`, error hierarchy จาก `ValueError`, TypeError สำหรับชนิดผิด · ตัวเลขจาก H001 ข้อ 3/6 และ SPIKE-001 · ไม่แก้ `core` และ `timebase`
3. Steps, each with its check:
   1. เจ้าของอนุมัติ acceptance นี้ → Status approved · commit contract บน `feat/CORE-002-costs`
   2. Codex `$write-acceptance-tests CORE-002`: acceptance (AC-01–06), golden tables (Decimal strings), ขยาย architecture test → `docs/proposals/CORE-002-tests.patch` พร้อม hash → Claude apply ตาม D-006, ตรวจ hash, session ใหม่ตรวจ, commit → check: tests **FAIL** ก่อนมีโค้ด (red) · ถ้า Codex ต้องการ `hypothesis` สำหรับ property tests (SPIKE FIRST ที่เจ้าของอนุมัติ) ให้ทำ `$dependency-admission` แยกและรอเจ้าของอนุมัติ D-013 ก่อน; ถ้าไม่อนุมัติใช้ตารางค่าคงที่แทน
   3. Claude implement `sochron.costs` ทีละฟังก์ชันพร้อม unit tests → check: `uv run --offline pytest tests -q -p no:cacheprovider` เขียว commit ทีละขั้น
   4. Claude เขียน `docs/evidence/CORE-002.md` (รวม demo 3 ขั้น) + handoff → Codex `$cross-agent-review` → Claude `/fix-findings` → re-review จนไม่มี finding ค้าง
   5. เจ้าของเปิด PR (มี tests ที่ล็อก → ต้องติด label `owner-approved-control-change`) → `ci / control-plane` และ `control-gate / locked-paths` เขียว → merge
4. Risks and negative cases to test: ตามหัวข้อ Negative cases ทั้งหมด · property: `points_to_money` เป็นเชิงเส้นใน lots และ points; `stress(m, 2)` ให้ทุก charge เป็น 2 เท่าพอดี; `round_trip_cost.total == spread + commission + slippage + swap` เสมอ (ถ้าใช้ `hypothesis` ต้องผ่าน admission ก่อน)
5. Decisions needed from the owner: ตัดสินแทนแล้วภายใต้การมอบอำนาจ 2026-10-21 (เจ้าของ veto ได้ก่อน merge): (ก) acceptance 7 ข้ออนุมัติ (ข) ค่า [A] ของ H001 (commission 0, slippage 50 points, พุธคิด 3 เท่า) เข้า model ด้วยสถานะ `assumed` ตามตาราง — ติดป้าย ไม่ใช่ยืนยันค่า (ค) ถ้า Codex ขอ `hypothesis`: ทำ admission แล้ว Claude ตัดสินตามผล admission ภายใต้สิทธิ์เดียวกัน เว้นแต่ admission พบความเสี่ยงด้าน supply chain → ส่งเจ้าของ

## Authorization (filled by the owner)
- Claude Code / เขียน `src/sochron/costs/**`, `tests/unit/costs/**`, evidence, handoff, PROGRESS / repo นี้ / จนกว่า CORE-002 จะ done — อนุมัติโดยมอบอำนาจ (เจ้าของ 2026-10-21 19:1x/19:3x ดู Status) · เจ้าของ veto ได้ก่อน merge
- Codex / เขียน tests ที่ล็อกเป็น patch ใน `docs/proposals/` / `tests/acceptance/CORE-002`, `tests/golden/CORE-002`, `tests/architecture` / งานนี้ — อนุมัติโดยมอบอำนาจเดียวกัน (ขั้นตอน test author ปกติเหมือน CORE-001)
- ไม่มีการเชื่อม terminal หรือบัญชีใดๆ ในงานนี้ · ไม่มี dependency ใหม่เว้นแต่ผ่าน admission

## Budget
2 sessions · 3 attempts ต่อ test ที่ล้มโดยไม่มีหลักฐานใหม่ แล้วหยุดขอ second opinion · Codex headless ไม่เกิน 5 รัน (tests, review, re-review ×2, สำรอง; admission เพิ่มถ้าขอ `hypothesis`) · ไม่มีค่าใช้จ่ายเงิน

## Recovery, compensation and checkpoint
ลบ `src/sochron/costs`, tests ของ CORE-002 แล้วทิ้ง branch ได้ทั้งก้อน ไม่มีผลข้างเคียงนอกเครื่อง · checkpoint ใน PROGRESS.md หลังทุกขั้นที่ผ่าน check

## DoR status / missing items / next action
- ครบ: นิยามต้นทุนใน H001 (committed), spec สัญลักษณ์จาก SPIKE-001, สภาพแวดล้อม uv (D-012), สิทธิ์ branch/push ตาม D-006, การอนุมัติ acceptance โดยมอบอำนาจ (ดู Status)
- ครบเพิ่ม: Codex contract review r1 (`docs/reviews/CORE-002-contract-r1.md`: F1–F7) → แก้ใน v1.1 ครบทุกข้อ
- ขาด: Codex contract re-review r2 (F1–F7 เท่านั้น) · tests จาก Codex (patch)
- next action: Codex re-review r2 → Codex `$write-acceptance-tests CORE-002` → Claude apply ตาม D-006 + session ใหม่ตรวจ + commit red แล้วลงมือ

## Done scope
implementation (ทดสอบผ่านบนเครื่อง, review ปิด, merge แล้ว) · ยังไม่รวม Python CI job และการนับคืน swap จากเวลา
