# Runbook ENV-002: ทำ Mac ให้เป็น research host และสร้าง sentinel บน VPS (ฉบับ macOS)

Contract: `docs/contracts/ENV-002-research-host-separation.md` v2.6 (อนุมัติ 2026-11-18) และ D-023 · ผู้ทำ: เจ้าของ · ใช้เวลา ≈ 90 นาที · **ทำหลัง ENV-001 และ SPIKE-002 ผ่านแล้วเท่านั้น** · ฉบับ Windows (v1.9) อยู่ใน history ของ git ที่ `c97aac6` · ขั้นของเครื่อง Windows เดิมอยู่ในข้อ 7 ท้ายไฟล์

ลำดับ: ข้อ 1 (VPS) → Claude commit ค่า sentinel แล้วส่ง hash 40 ตัวให้คุณ → ข้อ 2 (เตรียม Mac) → ข้อ 3 (AC-01) → ข้อ 4 (AC-03 จาก Mac) → ข้อ 5 (VPS) → ข้อ 7 (เครื่อง Windows เดิม)

กติกาตลอดทั้ง runbook:
- **ก่อนเปิด RDP หรือ console ของผู้ให้บริการทุกครั้ง** (C9): Quit (⌘Q) Visual Studio Code, Claude, ChatGPT/Codex และทุกแอปที่ agent รันอยู่ (บน macOS การปิดหน้าต่างไม่ได้ปิดแอป) แล้วรันใน Terminal.app: `/usr/bin/pgrep -ilf 'claude|codex|chatgpt'` ต้องไม่พิมพ์อะไร
- ส่งผลกลับเป็น**ข้อความ** และปิดบัง IP ทุกครั้ง (`x.x.x.x`) · **ห้ามคัดลอกไฟล์ sentinel มา Mac** คัดลอกได้แค่ข้อความที่สคริปต์พิมพ์
- Keychain, แอป Passwords และรายการ Credentials ของ Windows App: **คุณตรวจเองเท่านั้น** (agent ห้ามอ่าน) และส่งแค่คำยืนยัน
- ห้ามติดตั้ง MT5, Wine หรือแพ็กเกจ `MetaTrader5` บน Mac ไม่ว่าด้วยเหตุใด
- คำสั่งที่ขึ้นต้นด้วย `PS>` รันใน PowerShell (VPS หรือเครื่อง Windows เดิม) · ที่ขึ้นต้นด้วย `%` รันใน zsh บน Mac · ไม่ต้องพิมพ์ `PS>` หรือ `%`

