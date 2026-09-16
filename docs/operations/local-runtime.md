# Local API and Web Runtime

## Status

The topology is a Demo-only local candidate. On this workstation, no-cache API/web builds, runtime hardening, host HTTP/proxy health, API replacement, and volume-marker persistence passed on Docker Engine 29.5.2 arm64 with Compose 5.5.1. The initial single-internal-network topology failed port publication; see [ADR-003](../decisions/ADR-003-local-proxy-network.md). This is local container evidence, not broker recovery or release readiness.

This runbook does not start MT5, place an order, link Supabase, expose a public port, or prove VPS readiness.

## Prerequisites

- Node.js 24.21.0 and npm 11.19.0.
- A Docker-compatible engine with the Compose plugin (verified here with 5.5.1).
- Free loopback port 8080, or a different `SOCHRON_WEB_PORT` value.
- No broker or cloud credentials are required.

The admitted base images and multi-platform digests are recorded in [container-images.lock.md](container-images.lock.md).

### Dedicated workstation runtime

The owner-authorized runtime is installed under `$HOME/.local/share/sochron-runtime`: Colima 0.10.3, Lima 2.2.0, Docker CLI 29.8.1, Compose 5.5.1, and Buildx 0.37.1. Official release checksums verified Colima, Lima, Compose, and Buildx. The Docker CLI tarball came from the official HTTPS distribution; its locally observed SHA256 is `5a8f5604d7673202b2af925229d15eb4bbb86f7f542e4ac8cd7aa3f14cfa0f8b` (not independently authenticated against a publisher checksum).

The dedicated `sochron1k` Colima profile uses VZ, 4 CPUs, 8 GiB RAM and a 40 GiB disk. Its only project mount is `supabase/tests`, read-only, so the CLI's pg_prove container can see fixtures. It does not mount the home directory, modify SSH configuration, or switch the user's active Docker context. The engine socket is `$HOME/.colima/sochron1k/docker.sock`. Nothing is installed into the user's shell profile.

Prefix Docker-dependent commands on this workstation with `bash scripts/with-local-docker.sh`. This selects only that runtime and socket:

```bash
bash scripts/with-local-docker.sh docker version
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local
```

To restart this already-created local VM if stopped:

```bash
bash scripts/with-local-docker.sh colima start sochron1k --vm-type vz --cpus 4 --memory 8 --disk 40 --mount "$(pwd -P)/supabase/tests" --ssh-config=false --activate=false --binfmt=false
```

The wrapper does not start the VM or install tools. Other workstations can use their own verified local engine without the wrapper. No VPS, cloud account, or MT5 target is selected.

## Verify

Run the static checks first:

```bash
npx -y -p node@24.21.0 npm run check:compose:static
```

Then run the local build and smoke verifier:

```bash
npx -y -p node@24.21.0 npm run check:compose:local
```

The local verifier performs a no-cache build and owns a unique project, image tags, loopback port and journal volume for each invocation. It checks effective port publication, network membership and runtime hardening, requests the web page and proxied health, writes a marker as the API user, recreates the API, verifies the marker and proxy again, then stops only its own stack. It retains `sochron-verify-<id>_journal`, images, and `output/compose/<project>/result.json` plus build logs. It does not touch the manual development stack or volume. Retained artifacts consume disk space; inspect exact names before any separately authorized removal.

Results record source revision, dirty state, input hashes, runtime versions, image identities, UTC times, failed stage/error type when applicable, and cleanup result. A dirty-source result is not evidence for an arbitrary later revision. A Unix socket check rejects ordinary remote endpoints but does not establish trust in a forwarded socket.

## Manual observation

For interactive observation without the verifier's automatic shutdown:

```bash
docker compose up --build --detach --wait
curl --fail http://127.0.0.1:8080/api/health
docker compose ps
```

Expected health fields are `trading_mode: demo`, `auto_trading_enabled: false`, and `execution_ready: false`. The web console is at `http://127.0.0.1:8080/`.

Stop the services without deleting the journal volume:

```bash
docker compose down
```

Do not use `docker compose down --volumes` as a routine stop command. Deleting the named volume is a destructive recovery action and requires a separately verified backup or an explicit decision that the local evidence can be discarded.

## Evidence limits

- An HTTP 200 proves process and proxy health only.
- A surviving volume name does not prove journal contents, command recovery, or MT5 reconciliation.
- No API port is published to the host.
- The API joins only the internal network. The web proxy also joins an ingress bridge; its outbound connectivity is not blocked by this topology. Loopback binding limits inbound exposure, not egress.
- VPS, Wine, MT5, network-loss, backup/restore, and multi-day burn-in evidence remain separate future gates.
