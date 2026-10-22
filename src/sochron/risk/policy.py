"""The risk policy, its provenance, and the exact-arithmetic helpers shared by the module.

H001_RISK carries SPEC section 6 [A] values as "assumed" and the halt clearers as "unknown"
until the owner answers SPEC Q-04. Decisions use exact rationals; only display fields are
rounded, once, in the costs module's Decimal context (docs/contracts/CORE-003-risk.md).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import (
    MAX_EMAX,
    MAX_PREC,
    MIN_EMIN,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Underflow,
    localcontext,
)
from fractions import Fraction
from types import MappingProxyType

from sochron.costs import CONTEXT, Provenance

from .errors import BadPolicy, RiskError

POLICY_FIELDS = (
    "risk_per_trade",
    "daily_loss_limit",
    "experiment_loss_limit",
    "max_open_exposures",
    "halt_clearers",
)
_FRACTION_FIELDS = ("risk_per_trade", "daily_loss_limit", "experiment_loss_limit")


# Exact types only (security pre-review F1): a subclass can answer validation (is_finite, <=, in,
# ==, strip) differently from the decision (as_integer_ratio), so no subclass is accepted anywhere.


def is_int(value: object) -> bool:
    return type(value) is int


def require_exact(value: object, kind: type, name: str) -> object:
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")
    return value


def require_decimal(value: object, name: str) -> Decimal:
    if type(value) is not Decimal:
        raise TypeError(f"{name} must be exactly Decimal, not {type(value).__name__}")
    return value


# Size bound (contract v1.3, security pre-review F3): rational conversion builds 10**|exponent| and
# runs gcds, so oversized values are refused before any conversion and the gate always answers fast.
MAX_DIGITS = 1000
MAX_ADJUSTED = 1_100_000


# Counts coefficient digits in C (security pre-review r2 F11): plus() in this context signals Rounded
# exactly when the coefficient has more than MAX_DIGITS digits (trailing zeros included), without the
# per-digit tuple that len(as_tuple().digits) builds. Only Rounded is trapped; flags are never read.
_DIGITS = Context(prec=MAX_DIGITS, rounding=ROUND_HALF_EVEN, Emax=MAX_EMAX, Emin=MIN_EMIN, traps=[Rounded])


def finite_bounded(value: Decimal, name: str, error: type[RiskError]) -> Decimal:
    """A finite Decimal within the supported size, or the slot's domain error (value not echoed)."""
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


def positive_decimal(value: object, name: str, error: type[RiskError]) -> Decimal:
    """A finite, bounded Decimal greater than zero, or the given domain error."""
    number = finite_bounded(require_decimal(value, name), name, error)
    if number <= 0:
        raise error(f"{name} must be positive, got {number}")
    return number


def require_day(value: object, name: str = "day") -> date:
    if type(value) is not date:
        raise TypeError(f"{name} must be exactly a date (not a datetime or a subclass), not {type(value).__name__}")
    return value


def exact(value: Decimal) -> Fraction:
    return Fraction(value)


def loss_reached(baseline: Decimal, equity: Decimal, limit: Decimal) -> bool:
    """Exact and inclusive: baseline - equity >= limit x baseline."""
    return exact(baseline) - exact(equity) >= exact(limit) * exact(baseline)


# Products and sums of finite Decimals are terminating decimals, so this context computes them
# exactly (any rounding would trap as Inexact); display() then rounds each result once.
_EXACT = Context(
    prec=MAX_PREC,
    rounding=ROUND_HALF_EVEN,
    Emax=MAX_EMAX,
    Emin=MIN_EMIN,
    traps=[InvalidOperation, DivisionByZero, Overflow, Underflow, Inexact],
)


def exact_product(*factors: Decimal) -> Decimal:
    with localcontext(_EXACT):
        result = Decimal(1)
        for factor in factors:
            result = result * factor
        return result


def exact_sum(*terms: Decimal) -> Decimal:
    # Zero terms are skipped (review CORE-003-r1 F2): adding 0E-999999999999999999 changes no value
    # but would align the other term to a 10**18-digit coefficient.
    with localcontext(_EXACT):
        result = Decimal(0)
        for term in terms:
            if not term.is_zero():
                result = result + term
        return result


def exact_reduce(value: Decimal) -> Decimal:
    """The same value with trailing zeros of the coefficient removed, exactly."""
    with localcontext(_EXACT):
        return value.normalize()


def display(value: Decimal) -> Decimal:
    """Round an exact value once into CONTEXT; overflow or inexact underflow is a RiskError."""
    context = CONTEXT.copy()
    context.traps[Overflow] = True
    context.traps[Underflow] = True
    try:
        return context.create_decimal(value)
    except (Overflow, Underflow) as error:
        raise RiskError(f"a result is outside the representable range of the risk context ({type(error).__name__})") from error


