---
name: sochron-mt5-execution
description: Build or review the Sochron1k MQL5 EA and Demo execution adapter, command lifecycle, broker event reconciliation, partial fills, and SL confirmation. Use for Sochron1k execution work, not generic investment advice or unrelated trading projects.
metadata:
  version: "1.0.0"
---

# Sochron1k MT5 execution

Locate the Sochron1k repository from the working directory. Read its `AGENTS.md`, `docs/architecture.md`, and the current execution contract (initially `docs/contracts/SCN-001-mt5-demo-round-trip.md`). The blueprint sections 04, 05, 13, 14 and 22 define the product. If those sources are absent, do not invent a broker configuration; continue isolated adapter design with explicit assumptions.

## Select the working mode

- Local implementation: implement interfaces, simulator fixtures, journal integration and MQL5 source without needing account credentials.
- Compile/test: discover the actual MetaEditor/terminal installation, build number and terminal data path. Record the source digest, fresh compiler log and generated artifact; a Wine exit code alone is not proof of compilation. If MetaEditor is absent, report compilation unverified and continue Python-side contract tests.
- Broker operation: use existing authorization covering the specific Demo account and action. Prepare the command and risk preview first. Never infer authorization for live accounts or a different terminal from a general development request.

## Executor rules

1. Require the terminal's trade mode to equal `ACCOUNT_TRADE_MODE_DEMO`; deny real, contest, missing, and unknown modes. Match expected account identity, server, symbol, currency and margin mode immediately before every account mutation. A config string saying `demo` is insufficient.
2. Discover tick size, digits, volume min/max/step, stops/freeze levels, supported filling modes and margin from the actual contract. Align prices to tick size, not only decimal digits. Recheck risk after alignment. Do not silently move a strategy's stop to meet broker limits.
3. Authenticate the bridge separately from browser sessions. Validate command schema, expiry, identity and fingerprint at the executor too. Keep executor ownership exclusive with an enforceable lock/fencing design, including reconnect and restart paths.
4. Commit command intent and attempt identity before the external send. Concurrent submissions reserve the single exposure slot transactionally. HTTP success and `OrderSend` returning true do not establish a fill.
5. Track requested, accepted, filled and remaining volume. Store order ticket, deal ticket and position identifier separately. Handle repeated/out-of-order transaction notifications without duplicating deals or regressing a terminal state. Fetch broker state to resolve uncertainty; do not rely on comments alone.
6. If acceptance may have occurred but the response is missing, mark `UNKNOWN`, reserve the exposure slot and reconcile orders, positions and history. An empty or failed query is not proof that no order exists. Do not send a replacement while uncertainty remains.
7. A partial fill with a pending remainder is one logical command and still occupies the single exposure slot. Do not create another independent entry. Validate aggregate risk and protection for filled and outstanding volume.
8. Confirm the broker-side SL against the intended position before reporting protection. Rejected or missing SL triggers the approved emergency procedure; show unresolved/closing state until broker evidence confirms closure. Apply reconciliation to ambiguous close/cancel requests as well as entries.
9. Keep event handlers bounded. Network communication must not stall tick/timer risk management; measure worst-case blocking time in the actual topology. Use simulated transport in Strategy Tester where external requests are unavailable.

## Verification and handoff

Map tests to the current contract: deny non-Demo/mismatched identity; duplicate and changed-payload submissions; accepted-send/lost-response; partial fills; rejected SL; reordered events; expired commands; disconnected executor; restart before/after send; unknown foreign positions. Use pytest for simulator/contract verification and actual MetaEditor/MT5 evidence for MQL5 behavior. Neither substitutes for the other.

Return changed boundaries, acceptance IDs, commands run, candidate/source digest, terminal/config/fixture identity, observed broker IDs and unresolved effects. Keep credentials out of all evidence. Simulator passes do not close the real-Demo acceptance criterion.

## Official references

Consult the relevant current API page before implementing the operation:

- [OrderSend](https://www.mql5.com/en/docs/trading/ordersend)
- [OnTradeTransaction](https://www.mql5.com/en/docs/event_handlers/ontradetransaction)
- [OrderCheck](https://www.mql5.com/en/docs/trading/ordercheck)
- [Account properties](https://www.mql5.com/en/docs/constants/environment_state/accountinformation)
- [Symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants)
- [WebRequest limitations](https://www.mql5.com/en/docs/network/webrequest)
