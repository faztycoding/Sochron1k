"""sochron.risk: sizing, halt state and the risk gate (CORE-003).

Pure and deterministic: no I/O, no clock, no MetaTrader5. Policy values carry provenance and stay
"assumed" or "unknown" until the owner answers SPEC Q-04. See docs/contracts/CORE-003-risk.md.
"""

from .errors import BadEquity, BadHaltClear, BadPolicy, BadStop, RiskError, TimeReversal
from .gate import EntryRequest, GateDecision, check_entry, check_stop_change
from .halts import HaltState, restart_experiment, start_experiment, update_equity
from .policy import H001_RISK, POLICY_FIELDS, RiskPolicy, unknowns
from .sizing import SizeDecision, size_position

__all__ = [
    "BadEquity",
    "BadHaltClear",
    "BadPolicy",
    "BadStop",
    "EntryRequest",
    "GateDecision",
    "H001_RISK",
    "HaltState",
    "POLICY_FIELDS",
    "RiskError",
    "RiskPolicy",
    "SizeDecision",
    "TimeReversal",
    "check_entry",
    "check_stop_change",
    "restart_experiment",
    "size_position",
    "start_experiment",
    "unknowns",
    "update_equity",
]
