# SCN-027 MQL5 cumulative execution evidence codec verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`fecfc0ea20fff832d3e76d99418eefcb97b63071`. The delivery report binds the final
commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-027-mql5-cumulative-execution-evidence-codec.md)
pass for Python schema validation, exact synthetic fixtures, MQL source purity and
the typed source-level codec. MetaEditor compilation, MQL script execution, an
attached terminal, account state and every broker operation are `NOT RUN`.

## Implemented scope

- Aligned Python configuration, inventory and dispatch identifiers with the
  bounded ASCII alphabet accepted by the MQL command parser.
- Added typed MQL structures and encoders for deal, entry, management and
  rejection evidence rather than accepting arbitrary JSON fragments.
- Required finite values, bounded deal sets, unique deal IDs, UTC timestamps,
  volume conservation, ticket/position/SL state relations and operation binding.
- Added a cumulative inventory encoder bounded to one entry, one management result
  and one rejection under the existing single-exposure invariant.
- Added exact synthetic inventory and outcome fixtures covering filled, protected,
  closed and management evidence, while preserving the source-only evidence limit.
- Added Python causal checks that reject broker evidence observed after its parent
  inventory or outcome observation time.

## Acceptance evidence

- **AC-01:** configuration and dispatch tests reject unsafe executor, account,
  symbol, generation, attempt and command identifiers before polling exposure.
- **AC-02:** source guard and self-test source require deal volume, price, signed
  financials, bounded UTC occurrence time and duplicate-deal rejection.
- **AC-03:** the entry encoder validates volume conservation, cumulative deal
  totals, ticket/position requirements, SL semantics and terminal-state relations.
- **AC-04:** the management encoder validates operation binding, its own cumulative
  deals and the updated target entry snapshot.
- **AC-05:** outcome encoders bind boot, sequence, attempt, generation, command,
  target and operation fields to the parsed command.
- **AC-06:** the inventory encoder rejects conflicting IDs/namespaces and remains
  bounded to the current single-exposure model.
- **AC-07:** both exact golden fixtures pass Python schema and causal validation;
  source mutation tests fail when a required typed encoder is removed.
- **AC-08:** local, web, static, installed-package, worker-container, Linux,
  source-purity, secret and whitespace gates pass. MT5 evidence remains absent.

## Verification run

- Focused execution bridge, MQL source and exact fixture checks: **86 passed**.
- Final `bash scripts/check-scn-001-local.sh`: Ruff PASS, **987 tests passed** in
  40.48s and repository secret scan PASS over 3,166 text files.
- `npx -y -p node@24.21.0 npm run check:web`: TypeScript PASS, **180 tests
  passed**, production Vite build and browser-bundle secret scan PASS.
- Static Supabase and Compose checks, project baseline, installed/repository skill
  integrity and whitespace checks: PASS.
- Pure execution protocol source guard: PASS. Source hashes are
  `09cffdcd45934e51153e87c775fc25314b6edb2cab7dc2f4d4045801a9a73286`
  for `ExecutionProtocol.mqh` and
  `7d45227ec3f7f0627e5be5b4927ad95cbe357623ac5522eb8aac0c6d99875e9a`
  for its self-test.
- Exact fixture hashes are
  `f07bbc6f656f20fca3e39cca405d3f5f240107af0ea13adce5d8ff921eee923d`
  for inventory and
  `a412c0f65a313ac1586f79824e3a8e480cf279f69b7862c49fef9c0d34389d21`
  for outcome.
- Installed worker package: PASS. Evidence:
  `output/worker-package/ecb1bac2a54d431fa67142a659d040dd/result.json`.
- Worker container: PASS for installed bytes, fixed SQLite identity, private
  volumes and restart/UNKNOWN behavior. Evidence:
  `output/worker-container/sochron-worker-6ac2e1bff152/result.json`.
- Linux full suite: **922 tests passed** in 23.87s on Python 3.14.7 / SQLite
  3.53.4. Evidence:
  `output/container-python/sochron-python-30a3fdd97c1a/result.json`.

## Evidence limits and next boundary

The verified candidate defines and validates how a future EA must report cumulative
orders, deals, positions, management results and broker-side SL state. It does not
populate those structures from a terminal and proves no compile, callback, restart
or broker behavior.

The next execution unit is a separately default-off mutation EA with an exclusive
executor lock, durable local attempt ledger, exact Demo/account/symbol preflight,
`OrderCalcProfit`, `OrderCheck`, at most one `OrderSend`, cumulative
`OnTradeTransaction` reconciliation and broker-side SL confirmation. Selected-host
MetaEditor compilation is required before any owner-authorized Demo operation.
