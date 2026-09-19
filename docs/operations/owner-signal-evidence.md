# Owner signal evidence operations

SCN-016 adds a read-only owner projection at `/owner/signals` (browser proxy
`/api/owner/signals`). It reuses the existing private owner Auth configuration;
there is no additional service-role key, signal credential or browser write path.

## Required connections

1. Configure owner Auth exactly as described in
   [owner authentication](owner-authentication.md). The project origin and
   publishable/legacy anon key must identify the same Supabase project containing
   the SCN-002 schema.
2. Keep SELECT grants and forced owner RLS on `signals`, `experiments`, and
   `strategy_versions`. Do not grant browser INSERT, UPDATE, DELETE or strategy
   promotion authority.
3. Run a separate reviewed strategy producer that writes versioned, immutable
   signal evidence after its closed-bar decision is confirmed. SCN-016 does not
   provide that producer.
4. Access the panel only through an online-verified owner session. FastAPI forwards
   that exact token and the unprivileged project key to the pinned Supabase origin,
   then independently verifies all returned owner IDs and removes them from the
   response.

The UI connection map shows `supabase_signals` as the source. When Auth is not
configured it reports `awaiting_configuration`. When Auth is configured, the
public map reports `awaiting_source` because it cannot inspect private owner rows.
After login, an empty owner result is also `awaiting_source`; it is not replaced by
a fabricated WAIT signal.

## Response boundary

The endpoint returns at most 50 rows ordered by `confirmed_at DESC, id DESC` and
exposes only:

- signal/setup identifiers and the exact BUY, SELL, WAIT or BLOCK action;
- formed, confirmed, expiry and created UTC timestamps;
- immutable evidence identifiers and a bounded blocked reason;
- experiment identifier/status/policy version; and
- strategy version/status/code hash/data cutoff.

It never exposes owner UUIDs, internal numeric keys, strategy parameters, access
tokens, Supabase origin, privileged keys, account references or upstream error
bodies. Invalid ownership, malformed joins, duplicate IDs, non-causal timestamps,
future data cutoff, oversized data, redirect, timeout or non-JSON response fails as
the redacted `SIGNALS_UNAVAILABLE` state and the browser clears earlier rows.

## Operator checks

Run the local API/UI tests:

```bash
.venv/bin/python -m pytest tests/test_signal_evidence.py tests/test_owner_auth.py tests/test_api_safety.py -q
npx -y -p node@24.21.0 npm run check:web
```

For real local RLS and browser evidence, start the guarded local stack, run the
browser verifier, then stop it:

```bash
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh start
env -u DEBUG bash scripts/with-local-docker.sh npx -y -p node@24.21.0 node scripts/check-owner-browser.mjs
bash scripts/with-local-docker.sh npx -y -p node@24.21.0 bash scripts/supabase-local.sh stop
```

The verifier creates two local users plus isolated version/account/experiment/
signal rows, proves RLS visibility and API owner denial, checks desktop/mobile
layout and removes every generated row/user. It does not contact hosted Supabase,
MT5 or a broker.

## What is still required

Displaying a synthetic SCN-016 row does not create a working strategy. A Demo
producer still needs closed-bar feature parity, `available_at`/
`formed_at`/`confirmed_at` enforcement, a pinned PA01 version and dataset/feed
provenance, deterministic replay/leakage tests, shadow evidence, and owner approval
before promotion. Signal output must still pass deterministic risk, journal,
executor and MT5 gates; this route cannot call any of them.
