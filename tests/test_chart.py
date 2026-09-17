from __future__ import annotations

import asyncio
import copy
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient, MockTransport, Response
from pydantic import SecretStr, ValidationError
from sochron1k.chart import (
    MAX_CHART_BYTES,
    PERIODS,
    ChartFrame,
    ChartSettings,
    ChartStore,
    load_chart_settings,
)
from sochron1k.main import create_app
from sochron1k.owner_auth import OwnerAuthSettings, OwnerVerifier
from sochron1k.telemetry import BridgeDenied, BridgeSettings, TelemetryBridge, TelemetryFrame
from test_owner_auth import ORIGIN, OWNER, bearer
from test_telemetry_bridge import Clock


@pytest.fixture
def setup_chart():
    clock = Clock()
    raw = json.loads(Path("tests/fixtures/mt5-telemetry-v1.json").read_text())
    settings = BridgeSettings(
        identity=raw["identity"],
        token=SecretStr(secrets.token_urlsafe(32)),
        broker_utc_offset_seconds=7200,
    )
    bridge = TelemetryBridge(settings, utc_now=clock.now, monotonic=clock.monotonic)
    raw.update(
        boot_id=str(bridge.boot_id),
        observed_at=clock.utc.isoformat(),
        tick_time_server_msc=int(clock.utc.timestamp() * 1000) + 7_200_000,
    )
    bridge.accept(TelemetryFrame.model_validate(raw))
    server_now = int(clock.utc.timestamp()) + 7200
    chart_settings = ChartSettings(
        offset_valid_from_server_s=server_now - 86400 * 30,
        offset_valid_until_server_s=server_now + 86400 * 30,
    )
    store = ChartStore(bridge, chart_settings, utc_now=clock.now, monotonic=clock.monotonic)
    return clock, bridge, store, raw


def packet(setup_chart, timeframe="M1", sequence=1):
    clock, bridge, _, raw = setup_chart
    current = (int(clock.utc.timestamp()) + 7200) // PERIODS[timeframe] * PERIODS[timeframe]
    return {
        "protocol": "sochron.chart.v1",
        "source": "mt5-copyrates",
        "boot_id": str(bridge.boot_id),
        "sequence": sequence,
        "identity": raw["identity"],
        "trade_mode": "demo",
        "terminal_build": raw["terminal_build"],
        "observed_at": clock.utc.isoformat(),
        "broker_utc_offset_seconds": 7200,
        "timeframe": timeframe,
        "price_basis": "bid",
        "digits": raw["contract"]["digits"],
        "tick_size": raw["contract"]["tick_size"],
        "bars": [
            {
                "time_server_s": current - (2 - index) * PERIODS[timeframe],
                "open": "2500.0000000000",
                "high": "2501.0000000000",
                "low": "2499.0000000000",
                "close": "2500.2000000000",
                "tick_volume": 10,
                "spread_points": 20,
            }
            for index in range(3)
        ],
    }


@pytest.mark.parametrize("timeframe", PERIODS)
def test_ac01_native_window_utc_precision_closed_vs_forming(setup_chart, timeframe):
    clock, _, store, _ = setup_chart
    data = packet(setup_chart, timeframe)
    assert not store.accept(ChartFrame.model_validate(data)).duplicate
    view = store.view(timeframe)
    assert view.state == "ready" and not view.execution_ready
    assert not view.feed_status.auto_trading_enabled
    assert [bar.closed for bar in view.observation.bars] == [True, True, False]
    assert view.observation.bars[-1].open_time_utc == clock.utc
    assert view.observation.received_time_utc == clock.utc
    assert view.observation.bars[-1].time_server_s == int(clock.utc.timestamp()) + 7200
    assert '"2500.0000000000"' in view.model_dump_json()
    assert not view.observation.gaps