## 1. สร้าง sentinel บน VPS (PowerShell ธรรมดา บน VPS)
1. ดึง commit ที่ตรวจแล้วจาก Claude (สคริปต์ยังไม่อยู่ใน `main` จนกว่าจะ merge):
   ```powershell
   PS> cd C:\Sochron1k
   PS> git fetch origin chore/ENV-002-macos-research-host
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
4. **ส่งให้ Claude:** ข้อความ JSON ที่สคริปต์พิมพ์ทั้งก้อน (ค่า token ส่งได้ครั้งนี้ครั้งเดียว เพราะต้อง commit ไว้ใน `docs/evidence/ENV-002-sentinel.json` ไฟล์เดียว) และผลของ `Get-FileHash` · ช่องทาง: คัดลอกเป็น**ข้อความ**ผ่าน clipboard แบบข้อความที่ ENV-001 เปิดไว้ หรือพิมพ์เอง (ไม่คัดลอกไฟล์) · Claude commit ค่าแล้วส่ง hash 40 ตัวของ commit ใหม่ให้คุณ

## 2. เตรียม Mac (ทำครั้งแรก แล้วทวนก่อนทุกรอบของข้อ 3)
1. **สิทธิ์ Privacy (decision (ช))**: System Settings → Privacy & Security → Files and Folders → Visual Studio Code: เปิดเฉพาะ Desktop Folder, Documents Folder, Downloads Folder และ iCloud Drive · Full Disk Access: Visual Studio Code ต้องปิดหรือไม่อยู่ในรายการ · คำถามสิทธิ์อื่นที่ macOS ถามระหว่างรัน (เช่น Photos, Music, Contacts, Network Volumes) ให้ตอบไม่อนุญาต
2. **iCloud Desktop & Documents (F21)**: repo อยู่ใต้ `~/Documents` · System Settings → Apple Account → iCloud → Drive: ต้องปิด "Desktop & Documents Folders" (agent อ่านค่านี้ไม่ได้: ยืนยันพร้อมเวลา) · ถ้าเปิดอยู่ repo, `.venv` และ snapshot ใน `data/transfer/` จะ sync ขึ้น iCloud และ envcheck จะเป็น UNKNOWN เมื่อไฟล์ถูกย้ายออกจากเครื่อง
3. **โฟลเดอร์ cloud ต้องอยู่ในเครื่องครบ (F6)**: ปิด "Optimize Mac Storage" ในหน้าเดียวกัน หรือใน Finder คลิกขวาที่ iCloud Drive → Keep Downloaded (หรือ Download Now) · ถ้ามีโฟลเดอร์ใน `~/Library/CloudStorage` (OneDrive, Google Drive, Dropbox) ตั้ง "Always Keep on This Device" ด้วย · โฟลเดอร์ที่ยังเป็น dataless ทำให้ `sentinel` เป็น UNKNOWN
4. **ไม่มี volume อื่น (F15, F19)**: ก่อนรัน envcheck ทุกครั้ง Eject external disk, disk image และ network volume ทุกตัว (รวม Time Machine ผ่านเครือข่าย) · `% /sbin/mount` ต้องมีแต่จุด mount `/`, `/dev` และ path ใต้ `/System/Volumes/` โดยใต้ `/System/Volumes/Data/` มีได้แค่ `Data` เองและ `Data/home` · วัด 2026-11-18: เครื่องนี้มี 12 mount ชนิด `apfs`, `devfs`, `autofs` ตามกฎนี้
5. **ล้าง Trash** ก่อนรัน (Finder → Empty Trash): terminal หรือสำเนา sentinel ใน Trash ตรวจไม่เจอ
6. ไม่ต้องลบอะไรเกี่ยวกับ MT5 บน Mac ถ้าไม่เคยติดตั้ง (และห้ามติดตั้ง) · envcheck ดูแอป MetaTrader, โฟลเดอร์ใน Application Support, Wine prefix, `terminal64.exe` ใต้ home และโปรเซสที่รันอยู่ให้ในข้อ 3

## 3. ตรวจ Mac (AC-01, ใน terminal ของ Visual Studio Code)
**3.1 ดึง commit ที่ Claude ให้** (terminal ปกติของ VS Code):
```zsh
% cd ~/Documents/GitHub/Sochron1k
% /usr/bin/git fetch origin chore/ENV-002-macos-research-host
% /usr/bin/git switch --detach <hash 40 ตัวที่ Claude ให้>
% /usr/bin/git status --short
```
`git status --short` ต้องไม่พิมพ์อะไร · แล้ว**ปิด session ของ agent ทั้งหมด** (r3 F20): Quit (⌘Q) Visual Studio Code, Claude, ChatGPT/Codex และ terminal ทุกหน้าต่างที่มี Claude Code หรือ Codex แบบ command line → เปิด Visual Studio Code ใหม่**โดยไม่เปิด panel ของ agent** (รอบนี้รันใน terminal ของ VS Code ซึ่งเป็นแอปเดียวกับที่ R1 จะรัน) → ใน terminal ของ VS Code:
```zsh
% /usr/bin/pgrep -ilf 'claude|codex|chatgpt'; echo "exit $?"
```
ต้องไม่พิมพ์บรรทัดของโปรเซส (`exit 1`) · วางผลนี้ในหลักฐาน · ถ้ามีบรรทัดขึ้น: ปิดโปรเซสนั้นแล้วรันใหม่ · ถ้าบรรทัดที่เหลือเป็นของ VS Code เองไม่ใช่ session ของ agent ให้ส่งบรรทัดนั้นให้ Claude ตัดสินก่อนเริ่มขั้น (0) · (r4 F24) หลังได้คำตัดสิน: Quit แอปที่ใช้ถาม Claude แล้วรัน `pgrep` เดิมอีกครั้ง · ยอมได้เฉพาะบรรทัดที่ Claude ยอมรับ · วางผลทั้งสองรอบและคำตัดสินในหลักฐาน

**3.2 ขั้น (0)–(7)**: ทำต่อกันทันทีตามลำดับ ในโฟลเดอร์ของ repo · วางทุกคำสั่งและผลลงในหลักฐาน (ส่งให้ Claude เป็นข้อความ) · **ขอบเขต:** ขั้นเหล่านี้จับไฟล์ที่ค้างอยู่ สภาพที่ผิดโดยไม่ตั้งใจ และทุกเส้นทางที่เขียนชื่อไว้ แต่รันด้วยบัญชี macOS เดียวกับ agent จึงไม่กันโปรเซสของบัญชีนี้ที่ตั้งใจเตรียมรอบนี้ไว้ล่วงหน้า (contract (ญ) ข้อ 16 ที่คุณรับไว้)

(0) shell ที่สะอาด (ไม่สืบทอดตัวแปรใด และไม่อ่านไฟล์เริ่มต้นของ zsh):
```zsh
% /usr/bin/env -i HOME="$HOME" TERM="$TERM" /bin/zsh -f
% cd ~/Documents/GitHub/Sochron1k
```
ตั้งแต่ขั้นนี้ใช้ path เต็มของเครื่องมือทุกตัวตามที่เขียนไว้ และ uv ใช้ `~/.local/bin/uv` หลังผ่านขั้น (1)

(1) ตรวจตัว uv กับไฟล์ทางการ:
```zsh
% cd "$(/usr/bin/mktemp -d)"
% /usr/bin/curl -LsSfO https://github.com/astral-sh/uv/releases/download/0.13.5/uv-aarch64-apple-darwin.tar.gz
% /usr/bin/curl -LsSfO https://github.com/astral-sh/uv/releases/download/0.13.5/uv-aarch64-apple-darwin.tar.gz.sha256
% /usr/bin/shasum -a 256 -c uv-aarch64-apple-darwin.tar.gz.sha256
% /usr/bin/tar -xzf uv-aarch64-apple-darwin.tar.gz
% /usr/bin/shasum -a 256 uv-aarch64-apple-darwin/uv ~/.local/bin/uv
% cd ~/Documents/GitHub/Sochron1k
```
`shasum -c` ต้องได้ `OK` · สองบรรทัดของ `shasum` ตัวสุดท้ายต้องเป็นค่าเดียวกัน (วัด 2026-11-18: `7dad6047…2338`) · ไม่เท่า = หยุดแล้วบอก Claude

(2) ลง interpreter ใหม่ทั้งโฟลเดอร์และสร้าง `.venv` ใหม่:
```zsh
% /bin/rm -rf ~/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none
% ~/.local/bin/uv python install --compile-bytecode 3.12.15
% /bin/rm -rf .venv
% ~/.local/bin/uv sync --locked --no-cache --python ~/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/bin/python3.12
```
ถ้า `uv sync` บอกว่า lockfile ต้องเปลี่ยน = หยุดแล้วบอก Claude (ห้ามแก้ `uv.lock`)

(3) ลบ bytecode และ cache นอก `.venv`:
```zsh
% /usr/bin/find . -path ./.venv -prune -o \( -name __pycache__ -o -name .mypy_cache \) -type d -exec /bin/rm -rf {} +
% /usr/bin/find . -path ./.venv -prune -o -name '*.py[co]' -type f -exec /bin/rm -f {} +
```

(4) state ของ git ต้องไม่ซ่อนการแก้ไฟล์:
```zsh
% /usr/bin/git ls-files -v | /usr/bin/grep -v '^H '
% /usr/bin/git config --show-origin --get-regexp '^core\.(fsmonitor|ignorestat)$'
% /usr/bin/git replace -l
% GIT_INDEX_FILE=/tmp/sochron-check.idx /usr/bin/git --no-replace-objects read-tree HEAD
% GIT_INDEX_FILE=/tmp/sochron-check.idx /usr/bin/git --no-replace-objects update-index --refresh; echo "exit $?"
% /bin/rm -f /tmp/sochron-check.idx
% /usr/bin/git rev-parse HEAD
% /usr/bin/git ls-files | /usr/bin/git check-attr --stdin filter | /usr/bin/grep -v ': filter: unspecified$'
% /usr/bin/git config --get-regexp '^(core\.(worktree|attributesfile)|include\..*|includeif\..*)$'
% /usr/bin/git config --list --name-only --show-origin --show-scope
```
- คำสั่งที่ 1, 2, 3, 8 และ 9 ต้องไม่พิมพ์อะไร
- `update-index --refresh` ต้องไม่พิมพ์อะไรและได้ `exit 0` (บรรทัด `<path>: needs update` = ไฟล์นั้นต่างจาก HEAD: หยุดแล้วบอก Claude)
- `git rev-parse HEAD` ต้องเป็น hash **40 ตัวเต็ม**ตัวเดียวกับที่ Claude ให้ (r7 F66)
- คำสั่งสุดท้ายพิมพ์แค่ชื่อ key และที่มา ไม่พิมพ์ค่า (r7 F67) จึงวางทั้งหมดในหลักฐานได้

(5) ไฟล์โค้ดที่ git ignore หรือไม่ track:
```zsh
% /usr/bin/git status --short --ignored --untracked-files=all -- . ':(exclude).venv'
% /usr/bin/git status --short --ignored --untracked-files=all -- . ':(exclude).venv' | /usr/bin/grep -E '\.(py|pyc|pyo|pth|so|dylib)$|__pycache__'
```
คำสั่งที่สองต้องไม่พิมพ์อะไร · วางผลของคำสั่งแรกทั้งหมดในหลักฐาน

(6) บันทึก manifest (R1 เทียบสามค่านี้ทุกครั้ง):
```zsh
% /usr/bin/find ~/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none -type f -print0 | /usr/bin/sort -z | /usr/bin/xargs -0 /usr/bin/shasum -a 256 | /usr/bin/shasum -a 256
% /usr/bin/shasum -a 256 ~/.local/bin/uv
% /usr/bin/grep '^home' .venv/pyvenv.cfg
```
บรรทัด `home` ต้องชี้ `…/cpython-3.12.15-macos-aarch64-none/bin`

(7) รอบควบคุมแล้วรอบ PASS ใน shell เดียวกัน · คำสั่งตรวจ (ใช้ซ้ำทั้งสองรอบ):
```zsh
% /sbin/mount
% PYTHONPATH=src PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 ~/.local/bin/uv run --offline python -m sochron.app.envcheck --role research --sentinel-file docs/evidence/ENV-002-sentinel.json; echo "exit status: $?"
```
**รอบควบคุม** (สร้างโฟลเดอร์เปล่าสองตัว: ไม่ใช่การติดตั้ง):
```zsh
% /bin/ls -d ~/Applications
% /bin/mkdir -p ~/Applications/"MetaTrader 5.app"
% /bin/mkdir ~/Library/"Application Support"/net.metaquotes.wine.metatrader5
```
แล้วรันคำสั่งตรวจ → `terminal_install` และ `terminal_data` ต้องเป็น FAIL และ `exit status` ต้องไม่ใช่ 0 · จากนั้นลบด้วย `rmdir` (ไม่ลากลง Trash) และตรวจว่าไม่มีแล้ว:
```zsh
% /bin/rmdir ~/Applications/"MetaTrader 5.app" ~/Library/"Application Support"/net.metaquotes.wine.metatrader5
% /bin/ls -d ~/Applications/"MetaTrader 5.app" ~/Library/"Application Support"/net.metaquotes.wine.metatrader5
```
`ls -d` ต้องบอก `No such file or directory` ทั้งสองตัว · ถ้า `ls -d ~/Applications` ตอนแรกบอกว่าไม่มีโฟลเดอร์นี้ ให้ `/bin/rmdir ~/Applications` ด้วย

**รอบ PASS**: รันคำสั่งตรวจอีกครั้ง ผลที่ต้องได้ (AC-01):
- ทุก item เป็น PASS · บรรทัดแรก `reader: darwin` · `home=` ในบรรทัด `roots:` คือ home ของคุณเอง · บรรทัดสุดท้ายของรายงาน `RESEARCH HOST: PASS` และ `exit status: 0`
- บรรทัด `processes:` มี `paths read` มากกว่า 0 · ชนิดในบรรทัด `mounts:` ตรงกับผลของ `/sbin/mount` รอบเดียวกัน
- บรรทัดอื่นที่คาดบนเครื่องนี้ (Claude วัด 2026-11-18 โดยไม่ใส่ sentinel): `mounts: 12 (apfs, devfs, autofs)`, `wine: 0 prefixes; looked at none`, `skipped: 2 folders (~/.Trash, ~/Pictures/Photos Library.photoslibrary)`, `apps: none`, `tools: .colima, .docker` · บรรทัด `apps:`, `tools:` และ `wine:` ที่ได้จริงเป็นค่าที่ commit ในหลักฐาน และ R1 จะเทียบกับค่านี้ทุกครั้ง
- (F20) `mt5_package: PASS` และส่วน vault path ของ `sentinel` ไม่นับเป็นหลักฐานบน Mac (ล้มไม่ได้บน macOS) · หลักฐานคือ item ที่เหลือและรอบควบคุม
- detail ของ item ใช้ถ้อยคำเดิมของ v1.9 (เช่น `no %APPDATA%\MetaQuotes`, `Uninstall entry`, `remote drive`): บน Mac หมายถึงชื่อใน `~/Library/Application Support`, (ไม่มีกฎ Uninstall) และ mount ตามลำดับ
- ถ้าคุณรับไฟล์ snapshot ไว้นอก `data/` ให้เพิ่ม `--data-dir <โฟลเดอร์>` **เฉพาะโฟลเดอร์ข้อมูลนั้นเอง ห้ามใส่โฟลเดอร์ที่ครอบ repo ไว้**

**ชื่อบัญชีในหลักฐาน (r3 F21):** ส่งผลของข้อ 3 ให้ Claude ตามที่เห็นได้ · ก่อน commit หลักฐาน Claude แทน `/Users/<ชื่อบัญชี>` ด้วย `/Users/<owner>` ทุกที่ (รอบควบคุม, ขั้น (1)–(6), detail ของ item) **ยกเว้นบรรทัด `roots:`** ซึ่ง contract ยอมให้มีชื่อบัญชี (คำตัดสินข้อ 8, r3 F41) · (r4 F25) บรรทัด `home` ของ `.venv/pyvenv.cfg` จากขั้น (6) ถูกปิดบังด้วย: ตัวเปิดของ R1 (SLICE-R1) ต้องเทียบหลังแทนชื่อบัญชีแบบเดียวกัน (งานที่ส่งต่อใน `docs/handoff/ENV-002.md`)

ถ้าได้ FAIL หรือ UNKNOWN: แก้ตามข้อความของ item นั้นแล้วรันขั้น (7) ใหม่ (ถ้าแก้ไฟล์ใน repo หรือ uv ให้เริ่มใหม่จากขั้น (0)) · `could not be listed` หรือ `dataless` → ข้อ 2.1 หรือ 2.3 · `not allowed:` ในบรรทัด `mounts:` → ข้อ 2.4 · `processes: unreadable (DYLD_ variables set)` → shell ไม่ได้เริ่มตามขั้น (0) · ส่งชื่อให้ Claude ถ้าไม่แน่ใจ

## 4. Break-it test จาก Mac (AC-03 ข้อ 1–4 และ 6; ทำตามกติกา C9 ก่อน)
Quit แอปของ agent ตาม C9 แล้วรันใน **Terminal.app**:
```zsh
% /usr/bin/nc -vz -G 5 <IP ของ VPS> 3389; echo "exit $?"
% for p in 22 80 139 443 445 5985 5986; do /usr/bin/nc -vz -G 5 <IP ของ VPS> $p; echo "port $p exit $?"; done
% /usr/bin/nc -vz -G 5 <IP ของ VPS> 3389; echo "exit $?"
% /usr/bin/smbutil view -g -N //<IP ของ VPS>; echo "exit $?"
% /sbin/mount | /usr/bin/grep smbfs
```
ผลที่ถูก:
1. **ตัวควบคุม**: 3389 สำเร็จ (`exit 0`) ทั้งบรรทัดแรกและบรรทัดหลังพอร์ตสุดท้าย (IP ถูกและ Mac ออนไลน์ทั้งก่อนและหลัง) · ถ้าตัวหลังล้ม ผลของรอบนั้นไม่มีผล ให้ทำซ้ำ (กติกาเดียวกับ ENV-001 v2.2)
2. พอร์ต 22, 80, 139, 443, 445, 5985, 5986 **ล้มทั้งหมด** · ที่คาดคือ `Operation timed out` · `Connection refused` ต้องมีคำอธิบายจากฝั่ง ENV-001 · ข้อความอื่นไม่ใช่ผล ให้ทำซ้ำ · บันทึกข้อความและ `exit` ของทุกพอร์ต
3. `smbutil view` **ล้ม** (`-g -N` = guest และไม่ถามรหัส จึงไม่มีอะไรถูกบันทึกลง Keychain · ห้ามใช้ Connect to Server ของ Finder) · วางข้อความที่พิมพ์ทั้งหมด · `grep smbfs` ต้องไม่พิมพ์อะไร · flag มาจาก `man smbutil` บน Mac เครื่องนี้และยังไม่เคยรันกับ server จริง: ถ้าผลดูแปลก ส่งให้ Claude ตามที่เห็น
4. **Checklist "credential และ session บน Mac"**: คุณทำเองทุกข้อ (agent ห้ามทำ) แล้วยืนยันทีละข้อพร้อมเวลา:
   - C1 Windows App → Settings → Credentials ไม่มีรายการของ VPS และรายการ PC ไม่ผูก credential
   - C2 แอป Passwords และ Keychain Access (keychain `login`): ค้น `com.microsoft.rdc.macos`, `Windows App`, `Remote Desktop`, IP ของ VPS, ชื่อผู้ใช้ RDP และโดเมนของผู้ให้บริการ → ไม่พบรายการของ VPS (รวมรายการที่ sync มาจากอุปกรณ์อื่น)
   - C3 Windows App → Settings → General ช่อง "If folder redirection is enabled for RDP files or managed resources, redirect:" ไม่ได้เลือกโฟลเดอร์ · ทุกรายการ PC ของ VPS (รวมรายการที่ Duplicate) → Edit: แท็บ Folders ไม่ติ๊ก Redirect folders, แท็บ Devices & Audio ไม่ติ๊กอุปกรณ์ใด, clipboard ตามที่เลือกใน ENV-001 (ค) · บันทึกค่าที่ตั้งไว้ในหลักฐาน
   - C4 browser ทุกตัวบน Mac ไม่บันทึกรหัสและ logout จาก console ของผู้ให้บริการแล้ว และ console เปิด 2FA ด้วยอุปกรณ์ที่ไม่ใช่ Mac
   - C5 ไม่มี API token, ไฟล์ config ของ CLI ผู้ให้บริการ หรือ SSH key ของ VPS บน Mac
   - C6 password manager ที่มี CLI หรือ extension ไม่เก็บรหัสของ VPS, console หรือบัญชีโบรกเกอร์ หรือถามการยืนยันตัวทุกครั้ง
   - C7 browser และ Passwords ไม่บันทึกรหัสของบัญชีโบรกเกอร์ (Personal Area, MT5 login)
   - C8 Privacy & Security → Screen Recording และ Accessibility ไม่มีแอปที่ agent รันอยู่
   - C9 ทำตามกติกาบนหัวไฟล์ทุกครั้งก่อนเปิด RDP หรือ console · เปิด console ใน browser หรือ profile ที่ไม่มี extension ของ Claude หรือ ChatGPT (ถ้ามี ให้รัน `pgrep` ซ้ำหลังเปิด browser)
   - C10 Mac ไม่มี VM หรือ container ใดๆ (Windows หรือ Linux; Parallels, VMware Fusion, UTM, VirtualBox, Docker Desktop, OrbStack, colima/Lima, podman, qemu) ที่มี MT5 หรือ Wine รวมเครื่องมือที่ติดตั้งทาง command line · Mac มีบัญชีผู้ใช้ที่ login ได้บัญชีเดียว หรือบัญชีอื่นไม่มี MT5 · เครื่องนี้มี `.colima` และ `.docker` (บรรทัด `tools:`): ยืนยันว่า VM ของ colima และ container ของ Docker ไม่มี MT5 หรือ Wine · ยืนยันข้อนี้ซ้ำทุกครั้งที่บรรทัด `apps:`, `tools:` หรือ `wine:` ต่างจากหลักฐานของ ENV-002
   - ชื่อเมนูมาจากหน้า Microsoft Learn และโพสต์ของผู้ใช้ที่อ่าน 2026-11-17 ยังไม่ได้ตรวจในแอปจริง: ถ้าไม่ตรง ใช้ชื่อในแอปแล้วบอก Claude
5. ข้อ 6 ของ AC-03 (`sentinel` บน Mac เป็น PASS) คือรอบ PASS ของข้อ 3

## 5. ตรวจ hash ของ sentinel บน VPS (AC-03 ข้อ 5, PowerShell ธรรมดา บน VPS)
```powershell
PS> Get-FileHash C:\vault\SENTINEL-ENV002-*.json
PS> (Get-Item C:\vault\SENTINEL-ENV002-*.json).Length
PS> Select-String -Path C:\vault\SENTINEL-ENV002-*.json -SimpleMatch -Pattern '<token จาก docs/evidence/ENV-002-sentinel.json>' -Quiet
```
ค่า SHA256 ต้องตรงกับ `sha256`, ความยาวต้องตรงกับ `size` ใน `docs/evidence/ENV-002-sentinel.json` (ตัวพิมพ์ของ hash ไม่สำคัญ) และ `Select-String` ต้องพิมพ์ `True` · ห้ามลบไฟล์นี้ (ถ้าลบ ค่าที่ commit ใช้ไม่ได้ ต้องสร้างใหม่ตั้งแต่ข้อ 1)

## 6. ส่ง snapshot ก่อน cutoff ในภายหลัง
ใช้ขั้นตอนของ `docs/runbooks/ENV-001-vps.md` ข้อ 10 (D-021 ทาง (a); บน Mac แทน `subst` + mstsc ด้วยการ redirect โฟลเดอร์เดียวใน Windows App ตาม D-023 ข้อ 5) แล้วรันข้อ 3 ของ runbook นี้ซ้ำทุกครั้งหลังส่ง · **ใช้ได้หลัง ENV-1 ผ่านเท่านั้น:** runbook ฉบับ macOS ของ ENV-001 (branch `chore/ENV-001-vps-acquisition-host`) ผ่านการตรวจปิด r2 และ r3 แล้ว (`docs/reviews/ENV-001-runbook-v2-r2.md` และ `-r3.md` บน branch นั้น: F17 และ F27–F30 ปิด, ข้อ 0–10 พร้อมใช้) · F31 และ F32 ของ r3 (Low) แก้แล้วแต่ยังไม่มีผู้ตรวจปิด

## 7. เครื่อง Windows เดิม (AC-03 ข้อ 7, D-023 ข้อ 2 ทาง 1; หลัง SPIKE-002 ผ่านบน VPS)
ยืนยันทีละข้อพร้อมเวลา**ตามลำดับนี้**:
- (a) `docs/proposals/` และ memory ของ Claude Code (โฟลเดอร์ `memory/` ของโปรเจกต์นี้ใต้ `.claude/projects/` ใน home) ย้ายมา Mac แล้ว และรายการ SHA-256 ของสองฝั่งตรงกัน (วางรายการทั้งสองในหลักฐาน) · ย้ายด้วยรายการไฟล์ที่ระบุชื่อเท่านั้น ไม่ใช้ Migration Assistant และไม่คัดลอกทั้งโฟลเดอร์ผู้ใช้หรือ `AppData`
- (b) ในทุก worktree บนเครื่องนั้น ทั้งสามคำสั่งไม่พิมพ์อะไร:
  ```powershell
  PS> git status --short
  PS> git stash list
  PS> git log --branches --not --remotes --oneline
  ```
- (c) ถอน MetaTrader 5 (และ terminal ของโบรกเกอร์ทุกตัว): Settings → Apps → Installed apps → MetaTrader 5 → Uninstall · ถ้าตัวถอนทิ้งโฟลเดอร์ `C:\Program Files\MetaTrader 5` ไว้ ให้ลบด้วย PowerShell แบบ Administrator: `Remove-Item -Recurse -Force "C:\Program Files\MetaTrader 5"`
- (d) ลบโฟลเดอร์ข้อมูลของ terminal ทั้งโฟลเดอร์ (มี config ของบัญชีและ cache ของช่วงหลัง cutoff): `PS> Remove-Item -Recurse -Force "$env:APPDATA\MetaQuotes"`
- (d2) ก่อนลบ clone รัน envcheck โค้ด v1.9 หนึ่งครั้ง (ไม่ใส่ sentinel):
  ```powershell
  PS> git checkout c97aac6
  PS> git rev-parse --short HEAD
  PS> $env:PYTHONPATH="src"; uv run --offline python -m sochron.app.envcheck --role research; "exit status: $LASTEXITCODE"
  ```
  `git rev-parse` ต้องเป็น `c97aac6` · `terminal_install`, `terminal_data` และ `network_shares` ต้องเป็น PASS (`sentinel` UNKNOWN และ exit status ไม่ใช่ 0 ตามคาด) · วางรายงานทั้งหมดพร้อมเวลา · detail ของ item ที่ไม่ PASS อาจมี path เต็ม: ปิดบังชื่อบัญชีก่อนส่ง
- (e) ลบ clone และ worktree แล้ว
- (f) ไม่เปิด session ของ agent กับโปรเจกต์นี้บนเครื่องนั้นอีก
- (g) เครื่องนั้นไม่ถูกใช้เชื่อมต่อ VPS หรือ console ของผู้ให้บริการเลย ตั้งแต่เช่าจนถึงวันล้าง · ถ้าเคยเชื่อมต่อ: รัน `cmdkey /list` เอง (ไม่มี `TERMSRV/<IP ของ VPS>`), mstsc ไม่มี Saved credentials, ไม่มีไฟล์ `.rdp` ของ VPS และ browser บนเครื่องนั้นไม่บันทึกรหัสของ console

## สรุปสิ่งที่ส่งกลับ
| ข้อ | สิ่งที่ส่ง |
|---|---|
| 1 | JSON 6 ค่าที่ `make_sentinel.py` พิมพ์ และผล `Get-FileHash` |
| 2 | คำยืนยันข้อ 2.1–2.5 พร้อมเวลา และชื่อแอปที่รัน (Visual Studio Code) |
| 3 | ผลของ `pgrep` ก่อนขั้น (0) · ผลของขั้น (0)–(6) ทั้งหมด · รายงาน envcheck และ `/sbin/mount` ของรอบควบคุมและรอบ PASS พร้อมเวลาและ `exit status` · ผลของ `rmdir` และ `ls -d` |
| 4 | ผล `nc` ทุกบรรทัด (ปิดบัง IP), ผลของ `smbutil` และ `grep smbfs`, คำยืนยัน C1–C10 พร้อมเวลา และค่าที่ตั้งใน C3 |
| 5 | ผล `Get-FileHash`, ความยาว และ `Select-String` ของ sentinel บน VPS พร้อมเวลา |
| 7 | คำยืนยัน (a)–(g) ตามลำดับพร้อมเวลา, รายการ SHA-256 สองฝั่งของ (a) และรายงานของ (d2) |
