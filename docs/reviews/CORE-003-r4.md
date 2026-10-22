# Review CORE-003 round 4 · base origin/main · head 6f38403 · reviewer Claude Code, fresh session acting as Codex reviewer under the role swap (PROGRESS.md `34097d9`)

This is a short closing recheck. It covers contract v1.7 (`docs/contracts/CORE-003-risk.md`, Tier High), the round delta `git diff 18dcfea..HEAD`, review r3 (`docs/reviews/CORE-003-r3.md`) and the handoff section "Application of tests r4 and findings response to review r3". HEAD is `6f38403fe1fdd1309005cb4cb118e374b5f3a9f5`. Local `origin/main` and `main` are both `3456e7d16430443df0ed26cd7f87b71f31f95914`, and the merge-base is `47151e87a0f0fafe440a5a74d1db0f353edb00f0`. No fetch was done. Date 2026-10-22, all times +07. I am not the implementer, a test author or an earlier reviewer of CORE-003. I followed `.agents/skills/cross-agent-review/SKILL.md` as a plain procedure. Because this is a re-review by finding ID, I read the implementer's response before checking. This file is the only change I made to the repository, and it is not staged.

**F6 and F7 are closed by owner allocation.** Contract `:160` names both carriers as outside the module's protection, gives the reason, assigns them to E1 L2 and closes them with no code change. `:201` extends L2. The rest of the contract agrees with this.

**No regression since round 3.** `git diff 18dcfea..HEAD -- src` is empty. The new unit test checks one traversal and one lookup per key for each of its 7 calls. It fails against `073ab70`'s `halts.py`, and it also catches five more one-line reread mutants, each in a different call. The locked tests are byte-identical to `a4bb3fe` and to the handoff hashes. The suite gives **784 passed in 3.24s**, 0 skipped. An independent exact oracle gives 0 mismatches over 2,880 sizing cases and 30,000 gate cases.

**One new Low question (F8):** read literally, the L2 ban list does not cover F7's own reproduction, and its two halves exempt different paths. It affects only the obligation handed to the E1 contract, not `sochron.risk` code or any CORE-003 AC. This is review evidence. It is not approval to merge or to operate an account.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F8 | Low | question | `docs/contracts/CORE-003-risk.md:201` (the v1.7 L2 sentence), read with `:160` | `:160` assigns F7 ("hook ระดับ process ผ่าน ABC หรือ monkeypatch") to E1 L2. The v1.7 L2 sentence lists its bans after "ได้แก่" (namely): `vars(` and `__dict__` writes, "`.register(` ของ ABC (`numbers`, `collections.abc`)", and runtime replacement of module or class attributes. R7, the reproduction F7 was closed on (`docs/reviews/CORE-003-r3.md:117`–`:149`), uses two mechanisms. The first runs the hook: `class Evil(numbers.Rational, metaclass=Meta)`, whose metaclass defines `__subclasscheck__` (`:136`–`:144`). No L2 item names it. The second re-arms the hook by invalidating ABC caches: `Bump.register(...)` on a user-defined `abc.ABC` (`:133`, `:140`, `:146`). The parenthetical can be read as limiting the ban to ABCs from `numbers` and `collections.abc`, and `Bump` is neither. Separately, the two halves of L2 exempt different paths. The original bans (`HaltState(`, `replace(`, `object.__setattr__`) exempt `sochron.risk` and journal only, while the v1.7 bans also exempt `tests/`. The tests use the original bans' calls throughout: `tests/unit/risk/test_risk_unit.py` has `replace(` on 32 lines, `object.__setattr__` on 15 and `HaltState(` on 3, and the locked acceptance file has `object.__setattr__` on 19 (grep, 20:44). F6's carrier is covered in either reading: R6 uses `vars(obj)` and re-keys that dict. | The E1 contract author writes the architecture test from the literal L2 list. | Under the narrow reading, an E1 architecture test that bans exactly the listed patterns would accept a module holding R7 verbatim. The allocation that closes F7 would then not hold where `:160` puts it. The exemption mismatch either flags every risk test or invites an unwritten exemption. There is no effect on `sochron.risk` code or on AC-01..AC-07. The obligation takes effect in E1. | Owner, as one contract sentence (in v1.8, or carried into the E1 contract): say the list gives examples of the `:160` principle and is not complete. Add R7's own mechanisms: `.register(` on any ABC, and a class that subclasses a `numbers` or `collections.abc` ABC or whose metaclass defines `__subclasscheck__`/`__instancecheck__`. Use one exemption list (`sochron.risk`, journal, `tests/`) for both halves of L2. | E1's architecture test rejects a scratch module holding r3's R6 and R7 code verbatim, and accepts `src/sochron/risk/**` and `tests/**`. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

