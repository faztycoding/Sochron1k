# Review CORE-002 round 2 · base origin/main · head 493202c · reviewer Codex, fresh headless session 2026-10-22

Complete review of contract v1.2 and the fixed implementation, including the r1 F1–F3 re-check. This supersedes r1's incomplete AC/hash checkpoint; it does not replace the original finding record.

- Head: `493202cc3738dc066919146b23eab9eed01954f8`; base/merge-base: `b2eb69c07a553b30f293689edeaed55526c41c5d`; branch: `feat/CORE-002-costs`.
- Starting working tree/index: clean. Only this report is written, unstaged. No code, tests, PROGRESS, dependency, configuration, Git index or commit is changed.
- Inputs: contract, `git diff origin/main...HEAD`, prior finding/test-review records, and the explicitly requested implementation/findings-response handoff. The inherited CORE-001 post-merge chore is excluded as instructed. Two read-only helpers independently inspected static behavior and Decimal edge cases; the report author reproduced the finding and the numerical evidence.
- The headless tool interface does not expose the interactive `/review` slash command. Direct contract/diff inspection and the skill's remaining review procedure were performed. The owner's explicit one-report authorization supersedes the skill's write-confirmation step and AGENTS.md's default checkpoint/commit steps.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F4 | Low | confirmed | src/sochron/costs/charges.py:39 | The direct-construction probe below prints `True InvalidOperation True False` and `False CostsError True False`. The comparison of total with the ordered sum is outside `localcontext(CONTEXT)`. Contract Decimal-context rule, line 87, requires independence from and no mutation of caller context. | `CostBreakdown(D("1"), D("2"), D("3"), D("4"), D("sNaN"), D("1"))`, with caller InvalidOperation trap enabled or disabled. | Rejection changes the caller's InvalidOperation flag and its exception depends on the caller's traps. A caller catching the error retains contaminated arithmetic state. Normal factory outputs are unaffected. | Keep validation comparisons in the module context, or use a context-independent rejection guard before a signaling comparison. Do not execute this comparison in the caller context. | Regression invokes both caller trap settings, requires rejection in both, and verifies identical exception behavior plus unchanged context identity, settings, flags and traps. Existing valid/invalid-total and factory tests must stay green. No new broad finite-domain rule is demanded here. |

Findings open: 1

## F1–F3 verdicts

All pre-fix probes loaded `git show c2e6725:src/sochron/costs/{errors,model,charges}.py` directly into separate in-memory modules. No checkout, source replacement, temporary source file or Git write was used.

| ID | Original severity | Verdict | Diff and regression evidence | Independent confirmation |
|----|-------------------|---------|------------------------------|--------------------------|
| F1 | Medium | closed | `7562246`; charges.py:85–99 uses exact integer ratios for the volume grid. Unit `test_check_volume_grid_check_never_overflows_the_context` passes. | With step `1e-30`, pre-fix lots `1` and off-grid `1.0000000000000000000000000000001` both raise InvalidOperation/DivisionImpossible. HEAD returns the original valid Decimal object and rejects the off-grid value with BadVolume. Also checked `0.01` and caller context preservation with precision 4, ROUND_UP, Inexact/Rounded traps enabled. |
| F2 | Medium | closed (original cases) | `c97befb`; charges.py:33–40 validates six Decimal fields and the ordered total. Unit `test_cost_breakdown_rejects_wrong_types_and_totals` passes. | Pre-fix accepts all-int construction and Decimal components 1/2/3/4 with total 999. HEAD rejects them with TypeError and CostsError. Each of the six fields was independently replaced with an int and rejected. Total 10 is accepted; ordered p28 cancellation `1e28 + 1 + 1 - 1e28` correctly accepts total 0. The distinct surrounding-impact context defect is F4, not a recurrence of these original cases. |
| F3 | Low | closed | `f7b88f5`; model.py:116–117 validates Mapping before keys/items. Unit `test_provenance_must_be_a_mapping` passes. | Pre-fix list/set of the eleven keys raises AttributeError; string raises BadProvenance. HEAD list/set/string/None all raise TypeError. A valid UserDict is accepted and copied: clearing it leaves the model's eleven records intact. Caller context remains unchanged. |

## AC status

