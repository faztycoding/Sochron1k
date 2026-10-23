"""Charges in account currency (USD) as Decimals computed in the module's own context.

Conventions (docs/contracts/CORE-002-costs.md): a charge is positive when the trader pays and
negative when the trader receives; the spread is paid once per round trip, at the side that
crosses from bid to ask (the buy), because the data are bid bars; every charge is multiplied by
the model's stress_factor; nights are counts supplied by the caller, this module never reads a
clock. Wrong scalar types raise TypeError; bad values raise the CostsError family.

Every public function checks the model first, once (docs/contracts/CORE-004-costs-hardening.md
AC-03), then its own arguments; the private helpers below take values that are already checked,
so a model's provenance is read exactly once per call.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Literal

from .errors import BadNights, BadPoints, BadR, BadSides, BadVolume, CostsError
from .model import CONTEXT, CostModel, bounded_decimal, is_int, require_exact, validate_model

Side = Literal["long", "short"]
_ZERO = Decimal("0")


@dataclass(frozen=True)
class CostBreakdown:
    """The four charges of one round trip and their total, all in USD."""

    spread: Decimal
    commission: Decimal
    slippage: Decimal
    swap: Decimal
    total: Decimal
    stress_factor: Decimal

    def __post_init__(self) -> None:
        for name in ("spread", "commission", "slippage", "swap", "total", "stress_factor"):
            bounded_decimal(getattr(self, name), name, CostsError)
        with localcontext(CONTEXT):
            expected = self.spread + self.commission + self.slippage + self.swap
            consistent = self.total == expected
        if not consistent:
            raise CostsError(f"total {self.total} is not the ordered sum of the components {expected}")


def _lots(lots: Decimal) -> Decimal:
    return bounded_decimal(lots, "lots", BadVolume)


def _points(points: int | Decimal, name: str) -> Decimal:
    # An int converts exactly and never reaches a rational conversion, so only Decimals are size-bounded.
    if is_int(points):
        return Decimal(points)
    if type(points) is not Decimal:
        raise TypeError(f"{name} must be exactly an int or Decimal, not {type(points).__name__}")
    return bounded_decimal(points, name, BadPoints)


def _count(value: int, name: str) -> int:
    if not is_int(value):
        raise TypeError(f"{name} must be exactly int, not {type(value).__name__}")
    return value


def _side(side: Side) -> Side:
    require_exact(side, str, "side")
    if side not in ("long", "short"):
        raise CostsError(f"side must be 'long' or 'short', got {side!r}")
    return side


def _sides(sides: int) -> int:
    sides = _count(sides, "sides")
    if sides < 0:
        # The value is not echoed: a huge int exceeds Python's int-to-str limit (AC-06).
        raise BadSides("sides cannot be negative")
    return sides


def _on_grid(lots: Decimal, step: Decimal) -> bool:
    """Whether lots is an integer multiple of step, decided with exact integer arithmetic.

    Both values are size-bounded first, so the rational conversion stays bounded too.
    """
    lots_num, lots_den = lots.as_integer_ratio()
    step_num, step_den = step.as_integer_ratio()
    return (lots_num * step_den) % (step_num * lots_den) == 0


def _volume(lots: Decimal, model: CostModel) -> Decimal:
    """check_volume for a model that is already validated."""
    lots = _lots(lots)
    if not model.volume_min <= lots <= model.volume_max:
        raise BadVolume(f"lots {lots} outside [{model.volume_min}, {model.volume_max}]")
    if not _on_grid(lots, model.volume_step):
        raise BadVolume(f"lots {lots} is not a multiple of {model.volume_step}")
    return lots


def _money(value: Decimal, lots: Decimal, model: CostModel) -> Decimal:
    """points x point x contract_size x lots x stress_factor for checked values."""
    with localcontext(CONTEXT):
        return value * model.point * model.contract_size * lots * model.stress_factor


def check_volume(lots: Decimal, model: CostModel) -> Decimal:
    """The same lots when they are finite, in [volume_min, volume_max] and on the volume_step grid."""
    validate_model(model)
    return _volume(lots, model)


def points_to_money(points: int | Decimal, lots: Decimal, model: CostModel) -> Decimal:
    """points x point x contract_size x lots x stress_factor; points may carry a sign."""
    validate_model(model)
    value = _points(points, "points")
    return _money(value, _volume(lots, model), model)


def _spread_points(spread_points: int | None, model: CostModel, name: str) -> Decimal:
    """A bar's spread in points: an int, or None for a bar that carried none (the fallback applies)."""
    if spread_points is None:
        return Decimal(model.spread_fallback_points)
    if not is_int(spread_points):
        raise TypeError(f"{name} must be exactly an int or None, not {type(spread_points).__name__}")
    if spread_points < 0:
        # The value is not echoed: a huge int exceeds Python's int-to-str limit (AC-06).
        raise BadPoints(f"{name} cannot be negative")
    return Decimal(spread_points)


