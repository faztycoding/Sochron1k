# Review CORE-003 contract round 1 · base main · head 79ac49b · reviewer Codex, fresh headless review session

Reviewed on 2026-10-22, Asia/Bangkok (+07:00). Object: draft v1 of
`docs/contracts/CORE-003-risk.md`, before risk implementation or tests.
Full HEAD: `79ac49ba8f8967d45622a06315deba2dfb3801a7`; branch
`feat/CORE-003-risk`. All source line references below refer to this revision.

**Ready for test authoring: no**

The stated numerical examples in AC-01 through AC-05 recompute correctly.
The contract nevertheless permits an over-budget entry, has contradictory halt
transitions, and lacks complete validation and rounding oracles. Nine confirmed
findings and one owner-decision question follow. This is readiness evidence,
not implementation acceptance, policy approval, or permission to trade.

Applied `adversarial-design-review` and `cross-agent-review`, adapted to the
explicit contract-only task. Two read-only helpers independently checked source
policy and API testability; this session checked their evidence, performed the
exact arithmetic, and wrote only this report. The user's explicit instruction
authorizes this file and supersedes generic requests to update PROGRESS, write
a separate handoff, commit, or ask permission. No approval is inferred from the
previous CORE-002 delegation. This report is the handoff and remains unstaged.

