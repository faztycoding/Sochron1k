"""Implementer unit tests for sochron.strategy (CORE-006). The locked acceptance and golden tests own the
contract; these pin what the implementer relied on: the 1 - alpha reading of the EMA rule, the O(n)
sliding windows against brute force, and speed on a realistic number of bars."""

import importlib
import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from time import perf_counter

import pytest

from sochron.core import Bar
from sochron.data.snapshot import AggregatedBar
from sochron.strategy import H001Params, IndicatorRow, StrategyError, decide, indicators
from sochron.strategy.params import CONTEXT


def _series(count: int, seed: int, flag_every: int = 0, gap_spread_every: int = 0) -> list[AggregatedBar]:
    rng = random.Random(seed)
    start = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)
    price = Decimal("2000.000")
    bars = []
    for index in range(count):
        when = start + timedelta(minutes=15 * index)
        step = Decimal(rng.randint(-250, 250)) / Decimal(100)
        open_, close = price, price + step
        high = max(open_, close) + Decimal(rng.randint(0, 80)) / Decimal(100)
        low = min(open_, close) - Decimal(rng.randint(0, 80)) / Decimal(100)
        spread = None if gap_spread_every and index % gap_spread_every == 7 else 200 + rng.randint(0, 90)
        flags = frozenset({"unexpected_gap"}) if flag_every and index % flag_every == 3 else frozenset()
        if index % 11 == 5:
            flags = flags | {"incomplete"}
        bar = Bar(int(when.timestamp()), when, 15, open_, high, low, close, spread, 100, 15)
        bars.append(AggregatedBar(bar, flags))
        price = close
    return bars


