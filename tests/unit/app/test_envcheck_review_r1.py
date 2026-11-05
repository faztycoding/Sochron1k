"""Implementer's regression tests for implementation review r1 of ENV-002 (docs/reviews/ENV-002-r1.md).

One group per finding (F1-F10), against contract v1.9. Every folder is under tmp_path; Windows APIs
are replaced by fakes. The acceptance helpers in tests/acceptance/ENV-002/envkit.py are loaded by path
for their audit recording, as the acceptance tests load them.
"""

import ctypes
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from sochron.app import envcheck as ec

REPO_ROOT = Path(__file__).resolve().parents[3]
TOKEN = "0123456789abcdef0123456789abcdef"
SENTINEL_BYTES = (json.dumps({"synthetic": True, "purpose": "ENV-002 sentinel", "token": TOKEN}) + "\n").encode()
LATE, EARLY = "2025-06-30T00:00:00Z", "2024-07-01T00:00:00Z"


def _kit():
    name, path = "envkit_env002", REPO_ROOT / "tests" / "acceptance" / "ENV-002" / "envkit.py"
    module = sys.modules.get(name)
    if module is None or getattr(module, "__file__", None) != str(path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


K = _kit()


def touch(path: Path, content=b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    return path


def manifest(folder: Path, end: str, names=("bars.parquet",), file_name="manifest.json") -> Path:
    files = [{"name": name, "sha256": "0" * 64} for name in names]
    return touch(folder / file_name, json.dumps({"files": files, "period_end_utc": end}))


def snapshot(folder: Path, end: str, *, per_file=None) -> Path:
    data = touch(folder / "bars.parquet", b"PAR1")
    manifest(folder, end)
    if per_file is not None:
        manifest(folder, per_file, file_name="bars.parquet.manifest.json")
    return data


def sentinel(tmp_path: Path, **changes):
    values = {"name": f"SENTINEL-ENV002-{TOKEN[:8]}.json", "size": len(SENTINEL_BYTES),
              "sha256": hashlib.sha256(SENTINEL_BYTES).hexdigest(), "token": TOKEN,
              "vault_path": str(tmp_path / "vps" / "vault"), "created_utc": "2026-11-05T00:00:00Z"}
    return ec.Sentinel(**{**values, **changes})


FACTS = ec.Facts(terminal_paths=(), uninstall_display_names=(), process_names=("explorer.exe",),
                 metaquotes_exists=False, mt5_spec_found=False, remote_drives=(), connected_resources=())


def roots(tmp_path, repo, data_dirs=None, search_dirs=(), appdata=None):
    return ec.ResearchRoots(repo=repo, data_dirs=tuple((repo / "data",) if data_dirs is None else data_dirs),
                            program_files=(), appdata=appdata or tmp_path / "AppData" / "Roaming",
                            user_profile=tmp_path, search_dirs=tuple(search_dirs))


def judge(monkeypatch, research_roots, sentinel_value, cloud=()):
    wanted = {ec._norm(path) for path in cloud}
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: ec._norm(path) in wanted)
    report = ec.evaluate(FACTS, research_roots, sentinel_value)
    return {item.name: item.status for item in report.items}, report


# ---- F1: a data dir that contains the repository keeps the data rules ------------------------------------------
@pytest.mark.parametrize("case", ["parent", "repo itself", "desktop"])
def test_f1_a_data_dir_around_the_repo_keeps_the_manifest_rules(tmp_path, monkeypatch, case):
    base = tmp_path / ("Desktop" if case == "desktop" else "work")
    repo = base / "Sochron1k"
    snapshot(repo / "data" / "transfer", LATE)
    outer = repo if case == "repo itself" else base
    search = (base,) if case == "desktop" else ()
    found, _ = judge(monkeypatch, roots(tmp_path, repo, (repo / "data", outer), search), sentinel(tmp_path))
    assert found["excluded_period"] == ec.FAIL


def test_f1_repo_files_under_a_data_dir_follow_the_data_rules(tmp_path, monkeypatch):
    repo = tmp_path / "work" / "Sochron1k"
    touch(repo / "research" / "out.parquet", b"PAR1")  # under the repo, outside <repo>/data
    found, _ = judge(monkeypatch, roots(tmp_path, repo, (repo / "data", tmp_path / "work")), sentinel(tmp_path))
    assert found["excluded_period"] == ec.FAIL


# ---- F2 and F3: reparse points ---------------------------------------------------------------------------------------
class _Entry:
    def __init__(self, path: Path, *, junction=False, symlink=False, directory=False, broken=False, no_stat=False):
        self.path, self.name = str(path), path.name
        self._junction, self._symlink, self._directory, self._broken = junction, symlink, directory, broken
        self._no_stat = no_stat

    def is_junction(self):
        return self._junction

    def is_symlink(self):
        return self._symlink

    def is_dir(self, follow_symlinks=True):
        if self._broken:
            raise PermissionError(13, "denied", self.path)
        return self._directory

    def is_file(self, follow_symlinks=True):
        return not self._directory

    def stat(self, follow_symlinks=True):
        if self._broken or self._no_stat:
            raise PermissionError(13, "denied", self.path)
        return os.stat(self.path)


class _Listing(list):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fake_listing(monkeypatch, folder: Path, extra):
    """os.scandir(folder) gives the real entries plus the fake ones."""
    real = os.scandir

    def scandir(path):
        if ec._norm(path) == ec._norm(folder):
            with real(path) as listing:
                entries = list(listing)
            return _Listing(entries + list(extra))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


def test_f2_a_junction_named_holdout_fails_holdout_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    _fake_listing(monkeypatch, repo / "data", [_Entry(repo / "data" / "holdout", junction=True, directory=True)])
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path))
    assert found["holdout_dir"] == ec.FAIL


