# TASK CORE-001 — timebase: โมดูลเวลาเดียวของระบบ (raw MT5 ↔ UTC, sessions แบบ New York, DST, วันไทย)

Version v1 · Owner เจ้าของ repository · Parent SPEC J2/J3 (ทุกเส้นทางต้องแปลงเวลาผ่านโมดูลเดียว) · `docs/architecture.md` ข้อ 8 แถว `timebase` และข้อ 13a แถว "R1 time/data" · Tier **Standard** · Branch `feat/CORE-001-timebase`
Status: approved by owner 2026-10-21 (acceptance 7 ข้อและแผน อนุมัติในแชท Claude ราว 08:2x) · ยังรอ: การอนุมัติ dependency ระดับโปรเจกต์และ `pyproject.toml`/`uv.lock` ฉบับแรกหลังผล admission (D-012)
Hypothesis (research tasks): ไม่ใช่งานวิจัย แต่ให้บริการ H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`, commit `0c392a9`) ซึ่งกำหนดหน้าต่างเข้าไม้ 03:00–15:59 New York และแท่ง M15 ที่สร้างจาก M1

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no — โค้ด pure ไม่แตะสิทธิ์ ไม่เชื่อมต่ออะไร
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no — ไม่มีข้อมูลตลาด ไม่มีข้อมูลบัญชี
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no
- Q6 changes controls (CI, hooks, permissions, policy): no — งานนี้ไม่แก้ `.github`, hooks หรือ policy · Python CI job เป็น control change แยกภายหลัง · tests ที่ล็อก (`tests/acceptance`, `tests/golden`, `tests/architecture`) เขียนโดย Codex และเข้า repo ผ่าน patch ใน `docs/proposals/` ที่ Claude apply ตาม D-006 ตามขั้นตอนปกติของ test author

เป็น Standard เพราะเป็นโค้ด Python ชิ้นแรกของโปรเจกต์ มี dependency แรก (lockfile แรก) และเป็น invariant ด้านเวลาที่ผิดแล้วเกิด look-ahead ทั้งระบบ (Handbook §15)

## Goal / user outcome (Thai)
มีโมดูลเดียวชื่อ `sochron.timebase` ที่ทุกส่วนของระบบ (data, strategy, backtest, broker, execution) ใช้แปลงเวลา โดย:
- แปลงเวลาดิบจาก MT5 (จำนวนเต็มวินาทีและมิลลิวินาที) ↔ UTC ด้วย **กฎที่มีเวอร์ชันและระบุ server, symbol, terminal build และช่วงหลักฐาน** (จาก SPIKE-001: `Exness-MT5Trial14` offset 0 วินาที, กลไกยัง UNKNOWN) และ**ปฏิเสธ** server ที่ไม่มีกฎ ไม่เดา offset เอง
- บอกว่าเวลาหนึ่งอยู่ในหน้าต่างเข้าไม้ของ H001 (03:00–15:59 เวลา New York) หรือไม่ โดยถูกต้องข้ามช่วงเปลี่ยน DST ของสหรัฐ
- บอก "วันเทรดแบบไทย" (วันที่ตามเวลา Asia/Bangkok) สำหรับ baseline การหยุดรายวันใน SPEC ข้อ 6
- จัดแท่ง M1 เข้าแท่ง timeframe ใหญ่กว่า (เช่น M15) ได้ตรงกับ MT5 (ขอบแท่งอยู่ที่ UTC เพราะ offset 0)
- จำแนกผลการวัด offset ระหว่าง tick กับนาฬิกาเครื่อง (ok / shifted / unknown) แบบเดียวกับ SPIKE-001 โดย**ไม่**ปรับกฎเองโดยอัตโนมัติ
- ไม่เรียกนาฬิกาของเครื่องเอง ไม่ import `MetaTrader5` และทุก datetime ต้องเป็น timezone-aware

## Current behavior and evidence (revision)
ที่ main `90278b4`: ไม่มีโค้ดแอป ไม่มี `pyproject.toml` ไม่มี dependency ของโปรเจกต์ · กฎเวลาที่วัดได้อยู่ใน `docs/evidence/SPIKE-001.md` (12 ตัวอย่าง offset −3.8 ถึง +0.87 วินาที, M1 open ตรงต้นนาที UTC, เวลาพักตลาดเลื่อนตาม US DST) · โค้ดจำแนก offset ต้นแบบอยู่ใน `spikes/SPIKE-001/probe.py` (`classify_offsets`) ซึ่งเป็นโค้ดทิ้งได้และห้าม import จาก `src`

## Scope
- In scope: แพ็กเกจ `sochron.timebase` ตาม API ด้านล่าง · `pyproject.toml` + `uv.lock` ฉบับแรกของโปรเจกต์ (หลัง dependency admission และเจ้าของอนุมัติ) · unit tests ของผู้ทำ · acceptance, golden และ architecture tests โดย Codex · หลักฐานใน `docs/evidence/CORE-001.md` · handoff
- Exclusions: การอ่านข้อมูลจาก MT5 หรือไฟล์ใดๆ · เวลาทำการ/พักตลาดของ `XAUUSDm` (AC-03 ของ SPIKE-001 ยัง UNKNOWN ด้าน timezone จึงไม่ใส่ใน timebase รุ่นนี้) · timeframe W1/MN1 · Python job ใน CI (control change แยก) · โมดูล `costs`, `risk`, `data`
- Allowed files/modules: `pyproject.toml`, `uv.lock`, `src/sochron/__init__.py`, `src/sochron/py.typed`, `src/sochron/core/__init__.py` (ว่างหรือชนิดข้อมูลที่ timebase ต้องใช้เท่านั้น), `src/sochron/timebase/**`, `tests/__init__.py`, `tests/conftest.py`, `tests/unit/timebase/**`, `docs/evidence/CORE-001.md`, `docs/handoff/CORE-001.md`, `PROGRESS.md` · โดย Codex ผ่าน patch: `tests/acceptance/CORE-001/**`, `tests/golden/CORE-001/**`, `tests/architecture/**`
- Must not touch: `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`, `docs/hypotheses/**`, `research/**`

## Inputs / outputs / errors (contract)
ชื่อด้านล่างเป็นสัญญาสำหรับ acceptance tests (เปลี่ยนไม่ได้โดยผู้ทำ) · ทุกฟังก์ชันเป็น pure: ไม่มี I/O, ไม่อ่านนาฬิกา, ไม่มี global state ที่เปลี่ยนได้

```text
sochron.timebase
  TimeRule (frozen dataclass): server: str, symbol: str, terminal_build: int, offset_seconds: int,
      evidence_from: date, evidence_to: date, evidence_ref: str, version: str
  RULES: Mapping[str, TimeRule]        # key = server; รุ่นแรกมีรายการเดียว:
      "Exness-MT5Trial14": symbol "XAUUSDm", build 6274, offset_seconds 0,
      evidence 2026-10-20..2026-10-21, evidence_ref "docs/evidence/SPIKE-001.md", version "1"
  rule_for(server: str) -> TimeRule                      # UnknownTimeRule ถ้าไม่มี
  to_utc(raw_seconds: int, rule: TimeRule, msc: int | None = None) -> datetime   # tz = UTC
  to_raw(dt: datetime, rule: TimeRule) -> int            # inverse ของ to_utc (วินาที)
  to_zone(dt: datetime, zone: str) -> datetime           # zone เช่น "America/New_York", "Asia/Bangkok"
  EntryWindow (frozen dataclass): zone: str, start: time, end_inclusive: time
  NY_ENTRY_WINDOW = EntryWindow("America/New_York", 03:00, 15:59)
  in_entry_window(dt: datetime, window: EntryWindow = NY_ENTRY_WINDOW) -> bool
  bangkok_date(dt: datetime) -> date
  bar_open(raw_seconds: int, timeframe_minutes: int, rule: TimeRule) -> int   # raw seconds ของเวลาเปิดแท่ง
  TIMEFRAMES_MINUTES = {1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720, 1440}
  OffsetClass (frozen dataclass): kind: "ok" | "shifted" | "unknown", hours: int | None, samples: int
  classify_offset(offsets_seconds: Sequence[float], tolerance_seconds: float = 120.0) -> OffsetClass
  errors (ทั้งหมดสืบจาก TimebaseError(ValueError)):
      UnknownTimeRule · NaiveDatetime · RawTimeOutOfRange · RawTimeMismatch · BadTimeframe
```

- ช่วง raw ที่รับ: `946684800 ≤ raw_seconds < 4102444800` (2000-01-01 ถึงก่อน 2100-01-01) · ถ้าให้ `msc` มาด้วย ต้อง `msc // 1000 == raw_seconds` ไม่งั้น `RawTimeMismatch`
- `to_utc(raw, rule) = datetime.fromtimestamp(raw − rule.offset_seconds, tz=UTC)` (บวกมิลลิวินาทีจาก `msc` ถ้ามี) · `to_raw` คือ inverse ทิ้งเศษมิลลิวินาที
- `in_entry_window`: แปลง `dt` ไปยัง `window.zone` แล้วเทียบ `start ≤ local.time() ≤ end_inclusive` ที่ความละเอียดนาที (วินาทีไม่นับ) · ขอบ: 03:00:00 อยู่ใน, 02:59:59 ไม่อยู่, 15:59:59 อยู่ใน, 16:00:00 ไม่อยู่
- `bar_open(raw, tf, rule)`: `utc = raw − offset`; `open_utc = utc − (utc mod (tf × 60))`; คืน `open_utc + offset` · timeframe นอก `TIMEFRAMES_MINUTES` → `BadTimeframe`
- `classify_offset`: ว่าง → unknown (samples 0) · ทุกค่า |x| ≤ tolerance → ok · ทุกค่าใกล้จำนวนชั่วโมงเต็มเดียวกัน (|x − h×3600| ≤ tolerance, h เท่ากันทุกค่า, h ≠ 0) → shifted พร้อม hours = h · อื่นๆ → unknown
- ทุกฟังก์ชันที่รับ `datetime` ปฏิเสธ naive datetime ด้วย `NaiveDatetime`

## Invariants
- ไม่มี `datetime.now()`, `time.time()`, `datetime.utcnow()` หรือการอ่านนาฬิกาใดๆ ใน `src/sochron/timebase` (now เป็น argument เสมอ)
- ไม่มี `import MetaTrader5` และไม่มี I/O (ไฟล์, เครือข่าย, env) ใน `src/sochron/timebase` และ `src/sochron/core`
- เวลาดิบเป็น `int` และไม่ถูกแก้ · ทุกการแปลงอ้าง `TimeRule` ที่ระบุ server/symbol/build/version · `RULES` เปลี่ยนได้เฉพาะผ่าน contract ใหม่พร้อมหลักฐานใหม่
- `classify_offset` รายงานอย่างเดียว ห้ามมีโค้ดใดแก้ `offset_seconds` จากผลการวัด (13a: ห้ามปรับ offset อัตโนมัติ)
- `to_raw(to_utc(x)) == x` สำหรับทุก x ในช่วงที่รับ · `to_utc(to_raw(dt)) == dt` ที่ความละเอียดวินาที
- timezone มาจาก `zoneinfo` ของ stdlib พร้อมแพ็กเกจ `tzdata` (Windows ไม่มีฐานข้อมูล tz) · ไม่ hard-code กฎ DST เอง
- ไม่มี `.skip`, `xfail` หรือ test ที่อ่อนลงใน tests ที่ล็อก · ไม่มี dependency นอกเหนือจากที่ผ่าน admission

## Negative cases
- server ที่ไม่มีกฎ (`rule_for("Other-Server")`) → `UnknownTimeRule` ไม่คืนค่า default
- naive datetime ในทุกฟังก์ชันที่รับ datetime → `NaiveDatetime`
- raw นอกช่วง (เช่น 0, −1, 4102444800) → `RawTimeOutOfRange` · `msc` ไม่ตรงวินาที → `RawTimeMismatch`
- DST/session boundary: วันเปลี่ยน DST ของสหรัฐปี 2026 ทั้งสองวัน (08 มี.ค. และ 01 พ.ย.) หน้าต่างในหน่วย UTC เลื่อน 1 ชั่วโมง · ขอบหน้าต่างทั้งสี่จุด (02:59:59 / 03:00:00 / 15:59:59 / 16:00:00 NY)
- วันที่ไทยข้ามเที่ยงคืน: 2026-10-20 16:59:59 UTC → 2026-10-20 (BKK 23:59:59) และ 17:00:00 UTC → 2026-10-21
- bar_open กับเวลาที่ไม่ตรงต้นนาที (เวลาของ tick) และกับ timeframe ที่ไม่รองรับ (7, 1441) → `BadTimeframe`
- classify_offset: ตัวอย่างว่าง, ค่าปนกัน (0.5, 7200, 30), ค่าเท่ากับ tolerance พอดี (อยู่ใน ok), ค่า shift ที่ไม่ใช่ชั่วโมงเต็ม (เช่น 1800) → unknown

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given ค่าเวลาดิบจาก SPIKE-001 รอบ 3 (`raw_seconds = 1792525992`, `msc = 1792525992035`) และกฎ `Exness-MT5Trial14` v1, When เรียก `to_utc` แล้ว `to_raw` กลับ, Then ได้ `2026-10-20 19:53:12.035+00:00` และ `to_raw` คืน `1792525992` เท่าเดิมทุก byte · ทำซ้ำกับค่าดิบที่ Codex สุ่มเลือกในช่วงที่รับอีกอย่างน้อย 20 ค่า ต้องกลับมาเท่าเดิมทั้งหมด
- AC-02 Given เวลา UTC ในตารางที่ Codex คำนวณด้วยมือรอบวันเปลี่ยน DST ของสหรัฐปี 2026 (อย่างน้อย 8 จุด: วันก่อนและวันหลัง 08 มี.ค. และ 01 พ.ย. ที่ขอบ 03:00 และ 16:00 New York) When เรียก `in_entry_window`, Then คำตอบตรงกับเวลา New York ในตาราง เช่น `2026-03-08 07:30 UTC` (03:30 EDT) = อยู่ใน แต่ `2026-03-07 07:30 UTC` (02:30 EST) = ไม่อยู่ และขอบทั้งสี่จุดถูกต้อง
- AC-03 Given เวลา UTC `2026-10-20 16:59:59` และ `2026-10-20 17:00:00`, When เรียก `bangkok_date`, Then ได้ `2026-10-20` และ `2026-10-21` ตามลำดับ (และ `to_zone(..., "Asia/Bangkok")` ให้เวลา 23:59:59 กับ 00:00:00)
- AC-04 Given เวลาเปิดแท่ง M1 ดิบ 15 แท่งติดกันตั้งแต่ `1792525980` (19:53:00 UTC) และ tick ที่ `1792525992` When เรียก `bar_open(raw, 15, rule)` Then ทุกค่าตั้งแต่ 19:45:00 ถึง 19:59:59 ได้เวลาเปิดแท่ง `1792525500` (19:45:00 UTC) และค่าที่ 20:00:00 ได้ `1792526400` · timeframe 7 → `BadTimeframe`
- AC-05 Given server ที่ไม่มีกฎ, naive datetime, raw นอกช่วง และ `msc` ไม่ตรง When เรียกฟังก์ชันที่เกี่ยวข้อง Then แต่ละกรณี raise error ชนิดที่ระบุ ไม่คืนค่าใดๆ และไม่มีกรณีไหน "เดา" ค่า default
- AC-06 Given ชุด offset ตามตาราง (ทั้งหมดใน ±120 วินาที / ทั้งหมดใกล้ +7200 / ปนกัน / ว่าง / shift 1800) When เรียก `classify_offset` Then ได้ `ok` / `shifted` hours = 2 / `unknown` / `unknown` samples 0 / `unknown` ตามลำดับ และโมดูลไม่มีเส้นทางใดเปลี่ยน `TimeRule`
- AC-07 Given โค้ดใน `src/sochron/timebase` และ `src/sochron/core` When รัน architecture test (AST) และ `bash scripts/controls/red-flags.sh main` Then ไม่พบ `MetaTrader5`, `datetime.now`, `utcnow`, `time.time` หรือ I/O ใน sources · import ของ timebase มีแค่ stdlib และ `sochron.core` · red-flag กลุ่ม secret และกลุ่ม order/account mutation ว่าง · `uv run pytest tests -q` ผ่านทั้งหมด skipped 0

## Verification per AC
| AC | Verifier (test author / CI / owner demo) | Command or procedure | Evidence level |
|----|------------------------------------------|----------------------|----------------|
| 01–06 | Codex: acceptance + golden tests (ตารางคำนวณมือ) ใน `tests/acceptance/CORE-001`, `tests/golden/CORE-001` · Claude: unit tests | `uv run pytest tests -q` บน Windows (Python 3.12 ผ่าน uv) | L2 · L3 เมื่อมี Python CI job (งานแยก) |
| 07 | Codex: `tests/architecture/test_imports.py` (AST) · สคริปต์ควบคุม | `uv run pytest tests/architecture -q` · `bash scripts/controls/red-flags.sh main` · `node scripts/controls/check-locked-paths.mjs main` | L2 |
| ทั้งหมด | เจ้าของ | อ่าน `docs/evidence/CORE-001.md` (ผลรัน, commit, เวลา) และตาราง golden ของ Codex | เจ้าของตรวจ |

## Risk, data and external side effects
- ไม่มีผลภายนอก ไม่เชื่อมต่อ terminal ไม่ใช้ข้อมูลตลาด
- ผลข้างเคียงบนเครื่อง: `uv` สร้าง `.venv/` (gitignored) และติดตั้งแพ็กเกจที่ผ่าน admission เท่านั้น
- ความเสี่ยงหลัก: กฎเวลาถูก hard-code ผิด หรือ DST ผิด → look-ahead ทั้งระบบ · ลดด้วย golden tables ที่ Codex คำนวณด้วยมือและ property round-trip
- ความเสี่ยงรอง: ชื่อ API ใน contract นี้ไม่พอใช้ในโมดูลถัดไป → เพิ่มได้ใน contract ใหม่ ห้ามเปลี่ยนชื่อเดิมโดยไม่มี contract

## Plan, dependencies and unknowns (P06)
1. Understanding (3 lines) and likely misunderstandings: โมดูลนี้คือ "ความจริงเรื่องเวลา" ของทั้งระบบ แปลงเวลาดิบด้วยกฎที่มีหลักฐาน และตอบคำถามเรื่องหน้าต่างเวลาแบบ New York กับวันไทย โดยไม่อ่านนาฬิกาเอง · เข้าใจผิดที่เป็นไปได้: (ก) คิดว่า "MT5 = UTC" ถูกพิสูจน์แล้ว — ไม่ใช่ เราเข้ารหัส "offset 0 ที่วัดได้บน server นี้" (AC-04 ของ SPIKE UNKNOWN) จึงต้องมี server ใน rule และปฏิเสธ server อื่น (ข) ใช้เวลา UTC คงที่เป็นหน้าต่างเทรด — ไม่ใช่ หน้าต่างเป็นเวลา New York และเลื่อนในหน่วย UTC ตาม DST (ค) ใช้วันไทยกับ session — ไม่ใช่ วันไทยใช้กับ baseline การหยุดรายวันเท่านั้น
2. Files to touch / what is reused: ใหม่ทั้งหมดใน `src/sochron/timebase/` (`__init__.py`, `rules.py`, `convert.py`, `sessions.py`, `offset.py`) · reuse ตรรกะ `classify_offsets` และตัวอย่างค่าจริงจาก `spikes/SPIKE-001` (คัดลอกแนวคิด ไม่ import) · `zoneinfo` + `tzdata` · `pyproject.toml` ใหม่ (requires-python `>=3.12,<3.13`, dependencies `tzdata==2026.5`, dev `pytest==9.1.1`) + `uv.lock`
3. Steps, each with its check:
   1. เจ้าของอนุมัติ acceptance นี้ → Status เปลี่ยนเป็น approved · commit contract
   2. Codex `$dependency-admission` ระดับโปรเจกต์สำหรับ `tzdata` และ `pytest` (+ transitives) โดยใช้หลักฐาน SPIKE-001 → ร่าง D-012 → เจ้าของอนุมัติ → Claude สร้าง `pyproject.toml` และ `uv lock` (ask-first: build/lockfile) → check: `uv run python -c "import zoneinfo; zoneinfo.ZoneInfo('America/New_York')"` ผ่านบน Windows
   3. Codex `$write-acceptance-tests CORE-001`: acceptance (AC-01–06), golden tables (DST, Bangkok, bar_open, offset), architecture test → ส่งเป็น `docs/proposals/CORE-001-tests.patch` พร้อม hash → Claude apply ตาม D-006, ตรวจ hash, session ใหม่ตรวจ patch, commit → check: tests ทั้งหมด **FAIL** ก่อนมีโค้ด (red)
   4. Claude implement `sochron.timebase` ทีละฟังก์ชันพร้อม unit tests → check: `uv run pytest tests -q` เขียวทีละ AC commit ทีละขั้น
   5. Claude เขียน `docs/evidence/CORE-001.md` + handoff → Codex `$cross-agent-review` (read-only) → Claude `/fix-findings` → re-review
   6. เจ้าของเปิด PR (แตะ `tests/acceptance|golden|architecture` ซึ่งล็อก จึงต้องติด label `owner-approved-control-change`) → CI control-plane เขียว → merge
4. Risks and negative cases to test: ตามหัวข้อ Negative cases ทั้งหมด · เพิ่ม property test round-trip (`to_raw(to_utc(x)) == x`) ถ้า Codex ใช้ skill `property-based-testing` (SPIKE FIRST ที่เจ้าของอนุมัติ) ซึ่งต้องขอ admission ของไลบรารี `hypothesis` แยก
5. Decisions needed from the owner: (ก) อนุมัติ acceptance 7 ข้อ (ข) อนุมัติ dependency ระดับโปรเจกต์หลัง admission: `tzdata==2026.5` (runtime), `pytest==9.1.1` + transitives (dev) และการสร้าง `pyproject.toml`/`uv.lock` ฉบับแรก (ค) ยอมรับ prefix `CORE-` สำหรับ contract ของส่วน pure (timebase, costs, risk) เพราะชื่อ branch ต้องผ่าน guard (F26) (ง) ถ้า Codex ขอใช้ `hypothesis` สำหรับ property tests ให้ตัดสินตอน admission

## Authorization (filled by the owner)
- Claude Code / สร้าง `pyproject.toml` + `uv.lock` และติดตั้ง dependency ที่ผ่าน admission ลง `.venv` ของเครื่องนี้ / repo นี้ / จนกว่า CORE-001 จะ done — รอเจ้าของกรอก
- Codex / เขียน tests ที่ล็อกเป็น patch ใน `docs/proposals/` / `tests/acceptance/CORE-001`, `tests/golden/CORE-001`, `tests/architecture` / งานนี้ — รอเจ้าของกรอก
- ไม่มีการเชื่อม terminal หรือบัญชีใดๆ ในงานนี้

## Budget
2 sessions · 3 attempts ต่อ test ที่ล้มโดยไม่มีหลักฐานใหม่ แล้วหยุดขอ second opinion · Codex headless ไม่เกิน 5 รัน (admission, tests, review, re-review, สำรอง) · ไม่มีค่าใช้จ่ายเงิน

## Recovery, compensation and checkpoint
ลบ `src/sochron/timebase`, tests ของ CORE-001, `pyproject.toml`, `uv.lock`, `.venv/` แล้วทิ้ง branch ได้ทั้งก้อน ไม่มีผลข้างเคียงนอกเครื่อง · checkpoint ใน PROGRESS.md หลังทุกขั้นที่ผ่าน check

## DoR status / missing items / next action
- ครบ: การอนุมัติ acceptance จากเจ้าของ (2026-10-21)
- ขาด: dependency admission ระดับโปรเจกต์ (D-012) · tests จาก Codex (patch) · สภาพแวดล้อม uv
- next action: Codex ทำ admission และ tests → เจ้าของอนุมัติ D-012 → Claude สร้าง environment, apply patch ของ tests ตาม D-006 แล้วลงมือ

## Done scope
implementation (ทดสอบผ่านบนเครื่อง, review ปิด, merge แล้ว) · ยังไม่รวม Python CI job
