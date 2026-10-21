# Review CORE-002 contract round 1 · base main · head e589edc · reviewer Codex, fresh headless review session

Reviewed on 2026-10-21, Asia/Bangkok (+07:00). Object: the approved-by-delegation
contract, before implementation or tests. This is an authoring-readiness review,
not approval, a code review result, or a change to the task's delivery state.

**Ready for test authoring: no**

All stated AC-01–AC-04 monetary answers recompute correctly. Six confirmed
contract defects below prevent an unambiguous test contract; F7 is a separate
nonblocking architecture question. No unsupported H001 default value or date
was found. Resolve F1–F6 in the contract before freezing golden tests.

Scope and authority: followed `cross-agent-review`, adapted to the explicitly
requested contract review and source list. The task prompt already authorized
this one review file. No additional approval question was needed. Only this file
is written, unstaged; no PROGRESS edit, test patch, commit, push, or configuration
change. Read-only helpers independently checked provenance and API ambiguity;
this session alone assembled the report.

Revision: `e589edc22c945b24f54f2d0f14865a972b4a4481`, branch
`feat/CORE-002-costs`. Initial working tree and index were clean. The full
`main...HEAD` path inventory includes inherited CORE-001 documentation/control
updates. The CORE-002 commits (`dd1db57`, `e589edc`) change only
`docs/contracts/CORE-002-costs.md`; those inherited changes are not new CORE-002
scope violations and are not re-certified here. Line references below refer to
this HEAD.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | High | confirmed | docs/contracts/CORE-002-costs.md:65, :88 | `r_multiple` admits Decimal 1 / 3, while every result must be exact. No finite Decimal represents that quotient. Ambient precision 4 also changes the AC-04 formula to total 1.688 and R 0.06752; precision 28 gives 1.687600 and 0.067504. | A nonterminating quotient or a caller with a different Decimal context. | The invariant is impossible as written; otherwise-identical valid inputs can yield different golden answers. | Define context ownership, precision/rounding or exact-result refusal, and numeric equality. See F1 below. | The contract specifies the full result or error for 1 / 3, behavior under a low caller precision, and preservation of the caller context. |
| F2 | Medium | confirmed | docs/contracts/CORE-002-costs.md:35, :40–68, :95–103 | The round-trip signature omits input annotations. Invalid side strings, bool-as-int, nonfinite Decimals, invalid model fields, and validation on zero/unused branches have no complete outcome/error contract. | Examples: side `"buy"`; factor `Decimal("NaN")`; model volume_step zero; lots outside bounds with sides zero; negative unused exit spread on a long. | Two test authors can choose different errors or accept/reject behavior; unsafe values can escape the negative-case oracle. | Add the full signature and a small type/domain/error table, including constructor validation and validation before early returns. See F2. | Every listed boundary example has one documented result/error, tested independently with all other inputs valid. |
| F3 | Medium | confirmed | docs/contracts/CORE-002-costs.md:35, :92, :106, :109 | Decimal-only lots/money conflict with literal calls using float lots `0.02`, integer lots `1`, and integer R `25`. | Copy the invariant/API examples literally into acceptance tests. | A conforming implementation must reject examples that the contract says return monetary values. | Replace concrete calls with Decimal-string operands; clarify prose/table notation. See F3. | All positive examples satisfy signatures; separate negative rows reject wrong scalar types without coercion. |
| F4 | Medium | confirmed | docs/contracts/CORE-002-costs.md:57–64, :102, :110 | Three APIs accept `sides`, but the negative-case section says unqualified `sides 0 -> 0`. Round-trip spread/swap do not depend on sides. Slippage/commission formulas are conveyed by units/examples rather than explicit equations. | AC-04 long inputs with sides zero. | One interpretation returns zero; another returns CostBreakdown with total 1.48760. AC-05 cannot select an oracle. | Scope sides to slippage/commission, state their equations and round-trip behavior, and specify accepted integer values. See F4. | Explicit rows for sides 0/1/2 and negative/wrong types; round trip always returns CostBreakdown. |
| F5 | Medium | confirmed | docs/contracts/CORE-002-costs.md:49–51, :85, :90–91, :111 | There are 11 base numeric fields before provenance, plus numeric stress_factor after it. AC-06 requires 11 entries, while the invariant requires provenance for every numeric model field and extra keys are forbidden. | Construct a provenance mapping with or without a stress_factor entry. | Either choice conflicts with a clause; construction and AC-06 cannot share one authoritative key set. | Exempt the derived stress_factor explicitly and enumerate the 11 keys. State copied immutable provenance, extending the MappingProxyType precedent already named at line 129. See F5. | Exact-key-set assertions, missing/extra-key rejection, unchanged provenance under stress, and caller-dictionary mutation cannot alter the model. |
| F6 | Medium | confirmed | docs/contracts/CORE-002-costs.md:107–108 | The custom commission model does not explicitly identify unchanged base fields; the short seven-night case omits triple_nights; the positive-swap case omits lots/night counts and an exact answer. | Two authors turn the synthetic cases into golden tables. | Different rows all satisfy the prose, so the contract does not freeze the intended independent oracle. | Fully specify the synthetic model and each argument/result, including nonzero stressed commission. See F6. | One complete numeric row per case; credit sign, triple counting, and nonzero commission stress have explicit expected values. |
| F7 | Low | question | docs/contracts/CORE-002-costs.md:18, :30; docs/architecture.md:207–214 | The goal says journal uses costs to calculate costs, and PnL is assigned to backtest/journal. The module map permits journal to import core only and describes journal as persistence. | A later implementer interprets this as permission for journal to import costs or own PnL calculation. | Future integration ownership is unclear; this does not require a forbidden import in CORE-002 itself. | Clarify that journal integration/PnL ownership is deferred and must respect the module map. See F7. | No statement in this contract grants journal a new dependency; the later integration contract identifies the calculation owner. |

