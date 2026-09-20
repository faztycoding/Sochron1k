"""One explicitly authorized Demo round trip; never an unattended dispatcher."""

from __future__ import annotations

import os
import secrets
import stat
import threading
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, SecretStr, StrictBool, field_validator, model_validator

from .executor import ExecutorAdapter
from .journal import (
    ExposureConflict,
    IdempotencyConflict,
    Journal,
    ManagementConflict,
    RiskStateConflict,
)
from .models import (
    AccountSnapshot,
    CommandIntent,
    CommandState,
    ContractSpec,
    ManagementIntent,
    ManagementOperation,
    MarketSnapshot,
    RiskContext,
    RiskState,
    StrictModel,
    SubmissionResult,
    TradeMode,
)
from .preflight import PreflightPolicy
from .risk import EXPERIMENT_LOSS_LIMIT
from .service import ExecutionService, RiskDenied
from .telemetry import DemoIdentity

MAX_ROUND_TRIP_CONFIG_BYTES = 32_768
SafeText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"),
]
WireId = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


class DemoRoundTripSettings(StrictModel):
    protocol: Literal["sochron.demo-round-trip-config.v1"]
    identity: DemoIdentity
    token: SecretStr
    journal_file: Path
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    decision_revision: SafeText
    experiment_id: WireId
    signal_id: WireId
    strategy_version: str = Field(
        min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"
    )
    entry_command_id: WireId
    cancel_command_id: WireId
    close_command_id: WireId
    experiment_baseline: Decimal = Field(
        gt=0, allow_inf_nan=False, max_digits=18, decimal_places=2
    )
    minimum_costs_per_lot: Decimal = Field(
        gt=0, allow_inf_nan=False, max_digits=18, decimal_places=8
    )
    authorized_at_utc: AwareDatetime
    entry_authorization_expires_at_utc: AwareDatetime

    @field_validator("token")
    @classmethod
    def private_token(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not 43 <= len(raw) <= 128 or not all(
            char.isascii() and (char.isalnum() or char in "-_") for char in raw
        ):
            raise ValueError("use a separately generated URL-safe round-trip credential")
        return value

    @field_validator("journal_file", mode="before")
    @classmethod
    def canonical_journal_path(cls, value: object) -> Path:
        if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
            raise ValueError("canonical absolute journal path required")
        path = Path(value)
        if not path.is_absolute() or path.resolve() != path or str(path) != str(value):
            raise ValueError("canonical absolute journal path required")
        return str(path)

    @field_validator("authorized_at_utc", "entry_authorization_expires_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def bounded_authorization(self) -> Self:
        window = self.entry_authorization_expires_at_utc - self.authorized_at_utc
        if not timedelta(0) < window <= timedelta(hours=24):
            raise ValueError("entry authorization must be positive and no longer than 24 hours")
        if len({self.entry_command_id, self.cancel_command_id, self.close_command_id}) != 3:
            raise ValueError("round-trip command identifiers must be distinct")
        return self

    @property
    def policy(self) -> PreflightPolicy:
        return PreflightPolicy(
            account_ref=self.identity.account_ref,
            server=self.identity.server,
            symbol=self.identity.symbol,
            currency=self.identity.currency,
            margin_mode=self.identity.margin_mode,
        )


def _private_config_bytes(path: Path) -> bytes:
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("canonical private config required")
    parent = path.parent.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.getuid()
        or stat.S_IMODE(parent.st_mode) & 0o077
    ):
        raise ValueError("private config directory required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
            ):
                raise ValueError("private config required")
            raw = stream.read(MAX_ROUND_TRIP_CONFIG_BYTES + 1)
            after = os.fstat(stream.fileno())
        current = path.lstat()
        if (
            len(raw) > MAX_ROUND_TRIP_CONFIG_BYTES
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or (after.st_dev, after.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise ValueError("unstable private config")
        return raw
    except Exception:
        with suppress(OSError):
            os.close(descriptor)
        raise


def load_demo_round_trip_settings() -> DemoRoundTripSettings | None:
    configured = os.environ.get("SOCHRON_DEMO_ROUND_TRIP_CONFIG_FILE")
    if not configured:
        return None
    try:
        return DemoRoundTripSettings.model_validate_json(
            _private_config_bytes(Path(configured))
        )
    except (OSError, ValueError):
        raise RuntimeError(
            "Invalid private Demo round-trip configuration; admission not started"
        ) from None


class DemoRoundTripOpenRequest(StrictModel):
    protocol: Literal["sochron.demo-round-trip-open.v1"]
    account: AccountSnapshot
    contract: ContractSpec
    market: MarketSnapshot
    intent: CommandIntent
    risk: RiskContext


class DemoRoundTripManagementRequest(StrictModel):
    protocol: Literal["sochron.demo-round-trip-management.v1"]
    account: AccountSnapshot
    intent: ManagementIntent


RoundTripState = Literal[
    "disabled",
    "awaiting_baseline",
    "awaiting_startup",
    "armed",
    "entry_recorded",
    "complete",
    "expired",
    "degraded",
]


class DemoRoundTripStatus(StrictModel):
    protocol: Literal["sochron.demo-round-trip-status.v1"] = (
        "sochron.demo-round-trip-status.v1"
    )
    state: RoundTripState
    configured: StrictBool
    risk_baseline_present: StrictBool = False
    entry_recorded: StrictBool = False
    entry_authorization_current: StrictBool = False
    bounded_round_trip: Literal[True] = True
    trading_mode: Literal["demo"] = "demo"
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False
    release_ready: Literal[False] = False
    unattended_demo_ready: Literal[False] = False


class RiskBaselineReceipt(StrictModel):
    protocol: Literal["sochron.risk-baseline-receipt.v1"] = (
        "sochron.risk-baseline-receipt.v1"
    )
    created: StrictBool
    bangkok_day: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    daily_halt: StrictBool
    total_halt: StrictBool
    execution_ready: Literal[False] = False
    auto_trading_enabled: Literal[False] = False


class StartupReceipt(StrictModel):
    protocol: Literal["sochron.demo-round-trip-startup.v1"] = (
        "sochron.demo-round-trip-startup.v1"
    )
    state: Literal["RECONCILED"]
    local_entries_admitted: StrictBool
    execution_ready: Literal[False] = False
    auto_trading_enabled: Literal[False] = False


class DemoRoundTripDenied(RuntimeError):
    def __init__(self, code: str, *, unavailable: bool = False) -> None:
        self.code = code
        self.unavailable = unavailable
        super().__init__(code)


class DemoRoundTripController:
    def __init__(
        self,
        settings: DemoRoundTripSettings,
        adapter: ExecutorAdapter,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = settings
        self.adapter = adapter
        self._utc_now = utc_now
        self._lock = threading.RLock()
        self._started = False
        self.journal = Journal(self._prepare_journal(settings.journal_file))
        self.service = ExecutionService(self.journal, adapter)

    @staticmethod
    def _prepare_journal(path: Path) -> Path:
        parent = path.parent
        info = parent.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise RuntimeError("Private Demo round-trip journal directory required")
        try:
            current = path.lstat()
        except FileNotFoundError:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            os.close(descriptor)
            current = path.lstat()
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_uid != os.getuid()
            or current.st_nlink != 1
            or stat.S_IMODE(current.st_mode) & 0o077
        ):
            raise RuntimeError("Private Demo round-trip journal required")
        return path

    def authenticate(self, credentials: list[str]) -> bool:
        if len(credentials) != 1:
            return False
        supplied = credentials[0]
        if not supplied.isascii() or len(supplied) > 256:
            return False
        expected = "Bearer " + self.settings.token.get_secret_value()
        return secrets.compare_digest(supplied, expected)

    def _now(self) -> datetime:
        value = self._utc_now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise DemoRoundTripDenied("SERVER_TIME_INVALID", unavailable=True)
        return value.astimezone(UTC)

    def status(self) -> DemoRoundTripStatus:
        try:
            now = self._now()
            risk = self.journal.risk_state(
                self.settings.identity.account_ref, self.settings.experiment_id
            )
            try:
                entry = self.journal.command(self.settings.entry_command_id)
            except KeyError:
                entry = None
            current = (
                self.settings.authorized_at_utc
                <= now
                <= self.settings.entry_authorization_expires_at_utc
            )
            if entry is not None:
                state = (
                    "complete"
                    if CommandState(entry["state"])
                    in {
                        CommandState.CLOSED,
                        CommandState.CANCELLED,
                        CommandState.REJECTED,
                        CommandState.EXPIRED,
                    }
                    else "entry_recorded"
                )
            elif risk is None:
                state = "awaiting_baseline"
            elif not current:
                state = "expired"
            elif not self._started:
                state = "awaiting_startup"
            else:
                state = "armed"
            return DemoRoundTripStatus(
                state=state,
                configured=True,
                risk_baseline_present=risk is not None,
                entry_recorded=entry is not None,
                entry_authorization_current=current,
            )
        except DemoRoundTripDenied:
            return DemoRoundTripStatus(state="degraded", configured=True)
        except Exception:
            return DemoRoundTripStatus(state="degraded", configured=True)

    def initialize_risk_baseline(self) -> RiskBaselineReceipt:
        with self._lock:
            now = self._now()
            try:
                inventory = self.adapter.inventory()
            except Exception:
                raise DemoRoundTripDenied(
                    "EXECUTOR_INVENTORY_UNAVAILABLE", unavailable=True
                ) from None
            account = inventory.account
            identity = self.settings.identity
            if (
                not inventory.complete
                or inventory.executor_id != identity.executor_id
                or inventory.symbol != identity.symbol
                or inventory.foreign_orders
                or inventory.foreign_positions
                or inventory.snapshots
                or inventory.management_snapshots
                or inventory.rejections
                or account.trade_mode is not TradeMode.DEMO
                or account.account_ref != identity.account_ref
                or account.server != identity.server
                or account.currency != identity.currency
                or account.margin_mode != identity.margin_mode
                or not account.can_trade
                or inventory.observed_at.tzinfo is None
                or account.checked_at.tzinfo is None
                or not 0
                <= (now - inventory.observed_at.astimezone(UTC)).total_seconds()
                <= 5
                or not 0 <= (now - account.checked_at.astimezone(UTC)).total_seconds() <= 5
            ):
                raise DemoRoundTripDenied("RISK_BASELINE_INVENTORY_DENIED")
            day = now.astimezone(ZoneInfo("Asia/Bangkok")).date()
            existing = self.journal.risk_state(identity.account_ref, self.settings.experiment_id)
            if existing is not None:
                if (
                    existing.experiment_baseline != self.settings.experiment_baseline
                    or existing.bangkok_day != day
                ):
                    raise DemoRoundTripDenied("RISK_BASELINE_CONFLICT")
                updated = self.journal.latch_halts(
                    identity.account_ref,
                    self.settings.experiment_id,
                    account.equity,
                    now,
                )
                return RiskBaselineReceipt(
                    created=False,
                    bangkok_day=updated.bangkok_day.isoformat(),
                    daily_halt=updated.daily_halt,
                    total_halt=updated.total_halt,
                )
            experiment_floor = self.settings.experiment_baseline * (
                Decimal(1) - EXPERIMENT_LOSS_LIMIT
            )
            state = RiskState(
                account_ref=identity.account_ref,
                experiment_id=self.settings.experiment_id,
                bangkok_day=day,
                daily_baseline=account.equity,
                experiment_baseline=self.settings.experiment_baseline,
                total_halt=account.equity <= experiment_floor,
                updated_at=now,
            )
            try:
                created = self.journal.initialize_risk_state(state)
            except RiskStateConflict:
                raise DemoRoundTripDenied("RISK_BASELINE_CONFLICT") from None
            return RiskBaselineReceipt(
                created=created,
                bangkok_day=state.bangkok_day.isoformat(),
                daily_halt=state.daily_halt,
                total_halt=state.total_halt,
            )

    def startup(self) -> StartupReceipt:
        with self._lock:
            now = self._now()
            try:
                result = self.service.startup(
                    policy=self.settings.policy,
                    experiment_id=self.settings.experiment_id,
                    executor_id=self.settings.identity.executor_id,
                    now=now,
                )
            except RiskDenied as error:
                self._started = False
                raise DemoRoundTripDenied(error.reason) from None
            except Exception:
                self._started = False
                raise DemoRoundTripDenied("STARTUP_UNAVAILABLE", unavailable=True) from None
            self._started = True
            return StartupReceipt(**result)

    def _entry_binding(self, request: DemoRoundTripOpenRequest, now: datetime) -> None:
        settings = self.settings
        intent = request.intent
        if not settings.authorized_at_utc <= now <= settings.entry_authorization_expires_at_utc:
            raise DemoRoundTripDenied("ENTRY_AUTHORIZATION_EXPIRED")
        if (
            intent.command_id != settings.entry_command_id
            or intent.account_ref != settings.identity.account_ref
            or intent.experiment_id != settings.experiment_id
            or intent.signal_id != settings.signal_id
            or intent.strategy_version != settings.strategy_version
            or intent.symbol != settings.identity.symbol
            or request.account.account_ref != settings.identity.account_ref
            or request.account.server != settings.identity.server
            or request.account.currency != settings.identity.currency
            or request.account.margin_mode != settings.identity.margin_mode
            or request.contract.symbol != settings.identity.symbol
            or request.market.symbol != settings.identity.symbol
            or request.risk.reserved_loss != 0
            or request.risk.costs_per_lot < settings.minimum_costs_per_lot
        ):
            raise DemoRoundTripDenied("ENTRY_AUTHORIZATION_MISMATCH")

    def open(self, request: DemoRoundTripOpenRequest) -> SubmissionResult:
        with self._lock:
            now = self._now()
            self._entry_binding(request, now)
            try:
                return self.service.submit(
                    policy=self.settings.policy,
                    account=request.account,
                    contract=request.contract,
                    market=request.market,
                    intent=request.intent,
                    risk=request.risk,
                    now=now,
                )
            except RiskDenied as error:
                self._started = False
                raise DemoRoundTripDenied(error.reason) from None
            except (ExposureConflict, IdempotencyConflict, RiskStateConflict) as error:
                self._started = False
                raise DemoRoundTripDenied(type(error).__name__.upper()) from None
            except Exception:
                self._started = False
                raise DemoRoundTripDenied("ENTRY_UNAVAILABLE", unavailable=True) from None

    def _management_binding(
        self,
        request: DemoRoundTripManagementRequest,
        operation: ManagementOperation,
    ) -> None:
        expected = (
            self.settings.cancel_command_id
            if operation is ManagementOperation.CANCEL
            else self.settings.close_command_id
        )
        intent = request.intent
        if (
            intent.command_id != expected
            or intent.target_command_id != self.settings.entry_command_id
            or intent.account_ref != self.settings.identity.account_ref
            or intent.experiment_id != self.settings.experiment_id
            or intent.symbol != self.settings.identity.symbol
            or intent.operation is not operation
            or request.account.account_ref != self.settings.identity.account_ref
            or request.account.server != self.settings.identity.server
            or request.account.currency != self.settings.identity.currency
            or request.account.margin_mode != self.settings.identity.margin_mode
        ):
            raise DemoRoundTripDenied("MANAGEMENT_AUTHORIZATION_MISMATCH")

    def manage(
        self,
        request: DemoRoundTripManagementRequest,
        operation: ManagementOperation,
    ) -> SubmissionResult:
        with self._lock:
            self._management_binding(request, operation)
            try:
                return self.service.manage(
                    policy=self.settings.policy,
                    account=request.account,
                    intent=request.intent,
                    now=self._now(),
                )
            except RiskDenied as error:
                if error.reason not in {
                    "NO_PENDING_ORDER",
                    "PENDING_CANCEL_REQUIRED",
                    "NO_OPEN_POSITION",
                    "TARGET_COMMAND_NOT_FOUND",
                    "TARGET_BINDING_MISMATCH",
                    "TARGET_BROKER_EVIDENCE_MISSING",
                }:
                    self._started = False
                raise DemoRoundTripDenied(error.reason) from None
            except (IdempotencyConflict, ManagementConflict, RiskStateConflict) as error:
                self._started = False
                raise DemoRoundTripDenied(type(error).__name__.upper()) from None
            except Exception:
                self._started = False
                raise DemoRoundTripDenied("MANAGEMENT_UNAVAILABLE", unavailable=True) from None

    def reconcile(self, command_id: str) -> SubmissionResult:
        with self._lock:
            self._started = False
            try:
                if command_id == self.settings.entry_command_id:
                    return self.service.reconcile(command_id)
                if command_id in {
                    self.settings.cancel_command_id,
                    self.settings.close_command_id,
                }:
                    return self.service.reconcile_management(command_id)
                raise DemoRoundTripDenied("COMMAND_NOT_AUTHORIZED")
            except DemoRoundTripDenied:
                raise
            except KeyError:
                raise DemoRoundTripDenied("COMMAND_NOT_RECORDED") from None
            except Exception:
                raise DemoRoundTripDenied("RECONCILIATION_UNAVAILABLE", unavailable=True) from None


def disabled_demo_round_trip_status() -> DemoRoundTripStatus:
    return DemoRoundTripStatus(state="disabled", configured=False)
