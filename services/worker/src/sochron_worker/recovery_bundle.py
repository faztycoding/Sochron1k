"""Private local recovery bundles; creation and inspection never activate state."""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

import sochron1k
from pydantic import Field, StrictInt, field_validator, model_validator
from sochron1k.models import StrictModel
from sochron1k.sqlite_snapshot import (
    _invalidate,
    _new_file,
    _private,
    _sync,
    create_snapshot,
    materialize_snapshot,
    verify_snapshot,
)

import sochron_worker

from .native_source import _json
from .recovery_audit import RecoveryBinding, audit_recovery_set
from .sync_config import private_bytes
from .sync_journal import canonical, utc

ROLES = ("commands", "sync", "archive")
MAX_SECONDS = 180
MAX_MANIFEST_BYTES = 65536
DEPENDENCIES = ("fastapi", "httpx", "pydantic", "pydantic-core", "uvicorn")
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class BundleUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("RECOVERY_BUNDLE_UNAVAILABLE")


def require(condition):
    if not condition:
        raise BundleUnavailable()


class ProvenanceClaims(StrictModel):
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    artifact_sha256: Hash


class RecoveryConfig(StrictModel):
    binding: RecoveryBinding
    command_database: str
    sync_database: str
    archive_database: str
    max_age_seconds: StrictInt = Field(ge=1, le=86400)
    max_span_seconds: StrictInt = Field(ge=1, le=86400)
    operator_provenance_claims: ProvenanceClaims

    @field_validator("command_database", "sync_database", "archive_database")
    @classmethod
    def original_path(cls, value):
        # Old-machine paths must be valid identities but need not exist during restore.
        return RecoveryBinding.original_path(value)

    @model_validator(mode="after")
    def relationships(self):
        require(self.max_span_seconds <= self.max_age_seconds)
        paths = (self.command_database, self.sync_database, self.archive_database)
        require(len(set(paths)) == 3)
        require(
            self.archive_database
            == str(PurePosixPath(self.binding.source_directory) / "bars.sqlite3")
        )
        return self

    @property
    def sources(self):
        return dict(
            zip(
                ROLES,
                map(Path, (self.command_database, self.sync_database, self.archive_database)),
                strict=True,
            )
        )


class BundleManifest(StrictModel):
    format: Literal["sochron.recovery-bundle.v1"]
    kind: Literal["backup", "inspection"]
    execution_ready: Literal[False]
    started_at: str
    completed_at: str
    duration_seconds: float = Field(strict=True, ge=0, le=MAX_SECONDS, allow_inf_nan=False)
    capture_start: str
    capture_end: str
    config_sha256: Hash
    parent_bundle_sha256: Hash | None
    operator_provenance_claims: ProvenanceClaims
    producer: dict
    member_manifest_sha256: dict[str, Hash]
    evidence: dict


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _config(path):
    _private(path.parent, directory=True)
    _private(path)
    raw = private_bytes(path, 16384)
    return RecoveryConfig.model_validate(_json(raw.decode(), 16384)), digest(raw)


def _producer():
    modules = {}
    for package in (sochron1k, sochron_worker):
        directory = Path(package.__file__).parent
        for path in sorted(directory.glob("*.py")):
            modules[package.__name__ + "/" + path.name] = digest(path.read_bytes())
    require(
        {
            "sochron1k/sqlite_snapshot.py",
            "sochron_worker/recovery_audit.py",
            "sochron_worker/recovery_bundle.py",
            "sochron_worker/recovery_cli.py",
        }
        <= set(modules)
    )
    with closing(sqlite3.connect(":memory:")) as db:
        source_id = db.execute("SELECT sqlite_source_id()").fetchone()[0]
    return dict(
        modules=modules,
        python=platform.python_version(),
        sqlite=sqlite3.sqlite_version,
        sqlite_source_id=source_id,
        dependencies={name: importlib.metadata.version(name) for name in DEPENDENCIES},
    )


def _producer_valid(producer):
    current = _producer()
    require(set(producer) == set(current) and producer["modules"] == current["modules"])
    for name in ("python", "sqlite", "sqlite_source_id"):
        require(isinstance(producer[name], str) and 0 < len(producer[name]) <= 128)
    dependencies = producer["dependencies"]
    require(
        isinstance(dependencies, dict)
        and set(dependencies) == set(DEPENDENCIES)
        and all(isinstance(value, str) and 0 < len(value) <= 64 for value in dependencies.values())
    )
    # Runtime identity is recorded, not an implicit authorization for a different host/runtime.


def _evidence(audit):
    return {
        key: value for key, value in audit.items() if key not in {"audited_at", "duration_seconds"}
    }


def _audit(directory, config):
    return audit_recovery_set(
        **{role: directory / role for role in ROLES},
        binding=config.binding,
        now=datetime.now(UTC),
        max_age_seconds=config.max_age_seconds,
        max_span_seconds=config.max_span_seconds,
    )


def _members(directory):
    return {role: digest(private_bytes(directory / role / "manifest.json", 4096)) for role in ROLES}


def _new_directory(output, owned):
    parent = _private(output.parent, directory=True)
    require(output.is_absolute() and output.resolve() == output)
    output.mkdir(mode=0o700)
    owned.append(_private(output, directory=True))
    return parent


def _check_time(start):
    require(time.monotonic() - start <= MAX_SECONDS)