## Exact clarifications and proof cases

### F1 — Decimal exactness and representation

`docs/contracts/CORE-002-costs.md:88` prohibits quantization, which does not
prevent normal Decimal arithmetic from rounding at the active precision.
`r_multiple(Decimal("1"), Decimal("3"))` cannot meet an unqualified exactness
promise. This needs an explicit technical decision; no source supplies a
precision or rounding mode that the test author can silently adopt.

One possible replacement, **proposed rather than already approved**, is:

> การคูณและบวกต้นทุนต้องไม่สูญเสียหลักเลขระหว่างทางสำหรับ input ที่รับ; `r_multiple` คำนวณใน local Decimal context precision 28, ROUND_HALF_EVEN; ทุกฟังก์ชันไม่ขึ้นกับและไม่แก้ context ของผู้เรียก และไม่ quantize เป็นหน่วยสตางค์; golden tests เทียบชนิด Decimal และค่าเชิงตัวเลข ไม่เทียบ exponent หรือรูปแบบ string

If this policy is chosen, the proposed 1 / 3 result is
`Decimal("0.3333333333333333333333333333")`. A documented refusal for
nonterminating quotients is also coherent, but must name its error and replace
the unconditional division promise. Do not invent that choice in tests.

`Decimal("0.20000") == Decimal("0.20")` is True. Their string forms differ.
The present contract does not demand a particular exponent; do not turn its
displayed trailing zeros into an additional representation requirement.

### F2 — Boundary types and errors

Replace the untyped signature with:

```text
round_trip_cost(side: Side, lots: Decimal,
                entry_spread_points: int | None, exit_spread_points: int | None,
                nights: int, triple_nights: int, model: CostModel,
                sides: int = 2) -> CostBreakdown
```

Suggested boundary sentence:

> ชนิดของ argument และฟิลด์ต้องตรง signature โดยไม่แปลงค่าอัตโนมัติ; bool ไม่ใช่ int ที่รับได้; ชนิดผิดให้ TypeError และ Decimal ทุกค่าต้อง finite; ตรวจ input ก่อนคืนศูนย์หรือเลือก spread ฝั่งที่ใช้ รวมถึงตรวจ lots ในทุก charge function

