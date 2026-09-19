# SCN-016 Owner signal evidence

## Task contract

Add the missing authenticated owner read model and browser panel for synchronized
strategy signals. The read model consumes the existing Supabase `signals`,
`experiments`, and `strategy_versions` relations through the verified owner's
access token and existing owner RLS. It does not generate a strategy decision,
write research data, create a command, or imply that a signal passed execution or
risk admission.

The browser route is `/api/owner/signals`; the FastAPI route is
`/owner/signals`. The panel belongs immediately after the market chart and before
history because Blueprint screens 05-08 group chart, indicators, signals, and
decision evidence. The API connection map must identify the route and its pending
producer dependency even when the synchronized source contains no signals.

## In scope

- Forward only the already online-verified owner bearer token and configured
  publishable/legacy anon key to the same pinned Supabase origin.
- Select at most the latest 50 signal rows, using deterministic
  `confirmed_at DESC, id DESC` ordering and embedded experiment/strategy evidence.
- Validate every upstream field, timestamp relation, nested owner ID, action,
  lifecycle status, evidence ID, version and code hash before returning a row.
- Expose signal/setup IDs, exact action, formed/confirmed/expiry/created times,
  evidence IDs, blocked reason, experiment ID/status/policy version, and strategy
  version/status/code hash/data cutoff.
- Render BUY, SELL, WAIT and BLOCK distinctly, with UTC and Asia/Bangkok time,
  active/expired state, loading, empty, denied, unavailable and retry states.
- Keep the response and UI explicitly Demo-only, read-only and non-authoritative
  for order, fill, risk admission, probability of profit, or strategy promotion.
- Verify owner isolation against real local Auth/PostgREST plus strict synthetic
  upstream faults and a production browser build.

## Out of scope

- PA01/SMC01/ICT01 feature calculation or signal production.
- Strategy activation, selection, promotion, parameter editing, AI/news
  interpretation, backtests, statistics, command creation, position sizing, risk
  admission, MT5 execution, or a live-account path.
- Service-role credentials in FastAPI or the browser.
- Hosted Supabase writes, MT5 operations, deployment, or release approval.

## Acceptance criteria

- **AC-01 Owner authentication:** missing/duplicate/invalid bearer values return
  the existing owner Auth denial, and a valid non-owner returns `403` before any
  signal data is returned.
- **AC-02 RLS-scoped source:** the request uses the verified user's token and an
  unprivileged project key. Local integration proves another owner's rows are not
  readable, while the response independently rejects any nested owner mismatch.
- **AC-03 Bounded strict projection:** the reader accepts only a JSON array within
  the response-byte limit, returns no more than 50 deterministically ordered rows,
  rejects duplicates or malformed evidence, and never exposes owner UUIDs,
  internal numeric keys, tokens, URLs, parameters or unrestricted upstream errors.
- **AC-04 Temporal truth:** `formed_at <= confirmed_at < expires_at`,
  `created_at >= confirmed_at`, and `strategy.data_cutoff <= confirmed_at` are
  enforced. The UI never presents a row before its stored `confirmed_at` and
  labels expired evidence without rewriting the stored action.
- **AC-05 Exact decision semantics:** BUY, SELL, WAIT and BLOCK remain distinct;
  missing source rows render `awaiting_source`. A signal is never described as an
  order, fill, approved trade, calibrated probability, or executable instruction.
- **AC-06 No mutation authority:** source/static checks prove the route and panel
  contain no insert/update/delete/RPC request, command endpoint, automatic retry
  mutation, strategy dispatcher, risk override, halt release, or Auto Trading
  control.
- **AC-07 UI placement and states:** the owner workspace renders `#signal-evidence`
  after `#market-chart` and before `#bar-history`, provides loading/empty/error/
  reconnect/auth states, preserves Charcoal Gold styling, keyboard access and
  320 px page containment.
- **AC-08 Connection map:** the public redacted map lists
  `/api/owner/signals`, implementation `available`, source
  `supabase_signals`, and runtime separately as awaiting Auth configuration or
  awaiting synchronized strategy evidence. Public readiness remains false.
- **AC-09 Local end to end:** real local Auth/PostgREST with two generated users
  proves owner isolation and displays one strictly synthetic, versioned signal in
  the production browser build. MT5 and hosted Supabase remain `NOT RUN`.
- **AC-10 Regression gates:** affected FastAPI, web, RLS/static, package,
  container and browser verifiers pass without weakening existing assertions.

## Evidence boundary

A passing SCN-016 verifies the owner signal read boundary and browser projection
only. It does not prove PA01 correctness, temporal feature parity, a promoted
strategy, profitability, MT5 agreement, risk/execution admission, or Demo release
readiness. Until a versioned signal producer writes validated rows, the correct
runtime state is `awaiting_source`.
