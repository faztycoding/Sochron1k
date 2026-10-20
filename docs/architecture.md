# สถาปัตยกรรมเริ่มต้นของ Sochron1k

สถานะ: **Proposed (D-001)** — รอเจ้าของตัดสิน · ร่างเมื่อ 18 ต.ค. 2026 โดย Claude Code ตาม Handbook v5 บท 6 และบท 34 (P04)
ก่อนรับข้อเสนอ ควรให้ Codex โจมตีทางเลือกนี้ใน chat ใหม่ก่อน (`$adversarial-design-review` โหมด architecture) โดยใช้ผลของ SPIKE-001 ประกอบ SPIKE-001 รันได้ก่อนที่ D-001 จะได้รับการยอมรับ

## 1. สรุปข้อเสนอ

- ทำเป็น **Python modular monolith ตัวเดียว** รันบน Windows และคุยกับ MT5 terminal ผ่านแพ็กเกจทางการ `MetaTrader5` โดยตรง ไม่ต้องมี EA bridge, web server, database server หรือ Docker ในรอบแรก
- **วิจัยก่อน เทรดทีหลัง**: slice แรกที่ใช้งานจริงคือวงวิจัยบนข้อมูลจริง (snapshot → ตรวจข้อมูล → สมมติฐาน → backtest → registry → รายงาน) ส่วนการส่งคำสั่งบน Demo เป็น slice ถัดไป
- กลยุทธ์เป็น **pure function ชุดเดียว** ใช้ทั้ง backtest และ Demo, เวลาแปลงผ่าน **โมดูลเดียว** และ **risk gate** อยู่หน้าทุกคำสั่ง
- เริ่มจาก spike แบบอ่านอย่างเดียว (SPIKE-001) เพื่อพิสูจน์ว่าเชื่อม MT5 ได้จริง และรู้ความหมายของเวลาในข้อมูลของโบรกเกอร์ ก่อนลงทุนเขียนระบบ ผลของ spike ใช้ตัดสินรับหรือปฏิเสธ D-001

## 2. ข้อเท็จจริงที่ใช้ตัดสิน (ตรวจเมื่อ 18 ต.ค. 2026)

| ข้อเท็จจริง | ที่มา |
|---|---|
| เครื่องพัฒนาเป็น Windows 11 มี Git Bash, Node.js v26.12.0 และ uv 0.13.0 (มี CPython 3.12.15 และ 3.15.0 ผ่าน uv) แต่ไม่มี system Python และไม่มี Docker | ตรวจคำสั่งบนเครื่อง |
| ยังไม่พบ MT5 terminal ในตำแหน่งมาตรฐาน (Program Files, %APPDATA%\MetaQuotes) | ตรวจบนเครื่อง |
| `MetaTrader5` 5.0.6231 (ออก 27 ก.ย. 2026) มี wheel เฉพาะ `win_amd64` สำหรับ cp310–cp314 จึงใช้ได้เฉพาะ Windows และยังไม่รองรับ Python 3.15 | pypi.org/pypi/MetaTrader5 |
| เอกสาร Python API ของ MetaQuotes ระบุว่า MT5 เก็บเวลา tick และเวลาเปิดแท่งเป็น UTC "without the shift" และ "Data received from the MetaTrader 5 terminal has UTC time" | mql5.com/en/docs/python_metatrader5 (copy_rates_from, copy_ticks_from) |
| ฟอรัม MQL5 (moderator, ในกระทู้เรื่อง CopyRates ของ MQL5) ระบุว่าข้อมูลที่ MT5 ส่งเป็นเวลา server ของโบรกเกอร์ และไม่มีฟังก์ชันทางการที่บอก offset หลักฐานสองแหล่งนี้ขัดกัน จึงยังสรุปไม่ได้ ต้องวัดจริงใน SPIKE-001 (Handbook บท 34: เอกสารกับพฤติกรรมจริงอาจไม่ตรงกัน) | mql5.com/en/forum/517974 (Handbook S22) |
| Claude Code 2.1.301 อ่าน AGENTS.md ผ่าน `@AGENTS.md` ใน CLAUDE.md ส่วน Codex IDE 26.1007 อ่าน AGENTS.md เองและหา skills จาก `.agents/skills/` | เอกสารทางการของทั้งสองเครื่องมือ |
| รอบก่อน (git `a3b3fbf`) มี 415 ไฟล์, 37 contracts, 40 ADRs ใช้ React/Vite + FastAPI + worker + MQL5 EA bridge + Supabase + Docker แต่ README ระบุว่ายังไม่เคยมี Demo round trip จริง และไม่มีข้อมูลจริงสำหรับ replay/backtest | README และ docs ที่ `a3b3fbf` |

