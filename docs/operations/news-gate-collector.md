# Coverage-complete News Gate collector (SCN-025)

## Status and API position

The optional `sochron-news-gate` worker can produce the owner-private
`sochron.news-gate.v1` file consumed by the API policy writer. It is disabled when
`SOCHRON_NEWS_GATE_CONFIG_FILE` is unset or points to the exact JSON
`{"enabled":false}`. Importing its modules and running `status` perform no network
request or output write.

```text
licensed calendar/vendor adapter
          |
          v
HTTPS GET /v1/calendar-window  (private outbound worker API)
          |
          v
sochron-news-gate -> owner-private news-gate.json
          |
          v
API policy writer -> GET /api/policy/v1/status
          |
          v
sochron-pa01 -> Supabase -> GET /api/owner/signals
```

The calendar call and bearer credential are never browser routes. The UI sees only
the redacted policy status and owner signal read model. No News Gate route creates
a trade command or changes execution readiness; Auto Trading stays false.

This repository does **not** provide or select the licensed calendar gateway.
Local fixtures verify the normalized contract, not external completeness. Signals
remain waiting until the owner supplies a qualifying source and target scheduling.

## Private collector configuration

Create one canonical owner-only file (0400 or 0600) in an owner-only directory and
set its path in `SOCHRON_NEWS_GATE_CONFIG_FILE`:

```json
{
  "enabled": true,
  "origin": "https://calendar-gateway.example",
  "credential_file": "/absolute/private/calendar.token",
  "output_file": "/absolute/private/news-gate.json",
  "currencies": ["USD"],
  "impacts": ["high"],
  "blackout_before_seconds": 1800,
  "blackout_after_seconds": 1800,
  "poll_seconds": 60
}
```

The origin is a placeholder, not a working service. It must be an exact HTTPS
origin with no path, query, fragment, user information or custom port. The worker
calls only `/v1/calendar-window`, disables redirects and environment proxies and
requires normal TLS verification.

The credential file contains only the gateway-issued 32–256 character bearer
token using letters, digits, dot, underscore, tilde or hyphen, with no newline.
Keep it separate from the config, repository, environment value, command line,
screenshots and logs. The config, credential and output paths must be distinct.

The `output_file` must exactly equal `news_gate_file` in the SCN-023 policy-writer
config. Both processes need access under the same target UID or an equally narrow
reviewed handoff; this repository has tested only the same-owner local file model.

## Normalized gateway contract

The worker requests URL-encoded `from`, exclusive `until`, comma-separated
`currencies` and comma-separated `impacts`. The response has exact fields:

```json
{
  "protocol": "sochron.calendar-window.v1",
  "source_id": "licensed-source-id",
  "revision": "source-revision-123",
  "published_at_utc": "2026-09-20T03:00:00Z",
  "coverage_from_utc": "2026-09-20T02:30:00Z",
  "coverage_until_utc": "2026-09-20T03:30:00.000001Z",
  "complete": true,
  "events": [
    {
      "event_id": "source-event-id",
      "scheduled_at_utc": "2026-09-20T03:10:00Z",
      "currency": "USD",
      "impact": "high",
      "status": "scheduled"
    }
  ]
}
```

The source must explicitly attest the entire requested window and publish a fresh
revision. Events are unique, sorted by `(scheduled_at_utc, event_id)`, inside the
coverage and limited to requested currencies/impacts. `cancelled` is the only
other status and never blocks. Extra fields, partial coverage, old/future
publication, duplicates, disorder, redirects, compression, wrong media type or an
oversized body all fail closed.

The repository cannot prove a third party's `complete=true` assertion by schema
alone. Before target use, audit the gateway's vendor mapping, licensing, outage
semantics, revision/correction behavior, DST/UTC handling and completeness SLA.
An RSS or AI summary adapter does not meet this contract merely by returning
`complete=true`.

## Operation

With no configuration, both commands safely report `DISABLED`:

```bash
sochron-news-gate status
sochron-news-gate run --once
```

After private target configuration, `status` validates non-secret structure
without reading the bearer credential or making a request. `run --once` performs
one scheduler invocation. `run` refreshes at `poll_seconds`; five consecutive
failures exhaust its retry budget and require supervisor alert/review.

A successful refresh atomically replaces the 0600 gate. Failure leaves the last
valid inode unchanged; the policy writer rejects it after five minutes, so a dead
collector cannot manufacture a clear window. Operator JSON is redacted and always
reports `execution_ready=false` and `auto_trading_enabled=false`.

Local verification:

```bash
.venv/bin/pytest -q tests/test_news_gate.py tests/test_policy_evidence.py
SOCHRON_UV=/absolute/path/to/uv-0.12.15 .venv/bin/python scripts/check-worker-package.py
```

The tests use a synthetic in-process HTTP transport. They make no vendor, hosted,
broker or account request.

## Missing owner inputs

To finish the real connection, provide:

- the selected licensed calendar source/gateway and its exact HTTPS origin;
- its owner-private bearer credential and rotation/revocation procedure;
- approved currencies, impacts and before/after blackout durations;
- target outbound firewall/DNS/TLS design, scheduler and alert destination;
- evidence that complete windows, corrections, outages and clock behavior match
  the contract over an owner-approved observation period.

Until those inputs exist, keep the worker disabled and treat `news_ready=false` as
the correct state.
