# ADR-009 Native M1 archive synchronization boundary

2026-09-17. Receiving boundary implemented locally under SCN-008, Demo only;
read-only source, durable worker journal and one-step driver implemented locally.
Private config, bounded HTTP transport and explicit runner implemented locally.
Real local Supabase end-to-end HTTP evidence is retained under
[AC-06 verification](../verification/SCN-008-local-sync.md). Deployment packaging,
hosted integration and target recovery remain outstanding.

## Decision

Reuse `public.bars` for synchronized M1 values and add an owner-scoped
`native_bar_archives` identity binding. Add nullable native provenance columns so
existing generic research-bar rows remain valid. Widen OHLC to numeric(24,10);
validate exact raw decimal values before accepting typed representations. Preserve
the original SCN-007 JSON decimal strings/timestamps as immutable capture evidence.

Use two bounded PostgREST RPCs: insert-or-verify a batch and independently read
stored native payloads. Both are security-invoker and backend-only, with explicit
grants; browser roles stay read-only under owner RLS. SQL uniqueness and transactions
resolve races, not a client-only SELECT-then-INSERT precheck. Changed replays raise
conflict and roll back the whole batch. Do not use merge-upsert to rewrite history.

The future worker is a separate Python process, not part of the tick/API risk loop.
Its durable batch journal is separate from the command journal. It consumes source
rows in first-receipt/time order, journals before send and reconciles UNKNOWN
results before retry. The server's receipt of a request alone never advances the
local sync cursor; independent committed-data comparison does.

The source adapter opens the existing SCN-007 database with `mode=ro`, never the
initializing `BarHistory` constructor. Read transactions include binding/cursor
validation and bounded receipt-ordered rows in one WAL snapshot. Availability is
observed after fetching committed rows. Domain models are reused from the current
API source package without importing its HTTP routes or startup entry point; a
separate shared package is unnecessary for this boundary. Deployment packaging
for the runnable worker remains future work, not implied by pytest's import paths.

The worker journal uses a separately initialized private POSIX directory and
`sync.sqlite3`, WAL/FULL, a process-held nonblocking `flock`, and one in-process
step lock shared by drivers using the journal. Normal reopen never creates missing
state. It pins source identity/path and destination owner/origin without storing
credentials. Schema/immutable intents and the complete cursor chain are audited
on startup; selected state and schema are checked during subsequent operations.
At most one unverified batch exists. PREPARED becomes durable UNKNOWN before
external send; independent read-back produces VERIFIED, retryable PREPARED if
rows are absent, or persistent QUARANTINED on contradiction. Cursor and VERIFIED
commit atomically. No API automatically releases quarantine or deletes evidence.

The fixed 64 MiB journal page quota and warning states bound the main database,
not WAL/SHM or filesystem use. Every verified batch remains in the ledger, so
eventual capacity requires a reviewed retention/export procedure rather than
silent deletion. The lock is advisory on the supported local POSIX filesystem;
Windows worker operation and network filesystems are not established. This is
separate from the Windows-or-Wine MT5 executor choice. Process termination tests
are not power-loss, storage-controller, target-host restore or release evidence.

The operator runner reads one private config and separate credential file, uses
the existing HTTPX dependency and exposes only the two fixed native RPCs. No SDK,
automatic service or Compose enablement is added. Each sync HTTP operation runs
in its own async client with a total cancellation deadline; the synchronous driver
waits for it serially. Cookies/client sessions are not retained between RPCs.
The worker supports backend secret keys and legacy service-role JWTs without
passing a secret key as an invalid user bearer token. Config pins the owner/origin;
credential syntax validation does not substitute for Supabase authentication.

Every batch has at most five persisted sends, including across process restarts.
UNKNOWN remains eligible for read-back at that limit, but not another send. The
runner additionally exits after five unresolved steps and uses bounded backoff.
There is no automatic reset/repair or background restart. This favors explicit
operator review over indefinitely hammering an unavailable/misconfigured target.
Local PostgREST acceptance now has AC-06 evidence. Complete operator delivery
and target-host recovery still need AC-07 evidence.

## Alternatives and consequences

Direct browser inserts violate the existing authority boundary. Blind REST upsert
would overwrite immutable capture evidence. Copying only time-ordered OHLC loses
late historical captures, first receipt and closure provenance. A new queue service
is unnecessary for the single-archive worker; SQLite is already the local durable
boundary. Keeping all metadata only in JSON would make stable uniqueness and owner
joins less explicit, so archive/raw-time/receipt keys are also typed and indexed.

Existing generic bars remain compatible; native evidence is stricter. Native
archive/row UPDATE and DELETE are denied by triggers, including service-role
attempts; deliberate retention/repair needs a separately reviewed export/migration
procedure. A privileged database administrator can change/drop these controls:
they are integrity guards, not protection against a compromised DBA.

Explicitly revoke inherited backend maintenance grants on bars and archives.
TRUNCATE bypasses row-level triggers; native guards alone were insufficient in the
actual Supabase defaults. Bars retain SELECT/INSERT/UPDATE/DELETE for generic rows;
archives permit only SELECT/INSERT. Browser grants and other tables are unchanged.

The backend service role is an existing privileged project principal, not a
per-worker capability. Keep its key private and expose only fixed RPC destinations
in the worker. Hosted least-privilege provisioning and actual deployment remain
unverified. Local schema/fixture tests cannot establish broker or strategy truth.
