# Sochron MQL5 Demo adapters

**Source checkpoint, not a compiled release.** No MetaEditor executable/terminal
was found in the checked application directories or the workstation's Spotlight
filename index on 2026-09-17. Unindexed/custom Wine prefixes were not exhausted;
the owner still needs to select the MT5 host. No `.ex5`, compiler-success log,
terminal self-test result or actual Demo observation is claimed.

## Files and authority

- `SochronTelemetry.mq5`: opt-in, sampled account/contract/quote observer, with a
  separately default-off native candlestick producer and symbol-session evidence
  (source version 0.12).
- `TelemetryProtocol.mqh`: pure JSON encoder and bounded flat-response parser.
- `SochronTelemetrySelfTest.mq5`: pure protocol tests and synthetic fixture output;
  it never reads an account or uses the network.
- `ExecutionProtocol.mqh`: pure SCN-013 parser/encoder for the authenticated
  SCN-012 execution wire contract. It has no network, account, file or trade access.
- `SochronExecutionInventory.mq5`: separately default-off, read-only Demo account
  inventory uploader for policy evidence (source version 0.10). It hard-codes
  algorithmic trading false and never polls a command.
- `SochronExecutionProtocolSelfTest.mq5`: pure execution-protocol cases that may
  write only two named synthetic JSON fixtures.

Neither observer can send, modify, close or cancel an order or manage positions.
They do not replace the future execution/risk EA. Do not attach either as the only
safety component to a running experiment or imply it protects positions. Keep
application Auto Trading off. Compile checks do not authorize broker use.

## Read-only execution inventory source (SCN-024)

The inventory observer uses only `GET /executor/v1/challenge` and
`POST /executor/v1/inventory`. It scans current orders and positions twice and can
publish a complete empty inventory only when no item matches the configured
symbol/magic. Foreign items remain counted and rejected by policy admission; an
owned item forces incomplete evidence. This does not reconstruct command, deal or
SL history.

Run the source-only guard and local API compatibility tests with:

```bash
.venv/bin/python scripts/check-execution-inventory-source.py
.venv/bin/pytest -q tests/test_execution_inventory_source.py tests/test_execution_bridge.py tests/test_policy_evidence.py
```

These checks are not a compiler or actual account evidence. The selected-host
procedure, API/UI route map and private provisioning boundary are documented in
[`docs/operations/read-only-execution-inventory.md`](../../docs/operations/read-only-execution-inventory.md).

## Execution protocol checkpoint (SCN-013)

The execution protocol sources are an **uncompiled enabling component**, not an EA
that can place, cancel or close an order. They parse the exact bounded command
envelope, encode an empty Demo inventory bootstrap and encode confirmed-rejection
or uncertain outcomes. No `WebRequest`, account query, `OrderCheck`, `OrderSend`,
broker inventory scan or transaction callback exists in this checkpoint.

SCN-026 evolves the command envelope to exactly 24 fields. Open commands require
account-currency decimal strings `risk_limit` and `cost_budget`; cancel/close
commands require both fields as `null`. The pure codec checks their shape and
relation only. A future mutation EA must still calculate current broker loss with
`OrderCalcProfit` before `OrderCheck`/`OrderSend`.

SCN-027 adds typed cumulative deal, entry, management, rejection, inventory and
snapshot-outcome encoders. The synthetic inventory now covers a closed parent and
its close result; the synthetic outcome covers a protected filled entry. These are
hand-authored/MQL-source compatibility checkpoints. The codec still has no account,
history, network, file or trade access and therefore does not observe these states.

Local source and hand-authored golden-fixture checks:

```bash
.venv/bin/python scripts/check-execution-protocol-source.py
.venv/bin/python scripts/check-execution-protocol-fixture.py --kind inventory
.venv/bin/python scripts/check-execution-protocol-fixture.py --kind outcome
.venv/bin/python -m pytest -q tests/test_mt5_source.py
```

On the selected MT5 host, copy `TelemetryProtocol.mqh` and
`ExecutionProtocol.mqh` beside `SochronExecutionProtocolSelfTest.mq5` in an
isolated `MQL5/Scripts` folder. Compile with a recorded MetaEditor build and retain
fresh zero-error/zero-warning output. Run the script with Auto Trading off; a pass
writes `MQL5/Files/SochronExecutionInventorySelfTest.json` and
`MQL5/Files/SochronExecutionOutcomeSelfTest.json`. Verify each actual generated
path using the matching command above plus `--fixture PATH`. Require a fresh script
PASS log and `input_is_committed_golden=false`; copied golden files alone are not
MQL evidence. This host procedure is `NOT RUN` in the repository evidence.

## Read-only observer source and wire checks

Verified with the pinned project Python environment:

```bash
.venv/bin/python scripts/check-mt5-source.py
.venv/bin/python scripts/check-mt5-fixture.py
.venv/bin/python scripts/check-mt5-fixture.py --chart
.venv/bin/pytest -q tests/test_mt5_source.py
```

