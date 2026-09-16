# SCN-002 all-table owner isolation

Scope: AC-02 and R-011 at the local PostgreSQL role boundary. No application policy or grant was widened. All new records and helper functions are synthetic, transaction-local, and rolled back. The helpers are security-invoker, so reads and write attempts run as the selected browser role.

## Coverage

`supabase/tests/scn_002_all_table_access.test.sql` has 256 assertions:

| Scenario | Assertions |
| --- | ---: |
| Explicit fixture inventory matches all public application tables | 1 |
| Both owners' rows exist in each table before role switching | 17 |
| Each of two authenticated owners sees only their own row | 34 |
| Each of two authenticated owners is denied insert/update/delete on every table | 102 |
| Authenticated owner with no records sees no rows | 17 |
| Authenticated role with missing subject sees no rows | 17 |
| Anonymous select/insert/update/delete denied on every table | 68 |

The original 16 assertions remain in `scn_002_rls.test.sql`. The combined pgTAP result is 272 checks across two files. Exact owner arrays prevent empty results or an extra owner's row from passing. SQLSTATE and permission-error assertions distinguish permission denial from malformed fixture data.

## Verifier challenge

`scripts/check-supabase-rls-mutation.py` runs only after the local endpoint/project guard. It modifies the `audit_events_owner_select` predicate to `true` inside the fixture transaction. The expected result is exactly four failing audit-events read assertions (owners A and B, empty owner C, and missing subject). It then verifies the catalog predicate equals its pre-test value and reruns all 256 assertions successfully. This is an intentionally failing fixture, not an accepted authorization bypass. Errors abort the connection/transaction; no commit is issued.

The mutation verifier prints the source revision, dirty-state flag and fixture SHA256. A dirty candidate result does not prove a later commit. The final saved candidate is rerun before push.

## Commands and environment

Full disposable-local verification (reset acknowledgement required):

```bash
SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:db:local
```

Targeted, non-reset verification against the running local stack:

```bash
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm exec supabase -- test db --local supabase/tests --network-id sochron1k_supabase_local
bash scripts/with-local-docker.sh .venv/bin/python scripts/check-supabase-rls-mutation.py
```

Environment: PostgreSQL 17.6, Supabase CLI 2.117.0, Node 24.21.0, Docker Engine 29.5.2 arm64; fixtures mounted read-only. Initial expanded candidate is based on `535a484`; full-run output is retained locally at `output/verification/scn-002-all-tables-candidate.log`. Runtime startup/stop and source-secret scan constraints are in the local database runbook.

## Limits

Role switching and request-subject settings deliberately simulate the database end of a verified request. They do not verify JWT signatures, token expiry, session revocation, HTTP grants, application Auth wiring, or an actual browser login. Service-role/backend authority, immutable history, all schema-integrity cases, recovery, and MT5 readiness remain separate gates. No hosted Supabase project or broker was accessed.
