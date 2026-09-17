from __future__ import annotations

import copy
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sochron_worker import sync_journal
from sochron_worker.native_source import SourceUnavailable
from sochron_worker.sync_driver import DestinationConflict, DestinationUnavailable, SyncDriver
from sochron_worker.sync_journal import JournalUnavailable, SyncJournal
from test_bar_history import accept, attach
from test_bar_history import archive as archive
from test_chart import packet
from test_chart import setup_chart as setup_chart
from test_native_source import record_packet, source, tamper

OWNER = UUID("10000000-0000-0000-0000-000000000001")
ORIGIN = "http://127.0.0.1:54321"


class FakeDestination:
    owner_id = str(OWNER)
    origin = ORIGIN

    def __init__(self):
        self.calls = []
        self.snapshot = None
        self.lose = False
        self.read_fail = False
        self.write_conflict = False
        self.ack_without_write = False
        self.on_store = lambda batch: None

    def store(self, batch):
        self.calls.append("store")
        self.on_store(batch)
        if self.write_conflict:
            raise DestinationConflict()
        if not self.ack_without_write:
            self.snapshot = {
                "archive_id": batch.archive_id,
                "binding": json.loads(batch.binding_json),
                "rows": batch.wire_rows(),
            }
        if self.lose:
            raise DestinationUnavailable()

    def read(self, batch):
        self.calls.append("read")
        if self.read_fail:
            raise DestinationUnavailable()
        return (
            copy.deepcopy(self.snapshot)
            if self.snapshot is not None
            else {"archive_id": batch.archive_id, "binding": None, "rows": []}
        )


@pytest.fixture
def journal(setup_chart, archive, tmp_path):
    attach(setup_chart, archive)
    accept(setup_chart)
    directory = tmp_path / "worker"
    directory.mkdir(mode=0o700)
    with SyncJournal(
        directory,
        source(setup_chart, archive),
        OWNER,
        ORIGIN,
        create=True,
        utc_now=setup_chart[0].now,
    ) as result:
        yield result


def reopen(journal, setup_chart, **changes):
    args = dict(
        directory=journal.directory,
        source=journal.source,
        owner_id=OWNER,
        destination=ORIGIN,
        utc_now=setup_chart[0].now,
    )
    args.update(changes)
    journal.close()
    return SyncJournal(**args)


def test_intent_before_send_independent_readback_and_reopen(journal, setup_chart):
    destination = FakeDestination()

    def inspect(batch):
        with sqlite3.connect(journal.path) as db:
            state, attempts, payload = db.execute(
                "SELECT state,attempts,payload FROM batches"
            ).fetchone()
            assert state == "UNKNOWN" and attempts == 1
            assert json.loads(payload)["rows"][0]["payload"] == batch.rows[0].payload
            assert db.execute("SELECT receipt FROM meta").fetchone()[0] == 0

    destination.on_store = inspect
    assert SyncDriver(journal, destination).step() == "VERIFIED"
    assert destination.calls == ["store", "read"]
    state = journal.status()
    assert state.cursor.receipt == 1 and state.pending is None
    with journal._connect() as db:
        assert db.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            db.execute("UPDATE batches SET payload='{}'")
        with pytest.raises(sqlite3.IntegrityError, match="retained"):
            db.execute("DELETE FROM batches")
    with reopen(journal, setup_chart) as restarted:
        assert restarted.status().cursor == state.cursor
        assert SyncDriver(restarted, destination).step() == "IDLE"
    assert destination.calls == ["store", "read"]


def test_ack_without_rows_never_advances(journal):
    destination = FakeDestination()
    destination.ack_without_write = True
    assert SyncDriver(journal, destination).step() == "PREPARED"
    assert journal.status().cursor.receipt == 0
    assert journal.status().pending.attempts == 1


def test_lost_response_reconciles_without_second_send_after_restart(journal, setup_chart):
    destination = FakeDestination()
    destination.lose = True
    assert SyncDriver(journal, destination).step() == "UNKNOWN"
    assert destination.calls == ["store"]
    original = journal.status().pending
    setup_chart[0].advance(1)
    with reopen(journal, setup_chart) as restarted:
        assert restarted.status().pending == original
        assert SyncDriver(restarted, destination).step() == "VERIFIED"
    assert destination.calls == ["store", "read"]


