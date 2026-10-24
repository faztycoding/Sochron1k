"""The value types and constants of sochron.research (CORE-008): versions, errors, Dataset, Summary,
BaselineSummary and the small checks they share.

Every type is a frozen dataclass that checks itself when built: a wrong type is TypeError (bool is not
an int, a list is not a tuple) and a right type with a value outside the contract is ResearchError.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, TypeVar, cast, get_args

RESEARCH_VERSION = "research-v1"
HOLDOUT_CUTOFF_UTC = datetime(2025, 1, 1, tzinfo=UTC)  # H001 section 5
BASELINE_RUNS = 1000  # H001 section 7
HYPOTHESIS = "H001"  # what run_variant and random_entry_baseline write
# H001 section 4 budgets as the contract counts them (runner step 5, D10).
SELECT_BUDGET = 6  # distinct params of select per variant
ROBUSTNESS_BUDGET = 14  # robustness started lines per variant
TOTAL_BUDGET = 63  # distinct select params + robustness and stress started lines, summed over variants

Purpose = Literal["select", "robustness", "stress", "long_only", "random_entry"]
PURPOSES: tuple[str, ...] = get_args(Purpose)
VARIANTS = ("A", "B", "C")
STATUSES = ("started", "ok", "failed")
PARAM_NAMES = ("f", "s", "n", "theta", "N", "M", "k")  # H001Params field order without variant
# The parameters each structure's rules read (H001 section 3, contract D9).
USED_PARAMETERS = MappingProxyType({
    "A": ("f", "s", "n", "theta", "k"),
    "B": ("n", "N", "M", "k"),
    "C": ("f", "s", "n", "N", "M", "k"),
})

T = TypeVar("T")
_HEX = frozenset("0123456789abcdef")
_DIGITS = frozenset("0123456789")


class ResearchError(ValueError):
    """A value of the right type that the research contract does not allow."""


class BudgetExceeded(ResearchError):
    """The run would go past a variant budget of H001 section 4, or change what the file has fixed."""


class HoldoutRefused(ResearchError):
    """The input holds data from the holdout cutoff on (H001 section 5)."""


def too_large(error: ArithmeticError) -> ResearchError:
    """A finite value whose sum or product leaves the Decimal exponent range of CONTEXT is outside the domain."""
    return ResearchError(f"a value is too large for the research Decimal arithmetic ({type(error).__name__})")


def exact(value: object, kind: type[T], name: str) -> T:
    """The same object when its type is exactly kind (no subclass, no bool for int); TypeError otherwise."""
    if type(value) is not kind:
        raise TypeError(f"{name} must be exactly {kind.__name__}, not {type(value).__name__}")
    return cast(T, value)


def exact_optional(value: object, kind: type[T], name: str) -> T | None:
    return None if value is None else exact(value, kind, name)


def is_hex(text: str, length: int) -> bool:
    """Lower-case hexadecimal of exactly length characters."""
    return len(text) == length and all(character in _HEX for character in text)


def is_ascii(text: str) -> bool:
    return all(ord(character) < 128 for character in text)


def ascii_text(text: str) -> str:
    """Every character that is not ASCII becomes '?' (the registry's error field)."""
    return "".join(character if ord(character) < 128 else "?" for character in text)


def is_digits(text: str) -> bool:
    return bool(text) and all(character in _DIGITS for character in text)


def finite(value: Decimal, name: str) -> None:
    if not value.is_finite():
        raise ResearchError(f"{name} must be finite")


def check_utc_second(value: datetime, name: str) -> None:
    """Aware, offset 0 and no microsecond: the instants the registry writes as %Y-%m-%dT%H:%M:%SZ."""
    if value.utcoffset() is None:
        raise ResearchError(f"{name} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ResearchError(f"{name} must be in UTC (offset 0)")
    if value.microsecond:
        raise ResearchError(f"{name} must be a whole second")


def utc_text(value: datetime) -> str:
    """The canonical text of a checked UTC instant."""
    return (f"{value.year:04d}-{value.month:02d}-{value.day:02d}T"
            f"{value.hour:02d}:{value.minute:02d}:{value.second:02d}Z")


@dataclass(frozen=True)
class Dataset:
    """What the caller says the bars are: snapshot, manifest hash and the period [start, end)."""

    snapshot_id: str
    manifest_sha256: str
    period_start_utc: datetime
    period_end_utc: datetime
    m1_bars: int

    def __post_init__(self) -> None:
        exact(self.snapshot_id, str, "snapshot_id")
        exact(self.manifest_sha256, str, "manifest_sha256")
        exact(self.period_start_utc, datetime, "period_start_utc")
        exact(self.period_end_utc, datetime, "period_end_utc")
        exact(self.m1_bars, int, "m1_bars")
        if not self.snapshot_id:
            raise ResearchError("snapshot_id must not be empty")
        if not is_hex(self.manifest_sha256, 64):
            raise ResearchError("manifest_sha256 must be 64 lower-case hex characters")
        check_utc_second(self.period_start_utc, "period_start_utc")
        check_utc_second(self.period_end_utc, "period_end_utc")
        if self.period_start_utc >= self.period_end_utc:
            raise ResearchError("period_start_utc must be before period_end_utc")
        if self.m1_bars < 1:
            raise ResearchError("m1_bars must be at least 1")


def _check_count(value: object, name: str) -> None:
    if exact(value, int, name) < 0:
        raise ResearchError(f"{name} must not be negative")


def _check_decimal(value: object, name: str, optional: bool = False) -> None:
    number = exact_optional(value, Decimal, name) if optional else exact(value, Decimal, name)
    if number is not None:
        finite(number, name)


@dataclass(frozen=True)
class Summary:
    """The statistics of one run's trades (contract "summarize และสถิติ")."""

    trades: int
    expectancy_r: Decimal | None
    max_drawdown_r: Decimal
    net_money: Decimal
    long_trades: int
    long_expectancy_r: Decimal | None
    short_trades: int
    short_expectancy_r: Decimal | None
    top5_removed_expectancy_r: Decimal | None
    expectancy_by_year: tuple[tuple[int, Decimal], ...]
    ambiguous_trades: int
    flagged_trades: int
    gap_fills: int
    end_of_data_trades: int

    def __post_init__(self) -> None:
        for name in ("trades", "long_trades", "short_trades", "ambiguous_trades", "flagged_trades", "gap_fills",
                     "end_of_data_trades"):
            _check_count(getattr(self, name), name)
        for name in ("max_drawdown_r", "net_money"):
            _check_decimal(getattr(self, name), name)
        for name in ("expectancy_r", "long_expectancy_r", "short_expectancy_r", "top5_removed_expectancy_r"):
            _check_decimal(getattr(self, name), name, optional=True)
        years = exact(self.expectancy_by_year, tuple, "expectancy_by_year")
        previous = None
        for item in years:
            pair = exact(item, tuple, "an expectancy_by_year item")
            if len(pair) != 2:
                raise ResearchError("an expectancy_by_year item must be (year, expectancy)")
            year = exact(pair[0], int, "a year")
            _check_decimal(pair[1], "a year's expectancy")
            if previous is not None and year <= previous:
                raise ResearchError("expectancy_by_year must be sorted by year, each year once")
            previous = year


@dataclass(frozen=True)
class BaselineSummary:
    """The random-entry distribution of one variant (contract "random-entry baseline" step 8)."""

    runs: int
    trades_per_run: int
    seed: int
    mean_r: Decimal
    p05_r: Decimal
    p50_r: Decimal
    p95_r: Decimal
    variant_mean_hold_m1: Decimal
    variant_median_hold_m1: int
    baseline_mean_hold_m1: Decimal
    baseline_median_hold_m1: int

    def __post_init__(self) -> None:
        for name in ("runs", "trades_per_run", "seed", "variant_median_hold_m1", "baseline_median_hold_m1"):
            _check_count(getattr(self, name), name)
        for name in ("mean_r", "p05_r", "p50_r", "p95_r", "variant_mean_hold_m1", "baseline_mean_hold_m1"):
            _check_decimal(getattr(self, name), name)
