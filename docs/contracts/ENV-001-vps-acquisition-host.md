# TASK ENV-001 — Windows VPS เป็น acquisition/execution host: เช่า, ทำให้ปลอดภัย และพิสูจน์ว่าปิดช่องทางรั่ว

Version v1.2 (v1 ร่าง 2026-10-25 → v1.1 ตอบ `docs/reviews/ENV-contracts-r1.md`: ย้ายการวัดซ้ำไป SPIKE-002 (F2, F14, F19), firewall สองชั้น (F5), ช่องทางไฟล์ (F3, F4), API ของ host_report (F10), runbook (F15), แหล่งราคา (F16), ปิดบัง IP (F17), ความสอดคล้อง (F20) → v1.2 ตอบ `docs/reviews/ENV-contracts-r2.md`: schema ของ firewall rule (F21), `.env.example` (F22), ที่มาของแต่ละ fact (F23), AC-05 ไม่รอ SPIKE-002 (F24), uv ≥ 0.13.4 (F25), ค่าที่คาดของ uv/Python (F10), การโหลดสคริปต์ใน tests (F31), บันทึกผู้เขียน tests (F20)) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 6.1, 10 แถว 1c, 13a · Tier **High** · Branch `chore/ENV-001-vps-acquisition-host`
Status: **draft v1.2** (Claude ร่าง 2026-10-25 · รอ contract review r3 แล้วเจ้าของอนุมัติ: High และมีค่าใช้จ่าย จึงอนุมัติแทนไม่ได้)
Hypothesis (research tasks): ไม่ใช่งานวิจัย

**ด่าน ENV-1** = ENV-001 (contract นี้: VPS ปลอดภัย) → SPIKE-002 (`docs/contracts/SPIKE-002-vps-remeasure.md`: วัดซ้ำบน VPS แบบอ่านอย่างเดียว) → ENV-002 (`docs/contracts/ENV-002-research-host-separation.md`: แยก research host + sentinel) · SPIKE-002 เริ่มได้เมื่อ ENV-001 ผ่านครบทุก AC (AC-05 เป็น checklist ของเจ้าของ ไม่รอผลของ SPIKE-002) · terminal บนเครื่องเจ้าของอยู่จนกว่า VPS ผ่าน ENV-001 และ SPIKE-002 · ความหมายของ "ENV-1 ผ่าน" ลำดับการตัด holdout และช่องทางส่ง snapshot อยู่ใน D-021 (proposed)

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: **yes** — เพิ่มทางเข้าระยะไกล (RDP) ไปเครื่องที่จะถือ terminal, holdout และ Demo runner และเป็นฝั่งหนึ่งของขอบเขต research/holdout
- Q2 real money: no — ไม่มีเส้นทางส่งคำสั่งในงานนี้ (ค่าเช่า VPS อยู่ใน SPEC Q-10)
- Q3 new storage/transfer of personal or confidential data: **yes** — session ของบัญชีโบรกเกอร์อยู่บนเครื่องของผู้ให้บริการภายนอก
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: **yes (บางส่วน)** — ข้อผูกพันรายเดือนกับผู้ให้บริการ
- Q6 changes controls: no

**High** ตาม Q1, Q3 (architecture ข้อ 10 แถว 1c เขียน Standard ไว้ก่อน: งานนี้แก้แถวนั้นเป็น High)

## Goal / user outcome (Thai)
เจ้าของมี Windows VPS ของตัวเองที่:
- เข้าได้ทาง RDP จาก IP ของเจ้าของเท่านั้น โดยกั้นสองชั้น (firewall ของผู้ให้บริการ และ firewall ของ Windows) มี NLA และ lockout · พอร์ตอื่นปิดทั้งหมด พิสูจน์จากภายนอก
- คัดลอก**ไฟล์**จาก VPS มาเครื่องเจ้าของไม่ได้ (ปิด drive redirection, จำกัด clipboard เป็นข้อความ, ไม่มีโปรแกรม sync เช่น OneDrive) · ช่องทางเดียวที่ส่ง snapshot ก่อน cutoff มาได้คือขั้นตอนใน D-021 ที่เจ้าของทำเองแล้วตรวจซ้ำ
- มี MT5 terminal จากเว็บของ Exness ที่เจ้าของ login เองด้วยรหัสผ่านแบบ investor (อ่านอย่างเดียว) และมี Python ของโปรเจกต์กับสำเนา repo ที่ไม่มีสิทธิ์ push

