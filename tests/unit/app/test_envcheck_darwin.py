"""Implementer's unit tests for the darwin reader of sochron.app.envcheck (ENV-002 v2.6).

They cover what the locked acceptance tests leave to tests/unit/app: the struct statfs layout (contract
v2.1 F19), the measured mount table of the owner's Mac and the python3.12 link that uv makes (tests review
v2 r1 F2), the layer that builds the reason of a failing raw reader (tests review v2 r1 Q6), the buffer
limits of the two pure readers, and the forms of the apps:, tools:, skipped:, wine: and roots: lines. No OS
reader is called: the raw readers are replaced and every folder is under tmp_path, so the tests give the
same result on Linux CI and on the Mac.
"""

import ctypes
import os
import sys
from pathlib import Path

import pytest

from sochron.app import envcheck as ec

TOKEN = "0123456789abcdef0123456789abcdef"
LOCAL = 0x00001000


def _facts(**changes):
    values = {"terminal_paths": (), "uninstall_display_names": (), "process_names": (), "metaquotes_exists": False,
              "mt5_spec_found": False, "remote_drives": (), "connected_resources": ()}
    return ec.Facts(**{**values, **changes})


def _sentinel(tmp_path):
    return ec.Sentinel(name="SENTINEL-ENV002-01234567.json", size=10, sha256="0" * 64, token=TOKEN,
                       vault_path=str(tmp_path / "vault"), created_utc="2026-11-05T00:00:00Z")


def _roots(tmp_path, repo, **changes):
    values = {"repo": repo, "data_dirs": (repo / "data",), "program_files": (), "appdata": tmp_path / "AppData",
              "user_profile": tmp_path / "home", "search_dirs": ()}
    return ec.ResearchRoots(**{**values, **changes})


# ---- struct statfs (v2.1 F19: 2168 bytes and the four offsets) --------------------------------------------
def test_statfs_is_the_arm64_struct_of_the_sdk():
    offsets = {name: getattr(ec._STATFS, name).offset
               for name in ("f_flags", "f_fstypename", "f_mntonname", "f_mntfromname")}
    assert ctypes.sizeof(ec._STATFS) == 2168
    assert offsets == {"f_flags": 64, "f_fstypename": 72, "f_mntonname": 88, "f_mntfromname": 1112}


# ---- mounts ------------------------------------------------------------------------------------------------
MEASURED = (  # /sbin/mount on the owner's Mac, 2026-11-18: 12 mounts (tests review v2 r1 F2)
    ("apfs", "/dev/disk3s1s1", "/", LOCAL | 0x1),
    ("devfs", "devfs", "/dev", LOCAL),
    ("apfs", "/dev/disk3s6", "/System/Volumes/VM", LOCAL),
    ("apfs", "/dev/disk3s2", "/System/Volumes/Preboot", LOCAL),
    ("apfs", "/dev/disk3s4", "/System/Volumes/Update", LOCAL),
    ("apfs", "/dev/disk1s2", "/System/Volumes/xarts", LOCAL),
    ("apfs", "/dev/disk1s1", "/System/Volumes/iSCPreboot", LOCAL),
    ("apfs", "/dev/disk1s3", "/System/Volumes/Hardware", LOCAL),
    ("apfs", "/dev/disk3s5", "/System/Volumes/Data", LOCAL),
    ("autofs", "map auto_home", "/System/Volumes/Data/home", 0x00100000),
    ("apfs", "/dev/disk2s1", "/System/Volumes/Update/SFR/mnt1", LOCAL),
    ("apfs", "/dev/disk3s1", "/System/Volumes/Update/mnt1", LOCAL),
)


def test_the_measured_mounts_of_the_owners_mac_pass():
    assert ec.MNT_LOCAL == LOCAL
    assert ec.classify_mounts(MEASURED) == ((), (), (), None)
    assert ec._mounts_line(MEASURED, (), None) == "12 (apfs, devfs, autofs)"


