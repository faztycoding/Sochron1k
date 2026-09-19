# SCN-012 authenticated Demo execution polling bridge

2026-09-20; base `201e05bbb85f32dfea7c264c67143ebbb46f750d`, dirty
candidate inputs. The containing commit identifies delivery; retained reports bind
the precommit base to exact input hashes. macOS 26.6.2 arm64, Python 3.14.7,
SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8 and uv 0.12.15. Local Docker 29.5.2 /
Compose 5.5.1; Linux arm64 Python 3.14.7 and source/linkage-admitted SQLite 3.53.4.

## Outcome and acceptance status

The API now has an opt-in single-executor adapter for one future MT5 Demo EA. A
separate private credential, fixed Demo identity and magic number, API boot fence,
executor generation, fresh complete inventory, monotonic sequence/time and one
active command fence constrain the transport. Missing configuration returns a
disabled state. Public health still reports `execution_ready=false` and
`auto_trading_enabled=false`; no owner/browser mutation route exists.

Entry, cancel and close dispatches are derived only after the existing service has
journaled the command and attempt. Polling claims and then repeats the exact same
dispatch. Unclaimed timeout withdraws transport delivery; claimed timeout retains
the dispatch for late outcome/query reconciliation and never creates a replacement.
Outcome boot, sequence, attempt, generation, command, target and operation are all
bound. Exact replay is idempotent; changed replay and malformed/foreign evidence
fail closed.

A separate `ExecutorRejection` records reviewed no-effect broker return codes,
external code, request ID and UTC time without inventing order/deal/position IDs or
retaining raw broker comments. Timeout, disconnect, in-flight, success and
already-mutated-state return codes cannot be terminal rejection. Entry rejection
releases exposure only after durable validation. Rejected management keeps the
parent exposure and restores rejected close from `CLOSING` to the retained snapshot
state. Fresh complete startup inventory can resolve either kind after restart.

The exact command schema signature is now
`66bd1ddfbe98c0556fa66180aa0fd676e460d8ccf3187ef50e132a93cf4cd7d8`.
The read-only recovery inspector verifies rejection binding, attempt, transition,
retcode, time, exposure and absence of conflicting broker evidence; a corrupted
timeout-as-rejection fixture is denied.

SCN-012 AC-01 through AC-10 pass for the local API/simulator/recovery and installed
artifact scope. This does not pass SCN-001 AC-07: no MQL5 mutation consumer,
MetaEditor build, actual Demo identity/inventory, target network/TLS, broker action,
terminal restart or owner-authorized open-to-close round trip was run. Release is
`NOT READY` and Auto Trading remains off.

## Failing-first and negative evidence

The first rejection test run failed during collection because the typed exception
did not exist:

```text
.venv/bin/python -m pytest -q tests/test_executor_rejection.py
ImportError: cannot import name 'ExecutorRejected' from 'sochron1k.executor'
1 error in 0.14s
```

The first polling test likewise failed because the bridge module did not exist:

```text
.venv/bin/python -m pytest -q tests/test_execution_bridge.py
ModuleNotFoundError: No module named 'sochron1k.execution_bridge'
1 error in 0.15s
```

Negative fixtures cover missing/insecure/symlinked config, shared telemetry token,
anonymous access, duplicate JSON keys, oversized input, changed sequence replay,
generation change during an active dispatch, a latched protocol rejection, unclaimed
and claimed timeout, exact and conflicting outcome replay, uncertain return code,
typed no-ticket rejection, stale immediate rejection, historical rejection recovery,
cross-type command-ID reuse, entry and close restart recovery, immutable rejection
evidence and recovery-table corruption. Existing duplicate, stale, wrong-target,
halt, management and recovery tests continued to pass. No assertion, gate or timeout
was weakened.

The first package-verifier invocation stopped before a build because uv 0.12.15 was
not on PATH. A pinned disposable `/tmp` environment was created and the unchanged
candidate passed. The first Python-container invocation used the Compose image ID as
a Dockerfile `FROM`; BuildKit treated the bare `sha256:` value as a registry name and
denied it. The same local image was rerun by its exact local tag and passed. Both
failed attempts remain retained; neither is relabelled as product evidence.

## Verification

