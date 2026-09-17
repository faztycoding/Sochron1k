# SCN-009 restored-service rehearsal and no-send reconciliation

2026-09-17; base `6da644a8f180a68a11228597015a849bb95214bd` plus dirty candidate
inputs. The containing commit identifies delivery; reports preserve the precommit
base and exact tested bytes. macOS 26.6.2 arm64, Python 3.14.7, SQLite 3.53.1,
pytest 9.1.1, Ruff 0.16.8, uv 0.12.15. Local Docker 29.5.2 / Compose 5.5.1,
Linux arm64 Python 3.14.7 and source/linkage-admitted SQLite 3.53.4.

## Outcome and scope

Installed `sochron-sync reconcile` now performs one pending UNKNOWN read-back
without invoking store, preparing a batch or incrementing attempts. Source and
destination binding, current source content and existing exclusive locks remain
required. Exact read-back may advance local evidence to VERIFIED; missing/partial
data yields PREPARED, read failure UNKNOWN, conflicts QUARANTINED. PREPARED is
REVIEW_REQUIRED, never an implicit send; existing quarantine is retained. NO_PENDING
does not certify all remote history, all source rows or recovery completeness.

Exit 0 means VERIFIED/NO_PENDING (or disabled configuration); unresolved/review is
3, quarantine/errors 2. `--once` remains run-only. The action uses the existing
private key/transport and can update the local journal. It is externally read-only,
not a read-only local database operation. Runtime flags always deny execution.

Changed production scope is the worker driver and CLI only. No API/Auth/UI route,
database schema, migration, dependency, risk policy, deployment or default worker
startup changed. The existing run path reuses the extracted source comparison
without altered send/retry semantics. Package verification and tests now exercise
actual recovered runtime copies, not only byte inspection.

