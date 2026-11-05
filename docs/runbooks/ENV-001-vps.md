# Runbook ENV-001: เช่าและตั้ง Windows VPS ให้ปลอดภัย

Contract: `docs/contracts/ENV-001-vps-acquisition-host.md` (v1.7) · ผู้ทำ: เจ้าของ · ใช้เวลา ≈ 2–3 ชั่วโมง

กติกาตลอดทั้ง runbook:
- **คุณ**รันทุกคำสั่งบน VPS · Claude ไม่เข้าถึง VPS
- ส่งผลกลับเป็น**ข้อความ** และ**ปิดบัง IP ทุกครั้ง**ก่อนวาง (เขียนเป็น `x.x.x.x`) · ไม่ส่งไฟล์ ไม่ส่งรหัสผ่าน ไม่ส่งเลขบัญชีเต็ม
- ปิดหน้าต่าง Claude Code และ Codex บนเครื่องคุณก่อนเปิด RDP ไป VPS (ENV-002 (ค))
- คำสั่งที่ขึ้นต้นด้วย `PS>` รันใน PowerShell ไม่ต้องพิมพ์ `PS>` · แต่ละขั้นบอกว่าต้องเปิดแบบ **Administrator** หรือแบบธรรมดา
- **กฎกันล็อกตัวเอง:** ก่อนเปลี่ยน firewall, ปิด rule ใดๆ หรือ restart ให้เปิด RDP session ที่สองจากบ้านให้ได้ก่อนเสมอ และอย่าปิด session แรกจนกว่า session ใหม่จะเข้าได้ · ถ้าเข้าไม่ได้ ใช้ console ของผู้ให้บริการแก้ · Windows Server ให้บัญชีหนึ่งมี session เดียว: ถ้าใช้บัญชีเดิมแล้ว session ใหม่เข้าได้ หน้าต่างแรกจะขึ้นว่าถูกตัดการเชื่อม ซึ่งเป็นเรื่องปกติ · ถ้า session ใหม่เข้าไม่ได้ หน้าต่างแรกจะยังอยู่ ให้แก้จากหน้าต่างนั้น

## 0. เช่า VPS
- **สเปก:** Windows Server 2025 (64-bit, license รวมในราคา), 2–4 vCPU, RAM 8 GB, SSD 80–100 GB, IP คงที่, จ่ายรายเดือน · งบไม่เกิน 40 USD/เดือน (SPEC Q-10)
- **ผู้ให้บริการต้องมี:** firewall ที่จำกัด IP ต้นทางได้ (ชั้นนอก) และ console สำรอง (VNC/web console) ที่ใช้ได้แม้ RDP ปิด · ถ้ามี MFA ของ console ให้เปิด · ถ้า IP บ้านเปลี่ยนบ่อยหรืออยู่หลัง CGNAT ต้องมี VPN ของผู้ให้บริการ
- **ห้ามใช้:** MQL5 virtual hosting (รัน Python ไม่ได้)
- ตรวจ CGNAT: เทียบ WAN IP ในหน้าตั้งค่า router กับ IPv4 ที่ https://api.ipify.org แสดง · ไม่ตรงกัน = CGNAT → ใช้ทาง VPN
- ส่งให้ Claude: ชื่อผู้ให้บริการ, แพ็กเกจ, ราคา/เดือน, ผลตรวจ CGNAT (ตรง/ไม่ตรง)

