"""Approved ENV-002 v1.6 contract tests for AC-04 (docs/contracts/ENV-002-research-host-separation.md);
run pytest from the repository root.

synthetic.py (next to this file) is loaded by the contract's recipe. Its bars go into the merged
sochron.research (run_variant, random_entry_baseline, HoldoutRefused, HOLDOUT_CUTOFF_UTC, Dataset,
read_records); the other inputs are built from the merged sochron.backtest (Rollover, SizedLots),
sochron.costs (H001_COSTS), sochron.strategy (H001Params), sochron.timebase (rule_for, bar_open,
to_utc), sochron.core (Bar) and sochron.data.snapshot (AggregatedBar). ENV-002 changes none of them:
these tests fix what the excluded period means for research.

Conventions the contract leaves to these tests (also in docs/handoff/ENV-002.md):
1. The excluded period starts at HOLDOUT_CUTOFF_UTC, 2025-01-01T00:00:00Z, inclusive. The cases are the
   contract's 2025-01-02, 60 bars from the cutoff itself, one bar exactly at the cutoff, and 60 bars
   that cross it (the first 30 before it).
2. Every other input is valid. The same inputs built from bars before the cutoff (2024-12-02) run and
   are recorded (started, ok), so a refusal can only come from the period. random_entry_baseline gets
   that run's ok record as its base and its Result as its variant.
3. M15 bars are AggregatedBar values built from their M1 (first open, highest high, lowest low, last
   close, the last spread), no flags. The Dataset matches the bars (start, end exclusive, count); one
   case labels the excluded bars with a Dataset that ends at the cutoff.
4. "The registry does not change": the registry file keeps its bytes, the folder keeps its file list, and a
   registry path that did not exist still does not exist.
"""

import importlib.util
import os
import sys
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
SYNTHETIC = REPO / "tests" / "acceptance" / "ENV-002" / "synthetic.py"
SERVER = "Exness-MT5Trial14"
CODE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
SIZER_LABEL = "fixed-0.02"
EQUITY = Decimal("10000")
CUTOFF = datetime(2025, 1, 1, tzinfo=UTC)
BEFORE = datetime(2024, 12, 2, tzinfo=UTC)
EXCLUDED = (
    ("2025-01-02, the contract's day", datetime(2025, 1, 2, tzinfo=UTC), 60),
    ("from the cutoff itself", CUTOFF, 60),
    ("one bar exactly at the cutoff", CUTOFF, 1),
    ("across the cutoff", CUTOFF - timedelta(minutes=30), 60),
)
_MINUTE = timedelta(minutes=1)


def _synthetic():
    """synthetic.py by the contract's recipe."""
    spec = importlib.util.spec_from_file_location("synthetic", SYNTHETIC)
    module = importlib.util.module_from_spec(spec)
    sys.modules["synthetic"] = module
    spec.loader.exec_module(module)
    return module


def _kit():
    names = {"research": ("run_variant", "random_entry_baseline", "HoldoutRefused", "HOLDOUT_CUTOFF_UTC",
                          "Dataset", "read_records"),
             "backtest": ("Rollover", "SizedLots"), "costs": ("H001_COSTS",), "strategy": ("H001Params",),
             "timebase": ("rule_for", "bar_open", "to_utc", "to_raw"), "core": ("Bar",),
             "data.snapshot": ("AggregatedBar",)}
    kit = SimpleNamespace()
    for package, symbols in names.items():
        try:
            module = import_module(f"sochron.{package}")
        except ImportError as error:
            pytest.fail(f"AC-04: sochron.{package} not implemented ({error})", pytrace=False)
        for symbol in symbols:
            if not hasattr(module, symbol):
                pytest.fail(f"AC-04: sochron.{package}.{symbol} not implemented", pytrace=False)
            setattr(kit, symbol, getattr(module, symbol))
    kit.synthetic_bars = getattr(_synthetic(), "synthetic_bars")
    kit.rule = kit.rule_for(SERVER)
    kit.params = kit.H001Params(variant="B", f=8, s=32, n=10, theta=Decimal("0.50"), N=48, M=24, k=Decimal("3.0"))
    kit.rollover = kit.Rollover("America/New_York", time(17, 0))
    return kit


def _m15(kit, m1):
    groups = {}
    for bar in m1:
        groups.setdefault(kit.bar_open(bar.time_raw, 15, kit.rule), []).append(bar)
    out = []
    for opened, members in groups.items():
        bar = kit.Bar(time_raw=opened, time_utc=kit.to_utc(opened, kit.rule), timeframe=15, open=members[0].open,
                      high=max(item.high for item in members), low=min(item.low for item in members),
                      close=members[-1].close, spread=members[-1].spread, tick_volume=len(members),
                      m1_count=len(members))
        out.append(kit.AggregatedBar(bar, frozenset()))
    return tuple(out)


def _dataset(kit, m1, *, start=None, end=None):
    return kit.Dataset(snapshot_id="SYN-ENV002", manifest_sha256="0" * 64,
                       period_start_utc=start or m1[0].time_utc, period_end_utc=end or m1[-1].time_utc + _MINUTE,
                       m1_bars=len(m1))


def _sizer(kit):
    def sizer(equity, stop_distance):
        return kit.SizedLots(lots=Decimal("0.02"), risk_money=Decimal("25"), actual_risk=None, reason="fixed")
    return sizer