def test_f2_a_symlink_with_the_sentinel_name_fails_rule_2_anywhere(tmp_path, monkeypatch):
    repo, desktop = tmp_path / "repo", tmp_path / "Desktop"
    repo.mkdir()
    desktop.mkdir()
    name = f"SENTINEL-ENV002-{TOKEN[:8]}.json"
    _fake_listing(monkeypatch, desktop, [_Entry(desktop / name, symlink=True)])
    found, _ = judge(monkeypatch, roots(tmp_path, repo, search_dirs=(desktop,)), sentinel(tmp_path))
    assert found["sentinel"] == ec.FAIL


def test_f3_a_reparse_point_under_a_data_dir_is_unknown_and_under_a_search_dir_skipped(tmp_path, monkeypatch):
    repo, desktop = tmp_path / "repo", tmp_path / "Desktop"
    (repo / "data" / "transfer").mkdir(parents=True)
    desktop.mkdir()
    _fake_listing(monkeypatch, repo / "data" / "transfer", [_Entry(repo / "data" / "transfer" / "vps", junction=True,
                                                                  directory=True)])
    found, report = judge(monkeypatch, roots(tmp_path, repo, search_dirs=(desktop,)), sentinel(tmp_path))
    assert (found["holdout_dir"], found["excluded_period"], found["sentinel"]) == (ec.UNKNOWN,) * 3
    monkeypatch.undo()
    _fake_listing(monkeypatch, desktop, [_Entry(desktop / "My Music", junction=True, directory=True)])
    found, _ = judge(monkeypatch, roots(tmp_path, repo, search_dirs=(desktop,)), sentinel(tmp_path))
    assert found["sentinel"] == ec.PASS


