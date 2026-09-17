# SCN-008 Native M1 synchronization

Version 1.0, High assurance. Owner: project owner. Acceptance recorded before
implementation on `e5602a4`. Blueprint sections 06/15/22/23, SCN-002 and SCN-007
require a durable asynchronous path from local capture to owner-scoped Supabase
history. Local development/test is authorized; hosted writes, deployment and MT5
operation are not. This contract does not make the full Demo product ready.

## Outcome

Synchronize every committed native closed M1 bar, preserving its archive identity,
first receipt and exact decimal/time provenance. Supabase is a copy, never broker
or execution truth. Leave forming bars, raw ticks, strategy promotion and command
dispatch outside this worker. No UI fake history or browser write grant.

## Acceptance before implementation

- AC-01 database receiver: retain SCN-002 rows and grants; widen only bar OHLC
  precision to the native 24-digit/10-decimal bound without truncating input, and
  widen tick-volume integer capacity while retaining legacy fractional precision.
  Bind each owner/archive to immutable Demo capture identity, UTC offset and its
  validity interval. Store the exact archived payload alongside typed columns.
  Unique owner/archive/raw-time keys reject changed replays; matching replays
  preserve first availability and create no duplicate row. A batch is atomic.
  Grant preservation means intended browser SELECT and backend bar CRUD, not
  inherited Supabase maintenance privileges: revoke backend TRUNCATE/TRIGGER/
  REFERENCES/MAINTAIN on bars and all privileges except SELECT/INSERT on archives,
  so table-wide operations cannot bypass native immutability. Verify actual role
  TRUNCATE denial (acceptance clarified after inherited-grant failure reproduced).
- AC-02 database authorization/integrity: receiver and reconciliation RPCs are
  security-invoker, explicit backend-only grants, empty search path and bounded
  batches. Authenticated owners can read only their archive/rows, not invoke
  worker writes/reads or mutate evidence. Anonymous access is denied. Validate
  provenance, M1 alignment, closure, exact price grid/precision, types and time
  order; deny native-row/archive overwrite or deletion. Existing generic bars
  stay compatible. Verify live local SQL roles, negative payloads, atomic rollback,
  duplicate/conflicting concurrent writers and fresh/forward migration paths.
- AC-03 source/export: worker reads the existing private SCN-007 archive without
  creating/replacing it. Verify pinned identity/config/schema and payload hashes.
  Traverse `(first_receipt, time_server_s)`, not only candle time, so later captures
  of older bars cannot be skipped. Bounded batches contain closed M1 only. Preserve
  missing intervals; never invent prices. Export availability is an observed time
  after local commit, not candle-open/close or precommit receive time.
- AC-04 durable worker: journal exact batch intent and source/destination binding
  before send, preserve pending state and cursor across restart, one writer per
  state directory. Advance cursor only after independent destination read-back
  matches archive binding and every payload. A timeout/ambiguous send is UNKNOWN;
  reconcile before another write. Changed payload/binding is quarantined, never
  overwritten. Storage failure prevents dispatch. No automatic evidence pruning.
- AC-05 transport/config: disabled without a private explicit configuration;
  service credentials never enter browser, source, arguments, logs or artifacts.
  Bind one owner/archive/destination, strict origin validation, no redirects or
  environment proxy, bounded request/response size and deadlines. Serial bounded
  retry/backoff; no unbounded request fan-out or silent destination switch.
- AC-06 end-to-end evidence: real loopback Supabase/PostgREST plus temporary source
  and worker SQLite state prove exact high-precision values, owner isolation,
  retry after committed-but-lost response, process restart, no skipped older bars,
  conflict quarantine and denied unsafe configuration. No actual account data.
- AC-07 operator delivery: documented enable/disable/reconcile/recovery procedures,
  observable local sync state and explicit missing hosted/owner/MT5 requirements.
  Full gates remain incomplete until the real requested Demo behavior is verified.

## Sequencing and status

1. Build and verify the receiving schema/RPC boundary (AC-01/02).
2. Implement receipt-ordered export and durable worker (AC-03/04/05).
3. Exercise full local HTTP/crash workflow and operator entry point (AC-06/07).

AC-01/02 now have local database evidence; see
[receiver verification](../verification/SCN-008-native-m1-receiver.md).
AC-03 now has local read-only exporter evidence; see
[source verification](../verification/SCN-008-native-source.md).
AC-04 now has local journal/one-step driver and process-crash evidence; see
[journal verification](../verification/SCN-008-sync-journal.md).
AC-05 now has private config, bounded HTTP transport and explicit runner evidence;
see [transport verification](../verification/SCN-008-sync-transport.md).
AC-06 real Supabase end-to-end evidence remains NOT RUN. AC-07 has an initial
[operator runbook](../operations/native-m1-sync.md), but complete operator delivery,
packaging and target recovery gates remain incomplete. The worker is not enabled
or deployed; strategy dataset approval and full Demo acceptance are not claimed.
Next is actual local Supabase HTTP/role/recovery integration.

## Availability and recovery semantics

### AC-05 transport/config/runner detail (before implementation)

Use the existing pinned HTTPX dependency; no SDK or new package. The operator
sets only `SOCHRON_SYNC_CONFIG_FILE`, a canonical absolute private JSON file.
No config means DISABLED and no source/journal/network access. Explicit enabled
config pins the source directory/archive/Demo identity/offset interval, separate
state directory, owner UUID and destination origin. The service key is read from
a separate private file, never an argument or environment value. Reject oversized,
duplicate-key, unknown-field, unsafe-path/mode/owner/link or malformed input with
fixed redacted errors. Accept backend secret keys or legacy service-role JWT syntax;
syntax is not proof of remote authentication. No publishable/anon/user credential.

