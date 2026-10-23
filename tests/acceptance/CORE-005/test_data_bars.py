"""Approved CORE-005 v1.1 contract tests; run pytest from the repository root.

Round 2 (docs/reviews/CORE-005-tests-r1.md, owner 2026-10-24) fixes F1, F2, F4, F5, F7, F8
and F11, states F3 below, and adds the v1.1 items: Bar range refusals, an m1_count without
upper bound, duplicate and out-of-order M1 in aggregate, max_gap_minutes < 0 and
ValidationReport.calendar.

Conventions the contract leaves to this table (docs/contracts/CORE-005-data-bars.md):
- Wrong type -> TypeError; a finite-but-unsupported value (non-finite Decimal, a timeframe
  outside TIMEFRAMES_MINUTES) -> ValueError. Subclasses of int, str, Decimal, datetime and
  Bar are wrong types.
- Gap length = missing M1 minutes between consecutive bars, (t2 - t1) / 60 - 1, so 13:04 then
  13:10 is a gap of 5. Minutes inside a calendar closure are not counted. A gap is
  unexpected_gap (WARN) when its in-session minutes exceed max_gap_minutes.
- unexpected_gap.time_raw = open time of the first bar after the gap (where it is observed).
- empty_weekday.time_raw = None; a weekday is a Monday..Friday UTC date with no bar at all,
  strictly inside the span of the input.
- A Saturday or Sunday UTC date without bars is not a key of report.days, even inside the
  span of the input (contract v1.1 item 5).
- An equal time -> duplicate_time only; a time below its predecessor -> time_not_increasing.
- ClosureCalendar.weekend weekdays follow datetime.date.weekday(): Friday = 4, Sunday = 6.
- incomplete is judged with report.calendar (v1.1 item 3): a produced bar with fewer M1 than
  its timeframe is not incomplete when every missing minute of its slot is inside a closure,
  and is incomplete when an in-session minute is missing. Every H001 closure boundary (17:00,
  18:00 New York) falls on an M15 boundary in UTC, so under H001_CLOSURES a produced M15 bar
  is incomplete exactly when it has fewer than 15 M1.
"""

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from runpy import run_path

import pytest


_MODULES = {"core": "sochron.core", "snapshot": "sochron.data.snapshot"}
SERVER = "Exness-MT5Trial14"
DAY = "2026-03-10"  # Tuesday, New York on EDT (UTC-4)


def _api(monkeypatch, ac, *names):
    """Missing implementation fails each AC without breaking collection; contract names only."""
    monkeypatch.syspath_prepend(str(Path.cwd() / "src"))
    symbols = []
    for name in names:
        prefix, _, attribute = name.partition(".")
        module_name = _MODULES[prefix]
        try:
            module = import_module(module_name)
        except ImportError as error:
            pytest.fail(f"{ac}: {module_name} not implemented ({error})", pytrace=False)
        try:
            symbols.append(getattr(module, attribute))
        except AttributeError:
            pytest.fail(f"{ac}: {module_name}.{attribute} not implemented", pytrace=False)
    return tuple(symbols)


def _tb():
    """sochron.timebase (CORE-001, merged); call after _api has put src on the path."""
    return import_module("sochron.timebase")


def _golden():
    return run_path(str(Path(__file__).resolve().parents[2] / "golden/CORE-005/bars_cases.py"))


def _raw(iso):
    """Raw MT5 seconds of a naive ISO string read as UTC (the rule has offset 0)."""
    return int(datetime.fromisoformat(iso).replace(tzinfo=UTC).timestamp())


def _minutes(iso, count):
    """`count` consecutive minute strings starting at iso (naive UTC)."""
    start = datetime.fromisoformat(iso)
    return tuple((start + timedelta(minutes=step)).isoformat(timespec="minutes") for step in range(count))


def _m1(Bar, tb, rule, iso, open_="4000.000", high="4000.300", low="3999.900", close="4000.200",
        spread=240, volume=7, time_utc_shift=0):
    raw = _raw(iso)
    return Bar(
        time_raw=raw,
        time_utc=tb.to_utc(raw, rule) + timedelta(seconds=time_utc_shift),
        timeframe=1,
        open=Decimal(open_), high=Decimal(high), low=Decimal(low), close=Decimal(close),
        spread=spread, tick_volume=volume, m1_count=1,
    )


def _series(Bar, tb, rule, isos, overrides=None):
    overrides = overrides or {}
    return [_m1(Bar, tb, rule, iso, **overrides.get(index, {})) for index, iso in enumerate(isos)]


def _snapshot(bars):
    """Identity, order and every field of every bar, to prove the input is untouched."""
    return tuple((id(bar), tuple(getattr(bar, field.name) for field in fields(bar))) for bar in bars)


def _defects(report):
    return sorted(
        ((defect.code, defect.severity, defect.time_raw) for defect in report.defects),
        key=lambda item: (item[0], item[1], -1 if item[2] is None else item[2]),
    )


def _expected(rows):
    return sorted(
        ((code, severity, None if iso is None else _raw(iso)) for code, severity, iso in rows),
        key=lambda item: (item[0], item[1], -1 if item[2] is None else item[2]),
    )


def _check_report(report, Defect, bars):
    """Shape of a ValidationReport; m1_bars counts the input and nothing was added or removed."""
    assert type(report.defects) is tuple
    for defect in report.defects:
        assert isinstance(defect, Defect)
        assert type(defect.code) is str and defect.code
        assert defect.severity in ("WARN", "UNKNOWN", "STOP")
        assert defect.time_raw is None or type(defect.time_raw) is int
        assert type(defect.detail) is str
        assert (defect.code == "empty_weekday") == (defect.time_raw is None)
    assert isinstance(report.days, Mapping)
    for day, status in report.days.items():
        assert type(day) is date
        assert status in ("PASS", "WARN", "UNKNOWN", "STOP")
    assert type(report.m1_bars) is int
    assert report.m1_bars == len(bars)


class _Int(int):
    pass


class _Dec(Decimal):
    pass


class _Str(str):
    pass


class _Datetime(datetime):
    pass


_FIELDS = ("time_raw", "time_utc", "timeframe", "open", "high", "low", "close",
           "spread", "tick_volume", "m1_count")


