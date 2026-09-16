# Owner-authenticated API reads

SCN-005 adds `GET /owner/session` and `GET /owner/telemetry`. Both require exactly
one `Authorization: Bearer <Supabase user access token>` header. They do not accept
passwords, query-string tokens, executor tokens or client-supplied ownership.
They cannot send trades or enable Auto Trading. The React login integration is
still pending; this runbook documents the API boundary, not a finished login UI.

## Configuration

The API defaults to `503 OWNER_AUTH_DISABLED`. To enable private reads, an operator
must provide `SOCHRON_OWNER_AUTH_CONFIG_FILE` pointing to a regular, owner-readable
private JSON file (mode 0600 or 0400, owned by the API user, not a symlink) outside
the repository. It contains exactly:

- `supabase_url`: HTTPS project origin; explicit loopback HTTP is permitted locally.
- `public_key`: project publishable key, or legacy anon key for local compatibility.
- `owner_id`: UUID of the explicitly selected owner in that same Auth project.

Do not use service_role/secret keys, put tokens in command arguments, commit private
configuration, or send passwords in chat. Private file errors fail startup with a
redacted message. Changing the selected owner requires an operator configuration
change and API restart; user-editable metadata cannot select or impersonate the owner.

Apply the committed session-validation migration to the local test database before
enabling reads. Hosted migrations and an actual owner account are not provisioned
by this work. Container secret mounting and hosted setup need their own scoped
configuration; the existing default Compose deployment leaves owner Auth disabled.

## Behavior and failures

Each read verifies the access token with Supabase Auth, matches the verified owner
ID, then checks the specified session through an authenticated boolean RPC. The
lookup checks current row membership, user ownership and `not_after`; it does not
claim to implement every optional hosted inactivity/single-session policy earlier
than Supabase enforces it. No private authorization result is cached across reads.

- `401 AUTH_REQUIRED`: absent/invalid/expired identity or revoked session.
- `403 OWNER_REQUIRED`: authenticated user is not the configured owner.
- `503 AUTH_UNAVAILABLE`: Auth/RPC timeout, outage or invalid upstream response.
- All owner-route responses are `Cache-Control: no-store`.

Telemetry returns `status` and `observation` from one lock-protected view. A last
observation can remain present while status is stale/rejected: clients must show
that status and must not treat the retained quote as current. Disabled and awaiting
snapshot states do not fabricate account values. The status always reports
`execution_ready=false` and `auto_trading_enabled=false`.

## Local verifier

With the project-scoped Supabase stack running and migrations applied:

```bash
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 .venv/bin/python scripts/check-owner-auth-local.py
```

The verifier guards the local project/workdir and loopback API, captures local CLI
keys without printing them, creates two uniquely named synthetic users, signs in,
checks owner/foreign/anonymous access, checks cross-user session denial, signs out,
and proves the still-unexpired token is denied. Its administrative credential is
used only for fixture creation/removal, never supplied to application settings.
It deletes only the users it created, including on failed assertions, and reports
cleanup failure explicitly. No real owner account or MT5 account is touched.

Stop the local stack before the repository secret scan; generated local runtime
keys must not be mistaken for committed configuration or exempted from scanning.
