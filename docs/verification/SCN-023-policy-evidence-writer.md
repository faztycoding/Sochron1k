# SCN-023 coherent policy-evidence writer verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`0dd4461529727703e6703648c5e2762316c32fc2`. The delivery report binds the final
commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-023-coherent-policy-evidence-writer.md) pass for
the local Python coordinator, strict news-gate handoff, synthetic telemetry v2
wire and static MQL source. No news collector, MetaEditor compilation, terminal
self-test, actual MT5 connection, hosted write, broker operation, deployment or
Auto Trading change was performed.

## Implemented scope

- Added telemetry protocol v2 with exact MT5 symbol-session evidence while keeping
  v1 monitor compatibility. The read-only MQL source checks symbol trade mode and
  current/overnight broker sessions and suppresses ambiguous observations.
- Added a fresh, already-fenced execution inventory projection for policy use.
  Exposure and pending state include cumulative open/remaining volume and current
  local dispatch occupancy; incomplete, foreign or stale inventory remains denied.
- Added a strict owner-private `sochron.news-gate.v1` coverage/revision contract.
  Missing, stale, incomplete, malformed or insecure input never becomes a clear
  news window.
- Added a disabled-by-default API coordinator that binds all sources at one cutoff,
  derives canonical evidence IDs and atomically publishes the exact SCN-021 policy
  model to the configured SCN-022 handoff path.
- Added redacted `/policy/v1/status` and placed it before `/owner/signals` in the UI
  connection rail. All public flags retain Demo-only, execution-ready false and
  Auto Trading false.

## Acceptance evidence

- **AC-01:** config tests cover unset/exact-disabled, canonical private enabled
  config, insecure mode, symlink and mixed bridge identity. Startup remains inert
  without configuration.
- **AC-02:** model tests admit v1 monitoring but require both exact v2 market fields
  together. The committed v2 synthetic fixture validates against the API, and the
  MQL source guard keeps terminal session access out of the pure protocol helper.
- **AC-03:** tests derive exposure/pending from partial inventory volume and reject
  any bridge state that is not already fresh, complete, Demo-bound and foreign-free.
- **AC-04:** missing and stale news are `awaiting_sources`; malformed private news
  is `degraded`; none publishes a clear policy. Blocked evidence requires a unique
  explicit event ID.
- **AC-05:** the successful output preserves exact Decimal spread, archive feed,
  symbol, four unique derived IDs and causal times, and is read successfully by
  the existing worker `PolicyFileSource`/SCN-021 model.
- **AC-06:** a forced atomic-replace failure retains the previous complete file and
  removes only the writer-owned temporary inode. Existing symlink output is denied.
- **AC-07:** HTTP tests prove background refresh, no-store redacted status and exact
  UI route/source placement without any private identity, path, quote or token.
- **AC-08:** targeted, full Python, web, artifact, static database/Compose, baseline,
  skill-integrity, source-guard and secret checks pass. MQL and target evidence are
  reported separately below.

## Verification run

- Targeted Ruff and SCN-023/telemetry/MT5/API tests: **123 passed**.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **893 tests passed** in 39.61s
  and repository secret scan PASS; later static gates repeated the scan
  successfully after documentation updates.
- `npx -y -p node@24.21.0 npm run check:web`: TypeScript PASS, **180 tests passed**,
  production Vite build and browser-bundle secret scan PASS.
- `scripts/check-worker-package.py`: exact wheel/sdist, isolated installed artifact,
  disabled PA01 command and recovery/startup regressions PASS using a temporary
  isolated uv 0.12.15 executable. Evidence:
  `output/worker-package/bef15f440f3c45b0b9e3004bb6f88b47/result.json`.
- `scripts/check-mt5-fixture.py`: telemetry-v2 synthetic golden/API model PASS;
  this explicitly does not attest MQL execution or an MT5 account.
- `scripts/check-mt5-source.py`: static source guard PASS with compilation,
  MQL self-test and broker operation all reported **NOT RUN**.
- Project baseline, installed/repository skill integrity, static database/Compose,
  repository secret scan and `git diff --check`: PASS.
- Candidate Linux/container checks: **NOT RUN** because no Docker-compatible engine
  was available. This is not a PASS and no target-platform claim is made.

The first installed-package attempt stopped before building because uv 0.12.15 was
not installed on PATH. A temporary isolated pinned uv was then used and the full
verifier passed; no global tool or project dependency was changed.

## Evidence limits and next boundary

This proves local coherent policy construction, atomic handoff and synthetic v2
wire compatibility. It does not prove that the MQL source compiles, that a broker's
session table matches the algorithm, that a news calendar is complete, or that any
target service stays scheduled and recoverable. The next source boundary is a
bounded news-calendar collector that records official URL, publication/receipt
times, content hash and revision and produces this gate without treating RSS
absence as complete protection. Actual MT5 compile/read parity and target private
configuration remain independent gates.
