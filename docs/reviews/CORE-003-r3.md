# Review CORE-003 round 3 · base origin/main · head 18dcfea · reviewer Claude Code, fresh session acting as Codex reviewer under the role swap (PROGRESS.md `34097d9`)

Reviewed contract v1.6 (`docs/contracts/CORE-003-risk.md`, Tier High), the round delta `git diff c2c365c..HEAD`, and the whole PR `git diff origin/main...HEAD`. HEAD is `18dcfead767e85f5346349ad35c01db6936738d2`. Local `origin/main` and `main` are both `3456e7d16430443df0ed26cd7f87b71f31f95914`, merge-base `47151e87a0f0fafe440a5a74d1db0f353edb00f0`. No fetch was done. Date 2026-10-22, all times +07. I am neither the implementer nor the test author of CORE-003. I followed `.agents/skills/cross-agent-review/SKILL.md` as a plain procedure. I wrote my probes and findings before reading the implementer's findings response in `docs/handoff/CORE-003.md`. This file is the only change. It is not staged.

**Round-2 F4 and F5 are closed.** Both reproduce at `c2c365c` and are refused, or decided consistently, at HEAD. HEAD reads provenance exactly once per public call. Honest inputs behave the same on both revisions under an independent exact oracle (157,296 cases per revision, 0 mismatches). The suite passes: **783 passed in 3.87s**, 0 skipped.

**The F9 class is not closed.** Caller code can still run after validation and after a decision through another carrier: a `str`-subclass key planted in an object's own instance `__dict__` (**F6, Low, confirmed**). It reproduces both R4 impacts (the gate allows 41.66 lots, USD 49,992 risk against a USD 25 budget) and R5 impacts (a lost daily latch, then an allowed entry after recovery). At HEAD it also makes `_new_state` return states that a direct `HaltState(...)` rejects. A process-wide ABC hook reached through `Fraction(Decimal)` has the same gate effect (**F7, Low, question**). Its scope is for the owner to decide. This is review evidence. It is not approval to merge or to operate an account.

## Findings

