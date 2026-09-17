# SCN-007 Durable native-bar history

Version 1.0; High assurance; owner: project owner. Acceptance recorded before
implementation, based on `601dfdb`. Supports the full Demo goal without authorizing
MT5 account operations, hosted writes, deployment or trading. Blueprint sections
06, 15 and 23 require retained bars/evidence and bounded local storage.

## Outcome and boundary

Persist accepted closed native bars locally so a process restart does not erase
them or silently accept a correction. This is a local capture/spool boundary for
future Supabase M1 synchronization, not a replacement for that requirement or for
30-day Parquet raw ticks. No strategy, fills, intrabar ordering, historical forming
bar replay or profitability is inferred from these monitoring windows.

## Acceptance before implementation

- AC-01: Optional private absolute history directory, fixed database filename;
  absent means explicitly disabled history, not durable success. Fail startup on
  unsafe file/directory permissions, symlinks, wrong identity/config, incompatible
  schema or corruption. Database/sidecars stay owner-private. Existing chart-only
  monitoring remains supported; it is not release-ready history capture.
- AC-02: In one SQLite WAL/FULL transaction, store a unique boot/sequence receipt,
  new closed bars with first-receipt/time provenance, and latest validation frame.
  Retain the next native bar's raw timestamp as evidence for the closure inference.
  Do not store the forming row as closed. Matching receipts/bars deduplicate;
  changed receipts/closed bars conflict, with no partial inserts. Decimal values,
  raw broker timestamps, UTC mapping, offset, basis, identity and build persist.
- AC-03: Commit before publishing the in-memory chart or acknowledging ingress.
  Storage/lock/quota failure returns a redacted 503 and latches chart rejection
  until reviewed restart. Quote monitoring remains independent; trading remains
  disabled. Blocking SQLite work runs outside the async request event loop.
- AC-04: Restart restores validation baselines but no live chart/freshness state.
  The API gets a new boot; old packets fail. Previously closed bars cannot change
  across restarts or after leaving the monitoring window. Wall-clock rollback
  cannot backdate receipt provenance. Crash tests distinguish before/after commit;
  process termination is not power-loss or disk-controller evidence.
- AC-05: Owner-only bounded closed-bar history reads retain first receipt time,
  not candle-open time as historical availability. Pagination uses increasing raw
  bar time and an immutable receipt high-watermark, scoped to this archive identity.
  Later captures cannot enter an earlier watermark. This is replay ordering, not
  proof of when a strategy ran or a complete historical dataset. No public route,
  executor-token substitution, account selector or mutable history endpoint.
- AC-06: Fixed 128 MiB SQLite page quota, bounded lock wait, 70%/85% usage states,
  no automatic pruning or overwrites of closed evidence. Quota excludes SQLite
  sidecars/filesystem overhead and does not replace target disk monitoring.
  Preserve gaps, including gaps between paginated rows; never synthesize bars.
- AC-07: Verify temporary real databases, concurrent duplicate/conflict writers,
  atomic rollback, rejected/invalid ingress, restart, process crash, permission,
  clock and storage failure, owner isolation and safe disabled configuration.
  Retain exact revision/environment evidence. Actual MT5, sync worker, target-host
  backup/restore/retention, raw ticks and full Demo release remain separate gates.

## Implementation plan and status

Use a dedicated SQLite file, not the command journal. One configured Demo identity
and offset-validity interval per archive. Record an ADR for this durable boundary.
Add archive integration and authenticated history API using existing owner checks;
no new dependencies or database platform. Add local tests before claiming local
acceptance. Local implementation now has temporary SQLite, subprocess crash,
ASGI owner-isolation and real-loopback HTTP evidence for AC-01 through AC-07;
see [verification](../verification/SCN-007-durable-bar-history.md). This is local
acceptance only, not power-loss, actual MT5, target-host or full Demo acceptance.
Full Demo remains NOT READY.
