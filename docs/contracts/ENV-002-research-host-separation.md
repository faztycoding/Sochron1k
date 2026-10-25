# TASK ENV-002 — แยก research host ออกจาก terminal และ holdout พร้อม synthetic excluded-period sentinel

Version v1.5 (v1 ร่าง 2026-10-25 → v1.1 ตอบ `docs/reviews/ENV-contracts-r1.md`: research identity และ break-it test (F1), OneDrive (F3), ความหมายของ "ผ่าน data" และงานที่ส่งต่อ (F7), คำสั่งที่รันได้จริง (F8), นิยามที่ผู้เขียน tests ต้องใช้ (F9), ขอบเขตของ excluded_period (F11), การค้น sentinel ที่ไม่อ่านไฟล์ลับ (F12), terminal ที่ติดตั้งที่อื่น (F13), ความสอดคล้อง (F20) → v1.2 ตอบ `docs/reviews/ENV-contracts-r2.md`: การประเมิน holdout เป็นงานส่งต่อ (F7), ที่อยู่ของตัวสร้างแท่งปลอม (F9), เอกสารที่แก้ตอนบันทึก ENV-1 ผ่าน (F20), โฟลเดอร์รับไฟล์ของ D-021 (F29), shell folder/ขอบเขตของ hash/token (F30), ความเสี่ยงของ RDP ที่เปิดอยู่ (F32) → v1.3 ตอบ `docs/reviews/ENV-contracts-r3.md`: ขอบเขตการค้น token และไฟล์ cloud-only (F36), ขั้นตอนโหลด `synthetic.py` (F37), `ResearchRoots` ชุดเดียวของ R1 (F43 a), ป้ายเวอร์ชัน (F44) → v1.4 ตอบ `docs/reviews/ENV-contracts-r4.md` (ทุกข้อ Low): ไฟล์ cloud-only ใน repo/data dirs (F49), จุดที่ tests แทนและการดักการเปิดไฟล์ (F50) → v1.5 ตอบ `docs/reviews/ENV-contracts-r5.md` (Low): ไฟล์ที่อยู่ทั้งใต้ data dirs และ search_dirs (F51)) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 6.1 ("ด่านก่อน SLICE-R1"), 9, 13a · D-017, D-019, D-020, D-021 (proposed) · Tier **High** · Branch `feat/ENV-002-research-host-separation`
Status: **draft v1.5** (Claude ร่าง 2026-10-25 · review r5: พร้อมให้อนุมัติ, F49/F50 ปิด · ข้อ Low F51 ของ r5 แก้ใน v1.5 ให้ผู้ตรวจรอบถัดไปตรวจซ้ำ · รอเจ้าของอนุมัติ: High) · เริ่มได้หลัง ENV-001 และ SPIKE-002 ผ่าน
Hypothesis (research tasks): ไม่ใช่งานวิจัย

ด่าน ENV-1: ENV-001 → SPIKE-002 → **ENV-002**

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: **yes** — งานนี้คือขอบเขตระหว่าง research identity กับ holdout
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no — sentinel เป็นข้อมูลปลอม
- Q4 schema change or deletion of real data: **yes** — เจ้าของถอน MT5 terminal และลบโฟลเดอร์ข้อมูลของ terminal บนเครื่องตัวเอง
- Q5 hard-to-reverse external effect: no (ติดตั้งใหม่ได้)
- Q6 changes controls: no สำหรับ hooks/CI · เพิ่มกฎใน `tests/architecture` (ล็อก) ผ่าน patch ของผู้เขียน tests ตาม D-006

**High** ตาม Q1, Q4

## นิยาม
- **research identity** = บัญชีผู้ใช้ Windows ของเจ้าของบนเครื่องเจ้าของ (research host) รวมทุกโปรเซสที่ agent (Claude Code, Codex) เปิด · การเข้า VPS ผ่าน RDP แบบ interactive ของเจ้าของเป็น **ประตูของคน**: รหัสผ่าน RDP ต้องไม่ถูกบันทึกบนเครื่องนี้ และ **ขณะที่หน้าต่าง RDP เปิดอยู่ โปรเซสของ research identity มองเห็นและส่ง input เข้าหน้าต่างนั้นได้** (โปรเซสผู้ใช้เดียวกัน, session เดียวกัน, integrity ระดับเดียวกัน) จึงต้องเปิด RDP เฉพาะเมื่อไม่มี session ของ agent รันอยู่ (decision (ค))
- **ช่วงที่ตัดออก** = ข้อมูลตลาดตั้งแต่ `HOLDOUT_CUTOFF_UTC` (2025-01-01 00:00 UTC) · `period_end_utc` เป็นจุดสิ้นสุดแบบไม่รวม ความหมายเดียวกับ `research.Dataset`
- **"อ่านหรือดึงไม่ได้ ทั้งโดยตรงและผ่าน data" ที่ ENV-1** (architecture ข้อ 6.1) = (1) โดยตรง: research identity ไม่มีไฟล์ช่วงที่ตัดออก ไม่มี share/drive ไป VPS ไม่มีพอร์ตอื่นนอกจาก RDP และไม่มี credential ของ VPS (break-it test, AC-03) (2) ดึงจากโบรกเกอร์: ไม่มี terminal และ `MetaTrader5` บนเครื่องนี้ (3) ผ่านโค้ด: `research` ปฏิเสธแท่งของช่วงนั้น (`HoldoutRefused`) และ `research`/`backtest`/`strategy` import `data.acquire`, `broker`, `app` ไม่ได้ · loader ของ R1 ที่ยังไม่มีเป็นงานส่งต่อ (หัวข้อ "งานที่ส่งต่อ")

