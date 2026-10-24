# TASK CORE-006 — `strategy`: indicators และ `decide()` ของ H001 (V-A, V-B, V-C) แบบ pure และมี version

Version v1 (ร่าง 2026-10-23 15:0x) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 7 (strategy.decide - pure, versioned), ข้อ 8 แถว `strategy`, ข้อ 9 (Strategy ไม่มี I/O), AGENTS.md "One strategy implementation, a pure function shared by backtest and live" · H001 ข้อ 3 (Rules), ข้อ 4 (Parameters) · ต่อจาก CORE-005 (`Bar`, `AggregatedBar`) · Tier **Standard** · Branch `feat/CORE-006-strategy-h001`
Status: **tests started 2026-10-24 07:xx on branch `feat/CORE-006-strategy-h001` stacked on `feat/CORE-005-data-bars` before CORE-005 merges** (เจ้าของมอบอำนาจ 2026-10-24 ~07:0x "ทำให้เสร็จทั้งหมดเลย … เอา recommanded ทุกอัน": เริ่มก่อน merge เพราะ API ของ CORE-005 ผ่าน review r2 แล้ว · ถ้า CORE-005 เปลี่ยนก่อน merge ให้ merge เข้ามาและตรวจ tests ซ้ำ · veto ได้ก่อน merge) · approved by owner 2026-10-23 15:0x (acceptance AC-01–AC-07 และการตีความ H001 ตามที่แนะนำทุกข้อ D1–D5 · D6 ผู้เขียน tests และผู้ตรวจ = Claude session ใหม่ตามการสลับบทบาท) · เริ่มเขียน tests ได้หลัง CORE-005 merge (ใช้ `AggregatedBar` ที่ merge แล้ว)
Hypothesis (research tasks): H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`, registered `0c392a9`) · งานนี้เขียนกฎเป็นโค้ดเท่านั้น **ไม่รัน backtest และไม่ใช้ข้อมูลตลาดจริง** (ห้ามก่อน ENV-1 และ contract SLICE-R1) · tests ใช้ข้อมูลสังเคราะห์และตัวอย่างใน H001 ข้อ 3

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no — คืน "การตัดสินใจ" เท่านั้น สิทธิ์ส่งคำสั่งอยู่ที่ risk gate + execution (architecture ข้อ 7)
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — tests ที่ล็อกเข้า repo ผ่าน patch ตาม D-006

เป็น Standard เพราะเป็นโค้ดชุดเดียวที่ทั้ง backtest และ Demo จะใช้ ถ้ากฎผิดจากที่ลงทะเบียนไว้ ผลวิจัยจะไม่ใช่ผลของ H001

## Goal / user outcome (Thai)
มีโมดูล `sochron.strategy` ที่แปลงกฎของ H001 เป็นโค้ดตรงตัวอักษร โดยคนสองคนที่คำนวณแท่งเดียวกันได้คำตอบเดียวกัน:
- คำนวณ `EMA_f`, `EMA_s`, Wilder `ATR_n`, `TS = (EMA_f − EMA_s) / ATR_n`, `HH_N`/`LL_N`/`HH_M`/`LL_M` (ไม่รวมแท่ง t) จากแท่ง M15 ที่ปิดแล้ว
- `decide()` คืนการตัดสินใจหนึ่งอย่างต่อแท่ง: เข้า long, เข้า short, ปิด, ถือต่อ, ไม่มีสัญญาณ หรือข้ามไม้พร้อมเหตุผลครบทุกข้อ · การเข้าไม้คืนระยะ SL = `k × ATR_n[t]` ให้ผู้ส่งคำสั่งคำนวณราคา SL จากราคาที่ได้จริง
- ใช้กฎ Invalidation ของ H001 ทุกข้อ: หน้าต่าง 03:00–15:59 NY ของเวลาเปิดแท่ง t+1, spread filter 3 × median 96 แท่ง, ATR = 0, แท่งใน lookback ที่ validation ติดป้าย, มีสถานะเปิดอยู่
- ไม่ดูข้อมูลอนาคต (no look-ahead) และไม่มี I/O, นาฬิกา, สุ่ม หรือ `MetaTrader5` · ทุกการตัดสินใจมี `STRATEGY_VERSION` สำหรับ registry
- ไม่คำนวณขนาดไม้ (อยู่ใน `risk.size_position` แล้ว) และไม่จำลองการ fill (อยู่ใน `backtest` ของ CORE-007)

## Current behavior and evidence (revision)
ที่ main `6bd9ef8`: ไม่มีแพ็กเกจ `strategy` · `timebase.in_entry_window(dt, NY_ENTRY_WINDOW)` มีแล้ว (03:00–15:59 NY) · `risk.size_position` ทำสูตร sizing ของ H001 · CORE-005 (ยังเป็นร่าง) ให้ `Bar` และ `AggregatedBar` พร้อม flags ของ validation

## Scope
- In scope: แพ็กเกจ `sochron.strategy` (`params`, `indicators`, `h001`) · unit tests · acceptance, golden และการขยาย architecture test ให้ครอบ `sochron.strategy` โดยผู้เขียน tests ผ่าน patch D-006 · หลักฐาน · handoff
- Exclusions: sizing · การ fill, SL ภายในแท่ง M1, ต้นทุน (CORE-007) · registry และ baseline (CORE-008) · การเลือกพารามิเตอร์ · trailing stop (H001 ไม่มี) · การรันกับข้อมูลจริง
- Allowed files/modules: `src/sochron/strategy/**`, `tests/unit/strategy/**`, `docs/evidence/CORE-006.md`, `docs/handoff/CORE-006.md`, `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch: `tests/acceptance/CORE-006/**`, `tests/golden/CORE-006/**`, `tests/architecture/**`
- Must not touch: `src/sochron/{timebase,core,data,costs,risk}/**` (ถ้าต้องเปลี่ยนให้เสนอ contract แยก), `docs/hypotheses/**`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `research/**`, `pyproject.toml`, `uv.lock`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests · ตัวเลขเป็น `Decimal` และคำนวณใน context ของโมดูล (D1) · ชนิดผิด (float, bool, subclass) → `TypeError` · ค่านอกช่วง → `StrategyError` (subclass ของ `ValueError`)

```text
sochron.strategy
  STRATEGY_ID = "H001" · STRATEGY_VERSION = "H001-v1"
  Variant = Literal["A", "B", "C"]
  H001Params (frozen): variant, f: int, s: int, n: int, theta: Decimal, N: int, M: int, k: Decimal
    ช่วงตาม H001 ข้อ 4 (ขอบรวม): f 8–24 · s 32–96 และ s >= 3f · n 10–30 · theta 0.25–1.00 · N 48–192 · M 24–96 และ M <= N · k 1.5–3.0
  H001_DEFAULTS: Mapping[Variant, H001Params]  # f16 s64 n20 theta 0.50 N96 M48 k 2.0
  IndicatorRow (frozen): ema_f, ema_s, atr, ts (Decimal | None เมื่อ ATR = 0), hh_n, ll_n, hh_m, ll_m (Decimal | None ก่อนมีแท่งพอ),
                         close, spread (int | None), spread_median_96 (Decimal | None), warm: bool, lookback_flags: frozenset[str]
  indicators(bars: Sequence[AggregatedBar], params: H001Params) -> tuple[IndicatorRow, ...]   # แถวที่ t ใช้เฉพาะ bars[0..t]
  Position = Literal["flat", "long", "short"]
  Decision (frozen): action: Literal["enter_long", "enter_short", "exit", "hold", "none", "skip"],
                     stop_distance: Decimal | None, reasons: tuple[str, ...], version: str
  decide(rows: Sequence[IndicatorRow], t: int, position: Position, next_open_utc: datetime, params: H001Params) -> Decision
```

**v1.1 (2026-10-24, ตอบคำถามเปิดของผู้เขียน tests ใน `docs/handoff/CORE-006.md` โดยอำนาจที่เจ้าของมอบไว้ "เอา recommanded ทุกอัน"; veto ได้ก่อน merge):**
1. สูตร EMA (D1/D2): `α = 2/(p+1)` และ `1 − α` คำนวณครั้งเดียวใน context ของโมดูล · `EMA_p[t] = α × close[t] + (1 − α) × EMA_p[t−1]` ปัดหลังแต่ละ operation ตามลำดับที่เขียน (คูณ, คูณ, บวก)
2. `atr` เป็น None ก่อน t = n − 1 (ชนิด `Decimal | None`) · `ts` เป็น None เมื่อ `atr` เป็น None หรือ 0 · TR สำหรับ t ≥ 1 = max(high − low, |high − close[t−1]|, |low − close[t−1]|)
3. `spread_median_96[t]` = ค่าเฉลี่ยของตัวที่ 48 และ 49 เมื่อเรียงจากน้อย ของ spread[t−96 … t−1] · None ถ้า t < 96 หรือ spread ใดในช่วงนั้นเป็น None (เหตุผล `spread_unknown`)
4. "ช่วงที่ data validation ให้ STOP" ของ H001 บังคับที่ต้นทาง: SLICE-R1 ตัดวันที่ report เป็น STOP หรือ UNKNOWN ออกจากข้อมูลก่อน `aggregate`/`indicators` · strategy เห็นเฉพาะ flags รายแท่งใน lookback (D3)
5. ไม่มีสัญญาณเข้าระหว่างอุ่นเครื่อง → `none` (ไม่มี skip) · `warmup` เป็นเหตุผลเฉพาะเมื่อมีสัญญาณเข้า
6. ATR = 0: V-A/V-C ไม่มีสัญญาณเพราะกฎที่ใช้ TS เป็นเท็จ → `none` · V-B ที่มีสัญญาณ breakout → `skip` เหตุผล `atr_zero`
7. แท่ง M15 รับแบบ duck typing (`.bar` เป็น `core.Bar` พอดี, `.flags` เป็น `frozenset`) เพราะ strategy import `data.snapshot` ไม่ได้ · ชนิดผิด → `TypeError` · position ที่ไม่รู้จักหรือ t นอกช่วง → `StrategyError`
8. กฎปิดทำงานเมื่อ indicator ที่ใช้มีค่า แม้ยังไม่ warm (backtest ถือไม้ระหว่างอุ่นเครื่องไม่ได้อยู่แล้ว)
9. ผลจริงของ D3 (บันทึกไว้ ไม่แก้): flag ระดับ WARN (`missing_spread`, `unexpected_gap`) ทำให้ข้ามไม้ราว L แท่ง (≈1 วันทำการ) · R1 ต้องวัดผลกระทบจากข้อมูลจริงก่อนเชื่อจำนวนไม้

กฎ (H001 ข้อ 3 แปลตรงตัว; long แสดงไว้ short กลับด้านตาม D5):
- เข้า long: V-A `ts[t] > theta` และ `ts[t−1] <= theta` · V-B `close[t] > hh_n[t]` · V-C เงื่อนไข V-B และ `ts[t] > 0`
- เข้า short: V-A `ts[t] < −theta` และ `ts[t−1] >= −theta` · V-B `close[t] < ll_n[t]` · V-C เงื่อนไข V-B และ `ts[t] < 0`
- ปิด long: V-A `ts[t] <= 0` · V-B/V-C `close[t] < ll_m[t]` · หรือเกิดสัญญาณเข้า short (ปิดอย่างเดียว ไม่เปิดสวนในแท่งเดียวกัน) · ปิด short กลับด้าน
- position ไม่ใช่ `flat` และไม่มีเงื่อนไขปิด → `hold` (ไม่เปิดเพิ่ม) · การปิดทำได้ทุกเวลา ไม่ขึ้นกับหน้าต่างเวลาและ invalidation
- เข้าไม้ได้เมื่อผ่านทุกข้อ ไม่ผ่านข้อใด → `skip` พร้อมเหตุผลทุกข้อที่ไม่ผ่าน: `outside_window` (`in_entry_window(next_open_utc)` เป็นเท็จ), `spread_filter` (`spread[t] > 3 × spread_median_96[t]`, เท่ากันพอดีผ่าน), `spread_unknown`, `atr_zero`, `data_flag` (`lookback_flags` ไม่ว่าง), `warmup`
- เข้าไม้: `stop_distance = k × atr[t]`

## Invariants
- ไม่มี look-ahead: แถว t และการตัดสินใจที่ t ไม่เปลี่ยนเมื่อเพิ่มหรือแก้แท่งหลัง t
- pure และ deterministic: input เดิมได้ผลเดิม ไม่แก้ input
- กฎตรงกับ H001 ที่ลงทะเบียนแล้ว · พารามิเตอร์นอกช่วงที่ลงทะเบียนไม่ถูกยอมรับ (กันการลองนอกงบ variant)
- import ได้เฉพาะ `core`, `timebase` และ stdlib ที่ไม่ใช่ side effect ตาม module map

## Negative cases
TS ข้าม θ พอดี (`ts[t] == theta` ไม่เข้า, `ts[t−1] == theta` แล้ว `ts[t] > theta` เข้า) · `ts[t] == 0` ปิด V-A · close เท่ากับ HH/LL พอดี (ไม่ใช่ breakout) · spread เท่ากับ 3× median พอดี · spread ว่างในแท่ง t หรือใน 96 แท่ง · ATR = 0 · แท่งที่มี flag อยู่ขอบ lookback · ขอบหน้าต่าง NY 02:45, 03:00, 15:45, 16:00 ในวันเปลี่ยน DST ทั้งมีนาคมและพฤศจิกายน · มี position อยู่แล้วเจอสัญญาณเข้าเดิม · สัญญาณฝั่งตรงข้ามขณะถือ · พารามิเตอร์ที่ขอบช่วงและเกินขอบหนึ่งหน่วย · s = 3f พอดี · M = N พอดี · ชนิดผิดทุกช่อง

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given พารามิเตอร์ที่ขอบช่วง เกินขอบ ผิดข้อจำกัด (s < 3f, M > N) และผิดชนิด When สร้าง `H001Params` Then ค่าในช่วงสร้างได้ ค่านอกช่วงได้ `StrategyError` ชนิดผิดได้ `TypeError` · `H001_DEFAULTS` ตรงตาราง H001 ข้อ 4 ทุกค่า
- AC-02 Given แท่ง M15 สังเคราะห์ที่ผู้เขียน tests คำนวณคำตอบด้วยมือตามกฎ D1–D2 (golden) When `indicators` Then `ema_f`, `ema_s`, `atr`, `ts`, `hh_*`, `ll_*`, `spread_median_96`, `warm` ตรง golden ทุกแถว · HH/LL ไม่รวมแท่ง t
- AC-03 Given แถว indicator ตามตัวอย่างใน H001 ข้อ 3 (TS 1.20, TS ก่อนหน้า 0.45, θ 0.5, ATR 6.00, k 2.0, HH_96 4015.00, close 4016.30, เวลาเปิดแท่งถัดไป 09:45 NY) When `decide` ของ V-A, V-B, V-C Then ทั้งสามได้ `enter_long` และ `stop_distance = 12.00` · ตัวอย่างกลับด้านได้ `enter_short`
- AC-04 Given position `long`/`short` กับแถวที่เข้าเงื่อนไขปิดแต่ละแบบ รวมสัญญาณฝั่งตรงข้ามและแท่งนอกหน้าต่างเวลา When `decide` Then ได้ `exit` (ไม่ใช่ `enter_*`) · เมื่อไม่มีเงื่อนไขปิดได้ `hold` แม้มีสัญญาณเข้าเดิมซ้ำ
- AC-05 Given position `flat` กับสัญญาณเข้าที่ไม่ผ่าน invalidation ทีละข้อและหลายข้อพร้อมกัน รวมขอบหน้าต่าง NY ในวันเปลี่ยน DST และ spread เท่ากับ 3× median พอดี When `decide` Then ได้ `skip` และ `reasons` มีเหตุผลครบทุกข้อที่ไม่ผ่าน (เรียงตามลำดับที่กำหนด) · ขอบที่ผ่านได้ `enter_*`
- AC-06 Given ชุดแท่ง When เพิ่มหรือแก้แท่งหลัง t แล้วคำนวณใหม่ Then แถว t และการตัดสินใจที่ t เหมือนเดิมทุกค่า · และ architecture test ยืนยันว่า `sochron.strategy` ไม่มี I/O, นาฬิกา, สุ่ม, `MetaTrader5`, network และไม่ import `broker`, `data.acquire`, `execution`, `journal`, `backtest`, `research`, `risk`
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมด skipped 0 และ CI `python-tests` เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–05 | test author (acceptance + golden ที่คำนวณด้วยมือ) | `uv run --offline pytest tests/acceptance/CORE-006 tests/golden/CORE-006 -q -p no:cacheprovider` | L2 |
| 06 | test author + reviewer | test no-look-ahead แบบ property (เพิ่มแท่งสุ่มด้วย seed คงที่หลัง t) + architecture test + mutation | L2 |
| 07 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยงหลัก: การตีความ H001 ในจุดที่ข้อความไม่ระบุ (D1–D5) ถ้าตีความผิดผลวิจัยจะไม่ใช่ H001 จึงให้เจ้าของเลือกก่อนเขียน tests และบันทึกใน contract (H001 แก้ไม่ได้หลัง commit)

## Plan, dependencies and unknowns (P06)
1. Understanding: เขียนกฎ H001 เป็น pure function ที่ backtest และ Demo ใช้ร่วมกัน · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่าต้องคำนวณขนาดไม้หรือราคา SL — ไม่ คืนระยะ SL เท่านั้น (ข) คิดว่าควรเปิดสวนทันทีเมื่อเจอสัญญาณตรงข้าม — ห้าม (ค) คิดว่านับแท่งตามช่องเวลา — นับตามแท่งที่มีอยู่จริง (ช่วงปิดตลาดไม่มีแท่ง)
2. Files / reuse: `timebase.in_entry_window`, `NY_ENTRY_WINDOW`; `AggregatedBar` จาก CORE-005; รูปแบบตรวจชนิดแบบ exact จาก `costs`/`risk`
3. Steps: (1) CORE-005 merge (2) เจ้าของอนุมัติ (3) ผู้เขียน tests เขียน patch (4) Claude apply ตาม D-006 + fresh review → commit red (5) implement + unit tests (6) review → PR (label) → merge
4. Risks: ดูข้างบน · ประสิทธิภาพ: ราว 170,000 แท่ง M15 ต่อรันด้วย Decimal ต้องเสร็จในไม่กี่วินาที → unit test วัดเวลาบนข้อมูลสังเคราะห์
5. Decisions needed from the owner:
   - **D1 เลขคณิต:** (แนะนำ) `Decimal` context ของโมดูล precision 28, `ROUND_HALF_EVEN`, ปัดหลังทุก operation ตามลำดับที่เขียนในสูตร (แบบเดียวกับ CORE-002) → ผลเท่ากันทุกเครื่องและตรวจด้วยมือได้ · ทางอื่น: `float` (เร็วกว่าแต่เทียบเท่ากันได้ยากและขัดกับแนวของ costs/risk)
   - **D2 ค่าเริ่มของ EMA/ATR และช่วงอุ่นเครื่อง:** (แนะนำ) `EMA_p[0] = close[0]`, `α = 2/(p+1)` · `TR[0] = high[0] − low[0]` · `ATR[n−1]` = ค่าเฉลี่ยของ `TR[0..n−1]`, ต่อจากนั้น `ATR[t] = (ATR[t−1] × (n−1) + TR[t]) / n` · ตัดสินใจได้เมื่อ `t >= max(3s, N+1, M+1, 97, n+1)` ก่อนหน้านั้นเหตุผล `warmup`
   - **D3 lookback ที่ใช้ตรวจ "ข้อมูลขาดหาย":** (แนะนำ) แท่ง `t−L+1 … t` โดย `L = max(n, 96, N, M) + 1` (V-A ไม่นับ N, M) · invalid เมื่อแท่งใดมี flag ของ defect จาก validation · flag `incomplete` อย่างเดียวไม่ทำให้ invalid (แท่งมีข้อมูล แค่ไม่ครบ 15 นาทีในช่วงที่ไม่ผิดปกติ)
   - **D4 ATR = 0:** (แนะนำ) `ts` เป็น None · กฎที่ใช้ TS เป็นเท็จ · เข้าไม้ได้ `skip` เหตุผล `atr_zero` · การปิดด้วย TS ไม่เกิด (SL ยังป้องกันอยู่)
   - **D5 V-A ฝั่ง short:** (แนะนำ) "กลับด้าน" = `ts` ข้ามลงใต้ `−θ` และปิด short เมื่อ `ts >= 0`
   - **D6 ผู้เขียน tests และผู้ตรวจ:** เหมือน CORE-005 D4

## Authorization (filled by the owner)
- เจ้าของอนุมัติ 2026-10-23 15:0x · ผู้เขียน tests (Claude session ใหม่): patch ของ `tests/acceptance/CORE-006/**`, `tests/golden/CORE-006/**`, `tests/architecture/**` · Claude: implement ตาม scope, apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1–2 sessions · headless session ไม่เกิน 5 · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง

## DoR status / missing items / next action
ครบ: กฎและตัวอย่างใน H001, `timebase` · ครบ: การอนุมัติและ D1–D6 · ขาด: CORE-005 merge · next: เริ่มเขียน tests หลัง CORE-005 merge

## Done scope
merge แล้ว, suite เขียวใน CI
