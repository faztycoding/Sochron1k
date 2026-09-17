"""Private, single-writer synchronization journal. No broker or network authority."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from uuid import UUID, uuid4

from sochron1k.bar_history import ArchivedBar

from .native_source import (
    MAX_BATCH_BYTES,
    MAX_ROWS,
    UTC_TEXT,
    ExportBatch,
    ExportRow,
    NativeArchiveSource,
    SourceCursor,
    _json,
)

MAX_JOURNAL_BYTES = 64 * 1024 * 1024
MAX_INTENT_BYTES = 1_048_576
STATES = {"PREPARED", "UNKNOWN", "VERIFIED", "QUARANTINED"}
SCHEMA = """
CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),binding TEXT NOT NULL,
  receipt INTEGER NOT NULL,time_server_s INTEGER NOT NULL,last_clock TEXT NOT NULL);
CREATE TABLE batches(seq INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id TEXT NOT NULL UNIQUE,payload TEXT NOT NULL,digest TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('PREPARED','UNKNOWN','VERIFIED','QUARANTINED')),
  attempts INTEGER NOT NULL CHECK(attempts>=0),created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL);
CREATE UNIQUE INDEX one_pending ON batches((1)) WHERE state<>'VERIFIED';
CREATE TRIGGER immutable_batch BEFORE UPDATE OF batch_id,payload,digest,created_at
  ON batches BEGIN SELECT RAISE(ABORT,'immutable batch'); END;
CREATE TRIGGER retain_batch BEFORE DELETE ON batches
  BEGIN SELECT RAISE(ABORT,'retained batch'); END;
