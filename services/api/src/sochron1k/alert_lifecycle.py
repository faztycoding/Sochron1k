"""Durable owner workflow for redacted operational alerts; no delivery authority."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from .models import StrictModel
from .operational_alerts import (
    LIFECYCLE_ORDER,
    SEVERITY_ORDER,
    AlertCoverage,
    OperationalAlert,
    OperationalAlertInventory,
)

MAX_JOURNAL_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 64
SCHEMA = """
CREATE TABLE lifecycle_meta(
  id INTEGER PRIMARY KEY CHECK(id=1), last_clock TEXT NOT NULL
);
CREATE TABLE alert_lifecycle(
  owner_id TEXT NOT NULL,
  condition_id TEXT NOT NULL,
  alert_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  severity TEXT NOT NULL,
  source TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  detail_code TEXT NOT NULL,
  observed_at_utc TEXT NOT NULL,
  evidence_routes_json TEXT NOT NULL,
  acknowledged_at_utc TEXT NOT NULL,
  resolved_at_utc TEXT,
  updated_at_utc TEXT NOT NULL,
  snapshot_digest TEXT NOT NULL,
  PRIMARY KEY(owner_id, condition_id)
);
CREATE TABLE lifecycle_receipts(
  idempotency_key TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK(action IN ('acknowledge','resolve')),
  condition_id TEXT NOT NULL,
  request_fingerprint TEXT NOT NULL,
  acknowledged_at_utc TEXT NOT NULL,
  resolved_at_utc TEXT,
  committed_at_utc TEXT NOT NULL,
  receipt_digest TEXT NOT NULL
);
CREATE TRIGGER immutable_lifecycle_receipt_update BEFORE UPDATE ON lifecycle_receipts
  BEGIN SELECT RAISE(ABORT,'immutable lifecycle receipt'); END;
CREATE TRIGGER immutable_lifecycle_receipt_delete BEFORE DELETE ON lifecycle_receipts
  BEGIN SELECT RAISE(ABORT,'retained lifecycle receipt'); END;
