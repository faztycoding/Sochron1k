# Owner execution evidence

This runbook configures the read-only SCN-015 owner projection. It does not start
ExecutionService, connect MT5, send a command, clear a halt or make Demo execution
ready.

## UI and API location

- UI: authenticated owner workspace, below chart and closed-bar history.
- Browser route: `GET /api/owner/execution`.
- FastAPI route: `GET /owner/execution`.
- Public integration status: the `execution_evidence` row of
  `GET /api/ui/connections`.

The UI displays Command, Order, Deal, Position, cumulative volume, rejection and
broker-side SL evidence only when those records exist in the journal. It contains
no order, retry, halt-release or Auto Trading control.

## Default-off configuration

Leave `SOCHRON_EXECUTION_JOURNAL_PATH` unset to return the authenticated disabled
view. To enable reads, point it to the canonical absolute path of an **existing**
ExecutionService SQLite journal. The API never creates a missing file.

The journal and its parent directory must be owned by the API operating-system
user. The directory must deny group/world access; the database and any `-wal` or
`-shm` sidecars must be regular, single-link files that deny group/world access.
The execution writer and API reader must refer to the same mounted file identity.

Example target value (location only, not a credential):

```text
SOCHRON_EXECUTION_JOURNAL_PATH=/app/data/commands.sqlite3
```

Do not set this example until a separately admitted ExecutionService owns that
journal. The current default Compose application has no execution writer and does
not set the variable.

## Expected states

| Owner view | Meaning | Safe action |
| --- | --- | --- |
| `disabled / not_configured` | API contract exists; no journal path loaded | Provision the writer and reviewed private mount first |
| `available` | A bounded, validated journal projection was read | Treat records as local evidence; MT5 remains authoritative |
| `unavailable / source_unavailable` | Identity, permissions, SQLite integrity, schema or stored evidence failed validation | Stop relying on the projection; inspect writer/storage without replacing or repairing from the API |

`available` is not execution readiness. `/health` remains Demo-only with Auto
Trading off and `execution_ready=false`.

## Verification

```bash
.venv/bin/python -m pytest -q tests/test_execution_evidence.py
npx -y -p node@24.21.0 npm run check:web
bash scripts/check-scn-001-local.sh
```

Tests use synthetic journals. No test result in this runbook proves an MT5 fill,
close, cancellation, broker-side SL, target-host filesystem or Demo round trip.
