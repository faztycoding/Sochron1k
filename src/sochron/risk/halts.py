"""Halt state of one experiment, bound to its policy.

The daily halt latches at the Thai-day loss limit and lifts only on a later Thai day; the
experiment halt latches at the experiment loss limit and lifts only through an authorized
restart, which keeps the day's daily halt (owner decision, 2026-10-22). This module never reads
a clock; the caller supplies the Thai day and must keep the returned state (E1: from a journal).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .errors import BadEquity, BadHaltClear, RiskError, TimeReversal
from .policy import RiskPolicy, loss_reached, positive_decimal, require_day, require_exact
from .sizing import require_policy


@dataclass(frozen=True)
class HaltState:
    """Where one experiment stands: its policy, Thai day, baselines and the two halt latches."""

    policy: RiskPolicy
    day: date
    day_start_equity: Decimal
    experiment_start_equity: Decimal
    daily_halted: bool
    experiment_halted: bool

    def __post_init__(self) -> None:
        validate_state(self)


def validate_state(state: object) -> HaltState:
    """Type and domain of every state field; run at construction and again at use (pre-review F4).

    The policy is validated first, because reading its provenance is the only caller code validation
    can run; every other field is read after it, and the policy object is pinned (pre-review r2 F9).
    """
    checked = require_exact(state, HaltState, "state")
    policy = checked.policy
    require_policy(policy)
    require_day(checked.day)
    positive_decimal(checked.day_start_equity, "day_start_equity", BadEquity)
    positive_decimal(checked.experiment_start_equity, "experiment_start_equity", BadEquity)
    for name in ("daily_halted", "experiment_halted"):
        require_exact(getattr(checked, name), bool, name)
    if checked.policy is not policy:
        raise RiskError("state.policy was replaced while the state was being validated")
    return checked


def _require_state(state: object) -> HaltState:
    return validate_state(state)


def _new_state(
    policy: RiskPolicy, day: date, day_start: Decimal, experiment_start: Decimal, daily: bool, experiment: bool
) -> HaltState:
    """The result of a public operation, built from values that operation has already validated.

    It does not run HaltState's validation again: that would read the policy's provenance a second
    time, after the decision, and a planted Mapping could change the policy the result is bound to
    (review CORE-003-r2 F5). A HaltState built directly by a caller is still fully validated.
    """
    state = object.__new__(HaltState)
    for name, value in (
        ("policy", policy),
        ("day", day),
        ("day_start_equity", day_start),
        ("experiment_start_equity", experiment_start),
        ("daily_halted", daily),
        ("experiment_halted", experiment),
    ):
        object.__setattr__(state, name, value)
    return state


def _authorize(policy: RiskPolicy, authorized_by: object, reason: object) -> None:
    clearer = require_exact(authorized_by, str, "authorized_by")
    text = require_exact(reason, str, "reason")
    if clearer not in policy.halt_clearers:
        raise BadHaltClear(f"{clearer!r} is not allowed to start or restart this experiment")
    if not text.strip():
        raise BadHaltClear("a start or restart needs a reason")


def start_experiment(equity: Decimal, day: date, policy: RiskPolicy, authorized_by: str, reason: str) -> HaltState:
    """A new, authorized experiment: both baselines at equity, no halt, the policy bound for the run."""
    require_policy(policy)
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    _authorize(policy, authorized_by, reason)
    return _new_state(policy, day, equity, equity, False, False)


def _roll(state: HaltState, policy: RiskPolicy, equity: Decimal, day: date) -> tuple[Decimal, bool, bool]:
    """Daily baseline and both latches after this equity on this day; inputs are already validated."""
    if day == state.day:
        day_start = state.day_start_equity
        daily = state.daily_halted or loss_reached(day_start, equity, policy.daily_loss_limit)
    else:
        day_start = equity
        daily = False
    experiment = state.experiment_halted or loss_reached(
        state.experiment_start_equity, equity, policy.experiment_loss_limit
    )
    return day_start, daily, experiment


def update_equity(state: HaltState, equity: Decimal, day: date) -> HaltState:
    """Roll the state to this Thai day and equity; latches never clear here except daily on a later day."""
    state = _require_state(state)
    policy = state.policy  # pinned by validate_state; no caller code runs after it
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    if day < state.day:
        raise TimeReversal(f"day {day} is before the state's day {state.day}")
    day_start, daily, experiment = _roll(state, policy, equity, day)
    return _new_state(policy, day, day_start, state.experiment_start_equity, daily, experiment)


def restart_experiment(state: HaltState, equity: Decimal, day: date, authorized_by: str, reason: str) -> HaltState:
    """Clear a halted experiment by an authorized name with a reason; the day's daily halt stays.

    It rolls the day with _roll, not update_equity, so the state is validated once and the policy it
    validated is the one bound to the result (security pre-review r2 F9).
    """
    state = _require_state(state)
    policy = state.policy
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    if day < state.day:
        raise TimeReversal(f"day {day} is before the state's day {state.day}")
    _authorize(policy, authorized_by, reason)
    if not state.experiment_halted:
        raise BadHaltClear("only a halted experiment can be restarted")
    day_start, daily, _ = _roll(state, policy, equity, day)
    return _new_state(policy, day, day_start, equity, daily, False)
