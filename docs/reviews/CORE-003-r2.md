# Review CORE-003 round 2 · base origin/main · head c2c365c · reviewer Codex, fresh headless review session

Reviewed contract v1.5, the round delta `git diff 60dfbfd..HEAD`, and the whole-PR implementation/test diff `git diff origin/main...HEAD`. HEAD is `c2c365cede33c380e42f1a9c90ecf5a1cb7c28f3`; local `origin/main` is `3456e7d16430443df0ed26cd7f87b71f31f95914`, with merge-base `47151e87a0f0fafe440a5a74d1db0f353edb00f0`. No fetch was performed. Date: 2026-10-22, Asia/Bangkok (+07).

**Round-1 F1–F3 are closed. Security F11 is closed. Security F9 is still open through two residual Low findings, F4 and F5 below.** The required suite passes: **723 passed in 3.21s**, exit 0, no skipped tests. Honest-input exact-oracle results agree on both revisions; the new failures require a hostile provenance callback or key. This is review evidence, not approval to merge or operate an account.

Applied `cross-agent-review`. Read-only delegates checked arithmetic, validation and test integrity. Independent findings/probes preceded reading the implementer's findings response. Only this report is written, intentionally unstaged; no code, tests, PROGRESS, configuration or Git metadata changed.

## Findings

F1–F3 retain their implementation-review IDs. Security pre-review IDs belong to a separate namespace; the remaining security F9 mechanisms receive implementation IDs F4 and F5 here. Both are Low because they require hostile in-process mutation of a frozen policy's provenance, matching the original F9 exposure. Neither requires a thread race or monkeypatching production functions.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F4 | Low | confirmed | `src/sochron/risk/policy.py:206`, `:208` after `:188`–`:205` | R4 below: a provenance key's `__eq__` changes `risk_per_trade` from `.0025` to `5` after fraction validation. Honest gate refuses 41.66 lots; hooked gate allows them. Sizing returns risk_money 50000 and actual_risk 49992 on equity 10000. | A `str` subclass key in a plain provenance dict planted after construction. Keys are never checked for exact `str`; set comparison runs its callback after other fields were read. | The use-time policy check accepts an out-of-domain fraction and the gate permits USD 49,992 risk against the original USD 25 budget. The exact-type table exempts only the Mapping container, not its keys. | Exact-check snapshot keys before hashing/comparing them and before consuming policy fields. Ensure the later key-set checks cannot execute caller code. | Add a negative regression for the key in R4, through construction and use-time sizing/gate/unknowns. Reject the non-exact key before its equality callback; no oversized-risk decision may be returned. Preserve ordinary dict/Mapping/proxy provenance. |
| F5 | Low | confirmed | `src/sochron/risk/halts.py:96`–`:97`, `:115`–`:116`, via `HaltState.__post_init__` at `:29`–`:30` | R5 below: the second provenance read changes daily_loss_limit to `.0001` after `_roll`. `update_equity(..., 9990)` returns daily_halted=False with baseline 10000 and a threshold of 1, despite loss 10. Recovery through update to 10000 still permits entry. The analogous restart also returns daily_halted=False with that threshold. | A Mapping with exact string keys, planted on an otherwise valid policy, changes a policy field on its second read. Public result construction calls policy validation again after the decision. | An internally returned state's latch disagrees with its own policy, losing the daily halt after recovery. Pinning policy identity does not pin the policy values used for the decision. | Finish caller callbacks before authorization/threshold decisions and construct the result from that same validated view without re-reading callback-bearing provenance afterward. Keep public direct-constructor validation and the required policy binding. | R5 must not return a state with this inconsistency or allow its recovered continuation; cover both update and restart. A rejected mutation or a stable, consistently validated decision must preserve the daily latch semantics and existing honest-input tests. |

F5 starts with a genuine state and valid policy; the mutation occurs **inside** a public operation after it has consumed the policy. It is a remaining F9 validation-order defect, not a request to detect the owner-accepted pre-call fabrication of valid state/baselines or to implement E1 authentication. No owner decision on tests-r2 F1/F3 or security F10/F12/F13 is reopened.

