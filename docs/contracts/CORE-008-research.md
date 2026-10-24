# TASK CORE-008 — `research`: registry, runner, random-entry baseline, robustness และการประเมินตามเงื่อนไขของ H001 แบบ pure

Version v1.5 (v1 ร่าง 2026-10-24 12:xx → v1.1 ตอบ contract review r1 F1–F17 → v1.2 ตอบ r2 F9, F18–F32 → v1.3 ตอบ r3 F33–F42 → v1.4 ตอบ r4 F43–F46 → v1.5 ตอบ r5 F47 ดูหัวข้อ "Answers to contract reviews") · Owner เจ้าของ repository · Parent `docs/architecture.md` ข้อ 7 (backtest → research runner + random-entry baselines → registry JSONL), ข้อ 8 แถว `research`, ข้อ 10 แถว 2 (SLICE-R1), เกณฑ์ "R1 first experiment" · H001 ข้อ 3, 4, 5, 7, 8, 9 · HANDBOOK-CORE §15 · ต่อจาก CORE-007 (`backtest.run`, `simulate_trade`) · Tier **Standard** · Branch `feat/CORE-008-research`
Status: **approved by delegation 2026-10-24 14:3x** — ร่างและอนุมัติแทนโดย Claude ภายใต้อำนาจที่เจ้าของมอบไว้ 2026-10-24 ~07:0x ("ทำให้เสร็จทั้งหมดเลย", "มึงตัดสินไปเลย… เอา recommanded ทุกอัน") และคำสั่ง ~13:5x "ทำให้เสร็จทั้งหมด" · ผู้ตรวจอิสระ (subagent) อ่าน contract แทนเจ้าของ 6 รอบ: r1 ไม่พร้อม 17 findings → v1.1 · r2 ไม่พร้อม (F9 ค้าง + F18–F32) → v1.2 · r3 ไม่พร้อม (F33–F42) → v1.3 · r4 ไม่พร้อม (F43–F46 Low) → v1.4 · r5 ตรวจแคบ: F47 Low → v1.5 · r6 ตรวจแคบ: **"Ready for test authoring: yes", findings open 0** · เรื่องใน Plan ข้อ 5 (ก)–(ฉ) เจ้าของตัดสินเองก่อน SLICE-R1 (ไม่อนุมัติแทน) · **เจ้าของ veto หรือแก้ acceptance ได้ทุกเมื่อก่อน merge**
Hypothesis (research tasks): H001 (`docs/hypotheses/H001-m15-momentum-breakout.md`, committed `0c392a9`) · เขียนเครื่องมือเท่านั้น **ไม่รันการทดลองกับข้อมูลจริงและไม่เขียน `research/registry/` จริง** (ห้ามก่อน ENV-1 และ SLICE-R1) · tests ใช้ข้อมูลสังเคราะห์และไฟล์ใน `tmp_path`

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation: no
- Q2 real money: no — ไม่มีเส้นทางส่งคำสั่ง
- Q3 new storage/transfer of personal or confidential data: no — registry เก็บพารามิเตอร์ ต้นทุน และผลการทดลอง ไม่มีข้อมูลบัญชี
- Q4 schema change or deletion of real data: no วันนี้ (ยังไม่มีข้อมูลจริง) · หมายเหตุ: schema ของ registry จะแก้ไม่ได้หลัง commit แรกของ R1 เพราะไฟล์เป็น append-only (`scripts/controls/rules.mjs`) จึงต้องถูกตั้งแต่ contract นี้
- Q5 hard-to-reverse external effect: no
- Q6 changes controls: no — ไม่แตะ `control-gate` หรือ hooks · tests ที่ล็อกเข้า repo ผ่าน patch ตาม D-006

เป็น Standard เพราะคำตัดสิน go/stop/insufficient ของ H001 คำนวณจากโมดูลนี้

## Goal / user outcome (Thai)
มีโมดูล `sochron.research` ที่ทำให้วงวิจัยของ SLICE-R1 รันได้โดยตัวเลขทุกตัวมาจากสคริปต์ที่บันทึกตัวเอง:
- **registry:** ทุกการรันถูกบันทึกลงไฟล์ JSONL แบบเพิ่มบรรทัดอย่างเดียว: บรรทัด "started" ก่อนเริ่มคำนวณ แล้วบรรทัดผล "ok" หรือ "failed" · การรันที่ถูกขัดกลางทางยังเหลือบรรทัด started และนับงบ · record มีพารามิเตอร์, version ของโค้ด, commit, ชุดข้อมูล, ค่าต้นทุนทุกค่า, equity เริ่มต้น, sizer, rollover, กฎเวลา และผลสรุป
- **runner:** รัน variant ผ่าน `backtest.run` แล้วลง registry อัตโนมัติ · ปฏิเสธเมื่อเกินงบของ H001 ข้อ 4 · ปฏิเสธข้อมูลตั้งแต่ cutoff ของ holdout (2025-01-01 UTC) เป็นชั้นป้องกันเสริม
- **random-entry baseline:** 1,000 รันสุ่มต่อ variant ตาม H001 ข้อ 7 ด้วย seed ที่ได้จาก record ของ variant (เลือก seed เองไม่ได้) รันซ้ำได้ผลเดิม
- **robustness:** สร้างเพื่อนบ้าน ±10% ทีละพารามิเตอร์เฉพาะพารามิเตอร์ที่กฎของโครงสร้างนั้นใช้ (D9)
- **การประเมิน:** ตรวจเงื่อนไขทุกข้อของ H001 ข้อ 8 จาก record ใน registry แล้วให้ go/stop/insufficient พร้อมค่าจริงของแต่ละข้อ · ถ้าข้อมูลจบก่อน cutoff ของ holdout รายงานว่าเป็น **screen ไม่ใช่คำตัดสินของ H001**
- **รายงาน:** ข้อความ Markdown ภาษาไทยที่เจ้าของอ่านเอง: จำนวนการรันเทียบงบ, ผลแต่ละเงื่อนไขของแต่ละโครงสร้าง, การแจกแจงของ baseline, ข้อจำกัดที่ต้องรายงาน
- pure ยกเว้นการอ่าน/เขียนไฟล์ registry ที่เดียว · ไม่มีนาฬิกา · สุ่มด้วย `random.Random(seed)` เท่านั้น

## Current behavior and evidence (revision)
ยังไม่มี `src/sochron/research` · `research/registry/` ยังไม่มีไฟล์ · `scripts/controls/rules.mjs` ล็อก `research/registry/*.jsonl` เป็น append-only ("written only by the experiment runner") และ `control-gate` ตรวจทุก commit · `backtest` (CORE-007 v1.5) ให้ `run` และ `simulate_trade` · `strategy.decide` ตรวจ invalidation ในฟังก์ชัน private `_invalid` · การประเมินบน holdout รันบน acquisition host (architecture ข้อ 6.1, 158) ซึ่งยังไม่มี (ENV-1)

## Scope
- In scope: แพ็กเกจ `sochron.research` · ฟังก์ชัน public ใหม่ `strategy.entry_blockers` แทน `_invalid` (D1) · unit tests · acceptance, golden และการขยาย architecture test ให้ครอบ `sochron.research` โดยผู้เขียน tests ผ่าน patch D-006 · หลักฐาน · handoff
- Exclusions: การรันกับข้อมูลจริง · การเขียน `research/registry/` จริง · การรันบน holdout และการลง registry ของรันเหล่านั้น (contract ของ acquisition host หลัง ENV-1: guard ของ contract นี้ยังอยู่) · กฎการเลือกชุดพารามิเตอร์บน validation (H001 ไม่ได้ระบุ: เจ้าของกำหนดก่อน SLICE-R1) · การรวมคำตัดสินของ 3 โครงสร้าง (เจ้าของกำหนดก่อน SLICE-R1) · Deflated Sharpe / PBO · ตัวเชื่อม sizer จริง (ประกอบใน `app`) · การอ่าน Parquet/snapshot
- Allowed files: `src/sochron/research/**`, `src/sochron/strategy/h001.py` และ `src/sochron/strategy/__init__.py` (เฉพาะ D1), `tests/unit/research/**`, `docs/evidence/CORE-008.md`, `docs/handoff/CORE-008.md`, `PROGRESS.md` · โดยผู้เขียน tests ผ่าน patch: `tests/acceptance/CORE-008/**`, `tests/golden/CORE-008/**`, `tests/architecture/**`
- Must not touch: `research/registry/**`, `src/sochron/{timebase,core,data,costs,risk,backtest}/**`, ส่วนอื่นของ `src/sochron/strategy/**`, `docs/hypotheses/**`, `docs/architecture.md`, `.claude/**`, `.github/**`, `scripts/controls/**`, `AGENTS.md`, `CLAUDE.md`, `pyproject.toml`, `uv.lock`

## Inputs / outputs / errors (contract)
ตัวเลขเป็น `Decimal` คำนวณใน `sochron.costs.CONTEXT` (precision 28, ROUND_HALF_EVEN) · ค่าเฉลี่ย = ผลรวมตามลำดับที่กำหนด แล้วหารด้วยจำนวน ใน CONTEXT · ชนิดผิด (float, bool, subclass, None ที่ต้องมีค่า) → `TypeError` · ค่าผิดโดเมน → `ResearchError` (subclass ของ `ValueError`) หรือ subclass ของมัน · error จาก `backtest`, `costs`, `strategy`, `timebase` และ sizer ส่งต่อโดยไม่ห่อ (object เดิม)

