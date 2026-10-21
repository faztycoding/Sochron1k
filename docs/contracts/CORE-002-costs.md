# TASK CORE-002 — costs: cost model เดียวของระบบ (spread, commission, slippage, swap, stress ×2) พร้อมที่มาของทุกค่า

Version v1 · Owner เจ้าของ repository · Parent SPEC J2/J3 (backtest หลังต้นทุน, trade attribution ใน journal) · `docs/architecture.md` ข้อ 8 แถว `costs` และข้อ 13a แถว "R1 data selection" (freeze cost provenance) · Tier **Standard** · Branch `feat/CORE-002-costs`
Status: draft (รอเจ้าของอนุมัติ acceptance 7 ข้อ)
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
มีโมดูลเดียวชื่อ `sochron.costs` ที่ backtest (R1) และ journal/attribution (E1) ใช้คิดต้นทุนต่อไม้แบบเดียวกัน โดย:
- คิด 4 องค์ประกอบเป็นเงิน USD แบบ `Decimal`: spread (จากฟิลด์ `spread` ของแท่งที่ fill, มีค่า fallback), commission, slippage ต่อข้าง และ swap ต่อคืน (รวมคืนที่คิด 3 เท่า) · รวมเป็น `CostBreakdown` และแปลงเป็น R-multiple ได้
- **ทุกค่าใน model มีที่มา (provenance): แหล่ง, วันที่, และสถานะ `measured` / `spec` / `assumed` / `unknown`** ตามด่าน "freeze cost provenance, do not infer historical swaps from today's specification" (review D-001 r1) · รายงานได้ว่าค่าไหนยังเป็นสมมติฐาน
- ทดสอบความทน (stress) ด้วย `×2` กับทุกองค์ประกอบในคำสั่งเดียว ตาม H001 ข้อ 6
- ค่าเริ่มต้นสำหรับ H001 บน `XAUUSDm` (`H001_COSTS`) ตรงกับ H001 ข้อ 6 และ spec ใน `docs/evidence/SPIKE-001.md` ทุกตัว พร้อมที่มา
- ปฏิเสธ input ที่ไม่ปลอดภัยต่อเงิน: float, volume นอก step/ขอบของสัญลักษณ์, จำนวนคืนติดลบ, spread ติดลบ · ไม่มี I/O ไม่อ่านนาฬิกา ไม่ import `MetaTrader5`

## Current behavior and evidence (revision)
ที่ main `b2eb69c`: มีแค่ `sochron.timebase` (CORE-001) · ไม่มีโค้ดเรื่องเงิน · นิยามต้นทุนของ H001 อยู่ใน `docs/hypotheses/H001-m15-momentum-breakout.md` ข้อ 3 (worked example: lots 0.02, swap 1 คืน ≈ 1.01 USD) และข้อ 6 · spec สัญลักษณ์ที่วัดได้อยู่ใน `docs/evidence/SPIKE-001.md` (digits 3, point 0.001, contract 100, volume 0.01–200 step 0.01, spread 240 points ตอนวัด, swap long −503.8 / short 0 points, วันคิด swap 3 เท่า = พุธ จากภาพ Specification) · ตัววิจารณ์แผน 2026-10-21 ชี้ว่า H001 ใช้ swap/spread ของ spec วันนี้กับประวัติ 2018–2024 จึงต้องติดป้ายที่มาและคง UNKNOWN ของ swap ย้อนหลังไว้ให้เห็นในรายงาน

## Scope
- In scope: แพ็กเกจ `sochron.costs` ตาม API ด้านล่าง · unit tests ของผู้ทำ · acceptance, golden และ architecture tests โดย Codex (ขยาย `tests/architecture/test_imports.py` ให้ครอบ `sochron.costs`) · หลักฐานใน `docs/evidence/CORE-002.md` · handoff
- Exclusions: การคำนวณ PnL จากราคา (เป็นของ `backtest`/`journal`) · การนับจำนวนคืนและคืนที่คิด 3 เท่าจากเวลา (ต้องรู้เวลา rollover ของโบรกเกอร์ซึ่งยัง UNKNOWN; จะเป็นฟังก์ชันใน `timebase` รุ่นถัดไปเมื่อมีหลักฐาน) · margin · currency conversion (บัญชี USD, profit currency USD) · การอ่าน spec จาก MT5 · การเปลี่ยนค่าใน model ระหว่างรัน
- Allowed files/modules: `src/sochron/costs/**`, `tests/unit/costs/**`, `docs/evidence/CORE-002.md`, `docs/handoff/CORE-002.md`, `PROGRESS.md` · โดย Codex ผ่าน patch: `tests/acceptance/CORE-002/**`, `tests/golden/CORE-002/**`, `tests/architecture/**` · `pyproject.toml`/`uv.lock` เฉพาะเมื่อมี admission ใหม่ (ไม่คาดว่าจะมี)
- Must not touch: `src/sochron/timebase/**`, `src/sochron/core/**` (ถ้าต้องมีชนิด Money กลาง ให้เสนอใน contract ถัดไป), `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`, `docs/hypotheses/**`, `research/**`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests (เปลี่ยนไม่ได้โดยผู้ทำ) · ทุกฟังก์ชันเป็น pure · เงินและปริมาณเป็น `decimal.Decimal` เท่านั้น (รับ `int` ได้สำหรับ points และจำนวนคืน) · `float` ทุกตำแหน่ง → `TypeError`

