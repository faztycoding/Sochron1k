"""Private configuration for the disabled-by-default calendar News Gate collector."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sochron1k.policy_evidence import _directory_identity, _validate_existing_output

from .native_source import _json
from .sync_config import SyncConfigInvalid, canonical_path, origin, private_bytes

Impact = Literal["low", "medium", "high"]
IMPACTS = frozenset(("low", "medium", "high"))


class NewsGateConfigInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("NEWS_GATE_CONFIG_INVALID")


@dataclass(frozen=True)
class NewsGateConfig:
    origin: str
    credential_file: Path
    output_file: Path
    currencies: tuple[str, ...]
    impacts: tuple[Impact, ...]
    blackout_before_seconds: int
    blackout_after_seconds: int
    poll_seconds: int


def _members(value: object, *, impacts: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or len(value) > 16:
        raise NewsGateConfigInvalid()
    if any(not isinstance(item, str) for item in value) or len(set(value)) != len(value):
        raise NewsGateConfigInvalid()
    if impacts:
        if any(item not in IMPACTS for item in value):
            raise NewsGateConfigInvalid()
    elif any(re.fullmatch(r"[A-Z]{3}", item) is None for item in value):
        raise NewsGateConfigInvalid()
    return tuple(sorted(value))


def load_news_gate_config() -> NewsGateConfig | None:
    configured = os.environ.get("SOCHRON_NEWS_GATE_CONFIG_FILE")
    if not configured:
        return None
    try:
        config_path = canonical_path(configured)
        data = _json(private_bytes(config_path, 16_384).decode("utf-8"), 16_384)
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        fields = set(NewsGateConfig.__dataclass_fields__)
        if set(data) != fields | {"enabled"} or data.pop("enabled", None) is not True:
            raise NewsGateConfigInvalid()
        data["origin"] = origin(data["origin"])
        if not data["origin"].startswith("https://"):
            raise NewsGateConfigInvalid()
        for key in ("credential_file", "output_file"):
            data[key] = canonical_path(data[key])
        if len({config_path, data["credential_file"], data["output_file"]}) != 3:
            raise NewsGateConfigInvalid()
        data["currencies"] = _members(data["currencies"])
        data["impacts"] = _members(data["impacts"], impacts=True)
        for key in ("blackout_before_seconds", "blackout_after_seconds"):
            value = data[key]
            if type(value) is not int or not 60 <= value <= 7_200:
                raise NewsGateConfigInvalid()
        if type(data["poll_seconds"]) is not int or not 30 <= data["poll_seconds"] <= 300:
            raise NewsGateConfigInvalid()
        _directory_identity(data["credential_file"].parent)
        _directory_identity(data["output_file"].parent)
        _validate_existing_output(data["output_file"])
        return NewsGateConfig(**data)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        RuntimeError,
        SyncConfigInvalid,
        NewsGateConfigInvalid,
    ):
        raise NewsGateConfigInvalid() from None


def read_calendar_token(path: Path) -> str:
    try:
        value = private_bytes(path, 512).decode("ascii")
        if re.fullmatch(r"[A-Za-z0-9._~-]{32,256}", value) is None:
            raise NewsGateConfigInvalid()
        return value
    except (OSError, UnicodeError, ValueError, TypeError, SyncConfigInvalid):
        raise NewsGateConfigInvalid() from None
