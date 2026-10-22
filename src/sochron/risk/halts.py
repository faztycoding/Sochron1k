"""Halt state of one experiment, bound to its policy.

The daily halt latches at the Thai-day loss limit and lifts only on a later Thai day; the
experiment halt latches at the experiment loss limit and lifts only through an authorized
restart, which keeps the day's daily halt (owner decision, 2026-10-22). This module never reads
a clock; the caller supplies the Thai day and must keep the returned state (E1: from a journal).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .errors import BadEquity, BadHaltClear, TimeReversal
from .policy import RiskPolicy, loss_reached, positive_decimal, require_day
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
        require_policy(self.policy)
        require_day(self.day)
        positive_decimal(self.day_start_equity, "day_start_equity", BadEquity)
        positive_decimal(self.experiment_start_equity, "experiment_start_equity", BadEquity)
        for name in ("daily_halted", "experiment_halted"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool, not {type(getattr(self, name)).__name__}")


def _require_state(state: object) -> HaltState:
    if not isinstance(state, HaltState):
        raise TypeError(f"state must be a HaltState, not {type(state).__name__}")
    return state


def _authorize(policy: RiskPolicy, authorized_by: object, reason: object) -> None:
    if not isinstance(authorized_by, str):
        raise TypeError(f"authorized_by must be a str, not {type(authorized_by).__name__}")
    if not isinstance(reason, str):
        raise TypeError(f"reason must be a str, not {type(reason).__name__}")
    if authorized_by not in policy.halt_clearers:
        raise BadHaltClear(f"{authorized_by!r} is not allowed to start or restart this experiment")
    if not reason.strip():
        raise BadHaltClear("a start or restart needs a reason")


def start_experiment(equity: Decimal, day: date, policy: RiskPolicy, authorized_by: str, reason: str) -> HaltState:
    """A new, authorized experiment: both baselines at equity, no halt, the policy bound for the run."""
    require_policy(policy)
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    _authorize(policy, authorized_by, reason)
    return HaltState(policy, day, equity, equity, False, False)


def update_equity(state: HaltState, equity: Decimal, day: date) -> HaltState:
    """Roll the state to this Thai day and equity; latches never clear here except daily on a later day."""
    state = _require_state(state)
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    if day < state.day:
        raise TimeReversal(f"day {day} is before the state's day {state.day}")
    policy = state.policy
    if day == state.day:
        day_start = state.day_start_equity
        daily = state.daily_halted or loss_reached(day_start, equity, policy.daily_loss_limit)
    else:
        day_start = equity
        daily = False
    experiment = state.experiment_halted or loss_reached(
        state.experiment_start_equity, equity, policy.experiment_loss_limit
    )
    return HaltState(policy, day, day_start, state.experiment_start_equity, daily, experiment)


def restart_experiment(state: HaltState, equity: Decimal, day: date, authorized_by: str, reason: str) -> HaltState:
    """Clear a halted experiment by an authorized name with a reason; the day's daily halt stays."""
    state = _require_state(state)
    equity = positive_decimal(equity, "equity", BadEquity)
    require_day(day)
    if day < state.day:
        raise TimeReversal(f"day {day} is before the state's day {state.day}")
    _authorize(state.policy, authorized_by, reason)
    if not state.experiment_halted:
        raise BadHaltClear("only a halted experiment can be restarted")
    rolled = update_equity(state, equity, day)
    return HaltState(state.policy, rolled.day, rolled.day_start_equity, equity, rolled.daily_halted, False)
