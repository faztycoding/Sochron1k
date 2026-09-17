# Container Image Lock

Verified against the upstream registries on 2026-09-16 UTC. Tags document the intended release; digests are the enforced multi-platform identities in the Dockerfiles.

| Purpose | Image tag | Multi-platform digest |
| --- | --- | --- |
| API and worker build/runtime | `python:3.14.7-slim-bookworm` | `sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f` |
| SQLite compiler stage (admitted 2026-09-17) | `python:3.14.7-bookworm` | `sha256:ecac9e212daacda8a702eae372fceebc0ee36f5805abe087880367e8d061fa5b` |
| Web build | `node:24.21.0-bookworm-slim` | `sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553` |
| Web runtime | `nginx:1.30.5-alpine3.24` | `sha256:25820c39dba41369486df729ad6697de2fab631ca809e0503e1d1e0c73d9a232` |

Digest admission is verified metadata, not a vulnerability scan or a successful local build. Changing any tag or digest requires fresh upstream verification, a clean rebuild, and runtime smoke evidence.

2026-09-17 original base inspection: Python linked SQLite 3.40.1, Debian package
`libsqlite3-0 3.40.1-2+deb12u2`, not the workstation's SQLite 3.53.1.
Upstream documents a [WAL-reset corruption race](https://sqlite.org/wal.html#walreset)
in older versions, fixed in 3.51.3+ and selected backports. Patch admission for this
Debian binary is **NOT VERIFIED**; functional container tests do not resolve it.
The current API/worker Dockerfiles now add upstream SQLite 3.53.4, built in the
compiler stage above. The official archive/source hashes, source ID and compiler
identity are pinned in `services/runtime/sqlite.lock.json`. Python's actual loaded
path and library hash are checked during build and runtime verification. The Debian
package version remains old, but Python uses the explicitly admitted library;
this is not an OS-wide vulnerability scan. See [ADR-012](../decisions/ADR-012-container-sqlite-runtime.md).

Local Linux arm64 admission and affected recovery tests now PASS in
[R-015 evidence](../verification/SCN-003-fixed-sqlite.md). Target-host/amd64 admission
and full release gates remain pending. Never deploy solely on a digest or tag.
