"""The cost model: every constant carries its provenance.

H001_COSTS encodes H001 section 6 and the XAUUSDm specification measured in SPIKE-001 on
2026-10-21. Values with status "assumed" are the owner's [A] assumptions from H001; the swap
values are today's specification and say nothing about 2018-2024, which stays UNKNOWN
(docs/architecture.md section 13a, R1 data selection gate). All arithmetic runs in the module's
own Decimal context (precision 28, ROUND_HALF_EVEN), never the caller's.

Inputs are checked the way sochron.risk checks them (docs/contracts/CORE-004-costs-hardening.md):
exact types only, provenance read once and first, every field checked again at each use, and a
size bound on every Decimal that refuses oversized values before any rational conversion.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, Context, Decimal, Rounded, localcontext
from types import MappingProxyType
from typing import Literal

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


# Exact types only (CORE-004 AC-01, as in sochron.risk): a subclass can answer the validation
# (is_finite, <=, in, ==) differently from the arithmetic that follows, so none is accepted.


def is_int(value: object) -> bool:
    return type(value) is int


def require_exact(value: object, kind: type, name: str) -> object:
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")
    return value


# Size bound (CORE-004 AC-04, the same numbers as sochron.risk): rational conversion builds
# 10**|exponent|, so oversized values are refused first, and quickly. plus() in _DIGITS signals
# Rounded exactly when the coefficient has more than MAX_DIGITS digits (trailing zeros included),
# counted in C. Zero is never bounded by its exponent: 0E-999999999999999999 is zero.
MAX_DIGITS = 1000
MAX_ADJUSTED = 1_100_000
_DIGITS = Context(prec=MAX_DIGITS, rounding=ROUND_HALF_EVEN, Emax=MAX_EMAX, Emin=MIN_EMIN, traps=[Rounded])


def bounded_decimal(value: object, name: str, error: type[CostsError]) -> Decimal:
    """Exactly a finite Decimal within the supported size, or TypeError / the slot's error.

    Messages never echo the value: an oversized value would make the message itself huge.
    """
    if type(value) is not Decimal:
        raise TypeError(f"{name} must be exactly Decimal, not {type(value).__name__}")
    if not value.is_finite():
        raise error(f"{name} must be finite")
    too_big = f"{name} is outside the supported size: at most {MAX_DIGITS} digits and |adjusted exponent| <= {MAX_ADJUSTED}"
    if not value.is_zero() and abs(value.adjusted()) > MAX_ADJUSTED:
        raise error(too_big)
    try:
        _DIGITS.plus(value)
    except Rounded:
        raise error(too_big) from None
    return value


@dataclass(frozen=True)
class Provenance:
    """Where a constant came from: source, the date it was read, and how firm it is."""

    source: str
    as_of: date
    status: Status
    note: str = ""

    def __post_init__(self) -> None:
        if type(self) is not Provenance:
            raise TypeError(f"Provenance cannot be subclassed, got {type(self).__name__}")
        require_exact(self.source, str, "source")
        require_exact(self.note, str, "note")
        if type(self.as_of) is not date:
            raise TypeError(f"as_of must be exactly a date (not a datetime or a subclass), not {type(self.as_of).__name__}")
        require_exact(self.status, str, "status")
        if self.status not in STATUSES:
            raise BadProvenance(f"status must be one of {sorted(STATUSES)}")


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
        if type(self) is not CostModel:
            raise TypeError(f"CostModel cannot be subclassed, got {type(self).__name__}")
        snapshot = _check_model(self)
        object.__setattr__(self, "provenance", MappingProxyType(snapshot))


def _check_model(model: CostModel) -> dict[str, Provenance]:
    """Type and domain of every model field; returns the one copy of provenance it validated.

    Provenance is read first and only once (one traversal, each key once): a Mapping planted after
    construction is the only caller code this check can run, so every other field is read after it.
    The same check runs at construction and at every use (CORE-004 AC-03), with the same errors.
    """
    if not isinstance(model.provenance, Mapping):
        raise TypeError(f"provenance must be a Mapping, not {type(model.provenance).__name__}")
    snapshot = dict(model.provenance)
    # Keys must be exactly str before anything compares them: a str subclass's __eq__ is caller code
    # that the key-set comparison below would otherwise run.
    for key in snapshot:
        if type(key) is not str:
            raise TypeError(f"provenance keys must be exactly str, not {type(key).__name__}")
    require_exact(model.symbol, str, "symbol")
    for name in _DECIMAL_FIELDS:
        bounded_decimal(getattr(model, name), name, BadStress if name == "stress_factor" else CostsError)
    for name in _INT_FIELDS:
        if not is_int(getattr(model, name)):
            raise TypeError(f"{name} must be exactly int, not {type(getattr(model, name)).__name__}")
    if model.point <= 0 or model.contract_size <= 0 or model.volume_step <= 0 or model.volume_min <= 0:
        raise CostsError("point, contract_size, volume_step and volume_min must be positive")
    if model.volume_max < model.volume_min:
        raise CostsError("volume_max must not be below volume_min")
    if model.commission_per_lot_per_side < 0 or model.spread_fallback_points < 0 or model.slippage_points_per_side < 0:
        raise CostsError("commission, spread fallback and slippage cannot be negative")
    if not 0 <= model.triple_swap_weekday <= 6:
        # The value is not echoed: a huge int exceeds Python's int-to-str limit (AC-06).
        raise CostsError("triple_swap_weekday must be 0 (Monday) to 6 (Sunday)")
    if model.stress_factor <= 0:
        raise BadStress("stress_factor must be positive")
    keys = set(snapshot)
    expected = set(PROVENANCE_FIELDS)
    if keys != expected:
        raise BadProvenance(
            f"provenance must cover exactly the 11 base fields; missing {sorted(expected - keys)}, extra {sorted(keys - expected)}"
        )
    for name, record in snapshot.items():
        if type(record) is not Provenance:
            raise BadProvenance(f"provenance[{name!r}] must be exactly a Provenance")
    return snapshot


def validate_model(model: object) -> dict[str, Provenance]:
    """Exactly a CostModel whose fields still hold; returns its validated provenance snapshot."""
    require_exact(model, CostModel, "model")
    return _check_model(model)


def stress(model: CostModel, factor: Decimal | int = Decimal("2")) -> CostModel:
    """A copy of the model whose every charge is multiplied by factor; provenance is unchanged."""
    snapshot = validate_model(model)
    if is_int(factor):
        # An int converts exactly and never reaches a rational conversion, so only Decimals are size-bounded.
        value = Decimal(factor)
    elif type(factor) is Decimal:
        value = bounded_decimal(factor, "stress factor", BadStress)
    else:
        raise TypeError(f"factor must be exactly a Decimal or int, not {type(factor).__name__}")
    if value <= 0:
        raise BadStress("stress factor must be positive")
    with localcontext(CONTEXT):
        scaled = model.stress_factor * value
    # Built from the validated snapshot, so the container is not read a second time.
    return replace(model, stress_factor=scaled, provenance=snapshot)


def unknowns(model: CostModel) -> tuple[str, ...]:
    """Names of the constants whose provenance status is assumed or unknown, sorted."""
    snapshot = validate_model(model)
    return tuple(sorted(name for name, p in snapshot.items() if p.status in ("assumed", "unknown")))


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
