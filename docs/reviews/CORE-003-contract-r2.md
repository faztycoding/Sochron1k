# Review CORE-003 contract round 2 · base 79ac49b · head d79b3f5 · reviewer Codex, fresh headless session

Reviewed on 2026-10-22, Asia/Bangkok (+07:00). Object:
`docs/contracts/CORE-003-risk.md` v1.1, Tier High, on
`feat/CORE-003-risk`. Full HEAD:
`d79b3f550ee73dc3d42dc71ff106f3847a072654`.
Revision reviewed: `git diff 79ac49b..HEAD -- docs/contracts/CORE-003-risk.md`.
Contract line references below refer to this HEAD.

**Ready for test authoring: no**

Nine original findings are closed at contract level. F6 remains open only for
the Decimal exponent-range error boundary. F11 identifies a new inconsistency
between the gate's current equity and its halt predicates. F12 identifies
incomplete inputs in the newly added no-valid-grid golden example. All stated
numerical results recompute correctly; the problems are specification and
safety gaps, not an arithmetic error in the displayed examples.

**Could two test authors now write identical golden rows for every AC without
asking a question? No.** F6 permits different exception expectations for
subnormal results; F12 permits different full SizeDecision expectations.
The ordinary AC-02 through AC-05 examples now have deterministic predicates,
but AC-04 also codifies F11's unsafe combination of fresh equity and old flags.
The owner's plan/acceptance approval remains a separate prerequisite even
after these technical issues are fixed.

Applied `adversarial-design-review` and the re-review/output procedure of
`cross-agent-review`, limited to F1–F10 and the revision's surrounding impact.
Two read-only helpers checked gate/validation and halt/policy clauses; this
session checked the evidence and ran the independent arithmetic oracle.
The explicit task authorizes only this report. It supersedes generic requests
to write PROGRESS, a separate handoff, tests, or a commit. This unstaged report
is the handoff. No question, approval, staging, push, or .git write was needed.

## F1–F10 verdict table

“Closed” means the original contract defect is resolved, not that an
implementation passed tests or that a pending business policy was approved.
No original finding is classified reopened.