"""


def schema_signature(db: sqlite3.Connection) -> tuple:
    return tuple(
        tuple(row)
        for row in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name")
    )


@cache
def expected_schema() -> tuple:
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(SCHEMA)
        return schema_signature(db)
    finally:
        db.close()


class JournalUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("SYNC_JOURNAL_UNAVAILABLE")


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not UTC_TEXT.fullmatch(value):
        raise ValueError("UTC timestamp required")
    return datetime.fromisoformat(value).astimezone(UTC)


def decode_batch(raw: str) -> ExportBatch:
    data = _json(raw, MAX_INTENT_BYTES)
    if set(data) != {"archive_id", "binding_json", "after", "next_cursor", "rows"}:
        raise ValueError("invalid batch")
    if (
        not isinstance(data["archive_id"], str)
        or str(UUID(data["archive_id"])) != data["archive_id"]
    ):
        raise ValueError("invalid archive")
    _json(data["binding_json"], 4096)
    before = SourceCursor(**data["after"])
    end = SourceCursor(**data["next_cursor"])
    if not isinstance(data["rows"], list) or not 1 <= len(data["rows"]) <= MAX_ROWS:
        raise ValueError("invalid rows")
    rows = []
    previous = before
    times = set()
    for item in data["rows"]:
        if set(item) != {"cursor", "payload", "available_at"}:
            raise ValueError("invalid row")
        cursor = SourceCursor(**item["cursor"])
        payload = _json(item["payload"], 8192)
        bar = ArchivedBar.model_validate_json(item["payload"])
        if (
            payload.get("closed") is not True
            or cursor <= previous
            or cursor != SourceCursor(bar.first_receipt, bar.time_server_s)
            or cursor.time_server_s in times
            or utc(item["available_at"]) < bar.first_received_at
        ):
            raise ValueError("invalid cursor or availability")
        times.add(cursor.time_server_s)
        rows.append(ExportRow(cursor, item["payload"], item["available_at"]))
        previous = cursor
    if previous != end:
        raise ValueError("invalid end cursor")
    batch = ExportBatch(data["archive_id"], data["binding_json"], before, end, tuple(rows))
    if len(json.dumps(batch.wire_rows()).encode()) > MAX_BATCH_BYTES:
        raise ValueError("oversized batch")
    return batch


@dataclass(frozen=True)
class Pending:
    batch_id: str
    state: str
    attempts: int
    batch: ExportBatch


@dataclass(frozen=True)
class SyncStatus:
    cursor: SourceCursor
    pending: Pending | None
    last_clock: str
    database_bytes: int
    storage: str


class SyncJournal:
    def __init__(
        self,
        directory: Path,
        source: NativeArchiveSource,
        owner_id: UUID,
        destination: str,
        *,
        create: bool = False,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.directory, self.path = directory, directory / "sync.sqlite3"
        self.source, self.owner_id, self.destination = source, str(owner_id), destination
        self._now = utc_now
        self._lock_fd: int | None = None
        self._pid = os.getpid()
        self.step_lock = threading.Lock()
        self.binding = canonical(
            {
                "source_directory": str(source.directory),
                "archive_id": source.archive_id,
                "binding_json": source.binding_json,
                "owner_id": self.owner_id,
                "destination": destination,
            }
        )
        try:
            if (
                not isinstance(owner_id, UUID)
                or directory == source.directory
                or not re.fullmatch(
                    r"https://[a-z0-9.-]+(?::[0-9]{1,5})?|http://127\.0\.0\.1:[0-9]{1,5}",
                    destination,
                )
            ):
                raise JournalUnavailable()
            self._directory()
            if create and any(directory.iterdir()):
                raise JournalUnavailable()
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            self._lock_fd = os.open(
                directory / "sync.lock", flags | (os.O_CREAT | os.O_EXCL if create else 0), 0o600
            )
            self._lock_identity = self._private_file(directory / "sync.lock")
            opened = os.fstat(self._lock_fd)
            if (opened.st_dev, opened.st_ino) != self._lock_identity:
                raise JournalUnavailable()
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if create:
                fd = os.open(self.path, flags | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            self._file_identity = self._private_file(self.path)
            with self._connect() as db:
                if create:
                    self._initialize(db)
                db.execute("BEGIN")
                self._audit(db)
            if create:
                fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, JournalUnavailable:
            self.close()
            raise JournalUnavailable() from None

    def close(self) -> None:
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def __enter__(self) -> SyncJournal:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _directory(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise JournalUnavailable()
        info = self.directory.lstat()
        identity = (info.st_dev, info.st_ino)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or getattr(self, "_directory_identity", identity) != identity
        ):
            raise JournalUnavailable()
        self._directory_identity = identity

    @staticmethod
    def _private_file(path: Path) -> tuple[int, int]:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise JournalUnavailable()
        return info.st_dev, info.st_ino

    def _files(self) -> None:
        self._directory()
        if (
            self._lock_fd is None
            or self._pid != os.getpid()
            or self._private_file(self.directory / "sync.lock") != self._lock_identity
            or self._private_file(self.path) != self._file_identity
        ):
            raise JournalUnavailable()
        for suffix in ("-wal", "-shm"):
            with suppress(FileNotFoundError):
                self._private_file(Path(str(self.path) + suffix))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = None
        try:
            self._files()
            db = sqlite3.connect(
                self.path.as_uri() + "?mode=rw", uri=True, timeout=0.1, isolation_level=None
            )
            db.row_factory = sqlite3.Row
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_INTENT_BYTES * 2)
            db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            db.execute("PRAGMA trusted_schema=OFF")
            if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise JournalUnavailable()
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA fullfsync=ON")
            db.execute("PRAGMA checkpoint_fullfsync=ON")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            maximum = MAX_JOURNAL_BYTES // page_size
            if (
                db.execute(f"PRAGMA max_page_count={maximum}").fetchone()[0] != maximum
                or db.execute("PRAGMA synchronous").fetchone()[0] != 2
            ):
                raise JournalUnavailable()
            self._files()
            yield db
            self._files()
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise JournalUnavailable() from None
        finally:
            if db is not None:
                db.close()

    def _timestamp(self, previous: str | None = None) -> str:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise JournalUnavailable()
        now = now.astimezone(UTC)
        if previous is not None and now < utc(previous):
            raise JournalUnavailable()
        return now.isoformat(timespec="microseconds")

    def _initialize(self, db: sqlite3.Connection) -> None:
        db.executescript("BEGIN IMMEDIATE;" + SCHEMA + "PRAGMA user_version=1;")
        db.execute("INSERT INTO meta VALUES(1,?,0,0,?)", (self.binding, self._timestamp()))
        db.commit()

    def _pending(self, row: sqlite3.Row) -> Pending:
        if (
            type(row["seq"]) is not int
            or row["seq"] <= 0
            or not isinstance(row["payload"], str)
            or not isinstance(row["batch_id"], str)
            or hashlib.sha256(row["payload"].encode()).hexdigest() != row["digest"]
            or str(UUID(row["batch_id"])) != row["batch_id"]
            or row["state"] not in STATES
            or type(row["attempts"]) is not int
            or row["attempts"] < 0
        ):
            raise JournalUnavailable()
        batch = decode_batch(row["payload"])
        if (
            batch.archive_id != self.source.archive_id
            or batch.binding_json != self.source.binding_json
            or utc(row["updated_at"]) < utc(row["created_at"])
            or any(utc(r.available_at) > utc(row["created_at"]) for r in batch.rows)
            or (row["state"] in {"UNKNOWN", "VERIFIED"} and row["attempts"] == 0)
        ):
            raise JournalUnavailable()
        return Pending(row["batch_id"], row["state"], row["attempts"], batch)

    def _state(self, db: sqlite3.Connection) -> SyncStatus:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or schema_signature(db) != expected_schema()
        ):
            raise JournalUnavailable()
        meta = db.execute("SELECT * FROM meta LIMIT 2").fetchall()
        if len(meta) != 1 or meta[0]["id"] != 1 or meta[0]["binding"] != self.binding:
            raise JournalUnavailable()
        row = meta[0]
        self._timestamp(row["last_clock"])
        cursor = SourceCursor(row["receipt"], row["time_server_s"])
        latest = db.execute(
            "SELECT * FROM batches WHERE state='VERIFIED' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if cursor != (self._pending(latest).batch.next_cursor if latest else SourceCursor()):
            raise JournalUnavailable()
        rows = db.execute("SELECT * FROM batches WHERE state<>'VERIFIED' LIMIT 2").fetchall()
        pending = self._pending(rows[0]) if rows else None
        if len(rows) > 1 or (pending and pending.batch.after != cursor):
            raise JournalUnavailable()
        for item in ([latest] if latest else []) + rows:
            if utc(item["updated_at"]) > utc(row["last_clock"]):
                raise JournalUnavailable()
        size = (
            db.execute("PRAGMA page_count").fetchone()[0]
            * db.execute("PRAGMA page_size").fetchone()[0]
        )
        storage = (
            "warning_85"
            if size >= MAX_JOURNAL_BYTES * 0.85
            else ("warning_70" if size >= MAX_JOURNAL_BYTES * 0.70 else "normal")
        )
        return SyncStatus(cursor, pending, row["last_clock"], size, storage)

    def _audit(self, db: sqlite3.Connection) -> None:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
        ):
            raise JournalUnavailable()
        state = self._state(db)
        cursor, outstanding, previous_time = SourceCursor(), False, None
        for sequence, row in enumerate(db.execute("SELECT * FROM batches ORDER BY seq"), 1):
            pending = self._pending(row)
            if (
                outstanding
                or row["seq"] != sequence
                or pending.batch.after != cursor
                or utc(row["updated_at"]) > utc(state.last_clock)
                or (previous_time is not None and utc(row["created_at"]) < previous_time)
            ):
                raise JournalUnavailable()
            previous_time = utc(row["updated_at"])
            if pending.state == "VERIFIED":
                cursor = pending.batch.next_cursor
            else:
                outstanding = True

    def status(self) -> SyncStatus:
        with self._connect() as db:
            db.execute("BEGIN")
            return self._state(db)

    def prepare(self, batch: ExportBatch) -> Pending:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            payload = canonical(asdict(batch))
            checked = decode_batch(payload)
            if (
                checked.archive_id != self.source.archive_id
                or checked.binding_json != self.source.binding_json
                or checked.after != state.cursor
            ):
                raise JournalUnavailable()
            if state.pending:
                if state.pending.batch != checked:
                    raise JournalUnavailable()
                return state.pending
            now = self._timestamp(state.last_clock)
            if any(
                not utc(state.last_clock) <= utc(r.available_at) <= utc(now) for r in checked.rows
            ):
                raise JournalUnavailable()
            batch_id = str(uuid4())
            db.execute(
                "INSERT INTO batches(batch_id,payload,digest,state,attempts,created_at,updated_at) "
                "VALUES(?,?,?,'PREPARED',0,?,?)",
                (batch_id, payload, hashlib.sha256(payload.encode()).hexdigest(), now, now),
            )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return Pending(batch_id, "PREPARED", 0, checked)

    def _transition(self, batch_id: str, target: str) -> Pending:
        """Internal driver boundary: VERIFIED is used only after independent read-back."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            pending = state.pending
            allowed = {
                "PREPARED": {"UNKNOWN", "QUARANTINED"},
                "UNKNOWN": {"PREPARED", "VERIFIED", "QUARANTINED"},
            }
            if (
                pending is None
                or pending.batch_id != batch_id
                or target not in allowed.get(pending.state, set())
            ):
                raise JournalUnavailable()
            now = self._timestamp(state.last_clock)
            attempts = pending.attempts + int(target == "UNKNOWN")
            db.execute(
                "UPDATE batches SET state=?,attempts=?,updated_at=? WHERE batch_id=?",
                (target, attempts, now, batch_id),
            )
            cursor = pending.batch.next_cursor if target == "VERIFIED" else state.cursor
            db.execute(
                "UPDATE meta SET receipt=?,time_server_s=?,last_clock=? WHERE id=1",
                (cursor.receipt, cursor.time_server_s, now),
            )
            db.commit()
            return Pending(batch_id, target, attempts, pending.batch)

    def begin_send(self, batch_id: str) -> Pending:
        return self._transition(batch_id, "UNKNOWN")

    def quarantine(self, batch_id: str) -> Pending:
        return self._transition(batch_id, "QUARANTINED")

    def reconcile(self, batch_id: str, snapshot: object) -> Pending:
        state = self.status()
        pending = state.pending
        if pending is None or pending.batch_id != batch_id or pending.state != "UNKNOWN":
            raise JournalUnavailable()
        target = "QUARANTINED"
        try:
            result = _json(canonical(snapshot), MAX_INTENT_BYTES)
            if set(result) != {"archive_id", "binding", "rows"}:
                raise ValueError("invalid read-back")
            if result["archive_id"] != pending.batch.archive_id:
                raise ValueError("archive conflict")
            rows = result["rows"]
            if not isinstance(rows, list) or len(rows) > len(pending.batch.rows):
                raise ValueError("invalid rows")
            if result["binding"] is None:
                if rows:
                    raise ValueError("orphan rows")
                target = "PREPARED"
            else:
                if canonical(result["binding"]) != canonical(
                    json.loads(pending.batch.binding_json)
                ):
                    raise ValueError("binding conflict")
                expected = {
                    r.cursor.time_server_s: json.loads(r.payload) for r in pending.batch.rows
                }
                seen = set()
                now = utc(self._timestamp(state.last_clock))
                for row in rows:
                    if not isinstance(row, dict) or set(row) != {"bar", "available_at"}:
                        raise ValueError("invalid row")
                    bar = row["bar"]
                    key = bar["time_server_s"]
                    if (
                        type(key) is not int
                        or key in seen
                        or key not in expected
                        or canonical(bar) != canonical(expected[key])
                        or not utc(bar["first_received_at"]) <= utc(row["available_at"]) <= now
                    ):
                        raise ValueError("bar conflict")
                    seen.add(key)
                target = "VERIFIED" if len(seen) == len(expected) else "PREPARED"
        except ValueError, TypeError, KeyError, RecursionError:
            target = "QUARANTINED"
        return self._transition(batch_id, target)
