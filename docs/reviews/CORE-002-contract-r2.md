# Review CORE-002 contract round 2 · base e589edc · head 5bce19b · reviewer Codex, fresh headless review session

Reviewed on 2026-10-21, Asia/Bangkok (+07:00). Object: contract v1.1,
`docs/contracts/CORE-002-costs.md`, before test authoring. Compared exactly
`git diff e589edc..HEAD -- docs/contracts/CORE-002-costs.md` against round 1.
Full HEAD: `5bce19be7cc425d1f1847ea3ec88dfba49542759`; branch:
`feat/CORE-002-costs`. All contract locations below refer to this HEAD.

**Ready for test authoring: no**

F2–F7 are closed. F1 is still open: the chosen precision and rounding resolve
the 1/3 and caller-context questions, but the revised claim that multiplication
cannot lose digits is false even within its stated bounds. The universal exact
stress property still conflicts with precision 28. Every requested acceptance
number recomputes correctly; the remaining problem is the general contract,
not those numbers. No new finding or unrelated reopened matter is introduced.

Two test authors can now reproduce the same explicitly enumerated monetary
rows in AC-01–AC-04. They cannot yet write a complete suite satisfying every AC
and its applicable invariants without choosing how to resolve F1. One author
can enforce precision-28 equations, while another enforces the promised exact
doubling; the counterexample below proves those expectations disagree.

Scope and authority: used `adversarial-design-review` and `cross-agent-review`
for this explicitly authorized re-review of F1–F7 and their surrounding impact.
The prompt authorizes this report, so no additional permission was requested.
Only this review file is written, unstaged. No contract, PROGRESS, implementation,
tests, configuration, Git metadata, commit or external write is part of this
review. Read-only helpers independently checked F1/F2 and F5–F7; this session
alone assembled the report and independently recomputed the numbers.

## F1–F7 verdicts

| ID | Original severity | Verdict | File:line | Re-check evidence |
|----|-------------------|---------|-----------|-------------------|
| F1 | High | still open | docs/contracts/CORE-002-costs.md:80, :87–88, :123, :174 | Module-owned precision 28, ROUND_HALF_EVEN, caller-context independence, numeric Decimal equality and the explicit 1/3 result resolve those portions. However, :87 still promises lossless multiplication/addition for inputs with at most six fractional digits and integers at most 10^9; the in-bounds probe below rounds and violates :174's exact stress ×2 property. |
| F2 | Medium | closed | docs/contracts/CORE-002-costs.md:35, :41, :52, :59–80, :93–100, :138–141, :148 | Full round-trip annotations; no implicit scalar coercion; bool rejection; named errors for invalid side, nonfinite values and model domains; construction-time validation; lots validation before zero return; validation of both spreads before selection; and no error-order requirement for multiple simultaneous defects address the original cases. The numeric-bound wording remaining at :87 is handled under F1. |
| F3 | Medium | closed | docs/contracts/CORE-002-costs.md:35, :51, :55, :127, :144–148 | Positive API examples now use Decimal-string money/lots/R/factor defaults. Prose/table numbers are explicitly mathematical notation. Integer points/counts/sides and integer stress factors are explicitly permitted. Wrong scalar types remain separate negative cases. |
| F4 | Medium | closed | docs/contracts/CORE-002-costs.md:55–78, :137, :145, :147 | Normative spread/slippage/commission/stress equations apply stress once. Sides is a non-bool int >= 0 affecting only commission/slippage. Round trips always return CostBreakdown, retaining spread/swap at sides zero; the independently checked total is 1.48760. Total and stress_factor fields are specified at :74. |
| F5 | Medium | closed | docs/contracts/CORE-002-costs.md:50–53, :98, :103–104, :126, :136, :149 | Exactly 11 keys are enumerated; symbol/provenance/stress_factor are excluded. MappingProxyType wraps a new dict, source-dict mutation cannot affect the model, nested Provenance is frozen, and stress preserves provenance equality. AC-06 names mutation errors and missing/extra keys have BadProvenance. |
| F6 | Medium | closed | docs/contracts/CORE-002-costs.md:30, :72, :145–146 | Both synthetic models are explicit replacements of H001_COSTS with matching synthetic provenance. Lots, sides, side, nights and triple_nights are complete. Base/stressed nonzero commission and positive-swap credit have exact expected values, all recomputed below. Supplied rollover counts are distinguished from calendar dates. |
| F7 | Low question | closed | docs/contracts/CORE-002-costs.md:18, :30, :162 | Journal remains core-only and receives calculated values. PnL/integration ownership is deferred to a later contract without granting a new import. The separate R1 swap-attribution metric is deferred while historical-swap UNKNOWN and stress reporting remain required. |

