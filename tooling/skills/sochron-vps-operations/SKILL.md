---
name: sochron-vps-operations
description: Prepare and verify Sochron1k Docker Compose deployment, MT5 Wine or Windows executor integration, monitoring, backups, restore and release recovery. Use for this project's operations work; local preparation does not require broker or cloud credentials.
metadata:
  version: "1.0.0"
---

# Sochron1k VPS operations

Read the current task contract, `docs/architecture.md`, and blueprint sections 05, 19-23. Locate actual manifests and runbooks before editing. The target is Hostinger Linux plus a Wine MT5 executor; compatibility is a hypothesis requiring evidence. Do not switch to another host or change the trading platform merely because a deployment skill is available.

## Local preparation

Proceed with Compose files, image builds, health checks, synthetic fixtures, backup tooling and dry-run plans within the development request. Record pinned runtime/dependency versions, image digests, config names and persistent-volume layout. Keep auto trading off by default. Never print fully interpolated secret-bearing configuration into logs or chat.

Expose only the intended reverse-proxy endpoints publicly. Keep the executor bridge and databases private, authenticate service identities separately from owner sessions, and keep privileged credentials out of browser assets and images. Use HTTPS and a restricted administration path on the target host. Do not assume localhost addressing is shared between containers, host Wine and a remote executor.

## Target validation and deployment

1. Check existing authorization against the actual host/account, artifact, cost and action. Reuse authorization that still covers the target; do not request it again. If something material is missing, finish the local build, diff, dry run and recovery plan before requesting that missing decision.
2. Verify target identity, terminal data directory/build, account Demo mode, symbol contract, clock synchronization, disk headroom, service user, mounts and private network reachability without exposing secrets.
3. Test the bridge under restart and network interruption. Measure heartbeat gaps, pending/unknown reconciliation and bounded risk-loop delay. A successful container start or HTTP health endpoint does not establish executor readiness.
4. Deploy the reviewed artifact/config/schema combination using the contract's rollout plan. A schema-changing release must preserve supported application versions and have a tested forward-fix/restore decision. An application rollback alone does not restore lost data.
5. Do not restart the terminal or update uncontrolled dependencies while a position is open as a routine deploy step. During incidents, select the recovery procedure based on observed exposure and the granted authority.
6. If a deployment/write times out, inspect the actual job and target state before repeating it. Reconcile outstanding broker effects before accepting new entries.

If Wine fails the actual environment gate, document evidence and prepare the existing API contract for a Windows executor. Record additional costs separately; do not buy or provision the fallback implicitly.

## Backup and restore

Keep research history, journal, risk baselines and experiment state in the recovery scope. Copying an active SQLite main database without handling WAL is not a valid backup procedure. Use its online backup API or a verified quiescent method. For Supabase, use the current supported export/restore procedure, respect data classification and retain an off-host copy.

Restore into an isolated target with broker dispatch disabled. Validate schema, constraints, unique deals, pending operations, baselines and halts; then compare recovery point/time against project RPO/RTO. Record actual measured results. If objectives are undefined, local rehearsal can proceed but unattended-Demo release readiness remains incomplete.

Initial retention is raw ticks 30 days and diagnostic logs 14-30 days, with signals/deals/versions retained throughout an experiment. Back up and verify before retention deletion; use exact scoped paths, not a broad cleanup command. Measure storage and alert at the blueprint's initial 70% and 85% thresholds.

## Observe and hand off

Check feed age, executor heartbeat, confirmed SL, risk halt, journal writability, queue age, reconciliation mismatch, storage and API budgets. Measure feed-to-UI, signal-to-send and send-to-fill p50/p95 separately. Alerts need an actual authorized destination and a tested delivery path; creating configuration is not proof of notification.

Unattended Demo requires critical scenarios on the target host, restart/network-loss evidence, no unresolved positions/mismatches, restored backups and the specified multi-market-day burn-in. Time still needed for observation is pending work, not PASS. A web emergency-close click remains a request until the executor confirms the result.

Return source/artifact/config/schema identities, commands and results, current service/executor state, unresolved side effects, observation window and next safe action. Never label local simulation or deployment preparation as an operational Demo release.

## References

- [Docker Compose](https://docs.docker.com/compose/)
- [SQLite backup](https://www.sqlite.org/backup.html)
- [Supabase backups](https://supabase.com/docs/guides/platform/backups)
- [Hostinger MT5 environment](https://www.hostinger.com/applications/metatrader-5)

Read the relevant current official documentation for the installed version before implementing host commands; this skill supplies no guessed production shell commands.
