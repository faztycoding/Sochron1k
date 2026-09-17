# SCN-008 AC-04 durable synchronization journal

2026-09-17. Base `a72ccd98daa2e548f076a7442043ee3db41ff397`; candidate dirty
during verification. Python 3.14.7, SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8,
macOS 26.6.2 arm64. Fixtures use only generated synthetic bars and temporary local
databases. No hosted service, credential, MT5 account, deployment or trading action.

## Outcome and scope

AC-04 has local library evidence. `SyncJournal` retains immutable exact intents,
single-pending uniqueness, attempt counts and the receipt/time cursor. It validates
private canonical paths, ownership/modes, link count/inodes, pinned source and
owner/destination, exact schema SQL, payload fingerprints and full ledger order
on restart. It rejects missing state without recreating it; explicit initialization
requires an empty private directory and cannot reset existing/partial state.

`SyncDriver.step()` journals UNKNOWN before external send. ACK alone never advances
the cursor. A separate destination read must match archive binding and every bar's
exact JSON values and valid conservative availability. Missing/partial matching
rows permit a later retry, never an immediate send in the same recovery step.
Invalid/conflicting evidence quarantines persistently. VERIFIED and cursor advance
in one transaction; write failure rolls back both. No broker operations exist here.

This is not an enabled service: destination calls in these tests implement the
protocol locally. AC-05 private configuration/HTTP/retry scheduling, AC-06 real
PostgREST integration and AC-07 operator delivery remain NOT IMPLEMENTED / NOT RUN.
Full Demo is NOT READY; Auto Trading stays disabled. UI, PostgreSQL receiver and
actual MT5 were not retested by this change.

## Tests and observed failures

- `.venv/bin/pytest -q tests/test_sync_driver.py`: **46 PASS**.
- `.venv/bin/ruff check services/worker/src tests/test_sync_driver.py`: PASS.
- `bash scripts/check-scn-001-local.sh`: **358 PASS**, Ruff and secret scan PASS.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: PASS. Installed copies and repository custom skill sources
  match the pinned registry; this is integrity, not actual broker/tool operation.

The tests observe committed UNKNOWN, attempt count and exact intent through an
independent SQLite connection at the moment the destination is invoked. ACK with
no rows leaves cursor zero. Lost response, read failure, partial result and restart
keep the expected state and exact original availability. Valid different destination
availability is accepted without rewriting it, matching receiver replay semantics.

The process-crash fixture starts another Python interpreter, which opens the journal,
commits one snapshot to a separate SQLite destination and calls `os._exit(73)` before
read-back. Parent observes UNKNOWN/attempt=1/cursor=0. Reopened driver independently
reads that durable destination, reaches VERIFIED and never invokes a second store.
The destination row count remains exactly one. A separate live process attempting
the already-held state directory exits with lock denial and zero destination rows.

Storage tests use SQLite's authorizer to deny the intent insert, UNKNOWN update,
or the cursor update after the VERIFIED row update. Independent subsequent reads
prove no dispatch or atomic rollback as appropriate. Another fixture lowers the
page quota to the current database size, submits a separately validated large
intent, and checks the underlying SQLite error is **SQLITE_FULL**. It leaves no
pending row/cursor advancement. An independent writer lock also denies dispatch.
These are local quota/transaction tests, not an actual full host disk or power cut.

Other coverage includes immutable payload/delete guards, repeated prepare and
denied state transitions, persistent conflict quarantine, destination/source drift,
clock rollback, file permissions/hardlinks/missing lock, altered schema/columns/
indexes/triggers, digest/attempt/time/sequence corruption, late older bars after a
later receipt and old ledger corruption across multiple VERIFIED batches. Storage
warnings exercise both 70% and 85% thresholds. Shared-journal driver calls cannot
interleave a send and recovery read.

Before the fixes, targeted tests reproduced **five failures**: removed trigger,
removed unique index, added column, metadata clock preceding the batch update,
and two drivers interleaving on one journal object. A later test also reproduced
acceptance of a negative sequence number. Exact schema checks, timestamp/sequence
audit and a shared journal step lock close these failures without weakening tests.
Initial unused imports and Ruff findings were corrected before the final run.

## Exact candidate identities

SHA-256:

- `services/worker/src/sochron_worker/sync_journal.py`:
  `270b8d6629abb8a248e807682ee74842e507c8dc0a26095262b5b58c840d5946`
- `services/worker/src/sochron_worker/sync_driver.py`:
  `c6e36396e7ab941bf9d78c0b084e31ae2a6eaa000be8fb1780b968ac73777f35`
- `tests/test_sync_driver.py`:
  `3e20510c7466fe9dc15fb06e0ce21bb59b337412ec8939a94ef96eb246b4a3f1`

## Limits and next work

Durability configuration is checked per connection: WAL, synchronous FULL,
fullfsync/checkpoint_fullfsync and 64 MiB page quota. Writes use BEGIN IMMEDIATE
and a 100 ms busy timeout. The implementation follows
[SQLite synchronization semantics](https://www.sqlite.org/pragma.html#pragma_synchronous)
and [transaction rollback behavior](https://www.sqlite.org/lang_transaction.html).
These settings and process-crash observations do not prove hardware/power-loss
durability. The startup full-ledger audit is not benchmarked at quota. Runtime
checks do not reread every verified historical payload on every step.

The [Python 3.14 flock interface](https://docs.python.org/3.14/library/fcntl.html#fcntl.flock)
provides the POSIX advisory process lock. Private paths/hashes detect accidental
replacement or corruption, not a compromised same-user host rewriting all evidence.
Python-private methods and protocol attributes are trusted implementation boundaries,
not a sandbox. No tokens are stored in this journal. Strict origin/credential
validation, redirects/proxy denial, deadlines and bounded actual HTTP responses
belong to AC-05 and are still required before enabling synchronization.

The next task is private transport/config and the runnable worker, followed by
local PostgREST/crash evidence and operator instructions. Real Demo still needs
owner/broker/account/executor configuration and target-environment gates.

The [sochron-risk-recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md)
guided journal-before-send, UNKNOWN recovery and independent durable-effect tests.
PDF inspection of Blueprint sections 13-16 and 22-23 confirmed the existing
product invariants; no risk policy or trading authorization was changed.
