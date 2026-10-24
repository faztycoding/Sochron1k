"""Approved CORE-007 contract tests (docs/contracts/CORE-007-backtest.md v1.4); run pytest from the
repository root.

Only contract names are used: sochron.backtest (BACKTEST_VERSION, Side, Sizer, SizedLots, Rollover,
Trade, Skip, Result, BacktestError, simulate_trade, run) and, to build inputs and expectations, the
merged modules sochron.core (Bar), sochron.costs (H001_COSTS, CONTEXT, CostBreakdown, BadVolume,
stress), sochron.timebase (TimeRule, rule_for, bar_open), sochron.strategy (H001Params,
STRATEGY_VERSION) and sochron.data.snapshot (AggregatedBar, aggregate, ValidationReport,
H001_CLOSURES). Every bar is synthetic. The hand-computed values and their arithmetic are in
tests/golden/CORE-007/backtest_cases.py.

Conventions the contract leaves to these tests (also in docs/handoff/CORE-007.md):
1. SizedLots, Rollover, Trade, Skip and Result are frozen dataclasses whose fields are exactly the
   contract's names in the contract's order. BacktestError is a public name and a ValueError.
   get_args(Side) is ("long", "short"); Sizer is a Callable of (Decimal, Decimal) to SizedLots.
2. Trade: prices, stop_distance, stop_price, lots, money, risk_money and r are exactly Decimal (the
   golden values are compared as Decimal values, never as strings); times, spread points and
   nights exactly int; ambiguous exactly bool; data_flags a frozenset of str; costs exactly
   costs.CostBreakdown with the model's stress_factor. Skip.time_raw is an int and Skip.reasons a
   tuple of str. Result.equity is a tuple of (int, Decimal) tuples; trades and skips are compared
   as sequences (their container type is not fixed by the contract).
3. Wrong type is TypeError: float, int or bool where a Decimal is required, bool or float for an
   index, any subclass (Decimal, str, Bar, Rollover, SizedLots), None where a value is required,
   a set or tuple where a frozenset is required, a generator for m1 or m15, an M15 item whose .bar
   is not exactly core.Bar or whose .flags is not a frozenset of str, a sizer result that is not
   exactly SizedLots and a sizer that is not callable. A right type with a wrong value is
   BacktestError, non-finite Decimals (NaN, sNaN, Infinity, -Infinity) included. An unknown zone
   includes the empty string. Errors of sochron.costs (BadVolume) and of the sizer reach the
   caller unchanged: the same exception object, never wrapped. SizedLots checks exactly the
   contract's list, so lots of 0 or below pass it and run refuses them through
   costs.check_volume (BadVolume), like lots off the 0.01 grid or above volume_max.
4. simulate_trade's per-M1 checks are tested only on M1 the call must read: the entry M1, an M1
   before exit_index with the stop far away, the exit_index M1, and the last M1 of an end of data.
5. run's input checks use a small valid dataset (4 M15 bars of 15 M1, no entry) and change one
   thing per case. M15 bars are built from M1 with sochron.data.snapshot.aggregate (the R1 path);
   data_flags cases replace the flags of chosen bars; one case passes a test-local duck type.
6. No overlapping positions: each trade's exit_time_raw is earlier than the next trade's
   entry_time_raw (a decision is either an exit or an entry, and an entry fills at the next bar).
7. AC-05: u is the M15 bar holding trade k's exit M1 (timebase.bar_open). The cut keeps the M15
   objects 0..u unchanged and the M1 inside them; the cut run must give exactly trades 1..k, the
   Skips with time_raw before u's open and equity points 0..k. The run -> simulate_trade mapping:
   entry_index is the M1 of entry_time_raw (the first M1 of its M15 bar); exit_index is the M1 of
   exit_time_raw when exit_reason is "signal" or ambiguous is True (an exit decided by the
   strategy), otherwise None; data_flags is the union of M15 flags from the bar before the entry
   bar (the decision bar t) to u.
8. Nights: entry exactly at a rollover does not count it; exit exactly at one does (entry < T <=
   exit). Stress: with stress(model, 2) every one of spread, commission, slippage, swap and total
   is exactly twice the 1x value, also for a model whose commission and short swap are not zero.
9. The numbers do not depend on the caller's Decimal context (contract: computed in
   sochron.costs.CONTEXT), and the caller's context is left as it was.

Round 2 (tests r2: contract v1.5 and docs/reviews/CORE-007-tests-r1.md F1, F2, F4, F5, F7) appends
tests after the last round-1 test and changes nothing above them. Its conventions:
10. Result.trades and Result.skips are exactly tuple (contract v1.5 item 5).
11. sides with an element that is not exactly str (a str subclass included) is TypeError (v1.5
    item 4); so is a data_flags element that is not exactly str, or a frozenset subclass as
    data_flags (convention 3).
12. An M15 bar whose time_utc differs from timebase.to_utc(time_raw, rule) is BacktestError (v1.5
    item 6), tested with AggregatedBar and with a duck-typed M15 item, each with a UTC time_utc.
13. Round-2 run scenarios may drop M1 rows, so an M15 bar from aggregate can be "incomplete" and
    lack its minute 0: entries and strategy exits fill at the first M1 present in the bar, and the
    first equity point is the first M1, not the first M15 bar's time.
"""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, dataclass, fields, is_dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_UP, Decimal, Inexact, Rounded, getcontext, localcontext
from importlib import import_module
from pathlib import Path
from runpy import run_path
from types import MappingProxyType, SimpleNamespace
from typing import ForwardRef, get_args, get_origin

import pytest


_MODULES = {"backtest": "sochron.backtest", "core": "sochron.core", "costs": "sochron.costs",
            "timebase": "sochron.timebase", "strategy": "sochron.strategy",
            "snapshot": "sochron.data.snapshot"}
_TRADE_FIELDS = ("side", "entry_time_raw", "entry_bid", "entry_spread_points", "exit_time_raw", "exit_bid",
                 "exit_spread_points", "lots", "stop_distance", "stop_price", "exit_reason", "ambiguous",
                 "nights", "triple_nights", "costs", "gross_money", "net_money", "risk_money", "actual_risk",
                 "r", "data_flags")
_SHAPES = {
    "SizedLots": ("lots", "risk_money", "actual_risk", "reason"),
    "Rollover": ("zone", "at"),
    "Trade": _TRADE_FIELDS,
    "Skip": ("time_raw", "reasons"),
    "Result": ("trades", "skips", "equity", "backtest_version", "strategy_version"),
}
_NON_FINITE = ("NaN", "sNaN", "Infinity", "-Infinity")
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_FLAT5 = tuple((f"2026-03-10T14:0{minute}", "4000.00", "4000.50", "3999.50", "4000.00", 200)
               for minute in range(5))


class _Dec(Decimal):
    pass


class _Str(str):
    pass


class _SizerFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class _DuckM15:
    """An M15 bar that is not sochron.data.snapshot.AggregatedBar (contract: duck typing, D9)."""

    bar: object
    flags: object


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
        try:
            symbols.append(getattr(module, attribute))
        except AttributeError:
            pytest.fail(f"{ac}: {module_name}.{attribute} not implemented", pytrace=False)
    return tuple(symbols)


def _golden():
    return run_path(str(Path(__file__).resolve().parents[2] / "golden/CORE-007/backtest_cases.py"))


def _kit(monkeypatch, ac, *names):
    """The named sochron.backtest symbols plus the merged modules the tests build inputs with."""
    symbols = _api(monkeypatch, ac, *(f"backtest.{name}" for name in names))
    kit = SimpleNamespace(**dict(zip(names, symbols)))
    kit.ac = ac
    kit.Bar = import_module("sochron.core").Bar
    kit.costs = import_module("sochron.costs")
    kit.tb = import_module("sochron.timebase")
    kit.strategy = import_module("sochron.strategy")
    kit.snapshot = import_module("sochron.data.snapshot")
    kit.golden = _golden()
    kit.rule = kit.tb.rule_for(kit.golden["RULE_SERVER"])
    return kit


def _rollover(kit):
    zone, hour, minute = kit.golden["ROLLOVER"]
    return kit.Rollover(zone, time(hour, minute))


def _dec(value):
    return None if value is None else Decimal(value)


def _utc(stamp):
    return datetime.fromisoformat(stamp).replace(tzinfo=UTC)


def _raw(stamp):
    """Raw MT5 seconds of a UTC stamp under the measured rule (offset 0, CORE-001)."""
    return (_utc(stamp) - _EPOCH) // timedelta(seconds=1)


def _context_state():
    context = getcontext()
    return (context.prec, context.rounding, context.Emin, context.Emax, context.capitals,
            context.clamp, dict(context.traps), dict(context.flags))


def _hostile(context):
    """A caller context that changes every rounded result if the module used it."""
    context.prec = 4
    context.rounding = ROUND_UP
    context.traps[Inexact] = True
    context.traps[Rounded] = True
    context.clear_flags()


# ----------------------------------------------------------------------------------- builders

def _m1(kit, stamp, open_, high, low, close, spread):
    """One synthetic M1 bid bar opening at `stamp` (UTC)."""
    return kit.Bar(time_raw=_raw(stamp), time_utc=_utc(stamp), timeframe=1, open=Decimal(open_),
                   high=Decimal(high), low=Decimal(low), close=Decimal(close), spread=spread, tick_volume=1,
                   m1_count=1)


def _m1s(kit, rows):
    return tuple(_m1(kit, *row) for row in rows)