def test_f2_the_terminal_search_names_reparse_points_without_entering_them(tmp_path, monkeypatch):
    program_files, profile = tmp_path / "Program Files", tmp_path / "Users" / "owner"
    program_files.mkdir(parents=True)
    (profile / "Desktop").mkdir(parents=True)
    junction = program_files / "MetaTrader 5"
    link = profile / "Desktop" / "terminal64.exe"
    other = program_files / "Elsewhere"
    real = os.scandir

    def scandir(path):
        key = ec._norm(path)
        if key in (ec._norm(junction), ec._norm(other)):
            raise AssertionError("a reparse point was entered")
        with real(path) as listing:
            entries = list(listing)
        if key == ec._norm(program_files):
            entries += [_Entry(junction, junction=True, directory=True), _Entry(other, junction=True, directory=True)]
        if key == ec._norm(profile / "Desktop"):
            entries.append(_Entry(link, symlink=True))
        return _Listing(entries)

    monkeypatch.setattr(os, "scandir", scandir)
    found = ec.find_terminal_paths((program_files,), profile, profile / "AppData" / "Roaming")
    assert {Path(path) for path in found} == {junction, link}


# ---- F4: the process list ---------------------------------------------------------------------------------------------
class _Fn:
    def __init__(self, function):
        self.function = function

    def __call__(self, *args):
        return self.function(*args)


def _fake_kernel32(monkeypatch, names, *, first_ok=True, last_error=18):
    queue = list(names)

    def fill(ref):
        if not queue:
            return 0
        ref._obj.szExeFile = queue.pop(0)
        return 1

    kernel32 = SimpleNamespace(
        CreateToolhelp32Snapshot=_Fn(lambda flags, pid: 1234),
        Process32FirstW=_Fn(lambda handle, ref: fill(ref) if first_ok else 0),
        Process32NextW=_Fn(lambda handle, ref: fill(ref)),
        CloseHandle=_Fn(lambda handle: 1))
    monkeypatch.setattr(ec.ctypes, "WinDLL", lambda name, use_last_error=False: kernel32, raising=False)
    monkeypatch.setattr(ec.ctypes, "get_last_error", lambda: last_error, raising=False)  # r2 F12: Windows only
    monkeypatch.setattr(ec.ctypes, "WinError", lambda code=None: OSError(code, "fake WinError"), raising=False)


def test_f4_a_failed_process_list_is_not_an_empty_one(monkeypatch):
    _fake_kernel32(monkeypatch, ["System", "explorer.exe"])
    assert ec._process_names() == ("System", "explorer.exe")
    _fake_kernel32(monkeypatch, ["System"], first_ok=False)
    with pytest.raises(OSError):
        ec._process_names()
    _fake_kernel32(monkeypatch, ["System"], last_error=5)  # Next failed for another reason than the end
    with pytest.raises(OSError):
        ec._process_names()


def test_f4_the_process_entry_has_the_windows_layout():
    wide = ctypes.sizeof(ctypes.c_wchar)
    assert ec._PROCESSENTRY32W.szExeFile.offset == (44 if ctypes.sizeof(ctypes.c_void_p) == 8 else 36)
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        assert ec._PROCESSENTRY32W.th32DefaultHeapID.offset == 16
        assert ctypes.sizeof(ec._PROCESSENTRY32W) == -(-(44 + 260 * wide) // 8) * 8  # 568 on Windows


# ---- F5: what cannot be read is UNKNOWN -------------------------------------------------------------------------------
def test_f5_terminal_roots_that_are_missing_or_unlistable_raise(tmp_path, monkeypatch):
    profile = tmp_path / "Users" / "owner"
    profile.mkdir(parents=True)
    with pytest.raises(OSError):
        ec.find_terminal_paths((), profile, profile)  # no Program Files root at all
    with pytest.raises(OSError):
        ec.find_terminal_paths((tmp_path / "no-such",), profile, profile)
    program_files = tmp_path / "Program Files"
    program_files.mkdir()
    with pytest.raises(OSError):
        ec.find_terminal_paths((program_files,), tmp_path / "no-profile", profile)
    real = os.scandir
    monkeypatch.setattr(os, "scandir", lambda path: (_ for _ in ()).throw(PermissionError(13, "denied"))
                        if ec._norm(path) == ec._norm(program_files) else real(path))
    with pytest.raises(OSError):
        ec.find_terminal_paths((program_files,), profile, profile)


def test_f5_a_missing_search_dir_and_an_unreadable_vault_path_are_unknown(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    found, _ = judge(monkeypatch, roots(tmp_path, repo, search_dirs=(tmp_path / "Desktop",)), sentinel(tmp_path))
    assert found["sentinel"] == ec.UNKNOWN
    vault = tmp_path / "vps" / "vault"
    real = os.stat
    monkeypatch.setattr(os, "stat", lambda path, *args, **kwargs: (_ for _ in ()).throw(PermissionError(13, "denied"))
                        if ec._norm(path) == ec._norm(vault) else real(path, *args, **kwargs))
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path))
    assert found["sentinel"] == ec.UNKNOWN


