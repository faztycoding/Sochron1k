# Demo execution bridge operations

Status: API-side SCN-012 transport is implemented and locally verified with
synthetic fixtures. SCN-024 adds an uncompiled, default-off MQL source that can
upload policy-only current-empty inventory while hard-coding algorithmic trading
false. SCN-028 now adds a distinct, default-off mutation EA source with a local
ledger, exact Demo fence, broker preflight and cumulative reconciliation. It has
not been compiled, attached, connected or allowed to make a broker request, and
the current Compose topology does not mount its private configuration or establish
the MT5 loopback path. It is not a Demo release gate or unattended-trading
authorization.

## Internal routes

| Route | Authorization | Meaning |
| --- | --- | --- |
| `GET /executor/v1/status` | None | Redacted disabled/awaiting/connected/stale/rejected state |
| `GET /executor/v1/challenge` | Executor Bearer token | Current API boot fence and next inventory sequence |
| `POST /executor/v1/inventory` | Executor Bearer token | Fresh cumulative Demo executor inventory |
| `GET /executor/v1/commands/next` | Executor Bearer token | Claim or repeat one journal-approved dispatch; `204` means none |
| `POST /executor/v1/outcomes` | Executor Bearer token | Bound cumulative snapshot, confirmed rejection or uncertainty |

All responses use `Cache-Control: no-store`. The public health response still says
`execution_ready=false` and `auto_trading_enabled=false`. There is no browser or
owner route that creates an execution command.

The browser-safe route map is in
[`read-only-execution-inventory.md`](read-only-execution-inventory.md). The
read-only observer may satisfy the policy writer's empty-account source without
changing the normal execution status from non-ready. It does not feed the owner
execution journal panel.

Every current `sochron.execution.command.v1` response has exactly 24 fields.
Entry commands carry decimal-string `risk_limit` and `cost_budget`; management
commands carry both as `null`. These values are persisted beside the API dispatch
attempt before the command is exposed. They are account-currency authorization,
not evidence that broker loss has already been calculated.

The SCN-027 codec encodes cumulative entry/deal/SL and management evidence. The
SCN-028 source EA now populates that schema from bounded MT5 current/history reads,
but this behavior remains uncompiled and unobserved on a terminal.

## Private API configuration

Create an owner-only regular JSON file (mode `0600` or `0400`) outside the
repository. Do not use a symlink, account password, telemetry token, owner token,
Supabase key, screenshot, command-line argument or committed environment file.
Generate at least 32 random bytes and encode them URL-safe for the dedicated token.

The file has this shape; placeholders are not valid target values:

```json
{
  "identity": {
    "executor_id": "chosen-single-executor-id",
    "account_ref": "exact-demo-login",
    "server": "exact-demo-server",
    "currency": "USD",
    "margin_mode": "retail_hedging",
    "symbol": "exact-broker-symbol"
  },
  "token": "generated-separate-url-safe-secret",
  "magic_number": 910001,
  "response_timeout_seconds": "2.000"
}
```

Point `SOCHRON_EXECUTION_BRIDGE_CONFIG_FILE` to the canonical target file before
starting the single API process. Missing configuration is a safe disabled state;
invalid ownership, permissions, JSON or value fails startup with a redacted error.
If the telemetry bridge is also enabled, its token must differ.

Do not expose these routes to the public Internet with an ad hoc port. The final
host requires a separately verified narrow network path, TLS/auth design, secret
mount, access-log redaction and firewall rule. This repository has not established
those target controls.

## EA lifecycle required by the contract

1. Fetch the authenticated challenge after every API restart.
2. Reconcile MT5 orders, deals, positions, broker-side SL and known no-effect
   rejections, then post one complete fresh inventory under that boot fence.
3. Poll for a command with short bounded HTTP timeouts. Network I/O must never block
   the broker-risk event loop.
4. Before any mutation, locally recheck Demo mode, exact account/server/symbol,
   terminal trading permission, magic number, contract metadata, freshness, command
   expiry and local attempt/command idempotency.
5. For an entry, use `OrderCalcProfit` with current broker metadata and deny when
   absolute entry-to-SL loss plus `cost_budget` exceeds `risk_limit`. Journal the
   local attempt, run `OrderCheck`, issue at most the exact claimed mutation, and
   reconcile `OnTradeTransaction`, orders, history and positions.
6. Report a cumulative snapshot. Report confirmed rejection only after both the
   reviewed return code and reconciled absence of any effect. Report timeout,
   disconnect, processing or conflicting state as uncertain.
7. Repeat the exact same outcome after a lost HTTP response. Never create a new
   broker request just because outcome delivery failed.

SCN-028 additionally caps that same loss-plus-cost amount at 0.25% of current MT5
Equity, rounded down for the allowed budget in account-currency precision. The
dispatched limit remains an upper bound; a later Equity decline cannot make the EA
increase risk.

An HTTP 200 acknowledges only API validation/receipt. It is not a fill, close,
cancel or protection claim. `OrderSend=true` is also not enough; the cumulative
broker snapshot must prove the state.

## SCN-028 source boundary

The reviewed source is `mt5/ea/SochronDemoExecutor.mq5` with
`ExecutionRuntime.mqh`, `ExecutionLedger.mqh`, `ExecutionProtocol.mqh` and
`TelemetryProtocol.mqh`. Its committed default is disabled. The executor token,
lock and ledger names are fixed and terminal-local; no token, password or URL is
an EA input. The lock and ledger omit sharing flags, and ledger records use
single-byte ASCII plus explicit flushes. Those design choices still require an
actual second-instance denial test and power/crash recovery evidence on the
selected filesystem.

Source admission is:

```bash
.venv/bin/python scripts/check-demo-executor-source.py
.venv/bin/pytest -q tests/test_demo_executor_source.py tests/test_execution_bridge.py
```

The guard constrains the include graph, fixed files/routes, default-off start,
Demo-only identifiers, one send/check call site, journal ordering, repeated scans,
bounded callback and broker risk gate. It deliberately reports compilation,
runtime locking/durability, account access, broker operation and Demo round trip as
`NOT RUN`.

## Local verification

The focused verifier is the test module below; the full safety gate also checks
the complete package, recovery schema and unrelated boundaries:

```bash
.venv/bin/python -m pytest -q tests/test_execution_bridge.py tests/test_executor_rejection.py
bash scripts/check-scn-001-local.sh
```

These use only synthetic local state. The SCN-026 source guard checks the exact
24-field risk envelope, SCN-024 keeps the observer mutation-free, and SCN-028
checks the mutation-source boundary. Actual MetaEditor compilation, EA HTTP,
account reads and trade APIs, target-host network loss, terminal restart, broker
return codes and an owner-authorized Demo open/close remain `NOT RUN`.

## Inputs still required for a real Demo target

- broker name and exact Demo server;
- Demo account reference, currency and starting capital (password through the
  approved private secret channel, never chat or Git);
- exact XAU/USD symbol and measured contract specification;
- netting or hedging mode, trading hours and overnight policy;
- selected terminal/MetaEditor build and executor host/OS;
- approved magic number and separate token provisioning path;
- named halt-release authority, alert destination and explicit authorization for
  the first bounded Demo open-to-close dry run.

Until those inputs and the remaining compile/target gates pass, leave this bridge
and EA disabled and do not label the system Demo-ready.