The contract then needs explicit domain/error rows. A minimal proposal using
the existing hierarchy, without new exception classes, is:

| Input/domain | Proposed outcome |
|---|---|
| Decimal-only money/lots/model fields receive int, str, bool or float; int-only fields receive Decimal, str, bool or float | TypeError |
| side is a string other than exactly `long` / `short` | CostsError; wrong side type remains TypeError |
| Nonfinite lots, factor, points, or r | BadVolume, BadStress, BadPoints, or BadR respectively |
| Nonfinite money passed to r_multiple | CostsError |
| Model point/contract_size/volume_step/volume_min nonpositive; volume_max below min; model commission/spread/slippage negative; weekday outside 0–6; model stress_factor nonpositive; any nonfinite numeric model field | CostsError, with the existing BadStress specialization for stress_factor |
| Provenance missing/extra key, invalid status, or malformed source/date/note | BadProvenance for invalid values; TypeError for wrong scalar types |
| Both round-trip spreads | Validate as int-or-None and nonnegative before selecting; only the selected None invokes fallback |

Also state whether generic `points_to_money` accepts signed points. A coherent
choice is to allow finite signed points there, while rejecting negative spread,
slippage and commission. Swap points already have an explicit signed meaning.
Document the model/provenance validation at construction so malformed instances
cannot enter the calculation API. Inputs with more than one defect need no
error-precedence requirement if the acceptance rows deliberately isolate one
defect at a time.

This is a missing-contract finding, not a claim that nonexistent code currently
accepts bad data. The stated CORE-001 precedent supports deliberate scalar
validation: `src/sochron/timebase/convert.py:22–28` rejects bool and wrong raw
types, and `src/sochron/timebase/errors.py:4–25` defines a ValueError hierarchy.

### F3 — Literal examples

Use these replacements at lines 92, 106 and 109:

```text
points_to_money(240, Decimal("0.02"), H001_COSTS) == Decimal("0.48")
swap_charge("long", Decimal("0.02"), 1, 0, H001_COSTS) == Decimal("1.00760")
points_to_money(1, Decimal("1"), H001_COSTS) == Decimal("0.1")
r_multiple(total, Decimal("25")) == Decimal("0.067504")
```

Add:

> ตัวเลขเงินและ lots ในข้อความและตารางเป็นค่าเชิงคณิตศาสตร์; ใน API และ golden tests ต้องสร้างจาก Decimal string เสมอ โดยไม่มี implicit coercion

### F4 — Sides and explicit equations

Replace the sides clause at line 102 with:

> sides เป็น int ที่ไม่ใช่ bool และมีค่าอย่างน้อย 0; มีผลเฉพาะ commission และ slippage ซึ่งเป็นศูนย์เมื่อ sides=0; round_trip_cost ยังคำนวณ spread และ swap ตามเดิมและคืน CostBreakdown เสมอ; sides ติดลบให้ BadSides และชนิดผิดให้ TypeError

Make the implied equations normative:

```text
spread_charge(p, lots, m) = points_to_money(m.spread_fallback_points if p is None else p, lots, m)
slippage_charge(lots, m, sides) = points_to_money(m.slippage_points_per_side, lots, m) * sides
commission_charge(lots, m, sides) = m.commission_per_lot_per_side * lots * sides * m.stress_factor
stress(m, f).stress_factor = m.stress_factor * f
```

Only stress_factor changes under stress; base cost fields and provenance remain
equal. This makes clear that stress is applied exactly once. Commission stress
is **already required** by lines 53 and 136; the issue is an implicit equation
and an insufficiently discriminating zero-valued fixture, not absent authority
to stress commission. With AC-04 long inputs and sides zero, the proposed total
is `0.48 + 0 + 0 + 1.00760 = 1.48760`.
State also that `CostBreakdown.stress_factor` equals the input model's factor
and its total is the sum of its four charge components (the latter is already
required by the property at contract line 136).

### F5 — Provenance schema and immutability

Replace the key/invariant wording with:

