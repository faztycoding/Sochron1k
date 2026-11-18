r"""ENV-002 v2.6 contract tests for AC-02, macOS cases at the level of collect and default_roots
(docs/contracts/ENV-002-research-host-separation.md, "v2.0 (ร่าง, D-023): ตัวอ่านตามแพลตฟอร์ม",
"default_roots บน darwin", the darwin item rules and the Negative cases marked (v2.0) and later); run
pytest from the repository root.

Contract v2.1 F4: the collect-level cases (applications, Wine prefixes, levels of terminal64.exe,
processes, mounts, other platforms) call collect for real with envcheck.sys.platform set and the raw
readers replaced. Each case here builds one wrong state on the fake Mac of darwinkit.py, runs collect,
then evaluate on the same roots, and expects the item results the contract gives (D5); the other items
stay PASS. Conventions D1-D8 are in darwinkit.py; the ones below are specific to this file:
D12. A case's roots are built by hand like default_roots builds them: program_files holds the
     drive_c/Program Files* folders of the prefixes the case makes (collect also finds them itself,
     contract v2.3 r3 F25). appdata is <home>/Library/Application Support unless the case moves it.
D13. "Looks at names only, never enters" (the application rule, the terminal_data rule) is checked as no
     listing and no open at or under the matching folder while collect runs (D6). The home search may
     list ~/Applications, so that check is made for /Applications and Application Support only.
"""

import errno
import importlib.util
import os
import sys
from pathlib import Path

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
TOKEN = K.TOKEN
EXE = b"MZ synthetic"


def _host(tmp_path, monkeypatch, build=None, *, platform="darwin", machine="arm64"):
    """The fake Mac with its fake OS installed; build(mac, fake) makes the case's state and returns options."""
    ec = D.reader(AC)
    mac = D.Mac(tmp_path)
    fake = D.FakeOS(ec, mac)
    fake.machine = machine
    options = (build(mac, fake) if build else None) or {}
    fake.install(monkeypatch, ec, platform=platform, cloud=options.get("cloud", ()))
    return ec, mac, fake, options


# ------------------------------------------------------------------------- case builders

def _app(folder, name, *, untouched=True):
    bundle = folder / name
    K.put(bundle / "Contents" / "MacOS" / "app", b"\xcf\xfa\xed\xfe synthetic")
    return {"untouched": [bundle]} if untouched else {}


def _terminal(path, **options):
    K.put(path, EXE)
    return options


def _wine_terminal(source, levels):
    def build(mac, fake):
        root = mac.program_files_root(source)
        K.put(root.joinpath(*("Vendor", "MT5", "bin")[:levels], "terminal64.exe"), EXE)
        return {"program_files": (root,)}
    return build


def _metatrader_in_program_files(mac, fake):
    root = mac.program_files_root("wine")
    (root / "MetaTrader 5").mkdir()
    return {"program_files": (root,)}


def _unlistable_in_program_files(mac, fake):
    root = mac.program_files_root("PlayOnMac")
    folder = root / "Vendor"
    K.put(folder / "readme.txt", "x\n")
    return {"program_files": (root,), "deny_list": [folder]}


def _support(name):
    def build(mac, fake):
        folder = mac.appsupport / name
        K.put(folder / "config" / "common.ini", "[Common]\n")
        return {"untouched": [folder]}
    return build


def _process(*paths):
    def build(mac, fake):
        for index, path in enumerate(paths):
            fake.table[501 + index] = (path, 0)
        return {}
    return build


def _unreadable_process_list(mac, fake):
    fake.list_error = OSError(errno.EIO, "proc_listallpids failed")
    return {"facts": {"process_names": None}}


def _mount(entry):
    def build(mac, fake):
        fake.mounts.append(entry(fake.local))
        return {}
    return build


def _failing_getfsstat(mac, fake):
    fake.mount_error = OSError(errno.EIO, "getfsstat failed")
    return {}