- `.venv/bin/python -m pytest -q tests/test_execution_bridge.py tests/test_executor_rejection.py tests/test_execution_startup.py tests/test_position_management.py tests/test_recovery_audit.py`:
  **218 passed** in 9.10s.
- `bash scripts/check-scn-001-local.sh`: Ruff passed, **726 passed** in 34.09s,
  and the repository secret scan passed over 1,770 text files on Python 3.14.7.
- `python3 scripts/check-agent-skills.py`: all recorded general and four Sochron
  skills passed installed/source integrity checks.
- `SOCHRON_UV=/tmp/sochron-uv.pLqxNq/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS; `output/worker-package/298140246ac1473686f804e50afeb00d/result.json`,
  recorded 2026-09-19 21:09:36 UTC. Wheel SHA-256
  `853111a8de08200c8dfbdd8e5e61ffc34d3a69d48d969b52bb59920d15644195`;
  hosted, MT5 and deployment remain NOT RUN.
- `SOCHRON_UV=/tmp/sochron-uv.pLqxNq/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS; `output/worker-container/sochron-worker-8cc99044c6c4/result.json`,
  21:10:24–21:10:54 UTC; candidate
  `sha256:aa68fee50057a810b31a901fb28d989b7d1f4bc4501020918a8283cc39ba92ae`,
  cleanup 0 and release_ready=false.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  PASS; `output/compose/sochron-verify-44d64f4d3577/result.json`,
  21:09:42–21:10:19 UTC. API image
  `sha256:dea44056c82e877f77afb02f17c3481c4557b2109fb70e21fa613819194cd0ec`;
  cleanup 0.
- `SOCHRON_UV=/tmp/sochron-uv.pLqxNq/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-verify-44d64f4d3577-api:local`:
  **703 passed** in 16.96s;
  `output/container-python/sochron-python-f6fa2b28bffa/result.json`.
- `npx -y -p node@24.21.0 npm run check:web`: 7 files / **132 tests passed**,
  production build and client-bundle scan passed.
- Project baseline, static Compose and static Supabase guards passed. All use local
  generated fixtures; no hosted, broker or paid resource was accessed.

The Linux suite excludes 23 workstation-only MQL5 source-scanner tests. Compose and
package reports identify dirty precommit inputs by exact hashes; the containing Git
commit and remote confirmation provide the final revision identity.

## Candidate identities

| File | SHA-256 |
| --- | --- |
| `execution_bridge.py` | `350017b489de029504b601d2bdc39e2f324fb12bdd6e6cbc44b796f66ce19343` |
| `execution_bridge_api.py` | `63901c6acd43218474000db908de0f2101d3a5f09ab7faa1c506e6d15fbf29e6` |
| `executor.py` | `59e59a5e6d95084ab5ffcb0a1a414b247b45b9a5cf194daabceb13e23755d7fe` |
| `models.py` | `28c0d54cd5f81c8f6d7ac8e0808d2c3fc4c196ed5c1371a8caa5ea87c576772f` |
| `journal.py` | `7255c7b3abdc4ffcca6e67072bb94ccf0facabb0ea742eb7dec7dd51a8b96d52` |
| `service.py` | `71f211d70bd0b59206c8eaa4e4b541246b50f517b076745ee84b2f470b2f744d` |
| `startup.py` | `498d24ae046c65d12fdf8041f8fc86cc6e1d3efb427c9bdacd5a80110c2002ac` |
| `recovery_audit.py` | `b08459555ae8bad403db6cef8c7990f75413a03a2ad4eee90bf4367a921364fe` |
| `test_execution_bridge.py` | `a14dde21794ef77ef2f0f74a9ddcd6b129d8e028914bf37a4e6a305063e71b4b` |
| `test_executor_rejection.py` | `0d5c98b89545d4dfea45470e8293e34909120277c85aa1e6e4fe86e1d7ee5445` |
| `test_recovery_audit.py` | `6292b916a0f133e02c4aad49a8bcbc4e764bf65b51cc7e4dd1d3f640daa54bfd` |

Passing synthetic checks do not authorize MT5. The next safe increment is the
default-off MQL5 Demo execution consumer that performs mutation-boundary identity
checks, local idempotency, `OrderCheck`/`OrderSend`, transaction reconciliation and
cumulative inventory/outcome reporting, followed by MetaEditor and target-host
verification after the missing owner/broker inputs are recorded.
