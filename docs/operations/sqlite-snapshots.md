# Internal SQLite snapshot engine (SCN-009)

This is a development library, not a completed operator backup/recovery workflow.
No daemon, API endpoint, CLI, upload or retention deletion is enabled. Full Demo
remains NOT READY. Use only synthetic fixtures until the domain bundle/operator
gates are complete; no owner database has been backed up or restored in this task.

`sochron1k.sqlite_snapshot` exposes:

- `create_snapshot(source: Path, output: Path)`: read an existing private database,
  including its committed WAL state, and create a new private snapshot directory.
- `verify_snapshot(directory: Path)`: validate bounded manifest, exact file set,
  private ownership, database/schema hashes, SQLite integrity and foreign keys.
- `materialize_snapshot(snapshot: Path, output: Path)`: make a byte-identical,
  separately verified inspection copy in a new directory. This does not make it
  safe to resume an execution service or sync worker.

Paths must be absolute/canonical. Existing parent directories must be owned by the
process and mode 0700; database and existing WAL/SHM files must be regular,
single-linked, owned and mode 0600. The engine does not change unsafe source modes.
Some existing command-journal setups may therefore require separately reviewed
permission preparation. Do not chmod/chown a running operator directory blindly.

Each accepted output contains exactly `snapshot.sqlite3` and `manifest.json`.
The standalone snapshot is DELETE-journal mode; source mode is unchanged. The
manifest records the UTC backup interval, duration, SQLite version, database size,
database/schema hashes and optional parent database hash. It excludes source paths,
account payloads and credentials, but the database itself remains confidential.
There is no encryption or off-host copy yet. Hashes do not authenticate an untrusted
manifest; obtain both through the reviewed backup custody process before any future
operator restore. Materialization preserves the original backup timestamps.

Any error is `SQLITE_SNAPSHOT_UNAVAILABLE`, without source paths or raw DB errors.
Existing output paths are never overwritten. Incomplete output is retained; missing
manifest, INCOMPLETE marker, extra files, tamper or unsafe permissions are denied.
Even a valid manifest is **not** application or broker recovery readiness. Fsync
and process-exit tests are not power-loss/device-controller evidence.

The 256 MiB limit applies separately to main DB and sidecars; no compression is
performed. The 30-second deadline is checked between backup/SQL/copy work and cannot
interrupt a blocked kernel I/O operation. Continuous writers can grow WAL while
a read snapshot is pinned; bounds/deadline fail instead of claiming success.

Development check:

```bash
.venv/bin/pytest -q tests/test_sqlite_snapshot.py
```

The [read-only recovery-set inspector](recovery-set-audit.md) now checks domain
relationships across three ordered snapshots without starting their writers.
Next: capture orchestration and a compatible recovery-set manifest for command
journal, bar archive and sync journal; explicit operator commands; isolated reconciliation;
measured recovery objectives; then approved actual-target/off-host rehearsal.
Do not rebind a sync journal, initialize a second journal or clear a halt to make a
restore pass. See [contract](../contracts/SCN-009-local-recovery.md) and
[ADR-013](../decisions/ADR-013-private-sqlite-snapshots.md).
Local engine checks and their exact source/artifact identities are recorded in
[SCN-009 evidence](../verification/SCN-009-sqlite-snapshots.md); they do not clear
the outstanding domain/operator or target release gates.
