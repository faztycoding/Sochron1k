# Review CORE-003 round 1 · base origin/main · head 60dfbfd · reviewer Codex, fresh headless review session

Reviewed HEAD `60dfbfdb7a857210957d395b4f3c27648f784a1d` against owner-approved contract v1.3 and `git diff origin/main...HEAD`. The local `origin/main` is `3456e7d16430443df0ed26cd7f87b71f31f95914`; the diff merge-base is `47151e87a0f0fafe440a5a74d1db0f353edb00f0`. No fetch was performed. Review date: 2026-10-22, Asia/Bangkok (+07).

**Three confirmed findings remain: two Medium and one Low.** The required suite passes, but independent probes demonstrate a model-domain validation bypass, a valid-zero display failure, and incorrect exceptions for large negative counts. This is implementation review evidence, not approval to merge or operate an account.

Applied `cross-agent-review` and the High-tier security-review procedure. Read-only delegates independently examined arithmetic, security regressions and test integrity. First findings were recorded before reading the implementation handoff sections and their “Please look hard at” lists. This session writes only this report, unstaged; it does not change code, tests, PROGRESS or Git metadata.

## Findings

IDs in this table are this implementation review's IDs. The separate security pre-review F1–F8 verdicts appear below.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `src/sochron/risk/sizing.py:66`–`:70`, used by `gate.py:135` | Probe R1 below: changing a copied model's `volume_step` to `Decimal('-0.01')` makes `check_entry` allow 1 lot with exact risk USD 1,200 against budget USD 25. `size_position` returns 200 lots and actual risk USD 240,000 with reason `capped_at_volume_max`. Honest-model sizing is 0.02 lots. | An exact `CostModel` whose consumed field was corrupted after construction; finite/type/size checks pass despite the invalid domain. | The gate returns `allowed=True` above the risk budget. The sizing invariant `actual_risk <= risk_money` is violated. This is a boundary-validation defect within risk, not a request to implement E1's broker/model binding. | In `require_model`, validate positive `contract_size`, `volume_min`, `volume_step`, `volume_max` and `volume_max >= volume_min` before rational conversion or selecting a gate branch. Raise `RiskError` for malformed consumed fields. | Add implementer regression tests using fresh copied models with zero/negative consumed fields and reversed min/max; both sizing and gate must raise `RiskError`, including gate calls already subject to another refusal. Preserve all valid synthetic grids and the exact oracle results. |
| F2 | Medium | confirmed | `src/sochron/risk/sizing.py:127`; `src/sochron/risk/policy.py:119`–`:124` | Probe R2: ordinary H001 sizing with `cost_per_lot=Decimal('0E-999999999999999999')` raises `MemoryError`; root replay completed in about 0.000098 s inside a bounded child process. | A valid zero budget with an extreme negative exponent. It has one coefficient digit, is finite, and v1.3 explicitly exempts zero from the adjusted-exponent bound. | The exact display intermediate attempts an enormous coefficient allocation when adding zero to 1200. A supported value fails outside the documented error behavior; other representations on this path can consume substantial memory. This finding does **not** impose the oversized-input deadline on accepted inputs. | Canonicalize exact zero before exact Decimal arithmetic, or avoid adding zero terms while preserving exact nonzero arithmetic. Do not reject zero or introduce a new domain bound to fix this implementation issue. | In a bounded process, compare H001 sizing for `0`, `-0` and zero values with extreme positive/negative exponents; all must equal the normal zero-budget result without a large intermediate. Retain Overflow/Underflow and single-rounding tests. |
| F3 | Low | confirmed | `src/sochron/risk/gate.py:87`; `src/sochron/risk/policy.py:170` | Probe R3: `open_exposures=-(10**5000)` and `max_open_exposures=-(10**5000)` each raise plain `ValueError: Exceeds the limit (4300 digits) for integer string conversion`, not the contract's `RiskError` / `BadPolicy`. | A correctly typed negative `int` whose decimal representation exceeds Python's configured conversion limit. The contract places the 1,000-digit bound on Decimal inputs, not ints. | The intended domain error is replaced while constructing its message. Callers handling the risk error hierarchy do not catch this failure. The same problem is reachable when a mutated request/policy is revalidated. | Do not interpolate an unbounded integer into these errors; use bounded or value-free diagnostics. Do not change Python's conversion limit or add an unapproved int domain bound. | Constructor and use-time tests with large negative counts must raise `RiskError` for exposures and `BadPolicy` for the policy count. Normal negative counts must retain their existing errors. |

