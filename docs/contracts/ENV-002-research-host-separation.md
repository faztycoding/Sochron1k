# TASK ENV-002 — แยก research host ออกจาก terminal และ holdout พร้อม synthetic excluded-period sentinel

Version v1.5 (v1 ร่าง 2026-10-25 → v1.1 ตอบ `docs/reviews/ENV-contracts-r1.md`: research identity และ break-it test (F1), OneDrive (F3), ความหมายของ "ผ่าน data" และงานที่ส่งต่อ (F7), คำสั่งที่รันได้จริง (F8), นิยามที่ผู้เขียน tests ต้องใช้ (F9), ขอบเขตของ excluded_period (F11), การค้น sentinel ที่ไม่อ่านไฟล์ลับ (F12), terminal ที่ติดตั้งที่อื่น (F13), ความสอดคล้อง (F20) → v1.2 ตอบ `docs/reviews/ENV-contracts-r2.md`: การประเมิน holdout เป็นงานส่งต่อ (F7), ที่อยู่ของตัวสร้างแท่งปลอม (F9), เอกสารที่แก้ตอนบันทึก ENV-1 ผ่าน (F20), โฟลเดอร์รับไฟล์ของ D-021 (F29), shell folder/ขอบเขตของ hash/token (F30), ความเสี่ยงของ RDP ที่เปิดอยู่ (F32) → v1.3 ตอบ `docs/reviews/ENV-contracts-r3.md`: ขอบเขตการค้น token และไฟล์ cloud-only (F36), ขั้นตอนโหลด `synthetic.py` (F37), `ResearchRoots` ชุดเดียวของ R1 (F43 a), ป้ายเวอร์ชัน (F44) → v1.4 ตอบ `docs/reviews/ENV-contracts-r4.md` (ทุกข้อ Low): ไฟล์ cloud-only ใน repo/data dirs (F49), จุดที่ tests แทนและการดักการเปิดไฟล์ (F50) → v1.5 ตอบ `docs/reviews/ENV-contracts-r5.md` (Low): ไฟล์ที่อยู่ทั้งใต้ data dirs และ search_dirs (F51) → **v1.6 ตอบคำถามของผู้เขียน tests (`docs/handoff/ENV-002.md` Q2–Q12) อนุมัติโดยการมอบอำนาจ 2026-11-05 15:0x:** ระดับของการค้น terminal และ helper ที่ทดสอบได้ (Q2, Q3), ไม่สนตัวพิมพ์ (Q4), data dir ที่ไม่มีอยู่ (Q5), ไฟล์ห้ามเปิดที่กฎค้นต้องเปิด = UNKNOWN (Q6), รายงานไม่พิมพ์ token (Q7), vault_path (Q8), `default_roots` และ `main` (Q9), ค้นรวม `.git`/`.venv` (Q11), ขอบเขตของตัวตรวจ AC-06 (Q12) → **v1.7 ตอบ `docs/reviews/ENV-002-tests-r1.md` F2, F5–F8 อนุมัติโดยการมอบอำนาจ 2026-11-05 17:4x:** manifest ที่เป็น cloud-only (F2), allow list ของ stdlib และ sub-key ของ registry (F5), token แบบ UTF-16 (F6), token ใน stderr และข้อความ error (F7), โฟลเดอร์ที่ list ไม่ได้และ reparse point (F8) → **v1.8 (implementer, อนุมัติโดยการมอบอำนาจ 2026-11-05 17:5x):** การค้น path ของ terminal ข้ามโฟลเดอร์ระบบที่ list ไม่ได้ ตามที่วัดบนเครื่องเจ้าของ → **v1.9 ตอบ `docs/reviews/ENV-002-r1.md` F1–F9 อนุมัติโดยการมอบอำนาจ 2026-11-05 19:3x:** data dir ที่ครอบ repo (F1), reparse point (F2, F3 ทาง (a)), root และค่าที่อ่านไม่ได้ (F5, F6), ไฟล์ค่าของ sentinel (F7), manifest สองแบบ (F8), detail ที่เป็นหลักฐาน (F9) → **v2.0 ร่าง 2026-11-17 (ยังไม่อนุมัติ): research host เป็นเครื่อง Mac ตาม D-023 (proposed)**: research identity บน macOS, ตัวอ่านข้อเท็จจริงของ macOS ใน envcheck, AC-01 และ AC-03 ฉบับ macOS, เครื่อง Windows เดิม, runbook ฉบับ macOS · ทุกจุดที่เปลี่ยนติดป้าย "(v2.0)") · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 6.1 ("ด่านก่อน SLICE-R1"), 9, 13a · D-017, D-019, D-020, D-021, D-023 (proposed) · Tier **High** · Branch `feat/ENV-002-research-host-separation` (ร่าง v2.0 อยู่บน `chore/ENV-002-macos-research-host` จาก `c97aac6` จนกว่าเจ้าของอนุมัติ)
Status: **v2.0 draft 2026-11-17: รอ contract review และการอนุมัติของเจ้าของ (High) · ฉบับที่อนุมัติล่าสุดคือ v1.9 ซึ่งโค้ดและ tests บน branch ทำตาม** · ประวัติ v1.x: **approved by owner 2026-10-25 17:5x; v1.6 approved by delegation 2026-11-05 15:0x; v1.7 approved by delegation 17:4x; v1.8 approved by delegation 17:5x; v1.9 approved by delegation 19:3x** (v1.9: ทางที่แนะนำของ `docs/reviews/ENV-002-r1.md` F1–F9 รวม F3 ทาง (a) และ F8 "ผ่านทั้งสอง") (v1.7: ทางที่แนะนำ (a) ของ tests-r1 F5–F8 และข้อเสนอของ F2 ตามการมอบอำนาจเดียวกัน) · (v1.6: เจ้าของสั่ง 13:4x "อนุมัติตาม recommended ไปเลย" จึงใช้ทางที่แนะนำของ Q2–Q12 ทุกข้อ เลือกทาง fail-closed; เจ้าของ veto ได้ก่อน merge · branch จริงคือ `feat/ENV-002-research-host-separation` ตามหัวข้อนี้) · (v1.5 · เจ้าของตอบ "อนุมัติทั้งหมด" ในแชท Claude: contract นี้, การตัดสิน (ก)–(ง) ตามที่แนะนำ และ D-021 · review r5 ว่าพร้อม · ข้อ Low F51 ของ r5 แก้ใน v1.5 ให้ผู้ตรวจรอบถัดไปตรวจซ้ำ) · เริ่มได้หลัง ENV-001 และ SPIKE-002 ผ่าน
Hypothesis (research tasks): ไม่ใช่งานวิจัย

ด่าน ENV-1: ENV-001 → SPIKE-002 → **ENV-002**

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: **yes** — งานนี้คือขอบเขตระหว่าง research identity กับ holdout
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no — sentinel เป็นข้อมูลปลอม
- Q4 schema change or deletion of real data: **yes** — เจ้าของถอน MT5 terminal และลบโฟลเดอร์ข้อมูลของ terminal บนเครื่องตัวเอง · (v2.0) เครื่องที่ถูกล้างคือเครื่อง Windows เดิม รวมการลบ clone และ worktree ของ repo บนเครื่องนั้น (D-023 ข้อ 2)
- Q5 hard-to-reverse external effect: no (ติดตั้งใหม่ได้)
- Q6 changes controls: no สำหรับ hooks/CI · เพิ่มกฎใน `tests/architecture` (ล็อก) ผ่าน patch ของผู้เขียน tests ตาม D-006

**High** ตาม Q1, Q4

## นิยาม
- **research identity** = (v2.0, D-023) บัญชีผู้ใช้ macOS ของเจ้าของบนเครื่อง Mac ซึ่งเป็น research host เครื่องเดียว (v1.9 เดิม: บัญชีผู้ใช้ Windows บนเครื่อง Windows) รวมทุกโปรเซสที่ agent (Claude Code, Codex) เปิด · (v2.0) บน macOS โปรแกรม RDP คือ Windows App และการมองเห็นหน้าจอหรือส่ง input ข้ามแอปต้องมีสิทธิ์ Screen Recording/Accessibility ของแอปที่ agent รันอยู่ ซึ่งโค้ดตรวจไม่ได้ จึงคงกฎของ decision (ค) ตามเดิม · การเข้า VPS ผ่าน RDP แบบ interactive ของเจ้าของเป็น **ประตูของคน**: รหัสผ่าน RDP ต้องไม่ถูกบันทึกบนเครื่องนี้ และ **ขณะที่หน้าต่าง RDP เปิดอยู่ โปรเซสของ research identity มองเห็นและส่ง input เข้าหน้าต่างนั้นได้** (โปรเซสผู้ใช้เดียวกัน, session เดียวกัน, integrity ระดับเดียวกัน) จึงต้องเปิด RDP เฉพาะเมื่อไม่มี session ของ agent รันอยู่ (decision (ค))
- **ช่วงที่ตัดออก** = ข้อมูลตลาดตั้งแต่ `HOLDOUT_CUTOFF_UTC` (2025-01-01 00:00 UTC) · `period_end_utc` เป็นจุดสิ้นสุดแบบไม่รวม ความหมายเดียวกับ `research.Dataset`
- **"อ่านหรือดึงไม่ได้ ทั้งโดยตรงและผ่าน data" ที่ ENV-1** (architecture ข้อ 6.1) = (1) โดยตรง: research identity ไม่มีไฟล์ช่วงที่ตัดออก ไม่มี share/drive ไป VPS ไม่มีพอร์ตอื่นนอกจาก RDP และไม่มี credential ของ VPS (break-it test, AC-03) (2) ดึงจากโบรกเกอร์: ไม่มี terminal และ `MetaTrader5` บนเครื่องนี้ (3) ผ่านโค้ด: `research` ปฏิเสธแท่งของช่วงนั้น (`HoldoutRefused`) และ `research`/`backtest`/`strategy` import `data.acquire`, `broker`, `app` ไม่ได้ · loader ของ R1 ที่ยังไม่มีเป็นงานส่งต่อ (หัวข้อ "งานที่ส่งต่อ")