The repository suite is green. The FAIL below is an independently reproduced contract violation, not a failing result hidden from the suite.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Locked `test_ac01_spread_fallback_points_and_decimal_context` passes. Fraction oracle independently verifies spread 0.48, fallback 0.48, stress 0.96, point value 0.1, signed points, tie rounding and per-operation order. Caller traps/precision cannot affect these calls. |
| AC-02 | PASS | Locked `test_ac02_slippage_commission_sides_and_stress` passes. Slippage 0.20/0.40, commission zero and synthetic rate 3.5 producing 10.5/21.0 are independently verified. Sides 0/1/2/3 apply only to commission/slippage; default is 2. |
| AC-03 | PASS | Locked `test_ac03_swap_debits_credits_and_triple_counts` passes. Oracle verifies 1.00760/9.06840/0 and stress 2.01520/18.13680/0, positive swap credits -0.20/-0.40, zero nights/all-triple counts, and unsigned zero. |
| AC-04 | PASS | Locked `test_ac04_round_trip_selection_breakdown_order_and_r` passes. Long total 1.68760 and R 0.067504, sides-zero 1.48760, short exit-spread total 0.68, stressed total 3.37520. Both spread arguments are checked; selected None alone triggers fallback. Ordered-total cancellation is 0, not the exact-algebra value 2. F2 direct-construction cases now pass. |
| AC-05 | FAIL | All enumerated locked negative cases and the three implementer regressions pass. Expanded rejection-path review finds F4: a direct CostBreakdown total comparison mutates caller context and depends on its trap setting, violating the global Decimal rule on invalid input. The original type/domain/error cases remain correct. |
| AC-06 | PASS | Locked `test_ac06_h001_provenance_unknowns_frozen_and_stress_copy` passes. All H001 values/statuses/sources/dates checked against contract; exact eleven keys; both swap notes contain UNKNOWN; frozen instances and copied immutable provenance; stress makes a fresh model preserving base fields/provenance; nested default stress gives 4. |
| AC-07 | PASS | Locked costs AST test and existing CORE-001 tests pass. Full suite: exactly `44 passed in 0.10s`, 0 skipped. Four production source files have no float AST name/literal, external I/O, clock, random or MT5 path. Secret and order/account-mutation scan groups empty. The separate owner-controlled locked-path gate remains FAIL, as recorded below. |

## Checked, nothing found (and how)

### Arithmetic and caller context, apart from F4

An independent oracle uses `fractions.Fraction` and integer quotient/remainder with tie-to-even rounding after **each** written operation. It never uses Decimal arithmetic to calculate expected money. The full rerunnable script is in Appendix C.

- **124 golden monetary/factor values** independently matched their literal strings and HEAD outputs, including every AC fixture and the ordered-total fixture.
- **2,000 deterministic trade cases**, including H001, nonzero-commission, positive-swap-credit and the r2 synthetic model; volume grid within 0.01–200, sides 0–3, nights 0–21 with valid triple counts, missing/zero/unequal entry and exit spreads, and stress factors 1/2/4/a long decimal.
- **22,126 exact rational comparisons** and **14,126 calls** with caller identity/settings/flags/traps preserved. Caller precision was 4, ROUND_UP, Emin=-9, Emax=9, all traps enabled and a pre-existing Rounded flag set. Preservation was checked even when computing recurring R ratios and products requiring rounding.
- r2 model: points, point, contract_size and stress_factor are 12.345678, lots 1.23. HEAD and oracle agree on base `28573.59557212382385913406202` and stressed `57147.19114424764771826812405`. Doubling the already-rounded base gives `57147.19114424764771826812404`; general exact doubling is correctly not asserted under v1.2.
- `check_volume` returns the same Decimal object; exact grid decisions do not use a precision-limited remainder. No model mutation occurs through any ordinary exported operation. Initial provenance assignment in frozen construction uses a new mapping proxy.
- Import-time hostile caller-context probe also passed (read-only helper): precision 3, ROUND_FLOOR and Inexact/Rounded traps enabled before import; import plus worked example and 1/3 leave caller state unchanged.

### API, provenance and test quality

