# Review CORE-002 round 3 · base origin/main · head 2a1b2a1 · reviewer Codex, fresh headless session 2026-10-22

Targeted re-review of **F4 only** and the surrounding impact of its fix. This supplements round 2; F1–F3 remain closed and are not reopened.

- Head: `2a1b2a1fd3c5ea64973be086d31c7476992664ca`; branch: `feat/CORE-002-costs`. Both `main` and `origin/main`: `b2eb69c07a553b30f293689edeaed55526c41c5d`.
- Fix: `cec0f4b3c6ca6773a0f8d9544ce2bcc2e3d965b4`, confirmed by `git log -1 -- src/sochron/costs/charges.py`. Reviewed the complete source/unit-test delta from r2 head `493202c`, contract v1.2, r2 F4 and the requested r2 findings-response handoff.
- Starting tree/index clean. Authorization is limited to this unstaged report; no code, tests, PROGRESS, Git index/commit or external write. One read-only helper independently inspected the fix; the report author ran all probes below.
- The headless interface has no interactive `/review` command; direct contract/diff inspection performs the applicable re-review procedure. Explicit authorization to write this report supersedes the skill's confirmation step and the repository's default checkpoint/commit steps.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F4 | Low | confirmed | src/sochron/costs/charges.py:37–44 | **Closed.** `cec0f4b` rejects all six non-finite Decimal fields before arithmetic; both ordered addition and total equality execute inside `localcontext(CONTEXT)`. Appendix A reproduces r2 at `493202c` and passes at HEAD. | Direct construction with sNaN total under caller InvalidOperation trap True/False. | The former trap-dependent exception and caller flag mutation no longer occur: both modes raise exactly CostsError and preserve caller identity/settings/flags/traps. | Implemented; no further change requested for F4. | Original probe returns `HEAD True CostsError False True` and `HEAD False CostsError False True`; 240 additional calls preserve full caller state, including non-finite rejection, F2 cases and valid AC-04 factories. Full suite passes. |

**F4 verdict: closed.** No defect introduced by the fix was found; no F5 finding is opened.

Findings open: 0

## AC status

Only AC-05 changes verdict (r2 FAIL → PASS). Other PASS statuses are retained with a fresh full-suite run; broader r2 arithmetic/provenance review is not repeated.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Existing locked spread/point/context acceptance test passes in the full suite; relevant implementation unchanged by F4. |
| AC-02 | PASS | Existing locked commission/slippage/stress acceptance test passes; implementation unchanged by F4. |
| AC-03 | PASS | Existing locked swap/debit/credit/triple-night acceptance test passes; implementation unchanged by F4. |
| AC-04 | PASS | Locked round-trip/order/R acceptance test and F2 unit regression pass. Appendix A independently repeats all 11 ROUND_TRIP_ROWS under four caller configurations (44 factory outputs), checks all six fields, repeats 44 F2 cases and 8 R checks. |
| AC-05 | PASS | F4 corrected with identical CostsError under both caller trap settings and unchanged context identity, every setting, flags and traps. All locked negative cases and the new non-finite unit regression pass. |
| AC-06 | PASS | Existing locked provenance/unknowns/frozen/stress-copy test passes; the fix preserves frozen CostBreakdown behavior. |
| AC-07 | PASS | Full suite: exactly **45 passed in 0.09s**, 0 skipped. Architecture checks pass; red-flag secret and order/account mutation groups empty. This is local evidence, not a CI/control-gate verdict. |

## Checked, nothing found (and how)

### F4 reproduction and surrounding impact

Original r2 Appendix B payload, loaded from old source into an isolated in-memory module without checkout or file replacement:

```text
493202c True InvalidOperation True False
493202c False CostsError True False
HEAD True CostsError False True
HEAD False CostsError False True
```

Columns after the revision are caller InvalidOperation trap, exception class, caller InvalidOperation flag, and whether caller repr is unchanged. The old trap-disabled case rejects with CostsError but contaminates the flag; it does not accept this exact sNaN payload.

