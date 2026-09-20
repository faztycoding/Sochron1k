"""Explicit private configuration for the disabled-by-default PA01 producer."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sochron1k.chart import ChartSettings
from sochron1k.telemetry import DemoIdentity

from .native_source import _json
from .sync_config import SyncConfigInvalid, canonical_path, origin, private_bytes


class PA01ConfigInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_CONFIG_INVALID")


@dataclass(frozen=True)
class PA01ProducerConfig:
    source_directory: Path
    state_directory: Path
    policy_file: Path
    archive_id: UUID
    identity: DemoIdentity
    offset_seconds: int
    chart: ChartSettings
    owner_id: UUID
    strategy_version_id: int
    experiment_id: int
    code_hash: str
    origin: str
    service_key_file: Path


def load_pa01_config() -> PA01ProducerConfig | None:
    configured = os.environ.get("SOCHRON_PA01_CONFIG_FILE")
    if not configured:
        return None
    try:
        config_path = canonical_path(configured)
        data = _json(private_bytes(config_path, 16_384).decode("utf-8"), 16_384)
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        fields = set(PA01ProducerConfig.__dataclass_fields__)
        if set(data) != fields | {"enabled"} or data.pop("enabled") is not True:
            raise PA01ConfigInvalid()
        for key in (
            "source_directory",
            "state_directory",
            "policy_file",
            "service_key_file",
        ):
            data[key] = canonical_path(data[key])
        if (
            data["source_directory"] == data["state_directory"]
            or data["policy_file"].parent == data["state_directory"]
            or data["policy_file"] == data["service_key_file"]
            or config_path in {data["policy_file"], data["service_key_file"]}
        ):
            raise PA01ConfigInvalid()
        for key in ("owner_id", "archive_id"):
            if not isinstance(data[key], str) or str(UUID(data[key])) != data[key]:
                raise PA01ConfigInvalid()
            data[key] = UUID(data[key])
        for key in ("strategy_version_id", "experiment_id"):
            if type(data[key]) is not int or data[key] <= 0 or data[key] > 9_007_199_254_740_991:
                raise PA01ConfigInvalid()
        offset = data["offset_seconds"]
        if type(offset) is not int or offset % 60 or not -50_400 <= offset <= 50_400:
            raise PA01ConfigInvalid()
        code_hash = data["code_hash"]
        if (
            not isinstance(code_hash, str)
            or len(code_hash) != 64
            or any(char not in "0123456789abcdef" for char in code_hash)
        ):
            raise PA01ConfigInvalid()
        data["identity"] = DemoIdentity.model_validate(data["identity"])
        data["chart"] = ChartSettings.model_validate(data["chart"])
        data["origin"] = origin(data["origin"])
        return PA01ProducerConfig(**data)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        SyncConfigInvalid,
        PA01ConfigInvalid,
    ):
        raise PA01ConfigInvalid() from None
