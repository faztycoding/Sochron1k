"""The cost model: every constant carries its provenance.

H001_COSTS encodes H001 section 6 and the XAUUSDm specification measured in SPIKE-001 on
2026-10-21. Values with status "assumed" are the owner's [A] placeholders from H001; the swap
values are today's specification and say nothing about 2018-2024, which stays UNKNOWN
(docs/architecture.md section 13a, R1 data selection gate). All arithmetic runs in the module's
own Decimal context (precision 28, ROUND_HALF_EVEN), never the caller's.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from types import MappingProxyType
from typing import Literal, Mapping

from .errors import BadProvenance, BadStress, CostsError

Status = Literal["measured", "spec", "assumed", "unknown"]
STATUSES = frozenset({"measured", "spec", "assumed", "unknown"})
CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)

PROVENANCE_FIELDS = (
    "point",
    "contract_size",
    "volume_min",
    "volume_step",
    "volume_max",
    "spread_fallback_points",
    "commission_per_lot_per_side",
    "slippage_points_per_side",
    "swap_long_points_per_night",
    "swap_short_points_per_night",
    "triple_swap_weekday",
)
_DECIMAL_FIELDS = (
    "point",
    "contract_size",
    "volume_min",
    "volume_step",
    "volume_max",
    "commission_per_lot_per_side",
    "swap_long_points_per_night",
    "swap_short_points_per_night",
    "stress_factor",
)
_INT_FIELDS = ("spread_fallback_points", "slippage_points_per_side", "triple_swap_weekday")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class Provenance:
    """Where a constant came from: source, the date it was read, and how firm it is."""

    source: str
    as_of: date
    status: Status
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not isinstance(self.note, str):
            raise TypeError("source and note must be str")
        if not isinstance(self.as_of, date):
            raise TypeError("as_of must be a date")
        if self.status not in STATUSES:
            raise BadProvenance(f"status must be one of {sorted(STATUSES)}, got {self.status!r}")


@dataclass(frozen=True)
class CostModel:
    """Constants of one symbol's cost model, all with provenance; stress_factor scales every charge."""

    symbol: str
    point: Decimal
    contract_size: Decimal
    volume_min: Decimal
    volume_step: Decimal
    volume_max: Decimal
    spread_fallback_points: int
    commission_per_lot_per_side: Decimal
    slippage_points_per_side: int
    swap_long_points_per_night: Decimal
    swap_short_points_per_night: Decimal
    triple_swap_weekday: int
    provenance: Mapping[str, Provenance]
    stress_factor: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError("symbol must be str")
        for name in _DECIMAL_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be a Decimal, not {type(value).__name__}")
            if not value.is_finite():
                if name == "stress_factor":
                    raise BadStress("stress_factor must be finite")
                raise CostsError(f"{name} must be finite")
        for name in _INT_FIELDS:
            value = getattr(self, name)
            if not _is_int(value):
                raise TypeError(f"{name} must be an int, not {type(value).__name__}")
        if self.point <= 0 or self.contract_size <= 0 or self.volume_step <= 0 or self.volume_min <= 0:
            raise CostsError("point, contract_size, volume_step and volume_min must be positive")
        if self.volume_max < self.volume_min:
            raise CostsError("volume_max must not be below volume_min")
        if self.commission_per_lot_per_side < 0 or self.spread_fallback_points < 0 or self.slippage_points_per_side < 0:
            raise CostsError("commission, spread fallback and slippage cannot be negative")
        if not 0 <= self.triple_swap_weekday <= 6:
            raise CostsError("triple_swap_weekday must be 0 (Monday) to 6 (Sunday)")
        if self.stress_factor <= 0:
            raise BadStress(f"stress_factor must be positive, got {self.stress_factor}")
        keys = set(self.provenance)
        expected = set(PROVENANCE_FIELDS)
        if keys != expected:
            raise BadProvenance(
                f"provenance must cover exactly the 11 base fields; missing {sorted(expected - keys)}, extra {sorted(keys - expected)}"
            )
        for name, record in self.provenance.items():
            if not isinstance(record, Provenance):
                raise BadProvenance(f"provenance[{name!r}] must be a Provenance")
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))


def stress(model: CostModel, factor: Decimal | int = Decimal("2")) -> CostModel:
    """A copy of the model whose every charge is multiplied by factor; provenance is unchanged."""
    if not isinstance(factor, Decimal) and not _is_int(factor):
        raise TypeError(f"factor must be a Decimal or int, not {type(factor).__name__}")
    value = Decimal(factor)
    if not value.is_finite() or value <= 0:
        raise BadStress(f"stress factor must be finite and positive, got {value}")
    with localcontext(CONTEXT):
        return replace(model, stress_factor=model.stress_factor * value)


def unknowns(model: CostModel) -> tuple[str, ...]:
    """Names of the constants whose provenance status is assumed or unknown, sorted."""
    return tuple(sorted(name for name, p in model.provenance.items() if p.status in ("assumed", "unknown")))


_SPIKE = "docs/evidence/SPIKE-001.md"
_H001 = "docs/hypotheses/H001-m15-momentum-breakout.md"
_AS_OF = date(2026, 10, 21)
_SWAP_NOTE = "today's specification; the value for 2018-2024 history is UNKNOWN (13a R1 data selection)"

H001_COSTS = CostModel(
    symbol="XAUUSDm",
    point=Decimal("0.001"),
    contract_size=Decimal("100"),
    volume_min=Decimal("0.01"),
    volume_step=Decimal("0.01"),
    volume_max=Decimal("200"),
    spread_fallback_points=240,
    commission_per_lot_per_side=Decimal("0"),
    slippage_points_per_side=50,
    swap_long_points_per_night=Decimal("-503.8"),
    swap_short_points_per_night=Decimal("0"),
    triple_swap_weekday=2,
    provenance={
        "point": Provenance(f"{_SPIKE} symbol_info digits/point", _AS_OF, "measured"),
        "contract_size": Provenance(f"{_SPIKE} symbol_info contract size", _AS_OF, "measured"),
        "volume_min": Provenance(f"{_SPIKE} symbol_info volume min", _AS_OF, "measured"),
        "volume_step": Provenance(f"{_SPIKE} symbol_info volume step", _AS_OF, "measured"),
        "volume_max": Provenance(f"{_SPIKE} symbol_info volume max", _AS_OF, "measured"),
        "spread_fallback_points": Provenance(
            f"{_SPIKE} spread at measurement", _AS_OF, "measured", "floating spread; used only when a bar has no spread"
        ),
        "commission_per_lot_per_side": Provenance(
            f"{_H001} section 6, Exness Standard account", _AS_OF, "assumed", "confirm in R1"
        ),
        "slippage_points_per_side": Provenance(f"{_H001} section 6 [A]", _AS_OF, "assumed"),
        "swap_long_points_per_night": Provenance(f"{_SPIKE} symbol_info swap_long", _AS_OF, "spec", _SWAP_NOTE),
        "swap_short_points_per_night": Provenance(f"{_SPIKE} symbol_info swap_short", _AS_OF, "spec", _SWAP_NOTE),
        "triple_swap_weekday": Provenance(
            f"{_SPIKE} Specification screenshot, swap rates Wednesday = 3", _AS_OF, "assumed", "[A]; Monday = 0"
        ),
    },
)
