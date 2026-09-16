# Local read-only MT5 bridge

Status: API ingress implemented and locally verified; EA and actual MT5 integration
remain unimplemented/unverified. This is not a Demo-ready or unattended release.
The bridge follows SCN-004 and ADR-004. Never put the credential in a browser,
Vite environment, command-line argument, screenshot, chat, fixture or Git file.

## What is available

| API route | Authorization | Meaning |
| --- | --- | --- |
| `GET /health` | None | API alive, Demo-only, execution still disabled |
| `GET /bridge/v1/status` | None | Redacted connection/age state, no account values or prices |
| `GET /bridge/v1/challenge` | Executor bearer token | Current process boot ID and next sequence |
| `POST /bridge/v1/snapshot` | Executor bearer token | Receive one sampled MT5 observation, no broker mutation |
| `GET /bridge/v1/snapshot` | Executor bearer token | Last observation, potentially stale or invalidated; read status separately |

Without a private configuration, protected routes return 503 and status is
`disabled`. Configuration never enables execution, even if inherited environment
variables request live or Auto Trading. The web console is not yet wired to these
routes; only its existing API health check is active.

## Local verification without a broker

These commands have run successfully with the pinned project environment:

```bash
.venv/bin/pytest -q tests/test_telemetry_bridge.py
.venv/bin/python scripts/check-bridge-local.py
bash scripts/check-scn-001-local.sh
```

The HTTP verifier owns an ephemeral loopback listener and one Uvicorn child. It
generates a synthetic configuration and random credential in a private temporary
directory, exercises the API over real HTTP, then stops only that child and
removes only its own temporary configuration. It does not connect to MT5, create
an account, send an order, change an existing stack or print credentials.
Its report identifies revision, dirty state, source hashes, runtime and fixture.

## Configuration to prepare after the owner chooses the Demo target

Provision an owner-only regular JSON file (mode 0600 or 0400) outside the repository
on the API host. Symlinks, group/other permissions, non-regular files, files owned
by another user and invalid configuration stop startup with a redacted error.
Use a separately generated URL-safe token with at least 32 random bytes (normally
43 characters), not an account password or Supabase key. The same narrowly scoped
credential will later be provisioned privately to the EA. The validator checks
format/length, not randomness; secure generation remains a provisioning requirement.

Required configuration fields:

- `identity.executor_id`: chosen local executor identifier.
- `identity.account_ref`: exact Demo account reference agreed with the EA.
- `identity.server`, `identity.currency`, `identity.symbol`: exact terminal values.
- `identity.margin_mode`: `retail_netting`, `retail_hedging` or `exchange`.
- `broker_utc_offset_seconds`: independently verified offset for the broker tick
  timestamp, positive east of UTC, in whole minutes. Do not assume Bangkok time.
- `token`: private telemetry credential; never include it in evidence output.

`SOCHRON_BRIDGE_CONFIG_FILE` points to that file. Run only one API worker, bound to
127.0.0.1, with access logs disabled. The real-HTTP verifier demonstrates this file
configuration path, but no real target configuration has been provisioned.
The current Compose topology does not mount this private file; ingress therefore
stays disabled there. Remote transport/TLS and secret mounts need a separate
operations verification, not an ad hoc public port.

## Wire contract for the EA work

The authoritative validated schema is `TelemetryFrame` in
`services/api/src/sochron1k/telemetry.py`. Every frame includes:

- `protocol=sochron.telemetry.v1`, `source=mt5-ea-sampled`, current `boot_id`, and a
  positive, strictly increasing integer `sequence` (within JSON-safe integer range).
- `identity` matching all six configured identity fields, explicit `trade_mode=demo`,
  actual `terminal_build`, `terminal_connected`, and `account_trade_allowed` booleans.
- `observed_at` as a timezone-aware UTC observation timestamp; raw integer
  `tick_time_server_msc`; explicitly verified `broker_utc_offset_seconds`.
- Finite decimal `equity`, `balance`, `free_margin`, `bid`, `ask`. Send decimals as
  strings to avoid wire float rounding. Negative account values remain observable;
  Bid/Ask must be positive and ordered. This does not authorize any risk decision.
- `contract`: exact symbol, digits, tick size, volume min/max/step, stops/freeze
  levels and filling modes (`fok`, `ioc`, `return`, `boc`). This is metadata only,
  not margin sufficiency, profit calculation or a successful execution preflight.

Obtain the challenge with the executor token before sending. On an API restart,
discard old queued samples and obtain a new boot ID; never relabel old data as a
new observation. The challenge GET does not reset state. A changed producer still
requires explicit local configuration; this protocol is not execution fencing.

The API owns `received_time_utc` and derives `event_time_utc` from the raw tick
timestamp and configured offset. Observations must arrive within five seconds and
cannot be future-dated. A tick up to one second ahead of observation is tolerated
for terminal clock granularity; a larger lead is rejected. An old tick can be
stored for diagnosis but remains stale even under a new heartbeat. No market-open
calendar is inferred. Snapshots are sampled, not a complete tick stream.

Exact duplicate sequence/content returns `duplicate=true` without changing receipt
time or clearing a rejection. Changed duplicates, decreasing sequence, reversed
observation/event times and old boot IDs fail closed. A new higher-sequence valid
frame is required to recover from a rejection. Unauthorized requests cannot
invalidate accepted telemetry. Startup always begins with no observation.

The body limit is 16 KiB and the body-read deadline is two seconds. JSON is required;
compressed, duplicate-key, non-finite, over-deep and invalid-schema input is rejected
without echoing it. All bridge responses are `Cache-Control: no-store`.

## Missing evidence and owner inputs

Needed next: broker, exact Demo server, chosen MT5 host/OS, terminal/MetaEditor
build, Demo currency/capital, exact symbol, margin mode and broker timestamp offset.
Do not send the account password in chat. Account reference and credential must be
configured locally through the approved secret channel.

Still required: compiled EA, actual read-only round trip, authenticated owner UI,
persistent bars/ticks/history, execution fencing, command/SL/reconciliation and
recovery gates, one separately authorized Demo open/close, alerts/restore and
target-host burn-in. Local ingress success does not satisfy those gates.
