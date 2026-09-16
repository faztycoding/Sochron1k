# ADR-003 Local proxy ingress and isolated verification

Status: accepted for local development only, 17 September 2026.

## Evidence and decision

On Docker Engine 29.5.2 arm64, the initial SCN-003 topology started healthy API and web containers but did not publish the requested loopback port. `HostConfig.PortBindings` contained the request while `NetworkSettings.Ports["8080/tcp"]` was null. Host HTTP failed with connection refused (run `sochron-verify-c22da95a705e`, base `55723ab`, dirty candidate).

Keep the API on `app_internal` only. Attach the unprivileged web proxy to that internal network and a separate bridge, `web_ingress`, with only `127.0.0.1:<port>:8080` published. This follows Docker's frontend/backend network pattern. Do not expose API ports, enable host networking, or change host firewall rules. The proxy may have outbound connectivity; this is not an egress-denial control. It receives no secrets and has a read-only root, no capabilities, and no execution authority.

Use nginx's shared upstream and Docker DNS re-resolution so an API container replacement does not leave a stale backend address. Wait for API health before starting the web proxy.

## Verification and recovery

Inspect effective port bindings and network membership, then request the host-facing web page and proxied health before and after API replacement. Verify a marker written by the API user survives on the same named volume. Each verifier invocation owns unique project, images, port, and volume; cleanup stops only that invocation and retains its data volume. Reject non-Unix Docker endpoints; this is a guardrail, not proof that an arbitrary forwarded socket is local.

Reverting to the original single-network topology reintroduces the observed connectivity failure and is not a valid operational rollback. Stop the local stack without deleting its volume if verification fails. MT5, public hosting, TLS, VPS, and unattended Demo remain outside this decision.

References: [Docker networking](https://docs.docker.com/engine/network/), [port publication](https://docs.docker.com/engine/network/port-publishing/), [nginx upstream resolution](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#resolve).