## VPS ที่ต้องเช่า (คำแนะนำ)
| รายการ | ขั้นต่ำ (เกณฑ์ของ host_report) | แนะนำ | เหตุผล |
|---|---|---|---|
| ระบบปฏิบัติการ | Windows Server 2022 หรือ 2025, 64-bit, license รวมในราคา | **Windows Server 2025** | `MetaTrader5` มีแต่ wheel ของ Windows (D-001) · Server 2022 หมด mainstream support แล้ว 2026-10-13 (ได้ security update ถึง 2031-10) [1][2] |
| CPU | 2 vCPU | 2–4 vCPU ที่ความเร็วต่อ core สูง | baseline เป็น single-thread: ความเร็วต่อ core สำคัญกว่าจำนวน (≈ 1 ชั่วโมงต่อโครงสร้างบนเครื่องเจ้าของ, `docs/evidence/CORE-008.md`) |
| RAM | หน่วยความจำที่ Windows เห็น ≥ 3.5 GiB (= เครื่อง "4 GB") | **8 GB** | ประเมิน holdout ≈ 2 ปีของ M1 (≈ 0.63–0.7 ล้านแท่ง) เป็น object ของ Python ราว 0.5–1 GB [ประมาณ ยังไม่วัด] + terminal |
| Disk | SSD · พื้นที่ว่างบนไดรฟ์ของ repo ≥ 30 GB | SSD 80–100 GB | history ของ terminal (M1 ตั้งแต่ 2014), snapshot, environment, backup |
| เครือข่าย | IP คงที่ · ผู้ให้บริการมี firewall ที่จำกัด IP ต้นทางได้ | + VPN ของผู้ให้บริการ ถ้า IP บ้านอยู่หลัง CGNAT หรือเปลี่ยนบ่อย | กั้นชั้นนอก |
| ตำแหน่ง | ใดก็ได้ | ตัดสินอีกครั้งตอน E1 | R1 ไม่ขึ้นกับความหน่วง |
| ราคา [ประมาณ ต.ค. 2026, ตรวจราคาจริงก่อนเช่า] | – | 2 vCPU/4 GB ส่วนใหญ่ ≈ 25–40 USD/เดือนในหน้ารวมราคาของ VPS สำหรับ MT5 [3][4][5] · 8 GB พบตั้งแต่ ≈ 10 USD (3 vCPU, รวม Windows ตามหน้ารวมราคาหนึ่ง) ถึง ≈ 33 EUR (4 dedicated vCPU, รวม license) [6] | ราคาจากหน้ารวมราคาของบุคคลที่สาม ไม่ใช่หน้าสั่งซื้อ · นับใน SPEC Q-10 |

แหล่ง (ค้น 2026-10-25): [1] bleepingcomputer.com "Windows Server 2022 reached end of mainstream support" · [2] elevenforum.com "Windows Server 2022 reached end of mainstream support on October 13, 2026" · [3] forexvps.net/resources/best-mt5-vps-providers · [4] newyorkcityservers.com/compare/forexvps-net-alternatives · [5] go.lightnode.com/forex-vps · [6] vpssos.com "2026 VPS Price Comparison … 4 vCPU/8GB" และหน้ารวมราคา Windows VPS ของ itechguides.com

## Current behavior and evidence (revision)
`main` `a11bff7` · ยังไม่มี VPS · MT5 terminal อยู่บนเครื่องเจ้าของ (`C:\Program Files\MetaTrader 5` และ `%APPDATA%\MetaQuotes`; ตรวจแค่การมีอยู่) · repo `faztycoding/Sochron1k` เป็น public (GitHub REST API อ่านได้โดยไม่ login) จึง clone ผ่าน HTTPS ได้โดยไม่มี credential · uv บนเครื่องเจ้าของและ CI = 0.13.0 (D-013, มี advisory ที่แก้ใน 0.13.4 และมีงานติดตามให้ยกพร้อมกัน)

