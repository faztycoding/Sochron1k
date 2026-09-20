# SCN-028 default-off MT5 Demo mutation EA

## Task contract

Implement the first complete MQL5 mutation boundary for the existing authenticated
execution polling bridge. The EA must remain inert by default, admit only one exact
Demo account/symbol/magic identity, reconcile durable local evidence before polling
commands, journal every attempt before a broker write, and report only cumulative
MT5-confirmed outcomes.

This unit implements source and local static/contract verification. It does not
authorize an account operation. MetaEditor compilation, terminal execution,
selected-broker parity and the SCN-001 Demo round trip remain separate target gates.

## Authority and safety boundary

- `EnableDemoExecution=false` is the committed default. No file, timer, account,
  network or broker access occurs while disabled.
- The source has no live-account branch. Every startup, poll, preflight and mutation
  rechecks `ACCOUNT_TRADE_MODE_DEMO` plus the exact login, server, currency, margin
  mode, chart symbol and magic number.
- Browser and owner routes remain read-only. The EA consumes only commands already
  journaled and admitted by `ExecutionService` through `/executor/v1`.
- A terminal-local token, lock and append-only ledger use fixed private filenames.
  They are not EA inputs, `FILE_COMMON` files, logs, fixtures or repository data.
- An ambiguous mutation remains `UNKNOWN`. It is reconciled from current orders,
  positions and history before any further command can be polled or sent.

## Acceptance criteria

- **AC-01 inert exact-Demo fence:** source defaults off and rejects missing, live,
  contest, changed or mismatched account/server/currency/margin/symbol identity.
  Terminal, account and MQL trade permission are required immediately before each
  mutation; no setting enables or bypasses terminal Algo Trading.
- **AC-02 exclusive durable executor:** one terminal-local non-shared lock handle
  owns execution. A bounded append-only ledger validates every record and restores
  the unresolved command/generation after restart. `PREPARED` and `SEND_STARTED`
  records are flushed successfully before the sole `OrderSend` call.
- **AC-03 startup reconciliation:** before command polling, the EA scans bounded
  current orders, positions and selected history twice, rejects foreign/ambiguous
  effects, reconstructs the unresolved command from MT5 identifiers and posts a
  complete cumulative inventory. Missing or conflicting evidence keeps command
  polling quarantined; corrupt durable state fails initialization. New entries
  remain closed.
- **AC-04 bound authenticated polling:** challenge, inventory, command and outcome
  routes use one fixed loopback origin, a dedicated private token, strict body and
  response limits, one synchronous request per timer turn and boot/sequence/
  generation fences. Claimed duplicate payloads never create another send.
- **AC-05 immediate broker preflight:** an open command rechecks a fresh native
  tick, market session, order/SL capabilities, tick size, digits, volume min/max/
  step, stops/freeze levels, filling mode, spread, margin, expiry and side-correct
  SL/TP. Inputs must already lie on broker grids; the EA never moves a stop or
  rounds volume upward to force admission.
- **AC-06 broker risk authorization:** immediately before an entry write,
  `OrderCalcProfit` measures entry-to-SL loss in account currency. Conservatively
  rounded loss from the adverse configured deviation plus the command cost budget
  must not exceed its durable risk limit.
  It also must not exceed 0.25% of current MT5 Equity rounded down in account
  currency. Failed/nonfinite calculation, conversion, margin or minimum-volume
  evidence denies the send.
- **AC-07 checked single write:** each operation builds one explicit
  `MqlTradeRequest`, requires successful `OrderCheck`, appends/flushed
  `SEND_STARTED`, then invokes `OrderSend` at most once. A successful function
  return is never treated as a fill. Cancel and close are bound to the target order
  or position and cannot widen SL, average down or open another exposure.
- **AC-08 cumulative reconciliation:** `OnTradeTransaction` performs no file or
  network I/O and only schedules reconciliation. Timer work deduplicates bounded
  order/deal/position history, preserves partial fills and costs, and separately
  records order ticket, deal ticket and position identifier. Reordered or duplicate
  events cannot regress terminal evidence.
- **AC-09 SL and no-effect truth:** protection is true only when the current MT5
  position carries the intended broker-side SL. Missing/rejected SL is reported
  unprotected and blocks new entries pending the existing emergency-close workflow.
  A rejection is emitted only for an allowlisted no-effect return code after a
  fresh scan confirms no order, deal or position effect; otherwise the result is
  uncertain.
- **AC-10 exact replay and evidence limits:** an outcome is journaled before its
  first upload and replayed byte-for-byte after a lost response. Source guards,
  mutation tests, Python/API regressions, installed/container checks, secret scans
  and whitespace checks pass. MetaEditor, MQL runtime, target network, broker and
  Demo order evidence remain `NOT RUN` until performed on the selected host.

## Required target verification

Before any Demo send, retain a fresh compiler log with zero errors/warnings and the
source/EX5 hashes, run the non-mutating self-tests, confirm exact broker contract
metadata, and exercise disabled startup, duplicate command, expired command,
accepted-send/lost-response, partial fill, duplicate/reordered trade events,
rejected SL, rejected cancel/close, terminal restart, network loss and foreign
effect quarantine. Measure timer/network blocking on the selected topology.

Only after those checks may the owner review a dry-run preview identifying the
exact Demo target, volume, entry/SL/TP, risk/cost limits, abort conditions and
recovery procedure and separately authorize one bounded open-to-close action.

## Evidence boundary

A passing local SCN-028 proves the candidate contains a guarded mutation EA design
and that its wire/API contracts remain compatible. It cannot prove MQL syntax,
filesystem durability, exclusive locking, terminal callbacks, broker calculations,
fills, SL protection or recovery behavior on the selected MT5 build.
