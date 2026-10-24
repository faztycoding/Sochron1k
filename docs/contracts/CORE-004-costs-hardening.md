# TASK CORE-004 — ทำให้ `sochron.costs` ปฏิเสธ input ผิดแบบเดียวกับ `sochron.risk`

Version v1.2 (v1.2 2026-10-23 เจ้าของตอบระหว่าง 19:2x–20:1x ตาม `docs/reviews/CORE-004-r1.md`: F3 = ตรวจ field ของทุก Provenance record ซ้ำตอนใช้, F4 = status ที่ไม่ใช่ `str` เป็น `TypeError` (เดิม CORE-002 ให้ `BadProvenance`), F5 และ F6 = ข้อจำกัดที่รับไว้ ดูหัวข้อ Risk · acceptance เดิมทุกข้อ) · เดิม v1.1 (ร่าง 2026-10-22 23:2x → v1.1 2026-10-23 18:3x: เจ้าของตัดสินตาม `docs/reviews/CORE-004-tests-r1.md` F1 = ขยาย allowed files ให้แก้ `tests/unit/risk/test_risk_unit.py` บรรทัด 252–254 โดยคงเจตนาเดิม, F2/F3 = ให้ผู้รับบท test author เขียน tests patch รอบ 2 ทันที · acceptance เดิมทุกข้อ) · Owner เจ้าของ repository · Parent `docs/contracts/CORE-002-costs.md` (merged PR #10) · `docs/reviews/CORE-003-security-pre-r1.md` ข้อ "Not checked": costs มี Mapping TOCTOU และรับ subclass แบบเดียวกับที่ risk แก้แล้ว · `docs/contracts/CORE-003-risk.md` v1.9 (ขอบเขตของการป้องกัน) · Tier **Standard** · Branch `fix/CORE-004-costs-hardening`
Status: **merged 2026-10-24 03:21 (PR #15 → main `b7e0dd2`, label owner-approved-control-change); CI ของ PR และของ main เขียว** (`docs/evidence/CORE-004.md` หัวข้อ "หลัง merge") · implemented and verified locally; reviews ปิดครบ 2026-10-24 02:1x (`docs/evidence/CORE-004.md`) · เดิม: approved by owner 2026-10-22 23:4x (acceptance และแผน · ผู้เขียน tests ที่ล็อกและผู้ตรวจ = Claude session ใหม่ตามการสลับบทบาทระหว่าง Codex หมดโควตา)
Hypothesis (research tasks): ไม่ใช่งานวิจัย (ให้บริการ H001 ข้อ 6 Costs)

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no — ไม่มีเส้นทางส่งคำสั่ง (แต่ costs ป้อนเข้า sizing ของ risk gate ใน E1)
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — แก้โค้ดของโมดูล ไม่แก้ด่านควบคุม · tests ที่ล็อกชุดใหม่ (`tests/acceptance/CORE-004/**`) เขียนโดยผู้รับบท test author ส่งเป็น patch ตาม D-006 PR จึงต้องติด label

Standard: ผู้ทำประกาศแผนแล้วทำต่อได้ เว้นแต่มีการตัดสินที่เปลี่ยนผลลัพธ์หลัก · ต้องมี review จากผู้รับบท reviewer ก่อน merge

## Goal / user outcome (Thai)
`sochron.costs` ตอนนี้รับ subclass ของ `Decimal`, `int`, `str`, `date` ได้, อ่าน provenance ของ `CostModel` สองรอบ (ค่าที่ตรวจกับค่าที่เก็บอาจไม่ใช่ชุดเดียวกัน), ไม่ตรวจ model ซ้ำตอนใช้ และ `check_volume` ช้ามากถ้า lots มีเลขชี้กำลังสุดขีด งานนี้ทำให้ costs ปฏิเสธ input เหล่านี้แบบเดียวกับที่ `sochron.risk` ทำแล้ว (ชนิดต้องพอดี, อ่าน provenance ครั้งเดียว, ตรวจ model ซ้ำตอนใช้, เพดานขนาดตัวเลขที่ปฏิเสธเร็ว) **โดยผลของ input ที่ถูกต้องไม่เปลี่ยนเลยแม้แต่หลักเดียว** (tests ที่ล็อกของ CORE-002 ต้องผ่านโดยไม่แก้)

## Current behavior and evidence (revision)
`src/sochron/costs/model.py`: `Provenance.__post_init__` ใช้ `isinstance` (status ที่เป็น str subclass ซ่อนค่า assumed จาก `unknowns()` ได้ — security pre-review r2 "Out of scope") · `CostModel.__post_init__` ใช้ `isinstance` และ `_is_int`, ตรวจ `set(self.provenance)` และ `.items()` แล้วจึง `dict(self.provenance)` อีกรอบ (อ่านสองครั้ง) · `charges.py`: `_lots`, `_points`, `_count`, `_side`, `r_multiple` ใช้ `isinstance` · `check_volume` ใช้ `as_integer_ratio` (CORE-002 F1) จึงสร้าง `10**|exponent|` กับ lots สุดขีด · ฟังก์ชันที่รับ `model` ไม่ตรวจ field ซ้ำ · tests ที่ล็อกของ CORE-002 ไม่มีกรณีที่คาดว่าต้องรับ subclass (grep 2026-10-22)

## Scope
- In scope: `src/sochron/costs/**` · unit tests ของผู้ทำ `tests/unit/costs/**` · tests ที่ล็อกใหม่ `tests/acceptance/CORE-004/**` (และ `tests/golden/CORE-004/**` ถ้าจำเป็น) โดยผู้รับบท test author · evidence · handoff · PROGRESS
- Exclusions: เปลี่ยนสูตรหรือ context ของ costs (precision 28, ROUND_HALF_EVEN) · `sochron.risk` (ยกเว้นถ้า test ของ risk ต้องตามการเปลี่ยนนี้ ซึ่งไม่ควรเกิด) · tests ที่ล็อกของ CORE-002/003 (ห้ามแก้) · ขอบเขตการป้องกัน: เหมือน CORE-003 v1.7 — ไม่กันโค้ดร้ายที่รันใน process เดียวกันและแก้ภายในของ object หรือ runtime (เป็นของ E1 L2)
- Allowed files: `src/sochron/costs/**`, `tests/unit/costs/**`, `tests/unit/risk/test_risk_unit.py` บรรทัด 252–254 เท่านั้น (v1.1, F1: unit test ของ CORE-003 สร้าง `CostModel` ด้วย Decimal subclass ซึ่ง AC-01 ห้าม → ย้ายไปแอบใส่หลังสร้างด้วย `object.__setattr__` โดย risk ยังต้องปฏิเสธเหมือนเดิม), `docs/evidence/CORE-004.md`, `docs/handoff/CORE-004.md`, `docs/proposals/CORE-004-*.patch`, `PROGRESS.md` · โดย test author ผ่าน patch: `tests/acceptance/CORE-004/**`, `tests/golden/CORE-004/**`
- Must not touch: `src/sochron/{timebase,core,risk}/**`, `tests/acceptance/CORE-00{1,2,3}/**`, `tests/golden/CORE-00{1,2,3}/**`, `tests/architecture/**`, `.github/**`, `scripts/controls/**`, `.claude/**`

## Inputs / outputs / errors (contract)
API ของ CORE-002 ไม่เปลี่ยนชื่อหรือ signature · เพิ่มเฉพาะการปฏิเสธ:
| Input | ผล |
|---|---|
| subclass ของ `Decimal`, `int`, `str`, `date`, `bool` ทุกตำแหน่งที่ costs รับ (รวม field ของ `Provenance`, `CostModel`, `CostBreakdown` และ argument ของทุกฟังก์ชัน) · object ที่ไม่ใช่ `CostModel`/`Provenance` พอดี | `TypeError` · ค่าใน provenance ที่ไม่ใช่ `Provenance` พอดี → `BadProvenance` (เหมือนเดิม) |
| provenance container: `dict`, `MappingProxyType`, `Mapping` อื่น → รับ (อ่านครั้งเดียวเป็นสำเนา ตรวจสำเนา เก็บเป็น `MappingProxyType`) · ไม่ใช่ `Mapping` → `TypeError` · key ที่ไม่ใช่ `str` พอดี → `TypeError` ก่อนการตรวจอื่นของ provenance | ตามที่ระบุ |
| field ของ `CostModel` ที่ถูกแก้หลังสร้าง (เช่น `object.__setattr__`) | ทุกฟังก์ชันที่รับ `model` ตรวจ field ทั้งหมดซ้ำด้วยกติกาเดียวกับตอนสร้าง และให้ error เดียวกัน |
| Decimal ที่ coefficient เกิน 1,000 หลัก หรือไม่ใช่ศูนย์และ `abs(adjusted())` > 1,100,000 (เพดานเดียวกับ risk) ทุกตำแหน่ง | error ของช่องนั้น: lots → `BadVolume`, points → `BadPoints`, `r` → `BadR`, `stress_factor`/factor → `BadStress`, field อื่นของ model และ `money` → `CostsError` · ปฏิเสธก่อนแปลงเป็นตรรกยะ และทุกครั้ง < 1.000 วินาทีบนเครื่องอ้างอิง (Decimal ที่สร้างไว้ก่อน, `perf_counter` รอบการเรียก) |
| int ขนาดยักษ์ที่ผิดโดเมน (เช่น nights = −10**5000) | error เดิมของช่องนั้น ไม่ใช่ `ValueError` จากการแปลงเป็น str |
| (v1.2, r1 F3) Provenance record ใน model ที่ field ถูกแก้หลังสร้าง | ทุกการใช้ model ตรวจ record ซ้ำด้วยกติกาเดียวกับตอนสร้าง Provenance และให้ error เดียวกัน |
| (v1.2, r1 F4) `status` ที่ไม่ใช่ `str` (เช่น `None`, `1`) | `TypeError` ตามกติกาทั่วไป "ชนิดผิด = `TypeError`" (CORE-002 เดิมให้ `BadProvenance`) · `str` ที่ไม่อยู่ใน 4 ค่ายังเป็น `BadProvenance` |

## Invariants
- input ที่ถูกต้องให้ผลเท่าเดิมทุกหลัก: tests ที่ล็อกของ CORE-002 และ CORE-003 ผ่านโดยไม่แก้ · `H001_COSTS` เท่าเดิม
- context ของผู้เรียกไม่เปลี่ยน (เหมือน CORE-002) · ไม่มี float, นาฬิกา, I/O, random (architecture test เดิม)
- อ่าน provenance ครั้งเดียวต่อการสร้างหรือการใช้ และก่อน field อื่น · ผลที่คืนไม่อ่าน provenance ซ้ำหลังตัดสิน

## Negative cases
subclass ที่ตอบ `is_finite`/`as_integer_ratio`/`==` หลอก · `Provenance(status=StrSubclass("measured"))` · Mapping ที่เปลี่ยนค่าระหว่างอ่าน · model ที่ `volume_step` ถูกแก้เป็น 0/ลบหลังสร้าง · lots `1E-999999999` ใน `check_volume` · `0E-999999999999999999` ที่ถูกต้อง (ศูนย์ไม่ติดเพดาน exponent) ต้องให้ผลเหมือน 0 · nights −10**5000

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given subclass ของ `Decimal`, `int`, `str`, `date`, `bool` (รวมแบบที่ตอบ method หลอก) ในทุกตำแหน่ง และ subclass ของ `CostModel`/`Provenance`, When สร้าง object หรือเรียกฟังก์ชันของ costs, Then `TypeError` (ค่าใน provenance → `BadProvenance`) และไม่มีกรณีไหนคืนค่า
- AC-02 Given provenance เป็น `dict`, `MappingProxyType` และ `Mapping` ที่เขียนเอง, When สร้าง `CostModel`, Then รับ, อ่าน container ครั้งเดียว (หนึ่ง traversal, แต่ละ key ครั้งเดียว), เก็บเป็น `MappingProxyType` ของสำเนา · container ที่ไม่ใช่ Mapping หรือ key ที่ไม่ใช่ `str` พอดี → `TypeError`
- AC-03 Given `CostModel` ที่ field ถูกแก้หลังสร้างเป็นค่าผิด (ทีละ field), When เรียกทุกฟังก์ชันที่รับ `model`, Then ได้ error เดียวกับตอนสร้าง
- AC-04 Given Decimal เกินเพดาน (1,001 หลัก รวม trailing zero; `adjusted` ±1,100,001) ในแต่ละช่อง, When เรียก, Then ได้ error ของช่องนั้นภายใน 1.000 วินาที · ค่าที่ขอบพอดี (1,000 หลัก, ±1,100,000, ศูนย์เลขชี้กำลังใดก็ได้) รับได้
- AC-05 Given input ที่ถูกต้องทั้งหมดของ CORE-002, When รัน `uv run --offline pytest tests -q -p no:cacheprovider`, Then tests ที่ล็อกของ CORE-002/003 และ unit tests ทั้งหมดผ่านโดยไม่แก้ tests เดิม (ยกเว้น `tests/unit/risk/test_risk_unit.py` บรรทัด 252–254 ตามที่เจ้าของอนุมัติใน v1.1), skipped 0
- AC-06 Given int ขนาดยักษ์ที่ผิดโดเมนในช่องนับ (nights, triple_nights, sides, field int ของ model), When เรียก, Then ได้ error เดิมของช่องนั้น (ไม่ใช่ `ValueError` ธรรมดาจากการแปลงเป็นข้อความ)

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–04, 06 | test author: `tests/acceptance/CORE-004` · Claude: unit tests | `uv run --offline pytest tests -q -p no:cacheprovider` | L2 · L3 เมื่อ OPS-001 merge |
| 05 | CI + Claude | คำสั่งเดียวกัน + `git diff origin/main -- tests/acceptance/CORE-002 tests/golden/CORE-002 tests/acceptance/CORE-003 tests/golden/CORE-003` ว่าง | L2/L3 |
| ทั้งหมด | ผู้รับบท reviewer | cross-agent review | review |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยงหลัก: ผลของ input ที่ถูกต้องเปลี่ยน → AC-05 และ golden ของ CORE-002 · risk พึ่ง costs (`CostModel`, `Provenance`, `CONTEXT`) → suite ของ CORE-003 ต้องผ่าน
ข้อจำกัดที่เจ้าของรับไว้ (v1.2): **F5** int ในโดเมนที่ใหญ่ระดับล้านหลัก (points, sides, nights, factor) ทำให้การเรียกครั้งเดียวช้าราว 15 วินาที ซึ่งเป็นอยู่แล้วบน main ก่อน CORE-004 และ contract นี้คุมขนาดเฉพาะ Decimal · ค่าจริงมาจาก MT5 และ E1 ต้องตรวจตอนสร้าง (แนวเดียวกับ CORE-003 E1 L3) · **F6** subclass ที่ใช้ metaclass ประหลาดเลือกชนิด error ตอนถูกปฏิเสธได้ แต่ยังถูกปฏิเสธเสมอ (รูปแบบเดียวกับ risk; โค้ดร้ายใน process อยู่นอกขอบเขตตาม CORE-003 v1.7, E1 L2)

## Plan, dependencies and unknowns (P06)
1. Understanding: ยกรูปแบบป้องกันของ risk (`require_exact`, `finite_bounded`, snapshot provenance, validate ตอนใช้) มาใช้ใน costs โดยไม่เปลี่ยนผลของ input ที่ถูกต้อง · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่าเปลี่ยนสูตร/การปัด — ไม่ (ข) คิดว่าแก้ tests ที่ล็อกเดิม — ไม่ (ค) คิดว่ากันโค้ดร้ายใน process — ไม่ (ขอบเขต v1.7 ของ CORE-003)
2. Files / reuse: `model.py`, `charges.py`, `errors.py` (ถ้าต้อง) · ยืมแนวคิดจาก `sochron.risk.policy` (ห้าม import risk เข้า costs: module map ให้ risk พึ่ง costs ไม่ใช่กลับกัน จึงเขียน helper ใน costs เอง)
3. Steps: (1) เจ้าของอนุมัติ → (2) ผู้รับบท test author เขียน `tests/acceptance/CORE-004` เป็น patch → apply ตาม D-006 + hash + fresh review → commit red → (3) Claude implement + unit tests → suite เขียว → commit → push → (4) ผู้รับบท reviewer ตรวจ → `/fix-findings` → (5) PR (label) → merge
4. Risks: ดูข้างบน
5. Decisions needed from the owner: ไม่มี (เพดานใช้ค่าเดียวกับ risk; error ของแต่ละช่องตามตาราง) นอกจากผู้รับบท test author/reviewer ระหว่างที่ Codex หมดโควตา

## Authorization (filled by the owner)
- เจ้าของอนุมัติ 2026-10-22 23:4x · Claude: `src/sochron/costs/**`, unit tests, evidence, handoff, PROGRESS, apply patch ตาม D-006, push task branch · ผู้รับบท test author: tests ที่ล็อกของ CORE-004 · ผู้รับบท reviewer: review

## Budget
1–2 sessions · headless session ไม่เกิน 6 (tests, fresh review, review ×2, สำรอง ×2) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียงนอกเครื่อง

## DoR status / missing items / next action
ครบ: CORE-002 merged, รูปแบบอ้างอิงใน CORE-003 · ขาด: การอนุมัติ, ผู้รับบท test author/reviewer · next: เจ้าของอนุมัติ

## Done scope
merge แล้ว, suite เขียว (ในเครื่องและ CI ถ้า OPS-001 merge ก่อน)