def test_ac01_bar_exact_types_finiteness_timeframe_set_and_immutability(monkeypatch):
    (Bar,) = _api(monkeypatch, "AC-01", "core.Bar")
    tb = _tb()
    rule = tb.rule_for(SERVER)
    raw = 1773147600  # 2026-03-10T13:00:00Z, hand-computed in the golden file
    assert _raw(f"{DAY}T13:00") == raw
    valid = dict(
        time_raw=raw, time_utc=tb.to_utc(raw, rule), timeframe=1,
        open=Decimal("4000.000"), high=Decimal("4000.300"), low=Decimal("3999.900"),
        close=Decimal("4000.200"), spread=240, tick_volume=7, m1_count=1,
    )
    assert is_dataclass(Bar)
    assert tuple(field.name for field in fields(Bar)) == _FIELDS
    bar = Bar(**valid)
    for name, value in valid.items():
        actual = getattr(bar, name)
        assert type(actual) is type(value), name
        assert actual == value, name
    assert bar.time_utc.utcoffset() == timedelta(0)

    # Accepted values: no spread, every supported timeframe with 1..timeframe M1, zero volume,
    # an exponent form of a finite Decimal.
    assert Bar(**{**valid, "spread": None}).spread is None
    for timeframe in sorted(tb.TIMEFRAMES_MINUTES):
        assert Bar(**{**valid, "timeframe": timeframe, "m1_count": timeframe}).m1_count == timeframe
        assert Bar(**{**valid, "timeframe": timeframe, "m1_count": 1}).timeframe == timeframe
    assert Bar(**{**valid, "tick_volume": 0}).tick_volume == 0
    assert Bar(**{**valid, "open": Decimal("4.000000E+3")}).open == Decimal("4000")
    # Construction checks types and finiteness only: an inconsistent or non-positive price and
    # a negative spread must construct, so that validate_m1 can report them (AC-03).
    assert Bar(**{**valid, "high": Decimal("3999.000")}).high == Decimal("3999.000")
    assert Bar(**{**valid, "low": Decimal("0")}).low == Decimal("0")
    assert Bar(**{**valid, "low": Decimal("-1")}).low == Decimal("-1")
    assert Bar(**{**valid, "spread": -3}).spread == -3

    # Wrong types, deliberately including float, bool and subclasses -> TypeError.
    wrong = {
        **{name: (True, 1.0, "1", _Str("1"), Decimal("1"), _Int(1), None)
           for name in ("time_raw", "timeframe", "tick_volume", "m1_count")},
        "spread": (True, 240.0, "240", _Str("240"), Decimal("240"), _Int(240)),
        **{name: (4000, 4000.0, "4000", _Str("4000"), True, _Dec("4000.000"), None)
           for name in ("open", "high", "low", "close")},
        "time_utc": (raw, "2026-03-10T13:00:00+00:00", date(2026, 3, 10), True, None,
                     _Datetime(2026, 3, 10, 13, 0, tzinfo=UTC)),
    }
    for name, values in wrong.items():
        for bad in values:
            with pytest.raises(TypeError):
                Bar(**{**valid, name: bad})
    # A naive datetime is not "aware UTC"; either refusal class is accepted.
    with pytest.raises((TypeError, ValueError)):
        Bar(**{**valid, "time_utc": datetime(2026, 3, 10, 13, 0)})
    # Finite-but-unsupported values -> ValueError.
    for name in ("open", "high", "low", "close"):
        for bad in (Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with pytest.raises(ValueError):
                Bar(**{**valid, name: bad})
    for bad in (0, 7, 13, 25, -15, 1441):
        assert bad not in tb.TIMEFRAMES_MINUTES
        with pytest.raises(ValueError):
            Bar(**{**valid, "timeframe": bad})

    # Frozen with slots: no field can be set or deleted, and no attribute can be added. On
    # CPython 3.12 a new attribute on @dataclass(frozen=True, slots=True) raises TypeError
    # instead of FrozenInstanceError (review tests-r1 F2); either refusal is accepted there.
    for name in _FIELDS:
        with pytest.raises(FrozenInstanceError):
            setattr(bar, name, getattr(bar, name))
        with pytest.raises(FrozenInstanceError):
            delattr(bar, name)
    with pytest.raises((FrozenInstanceError, TypeError)):
        bar.extra = 1
    assert not hasattr(bar, "__dict__")
    assert Bar(**valid) == bar


def test_ac01_v11_bar_refuses_negative_volume_m1_count_below_one_and_a_non_utc_offset(monkeypatch):
    (Bar,) = _api(monkeypatch, "AC-01", "core.Bar")
    tb = _tb()
    rule = tb.rule_for(SERVER)
    raw = _raw(f"{DAY}T13:00")
    utc = tb.to_utc(raw, rule)
    valid = dict(
        time_raw=raw, time_utc=utc, timeframe=1,
        open=Decimal("4000.000"), high=Decimal("4000.300"), low=Decimal("3999.900"),
        close=Decimal("4000.200"), spread=240, tick_volume=7, m1_count=1,
    )
    # Contract v1.1 item 1: ValueError for tick_volume < 0 and m1_count < 1.
    for name, bad in (("tick_volume", -1), ("tick_volume", -7), ("m1_count", 0), ("m1_count", -1)):
        with pytest.raises(ValueError):
            Bar(**{**valid, name: bad})
    # ValueError for an aware time_utc whose offset is not 0, even at the same instant.
    for zoned in (utc.astimezone(timezone(timedelta(hours=7))), tb.to_zone(utc, "Asia/Bangkok"),
                  tb.to_zone(utc, "America/New_York")):
        assert zoned == utc and zoned.utcoffset() != timedelta(0)
        with pytest.raises(ValueError):
            Bar(**{**valid, "time_utc": zoned})
    # No upper bound on m1_count: duplicate M1 times can put more M1 than the timeframe into
    # one aggregated bar, and those are reported as duplicate_time (v1.1 item 1).
    for timeframe, m1_count in ((15, 16), (15, 30), (1440, 1441)):
        bar = Bar(**{**valid, "timeframe": timeframe, "m1_count": m1_count})
        assert (bar.timeframe, bar.m1_count) == (timeframe, m1_count)


def test_ac02_m15_aggregation_matches_the_golden_tables(monkeypatch):
    Bar, validate_m1, aggregate, AggregatedBar, Defect, H001_CLOSURES = _api(
        monkeypatch, "AC-02", "core.Bar", "snapshot.validate_m1", "snapshot.aggregate",
        "snapshot.AggregatedBar", "snapshot.Defect", "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    golden = _golden()
    rule = tb.rule_for(golden["RULE_SERVER"])
    day = golden["DAY"]
    assert _raw(f"{day}T13:00") == golden["ANCHOR_RAW"]
    bars = [
        _m1(Bar, tb, rule, f"{day}T{hhmm}", open_, high, low, close, spread, volume)
        for hhmm, open_, high, low, close, spread, volume in golden["M1_ROWS"]
    ]
    assert len(bars) == golden["M1_COUNT"]
    before = _snapshot(bars)

    report = validate_m1(bars, rule, H001_CLOSURES, golden["MAX_GAP_MINUTES"])
    _check_report(report, Defect, bars)
    assert _defects(report) == _expected(
        (code, severity, f"{day}T{hhmm}") for code, severity, hhmm in golden["REPORT_DEFECTS"]
    )
    assert dict(report.days) == {
        date.fromisoformat(iso): status for iso, status in golden["REPORT_DAYS"]
    }

    result = aggregate(bars, 15, rule, report)
    assert _snapshot(bars) == before
    assert type(result) is tuple
    assert len(result) == len(golden["M15_ROWS"])
    for actual, expected in zip(result, golden["M15_ROWS"], strict=True):
        hhmm, open_, high, low, close, spread, volume, m1_count, flags = expected
        assert isinstance(actual, AggregatedBar), hhmm
        bar = actual.bar
        assert type(bar) is Bar, hhmm
        raw = _raw(f"{day}T{hhmm}")
        assert bar.time_raw == raw, hhmm
        assert bar.time_raw == tb.bar_open(raw, 15, rule), hhmm
        assert bar.time_utc == tb.to_utc(raw, rule), hhmm
        assert bar.timeframe == 15, hhmm
        for name, value in (("open", open_), ("high", high), ("low", low), ("close", close)):
            price = getattr(bar, name)
            assert type(price) is Decimal, (hhmm, name)
            assert price == Decimal(value), (hhmm, name)
        assert bar.spread == spread, hhmm
        if spread is not None:
            assert type(bar.spread) is int, hhmm
        assert type(bar.tick_volume) is int and bar.tick_volume == volume, hhmm
        assert type(bar.m1_count) is int and bar.m1_count == m1_count, hhmm
        assert type(actual.flags) is frozenset, hhmm
        assert actual.flags == frozenset(flags), hhmm
    opens = [aggregated.bar.time_raw for aggregated in result]
    assert opens == sorted(opens)
    for hhmm in golden["ABSENT_M15"]:
        assert _raw(f"{day}T{hhmm}") not in opens
    # No M1 was dropped or invented: the M15 counts add up to the input.
    assert sum(aggregated.bar.m1_count for aggregated in result) == golden["M1_COUNT"]
    # Results depend on the input only, and a tuple is a Sequence too.
    assert aggregate(bars, 15, rule, report) == result
    again = validate_m1(tuple(bars), rule, H001_CLOSURES, golden["MAX_GAP_MINUTES"])
    assert _defects(again) == _defects(report)
    assert dict(again.days) == dict(report.days)
    assert aggregate(tuple(bars), 15, rule, again) == result
    assert _snapshot(bars) == before
    # AggregatedBar, ValidationReport and Defect are frozen.
    for instance, name in ((result[0], "flags"), (report, "m1_bars"), (report.defects[0], "detail")):
        with pytest.raises(AttributeError):
            setattr(instance, name, None)


def test_ac02_m15_open_times_raw_and_utc_under_rules_whose_offset_is_not_zero(monkeypatch):
    Bar, validate_m1, aggregate, H001_CLOSURES = _api(
        monkeypatch, "AC-02", "core.Bar", "snapshot.validate_m1", "snapshot.aggregate",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    measured = tb.rule_for(SERVER)
    # Review tests-r1 F4. Raw time two hours ahead of UTC (the AC-05 synthetic server): raw
    # 2026-03-10 00:30..00:34 is 2026-03-09 22:30..22:34 UTC (18:30 New York, EDT, in
    # session), so one incomplete M15 bar opens at raw 00:30 = 22:30 UTC.
    shifted = replace(measured, server="synthetic-test", offset_seconds=7200, version="test")
    ahead = _series(Bar, tb, shifted, _minutes("2026-03-10T00:30", 5))
    report = validate_m1(ahead, shifted, H001_CLOSURES, 5)
    assert _defects(report) == []
    result = aggregate(ahead, 15, shifted, report)
    assert _aggregated(result) == [(_raw("2026-03-10T00:30"), 5, frozenset({"incomplete"}))]
    assert result[0].bar.time_utc == datetime(2026, 3, 9, 22, 30, tzinfo=UTC)
    # Raw time ten minutes ahead of UTC: the M15 grid lies on UTC, so raw 22:38..22:42 on
    # 2026-03-09 (22:28..22:32 UTC) splits into the slots that open at raw 22:25 (22:15 UTC)
    # and raw 22:40 (22:30 UTC). A floor taken on raw seconds would give one slot at raw 22:30.
    odd = replace(measured, server="synthetic-test", offset_seconds=600, version="test")
    bars = _series(Bar, tb, odd, _minutes("2026-03-09T22:38", 5))
    report = validate_m1(bars, odd, H001_CLOSURES, 5)
    assert _defects(report) == []
    assert dict(report.days) == {date(2026, 3, 9): "PASS"}
    result = aggregate(bars, 15, odd, report)
    assert _aggregated(result) == [
        (_raw("2026-03-09T22:25"), 2, frozenset({"incomplete"})),
        (_raw("2026-03-09T22:40"), 3, frozenset({"incomplete"})),
    ]
    assert [aggregated.bar.time_utc for aggregated in result] == [
        datetime(2026, 3, 9, 22, 15, tzinfo=UTC), datetime(2026, 3, 9, 22, 30, tzinfo=UTC),
    ]
    for aggregated in result:
        assert aggregated.bar.time_raw == tb.bar_open(aggregated.bar.time_raw, 15, odd)
        assert aggregated.bar.time_utc == tb.to_utc(aggregated.bar.time_raw, odd)


def test_ac02_v11_aggregate_keeps_duplicate_and_out_of_order_m1_and_flags_them(monkeypatch):
    Bar, validate_m1, aggregate, H001_CLOSURES = _api(
        monkeypatch, "AC-02", "core.Bar", "snapshot.validate_m1", "snapshot.aggregate",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    # Contract v1.1 items 1 and 5: aggregate neither refuses nor drops such M1. Members of a
    # slot are ordered by time_raw, stably, so of two 13:14 copies the later one is the last M1.
    isos = (*_minutes(f"{DAY}T13:00", 15), f"{DAY}T13:14")
    bars = _series(Bar, tb, rule, isos, {15: {"close": "4000.250", "spread": 260}})
    before = _snapshot(bars)
    report = validate_m1(bars, rule, H001_CLOSURES, 5)
    assert _defects(report) == _expected((("duplicate_time", "STOP", f"{DAY}T13:14"),))
    result = aggregate(bars, 15, rule, report)
    assert _snapshot(bars) == before
    assert _aggregated(result) == [(_raw(f"{DAY}T13:00"), 16, frozenset({"duplicate_time"}))]
    bar = result[0].bar
    assert bar.m1_count > bar.timeframe == 15
    assert (bar.open, bar.high, bar.low, bar.close) == (
        Decimal("4000.000"), Decimal("4000.300"), Decimal("3999.900"), Decimal("4000.250"),
    )
    assert (bar.spread, bar.tick_volume) == (260, 16 * 7)
    assert bar.time_utc == tb.to_utc(_raw(f"{DAY}T13:00"), rule)
    # 13:01..13:14, then 13:00 (below its predecessor): the bar still opens with the 13:00 M1
    # and closes with the 13:14 M1.
    isos = (*_minutes(f"{DAY}T13:01", 14), f"{DAY}T13:00")
    bars = _series(Bar, tb, rule, isos, {13: {"close": "4000.250"}, 14: {"open_": "3999.950"}})
    before = _snapshot(bars)
    report = validate_m1(bars, rule, H001_CLOSURES, 5)
    assert _defects(report) == _expected((("time_not_increasing", "STOP", f"{DAY}T13:00"),))
    result = aggregate(bars, 15, rule, report)
    assert _snapshot(bars) == before
    assert _aggregated(result) == [(_raw(f"{DAY}T13:00"), 15, frozenset({"time_not_increasing"}))]
    assert (result[0].bar.open, result[0].bar.close) == (Decimal("3999.950"), Decimal("4000.250"))


_BASE = _minutes(f"{DAY}T13:00", 10)
_MIDDLE = f"{DAY}T13:05"
_STOP = {DAY: "STOP"}
_WARN = {DAY: "WARN"}
_PASS = {DAY: "PASS"}

# (label, M1 open times, {index: field overrides}, expected (code, severity, time), days)
_DEFECT_CASES = (
    ("clean series", _BASE, {}, (), _PASS),
    ("time_not_increasing: 13:03 follows 13:04",
     (*_BASE[:3], f"{DAY}T13:04", f"{DAY}T13:03", *_BASE[5:]), {},
     (("time_not_increasing", "STOP", f"{DAY}T13:03"),), _STOP),
    ("duplicate_time: 13:05 twice",
     (*_BASE[:6], _MIDDLE, *_BASE[6:9]), {},
     (("duplicate_time", "STOP", _MIDDLE),), _STOP),
    ("not_minute_aligned: 13:05:30",
     (*_BASE[:5], f"{DAY}T13:05:30", *_BASE[6:]), {},
     (("not_minute_aligned", "STOP", f"{DAY}T13:05:30"),), _STOP),
    ("time_rule_mismatch: time_utc one second after to_utc(time_raw, rule)",
     _BASE, {5: {"time_utc_shift": 1}},
     (("time_rule_mismatch", "STOP", _MIDDLE),), _STOP),
    ("ohlc_inconsistent: high below low",
     _BASE, {5: {"high": "3999.800"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE),), _STOP),
    ("ohlc_inconsistent: open above high",
     _BASE, {5: {"open_": "4000.400"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE),), _STOP),
    ("ohlc_inconsistent: open below low",
     _BASE, {5: {"open_": "3999.800"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE),), _STOP),
    ("ohlc_inconsistent: close below low",
     _BASE, {5: {"close": "3999.800"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE),), _STOP),
    ("open equal to high and close equal to low are inside [low, high]",
     _BASE, {5: {"open_": "4000.300", "close": "3999.900"}}, (), _PASS),
    ("non_positive_price: low is zero (open and close stay inside [0, high])",
     _BASE, {5: {"low": "0"}},
     (("non_positive_price", "STOP", _MIDDLE),), _STOP),
    ("non_positive_price: low is negative",
     _BASE, {5: {"low": "-0.001"}},
     (("non_positive_price", "STOP", _MIDDLE),), _STOP),
    ("non_positive_price: open is zero, so also below low",
     _BASE, {5: {"open_": "0"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE), ("non_positive_price", "STOP", _MIDDLE)), _STOP),
    ("non_positive_price: high is zero, so also below low",
     _BASE, {5: {"high": "0"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE), ("non_positive_price", "STOP", _MIDDLE)), _STOP),
    ("non_positive_price: close is negative, so also below low",
     _BASE, {5: {"close": "-0.001"}},
     (("ohlc_inconsistent", "STOP", _MIDDLE), ("non_positive_price", "STOP", _MIDDLE)), _STOP),
    ("negative_spread", _BASE, {5: {"spread": -1}},
     (("negative_spread", "STOP", _MIDDLE),), _STOP),
    ("missing_spread", _BASE, {5: {"spread": None}},
     (("missing_spread", "WARN", _MIDDLE),), _WARN),
    ("unexpected_gap: 13:05..13:10 missing (6 > 5), reported at the first bar after",
     (*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:11", 5)), {},
     (("unexpected_gap", "WARN", f"{DAY}T13:11"),), _WARN),
    ("empty_weekday: Wednesday 2026-03-11 has no bar between Tuesday and Thursday",
     (*_minutes("2026-03-10T13:00", 5), *_minutes("2026-03-12T13:00", 5)), {},
     (("empty_weekday", "UNKNOWN", None), ("unexpected_gap", "WARN", "2026-03-12T13:00")),
     {"2026-03-10": "PASS", "2026-03-11": "UNKNOWN", "2026-03-12": "WARN"}),
    ("two defects on one bar keep one time each",
     _BASE, {5: {"spread": None, "low": "0"}},
     (("missing_spread", "WARN", _MIDDLE), ("non_positive_price", "STOP", _MIDDLE)), _STOP),
    ("defects on different bars keep their own times",
     _BASE, {2: {"spread": -1}, 7: {"spread": None}},
     (("negative_spread", "STOP", f"{DAY}T13:02"), ("missing_spread", "WARN", f"{DAY}T13:07")),
     _STOP),
    ("single bar", _BASE[:1], {}, (), _PASS),
    ("single bar with a defect", _BASE[:1], {0: {"spread": None}},
     (("missing_spread", "WARN", f"{DAY}T13:00"),), _WARN),
)


@pytest.mark.parametrize("row", _DEFECT_CASES, ids=[row[0] for row in _DEFECT_CASES])
def test_ac03_each_defect_code_severity_and_time_with_input_untouched(monkeypatch, row):
    Bar, validate_m1, Defect, H001_CLOSURES = _api(
        monkeypatch, "AC-03", "core.Bar", "snapshot.validate_m1", "snapshot.Defect",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    _, isos, overrides, expected, days = row
    bars = _series(Bar, tb, rule, isos, overrides)
    before = _snapshot(bars)
    report = validate_m1(bars, rule, H001_CLOSURES, 5)
    assert _snapshot(bars) == before
    _check_report(report, Defect, bars)
    assert _defects(report) == _expected(expected)
    assert dict(report.days) == {date.fromisoformat(iso): status for iso, status in days.items()}
    # Calling again with the same input gives the same report (no hidden state).
    assert _defects(validate_m1(bars, rule, H001_CLOSURES, 5)) == _defects(report)
    assert _snapshot(bars) == before


def test_ac03_time_rule_mismatch_is_judged_under_the_validating_rule(monkeypatch):
    Bar, validate_m1, Defect, H001_CLOSURES = _api(
        monkeypatch, "AC-03", "core.Bar", "snapshot.validate_m1", "snapshot.Defect",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    measured = tb.rule_for(SERVER)
    # A synthetic server whose raw time runs two hours ahead of UTC (raw = UTC + 7200).
    shifted = replace(measured, server="synthetic-test", offset_seconds=7200, version="test")
    bars = _series(Bar, tb, measured, _BASE)  # time_utc computed under offset 0
    before = _snapshot(bars)
    report = validate_m1(bars, shifted, H001_CLOSURES, 5)
    assert _snapshot(bars) == before
    _check_report(report, Defect, bars)
    assert _defects(report) == _expected(
        ("time_rule_mismatch", "STOP", iso) for iso in _BASE
    )
    # Days are UTC days under the rule: raw 13:00..13:09 is 11:00..11:09 UTC, still 2026-03-10.
    assert dict(report.days) == {date(2026, 3, 10): "STOP"}
    # The same bars rebuilt under the shifted rule are clean under it.
    rebuilt = _series(Bar, tb, shifted, _BASE)
    assert _defects(validate_m1(rebuilt, shifted, H001_CLOSURES, 5)) == []
    assert dict(validate_m1(rebuilt, shifted, H001_CLOSURES, 5).days) == {date(2026, 3, 10): "PASS"}


def test_ac03_empty_input_and_wrong_argument_types(monkeypatch):
    Bar, validate_m1, aggregate, Defect, H001_CLOSURES = _api(
        monkeypatch, "AC-03", "core.Bar", "snapshot.validate_m1", "snapshot.aggregate",
        "snapshot.Defect", "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    empty = validate_m1([], rule, H001_CLOSURES, 5)
    _check_report(empty, Defect, [])
    assert empty.defects == ()
    assert dict(empty.days) == {}
    assert aggregate([], 15, rule, empty) == ()

    bars = _series(Bar, tb, rule, _BASE)
    report = validate_m1(bars, rule, H001_CLOSURES, 5)
    for bad in (True, 5.0, "5", _Str("5"), Decimal("5"), _Int(5), None):
        with pytest.raises(TypeError):
            validate_m1(bars, rule, H001_CLOSURES, bad)
    for bad in (True, 15.0, "15", _Str("15"), Decimal("15"), _Int(15), None):
        with pytest.raises(TypeError):
            aggregate(bars, bad, rule, report)
    for bad in (0, 7, 13):
        assert bad not in tb.TIMEFRAMES_MINUTES
        with pytest.raises(ValueError):
            aggregate(bars, bad, rule, report)
    for bad in (None, rule.offset_seconds, "Exness-MT5Trial14"):
        with pytest.raises(TypeError):
            validate_m1(bars, bad, H001_CLOSURES, 5)
        with pytest.raises(TypeError):
            aggregate(bars, 15, bad, report)
    for bad in (None, "America/New_York", H001_CLOSURES.daily_break):
        with pytest.raises(TypeError):
            validate_m1(bars, rule, bad, 5)
    for bad in (None, report.defects, {"defects": ()}):
        with pytest.raises(TypeError):
            aggregate(bars, 15, rule, bad)

    class _SubBar(Bar):
        pass

    valid = {field.name: getattr(bars[0], field.name) for field in fields(bars[0])}
    # Each bad element goes to aggregate with a report of matching length (review tests-r1
    # F11), so a check of the report against the input cannot refuse it first.
    one = validate_m1(bars[:1], rule, H001_CLOSURES, 5)
    for element in (object(), bars[0].time_raw, valid, _SubBar(**valid)):
        with pytest.raises(TypeError):
            validate_m1([element], rule, H001_CLOSURES, 5)
        with pytest.raises(TypeError):
            validate_m1([*bars[:3], element, *bars[3:]], rule, H001_CLOSURES, 5)
        with pytest.raises(TypeError):
            aggregate([element], 15, rule, one)


def test_ac03_v11_negative_max_gap_minutes_is_refused(monkeypatch):
    Bar, validate_m1, H001_CLOSURES = _api(
        monkeypatch, "AC-03", "core.Bar", "snapshot.validate_m1", "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    # Contract v1.1 item 2: ValueError, with or without bars; 0 stays valid (AC-04).
    for bars in ([], _series(Bar, tb, rule, _BASE)):
        for bad in (-1, -5):
            with pytest.raises(ValueError):
                validate_m1(bars, rule, H001_CLOSURES, bad)
        assert validate_m1(bars, rule, H001_CLOSURES, 0).m1_bars == len(bars)


def test_ac04_h001_closure_calendar_values_and_the_calendar_argument(monkeypatch):
    Bar, validate_m1, ClosureCalendar, H001_CLOSURES = _api(
        monkeypatch, "AC-04", "core.Bar", "snapshot.validate_m1", "snapshot.ClosureCalendar",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    # D2 [A]: America/New_York, 17:00-18:00 daily, Friday 17:00 -> Sunday 18:00.
    assert isinstance(H001_CLOSURES, ClosureCalendar)
    assert H001_CLOSURES.zone == "America/New_York"
    assert H001_CLOSURES.daily_break == (time(17, 0), time(18, 0))
    (start_day, start_time), (end_day, end_time) = H001_CLOSURES.weekend
    # int-valued, never bool; an int subclass such as calendar.FRIDAY is fine (review F8).
    for weekday in (start_day, end_day):
        assert isinstance(weekday, int) and not isinstance(weekday, bool)
    assert (start_day, start_time) == (4, time(17, 0))
    assert (end_day, end_time) == (6, time(18, 0))
    assert "assumed" in str(H001_CLOSURES.provenance).lower()
    with pytest.raises(AttributeError):
        H001_CLOSURES.zone = "UTC"

    # The calendar argument is used, not a built-in one: a break that starts at 16:50 New York
    # makes 20:49 -> 22:00 UTC (16:49 -> 18:00 EDT) a closure; under H001 the ten in-session
    # minutes 16:50..16:59 exceed max_gap_minutes 5.
    wider = ClosureCalendar(
        zone=H001_CLOSURES.zone, daily_break=(time(16, 50), time(18, 0)),
        weekend=H001_CLOSURES.weekend, provenance=H001_CLOSURES.provenance,
    )
    bars = _series(Bar, tb, rule, (*_minutes(f"{DAY}T20:45", 5), *_minutes(f"{DAY}T22:00", 5)))
    assert _defects(validate_m1(bars, rule, wider, 5)) == []
    assert _defects(validate_m1(bars, rule, H001_CLOSURES, 5)) == _expected(
        (("unexpected_gap", "WARN", f"{DAY}T22:00"),)
    )
    # The zone is used too: the same clock times in UTC are a closure only under a UTC calendar.
    utc_calendar = ClosureCalendar(
        zone="UTC", daily_break=H001_CLOSURES.daily_break, weekend=H001_CLOSURES.weekend,
        provenance=H001_CLOSURES.provenance,
    )
    bars = _series(Bar, tb, rule, (*_minutes(f"{DAY}T16:55", 5), *_minutes(f"{DAY}T18:00", 5)))
    assert _defects(validate_m1(bars, rule, utc_calendar, 5)) == []
    assert _defects(validate_m1(bars, rule, H001_CLOSURES, 5)) == _expected(
        (("unexpected_gap", "WARN", f"{DAY}T18:00"),)
    )


# New York 2026: DST begins Sunday 2026-03-08 02:00 (UTC-5 -> UTC-4) and ends Sunday
# 2026-11-01 02:00 (UTC-4 -> UTC-5). The 17:00 New York break is 22:00 UTC on EST days and
# 21:00 UTC on EDT days; 18:00 New York is 23:00 and 22:00 UTC.
# (label, M1 open times, max_gap_minutes, expected (code, severity, time))
_GAP_CASES = (
    ("daily break on an EST day: Thu 2026-03-05 16:59 -> 18:00 NY = 21:59 -> 23:00 UTC",
     (*_minutes("2026-03-05T21:55", 5), *_minutes("2026-03-05T23:00", 5)), 5, ()),
    ("daily break on the first EDT weekday: Mon 2026-03-09 16:59 -> 18:00 NY = 20:59 -> 22:00 UTC",
     (*_minutes("2026-03-09T20:55", 5), *_minutes("2026-03-09T22:00", 5)), 5, ()),
    ("daily break on an EDT day: Thu 2026-10-29 20:59 -> 22:00 UTC",
     (*_minutes("2026-10-29T20:55", 5), *_minutes("2026-10-29T22:00", 5)), 5, ()),
    ("daily break on the first EST weekday: Mon 2026-11-02 16:59 -> 18:00 NY = 21:59 -> 23:00 UTC",
     (*_minutes("2026-11-02T21:55", 5), *_minutes("2026-11-02T23:00", 5)), 5, ()),
    ("the EST break hours are in session once EDT began: Mon 2026-03-09 22:04 -> 23:05 UTC "
     "= 18:04 -> 19:05 NY, 60 missing in session",
     (*_minutes("2026-03-09T22:00", 5), *_minutes("2026-03-09T23:05", 5)), 5,
     (("unexpected_gap", "WARN", "2026-03-09T23:05"),)),
    ("the EDT break hours are in session once EST resumed: Mon 2026-11-02 20:59 -> 21:55 UTC "
     "= 15:59 -> 16:55 NY, 55 missing in session",
     (*_minutes("2026-11-02T20:55", 5), *_minutes("2026-11-02T21:55", 5)), 5,
     (("unexpected_gap", "WARN", "2026-11-02T21:55"),)),
    ("break plus five in-session minutes (16:58, 16:59, 18:00..18:02 NY) is not a defect: "
     "Tue 2026-03-10 20:57 -> 22:03 UTC",
     (*_minutes("2026-03-10T20:53", 5), *_minutes("2026-03-10T22:03", 5)), 5, ()),
    ("break plus six in-session minutes is a defect: Tue 2026-03-10 20:57 -> 22:04 UTC",
     (*_minutes("2026-03-10T20:53", 5), *_minutes("2026-03-10T22:04", 5)), 5,
     (("unexpected_gap", "WARN", "2026-03-10T22:04"),)),
    ("weekend around the March change: Fri 2026-03-06 16:59 EST -> Sun 2026-03-08 18:00 EDT "
     "= 21:59 -> 22:00 UTC (48 h)",
     (*_minutes("2026-03-06T21:55", 5), *_minutes("2026-03-08T22:00", 5)), 5, ()),
    ("weekend around the November change: Fri 2026-10-30 16:59 EDT -> Sun 2026-11-01 18:00 EST "
     "= 20:59 -> 23:00 UTC (50 h)",
     (*_minutes("2026-10-30T20:55", 5), *_minutes("2026-11-01T23:00", 5)), 5, ()),
    ("ordinary EDT weekend: Fri 2026-03-13 20:59 -> Sun 2026-03-15 22:00 UTC (49 h)",
     (*_minutes("2026-03-13T20:55", 5), *_minutes("2026-03-15T22:00", 5)), 5, ()),
    ("weekend plus six in-session minutes: Fri 2026-03-13 20:57 -> Sun 2026-03-15 22:04 UTC",
     (*_minutes("2026-03-13T20:53", 5), *_minutes("2026-03-15T22:04", 5)), 5,
     (("unexpected_gap", "WARN", "2026-03-15T22:04"),)),
    ("no bar on Saturday or Sunday: Fri 2026-03-13 20:59 -> Mon 2026-03-16 13:00 UTC misses "
     "Sun 18:00 NY onwards, 900 in session; neither weekend day is a key of report.days",
     (*_minutes("2026-03-13T20:55", 5), *_minutes("2026-03-16T13:00", 5)), 5,
     (("unexpected_gap", "WARN", "2026-03-16T13:00"),)),
    ("in-session gap of exactly max_gap_minutes (5 missing): 13:04 -> 13:10",
     (*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:10", 5)), 5, ()),
    ("in-session gap one minute above (6 missing): 13:04 -> 13:11",
     (*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:11", 5)), 5,
     (("unexpected_gap", "WARN", f"{DAY}T13:11"),)),
    ("max_gap_minutes 2: two missing minutes pass",
     (*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:07", 5)), 2, ()),
    ("max_gap_minutes 2: three missing minutes fail",
     (*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:08", 5)), 2,
     (("unexpected_gap", "WARN", f"{DAY}T13:08"),)),
    ("max_gap_minutes 0: consecutive minutes pass", _minutes(f"{DAY}T13:00", 5), 0, ()),
    ("max_gap_minutes 0: one missing minute fails",
     (*_minutes(f"{DAY}T13:00", 3), *_minutes(f"{DAY}T13:04", 3)), 0,
     (("unexpected_gap", "WARN", f"{DAY}T13:04"),)),
    ("consecutive minutes across UTC midnight are not a gap: 2026-03-10 23:57 -> 03-11 00:02",
     _minutes("2026-03-10T23:57", 6), 5, ()),
)


@pytest.mark.parametrize("row", _GAP_CASES, ids=[row[0] for row in _GAP_CASES])
def test_ac04_gaps_against_the_new_york_calendar_on_both_dst_changes(monkeypatch, row):
    Bar, validate_m1, Defect, H001_CLOSURES = _api(
        monkeypatch, "AC-04", "core.Bar", "snapshot.validate_m1", "snapshot.Defect",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    _, isos, max_gap, expected = row
    bars = _series(Bar, tb, rule, isos)
    before = _snapshot(bars)
    report = validate_m1(bars, rule, H001_CLOSURES, max_gap)
    assert _snapshot(bars) == before
    _check_report(report, Defect, bars)
    assert _defects(report) == _expected(expected)
    # Day statuses: WARN on the UTC day of a reported gap, PASS on every other day with bars;
    # a weekend day without bars is never empty_weekday (checked by the exact list above) and
    # never a key of report.days, even inside the span (v1.1 item 5, review tests-r1 F3).
    warn_days = {tb.to_utc(_raw(iso), rule).date() for _, _, iso in expected}
    days = {bar.time_utc.date() for bar in bars}
    assert dict(report.days) == {day: ("WARN" if day in warn_days else "PASS") for day in days}


def _aggregated(result):
    return [(aggregated.bar.time_raw, aggregated.bar.m1_count, aggregated.flags) for aggregated in result]


def test_ac04_m15_bars_around_closures_and_unexpected_gaps(monkeypatch):
    Bar, validate_m1, aggregate, H001_CLOSURES = _api(
        monkeypatch, "AC-04", "core.Bar", "snapshot.validate_m1", "snapshot.aggregate",
        "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)

    def run(isos):
        bars = _series(Bar, tb, rule, isos)
        before = _snapshot(bars)
        result = aggregate(bars, 15, rule, validate_m1(bars, rule, H001_CLOSURES, 5))
        assert _snapshot(bars) == before
        assert sum(aggregated.bar.m1_count for aggregated in result) == len(bars)
        return _aggregated(result)

    # Daily break on an EDT day: two complete slots, nothing for 21:00..21:45 UTC, no flag.
    assert run((*_minutes("2026-03-09T20:45", 15), *_minutes("2026-03-09T22:00", 15))) == [
        (_raw("2026-03-09T20:45"), 15, frozenset()),
        (_raw("2026-03-09T22:00"), 15, frozenset()),
    ]
    # Weekend: the same on both sides of 49 closed hours.
    assert run((*_minutes("2026-03-13T20:45", 15), *_minutes("2026-03-15T22:00", 15))) == [
        (_raw("2026-03-13T20:45"), 15, frozenset()),
        (_raw("2026-03-15T22:00"), 15, frozenset()),
    ]
    # Unexpected in-session gap 13:05..13:10: the slot that holds the first bar after the gap
    # carries the defect code; both partial slots are incomplete.
    assert run((*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:11", 5))) == [
        (_raw(f"{DAY}T13:00"), 9, frozenset({"incomplete", "unexpected_gap"})),
        (_raw(f"{DAY}T13:15"), 1, frozenset({"incomplete"})),
    ]
    # A gap of exactly max_gap_minutes leaves the slot incomplete but carries no gap code.
    assert run((*_minutes(f"{DAY}T13:00", 5), *_minutes(f"{DAY}T13:10", 5))) == [
        (_raw(f"{DAY}T13:00"), 10, frozenset({"incomplete"})),
    ]
    # Break plus six in-session minutes: the first slot after the break has the gap code.
    assert run((*_minutes(f"{DAY}T20:53", 5), *_minutes(f"{DAY}T22:04", 5))) == [
        (_raw(f"{DAY}T20:45"), 5, frozenset({"incomplete"})),
        (_raw(f"{DAY}T22:00"), 5, frozenset({"incomplete", "unexpected_gap"})),
    ]
    # A single M1 makes one incomplete M15 bar.
    assert run((f"{DAY}T13:07",)) == [(_raw(f"{DAY}T13:00"), 1, frozenset({"incomplete"}))]


def test_ac04_v11_report_carries_its_calendar_and_aggregate_judges_incomplete_by_it(monkeypatch):
    Bar, validate_m1, aggregate, ClosureCalendar, H001_CLOSURES = _api(
        monkeypatch, "AC-04", "core.Bar", "snapshot.validate_m1", "snapshot.aggregate",
        "snapshot.ClosureCalendar", "snapshot.H001_CLOSURES",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    # Contract v1.1 item 3 (review tests-r1 F12). A daily break of 16:50-18:10 New York starts
    # and ends off the M15 grid: on Tue 2026-03-10 (EDT) it is 20:50-22:10 UTC, so slot 20:45
    # is in session for 20:45..20:49 only and slot 22:00 for 22:10..22:14 only.
    offgrid = ClosureCalendar(
        zone=H001_CLOSURES.zone, daily_break=(time(16, 50), time(18, 10)),
        weekend=H001_CLOSURES.weekend, provenance=H001_CLOSURES.provenance,
    )
    assert validate_m1([], rule, offgrid, 5).calendar == offgrid
    bars = _series(Bar, tb, rule, (*_minutes(f"{DAY}T20:45", 5), *_minutes(f"{DAY}T22:10", 5)))
    report = validate_m1(bars, rule, offgrid, 5)
    assert isinstance(report.calendar, ClosureCalendar)
    assert report.calendar == offgrid
    with pytest.raises(AttributeError):
        report.calendar = H001_CLOSURES
    assert _defects(report) == []
    # Every missing minute of both slots is inside the closure: neither bar is incomplete.
    assert _aggregated(aggregate(bars, 15, rule, report)) == [
        (_raw(f"{DAY}T20:45"), 5, frozenset()),
        (_raw(f"{DAY}T22:00"), 5, frozenset()),
    ]
    # The same bars under H001_CLOSURES: 16:50..16:59 and 18:00..18:09 New York are in session,
    # so both slots miss in-session minutes and the 20 missing minutes are an unexpected gap.
    h001 = validate_m1(bars, rule, H001_CLOSURES, 5)
    assert h001.calendar == H001_CLOSURES
    assert _defects(h001) == _expected((("unexpected_gap", "WARN", f"{DAY}T22:10"),))
    assert _aggregated(aggregate(bars, 15, rule, h001)) == [
        (_raw(f"{DAY}T20:45"), 5, frozenset({"incomplete"})),
        (_raw(f"{DAY}T22:00"), 5, frozenset({"incomplete", "unexpected_gap"})),
    ]
    # Under the off-grid calendar a partly closed slot is still incomplete when one of its
    # in-session minutes is missing: 20:49 in the first slot, 22:12 in the second.
    holes = (*_minutes(f"{DAY}T20:45", 4), f"{DAY}T22:10", f"{DAY}T22:11", f"{DAY}T22:13",
             f"{DAY}T22:14")
    bars = _series(Bar, tb, rule, holes)
    partial = validate_m1(bars, rule, offgrid, 5)
    assert _defects(partial) == []
    assert _aggregated(aggregate(bars, 15, rule, partial)) == [
        (_raw(f"{DAY}T20:45"), 4, frozenset({"incomplete"})),
        (_raw(f"{DAY}T22:00"), 4, frozenset({"incomplete"})),
    ]


def test_ac05_day_status_precedence_empty_weekday_and_utc_day_keys(monkeypatch):
    Bar, validate_m1, Defect, ValidationReport, H001_CLOSURES, Severity, DayStatus = _api(
        monkeypatch, "AC-05", "core.Bar", "snapshot.validate_m1", "snapshot.Defect",
        "snapshot.ValidationReport", "snapshot.H001_CLOSURES", "snapshot.Severity",
        "snapshot.DayStatus",
    )
    tb = _tb()
    rule = tb.rule_for(SERVER)
    # Monday 2026-03-09 .. Friday 2026-03-13, five M1 at 13:00 UTC each day; Wednesday absent.
    # Each day after Monday starts with the overnight gap (WARN at its first bar).
    week = (
        *_minutes("2026-03-09T13:00", 5),
        *_minutes("2026-03-10T13:00", 5),
        *_minutes("2026-03-12T13:00", 5),
        *_minutes("2026-03-13T13:00", 5),
    )
    bars = _series(Bar, tb, rule, week, {12: {"spread": -1}, 18: {"spread": None}})
    assert bars[12].time_raw == _raw("2026-03-12T13:02")
    assert bars[18].time_raw == _raw("2026-03-13T13:03")
    before = _snapshot(bars)
    report = validate_m1(bars, rule, H001_CLOSURES, 5)
    assert _snapshot(bars) == before
    assert isinstance(report, ValidationReport)
    _check_report(report, Defect, bars)
    assert _defects(report) == _expected((
        ("unexpected_gap", "WARN", "2026-03-10T13:00"),
        ("empty_weekday", "UNKNOWN", None),
        ("unexpected_gap", "WARN", "2026-03-12T13:00"),
        ("negative_spread", "STOP", "2026-03-12T13:02"),
        ("unexpected_gap", "WARN", "2026-03-13T13:00"),
        ("missing_spread", "WARN", "2026-03-13T13:03"),
    ))
    assert dict(report.days) == {
        date(2026, 3, 9): "PASS",      # no defect
        date(2026, 3, 10): "WARN",     # WARN only
        date(2026, 3, 11): "UNKNOWN",  # empty weekday
        date(2026, 3, 12): "STOP",     # STOP beats WARN
        date(2026, 3, 13): "WARN",     # two WARNs
    }
    # The mapping is read-only and the report is frozen.
    with pytest.raises(TypeError):
        report.days[date(2026, 3, 9)] = "STOP"
    with pytest.raises(TypeError):
        del report.days[date(2026, 3, 9)]
    with pytest.raises(AttributeError):
        report.m1_bars = 0
    assert dict(report.days)[date(2026, 3, 9)] == "PASS"
    assert Severity is not None and DayStatus is not None

    # Two STOP codes on one day, with a WARN: still one STOP day.
    mixed = _series(Bar, tb, rule, _BASE, {1: {"spread": -1}, 3: {"low": "0"}, 7: {"spread": None}})
    stop = validate_m1(mixed, rule, H001_CLOSURES, 5)
    assert _defects(stop) == _expected((
        ("negative_spread", "STOP", f"{DAY}T13:01"),
        ("non_positive_price", "STOP", f"{DAY}T13:03"),
        ("missing_spread", "WARN", f"{DAY}T13:07"),
    ))
    assert dict(stop.days) == {date(2026, 3, 10): "STOP"}

    # Days are keyed by the UTC date under the rule. On a synthetic server two hours ahead of
    # UTC, raw 2026-03-10 00:30..00:34 is 2026-03-09 22:30..22:34 UTC (18:30 New York, EDT,
    # in session), so the only day is 2026-03-09.
    shifted = replace(rule, server="synthetic-test", offset_seconds=7200, version="test")
    ahead = _series(Bar, tb, shifted, _minutes("2026-03-10T00:30", 5))
    assert ahead[0].time_utc == datetime(2026, 3, 9, 22, 30, tzinfo=UTC)
    moved = validate_m1(ahead, shifted, H001_CLOSURES, 5)
    _check_report(moved, Defect, ahead)
    assert _defects(moved) == []
    assert dict(moved.days) == {date(2026, 3, 9): "PASS"}
