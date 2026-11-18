# Runbook ENV-001: เช่าและตั้ง Windows VPS ให้ปลอดภัย (ขั้นฝั่งเครื่องเจ้าของเป็นฉบับ macOS)

Contract: `docs/contracts/ENV-001-vps-acquisition-host.md` v2.2 (อนุมัติ 2026-11-18; ขั้นฝั่งเครื่องเจ้าของตามหัวข้อ "v2.0: ขั้นฝั่งเครื่องเจ้าของบน macOS") · ผู้ทำ: เจ้าของ · ใช้เวลา ≈ 2–3 ชั่วโมง · ขั้นบน VPS (ข้อ 2–6 และ 9) คงตาม v1.9 · ฉบับ Windows ของขั้นฝั่งเครื่องเจ้าของอยู่ใน history ของ git

กติกาตลอดทั้ง runbook:
- **คุณ**รันทุกคำสั่งบน VPS · Claude ไม่เข้าถึง VPS
- ส่งผลกลับเป็น**ข้อความ** และ**ปิดบัง IP ทุกครั้ง**ก่อนวาง (เขียนเป็น `x.x.x.x`) · ไม่ส่งไฟล์ ไม่ส่งรหัสผ่าน ไม่ส่งเลขบัญชีเต็ม
- **ก่อนเปิด RDP หรือ console ของผู้ให้บริการทุกครั้ง** (ENV-002 checklist C9; รวมข้อ 0, 1.1 และ 1.5): Quit (⌘Q) Visual Studio Code, Claude, ChatGPT/Codex และทุกแอปที่ agent รันอยู่ (บน macOS การปิดหน้าต่างไม่ได้ปิดแอป) แล้วรันใน Terminal.app: `/usr/bin/pgrep -ilf 'claude|codex|chatgpt'` ต้องไม่พิมพ์อะไร · เปิด console ใน browser หรือ profile ที่ไม่มี extension ของ Claude หรือ ChatGPT (ถ้ามี ให้รัน `pgrep` ซ้ำหลังเปิด browser)
- คำสั่งที่ขึ้นต้นด้วย `PS>` รันใน PowerShell บน VPS (แต่ละขั้นบอกว่าต้องเปิดแบบ **Administrator** หรือแบบธรรมดา) · ที่ขึ้นต้นด้วย `%` รันใน Terminal.app บน Mac · ไม่ต้องพิมพ์ `PS>` หรือ `%`
- **กฎกันล็อกตัวเอง:** ก่อนเปลี่ยน firewall, ปิด rule ใดๆ หรือ restart ให้เปิด RDP session ที่สองให้ได้ก่อนเสมอ และอย่าปิด session แรกจนกว่า session ใหม่จะเข้าได้ · บน Mac: ใน Windows App ใช้**รายการ PC ที่สอง**ของ VPS ตัวเดียวกัน (Duplicate รายการเดิม) เพื่อเปิด session ที่สอง เพราะการคลิกรายการเดิมซ้ำอาจนำหน้าต่างเดิมขึ้นมาแทน (ยังไม่ได้ตรวจในแอปจริง: ตรวจตอนใช้ครั้งแรกแล้วบันทึก) · รายการที่ Duplicate ต้องตั้งค่าเหมือนรายการหลักทุกข้อ (ข้อ 1.2 และ C3) และลบทิ้งหลังขั้นที่ต้องใช้มันเสร็จ · ถ้าเปิด session ที่สองไม่ได้ ห้ามเปลี่ยน firewall ให้ใช้ console ของผู้ให้บริการแก้ · Windows Server ให้บัญชีหนึ่งมี session เดียว: ถ้าใช้บัญชีเดิมแล้ว session ใหม่เข้าได้ หน้าต่างแรกจะขึ้นว่าถูกตัดการเชื่อม ซึ่งเป็นเรื่องปกติ · ถ้า session ใหม่เข้าไม่ได้ หน้าต่างแรกจะยังอยู่ ให้แก้จากหน้าต่างนั้น
- ชื่อเมนูของ Windows App มาจากหน้า Microsoft Learn ที่อ่าน 2026-11-17 และยังไม่ได้ตรวจในแอปจริง: ถ้าไม่ตรง ใช้ชื่อในแอปแล้วบันทึกในหลักฐาน

