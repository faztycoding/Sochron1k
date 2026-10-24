"""Approved CORE-006 contract tests (docs/contracts/CORE-006-strategy-h001.md, D1-D6); run pytest
from the repository root.

Only contract names are used: sochron.strategy (STRATEGY_ID, STRATEGY_VERSION, Variant,
H001Params, H001_DEFAULTS, StrategyError, IndicatorRow, indicators, Position, Decision, decide),
sochron.core.Bar, sochron.data.snapshot.AggregatedBar and sochron.timebase. Every bar is synthetic.

Conventions the contract leaves to these tests (also in docs/handoff/CORE-006.md):
1. StrategyError is a public name of sochron.strategy. H001Params, IndicatorRow and Decision are
   frozen dataclasses whose fields are exactly the contract's names in the contract's order; the
   tests build IndicatorRow by keyword (decide() is tested on such rows, AC-03 to AC-05).
2. A wrong type is TypeError: float, bool, int for a Decimal field, Decimal for an int field, str
   for a number, None and every subclass. A right type with a value outside H001 section 4 (or a
   variant other than "A", "B", "C") is StrategyError, a non-finite Decimal included. One unit
   beyond an edge is 1 for the int parameters, 0.01 for theta and 0.1 for k (the decimals H001
   section 4 writes); a 0.0001 step beyond is refused too.
3. IndicatorRow: atr is None before t = n - 1 (no Wilder seed yet), and ts is None whenever atr is
   None or 0 (D4); hh_n/ll_n exist from t = N and hh_m/ll_m from t = M; spread_median_96[t] is
   the mean of the 48th and 49th smallest of spread[t-96 .. t-1], None while t < 96 or while any
   of those 96 spreads is None. lookback_flags holds the defect flags of bars t-L+1 .. t (D3) and
   is empty when those bars carry nothing but "incomplete" (whether "incomplete" is listed next to
   a defect is left open). warm is t >= max(3s, N+1, M+1, 97, n+1) for every variant (D2). Bars
   are counted as given, never by clock slots. The golden EMA values are exact (no rounding), so
   they do not depend on how the EMA recurrence is written (open question 1 in the handoff).
4. Decision: skip has every failed reason in the contract order and stop_distance None; enter_*
   has reasons () and stop_distance = k x atr[t] in the module's own context (D1); exit, hold and
   none have reasons () and stop_distance None. spread_unknown replaces spread_filter when
   spread[t] or spread_median_96[t] is None. A flat position without an entry signal is "none".
   The caller's Decimal context is never used or changed (D1 "context of the module").

Left untested because the contract does not say: what decide() returns without an entry signal
during warm-up (none or skip), V-A/V-C entries when atr[t] = 0 (none or skip with atr_zero), exits
during warm-up, wrong argument types of indicators() and decide(), flag strings that are not
validation defect codes.
"""

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_UP, Decimal, Inexact, Rounded, getcontext, localcontext
from fractions import Fraction
from importlib import import_module
from pathlib import Path
import random
from runpy import run_path
from typing import get_args

import pytest


_MODULES = {"strategy": "sochron.strategy", "core": "sochron.core", "snapshot": "sochron.data.snapshot"}
_PARAM_FIELDS = ("variant", "f", "s", "n", "theta", "N", "M", "k")
_ROW_FIELDS = ("ema_f", "ema_s", "atr", "ts", "hh_n", "ll_n", "hh_m", "ll_m", "close", "spread",
               "spread_median_96", "warm", "lookback_flags")
_DECISION_FIELDS = ("action", "stop_distance", "reasons", "version")
_ACTIONS = ("enter_long", "enter_short", "exit", "hold", "none", "skip")
_REASONS = ("outside_window", "spread_filter", "spread_unknown", "atr_zero", "data_flag", "warmup")
# Defect codes sochron.data.snapshot.validate_m1 can put on a bar (empty_weekday has no bar time).
_DEFECT_CODES = ("not_minute_aligned", "time_rule_mismatch", "ohlc_inconsistent", "non_positive_price",
                 "missing_spread", "negative_spread", "duplicate_time", "time_not_increasing",
                 "unexpected_gap")
_VALID = {"variant": "B", "f": 16, "s": 64, "n": 20, "theta": Decimal("0.50"), "N": 96, "M": 48,
          "k": Decimal("2.0")}
T = 200  # warm under the defaults: max(3*64, 97, 49, 97, 21) = 192
IN_WINDOW = datetime(2026, 3, 10, 13, 45, tzinfo=UTC)  # 09:45 New York (EDT): the H001 example
OUT_OF_WINDOW = datetime(2026, 3, 10, 20, 0, tzinfo=UTC)  # 16:00 New York (EDT)


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


def _tb():
    """sochron.timebase (CORE-001, merged); call after _api has put src on the path."""
    return import_module("sochron.timebase")


def _golden():
    return run_path(str(Path(__file__).resolve().parents[2] / "golden/CORE-006/strategy_cases.py"))


def _context_state():
    context = getcontext()
    return (context.prec, context.rounding, context.Emin, context.Emax, context.capitals,
            context.clamp, dict(context.traps), dict(context.flags))


def _hostile(context):
    """A caller context that would change every rounded result if the module used it (D1)."""
    context.prec = 4
    context.rounding = ROUND_UP
    context.traps[Inexact] = True
    context.traps[Rounded] = True
    context.clear_flags()


class _Int(int):
    pass


class _Dec(Decimal):
    pass


class _Str(str):
    pass


# ----------------------------------------------------------------------------------- builders

def _bar(Bar, AggregatedBar, stamp, open_, high, low, close, spread, flags=()):
    """One synthetic M15 bar opening at `stamp` (naive UTC; the rule has offset 0, CORE-001)."""
    when = datetime.fromisoformat(stamp).replace(tzinfo=UTC)
    bar = Bar(time_raw=int(when.timestamp()), time_utc=when, timeframe=15, open=Decimal(open_),
              high=Decimal(high), low=Decimal(low), close=Decimal(close), spread=spread,
              tick_volume=100, m1_count=15)
    return AggregatedBar(bar, frozenset(flags))


def _series(Bar, AggregatedBar, count, start="2026-03-10T00:00", changes=None):
    """`count` consecutive M15 bars: open 4000, high 4001, low 3999, close 4000 (TR 2), spread
    240, no flag; changes {t: {"high": ..., "flags": ...}} replace values of single bars."""
    changes = changes or {}
    first = datetime.fromisoformat(start)
    bars = []
    for t in range(count):
        values = {"open_": "4000.00", "high": "4001.00", "low": "3999.00", "close": "4000.00",
                  "spread": 240, "flags": ()}
        values.update(changes.get(t, {}))
        stamp = (first + timedelta(minutes=15 * t)).isoformat(timespec="minutes")
        bars.append(_bar(Bar, AggregatedBar, stamp, **values))
    return tuple(bars)


def _params(H001Params, **changes):
    return H001Params(**{**_VALID, **changes})


def _row(IndicatorRow, ts="0", atr="6.00", close="4000.00", hh_n="4015.00", ll_n="3985.00",
         hh_m="4010.00", ll_m="3990.00", spread=240, median="240", warm=True, flags=()):
    """One indicator row consistent with TS = (EMA_f - EMA_s) / ATR: EMA_s 4005.20 and EMA_f =
    EMA_s + ts * atr. The defaults meet no entry condition under the defaults (theta 0.50)."""
    ema_s = Decimal("4005.20")
    atr_value = None if atr is None else Decimal(atr)
    ema_f = ema_s if ts is None else ema_s + Decimal(ts) * atr_value
    return IndicatorRow(
        ema_f=ema_f, ema_s=ema_s, atr=atr_value, ts=None if ts is None else Decimal(ts),
        hh_n=Decimal(hh_n), ll_n=Decimal(ll_n), hh_m=Decimal(hh_m), ll_m=Decimal(ll_m),
        close=Decimal(close), spread=spread, spread_median_96=None if median is None else Decimal(median),
        warm=warm, lookback_flags=frozenset(flags),
    )