```text
sochron.costs
  Status = Literal["measured", "spec", "assumed", "unknown"]
  Provenance (frozen dataclass): source: str, as_of: date, status: Status, note: str = ""
  CostModel (frozen dataclass):
      symbol: str, point: Decimal, contract_size: Decimal,
      volume_min: Decimal, volume_step: Decimal, volume_max: Decimal,
      spread_fallback_points: int,                 # ใช้เมื่อแท่งไม่มีค่า spread (None)
      commission_per_lot_per_side: Decimal,        # USD
      slippage_points_per_side: int,
      swap_long_points_per_night: Decimal, swap_short_points_per_night: Decimal,   # ลบ = จ่าย, บวก = ได้รับ
      triple_swap_weekday: int,                    # 0 = Monday … 6 = Sunday (ISO weekday − 1)
      provenance: Mapping[str, Provenance],        # key = ชื่อฟิลด์ทุกตัวข้างบนยกเว้น symbol และ provenance
      stress_factor: Decimal = Decimal(1)
      → สร้างไม่ได้ (BadProvenance) ถ้า provenance ขาดฟิลด์ใด หรือมี key เกิน
  H001_COSTS: CostModel        # XAUUSDm ตาม H001 ข้อ 6 + SPIKE-001 (ค่าและ provenance ตามตารางด้านล่าง)
  stress(model: CostModel, factor: Decimal = Decimal(2)) -> CostModel     # คูณ spread, commission, slippage, swap ทุกตัวด้วย factor ผ่าน stress_factor; provenance คงเดิม; factor ≤ 0 → BadStress
  check_volume(lots: Decimal, model: CostModel) -> Decimal                # คืน lots เดิมถ้า volume_min ≤ lots ≤ volume_max และเป็นพหุคูณของ volume_step ไม่งั้น BadVolume
  points_to_money(points: int | Decimal, lots: Decimal, model: CostModel) -> Decimal   # points × point × contract_size × lots × stress_factor
  spread_charge(spread_points: int | None, lots: Decimal, model: CostModel) -> Decimal  # None → fallback; ลบ → BadPoints
  slippage_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal           # sides < 0 → BadSides
  commission_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal
  swap_charge(side: Side, lots: Decimal, nights: int, triple_nights: int, model: CostModel) -> Decimal
      # Side = Literal["long", "short"] · ค่าบวก = จ่าย (charge) · points_per_night × point × contract × lots × (nights − triple_nights + 3 × triple_nights) × stress_factor แล้วกลับเครื่องหมาย
      # nights < 0, triple_nights < 0 หรือ triple_nights > nights → BadNights
  CostBreakdown (frozen dataclass): spread: Decimal, commission: Decimal, slippage: Decimal, swap: Decimal, total: Decimal, stress_factor: Decimal
  round_trip_cost(side, lots, entry_spread_points, exit_spread_points, nights, triple_nights, model, sides: int = 2) -> CostBreakdown
      # spread คิดครั้งเดียวต่อรอบ ที่ข้างที่ข้ามจาก bid ไป ask: long → spread ของแท่งเข้า, short → spread ของแท่งออก (ข้อมูลเป็น bid bars)
  r_multiple(money: Decimal, r: Decimal) -> Decimal        # money ÷ r; r ≤ 0 → BadR
  unknowns(model: CostModel) -> tuple[str, ...]            # ชื่อฟิลด์ที่ provenance.status เป็น assumed หรือ unknown เรียงตามชื่อ
  errors (ทั้งหมดสืบจาก CostsError(ValueError)):
      BadProvenance · BadStress · BadVolume · BadPoints · BadSides · BadNights · BadR
```

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
- ไม่มี `float` ในการคำนวณเงิน: ไม่มี float literal และไม่เรียก `float(` ใน `src/sochron/costs` (AST test) · ทุกผลลัพธ์เป็น `Decimal` ที่คำนวณแบบ exact (ไม่ quantize ภายในโมดูล การปัดเป็นสตางค์เป็นหน้าที่ของผู้แสดงผล)
- `costs` import ได้เฉพาะ stdlib และ `sochron.core` (architecture ข้อ 8) · ไม่มี I/O, นาฬิกา, `MetaTrader5`, random
- `CostModel`, `Provenance`, `CostBreakdown` เป็น frozen · `H001_COSTS` เปลี่ยนไม่ได้ · การ stress สร้าง model ใหม่เสมอ ไม่แก้ของเดิม
- ทุกฟิลด์ตัวเลขของ model มี provenance; โค้ดไม่มีเส้นทาง "เดา" ค่าเมื่อ input หาย ยกเว้น `spread_fallback_points` ที่ประกาศไว้ชัดและมี provenance
- ความสัมพันธ์ตรวจสอบได้ด้วยมือ: `points_to_money(240, 0.02, H001_COSTS) == Decimal("0.48")`; `swap_charge("long", 0.02, 1, 0, H001_COSTS) == Decimal("1.00760")` (ค่าจาก H001 worked example ก่อนปัด 1.01)
- ไม่มี `.skip`, `xfail` หรือ test ที่อ่อนลงใน tests ที่ล็อก · ไม่มี dependency ใหม่นอกเหนือจากที่ผ่าน admission (คาดว่าไม่มี)

