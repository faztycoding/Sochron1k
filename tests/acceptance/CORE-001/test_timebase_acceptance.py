"""Owner-approved CORE-001 contract tests; run pytest from the repository root."""

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, asdict, is_dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from importlib import import_module
from pathlib import Path
from runpy import run_path

import pytest


def _api(monkeypatch, ac, *names):
    """Defer missing implementation to test execution, preserving clean collection."""
    monkeypatch.syspath_prepend(str(Path.cwd() / "src"))
    try:
        module = import_module("sochron.timebase")
    except ImportError as error:
        pytest.fail(f"{ac}: sochron.timebase not implemented ({error})", pytrace=False)
    symbols = []
    for name in names:
        try:
            symbols.append(getattr(module, name))
        except AttributeError:
            pytest.fail(f"{ac}: sochron.timebase.{name} not implemented", pytrace=False)
    return tuple(symbols)


def _golden():
    path = Path(__file__).resolve().parents[2] / "golden/CORE-001/timebase_cases.py"
    return run_path(str(path))


def test_ac01_raw_utc_milliseconds_and_fixed_round_trips(monkeypatch):
    TimeRule, RULES, rule_for, to_utc, to_raw = _api(
        monkeypatch, "AC-01", "TimeRule", "RULES", "rule_for", "to_utc", "to_raw"
    )
    rule = rule_for("Exness-MT5Trial14")
    assert isinstance(RULES, Mapping)
    assert set(RULES) == {"Exness-MT5Trial14"}
    assert isinstance(rule, TimeRule)
    assert is_dataclass(rule)
    assert asdict(rule) == {
        "server": "Exness-MT5Trial14",
        "symbol": "XAUUSDm",
        "terminal_build": 6274,
        "offset_seconds": 0,
        "evidence_from": date(2026, 10, 20),
        "evidence_to": date(2026, 10, 21),
        "evidence_ref": "docs/evidence/SPIKE-001.md",
        "version": "1",
    }
    assert RULES[rule.server] == rule
    golden = _golden()
    raw, msc, expected = golden["SPIKE_TICK"]
    converted = to_utc(raw, rule, msc=msc)
    assert converted == datetime.fromisoformat(expected)
    assert converted.utcoffset() == timedelta(0)
    assert converted.microsecond == 35000
    assert type(to_raw(converted, rule)) is int
    assert to_raw(converted, rule) == raw
    # Same instant expressed in another aware zone must have the same raw seconds.
    assert to_raw(datetime.fromisoformat("2026-10-21T02:53:12.035+07:00"), rule) == raw
    last_raw, last_msc, last_utc = golden["LAST_MILLISECOND"]
    last = to_utc(last_raw, rule, msc=last_msc)
    assert last == datetime.fromisoformat(last_utc)
    assert last.microsecond == 999000
    assert to_raw(last, rule) == last_raw
    for raw_value, utc_iso in golden["ROUND_TRIP_ROWS"]:
        utc = to_utc(raw_value, rule)
        assert utc == datetime.fromisoformat(utc_iso), f"AC-01: raw={raw_value}"
        assert utc.utcoffset() == timedelta(0), f"AC-01: raw={raw_value}"
        restored = to_raw(utc, rule)
        assert type(restored) is int
        assert restored == raw_value, f"AC-01: round trip raw={raw_value}"
        assert to_utc(restored, rule) == utc
    for offset, utc_iso in golden["SHIFTED_TICK_ROWS"]:
        synthetic = replace(rule, offset_seconds=offset)
        utc = to_utc(raw, synthetic, msc=msc)
        assert utc == datetime.fromisoformat(utc_iso), f"AC-01: offset={offset}"
        assert utc.utcoffset() == timedelta(0)
        assert to_raw(utc, synthetic) == raw


def test_ac02_new_york_window_across_both_dst_changes(monkeypatch):
    EntryWindow, NY_ENTRY_WINDOW, in_entry_window, to_zone = _api(
        monkeypatch, "AC-02", "EntryWindow", "NY_ENTRY_WINDOW", "in_entry_window", "to_zone"
    )
    assert isinstance(NY_ENTRY_WINDOW, EntryWindow)
    assert is_dataclass(NY_ENTRY_WINDOW)
    assert (NY_ENTRY_WINDOW.zone, NY_ENTRY_WINDOW.start, NY_ENTRY_WINDOW.end_inclusive) == (
        "America/New_York", time(3), time(15, 59)
    )
    for utc_iso, local_iso, abbreviation, expected in _golden()["NY_WINDOW_ROWS"]:
        utc = datetime.fromisoformat(utc_iso)
        local = to_zone(utc, "America/New_York")
        assert local.isoformat() == local_iso, f"AC-02: {utc_iso} local time"
        assert local.tzname() == abbreviation, f"AC-02: {utc_iso} EST/EDT"
        assert in_entry_window(utc) is expected, f"AC-02: {utc_iso} -> {local_iso}"
        assert in_entry_window(utc, NY_ENTRY_WINDOW) is expected
        assert in_entry_window(local) is expected
    # The declared window argument must be honored, including minute precision.
    custom = EntryWindow("Asia/Bangkok", time(23, 59), time(23, 59))
    assert in_entry_window(datetime(2026, 10, 20, 16, 59, 59, tzinfo=UTC), custom) is True
    assert in_entry_window(datetime(2026, 10, 20, 17, tzinfo=UTC), custom) is False


