"""Implementer unit tests for sochron.research (CORE-008). The locked acceptance and golden tests own the
contract; these pin what they cannot see: the flags a random trade carries, a write that fails after the
file is open, a corrupt exponent in a registry line, the Summary value checks, and a baseline drawn on the
result of a real run_variant (the R1 speed estimate is in docs/evidence/CORE-008.md)."""

import random
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_UP, Decimal, localcontext
from time import perf_counter
from types import MappingProxyType

import pytest

import sochron.backtest
import sochron.research.registry as registry_module
from sochron.backtest import BACKTEST_VERSION, Result, Rollover, SizedLots, Trade
from sochron.core import Bar
from sochron.costs import H001_COSTS, CostBreakdown
from sochron.data.snapshot import H001_CLOSURES, ValidationReport, aggregate
from sochron.research import (
    BudgetExceeded,
    Dataset,
    ResearchError,
    Summary,
    append_record,
    evaluate,
    neighbours,
    percentile,
    random_entry_baseline,
    read_records,
    render_report,
    run_variant,
    summarize,
)
from sochron.research.baseline import _Plan, _round
from sochron.research.inputs import param_pairs, started_record
from sochron.strategy import STRATEGY_VERSION, H001Params
from sochron.timebase import rule_for

RULE = rule_for("Exness-MT5Trial14")
ROLLOVER = Rollover("America/New_York", time(17, 0))
COMMIT = "0123456789abcdef0123456789abcdef01234567"
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _bar(when: datetime, timeframe: int = 1, open_: str = "2000.00", high: str = "2000.50", low: str = "1999.50",
         close: str = "2000.00", spread: int | None = 200) -> Bar:
    return Bar((when - _EPOCH) // timedelta(seconds=1), when, timeframe, Decimal(open_), Decimal(high), Decimal(low),
               Decimal(close), spread, 1, 1)


def _random_walk(count: int, seed: int, start: datetime) -> tuple[Bar, ...]:
    rng = random.Random(seed)
    price = Decimal("2000.00")
    bars = []
    for i in range(count):
        step = Decimal(rng.randint(-60, 60)) / Decimal(100)
        open_, close = price, price + step
        high = max(open_, close) + Decimal(rng.randint(0, 30)) / Decimal(100)
        low = min(open_, close) - Decimal(rng.randint(0, 30)) / Decimal(100)
        bars.append(_bar(start + timedelta(minutes=i), 1, str(open_), str(high), str(low), str(close),
                         200 + rng.randint(0, 80)))
        price = close
    return tuple(bars)


class _ScriptedRandom:
    """randrange always answers the next value of a script (modulo n)."""

    def __init__(self, script: tuple[int, ...]) -> None:
        self.script = list(script)

    def randrange(self, n: int) -> int:
        return self.script.pop(0) % n


def _sizer(equity: Decimal, stop_distance: Decimal) -> SizedLots:
    return SizedLots(Decimal("0.02"), Decimal("25"), None, "fixed")


