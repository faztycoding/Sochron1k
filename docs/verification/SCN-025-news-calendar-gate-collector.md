# SCN-025 News Gate collector verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`0a361403473a031547395559b6e475058a1a1a88`. The delivery report binds the final
commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-025-news-calendar-gate-collector.md) pass for the
local normalized gateway client, deterministic gate logic, private file handoff and
installed worker artifact. No external calendar/vendor/gateway was selected or
contacted. External completeness, target scheduling, deployment, hosted writes,
broker operation and Auto Trading changes are `NOT RUN`.

## Implemented scope

- Added strict private configuration with unset/exact-disabled states, an exact
  HTTPS origin, separate credential/output files, bounded currency/impact sets,
  blackout durations and polling interval.
- Added a fixed authenticated `GET /v1/calendar-window` client with redirects and
  environment proxies disabled, short timeouts, one-connection limits, identity
  encoding and bounded uncompressed JSON.
- Added strict complete-window and ordered-event models. Partial/stale/future,
  duplicate, out-of-coverage, unrequested or unexpected content fails closed.
- Added deterministic half-open blackout calculation and a content-bound revision.
  A local receipt timestamp distinguishes collection time from source publication.
- Reused the hardened atomic owner-only writer for the exact SCN-023 News Gate
  schema. Refresh failure preserves the previous gate so it can expire naturally.
- Added the installed `sochron-news-gate status|run [--once]` operator with redacted
  states, bounded retry exhaustion and permanent execution/Auto Trading false flags.

## Acceptance evidence

- **AC-01:** tests cover unset and exact-disabled configuration, exact field sets,
  HTTPS-only origin, canonical distinct paths, private permissions, hard-linked
  output and permissive directory denial. `status` does not read a credential or
  make a request.
- **AC-02:** the synthetic transport asserts fixed path, bearer header, identity
  encoding and exact filters. Redirect, wrong media/encoding, declared/streamed
  oversize and non-200 responses are denied; implementation pins no redirects,
  no environment proxy, one connection, two-second request and ten-second total
  limits.
- **AC-03:** tests reject incomplete, extra, stale/future, partial-coverage,
  duplicate-ID/key, unordered, wrong currency/impact and out-of-window content.
- **AC-04:** boundary cases prove an event exactly at blackout end is clear, an
  event exactly at blackout start blocks, cancellation is clear, multiple IDs are
  stable and a repeated validated response produces the same revision and gate.
- **AC-05:** output round-trips through `NewsGateFrame`, is mode 0600 and atomically
  replaces. Failed HTTP preserves exact prior bytes/inode; symlink and hard-link
  output are denied.
- **AC-06:** disabled/configured, invalid-argument, ready/unavailable and five-fail
  retry-exhaustion states are redacted and retain false safety flags. Installed
  artifact verification runs the default-disabled console entry point.
- **AC-07:** an actual collector fixture publishes a blocked gate consumed by the
  SCN-023 writer. A subsequent failed refresh retains blocked evidence rather than
  manufacturing clear.
- **AC-08:** targeted/full Python, installed artifact, web/build, static database
  and Compose, baseline, skill-integrity, secret and whitespace checks pass.
  External and target evidence remains explicitly absent.

## Verification run

- Targeted Ruff and `tests/test_news_gate.py tests/test_policy_evidence.py`:
  **35 passed**.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **966 tests passed** in 40.69s
  and repository secret scan PASS.
- `npx -y -p node@24.21.0 npm run check:web`: TypeScript PASS, **180 tests passed**,
  production Vite build and browser-bundle secret scan PASS.
- `scripts/check-worker-package.py`: byte-identical wheel rebuild, fresh installed
  environment, default-disabled installed News Gate/PA01 commands and all existing
  recovery/startup checks PASS with uv 0.12.15. Evidence:
  `output/worker-package/79ab2967674a486799a27ec51cd80998/result.json`.
- Static database and Compose guards, project baseline, installed/repository skill
  integrity and `git diff --check`: PASS.
- External calendar/gateway request, provider completeness audit, target scheduler,
  alert/retry supervision, deployment and burn-in: `NOT RUN`.
- Docker candidate/container checks: `NOT RUN`; no Docker executable was available
  on PATH. This is not target-platform evidence.

## Evidence limits and next boundary

The verified collector proves the project-side normalized contract, destination
restriction, strict parsing, deterministic blackout and fail-closed handoff. It
cannot prove that an external provider lists every relevant event, handles
corrections promptly, meets its availability promise or is licensed for the target
use. The owner must select and audit that source/gateway, provision its private
credential and authorize target outbound access before News Gate can be called
operational.

Even after that connection, Demo release readiness still requires compiled and
observed MT5 adapters, the full mutation/reconciliation EA, target scheduling and
recovery, hosted Supabase setup, alerting/restore and the separately authorized
bounded Demo round trip.