## Outstanding finding

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | High | confirmed | docs/contracts/CORE-002-costs.md:61, :87, :174 | Exact scalar product is 28573.59557212382385913406202288; precision 28 returns 28573.59557212382385913406202. Recomputing after doubling stress returns ...12405, while doubling the rounded base returns ...12404. | Valid synthetic model with point, contract_size and stress_factor all Decimal("12.345678"), points Decimal("12.345678"), lots Decimal("1.23"), H001 volume limits/step and valid synthetic provenance. All values satisfy even the new six-fractional-digit/10^9 description. | A conforming implementation cannot satisfy both precision-28 evaluation and the unconditional exactness/doubling promises; test authors would freeze conflicting oracles. | Retain the selected precision policy, replace the no-loss claim with explicit per-operation rounding/evaluation order, and restrict exact linearity/doubling properties to the stated fixtures. Exact replacement wording follows. | Contract no longer claims general lossless multiplication or exact doubling; the counterexample has a single normative rounded result, while all AC monetary rows and 1/3 remain unchanged. Later tests must also verify caller-context independence and preservation. |

### F1 reproduction and exact replacement wording

This is the unresolved exactness portion of F1, not a new finding. No application
code was imported. A model with the listed positive fields passes the specified
constructor domains; lots 1.23 is within 0.01–200 and is a multiple of 0.01.
The model's changed base-field provenance can use the already specified
synthetic-fixture pattern; stress_factor is exempt from provenance. Its factor
can be produced by stress with factor 12.345678. The arithmetic is exactly the
formula at contract line 61.

Executed through `uv run --offline --no-sync python -B -`:

```python
from decimal import Context, Decimal, Inexact, ROUND_HALF_EVEN, localcontext

D = Decimal
x, lots = D("12.345678"), D("1.23")
with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)) as ctx:
    ctx.traps[Inexact] = True
    exact = x * x * x * lots * x
with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
    base = x * x * x * lots * x
    stressed = x * x * x * lots * (x * D("2"))
    twice_base = base * D("2")
    assert base != exact
    assert stressed != twice_base
```

| Calculation | Observed Decimal value |
|-------------|------------------------|
| Exact product, precision 80 with Inexact trapped | 28573.59557212382385913406202288 |
| Base product, precision 28 | 28573.59557212382385913406202 |
| Product with stress_factor doubled, precision 28 | 57147.19114424764771826812405 |
| Rounded base multiplied by 2, precision 28 | 57147.19114424764771826812404 |
| Difference between the last two rows | 1E-23 |

The small size of this difference does not resolve the contradictory oracle;
the contract explicitly requires exact Decimal equality. This is not evidence
of a trading loss or an implementation defect.

Proposed exact replacements, preserving the already chosen precision 28 and
all displayed acceptance answers, rather than silently changing that policy:

1. At `docs/contracts/CORE-002-costs.md:87`, replace the subclause beginning
   "การคูณและบวกของ input ที่รับ" and ending "ไม่สูญเสียหลักเลขที่ precision นี้" with:

   > การคูณและบวกอาจปัดที่ precision 28; ประเมินสมการตามวงเล็บและลำดับซ้ายไปขวาที่เขียนไว้ โดยปัดหลังแต่ละ operation; ชนิดและโดเมน input เป็นไปตามตารางด้านล่าง โดยไม่มีข้อจำกัดจำนวนหลักเพิ่มเติม

   Retain the surrounding module-owned context, ROUND_HALF_EVEN,
   caller-context preservation, 1/3 result and no-quantization requirements.
   This also removes the unexplained six-digit/10^9 parenthetical rather than
   leaving a new input restriction without a rejection rule.

2. At `docs/contracts/CORE-002-costs.md:174`, replace the property clause from
   "property:" through "เสมอ", retaining the Hypothesis admission condition, with:

   > property: สำหรับ fixtures ของ AC-01–AC-04 ให้ points_to_money เป็นเชิงเส้นใน lots และ points และ stress(m, 2) ให้ทุก charge เป็นสองเท่าพอดี; สำหรับ input อื่นให้ตรวจค่าตามสมการที่ประกาศใน Decimal context ของโมดูล โดยไม่อ้างความเป็นเชิงเส้นหรือการเพิ่มสองเท่าแบบ exact; round_trip_cost.total เท่ากับผลบวก spread + commission + slippage + swap ตามลำดับนี้ใน context เดียวกันเสมอ

No replacement is needed for F2–F7. These sentences are review proposals;
the contract has not been edited or approved by this reviewer.

## AC status

