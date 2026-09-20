"""Private, default-off configuration for one research-evaluation publication."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from .native_source import _json
from .sync_config import SyncConfigInvalid, canonical_path, origin, private_bytes


class ResearchEvaluationConfigInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("RESEARCH_EVALUATION_CONFIG_INVALID")


@dataclass(frozen=True)
class ResearchEvaluationConfig:
    input_file: Path
    state_directory: Path
    owner_id: UUID
    strategy_version_id: int
    experiment_id: int | None
    origin: str
    service_key_file: Path


def load_research_evaluation_config() -> ResearchEvaluationConfig | None:
    configured = os.environ.get("SOCHRON_RESEARCH_EVALUATION_CONFIG_FILE")
    if not configured:
        return None
    try:
        config_path = canonical_path(configured)
        data = _json(private_bytes(config_path, 16_384).decode("utf-8"), 16_384)
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        fields = set(ResearchEvaluationConfig.__dataclass_fields__)
        if set(data) != fields | {"enabled"} or data.pop("enabled") is not True:
            raise ResearchEvaluationConfigInvalid()
        for key in ("input_file", "state_directory", "service_key_file"):
            data[key] = canonical_path(data[key])
        if (
            data["input_file"] == data["service_key_file"]
            or data["input_file"].parent == data["state_directory"]
            or data["service_key_file"].parent == data["state_directory"]
            or config_path in {data["input_file"], data["service_key_file"]}
        ):
            raise ResearchEvaluationConfigInvalid()
        if not isinstance(data["owner_id"], str) or str(UUID(data["owner_id"])) != data["owner_id"]:
            raise ResearchEvaluationConfigInvalid()
        data["owner_id"] = UUID(data["owner_id"])
        if (
            type(data["strategy_version_id"]) is not int
            or not 1 <= data["strategy_version_id"] <= 9_007_199_254_740_991
        ):
            raise ResearchEvaluationConfigInvalid()
        experiment = data["experiment_id"]
        if experiment is not None and (
            type(experiment) is not int or not 1 <= experiment <= 9_007_199_254_740_991
        ):
            raise ResearchEvaluationConfigInvalid()
        data["origin"] = origin(data["origin"])
        return ResearchEvaluationConfig(**data)
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        SyncConfigInvalid,
        ResearchEvaluationConfigInvalid,
    ):
        raise ResearchEvaluationConfigInvalid() from None
