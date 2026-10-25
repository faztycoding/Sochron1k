# SPEC — Sochron1k

Version 0.1 (ร่าง) · Owner: เจ้าของ repository · Stage: prototype (research) · Reviewed: — (เจ้าของยังไม่รับรอง)

> ร่างโดย Claude Code เมื่อ 18 ต.ค. 2026 จากข้อมูลรอบก่อน (git `a3b3fbf`: `docs/product.md` ซึ่งสรุปจาก Blueprint v1.1)
> ทุกข้อที่มีป้าย **[A]** เป็นสมมติฐานที่ยกมาจากรอบก่อนและเจ้าของยังไม่ยืนยัน ช่อง **TBD** คือคำถามที่เจ้าของต้องตอบ
> ขั้นต่อไป: ใช้ `/spec-interview` เพื่อเติมให้ครบ แล้วเจ้าของรับรองก่อนเริ่ม contract แรก

## 1. Problem
- Users: เจ้าของคนเดียว ใช้บัญชี MT5 **Demo** ที่แยกไว้ให้ระบบนี้โดยเฉพาะ [A]
- Current problem: ยังไม่มีหลักฐานที่ตรวจซ้ำได้ว่ากลยุทธ์ XAU/USD ที่นิยามชัดมีความได้เปรียบหลังหักต้นทุน และยังไม่มีระบบที่ส่งคำสั่ง Demo ได้อย่างปลอดภัยและตรวจย้อนได้ [A]
- Desired outcome: (1) วงวิจัยที่ให้คำตัดสิน go / stop / insufficient จากหลักฐาน (รายงานข้อมูล, golden tests, registry, holdout) และ (2) runner บน Demo ที่คุมความเสี่ยงด้วยโค้ดและ reconcile กับ MT5 ได้ [A]
- Measured by:
  - วิจัย: H001 ได้คำตัดสินตามเงื่อนไขที่ลงทะเบียนไว้ก่อนรัน พร้อม 3 รายงานที่เจ้าของอ่านเอง — TBD: วันที่คาดว่าจะได้คำตัดสิน
  - วิศวกรรม: Demo round trip ที่ MT5 ยืนยัน (เปิด → SL ยืนยัน → ปิด → reconcile) ผ่าน negative cases ที่กำหนด [A]
- Not doing (non-goals) [A]:
  - เงินจริง, ฝากถอน, copy trading, ขายสัญญาณ, หลายบัญชี
  - martingale, เฉลี่ยขาดทุน, ขยาย SL, เพิ่มความเสี่ยงเพื่อไล่เป้ารายได้
  - ให้ AI เลื่อนขั้นกลยุทธ์หรือแก้ risk policy เอง
  - Order Flow ที่ไม่มีข้อมูลที่มี license
  - การการันตีกำไรหรือ win rate

## 2. Risk tier
- Q1 auth/permissions/isolation: no — ระบบผู้ใช้คนเดียว ไม่มีหน้าเว็บที่เปิดออกนอกเครื่องใน phase 1–3 (ถ้าเพิ่ม dashboard ภายนอก งานนั้นจะเป็น High)
- Q2 real money: no — Demo เท่านั้น (เมื่อไรแตะเงินจริง = High และต้องมี SPEC รุ่นใหม่)
- Q3 new storage/transfer of personal or confidential data: no สำหรับวิจัย; ข้อมูลบัญชี Demo เก็บในเครื่องเท่านั้น และไม่ลง log/รายงานแบบเต็ม — TBD: ยืนยันว่าไม่ส่งข้อมูลบัญชีไปผู้ให้บริการ AI ใดๆ
- Q4 schema change or deletion on real data: no — ยังไม่มีข้อมูลจริงที่ต้องรักษา
- Q5 hard-to-reverse external effect: **yes** สำหรับงานส่งคำสั่ง Demo (คำสั่งที่ fill แล้วย้อนไม่ได้) → Standard + external-action controls (บท 34)
- Q6 changes to controls: **yes** สำหรับ BOOT-001 (ตั้ง hooks, permissions, CI) → High และแยกเป็น task ของตัวเอง
- Tier: **Standard** สำหรับวิจัยและ Demo · **High** สำหรับงานที่แตะ controls, credentials หรือเงินจริง
- Profiles: data · AI-assisted research · financial automation (Quant, บท 34) · own product

