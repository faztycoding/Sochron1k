# Review CORE-003 contract round 3 · base d79b3f5 · head 01a74f5 · reviewer Codex, fresh headless session

Reviewed on 2026-10-22, Asia/Bangkok (+07:00). Object:
`docs/contracts/CORE-003-risk.md` v1.2, Tier High, on
`feat/CORE-003-risk`. Full HEAD:
`01a74f5e098c818faccf96f9d304f3e40cbd3f26`.
Revision: `git diff d79b3f5..HEAD -- docs/contracts/CORE-003-risk.md`.
All contract line references below refer to this HEAD.

**Ready for test authoring: yes**

F6, F11 and F12 are closed at contract level. No new defect was found in
v1.2, so no F13 is opened. No previously closed finding was reopened.
Owner choice (ช) is now explicitly disclosed as pending approval.

**Could two test authors now write identical golden rows for every AC
without asking a question? Yes, for the specified inputs and expected
outcomes.** The display-range rule, no-grid fixture and entry-gate predicates
now determine the formerly divergent rows. Unchanged ACs retain their r2
authoring-readiness conclusions. Multi-invalid exception priority remains
deliberately unspecified at contract :115; tests isolate each invalid input.
This does not require identical test organization or arbitrarily chosen
additional fixtures.

This technical verdict does not approve the plan, acceptance criteria or
business policies. The draft/authorization requirements at contract :4,
:201 and :203-205 remain in force; owner approval is still separately required.

Scope: `adversarial-design-review`, using the re-review/findings format of
`cross-agent-review`, limited to F6/F11/F12 and the surrounding impact of
v1.2. One independent read-only helper checked the amended clauses; this
session verified the evidence and executed the arithmetic probes. The
explicit task permits only this unstaged report, which also serves as the
handoff. No PROGRESS update, tests, commit, staging or external write is
authorized by this review.

## Verdict table

“Closed” means the specification defect is resolved, not that risk code has
passed an implementation test.

| ID | Verdict | Evidence at current file:line |
|----|---------|-------------------------------|
| F6 | closed | `docs/contracts/CORE-003-risk.md:42`, `:132`: both range clauses now specify Overflow/Underflow traps and RiskError translation, accept exact subnormals, reject inexact subnormal rounding including nonzero-to-zero, and preserve caller context. Exact R1E-1000000 is accepted; R1E-1000027 is rejected. The independent Context probes below confirm these numerical boundaries. |
| F11 | closed | `docs/contracts/CORE-003-risk.md:97`, `:98`, `:99`, `:100`, `:168`: both halt predicates use current equity OR their existing latches, with exact inclusive comparisons. Caller rollover/update and persistence before every gate call are explicit. Baselines10000/equity9800 now return both halt reasons while sizing still allows .02; isolated baseline/equity100 returns only the two sizing reasons. Baseline/equity10000 still allows. |
| F12 | closed | `docs/contracts/CORE-003-risk.md:165` resets every AC-01 fixture, supplies equity10000/stop1/cost0 and the model overrides for the no-grid case, and states all five SizeDecision fields. The duplicate negative example at `:156` also fixes stop1 and risk_per_lot100. The exact oracle reproduces the complete row below. |

## Findings

No open findings in this round. No new ID assigned.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|

## Owner choice disclosure

Choice **(ช)** at `docs/contracts/CORE-003-risk.md:201` now explicitly says
that the experiment halt survives recovery and new days, that only an
authorized restart with a reason clears it, and that restart rebases
`experiment_start_equity` to the equity supplied at restart. It also states
the daily latch survives same-day recovery. This agrees with the transition
rules at :80-89 and the unchanged AC-03 at :167.

The new budget examples are exact: `9800 * .02 = 196`, and
`10500 * .02 = 210`. They are disclosed choices awaiting owner acceptance,
not implicitly approved by their inclusion in golden tests. No further
undisclosed business choice was found in the v1.2 delta.

## AC status

Implementation acceptance is UNKNOWN for every AC: this task reviews a
contract. Authoring readiness is a separate specification judgment.

