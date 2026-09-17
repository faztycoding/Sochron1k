# Native M1 sync worker (SCN-008)

## Status and authority

Optional backend worker, not enabled by default or included in API/web Compose. AC-03/04
have source/journal evidence; AC-05 now has config/HTTP/runner tests against fake
HTTP and real loopback sockets/processes. AC-06 now has
[actual local Supabase/Auth/PostgREST evidence](../verification/SCN-008-local-sync.md),
including process termination after commit and read-back without a second send.
An [internal Python artifact](../verification/SCN-008-worker-package.md) now provides
an installed `sochron-sync` command, verified outside the source checkout. This is
part of AC-07. An opt-in [Linux container](worker-container.md) now has local
replacement/reconciliation evidence, not target/backup delivery or release approval.
Hosted setup, destination credentials,
target deployment and full Demo gates are NOT READY. No MT5/execution operation
exists in this worker. Starting it does not enable Auto Trading.

Do not run against a hosted destination without explicit authorization for that
project and the data transfer. No such operation was performed while developing
this component. The key has backend service-role authority and bypasses RLS;
it is not an owner-limited token. The worker pins one owner/archive in its code
path, but those attributes do not reduce the key's privileges outside this process.

## Configuration

Use pinned Python 3.14.7. For source development using the project `.venv`, both
`services/api/src` (shared domain types only) and `services/worker/src` must be on
`PYTHONPATH`. The installed artifact below needs neither source path.

## Build and verify the internal artifact

Use uv 0.12.15. Build dependencies are locked separately; production dependencies
are unchanged. From the repository root:

```bash
uv sync --frozen --all-groups
.venv/bin/python scripts/check-worker-package.py
```

If uv is not on PATH, set `SOCHRON_UV` to its absolute executable path for the
verifier. The verifier checks its version. It creates a unique ignored directory
under `output/worker-package/`, containing a wheel, sdist, hash-locked production
`requirements.txt` and `result.json`. It checks exact contents, builds a matching
wheel directly and from the sdist, and installs into a disposable fresh environment
outside the checkout. It exercises the installed command against a loopback fixture,
including SIGTERM/UNKNOWN/restart. Test environment, keys and fixture journals are
removed afterward; artifact/evidence files are retained. No owner service is enabled.

`uv sync` intentionally does not install project console scripts in the developer
environment (`tool.uv.package=false`). Its entry-point warning is expected; use
the installed wheel or the source commands below, not an assumed `.venv/bin/sochron-sync`.

For a reviewed artifact with result PASS, transfer its wheel, requirements and
evidence together to the approved POSIX host. Verify SHA-256 against the retained
manifest and trusted source revision first. Create a new version-specific environment,
not an in-place upgrade of an active worker. Example placeholders below must be
replaced with exact reviewed paths; these do not select or authorize a hosted target:

```bash
uv venv --no-project --python /absolute/path/to/python3.14 /absolute/new/release/venv
uv pip install --python /absolute/new/release/venv/bin/python --require-hashes --only-binary :all: -r /absolute/artifact/requirements.txt
uv pip install --python /absolute/new/release/venv/bin/python --no-deps --no-index /absolute/artifact/sochron1k-0.1.0-py3-none-any.whl
/absolute/new/release/venv/bin/sochron-sync --help
```

The verifier has exercised these installation operations locally, not on Linux or
the target host. The wheel contains the API domain and worker packages, not a
Python interpreter, frontend, credentials or database state. It is not published
to a package registry. Do not use version `0.1.0` alone as artifact identity.

After private configuration is prepared under the authority above, substitute
`/absolute/new/release/venv/bin/sochron-sync` for the source prefix in init/status/run
commands below. Importing/installing does not initialize a journal. Start `run`
only explicitly, stop with SIGINT/SIGTERM and inspect the exit/status. Do not add
an automatic restart loop after retry exhaustion. Preserve the same source/state
paths during an application update; do not initialize another journal to evade
UNKNOWN or quarantine. Before any rollback, verify old code understands the current
schema/config and rehearse recovery separately; an old wheel is not a state backup.

## Private configuration

`SOCHRON_SYNC_CONFIG_FILE` contains only an absolute config-file path. No variable
means DISABLED, with no archive/journal/network access. An explicit private JSON
file containing only `{"enabled":false}` also disables the worker. `.env.example`
is documentation, not an automatically loaded config. There are no secret/URL CLI
arguments and no environment service-key fallback.

Enabled JSON requires exactly these fields (replace placeholders using verified
local capture metadata; do not guess an archive UUID, identity or broker offset):

| Field | Value |
| --- | --- |
| `enabled` | boolean `true` |
| `source_directory` | Existing SCN-007 private archive directory |
| `state_directory` | Separate existing empty private directory for initial setup |
| `archive_id` | Canonical UUID of the source archive |
| `identity` | Exact object: `executor_id`, `account_ref`, `server`, `currency`, `margin_mode`, `symbol` |
| `offset_seconds` | Verified broker UTC offset, integer seconds divisible by 60 |
| `chart` | Exact `offset_valid_from_server_s` and `offset_valid_until_server_s` interval |
| `owner_id` | Canonical Supabase owner UUID for the target project |
| `origin` | Canonical `https://project.supabase.co` or approved custom DNS origin; local `http://127.0.0.1:54321` |
| `service_key_file` | Absolute path to a separate owner-private credential file |

