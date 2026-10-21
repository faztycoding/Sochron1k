# Review CORE-002 contract round 3 · base 5bce19b · head c8e3793 · reviewer Codex, fresh headless review session

Reviewed on 2026-10-21, Asia/Bangkok (+07:00). Object: contract v1.2,
`docs/contracts/CORE-002-costs.md`. Full HEAD:
`c8e379310edf942a020de90db40bbd523eb18b96`; branch `feat/CORE-002-costs`.
Compared `git diff 5bce19b..HEAD -- docs/contracts/CORE-002-costs.md` with
the remaining F1 evidence in `docs/reviews/CORE-002-contract-r2.md`.
Contract line references below refer to this HEAD.

**F1 verdict: closed.** The lossless-multiplication and universal exact-doubling
contradiction is gone. The r2 reproduction now has the rounded result specified
by v1.2. No replacement sentence is needed. F2–F7 retain their r2 closure and
were not reopened; no new F8 finding was identified in this revision.

**Ready for test authoring: yes**

This is contract readiness, not implementation acceptance or merge approval.
Applied `adversarial-design-review` and the `cross-agent-review` re-review
procedure within the owner's explicit F1-only scope. A read-only helper checked
the clauses independently; this session reproduced the arithmetic and wrote
only this report. The report is left unstaged. The explicit single-file scope
excludes a PROGRESS update, test edits, commits and pushes.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 (closed) | High (original) | confirmed (resolved) | docs/contracts/CORE-002-costs.md:61, :74, :87–88, :123, :127, :144–147, :174 | :87 permits rounding after each operation in the written order, with precision 28 and ROUND_HALF_EVEN; :174 confines exact linearity/doubling to AC-01–AC-04 fixtures and expressly excludes that promise for other inputs. | The r2 model with points, point, contract_size and stress_factor all Decimal("12.345678"), and lots Decimal("1.23"). | The previously incompatible numeric oracles are resolved: general inputs follow the rounded equations; the stated fixtures retain their exact answers. | Both requested changes are present. No further replacement required. | Reproduction below matches the specified rounded base and stressed results. The 23 finite fixture rows and 18 fixture scaling checks pass at precision 28 with Inexact and Rounded trapped; ordered total doubling and 1/3 also pass. |

## AC status

These statuses describe implementation acceptance, which this contract-only
review cannot establish. Arithmetic checks below support F1 closure only.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | UNKNOWN | Fixed spread/fallback/point values and fixture scaling recomputed successfully; no implementation executed. |
| AC-02 | UNKNOWN | Base/stressed slippage and zero/nonzero commission fixture values recomputed successfully; no implementation executed. |
| AC-03 | UNKNOWN | Base/stressed swap charge and credit fixture values recomputed successfully; no implementation executed. |
| AC-04 | UNKNOWN | Ordered totals, sides-zero total, short total, stressed total and R recomputed successfully; no implementation executed. |
| AC-05 | UNKNOWN | F1's undocumented digit restriction is removed. Runtime validation and errors are outside this re-check. |
| AC-06 | UNKNOWN | Unchanged provenance/immutability acceptance was not rerun; F2–F7 remain closed per r2. |
| AC-07 | UNKNOWN | Documentary red-flag scan executed; architecture and application test suites were not run. |

## Checked, nothing found (and how)

### R2 reproduction under the revised rule

No application code was imported. Used the existing CPython 3.12.15 environment
and stdlib Decimal. The hypothetical model retains H001's valid volume limits
and step; lots 1.23 is valid. Its changed fields have the same synthetic
provenance treatment described in r2. The expression is exactly API line 61.

Read-only reproduction, sent to `uv run --offline --no-sync python -B -`:

```python
from decimal import Context, Decimal, Inexact, Rounded, ROUND_HALF_EVEN, localcontext

D = Decimal
x, lots = D("12.345678"), D("1.23")
with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)) as ctx:
    ctx.traps[Inexact] = True
    ctx.traps[Rounded] = True
    exact = x * x * x * lots * x
with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
    base = x * x * x * lots * x
    stressed = x * x * x * lots * (x * D("2"))
    twice_base = base * D("2")
    assert exact == D("28573.59557212382385913406202288")
    assert base == D("28573.59557212382385913406202")
    assert stressed == D("57147.19114424764771826812405")
    assert twice_base == D("57147.19114424764771826812404")
    assert base != exact and stressed != twice_base
    assert stressed - twice_base == D("1E-23")
```

The precision-28 base calculation produced these successive values:

| Operation | Observed Decimal value |
|-----------|------------------------|
| points × model.point | 152.415765279684 |
| previous × model.contract_size | 1881.675960266558605752 |
| previous × lots | 2314.46143112786708507496 |
| previous × model.stress_factor | 28573.59557212382385913406202 |

