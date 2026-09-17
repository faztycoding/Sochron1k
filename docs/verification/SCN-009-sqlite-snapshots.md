# SCN-009 AC-01/02 SQLite snapshot engine

2026-09-17; base `e369e29feea66d183a1ab31a3272f7d70879ce43` plus recorded dirty
candidate inputs. The containing commit identifies the final source. macOS 26.6.2
arm64, Python 3.14.7, workstation SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8,
uv 0.12.15. Linux arm64 images load the separately pinned/verified SQLite 3.53.4;
Docker 29.5.2 and Compose 5.5.1. No tested code, fixture or build input changed
after the final successful runs; subsequent edits only document results.

## Outcome and acceptance limits

AC-01/02: PASS for the internal individual-database engine on these local
environments. New snapshots include committed WAL data, reject incomplete or
changed outputs and materialize only into a new private inspection directory.
AC-03 domain/multi-store admission and AC-04 operator delivery: NOT IMPLEMENTED,
NOT RUN. Full Demo remains NOT READY. This is not a complete backup/recovery
workflow, RPO/RTO approval, target-host admission, off-host backup, encryption,
Supabase export, raw-tick retention or MT5 reconciliation evidence.

The only application addition is `sochron1k.sqlite_snapshot`; existing API/worker
entry points and policies are unchanged. It imports only the standard library,
does not instantiate execution services, and has no network, CLI, scheduler,
in-place restore, initialization, rebinding or halt-release path. Every accepted
manifest has `execution_ready=false`. See [ADR-013](../decisions/ADR-013-private-sqlite-snapshots.md)
and [development runbook](../operations/sqlite-snapshots.md).

## Oracles and failures

The 31 targeted cases use real private temporary SQLite files, not mocked backup
results. A WAL writer stays open with auto-checkpoint disabled; an uncommitted row
is excluded while the committed row is restored. A separate connection commits
during a multi-page backup; the pinned snapshot retains the earlier row count.
Materialized bytes match the snapshot hash and preserve its original UTC interval.

Independent SQL queries on an isolated synthetic command-journal copy retain
UNKNOWN, its dispatch attempt and exposure reservation, exact risk baselines,
daily halt and total halt. No execution service is started to read this copy.
This fixture checks preservation, not arbitrary command-domain validity or
cross-database compatibility; those remain AC-03 work.

Negative cases deny unsafe modes, symlinks/hardlinks, missing sources, preexisting
targets, nested materialization into the source snapshot, size/deadline excess,
corrupt DB, foreign-key violation, failed fsync, extra files, modified bytes,
duplicate JSON keys and malformed metadata. Existing target marker files remain
unchanged. A child exits with code 73 before manifest publication: its DB exists,
but verification rejects it. A final directory-fsync failure leaves an INCOMPLETE
marker and is rejected. No test/gate was relaxed. Earlier fixture errors (missing
RiskState updated_at and uppercase expectation for the lowercase UNKNOWN enum)
were corrected before these final runs.

Checksums are not signatures; an attacker controlling the private directory and
manifest is outside the integrity claim. The 30-second deadline is cooperative,
not a kernel-I/O timeout. Limits apply to each DB/sidecar, not the whole filesystem.
Process-exit and fsync-failure tests do not prove power-loss durability. A snapshot
is not proof that commands, archive and sync cursor form one recovery transaction.

## Exact checks and retained evidence

- `.venv/bin/pytest -q tests/test_sqlite_snapshot.py`: **31 PASS**, 0.45s.
- `bash scripts/check-scn-001-local.sh`: **464 PASS**, 20.83s; Ruff and secret scan PASS.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS; exact 23 module files, byte-identical wheel rebuild, clean non-editable
  installation, disabled CLI default and UNKNOWN/restart without resend.
  `output/worker-package/73c4040200b3424daf5d4876944139a0/result.json`,
  recorded 07:24:57.820115 UTC.
- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS; hardening/runtime probe, private init, competing writer denial, SIGTERM
  UNKNOWN, independent replacement read-back without resend, unsafe config denial.
  `output/worker-container/sochron-worker-12b036d097ad/result.json`,
  07:24:53.113955–07:25:32.512376 UTC; cleanup exit 0, generated key removed.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  PASS; fixed SQLite probe, hardened API/web, Demo/auto-off health and volume
  preservation across replacement. `output/compose/sochron-verify-907a83fd74a2/result.json`,
  07:24:53.844141–07:25:38.188097 UTC; cleanup exit 0.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-12b036d097ad:candidate`:
  **441 PASS**, 14.47s; `output/container-python/sochron-python-285e40c1ba90/result.json`,
  completed 07:26:25.127911 UTC.
- Same container Python command with `sochron-verify-907a83fd74a2-api:local`:
  **441 PASS**, 14.39s; `output/container-python/sochron-python-a5f6bd0e193a/result.json`,
  completed 07:26:25.237992 UTC.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`,
  `python3 scripts/check-no-secrets.py` and `git diff --check`: PASS.

Linux runtime suites exclude the 23 MT5 source-static checks included in the
464-test workstation suite. No actual MetaEditor compilation is claimed. Linux
test images add locked dev dependencies and exact reviewed source/fixtures to the
candidate runtime; they are not production artifacts. Both candidate and derived
images must pass the same loaded-SQLite probe. The uv path above is a verified
workstation tool location, not a portable deployment path.

## Exact identities

SHA-256 values:

| Input/artifact | SHA-256 |
| --- | --- |
| Snapshot module | `5a3bb18dc237e49d97499b055fe2960165f9aeecc8ffde20273864ae86c56e00` |
| Snapshot tests | `7a063573e428078e0248bf945666badbb8fd19e37036b8fdd45238204a88c9e9` |
| Wheel | `9bfa0c1634762361e3f0f5a2186927b7a55af22d8830c3de5669a8144ebbfce9` |
| sdist | `0a7873957a5224494e3c99e5ccdba4848110a48aa5e7d1b685536e01449a4a97` |
| Worker candidate image | `7c3a2670b2f063279480d0e282dc958d1381b2cd17b701061d7e34ffd3d580a5` |
| API candidate image | `2a7b1e078b8814d25177476ea57ad2bfa668cb7962d5f4e11e48aad5ae7e7c82` |

Result manifests retain full source/build/verifier/fixture identities. Both Linux
reports carry the same snapshot module and test hashes above. Evidence outputs
are ignored local artifacts; source, tests, contract and this report are committed.
All test containers were removed; no running containers remained in the dedicated
local engine after verification. Retained synthetic volumes/images/logs are not
owner data. Existing UI/API processes and local Supabase were not restarted, and
no broker, hosted service, user database or deployment was operated.

Frontend/authenticated browser and real Supabase integration were not rerun: no
UI/Auth/migration/transport behavior changed. Target/off-host/operator recovery
tests were not run and are not inferred from generic snapshot tests.

The [operations skill](../../tooling/skills/sochron-vps-operations/SKILL.md) guided
WAL-aware backup and isolated output/artifact identity; the
[risk/recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md) guided
UNKNOWN/halts preservation and explicit separation from resumption authority.
Next: compatible domain-validated recovery sets, operator commands and measured
local recovery; then separately approved target/off-host/reconciliation gates.