@dataclass(frozen=True)
class RiskPolicy:
    """Risk limits of one experiment; frozen and bound to its HaltState for the whole run."""

    risk_per_trade: Decimal
    daily_loss_limit: Decimal
    experiment_loss_limit: Decimal
    max_open_exposures: int
    halt_clearers: tuple[str, ...]
    provenance: Mapping[str, Provenance]

    def __post_init__(self) -> None:
        # Read the caller's mapping once (security pre-review F5): validate and store that same copy.
        snapshot = _check_policy(self)
        object.__setattr__(self, "provenance", MappingProxyType(snapshot))


def _check_policy(policy: RiskPolicy) -> dict[str, Provenance]:
    """Type and domain of every policy field; returns the one copy of provenance it validated.

    Provenance is read first and only once: a Mapping planted after construction is the only caller
    code validation can run, so every other field is read after it (security pre-review r2 F9).
    """
    if not isinstance(policy.provenance, Mapping):
        raise TypeError(f"provenance must be a Mapping, not {type(policy.provenance).__name__}")
    snapshot = dict(policy.provenance)
    for name in _FRACTION_FIELDS:
        value = finite_bounded(require_decimal(getattr(policy, name), name), name, BadPolicy)
        if not 0 < value < 1:
            raise BadPolicy(f"{name} must be a fraction strictly between 0 and 1, got {value}")
    if not is_int(policy.max_open_exposures):
        raise TypeError(f"max_open_exposures must be an int, not {type(policy.max_open_exposures).__name__}")
    if policy.max_open_exposures < 1:
        # The value is not echoed: a huge int exceeds Python's int-to-str limit (review r1 F3).
        raise BadPolicy("max_open_exposures must be at least 1")
    require_exact(policy.halt_clearers, tuple, "halt_clearers")
    for name in policy.halt_clearers:
        require_exact(name, str, "a halt_clearers name")
    if not policy.halt_clearers:
        raise BadPolicy("halt_clearers must name at least one clearer")
    if any(not name.strip() for name in policy.halt_clearers):
        raise BadPolicy("halt_clearers cannot hold an empty or blank name")
    if len(set(policy.halt_clearers)) != len(policy.halt_clearers):
        raise BadPolicy("halt_clearers cannot repeat a name")
    keys = set(snapshot)
    expected = set(POLICY_FIELDS)
    if keys != expected:
        raise BadPolicy(
            f"provenance must cover exactly the 5 policy fields; missing {sorted(expected - keys)}, extra {sorted(keys - expected)}"
        )
    for name, record in snapshot.items():
        if type(record) is not Provenance:
            raise BadPolicy(f"provenance[{name!r}] must be exactly a Provenance")
    return snapshot


def validate_policy(policy: object) -> RiskPolicy:
    """Exactly a RiskPolicy whose fields still hold; run again at every use (pre-review F4)."""
    require_exact(policy, RiskPolicy, "policy")
    _check_policy(policy)
    return policy


def unknowns(policy: RiskPolicy) -> tuple[str, ...]:
    """Names of the policy fields whose provenance status is assumed or unknown, sorted."""
    require_exact(policy, RiskPolicy, "policy")
    snapshot = _check_policy(policy)  # the one validated read; provenance is not read again
    return tuple(sorted(name for name, p in snapshot.items() if p.status in ("assumed", "unknown")))


_SPEC6 = "SPEC.md section 6 Risk policy [A]"
_H001 = "docs/hypotheses/H001-m15-momentum-breakout.md section 3"

H001_RISK = RiskPolicy(
    risk_per_trade=Decimal("0.0025"),
    daily_loss_limit=Decimal("0.0075"),
    experiment_loss_limit=Decimal("0.02"),
    max_open_exposures=1,
    halt_clearers=("owner",),
    provenance={
        "risk_per_trade": Provenance(f"{_SPEC6}; {_H001}", date(2026, 10, 21), "assumed", "Q-04 open"),
        "daily_loss_limit": Provenance(
            _SPEC6, date(2026, 10, 21), "assumed", "Q-04 open; baseline is the first equity supplied for the Thai day"
        ),
        "experiment_loss_limit": Provenance(_SPEC6, date(2026, 10, 21), "assumed", "Q-04 open"),
        "max_open_exposures": Provenance(
            f"{_SPEC6}; {_H001}", date(2026, 10, 21), "assumed", "one position or pending order at a time"
        ),
        "halt_clearers": Provenance(
            "SPEC.md section 9 Q-04", date(2026, 10, 22), "unknown", "safe default: the owner only; no agent may clear"
        ),
    },
)
