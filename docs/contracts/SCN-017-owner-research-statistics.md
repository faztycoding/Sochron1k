# SCN-017 Owner research statistics

## Task contract

Add the authenticated owner read model and browser panel for versioned research
evaluations. The read model consumes existing owner-RLS `evaluations`,
`strategy_versions`, and optional `experiments` rows. It projects recorded research
evidence; it does not infer performance from UI state, recalculate broker P/L,
promote a strategy, or grant execution authority.

The browser route is `/api/owner/statistics`; the FastAPI route is
`/owner/statistics`. The panel belongs after signal evidence and before raw bar
history. Empty data must remain `awaiting_source` until a reproducible research
producer writes a conforming evaluation.

## In scope

- Forward only the already online-verified owner bearer token and configured
  publishable/legacy anon key to the same pinned Supabase origin.
- Select at most the latest 30 evaluations with deterministic
  `created_at DESC, id DESC` ordering and embedded strategy/experiment evidence.
- Require an exact metric contract containing sample size, win/loss/breakeven
  counts, expectancy in R, its 95% interval, net return, maximum drawdown and
  profit factor; derive displayed win rate only from the validated counts.
- Require exact spread, slippage, commission, swap and per-trade operating-cost
  assumptions with a currency, plus dataset hash, split, data cutoff, strategy
  code hash and optional experiment identity.
- Render train/validation/test/walk-forward/shadow-Demo distinctly; label train as
  in-sample and never present it as out-of-sample evidence.
- Render sample size beside win rate, uncertainty beside expectancy and all cost
  assumptions. Preserve UTC and Asia/Bangkok display for the evaluation cutoff.
- Verify owner isolation against real local Auth/PostgREST and strict synthetic
  upstream faults in the production browser build.

## Out of scope

- Producing research datasets, PA01 features, temporal splits, backtests or
  shadow-Demo evaluations.
- Computing realized Demo P/L from MT5 deals, merging deposits/withdrawals,
  selecting a strategy or deciding whether evidence clears a promotion gate.
- Strategy mutation, command creation, position sizing, risk admission, MT5
  execution, hosted Supabase writes, deployment or a live-account path.

## Acceptance criteria

- **AC-01 Owner authentication:** missing/duplicate/invalid bearer values use the
  existing owner Auth denial, and a valid non-owner receives `403` before any
  evaluation is returned.
- **AC-02 RLS-scoped source:** the verified user's token and an unprivileged
  project key are used. Local integration proves another owner's evaluation is
  not readable, while the response rejects any nested owner mismatch.
- **AC-03 Bounded strict projection:** accept only a JSON array within 256 KiB,
  return no more than 30 deterministically ordered unique rows and reject unknown,
  malformed or non-finite metrics. Do not expose owner UUIDs, numeric database
  keys, tokens, URLs, unrestricted JSON or upstream errors.
- **AC-04 Reproducible identity:** every row exposes an exact 64-hex dataset hash,
  strategy version/code hash, split and data cutoff. Strategy data cutoff cannot
  be later than evaluation data cutoff, and creation cannot precede that cutoff.
- **AC-05 Honest metrics:** sample size equals wins plus losses plus breakeven;
  win rate is derived from those counts; the 95% expectancy interval contains the
  point estimate; maximum drawdown is 0-100%; and all cost assumptions are shown.
  No value is described as a guarantee, forecast or promotion decision.
- **AC-06 No mutation authority:** source/static checks prove the route and panel
  contain no write/RPC request, strategy promotion, command endpoint, risk
  override, halt release or Auto Trading control.
- **AC-07 UI placement and states:** `#research-statistics` renders after
  `#signal-evidence` and before `#bar-history`, supports loading/empty/error/retry/
  auth states, preserves Charcoal Gold styling, keyboard access and 320 px page
  containment. Desktop and mobile navigation link to the panel.
- **AC-08 Connection map:** the redacted map lists `/api/owner/statistics`,
  implementation `available`, source `supabase_evaluations`, and runtime as
  awaiting Auth configuration or source evidence. Public readiness remains false.
- **AC-09 Local end to end:** real local Auth/PostgREST with two generated users
  proves owner isolation and displays one strictly synthetic evaluation in the
  production browser build. MT5 and hosted Supabase remain `NOT RUN`.
- **AC-10 Regression gates:** affected FastAPI, web, RLS/static, package,
  container and browser verifiers pass without weakening existing assertions.

## Evidence boundary

A passing SCN-017 verifies only an owner-scoped projection of already recorded
evaluation evidence. It does not prove the research producer is correct, the
dataset is licensed or immutable, temporal leakage is absent, transaction costs
match a broker, results reproduce, a strategy has an edge, or Demo release gates
have passed. Those remain separate research and execution work.