ข้อสังเกตจากรอบก่อน: งานส่วนใหญ่ไปอยู่ที่ระบบรอบตัว (bridge, sync, dashboard, alert) ก่อนที่จะมีหลักฐานแม้แต่ชิ้นเดียวว่ากลยุทธ์มีความได้เปรียบ ซึ่งตรงกับกับดักในบท 34 ("ผลลัพธ์ของงานประเภทนี้คือหลักฐานว่ามีความได้เปรียบ ไม่ใช่ฟีเจอร์") และรูปแบบ F15 (ออกแบบเกินจำเป็น) ข้อเสนอรอบนี้จึงกลับลำดับ: พิสูจน์ข้อมูลและความได้เปรียบก่อน

## 3. หลักที่ใช้ตัดสิน

1. ผลลัพธ์คือหลักฐานว่ามี edge หลังหักต้นทุน ไม่ใช่จำนวนฟีเจอร์ (บท 34)
2. โครงสร้างเล็กที่สุดที่รองรับข้อจำกัดจริง แยก module ก่อนแยก service ใช้เทคโนโลยีที่น่าเบื่อและ AI รู้จักดี (บท 6)
3. Strategy เป็น pure function ชุดเดียวทั้ง backtest และ live (บท 34)
4. MT5 เป็นความจริงของราคา คำสั่ง และ position ถ้าผลไม่แน่ชัดให้เป็น UNKNOWN แล้ว reconcile (บท 20, 34)
5. Risk gate ของเราอยู่หน้าทุกคำสั่ง และ Demo-only ต้องบังคับด้วยโค้ด ไม่ใช่ config (บท 13, 34)
6. ทดสอบได้ใน CI บน Linux โดยไม่ต้องมี MT5 ส่วนที่ต้องใช้ MT5 แยกไว้หลัง adapter ตัวเดียว
7. เจ้าของคนเดียวต้องดูแลไหว ไม่เพิ่มภาระ ops เกินจำเป็น

## 4. ทางเลือก

| ประเด็น | A. Python monolith + `MetaTrader5` (แนะนำ) | B. MQL5 EA ส่งคำสั่ง + Python วิจัย/สั่งงานผ่าน bridge | C. MQL5 ล้วน (EA + Strategy Tester) |
|---|---|---|---|
| ภาพรวม | แอป Python เดียว คุย terminal ผ่าน IPC ของแพ็กเกจทางการ | EA ใน terminal ทำหน้าที่ executor, Python ส่ง command ผ่านไฟล์/HTTP | ทุกอย่างอยู่ใน EA, วิจัยด้วย Strategy Tester |
| Strategy ชุดเดียว backtest = live | ได้ ตรงๆ | เสี่ยงมีสองชุด (Python วิจัย / MQL5 live) เว้นแต่ EA เป็นแค่ executor | ได้ (MQL5 ชุดเดียว) |
| ความเข้มงวดของการวิจัย (registry, holdout, random-entry, golden tests) | ทำได้ครบด้วย Python + pytest | ทำได้ในฝั่ง Python | ยาก, optimizer ของ Tester ชวนให้ลองหลายร้อย variant |
| ทดสอบใน CI | ได้ทุกส่วน ยกเว้น adapter ที่ต้องมี terminal | ฝั่ง EA ทดสอบอัตโนมัติยาก | แทบไม่ได้ |
| ความซับซ้อน | ต่ำ ภาษาเดียว process เดียว | สูง สองภาษา + protocol bridge + journal สองฝั่ง | กลาง แต่ test/วิเคราะห์ยาก |
| ข้อจำกัดของ host | ต้องรันบน Windows (terminal + Python เครื่องเดียวกัน) | Python อยู่ที่ไหนก็ได้ แต่ EA ต้องอยู่กับ terminal | Windows (terminal) |
| ความแม่นของ AI agent | สูง (Python กระแสหลัก) | กลาง (MQL5 ตัวอย่างน้อยกว่า) | กลาง–ต่ำ |
| ทำงานต่อเมื่อ Python ล่ม | ไม่ได้ แต่ SL/TP อยู่ฝั่ง server ของโบรกเกอร์อยู่แล้ว | EA ทำงานต่อได้ | ทำงานต่อได้ |
| ค่าใช้จ่าย [A] (ขอบเขตอยู่ใต้ตาราง) | 0 บนเครื่องเจ้าของ [A] | 0 + เวลาพัฒนา bridge [A] | 0 [A] |
| สิ่งที่ย้อนกลับยาก | น้อย ถ้าแยก adapter ไว้ เปลี่ยนเป็น B ภายหลังได้ | protocol และ journal สองฝั่ง | การวิจัยผูกกับ MQL5 |