## 0. เช่า VPS
- **สเปก:** Windows Server 2025 (64-bit, license รวมในราคา), 2–4 vCPU, RAM 8 GB, SSD 80–100 GB, IP คงที่, จ่ายรายเดือน · งบไม่เกิน 40 USD/เดือน (SPEC Q-10)
- **ผู้ให้บริการต้องมี:** firewall ที่จำกัด IP ต้นทางได้ (ชั้นนอก) และ console สำรอง (VNC/web console) ที่ใช้ได้แม้ RDP ปิด · ถ้ามี MFA ของ console ให้เปิด (ด้วยอุปกรณ์ที่ไม่ใช่ Mac) · ถ้า IP บ้านเปลี่ยนบ่อยหรืออยู่หลัง CGNAT ต้องมี VPN ของผู้ให้บริการ
- **ห้ามใช้:** MQL5 virtual hosting (รัน Python ไม่ได้)
- ตรวจ CGNAT: เทียบ WAN IP ในหน้าตั้งค่า router กับ IPv4 ที่ `% /usr/bin/curl -s https://api.ipify.org; echo` (หรือ browser) แสดง · ไม่ตรงกัน = CGNAT → ใช้ทาง VPN · จด IP บ้านไว้ใช้ในข้อ 7 แต่**ไม่วางในแชท**
- ส่งให้ Claude: ชื่อผู้ให้บริการ, แพ็กเกจ, ราคา/เดือน, ผลตรวจ CGNAT (ตรง/ไม่ตรง)

## 1. ชั้นนอก: firewall ของผู้ให้บริการ และบัญชี
1. ใน console ของผู้ให้บริการ ตั้ง rule ขาเข้า: อนุญาต **TCP 3389** (และ UDP 3389 ถ้ามีให้เลือก) จาก **IPv4 บ้านของคุณ** (หรือ subnet ของ VPN) เท่านั้น · พอร์ตอื่นปิดทั้งหมด · ผูก rule ชุดนี้กับ VPS เครื่องนี้และเปิดใช้ · ถ้าผู้ให้บริการมี rule ชุดอื่นผูกกับ VPS อยู่แล้ว (เช่น ชุดตั้งต้น) ให้ถอดออก (ข้อ 7.4 จะตรวจทุกชุด) · IPv6: ข้อ 5 จะตรวจว่า VPS มี IPv6 สาธารณะหรือไม่ ถ้ามี ให้กลับมาข้อนี้แล้วปิด IPv6 ที่ผู้ให้บริการ หรือทำ rule แบบเดียวกันให้ IPv6
2. **RDP ด้วย Windows App บน Mac** (ติดตั้งจาก Mac App Store ผู้พัฒนา Microsoft):
   - Add PC: ที่อยู่ = IP ของ VPS · Credentials: **"Ask when required"** (หรือชื่อเทียบเท่า) **ไม่บันทึกรหัส** · แท็บ Folders: ไม่ติ๊ก Redirect folders · แท็บ Devices & Audio: ไม่ติ๊กอุปกรณ์ใด · clipboard ตามที่เลือกใน (ค) (ข้อความเท่านั้น)
   - เชื่อมด้วยบัญชีที่ผู้ให้บริการให้มา · ถ้าแอปถามว่าจะบันทึกรหัส ตอบไม่
   - **ทันทีหลังเชื่อมครั้งแรก** ตรวจเอง (agent ห้ามทำ): C1 Windows App → Settings → Credentials ไม่มีรายการของ VPS · C2 แอป Passwords และ Keychain Access (keychain `login`) ค้น `com.microsoft.rdc.macos`, `Windows App`, `Remote Desktop`, IP ของ VPS, ชื่อผู้ใช้ RDP และโดเมนของผู้ให้บริการ → ไม่พบรายการของ VPS (รวมรายการที่ sync มาจากอุปกรณ์อื่น) · ถ้าพบ ลบแล้วตรวจใหม่
   - การตั้งค่าของข้อนี้ใช้กับ**ทุก**รายการ PC ของ VPS รวมรายการที่ Duplicate ไว้เปิด session ที่สอง
