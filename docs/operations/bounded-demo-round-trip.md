# Bounded Demo round-trip operations

Status: SCN-037 is locally implemented and disabled by default. This runbook does
not authorize an MT5 operation. Use it only after the project owner separately
approves the exact Demo account, source revision, command identifiers and test
effect. Never use it with a live or contest account.

## API positions

| Private API route | Purpose |
| --- | --- |
| `GET /internal/v1/demo-round-trip/status` | Redacted disabled/baseline/startup/armed/recorded/complete state |
| `POST /internal/v1/demo-round-trip/risk-baseline` | Create the first risk baseline from fresh empty Demo inventory |
| `POST /internal/v1/demo-round-trip/startup` | Reconcile journal, risk and MT5 inventory before mutation |
| `POST /internal/v1/demo-round-trip/open` | Submit only the configured entry while authorization is current |
| `POST /internal/v1/demo-round-trip/cancel` | Cancel the configured entry's confirmed pending remainder |
| `POST /internal/v1/demo-round-trip/close` | Close the configured entry's confirmed open position |
| `POST /internal/v1/demo-round-trip/reconcile/{command_id}` | Query and apply evidence for one configured command; never resend |

All POST routes require the dedicated bearer credential. The web nginx route
`/api/internal/` returns 404, so these actions are not browser controls. Blocking
executor waits run in FastAPI's sync worker thread. All responses are `no-store`.

## Private configuration

Create the journal/config parent directory as the API UID with mode `0700`. Store
the config as a regular `0600` file outside Git. Generate a dedicated URL-safe
token from at least 32 random bytes; it must differ from telemetry, executor,
owner, alert and provider credentials. Place MT5 passwords only in the approved
executor secret channel, never in this file.

```json
{
  "protocol": "sochron.demo-round-trip-config.v1",
  "identity": {
    "executor_id": "reviewed-executor-id",
    "account_ref": "exact-demo-login",
    "server": "exact-demo-server",
    "currency": "USD",
    "margin_mode": "retail_hedging",
    "symbol": "exact-broker-symbol"
  },
  "token": "generated-separate-url-safe-service-secret",
  "journal_file": "/private/sochron/commands.sqlite3",
  "source_revision": "40-character-deployed-git-commit",
  "decision_revision": "reviewed-owner-decision-revision",
  "experiment_id": "reviewed-experiment-id",
  "signal_id": "reviewed-signal-id",
  "strategy_version": "PA01-v1",
  "entry_command_id": "reviewed-entry-command-id",
  "cancel_command_id": "reviewed-cancel-command-id",
  "close_command_id": "reviewed-close-command-id",
  "experiment_baseline": "10000.00",
  "minimum_costs_per_lot": "1.00",
  "authorized_at_utc": "2026-09-20T08:00:00Z",
  "entry_authorization_expires_at_utc": "2026-09-20T08:15:00Z"
}
```

Set `SOCHRON_DEMO_ROUND_TRIP_CONFIG_FILE` to the canonical config path and
`SOCHRON_SOURCE_REVISION` to the same exact deployed Git revision. The execution
bridge config and owner-decision record must also be present and match identity,
account mode, currency, symbol, starting capital and magic number. Mismatch fails
API startup with a redacted error. Missing round-trip config is inert.

## Required sequence

1. Confirm the target artifact gate and exact Demo identity out of band. Keep the
   normal application UI read-only and Auto Trading status off.
2. Start one API process with the private configs and narrow executor-only network.
   Do not expose the internal route through the web proxy or public port.
3. Attach the reviewed EA to the exact Demo terminal and obtain complete fresh
   empty inventory. If any order, position, known snapshot or foreign effect is
   present, baseline creation fails closed.
4. Call `risk-baseline`, then `startup`. A replay returns the existing baseline but
   never changes its day, capital or halt state.
5. Submit the exact configured open envelope. Contract, market and risk inputs are
   typed API evidence; MT5 independently rechecks current contract/tick/session,
   `OrderCalcProfit`, cost/risk cap, margin and `OrderCheck` before its single send.
6. If the result is `UNKNOWN`, call reconcile for the same command. Do not issue a
   new command or change the config to force a retry.
7. If partially filled, cancel the pending remainder before close. Call startup
   again after restart, changed executor generation or reconciliation.
8. Close the confirmed position. Entry authorization expiry and a risk halt do not
   disable cancel/close. Preserve journal, EA ledger and MT5 evidence.
9. Run the target verifier, admit normalized evidence separately and leave
   operational authorization false until all remaining target gates are reviewed.

## Failure rules

- `401` means the service credential is absent, duplicated or wrong.
- `409` is a deterministic admission denial such as wrong command binding, stale
  authorization, missing baseline, halt, pending-before-close or startup mismatch.
- `503` means required durable/executor state is unavailable. It is not proof that
  an attempted broker write had no effect; inspect journal and reconcile MT5.
- Never replace the SQLite journal, clear a halt, widen an SL or change a command
  identifier to make the test pass.

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_demo_round_trip.py tests/test_execution_service.py tests/test_execution_bridge.py tests/test_position_management.py
bash scripts/check-scn-001-local.sh
```

These tests use synthetic adapters and do not authorize or prove an MT5 operation.
