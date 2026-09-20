from __future__ import annotations

import asyncio
import copy
import json
import os
import sqlite3
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sochron1k import bar_history
from sochron1k.bar_history import BarHistory, HistoryUnavailable
from sochron1k.chart import ChartFrame, ChartStore
from sochron1k.main import create_app
from sochron1k.telemetry import BridgeDenied, TelemetryBridge, TelemetryFrame
from test_chart import bridge_headers, packet
from test_chart import chart_client as chart_client
from test_chart import setup_chart as setup_chart
from test_owner_auth import OTHER, bearer, token


@pytest.fixture
def archive(tmp_path, setup_chart):
    directory = tmp_path.resolve()
    directory.chmod(0o700)
    _, bridge, store, _ = setup_chart
    return BarHistory(directory, bridge.settings, store.settings)


def attach(setup_chart, archive):
    store = setup_chart[2]
    store.history = archive
    return store


def accept(setup_chart, sequence=1):
    frame = ChartFrame.model_validate(packet(setup_chart, sequence=sequence))
    store = setup_chart[2]
    store.accept(frame)
    return frame, store.view("M1").observation


def counts(archive):
    with archive._connect() as db:
        return tuple(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("receipts", "closed_bars", "latest_frames")
        )


def test_ac02_commit_provenance_exact_values_and_duplicate(setup_chart, archive):
    store = attach(setup_chart, archive)
    frame, observation = accept(setup_chart)
    history = archive.read("M1")
    assert history.state == "available" and history.through_receipt == 1
    assert counts(archive) == (1, 2, 1)
    assert len(history.bars) == 2 and all(bar.closed for bar in history.bars)
    assert history.bars[0].first_received_at == observation.received_time_utc
    assert history.bars[0].first_received_at > history.bars[0].open_time_utc
    assert history.bars[0].first_receipt == 1
    assert history.bars[0].confirmed_by_server_s == frame.bars[1].time_server_s
    assert history.bars[1].confirmed_by_server_s == frame.bars[2].time_server_s
    assert str(history.bars[0].close) == "2500.2000000000"
    assert history.bars[0].source_observed_at == frame.observed_at
    assert not history.execution_ready
    assert store.accept(frame).duplicate
    assert archive.record(frame, observation) == 1
    assert archive.read("M1") == history and counts(archive) == (1, 2, 1)
    assert archive.read("M1", through_receipt=0, archive_id=archive.archive_id).bars == ()
    assert archive.path.stat().st_mode & 0o777 == 0o600
    with archive._connect() as db:
        assert db.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        for table in ("closed_bars", "receipts"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                db.execute(f"DELETE FROM {table}")


def test_ac05_closed_transition_pagination_and_immutable_watermark(setup_chart, archive):
    clock, _, store, _ = setup_chart
    attach(setup_chart, archive)
    frame, _ = accept(setup_chart)
    first = archive.read("M1", limit=1)
    clock.advance(60)
    accept(setup_chart, sequence=2)
    history = archive.read("M1")
    assert len(history.bars) == 3
    assert history.bars[-1].time_server_s == frame.bars[-1].time_server_s
    assert history.bars[-1].first_receipt == 2
    assert history.bars[-1].first_received_at == clock.utc
    assert history.bars[0].first_received_at < clock.utc
    second = archive.read(
        "M1",
        after_server_s=first.bars[-1].time_server_s,
        through_receipt=first.through_receipt,
        archive_id=first.archive_id,
    )
    assert len(second.bars) == 1 and second.through_receipt == 1
    assert second.bars[0] == history.bars[1]
    assert store.view("M1").observation.bars[-1].closed is False
    with pytest.raises(BridgeDenied, match="WATERMARK"):
        archive.read("M1", through_receipt=3, archive_id=archive.archive_id)
    with pytest.raises(BridgeDenied, match="ARCHIVE_REQUIRED"):
        archive.read("M1", through_receipt=1)
    with pytest.raises(BridgeDenied, match="ARCHIVE_MISMATCH"):
        archive.read("M1", archive_id="not-this-archive")


def test_ac06_gaps_remain_explicit_across_page_boundary(setup_chart, archive):
    store = attach(setup_chart, archive)
    data = packet(setup_chart)
    data["bars"][0]["time_server_s"] -= 120
    store.accept(ChartFrame.model_validate(data))
    first = archive.read("M1", limit=1)
    second = archive.read(
        "M1",
        after_server_s=first.bars[0].time_server_s,
        through_receipt=first.through_receipt,
        archive_id=first.archive_id,
    )
    assert len(second.bars) == 1 and second.gaps[0].missing_intervals == 2
    assert second.gaps[0].classification == "unclassified"
    assert counts(archive) == (1, 2, 1)


def test_ac04_restart_restores_validation_not_live_data(setup_chart, archive):
    clock, bridge, store, raw = setup_chart
    attach(setup_chart, archive)
    frame, _ = accept(setup_chart)
    restarted_archive = BarHistory(archive.directory, bridge.settings, store.settings)
    restarted_bridge = TelemetryBridge(
        bridge.settings, utc_now=clock.now, monotonic=clock.monotonic
    )
    restarted = ChartStore(
        restarted_bridge,
        store.settings,
        history=restarted_archive,
        utc_now=clock.now,
        monotonic=clock.monotonic,
    )
    assert restarted_archive.read("M1").bars == archive.read("M1").bars
    assert restarted.view("M1").state == "awaiting_snapshot"
    assert restarted.view("M1").observation is None
    with pytest.raises(BridgeDenied, match="BOOT_MISMATCH"):
        restarted.accept(frame)
    quote = copy.deepcopy(raw)
    quote["boot_id"] = str(restarted_bridge.boot_id)
    restarted_bridge.accept(TelemetryFrame.model_validate(quote))
    data = packet(setup_chart)
    data["boot_id"] = str(restarted_bridge.boot_id)
    data["bars"][0]["close"] = "2500.3"
    with pytest.raises(BridgeDenied, match="CLOSED_BAR_CHANGED"):
        restarted.accept(ChartFrame.model_validate(data))
    assert counts(archive) == (1, 2, 1)
    data["bars"][0]["close"] = "2500.2000000000"
    restarted.accept(ChartFrame.model_validate(data))
    assert counts(archive) == (2, 2, 1)


def test_ac02_independent_connections_deduplicate_and_reject_conflicts(setup_chart, archive):
    frame, observation = accept(setup_chart)
    _, bridge, store, _ = setup_chart
    another = BarHistory(archive.directory, bridge.settings, store.settings)
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(lambda a: a.record(frame, observation), [archive, another] * 4))
    assert receipts == [1] * 8 and counts(archive) == (1, 2, 1)
    changed = frame.model_dump(mode="json")
    changed["bars"][-1]["close"] = "2500.3"
    with pytest.raises(BridgeDenied, match="RECEIPT_CONFLICT"):
        another.record(ChartFrame.model_validate(changed), observation)
    changed["sequence"] = 2
    changed["bars"][0]["close"] = "2500.3"
    changed_frame = ChartFrame.model_validate(changed)
    changed_observation = observation.model_copy(
        update={
            "sequence": 2,
            "bars": (
                observation.bars[0].model_copy(update={"close": changed_frame.bars[0].close}),
                *observation.bars[1:],
            ),
        }
    )
    with pytest.raises(BridgeDenied, match="HISTORY_CLOSED_BAR_CHANGED"):
        another.record(changed_frame, changed_observation)
    assert counts(archive) == (1, 2, 1)


