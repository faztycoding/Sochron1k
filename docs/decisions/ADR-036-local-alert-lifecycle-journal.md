# ADR-036: Keep owner alert workflow in a local durable journal

- Status: accepted
- Date: 2026-09-20

## Context

SCN-032 deliberately exposes detector facts without claiming acknowledgement or
resolution. The Blueprint requires both fields in the notification center, but no
external alert destination, provider, hosted store or delivery budget has been
selected. A browser-only flag would disappear on refresh and an acknowledgement
written into an execution source would violate source ownership.

Detector facts also have two meanings. Rejections are immutable occurred events;
no-SL, UNKNOWN, risk halt, stale price, disconnected source and storage pressure
are continuing conditions. A generic “close” button could therefore hide a safety
condition that is still active.

## Decision

Use one optional owner-private SQLite WAL journal dedicated to alert workflow.
The API stores a redacted alert snapshot, owner-scoped acknowledgement/resolution
times and immutable idempotency receipts. It does not store credentials or broker
identity and never writes the detector sources.

The derived alert gets a stable `condition_id` distinct from its occurrence ID.
The journal uses that key to merge lifecycle evidence into the v2 inventory.
Current safety conditions cannot resolve while detected. Once absent they remain
visible as `cleared` and require healthy, complete source evidence before an owner
may resolve them. An acknowledged rejection may be resolved as an operator-workflow
event even while the immutable rejection remains in the execution projection.

No GET request creates lifecycle state. Only the two authenticated POST routes
mutate the journal, and every mutation requires an idempotency key committed in the
same transaction as the transition.

## Consequences

- Acknowledgement survives refresh, restart and response loss without implying
  delivery or source recovery.
- The notification center can show cleared and recently resolved episodes without
  weakening the authoritative detector.
- The API now has a narrowly mutable owner boundary, so private filesystem,
  durability, exact replay and negative authorization tests are required.
- External delivery, escalation, API-budget monitoring and target alert tests
  remain separate release gaps. This ADR cannot clear the unattended-Demo gate.
