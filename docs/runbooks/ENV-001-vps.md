# Runbook ENV-001: เช่าและตั้ง Windows VPS ให้ปลอดภัย

Contract: `docs/contracts/ENV-001-vps-acquisition-host.md` (v1.5) · ผู้ทำ: เจ้าของ · ใช้เวลา ≈ 2 ชั่วโมง

กติกาตลอดทั้ง runbook:
- **คุณ**รันทุกคำสั่งบน VPS · Claude ไม่เข้าถึง VPS
- ส่งผลกลับเป็น**ข้อความ** และ**ปิดบัง IP ทุกครั้ง**ก่อนวาง (เขียนเป็น `x.x.x.x`) · ไม่ส่งไฟล์ ไม่ส่งรหัสผ่าน ไม่ส่งเลขบัญชีเต็ม
- ปิดหน้าต่าง Claude Code และ Codex บนเครื่องคุณก่อนเปิด RDP ไป VPS (ENV-002 (ค))
- คำสั่งที่ขึ้นต้นด้วย `PS>` รันใน PowerShell · ส่วนใหญ่ต้องเปิดแบบ **Administrator** (ระบุไว้ทุกขั้น)

## 0. เช่า VPS
- **สเปก:** Windows Server 2025 (64-bit, license รวมในราคา), 2–4 vCPU, RAM 8 GB, SSD 80–100 GB, IP คงที่, จ่ายรายเดือน · งบไม่เกิน 40 USD/เดือน (SPEC Q-10)
- **ผู้ให้บริการต้องมี:** firewall ที่จำกัด IP ต้นทางได้ (ชั้นนอก) · ถ้ามี MFA ของ console ให้เปิด · ถ้า IP บ้านเปลี่ยนบ่อยหรืออยู่หลัง CGNAT ต้องมี VPN ของผู้ให้บริการ
- **ห้ามใช้:** MQL5 virtual hosting (รัน Python ไม่ได้)
- ตรวจ CGNAT ก่อน: เทียบ WAN IP ในหน้าตั้งค่า router กับ IP ที่ https://ifconfig.me แสดง · ไม่ตรงกัน = CGNAT → ใช้ทาง VPN
- ส่งให้ Claude: ชื่อผู้ให้บริการ, แพ็กเกจ, ราคา/เดือน, ผลตรวจ CGNAT (ตรง/ไม่ตรง)

## 1. ชั้นนอก: firewall ของผู้ให้บริการ
1. ใน console ของผู้ให้บริการ ตั้ง rule ขาเข้า: อนุญาต **TCP 3389** (และ UDP 3389 ถ้ามีให้เลือก) จาก **IP บ้านของคุณ** (หรือ subnet ของ VPN) เท่านั้น · พอร์ตอื่นปิดทั้งหมด
2. เปลี่ยนรหัสผ่าน Administrator ที่ผู้ให้บริการให้มา เป็นรหัสยาวที่ไม่ซ้ำที่ใด · **ไม่บันทึกรหัส RDP** ในเครื่องคุณ (ไม่ติ๊ก "Remember me")
3. RDP เข้า VPS แล้วรัน Windows Update จนไม่มีอะไรค้าง แล้ว restart

## 2. ชั้นใน: firewall ของ Windows (PowerShell แบบ Administrator บน VPS)
**ระวัง:** ทำจากเครื่องที่ใช้ IP บ้านเท่านั้น ถ้าใส่ IP ผิดจะเข้า RDP ไม่ได้ และต้องกู้ผ่าน console ของผู้ให้บริการ
```powershell
PS> Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -DefaultInboundAction Block
PS> Set-NetFirewallRule -Name RemoteDesktop-UserMode-In-TCP,RemoteDesktop-UserMode-In-UDP -RemoteAddress <IP บ้าน>
PS> Disable-NetFirewallRule -Name RemoteDesktop-Shadow-In-TCP
```
rule อื่นที่ต้องปิด host_report จะบอกชื่อในขั้นที่ 6 (เช่น rule ของ WinRM หรือของแอป) · **ห้ามปิด rule ที่ host_report แนะนำให้แก้ด้วย `Set-NetFirewallRule`**

## 3. RDP: NLA, lockout, drive, clipboard (PowerShell แบบ Administrator)
```powershell
PS> $k = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services'
PS> New-Item -Path $k -Force | Out-Null
PS> Set-ItemProperty -Path $k -Name UserAuthentication -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name fDisableCdm -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name SCClipLevel -Type DWord -Value 1
PS> net accounts /lockoutthreshold:5 /lockoutduration:30 /lockoutwindow:30
PS> Restart-Computer
```
- `UserAuthentication = 1`: บังคับ NLA · `fDisableCdm = 1`: ปิด drive redirection · `SCClipLevel = 1`: clipboard จาก VPS มาเครื่องคุณได้แค่**ข้อความ** (ENV-001 (ค))
- Server 2022 ต้องมี cumulative update 2024-07 (KB5040437) ขึ้นไป จึงจะรู้จัก `SCClipLevel` · ถ้าเลือกปิด clipboard ทั้งหมดแทน: `Set-ItemProperty -Path $k -Name fDisableClip -Type DWord -Value 1` แล้วส่งผลด้วยการพิมพ์
- ถ้ามี OneDrive, Dropbox, Google Drive หรือ iCloud ติดตั้งอยู่: ถอนออกใน Settings → Apps