## Goal / user outcome (Thai)
เครื่องเจ้าของเป็น research host ตามข้อ 6.1 ที่พิสูจน์ได้:
- ไม่มี MT5 terminal (ทั้งแบบติดตั้งและแบบ portable), โฟลเดอร์ `%APPDATA%\MetaQuotes` หรือแพ็กเกจ `MetaTrader5` ที่ import ได้ · (v2.0) บน Mac: ไม่มีแอป `MetaTrader*.app`, ไม่มีโฟลเดอร์ Wine ของ MT5 ใต้ `~/Library/Application Support`, ไม่มี `terminal64.exe` ใน Wine prefix ที่รู้จัก
- (v2.0) เครื่อง Windows เดิมเลิกใช้กับโปรเจกต์นี้และถูกล้างตาม D-023 ข้อ 2 (ก): ไม่มี terminal, ไม่มีโฟลเดอร์ข้อมูลของ terminal, ไม่มี clone ของ repo และไม่มี session ของ agent
- ไม่มี holdout หรือไฟล์ข้อมูลตลาดของช่วงที่ตัดออกในพื้นที่ที่ research ใช้ ไม่มี drive/share ที่ต่อไป VPS
- เจ้าของทดสอบจากเครื่องตัวเองแล้วว่าเข้า VPS ได้ทาง RDP แบบ interactive เท่านั้น และไม่มี credential ของ VPS บันทึกไว้
- `sochron.app.envcheck` ที่ R1 ต้องผ่านก่อนทุกครั้ง และ synthetic sentinel บน VPS ที่หาไม่เจอบนเครื่องนี้

## Current behavior and evidence (revision)
`main` `a11bff7` · เครื่องเจ้าของมี `C:\Program Files\MetaTrader 5` และ `%APPDATA%\MetaQuotes` (ตรวจแค่การมีอยู่) · `MetaTrader5` ไม่อยู่ใน `pyproject.toml` · โปรเจกต์เป็น virtual project (`package = false`): `python -m sochron…` ต้องตั้ง `PYTHONPATH=src` (pytest ใช้ `pythonpath = ["src"]` เอง) · `research` ปฏิเสธแท่งตั้งแต่ cutoff ก่อนการตรวจอื่น (`inputs.py` holdout guard) และต้องการ `core.Bar` พอดี · `data.snapshot` ยังไม่มีตัวอ่าน snapshot (SLICE-R1, D-020)

(v2.0) วัดบนเครื่อง Mac 2026-11-17 ที่ `c97aac6` (macOS 26.6.2, arm64, zsh 5.9, uv 0.13.5, CPython 3.12.15):
- `uv run --offline pytest tests -q -p no:cacheprovider` → 3692 passed (เท่ากับ Windows 2026-11-05)
- อ่านโค้ด `src/sochron/app/envcheck.py` (ยังไม่ได้รันบน Mac เพราะตัวตรวจค้นโฟลเดอร์ส่วนตัวของเจ้าของ): ไม่มีตัวแปร `ProgramFiles*` จึง `raise OSError("no Program Files folder to search")` (บรรทัด 599–600) · `ctypes.WinDLL` (643, 650, 677, 739–740), `os.listdrives` (646), `import winreg` (717) ล้มแล้ว `guarded` คืน None (756–759) → `terminal_install` และ `network_shares` เป็น UNKNOWN · `terminal_data` ตรวจ `~/AppData/Roaming/MetaQuotes` ซึ่งไม่มีความหมายบน Mac (784–785) · `is_cloud_only` อ่าน `st_file_attributes` ซึ่ง macOS ไม่มี (175) · symlink ใต้ repo ทำให้ `holdout_dir`, `excluded_period`, `sentinel` เป็น UNKNOWN (338, 562) → verdict บน Mac เป็น UNKNOWN เสมอ
- symlink ใต้ repo มี 3 ตัว ทั้งหมดอยู่ใต้ `.venv/bin/`: `python` → interpreter ของ uv, `python3` → `python`, `python3.12` → `python` · ใต้ `.git` ไม่มี
- filesystem ที่ mount: `apfs`, `devfs`, `autofs` เท่านั้น · ไม่มี `/Applications/MetaTrader*`, `~/Applications/MetaTrader*`, `~/Library/Application Support/net.metaquotes.wine.metatrader5`, `~/Library/Application Support/CrossOver`, `~/Library/PlayOnMac` · มี iCloud Drive (`~/Library/Mobile Documents/com~apple~CloudDocs`) · ไม่มี `~/Library/CloudStorage`
- `SF_DATALESS` = `0x40000000` (`sys/stat.h` ของ macOS SDK) · `os.stat()` บน Mac มี `st_flags` · โมดูล `stat` ของ Python 3.12 ไม่มีค่าคงที่ `SF_DATALESS`
- แพ็กเกจ `MetaTrader5` ไม่มี wheel สำหรับ macOS (AGENTS.md: "Windows-only wheels") `mt5_package` จึงผ่านโดยแพลตฟอร์ม
- path ของ MT5 บน macOS มาจากผลค้นเว็บ 2026-11-17 (หน้า help ทางการของ MetaQuotes และคู่มือโบรกเกอร์) ยังไม่ได้เปิดหน้าทางการตรวจเอง: **ผู้ตรวจ contract ต้องยืนยัน** (D-023 ข้อ 4)

## Scope
- In scope: `src/sochron/app/__init__.py`, `src/sochron/app/envcheck.py` · `scripts/env/make_sentinel.py` (stdlib เท่านั้น, รันบน VPS) · unit tests `tests/unit/app/**` · runbook `docs/runbooks/ENV-002-research-host.md` · `docs/evidence/ENV-002-sentinel.json` (ค่าของ sentinel ที่ commit: ชื่อ, ขนาด, SHA-256, token, vault path, เวลาสร้าง) · หลักฐาน · โดยผู้เขียน tests ผ่าน patch D-006: `tests/acceptance/ENV-002/**`, `tests/architecture/**`
- (v2.0) In scope เพิ่ม: ตัวอ่าน macOS ใน `src/sochron/app/envcheck.py` (เพิ่ม ไม่รื้อตัวอ่าน Windows) · unit tests ของตัวอ่าน macOS ใน `tests/unit/app/**` · runbook ฉบับ macOS ใน `docs/runbooks/ENV-002-research-host.md` (ขั้นบน VPS ไม่เปลี่ยน) · โดยผู้เขียน tests ผ่าน patch D-006: กรณี macOS ใน `tests/acceptance/ENV-002/**` และตัวตรวจ ctypes ของ envcheck ใน `tests/architecture/test_imports.py` (v2.1, F2: แก้แบบแคบตามหัวข้อ Invariants; allow list ของ stdlib ไม่เปลี่ยน) · `DECISIONS.md` เฉพาะ D-023 และบรรทัดอ้างกลับใต้ D-021 (v2.1, F17)
- (v2.0) Exclusions เพิ่ม: runbook และ AC ของ ENV-001 ฝั่งเครื่องเจ้าของ (contract revision ของ ENV-001) · การแก้ controls ให้ผ่านบน macOS (งาน FIX แยก, Q6) · patch ของ `AGENTS.md`/`CLAUDE.md` และ `docs/tooling/**` (งานตามของ D-023) · การติดตั้ง MT5 หรือ Wine บน Mac เพื่อทดสอบ (ห้าม)
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
  (v1.6, Q9) default_roots(extra_data_dirs) -> ResearchRoots         # data_dirs = (<repo>/data, *extra_data_dirs) · ใช้เมื่อ roots เป็น None และใน CLI
  (v1.6, Q9) main(argv) -> int                                        # CLI: พิมพ์ทุก item แล้วบรรทัดสุดท้าย "RESEARCH HOST: <verdict>" · exit 0 เฉพาะ PASS
  CLI (Git Bash):   PYTHONPATH=src uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json [--data-dir <path> …]
      (PowerShell): $env:PYTHONPATH="src"; uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json
      พิมพ์รายงาน + "RESEARCH HOST: PASS|FAIL|UNKNOWN" · exit 0 เฉพาะ PASS
