# SCN-010 Execution startup admission

2026-09-17, High assurance, base c31adbb. Local implementation under the full Demo
goal, not authority to operate an MT5 account. Extends SCN-001 AC-03/04/05/06.
Acceptance recorded before implementation.

## Required outcome

Every new ExecutionService starts closed to submissions. Explicit startup must
verify a complete, fresh executor inventory against pinned Demo account/server/
currency/margin/symbol/executor identity and the active experiment, restore an
existing risk baseline and reconcile retained active commands before admitting
local submissions. A missing baseline, unknown foreign exposure, incomplete or
unavailable inventory, unresolved command or mismatch keeps admission closed.
Startup never creates a baseline, clears a halt or sends/replays a command.

## Local acceptance

- AC-01: Introduce an explicit adapter inventory contract and simulator implementation.
  No automatic configured identity from a submitted request. Require Demo mode,
  complete inventory, aware UTC-compatible times no more than five seconds old,
  no future/naive timestamps, matching expected identity and stable executor
  generation. Foreign orders/positions or unknown command identifiers deny startup.
- AC-02: Require existing active-experiment risk state, the current Bangkok day,
  no future risk timestamp and unchanged baselines/halts. Inspect retained active
  commands and exposure relationships; reject foreign-account/experiment state,
  missing/unmatched commands and invalid command fingerprints. Reconcile only
  actual matching inventory snapshots; absent evidence is not proof of no order.
- AC-03: Revalidate the bound inventory and persistent risk before each submit.
  A restarted/new/fork-inherited service has no admission; query-only recover alone
  cannot grant it. Serialize service operations, reject changed policy/experiment/
  executor generation and close admission on validation/journal/adapter failure.
  Preserve per-command idempotency and account-wide one-exposure reservation.
- AC-04: Before applying broker evidence transactionally, validate volume balance,
  aggregate deals, identifiers, command volume/dispatch evidence and immutable
  ticket ownership. Reject changed/omitted existing deals, reduced fill and terminal
  regression without modifying the journal. Risk state is rechecked atomically
  with reserve and begin_dispatch so a concurrent halt/baseline change prevents send.
- AC-05: Add failing-first startup/baseline regressions, negative inventory/identity/
  clock/foreign/unknown cases, generation/restart/fork, persistent-halt, concurrent
  risk/exposure and broker-evidence corruption tests. Keep original duplicate,
  timeout, partial-fill, SL and recovery assertions. Use fresh installed artifacts
  and affected Linux checks; actual MT5 identity/inventory coverage remains NOT RUN.

No execution route, real-account path, automatic worker/service start, halt release,
close/cancel implementation or target release is supplied by this increment.
The Python gate is not distributed executor fencing or a hard I/O deadline. A
complete MT5 inventory producer, broker OrderCalcProfit, close/cancel reconciliation,
target crash tests and approved Demo round trip remain required. Public API health
and all release-level execution/Auto Trading flags remain false.

## Candidate review additions (2026-09-20, before fixes)

Review the checkpoint against these explicit negative cases: a known rejected
command in inventory must still have validated zero-fill/volume/ticket evidence;
its terminal label alone cannot justify admission. Optional low-level expected-risk
arguments must identify the command's actual account and experiment. A pre-dispatch
QUEUED command cannot gain fill evidence just because an orphan attempt exists.
Unexpected adapter response/exception after invocation must retain UNKNOWN when
the journal is writable, while a journal failure still prevents a successful
result. Runtime dispatch/close/release authority remains unchanged.

## Evidence status

Local AC-01 through AC-05 are verified against the simulator, fresh installed
artifact and the affected API/worker Linux images. The review additions above are
covered by failing-first regressions. This does not verify an MT5 inventory producer,
broker mutation, target fencing, close/cancel, halt release or a Demo round trip;
those gates remain open. See [SCN-010 verification](../verification/SCN-010-execution-startup.md).
