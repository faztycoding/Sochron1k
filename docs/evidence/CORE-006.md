# หลักฐาน CORE-006: strategy H001 (indicators และ decide แบบ pure และมี version)

Contract: `docs/contracts/CORE-006-strategy-h001.md` v1.1 (Tier Standard; เจ้าของอนุมัติ 2026-10-23 15:0x · เริ่มก่อน CORE-005 merge และ v1.1 ภายใต้อำนาจที่เจ้าของมอบไว้ 2026-10-24 ~07:0x "เอา recommanded ทุกอัน", veto ได้ก่อน merge) · Branch `feat/CORE-006-strategy-h001` (ต่อจาก CORE-005 ซึ่ง merge แล้วเป็น `419eee3`) · การสลับบทบาท: ผู้เขียน tests 2 session และผู้ตรวจ tests 2 session เป็น Claude session ใหม่ คนละ session กับผู้ทำ · รายละเอียด tests: `docs/handoff/CORE-006.md`

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 พารามิเตอร์ในช่วง H001 ข้อ 4, ค่านอกช่วง/ผิดชนิดถูกปฏิเสธ, ค่าตั้งต้นตรงตาราง | **PASS** | tests ล็อก AC-01 เขียว |
| AC-02 indicators ตรง golden ที่คำนวณด้วยมือ | **PASS** | golden 4 ชุด (S, P, G และ E ที่ค่าตั้งต้นซึ่งล็อกสูตร EMA ของ v1.1) เขียว |
| AC-03 ตัวอย่างใน H001 ได้ enter ระยะ SL 12.00 ทั้ง V-A/V-B/V-C และฝั่งกลับด้าน | **PASS** | tests ล็อก AC-03 เขียว |
| AC-04 ปิดตามกฎ, สัญญาณตรงข้ามปิดโดยไม่เปิดสวน, hold | **PASS** | tests ล็อก AC-04 เขียว |
| AC-05 invalidation ทุกข้อ ทีละข้อและพร้อมกัน, ขอบหน้าต่าง NY ทั้งสองวันเปลี่ยน DST | **PASS** | tests ล็อก AC-05 เขียว |
| AC-06 ไม่ดูข้อมูลอนาคต, pure, import ได้เฉพาะ core/timebase/stdlib ที่อนุญาต | **PASS** | tests ล็อก AC-06 + architecture (allowlist ของ stdlib) เขียว |
| AC-07 ทั้ง suite ผ่าน skipped 0 | **PASS ในเครื่อง** · CI รอ PR | `3084 passed` ที่ `3fc487e` |

## สิ่งที่ส่งมอบ (ไฟล์)
- `src/sochron/strategy/{__init__,params,indicators,h001}.py`
- `tests/unit/strategy/test_strategy_unit.py` (1 − α ที่ s = 62, sliding window เทียบ brute force, ความเร็ว 60,000 แท่ง)
- tests ล็อก: `tests/acceptance/CORE-006/test_strategy_h001.py`, `tests/golden/CORE-006/strategy_cases.py`, `tests/architecture/test_imports.py` (patch D-006 2 รอบ)
- `docs/contracts/CORE-006-strategy-h001.md` v1.1 · `docs/handoff/CORE-006.md` · `docs/reviews/CORE-006-tests-r1.md`, `-tests-r2.md` · ไฟล์นี้

## การตัดสินใจของผู้ทำ
- context Decimal ของโมดูลเอง (precision 28, ROUND_HALF_EVEN) เพราะ strategy import `costs` ไม่ได้ · ผลไม่ขึ้นกับ context ของผู้เรียกและไม่แตะ context นั้น
- HH/LL ใช้ deque แบบ monotonic, median ใช้ list ที่เรียงไว้ (bisect), flags ใช้ Counter แบบ sliding → O(n)
- แท่ง M15 รับแบบ duck typing (contract v1.1 ข้อ 7) · ตรวจ type ของ `rows[t]` และ `rows[t−1]` เท่านั้นใน `decide` เพื่อไม่ให้ backtest เป็น O(n²)
- import stdlib อยู่ใน allowlist ของ tests รอบ 2: bisect, collections, dataclasses, datetime, decimal, types, typing

