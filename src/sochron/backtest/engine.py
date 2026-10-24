"""run(): H001 over checked M1 and M15 bid bars, one position at a time (CORE-007 event order).

Per M15 bar t: (1) a held position checks its stop on every M1 of bar t; (2) unless t is the last bar,
strategy.decide at the close of t with the position after (1); (3) exit at the open of the first M1 of
t+1; (4) an entry on an allowed side is sized with the equity after every closed trade and fills at
that open; (5) a skip from decide is always recorded; (6) the last bar closes what is still held at
the end of the data. Every trade is built by the same fill code as simulate_trade.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, Overflow, localcontext

from sochron.core import Bar
from sochron.costs import CONTEXT, CostModel, check_volume
from sochron.strategy import STRATEGY_VERSION, H001Params, decide, indicators
from sochron.timebase import RAW_MAX_EXCLUSIVE, RAW_MIN, TimeRule, bar_open, to_utc

from .model import BACKTEST_VERSION, SIDES, BacktestError, Result, Rollover, Side, SizedLots, Sizer, Skip, Trade, exact, finite
from .trade import Plan, check_flags, check_m1, simulate, stop_fill, stop_price, too_large


def _sequence(value: object, name: str) -> Sequence:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence, not {type(value).__name__}")
    return value


def _m15_shape(m15: Sequence) -> list[tuple[Bar, frozenset[str]]]:
    """M15 bars by shape (D9): .bar exactly core.Bar, .flags a frozenset of str."""
    checked = []
    for index, item in enumerate(m15):
        bar = getattr(item, "bar", None)
        flags = getattr(item, "flags", None)
        exact(bar, Bar, f"m15[{index}].bar")
        check_flags(flags, f"m15[{index}].flags")
        checked.append((bar, flags))
    return checked


def _check_time(bar: Bar, rule: TimeRule, name: str) -> None:
    """time_utc read from time_raw by the rule; a raw time timebase cannot read is refused here too."""
    if not RAW_MIN <= bar.time_raw < RAW_MAX_EXCLUSIVE or bar.time_utc != to_utc(bar.time_raw, rule):
        raise BacktestError(f"{name} time_utc does not match its raw time under the rule")


def _check_m15(bars15: list[tuple[Bar, frozenset[str]]], rule: TimeRule) -> None:
    """15 minutes, strictly increasing time, and time_utc read from time_raw by the rule (v1.5)."""
    for index, (bar, _) in enumerate(bars15):
        if bar.timeframe != 15:
            raise BacktestError(f"m15[{index}] is not an M15 bar")
        if index and bar.time_raw <= bars15[index - 1][0].time_raw:
            raise BacktestError(f"m15[{index}] time is not after the bar before it")
        _check_time(bar, rule, f"m15[{index}]")


def _check_m1(m1: Sequence, rule: TimeRule) -> None:
    previous = None
    for index, bar in enumerate(m1):
        check_m1(bar, previous, f"m1[{index}]")
        _check_time(bar, rule, f"m1[{index}]")
        previous = bar


def _m1_spans(m1: Sequence, m15: list[tuple[Bar, frozenset[str]]], rule: TimeRule) -> tuple[list[int], list[int]]:
    """(first M1 index, end M1 index) of every M15 bar; every M1 sits in one bar and no bar is empty."""
    first = [0] * len(m15)
    end = [0] * len(m15)
    bar_index = 0
    for index, bar in enumerate(m1):
        opened = bar_open(bar.time_raw, 15, rule)
        while bar_index < len(m15) and m15[bar_index][0].time_raw < opened:
            if end[bar_index] == 0:
                raise BacktestError(f"m15[{bar_index}] has no M1 bar")
            bar_index += 1
        if bar_index == len(m15) or m15[bar_index][0].time_raw != opened:
            raise BacktestError(f"m1[{index}] is not inside any M15 bar")
        if end[bar_index] == 0:
            first[bar_index] = index
        end[bar_index] = index + 1
    if bar_index != len(m15) - 1 or end[bar_index] == 0:
        raise BacktestError(f"m15[{min(bar_index + 1, len(m15) - 1)}] has no M1 bar")
    return first, end


@dataclass(frozen=True)
class _Open:
    """A position that run holds: the plan without its exit, its stop and the bar that decided it."""

    side: Side
    entry_index: int
    decision_bar: int
    stop_distance: Decimal
    stop: Decimal
    lots: Decimal
    risk_money: Decimal
    actual_risk: Decimal | None


def run(
    m1: Sequence[Bar],
    m15: Sequence[object],
    params: H001Params,
    model: CostModel,
    sizer: Sizer,
    equity: Decimal,
    rule: TimeRule,
    rollover: Rollover,
    *,
    sides: frozenset[Side] = frozenset({"long", "short"}),
) -> Result:
    """Every H001 trade and skip over the bars, with the realized equity curve."""
    m1 = _sequence(m1, "m1")
    m15 = _sequence(m15, "m15")
    for index, bar in enumerate(m1):
        exact(bar, Bar, f"m1[{index}]")
    bars15 = _m15_shape(m15)
    exact(params, H001Params, "params")
    exact(model, CostModel, "model")
    if not callable(sizer):
        raise TypeError("sizer must be callable")
    exact(equity, Decimal, "equity")
    exact(rule, TimeRule, "rule")
    exact(rollover, Rollover, "rollover")
    check_flags(sides, "sides")
    if not m1 or not m15:
        raise BacktestError("m1 and m15 must not be empty")
    finite(equity, "equity")
    if equity <= 0:
        raise BacktestError("the starting equity must be positive")
    if not sides or not sides <= SIDES:
        raise BacktestError("sides must be a non-empty subset of {'long', 'short'}")
    _check_m1(m1, rule)
    _check_m15(bars15, rule)
    first, end = _m1_spans(m1, bars15, rule)
    try:
        rows = indicators(m15, params)
    except Overflow as error:
        raise too_large(error) from error
    return _Run(m1, bars15, rows, first, end, params, model, sizer, equity, rollover, sides).result()


class _Run:
    """The state of one run: the held position, equity, trades, skips and equity points."""

    def __init__(self, m1, bars15, rows, first, end, params, model, sizer, equity, rollover, sides) -> None:
        self.m1, self.bars15, self.rows, self.first, self.end = m1, bars15, rows, first, end
        self.params, self.model, self.sizer, self.rollover, self.sides = params, model, sizer, rollover, sides
        self.equity = equity
        self.open: _Open | None = None
        self.trades: list[Trade] = []
        self.skips: list[Skip] = []
        self.points: list[tuple[int, Decimal]] = [(m1[0].time_raw, equity)]

    def result(self) -> Result:
        last = len(self.bars15) - 1
        for t in range(len(self.bars15)):
            held = self.open
            if held is not None and self._stopped(held, t):
                self._close(held, None, t)  # step 1: the stop M1 is inside bar t
            if t == last:
                held = self.open
                if held is not None:
                    self._close(held, None, last)  # step 6: end of data
                break
            self._decide(t)
        return Result(tuple(self.trades), tuple(self.skips), tuple(self.points), BACKTEST_VERSION, STRATEGY_VERSION)

    def _stopped(self, held: _Open, t: int) -> bool:
        try:
            return any(stop_fill(held.side, self.m1[index], held.stop, self.model) is not None
                       for index in range(self.first[t], self.end[t]))
        except Overflow as error:
            raise too_large(error) from error

    def _decide(self, t: int) -> None:
        held = self.open
        position = "flat" if held is None else held.side
        try:
            decision = decide(self.rows, t, position, self.bars15[t + 1][0].time_utc, self.params)
        except Overflow as error:
            raise too_large(error) from error
        time_raw = self.bars15[t][0].time_raw
        if decision.action == "exit" and held is not None:
            self._close(held, self.first[t + 1], t + 1)  # step 3: the open of the first M1 of t+1
        elif decision.action == "skip":
            self.skips.append(Skip(time_raw, decision.reasons))
        elif decision.action in ("enter_long", "enter_short"):
            side: Side = "long" if decision.action == "enter_long" else "short"
            if side in self.sides:
                self._enter(t, side, decision.stop_distance, time_raw)

    def _enter(self, t: int, side: Side, stop_distance: Decimal, time_raw: int) -> None:
        if self.equity <= 0:
            self.skips.append(Skip(time_raw, ("equity_exhausted",)))
            return
        sized = self.sizer(self.equity, stop_distance)
        exact(sized, SizedLots, "the sizer's result")
        if sized.lots is None:
            self.skips.append(Skip(time_raw, (sized.reason,)))
            return
        check_volume(sized.lots, self.model)
        entry_index = self.first[t + 1]
        try:
            stop = stop_price(side, self.m1[entry_index], stop_distance, self.model)
        except Overflow as error:
            raise too_large(error) from error
        self.open = _Open(side, entry_index, t, stop_distance, stop, sized.lots, sized.risk_money, sized.actual_risk)

    def _close(self, held: _Open, exit_index: int | None, exit_bar: int) -> None:
        """Build the trade with the simulate_trade fill code; exit_bar is the M15 bar of the closing M1.

        exit_index None is a stop or the end of data: the fill code scans from the entry M1 and finds the
        same stop M1 that step 1 found (nothing earlier triggered), or reaches the last M1.
        """
        flags: frozenset[str] = frozenset().union(*(self.bars15[u][1] for u in range(held.decision_bar, exit_bar + 1)))
        plan = Plan(held.entry_index, held.side, held.stop_distance, held.lots, self.model, self.rollover,
                    held.risk_money, held.actual_risk, exit_index, flags)
        trade = simulate(self.m1, plan, checked=True)
        self.trades.append(trade)
        try:
            with localcontext(CONTEXT):
                self.equity = self.equity + trade.net_money
        except Overflow as error:
            raise too_large(error) from error
        self.points.append((trade.exit_time_raw, self.equity))
        self.open = None