def test_unknown_read_failure_stays_unknown_then_missing_allows_later_retry(journal):
    destination = FakeDestination()
    destination.lose = destination.ack_without_write = True
    driver = SyncDriver(journal, destination)
    assert driver.step() == "UNKNOWN"
    destination.read_fail = True
    assert driver.step() == "UNKNOWN"
    assert destination.calls == ["store", "read"]
    destination.read_fail = False
    assert driver.step() == "PREPARED"
    assert destination.calls == ["store", "read", "read"]
    destination.lose = destination.ack_without_write = False
    assert driver.step() == "VERIFIED"
    assert destination.calls == ["store", "read", "read", "store", "read"]


@pytest.mark.parametrize(
    "mode",
    ["binding", "payload", "duplicate", "foreign-row", "future", "early", "archive", "shape"],
)
def test_conflicts_quarantine_persistently(journal, setup_chart, mode):
    destination = FakeDestination()
    destination.lose = True
    driver = SyncDriver(journal, destination)
    assert driver.step() == "UNKNOWN"
    snapshot = destination.snapshot
    if mode == "binding":
        snapshot["binding"]["identity"]["server"] = "Changed-Demo"
    elif mode == "payload":
        snapshot["rows"][0]["bar"]["close"] = "2500.3"
    elif mode == "duplicate":
        snapshot["rows"][1] = snapshot["rows"][0]
    elif mode == "foreign-row":
        snapshot["rows"][0]["bar"]["time_server_s"] = 60
    elif mode in {"future", "early"}:
        snapshot["rows"][0]["available_at"] = (
            "2099-01-01T00:00:00Z" if mode == "future" else "2000-01-01T00:00:00Z"
        )
    elif mode == "archive":
        snapshot["archive_id"] = str(uuid4())
    else:
        snapshot["extra"] = "not allowed"
    assert driver.step() == "QUARANTINED"
    with reopen(journal, setup_chart) as restarted:
        calls = destination.calls[:]
        assert SyncDriver(restarted, destination).step() == "QUARANTINED"
        assert destination.calls == calls and restarted.status().cursor.receipt == 0


def test_partial_readback_requires_retry_without_advancing(journal):
    destination = FakeDestination()
    destination.lose = True
    driver = SyncDriver(journal, destination)
    assert driver.step() == "UNKNOWN"
    destination.snapshot["rows"].pop()
    assert driver.step() == "PREPARED"
    assert journal.status().cursor.receipt == 0
    destination.lose = False
    assert driver.step() == "VERIFIED"


def test_repeated_prepare_and_denied_transitions(journal):
    batch = journal.source.read()
    pending = journal.prepare(batch)
    assert journal.prepare(batch) == pending
    with pytest.raises(JournalUnavailable):
        journal.prepare(replace(batch, archive_id=str(uuid4())))
    with pytest.raises(JournalUnavailable):
        journal.reconcile(pending.batch_id, {})
    journal.begin_send(pending.batch_id)
    with pytest.raises(JournalUnavailable):
        journal.begin_send(pending.batch_id)
    journal.quarantine(pending.batch_id)
    with pytest.raises(JournalUnavailable):
        journal.begin_send(pending.batch_id)


def deny_write(journal, monkeypatch, operation, table, column=None):
    connect = journal._connect

    @contextmanager
    def connection():
        with connect() as db:
            db.set_authorizer(
                lambda action, name, field, *_: (
                    sqlite3.SQLITE_DENY
                    if action == operation and name == table and (column is None or field == column)
                    else sqlite3.SQLITE_OK
                )
            )
            yield db

    monkeypatch.setattr(journal, "_connect", connection)


def test_storage_failure_prevents_dispatch(journal, monkeypatch):
    destination = FakeDestination()
    deny_write(journal, monkeypatch, sqlite3.SQLITE_INSERT, "batches")
    with pytest.raises(JournalUnavailable):
        SyncDriver(journal, destination).step()
    assert destination.calls == [] and journal.status().pending is None


def test_unknown_marker_failure_prevents_send(journal, monkeypatch):
    pending = journal.prepare(journal.source.read())
    deny_write(journal, monkeypatch, sqlite3.SQLITE_UPDATE, "batches", "state")
    destination = FakeDestination()
    with pytest.raises(JournalUnavailable):
        SyncDriver(journal, destination).step()
    assert destination.calls == [] and journal.status().pending == pending


def test_single_writer_missing_state_config_and_clock_denied(journal, setup_chart):
    with pytest.raises(JournalUnavailable):
        SyncJournal(journal.directory, journal.source, OWNER, ORIGIN, utc_now=setup_chart[0].now)
    with pytest.raises(JournalUnavailable):
        reopen(journal, setup_chart, owner_id=uuid4())
    with reopen(journal, setup_chart) as restarted:
        setup_chart[0].advance(-1)
        with pytest.raises(JournalUnavailable):
            SyncDriver(restarted, FakeDestination()).step()
    setup_chart[0].advance(1)
    journal.path.unlink()
    with pytest.raises(JournalUnavailable):
        reopen(journal, setup_chart)
    assert not journal.path.exists()


