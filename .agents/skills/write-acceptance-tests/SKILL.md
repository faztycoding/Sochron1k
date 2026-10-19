---
name: write-acceptance-tests
description: Test-author role for Sochron1k. Writes failing acceptance tests (and hand-computed golden tests for quant work) from an approved task contract BEFORE any implementation exists, then explains each test in plain language for the owner. Use when the owner asks to write tests first, "เขียน test ก่อน", "เขียน acceptance test", "golden test", or starts a Standard/High task after the contract is approved. Do not use if this chat has seen the implementation.
metadata:
  version: "1.0.0"
  source: "Handbook v5 P26, P09; ch.16, ch.34"
---

# Write acceptance tests from the contract (test author)

Tests written after seeing the code check what the code does; tests written from the contract
check what the code should do. That difference is the whole point of this role. Approved
acceptance tests become part of the contract and are locked: the implementer can never edit them.

## Preconditions (stop if any fails)
- This is a new chat that has not seen the implementation, the task branch's source diff or a handoff note.
- `docs/contracts/<TASK-ID>*.md` exists and its status says the owner approved the acceptance criteria.
- You are on the task branch named in the contract, and nobody else is writing to this working tree.

## Inputs
Only the contract and the interfaces that already exist (signatures, module paths, data schemas).
Do not read implementation code for the task, `docs/handoff/` or chat history from the implementer.

## Procedure
1. Read AGENTS.md, docs/HANDBOOK-CORE.md (sections 4, 11 and, for quant work, 15) and the contract.
2. For every acceptance ID write at least one test in `tests/acceptance/<task-id-lowercase>/`, named after the AC
   (Python: `test_ac01_<behavior>.py` or functions `test_ac01_...`). Cover the normal case, the
   edges and the failure cases the contract names, and nothing it does not name.
3. Quant tasks: put hand-computed known-answer tests in `tests/golden/<task-id-lowercase>/`. Show
   the arithmetic in a comment or a small fixture README so the owner can re-check it by hand. Use
   synthetic data whose correct answer is known in advance (for example a series where the only
   valid entry is on one known bar).
4. If the interface does not exist yet, import it inside each test through a tiny helper that
   turns ImportError/AttributeError into `pytest.fail("AC-xx: <symbol> not implemented")`. That
   way the run fails for the right reason, not with a collection error. Never mark tests
   skip or xfail.
5. Run the new tests with the verified test command (or `uv run pytest <dir>` once it exists) and
   confirm every test FAILS because the behavior is missing, not because of syntax or import
   mistakes in the test itself. Keep the real output.
6. Commit only the test files on the task branch: `test(<scope>): acceptance tests for <TASK-ID>`
   with `Refs: <TASK-ID>`.

## Output (return to the owner, in Thai)
| AC | Test (file::name) | What it proves, in plain words | Why it fails now (real output) |
|----|-------------------|--------------------------------|--------------------------------|

Then list the questions the contract does not answer. Never guess behavior the contract does not
state; write it down as a question for the owner.

## Must not
- Write or change implementation code, the contract, or files outside `tests/`.
- Weaken a test so it passes, or write a test that cannot fail.
- Read the implementer's reasoning before your tests are committed.
