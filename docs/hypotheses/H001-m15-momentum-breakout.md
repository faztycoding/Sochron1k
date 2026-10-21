# H001 — Volatility-normalized momentum + Donchian breakout บน XAUUSDm M15
สถานะ: ยังไม่พิสูจน์ (UNPROVEN)

Registered 2026-10-21 by เจ้าของ (ผ่านแชท Claude Code) · registration commit: (the commit that adds this file)
<!-- After commit this file is immutable (hook + CI). A changed idea becomes H<nnn+1>.
     Results go to the registry and to a separate result note, never into this file. -->

ที่มาของไอเดีย: เจ้าของเลือกแนว quantitative ที่ใช้ indicator พื้นฐาน โดยอ้างอิงแนวคิด EWMAC/time-series momentum (Carver, AQR) และ Donchian breakout ตามบันทึก `docs/research/H001-background.md` ซึ่งระบุชัดว่า **ยังไม่มีหลักฐานสาธารณะที่เชื่อถือได้ว่าชุดนี้ทำกำไรกับทอง M15 หลังหักต้นทุน** สมมติฐานนี้จึงมีไว้เพื่อทดสอบ ไม่ใช่เพื่อยืนยัน

ข้อจำกัดก่อนรัน: ห้ามรัน backtest ของสมมติฐานนี้จนกว่าด่าน ENV-1 (`docs/architecture.md` ข้อ 6.1) จะผ่าน และต้องมี contract SLICE-R1 ที่อนุมัติ

## 1. Mechanism (why should this edge exist? who loses to us?)
- **Momentum:** หลังมีข้อมูลใหม่ (macro, flow) ราคาทองมักปรับตัวต่อเนื่องเกินกว่าที่ปรับทันที เพราะผู้เล่นรายใหญ่ทยอยสร้างสถานะ และนักเทรดรายย่อยมักเทรดสวนแนวโน้ม (fade) เร็วเกินไป ผู้ที่เสียให้เราคือ (ก) รายย่อยที่ขายใส่แนวโน้มขาขึ้นหรือซื้อใส่ขาลงเพราะคิดว่า "แพงแล้ว/ถูกแล้ว" และ (ข) ผู้ที่ถูกบังคับปิดสถานะ (stop-out) เมื่อแนวโน้มเดินต่อ
- **Breakout:** ราคาทะลุกรอบสูงสุด/ต่ำสุดย้อนหลัง เป็นจุดที่ stop orders ของฝั่งตรงข้ามกระจุกตัว การทะลุจึงมักมีแรงส่งระยะสั้นจาก forced liquidation
- **ทำไมต้องปรับด้วยความผันผวน:** ระยะห่างของ EMA ที่เท่ากันมีความหมายต่างกันเมื่อ ATR ต่างกัน การหารด้วย ATR ทำให้ threshold และขนาดสถานะเทียบกันได้ข้ามช่วงเวลา
- **สิ่งที่จะทำให้สมมติฐานผิด:** ทอง M15 อาจ mean-revert แรงพอที่สัญญาณเหล่านี้จะแพ้ต้นทุน และกำไรที่เห็นในอดีตอาจมาจากขาขึ้นใหญ่ปี 2024–2026 (direction bias) ไม่ใช่จาก timing ข้อ 8 จึงบังคับให้ตรวจทั้งสองเรื่อง

## 2. Market and scope
- Symbol (broker quote name): `XAUUSDm` บน `Exness-MT5Trial14` (Demo) · spec ณ 2026-10-21: digits 3, point 0.001, contract 100 oz, volume 0.01–200 step 0.01, spread ลอยตัว (วัดได้ 240 points = 0.24 USD/oz), swap mode points: long −503.8 / short 0 (`docs/evidence/SPIKE-001.md`)
- Timeframe(s): **M15** สำหรับสัญญาณทั้งหมด สร้างจาก M1 ของโบรกเกอร์ (เพื่อให้ตรวจคุณภาพและประกอบแท่งเองได้) · M1 ใช้เฉพาะตรวจการชน SL ภายในแท่ง
- Sessions / hours (time-module convention): เวลาดิบจาก MT5 เป็น Unix epoch ที่ offset ต่อ UTC = 0 สำหรับ server นี้ (SPIKE-001 AC-04 วัดได้ 0 แต่กลไกยัง UNKNOWN) แปลงผ่าน `timebase` เท่านั้น · หน้าต่างเข้าไม้กำหนดด้วย **เวลา New York (`America/New_York`)**: เปิดไม้ใหม่ได้เมื่อเวลาเปิดแท่งอยู่ใน **03:00–15:59 NY** (ครอบคลุม London + New York, จบก่อนช่วงพักตลาดราว 17:00 NY ที่ SPIKE-001 เห็น) · ปิดไม้ได้ทุกเวลา · ถือข้ามคืนและข้ามสุดสัปดาห์ได้ (คิด swap)
- Research period: ข้อมูลตั้งแต่ **2018-01-01** (SPIKE-001: M1 ปี 2014–2016 มีราว 1 แท่ง/วัน และปี 2017 ผิดปกติ จึงตัดออก) ถึงวัน cutoff ของ holdout · ช่วงที่ใช้วิจัยจริงให้ data validation ของ R1 เป็นผู้ยืนยัน (ปีที่เริ่มใช้วิจัยได้ยัง UNKNOWN ตาม review SPIKE-001)