## Goal / user outcome (Thai)
เครื่องเจ้าของเป็น research host ตามข้อ 6.1 ที่พิสูจน์ได้:
- ไม่มี MT5 terminal (ทั้งแบบติดตั้งและแบบ portable), โฟลเดอร์ `%APPDATA%\MetaQuotes` หรือแพ็กเกจ `MetaTrader5` ที่ import ได้
- ไม่มี holdout หรือไฟล์ข้อมูลตลาดของช่วงที่ตัดออกในพื้นที่ที่ research ใช้ ไม่มี drive/share ที่ต่อไป VPS
- เจ้าของทดสอบจากเครื่องตัวเองแล้วว่าเข้า VPS ได้ทาง RDP แบบ interactive เท่านั้น และไม่มี credential ของ VPS บันทึกไว้
- `sochron.app.envcheck` ที่ R1 ต้องผ่านก่อนทุกครั้ง และ synthetic sentinel บน VPS ที่หาไม่เจอบนเครื่องนี้

## Current behavior and evidence (revision)
`main` `a11bff7` · เครื่องเจ้าของมี `C:\Program Files\MetaTrader 5` และ `%APPDATA%\MetaQuotes` (ตรวจแค่การมีอยู่) · `MetaTrader5` ไม่อยู่ใน `pyproject.toml` · โปรเจกต์เป็น virtual project (`package = false`): `python -m sochron…` ต้องตั้ง `PYTHONPATH=src` (pytest ใช้ `pythonpath = ["src"]` เอง) · `research` ปฏิเสธแท่งตั้งแต่ cutoff ก่อนการตรวจอื่น (`inputs.py` holdout guard) และต้องการ `core.Bar` พอดี · `data.snapshot` ยังไม่มีตัวอ่าน snapshot (SLICE-R1, D-020)

## Scope
- In scope: `src/sochron/app/__init__.py`, `src/sochron/app/envcheck.py` · `scripts/env/make_sentinel.py` (stdlib เท่านั้น, รันบน VPS) · unit tests `tests/unit/app/**` · runbook `docs/runbooks/ENV-002-research-host.md` · `docs/evidence/ENV-002-sentinel.json` (ค่าของ sentinel ที่ commit: ชื่อ, ขนาด, SHA-256, token, vault path, เวลาสร้าง) · หลักฐาน · โดยผู้เขียน tests ผ่าน patch D-006: `tests/acceptance/ENV-002/**`, `tests/architecture/**`
- Exclusions: รูปแบบ snapshot/manifest เต็มและ loader ของ R1 (SLICE-R1) · การดึงข้อมูล การตัดและย้าย holdout (D-021, contract ของ acquisition host) · `data.acquire`, `broker` · แก้ `research`, `backtest`, `strategy`, `data`
- Allowed files/modules: ข้างบน + `docs/evidence/ENV-002.md`, `docs/handoff/ENV-002.md`, `PROGRESS.md` · หลัง ENV-1 ผ่าน (ตอนบันทึก "ENV-1 ผ่าน": วันที่, commit ของ 3 งาน) แก้ได้เฉพาะ: `docs/architecture.md` ข้อ 6.1 ("ระยะนี้" และ bullet ด่าน ENV-1 ตาม D-021 ข้อ 1), ข้อ 7 ประโยคขอบเขต research/holdout ("ระยะนี้ที่ยังใช้เครื่องเดียว…"), ข้อ 9 แถว holdout, และแถว Q-08 ของ `SPEC.md` (ชี้ไป D-021) · การแก้บรรทัด Phase ใน `AGENTS.md` เป็น patch D-006 แยกให้เจ้าของ
- Must not touch: `src/sochron/{core,timebase,data,strategy,costs,risk,backtest,research}/**`, `pyproject.toml`, `uv.lock`, `.github/**`, `.claude/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`