```text
sochron.strategy (เปลี่ยนใน CORE-008, D1)
  entry_blockers(row: IndicatorRow, next_open_utc: datetime) -> tuple[str, ...]
      # row ต้องเป็น IndicatorRow พอดี, next_open_utc เป็น datetime พอดี (TypeError) และมี timezone (StrategyError)
      # คืนเหตุผลตามลำดับ outside_window, spread_filter, spread_unknown, atr_zero, data_flag, warmup (ว่าง = เข้าได้)
      # decide เรียกฟังก์ชันนี้ผ่านชื่อในโมดูล h001 เพื่อหาเหตุผลของ skip · `_invalid` ถูกลบ · STRATEGY_VERSION ไม่เปลี่ยน

sochron.research
  RESEARCH_VERSION = "research-v1"
  HOLDOUT_CUTOFF_UTC = datetime(2025, 1, 1, tzinfo=UTC)               # H001 ข้อ 5
  ResearchError(ValueError) · BudgetExceeded(ResearchError) · HoldoutRefused(ResearchError)
  Purpose = Literal["select", "robustness", "stress", "long_only", "random_entry"]
  USED_PARAMETERS = {"A": ("f", "s", "n", "theta", "k"), "B": ("n", "N", "M", "k"), "C": ("f", "s", "n", "N", "M", "k")}
  BASELINE_RUNS = 1000                                                    # H001 ข้อ 7 (ไม่มี argument runs)
  Dataset (frozen): snapshot_id: str, manifest_sha256: str, period_start_utc: datetime, period_end_utc: datetime, m1_bars: int
  Summary (frozen): trades: int, expectancy_r: Decimal | None, max_drawdown_r: Decimal, net_money: Decimal,
                    long_trades: int, long_expectancy_r: Decimal | None, short_trades: int, short_expectancy_r: Decimal | None,
                    top5_removed_expectancy_r: Decimal | None, expectancy_by_year: tuple[tuple[int, Decimal], ...],
                    ambiguous_trades: int, flagged_trades: int, gap_fills: int, end_of_data_trades: int
  BaselineSummary (frozen): runs: int, trades_per_run: int, seed: int, mean_r: Decimal, p05_r: Decimal, p50_r: Decimal,
                    p95_r: Decimal, variant_mean_hold_m1: Decimal, variant_median_hold_m1: int,
                    baseline_mean_hold_m1: Decimal, baseline_median_hold_m1: int
  RunRecord (frozen): ทุก field ในตารางของ "registry" ยกเว้น run_id · `run_id` เป็น property ที่คำนวณจากเนื้อหา ·
                    `line()` คืนไบต์ canonical ของบรรทัด (รวม run_id และ LF)
  append_record(path: Path, record: RunRecord) -> None
  read_records(path: Path) -> tuple[RunRecord, ...]
  summarize(result: backtest.Result, rule: TimeRule) -> Summary
  percentile(values: Sequence[Decimal], q: Decimal) -> Decimal                    # nearest rank (D6)
  run_variant(m1, m15, params, model, sizer, equity, rule, rollover, *, purpose, dataset, code_commit, sizer_label,
              registry: Path, base_run_id: str | None = None) -> tuple[RunRecord, backtest.Result]
  BaselineResult (frozen): expectancies_r: tuple[Decimal, ...], summary: BaselineSummary, record: RunRecord
  random_entry_baseline(m1, m15, params, model, sizer, equity, rule, rollover, variant: backtest.Result, *,
                        base_run_id: str, dataset, code_commit, sizer_label, registry: Path) -> BaselineResult
  Neighbour (frozen): parameter: str, direction: Literal["-", "+"], value: str, params: H001Params | None
  neighbours(params: H001Params) -> tuple[Neighbour, ...]                         # D9
  Check (frozen): name: str, value: str, threshold: str, passed: bool
  Evaluation (frozen): variant: str, base_run_id: str, dataset: Dataset, screen: bool,
                       verdict: Literal["go", "stop", "insufficient"], checks: tuple[Check, ...]
  evaluate(base: RunRecord, stress: RunRecord | None, long_only: RunRecord | None, random_entry: RunRecord | None,
           robustness: Sequence[RunRecord]) -> Evaluation          # None/ว่างได้เสมอ: แถวนั้นไม่ผ่าน (F27, F34)
  render_report(records: Sequence[RunRecord], evaluations: Mapping[str, Evaluation], *, hypothesis: str = "H001") -> str
```

### Dataset
- `snapshot_id` str ไม่ว่าง · `manifest_sha256` 64 ตัวอักษร hex ตัวเล็ก · `period_start_utc` < `period_end_utc` ทั้งคู่เป็น datetime พอดี, offset 0, ไม่มี microsecond (`period_end_utc` เป็นจุดสิ้นสุดแบบไม่รวม) · `m1_bars` int ≥ 1 · ตรวจตอนสร้าง (`__post_init__`): ชนิดผิด → `TypeError`, ค่าผิด → `ResearchError`
- `run_variant` และ `random_entry_baseline` ต้องได้ `dataset.m1_bars == len(m1)` และทุก M1 มี `period_start_utc ≤ time_utc < period_end_utc` ไม่ตรง → `ResearchError`

### registry (D12)
**Field ของ RunRecord** (ตรวจตอนสร้างใน `__post_init__`: ชนิด → `TypeError`, ค่า → `ResearchError` · Summary, BaselineSummary และ Dataset ตรวจชนิดของตัวเองแบบเดียวกัน)
**สิ่งที่ `RunRecord.__post_init__` ตรวจ (F36) ครบรายการ:** ชนิดของทุก field · status, purpose และ variant อยู่ในชุดที่กำหนด · รูปแบบ null ตามตารางของ status และ purpose · seq ≥ 1 และ started_seq < seq สำหรับ ok/failed · code_commit 40 hex ตัวเล็ก, base_run_id 64 hex ตัวเล็ก · hypothesis เป็น str ASCII ไม่ว่าง (ค่าใดก็ได้ ไม่บังคับ "H001") · params มีชื่อ f, s, n, theta, N, M, k ตามลำดับนี้และค่าเป็น str · cost_model มีชื่อตามลำดับ field ของ CostModel (ไม่รวม provenance) · cost_provenance เรียงตามชื่อ · equity เป็น Decimal finite > 0 · sizer_label เป็น str ASCII ไม่ว่าง (F46) และ error เป็น ASCII · rollover_at รูป "HH:MM" · sides ตาม purpose · สำหรับ random_entry: runs = 1000 และ seed = `int(base_run_id[:15], 16)` · นอกนั้นไม่ตรวจ (เช่น ไม่ตรวจว่า params เป็น H001Params ที่ valid: runner ตรวจตอนรัน)

| field | ชนิด / ค่า | started | ok | failed |
|---|---|---|---|---|
| seq | int ≥ 1 (ลำดับบรรทัดใน registry) | มี | มี | มี |
| run_id | **property ไม่ใช่ argument:** 64 hex ตัวเล็ก = SHA-256 ของ record ที่ไม่มี run_id (ด้านล่าง) | มี | มี | มี |
| status | "started" \| "ok" \| "failed" | started | ok | failed |
| started_seq | int: seq ของบรรทัด started ที่คู่กัน | null | มี | มี |
| hypothesis | "H001" | มี | มี | มี |
| purpose | Purpose | มี | มี | มี |
| variant | "A" \| "B" \| "C" (= `H001Params.variant`) | มี | มี | มี |
| params | list ของ [ชื่อ, str(ค่า)] ตามลำดับ field ของ H001Params ไม่รวม variant: f, s, n, theta, N, M, k | มี | มี | มี |
| base_run_id | run_id ของ record select (status ok) ที่เป็นฐาน | null สำหรับ select · มีสำหรับ purpose อื่น | เหมือน started | เหมือน started |
| strategy_version, backtest_version, research_version | str ของค่าคงที่ของแต่ละโมดูล | มี | มี | มี |
| code_commit | 40 hex ตัวเล็ก (ผู้เรียกส่ง): commit ล่าสุดที่แตะโค้ด (เช่น `git log -1 --format=%H -- src`) ไม่ใช่ HEAD · commit ที่เพิ่มแค่ registry หรือเอกสารจึงไม่เปลี่ยนค่านี้ | มี | มี | มี |
| dataset | object ของ Dataset | มี | มี | มี |
| cost_model | list ของ [ชื่อ, str(ค่า)] ทุก field ของ CostModel ตามลำดับ field ไม่รวม provenance (รวม stress_factor) | มี | มี | มี |
| cost_provenance | list ของ [ชื่อ field, status] เรียงตามชื่อ | มี | มี | มี |
| equity | str(Decimal) equity เริ่มต้น | มี | มี | มี |
| sizer_label | str ไม่ว่าง ASCII (ผู้เรียกส่ง) | มี | มี | มี |
| rollover_zone, rollover_at | str, "HH:MM" | มี | มี | มี |
| time_rule_server, time_rule_version | `TimeRule.server`, `TimeRule.version` | มี | มี | มี |
| sides | list เรียงตามตัวอักษรของ sides ที่ใช้: long_only = ["long"] · purpose อื่นทั้งหมดรวม random_entry = ["long","short"] | มี | มี | มี |
| seed, runs | int: seed ตาม baseline ข้อ 5, runs = 1000 | เฉพาะ random_entry (อื่นเป็น null) | เหมือน started | เหมือน started |
| error | `f"{type(e).__name__}: {e}"` แล้วแทนอักษรที่ไม่ใช่ ASCII ด้วย `?` (ข้อความว่างให้ เช่น `"KeyboardInterrupt: "`) | null | null | มี |
| summary | object ของ Summary | null | มี ยกเว้น random_entry (null) | null |
| baseline | object ของ BaselineSummary | null | มีเฉพาะ random_entry | null |

**ชนิด Python ของแต่ละ field** (คอลัมน์ "ชนิด / ค่า" ข้างบนบอกรูปใน JSON): seq, started_seq, seed, runs → `int` (หรือ None) · run_id, status, hypothesis, purpose, variant, base_run_id, *_version, code_commit, sizer_label, rollover_zone, rollover_at ("HH:MM"), time_rule_server, time_rule_version, error → `str` (หรือ None) · params, cost_model, cost_provenance → `tuple[tuple[str, str], ...]` · sides → `tuple[str, ...]` เรียงแล้ว · equity → `Decimal` · dataset → `Dataset` · summary → `Summary | None` · baseline → `BaselineSummary | None` · `read_records` คืนชนิดเหล่านี้ (list → tuple, string ของ field ที่เป็น Decimal → `Decimal`) จึงได้ record ที่เท่ากับตอนเขียนทั้งค่าและชนิด
- tests สร้าง record ด้วยตัวสร้างของ RunRecord โดยไม่ต้องคำนวณ run_id เอง · ตัวอย่างบังคับข้างล่างเป็น oracle ของ `run_id` และ `line()`

**รูปแบบ canonical:** `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` แล้ว encode เป็น ASCII · Decimal → `str(ค่า)` ตามที่เป็น ไม่ normalize · datetime → `"%Y-%m-%dT%H:%M:%SZ"` · tuple/list → list · dataclass ซ้อน (Dataset, Summary, BaselineSummary) → object ที่ key เป็นชื่อ field · `expectancy_by_year` → list ของ [ปี (int), str(ค่า)] เรียงตามปี · None → `null` · bool → `true`/`false`
- `run_id` = SHA-256 hex ของไบต์ canonical ของ record ทั้งหมด **ยกเว้น key `run_id`** (ไม่มี LF) · บรรทัด = ไบต์ canonical ของ record ทั้งหมด (รวม run_id) + `b"\n"`
- **ตัวอย่างบังคับ (normative):** record started ของ select, variant B ค่าตั้งต้น, H001_COSTS, Dataset("SYN-0001", "a"×64, 2023-01-02T00:00:00Z, 2023-01-07T00:00:00Z, 7200), code_commit "0123456789abcdef0123456789abcdef01234567", equity 10000, sizer_label "fixed-0.02", Rollover America/New_York 17:00, TimeRule ของ Exness-MT5Trial14, sides long+short, seq 1 → `run_id = e35809037fb2878f02919adc04332a45e841ac04b54354f5548b3f88732d314f` · บรรทัดยาว 1,671 ไบต์ รวม LF · SHA-256 ของบรรทัด (รวม LF) = `f50c0bcb139bc587cef4882c8650e34cfa714df8ac51721eab20f23140533f44` · บรรทัดเต็ม:

```text
{"backtest_version":"backtest-v1","base_run_id":null,"baseline":null,"code_commit":"0123456789abcdef0123456789abcdef01234567","cost_model":[["symbol","XAUUSDm"],["point","0.001"],["contract_size","100"],["volume_min","0.01"],["volume_step","0.01"],["volume_max","200"],["spread_fallback_points","240"],["commission_per_lot_per_side","0"],["slippage_points_per_side","50"],["swap_long_points_per_night","-503.8"],["swap_short_points_per_night","0"],["triple_swap_weekday","2"],["stress_factor","1"]],"cost_provenance":[["commission_per_lot_per_side","assumed"],["contract_size","measured"],["point","measured"],["slippage_points_per_side","assumed"],["spread_fallback_points","measured"],["swap_long_points_per_night","spec"],["swap_short_points_per_night","spec"],["triple_swap_weekday","assumed"],["volume_max","measured"],["volume_min","measured"],["volume_step","measured"]],"dataset":{"m1_bars":7200,"manifest_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","period_end_utc":"2023-01-07T00:00:00Z","period_start_utc":"2023-01-02T00:00:00Z","snapshot_id":"SYN-0001"},"equity":"10000","error":null,"hypothesis":"H001","params":[["f","16"],["s","64"],["n","20"],["theta","0.50"],["N","96"],["M","48"],["k","2.0"]],"purpose":"select","research_version":"research-v1","rollover_at":"17:00","rollover_zone":"America/New_York","run_id":"e35809037fb2878f02919adc04332a45e841ac04b54354f5548b3f88732d314f","runs":null,"seed":null,"seq":1,"sides":["long","short"],"sizer_label":"fixed-0.02","started_seq":null,"status":"started","strategy_version":"H001-v1","summary":null,"time_rule_server":"Exness-MT5Trial14","time_rule_version":"1","variant":"B"}
```

**append_record (D12, F3, F6):** path ต้องลงท้าย `.jsonl` · อ่านไฟล์เดิมแบบไบต์ (`read_records` ต้องผ่าน) · `record.seq` ต้องเท่ากับจำนวน record เดิม + 1 · record ok/failed ต้องอ้าง `started_seq` ของบรรทัด started ที่มี identity เดียวกัน (ทุก field ยกเว้น seq, run_id, status, started_seq, error, summary, baseline) และยังไม่มีบรรทัดผลอื่น · เขียนด้วย `open(path, "ab")` และ `write` ครั้งเดียวของบรรทัดทั้งบรรทัด แล้ว `flush` · ไม่ตรงเงื่อนไข → `ResearchError` และไฟล์ไม่เปลี่ยน · error ของระบบไฟล์ (เช่น `OSError` ดิสก์เต็ม) ส่งต่อตรงๆ
**read_records (F3, F6):** อ่านเป็นไบต์ แยกด้วย `b"\n"` · ไฟล์ที่ยังไม่มี → tuple ว่าง · ไฟล์ว่าง → tuple ว่าง · ไบต์หลัง `\n` ตัวสุดท้าย (บรรทัดขาด) → `ResearchError` ที่บอก byte offset ของบรรทัดนั้น · `b"\r"`, ไบต์ที่ไม่ใช่ ASCII, JSON เสีย, ไม่ใช่ canonical (เข้ารหัสใหม่แล้วไม่ได้ไบต์เดิม), field ขาดหรือเกิน, ชนิด/ค่าผิด, seq ไม่เป็น 1, 2, 3, …, run_id ไม่ตรง, ok/failed ที่อ้าง started ไม่ถูก → `ResearchError` ที่บอกเลขบรรทัด
**การกู้บรรทัดขาด (สำหรับเจ้าของ):** โค้ดไม่แก้ไฟล์ registry เอง · เมื่อ `read_records` รายงานบรรทัดขาด เจ้าของตรวจว่าไบต์หลัง LF สุดท้ายไม่อยู่ใน commit ใด (`git diff` ของไฟล์แสดงเฉพาะส่วนนั้น) แล้วตัดเฉพาะไบต์เหล่านั้นออกเอง และบันทึกเหตุการณ์ใน PROGRESS · ถ้าส่วนนั้นถูก commit แล้วห้ามแก้ (`control-gate` ปฏิเสธ) ต้องเปิดงานแก้ใหม่ · agent ห้ามแก้ไฟล์นี้ (locked)

### runner (D10, D11)
`run_variant` ตามลำดับ:
1. **holdout guard (ก่อนการตรวจอื่นทั้งหมด, F23):** ถ้า m1 และ m15 เป็น sequence ของวัตถุที่มี `time_utc` (M1) และ `.bar.time_utc` (M15) ให้หา M1 หรือ M15 ใดที่ `time_utc ≥ HOLDOUT_CUTOFF_UTC` · หรือถ้า `dataset` เป็น Dataset ที่ `period_end_utc > HOLDOUT_CUTOFF_UTC` → `HoldoutRefused` (input ที่อ่านเวลาไม่ได้ปล่อยให้ข้อ 2 ปฏิเสธ)
2. ตรวจชนิดและค่าทุก argument (รวม Dataset ข้างบน, `code_commit` 40 hex ตัวเล็ก, `sizer_label`) · purpose ต้องเป็น select, robustness, stress หรือ long_only (random_entry → `ResearchError`) · `cost_model` ของ model ต้องมี stress_factor เป็น string `"1"` พอดี ยกเว้น stress ที่ต้องเป็น `"2"` พอดี (เทียบแบบ string ของ record, F19) · sides ที่ใช้: long_only = {"long"} อื่นๆ = {"long", "short"}
3. **ตรวจ input แบบ CORE-007 (F18):** ตรวจ M1/M15 ชุดเดียวกับ baseline ข้อ 2 (`ResearchError`) ก่อนเขียนอะไร เพื่อให้ข้อมูลเสียไม่กินงบ
4. **ฐาน (F9, F19):** select ต้องไม่มี base_run_id · purpose อื่นต้องมี base_run_id ที่ชี้ record **ok** ของ purpose select, hypothesis และ variant เดียวกันใน registry · ทุก field ที่ `evaluate` เทียบต้องเท่ากับของฐานแบบ string ของ record: dataset, code_commit, sizer_label, equity, rollover_zone, rollover_at, time_rule_server, time_rule_version และ cost_model ทุกคู่ยกเว้น stress_factor · params (string ของ record): robustness ต้องเท่ากับ params ของเพื่อนบ้าน valid ตัวหนึ่งของ `neighbours(params ของฐาน)` · stress และ long_only ต้องเท่ากับของฐาน · ไม่ตรง → `ResearchError`
5. **งบ (D10, F9, F18):** นับจากบรรทัด started ของ hypothesis เดียวกันใน registry
   - **ฐานเดียวต่อโครงสร้าง:** บรรทัด started แรกของ purpose ใดๆ ที่ไม่ใช่ select (robustness, stress, long_only, random_entry) ของ variant หนึ่งกำหนดฐานของ variant นั้น · ฐานอื่น → `BudgetExceeded`
   - **setup เดียวต่อ hypothesis ต่อไฟล์ registry (F33):** บรรทัด started แรกของ hypothesis ในไฟล์กำหนด setup = code_commit, sizer_label, equity, rollover_zone, rollover_at, time_rule_server, time_rule_version, cost_model ทุกคู่ยกเว้น stress_factor และ cost_provenance · บรรทัด started ใหม่ที่ setup ต่างจากนี้ → `BudgetExceeded` · ดังนั้นสิ่งที่เปลี่ยนได้ระหว่างรันมีแค่ params, dataset และ purpose (กับ stress_factor ของ stress) · แก้โค้ดหลังบรรทัด started แรกต้องเริ่มไฟล์ registry ใหม่ (เจ้าของบันทึกเหตุผล)
   - **identity ของรัน** = ทุก field ยกเว้น seq, run_id, status, started_seq, error, summary, baseline (เท่ากับ identity ที่ `append_record` ใช้จับคู่ ok/failed กับ started, F35) · **รันซ้ำ:** identity ที่มีบรรทัด ok แล้ว → `BudgetExceeded` · identity ที่มีแต่ started (ไม่มีผล หรือ failed) รันซ้ำได้ เพราะผลกำหนดได้จาก input จึงไม่ได้ทางเลือกใหม่
   - select: จำนวน params ที่ต่างกันของ variant ≤ 6 (params เดิมบน dataset อื่นไม่เพิ่มยอด)
   - robustness: บรรทัด started ต่อ variant ≤ 14 (H001 ข้อ 4) · ok ได้ไม่เกินหนึ่งต่อเพื่อนบ้าน
   - stress, long_only: ok ได้ไม่เกินหนึ่งต่อ variant (ตามกฎรันซ้ำ)
   - รวมทั้ง hypothesis: ผลรวมต่อ variant ของจำนวน params select ที่ต่างกัน (คีย์ = variant + params: ค่าตั้งต้นของ A, B และ C จึงนับเป็น 3 ชุด, F43) + บรรทัด started ของ robustness + บรรทัด started ของ stress ≤ 63 (H001 ข้อ 4 · long_only และ random_entry ไม่นับ) · รันซ้ำนับด้วย
   - เกินข้อใด → `BudgetExceeded`
6. append บรรทัด **started** (seq = จำนวน record เดิม + 1)
7. `backtest.run(m1, m15, params, model, sizer, equity, rule, rollover, sides=…)`
8. สำเร็จ → append บรรทัด **ok** พร้อม `summarize(result, rule)` แล้วคืน (record ok, result) · **exception ใดๆ หลังข้อ 6** (ในข้อ 7, ใน `summarize`, ตอนสร้าง record ok หรือตอน append บรรทัด ok · รวม `BaseException` เช่น `KeyboardInterrupt` และ `OSError` ดิสก์เต็ม, F39) → พยายาม append บรรทัด **failed** (`error`) แล้ว raise object เดิม · ถ้าการ append บรรทัด failed ก็ล้มด้วย ให้ raise exception เดิม (บรรทัด started ที่ไม่มีผลถูกรายงานเป็น interrupted และรันซ้ำได้)
- ข้อ 1–5 ไม่เขียน registry
- **seam สำหรับ tests (F39):** `run_variant` และ `random_entry_baseline` เขียน registry ผ่าน `registry.append_record` ของโมดูล `sochron.research.registry` โดยหาชื่อตอนเรียกใช้ (เช่น `from . import registry` แล้ว `registry.append_record(...)`) · tests แทน `sochron.research.registry.append_record` ด้วย monkeypatch ได้ (เช่น ให้การ append บรรทัด ok ล้มด้วย `OSError`)
- **ผู้เขียนคนเดียวต่อไฟล์ (F42):** หนึ่งไฟล์ registry มีโปรเซสของ runner เขียนได้ครั้งละหนึ่งโปรเซสเท่านั้น (เงื่อนไขของ R1) · โค้ดไม่ล็อกไฟล์ข้ามโปรเซส

### summarize และสถิติ (D6, D7, D8, F14)
- ลำดับไม้ = ลำดับใน `result.trades` · expectancy = ผลรวม `r` ÷ จำนวน · ไม่มีไม้ → None (ค่าอื่นที่เป็นค่าเฉลี่ยก็เป็น None, max_drawdown_r = `Decimal("0")`, net_money = `Decimal("0")`, ตัวนับเป็น 0, expectancy_by_year ว่าง)
- max_drawdown_r = ค่ามากสุดของ (จุดสูงสุดของผลรวมสะสมที่ผ่านมา − ผลรวมสะสม) โดยผลรวมสะสมเริ่มที่ 0 ก่อนไม้แรก · net_money = ผลรวม `net_money`
- long/short: นับและ expectancy แยกตาม `trade.side` · top5_removed_expectancy_r = expectancy หลังตัด 5 ไม้ที่ r สูงสุด (ถ้า r เท่ากัน ตัดไม้ที่มาก่อน) · มีไม้ ≤ 5 → None
- expectancy_by_year = ปี UTC ของ `timebase.to_utc(entry_time_raw, rule)` เฉพาะปีที่มีไม้ เรียงตามปี
- ambiguous_trades = จำนวนไม้ที่ `ambiguous` · flagged_trades = จำนวนไม้ที่ `data_flags` ไม่ว่าง · gap_fills = จำนวนไม้ที่ `data_flags` มี "unexpected_gap" · end_of_data_trades = จำนวนไม้ที่ `exit_reason == "end_of_data"`
- `percentile(values, q)` = nearest rank: เรียงจากน้อยไปมาก แล้วเอาค่าลำดับที่ ⌈q·n⌉ (นับจาก 1) · q เป็น Decimal ใน (0, 1] · values ว่าง → `ResearchError`