ขอบเขตของแถว "ค่าใช้จ่าย" [A]: นับเฉพาะค่า license และค่าบริการที่ต้องจ่ายเพิ่มเพราะเลือกทางนั้น โดยสมมติว่ารันบนเครื่องเจ้าของ · ไม่รวม VPS, ค่าข้อมูลจากแหล่งอื่น, ค่าไฟ, ค่าคอมมิชชันหรือ spread ของโบรกเกอร์ และเวลาพัฒนา (ยกเว้นที่เขียนไว้ในช่อง) · ยังไม่ได้ประเมินตัวเลขจริง งบรายเดือนยังเป็น TBD ตาม SPEC ข้อ 6 และ Q-10

**ทำไมรอบก่อนเลือก B แต่รอบนี้ไม่จำเป็น** รอบก่อนพัฒนาบน macOS (มีร่องรอย Colima และ `.venv/bin/python`) ซึ่งใช้แพ็กเกจ `MetaTrader5` ไม่ได้ จึงต้องมี EA + bridge ตอนนี้เครื่องเป็น Windows เงื่อนไขนั้นหมดไปแล้ว

## 5. ข้อเสนอ: ทางเลือก A

เลือก A เพราะรักษาหลัก "strategy ชุดเดียว" ได้ตรงที่สุด ทดสอบได้มากที่สุด และมีชิ้นส่วนน้อยที่สุดสำหรับเจ้าของคนเดียว

Stack ที่เสนอ (ยังไม่ติดตั้ง ต้องผ่าน dependency admission ทีละตัวเมื่อ contract ต้องใช้):
- Python **3.12.x** ผ่าน uv (มีในเครื่องแล้ว, มี wheel ของ `MetaTrader5`, ไลบรารีวิทยาศาสตร์รองรับครบ, หมดอายุ ต.ค. 2028) ส่วน 3.13/3.14 ก็ใช้ได้ แต่ 3.15 ใช้ไม่ได้
- `MetaTrader5` (MetaQuotes) เฉพาะใน `broker/mt5` และ optional บน Windows เท่านั้น เพื่อให้ CI บน Linux ติดตั้งส่วนอื่นได้
- pytest (+ hypothesis สำหรับ property tests ของ risk sizing), ruff, pyright
- ข้อมูล: numpy, pandas, pyarrow (Parquet) · journal และ registry: sqlite3 / JSONL จาก stdlib
- `tzdata` (Windows ไม่มีฐานข้อมูล timezone ให้ `zoneinfo`)
- CLI ด้วย `argparse` จาก stdlib (ไม่เพิ่ม framework)

ถ้าจะเปลี่ยนจาก A ไป B ภายหลัง ให้กลับมาทบทวนเมื่อเกิดเงื่อนไขใดเงื่อนไขหนึ่ง: ต้องย้ายไป host ที่ไม่ใช่ Windows, ต้องการ logic ฝั่ง terminal ที่ทำงานต่อได้แม้ Python ล่ม (เช่น trailing stop ที่ซับซ้อน), หรือ latency ต้องต่ำกว่าที่ Python polling ทำได้

## 6. ภาพรวมระบบ (system context)

```mermaid
flowchart LR
  Owner([Owner / approver]) -->|SPEC, approvals, demo| Repo[(Git repo: docs, code, registry)]
  CC[Claude Code: planner + implementer] -->|task-branch commits| Repo
  CX[Codex: test author + reviewer] -->|tests, reviews| Repo
  CI[GitHub Actions: verifier] -->|required checks| Repo
  subgraph Host[Windows host - owner PC first]
    App[Sochron1k Python app]
    Term[MT5 terminal logged in to Demo]
  end
  App <-->|MetaTrader5 package, local IPC| Term
  Term <-->|broker protocol| Broker[(Broker trade server - Demo)]
  App --> Store[(Local data: Parquet snapshots, SQLite journal)]
  Owner -->|reads reports| App
  Vault[(Holdout vault outside research checkout)] -.->|only on evaluation day| App
```

