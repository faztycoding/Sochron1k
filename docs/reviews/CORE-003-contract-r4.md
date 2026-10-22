# Review CORE-003 contract round 4 · base 0c00d92 · head 07856b9 · reviewer Codex, fresh headless reviewer session

Reviewed on 2026-10-22, Asia/Bangkok (+07:00). Object:
`docs/contracts/CORE-003-risk.md` v1.3 on `feat/CORE-003-risk`.
Full HEAD: `07856b90c7ddb3c335ad46a40157dce018785ec7`.
Scope: `git diff 0c00d92..HEAD -- docs/contracts/CORE-003-risk.md`
(20 additions, 7 deletions), its interaction with approved v1.2, and the
requested locked-test authoring inventory. All line references describe this HEAD.
The working tree was clean before this review. Only this report is written;
it remains unstaged. No implementation was imported or reviewed.

Ready for test authoring: no

F13 (Medium) and F14 (Low) need contract clarification. The temporal rows
and numeric compatibility checks are determinate. Rounds 1–3's F1–F12 are
not reopened. IDs below continue the contract-review sequence; references
to security F1–F8 identify the separate security pre-review sequence.
This verdict neither approves business policy nor verifies implementation.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F13 | Medium | confirmed | `docs/contracts/CORE-003-risk.md:122`, interacting with `:53`, `:134`, `:176` | The new blanket rule requires `type(x) is T` and rejects every subclass, while provenance is declared `Mapping`. Ordinary `dict` and `MappingProxyType` satisfy that interface but neither has exact type `Mapping`. AC-06's existing valid specifications use the stored mapping proxy (`tests/acceptance/CORE-003/test_risk_acceptance.py:393`); dictionary inputs and immutable output are explicitly tested at `:589`, `:612`, `:616`. The in-memory probe below confirms the type distinction. | A test author applies the exact-type sentence to the provenance container, or interprets it as applying only to concrete scalar/object types. | One reading rejects existing valid policy construction; another accepts it. Two authors cannot derive the same AC-06 oracle. | Explicitly exempt the provenance **container** from the exact-concrete-type rule: retain the `Mapping` interface requirement, copy once, validate and store the immutable copy. Keep provenance values exact `Provenance` with `BadPolicy` for a wrong value type; keep `Provenance`'s own field validation delegated to costs as `:134` already says. | Corrected text admits ordinary dict and mapping-proxy inputs, rejects non-Mapping containers with `TypeError`, and rejects a `Provenance` subclass value with `BadPolicy`. Existing copy/immutability rows remain valid; prohibited concrete subclasses still fail. |
| F14 | Low | confirmed | `docs/contracts/CORE-003-risk.md:123` | “Must answer in under 1 second” gives a number/unit but no timed region, reference environment, fixture set or trial rule. The error-column placement suggests oversized-input rejection, while it could also be read as a deadline for every in-bound operation. Security F3's example times one oversized `size_position` rejection. | Timing a prebuilt `Decimal` call versus including Decimal construction, imports, process startup or an entire matrix; applying the deadline to accepted extreme inputs. | A stopwatch assertion is possible, but it is not a reproducible acceptance criterion as written. Authors can produce incompatible pass/fail results without a functional difference. | Scope the deadline explicitly to oversized-input rejection. Specify preconstructed single-invalid fixtures, timing from public API invocation until the expected exception with a monotonic high-resolution timer, excluding setup/import/startup; name the Windows/Python 3.12 reference environment and whether every invocation or a stated statistic must be below 1.000 s. Preserve the existing numeric limits and one-second value. | A contract-defined timing row, including prebuilt `Decimal("1E-999999999")` as equity, raises `BadEquity` within the stated interval. The harness has an independent timeout so a regression cannot hang the suite. Record the environment and measured interval; do not silently extend the deadline to all accepted inputs. |

## AC status

Implementation acceptance is UNKNOWN for every AC: this is a contract
review, not an implementation test run. The separate readiness column
records only the reviewed delta and its surrounding impact.

