# TASK ENV-002 — แยก research host ออกจาก terminal และ holdout พร้อม synthetic excluded-period sentinel

Version v2.3 draft (ประวัติ: v1 ร่าง 2026-10-25 → v1.1 ตอบ `docs/reviews/ENV-contracts-r1.md`: research identity และ break-it test (F1), OneDrive (F3), ความหมายของ "ผ่าน data" และงานที่ส่งต่อ (F7), คำสั่งที่รันได้จริง (F8), นิยามที่ผู้เขียน tests ต้องใช้ (F9), ขอบเขตของ excluded_period (F11), การค้น sentinel ที่ไม่อ่านไฟล์ลับ (F12), terminal ที่ติดตั้งที่อื่น (F13), ความสอดคล้อง (F20) → v1.2 ตอบ `docs/reviews/ENV-contracts-r2.md`: การประเมิน holdout เป็นงานส่งต่อ (F7), ที่อยู่ของตัวสร้างแท่งปลอม (F9), เอกสารที่แก้ตอนบันทึก ENV-1 ผ่าน (F20), โฟลเดอร์รับไฟล์ของ D-021 (F29), shell folder/ขอบเขตของ hash/token (F30), ความเสี่ยงของ RDP ที่เปิดอยู่ (F32) → v1.3 ตอบ `docs/reviews/ENV-contracts-r3.md`: ขอบเขตการค้น token และไฟล์ cloud-only (F36), ขั้นตอนโหลด `synthetic.py` (F37), `ResearchRoots` ชุดเดียวของ R1 (F43 a), ป้ายเวอร์ชัน (F44) → v1.4 ตอบ `docs/reviews/ENV-contracts-r4.md` (ทุกข้อ Low): ไฟล์ cloud-only ใน repo/data dirs (F49), จุดที่ tests แทนและการดักการเปิดไฟล์ (F50) → v1.5 ตอบ `docs/reviews/ENV-contracts-r5.md` (Low): ไฟล์ที่อยู่ทั้งใต้ data dirs และ search_dirs (F51) → **v1.6 ตอบคำถามของผู้เขียน tests (`docs/handoff/ENV-002.md` Q2–Q12) อนุมัติโดยการมอบอำนาจ 2026-11-05 15:0x:** ระดับของการค้น terminal และ helper ที่ทดสอบได้ (Q2, Q3), ไม่สนตัวพิมพ์ (Q4), data dir ที่ไม่มีอยู่ (Q5), ไฟล์ห้ามเปิดที่กฎค้นต้องเปิด = UNKNOWN (Q6), รายงานไม่พิมพ์ token (Q7), vault_path (Q8), `default_roots` และ `main` (Q9), ค้นรวม `.git`/`.venv` (Q11), ขอบเขตของตัวตรวจ AC-06 (Q12) → **v1.7 ตอบ `docs/reviews/ENV-002-tests-r1.md` F2, F5–F8 อนุมัติโดยการมอบอำนาจ 2026-11-05 17:4x:** manifest ที่เป็น cloud-only (F2), allow list ของ stdlib และ sub-key ของ registry (F5), token แบบ UTF-16 (F6), token ใน stderr และข้อความ error (F7), โฟลเดอร์ที่ list ไม่ได้และ reparse point (F8) → **v1.8 (implementer, อนุมัติโดยการมอบอำนาจ 2026-11-05 17:5x):** การค้น path ของ terminal ข้ามโฟลเดอร์ระบบที่ list ไม่ได้ ตามที่วัดบนเครื่องเจ้าของ → **v1.9 ตอบ `docs/reviews/ENV-002-r1.md` F1–F9 อนุมัติโดยการมอบอำนาจ 2026-11-05 19:3x:** data dir ที่ครอบ repo (F1), reparse point (F2, F3 ทาง (a)), root และค่าที่อ่านไม่ได้ (F5, F6), ไฟล์ค่าของ sentinel (F7), manifest สองแบบ (F8), detail ที่เป็นหลักฐาน (F9) → **v2.0 ร่าง 2026-11-17 (ยังไม่อนุมัติ): research host เป็นเครื่อง Mac ตาม D-023 (proposed)**: research identity บน macOS, ตัวอ่าน darwin ใน envcheck, AC-01 และ AC-03 ฉบับ macOS, เครื่อง Windows เดิม, runbook ฉบับ macOS · ทุกจุดที่เปลี่ยนติดป้าย "(v2.0)" → **v2.1 ร่าง 2026-11-18 (ยังไม่อนุมัติ) ตอบ `docs/reviews/ENV-002-contract-v2-r1.md` F1–F24** ด้วยทางที่แนะนำตามการมอบอำนาจของเจ้าของ 2026-11-18 (หัวข้อ "คำตัดสินของ v2.1"): ไม่เพิ่ม field ใน Facts (F1), ข้อยกเว้นแบบแคบของตัวตรวจ ctypes ที่ล็อก (F2), library literal เดียว (F3), การ map ลง Facts 7 field และจุดที่ tests แทนได้ (F4), กฎที่รัดขึ้นของ symlink, cloud, โปรเซส, ชื่อโฟลเดอร์, Wine/VM, Privacy, home (F5–F12), AC-03 และ checklist ของเจ้าของ (F13, F14), สำเนา cache (F15), ถ้อยคำเก่าและ D-023 (F16–F24) · ทุกจุดที่เปลี่ยนติดป้าย "(v2.1, F<n>)" → **v2.2 ร่าง 2026-11-18 (ยังไม่อนุมัติ) ตอบ `docs/reviews/ENV-002-contract-v2-r2.md`** (ไม่มี High; Medium 8, Low 19): ตัวอ่านดิบและฟังก์ชัน pure ที่ถือกฎ (r2 F4, F7), `host_lines()` (F25), บรรทัด `tools:` และการเทียบของ R1 (r2 F9), การค้นใน Wine prefix (r2 F10), กรณีที่ขาด (r2 F12), checklist ข้อ C9 (r2 F14), การวัด search_dirs (F27), กฎ mount (F26, F31, F32), ข้อ Low ที่เหลือและ decision (ญ) · ทุกจุดที่เปลี่ยนติดป้าย "(v2.2, r2 F<n>)" หรือ "(v2.2, F<n>)" สำหรับข้อใหม่ F25–F41 → **v2.3 ร่าง 2026-11-18 (ยังไม่อนุมัติ) ตอบ `docs/reviews/ENV-002-contract-v2-r3.md`** (ไม่มี High; Medium 1, Low 13): สถานะของ `host_lines()` ถูกล้างทุกครั้งที่ `research_host_report` ทำงาน, แหล่งของทุกบรรทัด และค่าที่คืนพาตัวเลข (r3 F25), รูปของทุกบรรทัด (F48), รายการอนุญาตของจุด mount แคบลง (r3 F32), กฎ path ของโปรเซสแบบเข้ม (r3 F33), symlink ของ Wine (F43), `MNT_LOCAL` (F44), รายการฐานของกรณี mount (F45), รอบตรวจบนเครื่อง Windows เดิมใช้โค้ด v1.9 (F46), ข้อ Low ที่เหลือ · ทุกจุดที่เปลี่ยนติดป้าย "(v2.3, r3 F<n>)") · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 6.1 ("ด่านก่อน SLICE-R1"), 9, 13a · D-017, D-019, D-020, D-021, D-023 (proposed) · Tier **High** · Branch (v2.1, F24, คำตัดสินข้อ 12) งาน v2.x ทั้งหมดอยู่บน `chore/ENV-002-macos-research-host` ซึ่งต่อจาก `feat/ENV-002-research-host-separation` ที่ `c97aac6` (branch `feat/…` เป็นบันทึกของ v1.9 และไม่มี commit ใหม่อีก) · runbook ข้อ 1 fetch branch `chore/ENV-002-macos-research-host`
Status: **v2.3 draft 2026-11-18: ตอบ review r1 (24 ข้อ), r2 (27 ข้อ) และ r3 (14 ข้อ) ครบ รอการตรวจซ้ำของ r3 (ถ้าเจ้าของสั่ง) และการอนุมัติของเจ้าของ (High) · ฉบับที่อนุมัติล่าสุดคือ v1.9 ซึ่งโค้ดและ tests บน branch ทำตาม** · ประวัติ v1.x: **approved by owner 2026-10-25 17:5x; v1.6 approved by delegation 2026-11-05 15:0x; v1.7 approved by delegation 17:4x; v1.8 approved by delegation 17:5x; v1.9 approved by delegation 19:3x** (v1.9: ทางที่แนะนำของ `docs/reviews/ENV-002-r1.md` F1–F9 รวม F3 ทาง (a) และ F8 "ผ่านทั้งสอง") (v1.7: ทางที่แนะนำ (a) ของ tests-r1 F5–F8 และข้อเสนอของ F2 ตามการมอบอำนาจเดียวกัน) · (v1.6: เจ้าของสั่ง 13:4x "อนุมัติตาม recommended ไปเลย" จึงใช้ทางที่แนะนำของ Q2–Q12 ทุกข้อ เลือกทาง fail-closed; เจ้าของ veto ได้ก่อน merge · branch จริงคือ `feat/ENV-002-research-host-separation` ตามหัวข้อนี้) · (v1.5 · เจ้าของตอบ "อนุมัติทั้งหมด" ในแชท Claude: contract นี้, การตัดสิน (ก)–(ง) ตามที่แนะนำ และ D-021 · review r5 ว่าพร้อม · ข้อ Low F51 ของ r5 แก้ใน v1.5 ให้ผู้ตรวจรอบถัดไปตรวจซ้ำ) · เริ่มได้หลัง ENV-001 และ SPIKE-002 ผ่าน
Hypothesis (research tasks): ไม่ใช่งานวิจัย

ด่าน ENV-1: ENV-001 → SPIKE-002 → **ENV-002**

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: **yes** — งานนี้คือขอบเขตระหว่าง research identity กับ holdout
- Q2 real money: no
- Q3 new storage/transfer of personal or confidential data: no — sentinel เป็นข้อมูลปลอม
- Q4 schema change or deletion of real data: **yes** — เจ้าของถอน MT5 terminal และลบโฟลเดอร์ข้อมูลของ terminal บนเครื่องตัวเอง · (v2.0) เครื่องที่ถูกล้างคือเครื่อง Windows เดิม รวมการลบ clone และ worktree ของ repo บนเครื่องนั้น (D-023 ข้อ 2)
- Q5 hard-to-reverse external effect: no (v1.9: ติดตั้งใหม่บนเครื่อง Windows ได้ · v2.1, F16: การลบ clone และโฟลเดอร์ของ terminal บนเครื่อง Windows ย้อนไม่ได้ แต่ไม่ใช่ผลภายนอก)
- Q6 changes controls: no สำหรับ hooks/CI · เพิ่มกฎใน `tests/architecture` (ล็อก) ผ่าน patch ของผู้เขียน tests ตาม D-006 · (v2.2, r2 F24) patch ของ v2.x แก้ฟังก์ชันและค่าคงที่ของตัวตรวจ ctypes ที่ล็อกแบบแคบด้วย: เจ้าของอนุมัติ diff ก่อน apply (หัวข้อ Invariants)

**High** ตาม Q1, Q4

## นิยาม
- **research identity** = (v2.0, D-023) บัญชีผู้ใช้ macOS ของเจ้าของบนเครื่อง Mac ซึ่งเป็น research host เครื่องเดียว (v1.9 เดิม: บัญชีผู้ใช้ Windows บนเครื่อง Windows) รวมทุกโปรเซสที่ agent (Claude Code, Codex) เปิด · (v2.0) บน macOS โปรแกรม RDP คือ Windows App และการมองเห็นหน้าจอหรือส่ง input ข้ามแอปต้องมีสิทธิ์ Screen Recording/Accessibility ของแอปที่ agent รันอยู่ ซึ่งโค้ดตรวจไม่ได้ จึงคงกฎของ decision (ค) ตามเดิม · การเข้า VPS ผ่าน RDP แบบ interactive ของเจ้าของเป็น **ประตูของคน**: รหัสผ่าน RDP ต้องไม่ถูกบันทึกบนเครื่องนี้ และ **ขณะที่หน้าต่าง RDP เปิดอยู่ โปรเซสของ research identity มองเห็นและส่ง input เข้าหน้าต่างนั้นได้** (v2.1, F24: บน Windows เพราะผู้ใช้, session และ integrity เดียวกัน · บน macOS เมื่อแอปของ agent มีสิทธิ์ Screen Recording หรือ Accessibility) จึงต้องเปิด RDP เฉพาะเมื่อไม่มี session ของ agent รันอยู่ (decision (ค))
- **ช่วงที่ตัดออก** = ข้อมูลตลาดตั้งแต่ `HOLDOUT_CUTOFF_UTC` (2025-01-01 00:00 UTC) · `period_end_utc` เป็นจุดสิ้นสุดแบบไม่รวม ความหมายเดียวกับ `research.Dataset`
- **"อ่านหรือดึงไม่ได้ ทั้งโดยตรงและผ่าน data" ที่ ENV-1** (architecture ข้อ 6.1) = (1) โดยตรง: research identity ไม่มีไฟล์ช่วงที่ตัดออก ไม่มี share/drive ไป VPS ไม่มีพอร์ตอื่นนอกจาก RDP และไม่มี credential ของ VPS (break-it test, AC-03) (2) ดึงจากโบรกเกอร์: ไม่มี terminal และ `MetaTrader5` บนเครื่องนี้ (3) ผ่านโค้ด: `research` ปฏิเสธแท่งของช่วงนั้น (`HoldoutRefused`) และ `research`/`backtest`/`strategy` import `data.acquire`, `broker`, `app` ไม่ได้ · loader ของ R1 ที่ยังไม่มีเป็นงานส่งต่อ (หัวข้อ "งานที่ส่งต่อ")

## Goal / user outcome (Thai)
เครื่องเจ้าของเป็น research host ตามข้อ 6.1 ที่พิสูจน์ได้:
- ไม่มี MT5 terminal (ทั้งแบบติดตั้งและแบบ portable), โฟลเดอร์ `%APPDATA%\MetaQuotes` หรือแพ็กเกจ `MetaTrader5` ที่ import ได้ · (v2.0; v2.1, F8) บน Mac: ไม่มีแอปที่ชื่อมี `metatrader`, ไม่มีโฟลเดอร์ของ MetaQuotes (MT4 หรือ MT5) ใต้ `~/Library/Application Support`, ไม่มี `terminal64.exe` ใน Wine prefix ที่รู้จัก
- (v2.0) เครื่อง Windows เดิมเลิกใช้กับโปรเจกต์นี้และถูกล้างตาม D-023 ข้อ 2 ทาง 1: ไม่มี terminal, ไม่มีโฟลเดอร์ข้อมูลของ terminal, ไม่มี clone ของ repo และไม่มี session ของ agent
- ไม่มี holdout หรือไฟล์ข้อมูลตลาดของช่วงที่ตัดออกในพื้นที่ที่ research ใช้ ไม่มี drive/share ที่ต่อไป VPS
- เจ้าของทดสอบจากเครื่องตัวเองแล้วว่าเข้า VPS ได้ทาง RDP แบบ interactive เท่านั้น และไม่มี credential ของ VPS บันทึกไว้
- `sochron.app.envcheck` ที่ R1 ต้องผ่านก่อนทุกครั้ง และ synthetic sentinel บน VPS ที่หาไม่เจอบนเครื่องนี้

## Current behavior and evidence (revision)
`main` `a11bff7` · เครื่องเจ้าของมี `C:\Program Files\MetaTrader 5` และ `%APPDATA%\MetaQuotes` (ตรวจแค่การมีอยู่) · `MetaTrader5` ไม่อยู่ใน `pyproject.toml` · โปรเจกต์เป็น virtual project (`package = false`): `python -m sochron…` ต้องตั้ง `PYTHONPATH=src` (pytest ใช้ `pythonpath = ["src"]` เอง) · `research` ปฏิเสธแท่งตั้งแต่ cutoff ก่อนการตรวจอื่น (`inputs.py` holdout guard) และต้องการ `core.Bar` พอดี · `data.snapshot` ยังไม่มีตัวอ่าน snapshot (SLICE-R1, D-020)

(v2.0) วัดบนเครื่อง Mac 2026-11-17 ที่ `c97aac6` (macOS 26.6.2, arm64, zsh 5.9, uv 0.13.5, CPython 3.12.15):
- `uv run --offline pytest tests -q -p no:cacheprovider` → 3692 passed (เท่ากับ Windows 2026-11-05)
- อ่านโค้ด `src/sochron/app/envcheck.py` (ยังไม่ได้รันบน Mac เพราะตัวตรวจค้นโฟลเดอร์ส่วนตัวของเจ้าของ): ไม่มีตัวแปร `ProgramFiles*` จึง `raise OSError("no Program Files folder to search")` (บรรทัด 599–600) · `ctypes.WinDLL` (643, 650, 677, 739–740), `os.listdrives` (646), `import winreg` (717) ล้มแล้ว `guarded` คืน None (756–759) → `terminal_install` และ `network_shares` เป็น UNKNOWN · `terminal_data` ตรวจ `~/AppData/Roaming/MetaQuotes` ซึ่งไม่มีความหมายบน Mac (784–785) · `is_cloud_only` อ่าน `st_file_attributes` ซึ่ง macOS ไม่มี (175) · symlink ใต้ repo ทำให้ `holdout_dir`, `excluded_period`, `sentinel` เป็น UNKNOWN (338, 362–363; v2.1, F24) → verdict บน Mac เป็น UNKNOWN เสมอ
- symlink ใต้ repo มี 3 ตัว ทั้งหมดอยู่ใต้ `.venv/bin/`: `python` → interpreter ของ uv, `python3` → `python`, `python3.12` → `python` · ใต้ `.git` ไม่มี
- filesystem ที่ mount: `apfs`, `devfs`, `autofs` เท่านั้น · ไม่มี `/Applications/MetaTrader*`, `~/Applications/MetaTrader*`, `~/Library/Application Support/net.metaquotes.wine.metatrader5`, `~/Library/Application Support/CrossOver`, `~/Library/PlayOnMac` · มี iCloud Drive (`~/Library/Mobile Documents/com~apple~CloudDocs`) · (v2.1, F10) มี `~/Library/CloudStorage` แต่ว่าง (0 รายการ, วัด 2026-11-17)
- (v2.1, F10, วัด 2026-11-18 โดย Claude ใน Visual Studio Code ซึ่งเป็นแอปที่จะรัน R1) การค้น home ระดับ 0–3 แบบดูชื่อโฟลเดอร์เท่านั้น ไม่เข้า `Library`, `.ssh`, `.gnupg`, `.git`, `.venv`, `node_modules`: list ได้ 891 โฟลเดอร์ · list ไม่ได้ 2 โฟลเดอร์ (errno 1 "Operation not permitted"): `~/.Trash` และ `~/Pictures/Photos Library.photoslibrary` · ไม่มีคำถามสิทธิ์ของ macOS ค้างระหว่างวัด · `.gnupg` ไม่ได้วัด (ตัววัดไม่เข้า แต่กฎของ contract เข้า)
- (v2.2, r2 F27, วัด 2026-11-18 โดย Claude ใน Visual Studio Code) การค้นของ evaluate ใน search_dirs ทุกระดับ แบบดูชื่อโฟลเดอร์เท่านั้น ไม่ตาม symlink ไม่ list โฟลเดอร์ dataless: `~/Downloads` 60 โฟลเดอร์, `~/Desktop` 9,450, `~/Documents` 201,841, iCloud Drive (`~/Library/Mobile Documents/com~apple~CloudDocs`) 24,665, `~/Library/CloudStorage` 1 (ว่าง) · list ไม่ได้ 0 โฟลเดอร์ · โฟลเดอร์ dataless 0 · symlink ที่ไม่ตาม 31,143 ตัว (ใต้ search_dirs อย่างเดียว = ข้ามตามกฎ v1.9) · ไม่มีคำถามสิทธิ์ของ macOS ค้าง · `~/.gnupg` ไม่มีอยู่ · สรุป: ด้วยสิทธิ์ Files and Folders ที่แอปมีอยู่วันนี้ AC-01 ไม่ติด UNKNOWN จากโฟลเดอร์ที่ list ไม่ได้ และไม่ต้องใช้ Full Disk Access · การวัดนี้เป็นสภาพ ณ วันวัด: โฟลเดอร์ที่ list ไม่ได้ที่เกิดภายหลังยังให้ UNKNOWN ตามกฎ (ไม่มีรายการข้ามใน search_dirs)
- `SF_DATALESS` = `0x40000000` (`sys/stat.h` ของ macOS SDK) · `os.stat()` บน Mac มี `st_flags` · โมดูล `stat` ของ Python 3.12 ไม่มีค่าคงที่ `SF_DATALESS`
- แพ็กเกจ `MetaTrader5` ไม่มี wheel สำหรับ macOS (AGENTS.md: "Windows-only wheels") (v2.1, F20) `mt5_package` บน darwin จึงผ่านเสมอ ไม่นับเป็นหลักฐาน · กฎ (1) ของ `sentinel` (vault_path มีอยู่บนเครื่องนี้) ก็ล้มไม่ได้บน Mac เพราะ `C:\vault` เป็น path สัมพัทธ์บน POSIX ที่ไม่มีวันมีอยู่ · ถ้อยคำ detail คงเดิม (F4) runbook ฉบับ macOS จึงเป็นที่บอกว่าสองข้อนี้ไม่นับ
- path ของ MT5 บน macOS มาจากผลค้นเว็บ 2026-11-17 (หน้า help ทางการของ MetaQuotes และคู่มือโบรกเกอร์) (v2.1, F9) ผู้ตรวจ contract เปิดหน้าทางการ 2026-11-17 แล้ว: โฟลเดอร์ทั้งสองตรงตามหน้า (หน้าเขียน `Metatrader 5`) · หน้าไม่ระบุชื่อ .app และไม่มีคำว่า `terminal64.exe`; ชื่อแอป `MetaTrader 5` มาจากแหล่งบุคคลที่สาม (D-023 ข้อ 4)
- (v2.1, F9, วัด 2026-11-18 ด้วยการดูชื่อโฟลเดอร์ระดับ 0 ของ home) มีโฟลเดอร์ `~/.colima` (เครื่องมือ VM/container แบบ command line) และ (v2.3, r3 F42) `~/.docker` (วัดการมีอยู่เท่านั้น ไม่ได้อ่านข้างใน): อยู่ในขอบเขตคำยืนยันเรื่อง VM และ container ของ AC-03 ข้อ 4

