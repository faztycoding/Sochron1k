# SCN-008 AC-07 local Linux worker container

2026-09-17. Base `edbbd89d9cf0031ed24b28d2074e10c16d37c1e4`, dirty candidate.
Final container run: `2026-09-17T06:53:15.343971+00:00` through
`2026-09-17T06:53:35.756475+00:00`. Local Colima Linux arm64,
Docker 29.5.2, Compose 5.5.1; Python 3.14.7, SQLite 3.40.1 in the image.

## Outcome and limit

Opt-in container packaging and functional replacement checks PASS. The default
API/web topology is unchanged; it does not start a worker. No owner processes,
Supabase stack, MT5, hosted project or deployment were changed. No application
Python module or dependency lock changed. The test uses synthetic chart fixtures
and a SQLite-backed HTTP oracle, **not actual PostgREST**.

Full AC-07 and full Demo remain incomplete. In particular **R-015 is OPEN**:
the image links Debian `libsqlite3-0 3.40.1-2+deb12u2`, unlike the workstation's
SQLite 3.53.1. Upstream documents a WAL-reset corruption race in older SQLite,
fixed in 3.51.3+ and selected backports. This binary's patch admission is not
verified. These functional checks do not reproduce/exclude that rare race or
authorize release. A verified fixed runtime and affected API/worker recovery tests
are required next. See [SQLite's advisory](https://sqlite.org/wal.html#walreset)
and the [image lock](../operations/container-images.lock.md).

## Oracles and observed results

- Default Compose run exits DISABLED without source/config/state mounts, network or
  ports. Inspect proves UID/GID 10001, init, read-only root, ALL capabilities dropped,
  no-new-privileges, no auto-restart, 256 MiB/64-process limits and bounded logs.
- Both installed package directories are in `/opt/worker` site-packages, no
  PYTHONPATH/source checkout. All 22 module hashes equal repository bytes. Every
  installed distribution version matches the lock; pytest/Hatchling/uv/Ruff/
  Hypothesis are absent from the runtime environment. The runtime retains the
  artifact manifest, not the wheel/source/build environment.
- Private local source/state/config volumes initialize successfully as UID 10001.
  Config is read-only in the worker; source/state mounts are writable. Source
  application connection remains mode=ro; table fingerprints stay unchanged.
  Init/status make no receiver calls; duplicate init and a competing journal
  reader/writer are denied.
- The receiver durably accepts one store and withholds its response. Compose
  SIGTERM produces STOPPED/exit 130. Independent SQLite inspection finds UNKNOWN,
  attempt 1, receipt cursor 0. The worker container is removed/recreated using the
  same volume identities and paths, independently reads back, exits VERIFIED/0,
  and a subsequent invocation is IDLE. Final oracle: one store, one read, one
  VERIFIED ledger batch, attempt 1, cursor receipt 1. No duplicate send.
- Deliberately unsafe config permissions return SYNC_CONFIG_INVALID without any
  receiver or journal change. Captured worker logs contain no generated key.
- Fixture network is `none`; worker shares only that container's loopback namespace.
  No host socket/bind mount/port or external destination is supplied. This does
  not test HTTPS, remote authentication, MT5, concurrent API capture, power loss,
  target-host recovery or backups. Source RW mount is not a security sandbox against
  a compromised worker; see ADR-011.

## Commands and evidence identity

- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`: PASS, six check groups, cleanup exit 0.
- `.venv/bin/ruff check scripts/check-worker-container.py tests/fixtures/worker_container_receiver.py`: PASS.
- `.venv/bin/pytest -q`: 427 PASS (workstation, not container test suite).
- `bash scripts/check-scn-001-local.sh`: 427 PASS again, Ruff and secret scan PASS.
- `npx -y -p node@24.21.0 npm run check:compose:static`: PASS; existing topology and secret scan.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`: PASS.
- `python3 scripts/check-no-secrets.py`, `git diff --check`: PASS; final scan 206 text files.

Local result: `output/worker-container/sochron-worker-b0b827059fb7/result.json`.
It retains every source/config/verifier/fixture input hash, runtime distribution
versions, image identities, seed hash, checks and cleanup status. Main identities:

| Item | SHA-256 |
| --- | --- |
| Candidate image | `f5b6ed52894fd4f71f9a95e2348aebab8d221b91dfad816b9e51adfee0c85ee5` |
| Worker Dockerfile | `785fdfd564211baf57e82e712b6372b151fa514b1952dca72d43f88b756bb6fe` |
| Worker Compose | `f839c3c9e29d2baa20b92539add5873edbd1da98dc7ef0423e4c94be13a9cd80` |
| Container verifier | `3933404442798a3d62100156c113310961e77ed9fb5cf00034ebe38f3de9f6e0` |
| Fixture receiver | `9c9e7c05ead1ebdc3eb606f59c843d38ad91d218da4781d51103019bb0f497cf` |
| Built wheel | `a5ef5a1d31325904aa5e01546f57742ea8a7d7e1f1900ffb084cc1d41bbec60c` |

The commit containing this report identifies the candidate. No tested source,
Dockerfile, Compose or verifier changed after this successful run. Earlier attempts
correctly failed: an unquoted comma split the tmpfs YAML item; a macOS temporary
directory needed canonicalization before archive creation. Both were fixed without
weakening runtime guards. Formatting errors were corrected before final checks.

Scoped containers were removed, generated test key deleted, and synthetic volumes,
images and logs retained locally (names in result.json). No operator data was removed.
These retained volumes are test evidence, not a backup. No multi-platform, target,
frontend/browser or fresh real-Supabase test is claimed for this change.

The [operations skill](../../tooling/skills/sochron-vps-operations/SKILL.md) guided
explicit activation, volume identity and release limits. The
[risk/recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md) guided
UNKNOWN persistence and independent read-back before resend. See
[runbook](../operations/worker-container.md) and [ADR-011](../decisions/ADR-011-worker-container.md).