def test_ac03_atomic_rollback_and_latch_without_publishing(setup_chart, archive):
    store = attach(setup_chart, archive)
    with archive._connect() as db:
        db.execute("""CREATE TRIGGER fail_projection BEFORE INSERT ON latest_frames
                      BEGIN SELECT RAISE(ABORT, 'synthetic disk failure'); END""")
    with pytest.raises(HistoryUnavailable, match=r"^HISTORY_UNAVAILABLE$"):
        accept(setup_chart)
    assert counts(archive) == (0, 0, 0)
    assert store.next_sequence() == 1 and store.view("M1").observation is None
    assert store.view("M1").state == "rejected"
    assert setup_chart[1].status().state == "connected"
    with archive._connect() as db:
        db.execute("DROP TRIGGER fail_projection")
    with pytest.raises(HistoryUnavailable):
        accept(setup_chart)
    assert counts(archive) == (0, 0, 0)


def test_ac03_busy_database_has_no_partial_ack(setup_chart, archive):
    store = attach(setup_chart, archive)
    with archive._connect() as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        with pytest.raises(HistoryUnavailable):
            accept(setup_chart)
        blocker.rollback()
    assert counts(archive) == (0, 0, 0)
    assert store.next_sequence() == 1


def test_ac06_page_quota_rolls_back_without_pruning(setup_chart, archive, monkeypatch):
    attach(setup_chart, archive)
    frame, _ = accept(setup_chart)
    before = archive.read("M1")
    monkeypatch.setattr(bar_history, "MAX_DATABASE_BYTES", before.database_bytes)
    data = packet(setup_chart, sequence=2)
    # Larger historical window cannot fit at the current page count. Use the
    # archive directly because the monitoring cache deliberately denies backfill.
    data["bars"] = [
        dict(data["bars"][0], time_server_s=frame.bars[-1].time_server_s - i * 60)
        for i in range(239, -1, -1)
    ]
    independent = ChartStore(setup_chart[1], setup_chart[2].settings, utc_now=setup_chart[0].now)
    expanded = ChartFrame.model_validate(data)
    independent.accept(expanded)
    with pytest.raises(HistoryUnavailable):
        archive.record(expanded, independent.view("M1").observation)
    assert counts(archive) == (1, 2, 1)
    assert archive.read("M1").bars == before.bars


