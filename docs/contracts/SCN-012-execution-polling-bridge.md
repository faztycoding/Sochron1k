# SCN-012 Authenticated Demo execution polling bridge

2026-09-20, High assurance, base
`201e05bbb85f32dfea7c264c67143ebbb46f750d`. Local implementation under the
full Demo goal; no broker operation, hosted write, deployment, account credential,
owner execution endpoint or unattended trading is authorized. Extends SCN-001
AC-01/03/04/05/06/07/08 and SCN-011.

## Required outcome

Add a disabled-by-default, executor-authenticated HTTP polling boundary between the
FastAPI service and one future MT5 Demo EA. The boundary carries the existing durable
entry, cancel and close commands only after `ExecutionService` has journaled the
intent and dispatch attempt. It carries cumulative broker evidence back to the
service and never treats transport delivery, `OrderSend` return, or an HTTP success
as proof of execution.

The configured Demo identity, bridge boot fence, executor generation, account,
server, currency, margin mode, symbol and magic number are fixed outside browser
control. Only one command may be exposed at a time. A claimed command can be
re-delivered with the exact same dispatch identity so that the EA can reconcile it;
the bridge never creates a replacement command after an ambiguous result.

MT5 remains authoritative. The bridge is an internal transport and adapter, not an
execution API for the browser or owner. Public health continues to report
`execution_ready=false` and `auto_trading_enabled=false` until separate release and
target gates pass.

## Local acceptance

- AC-01: Load a separately scoped execution credential and fixed Demo identity from
  an owner-only regular configuration file. Refuse symlinks, group/world access,
  oversized files, invalid secrets, live/contest/unknown modes and any identity
  mismatch. With no file configured, all mutation transport is disabled.
- AC-02: Accept a strict, bounded inventory frame only after executor authentication.
  Bind it to the API boot fence, configured executor identity and magic number.
  Require one Demo account, expected symbol, complete cumulative entry and management
  snapshots, monotonically increasing sequence/time and a fresh observation. An
  exact replay is idempotent; changed replay, reversal or foreign identity is denied
  and visible as a redacted rejected status.
- AC-03: Implement an `ExecutorAdapter` that derives entry, cancel and close wire
  commands exclusively from the journal-approved domain models, exact requested
  volume, attempt ID, fixed account/symbol/experiment and broker identifiers already
  in durable evidence. Browser input cannot choose broker tickets or volume.
- AC-04: Polling atomically claims at most one command. Repeated polls return the
  exact claimed dispatch until its result is accepted. An expired command that was
  never claimed is not delivered. A response wait is bounded; timeout leaves the
  service command `UNKNOWN`, withdraws only an unclaimed dispatch and never sends a
  replacement.
- AC-05: Accept only a strict result bound to boot fence, dispatch sequence, attempt,
  generation, command, target and operation. Exact duplicate results are idempotent;
  conflicts are denied. Entry results carry `BrokerSnapshot`; cancel/close results
  carry `ManagementSnapshot`; an explicitly uncertain result raises an ambiguous
  adapter failure and therefore remains `UNKNOWN`.
- AC-06: Represent a confirmed no-effect broker rejection without inventing an
  order/deal/position identifier. Persist retcode, external retcode, request ID and
  observed UTC time. Only reviewed no-effect retcodes are terminal rejection;
  timeout, disconnected, locked/processing, changed-order and already-closed results
  require snapshot reconciliation and cannot release exposure from a retcode alone.
- AC-07: A confirmed rejected entry becomes terminal `REJECTED` and releases its
  reserved exposure. A confirmed rejected management command becomes terminal
  `REJECTED` while its parent broker snapshot and exposure remain unchanged; a close
  parent returns from `CLOSING` to the state derived from the retained snapshot.
- AC-08: Query methods read only already accepted inventory/result evidence. They do
  not enqueue, expose, re-attempt or increment a dispatch. Startup admission can use
  the authenticated adapter only after a fresh complete inventory has arrived.
  Preserve historical rejection event time during restart reconciliation; do not
  relabel it as stale merely because the fresh inventory reports it later.
- AC-09: Reject unauthenticated, malformed, duplicate-key, non-finite, oversized,
  stale, future, wrong-boot, wrong-generation, wrong-attempt, wrong-target and
  conflicting payloads without echoing account data, secrets or raw broker comments.
  Entry and management commands cannot reuse a command ID across their shared
  evidence namespace. All executor routes use `Cache-Control: no-store`.
- AC-10: Add failing-first API, adapter, service/journal rejection and recovery tests.
  Extend installed-package, static source, schema/recovery and container checks for
  the new files. Actual MetaEditor compilation, EA mutation, MT5 transaction ordering,
  target-host networking and a Demo round trip remain `NOT RUN`.

## Transport boundary

The executor calls only these internal routes:

- `GET /executor/v1/status` returns redacted disabled/awaiting/connected/stale/rejected
  state and never returns a credential or account identity.
- `GET /executor/v1/challenge` returns the current API boot fence and next inventory
  sequence only after executor authentication.
- `POST /executor/v1/inventory` publishes one cumulative inventory frame.
- `GET /executor/v1/commands/next` claims or repeats the active dispatch and returns
  `204` when no command is eligible.
- `POST /executor/v1/outcomes` publishes one bound snapshot, confirmed rejection, or
  uncertain result.

Authentication uses a dedicated Bearer credential that is not the telemetry token,
owner token or Supabase key. The future EA must still perform an immediate local Demo
identity, permission, contract and broker-state check before any `OrderCheck` or
`OrderSend`; API validation cannot replace that mutation-boundary preflight.

## Result classification

`OrderSend=true` and `TRADE_RETCODE_PLACED/DONE/DONE_PARTIAL` are not terminal
evidence by themselves; the EA must reconcile orders, deals, positions and broker-side
SL into a cumulative snapshot. Transport failure and return codes whose effect may
still be changing or unknown are submitted as uncertain or omitted until inventory
can prove the state. Confirmed rejection is limited to a reviewed allowlist for which
the EA has also reconciled that no order, deal or position effect exists.

Raw broker comments are intentionally excluded. Numeric return codes and durable
identifiers provide bounded evidence without leaking account or broker text.

## Failure and recovery

- Before poll claim: an expired or timed-out pending dispatch is withdrawn and never
  exposed, while the durable command conservatively remains `UNKNOWN`.
- After poll claim: timeout or lost HTTP response is ambiguous. The same dispatch may
  be polled/reported again but no new attempt or replacement command is generated.
- After API restart: the old boot fence is invalid. The EA must post a new complete
  inventory under the new boot fence; durable `UNKNOWN` work is resolved by query-only
  reconciliation, not automatic resend.
- After executor restart: a generation change is admitted only while no dispatch is
  active. Startup remains closed until a complete fresh inventory reconciles local
  durable state.
- A malformed or conflicting outcome latches the bridge rejected and wakes the
  waiting adapter with failure so the service records `UNKNOWN`.

## Exclusions and evidence limits

No MQL5 execution EA, terminal credential, actual broker request, owner order-entry
route, UI trade control, automatic strategy dispatcher, VPS deployment, alert
delivery, halt release, daily rollover or actual Demo result is included. Synthetic
HTTP concurrency and failure fixtures demonstrate the local protocol only. They do
not prove MT5 behavior, network topology, broker return-code semantics for a target,
or target-host recovery.

## Required verification

Run targeted SCN-012 tests first, then the full Python safety suite, lint, installed
artifact verifier and affected container/static checks. Retain exact revision,
runtime, fixture and verifier output. `BLOCKED`, `SKIPPED`, `UNKNOWN` and `NOT RUN`
are not `PASS`.