def _skip_listed(relative):
    def build(mac, fake):
        folder = mac.home / relative
        folder.mkdir(parents=True, exist_ok=True)
        return {"deny_list": [folder]}
    return build


def _dataless_under_home(mac, fake):
    folder = mac.home / "Music" / "Archive"
    K.put(folder / "terminal64.exe", EXE)
    return {"cloud": [folder], "untouched": [folder]}


_TI, _TD, _NS = ("terminal_install",), ("terminal_data",), ("network_shares",)

_COLLECT = (
    # (label, build(mac, fake) -> options, fail, unknown)
    # Applications (v2.0; v2.1 F8; v2.2 r2 F12, r2 F33)
    ("MetaTrader 5.app in /Applications (FAIL)", lambda m, f: _app(m.applications, "MetaTrader 5.app"), _TI, ()),
    ("MetaTrader 5.app in ~/Applications (FAIL)",
     lambda m, f: _app(m.user_applications, "MetaTrader 5.app", untouched=False), _TI, ()),
    ("metatrader 5.APP in /Applications (FAIL: no case)", lambda m, f: _app(m.applications, "metatrader 5.APP"),
     _TI, ()),
    ("MetaEditor.app in /Applications (PASS)", lambda m, f: _app(m.applications, "MetaEditor.app"), (), ()),
    ("Exness MetaTrader 5.app in /Applications (FAIL)",
     lambda m, f: _app(m.applications, "Exness MetaTrader 5.app"), _TI, ()),
    ("a MetaTrader 5 folder without .app at level 0 of /Applications (FAIL)",
     lambda m, f: _app(m.applications, "MetaTrader 5"), _TI, ()),
    ("MetaTrader 5.app in /Applications/Trading, level 1 (PASS: a residual)",
     lambda m, f: _app(m.applications / "Trading", "MetaTrader 5.app"), (), ()),
    ("~/Applications does not exist (PASS)", lambda m, f: {}, (), ()),
    ("/Applications exists but cannot be listed (UNKNOWN)", lambda m, f: {"deny_list": [m.applications]}, (), _TI),
    # Wine prefixes and Program Files (v2.0; v2.1 F12; v2.2 r2 F10)
    *[(f"terminal64.exe at level {levels} of drive_c/Program Files in a {source} prefix "
       f"({'FAIL' if levels == 2 else 'PASS'})", _wine_terminal(source, levels), _TI if levels == 2 else (), ())
      for source in ("PlayOnMac", "CrossOver", "wine") for levels in (2, 3)],
    ("a MetaTrader 5 folder at level 0 of drive_c/Program Files (FAIL)", _metatrader_in_program_files, _TI, ()),
    ("a folder at level 1 of drive_c/Program Files cannot be listed (UNKNOWN)", _unlistable_in_program_files, (),
     _TI),
    ("no Wine prefix at all (PASS, not UNKNOWN)", lambda m, f: {}, (), ()),
    # The home search (v2.1 F10, F12; v2.2 r2 F12, r2 F30)
    ("terminal64.exe at level 3 under home (FAIL)",
     lambda m, f: _terminal(m.home / "Projects" / "a" / "b" / "terminal64.exe"), _TI, ()),
    ("terminal64.exe at level 4 under home (PASS)",
     lambda m, f: _terminal(m.home / "Projects" / "a" / "b" / "c" / "terminal64.exe"), (), ()),
    *[(f"terminal64.exe under <home>/x/{skipped}/ (PASS)",
       lambda m, f, skipped=skipped: _terminal(m.home / "x" / skipped / "terminal64.exe"), (), ())
      for skipped in (".git", ".venv", "node_modules")],
    ("terminal64.exe found beside a folder under home that cannot be listed (FAIL, not UNKNOWN)",
     lambda m, f: _terminal(m.home / "Projects" / "MT5" / "terminal64.exe", deny_list=[m.home / "Music"]), _TI, ()),
    ("another folder under home cannot be listed (UNKNOWN)", lambda m, f: {"deny_list": [m.home / "Music"]}, (), _TI),
    ("the home folder cannot be listed (UNKNOWN)", lambda m, f: {"deny_list": [m.home]}, (), _TI),
    ("~/.Trash cannot be listed (skipped: PASS)", _skip_listed(".Trash"), (), ()),
    ("~/Pictures/Photos Library.photoslibrary cannot be listed (skipped: PASS)",
     _skip_listed("Pictures/Photos Library.photoslibrary"), (), ()),
    ("a dataless folder under home (not listed, skipped: PASS)", _dataless_under_home, (), ()),
    # terminal_data (v2.0; v2.1 F8; v2.2 r2 F12)
    *[(f"{name} in Application Support (FAIL, never listed)", _support(name), _TD, ())
      for name in ("net.metaquotes.wine.metatrader5", "Metatrader 5", "net.metaquotes.wine.metatrader4",
                   "Metatrader 4", "METATRADER 5", "MetaQuotes")],
    *[(f"{name} in Application Support (PASS)", _support(name), (), ())
      for name in ("net.other.app", "metaquotes2", "my metatrader")],
    ("Application Support cannot be listed (UNKNOWN)", lambda m, f: {"deny_list": [m.appsupport]}, (), _TD),
    # Processes (v2.0; v2.1 F7, F8; v2.2 r2 F30)
    ("a process under MetaTrader 5.app (FAIL)",
     _process("/Applications/MetaTrader 5.app/Contents/MacOS/terminal"), _TI, ()),
    ("a process named terminal64.exe (FAIL)", _process("/Users/x/Downloads/mt5/terminal64.exe"), _TI, ()),
    ("a process under Exness MetaTrader 5.app outside /Applications (FAIL)",
     _process("/Users/x/Downloads/Exness MetaTrader 5.app/Contents/MacOS/Exness MT5"), _TI, ()),
    ("terminal64.exe beside wineserver (FAIL: the path is kept)",
     _process("/usr/local/bin/wineserver", "/Users/x/.wine/drive_c/Program Files/MT5/terminal64.exe"), _TI, ()),
    ("wineserver outside any metatrader folder (UNKNOWN)", _process("/usr/local/bin/wineserver"), (), _TI),
    ("the process list cannot be read (UNKNOWN)", _unreadable_process_list, (), _TI),
    # Mounts (v2.0; v2.1 F12)
    ("an smbfs mount (FAIL)", _mount(lambda L: ("smbfs", "//guest@vps.example/share", "/Volumes/share", 0)), _NS, ()),
    ("an nfs mount (FAIL)", _mount(lambda L: ("nfs", "vps.example:/vault", "/Volumes/vault", 0)), _NS, ()),
    ("a mount of a type outside both lists with MNT_LOCAL (UNKNOWN)",
     _mount(lambda L: ("macfuse", "fuse-t:/x", D.ALLOWED_POINT, L)), (), _NS),
    ("only / apfs, /dev devfs and autofs from map auto_home (PASS)", lambda m, f: {}, (), ()),
    ("getfsstat fails (UNKNOWN)", _failing_getfsstat, (), _NS),
)