def test_ac04_clock_rollback_cannot_backdate_receipts(setup_chart, archive):
    frame, observation = accept(setup_chart)
    archive.record(frame, observation)
    later = frame.model_copy(update={"sequence": 2})
    earlier = observation.model_copy(
        update={
            "sequence": 2,
            "received_time_utc": observation.received_time_utc - timedelta(seconds=1),
        }
    )
    with pytest.raises(BridgeDenied, match="HISTORY_CLOCK_REVERSED"):
        archive.record(later, earlier)
    assert counts(archive) == (1, 2, 1)


@pytest.mark.parametrize(
    "unsafe", ["directory", "file", "symlink", "hardlink", "version", "corrupt", "identity"]
)
def test_ac01_reject_unsafe_or_incompatible_archive(setup_chart, archive, unsafe):
    _, bridge, store, _ = setup_chart
    directory = archive.directory
    settings = bridge.settings
    if unsafe == "directory":
        directory.chmod(0o755)
    elif unsafe == "file":
        archive.path.chmod(0o644)
    elif unsafe == "symlink":
        target = directory / "original.sqlite3"
        archive.path.rename(target)
        archive.path.symlink_to(target)
    elif unsafe == "hardlink":
        os.link(archive.path, directory / "another.sqlite3")
    elif unsafe == "version":
        with archive._connect() as db:
            db.execute("PRAGMA user_version=999")
    elif unsafe == "corrupt":
        archive.path.write_bytes(b"not a database")
    else:
        settings = settings.model_copy(
            update={
                "identity": settings.identity.model_copy(update={"server": "different-fixture"})
            }
        )
    with pytest.raises(HistoryUnavailable, match=r"^HISTORY_UNAVAILABLE$"):
        BarHistory(directory, settings, store.settings)


def test_ac01_detect_projection_and_closed_record_corruption(setup_chart, archive):
    attach(setup_chart, archive)
    accept(setup_chart)
    _, bridge, store, _ = setup_chart
    with archive._connect() as db:
        db.execute("UPDATE latest_frames SET payload='{}'")
    with pytest.raises(HistoryUnavailable):
        BarHistory(archive.directory, bridge.settings, store.settings)
    with archive._connect() as db:
        db.execute("DROP TRIGGER immutable_bars_update")
        db.execute("UPDATE closed_bars SET payload='{}'")
    with pytest.raises(HistoryUnavailable):
        archive.read("M1")