## Scope
- In scope: `src/sochron/app/__init__.py`, `src/sochron/app/envcheck.py` · `scripts/env/make_sentinel.py` (stdlib เท่านั้น, รันบน VPS) · unit tests `tests/unit/app/**` · runbook `docs/runbooks/ENV-002-research-host.md` · `docs/evidence/ENV-002-sentinel.json` (ค่าของ sentinel ที่ commit: ชื่อ, ขนาด, SHA-256, token, vault path, เวลาสร้าง) · หลักฐาน · โดยผู้เขียน tests ผ่าน patch D-006: `tests/acceptance/ENV-002/**`, `tests/architecture/**`
- (v2.0) In scope เพิ่ม: ตัวอ่าน darwin ใน `src/sochron/app/envcheck.py` (เพิ่ม ไม่รื้อตัวอ่าน Windows) · unit tests ของตัวอ่าน darwin ใน `tests/unit/app/**` · runbook ฉบับ macOS ใน `docs/runbooks/ENV-002-research-host.md` (ขั้นบน VPS ไม่เปลี่ยน) · โดยผู้เขียน tests ผ่าน patch D-006: กรณี macOS ใน `tests/acceptance/ENV-002/**` และตัวตรวจ ctypes ของ envcheck ใน `tests/architecture/test_imports.py` (v2.1, F2: แก้แบบแคบตามหัวข้อ Invariants; allow list ของ stdlib ไม่เปลี่ยน) · `DECISIONS.md` เฉพาะ D-023 และบรรทัดอ้างกลับใต้ D-021 (v2.1, F17)
- (v2.0) Exclusions เพิ่ม: runbook และ AC ของ ENV-001 ฝั่งเครื่องเจ้าของ (contract revision ของ ENV-001) · การแก้ controls ให้ผ่านบน macOS (งาน FIX แยก, Q6) · patch ของ `AGENTS.md`/`CLAUDE.md` และ `docs/tooling/**` (งานตามของ D-023) · การติดตั้ง MT5 หรือ Wine บน Mac (ห้ามทุกกรณี; v2.1, F16)
- Exclusions: รูปแบบ snapshot/manifest เต็มและ loader ของ R1 (SLICE-R1) · การดึงข้อมูล การตัดและย้าย holdout (D-021, contract ของ acquisition host) · `data.acquire`, `broker` · แก้ `research`, `backtest`, `strategy`, `data`
- Allowed files/modules: ข้างบน + `docs/evidence/ENV-002.md`, `docs/handoff/ENV-002.md`, `PROGRESS.md` · หลัง ENV-1 ผ่าน (ตอนบันทึก "ENV-1 ผ่าน": วันที่, commit ของ 3 งาน) แก้ได้เฉพาะ: `docs/architecture.md` ข้อ 6.1 ("ระยะนี้" และ bullet ด่าน ENV-1 ตาม D-021 ข้อ 1), ข้อ 7 ประโยคขอบเขต research/holdout ("ระยะนี้ที่ยังใช้เครื่องเดียว…"), ข้อ 9 แถว holdout, และแถว Q-08 ของ `SPEC.md` (ชี้ไป D-021) · (v2.1, F17) และข้อ 2 แถว "เครื่องพัฒนา" กับแผนภาพข้อ 6 (คำว่า owner PC) ของ `docs/architecture.md` ให้ตรงกับ D-023 · การแก้บรรทัด Phase ใน `AGENTS.md` เป็น patch D-006 แยกให้เจ้าของ
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
    "darwin"  ตัวอ่าน darwin (ใหม่) ตามรายการข้างล่าง
    อื่นๆ      ทุก fact ที่ต้องอ่านจาก OS = อ่านไม่ได้ → `terminal_install`, `terminal_data`, `network_shares` เป็น UNKNOWN (ไม่มีวัน PASS)
              (v2.1, F22) v1.9: `terminal_install` และ `network_shares` เป็น UNKNOWN ผ่าน `guarded` แต่ `terminal_data` เป็น PASS เพราะตรวจแค่การมีอยู่
              ของ path · v2.0 ทำให้ทั้งสามเป็น UNKNOWN บน platform อื่น และมี test · `mt5_package` ยังอ่านได้ทุก platform · `default_roots` บน platform
              อื่นคงพฤติกรรม v1.9 · tests บน Linux ยังใช้ Facts ปลอมได้ตามเดิม
  (v2.1, F1) Facts, ResearchRoots, Item และ Report ไม่เพิ่ม field (tests ที่ล็อกเทียบชุด field แบบเท่ากันพอดี) · ชื่อตัวอ่านมาจากฟังก์ชันระดับโมดูล
    `reader_name() -> str` (`win32`, `darwin` หรือ `none` จาก `sys.platform` ที่อ่านตอนเรียก) · CLI (`main`) พิมพ์บรรทัด `reader: <ชื่อ>` ก่อนข้อความของ
    `render` ทุกแพลตฟอร์ม (`render` ไม่เปลี่ยน; รายละเอียดที่ r2 F25) · evaluate ไม่รู้ platform · ขอบเขต: `reader_name()` บอก platform ของโปรเซสที่พิมพ์ ไม่ได้บอกที่มาของ Facts ที่สร้างจากที่อื่น
  (v2.1, F4) ตัวอ่าน darwin เติม Facts เดิม 7 field (กฎของ evaluate ไม่เปลี่ยน):
    terminal_paths          = path ที่พบจากกฎแอป, โฟลเดอร์ `MetaTrader*`, `terminal64.exe` และ path ของ executable ที่รันอยู่ซึ่งเข้ากฎโปรเซสของ terminal_install (r3 F33)
    process_names           = ชื่อไฟล์ (basename) ของ executable ทุกโปรเซสที่อ่านได้ · รายการโปรเซสอ่านไม่ได้ตามกฎของ terminal_install
                              (รวมกรณี Wine loader และ `DYLD_*`) → None เท่านั้น (`terminal_paths` ยังเป็นผลของกฎ path)
    (v2.2, r2 F30) สิ่งที่พบแล้วไม่ถูกกลบด้วย "อ่านไม่ได้": path ที่พบอยู่ใน `terminal_paths` เสมอ · `terminal_paths` เป็น None เฉพาะเมื่อการค้นไม่ครบ
                              และไม่พบ path ใดเลย · โปรเซสชื่อ `terminal64.exe` ถูกใส่ใน `terminal_paths` ด้วย path เต็ม (จึงเป็น FAIL แม้
                              `process_names` เป็น None จากกฎ Wine loader) · (v2.3, r3 F30) "เสมอ" ใช้กับการค้น path และกฎ Wine loader
                              · เมื่อ `read_process_paths` ยก OSError ไม่มี path ของโปรเซสให้ใส่ (ฟังก์ชันคืน path หรือยก exception อย่างใดอย่างหนึ่ง)
    uninstall_display_names = `()` เสมอ (ไม่ใช่ None: macOS ไม่มีกฎนี้)
    metaquotes_exists       = มีรายการที่ตรงกฎของ terminal_data · `~/Library/Application Support` list ไม่ได้ → None
    mt5_spec_found          = ผลของ `find_spec` เหมือนทุกแพลตฟอร์ม
    remote_drives           = mount ที่เข้ากฎ FAIL ในรูป `<ชนิด> <ต้นทาง> on <จุด mount>`
    connected_resources     = `()` เมื่อไม่มี mount ใดเข้ากฎ UNKNOWN · None เมื่อมี mount ที่เข้ากฎ UNKNOWN, ไม่พบ `/` ตามกฎ,
                              API ล้ม, มี `DYLD_*` หรือเครื่องไม่ใช่ arm64 (r2 F26)
  (v2.1, F4) ฟังก์ชันระดับโมดูลที่ tests เรียกหรือแทนได้ (ไม่เรียก API ของ OS เอง; ชื่อและ signature เป็นข้อผูกของ contract ผู้เขียน tests ที่ต้องการ
    เปลี่ยนให้ถามใน handoff ก่อน):
    (v2.3, r3 F25: ค่าที่คืนขยายให้พาตัวเลขของบรรทัด CLI ได้ ทุกฟังก์ชันในรายการนี้ไม่เขียนสถานะของโมดูล มีแต่ `collect` และ `research_host_report` ที่เขียน)
    find_terminal_paths_darwin(applications, program_files, home, never_listed)
        -> tuple[tuple[str, ...], bool, tuple[str, ...]]          # (path ที่พบ, ค้นครบหรือไม่ (r2 F30), path ของโฟลเดอร์ที่ข้าม (บรรทัด `skipped:`))
    wine_prefixes(home) -> tuple[tuple[Path, ...], tuple[Path, ...], tuple[Path, ...]]
        # (prefix ที่พบ, โฟลเดอร์ต้นทางที่มีอยู่, root `drive_c/Program Files*`) · ยก OSError ตามกฎของ program_files ข้างล่าง (บรรทัด `wine:`)
    find_wine_program_files(home) -> tuple[Path, ...]              # = ส่วนที่สามของ `wine_prefixes(home)`
    classify_mounts(entries: tuple[tuple[str, str, str, int], ...])
        -> tuple[tuple[str, ...], tuple[str, ...] | None, tuple[str, ...], str | None]
        # entry = (ชนิด, ต้นทาง, จุด mount, flags) · คืน (remote_drives, connected_resources, จุด mount ที่ไม่อยู่ในรายการอนุญาต,
        #   ปัญหาของ `/`: None เมื่อผ่าน, `missing` หรือ `<ชนิด>` เมื่อไม่ใช่ apfs)
    classify_processes(paths: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...] | None, int]
        # คืน (terminal_paths ส่วนของโปรเซส, process_names, จำนวน Wine loader)
    _darwin_application_dirs(home) -> tuple[Path, ...]
    (v2.2, r2 F4) การอ่านโปรเซสและ mount แยกเป็นตัวอ่านดิบ (มีแต่การเรียก ctypes; tests แทนด้วยตัวปลอม) กับฟังก์ชัน pure ที่ถือกฎทั้งหมด (tests เรียกตรง):
      ตัวอ่านดิบ  _darwin_list_pids(capacity: int) -> tuple[int, tuple[int, ...]]     # (จำนวนที่ API คืน, pid ที่อ่านได้) · API ล้ม = ยก OSError
                 _darwin_pid_path(pid: int) -> tuple[str | None, int]                 # (path หรือ None, errno) · ไม่ยก exception
                 _darwin_mounts(capacity: int) -> tuple[int, tuple[tuple[str, str, str, int], ...]]   # (จำนวนที่ API คืน, entries) · API ล้ม = ยก OSError
      pure       read_process_paths(own_pid: int, own_path: str) -> tuple[tuple[str, ...], int, int]
                     # (path ที่อ่านได้, จำนวน pid ที่ list, จำนวนที่ข้าม (pid 0 และ ESRCH)) (v2.3, r3 F25) · ถือกฎของ F7 ทั้งหมด: วนขยาย buffer,
                     #   ข้าม pid 0 และ ESRCH, errno อื่น, PID ของตัวเอง · อ่านไม่ได้ตามกฎ = ยก OSError ที่ข้อความเป็น <เหตุ> ของบรรทัด `processes:`
                 read_mounts() -> tuple[tuple[str, str, str, int], ...]               # วนขยาย buffer (r2 F31) · อ่านไม่ได้ = ยก OSError
      ("pure" ในที่นี้ = ไม่เรียก ctypes เอง เรียกผ่านตัวอ่านดิบเท่านั้น และไม่เขียนสถานะของโมดูล)
      `collect` บน darwin เรียก `read_process_paths(os.getpid(), os.path.realpath(sys.executable))` แล้ว `classify_processes`, และ `read_mounts()`
      แล้ว `classify_mounts` · OSError จากฟังก์ชันเหล่านี้ → field ที่เกี่ยวเป็น None ตามตาราง Facts ข้างบน · `_darwin_process_paths()` ของ v2.1 ถูกแทนด้วยชุดนี้
      · (v2.3, r3 F25) `collect` บน darwin เรียก `wine_prefixes(roots.user_profile)` ซ้ำเพื่อทำบรรทัด `wine:` และค้น `terminal64.exe` ใต้ root
        `Program Files*` ที่ได้ รวมกับ `roots.program_files` (ไม่ซ้ำ) · roots ที่ประกอบเองจึงไม่ข้ามการค้น Wine prefix · `wine_prefixes` ยก OSError
        = `terminal_paths` None (UNKNOWN ของ terminal_install) และบรรทัด `wine: unreadable (<เหตุ>)`
    (v2.2, r2 F4) `never_listed: tuple[Path, ...]` = path เต็มที่การค้น home ไม่เข้า (`<home>/Library`, `<home>/.ssh` และ path ที่พบจากกฎ terminal_data)
    (v2.2, r2 F4) การตรวจ `DYLD_*` และ `os.uname().machine` อยู่ใน `collect` ก่อนเรียกฟังก์ชันอ่านโปรเซสและ mount ทั้งหมด (ไม่ผ่าน = ไม่เรียก และ field
      ที่เกี่ยวเป็น None) · tests ของ collect ตั้ง `envcheck.os.uname` ปลอมที่คืน machine `arm64` (CI เป็น Linux x86_64) และมีกรณี `x86_64` แยก
    · `find_terminal_paths(program_files, user_profile, appdata)` เดิมไม่เปลี่ยน · `collect` และ `default_roots` อ่าน `sys.platform` ตอนถูกเรียก
      (tests ตั้ง `envcheck.sys.platform`)
  (v2.1, F4) กรณี macOS ระดับ collect (แอป, Wine prefix, ระดับของ `terminal64.exe`, โปรเซส, mount, platform อื่น) เป็น tests ที่ล็อกของผู้เขียน tests ใน
    `tests/acceptance/ENV-002/` ซึ่งเรียก `collect` จริงโดยตั้ง `envcheck.sys.platform` และแทนตัวอ่านดิบ (ไม่ใช่ unit test ของ implementer อย่างเดียว
    เพราะงานนี้ High) · ถ้อยคำ detail ของ item ที่มาจาก Facts คงเดิมตาม v1.9 ทุกแพลตฟอร์ม (เช่น `%APPDATA%\MetaQuotes`, `Uninstall entries`,
    `remote drives`); บรรทัด `reader: darwin` และ runbook ฉบับ macOS บอกว่าคำเหล่านั้นหมายถึงอะไรบน Mac
  (v2.1, F4) ค่าที่ Facts 7 field พาไปไม่ได้ (errno, จำนวน pid, จำนวน Wine prefix, โฟลเดอร์ที่ข้าม, ชื่อแอปของ note) ไม่อยู่ใน detail ของ item:
    (v2.3, r3 F25: แทนถ้อยคำของ v2.2 เรื่อง "ตัวแปรระดับโมดูล" และ "ในโปรเซสนี้") สถานะของบรรทัด CLI:
    · ตัวแปรระดับโมดูลเดียวชื่อ `_HOST_SUMMARY` (dict) · ค่าตั้งต้นตอน import คือว่าง
    · `research_host_report(*, roots, sentinel)` ทุกครั้ง ทุก reader: ล้าง `_HOST_SUMMARY` แล้วบันทึก reader, `roots` ที่จะใช้ และ token ของ sentinel
      (ถ้ามี) ก่อนเรียก `collect` · signature ไม่เปลี่ยน (รับทั้ง roots และ sentinel อยู่แล้ว)
    · `collect` ตัวจริงบน darwin บันทึกสรุปของการอ่านลง `_HOST_SUMMARY` จากค่าที่ฟังก์ชันข้างบนคืน · ถ้าถูกเรียกตรง (ไม่ผ่าน `research_host_report`)
      ก็ล้างและบันทึก reader กับ `roots` เองก่อน (ไม่มี token ให้แทน)
    · `host_lines() -> tuple[str, ...]` คืนบรรทัดจาก `_HOST_SUMMARY` ของการเรียกครั้งล่าสุด ไม่อ่าน OS เอง ไม่ยก exception และแทน token ที่บันทึกไว้ด้วย
      `<token>` · ก่อนมีการเรียกใดเลย คืนแค่ `reader:`
    · ผลที่ตามมา: `collect` ที่ถูกแทนใน tests ไม่เขียนสรุป เมื่อเรียกผ่าน `research_host_report` หรือ `main` บน darwin จึงได้ `reader: darwin`, `roots:`,
      `processes: not read`, `mounts: not read`, `wine: not read` ไม่ว่า test ก่อนหน้าทำอะไร · reader อื่นได้แค่ `reader:` และ `roots:`
    · tests ของ `host_lines()` เรียกผ่าน `research_host_report` หรือ `main` เสมอ (หรือ `collect` ตัวจริงที่ตั้ง platform เป็น darwin พร้อมตัวอ่านดิบปลอม)
    · `main` พิมพ์บรรทัดของ `host_lines()` ทั้งหมดก่อนข้อความของ `render` (`render(report, note)`, Report และ Item คง signature และผลเดิม
      บรรทัดสุดท้ายจึงยังเป็น `RESEARCH HOST: <verdict>`) · เมื่อ `default_roots` ยก OSError: พิมพ์ `reader:` แล้วข้อความเดิมของ v1.9 (ไม่มี `roots:`)
    รูปของบรรทัด (v2.3, r3 F48: ทุกรูปที่เกิดได้ · รายการในวงเล็บคั่นด้วย `, ` · ชนิดของ mount ไม่ซ้ำ เรียงตามลำดับที่พบ · ชื่อใน `tools:` และ `apps:` เรียงตามลำดับ
    ของรายการใน contract นี้):
    ทุกแพลตฟอร์ม:
      reader: <win32|darwin|none>                                                                                              (F1)
      roots: repo=<path> home=<path> search_dirs=<path>, …[; cloud storage: <n> (<ผู้ให้บริการ>, …)]                           (F11, r2 F41)
             · ส่วน `cloud storage:` มีเฉพาะ darwin · โฟลเดอร์ระดับ 0 ของ `~/Library/CloudStorage` ไม่อยู่ใน `search_dirs=` แต่พิมพ์เป็นจำนวนและส่วนของ
               ชื่อก่อน `-` ตัวแรกเท่านั้น (เช่น `OneDrive`) ไม่พิมพ์ชื่อบัญชี · ไม่มีหรือว่าง = `cloud storage: 0`
             · (v2.3, r3 F46) บน win32 search_dirs ที่มาจากตัวแปร `OneDrive*` ไม่อยู่ใน `search_dirs=` แต่พิมพ์เป็น `; onedrive: <n>`
    เฉพาะ darwin:
      processes: <n> listed, <n> paths read, <n> skipped, <n> wine loaders                                                     (F7)
        หรือ processes: unreadable (<เหตุ>)   เหตุ = `DYLD_ variables set` · `not arm64: <machine>` · `proc_listallpids failed, errno <n>` ·
                                             `listed 0 pids` · `own pid missing, <n> pids` · `own path differs, <n> pids` · `errno <n> on pid <pid>, <n> pids`
        หรือ processes: not read
      mounts: <n> (<ชนิดที่พบ>)[; not allowed: <จุด mount>, …][; root: <missing|ชนิด>]                                      (F7, r2 F15, r2 F32)
        หรือ mounts: unreadable (<เหตุ>)      เหตุ = `DYLD_ variables set` · `not arm64: <machine>` · `getfsstat failed, errno <n>`
        หรือ mounts: not read
      wine: <n> prefixes; looked at <โฟลเดอร์ต้นทางที่มีอยู่, … หรือ none>   หรือ   wine: unreadable (<เหตุ>)   หรือ   wine: not read   (F9)
      skipped: <n> folders[ (<path>, …)]   โฟลเดอร์ที่การค้น terminal ข้าม: ในรายการข้ามที่ list ไม่ได้ และโฟลเดอร์ dataless · ไม่มี = `skipped: 0 folders`
      apps: <ชื่อแอปที่ตรงรายการ, … หรือ none>                                                              (F9; v2.1 เรียกบรรทัดนี้ว่า note:)
      tools: <ชื่อที่พบ, … หรือ none>                                                                                          (r2 F9)
    · ใน `collect` ที่ถูกเรียกจริง บรรทัด `skipped:`, `apps:`, `tools:` มาจากการค้นของรอบนั้น · เมื่อ `collect` ถูกแทน สามบรรทัดนี้ไม่ถูกพิมพ์
  default_roots บน darwin:
    user_profile  = โฟลเดอร์ home ของผู้ใช้
    appdata       = ~/Library/Application Support
    program_files = โฟลเดอร์ `drive_c/Program Files*` ของ Wine prefix ที่พบ (ดูระดับ 0 ของแต่ละ prefix ไม่ค้นลึก) ใต้
                    ~/Library/PlayOnMac/wineprefix/* (เทียบชื่อไม่สนตัวพิมพ์; v2.1, F9), ~/Library/Application Support/CrossOver/Bottles/* และ ~/.wine
                    · (v2.1, F9) ไม่มี prefix เลย = `program_files` ว่าง ซึ่งตัวอ่าน darwin ยอมรับ (ตัวอ่าน Windows ยังถือว่า `program_files` ว่าง
                      = UNKNOWN ตาม v1.9 r1 F5; `find_terminal_paths` เดิมไม่เปลี่ยน และตัวอ่าน darwin ไม่เรียกมันด้วยรายการ root ว่าง; unit test ของ
                      r1 F5 คงเดิม)
                    · (v2.1, F9) โฟลเดอร์ต้นทาง (`wineprefix`, `Bottles`) ที่มีอยู่แต่ list ไม่ได้ทำให้ `default_roots` ยก OSError: CLI พิมพ์
                      `RESEARCH HOST: UNKNOWN` exit 1 และ `require_research_host` ยก `ResearchHostError` (ทางเดียวกับ shell folder ของ v1.9 r1 F5)
                    · (v2.2, r2 F10; v2.3, r3 F43) กฎเดียวกันใช้กับ `~/.wine`, `~/Library/PlayOnMac`, `~/Library/PlayOnMac/wineprefix`,
                      `~/Library/Application Support/CrossOver`, `~/Library/Application Support/CrossOver/Bottles`, โฟลเดอร์ของแต่ละ prefix, `drive_c` ของ prefix
                      และรายการ `Program Files*` ระดับ 0 ของ `drive_c`: มีอยู่แต่ list ไม่ได้ หรือเป็น symlink → `default_roots` ยก OSError · prefix ที่ไม่มี
                      `drive_c` หรือไม่มี `Program Files*` = ไม่มี root จาก prefix นั้น (ไม่ใช่ข้อผิดพลาด)
                    · จำนวน Wine prefix ที่พบและโฟลเดอร์ต้นทางที่ดู อยู่ในบรรทัด `wine:` ของ CLI
    search_dirs   = ~/Downloads, ~/Desktop, ~/Documents
                    + ~/Library/Mobile Documents/com~apple~CloudDocs (iCloud Drive) ถ้ามี
                    + ทุกโฟลเดอร์ระดับ 0 ของ ~/Library/CloudStorage ถ้ามี (OneDrive, Google Drive, Dropbox แบบ File Provider)
    (v2.1, F11) ไม่อ่านตัวแปร `USERPROFILE`, `APPDATA`, `ProgramFiles*`, `OneDrive*` บน darwin · home มาจากฟังก์ชันระดับโมดูล `_darwin_home()`
                    (ค่าจริง: `os.path.expanduser("~")`; tests แทนได้) · `main` พิมพ์บรรทัด `roots:` ที่บอก repo, home และ search_dirs ที่ใช้
                    โดยแทน token ด้วย `<token>` · (v2.2, r2 F29) เมื่อ `default_roots` ยก OSError ไม่มีบรรทัด `roots:` (พิมพ์ `reader:` แล้วข้อความ
                    เดิมของ v1.9) · R1 บันทึกและเทียบบรรทัดนี้ตามหัวข้อ "งานที่ส่งต่อ" · บรรทัดนี้มีชื่อบัญชี macOS ซึ่งจะอยู่ในหลักฐานที่ commit (คำตัดสินข้อ 8: ยอม)
  terminal_install (darwin)  FAIL เมื่อพบอย่างใดอย่างหนึ่ง (ชื่อไม่สนตัวพิมพ์):
    · (v2.1, F8; v2.2, r2 F33, คำตัดสิน r2 ข้อ 3) รายการระดับ 0 ของ /Applications หรือ ~/Applications ที่ชื่อมี `metatrader` (ไม่สนตัวพิมพ์; กฎเดียวกับ
      Uninstall entry ของ v1.9) มีหรือไม่มี `.app` ก็ตาม (เหมือนกฎโฟลเดอร์ `MetaTrader*` ใน Program Files ของ Windows) (ดูชื่อเท่านั้น ไม่เข้าไป; ครอบชื่อของโบรกเกอร์เช่น `Exness MetaTrader 5.app` · ยังไม่ได้ตรวจว่าแอป iPhone/iPad จาก App Store ใช้ชื่อที่เข้ากฎนี้)
    · โฟลเดอร์ `MetaTrader*` ระดับ 0 ของ program_files แต่ละตัว · `terminal64.exe` ระดับ 0–2 ใต้ program_files แต่ละตัว
      (v2.2, r2 F10) การค้นใต้ program_files บน darwin ไม่ใช้กฎข้ามของ v1.8: โฟลเดอร์ใดใต้ root ที่ list ไม่ได้ = การค้นไม่ครบ (`terminal_paths` None
      ตามกฎของ r2 F30) · ตรรกะเทียบชื่อและระดับเหมือน helper เดิม แต่ helper เดิมของ Windows (ซึ่งข้ามโฟลเดอร์ที่ list ไม่ได้) ไม่ถูกเรียกบน darwin
    · `terminal64.exe` ใต้ home ระดับ 0–3 (ข้าม .git, .venv, node_modules และทุกรายการที่ตรงกฎของ terminal_data
      · (v2.1, F10, คำตัดสินข้อ 7) ไม่เข้า `~/Library` ทั้งโฟลเดอร์ และไม่เข้า `~/.ssh` (เทียบ path ไม่ใช่ชื่อ): ที่รู้จักใต้ `~/Library` ตรวจด้วยกฎ terminal_data
        และ Wine prefix อยู่แล้ว · การค้นนี้เทียบชื่อไฟล์เท่านั้น ไม่เปิดไฟล์)
    · (v2.2, r2 F12) /Applications หรือ ~/Applications ที่ไม่มีอยู่ = ไม่มีรายการให้ดู (ไม่ใช่ UNKNOWN: Mac ส่วนใหญ่ไม่มี ~/Applications) · มีอยู่แต่ list
      ไม่ได้ = การค้นไม่ครบ (`terminal_paths` None ตามกฎของ r2 F30)
    · โปรเซสที่รันอยู่ซึ่ง path ของ executable มี component ใดก็ตามที่ชื่อมี `metatrader` (ไม่สนตัวพิมพ์ มีหรือไม่มี `.app`, ที่ใดก็ได้บนเครื่อง;
      v2.3, r3 F33: อ่านแบบเข้ม) หรือชื่อไฟล์เป็น `terminal64.exe` · ราคาของกฎนี้: FAIL ตลอดเวลาที่มีโปรเซสใดรันจากโฟลเดอร์ที่ชื่อมีคำนี้
      (v2.1, F7) อ่านด้วย `proc_listallpids`, `proc_pidpath` · `proc_listallpids` ล้มหรือคืนค่าไม่เกิน 0 = UNKNOWN · ถ้าจำนวน pid ที่คืนเท่ากับความจุของ
      buffer ให้ขยาย buffer แล้วอ่านใหม่ (รายการที่ถูกตัดต้องไม่ถือว่าครบ) · ข้ามและนับเฉพาะ pid 0 และโปรเซสที่ `proc_pidpath` ล้มด้วย ESRCH (จบไปแล้ว)
      · ล้มด้วย errno อื่น (เช่น ENOMEM, EPERM) = UNKNOWN และบรรทัด `processes:` บอก errno กับจำนวน pid · ตัวอ่านต้องพบ PID ของตัวเอง (`os.getpid()`)
      และ `proc_pidpath` ของ PID นั้นต้องเท่ากับ `os.path.realpath(sys.executable)` ไม่เช่นนั้นรายการโปรเซสอ่านไม่ได้ (UNKNOWN)
      · วัด 2026-11-17: 770 pid, อ่านได้ 769 รวมโปรเซสของ root, pid 0 ให้ ESRCH, EPERM 0
    · (v2.1, F7, คำตัดสินข้อ 5) executable ที่ชื่อไฟล์ขึ้นต้นด้วย `wine` (ไม่สนตัวพิมพ์ เช่น `wine64-preloader`, `wineserver`) และ path ไม่มี
      component ที่ชื่อมี `metatrader` (ถ้ามี = FAIL ตามกฎข้างบน; v2.3, r3 F33) = รายการโปรเซสอ่านไม่ได้ (UNKNOWN: ปิด Wine ก่อนรัน) · ชื่อโปรเซสของ Wine ยังไม่เคยวัดบน macOS กฎนี้จึงเพิ่มได้แค่ UNKNOWN ไม่ใช่หลักฐานว่าไม่มี Wine
    · ไม่มีกฎ Uninstall entry บน macOS
    · (v2.1, F9, คำตัดสินข้อ 6) note ที่ไม่เปลี่ยน verdict: บรรทัด `wine:` (จำนวน Wine prefix ที่พบ, โฟลเดอร์ต้นทางที่ดู) และบรรทัด `apps:` ที่พิมพ์ชื่อแอป
      ระดับ 0 ของ /Applications กับ ~/Applications ที่ขึ้นต้นด้วย (ไม่สนตัวพิมพ์) crossover, whisky, playonmac, wineskin, kegworks, wine, parallels, vmware,
      utm, virtualbox, docker, orbstack · คำยืนยันของ AC-03 ข้อ 4 เรื่อง VM, container และบัญชีผู้ใช้ ต้องยืนยันซ้ำทุกครั้งที่บรรทัด `apps:`, `tools:` หรือ `wine:` ต่างจาก
      หลักฐานของ ENV-002
    · (v2.2, r2 F9, คำตัดสิน r2 ข้อ 2) บรรทัด `tools:` (ไม่เปลี่ยน verdict) พิมพ์ชื่อที่มีอยู่จากรายการนี้ โดยดูการมีอยู่เท่านั้น ไม่ list ข้างใน: ระดับ 0 ของ home
      `.colima`, `.lima`, `.docker`, `.orbstack`, `.wine`, `.podman` และ path `<home>/.local/share/containers` · (v2.3, r3 F42) เครื่องนี้มี `.colima` และ `.docker`
      (วัดการมีอยู่ 2026-11-18; อีกห้าชื่อไม่มี) บรรทัดในหลักฐานของ ENV-002 จึงคาดว่าเป็น `tools: .colima, .docker` (ค่าที่ commit คือค่าที่รอบ AC-01 พิมพ์จริง)
      และเจ้าของยืนยันใน AC-03 ข้อ 4 ว่า VM ของ colima และ container ของ Docker ไม่มี MT5 หรือ Wine
      · เครื่องมือ command line ที่ไม่ทิ้งชื่อในรายการนี้ (เช่น qemu ที่ติดตั้งเดี่ยว) ไม่ทำให้ต้องยืนยันซ้ำ: เป็นข้อที่เหลือ
  terminal_data (darwin; v2.1, F8)  FAIL เมื่อระดับ 0 ของ `~/Library/Application Support` มีรายการที่ชื่อ (เทียบแบบ lower-case) ขึ้นต้นด้วย `net.metaquotes.`
    หรือ `metatrader` หรือเท่ากับ `metaquotes` · list เฉพาะ `~/Library/Application Support` ระดับเดียวและดูชื่อเท่านั้น ห้าม list หรืออ่านข้างในรายการที่ตรง
    · `~/Library/Application Support` ที่ list ไม่ได้ = UNKNOWN · path จริงที่พบ (ตัวพิมพ์ตามบนดิสก์) คือชุดที่ไม่ถูก list และไม่ถูกเปิด ทั้งในการค้น terminal,
      ใน evaluate และใน `load_sentinel` (ไม่เทียบด้วยสตริงจากกฎ เพราะ `os.path.normcase` ไม่ทำอะไรบน macOS)
    · ใน evaluate โฟลเดอร์ระดับ 0 ของ `roots.appdata` ที่ชื่อตรงกฎนี้ไม่ถูก list และไม่ถูกเปิด บนทุกแพลตฟอร์ม
    · ชื่อจากหน้าทางการของ MetaQuotes (เปิดตรวจ 2026-11-17): `net.metaquotes.wine.metatrader5`, `Metatrader 5`, `net.metaquotes.wine.metatrader4`,
      `Metatrader 4` · กฎของ `<appdata>/MetaQuotes` เทียบแบบเดิมของ v1.9 ไม่เปลี่ยน
    · (v2.2, r2 F28) ผู้ใช้ชุด "ไม่ถูก list และไม่ถูกเปิด" แต่ละตัวได้ชุดนี้อย่างไร: การค้น terminal ใน `collect` รับ path ที่พบผ่าน `never_listed`
      · evaluate และ `load_sentinel` ไม่มี path ที่พบ (Facts มีแค่ bool) จึงเทียบเอง: รายการระดับ 0 ของ `roots.appdata` ที่ชื่อแบบ lower-case ตรงกฎข้างบน
      · โฟลเดอร์ที่ evaluate ข้ามด้วยกฎชื่อนี้ทำให้ทุก item ที่ค้น root นั้นเป็น UNKNOWN (ไม่ข้ามเงียบ) เว้นแต่ `terminal_data` เป็น FAIL อยู่แล้ว
      · (v2.3, r3 F28) `<appdata>/MetaQuotes` คงการข้ามเงียบของ v1.9 (ไม่ใช้ประโยคก่อนหน้า): ตัวอ่านจริงทุกตัวให้ `terminal_data` FAIL เมื่อโฟลเดอร์นี้มีอยู่
        (win32: `metaquotes_exists`; darwin: ชื่อเท่ากับ `metaquotes` ตรงกฎ) การข้ามจึงไม่ซ่อน PASS และไม่เปลี่ยนผลของ test ที่ล็อก
      · บน default roots ของ darwin รายการที่ตรงอยู่ใต้ `~/Library` ซึ่งการค้น home ไม่เข้าอยู่แล้ว `never_listed` จึงมีผลเมื่อ appdata อยู่นอก `<home>/Library`
  network_shares (darwin)    อ่านรายการ mount ด้วย `getfsstat` ของ libc:
    · (v2.3, r3 F44) `MNT_LOCAL` เป็นค่าคงที่ int `0x00001000` ใน envcheck (`sys/mount.h`:222 ของ macOS SDK) แบบเดียวกับ `SF_DATALESS` · tests ใช้ค่าคงที่นี้
    FAIL เมื่อมี mount ชนิด smbfs, nfs, afpfs, webdav, ftp หรือ mount ที่ไม่มี flag MNT_LOCAL และชนิดไม่ใช่ autofs
    · (v2.1, F19) mount ชนิด autofs ผ่านเฉพาะเมื่อ `f_mntfromname` เป็น `map auto_home` (ค่าที่วัดบนเครื่องนี้) · autofs อื่น (เช่น `map -static`, `map -fstab`,
      `map -hosts`) = UNKNOWN · devfs มี MNT_LOCAL อยู่แล้วจึงไม่ต้องยกเว้น
    · (v2.1, F19) ตัวอ่าน darwin รองรับเฉพาะ arm64 (`os.uname().machine == "arm64"`); เครื่องอื่น = อ่านจาก OS ไม่ได้ (UNKNOWN ของ `terminal_install` และ
      `network_shares`) · layout ของ `struct statfs` (2168 ไบต์; `f_flags` 64, `f_fstypename` 72, `f_mntonname` 88, `f_mntfromname` 1112) มี unit test
      เทียบ `ctypes.sizeof` และ offset ของแต่ละ field
    · (v2.1, F19, คำตัดสินข้อ 12) ไม่เพิ่ม `ntfs`, `cddafs`, `lifs` ในรายการ local: ไม่ให้ต่อ external disk ระหว่างรัน ชนิดเหล่านี้จึงเป็น UNKNOWN ตามกฎชนิดที่ไม่รู้จัก
    · ชนิดที่ไม่อยู่ในรายการ local ที่รู้จัก (apfs, hfs, devfs, autofs, msdos, exfat, udf, cd9660, tmpfs, nullfs) และไม่อยู่ในรายการ remote = UNKNOWN
    · API ล้ม = UNKNOWN
    · (v2.1, F15; v2.2, r2 F32, คำตัดสิน r2 ข้อ 4: รายการอนุญาตแทนกฎ `/Volumes/` ของ v2.1) mount ที่จุด mount ไม่ใช่ `/`, `/dev` หรือ path ใต้
      `/System/Volumes/` = UNKNOWN เมื่อไม่เข้ากฎ FAIL (external disk, disk image และ volume ที่ mount ด้วย `-mountpoint` ที่ใดก็ตาม: ถอดก่อนรัน)
      · (v2.3, r3 F32, คำตัดสิน r3: แคบลง) ใต้ `/System/Volumes/Data/` อนุญาตเฉพาะ `/System/Volumes/Data` เองและ `/System/Volumes/Data/home`
        (ส่วนนี้เขียนได้โดยผู้ใช้ผ่าน firmlink ของ `/Users`, `/Volumes`, `/private`) · path อื่นใต้ `/System/Volumes/` (VM, Preboot, Update, xarts,
        iSCPreboot, Hardware และ path ใต้มัน) ยังอนุญาต: เป็น volume ของระบบที่ผู้ใช้ทั่วไป mount ทับไม่ได้
      · บรรทัด `mounts:` บอกจุด mount ที่เข้ากฎนี้หลังคำว่า `not allowed:` (r2 F15) · วัด 2026-11-18: เครื่องนี้มี 12 mount ที่ `/`, `/dev` และใต้
        `/System/Volumes/` เท่านั้น
    · (v2.1, F7) ตัวอ่าน mount ต้องพบ mount ที่ `/` ชนิด `apfs` ที่มี MNT_LOCAL ไม่เช่นนั้น UNKNOWN (ตัวอ่านที่อ่านไม่ได้อะไรเลยต้องไม่ผ่าน)
    · (v2.2, r2 F26) ลำดับต่อ mount: กฎ FAIL ก่อน แล้วจึงกฎ UNKNOWN · ผลรวมของ item: FAIL ชนะ UNKNOWN ชนะ PASS (เหมือน `_status` ของ v1.9)
      · mount ที่ `/`: ไม่มีในรายการ หรือเป็นชนิด local อื่นที่ไม่ใช่ `apfs` = UNKNOWN · ไม่มี MNT_LOCAL หรือเป็นชนิด remote = FAIL ตามกฎ FAIL
      · กฎทั้งหมดของ mount อยู่ใน `classify_mounts` (pure)
    · (v2.2, r2 F31) `read_mounts`: จำนวน mount ที่ `_darwin_mounts` คืนเท่ากับ capacity = ขยายแล้วอ่านใหม่ (รายการที่ถูกตัดต้องไม่ถือว่าครบ; `getfsstat`
      เติม buffer ได้เท่าขนาดที่ให้) · บรรทัด `mounts:` บอกจำนวนที่อ่านได้
  is_cloud_only (v2.1, F6)   ฟังก์ชันเดียวทุกแพลตฟอร์ม (ไม่เลือกตาม `sys.platform`): True เมื่อ `getattr(st, "st_file_attributes", 0)` มี bit recall ของ v1.9
    หรือ `getattr(st, "st_flags", 0)` มี `0x40000000` (SF_DATALESS) · test ที่ล็อกของ v1.9 ต้องผ่านบน Mac โดยไม่แก้
    · (v2.1, F2) `SF_DATALESS` เป็นค่าคงที่ int `0x40000000` ใน envcheck (แบบเดียวกับ `RECALL_ATTRIBUTES`) ไม่ import `stat`
    · (v2.1, F6) ไฟล์ชื่อ `.<ชื่อ>.icloud` (ไม่สนตัวพิมพ์, ทุกแพลตฟอร์ม, ไม่ถูกเปิด): ใต้ repo หรือ data dir = UNKNOWN ของ `excluded_period` และ `sentinel`
      ยกเว้น `.<ชื่อ sentinel>.icloud` ซึ่งเป็น FAIL ของ `sentinel` ตามกฎ (2) ทุกพื้นที่ (r2 F30)
      · ใต้ search_dirs อย่างเดียว: `.<ชื่อ sentinel>.icloud` = FAIL ตามกฎ (2), `.<อะไรก็ได้>.json.icloud` = UNKNOWN ของ `sentinel` (ขนาดจริงอ่านไม่ได้โดย
        ไม่เปิด), อื่นๆ ข้าม (ครึ่งของ search_dirs เป็นกฎใหม่ของ v2.1; macOS 14 ขึ้นไปไม่สร้างไฟล์ตัวแทนแบบนี้แล้ว)
    · (v2.1, F6, คำตัดสินข้อ 4) โฟลเดอร์ dataless (`envcheck.is_cloud_only(folder)` เป็น True) ไม่ถูก list เพราะการ list ทำให้ macOS ดึงรายการจาก cloud
      (Apple TN3150) · ตรวจก่อน list ทุกครั้ง รวม root ของ data dirs และ search_dirs เอง และห้าม stat path ที่อยู่ใต้โฟลเดอร์ dataless
      · ใต้ repo หรือ data dir = UNKNOWN ของ holdout_dir, excluded_period และ sentinel · ใต้ search_dirs = UNKNOWN ของ sentinel
      · ใต้ root ของการค้น terminal = ข้ามและนับในบรรทัด `skipped:` · tests จำลองด้วยการแทน `envcheck.is_cloud_only` ตัวเดิม และตรวจว่าโฟลเดอร์นั้นไม่ถูก list
      · ไม่ใช้ `setiopolicy_np`
  symlink (ทุกแพลตฟอร์ม; ข้อยกเว้นเดียวของกฎ v1.9 r1 F2/F3):
    (v2.1, F5) symlink ที่อยู่ระดับ 0 ของ `<repo>/.venv/bin/` (`<repo>` คือ `roots.repo` เสมอ รวมกรณี data dir ครอบ repo) ชื่อตรงตัวพิมพ์กับ
    `python`, `python3` หรือ `python3\.[0-9]+` ซึ่ง `os.stat` (ตาม link) ให้ `st_dev` และ `st_ino` เท่ากับของ `os.stat(sys.executable)`
    ไม่ทำให้เป็น UNKNOWN และไม่ถูกเปิด · `sys.executable` ว่าง หรือ stat ของฝั่งใดล้ม = ไม่มีข้อยกเว้น (UNKNOWN ตามเดิม)
    · symlink ชื่อเดียวกันที่จบที่ไฟล์อื่น และ symlink อื่นทุกตัวใต้ repo หรือ data dir = UNKNOWN ของ holdout_dir, excluded_period และ sentinel ตามเดิม
    · กฎที่ดูแค่ชื่อของ v1.9 ยังใช้กับ symlink ที่ได้รับยกเว้น · link ที่ได้รับยกเว้นยังนับใน `reparse points skipped` และ detail บอกจำนวนที่ได้รับยกเว้น
    · วัดบน macOS: uv 0.13.5 สร้าง symlink สามตัวนี้เท่านั้น (บน Linux uv สร้าง `.venv/lib64 -> lib` เพิ่ม ซึ่งยังเป็น UNKNOWN; Linux ไม่ใช่ research host)
  โฟลเดอร์ที่ macOS ไม่ให้ list เพราะ Privacy (TCC, "Operation not permitted") ใช้กฎเดิมของโฟลเดอร์ที่ list ไม่ได้:
    ใน repo, data dirs, search_dirs = UNKNOWN · root เอง list ไม่ได้ = UNKNOWN (v1.9)
    · (v2.1, F10) ใต้ root ของการค้น terminal บน darwin: ข้ามได้เฉพาะโฟลเดอร์ที่ list ไม่ได้ซึ่งอยู่ในรายการที่วัดบนเครื่องเจ้าของ (เทียบ path จาก home):
      `~/.Trash` และ `~/Pictures/Photos Library.photoslibrary` · โฟลเดอร์อื่นใต้ home ที่ list ไม่ได้ = การค้นไม่ครบ
      (`terminal_paths` None ตามกฎของ r2 F30 → UNKNOWN ของ terminal_install; v2.3, r3 F30) · บรรทัด `skipped:` บอกจำนวนและ path ของโฟลเดอร์ที่ข้าม · เหตุที่กฎ v1.8 ("ข้ามทุกโฟลเดอร์ที่ list ไม่ได้") ไม่ถูกยกมา:
      บน macOS ผู้ใช้คนเดียวกันเขียนลงโฟลเดอร์ที่แอปที่รันอยู่ list ไม่ได้ (เช่น Trash) จึงไม่มีเงื่อนไข "ต้องมีสิทธิ์ admin" ของ v1.8
    · (v2.1, F10) `~/Library/CloudStorage` ที่มีอยู่แต่ list ไม่ได้ทำให้ `default_roots` ยก OSError (ทางเดียวกับโฟลเดอร์ต้นทางของ Wine prefix)
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
    · (v2.2, r2 F34) การเรียกที่ยอมรับมี argument สองตัวนี้เท่านั้น: literal ของ path และ `use_errno=True` · mutation เพิ่มที่ต้องถูกปฏิเสธ: literal เดียวกัน
      โดยไม่มี `use_errno=True`, มี `use_errno=False`, มี `handle=h` เพิ่ม, มี `mode=m` เพิ่ม (ไม่มี `use_errno=True` แล้ว `ctypes.get_errno()` เป็น 0 เสมอ
      กฎ errno จะกลายเป็น UNKNOWN ถาวรโดยไม่มีคำอธิบาย)
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
- **SLICE-R1:** loader ของ snapshot (ใน `app`, D-020) ปฏิเสธแท่งของ sentinel และ manifest ที่จบหลัง cutoff ก่อนส่งให้ `research` · จุดเริ่มของ R1 เรียก `require_research_host(sentinel=<docs/evidence/ENV-002-sentinel.json>)` และบันทึก verdict คู่กับการรัน · ไม่ PASS = ไม่รัน · (v2.1, F9; v2.2, r2 F9, r2 F29) หลัง `require_research_host` คืน PASS จุดเริ่มของ R1 เรียก `envcheck.host_lines()` และบันทึกบรรทัด `roots:`, `apps:`, `tools:` และ `wine:` คู่กับ verdict · โค้ดของ R1 เทียบสี่บรรทัดนี้กับบรรทัดที่ commit ไว้ในหลักฐานของ ENV-002 (รูปแบบที่เก็บเป็นของ contract SLICE-R1): home ใน `roots:` ต่าง = ไม่รัน · `apps:`, `tools:` หรือ `wine:` ต่าง = ไม่รันจนกว่าเจ้าของยืนยัน AC-03 ข้อ 4 เรื่อง VM, container และบัญชีผู้ใช้ซ้ำ แล้ว commit บรรทัดใหม่ · R1 สร้าง roots ด้วย `default_roots(extra_data_dirs)` เท่านั้น (roots ที่ประกอบเองข้ามการค้น Wine prefix ได้)
- **SLICE-R1 (ต่อ):** จุดเริ่มของ R1 สร้าง `ResearchRoots` ชุดเดียว แล้วส่งชุดนั้นให้ทั้ง `require_research_host(roots=…, sentinel=…)` และ loader · loader อ่าน snapshot จาก `roots.data_dirs` เท่านั้น (ค่าตั้งต้น `<repo>/data` ซึ่งรวมโฟลเดอร์รับไฟล์ `<repo>/data/transfer/` ของ D-021) จึงอ่านได้เฉพาะโฟลเดอร์ที่ `excluded_period` ตรวจแล้วในรอบเดียวกัน
- **Acquisition host (หลัง ENV-1):** `data.acquire` และการประเมิน holdout รันเมื่อ `host_report.py --role acquisition` เป็น PASS เท่านั้น · select บน holdout ใช้รายการที่ freeze (D-014, D-017) · ลำดับการตัด holdout และช่องทางส่ง snapshot ตาม D-021 · **การประเมิน holdout ต้องมีการแก้ guard ของ `research` (ตอนนี้ปฏิเสธทุกแท่งตั้งแต่ cutoff โดยไม่มี role หรือข้อยกเว้น) ผ่าน contract และ review ของตัวเอง:** ENV-1 ไม่ได้ให้สิทธิ์นี้

## Invariants
- ตัวตรวจอ่านเฉพาะ: การมีอยู่ของ path, รายการ drive/resource/โปรเซส/Uninstall entry จาก OS, manifest JSON ใน data dirs และไฟล์ที่ต้องค้น sentinel ตามกฎ · ไม่อ่าน .env, Credential Manager, `cmdkey`, ไฟล์ .rdp หรือเนื้อหาโฟลเดอร์ของ terminal (AGENTS.md) · ไม่เปิดไฟล์ cloud-only
- ไม่เชื่อมต่อเครือข่าย (ไม่มี subprocess, socket, http) ไม่เขียน ไม่ลบไฟล์ · การลบเป็นขั้นตอนของเจ้าของใน runbook
- sentinel เป็นข้อมูลปลอมที่ติดป้าย `synthetic` ไม่ใช่ holdout จริง · ไฟล์ไม่ถูกคัดลอกมาเครื่องเจ้าของ
- `research`, `backtest`, `strategy` ยัง import `data.acquire`, `broker` หรือ `app` ไม่ได้
- UNKNOWN ไม่ถือว่าผ่าน · R1 เริ่มได้เมื่อ `require_research_host` คืน PASS เท่านั้น
- (v2.0; v2.1, F16) ไม่ติดตั้ง MT5, Wine หรือแพ็กเกจ `MetaTrader5` บน Mac ไม่ว่าด้วยเหตุใด (รวมเพื่อทดสอบและเพื่อย้อน) · กรณีของ macOS ทดสอบด้วยโฟลเดอร์ชั่วคราวและค่าปลอมเท่านั้น ยกเว้นรอบควบคุมของ AC-01 (โฟลเดอร์เปล่าสองตัวที่เจ้าของสร้างและลบเอง; v2.2, r2 F35)
- (v2.0) agent ไม่อ่าน Keychain, รายการ credential ของ Windows App หรือไฟล์ `.rdp` · การตรวจรหัสที่บันทึกไว้เป็นของเจ้าของ
- (v2.0) tests ที่ล็อกของ v1.9 ไม่ถูกลบ ข้าม หรือทำให้อ่อนลง: (v2.1, F2) ทุกแถวของตารางกรณีที่ล็อก (`_ENVCHECK_FORBIDDEN`, `_ENVCHECK_ALLOWED` และ tests ของ acceptance) คงเดิมพร้อมผลที่คาดไว้ทุกตัวอักษร · ข้อยกเว้นเดียว (คำตัดสินข้อ 2 ของ v2.1): patch ของผู้เขียน tests เพิ่มแถว และแก้ฟังก์ชันกับค่าคงที่ของตัวตรวจ envcheck ใน `tests/architecture/test_imports.py` (อย่างน้อย `_ENVCHECK_CTYPES_DENIED`, `_ENVCHECK_CALLED`, การ resolve handle ของ library และกฎเปิดตอน import) เท่าที่รูป ctypes ของ darwin ใน AC-06 ต้องใช้ · ผู้เขียน tests ระบุทุกฟังก์ชันและค่าคงที่ที่แก้พร้อม diff ใน handoff ให้เจ้าของอนุมัติก่อน apply · จุดอื่นที่ต้องเปลี่ยน รายงานให้เจ้าของตัดสินก่อนแก้ · (v2.1, F5) ข้อยกเว้น symlink ไม่แตะ assertion ที่ล็อกข้อใด (ตรวจ 2026-11-17: tests ที่ล็อกไม่สร้าง symlink และ host ปลอมไม่มี `.venv/bin`)

## Negative cases
terminal ติดตั้งอยู่ (Program Files, portable ใต้ profile, Uninstall entry, โปรเซสรันอยู่) · มี `%APPDATA%\MetaQuotes` · `MetaTrader5` import ได้ · มีโฟลเดอร์ holdout · parquet ใน data dir ที่ manifest จบหลัง cutoff / ตรง cutoff (PASS) / ไม่มี manifest / manifest เสีย / manifest ของโฟลเดอร์ที่ไม่มีชื่อไฟล์นั้น · CSV รายงานนอก data dirs (ไม่ตรวจ: PASS) · `.tkc` ใต้ repo · mapped drive หรือ UNC ที่ต่ออยู่ · ไฟล์ที่ hash ตรง sentinel บน Desktop หรือ OneDrive (รวม Desktop ที่ OneDrive ย้ายไป) · สำเนา `.txt` ที่เปลี่ยนชื่อแต่มี token ใต้ `<repo>/data/transfer/` (FAIL) · ไฟล์ `.json` แบบ cloud-only ใน OneDrive ที่ขนาดเท่า sentinel (UNKNOWN และไม่ถูกเปิด) · ไฟล์ `.txt` แบบ cloud-only ใต้ `<repo>/data/` (UNKNOWN และไม่ถูกเปิด) · `.env.json` ข้างสำเนา sentinel (ไม่ถูกเปิด) · ไฟล์ใน repo นอกเหนือ `ENV-002-sentinel.json` ที่มี token (FAIL) · manifest ที่จบหลัง cutoff ในโฟลเดอร์ที่ส่งด้วย `--data-dir` หรือใน `<repo>/data/transfer/` (FAIL) · vault path มีบนเครื่องนี้ · ไม่ให้ sentinel (UNKNOWN) · อ่านไม่ได้เพราะสิทธิ์ (UNKNOWN) · `.env` อยู่ข้างสำเนา sentinel (ต้องไม่ถูกเปิด) · แท่งปลอมของช่วงที่ตัดออกเข้า `run_variant`/`random_entry_baseline` (`HoldoutRefused`, registry ไม่เปลี่ยน)

(v2.0) กรณีของ macOS (โฟลเดอร์ชั่วคราว, Facts ปลอม และฟังก์ชันระดับโมดูลของตัวอ่าน darwin; v2.1, F1, F4): แอป `MetaTrader 5.app` ใน /Applications หรือ ~/Applications (FAIL) · แอปชื่อ `metatrader 5.APP` (FAIL: ไม่สนตัวพิมพ์) · แอปอื่นชื่อ `MetaEditor.app` (PASS) · โฟลเดอร์ `net.metaquotes.wine.metatrader5` หรือ `Metatrader 5` ใต้ Application Support (FAIL และไม่ถูก list) · `terminal64.exe` ระดับ 2 ใต้ `drive_c/Program Files` ของ prefix ของ PlayOnMac, CrossOver หรือ `~/.wine` (FAIL) และระดับ 3 (PASS) · ไม่มี Wine prefix เลย (PASS ไม่ใช่ UNKNOWN) · โฟลเดอร์ `Bottles` หรือ `wineprefix` มีอยู่แต่ list ไม่ได้ (v2.1, F9: `default_roots` ยก OSError → CLI `RESEARCH HOST: UNKNOWN` exit 1 และ `require_research_host` ยก `ResearchHostError`) · โฟลเดอร์ `WinePrefix` ตัวพิมพ์ต่าง (พบ prefix เหมือนกัน) · แอป `Docker.app` หรือ `UTM.app` ใน /Applications (verdict ไม่เปลี่ยน และบรรทัด `apps:` ของ `host_lines()` มีชื่อแอป) · (v2.2, r2 F9) โฟลเดอร์ `.colima` ระดับ 0 ของ home (verdict ไม่เปลี่ยน, `tools: .colima`, และ audit hook ไม่เห็น `os.scandir` ใต้โฟลเดอร์นั้น) · ไม่มีชื่อใดในรายการ (`tools: none`) · โปรเซสที่ path อยู่ใต้ `MetaTrader 5.app` หรือชื่อ `terminal64.exe` (FAIL) · รายการโปรเซสอ่านไม่ได้ (UNKNOWN) · mount ชนิด `smbfs` หรือ `nfs` (FAIL) · mount ชนิดที่ไม่รู้จักที่มี MNT_LOCAL (UNKNOWN) · มีแต่ `/` ชนิด `apfs`, `devfs` และ `autofs` จาก `map auto_home` (PASS; v2.2, r2 F26) · ไฟล์ `.json` ที่มี flag dataless ขนาดเท่า sentinel ใน iCloud Drive (UNKNOWN และไม่ถูกเปิด) · ไฟล์ `.txt` dataless ใต้ `<repo>/data/` (UNKNOWN และไม่ถูกเปิด) · `.<ชื่อ>.icloud` ใต้ data dir (UNKNOWN) · โฟลเดอร์ใน search_dirs ที่ list ไม่ได้เพราะ Privacy (UNKNOWN) · (v2.1, F5) `.venv/bin/python` → interpreter ที่กำลังรัน (ไม่ UNKNOWN ไม่ถูกเปิด) · `.venv/bin/python3` → `python` → interpreter ที่กำลังรัน (ไม่ UNKNOWN) · chain ที่ออกนอกโฟลเดอร์ผ่าน symlink อื่นแต่จบที่ interpreter ที่กำลังรัน (ไม่ UNKNOWN) · `.venv/bin/python3.9` → ไฟล์ธรรมดาอื่นนอก repo (UNKNOWN) · `.venv/bin/python` → สำเนาของ interpreter ที่ path อื่น (UNKNOWN) · link ขาด, วนกลับ หรือชี้โฟลเดอร์ (UNKNOWN) · tests สร้าง link ไปที่ `os.path.realpath(sys.executable)` ในโฟลเดอร์ชั่วคราว นอกช่วงที่ envkit บันทึก side effect (`os.symlink` อยู่ในรายการต้องห้ามของ envkit.py:197) · symlink ชื่ออื่นใน `.venv/bin/` หรือ `python` ที่อยู่ที่อื่นใต้ repo (UNKNOWN) · `collect` จริงบน platform ที่ไม่ใช่ `win32` หรือ `darwin` (UNKNOWN ไม่มีวัน PASS)

(v2.1, F6) กรณีเพิ่มของ macOS: โฟลเดอร์ dataless ใน iCloud Drive (UNKNOWN ของ `sentinel` และไม่ถูก list) · โฟลเดอร์ dataless ใต้ `<repo>/data/` (UNKNOWN และไม่ถูก list) · `.<ชื่อ sentinel>.icloud` ใต้ search_dirs อย่างเดียว (FAIL) · `.x.json.icloud` ใต้ search_dirs อย่างเดียว (UNKNOWN) · `.x.png.icloud` ใต้ search_dirs อย่างเดียว (ข้าม: PASS) · `is_cloud_only` ตัวจริงกับ stat ปลอมที่มีแต่ `st_flags` = `0x40000000` (True) และที่ไม่มีทั้ง `st_flags` กับ `st_file_attributes` (False)

(v2.1, F7; v2.2, r2 F7: แต่ละกรณีบอกฟังก์ชันที่ถูกทดสอบ) กรณีเพิ่มของ macOS · บน `read_process_paths` โดยแทน `_darwin_list_pids` และ `_darwin_pid_path` ด้วยตัวปลอม: รายการ pid ไม่มี PID ของตัวเอง (ยก OSError) · path ของ PID ตัวเองไม่ตรงกับ `own_path` (ยก OSError) · `_darwin_pid_path` คืน errno ENOMEM หรือ EPERM (ยก OSError) · คืน errno ESRCH (ข้าม: คืน path ที่เหลือเมื่อ PID ของตัวเองอ่านได้) · pid 0 (ข้าม) · `_darwin_list_pids` คืนจำนวน 0 (ยก OSError) · คืนจำนวนเท่า capacity (เรียกใหม่ด้วย capacity ที่ใหญ่ขึ้นจนจำนวนน้อยกว่า capacity) · `_darwin_list_pids` ยก OSError (ยก OSError) · บน `collect` ที่แทน `read_process_paths` ให้ยก OSError: `process_names` เป็น None และ `terminal_install` เป็น UNKNOWN · บน `classify_processes`: โปรเซสชื่อ `wine64-preloader` หรือ `wineserver` ที่ path ไม่มี component ที่ชื่อมี `metatrader` (`process_names` None → UNKNOWN; จำนวน Wine loader 1) · (v2.3, r3 F33) path `/Users/x/MetaTrader 5/bin/wine64-preloader` (component ไม่มี `.app`: path อยู่ใน `terminal_paths` → FAIL) · path `/Users/x/dev/metatrader-notes/.venv/bin/python` (FAIL ตามกฎแบบเข้ม) · กรณีของ mount อยู่ในย่อหน้า r2 F26

(v2.1, F8) กรณีเพิ่มของ macOS: `net.metaquotes.wine.metatrader4` (FAIL และไม่ถูก list) · `Metatrader 4` (FAIL) · `METATRADER 5` (FAIL: ไม่สนตัวพิมพ์) · `net.other.app` (PASS) · Application Support ที่ list ไม่ได้ (UNKNOWN ของ `terminal_data`) · โฟลเดอร์ `metatrader 5` ที่มี `.txt` มี token โดย home และ data dir ครอบ และ appdata อยู่นอก `<home>/Library` ในกรณีนี้ (r2 F28) (`terminal_data` FAIL และ audit hook ไม่เห็น `os.scandir` หรือ `open` ใต้โฟลเดอร์นั้น) · แอป `Exness MetaTrader 5.app` (FAIL) · โปรเซสที่ path อยู่ใต้ `Exness MetaTrader 5.app` นอก /Applications (FAIL)

(v2.1, F11) กรณีเพิ่มของ macOS: `default_roots` บน darwin โดยมีตัวแปร `USERPROFILE` และ `APPDATA` ชี้โฟลเดอร์อื่น (roots ยังมาจาก `_darwin_home()`) · บรรทัด `roots:` ของ CLI ไม่มี token

(v2.1, F12) กรณีเพิ่มของ macOS ที่กฎมีแต่ยังไม่มีกรณี: mount ชนิด `apfs` ที่ไม่มี MNT_LOCAL (FAIL) · `afpfs`, `webdav`, `ftp` (FAIL) · `autofs` ตามกฎของ F19 · getfsstat ล้ม (UNKNOWN) · `.json` dataless ใน iCloud Drive ที่ขนาดไม่เท่า sentinel (PASS และไม่ถูกเปิด) · โฟลเดอร์ `MetaTrader 5` ระดับ 0 ของ `drive_c/Program Files` (FAIL) · `terminal64.exe` ใต้ home ระดับ 3 (FAIL) และระดับ 4 (PASS) · การค้น home ไม่ list `Library` และ `.ssh` (audit hook ไม่เห็น `os.scandir` ใต้สองโฟลเดอร์นั้น) · โฟลเดอร์ใต้ home ที่อยู่ในรายการข้ามและ list ไม่ได้ (ข้าม: PASS และอยู่ในบรรทัด `skipped:`), โฟลเดอร์อื่นใต้ home ที่ list ไม่ได้ (UNKNOWN) และ home เอง list ไม่ได้ (UNKNOWN) · `~/Library/CloudStorage` มีอยู่แต่ list ไม่ได้ (`default_roots` ยก OSError) · โฟลเดอร์ชื่อ `MetaTrader 5` ที่ไม่ลงท้าย `.app` ระดับ 0 ของ /Applications เป็น FAIL ตามกฎของ r2 F33 (v2.1 ปล่อยไว้ไม่กำหนดผล)

(v2.1, F15) กรณีเพิ่มของ macOS: mount ชนิด `apfs` ที่มี MNT_LOCAL ที่ `/Volumes/USB` (UNKNOWN) · mount ชนิด `smbfs` ที่ `/Volumes/share` (FAIL: กฎ FAIL มาก่อน) · mount `apfs` ที่ `/System/Volumes/Data` (PASS) · (v2.2, r2 F15) หลัง `collect` ที่มี mount `/Volumes/USB`: บรรทัด `mounts:` ของ `host_lines()` ลงท้ายด้วย `; not allowed: /Volumes/USB` · (v2.2, r2 F32) mount `apfs` ที่มี MNT_LOCAL ที่ `/Users/x/mnt` (UNKNOWN) · `devfs` ที่ `/dev` (PASS) · (v2.3, r3 F32) `apfs` ที่มี MNT_LOCAL ที่ `/System/Volumes/Data/Users/x/mnt` (UNKNOWN) · `apfs` ที่มี MNT_LOCAL ที่ `/System/Volumes/Preboot` (PASS)

(v2.1, F19) กรณีเพิ่มของ macOS: `autofs` จาก `map auto_home` ที่ไม่มี MNT_LOCAL (PASS) · `autofs` จาก `map -fstab`, `map -static` หรือ `map -hosts` (UNKNOWN) · `os.uname().machine` เป็น `x86_64` (UNKNOWN ของ `terminal_install` และ `network_shares`) · mount ชนิด `ntfs` หรือ `lifs` ที่มี MNT_LOCAL (UNKNOWN; ไม่มี MNT_LOCAL = FAIL)

(v2.3, r3 F45) รายการฐานของกรณี mount ทุกข้อในหัวข้อนี้ที่คาด PASS หรือคาดผลจาก mount ตัวเดียว: `/` ชนิด `apfs` ที่มี MNT_LOCAL บวก mount ของกรณี · `devfs` อยู่ที่ `/dev` · `autofs` จาก `map auto_home` อยู่ที่ `/System/Volumes/Data/home` · กรณีที่บอกจุด mount ไว้ใช้จุดนั้น · กรณีเพิ่ม: `autofs` จาก `map auto_home` ที่ `/home` (UNKNOWN: จุด mount นอกรายการอนุญาต)

(v2.2, r2 F26) กรณีของ mount บน `classify_mounts` (แทนกรณี mount ของย่อหน้า F7 เดิม): รายการ mount ไม่มี `/` (UNKNOWN) · `/` ชนิด `hfs` ที่มี MNT_LOCAL (UNKNOWN) · `/` ชนิด `apfs` ที่ไม่มี MNT_LOCAL (FAIL) · `/` ชนิด `nfs` (FAIL) · รายการที่มีทั้ง mount ที่เข้ากฎ FAIL และ mount ที่เข้ากฎ UNKNOWN (FAIL)

(v2.3, r3 F28) กรณีเพิ่ม (ทุกแพลตฟอร์ม, บน `evaluate`): Facts ที่ `metaquotes_exists=False`, appdata อยู่ใต้ data dir ที่ครอบ, โฟลเดอร์ `metatrader 5` ระดับ 0 ของ appdata มี `.txt` ที่มี token (`holdout_dir`, `excluded_period` และ `sentinel` เป็น UNKNOWN; audit hook ไม่เห็น `os.scandir` หรือ `open` ใต้โฟลเดอร์นั้น)

(v2.2, r2 F10) กรณีเพิ่มของ macOS: โฟลเดอร์ที่ list ไม่ได้ระดับ 1 ของ `drive_c/Program Files` ของ prefix (UNKNOWN ของ `terminal_install`) · `drive_c` ของ prefix มีอยู่แต่ list ไม่ได้ (`default_roots` ยก OSError) · โฟลเดอร์ของ prefix เป็น symlink (`default_roots` ยก OSError) · (v2.3, r3 F43) `Bottles` เป็น symlink (`default_roots` ยก OSError) · `drive_c/Program Files` เป็น symlink (`default_roots` ยก OSError) · prefix ที่ไม่มี `drive_c` (PASS, `wine: 1 prefixes`)

(v2.2, r2 F12) กรณีเพิ่มของ macOS สำหรับกฎของ v2.1 ที่ยังไม่มีกรณี: `collect` โดยมี `DYLD_INSERT_LIBRARIES` ใน `os.environ` (UNKNOWN ของ `terminal_install` และ `network_shares`; `read_process_paths`, `read_mounts` และตัวอ่านดิบไม่ถูกเรียก) · โฟลเดอร์ dataless ระดับ 1 ของ home (ไม่ถูก list, อยู่ในบรรทัด `skipped:`, PASS) · `~/Applications` ไม่มีอยู่ (PASS) และ `/Applications` มีอยู่แต่ list ไม่ได้ (UNKNOWN ของ `terminal_install`) · `terminal64.exe` ใต้ `<home>/x/.git/`, `<home>/x/.venv/` หรือ `<home>/x/node_modules/` (PASS) · โฟลเดอร์ `MetaQuotes` ใต้ Application Support (FAIL) · `metaquotes2` และ `my metatrader` ใต้ Application Support (PASS) · `--sentinel-file` ที่ชี้ไฟล์ใต้ `<appdata>/Metatrader 5/` (ไม่ถูกเปิด, `sentinel` UNKNOWN) · root ของ data dir หรือ search dir ที่มี ancestor เป็นโฟลเดอร์ dataless (UNKNOWN และ root ไม่ถูก stat หรือ list: ตรวจ ancestor จากบนลงล่างก่อน) · `host_lines()` หลัง `research_host_report` ที่ตั้ง platform เป็น darwin พร้อมตัวอ่านดิบปลอม (3 pid ซึ่งข้าม 1, mount `/` apfs, `/dev` devfs, `/System/Volumes/Data/home` autofs จาก `map auto_home`, home ปลอมที่ไม่มี Wine prefix): มีบรรทัด `reader: darwin`, `processes: 3 listed, 2 paths read, 1 skipped, 0 wine loaders`, `mounts: 3 (apfs, devfs, autofs)` และ `wine: 0 prefixes; looked at none` ตรงกับค่าปลอม · (v2.3, r3 F25) `host_lines()` หลัง `research_host_report` ที่แทน `collect` ด้วยตัวปลอม โดยรันต่อจาก test ข้างต้นใน process เดียวกัน (`processes: not read`, `mounts: not read`, `wine: not read`) · `host_lines()` เมื่อ `_HOST_SUMMARY` ว่าง (test แทนด้วย dict ว่างผ่าน `monkeypatch.setattr`: คืนแค่ `reader:`) · token ของ sentinel ที่ส่งให้ `research_host_report` ปรากฏใน path ของ roots ปลอม (บรรทัด `roots:` มี `<token>` และไม่มี token) · (v2.3, r3 F25) roots ที่ประกอบเองโดย `program_files=()` แต่ home ปลอมมี prefix ที่มี `terminal64.exe` ระดับ 1 (FAIL ของ `terminal_install` และ `wine: 1 prefixes`)

(v2.2, r2 F30, r2 F31, r2 F33) กรณีผสมและกรณีเพิ่มของ macOS: โปรเซส `terminal64.exe` พร้อม `wineserver` (FAIL ของ `terminal_install`: path ของ `terminal64.exe` อยู่ใน `terminal_paths`) · พบ `terminal64.exe` ใต้ home และมีโฟลเดอร์อื่นใต้ home ที่ list ไม่ได้ (FAIL ไม่ใช่ UNKNOWN) · `.<ชื่อ sentinel>.icloud` ใต้ `<repo>/data/` (FAIL ของ `sentinel`) · บน `read_mounts` โดยแทน `_darwin_mounts`: คืนจำนวนเท่า capacity (เรียกใหม่ด้วย capacity ที่ใหญ่ขึ้น) และ `_darwin_mounts` ยก OSError (ยก OSError → `network_shares` UNKNOWN) · โฟลเดอร์ `MetaTrader 5` ที่ไม่ลงท้าย `.app` ระดับ 0 ของ /Applications (FAIL) · `MetaTrader 5.app` ใต้ `/Applications/Trading/` (ระดับ 1: PASS จากกฎแอป เป็นข้อที่เหลือ)

(v2.2, r2 F41) กรณีเพิ่มของ macOS: `~/Library/CloudStorage` มีโฟลเดอร์ `OneDrive-Personal` และ `GoogleDrive-someone@example.com` (บรรทัด `roots:` ลงท้ายด้วย `cloud storage: 2 (OneDrive, GoogleDrive)` และไม่มีข้อความหลัง `-` ของชื่อโฟลเดอร์ทั้งสอง · ทั้งสองโฟลเดอร์ยังถูกค้นเป็น search_dirs)

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 (v2.0 แทนฉบับ Windows ของ v1.9) Given เครื่อง Mac หลังทำตาม runbook ฉบับ macOS (ไม่มีแอป MetaTrader, ไม่มีโฟลเดอร์ Wine ของ MT5, ไม่มี network volume ที่ mount อยู่ · (v2.1, F10) รันจากแอปเดียวกับที่ R1 จะรัน คือ Visual Studio Code (terminal ในแอปนั้น) และแอปนั้นได้สิทธิ์ Files and Folders ของ Desktop, Documents, Downloads และ iCloud Drive เท่านั้น ไม่มี Full Disk Access · หลักฐานบอกชื่อแอป · ล้าง Trash ก่อนรัน · ทำข้ออื่นของหัวข้อ "Runbook ฉบับ macOS: ข้อที่ต้องมี" ครบ) และ repo อยู่ที่ commit ที่ตรวจแล้ว (`git rev-parse --short HEAD` ตรงกับที่ Claude ให้ และ `git status --short` ไม่พิมพ์อะไร) When เจ้าของรันคำสั่ง CLI (zsh) ของ contract พร้อม `--sentinel-file docs/evidence/ENV-002-sentinel.json` Then ทุก item เป็น PASS, รายงานมีบรรทัด `reader: darwin` (v2.1, F1), home ในบรรทัด `roots:` คือ home ของเจ้าของเอง (v2.1, F11), บรรทัดสุดท้ายเป็น `RESEARCH HOST: PASS` และ exit status เป็น 0 · (v2.1, F7) บรรทัด `processes:` มี `paths read` มากกว่า 0 และชนิด mount ในบรรทัด `mounts:` ตรงกับผลของคำสั่ง `mount` ที่เจ้าของรันเวลาเดียวกัน · (v2.1, F7, คำตัดสินข้อ 5) รอบควบคุมก่อนรอบ PASS: เจ้าของสร้างโฟลเดอร์เปล่า `~/Applications/MetaTrader 5.app` และ `~/Library/Application Support/net.metaquotes.wine.metatrader5` (ไม่ใช่การติดตั้ง) แล้วรันคำสั่งเดียวกัน → `terminal_install` และ `terminal_data` ต้องเป็น FAIL และ exit status ไม่ใช่ 0 → ลบสองโฟลเดอร์ด้วย `rmdir` (ไม่ลากลง Trash) แล้วตรวจด้วย `ls -d` ว่าไม่มีทั้งสอง (v2.2, r2 F35) → รันใหม่ได้ PASS · หลักฐานมี commit, เวลา และรายงานทั้งหมดของทั้งสองรอบ
- AC-01 ฉบับ v1.9 (Windows, เลิกใช้เมื่อ v2.x อนุมัติ; v2.3, r3 F47): Given เครื่องเจ้าของหลังทำตาม runbook (ถอน terminal, ลบ `%APPDATA%\MetaQuotes`, ไม่มี mapped drive ไป VPS) When เจ้าของรันคำสั่ง CLI ของ contract พร้อม `--sentinel-file docs/evidence/ENV-002-sentinel.json` Then ทุก item เป็น PASS และบรรทัดสุดท้าย `RESEARCH HOST: PASS`
- AC-02 Given สภาพผิดทีละข้อในโฟลเดอร์ชั่วคราวและ Facts ปลอม (ตามรายการ Negative cases) When `evaluate` Then item นั้นเป็น FAIL หรือ UNKNOWN ตามกฎ, verdict ตามลำดับผลรวม · manifest ที่จบตรง cutoff และ CSV นอก data dirs ผ่าน · ไฟล์ที่ห้ามเปิด (รวม `.env.json` ซึ่งเป็นทั้งไฟล์ต้องห้ามและนามสกุล `.json`) และไฟล์ cloud-only ไม่ถูกเปิด: ตรวจด้วย `sys.addaudithook` ที่ดักเหตุการณ์ `"open"` (ครอบ `builtins.open`, `io.open`, `Path.open`, `os.open`) และทำงานเฉพาะเมื่อ flag ของ test เปิด เพราะ audit hook ถอดไม่ได้ · cloud-only จำลองด้วยการแทน `envcheck.is_cloud_only` · สำเนา `.txt` ที่เปลี่ยนชื่อแต่มี token ใต้ `<repo>/data/transfer/` เป็น FAIL · ไฟล์ `.txt` cloud-only ใต้ `<repo>/data/` เป็น UNKNOWN · ไฟล์ `.txt` cloud-only ใน `--data-dir` ที่อยู่ในโฟลเดอร์ OneDrive ปลอมเป็น UNKNOWN และไม่ถูกเปิด · ไฟล์ `.json` cloud-only ขนาดเท่า sentinel ใน OneDrive เป็น UNKNOWN · ไฟล์ `.png` cloud-only ขนาดเท่า sentinel ใน OneDrive ไม่ทำให้เป็น UNKNOWN · (v2.0; v2.1, F4) When เพิ่มสำหรับกรณีของ macOS: `evaluate`, `collect` ที่ตั้ง platform เป็น `darwin` พร้อมตัวอ่านดิบปลอม, `default_roots`, `main`, `host_lines` หรือฟังก์ชันระดับโมดูลของตัวอ่าน darwin ตามที่แต่ละกรณีระบุ (v2.2, r2 F12) · ทุกกรณีของ macOS ในหัวข้อ Negative cases (รวมกรณีเพิ่มของ v2.1) ให้ผลตามที่เขียนไว้ และไฟล์ dataless กับโฟลเดอร์ของ `terminal_data` ไม่ถูกเปิดหรือ list (ตรวจด้วย audit hook เดิม)
- AC-03 (v2.0 แทนฉบับ Windows ของ v1.9) Given sentinel ที่สร้างบน VPS ด้วย `make_sentinel.py` และค่าที่ commit ใน `docs/evidence/ENV-002-sentinel.json` When เจ้าของทำ break-it test จากเครื่อง Mac (research identity) โดย Quit แอปของ agent ตาม checklist ข้อ C9 ก่อน (v2.2, r2 F14) Then (1) ตัวควบคุม: `nc -vz -G 5 <vps> 3389` สำเร็จ (พิสูจน์ว่า IP ถูกและ Mac ออนไลน์อยู่; บันทึกข้อความและ exit status) (2) (v2.1, F13) `nc -vz -G 5 <vps> <port>` ที่พอร์ต 22, 80, 139, 443, 445, 5985, 5986 ล้มทั้งหมด · บันทึกข้อความและ exit status ของแต่ละพอร์ต (`nc -z` ไม่พิมพ์อะไรเมื่อล้ม): ที่คาดคือ timeout; `Connection refused` ต้องมีคำอธิบายจากฝั่ง ENV-001 (3) (v2.1, F13) `smbutil view -g -N //<vps>` ล้ม (guest เท่านั้น ไม่ถามรหัส จึงไม่มีอะไรถูกบันทึกลง Keychain; ไม่ใช้ Finder) · เจ้าของวางข้อความที่คำสั่งพิมพ์ แล้ว `mount` ไม่มีบรรทัด `smbfs` · flag มาจาก `man smbutil` บน Mac เครื่องนี้ ยังไม่เคยรันกับ server จริง (4) (v2.1, F14) เจ้าของทำ checklist "credential และ session บน Mac" ของหัวข้อ "Runbook ฉบับ macOS: ข้อที่ต้องมี" ครบทุกข้อ C1–C10 เอง (agent ห้ามทำและห้ามอ่าน Keychain) แล้วยืนยันทีละข้อพร้อมเวลา · ข้อ C10 คือ: (v2.1, F9) Mac ไม่มี VM หรือ container ใดๆ (Windows หรือ Linux; Parallels, VMware Fusion, UTM, VirtualBox, Docker Desktop, OrbStack, colima/Lima, podman, qemu) ที่มี MT5 หรือ Wine รวมเครื่องมือที่ติดตั้งทาง command line, และ Mac มีบัญชีผู้ใช้ที่ login ได้บัญชีเดียว หรือบัญชีอื่นไม่มี MT5 (5) บน VPS `Get-FileHash` ของ sentinel ตรงกับค่าที่ commit ณ เวลาตรวจ (6) item `sentinel` ของ envcheck บน Mac เป็น PASS (7) (v2.1, F13) เครื่อง Windows เดิมตาม D-023 ข้อ 2 ทาง 1: เจ้าของยืนยันทีละข้อพร้อมเวลาตามลำดับนี้: (a) `docs/proposals/` และ memory ของ Claude Code (โฟลเดอร์ `memory/` ของโปรเจกต์นี้ใต้ `.claude/projects/` ใน home) ย้ายมา Mac แล้ว และรายการ SHA-256 ของสองฝั่งตรงกัน (รายการอยู่ในหลักฐาน) · (v2.1, F15) ย้ายด้วยรายการไฟล์ที่ระบุชื่อเท่านั้น ไม่ใช้ Migration Assistant และไม่คัดลอกทั้งโฟลเดอร์ผู้ใช้หรือ `AppData` (b) ในทุก worktree บนเครื่อง Windows `git status --short` และ `git stash list` ไม่พิมพ์อะไร และ `git log --branches --not --remotes --oneline` ไม่พิมพ์อะไร (c) ถอน MT5 terminal แล้ว (d) ลบ `%APPDATA%\MetaQuotes` แล้ว (d2) (v2.2, r2 F37, คำตัดสิน r2 ข้อ 6; v2.3, r3 F46, คำตัดสิน r3: ใช้โค้ด v1.9) ก่อนลบ clone รันบนเครื่อง Windows หนึ่งครั้ง ที่ commit `c97aac6` ของ branch `feat/ENV-002-research-host-separation` (โค้ด v1.9 ซึ่งไม่มีบรรทัด `roots:` จึงไม่พิมพ์ path ของ profile Windows หรือชื่อโฟลเดอร์ OneDrive ในบรรทัดของ host) ใน PowerShell: `git checkout c97aac6` แล้ว `$env:PYTHONPATH="src"; uv run --offline python -m sochron.app.envcheck --role research` (ไม่ใส่ `--sentinel-file`) → `terminal_install`, `terminal_data` และ `network_shares` เป็น PASS (`sentinel` เป็น UNKNOWN และ exit status ไม่ใช่ 0 ตามคาด เพราะไม่ได้ให้ sentinel) · วางรายงานทั้งหมดในหลักฐาน พร้อมผลของ `git rev-parse --short HEAD` (ต้องเป็น `c97aac6`) และเวลา · detail ของ item ที่ไม่ PASS อาจมี path เต็ม: เจ้าของปิดบังชื่อบัญชีก่อน commit (e) ลบ clone และ worktree แล้ว (f) ไม่เปิด session ของ agent กับโปรเจกต์นี้บนเครื่องนั้นอีก (g) เครื่อง Windows เดิมไม่ถูกใช้เชื่อมต่อ VPS หรือ console ของผู้ให้บริการเลย ตั้งแต่เช่าจนถึงวันล้าง · ถ้าเคยเชื่อมต่อ: เจ้าของรัน `cmdkey /list` เอง (ไม่มี `TERMSRV/<IP ของ VPS>`), mstsc ไม่มี Saved credentials, ไม่มีไฟล์ `.rdp` ของ VPS, browser บนเครื่องนั้นไม่บันทึกรหัสของ console · หลักฐานมีคำสั่ง ผล เวลา และ hash ทั้งสองฝั่ง (IP ปิดบัง)
- AC-03 ฉบับ v1.9 (Windows, เลิกใช้เมื่อ v2.x อนุมัติ; v2.3, r3 F47): Given sentinel ที่สร้างบน VPS ด้วย `make_sentinel.py` และค่าที่ commit ใน `docs/evidence/ENV-002-sentinel.json` When เจ้าของทำ break-it test จากเครื่องตัวเอง (research identity) Then `Test-NetConnection <vps>` ที่พอร์ต 22, 80, 443, 445, 5985, 5986 ล้มทั้งหมด (3389 เปิดเป็นประตูของคน) · `dir \\<vps>\C$` และ share ของ vault ล้ม · เจ้าของรัน `cmdkey /list` เอง (agent ห้ามรัน) แล้วยืนยันว่าไม่มีรายการของ VPS · บน VPS `Get-FileHash` ของ sentinel ตรงกับค่าที่ commit ณ เวลาตรวจ · และ item `sentinel` ของ envcheck เป็น PASS · หลักฐานมีคำสั่ง ผล เวลา และ hash ทั้งสองฝั่ง (IP ปิดบัง)
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
- (F6) โฟลเดอร์ cloud ที่ตัวตรวจค้น (iCloud Drive และทุกโฟลเดอร์ระดับ 0 ของ `~/Library/CloudStorage`) ต้องถูกดาวน์โหลดไว้ในเครื่อง: ปิด Optimize Mac Storage หรือสั่ง Keep Downloaded / Download Now · โฟลเดอร์ที่ยังเป็น dataless ทำให้ `sentinel` เป็น UNKNOWN
- (F14) checklist "credential และ session บน Mac" ของ AC-03 ข้อ 4 (เจ้าของทำเองทุกข้อ agent ห้ามทำ; v2.2, r2 F24: ข้อย่อยใช้เลข C1–C10 เพื่อไม่ซ้ำกับตัวอักษรของ decisions): C1 Windows App → Settings → Credentials ไม่มีรายการของ VPS และรายการ PC ไม่ผูก credential C2 แอป Passwords และ Keychain Access (keychain `login`) ค้น `com.microsoft.rdc.macos`, `Windows App`, `Remote Desktop`, IP ของ VPS, ชื่อผู้ใช้ RDP และโดเมนของผู้ให้บริการ แล้วไม่พบรายการของ VPS (รวมรายการที่ sync มาจากอุปกรณ์อื่น) C3 Windows App → Settings → General ช่อง "If folder redirection is enabled for RDP files or managed resources, redirect:" ไม่ได้เลือกโฟลเดอร์ · การ์ดของ VPS (Edit): แท็บ Folders ไม่ติ๊ก Redirect folders, แท็บ Devices & Audio ไม่ติ๊กอุปกรณ์ใด, clipboard ตั้งตามที่เจ้าของเลือกใน ENV-001 (ค) (Disabled หรือค่าที่ใช้ส่งข้อความตาม D-021 ข้อ 4) และบันทึกค่าที่ตั้งไว้ในหลักฐาน C4 browser ทุกตัวบน Mac ไม่บันทึกรหัสและ logout จาก console ของผู้ให้บริการแล้ว และ console เปิด 2FA ด้วยอุปกรณ์ที่ไม่ใช่ Mac C5 ไม่มี API token, ไฟล์ config ของ CLI ผู้ให้บริการ หรือ SSH key ของ VPS บน Mac C6 password manager ที่มี CLI หรือ extension ไม่เก็บรหัสของ VPS, console หรือบัญชีโบรกเกอร์ หรือถามการยืนยันตัวทุกครั้ง C7 browser และ Passwords ไม่บันทึกรหัสของบัญชีโบรกเกอร์ (Personal Area, MT5 login) C8 Privacy & Security → Screen Recording และ Accessibility ไม่มีแอปที่ agent รันอยู่ C9 (v2.2, r2 F14) ก่อนเปิด RDP หรือ console: Quit (⌘Q) Visual Studio Code, Claude, ChatGPT/Codex และทุกแอปที่ agent รันอยู่ (บน macOS การปิดหน้าต่างไม่ได้ปิดแอป) แล้วรันใน Terminal.app: `pgrep -ilf 'claude|codex|chatgpt'` ต้องไม่พิมพ์อะไร (`-i` ไม่สนตัวพิมพ์: ชื่อแอปขึ้นต้นด้วยตัวใหญ่) · เปิด console ใน browser หรือ profile ที่ไม่มี extension ของ Claude หรือ ChatGPT; ถ้ามี ให้รัน pgrep ซ้ำหลังเปิด browser C10 VM, container และบัญชีผู้ใช้อื่นตามถ้อยคำของ AC-03 ข้อ 4 · ชื่อเมนูมาจากหน้า Microsoft Learn และโพสต์ของผู้ใช้ที่อ่าน 2026-11-17 ยังไม่ได้ตรวจในแอปจริง (Windows App ยังไม่ได้ติดตั้งบน Mac) เจ้าของแก้ให้ตรงเมื่อใช้ครั้งแรก
- (F15, F19) ก่อนรัน envcheck ทุกครั้ง: ถอด external disk, disk image และ network volume ทั้งหมด (รวม Time Machine ผ่านเครือข่าย) · `mount` ต้องมีแต่จุด mount `/`, `/dev` และใต้ `/System/Volumes/` (r2 F32)
- (F20) runbook เขียนไว้ตรงผลของ AC-01 ว่า `mt5_package: PASS` และส่วน "vault path" ของ `sentinel` บน Mac ไม่นับเป็นหลักฐาน (ล้มไม่ได้บน macOS) · หลักฐานของ AC-01 คือ item ที่เหลือและรอบควบคุม
- (F21) repo อยู่ใต้ `~/Documents`: System Settings → Apple Account → iCloud → Drive ต้องปิด "Desktop & Documents Folders" (เจ้าของยืนยันพร้อมเวลา; agent อ่านค่านี้ไม่ได้) หรือย้าย repo ออกนอก `~/Documents` และ `~/Desktop` · ถ้าเปิดอยู่ repo, `.venv` และ snapshot ใน `data/transfer/` จะ sync ขึ้น iCloud และ envcheck จะเป็น UNKNOWN เมื่อไฟล์ถูกย้ายออกจากเครื่อง

## Risk, data and external side effects
**Threat model ย่อ (High):**
| ภัย | ทางเข้า | การป้องกัน | ที่เหลือ (ระบุตรงๆ) |
|---|---|---|---|
| research identity ดึงช่วง holdout จากโบรกเกอร์ | terminal + `MetaTrader5` บนเครื่องนี้ | ถอน terminal, ลบ `%APPDATA%\MetaQuotes`, item `terminal_*`, `mt5_package` ก่อนทุก R1 | ติดตั้งใหม่ได้เสมอ: envcheck ก่อนทุก R1 จับแบบติดตั้งปกติ, portable ใต้ profile ≤ 3 ระดับ, Uninstall entry และโปรเซส · portable ที่อื่นและไม่รันอยู่ยังหลุดได้ · (v2.1, F16) แถวนี้เขียนสำหรับเครื่อง Windows ของ v1.9 · บน Mac ไม่มีสิ่งที่ต้องถอน การป้องกันคือ item `terminal_*` ก่อนทุก R1 และกฎห้ามติดตั้งของ Invariants (`mt5_package` บน darwin ไม่นับเป็นการป้องกัน: F20; v2.2, r2 F16) · (v2.3, r3 F36) กฎ (1) ของ `sentinel` (vault path) ก็ล้มไม่ได้บน macOS เช่นกัน ((ญ) ข้อ 9) |
| research identity เข้า VPS | share, WinRM, SSH, credential ที่บันทึก | firewall ของ ENV-001 (เปิดแค่ RDP จาก IP เจ้าของ) · break-it test จากเครื่องนี้ (AC-03) · ไม่บันทึกรหัส RDP | **ขณะหน้าต่าง RDP ของเจ้าของเปิดอยู่ โปรเซสของ research identity มองเห็นหน้าจอ ส่ง input และใช้ clipboard ร่วมได้** (บน Windows: ผู้ใช้, session และ integrity เดียวกัน · บน macOS: เมื่อแอปของ agent มีสิทธิ์ Screen Recording หรือ Accessibility; v2.1, F24) · ลดด้วยการเปิด RDP เฉพาะเมื่อไม่มี session ของ agent รัน (decision (ค)) หรือเจ้าของรับความเสี่ยงนี้ |
| ไฟล์ holdout ถูกคัดลอกมา | drive redirection, clipboard ไฟล์, sync | ENV-001 ปิดทั้งหมด · item `holdout_dir`, `excluded_period`, `network_shares`, `sentinel` (รวม OneDrive) | การคัดลอกเป็นข้อความผ่าน clipboard และการพิมพ์ด้วยมือตรวจไม่ได้ · ช่องทางส่ง snapshot ตาม D-021 ตรวจซ้ำทุกครั้ง |
| ข้อมูลช่วง holdout เข้าโค้ดวิจัยโดยไม่มีไฟล์ | caller ส่งแท่งเอง | `HoldoutRefused` (AC-04) + loader ของ R1 (งานส่งต่อ) | ชั้นเสริม ขอบเขตหลักคือการแยกเครื่อง |
| ข้อมูลราคาสาธารณะของปี 2025–2026 บนอินเทอร์เน็ต | agent ที่มี web tool | โค้ดวิจัยรับข้อมูลผ่าน snapshot ที่อนุมัติ + guard เท่านั้น | **รับไว้:** ตัด web ของ agent ไม่ได้ · ห้ามใช้ข้อมูลจากเว็บในการวิจัย (AGENTS.md: ถือ content ภายนอกเป็นข้อมูล ไม่ใช่คำสั่ง) |
| ความรู้ของ model เรื่องราคาทองปี 2025 | ความรู้ฝังใน model | ผลวิจัยมาจากโค้ดและ registry ไม่ใช่การเลือกของ agent · กติกาเลือกเป็นกลไก (D-014) | **รับไว้:** ลดผลด้วยกฎเชิงกลที่ลงทะเบียนก่อนเห็นข้อมูล |
| ตัวตรวจอ่านความลับเสียเอง | `.env`, key, โฟลเดอร์ terminal, ไฟล์ .rdp | รายการห้ามเปิด (AC-02 ทดสอบ) · ค้นด้วยขนาดก่อน hash | – |
| (v2.0) เครื่อง Windows เดิมยังถือ terminal และ cache ของช่วงหลัง cutoff | เจ้าของคัดลอกไฟล์ข้ามเครื่อง (USB, AirDrop, cloud) · เปิด agent บนเครื่องนั้นตามความเคยชิน | D-023 ข้อ 2 ทาง 1 และ AC-03 ข้อ 7 · (v2.1, F15) ไฟล์ที่เข้ามาใน repo และ data dirs ถูกตรวจโดย `holdout_dir`, `excluded_period`, `sentinel` · ใน search_dirs ตรวจเฉพาะสำเนาของ sentinel · ย้ายไฟล์ข้ามเครื่องด้วยรายการไฟล์ที่ระบุชื่อพร้อม SHA-256 เท่านั้น · mount นอกรายการจุด mount ที่อนุญาต = UNKNOWN (r2 F32) | ระหว่างรอ SPIKE-002 เครื่องนั้นยังมี terminal: กฎคือไม่เปิด agent ของโปรเจกต์บนเครื่องนั้น ซึ่งเป็นคำยืนยันของเจ้าของ โค้ดตรวจไม่ได้ · (v2.1, F15) cache ของ MT5 ที่ถูกคัดลอกมาไว้นอก repo และ data dirs (เช่น Downloads) ตรวจไม่เจอ และโค้ดวิจัยอ่านได้ด้วย path เต็ม (จุดบอดเดียวกับ v1.9; ไม่เพิ่มกฎนามสกุล cache ใน search_dirs ตามคำตัดสินข้อ 10) |
| (v2.0) MT5 บน Mac ที่กฎ path ไม่เห็น | Wine prefix ที่อื่น (เช่น Whisky), Windows VM, web terminal ของโบรกเกอร์ใน browser | กฎชื่อแอป, prefix ที่รู้จัก, home ระดับ 0–3, โปรเซสที่รันอยู่ · คำยืนยันเรื่อง VM ใน AC-03 ข้อ 4 | **เสนอให้รับ (รอเจ้าของที่ decision (ญ); v2.1, F7; v2.2, r2 F36):** terminal ใต้ Wine prefix ที่อื่นหรือใน VM ตรวจไม่เจอทั้งตอนรันและไม่รัน (libproc เห็นแค่ตัว loader ของ Wine หรือ hypervisor) · กฎชื่อ `terminal64.exe` ของโปรเซสและกฎ Wine loader ยังไม่เคยพิสูจน์บน macOS · (v2.2, r2 F33) แอป MetaTrader ที่อยู่นอกระดับ 0 ของสองโฟลเดอร์แอป (เช่น ใน Downloads หรือโฟลเดอร์ย่อยของ /Applications) และยังไม่เคยเปิด ตรวจไม่เจอ (เปิดครั้งแรกแล้ว `terminal_data` จึงจับได้) · (v2.1, F8) แอปของโบรกเกอร์ที่ชื่อไม่มีคำว่า metatrader และ MT5 ใต้บัญชีผู้ใช้ macOS อื่นบนเครื่องเดียวกัน ตรวจไม่เจอ · ไม่ใช้ `/var/db/receipts` เป็นหลักฐาน (ยังไม่มีใครยืนยันชื่อ receipt ของตัวติดตั้ง MT5; คำตัดสินข้อ 6) · (v2.1, F9) bottle ของ CrossOver ที่ย้ายที่เก็บ (CrossOver 24+: Settings → System Integration หรือ `defaults write com.codeweavers.CrossOver BottleDir`), Whisky, Wineskin/Kegworks, และ VM หรือ container ที่ติดตั้งหลัง ENV-1 ตรวจไม่เจอด้วยโค้ด: พึ่งคำยืนยันซ้ำของเจ้าของเมื่อบรรทัด `apps:`, `tools:` หรือ `wine:` เปลี่ยน (r2 F9) และเครื่องมือ command line ที่ไม่ทิ้งชื่อในรายการของ `tools:` ไม่ทำให้ต้องยืนยันซ้ำเลย · web terminal เปิดได้จาก browser ใดก็ได้ จัดเป็นความเสี่ยงเดียวกับแถว "ข้อมูลราคาสาธารณะ" |
| (v2.0) สิทธิ์ Privacy ของ macOS กว้างเกิน | ให้ Full Disk Access แก่แอปที่ agent รันอยู่ด้วย | runbook ให้เฉพาะ Files and Folders ของ Desktop, Documents, Downloads และ iCloud Drive (decision (ช)) | agent ที่รันในแอปเดียวกันอ่านโฟลเดอร์เหล่านั้นได้เท่ากับตัวตรวจ · (v2.1, F10) terminal หรือสำเนา sentinel ใน Trash ตรวจไม่เจอ ("Put Back" คืนได้): ลดด้วยการล้าง Trash ก่อนรัน · `terminal64.exe` ใต้ `~/Library` นอกที่ที่กฎ terminal_data และ Wine prefix ดู ตรวจไม่เจอ (รวมใต้ iCloud Drive, `~/Library/CloudStorage`) และใต้ `~/.ssh` (r2 F28) · PASS จากแอปอื่นไม่ได้พิสูจน์ว่า R1 ในแอปของ agent จะผ่าน จึงกำหนดแอปเดียว |
| (v2.1, F3) library หรือโค้ดที่ถูกวางให้ตัวตรวจโหลด | ตัวแปร `DYLD_*`, ไฟล์ library ใน working directory, ไฟล์ `.pth` ใน `.venv` | เปิด library ด้วย path เต็มตัวเดียว · มี `DYLD_*` = UNKNOWN · สร้าง `.venv` ใหม่ก่อนรอบหลักฐาน | ไฟล์ `.pth` ที่ถูกวางหลังสร้าง `.venv` ใหม่และก่อนรัน ตรวจไม่เจอ (เหมือน v1.9) |
| (v2.1, F14) agent บน Mac เข้า VPS ทางที่ไม่ใช่ RDP | console ของผู้ให้บริการที่ login ค้าง (reset รหัส Administrator, export snapshot), รหัสที่ sync มาจากอุปกรณ์อื่น, password manager ที่ปลดล็อกอยู่, API token หรือ SSH key, สิทธิ์ Screen Recording/Accessibility ของแอปที่ agent รัน, เครื่องมือคุม browser หรือ desktop ของ agent | checklist C1–C10 ของ AC-03 ข้อ 4 · decision (ค) รวม console | เป็นคำยืนยันของเจ้าของ ณ วันตรวจ โค้ดตรวจไม่ได้ และไม่มีการตรวจซ้ำอัตโนมัติหลัง ENV-1 |

- ผลภายนอก: ไม่มี · การลบเป็นขั้นตอนของเจ้าของบนเครื่องตัวเอง · ผู้อนุญาต: เจ้าของ

## Plan, dependencies and unknowns (P06)
1. Understanding: ทำให้เครื่องเจ้าของไม่มีทางดึงหรือถือข้อมูลช่วง holdout แล้วพิสูจน์ด้วย break-it test ของเจ้าของ, ตัวตรวจที่ R1 เรียกทุกครั้ง และ sentinel ปลอมบน VPS · เข้าใจผิดที่เป็นไปได้: ใช้ holdout จริงเป็น sentinel · ให้ตัวตรวจลบไฟล์เอง · ให้ agent รัน `cmdkey` · ตรวจครั้งเดียวตอน ENV-1 แทนที่จะตรวจก่อนทุก R1
2. Files / reuse: `research.HoldoutRefused`, `HOLDOUT_CUTOFF_UTC`, `core.Bar`, `timebase.rule_for` · stdlib `ctypes`, `winreg`, `importlib.util`, `pathlib`, `hashlib`, `json`, `secrets` (เฉพาะ make_sentinel)
3. Steps: (1) เจ้าของอนุมัติ + D-021 (review r5 พร้อม) (2) บันทึกผู้เขียน tests ใน PROGRESS → ผู้เขียน tests เขียน acceptance + architecture ผ่าน patch → apply → review → red (3) Claude implement envcheck + make_sentinel + runbook (4) เจ้าของสร้าง sentinel บน VPS → Claude commit ค่าของมัน → เจ้าของทำความสะอาดเครื่องตามลำดับใน runbook (5) เจ้าของรัน envcheck และ break-it test → PASS (6) review → PR → บันทึก "ENV-1 ผ่าน" และส่ง patch ของบรรทัด Phase ใน AGENTS.md ให้เจ้าของ
4. Risks: OneDrive ย้าย Desktop/Documents (อ่าน shell folder จริง) · การค้นในโฟลเดอร์ใหญ่ช้า (กรองด้วยนามสกุลและขนาดก่อน) · ชื่อ policy/API ต่างตามรุ่น Windows
5. Decisions needed from the owner:
   - (ก) อนุมัติ contract นี้ (High)
   - (ข) การทำความสะอาดเครื่อง · **แนะนำ:** หลัง ENV-001 และ SPIKE-002 ผ่าน ถอน MT5 terminal, ลบ `%APPDATA%\MetaQuotes` ทั้งโฟลเดอร์ (มี config ของบัญชีด้วย), ยกเลิกการบันทึกรหัส RDP ของ VPS (ถ้าเคยบันทึก) และตรวจ `cmdkey /list` ด้วยตัวเอง
   - (ค) ความเสี่ยงที่เหลือ · **แนะนำ:** (1) รับเรื่องข้อมูลราคาบนอินเทอร์เน็ตและความรู้ของ model พร้อมกฎว่าห้ามใช้ข้อมูลจากเว็บในการวิจัย (2) เปิด RDP ไป VPS เฉพาะเมื่อไม่มี session ของ Claude Code หรือ Codex รันอยู่ (v1.9: ปิดหน้าต่าง agent ก่อน · v2.2, r2 F14: บน macOS ต้อง Quit แอปของ agent ตาม checklist ข้อ C9 การปิดหน้าต่างไม่พอ) แทนการรับความเสี่ยงที่ agent มองเห็นและควบคุมหน้าต่าง RDP · (v2.1, F14) กฎเดียวกันใช้กับการเปิด console ของผู้ให้บริการใน browser
   - (ง) ที่อยู่ของ envcheck · **แนะนำ:** แพ็กเกจใหม่ `sochron.app` (SLICE-R1 เรียกจาก `app` ตาม D-020)

### Plan v2.0 (ร่าง 2026-11-17, D-023)
1. Understanding: research host เปลี่ยนเป็นเครื่อง Mac ตัวตรวจเดิมจึงต้องอ่านข้อเท็จจริงของ macOS ได้ และเครื่อง Windows เดิมต้องออกจากโปรเจกต์อย่างตรวจได้ · ข้อกำหนดของข้อ 6.1 และกฎของ evaluate ไม่เปลี่ยน · เข้าใจผิดที่เป็นไปได้: ติดตั้ง MT5 บน Mac เพื่อดู path จริง (ห้าม) · รื้อตัวอ่าน Windows และ tests ที่ล็อก · ให้ agent อ่าน Keychain แทน `cmdkey` · ให้ Full Disk Access เพื่อให้ผ่านเร็ว · ถือว่า PASS บน Mac แล้วเครื่อง Windows ไม่ต้องล้าง
2. Files / reuse: `src/sochron/app/envcheck.py` (เพิ่มตัวอ่าน darwin, ใช้กฎ evaluate เดิม และตรรกะเทียบชื่อของ helper ค้น `terminal64.exe` โดยไม่ใช้กฎข้ามของ v1.8; r2 F10) · `tests/unit/app/**` · `docs/runbooks/ENV-002-research-host.md` (ข้อ 2–4 ฉบับ macOS, ข้อ 1 และ 5 บน VPS คงเดิม ยกเว้นชื่อ branch ในข้อ 1 · ขั้นของเครื่อง Windows เดิม (ข้อ 2.1–2.2 เดิม และ AC-03 ข้อ 7) ย้ายไปหัวข้อใหม่ "เครื่อง Windows เดิม" ท้าย runbook (v2.2, r2 F24) · (v2.1, F17) ข้อ 6 ยังชี้ไป runbook ของ ENV-001 ข้อ 10 ซึ่งต้องเป็นฉบับ macOS ตาม D-023 ข้อ 5 ก่อนใช้: งานของ ENV-001 revision) · patch D-006 ของผู้เขียน tests สำหรับ `tests/acceptance/ENV-002/**` และ `tests/architecture/**`
3. Steps, each with its check:
   1. contract review ของ v2.0 และ D-023 โดย session ใหม่ (ตรวจ path ของ MT5 บน macOS จากหน้าทางการ, รายการชนิด mount, flag dataless, ขั้นของ Windows App) → แก้ตาม finding → เจ้าของอนุมัติ (High) และเลือก D-023 ข้อ 2 · check: review file ใน `docs/reviews/` ว่าพร้อม และบรรทัด Status ของ contract
   1a. (v2.1, F13) เจ้าของย้าย `docs/proposals/` และ memory ของ Claude Code จากเครื่อง Windows มา Mac ด้วยรายการไฟล์ที่ระบุชื่อ · check: รายการ SHA-256 สองฝั่งตรงกัน (เงื่อนไขก่อนขั้นลบ clone ของ AC-03 ข้อ 7)
   2. บันทึกผู้เขียน tests และผู้ตรวจใน PROGRESS → ผู้เขียน tests ส่ง patch ของกรณี macOS และของตัวตรวจ ctypes ของ envcheck (v2.2, r2 F24) → Claude apply ตาม D-006 และตรวจ hash → review ของ tests → red · check: tests ใหม่ล้มก่อนมีโค้ด และ tests เดิมยังผ่าน
   3. Claude implement ตัวอ่าน darwin, unit tests และ runbook ฉบับ macOS · check: suite ผ่านบน Mac ด้วย `PYTHONTZPATH=""`, red-flags 0, mypy: SKIPPED ถ้าไม่มีบนเครื่อง Mac (mypy ไม่อยู่ใน `pyproject.toml` และไม่ใช่ verified command; v2.1, F24) · (v2.1, F22) unit test เดิม `test_f10_collect_keeps_unreadable_facts_as_none` (`tests/unit/app/test_envcheck_review_r1.py`) ตั้ง `sys.platform` เป็น `win32` (ไฟล์ของ implementer, ระบุใน handoff)
   4. review งานโดย session ใหม่ รวมการตรวจซ้ำ F12–F15 ของ `ef7881e` ที่ยังไม่มีใครตรวจ → แก้ทีละ finding · check: review ว่าพร้อมรัน L4
   5. เจ้าของเปิด draft PR เพื่อให้ CI รันบน Linux (ยังไม่ merge) · check: `python-tests` และ `control-plane` เขียว
   6. หลัง ENV-001 และ SPIKE-002 ผ่าน: เจ้าของทำ runbook (sentinel บน VPS → envcheck บน Mac → break-it → เครื่อง Windows เดิม) · check: AC-01 และ AC-03 ครบทุกข้อพร้อม commit และเวลา
   7. evidence review → เจ้าของ label และ merge · บันทึก "ENV-1 ผ่าน"
4. Risks: path ของ MT5 บน macOS เปลี่ยนตามรุ่นของ MetaQuotes หรือวิธีติดตั้ง (ลดด้วยกฎชื่อแอปและโปรเซส; ทบทวนตาม D-023) · โปรเซสที่รันใต้ Wine อาจไม่แสดงชื่อ `terminal64.exe` ใน libproc (ทดสอบจริงไม่ได้เพราะห้ามติดตั้ง: เขียนเป็นข้อที่เหลือ) · สิทธิ์ Privacy ที่ยังไม่ให้ทำให้ได้ UNKNOWN ครั้งแรก (runbook บอกวิธีให้สิทธิ์) · control self-tests บน Mac ยังล้ม 2 จาก 76 จนกว่างาน FIX แยกจะเสร็จ: ไม่ใช่เงื่อนไขของ AC-07 แต่ต้องรายงานตามจริง · ไฟล์ `docs/proposals/` และ memory จากเครื่อง Windows ยังไม่ได้ย้ายมา ผู้เขียน tests อาจต้องใช้ patch เดิมอ้างอิง
5. Decisions needed from the owner (v2.0):
   - (จ) อนุมัติ contract v2.x ฉบับล่าสุดที่ contract review ว่าพร้อม (ตอนนี้ v2.3; High) และรับ D-023 (v2.2, r2 F24: v2.0 และ v2.1 ไม่ใช่ฉบับที่ขออนุมัติ) · (v2.1, F2) การอนุมัตินี้รวมข้อยกเว้นเดียวของ invariant "tests ที่ล็อกของ v1.9": การแก้ตัวตรวจ ctypes ของ envcheck ใน `tests/architecture/test_imports.py` แบบแคบตามหัวข้อ Invariants
   - (ฉ) เครื่อง Windows เดิม · **แนะนำ:** D-023 ข้อ 2 ทาง 1 เลิกใช้กับโปรเจกต์นี้และล้าง หลัง SPIKE-002 ผ่าน · (v2.1, F17) เลือกทาง 1 แล้วตามคำตัดสินข้อ 11 และ Goal, AC-03 ข้อ 7 กับ Done scope เขียนตามทางนี้ · ถ้าเจ้าของเลือกทาง 2 หรือ 3 ต้องแก้สามจุดนั้นก่อนอนุมัติ
   - (ช) สิทธิ์ Privacy บน Mac · **แนะนำ:** ให้ Files and Folders เฉพาะ Desktop, Documents, Downloads และ iCloud Drive แก่แอปที่รัน envcheck ไม่ให้ Full Disk Access · (v2.1, F10, คำตัดสินข้อ 7) แอปที่เริ่ม R1 (และจึงรัน `require_research_host`) คือ Visual Studio Code และเป็นแอปเดียวที่ได้สิทธิ์ Files and Folders ชุดนี้ (ถ้าเจ้าของจะเริ่ม R1 จากแอปอื่น ต้องแก้ชื่อแอปตรงนี้และวัดรายการข้ามใหม่ในแอปนั้นก่อนอนุมัติ) · คำถามสิทธิ์อื่นที่ macOS ถามระหว่างรัน (เช่น Photos, Music, Contacts, Network Volumes) ให้ตอบไม่อนุญาต
   - (ซ) ผู้เขียน tests และผู้ตรวจของ v2.0 · **แนะนำ:** Codex ตาม D-002 ถ้าใช้ได้บน Mac (งาน High ต้องมี tests และ review จาก Codex ตาม `docs/HANDBOOK-CORE.md` ข้อ 5) · ถ้าใช้ไม่ได้ ใช้ Claude session ใหม่คนละ session และบันทึกการสลับบทบาทใน PROGRESS ก่อนเริ่ม · (v2.2, r2 F38) ที่บันทึกใน PROGRESS 2026-11-18 ตามทางสำรองของข้อนี้: ผู้ตรวจ contract, ผู้เขียน tests และผู้ตรวจงาน เป็น Claude session ใหม่คนละ session เพราะ Codex บน Mac ยังไม่ผ่าน P25 · **รอเจ้าของยืนยันตอนอนุมัติ** (ผู้ทำงาน High ไม่ควรเป็นผู้ชี้ขาดว่าใครเขียน tests และตรวจงานของตัวเอง; `docs/HANDBOOK-CORE.md` ให้งาน High มี tests จาก Codex ก่อน) · ถ้าเจ้าของไม่ยืนยัน: ทำ P25 ของ Codex บน Mac ก่อนขั้นที่ 2 และ review ของ contract ทุกรอบที่ทำโดย Claude ถือเป็น pre-review
   - (ฌ) การตรวจซ้ำ F12–F15 · **แนะนำ:** รวมไว้ใน review งานของ v2.0 (ขั้นที่ 4) แทนการรอถึงหลัง L4 · (v2.2, r2 F38) เสนอตามที่แนะนำ รอเจ้าของยืนยันตอนอนุมัติ
   - (ญ) (v2.2, r2 F36) ความเสี่ยงที่เหลือของ v2.x · เจ้าของรับหรือไม่รับทีละข้อตอนอนุมัติ (อ่านคู่กับตาราง threat model; ข้อใดไม่รับ ต้องแก้กฎก่อนอนุมัติ):
     1. terminal ใต้ Wine prefix นอกที่ที่รู้จัก หรือใน VM/container ตรวจไม่เจอทั้งตอนรันและไม่รัน · พึ่งคำยืนยันของเจ้าของและบรรทัด `apps:`, `tools:`, `wine:`
     2. เครื่องมือ VM ทาง command line ที่ไม่ทิ้งชื่อในรายการของ `tools:` ไม่ทำให้ต้องยืนยันซ้ำ
     3. cache ของ MT5 ที่ถูกคัดลอกมาไว้นอก repo และ data dirs (เช่น Downloads) ตรวจไม่เจอ และโค้ดวิจัยอ่านได้ด้วย path เต็ม
     4. การค้น home ไม่เข้า `~/Library` (รวม iCloud Drive และ CloudStorage) และ `~/.ssh`: `terminal64.exe` ที่นั่นนอกกฎ terminal_data และ Wine prefix ตรวจไม่เจอ
     5. terminal หรือสำเนา sentinel ใน Trash หรือใน `~/Pictures/Photos Library.photoslibrary` (สองโฟลเดอร์ในรายการข้าม) ตรวจไม่เจอ (ลด Trash ด้วยการล้าง
        Trash ก่อนรัน; v2.3, r3 F36)
     6. แอป MetaTrader นอกระดับ 0 ของสองโฟลเดอร์แอปที่ยังไม่เคยเปิด และแอปของโบรกเกอร์ที่ชื่อไม่มีคำว่า metatrader ตรวจไม่เจอ
     7. ไฟล์ `.pth` ที่ถูกวางใน `.venv` หลังสร้างใหม่และก่อนรัน ตรวจไม่เจอ
     8. checklist credential C1–C10 เป็นคำยืนยัน ณ วันตรวจ ไม่มีการตรวจซ้ำอัตโนมัติหลัง ENV-1
     9. `mt5_package` และส่วน vault path ของ `sentinel` ล้มไม่ได้บน macOS จึงไม่ใช่การป้องกัน
     10. เครื่อง Windows เดิม: หลังรอบ envcheck ของ AC-03 ข้อ 7 การไม่กลับไปใช้เครื่องนั้นกับโปรเจกต์เป็นคำยืนยันของเจ้าของ
     11. ไม่ใช้ `/var/db/receipts` เป็นหลักฐาน (ชื่อ receipt ของ MT5 ยังไม่มีใครยืนยัน)
     12. กฎ Wine loader และกฎชื่อโปรเซส `terminal64.exe` ยังไม่เคยพิสูจน์กับ Wine จริงบน macOS (ห้ามติดตั้งเพื่อทดสอบ)
     13. (v2.3, r3 F36) ก่อนล้างเครื่อง Windows เดิม (ระหว่างรอ SPIKE-002): เครื่องนั้นยังมี terminal และ cache การไม่เปิด agent ของโปรเจกต์บนเครื่องนั้นเป็น
         คำยืนยันของเจ้าของ โค้ดตรวจไม่ได้
     14. (v2.3, r3 F36) agent ที่รันใน Visual Studio Code อ่าน Desktop, Documents, Downloads และ iCloud Drive ได้เท่ากับตัวตรวจ (ผลของ decision (ช))
     15. (v2.3, r3 F32) volume ที่ mount ทับ path ของระบบใต้ `/System/Volumes/` นอก `Data` (ต้องมีสิทธิ์ระดับระบบ) ตรวจไม่เจอ
     · จำนวน session (decision ในหัวข้อ Budget): Claude 5 และ session ใหม่ 8 เป็นข้อเสนอทั้งสองตัวเลข การอนุมัติ (จ) กำหนดทั้งสองตัว (v2.3, r3 F36)

### คำตัดสินของ v2.1 ตามการมอบอำนาจของเจ้าของ 2026-11-18
เจ้าของสั่งในแชท Claude 2026-11-18 หลังได้รับคำถาม 13 ข้อของ `docs/reviews/ENV-002-contract-v2-r1.md`: "อันไหนที่ว่าดีบอกทีจะได้ทำแล้วก็เอาไหนที่ว่าดีมึงตัดสินใจเองไปเลย แล้วก็พุทบันนี้หรือไม่แล้วแต่มึงเอาง่ายเอาให้มันดีที่สุดอะมึงตัดสินใจทำเองเลย…" (v2.2, r2 F39: ยกทั้งข้อความ ตัดเฉพาะคำอุทานคำสุดท้าย; v2.1 ยกแบบย่อโดยไม่ได้บอก) · ส่วน "บอกทีจะได้ทำ" Claude ทำด้วยการบอกเจ้าของว่าเลือกอะไรไว้: ตารางคำตัดสินสองตารางในหัวข้อนี้, decision (ญ) และรายงานในแชท · Claude จึงเลือกทางที่ review แนะนำทุกข้อ และข้อที่ review ไม่ได้แนะนำ เลือกทางที่ fail-closed กว่า (เพิ่มได้แค่ UNKNOWN หรือ FAIL ไม่เพิ่ม PASS) หรือทางที่งานของเจ้าของน้อยกว่าเมื่อผลด้านความปลอดภัยเท่ากัน · (v2.2, r2 F36) ข้อที่ไม่ตรงกับหลักนี้ ต้องบอกตรงๆ: คำตัดสินข้อ 6 (ไม่ใช้ receipts) และข้อ 7 (การค้น home ไม่เข้า `~/Library`) ตัดการตรวจออก ข้อที่เหลือของสองข้อนี้อยู่ใน decision (ญ) ข้อ 11 และข้อ 4 · ข้อ 9 ถูกกลับใน v2.2 · **การมอบอำนาจนี้ไม่ใช่การอนุมัติ contract:** v2.1 ยังต้องผ่าน contract review และเจ้าของยังต้องอนุมัติ (จ) เอง · เจ้าของกลับคำตัดสินข้อใดก็ได้ก่อนอนุมัติ · ความเสี่ยงที่เหลือในตาราง threat model เจ้าของเป็นผู้รับเมื่ออนุมัติ Claude ไม่ได้รับแทน

| คำถามของ review r1 | คำตัดสิน | เหตุผล |
|---|---|---|
| 1 (F1) field `platform` | ไม่เพิ่ม field · CLI พิมพ์บรรทัด `reader:` | ทางที่แนะนำ: ไม่แตะ test ที่ล็อก |
| 2 (F2) ข้อยกเว้นของตัวตรวจ ctypes ที่ล็อก | รับข้อยกเว้นแบบแคบ (ทาง (i)) · เจ้าของยังอนุมัติ diff ของผู้เขียน tests ก่อน apply | ไม่มีข้อยกเว้นนี้ ตัวอ่าน darwin อ่านโปรเซสและ mount ไม่ได้เลย |
| 3 (F3) ชื่อ library, `DYLD_*`, `.venv` | literal เดียว `/usr/lib/libSystem.B.dylib` · มีตัวแปร `DYLD_*` = UNKNOWN · สร้าง `.venv` ใหม่ก่อนรอบหลักฐาน | ทางที่แนะนำ และทางที่ fail-closed กว่าของ `.venv` |
| 4 (F6) โฟลเดอร์ dataless | ไม่ list และเป็น UNKNOWN (ทาง (i)) | ทางที่การรวม review แนะนำ: ตัวตรวจไม่ทำให้ macOS ดึงข้อมูลจาก cloud |
| 5 (F7) รอบควบคุม และ Wine | ทำรอบควบคุมด้วยโฟลเดอร์เปล่าสองตัวก่อนรอบ PASS · เพิ่มกฎ Wine loader = UNKNOWN พร้อมแก้ถ้อยคำข้อที่เหลือ | รอบควบคุมแนะนำ · กฎ Wine เพิ่มได้แค่ UNKNOWN |
| 6 (F8, F9) `/var/db/receipts` · Wine, VM, container | ไม่เพิ่มกฎ receipts · ใช้ note ที่ไม่เปลี่ยน verdict พร้อมคำยืนยันซ้ำ (ทาง (ii)) | ยังไม่มีใครยืนยันชื่อ receipt ของ MT5 กฎที่ตั้งบนชื่อเดาให้ PASS ที่ไม่มีความหมาย · ทาง (ii) แนะนำ |
| 7 (F10) แอปและรายการข้าม | แอปที่เริ่ม R1 และรัน envcheck คือ Visual Studio Code (แอปที่ Claude Code ทำงานอยู่ วัด 2026-11-18) · Claude วัดการค้น home ในแอปนั้นแล้ว รายการข้ามอยู่ในหัวข้อ contract · การค้น home ไม่เข้า `~/Library` ทั้งโฟลเดอร์ | เจ้าของไม่ต้องรันเอง · ที่รู้จักใต้ `~/Library` ตรวจด้วยกฎ terminal_data และ Wine prefix อยู่แล้ว |
| 8 (F11) ชื่อบัญชี macOS ในหลักฐาน | ยอมให้อยู่ในบรรทัด `roots:` · (v2.2, r2 F41) ชื่อโฟลเดอร์ของ cloud storage ไม่อยู่ในข้อนี้: บรรทัด `roots:` พิมพ์แค่จำนวนและชื่อผู้ให้บริการ | ชื่อเดียวกับชื่อบัญชี GitHub ของ repo ซึ่งอยู่ใน remote URL อยู่แล้ว |
| 9 (F13) รันตัวอ่าน Windows บนเครื่องเดิม | ~~ไม่ทำ~~ **กลับใน v2.2 (r2 F37): ทำหนึ่งครั้งโดยไม่ใส่ sentinel** · เหตุผลเดิมในช่องขวาผิด (CLI รันได้โดยไม่มี sentinel) | เครื่องนั้นเลิกเป็น research host แล้ว และการรันต้องตั้งค่า sentinel บนเครื่องที่กำลังจะล้าง: งานเพิ่มโดยไม่เปลี่ยนผลของด่าน |
| 10 (F15) สำเนา cache ของ MT5 | เพิ่มกฎ mount ใต้ `/Volumes/` = UNKNOWN และกฎย้ายไฟล์ด้วยรายการชื่อพร้อม SHA-256 เท่านั้น · ไม่เพิ่มกฎนามสกุล cache ใน search_dirs | กฎ `/Volumes` ไม่แตะ evaluate ของ Windows · กฎนามสกุลต้องแก้ evaluate ทุกแพลตฟอร์มและ tests ที่ล็อก · สำเนาใน Downloads ยังเป็นข้อที่เหลือ · (v2.2, r2 F32: กฎ `/Volumes/` ถูกแทนด้วยรายการอนุญาตของจุด mount; v2.3, r3 F47) |
| 11 (F17) D-021 และ D-023 ข้อ 2 | เพิ่มบรรทัดอ้างกลับใต้ D-021 · ยืนยันทาง 1 (เลิกใช้และล้างเครื่อง Windows หลัง SPIKE-002 ผ่าน) | ทางที่แนะนำ และ contract เขียนตามทางนี้อยู่แล้ว |
| 12 (F19, F23, F24) | ไม่ต่อ external disk, disk image หรือ network volume ระหว่างรัน · งบ session ใหม่ 8 และ lens ขนานของ pre-review หนึ่งรอบนับเป็นหนึ่ง session · งาน v2.x ทั้งหมดอยู่บน branch `chore/ENV-002-macos-research-host` | สอดคล้องกับกฎ `/Volumes` (v2.2, r2 F32: แทนด้วยรายการอนุญาตของจุด mount; v2.3, r3 F47) · ตัวเลขที่ review เสนอ (v2.3: ยังเป็นข้อเสนอ รอเจ้าของ) · branch นี้มี commit ของ `feat/ENV-002-research-host-separation` ครบถึง `c97aac6` |
| 13 ผู้ตรวจ contract ตัวจริง | Claude session ใหม่คนละ session (ผู้ตรวจที่เห็นเฉพาะ contract, review และ diff) ตามการสลับบทบาทที่บันทึกใน PROGRESS ตั้งแต่ ENV-001 r3 · (v2.2, r2 F38) PROGRESS บันทึกผู้เขียน tests และผู้ตรวจงานแบบเดียวกันด้วย ซึ่งกว้างกว่าคำถามข้อนี้: ทั้งสามบทบาทรอเจ้าของยืนยัน (decision (ซ)) | Codex บน Mac ยังไม่ผ่านการตรวจการตั้งค่า (P25 บน macOS เป็นงานตามของ D-023) · ผู้ทำและผู้ตรวจไม่ใช่ session เดียวกัน |

### คำตัดสินของ v2.2 (คำถาม 9 ข้อของ `docs/reviews/ENV-002-contract-v2-r2.md`) ตามการมอบอำนาจเดียวกัน
ใช้การมอบอำนาจ 2026-11-18 ข้างบน (เจ้าของยังไม่ได้ตอบเพิ่มหลัง review r2) · หลักเดียวกัน: ทางที่แนะนำ หรือทางที่เข้มกว่า · ข้อที่เป็นของเจ้าของโดยแท้ (รับความเสี่ยง, ยืนยันผู้ตรวจ, ตัวเลขงบ) Claude เสนอไว้และรอเจ้าของยืนยันตอนอนุมัติ ไม่ได้ตัดสินแทน

| คำถามของ review r2 | คำตัดสินหรือข้อเสนอ | เหตุผล |
|---|---|---|
| 1 (F27) วัดการค้น search_dirs | วัดแล้ว 2026-11-18: list ไม่ได้ 0 โฟลเดอร์ | ไม่มี path ให้เจ้าของตัดสิน |
| 2 (F9) เครื่องมือ VM ทาง command line | เพิ่มบรรทัด `tools:` (ดูชื่อระดับ 0 ของ home และ path `.local/share/containers`; v2.3, r3 F47) | เครื่องนี้มี `.colima` และ `.docker` อยู่แล้ว ซึ่งบรรทัด `apps:` ไม่เห็น |
| 3 (F33) โฟลเดอร์ `MetaTrader` ที่ไม่มี `.app` | FAIL เหมือน Windows · ที่อยู่นอกระดับ 0 เป็นข้อที่เหลือ | ทางที่เข้มกว่า |
| 4 (F32) จุด mount | รายการอนุญาต (`/`, `/dev`, ใต้ `/System/Volumes/`) นอกนั้น UNKNOWN | ทางที่เข้มกว่า และครอบ `/Volumes/` เดิม |
| 5 (F36) รับความเสี่ยงที่เหลือ | **รอเจ้าของ:** decision (ญ) แจกแจงทีละข้อ | agent ไม่รับความเสี่ยงแทนเจ้าของ (AGENTS.md) |
| 6 (F37) รันตัวอ่าน Windows บนเครื่องเดิม | ทำหนึ่งครั้งโดยไม่ใส่ sentinel ก่อนลบ clone (กลับคำตัดสินข้อ 9 ของ v2.1) | เหตุผลเดิมของข้อ 9 ผิด: CLI รันได้โดยไม่มี sentinel จึงเป็นคำสั่งเดียว และได้หลักฐานจากเครื่องแทนคำยืนยัน |
| 7 (F38) ผู้เขียน tests และผู้ตรวจ · (ฌ) | **เสนอ รอเจ้าของยืนยัน:** Claude session ใหม่คนละ session ทั้งสามบทบาท · (ฌ) รวมการตรวจซ้ำ F12–F15 ของ `ef7881e` ไว้ใน review งาน | ผู้ทำงาน High ไม่ควรเป็นคนชี้ขาดว่าใครเขียน tests และตรวจงานของตัวเอง · ถ้าเจ้าของไม่ยืนยัน ต้องทำ P25 ของ Codex บน Mac ก่อนขั้นที่ 2 |
| 8 (F40) งบ session ของ Claude | **เสนอ รอเจ้าของยืนยัน:** 5 sessions รวมการร่าง · ใช้ไป 2 (2026-11-17, 2026-11-18) | ตัวเลขเป็นของเจ้าของ |
| 9 (F41) ชื่อโฟลเดอร์ cloud storage ในหลักฐาน | ไม่พิมพ์ชื่อเต็มในบรรทัด `roots:`: พิมพ์จำนวนและชื่อผู้ให้บริการเท่านั้น · (v2.3, r3 F41) ขอบเขตคือบรรทัด `roots:` เท่านั้น: detail ของ item ในรายงานที่ไม่ PASS ยังพิมพ์ path เต็มของสิ่งที่พบหรืออ่านไม่ได้ เจ้าของปิดบังชื่อบัญชีก่อน commit (แบบเดียวกับ IP ใน AC-03) · รายงาน PASS ไม่มี path แบบนี้ | ชื่อโฟลเดอร์อาจมีชื่อบัญชี |

## Authorization (filled by the owner)
| รายการ | ค่า |
|---|---|
| actor | เจ้าของ (ลบ terminal และโฟลเดอร์ข้อมูลบนเครื่องตัวเอง, สร้าง sentinel บน VPS, รันตัวตรวจและ break-it test, รัน `cmdkey /list` เอง) · Claude (เขียนโค้ดและ runbook, commit ค่าของ sentinel) |
| action | ตรวจแบบอ่านอย่างเดียวบนเครื่องเจ้าของ · สร้างไฟล์ปลอมบน VPS · ไม่มีการเชื่อมต่อโบรกเกอร์ |
| target | เครื่องเจ้าของ (research host), vault path บน VPS |
| valid until | TBD (เจ้าของกรอก) |

(v2.0) target เปลี่ยนเป็น: เครื่อง Mac (research host), เครื่อง Windows เดิม (ล้างครั้งเดียวตาม D-023 ข้อ 2), vault path บน VPS · actor เพิ่ม: เจ้าของตรวจ credential ของ Windows App และ Keychain เอง (แทน `cmdkey /list`) · valid until ยัง TBD · (v2.1, F16) actor ของ v1.9 ที่เขียนว่าเครื่องตัวเองและ `cmdkey` หมายถึงเครื่อง Windows เดิม · เจ้าของเป็นผู้ลบ clone, worktree และย้ายไฟล์บนเครื่องนั้นเอง

## Budget
2 sessions ของ Claude · headless session ไม่เกิน 5 (ผู้เขียน tests, ผู้ตรวจ tests, ผู้ตรวจงาน, สำรอง ×2) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

(v2.0) งบของ v1.x ใช้ครบแล้ว (headless 5/5) · งบใหม่ของ v2.x: (v2.2, r2 F40) เสนอ 5 sessions ของ Claude โดยนับการร่าง contract ด้วย รอเจ้าของยืนยันตัวเลขตอนอนุมัติ (v2.0 เขียนไว้ 2 ซึ่งใช้ไปกับการร่างแล้ว: 2026-11-17 และ 2026-11-18) · (v2.1, F23, คำตัดสินข้อ 12) session ใหม่ไม่เกิน 8 (v2.3, r3 F36: เสนอ รอเจ้าของยืนยันตอนอนุมัติ เหมือนตัวเลข 5 ของ Claude): ผู้ตรวจ contract ×2 (รอบแรกและตรวจซ้ำ), ผู้เขียน tests, ผู้ตรวจ tests, ผู้ตรวจงาน ×2, ผู้ตรวจหลักฐาน, สำรอง ×1 · lens ขนานของ review หนึ่งรอบ (รวมการตรวจหักล้างและการรวมผล) นับเป็นหนึ่ง session · ใช้ไปแล้ว 2 (ผู้ตรวจ contract r1 และ r2: `docs/reviews/ENV-002-contract-v2-r1.md`, `-r2.md`) · รอบตรวจซ้ำ r3 ของ v2.2 ใช้ตัวสำรอง (รวมเป็น 3 จาก 8) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
(v1.9, เฉพาะเครื่อง Windows เดิมและก่อนล้างตาม D-023 ข้อ 2 เท่านั้น) ติดตั้ง MT5 ใหม่บนเครื่อง Windows ได้ถ้าต้องย้อน (ENV-1 จะไม่ผ่านจนกว่าจะถอนอีกครั้ง) · (v2.1, F16) บนเครื่อง Mac ไม่มีทางย้อนแบบนี้: ห้ามติดตั้ง MT5 หรือ Wine · ลบไฟล์ sentinel บน VPS ได้หลังบันทึกหลักฐาน (แล้วค่าที่ commit ใช้ไม่ได้: ต้องสร้างใหม่และ commit ใหม่) · revert PR

(v2.0) ถ้าเจ้าของไม่รับ D-023 หรือ v2.x (v2.3, r3 F47): ลบ branch `chore/ENV-002-macos-research-host` แล้ว v1.9 ยังใช้ได้ตามเดิมบนเครื่อง Windows · การลบ clone และโฟลเดอร์ของ terminal บนเครื่อง Windows ย้อนไม่ได้: ทำหลังยืนยันว่า push ครบและย้าย `docs/proposals/` กับ memory พร้อมตรวจ SHA-256 แล้วเท่านั้น · ตัวอ่าน Windows ยังอยู่ในโค้ด ถ้ากลับไปใช้ Windows เป็น research host ต้องตัดสินใหม่ตาม D-023 "Review when"

## DoR status / missing items / next action
ครบ: เจ้าของอนุมัติ (ก)–(ง) และ D-021 2026-10-25 17:5x · ขาด: ENV-001 และ SPIKE-002 ผ่าน, valid until · ผู้ตรวจรอบถัดไปตรวจซ้ำ F51 · next: หลัง ENV-001 และ SPIKE-002 ผ่าน (tests ของ ENV-002 เขียนได้ก่อน)

(v2.0) ครบ: เจ้าของเลือกทิศทาง "Mac เป็น research host" ในแชท 2026-11-17 · ข้อเท็จจริงของ Mac วัดแล้ว (หัวข้อ Current behavior) · ขาด: contract review ของ v2.0 และ D-023, การอนุมัติของเจ้าของ (จ)–(ฌ), การยืนยัน path ของ MT5 บน macOS จากหน้าทางการ, valid until, การย้าย `docs/proposals/` และ memory จากเครื่อง Windows, ENV-001 และ SPIKE-002 ผ่าน (สำหรับ L4)

(v2.1, 2026-11-18) ครบเพิ่ม: review r1 (24 ข้อ) ตอบครบใน v2.1 · path ของ MT5 บน macOS ยืนยันจากหน้าทางการแล้ว (review r1) · รายการข้ามของการค้น home วัดแล้ว · คำตัดสิน 13 ข้อเลือกตามการมอบอำนาจ · ขาด: contract review รอบตรวจซ้ำของ v2.1 โดย session ใหม่, การอนุมัติของเจ้าของ (จ) (High), valid until, การย้าย `docs/proposals/` และ memory จากเครื่อง Windows, ENV-001 และ SPIKE-002 ผ่าน (สำหรับ L4) · เมื่อเจ้าของอนุมัติ: ย้าย bullet ฉบับ v1.9 ของ AC-01 และ AC-03 ไปเป็นบรรทัดประวัติ "AC-01 และ AC-03 ฉบับ Windows ของ v1.9 อยู่ใน commit `c97aac6`" (F24) · next: contract review รอบตรวจซ้ำ → เจ้าของอ่าน AC-01, AC-03 และตารางคำตัดสิน แล้วอนุมัติหรือกลับคำตัดสิน

(v2.2, 2026-11-18) ครบเพิ่ม: review r2 (27 ข้อ) ตอบครบใน v2.2 · การค้น search_dirs วัดแล้ว (list ไม่ได้ 0) · ขาด: contract review รอบตรวจซ้ำ r3, การอนุมัติของเจ้าของ (จ) พร้อมการยืนยัน (ซ), (ฌ), ตัวเลขงบ session และการรับหรือไม่รับความเสี่ยงที่เหลือทีละข้อใน (ญ), valid until, การย้าย `docs/proposals/` และ memory, ENV-001 และ SPIKE-002 ผ่าน (สำหรับ L4) · next: review r3 → เจ้าของอ่าน AC-01, AC-03, ตารางคำตัดสินสองตาราง, decision (ญ), ตาราง threat model และ D-023 ทั้งฉบับใน `DECISIONS.md` (v2.3, r3 F36) แล้วอนุมัติหรือกลับคำตัดสิน

(v2.3, 2026-11-18) ครบเพิ่ม: review r3 (Medium 1, Low 13) ตอบครบใน v2.3 · คำถามของเจ้าของใน r3: ข้อ 2 (F32) ตอบตามการมอบอำนาจด้วยทางที่เข้มกว่า (แคบลง) · ข้อ 5 (F41, F46) ตอบด้วยทางที่เปิดเผยข้อมูลน้อยกว่า (รอบบนเครื่องเดิมใช้โค้ด v1.9; เจ้าของปิดบังชื่อบัญชีในรายงานที่ไม่ PASS) · ข้อ 1, 3, 4 (ผู้ตรวจ, ความเสี่ยงที่เหลือ, ตัวเลขงบ) ยังเป็นของเจ้าของ · งบ session ใหม่: ใช้ 3 จาก 8 (r1, r2, r3) ซึ่งเกินส่วนของผู้ตรวจ contract (×2 + สำรอง ×1) แล้ว การตรวจซ้ำรอบที่ 4 ต้องให้เจ้าของเพิ่มงบหรือยอมใช้จากส่วนอื่น · next: เจ้าของตัดสินว่าจะสั่งตรวจซ้ำ r4 หรืออ่านแล้วอนุมัติ

## Done scope
operation: เครื่องเจ้าของเป็น research host ที่ตรวจได้ · ENV-1 ผ่านเมื่อ ENV-001, SPIKE-002 และ ENV-002 ผ่านครบ และเจ้าของบันทึกการตัดสินที่ D-021 และ SPIKE-002 AC-04 ต้องการ · (v2.0) "เครื่องเจ้าของ" คือเครื่อง Mac และเครื่อง Windows เดิมออกจากโปรเจกต์แล้วตาม AC-03 ข้อ 7