@pytest.mark.parametrize("point, allowed", [
    ("/", True), ("/dev", True), ("/System/Volumes/Data", True), ("/System/Volumes/Data/home", True),
    ("/System/Volumes/Update/SFR/mnt1", True), ("/System/Volumes/xarts", True),
    ("/System/Volumes/Data/Users/x", False), ("/System/Volumes/Data/private/tmp/mnt", False),
    ("/System/Volumes", False), ("/Volumes/USB", False), ("/home", False), ("/devices", False),
])
def test_mount_points_follow_the_allow_list(point, allowed):
    assert ec._mount_point_allowed(point) is allowed


@pytest.mark.parametrize("kind", ("tmpfs", "hfs", "nullfs", "autofs"))
def test_a_local_filesystem_stacked_over_the_apfs_root_is_unknown(kind):
    """Work review r3 F16: every mount at / that passes the FAIL rules must be apfs, not only the first one."""
    base = (("apfs", "/dev/disk3s1s1", "/", LOCAL | 0x1), ("devfs", "devfs", "/dev", LOCAL),
            ("autofs", "map auto_home", "/System/Volumes/Data/home", 0x00100000))
    stacked = base + ((kind, kind, "/", LOCAL if kind != "autofs" else 0),)
    assert ec.classify_mounts(base) == ((), (), (), None)
    assert ec.classify_mounts(stacked) == ((), None, (), kind)


def test_a_remote_root_is_fail_without_a_root_problem():
    """The FAIL rules come first: nfs at / is in remote_drives and is no root: problem (work review r3 F16)."""
    remote, resources, outside, root = ec.classify_mounts((("nfs", "vps.example:/", "/", 0),
                                                           ("devfs", "devfs", "/dev", LOCAL)))
    assert (remote, resources, outside, root) == (("nfs vps.example:/ on /",), (), (), None)


def test_the_mounts_line_names_points_outside_the_list_and_the_root_problem():
    entries = (("hfs", "/dev/disk2s1", "/", LOCAL), ("apfs", "/dev/disk4s1", "/Volumes/USB", LOCAL),
               ("apfs", "/dev/disk4s2", "/Volumes/USB2", LOCAL))
    remote, resources, outside, root = ec.classify_mounts(entries)
    assert (remote, resources, outside, root) == ((), None, ("/Volumes/USB", "/Volumes/USB2"), "hfs")
    assert ec._mounts_line(entries, outside, root) == "3 (hfs, apfs); not allowed: /Volumes/USB, /Volumes/USB2; root: hfs"


# ---- the pure readers: the reason of a failing raw reader (Q6) and the buffer limits ----------------------
def test_the_pure_readers_build_the_reason_of_a_failing_raw_reader(monkeypatch):
    def fail(capacity):
        raise OSError(5, "failed")

    monkeypatch.setattr(ec, "_darwin_list_pids", fail)
    monkeypatch.setattr(ec, "_darwin_mounts", fail)
    with pytest.raises(OSError) as pids:
        ec.read_process_paths(os.getpid(), "/x")
    with pytest.raises(OSError) as mounts:
        ec.read_mounts()
    assert (str(pids.value), str(mounts.value)) == ("proc_listallpids failed, errno 5", "getfsstat failed, errno 5")


def test_a_pid_list_that_always_fills_its_buffer_is_unreadable(monkeypatch):
    capacities = []

    def full(capacity):
        capacities.append(capacity)
        return capacity, tuple(range(1, capacity + 1))

    monkeypatch.setattr(ec, "_darwin_list_pids", full)
    with pytest.raises(OSError, match="filled a buffer"):
        ec.read_process_paths(os.getpid(), "/x")
    assert capacities[0] == ec.PID_CAPACITY and capacities[-1] == ec.PID_LIMIT


def test_a_mount_list_that_always_fills_its_buffer_is_unreadable(monkeypatch):
    entry = ("apfs", "/dev/disk3s1s1", "/", LOCAL)
    monkeypatch.setattr(ec, "_darwin_mounts", lambda capacity: (capacity, (entry,) * capacity))
    with pytest.raises(OSError, match="filled a buffer"):
        ec.read_mounts()


