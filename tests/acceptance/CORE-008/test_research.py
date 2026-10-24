"""Approved CORE-008 contract tests (docs/contracts/CORE-008-research.md v1.5); run pytest from the
repository root.

Only contract names are used: sochron.research (RESEARCH_VERSION, HOLDOUT_CUTOFF_UTC, ResearchError,
BudgetExceeded, HoldoutRefused, Purpose, USED_PARAMETERS, BASELINE_RUNS, Dataset, Summary,
BaselineSummary, RunRecord, append_record, read_records, summarize, percentile, run_variant,
BaselineResult, random_entry_baseline, Neighbour, neighbours, Check, Evaluation, evaluate,
render_report), the module sochron.research.registry (append_record: the write seam of F39),
sochron.strategy (entry_blockers, decide, indicators, IndicatorRow, H001Params, StrategyError,
STRATEGY_VERSION) and sochron.strategy.h001 (the module whose entry_blockers decide calls) and, to
build inputs and expectations, the merged sochron.backtest (run, simulate_trade, Result, SizedLots,
Rollover, BACKTEST_VERSION), sochron.costs (H001_COSTS, CONTEXT, CostModel, Provenance, BadVolume,
stress), sochron.timebase (rule_for, TimeRule, to_utc, bar_open), sochron.core (Bar) and
sochron.data.snapshot (AggregatedBar). Every bar is synthetic and every registry file is in tmp_path.
The hand-computed values and their arithmetic are in tests/golden/CORE-008/research_cases.py.

Conventions the contract leaves to these tests (also in docs/handoff/CORE-008.md):
1. Dataset, Summary, BaselineSummary, BaselineResult, Neighbour, Check and Evaluation are frozen
   dataclasses with the contract's field names in the contract's order. RunRecord is a frozen
   dataclass whose fields are the registry table's names without run_id (in any order); run_id is a
   property and line() returns bytes. Tests build every one of them with keyword arguments.
2. A value error is ResearchError or a subclass of it, but never BudgetExceeded or HoldoutRefused
   where the contract does not name those; budget refusals are BudgetExceeded and holdout refusals
   HoldoutRefused. A wrong type is TypeError: bool, int, float or str where a Decimal is required,
   a list where a tuple is required, a str registry path, None where a value is required.
3. A torn tail's message names its byte offset (the first byte after the last LF) as a number; a bad
   line's message names its line number (counted from 1) as a number of its own.
4. run_variant and random_entry_baseline write hypothesis "H001"; the setup freeze, the budgets and
   the base lock read only lines of that hypothesis.
5. Interrupted runs are made by appending a started line with append_record exactly as the runner
   writes it; failed runs by a started line and its failed line.
6. M15 bars are sochron.data.snapshot.AggregatedBar values built here from their M1 (first open,
   highest high, lowest low, last close) with an explicit spread and flags, 1 to 3 M1 per bar. On
   the 106-bar series the M15 spread of bar 99 is 700 while its M1 spreads are 200: the contract's
   checks do not compare M15 values with their M1 (CORE-007 "Input และการตรวจ").
7. The fake random.Random has only randrange (randrange(n), or randrange(0, n)) and records its
   seed and every n. The seam tests wrap sochron.research.registry.append_record and record the
   status of every record written through it.
8. Decimals are compared by value; a representation is pinned only where the contract fixes it: the
   registry line, the report text, Check strings, neighbour values and the top-5 tie rule.
9. The report lists the summary bullets by seq, then the baseline bullets by seq.
"""

import difflib
import hashlib
import json
import random
import re
from bisect import bisect_right
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_UP, Decimal, Inexact, Rounded, getcontext, localcontext
from importlib import import_module
from itertools import cycle, product
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from typing import get_args

import pytest


def _golden():
    return run_path(str(Path(__file__).resolve().parents[2] / "golden/CORE-008/research_cases.py"))


_G = _golden()
_MODULES = {"research": "sochron.research", "registry": "sochron.research.registry",
            "strategy": "sochron.strategy", "h001": "sochron.strategy.h001"}
_BASE_NAMES = ("ResearchError", "BudgetExceeded", "HoldoutRefused", "Dataset", "Summary", "BaselineSummary",
               "RunRecord", "append_record", "read_records")
_RECORD_FIELDS = frozenset({
    "seq", "status", "started_seq", "hypothesis", "purpose", "variant", "params", "base_run_id",
    "strategy_version", "backtest_version", "research_version", "code_commit", "dataset", "cost_model",
    "cost_provenance", "equity", "sizer_label", "rollover_zone", "rollover_at", "time_rule_server",
    "time_rule_version", "sides", "seed", "runs", "error", "summary", "baseline",
})
_SHAPES = {
    "Dataset": ("snapshot_id", "manifest_sha256", "period_start_utc", "period_end_utc", "m1_bars"),
    "Summary": ("trades", "expectancy_r", "max_drawdown_r", "net_money", "long_trades", "long_expectancy_r",
                "short_trades", "short_expectancy_r", "top5_removed_expectancy_r", "expectancy_by_year",
                "ambiguous_trades", "flagged_trades", "gap_fills", "end_of_data_trades"),
    "BaselineSummary": ("runs", "trades_per_run", "seed", "mean_r", "p05_r", "p50_r", "p95_r",
                        "variant_mean_hold_m1", "variant_median_hold_m1", "baseline_mean_hold_m1",
                        "baseline_median_hold_m1"),
    "BaselineResult": ("expectancies_r", "summary", "record"),
    "Neighbour": ("parameter", "direction", "value", "params"),
    "Check": ("name", "value", "threshold", "passed"),
    "Evaluation": ("variant", "base_run_id", "dataset", "screen", "verdict", "checks"),
}
_INT_SUMMARY = frozenset({"trades", "long_trades", "short_trades", "ambiguous_trades", "flagged_trades",
                          "gap_fills", "end_of_data_trades"})
_INT_BASELINE = frozenset({"runs", "trades_per_run", "seed", "variant_median_hold_m1", "baseline_median_hold_m1"})
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_DEFAULT = object()  # "use the valid value": lets a test pass None itself
_NON_FINITE = ("NaN", "sNaN", "Infinity", "-Infinity")


class _SizerFailure(RuntimeError):
    pass


class _FakeMisuse(Exception):
    pass


def _api(monkeypatch, ac, *names):
    """Missing implementation fails each AC without breaking collection; contract names only."""
    monkeypatch.syspath_prepend(str(Path.cwd() / "src"))
    symbols = []
    for name in names:
        prefix, _, attribute = name.partition(".")
        module_name = _MODULES[prefix]
        try:
            module = import_module(module_name)
        except ImportError as error:
            pytest.fail(f"{ac}: {module_name} not implemented ({error})", pytrace=False)
        if not attribute:
            symbols.append(module)
            continue
        try:
            symbols.append(getattr(module, attribute))
        except AttributeError:
            pytest.fail(f"{ac}: {module_name}.{attribute} not implemented", pytrace=False)
    return tuple(symbols)


def _kit(monkeypatch, ac, *names):
    """The named sochron.research symbols, the helpers' symbols and the merged modules."""
    wanted = tuple(dict.fromkeys(_BASE_NAMES + names))
    symbols = _api(monkeypatch, ac, *(f"research.{name}" for name in wanted))
    kit = SimpleNamespace(**dict(zip(wanted, symbols)))
    kit.ac = ac
    kit.Bar = import_module("sochron.core").Bar
    kit.bt = import_module("sochron.backtest")
    kit.costs = import_module("sochron.costs")
    kit.tb = import_module("sochron.timebase")
    kit.strategy = import_module("sochron.strategy")
    kit.snapshot = import_module("sochron.data.snapshot")
    kit.g = _G
    kit.rule = kit.tb.rule_for(_G["RULE_SERVER"])
    return kit


def _registry_module(monkeypatch, ac):
    (module,) = _api(monkeypatch, ac, "registry")
    if not callable(getattr(module, "append_record", None)):
        pytest.fail(f"{ac}: sochron.research.registry.append_record not implemented", pytrace=False)
    return module


# ----------------------------------------------------------------------------------- values

def _dec(value):
    return None if value is None else Decimal(value)


def _utc(stamp):
    return datetime.fromisoformat(stamp).replace(tzinfo=UTC)


def _raw(stamp):
    """Raw MT5 seconds of a UTC stamp under the measured rule (offset 0, CORE-001)."""
    return (_utc(stamp) - _EPOCH) // timedelta(seconds=1)


def _or(value, default):
    return default if value is _DEFAULT else value


def _ascii(text):
    return "".join(character if ord(character) < 128 else "?" for character in text)


def _error_text(error):
    """The registry error field the contract defines for an exception object."""
    return _ascii(f"{type(error).__name__}: {error}")


def _context_state():
    context = getcontext()
    return (context.prec, context.rounding, context.Emin, context.Emax, context.capitals,
            context.clamp, dict(context.traps), dict(context.flags))


def _hostile(context, prec=50):
    """A caller context that changes rounded results if the module used it."""
    context.prec = prec
    context.rounding = ROUND_UP
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    context.clear_flags()


def _rollover(kit, hour=17):
    zone, _, minute = kit.g["ROLLOVER"]
    return kit.bt.Rollover(zone, time(hour, minute))


def _params(kit, variant, values=None, **changes):
    values = {**(values or kit.g["DEFAULTS"]), **changes}
    return kit.strategy.H001Params(variant=variant, f=values["f"], s=values["s"], n=values["n"],
                                   theta=Decimal(values["theta"]), N=values["N"], M=values["M"],
                                   k=Decimal(values["k"]))


def _run_params(kit, variant="B", **changes):
    return _params(kit, variant, kit.g["RUN_PARAMS"], **changes)


def _dataset(kit, spec, **changes):
    snapshot, manifest, start, end, bars = spec
    values = {"snapshot_id": snapshot, "manifest_sha256": manifest, "period_start_utc": _utc(start),
              "period_end_utc": _utc(end), "m1_bars": bars, **changes}
    return kit.Dataset(**values)


def _summary(kit, spec, **changes):
    spec = {**spec, **changes}
    values = {}
    for name in _SHAPES["Summary"]:
        value = spec[name]
        if name == "expectancy_by_year":
            value = tuple((year, Decimal(text)) for year, text in value)
        elif isinstance(value, str):
            value = Decimal(value)
        values[name] = value
    return kit.Summary(**values)


def _baseline(kit, spec, seed, **changes):
    values = {name: (Decimal(value) if isinstance(value, str) else value) for name, value in spec.items()}
    values.update(runs=1000, seed=seed)
    values.update(changes)
    return kit.BaselineSummary(**values)


def _param_pairs(params):
    return tuple((name, str(getattr(params, name))) for name in _G["PARAM_ORDER"])


def _cost_pairs(kit, model):
    return tuple((item.name, str(getattr(model, item.name))) for item in fields(kit.costs.CostModel)
                 if item.name != "provenance")


def _provenance_pairs(model):
    return tuple(sorted((name, record.status) for name, record in model.provenance.items()))


def _flat_model(kit):
    return replace(kit.costs.H001_COSTS, swap_long_points_per_night=Decimal("0"))


def _other_rule(kit, server="SYN-OTHER"):
    rule = kit.rule
    return kit.tb.TimeRule(server=server, symbol=rule.symbol, terminal_build=rule.terminal_build,
                           offset_seconds=0, evidence_from=rule.evidence_from, evidence_to=rule.evidence_to,
                           evidence_ref="synthetic", version=rule.version)


def _fields(kit, *, seq, status="started", started_seq=None, purpose="select", params=None, dataset=None,
            base=None, model=None, equity="10000", sizer_label=None, rollover=None, rule=None, code_commit=None,
            hypothesis="H001", sides=None, error=None, summary=None, baseline=None, seed=_DEFAULT, runs=_DEFAULT):
    """Every RunRecord field as the contract's registry table derives it from the run's inputs."""
    g = kit.g
    params = params if params is not None else _params(kit, "B")
    dataset = dataset if dataset is not None else _dataset(kit, g["NORMATIVE_DATASET"])
    model = model if model is not None else kit.costs.H001_COSTS
    rollover = rollover if rollover is not None else _rollover(kit)
    rule = rule if rule is not None else kit.rule
    if sides is None:
        sides = ("long",) if purpose == "long_only" else ("long", "short")
    if seed is _DEFAULT:
        seed = int(base[:15], 16) if purpose == "random_entry" else None
    if runs is _DEFAULT:
        runs = 1000 if purpose == "random_entry" else None
    return {
        "seq": seq, "status": status, "started_seq": started_seq, "hypothesis": hypothesis, "purpose": purpose,
        "variant": params.variant, "params": _param_pairs(params), "base_run_id": base,
        "strategy_version": kit.strategy.STRATEGY_VERSION, "backtest_version": kit.bt.BACKTEST_VERSION,
        "research_version": "research-v1", "code_commit": code_commit or g["CODE_COMMIT"], "dataset": dataset,
        "cost_model": _cost_pairs(kit, model), "cost_provenance": _provenance_pairs(model),
        "equity": Decimal(equity), "sizer_label": sizer_label or g["SIZER_LABEL"], "rollover_zone": rollover.zone,
        "rollover_at": f"{rollover.at.hour:02d}:{rollover.at.minute:02d}", "time_rule_server": rule.server,
        "time_rule_version": rule.version, "sides": tuple(sides), "seed": seed, "runs": runs, "error": error,
        "summary": summary, "baseline": baseline,
    }


def _rec(kit, **kwargs):
    return kit.RunRecord(**_fields(kit, **kwargs))


def _result_of(kit, record, *, seq=None, status="ok", **changes):
    """The ok or failed record of a started record (contract: same identity, started_seq = its seq)."""
    return replace(record, seq=record.seq + 1 if seq is None else seq, status=status, started_seq=record.seq,
                   **changes)


def _snapshot(path):
    return path.read_bytes() if path.exists() else None


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _line_with(line, change):
    """A registry line rewritten by change(obj) and given the run_id of its new content (contract hash)."""
    obj = json.loads(line)
    change(obj)
    obj.pop("run_id", None)
    obj["run_id"] = hashlib.sha256(_canonical(obj)).hexdigest()
    return _canonical(obj) + b"\n"


def _same(a, b, label="value"):
    """Differences in type or value (Decimal and datetime representation included), recursively."""
    if type(a) is not type(b):
        return [f"{label}: {type(a).__name__} {a!r} vs {type(b).__name__} {b!r}"]
    if isinstance(a, Decimal):
        return [] if str(a) == str(b) else [f"{label}: {a!r} vs {b!r}"]
    if isinstance(a, datetime):
        return [] if a == b and a.utcoffset() == b.utcoffset() else [f"{label}: {a!r} vs {b!r}"]
    if isinstance(a, tuple):
        if len(a) != len(b):
            return [f"{label}: lengths {len(a)} vs {len(b)}"]
        return [item for index, (x, y) in enumerate(zip(a, b)) for item in _same(x, y, f"{label}[{index}]")]
    if is_dataclass(a):
        return [item for f in fields(a) for item in _same(getattr(a, f.name), getattr(b, f.name), f"{label}.{f.name}")]
    return [] if a == b else [f"{label}: {a!r} vs {b!r}"]


def _is(kit, error, kind):
    if kind == "type":
        return isinstance(error, TypeError)
    if kind == "research":
        return isinstance(error, kit.ResearchError) and not isinstance(error, (kit.BudgetExceeded, kit.HoldoutRefused))
    if kind == "budget":
        return isinstance(error, kit.BudgetExceeded)
    if kind == "holdout":
        return isinstance(error, kit.HoldoutRefused)
    raise AssertionError(kind)


def _outcome(call):
    try:
        call()
    except Exception as error:  # the error object is the outcome the test compares
        return error
    return None


def _refusal(kit, path, kind, call, label):
    """[] when call raises the kind and leaves the registry byte for byte as it was."""
    before = _snapshot(path)
    error = _outcome(call)
    wrong = [] if _is(kit, error, kind) else [f"{label}: expected {kind}, got {error!r}"]
    if _snapshot(path) != before:
        wrong.append(f"{label}: the registry changed")
    return wrong


# ----------------------------------------------------------------------------------- bars

def _m1(kit, row):
    stamp, open_, high, low, close, spread = row
    return kit.Bar(time_raw=_raw(stamp), time_utc=_utc(stamp), timeframe=1, open=Decimal(open_), high=Decimal(high),
                   low=Decimal(low), close=Decimal(close), spread=spread, tick_volume=1, m1_count=1)


def _m15(kit, m1, spreads=None, flags=None):
    """M15 AggregatedBar values from M1 grouped by timebase.bar_open (convention 6)."""
    groups = {}
    for bar in m1:
        groups.setdefault(kit.tb.bar_open(bar.time_raw, 15, kit.rule), []).append(bar)
    out = []
    for u, (opened, members) in enumerate(groups.items()):
        bar = kit.Bar(time_raw=opened, time_utc=kit.tb.to_utc(opened, kit.rule), timeframe=15, open=members[0].open,
                      high=max(item.high for item in members), low=min(item.low for item in members),
                      close=members[-1].close, spread=(spreads or {}).get(u, members[-1].spread),
                      tick_volume=len(members), m1_count=len(members))
        out.append(kit.snapshot.AggregatedBar(bar, frozenset((flags or {}).get(u, ()))))
    return tuple(out)


def _series(kit, kind):
    m1 = tuple(_m1(kit, row) for row in kit.g["m1_rows"](kind))
    return m1, _m15(kit, m1, kit.g["M15_SPREAD"], kit.g["M15_FLAGS"])


def _flat_row(stamp):
    return (stamp, "2000.00", "2000.50", "1999.50", "2000.00", 200)


def _small(kit, stamps):
    m1 = tuple(_m1(kit, _flat_row(stamp)) for stamp in stamps)
    return m1, _m15(kit, m1)


class _Sizer:
    """Lots 0.02, risk_money 25, actual_risk None, or lots None where lots_for(call index) says so."""

    def __init__(self, kit, lots_for=None, risk="25"):
        self.kit = kit
        self.lots_for = lots_for or (lambda index: "0.02")
        self.risk = Decimal(risk)
        self.calls = []

    def __call__(self, equity, stop_distance):
        lots = self.lots_for(len(self.calls))
        self.calls.append((equity, stop_distance))
        return self.kit.bt.SizedLots(lots=_dec(lots), risk_money=self.risk, actual_risk=None,
                                     reason="fixed" if lots is not None else "below_min_volume")


class _Raising:
    def __init__(self, error):
        self.error = error

    def __call__(self, equity, stop_distance):
        raise self.error