The starting tree and index were clean. HEAD adds the draft and a PROGRESS
checkpoint; the larger `main...HEAD` inventory contains inherited CORE-001 and
CORE-002 work. Those inherited changes are not new CORE-003 scope violations
and are not re-certified here.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | High | confirmed | docs/contracts/CORE-003-risk.md:78, :51, :79–86; SPEC.md:65 | `check_entry` compares request lots to an unrelated `SizeDecision`; it never checks the sizing stop distance, current equity, cost budget, model or policy. | AC-01 sizing at distance 12 permits .02 lots; use that decision with entry 4012.90 and correctly sided SL 3992.90. Every listed gate predicate passes, but principal risk is 40 USD against R25. | The proposed risk gate can authorize an over-budget trade even when every argument has the declared type and valid individual domain. | Bind the gate to current risk inputs and recompute sizing from the request, as proposed below. Update its signature and denial rules. | Original AC-04 remains allowed; a farther stop or stale higher-equity sizing cannot authorize .02 lots when recomputation permits only .01. Model/policy/budget mismatches also have a defined outcome. |
| F2 | High | confirmed | docs/contracts/CORE-003-risk.md:40–47, :62–78, :107–108; docs/architecture.md:210; AGENTS.md:115–117 | Frozen objects prevent field assignment, but each call accepts a replaceable policy; no state/decision binds the run's policy. `start_experiment` also initializes a clear state without authorization. | Start under .0075 daily loss limit, then evaluate equity 9925 using a new .02 limit; or discard a halted state and call `start_experiment` again. | The API alone cannot guarantee no runtime policy change, no risk increase after loss, or that only authorized restart clears an existing experiment halt. | Bind the approved policy and experiment lifecycle to the state; distinguish initialization, authorized new experiment, and process recovery. Explicitly assign persistence/authentication to E1 without claiming that frozen dataclasses enforce them. | Replacement policy is rejected for an existing experiment; recovery retains existing baselines/latches; initialization is never treated as authority to resume a previously halted run. |
| F3 | High | confirmed | docs/contracts/CORE-003-risk.md:64, :71–74, :108, :144 | Restart returns `start_experiment`, clearing both flags and replacing both baselines, while :144 says daily halt clears only on a new Thai day. | Baseline 10000, equity 9925, daily halt, then same-day restart by `owner` with a reason. | The contract both allows and forbids resuming trading that day; it can repeatedly reset the daily loss budget. | Preserve/evaluate the daily baseline and latch on a same-day experiment restart, or obtain an explicit owner-approved exception and revise the contrary clauses. | A golden sequence fixes the outcome of same-day restart, including when the supplied equity first crosses the daily limit during restart; new-day restart is separate. |
| F4 | High | confirmed | docs/contracts/CORE-003-risk.md:3, :13–15; docs/HANDBOOK-CORE.md:55, :64; SPEC.md:30; AGENTS.md:11–13 | Q6 is answered no because locked tests arrive via patch. The task itself introduces risk-policy enforcement and halt-clear control. Handbook Q6 explicitly includes policy. | Implement the proposed loss limits and restart authority under the stated Standard tier. | The risk classification and verification/approval plan do not reflect the control change; the patch mechanism does not establish containment. | Answer Q6 yes and classify High; align approval and verification requirements, or record an owner-approved, evidenced narrowing of scope before lowering the tier. | Consistent Q6/tier/authorization/evidence requirements throughout the revised contract; no inferred delegation. |
| F5 | Medium | confirmed | docs/contracts/CORE-003-risk.md:67–69, :115, :123 | New-day reset sets a new baseline, but the following equation subtracts old `state.day_start_equity` and uses unqualified `day_start_equity` on the right. | On AC-02's next-day equity 9925, the mixed formula is 75 >= 74.4375, hence true; AC-02 expects false. First new-day equity 9900 similarly gives 100 >= 74.25. | Two implementations produce different halt flags at the same transition. | Write explicit same-day and later-day branches, using the effective baseline consistently; evaluate the experiment latch independently in both. | First observation below the previous day's threshold still gives the owner-approved new-day result; AC-02 and exact threshold neighbors agree with the equations. |
| F6 | Medium | confirmed | docs/contracts/CORE-003-risk.md:36, :47, :62–91, :127; docs/contracts/CORE-002-costs.md:90–100 | `BadStop/RiskError ตามตาราง` references no table and chooses no exception. Invalid side, nonfinite values, constructor validation, and error-versus-reason behavior are incomplete. | Examples: exposures -1, entry 0, stop 0, side `buy`, NaN lots, invalid halt baseline, invalid current/new stop, or a halted state combined with a malformed request. | Test authors must guess an error class, when it occurs, and whether to return reasons instead; costs errors may leak unexpectedly. | Add the field-specific type/domain/error table and validation timing described below. | Each negative row has one exact exception and validation stage; business denials collect all sorted unique reasons only after input validation. |
| F7 | Medium | confirmed | docs/contracts/CORE-003-risk.md:36, :53–58, :153; docs/contracts/CORE-002-costs.md:86–88 | Exact floor/comparison is required, but use of `CONTEXT` does not specify rounding of returned R, per-lot risk or actual risk, or whether rounded intermediates feed decisions. | Equity 9599.9999999999999999999999999, stop 12: exact R is just below 24 and lots is .01; first rounding R to precision 28 produces 24 and lots .02. | Following CORE-002's per-operation convention blindly can oversize; public golden fields also lack a unique rounding oracle. | Separate exact decision arithmetic from public Decimal representation; specify operation/rounding order, equality and caller-context preservation. | Both numerator and denominator boundary probes below have one outcome; all reported Decimal fields have a reproducible oracle under different caller contexts. |
| F8 | Medium | confirmed | docs/contracts/CORE-003-risk.md:55–57, :153; src/sochron/costs/model.py:106–109; src/sochron/costs/charges.py:95–101 | A valid CostModel need not have its maximum on the step grid. Sizing caps directly to that maximum while promising grid-aligned lots. | Synthetic min .01, step .01, max .025, contract size 100; equity 10000, stop 1 gives uncapped .25, then cap .025. | Sizing returns a nonzero volume that `check_volume` rejects, contradicting the universal grid property. | Cap to the largest exact grid multiple <= volume_max, then check volume_min; define reason precedence and the no-valid-grid case. | Max .025 yields .02 with capped reason; min .026/max .029/step .01 yields zero with below-min reason, or an explicitly chosen risk-domain error. |
| F9 | Medium | question | docs/contracts/CORE-003-risk.md:19, :27, :31, :154; SPEC.md:65; docs/hypotheses/H001-m15-momentum-breakout.md:43, :45 | The zero-cost default reproduces H001, but SPEC's risk limit includes costs. A configurable parameter exposes both formulas; it does not decide which policy governs. The draft already identifies an owner decision. | Equity 9600, stop 12 gives R24 and principal risk24; a budget of 10 USD/lot makes .02 lots risk24.20. | An unapproved choice could be frozen into tests as though it satisfies both sources. | Record the owner's reconciliation; meanwhile explicitly label zero-cost mode as H001 formula compatibility, not evidence of inclusive SPEC compliance. Do not invent a budget. | Owner decision is recorded and the approved cost treatment has boundary golden rows; labels remain assumed/unknown until their actual source changes. |
| F10 | Medium | confirmed | docs/contracts/CORE-003-risk.md:23, :94–104, :127; src/sochron/costs/model.py:55–69 | The goal says all H001_RISK fields are assumed, but halt_clearers is unknown. The table requires provenance to match without saying whether source/note prose is literal or a semantic predicate. | Test the goal literally, or independently choose source strings/note wording from the descriptive table. | Tests disagree on status or reject equivalent provenance; the unresolved clearance default can look more settled than it is. | Say four numeric/count fields are assumed and halt_clearers unknown; publish literal source/note values or explicit predicates, including the empty-note case. | All five values, dates, statuses, keys and note/source checks have one assertion rule, and unknowns remains the specified sorted tuple. |

## Finding details and proposed contract wording

The replacements below are proposals for the contract author and owner. They
are not applied, and business-policy choices are not approved by this review.

### F1–F2: bind the gate and state to the inputs whose risk was checked

The F1 counterexample does not require forged objects or invalid inputs:

