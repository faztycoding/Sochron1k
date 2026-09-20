"""Private, explicit configuration for the alert-delivery worker."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from sochron1k.alert_delivery_source import AlertSourceSettings

from .native_source import _json
from .sync_config import canonical_path, origin, private_bytes


class AlertDeliveryConfigInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_DELIVERY_CONFIG_INVALID")


def _source_origin(value: object) -> str:
    try:
        return origin(value)
    except RuntimeError:
        pass
    if not isinstance(value, str) or len(value) > 253:
        raise AlertDeliveryConfigInvalid()
    matched = re.fullmatch(r"http://([a-z][a-z0-9-]{0,62}):([1-9][0-9]{1,4})", value)
    if matched and 1024 <= int(matched[2]) <= 65535:
        return value
    raise AlertDeliveryConfigInvalid()


def _private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
        if (
            not path.is_absolute()
            or path.resolve(strict=True) != path
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise AlertDeliveryConfigInvalid()
    except OSError, ValueError:
        raise AlertDeliveryConfigInvalid() from None


def _destination_token(path: Path) -> str:
    try:
        token = private_bytes(path, 256).decode("ascii").removesuffix("\n")
        if not 43 <= len(token) <= 128 or not all(
            character.isascii() and (character.isalnum() or character in "-_")
            for character in token
        ):
            raise AlertDeliveryConfigInvalid()
        return token
    except UnicodeError, RuntimeError:
        raise AlertDeliveryConfigInvalid() from None


@dataclass(frozen=True)
class AlertDeliveryConfig:
    source_origin: str
    destination_origin: str
    source_config_file: Path
    destination_token_file: Path
    state_directory: Path
    destination_ref: str
    poll_seconds: int
    max_sends: int

    def credentials(self) -> tuple[str, str]:
        try:
            source = AlertSourceSettings.model_validate_json(
                private_bytes(self.source_config_file, 4096)
            ).token.get_secret_value()
            destination = _destination_token(self.destination_token_file)
            if source == destination:
                raise AlertDeliveryConfigInvalid()
            return source, destination
        except ValueError, RuntimeError:
            raise AlertDeliveryConfigInvalid() from None


def load_alert_delivery_config() -> AlertDeliveryConfig | None:
    selected = os.environ.get("SOCHRON_ALERT_DELIVERY_CONFIG_FILE")
    if not selected:
        return None
    try:
        data = _json(private_bytes(canonical_path(selected), 16_384).decode("utf-8"), 16_384)
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        expected = {
            "enabled",
            "source_origin",
            "destination_origin",
            "source_config_file",
            "destination_token_file",
            "state_directory",
            "destination_ref",
            "poll_seconds",
            "max_sends",
        }
        if set(data) != expected or data.pop("enabled") is not True:
            raise AlertDeliveryConfigInvalid()
        source_origin = _source_origin(data.pop("source_origin"))
        destination_origin = origin(data.pop("destination_origin"))
        source_config_file = canonical_path(data.pop("source_config_file"))
        destination_token_file = canonical_path(data.pop("destination_token_file"))
        state_directory = canonical_path(data.pop("state_directory"))
        if len({source_config_file, destination_token_file, state_directory}) != 3:
            raise AlertDeliveryConfigInvalid()
        _private_directory(state_directory)
        destination_ref = data.pop("destination_ref")
        if not isinstance(destination_ref, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9_-]{0,63}", destination_ref
        ):
            raise AlertDeliveryConfigInvalid()
        poll_seconds = data.pop("poll_seconds")
        max_sends = data.pop("max_sends")
        if (
            type(poll_seconds) is not int
            or not 5 <= poll_seconds <= 300
            or type(max_sends) is not int
            or not 1 <= max_sends <= 5
            or data
        ):
            raise AlertDeliveryConfigInvalid()
        config = AlertDeliveryConfig(
            source_origin=source_origin,
            destination_origin=destination_origin,
            source_config_file=source_config_file,
            destination_token_file=destination_token_file,
            state_directory=state_directory,
            destination_ref=destination_ref,
            poll_seconds=poll_seconds,
            max_sends=max_sends,
        )
        config.credentials()
        return config
    except OSError, ValueError, TypeError, KeyError, RuntimeError, RecursionError:
        raise AlertDeliveryConfigInvalid() from None
