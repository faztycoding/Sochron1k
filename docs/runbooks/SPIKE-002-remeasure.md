# Runbook SPIKE-002: วัดซ้ำบน VPS แบบอ่านอย่างเดียว

Contract: `docs/contracts/SPIKE-002-vps-remeasure.md` (v1.2) · แพ็กเกจ: D-022 · ผู้ทำ: เจ้าของ · ใช้เวลา ≈ 30 นาที (รวมเวลารอ history)

Probe อ่านอย่างเดียว ไม่ส่ง แก้ หรือตรวจคำสั่งซื้อขาย และ login ด้วยรหัส investor ซึ่งซื้อขายไม่ได้อยู่แล้ว · ผลที่ส่งกลับเป็น**ข้อความ** ไม่ใช่ไฟล์

## ก่อนเริ่ม
- [ ] ENV-001 ผ่านครบทุก AC (`docs/evidence/ENV-001.md`) · uv บน VPS ≥ 0.13.4
- [ ] บนเครื่องของคุณ ปิดหน้าต่าง Claude Code และ Codex ก่อนเปิด RDP ไป VPS (ENV-002 (ค))
- [ ] ส่งสองค่านี้ให้ Claude บันทึกในตาราง Authorization ของ contract **ก่อน**รัน:
  - เลข 4 ตัวท้ายของบัญชี Demo
  - วันหมดสิทธิ์ (valid until) อย่างน้อย 2 สัปดาห์หลังวันที่จะรัน เช่น `2026-11-30T23:59:00+07:00`
- [ ] รับ **hash ของ commit ที่ตรวจแล้ว** จาก Claude (Claude push branch `spike/SPIKE-002-vps-remeasure` ก่อน เพราะ probe ยังไม่อยู่ใน `main` จนกว่าจะมีหลักฐานจาก VPS)
- [ ] เลือกเวลารัน: **วันอังคาร–พฤหัสบดี 09:00–23:00 เวลาไทย** (ห่างจากช่วงพักรายวันราว 03:58–05:00 เวลาไทย ซึ่งหลังสหรัฐเลิก DST วันที่ 1 พ.ย. 2026 น่าจะเลื่อนเป็นราว 04:58–06:00 ตามที่ SPIKE-001 เห็นในช่วง EST และห่างจากวันหยุดสุดสัปดาห์)

## ขั้นที่ 1: เตรียม terminal บน VPS
1. เปิด MT5 terminal แล้ว login บัญชี Demo บน server `Exness-MT5Trial14` ด้วย**รหัส investor** (ไม่ใช่รหัสหลัก)
2. Tools → Options → Charts → **Max bars in chart = Unlimited** → OK → ปิดแล้วเปิด terminal ใหม่
3. เปิดกราฟ `XAUUSDm` timeframe M1 แล้วรออย่างน้อย 15 นาทีให้ history โหลด (SPIKE-001 ต้องรอราว 14 นาที)

## ขั้นที่ 2: sync นาฬิกา
เปิด PowerShell แบบ Administrator แล้วรัน:
```powershell
w32tm /resync
w32tm /query /status
```
คัดลอกสองบรรทัด `Last Successful Sync Time` และ `Source` มาต่อกันเป็นบรรทัดเดียว คั่นด้วย ` | `

## ขั้นที่ 3: ดึง commit ที่ตรวจแล้ว และรัน probe
เปิด PowerShell **แบบธรรมดา (ไม่ใช่ Administrator)** ที่โฟลเดอร์ของ repo บน VPS:
```powershell
git fetch origin
git switch --detach <hash ที่ Claude ให้>
git rev-parse --short HEAD
git status --short
```
`git rev-parse` ต้องพิมพ์ hash เดียวกับที่ Claude ให้ และ `git status --short` ต้องไม่พิมพ์อะไรเลย ถ้าไม่ตรง หยุดแล้วส่งผลสองบรรทัดนั้นให้ Claude