def _read_bundle(directory, config, config_hash):
    identity = _private(directory, directory=True)
    require({p.name for p in directory.iterdir()} == set(ROLES) | {"bundle.json"})
    path = directory / "bundle.json"
    _private(path)
    raw = private_bytes(path, MAX_MANIFEST_BYTES)
    data = _json(raw.decode(), MAX_MANIFEST_BYTES)
    require(data.get("execution_ready") is False)
    manifest = BundleManifest.model_validate(data)
    now = datetime.now(UTC)
    require(
        utc(manifest.started_at) <= utc(manifest.completed_at) <= now
        and utc(manifest.capture_start) <= utc(manifest.capture_end) <= utc(manifest.completed_at)
        and manifest.config_sha256 == config_hash
        and manifest.operator_provenance_claims == config.operator_provenance_claims
        and set(manifest.member_manifest_sha256) == set(ROLES)
    )
    require(
        (
            manifest.kind == "backup"
            and manifest.parent_bundle_sha256 is None
            and utc(manifest.started_at) <= utc(manifest.capture_start)
        )
        or (
            manifest.kind == "inspection"
            and manifest.parent_bundle_sha256 is not None
            and utc(manifest.capture_end) <= utc(manifest.started_at)
        )
    )
    _producer_valid(manifest.producer)
    require(_members(directory) == manifest.member_manifest_sha256)
    audit = _audit(directory, config)
    require(_evidence(audit) == manifest.evidence)
    snapshots = {role: verify_snapshot(directory / role) for role in ROLES}
    for item in snapshots.values():
        require(
            item["parent_database_sha256"]
            == (item["database_sha256"] if manifest.kind == "inspection" else None)
        )
    require(
        manifest.capture_start == snapshots["commands"]["started_at"]
        and manifest.capture_end == snapshots["archive"]["completed_at"]
    )
    require(
        _members(directory) == manifest.member_manifest_sha256
        and private_bytes(path, MAX_MANIFEST_BYTES) == raw
        and _private(directory, directory=True) == identity
        and {p.name for p in directory.iterdir()} == set(ROLES) | {"bundle.json"}
    )
    return dict(manifest=manifest.model_dump(mode="json"), audit=audit, bundle_sha256=digest(raw))


def verify_bundle(config_path: Path, directory: Path) -> dict:
    try:
        start = time.monotonic()
        config, config_hash = _config(config_path)
        result = _read_bundle(directory, config, config_hash)
        require(_config(config_path)[1] == config_hash)
        _check_time(start)
        return result
    except Exception:
        raise BundleUnavailable() from None


def _publish(output, manifest, parent_identity, owned, start):
    require(
        _private(output.parent, directory=True) == parent_identity
        and _private(output, directory=True) == owned[0]
        and {p.name for p in output.iterdir()} == set(ROLES)
    )
    require(utc(manifest["started_at"]) <= utc(manifest["completed_at"]))
    raw = canonical(BundleManifest.model_validate(manifest).model_dump(mode="json")).encode()
    require(len(raw) <= MAX_MANIFEST_BYTES)
    _check_time(start)
    _new_file(output / "bundle.json", raw)
    _sync(output, directory=True)
    _sync(output.parent, directory=True)
    _check_time(start)


def _create(config_path, output, source_bundle):
    owned = []
    try:
        start, started = time.monotonic(), datetime.now(UTC).isoformat()
        config, config_hash = _config(config_path)
        producer = _producer()
        parent = None
        if source_bundle is not None:
            require(output != source_bundle and source_bundle not in output.parents)
            parent = _read_bundle(source_bundle, config, config_hash)
            _check_time(start)
        parent_identity = _new_directory(output, owned)
        for role in ROLES:
            if source_bundle is None:
                create_snapshot(config.sources[role], output / role)
            else:
                materialize_snapshot(source_bundle / role, output / role)
            _check_time(start)
        audit = _audit(output, config)
        if parent is not None:
            require(
                _evidence(audit) == parent["manifest"]["evidence"]
                and _read_bundle(source_bundle, config, config_hash)["bundle_sha256"]
                == parent["bundle_sha256"]
            )
        snapshots = {role: verify_snapshot(output / role) for role in ROLES}
        require(_config(config_path)[1] == config_hash and _producer() == producer)
        manifest = dict(
            format="sochron.recovery-bundle.v1",
            kind="backup" if parent is None else "inspection",
            execution_ready=False,
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
            duration_seconds=time.monotonic() - start,
            capture_start=snapshots["commands"]["started_at"],
            capture_end=snapshots["archive"]["completed_at"],
            config_sha256=config_hash,
            parent_bundle_sha256=parent["bundle_sha256"] if parent else None,
            operator_provenance_claims=config.operator_provenance_claims.model_dump(),
            producer=producer,
            member_manifest_sha256=_members(output),
            evidence=_evidence(audit),
        )
        _publish(output, manifest, parent_identity, owned, start)
        result = _read_bundle(output, config, config_hash)
        require(_config(config_path)[1] == config_hash)
        _check_time(start)
        return result
    except BaseException as error:
        _invalidate(output, owned)
        if not isinstance(error, Exception):
            raise
        raise BundleUnavailable() from None


def backup_bundle(config_path: Path, output: Path) -> dict:
    return _create(config_path, output, None)


def restore_bundle(config_path: Path, source_bundle: Path, output: Path) -> dict:
    """Produce an inspection bundle only, never activate or rebind application state."""
    return _create(config_path, output, source_bundle)