## 1. ชั้นนอก: firewall ของผู้ให้บริการ และบัญชี
1. ใน console ของผู้ให้บริการ ตั้ง rule ขาเข้า: อนุญาต **TCP 3389** (และ UDP 3389 ถ้ามีให้เลือก) จาก **IPv4 บ้านของคุณ** (หรือ subnet ของ VPN) เท่านั้น · พอร์ตอื่นปิดทั้งหมด · IPv6: ข้อ 5 จะตรวจว่า VPS มี IPv6 สาธารณะหรือไม่ ถ้ามี ให้กลับมาข้อนี้แล้วปิด IPv6 ที่ผู้ให้บริการ หรือทำ rule แบบเดียวกันให้ IPv6
2. RDP เข้า VPS ด้วยบัญชีที่ผู้ให้บริการให้มา · **ไม่บันทึกรหัส RDP** ในเครื่องคุณ (ไม่ติ๊ก "Remember me")
3. **สร้างบัญชี admin ของคุณเอง** (PowerShell แบบ Administrator) แล้วใช้บัญชีนี้ RDP ต่อจากนี้ (lockout คุ้มครองบัญชีนี้แน่นอน):
   ```powershell
   PS> $p = Read-Host -AsSecureString "รหัสผ่านใหม่ (ยาว ไม่ซ้ำที่ใด)"
   PS> New-LocalUser -Name "<ชื่อบัญชีของคุณ>" -Password $p -PasswordNeverExpires
   PS> Add-LocalGroupMember -Group "Administrators" -Member "<ชื่อบัญชีของคุณ>"
   PS> Add-LocalGroupMember -Group "Remote Desktop Users" -Member "<ชื่อบัญชีของคุณ>"
   ```
   เปิด RDP session ที่สองด้วยบัญชีใหม่ให้ได้ก่อน แล้วจึงปิดบัญชีเดิม: `Disable-LocalUser -Name Administrator` (ถ้าบัญชีที่ผู้ให้บริการให้ชื่ออื่น ใช้ชื่อนั้น)
4. รัน Windows Update จนไม่มีอะไรค้าง แล้ว restart (ตามกฎกันล็อกตัวเอง)
5. ตรวจ IPv6 (PowerShell ธรรมดา): `Get-NetIPAddress -AddressFamily IPv6 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' -and $_.IPAddress -notlike 'fe80*' } | Select-Object InterfaceAlias, PrefixOrigin` · ส่งให้ Claude ว่ามีหรือไม่มี (ไม่ต้องส่งตัวที่อยู่) · **ถ้ามี:** กลับไปทำส่วน IPv6 ของข้อ 1 ก่อนไปขั้นที่ 2

## 2. ชั้นใน: firewall ของ Windows (PowerShell แบบ Administrator บน VPS)
ทำตามลำดับนี้ห้ามสลับ:
1. ดูที่อยู่ที่ VPS เห็นว่าคุณต่อเข้ามา (อย่าวางผลนี้ในแชท):
   ```powershell
   PS> (Get-NetTCPConnection -LocalPort 3389 -State Established).RemoteAddress
   ```
2. เปิด rule RDP ตั้งต้นและจำกัดให้เป็นที่อยู่นั้น:
   ```powershell
   PS> Enable-NetFirewallRule -Name RemoteDesktop-UserMode-In-TCP,RemoteDesktop-UserMode-In-UDP
   PS> Set-NetFirewallRule -Name RemoteDesktop-UserMode-In-TCP,RemoteDesktop-UserMode-In-UDP -RemoteAddress <ที่อยู่จากข้อ 1>
   ```
3. **เปิด RDP session ที่สองจากบ้าน** ให้เข้าได้ก่อน (session แรกยังเปิดค้างไว้)
4. แล้วจึงตั้ง profile เป็น Block และปิด Shadow:
   ```powershell
   PS> Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -DefaultInboundAction Block
   PS> Disable-NetFirewallRule -Name RemoteDesktop-Shadow-In-TCP
   ```
5. ลองเปิด session ใหม่อีกครั้งก่อนปิด session เดิม

rule อื่นที่ต้องปิด host_report จะบอกในขั้นที่ 6 · **ห้ามปิด rule ที่ host_report แนะนำให้แก้ด้วย `Set-NetFirewallRule`** และ**ห้ามปิด rule ที่ชื่อขึ้นต้นด้วย `CoreNet-DHCP`** (VPS อาจเสียเน็ต)