### random-entry baseline (D1–D5, D13)
1. holdout guard ก่อน (ข้อ 1 ของ runner: `HoldoutRefused`) · แล้วตรวจชนิด/ค่า, Dataset, ฐาน (ข้อ 4 ของ runner: record ok ของ select, ทุก field ที่ evaluate เทียบและ params เท่ากับฐานแบบ string, stress_factor `"1"`) · variant ต้องเป็นผลของฐาน: `summarize(variant, rule) == summary ของฐาน` ทุก field (F24) · ข้อนี้ตรวจเฉพาะความเท่ากันของ summary และเวลาของไม้ (ข้อ 2) ไม่ได้รัน backtest ใหม่ ดังนั้น tests สร้าง variant Result และ record ฐานเองได้ (เช่น ข้อมูลราคานิ่งที่ H001 ไม่มีสัญญาณ, F41) · งบ (ข้อ 5 ของ runner: setup เดียวต่อไฟล์, ฐานเดียวต่อโครงสร้าง, ok ไม่เกินหนึ่งต่อ variant, รันซ้ำได้เมื่อยังไม่มี ok) · ทั้งหมดนี้ไม่เขียน registry
2. ตรวจ M1/M15 แบบเดียวกับ CORE-007 "Input และการตรวจ" (ว่าง, timeframe, เวลาเพิ่มขึ้นเคร่งครัด, `time_utc` เทียบกฎเวลาทั้ง M1 และ M15, M1 ที่ไม่อยู่ในแท่ง M15 ใดตาม `timebase.bar_open(t, 15, rule)`, แท่ง M15 ที่ไม่มี M1, M1 ระดับ STOP) แต่ raise `ResearchError` · ทุกไม้ของ `variant` ต้องมี `entry_time_raw` และ `exit_time_raw` เป็น `time_raw` ของ M1 ใน `m1` ไม่เช่นนั้น `ResearchError`
3. h ของ variant: `hs` = ระยะถือ (index ของ M1 ที่ออก − index ของ M1 ที่เข้า) ของไม้ที่ `exit_reason` เป็น "signal" หรือ "end_of_data" หรือ `ambiguous` (ไม้ที่ออกตามจังหวะของกลยุทธ์) ตามลำดับไม้ · ว่าง → `ResearchError` · K = จำนวนไม้ทั้งหมดของ variant (≥ 1)
4. eligible = ทุก t ใน 0 … len(m15) − 2 เรียงจากน้อยไปมาก ที่ `strategy.entry_blockers(rows[t], m15[t+1].bar.time_utc)` ว่าง โดย `rows = strategy.indicators(m15, params)` · `len(eligible) < K` → `ResearchError` (ไม่เขียน registry)
5. seed = `int(base_run_id[:15], 16)` (น้อยกว่า 2^60) · `rng = random.Random(seed)` ตัวเดียวต่อการเรียก โดยโมดูล baseline `import random` แล้วเรียก `random.Random` ผ่านชื่อโมดูลตอนเรียกใช้ (tests แทนด้วยตัวปลอมผ่าน monkeypatch ของ `random.Random` ได้, F26)
6. append บรรทัด **started** (purpose random_entry, seed, runs, base_run_id)
7. ทำ `BASELINE_RUNS` (1,000) รอบ ต่อรอบ: `pool = list(eligible)` แล้ววนจนได้ K ไม้: ถ้า pool ว่าง → `ResearchError` · `t = pool.pop(rng.randrange(len(pool)))` · `stop_distance = params.k × rows[t].atr` (ใน CONTEXT) · `sized = sizer(equity, stop_distance)` ต้องเป็น `backtest.SizedLots` พอดี (`TypeError`) · ถ้า `sized.lots is None` ข้ามไปสุ่มแท่งถัดไปโดยไม่สุ่มอย่างอื่น · `side = ("long", "short")[rng.randrange(2)]` · `h = hs[rng.randrange(len(hs))]` · `entry_index` = M1 แรกของแท่ง t+1 · `planned = entry_index + max(h, 1)` · `exit_index = planned` ถ้า `planned < len(m1)` ไม่เช่นนั้น None · `data_flags` = union ของ flags ของแท่ง M15 ตั้งแต่ t ถึงแท่งของ M1 `exit_index` (หรือ M1 สุดท้ายเมื่อ None) · ไม้ = `backtest.simulate_trade(m1, entry_index, side, stop_distance, sized.lots, model, rollover, risk_money=sized.risk_money, actual_risk=sized.actual_risk, exit_index=exit_index, data_flags=data_flags)`
8. expectancy ของรอบ = ผลรวม r ตามลำดับไม้ ÷ K · BaselineSummary: runs = 1000, trades_per_run = K, seed, mean_r = ผลรวม expectancy ของทุกรอบตามลำดับ ÷ 1000 · p05/p50/p95 = `percentile(…, 0.05 / 0.5 / 0.95)` · ระยะถือที่เกิดจริง (exit index − entry index) ของไม้ใน variant ทั้งหมดและของไม้สุ่มทั้งหมด: mean และ median (= `percentile(…, 0.5)`)
9. สำเร็จ → append **ok** พร้อม baseline แล้วคืน BaselineResult · exception ใดๆ หลังข้อ 6 (รวม BaseException และความล้มของการ append บรรทัด ok) → พยายาม append **failed** แล้ว raise object เดิม (แบบเดียวกับ runner ข้อ 8)
- ไม่ใช้ float ใดๆ (`randrange` เท่านั้น) · BaselineResult ไม่คืนรายการไม้ (1,000 × K ไม้ใหญ่เกินไป): tests ตรวจไม้ผ่าน `expectancies_r` และสถิติระยะถือ โดยคำนวณไม้ที่คาดด้วย `simulate_trade` จากลำดับการสุ่มที่ควบคุมด้วย `random.Random` ปลอม · ข้อมูลทดสอบที่เล็ก (K น้อย, h สั้น) ทำให้ 1,000 รอบรันได้เร็ว

### robustness (D9)
- พารามิเตอร์ที่ใช้ของแต่ละโครงสร้าง = `USED_PARAMETERS[variant]` (มาจากกฎ H001 ข้อ 3: V-A ใช้ f, s, n, θ, k · V-B ใช้ n, N, M, k เท่านั้น · V-C ใช้ f, s, n, N, M, k)
- `neighbours(params)` คืนเพื่อนบ้าน 2 ตัวต่อพารามิเตอร์ที่ใช้ เรียงตาม f−, f+, s−, s+, n−, n+, theta−, theta+, N−, N+, M−, M+, k−, k+ (ข้ามที่ไม่ใช้) · ค่าใหม่ = ค่าเดิม × `Decimal("0.9")` หรือ × `Decimal("1.1")` ใน CONTEXT · f, s, n, N, M ปัดเป็นจำนวนเต็มด้วย `quantize(Decimal(1), ROUND_HALF_UP)` · θ, k ไม่ปัด (เช่น 0.50 → 0.450, 0.550; 2.0 → 1.80, 2.20) · `value` = str ของค่าใหม่ · พารามิเตอร์อื่นคงเดิม
- ชุดที่ H001Params ปฏิเสธ (ผิดช่วงหรือผิด s ≥ 3f, M ≤ N) → `params=None` (invalid ไม่รัน นับว่าไม่ผ่าน)
- จำนวนเพื่อนบ้าน V-A 10, V-B 8, V-C 12 · ต้องผ่าน ⌈0.8 × จำนวน⌉ = 8, 7, 10

### evaluate (H001 ข้อ 8–9, D14, F9, F11)
ตรวจ input ก่อน (`ResearchError`): ทุก record status ok · base มี purpose select (F32) · purpose ของ record อื่นตรงตามชื่อ argument · stress, long_only, random_entry และทุก robustness มี base_run_id = run_id ของ base · hypothesis, variant, dataset, code_commit, sizer_label, equity, rollover และกฎเวลาเท่ากันทุก record (string ของ record) · params ของ stress, long_only, random_entry = ของ base · cost_model เท่ากันทุกคู่ยกเว้น stress_factor ที่ต้องเป็น `"2"` สำหรับ stress และ `"1"` สำหรับที่เหลือ · `baseline.trades_per_run == base.summary.trades` (runs = 1000 รับประกันโดย RunRecord) · robustness ที่ส่งมา = record ละหนึ่งต่อเพื่อนบ้าน valid ของ `neighbours(base)` ตามลำดับ (params ตรงทีละตัว) หรือว่างทั้งหมด
- **input ที่ขาด (F27, F34):** stress, long_only และ random_entry เป็น None ได้ และ robustness ว่างได้ **ที่จำนวนไม้เท่าใดก็ได้** (ถ้าส่งมาต้องผ่านการตรวจข้างบน) · แถวที่ขาด input ไม่ผ่าน จึงได้ verdict เป็น `stop` หรือ `insufficient` เท่านั้น ไม่มีทางได้ `go` · ใช้ได้กับโครงสร้างที่รันบางส่วนไม่ได้ (เช่น ไม้ทั้งหมดโดน SL จน baseline สร้าง hs ไม่ได้ หรือรันที่ล้มซ้ำจนหมดงบ) ให้ยังได้คำตัดสินตามข้อที่มี ("ผ่านบางข้อ = Stop" ของ H001 ข้อ 8)
- **ค่าของแถวเมื่อ input ขาด (F37):** เฉพาะส่วนที่มาจาก input ที่ขาดเป็น `none` · แถว 3: value `none`, threshold `0` · แถว 5: value `none`, threshold `<ต้องผ่าน>/<จำนวน>` ตามเดิม (จำนวนจาก `neighbours(base)`) · แถว 6: value = base expectancy ตามเดิม, threshold `none` · แถว 10: `expectancy:<base>/none;max_drawdown:<base>/none`, threshold `better on one` · ทุกแถวที่มีส่วน `none` ไม่ผ่าน
คืน `Evaluation(variant, run_id ของ base, dataset ของ base, screen = dataset.period_start_utc < HOLDOUT_CUTOFF_UTC (F29: ข้อมูลส่วนใดก็ตามก่อน cutoff ทำให้เป็น screen), verdict, checks)` · checks มี 10 แถวเสมอตามตารางนี้ (ค่าที่เป็น None เขียนว่า `none` และทำให้แถวนั้นไม่ผ่าน):

