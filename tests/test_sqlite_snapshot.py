import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from decimal import Decimal
from pathlib import Path

import pytest
from sochron1k import sqlite_snapshot as snapshot
from sochron1k.journal import Journal
from sochron1k.models import CommandState, RiskState


@pytest.fixture
def private(tmp_path):
    directory = tmp_path.resolve()
    directory.chmod(0o700)
    return directory


@pytest.fixture
def database(private):
    path = private / "source.sqlite3"
    path.touch(mode=0o600)
    with closing(sqlite3.connect(path, isolation_level=None)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA wal_autocheckpoint=0")
        db.execute("CREATE TABLE records(id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO records VALUES (1,'committed')")
        yield path, db


def rows(directory):
    with closing(sqlite3.connect(directory / "snapshot.sqlite3")) as db:
        return db.execute("SELECT * FROM records ORDER BY id").fetchall()


def test_wal_committed_not_uncommitted_and_isolated_copy(private, database):
    source, writer = database
    assert (private / "source.sqlite3-wal").stat().st_size > 0
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO records VALUES (2,'uncommitted')")
    output = private / "backup"
    manifest = snapshot.create_snapshot(source, output)
    assert rows(output) == [(1, "committed")]
    assert snapshot.verify_snapshot(output) == manifest
    assert not manifest["execution_ready"]
    assert str(source) not in json.dumps(manifest)
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in output.iterdir())
    assert output.stat().st_mode & 0o777 == 0o700
    restored = private / "inspection"
    copy = snapshot.materialize_snapshot(output, restored)
    assert copy["parent_database_sha256"] == manifest["database_sha256"]
    assert copy["database_sha256"] == manifest["database_sha256"]
    assert copy["started_at"] == manifest["started_at"]
    assert rows(restored) == [(1, "committed")]
    assert snapshot.verify_snapshot(restored) == copy
    writer.rollback()


def test_snapshot_stable_during_other_connection_commit(private, database, monkeypatch):
    source, writer = database
    writer.executemany("INSERT INTO records VALUES (?,?)", [(i, "x" * 4096) for i in range(2, 600)])
    original = snapshot._source
    calls = 0

    def while_copying(path):
        nonlocal calls
        calls += 1
        if calls == 2:
            writer.execute("INSERT INTO records VALUES (1000,'later commit')")
        return original(path)

    monkeypatch.setattr(snapshot, "_source", while_copying)
    output = private / "backup"
    snapshot.create_snapshot(source, output)
    assert len(rows(output)) == 599
    assert writer.execute("SELECT count(*) FROM records").fetchone()[0] == 600


@pytest.mark.parametrize(
    "change", ["file-mode", "directory-mode", "symlink", "hardlink", "missing"]
)
def test_unsafe_sources_never_create_backup(private, database, change):
    source, _ = database
    if change == "file-mode":
        source.chmod(0o644)
    elif change == "directory-mode":
        private.chmod(0o755)
    elif change == "symlink":
        link = private / "link"
        link.symlink_to(source)
        source = link
    elif change == "hardlink":
        os.link(source, private / "linked")
    else:
        source = private / "missing"
    output = private / "backup"
    with pytest.raises(snapshot.SnapshotUnavailable, match=r"^SQLITE_SNAPSHOT_UNAVAILABLE$"):
        snapshot.create_snapshot(source, output)
    assert not output.exists()


def test_existing_target_untouched(private, database):
    output = private / "existing"
    output.mkdir(mode=0o700)
    marker = output / "owner-data"
    marker.write_text("preserve")
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.create_snapshot(database[0], output)
    assert marker.read_text() == "preserve"
    assert list(output.iterdir()) == [marker]