## 3. Rules (two people must decide the same bar identically)
นิยามบนแท่ง M15 ที่ปิดแล้ว (index t) ทุกการตัดสินใจใช้เฉพาะข้อมูลถึงปิดแท่ง t และส่งคำสั่งที่ **ราคาเปิดของแท่ง t+1** ซื้อที่ ask ขายที่ bid
- `EMA_f[t]`, `EMA_s[t]`: EMA ของราคาปิด (bid) ช่วง f และ s
- `ATR_n[t]`: Wilder ATR ช่วง n จาก true range ของแท่ง M15
- `TS[t] = (EMA_f[t] − EMA_s[t]) / ATR_n[t]` (Trend Score, ไม่มีหน่วย)
- `HH_N[t]` = high สูงสุดของแท่ง t−N … t−1 (ไม่รวมแท่ง t) · `LL_N[t]` = low ต่ำสุดแบบเดียวกัน · ช่องออก `HH_M`, `LL_M` ด้วย M

สมมติฐานนี้มี **3 โครงสร้าง (variant family)** ที่ต้องทดสอบแยกกันและเทียบกัน:

| Variant | Entry long (short กลับด้าน) | Exit (นอกจาก SL) |
|---|---|---|
| **V-A momentum** | `TS[t] > θ` และ `TS[t−1] ≤ θ` | ปิดเมื่อ `TS[t] ≤ 0` |
| **V-B breakout** | `Close[t] > HH_N[t]` | ปิดเมื่อ `Close[t] < LL_M[t]` |
| **V-C breakout + momentum filter** | เงื่อนไข V-B **และ** `TS[t] > 0` | เหมือน V-B |

- Entry: ตามตาราง และต้องผ่านทุกข้อใน Invalidation · ถ้ามีสถานะอยู่แล้วห้ามเปิดเพิ่ม (1 สถานะต่อครั้ง)
- Stop loss: วางพร้อมคำสั่งทุกครั้ง ที่ `entry − k × ATR_n[t]` (long) / `entry + k × ATR_n[t]` (short) · ห้ามขยาย SL · ไม่มี trailing ใน H001 (V-B/V-C มี Donchian exit ทำหน้าที่คล้าย trailing อยู่แล้ว)
- Take profit / exit: ไม่มี TP · ออกตามกฎ exit ของ variant หรือ SL แล้วแต่อะไรถึงก่อน · ถ้าใน M1 แท่งเดียวกันราคาแตะทั้ง SL และระดับ exit ให้ติดป้าย ambiguous และนับเป็น **SL** (เลือกทางที่แย่กว่า)
- Time exit: ไม่มี · ถ้าเกิดสัญญาณฝั่งตรงข้ามขณะถือสถานะ ให้ปิดสถานะที่เปิดแท่ง t+1 และ**ไม่**เปิดสวนในแท่งเดียวกัน (ประเมินใหม่แท่งถัดไป)
- Position size: `R = 0.25% × equity` ณ เวลาเปิดแท่ง t+1 (ตาม risk policy [A] ใน SPEC ข้อ 6, Q-04) · `lots = floor_0.01( R / (k × ATR_n[t] × 100) )` · ถ้า `lots < 0.01` ให้ข้ามไม้และบันทึกเหตุผล `below_min_volume` · ไม่เกิน `volume_max` · รายงานผลเป็น R-multiple (กำไรขาดทุน ÷ R) ควบคู่กับเงิน
- Invalidation (ไม่เปิดไม้): เวลาเปิดแท่ง t+1 อยู่นอก 03:00–15:59 NY · `spread[t] > 3 × median(spread[t−96 … t−1])` · ATR_n[t] = 0 หรือข้อมูลแท่งใดใน lookback ขาดหาย (validation ติดป้าย) · อยู่ในช่วงที่ data validation ให้ STOP · มีสถานะเปิดอยู่
- Worked example on a concrete bar sequence (ตัวเลขสมมติเพื่อให้สองคนคำนวณตรงกัน ไม่ใช่ข้อมูลจริง): แท่ง M15 ปิด 2026-03-10 13:45 UTC = 09:45 NY (อยู่ในหน้าต่าง) `EMA_16 = 4012.40`, `EMA_64 = 4005.20`, `ATR_20 = 6.00` → `TS = 7.20/6.00 = 1.20` · แท่งก่อนหน้า `TS = 0.45` · θ = 0.5 → V-A ให้สัญญาณ long (ข้าม θ จากล่างขึ้นบน) · เปิดแท่งถัดไป bid 4012.66 / ask 4012.90 → ซื้อที่ 4012.90 · SL = 4012.90 − 2.0 × 6.00 = 4000.90 · equity 10,000 USD → R = 25 USD · ระยะ SL 12.00 USD/oz × 100 = 1,200 USD/lot → lots = floor_0.01(25/1200 = 0.0208) = **0.02** (เสี่ยงจริง 24 USD) · ต่อมาแท่งปิดที่ `TS = −0.10` ≤ 0 → ขายที่ bid เปิดแท่งถัดไป 4029.86 → PnL ก่อน swap = (4029.86 − 4012.90) × 100 × 0.02 = **+33.92 USD = +1.41 R** ถ้าถือข้ามคืน 1 คืน หัก swap 503.8 × 0.001 × 100 × 0.02 = 1.01 USD · สำหรับ V-B ในแท่งเดียวกัน ถ้า `HH_96 = 4015.00` และ `Close = 4016.30 > 4015.00` ก็ให้สัญญาณ long เช่นกัน และ V-C ให้สัญญาณเพราะ TS = 1.20 > 0

