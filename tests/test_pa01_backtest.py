from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import sochron_worker.pa01_backtest as backtest
from pydantic import ValidationError
from sochron_worker.pa01 import (
    H1_SECONDS,
    M5_SECONDS,
    PARAMETER_HASH,
    PARAMETER_VERSION,
    STRATEGY_VERSION,
    ClosedBar,
)
from sochron_worker.pa01_backtest import (
    INPUT_PROTOCOL,
    PA01_CODE_HASH,
    PRODUCER_REVISION,
    PA01BacktestInput,
    PA01BacktestInvalid,
    ReplayPolicy,
    ReplayTick,
    backtest_dict,
    build_bundle,
    load_backtest_input,
    write_bundle,
)
from sochron_worker.pa01_backtest_cli import main
from sochron_worker.research_evaluation import (
    BootstrapPlan,
    ClosedTrade,
    CostAssumptions,
    EvaluationWindow,
    evaluate_bundle,
)
from sochron_worker.sync_journal import canonical

D = Decimal
BASE = datetime(2026, 1, 1, tzinfo=UTC)
FEED = "fixture-feed"
SYMBOL = "XAUUSD.fixture"
TICK = D("0.01")


def bar(
    timeframe: str,
    index: int,
    *,
    close: Decimal,
    high: Decimal | None = None,
    low: Decimal | None = None,
    opened_at: datetime | None = None,
) -> ClosedBar:
    seconds = M5_SECONDS if timeframe == "M5" else H1_SECONDS
    origin = BASE if timeframe == "M5" else BASE - timedelta(days=2)
    opened = opened_at or origin + timedelta(seconds=index * seconds)
    high = high if high is not None else close + D("0.40")
    low = low if low is not None else close - D("0.40")
    return ClosedBar(
        evidence_id=f"{timeframe.lower()}-{index}",
        feed_id=FEED,
        source_revision="fixture-v1",
        symbol=SYMBOL,
        timeframe=timeframe,
        time_server_s=int(opened.timestamp()),
        broker_utc_offset_seconds=0,
        open_time_utc=opened,
        available_at_utc=opened + timedelta(seconds=seconds + 1),
        open=close,
        high=high,
        low=low,
        close=close,
        tick_size=TICK,
        digits=2,
    )


def warmup_m5() -> list[ClosedBar]:
    bars = [bar("M5", index, close=D("100") + D("0.05") * index) for index in range(59)]
    previous = D("100") + D("0.05") * 58
    bars[58] = bar(
        "M5",
        58,
        close=previous,
        high=previous + D("0.40"),
        low=previous - D("0.60"),
    )
    return bars


def h1_bars() -> tuple[ClosedBar, ...]:
    centers = [
        100,
        101,
        105,
        102,
        98,
        101,
        107,
        103,
        100,
        103,
        109,
        105,
        102,
        105,
        111,
        107,
        104,
        106,
        108,
        109,
    ]
    result = [
        bar(
            "H1",
            index,
            close=D(value),
            high=D(value) + D("0.80"),
            low=D(value) - D("0.80"),
        )
        for index, value in enumerate(centers)
    ]
    for index in range(20, 55):
        value = D("110") + D(index - 20) / D("10")
        result.append(
            bar(
                "H1",
                index,
                close=value,
                high=value + D("0.80"),
                low=value - D("0.80"),
            )
        )
    return tuple(result)


