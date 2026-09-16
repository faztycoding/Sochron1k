# ADR-004 Read-only telemetry before execution

Status: adopted for the local prototype; 2026-09-17.

SCN-001 requires real MT5 evidence but currently only has an isolated simulator.
Introduce an authenticated, versioned sampled-snapshot ingress independently of
execution. The API pins the expected identity and owns receipt timestamps. A boot
challenge and increasing sequence numbers reject stale-lifetime and reordered
messages. Duplicate messages cannot refresh data age.

Keep only the latest observation in memory, protected by a process-local lock.
This intentionally supports one API process, not distributed ownership or
execution fencing. The health endpoint cannot promote telemetry to trade
readiness. Do not connect this cache directly to the command service.

MQL5 tick timestamps are retained verbatim; normalization requires an explicit
verified broker UTC offset. UTC observation and receipt times remain separate.
Server-offset/DST drift fails closed rather than silently shifting history.

The executor uses a separate, locally provisioned, read/write-telemetry credential.
Anonymous status omits prices, balance/equity and all identity fields. Owner data
access awaits application Auth. Private configuration is never a Vite variable.

Alternatives: a public unauthenticated push would allow fabricated broker truth;
sharing a browser session would collapse the executor boundary; durable storage
for the latest heartbeat would add recovery semantics it cannot establish.
Persistent tick/history and execution journals remain required later.

Official reference semantics were checked on 2026-09-17:
[account properties](https://www.mql5.com/en/docs/constants/environment_state/accountinformation),
[tick structure](https://www.mql5.com/en/docs/constants/structures/mqltick),
[TimeGMT](https://www.mql5.com/en/docs/dateandtime/timegmt),
[WebRequest](https://www.mql5.com/en/docs/network/webrequest).
These references do not establish a terminal build or demonstrate broker behavior.
