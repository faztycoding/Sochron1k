# SCN-034: Provider-neutral API budget evidence

## Objective

Replace the placeholder `api_budget` coverage with a bounded, owner-configured,
provider-neutral cost snapshot that the authenticated Demo UI can inspect and the
operational alert inventory can evaluate without receiving provider credentials or
inventing usage.

## Scope

- Read one normalized private cost snapshot through an optional private config
  selected by `SOCHRON_API_BUDGET_CONFIG_FILE`.
- Expose the redacted current view at `GET /owner/api-budget` and embed the same
  view in `GET /owner/alerts`.
- Evaluate owner-selected warning and critical fractions against billed cost plus
  the provider collector's unbilled estimate.
- Render the current amount, limit, remaining amount, period, evidence freshness,
  source reference and exact browser/API positions in the notification center.
- Keep external provider collection, billing credentials, purchases and external
  notification delivery disabled until separately selected and authorized.

## Out of scope

- Calling any provider billing API, scraping a provider console or storing its
  credential.
- Currency conversion, tax estimation, token-price inference or default budgets.
- Enforcing provider-side spending caps or authorizing purchases.
- Email, chat, SMS, push, webhook delivery, deployment, MT5 operations or release
  promotion.

## Acceptance criteria

### AC-01 — Explicit private owner policy

- With no environment selection the source is `disabled`, the owner view remains
  readable, coverage reports `awaiting_configuration`, and no budget alert is
  fabricated.
- The selected config is one canonical absolute regular file owned by the API user,
  has no group/other permission bits, has one link, is bounded to 16 KiB, rejects
  duplicate JSON keys/non-finite numbers, and uses an unchanged private parent.
- Configuration requires an exact currency, positive monthly limit, explicit
  warning and critical fractions with `0 < warning < critical <= 1`, a bounded
  staleness window and one canonical private snapshot path. No defaults infer an
  owner's spending authority.

### AC-02 — Strict normalized evidence

- The snapshot has the exact `sochron.api-budget-snapshot.v1` schema: opaque source
  ID and revision, one 27–32 day billing period, aware UTC observed/coverage times,
  matching currency, non-negative billed cost and non-negative unbilled estimate.
- Coverage cannot precede the period, exceed observation time or extend beyond the
  billing period. Future observation, wrong currency, malformed/oversized/public,
  linked or non-regular input fails closed.
- The API never returns the source ID, revision, config/snapshot path or credential;
  it returns one deterministic redacted source reference.

### AC-03 — Truthful runtime and derived amounts

- Runtime is `awaiting_snapshot` when a valid configured source has no snapshot,
  `stale` when a valid snapshot is outside its period or either observation or
  coverage age exceeds the owner limit, and `degraded` when evidence cannot be
  trusted.
- Connected evidence reports exact decimal billed, unbilled estimate, total,
  limit and remaining amount plus usage percent rounded down to four decimal
  places, without binary floating-point conversion.
- State is `connected`, `warning`, `critical` or `exhausted` according to the exact
  configured fractions. `exhausted` begins at total cost greater than or equal to
  the limit.

### AC-04 — Owner API and alert integration

- `GET /owner/api-budget` uses the existing verified owner session, returns
  `Cache-Control: no-store`, a strict response model, Demo-only and read-only flags,
  and no mutation route.
- `api_budget` coverage becomes `available` and names both
  `/api/owner/alerts` and `/api/owner/api-budget`.
- Warning, critical and exhausted states emit bounded `api_budget` facts with
  increasing severity. Stale/degraded evidence emits a source-health fact rather
  than a false cost threshold.
- A current budget fact cannot be resolved through the lifecycle workflow. It may
  clear only after fresh below-threshold evidence; recurrence becomes a new episode
  under the existing lifecycle rules.

### AC-05 — Strict responsive UI

- The browser accepts only the exact v3 alert inventory and embedded budget schema,
  recalculates decimal relationships without binary floating-point comparison, and
  rejects contradictory state, amount, threshold, route or source data.
- Signed-out users can still see the two browser API positions and the external
  collector handoff. Authenticated users see current amounts, period, UTC and
  Asia/Bangkok coverage times, source reference and a clear stale/configuration
  state without exposing private paths.
- The additional budget strip remains contained at 320 CSS pixels and does not
  imply provider collection or external notification occurred.

### AC-06 — No readiness or spending claim

- `delivery_configured=false`, `auto_trading_enabled=false` and
  `execution_ready=false` remain literal invariants.
- The public connection map removes only the missing budget implementation claim;
  it continues to identify external alert delivery as missing.
- Local synthetic fixtures are not provider billing, deployment, delivered-alert
  or unattended-Demo evidence, and the SCN-031 recovery/observability gate remains
  `not_run`.

## Required evidence

- Python model/file/route/alert tests for disabled, absent, fresh thresholds,
  stale, future, malformed, wrong-currency, permission, replacement and owner-auth
  cases.
- Web parser/component checks for exact decimals, all runtime states, redaction,
  route visibility and 320px containment.
- Existing baseline, skill, Python, web, static database, Compose, package,
  container and production-browser checks where available.
