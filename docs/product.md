# Sochron1k Project Profile

## Decision summary

Sochron1k will begin as a **prototype moving toward a Demo-only pilot**. The first release is not a live-trading product and must not contain a path that can select or operate a live account.

The project uses a **High assurance** process because it combines unattended automation, broker credentials, external order side effects, persistent risk state, and recovery requirements. Demo-only scope limits financial loss but does not make incorrect execution or unsafe promotion acceptable.

## Profile

| Field | Adopted value |
| --- | --- |
| Project | Sochron1k |
| Product owner | Project owner; personal name not yet recorded |
| Technical decision authority | Project owner until explicitly delegated |
| Current stage | Prototype |
| Target stage | Demo-only pilot after unattended-Demo gates pass |
| Target user | One owner operating one dedicated MT5 Demo account |
| Profiles | Web, data, AI-assisted research, financial automation |
| Risk tier | High assurance |
| Product source | Blueprint v1.1 dated 16 September 2026 |
| Process source | Agentic Software Engineering Handbook v3.0 dated 16 September 2026 |

## Problem and intended outcome

The project needs an auditable way to determine how explicitly defined XAU/USD strategies behave after spread, slippage, fees, and operating costs. It must show each signal, block, command, broker response, fill, position, and close reason while enforcing the agreed risk limits even through restarts or partial service failures.

The outcome is a repeatable research and Demo execution system, not a promise of profit. Strategy names such as Price Action, SMC, and ICT are experiment labels. They do not establish an edge until versioned out-of-sample evidence supports that claim.

## Success measures

### Engineering success

- The system can read Demo XAU/USD market and contract data and complete one verified open-to-close round trip.
- Duplicate or ambiguous commands do not create an additional logical trade.
- Restart recovery reconstructs pending commands, broker-side SL state, positions, and halt state before accepting new work.
- UI and synchronized history reconcile with MT5 identifiers and account values.
- Critical failure scenarios in the blueprint pass on the actual execution environment before unattended Demo operation.

### Research success

- Results are separated by strategy version, setup, side, session, regime, and cost assumptions.
- Out-of-sample expectancy is reported with uncertainty and remains positive under agreed spread and slippage sensitivity before a candidate is considered for Demo promotion.
- Win rate is reported with sample size and never used alone as a success claim.

### Operational success

- Feed-to-UI latency is measured as p50 and p95; the initial display target is approximately one second when new data is available.
- Price is treated as stale after an initial five-second threshold only while the market is expected to be active; the threshold remains an experiment parameter.
- Alerts, backups, restore, and reconciliation are exercised before unattended operation.
- The local owner alert inventory may show derived conditions before delivery is configured; a visible row is not evidence that an external alert was sent or acknowledged.
- RPO and RTO are not yet set. They are required before the unattended-Demo release gate.

## Core journeys

1. Connect and verify a dedicated MT5 Demo account without exposing credentials to the browser.
2. Observe current Bid/Ask, feed age, account currency, Equity, risk state, and Demo status.
3. Generate a versioned PA01 signal from closed bars and record the evidence available at decision time.
4. Validate the command, journal it, send it once, and reconcile the MT5 order, deal, and position identifiers.
5. Maintain broker-side SL protection and enforce daily and experiment halts across restarts.
6. Review trades, costs, strategy versions, and experiment evidence without rewriting historical snapshots.
7. Stop, recover, reconcile, and resume using confirmed external state.

## Non-goals for the first release

- Live or real-money trading.
- Deposits, withdrawals, copy trading, signal sales, or multi-account operation.
- Martingale, averaging down, widening stop losses, or increasing risk to meet an income target.
- Automatic strategy promotion or autonomous risk-policy changes.
- Order Flow trading without licensed data and verified provenance.
- Claims that candle data reveals institutional intent or that the system is AGI.
- Guaranteed monthly profit or a guaranteed win rate above 50%.

## Risk policy

| Control | First-release value |
| --- | --- |
| Account | Dedicated Demo account; no manual trades mixed in |
| Risk per trade | At most 0.25% of current Equity, including the defined cost budget |
| Daily halt | 0.75% Equity loss from the Thailand-day baseline |
| Experiment halt | 2% Equity loss from initial experiment capital; no automatic reset |
| Exposure | One position or one pending order |
| At a limit | Cancel pending work, attempt an authorized close, and lock new entries |
| Forbidden | Martingale, averaging down, wider SL, AI halt release, silent risk changes |

## Data classification and sources of truth

| Data | Classification | Source of truth |
| --- | --- | --- |
| Public or licensed market/news data | Public or contract-limited | Recorded source, feed ID, event time, and revision |
| Prices, orders, deals, positions, broker-side SL | Confidential operational | MT5 and the EA |
| Active strategy rules and versions | Internal | Versioned repository and backend configuration |
| Unsynchronized commands and events | Confidential operational | Local durable journal |
| Synchronized research and audit history | Confidential | Supabase with owner-based RLS |
| Passwords and privileged API keys | Restricted | Executor or secret store; never the repository or browser |

Initial retention is 30 days for raw ticks on the VPS and 14-30 days for diagnostic logs. Signals, deals, experiments, and strategy versions remain for the experiment lifetime and must be exported before deletion. Retention must be revisited after measured storage use.

## Stack direction

- React, TypeScript, and Vite for `apps/web`.
- Python, FastAPI, and Pydantic for `services/api`.
- Python worker processes for asynchronous news, AI, synchronization, and reconciliation.
- MQL5 EA for broker execution and broker-side risk behavior.
- Supabase Postgres, Auth, and RLS for synchronized application data.
- SQLite WAL and Parquet for the durable local outbox and raw tick retention.
- Docker Compose and a reverse proxy for the VPS application services.
- pytest and Playwright for risk-driven verification.

Python 3.14.7, Node.js 24.21.0 and dependency lockfiles are now pinned; see [ADR-002](decisions/ADR-002-pinned-runtime-toolchain.md) and the local runtime runbook. This does not establish an MT5 terminal build, target-host compatibility or release reproducibility for unimplemented components.

## Budget and delivery frame

The blueprint estimates 200-320 hours over approximately 6-10 development weeks, excluding the time needed to collect forward results. Public-price estimates in the blueprint are planning assumptions, not authorization to purchase services. No paid resource may be created without explicit owner authorization for the target and price.

## Required owner decisions

The following values are not available in the repository and block real Demo integration or deployment, but they do not block contracts, simulators, schema design, or local unit tests:

- Broker name and Demo server.
- Demo account currency and starting capital.
- Exact XAU/USD symbol and contract specification.
- Netting or hedging account mode.
- Allowed trading hours and overnight-position policy.
- VPS region and payment term.
- Monthly API budget.
- Domain and alert destination.
- Named authority allowed to release a total halt.

These decisions must be recorded in a versioned task contract or decision record. Credentials must be delivered through an approved secret channel, not through chat or committed files.
