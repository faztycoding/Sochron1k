# SCN-014 UI and API connection map

2026-09-20, High assurance, base
`2a3a6c6a02ef4a907d5aaf1075ece63753c2ca09`. Local implementation under the
full Demo objective. It does not authorize MT5, hosted writes, deployment or Auto
Trading.

## Required outcome

Show the owner exactly which backend boundary supplies each visible UI area, which
browser-safe API routes exist, which upstream source is still required and why a
section is incomplete. Status must come from one redacted API read model rather
than from invented broker values or optimistic client-only labels.

Preserve the existing Charcoal Gold, Sarabun/Inter and Demo-only design. Add one
compact connection rail immediately below the safety banner. Its visual grammar is
`UI surface -> browser API -> authoritative source -> status`, not a collection of
generic dashboard cards. Desktop uses aligned columns; narrow screens preserve the
same reading order in one stack.

## Local acceptance

- AC-01: `GET /ui/connections` returns a typed, no-store, public redacted map with
  fixed IDs for core API, owner Auth, MT5 telemetry, native chart, closed-bar
  history, execution evidence, signals and statistics. It always asserts Demo only,
  Auto Trading false and execution readiness false.
- AC-02: Every node separates implementation state (`available`, `partial` or
  `missing`) from runtime state. Runtime is derived only from loaded configuration
  and existing redacted bridge/cache state; no account reference, broker value,
  owner ID, URL, public key, token, command ID or filesystem path is returned.
- AC-03: The execution node identifies the existing redacted transport status and
  the missing authenticated owner execution read model. Signals and statistics are
  explicitly missing rather than shown as empty or disabled data.
- AC-04: The browser strictly validates the complete response, known IDs, unique
  nodes, route shape, enum values, source identifiers and all three safe flags.
  Malformed or unsafe responses display a redacted unavailable state.
- AC-05: The connection rail names what each source will populate and shows exact
  browser-facing routes. It remains useful when the API is loading/offline and
  includes no order-entry control.
- AC-06: Desktop and mobile layouts remain readable, keyboard focus remains
  visible, status is not conveyed by color alone and reduced-motion behavior is
  unchanged.
- AC-07: Unit/API/component tests cover disabled and configured runtime maps,
  malformed/unsafe client data, API retry, exact missing routes and Demo/Auto-off
  invariants. The production web build and bundle secret scan pass.
- AC-08: Retain exact commands, revision and evidence limits. Synthetic local
  configuration is not MT5, hosted Supabase, strategy, statistics or deployment
  evidence.

## Exclusions and next boundary

This increment does not create signal/statistics/execution-history data, expose an
executor token to the browser, add a trade button or make a source connected. The
map is the truthful integration checklist for those next APIs. The separate
default-off MQL5 mutation EA remains the next execution work unit.

## Required verification

Run focused API and React tests, typecheck/build, the project web gate, full local
safety gate, baseline, skill integrity, secret scan and desktop/mobile browser
inspection. A screenshot can verify layout only; it cannot prove an upstream source.