| AC | Status (PASS/FAIL/UNKNOWN) | Authoring readiness | Why |
|----|----------------------------|---------------------|-----|
| AC-01 | UNKNOWN | PASS | Numeric bound admits the existing sizing and range operands; exact arithmetic/display rules remain unchanged. |
| AC-02 | UNKNOWN | PASS | Daily rollover/latch rules are unchanged and agree with the new gate-day check. |
| AC-03 | UNKNOWN | PASS | Same-day restart still retains daily halt; the new start prohibition belongs to E1. |
| AC-04 | UNKNOWN | PASS | Day argument, stale refusal, TimeReversal and complete reason tuples have a unique oracle below. |
| AC-05 | UNKNOWN | PASS | Stop-change rules are unchanged; exact-type and slot-bound additions use existing TypeError/BadStop categories. |
| AC-06 | UNKNOWN | FAIL | F13 leaves valid Mapping inputs contradictory; F14 leaves the added performance criterion incomplete. Other concrete-type/revalidation/error rules are consistent. |
| AC-07 | UNKNOWN | UNKNOWN | No new CORE-003 architecture requirement; the red-flag scan ran, but the implementation suite/import tests and future E1 enforcement were not run. |

## Checked, nothing found (and how)

### Day semantics and exact golden expectations

Contract `:97` preserves the stale state's policy, baselines and latches;
`:99–100` explicitly compare them against the **supplied current equity**,
and `:107` also uses that equity for sizing. There is no stored current-equity
field to substitute. Thus “evaluate the other reasons as usual with the
values in the state” does not imply rollover, discarding a latch, or sizing
from baseline equity. The gate does not mutate state.

Every row below uses H001_COSTS/H001_RISK, cost_per_lot 0, long, lots .02,
entry 4012.90, SL 4000.90, exposures 0. State day is 2026-10-22 and both
baselines are 10000. All other inputs are valid.

| Current equity | State daily / experiment flags | Request day | Exact result |
|----------------|--------------------------------|-------------|--------------|
| 10000 | False / False | 2026-10-22 | allowed True, reasons `()` |
| 10000 | False / False | 2026-10-23 | allowed False, reasons `("stale_state",)` |
| 10000 | True / False | 2026-10-23 | allowed False, reasons `("daily_halt", "stale_state")` |
| 10000 | True / True | 2026-10-23 | allowed False, reasons `("daily_halt", "experiment_halt", "stale_state")` |
| 10000 | False / False | 2026-10-21 | `TimeReversal`; no GateDecision |
| 9800 | False / False | 2026-10-23 | allowed False, reasons `("daily_halt", "experiment_halt", "stale_state")` |

“Daily-halted state” alone does not specify the experiment latch: the
daily-only row must be constructed explicitly, e.g. update the original
state to 9925 on day 22 and check at recovered equity 10000 on day 23.
A state obtained at 9800 on day 22 has both latches and yields the fourth row.
At equity 9800, loss 200 meets both thresholds (75 and 200), while sized
lots are still .02 (budget 24.5, risk/lot 1200); no sizing reason is added.
The same predicates were recomputed with a small Fraction oracle, without
importing risk. After `update_equity` advances a daily-only halted state to
day 23 at equity 10000, the returned state permits the ordinary request;
checking the original state still refuses. This is the useful rollover control.

Validation remains before branch selection (`:118`); an existing halt or
stale state cannot suppress a malformed input. Multiple-invalid-input
exception precedence remains intentionally unspecified; isolate each defect.

### Numeric bound and compatibility

An AST scan of both complete locked files parsed every numeric string
literal with Decimal, without importing production code or executing tests.
All finite numeric literals pass the new size bound:

| File | Numeric string literals | Maximum coefficient digits | Maximum absolute adjusted exponent |
|------|-------------------------|----------------------------|------------------------------------|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | 203 | 29 | 1,000,029 (`:555`, `1E-1000029`) |
| `tests/golden/CORE-003/risk_cases.py` | 151 | 34 | 1,000,027 |

The scan also checked all 21 explicit `Decimal("...")` literals in the
contract; the other numeric example rows were compared with the locked
fixtures. No existing numeric row is newly rejected by the bound. Existing
NaN/infinity negative rows remain domain errors, not valid-bound examples.
This finding concerns numeric compatibility; F13 is a separate type issue.

The bound is checked on the original finite Decimal before any rational
conversion. Coefficient count means the stored coefficient digits, including
trailing zeros, without normalization. Inclusive limits and the zero
exception were independently checked with Decimal tuple/adjusted inspection:

| Operand | Bound result |
|---------|--------------|
| `Decimal("1." + "2" * 999)` | admitted: 1,000 coefficient digits |
| `Decimal("1." + "2" * 1000)` | rejected: 1,001 coefficient digits |
| `1E+1100000`, `1E-1100000` | admitted by the input bound |
| `1E+1100001`, `1E-1100001` | rejected by the input bound |
| `0E-999999999` | admitted by this bound; the slot's ordinary zero-domain rule still applies |