The strengthened probe also asserts `getcontext() is caller` and snapshots precision, rounding, Emin, Emax, capitals, clamp, every flag and every trap around each call. Four caller configurations combine InvalidOperation on/off with clear/pre-existing Inexact and Rounded flags. Caller precision is 4, rounding ROUND_UP, Emin/Emax -9/9, capitals 0, clamp 1; other traps are enabled.

- **96 non-finite rejections:** sNaN, NaN, +Infinity and -Infinity separately in each of the six fields, under all four configurations; exact CostsError.
- **4 pre-arithmetic rejections:** a non-finite final stress_factor is rejected before adding components whose finite sum would overflow the module context.
- **44 F2 cases:** all-int construction; an int in each field separately; finite total 999 rejected; valid total 10 accepted; ordered p28 cancellation `1e28 + 1 + 1 - 1e28` accepts 0 and rejects 2. Every rejection uses the expected exact exception class.
- **44 AC-04 factory outputs:** all 11 locked ROUND_TRIP_ROWS across the four configurations. This includes the required totals 1.68760, 1.48760, 0.68 and 3.37520, selected/unused None, selected zero, both sides and stress. **8 R checks** preserve 0.067504 and 0.135008.
- **240 calls** in total preserve caller identity/settings/flags/traps, including stress-model creation. The locked AC-04 test additionally covers default sides and its synthetic ordered-total factory fixture.
- The added unit regression covers total/spread with sNaN/NaN/+Infinity and clean flags. Its narrower coverage is supplemented by the explicit two-trap/all-field/full-state probe here.
- No finite-valid input behavior changes in the fix. No new dependency, lockfile, core/timebase, CI, hook or control change appears in `493202c..HEAD`.

### Locked tests and red flags

`git diff dced669 HEAD -- tests/acceptance tests/golden tests/architecture` is **empty**, independently asserted by Appendix A. Starting and pre-report working-tree/index checks are clean; no test was edited by this review.

`bash scripts/controls/red-flags.sh origin/main` exits 0, **Pattern groups with hits: 2**:

- **Type checks disabled:** seven existing deliberate negative-input/immutability annotations in unit tests plus five documentation lines quoting the pattern. Runtime assertions and exceptions remain active; none was added by the F4 fix.
- **Lint disabled:** three documentation lines (PROGRESS, evidence and tests review) quote the scan pattern; no production lint suppression.
- Secret, secret-like value, order/account mutation, destructive/bypass and placeholder/mock groups: **empty**.
- Deleted/renamed tests: none. Untracked at scan time: none (this report was written afterward).
- Control paths listed: inherited AGENTS.md/CLAUDE.md and the three locked acceptance/golden/architecture files. This scan does not grant approval. The r2 standalone locked-path gate failure is historical and is not claimed resolved; no gate, label or CI action was performed here.

Failure-pattern review was limited to the fix: F01/F17 (scope and evidence), F02 (test diff), F03/F08 (real computation and error path), F04/F05/F18 (unchanged dependencies plus installed API docs), F06/F07/F15 (small in-scope change), F09–F12 (no external/credential/destructive path), F13/F14 (fresh bounded re-check), F16 (independent before/after probe and static helper). The fix adds no shared mutable state, external handle, I/O, order, retry, clock or data-ingestion path; caller-context isolation is exercised directly.

### Checks run

