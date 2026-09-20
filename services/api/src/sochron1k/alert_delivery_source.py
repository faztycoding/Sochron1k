"""Private, redacted alert source for the separately authenticated delivery worker."""

from __future__ import annotations

import os
import secrets
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, Field, SecretStr, field_validator

from .models import StrictModel
from .operational_alerts import AlertKind, AlertSource, OperationalAlertInventory

MAX_SOURCE_CONFIG_BYTES = 4096


def _directory_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_uid, stat.S_IMODE(value.st_mode)


class AlertSourceSettings(StrictModel):
    protocol: Literal["sochron.alert-source-config.v1"]
    token: SecretStr

    @field_validator("token")
    @classmethod
    def scoped_token(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not 43 <= len(raw) <= 128 or not all(
            character.isascii() and (character.isalnum() or character in "-_") for character in raw
        ):
            raise ValueError("invalid alert source credential")
        return value


def load_alert_source_settings() -> AlertSourceSettings | None:
    selected = os.environ.get("SOCHRON_ALERT_SOURCE_CONFIG_FILE")
    if not selected:
        return None
    try:
        path = Path(selected)
        if not path.is_absolute() or path.resolve(strict=True) != path or str(path) != selected:
            raise ValueError("canonical source config required")
        parent_before = path.parent.stat()
        if (
            not stat.S_ISDIR(parent_before.st_mode)
            or parent_before.st_uid != os.getuid()
            or stat.S_IMODE(parent_before.st_mode) & 0o077
        ):
            raise ValueError("private source config directory required")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(path, flags), "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
                or before.st_size > MAX_SOURCE_CONFIG_BYTES
            ):
                raise ValueError("private source config required")
            raw = stream.read(MAX_SOURCE_CONFIG_BYTES + 1)
            after = os.fstat(stream.fileno())
        current = path.lstat()

        def identity(value):
            return (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )

        if (
            len(raw) > MAX_SOURCE_CONFIG_BYTES
            or identity(before) != identity(after)
            or identity(after) != identity(current)
            or _directory_identity(path.parent.stat()) != _directory_identity(parent_before)
        ):
            raise ValueError("unstable source config")
        return AlertSourceSettings.model_validate_json(raw)
    except OSError, ValueError, RuntimeError:
        raise RuntimeError("Invalid private alert source configuration; source disabled") from None


class AlertDeliveryFact(StrictModel):
    id: str = Field(pattern=r"^[0-9a-f]{24}$")
    condition_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    kind: AlertKind
    severity: Literal["critical", "warning", "info"]
    source: AlertSource
    source_ref: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    detail_code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    observed_at_utc: AwareDatetime
    evidence_routes: tuple[str, ...]

    @field_validator("observed_at_utc")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class AlertDeliverySourceSnapshot(StrictModel):
    protocol: Literal["sochron.alert-delivery-source.v1"] = "sochron.alert-delivery-source.v1"
    generated_at_utc: AwareDatetime
    truncated: bool
    alerts: tuple[AlertDeliveryFact, ...] = ()

    @field_validator("generated_at_utc")
    @classmethod
    def utc_generated(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


def delivery_source_snapshot(
    inventory: OperationalAlertInventory,
) -> AlertDeliverySourceSnapshot:
    facts = tuple(
        AlertDeliveryFact(
            id=alert.id,
            condition_id=alert.condition_id,
            kind=alert.kind,
            severity=alert.severity,
            source=alert.source,
            source_ref=alert.source_ref,
            detail_code=alert.detail_code,
            observed_at_utc=alert.observed_at_utc,
            evidence_routes=alert.evidence_routes,
        )
        for alert in inventory.alerts
    )
    return AlertDeliverySourceSnapshot(
        generated_at_utc=inventory.generated_at_utc,
        truncated=inventory.truncated,
        alerts=facts,
    )


class AlertSourceAuthenticator:
    def __init__(self, settings: AlertSourceSettings | None) -> None:
        self.settings = settings

    def authenticate(self, credentials: list[str]) -> bool:
        if self.settings is None or len(credentials) != 1:
            return False
        supplied = credentials[0]
        if not supplied.isascii() or len(supplied) > 256:
            return False
        expected = "Bearer " + self.settings.token.get_secret_value()
        return secrets.compare_digest(supplied, expected)
