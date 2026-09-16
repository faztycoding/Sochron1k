# SCN-002 Supabase Data Foundation

## Contract

| Field | Value |
| --- | --- |
| ID | SCN-002 |
| Version | 1.0 |
| Owner | Project owner; technical implementer not yet named |
| Parent project | Sochron1k |
| Current state | Local migration, lint, advisors and 16 pgTAP checks pass; full data/auth acceptance remains partial and remote deployment is not authorized |
| Done scope | Reproducible local schema, owner isolation, and database tests; hosted deployment is a separate state |
| Risk tier | High assurance |
| Evidence base | Blueprint v1.1 section 15, architecture and risk register at revision `f4e3437` |

## Goal and user outcome

Provide a versioned Supabase/Postgres foundation for synchronized research and audit history without making Supabase authoritative for execution or exposing another owner's data. The schema must preserve account currency, UTC event and received times, external MT5 identifiers, immutable decision evidence, and deterministic risk-state history.

## Scope

- Pin the Supabase CLI and commit local configuration without project credentials.
- Create the section 15 entities for accounts, experiments, strategy versions, bars, feature snapshots, signals, commands, orders, deals, positions, equity snapshots, cash flows, risk events, news, AI runs, evaluations, and audit events.
- Use exact numeric types for money, prices, volumes, and costs; use `timestamptz` for events.
- Store MT5 identifiers without JavaScript precision loss and retain both event and received time.
- Enable and force RLS on every public table, revoke anonymous access, and grant authenticated users read-only access to their own rows.
- Keep browser writes out of the database boundary; mutations must pass through the authenticated API and durable local outbox.
- Add pgTAP checks for schema presence, RLS coverage, anonymous denial, owner isolation, and authenticated write denial.

## Exclusions

- Creating or linking a hosted Supabase project.
- Uploading a migration to a remote database.
- Storing MT5 credentials, service-role keys, unrestricted tokens, raw ticks, or the durable command outbox.
- Making Supabase a prerequisite for managing an already-open position.
- Granting browser-side insert, update, delete, halt release, strategy promotion, or execution authority.

## Acceptance criteria

### AC-01 Reproducible schema

Given a clean compatible local Supabase stack, when migrations are applied from the repository, then every in-scope table, constraint, foreign key, and query index is created without manual SQL or dashboard changes.

### AC-02 Owner isolation and least privilege

Given two authenticated owners and an anonymous request, when each reads synchronized history, then each owner sees only their own rows, anonymous access returns no rows or permission denied, and authenticated clients cannot insert, update, or delete operational records directly.

### AC-03 Evidence integrity

Given a decision, broker event, or risk event, when it is stored, then monetary values are exact numeric values in the recorded account currency, external identifiers remain lossless, UTC event and received times are present, and constraints reject impossible time ordering or malformed states.

AI cost and currency must be either both absent or both present with a nonnegative cost and uppercase three-letter currency. Fresh migration execution and positive/negative fixtures must verify the format and pairing constraints coexist. The initial migration has never been deployed remotely; repair its colliding constraint name before its first successful local application, preserving both checks.

### AC-04 Execution boundary preservation

Given Supabase is unavailable or contains stale data, when execution state is evaluated, then local journal and MT5 remain authoritative and the schema exposes no function, trigger, or browser grant that can send an order, release a halt, promote a strategy, or rewrite broker truth.

### AC-05 Database verification

Given the local container runtime and pinned Supabase CLI, when the database reset, lint, advisor, and pgTAP procedures run, then migrations apply from zero and the positive and negative authorization tests pass on the exact candidate revision.

Local startup must use a dedicated bridge with loopback-only port bindings, and verification must check effective bindings. Refuse a non-Unix Docker endpoint, a linked hosted project, or a same-named container from another working directory. Database reset requires explicit `SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k` acknowledgement and targets only this project's disposable local database. A zero-test run is not a pass. On Colima, mount only `supabase/tests` read-only for the CLI's pg_prove fixture bind mount; do not mount the home directory or credentials.

### AC-06 Secret and remote-action denial

Given repository and generated configuration scans, then no project reference, database password, service-role key, or credential is committed, and no remote project is linked or mutated by local setup.

## Required verification

| Acceptance | Verifier required before implementation is complete | Current result |
| --- | --- | --- |
| AC-01 | `supabase db reset --local` from a clean local stack plus schema assertions | PASS locally: initial migration applies from zero and 17-table/RLS assertions pass on PostgreSQL 17.6 |
| AC-02 | pgTAP anonymous, same-owner, cross-owner, and write-denial fixtures | PARTIAL, not PASS - all-table grant checks and two-owner accounts fixtures pass; every-table row fixtures and API/Auth integration remain |
| AC-03 | pgTAP constraint and type assertions with invalid fixtures | PARTIAL, not PASS - account numeric/Demo and AI cost/currency positive/negative fixtures pass; remaining integrity/immutability cases are unverified |
| AC-04 | Schema review and architecture fitness check for forbidden authority | PARTIAL, not PASS - static checks deny privileged functions and browser writes; application integration does not exist |
| AC-05 | Pinned CLI reset, lint, advisors, and `supabase test db` | PASS locally: reset, lint, advisors (INFO unused indexes, no errors), 16 pgTAP checks; NOTESTS failure corrected with read-only fixture mount |
| AC-06 | Repository secret scan plus CLI link-status inspection | PARTIAL, not PASS - repository scan passes and no local project reference exists; no hosted environment has been inspected |

No row can change to `PASS` without the exact source revision, CLI and database versions, environment identity, expected and observed result, and retained verifier output.

Local candidate evidence (17 September 2026 Asia/Bangkok): base `55723ab` plus the saved setup diff; CLI 2.117.0, PostgreSQL 17.6, Docker 29.5.2 arm64. Command: `SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:db:local`. Retained output: `output/verification/scn-002-local.log`. Exact saved candidate is rechecked before delivery. Startup/cleanup and known limits are in [the local database runbook](../operations/local-supabase.md).

## Authorization

Local configuration, migrations, tests, dependency installation, and static checks are authorized. Hosted project creation, login, linking, database push, paid resources, and any operation against a remote Supabase project are not authorized by this contract.

## Recovery

- A failed local migration is corrected forward before any remote use; never weaken a constraint or RLS assertion to make it pass.
- An ambiguous remote operation is treated as unknown and inspected before retry, but no remote operation is in scope for this task.
- If Supabase is unavailable, preserve the durable local outbox and stop new entries when required evidence cannot be journaled; do not infer synchronized success.

## Definition of Done

- AC-01 through AC-06 pass on a clean local stack.
- R-006 and R-011 controls have executable evidence.
- The schema is reviewed against the section 15 blueprint fields and repository authority boundaries.
- Hosted deployment and application integration remain separately reported states.
