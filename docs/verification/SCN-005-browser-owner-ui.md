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

At this initial checkpoint AC-07 was PARTIAL: real browser-to-Supabase sign-in, token refresh, logout,
owner denial and browser telemetry integration are not yet verified together.
The previously verified real local API/Auth boundary is not substituted for that
browser gate. No actual owner has been provisioned and no real MT5 telemetry was
received. Graph, signal, statistics and execution/recovery work remain incomplete.

## Real-browser integration increment, 2026-09-17

Candidate based on `fbf28e6d5514c08b0e15d62e9c16a55cfbff10f8`; source hashes and dirty
state are recorded rather than attributing new code to that base revision.
`scripts/check-owner-browser.mjs` rebuilds the production artifact and runs it in
Playwright 1.63.0 / Chromium headless 153.0.8010.12 against isolated real FastAPI
and the project-scoped real Supabase Auth/RPC. Node 24.21.0, Python 3.14.7,
Supabase CLI 2.117.0; container image IDs and production artifact SHA-256 are retained.

Command:

```bash
env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs
```

PASS: owner login/private account display; denial of a foreign authenticated user
with forged owner metadata; no localStorage/sessionStorage/cookies/IndexedDB left
by the session; desktop/mobile layout; price fresh-to-stale-to-fresh transitions;
real SDK refresh HTTP exchange followed by private reads using an issued new token;
logout revoking that still-unexpired token; reload losing the memory session.
Cleanup PASS includes deleting only the two generated users and confirming each
is absent, closing own child processes and removing own private temporary directory.
No existing developer process or account was stopped or changed.

Candidate result and synthetic screenshots:
`output/playwright/scn005-1afa1fa4-69fb-4e43-8f3c-3ea8fa0e823c/`.
Production artifact digest:
`081375df91e8e844be3a0c6a417b01a8673353a2319923515cd71037619c04f8`.
Verifier digest:
`c2a694ce54b1a857562052c5856a27a55483ff78d33c8e767776f44b1eead6ac`.
Artifacts are local and ignored by Git; they are not a public deployment.

Visual inspection found wrapped decimal strings at 390px. The CSS now adapts the
number of columns while retaining all digits; a DOM-range/width assertion verifies
four fixture values each occupy one line without overflowing their cells. Desktop
and mobile synthetic screenshots were inspected. No rounding or calculation changed.
The frontend-design skill guided this content-first adjustment within the existing
Charcoal Gold design. React review found no component change needed for refresh.

Development failures retained: DEBUG guard refused the inherited debug environment;
system Chrome was absent, so the pinned matching headless runtime is used. The
initial refresh assertion waited for only the first refreshed token, but the
accelerated browser clock caused two genuine refresh exchanges. Instrumentation
proved private reads used neither the original nor first refreshed token. The
verifier now checks the actually used token against successful real refresh
responses, then proves its revocation; no application Auth assertion was removed.
The observed failed runs that created fixtures reported cleanup PASS. The verifier
also reports cleanup UNKNOWN if user creation has an ambiguous outcome, rather
than retrying it or falsely asserting that every created user was removed.

The Playwright/Supabase skills informed isolated fixture lifecycle and exact-runtime
verification. A plain Node regression script avoids CLI password arguments, traces,
network logs and an additional test framework. Refresh uses a 59-minute browser
clock jump with the server clock unchanged; this is not real-duration expiry,
background-tab, multi-browser or unattended-operation evidence.

`npm run check:web` on pinned Node passes 26 tests, typecheck, build and client scan.
`bash scripts/check-scn-001-local.sh` passes Ruff, 153 tests and the source secret
scan after stopping the local Supabase stack (volumes preserved). Baseline, skill
integrity and `git diff --check` pass. Production-only signature audit verifies
14 registry signatures and 13 attestations.
`npm audit` finds zero vulnerabilities. Whole-tree signature audit still fails on
the registry's `whatwg-url@17.1.1` attestation 404; it remains an unresolved
supply-chain verification limit, not a PASS or accepted release exception.

AC-07 local integration is verified; actual owner provisioning, hosted Supabase,
MT5 connectivity/EA compilation, execution and recovery gates remain unverified.
Graph, signal and statistics features remain incomplete. No Demo-ready release,
deployment or broker operation is claimed. Next safe work is completing the remaining
application features and executor contracts; actual terminal work still requires
owner inputs and exact target authorization.