| AC | Status (PASS/FAIL/UNKNOWN) | Authoring readiness | Why |
|----|----------------------------|---------------------|-----|
| AC-01 | UNKNOWN | PASS | F6/F12 resolved; exact no-grid row and fixture independence verified below. Other numerical rows are unchanged from r2. |
| AC-02 | UNKNOWN | PASS | Unchanged exact daily/rollover rules; checked their interaction with the revised gate. |
| AC-03 | UNKNOWN | PASS | Unchanged restart/latch rules; choice (ช) now expressly discloses the budget reset. |
| AC-04 | UNKNOWN | PASS | F11 resolved; both changed rows and the base allow case recomputed, with sorted complete reasons. |
| AC-05 | UNKNOWN | PASS | Unchanged stop-change contract; no v1.2 impact found. R2 conclusion retained. |
| AC-06 | UNKNOWN | PASS | F6 now selects a unique range/error oracle; ordinary validation/immutability requirements unchanged. |
| AC-07 | UNKNOWN | PASS | Unchanged testable purity/import/scan/suite requirements. Risk implementation and its suite were not tested. |

## Checked, nothing found (and how)

### Exact rational recomputation

Executed stdin-only `uv run --offline --no-sync python -B -` using verified
CPython 3.12.15 and stdlib `fractions.Fraction`. The oracle imports no risk
implementation, uses no binary floats and does not round decision inputs.
H001 model constants were checked against
`docs/contracts/CORE-002-costs.md:111` and `:112`; the display Context
definition is `src/sochron/costs/model.py:21`.

All operands used in the required sizing rows are listed here. Money is USD;
distance is USD/oz, contract size is oz/lot, and volume is lots. Unchanged
CostModel fields are inherited from H001_COSTS and do not enter this sizing
formula. H001_RISK supplies rate .0025, daily limit .0075, experiment limit
.02 and maximum exposures1. Sizing explicitly ignores model stress_factor.

| Row | Equity | Stop distance | Contract size | Risk rate | Cost/lot | Volume min | Step | Volume max |
|-----|--------|---------------|---------------|-----------|----------|------------|------|------------|
| AC-01 no-grid | 10000 | 1.00 | 100 | .0025 | 0 | .026 | .01 | .029 |
| AC-04 isolated below-minimum | 100 | 12.00 | 100 | .0025 | 0 | .01 | .01 | 200 |
| AC-04 equity9800 threshold | 9800 | 12.00 | 100 | .0025 | 0 | .01 | .01 | 200 |
| AC-04 base allow | 10000 | 12.00 | 100 | .0025 | 0 | .01 | .01 | 200 |

The no-grid model is a fresh copy of H001_COSTS changing only volume_min and
volume_max, with each changed field's provenance
`Provenance("synthetic test fixture", date(2026, 10, 22), "assumed")`, as :165
requires. No prior example's stop or cost is inherited.

| Row | Exact R | Exact risk/lot | Raw lots | Uncapped grid lots | Max on grid | Final lots | Actual risk | Reason |
|-----|---------|----------------|----------|--------------------|-------------|------------|-------------|--------|
| No-grid | 25 | 100 | 1/4 | .25 | .02 | 0 | 0 | below_min_volume |
| Isolated100 | 1/4 | 1200 | 1/4800 | 0 | 200 | 0 | 0 | below_min_volume |
| Threshold9800 | 49/2 | 1200 | 49/2400 | .02 | 200 | .02 | 24 | ok |
| Base10000 | 25 | 1200 | 1/48 | .02 | 200 | .02 | 24 | ok |

All display fields in these four rows equal the exact values numerically
after precision28 rounding. Thus the full no-grid golden SizeDecision is
`(Decimal("0"), Decimal("25"), Decimal("100"), Decimal("0"), "below_min_volume")`.
In particular, `floor(.029/.01)*.01 = .02 < .026`; below-min takes precedence
over the cap reason. Every row satisfies the exact risk/grid checks.

Reproducible sizing core and equivalent full-row assertions (also executed
from this report during validation):