| ID | Verdict | Evidence at current file:line |
|----|---------|-------------------------------|
| F1 | closed | `docs/contracts/CORE-003-risk.md:94`, `:102`, `:104`, `:165`: no external SizeDecision; sizing uses current equity, actual stop distance, supplied model/budget and state.policy. Distance20 now sizes .01, so .02 is denied. The distinct halt/fresh-equity issue is F11. |
| F2 | closed | `docs/contracts/CORE-003-risk.md:72`, `:74`, `:77`, `:78`, `:85`, `:144`, `:182`: policy is embedded in state; operations have no replacement-policy argument; start/restart require the allowlist and reason; journal recovery/authentication remain explicitly E1 responsibilities. No claim that frozen objects prevent a caller discarding state. |
| F3 | closed | `docs/contracts/CORE-003-risk.md:85`, `:88`, `:89`, `:156`, `:164`: restart evaluates the daily transition and keeps its baseline/latch, then resets only the experiment. Same-day9800 and a first daily crossing during restart are verified below. Matches the owner's decision. |
| F4 | closed | `docs/contracts/CORE-003-risk.md:3`, `:8`, `:13`, `:15`, `:175`, `:189`, `:193`, `:201`: High, Q1/Q6=yes, owner plan/acceptance approval, security pre-review and owner-run demo are explicit. Authorization still pending is disclosed. |
| F5 | closed | `docs/contracts/CORE-003-risk.md:79`, `:80`, `:81`, `:82`, `:163`: separate same-day and new-day branches use the correct daily baseline; the experiment baseline/latch is independent. First-new-day9900 gives daily=false and baseline9900. |
| F6 | still open | `docs/contracts/CORE-003-risk.md:111`–`:129` fixes the original ordinary type/domain/timing cases. However `:42` and `:129` do not define whether the range includes exact subnormals or whether inexact underflow is an error. This was part of r1's requested arithmetic-result error oracle. Concrete divergence and replacement below. |
| F7 | closed | `docs/contracts/CORE-003-risk.md:38`–`:43`, `:148`: decisions use exact rationals; each display field rounds once from its own exact value; lots remain exact; comparisons use Decimal numerical equality and caller context is preserved by the specification. Both precision-boundary examples recompute .01. The separate range exception issue remains under F6. |
| F8 | closed | `docs/contracts/CORE-003-risk.md:64`–`:68`, `:153`, `:162`: cap is the largest grid point below max; below-min takes precedence after cap. Max.025 gives .02; min.026/max.029 gives zero. F12 concerns missing fixture operands, not this algorithm. |
| F9 | closed | `docs/contracts/CORE-003-risk.md:4`, `:19`, `:61`, `:70`, `:197`: the owner's zero-cost H001 default/E1 budget choice is recorded, and zero-cost mode explicitly makes no inclusive-SPEC-compliance claim. Cost10 boundary witnesses are below. |
| F10 | closed | `docs/contracts/CORE-003-risk.md:23`, `:131`–`:141`, `:167`: four numeric/count fields assumed, clearance unknown; all five provenance records are literal, including dates and notes; unknowns has a literal sorted tuple and copying/immutability expectations. |

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F6 | Medium | confirmed | docs/contracts/CORE-003-risk.md:42, :129; src/sochron/costs/model.py:21 | CONTEXT has Emin=-999999 but Etiny=-1000026. Exact subnormal 1E-1000000 survives rounding, while 1E-1000027 silently rounds to zero under its default traps. “Outside the exponent range” does not select a boundary/flag rule. | Valid equity4E-999998, stop12 yields exact R1E-1000000; an Emin-bound check raises RiskError, a context conversion returns it. | AC-01/06 cannot have a unique full range/error oracle. Ordinary examples are unaffected. | Specify subnormal acceptance and Overflow/Underflow handling explicitly; proposed sentence below. | A row at exact R1E-1000000 and a row at R1E-1000027 have one specified outcome, independent of caller context. |
| F11 | High | confirmed | docs/contracts/CORE-003-risk.md:94–103, :165 | Newly supplied current equity affects sizing but not halt predicates; those inspect only old flags. AC-04 even combines a clear baseline10000 state with equity100 without halt reasons. | Start10000, both flags false; check entry at current equity9800, long .02, entry4012.90, SL4000.90, exposures0. R24.5 sizes .02, so all listed predicates allow, although loss200 reaches daily75 and experiment200. | The new gate can authorize at a known halt threshold using individually valid current inputs. No ordering/freshness precondition closes this path. | Evaluate both threshold predicates from this equity as well as the latches, and state caller rollover/persistence ordering; isolate AC-04's low-equity fixture as proposed below. | This call returns both halt reasons; a previously latched halt survives recovery; rollover and the isolated below-min case still have specified outcomes. |
| F12 | Medium | confirmed | docs/contracts/CORE-003-risk.md:153, :162 | The new last synthetic case gives min.026/max.029 but no equity/stop/budget, after a synthetic case using stop1 and an original Given using stop12. | Author A inherits stop1, author B resets to stop12, both with equity10000/cost0. Both return lots0/below_min, but risk_per_lot is100 versus1200. | Two full golden SizeDecision rows differ while both satisfy the stated expected result. | State fixture reset semantics and give all operands for the no-grid row. Exact proposed sentence below. | Both authors derive (lots0, risk_money25, risk_per_lot100, actual_risk0, below_min_volume) from explicit inputs. |

## Exact replacement sentences

These are proposed contract edits, not applied changes or owner approval.

### F6 — replace the range rule at :42 and its duplicate at :129

> ฟิลด์แสดงผล `risk_money`, `risk_per_lot`, `actual_risk` ปัดครั้งเดียวจากค่า exact ภายใต้สำเนา `localcontext(CONTEXT)` โดยเปิด traps ของ `Overflow` และ `Underflow` และแปลงสอง exception นี้เป็น `RiskError`; อนุญาตผล subnormal ที่แทนค่า exact ได้ (`Subnormal` เพียงอย่างเดียวไม่เป็น error) แต่ไม่อนุญาตการปัด subnormal แบบ inexact รวมถึงการปัดค่าที่ไม่ใช่ศูนย์ให้เป็นศูนย์; ไม่ตรวจ exponent โดยเทียบกับ `Emin` เพียงอย่างเดียว และไม่แก้ context ของผู้เรียก

