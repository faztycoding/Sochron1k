# SCN-020 PA01 decision receiver verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`4ba9f6b82aa6f7ad372ccb8e417879f06d4b7de7`. The delivery report will bind the
final commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-020-pa01-decision-receiver.md) pass for the guarded
local Supabase persistence boundary and synthetic fixtures. No hosted database,
source reader, scheduled producer, MT5 operation, command, risk mutation, strategy
promotion, deployment or Auto Trading change was performed.

## Implemented scope

- Added a forward migration with optional producer identity on existing feature and
  signal rows, an owner-safe one-to-one snapshot link and partial unique decision
  identities.
- Added producer-only immutable row guards while preserving existing legacy-row
  update/delete behavior needed by scoped fixture cleanup.
- Added a strict atomic insert-or-verify RPC plus an independent reconciliation read
  RPC. Both are security invoker with empty search paths and backend-only grants.
- Pinned the exact PA01 parameter hash and native aggregation version, same-owner
  strategy/experiment eligibility and code hash, explicit UTC causal times, bounded
  evidence, feature and execution-parameter shapes.
- Removed service-role TRUNCATE/trigger bypass while retaining the legacy CRUD used
  by existing integration fixtures.

## Acceptance evidence

- **AC-01:** schema/pgTAP checks prove the owner foreign key, one-to-one indexes,
  shared producer identity, producer UPDATE/DELETE rejection and legacy CRUD.
- **AC-02:** missing/unknown/oversized fields, non-UTC timestamps, malformed feature
  and execution payloads, action/reason mismatch, wrong expiry and empty/duplicate
  evidence fail closed.
- **AC-03:** mixed-owner, halted experiment, retired strategy, future data cutoff
  and changed parameter identity fixtures fail without a partial snapshot.
- **AC-04:** exact replay retains one pair; changed replay raises the named conflict;
  a signal conflict rolls back the earlier snapshot insert.
- **AC-05:** role/grant checks deny anonymous/authenticated RPC execution and browser
  table mutation, retain forced owner SELECT RLS and verify invoker/empty-search-path
  functions.
- **AC-06:** independent SQL sessions demonstrably overlap on a database lock.
  Matching writers converge, changed writers conflict, and a deliberately discarded
  committed response is found by read-back before an idempotent retry.
- **AC-07:** fresh replay, forward migration with legacy rows, schema lint, advisors,
  all pgTAP suites and existing owner browser/API fixtures pass.
- **AC-08:** static and behavioral checks prove no command/risk row is created and
  no privileged execution-side table write exists in the migration.

## Verification run

- Guarded targeted pgTAP receiver suite: **52 passed**.
- `scripts/check-pa01-decision-concurrency.py`: PASS for forward migration, matching
  and changed concurrent writers, committed-response loss and exact cleanup of its
  invocation-owned database.
- Guarded `npm run check:db:local`: schema lint PASS; advisors had only expected
  fresh-database unused-index INFO; **432 pgTAP checks passed**; RLS mutation detector
  passed; native and PA01 forward/concurrency verifiers passed.
- `env -u DEBUG ... node scripts/check-owner-browser.mjs`: PASS with Playwright
  1.63.0 / Chromium 153.0.8010.12 against real local Auth/API/PostgREST, including
  owner signal RLS/UI evidence and successful scoped fixture cleanup after the new
  migration.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **850 tests passed** in 40.02s
  and repository secret scan PASS.
- `npm run check:web`: TypeScript PASS, **180 tests passed**, production Vite build
  and client-bundle secret scan PASS.
- `npm run check:db:static`, project baseline, installed/repository skill integrity,
  full Ruff, Ruff format and `git diff --check`: PASS.
- `npm run check:compose:static`: Compose topology and secret scan PASS; no service
  was deployed or started by this check.
- Candidate source hashes: migration
  `d7f1fd27c599709d503d0132d0e59dfc85f275aadaa231116f1779d5496cb6dc`,
  pgTAP fixture
  `19b1034967a8f463b0b472aaacbef0d388cd386e7cfb42727ec16c185af8a79b`,
  concurrency verifier
  `6f2244d5fd83b3cd28bdd8ad937a0ed648fb9dcecfb7af9cc7c67396dc933eda`.
- Worker package and candidate container checks were not rerun because this increment
  changes the Supabase migration/test boundary, verifier scripts and documentation,
  not packaged worker/API Python or image inputs. Their earlier SCN-019 results are
  not claimed as SCN-020 evidence.

## Evidence limits and next boundary

This evidence proves local PostgreSQL/RLS/RPC behavior for generated fixtures. The
new store/read RPCs were exercised as database functions, not through a producer
PostgREST transport; that adapter remains a separate increment. It does not prove
HTTPS, hosted Supabase durability, a service-role secret on a target, actual broker
data, producer crash recovery, strategy performance or Demo execution.

The next safe source-side increment is a private durable producer journal and one
bounded step that reads a pinned native archive, aggregates M5/H1, evaluates PA01,
records intent/UNKNOWN before the RPC, and reconciles by the read RPC before retry.
The owner signal UI remains correctly empty until that separately verified producer
is explicitly configured and run.