The source guard checks the reviewed include graph, default-off input and absence
of named forbidden APIs/imports/writes. Its mutation tests demonstrate detection
of those patterns only. It is not a MQL compiler, control-flow proof or execution
sandbox. The fixture check without arguments validates the committed synthetic
golden file; it is explicitly **not** evidence that MQL generated that file.

## Required compilation and protocol test on the selected host

This procedure has **NOT RUN** here. Do not relabel it passed from source checks.

1. Record terminal and MetaEditor build numbers and the selected platform/Wine
   version without capturing account credentials. Use the terminal's data-folder
   command to locate its actual `MQL5` tree; do not guess a Wine prefix.
2. Copy `SochronTelemetry.mq5` with `TelemetryProtocol.mqh` into an isolated
   subfolder of `MQL5/Experts`. Copy `SochronTelemetrySelfTest.mq5` with the same
   header into a subfolder of `MQL5/Scripts`. Confirm source hashes match the
   committed candidate. Do not copy token files into the repository.
3. Open each `.mq5` in that MetaEditor and compile. Retain fresh compiler output
   showing zero errors and zero warnings, compiler build, source hashes and
   resulting `.ex5` hashes/timestamps. A process exit code or an old `.ex5` alone
   is insufficient. Keep generated binaries untracked.
4. Run only the pure `SochronTelemetrySelfTest` script first. It requires no token,
   account access, WebRequest permission or trading operation. Retain its complete
   PASS result and case count. On success it overwrites only its generated
   `MQL5/Files/SochronTelemetrySelfTest.json` and
   `MQL5/Files/SochronChartSelfTest.json` with synthetic data.
5. Compare that generated file to the API golden fixture, using the verifier's
   `--fixture` argument with its actual local path. This invocation is pending,
   not a verified command for this workstation. Require exact golden values,
   `input_is_committed_golden=false`, source/artifact identity and a fresh terminal
   self-test log together; file equality alone cannot attest provenance.
   For the chart output add `--chart` as well as `--fixture` and its actual path.
   Require both outputs from the same fresh successful script run; a partial output
   or leftover file from an earlier run is not a passing self-test.

## Before actual read-only Demo operation

Obtain authorization for the selected Demo account/terminal and read-only upload
to its local API. The general software build request does not grant authority to
operate an unspecified account. Verify the API and MT5 actually share the expected
loopback endpoint; Wine/remote-host localhost behavior must be tested, not assumed.

Private provisioning requirements:

- Set `EnableReadOnlyTelemetry=true` only after identity and compilation checks.
- Set `ExpectedLogin` to the actual Demo login and the API's `account_ref` to its
  exact base-10 string (no alias or leading-zero padding).
- Supply the exact server, currency, symbol and margin-mode enum value. Attach to
  that symbol's chart. Supply a chosen `ExecutorId` matching the API identity.
- Verify the broker tick timestamp's UTC offset and configure it on both sides.
  The default offset is deliberately invalid. Recheck on DST/server changes.
- Privately provision the same API-scoped token as raw ASCII, 43–128 URL-safe
  characters, **without BOM, spaces or newline**, in the fixed terminal-local
  `MQL5/Files/sochron-telemetry.token`. Restrict it using the host's owner ACL.
  No `FILE_COMMON` access is used; MQL file APIs do not prove the host ACL is correct.
- Allow only the required local WebRequest origin in terminal options. The source
  destination is fixed to `http://127.0.0.1:8000/bridge/v1`; custom-port behavior
  must be proven on the actual terminal build. Do not broaden the URL allowlist
  or expose the API publicly to work around a failed connection.

No account password is requested by this EA. Do not put a token in EA inputs,
`.set` files, command arguments, code, logs, screenshots or chat. Ignore rules and
secret scans reduce accidental commits; they are not secret-storage boundaries.

## Behavior and failure expectations to verify

One timer per second performs at most one request, with a requested 500 ms timeout.
Challenge and snapshot occur on separate timer events. On a missing/unconfirmed
response, discard that monitoring sample, wait ten seconds and reacquire the
challenge before collecting another sample. No external trade is involved, and
this must not be reused as the retry policy for order sends.

The API uses the next sequence already accepted, so an accepted snapshot whose
response was lost does not cause a changed-payload duplicate after reconnect.
Boot changes invalidate previous observations. A reply must contain the expected
positive sequence and accepted flag, not merely HTTP 200. Response parsing is
bounded to 2 KiB after WebRequest returns; the library itself owns allocation
while receiving. Only the reviewed local API is an allowed destination.

Disconnection sends nothing and lets API data become stale. Identity mismatch
latches the observer until explicit reinitialization. A call observed taking over
one second also latches it; actual maximum blocking time cannot be proven by that
after-the-fact check and must be measured at AC-07. WebRequest is synchronous, so
this observer must not be merged into the future position-risk loop without a
reviewed transport design.

