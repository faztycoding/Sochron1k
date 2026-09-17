# SCN-007 local history verification

This is the capture/API checkpoint. The subsequent owner history UI increment
is recorded in [SCN-007 AC-08 workspace evidence](SCN-007-history-workspace.md).

2026-09-17. Candidate based on `601dfdbac24fb78ee7935bfea03d36962467e4ee`, dirty
during verification. macOS 26.6.2 arm64, Python 3.14.7, SQLite 3.53.1 and pinned
Node 24.21.0. All market
and account data in these tests are synthetic. No broker, hosted database or
deployment operation occurred. Developer servers/configurations were not changed.

## User-visible outcome and changed scope

An opt-in private SQLite archive now retains closed native bars and provenance
before chart acknowledgment. Owner-authenticated `/owner/history/{timeframe}`
returns bounded pages tied to one archive and receipt watermark; the live chart
UI itself is unchanged and does not yet browse this history. API restart retains
validation baselines while leaving live views empty. Disabled history remains
explicitly disabled; local test evidence does not provision an actual archive.

Changed boundaries: new archive/schema, chart accept-before-publish ordering,
threadpool handoff, owner history route, private startup configuration, HTTP
verifier, tests and runbooks. No new dependency, Supabase migration, execution
endpoint, MQL edit, credential or UI feature is included.

## Executed checks and oracles

- `bash scripts/check-scn-001-local.sh`: **258 PASS**, Ruff and source secret scan
  PASS (149 text files before this evidence document was added). Includes all
  existing risk/journal, telemetry, chart and owner authorization regressions.
- `.venv/bin/pytest -q tests/test_bar_history.py`: **29 PASS** on real temporary
  databases. Receipt/bar/checkpoint row counts and independent database reads are
  the persistence oracle; tests do not merely assert the returned HTTP status.
- `.venv/bin/ruff check services/api/src tests scripts/check-bridge-local.py`:
  **PASS**.
- `.venv/bin/python scripts/check-bridge-local.py`: **PASS**, real loopback Uvicorn
  with configured private history. After HTTP acknowledgment, a separate SQLite
  connection sees exactly 239 closed rows for a 240-bar window and one receipt.
  Duplicate and rejected corrections do not add receipts/rows. Reopening after
  API shutdown retains those counts, the latest validation frame and a successful
  SQLite quick check. The verifier reports exact revision/dirty state and SHA-256
  for implementation/tests; temporary fixtures are cleaned up, not published.
- `npx -y -p node@24.21.0 npm run check:web`: **PASS**, typecheck, **73 component
  tests**, production build and client-bundle secret scan. No browser E2E run or
  visual change is claimed for this increment.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: **PASS**. Skill integrity does not prove integration.

Final implementation SHA-256 identities (also emitted by the HTTP verifier):

| File | SHA-256 |
| --- | --- |
| `bar_history.py` | `c5f3d46d171f37f6635e1ef44bbee71bbf179b1887a7288d59d93e10b41fa117` |
| `chart.py` | `1c82a415761ec756ff1a5567e880ada65fa8510e70359bae8d24c772c9b1ed49` |
| `chart_api.py` | `7bb178a0dd3f839a298549f6c0a2d93cb067784dcbfb3288b1547c4ae87ccb40` |
| `main.py` | `ba7b5c1114084f8d54f09c4bb7757e4b3375155d9dfe9406dbae5a749c0eb936` |
| `tests/test_bar_history.py` | `b6b84f4794a41a44f3bf9599a47e6795b74d1f8b9b55b7671a485307a6b9cf16` |
| `scripts/check-bridge-local.py` | `ac34ef731d4b26d7c168a11643bff45f067e0b691fddbab85563a4b5ad60d087` |

## Acceptance coverage

AC-01: private directory/file modes, file/sidecar/directory symlinks, hard links,
missing/replaced files, wrong schema/identity/offset interval, corrupted database
or projections and startup configuration denial. Files are never automatically
recreated after removal. Same-user privileged tampering is not prevented by these
checks, SQL triggers or non-keyed hashes; this is not a security sandbox.

AC-02: exact decimal persistence, first receive/observation times, the later native
bar used to infer closure, forming-row exclusion, immutable closed evidence,
matching/conflicting receipt uniqueness and independent concurrent connections.
An injected failure at the final projection insert rolls back receipt and bar
inserts together. Existing evidence survives equivalent decimal representations.

AC-03: blocked/full storage produces no chart publication or sequence advance;
ingress returns a redacted 503 and stays latched even after the immediate fault is
removed. History-read failure also latches chart ingress. Quote status is unaffected.
A deliberately blocked record call runs in a thread while a concurrent health
request completes; invalid-body rejection also avoids waiting on the chart lock
in the event-loop thread. The 100ms SQLite lock wait is not an fsync/I/O deadline.

AC-04: restarted bridge gets a new boot, rejects old packets and restored closed-bar
corrections, and exposes no cached live observation. Two subprocess tests terminate
at the real SQLite commit boundary: before commit leaves zero records; after commit
leaves one receipt/two closed bars/one validation projection. Replaying that capture
does not duplicate it. Backward received time is rejected. These are process-exit
tests, not sudden power-loss or storage-controller durability tests.

AC-05: anonymous/executor/foreign-owner denial uses the existing live owner verifier
with a mocked Auth upstream; owner success, no-store headers, query bounds and
missing/mismatched archive ID/future watermark denial are tested. Advancing the
source cannot add newly closed bars to an older read watermark. First receive time
is not replaced with historical candle time. No claim that a strategy had data
before capture is made. Actual Supabase/owner/browser history integration is pending.

AC-06: quota fault tests cap the test database at its existing page count and force
a larger atomic insert to fail without pruning prior rows. 70%/85% response states
are tested separately. Production page quota remains 128 MiB; SQLite sidecar and
filesystem usage, target alerting and long-running capacity are not verified.
Unclassified gaps are retained, including across bounded page boundaries.

AC-07: the above unit/integration/process/HTTP checks provide local evidence only.
Dependency signature audits were not rerun; the prior whole-tree registry signature
failure remains unresolved. No browser, MT5 compiler, terminal, Demo order, VPS,
backup/restore, Supabase synchronization or power-loss check is silently marked PASS.

## Decisions, limits and next safe work

The risk/recovery skill informed WAL/FULL on every connection, atomic writes,
failure latches and subprocess evidence. Research-validation guidance and blueprint
sections 06/15/23 kept event/receipt times separate and excluded forming bars. The
PDF skill was used to inspect source pages (the text extractor's Thai output was
not adequate alone); no PDF was edited. FastAPI guidance informed typed owner
routes and moving blocking storage work outside async request processing, reusing
the installed Starlette threadpool rather than adding a dependency.

SCN-007 is locally verified for its capture/API scope. The full Demo product is
**NOT READY**; Auto Trading remains off. Next work remains Supabase M1 synchronization,
raw-tick capture, history UI, reproducible feature/strategy/statistics work, MT5
compilation and authorized actual data/execution comparisons, risk/recovery gates,
backup/restore, alerting and target-host burn-in. Owner/broker/host/Auth choices
remain necessary; passwords and privileged keys must not be requested in chat.

References: [ADR-008](../decisions/ADR-008-local-native-bar-history.md),
[operator runbook](../operations/local-mt5-bridge.md#durable-native-bar-history-scn-007),
[SQLite durability settings](https://www.sqlite.org/pragma.html#pragma_synchronous),
[Python 3.14 SQLite transaction semantics](https://docs.python.org/3.14/library/sqlite3.html).
