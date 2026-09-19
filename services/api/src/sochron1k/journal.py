from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path

from .models import BrokerSnapshot, CommandIntent, CommandState, RiskState


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


@dataclass(frozen=True)
class Reservation:
    command_id: str
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
        if snapshot.terminal_state is CommandState.REJECTED:
            target = CommandState.REJECTED
        elif snapshot.filled_volume == 0:
            target = CommandState.ACKNOWLEDGED
        elif snapshot.remaining_volume > 0:
            target = CommandState.PARTIALLY_FILLED
        elif not snapshot.stop_loss_confirmed:
            target = CommandState.PROTECTION_FAILED
        else:
            target = CommandState.FILLED
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM commands WHERE command_id=?", (snapshot.command_id,)
            ).fetchone()
            if row is None:
                raise KeyError(snapshot.command_id)
            self._validate_broker_evidence(connection, row, snapshot)
            if snapshot.order_ticket:
                connection.execute(
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
            for deal in snapshot.deals:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO broker_deals(deal_ticket, command_id, volume, price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (deal.deal_ticket, snapshot.command_id, str(deal.volume), str(deal.price)),
                )
            connection.execute(
                "UPDATE commands SET protected=? WHERE command_id=?",
                (int(snapshot.stop_loss_confirmed), snapshot.command_id),
            )
            self._transition_in(
                connection,
                snapshot.command_id,
                CommandState(row["state"]),
                target,
                self._now(),
                "broker reconciliation",
            )
            if target in {CommandState.REJECTED, CommandState.CLOSED, CommandState.CANCELLED}:
                connection.execute(
                    "DELETE FROM exposure_slots WHERE command_id=?", (snapshot.command_id,)
                )
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
    def _validate_broker_evidence(db, row, snapshot):
        def require(condition):
            if not condition:
                raise BrokerEvidenceConflict()

        require(snapshot.terminal_state in {None, CommandState.REJECTED})
        require(len(snapshot.deals) <= 1000)
        numbers = [
            snapshot.requested_volume,
            snapshot.filled_volume,
            snapshot.remaining_volume,
            *(d.volume for d in snapshot.deals),
            *(d.price for d in snapshot.deals),
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
            require(snapshot.filled_volume + snapshot.remaining_volume == snapshot.requested_volume)
            require(sum((d.volume for d in snapshot.deals), Decimal(0)) == snapshot.filled_volume)
        require(bool(snapshot.order_ticket) and len(snapshot.order_ticket) <= 128)
        require(len({d.deal_ticket for d in snapshot.deals}) == len(snapshot.deals))
        require(all(d.deal_ticket and len(d.deal_ticket) <= 128 for d in snapshot.deals))
        require(not snapshot.filled_volume or bool(snapshot.position_id))
        require(snapshot.position_id is None or 0 < len(snapshot.position_id) <= 128)
        require(not snapshot.stop_loss_confirmed or snapshot.filled_volume > 0)
        require(snapshot.terminal_state is None or snapshot.filled_volume == 0)
        require(
            row["state"] not in {"closed", "cancelled", "expired", "created", "validated", "queued"}
        )
        require(row["state"] != "rejected" or snapshot.terminal_state is CommandState.REJECTED)
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
                and (order["position_id"] is None or order["position_id"] == snapshot.position_id)
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
        for ticket in deals:
            previous = db.execute(
                "SELECT command_id FROM broker_deals WHERE deal_ticket=?", (ticket,)
            ).fetchone()
            require(previous is None or previous[0] == snapshot.command_id)

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
    def _check_risk(cls, db, expected):
        current = cls._risk_row(
            db.execute(
                "SELECT * FROM risk_state WHERE account_ref=? AND experiment_id=?",
                (expected.account_ref, expected.experiment_id),
            ).fetchone()
        )
        if current != expected or current.daily_halt or current.total_halt:
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
            return risk, active, exposure

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
                    "exposure_slots",
                )
            }