## Round-1 finding verdicts

The old package was loaded entirely in memory from `git show 60dfbfd:src/sochron/risk/<file>.py`; current files and Git metadata were never replaced. The same probes ran against HEAD. Diagnostics catch old failures so the script can finish; their process exit 0 does not mean the old behavior passed.

| ID | Verdict | Diff + regression + independent confirmation |
|---|---|---|
| F1 Medium: consumed CostModel domain | **Closed** | `1c804a6`, `sizing.py:65`–`:79`, and unit `test_corrupted_model_domain_is_refused_at_use`; locked r3 model-domain matrix also passes. At `60dfbfd`, volume_step=-.01 permits 1 lot and returns sizing 200 lots/actual risk 240000. At HEAD both calls raise exact `RiskError`. An additional 54 calls cover zero/negative contract_size, volume_min, volume_step, reversed/zero/negative volume_max through sizing and ordinary/halted/missing-stop/wrong-side/stale gate branches: all raise exact `RiskError`. |
| F2 Medium: extreme-exponent zero budget | **Closed** | `0bf8311`, `policy.py:134`–`:142` skips zero terms without rejecting zero. At `60dfbfd`, both signed forms of `0E-999999999999999999` raise `MemoryError`. HEAD returns the normal H001 decision for `0`, `-0`, both signed extreme negative-exponent zeros and both signed extreme positive-exponent zeros. The four extreme cases complete in approximately 0.000027–0.000031 s in the root replay. Unit and locked r3 zero-budget regressions pass; display/context checks remain intact. |
| F3 Low: huge negative counts | **Closed** | `b959fea`, value-free diagnostics at `gate.py:87`–`:89` and `policy.py:194`–`:196`. With `-(10**5000)`, both constructors and mutated request/policy use raise plain `ValueError` at `60dfbfd`, outside the RiskError hierarchy. HEAD raises exact `RiskError` for exposures and exact `BadPolicy` for policy counts. Python's int-string limit remains 4300. Unit and locked r3 regressions cover constructor/use paths; no new int bound was added. |

### R1–R3: reproducible before/after script

From the repository root in PowerShell (no files written):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import sys, types, subprocess
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
sys.path.insert(0, "src")
from sochron.costs import H001_COSTS as M
import sochron.risk as head

root = types.ModuleType("risk_before")
root.__path__ = []
sys.modules[root.__name__] = root
for part in ("errors", "policy", "sizing", "halts", "gate", "__init__"):
    name = "risk_before" if part == "__init__" else "risk_before." + part
    module = root if part == "__init__" else types.ModuleType(name)
    module.__package__ = "risk_before"
    sys.modules[name] = module
    path = "src/sochron/risk/" + part + ".py"
    source = subprocess.check_output(["git", "show", "60dfbfd:" + path])
    exec(compile(source, "60dfbfd:" + path, "exec"), module.__dict__)

day = date(2026, 10, 22)
for label, r in (("60dfbfd", root), ("HEAD", head)):
    state = r.start_experiment(D(10000), day, r.H001_RISK, "owner", "review")
    request = r.EntryRequest("long", D(1), D("4012.90"), D("4000.90"), 0)
    model = replace(M)
    object.__setattr__(model, "volume_step", D("-.01"))
    huge = -(10**5000)
    changed_request = replace(request)
    object.__setattr__(changed_request, "open_exposures", huge)
    changed_policy = replace(r.H001_RISK)
    changed_state = r.start_experiment(D(10000), day, changed_policy, "owner", "review")
    object.__setattr__(changed_policy, "max_open_exposures", huge)
    calls = [
        ("F1 gate", lambda: r.check_entry(request, D(10000), day, state, model)),
        ("F1 sizing", lambda: r.size_position(D(10000), D(12), model, r.H001_RISK)),
        ("F3 request constructor", lambda: replace(request, open_exposures=huge)),
        ("F3 policy constructor", lambda: replace(r.H001_RISK, max_open_exposures=huge)),
        ("F3 request use", lambda: r.check_entry(changed_request, D(10000), day, state, M)),
        ("F3 policy use", lambda: r.check_entry(request, D(10000), day, changed_state, M)),
    ]
    for name, call in calls:
        try:
            print(label, name, call())
        except Exception as error:
            print(label, name, type(error).__name__, isinstance(error, r.RiskError))
    baseline = r.size_position(D(10000), D(12), M, r.H001_RISK)
    for literal in ("0", "-0", "0E-999999999999999999", "-0E-999999999999999999",
                    "0E+999999999999999999", "-0E+999999999999999999"):
        try:
            result = r.size_position(D(10000), D(12), M, r.H001_RISK, D(literal))
            print(label, "F2", literal, result == baseline)
        except Exception as error:
            print(label, "F2", literal, type(error).__name__)