def _rows(IndicatorRow, current, previous_ts=None, t=T, threshold=192):
    """Rows 0..t: quiet rows (warm from `threshold`), a row with TS `previous_ts` at t - 1 when
    given, and `current` at t."""
    rows = [_row(IndicatorRow, warm=index >= threshold) for index in range(t + 1)]
    if previous_ts is not None:
        rows[t - 1] = _row(IndicatorRow, ts=previous_ts, warm=t - 1 >= threshold)
    rows[t] = current
    return tuple(rows)


def _check_decision(decision, Decision, version):
    """Shape of every Decision (contract) and the reasons/stop_distance convention (item 4)."""
    assert type(decision) is Decision
    assert type(decision.version) is str and decision.version == version
    assert decision.action in _ACTIONS
    assert type(decision.reasons) is tuple
    assert all(type(reason) is str for reason in decision.reasons)
    if decision.action == "skip":
        assert decision.reasons, "skip must carry its reasons"
        assert set(decision.reasons) <= set(_REASONS)
        assert len(set(decision.reasons)) == len(decision.reasons)
        assert list(decision.reasons) == sorted(decision.reasons, key=_REASONS.index)
        assert decision.stop_distance is None
    elif decision.action in ("enter_long", "enter_short"):
        assert decision.reasons == ()
        assert type(decision.stop_distance) is Decimal
    else:
        assert decision.reasons == ()
        assert decision.stop_distance is None


def _decider(monkeypatch, ac):
    """(decide wrapped with the shape and context checks, IndicatorRow, H001Params)."""
    decide, Decision, version, IndicatorRow, H001Params = _api(
        monkeypatch, ac, "strategy.decide", "strategy.Decision", "strategy.STRATEGY_VERSION",
        "strategy.IndicatorRow", "strategy.H001Params",
    )

    def call(rows, t, position, next_open, params):
        before = _context_state()
        decision = decide(rows, t, position, next_open, params)
        assert _context_state() == before, f"{ac}: decide changed the caller's Decimal context"
        _check_decision(decision, Decision, version)
        return decision

    return call, IndicatorRow, H001Params


def _expect(decision, action, reasons=(), stop=None, label=""):
    assert (decision.action, decision.reasons) == (action, tuple(reasons)), label
    if stop is None:
        assert decision.stop_distance is None, label
    else:
        assert decision.stop_distance == Decimal(stop), label


# ----------------------------------------------------------------------------------- AC-01

def test_ac01_params_accept_every_edge_and_keep_exact_values(monkeypatch):
    H001Params, Variant = _api(monkeypatch, "AC-01", "strategy.H001Params", "strategy.Variant")
    assert get_args(Variant) == ("A", "B", "C")
    assert is_dataclass(H001Params)
    assert tuple(field.name for field in fields(H001Params)) == _PARAM_FIELDS
    accepted = (
        {}, {"variant": "A"}, {"variant": "C"},
        {"f": 8}, {"f": 24, "s": 72}, {"f": 24, "s": 96},
        {"s": 32, "f": 8}, {"s": 32, "f": 10}, {"s": 96},
        # s = 3f exactly
        {"f": 11, "s": 33}, {"f": 12, "s": 36}, {"f": 16, "s": 48}, {"f": 20, "s": 60},
        {"n": 10}, {"n": 30},
        {"theta": Decimal("0.25")}, {"theta": Decimal("1.00")}, {"theta": Decimal("1")},
        {"theta": Decimal("0.250")}, {"theta": Decimal("2.5E-1")},
        {"N": 48, "M": 48}, {"N": 48, "M": 24}, {"N": 192}, {"N": 192, "M": 96},
        # M = N exactly
        {"N": 96, "M": 96}, {"N": 60, "M": 60}, {"M": 24},
        {"k": Decimal("1.5")}, {"k": Decimal("3.0")}, {"k": Decimal("3")}, {"k": Decimal("1.50")},
        {"variant": "A", "f": 8, "s": 96, "n": 30, "theta": Decimal("1.00"), "N": 192, "M": 96,
         "k": Decimal("3.0")},
        {"variant": "C", "f": 8, "s": 32, "n": 10, "theta": Decimal("0.25"), "N": 48, "M": 24,
         "k": Decimal("1.5")},
    )
    for changes in accepted:
        values = {**_VALID, **changes}
        params = H001Params(**values)
        for name in _PARAM_FIELDS:
            actual = getattr(params, name)
            assert type(actual) is type(values[name]), (changes, name)
            assert actual == values[name], (changes, name)
    params = H001Params(**_VALID)
    assert params == H001Params(**_VALID)
    for name in _PARAM_FIELDS:
        with pytest.raises(FrozenInstanceError):
            setattr(params, name, getattr(params, name))


def test_ac01_params_out_of_range_or_breaking_a_constraint_raise_strategy_error(monkeypatch):
    H001Params, StrategyError = _api(monkeypatch, "AC-01", "strategy.H001Params", "strategy.StrategyError")
    assert issubclass(StrategyError, ValueError)
    assert not issubclass(StrategyError, TypeError)
    refused = (
        {"variant": "D"}, {"variant": "a"}, {"variant": ""}, {"variant": "AB"}, {"variant": "V-A"},
        {"f": 7}, {"f": 25, "s": 96}, {"f": 0}, {"f": -16},
        {"s": 31, "f": 8}, {"s": 97}, {"s": 0},
        # s < 3f by one (s = 3f - 1), and s inside 32-96 but below 3f
        {"f": 16, "s": 47}, {"f": 24, "s": 71}, {"f": 11, "s": 32}, {"f": 24, "s": 64},
        {"n": 9}, {"n": 31},
        {"theta": Decimal("0.24")}, {"theta": Decimal("1.01")}, {"theta": Decimal("0.2499")},
        {"theta": Decimal("1.0001")}, {"theta": Decimal("0")}, {"theta": Decimal("-0.50")},
        {"theta": Decimal("NaN")}, {"theta": Decimal("sNaN")}, {"theta": Decimal("Infinity")},
        {"theta": Decimal("-Infinity")},
        {"N": 47, "M": 24}, {"N": 193}, {"N": 0, "M": 24},
        {"M": 23}, {"M": 97, "N": 192},
        # M > N by one (M = N + 1)
        {"N": 48, "M": 49}, {"N": 60, "M": 61}, {"N": 95, "M": 96},
        {"k": Decimal("1.4")}, {"k": Decimal("3.1")}, {"k": Decimal("1.4999")},
        {"k": Decimal("3.0001")}, {"k": Decimal("-2.0")}, {"k": Decimal("NaN")},
        {"k": Decimal("Infinity")},
    )
    for changes in refused:
        with pytest.raises(StrategyError):
            H001Params(**{**_VALID, **changes})


def test_ac01_params_of_a_wrong_type_raise_type_error(monkeypatch):
    (H001Params,) = _api(monkeypatch, "AC-01", "strategy.H001Params")

    def integers(value):
        return (True, False, float(value), Decimal(value), str(value), _Int(value), None, Fraction(value))

    wrong = {
        "variant": (1, None, b"B", _Str("B"), ["B"], True, ("B",)),
        "f": integers(16), "s": integers(64), "n": integers(20), "N": integers(96), "M": integers(48),
        "theta": (0.5, 1, True, False, "0.50", _Dec("0.50"), Fraction(1, 2), None),
        "k": (2.0, 2, True, "2.0", _Dec("2.0"), Fraction(2), None),
    }
    for name, values in wrong.items():
        for value in values:
            with pytest.raises(TypeError):
                H001Params(**{**_VALID, name: value})


def test_ac01_defaults_match_the_h001_table_for_every_variant(monkeypatch):
    H001Params, H001_DEFAULTS = _api(monkeypatch, "AC-01", "strategy.H001Params", "strategy.H001_DEFAULTS")
    assert isinstance(H001_DEFAULTS, Mapping)
    assert set(H001_DEFAULTS) == {"A", "B", "C"} and len(H001_DEFAULTS) == 3
    expected = {"f": 16, "s": 64, "n": 20, "theta": Decimal("0.50"), "N": 96, "M": 48, "k": Decimal("2.0")}
    for variant in ("A", "B", "C"):
        params = H001_DEFAULTS[variant]
        assert type(params) is H001Params
        assert params.variant == variant
        for name, value in expected.items():
            actual = getattr(params, name)
            assert type(actual) is type(value), (variant, name)
            assert actual == value, (variant, name)
        assert params == H001Params(variant=variant, **expected)


