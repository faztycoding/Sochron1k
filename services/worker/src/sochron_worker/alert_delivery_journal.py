"""Durable single-writer alert-delivery outbox and redacted status projection."""

from __future__ import annotations

import fcntl
import hashlib
import os
import sqlite3
import stat
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import AwareDatetime, Field, field_validator
from sochron1k.alert_delivery_source import AlertDeliveryFact
from sochron1k.alert_delivery_status import AlertDeliveryStatusSnapshot
from sochron1k.models import StrictModel

from .native_source import _json
from .sync_journal import canonical, utc

MAX_JOURNAL_BYTES = 32 * 1024 * 1024
MAX_PAYLOAD_BYTES = 16_384
STATES = {"PREPARED", "UNKNOWN", "VERIFIED", "QUARANTINED"}
SCHEMA = """
CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),binding TEXT NOT NULL,
  last_clock TEXT NOT NULL);
CREATE TABLE deliveries(seq INTEGER PRIMARY KEY AUTOINCREMENT,
  delivery_id TEXT NOT NULL UNIQUE,alert_id TEXT NOT NULL UNIQUE,
  payload TEXT NOT NULL,digest TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('PREPARED','UNKNOWN','VERIFIED','QUARANTINED')),
  attempts INTEGER NOT NULL CHECK(attempts>=0),created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,accepted_at TEXT);
CREATE UNIQUE INDEX one_pending ON deliveries((1))
  WHERE state IN ('PREPARED','UNKNOWN');
CREATE TRIGGER immutable_delivery BEFORE UPDATE OF
  delivery_id,alert_id,payload,digest,created_at ON deliveries
  BEGIN SELECT RAISE(ABORT,'immutable delivery'); END;
CREATE TRIGGER retain_delivery BEFORE DELETE ON deliveries
  BEGIN SELECT RAISE(ABORT,'retained delivery'); END;
"""


def _schema_signature(db: sqlite3.Connection) -> tuple:
    return tuple(
        tuple(row)
        for row in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name")
    )


@cache
def _expected_schema() -> tuple:
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(SCHEMA)
        return _schema_signature(db)
    finally:
        db.close()


class AlertDeliveryJournalUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_DELIVERY_JOURNAL_UNAVAILABLE")