Severity matches F4/F5. Both new findings need hostile code running in the same process that changes a frozen object after construction, or global interpreter state. Neither needs a thread race, and neither reassigns a module attribute or a production function.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F6 | Low | confirmed | `src/sochron/risk/policy.py:202`–`:210` (policy fields read after the fractions at `:193`–`:196`); `gate.py:136`–`:166` (request, model and state fields read after `validate_state` at `:134`, then read again to decide); `sizing.py:72`–`:77`, `:95`–`:101`; `halts.py:47` (`state.policy` read again for the pin check), `:81` via `:92`, `:98`–`:105`, `:119`, `:135`; `halts.py:56`–`:75` (`_new_state` skips validation) | R6 below. At HEAD (20:19:54): **(a)** a key planted in the policy's own dict lifts `risk_per_trade` to 5 when `halt_clearers` is read. The gate then returns `allowed=True` for 41.66 lots (honest: `('lots_exceed_sized',)`), `size_position` returns risk_money 50000 and actual_risk 49992.00, and `start_experiment` returns a state bound to `risk_per_trade` 5. **(b)** the same lift through the request's dict (`side`), **(c)** the model's dict (`volume_min`) and **(d)** the state's dict (`policy`, 2nd read = pin check) each gives `allowed=True`. **(e)** `update_equity(…, 9990)` reads `state.experiment_start_equity` a 3rd time while building the result. The lowering of `daily_loss_limit` to .0001 lands there, so the result says `daily_halted=False` under a threshold of 1 with a loss of 10. Recovery to 10000 then gives `allowed=True`. The same equities decided under .0001 latch, and the gate gives `('daily_halt',)`. **(f)** `restart_experiment` gives the same `daily_halted=False` under .0001. **(g)** `update_equity` returns `experiment_start_equity` **0**. `c2c365c` gives the same (a)–(f), except: (a) start raised `BadPolicy` and (g) raised `BadEquity`. The old result validation caught those two. F5's fix removed that check. | A key in the instance `__dict__` of a `RiskPolicy`, `HaltState`, `EntryRequest` or `CostModel`, swapped after construction through `vars(obj)`. Every later attribute read of that field calls the key's `__eq__` from the dict lookup. The F4 key check covers only provenance keys. | v1.6 `:127` says `check_entry` never allows a request or state changed during the check, and results are "built from validated values, without reading the policy again after deciding". v1.4 `:126` says use-time policy validation must catch out-of-domain fractions. Both are defeated, with the same effect as R4 and R5. Through (a) and (g), `_new_state` returns states that a direct `HaltState(...)` rejects (`BadPolicy` at 20:13:35, `BadEquity` at `c2c365c`). The next public use refuses such a state, so (a)/(g) alone gives no `allowed=True`. The E1 L2 ban list (`:200`) names `HaltState(`, `replace(` and `object.__setattr__`. It does not name `vars(`/`__dict__` writes, which also change frozen records. | Read each consumed field once per object per call into locals, and validate and decide only from those locals, never `obj.field` again. Before those reads, prove that the instance dict is an exact `dict` whose keys are all exact `str`: iterating an exact dict and calling `type()` run no caller code. Alternative for records that risk owns: `@dataclass(frozen=True, slots=True)` on `RiskPolicy`, `HaltState`, `EntryRequest`. `CostModel` lives in `sochron.costs`, which is out of scope, so it still needs the key check and a single read. Owner, contract text: add `vars(`/`__dict__` writes to E1 L2. | Regression rows for R6 (a)–(g) through construction and every use site. Each must raise `TypeError`/`RiskError`, or return the honest decision with `risk_per_trade`/`daily_loss_limit` unchanged. Every state returned by start/update/restart must be accepted by a direct `HaltState(...)` with the same fields. The honest oracle and the full suite stay unchanged. |
| F7 | Low | question | `src/sochron/risk/policy.py:106`–`:107` (`exact = Fraction(value)`), reached from `policy.py:112`, `gate.py:146`–`:166`, `sizing.py:95`–`:101` | R7 below. At HEAD (20:13:57, again 20:19:54): `allowed=True` for 41.66 lots, with `risk_per_trade` 5 after the call. In the 20:13:57 run the hook ran 22 times in one `check_entry`. CPython 3.12.15's `Fraction.__new__` calls `isinstance(value, numbers.Rational)` on the Decimal. After any ABC cache invalidation, that check walks `Rational.__subclasses__()` and calls the hook's metaclass `__subclasscheck__`. With a scratch variant `exact = Fraction(*value.as_integer_ratio())` patched into this process only, the same hook ran 0 times and the gate returned `('lots_exceed_sized',)` (20:18:34). | Code in the same process defines a `numbers.Rational` subclass whose metaclass has a `__subclasscheck__`, and calls any `ABC.register` to clear the negative cache. No module attribute or production function is reassigned. | Same as F6 (a)/(b): an over-budget entry allowed. It is a question because it relies on global interpreter state. Round 2 left "module-global monkeypatch attacks" unchecked, and the v1.6 example is an object-level planted Mapping. | Owner: decide whether process-wide hooks are in the F9 threat model, or are an E1 deployment obligation. If they are in scope: build the Fraction from `Decimal.as_integer_ratio()`, the method contract `:39` names, so no ABC check runs on a Decimal. | Re-run R7 against the fix: 0 hook calls, honest reasons, `risk_per_trade` unchanged. My variant check ran with ABC caches already warmed by one honest call. A cold-cache process was not proven. |

### Round-2 finding verdicts

The old package was loaded in memory from `git show c2c365c:src/sochron/risk/<part>.py`, as in round 2. Working-tree files and Git metadata were never replaced. The scripts caught exceptions only to print their type.

