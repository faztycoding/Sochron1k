# SCN-028 default-off MT5 Demo mutation EA verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`b85ee20aaabd2060174daeb56bd9bd1bcbbd922d`. The delivery report binds the final
commit after these files are committed and pushed.

AC-01 through AC-10 in the
[task contract](../contracts/SCN-028-default-off-demo-mutation-ea.md) pass only for
the reviewed source boundary, source-mutation tests and existing API/Python wire
contracts. MetaEditor compilation, MQL execution, exclusive-lock behavior, flush
durability, account access, broker calculations, fills, callback timing, restart
recovery and the SCN-001 Demo round trip are `NOT RUN`.

## Implemented scope

- Added an EA that returns before files, timer, account, network or broker access
  while `EnableDemoExecution=false`; no live or contest account branch exists.
- Bound startup and every request/send fence to one exact Demo login, server,
  currency, margin mode, chart symbol, executor identity and magic number.
- Added fixed terminal-local token, non-shared lock and bounded append-only ASCII
  ledger. The original UTC and trade-server times, exact command and exact outcome
  survive every allowed state transition.
- Required stable empty current state before replacing an entry, complete startup
  inventory before polling, and incomplete/quarantined inventory for foreign or
  unresolvable state.
- Added fresh tick/session, contract/grid/stops/filling/spread/deviation, margin and
  expiry checks. Broker loss comes from `OrderCalcProfit` and loss plus costs must
  fit both the durable command limit and 0.25% of current Equity.
- Kept one explicit `OrderCheck` and one `OrderSend` call site. `PREPARED` and
  flushed `SEND_STARTED` precede the send; function success never implies fill.
- Kept `OnTradeTransaction` to one dirty flag. Timer reconciliation rereads bounded
  current state and history, preserves partial deals and tickets separately, and
  confirms protection only from current `POSITION_SL`.
- Journaled outcome bytes before upload, replayed them unchanged after response
  loss, and allowed rejection only for a reviewed no-effect return code plus a
  fresh no-effect scan. All other ambiguity is uncertain.

## Acceptance evidence

- **AC-01:** source guard and mutations enforce default-off startup/shutdown, exact
  Demo-only identity, trading-permission checks and absence of live/contest APIs.
- **AC-02:** ledger record shapes, checksum, sequence, transition, exact-byte/time
  continuity, append/flush ordering and fixed non-shared files are source-checked.
- **AC-03:** current state and selected history are fingerprinted twice; foreign,
  changing, missing or ambiguous evidence makes inventory incomplete.
- **AC-04:** only four fixed authenticated executor routes exist, with one
  synchronous 500 ms request per one-second timer turn and bounded responses.
- **AC-05/06:** source requires broker-native grids, sessions, stops, filling,
  `OrderCalcProfit`, Equity, costs, authorized risk and margin before entry.
- **AC-07:** mutation tests fail on an additional/removed send, check, journal stage
  or reordered fence. Cancel/close bind exact current ticket/position and volume.
- **AC-08/09:** callback, repeated-scan, cumulative evidence, broker SL and
  confirmed-no-effect patterns are guarded; actual event order is not claimed.
- **AC-10:** local Python/API/web/static/package/secret/whitespace checks pass.
  MQL and target claims remain explicitly absent.

## Verification run

- Demo-executor source guard: PASS; it reports every target field `NOT RUN` and
  `execution_ready=false`, `auto_trading_enabled=false`.
- Source mutation module: **49 passed**.
- Focused execution/recovery/source regressions: **195 passed**.
- Final local safety core at the time of this record: Ruff PASS, **1,036 tests
  passed** in 42.44s, and secret scan PASS over 3,278 text files.
- Web: TypeScript PASS, **180 tests passed**, production Vite build and client
  bundle secret scan PASS on Node.js 24.21.0.
- Static Supabase/Compose, baseline and installed/repository skill integrity: PASS.
- Installed worker package: PASS using temporary pinned uv 0.12.15. Evidence:
  `output/worker-package/b63cb9e162924d688456c989990f72eb/result.json`.
- Worker-container and Linux candidate suites: `NOT RUN`; Docker is not installed
  or available in this environment. No current-candidate container claim is made.
- MetaEditor/terminal discovery: no executable was found on PATH, in the checked
  application directories or Spotlight results. Compilation and terminal tests
  are `NOT RUN`.

Source hashes at this source checkpoint:

| Source | SHA-256 |
| --- | --- |
| `SochronDemoExecutor.mq5` | `0a16756dace2d7737280910ad383b5e34babe323c996496700bde491b425770a` |
| `ExecutionRuntime.mqh` | `6cd9a0252e57d75cedf1456108129700fa2e03c7693719e55151f3fcb85c5959` |
| `ExecutionLedger.mqh` | `b37257c9551c4e6b339a98d207477d24cd0bb74cc1eba7a9f0fedc457d4d360e` |

## Evidence limits and next boundary

The implementation state is source-complete for this contract, not release-ready.
The selected MT5 host must compile the exact committed sources with zero errors and
warnings, retain EX5/source hashes, prove second-instance lock denial and ledger
crash recovery, and run the negative/fault matrix without a broker mutation first.

Before one bounded Demo open-to-close action, the owner must still supply the exact
Demo server/account/currency/symbol/margin mode, broker contract, terminal build and
host topology, magic number, private token delivery, alert destination and explicit
target authorization. The API/UI continue to report execution not ready and Auto
Trading off until those gates pass.

## Primary design references

- [OrderCalcProfit](https://www.mql5.com/en/docs/trading/ordercalcprofit)
- [OrderCheck](https://www.mql5.com/en/docs/trading/ordercheck)
- [OrderSend](https://www.mql5.com/en/docs/trading/ordersend)
- [OnTradeTransaction](https://www.mql5.com/en/docs/event_handlers/ontradetransaction)
- [FileWriteString](https://www.mql5.com/en/docs/files/filewritestring) and
  [FileFlush](https://www.mql5.com/en/docs/files/fileflush)
