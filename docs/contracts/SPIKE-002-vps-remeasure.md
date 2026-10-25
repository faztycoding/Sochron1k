# TASK SPIKE-002 — วัดซ้ำบน VPS แบบอ่านอย่างเดียว: การเชื่อมต่อ, identity, spec ของ XAUUSDm, ความหมายของเวลา และความลึกของข้อมูล

Version v1.1 (v1 แยกจาก ENV-001 v1 ตาม `docs/reviews/ENV-contracts-r1.md` F2 ทาง (b), F14, F15, F18, F19 → v1.1 ตอบ `docs/reviews/ENV-contracts-r2.md`: ความสดของ tick แยกจาก offset และค่าความคลาดเคลื่อน (F26), `first_tick_utc` (F27), ช่องทางผล/clock sync/trade_allowed/exit code/runbook/รุ่นแพ็กเกจ/red flag (F28), เงื่อนไขเริ่ม (F24)) · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 12 U1/U2/U3 ("host ใหม่ (VPS) ต้องวัดซ้ำใน ENV-1"), ข้อ 13a "เปลี่ยน dependency/host" · ต่อจาก SPIKE-001 · Tier **Standard** · Branch `spike/SPIKE-002-vps-remeasure`
Status: **draft v1.1** (Claude ร่าง 2026-10-25 · รอ contract review r3 แล้วเจ้าของอนุมัติ พร้อม D-022 แพ็กเกจของ probe) · เริ่มได้เมื่อ ENV-001 ผ่านครบทุก AC
Hypothesis (research tasks): ไม่ใช่งานวิจัย

ส่วนหนึ่งของด่าน ENV-1: ENV-001 → **SPIKE-002** → ENV-002

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no — ใช้ทางเข้าที่ ENV-001 พิสูจน์แล้ว ไม่เพิ่มทางใหม่
- Q2 real money: no — Demo, login ด้วยรหัส investor (ซื้อขายไม่ได้), อ่านอย่างเดียว
- Q3 new storage/transfer of personal or confidential data: no — ผลปิดบังเลขบัญชีเหลือ 4 ตัวท้าย ไม่มีรหัสผ่าน
- Q4 schema change or deletion of real data: no
- Q5 hard-to-reverse external effect: no — ไม่มีคำสั่งซื้อขาย
- Q6 changes controls: no

Standard เพราะเชื่อมระบบภายนอก (terminal ที่ login บัญชีของโบรกเกอร์) เหมือน SPIKE-001

## Goal / user outcome (Thai)
บน VPS ที่ผ่าน ENV-001 รัน probe แบบอ่านอย่างเดียวที่ได้คำตอบเดียวกับ SPIKE-001 หรือรายงานความต่างให้เจ้าของตัดสินก่อน ENV-1 ผ่าน:
- เชื่อมต่อได้ · บัญชีตรง Authorization ของ contract นี้ (server, เลข 4 ตัวท้าย, ก่อนวันหมดสิทธิ์) · Demo · `trade_allowed` เป็น false (login ด้วยรหัส investor)
- spec ของ `XAUUSDm` ตรงกับที่ `costs.H001_COSTS` ใช้ · offset ของเวลาตรงกฎ `timebase` version "1" · build ของ terminal ที่ใช้จริง
- วันแรกที่มี M1 (ข้อเท็จจริงก่อน cutoff) และวันแรกที่มี tick (SPIKE-001 พบ 2026-01: **เป็นวันที่หลัง cutoff หนึ่งค่าที่ความละเอียดระดับวัน ซึ่งเจ้าของรับเมื่ออนุมัติ contract นี้**) โดยไม่ส่งข้อมูลอื่นหลัง cutoff (จำนวนแท่ง, ช่องว่าง, ราคา, timestamp ของ tick) กลับมา

