"""H001 parameters within the registered ranges (docs/hypotheses/H001-m15-momentum-breakout.md section 4)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal
from types import MappingProxyType
from typing import Literal

Variant = Literal["A", "B", "C"]
STRATEGY_ID = "H001"
STRATEGY_VERSION = "H001-v1"

# The module's own arithmetic (contract D1): precision 28, ROUND_HALF_EVEN, every operation rounded
# in the written order; the caller's Decimal context is never read or changed.
CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


class StrategyError(ValueError):
    """A strategy input of the right type with a value outside the contract."""


def exact(value: object, kind: type, name: str) -> None:
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")


def _int_in(value: object, name: str, low: int, high: int) -> None:
    exact(value, int, name)
    if not low <= value <= high:
        raise StrategyError(f"{name} must be {low} to {high}")


def _decimal_in(value: object, name: str, low: str, high: str) -> None:
    exact(value, Decimal, name)
    if not value.is_finite():
        raise StrategyError(f"{name} must be finite")
    if not Decimal(low) <= value <= Decimal(high):
        raise StrategyError(f"{name} must be {low} to {high}")


@dataclass(frozen=True)
class H001Params:
    """One H001 parameter set; out-of-range values are refused so no run escapes the variant budget."""

    variant: Variant
    f: int
    s: int
    n: int
    theta: Decimal
    N: int
    M: int
    k: Decimal

    def __post_init__(self) -> None:
        exact(self.variant, str, "variant")
        for name in ("f", "s", "n", "N", "M"):
            exact(getattr(self, name), int, name)
        exact(self.theta, Decimal, "theta")
        exact(self.k, Decimal, "k")
        if self.variant not in ("A", "B", "C"):
            raise StrategyError("variant must be 'A', 'B' or 'C'")
        _int_in(self.f, "f", 8, 24)
        _int_in(self.s, "s", 32, 96)
        if self.s < 3 * self.f:
            raise StrategyError("s must be at least 3f")
        _int_in(self.n, "n", 10, 30)
        _decimal_in(self.theta, "theta", "0.25", "1.00")
        _int_in(self.N, "N", 48, 192)
        _int_in(self.M, "M", 24, 96)
        if self.M > self.N:
            raise StrategyError("M must not exceed N")
        _decimal_in(self.k, "k", "1.5", "3.0")


H001_DEFAULTS = MappingProxyType(
    {variant: H001Params(variant, 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0")) for variant in ("A", "B", "C")}
)