@pytest.mark.parametrize("label, build, fail, unknown", _COLLECT, ids=[case[0] for case in _COLLECT])
def test_ac02_collect_on_darwin(tmp_path, monkeypatch, label, build, fail, unknown):
    ec, mac, _, options = _host(tmp_path, monkeypatch, build)
    facts, wrong, audit = D.judge_collect(ec, mac, fail=fail, unknown=unknown,
                                          program_files=options.get("program_files", ()),
                                          deny_list=options.get("deny_list", ()))
    for folder in options.get("untouched", ()):
        wrong += D.touched_under(audit, folder)
    for field, value in options.get("facts", {}).items():
        if getattr(facts, field) != value:
            wrong.append(f"Facts.{field} is {getattr(facts, field)!r}, expected {value!r}")
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


def test_ac02_collect_on_darwin_fills_the_facts_of_a_clean_mac(tmp_path, monkeypatch):
    """v2.1 F4: uninstall_display_names is () on darwin, never None; the processes read are named."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    facts, wrong, _ = D.judge_collect(ec, mac)
    for field in ("uninstall_display_names", "terminal_paths", "remote_drives", "connected_resources"):
        value = getattr(facts, field)
        if value is None or tuple(value) != ():
            wrong.append(f"{field} is {value!r}, expected ()")
    if facts.process_names is None or "logd" not in facts.process_names:
        wrong.append(f"process_names {facts.process_names!r}, expected the basenames with logd")
    if facts.metaquotes_exists is not False:
        wrong.append(f"metaquotes_exists {facts.metaquotes_exists!r}, expected False")
    assert not wrong, "AC-02 a clean Mac:\n" + "\n".join(wrong)


def test_ac02_collect_when_read_process_paths_raises(tmp_path, monkeypatch):
    """v2.1 F7: OSError from read_process_paths leaves process_names None and terminal_install UNKNOWN."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)

    def failing(own_pid, own_path):
        raise OSError("own pid missing, 3 pids")

    monkeypatch.setattr(ec, "read_process_paths", failing)
    facts, wrong, _ = D.judge_collect(ec, mac, unknown=_TI)
    if facts.process_names is not None:
        wrong.append(f"process_names {facts.process_names!r}, expected None")
    assert not wrong, "AC-02 read_process_paths raises:\n" + "\n".join(wrong)


