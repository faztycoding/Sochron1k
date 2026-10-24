"""The value types of sochron.backtest (CORE-007): versions, errors, SizedLots, Rollover, Trade, Skip, Result.

Every type is a frozen dataclass. SizedLots and Rollover check themselves when built: a wrong type is
TypeError and a right type with a value outside the contract is BacktestError.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Literal

from sochron.costs import CostBreakdown
from sochron.timebase import to_zone

BACKTEST_VERSION = "backtest-v1"

Side = Literal["long", "short"]
SIDES: frozenset[str] = frozenset({"long", "short"})
ExitReason = Literal["signal", "stop", "end_of_data"]

_ZONE_PROBE = datetime(2026, 1, 1, tzinfo=UTC)


class BacktestError(ValueError):
    """A value of the right type that the backtest contract does not allow."""


def exact(value: object, kind: type, name: str) -> None:
    """TypeError unless value is exactly of kind (no subclass, no bool for int)."""
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")


def exact_optional(value: object, kind: type, name: str) -> None:
    if value is not None:
        exact(value, kind, name)


def finite(value: Decimal | None, name: str) -> None:
    """BacktestError for NaN, sNaN and infinities; None passes."""
    if value is not None and not value.is_finite():
        raise BacktestError(f"{name} must be finite")


@dataclass(frozen=True)
class SizedLots:
    """What the sizer returns: lots (None = do not trade), the formula R, the risk after rounding, why."""

    lots: Decimal | None
    risk_money: Decimal
    actual_risk: Decimal | None
    reason: str

    def __post_init__(self) -> None:
        exact_optional(self.lots, Decimal, "lots")
        exact(self.risk_money, Decimal, "risk_money")
        exact_optional(self.actual_risk, Decimal, "actual_risk")
        exact(self.reason, str, "reason")
        for name in ("lots", "risk_money", "actual_risk"):
            finite(getattr(self, name), name)
        if self.risk_money <= 0:
            raise BacktestError("risk_money must be positive")
        if self.lots is None and self.actual_risk is not None:
            raise BacktestError("actual_risk must be None when lots is None")
        if self.actual_risk is not None and self.actual_risk <= 0:
            raise BacktestError("actual_risk must be None or positive")
        if not self.reason:
            raise BacktestError("reason must not be empty")


Sizer = Callable[[Decimal, Decimal], SizedLots]  # (equity when the trade opens, stop_distance)


@dataclass(frozen=True)
class Rollover:
    """The daily swap rollover: a wall time in whole minutes in an IANA zone (D4 [A])."""

    zone: str
    at: time

    def __post_init__(self) -> None:
        exact(self.zone, str, "zone")
        exact(self.at, time, "at")
        if self.at.tzinfo is not None or self.at.second or self.at.microsecond:
            raise BacktestError("at must be a wall time in whole minutes without tzinfo")
        try:
            to_zone(_ZONE_PROBE, self.zone)
        except (KeyError, ValueError, OSError):
            # The zone lookup raises ZoneInfoNotFoundError (a KeyError), ValueError for a malformed
            # key and OSError for a key that names a directory.
            raise BacktestError(f"unknown zone {self.zone!r}") from None


@dataclass(frozen=True)
class Trade:
    """One simulated round trip on bid prices with its costs and R-multiple."""

    side: Side
    entry_time_raw: int
    entry_bid: Decimal
    entry_spread_points: int
    exit_time_raw: int
    exit_bid: Decimal
    exit_spread_points: int
    lots: Decimal
    stop_distance: Decimal
    stop_price: Decimal
    exit_reason: ExitReason
    ambiguous: bool
    nights: int
    triple_nights: int
    costs: CostBreakdown
    gross_money: Decimal
    net_money: Decimal
    risk_money: Decimal
    actual_risk: Decimal | None
    r: Decimal
    data_flags: frozenset[str]


@dataclass(frozen=True)
class Skip:
    """An entry the run did not take, at the decision bar's raw time, with every reason."""

    time_raw: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Result:
    """Every trade and skip of a run, the realized equity curve and the versions that produced them."""

    trades: tuple[Trade, ...]
    skips: tuple[Skip, ...]
    equity: tuple[tuple[int, Decimal], ...]
    backtest_version: str
    strategy_version: str
