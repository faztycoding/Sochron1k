# Operational alerts and owner lifecycle

Status: SCN-032 provides the owner-authenticated detector inventory, SCN-033 adds a
local durable acknowledgement/resolution workflow, SCN-034 adds provider-neutral
API-budget evidence, and SCN-035 adds a disabled-by-default receipt-capable delivery
worker. No real recipient/provider or target delivery has been selected or tested;
none of these boundaries authorizes a broker operation or satisfies the target
recovery/observability gate.

## UI and API positions

| Surface | Browser route | API route | Effect |
| --- | --- | --- | --- |
| Alert center | `GET /api/owner/alerts` | `GET /owner/alerts` | derive facts and merge retained lifecycle; no write |
| Acknowledge | `POST /api/owner/alerts/{condition_id}/acknowledge` | same path without `/api` | owner lifecycle write only |
| Resolve workflow | `POST /api/owner/alerts/{condition_id}/resolve` | same path without `/api` | guarded owner lifecycle write only |
| API budget | `GET /api/owner/api-budget` | `GET /owner/api-budget` | normalized cost snapshot and owner policy; no write |
| Delivery status | embedded in `GET /api/owner/alerts` | normalized private worker status | outbox/receipt projection; no destination credential |
| Worker source | blocked at browser ingress | `GET /internal/v1/alerts` | separate service-authenticated redacted facts |
| Connection map | `GET /api/ui/connections` | `GET /ui/connections` | fixed redacted API/source inventory |
| UI anchor | `#operational-alerts` | n/a | below account telemetry and above the market chart |

All owner routes use the same online owner/session verification and return
`Cache-Control: no-store`. Both POST routes require exactly one canonical UUID
`Idempotency-Key`. Reusing it with the same owner/action/condition replays the
committed receipt; reusing it for another mutation conflicts.

## Detector/source mapping

| Alert kind | Evidence route | Required source/configuration |
| --- | --- | --- |
| `order_reject` | `/api/owner/execution` | `SOCHRON_EXECUTION_JOURNAL_PATH` |
| `no_sl` | `/api/owner/execution` | open journal volume without broker-confirmed SL |
| `risk_halt` | `/api/owner/execution` | durable `risk_state` halt flags |
| `unknown_execution` | `/api/owner/execution` | entry/management state `unknown` |
| `stale_price` | `/api/owner/telemetry` | configured telemetry bridge and current heartbeat/price |
| `bridge_disconnected` | telemetry/executor/policy/budget status routes | configured source status |
| `storage_limit` | `/api/owner/history/{timeframe}` | `SOCHRON_CHART_HISTORY_DIR` and archive page use |
| `api_budget` | `/api/owner/api-budget` | `SOCHRON_API_BUDGET_CONFIG_FILE` plus provider collector snapshot |

Journal references and condition identifiers are deterministic hashes. The API
does not return account reference, server, owner UUID, credentials, raw payload or
filesystem path. Results are bounded and report truncation.

## Configure the lifecycle journal

Leave `SOCHRON_ALERT_LIFECYCLE_DIR` unset to keep both mutations disabled. Reads
continue with `lifecycle_runtime="awaiting_configuration"`.

For a local or target candidate, create one dedicated empty or retained directory
on the intended durable filesystem. It must be canonical and absolute, owned by
the API runtime UID and mode `0700`. Then set:

```text
SOCHRON_ALERT_LIFECYCLE_DIR=/absolute/private/sochron-alert-lifecycle
```

The API safely creates `alerts.sqlite3` mode `0600` when absent. An existing file
must retain its exact schema and pass integrity, ownership, permission and file
identity checks. The database uses WAL, full synchronization and a 32 MiB page
limit. Invalid configuration stops startup; later replacement, corruption, lock,
clock regression or write failure degrades lifecycle access and does not fabricate
a successful transition.

Do not place the directory in a browser-served tree, shared download directory or
ephemeral container layer. The base Compose file mounts `/app/data` read-write,
but this task does not prepare a correctly owned subdirectory or establish its
backup/restore behavior on a target host.

## Lifecycle meanings

| UI state | Meaning | Allowed next action |
| --- | --- | --- |
| `active` | detector currently emits the episode; not acknowledged | acknowledge when the journal is connected |
| `acknowledged` | owner workflow recorded; source condition may still be active | wait for source clearance; retained `order_reject` may resolve |
| `cleared` | detector no longer emits it and the applicable source is complete | owner may resolve the workflow |
| `resolved` | owner closed the workflow episode | no action; a later observation becomes a new episode |
| `unavailable` | lifecycle/source completeness cannot be proved | no mutation |

Acknowledgement records `acknowledged_by="owner"` rather than exposing the owner
UUID. Resolution requires prior acknowledgement. `no_sl`, `risk_halt`,
`unknown_execution`, `stale_price`, `bridge_disconnected` and `storage_limit`
cannot resolve while currently detected. `order_reject` is an immutable occurred
event and may resolve after acknowledgement even while its retained execution
evidence remains visible.

These fields describe local operator workflow only. `delivery_configured` says only
whether a status directory was selected. `disabled`, `awaiting_worker`, `pending`,
`UNKNOWN` and verified relay receipts remain distinct. See the
[alert-delivery runbook](alert-delivery.md); no email, SMS, chat, webhook or human
recipient is claimed without selected-provider evidence.

## Configure API-budget evidence

See the [API-budget runbook](api-budget.md). Leaving
`SOCHRON_API_BUDGET_CONFIG_FILE` empty reports `disabled` and never invents usage.
The exact currency, monthly limit and warning/critical fractions are owner inputs.
The provider collector remains missing until one is selected, credentialed and
tested against its real bill.

## Recovery and evidence limits

- Stop the API or use a reviewed SQLite online-backup procedure before copying the
  lifecycle journal. Copying only `alerts.sqlite3` while WAL frames are active is
  not a verified backup.
- A restore is not accepted until the API opens the retained private directory and
  focused restart/invariant checks pass. Target backup/restore is currently not run.
- There is no lifecycle purge/export workflow yet. Storage-limit or retention work
  must preserve immutable mutation receipts and requires a separate contract.
- Local synthetic checks do not prove target filesystem durability, notification
  delivery, escalation, MT5 behavior or unattended-Demo readiness.

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_operational_alerts.py
.venv/bin/python -m pytest -q tests/test_api_budget.py
npx -y -p node@24.21.0 npm run test --workspace @sochron1k/web -- src/operational-alerts-api.test.ts src/OperationalAlertsPanel.test.tsx
```

## Remaining target work

1. Owner selects the external alert destination, runtime billing provider, currency,
   monthly limit and warning/critical fractions.
2. Implement the provider-specific credential-isolated collector against the
   normalized snapshot and compare it with the actual bill.
3. Select and provision the receipt-capable relay/provider and recipient; exercise
   the implemented durable outbox/read-back path, then add tested escalation rules.
4. Define lifecycle retention plus tested target backup/restore and disk-exhaustion
   behavior.
5. Exercise stale feed, rejected SL, UNKNOWN, risk halt, bridge loss, disk pressure
   and delivery failure on the selected target; retain timing and receipt evidence.
6. Keep the SCN-031 recovery/observability gate `not_run` until target restart,
   network-loss, restore and delivered-alert evidence all pass.
