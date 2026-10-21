"""The one time module of Sochron1k (contract CORE-001).

Everything that converts, aligns or classifies time goes through here: raw MT5 time <-> UTC
by a measured TimeRule, wall time in a zone, the New York entry window, the Thai trading
date, bar alignment, and offset classification. Pure: no clock calls, no I/O, no MetaTrader5.
"""

from .convert import (
    RAW_MAX_EXCLUSIVE,
    RAW_MIN,
    TIMEFRAMES_MINUTES,
    bar_open,
    check_aware,
    to_raw,
    to_utc,
    to_zone,
)
from .errors import (
    BadTimeframe,
    NaiveDatetime,
    RawTimeMismatch,
    RawTimeOutOfRange,
    TimebaseError,
    UnknownTimeRule,
)
from .offset import OffsetClass, classify_offset
from .rules import RULES, TimeRule, rule_for
from .sessions import BANGKOK_ZONE, NY_ENTRY_WINDOW, EntryWindow, bangkok_date, in_entry_window

__all__ = [
    "BANGKOK_ZONE",
    "BadTimeframe",
    "EntryWindow",
    "NY_ENTRY_WINDOW",
    "NaiveDatetime",
    "OffsetClass",
    "RAW_MAX_EXCLUSIVE",
    "RAW_MIN",
    "RULES",
    "RawTimeMismatch",
    "RawTimeOutOfRange",
    "TIMEFRAMES_MINUTES",
    "TimeRule",
    "TimebaseError",
    "UnknownTimeRule",
    "bangkok_date",
    "bar_open",
    "check_aware",
    "classify_offset",
    "in_entry_window",
    "rule_for",
    "to_raw",
    "to_utc",
    "to_zone",
]
