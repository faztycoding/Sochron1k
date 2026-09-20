# SCN-027 MQL5 cumulative execution evidence codec

## Task contract

Complete the pure command/outcome wire layer required before a mutation EA can
truthfully report MT5 orders, deals, positions and management results. Align the
Python dispatch identifier alphabet with the already strict MQL parser, then add
typed MQL encoders for cumulative entry and management snapshots and inventory.

This unit remains pure and uncompiled. It adds no account, network, file, timer or
trade access; does not invoke `OrderCalcProfit`, `OrderCheck` or `OrderSend`; and
does not enable Auto Trading or claim a broker observation.

## Acceptance criteria

- **AC-01 lexical parity:** every Python field consumed by `ScxCommandJson` uses
  the same bounded ASCII identifier/reason/fingerprint alphabet as MQL. Unsafe
  configured identities or dispatch identifiers fail before command exposure.
- **AC-02 typed deal evidence:** MQL represents bounded deal ticket, volume, price,
  signed financials and optional UTC occurrence time without accepting nonfinite,
  duplicate or invalid values.
- **AC-03 cumulative entry evidence:** a typed encoder emits the exact
  `BrokerSnapshot` shape, validates volume conservation, deal totals, ticket/
  position requirements, SL semantics and terminal-state relations.
- **AC-04 cumulative management evidence:** a typed encoder emits the exact
  `ManagementSnapshot` shape with its updated target snapshot, bounded deals,
  observed UTC time, operation binding and volume conservation.
- **AC-05 bound outcome:** snapshot outcomes are bound to the parsed command's
  boot, sequence, attempt, generation, command, target and operation. Open cannot
  carry management evidence and management cannot carry entry-only evidence.
- **AC-06 restart inventory:** the inventory encoder can carry at most one entry,
  one management and one rejection evidence object under the existing single-
  exposure invariant; IDs/namespaces and operation bindings cannot conflict.
- **AC-07 exact synthetic fixtures:** pure self-tests cover entry and management
  encoders, invalid volume/deal/SL/time/binding paths and retain the reviewed two
  output files. Python validates exact generated-shape goldens without treating
  hand-authored bytes as MQL runtime evidence.
- **AC-08 evidence limits:** focused/full Python, web/static, installed package,
  Linux container, source-purity, secret and whitespace checks pass. MetaEditor
  compile/self-test, terminal state and broker operation remain `NOT RUN`.

## Next boundary

The default-off mutation EA must populate these typed structures only from a
durable local attempt ledger and reconciled MT5 state. An `OrderSend` return value
or one callback is never sufficient evidence for a snapshot.
