"""Private, WAL-aware snapshots and isolated copies; no execution authority."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import time
from contextlib import closing, suppress
from datetime import UTC, datetime
from pathlib import Path

MAX_BYTES = 256 * 1024 * 1024
DEADLINE_SECONDS = 30
MANIFEST_BYTES = 4096


class SnapshotUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("SQLITE_SNAPSHOT_UNAVAILABLE")


def _private(path: Path, *, directory=False):
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise SnapshotUnavailable()
    info = path.lstat()
    expected = 0o700 if directory else 0o600
    if (
        info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != expected
        or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        or (not directory and info.st_nlink != 1)
    ):
        raise SnapshotUnavailable()
    return info.st_dev, info.st_ino


def _source(path):
    parent = _private(path.parent, directory=True)
    identity = _private(path)
    for suffix in ("", "-wal", "-shm"):
        file = Path(str(path) + suffix)
        if file.exists() or file.is_symlink():
            _private(file)
            if file.stat().st_size > MAX_BYTES:
                raise SnapshotUnavailable()
    return parent, identity


def _hash(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _connect(path, mode):
    db = sqlite3.connect(
        path.as_uri() + "?mode=" + mode, uri=True, timeout=0.1, isolation_level=None
    )
    db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
    db.execute("PRAGMA trusted_schema=OFF")
    if mode == "ro":
        db.execute("PRAGMA query_only=ON")
    return db


def _schema(db):
    rows = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY name").fetchall()
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def _check(db):
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise SnapshotUnavailable()
    if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise SnapshotUnavailable()


def _sync(path, *, directory=False):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | (os.O_DIRECTORY if directory else 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _new_file(path, data=b""):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _invalidate(output, owned):
    # Only our newly created directory; never touch an existing operator target.
    with suppress(Exception):
        if owned and _private(output, directory=True) == owned[0]:
            _new_file(output / "INCOMPLETE")


def _create(source, output, owned):
    start = time.monotonic()
    started = datetime.now(UTC).isoformat()
    identity = _source(source)
    parent_identity = _private(output.parent, directory=True)
    if not output.is_absolute() or output.resolve() != output:
        raise SnapshotUnavailable()
    output.mkdir(mode=0o700)  # Never use exist_ok: no existing target can be replaced.
    output_identity = _private(output, directory=True)
    owned.append(output_identity)
    database = output / "snapshot.sqlite3"
    _new_file(database)
    target_identity = _private(database)

    def deadline():
        if time.monotonic() - start > DEADLINE_SECONDS:
            raise SnapshotUnavailable()

    def progress(status, remaining, total):
        deadline()
        if status not in (sqlite3.SQLITE_OK, sqlite3.SQLITE_DONE):
            raise SnapshotUnavailable()
        if total * page_size > MAX_BYTES or _source(source) != identity:
            raise SnapshotUnavailable()

    with closing(_connect(source, "ro")) as incoming, closing(_connect(database, "rw")) as target:
        incoming.execute("BEGIN")
        incoming.execute("SELECT count(*) FROM sqlite_schema").fetchone()  # Pin read snapshot.
        page_size = incoming.execute("PRAGMA page_size").fetchone()[0]
        if page_size * incoming.execute("PRAGMA page_count").fetchone()[0] > MAX_BYTES:
            raise SnapshotUnavailable()
        target.execute("PRAGMA synchronous=FULL")
        incoming.backup(target, pages=128, progress=progress, sleep=0.01)
        incoming.rollback()
        if target.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
            raise SnapshotUnavailable()
        target.set_progress_handler(lambda: int(time.monotonic() - start > DEADLINE_SECONDS), 1000)
        _check(target)
        schema_hash = _schema(target)
        target.set_progress_handler(None, 0)
    deadline()
    if (
        _source(source) != identity
        or _private(output.parent, directory=True) != parent_identity
        or _private(output, directory=True) != output_identity
        or _private(database) != target_identity
        or database.stat().st_size > MAX_BYTES
        or set(p.name for p in output.iterdir()) != {"snapshot.sqlite3"}
    ):
        raise SnapshotUnavailable()
    _sync(database)
    manifest = dict(
        format="sochron.sqlite-snapshot.v1",
        started_at=started,
        completed_at=datetime.now(UTC).isoformat(),
        duration_seconds=time.monotonic() - start,
        sqlite_version=sqlite3.sqlite_version,
        database_bytes=database.stat().st_size,
        database_sha256=_hash(database),
        schema_sha256=schema_hash,
        parent_database_sha256=None,
        execution_ready=False,
    )
    _metadata_values(manifest)
    deadline()
    _new_file(output / "manifest.json", json.dumps(manifest, sort_keys=True).encode())
    _sync(output, directory=True)
    _sync(output.parent, directory=True)
    deadline()
    return manifest


def create_snapshot(source: Path, output: Path) -> dict:
    """Create a new private snapshot; retain incomplete output if anything fails."""
    owned = []
    try:
        return _create(source, output, owned)
    except Exception:
        _invalidate(output, owned)
        raise SnapshotUnavailable() from None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotUnavailable()
        result[key] = value
    return result


def _metadata_values(manifest):
    for name in ("database_sha256", "schema_sha256", "parent_database_sha256"):
        value = manifest[name]
        if name == "parent_database_sha256" and value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise SnapshotUnavailable()
    times = []
    for name in ("started_at", "completed_at"):
        value = manifest[name]
        if not isinstance(value, str) or not value.endswith("+00:00"):
            raise SnapshotUnavailable()
        times.append(datetime.fromisoformat(value))
    duration = manifest["duration_seconds"]
    if (
        times[0] > times[1]
        or type(duration) not in (int, float)
        or not math.isfinite(duration)
        or not 0 <= duration <= DEADLINE_SECONDS
        or type(manifest["database_bytes"]) is not int
        or not 0 < manifest["database_bytes"] <= MAX_BYTES
        or not isinstance(manifest["sqlite_version"], str)
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", manifest["sqlite_version"])
    ):
        raise SnapshotUnavailable()


def verify_snapshot(directory: Path) -> dict:
    """Verify byte/schema integrity only, never application recovery readiness."""
    try:
        _private(directory, directory=True)
        if set(p.name for p in directory.iterdir()) != {"snapshot.sqlite3", "manifest.json"}:
            raise SnapshotUnavailable()
        metadata = directory / "manifest.json"
        _private(metadata)
        if metadata.stat().st_size > MANIFEST_BYTES:
            raise SnapshotUnavailable()
        manifest = json.loads(metadata.read_text(), object_pairs_hook=_unique)
        if (
            not isinstance(manifest, dict)
            or set(manifest)
            != {
                "format",
                "started_at",
                "completed_at",
                "duration_seconds",
                "sqlite_version",
                "database_bytes",
                "database_sha256",
                "schema_sha256",
                "parent_database_sha256",
                "execution_ready",
            }
            or manifest["format"] != "sochron.sqlite-snapshot.v1"
            or manifest["execution_ready"] is not False
        ):
            raise SnapshotUnavailable()
        _metadata_values(manifest)
        database = directory / "snapshot.sqlite3"
        identity = _source(database)
        if manifest["database_bytes"] != database.stat().st_size or manifest[
            "database_sha256"
        ] != _hash(database):
            raise SnapshotUnavailable()
        start = time.monotonic()
        with closing(_connect(database, "ro")) as db:
            db.set_progress_handler(lambda: int(time.monotonic() - start > DEADLINE_SECONDS), 1000)
            if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise SnapshotUnavailable()
            _check(db)
            if _schema(db) != manifest["schema_sha256"]:
                raise SnapshotUnavailable()
        if _source(database) != identity or manifest["database_sha256"] != _hash(database):
            raise SnapshotUnavailable()
        return manifest
    except Exception:
        raise SnapshotUnavailable() from None


def materialize_snapshot(snapshot: Path, output: Path) -> dict:
    """Make a new inspection copy; never replace state or start a service."""
    owned = []
    try:
        manifest = verify_snapshot(snapshot)
        if snapshot == output or snapshot in output.parents:
            raise SnapshotUnavailable()
        parent_identity = _private(output.parent, directory=True)
        if not output.is_absolute() or output.resolve() != output:
            raise SnapshotUnavailable()
        output.mkdir(mode=0o700)
        owned.append(_private(output, directory=True))
        database = output / "snapshot.sqlite3"
        start = time.monotonic()
        source = snapshot / "snapshot.sqlite3"
        descriptor = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with (
            os.fdopen(descriptor, "wb") as target,
            os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW), "rb") as incoming,
        ):
            copied = 0
            while block := incoming.read(1024 * 1024):
                copied += len(block)
                if copied > MAX_BYTES or time.monotonic() - start > DEADLINE_SECONDS:
                    raise SnapshotUnavailable()
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
        # Byte copying is safe only for the verified standalone DELETE-mode snapshot,
        # never for an active source database. Preserve the original recovery interval.
        if (
            _hash(database) != manifest["database_sha256"]
            or verify_snapshot(snapshot) != manifest
            or _private(output.parent, directory=True) != parent_identity
            or _private(output, directory=True) != owned[0]
        ):
            raise SnapshotUnavailable()
        result = {**manifest, "parent_database_sha256": manifest["database_sha256"]}
        _new_file(output / "manifest.json", json.dumps(result, sort_keys=True).encode())
        _sync(output, directory=True)
        _sync(output.parent, directory=True)
        verify_snapshot(output)
        return result
    except Exception:
        _invalidate(output, owned)
        raise SnapshotUnavailable() from None