## 3. RDP: NLA, lockout, redirection, clipboard (PowerShell แบบ Administrator)
```powershell
PS> $k = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services'
PS> if (-not (Test-Path $k)) { New-Item -Path $k | Out-Null }
PS> Set-ItemProperty -Path $k -Name UserAuthentication -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name fDisableCdm -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name fDisableCpm -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name fDisableCcm -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name fDisableLPT -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name fDisablePNPRedir -Type DWord -Value 1
PS> Set-ItemProperty -Path $k -Name SCClipLevel -Type DWord -Value 1
PS> net accounts /lockoutthreshold:5 /lockoutduration:30 /lockoutwindow:30
```
- `UserAuthentication = 1`: บังคับ NLA · `fDisableCdm`: ปิด drive redirection · `fDisableCpm`, `fDisableCcm`, `fDisableLPT`, `fDisablePNPRedir`: ปิด printer, COM, LPT และอุปกรณ์ PnP (เช่น มือถือ) ซึ่งเป็นทางส่งไฟล์ออกได้เหมือนกัน · `SCClipLevel = 1`: clipboard จาก VPS มาเครื่องคุณได้แค่**ข้อความ** (ENV-001 (ค))
- Server 2022 ต้องมี cumulative update 2024-07 (KB5040437) ขึ้นไป จึงจะรู้จัก `SCClipLevel` · ถ้าเลือกปิด clipboard ทั้งหมดแทน: `Set-ItemProperty -Path $k -Name fDisableClip -Type DWord -Value 1` แล้วส่งผลด้วยการพิมพ์
- ถ้ามี OneDrive, Dropbox, Google Drive หรือ iCloud ติดตั้งอยู่: ถอนออกใน Settings → Apps
- จากนั้น `Restart-Computer` (ตามกฎกันล็อกตัวเอง: เปิด session ที่สองได้ก่อน)

## 4. Git และสำเนา repo (PowerShell ธรรมดา)
1. ติดตั้ง Git for Windows จาก https://git-scm.com/download/win · ในหน้าเลือก **credential helper ให้เลือก "None"**
2. ```powershell
   PS> git config --global credential.helper --% ""
   PS> git config --show-origin --get-regexp "^credential\..*helper$"
   PS> git clone https://github.com/faztycoding/Sochron1k.git C:\Sochron1k
   PS> cd C:\Sochron1k
   ```
   บรรทัดแรกล้างตัวจัดการรหัสของ Git (VPS ต้องไม่มี credential ของ GitHub) · ต้องพิมพ์ `--%` ตามนี้ เพราะ PowerShell 5.1 ทิ้ง `""` ถ้าไม่มี `--%` · บรรทัดที่สองต้องจบด้วยบรรทัด `credential.helper` ที่ไม่มีค่า (ของไฟล์ global) · clone ผ่าน HTTPS โดยไม่ใส่ชื่อผู้ใช้ใน URL · **ห้ามตั้ง SSH ไป GitHub (key ใน `~/.ssh`), `insteadOf` ไป URL ที่ไม่ใช่ https หรือ `http.extraheader` บน VPS** (host_report จะ FAIL)

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
1. ตรวจชื่อ rule DHCP ก่อนทำตามคำแนะนำใดๆ แล้วส่งผลให้ Claude:
   ```powershell
   PS> Get-NetFirewallRule -Name CoreNet-DHCP-In,CoreNet-DHCPV6-In | Select-Object Name, Enabled
   ```
2. ```powershell
   PS> git pull
   PS> uv run --no-sync --offline python scripts/env/host_report.py --role acquisition --repo .
   ```
- บรรทัดสุดท้ายต้องเป็น `HOST REPORT: PASS` · ถ้าเป็น FAIL ทำตามคำแนะนำในคอลัมน์ Detail ทีละข้อแล้วรันใหม่ (ตามกฎกันล็อกตัวเอง) · ส่วนหลัง `#` ในคำแนะนำเป็นคำอธิบาย ไม่ต้องพิมพ์ · rule ที่ชื่อถูกบังไว้ (มี path หรือที่อยู่) ให้หาจาก `Get-NetFirewallRule` บน VPS · **rule ชื่อ `CoreNet-DHCP*` ห้ามปิด ให้ส่งให้ Claude แทน** · บันทึกรายการ rule ที่คุณปิดหรือแก้
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
- **ส่งให้ Claude:** ผลของข้อ 1, รายงานทั้งหมดของรอบที่ PASS, ผลของการทดสอบ drift, รายการ rule ที่ปิดหรือแก้

