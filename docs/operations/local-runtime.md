# Local API and Web Runtime

## Status

The committed topology is a Demo-only local candidate. Static structure and API safety tests pass. Image build, container hardening, proxy smoke, and restart/volume checks remain blocked until a Docker-compatible engine is installed and running.

This runbook does not start MT5, place an order, link Supabase, expose a public port, or prove VPS readiness.

## Prerequisites

- Node.js 24.21.0 and npm 11.19.0.
- A Docker-compatible engine with Compose v2.
- Free loopback port 8080, or a different `SOCHRON_WEB_PORT` value.
- No broker or cloud credentials are required.

The admitted base images and multi-platform digests are recorded in [container-images.lock.md](container-images.lock.md).

## Verify

Run the static checks first:

```bash
npx -y -p node@24.21.0 npm run check:compose:static
```

Then run the local build and smoke verifier:

```bash
npx -y -p node@24.21.0 npm run check:compose:local
```

The local verifier performs a no-cache build, starts both services, checks non-root/read-only configuration, requests the web page and proxied health endpoint, restarts the API, confirms the named volume identity, and stops the services. It preserves the named volume `sochron1k_journal_data`.

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
- The internal network intentionally has no external egress in this candidate because no Supabase, AI, or MT5 bridge integration is present.
- VPS, Wine, MT5, network-loss, backup/restore, and multi-day burn-in evidence remain separate future gates.
