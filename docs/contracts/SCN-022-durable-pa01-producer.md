# SCN-022 durable PA01 producer

## Task contract

Add an explicit, disabled-by-default worker path that reads one bounded PA01
decision from the immutable native M1 archive and an owner-only policy-evidence
file, journals the exact receiver payload before any HTTP write, publishes it to
the existing backend-only Supabase receiver, and independently reads it back
before advancing the local decision cursor.

This increment can populate `/api/owner/signals` when every configured source and
the eligible Supabase experiment exist. It does not create policy evidence, infer
missing market/news/account facts, create a command, size risk, call MT5, promote a
strategy, deploy a service or enable Auto Trading.

## Source and decision rules

- The native source is the existing pinned SCN-007 SQLite archive. A query-only
  snapshot validates the exact schema, archive binding, immutable rows and file
  identity before returning at most 6,120 M1 rows available at the policy cutoff.
- The policy source is one stable, owner-only, non-linked regular JSON file that
  validates as `PA01PolicyEvidence`. It is an integration boundary, not an
  assertion that its future writer is implemented or trustworthy.
- Policy cutoff must not be in the future or already beyond the 30-second signal
  expiry when a new decision is prepared. Archive, symbol, feed, offset and grid
  must agree. Aggregation and envelope construction use the existing pure SCN-019
  and SCN-021 boundaries.
- At most one decision is prepared for each strictly newer M5 formation time. The
  durable cursor moves only after exact independent receiver read-back.

## Durability and transport rules

- A private SQLite WAL journal stores a canonical payload and digest in
  `PREPARED` before an external write. Immediately before send it durably changes
  to `UNKNOWN` and increments the bounded attempt count.
- `UNKNOWN` always performs read-back first. A missing row may return to
  `PREPARED`, but is never resent in the same step. An exact row becomes
  `VERIFIED`; malformed or conflicting evidence becomes permanently
  `QUARANTINED`.
- A successful store response is not acknowledgement. The driver still uses the
  separate `sochron_read_pa01_decision` RPC and compares the receiver record with
  the exact journaled owner, strategy, experiment, protocol, fingerprint,
  snapshot and signal.
- HTTP is limited to the two fixed RPCs at one pinned origin, with a backend key
  read from a separate owner-only file, no redirects, no environment proxy,
  bounded bodies/responses and bounded timeouts.
- Import and default Compose startup perform no work. A separate installed
  `sochron-pa01` command requires an explicit private config and operator action.

## In scope

- Bounded native archive and policy-file readers.
- Deterministic decision source using the existing aggregation and envelope code.
- Private SQLite journal, one-step driver, Supabase HTTP transport and explicit
  init/status/run/reconcile CLI.
- Restart, lost-response, read-first UNKNOWN, no-duplicate, source-replacement,
  stale policy, conflict and configuration-denial tests.

## Out of scope

- The MT5/API/news/execution adapters that must atomically produce the policy file.
- Automatic OS scheduling, default Compose enablement, hosted Supabase writes or
  VPS deployment.
- Research evaluation/statistics, promotion, risk admission, execution commands,
  broker mutation or live trading.

## Acceptance criteria

- **AC-01 bounded source truth:** only verified closed native M1 rows available at
  the explicit cutoff are admitted; changed schema/binding/file identity,
  replacement, future/stale policy or mixed identity fails closed.
- **AC-02 exact decision:** source evidence is passed through the existing
  aggregation and envelope revalidation, producing at most one decision per
  strictly newer M5 formation time with no caller-supplied action.
- **AC-03 journal before send:** the exact canonical envelope and digest are
  durable in `PREPARED`, then `UNKNOWN`, before transport invocation. Journal
  failure causes no send and cursor advancement requires `VERIFIED` read-back.
- **AC-04 UNKNOWN reconciliation:** timeout or interruption remains `UNKNOWN`;
  restart reads first, exact committed evidence verifies without resend, and a
  missing row requires a later step before the bounded resend.
- **AC-05 conflict isolation:** changed, foreign, malformed, partial or duplicate
  receiver evidence and confirmed receiver rejection quarantine the decision and
  permanently block later source decisions until operator review.
- **AC-06 pinned private operation:** paths, source/destination identities, code
  hash and database IDs are bound in the journal; configs/keys are stable
  owner-only files and errors never print secrets, payloads or paths.
- **AC-07 no authority expansion:** the producer can call only the PA01 store/read
  RPCs; it creates no command/risk/order and reports execution readiness and Auto
  Trading as false.
- **AC-08 regression gates:** targeted failure tests, full Python checks,
  installed artifact and affected Linux-container checks pass without weakening
  existing database, API, browser or synchronization assertions.

## Evidence boundary

A passing SCN-022 proves a local synthetic end-to-end decision publication and
crash-reconciliation path. It does not prove the policy file's future writer,
actual market/news/account source parity, a hosted write, scheduler uptime,
strategy performance, Demo execution or release readiness.