3. **สร้างบัญชี admin ของคุณเอง** (PowerShell แบบ Administrator) แล้วใช้บัญชีนี้ RDP ต่อจากนี้ (lockout คุ้มครองบัญชีนี้แน่นอน):
   ```powershell
   PS> $p = Read-Host -AsSecureString "รหัสผ่านใหม่ (ยาว ไม่ซ้ำที่ใด)"
   PS> New-LocalUser -Name "<ชื่อบัญชีของคุณ>" -Password $p -PasswordNeverExpires
   PS> Add-LocalGroupMember -Group "Administrators" -Member "<ชื่อบัญชีของคุณ>"
   PS> Add-LocalGroupMember -Group "Remote Desktop Users" -Member "<ชื่อบัญชีของคุณ>"
   ```
   เปิด RDP session ที่สองด้วยบัญชีใหม่ (รายการ PC ที่ Duplicate ไว้) ให้ได้ก่อน แล้วจึงปิดบัญชีเดิม: `Disable-LocalUser -Name Administrator` (ถ้าบัญชีที่ผู้ให้บริการให้ชื่ออื่น ใช้ชื่อนั้น) · **ท้ายข้อนี้ ตรวจ C1 และ C2 ของข้อ 1.2 อีกครั้ง** (รหัสที่ใช้ยาวนานถูกพิมพ์ครั้งแรกที่ข้อนี้)
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
3. **เปิด RDP session ที่สองจากบ้าน** (รายการ PC ที่ Duplicate ไว้) ให้เข้าได้ก่อน (session แรกยังเปิดค้างไว้)
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
- Server 2022 ต้องมี cumulative update 2024-07 (KB5040437, OS Build 20348.2582) ขึ้นไป จึงจะรู้จัก `SCClipLevel` · ถ้าเลือกปิด clipboard ทั้งหมดแทน: `Set-ItemProperty -Path $k -Name fDisableClip -Type DWord -Value 1` แล้วส่งผลด้วยการพิมพ์
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
   บรรทัดแรกล้างตัวจัดการรหัสของ Git (VPS ต้องไม่มี credential ของ GitHub) · ต้องพิมพ์ `--%` ตามนี้ เพราะ PowerShell 5.1 ทิ้ง `""` ถ้าไม่มี `--%` · บรรทัดที่สองต้องจบด้วยบรรทัด `credential.helper` ที่ไม่มีค่า (ของไฟล์ global) · clone ผ่าน HTTPS โดยไม่ใส่ชื่อผู้ใช้ใน URL · **ห้ามตั้ง remote แบบ SSH, `insteadOf`/`pushInsteadOf` ไป URL ที่ไม่ใช่ https หรือ `http.extraheader` บน VPS** (host_report จะ FAIL) · **ห้ามสร้าง SSH key ใน `~/.ssh`, ไฟล์ `_netrc`/`.netrc` หรือไฟล์ใต้ `.git/remotes` และ `.git/branches`, ห้ามใส่ URL ใน `branch.*.remote`, `branch.*.pushRemote` หรือ `remote.pushDefault`, ห้ามตั้ง `core.askPass`, `GIT_ASKPASS` หรือ `SSH_ASKPASS` และห้าม sign in GitHub ในโปรแกรมใดบน VPS (editor, GitHub Desktop)**: ทางเหล่านี้ทำให้ git push ได้ และ host_report ตรวจไม่เห็น

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
3. **ส่งให้ Claude:** ผลของ `uv --version`, SHA-256 จาก `Get-FileHash` และผลของสองบรรทัด `Select-String` · Claude ตั้ง `EXPECTED_UV` และแถวใน `docs/tooling/registry.md`, push branch `chore/ENV-001-vps-acquisition-host` แล้วส่ง **hash ของ commit ที่ตรวจแล้ว** ให้คุณ (`host_report.py` ยังไม่อยู่ใน `main` จนกว่าจะ merge หลังได้หลักฐาน)

## 6. ตรวจเครื่อง (AC-01, PowerShell ธรรมดา ที่ `C:\Sochron1k`)
1. ตรวจชื่อ rule DHCP ก่อนทำตามคำแนะนำใดๆ แล้วส่งผลให้ Claude:
   ```powershell
   PS> Get-NetFirewallRule -Name CoreNet-DHCP-In,CoreNet-DHCPV6-In | Select-Object Name, Enabled
   ```
2. ดึง commit ที่ตรวจแล้วจาก Claude (ขั้นที่ 5.3) แล้วรัน host_report:
   ```powershell
   PS> git fetch origin chore/ENV-001-vps-acquisition-host
   PS> git switch --detach <hash ที่ Claude ให้>
   PS> git rev-parse --short HEAD
   PS> git status --short
   PS> uv run --no-sync --offline python scripts/env/host_report.py --role acquisition --repo .
   ```
   `git rev-parse` ต้องพิมพ์ hash เดียวกับที่ Claude ให้ และ `git status --short` ต้องไม่พิมพ์อะไร · ถ้าไม่ตรง หยุดแล้วส่งผลให้ Claude · ถ้า Claude ส่ง hash ใหม่ (เช่น หลังแก้ตามรายงาน) ให้ทำสี่บรรทัดแรกซ้ำด้วย hash ใหม่ · หลัง PR merge แล้วใช้ `git switch main` และ `git pull` แทน