## Inputs / outputs / errors (contract)
```text
sochron.app.envcheck   (stdlib · Windows-only API ผ่าน ctypes/winreg ภายใน collect เท่านั้น ให้ import และทดสอบได้บน Linux)
  Item (frozen): name, status "PASS"|"FAIL"|"UNKNOWN", detail
  Report (frozen): role "research", items: tuple[Item, ...], verdict      # มี FAIL → FAIL · ไม่มี FAIL แต่มี UNKNOWN → UNKNOWN · ทุกข้อ PASS → PASS
  Sentinel (frozen): name, size (bytes), sha256 (64 hex), token (32 hex), vault_path, created_utc    # อ่านจาก JSON ที่ commit
  ResearchRoots (frozen): repo, data_dirs (ค่าตั้งต้น = (<repo>/data,) + --data-dir เพิ่มเติม), program_files, appdata, user_profile,
      search_dirs (Downloads, Desktop, Documents จาก shell folder จริง + %OneDrive%, %OneDriveConsumer%, %OneDriveCommercial% ถ้ามี)
  Facts (frozen): ผลอ่านจาก OS ที่ evaluate ใช้ (เส้นทางที่มีอยู่, รายการ drive ระยะไกล, Uninstall entries, โปรเซส, find_spec)
  collect(roots) -> Facts          # Windows: ctypes เฉพาะ GetDriveTypeW, WNetOpenEnumW/WNetEnumResourceW/WNetCloseEnum (RESOURCE_CONNECTED),
                                   #   CreateToolhelp32Snapshot/Process32FirstW/Process32NextW/CloseHandle, shell32.SHGetKnownFolderPath + ole32.CoTaskMemFree
                                   #   (Downloads, Desktop, Documents ที่ OneDrive อาจย้าย) · winreg อ่านอย่างเดียวเฉพาะ Uninstall keys (HKLM, HKCU, WOW6432Node)
                                   #   · os.listdrives, os.environ (APPDATA, USERPROFILE, ProgramFiles*, OneDrive*) · ไม่มี subprocess, socket, http · ไม่เขียน ไม่ลบไฟล์
  evaluate(facts, roots, sentinel | None) -> Report     # อ่าน manifest JSON และไฟล์ที่ต้องค้น sentinel ตามกฎข้างล่าง
  research_host_report(*, roots=None, sentinel=None) -> Report       # = evaluate(collect(roots), roots, sentinel)
  require_research_host(*, roots=None, sentinel=None) -> Report      # ResearchHostError(ValueError) เมื่อ verdict ไม่ใช่ PASS พร้อมชื่อ item
  CLI (Git Bash):   PYTHONPATH=src uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json [--data-dir <path> …]
      (PowerShell): $env:PYTHONPATH="src"; uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json
      พิมพ์รายงาน + "RESEARCH HOST: PASS|FAIL|UNKNOWN" · exit 0 เฉพาะ PASS
Items:
  terminal_install  FAIL เมื่อพบอย่างใดอย่างหนึ่ง: โฟลเดอร์ `Program Files*\MetaTrader*` · `terminal64.exe` ในระดับ 1–2 ของ Program Files
                    · Uninstall entry (HKLM, HKCU, WOW6432Node) ที่ DisplayName มี "MetaTrader" · โปรเซส `terminal64.exe` ที่รันอยู่
                    · `terminal64.exe` ใต้ user profile ลึกไม่เกิน 3 ระดับ (ข้าม .git, .venv, node_modules)
  terminal_data     FAIL เมื่อ `%APPDATA%\MetaQuotes` มีอยู่ (ตรวจการมีอยู่เท่านั้น ห้าม list หรืออ่านข้างใน)
  mt5_package       FAIL เมื่อ `importlib.util.find_spec("MetaTrader5")` ไม่ใช่ None
  holdout_dir       FAIL เมื่อมีโฟลเดอร์ชื่อ holdout (ไม่สนตัวพิมพ์) ใต้ repo หรือ data dirs
  excluded_period   ใน data dirs: ทุกไฟล์ `*.parquet`, `*.csv`, `*.hcc`, `*.hc`, `*.tkc` ต้องมี manifest — `<ชื่อไฟล์>.manifest.json` ข้างกัน
                    หรือ `manifest.json` ในโฟลเดอร์เดียวกันที่มี {"files": [{"name", "sha256"}, …], "period_end_utc": "%Y-%m-%dT%H:%M:%SZ"}
                    และไฟล์นั้นอยู่ใน "files" · period_end_utc ≤ cutoff = PASS · > cutoff = FAIL · ไม่มี manifest = FAIL · manifest เสีย
                    (JSON ผิด, ขาด field, เวลาผิดรูปแบบ) = FAIL · อ่านไม่ได้เพราะสิทธิ์ = UNKNOWN
                    นอก data dirs แต่ใต้ repo: เฉพาะ `*.hcc`, `*.hc`, `*.tkc` (cache ของ MT5) = FAIL · CSV/parquet อื่นใต้ repo ไม่ตรวจที่นี่
                    (การตรวจ hash และเวลาจริงของไฟล์เป็นงานของ loader ใน SLICE-R1)
  network_shares    FAIL เมื่อมี drive ชนิด DRIVE_REMOTE หรือ resource ที่ต่ออยู่จาก WNetOpenEnumW
  sentinel          ไม่ให้ Sentinel = UNKNOWN · FAIL เมื่อพบอย่างใดอย่างหนึ่ง:
                    (1) vault_path มีอยู่บนเครื่องนี้
                    (2) ใน repo, data dirs และ search_dirs: ไฟล์ชื่อตรง sentinel (ชื่อเท่านั้น ไม่เปิด)
                    (3) ใน repo, data dirs และ search_dirs: ไฟล์ `.json` ขนาดเท่า size พอดีที่ SHA-256 ตรง
                    (4) ใน repo และ data dirs เท่านั้น (ที่เดียวที่โค้ดวิจัยอ่าน, หัวข้อ "งานที่ส่งต่อ"): ไฟล์ข้อความ (`.json`, `.csv`, `.txt`, `.md`)
                        ที่มี token
                    ไฟล์ cloud-only (`os.stat(...).st_file_attributes` มี FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS 0x00400000 หรือ
                    FILE_ATTRIBUTE_RECALL_ON_OPEN 0x00040000) ไม่ถูกเปิด เพราะการเปิดทำให้ OneDrive ดาวน์โหลด:
                      ใน repo และ data dirs: ไฟล์ cloud-only ที่นามสกุลอยู่ในชุดที่ค้น (`.json`, `.csv`, `.txt`, `.md`) = UNKNOWN ไม่ว่าขนาดเท่าไร
                      ใน search_dirs: เฉพาะไฟล์ cloud-only `.json` ที่ขนาดเท่า size พอดี = UNKNOWN (ไฟล์ cloud-only อื่นข้ามไป)
                      ไฟล์ที่อยู่ทั้งใต้ repo/data dirs และใต้ search_dirs (เช่น data dir ในโฟลเดอร์ OneDrive) ใช้กฎของ repo/data dirs
                    ตัวตรวจคือฟังก์ชันระดับโมดูล `envcheck.is_cloud_only(path) -> bool` (บน Linux ไม่มี attribute นี้ = False) ที่ tests แทนได้
                    ห้ามเปิดเด็ดขาด: `.env` และ `.env.*` (รวม `.env.example`), `*.key`, `*.pem`, `*.pfx`, `*.rdp`, ทุกอย่างใต้โฟลเดอร์ที่มี
                    `terminal64.exe` และใต้ `%APPDATA%\MetaQuotes`
                    · ข้ามไฟล์เดียว: `docs/evidence/ENV-002-sentinel.json` · กฎของ repo: มีเพียงไฟล์นั้นที่เก็บ token · หลักฐาน, handoff, review
                    และ PROGRESS อ้าง sentinel ด้วยชื่อ, ขนาด และ SHA-256 เท่านั้น (ไฟล์อื่นที่มี token = FAIL ตามที่ตั้งใจ)
  ค่าที่อ่านไม่ได้ (สิทธิ์, API ล้ม) = UNKNOWN ของ item นั้น

scripts/env/make_sentinel.py   (stdlib เท่านั้น · เจ้าของรันบน VPS ในโฟลเดอร์ vault)
  เขียน `SENTINEL-ENV002-<token 8 ตัวแรก>.json` = {"synthetic": true, "purpose": "ENV-002 sentinel", "token": <32 hex จาก secrets.token_hex>,
      "bars": [M1 ปลอม 60 แท่งตั้งแต่ 2025-01-02T00:00:00Z: time_utc, open/high/low/close เป็นข้อความ, spread]}
  พิมพ์ JSON ของค่าที่ต้อง commit: name, size, sha256, token, vault_path, created_utc (เจ้าของคัดลอกเป็นข้อความ ไม่คัดลอกไฟล์)

ตัวสร้างแท่งปลอม (ข้อมูลปลอมอยู่ใต้ tests/ เท่านั้นตาม AGENTS.md):
  tests/acceptance/ENV-002/synthetic.py (ผู้เขียน tests, ล็อก): synthetic_bars(start: datetime, count: int) -> list[core.Bar]
      # M1 ติดกัน, time_raw/time_utc สอดคล้องกันตาม timebase.rule_for("Exness-MT5Trial14"), ราคาคงที่ที่ผ่านการตรวจ OHLC
  tests ทั้งสองที่ (acceptance และ tests/unit/app/) โหลดไฟล์นั้นตามขั้นนี้ (repo ไม่มี conftest และ pythonpath มีแค่ src):
      spec = importlib.util.spec_from_file_location("synthetic", <repo>/tests/acceptance/ENV-002/synthetic.py)
      module = importlib.util.module_from_spec(spec); sys.modules["synthetic"] = module; spec.loader.exec_module(module)
  · `make_sentinel.py` เขียนแท่งปลอมของตัวเองด้วย stdlib (ไม่ import sochron)
```