def replay_ticks_and_bars() -> tuple[tuple[ReplayTick, ...], tuple[ClosedBar, ...]]:
    first_open = BASE + timedelta(seconds=59 * M5_SECONDS)
    ticks: list[ReplayTick] = []
    replay_bars: list[ClosedBar] = []
    prior_close = D("103.40")
    for relative, index in enumerate(range(59, 84)):
        opened = first_open + timedelta(seconds=relative * M5_SECONDS)
        values = [prior_close] * (M5_SECONDS // 5)
        if index == 59:
            values[10] = D("102.70")
            values[20] = D("103.50")
            values[-1] = D("103.40")
        elif index == 60:
            values[0] = D("103.40")
            values[1] = D("103.40")
            values[2] = D("106.50")
            values[-1] = D("106.00")
        else:
            values = [D("106.00")] * (M5_SECONDS // 5)
            values[10] = D("105.95")
            values[20] = D("106.05")
        for offset, bid in enumerate(values):
            event = opened + timedelta(seconds=offset * 5)
            ticks.append(
                ReplayTick(
                    tick_id=f"tick-{index}-{offset}",
                    event_time_utc=event,
                    available_at_utc=event + timedelta(seconds=1),
                    bid=bid,
                    ask=bid + D("0.05"),
                )
            )
        replay_bars.append(
            ClosedBar(
                evidence_id=f"m5-{index}",
                feed_id=FEED,
                source_revision="fixture-v1",
                symbol=SYMBOL,
                timeframe="M5",
                time_server_s=int(opened.timestamp()),
                broker_utc_offset_seconds=0,
                open_time_utc=opened,
                available_at_utc=opened + timedelta(seconds=M5_SECONDS + 1),
                open=values[0],
                high=max(values),
                low=min(values),
                close=values[-1],
                tick_size=TICK,
                digits=2,
            )
        )
        prior_close = values[-1]
    end = first_open + timedelta(seconds=25 * M5_SECONDS)
    ticks.append(
        ReplayTick(
            tick_id="tick-final",
            event_time_utc=end,
            available_at_utc=end + timedelta(seconds=1),
            bid=prior_close,
            ask=prior_close + D("0.05"),
        )
    )
    return tuple(ticks), tuple(replay_bars)


def source() -> PA01BacktestInput:
    ticks, replay_bars = replay_ticks_and_bars()
    m5 = (*warmup_m5(), *replay_bars)
    window_start = replay_bars[0].close_time_utc
    window_end = window_start + timedelta(hours=2)
    eligible = replay_bars[:12]
    fields = {
        "protocol": INPUT_PROTOCOL,
        "producer_revision": PRODUCER_REVISION,
        "strategy_version": STRATEGY_VERSION,
        "parameter_version": PARAMETER_VERSION,
        "parameter_hash": PARAMETER_HASH,
        "strategy_code_hash": PA01_CODE_HASH,
        "feed_id": FEED,
        "symbol": SYMBOL,
        "broker_utc_offset_seconds": 0,
        "tick_size": TICK,
        "digits": 2,
        "split": "train",
        "evaluation_window": EvaluationWindow(
            start_utc=window_start,
            end_utc=window_end,
            prior_development_cutoff_utc=None,
            embargo_seconds=0,
        ),
        "cost_assumptions": CostAssumptions(
            spread_points=D("5"),
            slippage_points=D("1"),
            commission_per_lot=D("2"),
            swap_included=True,
            operating_cost_per_trade=D("0.5"),
            currency="USD",
        ),
        "bootstrap": BootstrapPlan(seed=17, samples=1000, block_length=1),
        "initial_equity": D("10000"),
        "filled_volume_lots": D("0.1"),
        "point_value_per_lot": D("1"),
        "swap_cost_per_trade": D("0"),
        "m5_bars": m5,
        "h1_bars": h1_bars(),
        "policies": tuple(
            ReplayPolicy(
                m5_evidence_id=item.evidence_id,
                observed_at_utc=item.available_at_utc,
                source_id="fixture-news-coverage",
                market_open=True,
                news_blocked=False,
            )
            for item in eligible
        ),
        "ticks": ticks,
    }
    provisional = PA01BacktestInput.model_construct(source_dataset_hash="0" * 64, **fields)
    payload = provisional.model_dump(mode="json", exclude={"source_dataset_hash"})
    digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
    return PA01BacktestInput.model_validate({**fields, "source_dataset_hash": digest})


def source_data() -> dict:
    return source().model_dump(mode="json")


def rehash(value: dict) -> dict:
    value.pop("source_dataset_hash", None)
    value["source_dataset_hash"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    return value


def decimal_text(value: Decimal) -> str:
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result


def parse(value: dict) -> PA01BacktestInput:
    return PA01BacktestInput.model_validate(backtest_dict(canonical(value)))


def private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path.resolve()


def private_file(path: Path, raw: str) -> Path:
    path.write_text(raw)
    os.chmod(path, 0o600)
    return path.resolve()


def test_point_in_time_replay_builds_evaluator_compatible_bundle():
    candidate = source()
    bundle = build_bundle(candidate)
    repeated = build_bundle(candidate)
    evaluation = evaluate_bundle(bundle)
    trades = tuple(record for record in bundle.records if isinstance(record, ClosedTrade))

    assert bundle == repeated
    assert trades
    assert trades[0].label == "TP_FIRST"
    assert trades[0].gross_pnl > 0
    assert trades[0].evidence_ids[1].startswith(f"source:{candidate.source_dataset_hash}:")
    assert bundle.equity_samples[0].event_time_utc == candidate.evaluation_window.start_utc
    assert bundle.equity_samples[-1].event_time_utc == candidate.evaluation_window.end_utc
    assert any(sample.open_setup_ids for sample in bundle.equity_samples)
    assert evaluation.metrics.sample_size == len(trades)
    assert evaluation.metrics.net_return_pct > 0
    assert evaluation.evidence_manifest.record_counts.wait > 0


def test_tick_order_labels_stop_before_later_quotes():
    value = source_data()
    stopped = next(item for item in value["ticks"] if item["tick_id"] == "tick-60-2")
    stopped.update(bid="102", ask="102.05")
    replay_bar = next(item for item in value["m5_bars"] if item["evidence_id"] == "m5-60")
    replay_bar.update(high="106", low="102")
    bundle = build_bundle(parse(rehash(value)))
    trades = tuple(record for record in bundle.records if isinstance(record, ClosedTrade))
    assert trades[0].label == "SL_FIRST"
    assert trades[0].exit_at_utc == datetime(2026, 1, 1, 5, 0, 10, tzinfo=UTC)
    assert trades[0].gross_pnl < 0


def test_tick_order_uses_twelve_bar_time_exit_without_invented_price():
    value = source_data()
    for tick in value["ticks"]:
        if tick["tick_id"] == "tick-final" or int(tick["tick_id"].split("-")[1]) >= 60:
            tick.update(bid="103.4", ask="103.45")
    for replay_bar in value["m5_bars"]:
        if int(replay_bar["evidence_id"].split("-")[1]) >= 60:
            replay_bar.update(open="103.4", high="103.4", low="103.4", close="103.4")
    bundle = build_bundle(parse(rehash(value)))
    trades = tuple(record for record in bundle.records if isinstance(record, ClosedTrade))
    assert trades[0].label == "TIME_EXIT"
    assert trades[0].exit_at_utc == datetime(2026, 1, 1, 6, 0, 5, tzinfo=UTC)
    assert trades[0].gross_pnl == 0


def test_sell_replay_uses_ask_for_threshold_and_bid_path_for_gross_pnl():
    value = source_data()
    ceiling = D("220")
    for item in (*value["m5_bars"], *value["h1_bars"]):
        old = {key: D(item[key]) for key in ("open", "high", "low", "close")}
        item.update(
            open=decimal_text(ceiling - old["open"]),
            high=decimal_text(ceiling - old["low"]),
            low=decimal_text(ceiling - old["high"]),
            close=decimal_text(ceiling - old["close"]),
        )
    for tick in value["ticks"]:
        bid = ceiling - D(tick["bid"])
        tick.update(bid=decimal_text(bid), ask=decimal_text(bid + D("0.05")))
    bundle = build_bundle(parse(rehash(value)))
    trades = tuple(record for record in bundle.records if isinstance(record, ClosedTrade))
    assert trades[0].label == "TP_FIRST"
    assert trades[0].gross_pnl > 0


def test_canonical_input_and_future_append_do_not_rewrite_prior_outcomes(tmp_path):
    original_data = source_data()
    original_raw = canonical(original_data)
    input_file = private_file(private_directory(tmp_path / "input") / "replay.json", original_raw)
    original = load_backtest_input(input_file)
    before = build_bundle(original)

    later = deepcopy(original_data)
    last = later["ticks"][-1]
    event = datetime.fromisoformat(last["event_time_utc"].replace("Z", "+00:00"))
    available = datetime.fromisoformat(last["available_at_utc"].replace("Z", "+00:00"))
    later["ticks"].append(
        {
            "tick_id": "future-append",
            "event_time_utc": (event + timedelta(seconds=5))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
            "available_at_utc": (available + timedelta(seconds=5))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
            "bid": last["bid"],
            "ask": str(D(last["bid"]) + D("99")),
        }
    )
    later["m5_bars"].append(bar("M5", 84, close=D("106")).model_dump(mode="json"))
    after = build_bundle(parse(rehash(later)))
    assert before.dataset_hash != after.dataset_hash
    assert evaluate_bundle(before).metrics == evaluate_bundle(after).metrics
    assert [record.model_dump(exclude={"evidence_ids"}) for record in before.records] == [
        record.model_dump(exclude={"evidence_ids"}) for record in after.records
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["policies"].pop(),
        lambda value: value["ticks"].__setitem__(1, value["ticks"][0]),
        lambda value: value["ticks"].pop(),
        lambda value: value["m5_bars"][-1].update(high="999"),
        lambda value: value["cost_assumptions"].update(spread_points="4"),
        lambda value: value["h1_bars"].__delitem__(slice(-3, None)),
        lambda value: value["policies"][0].update(
            observed_at_utc="2026-01-01T04:59:50.000000Z"
        ),
        lambda value: value.update(initial_equity="100000000000001"),
    ],
)
def test_incomplete_schedule_order_path_spread_or_h1_fails_closed(mutate):
    value = source_data()
    mutate(value)
    with pytest.raises((ValidationError, ValueError)):
        parse(rehash(value))


def test_noncanonical_float_hash_and_unknown_fields_are_rejected():
    value = source_data()
    raw = canonical(value)
    with pytest.raises(ValueError):
        backtest_dict(raw.replace('"initial_equity":"10000"', '"initial_equity":10000.0'))
    with pytest.raises(ValueError):
        backtest_dict(json.dumps(value))
    value["unknown"] = True
    with pytest.raises(ValidationError):
        parse(rehash(value))
    value = source_data()
    value["evaluation_window"]["start_utc"] = "2026-01-01T05:00:00+00:00"
    with pytest.raises(ValueError):
        parse(rehash(value))
    value = source_data()
    value["strategy_code_hash"] = "f" * 64
    with pytest.raises(ValidationError):
        parse(rehash(value))
    value = source_data()
    value["source_dataset_hash"] = "0" * 64
    with pytest.raises(ValueError):
        backtest_dict(canonical(value))


def test_private_atomic_output_and_cli_are_idempotent(tmp_path, capsys):
    candidate = source()
    raw = canonical(candidate.model_dump(mode="json"))
    input_file = private_file(private_directory(tmp_path / "input") / "source.json", raw)
    output_directory = private_directory(tmp_path / "output")
    output_file = output_directory / "bundle.json"

    assert main(["build", "--input", str(input_file), "--output", str(output_file)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "BUILT"
    assert result["auto_trading_enabled"] is False
    assert stat_mode(output_file) == 0o600
    first = output_file.read_bytes()
    assert main(["build", "--input", str(input_file), "--output", str(output_file)]) == 0
    capsys.readouterr()
    assert output_file.read_bytes() == first

    other = output_directory / "other.json"
    private_file(other, "different")
    with pytest.raises(PA01BacktestInvalid):
        write_bundle(other, build_bundle(candidate))


def test_cli_redacts_invalid_relative_paths(capsys):
    assert main(["build", "--input", "relative.json", "--output", "bundle.json"]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "state": "PA01_BACKTEST_INVALID",
        "promotion_decided": False,
        "execution_ready": False,
        "auto_trading_enabled": False,
    }


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_output_failure_leaves_no_temporary_bundle(tmp_path):
    candidate = source()
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(PA01BacktestInvalid):
        write_bundle(public.resolve() / "bundle.json", build_bundle(candidate))
    assert list(public.iterdir()) == []


def test_output_size_boundary_fails_before_bundle_acceptance(monkeypatch):
    monkeypatch.setattr(backtest, "MAX_BUNDLE_BYTES", 1)
    with pytest.raises(PA01BacktestInvalid):
        build_bundle(source())


def test_replay_has_no_network_broker_promotion_or_command_authority():
    source_text = Path("services/worker/src/sochron_worker/pa01_backtest.py").read_text()
    for forbidden in (
        "import httpx",
        "import requests",
        "supabase",
        "OrderSend",
        "ExecutionService",
        "service_role",
        "strategy_versions",
        "commands",
        "risk_events",
        "auto_trading_enabled: Literal[True]",
    ):
        assert forbidden not in source_text
