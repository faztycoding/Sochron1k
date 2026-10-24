# หลักฐาน CORE-005: `core.Bar` + `data.snapshot` (ตรวจคุณภาพ M1 และประกอบ M15 แบบ pure)

Contract: `docs/contracts/CORE-005-data-bars.md` v1.3 (Tier Standard; เจ้าของอนุมัติ 2026-10-23 15:0x, v1.1 2026-10-24 03:0x, v1.2 ~06:0x, v1.3 ~06:3x) · Branch `feat/CORE-005-data-bars` (จาก main `6bd9ef8` + merge main `b7e0dd2` ที่มี CORE-004) · การสลับบทบาท: ผู้เขียน tests 2 session และผู้ตรวจ tests 2 session เป็น Claude session ใหม่ คนละ session กับผู้ทำ · รายละเอียด tests: `docs/handoff/CORE-005.md`

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 `Bar` ชนิดพอดี, finite, timeframe อยู่ในชุด, แก้ไม่ได้ (+ v1.1: tick_volume ≥ 0, m1_count ≥ 1, time_utc เป็น UTC) | **PASS** | tests ล็อก AC-01 เขียว |
| AC-02 ประกอบ M15 ตรง golden ที่คำนวณด้วยมือ | **PASS** | golden 148 แถว M1 → 11 แถว M15 ตรงทุกค่า (ผู้ตรวจ tests-r1 คำนวณซ้ำด้วยตัวเอง 0 ผิด) |
| AC-03 รายงาน defect ทุกรหัสพร้อม severity และเวลา ไม่แก้ input | **PASS** | tests ล็อก AC-03 เขียว |
| AC-04 ช่องว่างเทียบปฏิทิน NY ทั้งสองวันเปลี่ยน DST, ขอบ `max_gap_minutes` | **PASS** | tests ล็อก AC-04 เขียว |
| AC-05 สถานะรายวัน STOP > UNKNOWN > WARN > PASS, วันธรรมดาว่างเป็น UNKNOWN | **PASS** | tests ล็อก AC-05 เขียว |
| AC-06 ไม่มี I/O, นาฬิกา, สุ่ม, float ใน snapshot, import ได้เฉพาะ core/timebase (+ `data/__init__.py`) | **PASS** | `tests/architecture` เขียว |
| AC-07 ทั้ง suite ผ่าน skipped 0 | **PASS ในเครื่อง** · CI รอ PR | `2876 passed` ที่ `a158abf` (หลังแก้ review r1–r2; ก่อนแก้ 2870 ที่ `07d2639`) |

## สิ่งที่ส่งมอบ (ไฟล์)
- `src/sochron/core/__init__.py` (`Bar`, `TIMEFRAMES_MINUTES`) · เจ้าของ commit เป็น `7fd6fe1` ("f") จากโค้ดที่ Claude วางไว้ (ตรงกับร่างทุก byte)
- `src/sochron/data/__init__.py` (docstring อย่างเดียว) · `src/sochron/data/snapshot/{__init__,model,validate,aggregate}.py`
- `tests/unit/core/test_core_unit.py`, `tests/unit/snapshot/test_snapshot_unit.py` (unit tests ของผู้ทำ)
- `.gitignore` ข้อยกเว้น `.py` ของ `src/sochron/data/` (v1.2)
- tests ล็อก: `tests/acceptance/CORE-005/test_data_bars.py`, `tests/golden/CORE-005/bars_cases.py`, `tests/architecture/test_imports.py` (patch D-006 2 รอบ)

## การตัดสินใจของผู้ทำ
- `core` import อะไรจาก `sochron` ไม่ได้ (module map) จึงเก็บชุด timeframe ซ้ำกับ `timebase` และมี unit test บังคับให้เท่ากัน
- `ValidationReport.calendar` (v1.1) ให้ `aggregate` ตัดสิน `incomplete` จากนาทีที่ขาดในเวลาเปิดตลาดเท่านั้น
- การแปลงเวลาทั้งหมดผ่าน `timebase` (`to_utc`, `to_zone`, `bar_open`) · ปฏิทินที่ zone ไม่มีจริงถูกปฏิเสธตอนสร้าง
- นับช่องว่างทีละนาทีแบบหยุดเมื่อเกิน `max_gap_minutes` (ช่วงปิดสุดสัปดาห์ต้องไล่ครบ) · วัดแล้วเร็วพอ (ข้างล่าง)
- `aggregate` ปฏิเสธ report ที่ทำจากจำนวนแท่งต่างกัน (`ValueError`)

