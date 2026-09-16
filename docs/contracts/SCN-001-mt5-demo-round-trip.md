# SCN-001 MT5 Demo Round Trip

## Contract

| Field | Value |
| --- | --- |
| ID | SCN-001 |
| Version | 1.1 |
| Owner | Project owner; technical implementer not yet named |
| Parent project | Sochron1k |
| Current state | Local safety core implemented and under verification; BLOCKED for a real Demo send pending the MT5 adapter, owner inputs, credentials, and explicit target authorization |
| Done scope | Implementation verified first, then Demo operation verified as a separate gate |
| Risk tier | High assurance |
| Evidence base | Blueprint v1.1 and repository base revisions `776859c`, `e9a1972` |

## Goal and user outcome

Prove the first end-to-end execution slice: read XAU/USD Demo market and contract data, create one bounded command, persist it before send, open the smallest risk-compliant Demo position with a broker-side SL, reconcile the resulting identifiers, close the position, and present an audit trail that matches MT5.

## Current behavior

The repository contains a pinned Python runtime contract, FastAPI health boundary, Pydantic execution schemas, deterministic risk sizing, SQLite WAL command journal, isolated executor simulator, targeted pytest/Hypothesis checks, and a responsive local monitoring console. The worker, Supabase schema, MQL5 EA, real MT5 adapter, deployment manifests, and target-host evidence are not implemented. No Demo operation has been attempted or authorized by this contract alone.

## Scope

- Establish the repository modules needed by this slice: API, executor adapter, durable journal, simulator, and targeted tests.
- Define versioned schemas for market events, command intent, execution responses, and reconciliation results.
- Implement a simulator first, including timeout-after-acceptance and restart fixtures.
- Implement Demo-account preflight for account mode, server, symbol, currency, contract metadata, trading permission, time, and feed freshness.
- Calculate a volume that does not exceed the 0.25% risk limit and rounds down to the broker step.
- Persist the command before send and maintain the defined execution state machine.
- Reconcile order, deal, and position identifiers from MT5.
- Complete one owner-authorized Demo open and close only after local acceptance evidence passes.
- Produce an audit view or machine-readable report for the complete round trip.
- Keep the local web console visibly Demo-only, non-operational, and truthful about unavailable MT5 and market data until the applicable gates pass.

## Exclusions

- Live accounts or any configuration that can select them.
- PA01, SMC01, ICT01, news AI, Supabase, and production web UI beyond interfaces required by the slice.
- VPS deployment and unattended operation.
- Multiple accounts, symbols, concurrent positions, or manual trades in the Demo account.
- Strategy performance or profitability claims.

## Inputs and outputs

### Inputs

- Verified Demo account identity and mode.
- Broker server, exact XAU/USD symbol, account currency, and contract specification.
- Fresh Bid/Ask with event and received timestamps.
- Current Equity and risk baselines.
- Test command with entry, SL, TP, expiry, strategy version, and experiment ID.

### Outputs

- Durable command and state-transition record.
- MT5 order, deal, and position identifiers where applicable.
- Confirmed broker-side SL evidence.
- Reconciliation result showing local and MT5 state.
- Close reason, realized costs, and final Demo account values.
- Evidence record tied to the source revision, configuration fingerprint, simulator fixture, and MT5 environment identity.

### Errors

Invalid account, live-account detection, stale price, invalid Bid/Ask, closed market, missing contract data, volume below minimum, insufficient margin, duplicate request, mismatched idempotency fingerprint, send timeout, unknown execution, rejected SL, reconciliation mismatch, and journal failure must be explicit states. They must not be converted to success or silently retried.

## Invariants

- Demo account verification occurs immediately before any external send.
- The command is durable before send.
- One idempotency key plus the same fingerprint maps to one logical command.
- A changed fingerprint under the same key is rejected.
- `UNKNOWN` is reconciled before retry.
- The position is not reported protected until MT5 confirms the SL.
- The minimum lot is rejected when it exceeds the remaining risk budget.
- Opening is locked during stale price, journal failure, unresolved restart, risk halt, or reconciliation mismatch.
- No credential appears in source, test fixtures, logs, evidence, or browser-delivered configuration.

## Acceptance criteria

### AC-01 Demo preflight

Given an adapter response for the configured account, when preflight runs, then it accepts only a Demo account whose server, symbol, currency, account mode, trading permission, clock, and contract metadata match the configured expectation. A live or mismatched identity is denied before a command is journaled or sent.

### AC-02 Risk-compliant volume

Given current Equity, remaining daily and experiment budgets, entry, SL, contract data, and broker volume limits, when volume is calculated, then the rounded-down worst-case loss does not exceed every applicable budget. If the minimum volume exceeds the budget, the result is a blocked command with no external send.

### AC-03 Durable send and idempotency

Given a validated command, when it is submitted repeatedly with the same idempotency key and fingerprint, then exactly one logical command can reach the adapter, and its journal record predates the first send attempt. Reusing the key with another fingerprint is rejected.

### AC-04 Unknown-effect reconciliation

Given the adapter accepted a command but the response was lost, when the client observes a timeout, then the command becomes `UNKNOWN`, no replacement is sent, and the system queries MT5 orders, positions, and history until it resolves the original outcome or quarantines the command.

### AC-05 Fill and protection evidence

Given a Demo fill, when execution events are processed, then order ticket, deal ticket, and position identifier are stored separately, partial fills are represented correctly, and the UI or report states `protected` only after MT5 confirms the broker-side SL.

### AC-06 Restart recovery