## 4. Parameters and variant budget
| Parameter | Allowed range | Default |
|-----------|---------------|---------|
| f (EMA เร็ว, แท่ง M15) | 8–24 | 16 |
| s (EMA ช้า) | 32–96 และ s ≥ 3f | 64 |
| n (ATR) | 10–30 | 20 |
| θ (threshold ของ TS, V-A) | 0.25–1.00 | 0.50 |
| N (Donchian entry, V-B/V-C) | 48–192 | 96 (= 1 วัน) |
| M (Donchian exit) | 24–96 และ M ≤ N | 48 |
| k (SL เป็นเท่าของ ATR) | 1.5–3.0 | 2.0 |
| spread filter | คงที่ 3 × median 96 แท่ง | ไม่ปรับ |
- Maximum number of variants to try: **18 ชุดพารามิเตอร์สำหรับการเลือก** (3 โครงสร้าง × ไม่เกิน 6 ชุดต่อโครงสร้าง รวมค่า default) · การตรวจ robustness ±10% ของชุดที่ดีที่สุดต่อโครงสร้าง (ทีละพารามิเตอร์ ไม่เกิน 14 รันต่อโครงสร้าง) และการทดสอบต้นทุน 2× **ไม่ใช้เลือก** แต่ต้องลงทะเบียนทุกรัน รวมทุกอย่างไม่เกิน 63 รัน ไม่นับ baseline

## 5. Data contract
- Source and snapshot ID / build method: M1 bid bars ของ `XAUUSDm` จาก MT5 (`copy_rates_range`) พร้อมฟิลด์ `spread` ต่อแท่ง → เก็บเป็น Parquet snapshot ที่มี manifest (ช่วงเวลา, จำนวนแท่ง, SHA256, terminal build, symbol spec, เวอร์ชันกฎเวลาของ `timebase`) · สร้าง M15 จาก M1 ด้วยโค้ดใน repo (ไม่ใช้ M15 จาก terminal โดยตรง) · snapshot ID กำหนดโดย contract SLICE-R1 · ดึงข้อมูลจาก acquisition host เท่านั้น (ข้อ 6.1)
- Train period: 2018-01-01 → 2022-12-31
- Validation period: 2023-01-01 → 2024-12-31 (ใช้เลือกชุดพารามิเตอร์ภายในงบ 18 ชุด)
- Holdout cutoff date and custodian (never inside the research checkout): **cutoff 2025-01-01 00:00 UTC** ข้อมูลตั้งแต่วันนี้เป็นต้นไปเป็น holdout · ผู้ถือคือเจ้าของ เก็บบน acquisition host (Windows VPS ตามข้อ 6.1) · เปิดใช้ครั้งเดียวในวันประเมิน โดยรัน strategy version ที่ freeze แล้วบน acquisition host · (คำตอบของ SPEC Q-08 สำหรับ H001)

