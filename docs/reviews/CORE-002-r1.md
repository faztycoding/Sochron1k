# Review CORE-002 round 1 · base origin/main · head c2e6725 · reviewer Codex, fresh headless session 2026-10-21

Initial independent findings recorded before reading the handoff. Review in progress; the final report will replace this checkpoint in this same file.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | src/sochron/costs/charges.py:76 | `check_volume(Decimal("1"), replace(H001_COSTS, volume_step=Decimal("1e-30")))` raises `decimal.InvalidOperation: DivisionImpossible`; contract admits finite inputs without a digit limit. | The integer quotient of lots / step exceeds 28 digits. | A valid in-range, on-grid volume is rejected; off-grid input also escapes the promised BadVolume error. | Check exact grid membership without the 28-digit quotient restriction, retaining the contract's charge rounding rule. | Valid input returns the original Decimal; off-grid `1.0000000000000000000000000000001` raises BadVolume; caller context unchanged. |
| F2 | Medium | confirmed | src/sochron/costs/charges.py:21 | `CostBreakdown(1, 2, 3, 4, 10, 1)` and all-Decimal components 1/2/3/4 with total 999 both construct successfully. | A caller directly constructs the public frozen dataclass. | Decimal-only fields and the API's always-consistent total invariant are unenforced. | Validate all six Decimal fields and enforce the ordered p28 half-even total invariant during construction. | Wrong types raise TypeError; inconsistent total is refused or normalized according to the contract; factory outputs remain unchanged. |
| F3 | Low | confirmed | src/sochron/costs/model.py:119 | A list of all eleven provenance keys reaches `.items()` and raises AttributeError. | A non-Mapping iterable is supplied as provenance. | Wrong field type escapes the promised TypeError boundary. | Validate Mapping before inspecting keys or values. | List/set/string/non-Mapping provenance is rejected with TypeError; valid mappings still get immutable independent copies. |

## AC status

Pending the handoff hash comparison and independent arithmetic oracle. The full suite ran: 41 passed in 0.09s, zero skipped.

## Checked, nothing found (and how)

Initial contract/diff inspection: nominal formulas, H001 constants, spread selection, swap sign, frozen declarations, and no production float or external I/O paths.

## Not checked (and why)

Handoff not read yet, preserving the skill's initial-review ordering.
