"""Read-only owner projection of durable execution journal evidence."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
from collections import defaultdict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, Field, StrictInt, ValidationError, field_validator

from .models import (
    CommandIntent,
    CommandState,
    ManagementIntent,
    ManagementOperation,
    Side,
    StrictModel,
)

MAX_DATABASE_BYTES = 256 * 1024 * 1024
MAX_COMMANDS = 50
MAX_MANAGEMENT = 100
MAX_DEALS = 1_000
MAX_OPERATIONAL_FACTS = 100


class ExecutionEvidenceUnavailable(RuntimeError):
    pass


class DealEvidence(StrictModel):
    deal_ticket: str = Field(min_length=1, max_length=128)
    volume: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    occurred_at_utc: AwareDatetime | None = None

    @field_validator("occurred_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None


class RejectionEvidence(StrictModel):
    operation: Literal["open", "cancel", "close"]
    retcode: StrictInt
    retcode_external: StrictInt
    observed_at_utc: AwareDatetime

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ManagementOutcomeEvidence(StrictModel):
    broker_order_ticket: str = Field(min_length=1, max_length=128)
    position_id: str | None = Field(default=None, min_length=1, max_length=128)
    requested_volume: Decimal = Field(gt=0)
    completed_volume: Decimal = Field(ge=0)
    remaining_volume: Decimal = Field(ge=0)
    observed_at_utc: AwareDatetime
    deals: tuple[DealEvidence, ...] = ()

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ManagementEvidence(StrictModel):
    command_id: str = Field(min_length=1, max_length=128)
    operation: ManagementOperation
    state: CommandState
    requested_volume: Decimal = Field(gt=0)
    created_at_utc: AwareDatetime
    updated_at_utc: AwareDatetime
    outcome: ManagementOutcomeEvidence | None = None
    rejection: RejectionEvidence | None = None

    @field_validator("created_at_utc", "updated_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class OrderEvidence(StrictModel):
    order_ticket: str = Field(min_length=1, max_length=128)
    position_id: str | None = Field(default=None, min_length=1, max_length=128)
    requested_volume: Decimal = Field(gt=0)
    filled_volume: Decimal = Field(ge=0)
    remaining_volume: Decimal = Field(ge=0)
    cancelled_volume: Decimal = Field(ge=0)
    closed_volume: Decimal = Field(ge=0)
    stop_loss_confirmed: bool
    deals: tuple[DealEvidence, ...] = ()


class CommandEvidence(StrictModel):
    command_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    side: Side
    state: CommandState
    requested_volume: Decimal = Field(gt=0)
    created_at_utc: AwareDatetime
    updated_at_utc: AwareDatetime
    order: OrderEvidence | None = None
    rejection: RejectionEvidence | None = None
    management: tuple[ManagementEvidence, ...] = ()

    @field_validator("created_at_utc", "updated_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ExecutionEvidenceStatus(StrictModel):
    state: Literal["disabled", "available", "unavailable"]
    reason: Literal["not_configured", "source_unavailable"] | None = None
    total_commands: StrictInt = Field(ge=0)
    truncated: bool = False
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False


class ExecutionEvidenceView(StrictModel):
    trading_mode: Literal["demo"] = "demo"
    read_only: Literal[True] = True
    source: Literal["local-execution-journal"] = "local-execution-journal"
    status: ExecutionEvidenceStatus
    commands: tuple[CommandEvidence, ...] = ()


class ExecutionOperationalFact(StrictModel):
    kind: Literal["order_reject", "no_sl", "risk_halt", "unknown_execution"]
    source_ref: str = Field(min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$")
    observed_at_utc: AwareDatetime
    detail_code: Literal[
        "entry_rejected",
        "management_rejected",
        "entry_unknown",
        "management_unknown",
        "open_volume_without_confirmed_sl",
        "daily_halt",
        "total_halt",
        "daily_and_total_halt",
    ]

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_observed_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ExecutionOperationalView(StrictModel):
    state: Literal["available", "unavailable"]
    facts: tuple[ExecutionOperationalFact, ...] = ()
    truncated: bool = False


REQUIRED_COLUMNS = {
    "commands": {
        "command_id", "account_ref", "experiment_id", "payload_json", "volume", "state",
        "created_at", "updated_at",
    },
    "broker_orders": {
        "order_ticket", "command_id", "position_id", "requested_volume", "filled_volume",
        "remaining_volume", "sl_confirmed",
    },
    "broker_deals": {"deal_ticket", "command_id", "volume", "price"},
    "broker_deal_financials": {"deal_ticket", "occurred_at"},
    "broker_order_lifecycle": {"command_id", "cancelled_volume", "closed_volume"},
    "management_commands": {
        "command_id", "account_ref", "experiment_id", "target_command_id", "operation",
        "payload_json", "requested_volume", "state", "created_at", "updated_at",
    },
    "management_outcomes": {
        "command_id", "broker_order_ticket", "position_id", "requested_volume",
        "completed_volume", "remaining_volume", "observed_at",
    },
    "management_deals": {
        "deal_ticket", "command_id", "volume", "price", "occurred_at",
    },
    "executor_rejections": {
        "command_id", "target_command_id", "operation", "retcode", "retcode_external",
        "observed_at",
    },
    "risk_state": {
        "account_ref", "experiment_id", "daily_halt", "total_halt", "updated_at",
    },
}


def _decimal(value: object, *, positive: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ExecutionEvidenceUnavailable() from None
    if (
        not result.is_finite()
        or len(result.as_tuple().digits) > 80
        or not -100 <= result.as_tuple().exponent <= 100
        or result < 0
        or (positive and result <= 0)
    ):
        raise ExecutionEvidenceUnavailable()
    return result


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ExecutionEvidenceUnavailable()
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ExecutionEvidenceUnavailable() from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExecutionEvidenceUnavailable()
    return parsed.astimezone(UTC)


def _bounded(rows: Iterable[sqlite3.Row], maximum: int) -> list[sqlite3.Row]:
    result = list(rows)
    if len(result) > maximum:
        raise ExecutionEvidenceUnavailable()
    return result


class ExecutionEvidenceReader:
    """Pins one private journal and exposes validated, bounded read-only projections."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._directory_identity: tuple[int, int] | None = None
        self._file_identity: tuple[int, int] | None = None
        try:
            self._private_files(pin=True)
            with self._connect() as db:
                self._validate_database(db, integrity=True)
            self._runtime: Literal["connected", "degraded"] = "connected"
        except (OSError, sqlite3.Error, ExecutionEvidenceUnavailable):
            raise RuntimeError("Invalid private execution journal; API not started") from None

    @property
    def configured(self) -> Literal[True]:
        return True

    def _private_files(self, *, pin: bool = False) -> None:
        if not self.path.is_absolute() or self.path.resolve(strict=True) != self.path:
            raise ExecutionEvidenceUnavailable()
        directory = self.path.parent
        directory_info = directory.lstat()
        if (
            not stat.S_ISDIR(directory_info.st_mode)
            or directory_info.st_uid != os.getuid()
            or stat.S_IMODE(directory_info.st_mode) & 0o077
        ):
            raise ExecutionEvidenceUnavailable()
        directory_identity = (directory_info.st_dev, directory_info.st_ino)
        if not pin and directory_identity != self._directory_identity:
            raise ExecutionEvidenceUnavailable()

        total_bytes = 0
        file_identity = None
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
                raise ExecutionEvidenceUnavailable()
            total_bytes += info.st_size
            if not suffix:
                file_identity = (info.st_dev, info.st_ino)
        if total_bytes <= 0 or total_bytes > MAX_DATABASE_BYTES:
            raise ExecutionEvidenceUnavailable()
        if not pin and file_identity != self._file_identity:
            raise ExecutionEvidenceUnavailable()
        if pin:
            self._directory_identity = directory_identity
            self._file_identity = file_identity

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._private_files()
        wal = Path(str(self.path) + "-wal")
        shm = Path(str(self.path) + "-shm")
        pending_wal = wal.exists() and wal.stat().st_size > 0
        if pending_wal and not shm.exists():
            raise ExecutionEvidenceUnavailable()
        # A clean WAL database needs no sidecars. Immutable mode prevents a read
        # from creating them; if a writer starts concurrently, the post-read WAL
        # fence rejects the stale projection. A pending WAL must use normal
        # read-only semantics so SQLite includes committed frames.
        parameters = "?mode=ro" if pending_wal else "?mode=ro&immutable=1"
        db = sqlite3.connect(
            self.path.as_uri() + parameters, uri=True, timeout=0.1, isolation_level=None
        )
        try:
            db.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA busy_timeout=100")
            if db.execute("PRAGMA query_only").fetchone()[0] != 1:
                raise ExecutionEvidenceUnavailable()
            yield db
            self._private_files()
            if not pending_wal and wal.exists() and wal.stat().st_size > 0:
                raise ExecutionEvidenceUnavailable()
        finally:
            db.close()

    @staticmethod
    def _validate_database(db: sqlite3.Connection, *, integrity: bool = False) -> None:
        if integrity:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ExecutionEvidenceUnavailable()
            if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ExecutionEvidenceUnavailable()
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall()
        }
        if not REQUIRED_COLUMNS.keys() <= tables:
            raise ExecutionEvidenceUnavailable()
        for table, required in REQUIRED_COLUMNS.items():
            columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
            if not required <= columns:
                raise ExecutionEvidenceUnavailable()

    @staticmethod
    def _rejection(row: sqlite3.Row | None) -> RejectionEvidence | None:
        if row is None:
            return None
        return RejectionEvidence(
            operation=row["operation"],
            retcode=row["retcode"],
            retcode_external=row["retcode_external"],
            observed_at_utc=_utc(row["observed_at"]),
        )

    @staticmethod
    def _deal(row: sqlite3.Row) -> DealEvidence:
        return DealEvidence(
            deal_ticket=row["deal_ticket"],
            volume=_decimal(row["volume"], positive=True),
            price=_decimal(row["price"], positive=True),
            occurred_at_utc=_utc(row["occurred_at"]) if row["occurred_at"] else None,
        )

    def _read(self) -> ExecutionEvidenceView:
        with self._connect() as db:
            self._validate_database(db)
            db.execute("BEGIN")
            total = db.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
            command_rows = db.execute(
                """
                SELECT * FROM commands
                ORDER BY updated_at DESC, command_id DESC
                LIMIT ?
                """,
                (MAX_COMMANDS,),
            ).fetchall()
            command_ids = [row["command_id"] for row in command_rows]
            if len(set(command_ids)) != len(command_ids):
                raise ExecutionEvidenceUnavailable()
            if not command_ids:
                return ExecutionEvidenceView(
                    status=ExecutionEvidenceStatus(
                        state="available", total_commands=total, truncated=False
                    )
                )

            placeholders = ",".join("?" for _ in command_ids)
            order_rows = _bounded(
                db.execute(
                    f"SELECT * FROM broker_orders WHERE command_id IN ({placeholders}) "
                    "ORDER BY command_id,order_ticket",
                    command_ids,
                ).fetchall(),
                len(command_ids),
            )
            lifecycle_rows = db.execute(
                f"SELECT * FROM broker_order_lifecycle WHERE command_id IN ({placeholders})",
                command_ids,
            ).fetchall()
            entry_deals = _bounded(
                db.execute(
                    f"""
                    SELECT d.*,f.occurred_at FROM broker_deals d
                    LEFT JOIN broker_deal_financials f USING(deal_ticket)
                    WHERE d.command_id IN ({placeholders})
                    ORDER BY d.command_id,d.deal_ticket LIMIT ?
                    """,
                    (*command_ids, MAX_DEALS + 1),
                ).fetchall(),
                MAX_DEALS,
            )
            management_rows = _bounded(
                db.execute(
                    f"""
                    SELECT * FROM management_commands
                    WHERE target_command_id IN ({placeholders})
                    ORDER BY created_at,command_id LIMIT ?
                    """,
                    (*command_ids, MAX_MANAGEMENT + 1),
                ).fetchall(),
                MAX_MANAGEMENT,
            )
            management_ids = [row["command_id"] for row in management_rows]
            if len(set(management_ids)) != len(management_ids):
                raise ExecutionEvidenceUnavailable()
            evidence_ids = command_ids + management_ids
            evidence_placeholders = ",".join("?" for _ in evidence_ids)
            rejection_rows = db.execute(
                f"SELECT * FROM executor_rejections WHERE command_id IN ({evidence_placeholders})",
                evidence_ids,
            ).fetchall()
            rejection_by_id = {row["command_id"]: row for row in rejection_rows}
            if len(rejection_by_id) != len(rejection_rows):
                raise ExecutionEvidenceUnavailable()

            outcomes_by_id: dict[str, sqlite3.Row] = {}
            management_deals: list[sqlite3.Row] = []
            if management_ids:
                management_placeholders = ",".join("?" for _ in management_ids)
                outcome_rows = db.execute(
                    f"SELECT * FROM management_outcomes "
                    f"WHERE command_id IN ({management_placeholders})",
                    management_ids,
                ).fetchall()
                outcomes_by_id = {row["command_id"]: row for row in outcome_rows}
                if len(outcomes_by_id) != len(outcome_rows):
                    raise ExecutionEvidenceUnavailable()
                management_deals = _bounded(
                    db.execute(
                        f"SELECT * FROM management_deals "
                        f"WHERE command_id IN ({management_placeholders}) "
                        "ORDER BY command_id,deal_ticket LIMIT ?",
                        (*management_ids, MAX_DEALS + 1),
                    ).fetchall(),
                    MAX_DEALS,
                )

            orders_by_command = {row["command_id"]: row for row in order_rows}
            lifecycle_by_command = {row["command_id"]: row for row in lifecycle_rows}
            if len(lifecycle_by_command) != len(lifecycle_rows):
                raise ExecutionEvidenceUnavailable()
            entry_deals_by_command: defaultdict[str, list[sqlite3.Row]] = defaultdict(list)
            for row in entry_deals:
                entry_deals_by_command[row["command_id"]].append(row)
            management_deals_by_command: defaultdict[str, list[sqlite3.Row]] = defaultdict(list)
            for row in management_deals:
                management_deals_by_command[row["command_id"]].append(row)
            management_by_target: defaultdict[str, list[ManagementEvidence]] = defaultdict(list)

            for row in management_rows:
                intent = ManagementIntent.model_validate_json(row["payload_json"])
                if (
                    intent.command_id != row["command_id"]
                    or intent.target_command_id != row["target_command_id"]
                    or intent.account_ref != row["account_ref"]
                    or intent.experiment_id != row["experiment_id"]
                    or intent.operation.value != row["operation"]
                ):
                    raise ExecutionEvidenceUnavailable()
                requested = _decimal(row["requested_volume"], positive=True)
                outcome_row = outcomes_by_id.get(row["command_id"])
                rejection_row = rejection_by_id.get(row["command_id"])
                if rejection_row is not None and (
                    rejection_row["target_command_id"] != row["target_command_id"]
                    or rejection_row["operation"] != row["operation"]
                    or row["state"] != CommandState.REJECTED.value
                    or outcome_row is not None
                ):
                    raise ExecutionEvidenceUnavailable()
                outcome = None
                if outcome_row is not None:
                    completed = _decimal(outcome_row["completed_volume"])
                    remaining = _decimal(outcome_row["remaining_volume"])
                    outcome_requested = _decimal(outcome_row["requested_volume"], positive=True)
                    if outcome_requested != requested or completed + remaining != requested:
                        raise ExecutionEvidenceUnavailable()
                    deals = tuple(
                        self._deal(deal)
                        for deal in management_deals_by_command[row["command_id"]]
                    )
                    if intent.operation is ManagementOperation.CLOSE:
                        if sum((deal.volume for deal in deals), Decimal(0)) != completed:
                            raise ExecutionEvidenceUnavailable()
                    elif deals:
                        raise ExecutionEvidenceUnavailable()
                    outcome = ManagementOutcomeEvidence(
                        broker_order_ticket=outcome_row["broker_order_ticket"],
                        position_id=outcome_row["position_id"],
                        requested_volume=requested,
                        completed_volume=completed,
                        remaining_volume=remaining,
                        observed_at_utc=_utc(outcome_row["observed_at"]),
                        deals=deals,
                    )
                management_by_target[row["target_command_id"]].append(
                    ManagementEvidence(
                        command_id=row["command_id"],
                        operation=row["operation"],
                        state=CommandState(row["state"]),
                        requested_volume=requested,
                        created_at_utc=_utc(row["created_at"]),
                        updated_at_utc=_utc(row["updated_at"]),
                        outcome=outcome,
                        rejection=self._rejection(rejection_row),
                    )
                )

            commands = []
            for row in command_rows:
                intent = CommandIntent.model_validate_json(row["payload_json"])
                if (
                    intent.command_id != row["command_id"]
                    or intent.account_ref != row["account_ref"]
                    or intent.experiment_id != row["experiment_id"]
                    or intent.operation != "open"
                ):
                    raise ExecutionEvidenceUnavailable()
                requested = _decimal(row["volume"], positive=True)
                order_row = orders_by_command.get(row["command_id"])
                command_state = CommandState(row["state"])
                rejection_row = rejection_by_id.get(row["command_id"])
                if rejection_row is not None and (
                    rejection_row["target_command_id"] is not None
                    or rejection_row["operation"] != "open"
                    or command_state is not CommandState.REJECTED
                    or order_row is not None
                ):
                    raise ExecutionEvidenceUnavailable()
                order = None
                deals = tuple(
                    self._deal(deal) for deal in entry_deals_by_command[row["command_id"]]
                )
                lifecycle = lifecycle_by_command.get(row["command_id"])
                if order_row is None:
                    if deals or lifecycle is not None:
                        raise ExecutionEvidenceUnavailable()
                    if command_state in {
                        CommandState.ACKNOWLEDGED,
                        CommandState.PARTIALLY_FILLED,
                        CommandState.FILLED,
                        CommandState.PROTECTION_FAILED,
                        CommandState.CLOSING,
                        CommandState.CLOSED,
                    }:
                        raise ExecutionEvidenceUnavailable()
                else:
                    filled = _decimal(order_row["filled_volume"])
                    remaining = _decimal(order_row["remaining_volume"])
                    cancelled = _decimal(lifecycle["cancelled_volume"]) if lifecycle else Decimal(0)
                    closed = _decimal(lifecycle["closed_volume"]) if lifecycle else Decimal(0)
                    order_requested = _decimal(order_row["requested_volume"], positive=True)
                    if (
                        order_row["sl_confirmed"] not in (0, 1)
                        or order_requested != requested
                        or filled + remaining + cancelled != requested
                        or closed > filled
                        or sum((deal.volume for deal in deals), Decimal(0)) != filled
                        or (filled > 0 and not order_row["position_id"])
                        or (bool(order_row["sl_confirmed"]) and filled - closed <= 0)
                    ):
                        raise ExecutionEvidenceUnavailable()
                    if (
                        command_state
                        in {CommandState.CREATED, CommandState.VALIDATED, CommandState.QUEUED}
                        or (
                            command_state is CommandState.ACKNOWLEDGED
                            and (filled != 0 or remaining <= 0)
                        )
                        or (
                            command_state is CommandState.PARTIALLY_FILLED
                            and (filled <= 0 or remaining <= 0)
                        )
                        or (
                            command_state is CommandState.FILLED
                            and (not bool(order_row["sl_confirmed"]) or filled - closed <= 0)
                        )
                        or (
                            command_state is CommandState.PROTECTION_FAILED
                            and (bool(order_row["sl_confirmed"]) or filled - closed <= 0)
                        )
                        or (
                            command_state is CommandState.CLOSED
                            and (closed != filled or remaining != 0)
                        )
                    ):
                        raise ExecutionEvidenceUnavailable()
                    order = OrderEvidence(
                        order_ticket=order_row["order_ticket"],
                        position_id=order_row["position_id"],
                        requested_volume=requested,
                        filled_volume=filled,
                        remaining_volume=remaining,
                        cancelled_volume=cancelled,
                        closed_volume=closed,
                        stop_loss_confirmed=bool(order_row["sl_confirmed"]),
                        deals=deals,
                    )
                commands.append(
                    CommandEvidence(
                        command_id=row["command_id"],
                        symbol=intent.symbol,
                        side=intent.side,
                        state=command_state,
                        requested_volume=requested,
                        created_at_utc=_utc(row["created_at"]),
                        updated_at_utc=_utc(row["updated_at"]),
                        order=order,
                        rejection=self._rejection(rejection_row),
                        management=tuple(management_by_target[row["command_id"]]),
                    )
                )
            return ExecutionEvidenceView(
                status=ExecutionEvidenceStatus(
                    state="available",
                    total_commands=total,
                    truncated=total > len(commands),
                ),
                commands=tuple(commands),
            )

    def view(self) -> ExecutionEvidenceView:
        try:
            result = self._read()
        except (
            OSError,
            sqlite3.Error,
            ExecutionEvidenceUnavailable,
            ValidationError,
            ValueError,
            KeyError,
        ):
            self._runtime = "degraded"
            return ExecutionEvidenceView(
                status=ExecutionEvidenceStatus(
                    state="unavailable", reason="source_unavailable", total_commands=0
                )
            )
        self._runtime = "connected"
        return result

    @staticmethod
    def _safe_reference(*values: object) -> str:
        payload = "\x1f".join(str(value) for value in values)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _operational_facts(self) -> ExecutionOperationalView:
        with self._connect() as db:
            self._validate_database(db)
            db.execute("BEGIN")
            facts: list[ExecutionOperationalFact] = []
            truncated = False

            entry_rows = db.execute(
                """
                SELECT command_id,state,updated_at FROM commands
                WHERE state IN ('unknown','rejected')
                ORDER BY updated_at DESC,command_id DESC LIMIT ?
                """,
                (MAX_OPERATIONAL_FACTS + 1,),
            ).fetchall()
            management_rows = db.execute(
                """
                SELECT command_id,state,updated_at FROM management_commands
                WHERE state IN ('unknown','rejected')
                ORDER BY updated_at DESC,command_id DESC LIMIT ?
                """,
                (MAX_OPERATIONAL_FACTS + 1,),
            ).fetchall()
            no_sl_rows = db.execute(
                """
                SELECT c.command_id,c.updated_at,o.filled_volume,o.sl_confirmed,
                       COALESCE(l.closed_volume,'0') AS closed_volume
                FROM commands c JOIN broker_orders o USING(command_id)
                LEFT JOIN broker_order_lifecycle l USING(command_id)
                WHERE c.state IN ('partially_filled','filled','protection_failed','closing')
                  AND o.sl_confirmed<>1
                ORDER BY c.updated_at DESC,c.command_id DESC LIMIT ?
                """,
                (MAX_OPERATIONAL_FACTS + 1,),
            ).fetchall()
            risk_rows = db.execute(
                """
                SELECT account_ref,experiment_id,daily_halt,total_halt,updated_at
                FROM risk_state WHERE daily_halt<>0 OR total_halt<>0
                ORDER BY updated_at DESC,account_ref,experiment_id LIMIT ?
                """,
                (MAX_OPERATIONAL_FACTS + 1,),
            ).fetchall()
            groups = (entry_rows, management_rows, no_sl_rows, risk_rows)
            if any(len(rows) > MAX_OPERATIONAL_FACTS for rows in groups):
                truncated = True
            entry_rows, management_rows, no_sl_rows, risk_rows = (
                rows[:MAX_OPERATIONAL_FACTS] for rows in groups
            )

            for scope, rows in (("entry", entry_rows), ("management", management_rows)):
                for row in rows:
                    state = CommandState(row["state"])
                    if state not in {CommandState.UNKNOWN, CommandState.REJECTED}:
                        raise ExecutionEvidenceUnavailable()
                    facts.append(
                        ExecutionOperationalFact(
                            kind=(
                                "unknown_execution"
                                if state is CommandState.UNKNOWN
                                else "order_reject"
                            ),
                            source_ref=self._safe_reference(scope, row["command_id"]),
                            observed_at_utc=_utc(row["updated_at"]),
                            detail_code=f"{scope}_{state.value}",
                        )
                    )

            for row in no_sl_rows:
                if row["sl_confirmed"] != 0:
                    raise ExecutionEvidenceUnavailable()
                filled = _decimal(row["filled_volume"])
                closed = _decimal(row["closed_volume"])
                if filled <= closed:
                    continue
                facts.append(
                    ExecutionOperationalFact(
                        kind="no_sl",
                        source_ref=self._safe_reference("no-sl", row["command_id"]),
                        observed_at_utc=_utc(row["updated_at"]),
                        detail_code="open_volume_without_confirmed_sl",
                    )
                )

            for row in risk_rows:
                if row["daily_halt"] not in (0, 1) or row["total_halt"] not in (0, 1):
                    raise ExecutionEvidenceUnavailable()
                daily, total = bool(row["daily_halt"]), bool(row["total_halt"])
                detail = (
                    "daily_and_total_halt" if daily and total
                    else "total_halt" if total
                    else "daily_halt"
                )
                facts.append(
                    ExecutionOperationalFact(
                        kind="risk_halt",
                        source_ref=self._safe_reference(
                            "risk", row["account_ref"], row["experiment_id"]
                        ),
                        observed_at_utc=_utc(row["updated_at"]),
                        detail_code=detail,
                    )
                )

            facts.sort(
                key=lambda item: (
                    -item.observed_at_utc.timestamp(), item.kind, item.source_ref
                )
            )
            if len(facts) > MAX_OPERATIONAL_FACTS:
                facts = facts[:MAX_OPERATIONAL_FACTS]
                truncated = True
            return ExecutionOperationalView(
                state="available", facts=tuple(facts), truncated=truncated
            )

    def operational_facts(self) -> ExecutionOperationalView:
        try:
            result = self._operational_facts()
        except (
            OSError,
            sqlite3.Error,
            ExecutionEvidenceUnavailable,
            ValidationError,
            ValueError,
            KeyError,
        ):
            self._runtime = "degraded"
            return ExecutionOperationalView(state="unavailable")
        self._runtime = "connected"
        return result

    def runtime_state(self) -> Literal["connected", "degraded"]:
        return self._runtime


def disabled_execution_evidence() -> ExecutionEvidenceView:
    return ExecutionEvidenceView(
        status=ExecutionEvidenceStatus(
            state="disabled", reason="not_configured", total_commands=0
        )
    )


def load_execution_evidence_reader() -> ExecutionEvidenceReader | None:
    configured = os.environ.get("SOCHRON_EXECUTION_JOURNAL_PATH")
    return ExecutionEvidenceReader(Path(configured)) if configured else None