### Reproductions R1–R3

Run from the repository root in PowerShell. This script uses only in-memory copies and a bounded Python child; it writes no files. The printed failures below were observed on HEAD with CPython 3.12.15, default int-string limit 4,300.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import subprocess
import sys
sys.path.insert(0, "src")
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from fractions import Fraction as F
from sochron.costs import H001_COSTS as M
from sochron.risk import (
    H001_RISK as P, EntryRequest, RiskError, check_entry,
    size_position, start_experiment,
)

day = date(2026, 10, 22)
state = start_experiment(D("10000"), day, P, "owner", "review")
request = EntryRequest("long", D("1"), D("4012.90"), D("4000.90"), 0)
model = replace(M)
object.__setattr__(model, "volume_step", D("-0.01"))
print("R1 honest sizing:", size_position(D("10000"), D("12"), M, P))
print("R1 corrupted gate:", check_entry(request, D("10000"), day, state, model))
print("R1 corrupted sizing:", size_position(D("10000"), D("12"), model, P))
print("R1 exact request risk/budget:",
      F(request.lots) * (F(request.entry_price) - F(request.stop_loss)) * F(model.contract_size),
      F(P.risk_per_trade) * 10000)

child = '''import sys, time
sys.path.insert(0, "src")
from decimal import Decimal as D
from sochron.costs import H001_COSTS
from sochron.risk import H001_RISK, size_position
zero = D("0E-999999999999999999")
started = time.perf_counter()
try:
    print(size_position(D("10000"), D("12"), H001_COSTS, H001_RISK, zero))
except Exception as error:
    print(type(error).__name__, "after", time.perf_counter() - started)
'''
result = subprocess.run([sys.executable, "-B", "-c", child],
                        capture_output=True, text=True, timeout=10)
print("R2 child exit:", result.returncode, result.stdout.strip(), result.stderr.strip())

for name, call in (
    ("open_exposures", lambda: EntryRequest("long", D(".02"), D("4012.90"), D("4000.90"), -(10**5000))),
    ("max_open_exposures", lambda: replace(P, max_open_exposures=-(10**5000))),
):
    try:
        call()
    except Exception as error:
        print("R3", name, type(error).__name__, "is RiskError:", isinstance(error, RiskError), str(error))