Allow canonical HTTPS DNS origins with default TLS verification, or an explicit
IPv4 loopback HTTP origin/port for local testing. Reject userinfo, paths, query,
fragment, backslashes, whitespace, Unicode and ambiguous ports. Do not follow
redirects, use environment proxy/CA settings, retain cookies, or log request/response
bodies. Only two fixed POST RPCs exist, with pinned owner/archive arguments and
bounded JSON. Reject compressed responses; enforce 262,144-byte request/response
caps, 2-second socket inactivity and a 10-second total async request deadline.
No transport-layer retries. Known native conflict replies quarantine; other HTTP
errors/timeouts remain UNKNOWN. Successful store is still followed by independent
read-back; malformed successful read-back is a conflict, not synchronization.

Provide local `init`, `status`, `run --once` and serial `run` commands. Init creates
only the explicit empty private worker state, without network. Status reads local
state without a key/network and is not destination verification. Run is the explicit
operator action that can sync configured data. No automatic service installation,
Compose enablement or startup. Use bounded exponential backoff for unresolved work,
five persisted sends per batch, and exit after five consecutive unresolved steps
per process. At the send budget, an UNKNOWN batch may still reconcile; never send
again or reset its attempts. Do not auto-restart exhausted workers. Idle polling
and successful work may continue serially until stopped. SIGINT/SIGTERM must not
clear pending state or print a traceback/credential. Config/key rotation requires
stop and restart; missing state or quarantine requires operator review, not reset.

Verify fake HTTP plus real loopback socket behavior, redirect/auth/error/size/deadline
negatives, private config, disabled/no-send commands, budget persistence, restart
and redacted output. These tests are distinct from AC-06 real Supabase HTTP/roles.

### AC-04 journal/driver detail (before implementation)

Use a separate explicitly initialized private directory, `sync.sqlite3` and a
process-held nonblocking POSIX file lock. Normal reopening must not create missing
state; partial initialization requires operator review. Pin source directory,
archive UUID/binding, destination origin and owner UUID without credentials.
Verify ownership/mode/link count/inodes, schema and batch fingerprints on reopen.
Use WAL/FULL with bounded lock waits and a fixed 64 MiB main-database quota; never
prune old evidence automatically. Report quota warnings without claiming a whole-
filesystem bound or power-loss verification.

Atomically append immutable exact batch intent before dispatch; keep at most one
unverified batch. States are PREPARED, UNKNOWN, VERIFIED and QUARANTINED. Persist
UNKNOWN plus attempt count before calling the destination. An ACK alone changes
nothing. Read-back must match archive binding and every exact bar payload, with
valid UTC availability no earlier than the original receipt and no later than the
read observation. Existing matching rows may retain a different conservative
availability, as specified by AC-01. Missing matching rows permit a later retry
only after this reconciliation; contradictory/malformed state quarantines.

Update VERIFIED and the source cursor in the same durable transaction. Retain the
batch ledger and validate cursor-chain consistency on restart. Reject time rollback
relative to journal observations, changed config, concurrent writers, corrupt state
or storage failure before external dispatch. A one-step driver exposes no broker
operation or background loop; real transport, retry scheduling and private config
remain AC-05. Test actual temporary SQLite files, denied transitions, duplicate
prepare, lost response, missing/partial/conflicting read-back, disk/lock failures,
restart, and process exit after destination acceptance. Simulated transport is not
AC-06 real PostgREST/HTTP evidence.

### AC-03 source reader detail (before implementation)

Create a worker-owned read-only source adapter, sharing existing domain validators
but never constructing `BarHistory` (which can initialize a database). Require the
explicit archive UUID, Demo identity, broker offset and chart validity interval;
no bridge credential is needed. Use SQLite URI `mode=ro`, query-only/defensive
settings and a short read transaction. Do not use `immutable=1` on a changing WAL
archive, force a checkpoint, add indexes or repair the source from this reader.
SQLite may maintain WAL shared-memory sidecars; application tables and the main
database must not be created or changed by the reader.

Check canonical private paths, ownership/mode/link count and stable directory/file
identity before and after reads. Validate schema version/required table layouts,
archive binding, payload digest, receipt linkage, exact decimal/grid values,
closure/alignment/time bounds and UTC provenance. Reject invalid/oversized JSON,
duplicate keys, unknown schema and swapped archives with redacted errors.

Cursor `(0,0)` means start; any nonzero cursor must identify an existing closed M1
row in this same archive. Use a single committed snapshot per bounded page, return
only actual rows ordered by `(first_receipt,time_server_s)`, and advance the returned
cursor only through included rows. Return immutable payload strings plus a UTC
availability observed after reading those committed rows. This returned cursor is
a candidate, never a persisted sync acknowledgement. A rollback of wall time
relative to source receipt denies export. Bound query execution and payload size;
test WAL visibility with an independent writer, uncommitted invisibility, later
backfill, repeated/reopened reads, tampering, no-create/no-write and path changes.

`received_at` is the original API capture-processing time before local commit.
`available_at` for synchronized native rows is a conservatively observed time at
which the worker first read committed source evidence. It is not the destination
commit timestamp. A strategy must separately record its own data cutoff and
already-observed committed evidence; neither timestamp backdates a decision.
Matching retries retain the first stored availability rather than rewriting it.
Archive identity/config changes require a new reviewed binding, not a cursor reset.
Destructive local verification first proves its target contains no valuable rows;
never reset a hosted database or delete user data to make a test pass.