> provenance มี key ของ 11 base fields ต่อไปนี้เท่านั้น: point, contract_size, volume_min, volume_step, volume_max, spread_fallback_points, commission_per_lot_per_side, slippage_points_per_side, swap_long_points_per_night, swap_short_points_per_night, triple_swap_weekday; symbol, provenance และ stress_factor ไม่เป็น key; stress_factor เป็นค่าที่ได้จากการคูณ factor เริ่มที่ Decimal("1") และบันทึกแยกจาก provenance

Add:

> CostModel เก็บ immutable copy ของ provenance ที่ผู้เรียกส่งมา; การแก้ dict ต้นทางภายหลังไม่เปลี่ยน model และแก้สมาชิกของ model.provenance ไม่ได้

This operationalizes the existing frozen/MappingProxyType intent, not a new
abstraction. `src/sochron/timebase/rules.py:18` and `:32–45` demonstrate the
frozen dataclass/read-only mapping precedent. A frozen dataclass alone does not
prove that a caller-owned nested dict cannot change.

### F6 — Complete synthetic golden rows

Suggested additions to AC-02/03:

> model สมมติเป็นสำเนาของ H001_COSTS ที่แก้เฉพาะค่าที่ระบุและ provenance ของค่านั้นเป็น assumed จาก synthetic test fixture; commission=Decimal("3.5"), lots=Decimal("1.5"), sides=2 ให้ Decimal("10.5") ที่ stress_factor=1 และ Decimal("21.0") ที่ stress_factor=2

> ทุกแถว swap ใช้ lots=Decimal("0.02"); แถว 7 คืนทั้ง long และ short ใช้ nights=7, triple_nights=1; แถว swap long บวกใช้ Decimal("100"), side="long", nights=1, triple_nights=0 ให้ charge Decimal("-0.20000") และเมื่อ stress ×2 ให้ Decimal("-0.40000")

Clarify that nights are supplied chargeable rollover counts, including the
triple_nights subset. A seven-count example is arithmetic on supplied counts,
not proof of a seven-calendar-night broker schedule. Counting dates/weekends,
rollover time, and historical schedules remains excluded under line 30. No new
calendar policy should be inferred from this fixture.

### F7 — Future journal integration

Suggested clarification:

> CORE-002 คืนค่าต้นทุนแบบ pure เท่านั้น; การคำนวณ PnL และการส่งค่าที่คำนวณแล้วเข้า journal อยู่ใน contract ถัดไปซึ่งต้องเคารพ module map โดย journal ยัง import ได้เฉพาะ core

This is nonblocking for the current pure module once its limited scope is
understood. It does not request a module-map change in this task.

## AC status

Implementation acceptance is UNKNOWN for every AC: CORE-002 code and tests do
not exist and were not run. The separate readiness column evaluates whether the
contract gives the later test author a complete oracle; arithmetic checks below
do not constitute implementation acceptance.

| AC | Status (PASS/FAIL/UNKNOWN) | Authoring readiness | Why |
|----|----------------------------|---------------------|-----|
| AC-01 | UNKNOWN | FAIL | Numeric answers correct; F1/F3 affect arithmetic/types and F2 affects invalid-input interpretation. |
| AC-02 | UNKNOWN | FAIL | Numeric answers correct; F4 sides semantics and F6 custom fixture need clarification. Nonzero commission stress must not be hidden by the zero fixture. |
| AC-03 | UNKNOWN | FAIL | Stated long/short numbers correct; F2 side/domain policy and F6 complete synthetic inputs remain open. |
| AC-04 | UNKNOWN | FAIL | Totals and R correct; F1 rounding/context, F3 R type and F4 sides behavior remain open. |
| AC-05 | UNKNOWN | FAIL | F2 lacks a complete boundary/error oracle; F4 makes sides-zero expectations ambiguous. |
| AC-06 | UNKNOWN | FAIL | Table values/statuses match sources, but F5 conflicts on the required provenance key set. |
| AC-07 | UNKNOWN | PASS | Import/no-float/purity requirements are authorable and consistent with the module map. No costs source exists to test; only the documentary red-flag scan was run. |

