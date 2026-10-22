# Security pre-review CORE-003 round 1 · base main · head ab23325 · reviewer Claude Code security-reviewer subagent (read-only)

Saved verbatim by the implementer session from the subagent's final message (2026-10-22 ~08:50 +07). This is a pre-review only. It does not replace the Codex cross-agent review that a High-tier task requires. The reviewer edited, staged and committed nothing. Probes ran in memory from `PYTHONPATH=src uv run --offline --no-sync python -B`; their scripts are in the implementer's session scratchpad (`p1_honest.py` … `p9_fixcheck.py`). Nothing connected to a terminal, broker or network, and no credential store was read. **This review does not show that the module is secure.** It lists what was attacked, what held, and what was out of scope.

**Verdict:** no Critical or High finding.
- **F1–F5 are code defects**, one Medium and four Low. F1, F2, F4 and F5 can be fixed inside the current contract. F3's fix needs a new domain bound in the contract, so it goes to the owner.
- **F6–F8 are contract gaps.** Two Medium and one Low, all owner decisions.
- **L1–L4 are design limits** the contract already gives to E1. Each has a concrete abuse path so the E1 contract can carry it.
- **Honest-typed inputs found nothing.** A differential oracle over 20,000 such inputs found no violation of sizing, grid, threshold or exposure rules.

## Assets, identities, trust boundary
- **Assets:** the halt latches (`HaltState`), the bound policy (limits and `halt_clearers`), the sizing decision, and in E1 the order path and journal.
- **Identities:** the owner (the only legitimate clearer); Claude and Codex (authors of R1/E1 caller code); the E1 process; the MT5 terminal (source of equity, prices, positions and SL).
- **Boundary:** `sochron.risk` has no I/O, so every input comes from the in-process caller. The gate is only as strong as two things: E1 tying the inputs to MT5's values, and E1 sending exactly what the gate allowed.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `policy.py:43,47,61,67,133,136`; `halts.py:46,48,50,52`; `gate.py:39,127,137`; `sizing.py:90` | Probe p2, outputs below | A subclass of Decimal, str, tuple, date or int (or a subclass `volume_step` in a CostModel) | Gate allows 1.00 lots that print as `Decimal('1.00')` while it decided on 0.01. A non-listed name clears a halt against `H001_RISK`. A policy equal to `H001_RISK` lets anyone clear. A same-day call clears the daily halt. `max_exposure` is skipped. `size_position` reports 2 lots after deciding 0.02 | Exact-type checks (`type(v) is Decimal/int/str/tuple/date`) at those lines, plus exact-Decimal checks on the model fields risk reads | Same suite with the candidate checks patched in memory: 68 passed (p9). Attack replay BLOCKED (see Not checked) |
| F2 | Low | confirmed | `sizing.py:91-92` | p6: `ValueError: Exceeds the limit (4300 digits)`, not a RiskError, while `check_entry` allows the same inputs | `volume_max=1E+5000` with equity `1E+5010`, or a `volume_step` with more than 4,300 significant digits | A documented input raises an exception outside TypeError/RiskError | `with localcontext(_EXACT): return Decimal(steps) * step`. `Decimal(10**5000)` works because int→Decimal has no digit limit | Suite 68 passed with this patch (p9) |
| F3 | Low | confirmed | `policy.py:67` (`Fraction(value)`), reached from `sizing.py:108`, `gate.py:123-144`, `halts.py:75-80` | p5/p7/p8 timings below | Finite Decimals with huge exponents or long coefficients, e.g. from journal or config text | Gate blocks for seconds to forever before `display()` can raise. At the extreme, MemoryError | Owner/contract decision: a domain bound on `adjusted()` and digit count, checked before any Fraction conversion | Negative test below |
| F4 | Low | confirmed | `gate.py:114-117,127,129,137`; `halts.py:67,87` | p3: C1–C4 | `object.__setattr__` on a validated `EntryRequest` or `HaltState` | `side="buy"` skips the wrong-side check and is allowed. NaN lots or baseline raises a plain ValueError; Infinity raises OverflowError | Re-validate request and state fields at use, with shared validators | Negative test below |
| F5 | Low | confirmed | `policy.py:144-155` | p6 E3: the stored value is `'not a Provenance'`; `unknowns()` then raises AttributeError | A Mapping that changes between its three iterations | Unvalidated provenance is stored; an exception outside TypeError/RiskError | Take `dict(self.provenance)` once (after the Mapping check), validate it, store that copy | Suite 68 passed (p9) |
| F6 | Medium | question (contract gap) | `gate.py:106-145` (no `day` argument); contract `:100` | p1: A5, A6 | A state not rolled to today, or a state dated in the future | Entry allowed at or beyond today's daily threshold | Owner decision, options below | Negative test below |
| F7 | Medium | question (contract gap) | `halts.py:56-62` | p1: A4 | `start_experiment` on the same Thai day as a daily halt | The same authorized name gets a fresh daily budget that `restart_experiment` correctly refuses. The owner's same-day rule (decision 1) is sidestepped | Owner decision, options below | E1-level test |
| F8 | Low | question (contract wording) | contract `:147`, `:149` vs `HaltState`/`RiskPolicy` being public | p1: A1–A3; locked acceptance `:292`, `:302` use `replace(state, …)` | `dataclasses.replace` or the `HaltState(...)` constructor | The invariant "the halt can be cleared only by `restart_experiment`" is true only for callers that never construct or replace state | Correct the contract wording; E1 architecture test (L2) | — |