def test_f5_an_unreadable_root_and_a_deep_manifest_give_a_report(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    touch(repo / "data" / "m" / "bars.parquet", b"PAR1")
    touch(repo / "data" / "m" / "manifest.json", "[" * 200000)
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path))
    assert found["excluded_period"] == ec.FAIL  # broken manifest, no RecursionError
    clean = tmp_path / "clean"
    clean.mkdir()
    locked = tmp_path / "locked" / "data"
    real = os.stat
    monkeypatch.setattr(os, "stat", lambda path, *args, **kwargs: (_ for _ in ()).throw(PermissionError(13, "denied"))
                        if ec._norm(path) == ec._norm(locked) else real(path, *args, **kwargs))
    found, _ = judge(monkeypatch, roots(tmp_path, clean, (clean / "data", locked)), sentinel(tmp_path))
    assert found["excluded_period"] == ec.UNKNOWN


def test_f5_a_missing_repository_is_unknown(tmp_path, monkeypatch):
    found, _ = judge(monkeypatch, roots(tmp_path, tmp_path / "no-repo"), sentinel(tmp_path))
    assert (found["holdout_dir"], found["excluded_period"], found["sentinel"]) == (ec.UNKNOWN,) * 3


def test_f5_failed_shell_folders_stop_with_a_typed_error(monkeypatch, capsys):
    monkeypatch.setattr(ec.sys, "platform", "win32")
    monkeypatch.setattr(ec, "_known_folder", lambda name: None)
    with pytest.raises(OSError):
        ec.default_roots(())
    with pytest.raises(ec.ResearchHostError):
        ec.require_research_host()
    assert ec.main(["--role", "research"]) == 1
    assert capsys.readouterr().out.rstrip().splitlines()[-1] == "RESEARCH HOST: UNKNOWN"


# ---- F6: never open under a terminal folder, never list MetaQuotes ----------------------------------------------------
def test_f6_a_data_dir_below_a_terminal_folder_is_never_opened(tmp_path, monkeypatch):
    repo, terminal = tmp_path / "repo", tmp_path / "MT5"
    repo.mkdir()
    touch(terminal / "terminal64.exe", b"MZ")
    files = terminal / "MQL5" / "Files"
    touch(files / "notes.txt", f"{TOKEN}\n")
    snapshot(files / "snap", EARLY)
    with K.recording() as audit:
        found, _ = judge(monkeypatch, roots(tmp_path, repo, (repo / "data", files)), sentinel(tmp_path))
    assert not {path for path in audit.opened() if path.startswith(ec._norm(terminal))}
    assert found["sentinel"] == ec.UNKNOWN and found["excluded_period"] == ec.UNKNOWN


@pytest.mark.parametrize("kind", ["search", "data"])
def test_f6_metaquotes_is_never_listed_as_a_root(tmp_path, monkeypatch, kind):
    repo, appdata = tmp_path / "repo", tmp_path / "AppData" / "Roaming"
    repo.mkdir()
    folder = appdata / "MetaQuotes" / "Terminal"
    touch(folder / "x.txt", "x\n")
    data = (repo / "data", folder) if kind == "data" else None
    search = (folder,) if kind == "search" else ()
    with K.recording() as audit:
        found, _ = judge(monkeypatch, roots(tmp_path, repo, data, search, appdata), sentinel(tmp_path))
    assert not [path for path in audit.listings if path.startswith(ec._norm(appdata / "MetaQuotes"))]
    assert found["sentinel"] == ec.UNKNOWN


