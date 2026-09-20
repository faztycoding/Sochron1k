# ADR-023: atomic immutable PA01 decision receiver

- Status: Accepted as a local Supabase persistence boundary
- Date: 2026-09-20

## Context

SCN-018 and SCN-019 now produce a deterministic PA01 decision from immutable native
evidence, while SCN-016 already exposes owner-scoped signal rows. Writing a feature
snapshot and signal as unrelated operations would permit orphan evidence, a visible
signal without its decision snapshot, duplicate decisions after a lost response, or
historical rewriting. Browser table access cannot be widened to solve this because
the service-role credential must remain backend-only and owner SELECT RLS is already
the established read boundary.

The same tables also contain legacy synthetic fixtures used by the owner-browser
verification. A migration that made every historical row globally immutable would
break scoped cleanup without proving anything about producer evidence.

## Decision

Extend `feature_snapshots` and `signals` with an optional producer revision and
decision fingerprint. Producer signals additionally carry an owner-safe foreign key
to exactly one snapshot. Partial unique indexes enforce one fingerprint per owner
and one signal per producer snapshot. Rows with a producer revision are immutable;
legacy rows with all producer columns null retain their existing behavior.

Expose two security-invoker functions with an empty search path and explicit
`postgres`/`service_role` execution grants:

- `sochron_store_pa01_decision` validates one bounded, versioned payload and
  atomically insert-or-verifies the snapshot and signal;
- `sochron_read_pa01_decision` independently reads the exact linked pair by owner
  and signal ID for UNKNOWN reconciliation.

The receiver admits only the exact `PA01-v1.0.1` parameter hash and
`native-pa01-aggregation-v1` identity, an eligible same-owner `PA01-v1` strategy,
and a draft/shadow/Demo experiment bound to that strategy. It validates explicit
UTC causal times, dataset/provenance hashes, bounded feature and evidence shapes,
deterministic action/reason semantics and execution parameters with
`order_created=false` and `risk_admitted=false`.

An exact replay returns the existing pair. Reusing an ID or fingerprint with changed
evidence raises `PA01_DECISION_CONFLICT`; the surrounding statement rolls back any
earlier insert. Backend `TRUNCATE`/trigger privileges are removed from the two tables
so service-role calls cannot bypass immutability. Anonymous and authenticated roles
cannot invoke either RPC or mutate the tables; existing authenticated owner SELECT
policies remain unchanged.

The receiver does not read source bars, schedule work, promote a strategy, create a
command or risk event, contact MT5, or enable Auto Trading.

## Rejected alternatives

- **Two independent table writes:** rejected because process loss can leave a
  partial decision and retries cannot safely distinguish it from absence.
- **Use only a client-generated fingerprint without row comparison:** rejected
  because a faulty or malicious caller could reuse the fingerprint with changed
  evidence.
- **Make every existing snapshot/signal immutable:** rejected because producer
  evidence can be distinguished explicitly while legacy fixtures still need scoped
  lifecycle cleanup.
- **Grant the browser RPC access:** rejected because the receiver is a producer
  boundary, not an owner mutation or strategy-control surface.
- **Combine source read, evaluation and persistence in one database function:**
  rejected because the pure kernel, source availability and durable retry journal
  need independent evidence and failure handling.

## Consequences

- A lost receiver response is UNKNOWN until the read RPC confirms the exact pair;
  a matching retry stays singular.
- Concurrent matching writers converge on one linked pair, while a concurrent
  changed writer gets a named conflict after the first transaction commits.
- Corrections require a new decision/snapshot identity rather than rewriting prior
  evidence.
- Strategy/experiment eligibility is checked at persistence time but no strategy is
  promoted and no execution admission occurs.
- `/api/owner/signals` remains `awaiting_source` until a separately verified durable
  producer reads native rows, runs aggregation/PA01 and invokes this receiver.