- Signatures/defaults and named error hierarchy match the API block. Decimal-only fields reject int/str/bool/float, integer fields reject bool/Decimal/str/float, and allowed int points/factors are converted exactly. Finite/domain checks precede arithmetic and zero returns. Multiple-invalid-input ordering is deliberately unspecified.
- CostModel numeric values: point 0.001, contract_size 100, volume min/step/max 0.01/0.01/200, fallback 240, commission 0, slippage 50, long/short swap -503.8/0, triple weekday 2; symbol XAUUSDm; initial stress factor 1.
- Provenance: point/contract/volume/fallback measured; commission/slippage/triple weekday assumed; both swap fields spec with historical UNKNOWN. All dates 2026-10-21, sources identify SPIKE-001 or H001 as prescribed. Exact unknowns tuple: `("commission_per_lot_per_side", "slippage_points_per_side", "triple_swap_weekday")`.
- Every source file was inspected together with the architecture extension: only stdlib and package-local imports, no dependency beyond the allowed core boundary; date is a fixed provenance date, not a clock call. No float AST name/literal, I/O, MT5, random or sending path.
- All **13 implementer unit tests** make real value/error/immutability assertions: context, division, signed zero, signed points, volume grid, provenance isolation, constructor validation, stress, unknowns and F1–F3. No mocks replace cost calculations. Their 1/3 and 2/3 division cases alone would not prove half-even ties; the locked point fixtures independently cover ties and operation order.
- Six locked acceptance tests exercise multiple fixture/error rows; they are not six trivial assertions. The full suite consists of the existing 24 tests plus 6 costs acceptance, 1 costs architecture and 13 costs unit tests.
- The handoff's “Please look hard at” points were checked: scalar/provenance error split, int stress versus bool rejection, unspecified error precedence for multiple defects, and additional exports. CONTEXT/PROVENANCE_FIELDS/STATUSES are additional API exports; no change to the contracted signatures was found.
- Evidence's original 41-test entries are historical implementation-run records; the appended findings-response evidence and this review establish the current 44-test result. No owner-run demo is inferred from agent execution.

### Locked-test reconciliation

At 06:21:16 +07, raw working bytes, HEAD blobs, and `dced669` blobs were **byte-identical** for all three paths. Computed SHA256 and raw Git blob SHA1 both match the handoff table. Files contain LF, no CR and no BOM. `git diff dced669 HEAD -- tests/acceptance tests/golden tests/architecture` is empty.

| Path | Bytes | SHA256 | Git blob |
|------|-------|--------|----------|
| tests/acceptance/CORE-002/test_costs_acceptance.py | 18,727 | 45120963f76a15386ccef7447f40a5cd9caec0aee72abbedba0b9ef2fe926925 | 8f55412347898e9835216cfb585ce490d5043a28 |
| tests/golden/CORE-002/costs_cases.py | 9,740 | 8a2ac03dc66244b4a8ea88bea5899a9d7a8a7a96cee6319cb7cde0cf935bdc9f | ac381085b5bf8561b4eba64f43f4175724575453 |
| tests/architecture/test_imports.py | 9,571 | 45e09f850f48e611acc317f2a7e2b5f6d79f856e64dfcc10e77ac5615acb158d | ff72f6b8b0a7c723356ffef6cde715005f8ac310 |

There is no locked-test deletion, skip, weakening or changed expected value after the red commit. The architecture extension preserves the original test/helper code and adds the costs check.

### Scope, failure-pattern checklist and red flags

The whole PR path inventory was reconciled with commit boundaries. Relative to the last inherited chore commit `5a8f536`, CORE-002 changes consist of source/unit tests, its contract/review records, authorized locked tests, evidence/handoff and PROGRESS. AGENTS.md, CLAUDE.md, SPEC/architecture updates, CORE-001/SPIKE-001 status documents and tooling compatibility changes originate in the excluded chore. No new CORE-002 edit to core/timebase, pyproject.toml, uv.lock, CI, hooks or controls was found.

Handbook §12 F01–F18 walkthrough:

| Patterns | Check and result |
|----------|------------------|
| F01/F17 false done or overstated state | Per-AC evidence and local-only delivery state; F4 remains open despite green tests. |
| F02 weakened tests | Three-way raw-byte/hash reconciliation plus assertion inspection; none. |
| F03 production fakes | H001 is the contracted model; synthetic models live in tests/probes; no mock/stub substitution. |
| F04/F05/F18 package/API/toolchain drift | No dependency/lock/config diff; Python 3.12.15 and installed stdlib API docs checked; offline existing environment. |
| F06/F07 scope/duplication | Whole path inventory and in-scope diff checked; costs is the newly contracted module; core/timebase unchanged. |
| F08 swallowed errors/fallbacks | No broad catch in production; only declared spread None fallback. F4 captures the actual error-path defect. |
| F09/F10 security shortcuts/secrets | No external connection or credential path; secret scan groups empty. |
| F11/F12 destructive commands/untrusted instructions | No destructive action, external instruction execution or market-data input. Review data treated as evidence. |
| F13/F14 retries/context loss | No unresolved repeated failing implementation attempt; complete report consolidates the interrupted r1 evidence with new checks. |
| F15/F16 unnecessary design/reviewer agreement | Small pure dataclasses/functions, no new abstraction/dependency; independent Fraction oracle and concrete F4. |