### F1: subclasses get through `isinstance`; checks and decisions read different methods
Values are validated with `is_finite()`, `<=`, `in`, `strip()` and `==`. Decisions use `Fraction(value)`, which calls `value.as_integer_ratio()`. A subclass can answer the two differently. The contract already rejects the two subclasses it names (bool for int, datetime for date: contract `:36`, `:119-120`) and says "no automatic conversion". Rejecting all subclasses is consistent with that.

```python
class Lots(Decimal):
    def as_integer_ratio(self): return (1, 100)
req = EntryRequest("long", Lots("1.00"), D("4012.90"), D("4000.90"), 0)
check_entry(req, D("10000"), s0, H001_COSTS)
```
Output (p2):
```
B1 lots subclass: Decimal('1.00') 1.0 1.00 GateDecision(allowed=True, reasons=())
B2 str-subclass start by 'claude' -> HaltState
B2 restart by 'codex' -> False            # experiment_halted cleared
B3 policy == H001_RISK: True clearers repr: ('owner',)
B3 start by 'claude': True
B4 daily before/after same calendar day: True False 9925 GateDecision(allowed=True, reasons=())
B5 open_exposures=Count(7): GateDecision(allowed=True, reasons=())
B6 blank reason subclass: False           # started with a blank reason
B7 size_position lots with Step subclass: 2
```
- **Impact.** B1 is 50 times the sized 0.02 lots: a risk of 1,200 USD, or 12% of equity, while every log and journal shows `Decimal('1.00')` as approved. A human reviewer would see a compliant gate call (OWASP Agentic ASI09).
- **B3 defeats a natural E1 check.** A binding check such as `state.policy == H001_RISK` would pass.
- **What the subclass path adds.** Any in-process caller could skip the gate outright. The subclass path adds concealment, and it breaks the contract's own type rule.
- **Negative test** (unit; also a candidate for Codex to add):
```python
class Lots(Decimal):
    def as_integer_ratio(self): return (1, 100)
with pytest.raises(TypeError): EntryRequest("long", Lots("1.00"), Decimal("4012.90"), Decimal("4000.90"), 0)
class Name(str):
    def __eq__(self, other): return True
    __hash__ = str.__hash__
with pytest.raises(TypeError): start_experiment(Decimal("10000"), DAY, H001_RISK, Name("claude"), "x")
class Anyone(tuple):
    def __contains__(self, item): return True
with pytest.raises(TypeError): replace(H001_RISK, halt_clearers=Anyone(("owner",)))
class Day(date):
    def __eq__(self, other): return False
    __hash__ = date.__hash__
with pytest.raises(TypeError): update_equity(_start(), Decimal("9925"), Day(2026, 10, 22))
```

### F2: `grid_lots` is bound by Python's int↔str digit limit
`sys.get_int_max_str_digits()` is 4300. With `volume_max=Decimal("1E+5000")` (synthetic provenance) and equity `1E+5010`, `size_position` raises `ValueError` (`isinstance(e, RiskError)` is False). For the same inputs, `check_entry` returns `GateDecision(allowed=True, reasons=())`. The expected result is `SizeDecision(lots=1E+5000, reason="capped_at_volume_max")`, and every display value fits within CONTEXT's Emax.

**Negative test:** `assert size_position(D("1E+5010"), D("12"), big_max_model, H001_RISK).reason == "capped_at_volume_max"`.

### F3: decision cost has no bound
Measured (p5, p7, p8):

| Call | Input | Time | Result |
|---|---|---|---|
| `size_position` | equity `1E+10000000` | 5.17 s | then RiskError |
| `check_entry` | equity `1E+10000000` | 15.34 s | returns allowed |
| `check_entry` | lots `1E-10000000` | 5.10 s | — |
| `size_position` | equity `1E-999999999` | killed by a 60 s timeout (exit 124) | none |
| `check_entry` | equity with a 300,000-digit coefficient | 4.88 s | — |
| `size_position` | equity with a 2,000,000-digit coefficient | 71.77 s | — |

