# Review CORE-003-tests round 3 · base main · head e510726 + applied `CORE-003-tests-r3.patch` (uncommitted) · reviewer Claude Code (fresh session, D-006 post-apply review)

Scope: the two locked test files changed by `docs/proposals/CORE-003-tests-r3.patch` (Codex, test-author role),
which the implementer session applied under D-006 on 2026-10-22 and has not committed. I reviewed them
against contract v1.5 (`docs/contracts/CORE-003-risk.md`, Tier High; `git diff fcf77c5..HEAD` for the v1.4/v1.5
changes), `docs/reviews/CORE-003-tests-r2.md` (F1, F2, F4–F6), `docs/reviews/CORE-003-r1.md` (F1–F3),
`docs/reviews/CORE-003-security-pre-r2.md` (F9, F11, F12) and the section "Tests r3 for contract v1.4" of
`docs/handoff/CORE-003.md`. I did not edit, stage or commit any repository file except this one. Scratch evidence
lives under `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\8f32b926-0467-49cf-8932-b09a99722a66\scratchpad\`
(`mut\` trees and run logs, `fh\` watchdog probes, `redflags.txt`). All times are 2026-10-22, +07:00.

**Ready to commit: yes.** The applied files are byte-exact (both SHA256 values and both Git blobs match the
handoff), the patch reverses cleanly, and the ordinary full suite passes on disk: **723 passed in 3.15s**,
0 skipped, exit 0. This closes the disk-run evidence the handoff left BLOCKED. The timing harness matches v1.4
word for word. tests-r2 F2, F4, F5 and F6 are addressed as that review asked (F4 with a stronger design than
the one suggested). Every new numeric expectation agrees with an exact Fraction oracle. Nothing was deleted or
weakened: 5 removed lines, each replaced by an equal or stricter line; assertions 69 → 88. Mutation runs
show that the new rows fail against the pre-fix code for r1 F1–F3 (62 of 62 expected rows) and security F9
(8 of 8). The F11 row does not (F2 below).

Four Low findings, none blocking. F1: the F9 attack fires only through `keys()`, so a contract-compliant
read by iteration makes 2 rows fail falsely and 6 pass without the attack running. F2: the F11 deadline row
passes against the old linear check (0.150 s against a 1.000 s limit); Codex disclosed this. F3: when the new
watchdog fires under the project's own pytest command, the process exits 1 with no output at all, so the
"with traceback" half of v1.4 is not visible. F4 (question): the F9 rows add two expectations that the
contract does not state in words.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:1305-1307` (callback only in `keys()`), `:1329-1330`, `:1340` | In-memory variant: scratch plugin `mut\head\iterread_plugin.py` shadows `dict` inside `sochron.risk.policy`, so a non-dict provenance Mapping is copied by iteration (`(k, m[k]) for k in m`), still read once into a snapshot as the contract requires. Result: **2 failed, 648 passed**. The failures are exactly `[nan_lots-False]` and `[nan_lots-True]`, with `GateDecision(allowed=True, reasons=())` at `:1340` (11:10:15–11:10:17). The `_SnapshotMapping` construction rows still pass, because they count `__iter__`, not `keys()`. At HEAD the rows pass only because `src/sochron/risk/policy.py:187` copies with `dict(...)`, which happens to call `keys()`. | An implementation that reads the provenance Mapping at use through `__iter__`/`__getitem__` instead of `keys()`. | (a) False failure: a contract-compliant read fails 2 locked rows. The attack never runs, yet the row still demands a refusal for a request whose honest decision is "allowed". (b) Vacuous pass: with the same read path, the side, policy and both restart rows pass without any attack, so a later return of the F9 ordering bug would go unseen. Today the rows work: they all fail on `5d939a3` (see the mutation table). | Codex: fire the callback from the primitives that every copy strategy uses (`__iter__`, `__getitem__`, `__len__`; all three actions are idempotent). After the call, assert that the hook ran at least once. For the restart row, keep "swap on any read after the first", or swap on every read: pinning still separates the pre-fix code. | Rerun with `iterread_plugin.py`: all 8 rows must pass. Rerun against `5d939a3`: all 8 must still fail. Not run, because the test change belongs to Codex. |
| F2 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:1369-1375`; handoff "the old linear check may still meet 1 second at this size" | The repo's test ran in place against the pre-fix risk package (`5d939a3`, linear `len(value.as_tuple().digits)`). The row **passes** with BadEquity in 0.149623600 s; HEAD takes 0.002677800 s (11:06:44–11:06:45). Peak traced memory of the call under `tracemalloc`: 269.5 MiB before the fix, 12.0 MiB at HEAD (11:12:01–11:12:02). | The pre-fix linear digit count, or any other bound check that is linear in time or allocates per digit. | The locked suite does not detect the F11 regression. Only the implementer's unlocked unit test does (`tests/unit/risk/test_risk_unit.py:419`, < 0.05 s). The contract's only criterion is < 1.000 s, and meeting it would need about 2×10⁸ digits (~1.1 s and ~1.9 GiB per security-pre-r2), which is too heavy for routine runs. No contract rule passes falsely: at 30M digits the old code does meet the deadline. | Owner chooses: (a) accept, and record that the locked row is a deadline sample and that F11 regression detection rests on the unit test; or (b) add one contract sentence: rejecting an oversized Decimal must not allocate memory in proportion to its digit count, measured as the `tracemalloc` peak of the timed call (e.g. < 64 MiB for the 30M-digit sample). Codex then adds the assertion. | For (b): measured 269.5 MiB before the fix and 12.0 MiB at HEAD, so a 64 MiB limit leaves about 5× margin on each side. Not run as a test. |
| F3 | Low | confirmed | `tests/acceptance/CORE-003/test_risk_acceptance.py:758-764`; contract `:123` ("process จบพร้อม traceback และ exit code ไม่เป็น 0") | Scratch probe `fh\test_watchdog_probe.py` uses the same pattern: a daemon worker in one GIL-holding C call (`sum(range(10**11))`), `dump_traceback_later(3, exit=True)` before `start`, and `cancel` in `finally`. With the project's command form (`pytest -q -p no:cacheprovider`, default capture), the process exits 1 after ~3 s with **0 lines of output**: no traceback, no test name, no summary (11:07:45–11:07:49). With `-s` the full traceback appears (11:07:58–11:08:01). `file=sys.__stderr__` is still silent, because pytest's fd capture redirects fd 2 (11:08:36–11:08:39). Wrapping arm/start/join/cancel in `with capsys.disabled():` prints the full traceback and exits 1 (11:08:39–11:08:42). | Any regression on an oversized row that holds the GIL, e.g. a bound check moved after the rational conversion. | Half of the v1.4 promise holds: the run fails instead of hanging, and a hang can never pass. But the failure is anonymous. AC-07's command ends with exit 1 and no output, so nobody can see which row failed or why, and the run could be misreported as an environment failure (BLOCKED) instead of FAIL. The harness uses the contract's literal call, so this is a mechanism gap, like tests-r2 F1. | Codex: inside `_timed_rejection`, run arm/`start`/`join`/`cancel` under `capsys.disabled()` (callers pass `capsys`). Alternatively the owner accepts exit-code-only. Either way, one clause in contract `:123` (owner) keeps the text and the test aligned. | Probe above: with `capsys.disabled()` the watchdog exit printed 44 lines, including every thread's stack; without it, 0 lines. Not tried inside the locked file. |
| F4 | Low | question | `tests/acceptance/CORE-003/test_risk_acceptance.py:1311-1341`, `:1344-1366`, `:1218`, `:1360`; contract `:4` ("F9, F11 แก้ในโค้ด ไม่เปลี่ยน contract"), `:89`, `:98`, `:125-126` | The 8 F9 rows add two expectations that the contract text does not state in words. (1) `check_entry` must never return `allowed=True`, nor raise anything other than a `RiskError`, when caller code running during validation (a provenance Mapping) changes the request or swaps `state.policy`. The nan_lots row in particular rejects a snapshot-then-decide design that would allow the validated snapshot while the request object now holds NaN. (2) `restart_experiment` must return the *identical* validated policy object (`is`), which `:1218` also asserts. The contract says "policy เดิม", and the older rows compare with `==`. Both expectations match the owner-accepted security-pre-r2 F9 negative test and the F9 fix, and both point in the safe direction. | An implementer who reads `:98` and `:125-126` literally. | Same class as tests-r2 F3: tests are part of the contract (AGENTS.md), so these rows add requirements that the owner approved as a code fix, not in contract wording. | Owner: one sentence in the contract (v1.6), e.g. "caller code that runs while a public function reads its inputs cannot change the decision: the gate never allows a request or state that is invalid when it returns, and `restart_experiment` returns the policy object it validated". Alternatively, Codex relaxes `is` to `==`; the existing `risk_per_trade` check still separates the pre-fix code. | After the sentence lands, the rows trace to the contract text. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

## AC status

Status of the applied tests against the HEAD implementation (`e510726`). This is test-patch evidence. It does
not replace the Codex implementation review r2, the owner demo, CI or merge.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Full suite green, including the new golden row `inclusive_coefficient_equity`, the extreme-exponent zero budget and the v1.5 F12 sizing `RiskError`; the oracle agrees. |
| AC-02 | PASS | All existing halt rows pass, plus the 1,000-digit equity of 1 through `update_equity` (both latches set, baselines 10000). |
| AC-03 | PASS | All existing restart rows pass, plus the 1,000-digit equity restart and the F9 restart identity rows. |
| AC-04 | PASS | All gate rows pass, plus the 42 model-domain rows, the 6 callback rows and the F12 gate rows (`()` and `("lots_exceed_sized", "lots_not_on_grid")`). |
| AC-05 | PASS | Stop-change rows unchanged; the exact-type tightening of `_reject` passes. |
| AC-06 | PASS | All matrices pass under exact-type `_reject`: oversized rows (timed), huge negative counts (10 rows), model domain, F11 deadline. F2 and F3 qualify the strength of that evidence, not the result. |
| AC-07 | PASS | `uv run --offline pytest tests -q -p no:cacheprovider` → 723 passed, 0 skipped. `tests/architecture/test_imports.py` unchanged and passing. Red-flag secret and order/account groups empty. |

## Checked, nothing found (and how)

### Blocks and the post-run detector (CLAUDE.md, N6)
- After my first read-only command (`git status --porcelain && git diff --stat`), the post-run detector
  `check-locked-after.mjs` listed exactly `uncommitted M tests/acceptance/CORE-003/test_risk_acceptance.py` and
  `uncommitted M tests/golden/CORE-003/risk_cases.py`. These are the target files of the patch just applied,
  and nothing else was listed. Under CLAUDE.md I verified every expected SHA256 and blob against the handoff
  (all match; see "Hashes") and continued. The detector did not fire again.
- guard-bash blocked `git -C <repo> apply -R --check …` as "must be one standalone literal command" (F21).
  Under the owner's standing "standalone rerun" exception, I reran the same action alone from the repo root:
  `git apply -R --check docs/proposals/CORE-003-tests-r3.patch`.
- guard-bash blocked `mkdir -p "$S/$name/…"` because the scratch path was a shell variable. Under the owner's
  headless-reviewer exception (a variable scratchpad path becomes a literal path), I reran it with literal
  scratchpad paths.
- A permission rule **denied** `cp tests/acceptance/CORE-003/test_risk_acceptance.py <scratch>` (and the golden
  copy). No exception covers this, so I did not copy the locked files by any other means. For the mutation
  runs I used the method the task suggests instead: the old `src` packages sit in scratch trees, and pytest
  runs the repo's test file **in place**, as the ordinary suite does, with the working directory set to that
  tree (`uv run --offline --no-sync --project <repo> --directory <tree> python -B -m pytest <repo test file> -c pytest.ini --rootdir .`).
  No copy of a locked test file exists outside the repository. **Owner: please confirm this is acceptable.
  If it is not, discard the mutation evidence below; the rest of the review does not depend on it.**

### Hashes and patch state (items 1–2)
- `git status --porcelain` (10:57:19): exactly ` M docs/handoff/CORE-003.md`,
  ` M tests/acceptance/CORE-003/test_risk_acceptance.py`, ` M tests/golden/CORE-003/risk_cases.py`. Nothing
  untracked; `git diff --cached --name-only` empty; `git check-ignore -v` → `.gitignore:10:docs/proposals/`.
- `git diff --stat` / `--numstat`: handoff +138/−0 (append-only); acceptance +222/−4; golden +24/−1, matching the
  handoff's "+222/-4; +24/-1". `git diff --check`: exit 0.
- `sha256sum` (10:57:39): acceptance `d362fff230678f01c1705bfada9b5cd6eadf05b232248235c2a42ba237684119`, golden
  `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83`, patch
  `bea1632d3be31e57b6d7561bdbe446b69e9453b6e9a89c5c0de0aa0d729cf7fe`. `git hash-object --path=<p> <p>`: acceptance
  `2e3d154abce9042f7521393e7a27b24875914bb8`, golden `d4800f296435d10344eb68a468f6ab132e1fbaf2`. All five equal
  the handoff (`docs/handoff/CORE-003.md:849`, `:854-855`). Both files are ASCII, LF only, one final newline.
- `git apply -R --check docs/proposals/CORE-003-tests-r3.patch`, standalone (completed by 10:57:58): exit 0, no output.

### Architecture test (item 4)
- `git diff --exit-code HEAD -- tests/architecture/`: exit 0. Blob `9c18e04813b6970bcc0884de8d4f5db91846d093`
  equals `HEAD:tests/architecture/test_imports.py`; SHA256 `259ac6d4…5b933b195` equals the handoff's unchanged value.

### Fidelity (item 3)
- **Timing harness (tests-r2 F1 / v1.4).** `:758-764`: `Thread(target=invoke, daemon=True)`, then
  `faulthandler.dump_traceback_later(20, exit=True)` *before* `worker.start()`, then `try: start(); join(timeout=10)`
  with `finally: faulthandler.cancel_dump_traceback_later()`, then the `is_alive()` check (`:765-768`).
  `perf_counter()` brackets only `function(**arguments)` (`:747-756`), the hostile context is set up before the
  clock starts, the exception type must be identical (`:773`) and the limit is strict `elapsed < 1.000` (`:774`).
  Everything else in the harness is unchanged from HEAD. pytest's own `faulthandler_timeout` is unset, so the
  cancel cannot clear another timer. On a timeout, see F3.
- **tests-r2 F2.** `:1167-1169`: only the `restart_experiment` row replaces `()` with `("owner", "owner")`, so
  `"owner"` stays authorized and BadPolicy is the only rule that applies. The empty-tuple rows for `check_entry`
  (5 branches) and `update_equity` remain. Cosmetic: the parametrize ID still reads `value17` (the `()` row).
- **tests-r2 F4.** Golden `:193-196` and test `:800-809`. The compensating in-bound distance (and entry/stop)
  keeps per-lot risk at 0.1 or 10, so a missing model exponent bound produces a normal result rather than
  hiding behind the display `RiskError`. Oracle: `1E-1100001 × 1E+1100000 = 1/10` → lots 200 capped, actual 20;
  `1E+1100001 × 1E-1100000 = 10` → lots 2.5, actual 25. All compensating literals are in bound
  (|adjusted| ≤ 1,100,000). The exact no-bound arithmetic takes 0.307 s / 0.306 s (11:07:21–11:07:22), so a
  no-bound implementation would return within the join window and fail cleanly with "expected RiskError, got
  None". This does not rely on the watchdog, which makes it stronger than the timed ±999999999 rows the review
  suggested.
- **tests-r2 F5.** `_reject` (`:111-114`) now asserts `type(caught.value) is error`. I checked every caller:
  each expects exactly the error that the contract table names for a single defect. Base-`RiskError` rows are
  side, counts, lots, `SizeDecision`/`GateDecision` consistency, model fields and display range; `TypeError`
  rows are wrong types. No caller relies on subclass acceptance, and the multi-defect rows isolate one defect
  (`:446-448`).
- **tests-r2 F6.** Golden `:14-16` (equity `"0.1"+"0"*999` → lots 0, R .00025, per 1200, `below_min_volume`);
  `:1203-1219` (equity `"1."+"0"*999` through `update_equity` and `restart_experiment`);
  `:1222-1230` (budget `"0."+"1"*1000` through the gate: .02 allowed, .03 `lots_exceed_sized`). All
  three are in-bound edges with no deadline, as round 4 required.
- **v1.4 model domain (r1 F1).** `:1233-1253`: contract_size/volume_step/volume_min at 0 and −0.01, and
  volume_max 0.005 < min 0.01, through `size_position` and `check_entry` in the ordinary, halted, missing-stop,
  wrong-side and stale branches: 7 × 6 = 42 rows, exact `RiskError`. Each row mutates a fresh `replace` copy,
  never `H001_COSTS`. This matches contract `:127` ("ก่อนเลือก branch หรือรวบรวมเหตุผล").
- **v1.4 policy revalidation (tests-r2 F3).** The existing direct and nested rows are kept. The new
  huge-negative-count rows (`:1274-1286`) reach `RiskPolicy`, `HaltState`, `size_position`, `start_experiment`,
  `unknowns` and nested `state.policy` in `check_entry`, `update_equity` and `restart_experiment`. These are
  exactly the consumers named in `:126`.
- **r1 F2 / F3.** `:1255-1271`: zeros `0E-999999999999999999` and `-0E-999999999999999999` give the plain H001
  sizing tuple and an allowed gate under a hostile context. `:1274-1286`: `-(10**5000)` is built in the test
  body (no pytest ID stringification), with RiskError for exposures and BadPolicy for the policy count.
- **v1.5 F12.** `:1378-1399`, golden `:198-207`. The exact-lots `RiskError` from `size_position`, the gate allowing
  9×step and refusing 200 with both reasons all match contract `:140`.
- **security F9 / F11.** The rows are present and sound against HEAD; see F1, F2 and F4 for their limits.
- **Oracle** (`uv run --offline --no-sync python -B -`, stdin, Fraction; 11:03:41–11:03:43 and 11:03:51). 43
  computed checks over two runs, all PASS (one further line only restated the restart rule): the golden row; both compensation rows; step/sized/permitted digit counts (1000/1002/1000)
  and values (`199·step`, `9·step`); floor 357 and cap 199; grid membership; 200 off grid and above the sized
  lots; permitted risk < 6301 < 250000; the halt arithmetic for equity 1; budget 1200 < per < 1201 with
  sized .02; the zero literals; F9 `rate 5 → 41.66` and the wrong-side stop; `-(10**5000)` exceeding the
  4,300-digit limit; F11 `adjusted == -1`. The first run stopped at my own `str()` of the 5,001-digit int,
  which hit that same limit; this was a probe bug, rerun clean.
- **No weakening.** The removed lines are exactly the two docstrings, `with pytest.raises(error):` (now
  `… as caught` plus the exact-type assert), and `worker.start()`/`worker.join(timeout=10)` (now inside the
  `try`). AST compare against `git show HEAD:`: assertions 69 → 88, `pytest.raises` 19 → 19, test functions
  25 → 34, none removed. Golden: no rows removed; SIZE_ROWS gains 1 row; 2 tables added.
- **Disabled tests, money comparisons, imports.** Grep over `tests/**/CORE-003/**` for skip, xfail, importorskip,
  `.only`, `type: ignore`, `noqa`, TODO, FIXME, placeholder, pragma and deselect: no hits. The new code
  compares money through `_money`, Decimal `==`, dataclass `==` or Fraction. The only float literals in the
  file are pre-existing rejected inputs and the 1.000 threshold; there are none in new code or in the golden
  file. The only new import is the stdlib `faulthandler`. Every `sochron.risk` name used is in the contract's
  API block, and `sochron.costs` `H001_COSTS`/`Provenance` follow the existing pattern.
- **Flakiness and memory.** At HEAD, timed rows reject in milliseconds (F11 row 0.0027 s) against a 1.000 s
  limit. The largest fixture is the F11 30M-digit Decimal: about 60 MB of strings during construction and a
  12.0 MiB traced peak in the call. Other fixtures have ≤ 1,002 digits or a 5,001-digit int. The zero-budget
  rows use `-999999999999999999`, which fails fast even on pre-fix code (MemoryError at allocation, not a
  multi-GiB run).

### Full suite (item 5)
- `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` (11:03:02–11:03:05): **723 passed in 3.15s**,
  exit 0, no skips or deselections. That is 656 previous tests plus 67 new ones: 2 + 1 + 42 + 2 + 10 + 6 + 2 + 1 + 1.

### Mutation spot-check (item 6)
All runs execute the repo's applied test file in place (see "Blocks"). Each scratch `src/sochron/risk` was
checked blob-for-blob against its commit, and the import path resolved to the scratch tree.

| Risk code | Command scope | Result | Failure causes |
|---|---|---|---|
| HEAD copy (control) | whole acceptance file | **650 passed** in 2.50s (11:06:24–11:06:28) | — |
| `5d939a3` (before F9, F11) | whole acceptance file | **8 failed**, 642 passed (11:06:34–11:06:37) | exactly the 8 F9 rows: side ×2 and policy ×2 → `allowed=True`; nan_lots ×2 → plain `ValueError: cannot convert NaN to integer ratio`; restart ×2 → substituted policy (`risk_per_trade 0.5`) returned |
| `5d939a3` | F11 row only, `-rP` | **passed**, 0.149623600 s (HEAD 0.002677800 s) | none (F2) |
| `60dfbfd` (before r1 F1–F3) | whole acceptance file | **62 failed**, 588 passed (11:07:00–11:07:03) | 42/42 model domain (32 "DID NOT RAISE RiskError", 10 `ZeroDivisionError`); 10/10 huge counts (`ValueError: Exceeds the limit (4300 digits)`); 2/2 zero budget (`MemoryError`); 8 F9 rows |
| HEAD + `iterread_plugin.py` | whole acceptance file | 2 failed, 648 passed (11:10:15–11:10:17) | nan_lots ×2 (F1) |

### Red flags (item 7)
`bash scripts/controls/red-flags.sh origin/main` (11:08:51–11:08:52): exit 0; merge-base `47151e8`, 24 changed
paths; deleted or renamed tests none; untracked none (the proposal is ignored). There are 2 pattern groups with
hits, both inherited, and none in the two patched files.
- **Type checks disabled:** two intentional `# type: ignore[arg-type]` on negative cases in
  `tests/unit/risk/test_risk_unit.py` (a str day, an int halt flag), plus evidence, handoff and review prose quoting them.
- **Lint disabled:** review prose quoting `noqa`.
"Control files touched" lists the two patched locked files (expected), `tests/architecture/test_imports.py`
(red commit, unchanged here), and, by filename heuristic, `src/sochron/risk/policy.py` and the two security
review files. The secret, secret-like, destructive/bypass, placeholder/mock and order/account groups are empty.

## Not checked (and why)
- **The watchdog firing inside the locked file.** I proved its behaviour only with my scratch probe
  (same pattern, GIL-holding `sum`). A real GIL-holding regression inside the risk code was not built.
- **tests-r2 F4 rows against a real no-bound implementation.** I only timed the exact arithmetic such an
  implementation would do (0.31 s). The rows are not run against a mutant.
- **The proposed fixes for F1–F3 inside the locked file.** These are Codex's to write. The proofs are the
  probes above.
- **Implementation correctness beyond running these tests.** I read only the grep hits for `provenance` in
  `policy.py` and the F11 commit diff, to plan the mutation runs. The Codex implementation review r2 is still pending.
- **Handoff prose.** I checked its digests, counts (+222/−4, +24/−1, 69 → 88 assertions, 723 tests), commands and
  the F11 disclosure. I did not re-derive every sentence.
- **E1 obligations (F10/L3, F13/L5, F7, L1–L4).** These cannot be tested through the pure API, as the handoff
  says. CI, the owner demo, merge and deploy are outside this review. No terminal, broker, account or network
  action took place.
- **`node scripts/controls/check-locked-paths.mjs`.** Not run; it was not requested. The PR needs the owner's
  label for the locked files in any case.

## Checks run

| Command | Result | Commit | Time |
|---|---|---|---|
| `git status --porcelain`; `git diff --stat` | PASS: exactly the three expected paths | e510726 + applied patch | 10:57:19 |
| `sha256sum` ×3 (+ architecture); `git hash-object --path` ×2 | PASS: all equal handoff | same | 10:57:39 |
| `git -C <repo> apply -R --check …` | BLOCKED by guard-bash (F21); rerun standalone below | same | ~10:57:45 |
| `git apply -R --check docs/proposals/CORE-003-tests-r3.patch` (standalone) | PASS: exit 0, no output | same | ≤ 10:57:58 |
| `git diff --exit-code HEAD -- tests/architecture/`; blob compare | PASS: unchanged | same | ~11:02 |
| `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: 723 passed in 3.15s, exit 0 | same | 11:03:02–11:03:05 |
| uv stdin Fraction oracle (43 computed checks) | PASS (first run hit a probe-side `str()` limit; rerun clean) | same | 11:03:41–11:03:51 |
| `git diff --numstat`, removed-line list, `git diff --check`, `git check-ignore -v`, `git diff --cached --name-only` | PASS: 5 removed lines, all replaced by equal or stricter ones; handoff append-only; whitespace clean; index empty | same | ~11:04 |
| uv stdin AST compare against `git show HEAD:` | PASS: 0 assertions, raises or functions removed; ASCII/LF | same | ~11:04 |
| `mkdir -p "$S/…"` | BLOCKED by guard-bash (variable path); rerun with literal path | — | ~11:05 |
| `cp tests/acceptance/… tests/golden/… <scratch>` | BLOCKED by permission rule; not retried in any form | — | ~11:05 |
| in-place mutation runs (table above) | as tabulated | HEAD / 5d939a3 / 60dfbfd risk | 11:06:24–11:07:03, 11:10:15 |
| uv stdin no-bound arithmetic timing (F4 rows) | 0.307 s / 0.306 s | — | 11:07:21–11:07:22 |
| scratch watchdog probes (default capture, `-s`, `sys.__stderr__`, `capsys.disabled()`) | exit 1 every time; output 0 / traceback / 0 / 44 lines | — | 11:07:45–11:08:42 |
| `bash scripts/controls/red-flags.sh origin/main` | PASS execution, exit 0; 2 inherited groups | same | 11:08:51–11:08:52 |
| uv stdin `tracemalloc` peak of the F11 rejection | 269.5 MiB (5d939a3) vs 12.0 MiB (HEAD) | — | 11:12:01–11:12:02 |
| `git status --porcelain` before writing this file | PASS: unchanged three paths (`__pycache__` ignored) | same | 11:10:48 |

Delivery: review artifact written, unstaged. The applied test patch is **verified byte-exact and fit to
commit**; with this run, the implementation at HEAD passes the v1.5 tests on disk. CORE-003 is not yet
verified by the Codex implementation review r2, CI or the owner demo, and is not merged or deployed. Next
action: the implementer commits the two test files and the handoff. The owner decides F2, F3 and F4 (contract
wording or acceptance) and confirms the in-place mutation method. Codex closes F1, plus F3 if the owner picks
the `capsys.disabled()` fix, in a later D-006 patch.