Items:
  terminal_install  FAIL เมื่อพบอย่างใดอย่างหนึ่ง: โฟลเดอร์ `Program Files*\MetaTrader*` · `terminal64.exe` ในระดับ 1–2 ของ Program Files
                    · Uninstall entry (HKLM, HKCU, WOW6432Node) ที่ DisplayName มี "MetaTrader" · โปรเซส `terminal64.exe` ที่รันอยู่
                    · `terminal64.exe` ใต้ user profile ลึกไม่เกิน 3 ระดับ (ข้าม .git, .venv, node_modules)
                    · (v1.6, Q3) ระดับ = จำนวนโฟลเดอร์ระหว่างรากกับไฟล์ (`<root>\terminal64.exe` = 0): Program Files* ระดับ 0–2,
                      user profile ระดับ 0–3 · (Q4) "MetaTrader" และ `terminal64.exe` ไม่สนตัวพิมพ์ · (Q2) การค้น path อยู่ในฟังก์ชัน
                      ระดับโมดูลที่รับโฟลเดอร์ราก (ไม่เรียก Windows API) ซึ่ง collect เรียก และมี unit test ใน `tests/unit/app/` บนโฟลเดอร์ชั่วคราว
  terminal_data     FAIL เมื่อ `%APPDATA%\MetaQuotes` มีอยู่ (ตรวจการมีอยู่เท่านั้น ห้าม list หรืออ่านข้างใน)
  mt5_package       FAIL เมื่อ `importlib.util.find_spec("MetaTrader5")` ไม่ใช่ None
  holdout_dir       FAIL เมื่อมีโฟลเดอร์ชื่อ holdout (ไม่สนตัวพิมพ์) ใต้ repo หรือ data dirs
  excluded_period   ใน data dirs: ทุกไฟล์ `*.parquet`, `*.csv`, `*.hcc`, `*.hc`, `*.tkc` ต้องมี manifest — `<ชื่อไฟล์>.manifest.json` ข้างกัน
                    หรือ `manifest.json` ในโฟลเดอร์เดียวกันที่มี {"files": [{"name", "sha256"}, …], "period_end_utc": "%Y-%m-%dT%H:%M:%SZ"}
                    และไฟล์นั้นอยู่ใน "files" · period_end_utc ≤ cutoff = PASS · > cutoff = FAIL · ไม่มี manifest = FAIL · manifest เสีย
                    (JSON ผิด, ขาด field, เวลาผิดรูปแบบ) = FAIL · อ่านไม่ได้เพราะสิทธิ์ = UNKNOWN
                    นอก data dirs แต่ใต้ repo: เฉพาะ `*.hcc`, `*.hc`, `*.tkc` (cache ของ MT5) = FAIL · CSV/parquet อื่นใต้ repo ไม่ตรวจที่นี่
                    (การตรวจ hash และเวลาจริงของไฟล์เป็นงานของ loader ใน SLICE-R1)
                    · (v1.6, Q5) data dir ค่าตั้งต้น `<repo>/data` ที่ไม่มีอยู่ = ไม่มีไฟล์ให้ตรวจ (ไม่ทำให้ FAIL หรือ UNKNOWN) · data dir ที่ส่ง
                      ด้วย `--data-dir` แต่ไม่มีอยู่ = UNKNOWN (พิมพ์ผิดต้องไม่ผ่านเงียบ) · (Q4) นามสกุลไม่สนตัวพิมพ์
                    · (v1.7, tests-r1 F2) manifest ที่เป็น cloud-only ไม่ถูกเปิด และไฟล์ข้อมูลที่ต้องใช้ manifest นั้น = UNKNOWN
                    · (v1.9, r1 F8) ไฟล์ที่มีทั้ง `<ชื่อไฟล์>.manifest.json` และ `manifest.json` ต้องผ่านทั้งสอง (อ่านได้, ไม่เสีย, มีชื่อไฟล์,
                      จบไม่เกิน cutoff) · (r1 F1) data dir ทุกตัวใช้กฎของ data dir แม้อยู่ใต้ data dir อื่นหรือครอบ repo ไว้ และไฟล์ใน repo
                      ที่อยู่ใต้ data dir ใช้กฎของ data dir
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
                    · (v1.6, Q6) ไฟล์ห้ามเปิดที่กฎ (3) หรือ (4) จะต้องเปิด (เช่น `.env.json` ขนาดเท่า size ใน search_dirs หรือ `.env.txt`
                      ใน repo/data dirs) = UNKNOWN และไม่ถูกเปิด · (Q4) ชื่อ sentinel และนามสกุลไม่สนตัวพิมพ์ · (Q11) ค้นทุกโฟลเดอร์ใต้ repo
                      และ data dirs รวม `.git` และ `.venv` · (Q7) detail และรายงานไม่พิมพ์ token (แสดงได้แค่ชื่อ, ขนาด, SHA-256)
                    · (v1.6, Q8) vault_path เป็นโฟลเดอร์ vault หรือไฟล์ sentinel ก็ได้ (FAIL เมื่อ path นั้นมีอยู่บนเครื่องนี้)
                    · (v1.7, tests-r1 F6) token ค้นทั้งแบบ UTF-8/ASCII และ UTF-16 (LE และ BE, มีหรือไม่มี BOM) · (F7) token ไม่อยู่ใน
                      stdout, stderr หรือข้อความของ `ResearchHostError`
                    · (v1.9, r1 F5, F7) vault_path ที่ตรวจไม่ได้ (stat ล้มด้วยเหตุอื่นนอกจากไม่มี) = UNKNOWN · search dir ที่ไม่มีอยู่หรือ
                      list ไม่ได้ = UNKNOWN · `name` หรือ `vault_path` ว่าง = UNKNOWN · ไฟล์ค่าที่ CLI อ่าน: `name` ต้องเป็น
                      `SENTINEL-ENV002-<token 8 ตัวแรก>.json`, `vault_path` เป็น path เต็ม, `created_utc` ตามรูปแบบเวลา ไม่เช่นนั้นไม่ใช้
                      (UNKNOWN) · ไฟล์ที่ได้รับยกเว้น (`docs/evidence/ENV-002-sentinel.json`) ยกเว้นเฉพาะกฎ (4) กฎ (3) ยังใช้
                    · (v1.9, r1 F9) detail ของ sentinel บอกชื่อ, ขนาดและ SHA-256 ของ sentinel ที่ตรวจ และ item ที่ค้นไฟล์บอกจำนวน root,
                      โฟลเดอร์, ไฟล์ และ reparse point ที่ข้าม (หลักฐาน L4 ผูกกับ sentinel ที่ commit)
  การค้นทุก item (v1.7, tests-r1 F8): ไม่เข้า reparse point (junction, symlink) เพราะชี้ไปที่อื่น และ junction เก่าของ profile Windows
                    (เช่น `Documents\My Music`) ปฏิเสธการ list · โฟลเดอร์อื่นที่ list ไม่ได้ = UNKNOWN ของทุก item ที่ค้นโฟลเดอร์นั้น
                    · (v1.8) กฎนี้ใช้กับการค้นของ evaluate (repo, data dirs, search_dirs) · การค้น path ของ terminal ใน collect ข้าม
                      โฟลเดอร์ที่ list ไม่ได้ เพราะวัดบนเครื่องเจ้าของ 2026-11-05 แล้วเป็นโฟลเดอร์ระบบที่บัญชีเจ้าของแก้ไม่ได้ (`Program Files\
                      WindowsApps`, `AppData\Local\ElevatedDiagnostics`) ซึ่งถ้านับเป็น UNKNOWN AC-01 จะไม่มีวัน PASS · ที่เหลือ: terminal
                      ในโฟลเดอร์เช่นนั้นหาไม่เจอด้วยกฎ path (กฎ Uninstall entry และโปรเซสยังใช้) · การวางไฟล์ที่นั่นต้องมีสิทธิ์ admin
                    · (v1.9, r1 F2, F3 ทาง (a)) กฎที่ดูแค่ชื่อใช้กับ reparse point ด้วยโดยไม่เข้าไป: โฟลเดอร์ชื่อ holdout, ชื่อ sentinel,
                      `MetaTrader*` ระดับ Program Files และ `terminal64.exe` · reparse point ใต้ repo หรือ data dir = UNKNOWN ของ holdout_dir,
                      excluded_period และ sentinel (โค้ดวิจัยอ่านผ่านมันได้; วัดแล้ว repo ไม่มีเลย) · ใต้ search_dirs อย่างเดียว = ข้าม
                    · (v1.9, r1 F5, F6) root ของการค้น terminal (Program Files*, user profile) ที่ไม่มีหรือ list ไม่ได้ = UNKNOWN (v1.8 ยกเว้น
                      เฉพาะโฟลเดอร์ใต้ root) · root ที่อยู่ใต้โฟลเดอร์ที่มี `terminal64.exe` (ตรวจ ancestor ด้วย stat ไม่ list) ทุกไฟล์ห้ามเปิด ·
                      repo หรือ search dir ใต้ `%APPDATA%\MetaQuotes` ไม่ถูก list (UNKNOWN)
  ค่าที่อ่านไม่ได้ (สิทธิ์, API ล้ม) = UNKNOWN ของ item นั้น