'@ | uv run --offline python -B -
```

Observed salient output:

```text
R1 honest sizing: lots=0.02, risk_money=25, risk_per_lot=1200, actual_risk=24, reason=ok
R1 corrupted gate: GateDecision(allowed=True, reasons=())
R1 corrupted sizing: lots=200.00, risk_money=25, risk_per_lot=1200, actual_risk=240000.00, reason=capped_at_volume_max
R1 exact request risk/budget: 1200 25
R2 child exit: 0 MemoryError after 9.809999937715475e-05
R3 open_exposures ValueError is RiskError: False Exceeds the limit (4300 digits) ...
R3 max_open_exposures ValueError is RiskError: False Exceeds the limit (4300 digits) ...
```

The child exits zero because the diagnostic catches and prints the exception; that exit is not a passing sizing result. R1 was independently reproduced by two reviewers. A zero or negative `contract_size` combined with a positive budget was also accepted by the gate, supporting the same missing-domain-check finding.

## Security pre-review F1–F8 verdicts

“Closed” here refers to the specified original defect or approved contract disposition, not a claim that all related threat surfaces are closed.

| Pre-review ID | Verdict at HEAD | Independent probe and interpretation |
|---|---|---|
| F1: hostile subclasses | **Closed** | 22 checks rejected hostile Decimal, str, tuple, date and int subclasses and non-exact objects/Provenance values. Probes included an `as_integer_ratio` trap, deceptive name equality, tuple membership, exposure comparison and date equality, plus consumed model Decimal fields. Validation rejected them before their decision methods could run. |
| F2: huge lots / integer-string conversion | **Closed** | With copied model `volume_max=1E+5000` and equity `1E+5010`, sizing returns exactly `1E+5000` lots, `capped_at_volume_max`; the corresponding gate agrees. The independent negative-count defect is new finding F3, not a failure of this fixed lots conversion. |
| F3: oversized rational inputs | **Closed for the v1.3 bound requirement** | 87 independent calls used high/low adjusted exponents and 1,001-digit coefficients across Decimal slot families: equity, baselines, request lots/prices/stops, policy ratios, budget, consumed model fields, sizing displays and stop-change prices. Every call raised the required slot error; slowest 0.000023 s. A sentinel replacing the Fraction conversion helper confirmed rejection before conversion. New F2 concerns a permitted zero representation in the later display path. |
| F4: use-time request/state validation | **Closed for the original request/state scope** | 41 mutation calls covered invalid request fields, state dates/baselines/flags/policy and nested policy fields through gate, update and restart. Invalid values were rejected with the expected errors. The remaining consumed-model domain gap is new F1. Valid-valued state forgery remains the documented E1 limit. |
| F5: changing provenance Mapping | **Closed for the constructor defect** | A Mapping returned a valid Provenance on each key's first read and an invalid string on later reads. Construction read each key once, validated that snapshot, stored the immutable copy and produced stable `unknowns()`. External source-dict mutation and proxy writes are covered by the passing acceptance tests. |
| F6: stale/earlier days | **Closed** | A next-day request with old state returns `stale_state`; an earlier request day raises `TimeReversal`. Current equity 9,925 and 9,800 is refused at the inclusive daily/experiment thresholds even when flags were initially clear. Combined-reason probes include stale state alongside other reasons. |
| F7: fresh start bypasses same-day daily halt | **Closed by approved E1 allocation, not enforcement here** | Replayed both paths: same-day restart preserves daily halt, whereas a new authorized start gets new baselines/clear flags. Contract v1.3 explicitly requires E1 to forbid a fresh start when same-account/same-day journal state exists. This pure module has no journal/account information with which to enforce it. |
| F8: public state constructors/replace | **Closed by approved contract wording, not enforcement here** | Replacing baselines and flags can still manufacture a state that passes the gate. The revised invariant expressly excludes that behavior and requires E1 architecture restrictions and journal-only restore. No unapproved policy substitution parameter exists on gate/update/restart; deliberate state/policy replacement is the documented integration limit. |

## AC status

PASS denotes the evidence actually exercised below. The passing literal fixtures do not override a related violated API rule or invariant.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | **FAIL** | All nine specified sizing fixtures and 2,160 additional exact-oracle cases pass, including floor/cap/minimum and display values. F1 violates the required risk invariant through a consumed model field; F2 fails sizing for a permitted zero budget. |
| AC-02 | **PASS** | Acceptance tests and independent boundary probes confirm inclusive daily thresholds, retained same-day baseline/latch, fresh-day baseline/reset and `TimeReversal`. Input states remain unchanged. |
| AC-03 | **PASS** | Experiment halt remains latched across recovery/day changes. Independent calls reject unlisted/case-mismatched names, blank reason and unhalted restart. Authorized restart rebases experiment equity, keeps policy identity and retains the same day's daily halt/baseline; next day rolls daily state correctly. |
| AC-04 | **FAIL** | Specified fixtures and 16,800 independently computed gate cases pass for valid models: all reasons, sorted combinations, re-sizing, current thresholds and day rules. F1 nevertheless allows an over-budget request after incomplete model validation. |
| AC-05 | **PASS** | Passing acceptance tests plus 24 independent stop-change cases across both sides and three price scales: removal and widening refused, equality/tightening allowed; bad type/domain validation precedes the decision. |
| AC-06 | **FAIL** | The suite validates exact types, frozen public records, literal H001 provenance and `unknowns`, snapshots, bounded Decimal slots and request/state/policy revalidation. F1/F2/F3 expose remaining domain/error-handling failures outside those tests. |
| AC-07 | **PASS** | Full suite: **651 passed in 2.71s**, zero skipped. Independent AST/source inspection found no prohibited operations/imports or float name/literal. Red-flag scan exit 0, two explained pattern groups; secret and order/account-mutation groups empty. No dependencies/lockfiles changed. |

## Checks run

All successful checks below used HEAD `60dfbfdb7a857210957d395b4f3c27648f784a1d`. Times are 2026-10-22 +07. Python ran only through uv, with bytecode writes disabled; no packages/configuration were changed. Installed runtime observed: CPython **3.12.15**, uv **0.13.0**, project pytest pin **9.1.1**.

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| From repo root: `& 'C:/Program Files/Git/bin/bash.exe' -c 'uv run --offline pytest tests -q -p no:cacheprovider'` | **PASS**, exit 0; exact summary `651 passed in 2.71s`; no skipped/deselected | `60dfbfd` | 10:07 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh origin/main` | **PASS**, exit 0; `Pattern groups with hits: 2`; explanations below | `60dfbfd` | 10:07 |
| `uv run --offline python -B -`, in-memory exact Fraction oracle and fixture matrix | **PASS**, 2,169 sizing/display cases; 16,800 gate cases; 36 exact threshold boundaries; 24 stop changes; restart/context/range probes | `60dfbfd` | 10:06–10:11 |
| `uv run --offline python -B -`, in-memory security attack/rejection probes | **PASS** for the listed original-defect checks: 22 hostile-type, 41 mutation and 87 oversized-slot calls, plus huge lots, Mapping and date checks | `60dfbfd` | 10:08–10:11 |
| `uv run --offline python -B -`, R1–R3 above and root independent replays | **FAIL** against contract: three reproducible findings; diagnostic scripts themselves exit 0 | `60dfbfd` | 10:08:46, 10:10:38 |
| `uv run --offline python -B -`, `pytest.main(['tests/unit/risk','-q','-p','no:cacheprovider'])` under an in-memory line trace | **PASS**, `22 passed in 0.94s`; no trace/coverage files written | `60dfbfd` | 10:08–10:09 |
| Read raw working-tree bytes and `git show HEAD:<path>` / `git show 81322d9:<path>` via an inline Python SHA256 comparison | **PASS**, all three locked files identical; digests below | `60dfbfd` vs `81322d9` | 10:06–10:08 |
| Inline Python AST/frozen-dataclass inspection of all six risk source files | **PASS**, permitted imports, no float names/literals, all five public dataclasses frozen | `60dfbfd` | 10:06–10:08 |
| `git diff --check origin/main...HEAD` | **PASS**, exit 0, no output | `60dfbfd` | 10:12 |
| `git status --short`, tracked/index diff names, HEAD check and inline report/locked-byte validation | **PASS**, only `?? docs/reviews/CORE-003-r1.md`; index and tracked files unchanged; three locked files still byte-identical; report structure/whitespace checks pass | `60dfbfd` | 10:16 |

