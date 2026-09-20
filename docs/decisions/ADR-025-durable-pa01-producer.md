# ADR-025: explicit durable PA01 producer

- Status: Accepted for local Demo integration
- Date: 2026-09-20

## Context

SCN-018 through SCN-021 provide the pure PA01 calculation, native aggregation,
complete policy-context envelope and atomic Supabase destination. None reads the
archive, owns a durable producer cursor or handles an ambiguous external write.
Calling the receiver directly from a timer would lose the journal-before-send and
UNKNOWN-before-retry invariants.

The API currently holds quote and execution observations in separate runtime
boundaries and there is no news/session evidence producer. Inventing those values
inside the strategy worker would create misleading decision evidence. The next
step therefore needs a strict integration seam that is runnable with synthetic
or future real source evidence but fails closed when that evidence is absent.

## Decision

Add a separately invoked PA01 worker. It reads the existing immutable native M1
archive directly through a bounded, query-only adapter. A second adapter reads one
stable owner-only `PA01PolicyEvidence` JSON file. The file is explicitly a source
contract: this change validates and consumes it but does not claim the future
MT5/API/news/account writer exists.

The source aggregates at the policy cutoff, builds the protocol-v2 envelope and
returns it only when its M5 formation time is newer than the verified local
cursor. New preparations must still be inside their 30-second expiry. A private
SQLite journal binds archive, policy path, owner, destination, strategy database
identity and code hash. It retains immutable canonical payloads in
`PREPARED`, `UNKNOWN`, `VERIFIED` or `QUARANTINED`.

Use the same conservative delivery state machine as native synchronization:
journal before send, mark UNKNOWN before calling HTTP, independently read after
every store response, and read first after any ambiguous outcome. Only an exact
receiver record advances the formation-time cursor. A confirmed conflict or
malformed read-back quarantines the decision.

Expose this through a new installed `sochron-pa01` CLI with explicit
init/status/run/reconcile actions. Configuration absence means disabled. Import,
API startup and default Compose startup remain inert.

## Rejected alternatives

- **Infer policy state from the last bar:** rejected because bars do not prove the
  current spread, session, news window, exposure or pending-order state.
- **Hard-code safe blocker values:** rejected because even a BLOCK signal would
  falsely attribute evidence that was never observed.
- **Write directly without a journal:** rejected because a committed response can
  be lost and a retry could conceal conflicting evidence.
- **Treat the store response as acknowledgement:** rejected because only an
  independent read proves the durable linked snapshot/signal pair.
- **Run from API or Compose startup:** rejected because source credentials,
  lifecycle and failure isolation are not yet admitted for unattended operation.
- **Store only the latest decision:** rejected because historical snapshots are
  immutable evidence and cursor advancement must be auditable.

## Consequences

- A configured local environment can publish exactly one durable PA01 decision
  for a new closed M5 bar and make the owner Signals UI leave `awaiting_source`.
- Lost responses and process restarts do not silently resend before reconciliation.
- A real policy-evidence writer, target scheduling, hosted credentials and target
  recovery remain explicit release gaps. The worker cannot create trades or
  enable Auto Trading.
