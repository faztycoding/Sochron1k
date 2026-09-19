# Local execution startup and denial handling

SCN-010 is an internal Python/simulator boundary, not an enabled trading service.
There is no HTTP/CLI command to enable execution or provision owner risk state.
Do not use synthetic account defaults or test helpers to configure an MT5 account.
API health and Auto Trading remain false for execution readiness.

For local development, configure the simulator's account/symbol independently,
provision a synthetic baseline explicitly in a temporary fixture journal, construct
ExecutionService, and call startup with the pinned policy, experiment and executor.
Never automatically initialize a missing baseline in a request handler. A new
service or process needs new admission; query-only recover is not admission.
See the [contract](../contracts/SCN-010-execution-startup.md),
[decision](../decisions/ADR-016-execution-startup-admission.md) and
[verification](../verification/SCN-010-execution-startup.md).

## Failure handling

- STARTUP_REQUIRED: do not submit. Perform the explicit inventory/risk admission
  only after reviewing the actual source of failure. Never retry a possibly sent
  command using a new identifier.
- Missing baseline, wrong Bangkok day or baseline mismatch: keep entries closed.
  Do not create/reset a baseline to make startup pass. Day rollover, cash flows
  and experiment changes need the defined reviewed lifecycle, not a config edit.
- Incomplete/stale/foreign/mismatched inventory: retain existing commands and
  exposure; investigate executor identity and complete orders/positions/history.
  An empty query is not proof of no execution.
- Unprotected fill: retain recorded fill/protection failure and use the separately
  authorized position-management procedure; startup does not close it automatically.
- Ambiguous send result: preserve UNKNOWN and the reservation. Journal write
  failure means persistence is not confirmed; retain failure evidence and reconcile
  externally before any new dispatch. No automatic resend exists here.
- Daily/total halt: startup and recovery preserve it. This module does not release
  a halt or promote a strategy. A successful inventory query is not halt-release
  authorization.

## Local verification commands

```bash
.venv/bin/pytest -q tests/test_execution_startup.py tests/test_execution_service.py --tb=short
bash scripts/check-scn-001-local.sh
```

The installed wheel verifier also runs `tests/fixtures/execution_startup_probe.py`
in a fresh non-editable environment with synthetic inputs. It is a test fixture,
not an owner operation command. Runtime/container results must match current
source and artifact hashes. Actual MT5 Demo and unattended readiness still need
the target-specific broker/build/permissions and release gates.
