# SCN-011 durable position management and halt response

2026-09-20; base `17405ed51e3979e83608476923f89b8d49f14512`, dirty
candidate inputs. The containing commit identifies delivery; retained reports bind
the precommit base to exact input hashes. macOS 26.6.2 arm64, Python 3.14.7,
SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8 and uv 0.12.15. Local Docker 29.5.2 /
Compose 5.5.1; Linux arm64 Python 3.14.7 and source/linkage-admitted SQLite 3.53.4.

## Outcome and acceptance status

The local execution boundary now has separately idempotent durable cancel and close
commands bound to an existing entry. Requested management volume comes from the
journal's broker evidence. A partial entry must cancel its pending remainder before
close; exposure stays reserved through UNKNOWN and partial close. Management remains
available after deterministic daily/total halt latching, while new entries remain
denied and no halt-release operation exists.

Management intent, attempt, cumulative outcome and exit deals are journaled in
additive WAL tables. Invalid, regressing, foreign or reordered evidence is handled
transactionally. Deal ordering is insignificant but identity, volume and financial
fields cannot change or disappear. Any ordinary exception after adapter invocation
persists UNKNOWN and clears startup admission; query-only reconciliation performs no
resend. Startup now inventories active management and requires fresh exact evidence.

A final local audit is emitted only after full close with no active exposure or
management command. It contains entry/exit tickets, exact volumes, gross profit,
commission, swap, fee, net PnL and close reason. Recovery-domain inspection admits
the new exact schema signature
`bf15fe71e298eb12dcab1c08e51c62e4a59324a5e9fe0a67fd4667084f063a8d`
and rejects corrupted management financial evidence.

SCN-011 AC-01 through AC-10 pass for the local simulator and installed artefact
scope. This does not pass SCN-001 AC-07: no MQL5 mutation adapter, MetaEditor build,
Demo account operation, HTTP/UI control, automatic risk-loop dispatcher, target-host
recovery, broker fee/account-mode behavior or owner-authorized round trip was run.
Public `execution_ready` and `auto_trading_enabled` remain false; release is
NOT READY.

## Failing-first and negative evidence

The first targeted run failed during collection because the management journal
interface did not exist:

```text
.venv/bin/pytest -q tests/test_position_management.py --tb=short
ImportError: cannot import name 'ManagementConflict'
1 error in 0.17s
```

Negative coverage includes close-before-cancel, cancel/close with no applicable
volume, changed idempotent payload, concurrent management reservation and concurrent
halt escalation, partial close, timeout after broker effect, malformed/wrong-target
response, journal failure after invocation, restart with missing management
inventory, unordered cumulative entry deals, missing financial evidence, regressing
broker observation time, wrong evidence rollback, latched halts, incomplete final
audit and recovery corruption. No assertion, gate or timeout was weakened.

The first installed-wheel run reached the startup oracle and failed because the new
probe asserted a nonexistent aggregate key. A direct diagnostic exposed
`KeyError: management_unresolved`; the oracle was corrected to query durable
unresolved IDs and the entire isolated verifier then passed.

The first two Linux suites were started simultaneously. The worker image passed;
the API run retained one snapshot failure and 657 passes in
`output/container-python/sochron-python-03d3b97674a6/pytest.log`. The failure was
`test_snapshot_time_admission[naive]` while creating a private snapshot under the
parallel load, before the time assertion. The exact unchanged API image was rerun
alone and all 658 tests passed. The parallel failure remains recorded rather than
being relabelled PASS. Final candidate Linux suites were then run sequentially and
both passed 664 tests.

## Verification

- `.venv/bin/pytest -q tests/test_execution_service.py tests/test_execution_startup.py tests/test_position_management.py tests/test_recovery_audit.py tests/test_sqlite_snapshot.py tests/test_recovery_bundle.py --tb=short`:
  **247 passed** in 13.62s.
- `bash scripts/check-scn-001-local.sh`: **687 passed** in 35.98s; Ruff and
  repository secret scan passed over 1,318 text files on host Python 3.14.7.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS; `output/worker-package/9a8a188d79214041b62e8b0054f4fb03/result.json`,
  recorded 2026-09-19 20:14:23 UTC. A fresh non-editable wheel performed one entry
  send and one close mutation, preserved halt state, persisted UNKNOWN after close
  response loss, reconciled by query without resend, emitted final net PnL `0` and
  kept both release flags false. Wheel SHA-256:
  `1a0ba949e8fdc6b7f15ca0e8f7f093a7cf210c80d329f28dac95686dbd652ec3`.
- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS; `output/worker-container/sochron-worker-c8cad72d7fbb/result.json`,
  20:14:30–20:15:10 UTC. Candidate image
  `sha256:8ac7695bb2584a943ec34c412f542b1a28ff84d940b5730b15996a54f98f65e7`;
  cleanup 0 and release_ready=false.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  PASS; `output/compose/sochron-verify-c7ba33daf148/result.json`,
  20:14:31–20:15:15 UTC. API image
  `sha256:6479c31065253489773bbf93ccfd3357ff5270f9ab4d5c988c6b88d4c79ad7bb`;
  cleanup 0.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-c8cad72d7fbb:candidate`:
  **664 passed** in 20.68s;
  `output/container-python/sochron-python-2f0afad36525/result.json`.
- The same verifier with `sochron-verify-c7ba33daf148-api:local`, run sequentially:
  **664 passed** in 20.61s;
  `output/container-python/sochron-python-dec6dd309daf/result.json`.

The Linux suites exclude the 23 workstation-only MQL5 source-scanner tests. Package,
container and Compose evidence use generated local fixtures with no hosted or broker
access. Baseline, skill-lock, final secret and diff checks are recorded after this
report in the containing delivery.

## Candidate identities

| File | SHA-256 |
| --- | --- |
| `executor.py` | `d4cfa308e10e343381c8218801a2ba1296680dae8179bcb101228172e346f40d` |
| `models.py` | `974de7994fd524ebf50e2ec995352c4df07ae98a06fc6df6f63109dd603c265b` |
| `journal.py` | `c3766f77079a57c5ad724223e7bcd5b647f539cd0148400dcf1ff70a148400a2` |
| `service.py` | `90f1cddecff101905a0b70256a29bff87ca3633ef03fdb1f3df990f02d39002b` |
| `simulator.py` | `97407abf1738ade52a2e579e04a90960896062dd7e6387d41aced007a250c26c` |
| `startup.py` | `52fbb69cd345092c9767c57bc15be6737989378d647015aa397edb085351404b` |
| `recovery_audit.py` | `6ad61cc6d5d364baba229d30c49ed888f94eb84513bf89c4b89ad0524cb1455e` |
| `test_position_management.py` | `5dfa69e250ea879f943850f7224bf2f7f5ee6c8081700fc592f4c733146bb4e9` |
| `test_recovery_audit.py` | `d58eea232bfad8f08e8536f64b91bffe0d176d4674c77a2768ae67f5771732f6` |
| `execution_startup_probe.py` | `186366ced92e5d97fe4f8e4121f459e670b8dce0ab0d664fd5d686c8368f9043` |
| `check-worker-package.py` | `4275ad75795db53746a9264f75667ff931cd39e306fa537c270c9e81e3a35ccc` |

Passing synthetic checks do not authorize MT5. The next safe execution increment is
the authenticated, exclusively owned Demo MT5 inventory and management adapter with
complete order/deal/position/SL recovery, after the owner records the exact broker,
server, account mode and symbol contract inputs.
