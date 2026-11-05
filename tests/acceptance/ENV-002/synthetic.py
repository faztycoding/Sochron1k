"""ENV-002 synthetic M1 bars: the synthetic bar generator of docs/contracts/ENV-002-research-host-separation.md v1.6.

Written by the test author and locked with the acceptance tests: fake data lives under tests/ only
(AGENTS.md). Both test folders (tests/acceptance/ENV-002/ and tests/unit/app/) load this file by the
contract's recipe, because the repository has no conftest.py and pytest's pythonpath is only src:

    spec = importlib.util.spec_from_file_location("synthetic", <repo>/tests/acceptance/ENV-002/synthetic.py)
    module = importlib.util.module_from_spec(spec)
    sys.modules["synthetic"] = module
    spec.loader.exec_module(module)

synthetic_bars(start, count) returns count contiguous M1 core.Bar values, the first at start and each
next one a minute later. time_raw is timebase.to_raw(time_utc, rule) and time_utc is
timebase.to_utc(time_raw, rule) for rule = timebase.rule_for("Exness-MT5Trial14"), so the two agree
as research and backtest check them. Every bar has the same price (open = high = low = close =
2000.00), which passes the OHLC checks, spread 200 points, tick_volume 1 and m1_count 1.
start must be an aware UTC datetime on a whole minute; count is an int from 0.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from sochron.core import Bar
from sochron.timebase import rule_for, to_raw, to_utc

SERVER = "Exness-MT5Trial14"
PRICE = Decimal("2000.00")
SPREAD = 200
_MINUTE = timedelta(minutes=1)


def synthetic_bars(start: datetime, count: int) -> list[Bar]:
    """count contiguous synthetic M1 bars from start, raw and UTC times agreeing under the measured rule."""
    if type(count) is not int or count < 0:
        raise ValueError("count must be an int of at least 0")
    if not isinstance(start, datetime) or start.utcoffset() != timedelta(0):
        raise ValueError("start must be an aware datetime in UTC")
    if start.second or start.microsecond:
        raise ValueError("start must be on a whole minute")
    rule = rule_for(SERVER)
    bars = []
    for index in range(count):
        raw = to_raw(start + index * _MINUTE, rule)
        bars.append(Bar(time_raw=raw, time_utc=to_utc(raw, rule), timeframe=1, open=PRICE, high=PRICE,
                        low=PRICE, close=PRICE, spread=SPREAD, tick_volume=1, m1_count=1))
    return bars
