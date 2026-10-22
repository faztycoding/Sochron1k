# Security pre-review CORE-003 round 2 · base 737632b · head 60dfbfd, re-checked on 4fd4a60 · reviewer Claude Code security-reviewer subagent (read-only)

Saved verbatim by the implementer from the subagent's final message (2026-10-22 10:2x); only HTML entities from the transport were restored to `<` and `>`.

This is a pre-review only. It does not replace the Codex cross-agent review that a High-tier task requires. The reviewer edited, staged and committed nothing, and wrote no file. All probes ran in memory: Python scripts piped on stdin to `PYTHONPATH=src uv run --offline --no-sync python -B -` from the repo root. Nothing connected to a terminal, a broker or the network, and no credential store was read. **This review does not show that the module is secure.** It lists what was attacked, what held, and what was not checked. All times are 2026-10-22, +07:00.

**The review target moved during the review.** Commits `8d4e30b`, `1c804a6`, `0bf8311`, `b959fea`, `5d939a3` and `4fd4a60` landed between 10:17:51 and 10:20:52. They hold the Codex implementation review r1 fixes and contract v1.4. The early probes ran on the `60dfbfd` code. At 10:21–10:23 every new-hunt probe was re-run on `4fd4a60`. Source code is identical between `b959fea` and `4fd4a60` (`git diff --stat b959fea..HEAD -- src tests` is empty). Line numbers below refer to `4fd4a60`.

**Verdict:** no Critical or High finding.
- **Round 1:** F1, F2, F5, F6 and F8 are closed. F4 is closed for direct mutation, but F9 below bypasses it. F3 is closed for every round-1 input; F10 and F11 are what remains of it. F7 stays open by owner decision as an E1 obligation.
- **New:** five Low findings. F9–F11 are confirmed code issues. F12 and F13 are contract questions.
- **Overlap with Codex r1:** three of my probes on `60dfbfd` independently reproduced Codex r1 F1–F3. All three are fixed at HEAD; see "Overlap with Codex review r1".
- **Honest-typed inputs found nothing.** A differential oracle over 2 × 20,000 gate cases and 5,000 stop changes found no violation.