# ---- the interpreter links of uv (v2.1 F5; tests review v2 r1 F2) ----------------------------------------
def _venv(tmp_path, *links):
    repo = tmp_path / "repo"
    folder = repo / ".venv" / "bin"
    folder.mkdir(parents=True)
    for name, target in links:
        os.symlink(target, folder / name)
    return repo


def _searched(tmp_path, repo):
    report = ec.evaluate(_facts(), _roots(tmp_path, repo), _sentinel(tmp_path))
    return {item.name: item for item in report.items}


def test_the_three_links_that_uv_makes_are_excused(tmp_path):
    interpreter = os.path.realpath(sys.executable)
    repo = _venv(tmp_path, ("python", interpreter), ("python3", "python"), ("python3.12", "python"))
    items = _searched(tmp_path, repo)
    assert [items[name].status for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.PASS] * 3
    assert "reparse points skipped 3, interpreter links excused 3" in items["sentinel"].detail


def test_a_link_name_in_another_case_is_not_excused(tmp_path):
    repo = _venv(tmp_path, ("Python", os.path.realpath(sys.executable)))
    items = _searched(tmp_path, repo)
    assert [items[name].status for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.UNKNOWN] * 3
    assert "interpreter links excused 0" in items["sentinel"].detail


# ---- the lines of host_lines() ---------------------------------------------------------------------------
def test_the_apps_line_follows_the_contract_order(tmp_path):
    applications = tmp_path / "Applications"
    for name in ("Docker.app", "UTM.app", "Wineskin Winery.app", "CrossOver.app", "Safari.app", "Wine Stable.app"):
        (applications / name).mkdir(parents=True)
    assert ec._apps_line((applications, tmp_path / "missing")) == (
        "CrossOver.app, Wineskin Winery.app, Wine Stable.app, UTM.app, Docker.app")


def test_the_apps_line_names_an_unreadable_folder_and_what_the_other_one_holds(tmp_path, monkeypatch):
    applications, blocked = tmp_path / "Applications", tmp_path / "Blocked"
    (applications / "UTM.app").mkdir(parents=True)
    blocked.mkdir()
    real_scandir = os.scandir

    def scandir(path):
        if ec._norm(path) == ec._norm(blocked):
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    assert ec._apps_line((blocked, applications)) == f"unreadable ({blocked}); found: UTM.app"


def test_the_tools_line_looks_at_existence_only(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".colima" / "default").mkdir(parents=True)
    (home / ".local" / "share" / "containers").mkdir(parents=True)
    (home / ".docker").write_text("x")

    def no_listing(path="."):
        raise AssertionError(f"listed {path}")

    monkeypatch.setattr(os, "scandir", no_listing)
    monkeypatch.setattr(os, "listdir", no_listing)
    assert ec._tools_line(home) == ".colima, .docker, .local/share/containers"


def test_the_skipped_line_counts_the_folders_and_shortens_home(tmp_path):
    home = tmp_path / "home"
    other = tmp_path / "pf" / "Vendor"
    assert ec._skipped_line((), home) == "0 folders"
    assert ec._skipped_line((str(home / ".Trash"), str(other)), home) == f"2 folders (~/.Trash, {other})"


def test_a_symlinked_wine_folder_gives_the_symlink_reason_from_home(tmp_path):
    home = tmp_path / "home"
    (tmp_path / "elsewhere").mkdir()
    home.mkdir()
    os.symlink(tmp_path / "elsewhere", home / ".wine", target_is_directory=True)
    with pytest.raises(OSError) as raised:
        ec.wine_prefixes(home)
    assert ec._wine_reason(raised.value, home) == "~/.wine: symlink"