- บรรทัดสุดท้ายต้องเป็น `HOST REPORT: PASS` · ถ้าเป็น FAIL ทำตามคำแนะนำในคอลัมน์ Detail ทีละข้อแล้วรันใหม่ (ตามกฎกันล็อกตัวเอง) · ส่วนหลัง `#` ในคำแนะนำเป็นคำอธิบาย ไม่ต้องพิมพ์ · `|` ท้ายแถวเป็นเส้นขอบตาราง ไม่ใช่ส่วนของคำสั่ง: ก๊อปแค่คำสั่งหลัง `->` ถึง `""` (ถ้าติด `|` มาด้วย PowerShell จะไม่รันและขึ้นว่า empty pipe element) · rule ที่ชื่อถูกบังไว้ (มี path หรือที่อยู่) ให้หาจาก `Get-NetFirewallRule` บน VPS · **rule ชื่อ `CoreNet-DHCP*` ห้ามปิด ให้ส่งให้ Claude แทน** · บันทึกรายการ rule ที่คุณปิดหรือแก้
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

## 7. ทดสอบจากภายนอก (AC-03, Terminal.app บน Mac; ทำ C9 ก่อน)
คำสั่งของข้อนี้พิมพ์บรรทัดที่**ปิดบังที่อยู่แล้ว**พร้อม exit status ของ `nc` เอง (`nc -v` ใส่ที่อยู่ในทุกบรรทัด) · ใส่ที่อยู่จริงแค่ในบรรทัด `VPS=` และไม่วางบรรทัดนั้นในแชท

กติกาการอ่านผลของ `nc` (ใช้กับทุกข้อย่อย):
- ข้อความ usage หรือ option ผิด (เช่น `invalid option`, `port range not valid`) ไม่ใช่ผล: แก้คำสั่งแล้วทำซ้ำ
- ผลที่คาดของพอร์ตที่ปิดคือ `Operation timed out` · ข้อความอื่นนอกจาก timeout และ `Connection refused` (เช่น `No route to host`, `Network is unreachable`) ไม่ใช่ผล: ทำซ้ำ
- `Connection refused` ผ่านได้เฉพาะเมื่อแสดงที่มาได้: พอร์ตเดียวกันได้ timeout เมื่อทดสอบจาก hotspot ของข้อ 7.2 (reset มาจากเส้นทางฝั่งบ้าน) หรือรายการ rule ของข้อ 7.4 ปฏิเสธพอร์ตนั้นและผู้ให้บริการตอบแบบ reject ไม่ใช่ drop · นอกจากนั้นยังไม่ผ่านจนกว่าแก้ที่มา
- ตัวควบคุมทำทั้งก่อนและหลังการทดสอบ: ถ้าตัวควบคุมรอบหลังล้ม ผลของรอบนั้นไม่มีผล ให้ทำซ้ำ

1. **จากเครือข่ายบ้าน** (3389 อยู่ทั้งต้นและท้ายรายการเป็นตัวควบคุม):
   ```zsh
   % VPS='<IP ของ VPS>'
   % for p in 3389 22 80 139 443 445 5985 5986 3389; do out=$(/usr/bin/nc -vz -G 5 "$VPS" $p 2>&1); code=$?; print -r -- "port $p exit $code: ${out//$VPS/x.x.x.x}"; done
   ```
   ผลที่ถูก: 3389 ทั้งบรรทัดแรกและบรรทัดสุดท้าย `exit 0` (`succeeded`) · พอร์ต 22, 80, 139, 443, 445, 5985, 5986 exit ไม่ใช่ 0 ทั้งหมด