## Assets, identities, trust boundary
Unchanged from round 1. `sochron.risk` has no I/O, so every input comes from the in-process caller (R1, E1, and in future a journal or config parser). The new attack surfaces in v1.3/v1.4 are:
- The size bound, and the cost of checking it.
- The use-time revalidation of request, state, policy and model, including the provenance container it reads.
- `day` and `stale_state`.
- `grid_lots` / `exact_reduce`.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F9 | Low | confirmed | `policy.py:184-186` (`dict(policy.provenance)` at every use via `validate_policy` `:199-202`), reached from `gate.py:135` after `gate.py:132`; `gate.py:140` re-reads `state.policy` after validation; `halts.py:36` | Probe on 4fd4a60, 10:21:34. Wrong-side stop: honest call gives `('stop_loss_wrong_side',)`; the hooked call gives `GateDecision(allowed=True, reasons=())` and `request.side` is now `'buy'`. Policy swap: `risk_per_trade=5` (outside (0,1)) allows 41.66 lots. Lots → NaN: plain `ValueError` (not RiskError) | A Mapping planted in `policy.provenance` with `object.__setattr__` after construction. Its `keys()` runs caller code mid-validation | Defeats the F4 / v1.4 "revalidate at use" control. Request fields can change after they were checked, and an unvalidated policy can be swapped in. Gate allows a wrong-side stop, and about 49,992 USD of risk on 10,000 equity | Make use-time validation free of caller code (options below) | Negative test below |
| F10 | Low | confirmed | `sizing.py:101` and `gate.py:164` (`steps * step`: Fraction products → `math.gcd`); `sizing.py:112` (`Decimal(steps)`, quadratic import); claim at `policy.py:62-63` | 4fd4a60, 10:21:50–10:23:02: `check_entry` 43.3 s (32.5 s on 60dfbfd) and `size_position` 26.9 s, then RiskError. Profile at 4×10⁵: `math.gcd` is 3.74 of 4.50 s | In-bound model `volume_step = volume_min = 1E-1100000`, `volume_max = 1E+1100000`, equity `1E+1100000` (2.0 s with equity 10000) | The gate still blocks the calling thread for tens of seconds on values the bound accepts. That includes SL management in E1. The comment "the gate always answers fast" is false. Contract `:123` exempts in-bound input from the 1 s rule, so this is what remains of F3, not a contract breach | Owner: bound the model grid. Or the implementer: avoid gcd and int→Decimal conversion of huge step counts | Timed in-bound worst case < 1 s, or refused fast |
| F11 | Low | confirmed | `policy.py:72` (`len(value.as_tuple().digits)`) | Pre-built `Decimal("7"*200_000_000)` equity: `BadEquity` after 1.195 s (60dfbfd) and 1.116 s with a 1,895 MiB peak working set (4fd4a60). Linear: 10⁸ digits 0.546 s / 956 MiB peak | A pre-built Decimal with ≥ 2×10⁸ coefficient digits, e.g. parsed from a 200 MB text field | Breaks contract `:123`: every rejection beyond the bound must take < 1.000 s on this reference machine (Windows 11, CPython 3.12.15, uv). Plus a ~9-byte-per-digit memory spike. Locked rows use only 1,001-digit / 1E±1100001 edges, so the suite does not see it | Count digits without building a Python tuple: check `adjusted()` first, then a C-level test such as `Context(prec=1000, Emax=MAX_EMAX, Emin=MIN_EMIN, traps=[Rounded]).plus(value)` → `Rounded` means more than 1,000 digits. That primitive took 0.023 s at 2×10⁸ digits; not tried inside the module | Negative test below |
| F12 | Low | question (contract gap) | `sizing.py:48` (SizeDecision bound) applied to `grid_lots` output `sizing.py:112-114` | A valid CostModel with a 1,000-digit `volume_step = 1.000…0001` and equity `1E+8`: `size_position` raises `RiskError("lots is outside the supported size…")`, while `check_entry` on the same inputs with lots = 9 × step returns `allowed=True`. Same for step `1E-100000`, stop distance 7 | In-domain model and equity whose sized lots need more than 1,000 significant digits | Not a bypass: gate-allowed lots are ≤ exact sizing and fit the request bound. But the two public functions disagree, R1 cannot size on such a model, and the contract lists no such `size_position` error | Owner: either add "sized lots outside the bound → RiskError" to the table, or bound the model grid (shared with F10) so it cannot happen | Per decision |
| F13 | Low | question (E1 obligation) | `halts.py:58-64` (`start_experiment`), `:87-98` (`restart_experiment`), `:75-80` (rollover baseline); contract `:84`, `:193-199` | Honest start 10000, equity 9000 → `('daily_halt', 'experiment_halt')`. Start at equity 1 → `allowed=True` at 9000. Restart at 0.01 → `allowed=True` at 5000 the next day | A baseline that is too low at start, restart, or the first value of a Thai day: wrong account field (e.g. free margin), unit or parse error | Halts silently weakened or disabled for the run, while sizing still follows current equity. Not covered by L1–L4 | E1 obligation L5 (below). Optionally the owner decides on a plausibility check of current equity against baseline | E1-level test |

### F9: use-time revalidation runs caller code
Order in `check_entry`: `validate_request` (`gate.py:132`), then `validate_state` (`:135`). `validate_state` calls `validate_policy`, and `_check_policy` reads the provenance Mapping last (`policy.py:186`), after it has already checked the fractions, count and allowlist. Any Mapping code runs at that point. It can:
- change request fields that were already checked;
- change policy fields that `_check_policy` just checked;
- point `state.policy` at another object, which `gate.py:140` then uses without validation.

Construction always stores a `MappingProxyType` of a plain dict, so this needs `object.__setattr__` on a frozen RiskPolicy, the same precondition class as round-1 F4 and L2. Wrapping the hook in `MappingProxyType` does not help: the proxy forwards `keys()` to the planted Mapping.

A hooked restart by `"claude"` also succeeded, because the hook appended to `halt_clearers`. That adds nothing beyond L1 (C5 in round 1).

Severity is Low, to match round-1 F4. Codex r1 rated the analogous model-field mutation Medium, so the owner may raise it. Codex r1 saw this surface but did not count it ("forcibly replacing an already-created policy's provenance Mapping is not used to reopen the fixed constructor-snapshot finding"). The effect shown here goes beyond F5: it defeats use-time validation of the request.

