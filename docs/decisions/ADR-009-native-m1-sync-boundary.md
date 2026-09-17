# ADR-009 Native M1 archive synchronization boundary

2026-09-17. Receiving boundary implemented locally under SCN-008, Demo only;
worker design remains to be implemented and verified.

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
