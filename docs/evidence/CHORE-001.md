# หลักฐาน CHORE-001: แผง Problems (mypy) ไม่มี error ใน `strategy` และ `costs`

Contract: `docs/contracts/CHORE-001-mypy-clean.md` v1 (Tier Lite; เจ้าของสั่งในแชท 2026-10-24 "แก้ problem ด้วย", "เอาให้เสร็จ") · Branch `chore/CHORE-001-mypy-clean` จาก main `6fbed53` · ทำใน worktree แยก `Sochron1k-wt-chore001` เพราะโฟลเดอร์หลักมี reviewer ของ CORE-007 กำลังอ่านอยู่

## สรุปสำหรับเจ้าของ
| AC | ผล | หลักฐาน |
|----|----|---------|
| AC-01 ไม่มี error ของ mypy ใน 4 ไฟล์ | **PASS** | mypy 1.15.0 ตัวเดียวกับที่ extension ของ VS Code ใช้: ก่อนแก้ 11 errors ใน 4 ไฟล์ (ตรงกับแผง Problems ทุกข้อ) → หลังแก้ "Success: no issues found in 8 source files" |
| AC-02 ทั้ง suite ผ่านเท่าเดิม | **PASS ในเครื่อง** · CI รอ run ของ PR | `3093 passed` (เท่ากับ main ก่อนแก้) |
| AC-03 แตะเฉพาะไฟล์ที่อนุญาต ไม่มี `type: ignore` ไม่เปลี่ยนพฤติกรรม | **PASS ตามผู้ทำ** · รอผู้ตรวจ | diff 4 ไฟล์ใน src + เอกสาร |

## สิ่งที่แก้ (ไม่เปลี่ยนพฤติกรรม)
- `costs/model.py`: `require_exact` เป็น generic คืน object ตัวเดิมด้วยชนิดที่ตรวจแล้ว (`typing.cast` หลังการตรวจ `type(value) is kind`) · `validate_model` ส่งค่าที่ได้ต่อให้ `_check_model`
- `strategy/params.py`: `exact` เป็น generic แบบเดียวกัน · `_int_in`/`_decimal_in` ใช้ค่าที่ `exact` คืน · `H001_DEFAULTS` วนด้วย `_VARIANTS: tuple[Variant, ...]`
- `strategy/indicators.py`: `_bars` ใช้ค่าที่ `exact` คืนสำหรับ `.bar` และ `.flags`
- `strategy/h001.py`: ตรวจ `row.atr is None` ก่อนคูณ (ทางนี้ไปไม่ถึงจริง เพราะ `_invalid` รายงาน `atr_zero` ไปก่อน) โดย raise `StrategyError`
- ข้อความ error, ลำดับการตรวจ, ค่าที่คืน และ `STRATEGY_VERSION` เหมือนเดิม

## Checks (2026-10-24, +07, Windows 11, Git Bash, CPython 3.12.15)
| คำสั่ง | ผล | commit | เวลา |
|--------|----|--------|------|
| `mcp__claude-vscode__getDiagnostics` (โฟลเดอร์หลัก) | Mypy error 11 ข้อใน strategy/costs + 4 ข้อใน backtest (CORE-007) | main `6fbed53` + CORE-007 | 13:2x |
| mypy ของ extension บนโค้ดเดิม: `PYTHONPATH=<extension>/bundled/libs MYPYPATH=src uv run --offline python -m mypy --cache-dir <scratch> --explicit-package-bases -p sochron.strategy -p sochron.costs` | **Found 11 errors in 4 files** (ตรงกับแผง Problems) | `6fbed53` | 13:3x |
| คำสั่งเดียวกันบน worktree หลังแก้ | **Success: no issues found in 8 source files** | ก่อน commit ของการแก้ | 13:30 |
| `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` (worktree) | **3093 passed** | ก่อน commit ของการแก้ | 13:30:19 |

mypy ไม่ได้เพิ่มเป็น dependency ของโปรเจค: ใช้ตัวที่ extension `ms-python.mypy-type-checker` 2026.6.0 ติดมาอยู่แล้ว และเขียน cache ไว้ใน scratch นอก repo · แผง Problems ใน VS Code จะอัปเดตเมื่อไฟล์ถูกเปิดหรือบันทึกใน editor

## ไม่ได้ตรวจ
- CI บน Linux จนกว่า run ของ PR นี้เสร็จ · `backtest/engine.py` แก้ใน CORE-007 ไม่ใช่งานนี้ · ส่วนอื่นของ src ไม่มี error ของ mypy ในแผง Problems ณ เวลาที่ตรวจ

## Delivery state
implemented และ verified ในเครื่อง · รอผู้ตรวจ (subagent) → push → PR · ยังไม่ merged