Being admitted by the bound does not promise a valid display result. In a
precision-28, ROUND_HALF_EVEN context with Emin -999999, Emax 999999 and
Underflow/Overflow trapped, the independent display probe returned:

| Exact display value | Result |
|---------------------|--------|
| `1E-1000000` | exact subnormal accepted |
| `1E-1000026` | exact Etiny accepted |
| `1E-1000027` | Underflow, translated to RiskError by the contract |
| `1.1E-1000026` | inexact subnormal Underflow, translated to RiskError |

For the existing R rows, `4E-999998 * .0025 = 1E-1000000` and
`4E-1000025 * .0025 = 1E-1000027`. Both input equities satisfy the bound;
only the latter display conversion fails. The existing per-lot/actual-risk
range rows at acceptance `:524–563` also remain inside the input bound.

Per-slot errors at `:123` agree with the existing table: equity/baselines
use BadEquity; prices/SL/distance use BadStop; policy ratios and cost_per_lot
use BadPolicy; lots and the four consumed model fields use RiskError.
Direct SizeDecision display-field violations consistently use RiskError
under `:137`; no specialized display-field subclass is specified.
Finite nonpositive/off-grid lots remain business denials **when they satisfy
the new bound**; oversized lots are invalid input before reason collection.

### Concrete types, use-time validation and E1 boundaries

Except for F13's Mapping conflict, exact concrete types strengthen the
existing AC-06 rule without changing business values. Decimal/int/str/tuple/
date subclasses and model/policy/state/request subclasses are refused with
TypeError. Wrong provenance value types, including subclasses, use the
explicit BadPolicy exception. Provenance's own fields remain costs-owned
(`:134`), so this does not authorize a costs change.

`check_entry` must revalidate every request/state field, and `update_equity`
and `restart_experiment` must revalidate state (`:98`, `:118`, `:125`). This
covers type/domain changes made after construction. Valid-looking latch
forgery remains undetectable here; the contract explicitly delegates it to
E1. Existing constructor validation, FrozenInstanceError and provenance-copy
tests remain relevant and must not be weakened.

The added E1 list `:194–199` accurately carries the security pre-review:

| Source | E1 obligation carried into v1.3 |
|--------|--------------------------------|
| Security F7, owner option (b) | Refuse start_experiment if journal state already exists for the same account and Thai day. No change to CORE-003's pure start signature or restart rule. |
| L1 | Authenticate the clearer and pin policy by value/digest in the journal. |
| L2 / F8 | Journal restoration controls reconstruction; forbid direct HaltState construction, relevant replace calls and object.__setattr__ outside risk/journal; halt on unknown state. |
| L3 | Bind entry price to the current order-side tick, model to symbol_info, exposures to MT5, and send exactly the gated tuple. |
| L4 | Read current_stop from the actual MT5 position. |
| F6 | Update state before entry and pass the same request day into the gate. The gate itself rejects an unrolled/future-dated state as specified. |

The F8 invariant at `:155`, read with `:77`, `:153` and `:191`, acknowledges
constructor/replace/setattr bypasses rather than claiming frozen objects
are an authentication boundary. Its “public functions” qualifier assumes
retaining the returned state and obeying the stated lifecycle; public
start_experiment alone cannot enforce account/day history. The E1 F7/L2
rules carry that enforcement. No new risk rate, halt threshold, authorized
identity, cost budget or permission to trade is invented. Q1/Q6 remain yes,
Tier High remains appropriate, and Q2–Q5 do not change in this pure-module delta.

## Locked-test changes for the test author

Scope the next proposal to
`tests/acceptance/CORE-003/test_risk_acceptance.py` and
`tests/golden/CORE-003/risk_cases.py`. Clarify F13/F14 first. Existing
architecture coverage can remain unchanged for this delta; E1 enforcement
requires its future contract. Preserve all existing rows and expectations.

1. **Migrate every check_entry call.** Insert day between equity and state
   at acceptance lines **293, 297, 300, 304, 310, 316, 317, 320, 328, 336,
   341, 343 and 389**. For existing rows use the supplied state's day (DAY
   in these fixtures), preserving explicit cost_per_lot position. Add
   `day=DAY` to the `entry` valid-argument specification at **405–406** and
   the branch-validation dictionary at **508–509**, which feeds the call
   at **519**. These dictionaries also feed generic calls at 413/441 and
   the domain loop; updating only the named check_entry calls is insufficient.
   The golden file currently contains data, not check_entry invocations.