def test_host_lines_of_another_reader_print_no_darwin_line(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cloud = home / "Library" / "CloudStorage" / "OneDrive-Personal"
    roots = _roots(tmp_path, tmp_path / "repo", search_dirs=(cloud,))
    monkeypatch.setattr(ec, "_HOST_SUMMARY", {"reader": "win32", "roots": roots})
    assert ec.host_lines() == ("reader: win32", f"roots: repo={tmp_path / 'repo'} home={home} search_dirs={cloud}")


def test_the_darwin_roots_line_counts_no_cloud_storage_as_zero(tmp_path, monkeypatch):
    downloads = tmp_path / "home" / "Downloads"
    roots = _roots(tmp_path, tmp_path / "repo", search_dirs=(downloads,))
    monkeypatch.setattr(ec, "_HOST_SUMMARY", {"reader": "darwin", "roots": roots})
    lines = ec.host_lines()
    assert lines[1].endswith(f"search_dirs={downloads}; cloud storage: 0")
    assert lines[2:] == ("processes: not read", "mounts: not read", "wine: not read")


def test_host_lines_never_raise_on_a_broken_summary(monkeypatch):
    monkeypatch.setattr(ec, "_HOST_SUMMARY", {"reader": "darwin", "roots": object()})
    assert ec.host_lines()[:2] == ("reader: darwin", "roots: unreadable")


# ---- load_sentinel and the terminal data folders of appdata (v2.2 r2 F28) --------------------------------
@pytest.mark.parametrize("name", ("net.metaquotes.wine.metatrader5", "MetaTrader 5", "metaquotes"))
def test_a_sentinel_file_under_a_terminal_data_folder_is_never_examined(tmp_path, monkeypatch, name):
    appdata = tmp_path / "Application Support"
    path = appdata / name / "ENV-002-sentinel.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    def is_cloud_only(value):  # the file itself is never examined; appdata's ancestors may be (r4 F23)
        if ec._norm(value) == ec._norm(path):
            pytest.fail(f"{value} was examined")
        return False

    monkeypatch.setattr(ec, "is_cloud_only", is_cloud_only)
    sentinel, why = ec.load_sentinel(path, appdata=appdata)
    assert sentinel is None and "never opened" in why


def test_another_spelling_of_appdata_still_hides_its_terminal_data_folders(tmp_path, monkeypatch):
    """Work review r3 F17: appdata reached through a symlinked parent is recognised by identity, so its terminal
    data folder is never listed or opened in evaluate, and load_sentinel refuses a file under it."""
    home = tmp_path / "Home"
    appdata = home / "Library" / "Application Support"
    folder = appdata / "MetaTrader 5"
    folder.mkdir(parents=True)
    (folder / "notes.txt").write_text(f"pasted from the VPS: {TOKEN}\n")
    (folder / "values.json").write_text("{}")
    os.symlink(home, tmp_path / "alias", target_is_directory=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    listed = []
    real_scandir = os.scandir

    def scandir(path="."):
        listed.append(ec._norm(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    roots = _roots(tmp_path, repo, appdata=appdata, data_dirs=(repo / "data", tmp_path / "alias" / "Library"))
    report = ec.evaluate(_facts(metaquotes_exists=False), roots, _sentinel(tmp_path))
    statuses = {item.name: item.status for item in report.items}
    assert [statuses[name] for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.UNKNOWN] * 3
    assert [path for path in listed if "MetaTrader 5" in path] == []
    other = tmp_path / "alias" / "Library" / "Application Support" / "MetaTrader 5" / "values.json"
    sentinel, why = ec.load_sentinel(other, appdata=appdata)
    assert sentinel is None and "never opened" in why


def test_a_renamed_link_into_appdata_or_a_terminal_data_folder_is_caught(tmp_path, monkeypatch):
    """Work review r4 F22: a data dir that is a link with another name to appdata or to its terminal data folder,
    and a --sentinel-file link into that folder, are caught by identity or by the real path; nothing under the
    folder is listed and the values file is never opened."""
    appdata = tmp_path / "Home" / "Library" / "Application Support"
    folder = appdata / "MetaTrader 5"
    folder.mkdir(parents=True)
    (folder / "notes.txt").write_text(f"pasted from the VPS: {TOKEN}\n")
    (folder / "values.json").write_text("{}")
    os.symlink(appdata, tmp_path / "as-link", target_is_directory=True)
    os.symlink(folder, tmp_path / "mt5-link", target_is_directory=True)
    os.symlink(folder / "values.json", tmp_path / "link.json")
    repo = tmp_path / "repo"
    repo.mkdir()
    listed = []
    real_scandir = os.scandir

    def scandir(path="."):
        listed.append(ec._norm(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    for data_dir in (tmp_path / "as-link", tmp_path / "mt5-link"):
        listed.clear()
        roots = _roots(tmp_path, repo, appdata=appdata, data_dirs=(repo / "data", data_dir))
        report = ec.evaluate(_facts(metaquotes_exists=False), roots, _sentinel(tmp_path))
        statuses = {item.name: item.status for item in report.items}
        assert [statuses[name] for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.UNKNOWN] * 3
        assert [path for path in listed if "MetaTrader 5" in path or path == ec._norm(tmp_path / "mt5-link")] == []
    sentinel, why = ec.load_sentinel(tmp_path / "link.json", appdata=appdata)
    assert sentinel is None and "never opened" in why


def test_appdata_below_a_dataless_folder_is_matched_by_text_and_nothing_below_is_statted(tmp_path, monkeypatch):
    """Work review r4 F23: when appdata lies below a dataless folder, its identity is not taken, so evaluate stats
    nothing below that folder (v2.2 r2 F12)."""
    cloud = tmp_path / "Cloud"
    appdata = cloud / "Library" / "Application Support"
    appdata.mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: ec._norm(path) == ec._norm(cloud))
    seen = []

    def recorder(real):
        def wrapper(path, *args, **kwargs):
            if not isinstance(path, int):
                seen.append(ec._norm(path))
            return real(path, *args, **kwargs)
        return wrapper

    monkeypatch.setattr(os, "stat", recorder(os.stat))
    monkeypatch.setattr(os, "lstat", recorder(os.lstat))
    ec.evaluate(_facts(), _roots(tmp_path, repo, appdata=appdata), _sentinel(tmp_path))
    assert [path for path in seen if path.startswith(ec._norm(cloud) + os.sep)] == []


@pytest.mark.parametrize("error", (RecursionError, PermissionError, ValueError))
def test_a_real_path_that_cannot_be_resolved_is_unknown_or_refused_and_never_raises(tmp_path, monkeypatch, error):
    """Work review r5 F26: when realpath fails on a root (a link that cannot be read, or a chain deep enough for
    RecursionError), the three items are UNKNOWN with the reason and the token masked, and the sentinel file
    through that link is refused; nothing leaves evaluate or load_sentinel as an exception."""
    appdata = tmp_path / "AppData"
    appdata.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "values.json").write_text("{}")
    link = tmp_path / f"link-{TOKEN}"
    os.symlink(target, link, target_is_directory=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    real_realpath = os.path.realpath

    def realpath(path, *args, **kwargs):
        if str(link) in os.fspath(path):
            raise error("refused")
        return real_realpath(path, *args, **kwargs)

    monkeypatch.setattr(os.path, "realpath", realpath)
    roots = _roots(tmp_path, repo, appdata=appdata, data_dirs=(repo / "data", link))
    report = ec.evaluate(_facts(), roots, _sentinel(tmp_path))
    items = {item.name: item for item in report.items}
    assert [items[name].status for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.UNKNOWN] * 3
    assert f"could not be resolved to its real path ({error.__name__})" in items["sentinel"].detail
    assert TOKEN not in items["sentinel"].detail
    sentinel, why = ec.load_sentinel(link / "values.json", appdata=appdata)
    assert sentinel is None and f"could not be resolved to its real path ({error.__name__})" in why


def test_an_over_long_link_chain_is_unknown_or_refused_and_never_raises(tmp_path):
    """Work review r5 F26: a root or --sentinel-file at the head of 1,100 chained links (beyond what the kernel
    follows, and deep enough for realpath's recursion) is UNKNOWN or refused, as before work review r4 F22."""
    appdata = tmp_path / "AppData"
    appdata.mkdir()
    head = tmp_path / "target"
    head.mkdir()
    file_head = tmp_path / "values.json"
    file_head.write_text("{}")
    for index in range(1100):
        os.symlink(head, tmp_path / f"chain{index}", target_is_directory=True)
        os.symlink(file_head, tmp_path / f"file{index}.json")
        head, file_head = tmp_path / f"chain{index}", tmp_path / f"file{index}.json"
    repo = tmp_path / "repo"
    repo.mkdir()
    roots = _roots(tmp_path, repo, appdata=appdata, data_dirs=(repo / "data", head))
    report = ec.evaluate(_facts(), roots, _sentinel(tmp_path))
    statuses = {item.name: item.status for item in report.items}
    assert [statuses[name] for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.UNKNOWN] * 3
    sentinel, why = ec.load_sentinel(file_head, appdata=appdata)
    assert sentinel is None and "could not be read" in why


def test_a_nul_in_a_root_or_the_sentinel_path_is_unknown_or_refused_and_never_raises(tmp_path):
    """Work review r5 F26: a NUL in a hand-built root or sentinel path gives UNKNOWN or a refusal, not ValueError."""
    appdata = tmp_path / "AppData"
    appdata.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    roots = _roots(tmp_path, repo, appdata=appdata, data_dirs=(repo / "data", Path(f"{tmp_path}/bad\0name")))
    report = ec.evaluate(_facts(), roots, _sentinel(tmp_path))
    statuses = {item.name: item.status for item in report.items}
    assert [statuses[name] for name in ("holdout_dir", "excluded_period", "sentinel")] == [ec.UNKNOWN] * 3
    sentinel, why = ec.load_sentinel(Path(f"{tmp_path}/bad\0values.json"), appdata=appdata)
    assert sentinel is None and "could not be read" in why


@pytest.mark.parametrize("make", ("symlinked prefix", "home named with the token"))
def test_the_token_never_reaches_the_cli_or_the_gate_when_a_wine_folder_fails(tmp_path, monkeypatch, capsys, make):
    """Work review r3 F18: a Wine folder that cannot be read raises OSError naming only the fixed folder from ~/,
    so neither main's output nor ResearchHostError holds the token (or the account name)."""
    home = tmp_path / (f"home-{TOKEN}" if make == "home named with the token" else "home")
    source = home / "Library" / "PlayOnMac" / "wineprefix"
    source.mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    os.symlink(tmp_path / "elsewhere", source / (TOKEN if make == "symlinked prefix" else "p1"), target_is_directory=True)
    monkeypatch.setattr(ec.sys, "platform", "darwin")
    monkeypatch.setattr(ec, "_darwin_home", lambda: str(home))
    code = ec.main(["--role", "research"])
    captured = capsys.readouterr()
    assert code == 1 and TOKEN not in captured.out + captured.err
    assert "~/Library/PlayOnMac/wineprefix (symlink)" in captured.out
    assert str(tmp_path) not in captured.out
    with pytest.raises(ec.ResearchHostError) as raised:
        ec.require_research_host(sentinel=_sentinel(tmp_path))
    assert TOKEN not in str(raised.value) and raised.value.__cause__ is None


def test_a_dataless_search_root_makes_the_terminal_search_incomplete(tmp_path, monkeypatch):
    """Work review r3 F19: a dataless root is named in skipped: and the search is not complete (fail-closed);
    a dataless folder below a root is still only skipped."""
    home = tmp_path / "home"
    (home / "x").mkdir(parents=True)
    (home / "x" / "terminal64.exe").write_bytes(b"MZ synthetic")
    (home / "Music" / "Archive").mkdir(parents=True)
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: ec._norm(path) == ec._norm(home))
    found, complete, skipped = ec.find_terminal_paths_darwin((), (), home, ())
    assert (found, complete, skipped) == ((), False, (str(home),))
    monkeypatch.setattr(ec, "is_cloud_only", lambda path: ec._norm(path) == ec._norm(home / "Music" / "Archive"))
    found, complete, skipped = ec.find_terminal_paths_darwin((), (), home, ())
    assert complete is True and skipped == (str(home / "Music" / "Archive"),) and len(found) == 1


def test_the_reader_name_is_none_on_other_platforms(monkeypatch):
    monkeypatch.setattr(ec.sys, "platform", "linux")
    assert ec.reader_name() == "none"
    assert Path(ec._darwin_application_dirs("/Users/x")[1]) == Path("/Users/x/Applications")
