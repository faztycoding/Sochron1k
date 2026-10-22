"""sochron.costs: the one cost model (CORE-002).

Spread, commission, slippage and swap as Decimal charges in USD computed in the module's own
context (precision 28, ROUND_HALF_EVEN), a stress() that scales every component, a provenance
record for every constant, and H001_COSTS for XAUUSDm. Pure: no I/O, no clock, no MetaTrader5;
nights are inputs. See docs/contracts/CORE-002-costs.md.
"""

from .charges import (
    CostBreakdown,
    Side,
    check_volume,
    commission_charge,
    points_to_money,
    r_multiple,
    round_trip_cost,
    slippage_charge,
    spread_charge,
    swap_charge,
)
from .errors import BadNights, BadPoints, BadProvenance, BadR, BadSides, BadStress, BadVolume, CostsError
from .model import (
    CONTEXT,
    H001_COSTS,
    PROVENANCE_FIELDS,
    STATUSES,
    CostModel,
    Provenance,
    Status,
    stress,
    unknowns,
)

__all__ = [
    "BadNights",
    "BadPoints",
    "BadProvenance",
    "BadR",
    "BadSides",
    "BadStress",
    "BadVolume",
    "CONTEXT",
    "CostBreakdown",
    "CostModel",
    "CostsError",
    "H001_COSTS",
    "PROVENANCE_FIELDS",
    "Provenance",
    "STATUSES",
    "Side",
    "Status",
    "check_volume",
    "commission_charge",
    "points_to_money",
    "r_multiple",
    "round_trip_cost",
    "slippage_charge",
    "spread_charge",
    "stress",
    "swap_charge",
    "unknowns",
]
