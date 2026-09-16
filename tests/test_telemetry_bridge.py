from __future__ import annotations

import asyncio
import json
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sochron1k.main import create_app
from sochron1k.telemetry import (
    MAX_FRAME_BYTES,
    BridgeDenied,
    BridgeSettings,
    DemoIdentity,
    TelemetryBridge,
    TelemetryFrame,
    load_bridge_settings,
)


@dataclass
class Clock:
    utc: datetime = datetime(2026, 9, 17, 0, 0, 0, tzinfo=UTC)
    ticks: float = 100.0

    def now(self) -> datetime:
        return self.utc

    def monotonic(self) -> float:
        return self.ticks

    def advance(self, seconds: float) -> None:
        self.utc += timedelta(seconds=seconds)
        self.ticks += seconds


@pytest.fixture
def settings() -> BridgeSettings:
    return BridgeSettings(
        identity=DemoIdentity(
            executor_id="synthetic-ea",
            account_ref="synthetic-demo-account",
            server="Synthetic-Demo",
            currency="USD",
            margin_mode="retail_hedging",
            symbol="XAUUSD.fixture",
        ),
        token=SecretStr(secrets.token_urlsafe(32)),
        broker_utc_offset_seconds=7200,
    )


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def bridge(settings, clock) -> TelemetryBridge:
    return TelemetryBridge(settings, utc_now=clock.now, monotonic=clock.monotonic)


@pytest.fixture
def payload(settings, clock, bridge) -> dict:
    return {
        "protocol": "sochron.telemetry.v1",
        "source": "mt5-ea-sampled",
        "boot_id": str(bridge.boot_id),
        "sequence": 1,
        "identity": settings.identity.model_dump(),
        "trade_mode": "demo",
        "terminal_build": 1,  # Synthetic; not evidence of any installed MT5 build.
        "terminal_connected": True,
        "account_trade_allowed": False,
        "observed_at": clock.utc.isoformat(),
        "tick_time_server_msc": int(clock.utc.timestamp() * 1000) + 7_200_000,
        "broker_utc_offset_seconds": 7200,
        "equity": "1000.00",
        "balance": "1000.00",
        "free_margin": "1000.00",
        "bid": "2500.00",
        "ask": "2500.20",
        "contract": {
            "symbol": "XAUUSD.fixture",
            "digits": 2,
            "tick_size": "0.01",
            "volume_min": "0.01",
            "volume_max": "100",
            "volume_step": "0.01",
            "stops_level_points": 10,
            "freeze_level_points": 0,
            "filling_modes": ["fok", "ioc"],
        },
    }


@pytest.fixture
async def client(bridge, settings):
    app = create_app(settings)
    app.state.telemetry_bridge = bridge
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://fixture") as client:
        yield client


@pytest.fixture
def auth(settings) -> dict:
    return {"Authorization": "Bearer " + settings.token.get_secret_value()}


@pytest.mark.anyio
async def test_ac01_default_disabled_and_private_routes_denied():
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://fixture"
    ) as client:
        assert (await client.get("/bridge/v1/status")).json()["state"] == "disabled"
        for path in ("challenge", "snapshot"):
            assert (await client.get(f"/bridge/v1/{path}")).status_code == 503
        assert (await client.post("/bridge/v1/snapshot", json={})).status_code == 503


@pytest.mark.anyio
async def test_ac01_authentication_precedes_body_consumption(client, bridge, auth):
    async def forbidden_body():
        raise AssertionError("unauthorized body was consumed")
        yield b""  # pragma: no cover

    for headers in ({}, {"Authorization": "Bearer invalid"}, [*auth.items(), *auth.items()]):
        response = await client.post(
            "/bridge/v1/snapshot", headers=headers, content=forbidden_body()
        )
        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"
    assert bridge.status().state == "awaiting_snapshot"
    assert (await client.get("/bridge/v1/snapshot")).status_code == 401
    assert (await client.get("/bridge/v1/challenge")).status_code == 401