def test_changed_destination_never_called(journal):
    destination = FakeDestination()
    destination.origin = "https://different.example.test"
    with pytest.raises(JournalUnavailable):
        SyncDriver(journal, destination).step()
    assert destination.calls == []


@pytest.mark.parametrize("mutation", ["trigger", "column", "index", "clock", "cursor"])
def test_invalid_schema_and_metadata_denied_on_reopen(journal, setup_chart, mutation):
    assert SyncDriver(journal, FakeDestination()).step() == "VERIFIED"
    with journal._connect() as db:
        if mutation == "trigger":
            db.execute("DROP TRIGGER immutable_batch")
        elif mutation == "column":
            db.execute("ALTER TABLE meta ADD COLUMN unexpected TEXT")
        elif mutation == "index":
            db.execute("DROP INDEX one_pending")
        elif mutation == "clock":
            db.execute("UPDATE meta SET last_clock='2000-01-01T00:00:00Z'")
        else:
            db.execute("UPDATE meta SET receipt=0,time_server_s=0")
    with (
        pytest.raises(JournalUnavailable, match=r"^SYNC_JOURNAL_UNAVAILABLE$"),
        reopen(journal, setup_chart),
    ):
        pytest.fail("corrupt journal accepted")


def test_shared_journal_serializes_drivers_during_send(journal):
    destination = FakeDestination()
    other = FakeDestination()

    def nested_step(batch):
        with pytest.raises(JournalUnavailable):
            SyncDriver(journal, other).step()

    destination.on_store = nested_step
    assert SyncDriver(journal, destination).step() == "VERIFIED"
    assert other.calls == []


# Separate interpreter and separate durable destination; no shared Python effects.
CRASH_CHILD = """
import json, os, sqlite3, sys
from datetime import datetime
from pathlib import Path
from uuid import UUID
from sochron1k.chart import ChartSettings
from sochron1k.telemetry import DemoIdentity
from sochron_worker.native_source import NativeArchiveSource
from sochron_worker.sync_journal import SyncJournal, JournalUnavailable
from sochron_worker.sync_driver import SyncDriver
c = json.load(sys.stdin)
b = json.loads(c['binding'])
clock = lambda: datetime.fromisoformat(c['now'])
source = NativeArchiveSource(Path(c['source']), UUID(c['archive']),
    DemoIdentity.model_validate(b['identity']), b['offset'],
    ChartSettings.model_validate(b['chart']), utc_now=clock)
try:
    journal = SyncJournal(Path(c['journal']), source, UUID(c['owner']),
        c['origin'], utc_now=clock)
except JournalUnavailable:
    sys.exit(74)
class Target:
    owner_id, origin = c['owner'], c['origin']
    def store(self, batch):
        snapshot = dict(archive_id=batch.archive_id,
            binding=json.loads(batch.binding_json), rows=batch.wire_rows())
        with sqlite3.connect(c['target']) as db:
            db.execute('INSERT INTO effects VALUES (?)', (json.dumps(snapshot),))
        os._exit(73)
    def read(self, batch):
        raise AssertionError('must crash before read-back')
SyncDriver(journal, Target()).step()
raise AssertionError('child did not crash')
"""


def run_child(journal, setup_chart, target):
    config = dict(
        binding=journal.source.binding_json,
        source=str(journal.source.directory),
        archive=journal.source.archive_id,
        journal=str(journal.directory),
        owner=str(OWNER),
        origin=ORIGIN,
        now=setup_chart[0].now().isoformat(),
        target=str(target),
    )
    return subprocess.run(
        [sys.executable, "-c", CRASH_CHILD],
        input=json.dumps(config),
        text=True,
        capture_output=True,
        timeout=10,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                str(Path(p).resolve()) for p in ("services/api/src", "services/worker/src")
            ),
        },
    )


