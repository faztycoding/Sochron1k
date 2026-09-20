"""Read-only projection of the durable alert-delivery worker journal."""

from __future__ import annotations

import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import AwareDatetime, Field, StrictInt, field_validator, model_validator

from .models import StrictModel

MAX_STATUS_BYTES = 8192
DeliveryState = Literal[
    "disabled",
    "awaiting_worker",
    "connected",
    "pending",
    "unknown",
    "quarantined",
    "retry_exhausted",
    "stale",
    "degraded",
]
WorkerDeliveryState = Literal[
    "connected", "pending", "unknown", "quarantined", "retry_exhausted", "degraded"
]


def _directory_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_uid, stat.S_IMODE(value.st_mode)


class AlertDeliveryStatusSnapshot(StrictModel):
    protocol: Literal["sochron.alert-delivery-status.v1"]
    state: WorkerDeliveryState
    destination_ref: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    updated_at_utc: AwareDatetime
    heartbeat_expires_at_utc: AwareDatetime
    pending_deliveries: StrictInt = Field(ge=0, le=1)
    unknown_deliveries: StrictInt = Field(ge=0, le=1)
    verified_deliveries: StrictInt = Field(ge=0, le=1_000_000)
    quarantined_deliveries: StrictInt = Field(ge=0, le=1_000_000)
    last_delivery_ref: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    last_verified_at_utc: AwareDatetime | None = None

    @field_validator("updated_at_utc", "heartbeat_expires_at_utc", "last_verified_at_utc")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        lifetime = (self.heartbeat_expires_at_utc - self.updated_at_utc).total_seconds()
        if not 5 <= lifetime <= 3600:
            raise ValueError("invalid delivery heartbeat interval")
        if self.unknown_deliveries > self.pending_deliveries:
            raise ValueError("unknown delivery must be pending")
        if self.state == "connected" and self.pending_deliveries != 0:
            raise ValueError("connected delivery cannot be pending")
        if self.state == "pending" and (
            self.pending_deliveries != 1 or self.unknown_deliveries != 0
        ):
            raise ValueError("incoherent pending delivery")
        if self.state in {"unknown", "retry_exhausted"} and (
            self.pending_deliveries != 1 or self.unknown_deliveries != 1
        ):
            raise ValueError("incoherent unknown delivery")
        if self.state == "quarantined" and (
            self.pending_deliveries != 0
            or self.unknown_deliveries != 0
            or self.quarantined_deliveries == 0
        ):
            raise ValueError("incoherent quarantined delivery")
        verified = self.verified_deliveries > 0
        if verified != (
            self.last_delivery_ref is not None and self.last_verified_at_utc is not None
        ):
            raise ValueError("incoherent verified receipt")
        if (
            self.last_verified_at_utc is not None
            and self.last_verified_at_utc > self.updated_at_utc
        ):
            raise ValueError("verified receipt is from the future")
        return self


