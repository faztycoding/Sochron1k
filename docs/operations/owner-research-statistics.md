# Owner research statistics operations

## Purpose and route

The owner workspace reads versioned evaluation evidence through browser route
`/api/owner/statistics` (FastAPI `/owner/statistics`). It is Demo-only and
read-only. A successful response is not a promotion, execution or profitability
decision.

## Runtime dependencies

1. Configure owner Auth exactly as described in
   [owner authentication](owner-authentication.md).
2. Apply the existing Supabase migrations. `evaluations`, `strategy_versions` and
   `experiments` must retain their authenticated SELECT grants, forced RLS and
   owner policies.
3. The optional SCN-029 producer must receive a separately validated canonical
   labelled-trade bundle and publish a conforming evaluation. See the
   [research evaluation producer](research-evaluation-producer.md).

Without Auth configuration the connection map reports `awaiting_configuration`.
With Auth but no rows it reports `awaiting_source`, and the owner panel states that
it is waiting for research evidence. The producer software existing does not make
a dataset available. Neither state is a failure or permission to fabricate metrics.

## Accepted evidence

Each evaluation must have a 64-hex dataset hash, explicit split and data cutoff,
strategy version/code hash, exact outcome counts, expectancy plus 95% interval,
net return, maximum drawdown and profit factor. Cost evidence must include spread,
slippage, commission, swap inclusion, per-trade operating cost and currency.
Sample size must equal wins plus losses plus breakeven.

The API derives win rate from those counts and displays no raw JSON. A `train`
split is always labelled in-sample. Results from different splits remain separate.

## Local verification

Start the guarded local stack, run the database and browser checks, then stop it:

```bash
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh start
SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:db:local
env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh stop
```

The browser verifier creates two disposable local Auth users, inserts isolated
synthetic evaluations using the local service-role key inside the verifier only,
proves direct RLS isolation, verifies the owner API/UI and deletes the rows/users.
It does not contact hosted Supabase or MT5.

## Failure behavior

- `401`/`403`: clear private values and reauthenticate; do not retain the prior
  evaluation on screen.
- `503 STATISTICS_UNAVAILABLE`: keep the panel degraded, redact upstream details
  and retry only the read.
- Malformed metrics, mixed owners, future cutoff, duplicate identity, excess rows
  or oversized payload: fail the whole read; do not show a partial subset.
- Missing producer evidence: remain `awaiting_source`; do not substitute zeroes.
