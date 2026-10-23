# TASK FIX-001 — ด่านตรวจ architecture จับนาฬิกา, สุ่ม, process และ console ที่ยังหลุด

Version v1 (ร่าง 2026-10-22 23:1x) · Owner เจ้าของ repository · Parent `docs/reviews/CORE-003-tests-r1.md` F5 (architecture checker gap) · AGENTS.md "One strategy implementation, a pure function … no I/O, clock" · Tier **High** · Branch `fix/FIX-001-architecture-side-effects`
Status: **approved by owner 2026-10-22 23:4x** (acceptance และแผน · ผู้เขียน patch และผู้ตรวจ = Claude session ใหม่ตามการสลับบทบาทระหว่าง Codex หมดโควตา)
Hypothesis (research tasks): ไม่ใช่งานวิจัย

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: **yes** — แก้ `tests/architecture/test_imports.py` (test ที่ล็อก ซึ่งเป็นด่านของโมดูล pure)

High เพราะ Q6: patch เขียนโดยผู้รับบท test author ส่งตาม D-006, fresh-session review, PR ติด label · ไม่มีโค้ดใน `src/` ให้ผู้ทำแก้ (ถ้าด่านใหม่จับโค้ดเดิมได้ ให้หยุดและเปิดงาน FIX แยก)

## Goal / user outcome (Thai)
ด่าน architecture ปัจจุบันจับ `time.time()`, `datetime.now()`, `open`, `print`, `random` ฯลฯ ได้ แต่ยังไม่จับวิธีอ่านนาฬิกา สุ่ม เรียก process หรือเขียน console แบบอื่น ถ้ามีคนเผลอใส่ไว้ในโมดูล pure (`timebase`, `core`, `costs`, `risk`) เช่น `time.localtime()`, `os.urandom()`, `uuid.uuid4()`, `subprocess.run(...)`, `sys.stdout.write(...)` test จะยังผ่าน งานนี้ปิดช่องนั้น เพื่อให้ "โมดูล pure ไม่มีนาฬิกา, ไม่สุ่ม, ไม่มี I/O" เป็นจริงตามที่ test บอก

## Current behavior and evidence (revision)
`tests/architecture/test_imports.py` (247 บรรทัด): `_inspect_source` มีรายการ `clocks` (`time.time`, `time.monotonic`, `time.perf_counter`, `datetime.now` ฯลฯ) และ `direct_io` (`open`, `os.open`, `os.getenv`, `print`, `input`, `urllib.request.urlopen` ฯลฯ) · costs/risk เพิ่ม float และ random · review tests-r1 F5 พบว่า `time.localtime()`, `os.urandom()`, `uuid.uuid4()`, `subprocess`, `sys.stdout.write` ไม่ถูกจับ · โค้ดใน `src/` ตอนนี้ไม่ใช้สิ่งเหล่านี้ (ตรวจด้วยตาโดย security review CORE-003)

## Scope
- In scope: ขยายการตรวจใน `tests/architecture/test_imports.py` ให้ครอบทุกโมดูล pure (`sochron.timebase`, `sochron.core`, `sochron.costs`, `sochron.risk`) · test ของตัวตรวจเอง (ป้อน source สังเคราะห์ให้ฟังก์ชันตรวจ แล้วต้องรายงาน) · หลักฐาน · handoff · PROGRESS
- Exclusions: แก้ `src/**` · โมดูลที่ไม่ pure ในอนาคต (`broker.mt5`, `data.acquire`) · red-flags.sh
- Allowed files: `tests/architecture/test_imports.py` (ผ่าน patch D-006 เท่านั้น), `docs/evidence/FIX-001.md`, `docs/handoff/FIX-001.md`, `docs/proposals/FIX-001-*.patch`, `PROGRESS.md`
- Must not touch: `src/**`, `tests/acceptance/**`, `tests/golden/**`, `.github/**`, `scripts/controls/**`, `.claude/**`

## Inputs / outputs / errors (contract)
รายการที่ต้องถูกรายงานเมื่อพบในโมดูล pure (เรียกตรง, ผ่าน alias `import x as y`, หรือ `from x import y`):
- นาฬิกาเพิ่มเติม: `time.localtime`, `time.gmtime`, `time.ctime`, `time.asctime`, `time.strftime`, `time.mktime` ที่อ่านเวลาปัจจุบัน (เรียกแบบไม่มี argument หรือใช้กับ `localtime()`), `time.clock_gettime`, `time.clock_gettime_ns`, `time.thread_time`, `time.thread_time_ns`
- สุ่ม: `os.urandom`, `os.getrandom`, import ของ `secrets` และ `uuid` (หรืออย่างน้อย `uuid.uuid1`, `uuid.uuid4`), `random.SystemRandom`
- process: import ของ `subprocess`, `os.system`, `os.popen`, `os.exec*`, `os.spawn*`, `os.fork`, `os.kill`, `multiprocessing`
- console/stream: `sys.stdout`, `sys.stderr`, `sys.stdin` (อ้างถึงใดๆ), `sys.__stdout__`/`__stderr__`
- network: import ของ `socket`, `http`, `ssl` (ส่วนที่ยังไม่ครอบ)
รายการตรวจเดิมทั้งหมดยังอยู่ · ผลที่รายงานรวมเลขบรรทัด