2. **Add day/reason rows to AC-04 and the golden data.** Include each row in
   the temporal table above, and the correctly updated day-23 control.
   Assert the entire sorted reason tuple, allowed flag and unchanged input
   state. Add `stale_state` to the valid GateDecision reason list at
   **495–500**. Add TypeError rows for non-date day, datetime and a custom
   date subclass; add the earlier-day TimeReversal row with otherwise valid
   inputs. A daily-only latch and a both-latches fixture must be distinct.
   Include a stale state with a malformed independent argument to prove
   stale refusal does not short-circuit validation.

3. **Add a numeric-bound matrix to AC-06.** Cover 1,000 versus 1,001 stored
   coefficient digits, exact positive/negative adjusted limits versus one
   beyond them, and a zero with a huge exponent in a slot permitting zero.
   Include trailing-zero coefficients (e.g. `1.` followed by 999 versus
   1,000 zeroes) so normalization cannot erase an oversized representation.
   Isolate coefficient and exponent violations, retain finite/domain-valid
   values otherwise, and assert the slot's specific error. Cover:

   | Slots / entry points | Oversize error |
   |-----------------------|----------------|
   | equity in size_position/start_experiment/update_equity/restart_experiment/check_entry; HaltState day_start_equity and experiment_start_equity | BadEquity |
   | size_position stop_distance; EntryRequest entry_price/stop_loss; check_stop_change current_stop/non-None new_stop | BadStop |
   | RiskPolicy risk_per_trade/daily_loss_limit/experiment_loss_limit; cost_per_lot in size_position/check_entry | BadPolicy |
   | EntryRequest lots; all four SizeDecision Decimal fields; consumed CostModel contract_size/volume_min/volume_step/volume_max through sizing and entry | RiskError |

   Include the use-time variants below. In-bound boundary acceptance can
   be shown through constructors/start_experiment without requiring enormous
   rational calculations; arithmetic calls may still legitimately fail the
   existing display range rule. Keep RANGE_ROWS and acceptance **524–563**
   intact, and distinguish display RiskError from an erroneous input-bound
   BadEquity/BadStop (a broad raises(RiskError) alone can mask that regression).
   Add the clarified F14 timed oversized-rejection row, including equity
   `1E-999999999`; do not benchmark unsafe rational conversion deliberately.

4. **Extend AC-06's type matrix with subclasses.** Test Decimal subclasses
   in every numeric slot, int subclasses in both count fields, date
   subclasses in state/day arguments, str subclasses in side/authorization/
   reason/tuple members, and tuple subclasses for halt_clearers/reasons.
   Test RiskPolicy, HaltState, EntryRequest and CostModel subclasses wherever
   those objects are arguments (including nested state.policy). Check exact
   Decimal types for each of the four consumed model fields. Test a
   Provenance subclass as a policy provenance value -> BadPolicy; other
   forbidden subclasses -> TypeError. Include adversarial variants from
   security F1 (misleading ratio/equality/membership), not only empty subclasses.
   Keep valid dict/mapping-proxy inputs and immutable-copy assertions after
   F13 is clarified. Do not require new validation inside sochron.costs.

5. **Add use-time revalidation rows.** Construct valid fresh local fixtures,
   mutate each EntryRequest field with object.__setattr__, and invoke the
   gate. Examples: side="buy" / exposures=-1 / lots=NaN -> RiskError;
   entry_price=Infinity or invalid non-None SL -> BadStop; wrong exact type
   -> TypeError; oversized Decimal -> the slot's bound error. Mutate each
   HaltState field and invoke check_entry/update_equity/restart_experiment:
   invalid baselines -> BadEquity; wrong day/flags/policy type -> TypeError;
   invalid nested policy domains -> BadPolicy. For restart, begin with a
   genuinely experiment-halted fixture and valid authorization to isolate
   the changed field. Use fresh policy/model copies, never mutate H001
   singleton fixtures. Cover existing-halt, missing/wrong-side-SL and stale
   branches so no early refusal hides validation. Retain ordinary finite
   off-grid/nonpositive-lots reason rows. Do not assert that changing a
   valid bool latch to False can be detected by the pure module.

