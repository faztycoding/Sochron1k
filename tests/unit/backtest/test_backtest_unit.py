"""Implementer unit tests for sochron.backtest (CORE-007). The locked acceptance and golden tests own the
contract; these pin what the implementer relied on: run's trades equal simulate_trade on random data
for every variant and side set, and run stays linear on a realistic number of bars."""

import random
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from time import perf_counter
from types import MappingProxyType

import pytest

from sochron.backtest import BacktestError, Rollover, SizedLots, run, simulate_trade
from sochron.core import Bar
from sochron.costs import H001_COSTS
from sochron.data.snapshot import H001_CLOSURES, AggregatedBar, ValidationReport, aggregate
from sochron.strategy import H001_DEFAULTS, H001Params
from sochron.timebase import bar_open, rule_for

RULE = rule_for("Exness-MT5Trial14")
ROLLOVER = Rollover("America/New_York", time(17, 0))
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _m1(count: int, seed: int, start: datetime = datetime(2026, 3, 2, tzinfo=UTC)) -> tuple[Bar, ...]:
    rng = random.Random(seed)
    price = Decimal("2600.000")
    bars = []
    for i in range(count):
        when = start + timedelta(minutes=i)
        step = Decimal(rng.randint(-60, 60)) / Decimal(100)
        open_, close = price, price + step
        high = max(open_, close) + Decimal(rng.randint(0, 30)) / Decimal(100)
        low = min(open_, close) - Decimal(rng.randint(0, 30)) / Decimal(100)
        spread = None if rng.random() < 0.002 else 200 + rng.randint(0, 80)
        bars.append(Bar((when - _EPOCH) // timedelta(seconds=1), when, 1, open_, high, low, close, spread, 10, 1))
        price = close
    return tuple(bars)


def _m15(m1: tuple[Bar, ...]):
    report = ValidationReport(defects=(), days=MappingProxyType({}), m1_bars=len(m1), calendar=H001_CLOSURES)
    return aggregate(m1, 15, RULE, report)


class _FixedSizer:
    def __init__(self, lots: str) -> None:
        self.lots = Decimal(lots)
        self.calls: list[tuple[Decimal, Decimal]] = []

    def __call__(self, equity: Decimal, stop_distance: Decimal) -> SizedLots:
        self.calls.append((equity, stop_distance))
        return SizedLots(self.lots, Decimal("25"), Decimal("24.5"), "fixed")


@pytest.mark.parametrize("variant", ["A", "B", "C"])
@pytest.mark.parametrize("sides", [frozenset({"long", "short"}), frozenset({"long"}), frozenset({"short"})],
                         ids=["both", "long", "short"])
def test_every_run_trade_equals_simulate_trade_on_random_data(variant, sides):
    # The invariant "every trade of run equals simulate_trade of the same entry and exit" on data the
    # golden scenarios do not cover: one random dataset of 20,000 consecutive M1 (each opening at the previous
    # close, so no price gaps or missing minutes) with missing spreads, in 9 variant/side configurations.
    m1 = _m1(20_000, seed=11)
    m15 = _m15(m1)
    params = H001Params(variant, 8, 32, 10, Decimal("0.50"), 48, 24, Decimal("2.0"))
    sizer = _FixedSizer("0.03")
    result = run(m1, m15, params, H001_COSTS, sizer, Decimal("10000"), RULE, ROLLOVER, sides=sides)
    assert result.trades, "fixture: the random walk must trade"
    index_of = {bar.time_raw: i for i, bar in enumerate(m1)}
    bar_of = {item.bar.time_raw: u for u, item in enumerate(m15)}
    equity = Decimal("10000")
    assert result.equity[0] == (m1[0].time_raw, equity)
    for k, trade in enumerate(result.trades):
        assert trade.side in sides
        entry = index_of[trade.entry_time_raw]
        exit_index = index_of[trade.exit_time_raw] if trade.exit_reason == "signal" or trade.ambiguous else None
        decision_bar = bar_of[bar_open(trade.entry_time_raw, 15, RULE)] - 1
        exit_bar = bar_of[bar_open(trade.exit_time_raw, 15, RULE)]
        flags = frozenset().union(*(m15[u].flags for u in range(decision_bar, exit_bar + 1)))
        again = simulate_trade(m1, entry, trade.side, trade.stop_distance, trade.lots, H001_COSTS, ROLLOVER,
                               risk_money=trade.risk_money, actual_risk=trade.actual_risk, exit_index=exit_index,
                               data_flags=flags)
        assert again == trade
        assert sizer.calls[k] == (equity, trade.stop_distance)
        equity += trade.net_money
        assert result.equity[k + 1] == (trade.exit_time_raw, equity)
        if k:
            assert result.trades[k - 1].exit_time_raw < trade.entry_time_raw


def test_one_hundred_thousand_m1_run_quickly():
    # Contract row "speed": 500,000 M1 within 60 s on the reference machine; a scratch script measured
    # 3.4-4.0 s per variant there (evidence). This smaller run keeps the suite fast; the bound is generous
    # for a slower CI runner while a quadratic regression (about 100,000 x the holding period) fails.
    m1 = _m1(100_000, seed=3)
    m15 = _m15(m1)
    began = perf_counter()
    result = run(m1, m15, H001_DEFAULTS["B"], H001_COSTS, _FixedSizer("0.02"), Decimal("10000"), RULE, ROLLOVER)
    assert perf_counter() - began < 30
    assert result.trades


def test_raw_time_outside_the_timebase_range_is_a_backtest_error():
    # Review CORE-007-r1 F1: a Bar accepts any int time_raw; run used to let timebase's RawTimeOutOfRange
    # through instead of refusing the bar as a BacktestError like any other time_utc/time_raw mismatch.
    m1 = _m1(60, seed=5)
    m15 = _m15(m1)
    sizer = _FixedSizer("0.02")
    bad_m1 = (replace(m1[0], time_raw=0),) + m1[1:]
    with pytest.raises(BacktestError):
        run(bad_m1, m15, H001_DEFAULTS["B"], H001_COSTS, sizer, Decimal("10000"), RULE, ROLLOVER)
    bad_m15 = (AggregatedBar(replace(m15[0].bar, time_raw=0), m15[0].flags),) + tuple(m15[1:])
    with pytest.raises(BacktestError):
        run(m1, bad_m15, H001_DEFAULTS["B"], H001_COSTS, sizer, Decimal("10000"), RULE, ROLLOVER)


@pytest.mark.parametrize("side", ["long", "short"])
def test_a_stop_distance_too_large_for_the_arithmetic_is_a_backtest_error(side):
    # Review CORE-007-r1 F2: a finite stop_distance of 1E+1000000 overflowed costs.CONTEXT (Emax 999999)
    # and raised decimal.Overflow, which is not a ValueError.
    m1 = _m1(10, seed=5)
    with pytest.raises(BacktestError):
        simulate_trade(m1, 0, side, Decimal("1E+1000000"), Decimal("0.10"), H001_COSTS, ROLLOVER,
                       risk_money=Decimal("25"), exit_index=4)


def _scenario_stop_in_the_last_minute() -> tuple[tuple[Bar, ...], tuple[AggregatedBar, ...]]:
    """Flat bars from Sunday 2026-03-08 22:00 UTC (the open after the weekend, the daily break of Monday
    21:00-21:59 UTC left out), a V-B breakout in bar D = 155 (13:45 UTC on Tuesday), the long's stop touched
    only in the last minute of bar D+1 and bar D+2 opening below the stop with an unexpected_gap flag."""
    start = datetime(2026, 3, 8, 22, 0, tzinfo=UTC)
    flat = ("2000.00", "2000.50", "1999.50", "2000.00")
    rows = []
    when = start
    while when < datetime(2026, 3, 10, 14, 30, tzinfo=UTC):
        if not (datetime(2026, 3, 9, 21, 0, tzinfo=UTC) <= when < datetime(2026, 3, 9, 22, 0, tzinfo=UTC)):
            prices = flat
            if when == datetime(2026, 3, 10, 13, 59, tzinfo=UTC):
                prices = ("2000.00", "2003.20", "1999.50", "2003.00")  # bar D closes above HH_48 = 2000.50
            elif datetime(2026, 3, 10, 14, 0, tzinfo=UTC) <= when < datetime(2026, 3, 10, 14, 14, tzinfo=UTC):
                prices = ("2003.00", "2003.50", "2002.50", "2003.00")  # bar D+1, minutes 0-13: above the stop
            elif when == datetime(2026, 3, 10, 14, 14, tzinfo=UTC):
                prices = ("2003.00", "2003.50", "1999.00", "2002.00")  # bar D+1, minute 14: low under the stop
            elif when >= datetime(2026, 3, 10, 14, 15, tzinfo=UTC):
                prices = ("1999.20", "1999.40", "1999.00", "1999.20")  # bar D+2 opens under the stop
            o, h, l, c = (Decimal(p) for p in prices)
            rows.append(Bar((when - _EPOCH) // timedelta(seconds=1), when, 1, o, h, l, c, 200, 10, 1))
        when += timedelta(minutes=1)
    m1 = tuple(rows)
    m15 = list(_m15(m1))
    assert len(m15) == 158 and m15[156].bar.time_utc == datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    assert all(not item.flags for item in m15), "fixture: every bar complete"
    m15[157] = AggregatedBar(m15[157].bar, frozenset({"unexpected_gap"}))
    return m1, tuple(m15)


def test_a_stop_in_the_last_minute_of_a_bar_closes_in_that_bar():
    # Review CORE-007-r1 F3: contract step 1 checks the stop on every M1 of bar t, the last one included.
    # A scan that skipped the last minute would keep the long open through bar D+1 and close it in D+2,
    # so data_flags would wrongly carry bar D+2's unexpected_gap (the fill itself is found again from the
    # entry M1 and would not change).
    m1, m15 = _scenario_stop_in_the_last_minute()
    params = H001Params("B", 8, 32, 10, Decimal("0.50"), 48, 24, Decimal("3.0"))
    sizer = _FixedSizer("0.02")
    result = run(m1, m15, params, H001_COSTS, sizer, Decimal("10000"), RULE, ROLLOVER)
    assert sizer.calls == [(Decimal("10000"), Decimal("3.810"))]  # k 3.0 x ATR 1.27 at bar D
    (trade,) = result.trades
    assert (trade.side, trade.exit_reason, trade.stop_price, trade.exit_bid) == (
        "long", "stop", Decimal("1999.390"), Decimal("1999.390"))
    assert trade.entry_time_raw == m15[156].bar.time_raw
    assert trade.exit_time_raw == m15[156].bar.time_raw + 14 * 60
    assert trade.data_flags == frozenset()


def test_m15_prices_too_large_for_the_strategy_arithmetic_are_a_backtest_error():
    # Review CORE-007-r2 F5: run passes M15 bars to strategy.indicators, whose ATR sum overflows the Decimal
    # context when M15 highs sit near the top of its range; that must surface as a BacktestError as well.
    m1 = _m1(3_000, seed=11)
    m15 = list(_m15(m1))
    for t in range(40):
        m15[t] = AggregatedBar(replace(m15[t].bar, high=Decimal("9E+999999")), m15[t].flags)
    with pytest.raises(BacktestError):
        run(m1, tuple(m15), H001_DEFAULTS["B"], H001_COSTS, _FixedSizer("0.02"), Decimal("10000"), RULE, ROLLOVER)


def test_a_starting_equity_too_large_for_the_arithmetic_is_a_backtest_error():
    # Review CORE-007-r1 F2 (same arithmetic in run): the equity update after a close overflows when the
    # starting equity sits at the top of the context's range; it must surface as a BacktestError too.
    m1 = _m1(20_000, seed=11)
    m15 = _m15(m1)
    params = H001Params("B", 8, 32, 10, Decimal("0.50"), 48, 24, Decimal("2.0"))
    with pytest.raises(BacktestError):
        run(m1, m15, params, H001_COSTS, _FixedSizer("0.03"), Decimal("9.9999999999999999999999999999E+999999"),
            RULE, ROLLOVER)