จากนั้นรัน (บรรทัดเดียว):
```powershell
uv run --no-project --python 3.12.15 --with MetaTrader5==5.0.6231 --with numpy==2.5.4 --with tzdata==2026.5 python spikes/SPIKE-002/probe.py --server Exness-MT5Trial14 --login-suffix <เลข 4 ตัวท้าย> --valid-until <วันหมดสิทธิ์> --clock-sync "<บรรทัดจากขั้นที่ 2>"
```
probe เก็บตัวอย่างเวลา 5 ครั้งห่างกัน 20 วินาที แล้วค้นวันแรกของ M1 ทีละเดือนก่อน 2025 จึงใช้เวลาราว 1–3 นาที

## ขั้นที่ 4: ส่งผลกลับ
- **ทุกกรณี:** วาง hash จาก `git rev-parse --short HEAD` ไว้บรรทัดแรก (หลักฐานต้องบอกว่ารันจาก commit ไหน)
- **สำเร็จ (exit 0):** คัดลอก JSON ทั้งก้อนที่พิมพ์ออกมาแล้ววางในแชทของ Claude · Claude บันทึกเป็น `spikes/SPIKE-002/results/<เวลา UTC>.json` และเขียน `docs/evidence/SPIKE-002.md`
- **ปฏิเสธ:** จะเห็นบรรทัดเดียว `REFUSED (exit N): …` ให้คัดลอกบรรทัดนั้นมา
  - exit 2: argument ผิด หมดสิทธิ์ บัญชีหรือ server ไม่ตรง ไม่ใช่ Demo หรือ **login ด้วยรหัสหลัก** (`trade_allowed` เป็น true) → login ใหม่ด้วยรหัส investor แล้วรันซ้ำ
  - exit 3: terminal ไม่ได้เปิด ไม่ได้ login หรือ environment ของ uv ไม่มี MetaTrader5
  - ถ้าเห็น `can't open file ... probe.py` แทนบรรทัด `REFUSED`: repo ไม่ได้อยู่ที่ commit ของขั้นที่ 3 · ทำขั้นที่ 3 ใหม่

ก่อนวาง ตรวจด้วยตาว่าไม่มีเลขบัญชีเต็ม (ต้องเห็นแค่ `****` ตามด้วย 4 ตัวท้าย) และไม่มีรหัสผ่าน

## เมื่อไรต้องรันซ้ำ
| ค่าในผล | ความหมาย | ทำอะไร |
|---|---|---|
| `"market_open": false` | tick ไม่ขยับ หรือวันเสาร์–อาทิตย์ (UTC) | รันใหม่ในเวลาที่แนะนำ |
| `"first_m1_utc": null` | ยังไม่มี M1 ก่อน 2025 ใน terminal (history ยังโหลดไม่ครบ) | รอเพิ่มแล้วรันใหม่ |
| `"first_m1_utc": "UNKNOWN"` | Max bars ยังไม่ใช่ Unlimited หรือการขอข้อมูลล้ม | ตรวจขั้นที่ 1 แล้วรันใหม่ |
| `"offset_class_s": null` ทั้งที่ `market_open` เป็น true | เวลาของตัวอย่างกระจายเกิน ±120 วินาที | ทำขั้นที่ 2 ใหม่แล้วรันใหม่ |
| `"first_tick_utc": null` หรือ `"UNKNOWN"` | terminal ไม่คืน tick หรือการขอข้อมูลล้ม | รอ history แล้วรันใหม่ |

ถ้า `terminal_build` ไม่ใช่ 6274 หรือ `offset_class_s` ไม่ใช่ 0: ไม่ต้องรันซ้ำ · Claude สรุปให้คุณตัดสินตาม (ข) ของ contract ก่อน ENV-1 ผ่าน

## หลังเสร็จ
ไม่มีผลข้างเคียงบนบัญชี · กลับ repo ไปที่ `main` ด้วย `git switch main` · ลบ environment ชั่วคราวได้ด้วย `uv cache clean` (ไม่บังคับ)
