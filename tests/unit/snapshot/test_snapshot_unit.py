"""Implementer unit tests for sochron.data.snapshot (CORE-005). The locked acceptance and golden tests
own the contract; these cover the helpers and decisions the implementer relied on."""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from time import perf_counter

import pytest

from sochron.core import Bar
from sochron.data.snapshot import H001_CLOSURES, ClosureCalendar, aggregate, validate_m1
from sochron.data.snapshot.validate import in_closure, in_session_missing
from sochron.timebase import rule_for, to_utc

RULE = rule_for("Exness-MT5Trial14")


def _bar(when: datetime) -> Bar:
    raw = int(when.timestamp())
    price = Decimal("2000.000")
    return Bar(raw, to_utc(raw, RULE), 1, price, price, price, price, 240, 1, 1)


@pytest.mark.parametrize(
    ("utc", "closed"),
    [
        (datetime(2026, 3, 9, 20, 59, tzinfo=UTC), False),  # 16:59 EDT
        (datetime(2026, 3, 9, 21, 0, tzinfo=UTC), True),  # 17:00 EDT
        (datetime(2026, 3, 9, 21, 59, tzinfo=UTC), True),  # 17:59 EDT
        (datetime(2026, 3, 9, 22, 0, tzinfo=UTC), False),  # 18:00 EDT
        (datetime(2026, 3, 5, 22, 0, tzinfo=UTC), True),  # 17:00 EST, before the March change
        (datetime(2026, 3, 7, 12, 0, tzinfo=UTC), True),  # Saturday
        (datetime(2026, 3, 8, 21, 59, tzinfo=UTC), True),  # Sunday 17:59 EDT
        (datetime(2026, 3, 8, 22, 0, tzinfo=UTC), False),  # Sunday 18:00 EDT, the week opens
    ],
)
def test_in_closure_follows_new_york_wall_time(utc, closed):
    assert in_closure(utc, H001_CLOSURES) is closed


def test_in_session_missing_stops_counting_after_the_limit():
    # The count is only compared with the limit, so a long gap stops at limit + 1 minutes.
    start = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    assert in_session_missing(start, start + timedelta(hours=3), H001_CLOSURES, 5) == 6
    assert in_session_missing(start, start + timedelta(minutes=4), H001_CLOSURES, 5) == 3


def test_a_calendar_with_an_unknown_zone_is_refused_at_construction():
    # Fail fast: the zone is resolved through timebase when the calendar is built.
    with pytest.raises(KeyError):
        replace(H001_CLOSURES, zone="Not/AZone")


def test_a_wrapped_daily_break_crosses_midnight():
    calendar = ClosureCalendar(
        zone="UTC", daily_break=(time(23, 30), time(0, 30)), weekend=H001_CLOSURES.weekend, provenance="test"
    )
    assert in_closure(datetime(2026, 3, 10, 23, 45, tzinfo=UTC), calendar)
    assert in_closure(datetime(2026, 3, 11, 0, 15, tzinfo=UTC), calendar)
    assert not in_closure(datetime(2026, 3, 11, 0, 30, tzinfo=UTC), calendar)


def test_aggregate_refuses_a_report_made_for_other_bars():
    bars = [_bar(datetime(2026, 3, 10, 13, minute, tzinfo=UTC)) for minute in range(3)]
    report = validate_m1(bars[:2], RULE, H001_CLOSURES, 5)
    with pytest.raises(ValueError):
        aggregate(bars, 15, RULE, report)


def test_fifty_thousand_m1_validate_and_aggregate_quickly():
    # Contract plan: real 2018-2024 data is about 2.5 million M1. 500,000 synthetic bars took about
    # 3.1 s to validate and 0.9 s to aggregate on the reference machine; this smaller run keeps a
    # generous bound so a slower CI runner still passes while a quadratic regression fails.
    start = datetime(2026, 3, 9, 0, 0, tzinfo=UTC)
    bars = [_bar(start + timedelta(minutes=step)) for step in range(50_000) if not in_closure(start + timedelta(minutes=step), H001_CLOSURES)]
    began = perf_counter()
    report = validate_m1(bars, RULE, H001_CLOSURES, 5)
    result = aggregate(bars, 15, RULE, report)
    elapsed = perf_counter() - began
    assert report.defects == ()
    assert sum(item.bar.m1_count for item in result) == len(bars)
    assert elapsed < 30