2. **จากเครือข่ายที่ไม่อยู่ใน allowlist** (เช่น Mac ต่อ hotspot ของมือถือ; เปิด Terminal.app ใหม่แล้วตั้ง `VPS=` อีกครั้ง):
   ```zsh
   % /usr/bin/curl -s https://api.ipify.org; echo
   % out=$(/usr/bin/nc -vz -G 5 "$VPS" 3389 2>&1); code=$?; print -r -- "port 3389 exit $code: ${out//$VPS/x.x.x.x}"
   % /usr/bin/curl -s https://api.ipify.org; echo
   ```
   `curl` ต้องได้ IP ที่ต่างจาก IP บ้าน (บันทึกแค่ "ต่างจาก IP บ้าน: ใช่" ไม่วาง IP) · ได้ IP เดียวกับบ้านหรือไม่มีเน็ต = ทดสอบนี้ไม่มีผล · 3389 ต้อง exit ไม่ใช่ 0 · `curl` บรรทัดหลังต้องได้ IP อีกครั้ง (ตัวควบคุมรอบหลัง)
3. **IPv6** (ทำเมื่อข้อ 1.5 พบ IPv6 สาธารณะ):
   ```zsh
   % /usr/bin/nc -6 -vz -G 5 ipv6.google.com 443; echo "exit $?"
   % VPS6='<IPv6 ของ VPS>'
   % for p in 3389 22 80 139 443 445 5985 5986; do out=$(/usr/bin/nc -6 -vz -G 5 "$VPS6" $p 2>&1); code=$?; print -r -- "port $p exit $code: ${out//$VPS6/x:x:x:x}"; done
   % /usr/bin/nc -6 -vz -G 5 ipv6.google.com 443; echo "exit $?"
   ```
   - บรรทัดแรกและบรรทัดสุดท้ายเป็นตัวควบคุม (Mac ออก IPv6 ได้ทั้งก่อนและหลัง; r3 F16): ถ้าตัวหลังล้ม ผลของรอบนั้นไม่มีผล
   - ผลที่ถูก: **ทุกพอร์ตรวม 3389 exit ไม่ใช่ 0** เพราะ scope ของ Windows ในขั้นที่ 2.2 มีแค่ที่อยู่ที่ VPS เห็นตอนนั้น (ปกติเป็น IPv4) · ยกเว้นคุณใส่ IPv6 ของบ้านไว้ทั้งใน firewall ของผู้ให้บริการและใน scope ของ Windows: 3389 จึงสำเร็จได้ ส่วนพอร์ตอื่นต้องล้ม
   - ถ้า hotspot ของข้อ 2 ออก IPv6 ได้ (ตรวจด้วยบรรทัดแรก) ให้ลอง 3389 ผ่าน IPv6 จาก hotspot ด้วย → ต้อง exit ไม่ใช่ 0
   - ถ้าบรรทัดแรกล้ม (Mac ไม่มี IPv6): บันทึก **"IPv6 ไม่ได้ทดสอบ"** แล้วส่ง rule IPv6 ของผู้ให้บริการ หรือหลักฐานว่าปิด IPv6 ที่ผู้ให้บริการแล้วแทน
4. **หลักฐานของชั้นนอก** (`nc` แยกไม่ได้ว่าชั้นไหนทิ้ง packet ชั้นนอกจึงพิสูจน์ด้วยข้อนี้):
   - รายการ rule ของ firewall ผู้ให้บริการ (ปิดบัง IP) · เกณฑ์ผ่าน: อนุญาตเฉพาะ TCP 3389 (และ UDP 3389 ถ้ามี) จากที่อยู่ใน allowlist และปฏิเสธที่เหลือทั้งหมด รวม IPv6
   - **หน้าของ VPS ที่แสดง rule ทุกชุดที่ใช้กับ VPS นี้** (firewall, rule set หรือ security group ทุกตัวที่ผูกอยู่ หรือสถานะเปิดของ firewall ราย IP) ปิดบัง IP และชื่อบัญชี · เกณฑ์ผ่านใช้กับ**ทุกชุดรวมกัน** (บางผู้ให้บริการอนุญาตผลรวมของทุกชุดที่ผูก: ชุดที่เปิดกว้างกว่าที่ยังผูกอยู่ = ไม่ผ่าน; r2 F10, r3 F14)
   - ผลตรวจ CGNAT จากข้อ 0 (ตรง/ไม่ตรง) · ถ้าเป็น CGNAT ใช้ทาง VPN แล้วทดสอบข้อ 7 ซ้ำ
5. **ส่งให้ Claude:** ทุกบรรทัดที่คำสั่งพิมพ์ (ปิดบังแล้ว) พร้อมเวลา, คำว่า "ต่างจาก IP บ้าน: ใช่" ของข้อ 2, ผลของข้อ 3 (หรือ "IPv6 ไม่ได้ทดสอบ"), รายการ rule และหน้าของ VPS ในข้อ 4

