# SCN-026 broker-bound risk authorization envelope

## Task contract

Extend the durable entry dispatch and MQL execution command with the exact
account-currency risk authorization required for the future MT5 mutation EA to run
`OrderCalcProfit` immediately before `OrderCheck`/`OrderSend`.

An open command carries the remaining `risk_limit` admitted by the deterministic
Python risk engine and the included `cost_budget` for its selected volume. The EA
must later reject when the absolute broker-calculated entry-to-SL loss plus this
cost budget exceeds the limit. Cancel/close commands carry null risk fields because
management must remain possible while entry risk is exhausted.

This increment changes and verifies the durable/wire contract. It does not call
`OrderCalcProfit`, `OrderCheck`, `OrderSend`, enable Auto Trading or claim MQL
compilation/broker evidence.

## Acceptance criteria

- **AC-01 exact risk derivation:** after sizing, `risk_limit` equals the already
  admitted remaining account-currency risk and `cost_budget` equals selected volume
  times the configured per-lot cost. Both are finite bounded Decimals; limit is
  positive and cost is nonnegative and strictly below the limit.
- **AC-02 durable before dispatch:** one entry dispatch authorization is inserted in
  the same SQLite transaction as its attempt and SENT transition, before adapter
  invocation. It is immutable, bound one-to-one to attempt/command and included in
  recovery/schema evidence.
- **AC-03 strict adapter contract:** every entry adapter invocation requires both
  values. The simulator records and validates them; missing, negative, nonfinite or
  inconsistent values cannot reach a broker adapter.
- **AC-04 strict API wire:** `sochron.execution.command.v1` adds exact decimal-string
  `risk_limit` and `cost_budget` fields. Open requires both; cancel/close require
  both null. Duplicate/extra/missing/over-precision values fail validation.
- **AC-05 MQL codec parity:** the pure MQL parser reads all 24 exact fields, preserves
  decimal text/value, enforces operation nullability and verifies risk relation.
  Pure self-test/source guards remain free of account/network/file/trade authority.
- **AC-06 polling/replay:** claimed and replayed dispatches preserve byte-equivalent
  authorization; changed authorization conflicts under the existing outcome/command
  binding and no replacement is generated.
- **AC-07 recovery and negative paths:** tests cover journal rollback, raw orphan or
  malformed authorization, installed recovery audit and startup behavior without
  weakening UNKNOWN, halt or management semantics.
- **AC-08 evidence limits:** targeted/full Python, MQL source/fixture, installed
  package, web/static and secret checks pass. MetaEditor compile, EA risk calculation,
  mutation and actual Demo parity remain `NOT RUN`.

## Next boundary

The mutation EA must consume these values with current broker symbol/account data,
tick/volume alignment and `OrderCalcProfit`; journal its local attempt before send;
then call `OrderCheck` and at most one `OrderSend`. This contract is necessary but
does not itself make execution ready.
