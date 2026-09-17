from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import FrozenInstanceError
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sochron1k.chart import ChartFrame, ChartStore
from sochron1k.telemetry import TelemetryFrame
from sochron_worker import native_source
from sochron_worker.native_source import NativeArchiveSource, SourceCursor, SourceUnavailable
from test_bar_history import accept, attach
from test_bar_history import archive as archive
from test_chart import packet
from test_chart import setup_chart as setup_chart


def source(setup_chart, archive, **changes):
    clock, bridge, store, _ = setup_chart
    args = dict(
        directory=archive.directory,
        archive_id=UUID(archive.archive_id),
        identity=bridge.settings.identity,
        offset_seconds=bridge.settings.broker_utc_offset_seconds,
        chart=store.settings,
        utc_now=clock.now,
    )
    args.update(changes)
    return NativeArchiveSource(**args)


def record_packet(setup_chart, archive, data):
    clock, bridge, store, _ = setup_chart
    independent = ChartStore(bridge, store.settings, utc_now=clock.now)
    frame = ChartFrame.model_validate(data)
    independent.accept(frame)
    archive.record(frame, independent.view(frame.timeframe).observation)


def test_exact_committed_pages_no_create_or_table_writes(setup_chart, archive):
    attach(setup_chart, archive)
    accept(setup_chart)
    original = archive.path.read_bytes()
    reader = source(setup_chart, archive)
    first = reader.read(limit=1)
    second = reader.read(first.next_cursor, limit=1)
    assert first.after == SourceCursor() and len(first.rows) == len(second.rows) == 1
    assert first.next_cursor.receipt == second.next_cursor.receipt == 1
    assert second.next_cursor.time_server_s - first.next_cursor.time_server_s == 60
    assert first.wire_rows()[0]["bar"]["close"] == "2500.2000000000"
    assert first.wire_rows()[0]["available_at"] == setup_chart[0].utc.isoformat(
        timespec="microseconds"
    )
    assert (
        first.wire_rows()[0]["bar"]["first_received_at"]
        != first.wire_rows()[0]["bar"]["open_time_utc"]
    )
    assert reader.read(second.next_cursor).rows == ()
    assert reader.read(second.next_cursor).next_cursor == second.next_cursor
    assert source(setup_chart, archive).read(limit=1) == first
    assert archive.path.read_bytes() == original
    assert reader.binding_json == archive._binding
    with reader._connect() as db, pytest.raises(sqlite3.OperationalError, match="readonly"):
        db.execute("INSERT INTO history_meta VALUES (2,'{}','invalid')")
    with pytest.raises(FrozenInstanceError):
        first.rows[0].payload = "changed"
    first.wire_rows()[0]["bar"]["close"] = "999"
    assert first.wire_rows()[0]["bar"]["close"] == "2500.2000000000"


def test_receipt_order_keeps_late_older_bars_and_filters_other_timeframes(setup_chart, archive):
    record_packet(setup_chart, archive, packet(setup_chart))
    reader = source(setup_chart, archive)
    first = reader.read()
    record_packet(setup_chart, archive, packet(setup_chart, "M5", sequence=2))
    data = packet(setup_chart, sequence=3)
    older = dict(data["bars"][0], time_server_s=data["bars"][0]["time_server_s"] - 180)
    data["bars"].insert(0, older)
    record_packet(setup_chart, archive, data)
    late = reader.read(first.next_cursor)
    assert len(late.rows) == 1 and late.next_cursor.receipt == 3
    assert late.next_cursor.time_server_s < first.next_cursor.time_server_s
    assert late.wire_rows()[0]["bar"]["time_server_s"] == older["time_server_s"]
    assert reader.read(late.next_cursor).rows == ()
    assert reader.read(limit=100).rows[:2] == first.rows


