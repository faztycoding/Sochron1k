"""Typed refusals of the time module (CORE-001). Every one is a ValueError."""


class TimebaseError(ValueError):
    """Base class: timebase refuses instead of guessing."""


class UnknownTimeRule(TimebaseError):
    """No measured rule exists for this server; no default offset is assumed."""


class NaiveDatetime(TimebaseError):
    """A datetime without a UTC offset was given; timebase only accepts aware datetimes."""


class RawTimeOutOfRange(TimebaseError):
    """A raw MT5 time lies outside [2000-01-01, 2100-01-01) UTC seconds."""


class RawTimeMismatch(TimebaseError):
    """The millisecond time does not belong to the given second."""


class BadTimeframe(TimebaseError):
    """The timeframe is not one of TIMEFRAMES_MINUTES."""