## 7. ทดสอบจากภายนอก (AC-03, PowerShell บนเครื่องคุณ)
1. จากเครือข่ายบ้าน:
   ```powershell
   PS> foreach ($p in 3389,22,80,443,445,5985,5986) { Test-NetConnection <IP ของ VPS> -Port $p -WarningAction SilentlyContinue | Select-Object RemotePort, TcpTestSucceeded }
   ```
   ผลที่ถูก: 3389 เป็น True · พอร์ตอื่นเป็น False ทั้งหมด
2. จากเครือข่ายอื่นที่ไม่อยู่ใน allowlist (เช่น เปิด hotspot มือถือแล้วต่อโน้ตบุ๊ก): รันเฉพาะพอร์ต 3389 → ต้องเป็น **False**
3. IPv6 (ทำเมื่อขั้นที่ 1.5 พบ IPv6 สาธารณะ):
   1. ตรวจก่อนว่าเครื่องคุณออก IPv6 ได้ (ปลายทางนี้มีแต่ IPv6): `Test-NetConnection ipv6.google.com -Port 443 -WarningAction SilentlyContinue | Select-Object TcpTestSucceeded`
   2. ถ้าเป็น True: รันคำสั่งของข้อ 1 กับที่อยู่ IPv6 ของ VPS → ผลที่ถูก: **ทั้ง 7 พอร์ตเป็น False** เพราะ scope ของ Windows ในขั้นที่ 2.2 มีแค่ที่อยู่ที่ VPS เห็นตอนนั้น (ปกติเป็น IPv4) · ยกเว้นคุณใส่ IPv6 ของบ้านไว้ทั้งใน firewall ของผู้ให้บริการและใน scope ของ Windows: 3389 จึงเป็น True ได้ ส่วนพอร์ตอื่นต้องเป็น False · ถ้า hotspot ของข้อ 2 ออก IPv6 ได้ (ตรวจแบบข้อ 3.1) ให้ลอง 3389 กับที่อยู่ IPv6 ด้วย → ต้องเป็น False
   3. ถ้าเป็น False (เครื่องคุณไม่มี IPv6): ผล "False ทุกพอร์ต" ไม่ได้พิสูจน์อะไร ให้บันทึกว่า **"IPv6 ไม่ได้ทดสอบ"** แล้วส่ง rule IPv6 ของผู้ให้บริการ หรือหลักฐานว่าปิด IPv6 ที่ผู้ให้บริการแล้วแทน
4. **ส่งให้ Claude:** ผลทุกชุด (ปิดบัง IP), ผลของข้อ 3.1 (หรือ "IPv6 ไม่ได้ทดสอบ"), รายการ rule ใน firewall ของผู้ให้บริการ (ปิดบัง IP), ผลตรวจ CGNAT · ถ้าเป็น CGNAT ให้ทำขั้นนี้ใหม่ผ่าน VPN