def _run_variant(kit, m1, m15, dataset, registry):
    return kit.run_variant(m1, m15, kit.params, kit.H001_COSTS, _sizer(kit), EQUITY, kit.rule, kit.rollover,
                           purpose="select", dataset=dataset, code_commit=CODE_COMMIT, sizer_label=SIZER_LABEL,
                           registry=registry)


def _baseline(kit, m1, m15, dataset, registry, variant, base_run_id):
    return kit.random_entry_baseline(m1, m15, kit.params, kit.H001_COSTS, _sizer(kit), EQUITY, kit.rule,
                                     kit.rollover, variant, base_run_id=base_run_id, dataset=dataset,
                                     code_commit=CODE_COMMIT, sizer_label=SIZER_LABEL, registry=registry)


def _before_cutoff_run(kit, registry):
    m1 = kit.synthetic_bars(BEFORE, 60)
    return _run_variant(kit, m1, _m15(kit, m1), _dataset(kit, m1), registry)


def _outcome(call):
    try:
        call()
    except Exception as error:  # the error object is what the test compares
        return error
    return None


def test_ac04_synthetic_bars_are_contiguous_m1_under_the_measured_rule():
    kit = _kit()
    wrong = []
    for label, start, count in (("before the cutoff", BEFORE, 60), *EXCLUDED):
        bars = kit.synthetic_bars(start, count)
        if not isinstance(bars, list) or len(bars) != count:
            wrong.append(f"{label}: {type(bars).__name__} of {len(bars)}, expected a list of {count}")
            continue
        for index, bar in enumerate(bars):
            moment = start + index * _MINUTE
            if type(bar) is not kit.Bar:
                wrong.append(f"{label}[{index}]: {type(bar).__name__}, expected core.Bar")
                continue
            if bar.time_utc != moment or bar.time_raw != kit.to_raw(moment, kit.rule):
                wrong.append(f"{label}[{index}]: time {bar.time_raw}/{bar.time_utc}, expected {moment}")
            if kit.to_utc(bar.time_raw, kit.rule) != bar.time_utc:
                wrong.append(f"{label}[{index}]: time_raw and time_utc disagree under {SERVER}")
            if bar.timeframe != 1 or not (Decimal(0) < bar.low <= min(bar.open, bar.close)
                                           <= max(bar.open, bar.close) <= bar.high):
                wrong.append(f"{label}[{index}]: not a valid M1 OHLC bar: {bar}")
            if len({bar.open, bar.high, bar.low, bar.close}) != 1 or bar.open != bars[0].open:
                wrong.append(f"{label}[{index}]: the price is not constant")
            if type(bar.spread) is not int or bar.spread < 0:
                wrong.append(f"{label}[{index}]: spread {bar.spread!r}")
    if kit.synthetic_bars(BEFORE, 0) != []:
        wrong.append("count 0 is not an empty list")
    assert not wrong, "AC-04 synthetic_bars:\n" + "\n".join(wrong)


def test_ac04_the_same_inputs_before_the_cutoff_run_and_are_recorded(tmp_path):
    kit = _kit()
    registry = tmp_path / "registry.jsonl"
    record, _ = _before_cutoff_run(kit, registry)
    statuses = [item.status for item in kit.read_records(registry)]
    assert statuses == ["started", "ok"] and record.status == "ok", f"AC-04: the control run wrote {statuses}"


@pytest.mark.parametrize("label, start, count", EXCLUDED, ids=[case[0] for case in EXCLUDED])
def test_ac04_excluded_period_bars_are_refused_and_the_registry_is_unchanged(tmp_path, label, start, count):
    kit = _kit()
    registry = tmp_path / "registry.jsonl"
    record, result = _before_cutoff_run(kit, registry)
    fresh = tmp_path / "fresh" / "registry.jsonl"
    fresh.parent.mkdir()
    m1 = kit.synthetic_bars(start, count)
    m15 = _m15(kit, m1)
    dataset = _dataset(kit, m1)
    labelled = _dataset(kit, m1, start=CUTOFF - timedelta(days=30), end=CUTOFF)
    if not any(bar.time_utc >= kit.HOLDOUT_CUTOFF_UTC for bar in m1):
        pytest.fail(f"AC-04 {label}: the bars do not reach the cutoff", pytrace=False)
    calls = (
        ("run_variant", lambda: _run_variant(kit, m1, m15, dataset, registry)),
        ("run_variant, Dataset labelled to end at the cutoff", lambda: _run_variant(kit, m1, m15, labelled, registry)),
        ("run_variant on a registry that does not exist yet", lambda: _run_variant(kit, m1, m15, dataset, fresh)),
        ("random_entry_baseline", lambda: _baseline(kit, m1, m15, dataset, registry, result, record.run_id)),
        ("random_entry_baseline, Dataset labelled to end at the cutoff",
         lambda: _baseline(kit, m1, m15, labelled, registry, result, record.run_id)),
    )
    wrong = []
    for name, call in calls:
        before = (registry.read_bytes(), sorted(os.listdir(tmp_path)), sorted(os.listdir(fresh.parent)))
        error = _outcome(call)
        if not isinstance(error, kit.HoldoutRefused):
            wrong.append(f"{name}: expected HoldoutRefused, got {error!r}")
        after = (registry.read_bytes(), sorted(os.listdir(tmp_path)), sorted(os.listdir(fresh.parent)))
        if after != before:
            wrong.append(f"{name}: the registry or its folder changed")
    if fresh.exists():
        wrong.append("a registry that did not exist was created")
    assert not wrong, f"AC-04 {label}:\n" + "\n".join(wrong)