class AlertDeliveryView(StrictModel):
    protocol: Literal["sochron.alert-delivery-view.v1"] = "sochron.alert-delivery-view.v1"
    state: DeliveryState
    configured: bool
    destination_ref: str | None = None
    updated_at_utc: AwareDatetime | None = None
    pending_deliveries: StrictInt = Field(ge=0, le=1)
    unknown_deliveries: StrictInt = Field(ge=0, le=1)
    verified_deliveries: StrictInt = Field(ge=0, le=1_000_000)
    quarantined_deliveries: StrictInt = Field(ge=0, le=1_000_000)
    last_delivery_ref: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    last_verified_at_utc: AwareDatetime | None = None

    @field_validator("updated_at_utc", "last_verified_at_utc")
    @classmethod
    def utc_optional(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (self.state == "disabled") != (not self.configured):
            raise ValueError("incoherent delivery configuration")
        if self.state in {"disabled", "awaiting_worker"} and (
            self.destination_ref is not None
            or self.updated_at_utc is not None
            or any(
                (
                    self.pending_deliveries,
                    self.unknown_deliveries,
                    self.verified_deliveries,
                    self.quarantined_deliveries,
                    self.last_delivery_ref is not None,
                    self.last_verified_at_utc is not None,
                )
            )
        ):
            raise ValueError("delivery evidence before worker status")
        if (
            self.state == "degraded"
            and self.destination_ref is None
            and any(
                (
                    self.pending_deliveries,
                    self.unknown_deliveries,
                    self.verified_deliveries,
                    self.quarantined_deliveries,
                    self.last_delivery_ref is not None,
                    self.last_verified_at_utc is not None,
                )
            )
        ):
            raise ValueError("delivery evidence without trusted destination")
        if self.state not in {"disabled", "awaiting_worker", "degraded"} and (
            self.destination_ref is None or self.updated_at_utc is None
        ):
            raise ValueError("trusted delivery evidence required")
        if self.unknown_deliveries > self.pending_deliveries:
            raise ValueError("unknown delivery must be pending")
        if self.state == "connected" and self.pending_deliveries != 0:
            raise ValueError("connected delivery cannot be pending")
        if self.state == "pending" and (
            self.pending_deliveries != 1 or self.unknown_deliveries != 0
        ):
            raise ValueError("incoherent pending delivery")
        if self.state in {"unknown", "retry_exhausted"} and (
            self.pending_deliveries != 1 or self.unknown_deliveries != 1
        ):
            raise ValueError("incoherent unknown delivery")
        if self.state == "quarantined" and (
            self.pending_deliveries != 0
            or self.unknown_deliveries != 0
            or self.quarantined_deliveries == 0
        ):
            raise ValueError("incoherent quarantined delivery")
        verified = self.verified_deliveries > 0
        if verified != (
            self.last_delivery_ref is not None and self.last_verified_at_utc is not None
        ):
            raise ValueError("incoherent verified receipt")
        if (
            self.updated_at_utc is not None
            and self.last_verified_at_utc is not None
            and self.last_verified_at_utc > self.updated_at_utc
        ):
            raise ValueError("verified receipt is from the future")
        return self


def _empty(state: Literal["disabled", "awaiting_worker", "degraded"]) -> AlertDeliveryView:
    return AlertDeliveryView(
        state=state,
        configured=state != "disabled",
        pending_deliveries=0,
        unknown_deliveries=0,
        verified_deliveries=0,
        quarantined_deliveries=0,
    )


class AlertDeliveryStatusReader:
    def __init__(self, directory: Path | None) -> None:
        self.directory = directory
        self.path = directory / "delivery-status.json" if directory is not None else None
        self._directory_identity: tuple[int, int] | None = None
        if directory is not None:
            try:
                if not directory.is_absolute() or directory.resolve(strict=True) != directory:
                    raise ValueError("canonical delivery status directory required")
                metadata = directory.lstat()
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) & 0o077
                ):
                    raise ValueError("private delivery status directory required")
                self._directory_identity = _directory_identity(metadata)
            except OSError, ValueError:
                raise RuntimeError(
                    "Invalid private alert delivery status directory; API not started"
                ) from None

    def _read(self) -> AlertDeliveryStatusSnapshot | None:
        if self.directory is None or self.path is None:
            return None
        before_parent = self.directory.lstat()
        if (
            _directory_identity(before_parent) != self._directory_identity
            or not stat.S_ISDIR(before_parent.st_mode)
            or before_parent.st_uid != os.getuid()
            or stat.S_IMODE(before_parent.st_mode) & 0o077
        ):
            raise ValueError("delivery status directory changed")
        try:
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            with os.fdopen(os.open(self.path, flags), "rb") as stream:
                before = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(before.st_mode)
                    or before.st_uid != os.getuid()
                    or before.st_nlink != 1
                    or stat.S_IMODE(before.st_mode) & 0o077
                    or before.st_size > MAX_STATUS_BYTES
                ):
                    raise ValueError("untrusted delivery status")
                raw = stream.read(MAX_STATUS_BYTES + 1)
                after = os.fstat(stream.fileno())
            current = self.path.lstat()
        except FileNotFoundError:
            return None

        def identity(value):
            return (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )

        if (
            len(raw) > MAX_STATUS_BYTES
            or identity(before) != identity(after)
            or identity(after) != identity(current)
            or _directory_identity(self.directory.lstat()) != _directory_identity(before_parent)
        ):
            raise ValueError("unstable delivery status")
        return AlertDeliveryStatusSnapshot.model_validate_json(raw)

    def view(self, now: datetime | None = None) -> AlertDeliveryView:
        if self.directory is None:
            return _empty("disabled")
        try:
            snapshot = self._read()
            if snapshot is None:
                return _empty("awaiting_worker")
            current = (now or datetime.now(UTC)).astimezone(UTC)
            if current < snapshot.updated_at_utc:
                raise ValueError("delivery status is from the future")
            state: DeliveryState = (
                "stale" if current > snapshot.heartbeat_expires_at_utc else snapshot.state
            )
            return AlertDeliveryView(
                state=state,
                configured=True,
                destination_ref=snapshot.destination_ref,
                updated_at_utc=snapshot.updated_at_utc,
                pending_deliveries=snapshot.pending_deliveries,
                unknown_deliveries=snapshot.unknown_deliveries,
                verified_deliveries=snapshot.verified_deliveries,
                quarantined_deliveries=snapshot.quarantined_deliveries,
                last_delivery_ref=snapshot.last_delivery_ref,
                last_verified_at_utc=snapshot.last_verified_at_utc,
            )
        except OSError, ValueError, RuntimeError:
            return _empty("degraded")


def load_alert_delivery_status_reader() -> AlertDeliveryStatusReader:
    selected = os.environ.get("SOCHRON_ALERT_DELIVERY_STATUS_DIR")
    return AlertDeliveryStatusReader(Path(selected) if selected else None)