Concurrency/duplicate calls: operations have no external state/side effects, use local Decimal contexts and frozen values, and stress creates a new instance. There is no transaction, retry, resource handle, network or storage lifecycle to exercise here. Demo guards/journaling/reconciliation/risk gates are not applicable to this pure, non-order-sending change. No research/holdout/backtest run occurred.

Red-flag scan at 06:19:57–06:19:59 +07, exit 0:

- **Pattern groups with hits: 2.** “Type checks disabled”: seven deliberate unit-test negative/mutation annotations plus documentation quoting scan patterns. The annotations do not suppress runtime assertions or exceptions.
- “Lint disabled”: three documentation lines in PROGRESS/evidence/the prior tests review quote the pattern; no new production lint bypass.
- Secret, secret-like value, order/account mutation, destructive/bypass and placeholder/mock pattern groups: empty.
- Deleted/renamed tests: none. Untracked at scan time: none.
- Control paths listed: inherited AGENTS.md/CLAUDE.md and the three Codex-authored locked tests. The standalone locked-path gate reports **FAIL: 5 control change(s) need owner approval (PR label "owner-approved-control-change")**. This is not a passed gate and no label was applied.

### Checks run

All times are 2026-10-22 Asia/Bangkok (+07:00). Python probes were stdin-only with `PYTHONDONTWRITEBYTECODE=1`; pytest cache was disabled. Git Bash was invoked using `C:/Program Files/Git/bin/bash.exe` from the repository root. Source HEAD remained `493202c`.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| `git status --short`, branch/head/base and `git diff origin/main...HEAD` inspection | PASS: clean start; intended branch/head/base; in-scope diff inspected | 493202c | 06:18–06:22 |
| `uv run --offline pytest tests -q -p no:cacheprovider` | PASS, exit 0: **44 passed in 0.10s**, 0 skipped | 493202c | 06:19:57–06:19:58 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; two hit groups explained above; secret/order groups empty | 493202c | 06:19:57–06:19:59 |
| `uv run --offline --no-sync python -B -` (Appendix A equivalent pre/HEAD loader plus extended cases) | PASS re-check: F1/F2/F3 fail pre-fix and corrected cases pass HEAD; caller state preserved | c2e6725 / 493202c | 06:20:49 |
| `uv run --offline --no-sync python -B -` (raw Git blob/working bytes/SHA256/handoff comparison) and `git diff dced669 HEAD -- tests/acceptance tests/golden tests/architecture` | PASS: all three byte-identical, all six handoff hashes match; diff empty | dced669 / 493202c | 06:21:16 |
| `node scripts/controls/check-locked-paths.mjs origin/main` | FAIL, exit 1: five control paths require owner PR label | 493202c | 06:21:16 |
| `uv run --offline --no-sync python -B -` (Appendix C Fraction oracle) | PASS: 124 golden values, 2,000 cases, 22,126 comparisons, 14,126 context-preserving calls | 493202c | 06:22:02 |
| `uv run --offline --no-sync python -B -` (Appendix B F4 probe) | FAIL contract behavior; probe exits 0 while showing both caller-context mutations | 493202c | 06:22:33 |
| `git diff --check origin/main...HEAD` | PASS, exit 0, no output | 493202c | 06:22:58 |
| `git diff origin/main...HEAD -- pyproject.toml uv.lock src/sochron/core src/sochron/timebase .github .claude scripts/controls` | PASS, empty | 493202c | 06:22:58 |
| `rg` text search | BLOCKED: “The term 'rg' is not recognized”; used PowerShell Select-String/Get-Content for read-only inspection; no config change | 493202c | 06:20 |
| `uv run --offline --no-sync python -B -` (report structure/appendix syntax and final Git scope assertions), `git status --short` | PASS: seven AC rows, three Python appendices compile; HEAD unchanged; no tracked/staged changes; only `?? docs/reviews/CORE-002-r2.md` | 493202c | 06:25:43 |

