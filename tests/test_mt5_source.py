from __future__ import annotations

import json
import runpy
import secrets
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sochron1k.chart import ChartFrame, ChartSettings, ChartStore
from sochron1k.main import create_app
from sochron1k.telemetry import BridgeSettings, TelemetryBridge, TelemetryFrame

ROOT = Path(__file__).resolve().parents[1]
GUARD = runpy.run_path(str(ROOT / "scripts/check-mt5-source.py"))
SAMPLE = ROOT / "tests/fixtures/mt5-telemetry-v1.json"
FIXTURE_VERIFIER = runpy.run_path(str(ROOT / "scripts/check-mt5-fixture.py"))


def test_ea06_observer_source_guard_and_header_secret_scan_coverage():
    for name in GUARD["SOURCES"]:
        assert (
            GUARD["findings"](
                (ROOT / name).read_text(),
                protocol=name.endswith(".mqh"),
                self_test="SelfTest" in name,
            )
            == []
        )
    scanner = runpy.run_path(str(ROOT / "scripts/check-no-secrets.py"))
    assert ROOT / "mt5/ea/TelemetryProtocol.mqh" in scanner["candidate_files"]()


@pytest.mark.parametrize("identifier", sorted(GUARD["FORBIDDEN"]))
def test_ea06_guard_detects_forbidden_operation_mutation(identifier):
    source = (ROOT / "mt5/ea/SochronTelemetry.mq5").read_text()
    assert GUARD["findings"](source + f"\nvoid injected() {{ {identifier}(); }}")


def test_ea06_guard_detects_external_include_and_enabled_default_mutations():
    source = (ROOT / "mt5/ea/SochronTelemetry.mq5").read_text()
    assert GUARD["findings"](source + "\n#include <Trade/Trade.mqh>")
    assert GUARD["findings"](source + '\n#import "external.dll"')
    assert GUARD["findings"](
        source.replace("EnableReadOnlyTelemetry=false", "EnableReadOnlyTelemetry=true")
    )
    assert GUARD["findings"](source + '\ninput string PrivateToken="";')
    assert GUARD["findings"](
        source.replace("EnableReadOnlyCharts=false", "EnableReadOnlyCharts=true")
    )


@pytest.mark.parametrize("operation", ["CopyRates", "SeriesInfoInteger", "SymbolInfoInteger"])
@pytest.mark.parametrize("name", ["TelemetryProtocol.mqh", "SochronTelemetrySelfTest.mq5"])
def test_chart_source_guard_denies_terminal_access_in_pure_helpers(operation, name):
    source = (ROOT / "mt5/ea" / name).read_text()
    assert GUARD["findings"](
        source + f"\nvoid injected() {{ {operation}(); }}",
        protocol=name.endswith(".mqh"),
        self_test="SelfTest" in name,
    )


def test_chart_golden_verifier_preserves_decimal_time_and_provenance(tmp_path):
    golden = ROOT / "tests/fixtures/mt5-chart-v1.json"
    report = FIXTURE_VERIFIER["verify"](golden, chart=True)
    assert report["input_is_committed_golden"] is True
    assert report["protocol"] == "sochron.chart.v1"
    generated = tmp_path / "chart.json"
    generated.write_bytes(golden.read_bytes())
    assert FIXTURE_VERIFIER["verify"](generated, chart=True)["input_is_committed_golden"] is False
    packet = json.loads(golden.read_bytes())
    packet["bars"][-1]["close"] = "2500.250"  # Even numerically equal is not exact wire parity.
    generated.write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="not the exact synthetic fixture"):
        FIXTURE_VERIFIER["verify"](generated, chart=True)
    generated.write_bytes(golden.read_bytes() + b"\0")
    with pytest.raises(ValueError, match="encoding or size"):
        FIXTURE_VERIFIER["verify"](generated, chart=True)
    generated.write_text('{"bars":[],"bars":[]}')
    with pytest.raises(ValueError):
        FIXTURE_VERIFIER["verify"](generated, chart=True)
    generated.write_bytes(b" " * 131073)
    with pytest.raises(ValueError, match="encoding or size"):
        FIXTURE_VERIFIER["verify"](generated, chart=True)


