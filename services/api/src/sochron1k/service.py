from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from .executor import ExecutorAdapter
from .journal import BrokerEvidenceConflict, Journal, ManagementConflict
from .models import (
    AccountSnapshot,
    CommandIntent,
    CommandState,
    ContractSpec,
    ManagementIntent,
    ManagementSnapshot,
    MarketSnapshot,
    RiskContext,
    SubmissionResult,
)
from .preflight import PreflightPolicy, validate_preflight
from .risk import size_position
from .startup import StartupDenied, inspect_startup


class RiskDenied(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ExecutionService:
    def __init__(self, journal: Journal, adapter: ExecutorAdapter) -> None:
        self.journal = journal
        self.adapter = adapter
        self._startup = None
        self._pid = os.getpid()
        self._lock = threading.RLock()
        self._journal_identity = (journal.path.stat().st_dev, journal.path.stat().st_ino)

    def _inspect(self, policy, experiment_id, executor_id, now, generation=None):
        if self._pid != os.getpid():
            self._startup = None
            raise RiskDenied("STARTUP_REQUIRED")
        try:
            if self._journal_identity != (
                self.journal.path.stat().st_dev,
                self.journal.path.stat().st_ino,
            ):
                raise StartupDenied("STARTUP_JOURNAL_CHANGED")
            return inspect_startup(
                self.journal, self.adapter, policy, experiment_id, executor_id, now, generation
            )
        except Exception as error:
            self._startup = None
            reason = error.reason if isinstance(error, StartupDenied) else "STARTUP_UNAVAILABLE"
            raise RiskDenied(reason) from None

    def startup(self, *, policy, experiment_id, executor_id, now=None):
        # PID check precedes a possibly inherited locked mutex after fork.
        if self._pid != os.getpid():
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            self._startup = None
            inventory, state, occupied = self._inspect(
                policy, experiment_id, executor_id, now or datetime.now(UTC)
            )
            self._startup = (policy, experiment_id, executor_id, inventory.generation, state)
            return dict(
                state="RECONCILED",
                local_entries_admitted=not (occupied or state.total_halt or state.daily_halt),
                execution_ready=False,
                auto_trading_enabled=False,
            )

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
        if self._pid != os.getpid() or self._startup is None:
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            try:
                return self._submit(
                    policy=policy,
                    account=account,
                    contract=contract,
                    market=market,
                    intent=intent,
                    risk=risk,
                    now=now,
                )
            except Exception:
                self._startup = None
                raise

    def _submit(self, *, policy, account, contract, market, intent, risk, now):
        if self._startup is None:
            raise RiskDenied("STARTUP_REQUIRED")
        started = time.monotonic()
        observed_at = now or datetime.now(UTC)

        def fresh_preflight():
            elapsed = time.monotonic() - started
            if elapsed < 0:
                raise RiskDenied("STARTUP_INVALID_TIME")
            checked_at = observed_at + timedelta(seconds=elapsed)
            validate_preflight(policy, account, contract, market, intent, now=checked_at)
            if not 0 <= (checked_at - account.checked_at).total_seconds() <= 5:
                raise RiskDenied("EXECUTOR_INVENTORY_STALE")
            if admitted_risk.bangkok_day != checked_at.astimezone(ZoneInfo("Asia/Bangkok")).date():
                raise RiskDenied("RISK_DAY_REVIEW_REQUIRED")

        bound_policy, experiment, executor, generation, admitted_risk = self._startup
        if policy != bound_policy or intent.experiment_id != experiment:
            raise RiskDenied("STARTUP_BINDING_MISMATCH")
        inventory, current_risk, _ = self._inspect(
            policy, experiment, executor, observed_at, generation
        )
        if (
            current_risk.bangkok_day,
            current_risk.daily_baseline,
            current_risk.experiment_baseline,
        ) != (
            admitted_risk.bangkok_day,
            admitted_risk.daily_baseline,
            admitted_risk.experiment_baseline,
        ):
            raise RiskDenied("RISK_BASELINE_MISMATCH")
        if account != inventory.account or risk.equity != inventory.account.equity:
            raise RiskDenied("ACCOUNT_SNAPSHOT_MISMATCH")
        if intent.operation != "open":
            raise RiskDenied("OPERATION_NOT_IMPLEMENTED")
        fresh_preflight()
        persistent_risk = self.journal.risk_state(intent.account_ref, intent.experiment_id)
        if persistent_risk is None:
            raise RiskDenied("RISK_BASELINE_MISSING")
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
        reservation = self.journal.reserve(
            intent, decision.volume, decision.estimated_loss, expected_risk=persistent_risk
        )
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
        self.journal.begin_dispatch(intent.command_id, attempt_id, expected_risk=persistent_risk)
        # Local journal work can outlive quote freshness or command expiry. The executor
        # must also recheck immediately at its own mutation boundary in a real adapter.
        fresh_preflight()
        try:
            snapshot = self.adapter.send(intent, decision.volume, attempt_id)
            if snapshot.command_id != intent.command_id:
                raise BrokerEvidenceConflict()
            state = self.journal.apply_broker_snapshot(snapshot)
        except Exception:
            # Invocation may already have had an effect even for an unexpected
            # exception/malformed response. Persist UNKNOWN or propagate storage
            # failure; never return a fill or silently replay the command.
            self._startup = None
            self.journal.transition(
                intent.command_id,
                CommandState.UNKNOWN,
                "adapter outcome unconfirmed after dispatch; reconciliation required",
            )
            return SubmissionResult(
                command_id=intent.command_id,
                state=CommandState.UNKNOWN,
                volume=decision.volume,
                reason="RECONCILIATION_REQUIRED",
            )
        return SubmissionResult(
            command_id=intent.command_id,
            state=state,
            volume=decision.volume,
            protected=snapshot.stop_loss_confirmed,
            reason="EMERGENCY_CLOSE_REQUIRED" if state is CommandState.PROTECTION_FAILED else None,
        )

    def manage(
        self,
        *,
        policy: PreflightPolicy,
        account: AccountSnapshot,
        intent: ManagementIntent,
        now: datetime | None = None,
    ) -> SubmissionResult:
        if self._pid != os.getpid() or self._startup is None:
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            try:
                return self._manage(policy=policy, account=account, intent=intent, now=now)
            except RiskDenied as error:
                if error.reason in {
                    "NO_PENDING_ORDER",
                    "PENDING_CANCEL_REQUIRED",
                    "NO_OPEN_POSITION",
                    "TARGET_COMMAND_NOT_FOUND",
                    "TARGET_BINDING_MISMATCH",
                    "TARGET_BROKER_EVIDENCE_MISSING",
                }:
                    raise
                self._startup = None
                raise
            except Exception:
                self._startup = None
                raise

    def _manage(self, *, policy, account, intent, now):
        if self._startup is None:
            raise RiskDenied("STARTUP_REQUIRED")
        started = time.monotonic()
        observed_at = now or datetime.now(UTC)

        def fresh_management_preflight():
            elapsed = time.monotonic() - started
            if elapsed < 0:
                raise RiskDenied("STARTUP_INVALID_TIME")
            checked_at = observed_at + timedelta(seconds=elapsed)
            if (
                checked_at > intent.expires_at
                or account.trade_mode.value != "demo"
                or not account.can_trade
                or account.account_ref != policy.account_ref
                or account.server != policy.server
                or account.currency != policy.currency
                or account.margin_mode != policy.margin_mode
                or intent.account_ref != policy.account_ref
                or intent.experiment_id != experiment
                or intent.symbol != policy.symbol
                or not 0 <= (checked_at - account.checked_at).total_seconds() <= 5
            ):
                raise RiskDenied("MANAGEMENT_PREFLIGHT_DENIED")
            return checked_at

        bound_policy, experiment, executor, generation, admitted_risk = self._startup
        if policy != bound_policy or intent.experiment_id != experiment:
            raise RiskDenied("STARTUP_BINDING_MISMATCH")
        inventory, current_risk, _ = self._inspect(
            policy, experiment, executor, observed_at, generation
        )
        if (
            current_risk.bangkok_day,
            current_risk.daily_baseline,
            current_risk.experiment_baseline,
        ) != (
            admitted_risk.bangkok_day,
            admitted_risk.daily_baseline,
            admitted_risk.experiment_baseline,
        ):
            raise RiskDenied("RISK_BASELINE_MISMATCH")
        if account != inventory.account:
            raise RiskDenied("ACCOUNT_SNAPSHOT_MISMATCH")
        fresh_management_preflight()
        try:
            reservation = self.journal.reserve_management(intent, expected_risk=current_risk)
        except ManagementConflict as error:
            if error.reason in {
                "NO_PENDING_ORDER",
                "PENDING_CANCEL_REQUIRED",
                "NO_OPEN_POSITION",
                "TARGET_COMMAND_NOT_FOUND",
                "TARGET_BINDING_MISMATCH",
                "TARGET_BROKER_EVIDENCE_MISSING",
            }:
                raise RiskDenied(error.reason) from None
            raise
        if reservation.duplicate:
            row = self.journal.management_command(reservation.command_id)
            return SubmissionResult(
                command_id=reservation.command_id,
                state=CommandState(row["state"]),
                volume=reservation.volume,
                duplicate=True,
            )
        attempt_id = str(uuid.uuid4())
        self.journal.begin_management_dispatch(
            intent.command_id, attempt_id, expected_risk=current_risk
        )
        fresh_management_preflight()
        target = self.journal.broker_snapshot(intent.target_command_id)
        try:
            snapshot = self.adapter.manage(intent, target, attempt_id)
            snapshot = ManagementSnapshot.model_validate(snapshot.model_dump())
            if (
                snapshot.command_id != intent.command_id
                or snapshot.target_command_id != intent.target_command_id
            ):
                raise BrokerEvidenceConflict()
            checked_at = observed_at + timedelta(seconds=time.monotonic() - started)
            if not 0 <= (checked_at - snapshot.observed_at).total_seconds() <= 5:
                raise BrokerEvidenceConflict()
            state = self.journal.apply_management_snapshot(snapshot)
        except Exception:
            self._startup = None
            self.journal.transition_management(
                intent.command_id,
                CommandState.UNKNOWN,
                "adapter outcome unconfirmed after management dispatch",
            )
            return SubmissionResult(
                command_id=intent.command_id,
                state=CommandState.UNKNOWN,
                volume=reservation.volume,
                reason="RECONCILIATION_REQUIRED",
            )
        return SubmissionResult(
            command_id=intent.command_id,
            state=state,
            volume=reservation.volume,
            protected=snapshot.target.stop_loss_confirmed,
        )

    def reconcile(self, command_id: str) -> SubmissionResult:
        if self._pid != os.getpid():
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            self._startup = None
            return self._reconcile(command_id)

    def _reconcile(self, command_id: str) -> SubmissionResult:
        row = self.journal.command(command_id)
        snapshot = self.adapter.query(command_id)
        if snapshot is None:
            return SubmissionResult(
                command_id=command_id,
                state=CommandState.UNKNOWN,
                volume=Decimal(row["volume"]),
                reason="BROKER_OUTCOME_NOT_FOUND",
            )
        if snapshot.command_id != command_id:
            raise BrokerEvidenceConflict()
        state = self.journal.apply_broker_snapshot(snapshot)
        return SubmissionResult(
            command_id=command_id,
            state=state,
            volume=Decimal(row["volume"]),
            protected=snapshot.stop_loss_confirmed,
        )

    def reconcile_management(self, command_id: str) -> SubmissionResult:
        if self._pid != os.getpid():
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            self._startup = None
            row = self.journal.management_command(command_id)
            snapshot = self.adapter.query_management(command_id)
            if snapshot is None:
                return SubmissionResult(
                    command_id=command_id,
                    state=CommandState.UNKNOWN,
                    volume=Decimal(row["requested_volume"]),
                    reason="BROKER_OUTCOME_NOT_FOUND",
                )
            if snapshot.command_id != command_id:
                raise BrokerEvidenceConflict()
            state = self.journal.apply_management_snapshot(snapshot)
            return SubmissionResult(
                command_id=command_id,
                state=state,
                volume=Decimal(row["requested_volume"]),
                protected=snapshot.target.stop_loss_confirmed,
            )

    def recover_management(self) -> dict[str, CommandState]:
        if self._pid != os.getpid():
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            self._startup = None
            outcomes = {}
            for command_id in self.journal.unresolved_management_ids():
                try:
                    outcomes[command_id] = self.reconcile_management(command_id).state
                except ConnectionError:
                    current = CommandState(self.journal.management_command(command_id)["state"])
                    if current is not CommandState.UNKNOWN:
                        self.journal.transition_management(
                            command_id,
                            CommandState.UNKNOWN,
                            "broker unavailable during management reconciliation",
                        )
                    outcomes[command_id] = CommandState.UNKNOWN
            return outcomes

    def recover(self) -> dict[str, CommandState]:
        if self._pid != os.getpid():
            raise RiskDenied("STARTUP_REQUIRED")
        with self._lock:
            self._startup = None
            return self._recover()

    def _recover(self) -> dict[str, CommandState]:
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