All times are 2026-10-22 Asia/Bangkok (+07:00). HEAD stayed `2a1b2a1`. Python used `PYTHONDONTWRITEBYTECODE=1`; stdin probes also used `-B`, and pytest's cache provider was disabled. Bash commands ran through `C:/Program Files/Git/bin/bash.exe` from the repository root.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| Branch/status/head/fix-log and `git diff 493202c HEAD -- src/sochron/costs tests` inspection | PASS: clean start; expected task branch; only charges validation and one unit regression change in runtime/test delta | 2a1b2a1 / cec0f4b | 06:28–06:32 |
| `uv run --offline pytest tests -q -p no:cacheprovider` | PASS, exit 0: **45 passed in 0.09s**, 0 skipped | 2a1b2a1 | 06:30:49–06:30:50 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; two hit groups explained above; required secret/order groups empty | 2a1b2a1 | 06:30:49–06:30:51 |
| `git diff dced669 HEAD -- tests/acceptance tests/golden tests/architecture` | PASS: empty output, exit 0; also asserted by Appendix A | dced669 / 2a1b2a1 | 06:30:49; 06:32:04 |
| `git diff --check 493202c HEAD` | PASS, exit 0, no output | 2a1b2a1 | 06:30:49 |
| `uv run --offline --no-sync python -B -` (installed version and stdlib docstrings) | PASS: Python 3.12.15, pytest 9.1.1; is_finite/localcontext/getcontext docs inspected | 2a1b2a1 | 06:31 |
| `uv run --offline --no-sync python -B -` (Appendix A) | PASS, exit 0: old defect reproduced; HEAD two-trap probe and 240 context-preserving calls pass | 493202c / 2a1b2a1 | 06:32:03–06:32:04 |
| `git diff 493202c HEAD -- pyproject.toml uv.lock .github .claude scripts/controls src/sochron/core src/sochron/timebase` | PASS: empty | 2a1b2a1 | 06:32:04 |
| `rg` file discovery | BLOCKED: “The term 'rg' is not recognized”; used git ls-files and PowerShell Select-String/Get-Content; no configuration change | 2a1b2a1 | 06:28 |
| `uv run --offline --no-sync python -B -` (report structure/appendix syntax and Git scope assertions) | PASS: seven AC rows; Appendix A compiles; HEAD unchanged; no tracked/staged changes; only `?? docs/reviews/CORE-002-r3.md` | 2a1b2a1 | 06:33:38–06:33:39 |

## Not checked (and why)

- No new full review of F1/F3, inherited chore changes or unrelated module behavior. Existing tests ran; r2's 2,000-case Fraction oracle and hash reconciliation were not repeated. This round is explicitly limited to F4 and fix-induced effects.
- No exhaustive arbitrary-exponent/performance, custom Decimal subclass or hostile reflection testing; no concurrency stress run. These are outside this targeted fix.
- No standalone locked-path/control test rerun, CI, owner demo, PR label, approval, merge or deployment. Local passing checks do not advance the owner/CI-controlled delivery state.
- No broker/account connection, orders, market data, backtest, holdout or historical-cost validity check.
- Interactive `/review` unavailable in this headless interface as noted above.

Delivery: implementation locally verified for this re-review; task merge/deployment not established. Next action is implementer handoff of this unstaged report and the existing owner/CI process, with no open code finding from this round.

## Appendix A — rerunnable F4/F2/AC-04 probe

From the repository root, pass this script on stdin to `uv run --offline --no-sync python -B -` with `PYTHONDONTWRITEBYTECODE=1`. It reads committed old source and locked fixtures, writes no file and performs no Git mutation.

