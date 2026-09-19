# ADR-018 Authenticated single-executor polling bridge

2026-09-20; SCN-012, builds on `201e05b` and ADR-016/017. Decision:
connect the durable `ExecutionService` boundary to one future MT5 Demo EA through a
disabled-by-default authenticated polling protocol. This increment implements and
verifies the API-side transport only. It does not implement an MQL5 mutation, expose
an owner trade route, operate an account or enable Auto Trading.

## Boundary and fencing

The executor uses a credential scoped only to `/executor/v1`; it cannot reuse the
read-only telemetry token, browser owner session or Supabase key. Configuration is
accepted only from an owner-only regular file outside the repository and fixes one
executor/account/server/currency/margin-mode/symbol identity plus one positive magic
number. Missing configuration leaves the transport disabled.

Each API process owns a random boot fence. The EA first obtains that fence from the
authenticated challenge, then posts a fresh complete inventory containing its own
generation. Inventory sequence and observation time are monotonic; exact replay is
idempotent and changed replay fails closed. A generation change is refused while a
dispatch is active. Startup admission still validates the inventory against the
durable journal, risk state and configured `PreflightPolicy`; transport acceptance
alone does not grant admission.

Only one command may be active. `ExecutionService` journals the intent and attempt
before calling the adapter. The adapter then exposes a typed immutable entry,
cancel or close dispatch. Management volume and broker identifiers come from the
validated parent snapshot, not from HTTP or browser input. First poll claims the
dispatch; later polls return the exact same command until a bound outcome arrives.
An unclaimed timed-out dispatch is withdrawn. A claimed timeout remains ambiguous
and is retained for reconciliation; no replacement attempt is created.

## Evidence semantics

An outcome is bound to boot, dispatch sequence, attempt, executor generation,
command, target and operation. Entry and management snapshots reuse the cumulative
domain evidence already validated by the journal. Explicit uncertainty raises an
ambiguous adapter failure, so the service records `UNKNOWN`. Exact outcome replay is
accepted; changed replay is rejected.

Broker rejection is a separate evidence type because a rejected request may have no
order ticket. It stores a conservative reviewed no-effect return-code allowlist,
external code, request ID and UTC observation time without raw broker comments. A
timeout, connection loss, processing lock, changed/already-closed state or successful
return code cannot be relabelled as rejection. A rejected entry releases its slot
only after the no-effect evidence is durable. Rejected cancel/close retains the
parent snapshot and exposure; rejected close restores the parent from `CLOSING` to
the state derived from that snapshot.

Complete inventories can carry the same typed rejection for restart recovery.
Query methods read accepted evidence only and never enqueue or resend a command.
The recovery inspector admits the new table only when return code, binding,
transition, attempt, exposure and absence of broker identifiers are consistent.

## Rationale and limitations

MQL5 documents that `OrderSend=true` establishes only basic request acceptance,
not execution, and that one request can produce multiple transactions. Server return
codes also distinguish placed, completed, partially completed, timed out, rejected
and disconnected requests. The transport therefore cannot use an HTTP response or a
single `MqlTradeResult` as execution truth. See the official
[OrderSend](https://www.mql5.com/en/docs/trading/ordersend),
[OnTradeTransaction](https://www.mql5.com/en/docs/event_handlers/ontradetransaction)
and [trade-server return codes](https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes).

The in-memory dispatch queue intentionally supports one API process and one
executor. Durable command truth remains SQLite; after API restart the new boot fence
requires a complete inventory and query-only recovery. This is not a distributed
queue, multi-worker lease or permission to expose the transport publicly.

Synthetic API, concurrency, timeout, rejection, startup and recovery tests do not
prove MQL5 compilation, local EA idempotency, target TLS/networking, broker semantics,
terminal restart or a Demo round trip. Public health remains
`execution_ready=false`; Auto Trading remains false.