## 3. Roles and permissions
| Role | Can | Cannot |
|------|-----|--------|
| Owner (คุณ) | รับรอง SPEC/AC/ADR, อนุมัติ action ภายนอก, ถือ credential, push/merge, ตัดสิน go/stop | – |
| Claude Code | วางแผน, เขียน contract, implement บน task branch, commit ในเครื่อง | แก้ locked paths/tests, push, merge, ส่งคำสั่งนอก contract, อ่าน .env |
| Codex | เขียน acceptance/golden tests, review, audit | เขียน implementation ของงานที่ตัวเองตรวจ, แก้โค้ดระหว่าง review |
| CI | รัน checks ที่กำหนด | – |
| ระบบ Sochron1k | อ่านข้อมูลตลาด, ส่งคำสั่งบน Demo ตามที่ contract อนุญาต | แตะบัญชีที่ไม่ใช่ Demo, เปลี่ยน risk policy เอง |

## 4. Core journeys
- J1 สร้าง snapshot ข้อมูล XAU/USD จาก MT5 พร้อมรายงานตรวจข้อมูล (PASS/WARN/UNKNOWN/STOP) → SPIKE-001, SLICE-R1
- J2 ลงทะเบียนสมมติฐาน → backtest พร้อมต้นทุน → registry → รายงานเทียบ random-entry → เจ้าของตัดสิน → SLICE-R1
- J3 ส่งคำสั่ง Demo ผ่าน risk gate → MT5 ยืนยัน SL → ปิด → reconcile → SLICE-E1
- J4 หยุด, กู้คืน, reconcile แล้วทำต่อหลัง restart → SLICE-E1 / OPS-1
- J5 ทบทวน journal ("paper journey", เจ้าของตัดสิน 2026-10-21): ทุกไม้บันทึกเหตุผลเข้าก่อนส่งคำสั่ง และหลังปิดถูกจำแนกว่าทำไมได้หรือเสีย (trade attribution: market move, spread, slippage, swap, reason code) → เจ้าของกับ agent ทบทวนสรุปเป็นรอบ → ข้อเสนอแก้กฎกลายเป็นสมมติฐานรุ่นถัดไป (H00n+1) ที่ต้องลงทะเบียนและทดสอบใหม่ · กลยุทธ์ที่รันอยู่ไม่เปลี่ยนตัวเอง → SLICE-R1 (รายงาน) / SLICE-E1 (journal)

## 5. Data
| Data | Class | Source of truth | Retention | Who can access |
|------|-------|-----------------|-----------|----------------|
| ราคา/ticks/bars จากโบรกเกอร์ | contract-limited (ตามเงื่อนไขโบรกเกอร์) | MT5 terminal → snapshot ที่บันทึก manifest | TBD | เครื่องเจ้าของ |
| Holdout | internal, ปิดผนึก | Windows VPS ที่เป็น acquisition host นอกเครื่องวิจัย (เจ้าของ 2026-10-21, `docs/architecture.md` ข้อ 6.1) · ระหว่างยังไม่มี VPS ห้ามตัด holdout · วัน cutoff TBD (Q-08) | ปิดผนึกตลอดอายุโปรเจกต์ หรืออย่างน้อยจนทุกสมมติฐานที่ใช้ cutoff เดียวกันมีคำตัดสิน · ลบได้เฉพาะเมื่อเจ้าของตัดสินและบันทึกใน DECISIONS (D-019, Q-12) | เจ้าของ (เปิดเฉพาะวันประเมิน) |
| Registry การทดลอง | internal | `research/registry/*.jsonl` (append-only) รวมไฟล์ของ holdout ที่คัดลอกเข้ามาหลังประเมิน (D-017) | ตลอดอายุโปรเจกต์ (D-019, Q-12) | repo |
| คำสั่ง/deals/positions | confidential operational | MT5 (ความจริง) + journal ในเครื่อง | TBD | เครื่องเจ้าของ |
| Login/รหัสผ่าน MT5 | restricted | ใน terminal หรือ .env บนเครื่อง runner เท่านั้น | – | เจ้าของ |
- Personal data: ไม่มีข้อมูลส่วนบุคคลของผู้อื่น ข้อมูลบัญชีของเจ้าของไม่ลง log/prompt/report แบบเต็ม

