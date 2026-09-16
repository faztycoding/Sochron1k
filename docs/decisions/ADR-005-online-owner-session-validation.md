# ADR-005 Validate owner identity and active session before private reads

Adopted for SCN-005; 2026-09-17.

Use a Supabase user access token, online `/auth/v1/user` validation and the pinned
owner UUID for API authorization. Decode only bounded token claims needed for
issuer, role, expiry and session identification; decoding is not signature
verification. Auth and the Data API independently validate the submitted token.
Never authorize from `user_metadata` or an unverified subject.

Check active session membership through a minimal authenticated boolean RPC. Its
security-invoker public wrapper calls a private-schema, empty-search-path definer
function whose query requires `auth.uid()` to equal the session owner. This avoids
granting browser roles direct access to auth tables and avoids putting a privileged
service-role key in the application API or browser. PUBLIC/anon execution is revoked.

Online checks introduce dependency latency and availability coupling. For this
owner-only sensitive monitoring boundary, fail closed on Auth/RPC failure and do
not cache authorization across reads. This does not move position protection into
Supabase; the executor remains independently responsible for its risk loop.

The API returns one consistent telemetry status/observation view only after these
checks. API health and redacted bridge status remain public. Trading is unchanged
and disabled. Browser login/logout and refresh are separate integration work, not
a new API password store or shared executor credential.

Sources checked:
[Supabase sessions and post-logout token checks](https://supabase.com/docs/guides/auth/sessions),
[getUser](https://supabase.com/docs/reference/javascript/auth-getuser),
[signOut](https://supabase.com/docs/reference/javascript/auth-signout).
The changelog's API_EXTERNAL_URL `/auth/v1` and gateway changes require explicit
configured base URL/issuer verification; no deployment topology is inferred from
the default self-hosting example. No Realtime or extension-version changes apply.