Config and key files must be regular, owned by the current UID, single-link and
mode 0600 or stricter; their containing directory must be owner-only (0700).
All paths must be canonical absolute paths without symlink components. State/source
directories are separately validated by their readers. Keep config/key outside the
initially empty state directory. Never commit them or put them in chat/logs/browser.

The key file contains only a backend `sb_secret_…` key, or a legacy service-role
HS256 JWT with an unexpired numeric expiry, optionally followed by one newline.
Publishable, anon and authenticated-user keys are denied. Local JWT parsing only
checks syntax/role/expiry: Supabase authenticates the actual key. For secret keys
the request uses `apikey`; legacy keys additionally use `Authorization: Bearer`.
See [Supabase API key roles](https://supabase.com/docs/guides/getting-started/api-keys).

HTTPS uses default certificate verification. No custom CA, TLS-disable setting,
environment proxy, redirect, URL userinfo/path/query/fragment, Unicode hostname,
nondefault HTTPS port or IPv6 origin is supported. Local HTTP requires exactly
127.0.0.1 with a canonical port 1024-65535. Origin is a trusted operator choice,
not automatic destination discovery or a promise of DNS/IP allowlisting.

## Explicit commands

Set the environment path privately before invoking. Do not place a key in the
command or environment. From the repository root:

```bash
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker init
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker status
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker run --once
PYTHONPATH=services/api/src:services/worker/src .venv/bin/python -m sochron_worker run
```

`init` is local only, refuses nonempty/partial state and never resets an existing
journal. `status` needs source/config/journal, but no key or network; it reports
local bookkeeping, not current destination truth. Both take the single-writer
lock: stop an active worker before using them. A live `run` prints JSON status
after each completed step, including cursor, pending state, attempts and journal
quota warning. No account identity, key, payload or remote error body is printed.
`IDLE` means no unsynced source rows, not a healthy broker or complete dataset.

`run --once` performs one bounded driver step, which can send then read back, or
only reconcile a previous UNKNOWN batch. A returned PREPARED state deliberately
does not send again in that same recovery step. Normal run polls serially every
2 seconds after IDLE/VERIFIED and backs off 1, 2, 4, 8 seconds on unresolved work,
then exits after the fifth consecutive unresolved step. There are at most five
persisted sends per batch across process restarts. No automatic supervisor restart
should bypass this review boundary. A final UNKNOWN may still reconcile after the
send budget, but a missing batch cannot be sent a sixth time.

Exit 0: disabled/local init/status or successful single step. Exit 2: config,
source, journal, quarantine, persisted-send-budget or unexpected failure. Exit 3:
unresolved single step or consecutive retry budget exhausted. SIGINT/SIGTERM emits
STOPPED and exits 130 without clearing pending state. These exit codes are not
Demo acceptance. `--help` describes syntax without accessing configuration.

Only the two native M1 RPCs are reachable through the transport. Request/response
JSON is capped at 262,144 bytes; compression is denied. HTTPX inactivity timeouts
are 2 seconds and an outer asyncio deadline is 10 seconds per request. A driver
step can contain both store and read-back, plus local disk work; this is not a
10-second whole-step or filesystem deadline. No request is automatically replayed
inside HTTPX. A timeout/lost response/HTTP error leaves UNKNOWN; known native
conflicts or malformed successful JSON read-back quarantine. ACK alone is not
evidence that rows were synchronized.

## Stop, reconcile and recover

1. Stop with SIGINT/SIGTERM; retain source and worker directories, including WAL
   state. Do not unlink `sync.lock`, delete `sync.sqlite3`, edit its rows, or run
   `init` to clear a failure. Configuration/key changes take effect only after
   restart, not by hot reload.
2. Inspect local status after the worker exits. UNKNOWN means the write may have
   committed. Once destination access is restored, `run --once` independently
   reads it before any resend. Do not infer completion from an HTTP ACK or cursor
   alone when investigating external changes.
3. On QUARANTINED, source/binding drift, corrupt/missing state or exhausted sends,
   stop and retain evidence. Compare the pinned archive and exact destination data
   under approved access. There is intentionally no reset/unquarantine command.
   Any repair, new binding, restore or reviewed retry-budget change is a separate
   operation; do not make a second worker directory to evade the guard.
4. A missing/invalid credential can be corrected in its private file after stopping;
   restart with the same owner/archive/origin. A different destination/owner is not
   credential rotation and will not silently reuse the journal.

The 64 MiB main-journal quota is not a filesystem/WAL cap. At warning thresholds
70%/85%, plan reviewed export/retention and verify free disk. Never prune ledger
rows automatically. Consistent backup/restore, target-host retention and measured
RPO/RTO are still required before unattended deployment; copying only a live
SQLite main file is not a verified backup.

## Outstanding delivery

Next: admit a fixed SQLite runtime (R-015), then complete recovery gates (AC-07).
Local AC-06 testing
does not establish installed-service or target-host behavior. Still required from the
owner: chosen Supabase project/owner, broker Demo server/account specifications,
MT5 host/build, and deployment/domain/alert/budget decisions. Credentials go only
through the approved private secret channel. No paid/cloud/broker action is implied.