## Negative cases
- float ใน lots, points, r, factor → `TypeError` ทุกฟังก์ชัน (ไม่แปลงเงียบๆ)
- volume: 0.005 (< min), 0.015 (ไม่ตรง step), 200.01 (> max) → `BadVolume` · 0.01, 0.02, 200 → ผ่าน (ขอบพอดีอยู่ใน)
- spread_points −1 → `BadPoints` · None → ใช้ fallback 240 · 0 → ค่า 0 (spread ศูนย์เป็นค่าที่ถูกต้องของข้อมูล ไม่ใช่ error)
- nights −1, triple_nights −1, triple_nights > nights → `BadNights` · nights 0 → swap 0
- stress factor 0 หรือ −2 → `BadStress` · factor 1 → model ที่เท่ากับเดิมทุกค่า (ยกเว้น stress_factor) · stress ซ้อน (stress(stress(m)) ) → stress_factor 4
- provenance ขาด 1 ฟิลด์ หรือมี key `symbol`/key แปลก → `BadProvenance`
- sides −1 → `BadSides` · sides 0 → 0 · r ≤ 0 → `BadR`
- swap ฝั่ง short ของ H001 = 0 ทุกจำนวนคืน · swap บวก (ได้รับ) ต้องคืนค่า charge ติดลบ (ทดสอบด้วย model สมมติ)

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given `H001_COSTS` และ lots 0.02, When เรียก `spread_charge(240, …)`, `spread_charge(None, …)` และ `spread_charge(240, …, stress(H001_COSTS))`, Then ได้ `0.48`, `0.48` (fallback 240) และ `0.96` USD ตามลำดับ และ `points_to_money(1, 1, H001_COSTS) == 0.1` (1 point ต่อ 1 lot = tick value 0.1 USD ตาม SPIKE-001)
- AC-02 Given lots 0.02, When เรียก `slippage_charge` (2 ข้าง) และ `commission_charge` (2 ข้าง) บน `H001_COSTS` และบน `stress(H001_COSTS)`, Then slippage = `0.20` / `0.40` USD และ commission = `0` / `0` · และ model สมมติที่ commission 3.5 USD/lot/ข้าง กับ lots 1.5 ให้ commission 2 ข้าง = `10.5`
- AC-03 Given `H001_COSTS`, When เรียก `swap_charge` สำหรับ long 0.02 lots 1 คืน (triple 0), long 7 คืนที่มีคืนพุธ 1 คืน, และ short 7 คืน, Then ได้ `1.00760`, `9.06840` และ `0` USD · ภายใต้ stress ×2 ได้สองเท่า · model สมมติที่ swap long +100 points ให้ charge เป็นค่าลบ (ได้รับเงิน)
- AC-04 Given worked example ของ H001 ข้อ 3 (long, lots 0.02, spread เข้า/ออก 240, 1 คืน, triple 0, R = 25 USD), When เรียก `round_trip_cost`, Then ได้ spread `0.48`, slippage `0.20`, commission `0`, swap `1.00760`, total `1.68760` USD และ `r_multiple(total, 25) == 0.067504` · short ด้วยค่าเดียวกัน (spread เข้า 100, ออก 240) ใช้ spread ของแท่งออก = `0.48` และ swap `0` → total `0.68` · stress ×2 ให้ total ของ long = `3.37520`
- AC-05 Given input ผิดตามหัวข้อ Negative cases, When เรียกฟังก์ชันที่เกี่ยวข้อง, Then แต่ละกรณี raise ชนิดที่ระบุ (`TypeError`, `BadVolume`, `BadPoints`, `BadNights`, `BadStress`, `BadProvenance`, `BadSides`, `BadR`) ไม่มีกรณีไหนคืนค่า และกรณีขอบที่ถูกต้อง (lots 0.01, 200; spread 0; nights 0; factor 1; sides 0) ผ่านด้วยค่าที่ระบุ
- AC-06 Given `H001_COSTS`, When อ่าน provenance และเรียก `unknowns`, Then ทุกฟิลด์ตัวเลข 11 ฟิลด์มี provenance ที่ `as_of = 2026-10-21`, สถานะตรงตาราง, `unknowns(H001_COSTS) == ("commission_per_lot_per_side", "slippage_points_per_side", "triple_swap_weekday")`, note ของ swap ทั้งสองมี `UNKNOWN`, และ `stress(H001_COSTS).provenance == H001_COSTS.provenance` · `CostModel`, `Provenance`, `CostBreakdown` แก้ค่าไม่ได้ (`FrozenInstanceError`)
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
- ความเสี่ยงรอง: ค่า assumed ถูกใช้เหมือนค่าจริง → ลดด้วย provenance ที่บังคับทุกฟิลด์และ `unknowns()` ที่รายงานต้องแสดงใน R1 · swap ย้อนหลังเป็น UNKNOWN โดยนิยาม จึงต้องให้ R1 แสดงสัดส่วน PnL ที่ขึ้นกับ swap ควบคู่ stress ×2 (ด่าน 13a)
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
5. Decisions needed from the owner: (ก) อนุมัติ acceptance 7 ข้อ (ข) ยืนยันว่าค่า [A] ของ H001 (commission 0, slippage 50 points, พุธคิด 3 เท่า) เข้า model ด้วยสถานะ `assumed` ตามตาราง — ไม่ใช่การยืนยันค่า แค่ยืนยันการติดป้าย (ค) ถ้า Codex ขอ `hypothesis` ให้ตัดสินตอน admission

