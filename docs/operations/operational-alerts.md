# Operational alert inventory

Status: SCN-032 provides an owner-authenticated, read-only detector inventory. It
does not send notifications, persist acknowledgement/resolution, authorize a
broker operation or satisfy the target recovery/observability gate.

## UI and API positions

| Surface | Browser route | API route | Source |
| --- | --- | --- | --- |
| Owner alert center | `GET /api/owner/alerts` | `GET /owner/alerts` | derived states below |
| Connection map | `GET /api/ui/connections` | `GET /ui/connections` | fixed redacted route/source inventory |
| UI anchor | `#operational-alerts` | n/a | owner workspace immediately below account telemetry |

The owner route uses the same online owner/session verification as the other
private reads and returns `Cache-Control: no-store`. It has no POST/PATCH/DELETE
route and hard-codes Demo mode, Auto Trading off, execution not ready, read-only
and external delivery not configured.

## Detector/source mapping

| Alert kind | Evidence route | Required source/configuration |
| --- | --- | --- |
| `order_reject` | `/api/owner/execution` | `SOCHRON_EXECUTION_JOURNAL_PATH` |
| `no_sl` | `/api/owner/execution` | open journal volume without broker-confirmed SL |
| `risk_halt` | `/api/owner/execution` | durable `risk_state` halt flags |
| `unknown_execution` | `/api/owner/execution` | entry/management state `unknown` |
| `stale_price` | `/api/owner/telemetry` | configured telemetry bridge and current heartbeat/price |
| `bridge_disconnected` | telemetry/executor/policy status routes | configured source status |
| `storage_limit` | `/api/owner/history/{timeframe}` | `SOCHRON_CHART_HISTORY_DIR` and archive page use |
| `api_budget` | `/api/owner/alerts` | **not implemented**; owner-selected bounded provider-cost source required |

Journal references returned by the alert route are deterministic hashes; account
reference, server, payload, credentials and filesystem paths are not returned.
Results are bounded and report truncation. Replaced, malformed or unavailable
configured sources degrade the response and do not become an all-clear state.

## Meaning of lifecycle fields

`acknowledged_by` and `resolved_at_utc` are always null in SCN-032. No operator
acknowledgement or resolution has been recorded. A later task must specify durable
storage, authorization, idempotency, retention and recovery before adding a
mutation route.

`delivery_configured=false` means no email, SMS, chat, webhook or push destination
was invoked. The owner decision record's redacted destination reference does not
configure or test delivery by itself.

## Next target work

1. Owner selects the external alert destination and monthly provider/API budget.
2. Define the durable alert lifecycle and narrowly authorized acknowledgement
   mutation in a separate contract/ADR.
3. Implement bounded delivery with retries, idempotency, escalation and safe
   credential handling.
4. Exercise stale feed, rejected SL, UNKNOWN, risk halt, bridge loss, disk pressure
   and delivery failure on the selected target; retain timing and receipt evidence.
5. Keep the SCN-031 recovery/observability gate `not_run` until target restart,
   network-loss, backup/restore and alert evidence all pass.

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_operational_alerts.py tests/test_execution_evidence.py tests/test_bar_history.py
npx -y -p node@24.21.0 npm run test --workspace @sochron1k/web -- src/operational-alerts-api.test.ts src/OperationalAlertsPanel.test.tsx
```

These commands use synthetic local sources only. They do not connect MT5, send a
notification, write a hosted service, deploy a target or clear a release gate.