## Current behavior and evidence (revision)
`spikes/SPIKE-001/probe.py` ฝัง `AUTH = Authorization("Exness-MT5Trial14", "8107", 2026-10-28 23:59 +07)` เป็นค่า default ของฟังก์ชัน จึงใช้ซ้ำหลังวันนั้นหรือกับบัญชีอื่นไม่ได้ และโหมด history คืนข้อมูลเชิงคุณภาพของปี 2025–2026 (จำนวน M1 ต่อปี, ช่องว่าง, ช่วงพักรอบ DST) · ผล SPIKE-001: build 6274, offset 0 (AC-04 UNKNOWN ว่า UTC หรือเวลา server), M1 ตั้งแต่ 2014, tick ตั้งแต่ 2026-01, maxbars เริ่ม 100,000 ต้องตั้ง Unlimited และรอ, ตลาดปิดเสาร์ถึงอาทิตย์ 22:01 (`docs/evidence/SPIKE-001.md`) · D-009/D-010 (MetaTrader5 5.0.6231, NumPy 2.5.4, tzdata 2026.5) อนุมัติเฉพาะ SPIKE-001

## Scope
- In scope: `spikes/SPIKE-002/probe.py` (ใหม่: เริ่มจากสำเนาของ SPIKE-001 แล้วแก้ตาม contract นี้; ไม่แก้ไฟล์ของ SPIKE-001) · `spikes/SPIKE-002/test_probe.py` (ใช้ MetaTrader5 ปลอม) · รันบน VPS โดยเจ้าของ · ผล JSON ปิดบังแล้วใน `spikes/SPIKE-002/results/` · หลักฐาน · D-022 · การตัดสินเรื่องกฎเวลาถ้าค่าต่าง (D entry)
- Exclusions: แก้ `timebase.RULES` หรือ `costs.H001_COSTS` (ถ้าต่าง เป็นงานแยกหลังเจ้าของตัดสิน) · ดึงข้อมูลเพื่อวิจัย · `data.acquire` · ส่งคำสั่ง
- Allowed files/modules: `spikes/SPIKE-002/**`, `docs/runbooks/SPIKE-002-remeasure.md` (ขั้นตอนของเจ้าของบน VPS), `docs/evidence/SPIKE-002.md`, `docs/handoff/SPIKE-002.md`, `DECISIONS.md` (D-022 และ D ของกฎเวลาถ้าต้องใช้), `docs/tooling/registry.md`, `PROGRESS.md`
- Must not touch: `spikes/SPIKE-001/**`, `src/sochron/**`, `pyproject.toml`, `uv.lock`, `tests/**`, `.github/**`, `.claude/**`, `scripts/controls/**`

