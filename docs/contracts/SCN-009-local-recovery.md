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
recovery admission. AC-03 now has local read-only domain/cross-store admission
evidence; see [audit verification](../verification/SCN-009-recovery-set-audit.md).
Operator capture/materialization orchestration and measured recovery (AC-04),
external reconciliation, full Demo, off-host recovery and actual-target RPO/RTO
remain NOT READY/NOT RUN. Do not label the entire recovery contract PASS.

### AC-03 read-only recovery-set admission (before implementation)

Audit three already verified individual snapshots, captured in command -> sync ->
archive order. The archive is append-only: every ledger row through the pending
batch must match the exact contiguous M1 prefix in the later archive, not merely
exist somewhere in it. Later archive rows are allowed; a cursor ahead of archive,
skipped row, mixed identity, different binding or changed payload is denied.
This establishes a compatible causal set, not a cross-database atomic instant.

Require explicit expected Demo identity, active experiment, archive/owner IDs,
original source-directory binding, destination and offset/config. No credentials,
environment discovery, path rebinding or original source access. Require an aware
audit time and explicit bounded maximum snapshot age/span, used for admission only,
not an inferred owner-approved RPO. Pinned schema fingerprints plus user_version
must match the current schema implementations; reject extra triggers/tables/indexes.

Validate all command payload fingerprints, scope/identity, transition chains,
attempts, broker order/deal volumes, exposure reservations and risk baselines/halts.
After the initial atomic CREATED/VALIDATED/QUEUED chain, never admit a rewind into
those states that could make a previously dispatched command look unsent.
Require the active risk baseline and a baseline for every retained experiment;
reject missing risk evidence rather than initializing it. Validate all archive
receipts, all four timeframes, closure/grid/offset evidence and latest projections.
Validate the entire sync ledger, cursor, state, attempts and clock ordering against
the archive prefix. Retain UNKNOWN, QUARANTINED and exhausted budgets as unresolved
conditions, never reset or relabel them VERIFIED. Return only bounded counts,
state summaries and hashes; execution_ready remains false even for an admitted set.

Use mode=ro/query_only inspection, bounded DB fields/queries and one overall
cooperative deadline. Reverify snapshot bytes/manifests after all domain checks.
Do not invoke Journal/BarHistory/SyncJournal constructors on snapshots, since they
initialize/change modes or acquire writer authority. Tests must use actual domain
writers to construct fixtures, then independently corrupt rows while retaining a
valid SQLite snapshot/hash, so generic integrity cannot substitute for the audit.
Cover missing baseline, cleared evidence inconsistencies, broken transition/order/
exposure relationships, older/wrong archive, skipped ledger rows, wrong origin/owner,
UNKNOWN/quarantine/budget preservation, stale/future/mixed capture intervals,
schema drift, clock and output changes; inspection must leave every input unchanged.
CLI/capture orchestration, isolated multi-store materialization and measured recovery
remain AC-04 work; this audit does not resume an application or contact a destination.