@pytest.mark.anyio
async def test_ac02_accept_snapshot_preserve_provenance_and_redact_public_status(
    client, payload, auth, clock, settings
):
    challenge = (await client.get("/bridge/v1/challenge", headers=auth)).json()
    assert challenge == {"boot_id": payload["boot_id"], "next_sequence": 1}
    assert (await client.get("/bridge/v1/snapshot", headers=auth)).status_code == 404
    response = await client.post("/bridge/v1/snapshot", headers=auth, json=payload)
    assert response.json() == {"accepted": True, "duplicate": False, "sequence": 1}
    observation = (await client.get("/bridge/v1/snapshot", headers=auth)).json()
    assert observation["received_time_utc"] == "2026-09-17T00:00:00Z"
    assert observation["event_time_utc"] == "2026-09-17T00:00:00Z"
    assert observation["frame"]["tick_time_server_msc"] == payload["tick_time_server_msc"]
    status = await client.get("/bridge/v1/status")
    assert status.json() == {
        "state": "connected",
        "heartbeat_fresh": True,
        "price_fresh": True,
        "heartbeat_age_seconds": 0.0,
        "price_age_seconds": 0.0,
        "auto_trading_enabled": False,
        "execution_ready": False,
    }
    for value in (*settings.identity.model_dump().values(), settings.token.get_secret_value()):
        assert value not in status.text
    assert (await client.get("/bridge/v1/challenge", headers=auth)).json()["next_sequence"] == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    "field", ["executor_id", "account_ref", "server", "currency", "margin_mode", "symbol"]
)
async def test_ac02_deny_changed_identity(client, payload, auth, field):
    payload["identity"][field] = {"currency": "EUR", "margin_mode": "retail_netting"}.get(
        field, "different"
    )
    response = await client.post("/bridge/v1/snapshot", headers=auth, json=payload)
    assert response.status_code == 409
    assert response.json() == {"detail": "IDENTITY_MISMATCH"}
    assert (await client.get("/bridge/v1/status")).json()["state"] == "rejected"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trade_mode", "real"),
        ("trade_mode", "contest"),
        ("trade_mode", "unknown"),
        ("trade_mode", None),
        ("equity", "NaN"),
        ("equity", "Infinity"),
        ("bid", "0"),
        ("ask", "2499"),
        ("sequence", True),
        ("sequence", "1"),
        ("terminal_connected", "false"),
        ("observed_at", "2026-09-17T00:00:00"),
        ("source", "simulator"),
        ("unexpected", "private-input-marker"),
    ],
)
async def test_ac02_ac03_invalid_frame_is_redacted(client, payload, auth, field, value, caplog):
    payload[field] = value
    response = await client.post("/bridge/v1/snapshot", headers=auth, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "INVALID_FRAME"}
    assert "private-input-marker" not in caplog.text
    assert payload["identity"]["account_ref"] not in caplog.text
    assert (await client.get("/bridge/v1/status")).json()["state"] == "rejected"


@pytest.mark.anyio
@pytest.mark.parametrize("field", ["identity", "trade_mode", "observed_at", "contract", "boot_id"])
async def test_ac02_missing_required_evidence(client, payload, auth, field):
    del payload[field]
    assert (await client.post("/bridge/v1/snapshot", headers=auth, json=payload)).status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tick_size", "NaN"),
        ("volume_max", "0.001"),
        ("volume_step", "0"),
        ("digits", True),
        ("filling_modes", []),
        ("filling_modes", ["invented"]),
    ],
)
async def test_ac03_invalid_contract(client, payload, auth, field, value):
    payload["contract"][field] = value
    assert (await client.post("/bridge/v1/snapshot", headers=auth, json=payload)).status_code == 422


@pytest.mark.anyio
async def test_ac03_clock_checks(client, payload, auth, clock):
    original = payload.copy()
    for changes, code in [
        ({"broker_utc_offset_seconds": 0}, "CLOCK_OFFSET_MISMATCH"),
        (
            {"observed_at": (clock.utc + timedelta(seconds=1)).isoformat()},
            "OBSERVATION_CLOCK_INVALID",
        ),
        (
            {"observed_at": (clock.utc - timedelta(seconds=6)).isoformat()},
            "OBSERVATION_CLOCK_INVALID",
        ),
        ({"tick_time_server_msc": payload["tick_time_server_msc"] + 2000}, "TICK_FROM_FUTURE"),
    ]:
        response = await client.post("/bridge/v1/snapshot", headers=auth, json=original | changes)
        assert response.status_code == 409
        assert response.json()["detail"] == code


