"""Shared value types (docs/architecture.md section 8, row core): no I/O, no clock, no imports from sochron.

Bar is one OHLC bar as MT5 reports it (bid prices), keeping the raw MT5 time next to its UTC time
(AGENTS.md "Store UTC plus the raw MT5 timestamp"). Construction checks types, finiteness, a UTC
time_utc and the few values only a bug can produce (docs/contracts/CORE-005-data-bars.md v1.1);
an inconsistent price or spread must still be representable so that sochron.data.snapshot can
report it instead of losing it.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

__all__ = ["TIMEFRAMES_MINUTES", "Bar"]

# The same set as sochron.timebase.TIMEFRAMES_MINUTES (MT5's timeframes in minutes). core may not
# import timebase (module map), so the set is repeated here and a unit test keeps the two equal.
TIMEFRAMES_MINUTES = frozenset({1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720, 1440})

_PRICES = ("open", "high", "low", "close")
_COUNTS = ("time_raw", "timeframe", "tick_volume", "m1_count")


def _exact(value: object, kind: type, name: str) -> None:
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Bar:
    """One bar: raw MT5 open time, the same instant in UTC, timeframe in minutes and bid OHLC."""

    time_raw: int
    time_utc: datetime
    timeframe: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    spread: int | None
    tick_volume: int
    m1_count: int

    def __post_init__(self) -> None:
        for name in _COUNTS:
            _exact(getattr(self, name), int, name)
        _exact(self.time_utc, datetime, "time_utc")
        if self.time_utc.utcoffset() != timedelta(0):
            raise ValueError("time_utc must be an aware datetime in UTC")
        if self.timeframe not in TIMEFRAMES_MINUTES:
            raise ValueError(f"timeframe must be one of {sorted(TIMEFRAMES_MINUTES)} minutes")
        for name in _PRICES:
            value = getattr(self, name)
            _exact(value, Decimal, name)
            if not value.is_finite():
                raise ValueError(f"{name} must be finite")
        if self.spread is not None:
            _exact(self.spread, int, "spread")
        # Contract v1.1: values only a bug can produce. m1_count has no upper bound: duplicate M1
        # (a STOP defect the report already carries) make an aggregated bar count more than its
        # timeframe, and refusing that would stop the whole aggregation.
        if self.tick_volume < 0:
            raise ValueError("tick_volume cannot be negative")
        if self.m1_count < 1:
            raise ValueError("m1_count must be at least 1")
