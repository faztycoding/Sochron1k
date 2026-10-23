"""Pure checks and builders for M1 snapshots (docs/contracts/CORE-005-data-bars.md).

validate_m1 reports every data defect of an M1 series and the status of each UTC day without
repairing anything; aggregate builds larger bars (M15 for H001) from M1. Reading Parquet files and
manifests is not here yet: it needs a dependency admission (SLICE-R1).
"""

from .aggregate import aggregate
from .model import (
    H001_CLOSURES,
    AggregatedBar,
    ClosureCalendar,
    DayStatus,
    Defect,
    Severity,
    ValidationReport,
)
from .validate import validate_m1

__all__ = [
    "AggregatedBar",
    "ClosureCalendar",
    "DayStatus",
    "Defect",
    "H001_CLOSURES",
    "Severity",
    "ValidationReport",
    "aggregate",
    "validate_m1",
]