_GUARDS = (
    ("DYLD_INSERT_LIBRARIES is set", {"DYLD_INSERT_LIBRARIES": "/tmp/inject.dylib"}, "arm64"),
    ("the machine is x86_64", {}, "x86_64"),
)


@pytest.mark.parametrize("label, environment, machine", _GUARDS, ids=[case[0] for case in _GUARDS])
def test_ac02_collect_reads_no_process_or_mount_when_the_guard_fails(tmp_path, monkeypatch, label, environment,
                                                                     machine):
    """v2.1 F3, F19; v2.2 r2 F4, r2 F12: the checks come first; nothing that reads processes or mounts runs."""
    ec, mac, fake, _ = _host(tmp_path, monkeypatch, machine=machine)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    calls = []
    D.spy(monkeypatch, ec, "read_process_paths", calls)
    D.spy(monkeypatch, ec, "read_mounts", calls)
    facts, wrong, _ = D.judge_collect(ec, mac, unknown=("terminal_install", "network_shares"))
    if calls or fake.raw_calls():
        wrong.append(f"called {calls + fake.raw_calls()}, expected no process or mount reader")
    if facts.process_names is not None or facts.connected_resources is not None:
        wrong.append(f"process_names {facts.process_names!r}, connected_resources {facts.connected_resources!r}; "
                     "expected None for both")
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


@pytest.mark.parametrize("platform", ("linux", "freebsd14"))
def test_ac02_collect_on_another_platform_is_never_pass(tmp_path, monkeypatch, platform):
    """v2.0; v2.1 F22: on a platform other than win32 and darwin the three OS items are UNKNOWN."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch, platform=platform)
    _, wrong, _ = D.judge_collect(ec, mac, unknown=("terminal_install", "terminal_data", "network_shares"))
    assert not wrong, f"AC-02 collect on {platform}:\n" + "\n".join(wrong)


def test_ac02_a_found_appdata_folder_is_never_listed_or_opened(tmp_path, monkeypatch):
    """v2.1 F8, v2.2 r2 F28: appdata outside <home>/Library, a covering data dir, a `metatrader 5` folder with a
    token .txt: terminal_data FAILs and nothing at or under that folder is listed or opened."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    appdata = mac.home / "AppSupport"
    K.put(appdata / "Code" / "User" / "settings.json", '{"editor.tabSize": 4}\n')
    folder = appdata / "metatrader 5"
    K.put(folder / "notes.txt", f"pasted from the VPS: {TOKEN}\n")
    roots = mac.roots(ec, appdata=appdata, data_dirs=(mac.data, mac.home))
    with K.recording() as audit:
        report = ec.research_host_report(roots=roots, sentinel=mac.sentinel(ec))
    others = tuple(name for name in K.ITEMS if name != "terminal_data")
    wrong = K.check_report(report, fail=("terminal_data",), ignore=others) + D.touched_under(audit, folder)
    assert not wrong, "AC-02 metatrader 5 folder in appdata:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- default_roots on darwin

