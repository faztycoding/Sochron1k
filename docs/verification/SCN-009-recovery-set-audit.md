# SCN-009 read-only recovery-set admission

2026-09-17, base `e99007a86f61565dee1ac6c026fbd308390f86c7` plus recorded dirty
candidate inputs. The containing commit identifies the delivered revision.
macOS 26.6.2 arm64; Python 3.14.7, SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8,
uv 0.12.15. Local Linux arm64: Docker 29.5.2, Compose 5.5.1; Python 3.14.7 and
admitted SQLite 3.53.4 with the same source/linkage probe as the prior release unit.

## Outcome and limits

AC-03's local read-only domain/cross-store admission is implemented and verified.
Command/risk, native archive and sync journal snapshots must match explicit expected
bindings, current schemas and a compatible contiguous M1 prefix. The result retains
UNKNOWN/quarantine/halts/budgets and always denies execution readiness. The inspector
does not open the original source directory, initialize databases, acquire writer
locks, change a binding, run a service or contact a destination.

This does **not** complete the whole recovery contract or Demo release. AC-04's
capture orchestration, recovery-set manifest, operator commands and measured
multi-store recovery remain pending. Actual broker/destination reconciliation,
target/off-host/encryption and owner-approved RPO/RTO are NOT RUN/NOT READY. No
owner database was inspected or changed. Existing UI/API and local Supabase were
not restarted. No hosted system, broker account, deployment or paid resource was used.

Only a new internal worker module and tests/docs were added. No existing runtime
entry point, policy, schema, dependency, migration or frontend behavior changed.
The shared Python artifact now includes 24 source modules; worker defaults still
disable operation without explicit configuration. The API image does not expose
an audit endpoint. Candidate-derived Linux test images add reviewed source and
locked development dependencies to verify runtime compatibility; they are not the
production artifacts and do not imply the API service ships a worker route.

## Independent oracles

78 targeted cases construct fixtures through actual Journal, BarHistory and
SyncJournal writers, then capture real SQLite snapshots. Generic snapshot
verification passes for deliberately corrupted-but-SQLite-valid cases before the
domain inspector rejects them. This distinguishes semantic checks from hashes.

- Compatible UNKNOWN + daily/total halt, exposure and attempts survive inspection
  and byte-identical isolated materialization. Input file fingerprints remain
  unchanged. Writer constructors and socket creation are patched to fail during
  inspection; a separate test admits only mode=ro snapshot connection URIs.
- PREPARED, VERIFIED, QUARANTINED and a five-attempt exhausted pending batch retain
  exact state/cursor/budget. No pending work is sent or relabelled to make it pass.
- Filled, partially filled, rejected and unprotected synthetic command evidence
  validates under the current one-order model. Altered quantities, missing deals,
  missing position ID, inconsistent SL flag, missing exposure/attempt/baseline,
  bad fingerprint/transition/sequence, nonfinite values and schema drift fail.
- All four archive timeframes and later source suffixes validate. Invalid closure,
  offset/grid/receipt/projection/build/clock evidence fails. An older archive's
  content recaptured with a fresh snapshot timestamp still fails when it cannot
  satisfy the pending second batch. This is a domain test, not merely an age test.
- A ledger whose payload/digest are recomputed after omitting the first source row
  fails despite all retained rows individually existing in the archive. Every
  batch must consume the exact source prefix, not an arbitrary matching subset.
- Wrong owner/archive/origin/original-path/experiment/config, stale or future
  intervals, wrong capture order, excessive span, naive clock, boolean limits,
  resource/deadline excess and changed output at final reverification are denied.
- Empty command/sync journals are admitted only with an explicit retained active
  risk baseline; unsynced archive rows do not imply a completed synchronization.

Tests initially caught two fixture mistakes: audit time was sampled before the
fixtures captured snapshots, and the generic command fixture symbol did not match
the chart fixture symbol. The fixtures now sample after capture and use the exact
expected identity/symbol. No production rule or negative assertion was removed.

Staged review found a real gap: transition continuity alone admitted a dispatched
command rewound into CREATED, VALIDATED or QUEUED. Three regression cases failed
with DID NOT RAISE before the fix. The inspector now rejects all three after the
initial atomic reservation chain. Targeted, full, package and both container/runtime
checks below were rerun on the fixed candidate; earlier 75/539/516-test results
are not used as final candidate evidence. This changes recovery admission only,
not the underlying journal writer or execution state machine.