def test_wal_snapshot_sees_commits_not_uncommitted_rows(setup_chart, archive):
    attach(setup_chart, archive)
    accept(setup_chart)
    reader = source(setup_chart, archive)
    baseline = reader.read()
    with archive._connect() as writer:
        writer.execute("BEGIN IMMEDIATE")
        old = baseline.wire_rows()[0]["bar"]
        old["time_server_s"] -= 60
        old["open_time_utc"] = (
            archive.read("M1").bars[0].open_time_utc - timedelta(seconds=60)
        ).isoformat()
        old["first_receipt"] = 2
        payload = json.dumps(old)
        writer.execute(
            "INSERT INTO receipts VALUES (2,?,2,?,?)",
            (str(uuid4()), "a" * 64, old["first_received_at"]),
        )
        writer.execute(
            "INSERT INTO closed_bars VALUES ('M1',?,2,?,?)",
            (old["time_server_s"], payload, hashlib.sha256(payload.encode()).hexdigest()),
        )
        assert reader.read() == baseline
        writer.commit()
        assert archive.path.with_name("bars.sqlite3-wal").stat().st_size > 0
        assert reader.read(baseline.next_cursor).wire_rows()[0]["bar"] == old


def test_availability_is_observed_after_snapshot_and_writer_can_commit(setup_chart, archive):
    record_packet(setup_chart, archive, packet(setup_chart))
    clock = setup_chart[0]
    calls = 0

    def after_fetch():
        nonlocal calls
        calls += 1
        if calls == 1:
            clock.advance(60)
            record_packet(setup_chart, archive, packet(setup_chart, sequence=2))
        return clock.utc

    reader = source(setup_chart, archive, utc_now=after_fetch)
    first = reader.read()
    assert len(first.rows) == 2
    assert first.rows[0].available_at == clock.utc.isoformat(timespec="microseconds")
    next_batch = reader.read(first.next_cursor)
    assert len(next_batch.rows) == 1 and next_batch.next_cursor.receipt == 2


@pytest.mark.parametrize(
    "change",
    [
        {"archive_id": uuid4()},
        {"offset_seconds": 0},
        {"offset_seconds": True},
        {"offset_seconds": 61},
        {"offset_seconds": 50460},
    ],
)
def test_pinned_identity_denial(setup_chart, archive, change):
    with pytest.raises(SourceUnavailable, match=r"^NATIVE_SOURCE_UNAVAILABLE$"):
        source(setup_chart, archive, **change)


def test_empty_missing_and_unknown_cursor(setup_chart, archive, tmp_path):
    reader = source(setup_chart, archive)
    assert reader.read().rows == ()
    with pytest.raises(SourceUnavailable):
        reader.read(SourceCursor(1, 60))
    missing = tmp_path / "missing"
    missing.mkdir(mode=0o700)
    with pytest.raises(SourceUnavailable):
        source(setup_chart, archive, directory=missing)
    assert not (missing / "bars.sqlite3").exists()


@pytest.mark.parametrize("cursor", [(True, 60), (-1, 60), (1, 61), (0, 60), (1, 0), (2**53, 60)])
def test_cursor_input_validation(cursor):
    with pytest.raises(ValueError):
        SourceCursor(*cursor)


@pytest.mark.parametrize("limit", [0, 101, True, 1.5])
def test_read_bounds(setup_chart, archive, limit):
    with pytest.raises(SourceUnavailable):
        source(setup_chart, archive).read(limit=limit)


