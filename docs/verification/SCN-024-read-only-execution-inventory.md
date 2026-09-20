# SCN-024 read-only MT5 execution inventory verification

## Candidate and acceptance status

Candidate: dirty working tree based on
`e22a326e53f5f3050cec9a911ea0797de21acd41`. The delivery report binds the final
commit after these files are committed and pushed.

AC-01 through AC-08 in the
[task contract](../contracts/SCN-024-read-only-mt5-execution-inventory.md) pass for
the static MQL source boundary and local Python policy-only admission. This is not
an MT5-compiled or account-connected result. MetaEditor compilation, MQL execution,
account access, broker operation, target networking and deployment are `NOT RUN`.

## Implemented scope

- Added a separately default-off MQL observer bound to one exact Demo identity,
  executor ID, symbol and magic number.
- Added bounded double enumeration of current orders and positions. A matching
  symbol/magic effect forces incomplete evidence; other current effects remain
  counted as foreign.
- Added authenticated challenge/inventory upload only. The source has no command
  polling, outcome upload, trade request/result type, `OrderCheck`, `OrderSend`,
  trade helper, history reconstruction or mutation callback.
- Hard-coded `algo_trading_allowed=false` and added a narrower API predicate that
  permits only fresh, complete, foreign-free policy inventory. Normal executor
  admission and command exposure retain the existing algorithmic-trading check.
- Documented private configuration, exact API/UI route placement and the missing
  selected-host loopback, compile/account and full executor work.

## Acceptance evidence

- **AC-01:** source guard and semantic tests require the exact default-off input,
  deny token/password/URL inputs and allow only one fixed read-only token file.
  Disabled `OnInit` returns before configuration, account reads, file access,
  timer setup or network calls.
- **AC-02:** the source requires connected Demo mode and exact login, server,
  currency, margin mode and chart symbol before initialization, sampling and send;
  an identity change latches the observer.
- **AC-03:** source and tests require native current order/position enumeration,
  a 32-item bound and two exact-enumeration fingerprints. A mismatch suppresses
  publication.
- **AC-04:** matching symbol/magic orders or positions force `complete=false`;
  foreign items retain nonzero counts. The existing protocol encoder can emit only
  empty effect arrays, so the source cannot claim history for a current effect.
- **AC-05:** Python tests prove an algorithmic-trading-false empty frame can feed
  the policy writer while `status=stale`, normal `inventory()` is unavailable,
  execution readiness is false and foreign evidence is denied to policy.
- **AC-06:** the guard pins one loopback origin and exactly challenge GET plus
  inventory POST. Existing protocol parsing and bridge tests cover boot, sequence,
  receipt, replay and rejection boundaries.
- **AC-07:** the source guard rejects named broker mutation, history, terminal
  algorithmic-trading authority, socket, notification, export and file-write
  identifiers; mutation tests prove each guarded class is detected.
- **AC-08:** targeted, full Python, web, installed-artifact, static database and
  Compose, baseline, skill-integrity, secret and whitespace checks pass. Missing
  native/container/target evidence is reported below rather than relabelled pass.

## Verification run

- Targeted Ruff, source guard and SCN-024/execution/policy tests: **71 passed**.
- `scripts/check-execution-inventory-source.py`: PASS for static source only;
  source SHA-256
  `7af57c27392f473c9e7cf7616f00852f50b9147e537f3b96f9ce2249978b73b5`;
  compilation, MQL execution, account access and broker operation all reported
  `NOT RUN`.
- `bash scripts/check-scn-001-local.sh`: Ruff PASS, **940 tests passed** in 40.20s
  and repository secret scan PASS.
- `npx -y -p node@24.21.0 npm run check:web`: TypeScript PASS, **180 tests passed**,
  production Vite build and browser-bundle secret scan PASS.
- `scripts/check-worker-package.py`: byte-identical package rebuild, fresh
  non-editable install, disabled command and installed recovery/startup checks
  PASS with uv 0.12.15. Evidence:
  `output/worker-package/0a37b5b46bc24557909472c43b458fb3/result.json`.
- Static database and Compose guards, project baseline, installed/repository skill
  integrity and `git diff --check`: PASS.
- Docker candidate/container checks: `NOT RUN`; no Docker executable was available
  on PATH. MetaEditor/MQL/Wine compile and runtime checks: `NOT RUN`; no matching
  executable was available on PATH. Absence on PATH is not an exhaustive host
  inventory and is not a native-platform result.

## Evidence limits and next boundary

This proves that the committed source is designed as a bounded read-only
current-empty observer and that the API preserves the separation between policy
evidence and execution admission. It does not prove the source compiles, that MT5
enumeration is stable on the selected build, that the selected Demo account is
empty, that Wine/Windows loopback reaches the API, or that any command can be
executed or recovered.

The next execution boundary is a separately default-off EA with an exclusive
executor lock, durable local attempt ledger, cumulative broker history, immediate
preflight, uncertain-write reconciliation and broker-side SL confirmation. The
next signal boundary remains the coverage-complete news collector. Neither is
authorized to operate an account by this source checkpoint.