```python
import sys
import subprocess
import types
from pathlib import Path
from runpy import run_path
from decimal import Decimal as D, InvalidOperation, Inexact, Rounded, ROUND_UP
from decimal import getcontext, localcontext
sys.path.insert(0, "src")
import sochron.costs as c

# Re-run the exact r2 Appendix B payload before and after the fix, in memory.
old = types.ModuleType("sochron.costs._r2charges")
sys.modules[old.__name__] = old
source = subprocess.check_output(
    ["git", "show", "493202c:src/sochron/costs/charges.py"], text=True)
exec(compile(source, "493202c:charges.py", "exec"), old.__dict__)
for label, cls in (("493202c", old.CostBreakdown), ("HEAD", c.CostBreakdown)):
    for trap in (True, False):
        with localcontext() as caller:
            caller.clear_flags()
            caller.traps[InvalidOperation] = trap
            before = repr(caller)
            try:
                cls(D("1"), D("2"), D("3"), D("4"), D("sNaN"), D("1"))
            except Exception as error:
                result = (type(error).__name__, caller.flags[InvalidOperation],
                          repr(caller) == before)
                print(label, trap, *result)
                expected = (("InvalidOperation" if trap else "CostsError"), True, False)
                if label == "HEAD":
                    expected = ("CostsError", False, True)
                assert result == expected
            else:
                raise AssertionError("sNaN total was accepted")

names = ("spread", "commission", "slippage", "swap", "total", "stress_factor")
valid = tuple(map(D, ("1", "2", "3", "4", "10", "1")))
def snapshot(ctx):
    return (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals, ctx.clamp,
            dict(ctx.flags), dict(ctx.traps))

calls = 0
def checked(caller, action, expected_error=None):
    global calls
    before = snapshot(caller)
    assert getcontext() is caller
    value = None
    try:
        value = action()
    except Exception as error:
        assert type(error) is expected_error, (type(error), expected_error)
    else:
        assert expected_error is None, expected_error
    finally:
        assert getcontext() is caller, "caller context identity changed"
        assert snapshot(caller) == before, "caller context state changed"
    calls += 1
    return value

rows = run_path("tests/golden/CORE-002/costs_cases.py")["ROUND_TRIP_ROWS"]
nonfinite = f2 = factory = early = ratio = 0
for trap in (True, False):
    for preset_flags in (False, True):
        with localcontext() as caller:
            caller.prec, caller.rounding = 4, ROUND_UP
            caller.Emin, caller.Emax, caller.capitals, caller.clamp = -9, 9, 0, 1
            for signal in caller.traps:
                caller.traps[signal] = True
            caller.traps[InvalidOperation] = trap
            caller.clear_flags()
            if preset_flags:
                caller.flags[Inexact] = caller.flags[Rounded] = True
            for index in range(len(names)):
                for token in ("sNaN", "NaN", "Infinity", "-Infinity"):
                    fields = list(valid)
                    fields[index] = D(token)
                    checked(caller, lambda: c.CostBreakdown(*fields), c.CostsError)
                    nonfinite += 1
                fields = list(valid)
                fields[index] = 1
                checked(caller, lambda: c.CostBreakdown(*fields), TypeError)
                f2 += 1
            checked(caller, lambda: c.CostBreakdown(1, 2, 3, 4, 10, 1), TypeError)
            checked(caller, lambda: c.CostBreakdown(
                D("1"), D("2"), D("3"), D("4"), D("999"), D("1")), c.CostsError)
            assert checked(caller, lambda: c.CostBreakdown(*valid)).total == D("10")
            ordered = (D("1e28"), D("1"), D("1"), D("-1e28"), D("0"), D("1"))
            assert checked(caller, lambda: c.CostBreakdown(*ordered)).total == D("0")
            checked(caller, lambda: c.CostBreakdown(
                *ordered[:4], D("2"), D("1")), c.CostsError)
            f2 += 5
            # A bad last field must be rejected before an overflowing component sum.
            checked(caller, lambda: c.CostBreakdown(
                D("9e999999"), D("9e999999"), D("0"), D("0"),
                D("0"), D("sNaN")), c.CostsError)
            early += 1
            for side, lots, entry, exit_, nights, triple, sides, factor, expected in rows:
                model = checked(caller, lambda: c.stress(c.H001_COSTS, D(factor)))
                result = checked(caller, lambda: c.round_trip_cost(
                    side, D(lots), entry, exit_, nights, triple, model, sides))
                assert tuple(getattr(result, name) for name in names) == tuple(map(D, expected))
                factory += 1
            for money, expected in (("1.68760", "0.067504"), ("3.37520", "0.135008")):
                assert checked(caller, lambda: c.r_multiple(D(money), D("25"))) == D(expected)
                ratio += 1
print(f"PASS: {nonfinite} non-finite rejections; {early} pre-arithmetic rejections; "
      f"{f2} F2 cases; {factory} AC-04 factory rows; {ratio} AC-04 R checks; "
      f"{calls} calls preserve caller identity/settings/flags/traps")
assert not subprocess.check_output([
    "git", "diff", "dced669", "HEAD", "--",
    "tests/acceptance", "tests/golden", "tests/architecture"])
print("PASS: locked-test diff dced669..HEAD empty")
```
