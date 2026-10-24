"""decide(): the H001 rules on indicator rows (H001 section 3; CORE-006 rules, D3-D5 and v1.1).

Entries are judged at the close of bar t and filled by the caller at the open of bar t+1; this
module only returns the decision and, for an entry, the stop distance k x ATR[t].
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Literal

from sochron.timebase import NY_ENTRY_WINDOW, in_entry_window

from .indicators import IndicatorRow
from .params import CONTEXT, STRATEGY_VERSION, H001Params, StrategyError, exact

Position = Literal["flat", "long", "short"]
Action = Literal["enter_long", "enter_short", "exit", "hold", "none", "skip"]


@dataclass(frozen=True)
class Decision:
    """What to do at the open of the next bar; skip lists every failed check in contract order."""

    action: Action
    stop_distance: Decimal | None
    reasons: tuple[str, ...]
    version: str


def _decision(action: Action, stop_distance: Decimal | None = None, reasons: tuple[str, ...] = ()) -> Decision:
    return Decision(action, stop_distance, reasons, STRATEGY_VERSION)


def _signals(row: IndicatorRow, previous: IndicatorRow | None, params: H001Params) -> tuple[bool, bool]:
    """(long entry signal, short entry signal) at row t; a rule that needs an unknown value is false."""
    ts = row.ts
    if params.variant == "A":
        if ts is None or previous is None or previous.ts is None:
            return False, False
        theta = params.theta
        negative_theta = theta.copy_negate()  # exact at any number of digits, so short mirrors long (D5)
        return (ts > theta and previous.ts <= theta), (ts < negative_theta and previous.ts >= negative_theta)
    long_breakout = row.hh_n is not None and row.close > row.hh_n
    short_breakout = row.ll_n is not None and row.close < row.ll_n
    if params.variant == "C":
        long_breakout = long_breakout and ts is not None and ts > 0
        short_breakout = short_breakout and ts is not None and ts < 0
    return long_breakout, short_breakout


def _exit(position: Position, row: IndicatorRow, params: H001Params, long_entry: bool, short_entry: bool) -> bool:
    if position == "long":
        if short_entry:
            return True
        if params.variant == "A":
            return row.ts is not None and row.ts <= 0
        return row.ll_m is not None and row.close < row.ll_m
    if long_entry:
        return True
    if params.variant == "A":
        return row.ts is not None and row.ts >= 0
    return row.hh_m is not None and row.close > row.hh_m


def _invalid(row: IndicatorRow, next_open_utc: datetime) -> tuple[str, ...]:
    reasons = []
    if not in_entry_window(next_open_utc, NY_ENTRY_WINDOW):
        reasons.append("outside_window")
    if row.spread is None or row.spread_median_96 is None:
        reasons.append("spread_unknown")
    else:
        with localcontext(CONTEXT):
            too_wide = Decimal(row.spread) > 3 * row.spread_median_96
        if too_wide:
            reasons.append("spread_filter")
    if row.atr is None or row.atr.is_zero():
        reasons.append("atr_zero")
    if row.lookback_flags:
        reasons.append("data_flag")
    if not row.warm:
        reasons.append("warmup")
    order = ("outside_window", "spread_filter", "spread_unknown", "atr_zero", "data_flag", "warmup")
    return tuple(sorted(reasons, key=order.index))


def decide(
    rows: Sequence[IndicatorRow], t: int, position: Position, next_open_utc: datetime, params: H001Params
) -> Decision:
    """The H001 decision at the close of bar t for the given position (exits never wait for a window)."""
    exact(params, H001Params, "params")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise TypeError(f"rows must be a sequence of IndicatorRow, not {type(rows).__name__}")
    exact(t, int, "t")
    exact(position, str, "position")
    exact(next_open_utc, datetime, "next_open_utc")
    if position not in ("flat", "long", "short"):
        raise StrategyError("position must be 'flat', 'long' or 'short'")
    if not 0 <= t < len(rows):
        raise StrategyError("t is outside the rows")
    row = rows[t]
    exact(row, IndicatorRow, "rows[t]")
    previous = rows[t - 1] if t >= 1 else None
    if previous is not None:
        exact(previous, IndicatorRow, "rows[t-1]")
    long_entry, short_entry = _signals(row, previous, params)
    if position != "flat":
        return _decision("exit" if _exit(position, row, params, long_entry, short_entry) else "hold")
    if not (long_entry or short_entry):
        return _decision("none")
    reasons = _invalid(row, next_open_utc)
    if reasons:
        return _decision("skip", reasons=reasons)
    with localcontext(CONTEXT):
        stop_distance = params.k * row.atr
    return _decision("enter_long" if long_entry else "enter_short", stop_distance)