| # | name | value | threshold | ผ่านเมื่อ |
|---|---|---|---|---|
| 1 | `trades` | str(trades) | `100` | trades ≥ 100 |
| 2 | `expectancy_1x` | str(base expectancy) | `0.10` | ≥ 0.10 |
| 3 | `expectancy_2x` | str(stress expectancy) | `0` | > 0 |
| 4 | `max_drawdown_r` | str(base max_drawdown_r) | `24` | ≤ 24 |
| 5 | `robustness` | `<ผ่าน>/<จำนวน>` | `<ต้องผ่าน>/<จำนวน>` | ผ่าน ≥ ⌈0.8 × จำนวน⌉ · จำนวน = เพื่อนบ้านทั้งหมดของ `neighbours(base)` รวม invalid · ผ่าน = เพื่อนบ้าน valid ที่ expectancy > 0 (expectancy None = เพื่อนบ้านตัวนั้นไม่ผ่าน แถวยังคำนวณต่อ) · ไม่มี robustness → value `none` |
| 6 | `vs_random_entry` | str(base expectancy) | str(baseline p95_r) | expectancy > p95 (เคร่งครัด) |
| 7 | `top5_removed` | str(top5_removed) | `0` | > 0 |
| 8 | `years` | `<ปี>:<ค่า>` คั่นด้วย `;` ตามปี (ไม่มีปี = `none`) | `0` | มีอย่างน้อยหนึ่งปี และทุกปี ≥ 0 |
| 9 | `sides` | `long:<ค่า>;short:<ค่า>` | `0` | ทั้งสองฝั่ง ≥ 0 (ฝั่งที่ไม่มีไม้ = `none` = ไม่ผ่าน) |
| 10 | `vs_long_only` | `expectancy:<base>/<long_only>;max_drawdown:<base>/<long_only>` | `better on one` | base expectancy > long-only expectancy หรือ base max_drawdown < long-only max_drawdown (ถ้า long-only ไม่มีไม้ หรือ base ไม่มีไม้ = ไม่ผ่าน) |

- verdict: แถว 1 ไม่ผ่าน → `insufficient` · ทั้ง 10 แถวผ่าน → `go` · ไม่เช่นนั้น `stop` · คำตัดสินของ H001 นับเฉพาะ Evaluation ที่ `screen = False` (ข้อมูล holdout) · "holdout ครอบคลุม regime เดียว" และ leakage audit เป็นการตัดสินของเจ้าของ

### render_report (F12, F14, F22)
คืน string (ไม่เขียนไฟล์) ตามแบบนี้พอดีทีละบรรทัด ทุกบรรทัดจบด้วย `\n` · `{…}` คือค่าที่แทน · บรรทัดว่างในแบบคือบรรทัดว่างจริง · ข้อความในวงเล็บหลัง `—` คือคำอธิบาย ไม่ใช่ส่วนของผลลัพธ์:
```text
# รายงานวิจัย {hypothesis}

## Registry

| โครงสร้าง | purpose | started | ok | failed | interrupted | งบ |
|---|---|---|---|---|---|---|
| {variant} | {purpose} | {started} | {ok} | {failed} | {interrupted} | {งบ} |      — 15 แถว: A, B, C × select, robustness, stress, long_only, random_entry ตามลำดับนี้

รวมที่นับงบ: {นับงบ}/63

## ผลการประเมิน {variant}      — หนึ่งส่วน (ถึงบรรทัด "คำตัดสิน") ต่อ Evaluation เรียงตาม variant A, B, C

ชุดข้อมูล: {snapshot_id} {period_start_utc} ถึง {period_end_utc}
setup: commit {code_commit} · sizer {sizer_label} · equity {equity} · rollover {rollover_zone} {rollover_at} · กฎเวลา {time_rule_server} {time_rule_version} · cost_model {ชื่อ=ค่า ของทุกคู่ใน cost_model ตามลำดับ คั่นด้วย ;}      — จาก record ฐาน (F33)
ชุดข้อมูลที่ select ของ {variant} ใช้: {จำนวน dataset ที่ต่างกันในบรรทัด started ของ select ของ variant นี้}
การประเมินนี้เป็น screen ไม่ใช่คำตัดสินของ H001: มีข้อมูลก่อน cutoff ของ holdout      — เฉพาะเมื่อ screen

| # | เงื่อนไข | ค่า | เกณฑ์ | ผล |
|---|---|---|---|---|
| {ลำดับ} | {name} | {value} | {threshold} | {ผ่าน หรือ ไม่ผ่าน} |      — 10 แถวตามลำดับของ checks

คำตัดสิน: {verdict}

## ข้อจำกัดที่ต้องรายงาน

- drawdown วัดจาก realized curve เท่านั้น
- {variant} {purpose} seq {seq ของบรรทัด ok}: ambiguous {ambiguous_trades}, data flag {flagged_trades}, fill หลังข้อมูลขาด {gap_fills}, ข้อมูลหมด {end_of_data_trades}      — หนึ่งบรรทัดต่อบรรทัด ok ที่มี summary เรียงตาม seq
- baseline {variant} seq {seq ของบรรทัด ok}: runs {runs}, seed {seed}, mean {mean_r}, P5 {p05_r}, P50 {p50_r}, P95 {p95_r}, ระยะถือ M1 variant {variant_mean_hold_m1}/{variant_median_hold_m1}, baseline {baseline_mean_hold_m1}/{baseline_median_hold_m1}      — หนึ่งบรรทัดต่อบรรทัด ok ของ random_entry เรียงตาม seq

## สิ่งที่เจ้าของตัดสินเอง

- holdout ครอบคลุม regime เดียวหรือไม่
- leakage audit
- วิธีรวมคำตัดสินของหลายโครงสร้าง: ทดสอบหลายโครงสร้างทำให้โอกาสได้ go โดยบังเอิญสูงขึ้น
```
- ทุกส่วนของรายงาน ทั้งตาราง registry, "นับงบ", การตรวจ key และฐานของ Evaluation (F32, F45), บรรทัด setup/จำนวนชุดข้อมูล และ bullet ข้อจำกัด ใช้เฉพาะ record ที่ `hypothesis` ตรงกับ argument (record ของ hypothesis อื่นในไฟล์เดียวกันไม่ถูกอ่าน, F47) · started/ok/failed = จำนวนบรรทัดตาม status ของแถวนั้น · interrupted = บรรทัด started ที่ไม่มีบรรทัด ok หรือ failed อ้างถึง
- คอลัมน์ "งบ": select = `{จำนวน params ที่ต่างกัน}/6` · robustness = `{started}/14` · stress = `{ok}/1` · long_only และ random_entry = `ไม่นับ` · แถวที่ไม่มีบรรทัดเลยแสดงตัวเลข 0 ในรูปเดียวกัน (เช่น `0`, `0/6`, `0/14`, `0/1`, `ไม่นับ`)
- "นับงบ" = ผลรวมต่อ variant ของจำนวน params select ที่ต่างกัน (คีย์ = variant + params) + started ของ robustness + started ของ stress ทุก variant (กฎเดียวกับ runner ข้อ 5 · select ค่าตั้งต้นของ A, B, C = 3, F43)
- datetime เขียนแบบ canonical `%Y-%m-%dT%H:%M:%SZ` · Decimal เขียนด้วย `str()` · key ของ `evaluations` ต้องเท่ากับ `Evaluation.variant` และเป็น A, B หรือ C ไม่เช่นนั้น `ResearchError` (F32) · `Evaluation.base_run_id` ต้องเป็น run_id ของบรรทัด ok ของ purpose select และ variant นั้นใน record ของ hypothesis นั้น และถ้า record ของ hypothesis นั้นมีบรรทัด started ที่ไม่ใช่ select ของ variant นั้น ต้องเท่ากับฐานที่บรรทัดแรกนั้นกำหนด (runner ข้อ 5) ไม่เช่นนั้น `ResearchError` (F45: รายงานแสดงคำตัดสินของฐานอื่นแทนฐานที่ถูกล็อกไม่ได้)
- **บรรทัดว่าง (F38):** ระหว่างส่วน "ผลการประเมิน" สองส่วนมีบรรทัดว่างหนึ่งบรรทัด (หลัง "คำตัดสิน" ของส่วนก่อน) · ไม่มี Evaluation เลย: "รวมที่นับงบ" ตามด้วยบรรทัดว่างหนึ่งบรรทัดแล้ว "## ข้อจำกัดที่ต้องรายงาน" · ไม่มีบรรทัดว่างติดกันสองบรรทัด · ไม่มีช่องว่างท้ายบรรทัด · บรรทัดที่เป็น bullet ต่อ record (ข้อจำกัด) ไม่มีบรรทัดว่างคั่น

## Invariants
- ใช้ `backtest`, `strategy` และ `costs` จริง ไม่เขียนกฎหรือสูตรซ้ำ (eligible ใช้ `entry_blockers` ตัวเดียวกับ decide) · ข้อยกเว้นเดียว (F30): การตรวจ M1/M15 แบบ CORE-007 "Input และการตรวจ" และการจับคู่ M1 กับแท่ง M15 ซึ่ง `backtest` เก็บเป็น private ให้ research เขียนเองโดยใช้ `timebase.bar_open`/`to_utc` และ raise `ResearchError`
- หนึ่งไฟล์ registry มีโปรเซสของ runner เขียนได้ครั้งละหนึ่งโปรเซส (F42) · ภายในไฟล์หนึ่ง setup ของ hypothesis คงที่ (F33)
- ทุกการรันที่เริ่มแล้วมีบรรทัด started ก่อนคำนวณ และนับงบ (รันซ้ำของ identity ที่ยังไม่มี ok ก็นับ) · registry เพิ่มได้อย่างเดียว ไม่มีโค้ดที่เขียนทับ ตัด หรือลบ
- ไม่อ่านข้อมูลตั้งแต่ cutoff ของ holdout · ไม่มีนาฬิกา · สุ่มเฉพาะผ่าน `random.Random(seed)` และ `randrange` · ไม่มี float · ผลซ้ำได้จาก input และ registry
- import ได้เฉพาะ `core`, `timebase`, `strategy`, `costs`, `backtest` และ stdlib: bisect, collections, collections.abc, dataclasses, datetime, decimal, enum, functools, hashlib, itertools, json, operator, pathlib, random, types, typing · อ่าน/เขียนไฟล์ได้เฉพาะใน `src/sochron/research/registry.py` · ห้าม `risk`, `broker`, `execution`, `journal`, `data` (ทั้งแพ็กเกจ), MetaTrader5, network, process, console, `os`
- `strategy.entry_blockers`: decide ให้ผลเดิมทุกกรณี, `STRATEGY_VERSION` คงเดิม, tests ล็อกของ CORE-006 ยังผ่าน