@pytest.mark.anyio
async def test_chart_mql_golden_wire_passes_ingress_and_normalizes_current_bar():
    # Golden source is hand-authored; this does not claim MQL execution or compilation.
    quote = TelemetryFrame.model_validate_json(SAMPLE.read_bytes())
    chart_packet = json.loads((ROOT / "tests/fixtures/mt5-chart-v1.json").read_bytes())
    ChartFrame.model_validate(chart_packet)
    settings = BridgeSettings(
        identity=quote.identity,
        token=SecretStr(secrets.token_urlsafe(32)),
        broker_utc_offset_seconds=7200,
    )
    clock = lambda: datetime(2026, 9, 17, tzinfo=UTC)  # noqa: E731
    bridge = TelemetryBridge(settings, utc_now=clock)
    chart = ChartStore(
        bridge,
        ChartSettings(
            offset_valid_from_server_s=1789600000, offset_valid_until_server_s=1789700000
        ),
        utc_now=clock,
    )
    app = create_app(settings)
    app.state.telemetry_bridge = bridge
    app.state.chart_store = chart
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://fixture") as client:
        auth = {"Authorization": "Bearer " + settings.token.get_secret_value()}
        telemetry = quote.model_dump(mode="json")
        telemetry["boot_id"] = str(bridge.boot_id)
        assert (
            await client.post("/bridge/v1/snapshot", headers=auth, json=telemetry)
        ).status_code == 200
        challenge = (await client.get("/bridge/v1/chart/challenge", headers=auth)).json()
        chart_packet["boot_id"] = challenge["boot_id"]
        response = await client.post("/bridge/v1/chart/snapshot", headers=auth, json=chart_packet)
        assert response.status_code == 200
        assert response.json() == {"accepted": True, "duplicate": False, "sequence": 1}
        view = chart.view("M5")
        assert view.state == "ready" and view.execution_ready is False
        assert view.observation.bars[0].closed is True
        assert view.observation.bars[1].closed is False
        assert view.observation.bars[1].open_time_utc == clock()
        assert str(view.observation.bars[1].close) == "2500.25"
        repeat = await client.post("/bridge/v1/chart/snapshot", headers=auth, json=chart_packet)
        assert repeat.json()["duplicate"] is True
        chart_packet["sequence"] = 2
        chart_packet["bars"][0]["close"] = "2500.25"
        invalid = await client.post("/bridge/v1/chart/snapshot", headers=auth, json=chart_packet)
        assert invalid.status_code == 409 and invalid.json()["detail"] == "CLOSED_BAR_CHANGED"
        assert chart.view("M5").state == "rejected"
        assert bridge.status().state == "connected"


def test_ea06_guard_does_not_treat_comments_or_strings_as_operations():
    source = (ROOT / "mt5/ea/SochronTelemetry.mq5").read_text()
    assert not GUARD["findings"](source + '\n// OrderSend();\nstring label="OrderSend";')


def test_ea06_fixture_verifier_is_explicit_about_provenance(tmp_path):
    report = FIXTURE_VERIFIER["verify"](SAMPLE)
    assert report["input_is_committed_golden"] is True
    generated = tmp_path / "synthetic.json"
    generated.write_text(json.dumps(json.loads(SAMPLE.read_bytes()), separators=(",", ":")))
    report = FIXTURE_VERIFIER["verify"](generated)
    assert report["input_is_committed_golden"] is False
    assert "Does not attest" in report["limits"]
    packet = json.loads(generated.read_bytes())
    packet["equity"] = "1001.0000000000"
    generated.write_text(json.dumps(packet))
    with pytest.raises(ValueError, match="not the exact synthetic fixture"):
        FIXTURE_VERIFIER["verify"](generated)
    generated.write_bytes(SAMPLE.read_bytes() + b"\0")
    with pytest.raises(ValueError, match="encoding or size"):
        FIXTURE_VERIFIER["verify"](generated)


@pytest.mark.anyio
async def test_ea06_synthetic_golden_fixture_is_accepted_by_api():
    # This proves the expected wire format, NOT that MQL5 produced this file.
    body = SAMPLE.read_bytes()
    frame = TelemetryFrame.model_validate_json(body)
    settings = BridgeSettings(
        identity=frame.identity,
        token=SecretStr(secrets.token_urlsafe(32)),
        broker_utc_offset_seconds=7200,
    )
    bridge = TelemetryBridge(settings, utc_now=lambda: datetime(2026, 9, 17, tzinfo=UTC))
    app = create_app(settings)
    app.state.telemetry_bridge = bridge
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://fixture") as client:
        auth = {"Authorization": "Bearer " + settings.token.get_secret_value()}
        challenge = (await client.get("/bridge/v1/challenge", headers=auth)).json()
        packet = json.loads(body)
        packet["boot_id"] = challenge["boot_id"]
        response = await client.post("/bridge/v1/snapshot", headers=auth, json=packet)
        assert response.status_code == 200
        observation = (await client.get("/bridge/v1/snapshot", headers=auth)).json()
        assert observation["event_time_utc"] == "2026-09-17T00:00:00Z"
        assert observation["frame"]["ask"] == "2500.2000000000"
        assert (await client.get("/bridge/v1/status")).json()["state"] == "connected"
        assert (await client.get("/health")).json()["execution_ready"] is False