## Invariants
- ทุก assertion เดิมของ timebase, core, costs, risk ยังมีความหมายเท่าเดิม (ไม่ลบ ไม่ผ่อน) · ไม่มี skip/xfail
- ไม่มี false positive บนโค้ดปัจจุบันของ `main`
- โค้ดที่ถูกต้องยังผ่าน: `datetime.date(2026, 1, 1)`, `datetime.timezone.utc`, `zoneinfo.ZoneInfo(...)`, `time` ที่ใช้เป็นชื่อตัวแปร/attribute ที่ไม่ใช่ module (ถ้าตัวตรวจแยกได้)

## Negative cases
alias (`import time as t; t.localtime()`), `from os import urandom`, `from sys import stdout`, `getattr(time, "localtime")()` (บันทึกว่าตรวจไม่ได้แบบ static ถ้าตรวจไม่ได้ ไม่ต้องอ้างว่าจับ), import ใน function body, import แบบ `import uuid` เฉยๆ

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given source สังเคราะห์ที่มีแต่ละรายการในหัวข้อ contract (เรียกตรง, alias, from-import), When ป้อนให้ตัวตรวจของแต่ละโมดูล pure, Then ทุกรายการถูกรายงานพร้อมเลขบรรทัด
- AC-02 Given source สังเคราะห์ที่ถูกต้อง (date literal, timezone, ZoneInfo, ชื่อตัวแปร `time` ที่ไม่ใช่ module), When ตรวจ, Then ไม่มีรายงาน
- AC-03 Given โค้ดจริงใน `src/sochron/{timebase,core,costs,risk}` ที่ `main`, When รัน `uv run --offline pytest tests/architecture -q -p no:cacheprovider`, Then ผ่าน
- AC-04 Given assertion เดิมทั้งหมดของไฟล์, When เทียบ diff, Then ไม่มีข้อใดถูกลบหรือผ่อน (AST เทียบ assert เดิม)
- AC-05 Given ทั้ง suite, When รัน `uv run --offline pytest tests -q -p no:cacheprovider`, Then ผ่านทั้งหมด skipped 0

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–02 | test author + fresh-session reviewer | test ใหม่ในไฟล์ + mutation: ใส่แต่ละรายการลงสำเนาโมดูลใน scratch แล้วรันตัวตรวจ | L2 |
| 03, 05 | Claude + CI (หลัง OPS-001) | คำสั่งในตาราง | L2/L3 |
| 04 | fresh-session reviewer | AST เทียบ assert เดิม | L2 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยง: false positive ทำให้โค้ดที่ถูกต้องเขียนไม่ได้ → AC-02 · ตัวตรวจแบบ static จับ dynamic access (`getattr`, `__import__`) ไม่ได้ทั้งหมด → บันทึกเป็นข้อจำกัด ไม่อ้างเกินจริง

## Plan, dependencies and unknowns (P06)
1. Understanding: ขยายรายการที่ห้ามใน test architecture ที่ล็อก โดยไม่แตะโค้ด · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่าต้องแก้ src — ไม่ (ข) คิดว่าจับ dynamic access ได้ครบ — ไม่ได้ บันทึกเป็นข้อจำกัด
2. Files / reuse: `_qualified`, `_inspect_source`, `_inspect_costs_source`, `_inspect_risk_source` เดิม
3. Steps: (1) เจ้าของอนุมัติ → (2) ผู้รับบท test author เขียน `docs/proposals/FIX-001-architecture.patch` + hash + mutation evidence → (3) Claude apply ตาม D-006 + ตรวจ hash + fresh-session review → commit → push → PR (label) → merge
4. Risks: ดูข้างบน
5. Decisions needed from the owner: ไม่มี นอกจากผู้รับบท test author ระหว่างที่ Codex หมดโควตา

## Authorization (filled by the owner)
- เจ้าของอนุมัติ 2026-10-22 23:4x · ผู้รับบท test author: เขียน patch ของ `tests/architecture/test_imports.py` · Claude: apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1 session · headless session ไม่เกิน 3 (patch author, fresh review, สำรอง) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง

## DoR status / missing items / next action
ครบ: finding tests-r1 F5, ไฟล์ test ปัจจุบัน · ขาด: การอนุมัติ, ผู้รับบท test author · next: เจ้าของอนุมัติ

## Done scope
merge แล้ว, suite เขียวใน CI