def _roots_host(tmp_path, monkeypatch):
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    return ec, mac


def _default_roots(ec, deny_list=()):
    with K.recording(deny_list=deny_list):
        return ec.default_roots(())


def _roots_problems(roots, mac, search, program_files=()):
    wrong = []
    if K.norm(roots.user_profile) != K.norm(mac.home):
        wrong.append(f"user_profile {roots.user_profile!r}, expected the home of _darwin_home() {mac.home}")
    if K.norm(roots.appdata) != K.norm(mac.appsupport):
        wrong.append(f"appdata {roots.appdata!r}, expected {mac.appsupport}")
    if sorted(map(K.norm, roots.search_dirs)) != sorted(map(K.norm, search)):
        wrong.append(f"search_dirs {roots.search_dirs!r}, expected {sorted(map(str, search))}")
    if sorted(map(K.norm, roots.program_files)) != sorted(map(K.norm, program_files)):
        wrong.append(f"program_files {roots.program_files!r}, expected {sorted(map(str, program_files))}")
    if not roots.data_dirs or K.norm(roots.data_dirs[0]) != K.norm(Path(roots.repo) / "data"):
        wrong.append(f"data_dirs {roots.data_dirs!r}, expected <repo>/data first")
    return wrong


def _shell_folders(mac):
    return [mac.downloads, mac.desktop, mac.documents]


def test_ac02_default_roots_on_darwin_come_from_the_home_folder(tmp_path, monkeypatch):
    """v2.0 default_roots on darwin: home, Application Support, no Wine prefix = no program_files, the three
    shell folders and iCloud Drive (it exists here)."""
    ec, mac = _roots_host(tmp_path, monkeypatch)
    wrong = _roots_problems(_default_roots(ec), mac, [*_shell_folders(mac), mac.icloud])
    assert not wrong, "AC-02 default_roots:\n" + "\n".join(wrong)


def test_ac02_default_roots_on_darwin_without_icloud_drive(tmp_path, monkeypatch):
    ec, mac = _roots_host(tmp_path, monkeypatch)
    mac.icloud.rmdir()
    wrong = _roots_problems(_default_roots(ec), mac, _shell_folders(mac))
    assert not wrong, "AC-02 default_roots without iCloud Drive:\n" + "\n".join(wrong)


def test_ac02_default_roots_on_darwin_ignore_the_windows_variables(tmp_path, monkeypatch):
    """v2.1 F11: USERPROFILE, APPDATA, ProgramFiles* and OneDrive* are not read on darwin."""
    ec, mac = _roots_host(tmp_path, monkeypatch)
    windows = tmp_path / "winprofile"
    for name in ("USERPROFILE", "APPDATA", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "OneDrive",
                 "OneDriveConsumer", "OneDriveCommercial"):
        folder = windows / name.replace("(", "_").replace(")", "_")
        folder.mkdir(parents=True)
        monkeypatch.setenv(name, str(folder))
    roots = _default_roots(ec)
    wrong = _roots_problems(roots, mac, [*_shell_folders(mac), mac.icloud])
    used = [roots.user_profile, roots.appdata, *roots.search_dirs, *roots.program_files]
    wrong += [f"{path} comes from a Windows variable" for path in used if K._under(K.norm(path), K.norm(windows))]
    assert not wrong, "AC-02 default_roots with Windows variables:\n" + "\n".join(wrong)