- **Cause.** `as_integer_ratio` builds `10**|exp|` and runs a gcd before any range check.
- **Reachability.** MT5 floats can't reach this: exponents stay within about ±324, with at most about 770 digits even for an exact float→Decimal. Text-parsed values can (journal restore, config, CSV).
- **Effect.** Fail-closed for that one entry, but it blocks the calling thread, including SL management in E1.
- **Fix.** A bound such as `abs(adjusted()) ≤ 1_100_000` and ≤ 1,000 coefficient digits, raised as the slot's RiskError subclass. The locked tests use exponents up to ±1,000,029 and literals of at most 37 characters, so they would stay valid. This is a new domain rule, so it needs a contract amendment.
- **Negative test:** `with pytest.raises(BadEquity): size_position(Decimal("1E-999999999"), Decimal("12"), H001_COSTS, H001_RISK)` finishes in under 1 s.

### F4: the gate trusts validation done at construction
Output (p3):
```
C1 honest wrong-side long: ('stop_loss_wrong_side',)
C1 side='buy' after construction: GateDecision(allowed=True, reasons=())
C2 open_exposures=-5: GateDecision(allowed=True, reasons=())
C3 lots NaN -> ValueError is RiskError: False
C3 entry_price Infinity -> OverflowError is RiskError: False
C4 day_start_equity NaN -> ValueError is RiskError: False
C4 day_start_equity -1 -> ('experiment_halt', 'lots_exceed_sized')   # daily check silently lost
```
Contract `:96` says to check the type and domain of every argument first. Setting the latch flags to False can't be prevented (that is L2). Domain re-validation is cheap.

**Negative test:** `object.__setattr__(r, "side", "buy")` → `pytest.raises(RiskError)` on `check_entry`. `object.__setattr__(state, "day_start_equity", Decimal("NaN"))` → `pytest.raises(BadEquity)`.

### F6: `check_entry` can't tell that the state is from another Thai day
Output (p1):
```
A6 rolled state gate @10020: ('daily_halt',)               # today's baseline 10100, loss 80 ≥ 75.75
A6 stale  state gate @10020: GateDecision(allowed=True, reasons=())
A5 daily-only halt cleared by tomorrow's date: True -> False GateDecision(allowed=True, reasons=())
A5 later honest date: TimeReversal
```
A missed rollover is an ordinary bug, which makes this the most likely real path to "entry at or beyond the daily threshold". A future date clears today's daily halt. After that, honest dates raise TimeReversal, which is fail-closed only if E1 halts on that error.

Options for the owner:
- **(a)** The E1 contract requires `update_equity(state, equity, bangkok_date(now))` immediately before every `check_entry`, with the same equity, plus a check that `state.day == today`.
- **(b)** Contract v1.3 adds `day: date` to `check_entry`. A day earlier than `state.day` raises `TimeReversal`; a day different from `state.day` is refused, for example with a new reason `"stale_state"`.

**Negative test for (b):** a stale state from day 22, checked on day 23 at equity 10020, is not allowed.

### F7: `start_experiment` resets the daily halt on the same Thai day
Output (p1):
```
A4 restart same day keeps daily: True ('daily_halt',)
A4 start_experiment same day daily: False GateDecision(allowed=True, reasons=())
```
Options for the owner:
- **(a)** Accept it, and record that a new experiment gets a new daily budget.
- **(b)** E1 refuses `start_experiment` while a journaled state exists for the same account and Thai day.

## Design limits already assigned to E1 (no ID; for the E1 contract)
- **L1 · The clearer's identity.** A name is not an identity. The allowlist is caller-supplied data: `restart_experiment(replace(halted, policy=loose_with_claude), …, "claude", "x")` cleared the halt (p1 A3b). In-process `object.__setattr__(H001_RISK, "halt_clearers", ("owner","claude"))` changes every state bound to `H001_RISK` (p3 C5). E1 needs an identity check, and the policy pinned by value or digest in the journal.
- **L2 · Persisting and forging `HaltState`.** `replace(halted, daily_halted=False, experiment_halted=False, …)` led to the gate returning `allowed=True` (A1). `HaltState(H001_RISK, DAY, 9800, 9800, False, False)` produced an allowed state (A2). `replace(halted, policy=loose)` with `risk_per_trade=0.5` allows 4.08 lots after losses, a martingale through state swap (A3, oracle 4.08). E1 needs journal restore as the only constructor, and an architecture test that forbids `HaltState(`, `replace(` on HaltState/RiskPolicy, and `object.__setattr__` outside `sochron.risk` and the journal module. Halt when the state is unknown.
- **L3 · Tying the gate result to the actual send.** The gate trusts `entry_price`: entry 4001.90 with SL 4000.90 allows 0.25 lots; a fill at 4012.90 risks 300 USD, 12 times the budget (A7). The gate trusts the model: `contract_size=1` allows 2.00 lots, a real risk of 2,400 USD (A8). `open_exposures` is caller-supplied, and `GateDecision(True, ())` can be constructed by anyone. E1 needs entry_price from the current tick on the order side, the model checked against `symbol_info`, exposures counted from MT5, and exactly the gated tuple sent.
- **L4 · Stop-change gate.** It trusts `current_stop`: a forged 3900 → 3950 is allowed (A9). E1 must read the current SL from the MT5 position.

