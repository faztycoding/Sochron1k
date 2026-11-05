"""Implementer's unit tests for sochron.app.envcheck (ENV-002 v1.8).

They cover what the locked acceptance tests leave to tests/unit/app (contract v1.6 Q2/Q3, v1.8):
the terminal path search of collect, the sentinel values file the CLI reads, the token search in
UTF-16 (v1.7 F6), the reparse-point rule (v1.7 F8) and that no message carries the token (v1.6 Q7,
v1.7 F7). Windows APIs are never called; every folder is under tmp_path.
"""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from sochron.app import envcheck as ec

TOKEN = "0123456789abcdef0123456789abcdef"


def touch(path: Path, content: bytes = b"MZ synthetic") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ---- find_terminal_paths (v1.6 Q2/Q3: levels 0-2 of Program Files*, 0-3 of the profile) ------------------
def test_terminal_paths_follow_the_levels_and_names(tmp_path):
    program_files = tmp_path / "Program Files"
    profile = tmp_path / "Users" / "owner"
    appdata = profile / "AppData" / "Roaming"
    expected = {
        program_files / "MetaTrader 5",  # a MetaTrader* folder
        program_files / "metatrader 4 portable",  # any case
        program_files / "terminal64.exe",  # level 0
        program_files / "Broker" / "MT5" / "TERMINAL64.EXE",  # level 2, any case
        profile / "Desktop" / "MT5" / "copy" / "terminal64.exe",  # level 3 of the profile
    }
    (program_files / "MetaTrader 5").mkdir(parents=True)
    (program_files / "metatrader 4 portable").mkdir(parents=True)
    for path in expected - {program_files / "MetaTrader 5", program_files / "metatrader 4 portable"}:
        touch(path)
    for path in (program_files / "a" / "b" / "c" / "terminal64.exe",  # level 3 of Program Files
                 profile / "a" / "b" / "c" / "d" / "terminal64.exe",  # level 4 of the profile
                 profile / ".venv" / "terminal64.exe", profile / "node_modules" / "x" / "terminal64.exe",
                 profile / ".git" / "terminal64.exe", appdata / "MetaQuotes" / "terminal64.exe"):
        touch(path)
    found = ec.find_terminal_paths((program_files, tmp_path / "Program Files (x86)"), profile, appdata)
    assert {Path(path) for path in found} == expected