def test_f6_a_manifest_beside_a_terminal_is_not_opened(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    folder = repo / "data" / "MT5"
    touch(folder / "terminal64.exe", b"MZ")
    snapshot(folder, EARLY)
    with K.recording() as audit:
        found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path))
    assert ec._norm(folder / "manifest.json") not in audit.opened() and found["excluded_period"] == ec.UNKNOWN


# ---- F7: the values file and empty values -------------------------------------------------------------------------------
GOOD = {"name": f"SENTINEL-ENV002-{TOKEN[:8]}.json", "size": 5731, "sha256": "a" * 64, "token": TOKEN,
        "vault_path": "C:\\vault", "created_utc": "2026-11-05T09:30:00Z"}


@pytest.mark.parametrize("change", [{"vault_path": ""}, {"vault_path": "vault"}, {"name": ""},
                                    {"name": "SENTINEL-ENV002-ffffffff.json"}, {"created_utc": "yesterday"}])
def test_f7_a_values_file_that_switches_a_rule_off_is_refused(tmp_path, monkeypatch, change):
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    sentinel_value, note = ec.load_sentinel(touch(tmp_path / "values.json", json.dumps({**GOOD, **change})))
    assert sentinel_value is None and note and TOKEN not in note


@pytest.mark.parametrize("change", [{"vault_path": ""}, {"name": ""}])
def test_f7_an_empty_name_or_vault_path_is_unknown(tmp_path, monkeypatch, change):
    repo = tmp_path / "repo"
    repo.mkdir()
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path, **change))
    assert found["sentinel"] == ec.UNKNOWN


def test_f7_the_excused_file_still_follows_rule_3(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    touch(repo / "docs" / "evidence" / "ENV-002-sentinel.json", SENTINEL_BYTES)
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path))
    assert found["sentinel"] == ec.FAIL


# ---- F8: both manifests ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("folder_end, per_file_end, cloud, expected", [
    (LATE, EARLY, False, ec.FAIL), (EARLY, LATE, False, ec.FAIL), (EARLY, EARLY, True, ec.UNKNOWN),
    (EARLY, EARLY, False, ec.PASS)])
def test_f8_a_file_with_both_manifests_must_pass_both(tmp_path, monkeypatch, folder_end, per_file_end, cloud, expected):
    repo = tmp_path / "repo"
    folder = repo / "data" / "m"
    snapshot(folder, folder_end, per_file=per_file_end)
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path),
                     cloud=(folder / "manifest.json",) if cloud else ())
    assert found["excluded_period"] == expected


