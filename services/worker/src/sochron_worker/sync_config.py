"""Explicit private worker configuration. No network and no environment secrets."""

from __future__ import annotations

import base64
import binascii
import os
import re
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sochron1k.chart import ChartSettings
from sochron1k.telemetry import DemoIdentity

from .native_source import _json


class SyncConfigInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("SYNC_CONFIG_INVALID")


def private_bytes(path: Path, limit: int) -> bytes:
    """Read one stable owner-only regular file; fail closed on replacement."""
    try:
        if not path.is_absolute() or path.resolve() != path:
            raise SyncConfigInvalid()
        parent = path.parent.stat()
        if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077:
            raise SyncConfigInvalid()
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        with os.fdopen(os.open(path, flags), "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
                or before.st_size > limit
            ):
                raise SyncConfigInvalid()
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        current = path.lstat()

        def fingerprint(s):
            return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

        if (
            len(data) > limit
            or fingerprint(before) != fingerprint(after)
            or fingerprint(after) != fingerprint(current)
            or path.parent.stat() != parent
        ):
            raise SyncConfigInvalid()
        return data
    except OSError, ValueError, TypeError:
        raise SyncConfigInvalid() from None


def origin(value: object) -> str:
    if not isinstance(value, str) or len(value) > 253:
        raise SyncConfigInvalid()
    local = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{3,4})", value)
    if local and 1024 <= int(local[1]) <= 65535:
        return value
    remote = re.fullmatch(r"https://([a-z0-9.-]+)", value)
    if remote:
        labels = remote[1].split(".")
        if (
            len(labels) >= 2
            and re.fullmatch(r"[a-z]{2,63}", labels[-1])
            and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p) for p in labels)
        ):
            return value
    raise SyncConfigInvalid()


def canonical_path(value: object) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise SyncConfigInvalid()
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path or str(path) != value:
        raise SyncConfigInvalid()
    return path


@dataclass(frozen=True)
class SyncConfig:
    source_directory: Path
    state_directory: Path
    archive_id: UUID
    identity: DemoIdentity
    offset_seconds: int
    chart: ChartSettings
    owner_id: UUID
    origin: str
    service_key_file: Path


def load_config() -> SyncConfig | None:
    path = os.environ.get("SOCHRON_SYNC_CONFIG_FILE")
    if not path:
        return None
    try:
        data = _json(private_bytes(canonical_path(path), 16384).decode("utf-8"), 16384)
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        fields = set(SyncConfig.__dataclass_fields__)
        if set(data) != fields | {"enabled"} or data.pop("enabled") is not True:
            raise SyncConfigInvalid()
        for key in ("source_directory", "state_directory", "service_key_file"):
            data[key] = canonical_path(data[key])
        if data["source_directory"] == data["state_directory"]:
            raise SyncConfigInvalid()
        for key in ("owner_id", "archive_id"):
            if not isinstance(data[key], str) or str(UUID(data[key])) != data[key]:
                raise SyncConfigInvalid()
            data[key] = UUID(data[key])
        offset = data["offset_seconds"]
        if type(offset) is not int or offset % 60 or not -50400 <= offset <= 50400:
            raise SyncConfigInvalid()
        data["identity"] = DemoIdentity.model_validate(data["identity"])
        data["chart"] = ChartSettings.model_validate(data["chart"])
        data["origin"] = origin(data["origin"])
        return SyncConfig(**data)
    except OSError, ValueError, TypeError, KeyError, RecursionError:
        raise SyncConfigInvalid() from None


def read_service_key(path: Path) -> tuple[str, bool]:
    """Return key and legacy flag. Remote service, never decoded claims, authenticates."""
    try:
        raw = private_bytes(path, 8192).decode("ascii").removesuffix("\n")
        if re.fullmatch(r"sb_secret_[A-Za-z0-9_-]{16,256}", raw):
            return raw, False
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", raw):
            raise SyncConfigInvalid()
        header, payload, _ = raw.split(".")

        def decode(part):
            return _json(
                base64.b64decode(
                    part + "=" * (-len(part) % 4), altchars=b"-_", validate=True
                ).decode("utf-8"),
                8192,
            )

        claims = decode(payload)
        if (
            decode(header).get("alg") != "HS256"
            or claims.get("role") != "service_role"
            or type(claims.get("exp")) is not int
            or claims["exp"] <= time.time()
        ):
            raise SyncConfigInvalid()
        return raw, True
    except OSError, ValueError, TypeError, binascii.Error, RecursionError:
        raise SyncConfigInvalid() from None
