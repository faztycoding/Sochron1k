# ADR-037: Normalize provider cost into a private snapshot

- Status: accepted
- Date: 2026-09-20

## Context

The Blueprint requires API-budget visibility and periodic cost review, but its price
tables are planning assumptions rather than current bills or purchasing authority.
The owner has not selected a runtime AI/billing provider, monthly limit, currency or
alert thresholds. Provider APIs also expose different usage delays, billing periods
and credential models.

Hard-coding one provider would create a false dependency and putting its credential
in the browser/API response would cross the restricted-secret boundary. Estimating
cost only from local call counts would omit provider-side retries, tools, reasoning,
discounts, credits and delayed charges.

## Decision

Define one exact normalized snapshot owned by a future provider collector. The
collector writes billed cost, its unbilled estimate, coverage time and provider
revision to an owner-private atomic file. A separate private config supplies the
owner-approved currency, monthly limit, warning fraction, critical fraction and
maximum evidence age.

The API is a query-only consumer. It validates file identity, permissions, schema,
period, UTC ordering, currency, exact decimals and freshness on every read. It
returns only a hashed source reference and derived amounts. It never calls a
provider, performs currency conversion, infers token prices or changes a spending
limit.

`GET /owner/api-budget` is the detailed owner surface. The operational-alert route
embeds the same view so one UI poll has a coherent budget state and alert decision.
Threshold alerts use billed plus unbilled estimated cost. Stale or invalid evidence
is a source-health failure, not a fabricated over-budget claim.

## Consequences

- The API/UI contract and alert logic can be completed before provider selection.
- Connecting a provider later requires a small credential-isolated collector that
  atomically publishes this schema; it does not require changing the browser model.
- Actual provider accuracy, delivery latency and price interpretation remain target
  evidence and must be tested after the owner selects the provider and budget.
- External alert delivery is a separate boundary. SCN-035 later implements its
  local provider-neutral outbox/read-back contract, but a real recipient and target
  exercise are still missing, so neither decision clears unattended-Demo readiness.
