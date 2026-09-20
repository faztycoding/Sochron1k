# SCN-022 durable PA01 producer verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`f105b027cf2b6baafab85cbd96f030f154ac474e`. The delivery report will bind the
final commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-022-durable-pa01-producer.md) pass for the local
synthetic producer, actual guarded local PostgREST receiver and affected installed
and Linux artifacts. No hosted write, actual MT5 read, policy-handoff writer,
scheduler, broker operation, deployment or Auto Trading change was performed.

## Implemented scope

- Added a bounded query-only native archive projection and a strict owner-only
  policy-evidence file reader. They feed the existing deterministic aggregation and
  protocol-v2 envelope and emit at most one strictly newer closed-M5 decision.
- Added a private SQLite WAL journal with immutable canonical payloads,
  `PREPARED`/`UNKNOWN`/`VERIFIED`/`QUARANTINED` states, a five-send ceiling and an
  exact source/owner/strategy/experiment/code/destination binding.
- Added fixed store/read PostgREST transport. Every send is journaled as UNKNOWN
  first, every store response still requires independent read-back, and confirmed
  receiver rejection or changed evidence is quarantined.
- Added the explicit installed `sochron-pa01` CLI. It is disabled without private
  configuration, absent from default Compose and always reports execution readiness
  and Auto Trading as false.
- Updated the Signals UI/connection rail to identify the implemented producer and
  the remaining policy evidence/config dependency without fabricating a signal.

## Acceptance evidence

- **AC-01/02:** native-source, aggregation, envelope and producer tests reject
  unavailable/future/stale/mixed evidence and preserve one decision per newer M5.
- **AC-03/04:** unit tests inspect UNKNOWN before transport. The local PostgREST
  verifier commits the row, kills the sender before its response, then proves the
  restarted journal reads the exact receiver record without a second store.
- **AC-05:** foreign, changed, malformed and exact named receiver denials become a
  persistent quarantine; an unknown transport result remains UNKNOWN.
- **AC-06:** private path/file and replacement checks, journal schema/digest audit,
  exact target binding and redacted CLI errors pass.
- **AC-07:** real local row counts prove one snapshot/signal and zero command,
  risk-event or order rows. Default CLI/container behavior stays disabled.
- **AC-08:** full Python/web/database, installed artifact and affected Linux-image
  regressions pass without weakening previous tests.

## Verification run

- Targeted Ruff plus PA01/native tests: **130 passed**.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **882 tests passed** in 40.25s
  and repository secret scan PASS.
- `.venv/bin/python -m pytest -q`: **882 passed** in 41.18s.
- `npm run check:web`: TypeScript PASS, **180 tests passed**, production Vite build
  and client-bundle scan PASS.
- Guarded `npm run check:db:local`: fresh reset/migrations and lint PASS; advisors
  returned only fresh-database unused-index INFO; **459 pgTAP checks passed**; RLS
  mutation, native concurrency and PA01 concurrency checks passed.
- `scripts/check-pa01-producer-local.py`: actual local PostgREST store/SIGKILL/
  restart read-back without resend PASS; exact singleton snapshot/signal and zero
  command/risk/order rows PASS. Evidence:
  `output/pa01-producer/7180c4543f2f42669a21361c6930755a/result.json`.
- `scripts/check-native-sync-local.py`: existing native worker PostgREST crash,
  owner-isolation, immutable replay and conflict recovery suite PASS.
- `scripts/check-owner-browser.mjs`: PASS on Playwright 1.63.0 / Chromium
  153.0.8010.12 against real local Auth/API/PostgREST, including signal placement,
  research/execution panels and 320px containment.
- `scripts/check-worker-package.py`: exact reproducible wheel/sdist and isolated
  install PASS, including disabled installed `sochron-pa01`. Evidence:
  `output/worker-package/e644802e93ea4d5099a2f29b7c744c85/result.json`.
- `scripts/check-worker-container.py`: candidate image
  `sha256:bdfd517942bb8a52e5c555b046ef37bb92a0bfe02b66bc4cb700c0d1633af988`
  PASS for installed source identity, hardening and restart reconciliation. Evidence:
  `output/worker-container/sochron-worker-84d4b341a006/result.json`.
- `scripts/check-container-python.py sochron-worker-84d4b341a006:candidate`:
  SQLite source/linkage probe and **827 tests passed** in the affected Linux image.
  Evidence: `output/container-python/sochron-python-e433223dc58b/result.json`.
- Project baseline, installed/repository skill integrity, static database/Compose,
  2,822-file secret scan and `git diff --check`: PASS. The guarded local Supabase
  stack was stopped after integration checks.

The first real PostgREST attempt exposed `PA01_FEATURES_INVALID`: unrounded
indicator decimals exceeded the receiver's 40-character text bound. JSON-only
feature/pivot serializers now remove insignificant trailing zeros without rounding;
the targeted regression and a fresh local crash-recovery run pass. A static scan
run while local Supabase was active correctly found its generated temporary service
key; after stopping the stack, the same scan passed and no key is committed.

Candidate source hashes include native reader
`0befae0776459f2a65699f29c4ad2c4ef8e6c38277570a01d4ff82b67b9b9a9a`, journal
`ac11fef0a315498500ca3829fe76f25df28548e583c67dc52f12f4bc075427a0`, transport
`3d721dc3ba3b6d27eb152452d27c0049f13c6a14cb8f8692a6e8682c55b72dfb` and local
verifier `2a1efbf39737563be0cfbc0e728dfd8c239ed4cbc68d3dfe7b4467b14288ba27`.

## Evidence limits and next boundary

This proves the local software publication and ambiguous-write recovery path using
generated evidence. The policy file remains a validated handoff contract, not an
authoritative observation producer. Hosted Supabase, target scheduling/recovery,
actual MT5 data parity, research splits/OOS, strategy performance, broker execution
and release readiness remain unverified. The next safe source increment is the
atomic quote/session/news/account policy writer; the Statistics panel separately
still needs a reproducible evaluation producer.
