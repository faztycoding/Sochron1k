# SCN-007 AC-08 owner history workspace

2026-09-17. Local UI increment based on `70a8e8d5d1282fcebc43403f078aa45372149441`;
candidate dirty during checks. This supplements, not replaces, the earlier
[capture/API evidence](SCN-007-durable-bar-history.md). No real MT5, hosted write,
deployment or trading operation occurred. Existing developer server configuration
was not changed. Full Demo remains **NOT READY**, with Auto Trading disabled.

## Outcome and acceptance

AC-08 has local component and production-browser evidence. The owner workspace now
includes a closed-bar ledger below the live chart. It provides four timeframes,
20-row pages, exact decimal OHLC, unclassified gaps (including page boundaries),
receipt/closure provenance, UTC/Bangkok labels and storage warnings. It does not
claim current prices, executed trades or historical strategy availability.

Pages pin archive ID, receipt watermark and identity; refresh deliberately starts
a new oldest-to-newest set. Only the current page and timestamp cursors are kept
in memory. Keyed account/session/timeframe scopes destroy rows, selection and
cursors; aborted or late requests cannot restore them. Owner authorization polling
also hides history on denial/network failure. No new dependency, schema, backend
endpoint, broker action or browser persistence was added in this increment.

## Verification and limits

- `npx -y -p node@24.21.0 npm run check:web`: typecheck, tests, production build and
  client-bundle scan PASS. Final component/parser suite: **132 tests**. New cases
  cover malformed identity/UTC/decimals/closure/receipt/gaps/quota, disabled/empty
  archives, precision beyond canvas numbers, paging/refresh, request cancellation,
  token/account/timeframe changes, logout, 401/403, network and oversized responses.
  Owner-panel integration proves visibility without live telemetry and hiding on
  authorization failure. Timer advancement proves no automatic history refresh.
- `bash scripts/check-scn-001-local.sh`: **258 PASS**, Ruff PASS and source secret
  scan PASS (160 text files after stopping the test stack). Standalone
  `.venv/bin/pytest -q` also passed. Backend source is unchanged.
- `.venv/bin/python scripts/check-bridge-local.py`: PASS with a real temporary
  Uvicorn/SQLite boundary, independent committed-data inspection and reopen checks.
- `env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs`:
  PASS at `2026-09-17T04:43:49.252Z`, cleanup PASS. Node 24.21.0, Playwright 1.63.0,
  Chromium 153.0.8010.12, Python 3.14.7, CLI 2.117.0. Real loopback Supabase Auth,
  API and temporary history archive; generated users and synthetic native bars only.
  Browser checks exact values against API rows, pinned forward/back paging, gaps,
  keyboard timeframe selection, deliberate error recovery, owner isolation,
  SDK refresh, revoked-token denial and logout/reload data removal. A real API
  process restart retains the same archive rows while telemetry and live chart
  remain empty; history is still visible to the reauthenticated owner.
- Desktop 1440px and mobile 390px screenshots inspected. Page containment also
  checked at 320px; keyboard scrolling reaches the overflowing data table without
  overflowing the page. The mobile navigation is intentionally fixed and appears
  across long full-section screenshot captures, not in the table's data layout.
- Baseline, installed/repository skill integrity and `git diff --check`: PASS.

Retained local artifact directory (ignored, not a committed data fixture):
`output/playwright/scn005-83d9cadc-ab69-451d-8f16-801627a5a9d8/`.
Its `result.json` records runtime image identities and per-source SHA-256 values.
The `scn005-` directory prefix is legacy; the verifier now covers SCN-005/006/007.

| Artifact/source | SHA-256 |
| --- | --- |
| Production build | `decb6ac07870261a79c15f776923ee53d39aae6cb6377f96194edcefa2a07d01` |
| `history-api.ts` | `d1001fd5c0466f085f245ae96572ce731656d7309054de0a45065c1b950679ea` |
| `HistoryPanel.tsx` | `a6cdac260a261c89b16474c89ce0e008fa777135cb30566c22095013c73aee11` |
| `styles.css` | `b5ba3d62a84cece8d7f5e39a6ec1043ebcf892abb45a0e102a515229adc28a48` |
| Browser verifier | `e1557ba2388865f91b5553551406b41cc276e4649ca926df5c9574919e9c2a91` |

Initial failures were retained, not counted as PASS: a shared mutable unit fixture
was isolated; real API integration exposed incorrect margin-mode literals in the
UI parser, now aligned to the API model; a synchronous keyboard-scroll assertion
was replaced with a bounded wait for the actual scroll condition. The final run
above passes those paths. Source scanning while Supabase ran detected its generated
local start-secret file; the normal scoped stop removes that runtime file before
the final source scan, without adding an exclusion or deleting database volumes.
The earlier whole-tree npm signature registry failure is still unresolved and
was not rerun here. No actual MT5/compiler/target-host or Demo order gate is PASS.

## Skills, decisions and next work

`frontend-design` retained the blueprint Charcoal Gold palette, Sarabun/Inter and
a single auditable ledger with gold selected-row emphasis. `vercel-react-best-practices`
informed stable effect inputs, keyed reset and no extra data cache. React documents
[keyed state reset](https://react.dev/learn/preserving-and-resetting-state) and
[effect cleanup](https://react.dev/reference/react/useEffect). `playwright` informed
browser/keyboard/screenshot verification using the project's existing committed
verifier, rather than introducing a second test framework. `supabase` kept the
real owner/session boundary, loopback-only fixtures and secret-safe cleanup; no
authorization is inferred from editable user metadata or a JWT alone. Existing
logout uses the SDK's [session scope](https://supabase.com/docs/reference/javascript/auth-signout).

Next full-product work still includes Supabase M1 synchronization, raw-tick capture,
strategy/research/statistics, actual EA compilation and authorized terminal/SL/
round-trip comparisons, recovery gates, backup/restore, alerts and target burn-in.
Owner choices for broker/Demo server, MT5 host/build and Supabase owner/project
remain missing; credentials must be provisioned privately, never pasted into chat.
