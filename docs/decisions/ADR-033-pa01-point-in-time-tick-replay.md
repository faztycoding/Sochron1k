# ADR-033: PA01 point-in-time tick replay produces evaluation bundles

## Status

Accepted for the offline Demo research toolchain.

## Context

SCN-018 through SCN-022 can calculate and publish a point-in-time PA01 decision,
and SCN-029 can evaluate a strict labelled-trade bundle. The missing boundary is a
repeatable transformation from historical decision evidence and ordered quotes to
that bundle. Using only M5 OHLC would make a bar that touches both SL and TP
ambiguous and would not implement the Blueprint's next-tick entry rule.

## Decision

Add a pure replay kernel and an explicit local CLI. The replay input contains
closed M5/H1 evidence with availability times, an ordered Bid/Ask tick stream and
one policy observation for every eligible M5 boundary. The kernel invokes the
existing PA01 implementation; it does not accept preselected signals.

Entries and exits use the executable side of the ordered quote stream. P/L is
decomposed onto the Bid path so one configured fixed spread scenario can be
deducted exactly once by SCN-029 even when observed spreads vary. The configured
spread must be at least the maximum observed input spread, preventing the replay
from silently improving the evidence. Equity is marked on every tick while a
position is open.

The CLI writes only one canonical private bundle via atomic create-once linkage.
It has no network client, database credential, strategy-promotion or execution
dependency.

## Consequences

- The Statistics data path can be exercised end to end once a conforming historical
  replay artifact is supplied.
- Future evidence cannot change earlier decisions because every cutoff is rerun
  against `available_at_utc`.
- Tick-level ordering removes OHLC SL/TP ambiguity for admitted inputs.
- The first version intentionally rejects incomplete scheduling, horizon coverage
  and understated spread instead of guessing.
- Source acquisition, Parquet capture, variable-cost sensitivity grids and real
  broker contract parity remain separate work and evidence gates.

## Rejected alternatives

- **Infer outcomes from M5 high/low:** rejected because SL/TP order can be unknown.
- **Accept a caller-supplied signal or label:** rejected because it permits
  cherry-picking and disconnects results from the pinned PA01 code.
- **Count observed spread in fill P/L and deduct it again:** rejected as double
  counting. The replay instead emits gross Bid-path P/L and one explicit fixed
  spread deduction.
- **Publish directly to Supabase:** rejected because replay, evaluation and remote
  publication have different failure and authorization boundaries.