## Checked, nothing found (and how)

### Exact arithmetic audit

Recomputed independently with CPython 3.12.15 `decimal.Decimal`, precision 80
and the Inexact trap enabled for the finite oracle calculations. All decimal
operands were constructed from strings (integers only for counts/points); no
application imports, data reads, research runs, quantization, or pytest.

Let `K = Decimal("0.001") * Decimal("100") * Decimal("0.02") = 0.002`.
The swap multiplier is `nights - triple_nights + 3*triple_nights`; charge is
the negative of signed swap points times K times the multiplier times stress.

| Clause | Independent calculation | Exact numeric result |
|---|---|---|
| AC-01 explicit spread / None fallback | 240 × K, twice | 0.48 / 0.48 |
| AC-01 stressed spread | 240 × K × 2 | 0.96 |
| AC-01 one point, one lot | 1 × 0.001 × 100 × 1 | 0.1 |
| AC-02 slippage two sides, base / stress | 50 × K × 2 × (1 or 2) | 0.20 / 0.40 |
| AC-02 zero commission, base / stress | 0 × 0.02 × 2 × (1 or 2) | 0 / 0 |
| AC-02 synthetic commission | 3.5 × 1.5 × 2 | 10.5; proposed stressed row 21.0 |
| AC-03 long, 1 night / 0 triple | -(-503.8) × K × (1 - 0 + 0) | 1.00760; stress 2.01520 |
| AC-03 long, 7 nights / 1 triple | -(-503.8) × K × (7 - 1 + 3) | 9.06840; stress 18.13680 |
| AC-03 short, 7 supplied nights | -(0) × K × multiplier | 0 at base and stress, regardless of valid triple count |
| AC-03 positive swap, proposed complete row | -(100) × K × (1 - 0 + 0) | -0.20000; stress -0.40000 |
| AC-04 long components and total | 0.48 + 0 + 0.20 + 1.00760 | 1.68760 |
| AC-04 R | 1.68760 / 25 | 0.067504 |
| AC-04 short, entry 100 / exit 240 | Uses exit: 240 × K; plus 0.20 + 0 + 0 | spread 0.48; total 0.68 |
| AC-04 long stress | 1.68760 × 2 | 3.37520 |
| Invariant at line 92 | Same spread/one-night calculations above | 0.48 / 1.00760 |
| Nested default stress | 1 × 2 × 2 | stress_factor 4 |
| H001 units | 240 × 0.001; 50 × 0.001; 503.8 × 0.001 × 100 | 0.24 USD/oz; 0.05 USD/oz; 50.38 USD/lot/night |

The volume predicate was also evaluated exactly: 0.005, 0.015, 200.01 fail;
0.01, 0.02, 200 pass inclusive min/max and zero remainder modulo 0.01.
Zero spread and zero valid night counts give zero by the formulas. Charge sign
is explicit for swap: negative broker swap is an expense; positive broker swap
is a credit. No numerical mismatch was found in the stated answers. Formula
linearity, the component sum, and multiplication by a stress factor hold
algebraically where all inputs satisfy the chosen domain; F1 prevents claiming
them for an unspecified finite-precision implementation.

### Every H001_COSTS table value and provenance

All references in this table are repository documents, not a new broker lookup.

| Contract field/value/status | Source and result |
|---|---|
| symbol XAUUSDm | H001:19 and SPIKE-001:46; matches. |
| point 0.001 / contract_size 100, measured | SPIKE-001:13,50–51 identify captured API specification fields; matches. |
| volume_min 0.01 / volume_step 0.01 / volume_max 200, measured | SPIKE-001:51; matches all three. |
| spread_fallback_points 240, measured | SPIKE-001:54 records floating spread 240; H001:67 explicitly permits that fallback. Snapshot measurement is not evidence of historical spreads. |
| commission_per_lot_per_side 0, assumed | H001:67 explicitly requires R1 confirmation; matches. |
| slippage_points_per_side 50, assumed | H001:67 explicitly labels 50 points per side [A]; matches. |
| swap_long -503.8 / swap_short 0, spec | SPIKE-001:54 and H001:19,67; values and point-based units match. Contract notes preserve historical UNKNOWN. |
| triple_swap_weekday 2, assumed | H001:67 assumes Wednesday pending confirmation; SPIKE-001:59,68 transcribes Wednesday multiplier 3 from the owner's screenshot. Conservatively retaining assumed is permitted; not a discrepancy. |
| as_of 2026-10-21 on all 11 provenance entries | H001:4,19,67 and SPIKE-001:13,33–40,59 support the recorded date. |
| stress_factor 1 / default stress ×2 | Baseline and stress distinction in H001:68,77; no new H001 business value. Provenance coverage exception still needs F5. |