# ---- F9: the report says what was checked ----------------------------------------------------------------------------------
def test_f9_the_pass_report_names_the_sentinel_and_counts_the_search(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    touch(repo / "README.md", "# repo\n")
    value = sentinel(tmp_path)
    found, report = judge(monkeypatch, roots(tmp_path, repo), value)
    details = {item.name: item.detail for item in report.items}
    assert found["sentinel"] == ec.PASS
    assert value.name in details["sentinel"] and value.sha256 in details["sentinel"] and TOKEN not in details["sentinel"]
    for name in ("holdout_dir", "excluded_period", "sentinel"):
        assert "folders listed" in details[name] and "files examined" in details[name]


# ---- F10: the guards the first unit tests left out --------------------------------------------------------------------------
def test_f10_within_is_not_a_plain_prefix():
    assert ec._within(ec._norm("x/data"), ec._norm("x/data")) and ec._within(ec._norm("x/data/a"), ec._norm("x/data"))
    assert not ec._within(ec._norm("x/data2"), ec._norm("x/data"))


@pytest.mark.parametrize("chunk", range(1, 71))
def test_f10_the_token_is_found_across_every_chunk_boundary(tmp_path, monkeypatch, chunk):
    monkeypatch.setattr(ec, "CHUNK", chunk)
    for encoding in ("ascii", "utf-16-le", "utf-16-be"):
        path = touch(tmp_path / f"{encoding}.txt", b"\x00" * 3 + TOKEN.encode(encoding) + b"\x00" * 2)
        assert ec._read(path, ec._token_patterns(TOKEN), False)[0] is True


def test_f10_unreadable_kinds_cloud_states_and_sizes_are_unknown(tmp_path, monkeypatch):
    repo, desktop = tmp_path / "repo", tmp_path / "Desktop"
    touch(repo / "notes.txt", "x\n")
    desktop.mkdir()
    _fake_listing(monkeypatch, repo, [_Entry(repo / "odd", broken=True)])
    found, _ = judge(monkeypatch, roots(tmp_path, repo), sentinel(tmp_path))
    assert found["sentinel"] == ec.UNKNOWN and found["holdout_dir"] == ec.UNKNOWN  # M25
    monkeypatch.undo()
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: (_ for _ in ()).throw(PermissionError(13, "denied")))
    assert {i.name: i.status for i in ec.evaluate(FACTS, roots(tmp_path, repo), sentinel(tmp_path)).items}[
        "sentinel"] == ec.UNKNOWN  # M40
    monkeypatch.undo()
    _fake_listing(monkeypatch, desktop, [_Entry(desktop / "export.json", broken=True)])
    found, _ = judge(monkeypatch, roots(tmp_path, repo, search_dirs=(desktop,)), sentinel(tmp_path))
    assert found["sentinel"] == ec.UNKNOWN  # M46


def test_f10_collect_keeps_unreadable_facts_as_none(tmp_path, monkeypatch):
    appdata = tmp_path / "AppData"
    (appdata / "MetaQuotes").mkdir(parents=True)
    research_roots = roots(tmp_path, tmp_path / "repo", appdata=appdata)

    def broken(*args):
        raise OSError("fake failure")

    for name in ("_uninstall_display_names", "_process_names", "_remote_drives", "_connected_resources",
                 "find_terminal_paths"):
        monkeypatch.setattr(ec, name, broken)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "MetaTrader5" else object())
    facts = ec.collect(research_roots)
    assert (facts.terminal_paths, facts.uninstall_display_names, facts.process_names, facts.remote_drives,
            facts.connected_resources) == (None,) * 5
    assert facts.metaquotes_exists is True and facts.mt5_spec_found is False
    monkeypatch.setattr(ec, "_uninstall_display_names", lambda: ("MetaTrader 5",))
    monkeypatch.setattr(ec, "_process_names", lambda: ("terminal64.exe",))
    monkeypatch.setattr(ec, "_remote_drives", lambda: ("Z:\\",))
    monkeypatch.setattr(ec, "_connected_resources", lambda: ("\\\\vps\\c$",))
    monkeypatch.setattr(ec, "find_terminal_paths", lambda *args: ("C:\\Program Files\\MetaTrader 5",))
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    facts = ec.collect(research_roots)
    assert facts == ec.Facts(terminal_paths=("C:\\Program Files\\MetaTrader 5",), uninstall_display_names=("MetaTrader 5",),
                             process_names=("terminal64.exe",), metaquotes_exists=True, mt5_spec_found=True,
                             remote_drives=("Z:\\",), connected_resources=("\\\\vps\\c$",))