## 6. Costs
- Spread (from real bid/ask), commission, slippage, swap: spread ใช้ค่าจริงของแท่งที่เข้า/ออกจากฟิลด์ `spread` ของ MT5 (points × 0.001) ถ้าฟิลด์ว่างใช้ 240 points · commission 0 (บัญชี Standard ของ Exness ณ 2026-10-21 ต้องยืนยันใน R1) · slippage [A] **50 points (0.05 USD/oz) ต่อข้าง** สำหรับคำสั่ง market และการชน SL · swap ตาม spec: long −503.8 points/คืน (= 50.38 USD/lot/คืน), short 0 · วันคิด swap 3 เท่า UNKNOWN (สมมติพุธ [A] ต้องยืนยันจาก spec จริงใน R1)
- Stress test: all costs × 2 (spread, slippage, swap ทั้งหมดคูณ 2)

## 7. Baselines
- Random entry: **1,000 รัน** ต่อ variant ที่ดีที่สุด แต่ละรันสุ่มจุดเข้าเฉพาะแท่งที่ผ่าน session/spread filter ให้จำนวนไม้เท่ากับ variant, ทิศทางสุ่ม 50/50, ใช้กฎ SL และ sizing เดียวกัน, ระยะเวลาถือสุ่มจากการแจกแจงระยะเวลาถือของ variant · ค่าเฉลี่ยของ baseline ควรอยู่ใกล้ −ต้นทุน
- Other simple baseline: **long-only** ของโครงสร้างเดียวกัน (เปิดเฉพาะ long) เพื่อวัดว่ากำไรมาจากขาขึ้นของทองหรือจาก timing

## 8. Fail conditions (numeric, evaluated on the holdout)
ประเมินกับ variant ที่เลือกจาก validation เพียงตัวเดียวต่อโครงสร้าง ด้วยพารามิเตอร์ที่ freeze ก่อนเปิด holdout
- Minimum independent trades: **≥ 100 ไม้ใน holdout** (สถานะไม่ซ้อนกันอยู่แล้ว) ถ้าน้อยกว่า = insufficient data
- Minimum net expectancy after costs: **≥ +0.10 R ต่อไม้** ที่ต้นทุน 1× และ **> 0** ที่ต้นทุน 2×
- Maximum drawdown: **≤ 24 R** (≈ 6% ของทุนที่ risk 0.25%/ไม้) วัดจาก equity curve หลังต้นทุน
- Robustness: parameter ± 10% must not collapse the result: ทีละพารามิเตอร์ ±10% (ปัดเป็นจำนวนเต็มแท่ง) expectancy หลังต้นทุน 1× ต้อง > 0 ใน **≥ 80% ของเพื่อนบ้าน** (อย่างน้อย 12 จาก 14)
- Versus random-entry distribution: expectancy ของ holdout ต้องสูงกว่า **percentile ที่ 95** ของ 1,000 รันสุ่ม
- ไม่ขึ้นกับไม้ใหญ่หรือ regime เดียว: ตัดไม้ที่กำไรสูงสุด 5 ไม้ออกแล้ว expectancy ยัง > 0 · expectancy หลังต้นทุน ≥ 0 ในทั้งปี 2025 และ 2026 (ส่วนที่มี) · expectancy ของฝั่ง long และฝั่ง short แยกกันต้อง ≥ 0 ทั้งคู่ (กัน direction bias) และ variant ต้องชนะ long-only baseline ด้านอย่างน้อยหนึ่งอย่างระหว่าง expectancy หรือ max drawdown
- ทุกข้อต้องผ่านพร้อมกันจึงจะ Go · ผ่านบางข้อ = Stop ไม่ใช่ "เกือบผ่าน"

## 9. Decision rule
Go / Stop / Insufficient data, as defined in docs/HANDBOOK-CORE.md §15: **Go** เมื่อ holdout ยังแสดง edge หลังต้นทุนตามเงื่อนไขข้อ 8 ครบ ผลไม่ขึ้นกับไม้ใหญ่ไม่กี่ไม้หรือ regime เดียว พารามิเตอร์เปลี่ยนเล็กน้อยแล้วไม่พัง และ leakage audit ไม่พบปัญหา · **Stop** เมื่อ holdout พลาดเงื่อนไขที่ลงทะเบียนไว้ ห้ามแก้เงื่อนไขหลังเห็นผล (ไอเดียใหม่ = H002 ขึ้นไป) · **Insufficient data** เมื่อไม้อิสระน้อยกว่า 100 หรือ holdout ครอบคลุม regime เดียว · ผู้ตัดสินคือเจ้าของ จากรายงาน 3 ชิ้น (data validation, golden tests, registry)
