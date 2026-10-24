"""The H001 simulator on checked bid bars (docs/contracts/CORE-007-backtest.md).

simulate_trade() fills one round trip on M1 bars under the fill and stop table; run() drives
strategy.decide over M15 bars and builds every trade with the same fill code. Prices are bid, costs
come once per trade from sochron.costs, R is the sizer's formula risk. Pure: no I/O, no clock, no
randomness; time goes through sochron.timebase only.
"""

from .engine import run
from .model import BACKTEST_VERSION, BacktestError, Result, Rollover, Side, SizedLots, Sizer, Skip, Trade
from .trade import simulate_trade

__all__ = [
    "BACKTEST_VERSION",
    "BacktestError",
    "Result",
    "Rollover",
    "Side",
    "SizedLots",
    "Sizer",
    "Skip",
    "Trade",
    "run",
    "simulate_trade",
]
