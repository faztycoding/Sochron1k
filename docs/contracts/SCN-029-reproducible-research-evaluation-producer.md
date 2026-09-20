# SCN-029 Reproducible research evaluation producer

## Task contract

Add a disabled-by-default worker that deterministically evaluates one immutable
closed-trade evidence bundle and can publish one owner-scoped `evaluations` row
for the existing `/owner/statistics` read model. The worker computes the metrics
shown by the UI; callers cannot submit precomputed metrics or a promotion result.

The first producer consumes already labelled setup-to-flat outcomes. It does not
generate trades from bars or ticks, resolve ambiguous intrabar ordering, select a
strategy or claim an edge. A bundle with ambiguous, rejected, WAIT or
counterfactual records retains those records but never counts them as wins or
losses.

## In scope

- Validate one canonical JSON bundle with exact dataset/code identity, UTC event
  and availability times, one temporal evaluation window, embargo evidence,
  explicit costs and a mark-to-market equity path.
- Aggregate each filled setup-to-flat record once, including partial-deal totals
  supplied by the upstream labeller, while retaining non-trade dispositions.
- Derive win/loss/breakeven counts, net return, expectancy in R, profit factor and
  equity maximum drawdown. Derive a deterministic moving-block bootstrap 95%
  interval with an explicit seed, sample count and block length.
- Require spread, slippage, commission, swap and operating costs without double
  counting. Verify exact gross-minus-costs-to-net arithmetic per closed trade.
- Persist the exact evaluation envelope in a private SQLite write-ahead journal
  before a Supabase RPC send. A lost or ambiguous response remains `UNKNOWN` and
  is reconciled by exact fingerprint before any retry.
- Add an insert-or-verify Supabase receiver for strict producer rows while
  preserving owner RLS and legacy/manual fixture rows. The receiver is callable
  only by backend roles and exposes no browser write path.
- Package an explicit operator CLI. Missing configuration is `DISABLED`; import,
  API startup and default Compose start no evaluation work or network request.

## Out of scope

- Building labels or entry/exit fills from raw M1/OHLC/tick data, running a PA01
  backtest, resolving `AMBIGUOUS` paths or proving absence of feed bias.
- Acquiring licensed data, deciding cost assumptions, choosing temporal windows,
  fitting a model or using a holdout for tuning.
- Strategy promotion, activation, command creation, position sizing, risk or halt
  mutation, MT5 execution, hosted writes, deployment or a live-account path.

## Acceptance criteria

- **AC-01 Strict immutable input:** accept one canonical bundle no larger than
  8 MiB with protocol/version, 64-hex dataset and strategy-code hashes, unique
  bounded setup/evidence IDs and UTC timestamps. Reject unknown fields,
  duplicate IDs, non-finite numbers, noncanonical input and any record whose
  `available_at` precedes its event or outcome horizon.
- **AC-02 Honest trade unit:** count only `closed_trade` records that have a
  positive filled volume, entry no earlier than the decision and an exit no
  earlier than entry. Retain `wait`, `rejected`, `counterfactual` and `ambiguous`
  records in the manifest counts but never include them in sample size, win rate,
  expectancy, profit factor or net return. A bundle with no closed trade fails.
- **AC-03 Exact cost accounting:** every closed trade records gross P/L, positive
  initial risk, lot volume, point value and swap in account currency. The producer
  derives spread, slippage, commission and operating cost from the stated fixed
  assumptions, requires swap to be zero when excluded, and derives net P/L as
  gross less all five components exactly. It never derives a more favourable cost.
- **AC-04 Temporal split and availability:** every decision and outcome lies
  inside the declared evaluation window; the label horizon cannot cross its end.
  Non-train splits require a prior-development cutoff plus the declared embargo
  no later than evaluation start. The data cutoff equals the window end. Later
  records cannot change an earlier bundle hash or evaluation.
- **AC-05 Equity and drawdown:** the path starts at positive initial equity, is
  strictly time ordered, ends at initial equity plus aggregate net P/L and
  includes at least one explicitly open-exposure mark within every filled trade.
  Maximum drawdown is computed peak-to-trough from the full path, not only closes.
- **AC-06 Deterministic uncertainty:** expectancy is the exact mean net R. The 95%
  interval uses a documented moving-block bootstrap seeded from the bundle, with
  1,000-100,000 resamples and a valid block length. Same input and code produce
  byte-identical metrics, manifest and evaluation fingerprint.
- **AC-07 UI contract compatibility:** emitted `metrics` and `cost_assumptions`
  conform exactly to SCN-017; the existing owner read model can display the row
  without recalculation. Training remains labelled in-sample and no producer
  output contains a forecast, guarantee or promotion decision.
- **AC-08 Durable idempotent publication:** private storage, fixed schema, process
  lock, binding audit and full-sync SQLite transitions prove
  `PREPARED -> UNKNOWN -> VERIFIED|QUARANTINED`. The first external send occurs
  only after durable prepare. `UNKNOWN` performs read-only reconciliation before
  another bounded send; same fingerprint/different body quarantines.
- **AC-09 Owner-scoped receiver:** the RPC verifies owner/strategy/optional
  experiment links, exact strategy code hash, temporal causality, metric/cost
  consistency and bounded strict manifest. Concurrent same-envelope calls produce
  one row; a conflicting source identity fails. Functions use an empty search
  path, explicit grants and no `SECURITY DEFINER`.
- **AC-10 Immutability and authorization:** producer rows cannot be updated or
  deleted through backend CRUD; anon/authenticated cannot call producer RPCs or
  write evaluations. Existing owner SELECT RLS remains enforced and browser/API
  code gains no service credential or mutation route.
- **AC-11 Failure paths:** malformed input, future evidence, split leakage,
  ambiguous-as-trade, cost mismatch, missing open-exposure marks, corrupt/full
  journal, lock contention, timeout after acceptance, malformed read-back,
  receiver conflict and send-budget exhaustion fail closed without fabricated
  statistics or a second logical evaluation.
- **AC-12 Packaging and regression:** the installed wheel contains the evaluator
  and operator. The installed command is inert without private configuration.
  Targeted Python, SQL/RLS, package, container and owner-browser checks pass where
  the current environment supports them; unrun hosted, MT5 or Docker checks remain
  explicitly `NOT RUN`.

## Evidence boundary

A passing SCN-029 proves metric calculation and durable publication for a supplied
synthetic or separately validated evidence bundle. It does not prove the bundle's
market data, labels, fills or costs are representative; it does not prove PA01 has
an edge; and it does not clear a strategy-promotion or unattended-Demo gate.