@pytest.mark.parametrize("failure", ["size", "deadline", "fsync", "corrupt"])
def test_failed_snapshot_not_verifiable(private, database, monkeypatch, failure):
    source, writer = database
    if failure == "size":
        monkeypatch.setattr(snapshot, "MAX_BYTES", 1024)
    elif failure == "deadline":
        monkeypatch.setattr(snapshot, "DEADLINE_SECONDS", -1)
    elif failure == "fsync":
        monkeypatch.setattr(snapshot, "_sync", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    else:
        writer.close()
        source.write_bytes(b"invalid SQLite")
    output = private / "failed"
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.create_snapshot(source, output)
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.verify_snapshot(output)


@pytest.mark.parametrize(
    "tamper", ["database", "manifest", "extra", "mode", "hardlink", "duplicate"]
)
def test_tampered_snapshot_never_materialized(private, database, tamper):
    output = private / "backup"
    snapshot.create_snapshot(database[0], output)
    if tamper == "database":
        with closing(sqlite3.connect(output / "snapshot.sqlite3")) as db:
            db.execute("INSERT INTO records VALUES (7,'tampered')")
            db.commit()
    elif tamper == "manifest":
        (output / "manifest.json").write_text("{}")
    elif tamper == "extra":
        (output / "unexpected").touch()
    elif tamper == "mode":
        (output / "manifest.json").chmod(0o644)
    elif tamper == "hardlink":
        os.link(output / "snapshot.sqlite3", private / "linked-backup")
    else:
        path = output / "manifest.json"
        path.write_text(
            path.read_text().replace(
                '"execution_ready": false', '"execution_ready": false, "execution_ready": false'
            )
        )
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.materialize_snapshot(output, private / "inspection")
    assert not (private / "inspection").exists()


def test_materialization_inside_source_or_existing_target_never_mutates(private, database):
    output = private / "backup"
    original = snapshot.create_snapshot(database[0], output)
    for target in (output, output / "child"):
        with pytest.raises(snapshot.SnapshotUnavailable):
            snapshot.materialize_snapshot(output, target)
        assert snapshot.verify_snapshot(output) == original
    existing = private / "existing"
    existing.mkdir(mode=0o700)
    (existing / "owner-file").write_text("keep")
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.materialize_snapshot(output, existing)
    assert [p.name for p in existing.iterdir()] == ["owner-file"]


def test_command_unknown_and_total_halt_preserved(private, intent, observed_at):
    path = private / "commands.sqlite3"
    path.touch(mode=0o600)
    journal = Journal(path)
    journal.reserve(intent, Decimal("0.1"), Decimal("100"))
    journal.begin_dispatch(
        intent.command_id, "attempt-fixture", Decimal("1000"), Decimal("0")
    )
    journal.transition(intent.command_id, CommandState.UNKNOWN)
    state = RiskState(
        account_ref=intent.account_ref,
        experiment_id=intent.experiment_id,
        bangkok_day="2026-09-17",
        daily_baseline=Decimal("100000"),
        experiment_baseline=Decimal("100000"),
        daily_halt=True,
        total_halt=True,
        updated_at=observed_at,
    )
    journal.save_risk_state(state)
    for file in private.iterdir():
        file.chmod(0o600)
    snapshot.create_snapshot(path, private / "backup")
    snapshot.materialize_snapshot(private / "backup", private / "inspection")
    with closing(sqlite3.connect(private / "inspection/snapshot.sqlite3")) as db:
        assert db.execute("SELECT state FROM commands").fetchone() == (CommandState.UNKNOWN.value,)
        assert db.execute("SELECT count(*) FROM dispatch_attempts").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM exposure_slots").fetchone()[0] == 1
        assert db.execute(
            "SELECT daily_baseline,experiment_baseline,daily_halt,total_halt FROM risk_state"
        ).fetchone() == ("100000", "100000", 1, 1)


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration_seconds", float("nan")),
        ("duration_seconds", -1),
        ("started_at", "2026-01-01"),
        ("database_bytes", True),
        ("schema_sha256", "invalid"),
        ("parent_database_sha256", "invalid"),
        ("sqlite_version", "unknown"),
        ("completed_at", "2000-01-01T00:00:00+00:00"),
    ],
)
def test_invalid_metadata_denied(private, database, field, value):
    output = private / "backup"
    metadata = snapshot.create_snapshot(database[0], output)
    metadata[field] = value
    (output / "manifest.json").write_text(json.dumps(metadata))
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.verify_snapshot(output)


def test_failed_final_directory_sync_marks_output_incomplete(private, database, monkeypatch):
    original = snapshot._sync

    def fail_directory(path, *, directory=False):
        if directory:
            raise OSError("simulated storage failure")
        return original(path)

    monkeypatch.setattr(snapshot, "_sync", fail_directory)
    output = private / "backup"
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.create_snapshot(database[0], output)
    assert (output / "INCOMPLETE").exists()
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.verify_snapshot(output)


def test_foreign_key_violation_rejected(private, database):
    source, writer = database
    writer.execute("CREATE TABLE invalid(parent INTEGER REFERENCES records(id))")
    writer.execute("INSERT INTO invalid VALUES (99)")
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.create_snapshot(source, private / "backup")
    assert not (private / "backup/manifest.json").exists()


def test_process_exit_before_publication_is_not_backup(private, database):
    code = """
import os, sys
from pathlib import Path
from sochron1k import sqlite_snapshot as s
original = s._new_file
def interrupt(path, data=b""):
    if path.name == "manifest.json":
        os._exit(73)
    return original(path, data)
s._new_file = interrupt
s.create_snapshot(Path(sys.argv[1]), Path(sys.argv[2]))
"""
    output = private / "interrupted"
    env = {**os.environ, "PYTHONPATH": str(Path("services/api/src").resolve())}
    result = subprocess.run(
        [sys.executable, "-c", code, str(database[0]), str(output)],
        env=env,
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 73 and not result.stderr
    assert (output / "snapshot.sqlite3").exists()
    assert not (output / "manifest.json").exists()
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.verify_snapshot(output)