## Inputs / outputs / errors (contract)
```text
คำสั่งบน VPS (เจ้าของรัน · environment ชั่วคราว นอก environment ของโปรเจกต์ ตาม D-022):
  uv run --no-project --python 3.12.15 --with MetaTrader5==5.0.6231 --with numpy==2.5.4 --with tzdata==2026.5 \
      python spikes/SPIKE-002/probe.py --server Exness-MT5Trial14 --login-suffix <4 ตัวท้าย> --valid-until <ISO 8601 พร้อม offset> \
      --clock-sync "<บรรทัด Last Successful Sync Time และ Source จาก w32tm /query /status ที่เจ้าของวาง>"
  ทุกค่าของ Authorization มาจาก argument (ไม่มีค่า default ฝังในโค้ด) · import MetaTrader5 หลังตรวจ argument
  ผลพิมพ์เป็น JSON ทาง stdout · เจ้าของคัดลอกกลับเป็นข้อความ · Claude บันทึกเป็น spikes/SPIKE-002/results/<UTC timestamp>.json บนเครื่องเจ้าของ
ลำดับ: ตรวจ argument (รูปแบบ, valid-until ยังไม่ถึง) → initialize → ตรวจ server และเลข 4 ตัวท้าย → trade_mode == DEMO → trade_allowed เป็น false → อ่านส่วนอื่น
  argument ผิดหรือขาด, หมดสิทธิ์, บัญชีไม่ตรง, ไม่ใช่ DEMO, trade_allowed true: หยุดทันที (exit 2) ก่อนเรียก symbol_* หรือ copy_*
  initialize ล้มหรือ terminal ไม่ได้ login: exit 3 (เหมือน SPIKE-001)
  trade mode เทียบกับค่า DEMO ของโมดูลจริง (ค่าอื่นทั้งหมดคือไม่ผ่าน) · tests ใช้ค่าตัวเลขของ trade mode (0 demo, 1 contest, 2 real) ไม่ใช้ชื่อค่าคงที่
ความสดของ tick และ offset (แยกกันตาม architecture ข้อ 13a):
  เก็บตัวอย่าง 5 ครั้งห่างกัน 20 วินาที: time_msc ของ tick ล่าสุด และเวลา UTC ของเครื่อง
  market_open = time_msc เพิ่มขึ้นอย่างน้อย 3 ครั้งใน 5 ตัวอย่าง และเวลาที่รันเป็นวันจันทร์–ศุกร์ (UTC) — ไม่ใช้ค่า offset ในการตัดสิน
  offset ต่อตัวอย่าง = tick time − เวลาเครื่อง (วินาที, ทศนิยมจาก time_msc) · offset_class = ค่าคูณของ 3600 ที่ใกล้ที่สุด เมื่อทุกตัวอย่างอยู่ห่าง
      ค่านั้นไม่เกิน ±120 วินาที (เกณฑ์เดียวกับ SPIKE-001) ไม่เช่นนั้น null · market_open false → offset_class null
  บันทึกเฉพาะ offset ของแต่ละตัวอย่าง (ปัดเป็นวินาที) ไม่บันทึก timestamp, bid หรือ ask ของ tick
ผล JSON (field ครบตามนี้ ไม่มีอื่น):
  identity: company, server, trade_mode, currency, leverage, login_masked ("****1234"), trade_allowed, terminal_build, terminal_path_kind ("installed"|"portable")
  spec (XAUUSDm): digits, point, trade_contract_size, volume_min, volume_step, volume_max, trade_stops_level, filling_mode,
                  swap_long, swap_short, swap_rollover3days, spread_float
  time: market_open, offset_samples_s (5 ค่า), offset_class_s หรือ null, clock_sync (ข้อความจาก --clock-sync)
  history: maxbars (ค่าที่ terminal รายงาน), first_m1_utc (วันที่, ก่อน cutoff), first_tick_utc (วันที่ระดับวัน: ค่าหลัง cutoff หนึ่งค่าที่เจ้าของรับไว้)
           # ไม่มีจำนวนแท่ง ช่องว่าง ราคา หรือ timestamp อื่นของ tick
  packages: MetaTrader5, numpy, tzdata, python   (อ่านด้วย importlib.metadata / platform · ไม่มีในเครื่อง = "not installed")
  run: started_utc (เวลาเครื่องตอนเริ่ม, ระดับนาที)
```

## Invariants
- ไม่มีการเรียก `order_send`, `order_check`, `positions_*`, `orders_*`, `history_*` หรือฟังก์ชันที่เปลี่ยนบัญชี (เรียกได้เฉพาะ initialize, shutdown, last_error, version, terminal_info, account_info, symbol_info, symbol_info_tick, copy_rates_range/from_pos, copy_ticks_range/from เพื่อหาวันแรก)
- ไม่มีรหัสผ่านใน argument, ไฟล์หรือ log · login ใน terminal ด้วยมือ (รหัส investor)
- ไม่มีข้อมูลหลัง cutoff ที่เป็นชุดราคา จำนวนแท่ง ช่องว่าง หรือ timestamp ของ tick ในผลที่คัดลอกกลับมา ยกเว้น `first_tick_utc` ระดับวันหนึ่งค่า (เจ้าของรับเมื่ออนุมัติ)
- ไม่แก้ไฟล์ของ SPIKE-001 · probe ใหม่ไม่ถูก import โดย `src`

