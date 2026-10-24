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
| AC-07 ทั้ง suite ผ่าน skipped 0 | **PASS ในเครื่อง** · CI รอ run ของ PR | `3093 passed` ที่ `52c8680` (โค้ดหลังแก้ review r1; commit หลังจากนั้นเป็นเอกสาร) · ครั้งแรก `3084 passed` ที่ `3fc487e` |

## สิ่งที่ส่งมอบ (ไฟล์)
- `src/sochron/strategy/{__init__,params,indicators,h001}.py`
- `tests/unit/strategy/test_strategy_unit.py` (1 − α ที่ s = 62 และที่ f = 22, s = 78 · sliding window เทียบ brute force · ความเร็ว 60,000 แท่ง · regression ของ review r1: F1 threshold ฝั่ง short กลับด้านพอดี, F2 เวลาไม่มี timezone → StrategyError, F3 ขนาด Counter ของ flags)
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
| implementation review r1 (Claude session ใหม่, headless ที่ 5 จาก 5) | Ready for PR: yes · Low F1–F5 · oracle อิสระ 58,035 แถว / 174,105 decisions ไม่ตรง 0 · 170,000 แท่ง indicators 1.8–4.1 s, decide 0.7–1.1 s | 7dfde0e | 09:15–09:27 |
| แก้ F1 → `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | regression ล้มก่อนแก้ (`none` แทน `enter_short`) · 3085 passed | 6b22b5b | 09:34 |
| แก้ F2 → suite | regression ล้มก่อนแก้ 6/6 · 3091 passed | 9338b46 | 09:35 |
| แก้ F3 → suite | regression ล้มก่อนแก้ (600 key > 98) · flag ใหม่ทุกแท่ง 2,000/4,000/8,000/16,000 แท่ง = 0.025/0.052/0.115/0.258 s · 3092 passed | 7055ea9 | 09:37 |
| เพิ่ม test F4 → mutant M2 ใน scratch / โค้ดจริง | M2: 1 failed, 3092 passed · โค้ดจริง: **3093 passed** | 52c8680 | 09:38 |
| F5 → `grep -c "CORE-006 tests-r2 F5" PROGRESS.md` | 1 | 6f93f6e | 09:39 |
| re-check r2 (subagent `fresh-eyes-reviewer`) | F1–F5 ปิด · F6 Low (เอกสาร) · suite 3093 passed · Ready for PR: yes | 9548ee3 | 09:40–09:52 |
| `bash scripts/controls/red-flags.sh origin/main` | 2 กลุ่มเดิม (เอกสารเท่านั้น) | 9548ee3 | 09:5x |
| `git push origin HEAD:refs/heads/feat/CORE-006-strategy-h001` (คำสั่งเดี่ยว) | new branch · รอบแรกถูก guard-bash บล็อกเพราะมี `cd … &&` นำหน้า → รันใหม่เป็นคำสั่งเดี่ยวตามข้อยกเว้นของเจ้าของ | 9548ee3 | 09:5x |

## ข้อจำกัดที่รับไว้ (โดยอำนาจที่เจ้าของมอบ)
- **tests-r2 F5:** ด่าน architecture แบบ static มองไม่เห็นโค้ดที่รันจาก string (`exec`, `eval`, `compile`) · ไม่มีใน src และ review จะจับได้ · บันทึกเป็นงานติดตามใน PROGRESS.md หัวข้อ "Claude ถัดไป" ข้อ (ข) (เดิมเขียนว่าใส่ในงานติดตามของ FIX-001 แล้ว ซึ่งยังไม่มีบันทึกจริง: review CORE-006-r1 F5)
- **tests-r2 F6:** golden ล็อกการคำนวณ 1 − α แค่ที่ period ค่าตั้งต้น · ผู้ทำล็อกการอ่าน "1 − α จาก α ที่ปัดแล้ว" ด้วย unit test ที่ s = 62 และ (ตาม review r1 F4) ที่ f = 22, s = 78 ซึ่งครอบ EMA เร็วด้วย (ไม่ใช่ test ล็อก) เพื่อไม่ใช้ headless session เกินงบ 5
- ผลจริงของ D3 (WARN flags ทำให้ข้ามไม้ราวหนึ่งวัน) ต้องวัดใน R1

## หลัง merge (2026-10-24, GitHub REST API แบบไม่ล็อกอิน)
- PR #17 `feat/CORE-006-strategy-h001` · Claude push ถึง `b7256cd` · เจ้าของกด "Update branch" บน GitHub → merge commit `8ead8af` (รวม `419eee3` ของ main ซึ่งไม่เปลี่ยนไฟล์: `git diff --stat b7256cd 8ead8af` ว่าง) · เจ้าของ merge เป็น `6fbed53` 10:20 +07 (03:20:04Z) · label `owner-approved-control-change` · `git diff --quiet b7256cd 6fbed53` → tree ของ main ตรงกับ `b7256cd` ทุกไฟล์

| Run | Event / head | ผล |
|-----|--------------|----|
| `40057041807` ci | pull_request `b7256cd` | success |
| `40057040644` control-gate | pull_request_target `b7256cd` (opened) | failure: event "opened" มาก่อน label (เหมือนทุก PR) |
| `40057053910` control-gate | pull_request_target `b7256cd` (labeled) | success |
| `40057582876` ci | pull_request `8ead8af` | success |
| `40057581599` control-gate | pull_request_target `8ead8af` | success |
| `40057873820` ci | push `6fbed53` (main) | success |

## Delivery state
**merged** 2026-10-24 10:20 (PR #17 → `6fbed53`) · CI เขียวบน PR และ main · เดิม: implemented และ verified ในเครื่อง (3093 passed at `52c8680`) · tests reviews r1–r2 ปิด · implementation review r1 (`docs/reviews/CORE-006-r1.md`, Ready for PR: yes, Low F1–F5) → แก้ครบ → re-check r2 (`docs/reviews/CORE-006-r2.md`, subagent context ใหม่): F1–F5 ปิด, F6 Low (เอกสารนี้) แก้ใน commit นี้ · push แล้ว รอเจ้าของเปิด PR และ CI · ยังไม่ merged, ไม่ deployed