# ----------------------------------------------------------------------------------- AC-02

_DECIMAL_COLUMNS = ("ema_f", "ema_s", "atr", "ts", "hh_n", "ll_n", "hh_m", "ll_m", "spread_median_96")


def _expected_rows(golden, series):
    expected = {}
    for first, last, *values in golden[f"ROWS_{series}"]:
        for t in range(first, last + 1):
            assert t not in expected, f"golden {series} lists row {t} twice"
            expected[t] = values
    return expected


def _golden_params(H001Params, golden, series, variant):
    values = golden[f"PARAMS_{series}"]
    return H001Params(variant=variant, f=values["f"], s=values["s"], n=values["n"],
                      theta=Decimal(values["theta"]), N=values["N"], M=values["M"], k=Decimal(values["k"]))


def _golden_mismatches(rows, bars, expected, IndicatorRow, label):
    assert type(rows) is tuple, label
    assert len(rows) == len(bars) == len(expected), label
    wrong = []
    for t, (row, aggregated) in enumerate(zip(rows, bars)):
        assert type(row) is IndicatorRow, label
        values = expected[t]
        for name, value in zip(_DECIMAL_COLUMNS, values):
            actual = getattr(row, name)
            ok = actual is None if value is None else type(actual) is Decimal and actual == Decimal(value)
            if not ok:
                wrong.append(f"{label} t={t} {name}: expected {value}, got {actual!r}")
        if row.warm is not values[-1]:
            wrong.append(f"{label} t={t} warm: expected {values[-1]}, got {row.warm!r}")
        if not (type(row.close) is Decimal and row.close == aggregated.bar.close):
            wrong.append(f"{label} t={t} close: got {row.close!r}")
        if not (row.spread == aggregated.bar.spread and type(row.spread) is type(aggregated.bar.spread)):
            wrong.append(f"{label} t={t} spread: got {row.spread!r}")
        if not (type(row.lookback_flags) is frozenset and row.lookback_flags == frozenset()):
            wrong.append(f"{label} t={t} lookback_flags: got {row.lookback_flags!r}")
    return wrong


@pytest.mark.parametrize("variant", ("A", "B", "C"))
@pytest.mark.parametrize("series", ("S", "P", "G"))
def test_ac02_indicators_match_the_hand_computed_golden_rows(monkeypatch, series, variant):
    H001Params, IndicatorRow, indicators, Bar, AggregatedBar = _api(
        monkeypatch, "AC-02", "strategy.H001Params", "strategy.IndicatorRow", "strategy.indicators",
        "core.Bar", "snapshot.AggregatedBar",
    )
    assert is_dataclass(IndicatorRow)
    assert tuple(field.name for field in fields(IndicatorRow)) == _ROW_FIELDS
    golden = _golden()
    bars = tuple(_bar(Bar, AggregatedBar, *row) for row in golden[f"BARS_{series}"])
    params = _golden_params(H001Params, golden, series, variant)
    expected = _expected_rows(golden, series)
    before = _context_state()
    rows = indicators(bars, params)
    assert _context_state() == before, "AC-02: indicators changed the caller's Decimal context"
    wrong = _golden_mismatches(rows, bars, expected, IndicatorRow, f"{series}/{variant}")
    assert not wrong, "AC-02: rows differ from the golden table:\n" + "\n".join(wrong)
    with pytest.raises(FrozenInstanceError):
        rows[0].close = Decimal("1")


@pytest.mark.parametrize("series", ("S", "P", "G"))
def test_ac02_golden_rows_hold_under_a_hostile_caller_context(monkeypatch, series):
    """D1: the module computes in its own context (precision 28, ROUND_HALF_EVEN), never the caller's."""
    H001Params, IndicatorRow, indicators, Bar, AggregatedBar = _api(
        monkeypatch, "AC-02", "strategy.H001Params", "strategy.IndicatorRow", "strategy.indicators",
        "core.Bar", "snapshot.AggregatedBar",
    )
    golden = _golden()
    bars = tuple(_bar(Bar, AggregatedBar, *row) for row in golden[f"BARS_{series}"])
    params = _golden_params(H001Params, golden, series, "B")
    with localcontext() as caller:
        _hostile(caller)
        before = _context_state()
        rows = indicators(bars, params)
        assert _context_state() == before, "AC-02: indicators changed the caller's Decimal context"
    wrong = _golden_mismatches(rows, bars, _expected_rows(golden, series), IndicatorRow, f"{series}/hostile")
    assert not wrong, "AC-02: rows depend on the caller's context:\n" + "\n".join(wrong)


@pytest.mark.parametrize(("changes", "threshold"), (
    ({"f": 8, "s": 32, "n": 10, "N": 48, "M": 24}, 97),  # the 97 of the 96-bar median binds
    ({}, 192),                                             # defaults: 3s = 192 binds
    ({"f": 8, "s": 32, "n": 30, "N": 192, "M": 96}, 193),  # N + 1 binds
    ({"f": 11, "s": 33, "n": 10, "N": 48, "M": 48}, 99),   # 3s = 99 binds, M = N
), ids=("97", "3s-192", "N+1-193", "3s-99"))
def test_ac02_warm_starts_exactly_at_the_d2_threshold_in_every_variant(monkeypatch, changes, threshold):
    H001Params, indicators, Bar, AggregatedBar = _api(
        monkeypatch, "AC-02", "strategy.H001Params", "strategy.indicators", "core.Bar", "snapshot.AggregatedBar",
    )
    bars = _series(Bar, AggregatedBar, threshold + 3)
    for variant in ("A", "B", "C"):
        rows = indicators(bars, _params(H001Params, variant=variant, **changes))
        assert [row.warm for row in rows] == [t >= threshold for t in range(len(bars))], variant
        assert all(type(row.warm) is bool for row in rows)


# ----------------------------------------------------------------------------------- AC-03

def _example(IndicatorRow, side="long"):
    """H001 section 3 worked example (TS 1.20 after 0.45, theta 0.5, ATR 6.00, HH_96 4015.00,
    close 4016.30) at t = T, and its mirror for side "short" (TS -1.20 after -0.45, LL_96 3995.00,
    close 3993.70)."""
    sign = "" if side == "long" else "-"
    current = _row(IndicatorRow, ts=f"{sign}1.20", close="4016.30" if side == "long" else "3993.70",
                   hh_n="4015.00", ll_n="3995.00", hh_m="4014.00", ll_m="3996.00")
    rows = _rows(IndicatorRow, current, previous_ts=f"{sign}0.45")
    return rows


def test_ac03_h001_worked_example_enters_long_in_every_variant_with_stop_12(monkeypatch):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-03")
    rows = _example(IndicatorRow)
    current = rows[T]
    # The example's own numbers: EMA_16 4012.40, EMA_64 4005.20, TS = 7.20 / 6.00 = 1.20.
    assert (current.ema_f, current.ema_s, current.atr, current.ts) == (
        Decimal("4012.40"), Decimal("4005.20"), Decimal("6.00"), Decimal("1.20"))
    for variant in ("A", "B", "C"):
        decision = decide(rows, T, "flat", IN_WINDOW, _params(H001Params, variant=variant))
        _expect(decision, "enter_long", stop="12.00", label=variant)


def test_ac03_mirrored_worked_example_enters_short_in_every_variant_with_stop_12(monkeypatch):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-03")
    rows = _example(IndicatorRow, "short")
    for variant in ("A", "B", "C"):
        decision = decide(rows, T, "flat", IN_WINDOW, _params(H001Params, variant=variant))
        _expect(decision, "enter_short", stop="12.00", label=variant)


