# ADR-008 Local closed-bar capture spool

2026-09-17; local implementation decision under SCN-007, not a deployment decision.

The existing chart cache disappears on restart and cannot provide retained history.
Use a separate owner-private SQLite WAL database with FULL synchronization on every
connection, atomic receipt/bar/checkpoint writes and a fixed page quota. Do not put
market windows into the command journal or send every window to Supabase. The future
worker will synchronize retained M1 bars using stable identities; raw-tick Parquet
capture remains unimplemented. No new dependency or alternate hosting is introduced.

Closed rows are immutable. Only the latest frame per timeframe is a replaceable
validation projection; this does not claim to preserve past forming observations.
An accepted receipt is persisted before acknowledgment. Its local monotonic integer
ID is the history-read watermark; it is scoped to the archive configuration, not a
broker sequence or wall-clock claim. First received time is retained separately
from bar event time. Strategy decision availability must reference an already
committed watermark, never assume a backfilled bar was known at its open/close.

Restart restores validation baselines but never marks historical data live. Identity
or offset-interval changes require a separately reviewed archive/migration; restarting
cannot silently rewrite closed bars. Failure latches chart capture, preserves quote
monitoring and leaves all execution gates disabled. Configuration absent explicitly
means monitoring-only, with no durability promise. Storage is local and opt-in;
target capacity, restore drills, synchronization and historical UI remain required.

References: [SQLite WAL](https://www.sqlite.org/wal.html),
[connection synchronization](https://www.sqlite.org/pragma.html#pragma_synchronous).