## 7. Data flow และ trust boundaries

```mermaid
flowchart TB
  subgraph BRK[Untrusted input: broker data, timestamp meaning unverified until SPIKE-001]
    Term[MT5 terminal]
  end
  Term -->|rates, ticks, symbol info| Adp[broker.mt5 adapter - the only importer of MetaTrader5]
  Adp --> Time[timebase: raw MT5 time to UTC by the measured rule, DST, sessions]
  Time --> Data[data: immutable snapshot + manifest, validation report PASS/WARN/UNKNOWN/STOP]
  Data --> Feat[strategy features, point-in-time]
  Feat --> Strat[strategy.decide - pure, versioned]
  Strat -->|research path| Sim[backtest: bid/ask fills, ambiguity labels]
  Cost[costs] --> Sim
  Sim --> Run[research runner + random-entry baselines]
  Run --> Reg[(registry JSONL - append-only, committed)]
  Run --> Rep[owner reports]
  Strat -->|Demo path| Risk[risk gate: Decimal sizing, limits, halts]
  Cost --> Risk
  Risk --> Exe[execution: state machine, idempotency]
  Exe --> Jrn[(journal SQLite WAL - intent before send)]
  Exe -->|Demo-only guard, then order| Adp
  Adp -->|results, positions, deals| Exe
  Exe --> Rec[reconcile UNKNOWN against terminal]
```

Trust boundaries ที่ต้องบังคับจริง:
- ข้อมูลจากโบรกเกอร์เป็น input ที่ไม่น่าเชื่อถือ ตรวจที่ boundary (bid > ask, เวลาถอยหลัง, ช่องว่าง) แล้วรายงาน ห้ามซ่อมเงียบ
- ระหว่าง strategy กับ execution: strategy ส่งได้แค่ "การตัดสินใจ" ส่วนสิทธิ์ส่งคำสั่งอยู่ที่ risk gate + execution เท่านั้น
- ระหว่างแอปกับบัญชี: ก่อนส่งทุกคำสั่ง ตรวจ `account_info().trade_mode` ว่าเป็น Demo ถ้าไม่ใช่ ให้ปฏิเสธและหยุด
- ระหว่าง research กับ holdout: โค้ดวิจัยอ่าน holdout ไม่ได้ (ข้อมูลไม่อยู่ในเครื่องวิจัยจนถึงวันประเมิน)
- ระหว่าง agent กับ repo: locked paths บังคับด้วย deny rules + hooks + CI (D-004)

## 8. Module map และกฎ import

โฟลเดอร์จะถูกสร้างเมื่อ contract ต้องใช้จริงเท่านั้น โฟลเดอร์ว่างไม่ใช่หลักฐานว่ามีส่วนนั้นอยู่

| Module (`src/sochron/…`) | หน้าที่ | ห้าม | import ได้เฉพาะ |
|---|---|---|---|
| `core` | ชนิดข้อมูลกลาง: Instrument, Bar, Tick, Side, Money (Decimal) | I/O | – |
| `timebase` | แปลงเวลาดิบจาก MT5 ↔ UTC ตามกติกาที่ SPIKE-001 วัดได้, DST, sessions, วันเทรดแบบไทย | เรียกนาฬิกาเอง (รับ `now` เป็น argument) หรือสมมติ offset เอง | core |
| `data` | ดึงข้อมูลผ่าน broker port, สร้าง snapshot + manifest, validation report | แก้ข้อมูลดิบเงียบๆ | core, timebase, broker (port) |
| `strategy` | features + `decide()` แบบ pure และมี version | I/O, clock, MetaTrader5, random ที่ไม่มี seed | core, timebase |
| `costs` | spread, commission, slippage, swap และ stress ×2 | – | core |
| `backtest` | จำลองการเทรดด้วย bid/ask, ติดป้าย ambiguous เมื่อ SL/TP อยู่ในแท่งเดียวกัน | อ่าน holdout | core, timebase, strategy, costs |
| `research` | runner, registry, random-entry baseline, holdout gate, สถิติ, รายงาน | เรียก broker หรือ execution | core, timebase, data, strategy, costs, backtest |
| `risk` | sizing ด้วย Decimal, limits, halt state | ถูกเปลี่ยนโดย AI หรือ config ระหว่างรัน | core, costs |
| `execution` | วงจรชีวิตคำสั่ง, idempotency, reconcile | ส่งคำสั่งโดยไม่ผ่าน risk gate และ journal | core, risk, journal, broker (port) |
| `broker` | port + `mt5` adapter (ตัวเดียวที่ import MetaTrader5) | ตัดสินใจเชิงกลยุทธ์ | core, timebase |
| `journal` | SQLite WAL: intent, events, external IDs, halts | ลบประวัติ | core |
| `app` | CLI, ตรวจ config ตอนเริ่ม (fail fast), ประกอบชิ้นส่วน | business logic | ทุกโมดูล |

