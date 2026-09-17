# SCN-008 AC-03 read-only native source

2026-09-17. Base `c7699803d8753fa3ca13206c4c6e69800420739d`, candidate dirty
during verification. Python 3.14.7, SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8,
macOS arm64. All source archives are generated synthetic fixtures in temporary
directories. No Supabase startup/write, MT5 operation, network send, deployment,
UI configuration change or credential provisioning occurred.

## Outcome and acceptance

AC-03 has local source-adapter evidence. `NativeArchiveSource` requires a private
canonical source directory, explicit archive UUID, Demo identity, verified offset
and chart validity interval. It does not need the bridge credential. It checks
schema version/table columns/types/primary keys and immutable trigger definitions,
binding, stable filesystem identity, exact payload hashes, receipt linkage,
UTC/closure/grid/precision constraints and bounded input size.

Each read uses a committed SQLite WAL snapshot and returns immutable payload
strings ordered by `(first_receipt,time_server_s)`. Only closed native M1 rows
are included; gaps remain gaps. Nonzero cursors must name an existing row in this
archive. Pages are bounded to 100 rows and 240,000 serialized bytes; omitted rows
do not advance the returned candidate cursor. Availability is UTC observed after
fetching committed rows, not candle time or precommit receive time. A naive clock
or wall time earlier than a source receipt denies the export.

This is a **library boundary, not an enabled sync service**. AC-04 journal/restart/
reconciliation, AC-05 private transport/config, AC-06 real HTTP/crash integration
and AC-07 operator delivery remain NOT IMPLEMENTED / NOT RUN. No returned cursor
is stored or counted as acknowledged by this source. Full Demo remains NOT READY
and Auto Trading remains disabled.

## Verification

- `.venv/bin/pytest -q tests/test_native_source.py`: **54 PASS**.
- `bash scripts/check-scn-001-local.sh`: **312 PASS**, Ruff PASS and secret scan PASS.
  The verifier now includes worker source in Ruff and pytest's import paths include
  both existing domain models and the new worker package. No new dependency.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: PASS. Installed skill/source integrity is unchanged.

Exact final candidate hashes (SHA-256):

- `services/worker/src/sochron_worker/native_source.py`:
  `8b648e83e1186f6ee8b55e1bc0228261efdca2d2fdd0bf889c8e650942d80ca0`
- `tests/test_native_source.py`:
  `0851e73ce131521b017e8eafd0c1af19035127d36f4a9ebe3f3e864f5789d674`

The final full suite was rerun after adding the SQLite value-size bound and
bounded metadata read. UI/browser, PostgreSQL and broker checks were not rerun:
their implementations are unchanged, and this is not new evidence for those gates.

The fixtures prove exact 24-digit/10-decimal prices and exponent tick strings,
same-receipt pagination, reopen/repeated reads, immutable result objects, non-M1
filtering, late older captures after later candles and no fabricated missing bars.
Main database bytes remain unchanged by source reads; direct writes through the
read connection fail. A missing database is not created.

An independent writer transaction is invisible before COMMIT and visible from a
new reader snapshot while a nonempty WAL exists. Another writer commits after the
reader fetched rows but before its availability observation; the current page
stays on the old snapshot and the next page sees the new row. This verifies WAL
snapshot behavior, not a simulated list or a process/power-loss recovery claim.

Negative fixtures cover malformed/duplicate-key/nonfinite/oversized/BLOB JSON,
digest mismatch and semantic corruption even with recomputed digests, bad closure,
receipt/build/offset/time/grid data, unknown schema/columns, removed or replaced
triggers, wrong archive, absent cursor, invalid page bounds, naive/rollback clocks,
file/directory permission changes, symlinks, hardlinks, inode replacement and
unsafe WAL-sidecar permissions. A recursive SQL query verifies cancellation via
the connection's progress deadline; OS filesystem stalls are not hard-bounded by
that mechanism. Errors use `NATIVE_SOURCE_UNAVAILABLE` without original path/data.

An initial added precision fixture was correctly rejected by the existing chart
contract because its telemetry still described two-decimal prices. The fixture
now supplies a matching ten-decimal telemetry contract before recording bars;
no chart gate or assertion was relaxed. Ruff findings were corrected before the
passing full run.

## Limits and next work

The reader uses URI `mode=ro`, defensive/query-only settings and does not checkpoint,
initialize, index or repair source data. It intentionally does not use
`immutable=1` on a changing WAL source. SQLite may create/update normal shared-memory
sidecars; read-only application data is not a claim of zero filesystem activity.
See [SQLite WAL snapshots and read-only databases](https://www.sqlite.org/wal.html)
and [URI mode/immutable semantics](https://www.sqlite.org/uri.html).

Source schema v1 has no receipt-order index. Reads have a two-second SQLite progress
budget and 100ms lock timeout; this is not proof of performance at the 128 MiB
quota or on the target host. A reviewed writer-side index migration/benchmark may
be needed; the reader must not silently add one. Long-lived reads are not kept
across network sends, so this adapter does not itself hold a snapshot during retry.

Private-path/inode checks and hashes detect accidental replacement/corruption,
not a compromised same-user host or an attacker who can rewrite all evidence.
Payload hashes are not signatures or MT5 authenticity proof. Current reads inspect
selected rows and the boundary cursor; they do not attest every historical row
on every page. Future worker state must pin source/destination, validate its own
durable batch on restart, maintain time/cursor invariants, reconcile UNKNOWN and
compare independent committed destination data before advancement.

The [sochron-risk-recovery skill](../../tooling/skills/sochron-risk-recovery/SKILL.md)
guided pinned identity, no source repair, exact values and independent database
effect tests. The blueprint's existing sections 13-16/22-23 remain the product
authority; no trading permission or risk-policy change is introduced.
