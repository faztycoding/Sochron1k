"""Read committed SCN-007 M1 evidence without initializing or repairing its archive."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sochron1k.bar_history import MAX_DATABASE_BYTES, ArchivedBar
from sochron1k.chart import EPOCH, ChartSettings
from sochron1k.telemetry import DemoIdentity

from .pa01_aggregation import MAX_SOURCE_ROWS, NativeM1Evidence

MAX_ROWS = 100
MAX_PAYLOAD_BYTES = 8192
MAX_BATCH_BYTES = 240_000
QUERY_SECONDS = 2.0
UTC_TEXT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:Z|\+00:00)\Z"
)
PRICE_TEXT = re.compile(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,2})?\Z")
TABLES = {
    "history_meta": ("id", "binding", "archive_id"),
    "receipts": ("receipt_id", "boot_id", "sequence", "fingerprint", "received_at"),
    "closed_bars": ("timeframe", "time_server_s", "first_receipt", "payload", "digest"),
    "latest_frames": ("timeframe", "receipt_id", "payload"),
}
PRIMARY_KEYS = {
    "history_meta": ("id",),
    "receipts": ("receipt_id",),
    "closed_bars": ("timeframe", "time_server_s"),
    "latest_frames": ("timeframe",),
}


class SourceUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("NATIVE_SOURCE_UNAVAILABLE")


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise ValueError("nonfinite JSON")


def _json(raw: str, maximum: int) -> dict:
    if not isinstance(raw, str) or len(raw.encode()) > maximum:
        raise ValueError("oversized JSON")
    value = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


@dataclass(frozen=True, order=True)
class SourceCursor:
    receipt: int = 0
    time_server_s: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.receipt) is not int
            or type(self.time_server_s) is not int
            or not 0 <= self.receipt <= 9_007_199_254_740_991
            or not 0 <= self.time_server_s <= 4_102_444_800
            or self.time_server_s % 60
            or (self.receipt == 0) != (self.time_server_s == 0)
        ):
            raise ValueError("invalid source cursor")


@dataclass(frozen=True)
class ExportRow:
    cursor: SourceCursor
    payload: str
    available_at: str


START = SourceCursor()


@dataclass(frozen=True)
class ExportBatch:
    archive_id: str
    binding_json: str
    after: SourceCursor
    next_cursor: SourceCursor
    rows: tuple[ExportRow, ...]

    def wire_rows(self) -> list[dict]:
        """Fresh objects preserve exact decimal strings; caller cannot mutate evidence."""
        return [
            {"bar": json.loads(row.payload), "available_at": row.available_at} for row in self.rows
        ]


class NativeArchiveSource:
    def __init__(
        self,
        directory: Path,
        archive_id: UUID,
        identity: DemoIdentity,
        offset_seconds: int,
        chart: ChartSettings,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.directory = directory
        self.path = directory / "bars.sqlite3"
        self.archive_id = str(archive_id)
        self._now = utc_now
        self._offset = offset_seconds
        self._chart = chart
        self.binding_json = json.dumps(
            {
                "identity": identity.model_dump(mode="json"),
                "offset": offset_seconds,
                "chart": chart.model_dump(mode="json"),
            },
            sort_keys=True,
        )
        try:
            if (
                not isinstance(archive_id, UUID)
                or type(offset_seconds) is not int
                or not -50400 <= offset_seconds <= 50400
                or offset_seconds % 60
            ):
                raise SourceUnavailable()
            with self._connect() as db:
                self._metadata(db)
                if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise SourceUnavailable()
                if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise SourceUnavailable()
        except OSError, sqlite3.Error, ValueError, TypeError, RecursionError:
            raise SourceUnavailable() from None

    def _files(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise SourceUnavailable()
        directory = self.directory.lstat()
        if (
            not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.getuid()
            or stat.S_IMODE(directory.st_mode) & 0o077
        ):
            raise SourceUnavailable()
        identity = (directory.st_dev, directory.st_ino)
        if getattr(self, "_directory_identity", identity) != identity:
            raise SourceUnavailable()
        self._directory_identity = identity
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            try:
                info = path.lstat()
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
                raise SourceUnavailable()
            if not suffix:
                identity = (info.st_dev, info.st_ino)
                if getattr(self, "_file_identity", identity) != identity:
                    raise SourceUnavailable()
                self._file_identity = identity

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._files()
        db = sqlite3.connect(
            self.path.as_uri() + "?mode=ro", uri=True, timeout=0.1, isolation_level=None
        )
        try:
            db.row_factory = sqlite3.Row
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 262_144)
            db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA query_only=ON")
            deadline = time.monotonic() + QUERY_SECONDS
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            self._files()
            db.execute("BEGIN")
            yield db
            self._files()
        finally:
            db.close()

    def _metadata(self, db: sqlite3.Connection) -> None:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or db.execute("PRAGMA journal_mode").fetchone()[0] != "wal"
            or db.execute("PRAGMA page_count").fetchone()[0]
            * db.execute("PRAGMA page_size").fetchone()[0]
            > MAX_DATABASE_BYTES
        ):
            raise SourceUnavailable()
        tables = {
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables != TABLES.keys():
            raise SourceUnavailable()
        for table, columns in TABLES.items():
            layout = db.execute(f"PRAGMA table_xinfo({table})").fetchall()
            if tuple(r[1] for r in layout) != columns:
                raise SourceUnavailable()
            integers = {"id", "receipt_id", "sequence", "time_server_s", "first_receipt"}
            for column in layout:
                name = column[1]
                primary = PRIMARY_KEYS[table]
                expected_pk = primary.index(name) + 1 if name in primary else 0
                nullable_pk = (table, name) in {
                    ("history_meta", "id"),
                    ("receipts", "receipt_id"),
                    ("latest_frames", "timeframe"),
                }
                if (
                    column[2] != ("INTEGER" if name in integers else "TEXT")
                    or column[3] != int(not nullable_pk)
                    or column[4] is not None
                    or column[5] != expected_pk
                    or column[6]
                ):
                    raise SourceUnavailable()
        for table in ("bars", "receipts"):
            target = "closed_bars" if table == "bars" else "receipts"
            for operation in ("update", "delete"):
                name = f"immutable_{table}_{operation}"
                trigger = db.execute(
                    "SELECT sql FROM sqlite_schema WHERE type='trigger' AND name=? AND tbl_name=?",
                    (name, target),
                ).fetchone()
                message = "immutable history" if table == "bars" else "immutable receipt"
                expected = (
                    f"create trigger {name} before {operation} on {target} "
                    f"begin select raise(abort, '{message}'); end"
                )
                if (
                    trigger is None
                    or not isinstance(trigger[0], str)
                    or " ".join(trigger[0].split()).lower().rstrip(";") != expected
                ):
                    raise SourceUnavailable()
        meta = db.execute(
            "SELECT substr(binding,1,4097), substr(archive_id,1,37) FROM history_meta LIMIT 2"
        ).fetchall()
        if (
            len(meta) != 1
            or meta[0][1] != self.archive_id
            or json.dumps(_json(meta[0][0], 4096), sort_keys=True) != self.binding_json
        ):
            raise SourceUnavailable()

    def _bar(self, row: sqlite3.Row) -> tuple[SourceCursor, str, datetime]:
        raw = row["payload"]
        payload = _json(raw, MAX_PAYLOAD_BYTES)
        if (
            hashlib.sha256(raw.encode()).hexdigest() != row["digest"]
            or payload.get("closed") is not True
        ):
            raise SourceUnavailable()
        bar = ArchivedBar.model_validate_json(raw)
        for key in ("open_time_utc", "source_observed_at", "first_received_at"):
            if not isinstance(payload[key], str) or not UTC_TEXT.fullmatch(payload[key]):
                raise SourceUnavailable()
        receipt_time = row["received_at"]
        if not isinstance(receipt_time, str) or not UTC_TEXT.fullmatch(receipt_time):
            raise SourceUnavailable()
        if (
            bar.time_server_s != row["time_server_s"]
            or bar.first_receipt != row["first_receipt"]
            or bar.terminal_build > 9_007_199_254_740_991
            or bar.broker_utc_offset_seconds != self._offset
            or not self._chart.offset_valid_from_server_s
            <= bar.time_server_s
            < bar.confirmed_by_server_s
            < self._chart.offset_valid_until_server_s
            or bar.confirmed_by_server_s % 60
            or bar.open_time_utc != EPOCH + timedelta(seconds=bar.time_server_s - self._offset)
            or bar.source_observed_at
            < EPOCH + timedelta(seconds=bar.confirmed_by_server_s - self._offset)
            or bar.first_received_at < bar.source_observed_at
            or datetime.fromisoformat(receipt_time) != bar.first_received_at
        ):
            raise SourceUnavailable()
        for key in ("open", "high", "low", "close", "tick_size"):
            if (
                not isinstance(payload[key], str)
                or len(payload[key]) > 40
                or not PRICE_TEXT.fullmatch(payload[key])
            ):
                raise SourceUnavailable()
            if key != "tick_size":
                numerator, denominator = getattr(bar, key).as_integer_ratio()
                tick_numerator, tick_denominator = bar.tick_size.as_integer_ratio()
                if (
                    numerator * tick_denominator % (denominator * tick_numerator)
                    or numerator * 10**bar.digits % denominator
                ):
                    raise SourceUnavailable()
        return SourceCursor(bar.first_receipt, bar.time_server_s), raw, bar.first_received_at

    def read(self, after: SourceCursor = START, limit: int = MAX_ROWS) -> ExportBatch:
        try:
            if (
                not isinstance(after, SourceCursor)
                or type(limit) is not int
                or not 1 <= limit <= MAX_ROWS
            ):
                raise SourceUnavailable()
            with self._connect() as db:
                self._metadata(db)
                projection = """
                    SELECT c.time_server_s,c.first_receipt,substr(c.payload,1,8193) AS payload,
                           substr(c.digest,1,65) AS digest,
                           substr(r.received_at,1,128) AS received_at
                    FROM closed_bars c LEFT JOIN receipts r ON r.receipt_id=c.first_receipt
                    WHERE c.timeframe='M1'
                """
                if after != SourceCursor():
                    boundary = db.execute(
                        projection + " AND (c.first_receipt,c.time_server_s)=(?,?)",
                        (after.receipt, after.time_server_s),
                    ).fetchone()
                    if boundary is None:
                        raise SourceUnavailable()
                    self._bar(boundary)
                rows = db.execute(
                    projection + " AND (c.first_receipt,c.time_server_s)>(?,?) "
                    "ORDER BY c.first_receipt,c.time_server_s LIMIT ?",
                    (after.receipt, after.time_server_s, limit),
                ).fetchall()
                verified = [self._bar(row) for row in rows]
                # Taken after fetching the committed snapshot, never before source commit.
                observed = self._now()
                if observed.tzinfo is None or observed.utcoffset() is None:
                    raise SourceUnavailable()
                observed = observed.astimezone(UTC)
                available = observed.isoformat(timespec="microseconds")
                exported: list[ExportRow] = []
                next_cursor = after
                size = 2
                for cursor, payload, received in verified:
                    if observed < received or cursor <= next_cursor:
                        raise SourceUnavailable()
                    wire = json.dumps({"bar": json.loads(payload), "available_at": available})
                    size += len(wire.encode()) + 2
                    if size > MAX_BATCH_BYTES:
                        break
                    exported.append(ExportRow(cursor, payload, available))
                    next_cursor = cursor
                result = ExportBatch(
                    self.archive_id, self.binding_json, after, next_cursor, tuple(exported)
                )
            return result
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise SourceUnavailable() from None

    def read_pa01(
        self, cutoff_utc: datetime, *, limit: int = MAX_SOURCE_ROWS
    ) -> tuple[NativeM1Evidence, ...]:
        """Read the newest bounded M1 evidence available at one explicit cutoff."""
        try:
            if (
                not isinstance(cutoff_utc, datetime)
                or cutoff_utc.tzinfo is None
                or cutoff_utc.utcoffset() is None
                or type(limit) is not int
                or not 1 <= limit <= MAX_SOURCE_ROWS
            ):
                raise SourceUnavailable()
            cutoff = cutoff_utc.astimezone(UTC)
            cutoff_text = cutoff.isoformat(timespec="microseconds")
            latest_open_server_s = int(cutoff.timestamp()) + self._offset - 60
            with self._connect() as db:
                self._metadata(db)
                rows = db.execute(
                    """
                    SELECT c.time_server_s,c.first_receipt,
                           substr(c.payload,1,8193) AS payload,
                           substr(c.digest,1,65) AS digest,
                           substr(r.received_at,1,128) AS received_at
                    FROM closed_bars c
                    LEFT JOIN receipts r ON r.receipt_id=c.first_receipt
                    WHERE c.timeframe='M1'
                      AND c.time_server_s<=?
                      AND r.received_at<=?
                    ORDER BY c.time_server_s DESC
                    LIMIT ?
                    """,
                    (latest_open_server_s, cutoff_text, limit),
                ).fetchall()
                verified = [self._bar(row) for row in reversed(rows)]
                binding = _json(self.binding_json, 4096)
                identity = DemoIdentity.model_validate(binding["identity"])
                result = tuple(
                    NativeM1Evidence(
                        archive_id=UUID(self.archive_id),
                        symbol=identity.symbol,
                        time_server_s=bar.time_server_s,
                        broker_utc_offset_seconds=self._offset,
                        offset_valid_from_server_s=self._chart.offset_valid_from_server_s,
                        offset_valid_until_server_s=self._chart.offset_valid_until_server_s,
                        open_time_utc=bar.open_time_utc,
                        confirmed_by_server_s=bar.confirmed_by_server_s,
                        source_observed_at_utc=bar.source_observed_at,
                        first_received_at_utc=bar.first_received_at,
                        available_at_utc=bar.first_received_at,
                        first_receipt=bar.first_receipt,
                        terminal_build=bar.terminal_build,
                        open=bar.open,
                        high=bar.high,
                        low=bar.low,
                        close=bar.close,
                        tick_volume=bar.tick_volume,
                        spread_points=bar.spread_points,
                        tick_size=bar.tick_size,
                        digits=bar.digits,
                    )
                    for _, payload, _ in verified
                    for bar in (ArchivedBar.model_validate_json(payload),)
                )
            if any(row.available_at_utc > cutoff or row.close_time_utc > cutoff for row in result):
                raise SourceUnavailable()
            return result
        except OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise SourceUnavailable() from None
