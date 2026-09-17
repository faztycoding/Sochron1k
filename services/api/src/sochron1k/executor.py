"""Local adapter contract; no MT5 transport or permission is implied by these types."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pydantic import Field, StrictBool, StrictInt

from .models import AccountSnapshot, BrokerSnapshot, CommandIntent, StrictModel


class ExecutorInventory(StrictModel):
    executor_id: str = Field(min_length=1, max_length=128)
    generation: str = Field(min_length=1, max_length=128)
    account: AccountSnapshot
    symbol: str = Field(min_length=1, max_length=32)
    observed_at: datetime
    complete: StrictBool
    foreign_orders: StrictInt = Field(ge=0, le=100000)
    foreign_positions: StrictInt = Field(ge=0, le=100000)
    snapshots: tuple[BrokerSnapshot, ...] = Field(max_length=1000)


class ExecutorAdapter(Protocol):
    def inventory(self) -> ExecutorInventory: ...

    def send(self, intent: CommandIntent, volume: Decimal, attempt_id: str) -> BrokerSnapshot: ...

    def query(self, command_id: str) -> BrokerSnapshot | None: ...