## 8. ทดสอบช่องทางไฟล์ (AC-04, Windows App บน Mac)
1. **ก่อนเชื่อม บน Mac:**
   ```zsh
   % /bin/mkdir ~/rdp-redirect-test
   % /usr/bin/lpstat -p
   ```
   โฟลเดอร์ทดสอบเปล่าอยู่**นอก repo** · บันทึกว่า `lpstat -p` บอกว่ามี printer queue หรือไม่
2. **ขอ redirect เพื่อทดสอบว่า VPS ปฏิเสธ:** Windows App → แก้รายการ PC หลักของ VPS → แท็บ Folders: ติ๊ก Redirect folders แล้วเพิ่ม `~/rdp-redirect-test` · แท็บ Devices & Audio: ติ๊ก Printers · **บันทึกค่าของสองแท็บนี้ระหว่างทดสอบ** (เขียนเป็นข้อความ) → Connect
3. **บน VPS** (PowerShell ธรรมดา; อ่านอย่างเดียว):
   ```powershell
   PS> Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' | Select-Object fDisableCdm, fDisableCpm, fDisableCcm, fDisableLPT, fDisablePNPRedir, SCClipLevel, fDisableClip
   PS> Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Select-Object ProductName, CurrentBuild, UBR
   PS> net view \\tsclient
   PS> Get-Printer | Select-Object Name, Type
   ```
   ผลที่ถูก:
   - **ห้าค่า** `fDisableCdm`, `fDisableCpm`, `fDisableCcm`, `fDisableLPT`, `fDisablePNPRedir` เป็น 1 และ `SCClipLevel` เป็น 1 · `fDisableClip` นับเฉพาะเมื่อ (ค) เลือกปิด clipboard ทั้งหมด (ต้องเป็น 1) · ภายใต้ (ค) แบบข้อความ `fDisableClip` ว่างได้ ไม่ใช่ FAIL (r3 F15)
   - ถ้า `CurrentBuild` เป็น `20348` (Server 2022): `UBR` ต้อง ≥ `2582` (KB5040437) · บันทึก `CurrentBuild` และ `UBR` ทุกกรณี
   - `net view \\tsclient` ไม่มี share (บันทึกข้อความที่พิมพ์) และใน File Explorer พิมพ์ `\\tsclient` ในช่อง address แล้วไม่มี share
   - `Get-Printer` ไม่มี printer ที่มาจาก Mac (ชื่อมักลงท้ายด้วย "(redirected …)") · ถ้าขึ้นว่าติดต่อ Print Spooler ไม่ได้ บันทึก **"spooler off"** · ถ้า `lpstat -p` บน Mac ไม่มี printer: บันทึก **"Mac ไม่มี printer: ช่องทาง printer พิสูจน์ด้วยค่า policy เท่านั้น"** (ไม่ใช่ PASS ของการทดสอบ printer)
4. **clipboard แบบไฟล์** ตามลำดับนี้ (ไฟล์ทดสอบสองฝั่งใช้ชื่อต่างกัน):
   1. ตัวควบคุม Mac → VPS: บน Mac สร้าง `~/mac-to-vps.txt` (`% echo test > ~/mac-to-vps.txt`) → Copy ใน Finder → Paste บน Desktop ของ VPS · วางได้ = Windows App ส่งไฟล์ผ่าน clipboard ได้ ผลของข้อถัดไปจึงพิสูจน์ VPS · วางไม่ได้ = บันทึกว่า "การทดสอบไฟล์ไม่พิสูจน์อะไรเกี่ยวกับ VPS" (การป้องกันทิศนี้อยู่ที่ `SCClipLevel` ของข้อ 3 และ AC-01)
   2. VPS → Mac: บน VPS สร้าง `vps-to-mac.txt` บน Desktop → Copy ใน File Explorer → Paste ใน Finder บน Mac → **ต้องวางไม่ได้** (ไฟล์ชื่อ `vps-to-mac.txt` ปรากฏใน Finder = FAIL)
   3. ข้อความ: บน VPS เปิด Notepad พิมพ์ข้อความ → Copy → วางใน TextEdit บน Mac → **ต้องวางได้** (ถ้า (ค) เลือกปิด clipboard ทั้งหมด ข้อความจะวางไม่ได้ ซึ่งถูกต้องเช่นกัน)