## Not checked (and why)

- No CI run, PR labels, owner approval, merge or deployment; local evidence is L2. The owner's demo was not performed by the owner in this session.
- No broker terminal/account connection, order execution, market-data ingestion, backtest or holdout access: all outside this contract.
- No historical spread/swap validity inference; the model's assumed values and historical swap UNKNOWN remain explicit. Rollover-time counting, PnL, currency conversion and journal integration are excluded.
- No exhaustive arbitrary-exponent resource/performance test or hostile custom-subclass/object-reflection test. Ordinary contract domains, declared edge fixtures and finite sampled arithmetic were checked. Frozen dataclasses are evaluated under their normal API, not deliberate Python internals bypass.
- No re-review of the inherited CORE-001 chore, and no control-test-suite rerun: the user excluded that chore and CORE-002 changes no control implementation.
- No fix of F4 or proof against a future fixed commit; Appendix B defines the required regression. No locked test is edited.
- The interactive `/review` UI command was unavailable in this headless interface; this does not mean the direct diff review was skipped.

Delivery state: CORE-002 is **implemented** with green local tests and an open review finding; not fully verified against the contract, not merged or deployed by this review. Next action: implementer fixes F4 with a failing-before/passing-after unit regression, then requests a focused re-review; the owner/CI still control labels and merging. Only this unstaged report is the reviewer deliverable.

## Appendix A — rerunnable pre-fix / HEAD reproduction

Run the following through `uv run --offline --no-sync python -B -` from the repository root (stdin; no source writes). This compact version reproduces the original findings; the recorded run also checked every Breakdown field, UserDict isolation and caller-context snapshots.

```python
import subprocess, sys, types
from dataclasses import replace
from decimal import Decimal as D
sys.path.insert(0, "src")
import sochron.costs as head

package = types.ModuleType("pre_costs")
package.__path__ = []
sys.modules["pre_costs"] = package
for part in ("errors", "model", "charges"):
    name = "pre_costs." + part
    module = types.ModuleType(name)
    module.__package__ = "pre_costs"
    sys.modules[name] = module
    source = subprocess.check_output(
        ["git", "show", "c2e6725:src/sochron/costs/" + part + ".py"]
    )
    exec(compile(source, "<git:c2e6725/" + part + ".py>", "exec"), module.__dict__)
old = types.SimpleNamespace(**{
    **vars(sys.modules["pre_costs.model"]),
    **vars(sys.modules["pre_costs.charges"]),
})
for label, api in (("PRE", old), ("HEAD", head)):
    fine = replace(api.H001_COSTS, volume_step=D("1e-30"))
    probes = {
        "F1 valid": lambda: api.check_volume(D("1"), fine),
        "F1 off grid": lambda: api.check_volume(
            D("1.0000000000000000000000000000001"), fine),
        "F2 ints": lambda: api.CostBreakdown(1, 2, 3, 4, 10, 1),
        "F2 total": lambda: api.CostBreakdown(
            *map(D, ("1", "2", "3", "4", "999", "1"))),
        "F3 list": lambda: replace(
            api.H001_COSTS, provenance=list(api.PROVENANCE_FIELDS)),
    }
    for name, call in probes.items():
        try:
            print(label, name, "RETURN", call())
        except Exception as error:
            print(label, name, type(error).__name__, str(error))
```

## Appendix B — F4 reproduction and expected regression

Run via the same stdin command. The two output rows currently show a changed caller flag and different exception classes. A fixed implementation must reject consistently without altering caller state.

```python
import sys
from decimal import Decimal as D, InvalidOperation, localcontext
sys.path.insert(0, "src")
from sochron.costs import CostBreakdown

for trap in (True, False):
    with localcontext() as caller:
        caller.clear_flags()
        caller.traps[InvalidOperation] = trap
        before = repr(caller)
        try:
            CostBreakdown(D("1"), D("2"), D("3"), D("4"), D("sNaN"), D("1"))
        except Exception as error:
            print(trap, type(error).__name__,
                  caller.flags[InvalidOperation], repr(caller) == before)
```

Observed:

```text
True InvalidOperation True False
False CostsError True False
```

