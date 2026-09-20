# ADR-022: broker-time native aggregation for PA01

- Status: Accepted as a local pure evidence boundary
- Date: 2026-09-20

## Context

SCN-008 preserves immutable native M1 bars with both broker `time_server_s` and UTC
time. SCN-018 consumes closed M5/H1 evidence, but its first model inferred candle
alignment from UTC. That inference is invalid when the broker offset is not a whole
hour and it leaves no deterministic bridge from synchronized M1 evidence to PA01.

Filling missing minutes, flooring UTC timestamps or aggregating forming/incompletely
available buckets would create evidence the broker never supplied and could change
an earlier decision with later information.

## Decision

Add the pure `sochron_worker.pa01_aggregation` boundary. It accepts one bounded,
validated `native-v1` archive identity and an explicit UTC cutoff. It revalidates
every immutable M1 record, selects only closed rows available at the cutoff, and
groups complete buckets by broker server time. M5 requires five exact consecutive
minutes and H1 requires sixty. Incomplete or gapped buckets do not exist in the
output and receive no market-close classification.

Aggregate OHLC uses first open, exact high/low extrema and last close. Availability
is the maximum child availability. Stable archive/time IDs identify a bucket, while
a revision hash covers the full exact child evidence. Separate source and output
hashes preserve deterministic replay. Results retain at most 100 bars per timeframe.

Strengthen SCN-018 `ClosedBar` with `time_server_s` and the pinned broker offset.
Alignment and gap detection use server time; UTC is derived and retained for audit
and display. Advance the parameter/evidence version to `PA01-v1.0.1` and include
`broker-time-server-v1` in its hash. PA01-v1 rule thresholds and indicator
calculations do not change.

The module has no filesystem, database, HTTP, current-clock, AI, risk, command or
execution authority. It does not classify sessions or persist a decision.

## Rejected alternatives

- **Floor UTC to five minutes or one hour:** rejected because broker H1 boundaries
  can be shifted in UTC and the native source already supplies authoritative server
  time.
- **Carry the prior close across missing M1 rows:** rejected because it fabricates
  prices, volumes and path evidence.
- **Emit partial buckets and revise them later:** rejected because PA01 consumes
  closed immutable evidence and historical decision snapshots must not repaint.
- **Aggregate only inside a database view:** deferred because the pure replay and
  leakage boundary must be testable independently before transport and persistence
  are granted service-role authority.

## Consequences

- A non-whole-hour broker offset produces valid shifted UTC H1 bars without changing
  broker candle boundaries.
- One missing M1 removes its containing aggregate; later complete bars preserve the
  resulting interval gap for PA01 to block.
- Appending future/later-available source evidence cannot change an earlier result.
- Existing synthetic SCN-018 fixtures now state server time and broker offset
  explicitly, so their evidence semantics are no longer inferred.
- `/api/owner/signals` still remains `awaiting_source`. The next boundary is a
  bounded source reader plus durable scheduled producer and atomic immutable
  feature/signal persistence with UNKNOWN/read-back recovery.