Implementation acceptance remains UNKNOWN for every AC: this review executes
independent arithmetic, not CORE-002 code or acceptance tests. Authoring
readiness is distinguished from implementation acceptance below.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | UNKNOWN | Fixed spread/point rows are unambiguous and arithmetic PASS; full numeric contract still has F1. |
| AC-02 | UNKNOWN | Sides, both models and commission stress rows are unambiguous and arithmetic PASS; general exact stress property still has F1. |
| AC-03 | UNKNOWN | All swap counts, fixtures, signs and stressed results are explicit and arithmetic PASS; general arithmetic invariant still has F1. |
| AC-04 | UNKNOWN | Long/short breakdowns, sides-zero total, R and stressed total are explicit and arithmetic PASS; general arithmetic invariant still has F1. |
| AC-05 | UNKNOWN | Original F2/F4 negative and zero-branch cases now have explicit outcomes. The numeric-scale/magnitude wording at :87 must be resolved as part of F1 before extending boundary rows from it. |
| AC-06 | UNKNOWN | F5 closure makes the exact key set, status/date/UNKNOWN assertions and immutable-copy checks authorable; no runtime mutation test was run. |
| AC-07 | UNKNOWN | No new ambiguity introduced; documentary red-flag scan ran. AST, purity and full-suite acceptance were not run in this contract-only task. |

## Checked, nothing found (and how)

### Decimal arithmetic audit

Used CPython 3.12.15 from the existing environment. All finite oracle calculations
used Decimal-string operands, precision 80, ROUND_HALF_EVEN and both Inexact and
Rounded traps enabled. Thus the oracle did not silently round these results.
The nonterminating 1/3 case was separately evaluated at precision 28 with
ROUND_HALF_EVEN; its Inexact flag is expected. Numeric Decimal equality was
used, not exponent/string equality, as contract line 88 requires.

Let `K = Decimal("0.001") * Decimal("100") * Decimal("0.02") = 0.002`.
The swap charge is `0 - points * K * stress_factor * weight`, with
`weight = nights - triple_nights + 3 * triple_nights`.

| Clause / row | Independent calculation | Expected and observed numeric value |
|--------------|-------------------------|-------------------------------------|
| AC-01 explicit / None fallback | 240 × K (fallback is explicitly 240) | 0.48 / 0.48 |
| AC-01 stressed spread | 240 × K × 2 | 0.96 |
| AC-01 one point / one lot | 1 × 0.001 × 100 × 1 | 0.1 |
| AC-02 slippage, base / stress | 50 × K × 2 × (1 or 2) | 0.20 / 0.40 |
| AC-02 zero commission, base / stress | 0 × 0.02 × 2 × (1 or 2) | 0 / 0 |
| AC-02 synthetic commission, base / stress | 3.5 × 1.5 × 2 × (1 or 2) | 10.5 / **21.0** |
| AC-03 long, one count / zero triple | (0 - (-503.8) × K) × 1 × (1 or 2) | 1.00760 / **2.01520** |
| AC-03 long, seven counts / one triple | (0 - (-503.8) × K) × (7 - 1 + 3) × (1 or 2) | 9.06840 / **18.13680** |
| AC-03 short, seven counts / one triple | (0 - 0 × K) × 9 × (1 or 2) | 0 / 0 |
| AC-03 synthetic credit, one count / zero triple | (0 - 100 × K) × 1 × (1 or 2) | **-0.20000 / -0.40000** |
| AC-04 long total | 0.48 + 0 + 0.20 + 1.00760 | 1.68760 |
| AC-04 sides-zero total | 0.48 + 0 + 0 + 1.00760 | **1.48760** |
| AC-04 R | 1.68760 / 25 | 0.067504 |
| AC-04 short total, exit spread 240 | 0.48 + 0 + 0.20 + 0 | 0.68 |
| AC-04 stressed long total | 1.68760 × 2 | 3.37520 |
| Decimal-context example | Decimal("1") / Decimal("3"), precision 28 | **0.3333333333333333333333333333** |
| Nested default stress | 1 × 2 × 2 | 4 |

All 23 finite scalar assertions passed, plus the precision-28 1/3 assertion.
The exact volume predicate also passed six rows: 0.01, 0.02, 200 accepted;
0.005, 0.015, 200.01 rejected. Sides-zero commission/slippage follow directly
from the specified multiplication by zero. No numerical correction to the
displayed AC answers is needed.

### Other resolved clauses

- Followed the diff and original F2 examples through each type/domain/error
  row. Invalid side, bool, nonfinite values, invalid constructor domains,
  invalid lots with zero sides and the unused negative spread each now have
  an explicit outcome. Multiple-invalid-input error ordering is intentionally
  unspecified, so tests must isolate one defect at a time.
