"""Local closed-bar capture spool; not tick history or strategy execution evidence."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import AwareDatetime, Field, StrictInt

from .chart import (
    PERIODS,
    ChartBar,
    ChartFrame,
    ChartGap,
    ChartObservation,
    ChartSettings,
    Timeframe,
)
from .models import StrictModel
from .telemetry import BridgeDenied, BridgeSettings, DemoIdentity, FiniteDecimal

MAX_DATABASE_BYTES = 128 * 1024 * 1024


class HistoryUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("HISTORY_UNAVAILABLE")


class ArchivedBar(ChartBar):
    closed: Literal[True] = True
    confirmed_by_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    first_receipt: StrictInt = Field(ge=1)
    first_received_at: AwareDatetime
    source_observed_at: AwareDatetime
    terminal_build: StrictInt = Field(gt=0)
    price_basis: Literal["bid", "last"]
    digits: StrictInt = Field(ge=0, le=10)
    tick_size: FiniteDecimal = Field(gt=0)
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)


class HistoryView(StrictModel):
    state: Literal["disabled", "available"]
    archive_id: str | None = None
    identity: DemoIdentity | None = None
    source: Literal["mt5-copyrates"] = "mt5-copyrates"
    through_receipt: int = 0
    timeframe: Timeframe
    bars: tuple[ArchivedBar, ...] = ()
    gaps: tuple[ChartGap, ...] = ()
    database_bytes: int = 0
    quota_bytes: int = MAX_DATABASE_BYTES
    storage: Literal["normal", "warning_70", "warning_85"] = "normal"
    execution_ready: Literal[False] = False


def _utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware time required")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


class BarHistory:
    """One private archive per pinned Demo identity/configuration; no external I/O."""

    def __init__(self, directory: Path, bridge: BridgeSettings, chart: ChartSettings) -> None:
        self.directory = directory
        self.path = directory / "bars.sqlite3"
        self.identity = bridge.identity
        self._binding = json.dumps(
            {
                "identity": bridge.identity.model_dump(mode="json"),
                "offset": bridge.broker_utc_offset_seconds,
                "chart": chart.model_dump(mode="json"),
            },
            sort_keys=True,
        )
        try:
            self._private_directory()
            created = False
            try:
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
                )
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
                created = True
            with self._connect() as db:
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if created:
                    self._initialize(db)
                elif version != 1:
                    raise HistoryUnavailable()
                if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise HistoryUnavailable()
                if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise HistoryUnavailable()
                meta = db.execute(
                    "SELECT binding, archive_id FROM history_meta WHERE id=1"
                ).fetchone()
                if meta is None or meta["binding"] != self._binding:
                    raise HistoryUnavailable()
                self.archive_id = meta["archive_id"]
                for row in db.execute("SELECT * FROM closed_bars"):
                    self._read_bar(row)
            self.latest_frames()  # Validate saved projection before the API can start.
        except OSError, sqlite3.Error, ValueError:
            raise HistoryUnavailable() from None

    def _private_directory(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise HistoryUnavailable()
        info = self.directory.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise HistoryUnavailable()
        observed = (info.st_dev, info.st_ino)
        if getattr(self, "_directory_identity", observed) != observed:
            raise HistoryUnavailable()
        self._directory_identity = observed

    def _private_files(self) -> None:
        self._private_directory()
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            try:
                info = candidate.lstat()
            except FileNotFoundError:
                if suffix:
                    continue
                raise
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise HistoryUnavailable()
            if not suffix:
                observed = (info.st_dev, info.st_ino)
                if getattr(self, "_file_identity", observed) != observed:
                    raise HistoryUnavailable()
                self._file_identity = observed

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._private_files()
        # mode=rw refuses to silently recreate a removed archive after startup.
        db = sqlite3.connect(
            self.path.as_uri() + "?mode=rw", uri=True, timeout=0.1, isolation_level=None
        )
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise HistoryUnavailable()
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA fullfsync=ON")
            db.execute("PRAGMA checkpoint_fullfsync=ON")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            maximum = MAX_DATABASE_BYTES // page_size
            if db.execute(f"PRAGMA max_page_count={maximum}").fetchone()[0] != maximum:
                raise HistoryUnavailable()
            if db.execute("PRAGMA synchronous").fetchone()[0] != 2:
                raise HistoryUnavailable()
            self._private_files()
            yield db
        finally:
            db.close()  # Unlike Connection's context manager, always release the handle.

    def _initialize(self, db: sqlite3.Connection) -> None:
        db.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE history_meta (
                id INTEGER PRIMARY KEY CHECK(id=1), binding TEXT NOT NULL,
                archive_id TEXT NOT NULL
            );
            CREATE TABLE receipts (
                receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                boot_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, received_at TEXT NOT NULL,
                UNIQUE(boot_id, sequence)
            );
            CREATE TABLE closed_bars (
                timeframe TEXT NOT NULL, time_server_s INTEGER NOT NULL,
                first_receipt INTEGER NOT NULL REFERENCES receipts(receipt_id),
                payload TEXT NOT NULL, digest TEXT NOT NULL,
                PRIMARY KEY(timeframe, time_server_s)
            );
            CREATE TABLE latest_frames (
                timeframe TEXT PRIMARY KEY,
                receipt_id INTEGER NOT NULL REFERENCES receipts(receipt_id),
                payload TEXT NOT NULL
            );
            CREATE TRIGGER immutable_bars_update BEFORE UPDATE ON closed_bars
                BEGIN SELECT RAISE(ABORT, 'immutable history'); END;
            CREATE TRIGGER immutable_bars_delete BEFORE DELETE ON closed_bars
                BEGIN SELECT RAISE(ABORT, 'immutable history'); END;
            CREATE TRIGGER immutable_receipts_update BEFORE UPDATE ON receipts
                BEGIN SELECT RAISE(ABORT, 'immutable receipt'); END;
            CREATE TRIGGER immutable_receipts_delete BEFORE DELETE ON receipts
                BEGIN SELECT RAISE(ABORT, 'immutable receipt'); END;
        """)
        db.execute("INSERT INTO history_meta VALUES (1, ?, ?)", (self._binding, str(uuid4())))
        db.execute("PRAGMA user_version=1")
        db.commit()

    def latest_frames(self) -> dict[str, ChartFrame]:
        try:
            with self._connect() as db:
                rows = db.execute("""
                    SELECT l.timeframe, l.payload, r.fingerprint
                    FROM latest_frames l JOIN receipts r USING(receipt_id)
                """).fetchall()
                frames = {}
                for row in rows:
                    if hashlib.sha256(row["payload"].encode()).hexdigest() != row["fingerprint"]:
                        raise HistoryUnavailable()
                    frame = ChartFrame.model_validate_json(row["payload"])
                    binding = json.loads(self._binding)
                    if (
                        frame.timeframe != row["timeframe"]
                        or frame.identity.model_dump(mode="json") != binding["identity"]
                        or frame.broker_utc_offset_seconds != binding["offset"]
                    ):
                        raise HistoryUnavailable()
                    frames[frame.timeframe] = frame
                return frames
        except OSError, sqlite3.Error, ValueError:
            raise HistoryUnavailable() from None

    @staticmethod
    def _read_bar(row: sqlite3.Row) -> ArchivedBar:
        if hashlib.sha256(row["payload"].encode()).hexdigest() != row["digest"]:
            raise HistoryUnavailable()
        bar = ArchivedBar.model_validate_json(row["payload"])
        if (
            not bar.closed
            or bar.time_server_s != row["time_server_s"]
            or bar.first_receipt != row["first_receipt"]
            or bar.confirmed_by_server_s <= bar.time_server_s
            or bar.open_time_utc.timestamp() != bar.time_server_s - bar.broker_utc_offset_seconds
            or bar.first_received_at < bar.source_observed_at
        ):
            raise HistoryUnavailable()
        return bar

    def record(self, frame: ChartFrame, observation: ChartObservation) -> int:
        """Called only after chart validation; commit before publishing or acknowledging."""
        payload = frame.model_dump_json()
        binding = json.loads(self._binding)
        if (
            frame.identity.model_dump(mode="json") != binding["identity"]
            or frame.broker_utc_offset_seconds != binding["offset"]
            or observation.identity != frame.identity
            or observation.sequence != frame.sequence
            or observation.timeframe != frame.timeframe
        ):
            raise BridgeDenied("HISTORY_IDENTITY_MISMATCH")
        fingerprint = hashlib.sha256(payload.encode()).hexdigest()
        received = _utc(observation.received_time_utc)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute(
                    "SELECT * FROM receipts WHERE boot_id=? AND sequence=?",
                    (str(frame.boot_id), frame.sequence),
                ).fetchone()
                if old is not None:
                    if old["fingerprint"] != fingerprint:
                        raise BridgeDenied("HISTORY_RECEIPT_CONFLICT")
                    db.rollback()
                    return old["receipt_id"]
                last = db.execute(
                    "SELECT received_at FROM receipts ORDER BY receipt_id DESC LIMIT 1"
                ).fetchone()
                if last is not None and received < last["received_at"]:
                    raise BridgeDenied("HISTORY_CLOCK_REVERSED")
                cursor = db.execute(
                    """
                    INSERT INTO receipts(boot_id, sequence, fingerprint, received_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (str(frame.boot_id), frame.sequence, fingerprint, received),
                )
                receipt_id = cursor.lastrowid
                for index, bar in enumerate(observation.bars):
                    existing = db.execute(
                        "SELECT * FROM closed_bars WHERE timeframe=? AND time_server_s=?",
                        (frame.timeframe, bar.time_server_s),
                    ).fetchone()
                    if existing is not None:
                        archived = self._read_bar(existing)
                        if (
                            ChartBar.model_validate(
                                archived.model_dump(include=set(ChartBar.model_fields))
                            )
                            != bar
                            or archived.price_basis != frame.price_basis
                            or archived.digits != frame.digits
                            or archived.tick_size != frame.tick_size
                            or archived.broker_utc_offset_seconds != frame.broker_utc_offset_seconds
                        ):
                            raise BridgeDenied("HISTORY_CLOSED_BAR_CHANGED")
                    elif bar.closed:
                        archived = ArchivedBar(
                            **bar.model_dump(),
                            confirmed_by_server_s=observation.bars[index + 1].time_server_s,
                            first_receipt=receipt_id,
                            first_received_at=observation.received_time_utc,
                            source_observed_at=frame.observed_at,
                            terminal_build=frame.terminal_build,
                            price_basis=frame.price_basis,
                            digits=frame.digits,
                            tick_size=frame.tick_size,
                            broker_utc_offset_seconds=frame.broker_utc_offset_seconds,
                        )
                        encoded = archived.model_dump_json()
                        db.execute(
                            "INSERT INTO closed_bars VALUES (?, ?, ?, ?, ?)",
                            (
                                frame.timeframe,
                                bar.time_server_s,
                                receipt_id,
                                encoded,
                                hashlib.sha256(encoded.encode()).hexdigest(),
                            ),
                        )
                db.execute(
                    """
                    INSERT INTO latest_frames VALUES (?, ?, ?)
                    ON CONFLICT(timeframe) DO UPDATE SET
                        receipt_id=excluded.receipt_id, payload=excluded.payload
                """,
                    (frame.timeframe, receipt_id, payload),
                )
                db.commit()
                return receipt_id
        except (OSError, sqlite3.Error, ValueError) as error:
            if isinstance(error, BridgeDenied):
                raise
            raise HistoryUnavailable() from None

    def read(
        self,
        timeframe: Timeframe,
        *,
        after_server_s: int = 0,
        through_receipt: int | None = None,
        archive_id: str | None = None,
        limit: int = 240,
    ) -> HistoryView:
        if limit < 1 or limit > 240 or after_server_s < 0 or timeframe not in PERIODS:
            raise ValueError("invalid history range")
        if through_receipt is not None and archive_id is None:
            raise BridgeDenied("HISTORY_ARCHIVE_REQUIRED")
        if archive_id is not None and archive_id != self.archive_id:
            raise BridgeDenied("HISTORY_ARCHIVE_MISMATCH")
        try:
            with self._connect() as db:
                db.execute("BEGIN")
                latest = db.execute("SELECT COALESCE(MAX(receipt_id),0) FROM receipts").fetchone()[
                    0
                ]
                cutoff = latest if through_receipt is None else through_receipt
                if cutoff < 0 or cutoff > latest:
                    raise BridgeDenied("HISTORY_WATERMARK_INVALID")
                rows = db.execute(
                    """
                    SELECT * FROM closed_bars WHERE timeframe=? AND time_server_s>?
                    AND first_receipt<=? ORDER BY time_server_s LIMIT ?
                """,
                    (timeframe, after_server_s, cutoff, limit),
                ).fetchall()
                previous = db.execute(
                    """
                    SELECT * FROM closed_bars WHERE timeframe=? AND time_server_s<=?
                    AND first_receipt<=? ORDER BY time_server_s DESC LIMIT 1
                """,
                    (timeframe, after_server_s, cutoff),
                ).fetchone()
                bars = tuple(self._read_bar(row) for row in rows)
                neighbors = ((self._read_bar(previous),) if previous is not None else ()) + bars
                gaps = tuple(
                    ChartGap(
                        after_open_time_utc=left.open_time_utc,
                        before_open_time_utc=right.open_time_utc,
                        missing_intervals=(right.time_server_s - left.time_server_s)
                        // PERIODS[timeframe]
                        - 1,
                    )
                    for left, right in pairwise(neighbors)
                    if right.time_server_s - left.time_server_s > PERIODS[timeframe]
                )
                size = (
                    db.execute("PRAGMA page_count").fetchone()[0]
                    * db.execute("PRAGMA page_size").fetchone()[0]
                )
                return HistoryView(
                    state="available",
                    archive_id=self.archive_id,
                    identity=self.identity,
                    timeframe=timeframe,
                    through_receipt=cutoff,
                    bars=bars,
                    gaps=gaps,
                    database_bytes=size,
                    quota_bytes=MAX_DATABASE_BYTES,
                    storage="warning_85"
                    if size >= MAX_DATABASE_BYTES * 0.85
                    else "warning_70"
                    if size >= MAX_DATABASE_BYTES * 0.70
                    else "normal",
                )
        except (OSError, sqlite3.Error, ValueError) as error:
            if isinstance(error, BridgeDenied):
                raise
            raise HistoryUnavailable() from None