```text
size_position(equity=10000, stop_distance=12, H001 model/policy) -> .02 lots, R25
request: long, .02 lots, entry4012.90, stop3992.90, exposures0
principal loss = (4012.90 - 3992.90) * 100 * .02 = 40 > 25
current check_entry predicates -> reasons (), allowed True
```

Merely checking that SizeDecision is frozen or internally arithmetically
consistent cannot fix this: the decision is legitimate but belongs to another
stop distance. The same problem occurs with stale equity or a different model,
cost budget or policy. Proposed replacement requirement:

> `check_entry` คำนวณ sizing ใหม่จาก equity ปัจจุบัน, ระยะ `abs(entry_price - stop_loss)` แบบ exact, cost budget, CostModel และ policy ที่ผูกกับการทดลองเดียวกัน; ห้ามใช้ SizeDecision จาก input อื่นเป็นหลักฐานอนุญาต และต้องตรวจว่า lots ของ request ไม่เกินผลที่คำนวณใหม่

The signature must expose those inputs, or the contract must define an equally
testable immutable binding carrying them. Specify what happens for a missing
or wrong-side stop before attempting sizing; the existing denial reasons should
still be returned for well-typed requests with those business conditions.
For the distance-20 counterexample, fresh sizing is floor_step(25/2000) = .01,
so request .02 receives `lots_exceed_sized` under a recomputing design.

For F2, proposed binding sentence:

> การทดลองผูกกับ policy ที่อนุมัติไว้ตั้งแต่เริ่ม; การประเมิน state และ gate ของการทดลองเดิมด้วย policy ต่างค่าให้ `BadPolicy`; frozen ป้องกันการแก้ object แต่ไม่ถือว่าเป็นหลักฐานว่าผู้เรียกเปลี่ยน policy ระหว่างรันไม่ได้

This is not a demand for authentication or disk I/O inside risk. A pure library
cannot establish caller identity or prevent a caller from discarding all state.
Document the boundary accurately:

> `start_experiment` ใช้เริ่มการทดลองใหม่ที่ได้รับอนุมัติเท่านั้น ไม่ใช่ API สำหรับ process restart; ผู้เรียกใน E1 ต้อง restore policy, baselines และ halt flags ของการทดลองเดิมจาก journal และเมื่อ state หายหรือไม่ทราบให้หยุด ไม่เริ่มใหม่โดยอัตโนมัติ; การเริ่มใหม่แทนการทดลองที่ halt แล้วต้องผ่าน authorization ของ `restart_experiment`

Add the corresponding E1 handoff obligation, including binding state and any
gate result to the actual send inputs. Architecture :233 and :290–293 require
gate/journal enforcement and recovery before external actions. CORE-003 cannot
certify that a future sender always calls it or preserves the checked request.
The name allowlist is a pure predicate; `authorized_by="owner"` is not proof
of a human authorization. That limitation is already disclosed at contract
:31 and :141 and is not a newly discovered authentication implementation bug.

### F3–F5: give day transition and experiment restart separate rules

The broad idea of resetting a daily limit on a new Thai day is compatible with
SPEC :65. It must not be implemented by carrying the previous day's baseline
into the new day's comparison. Proposed replacement for :67–69:

> ถ้า `day == state.day` ให้คง day_start_equity เดิมและใช้ `daily_halted = state.daily_halted or (day_start_equity - equity >= daily_loss_limit * day_start_equity)` แบบ exact; ถ้า `day > state.day` ให้ตั้ง day_start_equity = equity และ daily_halted = False โดยไม่เปรียบเทียบกับ baseline วันก่อน; ทั้งสองกรณีคง experiment_start_equity เดิมและประเมิน experiment_halted ด้วย latch เดิมแบบ exact; วันที่ย้อนหลังให้ TimeReversal

Under this proposed first-observation policy, a drop from old baseline 10000 to
9900 on the first call of the new day produces daily false and baseline9900;
the experiment comparison still uses 10000. At first-new-day equity9800,
daily resets but experiment halt becomes true. This does not establish whether
loss occurred before or after midnight: there is no intraday timestamp or
midnight valuation in this API. The owner must accept that consequence or
specify a separately supplied opening baseline; do not infer it in golden tests.

Proposed replacement for restart, preserving the stated daily invariant:

> `restart_experiment` ตรวจชื่อและเหตุผลก่อนอนุญาต; ประเมินกฎ daily ด้วย equity/day ที่ส่งมาโดยไม่ reset baseline ในวันเดิม แล้วคง daily baseline/flag ที่ได้; reset เฉพาะ experiment_start_equity เป็น equity และ experiment_halted เป็น False; วันใหม่ใช้กฎ rollover เดียวกับ update_equity

This covers the subtle case where daily_halted was false before restart but the
restart equity itself reaches the daily loss threshold. Simply copying the old
false flag would miss that loss. If the owner wants same-day daily-budget reset
instead, state that exception expressly, remove :144's exclusive new-day claim,
and add an owner-approved acceptance row. Also decide whether restarting an
unhalted experiment is intended; the draft permits it at :74 but no cited source
defines that policy. An authorized new experiment and recovery after a process
crash are different transitions.