```python
from fractions import Fraction as F

def size(equity, distance, cost="0", minimum=".01", maximum="200",
         step=".01", contract="100", rate=".0025"):
    e, d, c, lo, hi, st, cs, p = map(
        F, (equity, distance, cost, minimum, maximum, step, contract, rate))
    r, per = e * p, d * cs + c
    raw = r / per
    uncapped, cap = (raw // st) * st, (hi // st) * st
    lots = min(uncapped, cap)
    reason = "capped_at_volume_max" if uncapped > cap else "ok"
    if lots < lo:
        lots, reason = F(0), "below_min_volume"
    assert lots % st == 0 and lots * per <= r
    return lots, r, per, lots * per, reason, raw, uncapped, cap

assert size("10000", "1.00", minimum=".026", maximum=".029") == (
    0, 25, 100, 0, "below_min_volume", F("1/4"), F("1/4"), F("1/50"))
assert size("100", "12.00") == (
    0, F("1/4"), 1200, 0, "below_min_volume", F("1/4800"), 0, 200)
assert size("9800", "12.00") == (
    F("1/50"), F("49/2"), 1200, 24, "ok", F("49/2400"), F("1/50"), 200)
assert size("10000", "12.00") == (
    F("1/50"), 25, 1200, 24, "ok", F("1/48"), F("1/50"), 200)
```

### Entry gate and surrounding impact

All three required gate rows use day2026-10-22, H001_RISK, H001_COSTS,
cost_per_lot0, long, entry4012.90, SL4000.90 and exposures0. Therefore the
exact stop distance is12. Both input flags are false. The isolated row starts
with `start_experiment(Decimal("100"), date(2026, 10, 22), H001_RISK,
"owner", "isolated sizing fixture")`; the other rows start from AC-02's
initial10000 state. Only the isolated row requests .01 lots; the others
request .02.

| Row | Daily / experiment baselines | Current equity | Loss from each baseline | Daily threshold | Experiment threshold | Allowed | Complete reasons |
|-----|------------------------------|----------------|-------------------------|-----------------|----------------------|---------|------------------|
| Isolated below-minimum | 100 / 100 | 100 | 0 / 0 | .75 | 2 | false | ("below_min_volume", "lots_exceed_sized") |
| Equity9800 threshold | 10000 / 10000 | 9800 | 200 / 200 | 75 | 200 | false | ("daily_halt", "experiment_halt") |
| Base allow | 10000 / 10000 | 10000 | 0 / 0 | 75 | 200 | true | () |

For isolated100, requested.01 is a valid grid volume but exceeds sized0;
neither baseline has a loss. For threshold9800, requested.02 equals sized.02,
so sizing contributes no reason; loss200 meets both exact halt inequalities.
For base10000, the same request has risk24 <= budget25 and no denial predicate.

The changed predicates also passed six surrounding oracle cases: same-day
9925 gives daily_halt at loss75; 9925.01 gives no halt; previously latched
daily/experiment flags remain reasons at recovered equity10000; rolled
daily baseline9900 with experiment baseline10000 permits equity9900;
rolled daily baseline9800 still gives experiment_halt at equity9800; and
baseline10000/equity100 with both flags, lots.015 and exposures1 yields all
six sorted reasons:
`("below_min_volume", "daily_halt", "experiment_halt", "lots_exceed_sized",
"lots_not_on_grid", "max_exposure")`.

Contract :100 requires callers to update/roll over and retain the returned
state before every gate call. The stale-clear9800 fixture deliberately checks
the extra protection at :99; it does not waive that caller obligation. The
gate remains pure and cannot itself persist a latch. No contradiction with
AC-02/03's rollover/latching behavior was found.

### F6 display boundary

Using a separate `Context(prec=28, rounding=ROUND_HALF_EVEN)` matching the
referenced definition, the probe enabled Overflow and Underflow traps in
`localcontext`. It observed Emin=-999999, Emax=999999, Etiny=-1000026:

| Exact display value | Probe result | Required contract outcome |
|---------------------|--------------|---------------------------|
| 1E-1000000 | Exact result; Subnormal only | Accept |
| 1E-1000026 | Exact result at Etiny; Subnormal only | Accept |
| 1E-1000027 | Underflow | RiskError |
| 1.1E-1000026 | Underflow from inexact subnormal rounding | RiskError |
| 1E1000000 | Overflow | RiskError |

