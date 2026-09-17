# SCN-006 MT5 market chart

Version 1.0; High assurance; extends SCN-004/005. Owner: project owner.
Full goal remains a usable Demo application; this contract does not authorize
broker orders, deployment, new paid services or a hosted database mutation.

## User outcome and current evidence

Provide an authenticated responsive XAU/USD candlestick chart with M1/M5/M15/H1
selection, explicit forming/closed state, source/time metadata and truthful
loading/empty/stale/error/reconnect states. Blueprint sections 06 and 18 govern
data/UX; execution gates in 04/05/13/14/22 remain required. Current revision
`71ac86a` has latest sampled Bid/Ask but no bars, chart or raw-tick history.

## Acceptance before implementation

- AC-01: A separate chart channel receives MT5 `CopyRates` windows, not OHLC
  fabricated from one-second sampled telemetry. Versioned bounded snapshots contain
  one of M1/M5/M15/H1, 2–240 increasing broker-time bars, exact decimal OHLC,
  tick-volume/spread units, chart price basis (Bid or Last), pinned identity,
  terminal build, observation time, boot challenge and a chart-only sequence.
  The final row is explicitly unconfirmed/forming; earlier rows are closed because
  a later bar exists. Never infer final-bar closure from elapsed wall time alone.
- AC-02: Validate Demo identity against private bridge settings and contract/build
  against the latest valid telemetry observation. Reject future/misaligned bar
  starts, invalid OHLC/volume, tick-grid violations, time reversals, changed closed
  bars, rollback of a forming bar's high/low/volume, and unknown timeframes. Gaps
  are retained and labelled unclassified; do not invent candles or infer a market
  closure. Snapshot replacement is atomic and bounded per timeframe.
- AC-03: Normalize raw broker time only within an explicitly configured fixed-offset
  validity interval. The interval comes from a separate private chart config,
  not the payload; use the bridge's pinned offset. No chart config means disabled.
  Reject windows crossing its bounds. UTC bar-open and API received times are
  separate; historical bar times do not imply point-in-time research availability.
- AC-04: Authenticate executor before body reads; max 128 KiB JSON, no compression,
  duplicate JSON keys/nonfinite values, two-second body deadline and redacted
  errors. Existing telemetry remains at 16 KiB. Owner reads use the existing live
  identity/session checks; executor/browser tokens cannot substitute for each other.
  No cache, public OHLC, trading endpoint or execution-ready transition is added.
- AC-05: API boot fences earlier lifetimes. An exact duplicate chart sequence is
  acknowledged without refreshing timestamps or clearing rejection; changed and
  older sequences fail. Sequence reservation/window replacement are locked together.
  Invalid authenticated input marks all timeframe views rejected until each receives
  a new valid snapshot. Snapshot age uses wall and monotonic time; wall rollback
  cannot make data fresh. Restart discards all chart windows and changes the boot.
  Chart snapshot freshness (15s) is separate from live quote freshness (5s).
- AC-06: The opt-in read-only EA obtains a separate chart challenge and exports
  synchronized CopyRates windows oldest-first with explicit price basis. Recheck
  Demo identity before/after reads and before send. Keep one bounded network request
  per timer; no trade functions. Compiler/build, fixture protocol parity and actual
  terminal tests are required; source review is not compilation evidence.
- AC-07: The React/Vite chart uses the blueprint's Lightweight Charts with license
  attribution, Charcoal Gold/Sarabun/Inter, labeled timeframe controls and data
  age. Owner login/logout/token changes cancel and clear chart reads. Mark forming
  bars and gaps, retain exact values for inspection, display Bangkok separately
  from UTC, and never portray rejected/stale bars as a live feed. Keyboard/mobile,
  error/reconnect and real-browser integration tests cover the production build.
- AC-08: Retain exact-revision local evidence and a separately authorized MT5
  comparison of chart OHLC/timeframes/time mapping. Synthetic API/EA/browser fixtures
  cannot establish actual broker agreement, history completeness, strategy safety
  or Demo release readiness.

## Implementation boundaries and recovery

Single API process and one Demo identity as SCN-004. A bounded in-memory chart cache
is disposable monitoring state, not raw-tick storage, durable research history or
execution recovery. Raw ticks, Supabase M1 history, indicators, signals and strategy
parity remain separate required product work; this increment does not replace them.
Never silently accept a broker correction to an already closed bar in this cache:
reject, retain prior observation as rejected, and require reviewed resynchronization.

Private chart settings: `offset_valid_from_server_s`, `offset_valid_until_server_s`
(exclusive). They define where the bridge's fixed broker offset has been verified.
Actual values require broker evidence; no default timezone/DST rule is invented.
Configuration restart clears the cache. Outside that interval fail closed for
chart data while preserving the independent telemetry and execution safety gates.

## Verification plan / current status

### Browser increment acceptance details (before implementation)

Keep the existing Charcoal Gold tokens (#0d1117 canvas, #171d25 surface,
#303946 boundaries, #d6b46a forming/selection, #39c98a up, #f0646b down) and
Sarabun labels/Inter numbers. A full-width chart below account telemetry is the
primary market workspace: header/timeframes, freshness warning, candles, exact
OHLC inspection and source/time details. Mobile stacks controls without truncating
numbers. This follows the pinned blueprint, not a new visual system.

Reject a response with mismatched requested timeframe/account, malformed decimals,
incorrect UTC mapping/closure/gap metadata or unsafe execution flags. Preserve
decimal strings for the accessible bar selector/table; canvas numbers are display
only. If numeric conversion cannot preserve the symbol precision, show the exact
table and an explicit chart precision warning instead of misleading candles.
Represent a gap with a bounded whitespace marker and exact missing-interval label,
not generated bars or an unbounded loop over history. Poll one selected timeframe
serially, clear on authorization/network/shape error, and retry transient failures.
Do not retain private charts across logout, token or timeframe changes. Local
monotonic age must expire chart AND quote freshness while a request is pending.
Load the chart library only when validated bars are available. Unit tests cover
these failure paths; production browser rendering remains a separate gate.

API schema, duplicate/concurrency/clock/gap/correction fixtures; ASGI denial and
bounded-body tests; existing SCN-004/005 regression suites; live HTTP/browser chart
integration; MQL compiler/self-test and actual Demo comparison separately.
AC-01 through AC-05 now have local API/schema/concurrency/HTTP fixture evidence;
actual CopyRates/terminal agreement remains unverified. AC-06 is NOT IMPLEMENTED
for the EA chart producer and NOT RUN for compilation/terminal checks. AC-07 has
React component and real production-build browser/Auth/API evidence using synthetic
bars on desktop/mobile, including timeframe selection, exact OHLC agreement,
staleness, reconnect and logout/revocation. AC-08 is PARTIAL: source/artifact hashes
are retained locally, but actual broker comparison is NOT RUN. See
[verification evidence](../verification/SCN-006-market-chart.md).
Missing owner target, broker timezone evidence and MT5 compiler do not block local
contracts/tests; they do block actual terminal acceptance. This contract is not
fully accepted and the full Demo goal remains incomplete.
