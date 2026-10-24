"""summarize() and percentile() (contract "summarize และสถิติ", D6-D8).

Trades are taken in result order; every mean is the sum in that order divided by the count, all in
sochron.costs.CONTEXT (precision 28, ROUND_HALF_EVEN) whatever the caller's context is. A sum that leaves
the context's exponent range is a ResearchError, not decimal.Overflow.
"""

from collections.abc import Sequence
from decimal import Decimal, Overflow, localcontext

from sochron.backtest import Result, Trade
from sochron.costs import CONTEXT
from sochron.timebase import TimeRule, to_utc

from .model import ResearchError, Summary, exact, too_large


def sum_in_order(values: Sequence[Decimal]) -> Decimal:
    """The sum from Decimal(0), value by value in order, in CONTEXT."""
    try:
        with localcontext(CONTEXT):
            total = Decimal(0)
            for value in values:
                total = total + value
            return total
    except Overflow as error:
        raise too_large(error) from error


def mean_in_order(values: Sequence[Decimal]) -> Decimal | None:
    """Sum in order, then divide by the count, in CONTEXT; None for no values."""
    if not values:
        return None
    total = sum_in_order(values)
    with localcontext(CONTEXT):  # |total| / count <= |total|: the division cannot overflow
        return total / len(values)


def _max_drawdown(trades: Sequence[Trade]) -> Decimal:
    """The largest fall of cumulative R below its running peak, the cumulative sum starting at 0 (D7)."""
    try:
        with localcontext(CONTEXT):
            total = peak = deepest = Decimal(0)
            for trade in trades:
                total = total + trade.r
                peak = max(peak, total)
                deepest = max(deepest, peak - total)
            return deepest
    except Overflow as error:
        raise too_large(error) from error


def _top5_removed(trades: Sequence[Trade]) -> Decimal | None:
    """The mean R without the 5 highest R (a tie removes the earlier trade first); None for 5 trades or fewer."""
    if len(trades) <= 5:
        return None
    # copy_negate is exact in any context, so the order never depends on the caller's precision.
    removed = set(sorted(range(len(trades)), key=lambda index: (trades[index].r.copy_negate(), index))[:5])
    return mean_in_order([trade.r for index, trade in enumerate(trades) if index not in removed])


def summarize(result: Result, rule: TimeRule) -> Summary:
    """The statistics of result's trades; years are UTC years of the entry time read by rule (D8)."""
    exact(result, Result, "result")
    exact(rule, TimeRule, "rule")
    trades = exact(result.trades, tuple, "result.trades")
    for index, trade in enumerate(trades):  # a caller-built Result is allowed (baseline step 1), so check it
        exact(trade, Trade, f"result.trades[{index}]")
        for name in ("r", "net_money"):
            if not exact(getattr(trade, name), Decimal, f"result.trades[{index}].{name}").is_finite():
                raise ResearchError(f"result.trades[{index}].{name} must be finite")
    longs = [trade.r for trade in trades if trade.side == "long"]
    shorts = [trade.r for trade in trades if trade.side == "short"]
    by_year: dict[int, list[Decimal]] = {}
    for trade in trades:
        by_year.setdefault(to_utc(trade.entry_time_raw, rule).year, []).append(trade.r)
    years = []
    for year in sorted(by_year):
        mean = mean_in_order(by_year[year])
        if mean is not None:
            years.append((year, mean))
    net = sum_in_order([trade.net_money for trade in trades])
    return Summary(
        trades=len(trades),
        expectancy_r=mean_in_order([trade.r for trade in trades]),
        max_drawdown_r=_max_drawdown(trades),
        net_money=net,
        long_trades=len(longs),
        long_expectancy_r=mean_in_order(longs),
        short_trades=len(shorts),
        short_expectancy_r=mean_in_order(shorts),
        top5_removed_expectancy_r=_top5_removed(trades),
        expectancy_by_year=tuple(years),
        ambiguous_trades=sum(1 for trade in trades if trade.ambiguous),
        flagged_trades=sum(1 for trade in trades if trade.data_flags),
        gap_fills=sum(1 for trade in trades if "unexpected_gap" in trade.data_flags),
        end_of_data_trades=sum(1 for trade in trades if trade.exit_reason == "end_of_data"),
    )


def percentile(values: Sequence[Decimal], q: Decimal) -> Decimal:
    """Nearest rank (D6): sort ascending and take the value of rank ceil(q x n), counted from 1."""
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError(f"values must be a sequence of Decimal, not {type(values).__name__}")
    for value in values:
        exact(value, Decimal, "a value")
    exact(q, Decimal, "q")
    if not values:
        raise ResearchError("percentile needs at least one value")
    if not q.is_finite() or not 0 < q <= 1:
        raise ResearchError("q must be in (0, 1]")
    if not all(value.is_finite() for value in values):
        raise ResearchError("every value must be finite")
    numerator, denominator = q.as_integer_ratio()
    rank = -(-numerator * len(values) // denominator)  # exact ceil(q x n), in 1..n since 0 < q <= 1
    return sorted(values)[rank - 1]
