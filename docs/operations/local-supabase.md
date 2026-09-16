# Local Supabase verification

This is a disposable development database, not broker truth or a hosted deployment. Use Node 24.21.0, CLI 2.117.0 and the dedicated runtime described in [local-runtime.md](local-runtime.md). PostgreSQL 17.6 was observed in image `public.ecr.aws/supabase/postgres:17.6.1.167`.

## Start and stop

```bash
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh start
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh stop
```

Use the startup wrapper rather than raw `supabase start`: it checks the project/workdir and Unix socket, rejects a hosted-project link, creates a dedicated bridge with `com.docker.network.bridge.host_binding_ipv4=127.0.0.1`, validates that bridge's configuration, and checks effective bindings. An unsafe binding causes the newly requested stack to stop while preserving data. The CLI still prints a generic all-interface warning; authoritative Docker bindings and host listeners must be inspected, not inferred from that message.

The first raw start exposed development services on wildcard host interfaces. It was stopped without deleting data. The corrected startup was verified with all published Docker ports bound to `127.0.0.1` and macOS listeners for 54321/54322/54323 also on loopback. No public deployment or remote account is involved. Local default keys are not production credentials and must not be used as such.

The wrapper suppresses credential-bearing CLI status output. Supabase may create private generated key files under its ignored `.temp/start-secrets` directory while running. Never print, stage, or copy those files into images. The existing source secret scanner intentionally catches them; stop the local stack to let the CLI remove its generated runtime files before source verification/commit. Do not weaken the scanner to make a running stack pass. The Docker build context excludes all of `supabase`.

Stop preserves `supabase_db_sochron1k` and other project volumes. Never use `--no-backup`, `--all`, a broad volume prune, or a remote database URL for routine local verification.

## Test the disposable database

The Colima VM mounts only this project's `supabase/tests` read-only. Without that mount the CLI's pg_prove runner reports `NOTESTS`, which is failure, not acceptance.

Before a reset, inspect the target and ensure no valuable local data exists. Then explicitly acknowledge the destructive local reset:

```bash
SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:db:local
```

The command resets only the local project, reapplies migrations without seed data, runs public-schema lint, runs all advisors with errors blocking, and executes pgTAP fixtures inside a rolled-back transaction. INFO-level unused-index findings are expected for a fresh empty database; retained indexes support foreign keys and planned access patterns. This is not workload-based index validation.

## Findings and evidence limits

- Initial migration failed because the implicit currency-format constraint name collided with the explicit cost/currency-pair constraint. Rename the pair constraint before first successful deployment; both rules remain enforced. No remote migration history was rewritten.
- The initial pgTAP text-array comparison failed inside its record-comparison helper with indeterminate collation. Typed JSON equality now checks the exact same complete tuple/list, without dropping a value or owner-isolation assertion.
- The fixture suite contains 16 checks: 17-table presence, RLS/force-RLS and grants, account numeric type/Demo constraint, two-owner account reads, browser insert denial, and AI cost/currency positive/negative cases. It does not yet prove all-table row-level isolation, all data constraints, application Auth integration, or immutable decision evidence.
- SCN-001 MT5 gates, recovery, worker synchronization and unattended Demo remain incomplete.
