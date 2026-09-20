# SCN-031 redacted Demo readiness read model

## Task contract

Replace the dashboard's hard-coded release-blocker prose with one redacted API
read model that separates owner decisions, configured runtime integrations and
unrun target evidence. The read model is informational only: it cannot authorize
execution, release a halt, create a command or turn on Auto Trading.

## In scope

- One strict owner-private, non-secret decision record selected through
  `SOCHRON_DEMO_READINESS_CONFIG_FILE`.
- A public `GET /ui/demo-readiness` response with fixed gate identifiers, source
  classes, browser-facing routes and safe next-action codes.
- Runtime gate state derived from the existing Auth, telemetry, chart, history,
  executor, journal, policy, signal and statistics components.
- A responsive dashboard ledger that validates the entire API response and keeps
  all expected gates visible when the API is unavailable or invalid.
- Addition of the readiness route to the browser-safe connection map.

## Out of scope

- MT5 credentials, account references, tokens, passwords or secret provisioning.
- MetaEditor compilation, EA attachment, broker requests, hosted writes, target
  deployment or target-host fault injection.
- A positive release verdict. This increment has no target-evidence reader and
  therefore cannot emit `PASS`, `release_ready=true` or execution authorization.
- Editing risk limits, promoting a strategy or inferring that configuration is
  evidence of connectivity or broker behavior.

## Acceptance criteria

- **AC-01 Strict decision record:** the optional JSON file is an absolute
  canonical owner-owned regular file under an owner-private directory, is not a
  symlink, is bounded to 16 KiB and validates a versioned exact schema. It records
  broker/contract/operations decisions but contains no password, token, account
  reference or credential field. Missing configuration is a safe `missing` state;
  invalid configuration fails API startup with a redacted error.
- **AC-02 Fixed redacted contract:** `GET /ui/demo-readiness` is no-store and
  returns exactly the ordered gates `owner_decisions`, `owner_auth`,
  `market_data`, `execution_bridge`, `policy_research`, `target_artifact`,
  `broker_round_trip`, `recovery_observability` and
  `operational_authorization`. No configured value, filesystem path, identity,
  owner ID, account, server, URL, token or credential is returned.
- **AC-03 Safety invariants:** every response has `demo_only=true`,
  `auto_trading_enabled=false`, `release_ready=false`,
  `round_trip_authorized=false` and `unattended_demo_ready=false`, regardless of
  environment variables or component state.
- **AC-04 Evidence separation:** loading an owner decision record produces only
  `recorded`; loading component configuration produces only `configured` or
  `awaiting_source`; live component observations may produce `connected` or
  `degraded`. The target artifact, broker round trip and recovery gates remain
  `not_run`, and operational authorization remains `not_authorized` until a
  later, separately contracted evidence boundary exists.
- **AC-05 Truthful overall state:** the overall state is derived from gate state
  and can only be `awaiting_owner_inputs`, `awaiting_runtime`,
  `awaiting_target_evidence` or `degraded`. It is never a release assertion.
- **AC-06 Browser-safe location map:** `/ui/connections` includes the
  `/api/ui/demo-readiness` browser route and describes only redacted owner
  decisions, runtime gates and target-evidence classes.
- **AC-07 Strict UI projection:** the web client rejects unknown fields, missing
  or reordered gates, unsafe routes/sources, duplicate values and any true safety
  flag. On loading or failure, it renders the complete static gate inventory and
  never invents a successful state.
- **AC-08 Usable ledger:** the dashboard replaces the four hard-coded blocker
  lines with one full-width, keyboard-readable gate ledger showing state, API
  position/source and next action in Thai. It collapses to one column on mobile
  without hiding safety state.
- **AC-09 Parallel refresh:** health, connection-map and readiness requests start
  together, share the existing refresh action and ignore stale generations.
- **AC-10 Verification:** targeted API/UI tests cover unset, recorded, invalid,
  configured, connected/degraded, redaction, fallback and retry behavior. Full
  local package and browser regressions remain required before commit; MT5,
  hosted services and target evidence are reported `NOT RUN`.

## Evidence boundary

A passing SCN-031 check proves only that local code reports the configured and
observed states without promoting them into target evidence. It does not prove an
EA compiles, a Demo account is reachable, an order round trip works, broker-side
SL exists, alerts fire, a backup restores, or a VPS survives restart/network loss.