@pytest.mark.parametrize(
    "kind",
    [
        "schema",
        "binding",
        "archive",
        "trigger",
        "directory-mode",
        "file-mode",
        "symlink",
        "hardlink",
        "replacement",
    ],
)
def test_schema_and_files_fail_closed(setup_chart, archive, kind):
    reader = source(setup_chart, archive)
    if kind in {"schema", "binding", "archive", "trigger"}:
        with archive._connect() as db:
            if kind == "schema":
                db.execute("PRAGMA user_version=99")
            elif kind == "binding":
                db.execute("UPDATE history_meta SET binding='{}'")
            elif kind == "archive":
                db.execute("UPDATE history_meta SET archive_id=?", (str(uuid4()),))
            else:
                db.execute("DROP TRIGGER immutable_bars_delete")
    elif kind == "directory-mode":
        archive.directory.chmod(0o755)
    elif kind == "file-mode":
        archive.path.chmod(0o644)
    else:
        alternate = archive.directory / "alternate.sqlite3"
        if kind == "hardlink":
            os.link(archive.path, alternate)
        else:
            shutil.copy2(archive.path, alternate)
            archive.path.unlink()
            if kind == "symlink":
                archive.path.symlink_to(alternate)
            else:
                alternate.rename(archive.path)
    with pytest.raises(SourceUnavailable, match=r"^NATIVE_SOURCE_UNAVAILABLE$"):
        reader.read()


def tamper(archive, change, *, digest=True):
    with archive._connect() as db:
        row = db.execute(
            "SELECT rowid,payload FROM closed_bars ORDER BY time_server_s LIMIT 1"
        ).fetchone()
        payload = json.loads(row["payload"])
        payload.update(change)
        raw = json.dumps(payload)
        db.execute("DROP TRIGGER immutable_bars_update")
        db.execute(
            "UPDATE closed_bars SET payload=?,digest=? WHERE rowid=?",
            (raw, hashlib.sha256(raw.encode()).hexdigest() if digest else "0" * 64, row["rowid"]),
        )
        db.execute("""CREATE TRIGGER immutable_bars_update BEFORE UPDATE ON closed_bars
                      BEGIN SELECT RAISE(ABORT, 'immutable history'); END""")


@pytest.mark.parametrize(
    "change",
    [
        {"closed": False},
        {"closed": 1},
        {"time_server_s": 60},
        {"first_receipt": 99},
        {"terminal_build": 9_007_199_254_740_992},
        {"broker_utc_offset_seconds": 0},
        {"tick_size": "0.3"},
        {"digits": 0},
        {"open": "NaN"},
        {"open": 2500},
        {"confirmed_by_server_s": 60},
        {"source_observed_at": "2099-01-01T00:00:00Z"},
        {"first_received_at": "2000-01-01T00:00:00Z"},
        {"open_time_utc": "2026-09-16T24:00:00Z"},
        {"unexpected": "field"},
    ],
)
def test_semantic_corruption_even_with_recomputed_hash(setup_chart, archive, change):
    attach(setup_chart, archive)
    accept(setup_chart)
    reader = source(setup_chart, archive)
    tamper(archive, change)
    with pytest.raises(SourceUnavailable, match=r"^NATIVE_SOURCE_UNAVAILABLE$"):
        reader.read()


def test_digest_and_clock_rollback_deny_export(setup_chart, archive):
    attach(setup_chart, archive)
    accept(setup_chart)
    reader = source(setup_chart, archive)
    setup_chart[0].advance(-1)
    with pytest.raises(SourceUnavailable):
        reader.read()
    setup_chart[0].advance(1)
    tamper(archive, {}, digest=False)
    with pytest.raises(SourceUnavailable):
        reader.read()


def test_bounded_batch_size_does_not_advance_past_omitted_rows(setup_chart, archive, monkeypatch):
    attach(setup_chart, archive)
    accept(setup_chart)
    reader = source(setup_chart, archive)
    normal = reader.read()
    first_size = len(json.dumps(normal.wire_rows()[:1]).encode())
    monkeypatch.setattr(native_source, "MAX_BATCH_BYTES", first_size + 2)
    first = reader.read()
    assert len(first.rows) == 1 and first.next_cursor == normal.rows[0].cursor
    assert reader.read(first.next_cursor).rows == normal.rows[1:]