# (label, variant, row values at t, TS at t - 1 or None for a quiet row, expected action)
_ENTRY_EDGES = (
    ("V-A ts[t] equal to theta does not enter", "A", {"ts": "0.50"}, "0.45", "none"),
    ("V-A ts[t-1] equal to theta then ts[t] above enters", "A", {"ts": "0.51"}, "0.50", "enter_long"),
    ("V-A both above theta is no crossing", "A", {"ts": "0.60"}, "0.51", "none"),
    ("V-A a jump from below -theta to above theta enters long", "A", {"ts": "0.60"}, "-0.60", "enter_long"),
    ("V-A ts[t] equal to -theta does not enter short", "A", {"ts": "-0.50"}, "-0.45", "none"),
    ("V-A ts[t-1] equal to -theta then ts[t] below enters short", "A", {"ts": "-0.51"}, "-0.50",
     "enter_short"),
    ("V-A both below -theta is no crossing", "A", {"ts": "-0.60"}, "-0.51", "none"),
    ("V-A ignores a Donchian breakout", "A", {"ts": "0.30", "close": "4015.01"}, "0.20", "none"),
    ("V-A quiet row", "A", {"ts": "0.30"}, "0.30", "none"),
    ("V-B close equal to hh_n is not a breakout", "B", {"close": "4015.00"}, None, "none"),
    ("V-B close one cent above hh_n enters", "B", {"close": "4015.01"}, None, "enter_long"),
    ("V-B close equal to ll_n is not a breakout", "B", {"close": "3985.00"}, None, "none"),
    ("V-B close one cent below ll_n enters short", "B", {"close": "3984.99"}, None, "enter_short"),
    ("V-B ignores TS", "B", {"close": "4015.01", "ts": "-1.20"}, None, "enter_long"),
    ("V-B quiet row", "B", {}, None, "none"),
    ("V-C breakout with ts 0 does not enter", "C", {"close": "4015.01", "ts": "0"}, None, "none"),
    ("V-C breakout with ts above 0 enters", "C", {"close": "4015.01", "ts": "0.01"}, None, "enter_long"),
    ("V-C breakout with ts below 0 does not enter", "C", {"close": "4015.01", "ts": "-1.20"}, None, "none"),
    ("V-C breakdown with ts 0 does not enter", "C", {"close": "3984.99", "ts": "0"}, None, "none"),
    ("V-C breakdown with ts below 0 enters short", "C", {"close": "3984.99", "ts": "-0.01"}, None,
     "enter_short"),
    ("V-C breakdown with ts above 0 does not enter", "C", {"close": "3984.99", "ts": "1.20"}, None, "none"),
    ("V-C TS crossing theta without a breakout", "C", {"ts": "1.20"}, "0.45", "none"),
    ("V-C quiet row", "C", {}, None, "none"),
)


@pytest.mark.parametrize("case", _ENTRY_EDGES, ids=[case[0] for case in _ENTRY_EDGES])
def test_ac03_threshold_crossings_and_breakout_edges(monkeypatch, case):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-03")
    label, variant, values, previous_ts, action = case
    rows = _rows(IndicatorRow, _row(IndicatorRow, **values), previous_ts)
    decision = decide(rows, T, "flat", IN_WINDOW, _params(H001Params, variant=variant))
    _expect(decision, action, stop="12.00" if action.startswith("enter_") else None, label=label)


def test_ac03_stop_distance_is_k_times_atr_at_precision_28_half_even(monkeypatch):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-03")
    cases = (
        # (k, atr, stop): 2.5 * 1.000000000000000000000000001 = 2.5000000000000000000000000025 has
        # 29 digits; the tie goes to the even 2. With ...003 the product ends ...0075 and the tie
        # goes up to the even 8. Exact products stay exact.
        ("2.5", "1.000000000000000000000000001", "2.500000000000000000000000002"),
        ("2.5", "1.000000000000000000000000003", "2.500000000000000000000000008"),
        ("1.5", "6.00", "9.00"),
        ("3.0", "6.00", "18.00"),
        ("1.75", "2.09", "3.6575"),
        ("2.0", "3.58995937", "7.17991874"),
    )
    for k, atr, stop in cases:
        params = _params(H001Params, variant="B", k=Decimal(k))
        rows = _rows(IndicatorRow, _row(IndicatorRow, atr=atr, close="4015.01"))
        _expect(decide(rows, T, "flat", IN_WINDOW, params), "enter_long", stop=stop, label=(k, atr))
        with localcontext() as caller:
            _hostile(caller)
            decision = decide(rows, T, "flat", IN_WINDOW, params)
        _expect(decision, "enter_long", stop=stop, label=("hostile", k, atr))
        short = _rows(IndicatorRow, _row(IndicatorRow, atr=atr, close="3984.99"))
        _expect(decide(short, T, "flat", IN_WINDOW, params), "enter_short", stop=stop, label=(k, atr))


def test_ac03_constants_and_every_action_carry_the_strategy_version(monkeypatch):
    STRATEGY_ID, STRATEGY_VERSION, Position, Decision = _api(
        monkeypatch, "AC-03", "strategy.STRATEGY_ID", "strategy.STRATEGY_VERSION", "strategy.Position",
        "strategy.Decision",
    )
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-03")
    assert type(STRATEGY_ID) is str and STRATEGY_ID == "H001"
    assert type(STRATEGY_VERSION) is str and STRATEGY_VERSION == "H001-v1"
    assert get_args(Position) == ("flat", "long", "short")
    assert is_dataclass(Decision)
    assert tuple(field.name for field in fields(Decision)) == _DECISION_FIELDS
    params = _params(H001Params, variant="B")
    breakout = _rows(IndicatorRow, _row(IndicatorRow, close="4015.01"))
    breakdown = _rows(IndicatorRow, _row(IndicatorRow, close="3984.99"))
    quiet = _rows(IndicatorRow, _row(IndicatorRow))
    seen = [
        decide(breakout, T, "flat", IN_WINDOW, params),
        decide(breakdown, T, "flat", IN_WINDOW, params),
        decide(breakdown, T, "long", IN_WINDOW, params),
        decide(quiet, T, "long", IN_WINDOW, params),
        decide(quiet, T, "flat", IN_WINDOW, params),
        decide(breakout, T, "flat", OUT_OF_WINDOW, params),
    ]
    assert [decision.action for decision in seen] == list(_ACTIONS)
    for decision in seen:
        assert decision.version == STRATEGY_VERSION
        with pytest.raises(FrozenInstanceError):
            decision.version = "other"


# ----------------------------------------------------------------------------------- AC-04