- Checked the Decimal-string examples against their signatures (F3), and
  traced sides 0/1/2 and nonnegative integers through the stated equations
  (F4). Sides does not select or remove spread/swap.
- Counted the 11 provenance keys and their explicit exclusions, traced the
  immutable-copy and frozen-value requirements to AC-06, and confirmed stress
  preserves equality without requiring mapping object identity (F5).
- Compared synthetic replacements and all arguments to AC-02/03, including
  nonzero commission under stress and the short triple count (F6).
- Read the revised journal/PnL exclusions and deferred R1 metric; no new
  journal import authority or historical-swap certainty is asserted (F7).

### Commands and review evidence

All times below are 2026-10-21 +07:00; minute-only entries are approximate
session intervals. Every check refers to unchanged HEAD `5bce19b`.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean starting tree/index; expected task branch and HEAD. | 5bce19b | 20:47 |
| Numbered UTF-8 reads of contract, r1, review template and relevant AGENTS/PROGRESS/SPEC/Handbook/skills; requested `git diff e589edc..HEAD -- docs/contracts/CORE-002-costs.md` | PASS: F1–F7 and the entire revision inspected; findings above. | 5bce19b | 20:47–20:50 |
| `rg` source search | BLOCKED: `The term 'rg' is not recognized as the name of a cmdlet...` / CommandNotFoundException. Used native PowerShell reads/search, without environment changes. | 5bce19b | 20:47 |
| `Get-Content .python-version` | BLOCKED: `Cannot find path '.python-version' because it does not exist.` Existing `.venv/pyvenv.cfg` and the interpreter's `sys.version` supplied version evidence. | 5bce19b | 20:47 |
| Read-only stdin oracle via `uv run --offline --no-sync python -B -` | PASS, exit 0: 23 finite scalar assertions, six volume rows and 1/3; CPython 3.12.15. | 5bce19b | 20:49:13 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; one documentary pattern group explained below. | 5bce19b | 20:49 |
| Read-only stdin F1 probe via `uv run --offline --no-sync python -B -` | PASS reproduction, exit 0: exactness and exact stress promises FAIL on the same valid inputs; observed difference 1E-23. | 5bce19b | 20:49:58 |
| `git status --short`; `git diff --cached --name-only`; `git rev-parse HEAD`; `Test-Path docs/reviews/CORE-002-contract-r2.md` | PASS immediately before writing: tree/index clean, HEAD unchanged, target absent. | 5bce19b | 20:50:30 |
| `git status --porcelain=v1 --untracked-files=all`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD`; `git diff --check`; PowerShell read-only report structure/whitespace inspection | PASS after writing: only `?? docs/reviews/CORE-002-contract-r2.md`; tracked/staged diffs empty; HEAD unchanged; seven verdict rows and required sections present; no trailing-whitespace lines. `git diff --check` covers tracked content only, so the untracked report was checked separately. | 5bce19b | 20:53:24 |

Red-flag hits: the **Type checks disabled** group matches two inherited
documentation lines in `docs/reviews/CORE-001-agents-r1.md` and
`docs/tooling/compatibility.md` quoting an earlier suppression while explaining
it. Neither is a new code suppression. Secret and order/account-mutation groups
are empty; no deleted or renamed tests were reported. The scan also lists
inherited AGENTS.md/CLAUDE.md changes; their approval/CI is outside this re-review.
The scan ran before this report and does not scan untracked content. The report
is deliberately left unstaged.

## Not checked (and why)

- CORE-002 implementation, acceptance/golden/architecture execution, pytest,
  mutation tests and runtime validation/immutability/context isolation: this
  task is contract-only and precedes test authoring. The arithmetic probes are
  independent stdlib calculations, not implementation acceptance evidence.
- H001/SPIKE source provenance re-certification, unchanged architecture/risk
  decisions, historical swaps, calendars, R1 metrics or journal/PnL integration:
  those are outside the requested F1–F7 revision scope. No unchanged issue was
  reopened. F7 checks only the clarified boundary and explicit deferral.
- Broker/terminal, account, market-data, backtest, holdout, credential, network,
  dependency-install, CI, push or merge activity: none is required or authorized
  by this review.
- No general re-review of inherited branch changes, control tests, locked-path
  gate or approval-chain audit. No `/review` tool is exposed in this headless
  toolset; the requested contract re-review was performed directly.
- No edit to PROGRESS, handoff, contract or tests, and no staging or commit:
  the task explicitly permits only this review file. This report is the handoff.

**Ready for test authoring: no** — resolve the remaining F1 exactness/property
contradiction, then re-check F1 before freezing the full test contract. F2–F7
need no further changes for the issues reviewed here. The review is complete;
CORE-002's implementation delivery state is not advanced by this report.