This chooses a precise conservative numerical-domain rule. It is not claimed
to follow already from the draft. Exact lots and exact decision predicates
remain governed by :39–40. Under this proposal, R1E-1000000 is accepted and
R1E-1000027 raises RiskError. Ordinary precision-28 rounding remains allowed.

### F11 — replace :97 and add caller ordering alongside :94–104

> `check_entry` ให้เหตุผล `daily_halt` เมื่อ `state.daily_halted or (state.day_start_equity - equity >= state.policy.daily_loss_limit * state.day_start_equity)` และ `experiment_halt` เมื่อ `state.experiment_halted or (state.experiment_start_equity - equity >= state.policy.experiment_loss_limit * state.experiment_start_equity)` โดยคำนวณทั้งสองแบบ exact; ผู้เรียกต้องส่ง `state` ที่เลื่อนเป็นวันไทยของคำขอด้วย `update_equity` และเก็บ state ที่คืนก่อนเรียก gate ทุกครั้ง เพื่อคง latch แม้ equity ฟื้นในครั้งถัดไป; gate ไม่แก้ state เดิม

Replace AC-04's low-equity example with:

> กรณี equity 100 ให้สร้าง state ใหม่ด้วย `start_experiment(Decimal("100"), date(2026, 10, 22), H001_RISK, "owner", "isolated sizing fixture")` แล้วใช้ request long lots 0.01 entry 4012.90 SL 4000.90 open_exposures 0 กับ equity 100 และ H001_COSTS, cost_per_lot 0 → `("below_min_volume", "lots_exceed_sized")`; เพิ่มกรณี state เริ่มต้นที่ equity 10000 flags False ทั้งคู่ กับ equity ปัจจุบัน 9800 และ request long lots 0.02 entry 4012.90 SL 4000.90 open_exposures 0 → `("daily_halt", "experiment_halt")`

If the original baseline10000/equity100 fixture is retained instead, its
corrected reasons become
`("below_min_volume", "daily_halt", "experiment_halt", "lots_exceed_sized")`.
This repair enforces the already specified thresholds; it does not introduce
a new risk percentage, restart privilege or business budget.

### F12 — add an AC-01 fixture rule and replace the final synthetic row

> ทุกกรณีของ AC-01 เริ่มจาก H001_COSTS, H001_RISK, equity `Decimal("10000")`, stop_distance `Decimal("12.00")` และ cost_per_lot `Decimal("0")` ใหม่ แล้วเปลี่ยนเฉพาะค่าที่ระบุในกรณีนั้น ไม่สืบทอดค่าจากกรณีก่อนหน้า; กรณีไม่มีจุดบน grid ใช้สำเนา H001_COSTS ที่เปลี่ยนเฉพาะ volume_min เป็น `Decimal("0.026")` และ volume_max เป็น `Decimal("0.029")` พร้อม provenance synthetic ตามที่ระบุ, equity `Decimal("10000")`, stop_distance `Decimal("1.00")`, cost_per_lot `Decimal("0")` → lots 0, risk_money 25, risk_per_lot 100, actual_risk 0, reason `"below_min_volume"`

Apply the same explicit no-grid operands to the duplicate example at :153.

## Remaining business decisions — separate from technical findings

The owner's three decisions are accepted as facts for this review:
same-day restart preserves the daily halt; sizing defaults to H001's
cost-free formula and E1 chooses the cost budget; Tier High. No further
approval is inferred from headless execution or from the earlier delegation.

| Pending choice already named at :198 | What remains for owner approval |
|---|---|
| (ก) Restart only while experiment_halted | No restart to refresh an unhalted experiment's budget. |
| (ข) Authorized initial start with reason | Apply the clearance allowlist/reason predicate to initialization too. |
| (ค) First supplied equity is day baseline | Caller must provide the midnight Asia/Bangkok valuation; late/gapped inputs otherwise leave daily loss unallocated. |
| (ง) Equity <=0 is BadEquity | R1/E1 must treat the exception as a stop, never continue using an old clear state. |
| (จ) Default allowlist and provisional limits | ("owner",) remains unknown; .25%/.75%/2%/1 remain assumed until Q-04 is answered. |
| (ฉ) Research halt treatment | R1 explicitly decides whether these halt rules apply to its research, without silently rewriting H001. |