@pytest.mark.parametrize(
    "change",
    [
        {"trade_mode": "real"},
        {"trade_mode": "contest"},
        {"source": "mt5-ea-sampled"},
        {"timeframe": "D1"},
        {"sequence": True},
        {"sequence": 0},
        {"unexpected": "data"},
        {"observed_at": "2026-09-17T00:00:00"},
        {"bars": []},
    ],
)
def test_ac02_invalid_envelope(setup_chart, change):
    data = packet(setup_chart)
    data.update(change)
    with pytest.raises(ValidationError):
        ChartFrame.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        {"open": "0"},
        {"high": "2490"},
        {"low": "2502"},
        {"close": "2502"},
        {"open": "2500.001"},
        {"open": "NaN"},
        {"high": "Infinity"},
        {"tick_volume": -1},
        {"tick_volume": True},
        {"tick_volume": 0},
        {"tick_volume": 9_007_199_254_740_992},
        {"spread_points": -1},
        {"spread_points": 1.5},
        {"time_server_s": True},
        {"time_server_s": 1},
    ],
)
def test_ac02_invalid_bar_values(setup_chart, change):
    data = packet(setup_chart)
    data["bars"][0].update(change)
    with pytest.raises(ValidationError):
        ChartFrame.model_validate(data)


def test_ac02_exact_large_decimals_and_tick_grid(setup_chart):
    data = packet(setup_chart)
    data.update(digits=10, tick_size="0.0000000001")
    maximum = "99999999999999.9999999999"
    for bar in data["bars"]:
        bar.update(dict.fromkeys(("open", "high", "low", "close"), maximum))
    assert str(ChartFrame.model_validate(data).bars[0].open) == maximum
    data["bars"][0]["high"] = "999999999999999999999999"
    with pytest.raises(ValidationError):
        ChartFrame.model_validate(data)
    data = packet(setup_chart)
    data["tick_size"] = "0.5"
    with pytest.raises(ValidationError):
        ChartFrame.model_validate(data)


def test_ac02_order_bounds_gap_is_not_fabricated(setup_chart):
    _, _, store, _ = setup_chart
    data = packet(setup_chart)
    data["bars"].pop(1)
    store.accept(ChartFrame.model_validate(data))
    view = store.view("M1")
    assert len(view.observation.bars) == 2
    assert view.observation.gaps[0].missing_intervals == 1
    assert view.observation.gaps[0].classification == "unclassified"
    for bars in ([data["bars"][0]] * 2, list(reversed(data["bars"])), data["bars"] * 121):
        with pytest.raises(ValidationError):
            ChartFrame.model_validate({**data, "bars": bars})


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"boot_id": str(uuid4())}, "BOOT_MISMATCH"),
        ({"broker_utc_offset_seconds": 0}, "CLOCK_OFFSET_MISMATCH"),
        ({"terminal_build": 99999999}, "CHART_CONTRACT_MISMATCH"),
        ({"digits": 3}, "CHART_CONTRACT_MISMATCH"),
        ({"tick_size": "0.1"}, "CHART_CONTRACT_MISMATCH"),
        ({"observed_at": "2026-09-17T00:00:01Z"}, "OBSERVATION_CLOCK_INVALID"),
        ({"observed_at": "2026-09-16T23:59:54Z"}, "OBSERVATION_CLOCK_INVALID"),
    ],
)
def test_ac02_identity_contract_clock_rejections(setup_chart, change, code):
    _, _, store, _ = setup_chart
    with pytest.raises(BridgeDenied, match=code):
        store.accept(ChartFrame.model_validate({**packet(setup_chart), **change}))
    assert store.view("M1").state == "rejected"


@pytest.mark.parametrize(
    "field", ["executor_id", "account_ref", "server", "currency", "symbol", "margin_mode"]
)
def test_ac02_identity_pinning(setup_chart, field):
    _, _, store, _ = setup_chart
    data = packet(setup_chart)
    data["identity"] = dict(data["identity"])
    data["identity"][field] = {"currency": "EUR", "margin_mode": "retail_netting"}.get(
        field, "other"
    )
    with pytest.raises(BridgeDenied, match="IDENTITY_MISMATCH"):
        store.accept(ChartFrame.model_validate(data))


