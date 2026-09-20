# PA01 point-in-time tick replay

## Purpose and safety boundary

`sochron-pa01-backtest` reruns the pinned PA01 kernel over one retained historical
artifact and creates the canonical labelled bundle consumed by
`sochron-research-evaluation`. It is an explicit offline command: it has no
network, Supabase, MT5, command, risk, promotion or execution dependency.

A successful run proves that the supplied artifact was internally causal and that
the labels are reproducible. It does not prove that the source is licensed,
complete, representative or matched to the selected Demo broker. Auto Trading
remains off.

## Data path and UI position

```text
owner-supplied historical M5/H1 bars + Bid/Ask ticks + policy observations
  -> sochron-pa01-backtest
  -> canonical sochron.research-bundle.v1
  -> sochron-research-evaluation
  -> private SQLite journal
  -> backend-only Supabase RPC
  -> owner-RLS evaluations
  -> FastAPI GET /owner/statistics
  -> browser GET /api/owner/statistics
  -> UI #research-statistics
```

The UI panel is after `#signal-evidence` and before `#bar-history`. Until a real
historical artifact is replayed, evaluated and published, it displays
`awaiting_source`; it does not display fabricated zero performance.

## Input contract

The input is canonical `sochron.pa01-tick-replay.v1` JSON, at most 64 MiB. It must
contain:

- the exact PA01 strategy/parameter identity and SHA-256 code/source identities;
- one symbol, feed, broker UTC offset, tick grid and temporal split/window;
- fixed spread, slippage, commission, swap and operating-cost assumptions;
- exact volume, point value and starting equity assumptions;
- ordered closed M5/H1 bars with event and availability times;
- ordered Bid/Ask ticks with event and availability times and complete five-second
  or better coverage of the active replay window;
- exactly one market/news policy observation for every eligible M5 decision;
- a bootstrap plan accepted by the downstream evaluator.

Decimal evidence is encoded as JSON strings. Timestamps are normalized UTC `Z`
strings. The `source_dataset_hash` is SHA-256 over canonical JSON after
removing only that field. The full field constraints and acceptance cases are in
[SCN-030](../contracts/SCN-030-pa01-tick-replay-backtest.md).

The repository does not yet capture or convert broker tick history into this
artifact. The owner must still select the historical source, license/retention
method, broker contract assumptions and cost scenario. Do not repair missing ticks
or invent policy coverage to make an input pass.

## Private local operation

Use absolute canonical paths. Both parent directories must already exist, belong
to the current user and have mode `0700`; the input file must have mode `0600`.
The output must not exist, unless it already contains the identical bundle.

```bash
sochron-pa01-backtest build \
  --input /absolute/private/research/pa01-replay.json \
  --output /absolute/private/research/pa01-bundle.json
```

Success returns `BUILT`, the dataset hash, evaluation fingerprint and closed-trade
sample size. The response also states that promotion, execution readiness and Auto
Trading are false. Invalid input or path state returns `PA01_BACKTEST_INVALID` and
does not leave a partial accepted output.

To continue locally, point the separately configured evaluation producer at the
created bundle and run its `init` action. `init` is local and makes no network
request. `publish` is a separate backend-only hosted write and requires explicit
target configuration and authority; see the
[research evaluation runbook](research-evaluation-producer.md).

## Local verification

```bash
.venv/bin/python -m pytest tests/test_pa01_backtest.py -q
.venv/bin/python scripts/check-worker-package.py
```

Package verification builds a fresh installed artifact and proves that invoking
the installed backtest command without its explicit action performs no work. It
uses synthetic evidence only; MT5, hosted Supabase and real market data are not
contacted.