```text
src/sochron/<modules>        # implementation (Claude Code)
tests/unit, tests/integration # implementer tests
tests/acceptance/<task>/      # test author, locked
tests/golden/<task>/          # test author, hand-computed answers, locked
tests/architecture/           # import-rule checks, locked
research/registry/*.jsonl     # append-only, committed
spikes/<SPIKE-ID>/            # disposable spike code, never imported by src
data/ journal/ reports/out/   # runtime data, gitignored
```

## 9. Invariants ระดับระบบ และจุดที่บังคับ

| Invariant | บังคับด้วย |
|---|---|
| ไม่มีเส้นทางไปบัญชีเงินจริง | Demo guard ในโค้ด + negative test + red-flag "Order or account mutation surface" |
| ไม่มีคำสั่งไหนถูกส่งโดยไม่ผ่าน risk gate และ journal | โครงสร้าง module (execution เท่านั้นที่เรียก broker send) + architecture test |
| ส่งแล้วผลไม่ชัด = UNKNOWN และ reconcile ก่อน retry | state machine + test กรณี timeout |
| Strategy ไม่มี I/O และไม่ import MetaTrader5 | architecture test (AST) ใน `tests/architecture/` |
| เวลาแปลงผ่าน timebase เท่านั้น | architecture test + leakage audit |
| สมมติฐานแก้ไม่ได้หลัง commit / registry เพิ่มได้อย่างเดียว | hook + `control-gate` (ตรวจทุก commit ด้วยตัวตรวจจาก base revision) |
| Holdout ไม่อยู่ในเครื่องวิจัย | ขั้นตอนของเจ้าของ + loader ปฏิเสธช่วงเวลาหลัง cutoff + `.gitignore` |
| ไม่มี secret ใน repo/log | `.gitignore`, deny rules, red-flag scan |

## 10. ลำดับการสร้าง (vertical slices)

| Phase | Contract | ได้อะไร | เกณฑ์จบ | Tier |
|---|---|---|---|---|
| 0 | BOOT-001 | กติกา, controls, skills/agents, architecture ร่าง | เจ้าของรับ D-002 ถึง D-005 และ P25 ผ่านทั้งสองเครื่องมือ (D-001 ยัง proposed) | High (Q6) |
| 1 | SPIKE-001 | พิสูจน์ว่าเชื่อม MT5 ได้, รู้ว่า timestamp เป็น UTC หรือเวลา server และพฤติกรรมช่วง DST, รู้ความลึกของข้อมูล (อ่านอย่างเดียว, environment uv ชั่วคราว, ไม่ต้องรอ D-001) | evidence report และไม่มีการส่งคำสั่งใดๆ | Standard |
| 1b | ตัดสิน D-001 | Codex `$adversarial-design-review` พร้อมหลักฐานจาก SPIKE-001 แล้วเจ้าของรับหรือปฏิเสธ D-001 | ADR เปลี่ยนเป็น accepted หรือ rejected | – |
| 2 | SLICE-R1 | วงวิจัยครบ: snapshot → validation → H001 → golden tests → backtest + costs → registry → รายงานเทียบ random-entry | เจ้าของตัดสิน go/stop/insufficient จาก 3 รายงาน (ข้อมูล, golden, registry) | Standard |
| 3 | SLICE-E1 | วง Demo ครบ: risk gate → คำสั่งพร้อม SL → MT5 ยืนยัน → journal → ปิด → reconcile → restart recovery | round trip ที่ MT5 ยืนยัน พร้อม negative cases | Standard + external-action controls |
| 4 | OPS-1 | รัน Demo แบบไม่ต้องเฝ้า: scheduler, alert, backup/restore | ซ้อม restore และ alert จริงผ่าน | Standard/High |
| – | เงินจริง | อยู่นอกขอบเขต | ต้องมี SPEC รุ่นใหม่, threat model, ADR และ controls ระดับ High | High |

