# SCN-026 broker risk authorization verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`b7c9b593d2a162b2820efd662ed919e17053c67b`. The delivery report binds the final
commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-026-broker-risk-authorization-envelope.md) pass
for the local API, journal, recovery, simulator, polling wire and pure MQL codec
boundary. This does not implement or authorize an MT5 mutation EA. MetaEditor
compilation, `OrderCalcProfit`, `OrderCheck`, `OrderSend`, broker callbacks,
selected-account parity and an actual Demo round trip are `NOT RUN`.

## Implemented scope

- Derived an immutable entry authorization from the already admitted remaining
  account-currency risk and exact selected-volume cost allowance.
- Persisted one `dispatch_authorizations` row in the same transaction as the
  dispatch attempt and SENT transition, before adapter invocation.
- Required the risk/cost values through the executor interface, simulator and
  polling adapter. Management commands retain explicit null values.
- Evolved the command to an exact 24-field envelope and extended the pure MQL
  parser/self-test with bounded positive risk and nonnegative cost decimals.
- Added startup and offline recovery checks that reject missing, orphaned,
  nonfinite or reservation-inconsistent authorization.
- Repaired two verification fixtures exposed by the change: the installed-package
  recovery seed now supplies authorization, and the Linux full-suite context now
  includes the SCN-024 source guard and its MQL input.

## Acceptance evidence

- **AC-01:** service and simulator tests prove `risk_limit` is the sizing decision's
  available risk and `cost_budget` is volume times configured per-lot costs.
- **AC-02:** journal tests inspect the durable pair and prove invalid limit, cost,
  NaN and reservation relations roll back without an attempt or state transition.
- **AC-03:** every adapter send has the typed values; simulator and bridge reject
  missing, negative, nonfinite and inconsistent shapes.
- **AC-04:** API tests require 24 fields, both values on open, nulls on management,
  and preserve the same values on claimed polling replay.
- **AC-05:** MQL source guard passes for the 24-field parser. Its self-test source
  covers missing limit, cost equal to limit and zero-cost handling. Compilation and
  script execution remain absent.
- **AC-06:** claimed-timeout tests retain the same pending dispatch rather than
  generating a replacement; outcome binding and generation fences remain intact.
- **AC-07:** startup, snapshot and installed recovery tests deny missing/NaN/excess
  cost authorization while preserving UNKNOWN, exposure, halts and query-only
  reconciliation.
- **AC-08:** full local, web, static, installed-package and Linux container gates
  pass. MQL/MT5 and actual-target evidence remain explicitly absent.

## Verification run

- Focused execution/recovery/MQL-source tests: **327 passed** in 11.63s.
- Final `bash scripts/check-scn-001-local.sh`: Ruff PASS, **975 tests passed** in
  40.79s and repository secret scan PASS over 3,055 text files.
- `npx -y -p node@24.21.0 npm run check:web`: TypeScript PASS, **180 tests passed**,
  production Vite build and browser-bundle secret scan PASS.
- Static Supabase and Compose checks, project baseline, installed/repository skill
  integrity and whitespace checks: PASS.
- Pure execution protocol source guard: PASS. Current source hashes are
  `08e391e0ba4582c770a035943d3badab1a8c1e7ae0d2261c746ea65a0b876e1f`
  for `ExecutionProtocol.mqh` and
  `7c15a014adee3f598a3fd25c812de622c9551affecfe36c5aa16c92e248670f1`
  for its self-test. Both committed golden inventory/outcome verifiers pass.
- Commands SQLite schema fingerprint:
  `c94bc67e998e0a6ef7854f5ad23e8ce7b1c605ce62552786b0d21c32b5dfed7b`.
- Installed worker package: first run correctly failed because its recovery fixture
  still used the old dispatch signature. After the fixture was updated, the exact
  rebuild/install/startup/recovery verifier passed. Evidence:
  `output/worker-package/193f17bab3884cbabea36bf7ff4937c8/result.json`.
- Worker container: PASS for installed bytes, fixed SQLite identity, private
  volumes, UNKNOWN recovery, replacement and no resend. Evidence:
  `output/worker-container/sochron-worker-e28f954bdece/result.json`.
- Linux full suite: first run failed during collection because the verifier omitted
  the SCN-024 source-guard script from its isolated context. After the manifest was
  repaired, **918 tests passed** in 23.94s on Python 3.14.7 / SQLite 3.53.4.
  Evidence: `output/container-python/sochron-python-0b181062dcda/result.json`.

## Evidence limits and next boundary

The verified candidate can durably tell a future executor the maximum admitted
account-currency risk and cost allowance, and it fails closed when that evidence is
not recoverable. It cannot prove current broker loss, contract metadata, accepted
volume, mutation success, fills, positions or SL protection.

The next execution unit is a separately default-off mutation EA with an exclusive
executor lock, durable local attempt ledger, current Demo/account/symbol preflight,
`OrderCalcProfit`, `OrderCheck`, at most one `OrderSend`, cumulative
`OnTradeTransaction` reconciliation and broker-side SL confirmation. It requires
selected-host MetaEditor compilation before any owner-authorized Demo operation.