## Scope
- In scope: runbook `docs/runbooks/ENV-001-vps.md` · `scripts/env/host_report.py` (อ่านอย่างเดียว) + unit tests `tests/unit/env/**` · การทดสอบจากภายนอกและการทดสอบช่องทางไฟล์ (เจ้าของทำตาม runbook) · หลักฐาน · แก้แถว 1c ของ `docs/architecture.md` (tier High, ENV-1 = 3 contracts) · บันทึก uv บน VPS ใน `docs/tooling/registry.md`
- Exclusions: วัดซ้ำด้วย MetaTrader5 (SPIKE-002) · แยก research host (ENV-002) · ดึงข้อมูล, snapshot, ตัด holdout (contract ของ acquisition host หลัง ENV-1, D-021) · Demo runner, scheduler, backup (E1/OPS-1) · `data.acquire`, `broker`
- Allowed files/modules: `scripts/env/host_report.py`, `scripts/env/__init__.py` ถ้าจำเป็น, `tests/unit/env/**`, `docs/runbooks/ENV-001-vps.md`, `docs/evidence/ENV-001.md`, `docs/handoff/ENV-001.md`, `docs/architecture.md` (เฉพาะแถว 1c), `docs/tooling/registry.md` (แถว uv ของ VPS), `SPEC.md` (เฉพาะแถว Q-10 เมื่อเจ้าของให้ตัวเลขงบ), `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch D-006: `tests/acceptance/ENV-001/**`
- Must not touch: `src/sochron/**`, `pyproject.toml`, `uv.lock`, `.github/**`, `.claude/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `spikes/**`

## Inputs / outputs / errors (contract)
```text
scripts/env/host_report.py  (stdlib เท่านั้น · Windows-only import อยู่ใน collect_facts เท่านั้น ให้ import ได้บน Linux CI)
  ค่าคงที่ของโมดูล: EXPECTED_UV (รุ่นของ uv บน VPS ตามแถวใน docs/tooling/registry.md · ตั้งพร้อมแถวนั้น), EXPECTED_PYTHON = "3.12.15",
      ALLOWED_UDP = {68: "Core Networking - DHCP-In", 546: "Core Networking - DHCPv6-In"}, MIN_IPV4_PREFIX = 24, MIN_IPV6_PREFIX = 48
  Facts (frozen dataclass): os_caption: str | None, os_build: int | None, cpu_count: int | None, visible_ram_bytes: int | None,
      repo_drive_free_bytes: int | None, inbound_allow_rules: tuple[Rule, ...] | None,
      nla_required: bool | None, lockout_threshold: int | None, drive_redirection_disabled: bool | None,
      clipboard_files_to_client_blocked: bool | None, sync_clients: tuple[str, ...] | None,
      uv_version: str | None, python_version: str | None, project_synced: bool | None,
      git_credential_helpers: tuple[str, ...] | None, remote_has_userinfo: bool | None,
      secret_like_files_in_repo: int | None, holdout_dir_in_repo: bool | None
    Rule (frozen): name: str, protocol: str ("TCP", "UDP", "ICMPv4", "ICMPv6", "IGMP", "41", "Any", …), profiles: tuple[str, ...],
      local_ports: tuple[int | str, ...] | "Any"   (คำอย่าง "RPC", "IPHTTPSIn", "Teredo" เป็น str),
      remote_addresses: tuple[str, ...] | "Any"   (รายการตามที่ Windows คืน: CIDR, ช่วง "a-b", คำอย่าง "Internet", "LocalSubnet")
  collect_facts(repo: Path) -> Facts    # Windows เท่านั้น · ที่มาของแต่ละ fact (ตายตัว, อ่านอย่างเดียว, ไม่เปิด socket):
      os_*              winreg HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion (ProductName, CurrentBuildNumber)
      cpu_count         os.cpu_count()
      visible_ram_bytes ctypes kernel32.GlobalMemoryStatusEx (ullTotalPhys)
      repo_drive_free   shutil.disk_usage(repo)
      inbound rules     subprocess คำสั่งเดียว: PowerShell `Get-NetFirewallRule -Direction Inbound -Action Allow -Enabled True` ต่อกับ
                        `Get-NetFirewallPortFilter`/`Get-NetFirewallAddressFilter` ออกเป็น JSON (`ConvertTo-Json`) · ชื่อ field ไม่ขึ้นกับภาษาของระบบ
      nla_required      winreg HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp\UserAuthentication == 1
      lockout_threshold subprocess `net accounts` แล้วอ่านบรรทัด "Lockout threshold" (ระบบที่ไม่ใช่ภาษาอังกฤษ = None → UNKNOWN)
      drive_redirection winreg policy `fDisableCdm` == 1 (HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services หรือ RDP-Tcp)
      clipboard         winreg policy `fDisableClip` == 1 หรือ policy จำกัด clipboard จาก server ไป client เป็นข้อความ (ชื่อค่าตรวจตอน implement กับ
                        Server 2022/2025 และบันทึกใน handoff) · หาไม่ได้ = None
      sync_clients      Uninstall entries (winreg HKLM, HKCU, WOW6432Node) ที่ DisplayName มี OneDrive/Dropbox/Google Drive/iCloud
                        + โปรเซสที่รันอยู่ (ctypes CreateToolhelp32Snapshot/Process32FirstW/Process32NextW/CloseHandle)
      uv_version        subprocess `uv --version`
      python_version    subprocess `uv run --offline python -c "import platform; print(platform.python_version())"` ใน repo
      project_synced    subprocess `uv sync --locked --check --offline` ใน repo: exit 0 = True (ตรวจแล้วว่ามีใน uv 0.13.0 และไม่แก้ environment)
      git_credential    subprocess `git config --show-origin --get-all credential.helper` (ทุก scope) · ว่าง = ()
      remote_userinfo   อ่าน `<repo>/.git/config` แล้วตรวจว่า URL ของ remote มี "@" ก่อน host หรือไม่ (ไม่พิมพ์ URL)
      secret_like_files นับไฟล์ใต้ repo ที่ชื่อเป็น `.env` หรือ `.env.*` **ยกเว้น `.env.example`**, `*.key`, `*.pem`, `*.pfx`, `*.rdp` (ชื่อเท่านั้น ไม่เปิด)
      holdout_dir       มีโฟลเดอร์ชื่อ holdout (ไม่สนตัวพิมพ์) ใต้ repo
  evaluate(facts: Facts) -> Report         # pure · ใช้ทดสอบด้วย Facts ปลอมบน Linux
      Report: items: tuple[Item, ...], verdict    Item: name, status PASS|FAIL|UNKNOWN, detail
      ลำดับผลรวม: มี FAIL → FAIL · ไม่มี FAIL แต่มี UNKNOWN → UNKNOWN · ทุกข้อ PASS → PASS · ค่า None ของ fact = UNKNOWN ของ item นั้น
  Items และเกณฑ์:
      os                 Windows Server 2022 หรือ 2025 (build 20348 หรือ 26100)
      cpu                cpu_count ≥ 2
      ram                visible_ram_bytes ≥ 3.5 GiB
      disk               repo_drive_free_bytes ≥ 30 GB (10^9)
      inbound            ตัดสินเฉพาะ rule ที่ protocol เป็น TCP หรือ UDP (rule ของ ICMP, IGMP, IPv6 protocol 41 ไม่ตัดสิน)
                         · TCP: local_ports ต้องเป็น (3389,) เท่านั้น · UDP: (3389,) หรือพอร์ตเดียวใน ALLOWED_UDP ที่ชื่อ rule ตรงกับค่าใน ALLOWED_UDP
                         · local_ports เป็น "Any" หรือมีคำ (เช่น Teredo, IPHTTPSIn, RPC) = FAIL (เจ้าของปิด rule เช่น "Remote Desktop - Shadow (TCP-In)")
                         · rule ของ 3389 (TCP และ UDP): remote_addresses 1–4 รายการ แต่ละรายการเป็น host เดียว หรือ prefix IPv4 ≥ /24 หรือ IPv6 ≥ /48
                           · "Any", คำ (Internet, LocalSubnet, …) และช่วง "a-b" = FAIL
      nla                nla_required is True
      lockout            1 ≤ lockout_threshold ≤ 10
      drive_redirection  drive_redirection_disabled is True
      clipboard          clipboard_files_to_client_blocked is True
      sync_clients       sync_clients ว่าง
      python_env         uv_version == EXPECTED_UV, python_version == EXPECTED_PYTHON, project_synced is True
      git                git_credential_helpers ว่าง และ remote_has_userinfo is False
      secrets            secret_like_files_in_repo == 0
      holdout            holdout_dir_in_repo is False
  render(report) -> str                    # Markdown + บรรทัดสุดท้าย "HOST REPORT: PASS|FAIL|UNKNOWN" · ห้ามมี IPv4/IPv6 เต็ม
                                           # (แสดงจำนวนรายการและความยาว prefix ของ scope เท่านั้น)
  CLI: uv run --offline python scripts/env/host_report.py --role acquisition --repo <path>   (exit 0 เฉพาะ PASS)
  Tests โหลดสคริปต์ด้วย importlib.util.spec_from_file_location("host_report", <repo>/scripts/env/host_report.py) ทั้งใน
      tests/unit/env/ และ tests/acceptance/ENV-001/ (repo ไม่มี conftest และ pythonpath มีแค่ src)
```

## Invariants
- ไม่มีรหัสผ่าน, เลขบัญชีเต็ม, IP ของบ้านหรือของ VPS ใน repo, log หรือหลักฐาน · เจ้าของ login terminal ด้วยมือ (รหัส investor)
- `host_report.py` อ่านอย่างเดียว ไม่เปลี่ยนการตั้งค่า, ไม่เปิด socket, ไม่อ่านเนื้อหาไฟล์ credential, Credential Manager หรือโฟลเดอร์ของ terminal
- VPS ไม่มี credential ของ GitHub · repo บน VPS เป็น clone แบบ HTTPS ไม่ใส่ credential
- Claude ไม่เข้าถึง VPS · ทุกคำสั่งบน VPS และการทดสอบจากภายนอกเจ้าของเป็นผู้รันตาม runbook แล้วส่งผลกลับเป็นข้อความ (ไม่ส่งไฟล์)
- ไม่มีคำสั่งซื้อขาย และไม่มีโค้ดของงานนี้ที่ import `MetaTrader5`

## Negative cases
Windows client หรือ Server รุ่นเก่า · RAM ที่เห็นต่ำกว่า 3.5 GiB · ดิสก์ว่างต่ำกว่า 30 GB · rule ขาเข้าเปิดพอร์ตอื่น (เช่น 445, 5985) · RDP rule เป็น "Any" (ค่าตั้งต้นของ Windows), `0.0.0.0/0`, "Internet" หรือช่วงกว้าง · "Remote Desktop - Shadow (TCP-In)" เปิดอยู่ (พอร์ต Any) · rule ของ Core Networking (DHCP-In, DHCPv6-In, ICMPv6) เปิดอยู่ตามค่าตั้งต้น (ผ่าน) · `.env.example` ใต้ repo (ผ่าน) · NLA ปิด · ไม่มี lockout หรือ threshold > 10 · drive redirection เปิด · clipboard ส่งไฟล์ได้ · OneDrive รันอยู่ · uv/Python ไม่ตรงรุ่น หรือยังไม่ sync · credential.helper=manager (ค่าตั้งต้นของ Git for Windows) · remote URL มี userinfo · มีไฟล์ `.env` หรือ `.rdp` ใต้ repo · อ่านค่าใดไม่ได้ (UNKNOWN) · การทดสอบจากภายนอกเปิด 3389 ได้จากเครือข่ายที่ไม่อยู่ใน allowlist · IP บ้านอยู่หลัง CGNAT

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given VPS ที่เจ้าของตั้งตาม runbook When เจ้าของรัน `host_report.py --role acquisition` บน VPS Then ทุก item เป็น PASS ตามเกณฑ์ในหัวข้อ contract และบรรทัดสุดท้าย `HOST REPORT: PASS` โดยรายงานไม่มี IPv4 เต็ม
- AC-02 Given `Facts` ปลอมที่ผิดทีละ item (รวม: RDP scope "Any", `0.0.0.0/0`, "Internet", ช่วงกว้าง; rule Shadow พอร์ต Any; TCP 445; NLA ปิด; lockout 0; clipboard ส่งไฟล์ได้; OneDrive รัน; credential.helper=manager; ไฟล์ `.env` 1 ไฟล์; ค่า None) และ `Facts` ที่ถูกต้องรวม rule ของ Core Networking (DHCP-In, DHCPv6-In, ICMPv6) และ `.env.example` When `evaluate` และ `render` Then item ที่ผิดเป็น FAIL (หรือ UNKNOWN สำหรับ None) ตามลำดับผลรวม, Facts ที่ถูกต้องได้ PASS, ข้อความไม่มี IPv4/IPv6 เต็ม และ tests รันบน Linux ได้โดยไม่ import โมดูลของ Windows
- AC-03 Given VPS หลัง AC-01 When เจ้าของทดสอบจากภายนอกตาม runbook Then จากเครือข่ายที่ไม่อยู่ใน allowlist (เช่น hotspot มือถือ) `Test-NetConnection <vps> -Port 3389` ล้ม · จาก IP ของเจ้าของ 3389 เปิด และ 22, 80, 443, 445, 5985, 5986 ล้มทั้งหมด · รายการ rule ของ firewall ผู้ให้บริการ (ปิดบัง IP) และผลเทียบ IP ของ router กับ IP สาธารณะ (ตรวจ CGNAT) อยู่ในหลักฐาน · ถ้าเป็น CGNAT ใช้ทางเลือก VPN แล้วทดสอบซ้ำ
- AC-04 Given RDP session ปกติ When เจ้าของคัดลอกไฟล์ทดสอบใน Explorer ของ VPS แล้ววางบนเครื่องตัวเอง และเปิด `\\tsclient` บน VPS Then วางไฟล์ไม่ได้ (ข้อความยังคัดลอกได้) และ `\\tsclient` ใช้ไม่ได้ · runbook มีขั้นตอนส่ง snapshot ตาม D-021 พร้อมการรัน `host_report.py` และตัวตรวจของ ENV-002 ซ้ำหลังส่งทุกครั้ง
- AC-05 Given terminal บน VPS When เจ้าของทำ checklist ของ runbook Then หลักฐานบันทึกคำยืนยันของเจ้าของทีละข้อ: ติดตั้งจากเว็บของ Exness, login ด้วยรหัส investor, Max bars ตั้งเป็น Unlimited, `w32tm /resync` สำเร็จ, uv และ Python ติดตั้งแบบออนไลน์แล้ว `uv sync --locked` ก่อนคำสั่ง offline ใดๆ (การพิสูจน์ด้วยระบบว่า `trade_allowed` เป็น false อยู่ใน SPIKE-002 AC-02 ไม่ใช่เงื่อนไขของ AC นี้)
- AC-06 Given หลักฐานทั้งหมดของงาน When ค้นด้วย `\b[0-9]{7,}\b` และ `\b(?:\d{1,3}\.){3}\d{1,3}\b` Then ทุก hit ถูกตรวจว่าไม่ใช่เลขบัญชีหรือ IP เต็ม (รายการ hit และเหตุผลอยู่ในหลักฐาน) และไม่มีรหัสผ่าน
- AC-07 Given ทั้งงาน When `bash scripts/controls/red-flags.sh main` และ `uv run --offline pytest tests -q -p no:cacheprovider` Then กลุ่ม "Order or account mutation surface" ว่าง, suite ผ่าน skipped 0 และ CI เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01 | เจ้าของ (บน VPS) + Claude อ่านรายงาน | runbook "ตรวจเครื่อง" → `docs/evidence/ENV-001.md` | L4 |
| 02 | ผู้เขียน tests (Codex หลัง 2026-10-28 19:41 ถ้าใช้ได้ ไม่เช่นนั้น Claude session ใหม่ตามการสลับบทบาท) | `uv run --offline pytest tests/acceptance/ENV-001 tests/unit/env -q -p no:cacheprovider` | L2 |
| 03, 04 | เจ้าของ (break-it จากภายนอก) + ผู้ตรวจ | runbook "ทดสอบจากภายนอก", "ทดสอบช่องทางไฟล์" → ผลคำสั่งและเวลาในหลักฐาน | L4 |
| 05 | เจ้าของ | runbook checklist (คำยืนยันทีละข้อพร้อมเวลา) | L4 (คำยืนยันของเจ้าของ) |
| 06 | Claude + ผู้ตรวจ | grep ตามรูปแบบใน AC-06 | L3 |
| 07 | Claude + CI | red-flags + suite + run ของ PR | L2/L3 |

## Risk, data and external side effects
**Threat model ย่อ (High):**
| ภัย | ทางเข้า | การป้องกัน | ที่เหลือ |
|---|---|---|---|
| คนนอกเข้า VPS | RDP จากอินเทอร์เน็ต | firewall ผู้ให้บริการ + rule ของ Windows จำกัด IP (สองชั้น), NLA, lockout, รหัสผ่านยาวไม่ซ้ำ, Windows Update, MFA ที่ console ของผู้ให้บริการถ้ามี · ทดสอบจากภายนอก (AC-03) | CGNAT ทำให้ "IP ของเจ้าของ" มีคนอื่นใช้ร่วม → ใช้ VPN · Demo ไม่มีเงินจริง แต่เครื่องนี้จะเป็น Demo runner ต่อ |
| ไฟล์ข้อมูลจาก VPS ถูกคัดลอกมาเครื่องวิจัย | drive redirection, clipboard แบบไฟล์, โปรแกรม sync, share | ปิด drive redirection, clipboard ข้อความเท่านั้น, ไม่มี sync client, ไม่มี share (AC-01, AC-04) · ช่องทางเดียวคือขั้นตอนของ D-021 แล้วตรวจซ้ำ | ข้อความผ่าน clipboard ตรวจไม่ได้ · การพิมพ์ตัวเลขด้วยมือ |
| credential รั่ว | log, หลักฐาน, config, ผู้ให้บริการเห็นเครื่อง | login ด้วยมือด้วยรหัส investor, ไม่มีรหัสใน repo, ปิดบังเลขบัญชีและ IP (AC-06) | ผู้ให้บริการ VPS เข้าถึงเครื่องได้ในทางเทคนิค (ยอมรับ: Demo, ข้อมูลราคาเป็นของโบรกเกอร์) |
| VPS push โค้ด | git credential | ไม่มี credential.helper, clone ไม่มี userinfo (AC-01) | – |

- ผลภายนอก: ค่าเช่ารายเดือน · โบรกเกอร์อาจแจ้งเตือนการ login จากที่ใหม่ · ไม่มีคำสั่งซื้อขาย · ผู้อนุญาต: เจ้าของ

## Plan, dependencies and unknowns (P06)
1. Understanding: เช่า VPS แล้วทำให้เป็นเครื่องที่ปลอดภัยพอถือ terminal/holdout/runner และพิสูจน์จากภายนอกว่าเข้าได้แค่ RDP จากเจ้าของและส่งไฟล์ออกมาไม่ได้ · เข้าใจผิดที่เป็นไปได้: ใช้ MQL5 virtual hosting (รันได้แค่โปรแกรม MQL ไม่ใช่ Python) · ตั้ง allowlist ที่ผู้ให้บริการอย่างเดียวแล้วคิดว่า Windows เห็น (ไม่เห็น: ต้องสองชั้น) · ปล่อย clipboard เปิดเพราะคิดว่าส่งได้แค่ข้อความ (ส่งไฟล์ได้)
2. Files / reuse: รูปแบบหลักฐานของ SPIKE-001 · ใหม่: `scripts/env/host_report.py`, runbook
3. Steps: (1) contract review r3 → เจ้าของอนุมัติ + งบ (Q-10) + D-021 (2) บันทึกผู้เขียน tests และผู้ตรวจ (Codex หรือ Claude session ใหม่) ใน PROGRESS → ผู้เขียน tests เขียน acceptance ของ AC-02 ผ่าน patch → review → red (3) Claude เขียน `host_report.py` + unit tests + runbook (4) เจ้าของเช่าและตั้ง VPS ตาม runbook (5) เจ้าของรัน host_report, ทดสอบจากภายนอก, ทดสอบช่องทางไฟล์, checklist ของ terminal แล้วส่งผลกลับ (6) หลักฐาน → ผู้ตรวจ session ใหม่ → PR · แล้ว SPIKE-002
4. Risks: ชื่อ policy ของ clipboard ต่างตามรุ่น Windows (runbook ให้ทั้งทาง "ปิด clipboard ทั้งหมด" และ "จำกัดเป็นข้อความ") · ราคาเปลี่ยน · `netsh` แสดงผลตามภาษาของระบบ (ให้ใช้ PowerShell `Get-NetFirewallRule`/`Get-NetFirewallAddressFilter` ซึ่งคืนชื่อ field คงที่)
5. Decisions needed from the owner:
   - (ก) อนุมัติ contract นี้ (High) และงบรายเดือนใน Q-10 · **แนะนำ:** Windows Server 2025, 2–4 vCPU, 8 GB, SSD 80–100 GB, รายเดือน
   - (ข) วิธีกั้น RDP ชั้นนอก · **แนะนำ:** allowlist IP ที่ firewall ของผู้ให้บริการ (ถ้า IP บ้านเป็น CGNAT หรือเปลี่ยนบ่อย ใช้ VPN ของผู้ให้บริการ) + rule ของ Windows จำกัด IP เดียวกันเสมอ
   - (ค) clipboard · **แนะนำ:** ปิด clipboard redirection ทั้งหมดถ้าไม่จำเป็น ไม่เช่นนั้นจำกัด server→client เป็นข้อความ (ต้องใช้คัดลอกรายงานกลับมา: ส่งเป็นข้อความได้)
   - (ง) uv บน VPS · **แนะนำ:** uv **≥ 0.13.4** ตั้งแต่วันแรก (รุ่นล่าสุดที่ ≥ 0.13.4 ในวันติดตั้ง จากตัวติดตั้งทางการของ Astral) บันทึกรุ่นและ SHA-256 ของไฟล์ใน `docs/tooling/registry.md` และตั้ง `EXPECTED_UV` ตามนั้น · ไม่ใช้ 0.13.0 บน VPS เพราะเหตุผลที่ D-013 รับ advisory ไว้ (ทุกการดาวน์โหลดตรวจ hash ที่ตรึง) ไม่ครอบคำสั่ง `uv run --with` ของ SPIKE-002 ซึ่งไม่มี lockfile (review r2 F25) · `uv sync --locked` บน VPS ล้มดังๆ ถ้า lock ไม่เข้ากับ uv รุ่นนั้น · การยกเครื่องเจ้าของและ CI ยังเป็นงานติดตามของ D-013
   - (จ) D-021 (ENV-1 ผ่านได้ก่อนมี holdout, ลำดับการตัด, ช่องทางส่ง snapshot)

## Authorization (filled by the owner)
| รายการ | ค่า |
|---|---|
| actor | เจ้าของ (เช่า, ตั้งค่า, login terminal, รันทุกคำสั่งบน VPS และการทดสอบจากภายนอก) · Claude (เขียนสคริปต์และ runbook บนเครื่องเจ้าของ) |
| action | ตั้งค่าและตรวจเครื่อง · ไม่มีการเชื่อมต่อด้วย MetaTrader5 ในงานนี้ · ไม่มีคำสั่งซื้อขาย |
| target | VPS ที่เจ้าของเช่า |
| valid until | TBD (เจ้าของกรอก) |

## Budget
2–3 sessions ของ Claude · เวลาเจ้าของตั้ง VPS และทดสอบ ≈ 2 ชั่วโมง · headless session ไม่เกิน 4 (ผู้เขียน tests, ผู้ตรวจ tests, ผู้ตรวจงาน, สำรอง) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่ · ค่า VPS ตาม Q-10

## Recovery, compensation and checkpoint
ยกเลิกหรือ rebuild VPS ที่ผู้ให้บริการ · ถ้ารหัส RDP หรือบัญชีรั่ว: เปลี่ยนรหัสผ่านของบัญชี Demo ที่ Exness, rebuild VPS, บันทึกใน `docs/failures/` · terminal บนเครื่องเจ้าของยังอยู่จนกว่า ENV-002

## DoR status / missing items / next action
ขาด: contract review r3, การตัดสินของเจ้าของ (ก)–(จ), valid until · next: review r3 → เจ้าของ

## Done scope
operation: VPS ปลอดภัยและพิสูจน์แล้ว (ยังไม่มีการวัดด้วย MetaTrader5, ข้อมูลวิจัย หรือ holdout บนเครื่อง)
