# Sochron1k

Sochron1k is a demo-only XAU/USD research and automated-trading system. Its purpose is to measure whether explicitly versioned strategies have an edge after costs while preserving execution, risk, and audit invariants.

The repository now contains the first local SCN-001 safety core: versioned execution contracts, Demo-only preflight, deterministic risk sizing, a SQLite WAL journal, an isolated executor simulator, and targeted failure-path tests. It is still a prototype and is not ready for a real MT5 Demo send or unattended operation.

## Product boundaries

- One owner and one dedicated MT5 Demo account.
- XAU/USD only for the first release.
- Responsive web application for monitoring and control.
- MT5 and the EA remain authoritative for market, order, deal, and position state.
- Python services own strategy versions, feature calculation, queues, and the API.
- Supabase stores authenticated research history and audit records after synchronization.
- AI may classify news or support offline research. It cannot authorize risk, release a halt, or change a running strategy.
- Live trading, deposits, withdrawals, copy trading, signal sales, multi-account support, and Order Flow trading are outside the first-release scope.

## Safety baseline

The current project risk tier is **High assurance**. Demo-only operation reduces financial exposure but does not remove execution, credential, data-integrity, or automation risk.

- Live-account execution is prohibited.
- Auto trading defaults to disabled.
- Risk defaults are 0.25% per trade, 0.75% daily, and 2% per experiment.
- Only one position or pending order is permitted.
- Unknown write or execution outcomes must be reconciled before retry.
- The system must stop opening positions when price, journal, executor, or risk state is not trustworthy.

## Source documents

- `Sochron1k_Complete_Blueprint (1).pdf` is the product and engineering source of truth, version 1.1 dated 16 September 2026.
- `Agentic_Software_Engineering_Handbook_v3.docx` defines the project delivery and assurance process, version 3.0 dated 16 September 2026.
- [Project profile](docs/product.md) records the adopted scope, risk tier, unknowns, and decision authority.
- [Architecture](docs/architecture.md) records system boundaries, data ownership, and failure behavior.
- [SCN-001 Task Contract](docs/contracts/SCN-001-mt5-demo-round-trip.md) defines the first vertical slice, including the safe local console acceptance boundary.
- [Risk register](docs/risks/risk-register.md) tracks material project risks and required evidence.
- [Agent skills](docs/tooling/agent-skills.md) records the installed skills, source revisions, task routing, and verification limits.

## Verified project command

```bash
bash scripts/check-project-baseline.sh
python3 scripts/check-agent-skills.py
bash scripts/check-scn-001-local.sh
.venv/bin/python scripts/check-bridge-local.py
.venv/bin/python scripts/check-mt5-source.py
.venv/bin/python scripts/check-mt5-fixture.py
.venv/bin/python scripts/check-execution-protocol-source.py
.venv/bin/python scripts/check-execution-protocol-fixture.py --kind inventory
.venv/bin/python scripts/check-execution-protocol-fixture.py --kind outcome
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 .venv/bin/python scripts/check-owner-auth-local.py
env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs
npx -y -p node@24.21.0 npm run check:web
npx -y -p node@24.21.0 npm run check:db:static
npx -y -p node@24.21.0 npm run check:compose:static
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local
```

Only commands that have been run successfully in this repository should be added to this section or to `AGENTS.md`.

## Local development

The candidate runtimes are pinned to Python 3.14.7 and Node.js 24.21.0 LTS. Install uv 0.12.15, then create the Python environment from the committed lockfile:

```bash
uv python install 3.14.7
uv sync --all-groups --frozen
bash scripts/check-scn-001-local.sh
```

The API health endpoint always reports Demo mode and currently reports `execution_ready=false`.
An authenticated, disabled-by-default API-side execution polling adapter now exists,
and a pure source-only MQL5 command/inventory/outcome codec now fixes its wire
contract. No MQL5 mutation EA, compiled artifact or broker credential is present.
See the
[SCN-012 execution bridge runbook](docs/operations/execution-bridge.md).

Run the responsive monitoring console with the pinned Node.js release:

```bash
npx -y -p node@24.21.0 npm run dev --workspace @sochron1k/web
```

The console is deliberately monitoring-only. It shows the local API state, fixed risk policy, command lifecycle, and outstanding release gates without inventing broker values or exposing an order-entry control.