The final multiplication rounds. Recomputing with the doubled stress factor
returns `57147.19114424764771826812405`; doubling the already rounded base
returns `57147.19114424764771826812404`. Both observations are unchanged from
r2. Under v1.2, only the first is the stressed-charge oracle: the contract no
longer requires equality to twice the rounded base for this non-fixture model.

### Clause consistency and fixture checks

- Decimal context (:87–88): rounding after each operation is explicit, the
  unexplained six-digit/10^9 restriction is gone, and numeric Decimal equality
  compares the resulting rounded values. No quantization does not mean no
  context rounding.
- Invariants (:123, :127): calculations explicitly adopt that Decimal context;
  the hand-checkable equalities name H001 values, including default nested
  stress. They do not state a universal exactness or doubling property.
- AC-01–AC-04 (:144–147): exact expected numbers belong to explicit H001 and
  synthetic fixtures. Recomputed 23 finite scalar rows at precision 28 with
  both Inexact and Rounded trapped. Every row passed without rounding,
  including totals 1.68760, 1.48760, 0.68 and 3.37520, and R 0.067504.
- Plan item 4 (:174): exact linearity/doubling is expressly confined to those
  fixtures. For their point values 1, 50, 100, 240, -503.8 and 0 at lots 0.02,
  checked doubling points, doubling lots to 0.04 and doubling stress: all 18
  checks passed without rounding. This finite check makes no general claim.
- Total (:74, :174) uses `spread + commission + slippage + swap` in that
  written order and the same context. The fixture stressed total equals twice
  its base; no associative or lossless-sum promise remains for arbitrary inputs.
- API stress (:55–56) and the general stress goal (:21) specify applying the
  factor, subject to the explicit arithmetic policy. They do not override :174
  with a universal exact-doubling requirement. The precision-28 1/3 example
  also reproduced `0.3333333333333333333333333333`.
- Inspected the full requested diff: the remaining changes are version,
  review-status and next-action bookkeeping. No additional arithmetic promise
  or new conflict was introduced by v1.2.

### Commands and review evidence

All times are 2026-10-21 +07:00. Minute-only entries are approximate session
intervals. Every check used unchanged HEAD `c8e3793`.

| Command / procedure | Result | Commit | Time |
|---------------------|--------|--------|------|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: clean starting tree/index; expected task branch and HEAD. | c8e3793 | 20:55–20:56 |
| UTF-8 reads of contract, r2, review template and review procedures; `git diff 5bce19b..HEAD -- docs/contracts/CORE-002-costs.md` | PASS: F1 and surrounding exactness clauses checked; closure justified above. | c8e3793 | 20:56–20:58 |
| `uv run --offline --no-sync python -B -c 'import sys, decimal; print(sys.version); print(decimal.__file__); print(decimal.Context.__doc__); print(decimal.localcontext.__doc__)'` | PASS: CPython 3.12.15 and installed stdlib context documentation inspected. | c8e3793 | 20:56 |
| Read-only arithmetic stdin probe via `uv run --offline --no-sync python -B -` | PASS, exit 0: r2 reproduction, 23 finite fixture rows, 18 fixture scaling assertions, ordered total doubling and 1/3. | c8e3793 | 20:58:03 |
| `& 'C:/Program Files/Git/bin/bash.exe' scripts/controls/red-flags.sh main` | PASS execution, exit 0; one inherited documentary pattern group, explained below. | c8e3793 | 20:57 |
| `git status --porcelain=v1 --untracked-files=all`; `git diff --cached --name-only`; `git rev-parse HEAD`; `Test-Path docs/reviews/CORE-002-contract-r3.md` | PASS before writing: clean tree/index, unchanged HEAD, target absent. | c8e3793 | 20:58:35 |

Red-flag hits: **Type checks disabled** matched two inherited documentation
lines in `docs/reviews/CORE-001-agents-r1.md` and
`docs/tooling/compatibility.md` discussing an earlier suppression. Neither is
a new suppression in this revision. Secret and order/account-mutation groups
were empty; no deleted or renamed tests were reported. The broader comparison
with local main also lists inherited AGENTS.md/CLAUDE.md changes, whose approval
and CI are outside this F1-only review. The scan ran before this report and
does not scan untracked files.

## Not checked (and why)

- CORE-002 implementation, pytest, acceptance/golden/architecture execution,
  runtime input rejection, immutability and caller-context isolation: this is
  a contract review before test authoring. Stdlib arithmetic is not evidence
  that application acceptance passes.
- F2–F7, unrelated risk/architecture decisions, source provenance, other
  numeric-domain behavior and whole-branch approval: excluded by the explicit
  F1-only re-review scope. Their earlier closure is not a new review result.
- Broker/terminal connections, market data, research, dependencies and CI:
  neither required nor exercised. No external write or Git mutation was made.

Next action: author the CORE-002 tests against v1.2, preserving its ordered
precision-28 arithmetic and limiting exact scaling assertions to the fixtures.
