"""SPIKE-001 AC-02: the probe stops before reading anything else on a wrong or missing account.

A fake terminal module records every attribute the probe touches, so each refusal can prove
that nothing beyond initialize, account_info and shutdown was used. No terminal is needed.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import probe  # the spike module beside this test, importable after the path insert above

DEMO = 0
NOT_DEMO = 2
BEFORE_EXPIRY = probe.AUTH.valid_until - timedelta(days=1)


class FakeTerminal:
    ACCOUNT_TRADE_MODE_DEMO = DEMO

    def __init__(self, account, init_ok=True):
        self._account = account
        self._init_ok = init_ok
        self.calls: list[str] = []

    def initialize(self):
        self.calls.append("initialize")
        return self._init_ok

    def account_info(self):
        self.calls.append("account_info")
        return self._account

    def shutdown(self):
        self.calls.append("shutdown")

    def last_error(self):
        self.calls.append("last_error")
        return (-10003, "fake")

    def __getattr__(self, name):  # any other terminal call must not happen on a refusal
        self.calls.append(name)
        raise AssertionError(f"probe read {name} after a refusal")


def account(**overrides):
    base = dict(login=123458107, trade_mode=DEMO, server="Exness-MT5Trial14")
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.parametrize("acct, reason", [
    (None, "not logged in"),
    (account(trade_mode=NOT_DEMO), "is not Demo"),
    (account(server="Exness-MT5Real1"), "not the authorized server"),
    (account(login=123450001), "not the authorized account"),
])
def test_wrong_or_missing_account_stops_before_any_other_read(acct, reason):
    term = FakeTerminal(acct)
    code, report = probe.run(term, BEFORE_EXPIRY, samples=1, interval=0, history=False)
    assert code == 2
    assert reason in report["refused"]
    assert term.calls == ["initialize", "account_info", "shutdown"]
    assert set(report) == {"probe_started_bangkok", "symbol", "refused"}


def test_expired_authorization_stops_before_connecting():
    term = FakeTerminal(account())
    code, report = probe.run(term, probe.AUTH.valid_until + timedelta(minutes=1), history=False)
    assert code == 2
    assert "expired" in report["refused"]
    assert term.calls == []


def test_failed_initialize_reads_nothing_else():
    term = FakeTerminal(account(), init_ok=False)
    code, report = probe.run(term, BEFORE_EXPIRY, history=False)
    assert code == 3
    assert "initialize failed" in report["refused"]
    assert term.calls == ["initialize", "last_error"]


def test_authorized_demo_account_passes_the_check():
    probe.check_account(account(), DEMO)


def test_masked_login_keeps_only_last_four_digits():
    assert probe.mask_login(123458107) == "*****8107"
    assert "1234" not in probe.mask_login(123458107)


@pytest.mark.parametrize("offsets, expected", [
    ([0.4, -1.2, 3.0], "UTC"),
    ([7200.5, 7199.0, 7201.2], "shifted by +2 h"),
    ([10800.0, 10799.5, 10801.0], "shifted by +3 h"),
    ([0.5, 7200.0, 30.0], "UNKNOWN"),
    ([], "UNKNOWN"),
])
def test_offset_classification(offsets, expected):
    assert probe.classify_offsets(offsets).startswith(expected)


class RatesStub:
    """Minimal stand-in for the terminal's structured array: len() and ["time"]."""

    def __init__(self, times):
        self._times = times

    def __len__(self):
        return len(self._times)

    def __getitem__(self, key):
        assert key == "time"
        return self._times