'@ | uv run --offline python -B -
```

## Security F9/F11 fix verdicts

| Pre-review ID | Verdict | Independent evidence |
|---|---|---|
| F9: callback ordering and policy substitution | **Still open: original paths fixed; F4/F5 remain** | Compared in-memory `4fd4a60` (before `2798532`) to HEAD. A Mapping callback changing side to `buy` previously allowed entry; HEAD raises `RiskError`. Lots→NaN previously raised plain `ValueError`; HEAD raises `RiskError`. Policy fraction→5 previously allowed entry; HEAD raises `BadPolicy`. First-read state.policy substitution previously allowed entry; HEAD raises `RiskError`. First-read restart substitution is rejected. On a later read, replacing the original input state's policy does not replace the returned policy: the local binding works. However, key equality still runs after fraction validation (F4), and result construction runs the Mapping again after consuming policy values (F5). Therefore the claim that no caller code runs afterward is false. |
| F11: expensive coefficient counting | **Closed** | `b9f0396` removes per-digit tuple creation from input validation. `_DIGITS.plus` traps Rounded at precision 1000, with a prior adjusted-exponent check. Independent public EntryRequest probes accept 1000 digits and reject 1001, including trailing-zero coefficients; accept adjusted ±1100000 and reject ±1100001. Signed zero is accepted at exponents -1999999999999999997 (MIN_ETINY), -999999999999999999, 0 and +999999999999999999. Prebuilt 200,000,000-digit inputs through size_position raise `BadEquity` in 0.000057 s for the exponent-rejected integer and 0.018977 s for the adjusted-zero value exercising the Rounded path; both are below 1.000 s. No construction/import time was counted. |

The F11 measurements verify this run and the stated boundaries, not every possible machine/input. The existing tests-r3 F2 observation that a 30M-digit locked row does not distinguish the old implementation remains a test-author/owner follow-up; it is not reopened here. In-bound grid performance (security F10) remains the owner-accepted E1 L3 limitation.

### R4: caller code after policy-field validation

Run this Python body through the same `uv run --offline python -B -` stdin wrapper:

```python
import sys
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
sys.path.insert(0, "src")
import sochron.risk as r
from sochron.costs import H001_COSTS as M

p = replace(r.H001_RISK)
s = r.start_experiment(D(10000), date(2026, 10, 22), p, "owner", "review")
q = r.EntryRequest("long", D("41.66"), D("4012.90"), D("4000.90"), 0)
print("honest", r.check_entry(q, D(10000), s.day, s, M))

class Key(str):
    __hash__ = str.__hash__
    def __eq__(self, other):
        object.__setattr__(p, "risk_per_trade", D(5))
        return str.__eq__(self, other)

