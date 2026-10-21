"""Raw MT5 time <-> UTC under a TimeRule, zone conversion and bar alignment.

Pure functions: integer arithmetic on seconds, aware datetimes only, no clock, no I/O.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .errors import BadTimeframe, NaiveDatetime, RawTimeMismatch, RawTimeOutOfRange
from .rules import TimeRule

RAW_MIN = 946_684_800  # 2000-01-01T00:00:00Z
RAW_MAX_EXCLUSIVE = 4_102_444_800  # 2100-01-01T00:00:00Z
TIMEFRAMES_MINUTES = frozenset(
    {1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720, 1440}
)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_ONE_SECOND = timedelta(seconds=1)


def _check_raw(raw_seconds: int) -> int:
    if isinstance(raw_seconds, bool) or not isinstance(raw_seconds, int):
        raise TypeError(f"raw MT5 time must be an int of seconds, got {type(raw_seconds).__name__}")
    if not RAW_MIN <= raw_seconds < RAW_MAX_EXCLUSIVE:
        raise RawTimeOutOfRange(
            f"raw MT5 time {raw_seconds} is outside [{RAW_MIN}, {RAW_MAX_EXCLUSIVE})"
        )
    return raw_seconds


def check_aware(dt: datetime) -> datetime:
    """Return dt when it carries a UTC offset; refuse naive datetimes."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise NaiveDatetime("timebase only accepts timezone-aware datetimes")
    return dt


def to_utc(raw_seconds: int, rule: TimeRule, msc: int | None = None) -> datetime:
    """UTC instant of a raw MT5 time under the rule; msc supplies the millisecond part."""
    _check_raw(raw_seconds)
    microsecond = 0
    if msc is not None:
        if isinstance(msc, bool) or not isinstance(msc, int):
            raise TypeError(f"msc must be an int of milliseconds, got {type(msc).__name__}")
        if msc // 1000 != raw_seconds:
            raise RawTimeMismatch(f"msc {msc} does not belong to second {raw_seconds}")
        microsecond = (msc - raw_seconds * 1000) * 1000
    utc_seconds = raw_seconds - rule.offset_seconds
    return (_EPOCH + timedelta(seconds=utc_seconds)).replace(microsecond=microsecond)


def to_raw(dt: datetime, rule: TimeRule) -> int:
    """Raw MT5 seconds of an aware instant under the rule; the fraction of a second is dropped."""
    utc_seconds = (check_aware(dt) - _EPOCH) // _ONE_SECOND
    return _check_raw(utc_seconds + rule.offset_seconds)


def to_zone(dt: datetime, zone: str) -> datetime:
    """The same instant as wall time in an IANA zone such as America/New_York."""
    return check_aware(dt).astimezone(ZoneInfo(zone))


def bar_open(raw_seconds: int, timeframe_minutes: int, rule: TimeRule) -> int:
    """Raw time of the open of the bar that contains raw_seconds.

    Bars align to UTC boundaries under the rule (MT5 aligns them to server time, which the
    rule maps to UTC), so the floor is taken on UTC seconds and the offset is put back.
    """
    _check_raw(raw_seconds)
    if isinstance(timeframe_minutes, bool) or timeframe_minutes not in TIMEFRAMES_MINUTES:
        raise BadTimeframe(
            f"timeframe {timeframe_minutes!r} minutes is not supported; "
            f"use one of {sorted(TIMEFRAMES_MINUTES)}"
        )
    utc_seconds = raw_seconds - rule.offset_seconds
    span = timeframe_minutes * 60
    return utc_seconds - utc_seconds % span + rule.offset_seconds
