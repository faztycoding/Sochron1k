# SCN-019 native M1 aggregation for PA01

## Task contract

Implement the pure deterministic boundary that converts immutable SCN-008 native
closed M1 evidence into the closed M5 and H1 inputs required by the SCN-018 PA01
kernel. Aggregation follows broker-server candle boundaries, preserves UTC and
availability separately, and never invents a missing minute.

This increment prepares reproducible decision evidence. It does not read Supabase,
schedule a worker, persist feature snapshots or signals, create a command, size a
position, call MT5, or make `/api/owner/signals` leave `awaiting_source`.

## Versioned aggregation rules

- Input mirrors one immutable `native-v1` M1 archive binding: Demo symbol, archive
  UUID, Bid price basis, broker UTC offset, server time, exact OHLC/grid values,
  closure evidence, original receive time and synchronized `available_at`.
- The broker offset is pinned for the archive validity interval. M5 and H1 buckets
  start where `time_server_s` is divisible by 300 and 3,600 respectively. UTC open
  time is derived exactly as server time minus the pinned offset; it need not be on
  a UTC-hour boundary.
- Only source rows whose M1 close and `available_at` are at or before the explicit
  UTC cutoff are eligible. Appending later or later-available rows cannot alter an
  earlier result.
- A bucket exists only when it contains exactly 5 or 60 distinct, consecutive M1
  rows at the expected server minutes. Open is the first open, high/low are exact
  extrema, close is the final close, and aggregate availability is the latest
  child availability.
- Partial buckets and buckets containing a missing minute are omitted. No price,
  zero-volume row, carry-forward close or market-close classification is created.
  A later complete bucket remains separated by the missing aggregate interval so
  the PA01 kernel blocks the unexplained gap.
- Each aggregate has a stable archive/time identity plus a revision hash over all
  exact child evidence. The as-of source set and output have deterministic hashes.
  At most the latest 100 M5 and 100 H1 bars are returned.
- SCN-018 `ClosedBar` records `time_server_s` and the broker UTC offset. Alignment
  and gap checks use server time; UTC remains the display/audit representation.
  This advances the parameter/evidence version to `PA01-v1.0.1` and its hash without
  changing the PA01-v1 trading thresholds or setup rules.

## In scope

- Strict Pydantic evidence models with exact Decimal and aware UTC timestamps.
- Broker-server M5/H1 alignment, including offsets that are not whole hours.
- Complete-bucket OHLC aggregation and deterministic provenance hashes.
- Bounded as-of output suitable for direct input to `evaluate_pa01`.
- Negative fixtures for duplicates, mixed archives/identities, revised rows,
  malformed time/grid evidence, gaps, partial buckets and future information.

## Out of scope

- A Supabase reader/RPC, service-role transport, scheduler, durable producer
  journal, atomic `feature_snapshots`/`signals` persistence or retry reconciliation.
- Market-session calendar classification, news retrieval, spread/telemetry context,
  strategy evaluation/backtesting, statistics, promotion or claims of an edge.
- Risk admission, command creation, MT5 mutation, hosted writes, deployment or any
  live-account path.

## Acceptance criteria

- **AC-01 strict source evidence:** reject malformed, forming, off-grid, non-Bid,
  timezone-naive, mismatched UTC/server-time, duplicate/revised or mixed binding
  rows before returning an aggregate.
- **AC-02 broker alignment:** M5/H1 boundaries use server time and the pinned offset;
  a non-whole-hour UTC offset produces the exact shifted UTC H1 open and remains a
  valid SCN-018 input.
- **AC-03 complete buckets only:** exact child counts and consecutive server minutes
  are required. OHLC and availability match their children; partial/gapped buckets
  are absent and no synthetic evidence appears.
- **AC-04 no lookahead:** only closed and available rows at the cutoff participate.
  Appending future or later-available rows cannot change the earlier result or its
  hashes.
- **AC-05 deterministic provenance:** aggregate IDs, child revision hashes, source
  dataset hash and output bytes repeat exactly; a changed child changes the hash
  rather than silently revising the same evidence.
- **AC-06 PA01 handoff:** a sufficient native M1 fixture produces bounded M5/H1
  bars accepted directly by `evaluate_pa01`; server-time gap detection and all
  existing SCN-018 safety semantics remain intact.
- **AC-07 pure boundary:** static and behavioral checks prove no filesystem,
  database, HTTP, clock-now, AI, risk, command or executor authority.
- **AC-08 regression gates:** targeted tests, full local checks, installed worker
  package and affected Linux candidate checks pass without weakening assertions.

## Evidence boundary

A passing SCN-019 proves deterministic local aggregation for committed synthetic
fixtures only. It does not prove parity with a selected MT5 broker feed, a running
producer, atomic persistence, target-host uptime, a research edge, Demo execution
or release readiness. Those remain separate gates.