The quote output is sampled, not every tick. Telemetry v2 also records whether the
sampled broker tick falls inside the symbol's `SymbolInfoSessionTrade` table and
whether the symbol mode permits new entries; ambiguous session rows suppress the
sample instead of guessing. The API retains telemetry v1 for monitoring
compatibility, but the PA01 policy writer accepts only v2 market evidence. This
source behavior still requires selected-host compilation and actual broker parity.
It preserves the tick's original timestamp even if unchanged for many timers;
account values are finite observations, not
risk approvals. No positions, orders, deals or SL confirmation are invented or
claimed by this version. Optional chart snapshots are native monitoring windows,
not complete tick capture or durable research history.

## Optional native charts (SCN-006; source-only checkpoint)

`EnableReadOnlyCharts=false` by default. It requires `EnableReadOnlyTelemetry=true`,
the same private token/identity, and the API's independently verified chart offset
interval. `ChartBars` defaults to 120 and accepts 2–240; it is a monitoring window,
not permission to truncate required strategy history. Before enabling on an
authorized Demo target, warm the selected symbol's M1/M5/M15/H1 history in MT5 and
verify synchronization with at least the configured count. Unsynchronized or short
history is skipped, not downloaded in a blocking retry loop or filled with invented
bars. The owner API displays unavailable/stale timeframes explicitly.

Each chart attempt checks Demo identity, symbol contract and native Bid/Last basis,
rejects custom symbols, calls CopyRates once into a fixed array, and checks series
synchronization/last-bar identity again. A rollover during collection is discarded.
Prices must round-trip at the symbol digits and lie on an integer tick grid without
exceeding the safe scaled-integer bound. Unsupported numeric precision is refused;
native prices are not rounded to manufacture valid OHLC. API validation is independent.

After a successful quote, the next timer can perform one chart challenge or one
chart upload. The timeframe rotates M1/M5/M15/H1 even when one history is unavailable.
In successful steady state the design is one quote every two timer periods and one
window per timeframe every eight periods. This is **not measured latency evidence**.
A per-timer request counter also rejects a second WebRequest. Quote bodies remain
16 KiB; only `POST /chart/snapshot` gets the 128 KiB limit. Chart and quote challenge
sequences are separate but must agree on API boot identity.

Transport/unconfirmed chart responses back off ten seconds and reacquire the chart
challenge, without replaying an old sample. Telemetry continues independently.
Other chart 4xx responses (except transient 408/429 or recognized BOOT_MISMATCH)
latch the chart channel for review. This includes corrections, changed basis,
offset expiration and wrong identity/sequence. Reconnect does not release that
latch. A boot mismatch discards both connections and reacquires the new API boot.
Reinitializing the EA alone does not clear the API's immutable closed-bar cache;
never restart/reseed the API automatically to hide a rejected correction.

A history collection observed over 250ms halts the chart channel before uploading.
CopyRates can still block inside MT5; the measured-duration check cannot interrupt
that call. A WebRequest observed over one second still halts the whole observer.
Cold-history, clock/DST, timer jitter, disconnection, account switching, lost replies
and all timing limits require actual terminal testing. Keep this synchronous
read-only observer separate from future position protection/execution handlers.

Pending target tests: compile both sources with zero warnings; run all 50 pure
cases; compare generated telemetry/chart fixtures; check live Demo OHLC against
each of the four MT5 charts, Bid/Last, UTC mapping and forming-bar rollover; verify
gap/correction rejection, independent backoff, rejected-channel latch persistence,
one-request timer budget and worst-case timing. None has run on MT5 here.

## Evidence to retain for SCN-004 AC-07

Compile/self-test identities; configured non-secret identity reference; confirmed
Demo mode; redacted receipt sequence/time evidence; actual quote comparison in a
private review; stale tick and disconnect behavior; changed-account denial;
API/EA restarts and lost-response behavior; request-duration measurements.
Keep account values and secrets out of public Git evidence. SCN-001 order/SL/
recovery acceptance remains separate and unpassed.

Official reference semantics checked for this source:
[WebRequest](https://www.mql5.com/en/docs/network/webrequest),
[FileOpen](https://www.mql5.com/en/docs/files/fileopen),
[symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants),
[account properties](https://www.mql5.com/en/docs/constants/environment_state/accountinformation),
[SymbolInfoTick](https://www.mql5.com/en/docs/marketinformation/symbolinfotick),
[TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt),
[StringToCharArray](https://www.mql5.com/en/docs/convert/stringtochararray),
[EventSetTimer](https://www.mql5.com/en/docs/eventfunctions/eventsettimer).
[CopyRates](https://www.mql5.com/en/docs/series/copyrates),
[SeriesInfoInteger](https://www.mql5.com/en/docs/series/seriesinfointeger),
[MqlRates](https://www.mql5.com/en/docs/constants/structures/mqlrates).
Reference documentation does not substitute for build/runtime evidence.
