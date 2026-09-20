# SCN-024 read-only MT5 execution inventory observer

## Task contract

Add a separately default-off MQL5 observer that authenticates to the existing
SCN-012 execution bridge, proves the exact Demo identity, scans current MT5 orders
and positions twice for a stable empty-account view, and publishes an execution
inventory frame that the SCN-023 policy writer may use while MT5 Auto Trading
remains disabled.

This increment is intentionally read-only. It does not poll the command route,
parse a dispatch, run `OrderCheck`, send/modify/cancel/close an order, reconstruct
historical command snapshots, enable terminal algorithmic trading or make the
execution adapter ready.

## Inventory semantics

- The observer is bound to one exact Demo login, server, currency, margin mode,
  chart symbol, executor ID and positive magic number. It re-reads terminal truth
  before and after every scan and sends nothing after an identity change.
- Current orders and positions are enumerated through native MT5 read APIs. A
  bounded exact-enumeration fingerprint of ticket, symbol and magic is collected twice;
  any count/property change suppresses the observation.
- Items matching the configured symbol and magic are owned execution effects. This
  observer cannot reconstruct their command/deal/SL history, so `complete=false`
  whenever one exists. Other items are counted as foreign and remain rejected by
  the API's existing single-account invariant.
- Only a stable scan with no owned current item may carry `complete=true` and empty
  entry/management/rejection arrays. It proves current emptiness only, not command
  history or startup reconciliation.
- `algo_trading_allowed` is hard-coded false in this source. The API may use the
  fresh complete empty inventory for policy exposure/pending evidence, but the
  normal executor admission and command adapter remain unavailable.

## Transport and private input

- `EnableReadOnlyExecutionInventory=false` is the source default. Disabled startup
  opens no token file, timer, account scan or network request.
- The dedicated execution-bridge bearer token is read only from the fixed
  terminal-local `MQL5/Files/sochron-execution.token`; it is never an EA input,
  log value, fixture or repository value.
- The destination is fixed to loopback `/executor/v1`. Challenge and inventory
  upload occur on separate timer turns with at most one bounded `WebRequest` per
  turn. The observer never requests `/commands/next` or posts `/outcomes`.
- An API restart discards the boot fence and sequence. A missing or unconfirmed
  response causes a bounded reconnect, not a broker action or optimistic state.

## Acceptance criteria

- **AC-01 inert opt-in:** source and guards prove the feature defaults off, has no
  secret input and performs no account/file/network work until explicitly enabled.
- **AC-02 exact Demo fence:** configuration and repeated terminal reads deny real,
  contest, unknown or changed login/server/currency/margin/symbol identity.
- **AC-03 stable bounded scan:** orders/positions are bounded, selected natively,
  classified by exact symbol+magic and fingerprinted twice. Races or unsupported
  identifiers suppress publication.
- **AC-04 truthful empty evidence:** `complete=true` is possible only for a stable
  scan with no owned effects; owned effects force incomplete and foreign effects
  retain nonzero counts. Empty arrays are never used to claim an existing effect.
- **AC-05 policy-only admission:** API tests prove a fresh complete inventory with
  `algo_trading_allowed=false` can feed SCN-023, while execution status/inventory
  admission remains unavailable and all public execution-ready/Auto flags are false.
- **AC-06 authenticated bounded transport:** exact challenge/receipt parsing,
  boot/sequence handling, request/body/response/time budgets and a separate token
  file are statically guarded; malformed/unconfirmed responses never advance.
- **AC-07 no mutation authority:** source scanning rejects command polling,
  outcomes, trade request/result types, `OrderCheck`, `OrderSend`, trade helpers,
  global-variable writes, sockets and notification/export operations.
- **AC-08 evidence limits:** source guards, mutation tests, fixture/API compatibility,
  full Python/web regressions and secret scans pass. MetaEditor compilation, script
  execution, actual account scan and target networking remain NOT RUN.

## Evidence boundary

A passing SCN-024 proves a source-level read-only empty-inventory adapter and local
policy-only API admission. It does not prove MQL compilation, an actual empty Demo
account, stable broker reads, historical reconciliation or any mutation path. The
next execution unit must add a durable executor-local ledger and full cumulative
inventory before it can consume commands.
