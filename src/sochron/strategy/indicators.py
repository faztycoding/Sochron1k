"""H001 indicators on closed M15 bars: EMA, Wilder ATR, trend score, Donchian channels, spread median.

Row t uses bars[0..t] only (no look-ahead). Every rule is the contract's (CORE-006 D1-D3 and v1.1):
- EMA_p[0] = close[0]; EMA_p[t] = alpha x close[t] + (1 - alpha) x EMA_p[t-1], alpha = 2 / (p + 1),
  alpha and 1 - alpha computed once, every operation rounded in the module context.
- TR[0] = high - low; TR[t] = max(high - low, |high - close[t-1]|, |low - close[t-1]|).
- ATR is None before t = n - 1; ATR[n-1] is the mean of TR[0..n-1]; then
  ATR[t] = (ATR[t-1] x (n - 1) + TR[t]) / n.
- TS = (EMA_f - EMA_s) / ATR, None when ATR is None or 0.
- HH/LL over bars t-N..t-1 (bar t excluded), None before t = N (and M for the exit channel).
- spread_median_96 = mean of the 48th and 49th smallest of spread[t-96..t-1]; None while t < 96 or
  while any of them is None.
- lookback_flags = the defect flags of bars t-L+1..t without "incomplete", L = max(n, 96, N, M) + 1
  (V-A: max(n, 96) + 1).
- warm = t >= max(3s, N+1, M+1, 97, n+1).
Bars are taken by shape (an object with .bar, exactly sochron.core.Bar, and .flags, a frozenset):
the module map lets strategy import core and timebase only.
"""

from bisect import bisect_left, insort
from collections import Counter, deque
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext

from sochron.core import Bar

from .params import CONTEXT, H001Params, StrategyError, exact

_MEDIAN_SPAN = 96
_IGNORED_FLAGS = frozenset({"incomplete"})


@dataclass(frozen=True)
class IndicatorRow:
    """The indicator values at one closed M15 bar."""

    ema_f: Decimal
    ema_s: Decimal
    atr: Decimal | None
    ts: Decimal | None
    hh_n: Decimal | None
    ll_n: Decimal | None
    hh_m: Decimal | None
    ll_m: Decimal | None
    close: Decimal
    spread: int | None
    spread_median_96: Decimal | None
    warm: bool
    lookback_flags: frozenset[str]


def _bars(bars: object) -> list[tuple[Bar, frozenset[str]]]:
    if not isinstance(bars, Sequence) or isinstance(bars, (str, bytes)):
        raise TypeError(f"bars must be a sequence of aggregated bars, not {type(bars).__name__}")
    checked = []
    for item in bars:
        raw_bar = getattr(item, "bar", None)
        raw_flags = getattr(item, "flags", None)
        bar = exact(raw_bar, Bar, "an aggregated bar's .bar")
        flags = exact(raw_flags, frozenset, "an aggregated bar's .flags")
        for flag in flags:
            exact(flag, str, "a flag")
        if bar.timeframe != 15:
            raise StrategyError("H001 decides on M15 bars")
        checked.append((bar, flags))
    return checked


class _Window:
    """Max and min of the last `span` values before the current index, in O(1) amortized."""

    def __init__(self, span: int) -> None:
        self.span = span
        self.highs: deque[tuple[int, Decimal]] = deque()
        self.lows: deque[tuple[int, Decimal]] = deque()

    def push(self, index: int, high: Decimal, low: Decimal) -> None:
        while self.highs and self.highs[-1][1] <= high:
            self.highs.pop()
        self.highs.append((index, high))
        while self.lows and self.lows[-1][1] >= low:
            self.lows.pop()
        self.lows.append((index, low))

    def extremes(self, t: int) -> tuple[Decimal | None, Decimal | None]:
        """HH and LL of bars t-span..t-1; call after pushing bar t-1 and before pushing bar t."""
        if t < self.span:
            return None, None
        while self.highs[0][0] < t - self.span:
            self.highs.popleft()
        while self.lows[0][0] < t - self.span:
            self.lows.popleft()
        return self.highs[0][1], self.lows[0][1]


def indicators(bars: Sequence[object], params: H001Params) -> tuple[IndicatorRow, ...]:
    """One IndicatorRow per bar; row t depends on bars[0..t] only."""
    exact(params, H001Params, "params")
    items = _bars(bars)
    span = max(params.n, _MEDIAN_SPAN) + 1 if params.variant == "A" else max(params.n, _MEDIAN_SPAN, params.N, params.M) + 1
    warm_from = max(3 * params.s, params.N + 1, params.M + 1, _MEDIAN_SPAN + 1, params.n + 1)
    entry = _Window(params.N)
    exit_ = _Window(params.M)
    spreads: list[int] = []  # sorted known spreads of the last 96 bars
    unknown = 0  # how many of the last 96 spreads are None
    flags: Counter[str] = Counter()
    rows: list[IndicatorRow] = []
    with localcontext(CONTEXT):
        alpha_f = Decimal(2) / Decimal(params.f + 1)
        keep_f = Decimal(1) - alpha_f
        alpha_s = Decimal(2) / Decimal(params.s + 1)
        keep_s = Decimal(1) - alpha_s
        ema_f = ema_s = atr = Decimal(0)
        tr_sum = Decimal(0)
        for t, (bar, bar_flags) in enumerate(items):
            close = bar.close
            if t == 0:
                ema_f = ema_s = close
                tr = bar.high - bar.low
            else:
                ema_f = alpha_f * close + keep_f * ema_f
                ema_s = alpha_s * close + keep_s * ema_s
                previous_close = items[t - 1][0].close
                tr = max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))
            if t < params.n - 1:
                tr_sum = tr_sum + tr
                atr_t = None
            elif t == params.n - 1:
                tr_sum = tr_sum + tr
                atr = tr_sum / Decimal(params.n)
                atr_t = atr
            else:
                atr = (atr * Decimal(params.n - 1) + tr) / Decimal(params.n)
                atr_t = atr
            ts = None if atr_t is None or atr_t.is_zero() else (ema_f - ema_s) / atr_t
            hh_n, ll_n = entry.extremes(t)
            hh_m, ll_m = exit_.extremes(t)
            if t < _MEDIAN_SPAN or unknown:
                median = None
            else:
                median = (Decimal(spreads[_MEDIAN_SPAN // 2 - 1]) + Decimal(spreads[_MEDIAN_SPAN // 2])) / Decimal(2)
            flags.update(bar_flags - _IGNORED_FLAGS)
            if t >= span:
                for flag in items[t - span][1] - _IGNORED_FLAGS:
                    flags[flag] -= 1
                    if not flags[flag]:
                        del flags[flag]  # keep only flags still in the lookback, so each row stays O(window)
            lookback = frozenset(flags)
            rows.append(
                IndicatorRow(ema_f, ema_s, atr_t, ts, hh_n, ll_n, hh_m, ll_m, close, bar.spread, median,
                             t >= warm_from, lookback)
            )
            # Bar t joins the windows that rows t+1.. read (bar t is excluded from its own channels).
            entry.push(t, bar.high, bar.low)
            exit_.push(t, bar.high, bar.low)
            if bar.spread is None:
                unknown += 1
            else:
                insort(spreads, bar.spread)
            if t >= _MEDIAN_SPAN:
                leaving = items[t - _MEDIAN_SPAN][0].spread
                if leaving is None:
                    unknown -= 1
                else:
                    spreads.pop(bisect_left(spreads, leaving))
    return tuple(rows)
