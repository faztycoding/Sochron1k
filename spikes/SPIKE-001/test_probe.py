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
    assert probe.times_in_range(term, 1, start, datetime(2005, 2, 1, tzinfo=probe.timezone.utc)) == []
    inside = int(datetime(2026, 7, 10, 4, 2, tzinfo=probe.timezone.utc).timestamp())
    assert probe.times_in_range(term, 1, datetime(2026, 7, 1, tzinfo=probe.timezone.utc),
                                datetime(2026, 8, 1, tzinfo=probe.timezone.utc)) == [inside]


def test_daily_break_and_week_edges_from_raw_times():
    t0 = int(datetime(2026, 3, 2, 20, 0).timestamp())  # any fixed epoch base
    times = [t0 + 60 * i for i in range(60)]  # 20:00..20:59 bars
    times += [times[-1] + 61 * 60 + 60 * i for i in range(10)]  # one-hour break, then bars
    times += [times[-1] + 49 * 3600]  # weekend gap
    breaks = probe.daily_breaks(times)
    assert len(breaks) == 1 and breaks[0]["gap_minutes"] == 61
    edges = probe.week_edges(times)
    assert len(edges) == 1 and edges[0]["gap_hours"] == 49.0