Fraction assertions also proved the complete R operands:
`4E-999998 * .0025 = 1E-1000000` and
`4E-1000025 * .0025 = 1E-1000027`.
The probe's caller context and source Context settings/traps/flags remained
unchanged. These are checks of the specified numerical rule; actual
translation to RiskError in risk code is not yet tested. Ordinary inexact
normal rounding remains allowed under :41, so the existing precision-edge
rows do not acquire a new exception.

### Scope and red flags

- Compared only F6/F11/F12 and amended surrounding clauses against r2.
  No v1.2 change to rates, dependencies, cost selection, restart privileges,
  stop-change predicates or the previously closed findings was found.
- Red-flag scan against main completed with two inherited hit groups:
  type-check suppression comments in CORE-002 negative unit tests and
  documentation quoting them; lint-keyword mentions in existing documents.
  No secret or order/account-mutation group hit, and no deleted/renamed tests.
  Listed locked-path changes belong to the inherited branch delta, not this
  report. The scan does not inspect untracked content; this report is reviewed
  separately and is intentionally left unstaged.
- No test or implementation file was written. The report is the only session
  artifact; no approval is inferred from the headless invocation.

## Checks run

All timestamps are 2026-10-22 Asia/Bangkok (+07:00), and all checks refer to
HEAD `01a74f5e098c818faccf96f9d304f3e40cbd3f26`.

| Command / check | Result | Commit | Time |
|-----------------|--------|--------|------|
| `git diff d79b3f5..HEAD -- docs/contracts/CORE-003-risk.md`; numbered UTF-8 reads of the contract/r2/template and referenced constants | PASS: requested delta and closure evidence inspected | 01a74f5 | 07:38-07:40 |
| `rg -n ... SPEC.md docs/HANDBOOK-CORE.md docs/architecture.md` | BLOCKED: PowerShell reports "The term 'rg' is not recognized as the name of a cmdlet"; used Get-Content/Select-String, with no configuration change | 01a74f5 | 07:38; exact second not captured |
| `uv run --offline --no-sync python -B --version` | PASS: Python3.12.15 | 01a74f5 | 07:39:23 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit0; two inherited groups explained above | 01a74f5 | 07:39:23 |
| `uv run --offline --no-sync python -B -` with the stdin Fraction/Decimal oracle | PASS: four full sizing rows, nine gate cases, both restart budgets, five display boundaries, two exact exponent identities and context preservation | 01a74f5 | 07:40:10-07:40:11 |
| `git status --short`; `git diff --cached --name-only`; `git rev-parse HEAD`; `git diff --check d79b3f5..HEAD -- docs/contracts/CORE-003-risk.md` | PASS: clean tree/index before report, unchanged HEAD, no contract whitespace error | 01a74f5 | 07:40:40 |
| `uv run --offline --no-sync python -B -` with the read-only report validator | PASS, exit0: UTF-8, required sections/verdicts, trailing whitespace/EOF, and all four embedded oracle assertions | 01a74f5 | 07:42:22 |
| `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD`; `git diff --check` | PASS, exit0: only this report untracked; tracked worktree/index unchanged; HEAD unchanged | 01a74f5 | 07:42:22 |

## Not checked (and why)

- Risk implementation, runtime errors/immutability, executable acceptance,
  golden or AST tests, full pytest, CI and owner demo: outside this contract
  review. Their acceptance remains UNKNOWN, not tested-and-failed.
- Full security/leakage/mutation reviews, performance bounds, unrelated
  historical findings and prior module/control implementations: outside the
  requested recheck. The existing costs constants/Context were read only to
  anchor the independent oracle.
- R1/E1 integration, authentication, journal persistence, midnight valuations,
  broker/account actions and send binding: future contracts. No credential
  store, terminal, market data, holdout, network or external service accessed.
- Owner approval of the plan/acceptance and choices (ก)-(ช): not supplied and
  not this verdict. No question was asked in this unattended run.
- No PROGRESS or other-file update, stage, commit, push, merge or deployment.
  The explicit single-file authorization overrides generic checkpoint steps.

Next action: the owner approves the plan/acceptance and disclosed choices;
then the authorized test author writes acceptance/golden tests. Delivery
state: review report implemented with its numerical evidence verified;
CORE-003 functionality is not claimed verified, merged or deployed.