For F4, the minimum classification correction is:

> Q6 changes controls: yes — งานนี้เพิ่มการบังคับ risk policy, halt transitions และสิทธิ์ปลด halt; Tier High

Re-answering the remaining questions: Q2–Q5 are no for the scoped pure module
(no money movement, data storage/migration or irreversible external action).
Q1's exclusion of authentication is explicit, but introducing a halt-clear
allowlist is an authorization-policy question; under Handbook :55/:59 its
uncertainty cannot be resolved merely by saying there is no authentication
system. Q6 already establishes High irrespective of that Q1 distinction. The
High verification/approval plan must be made concrete before implementation;
this authorized read-only review does not itself need to change controls.

### F6: the contract needs a type/domain/error table

Yes, a table equivalent in purpose to CORE-002 v1.2 is needed. The slash in
`BadStop/RiskError ตามตาราง` is not a precise oracle. RiskError is a named base
class, but the contract never assigns it uniquely to the affected inputs.
`BadVolume` is defined by costs, not by the risk hierarchy. Its conversion to
`lots_not_on_grid` versus propagation is also unspecified for nonfinite input.

Proposed baseline sentence:

> ตรวจชนิดและโดเมนของ dataclass ตอนสร้างและของ argument ก่อนเลือก branch หรือคืน GateDecision ตามตารางนี้; ชนิดผิดให้ TypeError โดยไม่แปลงค่า; bool รับเฉพาะฟิลด์ bool และไม่รับแทน int/Decimal; input ผิดหลายอย่างไม่กำหนดลำดับ exception และ acceptance ทดสอบทีละความผิด; เมื่อ input ถูกต้องจึงรวบรวมเหตุผลปฏิเสธทั้งหมด เรียงตัวอักษรและไม่ซ้ำ

The contract author should complete at least these rows; the suggested outcomes
use the existing hierarchy rather than silently adding new exceptions:

| Input/domain requiring an oracle | Proposed outcome or decision to record |
|---|---|
| Wrong declared scalar or object type, including model/policy/state/decision and container types | TypeError; explicitly state constructor versus function timing. |
| side is str but not exactly long/short | RiskError, in both EntryRequest and check_stop_change; non-str remains TypeError. |
| equity or either halt baseline nonfinite or <=0 | BadEquity, including start/restart and direct HaltState construction. |
| entry_price, non-None stop_loss, stop_distance, current_stop or non-None new_stop nonfinite or <=0 | BadStop. None is allowed only in the declared optional stop fields, producing missing_stop_loss. |
| open_exposures negative | RiskError; bool is TypeError, not one exposure. |
| finite request lots <=0, out of model bounds or off-grid | Keep the existing lots_not_on_grid denial; collect other applicable business reasons too. Constructor must not reject the finite zero row required by AC-04. |
| request lots NaN, sNaN or Infinity | Choose a single outcome, e.g. RiskError before reason evaluation; define it explicitly rather than accidentally inheriting a Decimal exception or costs.BadVolume. |
| policy fractions nonfinite/outside (0,1), invalid exposure limit, negative/nonfinite cost_per_lot | BadPolicy; specify the cost-budget field even though it is not part of RiskPolicy. |
| halt_clearers empty tuple, blank/whitespace names, duplicate names, non-str members; authorized_by/reason normalization | Define acceptance and exact error separately. A non-str member is a type error; valid strings not on the allowlist must not clear a halt. |
| provenance not Mapping; missing/extra keys or non-Provenance values; malformed Provenance fields | TypeError for the container; BadPolicy for key/value mismatch per :47; explicitly retain or translate the reused Provenance constructor's TypeError/BadProvenance. |
| day and provenance dates | State whether datetime subclasses count as date; for trading-day inputs, a plain date-only rule avoids hidden time/zone comparisons. |
| direct SizeDecision/GateDecision construction | Define finite/domain and cross-field consistency, including allowed == (reasons == ()), sorted unique reasons, and SizeDecision reason/zero-lots consistency. |
| Arithmetic result outside the selected Decimal context's representable range | State the exception or supported input bounds; accepted finite input alone is not an overflow oracle. |

Validate malformed inputs even if a halt already denies entry or a missing stop
would allow an early return. Error precedence among multiple malformed fields
can remain deliberately unspecified, as CORE-002 :100 does. Reason ordering is
already specified at :77 and :125; no new ordering policy is needed. A wrong-side
positive SL is a business denial, while a nonpositive or nonfinite price is a
domain error: preserve that distinction in the table.

### F7–F8: exact decision arithmetic and volume-domain compatibility

Two exact counterexamples were recomputed with Fraction(Decimal(string)):