def test_out_of_range_bar_returned_for_an_empty_range_is_dropped():
    # Round 2: a 2005 range returned one bar from 2026-07-10, which read as "data since 2005".
    later_bar = int(datetime(2026, 7, 10, 4, 2, tzinfo=probe.timezone.utc).timestamp())
    term = SimpleNamespace(copy_rates_range=lambda *a: RatesStub([later_bar]))
    start = datetime(2005, 1, 1, tzinfo=probe.timezone.utc)
    assert probe.times_in_range(term, 1, start, datetime(2005, 2, 1, tzinfo=probe.timezone.utc)) == ([], None)
    inside = int(datetime(2026, 7, 10, 4, 2, tzinfo=probe.timezone.utc).timestamp())
    assert probe.times_in_range(term, 1, datetime(2026, 7, 1, tzinfo=probe.timezone.utc),
                                datetime(2026, 8, 1, tzinfo=probe.timezone.utc)) == ([inside], None)


UTC = probe.timezone.utc


def test_failed_range_call_is_reported_as_an_error_not_as_no_data():
    # Review r1 F3: None from the terminal is an error and must not read as "no bars".
    term = SimpleNamespace(copy_rates_range=lambda *a: None, last_error=lambda: (-10005, "IPC timeout"))
    times, error = probe.times_in_range(term, 1, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC))
    assert times == [] and error == [-10005, "IPC timeout"]


def test_failed_tick_probe_makes_the_month_search_unknown():
    term = SimpleNamespace(COPY_TICKS_ALL=-1, copy_ticks_range=lambda *a: None,
                           copy_ticks_from=lambda *a: None, last_error=lambda: (-10005, "IPC timeout"))
    result = probe.tick_depth(term, datetime(2026, 10, 21, tzinfo=UTC))
    assert result["first_tick"] == "UNKNOWN"
    assert result["month_sample_search"]["first_month_with_ticks"] == "UNKNOWN"


def test_first_tick_day_comes_from_the_first_tick_not_a_mid_month_sample():
    # Review r1 F2: history starting January 20 has no tick on the January 15 sample hour, so a
    # month search says February; the first tick itself must say January 20.
    start = int(datetime(2026, 1, 20, 9, 30, tzinfo=UTC).timestamp())

    def ticks_range(_symbol, frm, to, _flags):
        lo, hi = int(frm.timestamp()), int(to.timestamp())
        return RatesStub([t for t in range(max(lo, start), hi, 600)])

    term = SimpleNamespace(COPY_TICKS_ALL=-1, copy_ticks_from=lambda *a: RatesStub([start]),
                           copy_ticks_range=ticks_range, last_error=lambda: (1, "Success"))
    result = probe.tick_depth(term, datetime(2026, 3, 1, tzinfo=UTC))
    assert result["first_tick_as_if_utc"] == "2026-01-20 09:30:00"
    assert result["ticks_in_day_before_first"] == 0
    assert result["month_sample_search"]["first_month_with_ticks"] == "2026-02"  # why it is only supplementary


class HistoryTerminal:
    """Fake terminal for history_depth: M1 month requests fail before 2026, then return data."""
    TIMEFRAME_M1, TIMEFRAME_M5, TIMEFRAME_H1, TIMEFRAME_D1, COPY_TICKS_ALL = 1, 5, 16385, 16408, -1

    def __init__(self, fail_m1_before=None, fail_day_before=False):
        self.fail_m1_before = fail_m1_before
        self.fail_day_before = fail_day_before
        self.first_tick = int(datetime(2026, 1, 1, 23, 5, tzinfo=UTC).timestamp())

    def terminal_info(self):
        return SimpleNamespace(maxbars=1000)

    def copy_rates_from_pos(self, *_):
        return None

    def copy_rates_range(self, _symbol, _tf, start, end):
        if self.fail_m1_before and start < self.fail_m1_before:
            return None
        lo = max(int(start.timestamp()), int(datetime(2026, 7, 10, tzinfo=UTC).timestamp()))
        return RatesStub(list(range(lo, min(int(end.timestamp()), lo + 600), 60)))

    def copy_ticks_from(self, *_):
        return RatesStub([self.first_tick])

    def copy_ticks_range(self, _symbol, frm, to, _flags):
        if self.fail_day_before and int(to.timestamp()) == self.first_tick:
            return None
        return RatesStub([t for t in range(max(int(frm.timestamp()), self.first_tick), int(to.timestamp()), 600)])

    def last_error(self):
        return (-10005, "IPC timeout")