def spread_charge(spread_points: int | None, lots: Decimal, model: CostModel) -> Decimal:
    """The spread of one fill in USD; None means the bar carried no spread, so the fallback applies."""
    validate_model(model)
    value = _spread_points(spread_points, model, "spread_points")
    return _money(value, _volume(lots, model), model)


def _slippage(lots: Decimal, model: CostModel, sides: int) -> Decimal:
    with localcontext(CONTEXT):
        return _money(Decimal(model.slippage_points_per_side), lots, model) * sides


def _commission(lots: Decimal, model: CostModel, sides: int) -> Decimal:
    with localcontext(CONTEXT):
        return model.commission_per_lot_per_side * lots * sides * model.stress_factor


def slippage_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal:
    """Slippage for the given number of market fills (entry and exit by default)."""
    validate_model(model)
    sides = _sides(sides)
    return _slippage(_volume(lots, model), model, sides)


def commission_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal:
    """Commission for the given number of fills."""
    validate_model(model)
    sides = _sides(sides)
    return _commission(_volume(lots, model), model, sides)


def _nights(nights: int, triple_nights: int) -> tuple[int, int]:
    nights = _count(nights, "nights")
    triple_nights = _count(triple_nights, "triple_nights")
    if nights < 0 or triple_nights < 0 or triple_nights > nights:
        # The values are not echoed: a huge int exceeds Python's int-to-str limit (AC-06).
        raise BadNights("nights and triple_nights must be >= 0 with triple_nights <= nights")
    return nights, triple_nights


def _swap(side: Side, lots: Decimal, nights: int, triple_nights: int, model: CostModel) -> Decimal:
    points = model.swap_long_points_per_night if side == "long" else model.swap_short_points_per_night
    multiplier = nights - triple_nights + 3 * triple_nights
    with localcontext(CONTEXT):
        return _ZERO - _money(points, lots, model) * multiplier


def swap_charge(side: Side, lots: Decimal, nights: int, triple_nights: int, model: CostModel) -> Decimal:
    """Swap for a position charged on nights rollovers, triple_nights of them three times; positive = paid."""
    validate_model(model)
    side = _side(side)
    nights, triple_nights = _nights(nights, triple_nights)
    return _swap(side, _volume(lots, model), nights, triple_nights, model)


def round_trip_cost(
    side: Side,
    lots: Decimal,
    entry_spread_points: int | None,
    exit_spread_points: int | None,
    nights: int,
    triple_nights: int,
    model: CostModel,
    sides: int = 2,
) -> CostBreakdown:
    """All charges of one round trip; the spread is taken from the fill that crosses to the ask."""
    validate_model(model)
    side = _side(side)
    entry = _spread_points(entry_spread_points, model, "entry_spread_points")
    exit_ = _spread_points(exit_spread_points, model, "exit_spread_points")
    lots = _volume(lots, model)
    sides = _sides(sides)
    nights, triple_nights = _nights(nights, triple_nights)
    spread = _money(entry if side == "long" else exit_, lots, model)
    commission = _commission(lots, model, sides)
    slippage = _slippage(lots, model, sides)
    swap = _swap(side, lots, nights, triple_nights, model)
    with localcontext(CONTEXT):
        total = spread + commission + slippage + swap
    return CostBreakdown(spread, commission, slippage, swap, total, model.stress_factor)


def r_multiple(money: Decimal, r: Decimal) -> Decimal:
    """money expressed in units of R (the risk per trade), at precision 28."""
    if type(money) is not Decimal or type(r) is not Decimal:
        raise TypeError("money and r must be exactly Decimal")
    bounded_decimal(money, "money", CostsError)
    bounded_decimal(r, "R", BadR)
    if r <= 0:
        raise BadR("R must be positive")
    with localcontext(CONTEXT):
        return money / r
