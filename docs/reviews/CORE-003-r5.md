# Review CORE-003 round 5 · base origin/main · head 45d4889 · reviewer Claude Code, fresh session acting as Codex reviewer under the role swap (PROGRESS.md `34097d9`)

This is a short recheck of review r4 F8 only. It covers contract v1.8 (`docs/contracts/CORE-003-risk.md`, Tier High), the round delta `git diff 37daccf..45d4889`, review r4 (`docs/reviews/CORE-003-r4.md`) and the R6/R7 reproductions in `docs/reviews/CORE-003-r3.md`. The delta touches 3 files with 4 lines changed each way: the contract (version line and L2), `PROGRESS.md` and `docs/evidence/CORE-003.md`. HEAD is `45d4889c548e4e1e87bed43a6379a7efa98486fa`. Local `origin/main` and `main` are both `3456e7d16430443df0ed26cd7f87b71f31f95914`. No fetch was done. Date 2026-10-22, all times +07. I am not the implementer, a test author or an earlier reviewer of CORE-003. I followed `.agents/skills/cross-agent-review/SKILL.md` as a plain procedure, as a re-review by finding ID. This file is the only change I made to the repository, and it is not staged.

**F8 is closed.** The v1.8 L2 text (`:201`) states the principle and calls its list a minimum ("อย่างน้อย"). It names every mechanism of R7 and the R6 carrier, and it gives one exemption list that it applies by name to every L2 ban. It agrees with the v1.7 scope-of-protection invariant (`:160`).

**No regression.** `git diff 6f38403..HEAD -- src tests` is empty, and the suite gives **784 passed in 3.28s**, 0 skipped.

**One new Low question (F9):** read literally, the single exemption list rejects one line of existing honest code on `main`: `CostModel.__post_init__` calls `object.__setattr__` (`src/sochron/costs/model.py:127`). This predates v1.8, because v1.3 already banned that call outside `sochron.risk` and journal. It affects only the obligation handed to the E1 contract. It does not affect `sochron.risk` code or any CORE-003 AC. This is review evidence. It is not approval to merge or to operate an account.

## Findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F9 | Low | question | `docs/contracts/CORE-003-risk.md:201` (the v1.8 exemption sentence), read with `:159`; `src/sochron/costs/model.py:127` | `:201` (v1.8) says every L2 ban, including the earlier `HaltState(`, `replace(` and `object.__setattr__` bans, applies to code outside `sochron.risk`, the journal module and `tests/`. `src/sochron/costs/model.py:127`, inside `CostModel.__post_init__`, is `object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))`. `sochron.costs` is none of the three exempt places, and `CostModel` is a type that risk uses, so the principle sentence also applies to it. The line is on `main` (`git show origin/main:src/sochron/costs/model.py`, line 127), and blame gives `c2e6725` (2026-10-21). This predates v1.8: v1.3 (`07856b9`) already banned `object.__setattr__` "นอก `sochron.risk` และโมดูล journal", and v1.8 restates that as the one list. `:159` (the v1.3 invariant) still gives the older list, "นอก `sochron.risk` และการกู้ state จาก journal ของ E1", which does not name `tests/`. This is the only collision with honest code. A grep of `src` for the other L2 items finds hits only inside `sochron.risk`. The two `replace(` hits outside risk are `datetime.replace` (`timebase/convert.py:50`) and `replace(model, …)` on a `CostModel` (`costs/model.py:138`), which the ban (on `HaltState`/`RiskPolicy` only) does not cover. | The E1 contract author writes the architecture test from `:201` as written and runs it on a tree that includes `main`'s `sochron.costs`. | The test fails on existing honest code. The E1 author then has to edit `sochron.costs` or add an exemption the contract does not state. That is the same failure pattern r4 F8 raised for `tests/`. There is no effect on `sochron.risk` code or on AC-01..AC-07, and it does not block CORE-003. The obligation takes effect in E1. | The owner, as one sentence (in v1.9 or carried into the E1 contract): replace the v1.8 exemption sentence in `:201` with the exact sentence under "F9 replacement sentence" below. A narrow, named exemption keeps `sochron.costs` from gaining a general right to write fields of objects that risk uses. | Run on a tree that includes `main`'s `sochron.costs`, E1's architecture test accepts `src/sochron/costs/model.py`, `src/sochron/risk/**` and `tests/**`. It rejects a scratch module holding r3's R6 and R7 code verbatim, and one holding `object.__setattr__(H001_RISK, "risk_per_trade", Decimal("0.99"))`. |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

### F9 replacement sentence

Replace this v1.8 sentence in `:201`:

> ทุกข้อห้ามของ L2 (ทั้ง `HaltState(`, `replace(`, `object.__setattr__` ข้างต้นและรายการนี้) ใช้กับโค้ดนอก `sochron.risk`, โมดูล journal และ `tests/` เหมือนกัน

