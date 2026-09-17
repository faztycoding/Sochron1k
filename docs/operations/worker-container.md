# Opt-in Linux sync worker

SCN-008 AC-07; local preparation only. Full Demo and target release are NOT READY.
R-015 requires admission of a SQLite runtime with a verified WAL-reset fix before
deployment. The current image's Python 3.14.7 links Debian SQLite 3.40.1; passing
functional tests does not clear that gate. No hosted/broker operation is authorized.

## Artifact and local verifier

`services/worker/Dockerfile` builds the locked internal wheel and installs only
production dependencies into `/opt/worker`. It uses the same digest-pinned Python
base as the existing API. Build tools/source checkout are not copied to runtime.
`/opt/artifact/SHA256SUMS` records wheel and requirements hashes, not release approval.
Record candidate image ID, source/input hashes and test report together; do not use
the mutable `:local` tag or project version alone as an approved release identity.

Run the local verifier with the existing project Python environment and a running
local Docker engine. It requires development fixtures but does not install those
fixtures into the candidate runtime:

```bash
bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py
```

The command rejects non-Unix Docker endpoints and creates a UUID-scoped Compose
project/images/volumes under `output/worker-container/`. It builds without cache,
inspects controls/package hashes and exercises two isolated containers. The fixture
receiver has no egress or published port; the worker shares only its loopback network
namespace. A generated key is created privately at runtime, never in an image/env
or command argument. No Supabase stack, developer UI/API or MT5 process is started.

After verification, scoped containers are stopped/removed, the generated fixture key
is removed, and synthetic evidence volumes/images/build logs are retained. Report
cleanup failure honestly; do not use broad volume pruning. Retained volume names,
image IDs and checks appear in `result.json`. A failed build/config check is not PASS.

## Disabled default

The standalone `compose.worker.yaml` is deliberately not included by `compose.yaml`.
It has no source/state/config mounts, no networking or published port, a non-root
UID/GID 10001, read-only root, dropped capabilities, no privilege escalation, bounded
tmpfs/logs, 256 MiB memory and 64-process limits. The default command is `status`;
without private configuration it reports DISABLED and exits 0. Exit 0 here does not
mean a configured sync destination or a running daemon. Restart policy is `no`.

No status healthcheck is defined: local status takes the same single-writer lock as
an active worker. Use emitted JSON and inspect terminal status after stopping.
Memory/process limits are a tested local starting point, not target load evidence.

## Preparing an authorized operator overlay

Do not enable a hosted destination until its exact project, owner and transfer are
authorized, and release/runtime gates pass. Prepare a private reviewed Compose
overlay outside version control, retaining the base controls above:

1. Use the reviewed immutable image. Supply the existing capture directory at
   `/worker/source`, a separate persistent journal directory at `/worker/state`, and
   private configuration at `/worker/config`. Same host/local filesystem only, no
   NFS. Container UID 10001 must own private 0700 directories and 0600 files. Config
   volume is read-only. A bind mount must not silently create an absent directory.
2. `SOCHRON_SYNC_CONFIG_FILE=/worker/config/config.json` is the only required worker
   environment setting. Put the service key in a separate 0600 file in that private
   volume; do not place its value in Compose, `.env`, arguments, images or logs.
   Use exact archived identity/offset/owner/origin fields from the main sync runbook.
3. Source mount is writable only because SQLite may need to create WAL shared-memory
   sidecars after the writer closes/restarts. The adapter uses `mode=ro`/query-only,
   but this is **not** OS-level protection from a compromised worker. Do not set
   `immutable=1`, manually remove sidecars or copy a live database's main file alone.
4. Supply reviewed HTTPS egress/network policy in place of `network_mode: none`.
   The worker's origin validation is not a firewall or DNS allowlist. Container
   localhost is not host localhost. The verifier's shared loopback fixture topology
   is test-only, not a recipe for a hosted Supabase connection.
5. Keep restart disabled. Explicitly initialize a genuinely new empty journal once;
   subsequent updates must retain exact source/state container paths and volumes.
   A host-installed journal bound to different paths cannot simply be copied here;
   migration/rebinding requires a separately reviewed recovery procedure.

Use `docker compose` with both the base and exact reviewed overlay, and a fixed
operator project identity. `run --rm --no-deps -T worker init` is local initialization;
`run --rm --no-deps -T worker status` is local bookkeeping. Neither authorizes sync.
For an approved service, explicitly set command `[run]` and start only that worker.
These operator-target instructions are preparation, not evidence of a target run.

## Stop, replace and reconcile

Stop the worker with Compose's SIGTERM/grace period. Confirm terminal state before
inspection or replacement; an observation timeout alone does not mean it stopped.
Exit 130/STOPPED is expected for an interrupted active command. UNKNOWN remains
uncertain even if the HTTP server accepted it. Preserve all journal/source state.

Create the replacement using the same mounts, paths, identity and destination.
An explicitly authorized `run --once` must independently read the destination before
any retry. Never initialize another journal or restart repeatedly to evade a retry
budget/quarantine. Stop on corrupt/missing state or changed binding; preserve evidence.
Container replacement is not backup/restore or power-loss proof. Consistent backup,
isolated restore, RPO/RTO and actual target restart/network-loss/burn-in remain required.

See [local evidence](../verification/SCN-008-worker-container.md),
[private configuration and exit codes](native-m1-sync.md), and
[ADR-011](../decisions/ADR-011-worker-container.md).