def test_process_exit_after_acceptance_and_independent_writer_lock(journal, setup_chart, tmp_path):
    target = tmp_path / "synthetic-destination.sqlite3"
    with sqlite3.connect(target) as db:
        db.execute("CREATE TABLE effects(snapshot TEXT NOT NULL)")
    # A live independent process cannot acquire this held journal.
    denied = run_child(journal, setup_chart, target)
    assert denied.returncode == 74, denied.stderr
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT count(*) FROM effects").fetchone()[0] == 0
    journal.close()
    crashed = run_child(journal, setup_chart, target)
    assert crashed.returncode == 73, crashed.stderr
    with sqlite3.connect(target) as db:
        rows = db.execute("SELECT snapshot FROM effects").fetchall()
    assert len(rows) == 1

    class ReadOnlyRecovery(FakeDestination):
        def store(self, batch):
            pytest.fail("restart repeated an already accepted write")

        def read(self, batch):
            self.calls.append("read")
            with sqlite3.connect(target) as db:
                return json.loads(db.execute("SELECT snapshot FROM effects").fetchone()[0])

    destination = ReadOnlyRecovery()
    with reopen(journal, setup_chart) as restarted:
        pending = restarted.status().pending
        assert pending.state == "UNKNOWN" and pending.attempts == 1
        assert restarted.status().cursor.receipt == 0
        assert SyncDriver(restarted, destination).step() == "VERIFIED"
        assert restarted.status().cursor == pending.batch.next_cursor
    assert destination.calls == ["read"]
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT count(*) FROM effects").fetchone()[0] == 1


def test_cursor_write_failure_rolls_back_verified_state(journal, setup_chart, monkeypatch):
    destination = FakeDestination()
    destination.lose = True
    assert SyncDriver(journal, destination).step() == "UNKNOWN"
    pending = journal.status().pending
    # Deny the second write in the VERIFIED+cursor transaction after batches UPDATE.
    with monkeypatch.context() as patch:
        deny_write(journal, patch, sqlite3.SQLITE_UPDATE, "meta", "receipt")
        with pytest.raises(JournalUnavailable):
            SyncDriver(journal, destination).step()
        assert journal.status().pending == pending
        assert journal.status().cursor.receipt == 0
    with reopen(journal, setup_chart) as restarted:
        assert SyncDriver(restarted, destination).step() == "VERIFIED"
    assert destination.calls == ["store", "read", "read"]


def test_valid_different_destination_availability_is_preserved(journal, setup_chart):
    destination = FakeDestination()
    destination.lose = True
    assert SyncDriver(journal, destination).step() == "UNKNOWN"
    setup_chart[0].advance(1)
    for row in destination.snapshot["rows"]:
        row["available_at"] = setup_chart[0].now().isoformat()
    assert SyncDriver(journal, destination).step() == "VERIFIED"
    assert destination.calls == ["store", "read"]


@pytest.mark.parametrize("mode", ["permission", "hardlink", "source", "lock", "schema"])
def test_unsafe_state_prevents_external_effect(journal, archive, mode):
    pending = journal.prepare(journal.source.read())
    if mode == "permission":
        journal.path.chmod(0o644)
    elif mode == "hardlink":
        os.link(journal.path, journal.directory / "duplicate")
    elif mode == "source":
        archive.path.chmod(0o644)
    elif mode == "lock":
        (journal.directory / "sync.lock").unlink()
    else:
        with journal._connect() as db:
            db.execute("DROP TRIGGER retain_batch")
    destination = FakeDestination()
    with pytest.raises((JournalUnavailable, SourceUnavailable)):
        SyncDriver(journal, destination).step()
    assert destination.calls == []
    with sqlite3.connect(journal.path) as db:
        assert db.execute("SELECT batch_id,state FROM batches").fetchone() == (
            pending.batch_id,
            "PREPARED",
        )


def test_changed_but_valid_source_quarantines_pending(journal, archive):
    journal.prepare(journal.source.read())
    tamper(archive, {"close": "2500.3000000000"})
    destination = FakeDestination()
    assert SyncDriver(journal, destination).step() == "QUARANTINED"
    assert destination.calls == []


def test_sqlite_quota_failure_prevents_send(journal, monkeypatch):
    with journal._connect() as db:
        pages = db.execute("PRAGMA page_count").fetchone()[0]
        size = db.execute("PRAGMA page_size").fetchone()[0]
    # Real SQLite page quota exhaustion, not an exception raised by a fake writer.
    monkeypatch.setattr(sync_journal, "MAX_JOURNAL_BYTES", pages * size)
    batch = journal.source.read()
    large_rows = tuple(replace(row, payload=row.payload + " " * 7000) for row in batch.rows)
    sync_journal.decode_batch(
        sync_journal.canonical(sync_journal.asdict(replace(batch, rows=large_rows)))
    )
    with pytest.raises(JournalUnavailable) as failure:
        journal.prepare(replace(batch, rows=large_rows))
    assert failure.value.__context__.sqlite_errorcode == sqlite3.SQLITE_FULL
    assert journal.status().pending is None and journal.status().cursor.receipt == 0
    destination = FakeDestination()
    # A denied journal lock also prevents any external send.
    with sqlite3.connect(journal.path) as writer:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(JournalUnavailable):
            SyncDriver(journal, destination).step()
    assert destination.calls == []


