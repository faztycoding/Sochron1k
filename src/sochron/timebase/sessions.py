"""Entry windows in a local zone and the Thai trading date.

The H001 entry window is 03:00-15:59 New York wall time (docs/hypotheses/H001), so in UTC it
moves with US daylight saving time. The Thai date is the day of the daily loss baseline
(SPEC section 6). Both use zoneinfo; no DST rule is written by hand.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .convert import check_aware

BANGKOK_ZONE = "Asia/Bangkok"


@dataclass(frozen=True)
class EntryWindow:
    """Wall-clock minutes [start, end_inclusive] in an IANA zone during which entries are allowed."""

    zone: str
    start: time
    end_inclusive: time


NY_ENTRY_WINDOW = EntryWindow("America/New_York", time(3, 0), time(15, 59))


def in_entry_window(dt: datetime, window: EntryWindow = NY_ENTRY_WINDOW) -> bool:
    """Whether the instant falls inside the window, at minute precision.

    Seconds and microseconds are ignored on the instant and on both window bounds alike, so a
    window is a range of wall-clock minutes whatever the caller put in its time objects.
    """
    local = check_aware(dt).astimezone(ZoneInfo(window.zone))
    minute = time(local.hour, local.minute)
    start = time(window.start.hour, window.start.minute)
    end_inclusive = time(window.end_inclusive.hour, window.end_inclusive.minute)
    return start <= minute <= end_inclusive


def bangkok_date(dt: datetime) -> date:
    """Calendar date of the instant in Asia/Bangkok."""
    return check_aware(dt).astimezone(ZoneInfo(BANGKOK_ZONE)).date()