## Negative cases
valid-until ผ่านไปแล้ว · server หรือเลข 4 ตัวท้ายไม่ตรง · trade_mode ไม่ใช่ DEMO · `trade_allowed` เป็น true (login ด้วยรหัสหลัก: exit 2 ให้ login ใหม่ด้วยรหัส investor) · terminal ไม่ได้เปิดหรือไม่ได้ login (exit 3) · ไม่มี argument (exit 2) · ตลาดปิด: tick ไม่ขยับ (market_open false → offset_class null = UNKNOWN ไม่ใช่ 0) · tick สดแต่เวลาเลื่อน +7200 วินาที (market_open true, offset_class 7200: รายงานว่าต่าง ไม่ใช่ "ตลาดปิด") · ตัวอย่างกระจายเกิน ±120 วินาที (offset_class null) · maxbars ไม่ใช่ Unlimited (first_m1_utc ไม่น่าเชื่อ: UNKNOWN) · build ≠ 6274 หรือ offset_class ≠ 0 (รายงานให้เจ้าของตัดสิน) · spec ต่างจาก `H001_COSTS` (รายงาน) · แพ็กเกจรุ่นไม่ตรง D-022

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given MetaTrader5 ปลอมใน unit test When รัน probe ด้วย valid-until ที่ผ่านไปแล้ว, server อื่น, เลข 4 ตัวท้ายอื่น, trade mode 1 หรือ 2, `trade_allowed` true หรือไม่มี argument Then exit 2 พร้อมข้อความ และไม่มีการเรียก `copy_*`, `symbol_*` หรือฟังก์ชันอื่นนอกรายการที่จำเป็นต่อการตรวจ · initialize ล้ม = exit 3 · ไม่มีค่า Authorization ฝังในโค้ด
- AC-02 Given terminal บน VPS login บัญชี Demo ด้วยรหัส investor When เจ้าของรันคำสั่งของ contract Then identity ตรง Authorization, trade_mode DEMO, currency USD, `trade_allowed` false และบันทึก build
- AC-03 Given ผลรอบเดียวกัน When เทียบ spec กับ `costs.H001_COSTS` และ `docs/evidence/SPIKE-001.md` Then ทุกค่าตรง หรือหลักฐานแสดงความต่างทีละค่าและเปิดงานแก้ costs ก่อน SLICE-R1
- AC-04 Given (unit test) tick ปลอมที่สดแต่เลื่อน +7200 วินาที และ tick ที่ไม่ขยับ When คำนวณ Then แบบแรก market_open true, offset_class 7200 และแบบหลัง market_open false, offset_class null · Given (บน VPS) รันวันจันทร์–ศุกร์นอกช่วงพักรายวันหลัง `w32tm /resync` When อ่านผล Then market_open true, `offset_class_s` = 0 ตามกฎ `timebase` version "1" และ build = 6274 · หรือ (ค่าใดต่าง) เจ้าของบันทึกการตัดสิน (ขยายกฎ version "1" ไปยัง build ใหม่พร้อมหลักฐาน หรือเปิด contract เพิ่ม version ก่อนการดึงข้อมูลใดๆ) ใน DECISIONS **ก่อน** ENV-1 ผ่าน
- AC-05 Given terminal ตั้ง Max bars เป็น Unlimited และรอให้ history โหลด When รัน probe Then ผลมี first_m1_utc และ first_tick_utc และมี field ครบตามหัวข้อ contract เท่านั้น (test ตรวจรายการ key ของ JSON) · ไม่มีจำนวนแท่ง ช่องว่าง ราคา หรือ timestamp ของ tick ใดนอกจาก `first_tick_utc` ระดับวัน
- AC-06 Given ทั้งงาน When `bash scripts/controls/red-flags.sh main`, `uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` และ suite ทั้งหมด Then กลุ่ม "Order or account mutation surface" ว่าง (ทั้ง probe และ tests ไม่มีชื่อฟังก์ชันส่งคำสั่งหรือชื่อค่าคงที่ของบัญชีจริง: fake ตรวจว่าชุดชื่อที่ถูกเรียกเป็นส่วนย่อยของรายการที่อนุญาต), unit tests ของ probe ผ่าน (รุ่นแพ็กเกจที่ไม่มีใน environment ของโปรเจกต์ = "not installed"), suite ผ่าน skipped 0 และ CI เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01, 05 (รูปแบบ key), 06 | Claude (unit tests ของ spike) + ผู้ตรวจ | `uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` | L2 |
| 02–05 | เจ้าของ (รันบน VPS) + ผู้ตรวจ | `docs/runbooks/SPIKE-002-remeasure.md` → JSON ทาง stdout → `spikes/SPIKE-002/results/` + `docs/evidence/SPIKE-002.md` | L4 |