# (label, variant, position, row values at t, TS at t - 1 or None, expected action)
_EXIT_CASES = (
    ("V-A long, ts 0 exits", "A", "long", {"ts": "0"}, "0.30", "exit"),
    ("V-A long, ts -0.10 exits (H001 worked example)", "A", "long", {"ts": "-0.10"}, "0.30", "exit"),
    ("V-A long, ts 0.01 holds", "A", "long", {"ts": "0.01"}, "0.30", "hold"),
    ("V-A long, the long signal again holds", "A", "long", {"ts": "1.20"}, "0.45", "hold"),
    ("V-A long, the short signal exits without a short", "A", "long", {"ts": "-0.60"}, "-0.45", "exit"),
    ("V-A long, a Donchian breakdown alone holds", "A", "long", {"ts": "0.30", "close": "3984.99"}, "0.30",
     "hold"),
    ("V-A long, ts unknown (ATR 0) holds (D4)", "A", "long", {"ts": None, "atr": "0"}, "0.30", "hold"),
    ("V-A short, ts 0 exits (D5)", "A", "short", {"ts": "0"}, "-0.30", "exit"),
    ("V-A short, ts 0.10 exits", "A", "short", {"ts": "0.10"}, "-0.30", "exit"),
    ("V-A short, ts -0.01 holds", "A", "short", {"ts": "-0.01"}, "-0.30", "hold"),
    ("V-A short, the short signal again holds", "A", "short", {"ts": "-1.20"}, "-0.45", "hold"),
    ("V-A short, the long signal exits without a long", "A", "short", {"ts": "0.60"}, "0.45", "exit"),
    ("V-A short, a Donchian breakout alone holds", "A", "short", {"ts": "-0.30", "close": "4015.01"},
     "-0.30", "hold"),
    ("V-A short, ts unknown (ATR 0) holds (D4)", "A", "short", {"ts": None, "atr": "0"}, "-0.30", "hold"),
    ("V-B long, close below ll_m exits", "B", "long", {"close": "3989.99"}, None, "exit"),
    ("V-B long, close equal to ll_m holds", "B", "long", {"close": "3990.00"}, None, "hold"),
    ("V-B long, the long signal again holds", "B", "long", {"close": "4015.01"}, None, "hold"),
    ("V-B long, the short signal exits without a short", "B", "long", {"close": "3984.99"}, None, "exit"),
    ("V-B long, ts below 0 alone holds", "B", "long", {"ts": "-1.20"}, None, "hold"),
    ("V-B long, ATR 0 does not stop the Donchian exit", "B", "long", {"close": "3989.99", "ts": None,
                                                                      "atr": "0"}, None, "exit"),
    ("V-B short, close above hh_m exits", "B", "short", {"close": "4010.01"}, None, "exit"),
    ("V-B short, close equal to hh_m holds", "B", "short", {"close": "4010.00"}, None, "hold"),
    ("V-B short, the short signal again holds", "B", "short", {"close": "3984.99"}, None, "hold"),
    ("V-B short, the long signal exits without a long", "B", "short", {"close": "4015.01"}, None, "exit"),
    ("V-B short, ts above 0 alone holds", "B", "short", {"ts": "1.20"}, None, "hold"),
    ("V-C long, close below ll_m exits", "C", "long", {"close": "3989.99", "ts": "0.30"}, None, "exit"),
    ("V-C long, close equal to ll_m holds", "C", "long", {"close": "3990.00", "ts": "0.30"}, None, "hold"),
    ("V-C long, the long signal again holds", "C", "long", {"close": "4015.01", "ts": "0.30"}, None, "hold"),
    ("V-C long, the short signal exits without a short", "C", "long", {"close": "3984.99", "ts": "-1.20"},
     None, "exit"),
    ("V-C long, ts below 0 alone holds", "C", "long", {"ts": "-1.20"}, None, "hold"),
    ("V-C short, close above hh_m exits", "C", "short", {"close": "4010.01", "ts": "-0.30"}, None, "exit"),
    ("V-C short, close equal to hh_m holds", "C", "short", {"close": "4010.00", "ts": "-0.30"}, None, "hold"),
    ("V-C short, the short signal again holds", "C", "short", {"close": "3984.99", "ts": "-0.30"}, None,
     "hold"),
    ("V-C short, the long signal exits without a long", "C", "short", {"close": "4015.01", "ts": "1.20"},
     None, "exit"),
    ("V-C short, ts above 0 alone holds", "C", "short", {"ts": "1.20"}, None, "hold"),
)


@pytest.mark.parametrize("case", _EXIT_CASES, ids=[case[0] for case in _EXIT_CASES])
def test_ac04_exits_and_holds_in_every_variant(monkeypatch, case):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-04")
    label, variant, position, values, previous_ts, action = case
    rows = _rows(IndicatorRow, _row(IndicatorRow, **values), previous_ts)
    _expect(decide(rows, T, position, IN_WINDOW, _params(H001Params, variant=variant)), action, label=label)


# Conditions that block an entry; an exit or a hold must not depend on them.
_BLOCKERS = (
    ("next bar opens 16:00 New York", {}, OUT_OF_WINDOW),
    ("spread above 3 x median", {"spread": 721}, IN_WINDOW),
    ("spread unknown", {"spread": None}, IN_WINDOW),
    ("spread median unknown", {"median": None}, IN_WINDOW),
    ("a defect flag in the lookback", {"flags": ("ohlc_inconsistent",)}, IN_WINDOW),
    ("all of them", {"spread": None, "median": None, "flags": ("unexpected_gap", "missing_spread")},
     OUT_OF_WINDOW),
)
# (variant, position, row values at t, TS at t - 1, expected action without any blocker)
_POSITIONS = (
    ("A", "long", {"ts": "-0.10"}, "0.30", "exit"),
    ("A", "short", {"ts": "0.10"}, "-0.30", "exit"),
    ("A", "long", {"ts": "-0.60"}, "-0.45", "exit"),
    ("B", "long", {"close": "3989.99"}, None, "exit"),
    ("B", "short", {"close": "4010.01"}, None, "exit"),
    ("B", "short", {"close": "4015.01"}, None, "exit"),
    ("C", "long", {"close": "3989.99", "ts": "0.30"}, None, "exit"),
    ("C", "short", {"close": "4010.01", "ts": "-0.30"}, None, "exit"),
    ("A", "long", {"ts": "1.20"}, "0.45", "hold"),
    ("A", "short", {"ts": "-0.30"}, "-0.30", "hold"),
    ("B", "long", {"close": "4015.01"}, None, "hold"),
    ("B", "short", {}, None, "hold"),
    ("C", "long", {"ts": "0.30"}, None, "hold"),
    ("C", "short", {"close": "3984.99", "ts": "-0.30"}, None, "hold"),
)


@pytest.mark.parametrize("blocker", _BLOCKERS, ids=[blocker[0] for blocker in _BLOCKERS])
def test_ac04_exit_and_hold_ignore_the_window_and_every_invalidation(monkeypatch, blocker):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-04")
    label, extra, next_open = blocker
    for variant, position, values, previous_ts, action in _POSITIONS:
        rows = _rows(IndicatorRow, _row(IndicatorRow, **{**values, **extra}), previous_ts)
        decision = decide(rows, T, position, next_open, _params(H001Params, variant=variant))
        _expect(decision, action, label=(label, variant, position, values))
    # ATR 0 (ts unknown) blocks an entry too: the Donchian exits of V-B and V-C still happen.
    for variant, position, close in (("B", "long", "3989.99"), ("C", "short", "4010.01")):
        rows = _rows(IndicatorRow, _row(IndicatorRow, **{"close": close, "ts": None, "atr": "0", **extra}))
        decision = decide(rows, T, position, next_open, _params(H001Params, variant=variant))
        _expect(decision, "exit", label=(label, variant, "atr 0"))


# ----------------------------------------------------------------------------------- AC-05

# (label, variant, row values at t, TS at t - 1, action when every check passes)
_SIGNALS = (
    ("V-A long", "A", {"ts": "1.20"}, "0.45", "enter_long"),
    ("V-A short", "A", {"ts": "-1.20"}, "-0.45", "enter_short"),
    ("V-B long", "B", {"close": "4015.01"}, None, "enter_long"),
    ("V-B short", "B", {"close": "3984.99"}, None, "enter_short"),
    ("V-C long", "C", {"close": "4015.01", "ts": "1.20"}, None, "enter_long"),
    ("V-C short", "C", {"close": "3984.99", "ts": "-1.20"}, None, "enter_short"),
)
# (label, extra row values, next bar open, reasons)
_ALONE = (
    ("next bar opens 16:00 New York", {}, OUT_OF_WINDOW, ("outside_window",)),
    ("spread 721 above 3 x 240", {"spread": 721}, IN_WINDOW, ("spread_filter",)),
    ("spread 722 above 3 x 240.5", {"spread": 722, "median": "240.5"}, IN_WINDOW, ("spread_filter",)),
    ("spread unknown at t", {"spread": None}, IN_WINDOW, ("spread_unknown",)),
    ("median unknown (a spread missing in the 96 bars)", {"median": None}, IN_WINDOW, ("spread_unknown",)),
    ("spread and median unknown", {"spread": None, "median": None}, IN_WINDOW, ("spread_unknown",)),
    ("one defect flag in the lookback", {"flags": ("missing_spread",)}, IN_WINDOW, ("data_flag",)),
    ("two defect flags in the lookback", {"flags": ("unexpected_gap", "negative_spread")}, IN_WINDOW,
     ("data_flag",)),
)
# (label, extra row values, next bar open): edges that pass
_PASSING = (
    ("spread exactly 3 x median 240", {"spread": 720}, IN_WINDOW),
    ("spread 721 below 3 x 240.5 = 721.5", {"spread": 721, "median": "240.5"}, IN_WINDOW),
    ("spread exactly 3 x median 241 = 723", {"spread": 723, "median": "241"}, IN_WINDOW),
    ("next bar opens 03:00 New York", {}, datetime(2026, 3, 10, 7, 0, tzinfo=UTC)),
    ("next bar opens 15:45 New York", {}, datetime(2026, 3, 10, 19, 45, tzinfo=UTC)),
)


