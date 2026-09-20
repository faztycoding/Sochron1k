# SCN-013 MQL5 Demo execution protocol codec

> Current evolution: SCN-026 extends the original 22-field envelope documented
> below with required nullable `risk_limit` and `cost_budget` fields. The current
> parser therefore accepts exactly 24 fields; this file retains the original
> SCN-013 acceptance baseline. SCN-027 further adds typed cumulative entry,
> management, inventory and snapshot-outcome encoders without changing the pure
> no-authority boundary.

2026-09-20, High assurance, base
`1c886e3d9b2c01905206d436a9d501f79557bf2f`. Local source-only work under the
full Demo objective. It does not authorize an MT5 account operation, unlock Auto
Trading, add an owner execution route or claim MetaEditor compilation.

## Required outcome

Implement the pure MQL5 wire boundary needed by the future default-off Demo
execution EA. It must parse the exact SCN-012 command envelope, generate a complete
empty Demo inventory bootstrap frame, and generate bound confirmed-rejection and
uncertain outcome frames. Pure protocol code must have no account, network, file or
trade access. A separate self-test script may write only synthetic fixture files.

This work removes ambiguity from the API/EA JSON contract before any `OrderCheck`
or `OrderSend` path is added. It does not substitute source scanning or synthetic
fixtures for compiler, terminal, broker-event or Demo evidence.

## Local acceptance

- AC-01: Parse the exact 22-field `sochron.execution.command.v1` flat object with a
  16 KiB bound, unique known keys, printable unescaped ASCII strings, strict positive
  integers, UTC expiry, finite positive decimals and operation-specific nullability.
  Reject extra, missing, duplicate, escaped, non-ASCII, non-finite, expired-shape,
  self-targeting and inconsistent entry/management fields.
- AC-02: Validate boot UUID, SHA-256-shaped fingerprint, safe identifier alphabet,
  Demo account/symbol bindings, operation, side, dispatch sequence, positive magic
  number and requested volume without silently rounding a value.
- AC-03: Parse the authenticated challenge only when its keys are exactly `boot_id`
  and `next_inventory_sequence`. Exact receipts reuse the reviewed common parser.
- AC-04: Encode `sochron.execution.inventory.v1` bootstrap evidence with fixed Demo
  identity, generation, magic number, account snapshot, UTC observation and explicit
  empty snapshot/rejection arrays. `complete` and permission flags are explicit and
  cannot be inferred from HTTP success.
- AC-05: Encode a result bound to boot, dispatch sequence, attempt, generation,
  command, target and operation. A confirmed rejection carries only the reviewed
  no-effect retcode, external retcode, request ID and UTC event time. Uncertain
  evidence remains distinct and never invents order, deal or position identifiers.
- AC-06: Keep the codec free of `WebRequest`, account/symbol reads, file access,
  `OrderCheck`, `OrderSend`, asynchronous send, imports and external includes.
  The self-test is likewise free of terminal/account/network/trade access and may
  write only its two named synthetic fixture files.
- AC-07: Add failing-first source guards, mutation tests and API-schema fixture
  verification. The verifier must reject duplicate JSON keys, NUL, oversize and any
  value drift while redacting invalid contents.
- AC-08: Record source hashes, verifier identity and evidence limits. MetaEditor
  compile, MQL self-test execution, account reads, WebRequest, broker mutation,
  OnTradeTransaction and actual Demo reconciliation remain `NOT RUN`.

## Exclusions and next boundary

No executable execution EA, local attempt ledger, exclusive executor lock, broker
inventory scan, contract/margin preflight, mutation request, partial-fill rebuild,
SL confirmation, emergency close or restart reconciliation is included. Those are
the next SCN work unit and must consume this codec without weakening SCN-001/012.

## Required verification

Run the codec source guard, fixture verifier, targeted pytest, the full SCN-001
local gate and repository secret scan. A hand-authored golden fixture proves schema
compatibility only; it does not prove MQL generated the bytes.
