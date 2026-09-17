# SCN-009 installed local recovery operator

2026-09-17; base `36fabc7171e0f41d4ccacceeb175c857133b4b45` plus dirty candidate
inputs recorded below. The containing commit identifies the delivered revision.
macOS 26.6.2 arm64, Python 3.14.7, SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8,
uv 0.12.15. Local Linux arm64: Docker 29.5.2, Compose 5.5.1, Python 3.14.7,
SQLite 3.53.4 with pinned source/linkage admission.

## Outcome and acceptance boundary

AC-04's local installed backup/verify/isolated-inspection workflow is implemented
and verified. The wheel supplies `sochron-recovery` and the equivalent module
entry point. It captures command -> sync -> archive, verifies domain relationships,
publishes completion metadata last and restores into a new inspection directory.
No original source access is required by verify/restore; no paths are rebound.

This is not application activation, external reconciliation or full recovery
acceptance. Full Demo and unattended release remain NOT READY. Actual-target,
off-host/encryption/key custody, owner-approved RPO/RTO, hosted exports, MT5 and
release burn-in are NOT RUN. No owner database was read, backed up or restored.
No hosted write, deployment, broker action or paid resource was performed. Existing
UI/API processes were not restarted; Auto Trading remains off.

Changed scope: two worker modules, console metadata, package verifier, 26 focused
tests and operational/acceptance documentation. No dependency, schema, migration,
UI, Auth route, service schedule or default Compose behavior changed. Operations
and risk-recovery skills guided private WAL-aware capture, isolated restoration
and preservation of UNKNOWN, reservations, baselines and halts.

## Oracles and negative cases

- Actual domain writers create synthetic command UNKNOWN, one exposure reservation,
  daily/experiment baselines, both halts, an archive and sync UNKNOWN with one send
  attempt and cursor zero. Snapshot/domain checks run against real SQLite files.
- A fresh non-editable wheel install runs console backup, isolated module verify
  and console restore in separate processes. Synthetic original source directories
  and the command file are temporarily renamed unavailable. Neither operation
  recreates them. Independent SQL on the inspection checks UNKNOWN, exposure=1,
  baselines=100000/100000, both halts=1, sync UNKNOWN/attempts=1 and cursor=0.
- Inspection preserves original capture interval, database bytes, aggregate
  evidence and parent-bundle hash. Backup bytes remain unchanged. The original
  synthetic worker subsequently reconciles its receiver without a second store;
  this is not activation/reconciliation of the inspection bundle.
- Existing outputs retain their marker/data. Same/nested restore targets are
  rejected without invalidating the source. Missing/extra/mixed members, symlinks,
  unsafe permissions, manifest/config/code/evidence drift and false member lineage
  fail before restoration. Member-lineage corruption is tested even after its
  aggregate hash has been recomputed.
- Missing risk evidence, credential-like extra config fields, source permission,
  deadline, fsync and mid-capture config failures never yield an accepted bundle.
  SIGTERM at publication returns STOPPED/130 and INCOMPLETE. A separate process
  abruptly exits before publication; no completion manifest exists or verifies.
  This abrupt-exit case uses `os._exit(73)`, not a claimed physical power failure.
- CLI rejects missing/invalid arguments without disclosing random key-like input,
  paths or tracebacks. All successful results retain execution_ready=false,
  auto_trading_enabled=false and both external reconciliations NOT_RUN.

Hashes establish file identity, not authenticity or memory attestation. Operator
revision/artifact fields are labelled claims. The build verifier independently
compares installed wheel/source bytes; its revision is the base with dirty=true,
not a claim that the candidate was already committed. Exact-code admission is
not permission to use another runtime/host. Cooperative deadlines do not bound
kernel-blocked I/O. See [ADR-015](../decisions/ADR-015-local-recovery-operator.md)
and the [runbook](../operations/local-recovery.md).

## Measured installed rehearsal

Final package report captured data between
`2026-09-17T08:07:25.132457+00:00` and `2026-09-17T08:07:25.175054+00:00`.
The inspection retains this interval, not restoration time as a newer recovery point.

| Operation | Whole fresh process | CLI operation including final verification |
| --- | ---: | ---: |
| Backup | 0.640416500 s | 0.077032792 s |
| Verify | 0.148558084 s | 0.023403250 s |
| Restore to inspection | 0.214572708 s | 0.083555875 s |