def test_one_minus_alpha_is_computed_from_the_rounded_alpha():
    # Review CORE-006-tests-r2 F6: at s = 62, 1 - alpha differs from (s - 1)/(s + 1) in the last digit,
    # and contract v1.1 item 1 computes it from alpha. This pins that reading.
    params = H001Params("B", 16, 62, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    bars = _series(30, 7)
    rows = indicators(bars, params)
    with localcontext(CONTEXT):
        alpha = Decimal(2) / Decimal(63)
        keep = Decimal(1) - alpha
        other = Decimal(61) / Decimal(63)
        assert keep != other
        expected = rival = bars[0].bar.close
        for t, item in enumerate(bars):
            if t:
                expected = alpha * item.bar.close + keep * expected
                rival = alpha * item.bar.close + other * rival
            assert rows[t].ema_s == expected
        assert expected != rival


def test_fast_and_slow_ema_use_one_minus_the_rounded_alpha():
    # Review CORE-006-r1 F4: the s = 62 case above guards the slow EMA only. f = 22 is the one fast period
    # where 1 - alpha and (f - 1)/(f + 1) differ in the 28th digit (s = 78 is another slow one).
    params = H001Params("B", 22, 78, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    bars = _series(40, 7)
    rows = indicators(bars, params)
    for period, field in ((22, "ema_f"), (78, "ema_s")):
        with localcontext(CONTEXT):
            alpha = Decimal(2) / Decimal(period + 1)
            keep = Decimal(1) - alpha
            other = Decimal(period - 1) / Decimal(period + 1)
            assert keep != other
            expected = rival = bars[0].bar.close
            for t, item in enumerate(bars):
                if t:
                    expected = alpha * item.bar.close + keep * expected
                    rival = alpha * item.bar.close + other * rival
                assert getattr(rows[t], field) == expected
            assert expected != rival


def test_sliding_windows_equal_brute_force():
    params = H001Params("B", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    bars = _series(700, 11, flag_every=97, gap_spread_every=150)
    rows = indicators(bars, params)
    span = max(params.n, 96, params.N, params.M) + 1
    for t, row in enumerate(rows):
        highs = [b.bar.high for b in bars]
        lows = [b.bar.low for b in bars]
        assert row.hh_n == (max(highs[t - params.N:t]) if t >= params.N else None)
        assert row.ll_n == (min(lows[t - params.N:t]) if t >= params.N else None)
        assert row.hh_m == (max(highs[t - params.M:t]) if t >= params.M else None)
        assert row.ll_m == (min(lows[t - params.M:t]) if t >= params.M else None)
        window = [b.bar.spread for b in bars[t - 96:t]] if t >= 96 else None
        if window is None or None in window:
            assert row.spread_median_96 is None
        else:
            ordered = sorted(window)
            with localcontext(CONTEXT):
                assert row.spread_median_96 == (Decimal(ordered[47]) + Decimal(ordered[48])) / Decimal(2)
        expected_flags = set()
        for item in bars[max(0, t - span + 1):t + 1]:
            expected_flags |= item.flags
        assert row.lookback_flags == frozenset(expected_flags - {"incomplete"})


def test_sixty_thousand_bars_run_quickly():
    # Contract plan: about 170,000 M15 bars per run in Decimal must finish in seconds. 170,000 bars took
    # 1.2 s (indicators) + 0.35 s (decide) from a scratch script and 4.1 s inside pytest on the reference
    # machine (evidence). This smaller run keeps the suite fast; the bound is generous so a slower CI
    # runner still passes while a quadratic regression (about 60,000 x the window) fails.
    params = H001Params("C", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    bars = _series(60_000, 3)
    began = perf_counter()
    rows = indicators(bars, params)
    for t in range(len(rows) - 1):
        decide(rows, t, "flat", bars[t + 1].bar.time_utc, params)
    assert perf_counter() - began < 30


def _row(ts: Decimal | None, hh_n: Decimal | None = None) -> IndicatorRow:
    """A warm row that passes every invalidation check, with the given trend score and entry channel."""
    price = Decimal("2000.00")
    return IndicatorRow(price, price, Decimal("4.00"), ts, hh_n, None, None, None, price, 200, Decimal(200), True,
                        frozenset())


IN_WINDOW = datetime(2026, 3, 10, 14, 0, tzinfo=UTC)  # 10:00 New York (EDT), inside the entry window


def test_variant_a_short_threshold_mirrors_the_long_one_at_every_digit():
    # Review CORE-006-r1 F1: H001Params accepts a theta with more than 28 significant digits; the short
    # rule must compare against exactly -theta (D5), not -theta rounded to the module precision.
    theta = Decimal("0.25000000000000000000000000006")
    params = H001Params("A", 16, 64, 20, theta, 96, 48, Decimal("2.0"))
    above = Decimal("0.2500000000000000000000000001")
    long_rows = (_row(Decimal("0.25")), _row(above))
    short_rows = (_row(Decimal("-0.25")), _row(Decimal("-0.2500000000000000000000000001")))
    assert decide(long_rows, 1, "flat", IN_WINDOW, params).action == "enter_long"
    assert decide(short_rows, 1, "flat", IN_WINDOW, params).action == "enter_short"


@pytest.mark.parametrize("position", ["flat", "long", "short"])
@pytest.mark.parametrize("breakout", [False, True], ids=["no_signal", "breakout"])
def test_naive_next_open_is_refused_for_every_position(position, breakout):
    # Review CORE-006-r1 F2: a naive next_open_utc used to surface only on a flat bar with an entry signal,
    # and then as timebase's NaiveDatetime. It is now refused up front as a StrategyError.
    params = H001Params("B", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    rows = (_row(None), _row(None, hh_n=Decimal("1999.00") if breakout else None))
    with pytest.raises(StrategyError, match="timezone"):
        decide(rows, 1, position, datetime(2026, 3, 10, 13, 45), params)


def test_flag_counter_drops_flags_that_left_the_lookback(monkeypatch):
    # Review CORE-006-r1 F3: flags whose count fell to zero stayed in the Counter, and every row walked every
    # key ever seen, so a flag vocabulary that grows with the series made indicators() quadratic. Counting
    # keys (not timing) keeps this check deterministic on any runner.
    sizes = []

    class SizedCounter(Counter):
        def update(self, *args, **kwargs):
            super().update(*args, **kwargs)
            sizes.append(len(self))

    monkeypatch.setattr(importlib.import_module("sochron.strategy.indicators"), "Counter", SizedCounter)
    params = H001Params("A", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    span = max(params.n, 96) + 1
    bars = [AggregatedBar(item.bar, frozenset({f"defect_{t}"})) for t, item in enumerate(_series(600, 13))]
    rows = indicators(bars, params)
    assert len(sizes) > len(bars)
    assert max(sizes) <= span + 1  # bar t joins before bar t - span leaves (600 before the fix)
    for t, row in enumerate(rows):
        assert row.lookback_flags == frozenset(f"defect_{i}" for i in range(max(0, t - span + 1), t + 1))
