"""Fail-closed Linux runtime probe, not a general SQLite vulnerability scanner."""

import hashlib
import json
import platform
import sqlite3
from pathlib import Path


def inspect_runtime():
    if sqlite3.sqlite_version_info < (3, 51, 3):
        raise RuntimeError("SQLite predates the admitted upstream WAL-reset fix")
    lock = json.loads(Path("/opt/sochron/sqlite.lock.json").read_text())
    manifest = json.loads(Path("/opt/sochron/sqlite-build.json").read_text())
    with sqlite3.connect(":memory:") as db:
        source_id = db.execute("select sqlite_source_id()").fetchone()[0]
        options = sorted(row[0] for row in db.execute("pragma compile_options"))
    paths = {
        line.split()[-1]
        for line in Path("/proc/self/maps").read_text().splitlines()
        if "/libsqlite3.so" in line
    }
    expected_path = "/usr/local/lib/libsqlite3.so.0"
    if (
        platform.python_version() != "3.14.7"
        or sqlite3.sqlite_version != lock["version"]
        or source_id != lock["source_id"]
        or manifest["lock"] != lock
        or paths != {expected_path}
        or "THREADSAFE=1" not in options
    ):
        raise RuntimeError("SQLite runtime identity mismatch")
    digest = hashlib.sha256(Path(expected_path).read_bytes()).hexdigest()
    if digest != manifest["library_sha256"]:
        raise RuntimeError("SQLite library checksum mismatch")
    return dict(
        version=sqlite3.sqlite_version,
        source_id=source_id,
        loaded_path=expected_path,
        library_sha256=digest,
        compiler=manifest["compiler"],
        compile_options=options,
        source_sha3_256=lock["source_sha3_256"],
    )


if __name__ == "__main__":
    print(json.dumps(inspect_runtime(), sort_keys=True))