Tiny local synthetic workload only: not approved RPO/RTO, capacity or target timing.
Backup manifest SHA-256: `7cac23f9a6d5a291d04f69f271132e4b16c7afafa817cdaf62310c084c37e2a7`.
Inspection manifest SHA-256: `adaba44801b4d4095e9fef608dcd04d57f6836b0fec0e52d34a8b1b42d983078`.
Temporary fixture databases and fresh venv are cleaned by the scoped verifier;
artifact/results remain under ignored output paths. No owner data was deleted.

## Commands and retained evidence

- `.venv/bin/pytest -q tests/test_recovery_bundle.py --tb=short`: 26 PASS, 6.35s.
- `bash scripts/check-scn-001-local.sh`: latest rerun 568 PASS, 32.01s;
  source/test Ruff and secret scan PASS. Initial final-candidate run also passed.
- `.venv/bin/ruff check scripts/check-worker-package.py`: PASS.
- `/tmp/sochron-uv.dALxxk/venv/bin/uv lock --check`: PASS; no dependency change.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS, exact wheel contents and byte-identical rebuild, locked non-editable
  production install, both entry points, no source/dev imports, recovery rehearsal
  and original sync restart/no-resend regression.
  `output/worker-package/79c5555d2f52464d9502967d62455720/result.json`,
  recorded 08:07:26.679187 UTC.
- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS; `output/worker-container/sochron-worker-48db15853bed/result.json`,
  08:07:20.381564–08:08:12.150866 UTC; cleanup=0, synthetic key removed.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  API/web Compose smoke PASS;
  `output/compose/sochron-verify-82d83e31a1ed/result.json`,
  08:07:21.328255–08:08:17.765195 UTC; cleanup=0.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-48db15853bed:candidate`:
  545 PASS, 19.39s; `output/container-python/sochron-python-621aefe1d46d/result.json`,
  08:09:45.019206–08:10:12.125499 UTC.
- Same command with `sochron-verify-82d83e31a1ed-api:local`: 545 PASS, 19.38s;
  `output/container-python/sochron-python-affecc605fbe/result.json`,
  08:09:45.019246–08:10:12.135488 UTC. Each Linux run excludes 23 workstation MT5
  static scanner tests; neither invokes a terminal/compiler.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: PASS. Installed/pinned skill integrity is not service readiness.
- Exact retained artifact hashes and current input hashes were compared against
  final reports. Linux-generated requirements are checked in retained build
  contexts, not a nonexistent repository-root requirements.txt. An initial ad-hoc
  comparison stopped on that missing root file; corrected context-aware comparison
  passed. This was an evidence-reader error, not a runtime/test failure.
- Local Docker `ps` found no running containers after fixture cleanup. No images
  or retained volumes were broadly pruned. Full browser/Auth/PostgREST tests were
  not rerun: those boundaries are unchanged; API/web container smoke is narrower
  evidence and does not replace their prior integration reports.

## Final candidate identities

| Source | SHA-256 |
| --- | --- |
| recovery_bundle.py | `56b7dbdc0d77dad1089c2efad5577007733e9d858974c8c77a5587fc20d4f3e7` |
| recovery_cli.py | `22e09c058e10ef37353ae2d83eba75a1347a80e483bab6163d4a3d7c2410d419` |
| test_recovery_bundle.py | `4f2e571f4b485cb6e43178e342beea9d9f29d7b767930e26717ebec1d9fb9b40` |
| check-worker-package.py | `467de2a4b7717e7069a9f6e0c02abd24662bda2c1a6fcac856fe940cf261ff8b` |

- Wheel: `16ec00a1cbdfdd90339205e3c3feb5ce4bd8f45918d793bb49cfab0ebbe6c109`.
- Sdist: `8d00e880280954c650cb4666887e3a0d403d4c07cdc21ad3ada899b62d7482fb`.
- Locked artifact requirements: `4b1ac33c8d278e015c3aba2250cd65f20891f3705c61867fd831ca35950b5289`.
- Worker image: `sha256:55709ccd8b2b704cce5782131454e9bd65119d312e56573ad7729c8765ff0cda`.
- API image: `sha256:eb751be1aa990b491c396b9acdb25fb555bcced4e933305535ef73b6583ee24c`.

Reports retain the full input inventory, runtime/source/linkage and fixture evidence.
Documentation-only completion changes do not alter those tested runtime inputs.
Next safe work is application recovery/activation design and synthetic external
reconciliation, plus remaining Demo execution/strategy integration. Actual owner
identity, broker contract/host, destination and recovery objectives remain required
before their corresponding external operations; local development can continue.