class AlertNotification(StrictModel):
    protocol: Literal["sochron.alert-notification.v1"] = "sochron.alert-notification.v1"
    delivery_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    destination_ref: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    alert_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    condition_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    kind: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_]+$")
    severity: Literal["critical", "warning", "info"]
    source: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_]+$")
    source_ref: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    detail_code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    observed_at_utc: AwareDatetime
    evidence_routes: tuple[str, ...]

    @field_validator("observed_at_utc")
    @classmethod
    def utc_observed(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class AlertDeliveryReceipt(StrictModel):
    protocol: Literal["sochron.alert-delivery-receipt.v1"]
    delivery_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    destination_ref: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_at_utc: AwareDatetime

    @field_validator("accepted_at_utc")
    @classmethod
    def utc_accepted(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


@dataclass(frozen=True)
class DeliveryIntent:
    delivery_id: str
    state: str
    attempts: int
    payload: AlertNotification
    digest: str
    created_at: str
    updated_at: str
    accepted_at: str | None


@dataclass(frozen=True)
class AlertDeliveryJournalStatus:
    pending: DeliveryIntent | None
    verified: int
    quarantined: int
    last_verified_id: str | None
    last_verified_at: str | None
    last_clock: str
    database_bytes: int


class AlertDeliveryJournal:
    def __init__(
        self,
        directory: Path,
        *,
        source_origin: str,
        destination_origin: str,
        destination_ref: str,
        create: bool = False,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.directory = directory
        self.path = directory / "alert-delivery.sqlite3"
        self.status_path = directory / "delivery-status.json"
        self.source_origin = source_origin
        self.destination_origin = destination_origin
        self.destination_ref = destination_ref
        self._now = utc_now
        self._lock_fd: int | None = None
        self._pid = os.getpid()
        self.step_lock = threading.Lock()
        self.binding = canonical(
            {
                "source_origin": source_origin,
                "destination_origin": destination_origin,
                "destination_ref": destination_ref,
            }
        )
        try:
            self._directory()
            if create and any(directory.iterdir()):
                raise AlertDeliveryJournalUnavailable()
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            self._lock_fd = os.open(
                directory / "alert-delivery.lock",
                flags | (os.O_CREAT | os.O_EXCL if create else 0),
                0o600,
            )
            self._lock_identity = self._private_file(directory / "alert-delivery.lock")
            opened = os.fstat(self._lock_fd)
            if (opened.st_dev, opened.st_ino) != self._lock_identity:
                raise AlertDeliveryJournalUnavailable()
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
                self._fsync_directory()
        except (
            OSError,
            sqlite3.Error,
            ValueError,
            TypeError,
            KeyError,
            AlertDeliveryJournalUnavailable,
        ):
            self.close()
            raise AlertDeliveryJournalUnavailable() from None

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self) -> None:
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def _directory(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise AlertDeliveryJournalUnavailable()
        info = self.directory.lstat()
        identity = (info.st_dev, info.st_ino)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or getattr(self, "_directory_identity", identity) != identity
        ):
            raise AlertDeliveryJournalUnavailable()
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
            raise AlertDeliveryJournalUnavailable()
        return info.st_dev, info.st_ino

    def _files(self) -> None:
        self._directory()
        if (
            self._lock_fd is None
            or self._pid != os.getpid()
            or self._private_file(self.directory / "alert-delivery.lock") != self._lock_identity
            or self._private_file(self.path) != self._file_identity
        ):
            raise AlertDeliveryJournalUnavailable()
        for suffix in ("-wal", "-shm"):
            with suppress(FileNotFoundError):
                self._private_file(Path(str(self.path) + suffix))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = None
        try:
            self._files()
            db = sqlite3.connect(
                self.path.as_uri() + "?mode=rw",
                uri=True,
                timeout=0.1,
                isolation_level=None,
            )
            db.row_factory = sqlite3.Row
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_PAYLOAD_BYTES * 2)
            db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            db.execute("PRAGMA trusted_schema=OFF")
            if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise AlertDeliveryJournalUnavailable()
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA fullfsync=ON")
            db.execute("PRAGMA checkpoint_fullfsync=ON")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            maximum = MAX_JOURNAL_BYTES // page_size
            if (
                db.execute(f"PRAGMA max_page_count={maximum}").fetchone()[0] != maximum
                or db.execute("PRAGMA synchronous").fetchone()[0] != 2
            ):
                raise AlertDeliveryJournalUnavailable()
            self._files()
            yield db
            self._files()
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise AlertDeliveryJournalUnavailable() from None
        finally:
            if db is not None:
                db.close()

    def _timestamp(self, previous: str | None = None) -> str:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise AlertDeliveryJournalUnavailable()
        normalized = now.astimezone(UTC)
        if previous is not None and normalized < utc(previous):
            raise AlertDeliveryJournalUnavailable()
        return normalized.isoformat(timespec="microseconds")

    def _initialize(self, db: sqlite3.Connection) -> None:
        db.executescript("BEGIN IMMEDIATE;" + SCHEMA + "PRAGMA user_version=1;")
        db.execute("INSERT INTO meta VALUES(1,?,?)", (self.binding, self._timestamp()))
        db.commit()

    def _intent(self, row: sqlite3.Row) -> DeliveryIntent:
        if (
            type(row["seq"]) is not int
            or row["seq"] <= 0
            or not isinstance(row["payload"], str)
            or len(row["payload"].encode()) > MAX_PAYLOAD_BYTES
            or hashlib.sha256(row["payload"].encode()).hexdigest() != row["digest"]
            or row["state"] not in STATES
            or type(row["attempts"]) is not int
            or row["attempts"] < 0
        ):
            raise AlertDeliveryJournalUnavailable()
        payload = AlertNotification.model_validate(_json(row["payload"], MAX_PAYLOAD_BYTES))
        if (
            payload.delivery_id != row["delivery_id"]
            or payload.alert_id != row["alert_id"]
            or payload.destination_ref != self.destination_ref
            or (row["state"] in {"UNKNOWN", "VERIFIED"} and row["attempts"] == 0)
            or utc(row["updated_at"]) < utc(row["created_at"])
            or (row["state"] == "VERIFIED") != (row["accepted_at"] is not None)
        ):
            raise AlertDeliveryJournalUnavailable()
        if row["accepted_at"] is not None:
            accepted = utc(row["accepted_at"])
            if accepted < payload.observed_at_utc or accepted > utc(row["updated_at"]):
                raise AlertDeliveryJournalUnavailable()
        return DeliveryIntent(
            delivery_id=row["delivery_id"],
            state=row["state"],
            attempts=row["attempts"],
            payload=payload,
            digest=row["digest"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            accepted_at=row["accepted_at"],
        )

    def _state(self, db: sqlite3.Connection) -> AlertDeliveryJournalStatus:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or _schema_signature(db) != _expected_schema()
        ):
            raise AlertDeliveryJournalUnavailable()
        meta = db.execute("SELECT * FROM meta LIMIT 2").fetchall()
        if len(meta) != 1 or meta[0]["id"] != 1 or meta[0]["binding"] != self.binding:
            raise AlertDeliveryJournalUnavailable()
        last_clock = meta[0]["last_clock"]
        self._timestamp(last_clock)
        pending_rows = db.execute(
            "SELECT * FROM deliveries WHERE state IN ('PREPARED','UNKNOWN') LIMIT 2"
        ).fetchall()
        if len(pending_rows) > 1:
            raise AlertDeliveryJournalUnavailable()
        pending = self._intent(pending_rows[0]) if pending_rows else None
        verified = db.execute("SELECT count(*) FROM deliveries WHERE state='VERIFIED'").fetchone()[
            0
        ]
        quarantined = db.execute(
            "SELECT count(*) FROM deliveries WHERE state='QUARANTINED'"
        ).fetchone()[0]
        latest = db.execute(
            "SELECT * FROM deliveries WHERE state='VERIFIED' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        latest_intent = self._intent(latest) if latest else None
        size = (
            db.execute("PRAGMA page_count").fetchone()[0]
            * db.execute("PRAGMA page_size").fetchone()[0]
        )
        return AlertDeliveryJournalStatus(
            pending=pending,
            verified=verified,
            quarantined=quarantined,
            last_verified_id=latest_intent.delivery_id if latest_intent else None,
            last_verified_at=latest_intent.accepted_at if latest_intent else None,
            last_clock=last_clock,
            database_bytes=size,
        )

    def _audit(self, db: sqlite3.Connection) -> None:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise AlertDeliveryJournalUnavailable()
        state = self._state(db)
        pending_seen = False
        previous_time: datetime | None = None
        for sequence, row in enumerate(db.execute("SELECT * FROM deliveries ORDER BY seq"), 1):
            intent = self._intent(row)
            created = utc(intent.created_at)
            if (
                row["seq"] != sequence
                or (previous_time is not None and created < previous_time)
                or utc(intent.updated_at) > utc(state.last_clock)
                or (pending_seen and intent.state in {"PREPARED", "UNKNOWN"})
            ):
                raise AlertDeliveryJournalUnavailable()
            previous_time = utc(intent.updated_at)
            pending_seen = pending_seen or intent.state in {"PREPARED", "UNKNOWN"}

    def status(self) -> AlertDeliveryJournalStatus:
        with self._connect() as db:
            db.execute("BEGIN")
            return self._state(db)

    def prepare(self, fact: AlertDeliveryFact) -> DeliveryIntent | None:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            if state.quarantined:
                db.rollback()
                return None
            existing = db.execute(
                "SELECT * FROM deliveries WHERE alert_id=?", (fact.id,)
            ).fetchone()
            if existing is not None:
                db.rollback()
                return self._intent(existing)
            if state.pending is not None:
                db.rollback()
                return state.pending
            now = self._timestamp(state.last_clock)
            if fact.observed_at_utc > utc(now):
                raise AlertDeliveryJournalUnavailable()
            delivery_id = hashlib.sha256(
                f"{self.destination_ref}\x1f{fact.id}".encode()
            ).hexdigest()[:32]
            notification = AlertNotification(
                delivery_id=delivery_id,
                destination_ref=self.destination_ref,
                alert_id=fact.id,
                condition_id=fact.condition_id,
                kind=fact.kind,
                severity=fact.severity,
                source=fact.source,
                source_ref=fact.source_ref,
                detail_code=fact.detail_code,
                observed_at_utc=fact.observed_at_utc,
                evidence_routes=fact.evidence_routes,
            )
            payload = canonical(notification.model_dump(mode="json"))
            if len(payload.encode()) > MAX_PAYLOAD_BYTES:
                raise AlertDeliveryJournalUnavailable()
            digest = hashlib.sha256(payload.encode()).hexdigest()
            db.execute(
                "INSERT INTO deliveries(delivery_id,alert_id,payload,digest,state,attempts,"
                "created_at,updated_at,accepted_at) VALUES(?,?,?,?,'PREPARED',0,?,?,NULL)",
                (delivery_id, fact.id, payload, digest, now, now),
            )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return self._intent(
                db.execute(
                    "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)
                ).fetchone()
            )

    def begin_send(self, delivery_id: str) -> DeliveryIntent:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            pending = state.pending
            if pending is None or pending.delivery_id != delivery_id or pending.state != "PREPARED":
                raise AlertDeliveryJournalUnavailable()
            now = self._timestamp(state.last_clock)
            db.execute(
                "UPDATE deliveries SET state='UNKNOWN',attempts=attempts+1,updated_at=? "
                "WHERE delivery_id=?",
                (now, delivery_id),
            )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return self._intent(
                db.execute(
                    "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)
                ).fetchone()
            )

    def reconcile(self, delivery_id: str, receipt: AlertDeliveryReceipt | None) -> DeliveryIntent:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            pending = state.pending
            if pending is None or pending.delivery_id != delivery_id or pending.state != "UNKNOWN":
                raise AlertDeliveryJournalUnavailable()
            now = self._timestamp(state.last_clock)
            if receipt is None:
                db.execute(
                    "UPDATE deliveries SET state='PREPARED',updated_at=? WHERE delivery_id=?",
                    (now, delivery_id),
                )
            elif (
                receipt.delivery_id != pending.delivery_id
                or receipt.destination_ref != self.destination_ref
                or receipt.payload_sha256 != pending.digest
                or receipt.accepted_at_utc < pending.payload.observed_at_utc
                or receipt.accepted_at_utc > utc(now)
            ):
                db.execute(
                    "UPDATE deliveries SET state='QUARANTINED',updated_at=? WHERE delivery_id=?",
                    (now, delivery_id),
                )
            else:
                accepted = receipt.accepted_at_utc.isoformat(timespec="microseconds")
                db.execute(
                    "UPDATE deliveries SET state='VERIFIED',updated_at=?,accepted_at=? "
                    "WHERE delivery_id=?",
                    (now, accepted, delivery_id),
                )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return self._intent(
                db.execute(
                    "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)
                ).fetchone()
            )

    def quarantine(self, delivery_id: str) -> DeliveryIntent:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            pending = state.pending
            if pending is None or pending.delivery_id != delivery_id:
                raise AlertDeliveryJournalUnavailable()
            now = self._timestamp(state.last_clock)
            db.execute(
                "UPDATE deliveries SET state='QUARANTINED',updated_at=? WHERE delivery_id=?",
                (now, delivery_id),
            )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return self._intent(
                db.execute(
                    "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)
                ).fetchone()
            )

    def _fsync_directory(self) -> None:
        descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def publish_status(self, worker_state: str, *, heartbeat_seconds: int) -> None:
        states = {
            "IDLE": "connected",
            "VERIFIED": "connected",
            "PREPARED": "pending",
            "UNKNOWN": "unknown",
            "QUARANTINED": "quarantined",
            "RETRY_BUDGET_EXHAUSTED": "retry_exhausted",
            "DEGRADED": "degraded",
        }
        if worker_state not in states or not 5 <= heartbeat_seconds <= 3600:
            raise AlertDeliveryJournalUnavailable()
        state = self.status()
        now = utc(self._timestamp(state.last_clock))
        snapshot = AlertDeliveryStatusSnapshot(
            protocol="sochron.alert-delivery-status.v1",
            state=states[worker_state],
            destination_ref=self.destination_ref,
            updated_at_utc=now,
            heartbeat_expires_at_utc=now + timedelta(seconds=heartbeat_seconds),
            pending_deliveries=int(state.pending is not None),
            unknown_deliveries=int(state.pending is not None and state.pending.state == "UNKNOWN"),
            verified_deliveries=state.verified,
            quarantined_deliveries=state.quarantined,
            last_delivery_ref=state.last_verified_id,
            last_verified_at_utc=(
                utc(state.last_verified_at) if state.last_verified_at is not None else None
            ),
        )
        payload = canonical(snapshot.model_dump(mode="json")).encode()
        temporary = self.directory / f".delivery-status.{uuid4().hex}.tmp"
        descriptor: int | None = None
        try:
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.close(descriptor)
            descriptor = None
            with suppress(FileNotFoundError):
                self._private_file(self.status_path)
            os.replace(temporary, self.status_path)
            self._private_file(self.status_path)
            self._fsync_directory()
        except OSError, ValueError, TypeError:
            raise AlertDeliveryJournalUnavailable() from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            with suppress(FileNotFoundError):
                temporary.unlink()