@pytest.mark.parametrize("signal", _SIGNALS, ids=[signal[0] for signal in _SIGNALS])
def test_ac05_each_invalidation_alone_skips_with_its_reason(monkeypatch, signal):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-05")
    name, variant, values, previous_ts, action = signal
    params = _params(H001Params, variant=variant)
    clean = _rows(IndicatorRow, _row(IndicatorRow, **values), previous_ts)
    _expect(decide(clean, T, "flat", IN_WINDOW, params), action, stop="12.00", label=name)
    for label, extra, next_open, reasons in _ALONE:
        rows = _rows(IndicatorRow, _row(IndicatorRow, **{**values, **extra}), previous_ts)
        _expect(decide(rows, T, "flat", next_open, params), "skip", reasons, label=(name, label))
    for label, extra, next_open in _PASSING:
        rows = _rows(IndicatorRow, _row(IndicatorRow, **{**values, **extra}), previous_ts)
        _expect(decide(rows, T, "flat", next_open, params), action, stop="12.00", label=(name, label))
    # Warm-up (D2: threshold 192 under the defaults): t = 150 and 191 skip, t = 192 enters.
    for t, warm in ((150, False), (191, False), (192, True)):
        rows = _rows(IndicatorRow, _row(IndicatorRow, **values, warm=warm), previous_ts, t=t)
        decision = decide(rows, t, "flat", IN_WINDOW, params)
        if warm:
            _expect(decision, action, stop="12.00", label=(name, t))
        else:
            _expect(decision, "skip", ("warmup",), label=(name, t))


def test_ac05_atr_zero_skips_a_breakout_and_unknown_ts_makes_a_ts_rule_false(monkeypatch):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-05")
    breakout = {"ts": None, "atr": "0", "close": "4015.01"}
    breakdown = {"ts": None, "atr": "0", "close": "3984.99"}
    for values in (breakout, breakdown):
        rows = _rows(IndicatorRow, _row(IndicatorRow, **values))
        _expect(decide(rows, T, "flat", IN_WINDOW, _params(H001Params, variant="B")), "skip", ("atr_zero",))
    # D4: ts[t-1] unknown (ATR 0 at t - 1) makes "TS[t-1] <= theta" false, so V-A has no crossing.
    for ts in ("1.20", "-1.20"):
        rows = list(_rows(IndicatorRow, _row(IndicatorRow, ts=ts)))
        rows[T - 1] = _row(IndicatorRow, ts=None, atr="0")
        decision = decide(tuple(rows), T, "flat", IN_WINDOW, _params(H001Params, variant="A"))
        _expect(decision, "none", label=ts)


# (label, variant, row values at t, TS at t - 1, t, warm, next bar open, reasons in contract order)
_TOGETHER = (
    ("window, spread filter, flag and warm-up", "B",
     {"close": "4015.01", "spread": 721, "flags": ("missing_spread",)}, None, 150, False, OUT_OF_WINDOW,
     ("outside_window", "spread_filter", "data_flag", "warmup")),
    ("spread unknown and ATR 0", "B", {"close": "4015.01", "spread": None, "ts": None, "atr": "0"}, None,
     T, True, IN_WINDOW, ("spread_unknown", "atr_zero")),
    ("five reasons with the spread unknown", "B",
     {"close": "4015.01", "spread": None, "ts": None, "atr": "0", "flags": ("duplicate_time",)}, None,
     150, False, OUT_OF_WINDOW, ("outside_window", "spread_unknown", "atr_zero", "data_flag", "warmup")),
    ("five reasons with the spread filter", "B",
     {"close": "3984.99", "spread": 999, "ts": None, "atr": "0", "flags": ("negative_spread",)}, None,
     150, False, OUT_OF_WINDOW, ("outside_window", "spread_filter", "atr_zero", "data_flag", "warmup")),
    ("V-A window and spread filter", "A", {"ts": "1.20", "spread": 721}, "0.45", T, True, OUT_OF_WINDOW,
     ("outside_window", "spread_filter")),
    ("V-A short median unknown and warm-up", "A", {"ts": "-1.20", "median": None}, "-0.45", 191, False,
     IN_WINDOW, ("spread_unknown", "warmup")),
    ("V-C short spread filter and flag", "C",
     {"close": "3984.99", "ts": "-1.20", "spread": 800, "flags": ("ohlc_inconsistent",)}, None, T, True,
     IN_WINDOW, ("spread_filter", "data_flag")),
    ("V-C long window, flag and warm-up", "C", {"close": "4015.01", "ts": "1.20", "flags": ("unexpected_gap",)},
     None, 100, False, OUT_OF_WINDOW, ("outside_window", "data_flag", "warmup")),
)


@pytest.mark.parametrize("case", _TOGETHER, ids=[case[0] for case in _TOGETHER])
def test_ac05_several_invalidations_report_every_reason_in_contract_order(monkeypatch, case):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-05")
    label, variant, values, previous_ts, t, warm, next_open, reasons = case
    rows = _rows(IndicatorRow, _row(IndicatorRow, **values, warm=warm), previous_ts, t=t)
    decision = decide(rows, t, "flat", next_open, _params(H001Params, variant=variant))
    _expect(decision, "skip", reasons, label=label)


# New York 2026: DST begins Sunday 2026-03-08 at 07:00 UTC (02:00 EST -> 03:00 EDT) and ends Sunday
# 2026-11-01 at 06:00 UTC (02:00 EDT -> 01:00 EST). The window is 03:00-15:59 New York (H001).
# (label, next bar open UTC, inside the window)
_NY_EDGES = (
    ("Fri 03-06 EST 02:45", "2026-03-06T07:45", False),
    ("Fri 03-06 EST 03:00", "2026-03-06T08:00", True),
    ("Fri 03-06 EST 15:45", "2026-03-06T20:45", True),
    ("Fri 03-06 EST 16:00", "2026-03-06T21:00", False),
    ("Sun 03-08 01:45 EST, the last bar before the change (02:45 does not exist)", "2026-03-08T06:45", False),
    ("Sun 03-08 03:00 EDT", "2026-03-08T07:00", True),
    ("Sun 03-08 03:45 EDT (02:45 if EST were kept)", "2026-03-08T07:45", True),
    ("Sun 03-08 15:45 EDT", "2026-03-08T19:45", True),
    ("Sun 03-08 16:00 EDT", "2026-03-08T20:00", False),
    ("Sun 03-08 16:45 EDT (15:45 if EST were kept)", "2026-03-08T20:45", False),
    ("Mon 03-09 EDT 02:45", "2026-03-09T06:45", False),
    ("Mon 03-09 EDT 03:00", "2026-03-09T07:00", True),
    ("Mon 03-09 EDT 15:45", "2026-03-09T19:45", True),
    ("Mon 03-09 EDT 16:00", "2026-03-09T20:00", False),
    ("Fri 10-30 EDT 02:45", "2026-10-30T06:45", False),
    ("Fri 10-30 EDT 03:00", "2026-10-30T07:00", True),
    ("Fri 10-30 EDT 15:45", "2026-10-30T19:45", True),
    ("Fri 10-30 EDT 16:00", "2026-10-30T20:00", False),
    ("Sun 11-01 02:00 EST (03:00 if EDT were kept)", "2026-11-01T07:00", False),
    ("Sun 11-01 02:45 EST", "2026-11-01T07:45", False),
    ("Sun 11-01 03:00 EST", "2026-11-01T08:00", True),
    ("Sun 11-01 15:00 EST (16:00 if EDT were kept)", "2026-11-01T20:00", True),
    ("Sun 11-01 15:45 EST", "2026-11-01T20:45", True),
    ("Sun 11-01 16:00 EST", "2026-11-01T21:00", False),
    ("Mon 11-02 EST 02:45", "2026-11-02T07:45", False),
    ("Mon 11-02 EST 03:00", "2026-11-02T08:00", True),
    ("Mon 11-02 EST 15:45", "2026-11-02T20:45", True),
    ("Mon 11-02 EST 16:00", "2026-11-02T21:00", False),
)


