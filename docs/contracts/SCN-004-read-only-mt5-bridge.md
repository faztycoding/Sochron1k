# SCN-004 Read-only MT5 bridge

## Contract and scope

Version 1.0; High assurance; child of SCN-001. The full product goal remains a
usable Demo system, not a simulator-only substitute. This work unit supplies the
missing authenticated telemetry ingress before the EA and browser integration.
It does not grant any broker-operation or deployment authorization.

Receive sampled account, contract and Bid/Ask snapshots from one configured Demo
identity. Expose only connection/freshness status anonymously. Account values and
raw snapshots require the executor credential; browser Auth is a separate gate.
There are no order, close, cancel, halt-release or strategy-promotion endpoints.

## Acceptance criteria (written before implementation)

- AC-01: With no private bridge configuration, ingress is disabled. Reject absent,
  wrong, duplicated or malformed credentials before consuming a request body.
  A valid bridge token is separate from browser credentials. Error responses,
  public status and application logs must not echo payloads, identities or tokens.
- AC-02: Accept only the pinned executor/account/server/currency/margin-mode/symbol
  identity and explicit `demo` trade mode. Reject real, contest, unknown, missing,
  changed and extra fields. Invalid authenticated frames invalidate current
  telemetry readiness until a new, valid, higher-sequence frame arrives.
- AC-03: Validate finite numeric data, Bid <= Ask, contract bounds and aware UTC
  observation time. Preserve raw broker tick time, the explicitly configured
  broker UTC offset, normalized UTC event time and API receipt time separately.
  Do not infer the broker timezone from Bangkok or the host's local timezone.
  Missing offset configuration blocks ingestion; an offset change requires a
  reviewed configuration restart. Reject future and excessively delayed observation
  frames; allow at most one second of tick lead for terminal clock granularity.
- AC-04: A random per-process challenge prevents replay from an earlier API
  lifetime. Exact duplicate sequence/payload is acknowledged without refreshing
  freshness; changed duplicates and out-of-order events are rejected. Sequence
  checks and replacement are atomic under concurrent requests.
- AC-05: Derive heartbeat and tick freshness at read time, including monotonic
  elapsed time so wall-clock rollback cannot make an old sample fresh. Retain
  stale observations as stale, never synthesize prices. A fresh heartbeat with an
  unchanged old tick cannot report a fresh market. API restart starts empty.
- AC-06: Bound JSON requests to 16 KiB (including chunked requests), enforce JSON
  content type, reject ambiguous JSON and bodies exceeding a two-second read
  deadline, redact validation errors, and disable caching on bridge responses.
  A live HTTP smoke check and negative API/clock/concurrency tests must run.
- AC-07: An actual EA is compiled with a recorded MetaEditor build and source
  digest, receives the challenge, sends Demo-derived data and demonstrates
  identity changes/disconnection on the selected terminal. This criterion cannot
  pass from Python fixtures or a source-only MQL5 review.
- AC-08: Telemetry cannot enable execution. Existing health always reports
  `auto_trading_enabled=false` and `execution_ready=false`; trade routes are absent.

### EA source preparation (does not replace AC-07)

- EA-01: Off by default; no timer/network activity until explicitly enabled with
  a complete local identity. Deny non-Demo/changed account or symbol before every
  outbound observation. No order/close/cancel APIs, trading-library or DLL imports.
- EA-02: Read the scoped token only from a fixed terminal-local file, never an EA
  input, URL or log. Destination is the fixed local API; no configurable external
  destination. Never print credentials, account identity, prices or response bodies.
- EA-03: Read real terminal/account/symbol/tick properties, preserve raw tick time,
  serialize decimals and UTC observation consistently with `TelemetryFrame`, and
  label sampling explicitly. Never replace a stale tick with an invented timestamp.
- EA-04: Obtain the current API challenge; validate bounded response shape and
  positive safe-integer sequence. Parse receipts, not just HTTP success. After a
  transport/receipt failure discard the sample and refresh the challenge on a
  later timer; no order or fill state is inferred. Identity failure latches until
  explicit EA reinitialization; disconnection sends nothing.
- EA-05: One network request per one-second timer, 500 ms requested timeout,
  bounded retry backoff. This dedicated observer is not an execution/risk EA;
  actual worst-case blocking duration remains part of AC-07, not a source claim.
- EA-06: Supply a terminal-side pure protocol self-test and Python API acceptance
  of a synthetic golden wire fixture. Static source checks can establish only
  the reviewed include graph/absence of forbidden APIs, not compilation or runtime
  enforcement. Retain explicit NOT RUN status for the MQL self-test until executed.

## Evidence and current state

AC-01 through AC-06 and AC-08 have local Python/HTTP evidence: 51 targeted tests
in `tests/test_telemetry_bridge.py` and `scripts/check-bridge-local.py` passed on
Python 3.14.7, macOS arm64, synthetic fixtures. The full Python suite passed 78
tests. Candidate base `7f6db02` plus pending source hashes is identified by the
HTTP verifier; rerun on the saved revision before delivery. Retained clean-revision
reports belong under `output/verification/` and are not broker evidence.

EA source preparation now exists under `mt5/ea`: an opt-in read-only observer,
shared protocol helpers and a terminal self-test. Fifteen Python tests cover the
static guard (including forbidden-operation mutations) and synthetic golden
fixture/API compatibility. The full local Python suite has 93 tests. Source and
fixture verifier reports explicitly exclude MQL compilation/runtime evidence.

AC-07 is still BLOCKED on the selected MT5 host,
terminal/compiler and Demo identity. No MT5 installation was found by filename
inspection of `/Applications` and the user's `Applications` directory on
2026-09-17; this is not an exhaustive inventory of every Wine prefix.
Spotlight filename lookup also returned no terminal/compiler match. MQL source
compilation and the 24-case terminal self-test are NOT RUN. See
[`mt5/ea/README.md`](../../mt5/ea/README.md) for the pending verification procedure.

## Required next integrations

1. Compile and verify the sampled-data EA source against this wire contract.
2. Verify the broker's tick timestamp offset and contract on the authorized Demo
   terminal, including server DST changes. Clock synchronization is required.
3. Add authenticated owner access and bind the UI to confirmed observations.
4. Extend to raw ticks/closed bars and persistent history for research (sampled
   snapshots cannot prove intrasecond SL/TP ordering).
5. Implement execution fencing, durable journal/reconciliation and Demo round-trip
   gates before adding any account mutation. A telemetry lock is not an execution lock.

## Runtime boundary

One API process, one configured producer, loopback-only local prototype. The
in-memory latest snapshot is disposable monitoring state, not a journal or
recovery authority. Restart loses it deliberately and changes the challenge.
Multi-worker operation and public deployment are not supported by this contract.
Configuration is an owner-only private file outside the repository; failures
must stop startup without disclosing its contents. Tests use generated ephemeral
tokens and synthetic identities only.
