"""Implementer unit tests for sochron.core (CORE-005). The locked acceptance tests own the contract;
these cover what the implementer relied on."""

from datetime import UTC, datetime
from decimal import Decimal

from sochron import timebase
from sochron.core import TIMEFRAMES_MINUTES, Bar


def test_timeframes_repeat_the_timebase_set():
    # core may not import timebase (module map), so the set is repeated; this keeps the two equal.
    assert TIMEFRAMES_MINUTES == timebase.TIMEFRAMES_MINUTES


def test_an_aggregated_bar_may_count_more_m1_than_its_timeframe():
    # Contract v1.1: duplicate M1 (a STOP defect) make aggregate count more than the timeframe,
    # so m1_count has a lower bound only.
    bar = Bar(
        1773147600, datetime(2026, 3, 10, 13, 0, tzinfo=UTC), 15,
        Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"), None, 0, 16,
    )
    assert bar.m1_count == 16
