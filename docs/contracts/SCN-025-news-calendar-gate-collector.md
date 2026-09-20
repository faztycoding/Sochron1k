# SCN-025 coverage-complete news calendar gate collector

## Task contract

Add a disabled-by-default worker that requests one bounded, authenticated calendar
window from a separately operated upstream gateway, verifies explicit completeness
and coverage, deterministically derives the high-impact news blackout at the local
receipt cutoff, and atomically publishes the existing `sochron.news-gate.v1` file
for the SCN-023 policy writer.

This increment defines and verifies the project-side API boundary. It does not
choose, purchase or operate a calendar vendor, claim that RSS absence is complete,
use AI to decide the gate, schedule the target process, write Supabase, create a
trade command or enable Auto Trading.

## Upstream contract

- The configured remote origin is HTTPS with no path, credentials, query or
  fragment. The collector calls only `GET /v1/calendar-window` and never follows a
  redirect or environment proxy.
- Query values contain UTC `from`, exclusive UTC `until`, unique configured
  currencies and impacts. The requested interval is exactly the period needed to
  decide whether the current cutoff lies inside any event blackout.
- A successful response is strict `sochron.calendar-window.v1`: source ID, source
  revision, publication time, explicit coverage bounds, literal `complete=true`
  and a bounded ordered event list. Coverage must include the entire requested
  interval; publication must be recent and not in the future.
- Every event has a unique source event ID, UTC schedule, configured currency,
  configured impact and explicit `scheduled` or `cancelled` status. Events must be
  ordered and contained by the attested coverage. Unrecognized or extra content is
  rejected rather than inferred.

## Output semantics

- A scheduled matching event blocks when
  `event_time - before <= cutoff < event_time + after`. Cancelled events never
  block. Event IDs are copied exactly into a unique bounded blocking list.
- The gate's observation time is the local receipt time, not the upstream
  publication time. Its revision includes the explicit upstream revision plus a
  SHA-256 digest of the canonical validated response.
- Output is written as a synced mode-0600 temporary inode in the existing
  owner-private directory and atomically replaced. Any unavailable, ambiguous,
  malformed, incomplete, stale, oversized or insecure input leaves the previous
  gate untouched; SCN-023 then expires that gate after five minutes.

## Acceptance criteria

- **AC-01 inert configuration:** unset or exact disabled private configuration
  performs no credential read, output write or network request. Paths are canonical,
  private and pairwise distinct; credentials never enter environment values or CLI.
- **AC-02 narrow transport:** exact HTTPS origin/fixed route, bearer credential,
  identity encoding, no redirect/proxy, one connection, two-second request and
  ten-second total deadline, JSON media type and 256 KiB response bound are tested.
- **AC-03 strict completeness:** only a recent complete window covering the whole
  requested interval is accepted. Missing, partial, stale, future, malformed,
  duplicate, unordered, out-of-coverage or unexpected data fails closed.
- **AC-04 deterministic gate:** boundary/property tests cover before/after
  half-open blackout semantics, configured impact/currency filters, cancellation,
  multiple events and stable content-bound revisions without AI authority.
- **AC-05 durable private handoff:** output validates as `NewsGateFrame`, is 0600,
  atomically replaced and survives failed refresh unchanged. Symlink, hard link,
  permissive file/directory or replacement races are denied.
- **AC-06 safe operator:** `sochron-news-gate status|run [--once]` emits redacted
  machine-readable states with execution and Auto Trading false; rejected CLI or
  runtime errors never echo credentials, response bodies, URLs or paths.
- **AC-07 integration:** a generated clear and blocked gate is consumed by the
  SCN-023 writer; missing/failed refresh never manufactures clear news evidence.
- **AC-08 evidence limits:** targeted/full Python, installed artifact, web/static,
  secret and config checks pass. Actual vendor/gateway access, completeness audit,
  target scheduling/recovery and Demo operation remain `NOT RUN`.

## Required owner inputs

To make this boundary operational, the owner must select a licensed calendar
source or gateway that can attest complete revisioned windows, provide its HTTPS
origin and credential through owner-private files, define relevant currencies,
impacts and blackout durations, and authorize target outbound access. Until then,
the collector stays disabled and Signals correctly remain waiting for News Gate.
