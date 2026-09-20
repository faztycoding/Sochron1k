# SCN-023 coherent PA01 policy-evidence writer

## Task contract

Add a disabled-by-default API-side coordinator that combines one fresh MT5 quote
and symbol-session observation, one fresh complete Demo execution inventory, and
one stable owner-only news-gate observation at an explicit UTC cutoff. It publishes
the exact `PA01PolicyEvidence` handoff consumed by SCN-022 using an atomic,
owner-only file replacement.

This increment supplies policy evidence only. It does not schedule or invoke the
PA01 producer, write Supabase, calculate a trade, perform risk admission, call an
MT5 mutation API, deploy a service or enable Auto Trading.

## Source and cutoff rules

- Telemetry protocol v2 preserves Bid/Ask and adds the market-open result sampled
  by the read-only MT5 observer from the symbol's broker trade-session metadata at
  the same tick. Protocol v1 remains valid for monitoring but is not policy input.
- Account evidence comes only from a fresh, complete execution inventory whose
  Demo identity and magic number passed the existing bridge fence and which has no
  foreign orders or positions. Any remaining entry volume or active API dispatch
  is pending; any positive open-position volume is exposure.
- News evidence is one bounded, stable, owner-only `sochron.news-gate.v1` file.
  Its declared coverage must contain the cutoff, its revision must be explicit,
  and its observation may be at most five minutes old. Missing or incomplete
  calendar evidence is not interpreted as clear.
- The coordinator captures its UTC cutoff only after both authenticated MT5
  streams are available. Every source observation must be causal and fresh at
  that cutoff. Sources are bound to the same exact Demo identity and symbol.
- Evidence IDs are derived from canonical source content. Callers cannot provide
  the policy IDs, price-stale result, feed binding or AI state.

## Publication and failure rules

- Configuration is a canonical owner-only file selected only by
  `SOCHRON_POLICY_WRITER_CONFIG_FILE`. Absence or `{"enabled":false}` performs no
  file read or write. Enabled configuration binds the exact Demo identity,
  native archive UUID, output path and news-gate path.
- The output parent is an existing owner-private directory. A complete canonical
  JSON file is written and synced under a new private temporary inode, atomically
  replaced at the configured output path, then the directory is synced. Partial
  JSON is never published.
- Missing, stale, malformed, changed-during-read or mixed source evidence produces
  no new policy file. A prior file is historical evidence and naturally expires
  under SCN-022's 30-second admission rule; it is never rewritten with guessed
  blockers.
- Runtime status is redacted and public at `/policy/v1/status`. It contains only
  fixed state enums, source-ready booleans and safe timestamps; never identity,
  prices, account values, event IDs, revisions, paths, payloads or credentials.

## Acceptance criteria

- **AC-01 private opt-in:** missing/disabled configuration is inert; enabled
  configuration requires canonical owner-private files/directories, distinct
  input/output paths, a canonical archive UUID and exact bridge identities.
- **AC-02 authoritative market evidence:** telemetry v2 accepts only a causal
  MT5-derived session result bound to the same fresh tick. V1 remains backward
  compatible for monitoring but cannot cause a policy write.
- **AC-03 complete account evidence:** only fresh complete fenced execution
  inventory is admitted. Exposure, remaining order volume and active dispatch are
  derived conservatively; missing or foreign inventory fails closed.
- **AC-04 explicit news evidence:** only a strict, stable, fresh, coverage-complete
  news-gate revision is admitted. Missing or partial news data never becomes
  `news_blocked=false` by default.
- **AC-05 coherent deterministic output:** all four observations are causal at one
  cutoff, feed/symbol identities match the configured archive, Decimal spread is
  exact, AI is false, and identical source evidence yields canonical evidence IDs.
- **AC-06 atomic and private handoff:** fault and race tests prove no partial file,
  symlink follow, insecure output, replacement-during-read acceptance or secret
  disclosure. A successful file validates with the SCN-021 worker model.
- **AC-07 truthful UI/API map:** the redacted status route and Signals connection
  node identify the policy writer and its three upstream source classes while
  preserving Demo-only, execution-ready false and Auto Trading false.
- **AC-08 regression and evidence limits:** targeted negative tests, full Python
  and web gates, source guards and secret scans pass. Static MQL/source fixtures do
  not count as compilation, actual MT5, news-calendar completeness, deployment or
  Demo-operation evidence.

## Evidence boundary

A passing SCN-023 proves local coherent handoff construction and synthetic MT5
wire compatibility. It does not prove a real news collector, MetaEditor
compilation, an actual terminal session, scheduled PA01 publication, hosted
Supabase access, strategy performance, execution readiness or release readiness.