## OWASP Agentic mapping
- ASI02/ASI10: agent-written E1 could call `start_experiment("owner")` or `replace(state)` (F7, F8, L1, L2).
- ASI03: name-only clearer; str-subclass equality (F1, L1).
- ASI06: journal-restored strings and state (F3, F6, L2).
- ASI08: a hanging gate or a stale state (F3, F6).
- ASI09: B1/B3 values look compliant while deciding otherwise (F1).
- ASI04: no new dependency. ASI05: no eval or pickle. ASI01/ASI07: not applicable; no AI reads external content in this module.

## AC status (pre-review view)
| AC | Status | Why |
|---|---|---|
| 01–06 | PASS | The suite runs green: 68 passed at 08:31:18 +07 on ab23325, Windows. F1/F4 show the AC-06 type and domain rules hold only for exact types and at construction. |
| 07 | PASS | The architecture test passes. Runtime import check: importing `sochron.risk` loads only stdlib, `sochron`, `sochron.costs.*` and `sochron.risk.*`. |

## Checked, nothing found (and how)
- **Imports and I/O.** Risk sources import only stdlib, `sochron.costs` and relative modules. Grep found no open, print, time, random, os, sys, subprocess, socket, eval, exec, pickle or importlib.
- **Differential oracle (p8, seed 20261022).** 20,000 honest-typed cases with varied grid, contract size, limits, multi-day history, sides, off-grid lots and budgets: 3,783 allowed, 0 violations. Checked rules: exact lots×(dist×size+cost) ≤ R, on grid and in range, no latch set, both thresholds strictly below, exposures below the maximum.
- **Special-value sweep (p7).** NaN, -NaN, sNaN, -sNaN, ±Infinity, 0, -0, -1, 1E-1000000, 1E+999999, float, bool, int, str and None in 16 slots. Only TypeError or RiskError subclasses came out. A datetime, str, None or int `day` raises TypeError.
- **Hostile caller context (p4).** prec=1, ROUND_UP, Emax=1, Emin=-1, clamp=1, all 9 signals trapped. Results matched the default context, no flags were set, and the context was unchanged.
- **Honest-typed latches.** No honest-typed path clears the experiment halt except `restart_experiment`. Restart refuses a non-halted state and unlisted names, and keeps the same-day daily halt and baseline. Thresholds are inclusive and exact.
- **No martingale through the public functions.** A looser `size_position` result is refused by the gate's own re-sizing (A3: 4.16 → `lots_exceed_sized`). Stop widening or removal is refused on both sides.
- **red-flags.sh (main).** Ran at 08:47:17 +07, exit 0. The hits were the same two inherited groups the evidence already explains, and `policy.py` was flagged by a name heuristic. The secret and order/account groups were empty.
- **check-locked-paths.mjs (main).** "FAIL: 7 control change(s) need owner approval", all inherited from the branch delta. The implementation commit touches no locked path: `git diff --stat 831fa60..ab23325` on the locked roots is empty.

## Not checked (and why)
- **Attack replay against the in-memory candidate fixes: BLOCKED.** The `guard-bash.mjs` hook refused the command because it redirected output to a path held in a variable. The reviewer did not retry it in another form, per CLAUDE.md. The only evidence for the fixes is the 68/68 suite run with them patched in.
- Exponents ≥ 1E+100000000 and coefficients ≥ 10⁷ digits were not run, to protect the machine's memory. The extreme cases are extrapolated.
- Not checked: threads or concurrency, Linux/CI, the owner demo. E1, the journal and MT5 are out of scope.
- `sochron.costs` was not probed beyond what risk consumes. Its own Mapping TOCTOU and subclass acceptance (`costs/model.py:92-127`) follow the same pattern; that is a follow-up, since this task must not touch costs.
- Observation, not a finding: a zero-width space reason (`"​"`) passes the non-blank check.