5. **หลังทดสอบ:** ตัดการเชื่อม → ตั้ง**ทุก**รายการ PC ของ VPS (รวมรายการที่ Duplicate) เป็นสภาพของ C3: แท็บ Folders ไม่ติ๊ก Redirect folders (เอา `~/rdp-redirect-test` ออก), แท็บ Devices & Audio ไม่ติ๊กอุปกรณ์ใด, clipboard ตาม (ค) · บันทึกค่า · ลบไฟล์ทดสอบบน VPS และบน Mac: `% /bin/rm ~/mac-to-vps.txt` และ `% /bin/rmdir ~/rdp-redirect-test`
6. **ส่งให้ Claude:** ผลทุกข้อพร้อมเวลา, ค่าของแท็บ Folders และ Devices & Audio ระหว่างทดสอบและหลังข้อ 5, ผลของ `lpstat -p`, ค่า policy, `CurrentBuild` และ `UBR`, ลำดับและผลของข้อ 4

## 9. Terminal (AC-05, คำยืนยันทีละข้อพร้อมเวลา)
- [ ] ติดตั้ง MT5 จากเว็บของ Exness (ไม่ใช่จากแหล่งอื่น)
- [ ] login บัญชี Demo ด้วย**รหัส investor** (อ่านอย่างเดียว) · รหัสไม่ถูกบันทึกในไฟล์ใดที่ Claude เห็น
- [ ] Tools → Options → Charts → Max bars in chart = **Unlimited** แล้ว restart terminal
- [ ] PowerShell แบบ Administrator: `w32tm /resync` สำเร็จ
- [ ] uv และ Python ติดตั้งแบบออนไลน์ตามขั้นที่ 5 และสอง flag มีในรุ่นที่ติดตั้ง
- **ส่งให้ Claude:** คำยืนยันแต่ละข้อพร้อมเวลา (ไม่ต้องส่งเลขบัญชีหรือรหัส)

## 10. ส่ง snapshot ก่อน cutoff มาเครื่องวิจัย (D-021 ทาง (a), ฝั่ง Mac ตาม D-023 ข้อ 5) — ใช้หลัง ENV-1 ผ่านเท่านั้น
ทำครั้งละครั้ง และทำ C9 ก่อนเชื่อม · ช่องทางเดียวคือ folder redirection ของ Windows App เฉพาะโฟลเดอร์ `<repo>/data/transfer/` (repo บน Mac คือ `~/Documents/GitHub/Sochron1k`) · **ใช้ครั้งแรก:** ทำการทดสอบ T1–T4 ตามข้างล่างและบันทึกผลใน contract ของ acquisition host · ข้อใดของ T1–T4 ไม่ผ่าน = ช่องทางนี้ยังไม่อนุมัติ และต้องตัดสินใหม่ (ไม่มีทางสำรองแบบ VHD ของ v1.9)
· **ถ้า T1, T2 หรือ T3 ไม่ผ่าน (review F17): ห้ามคัดลอก · ทำข้อ 6.1–6.3 ทันที** (เอาโฟลเดอร์ออกจากทุกรายการ PC → เชื่อมแล้วตั้ง `fDisableCdm` เป็น 1 → เชื่อมใหม่และตรวจ T4) **แล้วจึงหยุดและส่งผลให้ Claude**
· อย่าเปิดโฟลเดอร์รับไฟล์ใน Finder (Finder เขียนไฟล์ `.DS_Store` ลงไป) · ไฟล์ `.DS_Store` ไม่นับในทุกการตรวจของข้อนี้
1. **ก่อนเปิดช่องทาง:** envcheck ของ ENV-002 บน Mac เป็น PASS (runbook ENV-002 ข้อ 3) และโฟลเดอร์รับไฟล์มีอยู่และว่าง:
   ```zsh
   % /bin/mkdir -p ~/Documents/GitHub/Sochron1k/data/transfer
   % cd ~/Documents/GitHub/Sochron1k/data/transfer
   % /usr/bin/find . -mindepth 1 ! -name .DS_Store
   ```
   `find` ต้องไม่พิมพ์อะไร