**Fix options** (any one closes the shown paths):
- (a) In `_check_policy`, read provenance **first**, so later checks see any callback mutation. In `check_entry`, validate state, policy and model **before** the request. Bind `policy = state.policy` once **before** validating and use only that local.
- (b) At use, skip re-reading provenance (no decision reads it). This needs one contract sentence, because v1.4 says to re-check every field.

**Negative test:**
```python
class Hook(Mapping):
    def __init__(self, good, action): self.good, self.action = good, action
    def __getitem__(self, k): return self.good[k]
    def __iter__(self): return iter(self.good)
    def __len__(self): return len(self.good)
    def keys(self): self.action(); return self.good.keys()

state = start_experiment(Decimal("10000"), DAY, replace(H001_RISK), "owner", "x")
req = EntryRequest("long", Decimal("0.02"), Decimal("4012.90"), Decimal("4024.90"), 0)  # wrong side
object.__setattr__(state.policy, "provenance",
                   Hook(dict(H001_RISK.provenance), lambda: object.__setattr__(req, "side", "buy")))
try:
    decision = check_entry(req, Decimal("10000"), DAY, state, H001_COSTS)
except (RiskError, TypeError):
    pass
else:
    assert not decision.allowed
# Same for a hook that swaps state.policy to one with risk_per_trade=Decimal("5")
# (lots 41.66 must not be allowed), and for a hook that sets req.lots to NaN
# (must raise RiskError, not ValueError).
```

### F10: in-bound worst case is still slow
- **Cause.** `steps` is the exact floor of R/rpl/step. With step 1E-1100000 it has 1.1–2.2M digits.
  - `steps * step` builds a Fraction, which runs `gcd(steps, 10**1100000)`, quadratic in CPython.
  - `size_position` then runs `Decimal(steps)`, also quadratic: 1.6 s at 4×10⁵ digits, ×4 per doubling.
- **Reachability.** Same as round-1 F3: MT5 floats cannot produce such fields. Text parsed from a journal or config can.
- **Fix options:**
  - (a) Owner: add a model-grid bound, e.g. `volume_max / volume_step` ≤ 10¹², or a much tighter `|adjusted|` for the four model fields. The contract's display examples (`1E-1000000`) concern R, not the model. The locked model rows only test rejection at 1E±1100001, which a tighter bound still rejects.
  - (b) Implementation: compare with integer cross-multiplication instead of Fraction products, and build lots by exact Decimal integer division instead of `Decimal(int)`.
- **Negative test.** Run it in a child process with a hard kill, because a GIL-holding gcd cannot be interrupted (tests-r2 F1):
```python
m = replace(H001_COSTS, volume_step=D("1E-1100000"), volume_min=D("1E-1100000"), volume_max=D("1E+1100000"))
s = start_experiment(D("1E+1100000"), DAY, H001_RISK, "owner", "x")
# check_entry(EntryRequest("long", D("1E+100"), D("4007"), D("4000"), 0), D("1E+1100000"), DAY, s, m)
# returns or raises RiskError in < 1 s; same for size_position(D("10000"), D("7"), m, H001_RISK)
```

### F11: the bound check itself is linear
**Negative test:**
```python
v = Decimal("7" * 200_000_000)  # built before timing, per contract :123
t = perf_counter()
with pytest.raises(BadEquity):
    size_position(v, Decimal("12"), H001_COSTS, H001_RISK)
assert perf_counter() - t < 1.0
```

### F13: E1 obligation L5 (proposed)
- `start_experiment`, `restart_experiment` and the first `update_equity` of each Thai day take equity from the MT5 account's **equity** field, read at that moment.
- The raw value is journaled.
- Any mismatch or unknown halts.
- The owner decides whether `sochron.risk` should also refuse a current-equity/baseline ratio outside a plausible band. AGENTS.md treats such jumps as data defects to report.

**Negative test (E1):** a start whose equity differs from the terminal's account equity is refused.

## Round-1 findings: status