| ID | Verdict | Diff + regression + my confirmation |
|----|---------|-------------------------------------|
| F4 Low (str-subclass provenance key ran code after the fractions were checked) | **Closed** | `073ab70`, `policy.py:188`–`:192`: keys must be exactly `str` right after the single snapshot, before any other field is read. R4 at `c2c365c` (20:12:59): gate `allowed=True` and `risk_per_trade` → 5. Sizing returned risk_money 50000 and actual_risk 49992.00. `unknowns` returned normally after the lift, and `start_experiment` raised `BadPolicy` only after the key's code had run. R4 at HEAD: all four raise `TypeError: provenance keys must be exactly str` and `risk_per_trade` stays 0.0025. A key with a Python `__hash__` runs only inside the snapshot copy, which v1.6 allows ("read once, before all other fields"). Unit `test_provenance_keys_must_be_exact_str_before_any_comparison` and the locked `test_ac06_provenance_keys_must_be_exact_str` (32 rows) pass in the 783 run. The same impact through the objects' own dicts is F6, a different carrier. |
| F5 Low (results re-read the policy after deciding) | **Closed** | `d7b45b5`, `halts.py:56`–`:75`, `:93`, `:119`, `:138`: results are built by `_new_state` and are not validated again. R5 at `c2c365c` (20:12:59): update made 2 reads, gave `daily_halted=False` under limit 0.0001, and recovery was allowed. Restart made 2 reads and gave `daily_halted=False` under 0.0001. Start made 2 reads and bound limit 0.0001. R5 at HEAD: 1 read each and limit 0.0075 everywhere. `daily_halted=False` is then consistent, because the loss of 10 is below the threshold of 75, and the allowed recovery is the honest result. Read profile (20:17:02): all 8 consumers make exactly one `keys()` and at most one lookup per key per call (`RiskPolicy`, `HaltState`, `size_position`, `unknowns`, start, update, restart, `check_entry`). So the implementation has **no** provenance re-read after deciding, whether by traversal or by key lookup. The tests-r4 F1 test gap is not counted here. Side effect: dropping result validation removed the backstop that caught F6 (a)/(g) at `c2c365c`. That is recorded under F6. |

### R6: caller code through a key in an object's own `__dict__` (F6)

Run from the repository root with `uv run --offline python -B <file>`, or through round 2's stdin wrapper.

```python
import sys
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
sys.path.insert(0, "src")
import sochron.risk as r
from sochron.costs import H001_COSTS as M

DAY, NEXT = date(2026, 10, 22), date(2026, 10, 23)

def plant(obj, field, action, on_call=None):
    """Re-key obj.__dict__[field] with an equal str subclass; its __eq__ runs action on attribute reads."""
    n = [0]
    class Key(str):
        __hash__ = str.__hash__
        def __eq__(self, other):
            n[0] += 1
            if on_call is None or n[0] == on_call:
                action()
            return str.__eq__(self, other)
    d = vars(obj)
    d[Key(field)] = d.pop(field)

def fresh():
    p = replace(r.H001_RISK)
    return p, replace(r.start_experiment(D(10000), DAY, p, "owner", "review"))

big = lambda: r.EntryRequest("long", D("41.66"), D("4012.90"), D("4000.90"), 0)
p, s = fresh()
print("honest", r.check_entry(big(), D(10000), DAY, s, M))
lift = lambda p: (lambda: object.__setattr__(p, "risk_per_trade", D(5)))

p, s = fresh(); plant(p, "halt_clearers", lift(p))
print("a gate", r.check_entry(big(), D(10000), DAY, s, M), p.risk_per_trade)
object.__setattr__(p, "risk_per_trade", D(".0025"))
print("a sizing", r.size_position(D(10000), D(12), M, p))
object.__setattr__(p, "risk_per_trade", D(".0025"))
print("a start policy.risk_per_trade", r.start_experiment(D(10000), DAY, p, "owner", "x").policy.risk_per_trade)

p, s = fresh(); q = big(); plant(q, "side", lift(p))
print("b request", r.check_entry(q, D(10000), DAY, s, M))
p, s = fresh(); m = replace(M); plant(m, "volume_min", lift(p))
print("c model", r.check_entry(big(), D(10000), DAY, s, m))
p, s = fresh(); plant(s, "policy", lift(p), on_call=2)
print("d state", r.check_entry(big(), D(10000), DAY, s, M))

p, s = fresh()
plant(s, "experiment_start_equity", lambda: object.__setattr__(p, "daily_loss_limit", D(".0001")), on_call=3)
loss = r.update_equity(s, D(9990), DAY)
q = r.EntryRequest("long", D(".02"), D("4012.90"), D("4000.90"), 0)
print("e update", loss.daily_halted, loss.policy.daily_loss_limit,
      "recovery", r.check_entry(q, D(10000), DAY, r.update_equity(loss, D(10000), DAY), M))

p, s = fresh()
s = replace(r.update_equity(r.update_equity(s, D(9800), DAY), D(10000), NEXT))
plant(s, "experiment_halted", lambda: object.__setattr__(p, "daily_loss_limit", D(".0001")), on_call=3)
restarted = r.restart_experiment(s, D(9990), NEXT, "owner", "review")
print("f restart", restarted.daily_halted, restarted.policy.daily_loss_limit)

p, s = fresh()
plant(s, "day", lambda: object.__setattr__(s, "experiment_start_equity", D(0)), on_call=2)
print("g update experiment_start_equity", r.update_equity(s, D(9990), DAY).experiment_start_equity)
```

