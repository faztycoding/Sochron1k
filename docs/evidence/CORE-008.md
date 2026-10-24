# หลักฐาน CORE-008: research (registry, runner, random-entry baseline, robustness, การประเมินตาม H001 ข้อ 8 และรายงาน แบบ pure)

Contract: `docs/contracts/CORE-008-research.md` v1.5 (Tier Standard; อนุมัติแทนโดย delegation ของเจ้าของ 2026-10-24 14:3x หลัง contract review 6 รอบ, veto ได้ก่อน merge) · Branch `feat/CORE-008-research` (merge main `f96e554` ที่มี CORE-007 + CHORE-001 แล้ว) · การสลับบทบาท (D15): ผู้เขียน tests 2 session, ผู้ตรวจ tests รอบ 1 เป็น Claude session ใหม่, ผู้ตรวจ tests รอบ 2 เป็น subagent context ใหม่ ทั้งหมดคนละ session กับผู้ทำ · รายละเอียด tests: `docs/handoff/CORE-008.md`

**ข้อจำกัดของงานนี้:** เขียนเครื่องมือเท่านั้น ไม่รันการทดลองกับข้อมูลจริง ไม่เขียน `research/registry/` จริง (ห้ามก่อน ENV-1 และ SLICE-R1) · ทุก test ใช้ข้อมูลสังเคราะห์และไฟล์ใน `tmp_path`

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 registry: ตัวอย่างบังคับตรงทุกไบต์ (run_id `e3580903…`, 1,671 ไบต์), อ่านคืนได้ค่าและชนิดเดิม, ไฟล์เสียทุกแบบถูกปฏิเสธโดยไฟล์ไม่เปลี่ยน | **PASS** | tests ล็อก AC-01 เขียว |
| AC-02 runner: started → ok/failed, exception เดิมถูก raise, งบ (select 6, robustness 14, รวม 63, ฐานเดียว, setup เดียว, รันซ้ำ), holdout guard มาก่อนทุกการตรวจ | **PASS** | tests ล็อก AC-02 เขียว |
| AC-03 summarize และ percentile ตรงคำตอบที่คำนวณด้วยมือ | **PASS** | tests ล็อก AC-03 เขียว |
| AC-04 random-entry baseline: ลำดับการสุ่มตามขั้นตอน, seed จากฐาน, ข้อมูลราคานิ่งได้ −0.024 ทุกรอบ, คำนวณใน CONTEXT, ปฏิเสธเวลาที่ไม่ใช่ M1 | **PASS** | tests ล็อก AC-04 (r1 + r2) เขียว |
| AC-05 neighbours และ evaluate 10 แถวที่ขอบเกณฑ์ทุกแถว, input ที่ขาด, input ไม่สอดคล้อง | **PASS** | tests ล็อก AC-05 (r1 + r2) เขียว |
| AC-06 รายงานตรงแบบทุกบรรทัด, architecture (import และ I/O), `entry_blockers` | **PASS** | report + entry_blockers เขียว · architecture 18 tests เขียว |
| AC-07 ทั้ง suite ผ่าน skipped 0 | **PASS ในเครื่อง** · CI รอ run ของ PR | `3343 passed` ที่ `23ba734` |
| ความเร็ว (unit test/หลักฐาน): baseline 1,000 รอบ × K = 100 × h ≈ 200 บน M1 100,000 แท่ง | **วัดแล้ว 72.3 วินาที** | ช้ากว่าสูตรที่ contract ประมาณราว 2.5 เท่า ดูหัวข้อ "ความเร็ว" |

## สิ่งที่ส่งมอบ (ไฟล์)
- `src/sochron/research/` 11 ไฟล์: `model.py` (ค่าคงที่, error, Dataset, Summary, BaselineSummary), `records.py` (RunRecord, รูปแบบ canonical, การอ่านบรรทัด), `registry.py` (อ่าน/เขียนไฟล์ที่เดียว), `stats.py`, `inputs.py` (การตรวจที่ runner กับ baseline ใช้ร่วมกัน), `runner.py`, `baseline.py`, `robustness.py`, `evaluate.py`, `report.py`, `__init__.py`
- `src/sochron/strategy/h001.py`, `__init__.py`: `entry_blockers` แทน `_invalid` (D1) · decide ให้ผลเดิม (tests ล็อกของ CORE-006 เขียวครบ) · `STRATEGY_VERSION` คงเดิม
- `tests/unit/research/test_research_unit.py` (21 tests)
- tests ล็อก: `tests/acceptance/CORE-008/test_research.py`, `tests/golden/CORE-008/research_cases.py`, `tests/architecture/test_imports.py` (patch D-006 2 รอบ)
- `docs/handoff/CORE-008.md` · `docs/reviews/CORE-008-tests-r1.md`, `-tests-r2.md` · ไฟล์นี้