## Negative cases
registry: ไฟล์ไม่จบ LF (บรรทัดขาด), `\r`, ไบต์ไม่ใช่ ASCII, JSON เสีย, ไม่ canonical, seq ขาด/ซ้ำ, run_id ปลอม, path ไม่ใช่ .jsonl, record ชนิดผิด, ok ที่อ้าง started ผิดหรือซ้ำ, OSError ตอนเขียน (ส่งต่อ) · runner: bar ที่ cutoff พอดีและหลัง cutoff (รวมกรณีที่ Dataset ผิดด้วย: holdout guard มาก่อน), dataset จบหลัง cutoff, Dataset ผิด (naive, start ≥ end, m1_bars ≠ len(m1), manifest ไม่ใช่ 64 hex), M1/M15 ไม่สอดคล้อง (เช่น แท่ง M15 ที่ไม่มี M1: `ResearchError` ไม่มีบรรทัดใหม่), งบครบพอดีและเกิน (select ชุดที่ 7, params เดิมบน dataset อื่น, robustness started ที่ 15, stress/long_only/random_entry หลังมี ok แล้ว, ผลรวมเกิน 63), ฐานอื่นหลังฐานแรกของ variant ถูกกำหนดแล้ว, setup ต่างจากบรรทัด started แรกของ hypothesis (เช่น slippage 20, equity อื่น, rollover อื่น, code_commit อื่น: `BudgetExceeded`), รันซ้ำหลัง interrupted หรือ failed (รับ) และหลัง ok (ปฏิเสธ รวม select ที่ identity เดิม), การ append บรรทัด ok ล้มผ่าน seam (บรรทัด failed), started ที่ไม่มีผลนับงบ, backtest ล้มกลางทาง, `KeyboardInterrupt` ระหว่าง backtest, การ append บรรทัด ok ล้ม (บรรทัด failed + raise เดิม), purpose ไม่ตรงกับ model/sides/base, base ที่ไม่ใช่ select ok, robustness ที่ไม่ใช่เพื่อนบ้าน, field ที่ evaluate เทียบไม่เท่ากับฐาน (dataset, code_commit, sizer_label, equity, rollover, กฎเวลา, cost_model), stress_factor `"2.0"` แทน `"2"`, θ `"0.45"` แทน `"0.450"` · baseline: model 2×, eligible น้อยกว่า K, sizer คืน None, hs ว่าง, h = 0, h เลยท้ายข้อมูล, variant ไม่มีไม้, variant ที่มีเวลาไม่อยู่ใน m1, variant ที่ไม่ใช่ผลของฐาน (summarize ไม่เท่ากับ summary ของฐาน), m1/m15 ไม่สอดคล้อง, random_entry หลังมี ok แล้วของ variant เดียวกัน, random_entry บนฐานที่สองของ variant เดียวกัน (หลัง ok บนฐานแรก และหลังมีเพียง robustness หรือ random_entry ที่ interrupted บนฐานแรก: `BudgetExceeded` ไม่มีบรรทัดใหม่), ไม้ของ variant ที่โดน SL ทั้งหมด (hs ว่าง), ข้อมูลราคานิ่ง (variant และฐานสร้างเอง) · RunRecord: runs ≠ 1000 หรือ seed ผิดของ random_entry, null ผิดรูปตาม status/purpose, started_seq ≥ seq, params/cost_model ชื่อผิดหรือผิดลำดับ, hypothesis ว่าง · robustness: ค่าที่ปัดครึ่งพอดี, เพื่อนบ้านผิดช่วง (f = 24 → 26) และผิดเงื่อนไข (s = 3f, M = N) · evaluate: ทุกเกณฑ์ที่ขอบพอดี (99/100 ไม้, 0.10 R, 24 R, ผ่านพอดี ⌈0.8n⌉, เท่ากับ P95), ฝั่งที่ไม่มีไม้, ปีที่ติดลบ, ≤ 5 ไม้, long-only ไม่มีไม้, base มีไม้ 0 หรือ < 100 กับ input ที่ขาด (insufficient), base ≥ 100 ไม้กับ input ที่ขาด (stop: แถวที่ขาดเป็น `none`), input ไม่สอดคล้องทุกแบบ (trades_per_run ≠ trades, dataset/params/cost ต่างกัน, เพื่อนบ้านขาด/เกิน/สลับลำดับ, base ที่ไม่ใช่ select) · render_report: key ที่ไม่ตรงกับ variant, base_run_id ที่ไม่มีใน records, Evaluation ที่ฐานเป็น select ok ตัวอื่นที่ไม่ใช่ฐานที่ถูกล็อกของ variant นั้น (F45), registry ที่มี H001 และ H002 ปนกัน (ฐานที่ล็อกของ H001 ผ่าน, ฐานที่เป็น select ของ H002 → `ResearchError`, F47), sizer_label ว่างใน RunRecord (F46), record ของ hypothesis อื่น, ไม่มี Evaluation เลย · ชนิดผิดทุกช่อง

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given registry ใน `tmp_path` When สร้าง record ตามตัวอย่างบังคับแล้ว `append_record` และ append ต่ออีก 2 record (ok ที่คู่กับ started และ started ใหม่) แล้ว `read_records` Then บรรทัดแรกมีไบต์และ run_id ตรงตัวอย่างบังคับทุกไบต์, seq 1–3, ไบต์ของบรรทัดเดิมไม่เปลี่ยนหลัง append, `read_records` คืน record เท่าเดิมทั้งค่าและชนิด · และทุกกรณีเสียในหัวข้อ registry ได้ error ตามที่หัวข้อนั้นกำหนด (ไฟล์หรือบรรทัดเสีย → `ResearchError` โดยบรรทัดขาดบอก byte offset; record ชนิดผิด → `TypeError`; error ของระบบไฟล์ส่งต่อ) โดยไฟล์ไม่เปลี่ยน
- AC-02 Given ข้อมูลสังเคราะห์และ sizer ปลอม When `run_variant` ของ select, robustness, stress, long_only Then registry ได้บรรทัด started แล้ว ok ที่มีทุก field ตามตาราง และ summary เท่ากับ `summarize(backtest.run(...))` · backtest ที่ล้ม, `KeyboardInterrupt` หรือการ append บรรทัด ok ที่ล้ม → บรรทัด started + failed แล้ว exception เดิมถูก raise · การ append บรรทัด ok ที่ล้ม ทดสอบผ่าน seam `sochron.research.registry.append_record` · started ที่ไม่มีผลนับงบ · รันซ้ำหลัง interrupted/failed รับ, หลัง ok (รวม select ที่ identity เดิม) → `BudgetExceeded` · บรรทัด started ที่ setup ต่างจากบรรทัด started แรกของ hypothesis ในไฟล์ (เช่น select params เดิมแต่ slippage 20, equity อื่น, code_commit อื่น) → `BudgetExceeded` · ครบงบแล้ว (select ชุดที่ 7, robustness started ที่ 15, stress หรือ long_only หลังมี ok, ผลรวมเกิน 63) → `BudgetExceeded` · ฐานอื่นหลังฐานแรกของ variant → `BudgetExceeded` · params เดิมบน dataset อื่นไม่เพิ่มยอด select · ฐานผิด, robustness ที่ไม่ใช่เพื่อนบ้าน, field ที่ evaluate เทียบไม่เท่ากับฐาน, stress_factor ที่ไม่ใช่ `"1"`/`"2"` พอดี, M1/M15 ไม่สอดคล้อง → `ResearchError` · แท่งที่ 2025-01-01 00:00 UTC พอดีหรือหลังจากนั้น (แม้ Dataset จะผิดด้วย) หรือ dataset จบหลัง cutoff → `HoldoutRefused` · กรณีที่ถูกปฏิเสธทั้งหมดไม่มีบรรทัดใหม่
- AC-03 Given ไม้ที่รู้ค่า r, ฝั่ง, ปี, flags และ exit_reason When `summarize` และ `percentile` Then ทุก field ของ Summary และ percentile แบบ nearest rank ตรงคำตอบที่คำนวณด้วยมือ (รวมไม่มีไม้, ≤ 5 ไม้, r เท่ากันใน top 5, drawdown ที่ลึกที่สุดอยู่ก่อนจุดสูงสุดใหม่)
- AC-04 Given ข้อมูลสังเคราะห์, record ฐาน และผลของ variant When `random_entry_baseline` Then ลำดับการเรียก `randrange` ตรงกับขั้นตอนข้อ 7 (ตรวจด้วย `random.Random` ปลอมที่ให้ค่าตามสคริปต์ผ่าน monkeypatch) และ `expectancies_r` กับสถิติระยะถือเท่ากับที่คำนวณจาก `simulate_trade` ของไม้ที่ลำดับนั้นกำหนด, seed = `int(base_run_id[:15], 16)`, runs = 1000, เรียกซ้ำบน registry ใหม่ได้ผลเหมือนกันทุกตัว · บนข้อมูลราคานิ่ง (open = close คงที่, high − low คงที่ > 0, spread คงที่, model ที่ swap ทั้งสองฝั่งเป็น 0, ไม่มีไม้ที่โดน SL · H001 ไม่มีสัญญาณบนข้อมูลแบบนี้ จึงสร้าง variant Result และ record ฐานเองให้ summary ตรงกัน ตาม baseline ข้อ 1) ทุกรอบได้ expectancy = −(spread charge + commission + slippage ทั้งสองข้าง) ÷ risk_money โดยเลือก risk_money ที่ทำให้ผลหารจบลงตัว (เช่น 25) จึงเท่ากับค่าเฉลี่ยตามกฎของ contract พอดี (H001_COSTS: commission 0) · sizer คืน None → สุ่มแท่งถัดไป · ทุกกรณีเสียในหัวข้อ baseline → error ตามที่กำหนด และบรรทัด registry ตามข้อ 1, 6, 9 · random_entry หลังมี ok ของ variant เดียวกัน → `BudgetExceeded` · random_entry บนฐานที่สองของ variant เดียวกัน → `BudgetExceeded` ไม่มีบรรทัดใหม่ ทั้งหลังมี ok บนฐานแรก และหลังมีเพียง robustness หรือ random_entry ที่ interrupted บนฐานแรก (F41)
- AC-05 Given ค่าตั้งต้นของ V-A, V-B, V-C และชุดที่ขอบช่วง When `neighbours` Then ได้เพื่อนบ้านตามจำนวน ลำดับ และค่าที่คำนวณด้วยมือ ชุดผิดช่วงหรือผิดเงื่อนไขเป็น invalid · Given ชุด record ที่สอดคล้องกันซึ่ง Summary และ BaselineSummary อยู่ที่ขอบเกณฑ์พอดีของทุกแถว When `evaluate` Then verdict, screen และค่า/เกณฑ์/ผลของทั้ง 10 แถวตรงคำตอบ (99 ไม้ → insufficient, 0 ไม้หรือไม้ < 100 ที่ไม่มี stress/long_only/random_entry/robustness → insufficient, 100 ไม้ + ผ่านครบ → go, พลาดแถวเดียว → stop, ≥ 100 ไม้ที่ขาด stress หรือ robustness → stop โดยแถวที่ขาดเป็นไปตามกฎ F37, ข้อมูลเริ่มก่อน cutoff → screen True) · และ input ไม่สอดคล้องแต่ละแบบ → `ResearchError`
- AC-06 Given registry ตัวอย่าง (มี failed และ interrupted) และ Evaluation ของ 3 โครงสร้าง และกรณีไม่มี Evaluation เลย When `render_report` Then ข้อความตรงตามแบบในหัวข้อ render_report ทุกบรรทัด รวมบรรทัด setup และจำนวนชุดข้อมูลของ select และกฎบรรทัดว่าง · Given source ของ `sochron.research` When รัน architecture test Then import และ I/O เป็นไปตาม Invariants · และ `entry_blockers` คืนเหตุผลเท่ากับ `decide` ทุกกรณีที่ decide ตอบ skip, decide ใช้ฟังก์ชันนี้จริง (แทนด้วยตัวปลอมผ่าน monkeypatch แล้ว reasons ของ decide เปลี่ยนตาม), ชนิดผิด → `TypeError`, เวลาไม่มี timezone → `StrategyError`, `_invalid` ไม่มีแล้ว
- AC-07 Given ทั้ง suite When `uv run --offline pytest tests -q -p no:cacheprovider` Then ผ่านทั้งหมด skipped 0 (รวม tests ล็อกของ CORE-006/007) และ CI เขียว