def _make_sentinel_module():
    spec = importlib.util.spec_from_file_location("make_sentinel_r1", REPO_ROOT / "scripts" / "env" / "make_sentinel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_f10_make_sentinel_never_overwrites_and_prints_a_time(tmp_path, monkeypatch, capsys):
    module = _make_sentinel_module()
    monkeypatch.setattr(module.secrets, "token_hex", lambda size: TOKEN)
    monkeypatch.chdir(tmp_path)
    assert module.main() == 0
    values = json.loads(capsys.readouterr().out)
    assert ec.TIME_PATTERN.fullmatch(values["created_utc"])  # S07
    before = (tmp_path / values["name"]).read_bytes()
    with pytest.raises(FileExistsError):  # S01: mode "xb"
        module.main()
    assert (tmp_path / values["name"]).read_bytes() == before
    assert isinstance(io.BytesIO(before).read(), bytes)


# ---- implementation review r2 ------------------------------------------------------------------------------------------
def test_r2_f10_a_search_dir_json_whose_size_cannot_be_read_is_unknown(tmp_path, monkeypatch):
    # M46 proper: the entry's kind is readable, only its stat is refused.
    repo, desktop = tmp_path / "repo", tmp_path / "Desktop"
    repo.mkdir()
    touch(desktop / "export.json", SENTINEL_BYTES)
    real = os.scandir

    def scandir(path):
        with real(path) as listing:
            entries = list(listing)
        if ec._norm(path) == ec._norm(desktop):
            entries = [_Entry(Path(entry.path), no_stat=True) for entry in entries]
        return _Listing(entries)

    monkeypatch.setattr(os, "scandir", scandir)
    found, _ = judge(monkeypatch, roots(tmp_path, repo, search_dirs=(desktop,)), sentinel(tmp_path))
    assert found["sentinel"] == ec.UNKNOWN


def test_r2_f13_a_relative_root_below_a_terminal_folder_is_never_opened(tmp_path, monkeypatch):
    repo, terminal = tmp_path / "repo", tmp_path / "MT5"
    repo.mkdir()
    touch(terminal / "terminal64.exe", b"MZ")
    touch(terminal / "MQL5" / "Files" / "notes.txt", f"{TOKEN}\n")
    monkeypatch.chdir(terminal / "MQL5")
    with K.recording() as audit:
        found, _ = judge(monkeypatch, roots(tmp_path, repo, (repo / "data", Path("Files"))), sentinel(tmp_path))
    assert not {path for path in audit.opened() if path.startswith(ec._norm(terminal))}
    assert found["sentinel"] == ec.UNKNOWN


def test_r2_f14_a_search_dir_behind_a_junction_under_another_is_walked(tmp_path, monkeypatch):
    repo, onedrive = tmp_path / "repo", tmp_path / "OneDrive"
    repo.mkdir()
    onedrive.mkdir()
    target = tmp_path / "D-drive" / "Docs"
    touch(target / "export.json", SENTINEL_BYTES)
    docs = onedrive / "Docs"  # a junction to target in OneDrive; given as its own search dir
    real = os.scandir

    def scandir(path):
        key = ec._norm(path)
        if key == ec._norm(docs):
            return real(target)  # what Windows lists through the junction
        with real(path) as listing:
            entries = list(listing)
        if key == ec._norm(onedrive):
            entries.append(_Entry(docs, junction=True, directory=True))
        return _Listing(entries)

    monkeypatch.setattr(os, "scandir", scandir)
    monkeypatch.setattr(ec, "_kind", lambda path: "dir")
    for order in ((onedrive, docs), (docs, onedrive)):
        found, _ = judge(monkeypatch, roots(tmp_path, repo, search_dirs=order), sentinel(tmp_path))
        assert found["sentinel"] == ec.FAIL


@pytest.mark.parametrize("relative", [".env.json", "values.key", "MT5/values.json", "AppData/Roaming/MetaQuotes/v.json"])
def test_r2_f15_the_cli_never_opens_a_closed_values_file(tmp_path, monkeypatch, relative):
    touch(tmp_path / "MT5" / "terminal64.exe", b"MZ")
    path = touch(tmp_path / relative, json.dumps({**GOOD}))
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: False)
    with K.recording() as audit:
        sentinel_value, note = ec.load_sentinel(path, appdata=tmp_path / "AppData" / "Roaming")
    assert sentinel_value is None and note and ec._norm(path) not in audit.opened()
    control = touch(tmp_path / "docs" / "values.json", json.dumps(GOOD))
    assert ec.load_sentinel(control, appdata=tmp_path / "AppData" / "Roaming")[0] is not None