## Checks (2026-10-24, +07, Windows 11, Git Bash, uv 0.13.0, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| tests r1: `git apply --check` / `git apply` / `git apply -R --check docs/proposals/CORE-006-tests.patch` (แยกคำสั่ง) | PASS · detector 3 ไฟล์ตรง target · SHA256/blob 6 ค่าตรง handoff | 812207c | 07:50 |
| red | 142 failed, 2876 passed | 812207c + r1 | 07:50:56 |
| fresh review tests r1 | ready to commit red · F1 Medium, F2–F4 Low (ขอ tests เพิ่ม) | – | 07:5x–08:14 |
| commit red | `a1c5188` | – | 08:1x |
| tests r2: apply 3 คำสั่งแยก | PASS · detector 3 ไฟล์ตรง target · acceptance `9b985946…`/`ef61bef6…`, golden `831ccd85…`/`9e9dadf5…`, architecture `e0f1cc4f…`/`504c88a6…` ตรง handoff | a1c5188 | 08:50 |
| red | 205 failed, 2876 passed | a1c5188 + r2 | 08:50:11 |
| fresh review tests r2 | F1–F4 ปิด · F5, F6 Low · ready to commit red | – | 08:50–09:07 |
| commit red r2 | `3eb1579` | – | 09:08 |
| วางโค้ด → `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | **3081 passed** (รันแรก) → เพิ่ม unit tests → **3084 passed in 25.18s** | 3fc487e | 09:08–09:11 |
| สคริปต์ scratch: 170,000 แท่ง M15 สังเคราะห์ | indicators 1.20 s · decide ทุกแท่ง 0.34 s | ก่อน 3fc487e (โค้ดเดียวกัน) | 08:2x |
| สคริปต์ scratch: random walk 20,000 แท่ง (seed 20261024) | มีสัญญาณเข้าทุก variant (V-A 92 long / 85 short, V-B 561 / 487) · skip ส่วนใหญ่ outside_window | – | 08:2x |
| `bash scripts/controls/red-flags.sh origin/main` | 2 กลุ่ม: Lint disabled (คำว่า noqa ในเอกสาร) และ Destructive or bypass (flag `--force-local` ของ tar ในข้อความ handoff/review) ไม่ใช่โค้ด | 3fc487e | 09:09 |

## ข้อจำกัดที่รับไว้ (โดยอำนาจที่เจ้าของมอบ)
- **tests-r2 F5:** ด่าน architecture แบบ static มองไม่เห็นโค้ดที่รันจาก string (`exec`, `eval`, `compile`) · ไม่มีใน src และ review จะจับได้ · บันทึกเป็นงานติดตามใน PROGRESS.md หัวข้อ "Claude ถัดไป" ข้อ (ข) (เดิมเขียนว่าใส่ในงานติดตามของ FIX-001 แล้ว ซึ่งยังไม่มีบันทึกจริง: review CORE-006-r1 F5)
- **tests-r2 F6:** golden ล็อกการคำนวณ 1 − α แค่ที่ period ค่าตั้งต้น · ผู้ทำล็อกการอ่าน "1 − α จาก α ที่ปัดแล้ว" ด้วย unit test ที่ s = 62 (ไม่ใช่ test ล็อก) เพื่อไม่ใช้ headless session เกินงบ 5
- ผลจริงของ D3 (WARN flags ทำให้ข้ามไม้ราวหนึ่งวัน) ต้องวัดใน R1

## Delivery state
implemented และ verified ในเครื่อง (3084 passed at `3fc487e`) · tests reviews r1–r2 ปิด · implementation review: รอ · ยังไม่ merged, ไม่ deployed