@pytest.mark.parametrize("edge", _NY_EDGES, ids=[edge[0] for edge in _NY_EDGES])
def test_ac05_new_york_window_edges_on_both_2026_dst_changes(monkeypatch, edge):
    decide, IndicatorRow, H001Params = _decider(monkeypatch, "AC-05")
    label, iso, inside = edge
    next_open = datetime.fromisoformat(iso).replace(tzinfo=UTC)
    assert _tb().in_entry_window(next_open) is inside, f"table error at {label}"
    for variant, values, previous_ts, action in (
        ("B", {"close": "4015.01"}, None, "enter_long"),
        ("A", {"ts": "-1.20"}, "-0.45", "enter_short"),
    ):
        rows = _rows(IndicatorRow, _row(IndicatorRow, **values), previous_ts)
        decision = decide(rows, T, "flat", next_open, _params(H001Params, variant=variant))
        if inside:
            _expect(decision, action, stop="12.00", label=(label, variant))
        else:
            _expect(decision, "skip", ("outside_window",), label=(label, variant))


def _flags_without_incomplete(flags):
    return frozenset(flags) - {"incomplete"}


def test_ac05_lookback_flags_cover_bars_t_minus_l_plus_1_to_t_by_variant(monkeypatch):
    """D3: L = max(n, 96, N, M) + 1 for V-B and V-C, max(n, 96) + 1 for V-A."""
    H001Params, indicators, Bar, AggregatedBar = _api(
        monkeypatch, "AC-05", "strategy.H001Params", "strategy.indicators", "core.Bar", "snapshot.AggregatedBar",
    )
    small = {"f": 8, "s": 32, "n": 10, "N": 192, "M": 96}
    bars = _series(Bar, AggregatedBar, 260, changes={30: {"flags": ("missing_spread",)}})
    for variant, length in (("A", 97), ("B", 193), ("C", 193)):
        rows = indicators(bars, _params(H001Params, variant=variant, **small))
        for t, row in enumerate(rows):
            assert type(row.lookback_flags) is frozenset
            expected = frozenset({"missing_spread"}) if 30 <= t <= 30 + length - 1 else frozenset()
            assert row.lookback_flags == expected, (variant, t)
    # Every defect code counts; with N = 48 the window of every variant is t-96 .. t.
    for code in _DEFECT_CODES:
        bars = _series(Bar, AggregatedBar, 200, changes={100: {"flags": (code,)}})
        for variant in ("A", "B", "C"):
            rows = indicators(bars, _params(H001Params, variant=variant, f=8, s=32, n=10, N=48, M=24))
            assert rows[99].lookback_flags == frozenset(), (code, variant)
            for t in (100, 150, 196):
                assert rows[t].lookback_flags == {code}, (code, variant, t)
            assert rows[197].lookback_flags == frozenset(), (code, variant)


def test_ac05_incomplete_alone_never_fills_lookback_flags(monkeypatch):
    """D3: "incomplete" alone does not invalidate; next to a defect, the defect still counts."""
    H001Params, indicators, Bar, AggregatedBar = _api(
        monkeypatch, "AC-05", "strategy.H001Params", "strategy.indicators", "core.Bar", "snapshot.AggregatedBar",
    )
    lone = {t: {"flags": ("incomplete",)} for t in (0, 20, 60, 100, 129)}
    bars = _series(Bar, AggregatedBar, 130, changes=lone)
    for variant in ("A", "B", "C"):
        rows = indicators(bars, _params(H001Params, variant=variant, f=8, s=32, n=10, N=48, M=24))
        assert all(row.lookback_flags == frozenset() for row in rows), variant
    mixed = {90: {"flags": ("missing_spread",)}, 100: {"flags": ("incomplete", "ohlc_inconsistent")},
             110: {"flags": ("incomplete",)}}
    bars = _series(Bar, AggregatedBar, 120, changes=mixed)
    for variant in ("A", "B", "C"):
        rows = indicators(bars, _params(H001Params, variant=variant, f=8, s=32, n=10, N=48, M=24))
        assert _flags_without_incomplete(rows[95].lookback_flags) == {"missing_spread"}
        assert rows[95].lookback_flags <= {"missing_spread", "incomplete"}
        assert _flags_without_incomplete(rows[105].lookback_flags) == {"missing_spread", "ohlc_inconsistent"}
        assert rows[115].lookback_flags <= {"missing_spread", "ohlc_inconsistent", "incomplete"}
        assert _flags_without_incomplete(rows[115].lookback_flags) == {"missing_spread", "ohlc_inconsistent"}


def test_ac05_spread_unknown_inputs_reach_the_row_spread_and_median(monkeypatch):
    H001Params, indicators, Bar, AggregatedBar = _api(
        monkeypatch, "AC-05", "strategy.H001Params", "strategy.indicators", "core.Bar", "snapshot.AggregatedBar",
    )
    bars = _series(Bar, AggregatedBar, 230, changes={120: {"spread": None}})
    rows = indicators(bars, _params(H001Params))
    assert rows[120].spread is None
    assert all(type(rows[t].spread) is int and rows[t].spread == 240 for t in range(230) if t != 120)
    for t, row in enumerate(rows):
        if t < 96 or 121 <= t <= 216:
            assert row.spread_median_96 is None, t
        else:
            # The median of 96 spreads of 240 is (240 + 240) / 2 = 240; bar t is not in its window.
            assert type(row.spread_median_96) is Decimal and row.spread_median_96 == Decimal("240"), t


# Known answer: 106 bars of open 4000, high 4001, low 3999, close 4000, spread 240 (TR 2, ATR 2),
# then two breakouts. Parameters f 8, s 32, n 10, theta 0.50, N 48, M 24, k 2.0: warm from
# t = max(96, 49, 25, 97, 11) = 97 and L = 97 (bars t-96 .. t) in every variant.
# t = 96: close 4002 > HH_48 = 4001, but t < 97 -> skip (warmup).
# t = 97: close 4003 > HH_48 = 4002.50 (bar 96 is now inside); TR[96] = max(3, 2.5, 0.5) = 3 gives
#   ATR[96] = (2*9 + 3)/10 = 2.1; TR[97] = max(2, 1.5, 0.5) = 2 gives ATR[97] = (18.9 + 2)/10 = 2.09
#   -> enter_long with stop 2.0 * 2.09 = 4.18 in V-B and in V-C (both EMAs rose, TS > 0).
# t = 98..105: closes 4002 stay inside HH_48 = 4003.50 and LL_48 = 3999 -> none in V-B and V-C.
# V-A: TS = (EMA_8 - EMA_32) / ATR_10 rises while the slow EMA lags: about 0.154 (t = 96), 0.343,
#   0.400, 0.446, 0.477, 0.4951 (t = 101), 0.5041 (t = 102), 0.5056, 0.5013, 0.4925 (t = 105). It
#   crosses theta 0.50 only at t = 102, by a margin no rounding at the 28th digit can move (alpha
#   2/9 and 2/33 are the only inexact steps), so V-A enters long at t = 102 and nowhere else.
#   ATR[98..102] = (ATR * 9 + TR) / 10 with TR 2, 1.6, 1.6, 1.6, 1.6: 2.081, 2.0329, 1.98961,
#   1.950649, 1.9155841, so the stop is 2.0 * 1.9155841 = 3.8311682.
_KNOWN_CHANGES = {
    96: {"high": "4002.50", "low": "3999.50", "close": "4002.00"},
    97: {"open_": "4002.00", "high": "4003.50", "low": "4001.50", "close": "4003.00"},
    98: {"open_": "4003.00", "high": "4003.50", "low": "4001.50", "close": "4002.00"},
    **{t: {"open_": "4002.00", "high": "4002.80", "low": "4001.20", "close": "4002.00"} for t in range(99, 106)},
}
_KNOWN_START = datetime(2026, 3, 10, 12, 45, tzinfo=UTC)  # bar 97 opens 2026-03-11 13:00 UTC (09:00 EDT)
# (label, flags by bar, V-B and V-C decision at t = 96, at t = 97, V-A decision at t = 102)
_KNOWN_FLAGS = (
    ("no flag", {}, ("skip", ("warmup",)), ("enter_long", ()), ("enter_long", ())),
    ("incomplete alone on bars 1, 50, 96 and 97", {1: ("incomplete",), 50: ("incomplete",),
                                                   96: ("incomplete",), 97: ("incomplete",)},
     ("skip", ("warmup",)), ("enter_long", ()), ("enter_long", ())),
    ("missing_spread on bar 1 = t - L + 1 for t = 97", {1: ("missing_spread",)},
     ("skip", ("data_flag", "warmup")), ("skip", ("data_flag",)), ("enter_long", ())),
    ("missing_spread on bar 0 = t - L for t = 97", {0: ("missing_spread",)},
     ("skip", ("data_flag", "warmup")), ("enter_long", ()), ("enter_long", ())),
    ("unexpected_gap on bar 97 itself", {97: ("unexpected_gap",)},
     ("skip", ("warmup",)), ("skip", ("data_flag",)), ("skip", ("data_flag",))),
)


