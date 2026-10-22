# Review CORE-003 contract round 5 · base 07856b9 · head e414246 · reviewer Codex, fresh headless reviewer session

Reviewed on 2026-10-22, Asia/Bangkok (+07:00).
Object: `docs/contracts/CORE-003-risk.md` v1.3 on `feat/CORE-003-risk`.
Full HEAD: `e414246120b1929c9993af038f4c08e16ebbdf62`.
Scope: `git diff 07856b9..HEAD -- docs/contracts/CORE-003-risk.md`
(3 additions, 3 deletions): F13/F14 from
[round 4](CORE-003-contract-r4.md), their immediate interactions, and the
requested test-author inventory. Contract line references describe this HEAD.

Ready for test authoring: yes

F13 (Medium) and F14 (Low) are **closed** at contract level. Neither is still
open or reopened. No new finding was introduced by these edits. No replacement
sentence is needed. F1–F12 and the other round-4 conclusions are not reopened.
This verdict concerns the determinacy of the contract, not implementation
acceptance, owner approval, CI, merge or deployment.

The working tree and index were clean at entry. The only authorized write
is this unstaged review file; it also carries the checkpoint and test-author
handoff. No implementation was imported or reviewed. A separate read-only
reviewer independently checked F14 against the contract and the same diff.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F13 | Medium | confirmed | `docs/contracts/CORE-003-risk.md:122`, with `:53`, `:132–134`, `:176` | The added exception explicitly accepts every `collections.abc.Mapping` container, naming `dict` and `MappingProxyType`; it requires one copy, validation of that copy, and storage as its mapping proxy. Non-Mapping containers explicitly raise TypeError. Values must still be exact Provenance, otherwise BadPolicy. | Valid dict/proxy/custom-Mapping provenance; non-Mapping input; Provenance-subclass value, each with all other fields valid. | The old exact-type/container contradiction is removed without relaxing concrete value types or immutable-copy semantics. | None; the requested exception is present. | Before/after comparison of `:122` against round 4's F13 proof-of-fix, and the case matrix below, gives one expected result for every requested case. AC-06 `:176` retains the copy/immutability obligations. Runtime regression tests remain to be authored/run. |
| F14 | Low | confirmed | `docs/contracts/CORE-003-risk.md:123`, with `:118`, `:176` | The replacement scopes timing exclusively to oversized-input rejection, prebuilds Decimal, excludes setup/import/startup, times the public call to its expected exception using perf_counter, requires every call < 1.000 s, names Windows 11 + Python 3.12.15 via uv, and specifies a daemon thread with join(timeout=10). | One otherwise-valid public call with an oversized numeric operand, including equity Decimal("1E-999999999"). | The timed region, pass rule, reference environment and watchdog are now determinate; accepted inputs acquire no new deadline. | None; the requested timing method is present. | Before/after comparison of `:123` against round 4's F14 proof-of-fix, the timing checklist below, and the independent read-only check agree. Single-invalid cases follow `:118`. Actual elapsed time and watchdog operation remain untested. |

## AC status

Implementation acceptance remains UNKNOWN for all seven ACs. PASS below
means authoring readiness for the two reviewed clauses only.

| AC | Status (PASS/FAIL/UNKNOWN) | Authoring readiness | Why |
|----|----------------------------|---------------------|-----|
| AC-01–AC-05 | UNKNOWN | Not re-reviewed | F13/F14 do not edit their outcomes; round 4's retained inventory still applies. |
| AC-06 | UNKNOWN | PASS for F13/F14 | The Mapping/container distinction and oversized-rejection timing method now have unambiguous expected results under the error table incorporated by `:176`. No implementation tests were run. |
| AC-07 | UNKNOWN | Not re-reviewed | The red-flag scan ran; architecture tests, the Python suite and CI did not. |

## Checked, nothing found (and how)

### F13: container versus exact values

Read the new exception together with the Mapping declaration (`:53`),
the policy/domain row (`:132`), costs-owned Provenance fields (`:134`)
and AC-06's immutable-copy requirement (`:176`). The following results
are contract expectations, not observations of the implementation.