Observed at HEAD `18dcfea` (20:19:54):

```text
honest GateDecision(allowed=False, reasons=('lots_exceed_sized',))
a gate GateDecision(allowed=True, reasons=()) 5
a sizing SizeDecision(lots=Decimal('41.66'), risk_money=Decimal('50000'), risk_per_lot=Decimal('1200'), actual_risk=Decimal('49992.00'), reason='ok')
a start policy.risk_per_trade 5
b request GateDecision(allowed=True, reasons=())
c model GateDecision(allowed=True, reasons=())
d state GateDecision(allowed=True, reasons=())
e update False 0.0001 recovery GateDecision(allowed=True, reasons=())
f restart False 0.0001
g update experiment_start_equity 0
```

A longer variant ran at 20:13:35 on both revisions. It also checked that a direct `HaltState` with the (a) policy value raises `BadPolicy`, and that the (e) equities decided honestly under 0.0001 latch and give `('daily_halt',)`. At `c2c365c`, (a) start raised `BadPolicy` and (g) raised `BadEquity`. Every other row matched HEAD.

### R7: process-wide ABC hook through `Fraction(Decimal)` (F7)

Run it in its own process, because the hook is global:

```python
import abc, numbers, sys
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
sys.path.insert(0, "src")
import sochron.risk as r
from sochron.costs import H001_COSTS as M

DAY = date(2026, 10, 22)
p = replace(r.H001_RISK)
s = r.start_experiment(D(10000), DAY, p, "owner", "review")
q = r.EntryRequest("long", D("41.66"), D("4012.90"), D("4000.90"), 0)
print("honest", r.check_entry(q, D(10000), DAY, s, M))
armed = [False]

class Bump(abc.ABC):
    pass

class Meta(abc.ABCMeta):
    def __subclasscheck__(cls, sub):
        if armed[0] and sub is D:
            object.__setattr__(p, "risk_per_trade", D(5))
            Bump.register(type("T", (), {}))  # invalidates ABC negative caches again
        return super().__subclasscheck__(sub)

class Evil(numbers.Rational, metaclass=Meta):
    pass

Bump.register(type("T", (), {}))
armed[0] = True
print("hooked", r.check_entry(q, D(10000), DAY, s, M), p.risk_per_trade)
```

Observed at HEAD (20:19:54): `honest GateDecision(allowed=False, reasons=('lots_exceed_sized',))`, then `hooked GateDecision(allowed=True, reasons=()) 5`.

## AC status