@pytest.mark.parametrize("mode", ["digest", "state", "attempts", "future", "sequence"])
def test_corrupt_batch_ledger_denied(journal, setup_chart, mode):
    assert SyncDriver(journal, FakeDestination()).step() == "VERIFIED"
    with journal._connect() as db:
        if mode == "digest":
            ddl = db.execute(
                "SELECT sql FROM sqlite_schema WHERE name='immutable_batch'"
            ).fetchone()[0]
            db.execute("DROP TRIGGER immutable_batch")
            db.execute("UPDATE batches SET digest=?", ("0" * 64,))
            # Restore the exact DDL so only the fingerprint, not schema check, catches it.
            db.execute(ddl)
        elif mode == "state":
            db.execute("UPDATE batches SET state='PREPARED'")
        elif mode == "attempts":
            db.execute("UPDATE batches SET attempts=0")
        elif mode == "future":
            db.execute("UPDATE batches SET updated_at='2099-01-01T00:00:00Z'")
        else:
            db.execute("UPDATE batches SET seq=-1")
    with pytest.raises(JournalUnavailable), reopen(journal, setup_chart):
        pytest.fail("corrupt batch accepted")


def test_later_backfill_is_synced_and_full_ledger_audited(journal, setup_chart, archive):
    destination = FakeDestination()
    assert SyncDriver(journal, destination).step() == "VERIFIED"
    first = journal.status().cursor
    data = packet(setup_chart, sequence=2)
    older = dict(data["bars"][0], time_server_s=data["bars"][0]["time_server_s"] - 180)
    data["bars"].insert(0, older)
    record_packet(setup_chart, archive, data)
    assert SyncDriver(journal, destination).step() == "VERIFIED"
    second = journal.status().cursor
    assert second.receipt > first.receipt and second.time_server_s < first.time_server_s
    assert len(destination.snapshot["rows"]) == 1
    with reopen(journal, setup_chart) as restarted:
        assert restarted.status().cursor == second
        assert SyncDriver(restarted, destination).step() == "IDLE"
        with restarted._connect() as db:
            assert db.execute("SELECT count(*) FROM batches").fetchone()[0] == 2
            db.execute("UPDATE batches SET updated_at='2099-01-01T00:00:00Z' WHERE seq=1")
    with pytest.raises(JournalUnavailable), reopen(journal, setup_chart):
        pytest.fail("older corrupted ledger row ignored")


def test_explicit_initialize_never_resets_existing_or_partial_state(journal, setup_chart, tmp_path):
    journal.prepare(journal.source.read())
    with pytest.raises(JournalUnavailable):
        reopen(journal, setup_chart, create=True)
    with reopen(journal, setup_chart) as original:
        assert original.status().pending.state == "PREPARED"
    directory = tmp_path / "partial-worker"
    directory.mkdir(mode=0o700)
    with pytest.raises(JournalUnavailable):
        SyncJournal(directory, journal.source, OWNER, ORIGIN)
    assert list(directory.iterdir()) == []
    (directory / "sync.lock").touch(mode=0o600)
    with pytest.raises(JournalUnavailable):
        SyncJournal(directory, journal.source, OWNER, ORIGIN, create=True)
    assert not (directory / "sync.sqlite3").exists()


@pytest.mark.parametrize("phase", ["store", "read"])
def test_destination_conflict_is_terminal_without_another_write(journal, phase):
    class ConflictTarget(FakeDestination):
        def read(self, batch):
            self.calls.append("read")
            raise DestinationConflict()

    destination = ConflictTarget()
    destination.write_conflict = phase == "store"
    driver = SyncDriver(journal, destination)
    assert driver.step() == "QUARANTINED"
    previous = destination.calls[:]
    assert driver.step() == "QUARANTINED"
    assert destination.calls == previous and previous.count("store") == 1


@pytest.mark.parametrize(
    "state,divisor", [("normal", 0.5), ("warning_70", 0.75), ("warning_85", 0.9)]
)
def test_journal_storage_warnings(journal, monkeypatch, state, divisor):
    used = journal.status().database_bytes
    # Keep page quota an integer number of pages while testing both warning thresholds.
    monkeypatch.setattr(sync_journal, "MAX_JOURNAL_BYTES", int(used / divisor))
    assert journal.status().storage == state