## Checks (2026-10-24, +07, Windows 11, Git Bash, uv 0.13.0, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| tests r1: `git apply --check` / `git apply` / `git apply -R --check docs/proposals/CORE-005-tests.patch` (แยกคำสั่ง) | PASS · detector 3 ไฟล์ตรง target · SHA256/blob 6 ค่าตรง handoff | 764cfe4 | 02:31 |
| red: `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider --tb=no` | 46 failed, 791 passed (ตรง handoff) | 764cfe4 + r1 | 02:32 |
| fresh review tests r1 | **ยังไม่พร้อม**: F1 High (2 แถวพังเอง), F2–F12 · เจ้าของรับข้อเสนอทั้งหมด 03:0x → contract v1.1 `f9504f8` | – | 02:3x–02:53 |
| tests r2: apply 3 คำสั่งแยก | PASS · detector 2 ไฟล์ตรง target · acceptance `ec99d21b…`/`f3273a15…`, architecture `2d3d05d3…`/`1319cce4…` ตรง handoff | f9504f8 | 03:42 |
| red | 56 failed, 793 passed (ตรง handoff) | f9504f8 + r1 + r2 | 03:42:56 |
| fresh review tests r2 | F1–F12 ปิด · F13 ถ้อยคำ contract · Ready to commit red: yes · reference ของผู้ตรวจผ่าน 68/68, mutant 32/32 ถูกจับ | – | 03:43–04:00 |
| commit red / F13 / merge main | `3605818` / `5993560` / `d97bd1f` | – | 04:00 |
| `git check-ignore -v --no-index` หลังแก้ `.gitignore` | `.parquet`, `.csv`, `.pyc` ใต้ `src/sochron/data/` ยังถูกกัน · `model.py` track · `data/` ที่ root ยังถูกกัน | b54605d | 06:12 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | **2855 passed** (รันแรกหลังวางโค้ด) → เพิ่ม unit tests → **2870 passed in 10.03s** | 07d2639 | 06:12–06:13 |
| ความเร็ว: สคริปต์ scratch `perf_core005.py` (M1 สังเคราะห์รูปแบบ XAUUSDm, 500,000 แท่ง) | build 2.92 s · `validate_m1` **3.08 s** · `aggregate` **0.91 s** · defects 0 | 07d2639 | 06:12 |
| `bash scripts/controls/red-flags.sh origin/main` | 1 กลุ่ม (Lint disabled) = คำว่า noqa ในข้อความของ handoff/review ไม่ใช่โค้ด | 07d2639 | 06:13 |

## Blocks และเหตุการณ์ระหว่างทาง
- permission ปฏิเสธ `sed -n` อ่านไฟล์ golden ที่ล็อก (2026-10-24 ~02:4x) → หยุดตามกฎ ไม่อ่านด้วยเครื่องมืออื่น · เขียนโค้ดจาก contract และ acceptance test แล้วให้ golden test ตัดสิน (ผ่าน)
- detector หลัง `git merge --no-ff origin/main` (`d97bd1f`) รายงานไฟล์ล็อก `tests/acceptance/CORE-004/test_costs_hardening.py` ที่มาจาก main (ไม่ใช่ patch D-006) → หยุดถาม · หลักฐาน: blob `cc64a073…` เท่ากับบน `origin/main` · เจ้าของตอบ "ได้ ทำต่อเลย" (04:0x)
- กฎ `data/` ใน `.gitignore` จับ `src/sochron/data/` → หยุดถาม · เจ้าของเลือกยกเว้นเฉพาะ `.py` (v1.2)

## ยังไม่ได้ทดสอบ / ข้อจำกัด
- CI บน Linux จนกว่า PR จะรัน · ข้อมูลตลาดจริง (ห้ามก่อน ENV-1)
- ปฏิทินช่วงปิด (D2) และ `max_gap_minutes` (D3) เป็นค่า [A]: กับข้อมูลรูปแบบ SPIKE-001 แท่ง M15 16:45 NY จะติด `incomplete` ทุกวัน และช่วงพัก 67 นาทีขึ้นไปเป็น WARN → R1 ต้องวัดช่วงพักจริงก่อนตั้งค่า (เจ้าของเลือก 2026-10-24 03:0x)
- การอ่าน Parquet/manifest ยังไม่มี (ต้อง admission dependency ใน SLICE-R1)