## 6. Non-functional requirements
ทุกข้อต้องมีหน่วยและเงื่อนไข ค่าด้านล่างยังเป็น TBD (บางข้อมีค่าจากรอบก่อนเป็นจุดตั้งต้น)
- Performance: เวลาจากแท่งปิดถึงส่งคำสั่ง p95 ≤ TBD วินาที (บน host ที่ตกลง)
- Reliability: runner ทำงานในชั่วโมงเทรดที่กำหนด ≥ TBD% ต่อสัปดาห์; ราคาถือว่า stale เมื่อไม่มี tick ใหม่เกิน 5 วินาทีในช่วงตลาดเปิด [A]
- Correctness: ไม่มีคำสั่งซ้ำจาก idempotency key เดียวกัน; ทุก UNKNOWN ถูก reconcile ก่อนส่งใหม่
- Security: ไม่มี secret ใน repo/log (red-flag + deny rules); Demo guard มี negative test
- Risk policy [A]: เสี่ยงต่อเทรด ≤ 0.25% ของ Equity (รวม cost budget), หยุดรายวันเมื่อขาดทุน 0.75% จาก baseline วันไทย, หยุดการทดลองเมื่อขาดทุน 2% จากทุนตั้งต้น, มี position หรือ pending ได้ครั้งละ 1 — TBD: ยืนยันค่าเหล่านี้และใครปลดล็อก halt ได้
- Cost: งบรายเดือน (VPS/ข้อมูล/API) TBD บาท

## 7. Architecture summary
- ดู `docs/architecture.md` (D-001: Python modular monolith + `MetaTrader5` บน Windows, วิจัยก่อน — **accepted** 2026-10-21 พร้อมด่าน ENV-1 ก่อนวิจัย)
- External services: MT5 terminal + เซิร์ฟเวอร์ Demo ของโบรกเกอร์ Exness (`Exness-MT5Trial14`; บัญชี Demo read-only ที่ใช้ใน SPIKE-001 หมดอายุการอนุญาต 2026-10-28; บัญชี/VPS สำหรับ R1/E1 ต้องมี authorization ใหม่ใน contract นั้น), GitHub (repo + CI)
- Key decisions: ดู `DECISIONS.md`

## 8. Environments and release
- Research host (Windows ของเจ้าของ): พัฒนา และวิจัยด้วย snapshot ก่อน cutoff เท่านั้น · หลังด่าน ENV-1 จะไม่มี terminal, terminal cache หรือการดึงข้อมูลจากโบรกเกอร์บนเครื่องนี้ (`docs/architecture.md` ข้อ 6.1)
- ระยะนี้ (เจ้าของ 2026-10-21): terminal ยังอยู่บนเครื่องนี้ ใช้ได้เฉพาะงานอ่านอย่างเดียวที่ contract อนุญาต (เช่น SPIKE-001) **ห้ามตัด holdout, ห้าม ingest ข้อมูลวิจัย และห้ามทดลองกลยุทธ์** จนกว่า ENV-1 จะผ่าน
- Acquisition/execution host และ Demo runner: Windows VPS (เจ้าของวางแผน 2026-10-21) ถือ terminal, raw captures, journal และ holdout · ส่งคำสั่งได้เฉพาะเมื่อ contract อนุญาตและอยู่ใน execution scope (`docs/architecture.md` ข้อ 7.1) · ค่าใช้จ่ายอยู่ใน Q-10
- Production (เงินจริง): ไม่มีในขอบเขตนี้
- Rollback: revert branch; ปิด runner; position ที่เปิดอยู่ปิดด้วยมือใน terminal (TBD: runbook)

