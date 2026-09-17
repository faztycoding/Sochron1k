# ADR-013 Private SQLite snapshot engine

2026-09-17, SCN-009 AC-01/02. Internal shared library under the existing API domain
package; no new service, scheduler, endpoint, dependencies or execution authority.

Use SQLite's online backup API through an existing mode=ro connection with a pinned
read transaction. This includes committed WAL pages and excludes uncommitted/later
transactions without forcing a checkpoint. Sidecar bookkeeping is allowed by
SQLite; the reader never writes application tables or repairs a source. Bound main
database/sidecar sizes to 256 MiB each and backup work to a cooperative 30-second
deadline. This is not a hard OS I/O timeout or whole-filesystem quota.

Only canonical owner-private paths are accepted: parent directories 0700, regular
single-link files 0600, current process UID; no symlink or silent chmod.
New output directory must not exist. An independent backup target is normalized
to DELETE mode, checked for SQLite integrity/foreign keys, hashed and fsynced.
Manifest publication is last. On ordinary failure, keep output and best-effort
INCOMPLETE marker; a process killed before publication leaves no accepted manifest.
No automatic cleanup of evidence or overwrite of operator paths.

A snapshot's SHA-256/schema checks detect accidental change, not a malicious owner
who can replace both files and manifest. Same-UID hostile mutation and a compromised
filesystem are outside this private-directory boundary. Domain authenticity and
cross-store consistency are separate SCN-009 AC-03 gates.

Materialization first verifies a standalone DELETE-mode snapshot, then copies its
exact bytes to a new private inspection directory and rechecks hash/manifest/source.
This byte copy is **never used on a live source/WAL database**. Preserve the original
backup time interval and record its database hash as the parent; copying later must
not pretend the data recovery point became newer. The caller must separately measure
restore duration. Materialization does not change path bindings, initialize missing
tables, reset any halt/budget, start a service or authorize an external send.

The library has no CLI until domain bundle validation and explicit operator config
are defined. A valid individual snapshot does not prove that independently copied
command/source/sync databases form a consistent recovery set. AC-03/04, off-host
encryption/storage, RPO/RTO and actual-target backup/reconciliation remain required.
The helper's `execution_ready` is always false; it never constructs ExecutionService.

References: [SQLite backup semantics](https://www.sqlite.org/backup.html) and
[Python 3.14 backup API](https://docs.python.org/3.14/library/sqlite3.html#sqlite3.Connection.backup).
