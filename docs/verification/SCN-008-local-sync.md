# SCN-008 AC-06 real local synchronization

2026-09-17. Base `322bdca1af71a1396bb55af341703d48b7a2e20b`; candidate dirty
during verification. The new verifier and documentation are the only changes;
production worker/API code, database migrations and dependency locks are unchanged.
Final local HTTP run completed at `2026-09-17T06:20:04.759818+00:00`.

## Outcome and scope

AC-06 PASS locally: actual worker subprocesses, private temporary SQLite source
and journal, real Supabase Auth JWTs, PostgREST RPCs, independent owner REST reads
and SQL numeric queries. The input bars/accounts are synthetic; this is not
actual MT5, hosted Supabase, target recovery, power-loss or full Demo evidence.
AC-07 operator packaging/recovery remains incomplete. No worker was enabled for
the owner, no cloud resource deployed, and Auto Trading remains disabled.

The guarded `sochron1k` Docker project exposed all published services only on
127.0.0.1. The verifier requires origin `http://127.0.0.1:54321`, no hosted link,
a local Unix Docker socket and the matching repository workdir. No database reset,
schema/grant change, migration or user UI/API restart was performed.

## Behavior and independent oracles

- A loopback proxy forwards only the two fixed RPCs to real PostgREST. It withholds
  the actual successful store response, then the verifier SIGKILLs the worker.
  An independent SQLite connection observes UNKNOWN, attempt 1 and cursor 0.
  A new CLI process reads back actual committed rows, reaches VERIFIED, and the
  proxy counts one store, not a second send. The proxy never fabricates success.
- SQL verifies two exact `99999999999999.9999999999` price values and tick volume
  `9007199254740991`. Owner REST returns exact original JSON payloads, including
  decimal strings, broker times and receipt/closure provenance. SQL numeric text
  is parsed with Decimal, not binary floating point.
- The worker's modern backend secret key authenticates through the actual local
  gateway; a legacy service-role key also authenticates a matching replay. Reading
  rows afterward proves replay preserves the first stored availability and payload.
- Two separately authenticated generated owners have rows under the same archive
  UUID. Each reads exactly their own two rows and archive binding. Anonymous reads
  reveal none; both anonymous privileged RPCs are denied (401/403). Both signed-in
  owners are denied store/read RPCs and table PATCH/DELETE (403). A service-role
  DELETE of native rows is also denied (400) and row count is unchanged.
- A later capture has receipt 2 but an older candle time. After the real database
  commits it, the proxy drops the response. The CLI returns UNKNOWN; reopening the
  same journal verifies the stored older row without another store. There are three
  owner rows and two total successful proxied stores across the two batches.
- Changing only the temporary config mode to 0644 returns SYNC_CONFIG_INVALID
  before any additional proxy call. Restoring 0600 permits normal inspection.
- A fresh source conflicts with a valid, preexisting database payload. The actual
  worker quarantines it, stays quarantined after restart, and an independent RPC
  confirms the destination payload was not overwritten.

The suite exercises process termination and lost HTTP responses, not actual disk
power loss. It does not test TLS or prove that a production service key is scoped
to one owner. Existing service-role authority remains privileged outside the worker.

## Fixture lifecycle

Random users are created only in the guarded local Auth instance; credentials are
kept in memory/private temporary files and never printed. Cleanup verifies each
returned UUID/email before deleting only its generated owner/archive rows in a
separate local transaction using session-local replica mode. This bypass of native
delete guards is restricted test housekeeping, after verifying normal service-role
deletion fails. No trigger, grant or global setting changes. Fixture sessions are
signed out before users are deleted; this is not a claim that JWT bytes cease to
be cryptographically valid. Temporary key/source/journal files are removed on exit.

Independent SQL counts after the run: bars 0, native archives 0, Auth users 0,
matching the empty starting state. The local stack was stopped with the reviewed
wrapper, preserving volumes. No local Supabase containers remained running and
generated key files were removed (an empty start-secrets directory may remain).
Only regenerable synthetic fixtures were deleted; no operator dataset was reset.

One intermediate verifier revision failed with UnboundLocalError because a new
row-count assertion preceded the SQL result assignment. Cleanup still completed.
The assertion was moved after the query, not removed or relaxed; the corrected
full run and subsequent anonymous-RPC additions passed. FAIL replaces earlier
PASS in the ignored result file, preventing stale successful evidence.

## Environment and evidence identity

macOS 26.6.2 arm64; Python 3.14.7, SQLite 3.53.1, HTTPX 0.28.1,
Node 24.21.0, Supabase CLI 2.117.0, pytest 9.1.1, Ruff 0.16.8.
Applied migrations: `20260916193652`, `20260916224038`, `20260917050541`.

Observed runtime image tags and immutable image IDs:

- `public.ecr.aws/supabase/postgres:17.6.1.167`:
  `sha256:6942962433a569e87f228b4d4ab7e11db5deca64e43babb3a038443ad6c4f1bb`
- `public.ecr.aws/supabase/postgrest:v16.2`:
  `sha256:85258123312dc496ad4c2ed832154a65e9746f84df0d6d09b44229ff9230c08e`
- `public.ecr.aws/supabase/gotrue:v2.196.0`:
  `sha256:c0c25187a6b835e65a6f6e6c6b39d090e832d40e6de5186f2c038e0411944232`

Verifier SHA-256:
`5a74e98c61c95fd74ed3968a026fd5febf7a9c2ed395d0b6a1210530a79e2d2a`.
The ignored `output/native-sync-local/result.json` also records checks, UTC time,
all worker/API module hashes, migration hashes, fixture dependencies and local
Supabase config hash. Its production inputs are unchanged from the base revision;
the commit containing this document identifies the final verifier candidate.

## Exact checks

- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 .venv/bin/python scripts/check-native-sync-local.py`:
  PASS, all eight reported groups, including cleanup.
- `.venv/bin/ruff check scripts/check-native-sync-local.py`: PASS.
- `bash scripts/check-scn-001-local.sh`: **425 PASS**, Ruff and secret scan PASS.
- `bash scripts/check-project-baseline.sh`: PASS.
- `python3 scripts/check-agent-skills.py`: PASS, all 15 installed trees and four
  repository skill sources match their pinned digests (integrity only).
- `python3 scripts/check-no-secrets.py` and `git diff --check`: PASS.

No frontend change: browser suite/build not rerun. No schema change: destructive
full-database reset/pgTAP not rerun; earlier receiver evidence remains separate.
No hosted, broker, deployment or unattended-Demo gate was run or marked PASS.

The Supabase skills prompted separate grant/RLS and real Auth checks, following
[Data API controls](https://supabase.com/docs/guides/api/securing-your-api) and
[backend key roles](https://supabase.com/docs/guides/getting-started/api-keys).
The current [default-grant change](https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically)
does not require a migration here: existing project grants are explicit.
The [risk/recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md)
guided the hard-crash and independent read-back oracle rather than ACK-based success.

Next safe work: operator packaging and verified backup/recovery delivery, then
remaining full-product gates. Real integration still needs the owner's Supabase
project/identity, Demo broker/account specifications and MT5 host/build; deployment
also needs host/domain/alerts/budget decisions and the corresponding authorization.