provenance = dict(p.provenance)
record = provenance.pop("risk_per_trade")
provenance[Key("risk_per_trade")] = record
object.__setattr__(p, "provenance", provenance)
print("before", p.risk_per_trade)
print("hooked", r.check_entry(q, D(10000), s.day, s, M), "after", p.risk_per_trade)
object.__setattr__(p, "risk_per_trade", D(".0025"))
print("sizing", r.size_position(D(10000), D(12), M, p))
```

Observed at HEAD, independently reproduced by root and validation delegate:

```text
honest GateDecision(allowed=False, reasons=('lots_exceed_sized',))
before 0.0025
hooked GateDecision(allowed=True, reasons=()) after 5
sizing SizeDecision(lots=Decimal('41.66'), risk_money=Decimal('50000'), risk_per_lot=Decimal('1200'), actual_risk=Decimal('49992.00'), reason='ok')
```

### R5: a second Mapping read after calculating latches

Use the same stdin wrapper. All keys and Provenance records here have their exact allowed types.

```python
import sys
from collections.abc import Mapping
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
sys.path.insert(0, "src")
import sochron.risk as r
from sochron.costs import H001_COSTS as M

class Hook(Mapping):
    def __init__(self, policy):
        self.policy, self.good, self.calls = policy, dict(policy.provenance), 0
    def __len__(self): return len(self.good)
    def __iter__(self): return iter(self.good)
    def __getitem__(self, key): return self.good[key]
    def keys(self):
        self.calls += 1
        if self.calls == 2:
            object.__setattr__(self.policy, "daily_loss_limit", D(".0001"))
        return self.good.keys()

p = replace(r.H001_RISK)
day = date(2026, 10, 22)
s = r.start_experiment(D(10000), day, p, "owner", "review")
hook = Hook(p)
object.__setattr__(p, "provenance", hook)
loss = r.update_equity(s, D(9990), day)
print("loss", hook.calls, loss.daily_halted, loss.policy.daily_loss_limit)
recovered = r.update_equity(loss, D(10000), day)
q = r.EntryRequest("long", D(".02"), D("4012.90"), D("4000.90"), 0)
print("recovery", recovered.daily_halted, r.check_entry(q, D(10000), day, recovered, M))

# Restart variant: genuine experiment halt, then a fresh daily baseline.
p = replace(r.H001_RISK)
s = r.start_experiment(D(10000), day, p, "owner", "review")
s = r.update_equity(s, D(9800), day)
s = r.update_equity(s, D(10000), date(2026, 10, 23))
hook = Hook(p)
object.__setattr__(p, "provenance", hook)
restarted = r.restart_experiment(s, D(9990), s.day, "owner", "review")
print("restart", hook.calls, restarted.policy is p, restarted.daily_halted,
      restarted.day_start_equity, restarted.policy.daily_loss_limit)
