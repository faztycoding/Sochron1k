"""The risk gate before an entry and before a stop-loss change.

check_entry re-sizes from the request itself (current equity, |entry - stop|, model, budget and
the policy bound to the state) and compares both loss thresholds against the current equity as
well as the stored latches, so neither a stale sizing nor a stale state can let a trade through.
It also takes the request's Thai day and refuses a state that was not rolled to that day
(contract v1.3). It returns every reason to refuse; it never changes the state it is given.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from sochron.costs import CostModel

from .errors import BadEquity, BadStop, RiskError, TimeReversal
from .halts import HaltState, validate_state
from .policy import (
    exact,
    finite_bounded,
    is_int,
    loss_reached,
    positive_decimal,
    require_day,
    require_decimal,
    require_exact,
)
from .sizing import cost_budget, require_model, size_exact

Side = Literal["long", "short"]
ENTRY_REASONS = frozenset(
    {
        "below_min_volume",
        "daily_halt",
        "experiment_halt",
        "lots_exceed_sized",
        "lots_not_on_grid",
        "max_exposure",
        "missing_stop_loss",
        "stale_state",
        "stop_loss_wrong_side",
    }
)
STOP_REASONS = frozenset({"missing_stop_loss", "stop_loss_widened"})
REASONS = ENTRY_REASONS | STOP_REASONS


def _side(side: object) -> Side:
    require_exact(side, str, "side")
    if side not in ("long", "short"):
        raise RiskError(f"side must be 'long' or 'short', got {side!r}")
    return side


def _optional_stop(value: object, name: str) -> Decimal | None:
    if value is None:
        return None
    return positive_decimal(value, name, BadStop)


@dataclass(frozen=True)
class EntryRequest:
    """One proposed entry; finite lots that are off-grid or not positive are a refusal reason, not an error."""

    side: Side
    lots: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    open_exposures: int

    def __post_init__(self) -> None:
        validate_request(self)


def validate_request(request: EntryRequest) -> EntryRequest:
    """Type and domain of every request field; run at construction and again at use (pre-review F4)."""
    require_exact(request, EntryRequest, "request")
    _side(request.side)
    finite_bounded(require_decimal(request.lots, "lots"), "lots", RiskError)
    positive_decimal(request.entry_price, "entry_price", BadStop)
    _optional_stop(request.stop_loss, "stop_loss")
    if not is_int(request.open_exposures):
        raise TypeError(f"open_exposures must be exactly int, not {type(request.open_exposures).__name__}")
    if request.open_exposures < 0:
        # The value is not echoed: a huge int exceeds Python's int-to-str limit (review r1 F3).
        raise RiskError("open_exposures cannot be negative")
    return request


@dataclass(frozen=True)
class GateDecision:
    """allowed is True exactly when there is no reason; reasons are sorted, unique and known."""

    allowed: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        require_exact(self.allowed, bool, "allowed")
        require_exact(self.reasons, tuple, "reasons")
        for reason in self.reasons:
            require_exact(reason, str, "a reason")
        if self.reasons != tuple(sorted(set(self.reasons))):
            raise RiskError("reasons must be sorted and unique")
        if not set(self.reasons) <= REASONS:
            raise RiskError(f"unknown reasons {sorted(set(self.reasons) - REASONS)}")
        if self.allowed != (self.reasons == ()):
            raise RiskError("allowed must be True exactly when there is no reason")


def _decision(reasons: set[str]) -> GateDecision:
    ordered = tuple(sorted(reasons))
    return GateDecision(ordered == (), ordered)


def _on_grid(lots: Fraction, model: CostModel) -> bool:
    if not exact(model.volume_min) <= lots <= exact(model.volume_max):
        return False
    return (lots / exact(model.volume_step)).denominator == 1


def check_entry(
    request: EntryRequest,
    equity: Decimal,
    day: date,
    state: HaltState,
    model: CostModel,
    cost_per_lot: Decimal = Decimal("0"),
) -> GateDecision:
    """Every reason this entry may not be sent on this Thai day; allowed only when there is none."""
    validate_request(request)
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    validate_state(state)
    require_model(model)
    budget = cost_budget(cost_per_lot)
    if day < state.day:
        raise TimeReversal(f"day {day} is before the state's day {state.day}")
    policy = state.policy
    reasons: set[str] = set()
    if day > state.day:
        reasons.add("stale_state")  # the caller did not roll the state with update_equity first
    if state.daily_halted or loss_reached(state.day_start_equity, equity, policy.daily_loss_limit):
        reasons.add("daily_halt")
    if state.experiment_halted or loss_reached(state.experiment_start_equity, equity, policy.experiment_loss_limit):
        reasons.add("experiment_halt")
    if request.open_exposures >= policy.max_open_exposures:
        reasons.add("max_exposure")
    lots = exact(request.lots)
    if not _on_grid(lots, model):
        reasons.add("lots_not_on_grid")
    entry = exact(request.entry_price)
    if request.stop_loss is None:
        reasons.add("missing_stop_loss")
    else:
        stop = exact(request.stop_loss)
        if (request.side == "long" and stop >= entry) or (request.side == "short" and stop <= entry):
            reasons.add("stop_loss_wrong_side")
        else:
            sized = size_exact(exact(equity), abs(entry - stop), model, policy, exact(budget))
            if sized.reason == "below_min_volume":
                reasons.add("below_min_volume")
            if lots > sized.steps * exact(model.volume_step):
                reasons.add("lots_exceed_sized")
    return _decision(reasons)


def check_stop_change(side: Side, current_stop: Decimal, new_stop: Decimal | None) -> GateDecision:
    """A stop loss may move toward the price, never away from it, and never be removed."""
    side = _side(side)
    current = positive_decimal(current_stop, "current_stop", BadStop)
    new = _optional_stop(new_stop, "new_stop")
    if new is None:
        return _decision({"missing_stop_loss"})
    widened = (side == "long" and new < current) or (side == "short" and new > current)
    return _decision({"stop_loss_widened"} if widened else set())
