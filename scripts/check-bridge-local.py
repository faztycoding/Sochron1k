#!/usr/bin/env python3
"""SCN-004/006/007 loopback HTTP and local history; no MT5 connection."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def main() -> None:
    identity = {
        "executor_id": "synthetic-http-ea",
        "account_ref": "synthetic-http-demo",
        "server": "Synthetic-Demo",
        "currency": "USD",
        "margin_mode": "retail_hedging",
        "symbol": "XAUUSD.fixture",
    }
    credential = secrets.token_urlsafe(32)
    config = {"identity": identity, "token": credential, "broker_utc_offset_seconds": 0}
    with tempfile.TemporaryDirectory(prefix="sochron-bridge-check-") as directory:
        private = Path(directory) / "bridge.json"
        with os.fdopen(
            os.open(private, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
        ) as stream:
            json.dump(config, stream)
        chart_private = Path(directory) / "chart.json"
        now_seconds = int(time.time())
        with os.fdopen(
            os.open(chart_private, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
        ) as stream:
            json.dump(
                {
                    "offset_valid_from_server_s": now_seconds - 86400,
                    "offset_valid_until_server_s": now_seconds + 86400,
                },
                stream,
            )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            port = listener.getsockname()[1]
            environment = os.environ | {
                "PYTHONPATH": str(ROOT / "services/api/src"),
                "SOCHRON_BRIDGE_CONFIG_FILE": str(private),
                "SOCHRON_CHART_CONFIG_FILE": str(chart_private),
                "SOCHRON_CHART_HISTORY_DIR": str(Path(directory).resolve()),
                "TRADING_MODE": "live",
                "AUTO_TRADING_ENABLED": "true",
            }
            environment.pop("SOCHRON_OWNER_AUTH_CONFIG_FILE", None)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "sochron1k.main:app",
                    "--fd",
                    str(listener.fileno()),
                    "--no-access-log",
                    "--log-level",
                    "critical",
                ],
                cwd=ROOT,
                env=environment,
                pass_fds=(listener.fileno(),),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False
                ) as client:
                    deadline = time.monotonic() + 10
                    while True:
                        require(process.poll() is None, "API exited before health check")
                        try:
                            health = client.get("/health")
                            if health.status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        require(time.monotonic() < deadline, "API startup deadline exceeded")
                        time.sleep(0.05)
                    require(not health.json()["execution_ready"], "health promoted execution")
                    require(not health.json()["auto_trading_enabled"], "auto trading enabled")
                    require(client.get("/bridge/v1/snapshot").status_code == 401, "anonymous read")
                    auth = {"Authorization": f"Bearer {credential}"}
                    challenge = client.get("/bridge/v1/challenge", headers=auth)
                    require(challenge.status_code == 200, "challenge failed")
                    now = datetime.now(UTC)
                    packet = {
                        "protocol": "sochron.telemetry.v1",
                        "source": "mt5-ea-sampled",
                        "boot_id": challenge.json()["boot_id"],
                        "sequence": 1,
                        "identity": identity,
                        "trade_mode": "demo",
                        "terminal_build": 1,
                        "terminal_connected": True,
                        "account_trade_allowed": False,
                        "observed_at": now.isoformat(),
                        "tick_time_server_msc": int(now.timestamp() * 1000) - 10_000,
                        "broker_utc_offset_seconds": 0,
                        "equity": "1000",
                        "balance": "1000",
                        "free_margin": "1000",
                        "bid": "2500",
                        "ask": "2500.2",
                        "contract": {
                            "symbol": "XAUUSD.fixture",
                            "digits": 2,
                            "tick_size": "0.01",
                            "volume_min": "0.01",
                            "volume_max": "100",
                            "volume_step": "0.01",
                            "stops_level_points": 0,
                            "freeze_level_points": 0,
                            "filling_modes": ["fok"],
                        },
                    }
                    require(
                        client.post("/bridge/v1/snapshot", headers=auth, json=packet).status_code
                        == 200,
                        "snapshot not accepted",
                    )
                    status = client.get("/bridge/v1/status")
                    require(status.json()["state"] == "stale", "old tick presented as fresh")
                    packet.update(sequence=2, tick_time_server_msc=int(now.timestamp() * 1000))
                    require(
                        client.post("/bridge/v1/snapshot", headers=auth, json=packet).status_code
                        == 200,
                        "fresh snapshot not accepted",
                    )
                    require(
                        client.get("/bridge/v1/status").json()["state"] == "connected",
                        "fresh telemetry not connected",
                    )
                    received = client.get("/bridge/v1/snapshot", headers=auth).json()[
                        "received_time_utc"
                    ]
                    duplicate = client.post("/bridge/v1/snapshot", headers=auth, json=packet)
                    require(duplicate.json()["duplicate"], "duplicate not recognized")
                    require(
                        client.get("/bridge/v1/snapshot", headers=auth).json()["received_time_utc"]
                        == received,
                        "replay refreshed receipt time",
                    )
                    chart_challenge = client.get("/bridge/v1/chart/challenge", headers=auth)
                    require(chart_challenge.status_code == 200, "chart challenge failed")
                    require(chart_challenge.json()["next_sequence"] == 1, "chart sequence shared")
                    bar_start = int(time.time()) // 60 * 60
                    chart_packet = {
                        "protocol": "sochron.chart.v1",
                        "source": "mt5-copyrates",
                        "boot_id": chart_challenge.json()["boot_id"],
                        "sequence": 1,
                        "identity": identity,
                        "trade_mode": "demo",
                        "terminal_build": 1,
                        "observed_at": datetime.now(UTC).isoformat(),
                        "broker_utc_offset_seconds": 0,
                        "timeframe": "M1",
                        "price_basis": "bid",
                        "digits": 2,
                        "tick_size": "0.01",
                        "bars": [
                            {
                                "time_server_s": bar_start - (239 - index) * 60,
                                "open": "2500.00",
                                "high": "2501.00",
                                "low": "2499.00",
                                "close": "2500.20",
                                "tick_volume": 10,
                                "spread_points": 20,
                            }
                            for index in range(240)
                        ],
                    }
                    require(len(json.dumps(chart_packet)) > 16_384, "fixture below chart boundary")
                    require(
                        client.post("/bridge/v1/chart/snapshot", json=chart_packet).status_code
                        == 401,
                        "anonymous chart write",
                    )
                    chart_received = client.post(
                        "/bridge/v1/chart/snapshot", headers=auth, json=chart_packet
                    )
                    require(chart_received.status_code == 200, "native bars not accepted")
                    with closing(
                        sqlite3.connect(
                            (Path(directory) / "bars.sqlite3").as_uri() + "?mode=ro", uri=True
                        )
                    ) as durable:
                        require(
                            durable.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0]
                            == 239,
                            "HTTP acknowledged before closed bars were durable",
                        )
                        require(
                            durable.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1,
                            "receipt missing after acknowledgment",
                        )
                    require(
                        client.post(
                            "/bridge/v1/chart/snapshot", headers=auth, json=chart_packet
                        ).json()["duplicate"],
                        "chart replay not detected",
                    )
                    require(
                        client.get("/bridge/v1/challenge", headers=auth).json()["next_sequence"]
                        == 3,
                        "chart changed telemetry sequence",
                    )
                    require(
                        client.get("/owner/chart/M1", headers=auth).status_code == 503,
                        "executor credential bypassed disabled owner auth",
                    )
                    require(
                        client.get("/owner/history/M1", headers=auth).status_code == 503,
                        "executor credential bypassed history owner authorization",
                    )
                    chart_packet["sequence"] = 2
                    chart_packet["bars"][0]["close"] = "2500.30"
                    correction = client.post(
                        "/bridge/v1/chart/snapshot", headers=auth, json=chart_packet
                    )
                    require(
                        correction.status_code == 409
                        and correction.json() == {"detail": "CLOSED_BAR_CHANGED"},
                        "closed bar changed silently",
                    )
                    require(
                        correction.headers.get("cache-control") == "no-store", "chart cacheable"
                    )
                    require(
                        client.get("/bridge/v1/status").json()["state"] == "connected",
                        "chart rejection mutated independent quote state",
                    )
                    packet["trade_mode"] = "real"
                    denied = client.post("/bridge/v1/snapshot", headers=auth, json=packet)
                    require(denied.status_code == 422, "non-Demo packet accepted")
                    status = client.get("/bridge/v1/status")
                    require(
                        status.json()["state"] == "rejected",
                        "invalid telemetry did not fail closed",
                    )
                    require(status.headers.get("cache-control") == "no-store", "status cacheable")
                    require(
                        not any(value in status.text for value in identity.values()),
                        "public identity leak",
                    )
                    require(
                        client.post("/bridge/v1/orders", headers=auth, json={}).status_code == 404,
                        "trade route exists",
                    )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

            # Reopen only this verifier's private archive after the API has stopped.
            with closing(
                sqlite3.connect((Path(directory) / "bars.sqlite3").as_uri() + "?mode=ro", uri=True)
            ) as durable:
                require(
                    durable.execute("PRAGMA quick_check").fetchone()[0] == "ok",
                    "history integrity check failed",
                )
                require(
                    durable.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 239,
                    "history lost after API shutdown",
                )
                require(
                    durable.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1,
                    "duplicate or rejected packet changed durable receipts",
                )
                require(
                    durable.execute("SELECT COUNT(*) FROM latest_frames").fetchone()[0] == 1,
                    "validation baseline missing",
                )

    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    files = [
        "scripts/check-bridge-local.py",
        "services/api/src/sochron1k/telemetry.py",
        "services/api/src/sochron1k/bridge_api.py",
        "services/api/src/sochron1k/main.py",
        "services/api/src/sochron1k/chart.py",
        "services/api/src/sochron1k/chart_api.py",
        "services/api/src/sochron1k/bar_history.py",
        "tests/test_bar_history.py",
        "tests/test_chart.py",
        "tests/test_telemetry_bridge.py",
    ]
    print(
        json.dumps(
            {
                "contracts": ["SCN-004", "SCN-006 API ingress", "SCN-007 local persistence"],
                "result": "PASS",
                "source_revision": revision,
                "dirty": dirty,
                "python": platform.python_version(),
                "environment": "loopback HTTP",
                "fixture": "synthetic-http-v1 and 240 native-bar wire fixtures",
                "checked_at": datetime.now(UTC).isoformat(),
                "sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files
                },
                "limits": (
                    "No MT5/EA/compiler/broker operation, browser Auth, "
                    "power-loss durability, Supabase history sync or deployment evidence"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Do not dump HTTP requests, private config or their containing exceptions.
        print(
            "FAIL SCN-004/006/007 loopback verifier; no broker operation attempted", file=sys.stderr
        )
        raise SystemExit(1) from None