def _m15(kit, m1, flags=None):
    """M15 bars from M1 through snapshot.aggregate; flags {t: codes} replaces the flags of bar t."""
    snapshot = kit.snapshot
    report = snapshot.ValidationReport(defects=(), days=MappingProxyType({}), m1_bars=len(m1),
                                       calendar=snapshot.H001_CLOSURES)
    bars = snapshot.aggregate(m1, 15, kit.rule, report)
    assert all(not item.flags for item in bars), "fixture: every M15 bar has all 15 minutes"
    flags = flags or {}
    return tuple(snapshot.AggregatedBar(item.bar, frozenset(flags[t])) if t in flags else item
                 for t, item in enumerate(bars))


def _params(kit, values=None):
    values = dict(values or kit.golden["RUN_PARAMS"])
    values["theta"] = Decimal(values["theta"])
    values["k"] = Decimal(values["k"])
    return kit.strategy.H001Params(**values)


def _scenario_data(kit, scenario):
    rows = kit.golden["run_m1_rows"](start=scenario["start"], bars=scenario["bars"],
                                     gap_after=scenario["gap_after"])
    m1 = _m1s(kit, rows)
    return m1, _m15(kit, m1, scenario["flags"])


class _Sizer:
    """A scripted sizer: hands out the golden responses in call order and records every call."""

    def __init__(self, kit, responses):
        self.kit = kit
        self.responses = list(responses)
        self.calls = []

    def __call__(self, equity, stop_distance):
        self.calls.append((equity, stop_distance))
        if not self.responses:
            pytest.fail(f"{self.kit.ac}: the sizer was called more often than the golden scenario expects",
                        pytrace=False)
        lots, risk_money, actual_risk, reason = self.responses.pop(0)
        return self.kit.SizedLots(lots=_dec(lots), risk_money=Decimal(risk_money),
                                  actual_risk=_dec(actual_risk), reason=reason)


def _run_scenario(kit, name, *, m1=None, m15=None, sides=None):
    scenario = kit.golden["SCENARIOS"][name]
    if m1 is None:
        m1, m15 = _scenario_data(kit, scenario)
    sizer = _Sizer(kit, scenario["responses"])
    result = kit.run(m1, m15, _params(kit), kit.costs.H001_COSTS, sizer, Decimal(scenario["start_equity"]),
                     kit.rule, _rollover(kit), sides=frozenset(sides or scenario["sides"]))
    return result, sizer, m1, m15


def _small(kit):
    """A valid dataset with no entry: 4 flat M15 bars of 15 M1 from 2026-03-10T14:00 UTC."""
    m1 = _m1s(kit, kit.golden["run_m1_rows"](start="2026-03-10T14:00", bars=4))
    return m1, _m15(kit, m1)


_DEFAULT = object()  # "use the valid value": lets a test pass None itself


def _or(value, default):
    return default if value is _DEFAULT else value


def _run_small(kit, m1, m15, *, params=_DEFAULT, model=_DEFAULT, sizer=_DEFAULT, equity=_DEFAULT,
               rule=_DEFAULT, rollover=_DEFAULT, sides=_DEFAULT):
    """run on the small dataset; every argument can be replaced. A sizer call fails the test."""
    return kit.run(m1, m15, _or(params, _params(kit)), _or(model, kit.costs.H001_COSTS),
                   _or(sizer, _Sizer(kit, ())), _or(equity, Decimal("10000")), _or(rule, kit.rule),
                   _or(rollover, _rollover(kit)), sides=_or(sides, frozenset({"long", "short"})))


def _simulate(kit, m1, *, side="long", entry_index=0, exit_index=4, stop_distance=Decimal("50.00"),
              lots=Decimal("0.10"), model=_DEFAULT, rollover=_DEFAULT, risk_money=Decimal("25"), actual_risk=None,
              data_flags=frozenset()):
    """simulate_trade on flat M1 with a stop far away; every argument can be replaced."""
    return kit.simulate_trade(m1, entry_index, side, stop_distance, lots, _or(model, kit.costs.H001_COSTS),
                              _or(rollover, _rollover(kit)), risk_money=risk_money, actual_risk=actual_risk,
                              exit_index=exit_index, data_flags=data_flags)


# ----------------------------------------------------------------------------------- checks

def _check_trade(kit, trade, expected, model, label):
    """Every field of one Trade against a golden dict: exact type and Decimal value."""
    if type(trade) is not kit.Trade:
        return [f"{label}: a {type(trade).__name__}, not a Trade"]
    entry_stamp, entry_bid, entry_spread = expected["entry"]
    exit_stamp, exit_bid, exit_spread = expected["exit"]
    want = {
        "side": expected["side"], "entry_time_raw": _raw(entry_stamp), "entry_bid": Decimal(entry_bid),
        "entry_spread_points": entry_spread, "exit_time_raw": _raw(exit_stamp), "exit_bid": Decimal(exit_bid),
        "exit_spread_points": exit_spread, "lots": Decimal(expected["lots"]),
        "stop_distance": Decimal(expected["stop_distance"]), "stop_price": Decimal(expected["stop_price"]),
        "exit_reason": expected["exit_reason"], "ambiguous": expected["ambiguous"],
        "nights": expected["nights"][0], "triple_nights": expected["nights"][1],
        "gross_money": Decimal(expected["gross"]), "net_money": Decimal(expected["net"]),
        "risk_money": Decimal(expected["risk_money"]), "actual_risk": _dec(expected["actual_risk"]),
        "r": Decimal(expected["r"]), "data_flags": frozenset(expected["data_flags"]),
    }
    kinds = {"side": str, "exit_reason": str, "ambiguous": bool, "data_flags": frozenset,
             "entry_time_raw": int, "exit_time_raw": int, "entry_spread_points": int,
             "exit_spread_points": int, "nights": int, "triple_nights": int}
    wrong = []
    for name, value in want.items():
        actual = getattr(trade, name)
        kind = kinds.get(name, Decimal)
        if not (value is None and actual is None) and type(actual) is not kind:
            wrong.append(f"{label}: {name} is {type(actual).__name__} {actual!r}, expected {kind.__name__}")
        elif actual != value:
            wrong.append(f"{label}: {name} = {actual!r}, expected {value!r}")
    if any(type(flag) is not str for flag in trade.data_flags):
        wrong.append(f"{label}: data_flags holds a non-str: {trade.data_flags!r}")
    costs = trade.costs
    if type(costs) is not kit.costs.CostBreakdown:
        return wrong + [f"{label}: costs is {type(costs).__name__}, not CostBreakdown"]
    for part, value in zip(("spread", "commission", "slippage", "swap", "total"), expected["costs"]):
        actual = getattr(costs, part)
        if type(actual) is not Decimal or actual != Decimal(value):
            wrong.append(f"{label}: costs.{part} = {actual!r}, expected {value}")
    if costs.stress_factor != model.stress_factor:
        wrong.append(f"{label}: costs.stress_factor {costs.stress_factor!r}, model {model.stress_factor!r}")
    return wrong


def _check_result(kit, result, scenario, sizer, label):
    """Trades, Skips, equity points, sizer calls and versions of one run against the golden."""
    model = kit.costs.H001_COSTS
    assert type(result) is kit.Result, f"{label}: run returned a {type(result).__name__}"
    wrong = []
    trades = tuple(result.trades)
    if len(trades) != len(scenario["trades"]):
        wrong.append(f"{label}: {len(trades)} trades, expected {len(scenario['trades'])}: {trades!r}")
    for index, (trade, expected) in enumerate(zip(trades, scenario["trades"]), start=1):
        wrong += _check_trade(kit, trade, expected, model, f"{label} trade {index}")
    skips = tuple(result.skips)
    for skip in skips:
        if (type(skip) is not kit.Skip or type(skip.time_raw) is not int or type(skip.reasons) is not tuple
                or any(type(reason) is not str for reason in skip.reasons)):
            wrong.append(f"{label}: malformed Skip {skip!r}")
    got = [(skip.time_raw, skip.reasons) for skip in skips]
    want = [(_raw(stamp), tuple(reasons)) for stamp, reasons in scenario["skips"]]
    if got != want:
        wrong.append(f"{label}: skips {got}, expected {want}")
    equity = result.equity
    if type(equity) is not tuple or any(type(point) is not tuple or len(point) != 2 or type(point[0]) is not int
                                        or type(point[1]) is not Decimal for point in equity):
        wrong.append(f"{label}: equity must be a tuple of (int, Decimal) tuples: {equity!r}")
    want_equity = tuple((_raw(stamp), Decimal(value)) for stamp, value in scenario["equity"])
    if tuple(equity) != want_equity:
        wrong.append(f"{label}: equity {equity!r}, expected {want_equity!r}")
    want_calls = [(Decimal(equity_), Decimal(stop)) for equity_, stop in scenario["calls"]]
    if sizer.calls != want_calls or any(type(a) is not Decimal or type(b) is not Decimal for a, b in sizer.calls):
        wrong.append(f"{label}: sizer calls {sizer.calls}, expected {want_calls}")
    if result.backtest_version != "backtest-v1" or type(result.backtest_version) is not str:
        wrong.append(f"{label}: backtest_version {result.backtest_version!r}")
    if result.strategy_version != kit.strategy.STRATEGY_VERSION or type(result.strategy_version) is not str:
        wrong.append(f"{label}: strategy_version {result.strategy_version!r}")
    return wrong


def _fill_case(kit, case, model=None):
    model = kit.costs.H001_COSTS if model is None else model
    return kit.simulate_trade(
        _m1s(kit, case["m1"]), case["entry_index"], case["side"], Decimal(case["stop_distance"]),
        Decimal(case["lots"]), model, _rollover(kit), risk_money=Decimal(case["risk_money"]),
        actual_risk=_dec(case["actual_risk"]), exit_index=case["exit_index"],
        data_flags=frozenset(case["data_flags"]))


