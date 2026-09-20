"""Read-only, single-process MT5 telemetry. Never an execution authority."""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    ConfigDict,
    Field,
    SecretStr,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from .models import ContractSpec, StrictModel

MAX_FRAME_BYTES = 16_384
MAX_AGE_SECONDS = 5.0
Identity = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$")]
MarginMode = Literal["retail_netting", "retail_hedging", "exchange"]
FiniteDecimal = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=24, decimal_places=10)]


class DemoIdentity(StrictModel):
    executor_id: Identity
    account_ref: Identity
    server: Identity
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3,8}$")]
    margin_mode: MarginMode
    symbol: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")]


class BridgeSettings(StrictModel):
    identity: DemoIdentity
    token: SecretStr
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)

    @field_validator("token")
    @classmethod
    def token_is_scoped_random_format(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not 43 <= len(raw) <= 128 or not all(
            char.isascii() and (char.isalnum() or char in "-_") for char in raw
        ):
            raise ValueError("use a separately generated URL-safe bridge credential")
        return value

    @field_validator("broker_utc_offset_seconds")
    @classmethod
    def offset_has_minute_precision(cls, value: int) -> int:
        if value % 60:
            raise ValueError("broker offset must have minute precision")
        return value


def load_bridge_settings() -> BridgeSettings | None:
    """Opt in with a private file; never emit its contents in startup errors."""
    configured_path = os.environ.get("SOCHRON_BRIDGE_CONFIG_FILE")
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
            raw = stream.read(MAX_FRAME_BYTES + 1)
        if len(raw) > MAX_FRAME_BYTES:
            raise ValueError("configuration too large")
        return BridgeSettings.model_validate_json(raw)
    except OSError, ValueError:
        raise RuntimeError("Invalid private bridge configuration; ingress not started") from None


class TelemetryContract(ContractSpec):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    digits: StrictInt = Field(ge=0, le=10)
    stops_level_points: StrictInt = Field(ge=0)
    freeze_level_points: StrictInt = Field(ge=0)
    filling_modes: tuple[Literal["fok", "ioc", "return", "boc"], ...] = Field(
        min_length=1, max_length=4
    )


class TelemetryFrame(StrictModel):
    protocol: Literal["sochron.telemetry.v1", "sochron.telemetry.v2"]
    source: Literal["mt5-ea-sampled"]
    boot_id: UUID
    sequence: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    identity: DemoIdentity
    trade_mode: Literal["demo"]
    terminal_build: StrictInt = Field(gt=0)
    terminal_connected: StrictBool
    account_trade_allowed: StrictBool
    observed_at: AwareDatetime
    tick_time_server_msc: StrictInt = Field(gt=0, le=4_102_444_800_000)
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)
    equity: FiniteDecimal
    balance: FiniteDecimal
    free_margin: FiniteDecimal
    bid: FiniteDecimal = Field(gt=0)
    ask: FiniteDecimal = Field(gt=0)
    market_open: StrictBool | None = None
    market_source: Literal["mt5-symbol-trade-session"] | None = None
    contract: TelemetryContract

    @field_validator("observed_at")
    @classmethod
    def normalize_observation(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @field_validator("ask")
    @classmethod
    def ordered_quote(cls, value: Decimal, info) -> Decimal:
        if value < info.data.get("bid", value):
            raise ValueError("invalid quote")
        return value

    @model_validator(mode="after")
    def market_evidence_matches_protocol(self):
        supplied = self.market_open is not None and self.market_source is not None
        if (self.protocol == "sochron.telemetry.v2") != supplied:
            raise ValueError("market evidence does not match telemetry protocol")
        if self.protocol == "sochron.telemetry.v1" and (
            self.market_open is not None or self.market_source is not None
        ):
            raise ValueError("telemetry v1 cannot carry market evidence")
        return self

    @property
    def event_time_utc(self) -> datetime:
        return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(
            milliseconds=self.tick_time_server_msc,
            seconds=-self.broker_utc_offset_seconds,
        )


class Observation(StrictModel):
    frame: TelemetryFrame
    event_time_utc: datetime
    received_time_utc: datetime


class BridgeStatus(StrictModel):
    state: Literal["disabled", "awaiting_snapshot", "connected", "stale", "rejected"]
    heartbeat_fresh: bool = False
    price_fresh: bool = False
    heartbeat_age_seconds: float | None = None
    price_age_seconds: float | None = None
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False


class TelemetryView(StrictModel):
    status: BridgeStatus
    observation: Observation | None


class FrameReceipt(StrictModel):
    accepted: Literal[True] = True
    duplicate: bool
    sequence: int


class BridgeDenied(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class TelemetryBridge:
    def __init__(
        self,
        settings: BridgeSettings | None,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.boot_id = uuid4()
        self._utc_now = utc_now
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._observation: Observation | None = None
        self._fingerprint: str | None = None
        self._received_monotonic = 0.0
        self._rejected = False

    def authenticate(self, credentials: list[str]) -> bool:
        if self.settings is None or len(credentials) != 1:
            return False
        supplied = credentials[0]
        if not supplied.isascii() or len(supplied) > 256:
            return False
        expected = "Bearer " + self.settings.token.get_secret_value()
        return secrets.compare_digest(supplied, expected)

    def reject(self) -> None:
        with self._lock:
            self._rejected = True

    def accept(self, frame: TelemetryFrame) -> FrameReceipt:
        fingerprint = hashlib.sha256(frame.model_dump_json().encode()).hexdigest()
        with self._lock:
            try:
                return self._accept_locked(frame, fingerprint)
            except BridgeDenied:
                self._rejected = True
                raise

    def _accept_locked(self, frame: TelemetryFrame, fingerprint: str) -> FrameReceipt:
        settings = self.settings
        if settings is None:
            raise BridgeDenied("BRIDGE_DISABLED")
        if frame.boot_id != self.boot_id:
            raise BridgeDenied("BOOT_MISMATCH")
        if frame.identity != settings.identity or frame.contract.symbol != settings.identity.symbol:
            raise BridgeDenied("IDENTITY_MISMATCH")
        if frame.broker_utc_offset_seconds != settings.broker_utc_offset_seconds:
            raise BridgeDenied("CLOCK_OFFSET_MISMATCH")

        previous = self._observation
        if previous is not None:
            old = previous.frame
            if frame.sequence == old.sequence:
                if fingerprint != self._fingerprint:
                    raise BridgeDenied("SEQUENCE_CONFLICT")
                # Neither receipt time nor a rejected state can be reset by replay.
                return FrameReceipt(duplicate=True, sequence=frame.sequence)
            if frame.sequence < old.sequence:
                raise BridgeDenied("OUT_OF_ORDER")
            if frame.observed_at < old.observed_at or frame.event_time_utc < old.event_time_utc:
                raise BridgeDenied("TIME_REVERSAL")

        now = self._utc_now()
        delay = (now - frame.observed_at).total_seconds()
        if delay < 0 or delay > MAX_AGE_SECONDS:
            raise BridgeDenied("OBSERVATION_CLOCK_INVALID")
        if frame.event_time_utc > frame.observed_at + timedelta(seconds=1):
            raise BridgeDenied("TICK_FROM_FUTURE")

        self._observation = Observation(
            frame=frame, event_time_utc=frame.event_time_utc, received_time_utc=now
        )
        self._fingerprint = fingerprint
        self._received_monotonic = self._monotonic()
        self._rejected = False
        return FrameReceipt(duplicate=False, sequence=frame.sequence)

    def observation(self) -> Observation | None:
        with self._lock:
            return self._observation

    def status(self) -> BridgeStatus:
        with self._lock:
            return self._status_locked()

    def view(self) -> TelemetryView:
        with self._lock:
            return TelemetryView(status=self._status_locked(), observation=self._observation)

    def _status_locked(self) -> BridgeStatus:
        if self.settings is None:
            return BridgeStatus(state="disabled")
        if self._rejected:
            return BridgeStatus(state="rejected")
        observation = self._observation
        if observation is None:
            return BridgeStatus(state="awaiting_snapshot")
        now = self._utc_now()
        elapsed = max(0.0, self._monotonic() - self._received_monotonic)
        received = observation.received_time_utc
        frame = observation.frame
        heartbeat_age = max(
            (now - frame.observed_at).total_seconds(),
            (received - frame.observed_at).total_seconds() + elapsed,
        )
        price_age = max(
            (now - observation.event_time_utc).total_seconds(),
            (received - observation.event_time_utc).total_seconds() + elapsed,
            0.0,
        )
        heartbeat_fresh = (
            frame.terminal_connected and now >= received and heartbeat_age <= MAX_AGE_SECONDS
        )
        price_fresh = heartbeat_fresh and price_age <= MAX_AGE_SECONDS
        return BridgeStatus(
            state="connected" if heartbeat_fresh and price_fresh else "stale",
            heartbeat_fresh=heartbeat_fresh,
            price_fresh=price_fresh,
            heartbeat_age_seconds=round(heartbeat_age, 3),
            price_age_seconds=round(price_age, 3),
        )
