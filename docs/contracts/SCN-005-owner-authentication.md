# SCN-005 Owner authentication and telemetry access

Version 1.2; High assurance; extends SCN-002 and SCN-004. The full goal is still a
usable Demo application. This slice establishes real Supabase authentication and
owner authorization before browser login/data integration. It does not complete
the full UI, authorize deployment or permit trading.

## Acceptance criteria written before implementation

- AC-01: Owner routes default disabled without private server configuration.
  Accept exactly one bounded Bearer access token, never a URL parameter, cookie,
  EA token, service-role key or client-supplied owner ID. Validate against the
  configured Supabase Auth service, pin issuer and authenticated role, deny
  anonymous users and compare the verified user ID to the configured owner UUID.
  User-editable metadata cannot grant ownership.
- AC-02: Before each private read, check the JWT session ID against a currently
  existing, unexpired `auth.sessions` row belonging to `auth.uid()`. A session
  revoked by logout is denied even while its JWT is otherwise unexpired. Missing,
  foreign, malformed and expired sessions fail closed. Auth/RPC outages deny
  access rather than serving cached private data.
- AC-03: Implement the session lookup in a non-exposed private schema with fixed
  empty search path and an explicit `auth.uid()` ownership predicate. Expose only
  a security-invoker boolean wrapper. Revoke PUBLIC/anon execution; authenticated
  callers can learn only whether their own specified session is active. No
  direct browser access to `auth.sessions`, new table grants or auth data writes.
- AC-04: `GET /owner/session` confirms owner authorization; `GET /owner/telemetry`
  returns the last observation together with its freshness state, acquired as one
  consistent in-process view. Empty/stale/rejected states remain explicit. Neither
  route can enable Auto Trading or execute a broker command. EA and user tokens
  are not interchangeable. All private responses, including errors, are no-store.
- AC-05: Bound upstream response sizes and timeouts, disable redirects and inherited
  proxy configuration. Redact tokens, user metadata, upstream bodies and credentials
  from errors/logs. Never collect an actual owner password in chat or source.
- AC-06: Negative API tests and real local Supabase sign-in/logout/revocation tests
  pass using generated synthetic users, including a second signed-in user denied
  access despite forged owner metadata. RPC role/ownership tests and existing RLS
  tests pass. Evidence identifies source revision, runtimes, fixture and boundary.
- AC-07: The actual React UI offers login/logout and displays owner-authorized
  telemetry without embedding privileged keys or fabricating broker truth. This
  criterion requires browser integration and browser tests; component mocks alone
  do not establish it.

### AC-07 browser implementation requirements (before implementation)

- Fetch public Auth configuration from the same-origin API; expose only enabled
  state, Supabase origin and a validated publishable/legacy-anon key, never the
  configured owner UUID, executor token or privileged key. Disabled/outage states
  explain what is missing and must not present a working login.
- Use the pinned official Supabase SDK for password sign-in, refresh notifications
  and local-session logout. Keep credentials/tokens out of logs, URLs and browser
  persistent storage. Reload requires sign-in again; server-side session authority
  remains the API's online checks. No browser metadata authorizes private reads.
- Poll owner telemetry serially, with cancellation and a bounded deadline. Discard
  old in-flight results on token change, logout or unmount. Clear private data on
  authorization/network/shape errors. Logout hides data immediately; failed remote
  revocation is explicit and retryable, never reported as successful logout.
- Validate displayed telemetry, preserve decimal strings and UTC timestamps, and
  display Bangkok time separately. Never label a quote fresh beyond five seconds
  using API age plus locally elapsed time, even during a stalled refresh.
- Component regression tests cover disabled/config failure, login errors, denied
  owner, malformed telemetry, stale data, logout races and retryable logout failure.
  Browser inspection covers desktop/mobile, keyboard labels and default-off state.
  Real browser-to-Supabase integration remains a distinct gate if not exercised.

### Browser integration verifier acceptance (before implementation)

The reproducible local verifier must use real browser UI controls, the production
web build, real FastAPI and real loopback Supabase Auth/RPC. Generate isolated owner
and foreign-user fixtures; clean up only created IDs and child processes. Never
put passwords/tokens in command arguments, traces, screenshots, network logs or
result artifacts. Capture only redacted results and synthetic account displays.

Verify owner sign-in, foreign-owner denial, logout and still-unexpired-token
revocation, no persisted browser credentials, memory-session loss on reload,
fresh-to-stale telemetry and desktop/mobile layout. Token refresh must be exercised
through the SDK with real refresh-token exchange; distinguish accelerated browser
clock evidence from real-duration expiry. Any missing check remains explicit.
No hosted project, real owner account, MT5 account or existing developer process
may be changed by this verifier. Synthetic telemetry is not broker evidence.

Mobile readability: at 390px, fixture account/quote decimals stay on one line and
fit their cells without page overflow. Preserve the complete decimal strings;
adapt column count, not precision. Exceptional longer values may scroll within
their value cell, never wrap into a misleading second number or widen the page.

## Implementation boundary

Use the existing HTTPX dependency for online Auth verification and an authenticated
RPC, not a new custom JWT signature implementation. The browser will use Supabase
Auth for password/session lifecycle; the API does not handle or store passwords.
The API needs only the project's publishable/legacy-anon key, not service_role.
All authoritative owner checks use the server-configured UUID and verified Auth
identity. Owner UUID provisioning remains an explicit local configuration step.

The private SQL function's elevated read is limited to one boolean ownership check
over the existing auth session primary key. It cannot change roles, sessions,
accounts, risk or execution state. Dropping the function makes API reads fail
closed. Migrations are local-only until separately approved for a hosted project.

## Current state and remaining work

API and session-lookup migration implemented with local verification. AC-01 through
AC-05 have Python/ASGI and local database evidence; AC-06 has real local Supabase
password sign-in, foreign-user denial, logout revocation and cleanup evidence.
AC-07 has local browser integration evidence: React login/logout, runtime public
configuration, owner telemetry display and component regressions are implemented.
The production build in pinned Chromium passes real loopback Supabase/API sign-in,
foreign-user denial, token refresh, logout revocation, reload, stale-state and mobile
readability checks. Refresh uses an accelerated browser clock, not a real-duration
expiry/burn-in test. Synthetic prices are not MT5 connectivity evidence. See the
[verification record](../verification/SCN-005-owner-authentication.md) for exact
commands and limits. No real owner account or hosted Supabase project is selected.
Local synthetic fixtures do not establish hosted configuration, all-browser safety,
MT5 connectivity or Demo release readiness. UI integration does not bypass API
authorization. SCN-001 execution/recovery and actual terminal gates
remain required before any Demo order or unattended operation.

The UI increment is recorded in [browser evidence](../verification/SCN-005-browser-owner-ui.md).