def _fill_labels():
    return [case["label"] for case in _golden()["FILL_CASES"]]


# ----------------------------------------------------------------------------------- AC-01

def test_ac01_h001_example_long_and_short_through_simulate_trade(monkeypatch):
    kit = _kit(monkeypatch, "AC-01", "Rollover", "Trade", "simulate_trade")
    golden = kit.golden
    for stamp, raw in golden["ANCHORS"]:
        assert _raw(stamp) == raw, f"fixture: {stamp} is raw {raw}"
    model = kit.costs.H001_COSTS
    wrong = []
    for rows, expected in ((golden["AC01_LONG_M1"], golden["AC01_LONG"]),
                           (golden["AC01_SHORT_M1"], golden["AC01_SHORT"])):
        trade = kit.simulate_trade(_m1s(kit, rows), 0, expected["side"], Decimal("12.00"), Decimal("0.02"),
                                   model, _rollover(kit), risk_money=Decimal("25"), exit_index=2)
        wrong += _check_trade(kit, trade, expected, model, f"AC-01 {expected['side']}")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_r_is_net_over_the_formula_r_not_the_actual_risk(monkeypatch):
    """D8: H001's lot rounding leaves an actual risk of 24 USD; r still divides by risk_money 25."""
    kit = _kit(monkeypatch, "AC-01", "Rollover", "Trade", "simulate_trade")
    golden = kit.golden
    model = kit.costs.H001_COSTS
    expected = {**golden["AC01_LONG"], "actual_risk": "24"}
    trade = kit.simulate_trade(_m1s(kit, golden["AC01_LONG_M1"]), 0, "long", Decimal("12.00"), Decimal("0.02"),
                               model, _rollover(kit), risk_money=Decimal("25"), actual_risk=Decimal("24"),
                               exit_index=2)
    wrong = _check_trade(kit, trade, expected, model, "AC-01 long, actual risk 24")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


def test_ac01_values_do_not_depend_on_the_caller_decimal_context(monkeypatch):
    kit = _kit(monkeypatch, "AC-01", "Rollover", "Trade", "simulate_trade")
    golden = kit.golden
    model = kit.costs.H001_COSTS
    rollover = _rollover(kit)
    wrong = []
    for rows, expected in ((golden["AC01_LONG_M1"], golden["AC01_LONG"]),
                           (golden["AC01_SHORT_M1"], golden["AC01_SHORT"])):
        m1 = _m1s(kit, rows)
        with localcontext() as context:
            _hostile(context)
            before = _context_state()
            trade = kit.simulate_trade(m1, 0, expected["side"], Decimal("12.00"), Decimal("0.02"), model,
                                       rollover, risk_money=Decimal("25"), exit_index=2)
            if _context_state() != before:
                wrong.append(f"{expected['side']}: simulate_trade changed the caller's Decimal context")
        wrong += _check_trade(kit, trade, expected, model, f"AC-01 {expected['side']} (hostile context)")
    assert not wrong, "AC-01:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-02

@pytest.mark.parametrize("label", _fill_labels())
def test_ac02_fill_table_case(monkeypatch, label):
    kit = _kit(monkeypatch, "AC-02", "Rollover", "Trade", "simulate_trade")
    case = next(case for case in kit.golden["FILL_CASES"] if case["label"] == label)
    trade = _fill_case(kit, case)
    wrong = _check_trade(kit, trade, case["expected"], kit.costs.H001_COSTS, label)
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_fill_cases_cover_every_row_on_both_sides(monkeypatch):
    """The golden table is not vacuous: each fill-table outcome appears for both sides."""
    kit = _kit(monkeypatch, "AC-02", "simulate_trade")
    seen = set()
    for case in kit.golden["FILL_CASES"]:
        expected = case["expected"]
        entry, exit_ = expected["entry"], expected["exit"]
        rows = case["m1"]
        outcome = expected["exit_reason"], expected["ambiguous"]
        if outcome == ("stop", False):
            exit_row = next(row for row in rows if row[0] == exit_[0])
            outcome += ("gap" if Decimal(exit_[1]) == Decimal(exit_row[1]) else "touch",)
            if exit_[0] == entry[0]:
                outcome += ("entry M1",)
        seen.add((case["side"], outcome))
        if None in (row[5] for row in rows[case["entry_index"]:]):
            seen.add((case["side"], "spread None"))
    for side in ("long", "short"):
        for outcome in (("signal", False), ("stop", True), ("end_of_data", False), ("stop", False, "gap"),
                        ("stop", False, "touch"), ("stop", False, "gap", "entry M1"),
                        ("stop", False, "touch", "entry M1"), "spread None"):
            assert (side, outcome) in seen, f"fixture: no {side} case for {outcome}"


@pytest.mark.parametrize("name", ["R", "R_long_only", "R_to_103", "R_flags_ends", "R_flags_before",
                                  "R_flags_105", "R_gap", "R_window"])
