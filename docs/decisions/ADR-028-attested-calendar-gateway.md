# ADR-028: attested calendar gateway for deterministic News Gate

- Status: Accepted for local software boundary
- Date: 2026-09-20

## Context

SCN-023 deliberately refuses to treat missing news as clear, but it has no producer
for its private News Gate file. Public RSS feeds and AI summaries do not prove that
a time window contains every relevant scheduled event. Vendor schemas, licensing
and credentials also cannot be selected or invented by the repository.

## Decision

Define one narrow normalized gateway contract and implement a disabled-by-default
collector around it. The gateway, not the collector, is responsible for adapting
the selected licensed source and explicitly attesting a complete revisioned UTC
window. The collector independently validates coverage, recency, ordering,
configured currency/impact membership and event status, then applies fixed
half-open blackout arithmetic without AI.

Use an exact HTTPS origin plus fixed `/v1/calendar-window` path, a separate
owner-private bearer credential, no redirects or environment proxies, bounded
timeouts/body size and strict response models. Bind the canonical validated
response to the output revision with SHA-256. Publish the existing News Gate schema
through an atomic owner-only file so the policy writer remains independent of the
vendor.

## Rejected alternatives

- **Assume no RSS item means clear:** RSS is not a completeness protocol.
- **Let AI classify whether trading is safe:** the gate is deterministic policy
  and AI has no risk or execution authority.
- **Embed a vendor key in environment or repository config:** this expands secret
  exposure and makes redaction harder.
- **Call arbitrary configured paths or follow redirects:** this broadens the
  destination and credential-forwarding boundary.
- **Overwrite the gate on failure:** an error must not create clear evidence; the
  last valid gate can age out under the writer's existing five-minute limit.

## Consequences

The project has a testable API position and deterministic News Gate producer that
can be wired once the owner selects a qualifying source/gateway. Local fixtures can
prove transport and arithmetic, but not external source completeness. Target
scheduling, alerting, gateway recovery and an actual provider audit remain release
gates. No execution readiness or Auto Trading state changes.
Use an exact HTTPS origin plus fixed `/v1/calendar-window` path, a separate