with:

> ทุกข้อห้ามของ L2 (ทั้ง `HaltState(`, `replace(`, `object.__setattr__` ข้างต้นและรายการนี้) ใช้กับโค้ดนอก `sochron.risk`, โมดูล journal และ `tests/` เหมือนกัน ยกเว้นข้อเดียวคือ `object.__setattr__(self, "provenance", ...)` ใน `CostModel.__post_init__` (`src/sochron/costs/model.py`) ซึ่งตรึง provenance ของ object ตัวเองตอนสร้าง · รายการยกเว้นนี้ใช้แทนรายการใน Invariants ข้อ v1.3 (การสร้าง `HaltState(...)` ตรงๆ, `replace` และ `object.__setattr__`) ด้วย

### Round-4 finding verdict

| ID | Verdict | Contract lines and confirmation |
|----|---------|---------------------------------|
| F8 Low, question (L2 list does not cover R7; two exemption lists) | **Closed** | All three parts of F8's fix are in `:201` (v1.8, commit `45d4889`, recorded in the version line `:3`). **(1) Principle, not a closed list:** "หลักคือ 'โค้ดนอกขอบเขตห้ามเปลี่ยนพฤติกรรมของ object หรือ type ที่ risk ใช้'" and "architecture test ของ E1 ต้องครอบอย่างน้อย". **(2) R7, both mechanisms** (r3 `:113`–`:151`). The hook runs through `class Meta(abc.ABCMeta)` with `def __subclasscheck__` (r3 `:136`–`:141`) and `class Evil(numbers.Rational, metaclass=Meta)` (r3 `:143`). Three separate items each reject it: "การนิยาม `__instancecheck__`, `__subclasscheck__` หรือ `__subclasshook__`", "metaclass ที่สืบจาก `abc.ABCMeta`" and "class ที่สืบจาก ABC ของ `numbers`". The re-arm, `Bump.register(...)` on a user-defined `abc.ABC` (r3 `:133`, `:140`, `:146`), is covered by "`.register(` บน ABC ใดก็ตาม (รวม ABC ที่ผู้เรียกสร้างเอง)", which removes the narrow reading r4 found. The mutation itself, `object.__setattr__(p, "risk_per_trade", D(5))` (r3 `:139`), is covered by the earlier ban. **R6 carrier:** `d = vars(obj)` and `d[Key(field)] = d.pop(field)` (r3 `:52`–`:53`) are covered by "`vars(` และการเขียน `__dict__` ของ object". **(3) One exemption:** "ทุกข้อห้ามของ L2 (ทั้ง `HaltState(`, `replace(`, `object.__setattr__` ข้างต้นและรายการนี้) ใช้กับโค้ดนอก `sochron.risk`, โมดูล journal และ `tests/` เหมือนกัน". It names the first-half bans explicitly, so the older "นอก `sochron.risk` และโมดูล journal" earlier in the same item is overridden by name and does not set a second rule. **Agreement with `:160`:** `:160` names three out-of-scope classes and gives them to E1 L2. Each maps to an L2 item: a foreign key in `__dict__` (F6) maps to `vars(`/`__dict__`. A process hook through ABC or monkeypatch (F7) maps to `.register(`, the hook dunders, the ABCMeta metaclass, the `numbers` subclass and monkeypatch. A valid but unintended value through `object.__setattr__` maps to the earlier ban. The L2 principle restates `:160`'s "hostile code that edits object or runtime internals". The `numbers` item does not extend to `collections.abc`, as r4 had suggested. That is consistent with `:122`: any `collections.abc.Mapping` is the accepted provenance container that `:160` protects, so a ban on subclassing it would ban a carrier the contract accepts. A Mapping subclass that carries a hook is still caught by the metaclass and dunder items. F9 does not reopen F8. F8 asked for one list covering `tests/`, which v1.8 gives. F9 is about a place that list does not name. |

## AC status

PASS counts only executed evidence. This round changed no src or tests, so r4's per-AC evidence holds on the same bytes.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01..AC-06 | PASS | `git diff --quiet 6f38403..HEAD -- src tests` exits 0, and the working tree equals HEAD. All locked rows and unit tests pass in today's run (784 passed, 0 skipped). r4's oracle runs (2,880 sizing and 30,000 gate cases, 0 mismatches) and its six reread mutants ran on the same src and test bytes. I did not rerun them. |
| AC-07 | PASS | The suite passes with 0 skipped, including `tests/architecture/test_imports.py`, unchanged since `6f38403`. I did not rerun the red-flag scan, which r4 ran at `6f38403`. This round changes docs only. This is local evidence, not CI. |

## Checks run