The owner workspace includes a Lightweight Charts candlestick panel with M1/M5/M15/H1,
exact OHLC inspection, forming/closed bars and explicit feed gaps/freshness. It stays
empty until owner telemetry and native chart data are available. The chart API/UI
have synthetic local evidence; the EA candle producer is a source-only checkpoint
awaiting compilation and actual terminal verification. See
[SCN-006](docs/contracts/SCN-006-market-chart.md) and the
[chart configuration runbook](docs/operations/local-mt5-bridge.md#native-chart-channel-scn-006).

Optional [durable closed-bar history (SCN-007)](docs/contracts/SCN-007-durable-bar-history.md)
now records validated native bars before chart acknowledgment and retains validation
baselines across API restarts. History reads are owner-authenticated and paginated
against an archive-scoped receipt watermark. It requires an explicitly configured
private local directory; unset means monitoring-only. Below the live chart, the
owner history workspace shows exact closed-bar values, receipt provenance and
gaps in 20-row pages. It can read the archive after API restart without a live
snapshot; only an explicit refresh advances the page set's watermark. This is not raw-tick capture,
Supabase history synchronization, a complete backtest dataset or Demo release evidence.

The optional [native M1 synchronization worker](docs/operations/native-m1-sync.md)
now has private configuration, a durable journal, bounded HTTP RPCs and explicit
init/status/run commands. It is disabled without configuration and is not started
by default API/web Compose. [Real local Supabase integration](docs/verification/SCN-008-local-sync.md)
now verifies Auth/owner isolation, exact values and recovery after a committed but
lost response. This is not target deployment or authority to enable a hosted destination.
The [internal Python artifact](docs/verification/SCN-008-worker-package.md) can now
be installed without source-relative PYTHONPATH and exposes `sochron-sync`.
It remains opt-in; a local worker container and the installed
[`sochron-recovery` operator](docs/operations/local-recovery.md) now have synthetic
verification. Recovery commands capture/verify three databases and create isolated
inspection bundles without enabling execution. Actual-target/off-host recovery,
external reconciliation and Demo release gates remain pending.

## Local Supabase foundation

The pinned Supabase CLI, local configuration, initial migration, and pgTAP authorization tests are committed. The browser role is read-only and owner-scoped; anonymous access and browser writes are denied. No hosted project is linked and no remote database has been changed.

Static verification does not need Docker:

```bash
npx -y -p node@24.21.0 npm run check:db:static
```

Full database verification requires a running Docker-compatible engine. Start the local stack, then reset and test it:

```bash
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh start
SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:db:local
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh stop
```

`check:db:local` resets the disposable local database before lint, advisors, and pgTAP; the acknowledgement explicitly permits loss of its local contents. Do not set it for a developer database containing valuable data. Startup uses a loopback-only network and suppresses generated keys; stop preserves volumes. See [local database operations](docs/operations/local-supabase.md) for prerequisites, security, and evidence limits. No hosted project is linked or pushed.

## Local container topology

`compose.yaml` builds the API and web console from pinned, digest-locked Python, Node.js, and nginx images. Both containers run non-root with read-only filesystems, dropped capabilities, and no privilege escalation. Only the web proxy binds to loopback; the API remains internal. Auto Trading is hard-disabled and no MT5 or worker container is implied.

Static verification does not need Docker:

```bash
npx -y -p node@24.21.0 npm run check:compose:static
```

The full verifier performs no-cache builds, starts the local stack, checks hardening and health through the proxy, recreates the API, confirms the journal volume identity, and shuts the containers down without deleting that volume:

```bash
npx -y -p node@24.21.0 npm run check:compose:local
```

This is local implementation evidence only. It is not VPS deployment, MT5 compatibility, recovery proof, or Demo readiness.

The dedicated local Colima runtime and its wrapper are documented in [the runtime runbook](docs/operations/local-runtime.md). Local arm64 container verification now passes; the web proxy has a separate loopback ingress network while the API stays internal. Each verifier run preserves its own named volume and evidence without stopping a developer stack.

## Current next action

The [owner-authenticated API](docs/operations/owner-authentication.md) now verifies
Supabase identity and active sessions, with local sign-in/logout and owner-isolation
evidence. Browser login/logout and private telemetry display are implemented with
component tests and a production-build browser verifier against real local Auth/API.
The Auth verifiers above require the local Supabase stack and both committed
migrations; they use only disposable synthetic users. The browser verifier also
needs the pinned Chromium headless runtime; see the owner-authentication runbook.
This is local fixture evidence, not actual MT5 connectivity or Demo release readiness.

The [read-only telemetry ingress](docs/operations/local-mt5-bridge.md) now has
authenticated API and real-loopback HTTP evidence; it defaults to disabled without
private local configuration. The owner web console now consumes its private view;
no actual EA connection is verified yet.
The [MQL5 sources](mt5/ea/README.md) contain the read-only observer and pure
execution-protocol codec as uncompiled checkpoints.
Compile/verify the native CopyRates producer against SCN-004/006,
verify actual Demo data, then implement and compile the default-off mutation EA
that consumes the SCN-012/013 contract and complete the remaining target recovery
work. A real Demo round trip still
requires owner inputs and explicit target authorization listed in the task contract.