## Verification per AC
| AC | Verifier | Command or procedure | Evidence level |
|----|----------|----------------------|----------------|
| 01–05 | test author (acceptance + golden ที่คำนวณด้วยมือจาก contract นี้) | `uv run --offline pytest tests/acceptance/CORE-008 tests/golden/CORE-008 -q -p no:cacheprovider` | L2 |
| 06 | test author + reviewer | acceptance + architecture test + mutation | L2 |
| 07 | Claude + CI | คำสั่งในตาราง + run ของ PR | L2/L3 |
| ความเร็ว | Claude (unit test/หลักฐาน ไม่ใช่ acceptance) | baseline 1,000 รอบ × K = 100 ไม้ × h ≈ 200 M1 บน M1 สังเคราะห์ 100,000 แท่ง · หลักฐานแสดงสูตรประมาณเวลา (≈ 1.5 µs ต่อ M1 ที่อ่าน + ≈ 47 µs ต่อไม้ ตามที่ผู้ตรวจวัด) และเวลาที่คาดของ R1 | L2 |

## Risk, data and external side effects
ไม่มีผลภายนอก · ไฟล์ที่เขียนอยู่ใน path ที่ผู้เรียกให้เท่านั้น (tests ใช้ `tmp_path`) · ความเสี่ยงหลัก: คำตัดสินผิดจากสถิติหรือ baseline ที่นิยามผิด (golden ที่คำนวณด้วยมือ, ขอบทุกเกณฑ์, input ของ evaluate ต้องสอดคล้อง), งบ variant ถูกเลี่ยง (นับจาก started, ปฏิเสธก่อนรัน, seed กำหนดจากฐาน), ข้อมูล holdout หลุดเข้ามา (guard เป็นชั้นเสริม ขอบเขตจริงคือ ENV-1), registry เสีย (ตรวจทุกบรรทัด, เขียนครั้งเดียวต่อบรรทัด, วิธีกู้ของเจ้าของ) · ความเร็ว: baseline หนึ่งชุดใน R1 อาจใช้หลายสิบนาที (ผู้ตรวจประมาณ ≈ 25 นาทีที่ K = 1,500, h = 600)

## Plan, dependencies and unknowns (P06)
1. Understanding: ห่อ `backtest` ด้วย registry ที่บันทึกทุกรันก่อนเริ่ม และงบของ H001, สร้าง baseline สุ่มและเพื่อนบ้านตาม H001, แล้วตัดสินตาม H001 ข้อ 8 จาก record ที่สอดคล้องกัน · เข้าใจผิดที่เป็นไปได้: เขียนตัวกรอง eligible ซ้ำ · ใช้ `random` ระดับโมดูล, float หรือนาฬิกา · บันทึกหลังรันอย่างเดียว · ไม่นับ started/failed ในงบ · percentile แบบ interpolate · DD ที่ไม่เริ่มจาก 0 · ปีตามเวลาไทย · ให้ go ทั้งที่ไม้น้อยกว่า 100 · ถือผลบน validation เป็นคำตัดสิน · เขียนไฟล์แบบ text บน Windows (CRLF) · เขียน registry จริงใน tests
2. Files / reuse: `backtest.run/simulate_trade/SizedLots/BACKTEST_VERSION`, `strategy.indicators/decide/STRATEGY_VERSION/H001Params` + `entry_blockers`, `costs.CONTEXT/CostModel`, `timebase.to_utc/bar_open/TimeRule`
3. Steps: (1) contract review ด้วย subagent จน ready → อนุมัติแทน (2) ผู้เขียน tests (Claude session ใหม่) (3) apply + review → red (4) implement (5) review → PR
4. Decisions (อนุมัติแทนโดย delegation ตามทางที่แนะนำ · ทางเลือกอื่นอยู่ในวงเล็บ):
   - **D1 eligible:** ตัวกรองของกลยุทธ์ทุกข้อผ่าน `strategy.entry_blockers` (ทางอื่น: เฉพาะ session/spread ตามถ้อยคำ H001 ข้อ 7 — ไม่เลือกเพราะกลยุทธ์จริงถูกตัวกรองอื่นด้วย ผู้ตรวจยืนยันว่าตัดเฉพาะแท่งที่ variant เข้าไม่ได้เช่นกัน; หรือเขียนตัวกรองซ้ำ — ผิด invariant)
   - **D2 ระยะถือ:** h จากไม้ของ variant ที่ออกตามจังหวะของกลยุทธ์ (signal, end_of_data, ambiguous) แบบใส่คืน แล้วให้ SL ของไม้สุ่มตัดเอง · รายงานแสดงระยะถือจริงของทั้งสองฝั่ง (ทางอื่น: h จากทุกไม้รวมที่โดน SL — ไม่เลือกเพราะถูกตัดสองครั้ง ระยะถือสั้นกว่าจริงและทำให้ P95 ต่ำลง, review r1 F13)
   - **D3 การสุ่ม:** แท่งไม่ซ้ำในรอบเดียว, ไม้ซ้อนกันได้, sizer ได้ equity เริ่มต้นทุกไม้, lots None → แท่งนั้นหายจาก pool ของรอบ ขั้นตอนตายตัวตามหัวข้อ baseline ข้อ 7
   - **D4 stop:** k × ATR[t] สูตรเดียวกับ decide
   - **D5 RNG:** `random.Random(int(base_run_id[:15], 16))`, `randrange` อย่างเดียว · ฐานเดียวต่อโครงสร้างสำหรับทุก purpose ที่ไม่ใช่ select และ random_entry ok ได้หนึ่งครั้งต่อโครงสร้าง จึงเลือก seed ไม่ได้ทั้งทางตรงและทางอ้อม (รัน select ซ้ำเพื่อหาฐานที่ P95 ต่ำ ถูกปิดด้วยกฎฐานเดียว, review r2 F9) (ทางอื่น: ผู้เรียกเลือก seed — ไม่เลือก)
   - **D6 percentile:** nearest rank, "สูงกว่า P95" = มากกว่าอย่างเคร่งครัด
   - **D7 drawdown:** จากผลรวมสะสมของ R ตามลำดับไม้ เริ่มที่ 0
   - **D8 ปี:** ปี UTC ของเวลาเข้าไม้ เฉพาะปีที่มีไม้ในชุดข้อมูลที่ประเมิน (บน holdout คือ 2025/2026 ของ H001)
   - **D9 robustness:** เฉพาะพารามิเตอร์ที่กฎของโครงสร้างใช้ (`USED_PARAMETERS`) เกณฑ์ ⌈80%⌉: V-A 8/10, V-B 7/8, V-C 10/12 · เพื่อนบ้านผิดช่วงหรือผิดเงื่อนไขนับว่าไม่ผ่าน (ชุดที่เลือกอยู่ขอบช่วงจึงเสียหนึ่งตัวต่อขอบ) · (ทางอื่น: 14 ตัวตามถ้อยคำ "12 จาก 14" — ไม่เลือกเพราะ review r1 F2 แสดงว่า θ ของ V-B/V-C และ f ของ V-B ไม่อยู่ในกฎเลย ส่วน s ของ V-B และ N, M ของ V-A เปลี่ยนแค่ช่วง warm-up (`warm_from = max(3s, N+1, M+1, 97, n+1)`) ไม่เปลี่ยนกฎเข้า/ออก V-B จึงผ่านได้ที่ 75% ของเพื่อนบ้านที่กฎใช้จริง ต่ำกว่า 80% ของ H001) · **เจ้าของ veto ได้**
   - **D10 งบ:** นับจากบรรทัด started · select นับเป็นชุดพารามิเตอร์ที่ต่างกันต่อโครงสร้าง (≤ 6) · ทุก purpose ที่ไม่ใช่ select ใช้ฐานเดียวต่อโครงสร้าง · robustness ≤ 14 started ต่อโครงสร้าง (H001) และ ok ≤ 1 ต่อเพื่อนบ้าน · stress, long_only, random_entry ok ≤ 1 ต่อโครงสร้าง · รันซ้ำได้เมื่อ identity ยังไม่มี ok และรันซ้ำนับงบ · **ขอบเขตจริง (review r3 F34):** ที่ค่าตั้งต้นเหลือ robustness สำรอง 4/6/2 รัน (V-A/V-B/V-C: 14 − 10/8/12) และรวมทั้ง hypothesis สำรอง 12 รัน (63 − 51) · ความล้มที่เกิดซ้ำทุกครั้ง (เช่น bug ใน sizer) ใช้งบสำรองหมดได้ และการแก้โค้ดหลังมีฐานต้องเริ่มไฟล์ registry ใหม่ (setup เดียวต่อไฟล์) · ถ้าโครงสร้างรันไม่ครบ `evaluate` ยังให้คำตัดสินได้ (แถวที่ขาดไม่ผ่าน จึงได้ stop หรือ insufficient ไม่ได้ go) · ผลรวม select (ชุด) + robustness + stress ≤ 63 · long_only และ random_entry ไม่นับใน 63 · ข้อมูลเสียถูกปฏิเสธก่อนเขียน started (ทางอื่น: นับ select เป็นรัน — ไม่เลือกเพราะรันชุดเดิมบน train แล้ว validation จะกินงบสองเท่า; ห้ามรันซ้ำเด็ดขาด — ไม่เลือกเพราะรันที่ถูกขัดจะทำให้ H001 จบไม่ได้)
   - **D11 holdout guard:** ปฏิเสธแท่งที่ `time_utc ≥ 2025-01-01 00:00 UTC` และ dataset ที่จบหลัง cutoff ก่อนเขียน registry
   - **D12 registry:** JSONL canonical ตามตัวอย่างบังคับ, started → ok/failed, เขียนแบบไบต์ครั้งเดียวต่อบรรทัด, ตรวจก่อนเขียนและตอนอ่าน, การกู้บรรทัดขาดเป็นงานของเจ้าของ
   - **D13 input จากผู้เรียก:** code_commit, Dataset และ sizer_label เป็น input (research ไม่เรียก git หรือนาฬิกา)
   - **D14 evaluate:** 10 แถวตามตาราง, input ต้องสอดคล้อง, screen เมื่อมีข้อมูลก่อน cutoff (`period_start_utc < cutoff`), input ที่ขาดได้ทุกจำนวนไม้ (แถวนั้นไม่ผ่าน ไม่มีทางได้ go)
   - **D16 setup เดียวต่อไฟล์ (review r3 F33):** ต้นทุน, equity, sizer, rollover, กฎเวลา และ code_commit คงที่ภายในไฟล์ registry หนึ่งต่อ hypothesis · รายงานแสดง setup ของฐานและจำนวนชุดข้อมูลที่ select ใช้ (ทางอื่น: แสดงในรายงานอย่างเดียว — ไม่เลือกเพราะยังเลือกต้นทุนหลังเห็นผลได้)
   - **D15 ผู้เขียน tests และผู้ตรวจ:** Claude session ใหม่ตามการสลับบทบาท · contract review ใช้ subagent
