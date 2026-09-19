# Local position-management recovery

SCN-011 adds an internal Python/simulator contract, not an operator command or MT5
control endpoint. `execution_ready` and `auto_trading_enabled` remain false. Never
use this runbook to infer permission for a broker operation.

See the [contract](../contracts/SCN-011-position-management.md),
[decision](../decisions/ADR-017-durable-position-management.md) and retained
verification report for the exact candidate revision.

## Required sequence

1. Keep new entries closed and establish explicit startup admission from a complete,
   fresh inventory for the expected Demo account, symbol and executor generation.
2. For a partially filled entry, submit one idempotent cancel intent for the durable
   pending remainder. Do not infer cancellation from timeout or request acceptance.
3. Reconcile until broker evidence confirms the pending remainder is zero. Preserve
   any filled position and its exposure reservation.
4. Submit one idempotent close intent for the durable open-position volume. Do not
   select a browser-provided ticket or volume.
5. If invocation is ambiguous, leave the command UNKNOWN and use query-only
   reconciliation. Never resend under another ID.
6. Treat the trade as final only when the journal reports CLOSED, no exposure slot
   or active management command remains, and the final audit can be generated.

## Failure handling

- `STARTUP_REQUIRED`, stale/incomplete inventory, executor generation change or
  account mismatch: send nothing; restore and reconcile the full inventory first.
- `PENDING_CANCEL_REQUIRED`: cancel the confirmed pending remainder before close.
- `NO_PENDING_ORDER` or `NO_OPEN_POSITION`: do not manufacture a mutation; review
  current broker evidence and command binding.
- `MANAGEMENT_CONFLICT`: another nonterminal management command already owns this
  target. Reconcile it instead of creating a replacement.
- `UNKNOWN` or response loss: preserve the attempt and exposure, query broker state,
  and keep admission closed. An empty query is not proof that nothing happened.
- Journal/storage failure after invocation: effect is unconfirmed. Stop new work and
  recover durable storage before external reconciliation.
- Daily or total halt: keep it latched. New entries remain denied while authorized
  cancel/close remains possible after explicit startup. This path never releases a
  halt.

## Local verification

```bash
.venv/bin/pytest -q tests/test_position_management.py tests/test_recovery_audit.py --tb=short
bash scripts/check-scn-001-local.sh
```

The installed wheel probe exercises timeout-after-close, durable UNKNOWN and
query-only reconciliation in a fresh non-editable environment. Container evidence
must be tied to the candidate image, source hashes and verifier report. These checks
do not establish actual MT5 behavior or Demo release readiness.
