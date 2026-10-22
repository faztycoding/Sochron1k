# TASK OPS-001 — ให้ CI รัน Python test suite บน Linux ทุก PR

Version v1 (ร่าง 2026-10-22 23:1x) · Owner เจ้าของ repository · Parent PROGRESS "Not done yet": Python test job ใน CI · Handbook ch.21 (pinned actions) · Tier **High** · Branch `chore/OPS-001-python-ci`
Status: draft (รอเจ้าของอนุมัติ)
Hypothesis (research tasks): ไม่ใช่งานวิจัย

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no — job ใหม่ใช้ token `contents: read` เท่าเดิม
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: **yes** — แก้ `.github/workflows/ci.yml` (path ที่ล็อก) และเพิ่มเครื่องมือใน CI (uv) ซึ่งเป็น dependency ใหม่ของ CI

High เพราะ Q6: เจ้าของอนุมัติแผน, patch ของไฟล์ล็อกเขียนโดยผู้รับบท test author (ไม่ใช่ผู้ทำ) ส่งเป็น patch ใน `docs/proposals/` ตาม D-006, fresh-session review, PR ต้องติด label

## Goal / user outcome (Thai)
ทุก PR และทุก push เข้า `main` มี job ใหม่ชื่อ `python-tests` ที่รัน `uv run pytest tests` แบบเดียวกับที่รันในเครื่อง บน Linux ถ้ามี test ล้ม job จะแดง เจ้าของจึงเห็นผล test จาก GitHub ได้เลยโดยไม่ต้องเชื่อผลจากเครื่องของ agent อย่างเดียว · ใช้ uv และ Python รุ่นที่ตรึงไว้ ใช้ `uv.lock` เดิมแบบห้ามแก้ (frozen) ไม่เปิดสิทธิ์เขียนใดๆ

## Current behavior and evidence (revision)
`ci.yml` มี job เดียว `control-plane` (node `test-controls.mjs` + `red-flags.sh`) · ไม่มี Python ใน CI · ผล pytest ทั้งหมดของ CORE-001..003 (784 passed) มาจาก Windows ในเครื่อง · `test-controls.mjs` F1 ตรวจว่า `control-gate.yml` ไม่ติดตั้ง/รันโค้ดของ PR และ `ci.yml` ไม่ใช่ด่าน locked-path (ต้องยังจริงหลังงานนี้)

## Scope
- In scope: job `python-tests` ใน `.github/workflows/ci.yml` · บันทึก dependency admission ของวิธีติดตั้ง uv ใน CI (DECISIONS + `docs/tooling/registry.md` ถ้าเป็น action ใหม่) · หลักฐาน `docs/evidence/OPS-001.md` · handoff · PROGRESS
- Exclusions: `control-gate.yml` · `pyproject.toml`, `uv.lock` (ไม่แก้, ไม่ regenerate) · การตั้ง required status check ใน GitHub settings (เจ้าของทำเอง ถ้าต้องการ) · Windows runner (งานแยกถ้าต้องการ)
- Allowed files: `.github/workflows/ci.yml` (ผ่าน patch D-006 เท่านั้น), `DECISIONS.md`, `docs/tooling/registry.md`, `docs/evidence/OPS-001.md`, `docs/handoff/OPS-001.md`, `docs/proposals/OPS-001-*.patch`, `PROGRESS.md`
- Must not touch: `src/**`, `tests/**`, `scripts/controls/**`, `.claude/**`, `AGENTS.md`, `CLAUDE.md`

## Inputs / outputs / errors (contract)
- job `python-tests`: `runs-on: ubuntu-24.04`, `timeout-minutes` ≤ 15, permissions สืบจาก workflow (`contents: read`)
- ขั้นตอน: checkout (action เดิม pinned SHA, `persist-credentials: false`) → ติดตั้ง uv รุ่นตรึง (วิธีตามที่เจ้าของเลือก ดู Plan ข้อ 5) → Python 3.12 → `uv sync --frozen` (หรือ `--locked`) → `uv run --frozen pytest tests -q -p no:cacheprovider -rs`
- job ล้มเมื่อ: test ล้มหรือ error, lockfile ไม่ตรงกับ `pyproject.toml`, หรือมี test ถูก skip (AGENTS.md: skipped ไม่นับว่าผ่าน)