def test_ac02_future_and_missing_contract(setup_chart):
    _, bridge, store, _ = setup_chart
    data = packet(setup_chart)
    data["bars"][-1]["time_server_s"] += 60
    with pytest.raises(BridgeDenied, match="BAR_FROM_FUTURE"):
        store.accept(ChartFrame.model_validate(data))
    bridge.reject()
    with pytest.raises(BridgeDenied, match="CHART_CONTRACT_UNAVAILABLE"):
        store.accept(ChartFrame.model_validate(packet(setup_chart)))


@pytest.mark.parametrize(
    ("index", "change", "code"),
    [
        (0, {"close": "2500.3"}, "CLOSED_BAR_CHANGED"),
        (0, {"spread_points": 21}, "CLOSED_BAR_CHANGED"),
        (2, {"open": "2500.1"}, "FORMING_BAR_REGRESSED"),
        (2, {"high": "2500.8"}, "FORMING_BAR_REGRESSED"),
        (2, {"low": "2499.1"}, "FORMING_BAR_REGRESSED"),
        (2, {"tick_volume": 9}, "FORMING_BAR_REGRESSED"),
    ],
)
def test_ac02_no_silent_revisions(setup_chart, index, change, code):
    _, _, store, _ = setup_chart
    data = packet(setup_chart)
    store.accept(ChartFrame.model_validate(data))
    before = store.view("M1").observation
    data["sequence"] += 1
    data["bars"][index].update(change)
    with pytest.raises(BridgeDenied, match=code):
        store.accept(ChartFrame.model_validate(data))
    assert store.view("M1").observation == before
    assert store.view("M1").state == "rejected"


def test_ac02_forming_update_closure_and_rolling_window(setup_chart):
    clock, _, store, _ = setup_chart
    data = packet(setup_chart)
    store.accept(ChartFrame.model_validate(data))
    data["sequence"] = 2
    data["bars"][-1].update(high="2502", low="2498", close="2501", tick_volume=20)
    store.accept(ChartFrame.model_validate(data))
    clock.advance(60)
    data["sequence"] = 3
    data["observed_at"] = clock.utc.isoformat()
    latest = copy.deepcopy(data["bars"][-1])
    latest["time_server_s"] += 60
    data["bars"].append(latest)
    data["bars"].pop(0)
    store.accept(ChartFrame.model_validate(data))
    assert [bar.closed for bar in store.view("M1").observation.bars] == [True, True, False]
    assert store.view("M1").observation.bars[-2].high == 2502


@pytest.mark.parametrize("mode", ["missing", "backward", "price_basis"])
def test_ac02_reject_missing_bar_backwards_window_and_basis_change(setup_chart, mode):
    _, _, store, _ = setup_chart
    data = packet(setup_chart)
    store.accept(ChartFrame.model_validate(data))
    data["sequence"] = 2
    if mode == "missing":
        data["bars"].pop(1)
    elif mode == "backward":
        for bar in data["bars"]:
            bar["time_server_s"] -= 60
    else:
        data["price_basis"] = "last"
    with pytest.raises(BridgeDenied):
        store.accept(ChartFrame.model_validate(data))


def test_ac03_fixed_offset_interval_is_required_and_exclusive(setup_chart):
    clock, bridge, _, _ = setup_chart
    frame = ChartFrame.model_validate(packet(setup_chart))
    disabled = ChartStore(bridge, None)
    assert disabled.view("M1").state == "disabled"
    with pytest.raises(BridgeDenied, match="CHART_DISABLED"):
        disabled.accept(frame)
    for start, end in (
        (frame.bars[0].time_server_s + 1, frame.bars[-1].time_server_s + 60),
        (frame.bars[0].time_server_s, frame.bars[-1].time_server_s),
    ):
        limited = ChartStore(
            bridge,
            ChartSettings(offset_valid_from_server_s=start, offset_valid_until_server_s=end),
            utc_now=clock.now,
        )
        with pytest.raises(BridgeDenied, match="OFFSET_VALIDITY_EXCEEDED"):
            limited.accept(frame)


