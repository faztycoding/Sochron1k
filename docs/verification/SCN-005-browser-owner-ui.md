# SCN-005 browser owner UI increment

2026-09-17 candidate based on `812043b275b464b04e1163e80eeeb19f3def8872`.
macOS arm64; Node 24.21.0, Python 3.14.7; React/Vite versions unchanged.

## Scope

Runtime public Auth configuration, official SDK memory-session adapter, Thai
email/password form, local logout with failure retry, authorized account/quote
display, serial cancelable polling and stale-state display. No broker operations,
new database writes, hosting changes or trade controls. Existing command history
placeholder now says history is unconnected instead of claiming no pending orders.

Design uses the frontend-design skill to preserve the project's Charcoal Gold
palette and Sarabun/Inter, adding one account workspace rather than reworking the
dashboard. React skill guidance keeps user actions in handlers and separates SDK
subscription from token-bound polling. Supabase/FastAPI skills shape the public
configuration and authorization boundary; browser metadata never grants ownership.

## Verification and known limits

- `npx -y -p node@24.21.0 npm run check:web`: typecheck, 26 tests, production build
  and client-bundle scan pass. Components exercise disabled/config-error states,
  sign-in errors, owner denial, malformed data, stale quotes, logout response races,
  failed logout retry, duplicate Auth events, token-refresh races, network failures
  and quote expiry during a hanging request. A test uses the actual SDK against
  synthetic HTTP responses and verifies local logout and no session storage writes.
- `bash scripts/check-scn-001-local.sh`: Ruff, 153 Python tests and source secret
  scan pass. New public config test proves the exact field allowlist, default-off
  behavior, absence of the owner UUID, and no-store caching.
- `npx -y -p node@24.21.0 npm audit signatures --omit=dev`: 14 registry signatures
  and 13 attestations verified. Whole-tree `npm audit signatures` failed with a
  registry attestation 404 for existing `whatwg-url@17.1.1`; not relabelled PASS.
- Desktop Chrome and 390x844 viewport inspected on the actual running application,
  default Auth-disabled state. Document width equals viewport width (390), safety
  state remains visible, and no login form falsely appears before configuration.
  Viewport override was reset. This is visual inspection, not committed E2E coverage.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: pass. A real HTTP request through the running Vite proxy
  to `/api/auth/config` returned `200`, `Cache-Control: no-store`, and only
  `{"enabled":false}` with the default private server configuration absent.

During development, existing App mocks failed because a second endpoint consumed
their shared/single-use response. Fixtures now route health/config requests
separately; health safety assertions remain. The SDK lifecycle test initially
included its module-load random storage capability probe. Module initialization is
now explicit fixture setup before recording session lifecycle writes; the no-write
assertion for client creation/sign-in/logout remains unchanged. SDK source confirms
the probe deletes its key and does not contain credentials.

AC-07 is PARTIAL, not PASS: real browser-to-Supabase sign-in, token refresh, logout,
owner denial and browser telemetry integration are not yet verified together.
The previously verified real local API/Auth boundary is not substituted for that
browser gate. No actual owner has been provisioned and no real MT5 telemetry was
received. Graph, signal, statistics and execution/recovery work remain incomplete.

Next safe work: a reproducible isolated browser verifier using generated local
Auth users, the real API, and explicitly synthetic telemetry; then actual MT5
integration when owner inputs and target authorization are available.