## Invariants
- ไม่มี `continue-on-error`, `|| true` หรือการกลืน exit code ในขั้น test
- action ภายนอกทุกตัวตรึงด้วย full commit SHA · ไม่มี `curl … | sh` · ไม่มี secret และไม่มีสิทธิ์เขียน
- `control-gate.yml` ไม่เปลี่ยน · `test-controls.mjs` ผ่านเหมือนเดิม (F1 ยังจริง)
- ไม่ regenerate lockfile และไม่เพิ่ม dependency ของโปรเจกต์

## Negative cases
- lockfile ไม่ตรง (`uv sync --frozen` ล้ม) → job แดง · test ล้มหนึ่งข้อ → job แดง · test ถูก skip → job แดง · uv รุ่นอื่นถูกติดตั้ง → มองเห็นได้จาก log และ step ตรึงรุ่น

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given PR ที่เปิดเข้า `main`, When CI รัน, Then มี job `python-tests` บน `ubuntu-24.04` ที่รัน suite เต็มด้วยคำสั่งเดียวกับในเครื่อง และ log แสดงจำนวน passed เท่ากับที่รันในเครื่องบน commit เดียวกัน, skipped 0
- AC-02 Given job ใน `ci.yml`, When อ่าน YAML, Then uv และ Python ตรึงรุ่นแน่นอน, action ภายนอกตรึงด้วย full SHA, ไม่มี `curl | sh`, ไม่มี `continue-on-error`/`|| true` ในขั้น test, permissions ยังเป็น `contents: read`
- AC-03 Given `pyproject.toml` กับ `uv.lock` ที่ไม่ตรงกัน (จำลองใน scratch), When รันคำสั่ง sync ของ job, Then คำสั่งล้ม (non-zero) แทนการแก้ lockfile
- AC-04 Given test ที่ล้มหรือถูก skip (จำลองใน scratch ด้วยคำสั่งเดียวกับ job), When รัน, Then exit code ไม่เป็น 0 จึงทำให้ job แดง
- AC-05 Given control plane เดิม, When รัน `node scripts/controls/test-controls.mjs` และดู `control-gate.yml`, Then ผ่านทั้งหมดและ `control-gate.yml` ไม่เปลี่ยน
- AC-06 Given admission ของวิธีติดตั้ง uv, When ตรวจ `DECISIONS.md` และ registry, Then มีบันทึกที่มา รุ่น และเหตุผล ที่เจ้าของอนุมัติก่อน patch ถูก apply

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01 | CI | ลิงก์ run ของ PR + จำนวน passed เทียบกับ `uv run --offline pytest tests -q -p no:cacheprovider` ในเครื่อง | L3 |
| 02, 05 | fresh-session reviewer + control tests | อ่าน YAML, `node scripts/controls/test-controls.mjs`, `git diff origin/main -- .github/workflows/control-gate.yml` ว่าง | L2 |
| 03, 04 | test author (scratch) | รันคำสั่งของ job ใน scratch กับ lockfile/test ที่จงใจทำให้ผิด แล้วบันทึก exit code | L2 |
| 06 | เจ้าของ | อนุมัติ admission | เจ้าของตรวจ |

## Risk, data and external side effects
- ไม่มีผลภายนอกนอก GitHub Actions · ดาวน์โหลด package ตาม `uv.lock` จาก PyPI ใน runner (hash ตรวจโดย uv)
- ความเสี่ยง: supply chain ของเครื่องมือ (uv/action) → ตรึงรุ่นและ SHA, admission · test ที่ผ่านบน Windows อาจล้มบน Linux (เวลา, path, encoding) → สืบหาสาเหตุ ห้ามทำให้ test อ่อนลง (ถ้าต้องแก้ src เป็นงาน FIX แยก)
- test เวลาของ CORE-003 (< 1.000 s ต่อการปฏิเสธ) บน runner ที่ช้ากว่า: ค่าที่วัดในเครื่องช้าสุด 0.000379 s จึงมี margin มาก