v2.0 (ร่าง, D-023): ตัวอ่านตามแพลตฟอร์ม — Item, Report, Sentinel, กฎของ evaluate และรูปแบบรายงานข้างบนไม่เปลี่ยน เว้นแต่ที่เขียนไว้ตรงนี้
  collect(roots) เลือกตัวอ่านจาก sys.platform:
    "win32"   ตัวอ่าน Windows ของ v1.9 (ไม่เปลี่ยน คงไว้พร้อม tests ที่ล็อก)
    "darwin"  ตัวอ่าน macOS (ใหม่) ตามรายการข้างล่าง
    อื่นๆ      ทุก fact ที่ต้องอ่านจาก OS = อ่านไม่ได้ → `terminal_install`, `terminal_data`, `network_shares` เป็น UNKNOWN (ไม่มีวัน PASS)
              (v1.9 ให้ผลนี้โดยบังเอิญผ่าน `guarded`; v2.0 ทำให้เป็นกฎที่มี test) · tests บน Linux ยังใช้ Facts ปลอมได้ตามเดิม
  (v2.1, F1) Facts, ResearchRoots, Item และ Report ไม่เพิ่ม field (tests ที่ล็อกเทียบชุด field แบบเท่ากันพอดี) · ชื่อตัวอ่านมาจากฟังก์ชันระดับโมดูล
    `reader_name() -> str` (`win32`, `darwin` หรือ `none` จาก `sys.platform` ที่อ่านตอนเรียก) · CLI (`main`) พิมพ์บรรทัด `reader: <ชื่อ>` ก่อนรายการ item
    ทุกแพลตฟอร์ม (`render` ไม่เปลี่ยน) · evaluate ไม่รู้ platform · ขอบเขต: `reader_name()` บอก platform ของโปรเซสที่พิมพ์ ไม่ได้บอกที่มาของ Facts ที่สร้างจากที่อื่น
  (v2.1, F4) ตัวอ่าน darwin เติม Facts เดิม 7 field (กฎของ evaluate ไม่เปลี่ยน):
    terminal_paths          = path ที่พบจากกฎแอป, โฟลเดอร์ `MetaTrader*`, `terminal64.exe` และ path ของ executable ที่รันอยู่ใต้แอปที่ตรงกฎ
    process_names           = ชื่อไฟล์ (basename) ของ executable ทุกโปรเซสที่อ่านได้ · รายการโปรเซสอ่านไม่ได้ตามกฎของ terminal_install
                              (รวมกรณี Wine loader และ `DYLD_*`) → None เท่านั้น (`terminal_paths` ยังเป็นผลของกฎ path)
    uninstall_display_names = `()` เสมอ (ไม่ใช่ None: macOS ไม่มีกฎนี้)
    metaquotes_exists       = มีรายการที่ตรงกฎของ terminal_data · `~/Library/Application Support` list ไม่ได้ → None
    mt5_spec_found          = ผลของ `find_spec` เหมือนทุกแพลตฟอร์ม
    remote_drives           = mount ที่เข้ากฎ FAIL ในรูป `<ชนิด> <ต้นทาง> on <จุด mount>`
    connected_resources     = `()` เมื่อไม่มี mount ใดเข้ากฎ UNKNOWN · None เมื่อมี mount ที่เข้ากฎ UNKNOWN, API ล้ม หรือมี `DYLD_*`
  (v2.1, F4) ฟังก์ชันระดับโมดูลที่ tests เรียกหรือแทนได้ (ไม่เรียก API ของ OS เอง; ชื่อและ signature เป็นข้อผูกของ contract ผู้เขียน tests ที่ต้องการ
    เปลี่ยนให้ถามใน handoff ก่อน):
    find_terminal_paths_darwin(applications, program_files, home, never_listed) -> tuple[str, ...]
    find_wine_program_files(home) -> tuple[Path, ...]
    classify_mounts(entries: tuple[tuple[str, str, str, int], ...]) -> tuple[tuple[str, ...], tuple[str, ...] | None]
        # entry = (ชนิด, ต้นทาง, จุด mount, flags) · คืน (remote_drives, connected_resources)
    classify_processes(paths) -> tuple[tuple[str, ...], tuple[str, ...] | None]      # คืน (terminal_paths ส่วนของโปรเซส, process_names)
    _darwin_application_dirs(home) -> tuple[Path, ...]
    ตัวอ่านดิบ `_darwin_process_paths()` และ `_darwin_mounts()` ที่ tests แทนด้วยตัวปลอม
    · `find_terminal_paths(program_files, user_profile, appdata)` เดิมไม่เปลี่ยน · `collect` และ `default_roots` อ่าน `sys.platform` ตอนถูกเรียก
      (tests ตั้ง `envcheck.sys.platform`)
  (v2.1, F4) กรณี macOS ระดับ collect (แอป, Wine prefix, ระดับของ `terminal64.exe`, โปรเซส, mount, platform อื่น) เป็น tests ที่ล็อกของผู้เขียน tests ใน
    `tests/acceptance/ENV-002/` ซึ่งเรียก `collect` จริงโดยตั้ง `envcheck.sys.platform` และแทนตัวอ่านดิบ (ไม่ใช่ unit test ของ implementer อย่างเดียว
    เพราะงานนี้ High) · ถ้อยคำ detail ของ item ที่มาจาก Facts คงเดิมตาม v1.9 ทุกแพลตฟอร์ม (เช่น `%APPDATA%\MetaQuotes`, `Uninstall entries`,
    `remote drives`); บรรทัด `reader: darwin` และ runbook ฉบับ macOS บอกว่าคำเหล่านั้นหมายถึงอะไรบน Mac
  (v2.1, F4) ค่าที่ Facts 7 field พาไปไม่ได้ (errno, จำนวน pid, จำนวน Wine prefix, โฟลเดอร์ที่ข้าม, ชื่อแอปของ note) ไม่อยู่ใน detail ของ item:
    `main` พิมพ์เป็นบรรทัดของ CLI จากฟังก์ชันระดับโมดูลแยก ไม่ผ่าน Facts (`render`, Report และ Item ไม่เปลี่ยน · token ถูกแทนด้วย `<token>`):
    ก่อนรายการ item ทุกแพลตฟอร์ม:
      reader: <win32|darwin|none>                                                        (F1)
      roots: repo=<path> home=<path> search_dirs=<path>, …                               (F11)
    หลังรายการ item ก่อนบรรทัดสุดท้าย เฉพาะ darwin:
      processes: <n> listed, <n> paths read, <n> skipped, <n> wine loaders               (F7) หรือ processes: unreadable (<เหตุ>, errno <n>, <n> pids)
      mounts: <n> (<ชนิดที่พบ>)                                                           (F7) หรือ mounts: unreadable (<เหตุ>)
      wine: <n> prefixes; looked at <โฟลเดอร์ต้นทางที่มีอยู่ หรือ none>                     (F9)
      skipped: <n> folders (<path>, …)                                                   (F10: โฟลเดอร์ในรายการข้ามที่ list ไม่ได้)
      note: apps <ชื่อแอปที่ตรงรายการของ note หรือ none>                                  (F9)
    บรรทัดสุดท้ายยังเป็น `RESEARCH HOST: <verdict>` ตามเดิม
  default_roots บน darwin:
    user_profile  = โฟลเดอร์ home ของผู้ใช้
    appdata       = ~/Library/Application Support
    program_files = โฟลเดอร์ `drive_c/Program Files*` ของ Wine prefix ที่พบ (ดูชั้นเดียว ไม่ค้นลึก) ใต้
                    ~/Library/PlayOnMac/WinePrefix/* , ~/Library/Application Support/CrossOver/Bottles/* และ ~/.wine
                    · ไม่มี prefix เลย = ไม่มี root ให้ค้น (ไม่ใช่ UNKNOWN: ต่างจาก Windows ที่ Program Files ต้องมีเสมอ)
                    · โฟลเดอร์ต้นทางที่มีอยู่แต่ list ไม่ได้ = UNKNOWN
    search_dirs   = ~/Downloads, ~/Desktop, ~/Documents
                    + ~/Library/Mobile Documents/com~apple~CloudDocs (iCloud Drive) ถ้ามี
                    + ทุกโฟลเดอร์ชั้นแรกใต้ ~/Library/CloudStorage ถ้ามี (OneDrive, Google Drive, Dropbox แบบ File Provider)
  terminal_install (darwin)  FAIL เมื่อพบอย่างใดอย่างหนึ่ง (ชื่อไม่สนตัวพิมพ์):
    · แอปชื่อ `MetaTrader*.app` ชั้นแรกของ /Applications หรือ ~/Applications (ดูชื่อเท่านั้น ไม่เข้าไป; ครอบแอป iPhone/iPad จาก App Store ด้วย)
    · โฟลเดอร์ `MetaTrader*` ชั้นแรกของ program_files แต่ละตัว · `terminal64.exe` ระดับ 0–2 ใต้ program_files แต่ละตัว (helper เดิม)
    · `terminal64.exe` ใต้ home ระดับ 0–3 (ข้าม .git, .venv, node_modules และสองโฟลเดอร์ของ terminal_data)
    · โปรเซสที่รันอยู่ซึ่ง path ของ executable อยู่ใต้โฟลเดอร์ `MetaTrader*.app` หรือชื่อไฟล์เป็น `terminal64.exe`
      (อ่านด้วย libproc: `proc_listallpids`, `proc_pidpath` · API ล้ม = UNKNOWN · โปรเซสที่อ่าน path ไม่ได้เพราะสิทธิ์ = ข้าม)
    · ไม่มีกฎ Uninstall entry บน macOS
  terminal_data (darwin)     FAIL เมื่อมีโฟลเดอร์ใดอยู่ (ตรวจการมีอยู่เท่านั้น ห้าม list หรืออ่านข้างใน; ชื่อไม่สนตัวพิมพ์):
    ~/Library/Application Support/net.metaquotes.wine.metatrader5 · ~/Library/Application Support/MetaTrader 5
    · กฎ "ใต้ `%APPDATA%\MetaQuotes` ห้ามเปิดและไม่ list" ของ v1.9 ใช้กับสองโฟลเดอร์นี้บน darwin
  network_shares (darwin)    อ่านรายการ mount ด้วย `getfsstat` ของ libc:
    FAIL เมื่อมี mount ชนิด smbfs, nfs, afpfs, webdav, ftp หรือ mount ที่ไม่มี flag MNT_LOCAL และชนิดไม่ใช่ autofs หรือ devfs
    · ชนิดที่ไม่อยู่ในรายการ local ที่รู้จัก (apfs, hfs, devfs, autofs, msdos, exfat, udf, cd9660, tmpfs, nullfs) และไม่อยู่ในรายการ remote = UNKNOWN
    · API ล้ม = UNKNOWN
  is_cloud_only (darwin)     True เมื่อ `os.stat(path).st_flags` มี SF_DATALESS (0x40000000)
    · (v2.1, F2) `SF_DATALESS` เป็นค่าคงที่ int `0x40000000` ใน envcheck (แบบเดียวกับ `RECALL_ATTRIBUTES`) ไม่ import `stat`
    · ไฟล์ตัวแทนแบบเก่าชื่อ `.<ชื่อ>.icloud`: ใต้ repo หรือ data dirs = UNKNOWN · ใต้ search_dirs อย่างเดียว = ข้าม
  symlink (ทุกแพลตฟอร์ม; ข้อยกเว้นเดียวของกฎ v1.9 r1 F2/F3):
    symlink ชื่อ `python`, `python3` หรือ `python3.<ตัวเลข>` ที่อยู่ชั้นแรกของ `<repo>/.venv/bin/` และจบที่ไฟล์ธรรมดา (ชี้ตรง หรือผ่าน symlink
    อีกตัวในโฟลเดอร์เดียวกัน) ไม่ทำให้เป็น UNKNOWN และไม่ถูกเปิด (uv สร้างแบบนี้บน macOS และ Linux) · symlink อื่นทุกตัวใต้ repo หรือ data dir
    ยังเป็น UNKNOWN ของ holdout_dir, excluded_period และ sentinel ตามเดิม
  โฟลเดอร์ที่ macOS ไม่ให้ list เพราะ Privacy (TCC, "Operation not permitted") ใช้กฎเดิมของโฟลเดอร์ที่ list ไม่ได้:
    ใน repo, data dirs, search_dirs = UNKNOWN · ใต้ root ของการค้น terminal = ข้าม (v1.8) · root เอง list ไม่ได้ = UNKNOWN (v1.9)
  ctypes บน darwin (v2.1, F3): เปิด library เดียวด้วย `ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)`
    (str literal เต็ม เทียบตรงทุกตัวอักษร ไม่ตัดโฟลเดอร์หรือนามสกุล · ภายในฟังก์ชันเท่านั้น เปิดตอน import = finding เหมือนกฎ Windows
    · ไฟล์นี้ไม่มีบนดิสก์ (dyld shared cache) จึงห้ามตรวจการมีอยู่ก่อนเปิด · วัด 2026-11-17: `CDLL("libproc")` และ `CDLL("libc")` โหลดไม่ได้
    และชื่อเปล่าถูกค้นใน `DYLD_LIBRARY_PATH`, working directory และ `/usr/local/lib` ก่อน `/usr/lib`)
    · เรียกเฉพาะ `<handle>.proc_listallpids`, `<handle>.proc_pidpath`, `<handle>.getfsstat` · อ่าน error ด้วย `ctypes.get_errno()`
    · `os.environ` มีตัวแปรที่ขึ้นต้นด้วย `DYLD_` = โปรเซสและ mount อ่านไม่ได้ (UNKNOWN ของ `terminal_install` และ `network_shares`) และไม่เปิด library
    · `from ctypes import CDLL`, `ctypes.cdll`, `ctypes.util` และ `ctypes.CDLL` ด้วย argument อื่น (รวม `libc.so.6`, ชื่อเปล่า และค่าที่ไม่ใช่ literal)
      ยังเป็น finding ด้วยข้อความเดิมของแต่ละรูป (`forbidden ctypes use ctypes.CDLL`, `… ctypes.cdll`, `… ctypes.util`)
    · mutation ใหม่ที่ต้องถูกปฏิเสธ: `ctypes.CDLL("libproc.dylib")`, `ctypes.CDLL("libSystem.B.dylib")`, `ctypes.CDLL("./libSystem.B.dylib")`,
      `ctypes.CDLL("/tmp/libSystem.B.dylib")`, `ctypes.CDLL(None)`, `<handle>.proc_pidinfo`
    · ยังไม่มี subprocess, socket, http · ไม่เขียน ไม่ลบไฟล์ · ไม่อ่าน Keychain และไม่เรียกโปรแกรม `security`
  CLI (zsh บน macOS): PYTHONPATH=src uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json [--data-dir <path> …]

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
- (v2.0) ไม่ติดตั้ง MT5, Wine หรือแพ็กเกจ `MetaTrader5` บน Mac เพื่อทดสอบ: กรณีของ macOS ทดสอบด้วยโฟลเดอร์ชั่วคราวและ Facts ปลอมเท่านั้น
- (v2.0) agent ไม่อ่าน Keychain, รายการ credential ของ Windows App หรือไฟล์ `.rdp` · การตรวจรหัสที่บันทึกไว้เป็นของเจ้าของ
- (v2.0) tests ที่ล็อกของ v1.9 ไม่ถูกลบ ข้าม หรือทำให้อ่อนลง: (v2.1, F2) ทุกแถวของตารางกรณีที่ล็อก (`_ENVCHECK_FORBIDDEN`, `_ENVCHECK_ALLOWED` และ tests ของ acceptance) คงเดิมพร้อมผลที่คาดไว้ทุกตัวอักษร · ข้อยกเว้นเดียว (คำตัดสินข้อ 2 ของ v2.1): patch ของผู้เขียน tests เพิ่มแถว และแก้ฟังก์ชันกับค่าคงที่ของตัวตรวจ envcheck ใน `tests/architecture/test_imports.py` (อย่างน้อย `_ENVCHECK_CTYPES_DENIED`, `_ENVCHECK_CALLED`, การ resolve handle ของ library และกฎเปิดตอน import) เท่าที่รูป ctypes ของ darwin ใน AC-06 ต้องใช้ · ผู้เขียน tests ระบุทุกฟังก์ชันและค่าคงที่ที่แก้พร้อม diff ใน handoff ให้เจ้าของอนุมัติก่อน apply · จุดอื่นที่ต้องเปลี่ยน รายงานให้เจ้าของตัดสินก่อนแก้ · ถ้า test เดิมขัดกับข้อยกเว้น symlink ของ `.venv/bin/python*` ผู้เขียน tests ต้องรายงานใน handoff ให้เจ้าของตัดสินก่อนแก้

## Negative cases
terminal ติดตั้งอยู่ (Program Files, portable ใต้ profile, Uninstall entry, โปรเซสรันอยู่) · มี `%APPDATA%\MetaQuotes` · `MetaTrader5` import ได้ · มีโฟลเดอร์ holdout · parquet ใน data dir ที่ manifest จบหลัง cutoff / ตรง cutoff (PASS) / ไม่มี manifest / manifest เสีย / manifest ของโฟลเดอร์ที่ไม่มีชื่อไฟล์นั้น · CSV รายงานนอก data dirs (ไม่ตรวจ: PASS) · `.tkc` ใต้ repo · mapped drive หรือ UNC ที่ต่ออยู่ · ไฟล์ที่ hash ตรง sentinel บน Desktop หรือ OneDrive (รวม Desktop ที่ OneDrive ย้ายไป) · สำเนา `.txt` ที่เปลี่ยนชื่อแต่มี token ใต้ `<repo>/data/transfer/` (FAIL) · ไฟล์ `.json` แบบ cloud-only ใน OneDrive ที่ขนาดเท่า sentinel (UNKNOWN และไม่ถูกเปิด) · ไฟล์ `.txt` แบบ cloud-only ใต้ `<repo>/data/` (UNKNOWN และไม่ถูกเปิด) · `.env.json` ข้างสำเนา sentinel (ไม่ถูกเปิด) · ไฟล์ใน repo นอกเหนือ `ENV-002-sentinel.json` ที่มี token (FAIL) · manifest ที่จบหลัง cutoff ในโฟลเดอร์ที่ส่งด้วย `--data-dir` หรือใน `<repo>/data/transfer/` (FAIL) · vault path มีบนเครื่องนี้ · ไม่ให้ sentinel (UNKNOWN) · อ่านไม่ได้เพราะสิทธิ์ (UNKNOWN) · `.env` อยู่ข้างสำเนา sentinel (ต้องไม่ถูกเปิด) · แท่งปลอมของช่วงที่ตัดออกเข้า `run_variant`/`random_entry_baseline` (`HoldoutRefused`, registry ไม่เปลี่ยน)

(v2.0) กรณีของ macOS (โฟลเดอร์ชั่วคราว, Facts ปลอม และฟังก์ชันระดับโมดูลของตัวอ่าน darwin; v2.1, F1, F4): แอป `MetaTrader 5.app` ใน /Applications หรือ ~/Applications (FAIL) · แอปชื่อ `metatrader 5.APP` (FAIL: ไม่สนตัวพิมพ์) · แอปอื่นชื่อ `MetaEditor.app` (PASS) · โฟลเดอร์ `net.metaquotes.wine.metatrader5` หรือ `MetaTrader 5` ใต้ Application Support (FAIL และไม่ถูก list) · `terminal64.exe` ระดับ 2 ใต้ `drive_c/Program Files` ของ prefix ของ PlayOnMac, CrossOver หรือ `~/.wine` (FAIL) และระดับ 3 (PASS) · ไม่มี Wine prefix เลย (PASS ไม่ใช่ UNKNOWN) · โฟลเดอร์ `Bottles` มีอยู่แต่ list ไม่ได้ (UNKNOWN) · โปรเซสที่ path อยู่ใต้ `MetaTrader 5.app` หรือชื่อ `terminal64.exe` (FAIL) · รายการโปรเซสอ่านไม่ได้ (UNKNOWN) · mount ชนิด `smbfs` หรือ `nfs` (FAIL) · mount ชนิดที่ไม่รู้จัก (UNKNOWN) · มีแต่ `apfs`, `devfs`, `autofs` (PASS) · ไฟล์ `.json` ที่มี flag dataless ขนาดเท่า sentinel ใน iCloud Drive (UNKNOWN และไม่ถูกเปิด) · ไฟล์ `.txt` dataless ใต้ `<repo>/data/` (UNKNOWN และไม่ถูกเปิด) · `.<ชื่อ>.icloud` ใต้ data dir (UNKNOWN) · โฟลเดอร์ใน search_dirs ที่ list ไม่ได้เพราะ Privacy (UNKNOWN) · symlink `.venv/bin/python` → ไฟล์ธรรมดา (ไม่ UNKNOWN ไม่ถูกเปิด) · symlink `.venv/bin/python` → โฟลเดอร์ (UNKNOWN) · symlink ชื่ออื่นใน `.venv/bin/` หรือ `python` ที่อยู่ที่อื่นใต้ repo (UNKNOWN) · `collect` จริงบน platform ที่ไม่ใช่ `win32` หรือ `darwin` (UNKNOWN ไม่มีวัน PASS)

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 (v2.0 แทนฉบับ Windows ของ v1.9) Given เครื่อง Mac หลังทำตาม runbook ฉบับ macOS (ไม่มีแอป MetaTrader, ไม่มีโฟลเดอร์ Wine ของ MT5, ไม่มี network volume ที่ mount อยู่, แอปที่ใช้รันคำสั่งได้สิทธิ์ Files and Folders ของ Desktop, Documents, Downloads และ iCloud Drive) และ repo อยู่ที่ commit ที่ตรวจแล้ว (`git rev-parse --short HEAD` ตรงกับที่ Claude ให้ และ `git status --short` ไม่พิมพ์อะไร) When เจ้าของรันคำสั่ง CLI (zsh) ของ contract พร้อม `--sentinel-file docs/evidence/ENV-002-sentinel.json` Then ทุก item เป็น PASS, รายงานมีบรรทัด `reader: darwin` (v2.1, F1), บรรทัดสุดท้ายเป็น `RESEARCH HOST: PASS` และ exit status เป็น 0 · หลักฐานมี commit, เวลา และรายงานทั้งหมด
- AC-01 ฉบับ v1.9 (Windows, เลิกใช้เมื่อ v2.0 อนุมัติ): Given เครื่องเจ้าของหลังทำตาม runbook (ถอน terminal, ลบ `%APPDATA%\MetaQuotes`, ไม่มี mapped drive ไป VPS) When เจ้าของรันคำสั่ง CLI ของ contract พร้อม `--sentinel-file docs/evidence/ENV-002-sentinel.json` Then ทุก item เป็น PASS และบรรทัดสุดท้าย `RESEARCH HOST: PASS`
- AC-02 Given สภาพผิดทีละข้อในโฟลเดอร์ชั่วคราวและ Facts ปลอม (ตามรายการ Negative cases) When `evaluate` Then item นั้นเป็น FAIL หรือ UNKNOWN ตามกฎ, verdict ตามลำดับผลรวม · manifest ที่จบตรง cutoff และ CSV นอก data dirs ผ่าน · ไฟล์ที่ห้ามเปิด (รวม `.env.json` ซึ่งเป็นทั้งไฟล์ต้องห้ามและนามสกุล `.json`) และไฟล์ cloud-only ไม่ถูกเปิด: ตรวจด้วย `sys.addaudithook` ที่ดักเหตุการณ์ `"open"` (ครอบ `builtins.open`, `io.open`, `Path.open`, `os.open`) และทำงานเฉพาะเมื่อ flag ของ test เปิด เพราะ audit hook ถอดไม่ได้ · cloud-only จำลองด้วยการแทน `envcheck.is_cloud_only` · สำเนา `.txt` ที่เปลี่ยนชื่อแต่มี token ใต้ `<repo>/data/transfer/` เป็น FAIL · ไฟล์ `.txt` cloud-only ใต้ `<repo>/data/` เป็น UNKNOWN · ไฟล์ `.txt` cloud-only ใน `--data-dir` ที่อยู่ในโฟลเดอร์ OneDrive ปลอมเป็น UNKNOWN และไม่ถูกเปิด · ไฟล์ `.json` cloud-only ขนาดเท่า sentinel ใน OneDrive เป็น UNKNOWN · ไฟล์ `.png` cloud-only ขนาดเท่า sentinel ใน OneDrive ไม่ทำให้เป็น UNKNOWN · (v2.0; v2.1, F4) When เพิ่มสำหรับกรณีของ macOS: `evaluate`, หรือ `collect` ที่ตั้ง platform เป็น `darwin` พร้อมตัวอ่านดิบปลอม · ทุกกรณีของ macOS ในหัวข้อ Negative cases (รวมกรณีเพิ่มของ v2.1) ให้ผลตามที่เขียนไว้ และไฟล์ dataless กับโฟลเดอร์ของ `terminal_data` ไม่ถูกเปิดหรือ list (ตรวจด้วย audit hook เดิม)
- AC-03 (v2.0 แทนฉบับ Windows ของ v1.9) Given sentinel ที่สร้างบน VPS ด้วย `make_sentinel.py` และค่าที่ commit ใน `docs/evidence/ENV-002-sentinel.json` When เจ้าของทำ break-it test จากเครื่อง Mac (research identity) โดยปิดหน้าต่าง agent ก่อน Then (1) ตัวควบคุม: `nc -z -G 5 <vps> 3389` สำเร็จ (พิสูจน์ว่า IP ถูกและ Mac ออนไลน์อยู่) (2) `nc -z -G 5 <vps> <port>` ที่พอร์ต 22, 80, 443, 445, 5985, 5986 ล้มทั้งหมด (3) Finder → Go → Connect to Server → `smb://<vps>` เชื่อมไม่ได้ (4) เจ้าของตรวจเอง (agent ห้ามทำและห้ามอ่าน Keychain) แล้วยืนยันพร้อมเวลาว่า: Windows App ไม่มี credential ของ VPS ที่บันทึกไว้, Keychain Access ค้นด้วย IP ของ VPS ไม่พบรายการ, browser บน Mac ไม่บันทึกรหัสของ console ผู้ให้บริการ VPS, Mac ไม่มี Windows VM ที่ติดตั้ง MT5 (5) บน VPS `Get-FileHash` ของ sentinel ตรงกับค่าที่ commit ณ เวลาตรวจ (6) item `sentinel` ของ envcheck บน Mac เป็น PASS (7) เครื่อง Windows เดิมตาม D-023 ข้อ 2 (ก): เจ้าของยืนยันทีละข้อพร้อมเวลาว่า ทุก branch และ worktree push แล้ว, ถอน MT5 terminal แล้ว, ลบ `%APPDATA%\MetaQuotes` แล้ว, ลบ clone และ worktree ของ repo แล้ว และไม่เปิด session ของ agent กับโปรเจกต์นี้บนเครื่องนั้นอีก · หลักฐานมีคำสั่ง ผล เวลา และ hash ทั้งสองฝั่ง (IP ปิดบัง)
- AC-03 ฉบับ v1.9 (Windows, เลิกใช้เมื่อ v2.0 อนุมัติ): Given sentinel ที่สร้างบน VPS ด้วย `make_sentinel.py` และค่าที่ commit ใน `docs/evidence/ENV-002-sentinel.json` When เจ้าของทำ break-it test จากเครื่องตัวเอง (research identity) Then `Test-NetConnection <vps>` ที่พอร์ต 22, 80, 443, 445, 5985, 5986 ล้มทั้งหมด (3389 เปิดเป็นประตูของคน) · `dir \\<vps>\C$` และ share ของ vault ล้ม · เจ้าของรัน `cmdkey /list` เอง (agent ห้ามรัน) แล้วยืนยันว่าไม่มีรายการของ VPS · บน VPS `Get-FileHash` ของ sentinel ตรงกับค่าที่ commit ณ เวลาตรวจ · และ item `sentinel` ของ envcheck เป็น PASS · หลักฐานมีคำสั่ง ผล เวลา และ hash ทั้งสองฝั่ง (IP ปิดบัง)
- AC-04 Given `synthetic_bars` ของช่วงที่ตัดออก (2025-01-02) When ส่งเข้า `research.run_variant` และ `research.random_entry_baseline` Then ได้ `HoldoutRefused` และ registry ไม่เปลี่ยน
- AC-05 Given รายงานที่ไม่ใช่ PASS When เรียก `require_research_host` Then ได้ `ResearchHostError` ที่บอกชื่อ item · รายงาน PASS คืนรายงานนั้น · CLI exit 0 เฉพาะ PASS
- AC-06 Given source ของ `sochron.app` และแพ็กเกจเดิม When รัน architecture test Then `research`/`backtest`/`strategy` import `data.acquire`, `broker`, `app` ไม่ได้ · `sochron.app.envcheck` ไม่ใช้ subprocess, socket, http, ไม่เขียน/ลบไฟล์ และใช้ ctypes/winreg เฉพาะฟังก์ชันที่ระบุในหัวข้อ contract · (v1.6, Q12) ตัวตรวจเป็นแบบ static และยอมรับเฉพาะรูปแบบที่ตรวจได้ (เปิด library ด้วยชื่อตรงตัว, เรียก `<handle>.<Function>`, อ่าน error ด้วย `ctypes.get_last_error()`) · รูปแบบอื่นถูกปฏิเสธโดยตั้งใจ · (v1.7, tests-r1 F5) stdlib ที่ envcheck import ได้เป็น allow list: `argparse`, `collections`, `ctypes`, `dataclasses`, `datetime`, `hashlib`, `importlib`, `json`, `os`, `pathlib`, `re`, `sys`, `typing`, `winreg` (ในฟังก์ชันเท่านั้น) · str literal ที่ส่งเป็น sub-key ของ `OpenKey`/`OpenKeyEx` ต้องเป็น Uninstall key ใดใน 2 key · (v2.0; v2.1, F3) ตัวตรวจยอมรับเพิ่มเฉพาะ: การเปิด `ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)` ภายในฟังก์ชัน (str literal เต็ม เทียบตรงทุกตัวอักษร; รูปอื่นของ `CDLL`, `cdll`, `util` ยังเป็น finding ด้วยข้อความเดิม และ mutation ใหม่ในหัวข้อ contract ต้องถูกปฏิเสธ), การเรียก `<handle>.proc_listallpids`, `<handle>.proc_pidpath`, `<handle>.getfsstat`, การอ่าน error ด้วย `ctypes.get_errno()` · (v2.1, F2) allow list ของ stdlib ไม่เปลี่ยน (ไม่เพิ่ม `stat`: กรณีที่ล็อก "forbidden stdlib import stat" คงเดิม) · ชื่อ library หรือฟังก์ชันอื่นถูกปฏิเสธ (ทดสอบด้วย mutation)
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` และ `bash scripts/controls/red-flags.sh main` Then ผ่านทั้งหมด skipped 0, CI เขียว (Linux) และกลุ่ม "Order or account mutation surface" ว่าง · (v2.0) คำสั่งเดียวกันผ่านบนเครื่อง Mac ด้วย โดยตั้ง `PYTHONTZPATH=""` เหมือน CI และจำนวน test ที่ผ่านบน Mac เท่ากับบน CI

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01, 03 | เจ้าของ (เครื่องตัวเองและ VPS) + Claude อ่านผล | runbook → `docs/evidence/ENV-002.md` | L4 |
| 02, 04, 05 | ผู้เขียน tests (Codex หลัง 2026-10-28 19:41 ถ้าใช้ได้ ไม่เช่นนั้น Claude session ใหม่ตามการสลับบทบาท; บันทึกใน PROGRESS ก่อนเริ่ม) | `uv run --offline pytest tests/acceptance/ENV-002 -q -p no:cacheprovider` | L2 |
| 06 | ผู้เขียน tests + ผู้ตรวจ | architecture test + mutation | L2 |
| 07 | Claude + CI | suite + red-flags + run ของ PR | L2/L3 |

(v2.0) AC-01 และ AC-03 ทำบนเครื่อง Mac และ VPS (ข้อ 7 ของ AC-03 ทำบนเครื่อง Windows เดิม) · AC-02 และ AC-06 เพิ่มกรณี macOS ผ่าน patch D-006 ของผู้เขียน tests · AC-07 รันทั้งบน Mac (Claude) และ CI (Linux) · ผู้เขียน tests และผู้ตรวจของ v2.0 ตาม decision (ซ) ข้างล่าง

## Runbook ฉบับ macOS: ข้อที่ต้องมี (v2.1)
ข้อเหล่านี้เป็นส่วนของ Given ใน AC-01 และ AC-03 · Claude เขียนลง `docs/runbooks/ENV-002-research-host.md` ตอน implement · เจ้าของเป็นผู้ทำ
- (F3) ก่อนรอบหลักฐานของ AC-01: ลบ `.venv` แล้วสร้างใหม่ด้วย `uv sync --locked` (ไฟล์ `.pth` ใน `.venv` ซึ่งถูก gitignore รันอยู่ในโปรเซสของ envcheck) · shell ที่รันไม่มีตัวแปรที่ขึ้นต้นด้วย `DYLD_` (`env | grep '^DYLD_'` ไม่พิมพ์อะไร)

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
| (v2.0) เครื่อง Windows เดิมยังถือ terminal และ cache ของช่วงหลัง cutoff | เจ้าของคัดลอกไฟล์ข้ามเครื่อง (USB, AirDrop, cloud) · เปิด agent บนเครื่องนั้นตามความเคยชิน | D-023 ข้อ 2 (ก) และ AC-03 ข้อ 7 · item `holdout_dir`, `excluded_period`, `sentinel` บน Mac จับไฟล์ที่เข้ามาใน repo, data dirs และ search_dirs | ระหว่างรอ SPIKE-002 เครื่องนั้นยังมี terminal: กฎคือไม่เปิด agent ของโปรเจกต์บนเครื่องนั้น ซึ่งเป็นคำยืนยันของเจ้าของ โค้ดตรวจไม่ได้ |
| (v2.0) MT5 บน Mac ที่กฎ path ไม่เห็น | Wine prefix ที่อื่น (เช่น Whisky), Windows VM, web terminal ของโบรกเกอร์ใน browser | กฎชื่อแอป, prefix ที่รู้จัก, home ระดับ 0–3, โปรเซสที่รันอยู่ · คำยืนยันเรื่อง VM ใน AC-03 ข้อ 4 | **รับไว้:** prefix ที่อื่นและ VM ที่ไม่ได้รันอยู่ตรวจไม่เจอ · web terminal เปิดได้จาก browser ใดก็ได้ จัดเป็นความเสี่ยงเดียวกับแถว "ข้อมูลราคาสาธารณะ" |
| (v2.0) สิทธิ์ Privacy ของ macOS กว้างเกิน | ให้ Full Disk Access แก่แอปที่ agent รันอยู่ด้วย | runbook ให้เฉพาะ Files and Folders ของ Desktop, Documents, Downloads และ iCloud Drive (decision (ช)) | agent ที่รันในแอปเดียวกันอ่านโฟลเดอร์เหล่านั้นได้เท่ากับตัวตรวจ |
| (v2.1, F3) library หรือโค้ดที่ถูกวางให้ตัวตรวจโหลด | ตัวแปร `DYLD_*`, ไฟล์ library ใน working directory, ไฟล์ `.pth` ใน `.venv` | เปิด library ด้วย path เต็มตัวเดียว · มี `DYLD_*` = UNKNOWN · สร้าง `.venv` ใหม่ก่อนรอบหลักฐาน | ไฟล์ `.pth` ที่ถูกวางหลังสร้าง `.venv` ใหม่และก่อนรัน ตรวจไม่เจอ (เหมือน v1.9) |

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

### Plan v2.0 (ร่าง 2026-11-17, D-023)
1. Understanding: research host เปลี่ยนเป็นเครื่อง Mac ตัวตรวจเดิมจึงต้องอ่านข้อเท็จจริงของ macOS ได้ และเครื่อง Windows เดิมต้องออกจากโปรเจกต์อย่างตรวจได้ · ข้อกำหนดของข้อ 6.1 และกฎของ evaluate ไม่เปลี่ยน · เข้าใจผิดที่เป็นไปได้: ติดตั้ง MT5 บน Mac เพื่อดู path จริง (ห้าม) · รื้อตัวอ่าน Windows และ tests ที่ล็อก · ให้ agent อ่าน Keychain แทน `cmdkey` · ให้ Full Disk Access เพื่อให้ผ่านเร็ว · ถือว่า PASS บน Mac แล้วเครื่อง Windows ไม่ต้องล้าง
2. Files / reuse: `src/sochron/app/envcheck.py` (เพิ่มตัวอ่าน `darwin`, ใช้ helper ค้น `terminal64.exe` และกฎ evaluate เดิม) · `tests/unit/app/**` · `docs/runbooks/ENV-002-research-host.md` (ข้อ 2–4 ฉบับ macOS, ข้อ 1 และ 5 บน VPS คงเดิม) · patch D-006 ของผู้เขียน tests สำหรับ `tests/acceptance/ENV-002/**` และ `tests/architecture/**`
3. Steps, each with its check:
   1. contract review ของ v2.0 และ D-023 โดย session ใหม่ (ตรวจ path ของ MT5 บน macOS จากหน้าทางการ, รายการชนิด mount, flag dataless, ขั้นของ Windows App) → แก้ตาม finding → เจ้าของอนุมัติ (High) และเลือก D-023 ข้อ 2 · check: review file ใน `docs/reviews/` ว่าพร้อม และบรรทัด Status ของ contract
   2. บันทึกผู้เขียน tests และผู้ตรวจใน PROGRESS → ผู้เขียน tests ส่ง patch ของกรณี macOS และ allow list → Claude apply ตาม D-006 และตรวจ hash → review ของ tests → red · check: tests ใหม่ล้มก่อนมีโค้ด และ tests เดิมยังผ่าน
   3. Claude implement ตัวอ่าน macOS, unit tests และ runbook ฉบับ macOS · check: suite ผ่านบน Mac ด้วย `PYTHONTZPATH=""`, red-flags 0, mypy ของแพ็กเกจ
   4. review งานโดย session ใหม่ รวมการตรวจซ้ำ F12–F15 ของ `ef7881e` ที่ยังไม่มีใครตรวจ → แก้ทีละ finding · check: review ว่าพร้อมรัน L4
   5. เจ้าของเปิด draft PR เพื่อให้ CI รันบน Linux (ยังไม่ merge) · check: `python-tests` และ `control-plane` เขียว
   6. หลัง ENV-001 และ SPIKE-002 ผ่าน: เจ้าของทำ runbook (sentinel บน VPS → envcheck บน Mac → break-it → เครื่อง Windows เดิม) · check: AC-01 และ AC-03 ครบทุกข้อพร้อม commit และเวลา
   7. evidence review → เจ้าของ label และ merge · บันทึก "ENV-1 ผ่าน"
4. Risks: path ของ MT5 บน macOS เปลี่ยนตามรุ่นของ MetaQuotes หรือวิธีติดตั้ง (ลดด้วยกฎชื่อแอปและโปรเซส; ทบทวนตาม D-023) · โปรเซสที่รันใต้ Wine อาจไม่แสดงชื่อ `terminal64.exe` ใน libproc (ทดสอบจริงไม่ได้เพราะห้ามติดตั้ง: เขียนเป็นข้อที่เหลือ) · การค้น home ระดับ 0–3 ช้าเพราะ `~/Library` ใหญ่ · สิทธิ์ Privacy ที่ยังไม่ให้ทำให้ได้ UNKNOWN ครั้งแรก (runbook บอกวิธีให้สิทธิ์) · control self-tests บน Mac ยังล้ม 2 จาก 76 จนกว่างาน FIX แยกจะเสร็จ: ไม่ใช่เงื่อนไขของ AC-07 แต่ต้องรายงานตามจริง · ไฟล์ `docs/proposals/` และ memory จากเครื่อง Windows ยังไม่ได้ย้ายมา ผู้เขียน tests อาจต้องใช้ patch เดิมอ้างอิง
5. Decisions needed from the owner (v2.0):
   - (จ) อนุมัติ contract v2.0 (High) และรับ D-023 · (v2.1, F2) การอนุมัตินี้รวมข้อยกเว้นเดียวของ invariant "tests ที่ล็อกของ v1.9": การแก้ตัวตรวจ ctypes ของ envcheck ใน `tests/architecture/test_imports.py` แบบแคบตามหัวข้อ Invariants
   - (ฉ) เครื่อง Windows เดิม · **แนะนำ:** D-023 ข้อ 2 (ก) เลิกใช้กับโปรเจกต์นี้และล้าง หลัง SPIKE-002 ผ่าน
   - (ช) สิทธิ์ Privacy บน Mac · **แนะนำ:** ให้ Files and Folders เฉพาะ Desktop, Documents, Downloads และ iCloud Drive แก่แอปที่ใช้รัน envcheck ไม่ให้ Full Disk Access
   - (ซ) ผู้เขียน tests และผู้ตรวจของ v2.0 · **แนะนำ:** Codex ตาม D-002 ถ้าใช้ได้บน Mac (งาน High ต้องมี tests และ review จาก Codex ตาม `docs/HANDBOOK-CORE.md` ข้อ 5) · ถ้าใช้ไม่ได้ ใช้ Claude session ใหม่คนละ session และบันทึกการสลับบทบาทใน PROGRESS ก่อนเริ่ม
   - (ฌ) การตรวจซ้ำ F12–F15 · **แนะนำ:** รวมไว้ใน review งานของ v2.0 (ขั้นที่ 4) แทนการรอถึงหลัง L4

### คำตัดสินของ v2.1 ตามการมอบอำนาจของเจ้าของ 2026-11-18
เจ้าของสั่งในแชท Claude 2026-11-18 หลังได้รับคำถาม 13 ข้อของ `docs/reviews/ENV-002-contract-v2-r1.md`: "อันไหนที่ว่าดีมึงตัดสินใจเองไปเลย แล้วก็พุทบันนี้หรือไม่แล้วแต่มึง เอาง่ายเอาให้มันดีที่สุด มึงตัดสินใจทำเองเลย" · Claude จึงเลือกทางที่ review แนะนำทุกข้อ และข้อที่ review ไม่ได้แนะนำ เลือกทางที่ fail-closed กว่า (เพิ่มได้แค่ UNKNOWN หรือ FAIL ไม่เพิ่ม PASS) หรือทางที่งานของเจ้าของน้อยกว่าเมื่อผลด้านความปลอดภัยเท่ากัน · **การมอบอำนาจนี้ไม่ใช่การอนุมัติ contract:** v2.1 ยังต้องผ่าน contract review และเจ้าของยังต้องอนุมัติ (จ) เอง · เจ้าของกลับคำตัดสินข้อใดก็ได้ก่อนอนุมัติ · ความเสี่ยงที่เหลือในตาราง threat model เจ้าของเป็นผู้รับเมื่ออนุมัติ Claude ไม่ได้รับแทน

| คำถามของ review r1 | คำตัดสิน | เหตุผล |
|---|---|---|
| 1 (F1) field `platform` | ไม่เพิ่ม field · CLI พิมพ์บรรทัด `reader:` | ทางที่แนะนำ: ไม่แตะ test ที่ล็อก |
| 2 (F2) ข้อยกเว้นของตัวตรวจ ctypes ที่ล็อก | รับข้อยกเว้นแบบแคบ (ทาง (i)) · เจ้าของยังอนุมัติ diff ของผู้เขียน tests ก่อน apply | ไม่มีข้อยกเว้นนี้ ตัวอ่าน darwin อ่านโปรเซสและ mount ไม่ได้เลย |
| 3 (F3) ชื่อ library, `DYLD_*`, `.venv` | literal เดียว `/usr/lib/libSystem.B.dylib` · มีตัวแปร `DYLD_*` = UNKNOWN · สร้าง `.venv` ใหม่ก่อนรอบหลักฐาน | ทางที่แนะนำ และทางที่ fail-closed กว่าของ `.venv` |
| 4 (F6) โฟลเดอร์ dataless | ไม่ list และเป็น UNKNOWN (ทาง (i)) | ทางที่การรวม review แนะนำ: ตัวตรวจไม่ทำให้ macOS ดึงข้อมูลจาก cloud |
| 5 (F7) รอบควบคุม และ Wine | ทำรอบควบคุมด้วยโฟลเดอร์เปล่าสองตัวก่อนรอบ PASS · เพิ่มกฎ Wine loader = UNKNOWN พร้อมแก้ถ้อยคำข้อที่เหลือ | รอบควบคุมแนะนำ · กฎ Wine เพิ่มได้แค่ UNKNOWN |
| 6 (F8, F9) `/var/db/receipts` · Wine, VM, container | ไม่เพิ่มกฎ receipts · ใช้ note ที่ไม่เปลี่ยน verdict พร้อมคำยืนยันซ้ำ (ทาง (ii)) | ยังไม่มีใครยืนยันชื่อ receipt ของ MT5 กฎที่ตั้งบนชื่อเดาให้ PASS ที่ไม่มีความหมาย · ทาง (ii) แนะนำ |
| 7 (F10) แอปและรายการข้าม | แอปที่เริ่ม R1 และรัน envcheck คือ Visual Studio Code (แอปที่ Claude Code ทำงานอยู่ วัด 2026-11-18) · Claude วัดการค้น home ในแอปนั้นแล้ว รายการข้ามอยู่ในหัวข้อ contract · การค้น home ไม่เข้า `~/Library` ทั้งโฟลเดอร์ | เจ้าของไม่ต้องรันเอง · ที่รู้จักใต้ `~/Library` ตรวจด้วยกฎ terminal_data และ Wine prefix อยู่แล้ว |
| 8 (F11) ชื่อบัญชี macOS ในหลักฐาน | ยอมให้อยู่ในบรรทัด `roots:` | ชื่อเดียวกับชื่อบัญชี GitHub ของ repo ซึ่งอยู่ใน remote URL อยู่แล้ว |
| 9 (F13) รันตัวอ่าน Windows บนเครื่องเดิม | ไม่ทำ | เครื่องนั้นเลิกเป็น research host แล้ว และการรันต้องตั้งค่า sentinel บนเครื่องที่กำลังจะล้าง: งานเพิ่มโดยไม่เปลี่ยนผลของด่าน |
| 10 (F15) สำเนา cache ของ MT5 | เพิ่มกฎ mount ใต้ `/Volumes/` = UNKNOWN และกฎย้ายไฟล์ด้วยรายการชื่อพร้อม SHA-256 เท่านั้น · ไม่เพิ่มกฎนามสกุล cache ใน search_dirs | กฎ `/Volumes` ไม่แตะ evaluate ของ Windows · กฎนามสกุลต้องแก้ evaluate ทุกแพลตฟอร์มและ tests ที่ล็อก · สำเนาใน Downloads ยังเป็นข้อที่เหลือ |
| 11 (F17) D-021 และ D-023 ข้อ 2 | เพิ่มบรรทัดอ้างกลับใต้ D-021 · ยืนยันทาง 1 (เลิกใช้และล้างเครื่อง Windows หลัง SPIKE-002 ผ่าน) | ทางที่แนะนำ และ contract เขียนตามทางนี้อยู่แล้ว |
| 12 (F19, F23, F24) | ไม่ต่อ external disk, disk image หรือ network volume ระหว่างรัน · งบ session ใหม่ 8 และ lens ขนานของ pre-review หนึ่งรอบนับเป็นหนึ่ง session · งาน v2.x ทั้งหมดอยู่บน branch `chore/ENV-002-macos-research-host` | สอดคล้องกับกฎ `/Volumes` · ตัวเลขที่ review เสนอ · branch นี้มี commit ของ `feat/ENV-002-research-host-separation` ครบถึง `c97aac6` |
| 13 ผู้ตรวจ contract ตัวจริง | Claude session ใหม่คนละ session (ผู้ตรวจที่เห็นเฉพาะ contract, review และ diff) ตามการสลับบทบาทที่บันทึกใน PROGRESS ตั้งแต่ ENV-001 r3 | Codex บน Mac ยังไม่ผ่านการตรวจการตั้งค่า (P25 บน macOS เป็นงานตามของ D-023) · ผู้ทำและผู้ตรวจไม่ใช่ session เดียวกัน |

## Authorization (filled by the owner)
| รายการ | ค่า |
|---|---|
| actor | เจ้าของ (ลบ terminal และโฟลเดอร์ข้อมูลบนเครื่องตัวเอง, สร้าง sentinel บน VPS, รันตัวตรวจและ break-it test, รัน `cmdkey /list` เอง) · Claude (เขียนโค้ดและ runbook, commit ค่าของ sentinel) |
| action | ตรวจแบบอ่านอย่างเดียวบนเครื่องเจ้าของ · สร้างไฟล์ปลอมบน VPS · ไม่มีการเชื่อมต่อโบรกเกอร์ |
| target | เครื่องเจ้าของ (research host), vault path บน VPS |
| valid until | TBD (เจ้าของกรอก) |

(v2.0) target เปลี่ยนเป็น: เครื่อง Mac (research host), เครื่อง Windows เดิม (ล้างครั้งเดียวตาม D-023 ข้อ 2), vault path บน VPS · actor เพิ่ม: เจ้าของตรวจ credential ของ Windows App และ Keychain เอง (แทน `cmdkey /list`) · valid until ยัง TBD

## Budget
2 sessions ของ Claude · headless session ไม่เกิน 5 (ผู้เขียน tests, ผู้ตรวจ tests, ผู้ตรวจงาน, สำรอง ×2) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

(v2.0) งบของ v1.x ใช้ครบแล้ว (headless 5/5) · งบใหม่ของ v2.0: 2 sessions ของ Claude · session ใหม่ไม่เกิน 5 (ผู้ตรวจ contract, ผู้เขียน tests, ผู้ตรวจ tests, ผู้ตรวจงาน, สำรอง ×1) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
ติดตั้ง MT5 ใหม่บนเครื่องเจ้าของได้ถ้าต้องย้อน (ENV-1 จะไม่ผ่านจนกว่าจะถอนอีกครั้ง) · ลบไฟล์ sentinel บน VPS ได้หลังบันทึกหลักฐาน (แล้วค่าที่ commit ใช้ไม่ได้: ต้องสร้างใหม่และ commit ใหม่) · revert PR

(v2.0) ถ้าเจ้าของไม่รับ D-023 หรือ v2.0: ลบ branch `chore/ENV-002-macos-research-host` แล้ว v1.9 ยังใช้ได้ตามเดิมบนเครื่อง Windows · การลบ clone และโฟลเดอร์ของ terminal บนเครื่อง Windows ย้อนไม่ได้: ทำหลังยืนยันว่า push ครบและย้าย `docs/proposals/` กับ memory พร้อมตรวจ SHA-256 แล้วเท่านั้น · ตัวอ่าน Windows ยังอยู่ในโค้ด ถ้ากลับไปใช้ Windows เป็น research host ต้องตัดสินใหม่ตาม D-023 "Review when"

## DoR status / missing items / next action
ครบ: เจ้าของอนุมัติ (ก)–(ง) และ D-021 2026-10-25 17:5x · ขาด: ENV-001 และ SPIKE-002 ผ่าน, valid until · ผู้ตรวจรอบถัดไปตรวจซ้ำ F51 · next: หลัง ENV-001 และ SPIKE-002 ผ่าน (tests ของ ENV-002 เขียนได้ก่อน)

(v2.0) ครบ: เจ้าของเลือกทิศทาง "Mac เป็น research host" ในแชท 2026-11-17 · ข้อเท็จจริงของ Mac วัดแล้ว (หัวข้อ Current behavior) · ขาด: contract review ของ v2.0 และ D-023, การอนุมัติของเจ้าของ (จ)–(ฌ), การยืนยัน path ของ MT5 บน macOS จากหน้าทางการ, valid until, การย้าย `docs/proposals/` และ memory จากเครื่อง Windows, ENV-001 และ SPIKE-002 ผ่าน (สำหรับ L4) · ร่างนี้ยังไม่ commit · next: เจ้าของอ่าน AC-01 และ AC-03 ฉบับ v2.0 แล้วสั่ง contract review

## Done scope
operation: เครื่องเจ้าของเป็น research host ที่ตรวจได้ · ENV-1 ผ่านเมื่อ ENV-001, SPIKE-002 และ ENV-002 ผ่านครบ และเจ้าของบันทึกการตัดสินที่ D-021 และ SPIKE-002 AC-04 ต้องการ · (v2.0) "เครื่องเจ้าของ" คือเครื่อง Mac และเครื่อง Windows เดิมออกจากโปรเจกต์แล้วตาม AC-03 ข้อ 7