**There is an additional choice outside (ก)–(ฉ): the experiment restart budget
is rebased to current equity, and the experiment halt stays latched through
recovery/new dates until authorized restart.** These policies are visible in
the body at `docs/contracts/CORE-003-risk.md:82`, `:89`, `:146`, `:164`,
but not covered by the owner's three stated decisions or fully enumerated in
the pending list. The old v1 pending item (ค) explicitly named the new
baseline; that disclosure was lost from the decision list in this revision.
The behavior is deterministic, not an arithmetic ambiguity, but must remain
an owner choice rather than become approved implicitly through golden tests.

Suggested addition to :198:

> (ช) experiment halt คงค้างแม้ equity ฟื้นหรือขึ้นวันใหม่ ปลดได้เฉพาะ restart ที่มีผู้มีสิทธิ์พร้อมเหตุผล และ restart ตั้ง experiment_start_equity เป็น equity ณ ตอน restart เพื่อเริ่มงบขาดทุนการทดลองใหม่

For example, restarting at9800 makes the next 2% experiment budget196,
not200; restarting after recovery at10500 makes it210. General daily
latching after recovery (:80/:146) should also be included in acceptance;
the owner's preservation-until-next-day decision supports that reading.
No additional hidden choice of percentages, cost amount, identity, or
research rule was found within this re-review's scope. Ignoring model
stress_factor in sizing (:69) leaves the final cost_per_lot budget with its
delegated R1/E1 caller; it is not evidence that a zero budget covers costs.

## AC status

Implementation acceptance remains UNKNOWN for every AC: this task reviews a
contract, not risk code or executable acceptance tests. “Authoring readiness”
below is a separate specification judgment, subject also to owner approval.

| AC | Status (PASS/FAIL/UNKNOWN) | Authoring readiness | Why |
|----|----------------------------|---------------------|-----|
| AC-01 | UNKNOWN | FAIL | All named numbers match the rational oracle; F6 affects range results and F12 prevents a unique full final fixture row. |
| AC-02 | UNKNOWN | PASS | Exact daily boundary, first-new-day9900 and experiment baseline retention are unambiguous. |
| AC-03 | UNKNOWN | PASS | Same-day daily preservation, threshold evaluation during restart, authorization failure and experiment reset rules are specified; business acceptance remains pending. |
| AC-04 | UNKNOWN | FAIL | Listed current-clause outcomes recompute, but F11 permits entry at known halt thresholds. |
| AC-05 | UNKNOWN | PASS | Side/price validation and each long/short narrowing, equality, widening and removal outcome are specified. |
| AC-06 | UNKNOWN | FAIL | Ordinary errors, validation timing, immutable values and literal provenance are specified; F6's range exception oracle remains incomplete. |
| AC-07 | UNKNOWN | PASS | Import/float/purity and zero-skipped-suite requirements are testable; High review obligations now align. Runtime/AST/suite compliance was not tested. |

## Checked, nothing found (and how)

### Exact recomputation of every revised numerical example

Executed `uv run --offline --no-sync python -B -` with stdin-only scripts,
CPython3.12.15 and `fractions.Fraction` from string operands. No risk
implementation, external library, market data or float arithmetic was used.
H001 model inputs (contract_size100, min/step.01, max200) were checked against
`docs/contracts/CORE-002-costs.md:111`–`:112`; the existing context
definition was checked at `src/sochron/costs/model.py:21`.
Display values were made from the exact terminating rational first, then
rounded once in a precision28/ROUND_HALF_EVEN context. Decision arithmetic
never consumed those rounded values.

For all sizing rows, rate=.0025 and step=.01. Unless explicitly overridden,
cost=0, min=.01, max=200. The no-grid row uses the explicit stop1 interpretation
proposed in F12; the alternative stop12 interpretation is also shown.