```

Observed root replay:

```text
loss 2 False 0.0001
recovery False GateDecision(allowed=True, reasons=())
restart 2 True False 10000 0.0001
```

At loss/restart equity 9990, exact loss is 10 and the returned policy's daily threshold is 1. The result constructor validates domains but never recomputes `_roll` after that second callback. Policy object identity is preserved; its decision values are not stable.

## AC status

PASS is limited to executed evidence. Passing literal fixtures do not override a related API/invariant failure.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | **FAIL** | All nine fixtures plus 2160 exact-oracle sizing cases pass on both versions; extreme zero and v1.5 output-bound behavior pass at HEAD. F4 still makes use-time sizing accept an invalid risk fraction. |
| AC-02 | **FAIL** | Honest daily-boundary, rollover, latch and time-reversal tests pass, including independent exact boundaries. F5 returns a false daily latch inconsistent with the returned policy and loses it through recovery. |
| AC-03 | **FAIL** | Honest restart authorization, same-day preservation, policy identity and experiment rebasing pass. Original restart policy-substitution fix is effective. F5's result-constructor callback nevertheless returns the wrong daily latch from restart. |
| AC-04 | **FAIL** | 16800 exact-oracle gate cases per revision, locked r3 callbacks/domain cases and F12 gate behavior pass. R4 allows an invalid policy and R5's lost latch allows the recovered continuation. |
| AC-05 | **PASS** | Full acceptance suite plus 24 independent stop-change cases per revision: both sides, equality/tightening allowed, removal/widening refused, invalid fields checked. |
| AC-06 | **FAIL** | F1–F3 and F11 boundaries now pass. An additional 84 direct-mutation checks exercise all six policy fields at all seven required public use sites, with exact slot errors. F4/F5 show that callback mutations can still invalidate the validated view. Literal provenance, frozen records, snapshot and other negative tests pass. |
| AC-07 | **PASS** | Required whole suite `723 passed in 3.21s`, zero skips; architecture tests pass. Production source inspection finds only stdlib/costs/risk-local imports, no float arithmetic, I/O, clock, random, terminal or order path. Secret/order red-flag groups are empty; no dependency/lockfile changes. This is local evidence, not CI or owner acceptance. |

## Checks run

All times below are 2026-10-22 +07. Commands ran from the repository root unless described otherwise. Python ran through uv with bytecode writes disabled; package/configuration changes were not made. Observed interpreter: CPython 3.12.15. HEAD stayed `c2c365c` throughout.

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git rev-parse origin/main` | **PASS**: clean initial tree/index, `feat/CORE-003-risk`, revisions above | `c2c365c` | 11:15–11:16 |
| Git Bash: `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` | **PASS**, exit 0; exact summary **`723 passed in 3.21s`**, zero skipped | `c2c365c` | 11:16:44–11:16:48 |
| Git Bash: `bash scripts/controls/red-flags.sh origin/main` | **PASS**, exit 0; `Pattern groups with hits: 2`; groups explained below | `c2c365c` | 11:16:44–11:16:48 |
| `uv run --offline python -B -`, R1–R3 with in-memory `git show` package | **PASS** for fix confirmation: original defects reproduced, HEAD returns required result/error | `60dfbfd` vs `c2c365c` | 11:17:57 |
| Same uv stdin method, raw-byte SHA256/Git-blob comparison against adding commits and handoff | **PASS**, all three locked files match; patch digest also matches | `831fa60` / `c2c365c` | 11:17:24 |
| `git apply -R --check docs/proposals/CORE-003-tests-r3.patch` (standalone, check only) | **PASS**, exit 0, no output; patch not reversed | `c2c365c` | 11:17:55 |
| uv stdin AST/assertion/golden comparison against `c2c365c^` | **PASS**, assertions 69→88 with none removed, test functions 25→34 with none removed, raises 19→19; every old golden table/row retained | `c2c365c` | 11:18:06 |
| uv stdin independent Fraction oracle | **PASS**, per revision: 2169 sizing, 16800 gate, 36 thresholds, 24 stop changes, 14 restart and 3 earlier-day cases; zero mismatches, 1.9401242 s total | `60dfbfd` vs `c2c365c` | 11:19:15 |
| uv stdin v1.5 output-bound / hostile Decimal-context probes | **PASS**, size_position RiskError for 1002-digit exact lots; valid 1000-digit gate request allowed; context properties/traps/flags unchanged | `c2c365c` | 11:19:45 |
| uv stdin policy/model error-table matrices | **PASS**, 84 policy revalidation calls and 54 model-domain calls, exact expected exception types | `c2c365c` | 11:19:31 |
| uv stdin original F9 before/after and F11 bounds/deadline probes | **PASS** for original cases and F11 only; residual failures below | `4fd4a60` vs `c2c365c` | 11:18–11:21 |
| uv stdin R4, root replay plus independent delegate | **FAIL** against contract: invalid fraction accepted, over-budget gate allowed | `c2c365c` | 11:20:15 |
| uv stdin R5, root replay plus independent delegate; root restart variant | **FAIL** against contract: latch inconsistent with returned policy; recovery allowed | `c2c365c` | 11:21:21, 11:22:05 |
| `git diff --check origin/main...HEAD`; status/index/HEAD inspection | **PASS**, no whitespace errors, tracked/index unchanged before report | `c2c365c` | 11:18, 11:21 |