Operations/risk skills required preserving exact source bindings, WAL compatibility,
UNKNOWN/attempts, baselines and halts. The Supabase skill kept the existing bounded
RPC and credentials boundary: no SDK, grants or schema changes. The official
[changelog](https://supabase.com/changelog) and
[function documentation](https://supabase.com/docs/guides/database/functions)
were checked; this increment reuses the already implemented read RPC, not a newly
inferred endpoint. The web reader rejected Markdown content types; direct HTTPS
reads supplied the docs. No hosted query was performed.

## Restored application oracle

The fresh non-editable wheel rehearsal first retains a worker UNKNOWN after a
loopback receiver accepted its batch and the client was SIGTERMed. One store is
observable in the independent receiver. The recovery CLI backs up all three
synthetic databases, then verifies/materializes them while originals are renamed
unavailable. Prior backup/inspection, independent-SQL and redaction checks remain.

Only inside the verifier's fresh private temporary root, recreate the original
fixture directories from verified inspection bytes, with private files and WAL
mode. Preserve original source-directory, owner, archive and destination identities;
no journal/config rebinding or init is used. Create an empty sync.lock only after
the original fixture worker has exited. Installed status reads UNKNOWN/attempts=1/
cursor=0; installed reconcile returns VERIFIED then NO_PENDING. Independent SQL
checks VERIFIED/attempts=1/cursor=1, and the receiver still records one store.
The original synthetic directories are restored afterward; recreated copies are
retained under separate fixture names until scoped temporary-directory cleanup.

A separate isolated installed interpreter opens the reconstructed command Journal
and ExecutionService with a query-only simulator whose send raises. Unavailable
and missing replies leave UNKNOWN and counts unchanged; exact then duplicate
replies yield one filled command/deal, the same order/position identifiers, one
original dispatch attempt, one exposure reservation and confirmed synthetic SL.
Independent SQL checks every risk-state field unchanged, with both halts still 1.
Four queries and zero new sends are asserted. This is simulator evidence only;
it is not an MT5 query, identity check or broker-side protection claim.

All inspection bytes are compared before/after activation rehearsal. Original
backup metadata stays unchanged; capture time is not advanced by restoration.
No owner database or existing UI/API process was touched. No auto activation tool
was added. Fencing stopped services, atomic target publication/mounts, actual broker
inventory/reconciliation, off-host/key custody, RPO/RTO and burn-in remain required.
Full Demo and unattended release remain NOT READY. Local safe development remains
possible without those target inputs; this evidence does not complete SCN-009.

## Verification

- `.venv/bin/pytest -q tests/test_sync_driver.py tests/test_sync_transport.py --tb=short`:
  133 PASS, 11.81s. Eighteen new cases cover exact/missing/partial/unavailable/conflict
  replies at attempts 1 and 5, repeated no-send calls, empty/prepared state,
  lock/target/source denial, CLI statuses/exits/flags. The final full runs also
  exercise the real-loopback SIGTERM test updated to use the reconcile command.
- `.venv/bin/ruff check services/worker/src tests/test_sync_driver.py tests/test_sync_transport.py scripts/check-worker-package.py tests/fixtures/recovery_query_probe.py`:
  PASS; Ruff formatting applied to the changed tests/verifier/fixture.
- `bash scripts/check-scn-001-local.sh`: final **586 PASS**, 35.41s, Ruff and secret
  scan PASS. No failed test was suppressed or assertion/timeout weakened.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS, `output/worker-package/d5eb00b64103417c81902addbeba76d3/result.json`,
  recorded 08:26:30.535705 UTC. Exact source/build metadata and byte-identical wheel
  rebuild, no development/source imports, locked dependencies, disabled defaults,
  query-only flags, installed recovery/reconstructed runtime and original restart.
- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS, `output/worker-container/sochron-worker-ab2a937c9ed0/result.json`,
  08:24:37.264569–08:25:20.820016 UTC; cleanup 0, synthetic key removed. This verifies
  installed image bytes/hardening and the existing container replacement workflow;
  the restored-path package rehearsal above runs on macOS, not this container.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  PASS, `output/compose/sochron-verify-6e645d3f443e/result.json`,
  08:24:39.475196–08:25:26.375800 UTC; cleanup 0.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-ab2a937c9ed0:candidate`:
  **563 PASS**, 19.64s; `output/container-python/sochron-python-839dfd95a06f/result.json`,
  08:26:43.891328–08:27:11.417750 UTC.
- Same command with `sochron-verify-6e645d3f443e-api:local`: **563 PASS**, 19.66s;
  `output/container-python/sochron-python-9c567ddba4a9/result.json`,
  08:26:45.048323–08:27:12.421995 UTC. Each excludes 23 workstation MT5 source
  scanner tests; there is no compiler/terminal evidence.
- Baseline, installed/pinned skills and `git diff --check`: PASS. Retained report
  input/artifact hashes were compared with current source and build contexts.
  Docker ps showed no running fixture containers after checks. Images/retained
  volumes were not broadly pruned. Fixture-only temporary data were cleaned.
- Full browser and real local Supabase/Auth/PostgREST suites were not rerun: no
  UI/Auth/schema/HTTP protocol changes. Driver/CLI, real loopback transport and
  both Linux runtime regressions were run; these do not establish hosted behavior.

Final tiny-fixture measurements: backup process 0.614416292s, verify 0.129179708s,
inspection restore 0.161288083s, subsequent reconstruction/application rehearsal
0.586434666s. These are separate measured intervals, not target RTO/RPO or capacity.
Capture interval remains 08:26:28.639395–08:26:28.650933 UTC on 2026-09-17.

## Candidate identities

| File | SHA-256 |
| --- | --- |
| sync_driver.py | `4e303089e5ffd5ac4bc18df76a4a424636ed5b64fdcdd35b89ca0655601d4fb7` |
| worker __main__.py | `026839ce29bcfc1c43ef3ed8702e7ab45a78aa2b766477b52ff14a9e264f626b` |
| check-worker-package.py | `079e0c061b6148d498dee7d021eba303368f6927925d2dbf24a7412492dbb102` |
| test_sync_driver.py | `435857afd6079bf7bc7eda6f71e97a1d1a5b39d34dfbb6c41a5c468badb11116` |
| test_sync_transport.py | `cbd4863685242cb9053bfe4d40e1cbe53c81808564bbc0a9d14b90e84eb14455` |
| recovery_query_probe.py | `ce9db563e43654d4a5ca40e2577e416ce13cbe97d3adb84a9463f81b0763cea2` |

- Wheel: `8137a15a55aec368dd77d44b793ab8a0f1f35aebfb8b1344c261653c4013b52e`.
- Sdist: `b79401569dd375998671b32b287b51ddc19521198742e76430513ea9c5d4770c`.
- Worker image: `sha256:4a5e933cbf042f91ab6236636795b60e34de0fd17c2e904c561c0a1d678c0889`.
- API image: `sha256:707e7b5cf96dd05cec2be50ee77213daced7737d5bf2d3be80bb126eb6b1363d`.

Full source/fixture/runtime identity is retained in the reports. Checksums do not
authenticate operator provenance, and passing synthetic checks is not target
deployment approval. Next execution work must complete startup admission and the
Demo executor/round-trip boundary without treating this sync read-back as broker
reconciliation or enabling Auto Trading.