def _seam(monkeypatch, ac, fail=None):
    """Wrap sochron.research.registry.append_record; record each status, raise fail[status] if given."""
    module = _registry_module(monkeypatch, ac)
    original = getattr(module.append_record, "_seam_original", module.append_record)  # never wrap a wrapper
    written = []

    def append_record(path, record):
        written.append(record.status)
        error = (fail or {}).get(record.status)
        if error is not None:
            raise error
        return original(path, record)

    append_record._seam_original = original
    monkeypatch.setattr(module, "append_record", append_record)
    return written, module, original


# ----------------------------------------------------------------------------------- runner bench

class _Bench:
    """run_variant on the signal series with the normative setup; every input can be replaced."""

    def __init__(self, kit, path):
        self.kit = kit
        self.path = path
        self.m1, self.m15 = _series(kit, "signal")
        self.dataset = _dataset(kit, kit.g["SIGNAL_DATASET"])

    def model(self, purpose):
        return self.kit.costs.stress(self.kit.costs.H001_COSTS) if purpose == "stress" else self.kit.costs.H001_COSTS

    def run(self, purpose="select", *, m1=_DEFAULT, m15=_DEFAULT, params=_DEFAULT, model=_DEFAULT, sizer=_DEFAULT,
            equity=_DEFAULT, rule=_DEFAULT, rollover=_DEFAULT, dataset=_DEFAULT, code_commit=_DEFAULT,
            sizer_label=_DEFAULT, registry=_DEFAULT, base_run_id=None):
        kit = self.kit
        return kit.run_variant(
            _or(m1, self.m1), _or(m15, self.m15), _or(params, _run_params(kit)), _or(model, self.model(purpose)),
            _or(sizer, _Sizer(kit)), _or(equity, Decimal("10000")), _or(rule, kit.rule), _or(rollover, _rollover(kit)),
            purpose=purpose, dataset=_or(dataset, self.dataset), code_commit=_or(code_commit, kit.g["CODE_COMMIT"]),
            sizer_label=_or(sizer_label, kit.g["SIZER_LABEL"]), registry=_or(registry, self.path),
            base_run_id=base_run_id)

    def records(self):
        return self.kit.read_records(self.path)

    def append(self, purpose="select", *, status="started", params=None, base=None, model=None, dataset=None,
               hypothesis="H001", equity="10000"):
        """Append a started line exactly as run_variant writes it (and its failed line on request)."""
        seq = len(self.records()) + 1
        record = _rec(self.kit, seq=seq, purpose=purpose, params=params or _run_params(self.kit),
                      dataset=dataset or self.dataset, base=base, model=model or self.model(purpose),
                      hypothesis=hypothesis, equity=equity)
        self.kit.append_record(self.path, record)
        if status == "failed":
            self.kit.append_record(self.path, _result_of(self.kit, record, status="failed",
                                                         error="RuntimeError: interrupted run"))
        return record

    def append_ok(self, record, summary):
        ok = _result_of(self.kit, record, seq=len(self.records()) + 1, summary=summary)
        self.kit.append_record(self.path, ok)
        return ok


def _neighbour_params(kit, base_params, parameter, value):
    value = Decimal(value) if parameter in ("theta", "k") else value
    return replace(base_params, **{parameter: value})


# ----------------------------------------------------------------------------------- AC-01