As in round 2, PASS counts only executed evidence, and passing literal fixtures do not override a related invariant failure. Every FAIL below comes from F6 alone, a Low finding that needs hostile mutation inside the process. Honest-input behaviour passes on every AC.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | **FAIL** | Honest inputs: 2,240 exact-oracle sizing cases (2 policies × 5 models × 7 equities × 8 distances × 4 budgets) give 0 mismatches on both revisions. The cases cover all three reasons, `actual_risk ≤ risk_money` and grid membership. The locked fixtures pass. F6 (a): use-time sizing returns risk_money 50000 after `risk_per_trade` is lifted to 5 mid-call. |
| AC-02 | **FAIL** | Honest inputs: 9,600 random update/restart steps (seeded) match the oracle on day, baselines, both latches and policy identity, on both revisions. R5 is closed. F6 (e): `update_equity` returns a false daily latch under its own returned limit, and the recovered continuation is allowed. |
| AC-03 | **FAIL** | Honest restart behaviour matches the oracle and the locked rows: same-day daily latch kept, experiment rebased, same policy object. F6 (f): restart returns `daily_halted=False` under a limit its loss reaches. |
| AC-04 | **FAIL** | Honest inputs: 138,240 + 7,200 gate cases give 0 mismatches on both revisions, every reason produced at least once (including `stale_state` and `below_min_volume`), 108 allowed in the coverage subset. F6 (a)–(d) give `allowed=True` for 41.66 lots (USD 49,992 risk against a USD 25 budget). F7, which is a question, gives the same. |
| AC-05 | **PASS** | 16 stop-change oracle cases (both sides, equal, tighter, wider, 1E-20 moves, removal) plus the locked rows. `check_stop_change` takes only scalars, so F6 has no carrier there. |
| AC-06 | **FAIL** | The F4 key rows pass: exact `TypeError`, and the key's code never runs. The locked suite and unit tests pass. F6 defeats the v1.4 use-time policy check (`risk_per_trade` 5 accepted). F6 (a)/(g) return states that a direct `HaltState(...)` rejects. |
| AC-07 | **PASS** | `783 passed in 3.87s`, 0 skipped, exit 0. The architecture file is byte-identical to its adding commit `831fa60` and passes. Production imports are stdlib, `sochron.costs` and package-local only. `float` appears only in a docstring. No clock, I/O, random or MetaTrader5. The red-flag secret and order/account groups are empty. This is local evidence, not CI. |

