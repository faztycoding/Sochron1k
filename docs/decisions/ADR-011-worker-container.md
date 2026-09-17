# ADR-011 Opt-in Linux sync worker container

2026-09-17. SCN-008 AC-07 local delivery; no hosted enablement or deployment.

Build the ADR-010 wheel in a digest-pinned Python builder and install hash-locked
runtime dependencies into a separate clean virtual environment. Copy only that
environment and an artifact hash manifest into the runtime. Reuse the admitted
Python base; no new runtime dependencies. Default invocation reports DISABLED.

Keep `compose.worker.yaml` separate from API/web Compose. It has no config,
mounts, published ports, network or automatic restart. An operator overlay must
explicitly supply private configuration and reviewed networking before `run`.
Retry exhaustion must not trigger an automatic restart loop. No worker healthcheck
invokes status because that command takes the journal's exclusive lock.

Use UID/GID 10001, private 0700 directories and 0600 files, config volume read-only,
and separate persistent source/state local volumes on the same Docker host. Source
is mounted read-write for SQLite WAL sidecar creation across writer restarts;
the source adapter still opens mode=ro/query_only and cannot write application
tables through that connection. This does not protect source data from a compromised
worker with filesystem access. A read-only mount only works under additional WAL
sidecar conditions; immutable=1 is incorrect for a changing archive. Do not use
network filesystems. Preserve exact container paths through replacement.

The local verifier uses a separate synthetic receiver sharing only a private
loopback network namespace with the worker. Neither container has egress or host
ports. The receiver fixture/image is not the delivered runtime, and its generated
key exists only in a private runtime volume. This verifies Linux packaging and
replacement recovery, not Supabase roles, MT5, target-host or power-loss behavior.

References: [Compose service controls](https://docs.docker.com/reference/compose-file/services/)
and [SQLite read-only WAL conditions](https://sqlite.org/wal.html#read_only_databases).