def test_ac03_private_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("SOCHRON_CHART_CONFIG_FILE", raising=False)
    assert load_chart_settings() is None
    path = tmp_path / "chart.json"
    path.write_text('{"offset_valid_from_server_s":100,"offset_valid_until_server_s":200}')
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_CHART_CONFIG_FILE", str(path))
    assert load_chart_settings().offset_valid_until_server_s == 200
    path.chmod(0o644)
    with pytest.raises(RuntimeError, match="Invalid private chart"):
        load_chart_settings()
    path.chmod(0o600)
    link = tmp_path / "link.json"
    link.symlink_to(path)
    monkeypatch.setenv("SOCHRON_CHART_CONFIG_FILE", str(link))
    with pytest.raises(RuntimeError):
        load_chart_settings()
    with pytest.raises(ValidationError):
        ChartSettings(offset_valid_from_server_s=200, offset_valid_until_server_s=100)


def test_ac05_duplicate_rejection_clock_and_concurrency(setup_chart):
    clock, _, store, _ = setup_chart
    frame = ChartFrame.model_validate(packet(setup_chart))
    with ThreadPoolExecutor(max_workers=8) as executor:
        receipts = list(executor.map(store.accept, [frame] * 32))
    assert sum(not receipt.duplicate for receipt in receipts) == 1
    before = store.view("M1").observation
    clock.advance(16)
    assert store.accept(frame).duplicate
    assert store.view("M1").state == "stale"
    assert store.view("M1").observation == before
    clock.utc -= timedelta(seconds=30)
    view = store.view("M1")
    assert view.state == "stale" and view.snapshot_age_seconds == 16
    store.reject()
    assert store.accept(frame).duplicate
    assert store.view("M1").state == "rejected"


def test_ac05_replay_sequence_independent_timeframes_and_restart(setup_chart):
    clock, bridge, store, _ = setup_chart
    data = packet(setup_chart)
    store.accept(ChartFrame.model_validate(data))
    store.accept(ChartFrame.model_validate(packet(setup_chart, "M5", 2)))
    with pytest.raises(BridgeDenied, match="OUT_OF_ORDER"):
        store.accept(ChartFrame.model_validate(data))
    store.accept(ChartFrame.model_validate(packet(setup_chart, "M1", 3)))
    assert store.view("M1").state == "ready"
    assert store.view("M5").state == "rejected"
    changed = packet(setup_chart, "M1", 3)
    changed["bars"][-1]["close"] = "2500.3"
    with pytest.raises(BridgeDenied, match="SEQUENCE_CONFLICT"):
        store.accept(ChartFrame.model_validate(changed))
    restarted = ChartStore(TelemetryBridge(bridge.settings), store.settings, utc_now=clock.now)
    assert restarted.view("M1").observation is None
    with pytest.raises(BridgeDenied, match="BOOT_MISMATCH"):
        restarted.accept(ChartFrame.model_validate(data))


def test_ac02_new_telemetry_contract_invalidates_cached_chart(setup_chart):
    _, bridge, store, raw = setup_chart
    store.accept(ChartFrame.model_validate(packet(setup_chart)))
    raw["sequence"] += 1
    raw["contract"]["digits"] += 1
    bridge.accept(TelemetryFrame.model_validate(raw))
    assert store.view("M1").state == "rejected"
    raw["sequence"] += 1
    raw["contract"]["digits"] -= 1
    bridge.accept(TelemetryFrame.model_validate(raw))
    assert store.view("M1").state == "rejected"
    store.accept(ChartFrame.model_validate(packet(setup_chart, sequence=2)))
    assert store.view("M1").state == "ready"


