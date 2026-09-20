# Read-only MT5 execution inventory (SCN-024)

## What this component closes

`mt5/ea/SochronExecutionInventory.mq5` is a separately opt-in observer for the
execution side of the PA01 policy handoff. It reads the selected Demo account's
current orders and positions, proves that the configured symbol/magic has no
current effect, and uploads an authenticated inventory to the API. It hard-codes
`algo_trading_allowed=false`, never polls commands, and never sends a broker
request.

This is source-level integration, not an MT5-verified release. MetaEditor
compilation, actual account reads, the MT5-to-API network path and broker parity
remain `NOT RUN`.

## API and UI placement

The paths are intentionally different because the browser must never receive the
executor credential or its private raw inventory.

| Producer or consumer | Route seen at the web proxy | FastAPI route | Purpose |
| --- | --- | --- | --- |
| MT5 observer | not browser-accessible | `GET /executor/v1/challenge` | obtain API boot fence and next sequence |
| MT5 observer | not browser-accessible | `POST /executor/v1/inventory` | upload current Demo inventory |
| Connection rail | `GET /api/ui/connections` | `GET /ui/connections` | show redacted MT5 execution integration state |
| Owner execution panel | `GET /api/owner/execution` | `GET /owner/execution` | show durable command/order/deal/position evidence once the full executor journal exists |
| Signals connection/status | `GET /api/policy/v1/status` | `GET /policy/v1/status` | show whether quote/session, inventory and News Gate are ready for policy writing |

The inventory observer can make the policy inventory source ready only when the
current scan is stable, complete, foreign-free and empty for the configured
symbol/magic. `/api/executor/v1/status` still reports a non-ready execution state
because algorithmic trading is false. The owner execution panel remains disabled
or empty until a full durable execution journal is configured; this observer does
not manufacture command history for that panel.

## Private configuration

Create the existing execution-bridge JSON described in
`docs/operations/execution-bridge.md`, keep it owner-only, and set
`SOCHRON_EXECUTION_BRIDGE_CONFIG_FILE` for the API process. The bridge identity,
magic number and token must exactly match the observer inputs and terminal-local
token file.

Keep `EnableReadOnlyExecutionInventory=false` until the selected host checks are
complete. When authorized for the named Demo target, configure these non-secret
EA inputs:

- exact Demo login, server, currency, margin mode and chart symbol;
- exact executor ID and positive magic number from the API config;
- no password, token or URL input.

Provision the separate bearer token as raw URL-safe ASCII in the terminal-local
`MQL5/Files/sochron-execution.token`, without BOM, whitespace or newline. Do not
commit it or pass it through chat, screenshots, command arguments or `.set` files.
Keep the telemetry and execution tokens different.

The source destination is fixed to
`http://127.0.0.1:8000/executor/v1`. The current Compose topology does not publish
that API port to the host, so it is **not** evidence of a working MT5 route. The
selected deployment must provide and verify a narrow loopback path without
exposing executor routes publicly or broadening the source URL. Wine and remote
Windows `localhost` behavior must be measured on the actual layout.

## Selected-host verification still required

1. Record terminal and MetaEditor builds, host/OS or Wine version and source hash.
2. Copy `SochronExecutionInventory.mq5` and `ExecutionProtocol.mqh` into one
   isolated `MQL5/Experts` folder and compile with zero errors and zero warnings.
3. Keep Auto Trading disabled. Attach only to the authorized Demo symbol and
   confirm the EA remains `DISABLED` with its default input.
4. Configure the exact identity and token, allow only the required local
   WebRequest origin, then opt in to read-only inventory.
5. Compare the API's redacted status with MT5's actual current orders/positions.
   Test empty, foreign-item, owned-item, identity-change, API restart, disconnect,
   lost response and account-switch cases. Owned or foreign state must stop policy
   readiness; none may make execution ready.
6. Retain redacted timestamps, build/source/artifact hashes and route results. Do
   not retain credentials, balances, account numbers or unrestricted logs in Git.

## What remains for the full execution path

This observer cannot satisfy order execution or recovery. A separate default-off
EA still needs an exclusive executor lock, durable local attempt ledger, command
polling, immediate Demo/risk preflight, `OrderCheck`, the exact broker mutation,
`OnTradeTransaction` reconciliation, cumulative order/deal/position/SL inventory,
`UNKNOWN` recovery, restart tests and an explicitly authorized bounded Demo dry
run. Auto Trading stays off until those gates pass.
