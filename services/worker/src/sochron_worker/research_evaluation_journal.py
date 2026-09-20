"""Private write-ahead journal for one immutable research evaluation envelope."""

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
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from uuid import UUID

from .research_evaluation import ResearchEvaluationEnvelope, decode_envelope
from .sync_config import SyncConfigInvalid, origin
from .sync_journal import canonical, utc

MAX_JOURNAL_BYTES = 16 * 1024 * 1024
MAX_PAYLOAD_BYTES = 262_144
STATES = {"PREPARED", "UNKNOWN", "VERIFIED", "QUARANTINED"}
SCHEMA = """
CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),binding TEXT NOT NULL,
  last_clock TEXT NOT NULL);
CREATE TABLE evaluation(id INTEGER PRIMARY KEY CHECK(id=1),fingerprint TEXT NOT NULL UNIQUE,
  payload TEXT NOT NULL,digest TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('PREPARED','UNKNOWN','VERIFIED','QUARANTINED')),
  attempts INTEGER NOT NULL CHECK(attempts>=0),created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL);
CREATE TRIGGER immutable_research_evaluation
  BEFORE UPDATE OF fingerprint,payload,digest,created_at ON evaluation
  BEGIN SELECT RAISE(ABORT,'immutable research evaluation'); END;
CREATE TRIGGER retain_research_evaluation BEFORE DELETE ON evaluation
  BEGIN SELECT RAISE(ABORT,'retained research evaluation'); END;
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


class ResearchEvaluationJournalUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("RESEARCH_EVALUATION_JOURNAL_UNAVAILABLE")


@dataclass(frozen=True)
class EvaluationPending:
    fingerprint: str
    state: str
    attempts: int
    envelope: ResearchEvaluationEnvelope


@dataclass(frozen=True)
class EvaluationJournalStatus:
    pending: EvaluationPending
    last_clock: str
    database_bytes: int
    storage: str


class ResearchEvaluationJournal:
    def __init__(
        self,
        directory: Path,
        envelope: ResearchEvaluationEnvelope,
        input_file: Path,
        owner_id: UUID,
        strategy_version_id: int,
        experiment_id: int | None,
        destination: str,
        *,
        create: bool = False,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.directory = directory
        self.path = directory / "research-evaluation.sqlite3"
        self.envelope = envelope
        self.input_file = input_file
        self.owner_id = str(owner_id)
        self.strategy_version_id = strategy_version_id
        self.experiment_id = experiment_id
        self.destination = destination
        self._now = utc_now
        self._lock_fd: int | None = None
        self._pid = os.getpid()
        self.step_lock = threading.Lock()
        self.binding = canonical(
            {
                "input_file": str(input_file),
                "dataset_hash": envelope.dataset_hash,
                "evaluation_fingerprint": envelope.evaluation_fingerprint,
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
                or (
                    experiment_id is not None
                    and (type(experiment_id) is not int or experiment_id <= 0)
                )
                or not input_file.is_absolute()
                or input_file.resolve() != input_file
                or input_file.parent == directory
                or origin(destination) != destination
            ):
                raise ResearchEvaluationJournalUnavailable()
            self._directory()
            if create and any(directory.iterdir()):
                raise ResearchEvaluationJournalUnavailable()
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            lock_path = directory / "research-evaluation.lock"
            self._lock_fd = os.open(
                lock_path, flags | (os.O_CREAT | os.O_EXCL if create else 0), 0o600
            )
            self._lock_identity = self._private_file(lock_path)
            opened = os.fstat(self._lock_fd)
            if (opened.st_dev, opened.st_ino) != self._lock_identity:
                raise ResearchEvaluationJournalUnavailable()
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
            ResearchEvaluationJournalUnavailable,
        ):
            self.close()
            raise ResearchEvaluationJournalUnavailable() from None

    def close(self) -> None:
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None

    def __enter__(self) -> ResearchEvaluationJournal:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _directory(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise ResearchEvaluationJournalUnavailable()
        info = self.directory.lstat()
        identity = (info.st_dev, info.st_ino)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or getattr(self, "_directory_identity", identity) != identity
        ):
            raise ResearchEvaluationJournalUnavailable()
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
            raise ResearchEvaluationJournalUnavailable()
        return info.st_dev, info.st_ino

    def _files(self) -> None:
        self._directory()
        if (
            self._lock_fd is None
            or self._pid != os.getpid()
            or self._private_file(self.directory / "research-evaluation.lock")
            != self._lock_identity
            or self._private_file(self.path) != self._file_identity
        ):
            raise ResearchEvaluationJournalUnavailable()
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
                raise ResearchEvaluationJournalUnavailable()
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA fullfsync=ON")
            db.execute("PRAGMA checkpoint_fullfsync=ON")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            maximum = MAX_JOURNAL_BYTES // page_size
            if (
                db.execute(f"PRAGMA max_page_count={maximum}").fetchone()[0] != maximum
                or db.execute("PRAGMA synchronous").fetchone()[0] != 2
            ):
                raise ResearchEvaluationJournalUnavailable()
            self._files()
            yield db
            self._files()
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise ResearchEvaluationJournalUnavailable() from None
        finally:
            if db is not None:
                db.close()

    def _timestamp(self, previous: str | None = None) -> str:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ResearchEvaluationJournalUnavailable()
        now = now.astimezone(UTC)
        if previous is not None and now < utc(previous):
            raise ResearchEvaluationJournalUnavailable()
        return now.isoformat(timespec="microseconds")

    def _initialize(self, db: sqlite3.Connection) -> None:
        now = self._timestamp()
        if self.envelope.data_cutoff_utc > utc(now):
            raise ResearchEvaluationJournalUnavailable()
        payload = canonical(self.envelope.model_dump(mode="json"))
        if len(payload.encode()) > MAX_PAYLOAD_BYTES:
            raise ResearchEvaluationJournalUnavailable()
        db.executescript("BEGIN IMMEDIATE;" + SCHEMA + "PRAGMA user_version=1;")
        db.execute("INSERT INTO meta VALUES(1,?,?)", (self.binding, now))
        db.execute(
            "INSERT INTO evaluation VALUES(1,?,?,?,'PREPARED',0,?,?)",
            (
                self.envelope.evaluation_fingerprint,
                payload,
                hashlib.sha256(payload.encode()).hexdigest(),
                now,
                now,
            ),
        )
        db.commit()

    def _pending(self, row: sqlite3.Row) -> EvaluationPending:
        payload = row["payload"]
        if (
            row["id"] != 1
            or not isinstance(payload, str)
            or hashlib.sha256(payload.encode()).hexdigest() != row["digest"]
            or row["state"] not in STATES
            or type(row["attempts"]) is not int
            or row["attempts"] < 0
            or (row["state"] in {"UNKNOWN", "VERIFIED"} and row["attempts"] == 0)
            or utc(row["updated_at"]) < utc(row["created_at"])
        ):
            raise ResearchEvaluationJournalUnavailable()
        try:
            envelope = decode_envelope(payload)
        except RuntimeError:
            raise ResearchEvaluationJournalUnavailable() from None
        if (
            row["fingerprint"] != envelope.evaluation_fingerprint
            or envelope != self.envelope
        ):
            raise ResearchEvaluationJournalUnavailable()
        return EvaluationPending(row["fingerprint"], row["state"], row["attempts"], envelope)

    def _state(self, db: sqlite3.Connection) -> EvaluationJournalStatus:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or schema_signature(db) != expected_schema()
        ):
            raise ResearchEvaluationJournalUnavailable()
        meta = db.execute("SELECT * FROM meta LIMIT 2").fetchall()
        rows = db.execute("SELECT * FROM evaluation LIMIT 2").fetchall()
        if (
            len(meta) != 1
            or meta[0]["id"] != 1
            or meta[0]["binding"] != self.binding
            or len(rows) != 1
            or utc(rows[0]["updated_at"]) > utc(meta[0]["last_clock"])
        ):
            raise ResearchEvaluationJournalUnavailable()
        self._timestamp(meta[0]["last_clock"])
        pending = self._pending(rows[0])
        size = (
            db.execute("PRAGMA page_count").fetchone()[0]
            * db.execute("PRAGMA page_size").fetchone()[0]
        )
        storage = (
            "warning_85"
            if size >= MAX_JOURNAL_BYTES * 0.85
            else ("warning_70" if size >= MAX_JOURNAL_BYTES * 0.70 else "normal")
        )
        return EvaluationJournalStatus(pending, meta[0]["last_clock"], size, storage)

    def _audit(self, db: sqlite3.Connection) -> None:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ResearchEvaluationJournalUnavailable()
        self._state(db)

    def status(self) -> EvaluationJournalStatus:
        with self._connect() as db:
            db.execute("BEGIN")
            return self._state(db)

    def _transition(self, fingerprint: str, target: str) -> EvaluationPending:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            pending = state.pending
            allowed = {
                "PREPARED": {"UNKNOWN", "QUARANTINED"},
                "UNKNOWN": {"PREPARED", "VERIFIED", "QUARANTINED"},
            }
            if (
                fingerprint != pending.fingerprint
                or target not in allowed.get(pending.state, set())
            ):
                raise ResearchEvaluationJournalUnavailable()
            now = self._timestamp(state.last_clock)
            attempts = pending.attempts + int(target == "UNKNOWN")
            db.execute(
                "UPDATE evaluation SET state=?,attempts=?,updated_at=? WHERE id=1",
                (target, attempts, now),
            )
            db.execute("UPDATE meta SET last_clock=? WHERE id=1", (now,))
            db.commit()
            return EvaluationPending(fingerprint, target, attempts, pending.envelope)

    def begin_send(self, fingerprint: str) -> EvaluationPending:
        return self._transition(fingerprint, "UNKNOWN")

    def quarantine(self, fingerprint: str) -> EvaluationPending:
        return self._transition(fingerprint, "QUARANTINED")

    def reconcile(self, fingerprint: str, snapshot: object) -> EvaluationPending:
        status = self.status()
        pending = status.pending
        if pending.fingerprint != fingerprint or pending.state != "UNKNOWN":
            raise ResearchEvaluationJournalUnavailable()
        target = "QUARANTINED"
        try:
            if not isinstance(snapshot, dict):
                raise ValueError("invalid read-back")
            if snapshot.get("found") is False:
                if set(snapshot) != {
                    "protocol",
                    "found",
                    "owner_id",
                    "evaluation_fingerprint",
                } or (
                    snapshot["protocol"] != ENVELOPE_READ_PROTOCOL
                    or snapshot["owner_id"] != self.owner_id
                    or snapshot["evaluation_fingerprint"] != fingerprint
                ):
                    raise ValueError("invalid absent read-back")
                target = "PREPARED"
            else:
                expected = {
                    "protocol": ENVELOPE_READ_PROTOCOL,
                    "found": True,
                    "owner_id": self.owner_id,
                    "strategy_version_id": self.strategy_version_id,
                    "experiment_id": self.experiment_id,
                    "evaluation": pending.envelope.model_dump(mode="json"),
                }
                if snapshot == expected:
                    target = "VERIFIED"
        except (ValueError, TypeError, KeyError, RecursionError):
            target = "QUARANTINED"
        return self._transition(fingerprint, target)


ENVELOPE_READ_PROTOCOL = "sochron.research-evaluation-read.v1"