def test_ac02_run_with_the_real_decide_matches_the_hand_computed_scenario(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-02", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS"][name]
    result, sizer, _, _ = _run_scenario(kit, name)
    wrong = _check_result(kit, result, scenario, sizer, scenario["label"])
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_run_does_not_depend_on_the_caller_decimal_context(monkeypatch):
    kit = _kit(monkeypatch, "AC-02", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS"]["R"]
    m1, m15 = _scenario_data(kit, scenario)
    with localcontext() as context:
        _hostile(context)
        before = _context_state()
        result, sizer, _, _ = _run_scenario(kit, "R", m1=m1, m15=m15)
        changed = _context_state() != before
    assert not changed, "AC-02: run changed the caller's Decimal context"
    wrong = _check_result(kit, result, scenario, sizer, "R under a hostile context")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_run_takes_m15_bars_by_duck_typing(monkeypatch):
    kit = _kit(monkeypatch, "AC-02", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS"]["R_flags_ends"]
    m1, m15 = _scenario_data(kit, scenario)
    ducks = tuple(_DuckM15(item.bar, item.flags) for item in m15)
    result, sizer, _, _ = _run_scenario(kit, "R_flags_ends", m1=m1, m15=ducks)
    wrong = _check_result(kit, result, scenario, sizer, "R_flags_ends with duck-typed M15")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-03

def test_ac03_public_types_versions_and_shapes(monkeypatch):
    names = ("BACKTEST_VERSION", "Side", "Sizer", "SizedLots", "Rollover", "Trade", "Skip", "Result",
             "BacktestError", "simulate_trade", "run")
    kit = _kit(monkeypatch, "AC-03", *names)
    assert kit.BACKTEST_VERSION == "backtest-v1" and type(kit.BACKTEST_VERSION) is str
    assert issubclass(kit.BacktestError, ValueError)
    assert get_args(kit.Side) == ("long", "short")
    assert get_origin(kit.Sizer) is Callable
    arguments, returned = get_args(kit.Sizer)
    assert list(arguments) == [Decimal, Decimal]
    assert returned is kit.SizedLots or returned in ("SizedLots", ForwardRef("SizedLots"))
    for name, shape in _SHAPES.items():
        cls = getattr(kit, name)
        assert is_dataclass(cls), f"{name} must be a dataclass"
        assert tuple(field.name for field in fields(cls)) == shape, f"{name} fields"
    sized = kit.SizedLots(lots=Decimal("0.01"), risk_money=Decimal("25"), actual_risk=None, reason="sized")
    rollover = _rollover(kit)
    skip = kit.Skip(time_raw=_raw("2026-03-10T14:00"), reasons=("warmup",))
    trade = _simulate(kit, _m1s(kit, _FLAT5))
    m1, m15 = _small(kit)
    result = _run_small(kit, m1, m15)
    for instance in (sized, rollover, skip, trade, result):
        with pytest.raises(FrozenInstanceError):
            setattr(instance, fields(instance)[0].name, None)
    # The small dataset has no entry: one equity point, the first M1 and the start equity.
    assert tuple(result.trades) == () and tuple(result.skips) == ()
    assert result.equity == ((_raw("2026-03-10T14:00"), Decimal("10000")),)
    assert type(result.equity[0][0]) is int and type(result.equity[0][1]) is Decimal
    assert result.backtest_version == kit.BACKTEST_VERSION
    assert result.strategy_version == kit.strategy.STRATEGY_VERSION


def test_ac03_sized_lots_checks_its_fields(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "BacktestError")
    good = {"lots": Decimal("0.02"), "risk_money": Decimal("25"), "actual_risk": Decimal("24"), "reason": "sized"}
    for changes in ({}, {"actual_risk": None}, {"lots": None, "actual_risk": None, "reason": "below_min_volume"},
                    {"lots": Decimal("0"), "actual_risk": None}, {"risk_money": Decimal("0.0001")}):
        values = {**good, **changes}
        sized = kit.SizedLots(**values)
        assert tuple(getattr(sized, name) for name in values) == tuple(values.values())
    bad_values = [
        {"risk_money": Decimal("0")}, {"risk_money": Decimal("-25")},
        {"lots": None, "actual_risk": Decimal("24")}, {"lots": None, "actual_risk": Decimal("0")},
        {"actual_risk": Decimal("0")}, {"actual_risk": Decimal("-1")}, {"reason": ""},
    ]
    for name in ("lots", "risk_money", "actual_risk"):
        bad_values += [{name: Decimal(text)} for text in _NON_FINITE]
    for changes in bad_values:
        with pytest.raises(kit.BacktestError):
            kit.SizedLots(**{**good, **changes})
    bad_types = [
        {"lots": 0.02}, {"lots": 1}, {"lots": True}, {"lots": _Dec("0.02")}, {"lots": "0.02"},
        {"risk_money": 25}, {"risk_money": 25.0}, {"risk_money": None}, {"risk_money": _Dec("25")},
        {"actual_risk": 24.0}, {"actual_risk": 24}, {"actual_risk": _Dec("24")},
        {"reason": None}, {"reason": 1}, {"reason": _Str("sized")}, {"reason": b"sized"},
    ]
    for changes in bad_types:
        with pytest.raises(TypeError):
            kit.SizedLots(**{**good, **changes})


def test_ac03_rollover_checks_zone_and_wall_time(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "Rollover", "BacktestError")
    rollover = kit.Rollover("America/New_York", time(17, 0))
    assert (rollover.zone, rollover.at) == ("America/New_York", time(17, 0))
    kit.Rollover("Asia/Bangkok", time(0, 0))
    for zone in ("Mars/Olympus_Mons", "America/Gotham", ""):
        with pytest.raises(kit.BacktestError):
            kit.Rollover(zone, time(17, 0))
    for at in (time(17, 0, tzinfo=UTC), time(17, 0, 30), time(17, 0, 0, 1)):
        with pytest.raises(kit.BacktestError):
            kit.Rollover("America/New_York", at)
    time_subclass = type("_Time", (time,), {})
    for zone, at in ((None, time(17, 0)), (b"America/New_York", time(17, 0)), (_Str("America/New_York"), time(17, 0)),
                     ("America/New_York", datetime(2026, 3, 10, 17, 0)), ("America/New_York", "17:00"),
                     ("America/New_York", None), ("America/New_York", time_subclass(17, 0))):
        with pytest.raises(TypeError):
            kit.Rollover(zone, at)


def test_ac03_run_refuses_every_input_mismatch(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _small(kit)
    _run_small(kit, m1, m15)  # the valid baseline runs
    offset_rule = kit.tb.TimeRule(server="Synthetic", symbol="XAUUSDm", terminal_build=1, offset_seconds=3600,
                                  evidence_from=date(2026, 1, 1), evidence_to=date(2026, 1, 2),
                                  evidence_ref="synthetic", version="test")
    late = _m1(kit, "2026-03-10T15:00", "4000.00", "4001.00", "3999.00", "4000.00", 240)
    early = _m1(kit, "2026-03-10T13:59", "4000.00", "4001.00", "3999.00", "4000.00", 240)
    bar_30 = kit.snapshot.AggregatedBar(replace(m15[1].bar, timeframe=30), m15[1].flags)
    cases = {
        "m1 empty": ((), m15, {}),
        "m15 empty": (m1, (), {}),
        "an M1 of timeframe 5": (m1[:5] + (replace(m1[5], timeframe=5),) + m1[6:], m15, {}),
        "an M1 time repeated": (m1[:6] + (m1[5],) + m1[6:], m15, {}),
        "two M1 out of order": (m1[:6] + (m1[7], m1[6]) + m1[8:], m15, {}),
        "an M15 bar of timeframe 30": (m1, (m15[0], bar_30) + m15[2:], {}),
        "an M15 time repeated": (m1, m15[:2] + (m15[1],) + m15[2:], {}),
        "two M15 out of order": (m1, (m15[0], m15[2], m15[1], m15[3]), {}),
        "an M1 after the last M15 bar": (m1 + (late,), m15, {}),
        "an M1 before the first M15 bar": ((early,) + m1, m15, {}),
        "an M15 bar without M1": (m1[:30] + m1[45:], m15, {}),
        "the M1 of a missing M15 bar": (m1, m15[:2] + m15[3:], {}),
        "an M1 whose time_utc is not to_utc(time_raw)":
            (m1[:10] + (replace(m1[10], time_utc=m1[10].time_utc + timedelta(minutes=1)),) + m1[11:], m15, {}),
        "a rule under which no time_utc matches": (m1, m15, {"rule": offset_rule}),
        "start equity 0": (m1, m15, {"equity": Decimal("0")}),
        "start equity below 0": (m1, m15, {"equity": Decimal("-0.01")}),
        "sides empty": (m1, m15, {"sides": frozenset()}),
        "sides with an unknown side": (m1, m15, {"sides": frozenset({"buy"})}),
        "sides with long and an unknown side": (m1, m15, {"sides": frozenset({"long", "buy"})}),
    }
    for text in _NON_FINITE:
        cases[f"start equity {text}"] = (m1, m15, {"equity": Decimal(text)})
    missed = []
    for label, (bars_m1, bars_m15, changes) in cases.items():
        try:
            _run_small(kit, bars_m1, bars_m15, **changes)
        except kit.BacktestError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: run must raise BacktestError for:\n" + "\n".join(missed)


def _prices(open_, high, low, close):
    return {"open": Decimal(open_), "high": Decimal(high), "low": Decimal(low), "close": Decimal(close)}


def _stop_level_variants(kit, bar):
    """M1 copies with a STOP-level defect that would make a fill wrong (D13)."""
    prices = _prices
    return {
        "negative spread": replace(bar, spread=-1),
        "high below low": replace(bar, **prices("4000.00", "3999.00", "4001.00", "4000.00")),
        "open above high": replace(bar, **prices("4001.50", "4001.00", "3999.00", "4000.00")),
        "open below low": replace(bar, **prices("3998.50", "4001.00", "3999.00", "4000.00")),
        "close above high": replace(bar, **prices("4000.00", "4001.00", "3999.00", "4001.50")),
        "close below low": replace(bar, **prices("4000.00", "4001.00", "3999.00", "3998.50")),
        "low of zero": replace(bar, **prices("1.00", "2.00", "0", "1.00")),
        "open of zero": replace(bar, **prices("0", "1.00", "0", "1.00")),
        "negative prices": replace(bar, **prices("-1.00", "-0.50", "-2.00", "-1.00")),
    }


def test_ac03_run_refuses_stop_level_m1(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _small(kit)
    missed = []
    for position in (0, 20, len(m1) - 1):
        for label, bad in _stop_level_variants(kit, m1[position]).items():
            try:
                _run_small(kit, m1[:position] + (bad,) + m1[position + 1:], m15)
            except kit.BacktestError:
                continue
            except Exception as error:  # reported below: the wrong exception
                missed.append(f"M1 {position} {label}: {type(error).__name__}: {error}")
                continue
            missed.append(f"M1 {position} {label}: no error")
    assert not missed, "AC-03: run must raise BacktestError for STOP-level M1:\n" + "\n".join(missed)


def test_ac03_run_refuses_wrong_types(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _small(kit)
    sub_bar = type("_SubBar", (kit.Bar,), {})
    sub_rollover = type("_SubRollover", (kit.Rollover,), {})
    bar_values = {field.name: getattr(m1[3], field.name) for field in fields(kit.Bar)}
    m15_bar_values = {field.name: getattr(m15[1].bar, field.name) for field in fields(kit.Bar)}
    duck = _DuckM15
    cases = {
        "m1 as a generator": lambda: _run_small(kit, (bar for bar in m1), m15),
        "m15 as a generator": lambda: _run_small(kit, m1, (item for item in m15)),
        "an AggregatedBar among the M1": lambda: _run_small(kit, m1[:3] + (m15[0],) + m1[4:], m15),
        "a Bar subclass among the M1": lambda: _run_small(kit, m1[:3] + (sub_bar(**bar_values),) + m1[4:], m15),
        "a plain Bar among the M15": lambda: _run_small(kit, m1, (m15[0], m15[1].bar) + m15[2:]),
        "an M15 .bar of a Bar subclass": lambda: _run_small(
            kit, m1, (m15[0], duck(sub_bar(**m15_bar_values), frozenset())) + m15[2:]),
        "an M15 .flags as a set": lambda: _run_small(kit, m1, (m15[0], duck(m15[1].bar, set())) + m15[2:]),
        "an M15 flag that is not str": lambda: _run_small(
            kit, m1, (m15[0], duck(m15[1].bar, frozenset({1}))) + m15[2:]),
        "params as a dict": lambda: _run_small(kit, m1, m15, params=dict(kit.golden["RUN_PARAMS"])),
        "params None": lambda: _run_small(kit, m1, m15, params=None),
        "model None": lambda: _run_small(kit, m1, m15, model=None),
        "model as a name": lambda: _run_small(kit, m1, m15, model="H001_COSTS"),
        "rule None": lambda: _run_small(kit, m1, m15, rule=None),
        "rule as a server name": lambda: _run_small(kit, m1, m15, rule="Exness-MT5Trial14"),
        "rollover None": lambda: _run_small(kit, m1, m15, rollover=None),
        "rollover as a tuple": lambda: _run_small(kit, m1, m15, rollover=("America/New_York", time(17, 0))),
        "rollover subclass": lambda: _run_small(kit, m1, m15,
                                                rollover=sub_rollover("America/New_York", time(17, 0))),
        "sides as a set": lambda: _run_small(kit, m1, m15, sides={"long", "short"}),
        "sides as a tuple": lambda: _run_small(kit, m1, m15, sides=("long", "short")),
        "sides None": lambda: _run_small(kit, m1, m15, sides=None),
    }
    for label, equity in (("float", 10000.0), ("int", 10000), ("bool", True), ("Decimal subclass", _Dec("10000")),
                          ("str", "10000"), ("None", None)):
        cases[f"equity as {label}"] = lambda equity=equity: _run_small(kit, m1, m15, equity=equity)
    missed = []
    for label, call in cases.items():
        try:
            call()
        except TypeError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: run must raise TypeError for:\n" + "\n".join(missed)


def test_ac03_simulate_trade_refuses_bad_indexes_and_values_before_any_fill(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "Rollover", "Trade", "BacktestError", "simulate_trade")
    m1 = _m1s(kit, _FLAT5)
    for exit_index in (4, None):  # the valid baselines: a signal exit and an end of data
        assert type(_simulate(kit, m1, exit_index=exit_index)) is kit.Trade
    cases = {
        "no M1": lambda: _simulate(kit, (), exit_index=None),
        "entry_index -1": lambda: _simulate(kit, m1, entry_index=-1),
        "entry_index = len(m1)": lambda: _simulate(kit, m1, entry_index=5, exit_index=None),
        "exit_index = entry_index": lambda: _simulate(kit, m1, entry_index=2, exit_index=2),
        "exit_index below entry_index": lambda: _simulate(kit, m1, entry_index=2, exit_index=1),
        "exit_index = len(m1)": lambda: _simulate(kit, m1, exit_index=5),
        "exit_index -1": lambda: _simulate(kit, m1, exit_index=-1),
        "side buy": lambda: _simulate(kit, m1, side="buy"),
        "side LONG": lambda: _simulate(kit, m1, side="LONG"),
        "side empty": lambda: _simulate(kit, m1, side=""),
        "stop_distance 0": lambda: _simulate(kit, m1, stop_distance=Decimal("0")),
        "stop_distance below 0": lambda: _simulate(kit, m1, stop_distance=Decimal("-0.01")),
        "risk_money 0": lambda: _simulate(kit, m1, risk_money=Decimal("0")),
        "risk_money below 0": lambda: _simulate(kit, m1, risk_money=Decimal("-25")),
        "actual_risk 0": lambda: _simulate(kit, m1, actual_risk=Decimal("0")),
        "actual_risk below 0": lambda: _simulate(kit, m1, actual_risk=Decimal("-1")),
    }
    for name in ("stop_distance", "lots", "risk_money", "actual_risk"):
        for text in _NON_FINITE:
            cases[f"{name} {text}"] = lambda name=name, text=text: _simulate(kit, m1, **{name: Decimal(text)})
    missed = []
    for label, call in cases.items():
        try:
            call()
        except kit.BacktestError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: simulate_trade must raise BacktestError for:\n" + "\n".join(missed)


def test_ac03_simulate_trade_refuses_stop_level_m1_it_reads(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "Rollover", "Trade", "BacktestError", "simulate_trade")
    m1 = _m1s(kit, _FLAT5)
    missed = []
    for side in ("long", "short"):
        # (position of the defect, exit_index): the entry M1, an M1 before the exit, the exit M1,
        # and the last M1 of an end of data. The stops (50.00 away) are never reached.
        for position, exit_index in ((0, 4), (2, 4), (4, 4), (4, None)):
            variants = dict(_stop_level_variants(kit, m1[position]))
            variants["timeframe 5"] = replace(m1[position], timeframe=5)
            if position:
                previous = m1[position - 1]
                variants["time equal to the previous M1"] = replace(
                    m1[position], time_raw=previous.time_raw, time_utc=previous.time_utc)
                variants["time before the previous M1"] = replace(
                    m1[position], time_raw=previous.time_raw - 60, time_utc=previous.time_utc - timedelta(minutes=1))
            for label, bad in variants.items():
                bars = m1[:position] + (bad,) + m1[position + 1:]
                try:
                    _simulate(kit, bars, side=side, exit_index=exit_index)
                except kit.BacktestError:
                    continue
                except Exception as error:  # reported below: the wrong exception
                    missed.append(f"{side} M1 {position} (exit_index {exit_index}) {label}: "
                                  f"{type(error).__name__}: {error}")
                    continue
                missed.append(f"{side} M1 {position} (exit_index {exit_index}) {label}: no error")
    assert not missed, "AC-03: simulate_trade must raise BacktestError for:\n" + "\n".join(missed)


def test_ac03_simulate_trade_refuses_wrong_types_and_lots_off_the_grid(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "Rollover", "Trade", "BacktestError", "simulate_trade")
    m1 = _m1s(kit, _FLAT5)
    sub_bar = type("_SubBar", (kit.Bar,), {})
    sub_rollover = type("_SubRollover", (kit.Rollover,), {})
    bar_values = {field.name: getattr(m1[0], field.name) for field in fields(kit.Bar)}
    model = kit.costs.H001_COSTS
    cases = {
        "m1 as a generator": lambda: _simulate(kit, (bar for bar in m1)),
        "an AggregatedBar as the entry M1": lambda: _simulate(
            kit, (kit.snapshot.AggregatedBar(m1[0], frozenset()),) + m1[1:]),
        "a Bar subclass as the entry M1": lambda: _simulate(kit, (sub_bar(**bar_values),) + m1[1:]),
        "entry_index True": lambda: _simulate(kit, m1, entry_index=True),
        "entry_index 0.0": lambda: _simulate(kit, m1, entry_index=0.0),
        "entry_index None": lambda: _simulate(kit, m1, entry_index=None),
        "exit_index True": lambda: _simulate(kit, m1, exit_index=True),
        "exit_index 4.0": lambda: _simulate(kit, m1, exit_index=4.0),
        "side None": lambda: _simulate(kit, m1, side=None),
        "side 1": lambda: _simulate(kit, m1, side=1),
        "side str subclass": lambda: _simulate(kit, m1, side=_Str("long")),
        "model None": lambda: _simulate(kit, m1, model=None),
        "model as a name": lambda: _simulate(kit, m1, model="H001_COSTS"),
        "rollover None": lambda: _simulate(kit, m1, rollover=None),
        "rollover as a tuple": lambda: _simulate(kit, m1, rollover=("America/New_York", time(17, 0))),
        "rollover subclass": lambda: _simulate(kit, m1, rollover=sub_rollover("America/New_York", time(17, 0))),
        "data_flags as a set": lambda: _simulate(kit, m1, data_flags={"incomplete"}),
        "data_flags as a tuple": lambda: _simulate(kit, m1, data_flags=("incomplete",)),
        "data_flags None": lambda: _simulate(kit, m1, data_flags=None),
        "risk_money missing": lambda: kit.simulate_trade(m1, 0, "long", Decimal("50.00"), Decimal("0.10"), model,
                                                         _rollover(kit), exit_index=4),
        "risk_money by position": lambda: kit.simulate_trade(m1, 0, "long", Decimal("50.00"), Decimal("0.10"),
                                                             model, _rollover(kit), Decimal("25")),
    }
    for name, values in (("stop_distance", (50.0, 50, True, _Dec("50.00"), "50.00", None)),
                         ("lots", (0.1, 1, _Dec("0.10"), "0.10", None)),
                         ("risk_money", (25.0, 25, _Dec("25"), "25", None)),
                         ("actual_risk", (24.0, 24, _Dec("24"), "24"))):
        for value in values:
            label = f"{name} as {type(value).__name__} {value!r}"
            cases[label] = lambda name=name, value=value: _simulate(kit, m1, **{name: value})
    missed = []
    for label, call in cases.items():
        try:
            call()
        except TypeError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: simulate_trade must raise TypeError for:\n" + "\n".join(missed)
    # Lots refused by the cost model are costs.BadVolume, not wrapped.
    for lots in ("0.015", "0.001", "200.01"):
        with pytest.raises(kit.costs.BadVolume) as caught:
            _simulate(kit, m1, lots=Decimal(lots))
        assert caught.type is kit.costs.BadVolume, f"lots {lots}"


def _size_data(kit):
    scenario = kit.golden["SCENARIOS"]["R"]
    return _scenario_data(kit, {**scenario, "bars": kit.golden["SIZE_BARS"], "flags": {}})


def _size_run(kit, m1, m15, sizer, equity="10000"):
    return kit.run(m1, m15, _params(kit), kit.costs.H001_COSTS, sizer, Decimal(equity), kit.rule, _rollover(kit))


def test_ac03_sizer_sizes_reach_the_trade(monkeypatch):
    """Bars 0..101 of R: one entry; the sizer's lots, risk_money and actual_risk reach the Trade."""
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    m1, m15 = _size_data(kit)
    wrong = []
    for lots, risk, actual, gross, spread, slippage, total, net, r in kit.golden["SIZE_CASES"]:
        sizer = _Sizer(kit, ((lots, risk, actual, "sized"),))
        result = _size_run(kit, m1, m15, sizer)
        expected = {"side": "long", "entry": ("2026-03-10T12:15", "4002.00", 240),
                    "exit": ("2026-03-10T12:29", "4002.40", 240), "lots": lots, "stop_distance": "6.30",
                    "stop_price": "3995.94", "exit_reason": "end_of_data", "ambiguous": False, "nights": (0, 0),
                    "costs": (spread, "0", slippage, "0", total), "gross": gross, "net": net, "risk_money": risk,
                    "actual_risk": actual, "r": r, "data_flags": ()}
        scenario = {"trades": (expected,), "skips": (),
                    "equity": (("2026-03-09T11:00", "10000"),
                               ("2026-03-10T12:29", str(Decimal("10000") + Decimal(net)))),
                    "calls": (("10000", "6.30"),)}
        wrong += _check_result(kit, result, scenario, sizer, f"lots {lots}")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


def test_ac03_sizer_without_lots_is_a_skip_with_its_reason(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    m1, m15 = _size_data(kit)
    wrong = []
    for reason in ("below_min_volume", "sizer said no"):
        sizer = _Sizer(kit, ((None, "25", None, reason),))
        result = _size_run(kit, m1, m15, sizer)
        scenario = {"trades": (), "skips": (("2026-03-10T12:00", (reason,)),),
                    "equity": (("2026-03-09T11:00", "10000"),), "calls": (("10000", "6.30"),)}
        wrong += _check_result(kit, result, scenario, sizer, f"lots None, reason {reason!r}")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


def test_ac03_sizer_lots_refused_by_costs_raise_bad_volume_unwrapped(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _size_data(kit)
    for lots in ("0.015", "0", "0.001", "200.01", "-0.01"):
        with pytest.raises(kit.costs.BadVolume) as caught:
            _size_run(kit, m1, m15, _Sizer(kit, ((lots, "25", None, "sized"),)))
        assert caught.type is kit.costs.BadVolume, f"lots {lots}: {caught.type.__name__}"


def test_ac03_sizer_errors_reach_the_caller_unchanged(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _size_data(kit)
    raised = []

    def building(**values):
        def sizer(equity, stop_distance):
            try:
                return kit.SizedLots(**{"lots": Decimal("0.01"), "risk_money": Decimal("25"), "actual_risk": None,
                                        "reason": "sized", **values})
            except Exception as error:
                raised.append(error)
                raise
        return sizer

    def failing(equity, stop_distance):
        error = _SizerFailure("the sizer failed")
        raised.append(error)
        raise error

    for sizer, kind in ((building(risk_money=Decimal("0")), kit.BacktestError),
                        (building(risk_money=Decimal("-1")), kit.BacktestError),
                        (building(reason=""), kit.BacktestError),
                        (building(lots=Decimal("NaN")), kit.BacktestError),
                        (building(lots=0.01), TypeError),
                        (failing, _SizerFailure)):
        raised.clear()
        with pytest.raises(kind) as caught:
            _size_run(kit, m1, m15, sizer)
        assert raised and caught.value is raised[0], "the sizer's exception must not be wrapped or replaced"


def test_ac03_sizer_result_of_the_wrong_type_is_a_type_error(monkeypatch):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _size_data(kit)
    sub_sized = type("_SubSizedLots", (kit.SizedLots,), {})
    results = {
        "None": lambda: None,
        "a tuple": lambda: (Decimal("0.01"), Decimal("25"), None, "sized"),
        "a Decimal": lambda: Decimal("0.01"),
        "a SizedLots subclass": lambda: sub_sized(lots=Decimal("0.01"), risk_money=Decimal("25"), actual_risk=None,
                                                  reason="sized"),
    }
    for label, make in results.items():
        with pytest.raises(TypeError):
            _size_run(kit, m1, m15, lambda equity, stop_distance, make=make: make())
    with pytest.raises(TypeError):
        _size_run(kit, m1, m15, None)  # a sizer that cannot be called


@pytest.mark.parametrize("name", ["R_exhausted", "R_negative"])
def test_ac03_exhausted_equity_skips_every_later_entry_without_sizing(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS"][name]
    result, sizer, _, _ = _run_scenario(kit, name)
    wrong = _check_result(kit, result, scenario, sizer, scenario["label"])
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


@pytest.mark.parametrize("name", ["R", "R_long_only", "R_flags_105"])
def test_ac03_sizer_sees_equity_after_each_trade_and_positions_never_overlap(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS"][name]
    result, sizer, _, _ = _run_scenario(kit, name)
    trades = tuple(result.trades)
    assert len(trades) >= 3, "fixture: the scenario must have several trades"
    for before, after in zip(trades, trades[1:]):
        assert before.exit_time_raw < after.entry_time_raw, "AC-03: positions overlap"
    # Equity points: the first M1 with the start equity, then one point per close in order.
    start = Decimal(scenario["start_equity"])
    assert result.equity[0] == (_raw(kit.golden["RUN_START"]), start)
    running = start
    for point, trade in zip(result.equity[1:], trades):
        running += trade.net_money
        assert point == (trade.exit_time_raw, running), "AC-03: equity point after a close"
    assert len(result.equity) == len(trades) + 1
    # The sizer is called with the equity after every trade that closed before the entry.
    for equity, _ in sizer.calls:
        assert equity in [point[1] for point in result.equity], f"AC-03: sizer saw equity {equity}"
    wrong = _check_result(kit, result, scenario, sizer, scenario["label"])
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-04

def _nights_trade(kit, case, model=None):
    label, entry, exit_, side, *_ = case
    golden = kit.golden
    m1 = _m1s(kit, ((entry, *golden["NIGHTS_ENTRY"]), (exit_, *golden["NIGHTS_EXIT"])))
    return kit.simulate_trade(m1, 0, side, Decimal("50.00"), Decimal("0.10"),
                              kit.costs.H001_COSTS if model is None else model, _rollover(kit),
                              risk_money=Decimal("25"), exit_index=1)


@pytest.mark.parametrize("label", [case[0] for case in _golden()["NIGHTS_CASES"]])
def test_ac04_nights_and_triple_nights_of_a_holding_period(monkeypatch, label):
    kit = _kit(monkeypatch, "AC-04", "Rollover", "Trade", "simulate_trade")
    case = next(case for case in kit.golden["NIGHTS_CASES"] if case[0] == label)
    _, entry, exit_, side, nights, triple, swap, total, net, r = case
    trade = _nights_trade(kit, case)
    expected = {"side": side, "entry": (entry, "4000.00", 200), "exit": (exit_, "4001.00", 200), "lots": "0.10",
                "stop_distance": "50.00", "stop_price": "3950.20" if side == "long" else "4050.00",
                "exit_reason": "signal", "ambiguous": False, "nights": (nights, triple),
                "costs": ("2.00", "0", "1.00", swap, total), "gross": "10.00" if side == "long" else "-10.00",
                "net": net, "risk_money": "25", "actual_risk": None, "r": r, "data_flags": ()}
    wrong = _check_trade(kit, trade, expected, kit.costs.H001_COSTS, label)
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_double_costs_keep_prices_and_gross_and_double_every_charge(monkeypatch):
    kit = _kit(monkeypatch, "AC-04", "Rollover", "Trade", "simulate_trade")
    golden = kit.golden
    base_model = kit.costs.H001_COSTS
    other_model = replace(base_model, commission_per_lot_per_side=Decimal("3.5"),
                          swap_short_points_per_night=Decimal("-120.5"))
    by_label = {case["label"]: case for case in golden["FILL_CASES"]}
    fills = ("long gap at a later M1 (low < open < stop)", "short gap at a later M1 (stop < open < high)",
             "long exit open beyond the stop is stop + ambiguous at the open",
             "short spread None at the M1 of the stop widens the ask", "long spread None at an entry M1 that stops")
    nights = [case for case in golden["NIGHTS_CASES"] if case[0] in ("Monday to next Monday",
                                                                     "short Monday to next Monday")]
    unchanged = ("side", "entry_time_raw", "entry_bid", "entry_spread_points", "exit_time_raw", "exit_bid",
                 "exit_spread_points", "lots", "stop_distance", "stop_price", "exit_reason", "ambiguous", "nights",
                 "triple_nights", "gross_money", "risk_money", "actual_risk", "data_flags")
    wrong = []
    for model in (base_model, other_model):
        doubled = kit.costs.stress(model, 2)
        makers = [(f"AC-01 {side}", lambda model, rows=rows, side=side: kit.simulate_trade(
                      _m1s(kit, rows), 0, side, Decimal("12.00"), Decimal("0.02"), model, _rollover(kit),
                      risk_money=Decimal("25"), exit_index=2))
                  for side, rows in (("long", golden["AC01_LONG_M1"]), ("short", golden["AC01_SHORT_M1"]))]
        makers += [(label, lambda model, case=by_label[label]: _fill_case(kit, case, model)) for label in fills]
        makers += [(case[0], lambda model, case=case: _nights_trade(kit, case, model)) for case in nights]
        for label, make in makers:
            label = f"{label} ({'commission and short swap' if model is other_model else 'H001_COSTS'})"
            once, twice = make(model), make(doubled)
            for name in unchanged:
                if getattr(once, name) != getattr(twice, name):
                    wrong.append(f"{label}: {name} {getattr(once, name)!r} became {getattr(twice, name)!r}")
            for part in ("spread", "commission", "slippage", "swap", "total"):
                single, double = getattr(once.costs, part), getattr(twice.costs, part)
                if double != 2 * single:
                    wrong.append(f"{label}: costs.{part} {single} at 1x but {double} at 2x")
            if (once.costs.stress_factor, twice.costs.stress_factor) != (model.stress_factor, 2 * model.stress_factor):
                wrong.append(f"{label}: stress factors {once.costs.stress_factor}, {twice.costs.stress_factor}")
            with localcontext(kit.costs.CONTEXT):
                net, r = twice.gross_money - twice.costs.total, (twice.gross_money - twice.costs.total) / twice.risk_money
            if twice.net_money != net:
                wrong.append(f"{label}: 2x net {twice.net_money} is not gross - total = {net}")
            if twice.r != r:
                wrong.append(f"{label}: 2x r {twice.r} is not net / risk_money = {r}")
            if model is other_model and (once.costs.commission == 0 or (once.side == "short" and once.nights
                                                                         and once.costs.swap == 0)):
                wrong.append(f"fixture: {label} must have commission and short swap")
    # The AC-01 long at 2x, by hand (H001_COSTS).
    long_twice = kit.simulate_trade(_m1s(kit, golden["AC01_LONG_M1"]), 0, "long", Decimal("12.00"), Decimal("0.02"),
                                    kit.costs.stress(base_model, 2), _rollover(kit), risk_money=Decimal("25"),
                                    exit_index=2)
    expected = {**golden["AC01_LONG"], **golden["AC01_LONG_STRESS2"]}
    wrong += _check_trade(kit, long_twice, expected, kit.costs.stress(base_model, 2), "AC-01 long at 2x")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- AC-05

@pytest.mark.parametrize("name", ["R", "R_long_only", "R_flags_105"])
def test_ac05_cutting_after_a_close_keeps_every_earlier_trade_skip_and_equity_point(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-05", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    result, _, m1, m15 = _run_scenario(kit, name)
    trades = tuple(result.trades)
    assert len(trades) >= 3, "fixture: the scenario must have several trades"
    opens = [item.bar.time_raw for item in m15]
    wrong = []
    for k, trade in enumerate(trades, start=1):
        u_open = kit.tb.bar_open(trade.exit_time_raw, 15, kit.rule)
        u = opens.index(u_open)
        cut_m15 = m15[:u + 1]
        cut_m1 = tuple(bar for bar in m1 if kit.tb.bar_open(bar.time_raw, 15, kit.rule) <= u_open)
        cut, _, _, _ = _run_scenario(kit, name, m1=cut_m1, m15=cut_m15)
        if tuple(cut.trades) != trades[:k]:
            wrong.append(f"trade {k} (u = bar {u}): trades {tuple(cut.trades)!r} != {trades[:k]!r}")
        before_u = tuple(skip for skip in result.skips if skip.time_raw < u_open)
        if tuple(cut.skips) != before_u:
            wrong.append(f"trade {k} (u = bar {u}): skips {tuple(cut.skips)!r} != {before_u!r}")
        if tuple(cut.equity) != tuple(result.equity[:k + 1]):
            wrong.append(f"trade {k} (u = bar {u}): equity {cut.equity!r} != {result.equity[:k + 1]!r}")
    assert not wrong, f"AC-05 {name}: look-ahead after the cut:\n" + "\n".join(wrong)


@pytest.mark.parametrize("name", ["R", "R_long_only", "R_to_103", "R_flags_ends", "R_flags_105", "R_exhausted",
                                  "R_gap", "R_window"])
def test_ac05_every_run_trade_equals_simulate_trade_of_its_entry_and_exit(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-05", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run", "simulate_trade")
    result, _, m1, m15 = _run_scenario(kit, name)
    index = {bar.time_raw: position for position, bar in enumerate(m1)}
    opens = [item.bar.time_raw for item in m15]

    def bar_of(raw):
        """Position in m15 of the M15 bar that holds raw time `raw`."""
        return opens.index(kit.tb.bar_open(raw, 15, kit.rule))

    trades = tuple(result.trades)
    assert trades, "fixture: the scenario must have trades"
    wrong = []
    for k, trade in enumerate(trades, start=1):
        entry_index = index[trade.entry_time_raw]
        entry_bar = bar_of(trade.entry_time_raw)
        if entry_index and bar_of(m1[entry_index - 1].time_raw) == entry_bar:
            wrong.append(f"trade {k}: the entry is not the first M1 of its M15 bar")
        decided_by_strategy = trade.exit_reason == "signal" or trade.ambiguous
        exit_index = index[trade.exit_time_raw] if decided_by_strategy else None
        if decided_by_strategy and bar_of(m1[exit_index - 1].time_raw) == bar_of(trade.exit_time_raw):
            wrong.append(f"trade {k}: a strategy exit is not at the first M1 of its M15 bar")
        flags = frozenset().union(*(m15[t].flags for t in range(entry_bar - 1, bar_of(trade.exit_time_raw) + 1)))
        if trade.data_flags != flags:
            wrong.append(f"trade {k}: data_flags {trade.data_flags!r}, expected {flags!r}")
        again = kit.simulate_trade(m1, entry_index, trade.side, trade.stop_distance, trade.lots,
                                   kit.costs.H001_COSTS, _rollover(kit), risk_money=trade.risk_money,
                                   actual_risk=trade.actual_risk, exit_index=exit_index, data_flags=flags)
        if again != trade:
            wrong.append(f"trade {k}: run gave {trade!r}\n  simulate_trade gave {again!r}")
    assert not wrong, f"AC-05 {name}:\n" + "\n".join(wrong)


# ----------------------------------------------------------------------------------- round 2
# Tests r2: docs/reviews/CORE-007-tests-r1.md F1, F2, F4, F5, F7 and contract v1.5 items 4-6 (the
# AC-06 part of the v1.5 time item is in tests/architecture/test_imports.py). Every round-1 test,
# table and helper above is unchanged; the hand-computed values are in the round-2 section of the
# golden file.

def _r2_scenario_data(kit, scenario):
    """M1 of a round-2 run scenario without the rows it drops, and M15 from aggregate as in R1.

    Unlike _m15, an M15 bar may be incomplete here; the fixture checks which bars are."""
    rows = kit.golden["run_m1_rows"](start=scenario["start"], bars=scenario["bars"],
                                     gap_after=scenario["gap_after"])
    dropped = frozenset(scenario["drop"])
    kept = tuple(row for row in rows if row[0] not in dropped)
    assert len(rows) - len(kept) == len(dropped), "fixture: every dropped M1 is in the scenario"
    m1 = _m1s(kit, kept)
    snapshot = kit.snapshot
    report = snapshot.ValidationReport(defects=(), days=MappingProxyType({}), m1_bars=len(m1),
                                       calendar=snapshot.H001_CLOSURES)
    m15 = snapshot.aggregate(m1, 15, kit.rule, report)
    assert len(m15) == scenario["bars"], "fixture: every M15 bar keeps at least one M1"
    incomplete = tuple(t for t, item in enumerate(m15) if item.flags)
    assert incomplete == tuple(scenario["incomplete"]), f"fixture: incomplete bars {incomplete}"
    assert all(item.flags <= {"incomplete"} for item in m15), "fixture: no flag but incomplete"
    opens = {item.bar.time_raw for item in m15}
    present = {bar.time_raw for bar in m1}
    for stamp in scenario["drop"]:
        assert _raw(stamp) in opens and _raw(stamp) not in present, f"fixture: {stamp} opens a bar without its M1"
    return m1, m15


def _r2_run(kit, scenario, m1, m15):
    sizer = _Sizer(kit, scenario["responses"])
    result = kit.run(m1, m15, _params(kit), kit.costs.H001_COSTS, sizer, Decimal(scenario["start_equity"]),
                     kit.rule, _rollover(kit), sides=frozenset(scenario["sides"]))
    return result, sizer


def _r2_mapping_wrong(kit, trades, m1, m15):
    """The AC-05 run -> simulate_trade mapping of the round-1 test (convention 7) for one run."""
    index = {bar.time_raw: position for position, bar in enumerate(m1)}
    opens = [item.bar.time_raw for item in m15]

    def bar_of(raw):
        return opens.index(kit.tb.bar_open(raw, 15, kit.rule))

    wrong = []
    for k, trade in enumerate(trades, start=1):
        if trade.entry_time_raw not in index or trade.exit_time_raw not in index:
            wrong.append(f"trade {k}: entry or exit time is not the time of an M1: {trade!r}")
            continue
        entry_index = index[trade.entry_time_raw]
        entry_bar = bar_of(trade.entry_time_raw)
        if entry_index and bar_of(m1[entry_index - 1].time_raw) == entry_bar:
            wrong.append(f"trade {k}: the entry is not the first M1 of its M15 bar")
        decided_by_strategy = trade.exit_reason == "signal" or trade.ambiguous
        exit_index = index[trade.exit_time_raw] if decided_by_strategy else None
        if decided_by_strategy and bar_of(m1[exit_index - 1].time_raw) == bar_of(trade.exit_time_raw):
            wrong.append(f"trade {k}: a strategy exit is not at the first M1 of its M15 bar")
        flags = frozenset().union(*(m15[t].flags for t in range(entry_bar - 1, bar_of(trade.exit_time_raw) + 1)))
        if trade.data_flags != flags:
            wrong.append(f"trade {k}: data_flags {trade.data_flags!r}, expected {flags!r}")
        again = kit.simulate_trade(m1, entry_index, trade.side, trade.stop_distance, trade.lots,
                                   kit.costs.H001_COSTS, _rollover(kit), risk_money=trade.risk_money,
                                   actual_risk=trade.actual_risk, exit_index=exit_index, data_flags=flags)
        if again != trade:
            wrong.append(f"trade {k}: run gave {trade!r}\n  simulate_trade gave {again!r}")
    return wrong


@pytest.mark.parametrize("label", [case[0] for case in _golden()["ROLLOVER_CASES"]])
def test_ac04_r2_nights_follow_the_rollover_zone_and_time_and_the_model_triple_weekday(monkeypatch, label):
    """Review F1, D4 [A]: T is rollover.at in rollover.zone on Monday-Friday of that zone, and a
    night is triple when that zone's weekday is model.triple_swap_weekday."""
    kit = _kit(monkeypatch, "AC-04", "Rollover", "Trade", "simulate_trade")
    golden = kit.golden
    case = next(case for case in golden["ROLLOVER_CASES"] if case[0] == label)
    _, zone, hour, minute, weekday, entry, exit_, nights, triple, swap, total, net, r = case
    model = replace(kit.costs.H001_COSTS, triple_swap_weekday=weekday)
    m1 = _m1s(kit, ((entry, *golden["NIGHTS_ENTRY"]), (exit_, *golden["NIGHTS_EXIT"])))
    rollover = kit.Rollover(zone, time(hour, minute))
    trade = kit.simulate_trade(m1, 0, "long", Decimal("50.00"), Decimal("0.10"), model, rollover,
                               risk_money=Decimal("25"), exit_index=1)
    expected = {"side": "long", "entry": (entry, "4000.00", 200), "exit": (exit_, "4001.00", 200), "lots": "0.10",
                "stop_distance": "50.00", "stop_price": "3950.20", "exit_reason": "signal", "ambiguous": False,
                "nights": (nights, triple), "costs": ("2.00", "0", "1.00", swap, total), "gross": "10.00",
                "net": net, "risk_money": "25", "actual_risk": None, "r": r, "data_flags": ()}
    wrong = _check_trade(kit, trade, expected, model, label)
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


def test_ac04_r2_nights_compare_time_utc_not_time_raw(monkeypatch):
    """Review F5: under a rule with offset 3600 the raw time is not UTC; nights use time_utc."""
    kit = _kit(monkeypatch, "AC-04", "Rollover", "Trade", "simulate_trade")
    golden = kit.golden
    label, shift, entry, exit_, anchors, nights, triple, swap, total, net, r = golden["RAW_SHIFT_CASE"]
    rows = ((entry, *golden["NIGHTS_ENTRY"]), (exit_, *golden["NIGHTS_EXIT"]))
    m1 = tuple(replace(bar, time_raw=bar.time_raw + shift) for bar in _m1s(kit, rows))
    assert tuple(bar.time_raw for bar in m1) == anchors, "fixture: raw = UTC seconds + 3600"
    assert tuple(bar.time_utc for bar in m1) == (_utc(entry), _utc(exit_)), "fixture: time_utc is UTC"
    model = kit.costs.H001_COSTS
    trade = kit.simulate_trade(m1, 0, "long", Decimal("50.00"), Decimal("0.10"), model, _rollover(kit),
                               risk_money=Decimal("25"), exit_index=1)
    # _check_trade turns a stamp into raw seconds at offset 0, so the times it gets are the raw
    # clock (UTC + 1 hour); the anchors above pin the same numbers.
    entry_raw, exit_raw = ((datetime.fromisoformat(stamp) + timedelta(seconds=shift)).isoformat(timespec="minutes")
                           for stamp in (entry, exit_))
    expected = {"side": "long", "entry": (entry_raw, "4000.00", 200), "exit": (exit_raw, "4001.00", 200),
                "lots": "0.10", "stop_distance": "50.00", "stop_price": "3950.20", "exit_reason": "signal",
                "ambiguous": False, "nights": (nights, triple), "costs": ("2.00", "0", "1.00", swap, total),
                "gross": "10.00", "net": net, "risk_money": "25", "actual_risk": None, "r": r, "data_flags": ()}
    wrong = _check_trade(kit, trade, expected, model, label)
    if type(trade) is kit.Trade and (trade.entry_time_raw, trade.exit_time_raw) != anchors:
        wrong.append(f"{label}: times {(trade.entry_time_raw, trade.exit_time_raw)}, expected {anchors}")
    assert not wrong, "AC-04:\n" + "\n".join(wrong)


@pytest.mark.parametrize("label", [case["label"] for case in _golden()["FILL_CASES_R2"]])
def test_ac02_r2_fill_case_spread_none_at_an_ambiguous_exit_or_a_short_entry_stop(monkeypatch, label):
    """Review F4: s is the spread of the M1 the event happens on, the fallback when it has none."""
    kit = _kit(monkeypatch, "AC-02", "Rollover", "Trade", "simulate_trade")
    case = next(case for case in kit.golden["FILL_CASES_R2"] if case["label"] == label)
    trade = _fill_case(kit, case)
    wrong = _check_trade(kit, trade, case["expected"], kit.costs.H001_COSTS, label)
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


@pytest.mark.parametrize("name", ["R_first_minutes_missing", "R_exit_minute_missing"])
def test_ac02_r2_run_fills_at_the_first_m1_present_in_the_next_bar(monkeypatch, name):
    """Review F2: "the open of the first M1 of the next M15 bar" and the first equity point "(time_raw
    of the first M1, ...)" are M1 times, which differ from the M15 slot time when minute 0 is missing."""
    kit = _kit(monkeypatch, "AC-02", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS_R2"][name]
    m1, m15 = _r2_scenario_data(kit, scenario)
    result, sizer = _r2_run(kit, scenario, m1, m15)
    wrong = _check_result(kit, result, scenario, sizer, scenario["label"])
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac03_r2_long_only_with_exhausted_equity_records_no_skip_for_a_short_entry(monkeypatch):
    """Review F7 (1), step 4: an enter_* whose side is not in sides is "none" (no Skip), also when
    the equity is exhausted; the equity check applies to the sides that may trade."""
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    scenario = kit.golden["SCENARIOS_R2"]["R_exhausted_long_only"]
    m1, m15 = _r2_scenario_data(kit, scenario)
    result, sizer = _r2_run(kit, scenario, m1, m15)
    wrong = _check_result(kit, result, scenario, sizer, scenario["label"])
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


@pytest.mark.parametrize("name", ["R_first_minutes_missing", "R_exit_minute_missing", "R_exhausted_long_only"])
def test_ac05_r2_every_run_trade_equals_simulate_trade_of_its_entry_and_exit(monkeypatch, name):
    kit = _kit(monkeypatch, "AC-05", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run", "simulate_trade")
    scenario = kit.golden["SCENARIOS_R2"][name]
    m1, m15 = _r2_scenario_data(kit, scenario)
    result, _ = _r2_run(kit, scenario, m1, m15)
    trades = tuple(result.trades)
    assert trades, "fixture: the scenario must have trades"
    wrong = _r2_mapping_wrong(kit, trades, m1, m15)
    assert not wrong, f"AC-05 {name}:\n" + "\n".join(wrong)


def test_ac03_r2_simulate_trade_refuses_data_flags_that_are_not_a_frozenset_of_str(monkeypatch):
    """Review F7 (2): data_flags is frozenset[str]; a wrong element type is TypeError (convention 3)."""
    kit = _kit(monkeypatch, "AC-03", "Rollover", "Trade", "BacktestError", "simulate_trade")
    m1 = _m1s(kit, _FLAT5)
    trade = _simulate(kit, m1, data_flags=frozenset({"incomplete"}))  # the valid baseline
    assert type(trade) is kit.Trade and trade.data_flags == frozenset({"incomplete"})
    frozenset_subclass = type("_Flags", (frozenset,), {})
    cases = {
        "a data flag that is not str": frozenset({1}),
        "a data flag of a str subclass": frozenset({_Str("incomplete")}),
        "data_flags of a frozenset subclass": frozenset_subclass({"incomplete"}),
    }
    missed = []
    for label, flags in cases.items():
        try:
            _simulate(kit, m1, data_flags=flags)
        except TypeError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: simulate_trade must raise TypeError for:\n" + "\n".join(missed)


def test_ac03_r2_run_refuses_sides_with_an_element_that_is_not_str(monkeypatch):
    """Contract v1.5 item 4: sides with an element that is not str is TypeError."""
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _small(kit)
    _run_small(kit, m1, m15, sides=frozenset({"long"}))  # the valid baseline: long-only
    cases = {
        "an int side": frozenset({1}),
        "a bytes side": frozenset({b"long"}),
        "a str subclass side": frozenset({_Str("long")}),
        "long and an int": frozenset({"long", 1}),
    }
    missed = []
    for label, sides in cases.items():
        try:
            _run_small(kit, m1, m15, sides=sides)
        except TypeError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: run must raise TypeError for:\n" + "\n".join(missed)


def test_ac03_r2_result_trades_and_skips_are_tuples(monkeypatch):
    """Contract v1.5 item 5: Result.trades and Result.skips are tuples, with trades or without."""
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Trade", "Skip", "Result", "run")
    full, _, _, _ = _run_scenario(kit, "R")
    m1, m15 = _small(kit)
    empty = _run_small(kit, m1, m15)
    wrong = []
    for label, result in (("scenario R", full), ("no entry", empty)):
        if type(result) is not kit.Result:
            wrong.append(f"{label}: run returned a {type(result).__name__}")
            continue
        for name in ("trades", "skips"):
            value = getattr(result, name)
            if type(value) is not tuple:
                wrong.append(f"{label}: Result.{name} is a {type(value).__name__}, not a tuple")
    assert not wrong, "AC-03:\n" + "\n".join(wrong)


def test_ac03_r2_run_refuses_an_m15_bar_whose_time_utc_is_not_to_utc_of_its_time_raw(monkeypatch):
    """Contract v1.5 item 6: next_open_utc comes from the M15 time_utc, so it must match the rule."""
    kit = _kit(monkeypatch, "AC-03", "SizedLots", "Rollover", "Result", "BacktestError", "run")
    m1, m15 = _small(kit)
    _run_small(kit, m1, m15)  # the valid baseline runs
    aggregated = kit.snapshot.AggregatedBar

    def moved(item, minutes):
        bar = replace(item.bar, time_utc=item.bar.time_utc + timedelta(minutes=minutes))
        assert bar.time_raw == item.bar.time_raw and bar.time_utc.utcoffset() == timedelta(0), "fixture: a UTC time"
        return bar

    cases = {
        "bar 1 one minute late (AggregatedBar)": (m15[0], aggregated(moved(m15[1], 1), m15[1].flags)) + m15[2:],
        "the last bar one hour late (AggregatedBar)": m15[:3] + (aggregated(moved(m15[3], 60), m15[3].flags),),
        "the first bar one minute early (duck type)": (_DuckM15(moved(m15[0], -1), m15[0].flags),) + m15[1:],
        "every bar one hour late (duck type)": tuple(_DuckM15(moved(item, 60), item.flags) for item in m15),
    }
    missed = []
    for label, bars_m15 in cases.items():
        try:
            _run_small(kit, m1, bars_m15)
        except kit.BacktestError:
            continue
        except Exception as error:  # reported below: the wrong exception
            missed.append(f"{label}: {type(error).__name__}: {error}")
            continue
        missed.append(f"{label}: no error")
    assert not missed, "AC-03: run must raise BacktestError for:\n" + "\n".join(missed)