def test_ac03_bangkok_calendar_day_changes_at_1700_utc(monkeypatch):
    bangkok_date, to_zone = _api(monkeypatch, "AC-03", "bangkok_date", "to_zone")
    for utc_iso, local_iso, expected_date in _golden()["BANGKOK_ROWS"]:
        utc = datetime.fromisoformat(utc_iso)
        local = to_zone(utc, "Asia/Bangkok")
        assert local.isoformat() == local_iso, f"AC-03: {utc_iso}"
        assert local.utcoffset() == timedelta(hours=7)
        actual_date = bangkok_date(utc)
        assert type(actual_date) is date
        assert actual_date == date.fromisoformat(expected_date), f"AC-03: {utc_iso}"
        assert bangkok_date(local) == actual_date


def test_ac04_m1_and_tick_alignment_to_m15(monkeypatch):
    bar_open, rule_for, TIMEFRAMES_MINUTES, BadTimeframe = _api(
        monkeypatch, "AC-04", "bar_open", "rule_for", "TIMEFRAMES_MINUTES", "BadTimeframe"
    )
    assert set(TIMEFRAMES_MINUTES) == {
        1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720, 1440
    }
    rule = rule_for("Exness-MT5Trial14")
    golden = _golden()
    assert {tf for tf, _ in golden["TIMEFRAME_ROWS"]} == set(TIMEFRAMES_MINUTES)
    for timeframe, expected in golden["TIMEFRAME_ROWS"]:
        assert bar_open(1792525992, timeframe, rule) == expected, f"AC-04: timeframe={timeframe}"
    for raw, expected in golden["M1_TO_M15_ROWS"] + golden["EXTRA_BAR_ROWS"]:
        actual = bar_open(raw, 15, rule)
        assert type(actual) is int
        assert actual == expected, f"AC-04: raw={raw}, M15 expected={expected}"
    raw, timeframe, offset, expected = golden["SHIFTED_BAR"]
    assert bar_open(raw, timeframe, replace(rule, offset_seconds=offset)) == expected
    for timeframe in (7, 1441):
        with pytest.raises(BadTimeframe):
            bar_open(1792525992, timeframe, rule)


def test_ac05_reject_unknown_naive_out_of_range_and_mismatched_input(monkeypatch):
    (
        rule_for, to_utc, to_raw, to_zone, in_entry_window, bangkok_date, bar_open,
        TimebaseError, UnknownTimeRule, NaiveDatetime, RawTimeOutOfRange, RawTimeMismatch,
        BadTimeframe,
    ) = _api(
        monkeypatch, "AC-05", "rule_for", "to_utc", "to_raw", "to_zone", "in_entry_window",
        "bangkok_date", "bar_open", "TimebaseError", "UnknownTimeRule", "NaiveDatetime",
        "RawTimeOutOfRange", "RawTimeMismatch", "BadTimeframe",
    )
    assert issubclass(TimebaseError, ValueError)
    for error in (UnknownTimeRule, NaiveDatetime, RawTimeOutOfRange, RawTimeMismatch, BadTimeframe):
        assert issubclass(error, TimebaseError)
    with pytest.raises(UnknownTimeRule):
        rule_for("Other-Server")
    rule = rule_for("Exness-MT5Trial14")
    naive = datetime(2026, 10, 20, 19, 53, 12)
    for function, args in (
        (to_raw, (naive, rule)),
        (to_zone, (naive, "America/New_York")),
        (in_entry_window, (naive,)),
        (bangkok_date, (naive,)),
    ):
        with pytest.raises(NaiveDatetime):
            function(*args)
    for raw in (-1, 0, 946684799, 4102444800):
        with pytest.raises(RawTimeOutOfRange):
            to_utc(raw, rule)
        with pytest.raises(RawTimeOutOfRange):
            bar_open(raw, 15, rule)
    # The preceding last millisecond and following first millisecond mismatch the raw second.
    for msc in (1792525991999, 1792525993000):
        with pytest.raises(RawTimeMismatch):
            to_utc(1792525992, rule, msc=msc)


def test_ac06_classify_offsets_without_mutating_time_rules(monkeypatch):
    (
        classify_offset, OffsetClass, TimeRule, EntryWindow, RULES, rule_for, NY_ENTRY_WINDOW
    ) = _api(
        monkeypatch, "AC-06", "classify_offset", "OffsetClass", "TimeRule", "EntryWindow",
        "RULES", "rule_for", "NY_ENTRY_WINDOW",
    )
    before = {server: asdict(rule) for server, rule in RULES.items()}
    rule = rule_for("Exness-MT5Trial14")
    golden = _golden()
    for offsets, tolerance, kind, hours, samples in golden["OFFSET_ROWS"] + golden["OFFSET_EDGE_ROWS"]:
        result = classify_offset(offsets, tolerance_seconds=tolerance)
        assert isinstance(result, OffsetClass)
        assert is_dataclass(result)
        assert result.kind == kind, f"AC-06: {offsets}, tolerance={tolerance}"
        assert result.samples == samples
        if kind == "shifted":
            assert result.hours == hours
        # Non-shifted hours is not fixed by the contract; do not invent a sentinel.
        if tolerance == 120.0:
            assert classify_offset(offsets) == result
        assert {server: asdict(value) for server, value in RULES.items()} == before
        assert asdict(rule) == before["Exness-MT5Trial14"]
        assert asdict(rule_for("Exness-MT5Trial14")) == before["Exness-MT5Trial14"]
    for obj, cls, field, value in (
        (rule, TimeRule, "offset_seconds", 3600),
        (NY_ENTRY_WINDOW, EntryWindow, "start", time(4)),
        (classify_offset(()), OffsetClass, "kind", "ok"),
    ):
        assert isinstance(obj, cls)
        assert is_dataclass(obj)
        assert cls.__dataclass_params__.frozen is True
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)
