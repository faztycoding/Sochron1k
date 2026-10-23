"""Value types of the M1 validation report and of aggregated bars (docs/contracts/CORE-005-data-bars.md)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Literal

from sochron.core import Bar
from sochron.timebase import to_zone

_PROBE = datetime(2026, 1, 1, tzinfo=UTC)

Severity = Literal["WARN", "UNKNOWN", "STOP"]
DayStatus = Literal["PASS", "WARN", "UNKNOWN", "STOP"]
SEVERITIES = ("WARN", "UNKNOWN", "STOP")


def exact(value: object, kind: type, name: str) -> None:
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class Defect:
    """One data defect: its code, severity, the raw time of the bar it was seen at, and a detail."""

    code: str
    severity: Severity
    time_raw: int | None
    detail: str


def _wall_minute(at: object, name: str) -> None:
    """A naive wall time on a whole minute (review CORE-005-r1 F4: seconds were cut silently)."""
    exact(at, time, name)
    if at.tzinfo is not None:
        raise ValueError(f"{name} is a wall time in the calendar zone, without tzinfo")
    if at.second or at.microsecond:
        raise ValueError(f"{name} must be on a whole minute")


def _weekly_point(value: object, name: str) -> tuple[int, time]:
    exact(value, tuple, name)
    if len(value) != 2:
        raise ValueError(f"{name} must be (weekday, time)")
    weekday, at = value
    exact(weekday, int, f"{name} weekday")
    _wall_minute(at, f"{name} time")
    if not 0 <= weekday <= 6:
        raise ValueError(f"{name} weekday must be 0 (Monday) to 6 (Sunday)")
    return weekday, at


@dataclass(frozen=True, slots=True)
class ClosureCalendar:
    """When the market is expected to be closed, as wall time in one IANA zone.

    daily_break is [start, end) every day; weekend is [(weekday, time), (weekday, time)) once a
    week, weekdays as datetime.date.weekday() (Monday 0 .. Sunday 6). Missing minutes inside a
    closure are not data defects.
    """

    zone: str
    daily_break: tuple[time, time]
    weekend: tuple[tuple[int, time], tuple[int, time]]
    provenance: str

    def __post_init__(self) -> None:
        exact(self.zone, str, "zone")
        exact(self.provenance, str, "provenance")
        exact(self.daily_break, tuple, "daily_break")
        if len(self.daily_break) != 2:
            raise ValueError("daily_break must be (start, end)")
        for at in self.daily_break:
            _wall_minute(at, "daily_break time")
        exact(self.weekend, tuple, "weekend")
        if len(self.weekend) != 2:
            raise ValueError("weekend must be ((weekday, time), (weekday, time))")
        _weekly_point(self.weekend[0], "weekend start")
        _weekly_point(self.weekend[1], "weekend end")
        # Fail fast on an unknown zone name: convert a fixed instant (no clock) through timebase.
        to_zone(_PROBE, self.zone)


# D2 [A] (owner, 2026-10-23 15:0x): SPIKE-001 saw a break near 17:00 New York; the usual gold
# hours are a 17:00-18:00 daily break and Friday 17:00 to Sunday 18:00. R1 must measure the real
# break on the data (SPIKE-001 bars suggest 63-68 minutes, so 66+ minute breaks are WARN here).
H001_CLOSURES = ClosureCalendar(
    zone="America/New_York",
    daily_break=(time(17, 0), time(18, 0)),
    weekend=((4, time(17, 0)), (6, time(18, 0))),
    provenance="assumed [A]: CORE-005 D2, owner 2026-10-23; docs/evidence/SPIKE-001.md break near 17:00 New York",
)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Defects of an M1 series, the status of each UTC day, and how many M1 bars were read.

    calendar is the closure calendar the report was made with; aggregate() uses it to tell an
    incomplete bar (missing in-session minutes) from one that touches a closure.
    """

    defects: tuple[Defect, ...]
    days: Mapping[date, DayStatus]
    m1_bars: int
    calendar: ClosureCalendar


@dataclass(frozen=True, slots=True)
class AggregatedBar:
    """A bar built from M1 bars, with the defect codes of its M1 and "incomplete" when it applies."""

    bar: Bar
    flags: frozenset[str]
