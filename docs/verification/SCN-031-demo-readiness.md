# SCN-031 Demo readiness ledger verification

## Candidate

- Source revision before commit: `c6eeb20235a3e28f9cba154ec77415f688875691`
- Candidate state during verification: dirty working tree containing only the
  scoped readiness API/UI, browser verifier and documentation changes
- Environment: macOS arm64, Python 3.14.7, Node.js 24.21.0, uv 0.12.15,
  Supabase CLI 2.117.0 and Chromium 153.0.8010.12; disposable worker verification
  used the repository's pinned Linux image
- Evidence type: synthetic/local only; no hosted Supabase write, MT5 connection,
  broker action, target deployment or target fault test

## Outcome

SCN-031 AC-01 through AC-10 pass for local and synthetic evidence. The dashboard
now obtains nine ordered Demo admission gates from a strict redacted endpoint and
keeps the complete API/source inventory visible when the response is missing or
unsafe. Owner-decision configuration, runtime connectivity, target evidence and
authorization remain separate states.

Every admitted response is Demo-only and explicitly not release-ready, not
round-trip-authorized and not unattended-ready. The implementation has no
positive target gate state and no execution command route. Auto Trading remains
off.

## Verification run on 2026-09-20

- `bash scripts/check-project-baseline.sh` — PASS.
- `python3 scripts/check-agent-skills.py` — PASS; integrity inventory only.
- Targeted Ruff and `.venv/bin/python -m pytest -q
  tests/test_demo_readiness.py tests/test_api_safety.py` — PASS, 10 tests.
- `bash scripts/check-scn-001-local.sh` — PASS, 1,080 Python tests and source
  secret scan over 3,330 text files.
- `npx -y -p node@24.21.0 npm run check:web` — PASS, TypeScript check, 187 tests,
  production build, responsive bundle and client-secret scan.
- `npx -y -p node@24.21.0 npm run check:db:static` — PASS; unchanged migration,
  RPC and source-secret guards.
- `npx -y -p node@24.21.0 npm run check:compose:static` — PASS; unchanged
  Demo-only, loopback and hardening assertions.
- Visual inspection of `http://127.0.0.1:5173` in Chrome — PASS for the desktop
  Charcoal/Gold layout, nine-row ledger, API/source/next-action columns, separate
  Broker truth panel, fail-closed labels and absence of an order-entry control.
- The first `scripts/check-owner-browser.mjs` attempt stopped at prerequisites
  because local Supabase was not running; no browser acceptance state was claimed.
  The guarded loopback-only local stack was then started and the exact verifier
  rerun.
- `env -u DEBUG ... node scripts/check-owner-browser.mjs` under the guarded local
  Docker environment — PASS: production API/UI/Auth flow, exact readiness route
  and nine-gate contract, owner RLS, 320 px containment, failure recovery, token
  refresh/logout and generated-user cleanup. Evidence:
  `output/playwright/scn005-c38f9476-7b28-489e-8c44-9e1a786123b3/result.json`.
  The local Supabase stack was stopped after the verifier.
- `SOCHRON_UV=/Users/faztycoding/.cache/uv/archive-v0/9jK08udG19IeS9M8/bin/uv
  .venv/bin/python scripts/check-worker-package.py` — PASS: byte-identical wheel,
  fresh non-editable install and existing recovery/disabled-command regressions.
  Evidence: `output/worker-package/e371d6380dc545d6bd9d64cd3775932d/result.json`.
- `SOCHRON_UV=... bash scripts/with-local-docker.sh .venv/bin/python
  scripts/check-worker-container.py` — PASS: installed wheel, default-disabled
  networking, runtime hardening and replacement/UNKNOWN recovery. Evidence:
  `output/worker-container/sochron-worker-cc74fc656810/result.json`.

## Acceptance mapping

- AC-01: private path, ownership, permissions, symlink/canonical-path, size,
  approval and unknown/credential-field rejection have focused tests.
- AC-02 through AC-05: ordered fixed gates, redaction, literal safety flags,
  configuration/runtime/target separation and degraded-state derivation have API
  unit and route tests.
- AC-06: the connection map contains the new browser route and exact source
  classes in Python, TypeScript and production-browser checks.
- AC-07 through AC-09: strict root/gate parsing, unsafe-flag rejection, fallback
  inventory, shared retry and parallel request construction have web tests. The
  production browser confirms the ledger and map at desktop, 390 px and 320 px.
- AC-10: complete Python/web, package, container, secret, static database/Compose
  and synthetic browser regressions pass in the recorded environment.

## Not run / not established

- Hosted Supabase, target VPS or public deployment: NOT RUN.
- MT5 terminal, MetaEditor compilation, broker account or Demo order: NOT RUN.
- Broker-side SL, rejected-SL emergency response or bounded open-to-close round
  trip: NOT RUN and NOT AUTHORIZED.
- Target restart, network loss, alerts, disk/storage failure, backup/restore,
  multi-market-day burn-in and p50/p95 latency: NOT RUN.
- Strategy edge, promotion, release approval, Auto Trading and unattended Demo:
  NOT ESTABLISHED and remain off.
