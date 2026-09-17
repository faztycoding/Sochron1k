# SCN-006 local chart API and browser checkpoint

2026-09-17. Candidate based on `71ac86aff734a37798e5ba641854bce426d7a67f`;
new work is dirty relative to that revision. macOS arm64, Python 3.14.7,
Node 24.21.0, Playwright 1.63.0 and Chromium 153.0.8010.12. No MT5 operation,
hosted change, deployment or execution enablement occurred.

## Changed boundaries

Native-bar contract and separate bounded, authenticated API ingress/owner read;
fixed-offset validity interval; disposable per-timeframe cache; exact decimal
validation; chart sequence/boot fence; immutable closed-bar handling; monotonic
freshness. Shared JSON parsing preserves the existing telemetry 16 KiB bound.

React owner workspace adds Lightweight Charts 5.2.1 (fancy-canvas 2.1.0), both
exact-pinned in the lockfile, with distributed license copies and attribution.
The existing login/session authority is reused, not bypassed. Chart requests use
a separate 256 KiB response allowance; telemetry retains its 64 KiB client limit.
Charts never own execution truth, generate missing bars, or become strategy inputs.

The frontend-design skill preserved blueprint Charcoal Gold/Sarabun/Inter and made
the full-width chart the market workspace. React guidance informed conditional
library loading, stable polling dependencies and cached numeric-display validation.
Playwright and Supabase guidance informed isolated local users, production-browser
checks, cleanup and avoiding persistent credentials. No DB migration was needed.

## Observed verification

- `.venv/bin/pytest -q`: **221 PASS**, including 68 chart cases and existing
  telemetry, authorization, deterministic risk/journal and simulator regressions.
- `.venv/bin/python scripts/check-bridge-local.py`: **PASS**, real loopback Uvicorn
  with a 240-bar input larger than the original telemetry limit, private chart
  configuration, anonymous denial, separate challenge/sequence, idempotent replay,
  closed-bar correction rejection and unchanged execution/telemetry policy.
- `npx -y -p node@24.21.0 npm run check:web`: **PASS**, typecheck, **73 tests**,
  production build and client-bundle scan. New tests cover all four periods,
  exact decimals/scientific notation, tick grid/OHLC/time/identity/closure/gaps,
  oversized responses, unsafe canvas precision fallback, token/timeframe races,
  unauthorized reads, network recovery, local freshness expiry and canvas disposal.
- `env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs`:
  **PASS** through real local Supabase Auth/RPC, FastAPI and the production build.
  Foreign-user chart denial; keyboard M1/M5/M15/H1 selection; actual canvas creation;
  closed/forming labels; exact displayed OHLC matched to API values; visible gaps;
  1440px desktop and 390px mobile with no page overflow; quote staleness and recovery;
  chart network failure clearing values; 15-second chart expiry while telemetry
  stays fresh; SDK refresh; logout/revoked chart read; memory-session loss on reload.
  Browser runtime errors zero. Cleanup PASS verifies the two generated users are
  absent and removes only its own private configs/processes. Developer servers
  were not stopped. Local Supabase volumes are preserved when stopping the stack.
- Production dependency signature audit: **16 signatures / 13 attestations PASS**.
  This does not establish an attestation for every package or a vulnerability-free
  future deployment. Whole-tree signature status is tracked separately below.
- Final `bash scripts/check-scn-001-local.sh`: Ruff, 221 tests and 143-file source
  secret scan PASS after stopping local Supabase. `bash scripts/check-project-baseline.sh`,
  `python3 scripts/check-agent-skills.py`, `npm run check:compose:static` on pinned
  Node, `git diff --check` and Node verifier syntax check PASS. Installed/repository
  skill integrity passes; that alone does not prove runtime integration.
- `npm audit`: zero known vulnerabilities at verification time. Whole-tree
  `npm audit signatures`: **FAIL**, registry 404 for `whatwg-url@17.1.1` again.
  The failure remains unresolved, not a PASS or approved release exception.

Latest candidate browser artifacts:
`output/playwright/scn005-a246e69a-bdb4-4d12-bd08-06bf5cc62641/`.
The existing SCN-005 verifier now covers SCN-006 too; the output prefix remains for
compatibility. `result.json` retains revision/dirty state, source hashes, image IDs,
fixture, checks, cleanup and actual runtimes. Artifact build SHA-256:
`d9b46d2a6ad962cddaef2fa6c09627b7bf6d2c953bd4b78b481869400eb8cd60`.
Verifier SHA-256: `950b4f066071731d27d8438727df46a9c0c4a21e6cc524ab1256098e514a5474`.
Artifacts are ignored local evidence, not published data or broker observations.
Desktop/mobile synthetic screenshots were visually inspected: controls and values
fit, forming candles are gold, gaps are identified, and Auto Trading stays off.

## Failures encountered, not silently accepted

- Typecheck initially found an untyped chart time formatter, a narrowed-field
  arithmetic issue and unsupported Testing Library `exact` options; corrected.
  The first browser run stopped at that failed build before creating fixture users.
- Near-deadline fake-timer test initially failed because the DOM performance clock
  did not advance with the timer driver. The fixture now explicitly controls its
  monotonic clock; the 20ms deadline assertion remains. Real-browser 5/15-second
  expiry checks also pass. No production timeout or freshness threshold was raised.
- A Compose static check while local Supabase was running correctly detected its
  generated private runtime secrets under `.temp/start-secrets`. The stack is stopped
  before the final scan; those files are never staged or exempted from scanning.
- Prior whole-tree signature verification failed on a registry attestation 404 for
  existing `whatwg-url@17.1.1`; do not infer success from production-only verification.

## Acceptance and remaining full product work

