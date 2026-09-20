# Coherent PA01 policy-evidence writer (SCN-023)

## Status and authority

The API can now create the strict policy file consumed by the optional SCN-022
PA01 producer. It combines authenticated MT5 telemetry v2, authenticated complete
execution inventory and one separate news-gate coverage file. It never runs the
strategy producer, writes Supabase, creates a command, performs risk admission or
enables Auto Trading.

The writer is disabled when `SOCHRON_POLICY_WRITER_CONFIG_FILE` is unset or its
private JSON contains exactly `{"enabled":false}`. API startup performs no policy
write. After enabled startup, every accepted telemetry or inventory update queues
one bounded refresh; a write occurs only while all sources are fresh and causal.

## UI/API placement

The complete Signals path is:

```text
MT5 Telemetry v2 (quote + symbol trade session) ----\
MT5 Execution inventory (exposure + pending) -------+-> API policy writer
Owner-private News Gate (coverage + revision) ------/       |
                                                            v
                                          owner-private policy.json
                                                            |
                                                            v
                              sochron-pa01 -> Supabase -> /api/owner/signals
```

The public browser-safe status is `GET /api/policy/v1/status` (FastAPI route
`GET /policy/v1/status`). The connection rail shows this route immediately before
`/api/owner/signals`. Status includes only source-ready booleans, a safe timestamp,
Demo/Auto-off flags and `disabled`, `awaiting_sources`, `ready` or `degraded`.
It never returns identities, prices, balances, news IDs/revisions, paths or tokens.

## Private writer configuration

Set `SOCHRON_POLICY_WRITER_CONFIG_FILE` to one canonical absolute owner-private
regular file in an owner-private directory. The enabled file contains exactly:

```json
{
  "enabled": true,
  "identity": {
    "executor_id": "exact configured executor ID",
    "account_ref": "exact Demo login string",
    "server": "exact Demo server",
    "currency": "USD",
    "margin_mode": "retail_hedging",
    "symbol": "exact broker symbol"
  },
  "archive_id": "00000000-0000-4000-8000-000000000000",
  "output_file": "/absolute/private/policy.json",
  "news_gate_file": "/absolute/private/news-gate.json"
}
```

The example values are placeholders, not evidence. The identity must exactly match
both loaded telemetry and execution-bridge configurations. Paths must differ;
their existing parents must be canonical, owned by the API UID and mode 0700 or
stricter. Existing files must be single-link owner files and mode 0600 or stricter.
The archive UUID must match the SCN-007 archive configured in the PA01 producer;
the worker independently rejects a different feed identity.

The output path must be the same `policy_file` configured for `sochron-pa01`. The
writer creates a synced 0600 temporary inode in the same directory, atomically
replaces `policy.json`, then syncs the parent directory. It never writes in place.
A previous complete file may remain after an unavailable source, but SCN-022
refuses it after the existing 30-second signal lifetime.

## News Gate contract

The optional [SCN-025 collector](news-gate-collector.md) can atomically publish
this exact `sochron.news-gate.v1` shape from a strict normalized calendar gateway:

```json
{
  "protocol": "sochron.news-gate.v1",
  "source_id": "configured-calendar-source",
  "revision": "explicit-source-revision",
  "observed_at_utc": "2026-09-20T02:05:00Z",
  "coverage_from_utc": "2026-09-20T02:00:00Z",
  "coverage_until_utc": "2026-09-20T02:10:00Z",
  "complete": true,
  "blocked": true,
  "blocking_event_ids": ["source-event-id"]
}
```

Times must be aware UTC values; coverage end is exclusive and must contain the
writer cutoff. Observation age is capped at five minutes. `blocked=true` requires
one or more unique event IDs; `blocked=false` requires an empty list. The file's
owner-only integrity establishes the local handoff boundary. The collector
software has local fixture evidence, but still needs an owner-selected licensed
gateway and separate evidence that its upstream calendar is complete and timely.
RSS or AI output alone must not be described as complete calendar protection.

Missing news data leaves the writer `awaiting_sources`; malformed/insecure data or
an output failure is `degraded`. Neither state manufactures `news_blocked=false`.

## MT5 telemetry v2

Telemetry v2 adds `market_open` and fixed
`market_source=mt5-symbol-trade-session`. The read-only EA calculates this from
the symbol's broker trade-session table at the sampled broker tick and refuses
ambiguous session rows. Disabled/close-only symbol trade modes report closed for
new entries. V1 remains accepted for monitoring compatibility but cannot feed the
writer.

The current MQL sources and v2 golden fixture pass static/source-only checks. They
have not been compiled or run in MetaTrader. Follow `mt5/ea/README.md` on the
selected Demo host and retain new compiler, pure self-test and actual read-only
round-trip evidence before treating the source as MT5-verified.

## Local verification and remaining gaps

Targeted local verification:

```bash
.venv/bin/pytest -q tests/test_policy_evidence.py tests/test_telemetry_bridge.py tests/test_mt5_source.py tests/test_api_safety.py
.venv/bin/python scripts/check-mt5-source.py
.venv/bin/python scripts/check-mt5-fixture.py
```

Synthetic success proves coherent atomic construction and SCN-021 model
compatibility only. The collector boundary exists locally; still missing are its
actual licensed gateway/provider, target private files and scheduling, selected-host
MQL compilation, actual Demo read-only source parity, the scheduled PA01 producer,
hosted Supabase authorization, target recovery/burn-in and every execution/release
gate.