| Single varied input | Required result |
|---------------------|-----------------|
| Valid ordinary dict with the five required keys and exact Provenance values | Accepted; copy once, validate the copy, store an immutable MappingProxyType of that copy. |
| MappingProxyType over equivalent valid data | Accepted with an independent copied snapshot; the original proxy's backing dictionary must not remain the policy's live source. |
| Another valid collections.abc.Mapping implementation/subclass | Accepted as a container; the exact-concrete-type rule does not turn Mapping into a dict/proxy-only allowlist. |
| Non-Mapping container, including an iterable of otherwise valid key/value pairs | TypeError; converting it to dict first would incorrectly broaden the contract. |
| Valid Mapping with one Provenance-subclass value | BadPolicy; the container exception does not exempt values. |
| Exact Provenance instance's own field validation | Still owned by sochron.costs, with its existing TypeError/BadProvenance contract. |

The exception therefore preserves the round-4 immutable-copy rows and
forbidden concrete-subclass rows without a contradictory acceptance oracle.

### F14: reproducible rejection timing

Compared each part of `:123` with round 4's requested fix and read `:118`
to retain single-invalid-input fixtures.

| Timing question | Contract answer |
|-----------------|-----------------|
| Which operations? | Only public calls rejecting input over the numeric ceiling; no deadline for in-bound input. |
| Fixture preparation? | Decimal exists before measurement; construction, imports and process startup excluded. Retain the round-4 equity fixture `Decimal("1E-999999999") -> BadEquity`. |
| Timed interval? | `time.perf_counter()` from public invocation until the expected exception. |
| Pass statistic? | Every call strictly < 1.000 s; equality is not a pass. |
| Hang protection? | Call runs in a daemon thread, with `join(timeout=10)`; the ten-second watchdog does not replace the one-second acceptance threshold. |
| Reference environment? | Windows 11 + Python 3.12.15 through uv, explicitly named. |

No numeric ceiling, slot-specific error, accepted-input behavior, cost
policy or E1 rule is changed. The remaining diff line is revision history.
The separate F14 reviewer reached the same contract-level closure without
running or importing implementation code.

## Locked-test changes for the test author

All six round-4 items remain valid. Only the F13/F14 details in items 3 and
4 and their resolved prerequisite are amended below; the temporal-table
link points back to round 4. Locked-test line numbers are unchanged because
`git diff --name-only 07856b9..HEAD -- tests/acceptance/CORE-003 tests/golden/CORE-003`
is empty. This is a retained authoring inventory, not a fresh test review.