SLICE-E1 เริ่มได้เมื่อ (ก) มี strategy version ที่ผ่าน R1 หรือ (ข) เจ้าของอนุมัติ "engineering test" ด้วย volume ขั้นต่ำและระบุชัดว่าไม่ใช่การทดสอบ edge

## 11. สิ่งที่ตั้งใจยังไม่ทำ และ trigger ที่จะกลับมาพิจารณา

| ยังไม่ทำ | กลับมาพิจารณาเมื่อ |
|---|---|
| Web dashboard / ดูผลจากที่อื่น | E1 รันแบบไม่เฝ้า และเจ้าของต้องดูจากนอกเครื่อง |
| Database server ภายนอก (เช่น Supabase) | ต้องแชร์ข้อมูลข้ามเครื่องหรือ dashboard ต้องใช้ |
| VPS | ต้องการ uptime เกินกว่าเครื่องเจ้าของ (Windows VPS; ถ้าเป็น Linux ต้องทบทวน D-001) |
| News/AI classification | ลงทะเบียนเป็นสมมติฐานแยกพร้อม evals (บท 30) |
| ML models | ต้องชนะ baseline แบบง่ายภายใต้การทดสอบที่ยุติธรรม (บท 34) |
| MQL5 EA | ต้องการ logic ฝั่ง terminal ที่ Python ทำแทนไม่ได้ |

## 12. ความเสี่ยงและสิ่งที่ยังไม่รู้

| ID | สิ่งที่ยังไม่รู้ | ผลถ้าผิด | วิธีพิสูจน์ |
|---|---|---|---|
| U1 | แพ็กเกจ `MetaTrader5` attach กับ terminal ของโบรกเกอร์ที่เลือกบนเครื่องนี้ได้จริง | ทั้งทางเลือก A ใช้ไม่ได้ | SPIKE-001 |
| U2 | timestamp จาก MT5 Python API เป็น UTC (ตามเอกสาร) หรือเวลา server (ตามรายงานในฟอรัม) และพฤติกรรมช่วง DST | สัญญาณผิดเวลา, look-ahead | SPIKE-001 (AC-04, AC-05) |
| U3 | ข้อมูลย้อนหลัง XAU/USD (M1/ticks) จากโบรกเกอร์ลึกและครบพอหรือไม่ | วิจัยได้ไม่พอ หรือต้องหาแหล่งอื่น (มีเรื่อง license) | SPIKE-001 |
| U4 | spread และต้นทุนจริงใกล้กับ cost model แค่ไหน | backtest สวยเกินจริง | R1 (cost model) และ E1 (วัดจริง) |
| U5 | เครื่องเจ้าของเปิดต่อเนื่องได้ไหม (sleep, update, reboot) | Demo runner หยุดกลางทาง | OPS-1 |
| U6 | พฤติกรรม `order_send`: timeout, retcode, filling mode ของโบรกเกอร์ | ส่งซ้ำหรือสถานะค้าง | E1 (negative cases) |

## 13. Architecture fitness checks ที่วางแผนไว้

- `tests/architecture/` (เขียนโดย test author, locked): ตรวจกฎ import ตามตารางในข้อ 8 ด้วย AST (ไม่ต้องเพิ่ม dependency) เช่น ห้าม import `MetaTrader5` นอก `broker/mt5` และ `strategy` import ได้เฉพาะ `core` และ `timebase`
- CI ที่มีอยู่แล้ว: `control-gate` (pull_request_target ใช้ตัวตรวจจาก base revision และไม่รันโค้ดจาก PR) ตรวจ locked paths, สมมติฐาน immutable และ registry append-only ทีละ commit; `ci` รัน self-tests และ red-flag scan
- ตั้งแต่ E1: negative test ว่า trade mode ที่ไม่ใช่ Demo ทำให้การส่งคำสั่งถูกปฏิเสธเสมอ
