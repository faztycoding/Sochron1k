"""Errors raised by sochron.costs.

Every domain error derives from CostsError, a ValueError, so callers can catch the family
in one clause. Wrong scalar types (a float where Decimal or int is required) raise TypeError
instead, because a float carrying money is a programming error, not a bad value.
"""


class CostsError(ValueError):
    """Base class for cost-model errors."""


class BadProvenance(CostsError):
    """The provenance mapping does not cover exactly the model's numeric fields."""


class BadStress(CostsError):
    """A stress factor that is not strictly positive."""


class BadVolume(CostsError):
    """Lots outside [volume_min, volume_max] or not a multiple of volume_step."""


class BadPoints(CostsError):
    """A negative spread in points."""


class BadSides(CostsError):
    """A negative number of sides."""


class BadNights(CostsError):
    """Negative nights, negative triple nights, or more triple nights than nights."""


class BadR(CostsError):
    """An R value that is not strictly positive."""