## งานที่ส่งต่อ (acceptance ที่ contract ถัดไปต้องยก)
- **SLICE-R1:** loader ของ snapshot (ใน `app`, D-020) ปฏิเสธแท่งของ sentinel และ manifest ที่จบหลัง cutoff ก่อนส่งให้ `research` · จุดเริ่มของ R1 เรียก `require_research_host(sentinel=<docs/evidence/ENV-002-sentinel.json>)` และบันทึก verdict คู่กับการรัน · ไม่ PASS = ไม่รัน
- **SLICE-R1 (ต่อ):** จุดเริ่มของ R1 สร้าง `ResearchRoots` ชุดเดียว แล้วส่งชุดนั้นให้ทั้ง `require_research_host(roots=…, sentinel=…)` และ loader · loader อ่าน snapshot จาก `roots.data_dirs` เท่านั้น (ค่าตั้งต้น `<repo>/data` ซึ่งรวมโฟลเดอร์รับไฟล์ `<repo>/data/transfer/` ของ D-021) จึงอ่านได้เฉพาะโฟลเดอร์ที่ `excluded_period` ตรวจแล้วในรอบเดียวกัน
- **Acquisition host (หลัง ENV-1):** `data.acquire` และการประเมิน holdout รันเมื่อ `host_report.py --role acquisition` เป็น PASS เท่านั้น · select บน holdout ใช้รายการที่ freeze (D-014, D-017) · ลำดับการตัด holdout และช่องทางส่ง snapshot ตาม D-021 · **การประเมิน holdout ต้องมีการแก้ guard ของ `research` (ตอนนี้ปฏิเสธทุกแท่งตั้งแต่ cutoff โดยไม่มี role หรือข้อยกเว้น) ผ่าน contract และ review ของตัวเอง:** ENV-1 ไม่ได้ให้สิทธิ์นี้

