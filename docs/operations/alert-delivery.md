# Durable alert-delivery worker

Status: SCN-035 implements a disabled-by-default local worker, private alert-source
route, durable SQLite outbox, receipt reconciliation and owner UI status. It does not
select a real relay/provider/recipient, provision infrastructure or establish target
delivery evidence.

## API, process and UI positions

| Surface | Position | Access/effect |
| --- | --- | --- |
| Current alert source | `GET /internal/v1/alerts` | private service credential; redacted read only |
| Browser ingress | `/api/internal/*` | always `404`; never forwarded to the API |
| Worker command | `sochron-alert-delivery` | explicit `init`, `status`, `run`, `reconcile` actions |
| Relay write | `PUT /v1/sochron/notifications/{delivery_id}` | idempotent external effect after local journal commit |
| Relay read-back | `GET /v1/sochron/notifications/{delivery_id}` | independent retained-receipt evidence |
| Owner status | `GET /api/owner/alerts` | embeds redacted delivery state and counts |
| UI anchor | `#operational-alerts .delivery-ledger` | below API Budget, above lifecycle events |

The API service owns no destination credential. The browser receives no origin,
token or filesystem path. A relay receipt proves only that the configured relay
retained the canonical notification; it does not prove that a human read a message.

## Private source credential

Create a canonical owner-only directory (`0700`) and a single-link config file
(`0600`) with this exact shape:

```json
{
  "protocol": "sochron.alert-source-config.v1",
  "token": "replace_with_a_unique_43_plus_character_url_safe_random_token"
}
```

Generate a different random token for this boundary; do not reuse telemetry,
execution, Supabase or destination credentials. Select the file for the API with:

```text
SOCHRON_ALERT_SOURCE_CONFIG_FILE=/absolute/private/alert-source.json
```

The delivery worker reads the same source config. It must connect directly to the
private API network (for example the API service name in a reviewed target Compose
override), not through the web proxy.

## Destination credential and worker config

Put the destination bearer token alone in another single-link `0600` file. Create a
dedicated empty or retained `0700` state directory. Then create the worker config:

```json
{
  "enabled": true,
  "source_origin": "http://api:8000",
  "destination_origin": "https://relay.example.invalid",
  "source_config_file": "/absolute/private/alert-source.json",
  "destination_token_file": "/absolute/private/relay.token",
  "state_directory": "/absolute/private/alert-delivery-state",
  "destination_ref": "owner-primary-alert-channel",
  "poll_seconds": 30,
  "max_sends": 3
}
```

`.invalid` and all values above are schema illustrations, not working defaults or
authorization. Remote origins require HTTPS. Loopback HTTP is accepted only for
local synthetic verification. Source and destination tokens must differ. Select the
file only in the worker process:

```text
SOCHRON_ALERT_DELIVERY_CONFIG_FILE=/absolute/private/alert-delivery.json
```

Expose the redacted status to the API by mounting the same state directory read-only
or through an otherwise reviewed private mount and setting:

```text
SOCHRON_ALERT_DELIVERY_STATUS_DIR=/absolute/private/alert-delivery-state
```

The base `compose.yaml` and `compose.worker.yaml` do not start this networked worker.
A target-specific override must explicitly mount the three private objects, attach
the worker to the private API network and a bounded egress network, set the command
entrypoint to `sochron-alert-delivery`, and retain the state directory. Do not expose
worker ports.

## Operator lifecycle

With the config environment set:

```bash
sochron-alert-delivery init
sochron-alert-delivery status
sochron-alert-delivery run --once
sochron-alert-delivery reconcile
sochron-alert-delivery run
```

- `init` accepts only an empty private state directory and creates the lock, WAL
  journal and first normalized status snapshot.
- `run --once` performs at most one bounded step. Continuous `run` uses the configured
  poll interval and bounded backoff.
- `reconcile` queries only an existing `UNKNOWN` receipt. It never prepares or sends.
- `status` reports redacted counts and refreshes the worker heartbeat. It does not
  contact either source or destination.
- With no config, every command returns `DISABLED` without filesystem or network work.

## State and retry semantics

| State | Meaning and allowed next effect |
| --- | --- |
| `PREPARED` | canonical notification committed; a later step may begin one send |
| `UNKNOWN` | attempt committed before `PUT`; next step performs `GET` only |
| `VERIFIED` | separate `GET` returned the exact delivery ID and payload digest |
| `QUARANTINED` | destination conflict or retained evidence mismatch; stop automatically |
| `RETRY_BUDGET_EXHAUSTED` | confirmed-missing receipt returned to `PREPARED`, but attempts reached the configured limit |

An HTTP success from `PUT` is not delivery evidence. A lost or malformed response
remains `UNKNOWN`. A definite `404` from the receipt read returns the same immutable
intent to `PREPARED`; resend can occur only on a later step with the same delivery ID.

## Relay contract

The relay must retain one payload per path delivery ID and authenticate a separately
scoped bearer token. A successful read returns exactly:

```json
{
  "protocol": "sochron.alert-delivery-receipt.v1",
  "delivery_id": "32_lowercase_hex_characters_here",
  "destination_ref": "owner-primary-alert-channel",
  "payload_sha256": "64_lowercase_hex_characters_for_the_canonical_payload_digest_here",
  "accepted_at_utc": "2026-09-20T04:00:00Z"
}
```

The relay returns `404` only when the ID is definitely absent and `409` for an ID or
digest conflict. Provider-specific email/chat/SMS formatting and human-recipient
delivery occur behind this relay and require separate evidence.

## Backup, restore and target limits

The durable files are `alert-delivery.sqlite3`, its WAL/SHM files and the lock; the
status JSON is a replaceable projection. Use SQLite online backup or a verified
quiescent capture. Restore into an isolated directory with network dispatch disabled,
verify schema/binding/pending state, then run `reconcile` before any normal worker
step. Copying only the main SQLite file while WAL frames are active is not valid.

Target acceptance still requires the selected recipient, real relay credentials,
private-network routing, TLS, restart/network-loss/disk-full tests, escalation rules,
backup/restore within owner-selected RPO/RTO and retained delivery receipts. Local
synthetic tests do not clear the recovery/observability or unattended-Demo gate.

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_alert_delivery.py tests/test_operational_alerts.py
npx -y -p node@24.21.0 npm run test --workspace @sochron1k/web -- src/operational-alerts-api.test.ts src/OperationalAlertsPanel.test.tsx
```
