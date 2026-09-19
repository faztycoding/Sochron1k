# ADR-020: Owner research statistics read model

- Status: Accepted for local Demo implementation
- Date: 2026-09-20

## Context

The UI needs statistics, but a browser-side calculation over partial signal or
execution data would hide dataset, split, cost and uncertainty boundaries. The
existing `evaluations` relation is the synchronized research-evidence boundary and
already has owner RLS plus foreign keys to strategy versions and experiments. Its
JSON fields intentionally support future metrics, so a public projection still
needs a narrow versioned contract before it can display them safely.

## Decision

FastAPI exposes a read-only `/owner/statistics` projection backed by one bounded
owner-token PostgREST read of `evaluations`, embedded strategy evidence and an
optional experiment. The reader uses the existing publishable/anon key and exact
verified bearer; it never uses a service-role credential.

Only the SCN-017 metric and cost schema is accepted. Unknown, incomplete,
non-finite, internally inconsistent, cross-owner, non-causal or out-of-order rows
fail closed. Win rate is derived from validated outcome counts. The API exposes no
numeric database keys, owner IDs, raw JSON, write method or promotion decision.
Empty evidence is `awaiting_source`.

The browser renders each evaluation separately with strategy version, split,
dataset/code hashes, sample size, expectancy interval, drawdown and all cost
assumptions. Training results are marked in-sample. It does not aggregate unlike
splits, infer a strategy edge or offer promotion/execution controls.

## Consequences

- Research producers have a precise minimum evaluation schema to publish.
- Owner RLS remains the confidentiality boundary and FastAPI independently checks
  nested owner and temporal evidence.
- A malformed recent evaluation intentionally degrades the whole projection rather
  than silently presenting a trustworthy-looking subset.
- This read model does not prove the producer, temporal split, costs, dataset or
  strategy result. Reproducible research validation remains a separate gate.
