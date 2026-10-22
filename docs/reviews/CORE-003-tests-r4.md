# Review CORE-003-tests round 4 · base main · head 34097d9 + applied `CORE-003-tests-r4.patch` (uncommitted) · reviewer Claude Code (fresh session, third session under the role swap; D-006 post-apply review)

Scope: the locked file changed by `docs/proposals/CORE-003-tests-r4.patch` (a fresh Claude session acting as
test author under the owner's role swap, PROGRESS.md `34097d9`). The implementer session applied it under D-006
and has not committed it. I reviewed it against contract v1.6 (`docs/contracts/CORE-003-risk.md`, Tier High),
`docs/reviews/CORE-003-tests-r3.md` (F1, F3), `docs/reviews/CORE-003-r2.md` (F4, F5) and the handoff section
"Tests r4 (Claude test author under the role swap, 2026-10-22)" (`docs/handoff/CORE-003.md:991-1124`). I am
neither the test author nor the implementer. I edited, staged and committed nothing except this file. Scratch
evidence lives under `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\ef81ebc7-fcc9-43d5-886e-a0a727885a31\scratchpad\`
(`mut\` trees, `fh\` watchdog probe, `probe_*.py`, `ast_compare.py`). All times are 2026-10-22, +07:00.

**Ready to commit: yes.** The applied file is byte-exact (SHA256 and Git blob match the handoff; the golden file
is unchanged), the patch reverses cleanly, and the full suite passes on disk: **783 passed in 4.07s**, 0 skipped,
exit 0. tests-r3 F1 and F3 are fixed as that review asked, and the timing harness keeps every v1.4 element. The
v1.6 rows (r2 F4 key type, r2 F5 bound policy, gate input changes) match the contract and fail against the code
before each fix. Nothing was weakened: assertions 88 → 104, `pytest.raises` + `_reject` 44 → 45, tests 34 → 38,
no assertion, test or decorator removed. I also ran the snapshot-then-decide mutation that the handoff left
BLOCKED: the 16 gate input-change rows fail against it.

Two Low findings, neither blocking. F1: a provenance reread *after* the decision is caught only when it
traverses the Mapping, and never in `check_entry`. Two one-line mutants pass all 708 locked rows plus the 29
unit tests, and scratch probes show both are unsafe. F2 (handoff Q1): the 16 int-key rows give two defects at
once and pin TypeError, so a contract-compliant count-first check fails them. My assessment of Q2 is below:
accepting any `RiskError` is consistent with v1.6.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:1494-1499` (`_lower_daily_limit_on_reread`: `traversals > 1`), `:1378-1381` (`swap_on_reread`: same), `:1590-1632` (gate rows; the hook changes the input on the *first* read, `:1614-1615`) | Two scratch mutants of HEAD, one change each. `head_lookup`: `_new_state` re-checks `type(policy.provenance[name]) is Provenance` for the 5 names after the decision (a lookup-only reread). `head_gate_reread`: `check_entry` calls `validate_state(state)` again just before `return _decision(reasons)`. Run in place, the locked file plus `tests/unit/risk` give **737 passed** for each (20:03:05–20:03:12). Probes use only the public API, with a hook that changes something only on a read after the first (a second traversal or a second lookup of a key). `probe_lookup.py` on `head_lookup`: `update_equity(9990)` returns `daily_halted=False` bound to limit `.0001`, although loss 10 ≥ threshold 1 (`consistent=False`): the r2 F5/R5 inconsistency. `probe_gate_reread.py` on `head_gate_reread`: `allowed=True, reasons=()`, while `request.lots` is now `41.66` (honest decision for those lots: `('lots_exceed_sized',)`). HEAD under the same hooks: consistent, request unchanged, 1 traversal (20:00:01, 20:03:29). | An implementation that rereads provenance after deciding: by fixed-name lookups in start/update/restart, or by any path in `check_entry`. | v1.6 `:127` ("read once per call", "no reread of the policy after deciding", "never allowed for a request changed during the check") is enforced only for traversing rereads in start/update/restart. It is not enforced at all in `check_entry`, because every gate attack fires on the first read, so a later read changes nothing. A plausible "defensive" re-validation at the end of the gate passes the whole locked suite while letting caller code change an approved request. HEAD is correct today. This is regression-detection strength, the same class as tests-r3 F1. The handoff discloses the lookup half for start/update/restart (`:1111-1113`) but not the gate half. | Test author: (a) fire the reread actions on a second traversal **or** a second lookup of any key. The locked `_SnapshotMapping` row already treats a second lookup of a key as a second read (`:1046-1064`, asserted at `:1079-1080`). (b) Add gate rows whose hook changes the request or state only on such a later read. Each must either return the honest `()` with the input unchanged, or never return `allowed=True`. Alternatively, assert the v1.6 sentence directly after each public call: 1 traversal and at most 1 lookup per key. | Read profile (`probe_lookup.py` part 2, 20:00:01): HEAD, the iteration copy and the `items()` copy each make exactly 1 traversal and at most 1 lookup per key per call, for all 8 consumers (`RiskPolicy`, `HaltState`, `size_position`, `unknowns`, start, update, restart, `check_entry`). So (a) adds no false failure. `head_lookup` makes 2 lookups per key in start/update/restart and `head_gate_reread` makes 2 traversals, so both would fail. Not run as a test, because the test change belongs to the test author. |
| F2 | Low | question | `tests/acceptance/CORE-003/test_risk_acceptance.py:1478-1480`, `:1487`; contract `:118`, `:127`, `:135` | The int rows add key `1` beside the 5 names: a non-str key (TypeError, v1.6 `:127`) **and** an extra key (BadPolicy, `:135`). The contract leaves the order of several defects open and tests one defect at a time (`:118`). Mutant `head_countfirst` adds HEAD + `if len(snapshot) != len(POLICY_FIELDS): raise BadPolicy` before the key-type loop; `len` on the plain-dict snapshot runs no caller code. It passes 692 rows and fails **exactly the 16 int rows** with `BadPolicy: … got 6 keys` (19:59:01; detail run right after). Pre-F4 code fails the same 16 with `BadPolicy … extra [1]`. | A contract-compliant implementation that checks the key count or set before the key types. | The rows pin an order the contract does not state, so a compliant implementation fails 16 locked rows (handoff Q1). HEAD checks key types first, so the rows pass today. The 16 str-subclass rows are single-defect and unaffected. | Owner chooses one: (a) one contract sentence, "the exact-str key check runs before every other provenance check" (matches HEAD and the r2 F4 reason; recommended, no test change); (b) the int rows accept exactly TypeError or exactly BadPolicy; (c) replace `1` with a single-defect non-str key that hashes and compares equal to a field name, keeping the exact TypeError and the no-equality-call assertion. | (a): the rows then trace to contract text. (b)/(c): rerun `head_countfirst`; expect 708 passed. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

Status of the applied tests against the HEAD implementation (`34097d9`). This is test-patch evidence. It does
not replace the implementation review r3, the owner demo, CI or merge.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Full suite green; sizing rows unchanged; the F4 `size_position` key rows pass. |
| AC-02 | PASS | Existing halt rows pass, plus the r2 F5 bound-policy rows (start, update) and the latch rows (update). |
| AC-03 | PASS | Existing restart rows pass, plus the F9 restart rows with the F1 assertions and the restart variants of both F5 tables. |
| AC-04 | PASS | Gate rows pass, plus the 6 amended F9 rows and the 16 input-change rows (HEAD: 14 exact reason sets, 2 `TimeReversal`). F1 qualifies their regression strength, not the result. |
| AC-05 | PASS | Stop-change rows unchanged. |
| AC-06 | PASS | All matrices pass, including the 32 key-type rows and the timed rows under `capsys.disabled()`. F2 concerns the int rows' contract basis, not the HEAD result. |
| AC-07 | PASS | `uv run --offline pytest tests -q -p no:cacheprovider` → 783 passed, 0 skipped. `tests/architecture/test_imports.py` unchanged. Red-flag secret and order/account groups empty. |

## Checked, nothing found (and how)

### Blocks and the post-run detector (CLAUDE.md, N6)
- After my first read-only command (`git status --porcelain && git diff --stat`, ≈19:47), `check-locked-after.mjs`
  listed exactly `uncommitted M tests/acceptance/CORE-003/test_risk_acceptance.py`. That is the only target of the
  patch just applied (the handoff table expects the golden file unchanged), and the file was already modified when
  this session started. Under CLAUDE.md I verified the expected SHA256 and blob values (all match, below) and continued.
  The detector did not fire again.
- guard-bash blocked a chained command containing `git apply --numstat …` ("git apply must be one standalone literal
  command"). Under the owner's standing "standalone rerun" exception, I reran `git apply --numstat
  docs/proposals/CORE-003-tests-r4.patch` alone, and the other read-only checks separately.
- guard-bash blocked `cp whichrisk.py pytest.ini "$t/"` (a variable destination). Under the owner's headless-reviewer
  exception (a variable scratchpad path becomes a literal path), I reran it with literal scratchpad paths. The
  copied files are my own scratch files, not repository files.
- No locked file was copied or edited. Mutation runs execute the repository's test file in place (the method the
  owner accepted in v1.6). The F3 and Q2 probes load it in place with `importlib`.

### Hashes and patch state (items 1–2)
- `git status --porcelain`: exactly ` M docs/handoff/CORE-003.md` and ` M tests/acceptance/CORE-003/test_risk_acceptance.py`.
  Nothing untracked (`git ls-files --others --exclude-standard` empty); index empty; `git check-ignore -v` →
  `.gitignore:10:docs/proposals/`. `git diff --check`: exit 0.
- `git diff --numstat`: handoff +135/−0 (append-only), acceptance +260/−27. `git apply --numstat` on the patch:
  `260 27` for the acceptance file only, matching the handoff.
- `sha256sum`: acceptance `fa1bde04706d177bb13a4da14e00751ff67c85816537e8417932e59d280c94df`, golden
  `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83`, patch
  `9d290dc9ab17b75c0098f51a894f4b50dccc155b2ebf65d3e33b30304285dc27`. `git hash-object` (plain and `--path=`):
  acceptance `d2ba11db5958d817c5830fc54a3eda5fa3e7ce35`; golden `d4800f296435d10344eb68a468f6ab132e1fbaf2`, equal to
  `HEAD:` (unchanged). All equal the handoff (`docs/handoff/CORE-003.md:1010`, `:1016-1017`).
- `git apply -R --check docs/proposals/CORE-003-tests-r4.patch`, standalone: exit 0, no output (by 19:48:10).
- The file is ASCII, LF only, one final newline, no tabs or trailing spaces (scratch byte count: CR 0, non-ASCII 0).

### Architecture test (item 4)
- `git diff --exit-code HEAD -- tests/architecture/`: exit 0. Blob `9c18e04813b6970bcc0884de8d4f5db91846d093` equals
  `HEAD:tests/architecture/test_imports.py`; SHA256 `259ac6d4…87933b195`.

### Fidelity (item 3)
- **tests-r3 F1.** `_HookMapping` (`:1293-1327`) runs the action from `keys()`, `__iter__`, `__getitem__` and
  `__len__`, and `keys()` returns a live `KeysView(self)`, so the mixins and every copy strategy run it. The 6 gate
  rows assert `hook.calls >= 1` and that the attack took effect (`:1364-1366`). The 2 restart rows assert the hook
  was read (`:1395-1396`). The restart swap stays "any traversal after the first", as tests-r3 offered. Every earlier
  F9 assertion is kept. In place against HEAD with an iteration copy and an `items()` copy (`head_iter`,
  `head_items`): **708 passed** each, so the tests-r3 false failure is gone. Against pre-F9 code (`b9f0396`) with the
  same two read paths: all 8 F9 rows fail, and each failure shows the attack ran: side/policy → `allowed is False`
  fails (4), `nan_lots` → plain `ValueError: cannot convert NaN to integer ratio` (2), restart → the substituted
  `risk_per_trade 0.5` policy returned (2). The vacuous pass of tests-r3 F1(b) is gone.
- **tests-r3 F3.** `_timed_rejection` (`:737-778`) arms, starts, joins and cancels inside `with capsys.disabled():`.
  The v1.4 elements are intact: `faulthandler.dump_traceback_later(20, exit=True)` before `worker.start()`
  (`:762`, `:764`), `cancel_dump_traceback_later()` in `finally` (`:766-767`), `Thread(..., daemon=True)` (`:758`),
  `join(timeout=10)` (`:765`), the `is_alive()` check (`:768-771`), `perf_counter()` around `function(**arguments)`
  only (`:747-756`), exact error type (`:776`) and strict `elapsed < 1.000` (`:777`). The four timed tests request
  `capsys`. pyproject sets no `faulthandler_timeout`, so the cancel cannot clear a pytest timer.
- **v1.6 / r2 F4 rows** (`:1434-1491`, 32 rows). A `str` subclass equal to `"risk_per_trade"` whose `__eq__` records
  the call and lifts `risk_per_trade` to 5, plus an int key; dict and proxy; construction and all 7 consumers named in
  `:126`. Each row expects exact TypeError, no equality call, and `.0025` kept. Building the fixture runs no equality
  test (`:1477`), and the call runs none either (`:1489`). An `isinstance(key, str)` check, a construction-only check or a dict-only check would each fail
  these rows. Contract basis of the int rows: F2.
- **v1.6 / r2 F5 rows** (`:1494-1586`, 10 rows). The hook is planted before the call. A reread lowers
  `daily_loss_limit` to `.0001`. The result must be the same policy object with the H001 values and the honest
  state. The latch rows check that a lowering that lands on the call's single read is decided with (latch True), kept
  through recovery, and refused by the gate with `("daily_halt",)`. This matches `:127` ("read provenance once per
  call, before every other field"; "build the result from the validated values"). Limit: F1.
- **v1.6 gate rows** (`:1590-1632`, 16 rows). The honest precondition is allowed; the hook changes one input from
  inside the read; the call must raise a `RiskError` or return the exact reasons for the changed input, and
  `state_day` must raise. The hook must have run and the change must be in place. Snapshot-then-decide mutant
  (`head_snapshot`: shallow copies of request, state and policy before the real gate): **18 failed** = all 16 rows
  (`allowed=True` where reasons were expected; `state_day` "must raise TimeReversal") plus the 2 F9 `nan_lots` rows.
  This fills the run the handoff left BLOCKED. Limit: F1.
- **Oracle** (`uv run --offline --no-sync python -B -I -`, Fraction, ≈19:55): 11 checks, all PASS: distance 12;
  sized .02; 41.66 on grid and above sized; rate .0001 sizes 0; daily threshold 76.5 ≤ 200; 9990 → 10 < 75 at .0075
  and ≥ 1 at .0001; experiment 10 < 200; 9800 latches both; recovered 10000 against base 9990 adds no experiment loss.
- **No weakening** (`ast_compare.py`, in memory against `git show HEAD:`; ≈19:54). Assertions 88 → 104 with every
  old assert statement present; `pytest.raises` 19 → 19, `_reject` 25 → 26; tests 34 → 38, none removed; no
  decorator changed; no non-parametrize marks. The 27 removed lines are the docstring, the import, 5 signatures and
  5 calls (now with `capsys`), the 5 harness lines (now inside `capsys.disabled()`), the old `keys()`-only hook body
  and its `count` lambdas. Each is replaced by an equal or stricter line.
- **Disabled tests, imports, money.** Grep of both CORE-003 test files for skip, xfail, importorskip, `.only`,
  `type: ignore`, noqa, TODO, FIXME, placeholder, pragma, deselect: no hits. The only new import is stdlib
  `KeysView`. Every `sochron.risk` name used is in the `v13` fixture and the contract's API block, and `H001_COSTS`
  follows the existing in-function pattern. Money comparisons go through `_money`, Decimal `==` or `_state`.
- **Flakiness and memory.** The new rows have no deadline and use 5-key dicts and small objects. The hook actions are
  idempotent. Timed rows still reject in milliseconds at HEAD (suite 4.07 s). `capsys.disabled()` only suspends
  capture around the worker; the worker prints nothing.
- **Cosmetic, not a finding.** Several new comments lost a space before numbers ("of10000", "Loss10", "baseline10000",
  `:1519`, `:1529`, `:1533`). Under `-q`, a watchdog traceback names the test function and line but not the
  parametrized row ID. The contract asks only for a traceback and a non-zero exit.

### Full suite (item 5)
- `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` (19:53:40–19:53:45): **783 passed in 4.07s**,
  exit 0, no skips or deselections. That is 725 previous tests plus 58 new rows (32 + 6 + 4 + 16).

### Mutation spot-check (item 6)
Each tree is `git archive <rev> src` in scratch, plus my `pytest.ini` (`pythonpath = src`) and a plugin
(`whichrisk.py`) that printed the loaded `sochron.risk` path, which was the scratch tree every time. Command:
`timeout 300 uv run --offline --no-sync --project <repo> --directory <tree> python -B -m pytest <repo>/tests/acceptance/CORE-003/test_risk_acceptance.py -q -p no:cacheprovider -c pytest.ini --rootdir . -p whichrisk --tb=no -rf`.
A `diff -r` against the HEAD tree confirmed each mutant differs only as described.

| Risk code | Result | Failing rows (cause) | Time |
|---|---|---|---|
| HEAD copy (control) | 708 passed | — | 19:57:47–19:57:50 |
| `82844d1` = `a6fde90~3` (before F4 `073ab70`) | **42 failed**, 666 passed | 32 key rows (16 int → `BadPolicy … extra [1]`; 10 subclass → `DID NOT RAISE TypeError`; 6 → `BadPolicy … got 5` after the key's side effect); 6 F5 bound rows (`.0001` in the result); 4 latch rows (start's own reread lowered the limit) | 19:57:57–19:58:00 |
| `073ab70` (before F5 `d7b45b5`) | **10 failed**, 698 passed | exactly the 6 + 4 F5 rows | 19:58:36–19:58:39 |
| `b9f0396` (before F9) | **50 failed**, 658 passed | 8 F9 rows, 32 key rows, 10 F5 rows | 19:58:39–19:58:42 |
| `b9f0396` + iteration copy / + `items()` copy | **50 failed** each, same set | F9 rows fail because the attack ran (see Fidelity) | 19:58:42–19:58:48 |
| HEAD + iteration copy / + `items()` copy | 708 passed each | — (tests-r3 F1 false failure fixed) | 19:58:48–19:58:55 |
| HEAD + snapshot-then-decide gate | **18 failed**, 690 passed | 16 gate input-change rows + 2 F9 `nan_lots` rows | 19:58:55–19:58:58 |
| HEAD + count-first key check | **16 failed**, 692 passed | exactly the 16 int-key rows (F2) | 19:59:01–19:59:04 |
| HEAD + lookup-only reread in `_new_state` | 708 passed (+29 unit: 737) | none (F1) | 19:58:58; 20:03:08–20:03:12 |
| HEAD + `validate_state` again at the end of `check_entry` | 708 passed (+29 unit: 737) | none (F1) | 20:03:05–20:03:08 |

### Watchdog probe (tests-r3 F3)
`fh\test_watchdog_probe.py` loads the locked file in place and drives its `_timed_rejection` with a worker that
holds the GIL in one C call (`sum(range(10**14))`). A control test rebuilds the pre-r4 arm/start/join/cancel
sequence without `capsys.disabled()`. Both ran from the repo root with
`timeout 120 uv run --offline pytest <probe>::<test> -q -p no:cacheprovider -c pyproject.toml --rootdir .`:
- amended harness (20:00:38–20:00:58, recount 20:01:30–20:01:51): exit 1 after 20 s with **46 lines**, starting
  `Timeout (0:00:20)!`, with both thread stacks through the locked file (`:749` in `invoke`, `:764` in
  `_timed_rejection`, called from the test function);
- old pattern (20:01:10–20:01:30): exit 1 after 20 s with **0 lines**.

### Red flags (item 7)
`bash scripts/controls/red-flags.sh origin/main` (20:01:56–20:01:58): exit 0; merge-base `47151e8`, 26 changed
paths; deleted or renamed tests none; untracked none (the proposal is ignored). 2 pattern groups with hits, both
inherited, none in the patched file:
- **Type checks disabled:** the two intentional `# type: ignore[arg-type]` negative cases in
  `tests/unit/risk/test_risk_unit.py`, plus evidence, handoff and review prose quoting the pattern (including the new
  handoff section's grep list).
- **Lint disabled:** prose quoting `noqa`.
"Control files touched" lists the locked acceptance and golden files (expected), `tests/architecture/test_imports.py`
(red commit, unchanged here), and, by filename heuristic, `src/sochron/risk/policy.py` and the two security review
files. The secret, secret-like, destructive/bypass, placeholder/mock and order/account groups are empty.

### Owner questions from the handoff (Q1, Q2)
- **Q1 (int keys expect TypeError).** The test author's concern holds against the contract text: see F2. Under
  `:118` an extra int key is a two-defect input, and the mutation run shows a compliant count-first check failing
  16 rows. I recommend option (a), one contract sentence that orders the key-type check first. It matches HEAD, the
  r2 F4 reason and the owner's instruction recorded in the handoff, and needs no test change.
- **Q2 (gate input-change rows accept any `RiskError`).** Consistent with v1.6, and I recommend keeping it.
  `:127` allows "check the request after state/policy **or** refuse with the error per the table". The table names
  no error for a valid value changed during validation, so no single subclass can be pinned without adding a
  requirement. The rows still reject `allowed=True`, any non-`RiskError` exception and, for `state_day`, any decision.
  This mirrors the owner-accepted F9 policy row (`:1357-1360`). At HEAD the leniency is never used:
  `probe_gate_outcomes.py` (20:04:08) shows 14 rows return exactly the expected reasons and both `state_day` rows
  raise `TimeReversal`. Optional: one contract phrase ("any `RiskError`") would remove the "ตามตาราง" ambiguity.

## Not checked (and why)
- **The F1 fix inside the locked file.** The test change belongs to the test author. My evidence is the two mutants
  and the read-profile probe.
- **Other mutants for v1.6 sentences**, such as an update that reads `daily_loss_limit` before the provenance (the
  latch rows should catch it). I reasoned it from the row design but did not build it.
- **The watchdog firing on a real GIL-holding regression inside the risk code.** I proved only the scratch probe
  through the locked harness.
- **Handoff prose beyond its numbers.** I checked its digests, counts (+260/−27, 708/783, 88 → 104, 44 → 45,
  34 → 38), the mutation table, the watchdog line counts and Q1/Q2. I did not re-derive every sentence.
- **The implementation itself beyond these runs.** I read `policy.py:150-259`, `halts.py`, `gate.py:95-179` and the
  F4/F5 fix diffs, only to build the mutants. Implementation review r3 stays separate.
- **CI, the owner demo, merge, deploy, `node scripts/controls/check-locked-paths.mjs`** (not requested), and E1
  obligations (L1–L5, F7), which cannot be tested through the pure API. No terminal, broker, account or network
  action took place.

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `git status --porcelain`; `git diff --stat` | PASS: exactly the two expected paths (detector fired once; see Blocks) | 34097d9 + applied patch | ≈19:47 |
| `sha256sum` ×3; `git hash-object` (plain and `--path=`); `git rev-parse HEAD:<golden>` | PASS: all equal the handoff | same | ≤19:48:10 |
| `git apply -R --check docs/proposals/CORE-003-tests-r4.patch` (standalone) | PASS: exit 0, no output | same | ≤19:48:10 |
| chained command with `git apply --numstat` | BLOCKED by guard-bash (F21); rerun standalone | same | ≈19:48 |
| `git apply --numstat …` (standalone); `git check-ignore -v`; `git diff --numstat`; `file`; CR count | PASS: 260/27 one file; ignored; handoff +135/−0; ASCII, 0 CR | same | 19:48:10 |
| `git diff --exit-code HEAD -- tests/architecture/`; blob compare; `git diff --cached`; `git diff --check`; untracked list | PASS: unchanged; index empty; clean; none | same | ≈19:53 |
| `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: 783 passed in 4.07s, exit 0 | same | 19:53:40–19:53:45 |
| `uv run … python -B -I ast_compare.py` | PASS: nothing removed; 88 → 104 asserts | same | ≈19:54 |
| grep for disabled-test markers (both CORE-003 files) | PASS: no hits | same | ≈19:55 |
| uv stdin Fraction oracle (11 checks) | PASS | — | ≈19:55 |
| `cp … "$t/"` into scratch trees | BLOCKED by guard-bash (variable path); rerun with literal paths | — | ≈19:57 |
| in-place mutation runs (table above) | as tabulated | scratch trees | 19:57:47–19:59:04, 20:03:05–20:03:12 |
| `probe_lookup.py` (4 trees) | `head_lookup` inconsistent; HEAD/iter/items consistent, 1 traversal, ≤1 lookup per key | — | 20:00:01–20:00:02 |
| watchdog probe (amended ×2, old pattern) | exit 1 each; 46 / 0 / 46 lines | — | 20:00:38–20:01:51 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; 2 inherited groups | same | 20:01:56–20:01:58 |
| `probe_gate_reread.py` (HEAD, `head_gate_reread`) | HEAD unchanged request; mutant allowed with lots 41.66 | — | 20:03:29 |
| `probe_gate_outcomes.py` (HEAD) | 14 exact reason sets, 2 `TimeReversal` | same | 20:04:08 |

Delivery: review artifact written, unstaged. The applied test patch is **verified byte-exact and fit to commit**.
With it, the HEAD implementation passes the v1.6 tests on disk. CORE-003 is not yet verified by implementation
review r3, CI or the owner demo, and is not merged or deployed. Next action: the implementer commits the test file
and the handoff (with this review). The owner decides F2 (recommended: one contract sentence) and whether F1 goes
into a later test patch. Implementation review r3 then re-checks r2 F4/F5.

Ready to commit: yes
