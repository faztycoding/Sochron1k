"""simulate_trade(): one round trip on M1 bid bars under the CORE-007 fill and stop table.

s is the spread (points) of the M1 where an event happens, the model's fallback when it is None; p is
model.point. Long enters at the bid open and pays the ask (open + s*p), so its stop sits at
fill ask - stop_distance on the bid; short enters at the bid open and its stop is an ask level
(open + stop_distance), reached when bid + s*p reaches it. Every M1 from the entry M1 on is checked
open first (a gap fills at the open), then high or low (a touch fills at the stop). Gross money is on
bid prices and never multiplied by the stress factor; costs come once from costs.round_trip_cost.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, Overflow, localcontext

from sochron.core import Bar
from sochron.costs import CONTEXT, CostModel, check_volume, r_multiple, round_trip_cost
from sochron.timebase import to_zone

from .model import BacktestError, ExitReason, Rollover, Side, Trade, exact, exact_optional, finite

_ONE_DAY = timedelta(days=1)


def check_m1(bar: Bar, previous: Bar | None, name: str) -> Bar:
    """The per-M1 checks shared by run and simulate_trade; previous is the M1 read just before."""
    exact(bar, Bar, name)
    if bar.timeframe != 1:
        raise BacktestError(f"{name} must be an M1 bar")
    if previous is not None and bar.time_raw <= previous.time_raw:
        raise BacktestError(f"{name} time is not after the M1 before it")
    if bar.spread is not None and bar.spread < 0:
        raise BacktestError(f"{name} has a negative spread")
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        raise BacktestError(f"{name} has a price that is zero or negative")
    if bar.high < bar.low or not bar.low <= bar.open <= bar.high or not bar.low <= bar.close <= bar.high:
        raise BacktestError(f"{name} has inconsistent OHLC")
    return bar


def spread_points(bar: Bar, model: CostModel) -> int:
    return model.spread_fallback_points if bar.spread is None else bar.spread


def stop_price(side: Side, entry: Bar, stop_distance: Decimal, model: CostModel) -> Decimal:
    """Long: fill ask - stop_distance (a bid level); short: bid open + stop_distance (an ask level)."""
    with localcontext(CONTEXT):
        if side == "long":
            return entry.open + spread_points(entry, model) * model.point - stop_distance
        return entry.open + stop_distance


def gap_at_open(side: Side, bar: Bar, stop: Decimal, model: CostModel) -> bool:
    """True when the bar opens at or beyond the stop (the fill is the open)."""
    with localcontext(CONTEXT):
        if side == "long":
            return bar.open <= stop
        return bar.open + spread_points(bar, model) * model.point >= stop


def stop_fill(side: Side, bar: Bar, stop: Decimal, model: CostModel) -> Decimal | None:
    """The exit bid if the stop is hit in this M1 (open checked first), else None."""
    if gap_at_open(side, bar, stop, model):
        return bar.open
    with localcontext(CONTEXT):
        if side == "long":
            return stop if bar.low <= stop else None
        ask_spread = spread_points(bar, model) * model.point
        return stop - ask_spread if bar.high + ask_spread >= stop else None


def count_nights(entry_utc: datetime, exit_utc: datetime, rollover: Rollover, triple_weekday: int) -> tuple[int, int]:
    """(nights, triple_nights): rollovers at rollover.at in rollover.zone, Monday to Friday, entry < T <= exit."""
    start = to_zone(entry_utc, rollover.zone)
    end = to_zone(exit_utc, rollover.zone)
    nights = triple = 0
    day = start.date()
    while day <= end.date():
        if day.weekday() < 5:
            moment = datetime.combine(day, rollover.at, tzinfo=start.tzinfo)
            if entry_utc < moment <= exit_utc:
                nights += 1
                if day.weekday() == triple_weekday:
                    triple += 1
        day += _ONE_DAY
    return nights, triple


@dataclass(frozen=True)
class Plan:
    """A checked trade request: everything simulate needs besides the bars."""

    entry_index: int
    side: Side
    stop_distance: Decimal
    lots: Decimal
    model: CostModel
    rollover: Rollover
    risk_money: Decimal
    actual_risk: Decimal | None
    exit_index: int | None
    data_flags: frozenset[str]


def too_large(error: Overflow) -> BacktestError:
    """A finite value whose arithmetic leaves the Decimal context's exponent range is outside the domain."""
    return BacktestError(f"a value is too large for the backtest's Decimal arithmetic ({type(error).__name__})")


def simulate(m1: Sequence[Bar], plan: Plan, *, checked: bool) -> Trade:
    """Fill the planned trade; checked=False runs the per-M1 checks on every M1 it reads first."""
    try:
        return _simulate(m1, plan, checked)
    except Overflow as error:
        raise too_large(error) from error


