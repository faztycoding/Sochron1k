# SCN-008 AC-05 private transport and runner

2026-09-17. Base `33afc944835eccb844056ec4da7dd49fb5e47b93`; candidate dirty
during verification. Python 3.14.7, SQLite 3.53.1, HTTPX 0.28.1, pytest 9.1.1,
Ruff 0.16.8 on macOS 26.6.2 arm64. No new dependency or schema migration.
All identities, keys and bars are generated fixtures. Tests use temporary SQLite
files, HTTPX MockTransport and ephemeral 127.0.0.1 HTTP servers. No actual Supabase
stack, hosted project, MT5 account, deployment or paid resource was used this turn.

## Outcome and acceptance

AC-05 is implemented with local transport/config/runner evidence. The worker reads
only an explicit private config-file path and a separate private service-key file.
It pins source/archive/owner/origin, rejects unsafe paths/permissions/links and
invalid/duplicate/oversized configuration, and is DISABLED without configuration.
No secret CLI/environment-value option exists. Local init/status require no key
or network; both enforce the journal's exclusive lock and integrity checks.

Only fixed native store/read RPCs are sent, with JSON arguments matching the
committed SQL signatures. Requests and responses are bounded to 262,144 bytes;
compressed responses, redirects and environment proxies/CA overrides are denied.
The client uses default TLS verification, 2-second inactivity timeouts, a 10-second
outer asyncio deadline and no transport retry. New clients do not carry cookies
between calls. A store ACK still requires a separate committed-state read-back.

Serial run polls after success/idle, backs off 1/2/4/8 seconds for unresolved steps,
and exits after the fifth consecutive unresolved step. Five sends per batch are
persisted across restarts. UNKNOWN at the send limit may still reconcile, but a
sixth store is denied. SIGTERM/SIGINT do not reset state. Fixed JSON status/error
output omits identities, paths, credentials and upstream bodies.

AC-06 actual local Supabase/PostgREST end-to-end/owner-isolation/crash acceptance
remains NOT RUN. AC-07 has an initial operator runbook but is not complete target
delivery. Full Demo remains NOT READY; Auto Trading is disabled. No worker config
was installed for the owner, no service enabled, and no manual web/API process
was changed. This evidence does not certify a hosted key, TLS endpoint or broker.

## Exact checks

- `.venv/bin/pytest -q tests/test_sync_transport.py tests/test_sync_driver.py`:
  **113 PASS** (67 transport/config/runner, 46 existing journal/driver).
- `bash scripts/check-scn-001-local.sh`: **425 PASS**, Ruff and secret scan PASS.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: PASS.
- `env -u SOCHRON_SYNC_CONFIG_FILE PYTHONPATH=services/api/src:services/worker/src
  .venv/bin/python -m sochron_worker run --once`: exit 0, DISABLED,
  `execution_ready=false`, `auto_trading_enabled=false`.

Tests inspect exact RPC URLs, owner/archive arguments, original decimal/time
payloads, modern-key versus legacy bearer headers and independent read-back.
Responses setting cookies do not affect the next request. Redirects 301/302/307/308,
400/401/403/404/429/500/503, unknown conflicts, oversized announced/streamed bodies,
compressed data and duplicate JSON keys fail without cursor advancement. Known
native conflicts and malformed successful JSON read-back quarantine. Oversized
requests and wrong archive IDs produce zero HTTP calls.

Unsafe-origin fixtures cover external cleartext, userinfo, path/query/fragment,
Unicode/case ambiguity, backslashes, control characters, invalid labels/ports,
localhost aliases and numeric-host HTTPS. Config/key fixtures cover wrong roles,
expired JWTs, publishable keys, header-injection bytes, permissive mode, symlink,
hardlink, public parent, duplicate/unknown fields, invalid offset, numeric disabled
flag and same source/state directory. Syntax tests are not cryptographic key
authentication. Real Supabase authentication remains an AC-06 oracle.

