"""Implementer unit tests for sochron.strategy (CORE-006). The locked acceptance and golden tests own the
contract; these pin what the implementer relied on: the 1 - alpha reading of the EMA rule, the O(n)
sliding windows against brute force, and speed on a realistic number of bars."""

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from time import perf_counter

from sochron.core import Bar
from sochron.data.snapshot import AggregatedBar
from sochron.strategy import H001Params, decide, indicators
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