## Risk, data and external side effects
อ่านอย่างเดียวจากบัญชี Demo ด้วยรหัส investor จึงซื้อขายไม่ได้แม้โค้ดผิด · ผลภายนอก: ไม่มี · ความเสี่ยงหลัก: ตีความค่าผิดเพราะรันตอนตลาดปิดหรือ history ยังโหลดไม่ครบ (บังคับด้วย market_open และ maxbars) · ผู้อนุญาต: เจ้าของ

## Plan, dependencies and unknowns (P06)
1. Understanding: ทำซ้ำการวัดของ SPIKE-001 บนเครื่องที่จะใช้จริง ด้วย probe ที่รับ authorization ใหม่และไม่ส่งข้อมูลหลัง cutoff กลับมา · เข้าใจผิดที่เป็นไปได้: แก้ probe ของ SPIKE-001 แทนการทำ probe ใหม่ · รันวันหยุดแล้วได้ offset ผิด · ยอมรับ build ใหม่โดยไม่ตัดสิน
2. Files / reuse: สำเนาของ `spikes/SPIKE-001/probe.py` (ส่วน initialize, mask_login, spec, การหาวันแรก) · ตัดโหมด census ของปี 2025–2026 ออก
3. Steps: (1) review r3 → เจ้าของอนุมัติ + D-022 (Claude ตรวจ advisory ของสามแพ็กเกจที่ OSV อีกครั้งในวันที่ขออนุมัติ) (2) Claude เขียน probe + unit tests (3) หลัง ENV-001 ผ่าน เจ้าของรันบน VPS ตามเงื่อนไข AC-04/AC-05 (4) หลักฐาน + การตัดสินเรื่องกฎเวลาถ้าต้องใช้ (5) ผู้ตรวจ session ใหม่ → PR
4. Risks: terminal บน VPS อัปเดต build เอง (คาดว่าเกิด) · PyPI มี MetaTrader5 รุ่นใหม่ (ต้อง admission ใหม่ถ้าจะใช้)
5. Decisions needed from the owner:
   - (ก) อนุมัติ contract นี้ และ D-022 (MetaTrader5 5.0.6231, numpy 2.5.4, tzdata 2026.5 ใน environment ชั่วคราวบน VPS สำหรับ SPIKE-002 เท่านั้น) · **แนะนำ:** อนุมัติ
   - (ข) ถ้า build ≠ 6274 แต่ offset = 0 · **แนะนำ:** ขยายกฎเวลา version "1" ไปยัง build ใหม่ด้วยหลักฐานจาก SPIKE-002 (บันทึกใน DECISIONS) · ถ้า offset ≠ 0: หยุด ENV-1 และเปิด contract ของกฎเวลา version ใหม่
   - (ค) valid-until ของ Authorization · **แนะนำ:** หลังวันที่วางแผนรันอย่างน้อย 2 สัปดาห์

## Authorization (filled by the owner)
| รายการ | ค่า |
|---|---|
| actor | เจ้าของ (login terminal ด้วยรหัส investor, รัน probe บน VPS) · Claude (เขียน probe บนเครื่องเจ้าของ) |
| action | อ่านอย่างเดียว: identity, spec, เวลา, วันแรกที่มีข้อมูล |
| target | บัญชี Demo บน `Exness-MT5Trial14` เลข 4 ตัวท้าย TBD (เจ้าของกรอก) · สัญลักษณ์ `XAUUSDm` |
| valid until | TBD (เจ้าของกรอก) |

## Budget
1 session ของ Claude · เจ้าของ ≈ 30 นาทีบน VPS (บวกเวลารอ history) · headless session ไม่เกิน 2 (ผู้ตรวจ, สำรอง) · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
ไม่มีผลข้างเคียง · ลบ environment ชั่วคราวได้ (`uv cache clean`) · ถ้าบัญชีไม่ตรงหรือไม่ใช่ Demo probe หยุดเอง

## DoR status / missing items / next action
ขาด: review r3, การตัดสินของเจ้าของ (ก)–(ค), ENV-001 ผ่าน · next: review r3

## Done scope
implementation (probe + tests) และหลักฐานการวัดบน VPS
