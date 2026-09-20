"""Authenticated single-executor polling transport for Demo execution only."""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    Field,
    SecretStr,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from .executor import ExecutorInventory, ExecutorRejected
from .models import (
    BrokerSnapshot,
    CommandIntent,
    ExecutorRejection,
    ManagementIntent,
    ManagementOperation,
    ManagementSnapshot,
    Side,
    StrictModel,
    TradeMode,
)
from .telemetry import DemoIdentity

MAX_EXECUTION_FRAME_BYTES = 262_144
MAX_EXECUTION_AGE_SECONDS = 5.0
MAX_EXECUTION_INVENTORY_ITEMS = 32


class ExecutionBridgeSettings(StrictModel):
    identity: DemoIdentity
    token: SecretStr
    magic_number: StrictInt = Field(gt=0, le=2_147_483_647)
    response_timeout_seconds: Decimal = Field(
        default=Decimal("2"), gt=0, le=5, allow_inf_nan=False, max_digits=4, decimal_places=3
    )

    @field_validator("token")
    @classmethod
    def token_is_scoped_random_format(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not 43 <= len(raw) <= 128 or not all(
            char.isascii() and (char.isalnum() or char in "-_") for char in raw
        ):
            raise ValueError("use a separately generated URL-safe executor credential")
        return value


def load_execution_bridge_settings() -> ExecutionBridgeSettings | None:
    configured_path = os.environ.get("SOCHRON_EXECUTION_BRIDGE_CONFIG_FILE")
    if not configured_path:
        return None
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(Path(configured_path), flags), "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
            ):
                raise ValueError("private configuration required")
            raw = stream.read(MAX_EXECUTION_FRAME_BYTES + 1)
        if len(raw) > MAX_EXECUTION_FRAME_BYTES:
            raise ValueError("configuration too large")
        return ExecutionBridgeSettings.model_validate_json(raw)
    except OSError, ValueError:
        raise RuntimeError(
            "Invalid private execution bridge configuration; executor transport not started"
        ) from None