def test_ac01_public_names_versions_errors_and_shapes(monkeypatch):
    kit = _kit(monkeypatch, "AC-01", "RESEARCH_VERSION", "HOLDOUT_CUTOFF_UTC", "Purpose", "USED_PARAMETERS",
               "BASELINE_RUNS", "BaselineResult", "Neighbour", "Check", "Evaluation", "summarize", "percentile",
               "run_variant", "random_entry_baseline", "neighbours", "evaluate", "render_report")
    registry = _registry_module(monkeypatch, "AC-01")
    wrong = []
    if kit.RESEARCH_VERSION != "research-v1" or type(kit.RESEARCH_VERSION) is not str:
        wrong.append(f"RESEARCH_VERSION {kit.RESEARCH_VERSION!r}")
    cutoff = kit.HOLDOUT_CUTOFF_UTC
    if type(cutoff) is not datetime or cutoff != datetime(2025, 1, 1, tzinfo=UTC) or cutoff.utcoffset() != timedelta(0):
        wrong.append(f"HOLDOUT_CUTOFF_UTC {cutoff!r}")
    if kit.BASELINE_RUNS != 1000 or type(kit.BASELINE_RUNS) is not int:
        wrong.append(f"BASELINE_RUNS {kit.BASELINE_RUNS!r}")
    if not issubclass(kit.ResearchError, ValueError):
        wrong.append("ResearchError is not a ValueError")
    for name in ("BudgetExceeded", "HoldoutRefused"):
        if not issubclass(getattr(kit, name), kit.ResearchError):
            wrong.append(f"{name} is not a ResearchError")
    if get_args(kit.Purpose) != ("select", "robustness", "stress", "long_only", "random_entry"):
        wrong.append(f"Purpose {get_args(kit.Purpose)}")
    used = {"A": ("f", "s", "n", "theta", "k"), "B": ("n", "N", "M", "k"), "C": ("f", "s", "n", "N", "M", "k")}
    if dict(kit.USED_PARAMETERS) != used:
        wrong.append(f"USED_PARAMETERS {kit.USED_PARAMETERS!r}")
    for name, shape in _SHAPES.items():
        kind = getattr(kit, name)
        if not is_dataclass(kind) or tuple(item.name for item in fields(kind)) != shape:
            wrong.append(f"{name} fields {[item.name for item in fields(kind)] if is_dataclass(kind) else kind}")
    if not is_dataclass(kit.RunRecord) or {item.name for item in fields(kit.RunRecord)} != _RECORD_FIELDS:
        names = {item.name for item in fields(kit.RunRecord)} if is_dataclass(kit.RunRecord) else set()
        wrong.append(f"RunRecord fields: missing {sorted(_RECORD_FIELDS - names)}, extra {sorted(names - _RECORD_FIELDS)}")
    if not isinstance(getattr(kit.RunRecord, "run_id", None), property):
        wrong.append("RunRecord.run_id is not a property")
    record = _rec(kit, seq=1)
    for target, attribute in ((record, "seq"), (record.dataset, "m1_bars")):
        try:
            setattr(target, attribute, 2)
            wrong.append(f"{type(target).__name__}.{attribute} can be assigned (not frozen)")
        except FrozenInstanceError:
            pass
    for name in ("append_record", "read_records", "summarize", "percentile", "run_variant", "random_entry_baseline",
                 "neighbours", "evaluate", "render_report"):
        if not callable(getattr(kit, name)):
            wrong.append(f"{name} is not callable")
    if not callable(registry.append_record):
        wrong.append("sochron.research.registry.append_record is not callable")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_the_normative_example_has_the_contract_bytes_run_id_and_hash(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    g = kit.g
    assert _cost_pairs(kit, kit.costs.H001_COSTS) == g["H001_COST_PAIRS"], "fixture: H001_COSTS record strings"
    assert _provenance_pairs(kit.costs.H001_COSTS) == g["H001_PROVENANCE_PAIRS"], "fixture: provenance pairs"
    record = _rec(kit, seq=1)
    line = record.line()
    expected = g["NORMATIVE_LINE"].encode("ascii") + b"\n"
    wrong = []
    if record.run_id != g["NORMATIVE_RUN_ID"] or type(record.run_id) is not str:
        wrong.append(f"run_id {record.run_id!r}, expected {g['NORMATIVE_RUN_ID']}")
    if type(line) is not bytes:
        wrong.append(f"line() is {type(line).__name__}, not bytes")
    elif line != expected:
        wrong.append(f"line() differs from the contract:\n{line!r}\n{expected!r}")
    if len(expected) != g["NORMATIVE_LINE_BYTES"] or hashlib.sha256(expected).hexdigest() != g["NORMATIVE_LINE_SHA256"]:
        wrong.append("fixture: the golden line does not have the contract's length and SHA-256")
    if type(line) is bytes and (len(line) != 1671 or hashlib.sha256(line).hexdigest() != g["NORMATIVE_LINE_SHA256"]):
        wrong.append(f"line() is {len(line)} bytes with SHA-256 {hashlib.sha256(line).hexdigest()}")
    path = tmp_path / "registry.jsonl"
    kit.append_record(path, record)
    if path.read_bytes() != expected:
        wrong.append(f"the file holds {path.read_bytes()!r}")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_append_two_more_records_and_read_back_values_and_types(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    g = kit.g
    path = tmp_path / "registry.jsonl"
    started = _rec(kit, seq=1)
    ok = _result_of(kit, started, summary=_summary(kit, g["OK_SUMMARY"]))
    second = _rec(kit, seq=3, params=_params(kit, "B", k="2.2"))
    wrong = []
    if ok.run_id != g["OK_RUN_ID"] or ok.line() != g["OK_LINE"].encode("ascii") + b"\n":
        wrong.append(f"the ok line differs from the golden one:\n{ok.line()!r}")
    written = b""
    for record in (started, ok, second):
        kit.append_record(path, record)
        written += record.line()
        if path.read_bytes() != written:
            wrong.append(f"after seq {record.seq} the file is not the earlier bytes plus the new line")
    if path.read_bytes().split(b"\n")[0] + b"\n" != g["NORMATIVE_LINE"].encode("ascii") + b"\n":
        wrong.append("the first line changed after the later appends")
    records = kit.read_records(path)
    if type(records) is not tuple:
        wrong.append(f"read_records returned a {type(records).__name__}")
    if [record.seq for record in records] != [1, 2, 3]:
        wrong.append(f"seq {[record.seq for record in records]}")
    for got, want in zip(records, (started, ok, second)):
        if got != want:
            wrong.append(f"seq {want.seq}: read back {got!r}")
        wrong += _same(got, want, f"seq {want.seq}")
        if got.run_id != want.run_id:
            wrong.append(f"seq {want.seq}: run_id {got.run_id}")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_a_random_entry_ok_line_with_its_baseline_summary(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    g = kit.g
    path = tmp_path / "registry.jsonl"
    started = _rec(kit, seq=1)
    ok = _result_of(kit, started, summary=_summary(kit, g["OK_SUMMARY"]))
    random_started = _rec(kit, seq=3, purpose="random_entry", base=ok.run_id)
    random_ok = _result_of(kit, random_started, baseline=_baseline(kit, g["RANDOM_BASELINE"], g["RANDOM_SEED"]))
    wrong = []
    if random_started.seed != g["RANDOM_SEED"] or g["RANDOM_SEED"] != int(g["OK_RUN_ID"][:15], 16):
        wrong.append(f"seed {random_started.seed}")
    if random_ok.run_id != g["RANDOM_RUN_ID"] or random_ok.line() != g["RANDOM_LINE"].encode("ascii") + b"\n":
        wrong.append(f"the random_entry ok line differs from the golden one:\n{random_ok.line()!r}")
    for record in (started, ok, random_started, random_ok):
        kit.append_record(path, record)
    records = kit.read_records(path)
    for got, want in zip(records, (started, ok, random_started, random_ok)):
        wrong += _same(got, want, f"seq {want.seq}")
    if len(records) != 4:
        wrong.append(f"{len(records)} records read back")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_a_missing_or_empty_registry_reads_as_no_records(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    for path in (tmp_path / "missing.jsonl", empty):
        records = kit.read_records(path)
        assert records == () and type(records) is tuple, f"AC-01: {path.name} read as {records!r}"
    assert not (tmp_path / "missing.jsonl").exists(), "AC-01: read_records created the file"


def test_ac01_a_torn_tail_names_its_byte_offset_and_blocks_append(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    first = _rec(kit, seq=1)
    ok = _result_of(kit, first, summary=_summary(kit, kit.g["OK_SUMMARY"]))
    wrong = []
    for label, lines, tail, nxt in (
        ("one line then a torn one", (first,), b'{"backtest_version":"backt', ok),
        ("two lines then a torn one", (first, ok), b'{"seq":3', _rec(kit, seq=3, params=_params(kit, "B", k="2.2"))),
    ):
        path = tmp_path / f"{len(lines)}.jsonl"
        content = b"".join(record.line() for record in lines) + tail
        path.write_bytes(content)
        offset = len(content) - len(tail)
        error = _outcome(lambda: kit.read_records(path))
        if not _is(kit, error, "research"):
            wrong.append(f"{label}: read_records gave {error!r}")
        elif not re.search(rf"(?<!\d){offset}(?!\d)", str(error)):
            wrong.append(f"{label}: the message does not name byte offset {offset}: {error}")
        wrong += _refusal(kit, path, "research", lambda: kit.append_record(path, nxt), f"{label}: append")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def _broken_registries(kit):
    """(label, file bytes, bad line number): every damaged-file case of the contract's read_records."""
    g = kit.g
    first = _rec(kit, seq=1)
    ok = _result_of(kit, first, summary=_summary(kit, g["OK_SUMMARY"]))
    one, two = first.line(), ok.line()
    other = _rec(kit, seq=1, params=_params(kit, "B", k="2.2"))
    cases = [
        ("a CR before the LF", one + two[:-1] + b"\r\n", 2),
        ("a CR inside the line", one + two.replace(b'"seq":2', b'"seq":2\r'), 2),
        ("a non-ASCII byte", one + two.replace(b"fixed-0.02", "fixed-0.0é".encode("utf-8")), 2),
        ("broken JSON", one + b'{"seq":2,\n', 2),
        ("an empty line", one + b"\n", 2),
        ("spaces after the separators", one + json.dumps(json.loads(two)).encode("ascii") + b"\n", 2),
        ("keys not sorted", one + json.dumps(dict(reversed(json.loads(two).items())), separators=(",", ":")).encode()
         + b"\n", 2),
        ("an escaped ASCII letter", one + two.replace(b'"variant":"B"', b'"variant":"\\u0042"'), 2),
        ("a seq gap", one + _result_of(kit, first, seq=3, summary=ok.summary).line(), 2),
        ("a repeated seq", one + other.line(), 2),
        ("seq not starting at 1", _rec(kit, seq=2).line(), 1),
        ("a forged run_id", one + two.replace(ok.run_id.encode(), b"0" * 64), 2),
        ("a missing field", one + _line_with(two, lambda obj: obj.pop("error")), 2),
        ("an extra field", one + _line_with(two, lambda obj: obj.update(note="x")), 2),
        ("a field of the wrong JSON type", one + _line_with(two, lambda obj: obj.update(seq="2")), 2),
        ("a float number", one + _line_with(two, lambda obj: obj.update(seq=2.0)), 2),
        ("a status outside the contract", one + _line_with(two, lambda obj: obj.update(status="done")), 2),
        ("a Decimal that is not a number", one + _line_with(two, lambda obj: obj.update(equity="ten")), 2),
        ("ok paired with a started line of another identity",
         one + _result_of(kit, other, seq=2, summary=ok.summary).line(), 2),
        ("a second result for one started line",
         one + two + _result_of(kit, first, seq=3, summary=ok.summary).line(), 3),
        ("a failed line paired with an ok line",
         one + two + replace(first, seq=3, status="failed", started_seq=2, error="RuntimeError: x").line(), 3),
        ("a failed line of another identity",
         one + replace(other, seq=2, status="failed", started_seq=1, error="RuntimeError: x").line(), 2),
    ]
    return cases


def test_ac01_every_damaged_line_is_refused_with_its_line_number(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    wrong = []
    for index, (label, content, number) in enumerate(_broken_registries(kit)):
        path = tmp_path / f"broken-{index}.jsonl"
        path.write_bytes(content)
        error = _outcome(lambda: kit.read_records(path))
        if not _is(kit, error, "research"):
            wrong.append(f"{label}: read_records gave {error!r}")
        elif not re.search(rf"(?<!\d){number}(?!\d)", str(error)):
            wrong.append(f"{label}: the message does not name line {number}: {error}")
        nxt = _rec(kit, seq=content.count(b"\n") + 1, params=_params(kit, "B", k="2.4"))
        wrong += _refusal(kit, path, "research", lambda: kit.append_record(path, nxt), f"{label}: append")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_append_refuses_records_that_do_not_continue_the_file(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    path = tmp_path / "registry.jsonl"
    first = _rec(kit, seq=1)
    kit.append_record(path, first)
    summary = _summary(kit, kit.g["OK_SUMMARY"])
    other = _rec(kit, seq=2, params=_params(kit, "B", k="2.2"))
    wrong = []
    for label, record in (
        ("seq 3 after one line", _rec(kit, seq=3)),
        ("seq 1 again", _rec(kit, seq=1, params=_params(kit, "B", k="2.2"))),
        ("ok paired with a started line of another identity", replace(other, status="ok", started_seq=1,
                                                                      summary=summary)),
        ("failed paired with a started line of another identity", replace(other, status="failed", started_seq=1,
                                                                          error="RuntimeError: x")),
    ):
        wrong += _refusal(kit, path, "research", lambda: kit.append_record(path, record), label)
    ok = _result_of(kit, first, summary=summary)
    kit.append_record(path, ok)
    for label, record in (
        ("a second ok for the same started line", _result_of(kit, first, seq=3, summary=summary)),
        ("a failed line for a started line that has its ok", _result_of(kit, first, seq=3, status="failed",
                                                                        error="RuntimeError: x")),
        ("a failed line paired with the ok line", replace(first, seq=3, status="failed", started_seq=2,
                                                          error="RuntimeError: x")),
    ):
        wrong += _refusal(kit, path, "research", lambda: kit.append_record(path, record), label)
    for name in ("registry.json", "registry.jsonl.txt", "registry"):
        target = tmp_path / name
        wrong += _refusal(kit, target, "research", lambda: kit.append_record(target, _rec(kit, seq=1)),
                          f"path {name}")
        if target.exists():
            wrong.append(f"path {name}: the file was created")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_wrong_types_are_type_errors_and_write_nothing(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    path = tmp_path / "registry.jsonl"
    record = _rec(kit, seq=1)
    wrong = []
    for label, call in (
        ("a str path", lambda: kit.append_record(str(path), record)),
        ("a None path", lambda: kit.append_record(None, record)),
        ("a dict record", lambda: kit.append_record(path, {"seq": 1})),
        ("a None record", lambda: kit.append_record(path, None)),
        ("read_records with a str path", lambda: kit.read_records(str(path))),
        ("read_records with None", lambda: kit.read_records(None)),
    ):
        wrong += _refusal(kit, path, "type", call, label)
    assert not path.exists(), "AC-01: a refused call created the registry"
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_filesystem_errors_reach_the_caller_unwrapped(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-01")
    record = _rec(kit, seq=1)
    folder = tmp_path / "folder.jsonl"
    folder.mkdir()
    wrong = []
    for label, call in (
        ("append under a missing directory", lambda: kit.append_record(tmp_path / "no" / "registry.jsonl", record)),
        ("append to a directory", lambda: kit.append_record(folder, record)),
        ("read a directory", lambda: kit.read_records(folder)),
    ):
        error = _outcome(call)
        if not isinstance(error, OSError) or isinstance(error, kit.ResearchError):
            wrong.append(f"{label}: expected the OSError itself, got {error!r}")
    if not folder.is_dir() or any(folder.iterdir()):
        wrong.append("the directory was changed")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def _record_cases(kit):
    """(label, fields builder, expected kind): every RunRecord.__post_init__ check of the contract (F36)."""
    g = kit.g
    summary = _summary(kit, g["OK_SUMMARY"])
    base = g["OK_RUN_ID"]
    started = _fields(kit, seq=1)
    ok = {**started, "seq": 2, "status": "ok", "started_seq": 1, "summary": summary}
    failed = {**started, "seq": 2, "status": "failed", "started_seq": 1, "error": "RuntimeError: x"}
    random_ok = {**_fields(kit, seq=4, status="ok", started_seq=3, purpose="random_entry", base=base),
                 "baseline": _baseline(kit, g["RANDOM_BASELINE"], g["RANDOM_SEED"])}
    robust = _fields(kit, seq=3, purpose="robustness", base=base, params=_params(kit, "B", n=18))
    long_only = _fields(kit, seq=3, purpose="long_only", base=base)
    pairs = list(started["params"])
    costs = list(started["cost_model"])
    provenance = list(started["cost_provenance"])
    return (
        ("status outside the set", {**started, "status": "done"}, "research"),
        ("purpose outside the set", {**started, "purpose": "train"}, "research"),
        ("variant outside the set", {**started, "variant": "D"}, "research"),
        ("seq 0", {**started, "seq": 0}, "research"),
        ("started with a started_seq", {**started, "seq": 2, "started_seq": 1}, "research"),
        ("ok without started_seq", {**ok, "started_seq": None}, "research"),
        ("ok with started_seq = seq", {**ok, "started_seq": 2}, "research"),
        ("ok with started_seq > seq", {**ok, "started_seq": 3}, "research"),
        ("select with a base_run_id", {**started, "base_run_id": base}, "research"),
        ("robustness without base_run_id", {**robust, "base_run_id": None}, "research"),
        ("base_run_id of 63 hex", {**robust, "base_run_id": base[:63]}, "research"),
        ("base_run_id in upper case", {**robust, "base_run_id": base.upper()}, "research"),
        ("random_entry with runs 999", {**random_ok, "runs": 999}, "research"),
        ("random_entry with another seed", {**random_ok, "seed": g["RANDOM_SEED"] + 1}, "research"),
        ("random_entry without seed", {**random_ok, "seed": None}, "research"),
        ("select with a seed", {**started, "seed": 7}, "research"),
        ("select with runs", {**started, "runs": 1000}, "research"),
        ("started with an error", {**started, "error": "RuntimeError: x"}, "research"),
        ("failed without an error", {**failed, "error": None}, "research"),
        ("ok with an error", {**ok, "error": "RuntimeError: x"}, "research"),
        ("started with a summary", {**started, "summary": summary}, "research"),
        ("select ok without a summary", {**ok, "summary": None}, "research"),
        ("select ok with a baseline", {**ok, "baseline": random_ok["baseline"]}, "research"),
        ("random_entry ok with a summary", {**random_ok, "summary": summary}, "research"),
        ("random_entry ok without a baseline", {**random_ok, "baseline": None}, "research"),
        ("failed with a summary", {**failed, "summary": summary}, "research"),
        ("code_commit of 39 hex", {**started, "code_commit": g["CODE_COMMIT"][:39]}, "research"),
        ("code_commit in upper case", {**started, "code_commit": g["CODE_COMMIT"].upper()}, "research"),
        ("code_commit not hex", {**started, "code_commit": "g" * 40}, "research"),
        ("empty hypothesis", {**started, "hypothesis": ""}, "research"),
        ("non-ASCII hypothesis", {**started, "hypothesis": "H00๑"}, "research"),
        ("a params name changed", {**started, "params": (("F", "16"), *pairs[1:])}, "research"),
        ("params out of order", {**started, "params": (pairs[1], pairs[0], *pairs[2:])}, "research"),
        ("params without k", {**started, "params": tuple(pairs[:-1])}, "research"),
        ("cost_model out of order", {**started, "cost_model": (costs[1], costs[0], *costs[2:])}, "research"),
        ("cost_model without stress_factor", {**started, "cost_model": tuple(costs[:-1])}, "research"),
        ("cost_provenance not sorted", {**started, "cost_provenance": (provenance[1], provenance[0],
                                                                       *provenance[2:])}, "research"),
        ("equity 0", {**started, "equity": Decimal("0")}, "research"),
        ("equity below 0", {**started, "equity": Decimal("-1")}, "research"),
        *((f"equity {text}", {**started, "equity": Decimal(text)}, "research") for text in _NON_FINITE),
        ("empty sizer_label", {**started, "sizer_label": ""}, "research"),
        ("non-ASCII sizer_label", {**started, "sizer_label": "fixed-0.0๒"}, "research"),
        ("non-ASCII error", {**failed, "error": "RuntimeError: ข"}, "research"),
        ("rollover_at 1700", {**started, "rollover_at": "1700"}, "research"),
        ("rollover_at 17:0", {**started, "rollover_at": "17:0"}, "research"),
        ("rollover_at 7:00", {**started, "rollover_at": "7:00"}, "research"),
        ("select with sides long only", {**started, "sides": ("long",)}, "research"),
        ("long_only with both sides", {**long_only, "sides": ("long", "short")}, "research"),
        ("sides not sorted", {**started, "sides": ("short", "long")}, "research"),
        ("seq as bool", {**started, "seq": True}, "type"),
        ("seq as str", {**started, "seq": "1"}, "type"),
        ("seq as float", {**started, "seq": 1.0}, "type"),
        ("started_seq as str", {**ok, "started_seq": "1"}, "type"),
        ("params as a list", {**started, "params": list(started["params"])}, "type"),
        ("a params value as Decimal", {**started, "params": (("f", Decimal("16")), *pairs[1:])}, "type"),
        ("a params pair as a list", {**started, "params": (["f", "16"], *pairs[1:])}, "type"),
        ("cost_model as a list", {**started, "cost_model": list(costs)}, "type"),
        ("sides as a list", {**started, "sides": ["long", "short"]}, "type"),
        ("equity as str", {**started, "equity": "10000"}, "type"),
        ("equity as int", {**started, "equity": 10000}, "type"),
        ("equity as float", {**started, "equity": 10000.0}, "type"),
        ("dataset as a tuple", {**started, "dataset": g["NORMATIVE_DATASET"]}, "type"),
        ("summary as a dict", {**ok, "summary": dict(g["OK_SUMMARY"])}, "type"),
        ("baseline as a dict", {**random_ok, "baseline": dict(g["RANDOM_BASELINE"])}, "type"),
        ("hypothesis None", {**started, "hypothesis": None}, "type"),
        ("sizer_label None", {**started, "sizer_label": None}, "type"),
        ("code_commit None", {**started, "code_commit": None}, "type"),
        ("status None", {**started, "status": None}, "type"),
        ("seed as str", {**random_ok, "seed": str(g["RANDOM_SEED"])}, "type"),
    )


def test_ac01_run_record_checks_every_field_the_contract_lists(monkeypatch):
    kit = _kit(monkeypatch, "AC-01")
    wrong = []
    for label, values, kind in _record_cases(kit):
        error = _outcome(lambda: kit.RunRecord(**values))
        if not _is(kit, error, kind):
            wrong.append(f"{label}: expected {kind}, got {error!r}")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_dataset_summary_and_baseline_summary_check_themselves(monkeypatch):
    kit = _kit(monkeypatch, "AC-01")
    g = kit.g
    spec = g["NORMATIVE_DATASET"]
    wrong = []
    for label, changes, kind in (
        ("snapshot_id None", {"snapshot_id": None}, "type"),
        ("snapshot_id int", {"snapshot_id": 1}, "type"),
        ("manifest None", {"manifest_sha256": None}, "type"),
        ("start as a date", {"period_start_utc": date(2023, 1, 2)}, "type"),
        ("start as str", {"period_start_utc": "2023-01-02T00:00:00Z"}, "type"),
        ("m1_bars as str", {"m1_bars": "7200"}, "type"),
        ("m1_bars as bool", {"m1_bars": True}, "type"),
        ("m1_bars as float", {"m1_bars": 7200.0}, "type"),
        ("empty snapshot_id", {"snapshot_id": ""}, "research"),
        ("manifest of 63 hex", {"manifest_sha256": "a" * 63}, "research"),
        ("manifest in upper case", {"manifest_sha256": "A" * 64}, "research"),
        ("manifest not hex", {"manifest_sha256": "g" * 64}, "research"),
        ("naive start", {"period_start_utc": datetime(2023, 1, 2)}, "research"),
        ("naive end", {"period_end_utc": datetime(2023, 1, 7)}, "research"),
        ("start at +07:00", {"period_start_utc": datetime(2023, 1, 2, 7, tzinfo=timezone(timedelta(hours=7)))},
         "research"),
        ("start with microseconds", {"period_start_utc": datetime(2023, 1, 2, 0, 0, 0, 1, tzinfo=UTC)}, "research"),
        ("start = end", {"period_end_utc": datetime(2023, 1, 2, tzinfo=UTC)}, "research"),
        ("start > end", {"period_end_utc": datetime(2023, 1, 1, tzinfo=UTC)}, "research"),
        ("m1_bars 0", {"m1_bars": 0}, "research"),
        ("m1_bars below 0", {"m1_bars": -1}, "research"),
    ):
        error = _outcome(lambda: _dataset(kit, spec, **changes))
        if not _is(kit, error, kind):
            wrong.append(f"Dataset {label}: expected {kind}, got {error!r}")
    summary = g["OK_SUMMARY"]
    for label, changes in (
        ("trades as bool", {"trades": True}), ("expectancy as float", {"expectancy_r": 0.5}),
        ("expectancy as str", {"expectancy_r": "0.5"}), ("max_drawdown None", {"max_drawdown_r": None}),
        ("expectancy_by_year as a list", {"expectancy_by_year": [(2023, Decimal("0.5"))]}),
        ("a year as str", {"expectancy_by_year": (("2023", Decimal("0.5")),)}),
        ("a year value as float", {"expectancy_by_year": ((2023, 0.5),)}),
        ("gap_fills as Decimal", {"gap_fills": Decimal("0")}),
    ):
        values = {name: (Decimal(value) if isinstance(value, str) else value) for name, value in summary.items()}
        values["expectancy_by_year"] = ((2023, Decimal("0.5")),)
        values.update(changes)
        error = _outcome(lambda: kit.Summary(**values))
        if not isinstance(error, TypeError):
            wrong.append(f"Summary {label}: expected TypeError, got {error!r}")
    for label, changes in (
        ("seed as str", {"seed": "7"}), ("mean as float", {"mean_r": -0.024}), ("p95 None", {"p95_r": None}),
        ("median hold as Decimal", {"variant_median_hold_m1": Decimal("0")}), ("runs as bool", {"runs": True}),
    ):
        error = _outcome(lambda: _baseline(kit, g["RANDOM_BASELINE"], 7, **changes))
        if not isinstance(error, TypeError):
            wrong.append(f"BaselineSummary {label}: expected TypeError, got {error!r}")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-02

def test_ac02_every_purpose_writes_started_then_ok_with_every_field(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant", "summarize")
    written, _, _ = _seam(monkeypatch, "AC-02")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    params = _run_params(kit)
    neighbour = _run_params(kit, N=53)  # RUN_NEIGHBOURS["B"]: N 48 x 1.1 = 52.8 -> 53
    wrong = []
    base_id = None
    for purpose, run_params in (("select", params), ("robustness", neighbour), ("stress", params),
                                ("long_only", params)):
        before = len(bench.records())
        sizer = _Sizer(kit)
        record, result = bench.run(purpose, params=run_params, sizer=sizer, base_run_id=base_id)
        sides = frozenset({"long"}) if purpose == "long_only" else frozenset({"long", "short"})
        expected_result = kit.bt.run(bench.m1, bench.m15, run_params, bench.model(purpose), _Sizer(kit),
                                     Decimal("10000"), kit.rule, _rollover(kit), sides=sides)
        if len(expected_result.trades) != 1:
            wrong.append(f"fixture: {purpose} on the signal series makes {len(expected_result.trades)} trades")
        if result != expected_result:
            wrong.append(f"{purpose}: the result is not backtest.run of the same inputs")
        expected = _rec(kit, seq=before + 1, purpose=purpose, params=run_params, dataset=bench.dataset,
                        base=base_id, model=bench.model(purpose))
        expected_ok = _result_of(kit, expected, summary=kit.summarize(expected_result, kit.rule))
        records = bench.records()
        if len(records) != before + 2:
            wrong.append(f"{purpose}: {len(records) - before} new lines, expected 2")
            continue
        if records[-2].line() != expected.line():
            wrong.append(f"{purpose}: started line\n{records[-2]!r}\nexpected\n{expected!r}")
        if records[-1].line() != expected_ok.line():
            wrong.append(f"{purpose}: ok line\n{records[-1]!r}\nexpected\n{expected_ok!r}")
        if record != records[-1] or record.line() != records[-1].line():
            wrong.append(f"{purpose}: the returned record is not the ok line")
        if purpose == "select":
            base_id = record.run_id
    if written != ["started", "ok"] * 4:
        wrong.append(f"writes through sochron.research.registry.append_record: {written}")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_an_exception_after_the_started_line_writes_failed_and_raises_the_same_object(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    wrong = []
    disk_full = OSError("disk full")
    cases = (
        ("the sizer raises", _Raising(_SizerFailure("ขาด")), {}, "_SizerFailure: ???"),
        ("KeyboardInterrupt inside the backtest", _Raising(KeyboardInterrupt()), {}, "KeyboardInterrupt: "),
        ("lots off the grid (costs.BadVolume)", _Sizer(kit, lots_for=lambda index: "0.015"), {}, None),
        ("the ok line cannot be written", _Sizer(kit), {"ok": disk_full}, "OSError: disk full"),
    )
    for index, (label, sizer, fail, text) in enumerate(cases):
        written, _, _ = _seam(monkeypatch, "AC-02", fail)
        bench = _Bench(kit, tmp_path / f"failure-{index}.jsonl")
        raised = None
        try:
            bench.run(sizer=sizer)
        except BaseException as error:  # KeyboardInterrupt included: the contract re-raises it
            raised = error
        expected_error = getattr(sizer, "error", None) or fail.get("ok")
        if expected_error is not None and raised is not expected_error:
            wrong.append(f"{label}: raised {raised!r}, not the original object")
        if expected_error is None and type(raised) is not kit.costs.BadVolume:
            wrong.append(f"{label}: raised {raised!r}, expected costs.BadVolume unwrapped")
        records = bench.records()
        started = _rec(kit, seq=1, params=_run_params(kit), dataset=bench.dataset)
        if raised is not None:
            failed = _result_of(kit, started, status="failed", error=_error_text(raised))
            if [record.line() for record in records] != [started.line(), failed.line()]:
                wrong.append(f"{label}: registry {records!r}")
            if text is not None and records and records[-1].error != text:
                wrong.append(f"{label}: error {records[-1].error!r}, expected {text!r}")
        expected_writes = ["started", "ok", "failed"] if fail else ["started", "failed"]
        if written != expected_writes:
            wrong.append(f"{label}: writes {written}, expected {expected_writes}")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_when_the_failed_line_also_fails_the_first_error_is_raised_and_a_rerun_is_accepted(monkeypatch,
                                                                                                  tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    first, second = OSError("disk full"), OSError("still full")
    written, module, original = _seam(monkeypatch, "AC-02", {"ok": first, "failed": second})
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    raised = _outcome(lambda: bench.run())
    started = _rec(kit, seq=1, params=_run_params(kit), dataset=bench.dataset)
    wrong = []
    if raised is not first:
        wrong.append(f"raised {raised!r}, not the first error")
    if written != ["started", "ok", "failed"]:
        wrong.append(f"writes {written}")
    if [record.line() for record in bench.records()] != [started.line()]:
        wrong.append(f"registry {bench.records()!r}, expected the started line only (interrupted)")
    monkeypatch.setattr(module, "append_record", original)
    record, _ = bench.run()
    rerun = replace(started, seq=2)
    if [item.line() for item in bench.records()[1:]] != [rerun.line(), _result_of(kit, rerun, summary=record.summary).line()]:
        wrong.append(f"the rerun after an interrupted run wrote {bench.records()[1:]!r}")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_the_holdout_guard_comes_before_every_other_check(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    g = kit.g
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    edge_m1, edge_m15 = _small(kit, g["EDGE_M1"])
    at_m1, at_m15 = _small(kit, g["EDGE_M1"] + (g["AT_CUTOFF"],))
    after_m1, after_m15 = _small(kit, (g["AFTER_CUTOFF"],))
    cutoff_bar = _m15(kit, (_m1(kit, _flat_row(g["AT_CUTOFF"])),))
    edge = _dataset(kit, g["EDGE_DATASET"])
    late_end = _dataset(kit, g["EDGE_DATASET"], period_end_utc=_utc(g["CUTOFF"]) + timedelta(seconds=1))
    wrong = []
    for label, changes in (
        ("an M1 at the cutoff (the Dataset is wrong too: count and period)", {"m1": at_m1, "m15": at_m15}),
        ("an M1 at the cutoff with every other input wrong",
         {"m1": at_m1, "m15": at_m15, "code_commit": "XYZ", "sizer_label": "", "purpose": "random_entry",
          "registry": tmp_path / "registry.json", "base_run_id": "f" * 64}),
        ("an M1 at the cutoff and no Dataset", {"m1": at_m1, "m15": at_m15, "dataset": None}),
        ("an M15 bar at the cutoff without M1", {"m1": edge_m1, "m15": edge_m15 + cutoff_bar}),
        ("an M1 after the cutoff", {"m1": after_m1, "m15": after_m15}),
        ("a Dataset that ends 1 s after the cutoff", {"m1": edge_m1, "m15": edge_m15, "dataset": late_end}),
    ):
        purpose = changes.pop("purpose", "select")
        call = lambda: bench.run(purpose, **{"dataset": edge, **changes})  # noqa: E731
        wrong += _refusal(kit, bench.path, "holdout", call, label)
        wrong += _refusal(kit, tmp_path / "registry.json", "holdout", call, f"{label} (other path)")
    record, _ = bench.run(m1=edge_m1, m15=edge_m15, dataset=edge)
    if [item.status for item in bench.records()] != ["started", "ok"]:
        wrong.append("the last M1 before the cutoff with a Dataset ending at the cutoff was refused")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def _inconsistent_series(kit, bench):
    """(label, m1, m15): each breaks one item of the CORE-007 input checks; the Dataset count follows len(m1)."""
    m1, m15 = list(bench.m1), list(bench.m15)

    def m1_with(index, **changes):
        out = list(m1)
        out[index] = replace(m1[index], **changes)
        return tuple(out)

    def m15_with(index, **changes):
        out = list(m15)
        out[index] = kit.snapshot.AggregatedBar(replace(m15[index].bar, **changes), m15[index].flags)
        return tuple(out)

    swapped = list(m1)
    swapped[10], swapped[11] = swapped[11], swapped[10]
    swapped15 = list(m15)
    swapped15[10], swapped15[11] = swapped15[11], swapped15[10]
    return (
        ("an M15 bar without M1", tuple(m1[:150] + m1[153:]), tuple(m15)),
        ("an M1 outside every M15 bar", tuple(m1), tuple(m15[:50] + m15[51:])),
        ("an M1 of timeframe 5", m1_with(10, timeframe=5), tuple(m15)),
        ("M1 times not increasing", tuple(swapped), tuple(m15)),
        ("an M1 time_utc not from the rule", m1_with(10, time_utc=m1[10].time_utc + timedelta(minutes=1)), tuple(m15)),
        ("an M15 bar of timeframe 5", tuple(m1), m15_with(10, timeframe=5)),
        ("M15 times not increasing", tuple(m1), tuple(swapped15)),
        ("an M15 time_utc not from the rule", tuple(m1), m15_with(10, time_utc=m15[10].bar.time_utc + timedelta(minutes=1))),
        ("an M1 with a negative spread", m1_with(10, spread=-1), tuple(m15)),
        ("an M1 with high below low", m1_with(10, high=Decimal("1999.00"), low=Decimal("2000.00")), tuple(m15)),
        ("an M1 opening above its high", m1_with(10, open=Decimal("2001.00")), tuple(m15)),
        ("an M1 closing below its low", m1_with(10, close=Decimal("1999.00")), tuple(m15)),
        ("an M1 with a price of 0", m1_with(10, low=Decimal("0")), tuple(m15)),
        ("no M15 bar", tuple(m1), ()),
    )


def test_ac02_inputs_are_checked_before_any_line(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    stress = kit.costs.stress
    wrong = []
    for label, purpose, changes in (
        ("purpose random_entry", "random_entry", {"base_run_id": "f" * 64}),
        ("purpose outside Purpose", "train", {}),
        ("stress with stress_factor 1", "stress", {"model": kit.costs.H001_COSTS, "base_run_id": "f" * 64}),
        ("select with stress_factor 2", "select", {"model": stress(kit.costs.H001_COSTS)}),
        ("stress with stress_factor 2.0", "stress", {"model": stress(kit.costs.H001_COSTS, Decimal("2.0")),
                                                     "base_run_id": "f" * 64}),
        ("select with stress_factor 1.0", "select", {"model": replace(kit.costs.H001_COSTS, stress_factor=Decimal("1.0"))}),
        ("code_commit of 39 hex", "select", {"code_commit": kit.g["CODE_COMMIT"][:39]}),
        ("code_commit in upper case", "select", {"code_commit": kit.g["CODE_COMMIT"].upper()}),
        ("empty sizer_label", "select", {"sizer_label": ""}),
        ("non-ASCII sizer_label", "select", {"sizer_label": "fixed-0.0๒"}),
        ("Dataset count is not len(m1)", "select", {"dataset": _dataset(kit, kit.g["SIGNAL_DATASET"], m1_bars=314)}),
        ("an M1 before the Dataset start", "select",
         {"dataset": _dataset(kit, kit.g["SIGNAL_DATASET"], period_start_utc=_utc("2024-01-08T08:00:00"))}),
        ("an M1 at the Dataset end (exclusive)", "select",
         {"dataset": _dataset(kit, kit.g["SIGNAL_DATASET"], period_end_utc=bench.m1[-1].time_utc)}),
        ("equity 0", "select", {"equity": Decimal("0")}),
        ("equity NaN", "select", {"equity": Decimal("NaN")}),
        ("a registry path that is not .jsonl", "select", {"registry": tmp_path / "registry.json"}),
        ("select with a base_run_id", "select", {"base_run_id": "f" * 64}),
    ):
        wrong += _refusal(kit, bench.path, "research", lambda: bench.run(purpose, **changes), label)
    for label, m1, m15 in _inconsistent_series(kit, bench):
        dataset = _dataset(kit, kit.g["SIGNAL_DATASET"], m1_bars=max(len(m1), 1))
        wrong += _refusal(kit, bench.path, "research", lambda: bench.run(m1=m1, m15=m15, dataset=dataset), label)
    assert not bench.path.exists(), "AC-02: a refused run created the registry"
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_wrong_types_are_type_errors_before_any_line(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    wrong = []
    for label, changes in (
        ("m1 as a generator", {"m1": (bar for bar in bench.m1)}),
        ("an AggregatedBar among the M1", {"m1": (bench.m15[0],) + bench.m1[1:]}),
        ("a Bar among the M15", {"m15": (bench.m1[0],) + bench.m15[1:]}),
        ("params as a dict", {"params": dict(kit.g["RUN_PARAMS"])}),
        ("model None", {"model": None}),
        ("a sizer that is not callable", {"sizer": "fixed"}),
        ("equity as int", {"equity": 10000}),
        ("equity as float", {"equity": 10000.0}),
        ("rule None", {"rule": None}),
        ("rollover None", {"rollover": None}),
        ("dataset None", {"dataset": None}),
        ("code_commit None", {"code_commit": None}),
        ("sizer_label None", {"sizer_label": None}),
        ("registry as str", {"registry": str(bench.path)}),
        ("base_run_id as int", {"base_run_id": 5}),
    ):
        wrong += _refusal(kit, bench.path, "type", lambda: bench.run(**changes), label)
    wrong += _refusal(kit, bench.path, "type", lambda: bench.run(1), "purpose as int")
    assert not bench.path.exists(), "AC-02: a refused run created the registry"
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_the_base_and_every_field_evaluate_compares_must_match_as_record_strings(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    base, _ = bench.run()
    base_started = bench.records()[0]
    failed = bench.append(params=_run_params(kit, k="2.9"), status="failed")
    a_base, _ = bench.run(params=_run_params(kit, "A"))
    h002 = bench.append(params=_run_params(kit, k="2.8"), hypothesis="H002")
    h002_ok = bench.append_ok(h002, base.summary)
    n53 = _run_params(kit, N=53)
    slip = replace(kit.costs.H001_COSTS, slippage_points_per_side=20)
    wrong = []
    for label, purpose, changes in (
        ("robustness without a base", "robustness", {"params": n53}),
        ("robustness on an unknown base", "robustness", {"params": n53, "base_run_id": "f" * 64}),
        ("robustness on the base's started line", "robustness", {"params": n53, "base_run_id": base_started.run_id}),
        ("robustness on a failed select", "robustness", {"params": n53, "base_run_id": bench.records()[3].run_id}),
        ("robustness on an H002 select", "robustness", {"params": n53, "base_run_id": h002_ok.run_id}),
        ("robustness of variant A on the B base", "robustness",
         {"params": _run_params(kit, "A", f=9), "base_run_id": base.run_id}),
        ("robustness with the base's own params", "robustness", {"params": _run_params(kit), "base_run_id": base.run_id}),
        ("robustness k 2.7 (the neighbour is 2.70)", "robustness",
         {"params": _run_params(kit, k="2.7"), "base_run_id": base.run_id}),
        ("robustness on theta, which V-B does not use", "robustness",
         {"params": _run_params(kit, theta="0.450"), "base_run_id": base.run_id}),
        ("stress with other params", "stress", {"params": _run_params(kit, k="2.9"), "base_run_id": base.run_id}),
        ("long_only with other params", "long_only", {"params": n53, "base_run_id": base.run_id}),
        ("robustness on another dataset", "robustness",
         {"params": n53, "base_run_id": base.run_id, "dataset": _dataset(kit, kit.g["SIGNAL_DATASET_2"])}),
        ("robustness with another code_commit", "robustness",
         {"params": n53, "base_run_id": base.run_id, "code_commit": kit.g["OTHER_COMMIT"]}),
        ("robustness with another sizer_label", "robustness",
         {"params": n53, "base_run_id": base.run_id, "sizer_label": "fixed-0.03"}),
        ("robustness with another equity", "robustness",
         {"params": n53, "base_run_id": base.run_id, "equity": Decimal("20000")}),
        ("robustness with equity 1E+4 (a different record string)", "robustness",
         {"params": n53, "base_run_id": base.run_id, "equity": Decimal("1E+4")}),
        ("robustness with another rollover", "robustness",
         {"params": n53, "base_run_id": base.run_id, "rollover": _rollover(kit, hour=18)}),
        ("robustness under another time rule", "robustness",
         {"params": n53, "base_run_id": base.run_id, "rule": _other_rule(kit)}),
        ("robustness with slippage 20", "robustness", {"params": n53, "base_run_id": base.run_id, "model": slip}),
        ("stress with slippage 20", "stress", {"base_run_id": base.run_id, "model": kit.costs.stress(slip)}),
        ("robustness of theta 0.45 on the A base (the neighbour is 0.450)", "robustness",
         {"params": _run_params(kit, "A", theta="0.45"), "base_run_id": a_base.run_id}),
    ):
        wrong += _refusal(kit, bench.path, "research", lambda: bench.run(purpose, **changes), label)
    if failed.status != "started":
        wrong.append("fixture: the failed select")
    for label, purpose, params, base_id in (
        ("robustness k 2.70", "robustness", _run_params(kit, k="2.70"), base.run_id),
        ("robustness theta 0.450 on the A base", "robustness", _run_params(kit, "A", theta="0.450"), a_base.run_id),
    ):
        try:
            record, _ = bench.run(purpose, params=params, base_run_id=base_id)
            if record.status != "ok":
                wrong.append(f"{label}: {record!r}")
        except Exception as error:  # the case must be accepted
            wrong.append(f"{label} was refused: {error!r}")
    stress_ok, _ = bench.run("stress", base_run_id=base.run_id)
    wrong += _refusal(kit, bench.path, "research",
                      lambda: bench.run("long_only", base_run_id=stress_ok.run_id), "long_only on a stress record")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_the_first_started_line_of_the_hypothesis_fixes_the_setup_of_the_file(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    bench.run()
    model = kit.costs.H001_COSTS
    unknown_point = dict(model.provenance)
    unknown_point["point"] = replace(unknown_point["point"], status="unknown")
    other = _run_params(kit, k="2.9")
    wrong = []
    for label, changes in (
        ("the same params with slippage 20",
         {"params": _run_params(kit), "model": replace(model, slippage_points_per_side=20)}),
        ("slippage 20", {"params": other, "model": replace(model, slippage_points_per_side=20)}),
        ("another equity", {"params": other, "equity": Decimal("20000")}),
        ("another rollover", {"params": other, "rollover": _rollover(kit, hour=18)}),
        ("another code_commit", {"params": other, "code_commit": kit.g["OTHER_COMMIT"]}),
        ("another sizer_label", {"params": other, "sizer_label": "fixed-0.03"}),
        ("another time rule", {"params": other, "rule": _other_rule(kit)}),
        ("another provenance", {"params": other, "model": replace(model, provenance=unknown_point)}),
    ):
        wrong += _refusal(kit, bench.path, "budget", lambda: bench.run(**changes), label)
    try:
        bench.run(params=other)
    except Exception as error:  # the same setup with new params is a new select
        wrong.append(f"new params with the same setup were refused: {error!r}")
    second = _Bench(kit, tmp_path / "mixed.jsonl")
    second.append(params=_run_params(kit, k="2.8"), hypothesis="H002", equity="5000")
    try:
        second.run()
    except Exception as error:  # another hypothesis's line does not fix H001's setup
        wrong.append(f"an H002 line fixed the setup of H001: {error!r}")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_a_rerun_is_refused_after_ok_and_accepted_after_an_interrupted_or_failed_run(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    base, _ = bench.run()
    wrong = _refusal(kit, bench.path, "budget", lambda: bench.run(), "select of the same identity after ok")
    for label, status, k in (("interrupted", "started", "2.9"), ("failed", "failed", "2.8")):
        params = _run_params(kit, k=k)
        bench.append(params=params, status=status)
        before = len(bench.records())
        try:
            record, _ = bench.run(params=params)
        except Exception as error:  # a rerun of a run without ok must be accepted
            wrong.append(f"rerun after an {label} select was refused: {error!r}")
            continue
        records = bench.records()
        if len(records) != before + 2 or records[-1].started_seq != before + 1 or record != records[-1]:
            wrong.append(f"rerun after an {label} select: {records[before:]!r}")
    for purpose, params in (("robustness", _run_params(kit, N=53)), ("stress", _run_params(kit)),
                            ("long_only", _run_params(kit))):
        bench.run(purpose, params=params, base_run_id=base.run_id)
        wrong += _refusal(kit, bench.path, "budget", lambda: bench.run(purpose, params=params, base_run_id=base.run_id),
                          f"{purpose} again after its ok")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_select_counts_six_distinct_params_per_variant(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    for k in ("3.0", "2.9", "2.8", "2.7", "2.6", "2.5"):
        bench.run(params=_run_params(kit, k=k))
    wrong = _refusal(kit, bench.path, "budget", lambda: bench.run(params=_run_params(kit, k="2.4")),
                     "a seventh params set of B")
    for label, changes in (
        ("params already counted, on another dataset", {"dataset": _dataset(kit, kit.g["SIGNAL_DATASET_2"])}),
        ("the first select of A (params B never ran)", {"params": _run_params(kit, "A", k="2.4")}),
    ):
        try:
            bench.run(**changes)
        except Exception as error:  # neither adds to B's six
            wrong.append(f"{label} was refused: {error!r}")
    other = _Bench(kit, tmp_path / "h002.jsonl")
    for k in ("2.9", "2.8", "2.7", "2.6", "2.5", "2.4"):
        other.append(params=_run_params(kit, k=k), hypothesis="H002")
    try:
        other.run()
    except Exception as error:  # H002's select lines are not H001's
        wrong.append(f"six H002 select params blocked H001: {error!r}")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_robustness_counts_fourteen_started_lines_per_variant(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    base, _ = bench.run()
    neighbours = [_neighbour_params(kit, _run_params(kit), name, value) for name, value in kit.g["RUN_NEIGHBOURS"]["B"]]
    for index in range(13):  # 7 interrupted and 6 failed robustness runs
        bench.append("robustness", params=neighbours[index % 4], base=base.run_id,
                     status="started" if index < 7 else "failed")
    wrong = []
    try:
        bench.run("robustness", params=neighbours[1], base_run_id=base.run_id)
    except Exception as error:  # the fourteenth started line is inside the budget
        wrong.append(f"the 14th robustness run was refused: {error!r}")
    wrong += _refusal(kit, bench.path, "budget",
                      lambda: bench.run("robustness", params=neighbours[0], base_run_id=base.run_id),
                      "a 15th robustness started line")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_the_total_budget_is_63_summed_over_variants(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    g = kit.g
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    summary = _summary(kit, g["ZERO_SUMMARY"])
    bases = {}
    for variant in ("A", "B", "C"):
        params = _run_params(kit, variant)
        started = bench.append(params=params)
        bases[variant] = bench.append_ok(started, summary)
        for k in ("2.9", "2.8", "2.7", "2.6", "2.5"):
            bench.append(params=_run_params(kit, variant, k=k), status="failed" if k == "2.5" else "started")
    for variant in ("A", "B", "C"):
        neighbours = [_neighbour_params(kit, _run_params(kit, variant), name, value)
                      for name, value in g["RUN_NEIGHBOURS"][variant]]
        for index in range(14):
            bench.append("robustness", params=neighbours[index % len(neighbours)], base=bases[variant].run_id)
    bench.append("stress", params=_run_params(kit, "A"), base=bases["A"].run_id)
    bench.append("stress", params=_run_params(kit, "B"), base=bases["B"].run_id)
    bench.append("long_only", params=_run_params(kit, "C"), base=bases["C"].run_id)
    # Counted: select 6 + 6 + 6, robustness 14 + 14 + 14, stress 1 + 1 = 62. long_only is not counted.
    wrong = []
    for label, purpose, variant in (("long_only of C (not counted)", "long_only", "C"),
                                    ("stress of C, the 63rd counted run", "stress", "C")):
        try:
            bench.run(purpose, params=_run_params(kit, variant), base_run_id=bases[variant].run_id)
        except Exception as error:  # still inside the 63
            wrong.append(f"{label} was refused: {error!r}")
    wrong += _refusal(kit, bench.path, "budget",
                      lambda: bench.run("stress", params=_run_params(kit, "A"), base_run_id=bases["A"].run_id),
                      "a rerun of A's interrupted stress: the 64th counted run")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_one_base_per_variant_for_every_purpose_but_select(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-02", "run_variant")
    bench = _Bench(kit, tmp_path / "registry.jsonl")
    first, _ = bench.run()
    second, _ = bench.run(params=_run_params(kit, k="2.9"))
    bench.run("robustness", params=_run_params(kit, N=53), base_run_id=first.run_id)
    other = _run_params(kit, k="2.9")
    wrong = []
    for label, purpose, params in (("robustness", "robustness", replace(other, N=53)), ("stress", "stress", other),
                                   ("long_only", "long_only", other)):
        wrong += _refusal(kit, bench.path, "budget",
                          lambda: bench.run(purpose, params=params, base_run_id=second.run_id),
                          f"{label} on a second base of B")
    try:
        a_base, _ = bench.run(params=_run_params(kit, "A"))
        bench.run("robustness", params=_run_params(kit, "A", f=9), base_run_id=a_base.run_id)
    except Exception as error:  # A has its own base
        wrong.append(f"A's first base was refused: {error!r}")
    locked = _Bench(kit, tmp_path / "locked.jsonl")
    one, _ = locked.run()
    two, _ = locked.run(params=other)
    locked.append("stress", params=other, base=two.run_id)  # interrupted: it still fixes the base
    wrong += _refusal(kit, locked.path, "budget",
                      lambda: locked.run("robustness", params=_run_params(kit, N=53), base_run_id=one.run_id),
                      "robustness on the first select after an interrupted stress on the second")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-03

def _summary_trade(kit, rule, spec):
    """A Trade with the fields summarize reads; the rest are fixed dummies (summarize never reads them)."""
    side, stamp, r, net, reason, ambiguous, flags = spec
    entry = _raw(stamp)
    zero = Decimal("0")
    costs = kit.costs.CostBreakdown(spread=zero, commission=zero, slippage=zero, swap=zero, total=zero,
                                    stress_factor=Decimal("1"))
    return kit.bt.Trade(
        side=side, entry_time_raw=entry, entry_bid=Decimal("2000.00"), entry_spread_points=200,
        exit_time_raw=entry + 3600, exit_bid=Decimal("2000.00"), exit_spread_points=200, lots=Decimal("0.02"),
        stop_distance=Decimal("10"), stop_price=Decimal("1990.20"), exit_reason=reason, ambiguous=ambiguous,
        nights=0, triple_nights=0, costs=costs, gross_money=Decimal(net), net_money=Decimal(net),
        risk_money=Decimal("25"), actual_risk=None, r=Decimal(r), data_flags=frozenset(flags))


def _summary_case(kit, name):
    case = kit.g["SUMMARY_CASES"][name]
    if case["rule"] == "measured":
        rule = kit.rule
    else:
        spec = kit.g["OFFSET_RULE"]
        rule = kit.tb.TimeRule(server=spec["server"], symbol=spec["symbol"], terminal_build=spec["terminal_build"],
                               offset_seconds=spec["offset_seconds"], evidence_from=date(2026, 10, 20),
                               evidence_to=date(2026, 10, 21), evidence_ref="synthetic", version=spec["version"])
    trades = tuple(_summary_trade(kit, rule, spec) for spec in case["trades"])
    result = kit.bt.Result(trades=trades, skips=(), equity=((946684800, Decimal("10000")),),
                           backtest_version=kit.bt.BACKTEST_VERSION, strategy_version=kit.strategy.STRATEGY_VERSION)
    return case, result, rule


def _check_summary(kit, summary, expected, label):
    wrong = []
    if type(summary) is not kit.Summary:
        return [f"{label}: a {type(summary).__name__}, not a Summary"]
    for name in _SHAPES["Summary"]:
        got, want = getattr(summary, name), expected[name]
        if name == "expectancy_by_year":
            want = tuple((year, Decimal(text)) for year, text in want)
            ok = (type(got) is tuple and all(type(item) is tuple and len(item) == 2 and type(item[0]) is int
                                             and type(item[1]) is Decimal for item in got) and got == want)
        elif name in _INT_SUMMARY:
            ok = type(got) is int and got == want
        elif want is None:
            ok = got is None
        else:
            ok = type(got) is Decimal and got == Decimal(want)
        if not ok:
            wrong.append(f"{label}: {name} = {got!r}, expected {want!r}")
    return wrong


@pytest.mark.parametrize("name", list(_G["SUMMARY_CASES"]))
def test_ac03_summarize_matches_the_hand_computed_summary(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-03", "summarize")
    case, result, rule = _summary_case(kit, name)
    summary = kit.summarize(result, rule)
    wrong = _check_summary(kit, summary, case["expected"], name)
    for field_name, text in case.get("repr", {}).items():
        if str(getattr(summary, field_name)) != text:
            wrong.append(f"{name}: {field_name} written {str(getattr(summary, field_name))!r}, expected {text!r}")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


def test_ac03_summarize_computes_in_the_costs_context_and_leaves_the_caller_context(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "summarize")
    wrong = []
    for name in ("order_at_precision_28", "seven"):
        case, result, rule = _summary_case(kit, name)
        with localcontext() as context:
            _hostile(context, prec=50)
            before = _context_state()
            summary = kit.summarize(result, rule)
            if _context_state() != before:
                wrong.append(f"{name}: the caller's context changed")
        wrong += _check_summary(kit, summary, case["expected"], f"{name} under a prec-50 caller context")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


def test_ac03_summarize_refuses_wrong_types(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "summarize")
    _, result, rule = _summary_case(kit, "seven")
    wrong = []
    for label, call in (("a tuple of trades", lambda: kit.summarize(result.trades, rule)),
                        ("None", lambda: kit.summarize(None, rule)),
                        ("a rule that is not a TimeRule", lambda: kit.summarize(result, "Exness-MT5Trial14"))):
        if not isinstance(_outcome(call), TypeError):
            wrong.append(f"{label}: expected TypeError")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


@pytest.mark.parametrize("values, q, expected", _G["PERCENTILE_CASES"])
def test_ac03_percentile_is_the_nearest_rank(monkeypatch, values, q, expected):
    kit = _kit(monkeypatch, "AC-03", "percentile")
    got = kit.percentile(tuple(Decimal(value) for value in values), Decimal(q))
    assert type(got) is Decimal and got == Decimal(expected), f"AC-03: percentile q={q} gave {got!r}, expected {expected}"


def test_ac03_percentile_of_a_thousand_values(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "percentile")
    values = [Decimal((37 * index) % 1000 - 500) for index in range(1000)]
    wrong = []
    for q, expected in kit.g["PERCENTILE_THOUSAND"].items():
        got = kit.percentile(values, Decimal(q))
        if got != Decimal(expected):
            wrong.append(f"q={q}: {got!r}, expected {expected}")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


def test_ac03_percentile_refuses_bad_inputs(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "percentile")
    values = (Decimal("1"), Decimal("2"))
    wrong = []
    for label, call, kind in (
        ("no values", lambda: kit.percentile((), Decimal("0.5")), "research"),
        ("q 0", lambda: kit.percentile(values, Decimal("0")), "research"),
        ("q below 0", lambda: kit.percentile(values, Decimal("-0.5")), "research"),
        ("q above 1", lambda: kit.percentile(values, Decimal("1.01")), "research"),
        ("q NaN", lambda: kit.percentile(values, Decimal("NaN")), "research"),
        ("q Infinity", lambda: kit.percentile(values, Decimal("Infinity")), "research"),
        ("q as float", lambda: kit.percentile(values, 0.5), "type"),
        ("q as int", lambda: kit.percentile(values, 1), "type"),
        ("q as str", lambda: kit.percentile(values, "0.5"), "type"),
        ("a float value", lambda: kit.percentile((Decimal("1"), 2.0), Decimal("0.5")), "type"),
        ("values as a generator", lambda: kit.percentile((value for value in values), Decimal("0.5")), "type"),
    ):
        error = _outcome(call)
        if not _is(kit, error, kind):
            wrong.append(f"{label}: expected {kind}, got {error!r}")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-04

def _fake_random(values):
    """A random.Random stand-in: returns next(values()) % n for randrange(n) and records seeds and every n."""

    class Fake:
        instances = []

        def __init__(self, *args, **kwargs):
            self.args, self.kwargs = args, kwargs
            self.calls = []
            self.source = values()
            Fake.instances.append(self)

        def randrange(self, *args, **kwargs):
            if kwargs or len(args) not in (1, 2) or any(type(item) is not int for item in args):
                raise _FakeMisuse(f"randrange{args} {kwargs}")
            if len(args) == 2 and args[0] != 0:
                raise _FakeMisuse(f"randrange{args}")
            n = args[-1]
            if n < 1:
                raise _FakeMisuse(f"randrange({n})")
            self.calls.append(n)
            return next(self.source) % n

    return Fake


def _lcg():
    state = 20241024
    while True:
        state = (state * 6364136223846793005 + 1442695040888963407) % 2 ** 64
        yield state >> 33


def _seed_of(fake):
    return fake.args[0] if fake.args else fake.kwargs.get("x")


class _Baseline:
    """random_entry_baseline on the flat or wave series with RUN_PARAMS (V-B) and a hand-built variant."""

    def __init__(self, kit, kind):
        g = kit.g
        self.kit = kit
        self.m1, self.m15 = _series(kit, kind)
        self.params = _run_params(kit)
        self.model = _flat_model(kit) if kind == "flat" else kit.costs.H001_COSTS
        self.dataset = _dataset(kit, g["FLAT_DATASET"] if kind == "flat" else g["WAVE_DATASET"])
        spec = g["FLAT_VARIANT"] if kind == "flat" else g["WAVE_VARIANT"]
        self.variant = self.result(spec)
        reasons = g["FLAT_VARIANT_REASONS"] if kind == "flat" else g["WAVE_VARIANT_REASONS"]
        got = tuple((trade.exit_reason, trade.ambiguous) for trade in self.variant.trades)
        assert got == reasons, f"fixture: the {kind} variant closes {got}, expected {reasons}"
        self.summary = _summary(kit, g["FLAT_SUMMARY"]) if kind == "flat" else kit.summarize(self.variant, kit.rule)

    def result(self, spec):
        kit = self.kit
        trades = tuple(kit.bt.simulate_trade(self.m1, entry, side, Decimal(stop), Decimal("0.02"), self.model,
                                             _rollover(kit), risk_money=Decimal("25"), exit_index=exit_index)
                       for side, entry, stop, exit_index in spec)
        equity = [(self.m1[0].time_raw, Decimal("10000"))]
        for trade in trades:
            with localcontext(kit.costs.CONTEXT):
                equity.append((trade.exit_time_raw, equity[-1][1] + trade.net_money))
        return kit.bt.Result(trades=trades, skips=(), equity=tuple(equity), backtest_version=kit.bt.BACKTEST_VERSION,
                             strategy_version=kit.strategy.STRATEGY_VERSION)

    def base(self, path, *, params=None, summary=None):
        """Append a select started line and its ok line, as run_variant would write them."""
        kit = self.kit
        seq = len(kit.read_records(path)) + 1
        started = _rec(kit, seq=seq, params=params or self.params, dataset=self.dataset, model=self.model)
        kit.append_record(path, started)
        ok = _result_of(kit, started, summary=summary or self.summary)
        kit.append_record(path, ok)
        return ok

    def started(self, path, base, purpose="random_entry", params=None):
        kit = self.kit
        record = _rec(kit, seq=len(kit.read_records(path)) + 1, purpose=purpose, params=params or self.params,
                      dataset=self.dataset, model=self.model, base=base.run_id)
        kit.append_record(path, record)
        return record

    def call(self, base_run_id, registry, *, m1=_DEFAULT, m15=_DEFAULT, params=_DEFAULT, model=_DEFAULT,
             sizer=_DEFAULT, equity=_DEFAULT, rule=_DEFAULT, rollover=_DEFAULT, variant=_DEFAULT, dataset=_DEFAULT,
             code_commit=_DEFAULT, sizer_label=_DEFAULT):
        kit = self.kit
        return kit.random_entry_baseline(
            _or(m1, self.m1), _or(m15, self.m15), _or(params, self.params), _or(model, self.model),
            _or(sizer, _Sizer(kit)), _or(equity, Decimal("10000")), _or(rule, kit.rule), _or(rollover, _rollover(kit)),
            _or(variant, self.variant), base_run_id=base_run_id, dataset=_or(dataset, self.dataset),
            code_commit=_or(code_commit, kit.g["CODE_COMMIT"]), sizer_label=_or(sizer_label, kit.g["SIZER_LABEL"]),
            registry=registry)


def _oracle(kit, bench, sizer, rng):
    """The contract's baseline steps 3-8 written out here, every trade through backtest.simulate_trade."""
    g = kit.g
    m1, m15, params = bench.m1, bench.m15, bench.params
    first = [kit.tb.bar_open(bar.time_raw, 15, kit.rule) for bar in m1]
    opens = [item.bar.time_raw for item in m15]
    layout = tuple(first.index(opened) for opened in opens)
    assert layout == g["FIRST_M1"] and len(m1) == g["M1_COUNT"], "fixture: the M1 layout of the series"
    rows = kit.strategy.indicators(m15, params)
    eligible = [t for t in range(len(m15) - 1) if kit.strategy.entry_blockers(rows[t], m15[t + 1].bar.time_utc) == ()]
    assert tuple(eligible) == g["ELIGIBLE"], f"fixture: eligible bars {eligible}"
    index = {bar.time_raw: position for position, bar in enumerate(m1)}
    hs = [index[t.exit_time_raw] - index[t.entry_time_raw] for t in bench.variant.trades
          if t.exit_reason in ("signal", "end_of_data") or t.ambiguous]
    count = len(bench.variant.trades)
    expectancies, holds, reasons = [], [], set()
    for _ in range(1000):
        pool = list(eligible)
        trades = []
        while len(trades) < count:
            assert pool, "fixture: the oracle ran out of bars"
            t = pool.pop(rng.randrange(len(pool)))
            with localcontext(kit.costs.CONTEXT):
                stop = params.k * rows[t].atr
            sized = sizer(Decimal("10000"), stop)
            if sized.lots is None:
                continue
            side = ("long", "short")[rng.randrange(2)]
            h = hs[rng.randrange(len(hs))]
            entry = layout[t + 1]
            planned = entry + max(h, 1)
            exit_index = planned if planned < len(m1) else None
            last = len(m1) - 1 if exit_index is None else exit_index
            flags = frozenset().union(*(m15[u].flags for u in range(t, bisect_right(layout, last))))
            trade = kit.bt.simulate_trade(m1, entry, side, stop, sized.lots, bench.model, _rollover(kit),
                                          risk_money=sized.risk_money, actual_risk=sized.actual_risk,
                                          exit_index=exit_index, data_flags=flags)
            trades.append(trade)
            holds.append(index[trade.exit_time_raw] - entry)
            reasons.add(trade.exit_reason)
        with localcontext(kit.costs.CONTEXT):
            total = Decimal(0)
            for trade in trades:
                total = total + trade.r
            expectancies.append(total / count)
    return expectancies, holds, hs, reasons


def _nearest(values, q):
    ordered = sorted(values)
    rank = -(-len(ordered) * Decimal(q) // 1)
    return ordered[int(rank) - 1]


def _expected_summary(kit, bench, expectancies, holds, seed):
    index = {bar.time_raw: position for position, bar in enumerate(bench.m1)}
    variant_holds = [index[t.exit_time_raw] - index[t.entry_time_raw] for t in bench.variant.trades]
    with localcontext(kit.costs.CONTEXT):
        total = Decimal(0)
        for value in expectancies:
            total = total + value
        mean = total / 1000
        variant_mean = Decimal(sum(variant_holds)) / Decimal(len(variant_holds))
        baseline_mean = Decimal(sum(holds)) / Decimal(len(holds))
    return kit.BaselineSummary(
        runs=1000, trades_per_run=len(bench.variant.trades), seed=seed, mean_r=mean,
        p05_r=_nearest(expectancies, "0.05"), p50_r=_nearest(expectancies, "0.5"), p95_r=_nearest(expectancies, "0.95"),
        variant_mean_hold_m1=variant_mean, variant_median_hold_m1=_nearest(variant_holds, "0.5"),
        baseline_mean_hold_m1=baseline_mean, baseline_median_hold_m1=_nearest(holds, "0.5"))


def _check_baseline_summary(kit, got, want, label):
    if type(got) is not kit.BaselineSummary:
        return [f"{label}: a {type(got).__name__}, not a BaselineSummary"]
    wrong = []
    for name in _SHAPES["BaselineSummary"]:
        a, b = getattr(got, name), getattr(want, name)
        kind = int if name in _INT_BASELINE else Decimal
        if type(a) is not kind or a != b:
            wrong.append(f"{label}: {name} = {a!r}, expected {b!r}")
    return wrong


def _check_lines(kit, bench, path, base, summary, label, before):
    """The started and ok lines of a successful baseline after `before` existing records (the started line
    byte for byte; the ok line by value, since its Decimals come from the arithmetic, convention 8)."""
    records = kit.read_records(path)
    started = _rec(kit, seq=before + 1, purpose="random_entry", params=bench.params, dataset=bench.dataset,
                   model=bench.model, base=base.run_id)
    ok = _result_of(kit, started, baseline=summary)
    if len(records) != before + 2 or records[before].line() != started.line() or records[-1] != ok:
        return [f"{label}: registry lines {records[before:]!r}"], None
    return [], records[-1]


def test_ac04_flat_prices_with_a_scripted_random_give_the_hand_computed_baseline(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "BaselineResult")
    g = kit.g
    bench = _Baseline(kit, "flat")
    path = tmp_path / "registry.jsonl"
    base = bench.base(path)
    fake = _fake_random(lambda: cycle(g["FLAT_SCRIPT"]))
    monkeypatch.setattr(random, "Random", fake)
    written, _, _ = _seam(monkeypatch, "AC-04")
    pattern = g["FLAT_SIZER_PATTERN"]
    sizer = _Sizer(kit, lots_for=lambda index: pattern[index % len(pattern)])
    result = bench.call(base.run_id, path, sizer=sizer)
    seed = int(base.run_id[:15], 16)
    wrong = []
    if len(fake.instances) != 1 or _seed_of(fake.instances[0]) != seed:
        wrong.append(f"random.Random built {len(fake.instances)} times, seeds {[_seed_of(item) for item in fake.instances]}"
                     f", expected one with {seed}")
    elif fake.instances[0].calls != list(g["FLAT_SCRIPT_N"]) * 1000:
        wrong.append(f"randrange arguments of round 1: {fake.instances[0].calls[:10]}, expected {g['FLAT_SCRIPT_N']}")
    if type(result) is not kit.BaselineResult:
        wrong.append(f"returned a {type(result).__name__}")
    expectancies = result.expectancies_r
    if (type(expectancies) is not tuple or len(expectancies) != 1000
            or any(type(item) is not Decimal or item != Decimal(g["FLAT_ROUND_EXPECTANCY"]) for item in expectancies)):
        wrong.append(f"expectancies: {expectancies[:5]!r}... ({len(expectancies)})")
    expected = _baseline(kit, g["FLAT_BASELINE"], seed)
    wrong += _check_baseline_summary(kit, result.summary, expected, "summary")
    stops = {stop for _, stop in sizer.calls}
    if (len(sizer.calls) != 4000 or any(type(equity) is not Decimal or equity != Decimal("10000")
                                        for equity, _ in sizer.calls)
            or stops != {Decimal(g["FLAT_STOP_DISTANCE"])}):
        wrong.append(f"sizer calls: {len(sizer.calls)}, stops {stops}")
    lines, last = _check_lines(kit, bench, path, base, expected, "lines", 2)
    wrong += lines
    if last is not None and result.record != last:
        wrong.append("the returned record is not the ok line")
    if written != ["started", "ok"]:
        wrong.append(f"writes through sochron.research.registry.append_record: {written}")
    wrong += _refusal(kit, path, "budget", lambda: bench.call(base.run_id, path), "random_entry again after its ok")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_every_scripted_draw_and_trade_follows_the_contract_steps(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "summarize")
    g = kit.g
    bench = _Baseline(kit, "wave")
    path = tmp_path / "registry.jsonl"
    base = bench.base(path)
    fake = _fake_random(_lcg)
    monkeypatch.setattr(random, "Random", fake)
    every, at = g["WAVE_SIZER_NONE_EVERY"]
    lots_for = lambda index: None if index % every == at else "0.02"  # noqa: E731
    sizer = _Sizer(kit, lots_for=lots_for)
    result = bench.call(base.run_id, path, sizer=sizer)
    seed = int(base.run_id[:15], 16)
    made = list(fake.instances)
    oracle_sizer = _Sizer(kit, lots_for=lots_for)
    expectancies, holds, hs, reasons = _oracle(kit, bench, oracle_sizer, fake(seed))
    wrong = []
    if tuple(hs) != g["WAVE_HS"]:
        wrong.append(f"fixture: hs {hs}")
    if not {"stop", "signal", "end_of_data"} <= reasons or not any(lots is None for lots in map(lots_for, range(40))):
        wrong.append(f"fixture: the scripted draws close by {reasons}")
    if len(made) != 1 or _seed_of(made[0]) != seed:
        wrong.append(f"random.Random built {len(made)} times with {[_seed_of(item) for item in made]}, expected {seed}")
    elif made[0].calls != fake.instances[-1].calls:
        first = next((i for i, (a, b) in enumerate(zip(made[0].calls, fake.instances[-1].calls)) if a != b), None)
        wrong.append(f"randrange arguments differ from the contract's steps (first at call {first}); "
                     f"{len(made[0].calls)} calls, expected {len(fake.instances[-1].calls)}")
    if result.expectancies_r != tuple(expectancies):
        wrong.append("expectancies differ from simulate_trade of the drawn trades")
    if sizer.calls != oracle_sizer.calls:
        wrong.append(f"sizer calls differ: {len(sizer.calls)} vs {len(oracle_sizer.calls)}")
    expected = _expected_summary(kit, bench, expectancies, holds, seed)
    if (expected.variant_mean_hold_m1, expected.variant_median_hold_m1) != (Decimal(g["WAVE_VARIANT_HOLD"][0]),
                                                                            g["WAVE_VARIANT_HOLD"][1]):
        wrong.append("fixture: variant holds")
    wrong += _check_baseline_summary(kit, result.summary, expected, "summary")
    lines, _ = _check_lines(kit, bench, path, base, expected, "lines", 2)
    wrong += lines
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_the_real_generator_is_seeded_from_the_base_and_repeats(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "summarize")
    g = kit.g
    bench = _Baseline(kit, "wave")
    every, at = g["WAVE_SIZER_NONE_EVERY"]
    lots_for = lambda index: None if index % every == at else "0.02"  # noqa: E731
    results = []
    for name in ("one.jsonl", "two.jsonl"):
        path = tmp_path / name
        base = bench.base(path)
        results.append((bench.call(base.run_id, path, sizer=_Sizer(kit, lots_for=lots_for)), base, path))
    (first, base, path), (second, _, other) = results
    seed = int(base.run_id[:15], 16)
    expectancies, holds, _, _ = _oracle(kit, bench, _Sizer(kit, lots_for=lots_for), random.Random(seed))
    wrong = []
    if first != second or path.read_bytes() != other.read_bytes():
        wrong.append("two calls on fresh registries differ")
    if first.expectancies_r != tuple(expectancies):
        wrong.append("expectancies differ from the contract's steps with random.Random(int(base_run_id[:15], 16))")
    if not seed < 2 ** 60 or first.summary.seed != seed or first.record.seed != seed:
        wrong.append(f"seed {first.summary.seed}/{first.record.seed}, expected {seed}")
    wrong += _check_baseline_summary(kit, first.summary, _expected_summary(kit, bench, expectancies, holds, seed),
                                     "summary")
    flat = _Baseline(kit, "flat")
    flat_path = tmp_path / "flat.jsonl"
    flat_result = flat.call(flat.base(flat_path).run_id, flat_path)
    if any(value != Decimal(g["FLAT_ROUND_EXPECTANCY"]) for value in flat_result.expectancies_r):
        wrong.append("on flat prices a round's expectancy is not -(spread + commission + slippage) / risk_money")
    for name in ("mean_r", "p05_r", "p50_r", "p95_r"):
        if getattr(flat_result.summary, name) != Decimal(g["FLAT_ROUND_EXPECTANCY"]):
            wrong.append(f"flat {name} {getattr(flat_result.summary, name)!r}")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_refusals_before_the_started_line_write_nothing(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "summarize")
    g = kit.g
    bench = _Baseline(kit, "flat")
    path = tmp_path / "registry.jsonl"
    base = bench.base(path)
    started_id = kit.read_records(path)[0].run_id
    at_cutoff = _m1(kit, _flat_row(g["AT_CUTOFF"]))
    late = _dataset(kit, g["FLAT_DATASET"], period_end_utc=_utc(g["CUTOFF"]) + timedelta(seconds=1))
    shifted = replace(bench.variant.trades[0], entry_time_raw=bench.variant.trades[0].entry_time_raw + 60)
    wrong = []
    m15_without_50 = bench.m15[:50] + bench.m15[51:]
    m1_spread = list(bench.m1)
    m1_spread[10] = replace(m1_spread[10], spread=-1)
    for label, kind, changes in (
        ("an M1 at the cutoff", "holdout", {"m1": bench.m1 + (at_cutoff,), "m15": bench.m15 + _m15(kit, (at_cutoff,))}),
        ("a Dataset ending after the cutoff", "holdout", {"dataset": late}),
        ("model at 2x", "research", {"model": kit.costs.stress(bench.model)}),
        ("another equity", "research", {"equity": Decimal("20000")}),
        ("another sizer_label", "research", {"sizer_label": "fixed-0.03"}),
        ("another dataset", "research", {"dataset": _dataset(kit, g["FLAT_DATASET"], snapshot_id="SYN-FLAT2")}),
        ("other params", "research", {"params": _run_params(kit, k="2.9")}),
        ("another code_commit", "research", {"code_commit": g["OTHER_COMMIT"]}),
        ("another rollover", "research", {"rollover": _rollover(kit, hour=18)}),
        ("a variant that is not the base's result", "research",
         {"variant": bench.result(g["FLAT_VARIANT"][:2])}),
        ("an M1 outside every M15 bar", "research", {"m15": m15_without_50}),
        ("an M1 with a negative spread", "research", {"m1": tuple(m1_spread)}),
        ("a variant trade time that is no M1", "research",
         {"variant": replace(bench.variant, trades=(shifted,) + bench.variant.trades[1:])}),
        ("a variant that is a tuple", "type", {"variant": bench.variant.trades}),
        ("equity as int", "type", {"equity": 10000}),
        ("a sizer that is not callable", "type", {"sizer": None}),
    ):
        wrong += _refusal(kit, path, kind, lambda: bench.call(base.run_id, path, **changes), label)
    for label, kind, base_id in (("an unknown base", "research", "f" * 64),
                                 ("the base's started line", "research", started_id),
                                 ("base_run_id None", "type", None)):
        wrong += _refusal(kit, path, kind, lambda: bench.call(base_id, path), label)
    wrong += _refusal(kit, path, "type", lambda: bench.call(base.run_id, str(path)), "a str registry")
    for label, spec in (("a variant without trades", ()), ("a variant of stops only", (g["FLAT_VARIANT"][1],)),
                        ("more variant trades than eligible bars",
                         tuple(("long", start, "50.00", start + 3) for start in range(0, 60, 10)))):
        other = tmp_path / f"{len(spec)}.jsonl"
        variant = bench.result(spec)
        own = bench.base(other, summary=kit.summarize(variant, kit.rule))
        wrong += _refusal(kit, other, "research", lambda: bench.call(own.run_id, other, variant=variant), label)
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_failures_after_the_started_line_write_failed_and_raise_the_same_object(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline")
    bench = _Baseline(kit, "flat")
    disk_full = OSError("disk full")
    interrupt = KeyboardInterrupt()
    wrong = []
    for index, (label, sizer, fail, expected) in enumerate((
        ("every bar of a round sized to None: the pool runs out", _Sizer(kit, lots_for=lambda i: None), {}, "research"),
        ("a sizer result that is not SizedLots", lambda equity, stop: ("0.02", "25"), {}, "type"),
        ("KeyboardInterrupt from the sizer", _Raising(interrupt), {}, interrupt),
        ("the ok line cannot be written", _Sizer(kit), {"ok": disk_full}, disk_full),
    )):
        path = tmp_path / f"failure-{index}.jsonl"
        base = bench.base(path)
        written, module, original = _seam(monkeypatch, "AC-04", fail)
        raised = None
        try:
            bench.call(base.run_id, path, sizer=sizer)
        except BaseException as error:  # KeyboardInterrupt included: the contract re-raises it
            raised = error
        monkeypatch.setattr(module, "append_record", original)
        if isinstance(expected, BaseException):
            if raised is not expected:
                wrong.append(f"{label}: raised {raised!r}, not the original object")
        elif not _is(kit, raised, expected):
            wrong.append(f"{label}: raised {raised!r}, expected {expected}")
        started = _rec(kit, seq=3, purpose="random_entry", params=bench.params, dataset=bench.dataset,
                       model=bench.model, base=base.run_id)
        failed = _result_of(kit, started, status="failed", error=_error_text(raised))
        if [record.line() for record in kit.read_records(path)[2:]] != [started.line(), failed.line()]:
            wrong.append(f"{label}: lines {kit.read_records(path)[2:]!r}")
        if written != (["started", "ok", "failed"] if fail else ["started", "failed"]):
            wrong.append(f"{label}: writes {written}")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_random_entry_keeps_one_base_per_variant(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline")
    bench = _Baseline(kit, "flat")
    other = _run_params(kit, k="2.9")
    wrong = []
    for label, setup in (
        ("after an ok on the first base", "ok"),
        ("after only an interrupted robustness on the first base", "robustness"),
        ("after only an interrupted random_entry on the first base", "random_entry"),
    ):
        path = tmp_path / f"{setup}.jsonl"
        first = bench.base(path)
        second = bench.base(path, params=other)
        if setup == "ok":
            bench.call(first.run_id, path)
        else:
            params = _run_params(kit, N=53) if setup == "robustness" else None
            bench.started(path, first, purpose=setup, params=params)
        wrong += _refusal(kit, path, "budget", lambda: bench.call(second.run_id, path, params=other),
                          f"random_entry on a second base {label}")
    path = tmp_path / "rerun.jsonl"
    first = bench.base(path)
    bench.started(path, first)
    try:
        bench.call(first.run_id, path)
    except Exception as error:  # a rerun on the locked base after an interrupted run
        wrong.append(f"the rerun on the first base was refused: {error!r}")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-05

@pytest.mark.parametrize("name", list(_G["NEIGHBOUR_CASES"]))
def test_ac05_neighbours_match_the_hand_computed_table(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-05", "neighbours", "Neighbour")
    case = kit.g["NEIGHBOUR_CASES"][name]
    base = _params(kit, case["variant"], case["params"])
    got = kit.neighbours(base)
    wrong = []
    if type(got) is not tuple or any(type(item) is not kit.Neighbour for item in got):
        wrong.append(f"neighbours returned {got!r}")
    rows = [(item.parameter, item.direction, item.value) for item in got]
    expected = [row[:3] for row in case["rows"]]
    if rows != expected:
        wrong.append(f"rows {rows}, expected {expected}")
    for item, (parameter, _, value, valid) in zip(got, case["rows"]):
        if not valid:
            if item.params is not None:
                wrong.append(f"{parameter}{item.direction} {value}: params {item.params!r}, expected None (invalid)")
            continue
        want = _neighbour_params(kit, base, parameter, int(value) if parameter not in ("theta", "k") else value)
        if type(item.params) is not kit.strategy.H001Params or _param_pairs(item.params) != _param_pairs(want):
            wrong.append(f"{parameter}{item.direction} {value}: params {item.params!r}, expected {_param_pairs(want)}")
    count, needed = kit.g["NEIGHBOUR_COUNTS"][case["variant"]]
    if len(got) != count or -(-8 * count // 10) != needed:
        wrong.append(f"{len(got)} neighbours, expected {count}")
    assert not wrong, "AC-05:\n" + "\n".join(wrong)


def test_ac05_neighbours_compute_in_the_costs_context(monkeypatch):
    kit = _kit(monkeypatch, "AC-05", "neighbours")
    case = kit.g["NEIGHBOUR_CASES"]["C_default"]
    base = _params(kit, "C", case["params"])
    with localcontext() as context:
        _hostile(context, prec=2)
        context.rounding = ROUND_DOWN
        before = _context_state()
        got = kit.neighbours(base)
        changed = _context_state() != before
    rows = [(item.parameter, item.direction, item.value) for item in got]
    assert rows == [row[:3] for row in case["rows"]] and not changed, f"AC-05: under a prec-2 caller context {rows}"


def test_ac05_neighbours_refuse_wrong_types(monkeypatch):
    kit = _kit(monkeypatch, "AC-05", "neighbours")
    for value in (None, dict(kit.g["DEFAULTS"]), "B"):
        assert isinstance(_outcome(lambda: kit.neighbours(value)), TypeError), f"AC-05: neighbours({value!r})"


def _eval_inputs(kit, changes):
    """Consistent records for evaluate from EVAL_GO and one case's changes (golden convention)."""
    g = kit.g
    go = g["EVAL_GO"]
    variant = changes.get("variant", go["variant"])
    params = _params(kit, variant, changes.get("params", go["params"]))
    dataset = _dataset(kit, changes.get("dataset", go["dataset"]))
    specs = {}
    for name in ("base", "stress", "long_only", "random"):
        change = changes.get(name, {})
        specs[name] = None if change is None else {**go[name], **change}
    base = _rec(kit, seq=2, status="ok", started_seq=1, params=params, dataset=dataset,
                summary=_summary(kit, specs["base"]))
    stress = long_only = random_entry = None
    if specs["stress"] is not None:
        stress = _rec(kit, seq=4, status="ok", started_seq=3, purpose="stress", params=params, dataset=dataset,
                      base=base.run_id, model=kit.costs.stress(kit.costs.H001_COSTS), summary=_summary(kit, specs["stress"]))
    if specs["long_only"] is not None:
        long_only = _rec(kit, seq=6, status="ok", started_seq=5, purpose="long_only", params=params, dataset=dataset,
                         base=base.run_id, summary=_summary(kit, specs["long_only"]))
    if specs["random"] is not None:
        random_entry = _rec(kit, seq=8, status="ok", started_seq=7, purpose="random_entry", params=params,
                            dataset=dataset, base=base.run_id,
                            baseline=_baseline(kit, specs["random"], int(base.run_id[:15], 16)))
    table = next(case for case in g["NEIGHBOUR_CASES"].values()
                 if case["variant"] == variant and _param_pairs(_params(kit, variant, case["params"])) == _param_pairs(params))
    valid = [_neighbour_params(kit, params, parameter, int(value) if parameter not in ("theta", "k") else value)
             for parameter, _, value, ok in table["rows"] if ok]
    expectancies = changes.get("robustness", go["robustness"])
    robustness = []
    for index, (neighbour, expectancy) in enumerate(zip(valid, expectancies)):
        summary = (_summary(kit, g["ZERO_SUMMARY"]) if expectancy is None
                   else _summary(kit, go["base"], expectancy_r=expectancy))
        robustness.append(_rec(kit, seq=10 + 2 * index, status="ok", started_seq=9 + 2 * index, purpose="robustness",
                               params=neighbour, dataset=dataset, base=base.run_id, summary=summary))
    assert len(robustness) == len(expectancies), "fixture: one expectancy per valid neighbour"
    return base, stress, long_only, random_entry, robustness


@pytest.mark.parametrize("label, changes, verdict, screen, rows", _G["EVALUATE_CASES"],
                         ids=[case[0] for case in _G["EVALUATE_CASES"]])
def test_ac05_evaluate_every_row_at_its_threshold(monkeypatch, label, changes, verdict, screen, rows):
    kit = _kit(monkeypatch, "AC-05", "evaluate", "Evaluation", "Check")
    base, stress, long_only, random_entry, robustness = _eval_inputs(kit, changes)
    got = kit.evaluate(base, stress, long_only, random_entry, robustness)
    expected = list(kit.g["EVAL_GO_ROWS"])
    for number, (value, threshold, passed) in rows.items():
        expected[number - 1] = (expected[number - 1][0], value, threshold, passed)
    variant = changes.get("variant", "B")
    wrong = []
    if type(got) is not kit.Evaluation:
        pytest.fail(f"AC-05: evaluate returned {got!r}", pytrace=False)
    if (got.variant, got.base_run_id, got.dataset, got.screen, got.verdict) != (variant, base.run_id, base.dataset,
                                                                                 screen, verdict):
        wrong.append(f"variant/base/dataset/screen/verdict {got.variant} {got.base_run_id} {got.dataset} "
                     f"{got.screen} {got.verdict}, expected {variant} {base.run_id} {screen} {verdict}")
    if type(got.screen) is not bool or type(got.checks) is not tuple or len(got.checks) != 10:
        wrong.append(f"screen {got.screen!r}, checks {got.checks!r}")
    for number, (check, want) in enumerate(zip(got.checks, expected), start=1):
        actual = (check.name, check.value, check.threshold, check.passed)
        if (type(check) is not kit.Check or actual != want or type(check.passed) is not bool
                or any(type(item) is not str for item in actual[:3])):
            wrong.append(f"row {number}: {actual!r}, expected {want!r}")
    assert not wrong, f"AC-05 {label}:\n" + "\n".join(wrong)


def test_ac05_evaluate_refuses_inconsistent_inputs(monkeypatch):
    kit = _kit(monkeypatch, "AC-05", "evaluate")
    g = kit.g
    base, stress, long_only, random_entry, robustness = _eval_inputs(kit, {})
    other_pairs = _param_pairs(_params(kit, "B", k="2.9"))
    slip = tuple(("slippage_points_per_side", "20") if name == "slippage_points_per_side" else (name, value)
                 for name, value in stress.cost_model)

    def with_factor(record, factor):
        return replace(record, cost_model=record.cost_model[:-1] + (("stress_factor", factor),))

    def moved(record, base_id):
        if record.purpose == "random_entry":
            return replace(record, base_run_id=base_id, seed=int(base_id[:15], 16))
        return replace(record, base_run_id=base_id)

    other_dataset = _dataset(kit, g["PARTIAL_DATASET"])
    cases = (
        ("a failed stress record", (base, replace(stress, status="failed", summary=None, error="RuntimeError: x"),
                                    long_only, random_entry, robustness)),
        ("a started base", (replace(base, status="started", started_seq=None, summary=None), stress, long_only,
                            random_entry, robustness)),
        ("a stress record as the base", (stress, stress, long_only, random_entry, robustness)),
        ("stress and long_only swapped", (base, long_only, stress, random_entry, robustness)),
        ("stress on another base", (base, moved(stress, "f" * 64), long_only, random_entry, robustness)),
        ("random_entry on another base", (base, stress, long_only, moved(random_entry, "e" * 64), robustness)),
        ("a robustness record on another base", (base, stress, long_only, random_entry,
                                                  [moved(robustness[0], "f" * 64)] + robustness[1:])),
        ("another hypothesis", (base, replace(stress, hypothesis="H002"), long_only, random_entry, robustness)),
        ("another dataset", (base, stress, replace(long_only, dataset=other_dataset), random_entry, robustness)),
        ("another code_commit", (base, stress, long_only, replace(random_entry, code_commit=g["OTHER_COMMIT"]),
                                 robustness)),
        ("another sizer_label", (base, replace(stress, sizer_label="fixed-0.03"), long_only, random_entry, robustness)),
        ("another equity", (base, stress, replace(long_only, equity=Decimal("20000")), random_entry, robustness)),
        ("equity 1E+4", (base, stress, replace(long_only, equity=Decimal("1E+4")), random_entry, robustness)),
        ("another rollover", (base, replace(stress, rollover_at="18:00"), long_only, random_entry, robustness)),
        ("another time rule server", (base, replace(stress, time_rule_server="SYN-OTHER"), long_only, random_entry,
                                      robustness)),
        ("another time rule version", (base, stress, replace(long_only, time_rule_version="2"), random_entry,
                                       robustness)),
        ("stress params differ", (base, replace(stress, params=other_pairs), long_only, random_entry, robustness)),
        ("long_only params differ", (base, stress, replace(long_only, params=other_pairs), random_entry, robustness)),
        ("random_entry params differ", (base, stress, long_only, replace(random_entry, params=other_pairs), robustness)),
        ("stress with slippage 20", (base, replace(stress, cost_model=slip), long_only, random_entry, robustness)),
        ("stress at stress_factor 2.0", (base, with_factor(stress, "2.0"), long_only, random_entry, robustness)),
        ("stress at stress_factor 1", (base, with_factor(stress, "1"), long_only, random_entry, robustness)),
        ("long_only at stress_factor 2", (base, stress, with_factor(long_only, "2"), random_entry, robustness)),
        ("a base at stress_factor 2", (with_factor(base, "2"), stress, long_only, random_entry, robustness)),
        ("trades_per_run is not the base's trades",
         (base, stress, long_only, replace(random_entry, baseline=replace(random_entry.baseline, trades_per_run=99)),
          robustness)),
        ("a neighbour missing", (base, stress, long_only, random_entry, robustness[:-1])),
        ("a neighbour too many", (base, stress, long_only, random_entry, robustness + robustness[-1:])),
        ("neighbours swapped", (base, stress, long_only, random_entry, [robustness[1], robustness[0], *robustness[2:]])),
        ("a robustness record that is no neighbour",
         (base, stress, long_only, random_entry, [replace(robustness[0], params=other_pairs)] + robustness[1:])),
        ("a failed robustness record",
         (base, stress, long_only, random_entry,
          [replace(robustness[0], status="failed", summary=None, error="RuntimeError: x")] + robustness[1:])),
    )
    wrong = []
    for label, arguments in cases:
        error = _outcome(lambda: kit.evaluate(*arguments))
        if not _is(kit, error, "research"):
            wrong.append(f"{label}: expected ResearchError, got {error!r}")
    for label, arguments in (("base None", (None, stress, long_only, random_entry, robustness)),
                             ("stress as a dict", (base, {"purpose": "stress"}, long_only, random_entry, robustness)),
                             ("a robustness item that is a dict", (base, stress, long_only, random_entry, [{}]))):
        if not isinstance(_outcome(lambda: kit.evaluate(*arguments)), TypeError):
            wrong.append(f"{label}: expected TypeError")
    assert not wrong, "AC-05:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-06 report

def _report_registry(kit, path, specs, records=None):
    """Append the golden report records (seq order) and return {seq: record} of the file read back."""
    g = kit.g
    records = {} if records is None else records
    for seq, status, started, purpose, key, dataset_key, base_seq, extra in specs:
        variant, values = g["REPORT_PARAMS"][key]
        base = records[base_seq].run_id if base_seq else None
        model = kit.costs.stress(kit.costs.H001_COSTS) if extra.get("stress") else kit.costs.H001_COSTS
        summary = _summary(kit, g["REPORT_SUMMARIES"][extra["summary"]]) if "summary" in extra else None
        baseline = _baseline(kit, g["REPORT_BASELINE"], int(base[:15], 16)) if extra.get("baseline") else None
        record = _rec(kit, seq=seq, status=status, started_seq=started, purpose=purpose,
                      params=_params(kit, variant, values), dataset=_dataset(kit, g["REPORT_DATASETS"][dataset_key]),
                      base=base, model=model, hypothesis=extra.get("hypothesis", "H001"),
                      equity=extra.get("equity", "10000"), error=extra.get("error"), summary=summary, baseline=baseline)
        kit.append_record(path, record)
        records[seq] = record
    read = kit.read_records(path)
    return {record.seq: record for record in read}


def _report_evaluations(kit, records, keys=("C", "A", "B")):
    out = {}
    for variant in keys:
        spec = kit.g["REPORT_EVALUATIONS"][variant]
        base = records[spec["base_seq"]]
        checks = tuple(kit.Check(name=name, value=value, threshold=threshold, passed=passed)
                       for name, value, threshold, passed in spec["checks"])
        out[variant] = kit.Evaluation(variant=variant, base_run_id=base.run_id, dataset=base.dataset,
                                      screen=spec["screen"], verdict=spec["verdict"], checks=checks)
    return out


def _text_diff(got, want):
    if got == want:
        return []
    if type(got) is not str:
        return [f"render_report returned a {type(got).__name__}"]
    diff = difflib.unified_diff(want.splitlines(), got.splitlines(), "expected", "render_report", lineterm="", n=1)
    return ["the report differs from the contract's template:", *list(diff)[:60]]


def _layout_rules(text):
    """F38: every line ends with LF, no two blank lines in a row, no trailing spaces."""
    wrong = []
    if not text.endswith("\n") or text.endswith("\n\n"):
        wrong.append("the text does not end with exactly one LF")
    if "\n\n\n" in text:
        wrong.append("two blank lines in a row")
    if any(line != line.rstrip() for line in text.split("\n")):
        wrong.append("a line ends with a space")
    return wrong


def test_ac06_the_report_with_failed_interrupted_lines_and_three_evaluations(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-06", "render_report", "Evaluation", "Check")
    g = kit.g
    records = _report_registry(kit, tmp_path / "registry.jsonl", g["REPORT_RECORDS"])
    assert records[7].run_id == g["REPORT_RUN_ID_7"], f"AC-06: run_id of seq 7 is {records[7].run_id}"
    assert records[14].baseline.seed == g["REPORT_SEED"], "fixture: the report seed"
    text = kit.render_report(tuple(records.values()), _report_evaluations(kit, records))
    wrong = _text_diff(text, g["REPORT_FULL"]) + _layout_rules(g["REPORT_FULL"])
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_the_report_without_any_evaluation(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-06", "render_report")
    g = kit.g
    records = _report_registry(kit, tmp_path / "registry.jsonl", g["REPORT_RECORDS"])
    wrong = _text_diff(kit.render_report(tuple(records.values()), {}), g["REPORT_NO_EVALUATION"])
    wrong += _text_diff(kit.render_report((), {}), g["REPORT_EMPTY"])
    wrong += _text_diff(kit.render_report((), {}, hypothesis="H001"), g["REPORT_EMPTY"])
    wrong += _layout_rules(g["REPORT_NO_EVALUATION"]) + _layout_rules(g["REPORT_EMPTY"])
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_the_report_reads_only_the_records_of_its_hypothesis(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-06", "render_report", "Evaluation", "Check")
    g = kit.g
    path = tmp_path / "registry.jsonl"
    records = _report_registry(kit, path, g["REPORT_RECORDS"])
    records = _report_registry(kit, path, g["REPORT_H002_RECORDS"], records)
    evaluations = _report_evaluations(kit, records)
    wrong = _text_diff(kit.render_report(tuple(records.values()), evaluations), g["REPORT_FULL"])
    wrong += _text_diff(kit.render_report(tuple(records.values()), {}, hypothesis="H002"), g["REPORT_H002"])
    on_h002 = dict(evaluations, B=replace(evaluations["B"], base_run_id=records[20].run_id))
    error = _outcome(lambda: kit.render_report(tuple(records.values()), on_h002))
    if not _is(kit, error, "research"):
        wrong.append(f"an H001 Evaluation on H002's select: {error!r}")
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_the_report_refuses_bad_keys_and_bases_that_are_not_the_locked_one(monkeypatch, tmp_path):
    kit = _kit(monkeypatch, "AC-06", "render_report", "Evaluation", "Check")
    g = kit.g
    path = tmp_path / "registry.jsonl"
    records = _report_registry(kit, path, g["REPORT_RECORDS"])
    records = _report_registry(kit, path, g["REPORT_SECOND_B"], records)
    evaluations = _report_evaluations(kit, records)
    rows = tuple(records.values())
    wrong = []
    for label, mapping in (
        ("a key that is not the Evaluation's variant", {"A": evaluations["B"]}),
        ("a key outside A, B, C", {"D": replace(evaluations["A"], variant="D")}),
        ("a base_run_id that is no record", {"A": replace(evaluations["A"], base_run_id="f" * 64)}),
        ("a base_run_id of a started select line", {"A": replace(evaluations["A"], base_run_id=records[1].run_id)}),
        ("a base_run_id of another variant's select", {"C": replace(evaluations["C"], base_run_id=records[2].run_id)}),
        ("a select ok that is not the locked base of B", {"B": replace(evaluations["B"], base_run_id=records[20].run_id)}),
    ):
        error = _outcome(lambda: kit.render_report(rows, mapping))
        if not _is(kit, error, "research"):
            wrong.append(f"{label}: expected ResearchError, got {error!r}")
    for label, call in (("records None", lambda: kit.render_report(None, {})),
                        ("evaluations as a list", lambda: kit.render_report(rows, [evaluations["A"]])),
                        ("hypothesis None", lambda: kit.render_report(rows, {}, hypothesis=None))):
        if not isinstance(_outcome(call), TypeError):
            wrong.append(f"{label}: expected TypeError")
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-06 entry_blockers

def _indicator_row(kit, *, spread=200, median="200", atr="1.5", flags=(), warm=True):
    """A row with a V-B long breakout (close 2001.00 > HH_N 2000.00) and the given invalidation inputs."""
    return kit.strategy.IndicatorRow(
        ema_f=Decimal("2000.5"), ema_s=Decimal("2000.0"), atr=_dec(atr), ts=Decimal("0.3"), hh_n=Decimal("2000.00"),
        ll_n=Decimal("1990.00"), hh_m=Decimal("2001.50"), ll_m=Decimal("1995.00"), close=Decimal("2001.00"),
        spread=spread, spread_median_96=_dec(median), warm=warm, lookback_flags=frozenset(flags))


def _expected_blockers(window, spread, median, atr, flags, warm):
    """The contract's reasons in its order (CORE-006 invalidation, D1)."""
    reasons = []
    if not window:
        reasons.append("outside_window")
    if spread is not None and median is not None and Decimal(spread) > 3 * Decimal(median):
        reasons.append("spread_filter")
    if spread is None or median is None:
        reasons.append("spread_unknown")
    if atr is None or Decimal(atr) == 0:
        reasons.append("atr_zero")
    if flags:
        reasons.append("data_flag")
    if not warm:
        reasons.append("warmup")
    return tuple(reasons)


_WINDOWS = (("2024-01-09T14:00", True), ("2024-01-09T20:59", True), ("2024-01-09T21:00", False),
            ("2024-01-09T07:59", False))  # 09:00 and 15:59 New York (EST) are inside; 16:00 and 02:59 are not
_SPREADS = ((200, "200"), (600, "200"), (601, "200"), (None, "200"), (200, None))


def test_ac06_entry_blockers_give_decide_s_skip_reasons_in_every_case(monkeypatch):
    (entry_blockers,) = _api(monkeypatch, "AC-06", "strategy.entry_blockers")
    kit = SimpleNamespace(strategy=import_module("sochron.strategy"))
    params = _run_params(SimpleNamespace(strategy=kit.strategy, g=_G))
    wrong = []
    checked = 0
    for (stamp, window), (spread, median), atr, flags, warm in product(
            _WINDOWS, _SPREADS, ("1.5", "0", None), ((), ("unexpected_gap",)), (True, False)):
        row = _indicator_row(kit, spread=spread, median=median, atr=atr, flags=flags, warm=warm)
        next_open = _utc(stamp)
        expected = _expected_blockers(window, spread, median, atr, flags, warm)
        got = entry_blockers(row, next_open)
        label = f"{stamp} spread {spread}/{median} atr {atr} flags {flags} warm {warm}"
        if type(got) is not tuple or got != expected:
            wrong.append(f"{label}: entry_blockers {got!r}, expected {expected!r}")
        decision = kit.strategy.decide((row, row), 1, "flat", next_open, params)
        if expected and (decision.action != "skip" or decision.reasons != expected):
            wrong.append(f"{label}: decide {decision.action} {decision.reasons}, expected skip {expected}")
        if not expected and (decision.action != "enter_long" or decision.stop_distance != Decimal("4.50")):
            wrong.append(f"{label}: decide {decision!r}, expected enter_long at 3.0 x 1.5")
        checked += 1
    assert checked == 240 and not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_decide_calls_entry_blockers_through_the_h001_module(monkeypatch):
    (h001,) = _api(monkeypatch, "AC-06", "h001")
    _api(monkeypatch, "AC-06", "strategy.entry_blockers")
    strategy = import_module("sochron.strategy")
    params = _run_params(SimpleNamespace(strategy=strategy, g=_G))
    kit = SimpleNamespace(strategy=strategy)
    calls = []
    answers = iter((("fake_reason",), ()))

    def fake(row, next_open_utc):
        calls.append((row, next_open_utc))
        return next(answers)

    wrong = []
    if strategy.entry_blockers is not getattr(h001, "entry_blockers", None):
        wrong.append("sochron.strategy.entry_blockers is not sochron.strategy.h001.entry_blockers")
    monkeypatch.setattr(h001, "entry_blockers", fake)
    ready = _indicator_row(kit)
    cold = _indicator_row(kit, warm=False)
    next_open = _utc("2024-01-09T14:00")
    first = strategy.decide((ready, ready), 1, "flat", next_open, params)
    second = strategy.decide((cold, cold), 1, "flat", next_open, params)
    if (first.action, first.reasons) != ("skip", ("fake_reason",)):
        wrong.append(f"with a fake that blocks, decide gave {first!r}")
    if (second.action, second.stop_distance) != ("enter_long", Decimal("4.50")):
        wrong.append(f"with a fake that blocks nothing on a cold row, decide gave {second!r}")
    if len(calls) != 2 or calls[0][0] is not ready or calls[0][1] != next_open or calls[1][0] is not cold:
        wrong.append(f"the fake was called with {calls!r}")
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_entry_blockers_refuse_wrong_types_and_naive_times(monkeypatch):
    (entry_blockers,) = _api(monkeypatch, "AC-06", "strategy.entry_blockers")
    strategy = import_module("sochron.strategy")
    row = _indicator_row(SimpleNamespace(strategy=strategy))

    class _Row(strategy.IndicatorRow):
        pass

    class _Moment(datetime):
        pass

    sub_row = _Row(**{item.name: getattr(row, item.name) for item in fields(row)})
    wrong = []
    for label, call, kind in (
        ("row None", lambda: entry_blockers(None, _utc("2024-01-09T14:00")), TypeError),
        ("row a tuple", lambda: entry_blockers(tuple(getattr(row, item.name) for item in fields(row)),
                                               _utc("2024-01-09T14:00")), TypeError),
        ("row a subclass", lambda: entry_blockers(sub_row, _utc("2024-01-09T14:00")), TypeError),
        ("a str time", lambda: entry_blockers(row, "2024-01-09T14:00Z"), TypeError),
        ("a date", lambda: entry_blockers(row, date(2024, 1, 9)), TypeError),
        ("a datetime subclass", lambda: entry_blockers(row, _Moment(2024, 1, 9, 14, tzinfo=UTC)), TypeError),
        ("a naive time", lambda: entry_blockers(row, datetime(2024, 1, 9, 14)), strategy.StrategyError),
    ):
        error = _outcome(call)
        if type(error) is not kind:
            wrong.append(f"{label}: expected {kind.__name__}, got {error!r}")
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_invalid_is_gone_and_the_strategy_version_is_unchanged(monkeypatch):
    (h001,) = _api(monkeypatch, "AC-06", "h001")
    _api(monkeypatch, "AC-06", "strategy.entry_blockers")
    strategy = import_module("sochron.strategy")
    wrong = []
    if hasattr(h001, "_invalid"):
        wrong.append("sochron.strategy.h001._invalid still exists")
    if strategy.STRATEGY_VERSION != "H001-v1":
        wrong.append(f"STRATEGY_VERSION {strategy.STRATEGY_VERSION!r}")
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


# ======================================================================= tests r2 (review tests-r1 F1-F6)
# Appended by the round-2 test author under contract v1.5 (docs/reviews/CORE-008-tests-r1.md F1-F6). Every
# statement above is unchanged and the conventions of the module docstring hold. The known answers and
# their arithmetic are in the "tests r2" part of tests/golden/CORE-008/research_cases.py.


def _wave_lots(index):
    """The sizer pattern of the round-1 wave tests: lots None on calls 3, 10, 17, ... (index % 7 == 2)."""
    every, at = _G["WAVE_SIZER_NONE_EVERY"]
    return None if index % every == at else "0.02"


def test_ac04_r2_the_baseline_computes_in_the_costs_context_and_leaves_the_caller_context(monkeypatch, tmp_path):
    """F1: k x ATR[t], each round's expectancy, mean_r and the mean holds are computed in costs.CONTEXT."""
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "BaselineResult", "summarize")
    g = kit.g
    bench = _Baseline(kit, "wave")
    path = tmp_path / "registry.jsonl"
    base = bench.base(path)
    sizer = _Sizer(kit, lots_for=_wave_lots)
    with localcontext() as context:
        _hostile(context, prec=g["HOSTILE_PRECISION"])
        before = _context_state()
        result = bench.call(base.run_id, path, sizer=sizer)
        changed = _context_state() != before
    if type(result) is not kit.BaselineResult:
        pytest.fail(f"AC-04: random_entry_baseline returned {result!r}", pytrace=False)
    seed = int(base.run_id[:15], 16)
    oracle_sizer = _Sizer(kit, lots_for=_wave_lots)
    expectancies, holds, _, _ = _oracle(kit, bench, oracle_sizer, random.Random(seed))
    expected = _expected_summary(kit, bench, expectancies, holds, seed)
    with localcontext() as context:  # premises: the caller context would change the CONTEXT arithmetic
        _hostile(context, prec=g["HOSTILE_PRECISION"])
        stops_move = any(+stop != stop for _, stop in oracle_sizer.calls)
        total = Decimal(0)
        for value in expectancies:
            total = total + value
        mean_moves = total / 1000 != expected.mean_r
    wrong = []
    if not stops_move or not mean_moves:
        wrong.append(f"fixture: the caller context changes no stop distance ({stops_move}) or not the mean "
                     f"({mean_moves})")
    if changed:
        wrong.append("the caller's Decimal context changed")
    if result.expectancies_r != tuple(expectancies):
        wrong.append("expectancies differ from the contract's steps computed in costs.CONTEXT")
    if sizer.calls != oracle_sizer.calls:
        wrong.append("the stop distances given to the sizer are not k x ATR[t] computed in costs.CONTEXT")
    wrong += _check_baseline_summary(kit, result.summary, expected, "summary under a precision-3 caller context")
    lines, last = _check_lines(kit, bench, path, base, expected, "lines", 2)
    wrong += lines
    if last is not None and result.record != last:
        wrong.append("the returned record is not the ok line")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_r2_a_variant_exit_time_that_is_no_m1_is_refused_before_the_started_line(monkeypatch, tmp_path):
    """F6: baseline step 2 needs the entry_time_raw and the exit_time_raw of every variant trade in m1."""
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "summarize")
    bench = _Baseline(kit, "flat")
    path = tmp_path / "registry.jsonl"
    base = bench.base(path)
    times = {bar.time_raw for bar in bench.m1}
    trades = bench.variant.trades
    wrong = []
    for label, position in (("a signal exit (a hold in hs)", 0), ("a stop exit (not in hs)", 1)):
        moved = replace(trades[position], exit_time_raw=trades[position].exit_time_raw + 60)
        variant = replace(bench.variant, trades=trades[:position] + (moved,) + trades[position + 1:])
        off_grid = [index for index, trade in enumerate(variant.trades) if trade.exit_time_raw not in times]
        if off_grid != [position] or any(trade.entry_time_raw not in times for trade in variant.trades):
            wrong.append(f"fixture: {label}: exit times off the M1 grid at {off_grid}")
        if kit.summarize(variant, kit.rule) != base.summary:
            wrong.append(f"fixture: {label}: the variant no longer matches the summary of its base")
        wrong += _refusal(kit, path, "research", lambda: bench.call(base.run_id, path, variant=variant), label)
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


@pytest.mark.parametrize("label, changes, verdict, screen, rows", _G["EVALUATE_CASES_R2"],
                         ids=[case[0] for case in _G["EVALUATE_CASES_R2"]])
def test_ac05_r2_evaluate_row_10_fails_when_the_base_has_no_trades(monkeypatch, label, changes, verdict, screen, rows):
    """F4: row 10 fails for a base without trades although its drawdown 0 is below the long-only one."""
    kit = _kit(monkeypatch, "AC-05", "evaluate", "Evaluation", "Check")
    base, _, long_only, _, _ = _eval_inputs(kit, changes)
    if base.summary.trades != 0 or long_only is None or long_only.summary.trades == 0:
        pytest.fail(f"AC-05 {label}: fixture: a base without trades and a long-only run with trades", pytrace=False)
    # The round-1 checks, unchanged: verdict, screen and value/threshold/passed of all 10 rows.
    test_ac05_evaluate_every_row_at_its_threshold(monkeypatch, label, changes, verdict, screen, rows)


def test_ac05_r2_evaluate_refuses_a_record_of_another_variant_base_or_rollover_zone(monkeypatch):
    """F5: evaluate's input rules compare the variant and the rollover zone and check long_only's base_run_id."""
    kit = _kit(monkeypatch, "AC-05", "evaluate", "Evaluation")
    base, stress, long_only, random_entry, robustness = _eval_inputs(kit, {})
    consistent = {"stress": stress, "long_only": long_only, "random_entry": random_entry}
    other_base = _rec(kit, seq=2, status="ok", started_seq=1, params=_params(kit, "B", k="2.9"), dataset=base.dataset,
                      summary=base.summary)
    wrong = []
    accepted = _outcome(lambda: kit.evaluate(base, stress, long_only, random_entry, robustness))
    if accepted is not None:
        wrong.append(f"fixture: the consistent records were refused: {accepted!r}")
    if other_base.run_id == base.run_id or (other_base.status, other_base.purpose, other_base.variant) != ("ok", "select", "B"):
        wrong.append("fixture: the other select ok of B")
    for label, slot, record, name in (
        ("a stress record of variant A", "stress", replace(stress, variant="A"), "variant"),
        ("a long-only record on another select ok of B", "long_only",
         replace(long_only, base_run_id=other_base.run_id), "base_run_id"),
        ("a random-entry record with another rollover zone", "random_entry",
         replace(random_entry, rollover_zone="Europe/London"), "rollover_zone"),
    ):
        differs = [item.name for item in fields(record) if getattr(record, item.name) != getattr(consistent[slot], item.name)]
        if differs != [name]:
            wrong.append(f"fixture: {label} differs in {differs}")
        inputs = {**consistent, slot: record}
        error = _outcome(lambda: kit.evaluate(base, inputs["stress"], inputs["long_only"], inputs["random_entry"],
                                              robustness))
        if not _is(kit, error, "research"):
            wrong.append(f"{label}: expected ResearchError, got {error!r}")
    assert not wrong, "AC-05:\n" + "\n".join(wrong)


def test_ac06_r2_an_interrupted_stress_and_its_rerun_in_the_stress_row_and_the_budget(monkeypatch, tmp_path):
    """F2: the stress "งบ" column is {ok}/1 and "นับงบ" counts every stress started line, reruns included."""
    kit = _kit(monkeypatch, "AC-06", "render_report")
    g = kit.g
    records = _report_registry(kit, tmp_path / "registry.jsonl", g["REPORT_RERUN_RECORDS"])
    interrupted, rerun, ok = records[3], records[4], records[5]
    text = g["REPORT_RERUN"]
    wrong = []
    if ((interrupted.status, rerun.status, ok.status, ok.started_seq) != ("started", "started", "ok", 4)
            or replace(interrupted, seq=4) != rerun):
        wrong.append("fixture: seq 3 is an interrupted stress line, seq 4 its rerun and seq 5 the rerun's ok")
    if "\n| B | stress | 2 | 1 | 0 | 1 | 1/1 |\n" not in text or "\nรวมที่นับงบ: 3/63\n" not in text:
        wrong.append("fixture: the golden stress row or budget line")
    wrong += _text_diff(kit.render_report(tuple(records.values()), {}), text) + _layout_rules(text)
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


def test_ac06_r2_records_out_of_seq_order_give_the_same_report(monkeypatch, tmp_path):
    """F3 (a): the bullets follow seq and every count is free of order, so the input order changes nothing."""
    kit = _kit(monkeypatch, "AC-06", "render_report", "Evaluation", "Check")
    g = kit.g
    table = _report_registry(kit, tmp_path / "registry.jsonl", g["REPORT_RECORDS"])
    records = tuple(table.values())
    evaluations = _report_evaluations(kit, table)
    rerun = tuple(_report_registry(kit, tmp_path / "rerun.jsonl", g["REPORT_RERUN_RECORDS"]).values())
    wrong = []
    for label, order in (("reversed", records[::-1]), ("odd seq first", records[0::2] + records[1::2])):
        if order == records or sorted(record.seq for record in order) != [record.seq for record in records]:
            wrong.append(f"fixture: {label} is not another order of the same records")
        wrong += [f"{label}, three evaluations: {item}"
                  for item in _text_diff(kit.render_report(order, evaluations), g["REPORT_FULL"])]
        wrong += [f"{label}, no evaluation: {item}"
                  for item in _text_diff(kit.render_report(order, {}), g["REPORT_NO_EVALUATION"])]
    wrong += [f"the rerun registry reversed: {item}"
              for item in _text_diff(kit.render_report(rerun[::-1], {}), g["REPORT_RERUN"])]
    assert not wrong, "AC-06:\n" + "\n".join(wrong)


# ======================================================================= tests r3 (implementation review r1 F4)
# Appended by the round-3 test author under contract v1.5 (docs/reviews/CORE-008-r1.md F4). Every statement
# above is unchanged and the conventions of the module docstring hold. The known answers and their arithmetic
# are in the "tests r3" part of tests/golden/CORE-008/research_cases.py.


class _WindowBaseline(_Baseline):
    """random_entry_baseline on the WINDOW series (golden r3) with RUN_PARAMS (V-B) and a hand-built variant."""

    def __init__(self, kit, spec, summary):
        g = kit.g
        self.kit = kit
        self.m1 = tuple(_m1(kit, row) for row in g["window_m1_rows"]())
        self.m15 = _m15(kit, self.m1)
        self.params = _run_params(kit)
        self.model = _flat_model(kit)
        self.dataset = _dataset(kit, g["WINDOW_DATASET"])
        self.variant = self.result(spec)
        self.summary = _summary(kit, summary)


def _window_variant_premises(kit, bench):
    """Fixture: every variant trade leaves by "signal" one M1 after its entry and the hand summary is its own."""
    index = {bar.time_raw: position for position, bar in enumerate(bench.m1)}
    holds = [(t.exit_reason, t.ambiguous, index.get(t.exit_time_raw, -1) - index[t.entry_time_raw])
             for t in bench.variant.trades]
    wrong = []
    if any(hold != ("signal", False, 1) for hold in holds):
        wrong.append(f"fixture: the variant trades close {holds}, expected signal exits with hold 1")
    if kit.summarize(bench.variant, kit.rule) != bench.summary:
        wrong.append(f"fixture: summarize of the {len(holds)}-trade variant is not its hand summary")
    return wrong


def _window_premises(kit, bench):
    """Fixture: the layout of the WINDOW series, the New York window of each bar open, no blocker but the window
    from bar 97 on, the contract's eligible set and the other sets of the three wrong rules, and the r of a
    trade entering each bar."""
    g = kit.g
    m1, m15 = bench.m1, bench.m15
    blockers = kit.strategy.entry_blockers
    rows = kit.strategy.indicators(m15, bench.params)
    opens = [item.bar.time_utc for item in m15]
    wrong = []
    if (tuple(moment.strftime("%Y-%m-%dT%H:%M") for moment in opens) != g["WINDOW_BAR_OPENS"]
            or len(m1) != g["WINDOW_M1_COUNT"]
            or any(m1[2 * u].time_raw != item.bar.time_raw or m1[2 * u + 1].time_raw != item.bar.time_raw + 300
                   or item.flags or item.bar.spread != g["window_spread"](u) for u, item in enumerate(m15))):
        wrong.append("fixture: the layout of the window series (bar opens, two M1 per bar, spreads, no flags)")
    windows = {u: kit.tb.in_entry_window(opens[u]) for u in g["WINDOW_IN"]}
    if windows != g["WINDOW_IN"]:
        wrong.append(f"fixture: in_entry_window of the bar opens {windows}, expected {g['WINDOW_IN']}")
    inside = _utc(g["WINDOW_INSIDE"])
    warm = g["WINDOW_WARM_FROM"]
    if any("warmup" not in blockers(rows[t], inside) for t in range(warm)):
        wrong.append(f"fixture: a bar before {warm} is not blocked by warmup")
    other = {t: blockers(rows[t], inside) for t in range(warm, len(m15)) if blockers(rows[t], inside)}
    if other:
        wrong.append(f"fixture: blockers other than the window from bar {warm} on: {other}")
    last = len(m15) - 1
    later = opens[last] + timedelta(minutes=15)
    for label, expected, got in (
        ("the contract (bar t+1's open, t <= len(m15) - 2)", g["WINDOW_ELIGIBLE"],
         [t for t in range(last) if blockers(rows[t], opens[t + 1]) == ()]),
        ("bar t's own open", g["WINDOW_OWN_OPEN"], [t for t in range(last) if blockers(rows[t], opens[t]) == ()]),
        ("no window check", g["WINDOW_NO_WINDOW"],
         [t for t in range(last) if set(blockers(rows[t], opens[t + 1])) <= {"outside_window"}]),
        ("the last bar at its own open and 15 minutes later", (last,),
         [t for t in (last,) if blockers(rows[t], opens[t]) == () and blockers(rows[t], later) == ()]),
    ):
        if tuple(got) != tuple(expected):
            wrong.append(f"fixture: eligible by {label}: {got}, expected {expected}")
    for u, text in g["WINDOW_ENTRY_R"].items():
        for side in ("long", "short"):
            trade = kit.bt.simulate_trade(m1, 2 * u, side, Decimal("3"), Decimal("0.02"), bench.model, _rollover(kit),
                                          risk_money=Decimal("25"), exit_index=2 * u + 1)
            if (trade.exit_reason, trade.ambiguous, trade.r) != ("signal", False, Decimal(text)):
                wrong.append(f"fixture: a {side} trade entering bar {u}: {trade.exit_reason} r {trade.r}, "
                             f"expected signal r {text}")
    if len(set(g["WINDOW_ENTRY_R"].values())) != len(g["WINDOW_ENTRY_R"]):
        wrong.append("fixture: two entry bars give the same r")
    return wrong


def test_ac04_r3_eligible_bars_are_judged_in_the_entry_window_at_the_open_of_bar_t_plus_1(monkeypatch, tmp_path):
    """F4 (baseline step 4): at both window edges and around the gaps the contract's eligible bars are
    (98, 99, 100, 102, 104): every round's first randrange gets n = 5 and each scripted draw enters its bar."""
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "BaselineResult", "summarize")
    g = kit.g
    bench = _WindowBaseline(kit, g["WINDOW_VARIANT"], g["WINDOW_SUMMARY"])
    wrong = _window_premises(kit, bench) + _window_variant_premises(kit, bench)
    path = tmp_path / "registry.jsonl"
    base = bench.base(path)
    fake = _fake_random(lambda: cycle(g["WINDOW_SCRIPT"]))
    monkeypatch.setattr(random, "Random", fake)
    sizer = _Sizer(kit)
    result = bench.call(base.run_id, path, sizer=sizer)
    seed = int(base.run_id[:15], 16)
    eligible = g["WINDOW_ELIGIBLE"]
    if len(fake.instances) != 1 or _seed_of(fake.instances[0]) != seed:
        wrong.append(f"random.Random built {len(fake.instances)} times, seeds {[_seed_of(item) for item in fake.instances]}"
                     f", expected one with {seed}")
    elif fake.instances[0].calls != list(g["WINDOW_SCRIPT_N"]) * 1000:
        calls = fake.instances[0].calls
        wrong.append(f"randrange arguments {calls[:9]}... ({len(calls)} calls), expected "
                     f"{list(g['WINDOW_SCRIPT_N'])} in every round: the first n is len(eligible) = {len(eligible)}, "
                     f"eligible {eligible}")
    if type(result) is not kit.BaselineResult:
        pytest.fail(f"AC-04: random_entry_baseline returned {result!r}", pytrace=False)
    got = result.expectancies_r
    expected_r = tuple(Decimal(g["WINDOW_ROUND_EXPECTANCY"][i % 5]) for i in range(1000))
    if type(got) is not tuple or any(type(item) is not Decimal for item in got) or got != expected_r:
        bar_of = {Decimal(text): u - 1 for u, text in g["WINDOW_ENTRY_R"].items()}
        drawn = [bar_of.get(item, item) for item in tuple(got)[:10]]
        wrong.append(f"bars drawn in rounds 1-10 (t named by the round's r): {drawn}, expected "
                     f"{[g['WINDOW_DRAWS'][i % 5] for i in range(10)]} ({len(got)} rounds)")
    expected = _baseline(kit, g["WINDOW_BASELINE"], seed)
    wrong += _check_baseline_summary(kit, result.summary, expected, "summary")
    if len(sizer.calls) != 1000 or any(call != (Decimal("10000"), Decimal("3")) for call in sizer.calls):
        wrong.append(f"sizer calls: {len(sizer.calls)}, the first {sizer.calls[:3]}")
    lines, last = _check_lines(kit, bench, path, base, expected, "lines", 2)
    wrong += lines
    if last is not None and result.record != last:
        wrong.append("the returned record is not the ok line")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_r3_k_equal_to_len_eligible_draws_each_eligible_bar_and_one_more_trade_is_refused(monkeypatch, tmp_path):
    """F4 (baseline steps 4 and 7): with len(eligible) = 5, K = 5 empties every round's pool with the five
    eligible bars, and K = 6 is a ResearchError before the started line."""
    kit = _kit(monkeypatch, "AC-04", "random_entry_baseline", "BaselineResult", "summarize")
    g = kit.g
    five = _WindowBaseline(kit, g["WINDOW_VARIANT_5"], g["WINDOW_SUMMARY_5"])
    six = _WindowBaseline(kit, g["WINDOW_VARIANT_6"], g["WINDOW_SUMMARY_6"])
    wrong = _window_variant_premises(kit, five) + _window_variant_premises(kit, six)
    path = tmp_path / "five.jsonl"
    base = five.base(path)
    fake = _fake_random(lambda: cycle((0,)))
    monkeypatch.setattr(random, "Random", fake)
    sizer = _Sizer(kit)
    result = five.call(base.run_id, path, sizer=sizer)
    made = list(fake.instances)
    seed = int(base.run_id[:15], 16)
    if len(made) != 1 or _seed_of(made[0]) != seed:
        wrong.append(f"random.Random built {len(made)} times, seeds {[_seed_of(item) for item in made]}, "
                     f"expected one with {seed}")
    elif made[0].calls != list(g["WINDOW_ALL_SCRIPT_N"]) * 1000:
        calls = made[0].calls
        wrong.append(f"randrange arguments {calls[:15]}... ({len(calls)} calls), expected "
                     f"{list(g['WINDOW_ALL_SCRIPT_N'])} in every round (pool 5, 4, 3, 2, 1)")
    if type(result) is not kit.BaselineResult:
        pytest.fail(f"AC-04: random_entry_baseline returned {result!r}", pytrace=False)
    got = result.expectancies_r
    if (type(got) is not tuple or len(got) != 1000 or any(type(item) is not Decimal for item in got)
            or set(got) != {Decimal(g["WINDOW_ALL_EXPECTANCY"])}):
        wrong.append(f"round expectancies {sorted(set(got))} ({len(got)} rounds), expected only "
                     f"{g['WINDOW_ALL_EXPECTANCY']}: the mean r of the five eligible bars")
    expected = _baseline(kit, g["WINDOW_ALL_BASELINE"], seed)
    wrong += _check_baseline_summary(kit, result.summary, expected, "summary")
    if len(sizer.calls) != 5000 or any(call != (Decimal("10000"), Decimal("3")) for call in sizer.calls):
        wrong.append(f"sizer calls: {len(sizer.calls)}, the first {sizer.calls[:3]}")
    lines, _ = _check_lines(kit, five, path, base, expected, "lines", 2)
    wrong += lines
    other = tmp_path / "six.jsonl"
    own = six.base(other)
    wrong += _refusal(kit, other, "research", lambda: six.call(own.run_id, other),
                      "a variant of 6 trades on 5 eligible bars")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)
