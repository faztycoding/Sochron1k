# SCN-037 bounded Demo round-trip admission

2026-09-20, High assurance, base
`1c55fbe0ada4e6c9a37ebbb72a3925dceec29a74`. This work remains inside the
Demo-only goal. It adds no live-account path, browser trading control, unattended
dispatcher, halt release or target authorization.

## Required outcome

Connect the existing durable `ExecutionService` to the existing authenticated
polling bridge through one separately authenticated, private API boundary that can
exercise one explicitly authorized Demo open/cancel/close lifecycle. The
authorization must bind one owner decision revision, Demo identity, experiment,
signal, strategy version and fixed command identifiers. It expires for new entry
but must not prevent risk-reducing cancel, close or query-only reconciliation.

The boundary is disabled without one owner-private configuration file. It never
accepts an account, experiment, signal, strategy or command identifier outside the
configured authorization. The browser ingress must continue to block `/api/internal/`
and the web UI remains read-only.

## Local acceptance

- **AC-01 Private opt-in and identity binding:** load one bounded private config
  with a separately generated service token, canonical private journal path,
  exact Demo identity, owner-decision revision, source revision, experiment
  baseline, minimum cost-per-lot floor and fixed entry/cancel/close identifiers. Reject shared credentials,
  mismatched telemetry/executor/owner decisions, unsafe files, duplicate command
  identifiers, invalid authorization order or an authorization window longer than
  24 hours. Missing config is inert.
- **AC-02 Create-only risk baseline:** initialize the active experiment baseline
  only from a fresh complete Demo executor inventory. The daily baseline is the
  observed MT5 equity and the experiment baseline is the owner-authorized value.
  Existing state is returned only when the immutable scope/baseline matches. Never
  overwrite a baseline, clear a halt, roll a Bangkok day or initialize while an
  account exposure exists.
- **AC-03 Explicit startup:** expose an authenticated startup action that calls the
  existing startup reconciliation with configured policy, experiment and executor
  identity. Missing/stale/foreign inventory, missing risk state, unresolved
  commands, changed generation or a non-Demo account sends nothing and returns a
  bounded failure code.
- **AC-04 One bounded entry:** admit only the configured command, signal and
  strategy while the entry authorization is current. Use server time, the
  configured policy, exact bridge inventory and the existing deterministic risk
  calculation. The caller may supply typed contract/market/risk observations, but
  MT5 still rechecks contract, price, `OrderCalcProfit`, cost/risk authorization,
  margin, `OrderCheck` and one `OrderSend`. Journal reservation and dispatch
  authorization must predate exposure to the polling bridge.
- **AC-05 Risk-reducing management:** admit only the configured cancel or close
  command bound to the configured entry. Derive managed volume and broker
  identifiers from journal evidence through `ExecutionService`; never accept those
  values from the request. Entry expiry or a latched risk halt cannot disable
  cancel, close or query-only reconciliation.
- **AC-06 Unknown and replay behavior:** a timeout or ambiguous result remains
  `UNKNOWN`; reconciliation queries the bridge evidence and never resends. Replays
  with the exact idempotency scope return durable state. Changed payloads or reused
  configured identifiers conflict before another external send.
- **AC-07 API and browser isolation:** all mutation/reconciliation routes require
  the separate bearer token and are synchronous `def` handlers because executor
  waits are blocking. Invalid bodies use strict response/request models. The nginx
  browser ingress continues to return 404 for `/api/internal/`; owner/public routes
  gain no mutation control.
- **AC-08 Truthful UI positions:** the redacted connection map and Demo-readiness
  execution row include `/api/internal/v1/demo-round-trip/status` and the bounded
  admission source. Missing, armed, expired and degraded runtime state must affect
  that row without changing the hard-coded false values for execution readiness,
  Auto Trading, release readiness, round-trip authorization or unattended readiness.
- **AC-09 Negative and recovery verification:** cover missing/duplicate/wrong
  credentials, config and identity mismatch, expired entry, wrong IDs/signal/
  strategy, baseline replay/mismatch, stale inventory, journal failure before send,
  duplicate entry, timeout to UNKNOWN, query-only recovery, halt-preserving close,
  source guards, full Python/web/Linux/container regressions and browser-ingress
  isolation. Actual MT5 compilation, broker mutation and target recovery remain
  NOT RUN until separately authorized.

## Evidence limits

A passing local SCN-037 proves only the bounded API-to-simulator/polling-transport
mechanics and truthful UI mapping. It does not prove MetaEditor compilation,
selected-broker behavior, a Demo fill, broker-side SL, target recovery, alert
receipt, multi-day burn-in, release readiness or permission for unattended Demo
operation. Those require actual target evidence and separate owner authorization.
