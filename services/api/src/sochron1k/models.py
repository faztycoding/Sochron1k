from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TradeMode(StrEnum):
    DEMO = "demo"
    CONTEST = "contest"
    REAL = "real"
    UNKNOWN = "unknown"


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class ManagementOperation(StrEnum):
    CANCEL = "cancel"
    CLOSE = "close"


class CommandState(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    QUEUED = "queued"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    PROTECTION_FAILED = "protection_failed"
    CLOSING = "closing"
    CLOSED = "closed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AccountSnapshot(StrictModel):
    account_ref: str = Field(min_length=1, max_length=128)
    server: str = Field(min_length=1, max_length=128)
    currency: str = Field(min_length=3, max_length=8)
    margin_mode: str = Field(min_length=1, max_length=64)
    trade_mode: TradeMode
    can_trade: bool
    equity: Decimal = Field(gt=0)
    checked_at: datetime


class ContractSpec(StrictModel):
    symbol: str = Field(min_length=1, max_length=32)
    digits: int = Field(ge=0, le=10)
    tick_size: Decimal = Field(gt=0)
    volume_min: Decimal = Field(gt=0)
    volume_max: Decimal = Field(gt=0)
    volume_step: Decimal = Field(gt=0)
    stops_level_points: int = Field(ge=0)
    freeze_level_points: int = Field(ge=0)
    filling_modes: tuple[str, ...] = Field(min_length=1)

    @field_validator("volume_max")
    @classmethod
    def maximum_not_below_minimum(cls, value: Decimal, info):
        minimum = info.data.get("volume_min")
        if minimum is not None and value < minimum:
            raise ValueError("volume_max must be greater than or equal to volume_min")
        return value


class MarketSnapshot(StrictModel):
    symbol: str = Field(min_length=1, max_length=32)
    bid: Decimal = Field(gt=0)
    ask: Decimal = Field(gt=0)
    event_time: datetime
    received_time: datetime
    market_open: bool

    @field_validator("ask")
    @classmethod
    def ask_not_below_bid(cls, value: Decimal, info):
        bid = info.data.get("bid")
        if bid is not None and value < bid:
            raise ValueError("ask must be greater than or equal to bid")
        return value


class CommandIntent(StrictModel):
    command_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    account_ref: str = Field(min_length=1, max_length=128)
    experiment_id: str = Field(min_length=1, max_length=128)
    signal_id: str = Field(min_length=1, max_length=128)
    strategy_version: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    side: Side
    requested_entry: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    take_profit: Decimal = Field(gt=0)
    expires_at: datetime
    operation: str = Field(default="open", pattern="^(open|close|cancel)$")

    @field_validator("expires_at")
    @classmethod
    def expiry_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        return value

    def canonical_fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"command_id"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def idempotency_scope(self) -> str:
        return f"{self.account_ref}:{self.experiment_id}:{self.operation}"


class ManagementIntent(StrictModel):
    command_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    account_ref: str = Field(min_length=1, max_length=128)
    experiment_id: str = Field(min_length=1, max_length=128)
    target_command_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    operation: ManagementOperation
    reason: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def management_expiry_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def cannot_target_itself(self):
        if self.command_id == self.target_command_id:
            raise ValueError("management command cannot target itself")
        return self

    def canonical_fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"command_id"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def idempotency_scope(self) -> str:
        return (
            f"{self.account_ref}:{self.experiment_id}:"
            f"{self.target_command_id}:{self.operation.value}"
        )


class RiskContext(StrictModel):
    equity: Decimal = Field(gt=0)
    daily_baseline: Decimal = Field(gt=0)
    experiment_baseline: Decimal = Field(gt=0)
    reserved_loss: Decimal = Field(default=Decimal("0"), ge=0)
    loss_per_lot: Decimal = Field(gt=0)
    costs_per_lot: Decimal = Field(default=Decimal("0"), ge=0)
    free_margin: Decimal = Field(gt=0)
    margin_per_lot: Decimal = Field(gt=0)


class RiskDecision(StrictModel):
    allowed: bool
    reason: str | None = None
    volume: Decimal = Decimal("0")
    available_risk: Decimal = Decimal("0")
    estimated_loss: Decimal = Decimal("0")
    estimated_margin: Decimal = Decimal("0")


class RiskState(StrictModel):
    account_ref: str
    experiment_id: str
    bangkok_day: date
    daily_baseline: Decimal = Field(gt=0)
    experiment_baseline: Decimal = Field(gt=0)
    daily_halt: bool = False
    total_halt: bool = False
    updated_at: datetime


class BrokerDeal(StrictModel):
    deal_ticket: str = Field(min_length=1, max_length=128)
    volume: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    profit: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def deal_time_is_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("occurred_at must be timezone-aware")
        return value


class BrokerSnapshot(StrictModel):
    command_id: str = Field(min_length=1, max_length=128)
    order_ticket: str | None = Field(default=None, max_length=128)
    position_id: str | None = Field(default=None, max_length=128)
    requested_volume: Decimal = Field(gt=0)
    filled_volume: Decimal = Field(ge=0)
    remaining_volume: Decimal = Field(ge=0)
    cancelled_volume: Decimal = Field(default=Decimal("0"), ge=0)
    closed_volume: Decimal = Field(default=Decimal("0"), ge=0)
    deals: tuple[BrokerDeal, ...] = ()
    stop_loss_confirmed: bool
    terminal_state: CommandState | None = None

    @property
    def open_position_volume(self) -> Decimal:
        return self.filled_volume - self.closed_volume


class ManagementSnapshot(StrictModel):
    command_id: str = Field(min_length=1, max_length=128)
    target_command_id: str = Field(min_length=1, max_length=128)
    operation: ManagementOperation
    broker_order_ticket: str = Field(min_length=1, max_length=128)
    position_id: str | None = Field(default=None, max_length=128)
    requested_volume: Decimal = Field(gt=0)
    completed_volume: Decimal = Field(ge=0)
    remaining_volume: Decimal = Field(ge=0)
    deals: tuple[BrokerDeal, ...] = ()
    terminal_state: CommandState | None = None
    target: BrokerSnapshot
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def management_observation_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class TradeAudit(StrictModel):
    command_id: str
    account_ref: str
    experiment_id: str
    symbol: str
    entry_order_ticket: str
    position_id: str
    requested_volume: Decimal
    entry_volume: Decimal
    cancelled_volume: Decimal
    closed_volume: Decimal
    entry_deal_tickets: tuple[str, ...]
    exit_order_tickets: tuple[str, ...]
    exit_deal_tickets: tuple[str, ...]
    gross_profit: Decimal
    commission: Decimal
    swap: Decimal
    fee: Decimal
    net_pnl: Decimal
    close_reason: str


class SubmissionResult(StrictModel):
    command_id: str
    state: CommandState
    volume: Decimal
    duplicate: bool = False
    protected: bool = False
    reason: str | None = None
