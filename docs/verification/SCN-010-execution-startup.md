# SCN-010 explicit execution startup admission

2026-09-20; base `6ee67dcc53af0906158ed36dad502bd4389ebf59`, dirty
candidate inputs. The containing commit identifies delivery; retained reports bind
the precommit base to exact input hashes. macOS 26.6.2 arm64, Python 3.14.7,
SQLite 3.53.1, pytest 9.1.1, Ruff 0.16.8 and uv 0.12.15. Local Docker 29.5.2 /
Compose 5.5.1; Linux arm64 Python 3.14.7 and source/linkage-admitted SQLite 3.53.4.

## Outcome and scope

ExecutionService now starts closed. Explicit startup admits only an existing,
current Bangkok-day risk baseline plus a complete/fresh simulator inventory bound
to the expected Demo account, server, currency, margin mode, symbol, executor and
generation. It reconciles retained active broker snapshots before admission and
does not create a baseline, clear a halt or send/replay a command. New services,
processes and forked instances require new admission; query-only recovery does not
grant it. Public `execution_ready` and `auto_trading_enabled` remain false.

Submit rechecks inventory, generation, account/Equity, risk baselines/halts,
five-second quote/expiry/account freshness and the current Thailand day. It reserves
account-wide exposure and expected risk transactionally, journals an attempt before
adapter invocation, and conservatively persists UNKNOWN for any ordinary exception
or malformed/conflicting response after invocation. UNKNOWN retains its reservation
and cannot be resubmitted without external reconciliation and a new startup.

Broker snapshots are bounded and checked transactionally for exact requested/
filled/remaining volume, aggregate and immutable deals, tickets/ownership,
dispatch evidence, nonregressing state and SL confirmation. Rejected inventory is
validated too; a terminal label cannot conceal a fill. Expected-risk records must
match the command account/experiment, and an orphan attempt cannot turn a QUEUED
command into broker evidence. Invalid evidence rolls back without journal mutation.

This is a local Python/simulator safety boundary. Inventory completeness, foreign
counts and executor generation are trusted adapter assertions. The five-second
duration bound is cooperative, not a hard kernel/I/O deadline. There is no execution
HTTP route, MT5 mutation adapter, distributed fence, broker OrderCalcProfit,
close/cancel, cash-flow/day-rollover lifecycle, total-halt release, or owner command
to provision a baseline. Actual MetaEditor/terminal, Demo broker identity/inventory,
broker-side SL, target restart/network-loss and open-to-close round trip are NOT RUN.
Full Demo and unattended release remain NOT READY.

## Failing-first and review regressions

The original startup implementation was developed from failing missing-admission
tests. Candidate review on 2026-09-20 then ran six new negative cases before fixes:

```text
.venv/bin/pytest -q tests/test_execution_startup.py \
  -k 'rejected_inventory_label or expected_risk_must or orphan_attempt or unexpected_adapter_outcome' \
  --tb=short
6 failed, 71 deselected in 0.46s
```

The failures showed that a rejected label could bypass snapshot validation, a
foreign expected-risk record could reach low-level reserve/dispatch, an orphan
attempt could admit QUEUED evidence, and unexpected adapter outcomes could escape
without durable UNKNOWN. No assertion, timeout or acceptance criterion was weakened.
After the fixes, the focused startup/execution/recovery set passed 166 tests in
8.31s.

## Final verification