## 9. Assumptions and open questions
คอลัมน์ Status: `TBD` คือคำถามที่ยังเปิดอยู่ · `[A]` คือสมมติฐานที่รอเจ้าของยืนยัน · แถวที่เจ้าของตัดสินแล้วจะอ้างถึง ADR
| ID | Assumption or question | How to verify | Review date | Status |
|----|------------------------|---------------|-------------|--------|
| Q-01 | Sochron1k ยังเป็นระบบวิจัย + เทรดอัตโนมัติ XAU/USD บน MT5 Demo เหมือนรอบก่อน | เจ้าของยืนยัน | ก่อน SPIKE-001 | TBD (open) |
| Q-02 | โบรกเกอร์, Demo server, สกุลเงินบัญชี, leverage, netting/hedging | เจ้าของ + SPIKE-001 | ก่อน SPIKE-001 | ตอบแล้ว: Exness, `Exness-MT5Trial14`, retail hedging (เจ้าของ 2026-10-21) · สกุลเงินบัญชี USD, leverage 1:200, trade_mode Demo (SPIKE-001 AC-01, `docs/evidence/SPIKE-001.md`) · บัญชี/server บน VPS ต้องวัดซ้ำใน ENV-1 |
| Q-03 | ชื่อสัญลักษณ์และ contract spec ของ XAU/USD ที่โบรกเกอร์ใช้ | SPIKE-001 | — | ตอบแล้ว: `XAUUSDm` · digits 3, point 0.001, contract 100 oz, volume 0.01–200 step 0.01, tick value 0.1 USD, spread ลอยตัว (240 points ตอนวัด), swap long −503.8 / short 0 points, คิด swap 3 เท่าวันพุธ (ภาพ Specification) (SPIKE-001 AC-03, 2026-10-21) · เวลาทำการเทียบ timezone ยัง UNKNOWN |
| Q-04 | ค่า risk policy 0.25% / 0.75% / 2% และผู้มีสิทธิ์ปลด halt | เจ้าของ | ก่อน SLICE-E1 | TBD (open) |
| Q-05 | ชั่วโมงเทรดและนโยบายถือข้ามคืน | เจ้าของ | ก่อน H001 | ตอบแล้วสำหรับ H001 (เจ้าของอนุมัติตัวเลขทั้งหมด 2026-10-21 ราว 07:40): เปิดไม้ใหม่เมื่อเวลาเปิดแท่งอยู่ใน 03:00–15:59 New York, ปิดได้ทุกเวลา, ถือข้ามคืน/สุดสัปดาห์ได้โดยคิด swap (`docs/hypotheses/H001-m15-momentum-breakout.md` ข้อ 2) · นโยบายของ Demo runner ยืนยันอีกครั้งใน contract SLICE-E1 |
| Q-06 | สมมติฐานแรก (PA01 จากรอบก่อน หรือไอเดียใหม่) | `/register-hypothesis` | ก่อน SLICE-R1 | ตอบแล้ว (เจ้าของ 2026-10-21): ไอเดียใหม่แนว quantitative = H001 volatility-normalized momentum + Donchian breakout บน M15 (`docs/hypotheses/H001-m15-momentum-breakout.md`) · ตัวกรองข่าวแรงเป็น H002 แยก · z-score mean reversion และ macro score เป็น H ถัดไป |
| Q-07 | ความลึกข้อมูลจากโบรกเกอร์พอไหม ถ้าไม่พอจะใช้แหล่งอื่นหรือไม่ (license) | SPIKE-001 | — | TBD (open) |
| Q-08 | วัน cutoff ของ holdout และที่เก็บนอกเครื่องวิจัย | เจ้าของ | ก่อน SLICE-R1 | ตอบแล้ว (เจ้าของ 2026-10-21): ที่เก็บ = Windows VPS ที่เป็น acquisition host (ผู้ถือ = เจ้าของ) · cutoff สำหรับ H001 = 2025-01-01 00:00 UTC (`docs/hypotheses/H001-m15-momentum-breakout.md` ข้อ 5) · ห้ามตัด holdout จนกว่า ENV-1 ผ่าน (ลำดับการตัดบน VPS ต้องระบุใน contract ENV-1) |
| Q-09 | Demo runner จะรันที่ไหน (เครื่องนี้ หรือ Windows VPS) | เจ้าของ | ก่อน OPS-1 | ตอบแล้ว (เจ้าของ 2026-10-21): Windows VPS ในอนาคต ส่วนระยะนี้ใช้เครื่องนี้ไปก่อน (`docs/architecture.md` ข้อ 6.1) |
| Q-10 | งบรายเดือน และ kill criteria ของทั้งโปรเจกต์ | เจ้าของ | ก่อน SLICE-R1 | ตอบแล้ว 2026-10-25: งบโครงสร้างพื้นฐาน (VPS) ไม่เกิน 40 USD/เดือน ไม่รวมค่า AI subscription · kill criteria: (1) ถ้า H001 ไม่ผ่าน holdout ทั้ง 3 โครงสร้างตาม D-015 หยุด H001 และทบทวนทั้งโปรเจกต์ก่อนลงทะเบียนสมมติฐานใหม่ (2) ทบทวนงบและความคืบหน้าทุก 3 เดือน (3) ครบ 6 เดือนนับจากวันเริ่มเช่า VPS แล้วยังไม่มีสมมติฐานใดผ่าน holdout: หยุดจ่าย VPS |
| Q-11 | ใช้ Codex เป็น test author + reviewer ตาม binding ค่าเริ่มต้น (D-002) | เจ้าของ | ก่อน contract แรก | TBD (open) |
| Q-12 | ระยะเวลาเก็บ holdout และ registry ในข้อ 5 (ตอนนี้เป็น [A]) | เจ้าของ | ก่อน SLICE-R1 | ตอบแล้ว (เจ้าของ 2026-10-24 ~20:0x "เอาที่ดีที่สุด" = ทางที่แนะนำ): D-019 · registry ตลอดอายุโปรเจกต์ · holdout ปิดผนึกบน VPS ลบได้เฉพาะเมื่อเจ้าของสั่ง · snapshot ก่อน holdout เก็บพร้อม manifest ตลอดอายุโปรเจกต์ |
| A-01 | เอกสารฝั่งเจ้าของเป็นภาษาไทย ส่วนโค้ด/commit/คำสั่ง agent เป็นอังกฤษ | เจ้าของยืนยัน | ก่อน contract แรก | [A] assumed |
| A-02 | Blueprint v1.1 และโค้ดรอบก่อนเป็นเพียงข้อมูลอ้างอิงใน git history ไม่ใช่ข้อกำหนด | เจ้าของยืนยัน (D-003) | ก่อน contract แรก | ยืนยันแล้วโดย D-003 (accepted) |

