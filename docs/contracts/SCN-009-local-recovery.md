# SCN-009 Local backup and recovery delivery

2026-09-17; High assurance; owner: project owner. Acceptance recorded before
implementation, base e369e29. Supports full Demo, not broker/hosted authorization.

## Required end state

Recover command journal (commands, attempts, broker identifiers, exposure, risk
baselines and halts), native bar archive and synchronization journal without
turning UNKNOWN into success, resetting a halt/budget or blindly replaying sends.
Backups alone are not recovery. Complete operator delivery requires compatible
multi-store evidence, isolated domain validation and measured restore/reconcile.
Off-host storage, encryption/key custody, RPO/RTO and actual-target approval remain
explicit owner/release decisions. Do not copy credentials into data bundles.

## Acceptance and sequencing

- AC-01 SQLite snapshot engine: read an existing canonical private owned regular
  database via mode=ro, never create/repair/checkpoint it. Use SQLite's backup API
  and a pinned read snapshot so committed WAL data is included and uncommitted data
  excluded. Fail on unsafe files/links/ownership, corruption, excessive size or
  deadline. Create only a new private output directory, never overwrite a target.
  Normalize the independent destination to DELETE journal mode; require integrity
  and foreign-key checks, fsync database/manifest/directory and publish a versioned
  completion manifest last. Retain incomplete outputs as unaccepted evidence.
  Manifest records UTC interval, duration, SQLite identity, size/hash and schema
  hash, not source path, account payload or credentials. A checksum is not a signature.
- AC-02 isolated materialization: verify exact manifest/file membership, bounds,
  canonical private ownership, checksum/schema/integrity before materializing into
  a new private directory. No overwrite, in-place restore, rebinding, initialization,
  networking or service start. Recheck output and record the parent snapshot hash.
  This produces an inspection copy only, not permission to dispatch commands.
- AC-03 domain rehearsal: validate application schemas and preserved command/
  attempt/order/deal/exposure relationships, baselines, halts, archive identity,
  closed bars, sync ledger/cursor/UNKNOWN/quarantine/send budgets. Fail closed on
  stale/incompatible/mixed bundles. Cross-file snapshots are not automatically
  one transaction: define and test source/sync consistency before bundle promotion.
  Confirm external state before any authorized resumption; do not reset identifiers.
- AC-04 operator delivery: explicit backup/verify/isolated-restore CLI, redacted
  errors and no implicit source/config discovery. Record artifact/config/revision
  provenance and recovery time/point evidence. No automatic retention deletion,
  upload, daemon or changes to existing processes. Actual-target and off-host
  rehearsal plus owner-approved RPO/RTO are required before unattended Demo.

Implement and verify AC-01/02 first as a shared internal engine; then AC-03 domain
bundle checks and AC-04 operator commands. Engine tests must use actual WAL files,
independent writer connections, interrupted/failed output, tamper/permission/link/
oversize/deadline cases, and a real command journal retaining UNKNOWN and total
halt. The engine must not import the API entry point or create an execution service.
Initial status: all criteria NOT RUN. Do not label this whole contract complete
when only the engine works. Hosted Supabase exports and raw-tick retention remain
separate recovery boundaries, not silently covered by a SQLite copy.

## Current acceptance

AC-01 and AC-02 have local engine verification with synthetic WAL databases and
an isolated copy of a synthetic command journal; see
[retained evidence](../verification/SCN-009-sqlite-snapshots.md). This is not domain
recovery admission. AC-03 and AC-04 remain NOT IMPLEMENTED/NOT RUN. Full Demo,
off-host recovery, actual-target reconciliation and RPO/RTO remain NOT READY.
