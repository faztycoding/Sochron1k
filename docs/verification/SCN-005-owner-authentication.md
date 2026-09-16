# SCN-005 local owner authentication evidence

Candidate based on `91cd0345e35bdacf4d39892ef9d6fb02bae56ce6`, 2026-09-17,
macOS arm64, Python 3.14.7, Node 24.21.0, Supabase CLI 2.117.0, dedicated local
Colima Docker runtime. Evidence is for the scoped candidate changes, not the base
revision alone. The real-Auth verifier reports source hashes and dirty status;
clean-revision runs are retained under ignored `output/verification/` after commit.

## Observed checks

- `.venv/bin/pytest -q`: 152 tests passed, including SCN-005 malformed/duplicate
  tokens, wrong issuer/role/subject, anonymous/foreign users, forged metadata,
  revoked sessions, invalid RPC shapes, redacted upstream failures, timeout,
  expiry during validation, separate EA/owner credentials, and stale/rejected views.
- `.venv/bin/ruff check services/api/src tests scripts/check-owner-auth-local.py`:
  passed. Formatting-only lint failures during development were corrected.
- `SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh npx -y
  -p node@24.21.0 npm run check:db:local`: clean local migration replay, schema lint,
  advisors, 286 pgTAP assertions and RLS mutation detector passed. Advisors emitted
  informational unused-index findings on the fixture database; no warning/error
  findings. Existing owner-isolation checks were not weakened.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 .venv/bin/python
  scripts/check-owner-auth-local.py`: real local Auth sign-in, owner/private read,
  anonymous/foreign denial, cross-user RPC denial, logout revocation with unexpired
  JWT and generated-user cleanup passed. API exercised through ASGI; Auth and RPC
  use real HTTP to the loopback Supabase stack, not mocks.
- Migration generated with `db pull owner_session_validation --local --schema
  public,sochron_private --yes --network-id sochron1k_supabase_local --agent no`
  after local SQL iteration and advisors. Reviewed migration creates only the
  private schema, two narrow functions and their grants. `migration list --local`
  confirmed both migrations matched the local database history.
- `bash scripts/check-scn-001-local.sh`: Ruff, all 152 Python tests and source
  secret scan passed after stopping the local Supabase stack.
- `.venv/bin/python scripts/check-bridge-local.py`: isolated real-loopback HTTP
  telemetry regression passed; owner configuration is explicitly excluded from
  that synthetic child process.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`,
  `npx -y -p node@24.21.0 npm run check:db:static`, and `git diff --check`: passed.
  Installed skill/source integrity passed; this does not prove broker readiness.

## Acceptance and release limits

AC-01–AC-06 have local implementation evidence at the boundaries above. This does
not validate a selected hosted project, actual owner login, browser token handling,
browser refresh/logout races, container secret injection or public deployment.
AC-07 remains PENDING. No frontend source changed in this unit.

No EA was compiled, no actual MT5 telemetry was received, no order was submitted,
and no execution/recovery gate changed. Full usable Demo readiness is NOT achieved.
Next: implement and verify React owner login/logout and private telemetry display;
then complete actual MT5 observer and execution/recovery integration with explicit
Demo target inputs and action authorization.
