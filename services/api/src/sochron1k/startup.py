"""Admission from explicit executor inventory; never a send or halt-release path."""

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .executor import ExecutorInventory
from .models import CommandIntent, CommandState, ManagementIntent, TradeMode


class StartupDenied(RuntimeError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def require(condition, reason):
    if not condition:
        raise StartupDenied(reason)


def aware(value):
    return (
        isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
    )


def inspect_startup(journal, adapter, policy, experiment_id, executor_id, now, generation=None):
    started = time.monotonic()
    require(aware(now), "STARTUP_INVALID_TIME")
    identity = (journal.path.stat().st_dev, journal.path.stat().st_ino)
    state, active, exposure, management = journal.startup_state(policy.account_ref, experiment_id)
    require(state is not None, "RISK_BASELINE_MISSING")
    require(
        state.bangkok_day == now.astimezone(ZoneInfo("Asia/Bangkok")).date(),
        "RISK_DAY_REVIEW_REQUIRED",
    )
    require(aware(state.updated_at) and state.updated_at <= now, "RISK_STATE_INVALID_TIME")
    require(len(active) <= 1 and len(exposure) == len(active), "JOURNAL_EXPOSURE_MISMATCH")
    require(len(management) <= 1, "JOURNAL_MANAGEMENT_MISMATCH")
    for row in active:
        intent = CommandIntent.model_validate_json(row["payload_json"])
        require(
            row["account_ref"] == policy.account_ref
            and row["experiment_id"] == experiment_id
            and intent.account_ref == policy.account_ref
            and intent.experiment_id == experiment_id
            and intent.symbol == policy.symbol
            and intent.command_id == row["command_id"]
            and intent.idempotency_scope == row["scope"]
            and intent.idempotency_key == row["idempotency_key"]
            and intent.canonical_fingerprint() == row["fingerprint"],
            "JOURNAL_COMMAND_MISMATCH",
        )
        slot = exposure[0]
        require(
            slot["command_id"] == row["command_id"]
            and slot["account_ref"] == row["account_ref"]
            and slot["experiment_id"] == row["experiment_id"]
            and slot["reserved_loss"] == row["reserved_loss"],
            "JOURNAL_EXPOSURE_MISMATCH",
        )
    active_ids = {row["command_id"] for row in active}
    for row in management:
        intent = ManagementIntent.model_validate_json(row["payload_json"])
        require(
            row["account_ref"] == policy.account_ref
            and row["experiment_id"] == experiment_id
            and row["target_command_id"] in active_ids
            and intent.account_ref == policy.account_ref
            and intent.experiment_id == experiment_id
            and intent.symbol == policy.symbol
            and intent.command_id == row["command_id"]
            and intent.target_command_id == row["target_command_id"]
            and intent.idempotency_scope == row["scope"]
            and intent.idempotency_key == row["idempotency_key"]
            and intent.canonical_fingerprint() == row["fingerprint"],
            "JOURNAL_MANAGEMENT_MISMATCH",
        )
    inventory = ExecutorInventory.model_validate(adapter.inventory().model_dump())
    require(inventory.complete, "EXECUTOR_INVENTORY_INCOMPLETE")
    require(
        inventory.executor_id == executor_id and inventory.symbol == policy.symbol,
        "EXECUTOR_IDENTITY_MISMATCH",
    )
    require(generation is None or inventory.generation == generation, "EXECUTOR_GENERATION_CHANGED")
    account = inventory.account
    require(account.trade_mode is TradeMode.DEMO, "NON_DEMO_ACCOUNT")
    require(
        account.account_ref == policy.account_ref
        and account.server == policy.server
        and account.currency == policy.currency
        and account.margin_mode == policy.margin_mode,
        "EXECUTOR_IDENTITY_MISMATCH",
    )
    require(account.can_trade, "EXECUTOR_TRADING_DISABLED")
    for stamp in (inventory.observed_at, account.checked_at):
        require(
            aware(stamp) and 0 <= (now - stamp).total_seconds() <= 5, "EXECUTOR_INVENTORY_STALE"
        )
    require(not inventory.foreign_orders and not inventory.foreign_positions, "FOREIGN_EXPOSURE")
    snapshots = {item.command_id: item for item in inventory.snapshots}
    require(len(snapshots) == len(inventory.snapshots), "EXECUTOR_INVENTORY_CONFLICT")
    for command_id, snapshot in snapshots.items():
        try:
            row = journal.command(command_id)
        except KeyError:
            raise StartupDenied("FOREIGN_EXPOSURE") from None
        require(row["account_ref"] == policy.account_ref, "FOREIGN_EXPOSURE")
        if row["state"] in {"closed", "cancelled", "expired", "rejected"}:
            require(
                snapshot.terminal_state is CommandState(row["state"]),
                "EXECUTOR_INVENTORY_CONFLICT",
            )
        # A terminal label is not evidence: validate volumes, tickets and deals even
        # when this snapshot will not mutate the active-command journal.
        journal.validate_broker_snapshot(snapshot)
    management_snapshots = {item.command_id: item for item in inventory.management_snapshots}
    require(
        len(management_snapshots) == len(inventory.management_snapshots),
        "EXECUTOR_INVENTORY_CONFLICT",
    )
    require(not (set(snapshots) & set(management_snapshots)), "EXECUTOR_INVENTORY_CONFLICT")
    for command_id, snapshot in management_snapshots.items():
        try:
            row = journal.management_command(command_id)
        except KeyError:
            raise StartupDenied("FOREIGN_EXPOSURE") from None
        require(
            row["account_ref"] == policy.account_ref and row["experiment_id"] == experiment_id,
            "FOREIGN_EXPOSURE",
        )
        if row["state"] in {"closed", "cancelled", "expired", "rejected"}:
            require(
                snapshot.terminal_state is CommandState(row["state"]),
                "EXECUTOR_INVENTORY_CONFLICT",
            )
        require(
            0 <= (now - snapshot.observed_at).total_seconds() <= 5,
            "EXECUTOR_INVENTORY_STALE",
        )
        journal.validate_management_snapshot(snapshot)
    require(all(row["command_id"] in snapshots for row in active), "STARTUP_UNRESOLVED")
    require(
        all(row["command_id"] in management_snapshots for row in management),
        "STARTUP_UNRESOLVED",
    )
    for row in management:
        journal.apply_management_snapshot(management_snapshots[row["command_id"]])
    for row in active:
        snapshot = snapshots[row["command_id"]]
        journal.apply_broker_snapshot(snapshot)
        require(
            not snapshot.open_position_volume or snapshot.stop_loss_confirmed,
            "STARTUP_UNPROTECTED",
        )
    after, remaining, slots, remaining_management = journal.startup_state(
        policy.account_ref, experiment_id
    )
    terminal = {
        CommandState.REJECTED,
        CommandState.CANCELLED,
        CommandState.CLOSED,
        CommandState.EXPIRED,
    }
    expected = {
        row["command_id"]
        for row in active
        if snapshots[row["command_id"]].terminal_state not in terminal
    }
    for row in management:
        snapshot = management_snapshots[row["command_id"]]
        if snapshot.target.terminal_state in terminal:
            expected.discard(snapshot.target_command_id)
    expected_management = {
        row["command_id"]
        for row in management
        if management_snapshots[row["command_id"]].terminal_state not in terminal
    }
    require(
        after == state
        and {r["command_id"] for r in remaining} == expected
        and {r["command_id"] for r in slots} == expected
        and {r["command_id"] for r in remaining_management} == expected_management
        and identity == (journal.path.stat().st_dev, journal.path.stat().st_ino),
        "STARTUP_STATE_CHANGED",
    )
    elapsed = time.monotonic() - started
    require(0 <= elapsed <= 5, "STARTUP_TIMEOUT")
    completed = now + timedelta(seconds=elapsed)
    completion_stamps = (
        inventory.observed_at,
        account.checked_at,
        *(snapshot.observed_at for snapshot in management_snapshots.values()),
    )
    require(
        all(0 <= (completed - value).total_seconds() <= 5 for value in completion_stamps),
        "EXECUTOR_INVENTORY_STALE",
    )
    require(
        state.bangkok_day == completed.astimezone(ZoneInfo("Asia/Bangkok")).date(),
        "RISK_DAY_REVIEW_REQUIRED",
    )
    return inventory, state, bool(slots)