| R1 ID | Status | My probe |
|---|---|---|
| F1 | **closed** | B1–B11 (Decimal, str, tuple, date and int subclasses; subclass CostModel, RiskPolicy and Provenance; subclass policy field set by mutation) → TypeError or BadPolicy before any decision method runs |
| F2 | **closed** | `volume_max=1E+5000`, equity `1E+5010` → `SizeDecision(lots=1E+5000, …, 'capped_at_volume_max')`; the gate allows the same inputs. The related int→str echo was Codex r1 F3, now fixed |
| F3 | **partly open** | All six round-1 inputs are now rejected in ≤ 0.011 s (1E+10000000, 1E-10000000, 1E-999999999, 300k and 2M digits). The zero exemption is fixed (Codex r1 F2). What remains is F10 (in-bound slowness) and F11 (rejection of ≥ 2×10⁸ digits > 1 s) |
| F4 | **closed for direct mutation; bypassable via F9** | C1–C4 replay: `side='buy'` → RiskError; exposures −5 → RiskError; lots NaN → RiskError; entry Infinity → BadStop; baseline NaN or −1 → BadEquity; str day / int latch → TypeError; policy fields → BadPolicy; model domain → RiskError at HEAD |
| F5 | **closed** | A Mapping that flips values after 5 reads: the stored proxy holds 5 exact Provenance values and `unknowns()` is stable |
| F6 | **closed** | A stale state at 10020 on the next day → `('stale_state',)`. A rolled state → `('daily_halt',)`. A future-dated state checked on today → TimeReversal. Still depends on E1 passing the true day (contract `:199`) |
| F7 | **open by owner decision (E1 obligation `:194`)** | A same-day `start_experiment` at 9925 still gives `allowed=True` |
| F8 | **closed (contract wording `:155`)** | A forged `HaltState(...)` and `replace(..., daily_halted=False)` still allow; that is expected (L2) |

## Overlap with Codex review r1 (no new IDs)
| Codex r1 | My probe on 60dfbfd | Fixed in | Re-check on 4fd4a60 (10:21) |
|---|---|---|---|
| F1 model domain | Mutated `volume_step=-0.01` → gate allows 200 lots (exact risk 240,000 USD against a 25 USD budget); `size_position` says `capped_at_volume_max` with actual_risk 240000 > risk_money 25. Step 0 or contract_size 0 → ZeroDivisionError | `1c804a6` | RiskError for step −0.01, step 0, contract_size 0, volume_min −5 |
| F2 zero budget | `cost_per_lot=0E-999999999` (in-domain) → 0.70 s, 1,222 MiB peak working set. `0E-1000000000000` and `0E-999999999999999999` → MemoryError (not RiskError) | `0bf8311` | 0.000 s, 17 MiB, lots 0.02 for `0E-1000000000000`, `0E-999999999`, `-0E-999999999999999999`, `0E+999999999` |
| F3 int echo | `open_exposures=-10**5000` and `max_open_exposures=-10**5000` → plain ValueError | `b959fea` | RiskError and BadPolicy |

## OWASP Agentic mapping
- **ASI02/ASI10:** agent-written E1 code could plant a hook or start with a wrong baseline (F9, F13).
- **ASI06:** journal or config text values (F10, F11, F12, F13).
- **ASI08:** a gate that blocks or exhausts memory (F10, F11).
- **ASI09:** the request is changed under a call that looks compliant (F9).
- **ASI03:** identity is name-only, unchanged (L1).
- **ASI04:** no new dependency. **ASI05:** no eval or pickle. **ASI01/ASI07:** not applicable.

## AC status (pre-review view, code of 4fd4a60)
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| 01 | PASS (F12 open as a question) | Suite green. The oracle matches sizing and gate. F12: `size_position` raises for some in-domain models |
| 02–03 | PASS | Suite green; latch, rollover and restart replays above |
| 04 | PASS for honest types | 0 oracle violations. F9 needs `object.__setattr__` |
| 05 | PASS | 5,000 stop-change oracle cases, 0 violations |
| 06 | FAIL for one input class (F11) | Otherwise every type, domain and size probe raised the specified error |
| 07 | PASS | `PYTHONDONTWRITEBYTECODE=1 uv run --offline pytest tests -q -p no:cacheprovider` → 654 passed in 2.71 s, 10:20:21–10:20:24, code identical to 4fd4a60. red-flags exit 0. The import grep is clean |