## 4. Git และสำเนา repo (PowerShell ธรรมดา)
1. ติดตั้ง Git for Windows จาก https://git-scm.com/download/win
2. ```powershell
   PS> git config --global credential.helper ""
   PS> git clone https://github.com/faztycoding/Sochron1k.git C:\Sochron1k
   PS> cd C:\Sochron1k
   ```
   บรรทัดแรกล้างตัวจัดการรหัสของ Git (VPS ต้องไม่มี credential ของ GitHub) · clone ผ่าน HTTPS โดยไม่ใส่ชื่อผู้ใช้ใน URL

## 5. uv และ Python (PowerShell ธรรมดา ที่ `C:\Sochron1k`)
1. ติดตั้ง uv รุ่น 0.13.x ล่าสุดที่ ≥ 0.13.4 (วันที่เขียน: **0.13.5**) จากตัวติดตั้งทางการ:
   ```powershell
   PS> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.13.5/install.ps1 | iex"
   ```
   ปิดแล้วเปิด PowerShell ใหม่
2. ```powershell
   PS> uv --version
   PS> Get-FileHash (Get-Command uv).Source
   PS> uv sync --help | Select-String -- '--check'
   PS> uv run --help | Select-String -- '--no-sync'
   PS> uv python install 3.12.15
   PS> uv sync --locked --python 3.12.15
   ```
   ทำขั้นนี้แบบออนไลน์ก่อนคำสั่ง offline ใดๆ · สองบรรทัด `Select-String` ต้องพิมพ์บรรทัดที่มี flag นั้นออกมา
3. **ส่งให้ Claude:** ผลของ `uv --version`, SHA-256 จาก `Get-FileHash` และผลของสองบรรทัด `Select-String` · Claude ตั้ง `EXPECTED_UV` และแถวใน `docs/tooling/registry.md` แล้วบอกให้คุณรัน `git pull`

## 6. ตรวจเครื่อง (AC-01, PowerShell ธรรมดา ที่ `C:\Sochron1k`)
```powershell
PS> git pull
PS> uv run --no-sync --offline python scripts/env/host_report.py --role acquisition --repo .
```
- บรรทัดสุดท้ายต้องเป็น `HOST REPORT: PASS` · ถ้าเป็น FAIL ทำตามคำแนะนำในคอลัมน์ Detail ทีละข้อ (ปิด rule ที่บอกให้ปิด, แก้ scope ที่บอกให้แก้) แล้วรันใหม่ · บันทึกรายการ rule ที่คุณปิดหรือแก้
- รายงานไม่มี IP เต็ม (แสดงแค่จำนวนรายการและความยาว prefix)
- **ทดสอบ drift (หลังได้ PASS):**
  ```powershell
  PS> Get-FileHash uv.lock
  PS> (Get-Content pyproject.toml) -replace 'tzdata==2026.5','tzdata==2026.4' | Set-Content pyproject.toml
  PS> uv run --no-sync --offline python scripts/env/host_report.py --role acquisition --repo .
  PS> Get-FileHash uv.lock
  PS> git checkout -- pyproject.toml
  PS> git status --short
  PS> uv run --no-sync --offline python scripts/env/host_report.py --role acquisition --repo .
  ```
  ผลที่ถูก: รอบกลาง `python_env` เป็น FAIL · SHA-256 ของ `uv.lock` สองครั้งเท่ากัน · `git status --short` ไม่พิมพ์อะไร · รอบสุดท้ายกลับเป็น PASS · ถ้า hash ของ `uv.lock` เปลี่ยน: `git checkout -- pyproject.toml uv.lock` แล้ว `uv sync --locked --python 3.12.15` ก่อนทำขั้นนี้ใหม่ และแจ้ง Claude
- **ส่งให้ Claude:** รายงานทั้งหมดของรอบที่ PASS, ผลของการทดสอบ drift, รายการ rule ที่ปิดหรือแก้

## 7. ทดสอบจากภายนอก (AC-03, PowerShell บนเครื่องคุณ)
1. จากเครือข่ายบ้าน:
   ```powershell
   PS> foreach ($p in 3389,22,80,443,445,5985,5986) { Test-NetConnection <IP ของ VPS> -Port $p -WarningAction SilentlyContinue | Select-Object RemotePort, TcpTestSucceeded }
   ```
   ผลที่ถูก: 3389 เป็น True · พอร์ตอื่นเป็น False ทั้งหมด
