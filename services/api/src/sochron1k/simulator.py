from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from .executor import ExecutorInventory, ExecutorRejected
from .models import (
    AccountSnapshot,
    BrokerDeal,
    BrokerSnapshot,
    CommandIntent,
    CommandState,
    ExecutorRejection,
    ManagementIntent,
    ManagementOperation,
    ManagementSnapshot,
)


class SimulatorBehavior(StrEnum):
    FILL = "fill"
    ACCEPT_THEN_TIMEOUT = "accept_then_timeout"
    PARTIAL_FILL = "partial_fill"
    REJECT_SL = "reject_sl"
    REJECT = "reject"


class ManagementBehavior(StrEnum):
    COMPLETE = "complete"
    ACCEPT_THEN_TIMEOUT = "accept_then_timeout"
    PARTIAL_CLOSE = "partial_close"
    REJECT = "reject"


@dataclass
class SimulatorAdapter:
    behavior: SimulatorBehavior = SimulatorBehavior.FILL
    account: AccountSnapshot | None = None
    symbol: str = ""
    management_behavior: ManagementBehavior = ManagementBehavior.COMPLETE
    close_profit: Decimal = Decimal("0")
    close_commission: Decimal = Decimal("0")
    close_swap: Decimal = Decimal("0")
    close_fee: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.send_count = 0
        self.manage_count = 0
        self._snapshots: dict[str, BrokerSnapshot] = {}
        self._management_snapshots: dict[str, ManagementSnapshot] = {}
        self._rejections: dict[str, ExecutorRejection] = {}
        self.query_available = True
        self.generation = uuid4().hex
        self.executor_id = "simulator"
        self.complete = True
        self.foreign_orders = 0
        self.foreign_positions = 0

    def inventory(self) -> ExecutorInventory:
        if not self.query_available or self.account is None:
            raise ConnectionError("simulator inventory is unavailable or unconfigured")
        return ExecutorInventory(
            executor_id=self.executor_id,
            generation=self.generation,
            account=self.account,
            symbol=self.symbol,
            observed_at=self.account.checked_at,
            complete=self.complete,
            foreign_orders=self.foreign_orders,
            foreign_positions=self.foreign_positions,
            snapshots=tuple(self._snapshots.values()),
            management_snapshots=tuple(self._management_snapshots.values()),
            rejections=tuple(self._rejections.values()),
        )

    def send(
        self,
        intent: CommandIntent,
        volume: Decimal,
        risk_limit: Decimal,
        cost_budget: Decimal,
        attempt_id: str,
    ) -> BrokerSnapshot:
        del attempt_id
        if (
            not all(isinstance(value, Decimal) and value.is_finite() for value in (
                volume,
                risk_limit,
                cost_budget,
            ))
            or volume <= 0
            or risk_limit <= 0
            or cost_budget < 0
            or cost_budget >= risk_limit
        ):
            raise ValueError("invalid simulator risk authorization")
        self.last_risk_limit = risk_limit
        self.last_cost_budget = cost_budget
        if intent.command_id in self._snapshots:
            return self._snapshots[intent.command_id]
        if intent.command_id in self._rejections:
            raise ExecutorRejected(self._rejections[intent.command_id])
        self.send_count += 1
        suffix = intent.command_id[-8:]
        order_ticket = f"ord-{suffix}"
        position_id = f"pos-{suffix}"
        if self.behavior is SimulatorBehavior.REJECT:
            rejection = ExecutorRejection(
                command_id=intent.command_id,
                operation="open",
                retcode=10006,
                retcode_external=0,
                request_id=self.send_count,
                observed_at=self.account.checked_at,
            )
            self._rejections[intent.command_id] = rejection
            raise ExecutorRejected(rejection)
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

    def query(self, command_id: str) -> BrokerSnapshot | ExecutorRejection | None:
        if not self.query_available:
            raise ConnectionError("simulated broker query unavailable")
        return self._snapshots.get(command_id) or self._rejections.get(command_id)

    def manage(
        self,
        intent: ManagementIntent,
        target: BrokerSnapshot,
        attempt_id: str,
    ) -> ManagementSnapshot:
        del attempt_id
        if intent.command_id in self._management_snapshots:
            return self._management_snapshots[intent.command_id]
        if intent.command_id in self._rejections:
            raise ExecutorRejected(self._rejections[intent.command_id])
        current = self._snapshots.get(intent.target_command_id)
        current_deals = (
            {deal.deal_ticket: deal for deal in current.deals} if current is not None else {}
        )
        target_deals = {deal.deal_ticket: deal for deal in target.deals}
        if (
            current is None
            or current.model_dump(exclude={"deals"}) != target.model_dump(exclude={"deals"})
            or len(current_deals) != len(current.deals)
            or current_deals != target_deals
        ):
            raise RuntimeError("simulated target changed before management")
        if self.account is None:
            raise ConnectionError("simulator is unconfigured")
        self.manage_count += 1
        suffix = intent.command_id[-8:]
        if intent.operation is ManagementOperation.CANCEL:
            requested = current.remaining_volume
            if requested <= 0:
                raise RuntimeError("simulated target has no pending volume")
            if self.management_behavior is ManagementBehavior.REJECT:
                rejection = ExecutorRejection(
                    command_id=intent.command_id,
                    target_command_id=intent.target_command_id,
                    operation=intent.operation.value,
                    retcode=10006,
                    retcode_external=0,
                    request_id=self.manage_count,
                    observed_at=self.account.checked_at,
                )
                self._rejections[intent.command_id] = rejection
                raise ExecutorRejected(rejection)
            else:
                completed = requested
                remaining = Decimal("0")
                target_terminal = (
                    CommandState.CANCELLED if current.open_position_volume == 0 else None
                )
                target_after = current.model_copy(
                    update={
                        "remaining_volume": Decimal("0"),
                        "cancelled_volume": current.cancelled_volume + requested,
                        "terminal_state": target_terminal,
                    }
                )
                terminal = CommandState.CANCELLED
            snapshot = ManagementSnapshot(
                command_id=intent.command_id,
                target_command_id=intent.target_command_id,
                operation=intent.operation,
                broker_order_ticket=current.order_ticket or f"cancel-{suffix}",
                position_id=current.position_id,
                requested_volume=requested,
                completed_volume=completed,
                remaining_volume=remaining,
                terminal_state=terminal,
                target=target_after,
                observed_at=self.account.checked_at,
            )
        else:
            requested = current.open_position_volume
            if current.remaining_volume or requested <= 0:
                raise RuntimeError("simulated target is not closeable")
            if self.management_behavior is ManagementBehavior.REJECT:
                rejection = ExecutorRejection(
                    command_id=intent.command_id,
                    target_command_id=intent.target_command_id,
                    operation=intent.operation.value,
                    retcode=10006,
                    retcode_external=0,
                    request_id=self.manage_count,
                    observed_at=self.account.checked_at,
                )
                self._rejections[intent.command_id] = rejection
                raise ExecutorRejected(rejection)
            else:
                completed = (
                    requested / 2
                    if self.management_behavior is ManagementBehavior.PARTIAL_CLOSE
                    else requested
                )
                remaining = requested - completed
                deal = BrokerDeal(
                    deal_ticket=f"exit-{suffix}-1",
                    volume=completed,
                    price=current.deals[-1].price,
                    profit=self.close_profit,
                    commission=self.close_commission,
                    swap=self.close_swap,
                    fee=self.close_fee,
                    occurred_at=self.account.checked_at,
                )
                deals = (deal,)
                target_terminal = CommandState.CLOSED if remaining == 0 else None
                target_after = current.model_copy(
                    update={
                        "closed_volume": current.closed_volume + completed,
                        "stop_loss_confirmed": current.stop_loss_confirmed and remaining > 0,
                        "terminal_state": target_terminal,
                    }
                )
                terminal = target_terminal
            snapshot = ManagementSnapshot(
                command_id=intent.command_id,
                target_command_id=intent.target_command_id,
                operation=intent.operation,
                broker_order_ticket=f"close-{suffix}",
                position_id=current.position_id,
                requested_volume=requested,
                completed_volume=completed,
                remaining_volume=remaining,
                deals=deals,
                terminal_state=terminal,
                target=target_after,
                observed_at=self.account.checked_at,
            )
        self._snapshots[intent.target_command_id] = snapshot.target
        self._management_snapshots[intent.command_id] = snapshot
        if self.management_behavior is ManagementBehavior.ACCEPT_THEN_TIMEOUT:
            raise TimeoutError("simulated response loss after management acceptance")
        return snapshot

    def query_management(self, command_id: str) -> ManagementSnapshot | ExecutorRejection | None:
        if not self.query_available:
            raise ConnectionError("simulated broker query unavailable")
        return self._management_snapshots.get(command_id) or self._rejections.get(command_id)
