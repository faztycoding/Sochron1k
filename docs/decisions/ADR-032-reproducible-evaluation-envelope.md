# ADR-032: Reproducible research evaluation envelope

- Status: Accepted for local Demo implementation
- Date: 2026-09-20

## Context

SCN-017 can display owner-scoped evaluation rows, but no project component creates
them. Allowing callers to send final metrics would make the UI unable to distinguish
reproducible evidence from hand-entered numbers. Publishing without durable state
would also make a timed-out insert ambiguous.

The first safe boundary is narrower than a complete backtest. It can validate and
aggregate labelled setup-to-flat outcomes while refusing to invent tick order or
market evidence that is not present.

## Decision

The worker owns a versioned `sochron.research-evaluation.v1` input bundle and a
pure deterministic evaluator. Closed trades contain exact gross P/L, risk and cost
components; excluded dispositions remain in the input and manifest but cannot
affect performance metrics. A full mark-to-market equity path is required for
drawdown. A seeded moving-block bootstrap represents serial dependence without
claiming statistical certainty.

The output is a strict `sochron.research-evaluation-envelope.v1`. Its fingerprint
binds the input hash, strategy code hash, split, cutoff, metrics, costs and evidence
manifest. A private SQLite journal durably stores that envelope before the worker
calls a backend-only Supabase insert-or-verify RPC. Ambiguous writes become
`UNKNOWN`; exact read-back is required before `VERIFIED`.

Producer provenance columns on `evaluations` are nullable for compatibility with
existing rows. When present they are all required, strictly validated, uniquely
fingerprinted and immutable. The receiver runs as `SECURITY INVOKER` with an empty
search path and is executable only by `postgres` and `service_role`. Owner browser
reads continue through RLS and receive only the SCN-017 projection.

## Consequences

- The Statistics panel can receive real producer output without browser-side
  metric calculation or privileged credentials.
- The producer cannot turn OHLC bars into fills; a separate labelled-trade/backtest
  task remains necessary before non-synthetic evaluation evidence exists.
- The database stores bounded provenance and counts, not the full trade bundle.
  The immutable input artifact must be retained under the operator's data policy.
- A successful evaluation never promotes a strategy or enables Auto Trading.
