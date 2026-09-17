# ADR-014 Read-only causal recovery-set admission

2026-09-17, SCN-009 AC-03; base e99007a. No new dependency, service or execution
authority. `sochron_worker.recovery_audit` depends on shared API domain models and
existing pure worker decoders. The API does not import a worker, and no running
process invokes this inspector automatically.

## Decision

Inspect three verified standalone snapshots in command -> sync -> archive capture
order. The archive is immutable/append-only: all retained sync batches, including
the unresolved batch, must be the exact contiguous M1 prefix of that later archive.
A newer archive suffix is allowed. Compare raw payload strings and receipt/time
cursors, not just matching timestamps or row counts. This supports a worker
snapshot before a later archive snapshot without falsely claiming an atomic
cross-database backup. The command journal has no stored foreign key to this bar
archive; its relationship is checked against the explicit expected account/symbol,
not an invented signal-to-bar link.

Require an explicit secret-free RecoveryBinding containing Demo identity, active
experiment, owner/archive IDs, original source path, destination and chart/offset
configuration. The original path is a lexical identity only; it is never resolved,
opened, replaced or rebound. Snapshots must retain their original binding even
when inspected elsewhere. This inspector cannot authorize changing that binding.

Pin exact sqlite_schema fingerprints and user_version for the three existing
writers. This includes tables, indexes, constraints and triggers, not only column
names. Any schema change, including SQL-text changes, needs explicit reviewed
admission and updated fixtures. Tests construct real current writer databases,
so the fingerprint pins fail if those writers drift. Generic SQLite integrity and
hash validation run before/after domain checks; they cannot replace domain checks.

Inspect only mode=ro/query_only connections to snapshot.sqlite3. Do not invoke
Journal, BarHistory or SyncJournal constructors, which can initialize, change
journal mode or acquire writer locks. Validate all commands, transition chains,
attempts, order/deal volumes, exposure, risk rows, receipts, bars in all four
timeframes, latest frames, sync ledger and cursor. Prohibit rewinding a command
into the initial atomic reservation states;
recorded transition continuity alone is not sufficient evidence against replay.
Require an active risk baseline
and a baseline for every retained experiment. Missing risk evidence is denied,
not initialized. Existing journals with missing baseline evidence need a separate
reviewed operational decision; the inspector never repairs them.

This revision admits the current open-intent/one-order command-journal model.
Future close/cancel command models or new outcome fields require explicit schema/
semantic admission. Persisted broker rows are historical assertions, not fresh
confirmation from MT5. Partial fills require exact retained deal-volume sums;
missing deal evidence is denied rather than guessed. UNKNOWN, quarantine, halts
and exhausted send budgets remain visible unresolved conditions, not validation
errors merely because they need later external reconciliation.

Caller-supplied audit time and maximum age/span are admission inputs, not an
owner-approved RPO. Limits: positive integer age/span <=24 hours, span<=age;
100,000 rows per table, 2 MiB SQLite field/row bound, existing 128 MiB archive and
64 MiB sync quotas plus the snapshot engine's 256 MiB cap. Command decimal text
is <=80 characters with exponent between -100 and 100; a 512-digit arithmetic
context keeps bounded sums exact. The overall 30-second cooperative deadline is
checked in Python loops and SQLite progress callbacks; blocked kernel I/O is not
interruptible by this bound. Exceeding limits denies admission without pruning.

## Evidence and remaining authority

Return bounded aggregate state and hashes, not payloads, account references,
original paths, broker tickets or credentials. `execution_ready` is always false;
broker and destination reconciliation are always NOT_RUN. No networking,
environment discovery, output writes, service starts or state resets occur.
All audit inputs are reverified after inspection. A self-consistent malicious
rewrite of both source and trusted backup metadata is not authenticated by a
checksum or this inspector; custody/provenance and external reconciliation remain
separate requirements. A cleared halt cannot be proven historically false from
one self-consistent snapshot alone.

This decision delivers local read-only admission, not the complete AC-03/04
operator recovery workflow. Capture orchestration, a recovery-set manifest,
isolated multi-store materialization, measured recovery and explicit operator CLI
remain next. Real target/off-host, encryption/key custody, RPO/RTO and external
reconciliation require their own evidence and owner authorization.