| Command / procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD 6f38403 37daccf 45d4889`, `git log --oneline 6f38403..HEAD`, `git diff --stat 37daccf..45d4889`, `git diff --stat 6f38403..HEAD` | **PASS**: clean tree, `feat/CORE-003-risk`, 2 commits (`37daccf`, `45d4889`), round delta of 3 docs files with 4 lines each way; since r4: those 3 plus the r4 file | `45d4889` | 20:49:16 |
| `git diff 37daccf..45d4889 -- docs/contracts/CORE-003-risk.md` | Read: version line `:3` and L2 `:201` only | `45d4889` | 20:49 |
| Check 2: `git diff --quiet 6f38403..HEAD -- src tests`; `git diff --stat 6f38403..HEAD -- src tests`; `git diff --quiet HEAD -- src tests` | **PASS**: exit 0, empty stat (0 lines), exit 0 | `45d4889` | 20:50:15 |
| Check 3: `timeout 300 uv run --offline pytest tests -q -p no:cacheprovider` (Git Bash, repository root) | **PASS**, exit 0: **`784 passed in 3.28s`**, 0 skipped | `45d4889` | 20:50:17–20:50:21 |
| Grep of `src` for `object.__setattr__`, `vars(`, `__dict__`, `.register(`, `__subclasscheck__`, `__instancecheck__`, `__subclasshook__`, `ABCMeta`, `numbers.`, `setattr(`; and for `HaltState(`, `replace(`, `RiskPolicy(` | 3 hits for the first set: `risk/halts.py:74`, `risk/policy.py:176` (exempt) and `costs/model.py:127` (F9). For the second set, 3 hits, none a banned use (see F9 evidence) | `45d4889` | 20:49–20:50 |
| `git rev-parse origin/main main`; `git show origin/main:src/sochron/costs/model.py \| grep -n "object.__setattr__"`; `git blame -L 127,127 HEAD -- src/sochron/costs/model.py`; grep of `07856b9:docs/contracts/CORE-003-risk.md` for the v1.3 exemption phrase | Both `3456e7d`; line 127 on main; blame `c2e6725` 2026-10-21; v1.3 phrase present (1 hit) | `3456e7d` / `45d4889` / `07856b9` | 20:50:28 |

No hook or deny rule blocked any step.

## Checked, nothing found (and how)

- **Round scope (F06/F04/F18).** The round delta is docs only: contract, PROGRESS and evidence. No src, tests, dependency, lockfile, CI or control-script change was made (stat above).
- **R6 and R7 against the v1.8 list, item by item:** see the F8 verdict. Every statement in both reproductions that changes risk behaviour matches at least one named item. The `Meta`/`Evil` hook matches three items independently.
- **Exemption covers the test suite.** The `tests/` usages r4 counted (`replace(`, `object.__setattr__`, `HaltState(`, and the unit test's `Mapping.register(_CountingMapping)`) all fall inside the one list. They no longer depend on an unwritten exemption.
- **Over-breadth against honest code.** Apart from F9, no `src` module outside `sochron.risk` uses any listed item. The `replace(` ban is typed (on `HaltState`/`RiskPolicy`), so E1's test needs to resolve types and cannot be a text match: `datetime.replace` and `replace(model, …)` on `CostModel` would otherwise be false hits. That is an implementation note for E1, not a contract defect. "metaclass ที่สืบจาก `abc.ABCMeta`" bans defining a metaclass. It does not ban ordinary classes that use `abc.ABC` or `typing.Protocol`, so normal E1 interfaces are not caught.

## Not checked (and why)

- Hostile in-process code is out of scope by the owner's v1.7 decision (`:160`). I looked for no new carriers or bypasses of the L2 list in that class, and I did not check whether the "at least" list is complete against all such tricks. The principle sentence carries that.
- I did not rerun the red-flag scan, the oracles, the reread mutants or the locked-test hash check. This round changed no src or tests, and r4 ran all of them on the same bytes.
- I did not check that the docs-only edits to `PROGRESS.md` and `docs/evidence/CORE-003.md` are complete. They are outside F8.
- No terminal, broker or account connection, no credentials, orders, market data or holdout. E1's architecture test does not exist yet, so neither F8's nor F9's proof of fix can run now. Both are wording checks against the contract text and r3's code.
- No CI, PR label, owner demo, merge or deployment. A local PASS does not move the delivery state.
- Native Codex `/review` does not apply to this Claude session; I followed the skill procedure instead.

Delivery state: **implemented. Verified locally against contract v1.8: F8 closed, no src or tests change since r4, 784 passed. F9 is a non-blocking Low question on E1 wording, present since v1.3. Not merged or deployed.** Next action: the owner answers F9 (the one-sentence replacement above, in v1.9 or carried into the E1 contract), then the PR body, the owner demo, opening the PR with the `owner-approved-control-change` label, CI, and the owner's merge.

Findings open: 1
