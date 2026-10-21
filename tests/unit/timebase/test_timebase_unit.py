"""Implementer unit tests for sochron.timebase (CORE-001). The locked acceptance and golden
tests own the contract; these cover edges and internals the implementer relied on."""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from sochron.timebase import (
    RULES,
    TIMEFRAMES_MINUTES,
    EntryWindow,
    OffsetClass,
    RawTimeOutOfRange,
    bar_open,
    bangkok_date,
    check_aware,
    classify_offset,
    in_entry_window,
    rule_for,
    to_raw,
    to_utc,
    to_zone,
)

RULE = rule_for("Exness-MT5Trial14")


def test_rules_mapping_is_read_only():
    with pytest.raises(TypeError):
        RULES["Other-Server"] = RULE  # type: ignore[index]


def test_to_utc_uses_integer_arithmetic_at_both_range_ends():
    assert to_utc(946_684_800, RULE) == datetime(2000, 1, 1, tzinfo=UTC)
    assert to_utc(4_102_444_799, RULE) == datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_to_utc_rejects_non_integer_raw_and_msc():
    with pytest.raises(TypeError):
        to_utc(1792525992.0, RULE)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_utc(True, RULE)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_utc(1792525992, RULE, msc=1792525992035.0)  # type: ignore[arg-type]


def test_to_raw_floors_fractions_and_accepts_any_aware_zone():
    bangkok = datetime(2026, 10, 21, 2, 53, 12, 999_999, tzinfo=ZoneInfo("Asia/Bangkok"))
    assert to_raw(bangkok, RULE) == 1792525992
    assert to_raw(bangkok.astimezone(UTC), RULE) == 1792525992


def test_to_raw_applies_the_rule_offset_and_checks_the_result_range():
    shifted = replace(RULE, offset_seconds=7200)
    instant = datetime(2026, 10, 20, 17, 53, 12, tzinfo=UTC)
    assert to_raw(instant, shifted) == 1792525992
    with pytest.raises(RawTimeOutOfRange):
        to_raw(datetime(2099, 12, 31, 23, 0, tzinfo=UTC), shifted)


def test_bar_open_is_idempotent_and_never_after_the_input():
    for timeframe in sorted(TIMEFRAMES_MINUTES):
        raw = 1792525992
        opened = bar_open(raw, timeframe, RULE)
        assert opened <= raw
        assert raw - opened < timeframe * 60
        assert bar_open(opened, timeframe, RULE) == opened


def test_bar_open_honours_a_nonzero_rule_offset_for_the_daily_bar():
    shifted = replace(RULE, offset_seconds=3600)
    # 2026-10-20 00:00 UTC is raw 1792454400 + 3600 under a +1 h rule.
    assert bar_open(1792525992, 1440, shifted) == 1792454400 + 3600


def test_entry_window_minute_precision_and_dst_shift():
    inside_est = datetime(2026, 3, 7, 8, 0, 59, tzinfo=UTC)  # 03:00:59 EST
    outside_est = datetime(2026, 3, 7, 7, 59, 59, tzinfo=UTC)  # 02:59:59 EST
    assert in_entry_window(inside_est) is True
    assert in_entry_window(outside_est) is False
    # After the spring change the same UTC minute is one hour later in New York.
    assert in_entry_window(datetime(2026, 3, 9, 7, 59, 59, tzinfo=UTC)) is True  # 03:59:59 EDT


def test_entry_window_in_another_zone():
    window = EntryWindow("Asia/Bangkok", time(9, 0), time(17, 0))
    assert in_entry_window(datetime(2026, 10, 21, 2, 0, tzinfo=UTC), window) is True
    assert in_entry_window(datetime(2026, 10, 21, 10, 1, tzinfo=UTC), window) is False


def test_bangkok_date_and_to_zone_agree():
    instant = datetime(2026, 10, 20, 17, 0, tzinfo=UTC)
    assert to_zone(instant, "Asia/Bangkok").utcoffset() == timedelta(hours=7)
    assert bangkok_date(instant) == to_zone(instant, "Asia/Bangkok").date()


def test_check_aware_accepts_fixed_offsets_and_rejects_naive():
    assert check_aware(datetime(2026, 1, 1, tzinfo=UTC)).tzinfo is UTC
    with pytest.raises(ValueError):
        check_aware(datetime(2026, 1, 1))


def test_classify_offset_examples_from_spike_001():
    assert classify_offset([-0.246, 0.268, 0.306]) == OffsetClass("ok", None, 3)
    assert classify_offset([0.735, 0.865, -3.8]).kind == "ok"
    assert classify_offset([3599.0, 3601.0]) == OffsetClass("shifted", 1, 2)
    assert classify_offset([3599.0, -3601.0]).kind == "unknown"


def test_classify_offset_finds_the_common_hour_at_a_wide_tolerance():
    # Review r1 F1: 1800 and 5400 are each exactly 1800 s from +1 h, so the contract's common
    # hour is 1; rounding each sample on its own gave 0 h and 2 h and answered unknown.
    assert classify_offset([1800.0, 5400.0], 1800.0) == OffsetClass("shifted", 1, 2)
    assert classify_offset([-1800.0, -5400.0], 1800.0) == OffsetClass("shifted", -1, 2)
    # 1800 fits 0 h or +1 h and 9000 fits +2 h or +3 h: no hour fits both.
    assert classify_offset([1800.0, 9000.0], 1800.0) == OffsetClass("unknown", None, 2)
    # 5400 alone fits +1 h and +2 h equally well: ambiguous evidence stays unknown, never a guess.
    assert classify_offset([5400.0], 1800.0) == OffsetClass("unknown", None, 1)
