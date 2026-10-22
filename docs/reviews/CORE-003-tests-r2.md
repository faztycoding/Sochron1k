# Review CORE-003-tests round 2 · base main · head fcf77c5 + applied `CORE-003-tests-r2.patch` (uncommitted) · reviewer Claude Code (fresh session, D-006 post-apply review)

Scope: the two locked test files changed by `docs/proposals/CORE-003-tests-r2.patch` (Codex, test-author
role), which the implementer session applied under D-006 on 2026-10-22 and has not committed. I reviewed
them against contract v1.3 (`docs/contracts/CORE-003-risk.md`, Tier High), the six-item "Locked-test changes
for the test author" list in `docs/reviews/CORE-003-contract-r5.md` (round 4's list with F13/F14 amended),
round 4's temporal table, the "Tests r2 for contract v1.3" section of `docs/handoff/CORE-003.md` and the
previous review `docs/reviews/CORE-003-tests-r1.md`. I did not edit, stage or commit anything. This file is
the only repository file I wrote. Scratch evidence lives under this session's scratchpad
(`C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\97683567-fd3b-4a4a-b126-40219d53b8cf\scratchpad\`:
`red-run.txt`, `red-lines.txt`, `pairs.tsv`, `collected.txt`, `redflags.txt`, `head_acc.py`, `head_golden.py`).
All times are 2026-10-22, +07:00.

Verdict: **Ready to commit red: yes.** The patch is byte-exact (all six digests match the handoff) and does
what round 5 asked. Every `check_entry` call passes `day`. The temporal rows equal round 4's table. The
size-bound, subclass, Mapping and use-time matrices cover every slot named in the inventory. No v1.2
assertion or golden row is lost: an AST multiset compare shows 0 missing. All new numeric expectations
agree with an exact Fraction oracle. The red state matches the implementer's numbers, and 381 of 382 failures
have the expected v1.3 cause.

There is one Medium finding, at contract level. F1: the timing harness's `join(timeout=10)` cannot stop a
regression that holds the GIL, so the extreme-equity row hangs the suite instead of failing it. That is the
case the contract says the watchdog prevents. Acceptance stays sound, because a hang is never a pass. There
are five Low findings. F2 is one fixture that breaks two contract rules at once. F3 is a revalidation scope
wider than the contract text (owner question). F4 is two non-discriminating `contract_size` exponent rows.
F5 is base-`RiskError` rows that accept subclasses. F6 shows in-bound acceptance only through constructors.
None blocks committing red.

Recommendation: commit red now. The owner decides F1 (add a hard process deadline or accept the limitation)
and F3 (confirm the wider revalidation in one contract sentence). Codex then closes F2 and F4, and optionally
F5 and F6, in a supplemental D-006 patch before the v1.3 implementation is finished.

Detector note (N6): the post-run locked-path detector fired after this session's first read-only command
(`git status --porcelain`). It listed exactly `uncommitted M tests/acceptance/CORE-003/test_risk_acceptance.py`
and `uncommitted M tests/golden/CORE-003/risk_cases.py`, the target files of the patch just applied, and
nothing else. Under CLAUDE.md I verified every expected SHA256 and blob against the handoff (all match, see
"Hashes") and continued. It did not fire again.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:756-762` (`Thread(daemon=True)`, `start`, `join(timeout=10)`, alive check), `:797-800`; contract `:123` ("harness รันการเรียกใน daemon thread และ `join(timeout=10)` เพื่อไม่ให้ regression ค้างทั้ง suite") | (1) Isolated run of `test_ac06_extreme_equity_rejection_deadline` against the v1.2 code under `timeout -k 5 45`: exit 124 after 46 s, no pytest output (09:55:38–09:56:24). This matches the implementer's 120 s run. (2) Stdlib probe, no production import: a daemon thread runs `Decimal("1E-999999999").as_integer_ratio()`, the same exact-ratio conversion. The main thread never returned from `worker.start()`, so `join(timeout=2)` was never reached. The faulthandler traceback shows the main thread in `threading.py:655 wait` called from `start` (09:56:30–09:56:35). (3) Handoff `:452-457`: `size_position.model.volume_step.negative_adjusted` took 28.052 s of wall time, although the watchdog is nominally 10 s. | A regression that converts an oversized Decimal to an exact ratio before the bound check, for example a deleted or misplaced bound check. The current v1.2 code (no bound) already does this. | A single C call that holds the GIL blocks every other Python thread. The daemon-thread watchdog therefore cannot fire for exactly the regression class the F3 bound exists to stop, and the contract's stated purpose is not met. Consequences: (a) the AC-07 command `uv run --offline pytest tests -q -p no:cacheprovider` does not terminate on the red commit or on any such regression; (b) red evidence must deselect that one test; (c) leaked workers from failed timing rows slow later tests in the same process. **Not affected:** no false pass is possible (a hang never reports PASS), and a correct v1.3 implementation rejects in microseconds. No CI job runs pytest today (`.github/workflows/ci.yml` runs only control self-tests and the red-flag scan), so CI cannot hang. The test follows the contract exactly; the defect is in the prescribed mechanism. | Owner decision, one of: (a) amend contract `:123` so that the harness also arms a hard process deadline from the stdlib, `faulthandler.dump_traceback_later(T, exit=True)` before `worker.start()` and `faulthandler.cancel_dump_traceback_later()` after the join. This turns a hang into a loud failure: process exit 1 with every thread's traceback. No dependency. Codex then adds it in the supplemental patch. (b) Run each timed call in a child process killed on timeout (heavier: one process per row, about 236 rows). (c) Accept the limitation: record in the contract/PROGRESS that the watchdog does not cover GIL-holding regressions, and that runs before v1.3 lands must deselect the row and use an outer `timeout`. I recommend (a). | Probe above: with `dump_traceback_later(5, exit=True)` the same hang ended after 5 s with exit 1 and a traceback (start 09:56:30, end 09:56:35). Not yet tried inside pytest. pytest's own faulthandler plugin arms a timer only when `faulthandler_timeout` > 0, and that is unset here. |
| F2 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:1106` (`("policy.halt_clearers", (), "BadPolicy")`), used by `:1140-1152` for `restart_experiment`; contract `:87`, `:118`, `:132`, `:135` | Red run: `test_ac06_revalidates_every_state_field_at_use[policy.halt_clearers-value17-BadPolicy-restart_experiment-ordinary]` fails with `sochron.risk.errors.BadHaltClear: 'owner' is not allowed to start or restart this experiment` (`halts.py:53`). This is the only one of 382 failures whose cause is not a missing v1.3 feature. Emptying the allowlist makes two contract rules apply to one call: `halt_clearers` empty → `BadPolicy` (`:132`), and `authorized_by` not in `state.policy.halt_clearers` → `BadHaltClear` (`:87`, `:135`). | An implementation checks authorization before it revalidates the nested policy. | The row pins an order between two applicable rules, which the contract leaves open. `:118` asks acceptance to test one defect at a time. A contract-compliant implementation could fail this row. Revalidating state before authorization is the natural order, and it makes the row pass. | For the `restart_experiment` row, use an invalid allowlist that still contains `"owner"`, such as `("owner", "owner")` (duplicate → `BadPolicy` under `:132`) or `("owner", " ")` (blank name). Optionally use the same value for all three entry points. | With `("owner", "owner")` exactly one rule applies, so BadPolicy is the only correct outcome whatever the check order. Against v1.2 the row stays red for the intended reason (no nested revalidation: "DID NOT RAISE BadPolicy", like the `update_equity` row). Not run. |
| F3 | Low | question | `tests/acceptance/CORE-003/test_risk_acceptance.py:722-724` (`policy.*` slots for `HaltState`, `size_position`, `start_experiment`, `unknowns`), used by `:787-794` and `:955-960`; contract `:98`, `:122-123`, `:125` | The 12 slots give 48 rows: 12 Decimal-subclass rows and 36 oversized rows. They require every entry point to revalidate a `RiskPolicy` that was mutated with `object.__setattr__` after construction and then passed in directly. The contract's use-time row `:125` (security F4) and `:98` name only `EntryRequest`/`HaltState` fields in `check_entry`, `update_equity` and `restart_experiment`. Exact types extend to the CostModel fields "ที่ risk อ่าน" only (`:122`). Rounds 4/5 items 3–5 list `RiskPolicy` construction and nested `state.policy`, not a directly passed policy. The v1.2 code already revalidates request/state at use (`0c00d92`), and it fails all 12 subclass rows for these slots, so the implementer read the contract more narrowly. Rows that are clearly beyond the text: `size_position` with an unconsumed `daily_loss_limit`/`experiment_loss_limit`, and all `unknowns.policy.*` rows. The bound for `size_position.policy.risk_per_trade` is contract-backed, because `:123` checks it "ก่อนแปลงเป็นตรรกยะ". | The implementer follows `:125` literally. | Tests are part of the contract (AGENTS.md), so these rows add a requirement the owner did not approve in words. The change is in the safe direction: a shared validator makes it cheap, and it closes a DoS/type path through a mutated policy. | The owner confirms with one contract sentence, for example "every public function and `HaltState(...)` revalidate every `RiskPolicy` they receive, directly or as `state.policy`, with the policy-row errors". Otherwise Codex drops the rows for unconsumed fields. | After the sentence lands, the rows trace to the text. |
| F4 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:713-715`, `:775-784`; handoff `:559-560` | The red run passes `test_ac06_oversized_decimal_per_slot[size_position.model.contract_size.negative_adjusted]` and `[...positive_adjusted]` against the v1.2 code, which has no size bound. The display rule raises the same exact `RiskError` (Underflow/Overflow of `risk_per_lot`) in about 0.15 s (handoff `:559-560`). The contract maps both the model-field bound and display range errors to `RiskError` (`:123`, `:138`), so exception type cannot tell them apart. Only the clock can, and 1E±1100001 converts in under 1 s. The same holds for the `check_entry.model.contract_size` exponent rows once the signature is migrated, because the gate's internal sizing raises the same display error. | A v1.3 implementation that bounds coefficients but forgets the exponent bound on `contract_size`, or checks it after conversion. | These two rows cannot detect a missing exponent bound on `contract_size`. A CostModel with, for example, `contract_size = 1E-999999999` would then hang `size_position`/`check_entry`. That is the DoS the bound exists to stop. | Add timed rows like the F14 equity row: prebuilt `Decimal("1E-999999999")` and `Decimal("1E+999999999")` as `model.contract_size` through `size_position` and `check_entry`, expecting exact `RiskError` in < 1.000 s. Pair this with F1 (a), so a regression fails loudly instead of hanging. | Against v1.2 the new rows would not complete. They use the same exact-ratio conversion as the extreme-equity row, which hangs (F1 evidence). A bound-first implementation rejects in microseconds. Not run. |
| F5 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:110-112` (`_reject` → `pytest.raises(error)`), `:1088-1094` (`side "buy"`, `open_exposures -1`, `lots NaN` → `RiskError`), `:1133-1137` | `pytest.raises(RiskError)` also accepts `BadStop`, `BadEquity`, `BadPolicy`, `BadHaltClear` and `TimeReversal`. For rows whose contract error is the base `RiskError` (`:127`, `:130`, `:131`), the use-time request rows therefore accept any subclass. The timing rows require the exact type (`:767`), and so do the five strengthened display rows (`:553-574`). The same loose pattern exists in the v1.2 generic domain loop (`:461-474`). | An implementation that raises, for example, `BadStop` for a mutated `side` or `lots`. | It still refuses, so there is no money impact, only a wrong error class that callers might branch on. The strictness is inconsistent within one file. | Optional: for rows whose expected error is the base `RiskError`, assert `type(caught.value) is RiskError`. Note the expected-test-red reasoning: this only tightens. | Not run. |
| F6 | Low | question | `tests/acceptance/CORE-003/test_risk_acceptance.py:803-824` | Inclusive-bound acceptance (1,000 digits, trailing zeros, `|adjusted|` = 1,100,000) is shown only through dataclass constructors and `start_experiment`. Round 4 permits this "without requiring enormous rational calculations". However, the coefficient edges are cheap in arithmetic calls too: equity `"0.1" + "0"*999` (= 0.1) in `size_position` → lots 0 `below_min_volume`; `"1." + "0"*999` in `update_equity`; `cost_per_lot` `"0." + "1"*1000` in `check_entry`. These rows are absent. | An implementation that checks the bound separately per function, with an off-by-one (`>= 1000`) only in an arithmetic entry point. | Such a rejection of valid input would pass the suite. It fails safe (refusal), so the risk is low. | Optional: add a few coefficient-edge rows through `size_position`, `update_equity`, `restart_experiment` and `check_entry`. Keep exponent edges at constructors, as round 4 allows. | Not run. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

The status is for the red state: the v1.2 implementation with the v1.3 tests. Red is the intended state
before the v1.3 implementation.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | `test_ac01_exact_sizing_grid_caps_and_display_context` passes, including the new `cap_equal` golden row (oracle-checked). Sizing is unchanged in v1.3. |
| AC-02 | FAIL (expected) | The original AC-02 test passes. The new distinct-baseline (4) and custom-limit (4) tests pass their `update_equity` assertions, then fail on `check_entry() got an unexpected keyword argument 'day'`. |
| AC-03 | PASS | The original AC-03 test and `test_ac03_restart_uses_distinct_daily_baseline` pass. |
| AC-04 | FAIL (expected) | All gate rows fail on the v1.2 signature: positional calls give "state must be exactly HaltState, not date"; keyword calls give "unexpected keyword argument 'day'". The six temporal rows and the rollover control are among them. |
| AC-05 | PASS | `test_ac05_stop_change_cannot_widen_or_remove` passes. Its v1.3 bound and type rows live in AC-06 matrices (`check_stop_change.*` oversized rows fail: no bound). |
| AC-06 | FAIL (expected) | 210 of 212 oversized rows fail (no bound) and 2 pass (F4). 18 subclass rows fail (no policy revalidation; 12 depend on F3). Nested-policy use-time rows fail. The one row that fails with `BadHaltClear` is F2. The extreme-equity row does not finish (F1), so its status is UNKNOWN. |
| AC-07 | FAIL (expected) | The three architecture tests pass, and `tests/architecture/test_imports.py` is byte-identical to HEAD. The "whole suite green" criterion fails (red by design), and the full command without `--deselect` does not terminate (F1). |

## Checked, nothing found (and how)

### Hashes and patch state (task item 1–2)
- `git status --porcelain` (09:45:22): exactly ` M docs/handoff/CORE-003.md`,
  ` M tests/acceptance/CORE-003/test_risk_acceptance.py`, ` M tests/golden/CORE-003/risk_cases.py`. Nothing
  untracked; `git diff --cached --name-only` is empty. `git check-ignore -v` shows
  `.gitignore:10:docs/proposals/` for the patch.
- `git diff --stat`: handoff +416; acceptance +600/−22 (numstat 578 added, 22 deleted); golden +46/−1.
  The handoff change is append-only (416 added, 0 deleted).
- `sha256sum` (09:45:41): acceptance `69cd888f057fbcc1365f41d3aaae448dfccb6caf1b94e945029d120fedfab373`,
  golden `68b34aced4943deda4ada60ed2d33872ba03ccebc8736fa29e38b5b64ec2e7c2`, patch
  `9a5d343ce72dd626152c2bf4394fd052297248c95e2d0da91e11de9fd620d28c`. `git hash-object --path=…`: acceptance
  `6d6630fbb5fe8cb49608bf39d46b5f82539ecc3d`, golden `8a344a1b635239734807707e3f47396636df4f1e`. All five equal
  the handoff table (`docs/handoff/CORE-003.md:333`, `:338-339`).
- `git apply -R --check docs/proposals/CORE-003-tests-r2.patch`, run as one standalone command (09:45):
  exit 0, no output.
- `tests/architecture/test_imports.py`: `git diff --exit-code HEAD` exit 0. Blob
  `9c18e04813b6970bcc0884de8d4f5db91846d093` equals `HEAD:tests/architecture/test_imports.py`.

### Fidelity to contract v1.3 and the round-5 inventory (task item 3)
- **Item 1 (day everywhere).** AST probe (stdin, no production import): 13 positional `check_entry`
  calls, now at `:299, 303, 306, 310, 316, 322, 323, 326, 334, 342, 347, 349, 395`. They are exactly round
  5's 293–389 list shifted by 6. Each has `DAY` in the third argument slot. The three argument dictionaries
  (`:411`, `:514`, `:674`) contain `day`. All `v13["check_entry"]` calls receive `**arguments` from `:674`.
  0 violations.
- **Item 2 (temporal).** `TEMPORAL_ROWS` (`risk_cases.py:147-154`) equals round 4's six-row table
  value for value. Latches are reached through public transitions, and the two fixtures are distinct:
  daily-only by `update_equity(…, 9925, DAY)`, both by `9800` (`:847-850`). The test asserts the full sorted
  tuple, the `allowed` flag and unchanged state and request (`:859-861`). The rollover control (`:864-873`)
  matches round 4. `stale_state` is in the valid reason list (`:504`). There are TypeError rows for a
  string, None, an int, a `datetime` and the adversarial `_Day` subclass (`:975-988`), an earlier-day
  TimeReversal row, and stale plus a malformed independent argument (`:1171-1181`, `:1131-1168`).
- **Item 3 (bound matrix).** `_NUMERIC_SLOTS` (`:698-728`) covers every row of round 5's slot table, with
  the slot error each row specifies: BadEquity, BadStop, BadPolicy, RiskError. It also covers the
  use-time paths. Rejected forms: 1,001 digits, trailing-zero 1,001 digits (`"0.1"+"0"*1000` normalises to
  one digit), and adjusted ±1,100,001. Accepted edges: 1,000 digits, trailing-zero 1,000 digits,
  `"1."+"0"*999`, adjusted ±1,100,000, and `0E±999999999` in the zero-permitting slots (`lots`, the four
  SizeDecision fields, `cost_per_lot`). The probe confirmed every literal with the round-4 predicate (digits
  of the stored tuple; `abs(adjusted)` only for non-zero). Exclusions (`:772-784`) are only the
  domain-impossible combinations, and they are documented. The five display rows are strengthened to
  exact `RiskError` (`:553-574`), so BadEquity/BadStop cannot mask them.
- **Timing harness (F14).** The Decimal is built in the test thread before `_changed_call`. Context setup
  happens in the worker before `perf_counter()`, and only `function(**arguments)` is timed (`:745-754`).
  There is one measurement per row, with no retries or statistics. The threshold is strict:
  `elapsed < 1.000`. The worker is a daemon thread with `join(timeout=10)` and then an `is_alive()` check
  that fails without waiting again. A return, or any exception other than the exact expected type, fails.
  The environment and elapsed time are recorded through `record_property` and stdout. The rule applies
  only to oversized rows. Flakiness risk under a correct implementation is low: rejection takes
  microseconds against a 1 s budget, and the main thread releases the GIL while joining. The leaked-worker
  slowdown exists only while rows fail (F1). Cosmetic: the environment label hard-codes "via uv" instead
  of detecting it.
- **Item 4 (exact types).** Adversarial subclasses cover the misleading cases: `_RatioDecimal`
  (`as_integer_ratio` returns 1/100), `_Count` (`__ge__` returns False), `_Name` (`__eq__` returns True),
  `_Names` (`__contains__` returns True) and `_Day`. They cover every Decimal slot (60), both count fields,
  side, authorization, reason, tuple members, `halt_clearers`, `reasons`, and the RiskPolicy, HaltState,
  EntryRequest and CostModel object slots, nested `state.policy` included (`:926-1024`). For provenance:
  dict, MappingProxyType and a custom `Mapping` stay valid. The custom one asserts one traversal and one read
  per key, a snapshot independent of the backing dict, and a write-proof proxy (`:1027-1068`). A list of
  valid pairs raises TypeError (`:1071-1073`). A Provenance-subclass value and a non-Provenance value raise
  BadPolicy through a custom Mapping (`:1076-1086`).
- **Item 5 (use-time).** `_v13_calls` builds fresh `replace` copies of `H001_RISK` and `H001_COSTS` for every
  row (`:650-679`). Mutations touch only those copies or fresh request/state objects. No row mutates an H001
  singleton: I checked every `object.__setattr__` target. Request and state defects run across ordinary,
  halted, missing-SL, wrong-side-SL and stale branches. Restart fixtures are experiment-halted with valid
  authorization. No row claims a valid bool latch set to False is detectable.
- **Item 6 (E1 out).** No E1, journal or same-day-history test. `start_experiment` is unchanged. The golden
  docstring now says v1.3, and the golden file still has no imports and no float literals.
- **Oracle** (`uv run --offline --no-sync python -B -`, stdin, Fraction; about 09:50): all 14 `SIZE_ROWS`,
  including `cap_equal`, match at the 28-digit HALF_EVEN display, and `lots × per_lot ≤ R` holds. All 6
  temporal rows, the rollover control, 4 distinct-baseline rows (flags and gate), 4 custom-limit rows, the
  distinct-baseline restart (daily True, base 10500), the new `lots 200 → ("lots_exceed_sized",)` row and the
  zero-exponent `("missing_stop_loss",)` row all match. No mismatch. The first probe run ended with a
  `decimal.Overflow` inside my own `normalize` call (default Emax). I reran it with an unbounded context and
  all literals matched. This was a probe bug, not a test finding.
- **No weakening.** AST multiset compare of HEAD against the working tree, with the `DAY` insertion
  normalised: assertions 45 → 69, `pytest.raises` contexts 17 → 19, `_reject`/`_gate`/`_state`/`_money` calls
  63 → 81. Zero HEAD items are missing. Golden tables: all HEAD rows are present (SIZE 13 → 14; the other five
  tables are unchanged). Five new tables were added. No `skip`, `xfail`, `importorskip`, `.only`, placeholder,
  `type: ignore` or `noqa` appears in either CORE-003 test file (grep over `tests/**/CORE-003/**`).
- **Money comparisons** go through `_money` (`isinstance` Decimal plus numeric `==`), `type(x) is Decimal and
  x == value`, or Fraction inequalities. The only float literals (`0.0`, `1.0`) are rejected inputs, plus the
  timing threshold.
- **Imports:** stdlib (`collections.abc`, `platform`, `sys`, `threading`, `time` plus the v1.2 set), `pytest`,
  and `sochron.costs.H001_COSTS`/`Provenance`. Every name fetched from `sochron.risk` is in the contract's
  API block. `POLICY_FIELDS` is not used.

### Red state (task item 5)
- `uv run --offline pytest tests -q -p no:cacheprovider --tb=no -rfE --deselect tests/acceptance/CORE-003/test_risk_acceptance.py::test_ac06_extreme_equity_rejection_deadline`
  under `timeout -k 5 300` (09:52:25–09:53:02): **382 failed, 266 passed, 1 deselected in 35.74s**, exit 1.
  This uses the implementer's command with `-rfE` instead of `-rN` (reporting only). The counts equal
  the implementer's 09:40 run.
- All 382 failures are in `tests/acceptance/CORE-003/test_risk_acceptance.py`. The same file alone with
  `--tb=line` (09:53:22–09:54:01): 382 failed, 200 passed, 1 deselected in 38.65s. `--collect-only`: 649
  tests (CORE-001 6, CORE-002 6, CORE-003 583, architecture 3, unit costs 14, unit risk 20, unit timebase
  17). So every CORE-001, CORE-002, architecture and unit test passes (66/66).
- Failure causes. I paired each `--tb=line` message with its test ID; both runs use the same order.

  | Cause | Count | Expected v1.3 reason? |
  |---|---|---|
  | v1.2 positional signature: "state must be exactly HaltState, not date" | 2 | yes, `day` argument |
  | v1.2 keyword signature: "unexpected keyword argument 'day'" | 110 | yes, `day` argument |
  | oversized input returned normally ("got None") | 152 | yes, no size bound |
  | oversized check_entry row got TypeError from the old signature | 75 (51 per-slot + 24 at-use) | yes, signature and bound |
  | oversized size_position row got display `RiskError` instead of the slot error | 6 | yes, the bound must precede conversion |
  | worker still alive after `join(timeout=10)` (`model.volume_step` 1E-1100001) | 1 | yes, no bound (see F1) |
  | Decimal subclass not refused (policy fields via HaltState/size_position/start/unknowns/update/restart) | 18 | yes, exact type at use (12 rest on F3's reading) |
  | nested policy not revalidated in `update_equity`/`restart_experiment` ("DID NOT RAISE") | 17 | yes, contract `:98`, `:125`, round 4 item 5 |
  | `BadHaltClear` instead of `BadPolicy` | 1 | **no**, see F2 |

- 100 of the 200 acceptance passes are artefacts of the old signature. They are `check_entry` rows that
  expect `TypeError` and get one only because `day` is unknown to v1.2: 14 subclass, 8 scalar-type, 4
  object-type, 25 request-revalidation, 45 state-revalidation and 4 refusal rows. They do not prove v1.3
  validation yet (see "Not checked"). The other passes are genuine against v1.2: the original AC-01, 02,
  03 and 05 tests, Mapping/copy rows, provenance-value rows, object types outside the gate, the inclusive
  bound and the update/restart revalidation already in v1.2. The `contract_size` exponent passes are F4.
- The isolated extreme-equity run is under F1.
- Implementer unit tests that call `check_entry` with the v1.2 signature: all pass now, because they match
  the v1.2 code. They need migration with v1.3 (outside the locked patch, round 5 item 6). There are 23
  call sites in 10 functions of `tests/unit/risk/test_risk_unit.py`:
  `test_callers_context_is_untouched_by_every_entry_point` (`:59`), `test_states_are_never_mutated` (`:71`),
  `test_gate_uses_current_equity_even_with_a_stale_clear_state` (`:85-86`),
  `test_gate_resizes_from_the_request_stop_and_short_side` (`:91`, `:93`),
  `test_cost_budget_reduces_lots_in_the_gate_too` (`:99`),
  `test_gate_and_halts_follow_the_bound_policy_not_h001_values` (`:133-134`, `:139`),
  `test_sizing_and_gate_respect_a_non_default_volume_step` (`:154`, `:158`),
  `test_gate_thresholds_use_each_baseline_and_the_bound_limits` (`:184-190`),
  `test_cap_boundary_is_not_a_cap_and_volume_max_is_on_the_grid` (`:199`),
  `test_gate_and_halts_revalidate_objects_mutated_after_construction` (`:295-303`).

### Red flags (task item 6)
`bash scripts/controls/red-flags.sh origin/main` (09:56:44–09:56:46): exit 0. The merge-base with `origin/main`
(`3456e7d`) is `47151e8`, with 21 changed paths. Deleted or renamed tests: none. Untracked: none (the
proposal is ignored). Two pattern groups with hits, both inherited, and none in the two patched files:
- **Type checks disabled:** one `# type: ignore[arg-type]` on an intentional negative case in
  `tests/unit/risk/test_risk_unit.py` (explained in `docs/evidence/CORE-003.md`), plus review/evidence prose
  quoting the term.
- **Lint disabled:** prose in `docs/reviews/CORE-003-tests-r1.md` quoting `noqa`.

"Control files touched" lists the two patched locked files (this patch, expected),
`tests/architecture/test_imports.py` (red commit `831fa60`, unchanged here), and, by filename heuristic,
`src/sochron/risk/policy.py` and the security-review file. The secret and order/account-mutation groups are
empty. The scan does not read the ignored proposal. I grepped the two applied files directly (above).

## Not checked (and why)

- **Whether the 100 signature-artefact passes discriminate.** They do so only after the v1.3 signature
  lands. I built no surrogate implementation and ran no mutation testing for the new rows. My reasoning
  is that the adversarial subclasses (`__ge__`, `__eq__`, `__contains__`, `as_integer_ratio`) make an
  accidental TypeError pass unlikely, but this is not shown at runtime.
- **The full suite without `--deselect`.** I did not run it, because it does not terminate (F1). The
  extreme-equity row ran only in isolation under a 45 s outer timeout. Its pass/fail under a correct
  implementation is UNKNOWN.
- **Timing under a v1.3 implementation.** None exists yet, so no interval was measured for a bound-first
  rejection.
- **The faulthandler fix inside pytest** (F1 option a). Only the standalone probe ran.
- **Proposed rows for F2, F4, F5 and F6.** Not executed. Their proofs are reasoned from the red-run
  evidence.
- **Handoff prose.** I checked its digests, commands and counts. I did not re-derive its 236-row interval
  table.
- **Implementation code under `src/sochron/risk`.** Not read. I saw only failure messages (`policy.py:52`,
  `halts.py:53`).
- **E1 obligations (F7, L1–L4, F6), CI, the owner demo, merge and deploy.** Outside this review. No terminal,
  broker, account or network action took place.

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `git status --porcelain`; `git diff --stat`; `git log --oneline -3` | PASS: three expected paths, index empty | fcf77c5 + applied patch | 09:45:22 |
| `sha256sum` ×3; `git hash-object --path` ×2; `git check-ignore -v` | PASS: all digests equal handoff; proposal ignored | same | 09:45:41 |
| `git apply -R --check docs/proposals/CORE-003-tests-r2.patch` (standalone) | PASS: exit 0, no output | same | 09:45 |
| `git diff --exit-code HEAD -- tests/architecture/`; blob compare | PASS: unchanged | same | ~09:46 |
| uv stdin AST probe (`check_entry` day, imports, API names) | PASS: 13 positional calls + 3 dicts with day; 0 violations | same | ~09:47 |
| uv stdin Fraction oracle (golden and new inline rows, bound literals) | PASS: no mismatch (first bound run hit a probe-side Overflow, rerun clean) | same | ~09:49–09:51 |
| `timeout -k 5 300 uv run --offline pytest tests -q -p no:cacheprovider --tb=no -rfE --deselect …extreme_equity_rejection_deadline` | FAIL (expected red): 382 failed, 266 passed, 1 deselected in 35.74s | same | 09:52:25–09:53:02 |
| same on `tests/acceptance/CORE-003` with `--tb=line -rN`; `pytest --collect-only` | FAIL (expected red): 382 failed, 200 passed, 1 deselected in 38.65s; 649 collected | same | 09:53:22–09:54:01 |
| `timeout -k 5 45 .venv/Scripts/python.exe -m pytest "…::test_ac06_extreme_equity_rejection_deadline" -q -p no:cacheprovider --tb=line` | UNKNOWN (did not finish): exit 124, no output | same | 09:55:38–09:56:24 |
| uv stdin faulthandler probe (daemon thread, `as_integer_ratio` of `1E-999999999`) | PASS for the probe: process ended after 5 s with exit 1 and a traceback; main thread stuck in `Thread.start` | same | 09:56:30–09:56:35 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; 2 inherited pattern groups | same | 09:56:44–09:56:46 |
| uv stdin AST multiset compare against `git show HEAD:` copies | PASS: 0 HEAD assertions, raises, helper calls or golden rows missing | same | ~09:57 |
| `git status --porcelain`; `git rev-parse HEAD` before writing this file | PASS: unchanged three paths; HEAD `fcf77c5e71db0c7b796148b4368146a9799bc526` | same | 09:59:16 |

Delivery: review artifact written, unstaged. The patch is **verified byte-exact and fit to commit red**.
CORE-003 v1.3 is not implemented, verified, merged or deployed. Next action: the implementer commits red
(with the evidence above, deselecting the extreme row). The owner decides F1 and F3. Codex closes F2 and F4
(F5 and F6 optional) in a supplemental D-006 patch. The implementer then implements v1.3 and migrates the
listed unit tests.
