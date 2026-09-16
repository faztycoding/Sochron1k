from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .models import BrokerDeal, BrokerSnapshot, CommandIntent, CommandState


class SimulatorBehavior(StrEnum):
    FILL = "fill"
    ACCEPT_THEN_TIMEOUT = "accept_then_timeout"
    PARTIAL_FILL = "partial_fill"
    REJECT_SL = "reject_sl"
    REJECT = "reject"


@dataclass
class SimulatorAdapter:
    behavior: SimulatorBehavior = SimulatorBehavior.FILL

    def __post_init__(self) -> None:
        self.send_count = 0
        self._snapshots: dict[str, BrokerSnapshot] = {}
        self.query_available = True

    def send(self, intent: CommandIntent, volume: Decimal, attempt_id: str) -> BrokerSnapshot:
        del attempt_id
        if intent.command_id in self._snapshots:
            return self._snapshots[intent.command_id]
        self.send_count += 1
        suffix = intent.command_id[-8:]
        order_ticket = f"ord-{suffix}"
        position_id = f"pos-{suffix}"
        if self.behavior is SimulatorBehavior.REJECT:
            snapshot = BrokerSnapshot(
                command_id=intent.command_id,
                order_ticket=order_ticket,
                requested_volume=volume,
                filled_volume=Decimal("0"),
                remaining_volume=volume,
                stop_loss_confirmed=False,
                terminal_state=CommandState.REJECTED,
            )
        else:
            filled = volume / 2 if self.behavior is SimulatorBehavior.PARTIAL_FILL else volume
            remaining = volume - filled
            deal = BrokerDeal(
                deal_ticket=f"deal-{suffix}-1",
                volume=filled,
                price=intent.requested_entry,
            )
            snapshot = BrokerSnapshot(
                command_id=intent.command_id,
                order_ticket=order_ticket,
                position_id=position_id,
                requested_volume=volume,
                filled_volume=filled,
                remaining_volume=remaining,
                deals=(deal,),
                stop_loss_confirmed=self.behavior is not SimulatorBehavior.REJECT_SL,
            )
        self._snapshots[intent.command_id] = snapshot
        if self.behavior is SimulatorBehavior.ACCEPT_THEN_TIMEOUT:
            raise TimeoutError("simulated response loss after broker acceptance")
        return snapshot

    def query(self, command_id: str) -> BrokerSnapshot | None:
        if not self.query_available:
            raise ConnectionError("simulated broker query unavailable")
        return self._snapshots.get(command_id)