| Inputs | Exact decision | Premature precision-28 rounding |
|---|---|---|
| equity 9599.9999999999999999999999999, rate .0025, stop12, contract100, step .01 | R = 23.99999999999999999999999999975; floor lots .01 | R rounds to 24; floor lots .02 |
| equity800, rate .0025, stop1.0000000000000000000000000001, contract100, step .01 | per-lot risk100.00000000000000000000000001, R2; floor lots .01 | per-lot risk rounds to 100; floor lots .02 |

Suggested representation rule, separate from policy approval:

> คำนวณ R, risk ต่อ lot, floor/cap/grid และ loss-threshold predicates จาก input เดิมแบบ exact rational; lots ที่คืนเป็น Decimal ของจำนวน step ที่ได้แบบ exact; ฟิลด์แสดงผล risk_money, risk_per_lot และ actual_risk ปัดครั้งเดียวจากค่าที่ exact ของแต่ละฟิลด์ด้วย localcontext(CONTEXT) precision 28 ROUND_HALF_EVEN โดยไม่ quantize เป็นสตางค์ และไม่ใช้ค่าที่ปัดแล้วตัดสิน risk; ไม่แก้ context ของผู้เรียก; golden เทียบชนิด Decimal และค่าเชิงตัวเลข ไม่เทียบ exponent/string

If this convention is chosen, define `actual_risk` from exact lots times the
exact per-lot risk, not from its rounded display field. State that the safety
inequality concerns exact underlying exposure and budget. The author may choose
another deterministic representation, but must not weaken the already required
exact floor and inclusive exact loss comparison. CORE-002's ordered rounding is
a precedent to specify arithmetic, not a rule to copy into risk decisions.

For the cap, a minimal replacement is:

> คำนวณ uncapped lots บน grid แบบ exact แล้วจำกัดด้วย `floor_exact(volume_max / volume_step) * volume_step`; หลัง cap ถ้า lots < volume_min ให้ lots=0 และ reason=below_min_volume; มิฉะนั้นใช้ capped_at_volume_max เมื่อ cap ลด lots และ ok เมื่อไม่ลด

No costs edit is required. Its current model domain deliberately permits
off-grid min/max; its check_volume correctly demands bounds and exact grid
membership. If risk instead rejects such models, name that narrower domain and
error rather than claiming that every accepted CostModel is supported.

## Owner-sensitive decisions (not approved by this review)

The numerical defaults .0025/.0075/.02/1 come from the sources. The following
additional policies do not follow uniquely from SPEC/H001 and must be visible
to the owner; some are already listed at draft :154, others are not:

| Proposed policy | Source gap / decision needed |
|---|---|
| cost_per_lot defaults to zero; R1/E1 choose the budget; model stress_factor is ignored by sizing (:19, :27, :60, :154) | SPEC :65 includes costs; H001 :43 omits them. Choose the reconciliation and who supplies a complete, possibly stressed budget. Do not estimate new business values here. |
| First received equity is the Thai-day baseline; later-day calls automatically clear daily halt (:67, :154) | SPEC says Thai-day baseline, not first-observation valuation. Delayed first observations and gaps can move losses outside the previous daily window. |
| A daily halt remains latched after recovery until a later day (:68, :144) | Conservative but not an explicit transition rule in SPEC. Confirm the latch and reset semantics. |
| Experiment halt remains latched across recovery/dates; only authorized restart with nonblank reason clears it (:69, :108) | SPEC says stop at 2%; Q-04 leaves clearing authority open. Confirm the transition and audit obligation. |
| Restart resets experiment capital to current equity and is permitted while not halted (:71–74) | Neither source defines repeated resets or their relation to one experiment/run identity. Decide this expressly. |
| Same-day restart resets daily budget as currently written (:64, :73) | Contradicts the new-day-only explanation; F3 requires owner resolution, not a test-author guess. |
| halt_clearers=("owner",), nonempty allowlist, caller-supplied names (:45, :102) | Consistent with the owner being the approver, but the literal default is a proposal and does not answer Q-04 or authenticate the caller. Keep unknown until approved. |
| One fixed approved policy per run versus replacement between calls (:23, :107) | Runtime changes are already prohibited by architecture :210; choose concrete binding/enforcement, not permission to increase limits after losses. |
| Applying these daily/experiment state rules to H001 research as well as E1 (:18) | H001 specifies sizing and one position, but not these halt transitions. R1 must record which rules govern research without silently rewriting the immutable hypothesis. |
| Rejecting equity <=0 as BadEquity (:59, :70), with halt handling delegated to callers | The draft chooses this domain; SPEC's loss rule alone does not say to discard such observations. Confirm that R1/E1 treat this error as stop, never permission to continue using an old clear state. |

Proposed clarification for F9:

> cost_per_lot=0 ใช้ทวนสูตร sizing ที่ลงทะเบียนใน H001 เท่านั้น ไม่ใช่หลักฐานว่าผ่าน SPEC ที่รวม cost budget; การเลือกสูตรและ budget สำหรับ R1/E1 ต้องมีคำตัดสินของเจ้าของที่อ้างถึงความต่างนี้ก่อน claim ว่าผ่าน risk policy