2. Windows App → แก้รายการ PC หลักของ VPS → แท็บ Folders → ติ๊ก Redirect folders → เพิ่ม**เฉพาะ** `~/Documents/GitHub/Sochron1k/data/transfer` **โดยไม่ติ๊ก Read-only** (VPS เขียนลงโฟลเดอร์นี้) · โฟลเดอร์อื่นต้องไม่อยู่ในรายการ
3. Connect · **T1** (policy ยังปิด, redirect เปิด): บน VPS `PS> net view \\tsclient` → ไม่มี share
4. บน VPS (Administrator): `PS> Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name fDisableCdm -Value 0` แล้วตัดการเชื่อม
5. Connect อีกครั้ง · **T2:** `PS> net view \\tsclient` มี share เดียว (บันทึกชื่อ share) และ `PS> Get-ChildItem -Force \\tsclient\<ชื่อ share>` แสดงเฉพาะสิ่งที่อยู่ใน `data/transfer` (ก่อนคัดลอก = ว่าง หรือมีแค่ `.DS_Store`) ไม่ใช่ไฟล์อื่นของ repo · **T3:** รัน `host_report.py` (ข้อ 6): item `clipboard` ต้องยังเป็น PASS ขณะ policy เปิด · ผลรวมของรายงานรอบนี้เป็น FAIL ได้เพราะ item `drive_redirection` (policy เปิดอยู่ตามตั้งใจ): **อย่าแก้ตาม FAIL นี้ระหว่างข้อนี้** ดูเฉพาะ item `clipboard` · **คัดลอกเฉพาะเมื่อ T2 และ T3 ผ่าน:** คัดลอก**เฉพาะไฟล์ที่อยู่ใน manifest ที่ `period_end_utc` ≤ 2025-01-01T00:00:00Z** (และตัว manifest) ไปที่ share นั้น · ตัดการเชื่อม
6. **ปิดช่องทางตามลำดับนี้** (ตอนนี้ VPS ยังยอมรับ redirection อยู่):
   1. ใน Windows App เอาโฟลเดอร์ออกจากแท็บ Folders ของรายการ PC (และไม่ติ๊ก Redirect folders) **ก่อนเชื่อมใหม่**
   2. Connect → บน VPS (Administrator): `PS> Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name fDisableCdm -Value 1` → ตัดการเชื่อม
   3. เชื่อมใหม่ → **T4:** `PS> net view \\tsclient` ไม่มี share และแท็บ Folders ของทุกรายการ PC ไม่มีโฟลเดอร์
   4. บน Mac รายการไฟล์ใต้ `data/transfer/` เท่ากับ manifest (ชื่อและ SHA-256) · พิมพ์ path แบบ `./<ไฟล์>` จึงไม่มีชื่อบัญชี (review F19):
      ```zsh
      % cd ~/Documents/GitHub/Sochron1k/data/transfer
      % /usr/bin/find . -type f ! -name .DS_Store -print0 | /usr/bin/xargs -0 /usr/bin/shasum -a 256
      ```
   5. `host_report.py` บน VPS เป็น PASS (ข้อ 6) → **ตัดการเชื่อม RDP** (กติกาบนหัวไฟล์) → envcheck บน Mac เป็น PASS (runbook ENV-002 ข้อ 3)
7. **ส่งให้ Claude:** วันที่, รายการไฟล์และ SHA-256, ผล T1–T4, ผลของตัวตรวจทั้งสอง

## สรุปสิ่งที่ส่งกลับ
| ขั้น | สิ่งที่ส่ง |
|---|---|
| 0 | ผู้ให้บริการ, แพ็กเกจ, ราคา, ผล CGNAT (ตรง/ไม่ตรง) |
| 1 | มีหรือไม่มี IPv6 สาธารณะ, ยืนยันว่าสร้างบัญชี admin ใหม่และปิดบัญชีเดิมแล้ว, คำยืนยัน C1 และ C2 หลังข้อ 1.2 และท้ายข้อ 1.3 พร้อมเวลา |
| 5 | `uv --version`, SHA-256 ของ uv, ผล `Select-String` สองบรรทัด |
| 6 | ชื่อ rule DHCP, รายงาน host_report รอบ PASS, ผล drift test, rule ที่ปิดหรือแก้ |
| 7 | บรรทัดของ `nc` ทุกบรรทัด (ข้อความและ exit status ของทุกพอร์ต, ปิดบังแล้ว), ผลของ hotspot, ผล IPv6 (หรือ "IPv6 ไม่ได้ทดสอบ"), rule ของผู้ให้บริการและหน้าของ VPS ที่แสดง rule ทุกชุด (ปิดบัง IP) |
| 8 | ผลทดสอบช่องทางไฟล์และ printer, ค่าของแท็บ Folders และ Devices & Audio ระหว่างทดสอบและหลังทดสอบ, `lpstat -p`, ค่า policy, `CurrentBuild` และ `UBR` |
| 9 | คำยืนยันของ checklist terminal |