Here H001 means `docs/hypotheses/H001-m15-momentum-breakout.md`, and SPIKE-001
means `docs/evidence/SPIKE-001.md`. Read H001 sections 2, 3, 6, 7, 8 and the
SPIKE specification/swap evidence. No source-status upgrade is required.

`unknowns()` ordering is already specified at contract line 66: sorted by field
name. The tuple at lines 85/111 is correctly ordered:
`commission_per_lot_per_side`, `slippage_points_per_side`,
`triple_swap_weekday`. Its exclusion of historical swap uncertainty is deliberate:
those fields describe today's specification; their UNKNOWN notes must also be
exposed in later reports. The contract already requires that at lines 81–85 and
124/128. Do not redefine unknowns to include spec fields without a contract change.

### Architecture, phase gates, scope and owner sensitivity

- `costs` imports only stdlib plus core, matching `docs/architecture.md:207`.
  No accepted operation needs timebase: nights and triple_nights are inputs,
  and date-to-rollover counting is excluded at contract line 30. Money
  conversion here does not require a clock, MT5, random, I/O or new dependency.
- PnL exclusion keeps the present arithmetic task bounded; backtest ownership
  is compatible with `docs/architecture.md:208`. Future journal wording needs
  the clarification in F7. No module-map change is proposed here.
- `docs/architecture.md:287` and `docs/reviews/D-001-design-r1.md:120` require
  frozen provenance and preserved unknowns before R1 selection. Current-swap
  notes and deferred R1 validation satisfy that documentary boundary; they do
  not prove historical swaps. ENV-1 and an approved R1 contract remain required
  before research, as H001:10 and architecture:289 state.
- Seven ACs, one pure module, and no external trust-boundary crossing: within
  the requested limit of seven ACs/three boundaries. Clarify within the existing
  ACs; no split is needed for this scope. The four cost components do not create
  four external boundaries.
- Q1–Q5 remain no for this task. Q6 adds reviewer-owned tests through the
  established patch workflow, without changing CI, permissions or policy;
  the contract does not authorize changing controls. Standard remains coherent
  for the scoped pure module. Inherited control-path changes are separate work.
- No invented H001 business default was found. Commission 3.5, lots 1.5 and
  positive swap 100 are explicitly synthetic test fixtures. Arbitrary positive
  stress factors are API flexibility; the approved default stress remains ×2.
- **Owner-visible addition:** contract line 124 prescribes a future R1 report of
  the proportion of PnL dependent on swap. The cited phase gate requires exposed
  uncertainty/provenance, but does not define that metric. This is a new reporting
  expectation, not an approved numeric trading value. Suggested wording:
  “R1 ต้องแสดงที่มาและความไม่แน่นอนของ swap ย้อนหลัง; metric สำหรับ swap attribution ให้กำหนดใน contract R1 ที่อนุมัติ”.
  Deferring that metric does not weaken the existing UNKNOWN requirement.
- The proposed F1 precision and F2/F4 boundary policies are review proposals,
  not claims of previously approved business decisions. The delegated contract
  revision must choose and state them before tests freeze those choices.

### Review checks and red-flag leads

