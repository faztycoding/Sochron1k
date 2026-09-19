# SCN-014 UI and API connection map

2026-09-20; base `2a3a6c6a02ef4a907d5aaf1075ece63753c2ca09`, dirty
candidate inputs. The containing commit identifies delivery. macOS 26.6.2 arm64,
Python 3.14.7, Node.js 24.21.0, pytest 9.1.1, Vitest 5.0.1, Playwright 1.63.0
and Chromium 153.0.8010.12.

## Outcome and acceptance status

The safety console now places a connection rail directly below the global Demo
lock. Each row maps a visible UI surface to its browser-facing API route, upstream
source and separate implementation/runtime state. The API supplies one typed,
redacted `/ui/connections` read model; the browser accepts only the eight known
nodes and exact route/source contract.

Existing account telemetry, native chart and closed-bar history routes are visible.
Execution is explicitly partial because only the redacted executor transport status
exists; `/api/owner/execution` is still missing. `/api/owner/signals` and
`/api/owner/statistics` are also explicitly missing. The rail remains visible when
status validation fails and contains no trade control.

SCN-014 AC-01 through AC-08 pass for local API/UI and synthetic browser scope.
No actual MT5, MetaEditor, hosted Supabase, strategy service, statistics service,
broker operation or deployment was used. Full Demo remains `NOT READY`, public
`execution_ready=false`, and Auto Trading remains off.

## Failing-first evidence

Before implementation, the API acceptance test received `404 Not Found` from
`GET /ui/connections` (one failure, two existing tests passed in 0.14s). The first
React acceptance run could not find the `แผนที่การเชื่อมต่อ API` heading (one
failure, one existing test passed). Neither failure was weakened or relabelled.

## Verification

- `.venv/bin/python -m pytest -q tests/test_api_safety.py`: **4 passed** in 0.16s.
- `.venv/bin/python -m ruff check services/api/src/sochron1k/ui_connections.py services/api/src/sochron1k/main.py tests/test_api_safety.py`: PASS.
- `npx -y -p node@24.21.0 npm run check:web`: typecheck PASS, 8 files /
  **141 tests passed**, production build PASS and client-bundle secret scan PASS.
- `env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs`:
  PASS with synthetic local Auth/telemetry/chart/history, owner isolation, session
  refresh/revocation, API map, desktop/mobile screenshots and 320 px containment.
  The first invocation stopped at prerequisites because the disposable local
  Supabase stack was not running; after guarded loopback-only startup the verifier
  passed and cleaned up both generated users/sessions. The stack was stopped after
  the run and its local volume was preserved.
- `bash scripts/check-scn-001-local.sh`: Ruff passed, **760 passed** in 35.30s,
  and the repository secret scan passed over 1,855 text files on Python 3.14.7.
- `bash scripts/check-project-baseline.sh`: PASS for the eight-file baseline,
  Demo-safe defaults, blank secret examples and SCN-001 IDs.
- `python3 scripts/check-agent-skills.py`: PASS for all recorded installed skills
  and the four repository Sochron skill sources; integrity scope only.
- `git diff --check`: PASS.

The Playwright CLI wrapper was attempted first as required by the browser skill but
could not find Chrome at its standard macOS path. No browser was installed. The
repository verifier used its already pinned Chromium instead.

Final source-list-bound browser artifact:
`output/playwright/scn005-f54fa31d-bbab-4719-9100-5a1649cf1c68/result.json`.
It passed with production build SHA-256
`45003b914530e42204eecbf43fc4f0a1f4020021d57fc712449d37fe4c0791b2`,
cleanup PASS and screenshots at 1440 px and 390 px. Page containment also passed
at 320 px. The earlier visual pass is retained but is not the final evidence link.

## Evidence limits and next inputs

Screenshots prove layout against synthetic values, not an external source. The map
describes integration state; it does not make an API or broker ready. To fill the
remaining UI, implement the authenticated owner execution evidence read model,
then versioned signal and statistics read models. Actual MT5 sections still require
the broker/Demo identity, exact symbol/contract, host/MetaEditor build, private
credential provisioning and the separately authorized first Demo round trip.