2. จากเครือข่ายอื่นที่ไม่อยู่ใน allowlist (เช่น เปิด hotspot มือถือแล้วต่อโน้ตบุ๊ก): รันเฉพาะพอร์ต 3389 → ต้องเป็น **False**
3. **ส่งให้ Claude:** ผลทั้งสองชุด (ปิดบัง IP), รายการ rule ใน firewall ของผู้ให้บริการ (ปิดบัง IP), ผลตรวจ CGNAT · ถ้าเป็น CGNAT ให้ทำขั้นนี้ใหม่ผ่าน VPN

## 8. ทดสอบช่องทางไฟล์ (AC-04, ใน RDP session ปกติ)
1. บน VPS สร้างไฟล์ `test.txt` บน Desktop → คลิกขวา Copy → บนเครื่องคุณ คลิกขวา Paste บน Desktop → **ต้องวางไม่ได้**
2. บน VPS เปิด Notepad พิมพ์ข้อความ → Copy → วางบนเครื่องคุณ → **ต้องวางได้** (ถ้าเลือกปิด clipboard ทั้งหมดในขั้นที่ 3 ข้อความจะวางไม่ได้ ซึ่งถูกต้องเช่นกัน)
3. บน VPS เปิด File Explorer พิมพ์ `\\tsclient` ในช่อง address → **ต้องเปิดไม่ได้**
4. **ส่งให้ Claude:** ผลทั้งสามข้อพร้อมเวลา

## 9. Terminal (AC-05, คำยืนยันทีละข้อพร้อมเวลา)
- [ ] ติดตั้ง MT5 จากเว็บของ Exness (ไม่ใช่จากแหล่งอื่น)
- [ ] login บัญชี Demo ด้วย**รหัส investor** (อ่านอย่างเดียว) · รหัสไม่ถูกบันทึกในไฟล์ใดที่ Claude เห็น
- [ ] Tools → Options → Charts → Max bars in chart = **Unlimited** แล้ว restart terminal
- [ ] PowerShell แบบ Administrator: `w32tm /resync` สำเร็จ
- [ ] uv และ Python ติดตั้งแบบออนไลน์ตามขั้นที่ 5 และสอง flag มีในรุ่นที่ติดตั้ง
- **ส่งให้ Claude:** คำยืนยันแต่ละข้อพร้อมเวลา (ไม่ต้องส่งเลขบัญชีหรือรหัส)

## 10. ส่ง snapshot ก่อน cutoff มาเครื่องวิจัย (D-021 ทาง (a)) — ใช้หลัง ENV-1 ผ่านเท่านั้น
ทำครั้งละครั้ง และปิดหน้าต่าง Claude Code และ Codex บนเครื่องคุณก่อน:
1. บนเครื่องคุณ: `subst T: C:\path\to\Sochron1k\data\transfer` (โฟลเดอร์ว่าง)
2. บน VPS (Administrator): `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name fDisableCdm -Value 0`
3. เชื่อม RDP ด้วยไฟล์ .rdp ที่ redirect เฉพาะไดรฟ์ T: · คัดลอก**เฉพาะไฟล์ที่อยู่ใน manifest ที่ `period_end_utc` ≤ 2025-01-01** · ตัดการเชื่อมต่อ
4. บน VPS: ตั้ง `fDisableCdm` กลับเป็น 1 · บนเครื่องคุณ: `subst T: /d`
5. รัน `host_report.py` บน VPS (ต้อง PASS) และ envcheck ของ ENV-002 บนเครื่องคุณ (ต้อง PASS)
6. **ส่งให้ Claude:** วันที่, รายการไฟล์และ SHA-256, ผลของตัวตรวจทั้งสอง
(ต้องยืนยันก่อนใช้จริงว่า mstsc redirect ไดรฟ์จาก `subst` ได้ ถ้าไม่ได้ ใช้ไดรฟ์ VHD ขนาดเล็กที่ mount ไว้ที่โฟลเดอร์เดียวกันแทน)

## สรุปสิ่งที่ส่งกลับ
| ขั้น | สิ่งที่ส่ง |
|---|---|
| 0 | ผู้ให้บริการ, แพ็กเกจ, ราคา, ผล CGNAT |
| 5 | `uv --version`, SHA-256 ของ uv, ผล `Select-String` สองบรรทัด |
| 6 | รายงาน host_report รอบ PASS, ผล drift test, rule ที่ปิดหรือแก้ |
| 7 | ผล Test-NetConnection ทั้งสองเครือข่าย, rule ของผู้ให้บริการ (ปิดบัง IP) |
| 8 | ผลทดสอบช่องทางไฟล์สามข้อ |
| 9 | คำยืนยันของ checklist terminal |