All checks below refer to HEAD `e589edc`; times are 2026-10-21 +07:00.
Minute-only read/search intervals are approximate session intervals; explicitly
recorded timestamps are shown for the numeric probes and Git-state checks.

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean starting tree/index; expected task branch and approved-delegation HEAD. | e589edc | 20:26–20:27 |
| Numbered UTF-8 reads (`Get-Content -Encoding utf8`) of contract, sources, template, CORE-001 precedent, relevant SPEC/PROGRESS/Handbook sections | PASS: evidence inspected; findings above. | e589edc | 20:27–20:32 |
| `git diff --stat main...HEAD`; `git log -6 --oneline`; `git diff --name-only dd1db57^...HEAD` | PASS: identified inherited changes; CORE-002 task commits change only the contract. | e589edc | 20:27–20:31 |
| `rg` source search | BLOCKED: `The term 'rg' is not recognized as the name of a cmdlet...` (CommandNotFoundException). Native PowerShell reads/search supplied the evidence; no environment repair. | e589edc | 20:27 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; one documentary pattern group, explained below. No secret or order/account-mutation group; no deleted/renamed tests. | e589edc | 20:29:33–20:29:34 |
| Read-only stdin script via `uv run --offline --no-sync python -B -` | PASS, exit 0, CPython 3.12.15: all finite monetary expectations and six volume rows match; Inexact trap enabled for oracle arithmetic. No pytest or application code. | e589edc | 20:30:47–20:30:48 |
| Same permitted Python command, reduced-context probe | PASS reproduction: precision 4 -> total 1.688 / R 0.06752; precision 28 -> 1.687600 / 0.067504. Supports F1; not an application test. | e589edc | 20:31:39 |
| `git rev-parse HEAD`; `git status --porcelain=v1`; `Test-Path docs/reviews/CORE-002-contract-r1.md` immediately before writing | PASS: unchanged HEAD, clean tree, target did not exist. | e589edc | 20:32:27 |
| `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD` after creating this report | PASS: only `?? docs/reviews/CORE-002-contract-r1.md`; tracked diff and staged diff empty; HEAD unchanged. | e589edc | 20:36:52 |

The red-flag group is **Type checks disabled**, with two lines in inherited
documentation: `docs/reviews/CORE-001-agents-r1.md` and
`docs/tooling/compatibility.md` quote an earlier type-suppression hit while
explaining it. Neither is a new code suppression. The scan lists inherited
AGENTS.md and CLAUDE.md control changes; their approval/CI is outside this
contract review. The scan ran before this untracked report and does not scan
untracked content. The report is intentionally not staged to include it.

Walked Handbook F01–F18 for this object: no missing implementation is presented
as done; no tests/dependencies/lockfiles are changed; no existing costs module
was found; boundary/error gaps are F1–F6; no secrets, external actions or unsafe
commands were introduced. Concurrency and duplicate sends have no current
effect surface in this pure module. Resource bounds for arbitrarily large
Decimals/counts are not specified; no performance claim is made.

## Not checked (and why)

- No CORE-002 implementation, acceptance/golden tests, pytest run, AST execution,
  mutation test, or runtime model-validation test: none exists yet, and this
  task explicitly requests review before authoring. Proposed proof cases above
  have not been executed against application code.
- No broker/terminal connection, market ingestion, strategy/backtest, holdout
  access, historical swap reconstruction, R1 calendar calculation or PnL
  integration. Those are outside this task and its authorizations.
- No original Specification screenshot inspection: SPIKE-001:59 says it is not
  stored in the repository. Reviewed its committed transcription and retained
  the approved assumed status for Wednesday.
- No external financial documentation lookup, new dependency admission, CI,
  PR label, approval-chain audit or merge verification. This review checks
  consistency with the named local sources and accepts the explicit delegation
  supplied in the task prompt.
- No comprehensive re-review of inherited CORE-001 housekeeping/control diffs,
  no CORE-002 handoff or implementer explanation, and no edits to the contract
  or PROGRESS. No `/review` tool is exposed in this headless toolset; performed
  the requested contract review directly rather than claiming that command ran.

**Ready for test authoring: no** — revise F1–F6, then re-review those IDs and
their surrounding clauses before the later fresh Codex test-authoring session.
