"""Charges in account currency (USD) as Decimals computed in the module's own context.

Conventions (docs/contracts/CORE-002-costs.md): a charge is positive when the trader pays and
negative when the trader receives; the spread is paid once per round trip, at the side that
crosses from bid to ask (the buy), because the data are bid bars; every charge is multiplied by
the model's stress_factor; nights are counts supplied by the caller, this module never reads a
clock. Wrong scalar types raise TypeError; bad values raise the CostsError family.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Literal

from .errors import BadNights, BadPoints, BadR, BadSides, BadVolume, CostsError
from .model import CONTEXT, CostModel

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


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _lots(lots: Decimal) -> Decimal:
    if not isinstance(lots, Decimal):
        raise TypeError(f"lots must be a Decimal, not {type(lots).__name__}")
    if not lots.is_finite():
        raise BadVolume(f"lots must be finite, got {lots}")
    return lots


def _points(points: int | Decimal, name: str) -> Decimal:
    if not isinstance(points, Decimal) and not _is_int(points):
        raise TypeError(f"{name} must be an int or Decimal, not {type(points).__name__}")
    value = Decimal(points)
    if not value.is_finite():
        raise BadPoints(f"{name} must be finite, got {value}")
    return value


def _count(value: int, name: str) -> int:
    if not _is_int(value):
        raise TypeError(f"{name} must be an int, not {type(value).__name__}")
    return value


def _side(side: Side) -> Side:
    if not isinstance(side, str):
        raise TypeError(f"side must be a str, not {type(side).__name__}")
    if side not in ("long", "short"):
        raise CostsError(f"side must be 'long' or 'short', got {side!r}")
    return side


def _sides(sides: int) -> int:
    sides = _count(sides, "sides")
    if sides < 0:
        raise BadSides(f"sides cannot be negative, got {sides}")
    return sides


def _on_grid(lots: Decimal, step: Decimal) -> bool:
    """Whether lots is an integer multiple of step, decided with exact integer arithmetic."""
    lots_num, lots_den = lots.as_integer_ratio()
    step_num, step_den = step.as_integer_ratio()
    return (lots_num * step_den) % (step_num * lots_den) == 0


def check_volume(lots: Decimal, model: CostModel) -> Decimal:
    """The same lots when they are finite, in [volume_min, volume_max] and on the volume_step grid."""
    lots = _lots(lots)
    if not model.volume_min <= lots <= model.volume_max:
        raise BadVolume(f"lots {lots} outside [{model.volume_min}, {model.volume_max}]")
    if not _on_grid(lots, model.volume_step):
        raise BadVolume(f"lots {lots} is not a multiple of {model.volume_step}")
    return lots


def points_to_money(points: int | Decimal, lots: Decimal, model: CostModel) -> Decimal:
    """points x point x contract_size x lots x stress_factor; points may carry a sign."""
    value = _points(points, "points")
    lots = check_volume(lots, model)
    with localcontext(CONTEXT):
        return value * model.point * model.contract_size * lots * model.stress_factor


def _spread_points(spread_points: int | None, model: CostModel, name: str) -> Decimal:
    """A bar's spread in points: an int, or None for a bar that carried none (the fallback applies)."""
    if spread_points is None:
        return Decimal(model.spread_fallback_points)
    if not _is_int(spread_points):
        raise TypeError(f"{name} must be an int or None, not {type(spread_points).__name__}")
    if spread_points < 0:
        raise BadPoints(f"{name} cannot be negative, got {spread_points}")
    return Decimal(spread_points)


def spread_charge(spread_points: int | None, lots: Decimal, model: CostModel) -> Decimal:
    """The spread of one fill in USD; None means the bar carried no spread, so the fallback applies."""
    return points_to_money(_spread_points(spread_points, model, "spread_points"), lots, model)


def slippage_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal:
    """Slippage for the given number of market fills (entry and exit by default)."""
    sides = _sides(sides)
    with localcontext(CONTEXT):
        return points_to_money(model.slippage_points_per_side, lots, model) * sides


def commission_charge(lots: Decimal, model: CostModel, sides: int = 2) -> Decimal:
    """Commission for the given number of fills."""
    sides = _sides(sides)
    lots = check_volume(lots, model)
    with localcontext(CONTEXT):
        return model.commission_per_lot_per_side * lots * sides * model.stress_factor


def swap_charge(side: Side, lots: Decimal, nights: int, triple_nights: int, model: CostModel) -> Decimal:
    """Swap for a position charged on nights rollovers, triple_nights of them three times; positive = paid."""
    side = _side(side)
    nights = _count(nights, "nights")
    triple_nights = _count(triple_nights, "triple_nights")
    if nights < 0 or triple_nights < 0 or triple_nights > nights:
        raise BadNights(f"nights {nights} and triple_nights {triple_nights} must be >= 0 with triple_nights <= nights")
    points = model.swap_long_points_per_night if side == "long" else model.swap_short_points_per_night
    multiplier = nights - triple_nights + 3 * triple_nights
    with localcontext(CONTEXT):
        return _ZERO - points_to_money(points, lots, model) * multiplier


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
    side = _side(side)
    entry = _spread_points(entry_spread_points, model, "entry_spread_points")
    exit_ = _spread_points(exit_spread_points, model, "exit_spread_points")
    spread = points_to_money(entry if side == "long" else exit_, lots, model)
    commission = commission_charge(lots, model, sides)
    slippage = slippage_charge(lots, model, sides)
    swap = swap_charge(side, lots, nights, triple_nights, model)
    with localcontext(CONTEXT):
        total = spread + commission + slippage + swap
    return CostBreakdown(spread, commission, slippage, swap, total, model.stress_factor)


def r_multiple(money: Decimal, r: Decimal) -> Decimal:
    """money expressed in units of R (the risk per trade), at precision 28."""
    if not isinstance(money, Decimal) or not isinstance(r, Decimal):
        raise TypeError("money and r must be Decimals")
    if not money.is_finite():
        raise CostsError(f"money must be finite, got {money}")
    if not r.is_finite() or r <= 0:
        raise BadR(f"R must be finite and positive, got {r}")
    with localcontext(CONTEXT):
        return money / r
