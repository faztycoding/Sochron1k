# Sochron read-only Demo observer

**Source checkpoint, not a compiled release.** No MetaEditor executable/terminal
was found in the checked application directories or the workstation's Spotlight
filename index on 2026-09-17. Unindexed/custom Wine prefixes were not exhausted;
the owner still needs to select the MT5 host. No `.ex5`, compiler-success log,
terminal self-test result or actual Demo observation is claimed.

## Files and authority

- `SochronTelemetry.mq5`: opt-in, sampled account/contract/quote observer.
- `TelemetryProtocol.mqh`: pure JSON encoder and bounded flat-response parser.
- `SochronTelemetrySelfTest.mq5`: pure protocol tests and synthetic fixture output;
  it never reads an account or uses the network.

This observer cannot send, modify, close or cancel an order and does not manage
positions. It does not replace the future execution/risk EA. Do not attach it as
the only safety component to a running experiment or imply it protects positions.
Keep application Auto Trading off. Compile checks do not authorize broker use.

## Local source and wire checks

Verified with the pinned project Python environment:

```bash
.venv/bin/python scripts/check-mt5-source.py
.venv/bin/python scripts/check-mt5-fixture.py
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
   account access, WebRequest permission or trading operation. Retain its 24-case
   result. On success it overwrites only its generated
   `MQL5/Files/SochronTelemetrySelfTest.json` with synthetic data.
5. Compare that generated file to the API golden fixture, using the verifier's
   `--fixture` argument with its actual local path. This invocation is pending,
   not a verified command for this workstation. Require exact golden values,
   `input_is_committed_golden=false`, source/artifact identity and a fresh terminal
   self-test log together; file equality alone cannot attest provenance.

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

The output is sampled, not every tick. It preserves the tick's original timestamp
even if unchanged for many timers; account values are finite observations, not
risk approvals. No positions, orders, deals, SL confirmation, bars or history are
invented or claimed by this version.

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
Reference documentation does not substitute for build/runtime evidence.