### Round-3 finding verdicts

| ID | Verdict | Contract lines and confirmation |
|----|---------|---------------------------------|
| F6 Low (key planted in an object's own `__dict__`) | **Closed by owner allocation** | `:160`: `sochron.risk` protects against a wrong type or domain at every position, including values changed after construction (re-validated at use). It also protects against caller code that arrives with an input the contract accepts: the provenance Mapping, read once per call before every other field. It does not protect against hostile code in the same process that edits object or runtime internals, "เช่น key แปลกปลอมใน `__dict__` ของ object (F6)", nor against a valid but unintended value (`risk_per_trade` 0.99 via `object.__setattr__`). Pure code cannot stop these, so protection belongs to E1 L2, and F6/F7 "ปิดด้วยการจัดสรรนี้ ไม่แก้โค้ด". `:201` bans `vars(` and `__dict__` writes outside `sochron.risk`, journal and `tests/`, which covers R6. The rest of the contract agrees. `:122` (exact types, with the Mapping container as the only exception) makes the provenance Mapping the only accepted carrier of caller code, which is what `:160` protects. `:125`–`:126` (re-validation at use) match the protected set. The 0.99 example matches `:125` ("การตั้ง latch เป็น False เองตรวจไม่ได้ในโมดูล pure (E1 ข้อ L2)"), because re-validation checks domain, not intent. `:127`'s sentence that the gate never returns `allowed=True` for a request or state changed during the check was not edited and does not refer to `:160`. Read with `:160`, it covers the protected carrier. That is not a contradiction, because `:160` names F6 explicitly. A cross-reference would help someone who reads only the table (no finding). The owner's choice is recorded in the version line `:3`, the Status line `:4` and handoff `:1139`. The src is unchanged, so this is an allocation, not a fix, as stated. |
| F7 Low, question (process-wide ABC hook) | **Closed by owner allocation** | `:160` names "hook ระดับ process ผ่าน ABC หรือ monkeypatch (F7)" as out of scope and assigns it to E1 L2. Handoff `:1140` records the same. The completeness of the L2 list meant to carry it is F8, which does not reopen F7 for CORE-003. |

### Check 2: the tests-r4 F1 unit test

`test_every_public_call_reads_provenance_exactly_once` (`tests/unit/risk/test_risk_unit.py:557`–`:610`, commit `fd50946`) plants `_CountingMapping` on one policy object that `state` and `halted` share. For each of `check_entry`, `size_position`, `start_experiment`, `update_equity`, `restart_experiment`, `unknowns` and `HaltState(...)`, it resets the counter, calls once, and asserts `traversals == 1` (`keys()` plus `__iter__`) and that every key has exactly one lookup. A pass therefore proves that each call reached the counter: 0 traversals would fail. No row can pass vacuously. The counter defines no `items`, `values`, `get` or `__contains__`. A reread through the Mapping mixins therefore raises `AttributeError`, and `in` falls back to `__iter__`, which is counted. Either way the test fails.

Every run used a scratch tree from `git archive HEAD pyproject.toml src tests/unit/risk`, with one file replaced or one line added. pytest's rootdir was the tree, so `pythonpath = ["src"]` loaded the tree's package. The command was `uv run --offline --no-sync --project <repo> --directory <tree> python -B -m pytest tests/unit/risk/test_risk_unit.py::test_every_public_call_reads_provenance_exactly_once -q -p no:cacheprovider -p loadcheck -s`. A scratch plugin printed the path and SHA256 of the loaded `halts.py`, `policy.py` and `gate.py` in every run, and each run loaded its own tree.

| Risk code (scratch) | Change | Result | Failing call and assertion |
|---|---|---|---|
| HEAD copy (control) | none | 1 passed | — |
| `073ab70` `halts.py` (blob `509037213884…`, SHA256 `3320110f…`) in a HEAD tree | pre-F5 result validation | **1 failed** | `start_experiment`: `assert 2 == 1` (traversals) |
| `mut_lookup` | `_new_state` looks up the 5 provenance keys again (tests-r4 F1 mutant `head_lookup`) | **1 failed** | `start_experiment`: `assert {2} == {1}` (lookups) |
| `mut_gate` | `validate_state(state)` again before `return _decision(reasons)` (tests-r4 F1 mutant `head_gate_reread`) | **1 failed** | `check_entry`: `assert 2 == 1` |
| `mut_unknowns` | one more lookup of `halt_clearers` after the snapshot | **1 failed** | `unknowns`: `assert {1, 2} == {1}` |
| `mut_sizing` | `require_policy(policy)` again before building the result | **1 failed** | `size_position`: `assert 2 == 1` |
| `mut_haltstate` | `__post_init__` validates twice | **1 failed** | `HaltState`: `assert 2 == 1` |

My own read profile (`probes/readprofile.py`) counts every Mapping entry point (`keys`, `__iter__`, `__getitem__`, `__len__`, `__contains__`, `items`, `values`, `get`, `__eq__`). At HEAD, each of the 7 calls makes 1 traversal and 1 lookup per key (5 keys) and touches no other entry point. At `073ab70` `halts.py`, `start_experiment`, `update_equity` and `restart_experiment` each make 2 traversals and 2 lookups per key, so the test's loop would fail on each of the three, not only the first. `RiskPolicy(...)` construction, the 8th consumer that round 3 profiled, is not in the test's list. At HEAD it makes 1 `keys()` and 1 lookup per key, and it stores a `mappingproxy` of the copy. The test does not count `__len__`, `__eq__` or `__bool__`. HEAD calls none of them on provenance, and tests-r4 F1 did not ask for them. So tests-r4 F1 is answered: both of its mutants now fail.

## AC status

PASS counts only executed evidence. Round 3's FAIL rows came from F6 alone. F6 is now outside the contract's scope (`:160`), so the ACs are judged on behaviour within that scope.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | The locked fixtures pass in the 784 run. My oracle: 2,880 sizing cases (5 models × 3 policies × 8 equities × 8 distances × 3 cost budgets, including the contract literals `9599.9999999999999999999999999` and `1.0000000000000000000000000001`) give 0 mismatches on lots, the three display fields and the reason. All three reasons occur. Exact `actual_risk ≤ risk_money` and grid membership hold whenever the reason is not `below_min_volume`. |
| AC-02 | PASS | The locked daily-halt, rollover and `TimeReversal` rows pass. The src is byte-identical to `18dcfea`, where round 3 ran 9,600 seeded update/restart steps with 0 mismatches. I did not rerun a halt oracle. |
| AC-03 | PASS | The locked restart rows pass: wrong names refused, same-day daily latch kept, rebase, same policy object. Round 3's oracle evidence applies to the same bytes. |
| AC-04 | PASS | The locked gate rows pass. My oracle: 30,000 seeded gate cases. 5,094 raised `TimeReversal` as expected, and 24,906 were decided with exact reason sets, 0 mismatches. 804 were allowed, and all 9 entry reasons occurred, including `stale_state` and `below_min_volume`. Self-test: a strict-threshold mutant gives 2,734 mismatches and a `>=` sized-lots mutant gives 5,355, so the oracle is not vacuous. |
| AC-05 | PASS | The locked stop-change rows pass. `gate.py` is unchanged since round 3's 16 oracle cases. |
| AC-06 | PASS | The locked F4 exact-str key rows and the error-table rows pass. The new read-once unit test passes at HEAD and fails on all six reread variants above. The H001 literal and the `unknowns` rows pass. |
| AC-07 | PASS | **784 passed in 3.24s**, 0 skipped, exit 0. `tests/architecture/test_imports.py` is byte-identical to `831fa60` and passes. In the red-flag scan, the secret and order/account groups are empty. This is local evidence, not CI. |

## Checks run

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD origin/main main`, `git merge-base HEAD origin/main`, `git log --oneline 18dcfea..HEAD` | **PASS**: clean tree, `feat/CORE-003-risk`, revisions as above, 4 commits (`6ec0631`, `fd50946`, `8992037`, `6f38403`) | `6f38403` | 20:34:57 |
| `git diff --quiet 18dcfea..HEAD -- src` | **PASS**, exit 0 (empty) | `6f38403` | 20:35 |
| `git diff --stat 18dcfea..HEAD` | 6 files: PROGRESS, contract, evidence, handoff, review r3, unit test (+56) | `6f38403` | 20:35 |
| `git diff --quiet a4bb3fe..HEAD -- tests/acceptance tests/golden`; `git diff --quiet 831fa60..HEAD -- tests/architecture`; `git diff --quiet HEAD -- tests src` | **PASS**, exit 0 for each | `6f38403` | 20:36 |
| `sha256sum`, `git hash-object`, `git rev-parse a4bb3fe:<f> HEAD:<f>` on the 3 locked files | **PASS**: table below | `a4bb3fe` / `6f38403` | 20:36 |
| Build scratch trees (`git archive` + `git show 073ab70:src/sochron/risk/halts.py`) | First attempt **BLOCKED** by guard-bash (block text below). Rerun once with literal scratch paths under the owner's headless-reviewer exception: **PASS** | `6f38403`, `073ab70` | 20:37–20:38 |
| New unit test on the HEAD tree and the `073ab70` `halts.py` tree | **PASS** (1 passed) / **expected FAIL** (`start_experiment`, `assert 2 == 1`) | scratch | by 20:38:22 |
| `uv run … python -B -I probes/readprofile.py` on both trees | **PASS**: HEAD 1 read in all 7 calls. `073ab70`: 2 in start, update and restart | scratch | 20:39:10 |
| New unit test on 5 reread mutants | **expected FAIL** on all 5, each naming the mutated call | scratch | 20:40:18 |
| `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` (Git Bash, repository root) | **PASS**, exit 0: **`784 passed in 3.24s`**, 0 skipped | `6f38403` | 20:40:35–20:40:39 |
| `bash scripts/controls/red-flags.sh origin/main` | **PASS**, exit 0, `Pattern groups with hits: 2` (explained below) | `6f38403` | 20:40:42–20:40:44 |
| `uv run --offline python -B -I probes/oracle.py <repo>/src` | **PASS**, exit 0: sizing 2,880 and gate 30,000 cases, 0 mismatches, 2.39 s | `6f38403` | 20:43:04–20:43:06 |
| The same oracle on `mut_strict` and `mut_sized` (self-test) | **expected FAIL**: 2,734 and 5,355 mismatches | scratch | by 20:43:34 |
| `RiskPolicy(...)` construction read count (inline `uv run … python -B -c`) | **PASS**: 1 `keys()`, 1 lookup per key | `6f38403` | 20:44:36 |
| `grep -c` for `replace(`, `object.__setattr__`, `HaltState(`, `.register(`, `vars(` in the two risk test files | Counts as cited in F8 | `6f38403` | 20:44 |

Block text, verbatim: `PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: mkdir would change $S/tree_head (a path that cannot be resolved here (variable or unknown directory)). The implementer may not change locked paths; ask the owner.` The command built the scratch trees through a shell variable `S` for the scratchpad path. I reran it once, unchanged except that each `$S` became the literal scratchpad path. This is the owner's recorded headless-reviewer exception: a variable path to the scratchpad becomes a literal path. It ran and passed. No other block occurred. I made one shell mistake of my own: a malformed `sed` in an output filter. It was not a block, and I reran the same runs without it.

The scratch files are in `C:\Users\MSI\AppData\Local\Temp\claude\C--Users-MSI-Desktop-------------Sochron1k\1efe9fa0-2232-4abb-9028-90e3e22811e1\scratchpad\` (`tree_head`, `tree_073`, `mut_*`, `plugins\loadcheck.py`, `probes\readprofile.py`, `probes\oracle.py`). Python 3.12.15 via uv, run with `-B` and `PYTHONDONTWRITEBYTECODE=1`. The repository's `src` was only read. No configuration was changed.

### Locked-test integrity

The working-tree bytes equal `HEAD` and `a4bb3fe`. The architecture file equals `831fa60`.

| File | SHA256 | Git blob (worktree = `a4bb3fe` = HEAD) | Handoff |
|---|---|---|---|
| `tests/acceptance/CORE-003/test_risk_acceptance.py` | `fa1bde04706d177bb13a4da14e00751ff67c85816537e8417932e59d280c94df` | `d2ba11db5958d817c5830fc54a3eda5fa3e7ce35` | `:1016`, `:1130` |
| `tests/golden/CORE-003/risk_cases.py` | `04c5e6443cc75506b581d72860e98421bb5eba1f3b3beec88f987fd7e0dd0d83` | `d4800f296435d10344eb68a468f6ab132e1fbaf2` | `:1017` |
| `tests/architecture/test_imports.py` | `259ac6d4a9c9b0dfd165f0936b092ca458bde033b453c4ffde3b44787933b195` | `9c18e04813b6970bcc0884de8d4f5db91846d093` | `:58`, `:955` |

### Red-flag scan groups

- **Type checks disabled:** the same two intentional `type: ignore[arg-type]` comments in negative unit tests as round 3. The other hits are review, handoff and evidence prose, including the new r3 file. There is no suppression in production code or locked tests.
- **Lint disabled:** prose quoting `noqa` only.
- **Control files touched** (listed separately): the 3 locked test files, `src/sochron/risk/policy.py` and the two security pre-review report names (the scan's naming heuristic). These are the same as round 3 and none changed in this round. The listing grants no approval.
- **Empty:** deleted or renamed tests, untracked files, secrets, order/account mutation, destructive/bypass patterns, placeholder/mock.

## Checked, nothing found (and how)

- **Round scope (F06/F04/F18).** The 6 changed files are workflow docs plus `tests/unit/risk/test_risk_unit.py`, which is an allowed path. There is no src, dependency, lockfile, CI, control-script or locked-test change. The new test's `Mapping.register(_CountingMapping)` is a process-wide ABC registration of a test-only class. It sits inside `tests/`, which the v1.7 L2 sentence exempts, and the full suite passes with it.
- **The decision is recorded.** The v1.7 entries in the version line (`:3`) and Status line (`:4`) match handoff `:1137`–`:1141`. The tests-r4 F1 choice (unit test, no further locked patch) and the tests-r4 F2 sentence (`:127`) agree with HEAD, which checks key types first (`policy.py:187`–`:192`).
- **Evidence numbers.** `docs/evidence/CORE-003.md` and PROGRESS now say 784 passed, which matches my run. A docs-only nit, not a finding: `docs/evidence/CORE-003.md:3` and the end of `PROGRESS.md:5` still label the contract "v1.3", while the same PROGRESS line says v1.7 earlier.
- **Honest-input behaviour.** The oracle and AC evidence are above. The oracle's models and policies are fresh `replace(...)` copies, and an end-of-run assert confirms the H001 singletons were not changed.

## Not checked (and why)

- No terminal, broker or account connection, no credentials, no orders, no market data, no holdout. The E1 obligations (L1–L5, F7 of the security pre-review) cannot be tested through the pure API.
- Hostile in-process code that edits object or runtime internals is out of scope by the owner's v1.7 decision, so I looked for no new carriers in that class. F8 is about the wording of the allocation only, and its evidence is round 3's existing R7 code. Thread races were not checked, as in rounds 2 and 3.
- I did not rerun a halt-state oracle. AC-02/AC-03 rest on the locked rows run now, plus round 3's oracle on byte-identical src.
- I did not rerun the mutation runs of the locked tests or force the watchdog: `docs/reviews/CORE-003-tests-r4.md` covers both.
- No CI, PR label, owner demo, merge or deployment. A local PASS does not move the delivery state.
- Native Codex `/review` does not apply to this Claude session; I followed the skill procedure instead.

Delivery state: **implemented. Verified locally against contract v1.7: F6/F7 closed by owner allocation, no regression, every AC PASS. F8 is a non-blocking question on E1 wording. Not merged or deployed.** Next action: the owner answers F8 (a one-line L2 wording change in v1.8, or carried into the E1 contract), then the PR body, the owner demo, opening the PR with the `owner-approved-control-change` label, CI, and the owner's merge.

Findings open: 1
