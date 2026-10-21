"""Measured time rules: how raw MT5 time relates to UTC on a given server.

A rule is evidence, not an assumption. SPIKE-001 measured an offset of 0 seconds on
Exness-MT5Trial14 but could not tell "the Python API returns UTC" from "the server runs at
GMT+0" (its AC-04 stays UNKNOWN), so each rule names the server, symbol, terminal build and
evidence window it was measured for. Another server, build or a contradicting measurement
needs a new rule through a new contract: nothing here ever adjusts offset_seconds
(docs/architecture.md section 13a, "R1 time/data").
"""

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

from .errors import UnknownTimeRule


@dataclass(frozen=True)
class TimeRule:
    """How to read raw MT5 seconds for one server: raw = UTC seconds + offset_seconds."""

    server: str
    symbol: str
    terminal_build: int
    offset_seconds: int
    evidence_from: date
    evidence_to: date
    evidence_ref: str
    version: str


RULES = MappingProxyType(
    {
        "Exness-MT5Trial14": TimeRule(
            server="Exness-MT5Trial14",
            symbol="XAUUSDm",
            terminal_build=6274,
            offset_seconds=0,
            evidence_from=date(2026, 10, 20),
            evidence_to=date(2026, 10, 21),
            evidence_ref="docs/evidence/SPIKE-001.md",
            version="1",
        ),
    }
)


def rule_for(server: str) -> TimeRule:
    """Return the measured rule for a server, or refuse: there is no default offset."""
    try:
        return RULES[server]
    except KeyError:
        raise UnknownTimeRule(
            f"no measured time rule for server {server!r}; measure it first (a SPIKE contract)"
        ) from None
