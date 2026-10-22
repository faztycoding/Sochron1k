# TASK CORE-003 — risk: sizing, halt state และ risk gate แบบ pure (ค่า risk policy เป็น parameter ที่มีที่มา)

Version v1.7 (v1 ร่าง 2026-10-22 07:0x → v1.1 07:3x แก้ตาม `docs/reviews/CORE-003-contract-r1.md` F1–F10 และคำตัดสินของเจ้าของ 3 ข้อ → v1.2 07:4x แก้ F6, F11, F12 ของ `CORE-003-contract-r2.md` และเปิดเผยทางเลือก (ช) → v1.3 09:0x ตาม `docs/reviews/CORE-003-security-pre-r1.md`: exact types, ตรวจซ้ำตอนใช้งาน, `check_entry` รับ `day` และเหตุผล `stale_state` (F6), เพดานขนาดตัวเลข (F3), ข้อบังคับ E1 (F7, L1–L4), ถ้อยคำ invariant (F8); contract review r4 F13/F14 ชี้แจงข้อยกเว้นของ provenance container และวิธีจับเวลา → v1.4 10:2x: `docs/reviews/CORE-003-tests-r2.md` F1 (watchdog ใช้ `faulthandler`) และ F3 (ตรวจ policy ซ้ำทุกจุดที่ใช้) ตามที่เจ้าของเลือก, `docs/reviews/CORE-003-r1.md` F1 (โดเมนของฟิลด์ model ตรวจซ้ำตอนใช้), งบ Codex 12 รัน → v1.5 10:5x: `docs/reviews/CORE-003-security-pre-r2.md` F12 (lots ที่เกินเพดานใน `size_position`), F10 (ยอมรับ ผูกกับ E1 L3), F13 (E1 ข้อ L5) ตามที่เจ้าของเลือก → v1.6 19:xx: `docs/reviews/CORE-003-tests-r3.md` F4 (เขียนพฤติกรรมของ F9 ลง contract ตามที่เจ้าของเลือก) และ `docs/reviews/CORE-003-r2.md` F4/F5 (key ของ provenance เป็น `str` พอดี, ผลของ start/update/restart ไม่อ่าน policy ซ้ำ) → v1.7 20:2x: `docs/reviews/CORE-003-r3.md` F6/F7 ขอบเขตของการป้องกันและ E1 ข้อ L2 ที่ขยาย ตามที่เจ้าของเลือก) · Owner เจ้าของ repository · Parent SPEC ข้อ 6 (Risk policy [A]) และ Q-04 · `docs/architecture.md` ข้อ 8 แถว `risk`, ข้อ 9 ("ไม่มีคำสั่งไหนถูกส่งโดยไม่ผ่าน risk gate") และข้อ 13a แถว E1 · AGENTS.md "Trading and research invariants" · Tier **High** · Branch `feat/CORE-003-risk`
Status: **approved by owner 2026-10-22 07:4x** (แผน, acceptance 7 ข้อ และทางเลือก (ก)–(ช) ทั้งหมด อนุมัติในแชท Claude หลัง contract reviews r1–r3 ปิดครบ) · **v1.3 การเปลี่ยนที่เจ้าของเลือก 2026-10-22 08:5x** หลัง security pre-review: F6 = ให้ด่านรับวันไทย, F3 = ใส่เพดานตัวเลข, F7 = ห้ามในระดับ E1 · tests ที่ล็อกต้องแก้ตาม (Codex patch) · **v1.4 เจ้าของเลือก 2026-10-22 10:1x** หลัง fresh review ของ tests r2: F1 = ใส่ `faulthandler`, F3 = เขียนยืนยันใน contract, งบ Codex headless เพิ่มเป็น 12 รัน · โดเมนของ model (review r1 F1) Claude เพิ่มเป็นข้อชี้แจงที่เข้มขึ้น เจ้าของ veto ได้ · **v1.5 เจ้าของเลือก 2026-10-22 10:5x** หลัง security pre-review r2: F10 = ยอมรับและผูกกับ E1, F12 = เขียนใน contract, F13 = E1 ข้อ L5 (F9, F11 แก้ในโค้ด ไม่เปลี่ยน contract) · **v1.6 เจ้าของเลือก 2026-10-22 11:2x** หลัง fresh review ของ tests r3: F1, F3 = ให้ Codex แก้ใน patch r4, F2 = ยอมรับ (unit test ของผู้ทำจับได้), F4 = เขียนใน contract, วิธีพิสูจน์ mutation โดยรัน tests ที่ล็อกจากที่เดิมกับโค้ดเก่าใน scratch = ยอมรับ · **v1.7 เจ้าของเลือก 2026-10-22 20:2x** หลัง implementation review r3 (Claude reviewer ภายใต้การสลับบทบาท): F6/F7 = กำหนดขอบเขตและผูก E1 L2 ไม่แก้โค้ด · tests-r4 F1 = unit test นับการอ่าน provenance (ไม่ทำ patch tests ที่ล็อกเพิ่ม) · tests-r4 F2 = ประโยคลำดับการตรวจ key (Claude เขียนตามที่เจ้าของฝากให้จัดการ) · เจ้าของเลือก 2026-10-22: ร่างแบบรับค่าเป็น parameter ติดป้าย assumed (ไม่รอ Q-04) · คำตัดสินของเจ้าของ 2026-10-22 07:2x หลัง contract review r1: (1) restart ในวันเดียวกันคง daily halt ไว้ (2) sizing ตั้งต้นไม่รวมต้นทุนให้ตรง H001 แต่รองรับ `cost_per_lot`; E1 เป็นผู้เลือก (3) Tier High
Hypothesis (research tasks): ไม่ใช่งานวิจัย แต่ให้บริการ H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`, commit `0c392a9`) ข้อ 3 Position size และ "1 สถานะต่อครั้ง" · ไม่มีการรันข้อมูลตลาด

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: yes (ระดับ policy) — มี allowlist ของผู้มีสิทธิ์เริ่ม/ปลดการทดลอง (`halt_clearers`) แต่ไม่มีระบบยืนยันตัวตน: ชื่อที่ส่งมาไม่ใช่หลักฐานว่ามนุษย์อนุมัติจริง การผูกกับตัวตนจริงเป็นงานของ E1
- Q2 real money: no — ไม่มีเส้นทางส่งคำสั่ง; โมดูลนี้ตัดสิน "อนุญาต/ไม่อนุญาต" เท่านั้น
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: **yes** — งานนี้เพิ่มการบังคับ risk policy, การเปลี่ยนสถานะ halt และสิทธิ์ปลด halt (Handbook Q6 รวม policy) · tests ที่ล็อกเขียนโดย Codex และเข้า repo ผ่าน patch ใน `docs/proposals/` ตาม D-006

เป็น **High** (contract review r1 F4, เจ้าของยืนยัน 2026-10-22): ด่าน risk ต้องเป็นโค้ด deterministic นอกอำนาจ AI และจะอยู่หน้าทุกคำสั่งใน E1 · ผลของ High: เจ้าของอนุมัติแผนและ acceptance ก่อนลงมือ, security-reviewer pre-review ก่อน Codex review, เจ้าของรัน demo เองก่อน merge, PR ต้องติด label

## Goal / user outcome (Thai)
มีโมดูลเดียวชื่อ `sochron.risk` ที่ backtest (R1) และ execution (E1) ใช้ตัดสินเรื่องความเสี่ยงแบบเดียวกัน โดย:
- **คำนวณขนาด lots** ตามสูตรของ H001: `R = risk_per_trade × equity`, `lots = floor_step( R / (ระยะ SL × contract_size + cost_per_lot) )` แบบตรรกยะ exact · ต่ำกว่า volume ขั้นต่ำ → ไม่เปิดไม้ (`below_min_volume`) · เกิน volume สูงสุด → จำกัดที่จุดสูงสุดบน grid · `cost_per_lot` ตั้งต้น 0 = ทวนสูตรที่ลงทะเบียนใน H001 เท่านั้น ไม่ใช่หลักฐานว่าผ่าน SPEC ข้อ 6 ที่ "รวม cost budget"; contract E1 เป็นผู้เลือกสูตรและ budget (คำตัดสินของเจ้าของ 2026-10-22)
- **halt state ผูกกับ policy ของการทดลอง**: หยุดรายวันเมื่อขาดทุนถึง 0.75% ของ equity ต้นวันไทย (ปลดเมื่อขึ้นวันไทยใหม่เท่านั้น) · หยุดการทดลองเมื่อขาดทุนถึง 2% ของ equity ตั้งต้น (ไม่ปลดเอง ต้อง restart โดยผู้มีสิทธิ์พร้อมเหตุผล และ restart ไม่ปลดหยุดรายวันของวันเดียวกัน)
- **risk gate ก่อนเปิดไม้คำนวณ sizing ใหม่จากคำขอจริง** (equity ปัจจุบัน, ระยะ |entry − SL|, model, cost budget, policy ของการทดลอง) แล้วตอบว่าอนุญาตหรือไม่ พร้อมทุกเหตุผลที่ไม่อนุญาต
- **gate ของการแก้ SL**: ห้ามขยาย SL และห้ามเอา SL ออก (AGENTS.md: never widen a stop loss) · ขยับเข้าใกล้ราคาได้
- **ค่า policy ทุกตัวเป็น parameter ที่มีที่มา** (`Provenance` เดียวกับ costs) · `H001_RISK`: 4 ค่าตัวเลข/จำนวนจาก SPEC ข้อ 6 สถานะ `assumed` และ `halt_clearers` สถานะ `unknown` จนกว่าเจ้าของตอบ Q-04
- เงิน, lots, ราคา และสัดส่วนเป็น `Decimal` · ไม่มี I/O ไม่อ่านนาฬิกา ไม่ import `MetaTrader5` · วันไทยรับเป็น `date` จากผู้เรียก (ผู้เรียกใช้ `timebase.bangkok_date`; module map ให้ `risk` import ได้เฉพาะ `core` และ `costs`)

## Current behavior and evidence (revision)
ที่ `feat/CORE-002-costs` (`47151e8`, รอ merge): มี `sochron.timebase` และ `sochron.costs` · ไม่มีโค้ด risk · ค่า risk อยู่ใน SPEC ข้อ 6 เป็น [A] (0.25% ต่อเทรดรวม cost budget, หยุดรายวัน 0.75% จาก baseline วันไทย, หยุดการทดลอง 2% จากทุนตั้งต้น, position หรือ pending ได้ครั้งละ 1) และ Q-04 ยังเปิด (รวม "ใครปลด halt ได้") · สูตร sizing และ worked example อยู่ใน H001 ข้อ 3 (equity 10,000 → R 25, ระยะ SL 12.00 → 0.02 lots, เสี่ยงจริง 24 USD) · H001 ไม่รวมต้นทุนในสูตร sizing ซึ่งต่างจาก SPEC ข้อ 6 · H001 ไม่ได้กำหนดกติกา halt ของการวิจัย: contract R1 ต้องระบุว่ากติกา halt ของโมดูลนี้ใช้กับการวิจัยหรือไม่ โดยไม่แก้สมมติฐานที่ลงทะเบียนแล้ว

## Scope
- In scope: แพ็กเกจ `sochron.risk` ตาม API ด้านล่าง · unit tests ของผู้ทำ · acceptance, golden และ architecture tests โดย Codex (ขยาย `tests/architecture/test_imports.py` ให้ครอบ `sochron.risk`) · หลักฐานใน `docs/evidence/CORE-003.md` · handoff
- Exclusions: การส่งหรือแก้คำสั่งจริง (E1) · journal และการบันทึก/กู้ halt state จากดิสก์ (E1/journal) · การยืนยันตัวตนผู้ปลด halt · การคำนวณวันไทยจากเวลา (ผู้เรียกใช้ `timebase`) · การคำนวณ PnL และ equity (ผู้เรียกส่ง equity มา) · การเลือก `cost_per_lot` ของ R1/E1 · การเปลี่ยน policy ระหว่างรัน
- Allowed files/modules: `src/sochron/risk/**`, `tests/unit/risk/**`, `docs/evidence/CORE-003.md`, `docs/handoff/CORE-003.md`, `PROGRESS.md` · โดย Codex ผ่าน patch: `tests/acceptance/CORE-003/**`, `tests/golden/CORE-003/**`, `tests/architecture/**`
- Must not touch: `src/sochron/timebase/**`, `src/sochron/costs/**`, `src/sochron/core/**`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`, `docs/hypotheses/**`, `research/**`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests (เปลี่ยนไม่ได้โดยผู้ทำ) · ทุกฟังก์ชันเป็น pure · เงิน, lots, ราคา และสัดส่วนเป็น `decimal.Decimal` เท่านั้น · จำนวนนับเป็น `int` · ชนิดผิดทุกตำแหน่ง (รวม `float` และ `bool`) → `TypeError` ไม่มีการแปลงค่าอัตโนมัติ · ตัวเลขในข้อความเป็นค่าเชิงคณิตศาสตร์; ใน API และ golden tests สร้างจาก Decimal string เสมอ

### Exact arithmetic และการแสดงผล (ตอบ F7)
- R, risk ต่อ lot, floor/cap/grid ของ lots และการเทียบเกณฑ์ขาดทุนทุกข้อ คำนวณจาก input เดิมแบบตรรกยะ exact (เช่น `Decimal.as_integer_ratio()` และจำนวนเต็ม) ไม่ปัดก่อนตัดสิน
- `lots` ที่คืนเป็น Decimal ของ (จำนวน step ที่ได้แบบ exact) × `volume_step` ซึ่งเป็นค่า exact
- ฟิลด์แสดงผล `risk_money`, `risk_per_lot`, `actual_risk` ปัด **ครั้งเดียว** จากค่า exact ของแต่ละฟิลด์ใน `localcontext(sochron.costs.CONTEXT)` (precision 28, ROUND_HALF_EVEN) ไม่ quantize เป็นสตางค์ และไม่ใช้ค่าที่ปัดแล้วตัดสินใดๆ · `actual_risk` = ค่า exact ของ lots × risk ต่อ lot (exact) แล้วจึงปัดเพื่อแสดง · ไม่แก้ context ของผู้เรียก
- ฟิลด์แสดงผล `risk_money`, `risk_per_lot`, `actual_risk` ปัดครั้งเดียวจากค่า exact ภายใต้สำเนา `localcontext(CONTEXT)` โดยเปิด traps ของ `Overflow` และ `Underflow` และแปลงสอง exception นี้เป็น `RiskError`; อนุญาตผล subnormal ที่แทนค่า exact ได้ (`Subnormal` เพียงอย่างเดียวไม่เป็น error) แต่ไม่อนุญาตการปัด subnormal แบบ inexact รวมถึงการปัดค่าที่ไม่ใช่ศูนย์ให้เป็นศูนย์; ไม่ตรวจ exponent โดยเทียบกับ `Emin` เพียงอย่างเดียว และไม่แก้ context ของผู้เรียก (contract review r2 F6) · ตัวอย่าง: R exact `1E-1000000` รับได้, R exact `1E-1000027` → `RiskError`
- golden เทียบชนิด `Decimal` และค่าเชิงตัวเลขด้วย `==` ไม่เทียบ exponent หรือรูปแบบ string

```text
sochron.risk
  RiskPolicy (frozen dataclass):
      risk_per_trade: Decimal            # สัดส่วนของ equity ต่อเทรด, 0 < x < 1
      daily_loss_limit: Decimal          # สัดส่วนของ equity ต้นวันไทย, 0 < x < 1
      experiment_loss_limit: Decimal     # สัดส่วนของ equity ตั้งต้นการทดลอง, 0 < x < 1
      max_open_exposures: int            # จำนวน position + pending order สูงสุด, ≥ 1
      halt_clearers: tuple[str, ...]     # ผู้มีสิทธิ์เริ่ม/ restart การทดลอง: ไม่ว่าง, ชื่อไม่ว่างหลังตัดช่องว่าง, ไม่ซ้ำ
      provenance: Mapping[str, Provenance]   # Provenance จาก sochron.costs · key = 5 ฟิลด์ข้างบนพอดี · เก็บเป็นสำเนา immutable
  H001_RISK: RiskPolicy        # ค่าและ provenance ตามตารางด้านล่าง (ค่า literal)
  unknowns(policy: RiskPolicy) -> tuple[str, ...]   # ชื่อฟิลด์ที่ status เป็น assumed หรือ unknown เรียงตามตัวอักษร

  SizeDecision (frozen dataclass): lots: Decimal, risk_money: Decimal, risk_per_lot: Decimal, actual_risk: Decimal,
                                   reason: Literal["ok", "below_min_volume", "capped_at_volume_max"]
      # ความสอดคล้อง: reason == "below_min_volume" ⇔ lots == 0 · lots ≥ 0 · ทุกฟิลด์ finite
  size_position(equity: Decimal, stop_distance: Decimal, model: CostModel, policy: RiskPolicy,
                cost_per_lot: Decimal = Decimal("0")) -> SizeDecision
      # risk_money = policy.risk_per_trade × equity
      # risk_per_lot = stop_distance × model.contract_size + cost_per_lot          (USD ต่อ 1 lot; stop_distance เป็นราคา USD/oz)
      # uncapped = floor(risk_money ÷ risk_per_lot ÷ model.volume_step) × model.volume_step     (exact)
      # max_on_grid = floor(model.volume_max ÷ model.volume_step) × model.volume_step         (exact)
      # lots = min(uncapped, max_on_grid)
      # ถ้า lots < model.volume_min → lots = 0, reason "below_min_volume"
      # มิฉะนั้น reason "capped_at_volume_max" ถ้า uncapped > max_on_grid ไม่งั้น "ok"
      # actual_risk = lots × risk_per_lot · ไม่ใช้ stress_factor ของ model
      # cost_per_lot = 0 ใช้ทวนสูตร H001 เท่านั้น ไม่ใช่หลักฐานว่าผ่าน SPEC ที่รวม cost budget

  HaltState (frozen dataclass): policy: RiskPolicy, day: date, day_start_equity: Decimal, experiment_start_equity: Decimal,
                                daily_halted: bool, experiment_halted: bool
  start_experiment(equity: Decimal, day: date, policy: RiskPolicy, authorized_by: str, reason: str) -> HaltState
      # เริ่มการทดลองใหม่ที่ได้รับอนุมัติ: authorized_by ต้องอยู่ใน policy.halt_clearers (เทียบตรงตัว) และ reason ไม่ว่างหลังตัดช่องว่าง ไม่งั้น BadHaltClear
      # ผล: policy ผูกกับ state, baseline ทั้งสอง = equity, ไม่ halt
      # ไม่ใช่ API สำหรับ process restart: E1 ต้องกู้ policy, baselines และ flags ของการทดลองเดิมจาก journal และเมื่อ state หายหรือไม่ทราบให้หยุด ไม่เริ่มใหม่อัตโนมัติ
  update_equity(state: HaltState, equity: Decimal, day: date) -> HaltState      # ใช้ state.policy เท่านั้น
      # day < state.day → TimeReversal (ข้อมูลผิดลำดับ: รายงาน ไม่ซ่อม)
      # day == state.day → คง day_start_equity; daily_halted = state.daily_halted or (day_start_equity − equity ≥ daily_loss_limit × day_start_equity)
      # day > state.day → day = day, day_start_equity = equity, daily_halted = False (ไม่เทียบกับ baseline วันก่อน)
      # ทุกกรณี: คง experiment_start_equity; experiment_halted = state.experiment_halted or (experiment_start_equity − equity ≥ experiment_loss_limit × experiment_start_equity)
      # การเทียบทั้งหมด exact และรวมค่าที่เท่ากับเกณฑ์พอดี
      # baseline ต้นวันไทย = equity แรกที่ผู้เรียกส่งมาในวันนั้น: ผู้เรียกมีหน้าที่ส่ง equity ณ ขอบวันไทย (00:00 Asia/Bangkok) เป็นค่าแรก
  restart_experiment(state: HaltState, equity: Decimal, day: date, authorized_by: str, reason: str) -> HaltState
      # อนุญาตเฉพาะเมื่อ state.experiment_halted เป็น True ไม่งั้น BadHaltClear (ไม่ใช้ restart เพื่อต่อ budget ของการทดลองที่ยังไม่ halt)
      # authorized_by ต้องอยู่ใน state.policy.halt_clearers และ reason ไม่ว่าง ไม่งั้น BadHaltClear · day < state.day → TimeReversal
      # ประเมินกฎรายวันด้วย equity/day ที่ส่งมาตามกฎเดียวกับ update_equity (วันเดิมคง baseline และ latch; วันใหม่ใช้ rollover) แล้วคงผลนั้น
      # reset เฉพาะ experiment_start_equity = equity และ experiment_halted = False · policy เดิม (คำตัดสินของเจ้าของ: restart ไม่ปลดหยุดรายวัน)

  EntryRequest (frozen dataclass): side: Literal["long", "short"], lots: Decimal, entry_price: Decimal, stop_loss: Decimal | None, open_exposures: int
  GateDecision (frozen dataclass): allowed: bool, reasons: tuple[str, ...]
      # ความสอดคล้อง: allowed == (reasons == ()) · reasons เรียงตามตัวอักษร ไม่ซ้ำ และทุกตัวอยู่ในชุดเหตุผลที่ระบุใน check_entry/check_stop_change
  check_entry(request: EntryRequest, equity: Decimal, day: date, state: HaltState, model: CostModel,
              cost_per_lot: Decimal = Decimal("0")) -> GateDecision
      # v1.3 (security pre-review F6, เจ้าของเลือก 2026-10-22): day = วันไทยของคำขอ (ผู้เรียกใช้ timebase.bangkok_date)
      #   day < state.day → TimeReversal · day > state.day → เหตุผล "stale_state" (state ยังไม่ถูกเลื่อนด้วย update_equity) และประเมินเหตุผลอื่นตามปกติด้วยค่าใน state
      # ตรวจชนิดและโดเมนของทุก argument ก่อน (ตามตาราง; ตรวจซ้ำทุกฟิลด์ของ request และ state ตอนใช้งาน ไม่พึ่งการตรวจตอนสร้างอย่างเดียว) แล้วรวบรวมเหตุผลทุกข้อที่เข้าเงื่อนไข:
      #   "daily_halt" ถ้า state.daily_halted or (state.day_start_equity − equity ≥ state.policy.daily_loss_limit × state.day_start_equity)
      #   "experiment_halt" ถ้า state.experiment_halted or (state.experiment_start_equity − equity ≥ state.policy.experiment_loss_limit × state.experiment_start_equity)
      #   (ทั้งสองแบบ exact: gate ไม่อนุญาตที่เกณฑ์หยุดแม้ state ยังไม่ได้อัปเดต; contract review r2 F11)
      #   ผู้เรียกต้องส่ง state ที่เลื่อนเป็นวันไทยของคำขอด้วย update_equity และเก็บ state ที่คืนก่อนเรียก gate ทุกครั้ง เพื่อคง latch แม้ equity ฟื้นในครั้งถัดไป; gate ไม่แก้ state เดิม
      #   "max_exposure" ถ้า request.open_exposures ≥ state.policy.max_open_exposures
      #   "missing_stop_loss" ถ้า stop_loss is None
      #   "stop_loss_wrong_side" ถ้า long และ stop_loss ≥ entry_price หรือ short และ stop_loss ≤ entry_price
      #   "lots_not_on_grid" ถ้า request.lots ไม่อยู่ใน [volume_min, volume_max] ของ model หรือไม่เป็นพหุคูณ exact ของ volume_step (รวม lots ≤ 0)
      #   เมื่อมี SL ฝั่งถูกต้องเท่านั้น: sized = size_position(equity, |entry_price − stop_loss|, model, state.policy, cost_per_lot) (exact)
      #     "below_min_volume" ถ้า sized.reason == "below_min_volume" · "lots_exceed_sized" ถ้า request.lots > sized.lots
      #   "stale_state" ถ้า day > state.day (v1.3)
      # ไม่รับ SizeDecision จากภายนอก: อนุญาตได้เฉพาะ lots ที่ไม่เกินผล sizing ของคำขอนี้เอง
  check_stop_change(side: Literal["long", "short"], current_stop: Decimal, new_stop: Decimal | None) -> GateDecision
      # new_stop is None → ("missing_stop_loss",) · long และ new_stop < current_stop → ("stop_loss_widened",)
      # short และ new_stop > current_stop → ("stop_loss_widened",) · เท่าเดิมหรือขยับเข้าหาราคา → allowed
  errors (ทั้งหมดสืบจาก RiskError(ValueError)): BadPolicy · BadEquity · BadStop · BadHaltClear · TimeReversal
```

### ชนิด โดเมน และ error (ตอบ F6)
ตรวจชนิดและโดเมนของ dataclass ตอนสร้าง และของ argument ก่อนเลือก branch หรือคืน `GateDecision` · input ผิดหลายอย่างพร้อมกันไม่กำหนดลำดับ exception (acceptance ทดสอบทีละความผิด) · เมื่อ input ถูกต้องทั้งหมดจึงรวบรวมเหตุผลปฏิเสธ · halt ที่มีอยู่แล้วไม่ทำให้ข้ามการตรวจ input

| Input / โดเมน | ผล |
|---|---|
| ชนิดผิดของ scalar หรือ object (Decimal ได้ int/str/bool/float; int ได้ bool/Decimal/float; model/policy/state/request ผิดชนิด; `halt_clearers` ไม่ใช่ tuple หรือสมาชิกไม่ใช่ str; `authorized_by`/`reason` ไม่ใช่ str; provenance ไม่ใช่ Mapping) · **v1.3: ต้องเป็นชนิดนั้นพอดี (`type(x) is T`) subclass ทุกชนิดไม่รับ** รวมถึงฟิลด์ของ `CostModel` ที่ risk อ่าน (`contract_size`, `volume_min`, `volume_step`, `volume_max` ต้องเป็น `Decimal` พอดี) และค่าใน provenance ต้องเป็น `Provenance` พอดี (security pre-review F1) · **ยกเว้น container ของ provenance** (contract review r4 F13): รับทุกชนิดที่เป็น `collections.abc.Mapping` (เช่น `dict`, `MappingProxyType`) โดยอ่านครั้งเดียวเป็นสำเนา ตรวจสำเนานั้น แล้วเก็บเป็น `MappingProxyType` ของสำเนา · container ที่ไม่ใช่ `Mapping` → `TypeError` | `TypeError` (ค่าใน provenance ที่ไม่ใช่ `Provenance` พอดี → `BadPolicy`) |
| **v1.3 เพดานขนาดตัวเลข (security pre-review F3, เจ้าของเลือก 2026-10-22):** Decimal ทุกตัวที่ risk รับ (argument, ฟิลด์ของ dataclass ของ risk, ฟิลด์ของ model ที่อ่าน) ต้องมี coefficient ไม่เกิน 1,000 หลัก และถ้าไม่เป็นศูนย์ ต้องมี `abs(value.adjusted()) ≤ 1_100_000` ตรวจก่อนแปลงเป็นตรรกยะ | error ของช่องนั้นตามตารางนี้ (`BadEquity` สำหรับ equity/baseline, `BadStop` สำหรับราคา/SL/ระยะ, `BadPolicy` สำหรับสัดส่วนของ policy และ `cost_per_lot`, `RiskError` สำหรับ lots และฟิลด์ของ model) · เกณฑ์เวลา (contract review r4 F14) ใช้กับ **การปฏิเสธ input ที่เกินเพดานเท่านั้น**: ใช้ Decimal ที่สร้างไว้ก่อน (ไม่นับการสร้าง, import หรือการเริ่ม process) จับเวลาด้วย `time.perf_counter()` ตั้งแต่เรียกฟังก์ชันสาธารณะจนได้ exception ที่คาด ทุกครั้งต้องน้อยกว่า 1.000 วินาที บนเครื่องอ้างอิง Windows 11 + Python 3.12.15 ผ่าน uv · harness รันการเรียกใน daemon thread และ `join(timeout=10)` เพื่อไม่ให้ regression ค้างทั้ง suite · **v1.4 (tests-r2 F1, เจ้าของเลือก):** thread หยุด C call ที่ถือ GIL ไม่ได้ ดังนั้นก่อนเริ่ม thread harness ตั้ง `faulthandler.dump_traceback_later(20, exit=True)` และเรียก `faulthandler.cancel_dump_traceback_later()` ใน `finally` หลัง join ทุกกรณี เมื่อการเรียกค้างเกิน 20 วินาที process จบพร้อม traceback และ exit code ไม่เป็น 0 (fail ไม่ใช่ค้าง) · ไม่ใช้เกณฑ์นี้กับ input ที่อยู่ในเพดาน |
| `check_entry` กับ `day` ที่ไม่ใช่ `date` พอดี · `day < state.day` | `TypeError` · `TimeReversal` |
| ฟิลด์ของ `EntryRequest`/`HaltState` ที่ถูกแก้หลังสร้าง (เช่นด้วย `object.__setattr__`) | ตรวจซ้ำตอนใช้งานใน `check_entry`, `update_equity`, `restart_experiment` และให้ error ตามตารางนี้ (security pre-review F4) · การตั้ง latch เป็น False เองตรวจไม่ได้ในโมดูล pure (E1 ข้อ L2) |
| v1.4 (tests-r2 F3, เจ้าของเลือก): ฟิลด์ของ `RiskPolicy` ที่ถูกแก้หลังสร้าง ทั้ง policy ที่ส่งเป็น argument และ `state.policy` | ตรวจซ้ำทุกฟิลด์ด้วยกติกาเดียวกับตอนสร้างทุกครั้งที่ใช้: `size_position`, `start_experiment`, `unknowns`, การสร้าง `HaltState` และ `state.policy` ใน `check_entry`, `update_equity`, `restart_experiment` · error ตามตารางนี้ (`BadPolicy` สำหรับโดเมน, `TypeError` สำหรับชนิด) |
| v1.6 (tests-r3 F4 เจ้าของเลือก; review r2 F4/F5): โค้ดของผู้เรียกที่ทำงานระหว่างการตรวจ (เช่น Mapping ที่ฝังใน provenance หลังสร้าง) | อ่าน provenance ครั้งเดียวต่อการเรียก ก่อนฟิลด์อื่นทั้งหมด · key ของ provenance ต้องเป็น `str` พอดี → ไม่งั้น `TypeError` และการตรวจชนิดของ key นี้ทำก่อนการตรวจ provenance อย่างอื่น (ชุด key ขาด/เกิน และชนิดของค่า) จึงเป็นข้อยกเว้นของ "หลายความผิดไม่กำหนดลำดับ": key ที่ไม่ใช่ `str` พอดีได้ `TypeError` เสมอ แม้ทำให้ชุด key ผิดด้วย (tests-r4 F2) · `check_entry` ไม่คืน `allowed=True` ให้คำขอหรือ state ที่ถูกแก้ระหว่างตรวจ (ตรวจคำขอหลังจาก state/policy หรือปฏิเสธด้วย error ตามตาราง) · `start_experiment`, `update_equity`, `restart_experiment` คืน state ที่ผูกกับ policy object ตัวเดิมที่ตรวจแล้วในการเรียกนั้น และสร้างผลจากค่าที่ตรวจแล้วโดยไม่อ่าน policy ซ้ำหลังตัดสิน |
| v1.4 (review r1 F1): ฟิลด์ของ `CostModel` ที่ risk อ่านออกนอกโดเมน (เช่นถูกแก้หลังสร้าง): `contract_size`, `volume_step` หรือ `volume_min` ≤ 0 หรือ `volume_max` < `volume_min` | `RiskError` ตรวจทุกครั้งที่ใช้ใน `size_position` และ `check_entry` ก่อนเลือก branch หรือรวบรวมเหตุผล (กติกาเดียวกับที่ `CostModel` ตรวจตอนสร้าง) |
| `day` ไม่ใช่ `date` หรือเป็น `datetime` (subclass ของ date) | `TypeError` |
| `side` เป็น str แต่ไม่ใช่ `"long"`/`"short"` (ทั้งใน `EntryRequest` และ `check_stop_change`) | `RiskError` |
| equity, `day_start_equity`, `experiment_start_equity` ไม่ finite หรือ ≤ 0 (รวมตอนสร้าง `HaltState` ตรงๆ) | `BadEquity` · ผู้เรียกใน R1/E1 ต้องถือ error นี้เป็นการหยุด ไม่ใช่ใช้ state เดิมต่อ |
| `stop_distance`, `entry_price`, `stop_loss` ที่ไม่ใช่ None, `current_stop`, `new_stop` ที่ไม่ใช่ None ไม่ finite หรือ ≤ 0 | `BadStop` |
| `open_exposures` < 0 | `RiskError` |
| `EntryRequest.lots` ไม่ finite (NaN, sNaN, Infinity) | `RiskError` ตอนสร้าง · lots ที่ finite แต่ ≤ 0, นอกช่วง หรือไม่ตรง grid ไม่ใช่ error แต่ได้เหตุผล `lots_not_on_grid` |
| `RiskPolicy`: สัดส่วนไม่ finite หรืออยู่นอก (0, 1) · `max_open_exposures` < 1 · `halt_clearers` ว่าง มีชื่อว่าง/ช่องว่างล้วน หรือชื่อซ้ำ · provenance ขาด/เกิน key หรือค่าไม่ใช่ `Provenance` | `BadPolicy` |
| `cost_per_lot` ไม่ finite หรือ < 0 | `BadPolicy` |
| ฟิลด์ของ `Provenance` เอง | เป็นของ `sochron.costs` ตามเดิม (`TypeError` / `BadProvenance`) |
| `authorized_by` ไม่อยู่ใน allowlist (เทียบตรงตัว ไม่ normalize) · `reason` ว่างหลังตัดช่องว่าง · restart เมื่อ experiment ไม่ halt | `BadHaltClear` |
| `day` ย้อนหลังกว่า `state.day` | `TimeReversal` |
| สร้าง `SizeDecision`/`GateDecision` ตรงๆ แบบไม่สอดคล้อง (reason กับ lots ไม่ตรงกัน, ค่าไม่ finite หรือ lots < 0, allowed ไม่ตรงกับ reasons, reasons ไม่เรียง/ซ้ำ/ไม่รู้จัก) | `RiskError` |
| v1.5 (security pre-review r2 F12, เจ้าของเลือก): `size_position` ที่ lots แบบ exact ต้องใช้ coefficient เกิน 1,000 หลัก (เพดานเดียวกับฟิลด์ของ `SizeDecision`) เช่น model ที่ `volume_step` ยาว 1,000 หลัก | `RiskError` · `check_entry` ไม่ได้รับผล: ยังตัดสินจาก sizing แบบ exact และ lots ของคำขอที่อยู่ในเพดาน จึงอาจอนุญาตคำขอที่ไม่เกินผล sizing ได้แม้ `size_position` ตอบ `RiskError` |
| ผลแสดงผลที่ทำให้เกิด `Overflow` หรือ `Underflow` ใน `CONTEXT` (รวม subnormal ที่ปัดแบบ inexact หรือปัดค่าไม่ใช่ศูนย์เป็นศูนย์) · subnormal ที่แทนค่า exact ได้ไม่ใช่ error | `RiskError` |

ค่าของ `H001_RISK` (ต้องตรงทุกตัวอักษร):

| ฟิลด์ | ค่า | Provenance(source, as_of, status, note) |
|---|---|---|
| risk_per_trade | `Decimal("0.0025")` | `"SPEC.md section 6 Risk policy [A]; docs/hypotheses/H001-m15-momentum-breakout.md section 3"`, `date(2026, 10, 21)`, `"assumed"`, `"Q-04 open"` |
| daily_loss_limit | `Decimal("0.0075")` | `"SPEC.md section 6 Risk policy [A]"`, `date(2026, 10, 21)`, `"assumed"`, `"Q-04 open; baseline is the first equity supplied for the Thai day"` |
| experiment_loss_limit | `Decimal("0.02")` | `"SPEC.md section 6 Risk policy [A]"`, `date(2026, 10, 21)`, `"assumed"`, `"Q-04 open"` |
| max_open_exposures | `1` | `"SPEC.md section 6 Risk policy [A]; docs/hypotheses/H001-m15-momentum-breakout.md section 3"`, `date(2026, 10, 21)`, `"assumed"`, `"one position or pending order at a time"` |
| halt_clearers | `("owner",)` | `"SPEC.md section 9 Q-04"`, `date(2026, 10, 22)`, `"unknown"`, `"safe default: the owner only; no agent may clear"` |

ดังนั้น `unknowns(H001_RISK) == ("daily_loss_limit", "experiment_loss_limit", "halt_clearers", "max_open_exposures", "risk_per_trade")`

## Invariants
- policy ผูกกับการทดลองตั้งแต่ `start_experiment` และอยู่ใน `HaltState`; `update_equity`, `restart_experiment` และ `check_entry` ใช้ `state.policy` เท่านั้น จึงไม่มีทางประเมินการทดลองเดิมด้วย policy อื่น · frozen ป้องกันการแก้ object แต่ไม่ใช่หลักฐานว่าผู้เรียกจะไม่ทิ้ง state: E1 ต้องกู้ state จาก journal และหยุดเมื่อ state ไม่ทราบ
- ไม่มีเส้นทางเพิ่ม risk_per_trade ตามผลขาดทุน (ห้าม martingale): sizing ขึ้นกับ equity ปัจจุบันและ policy ที่ผูกไว้เท่านั้น · gate ไม่รับผล sizing จากภายนอก
- สำหรับผู้เรียกที่ใช้ฟังก์ชันสาธารณะเท่านั้น: daily halt ปลดได้ทางเดียวคือขึ้นวันไทยใหม่ · experiment halt ปลดได้ทางเดียวคือ `restart_experiment` ที่ต้องมีชื่อใน `halt_clearers`, เหตุผลไม่ว่าง และ state ที่ halt อยู่จริง · `H001_RISK.halt_clearers` ไม่มี agent ใด · ชื่อในรายการไม่ใช่การยืนยันตัวตน · v1.3 (security pre-review F8): การสร้าง `HaltState(...)` ตรงๆ, `dataclasses.replace` บน `HaltState`/`RiskPolicy` และ `object.__setattr__` ข้ามกติกานี้ได้ จึงห้ามนอก `sochron.risk` และการกู้ state จาก journal ของ E1 (บังคับด้วย architecture test ของ E1)
- **ขอบเขตของการป้องกัน (v1.7, review r3 F6/F7, เจ้าของเลือก 2026-10-22):** `sochron.risk` กันค่าผิดชนิดหรือผิดโดเมนทุกตำแหน่ง รวมถึงค่าที่ถูกแก้หลังสร้าง (ตรวจซ้ำตอนใช้) และโค้ดของผู้เรียกที่มากับ input ที่ contract รับ (Mapping ของ provenance: อ่านครั้งเดียวต่อการเรียกก่อนฟิลด์อื่น) · ไม่กันโค้ดร้ายที่รันใน process เดียวกันและแก้ภายในของ object หรือของ runtime เช่น key แปลกปลอมใน `__dict__` ของ object (F6), hook ระดับ process ผ่าน ABC หรือ monkeypatch (F7) หรือการตั้งค่าที่ถูกกติกาแต่ผิดเจตนา (เช่น `risk_per_trade` 0.99 ด้วย `object.__setattr__`) เพราะโค้ด pure กันสิ่งเหล่านี้ไม่ได้ · การป้องกันเป็นของ E1 ข้อ L2 (architecture test) · findings F6/F7 ของ `docs/reviews/CORE-003-r3.md` ปิดด้วยการจัดสรรนี้ ไม่แก้โค้ด
- ไม่มี float ในโค้ดเงิน (AST test: ไม่มีชื่อ `float` หรือ float literal ใน `src/sochron/risk`) · import ได้เฉพาะ stdlib, `sochron.core`, `sochron.costs` · ไม่มี I/O, นาฬิกา, `MetaTrader5`, random
- เมื่อ reason เป็น `"ok"` หรือ `"capped_at_volume_max"`: ค่า exact ของ `actual_risk` ≤ ค่า exact ของ `risk_money` และ lots อยู่บน grid ของ model
- ตรวจสอบได้ด้วยมือจาก H001 ข้อ 3: `size_position(Decimal("10000"), Decimal("12.00"), H001_COSTS, H001_RISK)` → lots `0.02`, risk_money `25`, risk_per_lot `1200`, actual_risk `24`, reason `"ok"`
- ไม่มี `.skip`, `xfail` หรือ test ที่อ่อนลงใน tests ที่ล็อก · ไม่มี dependency ใหม่

## Negative cases
- sizing: equity 0 หรือ −1 → `BadEquity` · stop_distance 0 → `BadStop` · cost_per_lot −1 หรือ NaN → `BadPolicy` · float ทุกตำแหน่ง → `TypeError` · equity 100 กับ stop 12.00 → lots 0 `below_min_volume` · equity 100,000,000 กับ stop 0.10 → 200 lots `capped_at_volume_max` · raw = 0.02 พอดี (equity 9600, stop 12.00) → 0.02 ไม่ใช่ 0.01 · equity `9599.9999999999999999999999999` stop 12 → lots 0.01 (ปัด R ก่อน floor จะได้ 0.02 ผิด) · equity 800 stop `1.0000000000000000000000000001` → lots 0.01 · model สมมติ volume_max 0.025 (step 0.01) equity 10000 stop 1.00 → lots 0.02 `capped_at_volume_max` · model สมมติ volume_min 0.026, volume_max 0.029 กับ equity 10000 stop 1.00 → ไม่มีจุดบน grid ในช่วง → lots 0 `below_min_volume` (risk_per_lot 100)
- halt รายวัน: baseline 10,000 · equity 9,925.01 → ยังไม่ halt · 9,925 พอดี (ขาดทุน 75 = 0.75%) → halt · วันไทยถัดไปที่ equity 9,925 → ปลด, baseline ใหม่ 9,925 · วันถัดไปที่ equity แรก 9,900 → ไม่ halt (ไม่เทียบกับ baseline วันก่อน) baseline 9,900 · day ย้อนหลัง → `TimeReversal`
- halt การทดลอง: start 10,000 · equity 9,800 พอดี (2%) → halt และคงอยู่ข้ามวันแม้ equity กลับมา 10,500 · วันใหม่ที่ equity แรก 9,800 → daily ไม่ halt แต่ experiment halt · restart โดย `"claude"`, `"codex"`, `""` หรือ `"Owner"` → `BadHaltClear` · โดย `"owner"` แต่ reason `"  "` → `BadHaltClear` · restart ตอน experiment ไม่ halt → `BadHaltClear` · `start_experiment` โดยชื่อที่ไม่อยู่ใน allowlist → `BadHaltClear`
- restart ในวันเดียวกับ daily halt: daily_halted ยังเป็น True และ day_start_equity เดิม · restart ด้วย equity ที่ทำให้ถึงเกณฑ์รายวันในวันนั้นพอดี → daily_halted เป็น True
- gate: ทุกเหตุผลทีละข้อ และหลายเหตุผลพร้อมกัน (เรียงตามตัวอักษร) · ไม่มีการรับ SizeDecision จากภายนอก: ระยะ SL 20.00 (SL 3992.90) กับ lots 0.02 → `lots_exceed_sized` (sizing ใหม่ได้ 0.01) · request lots 0.015 หรือ 0 → `lots_not_on_grid` · SL เท่าราคาเข้า → `stop_loss_wrong_side` · request lots NaN → `RiskError` · side `"buy"` → `RiskError` · open_exposures −1 → `RiskError` · entry_price 0 → `BadStop`
- แก้ SL: long 4000.90 → 4001.00 อนุญาต · → 4000.00 `stop_loss_widened` · → None `missing_stop_loss` · short กลับทิศ · current_stop 0 → `BadStop`
- policy: risk_per_trade 0 หรือ 1 → `BadPolicy` · max_open_exposures 0 → `BadPolicy` · halt_clearers `()`, `("",)`, `(" ",)`, `("owner", "owner")` → `BadPolicy` · `["owner"]` (list) → `TypeError` · provenance ขาด key → `BadPolicy` · day เป็น `datetime` → `TypeError`

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 (กติกา fixture, contract review r2 F12: ทุกกรณีของ AC-01 เริ่มจาก `H001_COSTS`, `H001_RISK`, equity `Decimal("10000")`, stop_distance `Decimal("12.00")` และ cost_per_lot `Decimal("0")` ใหม่ แล้วเปลี่ยนเฉพาะค่าที่ระบุในกรณีนั้น ไม่สืบทอดค่าจากกรณีก่อนหน้า) Given `H001_COSTS` และ `H001_RISK`, When เรียก `size_position(Decimal("10000"), Decimal("12.00"), H001_COSTS, H001_RISK)`, Then ได้ lots `0.02`, risk_money `25`, risk_per_lot `1200`, actual_risk `24`, reason `"ok"` (ตรง H001 ข้อ 3) · ด้วย `cost_per_lot=Decimal("10")` ได้ risk_per_lot `1210` lots `0.02` actual_risk `24.2` · equity `100` → lots `0` reason `"below_min_volume"` · equity `100000000` stop `0.10` → lots `200` reason `"capped_at_volume_max"` · equity `9600` stop `12.00` (raw 0.02 พอดี) → `0.02` · equity `9599.9999999999999999999999999` stop `12` → lots `0.01` · equity `800` stop `1.0000000000000000000000000001` → lots `0.01` · model สมมติ (สำเนา `H001_COSTS` ที่แก้เฉพาะค่าที่ระบุ และ provenance ของค่านั้นเป็น `Provenance("synthetic test fixture", date(2026, 10, 22), "assumed")`) volume_max `0.025` equity `10000` stop `1.00` → lots `0.02` `"capped_at_volume_max"` · กรณีไม่มีจุดบน grid: สำเนา `H001_COSTS` ที่เปลี่ยนเฉพาะ volume_min เป็น `Decimal("0.026")` และ volume_max เป็น `Decimal("0.029")` พร้อม provenance synthetic ตามที่ระบุ, equity `Decimal("10000")`, stop_distance `Decimal("1.00")`, cost_per_lot `Decimal("0")` → lots `0`, risk_money `25`, risk_per_lot `100`, actual_risk `0`, reason `"below_min_volume"`
- AC-02 Given `start_experiment(Decimal("10000"), date(2026, 10, 22), H001_RISK, "owner", "H001 R1 run")`, When `update_equity` ด้วย 9925.01 แล้ว 9925 ในวันเดียวกัน แล้ว 9925 ในวันถัดไป, Then daily_halted เป็น False, True, False ตามลำดับ และ day_start_equity ของวันใหม่ = 9925 · จาก state เริ่มต้นเดิม ถ้าค่าแรกของวันถัดไปเป็น 9900 → daily_halted False, day_start_equity 9900, experiment_start_equity ยัง 10000 · `update_equity` ด้วยวันที่ย้อนหลัง → `TimeReversal`
- AC-03 Given การทดลองเริ่มที่ 10000, When equity ลงไป 9800 แล้วกลับเป็น 10500 ในวันถัดไป, Then experiment_halted เป็น True และยังเป็น True หลังกลับขึ้น · `restart_experiment` โดย `"claude"`, `"codex"`, `"Owner"` หรือ reason ว่าง → `BadHaltClear` · โดย `"owner"` พร้อมเหตุผล → experiment_halted False, experiment_start_equity = equity ที่ส่งมา, policy เดิม · restart ตอนไม่ halt → `BadHaltClear` · ถ้า restart ในวันเดียวกับที่ daily halt (equity 9800 จาก baseline 10000: ทั้ง daily และ experiment halt) → หลัง restart daily_halted ยัง True และ day_start_equity ยัง 10000 จนกว่าจะขึ้นวันไทยใหม่
- AC-04 Given HaltState ที่ไม่ halt จาก AC-02 (equity 10000) และ EntryRequest long lots 0.02 entry 4012.90 SL 4000.90 open_exposures 0, When `check_entry(request, Decimal("10000"), date(2026, 10, 22), state, H001_COSTS)` (ทุกแถวของ AC-04 ใช้ `day` = `state.day` เว้นแต่ระบุ), Then allowed True reasons `()` · v1.3: state ของวันที่ 22 กับ `day` = `date(2026, 10, 23)` ที่ equity 10000 → `("stale_state",)` · `day` = `date(2026, 10, 21)` → `TimeReversal` · เปลี่ยนทีละเงื่อนไขได้เหตุผล: state ที่ daily halt → `daily_halt`; experiment halt → `experiment_halt`; open_exposures 1 → `max_exposure`; SL None → `missing_stop_loss`; SL 4012.90 หรือ 4013.00 → `stop_loss_wrong_side`; lots 0.03 → `lots_exceed_sized`; SL 3992.90 (ระยะ 20 → sizing ใหม่ 0.01) กับ lots 0.02 → `lots_exceed_sized`; lots 0.015 หรือ 0 → `lots_not_on_grid`; กรณี sizing ต่ำกว่าขั้นต่ำแยก state: สร้าง state ใหม่ด้วย `start_experiment(Decimal("100"), date(2026, 10, 22), H001_RISK, "owner", "isolated sizing fixture")` แล้วใช้ request long lots 0.01 entry 4012.90 SL 4000.90 open_exposures 0 กับ equity 100 และ `H001_COSTS`, cost_per_lot 0 → `("below_min_volume", "lots_exceed_sized")` · state เริ่มต้นที่ 10000 (flags False ทั้งคู่) กับ equity ปัจจุบัน 9800 และ request long lots 0.02 entry 4012.90 SL 4000.90 open_exposures 0 → `("daily_halt", "experiment_halt")` (gate เทียบเกณฑ์จาก equity ปัจจุบัน) · หลายข้อพร้อมกันได้ทุกเหตุผลเรียงตามตัวอักษร และ allowed False
- AC-05 Given position long SL 4000.90 และ short SL 4024.90, When `check_stop_change`, Then long → 4001.00 และ 4000.90 อนุญาต, → 4000.00 ได้ `("stop_loss_widened",)`, → None ได้ `("missing_stop_loss",)` · short → 4024.00 อนุญาต, → 4025.00 ได้ `("stop_loss_widened",)`
- AC-06 Given input ผิดตามหัวข้อ Negative cases และตาราง "ชนิด โดเมน และ error", When เรียกฟังก์ชันหรือสร้าง dataclass ที่เกี่ยวข้อง, Then raise ชนิดที่ระบุ (`TypeError`, `RiskError` และลูก `BadPolicy`, `BadEquity`, `BadStop`, `BadHaltClear`, `TimeReversal`) ไม่มีกรณีไหนคืนค่า · `H001_RISK` มีค่าและ provenance ตรงตาราง literal, `unknowns(H001_RISK)` ตามที่ระบุ · `RiskPolicy`, `HaltState`, `SizeDecision`, `EntryRequest`, `GateDecision` แก้ค่าไม่ได้ (`FrozenInstanceError`) และ provenance เป็นสำเนา immutable (แก้ dict ต้นทางแล้วไม่กระทบ, แก้ผ่าน mapping proxy ไม่ได้)
- AC-07 Given โค้ดใน `src/sochron/risk`, When รัน architecture test (AST) และ `bash scripts/controls/red-flags.sh main`, Then import มีแค่ stdlib, `sochron.core`, `sochron.costs` · ไม่มีชื่อ `float`/float literal, นาฬิกา, I/O, `MetaTrader5`, random · red-flag กลุ่ม secret และ order/account mutation ว่าง · `uv run --offline pytest tests -q -p no:cacheprovider` ผ่านทั้งหมด skipped 0 (รวม tests ของ CORE-001/002 เดิม)

## Verification per AC
| AC | Verifier (test author / CI / owner demo) | Command or procedure | Evidence level |
|----|------------------------------------------|----------------------|----------------|
| 01–06 | Codex: acceptance + golden (ตารางคำนวณมือเป็น Decimal string, oracle ตรรกยะ) ใน `tests/acceptance/CORE-003`, `tests/golden/CORE-003` · Claude: unit tests | `uv run --offline pytest tests -q -p no:cacheprovider` บน Windows | L2 · L3 เมื่อมี Python CI job (งานแยก) |
| 07 | Codex: ขยาย `tests/architecture/test_imports.py` ให้ครอบ `sochron.risk` (imports + float ban) | `uv run --offline pytest tests/architecture -q` · `bash scripts/controls/red-flags.sh main` · `node scripts/controls/check-locked-paths.mjs main` | L2 |
| ทั้งหมด (High) | security-reviewer (read-only pre-review: เส้นทางเลี่ยง gate, เพิ่ม risk, ปลด halt โดยไม่มีสิทธิ์) ก่อน Codex `$cross-agent-review` · เจ้าของ | demo 3 ขั้นใน `docs/evidence/CORE-003.md` ที่เจ้าของรันเองก่อน merge: รัน suite, คำนวณ sizing ของ H001 (0.02 lots, เสี่ยง 24 USD), ลอง restart การทดลองด้วยชื่อ "claude" ต้องถูกปฏิเสธ | เจ้าของตรวจ |

## Risk, data and external side effects
- ไม่มีผลภายนอก ไม่เชื่อมต่อ terminal ไม่ใช้ข้อมูลตลาด ไม่มี dependency ใหม่
- ความเสี่ยงหลัก: floor หรือการเทียบเกณฑ์ที่ขอบพลาดเพราะการปัด → เสี่ยงเกิน R หรือ halt ช้าไปหนึ่งขั้น · ลดด้วย exact arithmetic และ golden ที่ขอบพอดี
- gate ที่ไม่ผูกกับคำขอจริงอนุญาตไม้เกินงบได้ (contract review r1 F1) → gate คำนวณ sizing ใหม่จากคำขอทุกครั้ง · E1 ต้องผูกผลของ gate กับ input ที่ส่งจริง (handoff ถึง E1)
- ค่า [A] ถูกใช้เหมือนค่าที่ยืนยันแล้ว → provenance และ `unknowns()` ซึ่ง contract ของ R1/E1 ต้องแสดง · ก่อน E1 เจ้าของต้องตอบ Q-04
- การปลด halt ตรวจแค่ชื่อ ไม่ใช่การยืนยันตัวตน · โมดูล pure ห้ามผู้เรียกทิ้ง state ไม่ได้ → E1: กู้ state จาก journal, หยุดเมื่อไม่ทราบ, ผูกชื่อผู้อนุมัติกับการยืนยันของเจ้าของ
- baseline ต้นวันไทย = equity แรกที่ส่งมา: ถ้าผู้เรียกส่งค่าแรกช้ากว่าขอบวัน ขาดทุนช่วงนั้นจะไม่ถูกนับในวันใด → ผู้เรียกต้องส่งค่า ณ ขอบวันไทย (หน้าที่ของ R1/E1)
- **ข้อบังคับที่ส่งต่อให้ contract E1** (จาก `docs/reviews/CORE-003-security-pre-r1.md`, เจ้าของเลือก F7 2026-10-22):
  - F7: ห้าม `start_experiment` ถ้า journal มี state ของบัญชีเดียวกันในวันไทยเดียวกันอยู่แล้ว (ไม่ให้การเริ่มใหม่ได้งบรายวันใหม่ในวันที่หยุดรายวัน)
  - L1: ผู้ปลด halt ต้องผ่านการยืนยันตัวตนจริง และ policy ต้องตรึงด้วยค่าหรือ digest ใน journal
  - L2: กู้ `HaltState` จาก journal เป็นทางเดียวที่สร้าง state ได้ · architecture test ห้าม `HaltState(`, `replace(` บน `HaltState`/`RiskPolicy` และ `object.__setattr__` นอก `sochron.risk` และโมดูล journal · หยุดเมื่อ state ไม่ทราบ · v1.7 (review r3 F6/F7, เจ้าของเลือก 2026-10-22): ห้ามเพิ่มเติมนอก `sochron.risk`, journal และ `tests/` ได้แก่ `vars(` และการเขียน `__dict__` ของ object, `.register(` ของ ABC (`numbers`, `collections.abc`) และการแทนที่ attribute ของ module หรือ class ระหว่างรัน (monkeypatch)
  - L3: entry_price จาก tick ปัจจุบันฝั่งที่ส่งคำสั่ง, model ตรวจกับ `symbol_info`, exposures นับจาก MT5, ส่งเฉพาะ tuple ที่ผ่าน gate · v1.5 (security pre-review r2 F10, เจ้าของยอมรับ 2026-10-22): model ที่ค่าสุดขีดแต่อยู่ในเพดาน (เช่น `volume_step` 1E-1100000) ทำให้ sizing และ gate ใช้เวลาหลายสิบวินาที จึงต้องสร้าง model จาก `symbol_info` เท่านั้น ไม่รับจากข้อความหรือ config ที่ไม่ได้ตรวจ
  - L4: `current_stop` อ่านจาก position ใน MT5 เท่านั้น
  - F6: เรียก `update_equity(state, equity, bangkok_date(now))` แล้วส่ง `day` เดียวกันให้ `check_entry` ทุกครั้ง (gate ปฏิเสธ state ค้างด้วย `stale_state` อยู่แล้ว)
  - L5 (v1.5, security pre-review r2 F13, เจ้าของเลือก 2026-10-22): equity ที่ส่งให้ `start_experiment`, `restart_experiment` และ `update_equity` ค่าแรกของแต่ละวันไทย ต้องอ่านจากช่อง equity ของบัญชีใน MT5 ณ ตอนนั้น (ไม่ใช่ balance หรือ free margin) และบันทึกค่าดิบลง journal · ไม่ตรงหรือไม่ทราบ → หยุด · baseline ที่ต่ำผิดทำให้ halt อ่อนลงทั้งการทดลอง โดยที่ `sochron.risk` ตรวจไม่ได้

## Plan, dependencies and unknowns (P06)
1. Understanding (3 lines) and likely misunderstandings: โมดูลนี้เป็น "ด่าน" ที่ตัดสินว่าเทรดได้แค่ไหนและเมื่อไรต้องหยุด จากตัวเลขที่ผู้เรียกส่งมา ไม่ใช่ตัวส่งคำสั่งหรือตัวคำนวณ equity · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่า halt รายวันปลดเมื่อ equity ฟื้นหรือเมื่อ restart — ไม่ใช่ ปลดเมื่อขึ้นวันไทยใหม่เท่านั้น (ข) คิดว่าการทดลองหยุดแล้วเริ่มเองวันถัดไป — ไม่ใช่ ต้อง restart โดยผู้มีสิทธิ์ (ค) คิดว่าค่า 0.25% ยืนยันแล้ว — ยังเป็น [A] (ง) คิดว่า gate เชื่อผล sizing ที่ส่งมา — ไม่ใช่ คำนวณใหม่จากคำขอ (จ) คิดว่า risk คำนวณวันไทยเอง — ไม่ใช่ ผู้เรียกส่ง `date` มา
2. Files to touch / what is reused: ใหม่ทั้งหมดใน `src/sochron/risk/` (`__init__.py`, `errors.py`, `policy.py`, `sizing.py`, `halts.py`, `gate.py`) · reuse จาก `sochron.costs`: `Provenance`, `CostModel`, `H001_COSTS` (ใน tests), `CONTEXT` · ไม่แก้ `costs`, `timebase`, `core`
3. Steps, each with its check:
   1. เจ้าของอนุมัติแผนและ acceptance (High) → Status approved · commit
   2. Codex contract re-review (F1–F10 ของ r1) → ready for test authoring
   3. Codex `$write-acceptance-tests CORE-003` → patch → Claude apply ตาม D-006 + ตรวจ hash + session ใหม่ตรวจ → commit red
   4. Claude implement + unit tests → `uv run --offline pytest tests -q -p no:cacheprovider` เขียว
   5. evidence + handoff → security-reviewer pre-review → Codex `$cross-agent-review` → `/fix-findings` จนไม่มี finding ค้าง
   6. เจ้าของรัน demo เอง → เปิด PR (ต้องติด label เพราะแตะ tests ที่ล็อก) หลัง PR ของ chore และ CORE-002 merge แล้ว → CI เขียว → merge
4. Risks and negative cases to test: ตามหัวข้อ Negative cases · property: `actual_risk ≤ risk_money` (exact) เมื่อ reason เป็น "ok" หรือ "capped_at_volume_max"; lots อยู่บน grid เสมอ; HaltState เดิมไม่เปลี่ยน; policy ของ state ไม่เปลี่ยนตลอดการทดลอง
5. Decisions needed from the owner:
   - ตัดสินแล้ว (2026-10-22 07:2x): restart ในวันเดียวกันคง daily halt · sizing ตั้งต้นไม่รวมต้นทุน (E1 เลือก) · Tier High
   - ยังต้องอนุมัติพร้อม acceptance (Claude เลือกแนวระมัดระวัง เจ้าของ veto ได้): (ก) restart ได้เฉพาะเมื่อการทดลอง halt อยู่ (ข) `start_experiment` ต้องมีชื่อในรายการผู้มีสิทธิ์และเหตุผลเช่นกัน (ค) baseline ต้นวันไทย = equity แรกที่ผู้เรียกส่งมา และผู้เรียกต้องส่งค่า ณ ขอบวัน (ง) equity ≤ 0 เป็น `BadEquity` และผู้เรียกต้องถือเป็นการหยุด (จ) `halt_clearers = ("owner",)` สถานะ unknown · ค่า 0.25% / 0.75% / 2% / 1 คงเป็น assumed จนกว่าตอบ Q-04 (ฉ) กติกา halt ใช้กับการวิจัย R1 หรือไม่ ให้ contract R1 เป็นผู้ระบุ (ช) experiment halt คงค้างแม้ equity ฟื้นหรือขึ้นวันใหม่ ปลดได้เฉพาะ restart ที่มีผู้มีสิทธิ์พร้อมเหตุผล และ restart ตั้ง experiment_start_equity เป็น equity ณ ตอน restart เพื่อเริ่มงบขาดทุนการทดลองใหม่ (เช่น restart ที่ 9800 → งบ 2% ถัดไป = 196 ไม่ใช่ 200; restart ที่ 10500 → 210) · daily halt ก็คงค้างแม้ equity ฟื้นภายในวันเดียวกัน (contract review r2)

## Authorization (filled by the owner)
- Claude Code / เขียน `src/sochron/risk/**`, `tests/unit/risk/**`, evidence, handoff, PROGRESS / repo นี้ / จนกว่า CORE-003 จะ done — เจ้าของอนุมัติพร้อม contract 2026-10-22 07:4x
- Codex / เขียน tests ที่ล็อกเป็น patch ใน `docs/proposals/` / `tests/acceptance/CORE-003`, `tests/golden/CORE-003`, `tests/architecture` / งานนี้ — เจ้าของอนุมัติพร้อม contract 2026-10-22 07:4x (ขั้นตอน test author ปกติ)
- ไม่มีการเชื่อม terminal หรือบัญชีใดๆ ในงานนี้ · ไม่มี dependency ใหม่

## Budget
2 sessions · 3 attempts ต่อ test ที่ล้มโดยไม่มีหลักฐานใหม่ แล้วหยุดขอ second opinion · Codex headless ไม่เกิน 12 รัน (เดิม 8; เจ้าของเพิ่ม 2026-10-22 10:1x · ใช้ไป 8 ณ 10:16: contract review r1–r5, tests r1–r2, implementation review r1) · ไม่มีค่าใช้จ่ายเงิน

## Recovery, compensation and checkpoint
ลบ `src/sochron/risk`, tests ของ CORE-003 แล้วทิ้ง branch ได้ทั้งก้อน ไม่มีผลข้างเคียงนอกเครื่อง · checkpoint ใน PROGRESS.md หลังทุกขั้นที่ผ่าน check

## DoR status / missing items / next action
- ครบ: ค่า [A] ใน SPEC ข้อ 6, สูตร sizing และ worked example ใน H001 ข้อ 3, `sochron.costs` (CORE-002) ให้ `Provenance`/`CostModel`/`CONTEXT` · contract review r1 (`docs/reviews/CORE-003-contract-r1.md`, F1–F10) → แก้ใน v1.1 · คำตัดสินของเจ้าของ 3 ข้อ
- ครบเพิ่ม: contract re-review r2 (`docs/reviews/CORE-003-contract-r2.md`) ปิด F1–F5, F7–F10 · F6 ส่วนที่เหลือ, F11 (High), F12 แก้ใน v1.2 · ทางเลือก (ช) เปิดเผยแล้ว
- ครบเพิ่ม: contract re-review r3 (`docs/reviews/CORE-003-contract-r3.md`) ปิด F6, F11, F12 → ready for test authoring · เจ้าของอนุมัติแผน, acceptance และ (ก)–(ช) 2026-10-22 07:4x
- ครบเพิ่ม (v1.3/v1.4): security pre-review r1 · contract reviews r4–r5 · Codex tests r2 + fresh review tests-r2 · implementation v1.3 · Codex implementation review r1 (F1–F3 แก้แล้ว) · CORE-002 merge แล้ว (PR #10)
- v1.4 ไม่มี Codex contract review แยก (ประหยัดงบ): Codex tests r3 อ่าน diff ของ v1.4 ก่อนเขียน และ Codex implementation review r2 ตรวจ v1.4 ด้วย
- next action: Codex tests r3 (tests-r2 F1 faulthandler, F2, F4–F6) เป็น patch → Claude apply ตาม D-006 + ตรวจ hash + session ใหม่ตรวจ → commit · Codex implementation review r2 (re-check r1 F1–F3)

## Done scope
implementation (ทดสอบผ่านบนเครื่อง, review ปิด, เจ้าของรัน demo, merge แล้ว) · ไม่รวมการผูกตัวตนผู้ปลด halt, การบันทึก/กู้ halt state และการผูกผล gate กับคำสั่งจริง (E1)
