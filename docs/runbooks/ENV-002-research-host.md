# Runbook ENV-002: ทำเครื่องคุณให้เป็น research host และสร้าง sentinel บน VPS

Contract: `docs/contracts/ENV-002-research-host-separation.md` (v1.9) · ผู้ทำ: เจ้าของ · ใช้เวลา ≈ 45 นาที · **ทำหลัง ENV-001 และ SPIKE-002 ผ่านแล้วเท่านั้น** (terminal บนเครื่องคุณต้องอยู่จนกว่า VPS ผ่านทั้งสองงาน)

กติกาตลอดทั้ง runbook:
- **ปิดหน้าต่าง Claude Code และ Codex บนเครื่องคุณก่อนเปิด RDP ไป VPS ทุกครั้ง** (ENV-002 (ค)): ขณะหน้าต่าง RDP เปิดอยู่ โปรแกรมบนเครื่องคุณมองเห็นและส่ง input เข้าหน้าต่างนั้นได้
- ส่งผลกลับเป็น**ข้อความ** และปิดบัง IP ทุกครั้ง (`x.x.x.x`) · **ห้ามคัดลอกไฟล์ sentinel มาเครื่องคุณ** คัดลอกได้แค่ข้อความที่สคริปต์พิมพ์
- `cmdkey /list` **คุณรันเองเท่านั้น** (agent ห้ามรัน) และไม่ต้องวางผลทั้งหมด ส่งแค่คำยืนยัน
- คำสั่งที่ขึ้นต้นด้วย `PS>` รันใน PowerShell ไม่ต้องพิมพ์ `PS>`

## 1. สร้าง sentinel บน VPS (PowerShell ธรรมดา บน VPS)
1. ดึง commit ที่ตรวจแล้วจาก Claude (สคริปต์ยังไม่อยู่ใน `main` จนกว่าจะ merge):
   ```powershell
   PS> cd C:\Sochron1k
   PS> git fetch origin feat/ENV-002-research-host-separation
   PS> git switch --detach <hash ที่ Claude ให้>
   PS> git rev-parse --short HEAD
   PS> git status --short
   ```
   `git rev-parse` ต้องพิมพ์ hash เดียวกับที่ Claude ให้ และ `git status --short` ต้องไม่พิมพ์อะไร
2. สร้างโฟลเดอร์ vault **นอก repo** แล้วรันสคริปต์ในโฟลเดอร์นั้น:
   ```powershell
   PS> New-Item -ItemType Directory -Path C:\vault | Out-Null
   PS> cd C:\vault
   PS> uv run --no-project --offline --python 3.12.15 python C:\Sochron1k\scripts\env\make_sentinel.py
   PS> Get-FileHash .\SENTINEL-ENV002-*.json
   ```
   สคริปต์เขียนไฟล์ `SENTINEL-ENV002-xxxxxxxx.json` หนึ่งไฟล์ (ข้อมูลสังเคราะห์ ไม่ใช่ราคาจริง) แล้วพิมพ์ JSON ที่มี 6 ค่า: `name`, `size`, `sha256`, `token`, `vault_path`, `created_utc` · **รันครั้งเดียว** (สคริปต์ไม่เขียนทับไฟล์เดิม ถ้ามีสองไฟล์ ให้เก็บไฟล์ที่ Claude commit ค่าไว้และบอก Claude)
3. **ห้าม share โฟลเดอร์ `C:\vault`** และห้ามย้ายไฟล์นี้ออกจาก VPS
4. **ส่งให้ Claude:** ข้อความ JSON ที่สคริปต์พิมพ์ทั้งก้อน (ค่า token ส่งได้ครั้งนี้ครั้งเดียว เพราะต้อง commit ไว้ใน `docs/evidence/ENV-002-sentinel.json` ไฟล์เดียว) และผลของ `Get-FileHash` · ช่องทาง: คัดลอกเป็น**ข้อความ**ผ่าน clipboard แบบข้อความที่ ENV-001 เปิดไว้ หรือพิมพ์เอง (ไม่คัดลอกไฟล์) · Claude commit ค่าแล้วส่ง hash ใหม่ให้คุณ

