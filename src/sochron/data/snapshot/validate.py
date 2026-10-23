"""validate_m1: report every defect of an M1 series without repairing anything (CORE-005 AC-03 to AC-05).

Conventions (docs/contracts/CORE-005-data-bars.md and the locked tests):
- The previous bar is the one just before in input order: an equal time is duplicate_time, a
  smaller one time_not_increasing.
- A gap is the minutes missing between two increasing bars; minutes inside a closure of the
  calendar do not count, and more than max_gap_minutes in-session minutes is unexpected_gap,
  reported at the first bar after the gap.
- Days are UTC dates under the rule (timebase.to_utc of the raw time). A Monday-Friday date with
  no bar strictly inside the span of the input is empty_weekday (UNKNOWN, no time).
- One defect per (bar, code). The input is never changed.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from types import MappingProxyType

from sochron.core import Bar
from sochron.timebase import TimeRule, to_utc, to_zone

from .model import ClosureCalendar, Defect, Severity, ValidationReport, exact

_RANK: dict[str, int] = {"PASS": 0, "WARN": 1, "UNKNOWN": 2, "STOP": 3}
_MINUTE = 60
_WEEK_MINUTES = 7 * 24 * 60


def require_bars(bars: object) -> tuple[Bar, ...]:
    """A sequence of exactly Bar (no subclass), as a tuple; the caller's object is not changed."""
    if not isinstance(bars, Sequence) or isinstance(bars, (str, bytes)):
        raise TypeError(f"bars must be a sequence of Bar, not {type(bars).__name__}")
    items = tuple(bars)
    for item in items:
        exact(item, Bar, "every bar")
        if item.timeframe != 1:
            raise ValueError("bars must be M1 (timeframe 1)")
    return items


def _minute_of_week(local: datetime) -> int:
    return local.weekday() * 24 * 60 + local.hour * 60 + local.minute


def _within(value: int, start: int, end: int) -> bool:
    """value in [start, end) on a circle; start == end is an empty window."""
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def _clock_minutes(at: time) -> int:
    return at.hour * 60 + at.minute


def in_closure(utc: datetime, calendar: ClosureCalendar) -> bool:
    """Whether a UTC instant falls in the daily break or the weekend of the calendar."""
    local = to_zone(utc, calendar.zone)
    minute_of_day = local.hour * 60 + local.minute
    start, end = calendar.daily_break
    if _within(minute_of_day, _clock_minutes(start), _clock_minutes(end)):
        return True
    (start_day, start_at), (end_day, end_at) = calendar.weekend
    begin = start_day * 24 * 60 + _clock_minutes(start_at)
    finish = end_day * 24 * 60 + _clock_minutes(end_at)
    return _within(_minute_of_week(local) % _WEEK_MINUTES, begin, finish)


def in_session_missing(after_utc: datetime, before_utc: datetime, calendar: ClosureCalendar, limit: int) -> int:
    """In-session minute starts strictly between two instants, counted up to limit + 1."""
    first = after_utc.replace(second=0, microsecond=0) + timedelta(minutes=1)
    count = 0
    minute = first
    while minute < before_utc:
        if not in_closure(minute, calendar):
            count += 1
            if count > limit:
                return count
        minute += timedelta(minutes=1)
    return count


def _bar_defects(bar: Bar, utc: datetime) -> list[tuple[str, Severity, str]]:
    found: list[tuple[str, Severity, str]] = []
    if utc.second or utc.microsecond:
        found.append(("not_minute_aligned", "STOP", "the open time is not on a whole minute"))
    if bar.time_utc != utc:
        found.append(("time_rule_mismatch", "STOP", "time_utc differs from timebase.to_utc(time_raw, rule)"))
    prices = (bar.open, bar.high, bar.low, bar.close)
    if bar.high < bar.low or not bar.low <= bar.open <= bar.high or not bar.low <= bar.close <= bar.high:
        found.append(("ohlc_inconsistent", "STOP", "high below low, or open or close outside [low, high]"))
    if any(price <= 0 for price in prices):
        found.append(("non_positive_price", "STOP", "a price is zero or negative"))
    if bar.spread is None:
        found.append(("missing_spread", "WARN", "the bar carries no spread; costs use the fallback"))
    elif bar.spread < 0:
        found.append(("negative_spread", "STOP", "the spread is negative"))
    return found


def validate_m1(bars: Sequence[Bar], rule: TimeRule, calendar: ClosureCalendar, max_gap_minutes: int) -> ValidationReport:
    """Every defect of an M1 series and the status of each UTC day; nothing is repaired."""
    items = require_bars(bars)
    exact(rule, TimeRule, "rule")
    exact(calendar, ClosureCalendar, "calendar")
    exact(max_gap_minutes, int, "max_gap_minutes")
    if max_gap_minutes < 0:
        raise ValueError("max_gap_minutes cannot be negative")

    defects: list[Defect] = []
    days: dict[date, str] = {}
    previous: tuple[int, datetime] | None = None
    for bar in items:
        utc = to_utc(bar.time_raw, rule)
        day = utc.date()
        days.setdefault(day, "PASS")
        found = _bar_defects(bar, utc)
        if previous is not None:
            previous_raw, previous_utc = previous
            if bar.time_raw == previous_raw:
                found.append(("duplicate_time", "STOP", "the same open time as the bar before"))
            elif bar.time_raw < previous_raw:
                found.append(("time_not_increasing", "STOP", "an open time before the bar before"))
            else:
                missing = in_session_missing(previous_utc, utc, calendar, max_gap_minutes)
                if missing > max_gap_minutes:
                    found.append(
                        ("unexpected_gap", "WARN", f"more than {max_gap_minutes} in-session minutes missing before this bar")
                    )
        for code, severity, detail in found:
            defects.append(Defect(code, severity, bar.time_raw, detail))
            if _RANK[severity] > _RANK[days[day]]:
                days[day] = severity
        previous = (bar.time_raw, utc)

    if days:
        first, last = min(days), max(days)
        current = first + timedelta(days=1)
        while current < last:
            if current.weekday() < 5 and current not in days:
                defects.append(Defect("empty_weekday", "UNKNOWN", None, f"no bar on {current.isoformat()}"))
                days[current] = "UNKNOWN"
            current += timedelta(days=1)

    ordered = {day: days[day] for day in sorted(days)}
    return ValidationReport(tuple(defects), MappingProxyType(ordered), len(items), calendar)