- `bash scripts/check-scn-001-local.sh`: **663 PASS**, 36.85s; Ruff and secret
  scan PASS over 962 text files on host Python 3.14.7.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv .venv/bin/python scripts/check-worker-package.py`:
  PASS; `output/worker-package/3796a670d0bc4a12bef6f01868e72d08/result.json`,
  recorded 2026-09-19 19:25:58 UTC. A fresh non-editable wheel ran explicit
  missing-baseline denial, one acceptance-then-UNKNOWN, restart/query reconciliation,
  no resend, generation mismatch and persistent-halt denial. Oracle: one send,
  one attempt, one deal, halts preserved, both release flags false. The same report
  also retained the existing synthetic recovery rehearsal; MT5 and hosted targets
  were NOT RUN.
- `bash scripts/with-local-docker.sh .venv/bin/python scripts/check-worker-container.py`:
  PASS; `output/worker-container/sochron-worker-5712f2b55496/result.json`,
  19:25:53–19:26:36 UTC. Candidate image
  `sha256:2afc016d920be6cf628d56549627fbc037f4a55f08c54ec1c12a58fdfe4d56ad`;
  cleanup 0, private synthetic fixture key removed, release_ready=false.
- `bash scripts/with-local-docker.sh npx -y -p node@24.21.0 npm run check:compose:local`:
  PASS; `output/compose/sochron-verify-20856f82d4a5/result.json`,
  19:25:54–19:26:41 UTC. API image
  `sha256:0fb1544dc232f7574d25f9bdec6969811e52c240294c80b0668dfa28f3950a0d`;
  cleanup 0.
- `SOCHRON_UV=/tmp/sochron-uv.dALxxk/venv/bin/uv bash scripts/with-local-docker.sh .venv/bin/python scripts/check-container-python.py sochron-worker-5712f2b55496:candidate`:
  **640 PASS**, 19.62s; `output/container-python/sochron-python-cafd60941758/result.json`,
  19:31:34–19:32:02 UTC.
- Same verifier with `sochron-verify-20856f82d4a5-api:local`: **640 PASS**,
  19.63s; `output/container-python/sochron-python-e798437305a4/result.json`,
  19:32:23–19:32:51 UTC. Both Linux suites exclude 23 workstation-only MT5
  source scanner tests. The initial API invocation used the image ID as a Dockerfile
  base reference; BuildKit attempted a registry pull and failed before tests. The
  corrected local tag resolved to that exact image ID and passed. This was retained
  as verifier-invocation evidence, not represented as a product-code failure.

Baseline, pinned-skill and final diff checks are recorded after this document in
the containing delivery. No browser/Auth/Supabase schema suite was rerun because
this increment changes no UI, route, authentication or migration. The installed
artifact, Compose and both affected Linux suites cover packaging/runtime drift but
do not establish target-host or broker behavior.

## Candidate identities

| File | SHA-256 |
| --- | --- |
| `executor.py` | `1683a43d3555614fd898081a773ec7333fbc1cc391eaa413f632d309a92a468c` |
| `simulator.py` | `4634542a8ef9d0025813c8f871b2ca8aa936bf8851165cba7a4fb690188bd99d` |
| `startup.py` | `da2911ca8ae0f9bce8b8791f7fcd8a552c8d509b7365cee33be1343bbf341cb5` |
| `service.py` | `4e9ce1ad05117f72d0c3f100939857f4c3b59f12e958fe9fbc5ce8fc8626e6b9` |
| `journal.py` | `69439942831b001e9491f9723d1580a08f76a019785183c46a248f4abc7b6a75` |
| `test_execution_startup.py` | `b1db5c60a246cc0267a116a60b6d0189793f54d57a154644fd1fca0f66c06a69` |
| `execution_startup_probe.py` | `7debbf2d6ff881af676a4eb0f73dc956ad259c914c9d86e21f85347275b8c397` |
| `check-worker-package.py` | `6e15b7a75f4f76d9c5fc9bfe9bfb6723eda5a09a3fc438839b7b07ff64287f8a` |

Wheel SHA-256 is
`2b3582697a980b156a671a431766ae7869fb3947dbdf686997ef92dd7001e56e`.
The report records exact source/build/fixture hashes; version 0.1.0 alone is not an
identity. Passing synthetic checks does not authorize a broker operation or clear
SCN-001. The next safe execution increment is the authenticated exclusive Demo MT5
inventory/command adapter and complete close/cancel/SL recovery, after the owner
records the exact broker/server/account-mode/symbol contract inputs.