## 8. ทดสอบช่องทางไฟล์ (AC-04)
1. ก่อนเชื่อม: เปิด mstsc → Show Options → Local Resources → More… → **ติ๊ก Drives** (ขอ redirect ทุกไดรฟ์ เพื่อทดสอบว่า VPS ปฏิเสธ) → Printers ติ๊กไว้ด้วย → Connect
2. บน VPS สร้างไฟล์ `test.txt` บน Desktop → คลิกขวา Copy → บนเครื่องคุณ คลิกขวา Paste บน Desktop → **ต้องวางไม่ได้**
3. บน VPS เปิด Notepad พิมพ์ข้อความ → Copy → วางบนเครื่องคุณ → **ต้องวางได้** (ถ้าเลือกปิด clipboard ทั้งหมดในขั้นที่ 3 ข้อความจะวางไม่ได้ ซึ่งถูกต้องเช่นกัน)
4. บน VPS เปิด File Explorer พิมพ์ `\\tsclient` ในช่อง address → **ต้องไม่มีไดรฟ์** และใน "This PC" ต้องไม่มีไดรฟ์ของเครื่องคุณ
5. บน VPS: `Get-Printer | Select-Object Name, Type` → **ต้องไม่มี printer ที่มาจากเครื่องคุณ** (ชื่อมักลงท้ายด้วย "(redirected …)") · ถ้า `Get-Printer` ขึ้นว่าติดต่อ Print Spooler ไม่ได้ ให้บันทึกว่า **"spooler off"** (ไม่มีช่องทาง printer)
6. ตัดการเชื่อม แล้วกลับไปเอาติ๊ก Drives และ Printers ออกใน mstsc
7. **ส่งให้ Claude:** ผลทุกข้อพร้อมเวลา และยืนยันว่าข้อ 1 ติ๊ก Drives ไว้จริง

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
2. ทำไฟล์ .rdp ที่ redirect **เฉพาะ T:**: เปิด mstsc → Show Options → Local Resources → More… → ใต้ Drives ติ๊ก**เฉพาะ T:** → OK → แท็บ General → Save As → เก็บไว้**นอก repo** (เช่น Documents)
3. บน VPS (Administrator): `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name fDisableCdm -Value 0` แล้วตัดการเชื่อม
4. เชื่อมด้วยไฟล์ .rdp จากข้อ 2 · คัดลอก**เฉพาะไฟล์ที่อยู่ใน manifest ที่ `period_end_utc` ≤ 2025-01-01** ไปที่ T: · ตัดการเชื่อม
5. ปิดช่องทางไฟล์กลับ:
   - ก่อนเชื่อม: เปิด mstsc → Show Options → Local Resources → More… → **เอาติ๊กไดรฟ์ออกทุกตัว** (การเชื่อมแบบปกติของ mstsc อาจจำ T: จากข้อ 2 ไว้ และตอนนี้ VPS ยังยอมรับไดรฟ์อยู่) → Connect
   - บน VPS (Administrator): `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name fDisableCdm -Value 1`
   - ตัดการเชื่อม แล้วเชื่อมใหม่ · บน VPS เปิด File Explorer พิมพ์ `\\tsclient` → **ต้องไม่มีไดรฟ์**
   - บนเครื่องคุณ: `subst T: /d`
6. รัน `host_report.py` บน VPS (ต้อง PASS) และ envcheck ของ ENV-002 บนเครื่องคุณ (ต้อง PASS)
7. **ส่งให้ Claude:** วันที่, รายการไฟล์และ SHA-256, ผลของตัวตรวจทั้งสอง
(ต้องยืนยันก่อนใช้จริงว่า mstsc redirect ไดรฟ์จาก `subst` ได้ ถ้าไม่ได้ ใช้ไดรฟ์ VHD ขนาดเล็กที่ mount ไว้ที่โฟลเดอร์เดียวกันแทน)

## สรุปสิ่งที่ส่งกลับ
| ขั้น | สิ่งที่ส่ง |
|---|---|
| 0 | ผู้ให้บริการ, แพ็กเกจ, ราคา, ผล CGNAT |
| 1 | มีหรือไม่มี IPv6 สาธารณะ, ยืนยันว่าสร้างบัญชี admin ใหม่และปิดบัญชีเดิมแล้ว |
| 5 | `uv --version`, SHA-256 ของ uv, ผล `Select-String` สองบรรทัด |
| 6 | ชื่อ rule DHCP, รายงาน host_report รอบ PASS, ผล drift test, rule ที่ปิดหรือแก้ |
| 7 | ผล Test-NetConnection ทุกชุด, ผลตรวจ IPv6 ของเครื่องคุณ (หรือ "IPv6 ไม่ได้ทดสอบ"), rule ของผู้ให้บริการ (ปิดบัง IP) |
| 8 | ผลทดสอบช่องทางไฟล์และ printer |
| 9 | คำยืนยันของ checklist terminal |