## Authorization (filled by the owner)
- Claude Code / เขียน `src/sochron/costs/**`, `tests/unit/costs/**`, evidence, handoff, PROGRESS / repo นี้ / จนกว่า CORE-002 จะ done — รอเจ้าของกรอก (ร่าง: อนุมัติพร้อม acceptance)
- Codex / เขียน tests ที่ล็อกเป็น patch ใน `docs/proposals/` / `tests/acceptance/CORE-002`, `tests/golden/CORE-002`, `tests/architecture` / งานนี้ — รอเจ้าของกรอก (ร่าง: อนุมัติพร้อม acceptance)
- ไม่มีการเชื่อม terminal หรือบัญชีใดๆ ในงานนี้ · ไม่มี dependency ใหม่เว้นแต่ผ่าน admission

## Budget
2 sessions · 3 attempts ต่อ test ที่ล้มโดยไม่มีหลักฐานใหม่ แล้วหยุดขอ second opinion · Codex headless ไม่เกิน 5 รัน (tests, review, re-review ×2, สำรอง; admission เพิ่มถ้าขอ `hypothesis`) · ไม่มีค่าใช้จ่ายเงิน

## Recovery, compensation and checkpoint
ลบ `src/sochron/costs`, tests ของ CORE-002 แล้วทิ้ง branch ได้ทั้งก้อน ไม่มีผลข้างเคียงนอกเครื่อง · checkpoint ใน PROGRESS.md หลังทุกขั้นที่ผ่าน check

## DoR status / missing items / next action
- ครบ: นิยามต้นทุนใน H001 (committed), spec สัญลักษณ์จาก SPIKE-001, สภาพแวดล้อม uv (D-012), สิทธิ์ branch/push ตาม D-006
- ขาด: การอนุมัติ acceptance จากเจ้าของ · tests จาก Codex (patch)
- next action: เจ้าของอนุมัติ acceptance → commit contract (approved) → Codex `$write-acceptance-tests CORE-002`

## Done scope
implementation (ทดสอบผ่านบนเครื่อง, review ปิด, merge แล้ว) · ยังไม่รวม Python CI job และการนับคืน swap จากเวลา