No new risk percentage, capital floor, cost estimate, principal identity,
overnight-loss allocation or restart privilege is approved here. Headless mode
does not delegate those decisions to either agent.

## AC status

Implementation acceptance is UNKNOWN for every AC: risk code and its tests do
not exist. Readiness below assesses the draft, not runtime behavior. Missing
owner approval is independently a prerequisite before authoring the final
acceptance contract.

| AC | Status (PASS/FAIL/UNKNOWN) | Authoring readiness | Why |
|----|----------------------------|---------------------|-----|
| AC-01 | UNKNOWN | FAIL | All stated numbers correct; F7/F8 leave general arithmetic/cap behavior incomplete, and F9 needs the cost-policy decision. |
| AC-02 | UNKNOWN | FAIL | Exact 75 USD boundary correct; F5 makes rollover contradictory; F2/F6 affect policy and state validation. |
| AC-03 | UNKNOWN | FAIL | Exact 200 USD boundary and sticky recovery example correct; F2/F3 leave lifecycle and same-day restart inconsistent. |
| AC-04 | UNKNOWN | FAIL | Listed valid-input examples recompute; F1 permits an over-budget entry and F6 leaves invalid-input behavior undefined. |
| AC-05 | UNKNOWN | FAIL | All stated long/short comparisons correct; F6 lacks a complete side/price/domain-error oracle. |
| AC-06 | UNKNOWN | FAIL | F6 needs an actual table; F10 needs consistent statuses and source/note assertions. Frozen-object checks do not establish F2's run invariant. |
| AC-07 | UNKNOWN | UNKNOWN | Dependency/purity intent is coherent and red-flag scan ran, but no risk implementation, AST coverage or suite exists; F4 changes required verification planning. |

## Checked, nothing found (and how)

### Exact recomputation of the displayed examples

Used only read-only Python through `uv run --offline --no-sync python -B -`,
with PYTHONPATH=src. CPython was 3.12.15. Fraction of Decimal-string operands
supplied the independent rational oracle. Imported only existing costs constants
for model values and the Decimal context; no risk code was available or run.
No float, market input or backtest was involved. Both stdin probes exited 0 and
all assertions passed, including the counterexample assertions above.

| AC-01 case | Exact R | Exact risk/lot | Exact raw lots | Step floor before cap | Returned lots | Actual risk | Reason |
|---|---|---|---|---|---|---|---|
| equity10000, stop12, budget0 | 25 | 1200 | 1/48 | .02 | .02 | 24 | ok |
| equity10000, stop12, budget10 | 25 | 1210 | 5/242 | .02 | .02 | 24.20 | ok |
| equity100, stop12, budget0 | .25 | 1200 | 1/4800 | 0 | 0 | 0 | below_min_volume |
| equity100000000, stop .10, budget0 | 250000 | 10 | 25000 | 25000 | 200 | 2000 | capped_at_volume_max |
| equity9600, stop12, budget0 | 24 | 1200 | .02 exactly | .02 | .02 | 24 | ok |

The bare `equity100` AC-01 example uses the original stop12 and budget0 fixture;
make that explicit in the eventual golden row. Its stated lots/reason also stay
zero/below-min if the preceding budget10 is retained, but other output fields
differ. Each golden fixture should spell out every argument.

| AC-02/03 comparison | Exact loss / threshold | Result |
|---|---|---|
| baseline10000, equity9925.01 | 74.99 / 75 | Daily false before any earlier latch. |
| baseline10000, equity9925 | 75 / 75 | Daily true; equality is included. |
| baseline10000, equity9924.99 | 75.01 / 75 | Daily true. |
| New-day baseline9925, equity9925 | 0 / 74.4375 | Daily false under the stated reset intent; F5 addresses the contrary formula. |
| experiment baseline10000, equity9800.01 | 199.99 / 200 | Experiment false before any earlier latch. |
| experiment baseline10000, equity9800 | 200 / 200 | Experiment true; equality is included. |
| experiment baseline10000, equity9799.99 | 200.01 / 200 | Experiment true. |
| After experiment halt, next-day equity10500 | -500 / 200 | Raw predicate false, but experiment_halted remains true through the latch. |

Also checked exact equality and a positive 1E-30 neighbor using baseline
10000.00000000000000000000000001. The equality halts; equity just above the
exact threshold does not. No pre-comparison rounding was used.

AC-04 base stop distance is 4012.90 - 4000.90 = 12. Request .02 is on-grid and
equals sizing .02. Each single change gives the stated reason: one open exposure
hits max1; SL4012.90 and SL4013.00 are wrong-side; .03 exceeds .02 but is on-grid;
.015 is 1.5 steps; zero is below minimum. Missing SL gives missing_stop_loss.
Replacing sizing with zero yields both below_min_volume and lots_exceed_sized.
The independent predicate probe covered all eleven named single/base cases and
one combined case. With both halts, exposures1, missing SL, request .015 and
below-min sizing0, the exact sorted tuple is:

```text
(below_min_volume, daily_halt, experiment_halt, lots_exceed_sized,
 lots_not_on_grid, max_exposure, missing_stop_loss)
```

AC-05 long deltas are +.10, 0 and -.90 for 4001.00, 4000.90 and 4000.00 from
4000.90: allowed, allowed, widened. Short deltas are -.90 and +.10 for 4024.00
and 4025.00 from 4024.90: allowed, widened. None is the specified missing-stop
denial. Directional comparison never needs a clock, floats or timebase. H001
itself has no trailing stop (:40); this general helper's existence must not be
used as authority to add trailing behavior to H001.

### H001_RISK provenance audit

| Field | Value / date / status in draft | Source and note assessment |
|---|---|---|
| risk_per_trade | .0025 / 2026-10-21 / assumed | Matches SPEC :65 and H001 :43; note Q-04 open is accurate. Inclusive cost interpretation remains F9. |
| daily_loss_limit | .0075 / 2026-10-21 / assumed | Matches SPEC :65; Q-04 remains open at :87. Thai-day baseline is sourced, while the exact first-observation transition is an owner proposal. |
| experiment_loss_limit | .02 / 2026-10-21 / assumed | Matches SPEC :65; note Q-04 open is accurate. Restart semantics are additional policy. |
| max_open_exposures | 1 / 2026-10-21 / assumed | SPEC :65 covers positions plus pending; H001 :39 specifies one position. No numeric mismatch; no note is specified, so declare empty note or a predicate for F10. |
| halt_clearers | ("owner",) / 2026-10-22 / unknown | Q-04 does not supply this literal value. Date is the draft proposal date and unknown is appropriate; note correctly excludes agents but must not imply name-only authentication. |

The first four dates are consistent with the dated source snapshot; the costs
Provenance class describes as_of as a source-read date (:56), not an approval
date. Do not recast these dates as measurements or owner confirmation. H001
registration on 2026-10-21 does not close Q-04. Provenance has exactly five keys;
neither the provenance mapping itself nor calculated cost_per_lot is a sixth
policy key. Immutable-copy intent is explicit. The expected unknowns tuple is
correctly sorted and includes all five fields.

Suggested F10 wording:

> H001_RISK มี risk_per_trade, daily_loss_limit, experiment_loss_limit และ max_open_exposures สถานะ assumed; halt_clearers สถานะ unknown; ตารางระบุค่า source/note แบบ literal หรือ predicate ที่ acceptance ต้องตรวจโดยชัดเจน และช่อง note ที่ไม่มีข้อความใช้สตริงว่าง

### Architecture, scope and safety boundaries

- The risk import allowlist of stdlib, sochron.core and sochron.costs matches
  architecture :210. Provenance, CostModel, H001_COSTS, CONTEXT and check_volume
  are exported by costs (`__init__.py:9–31`). Existing check_volume uses exact
  integer ratios (`charges.py:88–101`); CORE-003 need not modify costs.
- Caller-supplied Thai date avoids time conversion inside risk. Nothing in the
  requested API needs a timebase import, I/O, clock, MT5, random, or a dependency
  installation. The contract's intended AST/no-float checks are compatible with
  exact arithmetic; actual implementation enforcement remains untested.
- With fixed inputs, the sizing formula lowers or preserves risk budget when
  equity falls; it contains no martingale multiplier. H001 max1 rejects additional
  exposure, preventing averaging down under that fixed policy. F1/F2 identify
  the binding gaps that prevent making those claims for arbitrary caller flows.
- Well-typed valid stop-change comparisons forbid widening/removal in both
  directions and allow equality. Invalid side/price behavior remains F6.
- Q-04 resolution before E1 is explicitly required at :140. Journal, actual
  send enforcement, terminal identity, authenticated authorization, persistence,
  reconciliation and concurrency remain E1 obligations under architecture
  :290–293. No order path is introduced by this contract.
- Count: seven ACs, three cohesive behavior areas (sizing, halt transitions,
  gate predicates) in one pure risk module; the reused dependency boundary is
  costs. No >7 AC or >3 integration-boundary threshold is established. Do not
  count each pure function as a separate external boundary. Folding broker,
  persistence or authentication implementation into this task would need a
  scope/split reassessment.
- R1 follow-up: architecture :208–209 currently omits risk from the
  backtest/research import allowlists, although the draft goal says they will
  use it. Before integrating, the R1 contract must decide how composition/imports
  satisfy the module map. This is not a reason to import timebase into risk or
  change the module map silently in CORE-003.

### Commands and review evidence