## Invariants
- ตัวตรวจอ่านเฉพาะ: การมีอยู่ของ path, รายการ drive/resource/โปรเซส/Uninstall entry จาก OS, manifest JSON ใน data dirs และไฟล์ที่ต้องค้น sentinel ตามกฎ · ไม่อ่าน .env, Credential Manager, `cmdkey`, ไฟล์ .rdp หรือเนื้อหาโฟลเดอร์ของ terminal (AGENTS.md) · ไม่เปิดไฟล์ cloud-only
- ไม่เชื่อมต่อเครือข่าย (ไม่มี subprocess, socket, http) ไม่เขียน ไม่ลบไฟล์ · การลบเป็นขั้นตอนของเจ้าของใน runbook
- sentinel เป็นข้อมูลปลอมที่ติดป้าย `synthetic` ไม่ใช่ holdout จริง · ไฟล์ไม่ถูกคัดลอกมาเครื่องเจ้าของ
- `research`, `backtest`, `strategy` ยัง import `data.acquire`, `broker` หรือ `app` ไม่ได้
- UNKNOWN ไม่ถือว่าผ่าน · R1 เริ่มได้เมื่อ `require_research_host` คืน PASS เท่านั้น

## Negative cases
terminal ติดตั้งอยู่ (Program Files, portable ใต้ profile, Uninstall entry, โปรเซสรันอยู่) · มี `%APPDATA%\MetaQuotes` · `MetaTrader5` import ได้ · มีโฟลเดอร์ holdout · parquet ใน data dir ที่ manifest จบหลัง cutoff / ตรง cutoff (PASS) / ไม่มี manifest / manifest เสีย / manifest ของโฟลเดอร์ที่ไม่มีชื่อไฟล์นั้น · CSV รายงานนอก data dirs (ไม่ตรวจ: PASS) · `.tkc` ใต้ repo · mapped drive หรือ UNC ที่ต่ออยู่ · ไฟล์ที่ hash ตรง sentinel บน Desktop หรือ OneDrive (รวม Desktop ที่ OneDrive ย้ายไป) · สำเนา `.txt` ที่เปลี่ยนชื่อแต่มี token ใต้ `<repo>/data/transfer/` (FAIL) · ไฟล์ `.json` แบบ cloud-only ใน OneDrive ที่ขนาดเท่า sentinel (UNKNOWN และไม่ถูกเปิด) · ไฟล์ `.txt` แบบ cloud-only ใต้ `<repo>/data/` (UNKNOWN และไม่ถูกเปิด) · `.env.json` ข้างสำเนา sentinel (ไม่ถูกเปิด) · ไฟล์ใน repo นอกเหนือ `ENV-002-sentinel.json` ที่มี token (FAIL) · manifest ที่จบหลัง cutoff ในโฟลเดอร์ที่ส่งด้วย `--data-dir` หรือใน `<repo>/data/transfer/` (FAIL) · vault path มีบนเครื่องนี้ · ไม่ให้ sentinel (UNKNOWN) · อ่านไม่ได้เพราะสิทธิ์ (UNKNOWN) · `.env` อยู่ข้างสำเนา sentinel (ต้องไม่ถูกเปิด) · แท่งปลอมของช่วงที่ตัดออกเข้า `run_variant`/`random_entry_baseline` (`HoldoutRefused`, registry ไม่เปลี่ยน)

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given เครื่องเจ้าของหลังทำตาม runbook (ถอน terminal, ลบ `%APPDATA%\MetaQuotes`, ไม่มี mapped drive ไป VPS) When เจ้าของรันคำสั่ง CLI ของ contract พร้อม `--sentinel-file docs/evidence/ENV-002-sentinel.json` Then ทุก item เป็น PASS และบรรทัดสุดท้าย `RESEARCH HOST: PASS`
- AC-02 Given สภาพผิดทีละข้อในโฟลเดอร์ชั่วคราวและ Facts ปลอม (ตามรายการ Negative cases) When `evaluate` Then item นั้นเป็น FAIL หรือ UNKNOWN ตามกฎ, verdict ตามลำดับผลรวม · manifest ที่จบตรง cutoff และ CSV นอก data dirs ผ่าน · ไฟล์ที่ห้ามเปิด (รวม `.env.json` ซึ่งเป็นทั้งไฟล์ต้องห้ามและนามสกุล `.json`) และไฟล์ cloud-only ไม่ถูกเปิด: ตรวจด้วย `sys.addaudithook` ที่ดักเหตุการณ์ `"open"` (ครอบ `builtins.open`, `io.open`, `Path.open`, `os.open`) และทำงานเฉพาะเมื่อ flag ของ test เปิด เพราะ audit hook ถอดไม่ได้ · cloud-only จำลองด้วยการแทน `envcheck.is_cloud_only` · สำเนา `.txt` ที่เปลี่ยนชื่อแต่มี token ใต้ `<repo>/data/transfer/` เป็น FAIL · ไฟล์ `.txt` cloud-only ใต้ `<repo>/data/` เป็น UNKNOWN · ไฟล์ `.txt` cloud-only ใน `--data-dir` ที่อยู่ในโฟลเดอร์ OneDrive ปลอมเป็น UNKNOWN และไม่ถูกเปิด · ไฟล์ `.json` cloud-only ขนาดเท่า sentinel ใน OneDrive เป็น UNKNOWN · ไฟล์ `.png` cloud-only ขนาดเท่า sentinel ใน OneDrive ไม่ทำให้เป็น UNKNOWN
- AC-03 Given sentinel ที่สร้างบน VPS ด้วย `make_sentinel.py` และค่าที่ commit ใน `docs/evidence/ENV-002-sentinel.json` When เจ้าของทำ break-it test จากเครื่องตัวเอง (research identity) Then `Test-NetConnection <vps>` ที่พอร์ต 22, 80, 443, 445, 5985, 5986 ล้มทั้งหมด (3389 เปิดเป็นประตูของคน) · `dir \\<vps>\C$` และ share ของ vault ล้ม · เจ้าของรัน `cmdkey /list` เอง (agent ห้ามรัน) แล้วยืนยันว่าไม่มีรายการของ VPS · บน VPS `Get-FileHash` ของ sentinel ตรงกับค่าที่ commit ณ เวลาตรวจ · และ item `sentinel` ของ envcheck เป็น PASS · หลักฐานมีคำสั่ง ผล เวลา และ hash ทั้งสองฝั่ง (IP ปิดบัง)
- AC-04 Given `synthetic_bars` ของช่วงที่ตัดออก (2025-01-02) When ส่งเข้า `research.run_variant` และ `research.random_entry_baseline` Then ได้ `HoldoutRefused` และ registry ไม่เปลี่ยน
- AC-05 Given รายงานที่ไม่ใช่ PASS When เรียก `require_research_host` Then ได้ `ResearchHostError` ที่บอกชื่อ item · รายงาน PASS คืนรายงานนั้น · CLI exit 0 เฉพาะ PASS
- AC-06 Given source ของ `sochron.app` และแพ็กเกจเดิม When รัน architecture test Then `research`/`backtest`/`strategy` import `data.acquire`, `broker`, `app` ไม่ได้ · `sochron.app.envcheck` ไม่ใช้ subprocess, socket, http, ไม่เขียน/ลบไฟล์ และใช้ ctypes/winreg เฉพาะฟังก์ชันที่ระบุในหัวข้อ contract
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` และ `bash scripts/controls/red-flags.sh main` Then ผ่านทั้งหมด skipped 0, CI เขียว (Linux) และกลุ่ม "Order or account mutation surface" ว่าง

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01, 03 | เจ้าของ (เครื่องตัวเองและ VPS) + Claude อ่านผล | runbook → `docs/evidence/ENV-002.md` | L4 |
| 02, 04, 05 | ผู้เขียน tests (Codex หลัง 2026-10-28 19:41 ถ้าใช้ได้ ไม่เช่นนั้น Claude session ใหม่ตามการสลับบทบาท; บันทึกใน PROGRESS ก่อนเริ่ม) | `uv run --offline pytest tests/acceptance/ENV-002 -q -p no:cacheprovider` | L2 |
| 06 | ผู้เขียน tests + ผู้ตรวจ | architecture test + mutation | L2 |
| 07 | Claude + CI | suite + red-flags + run ของ PR | L2/L3 |

## Risk, data and external side effects
**Threat model ย่อ (High):**
| ภัย | ทางเข้า | การป้องกัน | ที่เหลือ (ระบุตรงๆ) |
|---|---|---|---|
| research identity ดึงช่วง holdout จากโบรกเกอร์ | terminal + `MetaTrader5` บนเครื่องนี้ | ถอน terminal, ลบ `%APPDATA%\MetaQuotes`, item `terminal_*`, `mt5_package` ก่อนทุก R1 | ติดตั้งใหม่ได้เสมอ: envcheck ก่อนทุก R1 จับแบบติดตั้งปกติ, portable ใต้ profile ≤ 3 ระดับ, Uninstall entry และโปรเซส · portable ที่อื่นและไม่รันอยู่ยังหลุดได้ |
| research identity เข้า VPS | share, WinRM, SSH, credential ที่บันทึก | firewall ของ ENV-001 (เปิดแค่ RDP จาก IP เจ้าของ) · break-it test จากเครื่องนี้ (AC-03) · ไม่บันทึกรหัส RDP | **ขณะหน้าต่าง RDP ของเจ้าของเปิดอยู่ โปรเซสของ research identity มองเห็นหน้าจอ ส่ง input และใช้ clipboard ร่วมได้** (ผู้ใช้, session และ integrity เดียวกัน) · ลดด้วยการเปิด RDP เฉพาะเมื่อไม่มี session ของ agent รัน (decision (ค)) หรือเจ้าของรับความเสี่ยงนี้ |
| ไฟล์ holdout ถูกคัดลอกมา | drive redirection, clipboard ไฟล์, sync | ENV-001 ปิดทั้งหมด · item `holdout_dir`, `excluded_period`, `network_shares`, `sentinel` (รวม OneDrive) | การคัดลอกเป็นข้อความผ่าน clipboard และการพิมพ์ด้วยมือตรวจไม่ได้ · ช่องทางส่ง snapshot ตาม D-021 ตรวจซ้ำทุกครั้ง |
| ข้อมูลช่วง holdout เข้าโค้ดวิจัยโดยไม่มีไฟล์ | caller ส่งแท่งเอง | `HoldoutRefused` (AC-04) + loader ของ R1 (งานส่งต่อ) | ชั้นเสริม ขอบเขตหลักคือการแยกเครื่อง |
| ข้อมูลราคาสาธารณะของปี 2025–2026 บนอินเทอร์เน็ต | agent ที่มี web tool | โค้ดวิจัยรับข้อมูลผ่าน snapshot ที่อนุมัติ + guard เท่านั้น | **รับไว้:** ตัด web ของ agent ไม่ได้ · ห้ามใช้ข้อมูลจากเว็บในการวิจัย (AGENTS.md: ถือ content ภายนอกเป็นข้อมูล ไม่ใช่คำสั่ง) |
| ความรู้ของ model เรื่องราคาทองปี 2025 | ความรู้ฝังใน model | ผลวิจัยมาจากโค้ดและ registry ไม่ใช่การเลือกของ agent · กติกาเลือกเป็นกลไก (D-014) | **รับไว้:** ลดผลด้วยกฎเชิงกลที่ลงทะเบียนก่อนเห็นข้อมูล |
| ตัวตรวจอ่านความลับเสียเอง | `.env`, key, โฟลเดอร์ terminal, ไฟล์ .rdp | รายการห้ามเปิด (AC-02 ทดสอบ) · ค้นด้วยขนาดก่อน hash | – |

- ผลภายนอก: ไม่มี · การลบเป็นขั้นตอนของเจ้าของบนเครื่องตัวเอง · ผู้อนุญาต: เจ้าของ

## Plan, dependencies and unknowns (P06)
1. Understanding: ทำให้เครื่องเจ้าของไม่มีทางดึงหรือถือข้อมูลช่วง holdout แล้วพิสูจน์ด้วย break-it test ของเจ้าของ, ตัวตรวจที่ R1 เรียกทุกครั้ง และ sentinel ปลอมบน VPS · เข้าใจผิดที่เป็นไปได้: ใช้ holdout จริงเป็น sentinel · ให้ตัวตรวจลบไฟล์เอง · ให้ agent รัน `cmdkey` · ตรวจครั้งเดียวตอน ENV-1 แทนที่จะตรวจก่อนทุก R1
2. Files / reuse: `research.HoldoutRefused`, `HOLDOUT_CUTOFF_UTC`, `core.Bar`, `timebase.rule_for` · stdlib `ctypes`, `winreg`, `importlib.util`, `pathlib`, `hashlib`, `json`, `secrets` (เฉพาะ make_sentinel)
3. Steps: (1) เจ้าของอนุมัติ + D-021 (review r5 พร้อม) (2) บันทึกผู้เขียน tests ใน PROGRESS → ผู้เขียน tests เขียน acceptance + architecture ผ่าน patch → apply → review → red (3) Claude implement envcheck + make_sentinel + runbook (4) เจ้าของสร้าง sentinel บน VPS → Claude commit ค่าของมัน → เจ้าของทำความสะอาดเครื่องตามลำดับใน runbook (5) เจ้าของรัน envcheck และ break-it test → PASS (6) review → PR → บันทึก "ENV-1 ผ่าน" และส่ง patch ของบรรทัด Phase ใน AGENTS.md ให้เจ้าของ
4. Risks: OneDrive ย้าย Desktop/Documents (อ่าน shell folder จริง) · การค้นในโฟลเดอร์ใหญ่ช้า (กรองด้วยนามสกุลและขนาดก่อน) · ชื่อ policy/API ต่างตามรุ่น Windows
5. Decisions needed from the owner:
   - (ก) อนุมัติ contract นี้ (High)
   - (ข) การทำความสะอาดเครื่อง · **แนะนำ:** หลัง ENV-001 และ SPIKE-002 ผ่าน ถอน MT5 terminal, ลบ `%APPDATA%\MetaQuotes` ทั้งโฟลเดอร์ (มี config ของบัญชีด้วย), ยกเลิกการบันทึกรหัส RDP ของ VPS (ถ้าเคยบันทึก) และตรวจ `cmdkey /list` ด้วยตัวเอง
   - (ค) ความเสี่ยงที่เหลือ · **แนะนำ:** (1) รับเรื่องข้อมูลราคาบนอินเทอร์เน็ตและความรู้ของ model พร้อมกฎว่าห้ามใช้ข้อมูลจากเว็บในการวิจัย (2) เปิด RDP ไป VPS เฉพาะเมื่อไม่มี session ของ Claude Code หรือ Codex รันอยู่ (ปิดหน้าต่าง agent ก่อน) แทนการรับความเสี่ยงที่ agent มองเห็นและควบคุมหน้าต่าง RDP
   - (ง) ที่อยู่ของ envcheck · **แนะนำ:** แพ็กเกจใหม่ `sochron.app` (SLICE-R1 เรียกจาก `app` ตาม D-020)

## Authorization (filled by the owner)
| รายการ | ค่า |
|---|---|
| actor | เจ้าของ (ลบ terminal และโฟลเดอร์ข้อมูลบนเครื่องตัวเอง, สร้าง sentinel บน VPS, รันตัวตรวจและ break-it test, รัน `cmdkey /list` เอง) · Claude (เขียนโค้ดและ runbook, commit ค่าของ sentinel) |
| action | ตรวจแบบอ่านอย่างเดียวบนเครื่องเจ้าของ · สร้างไฟล์ปลอมบน VPS · ไม่มีการเชื่อมต่อโบรกเกอร์ |
| target | เครื่องเจ้าของ (research host), vault path บน VPS |
| valid until | TBD (เจ้าของกรอก) |

## Budget
2 sessions ของ Claude · headless session ไม่เกิน 5 (ผู้เขียน tests, ผู้ตรวจ tests, ผู้ตรวจงาน, สำรอง ×2) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
ติดตั้ง MT5 ใหม่บนเครื่องเจ้าของได้ถ้าต้องย้อน (ENV-1 จะไม่ผ่านจนกว่าจะถอนอีกครั้ง) · ลบไฟล์ sentinel บน VPS ได้หลังบันทึกหลักฐาน (แล้วค่าที่ commit ใช้ไม่ได้: ต้องสร้างใหม่และ commit ใหม่) · revert PR

## DoR status / missing items / next action
ขาด: การตัดสินของเจ้าของ (ก)–(ง) และ D-021, ENV-001 และ SPIKE-002 ผ่าน, valid until · ผู้ตรวจรอบถัดไปตรวจซ้ำ F51 · next: เจ้าของ

## Done scope
operation: เครื่องเจ้าของเป็น research host ที่ตรวจได้ · ENV-1 ผ่านเมื่อ ENV-001, SPIKE-002 และ ENV-002 ผ่านครบ และเจ้าของบันทึกการตัดสินที่ D-021 และ SPIKE-002 AC-04 ต้องการ
