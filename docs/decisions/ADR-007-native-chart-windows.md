# ADR-007 Native MT5 chart windows, separate from sampled quotes

2026-09-17; SCN-006; accepted for local implementation, actual terminal unverified.

Use versioned `CopyRates` windows for the monitoring chart. One-second Bid/Ask
samples cannot reconstruct candle extremes or tick-volume and must not be repackaged
as native bars. Preserve broker timestamps, exact decimal strings, tick volume,
spread in points and the symbol's Bid/Last chart basis. These are not execution
prices or real-volume/order-flow evidence. Keep the last row unconfirmed, even if
its nominal close time has passed; a later native bar establishes closure.

A separate chart sequence/challenge avoids changing the deployed telemetry receipt
shape and its 16 KiB limit. Chart input is capped at 128 KiB and 240 rows per one
of four fixed timeframes, with a separate 15-second snapshot-age limit. Live quote
freshness remains the independent five-second telemetry status. Owner authorization
and no-store behavior are reused, not implemented again.

Pin a verified fixed-offset validity interval in a private chart configuration.
Without it charts stay disabled. Current broker offset alone cannot correctly map
historical windows crossing a DST change. Reject any snapshot outside the reviewed
interval rather than assuming a timezone rule. A future versioned broker calendar
may replace this deliberate local limitation after actual broker evidence exists.

Bounded monitoring cache, no new database or production dependency at the API stage.
Closed-bar conflicts and shrinking forming-bar ranges/volume are rejected rather
than silently rewriting evidence. Legitimate broker corrections require reviewed
resynchronization; durable history/revision storage remains separate product work.
Chart data is not a strategy input until temporal availability and persistence are
implemented and tested. Actual browser chart work retains Lightweight Charts per
the blueprint; no switch to a different charting stack is implied.

Official references: [CopyRates](https://www.mql5.com/en/docs/series/copyrates),
[MqlRates fields](https://www.mql5.com/en/docs/constants/structures/mqlrates),
[series synchronization](https://www.mql5.com/en/docs/series/seriesinfointeger).

EA source increment: keep native windows separately opt-in in the existing read-only
observer. Alternate telemetry and one chart timeframe per timer, enforce a single
request budget, and skip unavailable history. This deliberately requires warmed,
synchronized terminal history; it does not introduce a synchronous download loop.
History-duration and transport-duration latches are after-the-fact diagnostics, not
hard deadlines or suitability for a future risk loop. Rejected chart data remains
latched for review while independent telemetry may continue. Actual terminal build,
50-case pure self-test, source-to-wire parity and timing evidence are still absent.