Given pending, unknown, filled, or halted state, when the service or executor restarts, then it restores journal and risk state, reconciles MT5 before accepting new work, and preserves the single-position invariant.

### AC-07 Close and final reconciliation

Given the owner-authorized Demo position, when it is closed, then MT5 confirms the resulting deals and position state, local history reconciles identifiers and costs, and the final audit report contains no unresolved command or position mismatch.

### AC-08 Secret and live-path denial

Given repository, log, evidence, and client-bundle scans, then no credential is exposed and no first-release code path can select or send to a live account.

### AC-09 Safe local console

Given the local API is online, offline, or still loading, when the monitoring console is rendered at desktop or mobile width, then Demo-only and Auto Trading off remain visible, unconfirmed MT5 and market values are not invented, unavailable sections are not interactive, and health retry cannot submit an execution command.

## Required verification

| Acceptance | Verifier required before implementation is complete | Current result |
| --- | --- | --- |
| AC-01 | Adapter contract tests for accepted Demo and denied live/mismatch fixtures | PARTIAL, not PASS - local simulator fixtures cover Demo/live/mismatch/stale/expiry; actual MT5 preflight remains unverified |
| AC-02 | Unit and property tests for currency, tick size, step rounding, caps, and minimum-volume rejection | PARTIAL, not PASS - Decimal budget and volume-grid tests pass; broker OrderCalcProfit, conversion, tick alignment, and actual margin remain unverified |
| AC-03 | Integration test with concurrent duplicate submissions and journal ordering | PARTIAL, not PASS - SQLite concurrent duplicate, changed-payload, and journal-failure fixtures pass; process-level and MT5 boundary evidence remains |
| AC-04 | Fault test that accepts then drops the response, followed by reconciliation | PARTIAL, not PASS - isolated accept-then-timeout reconciliation passes without resend; actual bridge interruption remains unverified |
| AC-05 | Adapter integration test for fill, partial fill, and rejected-SL events | PARTIAL, not PASS - simulator identifier, duplicate-deal, partial-fill, and rejected-SL fixtures pass; MT5 event ordering remains unverified |
| AC-06 | Process restart test with persisted pending, unknown, position, and halt fixtures | PARTIAL, not PASS - durable UNKNOWN recovery and persistent halt fixtures pass; process-kill and actual executor recovery remain unverified |
| AC-07 | Owner-authorized MT5 Demo round trip and identifier/account reconciliation | BLOCKED - account details and authorization absent |
| AC-08 | Secret scan, client-bundle inspection, and live-account denial test | PARTIAL, not PASS - source and built client-bundle secret scans plus API live-mode denial pass; no MT5 executor exists to inspect |
| AC-09 | Component tests plus desktop and mobile browser inspection for safe state and unavailable controls | PARTIAL, not PASS - component tests and local Firefox inspection pass; committed cross-browser regression and authenticated backend integration remain |

No row can change to `PASS` without a named command or procedure, source revision, environment identity, expected result, observed result, and retained evidence reference.

## Plan

1. Record the missing owner and broker decisions without collecting credentials in the repository.
2. Select and pin Python, Node, package-manager, and MQL5 build assumptions.
3. Define schemas and the executor adapter interface.
4. Build the in-memory and durable simulator with duplicate, timeout, rejected-SL, partial-fill, and restart fixtures.
5. Implement risk sizing and journal state transitions with targeted tests.
6. Implement the MT5 Demo adapter and deny live or mismatched accounts.
7. Run all local acceptance checks and review the diff against this contract.
8. Prepare a dry run showing the exact account, symbol, risk estimate, command, abort conditions, and recovery action.
9. Obtain explicit authorization for one Demo open-to-close action.
10. Execute, reconcile, and report the operational result separately from local implementation evidence.

## Authorization

- Reading documents, creating local project files, implementing code, and running local simulators and tests are authorized by the project setup request.
- Installing dependencies must remain within project policy and use pinned versions after admission review.
- A real Demo send is **not authorized by this contract text**. It requires explicit owner authorization that identifies the Demo account target and the intended action after the dry-run preview exists.
- Live-account use is outside scope and cannot be authorized as an incidental extension of SCN-001.

## Budget and retry limits

- Prefer bounded experiments that produce new evidence.
- Stop after three failed iterations that add no new evidence and checkpoint the findings.
- Retry only transient, idempotent operations within a declared deadline.
- Never retry an external send whose effect is unknown; reconcile first.
- Paid services, VPS creation, and runtime API use require a separate approved cost target.

## Recovery

- Before external send: cancel safely by leaving the command unsent and recording the reason.
- After send with known rejection: retain the terminal result; do not mutate it into a retry.
- After unknown effect: halt new work, reconcile against MT5, and quarantine unresolved state.
- After fill without confirmed SL: follow an owner-approved emergency-close runbook and report the actual state.
- After restart: restore the journal and risk state, verify account identity, reconcile MT5, then decide whether the system may accept new work.

## Definition of Ready

Local schema, simulator, and test work is ready. Real Demo adapter verification remains blocked on:

- Broker name and Demo server.
- Demo account currency and starting capital.
- Exact symbol and contract details.
- Netting or hedging mode.
- Trading-hours and overnight policy.
- Named total-halt release authority.
- Approved secret-delivery method.

## Definition of Done

- AC-01 through AC-06 and AC-08 pass on the exact candidate revision.
- A review finds no unresolved Critical or High defect in the affected boundaries.
- The dry-run preview and recovery procedure are complete.
- AC-07 passes on the explicitly authorized Demo target, or the task is reported as implementation verified with Demo operation still blocked.
- All limitations, environment differences, and remaining unknowns are reported without labelling them passed.
