"""Build only inside the pinned compiler stage; verify upstream bytes first."""

import hashlib
import io
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path


def verified_source(payload, lock):
    if hashlib.sha3_256(payload).hexdigest() != lock["archive_sha3_256"]:
        raise ValueError("SQLite archive checksum mismatch")
    # Read one exact member, never extract arbitrary paths from a downloaded archive.
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        source = archive.read(lock["archive_directory"] + "/sqlite3.c")
    if hashlib.sha3_256(source).hexdigest() != lock["source_sha3_256"]:
        raise ValueError("SQLite source checksum mismatch")
    return source


def main():
    lock = json.loads(Path("/build/sqlite.lock.json").read_text())
    with urllib.request.urlopen(lock["url"], timeout=30) as response:
        payload = response.read(4 * 1024 * 1024 + 1)
    source = verified_source(payload, lock)
    Path("/build/sqlite3.c").write_bytes(source)
    output = Path("/out")
    output.mkdir()
    command = [
        "gcc",
        "-O2",
        "-fPIC",
        "-shared",
        "-pthread",
        "-DSQLITE_THREADSAFE=1",
        "-DSQLITE_USE_URI=1",
        "-DSQLITE_ENABLE_COLUMN_METADATA",
        "-DSQLITE_ENABLE_FTS5",
        "-DSQLITE_ENABLE_RTREE",
        "-DSQLITE_ENABLE_MATH_FUNCTIONS",
        "-DSQLITE_ENABLE_DBSTAT_VTAB",
        "-Wl,-soname,libsqlite3.so.0",
        "/build/sqlite3.c",
        "-o",
        "/out/libsqlite3.so.0",
        "-lm",
        "-ldl",
    ]
    subprocess.run(command, check=True, timeout=300)
    manifest = dict(
        lock=lock,
        command=command,
        compiler=subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
        library_sha256=hashlib.sha256((output / "libsqlite3.so.0").read_bytes()).hexdigest(),
    )
    (output / "sqlite-build.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
