# Target evidence admission

Status: SCN-036 provides a local query-only admission boundary. It does not run a
target verifier, compile MQL5, connect MT5, send an order, exercise a fault or grant
release authority. Auto Trading remains off.

## UI and API positions

| Evidence | Browser position | API source |
| --- | --- | --- |
| EA build and artifact identity | Demo readiness row 06 | `GET /api/owner/target-evidence` |
| Demo broker round trip and broker-side SL | Demo readiness row 07 | `GET /api/owner/execution` plus `GET /api/owner/target-evidence` |
| Target recovery, alerts and restore | Demo readiness row 08 | `GET /api/owner/target-evidence` |

The owner route requires the existing active owner session and returns only
redacted references and fixed states. `GET /api/ui/demo-readiness` projects those
states into the public fixed ledger, with every release and trading flag false.

## Private configuration

Create a dedicated directory owned by the API UID with mode `0700`, then write a
mode `0600` config using an absolute canonical manifest path:

```json
{
  "enabled": true,
  "snapshot_file": "/app/data/target-evidence/manifest.json",
  "source_revision": "0000000000000000000000000000000000000000",
  "target_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "decision_revision": "reviewed-demo-plan-revision",
  "decision_recorded_at_utc": "2026-09-20T08:00:00Z",
  "max_age_seconds": 3600
}
```

Set `SOCHRON_TARGET_EVIDENCE_CONFIG_FILE` to that file. Its decision revision and
time must exactly match the private `SOCHRON_DEMO_READINESS_CONFIG_FILE` record or
the API refuses startup. `{"enabled":false}` is the only disabled file form;
omitting the environment variable is the normal default.

## Atomic snapshot contract

The selected manifest uses protocol `sochron.target-evidence-manifest.v1` and an
ordered `reports` array for `target_artifact`, `broker_round_trip` and
`recovery_observability`. Each entry pins a basename-only report filename, exact
byte count and SHA-256. Reports use `sochron.target-gate-report.v1`, repeat the
source/target/decision bindings and contain the fixed checks documented in
[`target_evidence.py`](../../services/api/src/sochron1k/target_evidence.py).

A completed report needs a verifier digest, UTC start/finish and an evidence digest
for every check. `PASS` requires every check to pass; `FAIL` requires complete
checks with at least one failure; `NOT_RUN` cannot claim a verifier, time or digest.
The producer should write new private report files and manifest in a staging
directory, sync them according to the target recovery design, then atomically
publish the complete directory/snapshot. Never edit the admitted files in place.

## Interpretation

- `evidence_admitted`: normalized evidence is intact, bound and fresh; not release.
- `evidence_failed`: a complete normalized report contains a failed check.
- `not_run`: the normalized report explicitly contains no completed evidence.
- `stale`: evidence exceeded its configured age.
- `degraded`: permissions, identity, digest, shape, time or read stability failed.

Paths, filenames, raw target identity, decision text, verifier/check digests,
credentials and account/server identity are never returned. A real target verifier
must retain its raw logs separately and be reviewed before its output can support a
release decision.

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_target_evidence.py tests/test_demo_readiness.py tests/test_api_safety.py tests/test_owner_auth.py
npx -y -p node@24.21.0 npm run test --workspace @sochron1k/web -- src/demo-readiness-api.test.ts src/App.test.tsx src/connection-api.test.ts
```

These tests use generated local files only. Real target compile, broker round trip,
restart/network-loss, alert delivery, restore, latency and burn-in remain `NOT RUN`.