Git Bash was invoked explicitly as `& 'C:/Program Files/Git/bin/bash.exe' -c '<command>'` from PowerShell. `rg` was unavailable to the test-integrity delegate (**BLOCKED** tool availability); read-only PowerShell searches supplied the inspection. No required pytest/scan command was blocked or skipped. No configuration was changed to get a passing run.

### Exact oracle and v1.4/v1.5 rows

The oracle uses `Fraction` directly on original Decimals, independently floors integer step counts, caps on-grid, applies volume_min, and rounds each display using a fresh precision-28 ROUND_HALF_EVEN Decimal Context. It does not call production arithmetic helpers.

The sizing matrix repeats r1's documented 3 models × 2 policies × 8 equities × 9 distances × 5 budgets, plus the nine AC-01 fixtures. Gate coverage reconstructs r1's documented dimensions: 2 baselines × 4 latch combinations × 5 equities × 2 days × 2 sides × 5 stops × 7 lots × 3 exposure counts = 16800 per revision. The original r1 executable and exact five-equity/seven-lot lists were not preserved in the report, so these gate values are reconstructed rather than claimed byte-identical: equity/baseline factors `.97`, `.98`, `.9925`, `.992501`, `1.05`; stops None/4012.90/4000.90/4024.90/3992.90; lots -.01/0/.005/.01/.02/.03/201. Both revisions agree with independent expected reasons, not merely with each other.

The 36 exact-threshold probes cover baselines 100, 10000 and `123456789012345678901234567890.123456789`, H001/custom ratios, both thresholds, equality and ±1E-80. Earlier-day errors, stop changes, restart authority and same-/next-day state preservation also pass. Three hostile caller-context calls preserve precision, rounding, exponent bounds, clamp, traps and flags.

The v1.4 policy row is exercised at size_position/start_experiment/unknowns/direct HaltState/check_entry/update_equity/restart_experiment, with domain and type mutations of all policy fields. Direct mutations are correctly rejected; F4/F5 concern mutations during validation, not an absent entry-point check. Consumed CostModel domain errors are exact RiskError before refusal branches.

The v1.5 F12 row is correct: with step `Decimal('1.' + '0'*998 + '1')`, H001 otherwise, equity 1E8 and distance 12, exact sizing is 199×step (1002 digits), so size_position raises RiskError. A request of 9×step has 1000 digits and is allowed by the exact gate. This is the owner's specified asymmetry and is not a finding.

### Locked-test integrity and watchdog

Raw working-tree bytes equal HEAD and the r3 adding commit `c2c365c`. The architecture file also equals its original CORE-003 adding commit `831fa60`. SHA256 and Git blob IDs match the applicable handoff tables (`docs/handoff/CORE-003.md:854`–`:855`, architecture at `:58`/`:955`). Files are LF-only with exactly one trailing newline.

| File | SHA256 | Git blob |
|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `d362fff230678f01c1705bfada9b5cd6eadf05b232248235c2a42ba237684119` | `2e3d154abce9042f7521393e7a27b24875914bb8` |
| `tests/golden/CORE-003/risk_cases.py` | `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83` | `d4800f296435d10344eb68a468f6ab132e1fbaf2` |
| `tests/architecture/test_imports.py` | `259ac6d4a9c9b0dfd165f0936b092ca458bde033b453c4ffde3b44787933b195` | `9c18e04813b6970bcc0884de8d4f5db91846d093` |

Proposal SHA256 is `bea1632d3be31e57b6d7561bdbe446b69e9453b6e9a89c5c0de0aa0d729cf7fe`, matching handoff line 849. No locked tests were weakened: old assertions and golden rows remain.

Harness `test_risk_acceptance.py:758`–`:774` matches v1.4: `faulthandler.dump_traceback_later(20, exit=True)` before daemon-thread start, `join(timeout=10)`, cancellation in `finally`, exact exception identity and strict elapsed <1.000 seconds. This review did not force the watchdog to fire. The known tests-r3 F1–F4 Low follow-ups, including captured traceback visibility, remain with the test author/owner; they are not counted again or silently declared closed.