Scope the next proposal to
`tests/acceptance/CORE-003/test_risk_acceptance.py` and
`tests/golden/CORE-003/risk_cases.py`. F13/F14 are closed at contract level. Existing
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
   [round 4's temporal table](CORE-003-contract-r4.md#day-semantics-and-exact-golden-expectations), and the correctly updated day-23 control.
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
   **F14 clarification:** use prebuilt Decimal fixtures for oversized-input
   rejection rows, including `Decimal("1E-999999999")` as equity to
   size_position -> BadEquity, with every other argument valid. In the daemon
   worker, measure with `time.perf_counter()` immediately before the public
   call until the expected exception; exclude Decimal construction, imports
   and process startup. Every call must take < 1.000 s on the named reference
   environment, Windows 11 + Python 3.12.15 via uv; no percentile, averaging
   or retry-until-pass substitution. Use `join(timeout=10)` and fail if the
   worker is still alive, the call returns, or the exception is wrong; do not
   then wait indefinitely for a worker result. Record the environment and
   each elapsed interval. Do not apply this deadline to in-bound rows or
   benchmark unsafe rational conversion deliberately.

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
   **F13 clarification:** keep valid dict and MappingProxyType input rows;
   add a valid custom collections.abc.Mapping container to distinguish the
   interface exception from a two-concrete-types allowlist. Require a single
   copied snapshot, validation of that snapshot, and immutable
   MappingProxyType storage. Preserve source-dict mutation and proxy-write
   rejection assertions, including mutation of a proxy's backing dict.
   Non-Mapping containers (including a list of valid key/value pairs) must
   raise TypeError; a Provenance-subclass value in an otherwise valid
   Mapping must raise BadPolicy. The exemption is for the container only.
   Do not require new validation inside sochron.costs.

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

All times below are 2026-10-22 +07:00; the reviewed revision is `e414246`.
No new commit was created.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: initially clean, expected branch, full HEAD as above | e414246 | 09:12 |
| `git diff 07856b9..HEAD -- docs/contracts/CORE-003-risk.md`; line-numbered UTF-8 contract and round-4 inspection | PASS: complete 3-addition/3-deletion delta checked; F13/F14 closed at contract level | e414246 | 09:12–09:15 |
| `git diff --name-status 07856b9..HEAD` | PASS: only the contract modification and added round-4 review are in this revision delta | e414246 | 09:13 |
| `git diff --check 07856b9..HEAD -- docs/contracts/CORE-003-risk.md` | PASS, exit 0, no whitespace errors | e414246 | 09:15:10 |
| `git diff --name-only 07856b9..HEAD -- tests/acceptance/CORE-003 tests/golden/CORE-003` | PASS, exit 0, empty; retained inventory's locked-test line references are unchanged | e414246 | 09:15:10 |
| Independent read-only F14 clause/diff comparison | PASS for contract readiness only; same six timing requirements confirmed | e414246 | 09:13:55 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; two inherited pattern groups, explained below | e414246 | 09:14:07–09:14:09 |
| `rg -n 'risk\|Risk\|ความเสี่ยง\|CORE-003\|^##\|^###' SPEC.md` from PowerShell | BLOCKED: `The term 'rg' is not recognized as the name of a cmdlet, function, script file, or operable program.` Read-only Get-Content/Select-String fallback completed the reads; no configuration changed | e414246 | 09:12 |
| `git status --short`; `git diff --cached --name-only`; `git rev-parse HEAD` immediately before the report write | PASS: clean tree, empty index diff, unchanged HEAD | e414246 | 09:15:45 |
| Report UTF-8 read-back; `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD` after writing | PASS: report matches intended text with no trailing whitespace; only this review is untracked, tracked/index diffs empty, HEAD unchanged | e414246 | 09:18:17 |

Red-flag hits: the main-based scan reports **Type checks disabled** for
inherited intentional negative unit-test annotations and documentation
quoting them, and **Lint disabled** for documentation quoting suppression
terms. The control-name heuristic lists inherited locked paths, policy.py
and the security-review filename. None is introduced by the F13/F14 edit;
the inspected contract delta adds no suppression or control change.
No deleted/renamed tests or secret/order-account-mutation group was reported.
The scan ran before this report existed and does not scan this untracked
file. This is an explanation of scan hits, not a new audit of inherited code.

## Not checked (and why)

- Implementation behavior, runtime Mapping acceptance/error types, numeric
  performance, thread timeout behavior, pytest, mutation tests and security
  implementation review: outside this contract-only F13/F14 re-check.
  No runtime acceptance PASS is claimed.
- Other findings, the full v1.2/v1.3 contract, unchanged round-4 numeric or
  temporal oracles, and a fresh locked-test content review: not reopened.
  Existing inventory is carried forward; only F13/F14 details are amended.
- New locked tests were not authored or applied. Architecture/E1 enforcement,
  journal restoration, identity, terminal/account behavior, sends and market
  data remain outside this task. No broker or external/network action occurred.
- CI, owner demonstration, task approval, merge and deployment: not requested
  and not evidenced by this review.
- PROGRESS.md, handoff files, contract edits, staging, commits and push:
  excluded by the owner's explicit one-review-file instruction. This file
  records the checkpoint and next action instead.

Delivery: review artifact written; contract clarification verified for
F13/F14 only. Implementation delivery state is unchanged by this review.

Next action: the separate test-author session can prepare the locked-test
proposal using the retained six-item inventory above, then follow the
existing patch and fresh-review workflow. No further F13/F14 contract edit
is needed.
