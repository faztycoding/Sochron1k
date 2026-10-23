"""aggregate: build bars of a larger timeframe from M1 with code in this repository (H001 section 2).

Grouping follows timebase.bar_open, so bars align to UTC boundaries under the rule. open is the
first M1 open, high the maximum, low the minimum, close the last M1 close, tick_volume the sum,
spread the last M1 spread (owner decision D1: the state at the close of the bar), m1_count the
number of M1 read. A slot without any M1 makes no bar (nothing is filled in). flags are the defect
codes reported for the M1 inside the bar, plus "incomplete" when fewer than timeframe M1 are
present and a missing minute is in session under the report's calendar.
"""

from collections.abc import Sequence
from datetime import timedelta

from sochron.core import Bar
from sochron.timebase import TIMEFRAMES_MINUTES, TimeRule, bar_open, to_utc

from .model import AggregatedBar, ValidationReport, exact
from .validate import in_closure, require_bars


def _incomplete(members: list[Bar], start_raw: int, timeframe: int, rule: TimeRule, report: ValidationReport) -> bool:
    if len(members) >= timeframe:
        return False
    present = {(bar.time_raw - start_raw) // 60 for bar in members}
    start_utc = to_utc(start_raw, rule)
    return any(
        not in_closure(start_utc + timedelta(minutes=index), report.calendar)
        for index in range(timeframe)
        if index not in present
    )


def aggregate(bars: Sequence[Bar], timeframe: int, rule: TimeRule, report: ValidationReport) -> tuple[AggregatedBar, ...]:
    """Bars of `timeframe` minutes from M1 bars, in time order, each with its flags."""
    items = require_bars(bars)
    exact(timeframe, int, "timeframe")
    if timeframe not in TIMEFRAMES_MINUTES:
        raise ValueError(f"timeframe must be one of {sorted(TIMEFRAMES_MINUTES)} minutes")
    exact(rule, TimeRule, "rule")
    exact(report, ValidationReport, "report")
    if report.m1_bars != len(items):
        raise ValueError("the report was made for a different number of M1 bars")

    slots: dict[int, list[Bar]] = {}
    for bar in items:
        slots.setdefault(bar_open(bar.time_raw, timeframe, rule), []).append(bar)
    codes: dict[int, set[str]] = {}
    for defect in report.defects:
        if defect.time_raw is not None:
            codes.setdefault(bar_open(defect.time_raw, timeframe, rule), set()).add(defect.code)

    result = []
    for start_raw in sorted(slots):
        members = sorted(slots[start_raw], key=lambda bar: bar.time_raw)
        flags = set(codes.get(start_raw, ()))
        if _incomplete(members, start_raw, timeframe, rule, report):
            flags.add("incomplete")
        bar = Bar(
            time_raw=start_raw,
            time_utc=to_utc(start_raw, rule),
            timeframe=timeframe,
            open=members[0].open,
            high=max(member.high for member in members),
            low=min(member.low for member in members),
            close=members[-1].close,
            spread=members[-1].spread,
            tick_volume=sum(member.tick_volume for member in members),
            m1_count=len(members),
        )
        result.append(AggregatedBar(bar, frozenset(flags)))
    return tuple(result)
