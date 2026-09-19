# ADR-019: Owner signal read model uses the existing RLS source

## Status

Accepted for SCN-016 local implementation.

## Context

The synchronized data foundation already owns `signals`, `experiments`, and
`strategy_versions`, with owner-scoped SELECT policies. The browser needs a
stable, redacted application contract, while FastAPI already performs online Auth
and active-session validation. Creating another signal database would split
history; giving FastAPI a service-role key would unnecessarily bypass RLS; and
querying Supabase directly from each component would expose database shape as the
UI contract.

## Decision

FastAPI will make one bounded GET to the existing Supabase Data API after online
owner verification. It forwards the exact verified bearer token plus the existing
unprivileged project key to the same configured origin. PostgREST embeds the two
foreign-key relations needed for version and experiment evidence. Existing RLS is
the primary row boundary; FastAPI additionally validates every returned owner ID
against the verified UUID and removes owner/internal database identifiers from its
response.

The API exposes a strict application model at `/owner/signals`. It performs no
database mutation and owns no strategy rules. Empty results are
`awaiting_source`, not fabricated WAIT signals. Upstream failure produces a
redacted unavailable response rather than cached or synthetic signal data.

## Consequences

- Signal truth stays with immutable synchronized evidence and one owner RLS model.
- The browser contract is decoupled from raw table and relationship names.
- Auth and Data API availability are required for this view; an outage clears the
  displayed rows and must not affect position management.
- The strategy producer, feature parity, evaluation, promotion and MT5 execution
  remain separate future gates.
- The April 2026 Data API exposure change does not require a new object here: the
  existing migration already grants only SELECT on these tables to
  `authenticated` and forces RLS. New objects must continue to use explicit
  grants and RLS together.
