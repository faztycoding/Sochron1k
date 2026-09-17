# ADR-012 Explicit fixed SQLite for Python containers

2026-09-17. SCN-003 / SCN-008; R-015 local candidate admission, not deployment.

The pinned Python 3.14.7 slim-bookworm base links Debian SQLite 3.40.1, not the
development interpreter's 3.53.1. Upstream documents a WAL-reset race fixed in
3.51.3+; Debian's stable-package metadata does not establish that this older binary
contains the fix. Python version or functional smoke success is insufficient.

Build upstream SQLite 3.53.4 using the official amalgamation with pinned archive
and source-file SHA3-256, source ID and a digest-pinned Python bookworm compiler
image. Both Dockerfiles use one build script. Compiler/headers/source stay in the
build stage; runtime receives a shared library and provenance manifest. Python
and Python dependencies stay unchanged. No apt resolver, SQLite wrapper or import
monkeypatch is introduced.

Install at root-owned `/usr/local/lib/libsqlite3.so.0` and explicitly set
`LD_LIBRARY_PATH=/usr/local/lib`: the runtime probe demonstrated that `ldconfig`
alone did not select the new library in this base. Probe during build and runtime
verification for exact version/source ID, Linux loaded path, library hash and
serialized-threading option; require manifest/lock agreement. The original Debian
library remains installed but is not Python's admitted library. This does not
claim all OS packages or callers of an absolute Debian library path are patched.
Do not override loader environment or mount over the admitted library. Recheck on
every target. No target admission is inferred from local arm64 results.

Compilation enables threadsafe, URI filenames, column metadata, FTS5, RTree, math
and dbstat. Applications still explicitly enforce WAL/FULL, query-only/defensive
and private-file policies. Source checksum failure stops before compilation.

Reject the previous image through the probe. Rebuild API/web and worker without
cache and exercise both replacement workflows. Run affected Python tests in each
candidate-derived Linux image; test images add locked development dependencies
and reviewed fixture/source files, not a replacement SQLite. They are not release
images. Source admission and linkage prove the intended upstream fix is present;
ordinary passing tests alone cannot prove a rare upstream race absent.

Changing distro would broaden the change without proving its SQLite patched;
mutable apt upgrades weaken reproducibility. The pinned shared-library layer is
bounded and can be retired after equivalent distro/source/linkage/recovery evidence.
New library releases require fresh upstream admission and affected checks.

References: [release/source ID](https://sqlite.org/releaselog/3_53_4.html),
[download hashes](https://www.sqlite.org/download.html),
[compile instructions](https://sqlite.org/howtocompile.html),
[WAL-reset advisory](https://sqlite.org/wal.html#walreset), and
[Debian versions](https://security-tracker.debian.org/tracker/source-package/sqlite3).
