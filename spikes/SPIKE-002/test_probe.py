"""SPIKE-002 unit tests (AC-01, AC-04 unit part, AC-05 key list, AC-06 call surface).

A scripted terminal records every call the probe makes, so each refusal proves that nothing beyond
the checks was read. Trade modes are numeric (0 demo, 1 contest, 2 real) as the contract asks.
No terminal and no MetaTrader5 package are needed.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent


def _load_probe(module_name):
    spec = importlib.util.spec_from_file_location(module_name, HERE / "probe.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


probe = _load_probe("spike002_probe")

UTC = timezone.utc
DEMO, CONTEST, REAL_MODE = 0, 1, 2
SERVER = "Exness-MT5Trial14"
SUFFIX = "8107"
WEDNESDAY = datetime(2026, 10, 28, 3, 0, tzinfo=UTC)
SATURDAY = datetime(2026, 10, 31, 3, 0, tzinfo=UTC)
VALID_UNTIL = "2026-11-15T23:59:00+07:00"
CLOCK_SYNC = "Last Successful Sync Time: 28/10/2026 09:58:00\nSource: time.windows.com"
FIRST_M1 = datetime(2014, 1, 14, 0, 0, tzinfo=UTC)
FIRST_TICK = datetime(2026, 1, 1, 23, 5, tzinfo=UTC)
LATE_BAR = datetime(2026, 7, 10, 4, 2, tzinfo=UTC)  # what an empty early range returned in SPIKE-001
BID, ASK = 2650.125, 2650.305


def test_calendar_assumptions():
    assert WEDNESDAY.weekday() == 2 and SATURDAY.weekday() == 5


class Clock:
    def __init__(self, start: datetime):
        self.t = start

    def now(self) -> datetime:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += timedelta(seconds=seconds)


class Rates:
    """Stands in for the structured arrays the terminal returns: len() and ["time"]."""

    def __init__(self, times):
        self._times = list(times)

    def __len__(self):
        return len(self._times)

    def __getitem__(self, key):
        assert key == "time"
        return self._times


def account(**overrides):
    base = dict(login=123458107, server=SERVER, trade_mode=DEMO, trade_allowed=False,
                company="Exness Technologies Ltd", currency="USD", leverage=200)
    base.update(overrides)
    return SimpleNamespace(**base)


class ScriptedTerminal:
    ACCOUNT_TRADE_MODE_DEMO = DEMO
    TIMEFRAME_M1 = 1
    COPY_TICKS_ALL = -1

    def __init__(self, acct=None, *, clock=None, init_ok=True, shift_s=0, jitter_ms=(0, 300, -400, 150, -100),
                 stale=False, maxbars=probe.UNLIMITED_MAXBARS, fail_m1_before=None, tick_missing=False,
                 first_tick=FIRST_TICK, terminal_allowed=False, portable=False, first_m1=FIRST_M1,
                 empty_reply="late"):
        self.acct = account() if acct is None else acct
        self.clock = clock or Clock(WEDNESDAY)
        self.init_ok = init_ok
        self.shift_ms = shift_s * 1000
        self.jitter_ms = list(jitter_ms)
        self.stale = stale
        self.maxbars = maxbars
        self.fail_m1_before = fail_m1_before
        self.tick_missing = tick_missing
        self.first_tick = first_tick
        self.terminal_allowed = terminal_allowed
        self.portable = portable
        self.first_m1 = first_m1
        self.empty_reply = empty_reply
        self.calls: list[str] = []
        self.range_calls: list[tuple[datetime, datetime]] = []
        self._tick_index = 0

    def initialize(self):
        self.calls.append("initialize")
        return self.init_ok

    def last_error(self):
        self.calls.append("last_error")
        return (-10003, "scripted")

    def account_info(self):
        self.calls.append("account_info")
        return self.acct

    def shutdown(self):
        self.calls.append("shutdown")

    def terminal_info(self):
        self.calls.append("terminal_info")
        path = r"C:\Program Files\MetaTrader 5"
        data = path if self.portable else r"C:\Users\owner\AppData\Roaming\MetaQuotes\Terminal\ABC123"
        return SimpleNamespace(build=6274, maxbars=self.maxbars, path=path, data_path=data,
                               trade_allowed=self.terminal_allowed)

    def symbol_info(self, symbol):
        self.calls.append("symbol_info")
        assert symbol == "XAUUSDm"
        return SimpleNamespace(digits=3, point=0.001, trade_contract_size=100.0, volume_min=0.01,
                               volume_step=0.01, volume_max=200.0, trade_stops_level=0, filling_mode=2,
                               swap_long=-40.5, swap_short=20.25, swap_rollover3days=3, spread_float=True,
                               bid=BID, ask=ASK, description="Gold vs US Dollar")

    def symbol_info_tick(self, symbol):
        self.calls.append("symbol_info_tick")
        assert symbol == "XAUUSDm"
        i = self._tick_index
        self._tick_index += 1
        if self.tick_missing and i == 2:
            return None
        base_ms = (WEDNESDAY - probe.EPOCH) // timedelta(milliseconds=1) if self.stale \
            else (self.clock.now() - probe.EPOCH) // timedelta(milliseconds=1)
        jitter = 0 if self.stale else self.jitter_ms[i % len(self.jitter_ms)]
        msc = base_ms + self.shift_ms + jitter
        return SimpleNamespace(time=msc // 1000, time_msc=msc, bid=BID, ask=ASK)

    def copy_rates_range(self, symbol, timeframe, start, end):
        self.calls.append("copy_rates_range")
        assert symbol == "XAUUSDm" and timeframe == self.TIMEFRAME_M1
        self.range_calls.append((start, end))
        if self.fail_m1_before is not None and start < self.fail_m1_before:
            return None
        lo, hi = int(start.timestamp()), int(end.timestamp())
        first = int(self.first_m1.timestamp())
        # date_to treated as inclusive (MQL5 CopyRates semantics), so a bar at the cutoff comes back.
        inside = [t for t in range(max(lo, first), hi + 1, 60)][:5]
        if inside:
            return Rates(inside)
        # An empty range: SPIKE-001 saw the terminal return its earliest bar; "empty" returns nothing.
        return Rates([]) if self.empty_reply == "empty" else Rates([max(first, int(LATE_BAR.timestamp()))])

    def copy_ticks_from(self, symbol, start, count, flags):
        self.calls.append("copy_ticks_from")
        assert symbol == "XAUUSDm" and count == 1 and flags == self.COPY_TICKS_ALL
        assert start == datetime(2005, 1, 1, tzinfo=UTC)
        if self.first_tick is None:
            return None
        return Rates([int(self.first_tick.timestamp())])

    __spec__ = None  # read by the import system when this object stands in for MetaTrader5

    def __getattr__(self, name):  # any terminal name outside this class is a failure
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"probe used {name}")


def auth(valid_until=VALID_UNTIL, server=SERVER, suffix=SUFFIX):
    return probe.Authorization(server, suffix, datetime.fromisoformat(valid_until))


def run_ok(term):
    clock = term.clock
    return probe.run(term, auth(), CLOCK_SYNC, clock.now, clock.sleep)


# ---- AC-01: refusals -----------------------------------------------------------------------
@pytest.mark.parametrize("acct, reason", [
    (account(server="Exness-MT5Real1"), "not the authorized server"),
    (account(login=123450001), "not the authorized account"),
    (account(login=810712345), "not the authorized account"),  # the suffix digits, but not at the end
    (account(trade_mode=CONTEST), "is not Demo"),
    (account(trade_mode=REAL_MODE), "is not Demo"),
    (account(trade_allowed=True), "investor password"),
    (account(trade_allowed=None), "investor password"),
])
def test_ac01_wrong_account_stops_before_any_other_read(acct, reason):
    term = ScriptedTerminal(acct)
    code, report, message = run_ok(term)
    assert code == 2 and report is None
    assert reason in message
    assert term.calls == ["initialize", "account_info", "shutdown"]
    login = str(acct.login)
    assert login not in message  # review r1 F4: the owner pastes this line back
    if reason == "not the authorized account":
        assert "****" + login[-4:] in message


def test_ac01_account_flag_decides_not_the_terminal_flag():
    # AutoTrading off makes terminal_info().trade_allowed false even with the main password.
    term = ScriptedTerminal(account(trade_allowed=True), terminal_allowed=False)
    code, _, message = run_ok(term)
    assert code == 2 and "account_info().trade_allowed" in message
    assert "terminal_info" not in term.calls


def test_ac01_expired_authorization_stops_before_connecting():
    term = ScriptedTerminal()
    code, report, message = probe.run(term, auth(valid_until="2026-10-28T09:59:00+07:00"), CLOCK_SYNC,
                                      term.clock.now, term.clock.sleep)
    assert code == 2 and report is None and "expired" in message
    assert term.calls == []


def test_ac01_initialize_failure_is_exit_3():
    term = ScriptedTerminal(init_ok=False)
    code, report, message = run_ok(term)
    assert code == 3 and report is None and "initialize failed" in message
    assert term.calls == ["initialize", "last_error"]


def test_ac01_not_logged_in_is_exit_3():
    term = ScriptedTerminal()
    term.acct = None
    code, report, message = run_ok(term)
    assert code == 3 and "not logged in" in message
    assert term.calls == ["initialize", "account_info", "shutdown"]


GOOD_ARGS = ["--server", SERVER, "--login-suffix", SUFFIX, "--valid-until", VALID_UNTIL,
             "--clock-sync", CLOCK_SYNC]


def _without(flag):
    i = GOOD_ARGS.index(flag)
    return GOOD_ARGS[:i] + GOOD_ARGS[i + 2:]


def _with(flag, value):
    args = list(GOOD_ARGS)
    args[args.index(flag) + 1] = value
    return args


class RecordingFinder:
    """Makes `import MetaTrader5` succeed with an empty stand-in module, as on the VPS, and counts tries.

    Without it the project environment has no MetaTrader5, so an early import fails and leaves no
    trace in sys.modules (review r1 F5)."""

    def __init__(self):
        self.attempts = 0

    def find_spec(self, name, path=None, target=None):
        if name != "MetaTrader5":
            return None
        self.attempts += 1
        return importlib.util.spec_from_loader(name, loader=self)

    def create_module(self, spec):
        return types.ModuleType(spec.name)

    def exec_module(self, module):
        return None


@pytest.fixture
def mt5_finder(monkeypatch):
    finder = RecordingFinder()
    monkeypatch.delitem(sys.modules, "MetaTrader5", raising=False)
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    yield finder
    sys.modules.pop("MetaTrader5", None)


def test_ac01_recording_finder_sees_an_import(mt5_finder):
    importlib.import_module("MetaTrader5")
    assert mt5_finder.attempts == 1


BAD_ARGVS = [
    [],
    _without("--server"),
    _without("--login-suffix"),
    _without("--valid-until"),
    _without("--clock-sync"),
    _with("--login-suffix", "107"),
    _with("--login-suffix", "81O7"),
    _with("--login-suffix", "48107"),
    _with("--valid-until", "2026-11-15T23:59:00"),  # no UTC offset
    _with("--valid-until", "next week"),
    _with("--server", "  "),
    _with("--clock-sync", " "),
    _with("--valid-until", "2026-10-28T09:59:00+07:00"),  # expired at the Wednesday clock
]


@pytest.mark.parametrize("argv", BAD_ARGVS)
def test_ac01_bad_or_missing_arguments_exit_2_without_importing_metatrader5(argv, mt5_finder, capsys):
    clock = Clock(WEDNESDAY)
    assert probe.main(argv, clock.now, clock.sleep) == 2
    assert mt5_finder.attempts == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("REFUSED (exit 2): ")


def test_ac01_loading_the_probe_and_refusing_never_imports_metatrader5(mt5_finder, capsys):
    # A fresh load under the finder also catches an import at module level (review r1 F5).
    fresh = _load_probe("spike002_probe_fresh")
    clock = Clock(WEDNESDAY)
    for argv in BAD_ARGVS:
        assert fresh.main(argv, clock.now, clock.sleep) == 2
    assert mt5_finder.attempts == 0
    sys.modules.pop("spike002_probe_fresh", None)


@pytest.mark.parametrize("argv", [
    GOOD_ARGS + ["123458107"],  # a stray full login
    GOOD_ARGS + ["--account", "123458107"],  # an unknown flag carrying it
    GOOD_ARGS + ["--password", "typed-by-mistake"],
    GOOD_ARGS + ["--help=123458107"],  # review r2 F8: argparse quoted these too
    GOOD_ARGS + ["--he=123458107"],
    GOOD_ARGS + ["--=123458107"],
    ["--help"],  # no help screen: every unexpected argument is a refusal
])
def test_ac01_refusal_never_repeats_what_was_typed(argv, monkeypatch, capsys):
    # Review r1 F3: argparse quotes unknown tokens, and the owner pastes the refusal line back.
    monkeypatch.delitem(sys.modules, "MetaTrader5", raising=False)
    clock = Clock(WEDNESDAY)
    assert probe.main(argv, clock.now, clock.sleep) == 2
    err = capsys.readouterr().err
    assert err.startswith("REFUSED (exit 2): arguments:")
    assert "123458107" not in err and "typed-by-mistake" not in err


def test_ac01_abbreviated_flag_with_a_full_login_is_refused_without_echo(monkeypatch, capsys):
    monkeypatch.delitem(sys.modules, "MetaTrader5", raising=False)
    clock = Clock(WEDNESDAY)
    argv = _with("--login-suffix", "123458107")
    argv[argv.index("--login-suffix")] = "--login"  # argparse accepts the abbreviation
    assert probe.main(argv, clock.now, clock.sleep) == 2
    err = capsys.readouterr().err
    assert "exactly 4 digits" in err and "123458107" not in err


def test_ac01_no_authorization_value_is_built_in():
    source = (HERE / "probe.py").read_text(encoding="utf-8")
    assert "Exness" not in source and SUFFIX not in source
    assert not hasattr(probe, "AUTH")


def test_ac01_main_refuses_through_stderr_for_a_wrong_account(monkeypatch, capsys):
    term = ScriptedTerminal(account(trade_allowed=True))
    monkeypatch.setitem(sys.modules, "MetaTrader5", term)
    assert probe.main(GOOD_ARGS, term.clock.now, term.clock.sleep) == 2
    out = capsys.readouterr()
    assert out.out == "" and "investor password" in out.err


# ---- AC-04 (unit part): freshness and offset judged separately ------------------------------
def test_ac04_fresh_ticks_shifted_two_hours_are_open_and_shifted():
    term = ScriptedTerminal(shift_s=7200)
    code, report, _ = run_ok(term)
    t = report["time"]
    assert code == 0 and t["market_open"] is True and t["offset_class_s"] == 7200
    assert t["offset_samples_s"] == [7200, 7200, 7200, 7200, 7200]  # jitter of up to 0.4 s rounds away


def test_ac04_stale_ticks_are_closed_and_unknown():
    term = ScriptedTerminal(stale=True)
    _, report, _ = run_ok(term)
    assert report["time"]["market_open"] is False and report["time"]["offset_class_s"] is None


def test_ac04_fresh_ticks_on_saturday_are_closed():
    term = ScriptedTerminal(clock=Clock(SATURDAY))
    _, report, _ = run_ok(term)
    assert report["time"]["market_open"] is False and report["time"]["offset_class_s"] is None


def test_ac04_offset_zero_within_tolerance():
    term = ScriptedTerminal(jitter_ms=(-3800, 870, 0, -1200, 400))  # SPIKE-001's observed spread
    _, report, _ = run_ok(term)
    assert report["time"]["offset_class_s"] == 0
    assert report["time"]["offset_samples_s"] == [-4, 1, 0, -1, 0]


def test_ac04_samples_are_five_twenty_seconds_apart():
    term = ScriptedTerminal()
    run_ok(term)
    assert term.calls.count("symbol_info_tick") == 5
    assert term.clock.now() == WEDNESDAY + timedelta(seconds=80)


@pytest.mark.parametrize("offsets, is_open, expected", [
    ([0, 120_000, -120_000, 5_000, 0], True, 0),
    ([0, 120_001, 0, 0, 0], True, None),  # one sample just outside the tolerance
    ([7_199_000, 7_201_000, 7_200_000, 7_200_500, 7_199_500], True, 7200),
    ([-3_600_400, -3_599_900, -3_600_000, -3_600_100, -3_599_800], True, -3600),
    ([1_790_000, 1_810_000, 1_800_000, 1_800_000, 1_800_000], True, None),  # half an hour: no class
    ([0, 0, 0, 0, None], True, None),
    ([0, 0, 0, 0, 0], False, None),
])
def test_ac04_offset_class_rule(offsets, is_open, expected):
    assert probe.offset_class_s(offsets, is_open) == expected


def test_ac04_a_missing_tick_makes_the_class_unknown():
    term = ScriptedTerminal(tick_missing=True)
    _, report, _ = run_ok(term)
    assert report["time"]["offset_samples_s"][2] is None
    assert report["time"]["offset_class_s"] is None


def test_ac04_advances_counted_between_samples():
    s = [probe.Sample(0, v) for v in (1, 2, 2, 3, 4)]
    assert probe.market_open(s, WEDNESDAY) is True  # three advances
    s = [probe.Sample(0, v) for v in (1, 2, 2, 2, 3)]
    assert probe.market_open(s, WEDNESDAY) is False  # two advances


# ---- AC-05: exactly the contract's fields, nothing after the cutoff but first_tick_utc --------
EXPECTED_KEYS = {
    "identity": {"company", "server", "trade_mode", "currency", "leverage", "login_masked",
                 "trade_allowed", "terminal_build", "terminal_path_kind"},
    "spec": {"digits", "point", "trade_contract_size", "volume_min", "volume_step", "volume_max",
             "trade_stops_level", "filling_mode", "swap_long", "swap_short", "swap_rollover3days",
             "spread_float"},
    "time": {"market_open", "offset_samples_s", "offset_class_s", "clock_sync"},
    "history": {"maxbars", "first_m1_utc", "first_tick_utc"},
    "packages": {"MetaTrader5", "numpy", "tzdata", "python"},
    "run": {"started_utc"},
}


def test_ac05_report_has_exactly_the_contract_fields():
    term = ScriptedTerminal()
    code, report, _ = run_ok(term)
    assert code == 0
    assert set(report) == set(EXPECTED_KEYS)
    for group, keys in EXPECTED_KEYS.items():
        assert set(report[group]) == keys, group


def test_ac05_values():
    term = ScriptedTerminal()
    _, report, _ = run_ok(term)
    ident = report["identity"]
    assert ident["login_masked"] == "****8107" and ident["trade_allowed"] is False
    assert ident["trade_mode"] == DEMO and ident["terminal_build"] == 6274
    assert ident["terminal_path_kind"] == "installed"
    assert report["spec"]["digits"] == 3 and report["spec"]["swap_rollover3days"] == 3
    assert report["history"] == {"maxbars": 100_000_000, "first_m1_utc": "2014-01-14",
                                 "first_tick_utc": "2026-01-01"}
    assert report["time"]["clock_sync"] == CLOCK_SYNC
    assert report["run"]["started_utc"] == "2026-10-28T03:00Z"


def test_ac05_no_tick_time_price_or_full_login_in_the_output():
    term = ScriptedTerminal()
    _, report, _ = run_ok(term)
    text = json.dumps(report, ensure_ascii=False)
    first_tick_s = str(int(FIRST_TICK.timestamp()))
    for leaked in (str(BID), str(ASK), "123458107", first_tick_s, "23:05", "Program Files",
                   "AppData", str(int(LATE_BAR.timestamp()))):
        assert leaked not in text, leaked
    tick_msc = (WEDNESDAY - probe.EPOCH) // timedelta(milliseconds=1)
    assert str(tick_msc)[:9] not in text  # no tick time_msc, even partly


def test_ac05_m1_search_never_reaches_the_cutoff():
    term = ScriptedTerminal()
    run_ok(term)
    assert term.range_calls[0][0] == datetime(2005, 1, 1, tzinfo=UTC)
    assert all(end <= probe.CUTOFF_UTC for _, end in term.range_calls)
    assert term.range_calls[-1][0] == datetime(2014, 1, 1, tzinfo=UTC)  # stops at the first data


@pytest.mark.parametrize("first_m1, empty_reply", [
    (LATE_BAR, "late"),  # history not loaded back before 2025 (SPIKE-001 runs 2-3)
    (LATE_BAR, "empty"),
    (datetime(2025, 1, 1, 0, 0, tzinfo=UTC), "late"),  # a bar exactly at the cutoff
    (datetime(2025, 1, 2, 0, 0, tzinfo=UTC), "empty"),
])
def test_ac05_no_m1_before_the_cutoff_reads_null_and_never_asks_past_it(first_m1, empty_reply):
    # Review r1 F1: the 2014 history stopped the search long before 2025, so nothing guarded the cutoff.
    term = ScriptedTerminal(first_m1=first_m1, empty_reply=empty_reply)
    assert probe.first_m1_utc(term, probe.UNLIMITED_MAXBARS) is None
    assert len(term.range_calls) == 240  # 2005-01 .. 2024-12, one request per month
    assert all(start < probe.CUTOFF_UTC for start, _ in term.range_calls)
    assert all(end <= probe.CUTOFF_UTC for _, end in term.range_calls)
    assert term.range_calls[-1] == (datetime(2024, 12, 1, tzinfo=UTC), probe.CUTOFF_UTC)


def test_ac05_out_of_range_bar_is_not_taken_as_data():
    term = ScriptedTerminal()
    assert probe.first_m1_utc(term, probe.UNLIMITED_MAXBARS) == "2014-01-14"


def test_ac05_not_unlimited_maxbars_makes_first_m1_unknown_without_searching():
    term = ScriptedTerminal(maxbars=100_000)
    _, report, _ = run_ok(term)
    assert report["history"]["first_m1_utc"] == "UNKNOWN"
    assert "copy_rates_range" not in term.calls


def test_ac05_failed_month_before_data_makes_first_m1_unknown():
    term = ScriptedTerminal(fail_m1_before=datetime(2006, 1, 1, tzinfo=UTC))
    assert probe.first_m1_utc(term, probe.UNLIMITED_MAXBARS) == "UNKNOWN"


def test_ac05_failed_or_empty_tick_search():
    assert probe.first_tick_utc(ScriptedTerminal(first_tick=None)) == "UNKNOWN"
    empty = SimpleNamespace(COPY_TICKS_ALL=-1, copy_ticks_from=lambda *a: Rates([]))
    assert probe.first_tick_utc(empty) is None


def test_ac05_portable_terminal_kind():
    _, report, _ = run_ok(ScriptedTerminal(portable=True))
    assert report["identity"]["terminal_path_kind"] == "portable"


def test_ac05_missing_package_reads_not_installed(monkeypatch):
    real = probe.metadata.version

    def version(name):
        if name == "MetaTrader5":
            raise probe.metadata.PackageNotFoundError(name)
        return real(name)

    monkeypatch.setattr(probe.metadata, "version", version)
    out = probe.package_versions()
    assert out["MetaTrader5"] == "not installed"
    assert set(out) == {"MetaTrader5", "numpy", "tzdata", "python"}


def test_ac05_main_prints_the_report_as_json(monkeypatch, capsys):
    term = ScriptedTerminal()
    monkeypatch.setitem(sys.modules, "MetaTrader5", term)
    assert probe.main(GOOD_ARGS, term.clock.now, term.clock.sleep) == 0
    out = capsys.readouterr()
    assert out.err == ""
    assert set(json.loads(out.out)) == set(EXPECTED_KEYS)


# ---- AC-06: the probe's terminal surface is the contract's list ------------------------------
def _terminal_attributes_used():
    tree = ast.parse((HERE / "probe.py").read_text(encoding="utf-8"))
    return {node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "mt5"}


def test_ac06_probe_source_uses_only_allowed_terminal_names():
    constants = {"TIMEFRAME_M1", "COPY_TICKS_ALL"}
    assert _terminal_attributes_used() <= probe.ALLOWED_CALLS | constants
    assert probe.ALLOWED_CALLS == {
        "initialize", "shutdown", "last_error", "version", "terminal_info", "account_info",
        "symbol_info", "symbol_info_tick", "copy_rates_range", "copy_rates_from_pos",
        "copy_ticks_range", "copy_ticks_from"}


def test_ac06_a_full_run_calls_only_allowed_functions():
    term = ScriptedTerminal()
    code, _, _ = run_ok(term)
    assert code == 0 and set(term.calls) <= probe.ALLOWED_CALLS
    assert term.calls[0] == "initialize" and term.calls[-1] == "shutdown"