6. **Keep E1 work out of this patch.** Record F7, L1–L4 and F6 as future E1
   acceptance/architecture obligations. Do not add a same-day-history check
   to pure start_experiment, remove deliberate constructor/replace fixtures,
   alter CORE-001/002 expectations, or write E1 tests against absent code.
   Update the golden file's v1.2 description for the new contract revision;
   retain its production-independent literal oracles. The implementer will
   separately migrate its unit-test callers; that is outside the locked patch.

## Checks run

All times are 2026-10-22 +07:00; revision is `07856b9`. No new commit exists.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| `git diff 0c00d92..HEAD -- docs/contracts/CORE-003-risk.md` and line-numbered contract/test inspection | PASS: reviewed the complete delta and specified interactions; two findings above | 07856b9 | 09:00–09:06 |
| `git diff --check 0c00d92..HEAD -- docs/contracts/CORE-003-risk.md` | PASS, no whitespace errors | 07856b9 | 09:04, 09:06:42 |
| `git diff --name-only 0c00d92..HEAD -- tests/acceptance/CORE-003 tests/golden/CORE-003` | PASS, empty: this contract delta did not alter the locked tests | 07856b9 | 09:06:42 |
| `uv run --offline --no-sync python -B -c 'import sys; print(sys.version)'` | PASS: CPython 3.12.15, Windows AMD64 | 07856b9 | 09:04 |
| `uv run --offline --no-sync python -B -` (stdin-only AST/Decimal/Fraction/Mapping probes described below) | PASS: literal compatibility, bound endpoints, display boundaries and temporal oracles; Mapping distinction reproduced | 07856b9 | 09:04:54 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; two inherited pattern groups, explained below | 07856b9 | 09:04:01 |
| `rg` discovery/search attempt from PowerShell | BLOCKED: `The term 'rg' is not recognized as the name of a cmdlet, function, script file, or operable program.` Read-only Get-Content/Get-ChildItem/Select-String fallback completed inspection; no configuration changed | 07856b9 | 09:00–09:01 |

The literal probe uses ast.parse/ast.walk on the two named locked files,
selects string constants matching
`[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?`, and checks
`len(v.as_tuple().digits) <= 1000 and (v.is_zero() or abs(v.adjusted()) <= 1100000)`.
The same predicate checks explicit contract Decimal strings and the bound
table. The display probe applies unary plus to each displayed value within
a fresh Context having the parameters stated above. The temporal probe
uses Fraction for the two loss inequalities and sized lots, then adds
stale_state and sorts the complete reasons. No production imports, package
installation, bytecode/cache files or persistent probe scripts were used.
For F13, the minimal independent reproduction is:

```python
from collections.abc import Mapping
from types import MappingProxyType
for value in ({}, MappingProxyType({})):
    assert isinstance(value, Mapping)
    assert type(value) is not Mapping
```

Red flags: the two pattern groups are inherited type-suppression markers
in intentional negative unit tests and documentation quoting them, and
lint-suppression words in existing documentation. The control-name list
also includes policy.py and the security-review filename by heuristic,
plus inherited locked paths. None is introduced by the contract delta.
No secret or order/account-mutation group was reported; no tests were
deleted/renamed. The scan ran before this untracked report was created and
does not claim to scan it. The report is prose/evidence only.

## Not checked (and why)

- Implementation fixes in e1a095b/d7a312c/0c00d92, implementation security,
  the pytest suite, runtime API compatibility and the one-second deadline:
  outside this contract-only review. No runtime acceptance PASS is claimed.
- New locked tests were not authored/applied. Their precise scope is above;
  F13/F14 should be resolved before that separate test-author session.
- E1, journal enforcement, broker/terminal behavior, real identity, actual
  send binding, concurrency and account/day-history enforcement: future E1
  scope. No terminal/account/network action was performed.
- CI, owner demo, merge/deploy and broad branch approval: not requested.
  The required main-based scan contains inherited changes; those changes
  were not re-reviewed as part of this bounded delta review.
- No fresh full re-review of approved v1.2 or F1–F12. R3's closure remains
  the baseline; only interactions with v1.3 were inspected.
- No PROGRESS/handoff edit or commit: the owner explicitly limited this run
  to this single unstaged review file, which carries the checkpoint and
  test-author handoff. No write to .git, staging or push was attempted.

Next action: clarify F13/F14 in the contract, then run the scoped test-author
session. Review artifact written; implementation verification, merge and
deployment remain outside this delivery.