@pytest.mark.parametrize("phase", ["before", "after"])
def test_ac04_process_exit_at_commit_boundary(setup_chart, archive, phase):
    frame, observation = accept(setup_chart)
    source = r"""
import json, os, sqlite3, sys
from pathlib import Path
sys.path.insert(0, "services/api/src")
from pydantic import SecretStr
from sochron1k.bar_history import BarHistory
from sochron1k.chart import ChartFrame, ChartObservation, ChartSettings
from sochron1k.telemetry import BridgeSettings
data=json.load(sys.stdin)
frame=ChartFrame.model_validate(data["frame"])
settings=BridgeSettings(identity=frame.identity, token=SecretStr("s"*43),
                       broker_utc_offset_seconds=7200)
history=BarHistory(Path(sys.argv[1]), settings, ChartSettings.model_validate(data["settings"]))
original=sqlite3.connect
class CrashConnection(sqlite3.Connection):
    def commit(self):
        if sys.argv[2]=="before": os._exit(73)
        super().commit()
        os._exit(74)
sqlite3.connect=lambda *a, **kw: original(*a, **kw, factory=CrashConnection)
history.record(frame, ChartObservation.model_validate(data["observation"]))
raise AssertionError("crash point not reached")
"""
    result = subprocess.run(
        [sys.executable, "-c", source, str(archive.directory), phase],
        input=json.dumps(
            {
                "frame": frame.model_dump(mode="json"),
                "observation": observation.model_dump(mode="json"),
                "settings": setup_chart[2].settings.model_dump(mode="json"),
            }
        ),
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == (73 if phase == "before" else 74), result.stderr
    restored = BarHistory(archive.directory, setup_chart[1].settings, setup_chart[2].settings)
    assert counts(restored) == ((0, 0, 0) if phase == "before" else (1, 2, 1))
    assert restored.record(frame, observation) == 1
    assert counts(restored) == (1, 2, 1)


@pytest.mark.anyio
async def test_ac05_owner_history_authority_and_disabled_state(setup_chart, chart_client, archive):
    client = chart_client
    disabled = await client.get("/owner/history/M1", headers=bearer())
    assert disabled.json()["state"] == "disabled" and disabled.json()["bars"] == []
    attach(setup_chart, archive)
    for headers in ({}, bridge_headers(setup_chart), bearer(token(sub=str(OTHER)))):
        response = await client.get("/owner/history/M1", headers=headers)
        assert response.status_code in (401, 403) and "bars" not in response.json()
        assert response.headers["cache-control"] == "no-store"
    assert (
        await client.post(
            "/bridge/v1/chart/snapshot",
            headers=bridge_headers(setup_chart),
            json=packet(setup_chart),
        )
    ).status_code == 200
    response = await client.get("/owner/history/M1?limit=1", headers=bearer())
    assert response.status_code == 200 and len(response.json()["bars"]) == 1
    assert response.json()["through_receipt"] == 1
    assert response.json()["identity"] == setup_chart[1].settings.identity.model_dump(mode="json")
    for suffix in ("M2", "M1?limit=241", "M1?after_server_s=-1"):
        assert (await client.get("/owner/history/" + suffix, headers=bearer())).status_code == 422
    assert (
        await client.get("/owner/history/M1?through_receipt=2", headers=bearer())
    ).status_code == 409
    assert (
        await client.get(
            f"/owner/history/M1?through_receipt=1&archive_id={archive.archive_id}", headers=bearer()
        )
    ).status_code == 200
    assert (
        await client.get("/owner/history/M1?archive_id=wrong", headers=bearer())
    ).status_code == 409
    assert (await client.post("/owner/history/M1", headers=bearer(), json={})).status_code == 405


@pytest.mark.anyio
async def test_ac03_storage_failure_redacted_and_rejected_payload_not_saved(
    setup_chart, chart_client, archive
):
    store = attach(setup_chart, archive)
    malformed = packet(setup_chart)
    malformed["trade_mode"] = "real"
    response = await chart_client.post(
        "/bridge/v1/chart/snapshot", headers=bridge_headers(setup_chart), json=malformed
    )
    assert response.status_code == 422 and counts(archive) == (0, 0, 0)
    with archive._connect() as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        response = await chart_client.post(
            "/bridge/v1/chart/snapshot",
            headers=bridge_headers(setup_chart),
            json=packet(setup_chart),
        )
        assert response.status_code == 503 and response.json() == {"detail": "HISTORY_UNAVAILABLE"}
        blocker.rollback()
    assert counts(archive) == (0, 0, 0) and store.next_sequence() == 1
    assert store.view("M1").state == "rejected"
    assert setup_chart[1].status().state == "connected"


@pytest.mark.anyio
async def test_ac03_blocking_record_does_not_block_event_loop(
    setup_chart, chart_client, archive, monkeypatch
):
    attach(setup_chart, archive)
    entered, release = threading.Event(), threading.Event()
    original = archive.record

    def paused(*args):
        entered.set()
        if not release.wait(3):
            raise AssertionError("event loop was blocked by SQLite work")
        return original(*args)

    monkeypatch.setattr(archive, "record", paused)
    task = asyncio.create_task(
        chart_client.post(
            "/bridge/v1/chart/snapshot",
            headers=bridge_headers(setup_chart),
            json=packet(setup_chart),
        )
    )
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        async with asyncio.timeout(1):
            response = await chart_client.get("/health")
        assert response.status_code == 200 and not response.json()["execution_ready"]
    finally:
        release.set()
        await task
    assert task.result().status_code == 200


def test_ac01_application_requires_chart_config_for_history(tmp_path, setup_chart):
    with pytest.raises(HistoryUnavailable):
        create_app(history_directory=tmp_path.resolve())
    directory = tmp_path.resolve()
    directory.chmod(0o700)
    _, bridge, store, _ = setup_chart
    app = create_app(bridge.settings, chart_settings=store.settings, history_directory=directory)
    assert app.state.chart_store.history is not None
    assert app.state.chart_store.view("M1").state == "awaiting_snapshot"


def test_ac01_directory_sidecar_and_replaced_file_denial(setup_chart, archive):
    _, bridge, store, _ = setup_chart
    linked = archive.directory / "linked-directory"
    linked.symlink_to(archive.directory, target_is_directory=True)
    with pytest.raises(HistoryUnavailable):
        BarHistory(linked, bridge.settings, store.settings)
    sidecar = archive.directory / "bars.sqlite3-wal"
    sidecar.symlink_to(archive.path)
    with pytest.raises(HistoryUnavailable):
        archive.read("M1")
    sidecar.unlink()  # Only this test's generated symlink, never a user's archive.
    replacement = archive.directory / "saved.sqlite3"
    archive.path.rename(replacement)
    with pytest.raises(HistoryUnavailable):
        archive.read("M1")
    assert not archive.path.exists()  # No silent recreation of a missing archive.
    archive.path.write_bytes(replacement.read_bytes())
    archive.path.chmod(0o600)
    with pytest.raises(HistoryUnavailable):
        archive.read("M1")  # Existing handle pins the file identity too.


def test_ac01_offset_interval_change_requires_review(setup_chart, archive):
    _, bridge, store, _ = setup_chart
    changed = store.settings.model_copy(
        update={
            "offset_valid_until_server_s": store.settings.offset_valid_until_server_s + 1,
        }
    )
    with pytest.raises(HistoryUnavailable):
        BarHistory(archive.directory, bridge.settings, changed)


def test_ac02_equivalent_decimal_format_keeps_original_evidence(setup_chart, archive):
    store = attach(setup_chart, archive)
    accept(setup_chart)
    first = archive.read("M1")
    data = packet(setup_chart, sequence=2)
    for bar in data["bars"]:
        bar["close"] = "2500.2"
    store.accept(ChartFrame.model_validate(data))
    assert archive.read("M1").bars == first.bars
    assert counts(archive) == (2, 2, 1)


@pytest.mark.parametrize(("fraction", "expected"), [(0.71, "warning_70"), (0.86, "warning_85")])
def test_ac06_storage_warning_thresholds(setup_chart, archive, monkeypatch, fraction, expected):
    attach(setup_chart, archive)
    accept(setup_chart)
    size = archive.read("M1").database_bytes
    monkeypatch.setattr(bar_history, "MAX_DATABASE_BYTES", int(size / fraction))
    view = archive.read("M1")
    assert view.storage == expected and view.quota_bytes == int(size / fraction)
    status = archive.storage_status()
    assert status.state == expected
    assert status.database_bytes == size and status.quota_bytes == int(size / fraction)


@pytest.mark.anyio
async def test_ac03_read_failure_latches_ingress(setup_chart, chart_client, archive):
    store = attach(setup_chart, archive)
    accept(setup_chart)
    before = store.next_sequence()
    archive.path.chmod(0o644)
    response = await chart_client.get("/owner/history/M1", headers=bearer())
    assert response.status_code == 503 and response.json() == {"detail": "HISTORY_UNAVAILABLE"}
    archive.path.chmod(0o600)
    response = await chart_client.post(
        "/bridge/v1/chart/snapshot",
        headers=bridge_headers(setup_chart),
        json=packet(setup_chart, sequence=2),
    )
    assert response.status_code == 503 and store.next_sequence() == before
    assert store.view("M1").state == "rejected"