## Appendix C — exact arithmetic oracle

Run via `uv run --offline --no-sync python -B -` with this script on stdin. It reads the locked fixture table but computes every expected result independently with rational/integer arithmetic and checks the literal golden values as well as production outputs.

```python
import sys
from fractions import Fraction as F
from dataclasses import replace
from datetime import datetime, date
from decimal import Decimal as D, localcontext, getcontext, ROUND_UP, Rounded
from runpy import run_path
sys.path.insert(0, "src")
import sochron.costs as c

# Exact rational rounding to 28 significant decimal digits. No Decimal arithmetic.
def power10(e):
    return F(10**e) if e >= 0 else F(1, 10**(-e))
def q28(x):
    x = F(x)
    if not x:
        return x
    sign = -1 if x < 0 else 1
    x = abs(x)
    e = len(str(x.numerator)) - len(str(x.denominator))
    if x < power10(e):
        e -= 1
    unit = power10(e - 27)
    scaled = x / unit
    n, rem = divmod(scaled.numerator, scaled.denominator)
    if rem * 2 > scaled.denominator or (rem * 2 == scaled.denominator and n % 2):
        n += 1
    return sign * n * unit
def mul(*values):
    result = F(values[0])
    for v in values[1:]:
        result = q28(result * F(v))
    return result
def add(*values):
    result = F(values[0])
    for v in values[1:]:
        result = q28(result + F(v))
    return result
def pm(p, lots, model):
    return mul(p, model.point, model.contract_size, lots, model.stress_factor)
def components(side, lots, entry, exit_, nights, triple, model, sides):
    selected = entry if side == "long" else exit_
    spread = pm(model.spread_fallback_points if selected is None else selected, lots, model)
    commission = mul(model.commission_per_lot_per_side, lots, sides, model.stress_factor)
    slip = mul(pm(model.slippage_points_per_side, lots, model), sides)
    rate = model.swap_long_points_per_night if side == "long" else model.swap_short_points_per_night
    swap = add(0, -mul(pm(rate, lots, model), nights - triple + 3*triple))
    return spread, commission, slip, swap, add(spread, commission, slip, swap), F(model.stress_factor)
def snapshot():
    ctx = getcontext()
    return (id(ctx), ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals, ctx.clamp, dict(ctx.flags), dict(ctx.traps))
calls = matches = 0
def invoke(fn, *args, **kw):
    global calls
    before = snapshot()
    try:
        return fn(*args, **kw)
    finally:
        assert snapshot() == before, fn.__name__
        calls += 1
def same(actual, exact, expected=None):
    global matches
    assert isinstance(actual, D)
    assert F(actual) == exact, (actual, exact)
    if expected is not None:
        assert exact == F(expected), (exact, expected)
    matches += 1
def fixture(**kw):
    return replace(c.H001_COSTS, **kw, provenance={**c.H001_COSTS.provenance,
        **{key: c.Provenance("review synthetic", date(2026,10,21), "assumed")
           for key in kw if key != "stress_factor"}})
print("TIME", datetime.now().astimezone().isoformat())
g = run_path("tests/golden/CORE-002/costs_cases.py")
commissioned = fixture(commission_per_lot_per_side=D("3.5"))
credit = fixture(swap_long_points_per_night=D("100"))
r2 = fixture(point=D("12.345678"), contract_size=D("12.345678"), stress_factor=D("12.345678"))
with localcontext(prec=4, rounding=ROUND_UP, Emin=-9, Emax=9) as caller:
    for signal in caller.traps:
        caller.traps[signal] = True
    caller.flags[Rounded] = True
    for p,l,f,e in g["SPREAD_ROWS"]:
        m = invoke(c.stress, c.H001_COSTS, D(f))
        same(invoke(c.spread_charge,p,D(l),m),pm(240 if p is None else p,D(l),m),e)
    for p,l,f,e in g["POINT_ROWS"]:
        m = invoke(c.stress,c.H001_COSTS,D(f))
        same(invoke(c.points_to_money,D(p),D(l),m),pm(D(p),D(l),m),e)
    for l,s,f,e in g["SLIPPAGE_ROWS"]:
        m = invoke(c.stress,c.H001_COSTS,D(f))
        same(invoke(c.slippage_charge,D(l),m,s),mul(pm(50,D(l),m),s),e)
    for rate,l,s,f,e in g["COMMISSION_ROWS"]:
        m = invoke(c.stress,fixture(commission_per_lot_per_side=D(rate)),D(f))
        same(invoke(c.commission_charge,D(l),m,s),mul(D(rate),D(l),s,m.stress_factor),e)
    for label,side,l,n,t,f,e in g["SWAP_ROWS"]:
        m = invoke(c.stress,c.H001_COSTS if label == "h001" else credit,D(f))
        rate = m.swap_long_points_per_night if side == "long" else m.swap_short_points_per_night
        actual = invoke(c.swap_charge,side,D(l),n,t,m)
        same(actual,add(0,-mul(pm(rate,D(l),m),n-t+3*t)),e)
        if not actual:
            assert not actual.is_signed()
    for side,l,entry,exit_,n,t,s,f,expected in g["ROUND_TRIP_ROWS"]:
        m = invoke(c.stress,c.H001_COSTS,D(f))
        actual = invoke(c.round_trip_cost,side,D(l),entry,exit_,n,t,m,s)
        for name,exact,e in zip(("spread","commission","slippage","swap","total","stress_factor"),
                               components(side,D(l),entry,exit_,n,t,m,s),expected):
            same(getattr(actual,name),exact,e)
    for money,r,e in g["R_ROWS"]:
        same(invoke(c.r_multiple,D(money),D(r)),q28(F(money)/F(r)),e)
    row = g["ORDERED_TOTAL"]
    m = fixture(commission_per_lot_per_side=D(row["commission"]),slippage_points_per_side=row["slippage"],swap_long_points_per_night=D(row["swap_points"]))
    actual = invoke(c.round_trip_cost,"long",D("1"),row["entry"],0,1,0,m,1)
    for name,exact,e in zip(("spread","commission","slippage","swap","total","stress_factor"),
                           components("long",D("1"),row["entry"],0,1,0,m,1),row["expected"]):
        same(getattr(actual,name),exact,e)
    print("GOLDEN PASS", matches, "literal monetary/factor comparisons")
    base = invoke(c.points_to_money,D("12.345678"),D("1.23"),r2)
    stressed = invoke(c.points_to_money,D("12.345678"),D("1.23"),invoke(c.stress,r2))
    same(base,pm(D("12.345678"),D("1.23"),r2))
    same(stressed,pm(D("12.345678"),D("1.23"),invoke(c.stress,r2)))
    print("r2 base",base,"stressed",stressed,"double-rounded-base fraction",q28(F(base)*2))
    models = [c.H001_COSTS, commissioned, credit, r2]
    factors = [D("1"),D("2"),D("4"),D("1.2345678901234567890123456789")]
    for i in range(2000):
        m = invoke(c.stress,models[i%4],factors[(i//4)%4])
        hundredths = 1 + (i*137)%20000
        lots = D(str(hundredths//100)+"."+str(hundredths%100).zfill(2))
        side = "long" if (i//16)%2 == 0 else "short"
        entry = [None,0,37,100,240,800][(i//32)%6]
        exit_ = [None,0,65,420,270,1200][(i//7)%6]
        n = i%22
        t = (i//3)%(n+1)
        s = (i//11)%4
        expected = components(side,lots,entry,exit_,n,t,m,s)
        actual = invoke(c.round_trip_cost,side,lots,entry,exit_,n,t,m,s)
        for name,exact in zip(("spread","commission","slippage","swap","total","stress_factor"),expected):
            same(getattr(actual,name),exact)
        same(invoke(c.spread_charge,entry if side=="long" else exit_,lots,m),expected[0])
        same(invoke(c.commission_charge,lots,m,s),expected[1])
        same(invoke(c.slippage_charge,lots,m,s),expected[2])
        same(invoke(c.swap_charge,side,lots,n,t,m),expected[3])
        same(invoke(c.r_multiple,actual.total,D("25")),q28(expected[4]/25))
        if actual.swap == 0:
            assert not actual.swap.is_signed()
        assert c.H001_COSTS.stress_factor == D("1")
    print("MATRIX PASS 2000 deterministic trades; models H001/commission3.5/credit100/r2; lots0.01..200, sides0..3, nights0..21, variable triples, missing/zero/unequal spreads; 4 stress factors")
print("PASS",matches,"rational comparisons;",calls,"calls with exact caller-context preservation including traps/flags")
print("END",datetime.now().astimezone().isoformat())
```
