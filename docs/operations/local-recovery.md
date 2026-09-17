# Local recovery operator (SCN-009)

The internal wheel now provides `sochron-recovery` and the equivalent
`python -m sochron_worker.recovery_cli`. Use the reviewed installed artifact and
locked runtime from the [Python delivery instructions](native-m1-sync.md).
The repository's dependency-only development `.venv` does not automatically install
console scripts. No daemon, schedule, API route, upload or trading activation is
enabled. Full Demo remains NOT READY.

Only synthetic fixture databases were operated during implementation. Before an
owner/target operation, confirm exact paths, artifact/runtime admission, backup
custody and authority. Do not modify a live directory's permissions blindly to
make a check pass. This command cannot repair missing risk baselines or release halts.

## Explicit private configuration

Use a canonical absolute config path, existing owned 0700 parent, 0600 regular
single-link config file. All source databases/sidecars must meet the snapshot
engine's [private path requirements](sqlite-snapshots.md). The backup output's
parent must already exist, be canonical, owned and 0700. The output itself must
not exist. There is no automatic creation of broad parent paths.

Configuration shape below is a template, deliberately invalid until replaced with
the recorded existing identities and reviewed release evidence. Do not invent a
new archive/owner ID, choose a different source binding or paste a credential here.

```json
{
  "binding": {
    "identity": {
      "executor_id": "<existing-demo-executor>",
      "account_ref": "<existing-demo-reference>",
      "server": "<existing-demo-server>",
      "currency": "<existing-currency>",
      "margin_mode": "<existing-margin-mode>",
      "symbol": "<exact-existing-symbol>"
    },
    "active_experiment_id": "<existing-experiment>",
    "archive_id": "<existing-archive-uuid>",
    "owner_id": "<existing-owner-uuid>",
    "source_directory": "/srv/sochron/private/bars",
    "destination": "<existing-destination-origin>",
    "offset_seconds": 0,
    "chart": {
      "offset_valid_from_server_s": 0,
      "offset_valid_until_server_s": 0
    }
  },
  "command_database": "/srv/sochron/private/commands/journal.sqlite3",
  "sync_database": "/srv/sochron/private/sync/sync.sqlite3",
  "archive_database": "/srv/sochron/private/bars/bars.sqlite3",
  "max_age_seconds": 3600,
  "max_span_seconds": 60,
  "operator_provenance_claims": {
    "source_revision": "<reviewed-40-character-source-commit>",
    "artifact_sha256": "<verified-64-character-wheel-sha256>"
  }
}
```

Replace offset and interval with the archive's existing binding, not the example's
zeros. Age/span are explicit admission values (1..86400 seconds, span<=age), not
an approved RPO/RTO. The example paths do not imply an existing installation.
Unknown fields, duplicate JSON keys and credentials-as-extra-fields are denied.
Operator revision/artifact fields are labelled assertions; retain independent
release/build evidence. Actual application-module hashes are also recorded and
must match the inspecting artifact. Runtime identities do not clear target gates.

## Commands

These are invocation examples, not commands executed against an owner installation:

```bash
sochron-recovery backup --config /srv/sochron/private/recovery.json --output /srv/sochron/backups/run-001
sochron-recovery verify --config /srv/sochron/private/recovery.json --bundle /srv/sochron/backups/run-001
sochron-recovery restore --config /srv/sochron/private/recovery.json --bundle /srv/sochron/backups/run-001 --output /srv/sochron/inspection/run-001
```

Backup captures command journal, then sync journal, then archive. It validates the
causal source prefix and every domain record before publishing bundle.json last.
This is not a cross-database atomic transaction. Output contains exactly bundle.json
and commands/sync/archive subdirectories, each with snapshot.sqlite3 + manifest.json.
Config contents, credentials, source paths and broker tickets are not copied into
bundle metadata; database contents are still confidential.

Verify is read-only and reruns hashes, exact member checks and domain validation;
a stored success record alone is insufficient. Restore creates only a separately
verified inspection bundle with the original capture interval and parent hash.
It works when original sources are unavailable. Preserve the config bytes unchanged
when moving it to an inspection host; its old source paths are data and are not
opened by verify/restore. Do not edit config paths to activate the inspection files.

Exit 0 means the requested local operation was admitted, **not** that execution or
external reconciliation is ready. stdout always has execution_ready=false and
auto_trading_enabled=false. UNKNOWN/quarantine, send attempts and total halts remain
visible unresolved conditions. Do not start services from these files, recreate
sync.lock, replay queued work, reset a cursor/budget or clear a halt based on exit 0.

Exit 2 is redacted RECOVERY_BUNDLE_UNAVAILABLE; SIGINT/SIGTERM is STOPPED/130.
Failed newly created output is retained with best-effort INCOMPLETE. Missing bundle
manifest, extra files and incomplete output cannot verify. Do not overwrite existing
output or delete it automatically. If the command was killed after an uncertain
publication point, verify that exact path before attempting another operation.

## Recovery evidence and remaining gates

The CLI reports total elapsed seconds and age of the original capture; manifests
record capture/operation intervals and prepublication duration. The installed
rehearsal additionally measures fresh-process times and reads restored tables with
independent SQL. These are tiny local synthetic workloads, not target capacity,
power-loss proof or approved RPO/RTO. See [retained evidence](../verification/SCN-009-operator-recovery.md).

Still required: separately authorized application activation and external broker/
destination reconciliation, target-host and off-host restore, encryption/key custody,
retention policy execution, approved recovery objectives and release burn-in. No
off-host copy, key management, hosted Supabase export or raw-tick recovery is supplied
by these SQLite commands. Keep the existing Demo/Auto Trading gates closed.

## Restored-service rehearsal and query-only follow-up

The package verifier now reconstructs only its generated fixture runtime paths
from an inspection bundle, preserving the exact original source binding. It
explicitly restores WAL mode, supplies a new private sync lock after its fixture
worker has exited, and runs installed `sochron-sync reconcile`. Independent SQL
and the loopback receiver verify one original send, one retained attempt and the
confirmed cursor. A separate installed-process query-only broker simulator checks
unavailable/missing/exact replies and retained command risk/halts/exposure.
This is not a supported owner activation procedure; do not copy those fixture
operations into a running installation. Existing owner files are never overwritten.

For an already admitted runtime under authorized destination access, the explicit
`reconcile` command is the no-send pending read-back described in the
[worker runbook](native-m1-sync.md). It does not activate inspection bundles,
rebind source paths, release quarantine/halts or certify all destination history.
Its NO_PENDING result must not be treated as permission to resume trading.
See [rehearsal evidence](../verification/SCN-009-restored-services.md).
