"""Classification of measured tick-versus-clock offsets.

SPIKE-001 measured each sample as tick time_msc / 1000 minus the machine clock. This module
only reports what a set of samples looks like; it never changes a TimeRule, and a result of
"shifted" is a reason to stop and measure again, not to correct anything automatically
(docs/architecture.md section 13a).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

HOUR_SECONDS = 3600


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
    if not all(math.isfinite(x) for x in values):
        return OffsetClass("unknown", None, samples)  # NaN or infinity establishes nothing
    if all(abs(x) <= tolerance_seconds for x in values):
        return OffsetClass("ok", None, samples)
    hours = _common_whole_hour(values, tolerance_seconds)
    if hours is not None:
        return OffsetClass("shifted", hours, samples)
    return OffsetClass("unknown", None, samples)


def _common_whole_hour(values: list[float], tolerance: float) -> int | None:
    """The one nonzero whole hour h with |x - h * 3600| <= tolerance for every sample.

    None when no hour fits every sample, and also when more than one does: that evidence is
    ambiguous, not a shift. The hours fitting one sample are the integers between
    (x - tolerance) / 3600 and (x + tolerance) / 3600, so the hours fitting all samples lie
    between the largest lower bound and the smallest upper bound. The bounds are formed in
    exact rational arithmetic: a binary float could overflow there, or round neighbouring
    hours together, once a finite sample or tolerance is large enough.
    """
    width = Fraction(tolerance)
    lowest = max(math.ceil((Fraction(x) - width) / HOUR_SECONDS) for x in values)
    highest = min(math.floor((Fraction(x) + width) / HOUR_SECONDS) for x in values)
    if lowest == highest and lowest != 0:
        return lowest
    return None
