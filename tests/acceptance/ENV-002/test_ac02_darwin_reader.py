r"""ENV-002 v2.6 contract tests for AC-02, macOS cases on the darwin reader's module-level functions
(docs/contracts/ENV-002-research-host-separation.md, "v2.0 (ร่าง, D-023): ตัวอ่านตามแพลตฟอร์ม" and the
Negative cases marked (v2.0) and later); run pytest from the repository root.

Each test calls the one function the contract names for its case, with fakes for the raw readers where
the contract says tests replace them: classify_mounts, classify_processes, read_process_paths (fake
_darwin_list_pids and _darwin_pid_path), read_mounts (fake _darwin_mounts), wine_prefixes,
find_wine_program_files, find_terminal_paths_darwin, is_cloud_only (fake os.stat), reader_name and the
constants MNT_LOCAL and SF_DATALESS. Nothing here calls libproc, getfsstat or the real home folder; the
cases run the same on Linux CI and on the Mac. Conventions D1-D8 are in darwinkit.py; the ones below are
specific to this file:
D9.  classify_mounts returns (remote_drives, connected_resources, not allowed, root problem). An item
     result follows the Facts table of contract v2.1 F4: FAIL when remote_drives has an entry, else
     UNKNOWN when connected_resources is None, else PASS; connected_resources is () or None (a Mac has
     no connected resources of its own). A FAIL entry reads "<type> <source> on <mount point>".
D10. read_process_paths(own_pid, own_path) is called with a made-up own pid 4242 and path, since it reads
     only through the fake raw readers. Its OSError text holds the reason of the `processes:` line;
     test_ac02_darwin_host_lines.py checks the whole line.
D11. find_terminal_paths_darwin(applications, program_files, home, never_listed) is called with
     applications = (<base>/Applications, <home>/Applications), program_files = () and never_listed =
     (<home>/Library, <home>/.ssh), all Path; it returns (found paths as str, search complete, skipped
     folders as str).
"""

