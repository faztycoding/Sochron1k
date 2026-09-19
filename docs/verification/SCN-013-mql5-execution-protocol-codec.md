# SCN-013 MQL5 execution protocol codec

2026-09-20; base `1c886e3d9b2c01905206d436a9d501f79557bf2f`, dirty
candidate inputs. The containing commit identifies delivery; source hashes below
bind the precommit evidence. This is local source/static evidence only.

## Outcome and acceptance status

The repository now contains a pure MQL5 parser/encoder for the authenticated
SCN-012 execution wire contract and a pure self-test script. The parser requires
the exact 22-field command envelope with bounded, unique known fields and strict
operation nullability. Encoders produce an empty Demo inventory bootstrap and
either confirmed-rejection or uncertain outcome evidence bound to the command.

SCN-013 is a source checkpoint, not a fully passed acceptance boundary. AC-06's
source-purity guard and AC-07's Python verifier/mutation-test portion pass. The
sources implement AC-01 through AC-05, but those MQL behaviors and the remaining
AC-07/08 evidence stay `PARTIAL` until a selected MetaEditor compiles them and the
fresh MQL self-test generates both exact fixtures. Account reads, WebRequest, broker inventory,
`OrderCheck`, `OrderSend`, `OnTradeTransaction`, restart reconciliation and Demo
operation are all `NOT RUN`. This is not the mutation EA, does not pass SCN-001
AC-07, does not change public `execution_ready=false`, and does not enable Auto
Trading. Full Demo remains `NOT READY`.

## Failing-first and negative evidence

The first targeted test run failed during collection because the required source
guard did not exist:

```text
.venv/bin/python -m pytest -q tests/test_mt5_source.py
FileNotFoundError: scripts/check-execution-protocol-source.py
1 error in 0.20s
```

Mutation tests inject every forbidden terminal, account, file/network and trading
identifier. They also inject imports, an unreviewed include, credential input and
an extra file write. Golden verifiers reject value drift, duplicate JSON keys, NUL
and oversize data without printing invalid contents. Parser self-test cases reject
duplicates, unknown keys, trailing bytes, inconsistent operations, exponent and
over-precision decimals, non-UTC time, empty fractional seconds, invalid calendar
dates, unsafe identifiers and ambiguous/effectful rejection codes.

## Verification

Precommit checks on macOS arm64, Python 3.14.7, pytest 9.1.1 and Ruff 0.16.8:

- `.venv/bin/python scripts/check-execution-protocol-source.py`: PASS; pure source
  guard only; compilation, MQL execution, account access and broker operation all
  reported `NOT RUN`.
- `.venv/bin/python scripts/check-execution-protocol-fixture.py --kind inventory`:
  PASS against the committed synthetic API golden.
- `.venv/bin/python scripts/check-execution-protocol-fixture.py --kind outcome`:
  PASS against the committed synthetic API golden.
- `.venv/bin/python -m pytest -q tests/test_mt5_source.py`: **55 passed** in
  0.46s.
- `.venv/bin/python -m ruff check scripts/check-execution-protocol-source.py scripts/check-execution-protocol-fixture.py tests/test_mt5_source.py`:
  PASS.
- `bash scripts/check-scn-001-local.sh`: Ruff passed, **758 passed** in 35.06s,
  and the secret scan passed over 1,846 text files on Python 3.14.7.
- `bash scripts/check-project-baseline.sh`: PASS for the eight-file baseline,
  Demo-safe defaults, blank secret examples and SCN-001 IDs.
- `python3 scripts/check-agent-skills.py`: PASS for all recorded installed skills
  and the four repository Sochron skill sources; integrity scope only.
- `git diff --check`: PASS.

The committed fixtures are hand-authored expected bytes. Their successful schema
validation does not show that MQL produced them. The target-host procedure requires
a recorded MetaEditor build, fresh zero-error/zero-warning compiler output, a fresh
self-test PASS and separately verified generated paths.

## Candidate identities

| File | SHA-256 |
| --- | --- |
| `ExecutionProtocol.mqh` | `f042c00b136f0187136587a6f205fb4ed79caf5c80be56735ce72bfb7e18a509` |
| `SochronExecutionProtocolSelfTest.mq5` | `67b4960d3f1910e0f6caa78931956a45a9e15857d51daa0da1a7291bd7943897` |
| inventory golden | `4cd130b17f981940c91d15b85fafff1a7b29f933860b0c244b567302bb3bb19a` |
| outcome golden | `61990339afd24980d345af599e4981689f64fb201ebdcfd69e4b928dc24aef8a` |

## Remaining boundary

The next work unit is the default-off execution EA with a private token file,
exclusive local lock, durable attempt ledger before send, immediate Demo identity
and contract preflight, broker inventory/history reconstruction, entry/cancel/close,
partial-fill handling, broker-side SL confirmation and emergency behavior. Ambiguous
send outcomes must remain UNKNOWN and be reconciled without resend. Actual compile,
terminal and broker gates then require the owner's target inputs and separate Demo
operation authorization.
