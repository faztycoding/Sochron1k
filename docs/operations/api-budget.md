# Provider-neutral API budget evidence

SCN-034 gives the authenticated owner and operational-alert detector one exact
normalized view. It does not call a billing provider, hold its credential, enforce a
provider spending cap or authorize a purchase.

## API and UI positions

| Surface | Browser route | API route | Source |
| --- | --- | --- | --- |
| Detailed budget ledger | `GET /api/owner/api-budget` | `GET /owner/api-budget` | private normalized snapshot |
| Threshold/source alerts | `GET /api/owner/alerts` | `GET /owner/alerts` | same coherent budget view |
| Connection rail | `GET /api/ui/connections` | `GET /ui/connections` | redacted runtime state |
| UI anchor | `#operational-alerts .budget-ledger` | n/a | below alert coverage, above lifecycle events |

All owner reads reuse online owner/session verification and `Cache-Control: no-store`.
There is no budget mutation route. The UI never receives a provider credential,
source ID, revision or filesystem path.

## Private config

Create one dedicated directory owned by the API runtime UID with mode `0700`. Put
the config in that directory as a regular, single-link file with mode `0600`. Set
`SOCHRON_API_BUDGET_CONFIG_FILE` to its canonical absolute path. The file has this
exact shape:

```json
{
  "enabled": true,
  "snapshot_file": "/absolute/private/api-budget/current.json",
  "currency": "USD",
  "monthly_limit": "25.00",
  "warning_fraction": "0.70",
  "critical_fraction": "0.85",
  "stale_after_seconds": 86400
}
```

The numbers above illustrate schema only; they are not project defaults or owner
approval. Currency, limit and both fractions must match the owner's recorded
decision. Set only `{"enabled":false}` to explicitly disable the source. Leaving the
environment variable empty is also disabled.

For Compose, both the config and snapshot must be below a reviewed persistent mount
and the path in the config must be the container-visible canonical path. A host path
that is not mounted at the same container path will fail startup; do not weaken the
canonical/private checks to make it open.

## Normalized snapshot contract

A credential-isolated collector writes this exact object atomically:

```json
{
  "protocol": "sochron.api-budget-snapshot.v1",
  "source_id": "opaque-provider-billing-source",
  "revision": "opaque-provider-revision",
  "period_start_utc": "2026-09-01T00:00:00Z",
  "period_end_utc": "2026-10-01T00:00:00Z",
  "observed_at_utc": "2026-09-20T03:00:00Z",
  "coverage_until_utc": "2026-09-20T02:55:00Z",
  "currency": "USD",
  "billed_cost": "14.25",
  "unbilled_estimate": "1.10"
}
```

The file must be a regular, single-link, API-owned `0600` file under an unchanged
private parent and no larger than 16 KiB. The collector must write a new private
temporary file, flush it, atomically replace `snapshot_file`, then synchronize the
parent directory. It must never partially overwrite the current file. Provider
credentials belong only to the collector's secret boundary and never in either JSON
document.

`billed_cost` is the provider-confirmed amount. `unbilled_estimate` is the amount the
collector identifies as not yet billed; it must not be silently set to zero when the
provider cannot supply or compute it. In that case the collector must withhold the
snapshot or publish no newer coverage, allowing the API to become stale. Do not
derive these values solely from local request counts unless provider reconciliation
proves the method for the selected plan.

## Runtime meanings

| State | Meaning |
| --- | --- |
| `disabled` | no owner config selected |
| `awaiting_snapshot` | config valid; collector has not published the first file |
| `connected` | fresh and below warning fraction |
| `warning` | fresh total is at/above warning and below critical |
| `critical` | fresh total is at/above critical and below the limit |
| `exhausted` | fresh total is at/above the monthly limit |
| `stale` | structurally valid evidence is too old or outside its billing period |
| `degraded` | permissions, identity, schema, time ordering, currency or content cannot be trusted |

The total is exact `billed_cost + unbilled_estimate`. Threshold comparisons use
decimal arithmetic. The displayed percentage is rounded down to four decimal places;
it does not replace the exact amounts. A warning/critical/exhausted lifecycle cannot
resolve while that threshold fact remains current. A stale/degraded snapshot is a
source-health alert, not proof the budget was exceeded.

## Remaining provider evidence

Before relying on this in unattended Demo, retain the provider and plan identity,
collector version, credential-delivery method, actual billing response fixture,
rate-limit behavior, delayed-charge behavior, currency/tax treatment, snapshot
latency and reconciliation against the provider console/invoice. None of that is
established by local synthetic checks.

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_api_budget.py tests/test_operational_alerts.py
npx -y -p node@24.21.0 npm run test --workspace @sochron1k/web -- src/operational-alerts-api.test.ts src/OperationalAlertsPanel.test.tsx
```