def test_ac04_duplicates_never_refresh_or_release_rejection(bridge, payload, clock):
    frame = TelemetryFrame.model_validate(payload)
    bridge.accept(frame)
    clock.advance(6)
    assert bridge.accept(frame).duplicate
    assert bridge.status().heartbeat_age_seconds == 6
    assert not bridge.status().price_fresh
    bridge.reject()
    bridge.accept(frame)
    assert bridge.status().state == "rejected"


def test_ac04_sequence_conflict_reversal_and_recovery(bridge, payload, clock):
    bridge.accept(TelemetryFrame.model_validate(payload))
    with pytest.raises(BridgeDenied, match="SEQUENCE_CONFLICT"):
        bridge.accept(TelemetryFrame.model_validate(payload | {"bid": "2500.01"}))
    clock.advance(1)
    later = payload | {"sequence": 3, "observed_at": clock.utc.isoformat()}
    bridge.accept(TelemetryFrame.model_validate(later))
    assert bridge.status().state == "connected"
    with pytest.raises(BridgeDenied, match="OUT_OF_ORDER"):
        bridge.accept(TelemetryFrame.model_validate(later | {"sequence": 2}))
    with pytest.raises(BridgeDenied, match="TIME_REVERSAL"):
        bridge.accept(TelemetryFrame.model_validate(payload | {"sequence": 4}))
    with pytest.raises(BridgeDenied, match="TIME_REVERSAL"):
        bridge.accept(
            TelemetryFrame.model_validate(
                later | {"sequence": 4, "tick_time_server_msc": payload["tick_time_server_msc"] - 1}
            )
        )


def test_ac04_concurrent_duplicate_is_atomic(bridge, payload):
    frame = TelemetryFrame.model_validate(payload)
    with ThreadPoolExecutor(max_workers=8) as pool:
        receipts = list(pool.map(lambda _: bridge.accept(frame), range(32)))
    assert sum(not receipt.duplicate for receipt in receipts) == 1
    assert bridge.observation().frame.sequence == 1


def test_ac04_old_lifetime_cannot_replay(settings, bridge, payload, clock):
    bridge.accept(TelemetryFrame.model_validate(payload))
    restarted = TelemetryBridge(settings, utc_now=clock.now, monotonic=clock.monotonic)
    assert restarted.status().state == "awaiting_snapshot"
    with pytest.raises(BridgeDenied, match="BOOT_MISMATCH"):
        restarted.accept(TelemetryFrame.model_validate(payload))
    assert restarted.observation() is None


@pytest.mark.parametrize("seconds, fresh", [(5, True), (5.001, False), (100, False)])
def test_ac05_staleness_boundary(bridge, payload, clock, seconds, fresh):
    bridge.accept(TelemetryFrame.model_validate(payload))
    clock.advance(seconds)
    assert bridge.status().price_fresh is fresh
    assert bridge.status().heartbeat_fresh is fresh


def test_ac05_new_heartbeat_cannot_refresh_old_tick(bridge, payload, clock):
    bridge.accept(TelemetryFrame.model_validate(payload))
    clock.advance(6)
    bridge.accept(
        TelemetryFrame.model_validate(
            payload | {"sequence": 2, "observed_at": clock.utc.isoformat()}
        )
    )
    assert bridge.status().heartbeat_fresh
    assert not bridge.status().price_fresh
    assert bridge.status().price_age_seconds == 6


def test_ac05_clock_rollback_and_disconnected_terminal(bridge, payload, clock):
    bridge.accept(TelemetryFrame.model_validate(payload))
    clock.ticks += 10
    clock.utc -= timedelta(seconds=100)
    assert not bridge.status().price_fresh
    assert bridge.status().price_age_seconds == 10


def test_ac05_disconnected_and_negative_equity_remain_observable(bridge, payload):
    bridge.accept(
        TelemetryFrame.model_validate(
            payload | {"terminal_connected": False, "equity": "-1.00", "free_margin": "-1.00"}
        )
    )
    assert bridge.status().state == "stale"
    assert not bridge.status().heartbeat_fresh


