# SCN-021 reproducible PA01 evidence envelope

## Task contract

Add the deterministic producer-side boundary that combines one verified native
M1 aggregation, the complete PA01 policy context observed at an explicit UTC
cutoff, and the pure PA01 decision into the exact payload accepted by the atomic
Supabase receiver. Persist the policy context beside the immutable feature
snapshot so BUY, SELL, WAIT and BLOCK decisions can be reproduced rather than
inferred from the outcome alone.

This increment defines and verifies the payload. It does not read the native
archive, acquire live policy state, schedule work, send HTTP, maintain the durable
producer journal, create a command, size risk, call MT5, deploy or enable Auto
Trading.

## Evidence-envelope rules

- Input is exactly one `native-pa01-aggregation-v1` result, one bounded policy
  observation set and one lowercase 64-character registered strategy code hash.
  The aggregation cutoff, policy cutoff, symbol and feed identity must agree.
- The envelope recomputes the aggregation hash and reruns `evaluate_pa01`; callers
  cannot supply or alter the decision, features, action, reason or timing.
- Policy evidence records the exact spread and market-open, stale-price,
  news-pause, exposure and pending-order booleans used by the kernel. Quote,
  market-session, news and account-state observations each preserve a source
  evidence ID and UTC observation time at or before the decision cutoff.
- A canonical policy-context hash covers all policy values and observations. Its
  stable evidence ID is included in the signal evidence set. The producer decision
  fingerprint covers the code hash, aggregation provenance, policy context and
  recomputed kernel decision.
- The stored signal/snapshot IDs derive from that full fingerprint. The kernel's
  original decision ID and market-data cutoff remain inside the policy-context
  evidence for replay. The stored confirmed/available time is the explicit overall
  cutoff and expiry is exactly 30 seconds later.
- Receiver protocol v2 adds the policy context as a separate immutable snapshot
  field. Existing protocol-v1 producer rows and legacy rows remain readable and
  unchanged; v2 context is required, strictly bounded and returned by independent
  read-back.

## In scope

- Strict Pydantic policy-observation and receiver-envelope models.
- Deterministic canonical Decimal/UTC serialization, hashes and IDs.
- Aggregation-integrity revalidation plus exact PA01 recomputation.
- Forward Supabase migration for protocol-v2 policy context and compatible
  store/read reconciliation.
- Negative tests for forged aggregation, mixed identity, future policy evidence,
  changed context, malformed receiver payloads, authorization and immutable replay.

## Out of scope

- Native SQLite or Supabase source reads, market-calendar/news/account adapters,
  clock-driven scheduling, local producer journal, HTTP transport and retry loop.
- Research backtests, labels, statistics, strategy promotion or claims of an edge.
- Risk admission, command creation, MT5 execution, hosted writes, deployment or a
  live-account path.

## Acceptance criteria

- **AC-01 exact context:** spread and every decision blocker are stored with four
  bounded source observations, aware UTC times and a deterministic context hash;
  missing, duplicate, future or mixed-identity evidence fails closed.
- **AC-02 recomputed decision:** the builder revalidates the aggregation hash and
  reruns PA01. Its action, reason, features and kernel identity exactly match the
  admitted inputs and cannot be caller-forged.
- **AC-03 deterministic envelope:** identical evidence and code hash produce
  byte-identical protocol-v2 payload, fingerprint and IDs. Any policy, source,
  aggregation or code change alters the fingerprint.
- **AC-04 causal times:** formed time comes from the closed M5 bar; market evidence
  and policy observations are available no later than the explicit cutoff; stored
  confirmation equals that cutoff and expiry is exactly 30 seconds later.
- **AC-05 compatible persistence:** fresh and forward migrations retain protocol-v1
  behavior while v2 atomically stores and reads the exact immutable policy context.
  Exact replay is singular and a changed replay conflicts without a partial row.
- **AC-06 authorization and immutability:** browser roles cannot invoke producer
  RPCs or mutate evidence; service credentials remain backend-only; producer v1/v2
  rows cannot be updated or deleted.
- **AC-07 no authority expansion:** static and behavioral checks prove the envelope
  and receiver create no command/risk/order rows, contact no broker and leave Auto
  Trading disabled.
- **AC-08 regression gates:** targeted Python/pgTAP checks, full local suites,
  installed worker artifact, affected container and owner signal UI/API regression
  checks pass without weakening prior assertions.

## Evidence boundary

A passing SCN-021 proves deterministic construction and local persistence of a
complete synthetic PA01 decision envelope. It does not prove policy-source truth,
scheduled producer uptime, HTTPS/hosted durability, broker-feed parity, strategy
performance, Demo execution or release readiness. The UI remains
`awaiting_source` until the separate durable producer is configured and run.
