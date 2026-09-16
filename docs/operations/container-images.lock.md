# Container Image Lock

Verified against the upstream registries on 2026-09-16 UTC. Tags document the intended release; digests are the enforced multi-platform identities in the Dockerfiles.

| Purpose | Image tag | Multi-platform digest |
| --- | --- | --- |
| API build and runtime | `python:3.14.7-slim-bookworm` | `sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f` |
| Web build | `node:24.21.0-bookworm-slim` | `sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553` |
| Web runtime | `nginx:1.30.5-alpine3.24` | `sha256:25820c39dba41369486df729ad6697de2fab631ca809e0503e1d1e0c73d9a232` |

Digest admission is verified metadata, not a vulnerability scan or a successful local build. Changing any tag or digest requires fresh upstream verification, a clean rebuild, and runtime smoke evidence.