def _simulate(m1: Sequence[Bar], plan: Plan, checked: bool) -> Trade:
    entry = m1[plan.entry_index]
    if not checked:
        check_m1(entry, None, f"m1[{plan.entry_index}]")
    stop = stop_price(plan.side, entry, plan.stop_distance, plan.model)
    end = len(m1) if plan.exit_index is None else plan.exit_index
    previous = None
    for index in range(plan.entry_index, end):
        bar = m1[index]
        if not checked and index != plan.entry_index:
            check_m1(bar, previous, f"m1[{index}]")
        fill = stop_fill(plan.side, bar, stop, plan.model)
        if fill is not None:
            return _trade(plan, entry, stop, bar, fill, "stop", False)
        previous = bar
    if plan.exit_index is not None:
        bar = m1[plan.exit_index]
        if not checked:
            check_m1(bar, previous, f"m1[{plan.exit_index}]")
        ambiguous = gap_at_open(plan.side, bar, stop, plan.model)
        return _trade(plan, entry, stop, bar, bar.open, "stop" if ambiguous else "signal", ambiguous)
    last = m1[len(m1) - 1]
    return _trade(plan, entry, stop, last, last.close, "end_of_data", False)


def _trade(plan: Plan, entry: Bar, stop: Decimal, exit_bar: Bar, exit_bid: Decimal, reason: ExitReason,
           ambiguous: bool) -> Trade:
    model = plan.model
    entry_spread = spread_points(entry, model)
    exit_spread = spread_points(exit_bar, model)
    nights, triple = count_nights(entry.time_utc, exit_bar.time_utc, plan.rollover, model.triple_swap_weekday)
    with localcontext(CONTEXT):
        move = exit_bid - entry.open if plan.side == "long" else entry.open - exit_bid
        gross = move * model.contract_size * plan.lots
    costs = round_trip_cost(plan.side, plan.lots, entry_spread, exit_spread, nights, triple, model)
    with localcontext(CONTEXT):
        net = gross - costs.total
    return Trade(
        side=plan.side, entry_time_raw=entry.time_raw, entry_bid=entry.open, entry_spread_points=entry_spread,
        exit_time_raw=exit_bar.time_raw, exit_bid=exit_bid, exit_spread_points=exit_spread, lots=plan.lots,
        stop_distance=plan.stop_distance, stop_price=stop, exit_reason=reason, ambiguous=ambiguous,
        nights=nights, triple_nights=triple, costs=costs, gross_money=gross, net_money=net,
        risk_money=plan.risk_money, actual_risk=plan.actual_risk, r=r_multiple(net, plan.risk_money),
        data_flags=plan.data_flags,
    )


def check_side(side: str) -> Side:
    exact(side, str, "side")
    if side == "long":
        return "long"
    if side == "short":
        return "short"
    raise BacktestError("side must be 'long' or 'short'")


def check_trade_values(stop_distance: Decimal, risk_money: Decimal, actual_risk: Decimal | None) -> None:
    for name, value in (("stop_distance", stop_distance), ("risk_money", risk_money), ("actual_risk", actual_risk)):
        finite(value, name)
    if stop_distance <= 0:
        raise BacktestError("stop_distance must be positive")
    if risk_money <= 0:
        raise BacktestError("risk_money must be positive")
    if actual_risk is not None and actual_risk <= 0:
        raise BacktestError("actual_risk must be None or positive")


def check_flags(flags: object, name: str) -> frozenset[str]:
    """The same frozenset when it is exactly a frozenset of exactly str; TypeError otherwise."""
    checked = exact(flags, frozenset, name)
    for flag in checked:
        exact(flag, str, f"a flag in {name}")
    return checked


def simulate_trade(
    m1: Sequence[Bar],
    entry_index: int,
    side: Side,
    stop_distance: Decimal,
    lots: Decimal,
    model: CostModel,
    rollover: Rollover,
    *,
    risk_money: Decimal,
    actual_risk: Decimal | None = None,
    exit_index: int | None = None,
    data_flags: frozenset[str] = frozenset(),
) -> Trade:
    """One trade entered at the open of m1[entry_index]; closed by its stop, at the open of
    m1[exit_index] (a signal exit) or at the close of the last M1 (end of data)."""
    if not isinstance(m1, Sequence) or isinstance(m1, (str, bytes)):
        raise TypeError(f"m1 must be a sequence of Bar, not {type(m1).__name__}")
    exact(entry_index, int, "entry_index")
    side = check_side(side)
    exact(stop_distance, Decimal, "stop_distance")
    exact(lots, Decimal, "lots")
    exact(model, CostModel, "model")
    exact(rollover, Rollover, "rollover")
    exact(risk_money, Decimal, "risk_money")
    exact_optional(actual_risk, Decimal, "actual_risk")
    exact_optional(exit_index, int, "exit_index")
    check_flags(data_flags, "data_flags")
    check_trade_values(stop_distance, risk_money, actual_risk)
    finite(lots, "lots")
    if not 0 <= entry_index < len(m1):
        raise BacktestError("entry_index is outside m1")
    if exit_index is not None and not entry_index < exit_index < len(m1):
        raise BacktestError("exit_index must be after entry_index and inside m1")
    check_volume(lots, model)
    plan = Plan(entry_index, side, stop_distance, lots, model, rollover, risk_money, actual_risk, exit_index,
                data_flags)
    return simulate(m1, plan, checked=False)
