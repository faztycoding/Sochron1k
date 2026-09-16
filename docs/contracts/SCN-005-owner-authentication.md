# SCN-005 Owner authentication and telemetry access

Version 1.0; High assurance; extends SCN-002 and SCN-004. The full goal is still a
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
  criterion remains pending until browser integration and browser tests exist.

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
AC-07 remains PENDING: no browser login/logout integration yet. See the
[verification record](../verification/SCN-005-owner-authentication.md) for exact
commands and limits. No real owner account or hosted Supabase project is selected.
Local synthetic fixtures do not establish hosted configuration, browser safety,
MT5 connectivity or Demo release readiness. Pending UI integration is not a reason
to bypass API authorization. SCN-001 execution/recovery and actual terminal gates
remain required before any Demo order or unattended operation.