## Checked, nothing found (and how)
- **Differential oracle (seed 20261022), independent Fraction predicates.** It ran twice:
  - On 60dfbfd: 20,000 gate cases, 860 allowed, 6,666 stale-day, 4,971 at a threshold edge, 1,513 at exactly the sized lots.
  - On 4fd4a60 (10:23:21), with `0E-999999999` budgets mixed in: 20,000 cases, 905 allowed.

  Both runs: 0 violations, with reason sets exactly equal. No allowed decision occurred on another day, with a latch set, at or beyond a threshold, with a missing, wrong-side or equal stop, above `lots × rpl ≤ R`, off the grid, or at or above max exposures. 5,000 stop changes: 0 violations.
- **Validation before any reason.** Read `check_entry`, `check_stop_change`, `update_equity`, `restart_experiment` and `start_experiment`. Every argument and field, including nested policy and model, is validated before `TimeReversal` or any reason is produced. Halts do not skip validation. The only exception is the callback in F9.
- **Nothing reaches Fraction or display before `finite_bounded`.** All conversions follow validation. Zeros reach `Fraction` only as (0, 1): `check_entry` with budget `0E-999999999` took 0.0001 s.
- **`grid_lots` / `exact_reduce`.** `normalize()` runs in `_EXACT` with Inexact trapped, so the value never changes. Positive lots lie between `volume_min` and `volume_max`, so the adjusted bound always holds; only the digit bound can fail (F12).
- **Hostile caller context.** prec=1, ROUND_UP, Emax=1, Emin=−1, clamp=1, all traps on. Eight calls covering H001 sizing, the 1E+5000 cap, a zero budget, 1,000-digit equity, a gate on 1E+5000 lots, a gate on a 1,000-digit step, update and restart gave 0 mismatches. No flags were set and the context was unchanged.
- **`validate_policy` cost on hostile but valid-typed values.** It is linear:
  - 2M clearers: `check_entry` 0.26 s, `update_equity` 0.51 s.
  - A 200 MB clearer name: 0.000 s on reuse (the hash is cached).
  - `max_open_exposures = 10**100000`: 0.004 s.

  Observation, not a finding: the allowlist has no length bound. Error messages echo caller strings through `repr` (`authorized_by`, `side`); repr escapes newlines, so log lines cannot be injected, but a 200 MB name yields a 200 MB message (E1 log hygiene).
- **Imports and I/O.** A grep of `src/sochron/risk` finds only stdlib, `sochron.costs` and relative imports. There is no open, print, time, random, os, sys, subprocess, socket, eval, exec, pickle, importlib or float in code; the only hits are in a docstring.
- **red-flags.sh main.** 10:20:15, exit 0. Two groups, as in round 1: `type: ignore` in two negative unit tests plus prose, and lint words in prose. The secret and order/account groups are empty.
- **check-locked-paths.mjs main.** 10:23:32: the same 7 inherited control changes, which need the owner's label. Since 737632b the only locked-path delta is the Codex r2 test patch (`81322d9`).

## Not checked (and why)
- **Values not run, to protect the owner's machine:**
  - `size_position` on the ~2.2M-digit `steps` case; extrapolated to be slower than 26.9 s.
  - Coefficients above 2×10⁸ digits.
  - `0E-N` with 10⁹ < N < 10¹² on 60dfbfd, which would allocate several GB. It is fixed now anyway.
- **Candidate fixes.** The F11 primitive was timed only on its own. The F9 and F10 fixes were not tried in memory.
- **Locked tests.** Whether a tighter model bound for F10/F12 conflicts with locked tests was checked only by reading `_NUMERIC_SLOTS` and `BOUND_*`. The v1.4 `faulthandler` watchdog (tests-r2 F1) is not in the tests yet and was not exercised.
- **Out of scope:** threads and concurrency, Linux and CI, the owner demo, E1, the journal and MT5. The `sochron.costs` Provenance itself (a str-subclass `status` could hide an assumed value from `unknowns()`) is out of scope, as noted in round 1.
- **Timestamps.** Probes before 10:18 ran on the 60dfbfd code, as their outputs show; their exact times were not recorded. Contract v1.4 was read only as a diff.
