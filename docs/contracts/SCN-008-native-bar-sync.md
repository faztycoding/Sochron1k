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
AC-03 through AC-07 remain NOT IMPLEMENTED / NOT RUN. A database-only checkpoint
is not a working sync worker, deployment, strategy dataset approval or full Demo
acceptance. The next implementation is the receipt-ordered source exporter and
durable worker, not an assumption that database ACK means synchronization.

## Availability and recovery semantics

`received_at` is the original API capture-processing time before local commit.
`available_at` for synchronized native rows is a conservatively observed time at
which the worker first read committed source evidence. It is not the destination
commit timestamp. A strategy must separately record its own data cutoff and
already-observed committed evidence; neither timestamp backdates a decision.
Matching retries retain the first stored availability rather than rewriting it.
Archive identity/config changes require a new reviewed binding, not a cursor reset.
Destructive local verification first proves its target contains no valuable rows;
never reset a hosted database or delete user data to make a test pass.