| AC-01 / related row | Exact R | Exact risk/lot | Exact raw lots | Uncapped grid lots | Max on grid | Final lots | Exact actual risk | Reason |
|---|---|---|---|---|---|---|---|---|
| equity10000, stop12 | 25 | 1200 | 1/48 | .02 | 200 | .02 | 24 | ok |
| Same with cost10 | 25 | 1210 | 5/242 | .02 | 200 | .02 | 24.2 | ok |
| equity100, stop12 | .25 | 1200 | 1/4800 | 0 | 200 | 0 | 0 | below_min_volume |
| equity100000000, stop.10 | 250000 | 10 | 25000 | 25000 | 200 | 200 | 2000 | capped_at_volume_max |
| equity9600, stop12 | 24 | 1200 | .02 | .02 | 200 | .02 | 24 | ok |
| equity9599.9999999999999999999999999, stop12 | 23.99999999999999999999999999975 | 1200 | 95999999999999999999999999999 / 4800000000000000000000000000000 | .01 | 200 | .01 | 12 | ok |
| equity800, stop1.0000000000000000000000000001 | 2 | 100.00000000000000000000000001 | 200000000000000000000000000 / 10000000000000000000000000001 | .01 | 200 | .01 | 1.0000000000000000000000000001 | ok |
| equity10000, stop1, max.025 | 25 | 100 | .25 | .25 | .02 | .02 | 2 | capped_at_volume_max |
| equity10000, stop1, min.026/max.029 | 25 | 100 | .25 | .25 | .02 | 0 | 0 | below_min_volume |
| F12 alternative stop12, same min/max | 25 | 1200 | 1/48 | .02 | .02 | 0 | 0 | below_min_volume |
| AC-04 farther stop20 | 25 | 2000 | 1/80 | .01 | 200 | .01 | 20 | ok |
| F9 boundary equity9600, stop12, cost10 | 24 | 1210 | 12/605 | .01 | 200 | .01 | 12.1 | ok |
| F11 current equity9800, stop12 | 24.5 | 1200 | 49/2400 | .02 | 200 | .02 | 24 | ok |

Only the two precision-edge display rows change value on rounding:
the numerator-edge R displays24 while lots remains.01; the denominator-edge
risk_per_lot displays100 and actual_risk displays1 while lots remains.01.
All other display fields above equal their exact values numerically.
Every row's nonzero lots is on-grid and its exact actual risk is <= exact R.
Max.025 gives floor(2.5)*.01=.02; min.026/max.029 gives max_on_grid.02<.026.
The stress-factor exclusion is explicit in the formula.

### AC-02 and AC-03 state sequences

Day0 is 2026-10-22; Day1 is 2026-10-23. Each independent sequence starts at
equity10000 with daily and experiment baseline10000 and both flags false.
Input state is not mutated by these mathematical transitions.

| Operation / sequence | Daily loss / threshold after rollover rule | Daily baseline; flag | Experiment baseline; flag |
|---|---|---|---|
| Day0 update9925.01 | 74.99 < 75 | 10000; false | 10000; false |
| Then Day0 update9925 | 75 = 75 | 10000; true | 10000; false |
| Then Day1 update9925 | 0 < 74.4375 | 9925; false | 10000; false (loss75<200) |
| Independent first Day1 update9900 | 0 < 74.25 | 9900; false | 10000; false (loss100<200) |
| Independent first Day1 update9800 | 0 < 73.5 | 9800; false | 10000; true (loss200=200) |
| Independent Day0 update9800 | 200 >= 75 | 10000; true | 10000; true (loss200=200) |
| Then Day0 authorized restart9800 | 200 >= 75; retain daily latch | 10000; true | 9800; false |
| Then Day1 update9800 | 0 < 73.5 | 9800; false | 9800; false (new experiment threshold196) |
| Alternative after Day0 halt: Day1 recovery10500 | 0 < 78.75 | 10500; false | 10000; true (latched despite loss=-500) |
| Then authorized restart10500 | 0 < 78.75 | 10500; false | 10500; false (new threshold210) |
| First-crossing-on-restart: Day0 halt9800, Day1 update10000, then same-Day1 restart9925 | 75 = 75 during restart | 10000; true | 9925; false (new threshold198.5) |

The last sequence is reachable through the specified API: before restart,
daily=false and experiment=true. It verifies that restart evaluates the new
equity instead of merely copying a false daily flag. Earlier dates are
TimeReversal. Restart without an existing experiment halt, disallowed names,
wrong case, empty/whitespace reason remain BadHaltClear after valid types.