## 2. ทำความสะอาดเครื่องคุณ (หลัง SPIKE-002 ผ่าน, PowerShell บนเครื่องคุณ)
1. ถอน MetaTrader 5 (และ terminal ของโบรกเกอร์ทุกตัว): Settings → Apps → Installed apps → MetaTrader 5 → Uninstall · ถ้าตัวถอนทิ้งโฟลเดอร์ `C:\Program Files\MetaTrader 5` ไว้ (envcheck จะบอกชื่อใน `terminal_install`) ให้ลบด้วย PowerShell แบบ Administrator: `Remove-Item -Recurse -Force "C:\Program Files\MetaTrader 5"`
2. ลบโฟลเดอร์ข้อมูลของ terminal ทั้งโฟลเดอร์ (มี config ของบัญชีด้วย):
   ```powershell
   PS> Remove-Item -Recurse -Force "$env:APPDATA\MetaQuotes"
   ```
3. ไม่มี drive หรือ share ที่ต่อไป VPS: `net use` ต้องไม่มีรายการของ VPS (ถ้ามี: `net use <X:> /delete`)
4. รหัส RDP ของ VPS ต้องไม่ถูกบันทึก: เปิด mstsc → Show Options → ถ้ามี "Saved credentials" ให้กด delete · แล้วรัน `cmdkey /list` **ด้วยตัวเอง** ต้องไม่มีรายการ `TERMSRV/<IP ของ VPS>` (ถ้ามี: `cmdkey /delete:TERMSRV/<IP ของ VPS>`)
5. โฟลเดอร์ที่ list ไม่ได้: วันที่ 2026-11-05 บน Desktop มี 2 โฟลเดอร์ที่บัญชีคุณ list ไม่ได้ ซึ่งทำให้ item `sentinel` เป็น UNKNOWN: `...\PayBackGB\output\pytest-engine-history-tmp` และ `...\PayBackGB\output\pytest-engine-history-firstfailure` (โฟลเดอร์ชั่วคราวของ pytest) · ลบทิ้งด้วย PowerShell แบบ **Administrator**:
   ```powershell
   PS> takeown /f "<path เต็มของโฟลเดอร์>" /r /d y
   PS> Remove-Item -Recurse -Force "<path เต็มของโฟลเดอร์>"
   ```
   ถ้า `Remove-Item` ยังถูกปฏิเสธ (ACL ไม่มีบัญชีคุณ) ให้คืนสิทธิ์ก่อน หรือแค่ให้ list ได้ก็พอสำหรับ envcheck:
   ```powershell
   PS> icacls "<path เต็มของโฟลเดอร์>" /grant "${env:USERNAME}:(OI)(CI)F" /t
   ```
   ถ้า envcheck รายงานโฟลเดอร์อื่นว่า "could not be listed" ให้ทำแบบเดียวกัน หรือส่งชื่อให้ Claude ถ้าไม่แน่ใจ