## Checks run

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD origin/main main`, `git merge-base HEAD origin/main` | **PASS**: clean tree, `feat/CORE-003-risk`, revisions as above | `18dcfea` | 20:1x |
| `uv run --offline python -B <scratch>/r4r5.py`: R4/R5 against in-memory `c2c365c` and HEAD | **PASS** for F4/F5 closure: defects reproduce at `c2c365c`, refused or consistent at HEAD | `c2c365c` vs `18dcfea` | 20:12:59 |
| `uv run --offline python -B <scratch>/r6.py`, then the compact R6 above | **FAIL** against contract v1.4/v1.6: F6 (a)–(g) | both / `18dcfea` | 20:13:35, 20:19:54 |
| `uv run --offline python -B <scratch>/r7.py`, then the compact R7 above | **FAIL** (question F7): allowed=True | `18dcfea` | 20:13:57, 20:19:54 |
| `uv run --offline python -B <scratch>/r7_fixcheck.py` (`exact` variant patched in this process only) | **PASS**: 0 hook calls, honest reasons | `18dcfea` + in-memory variant | 20:18:34 |
| `uv run --offline python -B <scratch>/oracle.py`: independent Fraction oracle | **PASS**: per revision, 2,240 sizing, 138,240 gate, 9,600 halt steps and 16 stop changes, 0 mismatches (9.60 s / 11.03 s) | `c2c365c` vs `18dcfea` | 20:15:15–20:15:36 |
| `oracle_stats.py`, `oracle_small.py`: coverage and small-baseline rows | **PASS**: all 9 entry reasons produced; equality at the daily threshold halts in both oracle and production; 7,200 more gate cases, 0 mismatches, 2,352 `below_min_volume` rows | both | 20:16 (end 20:16:16) |
| `readprofile.py`: provenance reads per public call | **PASS**: 1 `keys()`, ≤1 lookup per key, for all 8 consumers | `18dcfea` | 20:17:02 |
| `sha256sum` and `git hash-object` on the 3 locked files; `git rev-parse a4bb3fe:<f> HEAD:<f>`; `git diff --stat a4bb3fe..HEAD -- tests/` and `831fa60..HEAD -- tests/architecture/` | **PASS**: identical to the r4 adding commit and HEAD; architecture unchanged since `831fa60`; hashes match the handoff (table below) | `a4bb3fe` / `18dcfea` | 20:16 |
| `sha256sum docs/proposals/CORE-003-tests-r4.patch` | **PASS**: `9d290dc9ab17b75c0098f51a894f4b50dccc155b2ebf65d3e33b30304285dc27`, same as handoff `:1010` | — | 20:17 |
| `git apply -R --check docs/proposals/CORE-003-tests-r4.patch` | First attempt **BLOCKED** by guard-bash because I chained it after `cd` (block text below). Rerun alone under the owner's standalone-rerun exception: **PASS**, exit 0, no output, not reversed | `18dcfea` | 20:17:2x–20:17:5x |
| uv AST comparison of the locked acceptance file, `c2c365c` vs HEAD | **PASS**: tests 34→38, none removed; asserts 88→104, none missing; `pytest.raises`/`_reject` 44→45; no decorator removed; no skip, xfail or `.only` | `c2c365c` vs `18dcfea` | 20:17:56 |
| `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` (Git Bash, repository root) | **PASS**, exit 0: **`783 passed in 3.87s`**, 0 skipped | `18dcfea` | 20:17:08–20:17:12 |
| `bash scripts/controls/red-flags.sh origin/main` | **PASS**, exit 0, `Pattern groups with hits: 2` (explained below) | `18dcfea` | 20:17:16 |
| `node scripts/controls/check-locked-paths.mjs main` | Expected **FAIL**, exit 1: 3 locked test files need the owner's PR label `owner-approved-control-change`. This is a control result, not a finding | `18dcfea` | 20:17 |
| `git diff --check origin/main...HEAD` | **PASS**, exit 0 | `18dcfea` | 20:17 |

Block text, verbatim: `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run each action separately.` The rerun is the same check-only command, alone, as the owner's recorded standalone-rerun exception for `git apply` (F21) allows. No other block occurred.

The scratch scripts are in `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\fc0827f4-8397-4172-be4e-1f0a730bdb14\scratchpad\`. Python 3.12.15 via uv with `-B` and `PYTHONDONTWRITEBYTECODE=1`. No configuration was changed.

### Locked-test integrity

The working-tree bytes equal `HEAD` and the adding commits. `git diff a4bb3fe..HEAD -- tests/` and `git diff 831fa60..HEAD -- tests/architecture/` are both empty.

| File | SHA256 | Git blob | Handoff |
|---|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `fa1bde04706d177bb13a4da14e00751ff67c85816537e8417932e59d280c94df` | `d2ba11db5958d817c5830fc54a3eda5fa3e7ce35` | `:1016` |
| `tests/golden/CORE-003/risk_cases.py` | `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83` | `d4800f296435d10344eb68a468f6ab132e1fbaf2` | `:855`, `:1017` |
| `tests/architecture/test_imports.py` | `259ac6d4a9c9b0dfd165f0936b092ca458bde033b453c4ffde3b44787933b195` | `9c18e04813b6970bcc0884de8d4f5db91846d093` | `:58`, `:955` |

### Red-flag scan groups

- **Type checks disabled:** the two intentional `type: ignore[arg-type]` comments in negative unit tests (`check_entry` with a str day, and `HaltState(..., 0, False)`). Every other hit is review, handoff or evidence prose that quotes the pattern. No suppression in production code or in locked tests.
- **Lint disabled:** prose quoting `noqa` only.
- **Control files touched** (listed separately): the 3 locked test files (D-006 patches), `src/sochron/risk/policy.py`, and the two security pre-review report names (the scan's naming heuristic). The listing grants no approval.
- **Empty:** deleted or renamed tests, untracked files, secrets, order/account mutation, destructive/bypass patterns, placeholder/mock.

## Checked, nothing found (and how)

- **Scope (F06/F04/F18).** The round touches `src/sochron/risk/{policy,halts}.py`, `tests/unit/risk/`, the locked acceptance file (D-006 patch r4) and workflow docs (contract, handoff, PROGRESS, reviews). No dependency, lockfile, CI, control-script, costs, timebase, core, hypothesis or research edit. Commit `82844d1` ("ฟ") is the owner committing review r2 (handoff `:978`–`:979`). Its message does not follow the convention, but it is docs only, so it is not an implementation finding.
- **Bypass hunting with honest public-API inputs.** At or beyond a loss threshold: both thresholds are exact and inclusive against current equity, regardless of the stored latches, and the equality row halts. Lots above sizing: always `lots_exceed_sized`. A missing or wrong-side stop: always refused, and sizing is skipped. A stale state: `stale_state` for `day > state.day`, `TimeReversal` for earlier days. Another policy: `check_entry`, `update_equity` and `restart_experiment` use only `state.policy`, and the gate does not accept a `SizeDecision` from outside. Widened or removed stop: refused. In the oracle, negative or zero lots, lots of 201 or 41.66, extra exposures, a min-off-grid model and a 0.001 grid all match.
- **Other caller-code points.** Provenance values have an exact `Provenance` type check, which runs no code. `unknowns` reads `p.status` after validation, but `Provenance` fields belong to `sochron.costs`, and changing them before the call has the same effect, so there is no new impact. Scalars are exact `Decimal`/`int`/`bool`/`date`/`str`/`tuple`, whose methods are C code. Error-message `type(x).__name__` reads happen only on raise paths. `__class__` reassignment fails the `type(x) is T` checks. Display rounding uses a copy of `CONTEXT`, and exact arithmetic uses a private context, so the caller's Decimal context does not affect decisions.
- **`_new_state` with honest inputs:** every value it receives was validated in the same call, and the latches are exact bools, so the result is a state a direct `HaltState(...)` accepts (the oracle checks identity and values). It can return an invalid state only through F6.
- **Locked tests:** byte-identical, nothing weakened (AST comparison above), patch digest matches, `-R --check` passes. Owner decisions are respected: tests-r2 F1/F3, tests-r3 F2, security r2 F10/F12/F13 and the tests-r4 F2 contract sentence (`:127`). HEAD checks key types first, which matches that sentence. tests-r4 F1, the gap in the locked rows, is not counted. The implementation question it raises is answered in the F5 verdict: no re-read.

## Not checked (and why)

- No terminal, broker or account connection, no credentials, no orders, no market data, no holdout. E1 obligations (L1–L5, F7 of the security pre-review) cannot be tested through the pure API.
- No CI, PR label, owner demo, merge or deployment. Local PASS does not move the delivery state.
- Thread races, and class-level or module-level monkeypatching (assigning to class attributes or module functions), are out of scope as in round 2. F7 is a process-wide hook without reassignment and is reported as a question. A cold-cache process for the F7 fix variant was not proven.
- The watchdog was not forced to fire, and the mutation runs of the locked tests were not repeated: `docs/reviews/CORE-003-tests-r4.md` covers both. In-bound performance extremes (security F10) are owner-accepted under E1 L3.
- Native Codex `/review` does not apply to this Claude session; the skill procedure was followed instead.

Delivery state: **implemented. Verification is incomplete because F6 is open, and F7 needs an owner scope decision. Not merged or deployed.** Next action: the implementer answers F6, with failing-before and passing-after regressions for R6 (a)–(g). The owner decides F7's scope, and whether to add `vars(`/`__dict__` writes to E1 L2. Then a fresh-session recheck of F6/F7 only.

Findings open: 2