class ExecutionInventoryFrame(StrictModel):
    protocol: Literal["sochron.execution.inventory.v1"]
    boot_id: UUID
    sequence: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    identity: DemoIdentity
    trade_mode: Literal["demo"]
    terminal_build: StrictInt = Field(gt=0)
    terminal_connected: StrictBool
    account_trade_allowed: StrictBool
    algo_trading_allowed: StrictBool
    magic_number: StrictInt = Field(gt=0, le=2_147_483_647)
    observed_at: AwareDatetime
    inventory: ExecutorInventory

    @field_validator("observed_at")
    @classmethod
    def normalize_observation(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def inventory_matches_envelope(self):
        account = self.inventory.account
        entry_ids = [item.command_id for item in self.inventory.snapshots]
        management_ids = [item.command_id for item in self.inventory.management_snapshots]
        rejection_ids = [item.command_id for item in self.inventory.rejections]
        if (
            self.inventory.executor_id != self.identity.executor_id
            or self.inventory.symbol != self.identity.symbol
            or account.account_ref != self.identity.account_ref
            or account.server != self.identity.server
            or account.currency != self.identity.currency
            or account.margin_mode != self.identity.margin_mode
            or account.trade_mode is not TradeMode.DEMO
            or account.can_trade != self.account_trade_allowed
            or self.inventory.observed_at != self.observed_at
            or account.checked_at != self.observed_at
            or len(self.inventory.snapshots) > MAX_EXECUTION_INVENTORY_ITEMS
            or len(self.inventory.management_snapshots) > MAX_EXECUTION_INVENTORY_ITEMS
            or len(self.inventory.rejections) > MAX_EXECUTION_INVENTORY_ITEMS
            or len(set(entry_ids)) != len(entry_ids)
            or len(set(management_ids)) != len(management_ids)
            or len(set(rejection_ids)) != len(rejection_ids)
            or set(entry_ids) & set(management_ids)
            or set(rejection_ids) & (set(entry_ids) | set(management_ids))
        ):
            raise ValueError("inventory envelope mismatch")
        return self


class ExecutionDispatch(StrictModel):
    protocol: Literal["sochron.execution.command.v1"] = "sochron.execution.command.v1"
    boot_id: UUID
    dispatch_sequence: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    attempt_id: str = Field(min_length=1, max_length=128)
    generation: str = Field(min_length=1, max_length=128)
    magic_number: StrictInt = Field(gt=0, le=2_147_483_647)
    command_id: str = Field(min_length=1, max_length=128)
    target_command_id: str | None = Field(default=None, min_length=1, max_length=128)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    account_ref: str = Field(min_length=1, max_length=128)
    experiment_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    operation: Literal["open", "cancel", "close"]
    volume: Decimal = Field(gt=0, allow_inf_nan=False, max_digits=24, decimal_places=10)
    expires_at: AwareDatetime
    side: Side | None = None
    requested_entry: Decimal | None = Field(
        default=None, gt=0, allow_inf_nan=False, max_digits=24, decimal_places=10
    )
    stop_loss: Decimal | None = Field(
        default=None, gt=0, allow_inf_nan=False, max_digits=24, decimal_places=10
    )
    take_profit: Decimal | None = Field(
        default=None, gt=0, allow_inf_nan=False, max_digits=24, decimal_places=10
    )
    broker_order_ticket: str | None = Field(default=None, min_length=1, max_length=128)
    position_id: str | None = Field(default=None, min_length=1, max_length=128)
    reason: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def fields_match_operation(self):
        entry_fields = (self.side, self.requested_entry, self.stop_loss, self.take_profit)
        if self.operation == "open":
            valid = (
                self.target_command_id is None
                and all(value is not None for value in entry_fields)
                and self.broker_order_ticket is None
                and self.position_id is None
                and self.reason is None
            )
        else:
            valid = (
                self.target_command_id is not None
                and all(value is None for value in entry_fields)
                and self.broker_order_ticket is not None
                and self.reason is not None
                and (self.operation != "close" or self.position_id is not None)
            )
        if not valid or self.target_command_id == self.command_id:
            raise ValueError("operation fields are inconsistent")
        return self


class UncertainEvidence(StrictModel):
    retcode: StrictInt | None = Field(default=None, ge=0, le=4_294_967_295)
    retcode_external: StrictInt = Field(default=0, ge=-2_147_483_648, le=2_147_483_647)
    request_id: StrictInt | None = Field(default=None, ge=0, le=4_294_967_295)


class ExecutionOutcomeFrame(StrictModel):
    protocol: Literal["sochron.execution.outcome.v1"]
    boot_id: UUID
    dispatch_sequence: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    attempt_id: str = Field(min_length=1, max_length=128)
    generation: str = Field(min_length=1, max_length=128)
    command_id: str = Field(min_length=1, max_length=128)
    target_command_id: str | None = Field(default=None, min_length=1, max_length=128)
    operation: Literal["open", "cancel", "close"]
    observed_at: AwareDatetime
    status: Literal["snapshot", "rejected", "uncertain"]
    snapshot: BrokerSnapshot | None = None
    management_snapshot: ManagementSnapshot | None = None
    rejection: ExecutorRejection | None = None
    uncertain: UncertainEvidence | None = None

    @field_validator("observed_at")
    @classmethod
    def normalize_outcome_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def evidence_matches_status_and_binding(self):
        supplied = sum(
            value is not None
            for value in (self.snapshot, self.management_snapshot, self.rejection, self.uncertain)
        )
        if supplied != 1:
            raise ValueError("exactly one outcome evidence object is required")
        if self.status == "snapshot":
            if self.operation == "open":
                valid = (
                    self.snapshot is not None
                    and self.management_snapshot is None
                    and self.snapshot.command_id == self.command_id
                    and self.target_command_id is None
                )
            else:
                item = self.management_snapshot
                valid = (
                    item is not None
                    and self.snapshot is None
                    and item.command_id == self.command_id
                    and item.target_command_id == self.target_command_id
                    and item.operation.value == self.operation
                    and 0 <= (self.observed_at - item.observed_at).total_seconds() <= 5
                )
        elif self.status == "rejected":
            valid = (
                self.rejection is not None
                and self.rejection.command_id == self.command_id
                and self.rejection.target_command_id == self.target_command_id
                and self.rejection.operation == self.operation
                and 0
                <= (self.observed_at - self.rejection.observed_at).total_seconds()
                <= 5
            )
        else:
            valid = self.uncertain is not None
        if not valid:
            raise ValueError("outcome evidence binding mismatch")
        return self


class ExecutionBridgeReceipt(StrictModel):
    accepted: Literal[True] = True
    duplicate: bool
    sequence: int


class ExecutionBridgeChallenge(StrictModel):
    boot_id: UUID
    next_inventory_sequence: int


class ExecutionBridgeStatus(StrictModel):
    state: Literal["disabled", "awaiting_inventory", "connected", "stale", "rejected"]
    inventory_fresh: bool = False
    active_command: bool = False
    claimed_command: bool = False
    inventory_age_seconds: float | None = None
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False


class ExecutionPolicySnapshot(StrictModel):
    """One already-fenced inventory plus current local dispatch occupancy."""

    frame: ExecutionInventoryFrame
    active_command: StrictBool


class ExecutionBridgeDenied(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class _PendingDispatch:
    command: ExecutionDispatch
    claimed: bool = False
    outcome: ExecutionOutcomeFrame | None = None
    failure: Exception | None = None


class ExecutionPollingBridge:
    def __init__(
        self,
        settings: ExecutionBridgeSettings | None,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.boot_id = uuid4()
        self._utc_now = utc_now
        self._monotonic = monotonic
        self._condition = threading.Condition(threading.RLock())
        self._inventory_frame: ExecutionInventoryFrame | None = None
        self._inventory_fingerprint: str | None = None
        self._inventory_received_monotonic = 0.0
        self._rejected = False
        self._dispatch_sequence = 0
        self._active: _PendingDispatch | None = None
        self._outcome_fingerprints: dict[int, str] = {}
        self._entry_evidence: dict[str, BrokerSnapshot | ExecutorRejection] = {}
        self._management_evidence: dict[str, ManagementSnapshot | ExecutorRejection] = {}

    def authenticate(self, credentials: list[str]) -> bool:
        if self.settings is None or len(credentials) != 1:
            return False
        supplied = credentials[0]
        if not supplied.isascii() or len(supplied) > 256:
            return False
        expected = "Bearer " + self.settings.token.get_secret_value()
        return secrets.compare_digest(supplied, expected)

    def reject(self) -> None:
        with self._condition:
            self._rejected = True
            if self._active is not None:
                self._active.failure = RuntimeError("EXECUTION_BRIDGE_REJECTED")
                self._active = None
                self._condition.notify_all()

    @staticmethod
    def _fingerprint(model: StrictModel) -> str:
        return hashlib.sha256(model.model_dump_json().encode()).hexdigest()

    def challenge(self) -> ExecutionBridgeChallenge:
        with self._condition:
            sequence = self._inventory_frame.sequence + 1 if self._inventory_frame else 1
            return ExecutionBridgeChallenge(boot_id=self.boot_id, next_inventory_sequence=sequence)

    def accept_inventory(self, frame: ExecutionInventoryFrame) -> ExecutionBridgeReceipt:
        frame = ExecutionInventoryFrame.model_validate(frame.model_dump())
        fingerprint = self._fingerprint(frame)
        with self._condition:
            try:
                return self._accept_inventory_locked(frame, fingerprint)
            except ExecutionBridgeDenied:
                self._rejected = True
                raise

    def _accept_inventory_locked(self, frame, fingerprint):
        settings = self.settings
        if settings is None:
            raise ExecutionBridgeDenied("EXECUTION_BRIDGE_DISABLED")
        if frame.boot_id != self.boot_id:
            raise ExecutionBridgeDenied("BOOT_MISMATCH")
        if frame.identity != settings.identity or frame.magic_number != settings.magic_number:
            raise ExecutionBridgeDenied("IDENTITY_MISMATCH")
        previous = self._inventory_frame
        if previous is not None:
            if frame.sequence == previous.sequence:
                if fingerprint != self._inventory_fingerprint:
                    raise ExecutionBridgeDenied("SEQUENCE_CONFLICT")
                return ExecutionBridgeReceipt(duplicate=True, sequence=frame.sequence)
            if frame.sequence < previous.sequence:
                raise ExecutionBridgeDenied("OUT_OF_ORDER")
            if frame.observed_at < previous.observed_at:
                raise ExecutionBridgeDenied("TIME_REVERSAL")
            if (
                frame.inventory.generation != previous.inventory.generation
                and self._active is not None
            ):
                raise ExecutionBridgeDenied("GENERATION_CHANGED_WITH_ACTIVE_COMMAND")
        now = self._utc_now().astimezone(UTC)
        age = (now - frame.observed_at).total_seconds()
        if age < 0 or age > MAX_EXECUTION_AGE_SECONDS:
            raise ExecutionBridgeDenied("OBSERVATION_CLOCK_INVALID")
        self._inventory_frame = frame
        self._inventory_fingerprint = fingerprint
        self._inventory_received_monotonic = self._monotonic()
        entry_evidence: dict[str, BrokerSnapshot | ExecutorRejection] = {}
        management_evidence: dict[str, ManagementSnapshot | ExecutorRejection] = {}
        for snapshot in frame.inventory.snapshots:
            entry_evidence[snapshot.command_id] = snapshot
        for snapshot in frame.inventory.management_snapshots:
            management_evidence[snapshot.command_id] = snapshot
        for rejection in frame.inventory.rejections:
            target = entry_evidence if rejection.operation == "open" else management_evidence
            target[rejection.command_id] = rejection
        self._entry_evidence = entry_evidence
        self._management_evidence = management_evidence
        self._rejected = False
        return ExecutionBridgeReceipt(duplicate=False, sequence=frame.sequence)

    def _inventory_age_locked(self) -> float | None:
        frame = self._inventory_frame
        if frame is None:
            return None
        now = self._utc_now().astimezone(UTC)
        elapsed = max(0.0, self._monotonic() - self._inventory_received_monotonic)
        return max((now - frame.observed_at).total_seconds(), elapsed, 0.0)

    def _inventory_usable_locked(self) -> bool:
        frame = self._inventory_frame
        age = self._inventory_age_locked()
        return bool(
            frame is not None
            and not self._rejected
            and age is not None
            and age <= MAX_EXECUTION_AGE_SECONDS
            and frame.terminal_connected
            and frame.account_trade_allowed
            and frame.algo_trading_allowed
            and frame.inventory.complete
            and not frame.inventory.foreign_orders
            and not frame.inventory.foreign_positions
        )

    def _inventory_policy_usable_locked(self) -> bool:
        frame = self._inventory_frame
        age = self._inventory_age_locked()
        return bool(
            frame is not None
            and not self._rejected
            and age is not None
            and age <= MAX_EXECUTION_AGE_SECONDS
            and frame.terminal_connected
            and frame.account_trade_allowed
            and frame.inventory.complete
            and not frame.inventory.foreign_orders
            and not frame.inventory.foreign_positions
        )

    def status(self) -> ExecutionBridgeStatus:
        with self._condition:
            if self.settings is None:
                return ExecutionBridgeStatus(state="disabled")
            active = self._active
            age = self._inventory_age_locked()
            if self._rejected:
                state = "rejected"
            elif self._inventory_frame is None:
                state = "awaiting_inventory"
            elif self._inventory_usable_locked():
                state = "connected"
            else:
                state = "stale"
            return ExecutionBridgeStatus(
                state=state,
                inventory_fresh=self._inventory_usable_locked(),
                active_command=active is not None,
                claimed_command=bool(active and active.claimed),
                inventory_age_seconds=round(age, 3) if age is not None else None,
            )

    def inventory(self) -> ExecutorInventory:
        with self._condition:
            if not self._inventory_usable_locked():
                raise ConnectionError("fresh complete executor inventory is unavailable")
            return self._inventory_frame.inventory

    def policy_snapshot(self) -> ExecutionPolicySnapshot:
        with self._condition:
            if not self._inventory_policy_usable_locked():
                raise ConnectionError("fresh complete policy inventory is unavailable")
            return ExecutionPolicySnapshot(
                frame=self._inventory_frame,
                active_command=self._active is not None,
            )

    def _new_dispatch_locked(self, **values) -> _PendingDispatch:
        if not self._inventory_usable_locked():
            raise ConnectionError("fresh complete executor inventory is unavailable")
        if self._active is not None:
            raise RuntimeError("EXECUTOR_COMMAND_ALREADY_ACTIVE")
        if (
            values.get("account_ref") != self.settings.identity.account_ref
            or values.get("symbol") != self.settings.identity.symbol
        ):
            raise RuntimeError("EXECUTOR_DISPATCH_IDENTITY_MISMATCH")
        self._dispatch_sequence += 1
        frame = self._inventory_frame
        command = ExecutionDispatch(
            boot_id=self.boot_id,
            dispatch_sequence=self._dispatch_sequence,
            generation=frame.inventory.generation,
            magic_number=self.settings.magic_number,
            **values,
        )
        pending = _PendingDispatch(command)
        self._active = pending
        return pending

    def _wait_for_outcome(self, pending: _PendingDispatch):
        timeout = float(self.settings.response_timeout_seconds)
        deadline = self._monotonic() + timeout
        with self._condition:
            while pending.outcome is None and pending.failure is None:
                remaining = deadline - self._monotonic()
                if remaining <= 0:
                    if self._active is pending and not pending.claimed:
                        self._active = None
                    raise TimeoutError("EXECUTOR_RESPONSE_TIMEOUT")
                self._condition.wait(remaining)
            if pending.failure is not None:
                raise pending.failure
            outcome = pending.outcome
        if outcome.status == "rejected":
            raise ExecutorRejected(outcome.rejection)
        if outcome.status == "uncertain":
            raise TimeoutError("EXECUTOR_OUTCOME_UNCERTAIN")
        return outcome.snapshot or outcome.management_snapshot

    def send(self, intent: CommandIntent, volume: Decimal, attempt_id: str) -> BrokerSnapshot:
        intent = CommandIntent.model_validate(intent.model_dump())
        if intent.operation != "open":
            raise RuntimeError("EXECUTOR_OPERATION_MISMATCH")
        with self._condition:
            pending = self._new_dispatch_locked(
                attempt_id=attempt_id,
                command_id=intent.command_id,
                fingerprint=intent.canonical_fingerprint(),
                account_ref=intent.account_ref,
                experiment_id=intent.experiment_id,
                symbol=intent.symbol,
                operation="open",
                volume=volume,
                expires_at=intent.expires_at,
                side=intent.side,
                requested_entry=intent.requested_entry,
                stop_loss=intent.stop_loss,
                take_profit=intent.take_profit,
            )
        result = self._wait_for_outcome(pending)
        if not isinstance(result, BrokerSnapshot):
            raise RuntimeError("EXECUTOR_OUTCOME_TYPE_MISMATCH")
        return result

    def manage(
        self,
        intent: ManagementIntent,
        target: BrokerSnapshot,
        attempt_id: str,
    ) -> ManagementSnapshot:
        intent = ManagementIntent.model_validate(intent.model_dump())
        target = BrokerSnapshot.model_validate(target.model_dump())
        if target.command_id != intent.target_command_id:
            raise RuntimeError("EXECUTOR_TARGET_MISMATCH")
        volume = (
            target.remaining_volume
            if intent.operation is ManagementOperation.CANCEL
            else target.open_position_volume
        )
        with self._condition:
            pending = self._new_dispatch_locked(
                attempt_id=attempt_id,
                command_id=intent.command_id,
                target_command_id=intent.target_command_id,
                fingerprint=intent.canonical_fingerprint(),
                account_ref=intent.account_ref,
                experiment_id=intent.experiment_id,
                symbol=intent.symbol,
                operation=intent.operation.value,
                volume=volume,
                expires_at=intent.expires_at,
                broker_order_ticket=target.order_ticket,
                position_id=target.position_id,
                reason=intent.reason,
            )
        result = self._wait_for_outcome(pending)
        if not isinstance(result, ManagementSnapshot):
            raise RuntimeError("EXECUTOR_OUTCOME_TYPE_MISMATCH")
        return result

    def next_command(self) -> ExecutionDispatch | None:
        with self._condition:
            pending = self._active
            if pending is None:
                return None
            if not pending.claimed and not self._inventory_usable_locked():
                pending.failure = ConnectionError("EXECUTOR_INVENTORY_UNAVAILABLE_BEFORE_CLAIM")
                self._active = None
                self._condition.notify_all()
                return None
            if not pending.claimed and self._utc_now().astimezone(UTC) > pending.command.expires_at:
                pending.failure = TimeoutError("EXECUTOR_COMMAND_EXPIRED_BEFORE_CLAIM")
                self._active = None
                self._condition.notify_all()
                return None
            pending.claimed = True
            return pending.command

    def accept_outcome(self, frame: ExecutionOutcomeFrame) -> ExecutionBridgeReceipt:
        frame = ExecutionOutcomeFrame.model_validate(frame.model_dump())
        fingerprint = self._fingerprint(frame)
        with self._condition:
            previous = self._outcome_fingerprints.get(frame.dispatch_sequence)
            if previous is not None:
                if previous != fingerprint:
                    self._rejected = True
                    raise ExecutionBridgeDenied("OUTCOME_CONFLICT")
                return ExecutionBridgeReceipt(duplicate=True, sequence=frame.dispatch_sequence)
            pending = self._active
            command = pending.command if pending else None
            if frame.boot_id != self.boot_id:
                return self._deny_outcome_locked("BOOT_MISMATCH")
            if pending is None or command.dispatch_sequence != frame.dispatch_sequence:
                return self._deny_outcome_locked("DISPATCH_NOT_ACTIVE")
            if (
                not pending.claimed
                or frame.attempt_id != command.attempt_id
                or frame.generation != command.generation
                or frame.command_id != command.command_id
                or frame.target_command_id != command.target_command_id
                or frame.operation != command.operation
            ):
                return self._deny_outcome_locked("OUTCOME_BINDING_MISMATCH")
            age = (self._utc_now().astimezone(UTC) - frame.observed_at).total_seconds()
            if age < 0 or age > MAX_EXECUTION_AGE_SECONDS:
                return self._deny_outcome_locked("OUTCOME_CLOCK_INVALID")
            if frame.status == "snapshot":
                if frame.snapshot is not None:
                    self._entry_evidence[frame.command_id] = frame.snapshot
                else:
                    self._management_evidence[frame.command_id] = frame.management_snapshot
            elif frame.status == "rejected":
                target = (
                    self._entry_evidence if frame.operation == "open" else self._management_evidence
                )
                target[frame.command_id] = frame.rejection
            self._outcome_fingerprints[frame.dispatch_sequence] = fingerprint
            pending.outcome = frame
            self._active = None
            self._condition.notify_all()
            return ExecutionBridgeReceipt(duplicate=False, sequence=frame.dispatch_sequence)

    def _deny_outcome_locked(self, code):
        self._rejected = True
        if self._active is not None:
            self._active.failure = RuntimeError(code)
            self._active = None
            self._condition.notify_all()
        raise ExecutionBridgeDenied(code)

    def query(self, command_id: str) -> BrokerSnapshot | ExecutorRejection | None:
        with self._condition:
            return self._entry_evidence.get(command_id)

    def query_management(self, command_id: str) -> ManagementSnapshot | ExecutorRejection | None:
        with self._condition:
            return self._management_evidence.get(command_id)
