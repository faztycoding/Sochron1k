# หลักฐาน CHORE-001: mypy (แผง Problems ของ VS Code) ไม่มี error ในแพ็กเกจ `sochron`

Contract: `docs/contracts/CHORE-001-mypy-clean.md` v1.1 (Tier Lite; เจ้าของสั่งในแชท 2026-10-24 "แก้ problem ด้วย", "เอาให้เสร็จ", "ทำให้เสร็จทั้งหมด") · Branch `chore/CHORE-001-mypy-clean` จาก main `6fbed53` · ทำใน worktree แยก `Sochron1k-wt-chore001` เพราะโฟลเดอร์หลักมี reviewer ของ CORE-007 กำลังอ่านอยู่

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 mypy ตัวเดียวกับ extension ไม่พบ error ทั้งแพ็กเกจ | **PASS** | main: **Found 32 errors in 9 files** (strategy 10, costs 1, risk 11, data.snapshot 10 · นับต่อแพ็กเกจด้วย `grep ": error:"` ของผลเดียวกัน; เดิมเขียน 12/9 ผิด, review r2 F3) → branch นี้: **Success: no issues found in 27 source files** |
| AC-02 ทั้ง suite ผ่านเท่าเดิม | **PASS ในเครื่อง** · CI รอ run ของ PR | `3093 passed` (เท่ากับ main ก่อนแก้) |
| AC-03 แตะเฉพาะไฟล์ที่อนุญาต ไม่มี `type: ignore` ไม่เปลี่ยนพฤติกรรม | **PASS** (review r2) | diff 9 ไฟล์ใน src + เอกสาร · probe 47,433 กรณีเท่ากับ main |

หมายเหตุ: แผง Problems ของ VS Code แสดงเฉพาะไฟล์ที่เปิดอยู่ (`reportingScope` ค่าเริ่มต้น "file") จะอัปเดตเมื่อเปิดหรือบันทึกไฟล์หลังงานนี้ merge · `src/sochron/backtest/` (4 ข้อ) แก้ใน CORE-007 (`cde8945`)

## สิ่งที่แก้ (ไม่เปลี่ยนพฤติกรรม)
- helper ตรวจชนิดทั้ง 4 ตัว (`costs.require_exact`, `strategy.exact`, `risk.require_exact`, `data.snapshot.exact`) เป็น generic: คืน object ตัวเดิมด้วยชนิดที่ตรวจแล้ว (`typing.cast` หลัง `type(value) is kind`) · ข้อความ `TypeError` เดิม
- จุดที่ใช้ค่าที่ helper คืน: `validate_model`, `_int_in`, `_decimal_in`, `_bars` (อ่าน `.bar` และ `.flags` ก่อนตรวจเหมือนเดิม, review r1 F1), `validate_policy`, `require_model`, `validate_state` (รับ `object`), `_authorize`, `_side`, `_wall_minute`, `_weekly_point`
- `H001_DEFAULTS` วนด้วย `_VARIANTS: tuple[Variant, ...]` · `decide` ตรวจ `row.atr is None` ก่อนคูณ (ไปไม่ถึง: `_invalid` รายงาน `atr_zero` ก่อน)