@pytest.mark.parametrize("bar, planned_exit, flags", [
    (4, 21, frozenset({"price_jump", "unexpected_gap"})),  # bars 4..7: the flags of 5 and 7
    (10, 39, frozenset()),  # bars 10..13 carry none
    (17, None, frozenset({"incomplete"})),  # entry 54 + 6 is past the data: flags up to the last bar, 19
])
def test_a_random_trade_carries_the_flags_of_every_bar_from_t_to_its_exit_bar(monkeypatch, bar, planned_exit, flags):
    start = datetime(2024, 1, 8, 8, 0, tzinfo=UTC)
    m1 = tuple(_bar(start + timedelta(minutes=5 * i)) for i in range(60))  # 20 M15 bars of 3 M1
    marks = {5: frozenset({"price_jump"}), 7: frozenset({"unexpected_gap"}), 19: frozenset({"incomplete"})}
    bars15 = [(_bar(start + timedelta(minutes=15 * u), 15), marks.get(u, frozenset())) for u in range(20)]
    plan = _Plan(m1, bars15, [3 * u for u in range(20)], [i // 3 for i in range(60)], (bar,),
                 {bar: Decimal("3")}, (6,), 1)
    seen = []
    original = sochron.backtest.simulate_trade

    def recording(*args, **kwargs):
        seen.append((kwargs["exit_index"], kwargs["data_flags"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(sochron.backtest, "simulate_trade", recording)
    trades = _round(plan, _ScriptedRandom((0, 0, 0)), _sizer, Decimal("10000"), H001_COSTS, ROLLOVER)
    assert len(trades) == 1 and seen == [(planned_exit, flags)]
    assert trades[0].data_flags == flags


def _record(seq: int = 1):
    dataset = Dataset("SYN-UNIT", "a" * 64, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC), 10)
    params = H001Params("B", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    return started_record(seq=seq, purpose="select", params=params, base_run_id=None, model=H001_COSTS,
                          equity=Decimal("10000"), rule=RULE, rollover=ROLLOVER, dataset=dataset, code_commit=COMMIT,
                          sizer_label="fixed-0.02")


def test_a_write_that_fails_after_the_file_is_open_reaches_the_caller_unwrapped(monkeypatch, tmp_path):
    full = OSError("disk full")

    class _Handle:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def write(self, data):
            raise full

        def flush(self):
            raise AssertionError("flush after a failed write")

    monkeypatch.setattr(registry_module, "open", lambda path, mode: _Handle(), raising=False)
    path = tmp_path / "registry.jsonl"
    with pytest.raises(OSError) as caught:
        append_record(path, _record())
    assert caught.value is full and not isinstance(caught.value, ResearchError)
    assert not path.exists()


@pytest.mark.parametrize("equity", ["1E+9999999999999999999", "1E-9999999999999999999"])
def test_an_exponent_beyond_decimal_in_a_registry_line_is_a_research_error_with_its_line(tmp_path, equity):
    line = _record().line().replace(b'"equity":"10000"', f'"equity":"{equity}"'.encode())
    path = tmp_path / "registry.jsonl"
    path.write_bytes(line)
    with pytest.raises(ResearchError, match=r"registry line 1\b"):
        read_records(path)


def test_a_deeply_nested_line_is_a_research_error_with_its_line(tmp_path):
    # implementation review r1 F2: json.loads raises RecursionError, not ValueError, on deep nesting.
    path = tmp_path / "registry.jsonl"
    content = _record().line() + b"[" * 100_000 + b"]" * 100_000 + b"\n"
    path.write_bytes(content)
    with pytest.raises(ResearchError, match=r"registry line 2\b"):
        read_records(path)
    with pytest.raises(ResearchError):
        append_record(path, _record(seq=3))
    assert path.read_bytes() == content


def _summary(**changes):
    values = dict(trades=1, expectancy_r=Decimal("0.5"), max_drawdown_r=Decimal("0"), net_money=Decimal("12.5"),
                  long_trades=1, long_expectancy_r=Decimal("0.5"), short_trades=0, short_expectancy_r=None,
                  top5_removed_expectancy_r=None, expectancy_by_year=((2024, Decimal("0.5")),), ambiguous_trades=0,
                  flagged_trades=0, gap_fills=0, end_of_data_trades=0)
    values.update(changes)
    return Summary(**values)


@pytest.mark.parametrize("changes", [
    {"trades": -1}, {"gap_fills": -1}, {"expectancy_r": Decimal("NaN")}, {"net_money": Decimal("Infinity")},
    {"expectancy_by_year": ((2024, Decimal("0.5")), (2023, Decimal("0.5")))},
    {"expectancy_by_year": ((2024, Decimal("0.5")), (2024, Decimal("0.5")))},
    {"expectancy_by_year": ((2024,),)},
], ids=["negative trades", "negative gap fills", "NaN", "Infinity", "years out of order", "a year twice", "no value"])
def test_summary_values_outside_the_domain_are_research_errors(changes):
    _summary()
    with pytest.raises(ResearchError):
        _summary(**changes)


def _trade(r: str, net: str) -> Trade:
    zero = Decimal("0")
    costs = CostBreakdown(spread=zero, commission=zero, slippage=zero, swap=zero, total=zero, stress_factor=Decimal("1"))
    entry = (datetime(2024, 1, 10, 14, tzinfo=UTC) - _EPOCH) // timedelta(seconds=1)
    return Trade(side="long", entry_time_raw=entry, entry_bid=Decimal("2000"), entry_spread_points=200,
                 exit_time_raw=entry + 60, exit_bid=Decimal("2000"), exit_spread_points=200, lots=Decimal("0.02"),
                 stop_distance=Decimal("10"), stop_price=Decimal("1990"), exit_reason="signal", ambiguous=False,
                 nights=0, triple_nights=0, costs=costs, gross_money=Decimal(net), net_money=Decimal(net),
                 risk_money=Decimal("25"), actual_risk=None, r=Decimal(r), data_flags=frozenset())


@pytest.mark.parametrize("r, net", [("9E+999999", "1"), ("1", "9E+999999"), ("-9E+999999", "1")],
                         ids=["R sum up", "net money sum", "R sum down"])
def test_sums_beyond_the_decimal_range_are_research_errors_not_decimal_overflow(r, net):
    result = Result(trades=(_trade(r, net), _trade(r, net)), skips=(), equity=((946684800, Decimal("10000")),),
                    backtest_version=BACKTEST_VERSION, strategy_version=STRATEGY_VERSION)
    with pytest.raises(ResearchError, match="too large"):
        summarize(result, RULE)


def test_percentile_does_not_depend_on_the_caller_context():
    # tests review r2 F1: ceil(q x n) at precision 3 would round 1000.5 up to 1010 and 1001 up to 1010.
    values = [Decimal(i) for i in range(2001)]
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_UP
        context.clear_flags()
        before = (context.prec, context.rounding, dict(context.flags), dict(context.traps))
        assert percentile(values, Decimal("0.5")) == Decimal(1000)
        assert percentile(values[:1001], Decimal("1")) == Decimal(1000)
        assert (context.prec, context.rounding, dict(context.flags), dict(context.traps)) == before


def test_the_setup_lock_compares_equity_as_its_record_string(tmp_path):
    # tests review r2 F2: Decimal("1E+4") equals 10000 but its record string differs, so it is another setup.
    start = datetime(2024, 3, 4, tzinfo=UTC)
    m1 = _random_walk(300, 5, start)
    report = ValidationReport(defects=(), days=MappingProxyType({}), m1_bars=len(m1), calendar=H001_CLOSURES)
    m15 = aggregate(m1, 15, RULE, report)
    dataset = Dataset("SYN-LOCK", "c" * 64, start, m1[-1].time_utc + timedelta(minutes=1), len(m1))
    path = tmp_path / "registry.jsonl"

    def select(k: str, equity: str) -> None:
        params = H001Params("B", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal(k))
        run_variant(m1, m15, params, H001_COSTS, _sizer, Decimal(equity), RULE, ROLLOVER, purpose="select",
                    dataset=dataset, code_commit=COMMIT, sizer_label="fixed-0.02", registry=path)

    select("2.0", "10000")
    before = path.read_bytes()
    with pytest.raises(BudgetExceeded):
        select("2.2", "1E+4")
    assert path.read_bytes() == before
    select("2.2", "10000")
    assert len(read_records(path)) == 4


def test_decimal_text_does_not_depend_on_the_callers_capitals(tmp_path):
    # implementation review r1 F1: str(Decimal) reads `capitals` from the current context ("1E+4" vs "1e+4").
    record = replace(_record(), equity=Decimal("1E+4"))
    summary = _summary(expectancy_r=Decimal("1E-7"), long_expectancy_r=Decimal("1E-7"),
                       expectancy_by_year=((2024, Decimal("1E-7")),))
    ok = replace(record, seq=2, status="ok", started_seq=1, summary=summary)
    params = H001Params("B", 16, 64, 20, Decimal("0.50"), 96, 48, Decimal("2.0"))
    default = (record.line(), record.run_id, ok.line(), [n.value for n in neighbours(params)],
               param_pairs(replace(params, k=Decimal("2.0E0"))), evaluate(ok, None, None, None, ()).checks)
    path = tmp_path / "registry.jsonl"
    with localcontext() as context:
        context.capitals = 0
        lowered = (record.line(), record.run_id, ok.line(), [n.value for n in neighbours(params)],
                   param_pairs(replace(params, k=Decimal("2.0E0"))), evaluate(ok, None, None, None, ()).checks)
        append_record(path, record)
        append_record(path, ok)
        lowered_report = render_report(read_records(path), {})
    assert lowered == default
    assert b'"equity":"1E+4"' in path.read_bytes() and read_records(path) == (record, ok)
    assert render_report(read_records(path), {}) == lowered_report
    assert "1E-7" in default[-1][1].value


def test_evaluate_needs_a_sequence_for_robustness():
    with pytest.raises(TypeError):
        evaluate(_record(), None, None, None, None)


def test_a_suffix_in_upper_case_is_not_a_registry(tmp_path):
    with pytest.raises(ResearchError):
        append_record(tmp_path / "registry.JSONL", _record())
    assert not (tmp_path / "registry.JSONL").exists()


def test_a_baseline_on_a_variant_from_run_variant(tmp_path):
    start = datetime(2024, 3, 4, tzinfo=UTC)  # a Monday, before the holdout cutoff
    m1 = _random_walk(6_000, 11, start)
    report = ValidationReport(defects=(), days=MappingProxyType({}), m1_bars=len(m1), calendar=H001_CLOSURES)
    m15 = aggregate(m1, 15, RULE, report)
    end = m1[-1].time_utc + timedelta(minutes=1)
    dataset = Dataset("SYN-WALK", "b" * 64, start, end, len(m1))
    params = H001Params("B", 8, 32, 10, Decimal("0.50"), 48, 24, Decimal("3.0"))
    path = tmp_path / "registry.jsonl"
    began = perf_counter()
    base, variant = run_variant(m1, m15, params, H001_COSTS, _sizer, Decimal("10000"), RULE, ROLLOVER,
                                purpose="select", dataset=dataset, code_commit=COMMIT, sizer_label="fixed-0.02",
                                registry=path)
    assert len(variant.trades) >= 3, "fixture: the walk gives the variant trades"
    result = random_entry_baseline(m1, m15, params, H001_COSTS, _sizer, Decimal("10000"), RULE, ROLLOVER, variant,
                                   base_run_id=base.run_id, dataset=dataset, code_commit=COMMIT,
                                   sizer_label="fixed-0.02", registry=path)
    elapsed = perf_counter() - began
    records = read_records(path)
    assert [item.status for item in records] == ["started", "ok", "started", "ok"]
    assert records[-1] == result.record and records[-1].params == param_pairs(params)
    assert len(result.expectancies_r) == 1000 and result.summary.trades_per_run == len(variant.trades)
    assert result.summary.p05_r <= result.summary.p50_r <= result.summary.p95_r
    assert elapsed < 60, f"the run and its baseline took {elapsed:.1f} s"