AC-01–05: locally verified API behaviors, **not** actual MT5 data agreement.
AC-06: EA CopyRates producer now exists as the source checkpoint recorded below;
compilation and terminal checks NOT RUN.
AC-07: local browser implementation/integration verified with synthetic bars.
AC-08: local revision/artifact evidence available; actual broker comparison NOT RUN.
SCN-006 overall PARTIAL. Demo release NOT READY. Auto Trading remains disabled.

Remaining: EA compiler/runtime verification, actual Demo/timezone comparison, durable raw ticks
and M1 history, indicators/signals/strategy evaluation/statistics, execution/SL and
recovery gates, authorized Demo round trip, target operations/alerts/restore/burn-in.
Owner inputs still needed: broker/Demo server, MT5 host/OS/build, currency/capital,
symbol/margin mode and offset evidence, owner Supabase target, then deployment/API
budget/alert decisions as their tasks become applicable. Never request passwords
or privileged keys in chat. These inputs do not prevent further local implementation.

References: [Lightweight Charts 5.2 documentation](https://tradingview.github.io/lightweight-charts/docs),
[v5.2.1 notice](https://github.com/tradingview/lightweight-charts/blob/v5.2.1/NOTICE),
[CopyRates](https://www.mql5.com/en/docs/series/copyrates).

## EA native-bar source checkpoint — 2026-09-17

Candidate based on `0537b11b09bfb0dbeef0ad04255b1653d0b5b10e`, dirty during
verification; macOS arm64 and Python 3.14.7. This section supersedes only the
previous missing-producer status, not its unpassed terminal/release gates.

Changes: observer 0.11 adds a separately default-off CopyRates chart channel,
fixed-size windows, synchronized-series/rollover checks, explicit Bid/Last basis,
Demo identity checks before/after collection and before requests, and separate
boot/sequence handling. Quote and chart requests alternate with a one-request
timer guard. A validation rejection latches the chart channel for review; a
transient unconfirmed response backs off without replaying the old sample.
An observed history call over 250ms latches charts, but cannot interrupt CopyRates.
No trade operation, API production change, UI change, dependency or DB migration
is included. The `sochron-mt5-execution` skill informed identity checks, transport
separation and the explicit distinction between source and terminal evidence.

Verification on this candidate:

- `bash scripts/check-scn-001-local.sh`: **PASS**, Ruff, **229 Python tests** and
  a 145-text-file secret scan. This covers existing local risk/recovery/authorization
  regressions, not actual executor behavior.
- `.venv/bin/pytest -q tests/test_mt5_source.py`: **23 PASS**. Added cases cover
  default-off mutation detection, forbidden terminal access in pure helpers,
  golden decimal/time/provenance validation, body limits and ASGI chart ingestion.
  The synthetic two-bar input becomes one closed and one forming bar; exact replay
  is idempotent and a closed-bar correction rejects charts without disabling quotes.
- `.venv/bin/ruff check scripts/check-mt5-source.py scripts/check-mt5-fixture.py tests/test_mt5_source.py`:
  **PASS**.
- `.venv/bin/python scripts/check-mt5-source.py`: **PASS, static patterns only**.
  It is not a compiler, MQL interpreter, control-flow proof or security boundary.
- `.venv/bin/python scripts/check-mt5-fixture.py` and the same command with
  `--chart`: **PASS** against committed hand-authored golden inputs. Both report
  `input_is_committed_golden=true`; neither claims an MT5-generated fixture.
- `.venv/bin/python scripts/check-bridge-local.py`: **PASS**, synthetic telemetry
  and 240-bar windows through a real loopback HTTP server. This confirms the
  receiving boundary still works, not that the MQL producer executed.
- `bash scripts/check-project-baseline.sh`, `python3 scripts/check-agent-skills.py`
  and `git diff --check`: **PASS**. All pinned installed/repository skill copies
  pass integrity checks; runtime integration is a different gate.

Candidate SHA-256 identities:

| Artifact | SHA-256 |
| --- | --- |
| `mt5/ea/SochronTelemetry.mq5` | `ff9b30728a3b08b000beeba19569f54ba786f0517244e27707e0175506a6e637` |
| `mt5/ea/TelemetryProtocol.mqh` | `9ba311a783840bae27c2937e0e3223d0145075009fe56c029713c5e062b07118` |
| `mt5/ea/SochronTelemetrySelfTest.mq5` | `452dddaf3534c847079da4b284c868581bd03ff6679275249105cf390f323a41` |
| `tests/fixtures/mt5-chart-v1.json` | `5b5affb45f3f0a033aa76d31f90a40f47a8e59dfdbeff5d00288eefc087f708f` |

Compiler discovery again found no matching MetaEditor/terminal executable in
Spotlight's filename index or `/Applications` and the user's `Applications`
directory. This is not an exhaustive search of custom/unindexed Wine prefixes.
No target host/build has been selected. **MQL compilation, the 50-case pure MQL
self-test, terminal-generated fixture comparison, actual Demo OHLC/clock agreement,
rollover, account-switch and network/timing tests are all NOT RUN.** The 50 cases
are source cases, not part of the 229 executed Python tests.

Browser/Compose checks and dependency audits were not rerun for this source-only
increment; the earlier chart browser evidence applies to the unchanged API/UI
boundary, not the EA. The prior whole-tree signature failure remains unresolved.
No MT5 login, broker operation, hosted write, deployment or Auto Trading enablement
occurred. SCN-006 remains PARTIAL; the full Demo product is NOT READY. The selected
host must follow the compile/self-test and read-only authorization procedure in
[`mt5/ea/README.md`](../../mt5/ea/README.md) before terminal integration.