def test_ac02_default_roots_on_darwin_search_every_cloud_storage_folder(tmp_path, monkeypatch):
    """v2.0, v2.2 r2 F41: every level-0 folder of ~/Library/CloudStorage is a search dir."""
    ec, mac = _roots_host(tmp_path, monkeypatch)
    cloud = [mac.library / "CloudStorage" / name for name in ("OneDrive-Personal", "GoogleDrive-someone@example.com")]
    for folder in cloud:
        folder.mkdir(parents=True)
    wrong = _roots_problems(_default_roots(ec), mac, [*_shell_folders(mac), mac.icloud, *cloud])
    assert not wrong, "AC-02 default_roots with CloudStorage:\n" + "\n".join(wrong)


def test_ac02_default_roots_on_darwin_take_program_files_from_the_wine_prefixes(tmp_path, monkeypatch):
    """v2.0, v2.1 F9: program_files are the drive_c/Program Files* folders of the prefixes found."""
    ec, mac = _roots_host(tmp_path, monkeypatch)
    expected = [mac.program_files_root("wine"), mac.program_files_root("PlayOnMac", folder="Program Files (x86)")]
    wrong = _roots_problems(_default_roots(ec), mac, [*_shell_folders(mac), mac.icloud], expected)
    assert not wrong, "AC-02 default_roots with Wine prefixes:\n" + "\n".join(wrong)


def _unlistable(path):
    def build(mac):
        folder = path(mac)
        folder.mkdir(parents=True, exist_ok=True)
        return [folder]
    return build


def _unlistable_drive_c(mac):
    mac.program_files_root("PlayOnMac")
    return [mac.prefix("PlayOnMac") / "drive_c"]


def _elsewhere(mac, *parts):
    target = mac.base.joinpath("elsewhere", *parts)
    target.mkdir(parents=True)
    return target


def _prefix_symlink(mac):
    target = _elsewhere(mac, "p1")
    (target / "drive_c" / "Program Files").mkdir(parents=True)
    mac.wine_source("PlayOnMac").mkdir(parents=True)
    os.symlink(target, mac.prefix("PlayOnMac"), target_is_directory=True)
    return []


def _bottles_symlink(mac):
    target = _elsewhere(mac, "Bottles")
    (target / "b1" / "drive_c" / "Program Files").mkdir(parents=True)
    mac.wine_source("CrossOver").parent.mkdir(parents=True)
    os.symlink(target, mac.wine_source("CrossOver"), target_is_directory=True)
    return []


def _program_files_symlink(mac):
    target = _elsewhere(mac, "pf")
    drive_c = mac.home / ".wine" / "drive_c"
    drive_c.mkdir(parents=True)
    os.symlink(target, drive_c / "Program Files", target_is_directory=True)
    return []


_ROOTS_RAISE = (
    ("~/Library/PlayOnMac/wineprefix exists but cannot be listed", _unlistable(lambda m: m.wine_source("PlayOnMac"))),
    ("~/Library/Application Support/CrossOver/Bottles exists but cannot be listed",
     _unlistable(lambda m: m.wine_source("CrossOver"))),
    ("~/Library/CloudStorage exists but cannot be listed", _unlistable(lambda m: m.library / "CloudStorage")),
    ("drive_c of a prefix exists but cannot be listed", _unlistable_drive_c),
    ("a prefix folder is a symlink", _prefix_symlink),
    ("Bottles is a symlink", _bottles_symlink),
    ("drive_c/Program Files is a symlink", _program_files_symlink),
)


@pytest.mark.parametrize("label, build", _ROOTS_RAISE, ids=[case[0] for case in _ROOTS_RAISE])
def test_ac02_default_roots_on_darwin_raise_for_a_folder_they_cannot_read(tmp_path, monkeypatch, label, build):
    """v2.1 F9, F10; v2.2 r2 F10; v2.3 r3 F43: default_roots raises OSError (the CLI and the gate: AC-05)."""
    ec, mac = _roots_host(tmp_path, monkeypatch)
    deny_list = build(mac)
    try:
        roots = _default_roots(ec, deny_list)
    except OSError:
        return
    pytest.fail(f"AC-02 {label}: default_roots returned {roots!r}, expected OSError", pytrace=False)