## การตัดสินใจของผู้ทำ (ที่ contract เปิดไว้)
- ทุกการเทียบที่ contract ให้เทียบ "แบบ string ของ record" (ฐาน, setup, identity ของรัน, ความสอดคล้องใน evaluate, จำนวน params/ชุดข้อมูลที่ต่างกัน) เทียบค่าในรูปที่เขียนลงไฟล์ ดังนั้น equity `1E+4` กับ `10000` ถือว่าต่างกัน รวมถึง setup lock (ผู้ตรวจ tests r2 ถามข้อนี้ไว้ F2: ผมเลือกทางเดียวกับข้อ 4 ของ runner และมี unit test ล็อกไว้) · **เจ้าของ veto ได้**
- argument ชื่อ `registry` (path ของไฟล์) บังชื่อโมดูล จึง import โมดูลเป็น `registry_module` แล้วเรียก `registry_module.append_record` ตอนใช้งาน (seam ของ tests ยังแทนได้ตามเดิม)
- Summary และ BaselineSummary ปฏิเสธค่าผิดโดเมนด้วย (ตัวนับติดลบ, Decimal ไม่ finite, ปีไม่เรียงหรือซ้ำ) นอกเหนือจากชนิด · ค่าที่ได้จาก `summarize` ผ่านเสมอ
- ผลรวมที่เกินช่วงของ Decimal ใน research เป็น `ResearchError` ("too large") เหมือนที่ CORE-007 ทำ · error จาก backtest, strategy, costs, timebase และ sizer ยังส่งต่อตรงๆ ตาม contract
- `percentile` หาลำดับ ⌈q·n⌉ ด้วยจำนวนเต็มแบบแม่นยำ จึงไม่ขึ้นกับ context ของผู้เรียก (tests r2 F1)
- นามสกุล `.jsonl` ต้องตรงตัวพิมพ์ · บรรทัด "ชุดข้อมูล" ในรายงานมาจาก Evaluation, บรรทัด setup มาจาก record ฐาน · บรรทัด screen เขียน "H001" ตามแบบใน contract
- stdlib ที่ใช้: collections.abc, dataclasses, datetime, decimal, hashlib, json, pathlib, random, types, typing (อยู่ในรายการของ contract)

## Checks (2026-10-24, +07, Windows 11, Git Bash, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| ผู้เขียน tests r1 (Claude session ใหม่, headless ที่ 1 จาก 6) | patch `48d5915f…` · 103 acceptance + architecture 1 · reference ของผู้เขียนผ่านทุก test | 320c5cd | 14:3x–15:18 |
| tests r1: `git apply --check` / `git apply` / `git apply -R --check` (แยกคำสั่ง) | PASS · detector 3 ไฟล์ตรง target · SHA256/blob 6 ค่าตรง handoff | 9f3bc63 | 15:2x |
| red r1 | 104 failed, 3212 passed (ทุกข้อล้มเพราะ "not implemented") | 9f3bc63 + r1 | 15:27 |
| tests review r1 (Claude session ใหม่, headless ที่ 2) | Ready to commit red: yes · golden 404 ค่าคำนวณซ้ำอิสระ ไม่ผิด · Low F1–F6 (ช่องที่ยังไม่ครอบ) | 9f3bc63 + r1 | 15:2x–16:00 |
| commit red r1 | `7523407` | – | 16:0x |
| ผู้เขียน tests r2 (Claude session ใหม่, headless ที่ 3) | patch `ff1e1ca0…` (+6 tests) · ติด deny rule ตอน `cp` ไป path แบบ relative จึงไม่ได้รัน tests ของตัวเอง (หยุดตามกฎ ไม่ลองซ้ำ) | 7523407 | 16:0x–16:24 |
| tests r2: apply 3 คำสั่งแยก | PASS · detector 2 ไฟล์ตรง target · SHA256/blob 4 ค่าตรง handoff | 7523407 | 16:3x |
| red r2 | 110 failed, 3212 passed · tests ใหม่ 6 ข้อล้มที่ `_kit` ด้วย "not implemented" ทุกข้อ | 7523407 + r2 | 16:31:35 |
| tests re-check r2 (subagent `fresh-eyes-reviewer`) | r1 F1–F6 ปิด (F3 (b) รับเป็นความเสี่ยงที่เหลือ) · reference อิสระของผู้ตรวจ r1 ผ่าน 109 · mutant ที่ขอ 9 ตัวถูกจับครบ · Low ใหม่ F1, F2 · Ready to commit red: yes | 7523407 + r2 | 16:3x–16:5x |
| commit red r2 | `3e95c0f` | – | 16:5x |
| วางโค้ด (เขียนใน scratch ระหว่าง review แล้วคัดลอกเข้า) → `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | **3343 passed in 42.43s** (110 tests ล็อกของ CORE-008 เขียวรอบแรก, unit 21) | 23ba734 | 16:53:23 |
| mypy 1.15 ของ extension VS Code `-p sochron` | Success: no issues found in 42 source files | 23ba734 | 16:5x |
| `bash scripts/controls/red-flags.sh origin/main` | 1 กลุ่ม (Lint disabled): `# noqa: E731` 3 บรรทัดใน tests ล็อกของผู้เขียน (ผู้ตรวจ r1 อธิบายแล้ว: test code, style เท่านั้น) และคำว่า noqa ในเอกสาร · โค้ดใน `src` ไม่มี hit · control files: tests ล็อก 3 ไฟล์ | 23ba734 | 16:5x |
| สคริปต์ scratch `measure_r1.py`: M1 random walk 100,000 แท่ง, variant 100 ไม้ถือ 200 M1 (สร้างเอง), baseline 1,000 รอบ | **72.3 s** · ไม้สุ่ม 100,000 ไม้ ถือเฉลี่ย 158.5 M1 (median 200) · อ่าน M1 ≈ 15.9 ล้านแท่ง ≈ 4.5 µs ต่อ M1 รวมทุกต้นทุน | scratch = โค้ดของ 23ba734 ก่อนเพิ่ม overflow guard | 15:54–15:55 (ขณะ session review รันพร้อมกัน) |

