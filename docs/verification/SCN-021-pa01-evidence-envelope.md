# SCN-021 PA01 evidence envelope verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`8ce5c3600a136c4b9fd571ca99bb36548358c135`. The delivery report will bind the
final commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-021-pa01-evidence-envelope.md) pass for the pure
envelope and guarded local Supabase protocol-v2 boundary using synthetic fixtures.
No hosted database, actual policy source, broker operation, command/risk mutation,
strategy promotion, deployment or Auto Trading change was performed.

## Implemented scope

- Added strict policy observations for quote, market session, news and account
  state, including UTC observation times, source IDs, exact spread/blocker values
  and a five-second fresh-quote check while an active market is claimed.
- Added a pure builder that revalidates the aggregation hash, reruns PA01 and derives
  the context hash, full decision fingerprint, stable snapshot/signal IDs and exact
  protocol-v2 receiver payload. Callers cannot provide a separate action or feature
  result.
- Added an additive receiver migration. Protocol v2 stores immutable policy context
  beside the feature snapshot and links its evidence ID from the signal. Protocol
  v1 rows remain unchanged, readable and accepted.
- Preserved backend-only RPC grants, owner RLS, producer immutability, atomic
  insert-or-verify, named conflicts and independent UNKNOWN read-back.

## Acceptance evidence

- **AC-01:** strict model and pgTAP fixtures reject duplicate, future, unknown and
  stale-but-marked-fresh policy observations; exact source IDs/times survive read-back.
- **AC-02:** Python fixtures reject a forged aggregation hash and mixed identity;
  BUY/SELL/WAIT/BLOCK output is recomputed by the kernel inside the builder.
- **AC-03:** identical inputs produce byte-identical JSON/fingerprint/IDs; policy,
  code or blocker changes alter the fingerprint and stable IDs.
- **AC-04:** model and receiver validators bind M5 formation, market-data cutoff,
  policy cutoff, available/confirmed time and exact 30-second expiry causally.
- **AC-05:** fresh migrations and a disposable forward-migration database preserve
  legacy and protocol-v1 producer bytes. Matching v2 writers converge; changed
  writers conflict; a discarded committed response reconciles before retry.
- **AC-06:** pgTAP denies anonymous/authenticated RPC execution and rejects updates
  or deletes of producer evidence. Existing owner SELECT RLS/browser flow passes.
- **AC-07:** static guards and row counts prove no command, risk event or order is
  created. Envelope code has no HTTP, filesystem, database, clock-now, broker or
  execution dependency.
- **AC-08:** local Python, web, database, installed-package and affected Linux image
  regressions pass without weakening earlier acceptance tests.

## Verification run

- Targeted PA01 kernel/aggregation/envelope: **50 passed**.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **856 tests passed** in 38.40s,
  repository secret scan PASS.
- Guarded `npm run check:db:local`: fresh migration and lint PASS; advisors reported
  only expected fresh-database unused-index INFO; **459 pgTAP checks passed**; RLS
  mutation detector passed; native and PA01 forward/concurrency verifiers passed.
- `scripts/check-pa01-decision-concurrency.py`: protocol-v1 forward compatibility,
  real lock overlap, v2 matching convergence, changed-writer conflict and
  committed-response loss/read-back PASS in an invocation-owned database.
- `env -u DEBUG ... scripts/check-owner-browser.mjs`: PASS on Playwright 1.63.0 /
  Chromium 153.0.8010.12 against real local Auth/API/PostgREST, including owner
  signal RLS/UI placement and scoped fixture cleanup.
- `npm run check:web`: TypeScript PASS, **180 tests passed**, production Vite build
  and client-bundle secret scan PASS.
- `scripts/check-worker-package.py`: PASS on Python 3.14.7 / uv 0.12.15 for exact
  wheel/sdist contents, isolated non-editable install (including the envelope
  module), recovery/startup and disabled-default behavior. Evidence:
  `output/worker-package/27a77dd13e404540aee2cf92a9e26dec/result.json`.
- `scripts/check-worker-container.py`: PASS for the worker candidate image, exact
  installed source bytes, hardening and UNKNOWN/restart behavior. Evidence:
  `output/worker-container/sochron-worker-62149cdc50c2/result.json`.
- `scripts/check-container-python.py sochron-worker-62149cdc50c2:candidate`: SQLite
  source/linkage probe PASS and **801 tests passed** in the affected Linux image.
  Evidence: `output/container-python/sochron-python-4d59f956a611/result.json`.
- Static database, Compose, project baseline, installed/repository skill integrity,
  targeted Ruff/format and `git diff --check`: PASS.
- Source hashes: envelope
  `ec1b2c7ac59e50805832b730ec8c97dbc5d987d86720a4f37ad74e91f4919658`,
  migration `c75e77a373802434d723e0373fa613054bfb7fb4443141f20477330ae348c264`,
  pgTAP fixture `4324204d29297ec432348e5a353a6c814600053a76f32f723789ae8d22f46ea6`,
  Python fixture `a9727dac1c1e9f5e3f845c3708190f40ed61f3ca7c79ec1409d71c889e6bb7a8`.

The first installed-package attempt stopped before building because uv 0.12.15 was
not on PATH. A temporary isolated uv 0.12.15 environment was then used and the full
package verifier passed. Early migration lint/test findings were corrected before
the final fresh reset and are not reported as passing evidence.

## Evidence limits and next boundary

This evidence proves deterministic envelope construction and local PostgreSQL/RLS/
RPC behavior for generated data. Policy observation IDs are validated and retained,
but no actual market calendar, quote, news or account-state reader supplied them.
It does not prove HTTPS or hosted Supabase durability, scheduled producer uptime,
broker-feed parity, a research edge, Demo execution or release readiness.

The next safe source-side increment is the private durable producer: bounded native
and policy-context readers, SQLite PREPARED/UNKNOWN/VERIFIED journal, PostgREST
store/read transport and one scheduled step that always reconciles UNKNOWN before
retry. `/api/owner/signals` remains correctly `awaiting_source` until that component
is explicitly configured and run.