@pytest.mark.anyio
async def test_ac06_body_bounds_and_redacted_errors(client, auth):
    async def chunks():
        yield b" " * (MAX_FRAME_BYTES // 2)
        yield b" " * (MAX_FRAME_BYTES // 2 + 1)

    response = await client.post(
        "/bridge/v1/snapshot", headers=auth | {"Content-Type": "application/json"}, content=chunks()
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "FRAME_TOO_LARGE"}
    for content, headers, expected in [
        (b"{}", auth, 415),
        (b"private-input-marker", auth | {"Content-Type": "application/json"}, 422),
        (b"{}", auth | {"Content-Type": "application/json", "Content-Encoding": "gzip"}, 415),
    ]:
        response = await client.post("/bridge/v1/snapshot", headers=headers, content=content)
        assert response.status_code == expected
        assert "private-input-marker" not in response.text
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_ac06_ambiguous_deep_and_nonfinite_json(client, auth):
    for body in (
        '{"trade_mode":"real","trade_mode":"demo"}',
        '{"identity":{"account_ref":"a","account_ref":"b"}}',
        '{"equity":NaN}',
        "[" * 1100 + "]" * 1100,
    ):
        response = await client.post(
            "/bridge/v1/snapshot", headers=auth | {"Content-Type": "application/json"}, content=body
        )
        assert response.status_code == 422
        assert response.json() == {"detail": "INVALID_FRAME"}


@pytest.mark.anyio
async def test_ac06_slow_body_has_deadline(client, auth):
    async def slow_body():
        yield b"{"
        await asyncio.sleep(10)
        yield b"}"

    response = await client.post(
        "/bridge/v1/snapshot",
        headers=auth | {"Content-Type": "application/json"},
        content=slow_body(),
    )
    assert response.status_code == 408
    assert response.json() == {"detail": "FRAME_TIMEOUT"}


@pytest.mark.anyio
async def test_ac08_telemetry_never_enables_or_adds_trade_routes(client, payload, auth):
    await client.post("/bridge/v1/snapshot", headers=auth, json=payload)
    health = (await client.get("/health")).json()
    assert health["auto_trading_enabled"] is False
    assert health["execution_ready"] is False
    for path in ("orders", "commands", "close", "cancel", "halt-release"):
        assert (await client.post(f"/bridge/v1/{path}", headers=auth, json={})).status_code == 404


def test_ac01_private_settings_disabled_and_rejects_bad_files(monkeypatch, tmp_path, settings):
    monkeypatch.delenv("SOCHRON_BRIDGE_CONFIG_FILE", raising=False)
    assert load_bridge_settings() is None
    private = tmp_path / "bridge.json"
    data = settings.model_dump(mode="json")
    data["token"] = settings.token.get_secret_value()
    private.write_text(json.dumps(data))
    private.chmod(0o600)
    monkeypatch.setenv("SOCHRON_BRIDGE_CONFIG_FILE", str(private))
    assert load_bridge_settings() == settings
    for mode in (0o644, 0o640, 0o604):
        private.chmod(mode)
        with pytest.raises(RuntimeError, match="Invalid private bridge configuration") as failure:
            load_bridge_settings()
        assert data["token"] not in str(failure.value)
    private.chmod(0o600)
    linked = tmp_path / "linked.json"
    linked.symlink_to(private)
    monkeypatch.setenv("SOCHRON_BRIDGE_CONFIG_FILE", str(linked))
    with pytest.raises(RuntimeError):
        load_bridge_settings()
    monkeypatch.setenv("SOCHRON_BRIDGE_CONFIG_FILE", str(private))
    private.write_text('{"token":"private-input-marker"}')
    with pytest.raises(RuntimeError) as failure:
        load_bridge_settings()
    assert "private-input-marker" not in str(failure.value)
    assert os.stat(private).st_mode & 0o777 == 0o600


def test_ac01_private_config_rejects_fifo_without_waiting(monkeypatch, tmp_path):
    fifo = tmp_path / "not-a-file"
    os.mkfifo(fifo, mode=0o600)
    monkeypatch.setenv("SOCHRON_BRIDGE_CONFIG_FILE", str(fifo))
    with pytest.raises(RuntimeError, match="Invalid private bridge configuration"):
        load_bridge_settings()