## ความเร็วและเวลาที่คาดของ R1
- contract ประมาณ ≈ 1.5 µs ต่อ M1 + ≈ 47 µs ต่อไม้ (ผู้ตรวจ contract วัด) → ขนาดข้างบนควรใช้ ≈ 29 วินาที · วัดจริง 72.3 วินาที (≈ 2.5 เท่า) ในขณะที่อีก session ใช้ CPU อยู่ด้วย
- เวลาเกือบทั้งหมดอยู่ใน `backtest.simulate_trade` ซึ่งตรวจ M1 ทุกแท่งที่อ่าน (CORE-007 v1.5 ข้อ 3) · contract บังคับให้ baseline ใช้ฟังก์ชันนี้ จึงเร่งใน research ไม่ได้
- **R1 ที่ K = 1,500 ไม้, h ≈ 600 M1:** 1,000 × 1,500 × 600 × 4.5 µs ≈ 68 นาทีต่อโครงสร้าง (น้อยลงเมื่อ SL ตัดไม้สั้นลง) แทน ≈ 25 นาทีใน contract · 3 โครงสร้างราว 3 ชั่วโมงรวม
- ถ้าต้องการเร็วขึ้น: งานใหม่ของ backtest ที่ให้ทาง public สำหรับ M1 ที่ตรวจแล้ว (ต้องแก้ contract ของ CORE-007) · ไม่ทำในงานนี้

## ข้อจำกัดที่รับไว้
- tests r2 F3 (b) ไม่ได้สร้าง: บรรทัด setup ในรายงานกับ record แรกของ hypothesis ต่างกันไม่ได้ในไฟล์ที่ runner เขียน (setup เดียวต่อไฟล์) ผู้ตรวจ r2 เห็นด้วย
- ด่าน architecture เป็นแบบ static เหมือนของ FIX-001 (เส้นทางแบบ dynamic มองไม่เห็น) · ไม่มีในโค้ด
- โค้ดไม่ล็อกไฟล์ข้ามโปรเซส: หนึ่งไฟล์ registry ต้องมี runner ครั้งละหนึ่งโปรเซส (F42, เงื่อนไขของ R1)
- ไม่ได้ทดสอบบน Linux ในเครื่อง (CI เป็น ubuntu-24.04) จนกว่า run ของ PR จะเสร็จ

## สิ่งที่เจ้าของต้องตัดสินเองก่อน SLICE-R1 (ไม่อนุมัติแทน)
- Plan ข้อ 5 (ก)–(ฉ) ของ contract: กฎเลือกชุดพารามิเตอร์และ Dataset ของ validation, วิธีรวมคำตัดสินของ 3 โครงสร้าง, งบกับ screen, การลง registry บน holdout, เงื่อนไขของ R1, Q-12 ระยะเก็บ registry
- `docs/architecture.md` ข้อ 8 ให้ research import `data.snapshot` ได้ แต่ contract นี้ห้ามทั้งแพ็กเกจ `data` (tests ทำตาม contract) · R1 ต้องโหลด snapshot จากโมดูลอื่นนอก research หรือแก้ contract (ผู้ตรวจ tests r1 คำถามเปิดข้อ 7)
- setup lock เทียบ equity แบบ string ของ record (ทางที่ผมเลือก) หรือแบบค่า (ผู้ตรวจ tests r2 F2)

## Delivery state
**implemented** และ **verified ในเครื่อง** (3343 passed ที่ `23ba734`) · ถัดไป implementation review (Claude session ใหม่, headless ที่ 4 จาก 6) → แก้ findings → push → PR · ยังไม่ merged, ไม่ deployed
