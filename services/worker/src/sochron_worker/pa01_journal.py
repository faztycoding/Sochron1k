"""Private PA01 write-ahead journal; no network, risk or execution authority."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import stat
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from functools import cache
from pathlib import Path
from uuid import UUID

from .native_source import PRICE_TEXT, _json
from .pa01_envelope import PA01DecisionEnvelope
from .pa01_source import PA01DecisionSource
from .sync_config import SyncConfigInvalid, origin
from .sync_journal import canonical, utc

MAX_JOURNAL_BYTES = 64 * 1024 * 1024
MAX_PAYLOAD_BYTES = 131_072
STATES = {"PREPARED", "UNKNOWN", "VERIFIED", "QUARANTINED"}
SCHEMA = """
CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),binding TEXT NOT NULL,
  last_formed_at TEXT,last_fingerprint TEXT,last_clock TEXT NOT NULL,
  CHECK((last_formed_at IS NULL)=(last_fingerprint IS NULL)));
CREATE TABLE decisions(seq INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id TEXT NOT NULL UNIQUE,payload TEXT NOT NULL,digest TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('PREPARED','UNKNOWN','VERIFIED','QUARANTINED')),
  attempts INTEGER NOT NULL CHECK(attempts>=0),created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL);
CREATE UNIQUE INDEX one_pending_pa01 ON decisions((1)) WHERE state<>'VERIFIED';
CREATE TRIGGER immutable_pa01_decision BEFORE UPDATE OF signal_id,payload,digest,created_at
  ON decisions BEGIN SELECT RAISE(ABORT,'immutable PA01 decision'); END;
CREATE TRIGGER retain_pa01_decision BEFORE DELETE ON decisions
  BEGIN SELECT RAISE(ABORT,'retained PA01 decision'); END;
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


class PA01JournalUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_JOURNAL_UNAVAILABLE")


def decode_envelope(raw: str) -> PA01DecisionEnvelope:
    if not isinstance(raw, str) or len(raw.encode()) > MAX_PAYLOAD_BYTES:
        raise ValueError("invalid envelope")
    data = _json(raw, MAX_PAYLOAD_BYTES)

    def decimal_field(container: dict, key: str, *, nullable: bool = False) -> None:
        value = container.get(key)
        if nullable and value is None:
            return
        if not isinstance(value, str) or len(value) > 40 or not PRICE_TEXT.fullmatch(value):
            raise ValueError("invalid exact decimal")
        container[key] = Decimal(value)

    snapshot = data["snapshot"]
    values = snapshot["values"]
    decimal_field(snapshot["policy_context"], "spread_price")
    features = values["features"]
    for key in (
        "ema20",
        "ema50",
        "previous_ema20",
        "atr14",
        "adx14",
        "spread_cap",
        "proposed_stop",
        "stop_distance_at_close",
        "stop_distance_atr",
    ):
        decimal_field(features, key, nullable=True)
    for key in ("latest_swing_highs", "latest_swing_lows"):
        for item in features[key]:
            decimal_field(item, "price")
    execution = values["execution_parameters"]
    for key in (
        "max_entry_drift_atr",
        "stop_buffer_atr",
        "stop_min_atr",
        "stop_max_atr",
        "target_r",
    ):
        decimal_field(execution, key)
    result = PA01DecisionEnvelope.model_validate(data)
    if canonical(result.model_dump(mode="json")) != raw:
        raise ValueError("noncanonical envelope")
    return result


@dataclass(frozen=True)
class PA01Pending:
    signal_id: str
    state: str
    attempts: int
    envelope: PA01DecisionEnvelope


@dataclass(frozen=True)
class PA01JournalStatus:
    last_formed_at: datetime | None
    last_fingerprint: str | None
    pending: PA01Pending | None
    last_clock: str
    database_bytes: int
    storage: str


