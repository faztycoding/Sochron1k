from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path

from .models import (
    BrokerDeal,
    BrokerSnapshot,
    CommandIntent,
    CommandState,
    ManagementIntent,
    ManagementOperation,
    ManagementSnapshot,
    RiskState,
    TradeAudit,
)
from .risk import DAILY_LOSS_LIMIT, EXPERIMENT_LOSS_LIMIT


class IdempotencyConflict(RuntimeError):
    pass


class ExposureConflict(RuntimeError):
    pass


class RiskStateConflict(RuntimeError):
    def __init__(self):
        super().__init__("RISK_STATE_CHANGED")


class BrokerEvidenceConflict(RuntimeError):
    def __init__(self):
        super().__init__("BROKER_EVIDENCE_CONFLICT")


class ManagementConflict(RuntimeError):
    def __init__(self, reason: str = "MANAGEMENT_CONFLICT"):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Reservation:
    command_id: str
    state: CommandState
    volume: Decimal
    duplicate: bool


@dataclass(frozen=True)
class ManagementReservation:
    command_id: str
    target_command_id: str
    operation: ManagementOperation
    state: CommandState
    volume: Decimal
    duplicate: bool


class Journal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if journal_mode.lower() != "wal":
                raise RuntimeError("SQLite WAL mode is required")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS commands (
                    command_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    account_ref TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    volume TEXT NOT NULL,
                    reserved_loss TEXT NOT NULL,
                    state TEXT NOT NULL,
                    protected INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(scope, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS command_transitions (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_id TEXT NOT NULL REFERENCES commands(command_id),
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    detail TEXT
                );
                CREATE TABLE IF NOT EXISTS dispatch_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    command_id TEXT NOT NULL REFERENCES commands(command_id),
                    started_at TEXT NOT NULL,
                    outcome TEXT
                );
                CREATE TABLE IF NOT EXISTS exposure_slots (
                    account_ref TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    command_id TEXT NOT NULL UNIQUE REFERENCES commands(command_id),
                    reserved_loss TEXT NOT NULL,
                    PRIMARY KEY(account_ref, experiment_id)
                );
                CREATE TABLE IF NOT EXISTS broker_orders (
                    order_ticket TEXT PRIMARY KEY,
                    command_id TEXT NOT NULL REFERENCES commands(command_id),
                    position_id TEXT,
                    requested_volume TEXT NOT NULL,
                    filled_volume TEXT NOT NULL,
                    remaining_volume TEXT NOT NULL,
                    sl_confirmed INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS broker_deals (
                    deal_ticket TEXT PRIMARY KEY,
                    command_id TEXT NOT NULL REFERENCES commands(command_id),
                    volume TEXT NOT NULL,
                    price TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS risk_state (
                    account_ref TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    bangkok_day TEXT NOT NULL,
                    daily_baseline TEXT NOT NULL,
                    experiment_baseline TEXT NOT NULL,
                    daily_halt INTEGER NOT NULL DEFAULT 0,
                    total_halt INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(account_ref, experiment_id)
                );
                CREATE TABLE IF NOT EXISTS broker_order_lifecycle (
                    command_id TEXT PRIMARY KEY REFERENCES commands(command_id),
                    cancelled_volume TEXT NOT NULL,
                    closed_volume TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS broker_deal_financials (
                    deal_ticket TEXT PRIMARY KEY REFERENCES broker_deals(deal_ticket),
                    profit TEXT NOT NULL,
                    commission TEXT NOT NULL,
                    swap TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    occurred_at TEXT
                );
                CREATE TABLE IF NOT EXISTS management_commands (
                    command_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    account_ref TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    target_command_id TEXT NOT NULL REFERENCES commands(command_id),
                    operation TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    requested_volume TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(scope, idempotency_key)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_management_per_target
                ON management_commands(target_command_id)
                WHERE state NOT IN ('closed','cancelled','rejected','expired');
                CREATE TABLE IF NOT EXISTS management_transitions (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_id TEXT NOT NULL REFERENCES management_commands(command_id),
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    detail TEXT
                );
                CREATE TABLE IF NOT EXISTS management_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    command_id TEXT NOT NULL REFERENCES management_commands(command_id),
                    started_at TEXT NOT NULL,
                    outcome TEXT
                );
                CREATE TABLE IF NOT EXISTS management_outcomes (
                    command_id TEXT PRIMARY KEY REFERENCES management_commands(command_id),
                    broker_order_ticket TEXT NOT NULL UNIQUE,
                    position_id TEXT,
                    requested_volume TEXT NOT NULL,
                    completed_volume TEXT NOT NULL,
                    remaining_volume TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS management_deals (
                    deal_ticket TEXT PRIMARY KEY,
                    command_id TEXT NOT NULL REFERENCES management_commands(command_id),
                    volume TEXT NOT NULL,
                    price TEXT NOT NULL,
                    profit TEXT NOT NULL,
                    commission TEXT NOT NULL,
                    swap TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    occurred_at TEXT
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def reserve(
        self,
        intent: CommandIntent,
        volume: Decimal,
        reserved_loss: Decimal,
        *,
        expected_risk: RiskState | None = None,
    ) -> Reservation:
        fingerprint = intent.canonical_fingerprint()
        payload = json.dumps(intent.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        now = self._now()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if expected_risk is not None:
                self._check_risk_scope(expected_risk, intent.account_ref, intent.experiment_id)
                self._check_risk(connection, expected_risk)
            existing = connection.execute(
                """
                SELECT command_id, fingerprint, state, volume
                FROM commands
                WHERE scope=? AND idempotency_key=?
                """,
                (intent.idempotency_scope, intent.idempotency_key),
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise IdempotencyConflict(
                        "idempotency key was already used with another payload"
                    )
                connection.commit()
                return Reservation(
                    command_id=existing["command_id"],
                    state=CommandState(existing["state"]),
                    volume=Decimal(existing["volume"]),
                    duplicate=True,
                )
            if connection.execute(
                "SELECT 1 FROM exposure_slots WHERE account_ref=?",
                (intent.account_ref,),
            ).fetchone():
                raise ExposureConflict(
                    "one logical exposure already occupies this account and experiment"
                )
            connection.execute(
                """
                INSERT INTO commands (
                    command_id, scope, idempotency_key, fingerprint, account_ref,
                    experiment_id, payload_json, volume, reserved_loss, state,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.command_id,
                    intent.idempotency_scope,
                    intent.idempotency_key,
                    fingerprint,
                    intent.account_ref,
                    intent.experiment_id,
                    payload,
                    str(volume),
                    str(reserved_loss),
                    CommandState.QUEUED.value,
                    now,
                    now,
                ),
            )
            for from_state, to_state in (
                (None, CommandState.CREATED),
                (CommandState.CREATED, CommandState.VALIDATED),
                (CommandState.VALIDATED, CommandState.QUEUED),
            ):
                connection.execute(
                    """
                    INSERT INTO command_transitions(command_id, from_state, to_state, occurred_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        intent.command_id,
                        from_state.value if from_state else None,
                        to_state.value,
                        now,
                    ),
                )
            connection.execute(
                """
                INSERT INTO exposure_slots(account_ref, experiment_id, command_id, reserved_loss)
                VALUES (?, ?, ?, ?)
                """,
                (intent.account_ref, intent.experiment_id, intent.command_id, str(reserved_loss)),
            )
            connection.commit()
            return Reservation(intent.command_id, CommandState.QUEUED, volume, False)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def begin_dispatch(
        self, command_id: str, attempt_id: str, *, expected_risk: RiskState | None = None
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state, account_ref, experiment_id FROM commands WHERE command_id=?",
                (command_id,),
            ).fetchone()
            if row is None:
                raise KeyError(command_id)
            if expected_risk is not None:
                self._check_risk_scope(expected_risk, row["account_ref"], row["experiment_id"])
                self._check_risk(connection, expected_risk)
            previous = CommandState(row["state"])
            if previous is not CommandState.QUEUED:
                raise RuntimeError(f"cannot dispatch command from {previous.value}")
            now = self._now()
            connection.execute(
                """
                INSERT INTO dispatch_attempts(attempt_id, command_id, started_at)
                VALUES (?, ?, ?)
                """,
                (attempt_id, command_id, now),
            )
            self._transition_in(connection, command_id, previous, CommandState.SENT, now, None)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _transition_in(
        connection: sqlite3.Connection,
        command_id: str,
        previous: CommandState,
        target: CommandState,
        occurred_at: str,
        detail: str | None,
    ) -> None:
        connection.execute(
            "UPDATE commands SET state=?, updated_at=? WHERE command_id=?",
            (target.value, occurred_at, command_id),
        )
        connection.execute(
            """
            INSERT INTO command_transitions(command_id, from_state, to_state, occurred_at, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (command_id, previous.value, target.value, occurred_at, detail),
        )

    def transition(self, command_id: str, target: CommandState, detail: str | None = None) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM commands WHERE command_id=?", (command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(command_id)
            self._transition_in(
                connection,
                command_id,
                CommandState(row["state"]),
                target,
                self._now(),
                detail,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def apply_broker_snapshot(self, snapshot: BrokerSnapshot) -> CommandState:
        snapshot = BrokerSnapshot.model_validate(snapshot.model_dump())
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM commands WHERE command_id=?", (snapshot.command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(snapshot.command_id)
            target = self._apply_broker_snapshot_in(connection, row, snapshot)
            connection.commit()
            return target
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def validate_broker_snapshot(self, snapshot: BrokerSnapshot) -> None:
        snapshot = BrokerSnapshot.model_validate(snapshot.model_dump())
        with self._connect() as db:
            db.execute("BEGIN")
            row = db.execute(
                "SELECT * FROM commands WHERE command_id=?", (snapshot.command_id,)
            ).fetchone()
            if row is None:
                raise BrokerEvidenceConflict()
            self._validate_broker_evidence(db, row, snapshot)

    @staticmethod
    def _broker_target(snapshot):
        if snapshot.terminal_state is not None:
            return snapshot.terminal_state
        if snapshot.remaining_volume:
            return (
                CommandState.PARTIALLY_FILLED
                if snapshot.filled_volume
                else CommandState.ACKNOWLEDGED
            )
        if snapshot.open_position_volume:
            return (
                CommandState.FILLED
                if snapshot.stop_loss_confirmed
                else CommandState.PROTECTION_FAILED
            )
        raise BrokerEvidenceConflict()

    @classmethod
    def _apply_broker_snapshot_in(cls, db, row, snapshot, *, target_override=None):
        cls._validate_broker_evidence(db, row, snapshot)
        target = target_override or cls._broker_target(snapshot)
        db.execute(
            """
            INSERT INTO broker_orders(
                order_ticket, command_id, position_id, requested_volume,
                filled_volume, remaining_volume, sl_confirmed
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_ticket) DO UPDATE SET
                filled_volume=excluded.filled_volume,
                remaining_volume=excluded.remaining_volume,
                sl_confirmed=excluded.sl_confirmed,
                position_id=excluded.position_id
            """,
            (
                snapshot.order_ticket,
                snapshot.command_id,
                snapshot.position_id,
                str(snapshot.requested_volume),
                str(snapshot.filled_volume),
                str(snapshot.remaining_volume),
                int(snapshot.stop_loss_confirmed),
            ),
        )
        db.execute(
            """
            INSERT INTO broker_order_lifecycle(command_id,cancelled_volume,closed_volume)
            VALUES (?, ?, ?)
            ON CONFLICT(command_id) DO UPDATE SET
                cancelled_volume=excluded.cancelled_volume,
                closed_volume=excluded.closed_volume
            """,
            (
                snapshot.command_id,
                str(snapshot.cancelled_volume),
                str(snapshot.closed_volume),
            ),
        )
        for deal in snapshot.deals:
            db.execute(
                """
                INSERT OR IGNORE INTO broker_deals(deal_ticket, command_id, volume, price)
                VALUES (?, ?, ?, ?)
                """,
                (deal.deal_ticket, snapshot.command_id, str(deal.volume), str(deal.price)),
            )
            db.execute(
                """
                INSERT INTO broker_deal_financials(
                    deal_ticket,profit,commission,swap,fee,occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(deal_ticket) DO UPDATE SET
                    profit=excluded.profit,
                    commission=excluded.commission,
                    swap=excluded.swap,
                    fee=excluded.fee,
                    occurred_at=excluded.occurred_at
                """,
                (
                    deal.deal_ticket,
                    str(deal.profit),
                    str(deal.commission),
                    str(deal.swap),
                    str(deal.fee),
                    deal.occurred_at.isoformat() if deal.occurred_at else None,
                ),
            )
        db.execute(
            "UPDATE commands SET protected=? WHERE command_id=?",
            (int(snapshot.stop_loss_confirmed), snapshot.command_id),
        )
        previous = CommandState(row["state"])
        if previous is not target:
            cls._transition_in(
                db,
                snapshot.command_id,
                previous,
                target,
                cls._now(),
                "broker reconciliation",
            )
        if target in {
            CommandState.REJECTED,
            CommandState.CLOSED,
            CommandState.CANCELLED,
            CommandState.EXPIRED,
        }:
            db.execute("DELETE FROM exposure_slots WHERE command_id=?", (snapshot.command_id,))
        return target

    @staticmethod
    def _validate_broker_evidence(db, row, snapshot):
        def require(condition):
            if not condition:
                raise BrokerEvidenceConflict()

        require(
            snapshot.terminal_state
            in {
                None,
                CommandState.REJECTED,
                CommandState.CANCELLED,
                CommandState.CLOSED,
                CommandState.EXPIRED,
            }
        )
        require(len(snapshot.deals) <= 1000)
        numbers = [
            snapshot.requested_volume,
            snapshot.filled_volume,
            snapshot.remaining_volume,
            snapshot.cancelled_volume,
            snapshot.closed_volume,
            *(d.volume for d in snapshot.deals),
            *(d.price for d in snapshot.deals),
            *(d.profit for d in snapshot.deals),
            *(d.commission for d in snapshot.deals),
            *(d.swap for d in snapshot.deals),
            *(d.fee for d in snapshot.deals),
        ]
        require(
            all(
                n.is_finite()
                and len(n.as_tuple().digits) <= 80
                and -100 <= n.as_tuple().exponent <= 100
                for n in numbers
            )
        )
        require(snapshot.requested_volume == Decimal(row["volume"]))
        with localcontext() as context:
            context.prec = 512
            require(
                snapshot.filled_volume + snapshot.remaining_volume + snapshot.cancelled_volume
                == snapshot.requested_volume
            )
            require(sum((d.volume for d in snapshot.deals), Decimal(0)) == snapshot.filled_volume)
            require(snapshot.closed_volume <= snapshot.filled_volume)
        require(bool(snapshot.order_ticket) and len(snapshot.order_ticket) <= 128)
        require(len({d.deal_ticket for d in snapshot.deals}) == len(snapshot.deals))
        require(all(d.deal_ticket and len(d.deal_ticket) <= 128 for d in snapshot.deals))
        require(not snapshot.filled_volume or bool(snapshot.position_id))
        require(snapshot.position_id is None or 0 < len(snapshot.position_id) <= 128)
        require(not snapshot.stop_loss_confirmed or snapshot.open_position_volume > 0)
        if snapshot.terminal_state is CommandState.REJECTED:
            require(
                snapshot.filled_volume == snapshot.cancelled_volume == snapshot.closed_volume == 0
                and snapshot.remaining_volume == snapshot.requested_volume
                and not snapshot.deals
                and snapshot.position_id is None
            )
        elif snapshot.terminal_state in {CommandState.CANCELLED, CommandState.EXPIRED}:
            require(
                snapshot.filled_volume == snapshot.closed_volume == snapshot.remaining_volume == 0
                and snapshot.cancelled_volume == snapshot.requested_volume
                and not snapshot.deals
                and snapshot.position_id is None
            )
        elif snapshot.terminal_state is CommandState.CLOSED:
            require(
                snapshot.filled_volume > 0
                and snapshot.closed_volume == snapshot.filled_volume
                and snapshot.remaining_volume == 0
                and not snapshot.stop_loss_confirmed
            )
        else:
            require(snapshot.remaining_volume > 0 or snapshot.open_position_volume > 0)
        require(row["state"] not in {"created", "validated", "queued"})
        if row["state"] in {"rejected", "closed", "cancelled", "expired"}:
            require(snapshot.terminal_state is CommandState(row["state"]))
        require(
            db.execute(
                "SELECT 1 FROM dispatch_attempts WHERE command_id=?", (snapshot.command_id,)
            ).fetchone()
            is not None
        )
        existing = db.execute(
            "SELECT * FROM broker_orders WHERE command_id=? OR order_ticket=?",
            (snapshot.command_id, snapshot.order_ticket),
        ).fetchall()
        for order in existing:
            require(
                order["command_id"] == snapshot.command_id
                and order["order_ticket"] == snapshot.order_ticket
                and Decimal(order["requested_volume"]) == snapshot.requested_volume
                and Decimal(order["filled_volume"]) <= snapshot.filled_volume
                and Decimal(order["remaining_volume"]) >= snapshot.remaining_volume
                and (order["position_id"] is None or order["position_id"] == snapshot.position_id)
            )
        lifecycle = db.execute(
            "SELECT * FROM broker_order_lifecycle WHERE command_id=?", (snapshot.command_id,)
        ).fetchone()
        if lifecycle:
            require(
                Decimal(lifecycle["cancelled_volume"]) <= snapshot.cancelled_volume
                and Decimal(lifecycle["closed_volume"]) <= snapshot.closed_volume
            )
        deals = {d.deal_ticket: d for d in snapshot.deals}
        for previous in db.execute(
            "SELECT * FROM broker_deals WHERE command_id=?", (snapshot.command_id,)
        ):
            require(previous["deal_ticket"] in deals)
            current = deals[previous["deal_ticket"]]
            require(
                Decimal(previous["volume"]) == current.volume
                and Decimal(previous["price"]) == current.price
            )
            financial = db.execute(
                "SELECT * FROM broker_deal_financials WHERE deal_ticket=?",
                (previous["deal_ticket"],),
            ).fetchone()
            if financial:
                require(
                    Decimal(financial["profit"]) == current.profit
                    and Decimal(financial["commission"]) == current.commission
                    and Decimal(financial["swap"]) == current.swap
                    and Decimal(financial["fee"]) == current.fee
                    and financial["occurred_at"]
                    == (current.occurred_at.isoformat() if current.occurred_at else None)
                )
        for ticket in deals:
            previous = db.execute(
                "SELECT command_id FROM broker_deals WHERE deal_ticket=?", (ticket,)
            ).fetchone()
            require(previous is None or previous[0] == snapshot.command_id)

    @staticmethod
    def _management_transition_in(db, command_id, previous, target, occurred_at, detail):
        db.execute(
            "UPDATE management_commands SET state=?,updated_at=? WHERE command_id=?",
            (target.value, occurred_at, command_id),
        )
        db.execute(
            """
            INSERT INTO management_transitions(
                command_id,from_state,to_state,occurred_at,detail
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                command_id,
                previous.value if previous else None,
                target.value,
                occurred_at,
                detail,
            ),
        )

    @staticmethod
    def _bounded_decimal(value, *, positive=False):
        value = Decimal(value)
        valid = (
            value.is_finite()
            and len(value.as_tuple().digits) <= 80
            and -100 <= value.as_tuple().exponent <= 100
            and (value > 0 if positive else value >= 0)
        )
        if not valid:
            raise BrokerEvidenceConflict()
        return value

    @classmethod
    def _broker_snapshot_in(cls, db, command_id):
        command = db.execute(
            "SELECT state FROM commands WHERE command_id=?", (command_id,)
        ).fetchone()
        if command is None:
            raise KeyError(command_id)
        order = db.execute(
            "SELECT * FROM broker_orders WHERE command_id=?", (command_id,)
        ).fetchone()
        if order is None:
            raise ManagementConflict("TARGET_BROKER_EVIDENCE_MISSING")
        lifecycle = db.execute(
            "SELECT * FROM broker_order_lifecycle WHERE command_id=?", (command_id,)
        ).fetchone()
        deals = []
        for row in db.execute(
            """
            SELECT d.*,f.profit,f.commission,f.swap,f.fee,f.occurred_at
            FROM broker_deals d
            LEFT JOIN broker_deal_financials f USING(deal_ticket)
            WHERE d.command_id=? ORDER BY d.deal_ticket
            """,
            (command_id,),
        ):
            if any(row[field] is None for field in ("profit", "commission", "swap", "fee")):
                raise BrokerEvidenceConflict()
            deals.append(
                BrokerDeal(
                    deal_ticket=row["deal_ticket"],
                    volume=row["volume"],
                    price=row["price"],
                    profit=row["profit"],
                    commission=row["commission"],
                    swap=row["swap"],
                    fee=row["fee"],
                    occurred_at=row["occurred_at"],
                )
            )
        state = CommandState(command["state"])
        terminal = (
            state
            if state
            in {
                CommandState.REJECTED,
                CommandState.CLOSED,
                CommandState.CANCELLED,
                CommandState.EXPIRED,
            }
            else None
        )
        return BrokerSnapshot(
            command_id=command_id,
            order_ticket=order["order_ticket"],
            position_id=order["position_id"],
            requested_volume=order["requested_volume"],
            filled_volume=order["filled_volume"],
            remaining_volume=order["remaining_volume"],
            cancelled_volume=lifecycle["cancelled_volume"] if lifecycle else "0",
            closed_volume=lifecycle["closed_volume"] if lifecycle else "0",
            deals=tuple(deals),
            stop_loss_confirmed=bool(order["sl_confirmed"]),
            terminal_state=terminal,
        )

    def broker_snapshot(self, command_id: str) -> BrokerSnapshot:
        with self._connect() as db:
            return self._broker_snapshot_in(db, command_id)

    def reserve_management(
        self,
        intent: ManagementIntent,
        *,
        expected_risk: RiskState,
    ) -> ManagementReservation:
        intent = ManagementIntent.model_validate(intent.model_dump())
        fingerprint = intent.canonical_fingerprint()
        payload = json.dumps(intent.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        now = self._now()
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            self._check_risk_scope(expected_risk, intent.account_ref, intent.experiment_id)
            self._check_risk(db, expected_risk, allow_halt=True)
            existing = db.execute(
                """
                SELECT command_id,target_command_id,operation,fingerprint,state,requested_volume
                FROM management_commands WHERE scope=? AND idempotency_key=?
                """,
                (intent.idempotency_scope, intent.idempotency_key),
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise IdempotencyConflict(
                        "idempotency key was already used with another payload"
                    )
                db.commit()
                return ManagementReservation(
                    command_id=existing["command_id"],
                    target_command_id=existing["target_command_id"],
                    operation=ManagementOperation(existing["operation"]),
                    state=CommandState(existing["state"]),
                    volume=Decimal(existing["requested_volume"]),
                    duplicate=True,
                )
            if db.execute(
                "SELECT 1 FROM commands WHERE command_id=?", (intent.command_id,)
            ).fetchone():
                raise ManagementConflict("COMMAND_ID_CONFLICT")
            target = db.execute(
                "SELECT * FROM commands WHERE command_id=?", (intent.target_command_id,)
            ).fetchone()
            if target is None:
                raise ManagementConflict("TARGET_COMMAND_NOT_FOUND")
            target_intent = CommandIntent.model_validate_json(target["payload_json"])
            if (
                target["account_ref"] != intent.account_ref
                or target["experiment_id"] != intent.experiment_id
                or target_intent.symbol != intent.symbol
            ):
                raise ManagementConflict("TARGET_BINDING_MISMATCH")
            if db.execute(
                """
                SELECT 1 FROM management_commands
                WHERE target_command_id=?
                  AND state NOT IN ('closed','cancelled','rejected','expired')
                """,
                (intent.target_command_id,),
            ).fetchone():
                raise ManagementConflict()
            snapshot = self._broker_snapshot_in(db, intent.target_command_id)
            if intent.operation is ManagementOperation.CANCEL:
                if snapshot.remaining_volume <= 0:
                    raise ManagementConflict("NO_PENDING_ORDER")
                volume = snapshot.remaining_volume
            else:
                if snapshot.remaining_volume:
                    raise ManagementConflict("PENDING_CANCEL_REQUIRED")
                if snapshot.open_position_volume <= 0:
                    raise ManagementConflict("NO_OPEN_POSITION")
                volume = snapshot.open_position_volume
            db.execute(
                """
                INSERT INTO management_commands(
                    command_id,scope,idempotency_key,fingerprint,account_ref,
                    experiment_id,target_command_id,operation,payload_json,
                    requested_volume,state,created_at,updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.command_id,
                    intent.idempotency_scope,
                    intent.idempotency_key,
                    fingerprint,
                    intent.account_ref,
                    intent.experiment_id,
                    intent.target_command_id,
                    intent.operation.value,
                    payload,
                    str(volume),
                    CommandState.QUEUED.value,
                    now,
                    now,
                ),
            )
            previous = None
            for state in (
                CommandState.CREATED,
                CommandState.VALIDATED,
                CommandState.QUEUED,
            ):
                self._management_transition_in(db, intent.command_id, previous, state, now, None)
                previous = state
            db.commit()
            return ManagementReservation(
                intent.command_id,
                intent.target_command_id,
                intent.operation,
                CommandState.QUEUED,
                volume,
                False,
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def begin_management_dispatch(
        self,
        command_id: str,
        attempt_id: str,
        *,
        expected_risk: RiskState,
    ) -> None:
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM management_commands WHERE command_id=?", (command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(command_id)
            self._check_risk_scope(expected_risk, row["account_ref"], row["experiment_id"])
            self._check_risk(db, expected_risk, allow_halt=True)
            if CommandState(row["state"]) is not CommandState.QUEUED:
                raise ManagementConflict("MANAGEMENT_NOT_QUEUED")
            target = db.execute(
                "SELECT state FROM commands WHERE command_id=?", (row["target_command_id"],)
            ).fetchone()
            if target is None or CommandState(target["state"]) in {
                CommandState.CLOSED,
                CommandState.CANCELLED,
                CommandState.REJECTED,
                CommandState.EXPIRED,
            }:
                raise ManagementConflict("TARGET_NOT_ACTIVE")
            now = self._now()
            db.execute(
                "INSERT INTO management_attempts VALUES (?, ?, ?, NULL)",
                (attempt_id, command_id, now),
            )
            self._management_transition_in(
                db,
                command_id,
                CommandState.QUEUED,
                CommandState.SENT,
                now,
                None,
            )
            if ManagementOperation(row["operation"]) is ManagementOperation.CLOSE:
                previous = CommandState(target["state"])
                if previous is not CommandState.CLOSING:
                    self._transition_in(
                        db,
                        row["target_command_id"],
                        previous,
                        CommandState.CLOSING,
                        now,
                        "close management dispatch",
                    )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def transition_management(
        self, command_id: str, target: CommandState, detail: str | None = None
    ) -> None:
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT state FROM management_commands WHERE command_id=?", (command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(command_id)
            previous = CommandState(row["state"])
            if previous is not target:
                self._management_transition_in(
                    db, command_id, previous, target, self._now(), detail
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @classmethod
    def _validate_management_evidence(cls, db, row, snapshot):
        def require(condition):
            if not condition:
                raise BrokerEvidenceConflict()

        require(
            snapshot.command_id == row["command_id"]
            and snapshot.target_command_id == row["target_command_id"]
            and snapshot.operation is ManagementOperation(row["operation"])
            and snapshot.requested_volume == Decimal(row["requested_volume"])
            and snapshot.terminal_state
            in {
                None,
                CommandState.CLOSED,
                CommandState.CANCELLED,
                CommandState.REJECTED,
            }
            and CommandState(row["state"])
            not in {CommandState.CREATED, CommandState.VALIDATED, CommandState.QUEUED}
            and len(snapshot.deals) <= 1000
        )
        local_state = CommandState(row["state"])
        if local_state in {
            CommandState.CLOSED,
            CommandState.CANCELLED,
            CommandState.REJECTED,
            CommandState.EXPIRED,
        }:
            require(snapshot.terminal_state is local_state)
        require(
            db.execute(
                "SELECT 1 FROM management_attempts WHERE command_id=?",
                (snapshot.command_id,),
            ).fetchone()
            is not None
        )
        numbers = [
            snapshot.requested_volume,
            snapshot.completed_volume,
            snapshot.remaining_volume,
            *(deal.volume for deal in snapshot.deals),
            *(deal.price for deal in snapshot.deals),
            *(deal.profit for deal in snapshot.deals),
            *(deal.commission for deal in snapshot.deals),
            *(deal.swap for deal in snapshot.deals),
            *(deal.fee for deal in snapshot.deals),
        ]
        require(
            all(
                number.is_finite()
                and len(number.as_tuple().digits) <= 80
                and -100 <= number.as_tuple().exponent <= 100
                for number in numbers
            )
        )
        with localcontext() as context:
            context.prec = 512
            require(
                snapshot.completed_volume + snapshot.remaining_volume == snapshot.requested_volume
            )
        current = cls._broker_snapshot_in(db, row["target_command_id"])
        own_outcome = db.execute(
            "SELECT * FROM management_outcomes WHERE command_id=?",
            (snapshot.command_id,),
        ).fetchone()
        previous_completed = (
            Decimal(own_outcome["completed_volume"]) if own_outcome is not None else Decimal(0)
        )
        if own_outcome is not None:
            previous_observed = datetime.fromisoformat(own_outcome["observed_at"])
            require(
                previous_observed.tzinfo is not None
                and previous_observed.utcoffset() is not None
                and previous_observed <= snapshot.observed_at
            )
        require(previous_completed <= snapshot.completed_volume)
        completed_delta = snapshot.completed_volume - previous_completed
        target_deals = {deal.deal_ticket: deal for deal in snapshot.target.deals}
        current_deals = {deal.deal_ticket: deal for deal in current.deals}
        require(
            snapshot.target.command_id == current.command_id
            and snapshot.target.order_ticket == current.order_ticket
            and snapshot.target.position_id == current.position_id
            and snapshot.target.requested_volume == current.requested_volume
            and snapshot.target.filled_volume == current.filled_volume
            and len(target_deals) == len(snapshot.target.deals)
            and target_deals == current_deals
        )
        if snapshot.operation is ManagementOperation.CANCEL:
            require(
                snapshot.broker_order_ticket == current.order_ticket
                and snapshot.position_id == current.position_id
                and current.remaining_volume == snapshot.remaining_volume + completed_delta
                and not snapshot.deals
                and snapshot.terminal_state in {CommandState.CANCELLED, CommandState.REJECTED}
            )
            if snapshot.terminal_state is CommandState.REJECTED:
                require(
                    snapshot.completed_volume == 0
                    and snapshot.remaining_volume == snapshot.requested_volume
                    and snapshot.target == current
                )
            else:
                require(
                    snapshot.completed_volume == snapshot.requested_volume
                    and snapshot.remaining_volume == 0
                    and snapshot.target.remaining_volume == 0
                    and snapshot.target.cancelled_volume
                    == current.cancelled_volume + completed_delta
                    and snapshot.target.closed_volume == current.closed_volume
                    and snapshot.target.terminal_state
                    == (CommandState.CANCELLED if current.open_position_volume == 0 else None)
                )
        else:
            require(
                current.remaining_volume == 0
                and current.open_position_volume == snapshot.remaining_volume + completed_delta
                and snapshot.position_id == current.position_id
                and bool(snapshot.position_id)
            )
            with localcontext() as context:
                context.prec = 512
                require(
                    sum((deal.volume for deal in snapshot.deals), Decimal(0))
                    == snapshot.completed_volume
                )
            if snapshot.terminal_state is CommandState.REJECTED:
                require(
                    snapshot.completed_volume == 0
                    and snapshot.remaining_volume == snapshot.requested_volume
                    and not snapshot.deals
                    and snapshot.target == current
                )
            elif snapshot.terminal_state is CommandState.CLOSED:
                require(
                    snapshot.completed_volume == snapshot.requested_volume
                    and snapshot.remaining_volume == 0
                    and snapshot.target.closed_volume == current.closed_volume + completed_delta
                    and snapshot.target.terminal_state is CommandState.CLOSED
                )
            else:
                require(
                    0 < snapshot.completed_volume < snapshot.requested_volume
                    and snapshot.remaining_volume > 0
                    and snapshot.target.closed_volume == current.closed_volume + completed_delta
                    and snapshot.target.terminal_state is None
                )
            require(
                snapshot.target.remaining_volume == current.remaining_volume
                and snapshot.target.cancelled_volume == current.cancelled_volume
                and snapshot.target.open_position_volume == snapshot.remaining_volume
            )
        existing = db.execute(
            "SELECT * FROM management_outcomes WHERE command_id=? OR broker_order_ticket=?",
            (snapshot.command_id, snapshot.broker_order_ticket),
        ).fetchall()
        for outcome in existing:
            require(
                outcome["command_id"] == snapshot.command_id
                and outcome["broker_order_ticket"] == snapshot.broker_order_ticket
                and outcome["position_id"] == snapshot.position_id
                and Decimal(outcome["requested_volume"]) == snapshot.requested_volume
                and Decimal(outcome["completed_volume"]) <= snapshot.completed_volume
                and Decimal(outcome["remaining_volume"]) >= snapshot.remaining_volume
            )
        deals = {deal.deal_ticket: deal for deal in snapshot.deals}
        require(len(deals) == len(snapshot.deals))
        require(
            all(
                deal.occurred_at is None or deal.occurred_at <= snapshot.observed_at
                for deal in snapshot.deals
            )
        )
        for previous in db.execute(
            "SELECT * FROM management_deals WHERE command_id=?", (snapshot.command_id,)
        ):
            require(previous["deal_ticket"] in deals)
            current_deal = deals[previous["deal_ticket"]]
            require(
                Decimal(previous["volume"]) == current_deal.volume
                and Decimal(previous["price"]) == current_deal.price
                and Decimal(previous["profit"]) == current_deal.profit
                and Decimal(previous["commission"]) == current_deal.commission
                and Decimal(previous["swap"]) == current_deal.swap
                and Decimal(previous["fee"]) == current_deal.fee
                and previous["occurred_at"]
                == (current_deal.occurred_at.isoformat() if current_deal.occurred_at else None)
            )
        for ticket in deals:
            previous = db.execute(
                "SELECT command_id FROM management_deals WHERE deal_ticket=?", (ticket,)
            ).fetchone()
            require(previous is None or previous["command_id"] == snapshot.command_id)

    def validate_management_snapshot(self, snapshot: ManagementSnapshot) -> None:
        snapshot = ManagementSnapshot.model_validate(snapshot.model_dump())
        with self._connect() as db:
            db.execute("BEGIN")
            row = db.execute(
                "SELECT * FROM management_commands WHERE command_id=?",
                (snapshot.command_id,),
            ).fetchone()
            if row is None:
                raise BrokerEvidenceConflict()
            self._validate_management_evidence(db, row, snapshot)

    def apply_management_snapshot(self, snapshot: ManagementSnapshot) -> CommandState:
        snapshot = ManagementSnapshot.model_validate(snapshot.model_dump())
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM management_commands WHERE command_id=?",
                (snapshot.command_id,),
            ).fetchone()
            if row is None:
                raise BrokerEvidenceConflict()
            self._validate_management_evidence(db, row, snapshot)
            db.execute(
                """
                INSERT INTO management_outcomes(
                    command_id,broker_order_ticket,position_id,requested_volume,
                    completed_volume,remaining_volume,observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(command_id) DO UPDATE SET
                    completed_volume=excluded.completed_volume,
                    remaining_volume=excluded.remaining_volume,
                    observed_at=excluded.observed_at
                """,
                (
                    snapshot.command_id,
                    snapshot.broker_order_ticket,
                    snapshot.position_id,
                    str(snapshot.requested_volume),
                    str(snapshot.completed_volume),
                    str(snapshot.remaining_volume),
                    snapshot.observed_at.isoformat(),
                ),
            )
            for deal in snapshot.deals:
                db.execute(
                    """
                    INSERT OR IGNORE INTO management_deals(
                        deal_ticket,command_id,volume,price,profit,commission,
                        swap,fee,occurred_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        deal.deal_ticket,
                        snapshot.command_id,
                        str(deal.volume),
                        str(deal.price),
                        str(deal.profit),
                        str(deal.commission),
                        str(deal.swap),
                        str(deal.fee),
                        deal.occurred_at.isoformat() if deal.occurred_at else None,
                    ),
                )
            target_row = db.execute(
                "SELECT * FROM commands WHERE command_id=?", (snapshot.target_command_id,)
            ).fetchone()
            target_override = (
                CommandState.CLOSING
                if snapshot.operation is ManagementOperation.CLOSE
                and snapshot.terminal_state is None
                else None
            )
            self._apply_broker_snapshot_in(
                db, target_row, snapshot.target, target_override=target_override
            )
            target = snapshot.terminal_state or CommandState.CLOSING
            previous = CommandState(row["state"])
            if previous is not target:
                self._management_transition_in(
                    db,
                    snapshot.command_id,
                    previous,
                    target,
                    self._now(),
                    "broker management reconciliation",
                )
            db.commit()
            return target
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def management_command(self, command_id: str) -> sqlite3.Row:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM management_commands WHERE command_id=?", (command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(command_id)
            return row

    def unresolved_management_ids(self) -> list[str]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT command_id FROM management_commands
                WHERE state NOT IN ('closed','cancelled','rejected','expired')
                ORDER BY created_at
                """
            ).fetchall()
        return [row["command_id"] for row in rows]

    def final_trade_audit(self, command_id: str) -> TradeAudit:
        with self._connect() as db, localcontext() as arithmetic:
            arithmetic.prec = 512
            command = db.execute(
                "SELECT * FROM commands WHERE command_id=?", (command_id,)
            ).fetchone()
            if (
                command is None
                or CommandState(command["state"]) is not CommandState.CLOSED
                or db.execute(
                    "SELECT 1 FROM exposure_slots WHERE command_id=?", (command_id,)
                ).fetchone()
                or db.execute(
                    """
                    SELECT 1 FROM management_commands
                    WHERE target_command_id=?
                      AND state NOT IN ('closed','cancelled','rejected','expired')
                    """,
                    (command_id,),
                ).fetchone()
            ):
                raise ManagementConflict("FINAL_AUDIT_NOT_READY")
            snapshot = self._broker_snapshot_in(db, command_id)
            closing = db.execute(
                """
                SELECT * FROM management_commands
                WHERE target_command_id=? AND operation='close' AND state='closed'
                ORDER BY created_at DESC LIMIT 1
                """,
                (command_id,),
            ).fetchone()
            if closing is None:
                raise ManagementConflict("FINAL_AUDIT_NOT_READY")
            intent = ManagementIntent.model_validate_json(closing["payload_json"])
            entry = db.execute(
                """
                SELECT d.deal_ticket,COALESCE(f.commission,'0') commission,
                       COALESCE(f.swap,'0') swap,COALESCE(f.fee,'0') fee
                FROM broker_deals d
                LEFT JOIN broker_deal_financials f USING(deal_ticket)
                WHERE d.command_id=? ORDER BY d.deal_ticket
                """,
                (command_id,),
            ).fetchall()
            exits = db.execute(
                """
                SELECT d.*,m.broker_order_ticket
                FROM management_deals d
                JOIN management_outcomes m USING(command_id)
                JOIN management_commands c USING(command_id)
                WHERE c.target_command_id=? AND c.operation='close'
                ORDER BY d.deal_ticket
                """,
                (command_id,),
            ).fetchall()
            gross = sum((Decimal(row["profit"]) for row in exits), Decimal(0))
            commission = sum((Decimal(row["commission"]) for row in (*entry, *exits)), Decimal(0))
            swap = sum((Decimal(row["swap"]) for row in (*entry, *exits)), Decimal(0))
            fee = sum((Decimal(row["fee"]) for row in (*entry, *exits)), Decimal(0))
            exit_orders = tuple(dict.fromkeys(row["broker_order_ticket"] for row in exits))
            original = CommandIntent.model_validate_json(command["payload_json"])
            return TradeAudit(
                command_id=command_id,
                account_ref=command["account_ref"],
                experiment_id=command["experiment_id"],
                symbol=original.symbol,
                entry_order_ticket=snapshot.order_ticket,
                position_id=snapshot.position_id,
                requested_volume=snapshot.requested_volume,
                entry_volume=snapshot.filled_volume,
                cancelled_volume=snapshot.cancelled_volume,
                closed_volume=snapshot.closed_volume,
                entry_deal_tickets=tuple(row["deal_ticket"] for row in entry),
                exit_order_tickets=exit_orders,
                exit_deal_tickets=tuple(row["deal_ticket"] for row in exits),
                gross_profit=gross,
                commission=commission,
                swap=swap,
                fee=fee,
                net_pnl=gross + commission + swap + fee,
                close_reason=intent.reason,
            )

    @staticmethod
    def _risk_row(row):
        if row is None:
            return None
        return RiskState(
            account_ref=row["account_ref"],
            experiment_id=row["experiment_id"],
            bangkok_day=row["bangkok_day"],
            daily_baseline=Decimal(row["daily_baseline"]),
            experiment_baseline=Decimal(row["experiment_baseline"]),
            daily_halt=bool(row["daily_halt"]),
            total_halt=bool(row["total_halt"]),
            updated_at=row["updated_at"],
        )

    @classmethod
    def _check_risk(cls, db, expected, *, allow_halt=False):
        current = cls._risk_row(
            db.execute(
                "SELECT * FROM risk_state WHERE account_ref=? AND experiment_id=?",
                (expected.account_ref, expected.experiment_id),
            ).fetchone()
        )
        if allow_halt:
            compatible = (
                current is not None
                and current.account_ref == expected.account_ref
                and current.experiment_id == expected.experiment_id
                and current.bangkok_day == expected.bangkok_day
                and current.daily_baseline == expected.daily_baseline
                and current.experiment_baseline == expected.experiment_baseline
                and current.updated_at >= expected.updated_at
                and (not expected.daily_halt or current.daily_halt)
                and (not expected.total_halt or current.total_halt)
            )
        else:
            compatible = current == expected and not (current.daily_halt or current.total_halt)
        if not compatible:
            raise RiskStateConflict()

    @staticmethod
    def _check_risk_scope(expected, account_ref, experiment_id):
        if (expected.account_ref, expected.experiment_id) != (account_ref, experiment_id):
            raise RiskStateConflict()

    def startup_state(self, account_ref, experiment_id):
        with self._connect() as db:
            db.execute("BEGIN")
            risk = self._risk_row(
                db.execute(
                    "SELECT * FROM risk_state WHERE account_ref=? AND experiment_id=?",
                    (account_ref, experiment_id),
                ).fetchone()
            )
            active = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM commands WHERE state NOT IN "
                    "('closed','rejected','expired','cancelled') LIMIT 1001"
                )
            ]
            exposure = [dict(row) for row in db.execute("SELECT * FROM exposure_slots LIMIT 1001")]
            management = [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM management_commands WHERE state NOT IN "
                    "('closed','rejected','expired','cancelled') LIMIT 1001"
                )
            ]
            return risk, active, exposure, management

    def command(self, command_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM commands WHERE command_id=?", (command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(command_id)
            return row

    def save_risk_state(self, state: RiskState) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO risk_state(
                    account_ref, experiment_id, bangkok_day, daily_baseline,
                    experiment_baseline, daily_halt, total_halt, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_ref, experiment_id) DO UPDATE SET
                    bangkok_day=excluded.bangkok_day,
                    daily_baseline=excluded.daily_baseline,
                    experiment_baseline=excluded.experiment_baseline,
                    daily_halt=excluded.daily_halt,
                    total_halt=excluded.total_halt,
                    updated_at=excluded.updated_at
                """,
                (
                    state.account_ref,
                    state.experiment_id,
                    state.bangkok_day.isoformat(),
                    str(state.daily_baseline),
                    str(state.experiment_baseline),
                    int(state.daily_halt),
                    int(state.total_halt),
                    state.updated_at.isoformat(),
                ),
            )
            connection.commit()

    def latch_halts(
        self,
        account_ref: str,
        experiment_id: str,
        equity: Decimal,
        observed_at: datetime,
    ) -> RiskState:
        equity = self._bounded_decimal(equity, positive=True)
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise RiskStateConflict()
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM risk_state WHERE account_ref=? AND experiment_id=?",
                (account_ref, experiment_id),
            ).fetchone()
            current = self._risk_row(row)
            if (
                current is None
                or current.updated_at > observed_at
                or current.account_ref != account_ref
                or current.experiment_id != experiment_id
            ):
                raise RiskStateConflict()
            daily_floor = current.daily_baseline * (Decimal(1) - DAILY_LOSS_LIMIT)
            experiment_floor = current.experiment_baseline * (Decimal(1) - EXPERIMENT_LOSS_LIMIT)
            updated = current.model_copy(
                update={
                    "daily_halt": current.daily_halt or equity <= daily_floor,
                    "total_halt": current.total_halt or equity <= experiment_floor,
                    "updated_at": observed_at,
                }
            )
            db.execute(
                """
                UPDATE risk_state
                SET daily_halt=?,total_halt=?,updated_at=?
                WHERE account_ref=? AND experiment_id=?
                """,
                (
                    int(updated.daily_halt),
                    int(updated.total_halt),
                    updated.updated_at.isoformat(),
                    account_ref,
                    experiment_id,
                ),
            )
            db.commit()
            return updated
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def risk_state(self, account_ref: str, experiment_id: str) -> RiskState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM risk_state WHERE account_ref=? AND experiment_id=?",
                (account_ref, experiment_id),
            ).fetchone()
        return self._risk_row(row)

    def unresolved_command_ids(self) -> list[str]:
        terminal = (
            CommandState.CLOSED.value,
            CommandState.REJECTED.value,
            CommandState.EXPIRED.value,
            CommandState.CANCELLED.value,
        )
        placeholders = ",".join("?" for _ in terminal)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT command_id FROM commands
                WHERE state NOT IN ({placeholders})
                ORDER BY created_at
                """,
                terminal,
            ).fetchall()
        return [row["command_id"] for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            return {
                name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in (
                    "commands",
                    "command_transitions",
                    "dispatch_attempts",
                    "broker_orders",
                    "broker_deals",
                    "broker_order_lifecycle",
                    "broker_deal_financials",
                    "exposure_slots",
                    "management_commands",
                    "management_transitions",
                    "management_attempts",
                    "management_outcomes",
                    "management_deals",
                )
            }
