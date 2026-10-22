"""Errors raised by sochron.risk.

Every domain error derives from RiskError, a ValueError. Wrong scalar or object types raise
TypeError instead, because passing a float or a bool where money or a count is required is a
programming error, not a bad value (docs/contracts/CORE-003-risk.md, type/domain/error table).
"""


class RiskError(ValueError):
    """Base class for risk errors; also raised for bad sides, exposures and inconsistent records."""


class BadPolicy(RiskError):
    """A risk policy field, its provenance or a cost budget outside its domain."""


class BadEquity(RiskError):
    """Equity or a halt baseline that is not finite and positive."""


class BadStop(RiskError):
    """A price, stop loss or stop distance that is not finite and positive."""


class BadHaltClear(RiskError):
    """An experiment start or restart without a listed name, a reason, or a halted experiment."""


class TimeReversal(RiskError):
    """A Thai trading day earlier than the state's day: a data defect to report, never to repair."""