@pytest.fixture
async def chart_client(setup_chart):
    _, bridge, store, _ = setup_chart
    owner_settings = OwnerAuthSettings(
        supabase_url=ORIGIN, owner_id=OWNER, public_key=SecretStr("sb_publishable_" + "fixture" * 4)
    )

    def upstream(request):
        if request.url.path == "/auth/v1/user":
            return Response(
                200, json={"id": str(OWNER), "role": "authenticated", "is_anonymous": False}
            )
        return Response(200, json=True)

    app = create_app(bridge.settings, owner_settings, store.settings)
    app.state.telemetry_bridge = bridge
    app.state.chart_store = store
    app.state.owner_verifier = OwnerVerifier(
        owner_settings, transport=MockTransport(upstream), now=lambda: 1000
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://fixture") as client:
        yield client


def bridge_headers(setup_chart):
    return {"Authorization": "Bearer " + setup_chart[1].settings.token.get_secret_value()}


@pytest.mark.anyio
async def test_ac04_auth_before_body_and_owner_token_separation(setup_chart, chart_client):
    async def forbidden_body():
        raise AssertionError("unauthorized body consumed")
        yield b""

    for headers in ({}, bearer(), [*bridge_headers(setup_chart).items()] * 2):
        response = await chart_client.post(
            "/bridge/v1/chart/snapshot", headers=headers, content=forbidden_body()
        )
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
    assert (
        await chart_client.get("/owner/chart/M1", headers=bridge_headers(setup_chart))
    ).status_code == 401
    assert (await chart_client.get("/owner/chart/M1")).status_code == 401
    result = await chart_client.post(
        "/bridge/v1/chart/snapshot", headers=bridge_headers(setup_chart), json=packet(setup_chart)
    )
    assert result.status_code == 200
    view = await chart_client.get("/owner/chart/M1", headers=bearer())
    assert view.status_code == 200 and view.json()["state"] == "ready"
    assert view.json()["observation"]["bars"][-1]["closed"] is False
    assert view.headers["cache-control"] == "no-store"
    assert (await chart_client.get("/owner/chart/invalid", headers=bearer())).json() == {
        "detail": "INVALID_TIMEFRAME"
    }
    challenge = await chart_client.get(
        "/bridge/v1/chart/challenge", headers=bridge_headers(setup_chart)
    )
    assert challenge.json()["next_sequence"] == 2
    assert (
        await chart_client.get("/bridge/v1/challenge", headers=bridge_headers(setup_chart))
    ).json()["next_sequence"] == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("body", "extra_headers", "status"),
    [
        (b"{}", {}, 415),
        (b"{}", {"Content-Type": "application/json", "Content-Encoding": "gzip"}, 415),
        (b'{"bars":[],"bars":[]}', {"Content-Type": "application/json"}, 422),
        (b'{"secret":NaN}', {"Content-Type": "application/json"}, 422),
        (b'{"secret":"do-not-echo"}', {"Content-Type": "application/json"}, 422),
        (b"[" * 2000 + b"]" * 2000, {"Content-Type": "application/json"}, 422),
        (b" " * (MAX_CHART_BYTES + 1), {"Content-Type": "application/json"}, 413),
    ],
)
async def test_ac04_bounded_redacted_input(setup_chart, chart_client, body, extra_headers, status):
    async def chunks():
        for index in range(0, len(body), 4096):
            yield body[index : index + 4096]

    response = await chart_client.post(
        "/bridge/v1/chart/snapshot",
        headers={**bridge_headers(setup_chart), **extra_headers},
        content=chunks(),
    )
    assert response.status_code == status
    assert "do-not-echo" not in response.text
    assert setup_chart[2].view("M1").state == "rejected"
    assert setup_chart[1].status().state == "connected"


@pytest.mark.anyio
async def test_ac04_body_deadline_and_chart_disabled(setup_chart, chart_client, monkeypatch):
    original_timeout = asyncio.timeout

    def short_test_timeout(seconds):
        assert seconds == 2
        return original_timeout(0.001)

    monkeypatch.setattr("sochron1k.bridge_api.asyncio.timeout", short_test_timeout)

    async def slow():
        yield b"{"
        await asyncio.sleep(0.02)

    response = await chart_client.post(
        "/bridge/v1/chart/snapshot",
        headers={**bridge_headers(setup_chart), "Content-Type": "application/json"},
        content=slow(),
    )
    assert response.status_code == 408
    async with AsyncClient(
        transport=ASGITransport(app=create_app(setup_chart[1].settings)), base_url="http://fixture"
    ) as client:
        assert (
            await client.get("/bridge/v1/chart/challenge", headers=bridge_headers(setup_chart))
        ).status_code == 503
        health = (await client.get("/health")).json()
        assert not health["auto_trading_enabled"] and not health["execution_ready"]
