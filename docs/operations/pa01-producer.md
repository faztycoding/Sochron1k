# Durable PA01 producer (SCN-022)

## Status and authority

The optional `sochron-pa01` worker can turn a verified local native M1 archive
plus one explicit policy-evidence file into an immutable Supabase signal. It is
disabled when `SOCHRON_PA01_CONFIG_FILE` is unset, is not in default Compose and
never creates a command, performs risk admission, calls MT5 or enables Auto
Trading.

SCN-023 now supplies the disabled-by-default writer that combines authenticated
MT5 quote/session and execution-inventory evidence with an owner-private news gate.
It remains unusable as actual Demo evidence until that writer is configured with a
real, coverage-complete news source and actual compiled MT5 adapters. Do not
hand-edit or hard-code the policy file and describe it as actual Demo evidence.
Local checks use generated values only. See
[the policy writer runbook](policy-evidence-writer.md).

Do not point this worker at hosted Supabase without explicit authorization for the
project and write effect. The service key is a backend credential that bypasses
RLS and must never reach the browser, repository, command line or logs.

## Private configuration

`SOCHRON_PA01_CONFIG_FILE` contains only a canonical absolute path. An unset
variable or a private file containing exactly `{"enabled":false}` returns
`DISABLED` without opening the archive, journal, policy file or network.

An enabled file requires exactly:

| Field | Required value |
| --- | --- |
| `enabled` | boolean `true` |
| `source_directory` | Existing private SCN-007 archive directory |
| `state_directory` | Separate existing empty private directory for `init` |
| `policy_file` | Separate owner-only PA01 policy JSON described below |
| `archive_id` | Exact canonical UUID from that archive |
| `identity` | Exact Demo executor/account/server/currency/margin-mode/symbol object |
| `offset_seconds` | Verified broker offset, integer seconds divisible by 60 |
| `chart` | Exact offset-valid-from/until server-second interval |
| `owner_id` | Exact Supabase owner UUID |
| `strategy_version_id` | Positive database ID for the registered `PA01-v1` row |
| `experiment_id` | Positive database ID for its eligible draft/shadow/Demo experiment |
| `code_hash` | Lowercase SHA-256 registered on the strategy version |
| `origin` | Pinned HTTPS Supabase origin or guarded loopback local origin |
| `service_key_file` | Separate owner-only backend key file |

Configuration, policy and key must be stable regular files owned by the worker
UID, single-link and mode 0600 or stricter; parents and state/source directories
must be 0700. Paths are canonical and absolute. Keep policy/config/key outside the
state directory. The source and state directories must differ.

The service key format, origin restrictions and TLS behavior match the
[native M1 worker](native-m1-sync.md#private-configuration): no redirect,
environment proxy, custom TLS disablement, URL credentials/path/query or public
key is accepted.

## Policy-evidence handoff

The file is the JSON serialization of `sochron.pa01.policy-context.v1` input. It
contains only these fields:

```json
{
  "cutoff_utc": "2026-09-20T02:05:02Z",
  "symbol": "XAUUSD.example",
  "feed_id": "mt5-copyrates:00000000-0000-4000-8000-000000000000",
  "spread_price": "0.20",
  "market_open": true,
  "price_stale": false,
  "news_blocked": false,
  "has_exposure": false,
  "has_pending": false,
  "ai_enabled": false,
  "observations": {
    "quote": {"evidence_id": "quote:example", "observed_at_utc": "2026-09-20T02:05:02Z"},
    "market": {"evidence_id": "session:example", "observed_at_utc": "2026-09-20T02:05:01Z"},
    "news": {"evidence_id": "news:example", "observed_at_utc": "2026-09-20T02:05:00Z"},
    "account": {"evidence_id": "account:example", "observed_at_utc": "2026-09-20T02:05:01Z"}
  }
}
```

Those are shape examples, not values to reuse. `spread_price` is an exact decimal
string. All observation IDs must be unique and all UTC times must be causal. The
feed ID must equal `mt5-copyrates:<archive_id>`. If market is claimed open and the
price is claimed fresh, quote evidence may be at most five seconds old at cutoff.

The handoff writer must collect the four observations as one coherent decision
cutoff and publish the file using an atomic owner-only replacement. It must not
infer missing news/session/exposure evidence. A new decision is prepared only
while the cutoff remains within the 30-second signal lifetime and only for a
strictly newer closed M5 bar. A stale, future, partial, replaced-during-read or
malformed file fails closed as `PA01_SOURCE_UNAVAILABLE`.

## Explicit commands

For a source checkout:

```bash
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker.pa01_cli init
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker.pa01_cli status
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker.pa01_cli reconcile
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker.pa01_cli run --once
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker.pa01_cli run
```

For a reviewed installed wheel, use the `sochron-pa01` command. `init` is local
only and refuses nonempty state. `status` requires config/archive/journal but no
key or network. `run --once` performs one bounded prepare/send/read or UNKNOWN
read. Continuous `run` polls serially and stops after five consecutive unresolved
steps. Do not add an automatic restart that bypasses retry exhaustion.

`reconcile` performs one read only. UNKNOWN is never resent during that same step.
A missing row becomes PREPARED for later reviewed `run`; exact evidence becomes
VERIFIED; confirmed conflict or malformed/foreign evidence becomes permanently
QUARANTINED. There is intentionally no reset or unquarantine command.

Every status keeps `execution_ready=false` and `auto_trading_enabled=false`.
`IDLE` means no newer M5 decision for the currently supplied policy cutoff, not a
healthy broker, complete news feed or release-ready system.

## UI/API placement

This worker writes the backend rows consumed by:

`Supabase signals/feature_snapshots -> GET /api/owner/signals -> Signals panel`

The browser never calls the producer RPC and never receives its key. The connection
rail can show the Signals API as implemented while the authenticated panel remains
`awaiting_source` until a verified producer row exists. A displayed BUY/SELL row
is evidence only; it does not become a command.

## Recovery and remaining gaps

Stop the worker and retain `pa01.sqlite3`, its WAL/SHM and `pa01.lock`. Never
initialize a second directory to escape UNKNOWN or quarantine. Restore destination
access, run `reconcile`, and inspect any PREPARED/QUARANTINED result before another
send. The journal is capped at 64 MiB for its main database and reports 70/85%
warnings; no automatic pruning exists.

Still required before unattended Demo: a real news-gate collector, writer/producer
private target configuration, target scheduler/service definition, target
backup/restore and burn-in, hosted project authorization/credentials, actual MT5
data parity and all release gates. Statistics also remain empty until the separate
reproducible evaluation producer exists.
