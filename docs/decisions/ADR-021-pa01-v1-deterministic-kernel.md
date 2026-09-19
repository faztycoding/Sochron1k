# ADR-021: PA01-v1 deterministic decision kernel

- Status: Accepted as an experimental calculation boundary
- Date: 2026-09-20

## Context

The Blueprint defines PA01 as the AI-disabled baseline, but names such as EMA20,
ADX14 and pivot L2/R2 do not by themselves fix initialization, tie handling,
warm-up or evidence timing. Implementing a scheduled producer before those details
were versioned would make historical decisions difficult to reproduce and could
confirm pivots with future bars.

## Decision

`sochron_worker.pa01` is a pure calculation kernel with no I/O. `PA01-v1.0.0`
uses strict L2/R2 pivots with no tied extrema, a fixed maximum 100-bar window,
minimum 60 M5/12 H1 warm-up, standard EMA seeded by an SMA, and an explicitly
versioned Wilder ATR/ADX initialization. Every bar retains close time and
`available_at`; the as-of cutoff excludes later evidence, and a pivot confirms at
the second right bar's availability.

Unexplained gaps block. A market-close gap may be admitted only when it is
explicitly classified and no longer than 72 hours; the kernel never fills bars.
Policy-state blockers remain inputs and dominate strategy setup. The kernel records
a proposed stop from confirmation-close evidence, but the future entry adapter must
recheck drift, spread, stop distance, contract, risk and next-tick price.

Stable parameter, dataset, setup and decision hashes make identical evidence
replayable. BUY/SELL/WAIT/BLOCK are evidence outputs only: order creation and risk
admission are hard-coded false.

## Consequences

- Appending bars unavailable at an earlier cutoff cannot repaint its decision.
- The exact calculation can be tested before choosing a data-source/scheduling and
  persistence architecture.
- The custom initialization is not yet proven numerically identical to MT5 or an
  external indicator library. It must not be silently replaced within PA01-v1.
- `/api/owner/signals` remains `awaiting_source` until aggregation, producer
  scheduling and atomic evidence persistence are implemented and verified.
