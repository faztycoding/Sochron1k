# SCN-015 Owner execution evidence read model

2026-09-20, High assurance, base
`382bb9b996b8f446ec6d93d69f585755d1045376`. Local read-only implementation
under the full Demo goal; no browser mutation, MT5 account operation, deployment,
or unattended trading is authorized. Extends SCN-001, SCN-011, SCN-012 and
SCN-014.

## Required outcome

Add an authenticated owner API and UI projection for the durable execution
journal. The projection shows only locally recorded command state and confirmed
MT5 evidence: command, order, deal, position, cumulative volume and broker-side
SL confirmation. It must preserve `UNKNOWN` and must not infer a fill, close,
cancellation or protected position from HTTP delivery, an attempt, or a terminal
label alone.

The endpoint is read-only and disabled by default. An explicitly configured
existing private SQLite journal may be opened only in read-only mode. A missing,
mistyped, replaced, insecure, corrupt or incompatible journal cannot be created,
migrated or repaired by the API. Public health continues to report
`execution_ready=false` and `auto_trading_enabled=false`.

## Local acceptance

- AC-01: Add `GET /owner/execution` behind the existing per-request owner/session
  verification. Reject unauthenticated access, expose no mutation method and set
  `Cache-Control: no-store`.
- AC-02: With no journal configured, return a strict disabled Demo-only view with
  no invented commands. Loading configuration requires an absolute canonical
  path to an existing owner-private regular file with one link; reject symlinks,
  group/world access, unsupported SQLite/schema state and oversized files.
- AC-03: Pin the configured journal device/inode and verify it before and after
  each bounded read. Use SQLite URI `mode=ro`, `query_only`, foreign-key,
  startup quick-check/foreign-key validation and per-read required-table/column
  validation. Use immutable reads only when no WAL frames exist, disable
  checkpoint-on-close when a WAL is present, and do not create, migrate,
  checkpoint or change database/WAL content. SQLite's shared-memory lock region
  may change while coordinating a live WAL read.
- AC-04: Return at most 50 latest entry commands in deterministic
  `updated_at,command_id` order. Validate payloads and all stored identifiers,
  states, decimal values and aware UTC times through strict models before
  returning them. A malformed or swapped source yields a redacted unavailable
  view, never a partial trusted projection.
- AC-05: For each entry show the journaled command ID, symbol, side, requested
  volume, state and UTC creation/update times. Show order/position identifiers,
  cumulative fill/pending/cancel/close volumes, deal identifiers and SL status
  only when those records exist. Absence remains `null` or an empty collection;
  do not turn absence into negative broker evidence.
- AC-06: Show bounded cancel/close management commands and confirmed no-effect
  rejection codes only when journal records exist and bind to the selected entry.
  Raw payloads, idempotency keys, account references, broker comments, filesystem
  paths, credentials and auth claims are excluded.
- AC-07: Preserve `UNKNOWN`, partial fills, protection failure and unresolved
  management work exactly. The UI must label journal evidence as read-only and
  must contain no order, retry, halt-release or Auto Trading control.
- AC-08: Update the SCN-014 connection map so `/api/owner/execution` is an
  implemented route while runtime state still distinguishes unconfigured,
  available and degraded evidence. The public map must not reveal journal paths
  or private command data.
- AC-09: Add failing-first configuration, read-only/identity, corruption,
  bounds, schema, authentication, serialization, frontend parser and UI tests.
  Verify that a clean read creates no sidecars and that live-WAL reads leave the
  database and WAL bytes/metadata unchanged; shared-memory lock bytes are excluded.
  Actual MT5 evidence, MetaEditor compilation and a Demo round trip remain
  `NOT RUN`.

## API shape and UI position

The browser uses `GET /api/owner/execution`, proxied to
`GET /owner/execution` by the existing web boundary. The execution panel is
rendered inside the authenticated owner area after market/chart/history data and
before the static local-safety summary. This keeps private command evidence out of
the public connection map while showing the exact API location near its consumer.

The public `/ui/connections` row for execution lists both the internal executor
status route and owner read route. `available` means the API contract exists; it
does not mean MT5, a journal, broker identity, SL evidence, startup gates or Demo
execution are ready.

## Configuration and failure behavior

`SOCHRON_EXECUTION_JOURNAL_PATH` is optional. When absent, the owner endpoint
returns `state=disabled`. When present, startup validates the fixed file and fails
closed on an invalid private path. A source that becomes invalid after startup
returns `state=unavailable` with a bounded reason code; it does not expose the path
or SQLite error text.

The journal remains owned and written by the deterministic execution service.
This read model neither constructs `ExecutionService` nor invokes an executor.
WAL visibility is read using ordinary read-only SQLite semantics, not an
`immutable` snapshot that could ignore current sidecars.

## Exclusions and evidence limits

No command creation API, strategy dispatcher, browser-selected ticket/volume,
halt release, automatic retry, journal writer, schema migration, MQL5 mutation,
target-host verification, alert delivery or deployment is included. Synthetic
journal fixtures prove local projection and failure behavior only; they are not
evidence that MT5 filled, closed, cancelled or protected anything.

## Required verification

Run targeted SCN-015 Python and React tests first, followed by the full Python
safety suite, web type-check/tests/build, installed-package/static/container checks
affected by the new module, repository secret scan and the existing browser
verifier. Record exact revision, runtime, fixtures and unrun target gates.