Harness setup failures are separate from these passing checks: initial delegate `uv run --offline python -B -` attempts without `src` on the import path stopped with `ModuleNotFoundError: No module named 'sochron'` before running probes (**BLOCKED**). Subsequent standalone probes supplied process-local `PYTHONPATH=src` or `sys.path.insert(0, 'src')`, consistent with the repository's pytest `pythonpath`, without changing configuration. `rg` was unavailable in PowerShell (**BLOCKED**); read-only `Select-String`/`Get-Content` searches supplied the needed inspection. These failures do not count as passing evidence.

### Exact oracle and numerical coverage

The independent oracle constructs Fractions directly from original Decimal inputs. For each sizing case it calculates `R = equity * risk_per_trade`, `per = distance * contract_size + budget`, integer step count `R // (per * step)`, cap count `volume_max // step`, and then the minimum-volume rule. It compares exact lots/reason and all three independently rounded displays, and checks exact `lots * per <= R`. The oracle does not call risk's arithmetic helpers.

Additional sizing matrix: three models (H001; step .003/min .007/max 3.001; contract size 117.3/step .025/min .055/max 7.011), two policies (H001 and risk fraction .001234567890123456789012345678901), eight equities (50, 99.99, 800, the contract's 9599.9999999999999999999999999 edge, 9600, 10000, 25000, 100000000), nine distances (.01, .1, .9999999999999999999999999999, 1, 1.0000000000000000000000000001, 2.5, 12, 50, 105.333333333333333333333333333), and five budgets (0, .01, 1.77, 10, 139.99): **2,160**, plus all **nine AC-01 fixtures**.

The **16,800** gate cases cross baselines 100/10000, both latch flags, five equities around/beyond thresholds, same/next request days, both sides, five stops including missing/equal/wrong-side, seven lots including negative/zero/off-grid/over-max, and exposures 0/1/2. Expected reason sets are independently derived from Fraction predicates, then sorted; allowed must be exactly equivalent to an empty reason set. Additional earlier-day probes check the exception path. Realistic H001 price 4012.90 with stops 4000.90, 4024.90 and 3992.90 is included.

The **36** threshold cases include high-digit baselines and custom finite ratios, exact equality and immediately adjacent exact values. Decimal precision/rounding/traps/flags of hostile caller contexts were preserved. Independent range probes accepted exact subnormal displays `1E-1000000` and `1E-1000026`; inexact underflow and overflow became `RiskError`. Locked tests also exercise per-lot and actual-risk display range failures and the single-rounding discriminator. Source inspection confirms display uses a copy of `sochron.costs.CONTEXT`, with Overflow/Underflow traps enabled, and decisions never use display values.

### Locked-test integrity

Raw bytes match **working tree = HEAD = red commit `81322d9`**, including the architecture file unchanged by the r2 patch. The hashes match the applicable handoff tables (r2 acceptance/golden entries and original architecture entry).

| File | SHA256 |
|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `69cd888f057fbcc1365f41d3aaae448dfccb6caf1b94e945029d120fedfab373` |
| `tests/golden/CORE-003/risk_cases.py` | `68b34aced4943deda4ada60ed2d33872ba03ccebc8736fa29e38b5b64ec2e7c2` |
| `tests/architecture/test_imports.py` | `259ac6d4a9c9b0dfd165f0936b092ca458bde033b453c4ffde3b44787933b195` |

No locked test was deleted, skipped or weakened after the red commit. The implementer's **22** unit tests add actual assertion coverage for custom policies/grids, split baselines, exact edges, subclasses, Mapping snapshots, mutation revalidation, day checking and bounds. In-memory tracing observed risk-source line execution of gate 102/118, halts 65/68, policy 127/137 and sizing 79/83 potential compiled executable lines. This is an informal line-execution measure, not branch coverage or proof of correctness. Unit tests do not exercise `check_stop_change` or every direct `GateDecision` error; locked acceptance supplies that coverage. The new findings show why the green suite is insufficient by itself.

### Red-flag scan groups

- **Type checks disabled:** two actual `type: ignore[arg-type]` comments in negative unit tests intentionally passing a string day and integer halt flag; the remaining hits are evidence/handoff/review prose quoting test patterns. No suppression in production risk code or locked CORE-003 tests.
- **Lint disabled:** documentation prose quoting `noqa`; no new production lint suppression.
- **Control files touched:** the three Codex-authored locked test files, plus `src/sochron/risk/policy.py` and `docs/reviews/CORE-003-security-pre-r1.md` selected by filename heuristics. This list is separate from the two pattern groups and does not itself grant control-change approval.
- **Empty groups:** secrets/secret-like values, order/account mutation, destructive/bypass patterns, placeholder/mock code. No deleted/renamed tests. The working tree was clean when scanned; this report was written afterward and is intentionally unstaged.

## Checked, nothing found (and how)

- Reviewed the 22-file PR diff as a team. Implementation stays in the contract's risk/unit/evidence/handoff/PROGRESS paths. Contract and prior review files are the explicit setup/review artifacts of this task. No edits to costs, core, timebase, credentials, CI, dependency declarations or lockfiles; no unexplained application scope expansion.
- All API-block exports exist. The extra `POLICY_FIELDS` export is an additive constant, not a new policy-changing path. Mapping proxies need not be hashable under this contract.
- H001 values, all five source/date/status/note literals, and the sorted `unknowns(H001_RISK)` tuple match the approved contract and passing locked fixtures. Policy inputs are copied into an immutable provenance container.
- No production float name/literal, clock, random, terminal access, I/O or dynamic imports. Imports are stdlib, costs and risk-local modules. Five public dataclasses and the internal exact-result dataclass are frozen. Normal functions do not mutate prior state/policy; the constructor assignment only installs its provenance snapshot.
- Source inspection and conversion sentinels found no public path converting an oversized Decimal before its slot bound. Gate validates request, equity, day, state/nested policy, model fields and budget before collecting reasons. F1 is the omitted **domain** portion of that model validation; F2 passes the bound legitimately and fails later.
- For valid models/policies, no gate bypass found at/beyond current loss thresholds, with too many exposures, missing/wrong-side stop, excessive lots or an unrolled request day. Stop-change removal/widening is refused on both sides. Gate recomputes sizing from the request and the state policy, including the cost budget; stress_factor does not affect this formula.
- No public gate/update/restart parameter can replace the state policy. Fresh-start authorization, restart authorization/reason/halted-only checks and same-day daily latch preservation match the approved rules. Name-only identity, forged valid state and broker-input truth remain explicitly assigned to E1.
- F01–F18 checklist walked: per-AC evidence and delivery limits recorded; locked-test integrity checked; no production fakes, dependency/API additions, toolchain drift, hidden error swallowing, secrets, destructive operations or out-of-scope code. Boundary/error-handling exceptions are the findings above. Historical review text was treated as evidence, not instructions.
- Sequential duplicate calls are deterministic and carry no external effects. There is no send/retry/journal/concurrency implementation in this scope to certify.
- A mixed-type extra provenance-key probe produced a raw sorting `TypeError`. It is **not** counted as a confirmed finding: such input also violates the declared string key type, and the contract leaves exception precedence unspecified for multiple-invalid inputs. Likewise, forcibly replacing an already-created policy's provenance Mapping is not used to reopen the fixed constructor-snapshot finding.

## Not checked (and why)

- No broker/terminal/account access, live or Demo execution, credentials, market data, research experiments or holdout access. Risk is a pure decision module; E1's authenticated clearer, journal restore, same-day start prohibition, truthful input binding and send/SL binding remain unimplemented integration responsibilities.
- No CI result, PR label, merge, deployment or owner demo was performed or inferred. The locked-path approval gate was not rerun in this read-only task; its earlier evidence is not reported as a new passing check.
- No production mutation edits, throwaway-branch break-it run or changes to locked tests: the invocation authorizes one report and no `.git` writes. Independent probes used only fresh in-memory objects; they do not substitute for a full mutation-testing campaign.
- No exhaustive thread/concurrency races, cross-platform execution or hostile monkeypatching of module globals. No exhaustive valid-domain performance guarantee; the contract's deadline is only for rejecting out-of-bound inputs. R2 used a bounded child process and an immediately failing allocation, not a memory-exhaustion stress run.
- Native interactive `/review` is not available as a callable action in this headless session. The requested explicit `origin/main...HEAD` diff review was completed directly using the skill procedure.
- The separate `CORE-003-tests-r2` owner decisions and Codex test follow-ups were not reopened. Their known watchdog/coverage limitations do not explain away the implementation failures reproduced here.

Delivery state: **implemented; verification incomplete because F1–F3 remain open; not merged or deployed**. Next action: implementer fixes F1–F3 with failing-before/passing-after unit regressions, then requests an independent finding-ID recheck. Owner/CI acceptance remains separate.

Findings open: 3
