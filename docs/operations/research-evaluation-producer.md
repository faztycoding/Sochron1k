# Reproducible research evaluation producer

## Purpose and boundary

`sochron-research-evaluation` validates one immutable labelled-trade bundle,
computes the SCN-017 metrics and can publish exactly one owner-scoped Supabase
evaluation. It is disabled unless `SOCHRON_RESEARCH_EVALUATION_CONFIG_FILE`
names an owner-private configuration file.

This operator does not turn bars into trades, resolve ambiguous OHLC paths,
choose cost assumptions, promote a strategy or operate MT5. A passing synthetic
run proves the calculation/publication path only. The Statistics UI remains
`awaiting_source` until a separately validated non-synthetic bundle is published.

## Data path and UI position

```text
labelled setup-to-flat bundle
  -> pure evaluator
  -> private research-evaluation.sqlite3
  -> backend-only Supabase RPC
  -> owner-RLS evaluations
  -> FastAPI GET /owner/statistics
  -> browser GET /api/owner/statistics
  -> UI #research-statistics
```

The UI panel is after `#signal-evidence` and before `#bar-history`. No service key,
owner UUID, database key or input-file path reaches the browser.

## Required input

The canonical `sochron.research-bundle.v1` JSON is the retained research artifact.
It contains:

- exact dataset and strategy code hashes;
- one train/validation/test/walk-forward/shadow-Demo window and embargo evidence;
- fixed spread, slippage, commission, swap and operating-cost assumptions;
- closed setup-to-flat records with gross P/L, initial risk, volume and point value;
- explicit WAIT, rejected, counterfactual and ambiguous records that remain excluded
  from performance metrics;
- a UTC mark-to-market equity path that names every open setup.

The `dataset_hash` is SHA-256 over canonical JSON after removing only the
`dataset_hash` field. Decimal values are strings, integer fields are JSON integers,
keys are sorted and separators are `,` and `:` without whitespace. The producer
rejects a pretty-printed, noncanonical or mismatched file. An upstream labeller or
backtest must create this artifact; editing a completed bundle is a new dataset.

## Private configuration

Create separate owner-only paths (directories mode `0700`, files mode `0600`). The
state directory must exist and be empty for `init`.

```json
{"enabled":true,"experiment_id":123,"input_file":"/absolute/private/research/bundle.json","origin":"https://PROJECT.supabase.co","owner_id":"00000000-0000-4000-8000-000000000000","service_key_file":"/absolute/private/secrets/supabase-service.key","state_directory":"/absolute/private/state/research-evaluation","strategy_version_id":456}
```

`experiment_id` may be `null` for an offline evaluation. The numeric strategy and
experiment IDs must already belong to the configured owner; the stored strategy
version and 64-hex code hash must match the bundle. Put only the config-file path in
the environment:

```bash
export SOCHRON_RESEARCH_EVALUATION_CONFIG_FILE=/absolute/private/config/research-evaluation.json
```

Do not put the service key in the config, environment example, repository or UI.
No hosted write is authorized merely by preparing these files.

## Operator sequence

Use the installed artifact, not a source-relative Python command:

```bash
sochron-research-evaluation init
sochron-research-evaluation status
sochron-research-evaluation publish
sochron-research-evaluation reconcile
```

- `init` validates and evaluates the bundle, creates the private journal and
  durably records `PREPARED`; it makes no network request.
- `publish` changes the journal to `UNKNOWN` before its one bounded RPC send, then
  performs an independent exact read-back.
- `reconcile` is read-only and is the required next action after `UNKNOWN`.
- `VERIFIED` means the exact row was read back. It does not mean promoted,
  profitable, execution-ready or Demo-release-ready.
- `QUARANTINED`, journal errors and send-budget exhaustion require evidence review;
  do not delete state and retry under a new identity.

## Local verification

```bash
.venv/bin/python -m pytest tests/test_research_evaluation_producer.py -q
npx -y -p node@24.21.0 npm run check:db:static
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:db:local
.venv/bin/python scripts/check-worker-package.py
```

The database check requires the guarded local Supabase stack. The package check
requires pinned `uv==0.12.15`. Neither command authorizes a hosted write or proves
market-data/fill validity.
