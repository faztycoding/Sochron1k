# Internal recovery-set audit (SCN-009)

This internal API is used by the explicit [local recovery operator](local-recovery.md),
not a daemon or HTTP route. Do not point it at user databases as part of this task.
Full Demo remains NOT READY. The operator supplies capture/materialization and
artifact/config records; no account/service has been resumed here.

`sochron_worker.recovery_audit.audit_recovery_set` accepts the three directories
produced by the [SQLite snapshot engine](sqlite-snapshots.md), a secret-free
`RecoveryBinding`, an aware `now`, and explicit `max_age_seconds`/`max_span_seconds`.
Capture command journal first, sync journal second and archive last. It validates
the resulting causal prefix; these are not one atomic transaction. Paths must be
distinct private snapshot directories, not live DB paths. Isolated copies made
with materialize_snapshot keep their original snapshot interval and can be audited.

Binding fields: Demo identity, active experiment ID, owner/archive UUIDs, original
source-directory string, destination origin, broker offset and chart validity
interval. Do not include a key, password, private token or service config file.
The original directory need not exist on the inspection machine; its recorded
string must still match the sync journal. Do not edit it to make the check pass.

The inspector pins exact current schemas, validates domain relationships and
requires every sync batch to match the exact M1 archive prefix. A later archive
suffix is allowed; older archive content, missing rows, skipped rows, different
account/config, clock inconsistencies and missing active risk baseline are denied.
All four archive timeframes are checked, not only M1. Halt and risk values are read
without normalization or release; no missing baseline is initialized.

Returned counts/hashes describe local evidence only. Pending UNKNOWN or QUARANTINED
and exhausted sends remain unresolved. Even an admitted set has execution_ready
false and broker/destination reconciliation NOT_RUN. Do not run a restored journal,
replay pending work, remove sync.lock, reset attempts or clear a halt based on this
result. The result is not MT5 confirmation of fills, closure or SL protection.

Any failure is the redacted `RECOVERY_SET_UNAVAILABLE`; no raw SQL/path/payload is
returned. Original inputs are retained unchanged, including failed sets. Inspect
exact source revision/config/custody and use synthetic reproduction to investigate;
do not dump sensitive database rows into chat or logs. Current bounded admission
and the limits of hash-based verification are detailed in
[ADR-014](../decisions/ADR-014-recovery-set-admission.md).

Development check:

```bash
.venv/bin/pytest -q tests/test_recovery_audit.py
```

Exact environment, regression commands and evidence are in
[local verification](../verification/SCN-009-recovery-set-audit.md). RPO/RTO have not
been approved: choosing age/span for a synthetic test does not set deployment
objectives. No hosted export, off-host copy, encryption or target recovery is covered.
