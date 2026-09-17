# ADR-015 Explicit local recovery operator

2026-09-17, SCN-009 AC-04, base 36fabc7. Extend the existing internal Python wheel
with `sochron-recovery`; no new dependencies, service, API endpoint, scheduler or
broker authority. Keep `sochron-sync` and default Compose behavior unchanged.

## Bundle and publication

An explicit private configuration names the three existing source database files,
the expected RecoveryBinding, age/span admission and operator provenance claims.
Unknown fields are denied; no credential field is accepted. Config identity is
its exact byte SHA-256. Restore/verify use the unchanged configuration without
accessing original database paths; no discovery or automatic path rebinding occurs.

Backup creates only a new owned 0700 directory and three snapshot subdirectories
in command -> sync -> archive order. Reuse the WAL-aware snapshot engine and the
full read-only domain inspector. Publish `bundle.json` only after all members and
domain evidence validate, then fsync it and its directory/parent. Reverify the
published bundle before returning success. The member set is exact; extra files,
INCOMPLETE, missing members or inconsistent evidence deny admission. On ordinary
failure or SIGINT/SIGTERM, retain newly created output with best-effort INCOMPLETE.
Never mark or replace a preexisting output. A killed process before publication
leaves no accepted bundle. After an ambiguous termination, verify the exact output
before choosing a new operation; do not overwrite it or infer success from existence.

The manifest records original capture interval, operation interval/duration,
config hash, member-manifest hashes, domain evidence, producer identities and
optional parent bundle hash. Members also retain their database/schema hashes.
All metadata files remain 0600 and bounded. Databases remain confidential despite
redacted metadata; no encryption/upload/off-host storage is supplied by this command.

Restore first verifies the source, creates only new private inspection directories,
materializes byte-identical member databases and re-audits the resulting set. It
rechecks the source bundle and config before publication, records the parent bundle
hash and retains the original data capture interval. Each inspection member must
record its original database hash as parent; backup members have no parent. No
live database filenames, sync.lock, service config or runtime mounts are created.
Restoration here means inspection materialization, not application activation.

## Identity and timing

The producer records SHA-256 of all current application package `.py` files,
Python/SQLite/source ID and the direct/core runtime dependency versions. Essential
recovery module files must exist; an empty/zip-only code inventory is denied.
Verification requires exact current application-module file hashes. Other artifact
versions need a separately reviewed compatibility/migration procedure. Recorded
runtime versions are evidence, not authorization for an untested target/runtime;
target runtime admission remains separate. This is file identity, not runtime
memory attestation or a package signature.

Config's `operator_provenance_claims` contains source revision and artifact hash.
They are explicitly claims, not authenticated by this tool. The package verifier
independently ties its installed wheel and source bytes to retained build evidence.
Custody/signing and owner/target admission remain release concerns; checksums do
not authenticate a malicious owner who rewrites both data and metadata.

Maximum bundle operation time is a cooperative 180 seconds, encompassing member
operations and audits with their narrower limits. Kernel-blocked I/O is not a
hard timeout. Config/metadata sizes are bounded to 16/64 KiB. CLI elapsed time
includes final verification; manifest duration measures work through prepublication
validation. The installed rehearsal also measures whole fresh-process times.
Capture age means time since the oldest DB snapshot, not market freshness or a
proved business RPO. Inspection does not make the data recovery point newer.

## Authority and delivery

CLI requires an explicit action/config and validates applicable bundle/output
arguments; errors never echo rejected arguments or paths. SIGTERM/SIGINT produce
STOPPED/130, ordinary denial 2, admitted operation 0. stdout contains bounded
status/timing/hash/state counts only. All results keep execution_ready and Auto
Trading false; broker/destination reconciliation remains NOT_RUN.

This delivers the local capture/verify/inspection workflow with synthetic installed
rehearsal. It does not resume a worker/executor or grant deployment authority.
Actual-target restoration/activation/reconciliation, off-host/encryption, approved
RPO/RTO and release burn-in remain uncompleted gates.