## Plan, dependencies and unknowns (P06)
1. Understanding: เพิ่ม job ทดสอบ Python ใน workflow ที่รันโค้ดของ PR อยู่แล้ว (`ci.yml`) ไม่ใช่ด่านล็อก · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่าแก้ `control-gate.yml` — ไม่ใช่ (ข) คิดว่าทำให้เป็น required check อัตโนมัติ — ไม่ใช่ เจ้าของตั้งใน settings เอง (ค) คิดว่าอัปเดต lockfile ได้ — ไม่ได้
2. Files / reuse: `ci.yml` (เพิ่ม job), checkout action เดิมและ pin เดิม · admission ใน DECISIONS
3. Steps: (1) เจ้าของอนุมัติ contract และเลือกวิธีติดตั้ง uv → (2) admission record → (3) ผู้รับบท test author เขียน `docs/proposals/OPS-001-ci.patch` พร้อม hash และหลักฐาน scratch ของ AC-03/04 → (4) Claude apply ตาม D-006 + ตรวจ hash + fresh-session review → commit → push → (5) PR: CI run แรกเป็นหลักฐาน AC-01 → เจ้าของติด label, merge
4. Risks: ดู Risk · ถ้า Linux run ล้มเพราะโค้ด ให้หยุดและเปิดงาน FIX แยก ไม่ merge OPS-001 จนกว่า suite เขียว
5. Decisions needed from the owner:
   - (ก) วิธีติดตั้ง uv ใน CI: **(1) action `astral-sh/setup-uv` ตรึง full SHA + `version: 0.13.0` (แนะนำ: ผู้ผลิตเดียวกับ uv ที่ใช้อยู่แล้ว, มี cache)** · (2) `pipx install uv==0.13.0` จาก PyPI (ไม่มี action ใหม่ แต่ไม่ตรวจ hash) · (3) `pip install --require-hashes` ใน venv ชั่วคราว (ตรวจ hash แต่ขั้นตอนยาวกว่า)
   - (ข) Python ใน CI: uv-managed 3.12.15 ให้ตรงเครื่อง (แนะนำ) หรือ Python 3.12 ของ runner
   - (ค) ต้องการให้ `python-tests` เป็น required check หรือไม่ (ตั้งใน GitHub settings โดยเจ้าของหลัง merge)

## Authorization (filled by the owner)
- (รอเจ้าของ) Claude: contract, admission record, apply patch ตาม D-006, evidence, handoff, PROGRESS, push task branch · ผู้รับบท test author (Codex หรือ Claude session ใหม่ตามการสลับบทบาท): เขียน patch ของ `ci.yml`

## Budget
1 session · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่ · headless session ไม่เกิน 4 (patch author, fresh review, implementation review, สำรอง) · ไม่มีค่าใช้จ่ายเงิน (GitHub Actions ฟรีสำหรับ repo นี้ตามปริมาณปัจจุบัน)

## Recovery, compensation and checkpoint
revert PR หรือลบ job `python-tests` · ไม่มีผลข้างเคียงนอก CI · checkpoint ใน PROGRESS หลังแต่ละขั้น

## DoR status / missing items / next action
ครบ: `uv.lock`, คำสั่งที่ verified ใน AGENTS.md · ขาด: การอนุมัติของเจ้าของ, ทางเลือก (ก)–(ค), ผู้รับบท test author (Codex หมดโควตาถึง 2026-10-28 19:41) · next: เจ้าของอนุมัติ

## Done scope
merge แล้วและ CI ของ `main` แสดง `python-tests` เขียว
