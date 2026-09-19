"""Read-only admission of a causal local recovery set, never permission to resume."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import ExitStack, closing
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path, PurePosixPath
from uuid import UUID

from pydantic import Field, StrictInt, field_validator
from sochron1k.bar_history import MAX_DATABASE_BYTES, ArchivedBar
from sochron1k.chart import EPOCH, PERIODS, ChartFrame, ChartSettings
from sochron1k.models import (
    CommandIntent,
    CommandState,
    ExecutorRejection,
    ManagementIntent,
    ManagementOperation,
    RiskState,
    StrictModel,
)
from sochron1k.sqlite_snapshot import verify_snapshot
from sochron1k.telemetry import DemoIdentity

from .native_source import PRICE_TEXT, SourceCursor, _json
from .sync_config import origin
from .sync_journal import MAX_JOURNAL_BYTES, STATES, canonical, decode_batch, utc

# Exact sqlite_schema signatures of the current writers; changes need reviewed admission.
SCHEMAS = {
    "commands": (0, "66bd1ddfbe98c0556fa66180aa0fd676e460d8ccf3187ef50e132a93cf4cd7d8"),
    "archive": (1, "ccb8fa69d2d66dfbf1ee506687234255084130feea32494968f650ccc003d809"),
    "sync": (1, "9e80d5a9d5c4bd688402afb716651b6eecca5e639c92ce5681a09313b7352b5d"),
}
AUDIT_SECONDS = 30
MAX_ROWS = 100_000
TERMINAL = {"closed", "rejected", "expired", "cancelled"}


class RecoveryUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("RECOVERY_SET_UNAVAILABLE")


class RecoveryBinding(StrictModel):
    identity: DemoIdentity
    active_experiment_id: str = Field(min_length=1, max_length=128)
    archive_id: UUID
    owner_id: UUID
    source_directory: str = Field(min_length=1, max_length=4096)
    destination: str
    offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)
    chart: ChartSettings

    @field_validator("source_directory")
    @classmethod
    def original_path(cls, value):
        # An original-host identity, not a path to resolve, open or silently rebind.
        path = PurePosixPath(value)
        if (
            not value.startswith("/")
            or value.startswith("//")
            or str(path) != value
            or ".." in path.parts
            or any(ord(c) < 32 for c in value)
        ):
            raise ValueError("invalid original binding")
        return value

    @field_validator("destination")
    @classmethod
    def destination_origin(cls, value):
        return origin(value)

    @field_validator("offset_seconds")
    @classmethod
    def minute_offset(cls, value):
        if value % 60:
            raise ValueError("invalid offset")
        return value

    @property
    def archive_binding(self):
        return json.dumps(
            dict(
                identity=self.identity.model_dump(mode="json"),
                offset=self.offset_seconds,
                chart=self.chart.model_dump(mode="json"),
            ),
            sort_keys=True,
        )

    @property
    def sync_binding(self):
        return canonical(
            dict(
                source_directory=self.source_directory,
                archive_id=str(self.archive_id),
                binding_json=self.archive_binding,
                owner_id=str(self.owner_id),
                destination=self.destination,
            )
        )


def _require(condition):
    if not condition:
        raise RecoveryUnavailable()


def _decimal(value, *, zero=False):
    _require(isinstance(value, str) and 0 < len(value) <= 80)
    result = Decimal(value)
    _require(result.is_finite() and (result >= 0 if zero else result > 0))
    _require(-100 <= result.as_tuple().exponent <= 100)
    return result


def _signed_decimal(value):
    _require(isinstance(value, str) and 0 < len(value) <= 80)
    result = Decimal(value)
    _require(
        result.is_finite()
        and len(result.as_tuple().digits) <= 80
        and -100 <= result.as_tuple().exponent <= 100
    )
    return result


def _bit(value):
    _require(type(value) is int and value in (0, 1))
    return bool(value)


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _hex(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _sequence(db, table, column):
    maximum = db.execute(f"SELECT COALESCE(MAX({column}),0) FROM {table}").fetchone()[0]
    rows = db.execute("SELECT name,seq FROM sqlite_sequence WHERE name=?", (table,)).fetchall()
    _require(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == maximum)
    _require(
        (maximum == 0 and not rows)
        or (len(rows) == 1 and rows[0][0] == table and rows[0][1] == maximum)
    )


def _commands(db, binding, latest, tick):
    risks = {}
    for row in db.execute("SELECT * FROM risk_state ORDER BY experiment_id"):
        tick()
        state = RiskState.model_validate(dict(row))
        _require(state.account_ref == binding.identity.account_ref)
        _require(0 < len(state.experiment_id) <= 128)
        _decimal(row["daily_baseline"])
        _decimal(row["experiment_baseline"])
        _bit(row["daily_halt"])
        _bit(row["total_halt"])
        _require(utc(row["updated_at"]) <= latest)
        risks[state.experiment_id] = dict(row)
    _require(binding.active_experiment_id in risks)
    counts = dict(
        commands=0,
        unresolved=0,
        unknown=0,
        attempts=0,
        orders=0,
        deals=0,
        exposure=0,
        management_commands=0,
        management_unresolved=0,
        management_unknown=0,
        management_attempts=0,
        management_deals=0,
        executor_rejections=0,
    )
    broker_evidence = {}
    for row in db.execute("SELECT * FROM commands ORDER BY command_id"):
        tick()
        counts["commands"] += 1
        intent = CommandIntent.model_validate(_json(row["payload_json"], 8192))
        state = CommandState(row["state"])
        _require(
            intent.account_ref == row["account_ref"] == binding.identity.account_ref
            and intent.experiment_id == row["experiment_id"]
            and intent.experiment_id in risks
            and intent.symbol == binding.identity.symbol
            and intent.operation == "open"
            and intent.command_id == row["command_id"]
            and intent.idempotency_scope == row["scope"]
            and intent.idempotency_key == row["idempotency_key"]
            and intent.canonical_fingerprint() == row["fingerprint"]
            and utc(row["created_at"]) <= utc(row["updated_at"]) <= latest
        )
        volume, loss = _decimal(row["volume"]), _decimal(row["reserved_loss"])
        protected = _bit(row["protected"])
        previous, occurred, transitions, sends = None, None, 0, []
        for event in db.execute(
            "SELECT * FROM command_transitions WHERE command_id=? ORDER BY transition_id",
            (intent.command_id,),
        ):
            tick()
            target = CommandState(event["to_state"])
            timestamp = utc(event["occurred_at"])
            _require(event["from_state"] == previous and timestamp <= latest)
            _require(occurred is None or occurred <= timestamp)
            if transitions < 3:
                _require(target.value == ("created", "validated", "queued")[transitions])
                _require(timestamp == utc(row["created_at"]))
            else:
                # These three states are created atomically by reserve, never replayed.
                _require(target.value not in {"created", "validated", "queued"})
            if target is CommandState.SENT:
                _require(previous == "queued")
                sends.append(event["occurred_at"])
            previous, occurred = target.value, timestamp
            transitions += 1
        _require(
            transitions >= 3 and previous == state.value and occurred == utc(row["updated_at"])
        )
        attempts = db.execute(
            "SELECT * FROM dispatch_attempts WHERE command_id=?", (intent.command_id,)
        ).fetchall()
        _require(len(attempts) == len(sends) <= 1)
        for attempt in attempts:
            _require(
                isinstance(attempt["attempt_id"], str) and 0 < len(attempt["attempt_id"]) <= 128
            )
            _require(attempt["started_at"] == sends[0] and attempt["outcome"] is None)
        if state.value not in {"queued", "unknown", "expired", "cancelled"}:
            _require(len(attempts) == 1)
        counts["attempts"] += len(attempts)
        slots = db.execute(
            "SELECT * FROM exposure_slots WHERE command_id=?", (intent.command_id,)
        ).fetchall()
        _require(len(slots) == int(state.value not in TERMINAL))
        for slot in slots:
            _require(
                slot["account_ref"] == intent.account_ref
                and slot["experiment_id"] == intent.experiment_id
                and _decimal(slot["reserved_loss"]) == loss
            )
        counts["exposure"] += len(slots)
        rejections = db.execute(
            "SELECT * FROM executor_rejections WHERE command_id=?", (intent.command_id,)
        ).fetchall()
        _require(len(rejections) <= 1)
        if rejections:
            rejection = ExecutorRejection.model_validate(dict(rejections[0]))
            _require(
                rejection.command_id == intent.command_id
                and rejection.target_command_id is None
                and rejection.operation == "open"
                and rejection.observed_at <= latest
                and state is CommandState.REJECTED
                and len(attempts) == 1
                and not protected
            )
            counts["executor_rejections"] += 1
        orders = db.execute(
            "SELECT * FROM broker_orders WHERE command_id=?", (intent.command_id,)
        ).fetchall()
        _require(len(orders) <= 1)
        _require(not (orders and rejections))
        if state is CommandState.REJECTED:
            _require(len(orders) + len(rejections) == 1)
        if orders:
            _require(len(attempts) == 1 and state.value not in {"created", "validated", "queued"})
        filled = Decimal(0)
        order_evidence = None
        for order in orders:
            _require(
                isinstance(order["order_ticket"], str) and 0 < len(order["order_ticket"]) <= 128
            )
            requested = _decimal(order["requested_volume"])
            filled = _decimal(order["filled_volume"], zero=True)
            remaining = _decimal(order["remaining_volume"], zero=True)
            lifecycle = db.execute(
                "SELECT * FROM broker_order_lifecycle WHERE command_id=?",
                (intent.command_id,),
            ).fetchall()
            _require(len(lifecycle) == 1)
            cancelled = _decimal(lifecycle[0]["cancelled_volume"], zero=True)
            closed = _decimal(lifecycle[0]["closed_volume"], zero=True)
            _require(
                requested == volume
                and filled + remaining + cancelled == requested
                and closed <= filled
            )
            position = filled - closed
            order_evidence = dict(
                order_ticket=order["order_ticket"],
                position_id=order["position_id"],
                requested=requested,
                filled=filled,
                remaining=remaining,
                cancelled=cancelled,
                closed=closed,
            )
            _require(_bit(order["sl_confirmed"]) == protected)
            if state is CommandState.ACKNOWLEDGED:
                _require(
                    filled == cancelled == closed == 0
                    and remaining == requested
                    and order["position_id"] is None
                    and not protected
                )
            if state is CommandState.REJECTED:
                _require(
                    filled == cancelled == closed == 0
                    and remaining == requested
                    and order["position_id"] is None
                    and not protected
                )
            if filled:
                _require(
                    isinstance(order["position_id"], str) and 0 < len(order["position_id"]) <= 128
                )
            if state is CommandState.FILLED:
                _require(remaining == 0 and position > 0 and protected)
            if state is CommandState.PARTIALLY_FILLED:
                _require(position > 0 and remaining > 0)
            if state is CommandState.PROTECTION_FAILED:
                _require(remaining == 0 and position > 0 and not protected)
            if state is CommandState.CLOSING:
                _require(remaining == 0 and position > 0)
            if state is CommandState.CLOSED:
                _require(filled > 0 and closed == filled and remaining == 0 and not protected)
            if state in {CommandState.CANCELLED, CommandState.EXPIRED}:
                _require(
                    filled == closed == remaining == 0
                    and cancelled == requested
                    and order["position_id"] is None
                    and not protected
                )
        if protected or state.value in {
            "acknowledged",
            "filled",
            "partially_filled",
            "protection_failed",
            "closing",
            "closed",
        }:
            _require(len(orders) == 1 and len(attempts) == 1)
        dealt = Decimal(0)
        for deal in db.execute(
            """
            SELECT d.*,f.profit,f.commission,f.swap,f.fee,f.occurred_at
            FROM broker_deals d
            LEFT JOIN broker_deal_financials f USING(deal_ticket)
            WHERE d.command_id=?
            """,
            (intent.command_id,),
        ):
            tick()
            _require(isinstance(deal["deal_ticket"], str) and 0 < len(deal["deal_ticket"]) <= 128)
            dealt += _decimal(deal["volume"])
            _decimal(deal["price"])
            _require(deal["profit"] is not None)
            for field in ("profit", "commission", "swap", "fee"):
                _signed_decimal(deal[field])
            if deal["occurred_at"] is not None:
                _require(utc(deal["occurred_at"]) <= latest)
            counts["deals"] += 1
        _require(dealt == filled)
        if order_evidence is not None:
            broker_evidence[intent.command_id] = order_evidence
        counts["orders"] += len(orders)
        counts["unresolved"] += int(state.value not in TERMINAL)
        counts["unknown"] += int(state is CommandState.UNKNOWN)
    _require(
        db.execute("SELECT count(*) FROM broker_order_lifecycle").fetchone()[0] == counts["orders"]
        and db.execute("SELECT count(*) FROM broker_deal_financials").fetchone()[0]
        == counts["deals"]
    )
    active_management = {}
    managed_volume = {}
    for row in db.execute("SELECT * FROM management_commands ORDER BY command_id"):
        tick()
        counts["management_commands"] += 1
        intent = ManagementIntent.model_validate(_json(row["payload_json"], 8192))
        state = CommandState(row["state"])
        _require(
            intent.command_id == row["command_id"]
            and intent.account_ref == row["account_ref"] == binding.identity.account_ref
            and intent.experiment_id == row["experiment_id"]
            and intent.experiment_id in risks
            and intent.target_command_id == row["target_command_id"]
            and intent.symbol == binding.identity.symbol
            and intent.operation.value == row["operation"]
            and intent.idempotency_scope == row["scope"]
            and intent.idempotency_key == row["idempotency_key"]
            and intent.canonical_fingerprint() == row["fingerprint"]
            and utc(row["created_at"]) <= utc(row["updated_at"]) <= latest
        )
        target = db.execute(
            "SELECT state,account_ref,experiment_id FROM commands WHERE command_id=?",
            (intent.target_command_id,),
        ).fetchone()
        _require(
            target is not None
            and target["account_ref"] == intent.account_ref
            and target["experiment_id"] == intent.experiment_id
        )
        parent = broker_evidence.get(intent.target_command_id)
        _require(parent is not None)
        volume = _decimal(row["requested_volume"])
        previous, occurred, transitions, sends = None, None, 0, []
        for event in db.execute(
            """
            SELECT * FROM management_transitions
            WHERE command_id=? ORDER BY transition_id
            """,
            (intent.command_id,),
        ):
            tick()
            current = CommandState(event["to_state"])
            timestamp = utc(event["occurred_at"])
            _require(event["from_state"] == previous and timestamp <= latest)
            _require(occurred is None or occurred <= timestamp)
            if transitions < 3:
                _require(
                    current.value == ("created", "validated", "queued")[transitions]
                    and timestamp == utc(row["created_at"])
                )
            else:
                _require(current.value not in {"created", "validated", "queued"})
            if current is CommandState.SENT:
                _require(previous == "queued")
                sends.append(event["occurred_at"])
            previous, occurred = current.value, timestamp
            transitions += 1
        _require(
            transitions >= 3 and previous == state.value and occurred == utc(row["updated_at"])
        )
        attempts = db.execute(
            "SELECT * FROM management_attempts WHERE command_id=?", (intent.command_id,)
        ).fetchall()
        _require(len(attempts) == len(sends) <= 1)
        for attempt in attempts:
            _require(
                isinstance(attempt["attempt_id"], str)
                and 0 < len(attempt["attempt_id"]) <= 128
                and attempt["started_at"] == sends[0]
                and attempt["outcome"] is None
            )
        if state is not CommandState.QUEUED:
            _require(len(attempts) == 1)
        counts["management_attempts"] += len(attempts)
        rejections = db.execute(
            "SELECT * FROM executor_rejections WHERE command_id=?", (intent.command_id,)
        ).fetchall()
        _require(len(rejections) <= 1)
        if rejections:
            rejection = ExecutorRejection.model_validate(dict(rejections[0]))
            _require(
                rejection.command_id == intent.command_id
                and rejection.target_command_id == intent.target_command_id
                and rejection.operation == intent.operation.value
                and rejection.observed_at <= latest
                and state is CommandState.REJECTED
                and len(attempts) == 1
            )
            counts["executor_rejections"] += 1
        outcomes = db.execute(
            "SELECT * FROM management_outcomes WHERE command_id=?",
            (intent.command_id,),
        ).fetchall()
        _require(len(outcomes) <= 1)
        _require(not (outcomes and rejections))
        if state is CommandState.REJECTED:
            _require(len(outcomes) + len(rejections) == 1)
        deals = db.execute(
            "SELECT * FROM management_deals WHERE command_id=? ORDER BY deal_ticket",
            (intent.command_id,),
        ).fetchall()
        completed = Decimal(0)
        if outcomes:
            outcome = outcomes[0]
            _require(
                isinstance(outcome["broker_order_ticket"], str)
                and 0 < len(outcome["broker_order_ticket"]) <= 128
                and (outcome["position_id"] is None or 0 < len(outcome["position_id"]) <= 128)
            )
            requested = _decimal(outcome["requested_volume"])
            completed = _decimal(outcome["completed_volume"], zero=True)
            remaining = _decimal(outcome["remaining_volume"], zero=True)
            observed = utc(outcome["observed_at"])
            _require(
                requested == volume and completed + remaining == requested and observed <= latest
            )
            totals = managed_volume.setdefault(
                intent.target_command_id,
                {ManagementOperation.CANCEL: Decimal(0), ManagementOperation.CLOSE: Decimal(0)},
            )
            totals[intent.operation] += completed
            dealt = Decimal(0)
            for deal in deals:
                tick()
                _require(
                    isinstance(deal["deal_ticket"], str) and 0 < len(deal["deal_ticket"]) <= 128
                )
                dealt += _decimal(deal["volume"])
                _decimal(deal["price"])
                for field in ("profit", "commission", "swap", "fee"):
                    _signed_decimal(deal[field])
                if deal["occurred_at"] is not None:
                    _require(utc(deal["occurred_at"]) <= observed)
            counts["management_deals"] += len(deals)
            if intent.operation is ManagementOperation.CLOSE:
                _require(
                    dealt == completed
                    and outcome["position_id"] == parent["position_id"]
                    and requested <= parent["filled"]
                    and completed <= parent["closed"]
                )
            else:
                _require(
                    not deals
                    and dealt == 0
                    and outcome["broker_order_ticket"] == parent["order_ticket"]
                    and outcome["position_id"] == parent["position_id"]
                    and requested <= parent["requested"]
                    and completed <= parent["cancelled"]
                )
            if state is CommandState.CLOSED:
                _require(
                    intent.operation is ManagementOperation.CLOSE
                    and completed == requested
                    and remaining == 0
                    and target["state"] == "closed"
                )
            elif state is CommandState.CANCELLED:
                _require(
                    intent.operation is ManagementOperation.CANCEL
                    and completed == requested
                    and remaining == 0
                )
            elif state is CommandState.REJECTED:
                _require(completed == 0 and remaining == requested and not deals)
            elif state is CommandState.CLOSING:
                _require(
                    intent.operation is ManagementOperation.CLOSE
                    and 0 < completed < requested
                    and remaining > 0
                    and target["state"] == "closing"
                )
            else:
                _require(False)
        else:
            _require(not deals)
            _require(
                state in {CommandState.QUEUED, CommandState.SENT, CommandState.UNKNOWN}
                or (state is CommandState.REJECTED and len(rejections) == 1)
            )
        if state.value not in TERMINAL:
            active_management[intent.target_command_id] = (
                active_management.get(intent.target_command_id, 0) + 1
            )
            _require(target["state"] not in TERMINAL)
            if intent.operation is ManagementOperation.CLOSE and state is not CommandState.QUEUED:
                _require(target["state"] == "closing")
        counts["management_unresolved"] += int(state.value not in TERMINAL)
        counts["management_unknown"] += int(state is CommandState.UNKNOWN)
    _require(
        all(value == 1 for value in active_management.values())
        and not db.execute(
            """
            SELECT 1 FROM commands
            INNER JOIN management_commands USING(command_id)
            LIMIT 1
            """
        ).fetchone()
        and db.execute("SELECT count(*) FROM management_outcomes").fetchone()[0]
        <= counts["management_commands"]
        and db.execute("SELECT count(*) FROM management_deals").fetchone()[0]
        == counts["management_deals"]
        and db.execute("SELECT count(*) FROM executor_rejections").fetchone()[0]
        == counts["executor_rejections"]
    )
    for command_id, totals in managed_volume.items():
        parent = broker_evidence[command_id]
        _require(
            totals[ManagementOperation.CANCEL] <= parent["cancelled"]
            and totals[ManagementOperation.CLOSE] <= parent["closed"]
        )
    _require(counts["exposure"] <= 1)
    _sequence(db, "command_transitions", "transition_id")
    _sequence(db, "management_transitions", "transition_id")
    return {
        **counts,
        "experiments": len(risks),
        "daily_halts": sum(row["daily_halt"] for row in risks.values()),
        "total_halts": sum(row["total_halt"] for row in risks.values()),
        "risk_sha256": _digest(canonical(risks)),
    }


def _archive(db, binding, latest, tick):
    meta = db.execute("SELECT * FROM history_meta").fetchall()
    _require(
        len(meta) == 1
        and meta[0]["id"] == 1
        and meta[0]["binding"] == binding.archive_binding
        and meta[0]["archive_id"] == str(binding.archive_id)
    )
    count, last, boot_sequences = 0, None, {}
    for row in db.execute("SELECT * FROM receipts ORDER BY receipt_id"):
        tick()
        count += 1
        timestamp = utc(row["received_at"])
        _require(
            row["receipt_id"] == count
            and str(UUID(row["boot_id"])) == row["boot_id"]
            and type(row["sequence"]) is int
            and 1 <= row["sequence"] <= 2**53 - 1
            and _hex(row["fingerprint"])
            and timestamp <= latest
            and (last is None or timestamp >= last)
        )
        last = timestamp
        _require(row["sequence"] > boot_sequences.get(row["boot_id"], 0))
        boot_sequences[row["boot_id"]] = row["sequence"]
    _sequence(db, "receipts", "receipt_id")
    counts = {name: 0 for name in PERIODS}
    for row in db.execute(
        "SELECT c.*,r.received_at FROM closed_bars c "
        "JOIN receipts r ON r.receipt_id=c.first_receipt"
    ):
        tick()
        _require(row["timeframe"] in PERIODS)
        period = PERIODS[row["timeframe"]]
        raw = _json(row["payload"], 8192)
        bar = ArchivedBar.model_validate(raw)
        _require(
            raw.get("closed") is True
            and _digest(row["payload"]) == row["digest"]
            and bar.time_server_s == row["time_server_s"]
            and bar.first_receipt == row["first_receipt"]
            and bar.time_server_s % period == bar.confirmed_by_server_s % period == 0
            and bar.broker_utc_offset_seconds == binding.offset_seconds
            and binding.chart.offset_valid_from_server_s
            <= bar.time_server_s
            < bar.confirmed_by_server_s
            < binding.chart.offset_valid_until_server_s
            and bar.open_time_utc
            == EPOCH + timedelta(seconds=bar.time_server_s - binding.offset_seconds)
            and bar.source_observed_at
            >= EPOCH + timedelta(seconds=bar.confirmed_by_server_s - binding.offset_seconds)
            and bar.source_observed_at <= bar.first_received_at == utc(row["received_at"])
            and bar.terminal_build <= 2**53 - 1
        )
        for key in ("open_time_utc", "source_observed_at", "first_received_at"):
            utc(raw[key])
        for key in ("open", "high", "low", "close", "tick_size"):
            _require(
                isinstance(raw[key], str) and len(raw[key]) <= 40 and PRICE_TEXT.fullmatch(raw[key])
            )
            if key != "tick_size":
                numerator, denominator = getattr(bar, key).as_integer_ratio()
                tick_numerator, tick_denominator = bar.tick_size.as_integer_ratio()
                _require(
                    numerator * tick_denominator % (denominator * tick_numerator) == 0
                    and numerator * 10**bar.digits % denominator == 0
                )
        counts[row["timeframe"]] += 1
    frames = 0
    for row in db.execute(
        "SELECT l.*,r.boot_id,r.sequence,r.fingerprint,r.received_at "
        "FROM latest_frames l JOIN receipts r USING(receipt_id)"
    ):
        tick()
        frame = ChartFrame.model_validate(_json(row["payload"], 131072))
        _require(
            frame.timeframe == row["timeframe"]
            and frame.identity == binding.identity
            and frame.broker_utc_offset_seconds == binding.offset_seconds
            and str(frame.boot_id) == row["boot_id"]
            and frame.sequence == row["sequence"]
            and _digest(row["payload"]) == row["fingerprint"]
            and frame.observed_at <= utc(row["received_at"])
            and frame.terminal_build <= 2**53 - 1
        )
        for index, bar in enumerate(frame.bars):
            _require(
                binding.chart.offset_valid_from_server_s
                <= bar.time_server_s
                < binding.chart.offset_valid_until_server_s
            )
            _require(
                EPOCH + timedelta(seconds=bar.time_server_s - binding.offset_seconds)
                <= frame.observed_at
            )
            if index < len(frame.bars) - 1:
                saved = db.execute(
                    "SELECT payload FROM closed_bars WHERE timeframe=? AND time_server_s=?",
                    (frame.timeframe, bar.time_server_s),
                ).fetchone()
                _require(saved is not None)
                closed = ArchivedBar.model_validate_json(saved[0])
                _require(
                    all(getattr(closed, name) == value for name, value in bar.model_dump().items())
                    and closed.first_receipt <= row["receipt_id"]
                    and closed.digits == frame.digits
                    and closed.tick_size == frame.tick_size
                    and closed.price_basis == frame.price_basis
                )
        frames += 1
    _require((count == 0 and frames == 0) or (count > 0 and frames > 0))
    return dict(receipts=count, bars=counts, frames=frames)


def _sync(db, archive, binding, latest, tick):
    meta = db.execute("SELECT * FROM meta").fetchall()
    _require(len(meta) == 1 and meta[0]["id"] == 1 and meta[0]["binding"] == binding.sync_binding)
    meta = meta[0]
    _require(utc(meta["last_clock"]) <= latest)
    cursor, previous, count, outstanding = SourceCursor(), None, 0, None
    attempts = 0
    for row in db.execute("SELECT * FROM batches ORDER BY seq"):
        tick()
        count += 1
        _require(
            row["seq"] == count
            and outstanding is None
            and str(UUID(row["batch_id"])) == row["batch_id"]
            and row["state"] in STATES
            and type(row["attempts"]) is int
            and 0 <= row["attempts"] <= 5
            and _digest(row["payload"]) == row["digest"]
            and utc(row["created_at"]) <= utc(row["updated_at"]) <= utc(meta["last_clock"])
            and (previous is None or utc(row["created_at"]) >= previous)
        )
        if row["state"] in {"UNKNOWN", "VERIFIED"}:
            _require(row["attempts"] > 0)
        batch = decode_batch(row["payload"])
        _require(
            batch.archive_id == str(binding.archive_id)
            and batch.binding_json == binding.archive_binding
            and batch.after == cursor
        )
        expected = archive.execute(
            "SELECT first_receipt,time_server_s,payload FROM closed_bars WHERE timeframe='M1' "
            "AND (first_receipt,time_server_s)>(?,?) ORDER BY first_receipt,time_server_s LIMIT ?",
            (cursor.receipt, cursor.time_server_s, len(batch.rows)),
        ).fetchall()
        _require(len(expected) == len(batch.rows))
        for item, stored in zip(batch.rows, expected, strict=True):
            tick()
            _require(
                item.cursor == SourceCursor(stored[0], stored[1])
                and item.payload == stored[2]
                and utc(item.available_at) <= utc(row["created_at"])
            )
        if row["state"] == "VERIFIED":
            cursor = batch.next_cursor
        else:
            outstanding = dict(
                state=row["state"],
                attempts=row["attempts"],
                send_budget_exhausted=row["attempts"] >= 5,
            )
        attempts += row["attempts"]
        previous = utc(row["updated_at"])
    _require(cursor == SourceCursor(meta["receipt"], meta["time_server_s"]))
    _sequence(db, "batches", "seq")
    return dict(
        batches=count,
        attempts=attempts,
        pending=outstanding,
        cursor_receipt=cursor.receipt,
        cursor_time_server_s=cursor.time_server_s,
    )


def audit_recovery_set(
    commands: Path,
    sync: Path,
    archive: Path,
    binding: RecoveryBinding,
    *,
    now: datetime,
    max_age_seconds: int,
    max_span_seconds: int,
) -> dict:
    """Inspect snapshots only. All local admission succeeds with execution_ready=False."""
    try:
        start = time.monotonic()

        def tick():
            _require(time.monotonic() - start <= AUDIT_SECONDS)

        _require(
            isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() is not None
        )
        _require(
            type(max_age_seconds) is int
            and type(max_span_seconds) is int
            and 1 <= max_span_seconds <= max_age_seconds <= 86400
        )
        binding = RecoveryBinding.model_validate(binding.model_dump())
        now = now.astimezone(UTC)
        paths = dict(commands=commands, sync=sync, archive=archive)
        _require(len(set(paths.values())) == 3)
        manifests, previous = {}, None
        for role, path in paths.items():
            manifests[role] = manifest = verify_snapshot(path)
            tick()
            beginning, end = utc(manifest["started_at"]), utc(manifest["completed_at"])
            _require(now - timedelta(seconds=max_age_seconds) <= beginning <= end <= now)
            _require(previous is None or previous <= beginning)
            _require(manifest["schema_sha256"] == SCHEMAS[role][1])
            previous = end
        _require(
            (
                utc(manifests["archive"]["completed_at"]) - utc(manifests["commands"]["started_at"])
            ).total_seconds()
            <= max_span_seconds
        )
        with ExitStack() as stack, localcontext() as arithmetic:
            arithmetic.prec = 512  # Exact sums for bounded decimals and <=100,000 rows.
            databases = {}
            for role, path in paths.items():
                db = stack.enter_context(
                    closing(
                        sqlite3.connect(
                            (path / "snapshot.sqlite3").as_uri() + "?mode=ro",
                            uri=True,
                            timeout=0.1,
                            isolation_level=None,
                        )
                    )
                )
                db.row_factory = sqlite3.Row
                db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2_097_152)
                db.execute("PRAGMA trusted_schema=OFF")
                db.execute("PRAGMA query_only=ON")
                db.set_progress_handler(lambda: int(time.monotonic() - start > AUDIT_SECONDS), 1000)
                db.execute("BEGIN")
                _require(db.execute("PRAGMA user_version").fetchone()[0] == SCHEMAS[role][0])
                tables = db.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall()
                for table in tables:
                    # Names have already passed an exact schema fingerprint check.
                    _require(
                        db.execute(f'SELECT count(*) FROM "{table[0]}"').fetchone()[0] <= MAX_ROWS
                    )
                databases[role] = db
            _require(
                manifests["archive"]["database_bytes"] <= MAX_DATABASE_BYTES
                and manifests["sync"]["database_bytes"] <= MAX_JOURNAL_BYTES
            )
            command_state = _commands(
                databases["commands"], binding, utc(manifests["commands"]["completed_at"]), tick
            )
            archive_state = _archive(
                databases["archive"], binding, utc(manifests["archive"]["completed_at"]), tick
            )
            sync_state = _sync(
                databases["sync"],
                databases["archive"],
                binding,
                utc(manifests["sync"]["completed_at"]),
                tick,
            )
        for role, path in paths.items():
            _require(verify_snapshot(path) == manifests[role])
            tick()
        return dict(
            format="sochron.recovery-audit.v1",
            execution_ready=False,
            consistency="causal-prefix-not-atomic",
            commands=command_state,
            archive=archive_state,
            sync=sync_state,
            binding_sha256=_digest(canonical(binding.model_dump(mode="json"))),
            snapshots={role: item["database_sha256"] for role, item in manifests.items()},
            audited_at=now.isoformat(),
            duration_seconds=time.monotonic() - start,
            broker_reconciliation="NOT_RUN",
            destination_reconciliation="NOT_RUN",
        )
    except Exception:
        raise RecoveryUnavailable() from None
