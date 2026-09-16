# SCN-003 Local Runtime Topology

## Contract

| Field | Value |
| --- | --- |
| ID | SCN-003 |
| Version | 1.0 |
| Owner | Project owner; technical implementer not yet named |
| Parent project | Sochron1k |
| Current state | Local arm64 build/runtime checks passed; MT5, VPS and unattended Demo remain outside this gate |
| Done scope | Reproducible local API/web topology with secure defaults; MT5 and VPS readiness remain separate gates |
| Risk tier | High assurance |
| Evidence base | Blueprint v1.1 sections 05 and 19-23, architecture and risk register at revision `a23bd58` |

## Goal and user outcome

Provide a reviewable container boundary for the current API and monitoring console so a developer can build and run the same Demo-only prototype locally without exposing the API or inventing MT5 readiness. The topology must remain deliberately incomplete until the executor, worker, recovery, and deployment gates exist.

## Scope

- Pin every base image by release tag and multi-platform digest.
- Build the FastAPI service from the committed Python lockfile and the web bundle from the committed npm lockfile.
- Serve the web bundle through an unprivileged reverse proxy and route `/api/` only to the internal API service.
- Bind the web port to loopback by default; do not publish the API port.
- Run containers as non-root with read-only roots, dropped Linux capabilities, `no-new-privileges`, health checks, bounded shutdown, and explicit persistent journal storage.
- Force `TRADING_MODE=demo` and `AUTO_TRADING_ENABLED=false`; the API must report auto trading off even if a local environment variable requests otherwise.
- Add static checks and a Docker-dependent build/config/smoke verifier.

## Exclusions

- An MT5/Wine image, broker credentials, a real bridge, or a Demo send.
- A worker process, background synchronization, AI provider, or Supabase service inside this Compose file.
- TLS certificates, public DNS, firewall mutation, VPS deployment, or a hosted release.
- Treating an HTTP health response as execution readiness.

## Acceptance criteria

### AC-01 Reproducible images

Given the candidate revision and a compatible container engine, when both images build without cache, then Python, Node.js, nginx, uv, Python dependencies, and npm dependencies match their committed versions and base image digests.

### AC-02 Secure process boundary

Given the rendered Compose configuration, then both services run as non-root with read-only root filesystems, all capabilities dropped, `no-new-privileges` enabled, and only the web port is published to loopback.

Runtime inspection must confirm the effective port mapping, not only the requested host configuration. The API joins only the internal network. Only the web proxy joins a second bridge for loopback publication; its outbound connectivity is not claimed to be blocked (ADR-003).

### AC-03 Demo lock

Given hostile local environment values including live mode or auto trading enabled, when the stack starts, then the container configuration and API response remain Demo-only, auto trading remains off, and execution readiness remains false.

### AC-04 Truthful health and routing

Given the API process is healthy, when the owner loads the web origin and `/api/health`, then the static console and proxied health response are available; neither response claims MT5, feed, or execution readiness.

### AC-05 Durable local boundary

Given an API restart, when the container is recreated, then the named journal volume remains attached; this alone does not prove command or broker-state recovery.

### AC-06 Runtime verification

Given a Docker-compatible engine, when the verifier renders configuration, builds images, starts the stack, runs health assertions, restarts the API, and shuts down cleanly, then the exact outputs and image identities are retained for the candidate revision.

The verifier must own a unique Compose project, image tags, loopback port and journal volume. It must refuse a non-local Docker endpoint, preserve existing developer stacks, and verify a marker written by the API user survives container recreation. It must verify the proxied health endpoint again after recreation and retain redacted results. Cleanup may stop only the verifier's own project and must preserve its journal volume.

## Required verification

| Acceptance | Verifier required before implementation is complete | Current result |
| --- | --- | --- |
| AC-01 | No-cache multi-platform-compatible image builds and in-container version checks | PASS on local arm64: digest-pinned builds and frozen dependency installs; Python 3.14.7 and nginx 1.30.5 checked in running images. amd64 execution NOT RUN |
| AC-02 | Rendered Compose assertions plus runtime user/capability/read-only checks | PASS locally, including effective loopback port mapping and API-only internal membership |
| AC-03 | API negative tests plus rendered environment assertions | PASS locally: hostile inherited live/auto values do not change rendered configuration or container health |
| AC-04 | Loopback HTTP smoke checks for `/` and `/api/health` | PASS locally before and after API replacement |
| AC-05 | Named-volume identity before and after API recreation | PASS locally: API-user marker survives replacement on the invocation-owned volume; broker/journal recovery is not implied |
| AC-06 | End-to-end local runtime verifier | PASS locally, with invocation-owned cleanup and retained evidence |

Initial passing run: `output/compose/sochron-verify-aeb3e6843bd4/result.json`, 2026-09-16 21:24 UTC (17 September Asia/Bangkok), base `55723ab` plus recorded dirty input hashes. Verifier: `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`; engine 29.5.2 arm64, Compose 5.5.1. Re-run on the saved candidate before delivery; these results do not grant VPS or Demo execution readiness.

## Authorization

The owner's continuing setup request covers a user-scoped local Colima/Docker runtime and local verification. The selected runtime uses a dedicated profile without host home-directory mounts or changes to the active Docker context. Deploying to a VPS, publishing images, changing firewall/DNS, paid resources, and operating MT5 retain their separate authorization requirements.

## Recovery

- Failed builds or health checks leave Auto Trading off and do not authorize bypassing health dependencies.
- A container restart is never evidence that open positions or unknown commands reconciled; that requires the SCN-001 executor boundary.
- Image tag or digest changes require a fresh admission review, rebuild, and smoke evidence.

## Definition of Done

- AC-01 through AC-06 pass on the exact revision and environment.
- No Critical or High issue remains in the affected container boundary.
- MT5/VPS implementation and observed Demo behavior remain reported separately from local container readiness.