def test_sql_progress_deadline(setup_chart, archive, monkeypatch):
    reader = source(setup_chart, archive)
    monkeypatch.setattr(native_source, "QUERY_SECONDS", 0)
    with pytest.raises(sqlite3.OperationalError, match="interrupted"), reader._connect() as db:
        db.execute("""WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<100000)
                      SELECT sum(x) FROM n""").fetchone()


@pytest.mark.parametrize("mode", ["duplicate-key", "oversized", "nonfinite", "blob"])
def test_bad_raw_json_is_redacted(setup_chart, archive, mode):
    attach(setup_chart, archive)
    accept(setup_chart)
    reader = source(setup_chart, archive)
    with archive._connect() as db:
        row = db.execute("SELECT rowid,payload FROM closed_bars LIMIT 1").fetchone()
        raw = row["payload"]
        if mode == "duplicate-key":
            raw = raw[:-1] + ',"closed":true}'
        elif mode == "oversized":
            raw += " " * 8193
        elif mode == "nonfinite":
            raw = raw[:-1] + ',"unexpected":NaN}'
        else:
            raw = raw.encode()
        digest = hashlib.sha256(raw.encode() if isinstance(raw, str) else raw).hexdigest()
        db.execute("DROP TRIGGER immutable_bars_update")
        db.execute("UPDATE closed_bars SET payload=?,digest=? WHERE rowid=?", (raw, digest, row[0]))
        db.execute("""CREATE TRIGGER immutable_bars_update BEFORE UPDATE ON closed_bars
                      BEGIN SELECT RAISE(ABORT, 'immutable history'); END""")
    with pytest.raises(SourceUnavailable, match=r"^NATIVE_SOURCE_UNAVAILABLE$"):
        reader.read()


def test_unknown_columns_and_replaced_trigger_are_not_accepted(setup_chart, archive):
    reader = source(setup_chart, archive)
    with archive._connect() as db:
        db.execute("DROP TRIGGER immutable_bars_update")
        db.execute("""CREATE TRIGGER immutable_bars_update BEFORE UPDATE ON closed_bars
                      BEGIN SELECT 1; END""")
    with pytest.raises(SourceUnavailable):
        reader.read()
    with archive._connect() as db:
        db.execute("ALTER TABLE history_meta ADD COLUMN unexpected TEXT")
    with pytest.raises(SourceUnavailable):
        source(setup_chart, archive)


def test_sidecar_permissions_and_directory_swap(setup_chart, archive):
    reader = source(setup_chart, archive)
    with archive._connect():
        wal = archive.path.with_name("bars.sqlite3-wal")
        wal.chmod(0o644)
        with pytest.raises(SourceUnavailable):
            reader.read()
        wal.chmod(0o600)
    saved = archive.directory.with_name(archive.directory.name + "-old")
    archive.directory.rename(saved)
    archive.directory.mkdir(mode=0o700)
    shutil.copy2(saved / "bars.sqlite3", archive.path)
    with pytest.raises(SourceUnavailable):
        reader.read()


def test_high_precision_and_naive_clock(setup_chart, archive):
    data = packet(setup_chart)
    data.update(digits=10, tick_size="1E-10")
    quote = copy.deepcopy(setup_chart[3])
    quote["sequence"] = 2
    quote["contract"].update(digits=10, tick_size="1E-10")
    setup_chart[1].accept(TelemetryFrame.model_validate(quote))
    maximum = "99999999999999.9999999999"
    for bar in data["bars"]:
        bar.update(dict.fromkeys(("open", "high", "low", "close"), maximum))
    record_packet(setup_chart, archive, data)
    exported = source(setup_chart, archive).read()
    assert exported.wire_rows()[0]["bar"]["open"] == maximum
    assert exported.wire_rows()[0]["bar"]["tick_size"] == "1E-10"
    with pytest.raises(SourceUnavailable):
        source(setup_chart, archive, utc_now=lambda: setup_chart[0].utc.replace(tzinfo=None)).read()
