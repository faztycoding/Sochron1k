# ADR-026: coherent policy-evidence handoff

- Status: Accepted for local Demo integration
- Date: 2026-09-20

## Context

SCN-022 consumes one strict policy file but deliberately does not create it. The
API already authenticates separate MT5 telemetry and execution-inventory streams,
while news coverage belongs to a separate asynchronous source. Reading these
independently in the worker would permit mixed cutoffs, stale account state and an
unsafe inference that an absent news event means a clear window.

Telemetry v1 also has no authoritative current-session observation. Inferring a
session from UTC, Bangkok time, recent ticks or a generic weekday would disagree
with broker symbol metadata and daylight-saving/holiday behavior.

## Decision

Keep acquisition in its existing trust boundaries and add one API-side policy
coordinator. The read-only MT5 observer emits telemetry v2 with a market-open
boolean derived from `SymbolInfoSessionTrade` at the sampled broker tick. The
execution polling bridge exposes one immutable, already-fenced inventory snapshot
for policy derivation. A future news collector publishes a strict owner-only
coverage frame; the API validates but does not invent or broaden its claim.

When all sources are fresh and causal, the coordinator computes spread,
market/session, news, exposure and pending state at one UTC cutoff. It derives
evidence IDs from canonical source content and atomically replaces the private
SCN-022 policy file. Configuration absence is inert. Failure retains no partial
output and the previous complete handoff expires under the producer's existing
30-second rule.

Expose only a redacted `/policy/v1/status` read model and add that route plus the
upstream source classes to the Signals node in `/ui/connections`. This map is an
integration diagnostic, not policy content or execution readiness.

## Rejected alternatives

- **Infer market-open from tick freshness:** a recent quote does not prove that
  new entries are accepted or identify a broker session boundary.
- **Treat a missing news file as clear:** absence cannot prove calendar coverage.
- **Let the PA01 worker query mutable services independently:** independently read
  values would not share an explicit causal cutoff.
- **Write the output in place:** readers could observe truncated or mixed JSON
  after failure.
- **Copy the worker model into an HTTP response:** policy evidence includes account
  and market details that do not belong in a public diagnostic route.
- **Create a signal or command in the coordinator:** policy acquisition must not
  gain strategy, risk or execution authority.

## Consequences

The PA01 producer gains a concrete, fail-closed handoff once all three upstream
source families are configured. Existing telemetry v1 clients continue to monitor
but cannot satisfy the writer. A real news collector, selected-host MQL5 compile,
actual terminal parity and target scheduling remain explicit later gates. Auto
Trading and execution readiness remain false.