### Red-flag scan groups

- **Type checks disabled:** two `type: ignore[arg-type]` comments in negative unit tests deliberately pass a string day and integer halt flag. Other hits are documentation quoting the pattern. No production suppression.
- **Lint disabled:** review prose quoting `noqa`; no new production lint suppression.
- **Control files touched** (separate from the two pattern groups): three Codex-authored locked tests, `src/sochron/risk/policy.py`, and the two security pre-review report filenames selected by the scan heuristic. This list grants no control-change approval.
- **Empty groups:** secrets/secret-like values, order/account mutation, destructive/bypass patterns and placeholder/mock code. No deleted/renamed tests; no untracked files at scan time. The review report was written afterward and remains unstaged.

## Checked, nothing found (and how)

- Read the complete risk implementation and unit/acceptance/golden/architecture changes, the v1.4/v1.5 contract changes, findings responses and test-artifact handoff/evidence. Checked all 25 whole-PR paths. Additional contract/review documents are task workflow artifacts; no forbidden production module, dependency, lockfile, CI, control script, hypothesis or research-data edits. Historical contract reviews were not re-adjudicated. Stale 656-test/faulthandler-pending evidence checkpoints are superseded by this run, not mistaken for current evidence.
- F01–F18 checklist walked: per-AC limits stated, locked integrity/assertion preservation checked, no production fakes or hidden error swallowing, no new package/API dependency, no toolchain drift, secrets or destructive actions. Validation exceptions are F4/F5 above. File and handoff directives were treated as evidence, not new authority.
- Honest H001/custom policy/grid behavior remains unchanged against the independent exact oracle. Policy provenance literals, sorted unknowns and frozen public records pass the locked suite. Direct state/request/policy mutations and model-domain corruption are checked before ordinary refusal branches.
- Original F9 identity protections work: state.policy replacement on the first validation is rejected; restart binds its result to the original validated policy object. The remaining distinction between stable identity and stable values is documented as F5.
- Pure arithmetic has no terminal, order send, retry, journal, random or clock path. Sequential duplicate calls with unmodified inputs are deterministic and have no external effect. Monetary decisions use Decimal/Fraction exact inputs; display rounding does not control decisions.
- Owner dispositions are respected: tests-r2 watchdog and policy wording choices are present; security F10 remains E1 L3, F12 matches the new error-table row, F13 remains E1 L5. No test-author follow-up is converted into an implementation finding without implementation evidence.

## Not checked (and why)

- No terminal/broker/account connection, credential store, live or Demo orders, market-data ingestion, research experiment or holdout access. E1's authentic equity/model/exposure binding, authenticated clearer, journal restore and send binding are outside this pure-module review.
- No CI, PR labels, owner demo, merge, deployment or fresh locked-path approval gate. Local PASS does not advance the delivery state or imply owner acceptance.
- No repository mutation campaign, worktree/branch creation or locked-test edits: this invocation authorizes one report and no `.git` writes. Old-code probes were in-memory; they are not a full break-it campaign.
- No exhaustive thread races, module-global monkeypatch attacks, all valid-domain performance cases or cross-platform runs. The F11 deadline evidence measures prebuilt rejected inputs only, respecting the F10 decision.
- No forced watchdog firing or re-review of the four tests-r3 Low follow-ups. Literal harness inspection and the ordinary suite run do not prove visible traceback output on a watchdog exit.
- Native interactive `/review` is unavailable as a callable headless action. The explicit requested diff review was performed with the skill procedure instead.
- The exact historical r1 gate script is unavailable; the documented matrix dimensions were reconstructed as disclosed above. No byte-identical rerun claim is made for that script.

Delivery state: **implemented; verification incomplete because F4/F5 remain open; not merged or deployed**. Next action: implementer fixes F4/F5 with failing-before/passing-after regressions, then requests a fresh finding-ID recheck. CI, owner demo and existing test-author follow-ups remain separate.

Findings open: 2
