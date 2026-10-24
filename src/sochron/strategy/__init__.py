"""The H001 strategy as pure functions shared by backtest and Demo (docs/contracts/CORE-006-strategy-h001.md).

indicators() turns closed M15 bars into IndicatorRow values; decide() turns rows into one Decision per
bar. No I/O, no clock, no randomness and no MetaTrader5: the caller passes every input, including the
open time of the next bar for the New York entry window.
"""

from .h001 import Decision, Position, decide
from .indicators import IndicatorRow, indicators
from .params import H001_DEFAULTS, STRATEGY_ID, STRATEGY_VERSION, H001Params, StrategyError, Variant

__all__ = [
    "Decision",
    "H001Params",
    "H001_DEFAULTS",
    "IndicatorRow",
    "Position",
    "STRATEGY_ID",
    "STRATEGY_VERSION",
    "StrategyError",
    "Variant",
    "decide",
    "indicators",
]
