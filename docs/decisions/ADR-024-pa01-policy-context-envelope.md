# ADR-024: policy-context-complete PA01 evidence envelope

- Status: Accepted as a local producer/receiver contract
- Date: 2026-09-20

## Context

SCN-018 through SCN-020 provide a pure PA01 kernel, deterministic native M1
aggregation and atomic snapshot/signal persistence. The receiver's first protocol
stored market features and the resulting action/reason, but not the exact spread,
market-open, stale-price, news-pause, exposure and pending-order inputs used by the
kernel. A BLOCK or WAIT row therefore could not be reproduced from its immutable
snapshot alone.

Adding those values only to an application log would not meet the Blueprint's
immutable decision-evidence requirement. Replacing protocol v1 would also make
already persisted synthetic evidence ambiguous and break forward compatibility.

## Decision

Add `sochron_worker.pa01_envelope` as a pure boundary. It accepts one revalidated
`native-pa01-aggregation-v1` result, a strict policy-evidence object at the same UTC
cutoff and a registered code hash. It recomputes the aggregation hash, reruns PA01
and constructs the receiver payload itself; a caller cannot submit an independent
action or feature set.

Policy evidence contains the exact kernel values plus quote, market-session, news
and account-state observation IDs/times. A canonical context hash produces one
stable policy evidence ID. The decision fingerprint covers code, aggregation,
policy context and the recomputed kernel output. Stored signal/snapshot IDs derive
from that full fingerprint. Overall confirmation is the explicit policy cutoff;
the earlier market-data cutoff and kernel decision ID remain in context evidence.

Extend the existing receiver with protocol v2. `feature_snapshots` gains optional
`decision_protocol` and `policy_context` fields guarded by strict insert validation.
The context remains separate from the protocol-v1 feature JSON so existing rows
and the established feature validator do not need rewriting. The signal must link
the stable context evidence ID. Existing producer immutability triggers continue
to own UPDATE/DELETE denial.

The same backend-only store/read functions accept both protocol versions. V1 rows
retain null context and read back as v1; v2 rows return the exact context. Anonymous
and authenticated roles remain denied. Store/reconcile semantics, one-to-one owner
links and named conflict behavior remain unchanged.

## Rejected alternatives

- **Infer context from action/reason:** rejected because several different input
  states can produce the same dominant reason and later source state is not the
  state used at decision time.
- **Put context only in logs:** rejected because logs are not the linked immutable
  decision snapshot and can have different retention or availability.
- **Silently widen feature schema v1:** rejected because the same schema identifier
  would describe two different required shapes.
- **Replace or backfill protocol-v1 rows:** rejected because historical evidence
  must not be rewritten or populated with facts that were never captured.
- **Acquire source state inside PostgreSQL:** rejected because native quote/session,
  news and account observations have separate trust and availability boundaries;
  this increment validates their envelope but does not invent them.

## Consequences

- Synthetic v2 decisions can be reproduced from the persisted market and policy
  inputs, and changed context changes the decision fingerprint.
- Protocol-v1 evidence remains valid but explicitly lacks policy context; it is not
  upgraded by inference.
- The next source-side boundary still needs bounded native/context readers, a local
  durable journal, HTTP store/read transport and scheduling. Until that producer is
  configured and run, `/api/owner/signals` correctly remains `awaiting_source`.
- This decision creates no command, risk admission, broker call, strategy promotion
  or Auto Trading authority.
