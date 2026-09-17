# Container Image Lock

Verified against the upstream registries on 2026-09-16 UTC. Tags document the intended release; digests are the enforced multi-platform identities in the Dockerfiles.

| Purpose | Image tag | Multi-platform digest |
| --- | --- | --- |
| API and worker build/runtime | `python:3.14.7-slim-bookworm` | `sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f` |
| Web build | `node:24.21.0-bookworm-slim` | `sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553` |
| Web runtime | `nginx:1.30.5-alpine3.24` | `sha256:25820c39dba41369486df729ad6697de2fab631ca809e0503e1d1e0c73d9a232` |

Digest admission is verified metadata, not a vulnerability scan or a successful local build. Changing any tag or digest requires fresh upstream verification, a clean rebuild, and runtime smoke evidence.

2026-09-17 worker runtime inspection: Python links SQLite 3.40.1, Debian package
`libsqlite3-0 3.40.1-2+deb12u2`. This is not the workstation's SQLite 3.53.1.
Upstream documents a [WAL-reset corruption race](https://sqlite.org/wal.html#walreset)
in older versions, fixed in 3.51.3+ and selected backports. Patch admission for this
Debian binary is **NOT VERIFIED**; functional container tests do not resolve it.
R-015 blocks target release until a fixed runtime is pinned and affected API/worker
SQLite checks are rerun. Do not deploy this candidate on the strength of its digest.