class PA01ProducerJournal:
    def __init__(
        self,
        directory: Path,
        source: PA01DecisionSource,
        owner_id: UUID,
        strategy_version_id: int,
        experiment_id: int,
        destination: str,
        *,
        create: bool = False,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.directory, self.path = directory, directory / "pa01.sqlite3"
        self.source = source
        self.owner_id = str(owner_id)
        self.strategy_version_id = strategy_version_id
        self.experiment_id = experiment_id
        self.destination = destination
        self._now = utc_now
        self._lock_fd: int | None = None
        self._pid = os.getpid()
        self.step_lock = threading.Lock()
        archive = source.archive
        self.binding = canonical(
            {
                "source_directory": str(archive.directory),
                "archive_id": archive.archive_id,
                "archive_binding": json.loads(archive.binding_json),
                "policy_file": str(source.policy.path),
                "code_hash": source.code_hash,
                "owner_id": self.owner_id,
                "strategy_version_id": strategy_version_id,
                "experiment_id": experiment_id,
                "destination": destination,
            }
        )
        try:
            if (
                not isinstance(owner_id, UUID)
                or type(strategy_version_id) is not int
                or strategy_version_id <= 0
                or type(experiment_id) is not int
                or experiment_id <= 0
                or directory == archive.directory
                or source.policy.path.parent == directory
                or not source.policy.path.is_absolute()
                or source.policy.path.resolve() != source.policy.path
                or origin(destination) != destination
            ):
                raise PA01JournalUnavailable()
            self._directory()
            if create and any(directory.iterdir()):
                raise PA01JournalUnavailable()
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            lock_path = directory / "pa01.lock"
            self._lock_fd = os.open(
                lock_path, flags | (os.O_CREAT | os.O_EXCL if create else 0), 0o600
            )
            self._lock_identity = self._private_file(lock_path)
            opened = os.fstat(self._lock_fd)
            if (opened.st_dev, opened.st_ino) != self._lock_identity:
                raise PA01JournalUnavailable()
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if create:
                descriptor = os.open(self.path, flags | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
            self._file_identity = self._private_file(self.path)
            with self._connect() as db:
                if create:
                    self._initialize(db)
                db.execute("BEGIN")
                self._audit(db)
            if create:
                descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        except (
            OSError,
            sqlite3.Error,
            ValueError,
            TypeError,
            KeyError,
            SyncConfigInvalid,
            PA01JournalUnavailable,
        ):
            self.close()
            raise PA01JournalUnavailable() from None

    def close(self) -> None:
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def __enter__(self) -> PA01ProducerJournal:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _directory(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise PA01JournalUnavailable()
        info = self.directory.lstat()
        identity = (info.st_dev, info.st_ino)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or getattr(self, "_directory_identity", identity) != identity
        ):
            raise PA01JournalUnavailable()
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
            raise PA01JournalUnavailable()
        return info.st_dev, info.st_ino

    def _files(self) -> None:
        self._directory()
        if (
            self._lock_fd is None
            or self._pid != os.getpid()
            or self._private_file(self.directory / "pa01.lock") != self._lock_identity
            or self._private_file(self.path) != self._file_identity
        ):
            raise PA01JournalUnavailable()
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
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_PAYLOAD_BYTES * 2)
            db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            db.execute("PRAGMA trusted_schema=OFF")
            if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise PA01JournalUnavailable()
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA fullfsync=ON")
            db.execute("PRAGMA checkpoint_fullfsync=ON")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            maximum = MAX_JOURNAL_BYTES // page_size
            if (
                db.execute(f"PRAGMA max_page_count={maximum}").fetchone()[0] != maximum
                or db.execute("PRAGMA synchronous").fetchone()[0] != 2
            ):
                raise PA01JournalUnavailable()
            self._files()
            yield db
            self._files()
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise PA01JournalUnavailable() from None
        finally:
            if db is not None:
                db.close()

    def _timestamp(self, previous: str | None = None) -> str:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise PA01JournalUnavailable()
        now = now.astimezone(UTC)
        if previous is not None and now < utc(previous):
            raise PA01JournalUnavailable()
        return now.isoformat(timespec="microseconds")

    def _initialize(self, db: sqlite3.Connection) -> None:
        db.executescript("BEGIN IMMEDIATE;" + SCHEMA + "PRAGMA user_version=1;")
        db.execute("INSERT INTO meta VALUES(1,?,NULL,NULL,?)", (self.binding, self._timestamp()))
        db.commit()

    def _pending(self, row: sqlite3.Row) -> PA01Pending:
        if (
            type(row["seq"]) is not int
            or row["seq"] <= 0
            or not isinstance(row["payload"], str)
            or not isinstance(row["signal_id"], str)
            or hashlib.sha256(row["payload"].encode()).hexdigest() != row["digest"]
            or row["state"] not in STATES
            or type(row["attempts"]) is not int
            or row["attempts"] < 0
        ):
            raise PA01JournalUnavailable()
        envelope = decode_envelope(row["payload"])
        if (
            row["signal_id"] != envelope.signal.signal_id
            or utc(row["updated_at"]) < utc(row["created_at"])
            or utc(row["created_at"]) < envelope.signal.confirmed_at
            or (row["state"] in {"UNKNOWN", "VERIFIED"} and row["attempts"] == 0)
        ):
            raise PA01JournalUnavailable()
        return PA01Pending(row["signal_id"], row["state"], row["attempts"], envelope)

    def _state(self, db: sqlite3.Connection) -> PA01JournalStatus:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or schema_signature(db) != expected_schema()
        ):
            raise PA01JournalUnavailable()
        meta = db.execute("SELECT * FROM meta LIMIT 2").fetchall()
        if len(meta) != 1 or meta[0]["id"] != 1 or meta[0]["binding"] != self.binding:
            raise PA01JournalUnavailable()
        row = meta[0]
        self._timestamp(row["last_clock"])
        last_formed = utc(row["last_formed_at"]) if row["last_formed_at"] is not None else None
        fingerprint = row["last_fingerprint"]
        if fingerprint is not None and (
            not isinstance(fingerprint, str)
            or len(fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in fingerprint)
        ):
            raise PA01JournalUnavailable()
        latest = db.execute(
            "SELECT * FROM decisions WHERE state='VERIFIED' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if latest is None:
            if last_formed is not None or fingerprint is not None:
                raise PA01JournalUnavailable()
        else:
            verified = self._pending(latest).envelope
            if (
                last_formed != verified.signal.formed_at
                or fingerprint != verified.decision_fingerprint
            ):
                raise PA01JournalUnavailable()
        rows = db.execute("SELECT * FROM decisions WHERE state<>'VERIFIED' LIMIT 2").fetchall()
        pending = self._pending(rows[0]) if rows else None
        if len(rows) > 1 or (
            pending is not None
            and last_formed is not None
            and pending.envelope.signal.formed_at <= last_formed
        ):
            raise PA01JournalUnavailable()
        for item in ([latest] if latest else []) + rows:
            if utc(item["updated_at"]) > utc(row["last_clock"]):
                raise PA01JournalUnavailable()
        size = (
            db.execute("PRAGMA page_count").fetchone()[0]
            * db.execute("PRAGMA page_size").fetchone()[0]
        )
        storage = (
            "warning_85"
            if size >= MAX_JOURNAL_BYTES * 0.85
            else ("warning_70" if size >= MAX_JOURNAL_BYTES * 0.70 else "normal")
        )
        return PA01JournalStatus(
            last_formed, fingerprint, pending, row["last_clock"], size, storage
        )

    def _audit(self, db: sqlite3.Connection) -> None:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
        ):
            raise PA01JournalUnavailable()
        state = self._state(db)
        cursor: datetime | None = None
        outstanding = False
        previous_time: datetime | None = None
        for sequence, row in enumerate(db.execute("SELECT * FROM decisions ORDER BY seq"), 1):
            pending = self._pending(row)
            formed = pending.envelope.signal.formed_at
            if (
                outstanding
                or row["seq"] != sequence
                or (cursor is not None and formed <= cursor)
                or utc(row["updated_at"]) > utc(state.last_clock)
                or (previous_time is not None and utc(row["created_at"]) < previous_time)
            ):
                raise PA01JournalUnavailable()
            previous_time = utc(row["updated_at"])
            if pending.state == "VERIFIED":
                cursor = formed
            else:
                outstanding = True
        if cursor != state.last_formed_at:
            raise PA01JournalUnavailable()

    def status(self) -> PA01JournalStatus:
        with self._connect() as db:
            db.execute("BEGIN")
            return self._state(db)

    def prepare(self, envelope: PA01DecisionEnvelope) -> PA01Pending:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            payload = canonical(envelope.model_dump(mode="json"))
            checked = decode_envelope(payload)
            if state.pending:
                if state.pending.envelope != checked:
                    raise PA01JournalUnavailable()
                return state.pending
            if (
                state.last_formed_at is not None
                and checked.signal.formed_at <= state.last_formed_at
            ):
                raise PA01JournalUnavailable()
            now = self._timestamp(state.last_clock)
            if not checked.signal.confirmed_at <= utc(now) <= checked.signal.expires_at:
                raise PA01JournalUnavailable()
            db.execute(
                "INSERT INTO decisions("
                "signal_id,payload,digest,state,attempts,created_at,updated_at) "
                "VALUES(?,?,?,'PREPARED',0,?,?)",
                (
                    checked.signal.signal_id,
                    payload,
                    hashlib.sha256(payload.encode()).hexdigest(),
                    now,
                    now,
                ),
            )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return PA01Pending(checked.signal.signal_id, "PREPARED", 0, checked)

    def _transition(self, signal_id: str, target: str) -> PA01Pending:
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
                or pending.signal_id != signal_id
                or target not in allowed.get(pending.state, set())
            ):
                raise PA01JournalUnavailable()
            now = self._timestamp(state.last_clock)
            attempts = pending.attempts + int(target == "UNKNOWN")
            db.execute(
                "UPDATE decisions SET state=?,attempts=?,updated_at=? WHERE signal_id=?",
                (target, attempts, now, signal_id),
            )
            formed = pending.envelope.signal.formed_at if target == "VERIFIED" else None
            fingerprint = pending.envelope.decision_fingerprint if target == "VERIFIED" else None
            db.execute(
                "UPDATE meta SET last_formed_at=coalesce(?,last_formed_at),"
                "last_fingerprint=coalesce(?,last_fingerprint),last_clock=? WHERE id=1",
                (
                    formed.isoformat(timespec="microseconds") if formed else None,
                    fingerprint,
                    now,
                ),
            )
            db.commit()
            return PA01Pending(signal_id, target, attempts, pending.envelope)

    def begin_send(self, signal_id: str) -> PA01Pending:
        return self._transition(signal_id, "UNKNOWN")

    def quarantine(self, signal_id: str) -> PA01Pending:
        return self._transition(signal_id, "QUARANTINED")

    def reconcile(self, signal_id: str, snapshot: object) -> PA01Pending:
        state = self.status()
        pending = state.pending
        if pending is None or pending.signal_id != signal_id or pending.state != "UNKNOWN":
            raise PA01JournalUnavailable()
        target = "QUARANTINED"
        try:
            if not isinstance(snapshot, dict):
                raise ValueError("invalid read-back")
            if snapshot.get("found") is False:
                if set(snapshot) != {"protocol", "found", "owner_id", "signal_id"} or (
                    snapshot["owner_id"] != self.owner_id or snapshot["signal_id"] != signal_id
                ):
                    raise ValueError("invalid missing row")
                target = "PREPARED"
            else:
                expected_keys = {
                    "protocol",
                    "found",
                    "owner_id",
                    "strategy_version_id",
                    "experiment_id",
                    "producer_revision",
                    "decision_fingerprint",
                    "snapshot",
                    "signal",
                }
                if set(snapshot) != expected_keys or snapshot["found"] is not True:
                    raise ValueError("invalid receiver record")
                envelope = pending.envelope
                if not (
                    snapshot["protocol"] == envelope.protocol
                    and snapshot["owner_id"] == self.owner_id
                    and snapshot["strategy_version_id"] == self.strategy_version_id
                    and snapshot["experiment_id"] == self.experiment_id
                    and snapshot["producer_revision"] == envelope.producer_revision
                    and snapshot["decision_fingerprint"] == envelope.decision_fingerprint
                ):
                    raise ValueError("receiver binding conflict")
                observed = []
                for key in ("snapshot", "signal"):
                    item = snapshot[key]
                    expected = getattr(envelope, key).model_dump(mode="json")
                    if not isinstance(item, dict) or set(item) != set(expected) | {
                        "row_id",
                        "created_at",
                    }:
                        raise ValueError("invalid receiver row")
                    if type(item["row_id"]) is not int or item["row_id"] <= 0:
                        raise ValueError("invalid receiver identity")
                    observed.append(utc(item["created_at"]))
                    time_fields = (
                        ("event_time", "received_at", "available_at")
                        if key == "snapshot"
                        else ("formed_at", "confirmed_at", "expires_at")
                    )
                    if any(utc(item[name]) != utc(expected[name]) for name in time_fields):
                        raise ValueError("receiver evidence conflict")
                    excluded = {"row_id", "created_at", *time_fields}
                    stripped = {name: value for name, value in item.items() if name not in excluded}
                    expected = {
                        name: value for name, value in expected.items() if name not in time_fields
                    }
                    if canonical(stripped) != canonical(expected):
                        raise ValueError("receiver evidence conflict")
                now = utc(self._timestamp(state.last_clock))
                if any(value > now for value in observed):
                    raise ValueError("receiver time from future")
                target = "VERIFIED"
        except ValueError, TypeError, KeyError, RecursionError:
            target = "QUARANTINED"
        return self._transition(signal_id, target)
