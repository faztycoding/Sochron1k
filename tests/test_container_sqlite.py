import hashlib
import io
import json
import runpy
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = runpy.run_path(str(ROOT / "scripts/build-container-sqlite.py"))


def fixture():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("release/sqlite3.c", b"synthetic-source")
        archive.writestr("../must-not-extract", b"never write this")
    payload = buffer.getvalue()
    lock = dict(
        archive_directory="release",
        archive_sha3_256=hashlib.sha3_256(payload).hexdigest(),
        source_sha3_256=hashlib.sha3_256(b"synthetic-source").hexdigest(),
    )
    return payload, lock


def test_verified_exact_member_only():
    payload, lock = fixture()
    assert BUILD["verified_source"](payload, lock) == b"synthetic-source"


@pytest.mark.parametrize("target", ["archive_sha3_256", "source_sha3_256"])
def test_checksum_mismatch_denied(target):
    payload, lock = fixture()
    lock[target] = "0" * 64
    with pytest.raises(ValueError, match="checksum mismatch"):
        BUILD["verified_source"](payload, lock)


def test_mutated_archive_denied_before_zip_parse():
    _, lock = fixture()
    with pytest.raises(ValueError, match="archive checksum"):
        BUILD["verified_source"](b"not even a zip", lock)


def test_both_images_share_exact_compiler_and_runtime_probe():
    lock = json.loads((ROOT / "services/runtime/sqlite.lock.json").read_text())
    for name in ("api", "worker"):
        source = (ROOT / f"services/{name}/Dockerfile").read_text()
        assert f"FROM {lock['compiler_image']} AS sqlite-builder" in source
        assert "COPY scripts/build-container-sqlite.py ./" in source
        assert "COPY scripts/check-container-sqlite.py /opt/sochron/check-sqlite.py" in source
        assert "RUN ldconfig && python /opt/sochron/check-sqlite.py" in source
        assert "ENV LD_LIBRARY_PATH=/usr/local/lib" in source
        assert (
            "COPY --from=sqlite-builder /out/libsqlite3.so.0 /usr/local/lib/libsqlite3.so.0"
            in source
        )


def test_old_runtime_denied_before_any_manifest_read(monkeypatch):
    import sqlite3

    probe = runpy.run_path(str(ROOT / "scripts/check-container-sqlite.py"))
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 40, 1))
    with pytest.raises(RuntimeError, match="predates"):
        probe["inspect_runtime"]()