def test_failed_earlier_month_makes_the_first_m1_month_boundary_unknown():
    # Review r2 F3: an earlier failed month followed by data must not read as a proven start.
    out = probe.history_depth(HistoryTerminal(fail_m1_before=datetime(2006, 1, 1, tzinfo=UTC)),
                              datetime(2026, 8, 1, tzinfo=UTC))
    assert out["m1_first_month_with_data"].startswith("2026-07")
    assert out["m1_first_month_boundary"].startswith("UNKNOWN")
    assert len(out["m1_range_call_errors"]) == 12 and out["m1_range_call_errors"][0]["error"] == [-10005, "IPC timeout"]
    clean = probe.history_depth(HistoryTerminal(), datetime(2026, 8, 1, tzinfo=UTC))
    assert clean["m1_first_month_boundary"] == "no failed request before it"


def test_failed_day_before_check_keeps_its_error_and_makes_the_tick_boundary_unknown():
    term = HistoryTerminal(fail_day_before=True)
    out = probe.tick_depth(term, datetime(2026, 3, 1, tzinfo=UTC))
    assert out["first_tick_as_if_utc"] == "2026-01-01 23:05:00"
    assert out["ticks_in_day_before_first"] == "UNKNOWN"
    assert out["first_tick_boundary"].startswith("UNKNOWN")
    assert out["day_before_call_error"]["error"] == [-10005, "IPC timeout"]
    ok = probe.tick_depth(HistoryTerminal(), datetime(2026, 3, 1, tzinfo=UTC))
    assert ok["ticks_in_day_before_first"] == 0 and ok["first_tick_boundary"] == "no ticks in the day before"


def test_gap_census_counts_every_interval_and_month_boundaries():
    # Review r1 F1: 2-5 minute gaps had no bucket, and a gap across a month boundary was lost.
    july_last = int(datetime(2026, 7, 31, 20, 59, tzinfo=UTC).timestamp())
    august = [july_last + 3 * 3600 + 60 * i for i in range(3)]  # first August bar 3 h after July's last
    counts, notable = probe.gap_census(august, prev_last=july_last)
    assert counts["gaps_15m_to_3h"] == 1  # exactly 3 h is in the 15 min to 3 h bucket
    alone, _ = probe.gap_census(august)
    assert sum(alone.values()) == 0  # without the carried bar the boundary gap would vanish
    t0 = int(datetime(2026, 8, 3, 10, 0, tzinfo=UTC).timestamp())
    times = [t0, t0 + 180, t0 + 180 + 600, t0 + 780 + 4 * 3600, t0 + 780 + 4 * 3600 + 2 * 86400]
    counts, notable = probe.gap_census(times)
    assert counts == {"gaps_2_to_5m": 1, "gaps_5_to_15m": 1, "gaps_15m_to_3h": 0,
                      "gaps_3h_to_24h": 1, "gaps_24h_plus": 1}
    assert [g["gap_minutes"] for g in notable] == [10.0, 240.0]


def test_daily_break_and_week_edges_from_raw_times():
    t0 = int(datetime(2026, 3, 2, 20, 0).timestamp())  # any fixed epoch base
    times = [t0 + 60 * i for i in range(60)]  # 20:00..20:59 bars
    times += [times[-1] + 61 * 60 + 60 * i for i in range(10)]  # one-hour break, then bars
    times += [times[-1] + 49 * 3600]  # weekend gap
    breaks = probe.daily_breaks(times)
    assert len(breaks) == 1 and breaks[0]["gap_minutes"] == 61
    edges = probe.week_edges(times)
    assert len(edges) == 1 and edges[0]["gap_hours"] == 49.0