## Implementation review r1 (`docs/reviews/CORE-005-r1.md`) และการตอบ
ผล: ยังไม่พร้อม PR · F1 Medium + Low F2–F9 · เจ้าของตัดสิน 2026-10-24 ~06:3x ตามทางที่ Claude แนะนำทุกข้อ (contract v1.3) · หมายเหตุ: F3 และ F6 ผู้ตรวจเสนอให้แก้โค้ด แต่ทางที่ Claude แนะนำและเจ้าของเลือกคือบันทึกเป็นข้อจำกัด
| ID | การตอบ | commit | Regression |
|----|--------|--------|------------|
| F1 Medium | เวลาซ้ำที่ใดก็ตามก่อนหน้าเป็น `duplicate_time` (เดิมเทียบแค่แท่งติดกัน) | `e52312a` | `test_a_time_repeated_after_a_step_back_is_a_duplicate` ล้มก่อน ผ่านหลัง |
| F2 | `incomplete` ตามนาทีที่ขาด ไม่ใช่จำนวน M1 | `da2ba68` | `test_a_slot_padded_by_a_duplicate_is_still_incomplete` ล้มก่อน ผ่านหลัง · golden ไม่เปลี่ยน |
| F3 | ข้อจำกัด (contract v1.3) | – | – |
| F4 | ปฏิทินที่มีวินาที → `ValueError` · `Defect`/`ValidationReport` ไม่ตรวจตอนสร้าง (ข้อจำกัด) | `61b75ed` | `test_calendar_times_with_seconds_are_refused` 2 กรณี ล้มก่อน ผ่านหลัง |
| F5 | M1 ที่ `m1_count` ≠ 1 → `ValueError` | `e9a0875` | `test_an_m1_bar_must_count_one_m1` ล้มก่อน ผ่านหลัง |
| F6 | ข้อจำกัด (contract v1.3) | – | – |
| F7 | ระบุใน PR body (`docs/proposals/CORE-005-pr-body.md`) ว่า branch มีเอกสาร CORE-004 (บันทึกหลัง merge) และ contract CORE-006 (PLAN-002) | – | – |
| F8 | test เวลาสร้าง 50,000 แท่งจริง (0.48 s) · สคริปต์ 500,000 แท่งบันทึกใน handoff | `280538b` | – |
| F9 | `.gitignore` กัน dotfile ใต้ `src/sochron/data/` | `b067cda` | `git check-ignore`: `.hidden.py`, `.secrets.py` ถูกกัน · `model.py`, `__init__.py` track · `bars.parquet` ถูกกัน |

suite หลังแก้ครบ: **2875 passed** (`e9a0875`) · block ของผู้ตรวจ: guard-bash ปฏิเสธ `git check-ignore` ที่มี path ชื่อ `.env` (ผู้ตรวจหยุด ไม่เลี่ยง)

## Review r2 (`docs/reviews/CORE-005-r2.md`, subagent `fresh-eyes-reviewer` ตรวจแคบๆ ตามที่เจ้าของเลือก)
F1, F2, F4, F5, F8, F9 ปิด (regression ล้มบน commit แม่และผ่านที่ HEAD ทุกข้อ) · F3, F6 ข้อจำกัดตรงตามที่บันทึก · F7 รอ PR body · พบ Low ใหม่ 2 ข้อ · **Ready for PR: yes**
| ID | การตอบ (เจ้าของมอบอำนาจ 2026-10-24 ~07:0x "เอา recommanded ทุกอัน") | commit | Regression |
|----|--------|--------|------------|
| F10 | ผลข้างเคียงของ F1: แท่งซ้ำที่ปิดช่องว่างจริงข้ามการตรวจช่องว่าง → ตรวจช่องว่างทุกครั้งที่เวลาเดินหน้า, `time_not_increasing` เฉพาะเวลาที่ยังไม่เคยอ่าน | `a158abf` | `test_a_repeated_bar_that_ends_a_real_gap_still_reports_the_gap` ล้มก่อน ผ่านหลัง · suite 2876 passed |
| F11 | แก้ถ้อยคำ: contract บรรทัดกติกาประกอบแท่งเป็นแบบ v1.3 และ Version เป็น v1.3 · หลักฐาน: version, ตัวเลข AC-07, F7 · handoff: เวลา build มาจากสคริปต์ scratch เดิม | (commit เอกสารนี้) | – |

## หลัง merge (2026-10-24, GitHub REST API แบบไม่ล็อกอิน)
- PR #16 `feat/CORE-005-data-bars` head `b91cff7` · เจ้าของ merge เป็น `419eee3` 09:00 +07 (02:00:29Z) · label `owner-approved-control-change` · `git diff b91cff7 origin/main` ว่าง

| Run | Event / head | ผล |
|-----|--------------|----|
| `40052145657` ci | pull_request `b91cff7` | success |
| `40052144404` control-gate | pull_request_target `b91cff7` (opened) | failure: event "opened" มาก่อน label (เหมือนทุก PR) |
| `40052149733` control-gate | pull_request_target `b91cff7` (labeled) | success |
| `40052338519` ci | push `419eee3` (main) | success |

## Delivery state
**merged** 2026-10-24 09:00 (PR #16 → `419eee3`) · CI เขียวบน PR และ main · เดิม: implemented และ verified ในเครื่อง (2876 passed at `a158abf`) · tests reviews r1–r2 ปิด · implementation review r1 ตอบครบ · review r2 (subagent) Ready for PR: yes, F10/F11 แก้แล้ว · ยังไม่ merged, ไม่ deployed
