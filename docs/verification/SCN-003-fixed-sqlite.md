# SCN-003 / SCN-008 fixed SQLite admission (R-015)

2026-09-17, base `2398abb7685e8cd52a0d5daec6b6138fa1e2f7bc` plus recorded dirty
candidate inputs. Local Docker 29.5.2 arm64, Compose 5.5.1, Python 3.14.7,
compiler GCC 12.2.0 from the pinned bookworm compiler image.

## Outcome

Both API and worker now load upstream SQLite **3.53.4** from
`/usr/local/lib/libsqlite3.so.0`. Source archive and sqlite3.c hashes are verified
before compilation; runtime version, source ID, Linux loaded path, threading mode
and compiled library hash match the lock/manifest. Library SHA-256 is
`c7f8ee180657c5cc5b85e1c9fbed3845e4516a7d1be5749cb50121d31f60dd9e` in both builds.
The exact upstream source ID is:

```text
2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc
```

Upstream [3.53.4 release notes](https://sqlite.org/releaselog/3_53_4.html) include
the WAL-reset fix and source identity; official archive/source hashes are retained
in `services/runtime/sqlite.lock.json`. Compiler image multi-platform digest was
resolved from the official Docker registry on this date:
`sha256:ecac9e212daacda8a702eae372fceebc0ee36f5805abe087880367e8d061fa5b`.

R-015's fixed-runtime gate is mitigated for the tested local arm64 candidates.
Target/amd64 admission remains pending. This is not a full OS security scan,
power-loss test, backup restore, broker operation, hosted integration or release
approval. Auto Trading remains disabled; default worker remains DISABLED.
No Python application behavior, dependencies, schemas, frontend or operator state
were changed. The original Debian SQLite remains installed; it is not the loaded
Python library. See [ADR-012](../decisions/ADR-012-container-sqlite-runtime.md).

## Independent checks and retained evidence

1. The previous image `sochron-worker-b0b827059fb7:candidate` was run with no
   network, read-only root and UID 10001, using the new probe supplied on stdin.
   It exited 1 as expected: SQLite predates the admitted upstream WAL-reset fix.
   The denial happens before manifest lookup; it was not merely a missing-file test.
2. Six new unit tests cover exact archive member selection without extraction,
   wrong archive/source hashes, invalid archive before ZIP parsing, both Dockerfiles'
   pin/probe/loader wiring and old runtime rejection. Full workstation suite:
   **433 PASS**, Ruff and secret scan PASS through `check-scn-001-local.sh`.
3. No-cache worker build and full isolated replacement verifier PASS, including
   runtime probe, private config/init/status, competing writer denial, durable
   UNKNOWN after SIGTERM, new container read-back without another store, source
   fingerprint preservation and unsafe config denial. One store/one read, cursor 1.
   Evidence: `output/worker-container/sochron-worker-2e31a35b5321/result.json`;
   07:03:57.530935–07:04:35.253209 UTC, cleanup 0 and generated fixture key removed.
   Candidate image index: `sha256:c44753b432c2e925aa1bce75efe9ed72e6922fea36656f705659329df8f60277`.
4. No-cache API/web Compose verifier PASS: loaded-library probe, runtime hardening,
   Demo/auto-off health, loopback routing and volume marker across API replacement.
   Evidence: `output/compose/sochron-verify-4d9822cb76fa/result.json`;
   07:03:59.371052–07:04:40.893057 UTC, cleanup 0.
   API container image config ID:
   `sha256:098d3cd071a2e37d37807a3b2dbfabb36fdd30d6543a0bfb5ec21de6165c832b`.
5. Candidate-derived Linux tests: **410 PASS per image**. Includes risk/preflight,
   API denial, durable bar history, native source, sync journal/driver/transport,
   SQLite concurrency, subprocess crash/restart and checksum tests. The 23
   MT5 source-scanner tests are deliberately excluded from these runtime suites;
   they passed in the full workstation suite. No actual MQL5 compilation is claimed.
   Tests run non-root/read-only/no-egress with temporary databases on bounded tmpfs.
   No user/broker data or credentials are used.
   - Worker: `output/container-python/sochron-python-3693e17b66d7/result.json`,
     410 PASS in 14.31s; completed 07:06:12.894922 UTC.
   - API: `output/container-python/sochron-python-6142f1bddc06/result.json`,
     410 PASS in 14.29s; completed 07:06:13.843648 UTC.

The test images add hash-locked development dependencies and exact reviewed source/
fixtures. They are not production artifacts. Before testing, both candidate and
derived image must return the same SQLite probe result. Candidate tag identity is
checked again after build. Test result manifests retain candidate/test image IDs,
all copied input hashes, requirements hash, verifier hash and pytest summary/log.
The verifier SHA-256 is `42b02a50d8e378d184b75501d237078bc5d080c33e23fa393ec90e4deb3ba1e0`.

## Commands

```bash
bash scripts/check-scn-001-local.sh
bash scripts/check-project-baseline.sh
python3 scripts/check-agent-skills.py
npx -y -p node@24.21.0 npm run check:compose:static
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local
bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py
SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-2e31a35b5321:candidate
SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-verify-4d9822cb76fa-api:local
```

All above PASS. The uv path is this workstation's verified 0.12.15 executable,
not a portable install location. Baseline, installed skill integrity, secret scan
and diff whitespace checks PASS. No existing tests/gates were relaxed.

Initial builds correctly failed runtime admission: copying the library and running
ldconfig alone still loaded the old library. Adding the explicit root-owned loader
path fixed selection; the same probe then passed in both images. These failures
were not reported as successful builds. Ordinary passing tests are not the proof
of the upstream race fix; source identity and actual linkage supply that evidence.

No tested code/build/probe/fixture changed after the successful runs; subsequent
edits only update documentation. The containing commit identifies the final source.
Test containers were removed; scoped synthetic evidence volumes/images and logs
remain recoverable locally. The developer UI/API and stopped local Supabase were
not restarted, and no MT5 process was operated.

The [operations skill](../../tooling/skills/sochron-vps-operations/SKILL.md) guided
source/image/runtime identities and isolated local builds. The
[risk/recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md) guided
durability regressions and separation of source admission from functional results.
Next safe work is consistent backup/restore with domain invariants and measured
local recovery, followed by separately authorized actual-target gates.
