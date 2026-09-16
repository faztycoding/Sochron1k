# ADR 001 Demo First Modular Boundaries

## Status

Accepted from blueprint v1.1 for the first release. Review when the first integration spike produces evidence or when the execution host changes.

## Context

Sochron1k needs low-latency position protection, durable command evidence, asynchronous news and synchronization work, a responsive UI, and reproducible research. The first release serves one owner and one MT5 Demo account. The execution environment may use MT5 under Wine on a Linux VPS, but that assumption is not yet verified.

## Decision

- Use a modular monorepo with `apps/web`, `services/api`, `services/worker`, `mt5/ea`, `research`, `supabase/migrations`, `tests`, and `scripts` boundaries.
- Keep the MT5 EA and executor path authoritative for broker execution and broker-side SL state.
- Keep the tick and risk-management loop independent of Supabase, news, and AI latency.
- Journal command intent locally before external send and synchronize asynchronously.
- Use Supabase for authenticated synchronized history, not raw tick storage or privileged MT5 credentials.
- Keep AI advisory and schema-bounded. Deterministic code and the EA enforce risk and execution policy.
- Operate Demo only. A live-trading path is not a dormant feature; it is excluded from this release.

## Alternatives considered

### Send every tick through Supabase

Rejected because database latency, quota, and outages would couple UI storage to the risk loop and create unnecessary cost and failure modes.

### Let the Python service own all position protection

Rejected because network and service failure could leave an open position without local executor safeguards.

### Use AI to choose or modify risk dynamically

Rejected because model output is probabilistic, untrusted input may influence it, and it cannot be the authority for risk or halt release.

### Start with multiple independent services

Rejected until measurable scale, ownership, isolation, or availability needs justify the operational cost.

## Consequences

- Adapter contracts and reconciliation logic become first-class work.
- The system must support durable local state and eventual synchronization.
- Research and runtime versions must be explicit and independently promotable.
- The UI may show pending, stale, or unknown states rather than optimistic success.
- Hostinger MT5 under Wine remains an integration risk. If it fails, the MT5 executor may move to Windows while the API contract remains stable.

## Fitness checks

- MT5 credentials and privileged Supabase keys never enter the web bundle.
- AI and research modules have no code path that releases a halt or sends an MT5 command directly.
- Every external command has a prior durable journal record and an idempotency key.
- The executor denies live and mismatched account identities.
- Supabase outage does not block management of an existing position.
- A restart test proves reconciliation before new work is accepted.

## Review triggers

- Wine or broker integration fails the defined stability gate.
- More than one account, owner, symbol, or execution host enters scope.
- Measured throughput or availability requires another deployment boundary.
- A new data provider or Order Flow feed changes licensing, storage, or trust boundaries.
- Live trading is proposed; that requires a separate project and risk decision rather than an edit to this ADR.