@pytest.mark.parametrize("case", _KNOWN_FLAGS, ids=[case[0] for case in _KNOWN_FLAGS])
def test_ac05_known_answer_series_enters_only_on_its_known_bar(monkeypatch, case):
    indicators, H001Params, Bar, AggregatedBar = _api(
        monkeypatch, "AC-05", "strategy.indicators", "strategy.H001Params", "core.Bar", "snapshot.AggregatedBar",
    )
    decide, _, _ = _decider(monkeypatch, "AC-05")
    label, flags, at_96, at_97, at_102 = case
    changes = {t: dict(values) for t, values in _KNOWN_CHANGES.items()}
    for t, codes in flags.items():
        changes.setdefault(t, {})["flags"] = codes
    bars = _series(Bar, AggregatedBar, 106, start="2026-03-10T12:45", changes=changes)
    for variant in ("A", "B", "C"):
        params = _params(H001Params, variant=variant, f=8, s=32, n=10, N=48, M=24)
        rows = indicators(bars, params)
        assert rows[97].atr == Decimal("2.09") and rows[97].hh_n == Decimal("4002.50"), label
        for t in range(106):
            next_open = _KNOWN_START + timedelta(minutes=15 * (t + 1))
            decision = decide(rows, t, "flat", next_open, params)
            if t < 96:
                assert decision.action in ("none", "skip"), (label, variant, t)
                assert decision.action == "none" or "warmup" in decision.reasons, (label, variant, t)
            elif variant == "A":
                if t == 102:
                    _expect(decision, at_102[0], at_102[1],
                            stop="3.8311682" if at_102[0] == "enter_long" else None, label=(label, variant, t))
                elif t >= 97:
                    _expect(decision, "none", label=(label, variant, t))
                else:
                    assert decision.action in ("none", "skip"), (label, variant, t)
            elif t == 96:
                _expect(decision, at_96[0], at_96[1], label=(label, variant, t))
            elif t == 97:
                _expect(decision, at_97[0], at_97[1], stop="4.18" if at_97[0] == "enter_long" else None,
                        label=(label, variant, t))
            else:
                _expect(decision, "none", label=(label, variant, t))


# ----------------------------------------------------------------------------------- AC-06

def _price(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def _random_bars(Bar, AggregatedBar, rng, count, start, base_cents):
    """A seeded random walk of M15 bars with missing spreads and flags (synthetic)."""
    first = datetime.fromisoformat(start)
    close = base_cents
    bars = []
    for t in range(count):
        open_ = close
        close = max(10_000, open_ + rng.randint(-300, 300))
        high = max(open_, close) + rng.randint(0, 150)
        low = min(open_, close) - rng.randint(0, 150)
        spread = None if rng.random() < 0.03 else rng.randint(150, 400)
        roll = rng.random()
        flags = ("incomplete",) if roll < 0.03 else (rng.choice(_DEFECT_CODES),) if roll < 0.035 else ()
        stamp = (first + timedelta(minutes=15 * t)).isoformat(timespec="minutes")
        bars.append(_bar(Bar, AggregatedBar, stamp, _price(open_), _price(high), _price(low), _price(close),
                         spread, flags))
    return tuple(bars)


def test_ac06_rows_and_decisions_at_t_ignore_every_bar_after_t(monkeypatch):
    indicators, H001Params, Bar, AggregatedBar = _api(
        monkeypatch, "AC-06", "strategy.indicators", "strategy.H001Params", "core.Bar", "snapshot.AggregatedBar",
    )
    decide, _, _ = _decider(monkeypatch, "AC-06")
    rng = random.Random(20261024)
    count = 240
    bars = _random_bars(Bar, AggregatedBar, rng, count, "2026-03-10T00:00", 400_000)
    checks = sorted({0, 1, 9, 10, 47, 48, 95, 96, 97, 98, 120, 191, 192, 193, 200, count - 1}
                    | {rng.randrange(count) for _ in range(6)})
    param_sets = [_params(H001Params, variant=variant) for variant in ("A", "B", "C")]
    param_sets += [_params(H001Params, variant=variant, f=8, s=32, n=10, theta=Decimal("0.25"), N=48, M=24,
                           k=Decimal("1.5")) for variant in ("A", "B", "C")]
    actions = set()
    for params in param_sets:
        full = indicators(bars, params)
        assert len(full) == count
        for t in checks:
            prefix = indicators(bars[:t + 1], params)
            assert prefix == full[:t + 1], (params.variant, t, "appending bars changed rows up to t")
            after = datetime.fromisoformat("2026-03-10T00:00") + timedelta(minutes=15 * (t + 1))
            tail = _random_bars(Bar, AggregatedBar, random.Random(t), 30, after.isoformat(timespec="minutes"),
                                500_000)
            changed = indicators(bars[:t + 1] + tail, params)
            assert changed[:t + 1] == full[:t + 1], (params.variant, t, "changing bars after t changed row t")
            for position in ("flat", "long", "short"):
                for next_open in (IN_WINDOW, OUT_OF_WINDOW):
                    decision = decide(full, t, position, next_open, params)
                    assert decide(prefix, t, position, next_open, params) == decision, (params.variant, t)
                    assert decide(changed, t, position, next_open, params) == decision, (params.variant, t)
                    if full[t].warm:
                        actions.add(decision.action)
    # The comparison above is not vacuous: on warm rows the random series reaches entries or skips,
    # exits, holds and bars without a signal.
    assert {"exit", "hold", "none"} <= actions and actions & {"enter_long", "enter_short", "skip"}, actions


def test_ac06_indicators_and_decide_are_deterministic_and_leave_inputs_untouched(monkeypatch):
    indicators, H001Params, Bar, AggregatedBar = _api(
        monkeypatch, "AC-06", "strategy.indicators", "strategy.H001Params", "core.Bar", "snapshot.AggregatedBar",
    )
    decide, _, _ = _decider(monkeypatch, "AC-06")
    bars = list(_random_bars(Bar, AggregatedBar, random.Random(7), 220, "2026-03-10T00:00", 400_000))
    before = [(id(item), item) for item in bars]
    params = _params(H001Params, variant="C")
    first = indicators(bars, params)
    second = indicators(bars, params)
    assert [(id(item), item) for item in bars] == before
    assert first == second and repr(first) == repr(second)
    rows = list(first)
    rows_before = [(id(item), item) for item in rows]
    for t in (0, 100, 196, 219):
        for position in ("flat", "long", "short"):
            one = decide(rows, t, position, IN_WINDOW, params)
            assert decide(rows, t, position, IN_WINDOW, params) == one
            assert decide(tuple(rows), t, position, IN_WINDOW, params) == one
    assert [(id(item), item) for item in rows] == rows_before
