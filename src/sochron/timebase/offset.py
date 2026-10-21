"""Classification of measured tick-versus-clock offsets.

SPIKE-001 measured each sample as tick time_msc / 1000 minus the machine clock. This module
only reports what a set of samples looks like; it never changes a TimeRule, and a result of
"shifted" is a reason to stop and measure again, not to correct anything automatically
(docs/architecture.md section 13a).
"""

import math
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
    """Classify offset samples; empty, ambiguous or inconsistent samples are unknown, never guessed."""
    values = [float(x) for x in offsets_seconds]
    samples = len(values)
    if samples == 0:
        return OffsetClass("unknown", None, 0)
    if all(abs(x) <= tolerance_seconds for x in values):
        return OffsetClass("ok", None, samples)
    hours = _common_whole_hour(values, tolerance_seconds)
    if hours is not None:
        return OffsetClass("shifted", hours, samples)
    return OffsetClass("unknown", None, samples)


def _common_whole_hour(values: list[float], tolerance: float) -> int | None:
    """The one nonzero whole hour h with |x - h * 3600| <= tolerance for every sample.

    None when no hour fits every sample, and also when more than one does: that evidence is
    ambiguous, not a shift. The hours fitting one sample are consecutive integers, so the
    hours fitting all samples lie between the largest lower bound and the smallest upper
    bound. Float division can be off by one exactly at a boundary, so the candidates around
    those bounds are settled with the contract's own inequality.
    """
    lowest = max(math.ceil((x - tolerance) / HOUR_SECONDS) for x in values)
    highest = min(math.floor((x + tolerance) / HOUR_SECONDS) for x in values)
    if highest - lowest > 2:
        return None  # at least two hours fit every sample, even allowing for float rounding
    fitting = [
        h
        for h in range(lowest - 1, highest + 2)
        if h != 0 and all(abs(x - h * HOUR_SECONDS) <= tolerance for x in values)
    ]
    return fitting[0] if len(fitting) == 1 else None
