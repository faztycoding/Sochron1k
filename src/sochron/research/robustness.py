"""neighbours(): the +-10% sets of H001 section 4 for the parameters each structure uses (contract D9)."""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Any, Literal

from sochron.costs import CONTEXT
from sochron.strategy import H001Params, StrategyError

from .model import PARAM_NAMES, USED_PARAMETERS, exact, text

_INTEGERS = frozenset({"f", "s", "n", "N", "M"})
Direction = Literal["-", "+"]
_STEPS: tuple[tuple[Direction, Decimal], ...] = (("-", Decimal("0.9")), ("+", Decimal("1.1")))


@dataclass(frozen=True)
class Neighbour:
    """One parameter moved by one step; params is None when H001Params refuses the moved set (not run)."""

    parameter: str
    direction: Direction
    value: str
    params: H001Params | None


def neighbours(params: H001Params) -> tuple[Neighbour, ...]:
    """Two neighbours per used parameter in the order f, s, n, theta, N, M, k, each "-" then "+"."""
    exact(params, H001Params, "params")
    used = USED_PARAMETERS[params.variant]
    out = []
    for name in PARAM_NAMES:
        if name not in used:
            continue
        for direction, factor in _STEPS:
            with localcontext(CONTEXT):
                moved = Decimal(getattr(params, name)) * factor
                if name in _INTEGERS:
                    moved = moved.quantize(Decimal(1), rounding=ROUND_HALF_UP)
            change: dict[str, Any] = {name: int(moved) if name in _INTEGERS else moved}
            try:
                candidate: H001Params | None = replace(params, **change)
            except StrategyError:  # outside its range, s < 3f or M > N: invalid, counted as failed
                candidate = None
            out.append(Neighbour(name, direction, text(moved), candidate))
    return tuple(out)