## Checks (2026-10-24, +07, Windows 11, Git Bash, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| `mcp__claude-vscode__getDiagnostics` (โฟลเดอร์หลัก) | Mypy error 11 ข้อใน strategy/costs + 4 ข้อใน backtest (เฉพาะไฟล์ที่เปิดอยู่) | main `6fbed53` + CORE-007 | 13:2x |
| mypy ของ extension บน main: `PYTHONPATH=<extension>/bundled/libs MYPYPATH=src uv run --offline python -m mypy --cache-dir <scratch> --explicit-package-bases -p sochron.strategy -p sochron.costs` | Found 11 errors in 4 files | `6fbed53` | 13:3x |
| คำสั่งเดียวกันหลังแก้รอบแรก | Success: no issues found in 8 source files | `2827fd1` | 13:30 |
| review r1 (subagent) | F1 Low (ลำดับการอ่าน attribute ใน `_bars`), F2 Low (ประโยคในหลักฐานนี้ผิด: ยังมี 21 ข้อใน risk/data.snapshot) · ทั้งแพ็กเกจบน main: 32 errors ใน 9 ไฟล์ | `2827fd1` | 13:3x–13:43 |
| แก้ F1 → probe item ที่ `.bar` ผิดและ `.flags` raise | main และ branch: `RuntimeError` + log `['bar', 'flags']` เท่ากัน | `aee9e67` | 13:4x |
| ขยายขอบเขต (v1.1) → mypy ของ extension `-p sochron` (ทั้งแพ็กเกจ) | **Success: no issues found in 27 source files** | `f58d3f9` | 13:47 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | **3093 passed** | `f58d3f9` | 13:47:22 |
| review r2 (subagent, `docs/reviews/CHORE-001-r2.md`) | F1, F2 ปิด · probe 47,433 กรณีบนสำเนา main และ branch: ผล, error และลำดับการอ่านเท่ากัน (รวม `check_entry` 30,720 กรณี, `size_position` 4,200, halt 300 ลำดับ) · F3 Low: ตัวเลขแยกแพ็กเกจในหลักฐานนี้ผิด | `7a61b20` | 13:51–14:04 |
| แก้ F3 → นับ error ต่อแพ็กเกจบนสำเนา main | costs 1, data 10, risk 11, strategy 10 (รวม 32) | หลัง `7a61b20` | 14:1x |

mypy ไม่ได้เพิ่มเป็น dependency ของโปรเจค: ใช้ตัวที่ extension `ms-python.mypy-type-checker` 2026.6.0 ติดมาอยู่แล้ว และเขียน cache ไว้ใน scratch นอก repo (`.mypy_cache` ใต้ src ใน worktree มาจาก extension ตอนวิเคราะห์ไฟล์ และ `.gitignore` กันไว้)

## ไม่ได้ตรวจ
- CI บน Linux จนกว่า run ของ PR นี้เสร็จ · แผง Problems จริงหลัง merge (ต้องเปิดไฟล์ใน editor)

## หลัง merge (2026-10-24, GitHub REST API แบบไม่ล็อกอิน)
- PR #19 `chore/CHORE-001-mypy-clean` · Claude push ถึง `fc7f3f0` · เจ้าของกด "Update branch" → `f920c07` (รวม main ที่มี CORE-007 แล้ว ไม่มี conflict) · merge เป็น `3af8333` 14:56 +07 (07:56:23Z) · มี label `owner-approved-control-change` (ไม่จำเป็น เพราะ check-locked-paths ผ่าน แต่ไม่มีผลเสีย)
- ตรวจซ้ำบน main `3af8333` ใน worktree แยก: **3212 passed** · mypy ของ extension `-p sochron` (รวม backtest) → **no issues found in 31 source files** (14:59)

| Run | Event / head | ผล |
|-----|--------------|----|
| `40073682417` ci | pull_request `fc7f3f0` | success |
| `40073680550` control-gate | pull_request_target `fc7f3f0` | success (ไม่มีไฟล์ล็อก) |
| `40073694469` control-gate | pull_request_target `fc7f3f0` (labeled) | success |
| `40073892062` ci | pull_request `f920c07` | success |
| `40073892251` control-gate | pull_request_target `f920c07` | success |
| `40076092321` ci | push `3af8333` (main) | success |

## Delivery state
**merged** 2026-10-24 14:56 (PR #19 → `3af8333`) · CI เขียวบน PR และ main · เดิม: implemented และ verified ในเครื่อง · review r1 ตอบแล้ว (F1 แก้, F2 ขยายขอบเขต) · review r2: F1, F2 ปิด, F3 (ตัวเลขพิมพ์ผิด) แก้แล้ว · push → PR · ยังไม่ merged
