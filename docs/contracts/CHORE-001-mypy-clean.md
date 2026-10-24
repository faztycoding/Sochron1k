# TASK CHORE-001 — ทำให้แผง Problems (mypy ใน VS Code) ไม่มี error ใน `strategy` และ `costs` โดยไม่เปลี่ยนพฤติกรรม

Version v1 · Owner เจ้าของ repository · Parent คำขอของเจ้าของในแชท Claude 2026-10-24 ~13:2x ("แก้ problem ด้วย", "เอาให้เสร็จ") · Tier **Lite** · Branch `chore/CHORE-001-mypy-clean`
Status: **approved by owner 2026-10-24** — เจ้าของสั่งให้แก้ Problems ในแชทโดยตรง และมอบอำนาจ "เอา recommanded ทุกอัน" ตั้งแต่ ~07:0x (Claude เขียน contract นี้ตามคำสั่งนั้น · veto ได้ก่อน merge)
Hypothesis (research tasks): ไม่ใช่งานวิจัย

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — ไม่แตะ CI, hooks หรือ tests ที่ล็อก

Lite เพราะแก้เฉพาะคำประกาศ type และการ narrow ชนิดในโค้ดที่ merge แล้ว ไม่เปลี่ยนค่าที่คืน ข้อผิดพลาดที่ raise หรือ API

## Goal / user outcome (Thai)
แผง Problems ของ VS Code ไม่แสดง error ของ mypy ใน `src/sochron/strategy/` และ `src/sochron/costs/` อีก (ตอนนี้มี 11 ข้อ: params.py 6, indicators.py 3, h001.py 1, costs/model.py 1) และทุก test ยังผ่านเหมือนเดิม · ส่วน `src/sochron/backtest/engine.py` (4 ข้อ) แก้ใน CORE-007 ซึ่งเป็นเจ้าของไฟล์นั้น

## Current behavior and evidence (revision)
`mcp__claude-vscode__getDiagnostics` 2026-10-24 13:2x (main `6fbed53` + branch CORE-007): Mypy error 11 ข้อใน 4 ไฟล์ข้างบน · ทุกข้อเกิดเพราะ helper ตรวจชนิด (`exact`, `require_exact`) คืน `None`/`object` mypy จึงไม่รู้ว่าค่าหลังการตรวจเป็นชนิดใด, `H001_DEFAULTS` วนด้วย str, และ `params.k * row.atr` ที่ `atr` เป็น `Decimal | None` (ตอนรันจริงไม่เป็น None เพราะ invalidation `atr_zero` ข้ามไปก่อน) · ไม่มีข้อใดเป็น bug ตอนรัน (tests 3211 ข้อผ่าน)

## Scope
- In scope: `src/sochron/strategy/params.py` (`exact` คืนค่าที่ตรวจแล้วแบบ generic, `_int_in`/`_decimal_in` ใช้ค่านั้น, `H001_DEFAULTS` วนด้วย tuple ของ `Variant`), `src/sochron/strategy/indicators.py` (`_bars` ใช้ค่าที่ `exact` คืน), `src/sochron/strategy/h001.py` (narrow `row.atr` ก่อนคูณ), `src/sochron/costs/model.py` (`require_exact` คืนค่าแบบ generic, `validate_model` ใช้ค่านั้น)
- Exclusions: ไฟล์อื่นทั้งหมด · การเปลี่ยนพฤติกรรม ข้อความ error หรือ API · การเพิ่ม mypy เป็น dependency หรือเข้า CI (งานแยกถ้าเจ้าของต้องการ)
- Allowed files: 4 ไฟล์ข้างบน, `docs/evidence/CHORE-001.md`, `PROGRESS.md`
- Must not touch: tests ทั้งหมด (รวมที่ล็อก), `pyproject.toml`, `uv.lock`, `.claude/**`, `.github/**`, `scripts/controls/**`, ไฟล์อื่นใต้ `src/`

## Inputs / outputs / errors (contract)
ไม่เปลี่ยน: ทุกฟังก์ชันคืนค่าเดิมและ raise ชนิดเดิมด้วยข้อความเดิมในทุกกรณีที่ tests ครอบ · `exact`/`require_exact` ยัง raise `TypeError` เมื่อชนิดไม่พอดี และคืน object ตัวเดิม (`is` เดียวกัน) เมื่อผ่าน · การ narrow ใช้ `typing.cast` หลังการตรวจชนิดจริง หรือการตรวจ None ที่ raise error ของโมดูล (`StrategyError`) ในทางที่ไปไม่ถึง · ห้าม `# type: ignore`

## Invariants
- tests ทั้งหมดผ่านโดยไม่แก้ test ใดๆ · `STRATEGY_VERSION` คงเดิม · import ของ strategy ยังอยู่ใน allowlist (typing มีอยู่แล้ว)

## Negative cases
ชนิดผิดทุกแบบที่ tests ล็อกของ CORE-002/004/006 ครอบยังได้ `TypeError` เดิม · `decide` ที่ ATR เป็น None ยังได้ skip `atr_zero` (ไม่ถึงบรรทัดที่ narrow)

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given branch นี้ When เปิดไฟล์ทั้ง 4 ใน VS Code แล้วดูแผง Problems (`getDiagnostics`) Then ไม่มี error ของ Mypy ในไฟล์เหล่านั้น
- AC-02 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมดเท่าก่อนแก้ skipped 0 และ CI เขียว
- AC-03 Given diff ของงานนี้ When ตรวจ Then แตะเฉพาะไฟล์ที่อนุญาต ไม่มี `type: ignore` และไม่เปลี่ยนข้อความ error หรือค่าที่คืน (ผู้ตรวจอ่าน diff)

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01 | Claude | `mcp__claude-vscode__getDiagnostics` ของ 4 ไฟล์หลังเปิดไฟล์ | L1 |
| 02 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |
| 03 | ผู้ตรวจ (subagent context ใหม่) | อ่าน diff + `bash scripts/controls/red-flags.sh origin/main` | L2 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ความเสี่ยง: เปลี่ยนพฤติกรรมโดยไม่ตั้งใจ (ปิดด้วย suite ทั้งหมดและการตรวจ diff) · CORE-008 จะแก้ `h001.py` ด้วย (`entry_blockers`) อาจต้อง merge main เข้า branch ของ CORE-008 หลังงานนี้ merge

## Plan, dependencies and unknowns (P06)
1. Understanding: ให้ mypy เห็นชนิดหลังการตรวจ โดยโค้ดตอนรันเหมือนเดิม · เข้าใจผิดที่เป็นไปได้: ใช้ `type: ignore`, เปลี่ยนข้อความ error, แก้ test
2. Files / reuse: helper เดิม `exact`, `require_exact`
3. Steps: แก้ 4 ไฟล์ → `getDiagnostics` เป็น 0 → suite → red-flags → subagent ตรวจ diff → PR
4. Risks: CORE-008 conflict ใน h001.py (merge ภายหลัง)
5. Decisions needed from the owner: none

## Authorization (filled by the owner)
เจ้าของสั่งในแชท 2026-10-24 ("แก้ problem ด้วย", "เอาให้เสร็จ") · Claude: แก้ไฟล์ที่อนุญาต, commit, push task branch (D-006) · ใช้ได้จนงานนี้ merge

## Budget
1 session · ไม่ใช้ headless session (ผู้ตรวจเป็น subagent) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR

## DoR status / missing items / next action
ครบ · next: แก้หลัง CORE-007 push

## Done scope
merge แล้ว, suite เขียวใน CI