### AC-04 and AC-05 predicates

For AC-04, unless a row says otherwise, use the initial clear10000 state,
current equity10000, long .02, entry4012.90, SL4000.90, exposures0, cost0.
The exact stop distance is12; farther SL3992.90 gives20.
These are the outcomes of the **current draft**, before the F11 repair.

| Change | Exact current-draft reasons |
|---|---|
| None | () |
| Only daily flag true / only experiment flag true | ("daily_halt",) / ("experiment_halt",) |
| exposures1 | ("max_exposure",) |
| SL None | ("missing_stop_loss",); no sizing branch |
| SL4012.90 / SL4013.00 | ("stop_loss_wrong_side",); no sizing branch |
| lots.03 | ("lots_exceed_sized",), since .03>.02 |
| SL3992.90, lots.02 | ("lots_exceed_sized",), since .02>.01 |
| lots.015 / lots0 | ("lots_not_on_grid",); .015/.01=1.5, zero disallowed |
| equity100, lots.01 | ("below_min_volume", "lots_exceed_sized"); .01>0 |
| Both halt flags, exposures1, equity100, lots.015 | ("below_min_volume", "daily_halt", "experiment_halt", "lots_exceed_sized", "lots_not_on_grid", "max_exposure") |

All nonempty tuples imply allowed=false; the empty tuple implies true.
The low-equity row is correctly recomputed as written, but its absence of
new halt reasons is part of F11, not an endorsement.

AC-05 exact comparisons also agree: long4000.90 to4001.00 increases the stop
by.10 (allowed), equality allowed, to4000.00 decreases it by.90 (widened);
short4024.90 to4024.00 decreases by.90 (allowed), to4025.00 increases by.10
(widened). None means missing_stop_loss; nonpositive/nonfinite prices are
BadStop, and an unknown side string is RiskError before branch selection.

### Minimal independent oracle / range reproduction

The executed stdin probes used this rational core; the tables above provide
the operands and asserted outputs. No production risk implementation was used.

```python
from fractions import Fraction as F

def oracle(equity, stop, cost="0", minimum=".01", maximum="200"):
    e, s, c, lo, hi = map(F, (equity, stop, cost, minimum, maximum))
    step = F(".01")
    r, per_lot = e * F(".0025"), s * 100 + c
    uncapped = ((r / per_lot) // step) * step
    cap = (hi // step) * step
    lots = min(uncapped, cap)
    reason = "capped_at_volume_max" if uncapped > cap else "ok"
    if lots < lo:
        lots, reason = F(0), "below_min_volume"
    assert lots % step == 0 and lots * per_lot <= r
    return lots, r, per_lot, lots * per_lot, reason
```

The range probe independently verified
`F(Decimal("4E-999998")) * F(".0025") == F(Decimal("1E-1000000"))`
and the corresponding equality for equity4E-1000025 / R1E-1000027.
With the existing Context definition:

| Exact value | Unary-plus result in CONTEXT | Relevant flags |
|---|---|---|
| 1E-1000000 | 1E-1000000 | Subnormal; no Underflow |
| 1E-1000027 | 0E-1000026 | Underflow, Subnormal, Inexact, Rounded, Clamped |
| 1E1000000 | Overflow exception | Overflow |

Emin=-999999, Emax=999999, Etiny=-1000026 were obtained from Context.
These observations demonstrate the F6 specification gap; they are not failed
tests of risk code.

### Other scoped checks

- Compared each r1 finding to the v1.1 diff and current clauses; no new risk
  percentage or dependency appears in the contract revision.
- The revised headless-run budget at :206 also adds correctly:
  Fraction(3)+Fraction(1)+Fraction(3)+Fraction(1)=8. Dates/version labels were
  checked as provenance or metadata, not interpreted as financial operands.
- Compared the three owner decisions in the prompt to :4/:19/:89/:197.
  No repeated approval was requested.
- Checked ordinary scalar/object errors, nonfinite domains, exact date rather
  than datetime, allowlist case/whitespace, negative exposures, malformed lots,
  missing/wrong-side stops and validation before business-denial branches
  against the completed table. Multi-invalid exception ordering is deliberately
  unspecified, so tests must isolate each fault.