Historical rows are not fresh MT5 truth. A causal-prefix set is not an atomic
cross-database instant. Hashes are not signatures; no claim is made to detect a
self-consistent malicious rewrite of both data and trusted metadata, or prove an
earlier halt from a single later snapshot. No power-loss or hard kernel-I/O deadline
claim is made. See [ADR-014](../decisions/ADR-014-recovery-set-admission.md) for
schema/admission bounds and [runbook](../operations/recovery-set-audit.md).

## Exact commands and evidence

- `.venv/bin/ruff format services/worker/src/sochron_worker/recovery_audit.py tests/test_recovery_audit.py`:
  formatted the two new files.
- `.venv/bin/ruff check services/worker/src/sochron_worker/recovery_audit.py tests/test_recovery_audit.py`:
  PASS; two initial long SQL lines were split before verification.
- `.venv/bin/pytest -q tests/test_recovery_audit.py --tb=short`: **78 PASS**, 12.28s.
- `bash scripts/check-scn-001-local.sh`: **542 PASS**, 31.95s; Ruff and secret scan PASS.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS; exact artifact source bytes, byte-identical rebuild, clean non-editable
  install and disabled/UNKNOWN/restart CLI regression groups.
  `output/worker-package/ce8ad1909a4741aaa8829e9363766f12/result.json`,
  recorded 07:51:06.115745 UTC.
- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS; hardening, fixed SQLite admission, installed artifact, init/writer denial,
  SIGTERM UNKNOWN and replacement read-back without resend. Evidence:
  `output/worker-container/sochron-worker-971801293216/result.json`,
  07:51:00.454044–07:51:40.834496 UTC; cleanup 0, synthetic key removed.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  PASS; isolated API/web build, hardening, fixed SQLite probe, Demo/auto-off health
  and journal volume across replacement. Evidence:
  `output/compose/sochron-verify-276074dfc4b5/result.json`,
  07:51:01.467718–07:51:46.038349 UTC; cleanup 0.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-971801293216:candidate`:
  **519 PASS**, 15.40s; `output/container-python/sochron-python-33167d4df736/result.json`,
  completed 07:52:31.852882 UTC.
- Same container command with `sochron-verify-276074dfc4b5-api:local`: **519 PASS**,
  15.39s; `output/container-python/sochron-python-4a5cb838d832/result.json`,
  completed 07:52:32.346340 UTC.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`,
  `python3 scripts/check-no-secrets.py` and `git diff --check`: PASS.

The 23 MT5 source-static checks excluded from Linux runtime suites passed on the
workstation. Actual MQL5 compilation and target-host tests were not run. No full
authenticated browser or real Supabase integration rerun was needed for this new
offline library; those boundaries are unchanged, and no new integration acceptance
is inferred. The uv path is this workstation's tool location, not a portable setup
requirement. All test containers were removed; Docker ps showed none remaining
in the dedicated local engine. Scoped synthetic images/volumes/evidence remain.

## Artifact and input identities

SHA-256:

| Item | SHA-256 |
| --- | --- |
| Recovery audit module | `37d00ea1e32438d54c9e73556510496d453adb4dd4019b313688db777161c6a9` |
| Recovery audit tests | `65d4425f330458fc665671ec1cf31652423ab2005df519efb3faf0381f761c33` |
| Wheel | `fa70620ef6175f9f4b16dea8b03b00d47211daa4ba6a15676c86fe3328c6000f` |
| sdist | `f8e449f1bfa60663ea88dcbbbe9ff73ba15e611a2cd045ff0c4ed478a0e302d9` |
| Worker candidate image | `9d1d3296e57fa261fc43b35b2710f2073215030a903f4d0ae115ed3a7bd61819` |
| API candidate image | `b7329009479d34881a9f8c191f5b8a1d933a4dd20267468696677f3f4cca6ea9` |

Both Linux reports retain matching module/test hashes and full candidate/test-image,
verifier, fixture and locked-input identities. The package report verifies all
module bytes, including the new inspector. No code/build/fixture changed after the
successful runs; only documentation followed. Outputs are ignored local artifacts;
source, tests and evidence report are committed.

The [risk/recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md) guided
baseline, halt, UNKNOWN and exact relationship preservation. The
[operations skill](../../tooling/skills/sochron-vps-operations/SKILL.md) guided isolated
inspection and the explicit separation between admission, restoration and resumption.
Next safe work: recovery-set capture/materialization and operator CLI with measured
local rehearsal, before separately authorized target/off-host/external gates.