def test_terminal_search_never_lists_metaquotes_and_skips_refused_folders(tmp_path, monkeypatch):
    profile = tmp_path / "Users" / "owner"
    appdata = profile / "AppData" / "Roaming"
    refused = profile / "AppData" / "Local" / "ElevatedDiagnostics"
    refused.mkdir(parents=True)
    touch(appdata / "MetaQuotes" / "Terminal" / "x.ini")
    touch(profile / "Desktop" / "terminal64.exe")
    real_scandir, listed = os.scandir, []

    def scandir(path):
        listed.append(ec._norm(path))
        if ec._norm(path) == ec._norm(refused):
            raise PermissionError(13, "denied", str(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    found = ec.find_terminal_paths((), profile, appdata)
    assert [Path(path) for path in found] == [profile / "Desktop" / "terminal64.exe"]  # v1.8: no UNKNOWN
    assert not any(path.startswith(ec._norm(appdata / "MetaQuotes")) for path in listed)


# ---- reparse points (v1.7 F8) -------------------------------------------------------------------------
class _Entry:
    def __init__(self, path: Path, *, junction=False, directory=False):
        self.path, self.name = str(path), path.name
        self._junction, self._directory = junction, directory

    def is_junction(self):
        return self._junction

    def is_symlink(self):
        return False

    def is_dir(self, follow_symlinks=True):
        return self._directory

    def is_file(self, follow_symlinks=True):
        return not self._directory

    def stat(self, follow_symlinks=True):
        return os.stat(self.path)


class _Listing(list):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_a_junction_is_not_entered(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    junction = repo / "My Music"
    touch(junction / "copy.txt", f"{TOKEN}\n".encode())
    real_scandir = os.scandir

    def scandir(path):
        if ec._norm(path) == ec._norm(repo):
            return _Listing([_Entry(junction, junction=True, directory=True)])
        if ec._norm(path) == ec._norm(junction):
            raise AssertionError("a junction was entered")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    roots = ec.ResearchRoots(repo=repo, data_dirs=(repo / "data",), program_files=(), appdata=tmp_path / "AppData",
                             user_profile=tmp_path, search_dirs=())
    sentinel = ec.Sentinel(name="SENTINEL-ENV002-01234567.json", size=10, sha256="0" * 64, token=TOKEN,
                           vault_path=str(tmp_path / "vault"), created_utc="2026-11-05T00:00:00Z")
    found = {item.name: item.status for item in ec.evaluate(_facts(), roots, sentinel).items}
    assert found["sentinel"] == ec.PASS


def _facts(**changes):
    values = {"terminal_paths": (), "uninstall_display_names": (), "process_names": (), "metaquotes_exists": False,
              "mt5_spec_found": False, "remote_drives": (), "connected_resources": ()}
    return ec.Facts(**{**values, **changes})


# ---- the token search (v1.7 F6) -------------------------------------------------------------------------
@pytest.mark.parametrize("encoding, bom", [("utf-8", b""), ("utf-16-le", b"\xff\xfe"), ("utf-16-be", b"\xfe\xff")])
def test_the_token_is_found_in_utf8_and_utf16(tmp_path, encoding, bom):
    path = touch(tmp_path / "note.txt", bom + f"pasted: {TOKEN}\r\n".encode(encoding))
    assert ec._read(path, ec._token_patterns(TOKEN), False) == (True, None)


def test_the_token_is_found_across_a_chunk_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "CHUNK", 7)
    path = touch(tmp_path / "note.txt", b"x" * 20 + TOKEN.encode("utf-16-le") + b"y" * 5)
    assert ec._read(path, ec._token_patterns(TOKEN), True)[0] is True


# ---- the sentinel values file the CLI reads -----------------------------------------------------------
GOOD = {"name": "SENTINEL-ENV002-01234567.json", "size": 5731, "sha256": "a" * 64, "token": TOKEN,
        "vault_path": "C:\\vault", "created_utc": "2026-11-05T09:30:00Z"}


@pytest.mark.parametrize("change", [
    {"extra": 1}, {"size": True}, {"size": "5731"}, {"size": 0}, {"token": TOKEN.upper()}, {"token": "x" * 32},
    {"sha256": "g" * 64}, {"name": None},
])
def test_a_wrong_sentinel_file_is_refused_without_echoing_the_token(tmp_path, monkeypatch, change):
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    path = touch(tmp_path / "values.json", json.dumps({**GOOD, **change}).encode())
    sentinel, note = ec.load_sentinel(path)
    assert sentinel is None and note and TOKEN not in note and TOKEN.upper() not in note


def test_a_good_sentinel_file_loads(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    sentinel, note = ec.load_sentinel(touch(tmp_path / "values.json", json.dumps(GOOD).encode()))
    assert note is None and sentinel == ec.Sentinel(**GOOD)


def test_a_cloud_only_or_broken_sentinel_file_is_not_used(tmp_path, monkeypatch):
    path = touch(tmp_path / "values.json", b"{not json")
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    assert ec.load_sentinel(path)[0] is None
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: True)
    sentinel, note = ec.load_sentinel(touch(tmp_path / "good.json", json.dumps(GOOD).encode()))
    assert sentinel is None and "cloud-only" in note


# ---- no message carries the token (v1.6 Q7, v1.7 F7) -----------------------------------------------------
def test_the_error_and_the_report_never_hold_the_token(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    touch(repo / "data" / "transfer" / f"{TOKEN}.txt", f"{TOKEN}\n".encode())  # even a file named after it
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    monkeypatch.setattr(ec, "collect", lambda roots: _facts())
    roots = ec.ResearchRoots(repo=repo, data_dirs=(repo / "data",), program_files=(), appdata=tmp_path / "AppData",
                             user_profile=tmp_path, search_dirs=())
    sentinel = ec.Sentinel(**{**GOOD, "vault_path": str(tmp_path / "vault")})
    report = ec.research_host_report(roots=roots, sentinel=sentinel)
    assert report.verdict == ec.FAIL and TOKEN not in ec.render(report)
    with pytest.raises(ec.ResearchHostError) as caught:
        ec.require_research_host(roots=roots, sentinel=sentinel)
    assert "sentinel FAIL" in str(caught.value) and TOKEN not in str(caught.value)


# ---- default_roots (v1.6 Q9) off Windows ------------------------------------------------------------------
def test_default_roots_off_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(ec.sys, "platform", "linux")
    for name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "OneDrive", "OneDriveConsumer",
                 "OneDriveCommercial"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "PF"))
    monkeypatch.setenv("ProgramW6432", str(tmp_path / "PF"))  # the same folder twice is listed once
    monkeypatch.setenv("OneDrive", str(tmp_path / "OneDrive"))
    roots = ec.default_roots((tmp_path / "usb",))
    repo = Path(ec.__file__).resolve().parents[3]
    assert roots.repo == repo and roots.data_dirs == (repo / "data", tmp_path / "usb")
    assert roots.program_files == (tmp_path / "PF",) and roots.appdata == tmp_path / "AppData" / "Roaming"
    assert roots.search_dirs == (tmp_path / "Downloads", tmp_path / "Desktop", tmp_path / "Documents",
                                 tmp_path / "OneDrive")


def test_is_cloud_only_tolerates_a_stat_without_attributes(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "stat", lambda path: SimpleNamespace(st_size=1))
    assert ec.is_cloud_only(tmp_path / "x.json") is False
