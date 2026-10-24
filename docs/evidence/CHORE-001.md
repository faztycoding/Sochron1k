# หลักฐาน CHORE-001: mypy (แผง Problems ของ VS Code) ไม่มี error ในแพ็กเกจ `sochron`

Contract: `docs/contracts/CHORE-001-mypy-clean.md` v1.1 (Tier Lite; เจ้าของสั่งในแชท 2026-10-24 "แก้ problem ด้วย", "เอาให้เสร็จ", "ทำให้เสร็จทั้งหมด") · Branch `chore/CHORE-001-mypy-clean` จาก main `6fbed53` · ทำใน worktree แยก `Sochron1k-wt-chore001` เพราะโฟลเดอร์หลักมี reviewer ของ CORE-007 กำลังอ่านอยู่

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 mypy ตัวเดียวกับ extension ไม่พบ error ทั้งแพ็กเกจ | **PASS** | main: **Found 32 errors in 9 files** (strategy 10, costs 1, risk 12, data.snapshot 9) → branch นี้: **Success: no issues found in 27 source files** |
| AC-02 ทั้ง suite ผ่านเท่าเดิม | **PASS ในเครื่อง** · CI รอ run ของ PR | `3093 passed` (เท่ากับ main ก่อนแก้) |
| AC-03 แตะเฉพาะไฟล์ที่อนุญาต ไม่มี `type: ignore` ไม่เปลี่ยนพฤติกรรม | **PASS ตามผู้ทำ** · review r1: F1 แก้แล้ว · รอผู้ตรวจรอบ 2 | diff 9 ไฟล์ใน src + เอกสาร |

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

mypy ไม่ได้เพิ่มเป็น dependency ของโปรเจค: ใช้ตัวที่ extension `ms-python.mypy-type-checker` 2026.6.0 ติดมาอยู่แล้ว และเขียน cache ไว้ใน scratch นอก repo (`.mypy_cache` ใต้ src ใน worktree มาจาก extension ตอนวิเคราะห์ไฟล์ และ `.gitignore` กันไว้)

## ไม่ได้ตรวจ
- CI บน Linux จนกว่า run ของ PR นี้เสร็จ · แผง Problems จริงหลัง merge (ต้องเปิดไฟล์ใน editor)

## Delivery state
implemented และ verified ในเครื่อง · review r1 ตอบแล้ว (F1 แก้, F2 ขยายขอบเขต) → re-check r2 → push → PR · ยังไม่ merged