5. Decisions needed from the owner: ไม่มีที่ขวางงานนี้ (ทุกข้ออนุมัติแทนได้และ veto ได้) · **ก่อน SLICE-R1 เจ้าของต้องตัดสินเอง (ไม่อนุมัติแทน เพราะเป็นการตีความงบของ H001):**
   - (ก) กฎเลือกชุดพารามิเตอร์บน validation (H001 ไม่ได้ระบุ) · ต้องเป็นกฎเชิงกลที่ตัดสินจาก record select ได้เอง (เช่น expectancy สูงสุดบน validation) เพราะ seed ของ baseline มาจาก run_id ของฐานซึ่งเปิดเผย ใครก็คำนวณ P95 ของฐานต่างๆ นอก registry ก่อนเลือกฐานได้ (review r3 F9 residual) · `base_run_id` ของทุกรันที่ไม่ใช่ select มาจากกฎนี้เท่านั้น · กฎต้องระบุ Dataset ของ validation (snapshot_id และช่วงเวลาจาก SLICE-R1) และ select บน Dataset อื่นไม่มีสิทธิ์เป็นฐาน (review r4 F44: dataset ไม่อยู่ใน setup จึงเลือกช่วงข้อมูลหลังเห็นผลได้ภายในไฟล์เดียว)
   - (ข) วิธีรวมคำตัดสินของ 3 โครงสร้าง (ทดสอบหลายโครงสร้างเพิ่มโอกาส go โดยบังเอิญ)
   - (ค) **งบกับ screen (review r2 F21):** ถ้ารัน robustness และ stress บนข้อมูลก่อน holdout (เพื่อให้ได้ screen) จะใช้ 10/8/12 + 1 รันต่อโครงสร้าง แล้วการประเมินบน holdout ต้องรันชุดเดิมอีกครั้ง: robustness 20/16/24 ต่อโครงสร้าง (เกิน 14) และรวม 51 + 33 = 84 รัน (เกิน 63) · ทางเลือก (1) บนข้อมูลก่อน holdout รันเฉพาะ select (และ baseline ที่ไม่นับ) ไม่รัน robustness/stress: ตรงตามตัวอักษรของ H001 แต่ไม่มี screen ของแถว 3 และ 5 · ทางเลือก (2) robustness/stress บนข้อมูลก่อน holdout ไม่นับใน 14/63 ของ H001 (registry บน acquisition host นับงบของ holdout เอง): ได้ screen ครบแต่เป็นการตีความงบ ต้องบันทึกก่อนเห็นผลใดๆ · โค้ดของ CORE-008 บังคับงบต่อไฟล์ registry จึงใช้ได้กับทั้งสองทาง · **ข้อเท็จจริงเพิ่ม (review r3 F40):** (i) ทั้งสองทาง การประเมินบน holdout ต้องใช้ไฟล์ registry แยก เพราะบรรทัดที่ไม่ใช่ select ใดๆ บนข้อมูลก่อน holdout (รวม baseline) ล็อกฐานของโครงสร้างในไฟล์นั้นแล้ว · (ii) ทางเลือก (1) ยังได้ screen แต่แถว 3 และ 5 เป็น `none` (ไม่ผ่าน) screen จึงได้ได้แค่ stop หรือ insufficient
   - (ฉ) **เงื่อนไขของ R1 (review r3 F34, F42):** ห้ามแก้ `src` ตั้งแต่บรรทัด started แรกของ hypothesis ในไฟล์ registry จนประเมินเสร็จ (แก้แล้วต้องเริ่มไฟล์ใหม่และบันทึกเหตุผล) · หนึ่งไฟล์ registry มีโปรเซสของ runner ได้ครั้งละหนึ่ง · `base_run_id` มาจากกฎ (ก)
   - (ง) การลง registry ของรันบน holdout บน acquisition host (contract หลัง ENV-1) · ข้อเสนอ (review r4 F44): ไฟล์ของ holdout มี select ได้หนึ่งครั้งต่อ variant ด้วย params ที่ freeze แล้วและ setup เดียวกับไฟล์ screen (โค้ดของ CORE-008 อนุญาต 6 ต่อ variant ต่อไฟล์ จึงต้องบังคับใน contract ของ acquisition host)
   - (จ) Q-12 ระยะเก็บ registry

## Answers to contract reviews
| Review | Finding | ตอบที่ |
|---|---|---|
| r1 | F1 | Goal (screen), Exclusions (holdout บน acquisition host), Evaluation.screen/dataset, D8, Plan ข้อ 5 (ค) |
| r1 | F2 | robustness, `USED_PARAMETERS`, D9 |
| r1 | F3 | registry (started/ok/failed, append, read, การกู้), runner ข้อ 5–7, baseline ข้อ 6, 9, Invariants |
| r1 | F4 | ตาราง field ของ RunRecord |
| r1 | F5 | รูปแบบ canonical และตัวอย่างบังคับ, robustness (Decimal 0.9/1.1) |
| r1 | F6 | append_record (`"ab"`), read_records (ไบต์, `\r`, ASCII) |
| r1 | F7 | baseline ข้อ 5, 7, D3, D5 |
| r1 | F8 | baseline ข้อ 1–2, 7 (data_flags ตามแผน), ข้อ 9 |
| r1 | F9 | evaluate (input ต้องสอดคล้อง), D5 (seed จากฐาน) |
| r1 | F10 | runner ข้อ 3–4, D10, Plan ข้อ 5 |
| r1 | F11 | ตาราง 10 แถวของ evaluate, ค่าเฉลี่ยใน Inputs |
| r1 | F12 | render_report (หลายโครงสร้าง, ข้อความเรื่องการรวม), Plan ข้อ 5 (ข) |
| r1 | F13 | baseline ข้อ 3, D2, BaselineSummary (ระยะถือ) |
| r1 | F14 | Summary (4 field ใหม่), render_report (ข้อจำกัด) |
| r1 | F15 | `entry_blockers` (ชนิด, timezone, ลบ `_invalid`), AC-06 |
| r1 | F16 | AC-04 (นิยามข้อมูลราคานิ่ง), แถวความเร็ว, Risk |
| r1 | F17 | Hypothesis sha, Authorization, Negative cases, Dataset |
| r2 | F9 | runner ข้อ 5 (ฐานเดียวต่อโครงสร้างทุก purpose ที่ไม่ใช่ select, ok ≤ 1), D5 |
| r2 | F18 | runner ข้อ 3 (ตรวจ input ก่อน started), ข้อ 5 (identity, รันซ้ำ, robustness ≤ 14), ข้อ 8, D10 |
| r2 | F19 | runner ข้อ 2 และ 4 (เทียบแบบ string ของ record), baseline ข้อ 1, `BASELINE_RUNS`, code_commit ในตาราง field |
| r2 | F20 | ชนิด Python ของทุก field, `run_id` เป็น property, `line()`, Summary/BaselineSummary ตรวจตัวเอง |
| r2 | F21 | Plan ข้อ 5 (ค) (เจ้าของตัดสินเอง) |
| r2 | F22 | render_report (แบบตายตัวทุกบรรทัด) |
| r2 | F23 | runner ข้อ 1 (holdout guard มาก่อน), AC-02 |
| r2 | F24 | baseline ข้อ 1 (`summarize(variant) == summary ของฐาน`) |
| r2 | F25 | AC-02, Negative cases |
| r2 | F26 | baseline ข้อ 5 (seam ของ `random.Random`), ข้อ 9 (ตรวจไม้ผ่าน expectancies), AC-04 (สูตร) |
| r2 | F27 | evaluate (base < 100 ไม้), signature ของ evaluate, AC-05 |
| r2 | F28 | AC-01 (ชนิดของ error), runner ข้อ 8 (append ok ล้ม) |
| r2 | F29 | evaluate (screen = `period_start_utc < cutoff`) |
| r2 | F30 | Invariants (ข้อยกเว้นของการตรวจ M1/M15) |
| r2 | F31 | D9 (warm-up) |
| r2 | F32 | evaluate (base เป็น select), ตาราง field (sides ของ random_entry), แถว 5 (None), render_report (key) |
| r3 | F33 | runner ข้อ 5 (setup เดียวต่อไฟล์), render_report (บรรทัด setup, จำนวนชุดข้อมูล), D16, AC-02, AC-06 |
| r3 | F34 | D10 (ขอบเขตจริง), evaluate (input ขาดได้ทุกจำนวนไม้), Plan ข้อ 5 (ฉ), AC-05 |
| r3 | F35 | runner ข้อ 5 (identity ไม่รวม run_id) |
| r3 | F36 | registry (รายการที่ `__post_init__` ตรวจ), evaluate (runs รับประกันโดย RunRecord), Negative cases |
| r3 | F37 | evaluate (ค่าของแถวเมื่อ input ขาด) |
| r3 | F38 | render_report (บรรทัดว่าง) |
| r3 | F39 | runner ข้อ 8 (exception ใดๆ หลังข้อ 6), seam ของ `registry.append_record`, รูปของ error |
| r3 | F40 | Plan ข้อ 5 (ค) ข้อเท็จจริง (i), (ii) |
| r3 | F41 | baseline ข้อ 1 (variant สร้างเองได้), AC-04 (ฐานที่สอง, ข้อมูลราคานิ่ง, ผลหารจบลงตัว) |
| r3 | F42 | runner (ผู้เขียนคนเดียวต่อไฟล์), Invariants, Plan ข้อ 5 (ฉ) |
| r4 | F43 | runner ข้อ 5 และ render_report ("นับงบ" ต่อ variant) |
| r4 | F44 | Plan ข้อ 5 (ก) Dataset ของ validation, (ง) select เดียวต่อ variant บน holdout (เจ้าของตัดสิน ไม่ขวาง tests) |
| r4 | F45 | render_report (ฐานของ Evaluation ต้องเป็นฐานที่ถูกล็อก), Negative cases |
| r4 | F46 | รายการที่ `__post_init__` ตรวจ (sizer_label ไม่ว่าง), Negative cases |
| r5 | F47 | render_report (ทุกส่วนอ่านเฉพาะ hypothesis ของ argument), Negative cases |

## Authorization (filled by the owner)
- อนุมัติแทนโดย delegation 2026-10-24 14:3x หลัง contract review r6 ได้ "Ready for test authoring: yes" · ใช้ได้จนกว่า CORE-008 merge หรือเจ้าของยกเลิก · veto ได้ก่อน merge · ผู้เขียน tests: patch ของ `tests/acceptance/CORE-008/**`, `tests/golden/CORE-008/**`, `tests/architecture/**` · Claude: implement, apply ตาม D-006, evidence, handoff, PROGRESS, push task branch

## Budget
1–2 sessions · headless session ไม่เกิน 6 (tests, tests review, implementation review ×2, สำรอง ×2) · contract review ใช้ subagent · 3 attempts ต่อปัญหาที่ไม่มีหลักฐานใหม่

## Recovery, compensation and checkpoint
revert PR · ไม่มีผลข้างเคียง (tests เขียนเฉพาะ `tmp_path`)

## DoR status / missing items / next action
ครบ: H001 (ข้อ 3, 4, 5, 7, 8, 9), CORE-007 contract v1.5 และโค้ด, architecture ข้อ 6.1–8 · contract review r1 (`docs/reviews/CORE-008-contract-r1.md`): ไม่พร้อม F1–F17 → v1.1 · r2 (`docs/reviews/CORE-008-contract-r2.md`): ปิด 16 ข้อ, F9 ค้าง + F18–F32 → v1.2 · r3 (`docs/reviews/CORE-008-contract-r3.md`): ปิดครบ, F33–F42 → v1.3 · r4 (`-r4.md`): ปิดครบ, F43–F46 → v1.4 · r5 (`-r5.md`, ตรวจแคบ): F43–F46 ปิด, F47 → v1.5 · r6 (`-r6.md`, ตรวจแคบ): F47 ปิด, **Ready for test authoring: yes** · next: ผู้เขียน tests (Claude session ใหม่, headless ที่ 1 จาก 6)

## Done scope
merge แล้ว, suite เขียวใน CI