All times below are 2026-10-22 +07:00; intervals are approximate. Every check
used unchanged HEAD `79ac49b`. PASS here refers only to the named read/oracle
operation, not approval or implementation acceptance.

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean starting tree/index, expected task branch and revision. | 79ac49b | 07:03 |
| `rg` searches / `rg --version` | BLOCKED: `The term 'rg' is not recognized as the name of a cmdlet, function, script file, or operable program.` Used available PowerShell UTF-8 reads and Select-String without config changes. | 79ac49b | 07:04 |
| Numbered `Get-Content -Encoding UTF8` reads of draft, requested sources, costs implementation, template, CORE-002 contract reviews r1–r3, Handbook, skills and PROGRESS | PASS: source clauses and API compared; findings above. Initial default-encoding output was unreadable Thai and was reread explicitly as UTF-8. | 79ac49b | 07:03–07:08 |
| `git diff --stat main...HEAD`; `git show --stat --oneline HEAD`; `git diff 47151e8..HEAD -- PROGRESS.md` | PASS: distinguished inherited work from the draft/checkpoint commit. | 79ac49b | 07:04–07:08 |
| Read `pyproject.toml`, `.venv/pyvenv.cfg`, costs exports and CONTEXT definition | PASS: existing Python 3.12 environment and reused API inspected; no install/sync. | 79ac49b | 07:04–07:05 |
| `$env:PYTHONPATH='src'`; read-only stdin oracle via `uv run --offline --no-sync python -B -` | PASS exit 0: five sizing rows, daily/experiment thresholds, volume/stop comparisons, over-budget gate, cap and numerator-rounding counterexamples; Python 3.12.15. | 79ac49b | 07:06:00 |
| Same read-only stdin command, transition and predicate oracle | PASS exit 0: exact threshold neighbors, AC-02/03 latch sequences, twelve AC-04 rows and denominator-rounding counterexample. | 79ac49b | 07:07:40 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; two inherited pattern groups explained below. | 79ac49b | 07:05 |
| `git status --porcelain=v1 --untracked-files=all`; `git diff --cached --name-only`; `git rev-parse HEAD`; `Test-Path` for review and risk/code-test directories | PASS before writing: clean tree/index, unchanged HEAD; review target and risk implementation/acceptance/golden directories absent. | 79ac49b | 07:08 |
| `git status --porcelain=v1 --untracked-files=all`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD`; `git diff --check`; PowerShell report structure/whitespace check | PASS after writing: only the requested review is untracked; tracked/staged diffs empty; HEAD unchanged; ten finding rows, seven AC rows and all required sections present; no trailing whitespace. The untracked report was checked separately because git diff --check does not cover it. Risk unit-test directory also absent. | 79ac49b | 07:12:23 |
| Read-only Decimal-literal check via `uv run --offline --no-sync python -B -`, PYTHONPATH=src | PASS exit 0: both long exact Decimal literals in the F7 table reproduce at precision 100 with Inexact/Rounded trapped. | 79ac49b | 07:12:42 |

Red-flag hits: **Type checks disabled** found seven existing CORE-002 unit-test
suppression lines for intentional invalid-input/immutability tests, plus
documentary quotations in earlier reviews/evidence/compatibility. **Lint
disabled** matched documentary mentions in PROGRESS, CORE-002 evidence and its
test review. None is a new CORE-003 code suppression. Secret and order/account
mutation groups were empty; no deleted/renamed test files were reported. The
listed locked paths belong to inherited work and their approval/CI is not
re-certified. The scan ran before this report and does not scan untracked files.

## Not checked (and why)

- Risk implementation, pytest, acceptance/golden/architecture execution,
  mutation tests, runtime immutability or actual caller-context isolation:
  this review precedes that code. Independent formula probes do not establish
  implementation PASS. No tests were created or changed.
- Full re-review of CORE-002, inherited controls, their approvals, CI results,
  or merge readiness: outside this draft review. Costs code was read only for
  the API/domain/context assumptions on which CORE-003 depends.
- Authentication, journal recovery, send-time gate enforcement, idempotency,
  concurrent send reservation, terminal behavior and E1 integration: excluded
  from CORE-003 and unavailable here. Their handoff obligations are identified,
  not claimed implemented.
- Broker/account connections, credentials, holdout, market data, backtests,
  network calls, dependency installation, push, merge or deployment: neither
  needed nor performed. No external messages were sent.
- No separate `/review` tool is exposed in this headless session; the explicitly
  requested adversarial contract procedure was carried out directly.
- No edits to PROGRESS, contract, tests or handoff, and no staging or commit:
  the user permits only this report. Outstanding owner decisions remain open;
  no question was sent in this unattended run.

**Ready for test authoring: no** — resolve F1–F8 and F10, record the owner's F9
and transition-policy decisions, and obtain approval of the revised contract
before freezing acceptance/golden tables. The review is complete; CORE-003
remains a draft and has not reached implemented, verified, merged or deployed.