"""


class AlertLifecycleUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_LIFECYCLE_UNAVAILABLE")


class AlertLifecycleConflict(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AlertMutationReceipt(StrictModel):
    protocol: Literal["sochron.alert-mutation.v1"] = "sochron.alert-mutation.v1"
    action: Literal["acknowledge", "resolve"]
    condition_id: str = Field(min_length=24, max_length=24, pattern=r"^[0-9a-f]{24}$")
    lifecycle_state: Literal["acknowledged", "resolved"]
    acknowledged_at_utc: AwareDatetime
    resolved_at_utc: AwareDatetime | None = None

    @field_validator("acknowledged_at_utc", "resolved_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def coherent_result(self) -> AlertMutationReceipt:
        if self.action == "acknowledge" and (
            self.lifecycle_state != "acknowledged" or self.resolved_at_utc is not None
        ):
            raise ValueError("incoherent acknowledgement receipt")
        if self.action == "resolve" and (
            self.lifecycle_state != "resolved"
            or self.resolved_at_utc is None
            or self.resolved_at_utc < self.acknowledged_at_utc
        ):
            raise ValueError("incoherent resolution receipt")
        return self


class LifecycleRecord(StrictModel):
    owner_id: UUID
    condition_id: str = Field(min_length=24, max_length=24, pattern=r"^[0-9a-f]{24}$")
    alert: OperationalAlert
    updated_at_utc: AwareDatetime


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _schema_signature(db: sqlite3.Connection) -> tuple[tuple[object, ...], ...]:
    return tuple(
        tuple(row)
        for row in db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name"
        )
    )


@cache
def _expected_schema() -> tuple[tuple[object, ...], ...]:
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(SCHEMA)
        return _schema_signature(db)
    finally:
        db.close()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("aware UTC time required")
    normalized = parsed.astimezone(UTC)
    if normalized.isoformat(timespec="microseconds") != value:
        raise ValueError("canonical UTC time required")
    return normalized


def _uuid(value: str) -> UUID:
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("canonical UUID required")
    return parsed


def _snapshot(alert: OperationalAlert) -> dict[str, object]:
    return {
        "alert_id": alert.id,
        "condition_id": alert.condition_id,
        "kind": alert.kind,
        "severity": alert.severity,
        "source": alert.source,
        "source_ref": alert.source_ref,
        "detail_code": alert.detail_code,
        "observed_at_utc": alert.observed_at_utc.isoformat(timespec="microseconds"),
        "evidence_routes": list(alert.evidence_routes),
    }


class AlertLifecycleJournal:
    """One private bounded lifecycle journal; never a detector or delivery source."""

    def __init__(
        self,
        directory: Path,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.directory = directory
        self.path = directory / "alerts.sqlite3"
        self._now = utc_now
        try:
            self._private_directory()
            created = False
            try:
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600
                )
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
                created = True
            self._file_identity = self._private_file(self.path)
            with self._connect() as db:
                if created:
                    self._initialize(db)
                self._audit(db)
            if created:
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
            AlertLifecycleUnavailable,
        ):
            raise AlertLifecycleUnavailable() from None

    def _private_directory(self) -> None:
        if not self.directory.is_absolute() or self.directory.resolve() != self.directory:
            raise AlertLifecycleUnavailable()
        info = self.directory.lstat()
        identity = (info.st_dev, info.st_ino)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or getattr(self, "_directory_identity", identity) != identity
        ):
            raise AlertLifecycleUnavailable()
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
            raise AlertLifecycleUnavailable()
        return info.st_dev, info.st_ino

    def _private_files(self) -> None:
        self._private_directory()
        if self._private_file(self.path) != self._file_identity:
            raise AlertLifecycleUnavailable()
        for suffix in ("-wal", "-shm"):
            with suppress(FileNotFoundError):
                self._private_file(Path(str(self.path) + suffix))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db: sqlite3.Connection | None = None
        try:
            self._private_files()
            db = sqlite3.connect(
                self.path.as_uri() + "?mode=rw",
                uri=True,
                timeout=0.1,
                isolation_level=None,
            )
            db.row_factory = sqlite3.Row
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 262_144)
            db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=100")
            if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise AlertLifecycleUnavailable()
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA fullfsync=ON")
            db.execute("PRAGMA checkpoint_fullfsync=ON")
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            maximum = MAX_JOURNAL_BYTES // page_size
            if (
                db.execute(f"PRAGMA max_page_count={maximum}").fetchone()[0] != maximum
                or db.execute("PRAGMA synchronous").fetchone()[0] != 2
            ):
                raise AlertLifecycleUnavailable()
            self._private_files()
            yield db
            self._private_files()
        except (
            OSError,
            sqlite3.Error,
            ValueError,
            TypeError,
            KeyError,
            RecursionError,
        ):
            raise AlertLifecycleUnavailable() from None
        finally:
            if db is not None:
                db.close()

    def _initialize(self, db: sqlite3.Connection) -> None:
        now = self._timestamp()
        db.executescript("BEGIN IMMEDIATE;" + SCHEMA + "PRAGMA user_version=1;")
        db.execute("INSERT INTO lifecycle_meta VALUES(1,?)", (now,))
        db.commit()

    def _timestamp(self, previous: str | None = None) -> str:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise AlertLifecycleUnavailable()
        value = now.astimezone(UTC).isoformat(timespec="microseconds")
        if previous is not None and _utc(value) < _utc(previous):
            raise AlertLifecycleUnavailable()
        return value

    def _audit(self, db: sqlite3.Connection) -> None:
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != 1
            or db.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchone() is not None
            or _schema_signature(db) != _expected_schema()
        ):
            raise AlertLifecycleUnavailable()
        meta = db.execute("SELECT * FROM lifecycle_meta LIMIT 2").fetchall()
        if len(meta) != 1 or meta[0]["id"] != 1:
            raise AlertLifecycleUnavailable()
        self._timestamp(meta[0]["last_clock"])
        for row in db.execute("SELECT * FROM alert_lifecycle"):
            self._record(row)
        for row in db.execute("SELECT * FROM lifecycle_receipts"):
            self._receipt(row)

    @staticmethod
    def _request_fingerprint(owner: UUID, action: str, condition_id: str) -> str:
        return _digest(
            {"owner_id": str(owner), "action": action, "condition_id": condition_id}
        )

    @staticmethod
    def _receipt_payload(row: sqlite3.Row) -> dict[str, object]:
        return {
            "idempotency_key": row["idempotency_key"],
            "owner_id": row["owner_id"],
            "action": row["action"],
            "condition_id": row["condition_id"],
            "request_fingerprint": row["request_fingerprint"],
            "acknowledged_at_utc": row["acknowledged_at_utc"],
            "resolved_at_utc": row["resolved_at_utc"],
            "committed_at_utc": row["committed_at_utc"],
        }

    def _receipt(self, row: sqlite3.Row) -> AlertMutationReceipt:
        payload = self._receipt_payload(row)
        _uuid(row["idempotency_key"])
        _uuid(row["owner_id"])
        acknowledged = _utc(row["acknowledged_at_utc"])
        resolved = _utc(row["resolved_at_utc"]) if row["resolved_at_utc"] else None
        committed = _utc(row["committed_at_utc"])
        if (
            row["action"] not in {"acknowledge", "resolve"}
            or row["request_fingerprint"]
            != self._request_fingerprint(
                UUID(row["owner_id"]), row["action"], row["condition_id"]
            )
            or row["receipt_digest"] != _digest(payload)
            or committed < acknowledged
            or (resolved is not None and (resolved < acknowledged or committed < resolved))
            or (row["action"] == "acknowledge") != (resolved is None)
        ):
            raise AlertLifecycleUnavailable()
        return AlertMutationReceipt(
            action=row["action"],
            condition_id=row["condition_id"],
            lifecycle_state="resolved" if resolved else "acknowledged",
            acknowledged_at_utc=acknowledged,
            resolved_at_utc=resolved,
        )

    def _record(self, row: sqlite3.Row) -> LifecycleRecord:
        owner = _uuid(row["owner_id"])
        observed = _utc(row["observed_at_utc"])
        acknowledged = _utc(row["acknowledged_at_utc"])
        resolved = _utc(row["resolved_at_utc"]) if row["resolved_at_utc"] else None
        updated = _utc(row["updated_at_utc"])
        routes = json.loads(row["evidence_routes_json"])
        snapshot = {
            "alert_id": row["alert_id"],
            "condition_id": row["condition_id"],
            "kind": row["kind"],
            "severity": row["severity"],
            "source": row["source"],
            "source_ref": row["source_ref"],
            "detail_code": row["detail_code"],
            "observed_at_utc": row["observed_at_utc"],
            "evidence_routes": routes,
        }
        if (
            not isinstance(routes, list)
            or row["snapshot_digest"] != _digest(snapshot)
            or acknowledged < observed
            or updated < acknowledged
            or (resolved is not None and (resolved < acknowledged or updated < resolved))
        ):
            raise AlertLifecycleUnavailable()
        alert = OperationalAlert(
            id=row["alert_id"],
            condition_id=row["condition_id"],
            kind=row["kind"],
            severity=row["severity"],
            source=row["source"],
            source_ref=row["source_ref"],
            detail_code=row["detail_code"],
            observed_at_utc=observed,
            evidence_routes=tuple(routes),
            lifecycle_state="resolved" if resolved else "acknowledged",
            acknowledged_by="owner",
            acknowledged_at_utc=acknowledged,
            resolved_at_utc=resolved,
        )
        return LifecycleRecord(
            owner_id=owner,
            condition_id=row["condition_id"],
            alert=alert,
            updated_at_utc=updated,
        )

    def _existing_receipt(
        self,
        db: sqlite3.Connection,
        owner: UUID,
        action: Literal["acknowledge", "resolve"],
        condition_id: str,
        idempotency_key: UUID,
    ) -> AlertMutationReceipt | None:
        row = db.execute(
            "SELECT * FROM lifecycle_receipts WHERE idempotency_key=?",
            (str(idempotency_key),),
        ).fetchone()
        if row is None:
            return None
        if (
            row["owner_id"] != str(owner)
            or row["action"] != action
            or row["condition_id"] != condition_id
        ):
            raise AlertLifecycleConflict("IDEMPOTENCY_CONFLICT")
        return self._receipt(row)

    def _insert_receipt(
        self,
        db: sqlite3.Connection,
        *,
        owner: UUID,
        action: Literal["acknowledge", "resolve"],
        condition_id: str,
        idempotency_key: UUID,
        acknowledged_at: str,
        resolved_at: str | None,
        committed_at: str,
    ) -> AlertMutationReceipt:
        payload = {
            "idempotency_key": str(idempotency_key),
            "owner_id": str(owner),
            "action": action,
            "condition_id": condition_id,
            "request_fingerprint": self._request_fingerprint(owner, action, condition_id),
            "acknowledged_at_utc": acknowledged_at,
            "resolved_at_utc": resolved_at,
            "committed_at_utc": committed_at,
        }
        db.execute(
            """
            INSERT INTO lifecycle_receipts(
              idempotency_key,owner_id,action,condition_id,request_fingerprint,
              acknowledged_at_utc,resolved_at_utc,committed_at_utc,receipt_digest
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (*payload.values(), _digest(payload)),
        )
        return AlertMutationReceipt(
            action=action,
            condition_id=condition_id,
            lifecycle_state="resolved" if resolved_at else "acknowledged",
            acknowledged_at_utc=_utc(acknowledged_at),
            resolved_at_utc=_utc(resolved_at) if resolved_at else None,
        )

    def replay(
        self,
        owner: UUID,
        action: Literal["acknowledge", "resolve"],
        condition_id: str,
        idempotency_key: UUID,
    ) -> AlertMutationReceipt | None:
        try:
            with self._connect() as db:
                return self._existing_receipt(
                    db, owner, action, condition_id, idempotency_key
                )
        except AlertLifecycleConflict:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            raise AlertLifecycleUnavailable() from None

    def acknowledge(
        self,
        owner: UUID,
        alert: OperationalAlert,
        idempotency_key: UUID,
    ) -> AlertMutationReceipt:
        if alert.lifecycle_state != "active":
            raise AlertLifecycleConflict("ALERT_NOT_ACTIVE")
        snapshot = _snapshot(alert)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                meta = db.execute("SELECT last_clock FROM lifecycle_meta WHERE id=1").fetchone()
                if meta is None:
                    raise AlertLifecycleUnavailable()
                existing_receipt = self._existing_receipt(
                    db, owner, "acknowledge", alert.condition_id, idempotency_key
                )
                if existing_receipt is not None:
                    db.rollback()
                    return existing_receipt
                now = self._timestamp(meta["last_clock"])
                row = db.execute(
                    "SELECT * FROM alert_lifecycle WHERE owner_id=? AND condition_id=?",
                    (str(owner), alert.condition_id),
                ).fetchone()
                if row is None:
                    acknowledged_at = now
                    db.execute(
                        """
                        INSERT INTO alert_lifecycle(
                          owner_id,condition_id,alert_id,kind,severity,source,source_ref,
                          detail_code,observed_at_utc,evidence_routes_json,
                          acknowledged_at_utc,resolved_at_utc,updated_at_utc,snapshot_digest
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            str(owner), alert.condition_id, alert.id, alert.kind,
                            alert.severity, alert.source, alert.source_ref,
                            alert.detail_code, snapshot["observed_at_utc"],
                            _canonical(snapshot["evidence_routes"]), acknowledged_at,
                            None, now, _digest(snapshot),
                        ),
                    )
                else:
                    record = self._record(row)
                    if record.alert.resolved_at_utc is not None:
                        if alert.observed_at_utc <= record.alert.resolved_at_utc:
                            raise AlertLifecycleConflict("ALERT_ALREADY_RESOLVED")
                        acknowledged_at = now
                        db.execute(
                            """
                            UPDATE alert_lifecycle SET
                              alert_id=?,kind=?,severity=?,source=?,source_ref=?,detail_code=?,
                              observed_at_utc=?,evidence_routes_json=?,acknowledged_at_utc=?,
                              resolved_at_utc=NULL,updated_at_utc=?,snapshot_digest=?
                            WHERE owner_id=? AND condition_id=?
                            """,
                            (
                                alert.id, alert.kind, alert.severity, alert.source,
                                alert.source_ref, alert.detail_code,
                                snapshot["observed_at_utc"],
                                _canonical(snapshot["evidence_routes"]), acknowledged_at,
                                now, _digest(snapshot), str(owner), alert.condition_id,
                            ),
                        )
                    else:
                        acknowledged_at = record.alert.acknowledged_at_utc.isoformat(
                            timespec="microseconds"
                        )
                receipt = self._insert_receipt(
                    db,
                    owner=owner,
                    action="acknowledge",
                    condition_id=alert.condition_id,
                    idempotency_key=idempotency_key,
                    acknowledged_at=acknowledged_at,
                    resolved_at=None,
                    committed_at=now,
                )
                db.execute("UPDATE lifecycle_meta SET last_clock=? WHERE id=1", (now,))
                db.commit()
                return receipt
        except AlertLifecycleConflict:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            raise AlertLifecycleUnavailable() from None

    def resolve(
        self,
        owner: UUID,
        condition_id: str,
        idempotency_key: UUID,
    ) -> AlertMutationReceipt:
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                meta = db.execute("SELECT last_clock FROM lifecycle_meta WHERE id=1").fetchone()
                if meta is None:
                    raise AlertLifecycleUnavailable()
                existing_receipt = self._existing_receipt(
                    db, owner, "resolve", condition_id, idempotency_key
                )
                if existing_receipt is not None:
                    db.rollback()
                    return existing_receipt
                now = self._timestamp(meta["last_clock"])
                row = db.execute(
                    "SELECT * FROM alert_lifecycle WHERE owner_id=? AND condition_id=?",
                    (str(owner), condition_id),
                ).fetchone()
                if row is None:
                    raise AlertLifecycleConflict("ALERT_NOT_ACKNOWLEDGED")
                record = self._record(row)
                if record.alert.resolved_at_utc is not None:
                    raise AlertLifecycleConflict("ALERT_ALREADY_RESOLVED")
                acknowledged_at = record.alert.acknowledged_at_utc.isoformat(
                    timespec="microseconds"
                )
                db.execute(
                    """
                    UPDATE alert_lifecycle SET resolved_at_utc=?,updated_at_utc=?
                    WHERE owner_id=? AND condition_id=? AND resolved_at_utc IS NULL
                    """,
                    (now, now, str(owner), condition_id),
                )
                receipt = self._insert_receipt(
                    db,
                    owner=owner,
                    action="resolve",
                    condition_id=condition_id,
                    idempotency_key=idempotency_key,
                    acknowledged_at=acknowledged_at,
                    resolved_at=now,
                    committed_at=now,
                )
                db.execute("UPDATE lifecycle_meta SET last_clock=? WHERE id=1", (now,))
                db.commit()
                return receipt
        except AlertLifecycleConflict:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            raise AlertLifecycleUnavailable() from None

    def records_with_truncation(
        self,
        owner: UUID,
        include_conditions: tuple[str, ...] = (),
    ) -> tuple[tuple[LifecycleRecord, ...], bool]:
        if (
            len(include_conditions) > MAX_RECORDS
            or len(set(include_conditions)) != len(include_conditions)
            or any(
                len(value) != 24
                or any(character not in "0123456789abcdef" for character in value)
                for value in include_conditions
            )
        ):
            raise AlertLifecycleUnavailable()
        try:
            with self._connect() as db:
                meta = db.execute("SELECT last_clock FROM lifecycle_meta WHERE id=1").fetchone()
                if meta is None:
                    raise AlertLifecycleUnavailable()
                self._timestamp(meta["last_clock"])
                rows = db.execute(
                    """
                    SELECT * FROM alert_lifecycle WHERE owner_id=?
                    ORDER BY updated_at_utc DESC,condition_id LIMIT ?
                    """,
                    (str(owner), MAX_RECORDS + 1),
                ).fetchall()
                selected = rows[:MAX_RECORDS]
                seen = {row["condition_id"] for row in selected}
                for condition_id in include_conditions:
                    if condition_id in seen:
                        continue
                    row = db.execute(
                        """
                        SELECT * FROM alert_lifecycle
                        WHERE owner_id=? AND condition_id=?
                        """,
                        (str(owner), condition_id),
                    ).fetchone()
                    if row is not None:
                        selected.append(row)
                        seen.add(condition_id)
                return (
                    tuple(self._record(row) for row in selected),
                    len(rows) > MAX_RECORDS,
                )
        except AlertLifecycleUnavailable:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            raise AlertLifecycleUnavailable() from None

    def records(self, owner: UUID) -> tuple[LifecycleRecord, ...]:
        return self.records_with_truncation(owner)[0]

    def record(self, owner: UUID, condition_id: str) -> LifecycleRecord | None:
        try:
            with self._connect() as db:
                row = db.execute(
                    "SELECT * FROM alert_lifecycle WHERE owner_id=? AND condition_id=?",
                    (str(owner), condition_id),
                ).fetchone()
                return self._record(row) if row is not None else None
        except AlertLifecycleUnavailable:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            raise AlertLifecycleUnavailable() from None


def _coverage_for(
    inventory: OperationalAlertInventory, alert: OperationalAlert
) -> AlertCoverage | None:
    return next((item for item in inventory.coverage if item.kind == alert.kind), None)


def _source_complete(
    inventory: OperationalAlertInventory, alert: OperationalAlert
) -> bool:
    coverage = _coverage_for(inventory, alert)
    return (
        coverage is not None
        and coverage.runtime == "connected"
        and not (alert.source == "execution_journal" and inventory.truncated)
    )


def enrich_operational_alert_inventory(
    inventory: OperationalAlertInventory,
    owner: UUID,
    journal: AlertLifecycleJournal | None,
) -> OperationalAlertInventory:
    if journal is None:
        return inventory
    current = {item.condition_id: item for item in inventory.alerts}
    try:
        records, lifecycle_truncated = journal.records_with_truncation(
            owner, tuple(current)
        )
    except AlertLifecycleUnavailable:
        unavailable = tuple(
            item.model_copy(
                update={
                    "lifecycle_state": "unavailable",
                    "acknowledge_allowed": False,
                    "resolve_allowed": False,
                }
            )
            for item in inventory.alerts
        )
        return inventory.model_copy(
            update={
                "lifecycle_runtime": "degraded",
                "lifecycle_mutations_enabled": False,
                "status": "degraded",
                "alerts": unavailable,
            }
        )

    retained = {item.condition_id: item for item in records}
    merged: list[OperationalAlert] = []
    for condition_id, alert in current.items():
        record = retained.pop(condition_id, None)
        if record is None:
            merged.append(alert.model_copy(update={"acknowledge_allowed": True}))
            continue
        saved = record.alert
        if (
            saved.resolved_at_utc is not None
            and alert.observed_at_utc > saved.resolved_at_utc
        ):
            merged.append(alert.model_copy(update={"acknowledge_allowed": True}))
        elif saved.resolved_at_utc is not None:
            merged.append(saved)
        else:
            merged.append(
                alert.model_copy(
                    update={
                        "lifecycle_state": "acknowledged",
                        "acknowledged_by": "owner",
                        "acknowledged_at_utc": saved.acknowledged_at_utc,
                        "resolve_allowed": alert.kind == "order_reject",
                    }
                )
            )
    for record in retained.values():
        saved = record.alert
        if saved.lifecycle_state == "resolved":
            merged.append(saved)
            continue
        complete = _source_complete(inventory, saved)
        merged.append(
            saved.model_copy(
                update={
                    "lifecycle_state": "cleared" if complete else "unavailable",
                    "resolve_allowed": complete,
                }
            )
        )
    merged.sort(
        key=lambda item: (
            LIFECYCLE_ORDER[item.lifecycle_state],
            SEVERITY_ORDER[item.severity],
            -item.observed_at_utc.timestamp(),
            item.kind,
            item.id,
        )
    )
    truncated = inventory.truncated or lifecycle_truncated or len(merged) > MAX_RECORDS
    return inventory.model_copy(
        update={
            "lifecycle_runtime": "connected",
            "lifecycle_mutations_enabled": True,
            "truncated": truncated,
            "alerts": tuple(merged[:MAX_RECORDS]),
        }
    )


def resolution_is_allowed(
    inventory: OperationalAlertInventory,
    record: LifecycleRecord,
    *,
    source_connected: bool | None = None,
) -> bool:
    current = {item.condition_id: item for item in inventory.alerts}
    if record.condition_id in current:
        return record.alert.kind == "order_reject"
    if source_connected is not None:
        return source_connected and not (
            record.alert.source == "execution_journal" and inventory.truncated
        )
    return _source_complete(inventory, record.alert)


def load_alert_lifecycle_journal() -> AlertLifecycleJournal | None:
    configured = os.environ.get("SOCHRON_ALERT_LIFECYCLE_DIR")
    return AlertLifecycleJournal(Path(configured)) if configured else None