## 10. Change log
| Date | Change | Requested by | Impact on time/cost/acceptance |
|------|--------|--------------|--------------------------------|
| 2026-10-18 | ร่าง 0.1 จากข้อมูลรอบก่อน + Handbook v5 | เจ้าของ (ขอให้ตั้งโปรเจกต์ใหม่) | ยังไม่มี: รอเจ้าของรับรอง |
| 2026-10-20 | ติดป้าย [A]/TBD ตาม review AC-08 (F1, F3): retention ในข้อ 5, คอลัมน์ Status ในข้อ 9 และเพิ่ม Q-12 · ไม่เปลี่ยนค่าใดๆ | เจ้าของ (ให้ปิด AC ของ BOOT-001) | ไม่มีผลต่อเวลา/ค่าใช้จ่าย · แก้ AC-08 |
| 2026-10-21 | Q-02 และ Q-03 ตอบบางส่วนจากข้อมูลบัญชี Demo ที่เจ้าของแจ้ง (Exness, server, hedging, `XAUUSDm`) | เจ้าของ (เตรียม SPIKE-001) | ไม่มีผลต่อเวลา/ค่าใช้จ่าย |
| 2026-10-21 | ข้อ 5 และ 8 ปรับตามการแยกเครื่องของ D-001 (Windows VPS เป็นเป้าหมาย, ระยะนี้ใช้เครื่องเดียวแบบจำกัด, ด่าน ENV-1 ก่อนวิจัย) ตาม review D-001 r2 F3 | เจ้าของ (เลือก VPS) | มีค่า VPS (Q-10) · งานวิจัยเริ่มได้หลัง ENV-1 |
| 2026-10-21 | Q-06 ตอบแล้ว (H001 momentum + breakout M15, ข่าวเป็น H002) · เพิ่ม journey J5 trade attribution แบบ journal-driven · research memo ใน `docs/research/H001-background.md` | เจ้าของ (ให้ทิศทางกลยุทธ์) | ไม่มีผลต่อเวลา/ค่าใช้จ่าย · H002 ต้องมีแหล่งข้อมูลปฏิทินที่ผ่าน admission |
| 2026-10-21 | บันทึกคำตอบที่มีหลักฐานแล้ว: Q-02, Q-03 ครบจาก SPIKE-001 (USD, 1:200, hedging, spec `XAUUSDm`) · Q-05, Q-08 สำหรับ H001 (หน้าต่าง NY, ถือข้ามคืน, cutoff 2025-01-01) · โบรกเกอร์ในข้อ 7 = Exness · ไม่เปลี่ยนค่าใดๆ | Claude (งานบ้านหลัง CORE-001 merge ตามคำสั่งเจ้าของ "เอาเต็มระบบ") | ไม่มีผลต่อเวลา/ค่าใช้จ่าย |
| 2026-10-24 | Q-12 ตอบแล้ว (D-019): ระยะเก็บ holdout และ registry ในข้อ 5 ไม่เป็น [A] แล้ว · กติกาของ R1 ที่เจ้าของรับพร้อมกัน D-014–D-018, D-020 (PLAN-003) | เจ้าของ ("เอาที่ดีที่สุด" = ทางที่แนะนำทุกข้อ) | ไม่มีผลต่อค่าใช้จ่าย · เงื่อนไขของ contract SLICE-R1 |
| 2026-10-25 | Q-10 ตอบแล้ว: งบ VPS ไม่เกิน 40 USD/เดือน และ kill criteria 3 ข้อ · พร้อมอนุมัติ ENV-001, SPIKE-002, ENV-002, D-021, D-022 | เจ้าของ ("อนุมัติทั้งหมด" = ทางที่แนะนำ) | ค่า VPS รายเดือนเริ่มเมื่อเช่า · เพดานงบเป็นเกณฑ์เลือกผู้ให้บริการ |