- Literal H001_RISK provenance, sorted unknowns and copied immutable mapping
  are consistent. Legitimate bool flags are covered by their declared bool
  fields; the wrong-type rule does not prohibit those fields.
- Red-flag scan completed with two inherited pattern groups: type-check
  suppressions in CORE-002 negative unit tests/documentation, and lint-keyword
  mentions in existing documentation. No secret or order/account-mutation
  group hit. Listed locked-path changes belong to the inherited branch delta,
  not this review. No deleted/renamed tests were reported.

## Checks run

All results below concern HEAD `d79b3f550ee73dc3d42dc71ff106f3847a072654`;
timestamps are 2026-10-22 Asia/Bangkok (+07:00). No check changed the index.

| Command / check | Result | Commit | Time |
|---|---|---|---|
| `git diff 79ac49b..HEAD -- docs/contracts/CORE-003-risk.md` and numbered UTF-8 reads | PASS: reviewed the specified revision, r1 and template; source policy/context references read only | d79b3f5 | Before 07:28; exact per-read timestamps not captured |
| `rg -n ... PROGRESS.md SPEC.md docs/HANDBOOK-CORE.md` | BLOCKED: PowerShell reports "The term 'rg' is not recognized as the name of a cmdlet". No config changed; continued reads with Get-Content/Select-String. | d79b3f5 | Before 07:28; exact timestamp not captured |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit0; two inherited groups explained above, not a finding-free certification | d79b3f5 | 07:28 |
| `uv run --offline --no-sync python -B -` — primary Fraction/display/state/gate probe | PASS, exit0: 12 sizing rows, 13 gate rows, halt/restart sequences and stop comparisons; F11 counterexample asserted | d79b3f5 | 07:29:48 |
| Same command — exact Fraction inputs at exponent boundary | PASS, exit0: both huge-exponent equalities and Context outcomes confirmed; F6 ambiguity demonstrated | d79b3f5 | 07:31:08 |
| `git status --short`, `git diff --cached --name-only`, `git rev-parse HEAD`, `git diff --check 79ac49b..HEAD -- docs/contracts/CORE-003-risk.md` | PASS, exit0: clean tree/index before report, expected HEAD, no contract whitespace errors | d79b3f5 | 07:31:44 |
| `uv run --offline --no-sync python -B -` — both final no-grid fixture interpretations | PASS, exit0: stop1 gives risk/lot100, stop12 gives1200; both give lots0/actual0, demonstrating F12 | d79b3f5 | 07:32:23 |
| Same command — report structure/UTF-8 and Fraction run-budget check | PASS, exit0: all ten verdicts, both new IDs, required sections and verdict line present; 3+1+3+1=8 | d79b3f5 | 07:35:59 |
| `git status --short`, `git diff --name-only`, `git diff --cached --name-only`, `git rev-parse HEAD` | PASS, exit0: only this report untracked; tracked worktree/index unchanged; HEAD unchanged | d79b3f5 | 07:35:59 |

## Not checked (and why)

- Risk implementation, runtime immutability, executable acceptance/golden/AST
  tests, the full pytest suite, CI and owner demo: not this contract-only task.
  UNKNOWN, not passed and not tested-and-failed.
- Full security/leakage/mutation review, performance/resource bounds, and
  unrelated F01–F18 defects: outside the requested F1–F10 recheck/revision impact.
- Prior CORE-001/CORE-002 code and inherited control changes: not re-certified;
  only the referenced cost inputs/context were inspected for oracle accuracy.
- E1 broker integration, actual send binding, journal persistence/recovery,
  identity authentication and Thai-midnight valuation: future contracts.
  No terminal, account, credential store, market/holdout data or network used.
- Owner acceptance of (ก)–(ฉ) and the additional experiment reset/latch
  policy: not supplied; no approval inferred or solicited.
- No files except this report edited; no PROGRESS update, test, stage,
  commit, push, merge or deployment. This report remains the sole handoff.

The next action is for the contract author to resolve F6/F11/F12 and expose
the additional experiment-budget choice for owner acceptance, then request
the bounded recheck before test authoring. Delivery state: review report
implemented; CORE-003 implementation acceptance remains UNKNOWN, with no
claim of verified, merged or deployed risk functionality.
