from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from .journal import Journal
from .models import (
    AccountSnapshot,
    CommandIntent,
    CommandState,
    ContractSpec,
    MarketSnapshot,
    RiskContext,
    SubmissionResult,
)
from .preflight import PreflightPolicy, validate_preflight
from .risk import size_position
from .simulator import SimulatorAdapter


class RiskDenied(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ExecutionService:
    def __init__(self, journal: Journal, adapter: SimulatorAdapter) -> None:
        self.journal = journal
        self.adapter = adapter

    def submit(
        self,
        *,
        policy: PreflightPolicy,
        account: AccountSnapshot,
        contract: ContractSpec,
        market: MarketSnapshot,
        intent: CommandIntent,
        risk: RiskContext,
        now: datetime | None = None,
    ) -> SubmissionResult:
        observed_at = now or datetime.now(UTC)
        validate_preflight(policy, account, contract, market, intent, now=observed_at)
        persistent_risk = self.journal.risk_state(intent.account_ref, intent.experiment_id)
        if persistent_risk is not None:
            if persistent_risk.total_halt:
                raise RiskDenied("TOTAL_HALT_ACTIVE")
            if persistent_risk.daily_halt:
                raise RiskDenied("DAILY_HALT_ACTIVE")
            if (
                persistent_risk.daily_baseline != risk.daily_baseline
                or persistent_risk.experiment_baseline != risk.experiment_baseline
            ):
                raise RiskDenied("RISK_BASELINE_MISMATCH")
        decision = size_position(risk, contract)
        if not decision.allowed:
            raise RiskDenied(decision.reason or "RISK_DENIED")
        reservation = self.journal.reserve(intent, decision.volume, decision.estimated_loss)
        if reservation.duplicate:
            row = self.journal.command(reservation.command_id)
            return SubmissionResult(
                command_id=reservation.command_id,
                state=CommandState(row["state"]),
                volume=reservation.volume,
                duplicate=True,
                protected=bool(row["protected"]),
            )

        attempt_id = str(uuid.uuid4())
        self.journal.begin_dispatch(intent.command_id, attempt_id)
        try:
            snapshot = self.adapter.send(intent, decision.volume, attempt_id)
        except TimeoutError:
            self.journal.transition(
                intent.command_id,
                CommandState.UNKNOWN,
                "adapter response missing after dispatch; reconciliation required",
            )
            return SubmissionResult(
                command_id=intent.command_id,
                state=CommandState.UNKNOWN,
                volume=decision.volume,
                reason="RECONCILIATION_REQUIRED",
            )
        state = self.journal.apply_broker_snapshot(snapshot)
        return SubmissionResult(
            command_id=intent.command_id,
            state=state,
            volume=decision.volume,
            protected=snapshot.stop_loss_confirmed,
            reason="EMERGENCY_CLOSE_REQUIRED" if state is CommandState.PROTECTION_FAILED else None,
        )

    def reconcile(self, command_id: str) -> SubmissionResult:
        row = self.journal.command(command_id)
        snapshot = self.adapter.query(command_id)
        if snapshot is None:
            return SubmissionResult(
                command_id=command_id,
                state=CommandState.UNKNOWN,
                volume=Decimal(row["volume"]),
                reason="BROKER_OUTCOME_NOT_FOUND",
            )
        state = self.journal.apply_broker_snapshot(snapshot)
        return SubmissionResult(
            command_id=command_id,
            state=state,
            volume=Decimal(row["volume"]),
            protected=snapshot.stop_loss_confirmed,
        )

    def recover(self) -> dict[str, CommandState]:
        outcomes: dict[str, CommandState] = {}
        for command_id in self.journal.unresolved_command_ids():
            try:
                outcomes[command_id] = self.reconcile(command_id).state
            except ConnectionError:
                current = CommandState(self.journal.command(command_id)["state"])
                if current is not CommandState.UNKNOWN:
                    self.journal.transition(
                        command_id,
                        CommandState.UNKNOWN,
                        "broker unavailable during startup reconciliation",
                    )
                outcomes[command_id] = CommandState.UNKNOWN
        return outcomes