A continuously dripping async response stays below socket inactivity yet exceeds
the outer test deadline. Cancellation closes the response and leaves UNKNOWN.
This uses a shortened injected deadline to test the same timeout mechanism, not
a claim of measured ten-second behavior on the target host.

A real loopback HTTP server accepts the exact store body then disconnects without
any HTTP response. The driver leaves UNKNOWN; its next step reads the server's
stored snapshot, reaches VERIFIED and creates only one observed store effect.
Hostile HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY and nonexistent SSL_CERT_FILE
values do not redirect/block that local request. Default HTTPS verification is
configured in code; no hosted/TLS handshake acceptance is claimed by HTTP fixtures.

A separate CLI process initializes its fixture state and runs a real HTTP request.
After the server accepts it, the test sends SIGTERM while the response is withheld.
The process exits 130, prints STOPPED without a traceback/key, and SQLite retains
UNKNOWN/attempt=1/cursor=0. A new CLI process independently reads the server,
reaches VERIFIED and does not store again. This is actual process/HTTP recovery,
not power-loss evidence; the destination in this case is an in-memory test server.
The preceding AC-04 test separately uses a durable SQLite destination/process exit.

Other tests verify bounded backoff, single-step exit behavior, persisted send
limits after reopening, successful reconciliation at the final send limit, and
init/status with the service-key file absent and a forbidden-network constructor.
Init cannot reset an existing journal. CLI usage/config failures do not echo even
a deliberately supplied generated key argument. Initial Ruff formatting/import
findings were corrected; no assertion/gate was relaxed.

## Candidate hashes

SHA-256:

- `services/worker/src/sochron_worker/sync_config.py`:
  `9b705d01071a71f093e8a1fe4a57a81a0d42ddf35abeb488c5ba3394d6a2fb61`
- `services/worker/src/sochron_worker/sync_http.py`:
  `982598175ac3b23f03dd69e017025c33ae0c921c26a6f122fe0502d54d927266`
- `services/worker/src/sochron_worker/__main__.py`:
  `3512e7c813f7cece781217cefc4be930d83165e5ecf755d0f1fb423cb80c7615`
- `services/worker/src/sochron_worker/sync_driver.py`:
  `ae25582262bc822be40b509c9368a3ab2f11f194e222186f887924f654dfa79c`
- `tests/test_sync_transport.py`:
  `e4a988e6b6c068d64ad7f461ce4e98061748e8d4f17f971cc9db103aa159603b`

## Documentation and remaining boundaries

The Supabase skill is represented by the pinned installed registry in
[agent skills](../tooling/agent-skills.md); it prompted checking
the current [changelog](https://supabase.com/changelog) and
[key roles](https://supabase.com/docs/guides/getting-started/api-keys). The self-hosted
gateway change concerns deployment topology; this client binds only the explicit
origin and fixed REST paths, not Kong/Envoy container names. The current local CLI
is not upgraded here. Secret keys use `apikey`; legacy service-role keys also use
bearer authorization. No claim is made that either fixture key is accepted by a
real server. The [PostgREST RPC contract](https://docs.postgrest.org/en/v14/references/api/functions.html)
informs JSON argument mapping. [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
are per inactivity phase, so an outer
[asyncio timeout](https://docs.python.org/3.14/library/asyncio-task.html#asyncio.timeout)
is required to bound a dripping response.

The [sochron-risk-recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md)
guided UNKNOWN retention, persisted attempt budgets and interruption tests. Private
Python/config boundaries do not defend a compromised same-user host. A service
key remains privileged outside this worker. No DNS/IP firewall, whole-step/disk
deadline, backup/restore, Windows worker or network-filesystem guarantee is implied.

Next: exercise the real local Supabase RPC/auth/roles with synthetic users and
immutable high-precision native rows, lost HTTP response and process restart.
Then complete packaging/operator evidence without enabling a hosted destination
or changing the original full Demo gates.