## 3. ตรวจเครื่องคุณ (AC-01, PowerShell ธรรมดา ที่โฟลเดอร์ repo บนเครื่องคุณ)
```powershell
PS> git fetch origin feat/ENV-002-research-host-separation
PS> git switch feat/ENV-002-research-host-separation
PS> git pull
PS> $env:PYTHONPATH="src"; uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json; "exit status: $LASTEXITCODE"
```
- บรรทัด `RESEARCH HOST:` ต้องเป็น `PASS` และบรรทัดสุดท้ายต้องเป็น `exit status: 0` · ถ้าเป็น FAIL หรือ UNKNOWN ให้แก้ตามข้อความของ item นั้นแล้วรันใหม่
- item `sentinel` ต้องบอกชื่อและ SHA-256 เดียวกับที่ Claude commit · item ที่ค้นไฟล์บอกจำนวนโฟลเดอร์และไฟล์ที่ค้น (ต้องมากกว่า 0)
- ถ้าคุณรับไฟล์ snapshot ไว้นอก `data\` ให้เพิ่ม `--data-dir <โฟลเดอร์>` **เฉพาะโฟลเดอร์ข้อมูลนั้นเอง ห้ามใส่โฟลเดอร์ที่ครอบ repo ไว้** (เช่น Desktop หรือโฟลเดอร์แม่ของ repo)
- รายงานไม่พิมพ์ token · **ส่งให้ Claude:** รายงานทั้งหมดของรอบที่ PASS พร้อมเวลา และบรรทัด `exit status`

## 4. Break-it test จากเครื่องคุณ (AC-03, PowerShell ธรรมดา บนเครื่องคุณ, ปิดหน้าต่าง agent ก่อน)
```powershell
PS> foreach ($p in 22,80,443,445,5985,5986) { Test-NetConnection <IP ของ VPS> -Port $p -WarningAction SilentlyContinue | Select-Object RemotePort, TcpTestSucceeded }
PS> dir \\<IP ของ VPS>\C$
PS> dir \\<IP ของ VPS>\vault
PS> cmdkey /list
```
ผลที่ถูก: ทุกพอร์ตเป็น False (3389 เปิดไว้สำหรับคุณเท่านั้น และไม่อยู่ในรายการนี้) · `dir` ทั้งสองบรรทัดล้ม · `cmdkey /list` ไม่มีรายการของ VPS (ส่งแค่คำยืนยัน ไม่ต้องวางรายการ)

## 5. ตรวจ hash ของ sentinel บน VPS (AC-03, PowerShell ธรรมดา บน VPS)
```powershell
PS> Get-FileHash C:\vault\SENTINEL-ENV002-*.json
PS> (Get-Item C:\vault\SENTINEL-ENV002-*.json).Length
PS> Select-String -Path C:\vault\SENTINEL-ENV002-*.json -SimpleMatch -Pattern '<token จาก docs/evidence/ENV-002-sentinel.json>' -Quiet
```
ค่า SHA256 ต้องตรงกับ `sha256`, ความยาวต้องตรงกับ `size` ใน `docs/evidence/ENV-002-sentinel.json` (ตัวพิมพ์เล็กหรือใหญ่ของ hash ไม่สำคัญ) และ `Select-String` ต้องพิมพ์ `True` (token ที่ commit ตรงกับไฟล์) · ห้ามลบไฟล์นี้ (ถ้าลบ ค่าที่ commit ใช้ไม่ได้ ต้องสร้างใหม่ตั้งแต่ข้อ 1)

## 6. ส่ง snapshot ก่อน cutoff ในภายหลัง
ใช้ขั้นตอนของ `docs/runbooks/ENV-001-vps.md` ข้อ 10 (D-021 ทาง (a)) แล้วรันข้อ 3 ของ runbook นี้ซ้ำทุกครั้งหลังส่ง · runbook นั้นอยู่ใน branch `chore/ENV-001-vps-acquisition-host` จนกว่า ENV-001 จะ merge

## สรุปสิ่งที่ส่งกลับ
| ข้อ | สิ่งที่ส่ง |
|---|---|
| 1 | JSON 6 ค่าที่ `make_sentinel.py` พิมพ์ และผล `Get-FileHash` |
| 2 | คำยืนยันว่าถอน terminal, ลบ `%APPDATA%\MetaQuotes`, ไม่มี `net use` และ `cmdkey` ของ VPS แล้ว |
| 3 | รายงาน envcheck รอบที่ `RESEARCH HOST: PASS` พร้อมเวลา และ `exit status: 0` |
| 4 | ผล Test-NetConnection (ปิดบัง IP), ผลของ `dir` ทั้งสองบรรทัด, คำยืนยันของ `cmdkey /list` |
| 5 | ผล `Get-FileHash`, ความยาว และ `Select-String` ของ sentinel บน VPS พร้อมเวลา |
