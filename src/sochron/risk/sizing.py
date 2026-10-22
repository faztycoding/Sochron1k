"""Position sizing by the H001 formula, decided in exact rational arithmetic.

R = risk_per_trade x equity; risk per lot = stop distance x contract size + cost per lot; lots
is the exact floor of R / risk per lot on the volume_step grid, capped at the largest grid point
not above volume_max, and zero below volume_min. cost_per_lot = 0 reproduces the H001 formula
only; it is no evidence of meeting SPEC section 6's "including cost budget" (E1 decides).
"""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from sochron.costs import CostModel

from .errors import BadEquity, BadPolicy, BadStop, RiskError
from .policy import (
    MAX_DIGITS,
    RiskPolicy,
    exact_reduce,
    display,
    exact,
    exact_product,
    exact_sum,
    finite_bounded,
    positive_decimal,
    require_decimal,
    require_exact,
    validate_policy,
)

Reason = Literal["ok", "below_min_volume", "capped_at_volume_max"]
SIZE_REASONS = frozenset({"ok", "below_min_volume", "capped_at_volume_max"})


@dataclass(frozen=True)
class SizeDecision:
    """Lots allowed for one entry and the risk behind them, in USD (display values)."""

    lots: Decimal
    risk_money: Decimal
    risk_per_lot: Decimal
    actual_risk: Decimal
    reason: Reason

    def __post_init__(self) -> None:
        for name in ("lots", "risk_money", "risk_per_lot", "actual_risk"):
            finite_bounded(require_decimal(getattr(self, name), name), name, RiskError)
        require_exact(self.reason, str, "reason")
        if self.reason not in SIZE_REASONS:
            raise RiskError(f"unknown sizing reason {self.reason!r}")
        if self.lots < 0:
            raise RiskError(f"lots cannot be negative, got {self.lots}")
        if (self.reason == "below_min_volume") != (self.lots == 0):
            raise RiskError("reason below_min_volume must go with zero lots, and only with zero lots")


@dataclass(frozen=True)
class _Exact:
    steps: int
    risk_money: Fraction
    risk_per_lot: Fraction
    reason: Reason


def require_model(model: object) -> CostModel:
    """Exactly a CostModel whose fields read by risk are exactly Decimal (costs accepts subclasses).

    The domain is checked again at every use (review CORE-003-r1 F1): a field set to zero or below
    after construction, or volume_max below volume_min, would let sizing exceed the risk budget.
    """
    require_exact(model, CostModel, "model")
    for name in ("contract_size", "volume_min", "volume_step", "volume_max"):
        finite_bounded(require_decimal(getattr(model, name), f"model.{name}"), f"model.{name}", RiskError)
    if model.contract_size <= 0 or model.volume_step <= 0 or model.volume_min <= 0:
        raise RiskError("model.contract_size, volume_step and volume_min must be positive")
    if model.volume_max < model.volume_min:
        raise RiskError("model.volume_max must not be below volume_min")
    return model


def require_policy(policy: object) -> RiskPolicy:
    return validate_policy(policy)


def cost_budget(value: object) -> Decimal:
    budget = finite_bounded(require_decimal(value, "cost_per_lot"), "cost_per_lot", BadPolicy)
    if budget < 0:
        raise BadPolicy(f"cost_per_lot cannot be negative, got {budget}")
    return budget


def size_exact(equity: Fraction, stop_distance: Fraction, model: CostModel, policy: RiskPolicy, budget: Fraction) -> _Exact:
    """The sizing decision in exact rationals; inputs are already validated."""
    risk_money = exact(policy.risk_per_trade) * equity
    risk_per_lot = stop_distance * exact(model.contract_size) + budget
    step = exact(model.volume_step)
    uncapped = (risk_money / risk_per_lot / step).__floor__()
    max_steps = (exact(model.volume_max) / step).__floor__()
    steps = min(uncapped, max_steps)
    if steps * step < exact(model.volume_min):
        return _Exact(0, risk_money, risk_per_lot, "below_min_volume")
    return _Exact(steps, risk_money, risk_per_lot, "capped_at_volume_max" if uncapped > max_steps else "ok")


def grid_lots(steps: int, step: Decimal) -> Decimal:
    """steps x step as an exact Decimal; int -> Decimal and the unbounded exact context avoid str(int) limits.

    A huge step count carries many trailing zeros; they are removed exactly when the coefficient
    would exceed the size bound, so the value stays representable (1E+5000, not 1000...0).
    """
    lots = exact_product(Decimal(steps), step)
    if len(lots.as_tuple().digits) > MAX_DIGITS:
        lots = exact_reduce(lots)
    return lots


def size_position(
    equity: Decimal,
    stop_distance: Decimal,
    model: CostModel,
    policy: RiskPolicy,
    cost_per_lot: Decimal = Decimal("0"),
) -> SizeDecision:
    """Lots for one entry by the H001 formula, with every decision taken in exact arithmetic."""
    require_policy(policy)  # first: its provenance read is the only caller code (pre-review r2 F9)
    require_model(model)
    equity = positive_decimal(equity, "equity", BadEquity)
    stop_distance = positive_decimal(stop_distance, "stop_distance", BadStop)
    budget = cost_budget(cost_per_lot)
    result = size_exact(exact(equity), exact(stop_distance), model, policy, exact(budget))
    lots = grid_lots(result.steps, model.volume_step)
    # Display values: the same quantities as exact Decimals (never via huge integers), rounded once.
    risk_money = exact_product(policy.risk_per_trade, equity)
    risk_per_lot = exact_sum(exact_product(stop_distance, model.contract_size), budget)
    return SizeDecision(
        lots=lots,
        risk_money=display(risk_money),
        risk_per_lot=display(risk_per_lot),
        actual_risk=display(exact_product(lots, risk_per_lot)),
        reason=result.reason,
    )
