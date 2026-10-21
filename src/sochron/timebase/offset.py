"""Classification of measured tick-versus-clock offsets.

SPIKE-001 measured each sample as tick time_msc / 1000 minus the machine clock. This module
only reports what a set of samples looks like; it never changes a TimeRule, and a result of
"shifted" is a reason to stop and measure again, not to correct anything automatically
(docs/architecture.md section 13a).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

HOUR_SECONDS = 3600.0


@dataclass(frozen=True)
class OffsetClass:
    """kind: ok (all within tolerance), shifted (all near the same whole hour), or unknown."""

    kind: Literal["ok", "shifted", "unknown"]
    hours: int | None
    samples: int


def classify_offset(
    offsets_seconds: Sequence[float], tolerance_seconds: float = 120.0
) -> OffsetClass:
    """Classify offset samples; empty or inconsistent samples are unknown, never guessed."""
    values = [float(x) for x in offsets_seconds]
    samples = len(values)
    if samples == 0:
        return OffsetClass("unknown", None, 0)
    if all(abs(x) <= tolerance_seconds for x in values):
        return OffsetClass("ok", None, samples)
    whole_hours = {round(x / HOUR_SECONDS) for x in values}
    if len(whole_hours) == 1:
        hours = whole_hours.pop()
        if hours != 0 and all(abs(x - hours * HOUR_SECONDS) <= tolerance_seconds for x in values):
            return OffsetClass("shifted", hours, samples)
    return OffsetClass("unknown", None, samples)