import errno
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_kit():
    name, path = "darwinkit_env002", Path(__file__).resolve().parent / "darwinkit.py"
    module = sys.modules.get(name)
    if module is None or getattr(module, "__file__", None) != str(path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


D = _load_kit()
K = D.K
AC = "AC-02"
OWN_PID = 4242
OWN_PATH = "/Users/x/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/bin/python3.12"
LAUNCHD = "/sbin/launchd"


# ------------------------------------------------------------------------- constants and reader_name

def test_ac02_mnt_local_and_sf_dataless_are_the_sdk_values():
    """v2.1 F2, v2.3 r3 F44: int constants in envcheck, not imported from stat."""
    ec = K.envcheck(AC, "MNT_LOCAL", "SF_DATALESS")
    wrong = []
    for name, expected in (("MNT_LOCAL", 0x00001000), ("SF_DATALESS", 0x40000000)):
        value = getattr(ec, name)
        if type(value) is not int or value != expected:
            wrong.append(f"{name} is {value!r}, expected the int {expected:#010x}")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


@pytest.mark.parametrize("platform, expected", (("win32", "win32"), ("darwin", "darwin"), ("linux", "none"),
                                                ("cygwin", "none"), ("freebsd14", "none")))
def test_ac02_reader_name_follows_sys_platform_at_call_time(monkeypatch, platform, expected):
    """v2.1 F1: reader_name() is win32, darwin or none, from sys.platform read when it is called."""
    ec = K.envcheck(AC, "reader_name", "sys")
    monkeypatch.setattr(ec.sys, "platform", platform)
    got = ec.reader_name()
    assert got == expected, f"AC-02: reader_name() gave {got!r} on {platform}, expected {expected!r}"


# ------------------------------------------------------------------------- is_cloud_only and st_flags

_FLAGS = (
    ("st_flags with SF_DATALESS only", {"st_flags": 0x40000000}, True),
    ("st_flags with SF_DATALESS and other bits", {"st_flags": 0x40000000 | 0x00000020}, True),
    ("st_flags with other bits only", {"st_flags": 0x00000020 | 0x00008000}, False),
    ("neither st_flags nor st_file_attributes", {}, False),
)


@pytest.mark.parametrize("label, extra, expected", _FLAGS, ids=[case[0] for case in _FLAGS])
def test_ac02_is_cloud_only_reads_the_dataless_flag(tmp_path, monkeypatch, label, extra, expected):
    """v2.1 F6: one function on every platform; SF_DATALESS (0x40000000) in st_flags is cloud-only."""
    ec = K.envcheck(AC, "is_cloud_only", "SF_DATALESS")
    target = K.put(tmp_path / "iCloud" / "file.json", "{}\n")
    real_stat = os.stat

    def fake_stat(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if isinstance(path, int) or K.norm(path) != K.norm(target):
            return result
        values = {name: getattr(result, name) for name in ("st_mode", "st_ino", "st_dev", "st_nlink", "st_uid",
                                                           "st_gid", "st_size", "st_atime", "st_mtime", "st_ctime")}
        return SimpleNamespace(**values, **extra)

    monkeypatch.setattr(os, "stat", fake_stat)
    with K.recording() as audit:
        answers = [ec.is_cloud_only(target), ec.is_cloud_only(str(target))]
    wrong = []
    if answers != [expected, expected]:
        wrong.append(f"is_cloud_only gave {answers} for Path and str, expected {expected}")
    if K.norm(target) in audit.opened():
        wrong.append("is_cloud_only opened the file")
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- classify_mounts

def _root(local):
    return ("apfs", "/dev/disk3s1s1", "/", local | D.MNT_RDONLY)


def _devfs(local):
    return ("devfs", "devfs", "/dev", local)


def _auto_home(point="/System/Volumes/Data/home", source="map auto_home"):
    return ("autofs", source, point, D.OTHER_FLAGS)


_SMBFS = ("smbfs", "//guest@vps.example/share", "/Volumes/share", 0)
_SMBFS_LINE = "smbfs //guest@vps.example/share on /Volumes/share"
_AT = D.ALLOWED_POINT

_MOUNTS = (
    # (label, build(MNT_LOCAL) -> entries, expected item result, checks)
    ("only / apfs, /dev devfs and autofs from map auto_home (PASS)", lambda L: D.base_mounts(L), "PASS", {}),
    ("devfs at /dev (PASS)", lambda L: [_root(L), _devfs(L)], "PASS", {}),
    ("autofs from map auto_home without MNT_LOCAL (PASS)", lambda L: [_root(L), _auto_home()], "PASS", {}),
    ("smbfs at /Volumes/share (FAIL; the FAIL rule comes first)",
     lambda L: D.base_mounts(L, _SMBFS), "FAIL", {"remote": (_SMBFS_LINE,), "not_allowed": ()}),
    ("nfs (FAIL)", lambda L: D.base_mounts(L, ("nfs", "vps.example:/vault", "/Volumes/vault", 0)), "FAIL",
     {"remote": ("nfs vps.example:/vault on /Volumes/vault",)}),
    ("afpfs (FAIL)", lambda L: D.base_mounts(L, ("afpfs", "//x@vps.example/vault", "/Volumes/vault", 0)), "FAIL",
     {"remote": ("afpfs //x@vps.example/vault on /Volumes/vault",)}),
    ("webdav (FAIL)", lambda L: D.base_mounts(L, ("webdav", "https://vps.example/vault", "/Volumes/vault", 0)), "FAIL",
     {"remote": ("webdav https://vps.example/vault on /Volumes/vault",)}),
    ("ftp (FAIL)", lambda L: D.base_mounts(L, ("ftp", "ftp://vps.example/", "/Volumes/vps.example", 0)), "FAIL",
     {"remote": ("ftp ftp://vps.example/ on /Volumes/vps.example",)}),
    ("apfs without MNT_LOCAL (FAIL)", lambda L: D.base_mounts(L, ("apfs", "/dev/disk5s1", _AT, 0)), "FAIL",
     {"remote": (f"apfs /dev/disk5s1 on {_AT}",)}),
    ("a type outside both lists with MNT_LOCAL (UNKNOWN)",
     lambda L: D.base_mounts(L, ("macfuse", "fuse-t:/x", _AT, L)), "UNKNOWN", {"not_allowed": ()}),
    ("ntfs with MNT_LOCAL (UNKNOWN)", lambda L: D.base_mounts(L, ("ntfs", "/dev/disk6s1", _AT, L)), "UNKNOWN",
     {"not_allowed": ()}),
    ("lifs with MNT_LOCAL (UNKNOWN)", lambda L: D.base_mounts(L, ("lifs", "/dev/disk6s1", _AT, L)), "UNKNOWN",
     {"not_allowed": ()}),
    ("ntfs without MNT_LOCAL (FAIL)", lambda L: D.base_mounts(L, ("ntfs", "/dev/disk6s1", _AT, 0)), "FAIL",
     {"remote": (f"ntfs /dev/disk6s1 on {_AT}",)}),
    ("lifs without MNT_LOCAL (FAIL)", lambda L: D.base_mounts(L, ("lifs", "/dev/disk6s1", _AT, 0)), "FAIL",
     {"remote": (f"lifs /dev/disk6s1 on {_AT}",)}),
    ("apfs with MNT_LOCAL at /Volumes/USB (UNKNOWN)",
     lambda L: D.base_mounts(L, ("apfs", "/dev/disk4s1", "/Volumes/USB", L)), "UNKNOWN",
     {"not_allowed": ("/Volumes/USB",)}),
    ("apfs with MNT_LOCAL at /System/Volumes/Data (PASS)",
     lambda L: D.base_mounts(L, ("apfs", "/dev/disk3s5", "/System/Volumes/Data", L)), "PASS", {}),
    ("apfs with MNT_LOCAL at /Users/x/mnt (UNKNOWN)",
     lambda L: D.base_mounts(L, ("apfs", "/dev/disk4s1", "/Users/x/mnt", L)), "UNKNOWN",
     {"not_allowed": ("/Users/x/mnt",)}),
    ("apfs with MNT_LOCAL at /System/Volumes/Data/Users/x/mnt (UNKNOWN)",
     lambda L: D.base_mounts(L, ("apfs", "/dev/disk4s1", "/System/Volumes/Data/Users/x/mnt", L)), "UNKNOWN",
     {"not_allowed": ("/System/Volumes/Data/Users/x/mnt",)}),
    ("apfs with MNT_LOCAL at /System/Volumes/Preboot (PASS)",
     lambda L: D.base_mounts(L, ("apfs", "/dev/disk3s6", "/System/Volumes/Preboot", L)), "PASS", {}),
    ("autofs from map -fstab (UNKNOWN)", lambda L: D.base_mounts(L, _auto_home(source="map -fstab")), "UNKNOWN",
     {"not_allowed": ()}),
    ("autofs from map -static (UNKNOWN)", lambda L: D.base_mounts(L, _auto_home(source="map -static")), "UNKNOWN",
     {"not_allowed": ()}),
    ("autofs from map -hosts (UNKNOWN)", lambda L: D.base_mounts(L, _auto_home(source="map -hosts")), "UNKNOWN",
     {"not_allowed": ()}),
    ("autofs from map auto_home at /home (UNKNOWN: outside the allow list)",
     lambda L: D.base_mounts(L, _auto_home(point="/home")), "UNKNOWN", {"not_allowed": ("/home",)}),
    ("no mount at / (UNKNOWN)", lambda L: [_devfs(L), _auto_home()], "UNKNOWN", {"root": "missing"}),
    ("/ is hfs with MNT_LOCAL (UNKNOWN)", lambda L: [("hfs", "/dev/disk2s1", "/", L), _devfs(L), _auto_home()],
     "UNKNOWN", {"root": "hfs"}),
    ("/ is apfs without MNT_LOCAL (FAIL)",
     lambda L: [("apfs", "/dev/disk3s1s1", "/", D.MNT_RDONLY), _devfs(L), _auto_home()], "FAIL",
     {"remote": ("apfs /dev/disk3s1s1 on /",), "root": None}),
    ("/ is nfs (FAIL)", lambda L: [("nfs", "vps.example:/", "/", 0), _devfs(L), _auto_home()], "FAIL",
     {"remote": ("nfs vps.example:/ on /",)}),
    ("a FAIL mount beside an UNKNOWN mount (FAIL)",
     lambda L: D.base_mounts(L, _SMBFS, ("apfs", "/dev/disk4s1", "/Volumes/USB", L)), "FAIL",
     {"remote": (_SMBFS_LINE,), "resources": None, "not_allowed": ("/Volumes/USB",)}),
)


def _mount_problems(result, expected, checks):
    if not (isinstance(result, tuple) and len(result) == 4):
        return [f"classify_mounts returned {result!r}, expected a tuple of four parts"]
    drives, resources, outside, root = result
    wrong = []
    if not (isinstance(drives, tuple) and all(isinstance(text, str) for text in drives)):
        wrong.append(f"remote_drives {drives!r} is not a tuple of str")
    if resources is not None and resources != ():
        wrong.append(f"connected_resources {resources!r}, expected () or None (D9)")
    got = "FAIL" if drives else "UNKNOWN" if resources is None else "PASS"
    if got != expected:
        wrong.append(f"item result {got} from {result!r}, expected {expected}")
    if "remote" in checks and tuple(drives or ()) != checks["remote"]:
        wrong.append(f"remote_drives {drives!r}, expected {checks['remote']!r}")
    if "resources" in checks and resources != checks["resources"]:
        wrong.append(f"connected_resources {resources!r}, expected {checks['resources']!r}")
    if "not_allowed" in checks and tuple(outside or ()) != checks["not_allowed"]:
        wrong.append(f"mount points not allowed {outside!r}, expected {checks['not_allowed']!r}")
    if "root" in checks and root != checks["root"]:
        wrong.append(f"root problem {root!r}, expected {checks['root']!r}")
    if expected == "PASS" and (tuple(outside or ()) != () or root is not None):
        wrong.append(f"a PASS list reports not allowed {outside!r} and root {root!r}")
    return wrong


@pytest.mark.parametrize("label, build, expected, checks", _MOUNTS, ids=[case[0] for case in _MOUNTS])
def test_ac02_classify_mounts(label, build, expected, checks):
    """v2.1 F12, F15, F19; v2.2 r2 F26, F32; v2.3 r3 F32, F45; v2.4 r4 F53: every rule of network_shares."""
    ec = K.envcheck(AC, "classify_mounts", "MNT_LOCAL")
    entries = tuple(build(ec.MNT_LOCAL))
    result = ec.classify_mounts(entries)
    wrong = _mount_problems(result, expected, checks)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- classify_processes

_UV_PYTHON = OWN_PATH
_PROCESSES = (
    # (label, paths, paths that must be in the terminal part (() = the part is empty), names, wine loaders)
    ("ordinary processes (PASS)", (LAUNCHD, D.LOGD, _UV_PYTHON), (), ("launchd", "logd", "python3.12"), 0),
    ("wine64-preloader outside any metatrader folder (UNKNOWN)", (LAUNCHD, "/usr/local/bin/wine64-preloader"), (),
     None, 1),
    ("wineserver outside any metatrader folder (UNKNOWN)", (LAUNCHD, "/usr/local/bin/wineserver"), (), None, 1),
    ("a Wine loader name in mixed case (UNKNOWN)", (LAUNCHD, "/opt/wine/bin/Wine64-Preloader"), (), None, 1),
    ("wine64-preloader under /Users/x/MetaTrader 5/bin (FAIL, no Wine loader)",
     (LAUNCHD, "/Users/x/MetaTrader 5/bin/wine64-preloader"), ("/Users/x/MetaTrader 5/bin/wine64-preloader",),
     ("launchd", "wine64-preloader"), 0),
    ("python under /Users/x/dev/metatrader-notes (FAIL, the strict rule)",
     (LAUNCHD, "/Users/x/dev/metatrader-notes/.venv/bin/python"), ("/Users/x/dev/metatrader-notes/.venv/bin/python",),
     ("launchd", "python"), 0),
    ("a process under MetaTrader 5.app (FAIL)", (LAUNCHD, "/Applications/MetaTrader 5.app/Contents/MacOS/terminal"),
     ("/Applications/MetaTrader 5.app/Contents/MacOS/terminal",), ("launchd", "terminal"), 0),
    ("a process under Exness MetaTrader 5.app outside /Applications (FAIL)",
     (LAUNCHD, "/Users/x/Downloads/Exness MetaTrader 5.app/Contents/MacOS/Exness MT5"),
     ("/Users/x/Downloads/Exness MetaTrader 5.app/Contents/MacOS/Exness MT5",), ("Exness MT5", "launchd"), 0),
    ("terminal64.exe (FAIL)", (LAUNCHD, "/Users/x/Downloads/mt5/terminal64.exe"),
     ("/Users/x/Downloads/mt5/terminal64.exe",), ("launchd", "terminal64.exe"), 0),
    ("TERMINAL64.EXE in upper case (FAIL)", (LAUNCHD, "/Users/x/Downloads/MT5/TERMINAL64.EXE"),
     ("/Users/x/Downloads/MT5/TERMINAL64.EXE",), ("TERMINAL64.EXE", "launchd"), 0),
    ("terminal64.exe beside wineserver (FAIL: its path is kept)",
     ("/usr/local/bin/wineserver", "/Users/x/.wine/drive_c/Program Files/MT5/terminal64.exe"),
     ("/Users/x/.wine/drive_c/Program Files/MT5/terminal64.exe",), None, 1),
)


@pytest.mark.parametrize("label, paths, terminal, names, loaders", _PROCESSES, ids=[case[0] for case in _PROCESSES])
def test_ac02_classify_processes(label, paths, terminal, names, loaders):
    """v2.1 F7; v2.2 r2 F30; v2.3 r3 F33; v2.4 r4 F53: the process rules of terminal_install."""
    ec = K.envcheck(AC, "classify_processes")
    result = ec.classify_processes(tuple(paths))
    if not (isinstance(result, tuple) and len(result) == 3):
        pytest.fail(f"AC-02 {label}: classify_processes returned {result!r}, expected three parts", pytrace=False)
    found, got_names, got_loaders = result
    wrong = []
    if terminal == () and tuple(found or ()) != ():
        wrong.append(f"terminal paths {found!r}, expected none")
    missing = [path for path in terminal if path not in tuple(found or ())]
    if missing:
        wrong.append(f"terminal paths {found!r} lack {missing}")
    if names is None and got_names is not None:
        wrong.append(f"process_names {got_names!r}, expected None (a Wine loader runs)")
    if names is not None and (got_names is None or sorted(got_names) != sorted(names)):
        wrong.append(f"process_names {got_names!r}, expected the basenames {sorted(names)}")
    if got_loaders != loaders:
        wrong.append(f"{got_loaders!r} Wine loaders, expected {loaders}")
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- read_process_paths

class _Pids:
    """Fake _darwin_list_pids and _darwin_pid_path over a table {pid: (path or None, errno)} (D3)."""

    def __init__(self, table, list_error=None):
        self.table = dict(table)
        self.list_error = list_error
        self.capacities = []

    def list_pids(self, capacity):
        self.capacities.append(capacity)
        if self.list_error is not None:
            raise self.list_error
        pids = tuple(self.table)
        if len(pids) >= capacity:
            return capacity, pids[:capacity]
        return len(pids), pids

    def pid_path(self, pid):
        return self.table.get(pid, (None, errno.ESRCH))

    def install(self, monkeypatch, ec):
        monkeypatch.setattr(ec, "_darwin_list_pids", self.list_pids)
        monkeypatch.setattr(ec, "_darwin_pid_path", self.pid_path)
        return self


class _GrowingPids(_Pids):
    """The first call decides the table: three more pids than its buffer holds, this process last."""

    def list_pids(self, capacity):
        if not self.table:
            size = max(capacity, 1)
            self.table = {0: (None, errno.ESRCH)}
            self.table.update({1000 + index: (f"/usr/libexec/fake{index}", 0) for index in range(size + 1)})
            self.table[OWN_PID] = (OWN_PATH, 0)
        return super().list_pids(capacity)


_ESRCH, _ENOMEM, _EPERM = errno.ESRCH, errno.ENOMEM, errno.EPERM
_OWN = (OWN_PATH, 0)
_UNREADABLE_PROCESSES = (
    # (label, table, reason in the OSError text)
    ("the list lacks this process", {0: (None, _ESRCH), 1: (LAUNCHD, 0), 333: (D.LOGD, 0)}, "own pid missing, 3 pids"),
    ("this process has another path", {0: (None, _ESRCH), 1: (LAUNCHD, 0), OWN_PID: ("/usr/bin/python3", 0)},
     "own path differs, 3 pids"),
    ("proc_pidpath fails with ENOMEM", {0: (None, _ESRCH), OWN_PID: _OWN, 333: (None, _ENOMEM)},
     f"errno {_ENOMEM} on pid 333, 3 pids"),
    ("proc_pidpath fails with EPERM", {0: (None, _ESRCH), OWN_PID: _OWN, 333: (None, _EPERM)},
     f"errno {_EPERM} on pid 333, 3 pids"),
    ("proc_listallpids returns 0", {}, "listed 0 pids"),
)


@pytest.mark.parametrize("label, table, reason", _UNREADABLE_PROCESSES, ids=[case[0] for case in _UNREADABLE_PROCESSES])
def test_ac02_read_process_paths_raises_when_the_list_cannot_be_trusted(monkeypatch, label, table, reason):
    """v2.1 F7; v2.2 r2 F4, F7: read_process_paths raises OSError whose text is the reason (D10)."""
    ec = K.envcheck(AC, "read_process_paths", "_darwin_list_pids", "_darwin_pid_path")
    _Pids(table).install(monkeypatch, ec)
    try:
        result = ec.read_process_paths(OWN_PID, OWN_PATH)
    except OSError as error:
        assert reason in str(error), f"AC-02 {label}: OSError {str(error)!r} does not give {reason!r}"
        return
    pytest.fail(f"AC-02 {label}: read_process_paths returned {result!r}, expected OSError", pytrace=False)


def test_ac02_read_process_paths_raises_when_proc_listallpids_fails(monkeypatch):
    ec = K.envcheck(AC, "read_process_paths", "_darwin_list_pids", "_darwin_pid_path")
    _Pids({OWN_PID: _OWN}, list_error=OSError(errno.EIO, "proc_listallpids failed")).install(monkeypatch, ec)
    with pytest.raises(OSError):
        ec.read_process_paths(OWN_PID, OWN_PATH)


_SKIPPED = (
    # (label, table, expected paths, listed, skipped)
    ("a process that ended (ESRCH) is skipped", {0: (None, _ESRCH), 1: (LAUNCHD, 0), 333: (None, _ESRCH), OWN_PID: _OWN},
     {LAUNCHD, OWN_PATH}, 4, 2),
    ("pid 0 is skipped whatever proc_pidpath says", {0: (None, _EPERM), OWN_PID: _OWN, 333: (D.LOGD, 0)},
     {OWN_PATH, D.LOGD}, 3, 1),
)


@pytest.mark.parametrize("label, table, paths, listed, skipped", _SKIPPED, ids=[case[0] for case in _SKIPPED])
def test_ac02_read_process_paths_skips_pid_0_and_ended_processes(monkeypatch, label, table, paths, listed, skipped):
    """v2.1 F7; v2.3 r3 F25: (paths read, pids listed, pids skipped)."""
    ec = K.envcheck(AC, "read_process_paths", "_darwin_list_pids", "_darwin_pid_path")
    _Pids(table).install(monkeypatch, ec)
    result = ec.read_process_paths(OWN_PID, OWN_PATH)
    expected = (paths, listed, skipped)
    got = (set(result[0]), result[1], result[2]) if isinstance(result, tuple) and len(result) == 3 else result
    assert got == expected, f"AC-02 {label}: read_process_paths gave {result!r}, expected {expected!r}"


def test_ac02_read_process_paths_grows_a_full_buffer_until_the_list_fits(monkeypatch):
    """v2.1 F7: a count equal to the buffer's capacity is a cut list; the buffer grows and the read repeats."""
    ec = K.envcheck(AC, "read_process_paths", "_darwin_list_pids", "_darwin_pid_path")
    fake = _GrowingPids({}).install(monkeypatch, ec)
    result = ec.read_process_paths(OWN_PID, OWN_PATH)
    total = len(fake.table)
    wrong = []
    if len(fake.capacities) < 2 or fake.capacities[-1] <= total:
        wrong.append(f"capacities {fake.capacities} for {total} pids: the cut list was not read again with room")
    if any(later <= earlier for earlier, later in zip(fake.capacities, fake.capacities[1:])):
        wrong.append(f"capacities {fake.capacities} do not grow")
    shaped = isinstance(result, tuple) and len(result) == 3
    if not (shaped and result[1] == total and result[2] == 1 and OWN_PATH in result[0]
            and len(result[0]) == total - 1):
        brief = (len(result[0]), result[1], result[2]) if shaped else result
        wrong.append(f"(paths read, listed, skipped) = {brief!r}, expected ({total - 1} with this process, "
                     f"{total}, 1)")
    assert not wrong, "AC-02 a full pid buffer:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- read_mounts

def test_ac02_read_mounts_grows_a_full_buffer_until_the_list_fits(monkeypatch):
    """v2.2 r2 F31: getfsstat fills at most the buffer it gets; a full buffer is read again with room."""
    ec = K.envcheck(AC, "read_mounts", "_darwin_mounts", "MNT_LOCAL")
    state = {"table": None, "capacities": []}

    def fake_mounts(capacity):
        state["capacities"].append(capacity)
        if state["table"] is None:
            extra = [("devfs", "devfs", f"/dev/fake{index}", ec.MNT_LOCAL) for index in range(max(capacity, 1))]
            state["table"] = tuple(D.base_mounts(ec.MNT_LOCAL, *extra))
        table = state["table"]
        if len(table) >= capacity:
            return capacity, table[:capacity]
        return len(table), table

    monkeypatch.setattr(ec, "_darwin_mounts", fake_mounts)
    result = ec.read_mounts()
    table, capacities = state["table"], state["capacities"]
    wrong = []
    if len(capacities) < 2 or capacities[-1] <= len(table):
        wrong.append(f"capacities {capacities} for {len(table)} mounts: the cut list was not read again with room")
    if tuple(tuple(entry) for entry in result) != table:
        wrong.append(f"read_mounts gave {len(result)} entries, expected the {len(table)} of the full table in order")
    assert not wrong, "AC-02 a full mount buffer:\n" + "\n".join(wrong)


def test_ac02_read_mounts_raises_when_getfsstat_fails(monkeypatch):
    ec = K.envcheck(AC, "read_mounts", "_darwin_mounts")

    def fake_mounts(capacity):
        raise OSError(errno.EIO, "getfsstat failed")

    monkeypatch.setattr(ec, "_darwin_mounts", fake_mounts)
    with pytest.raises(OSError):
        ec.read_mounts()


# ------------------------------------------------------------------------- wine_prefixes

def _norms(paths, lower=False):
    texts = [K.norm(path) for path in paths]
    return [text.lower() for text in texts] if lower else texts


def test_ac02_wine_prefixes_finds_prefixes_sources_and_program_files(tmp_path):
    """v2.4 r4 F53: ~/.wine and a PlayOnMac prefix give 2 prefixes, 2 sources in the contract's order, 2 roots."""
    ec = K.envcheck(AC, "wine_prefixes", "find_wine_program_files")
    home = tmp_path / "Users" / "x"
    wine_root = home / ".wine" / "drive_c" / "Program Files"
    playonmac = home / "Library" / "PlayOnMac" / "wineprefix"
    pol_root = playonmac / "p1" / "drive_c" / "Program Files"
    for folder in (wine_root, pol_root, home / "Library" / "Application Support"):
        folder.mkdir(parents=True)
    result = ec.wine_prefixes(home)
    wrong = []
    if not (isinstance(result, tuple) and len(result) == 3):
        pytest.fail(f"AC-02: wine_prefixes returned {result!r}, expected three parts", pytrace=False)
    prefixes, sources, roots = result
    if sorted(_norms(prefixes)) != sorted(_norms((home / ".wine", playonmac / "p1"))):
        wrong.append(f"prefixes {prefixes!r}")
    if _norms(sources) != _norms((playonmac, home / ".wine")):
        wrong.append(f"sources {sources!r}, expected ~/Library/PlayOnMac/wineprefix then ~/.wine")
    if sorted(_norms(roots)) != sorted(_norms((wine_root, pol_root))):
        wrong.append(f"Program Files roots {roots!r}")
    other = ec.find_wine_program_files(home)
    if sorted(_norms(other)) != sorted(_norms(roots)):
        wrong.append(f"find_wine_program_files gave {other!r}, expected the third part {roots!r}")
    assert not wrong, "AC-02 wine_prefixes:\n" + "\n".join(wrong)


def test_ac02_wine_prefixes_matches_a_winePrefix_folder_in_another_case(tmp_path):
    """v2.1 F9: the PlayOnMac wineprefix folder compares without case (the same prefix is found)."""
    ec = K.envcheck(AC, "wine_prefixes")
    home = tmp_path / "Users" / "x"
    root = home / "Library" / "PlayOnMac" / "WinePrefix" / "p1" / "drive_c" / "Program Files"
    root.mkdir(parents=True)
    prefixes, sources, roots = ec.wine_prefixes(home)
    wrong = []
    if _norms(prefixes, lower=True) != _norms((root.parents[1],), lower=True):
        wrong.append(f"prefixes {prefixes!r}, expected the WinePrefix/p1 prefix")
    if _norms(roots, lower=True) != _norms((root,), lower=True):
        wrong.append(f"roots {roots!r}, expected {root}")
    if _norms(sources, lower=True) != _norms((root.parents[2],), lower=True):
        wrong.append(f"sources {sources!r}, expected the WinePrefix folder")
    assert not wrong, "AC-02 WinePrefix:\n" + "\n".join(wrong)


def test_ac02_wine_prefixes_of_a_home_without_wine_is_empty(tmp_path):
    """v2.0: no Wine prefix at all is no error (PASS, not UNKNOWN)."""
    ec = K.envcheck(AC, "wine_prefixes")
    home = tmp_path / "Users" / "x"
    (home / "Library" / "Application Support").mkdir(parents=True)
    result = ec.wine_prefixes(home)
    assert tuple(tuple(part) for part in result) == ((), (), ()), f"AC-02: wine_prefixes gave {result!r}"


# ------------------------------------------------------------------------- find_terminal_paths_darwin

def _home(tmp_path):
    home = tmp_path / "Users" / "x"
    for folder in ("Desktop", "Documents/projects", "Music", "Pictures/Photos Library.photoslibrary/database",
                   "Library/Application Support/Code", ".ssh", ".Trash"):
        (home / folder).mkdir(parents=True, exist_ok=True)
    K.put(home / "Documents" / "projects" / "notes.txt", "x\n")
    applications = tmp_path / "Applications"
    (applications / "Safari.app" / "Contents").mkdir(parents=True)
    return home, applications


def _search(ec, monkeypatch, home, applications, *, cloud=(), deny_list=()):
    monkeypatch.setattr(ec, "is_cloud_only", K.cloud_only(cloud))
    with K.recording(deny_list=deny_list) as audit:
        result = ec.find_terminal_paths_darwin((applications, home / "Applications"), (), home,
                                               (home / "Library", home / ".ssh"))
    if not (isinstance(result, tuple) and len(result) == 3):
        pytest.fail(f"AC-02: find_terminal_paths_darwin returned {result!r}, expected three parts", pytrace=False)
    return result, audit


def test_ac02_home_search_never_lists_library_and_ssh(tmp_path, monkeypatch):
    """v2.1 F12; v2.4 r4 F49: never_listed paths are not listed; a folder named Library elsewhere is."""
    ec = K.envcheck(AC, "find_terminal_paths_darwin", "is_cloud_only")
    home, applications = _home(tmp_path)
    K.put(home / "Library" / "Wine" / "terminal64.exe", b"MZ synthetic")
    K.put(home / ".ssh" / "terminal64.exe", b"MZ synthetic")
    elsewhere = K.put(home / "Projects" / "Library" / "terminal64.exe", b"MZ synthetic")
    (found, complete, skipped), audit = _search(ec, monkeypatch, home, applications)
    wrong = D.touched_under(audit, home / "Library") + D.touched_under(audit, home / ".ssh")
    if sorted(_norms(found)) != [K.norm(elsewhere)]:
        wrong.append(f"found {found!r}, expected only {elsewhere} (paths compare, not names)")
    if complete is not True:
        wrong.append(f"complete is {complete!r}, expected True")
    assert not wrong, "AC-02 never_listed:\n" + "\n".join(wrong)


def test_ac02_home_search_lists_tool_folders_and_finds_terminal64_under_colima(tmp_path, monkeypatch):
    """v2.4 r4 F49: the home search does not skip .colima; <home>/.colima/x/terminal64.exe is found."""
    ec = K.envcheck(AC, "find_terminal_paths_darwin", "is_cloud_only")
    home, applications = _home(tmp_path)
    target = K.put(home / ".colima" / "x" / "terminal64.exe", b"MZ synthetic")
    (found, complete, _), _ = _search(ec, monkeypatch, home, applications)
    assert K.norm(target) in _norms(found) and complete is True, \
        f"AC-02: found {found!r}, complete {complete!r}; expected {target} and a complete search"


_SKIP_LIST = (".Trash", "Pictures/Photos Library.photoslibrary")


@pytest.mark.parametrize("relative", _SKIP_LIST)
def test_ac02_home_search_skips_the_measured_unlistable_folders(tmp_path, monkeypatch, relative):
    """v2.1 F10: a folder of the skip list that cannot be listed is skipped and reported, the search is complete."""
    ec = K.envcheck(AC, "find_terminal_paths_darwin", "is_cloud_only")
    home, applications = _home(tmp_path)
    folder = home / relative
    (found, complete, skipped), _ = _search(ec, monkeypatch, home, applications, deny_list=[folder])
    wrong = []
    if tuple(found) != () or complete is not True:
        wrong.append(f"found {found!r}, complete {complete!r}; expected nothing and a complete search")
    if K.norm(folder) not in _norms(skipped):
        wrong.append(f"skipped {skipped!r} lacks {folder}")
    assert not wrong, f"AC-02 skip list {relative}:\n" + "\n".join(wrong)


_INCOMPLETE = (
    ("another folder under home", lambda home: home / "Music"),
    ("a folder named .Trash that is not ~/.Trash (paths compare)", lambda home: home / "Documents" / ".Trash"),
    ("the home folder itself", lambda home: home),
)


@pytest.mark.parametrize("label, pick", _INCOMPLETE, ids=[case[0] for case in _INCOMPLETE])
def test_ac02_home_search_is_incomplete_when_a_folder_cannot_be_listed(tmp_path, monkeypatch, label, pick):
    """v2.1 F10, F12; v2.3 r3 F30: any other unlistable folder makes the search incomplete."""
    ec = K.envcheck(AC, "find_terminal_paths_darwin", "is_cloud_only")
    home, applications = _home(tmp_path)
    (home / "Documents" / ".Trash").mkdir()
    (found, complete, _), _ = _search(ec, monkeypatch, home, applications, deny_list=[pick(home)])
    assert complete is False and tuple(found) == (), \
        f"AC-02 {label}: found {found!r}, complete {complete!r}; expected nothing found and an incomplete search"


def test_ac02_home_search_keeps_what_it_found_beside_an_unlistable_folder(tmp_path, monkeypatch):
    """v2.2 r2 F30: a path found stays in the result when the search is incomplete."""
    ec = K.envcheck(AC, "find_terminal_paths_darwin", "is_cloud_only")
    home, applications = _home(tmp_path)
    target = K.put(home / "Desktop" / "MT5" / "terminal64.exe", b"MZ synthetic")
    (found, complete, _), _ = _search(ec, monkeypatch, home, applications, deny_list=[home / "Music"])
    assert K.norm(target) in _norms(found) and complete is False, \
        f"AC-02: found {found!r}, complete {complete!r}; expected {target} and an incomplete search"


def test_ac02_home_search_skips_a_dataless_folder_without_listing_it(tmp_path, monkeypatch):
    """v2.1 F6; v2.2 r2 F12: a dataless folder under home is not listed and is reported as skipped."""
    ec = K.envcheck(AC, "find_terminal_paths_darwin", "is_cloud_only")
    home, applications = _home(tmp_path)
    folder = home / "Music" / "Archive"
    K.put(folder / "terminal64.exe", b"MZ synthetic")
    (found, complete, skipped), audit = _search(ec, monkeypatch, home, applications, cloud=[folder])
    wrong = D.touched_under(audit, folder)
    if tuple(found) != () or complete is not True:
        wrong.append(f"found {found!r}, complete {complete!r}; expected nothing and a complete search")
    if K.norm(folder) not in _norms(skipped):
        wrong.append(f"skipped {skipped!r} lacks {folder}")
    assert not wrong, "AC-02 dataless folder under home:\n" + "\n".join(wrong)
