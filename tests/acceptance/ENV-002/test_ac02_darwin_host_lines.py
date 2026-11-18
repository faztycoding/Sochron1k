r"""ENV-002 v2.6 contract tests for AC-02, the lines of envcheck.host_lines() on darwin
(docs/contracts/ENV-002-research-host-separation.md: `_HOST_SUMMARY`, host_lines() and the shape of every
line, v2.1 F4 to v2.5 r5 F60, and the Negative cases that name a line); run pytest from the repository
root.

The contract says host_lines() is tested through research_host_report or main (or the real collect with
the platform set to darwin and fake raw readers). Each test here runs research_host_report on the fake Mac
of darwinkit.py with the platform set to darwin and the fake OS installed, then reads host_lines() and the
report. Lines whose form the contract fixes are compared exactly; a line the contract gives only in part
(the name in `apps:`, the path in `skipped:`) is compared by the part it fixes. Conventions D1-D8 are in
darwinkit.py. Two tests here also replace collect with a fake, as the contract's cases do.
"""

import dataclasses
import errno
import importlib.util
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


def _host(tmp_path, monkeypatch, build=None, *, machine="arm64"):
    ec = D.reader(AC)
    mac = D.Mac(tmp_path)
    fake = D.FakeOS(ec, mac)
    fake.machine = machine
    options = (build(mac, fake) if build else None) or {}
    fake.install(monkeypatch, ec, cloud=options.get("cloud", ()))
    return ec, mac, fake, options


def _fake_collect(monkeypatch, ec):
    monkeypatch.setattr(ec, "collect", lambda roots: K.facts(ec))


def _lines_problems(lines, expected):
    if not (isinstance(lines, tuple) and all(isinstance(text, str) for text in lines)):
        return [f"host_lines() returned {lines!r}, expected a tuple of str"]
    return [f"no line {text!r} in {list(lines)}" for text in expected if text not in lines]


def _only(lines, prefix):
    return [text for text in lines if text.startswith(prefix)]


def _app(folder, name):
    K.put(folder / name / "Contents" / "MacOS" / "app", b"\xcf\xfa\xed\xfe synthetic")


# ------------------------------------------------------------------------- the summary and its life

def test_ac02_host_lines_after_a_darwin_report_then_after_a_replaced_collect(tmp_path, monkeypatch):
    """v2.2 r2 F12; v2.3 r3 F25; v2.4 r4 F55: the lines of the real collect, then, in the same process, the
    lines of a report whose collect is replaced: research_host_report clears the summary every time."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    report, lines, audit = D.report_with_lines(ec, mac)
    wrong = K.check_report(report) + D.outside_reads(audit, mac.base)
    wrong += _lines_problems(lines, ("reader: darwin", "processes: 3 listed, 2 paths read, 1 skipped, 0 wine loaders",
                                     "mounts: 3 (apfs, devfs, autofs)", "wine: 0 prefixes; looked at none"))
    _fake_collect(monkeypatch, ec)
    second = ec.research_host_report(roots=mac.roots(ec), sentinel=mac.sentinel(ec))
    after = ec.host_lines()
    wrong += [f"replaced collect: {text}" for text in K.check_report(second)]
    wrong += [f"replaced collect: {text}" for text in _lines_problems(after, ("reader: darwin",))]
    for prefix in ("processes:", "mounts:", "wine:"):
        if _only(after, prefix) != [f"{prefix} not read"]:
            wrong.append(f"replaced collect: {_only(after, prefix)}, expected ['{prefix} not read']")
    if D.line(after, "roots:") is None:
        wrong.append(f"replaced collect: no roots: line in {list(after)}")
    wrong += [f"replaced collect: a {prefix} line is printed" for prefix in ("skipped:", "apps:", "tools:")
              if _only(after, prefix)]
    assert not wrong, "AC-02 host_lines:\n" + "\n".join(wrong)


@pytest.mark.parametrize("platform, expected", (("darwin", "reader: darwin"), ("linux", "reader: none"),
                                                ("win32", "reader: win32")))
def test_ac02_host_lines_of_an_empty_summary_is_the_reader_line_only(monkeypatch, platform, expected):
    """v2.2 r2 F12; v2.4 r4 F55: with _HOST_SUMMARY empty, host_lines() is reader: from reader_name() alone."""
    ec = K.envcheck(AC, "host_lines", "_HOST_SUMMARY", "reader_name", "sys")
    monkeypatch.setattr(ec, "_HOST_SUMMARY", {})
    monkeypatch.setattr(ec.sys, "platform", platform)
    got = ec.host_lines()
    assert got == (expected,), f"AC-02: host_lines() gave {got!r}, expected {(expected,)!r}"


def test_ac02_roots_line_shows_the_token_as_a_placeholder(tmp_path, monkeypatch):
    """v2.1 F11; v2.2 r2 F12: a root path that holds the token prints <token>; no line holds the token."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    folder = mac.home / f"Exports {TOKEN}"
    folder.mkdir()
    mac.search_dirs.append(folder)
    _fake_collect(monkeypatch, ec)
    report = ec.research_host_report(roots=mac.roots(ec), sentinel=mac.sentinel(ec))
    lines = ec.host_lines()
    roots_line = D.line(lines, "roots:")
    wrong = K.check_report(report)
    if roots_line is None or "<token>" not in roots_line:
        wrong.append(f"roots line {roots_line!r} does not show <token>")
    wrong += [f"the token is in {text!r}" for text in lines if TOKEN in text]
    assert not wrong, "AC-02 roots line and the token:\n" + "\n".join(wrong)


def test_ac02_roots_line_counts_cloud_storage_providers_without_account_names(tmp_path, monkeypatch):
    """v2.2 r2 F41: two CloudStorage folders print as `cloud storage: 2 (OneDrive, GoogleDrive)` and are
    still searched; nothing after the first '-' of their names is printed."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    cloud = [mac.library / "CloudStorage" / name for name in ("OneDrive-Personal", "GoogleDrive-someone@example.com")]
    for folder in cloud:
        folder.mkdir(parents=True)
    roots = dataclasses.replace(ec.default_roots(()), repo=mac.repo, data_dirs=(mac.data,))
    _fake_collect(monkeypatch, ec)
    report = ec.research_host_report(roots=roots, sentinel=mac.sentinel(ec))
    roots_line = D.line(ec.host_lines(), "roots:") or ""
    wrong = K.check_report(report)
    if not roots_line.endswith(("; cloud storage: 2 (OneDrive, GoogleDrive)", "; cloud storage: 2 (GoogleDrive, OneDrive)")):
        wrong.append(f"roots line {roots_line!r} does not end with the two providers")
    if "-Personal" in roots_line or "someone@example.com" in roots_line:
        wrong.append(f"roots line {roots_line!r} shows a folder name after its '-'")
    searched = set(map(K.norm, roots.search_dirs))
    wrong += [f"{folder} is not a search dir" for folder in cloud if K.norm(folder) not in searched]
    assert not wrong, "AC-02 cloud storage:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- apps:, tools:, skipped:

def test_ac02_a_clean_mac_prints_none_and_zero(tmp_path, monkeypatch):
    """v2.2 r2 F9, v2.3 r3 F48: no name of either list gives `apps: none`, `tools: none`, `skipped: 0 folders`."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    report, lines, _ = D.report_with_lines(ec, mac)
    wrong = K.check_report(report) + _lines_problems(lines, ("apps: none", "tools: none", "skipped: 0 folders"))
    assert not wrong, "AC-02 a clean Mac:\n" + "\n".join(wrong)


@pytest.mark.parametrize("app, name", (("Docker.app", "Docker"), ("UTM.app", "UTM")))
def test_ac02_a_vm_or_container_app_is_named_in_apps_and_changes_no_verdict(tmp_path, monkeypatch, app, name):
    """v2.0; v2.1 F9: Docker.app or UTM.app in /Applications: the verdict stays PASS, apps: names it."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch, lambda m, f: _app(m.applications, app))
    report, lines, _ = D.report_with_lines(ec, mac)
    apps = D.line(lines, "apps:") or ""
    wrong = K.check_report(report)
    if name not in apps:
        wrong.append(f"apps line {apps!r} does not name {name}")
    assert not wrong, f"AC-02 {app}:\n" + "\n".join(wrong)


def test_ac02_colima_is_named_in_tools_and_changes_no_verdict(tmp_path, monkeypatch):
    """v2.2 r2 F9: a .colima folder at level 0 of home gives `tools: .colima`; the verdict stays PASS."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch, lambda m, f: K.put(m.home / ".colima" / "default" / "colima.yaml", "cpu: 2\n") and {})
    report, lines, _ = D.report_with_lines(ec, mac)
    wrong = K.check_report(report) + _lines_problems(lines, ("tools: .colima",))
    assert not wrong, "AC-02 .colima:\n" + "\n".join(wrong)


def test_ac02_the_tools_line_only_looks_at_existence(tmp_path, monkeypatch):
    """v2.4 r4 F49: with find_terminal_paths_darwin replaced by a fake, nothing at or under .colima is listed."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    colima = mac.home / ".colima"
    K.put(colima / "default" / "colima.yaml", "cpu: 2\n")
    monkeypatch.setattr(ec, "find_terminal_paths_darwin", lambda *args, **kwargs: ((), True, ()))
    report, lines, audit = D.report_with_lines(ec, mac)
    wrong = K.check_report(report) + _lines_problems(lines, ("tools: .colima",)) + D.touched_under(audit, colima)
    assert not wrong, "AC-02 tools: looks at existence only:\n" + "\n".join(wrong)


def _dataless_archive(mac, fake):
    folder = mac.home / "Music" / "Archive"
    K.put(folder / "terminal64.exe", EXE)
    return {"cloud": [folder]}


def test_ac02_a_dataless_folder_under_home_is_skipped_and_counted(tmp_path, monkeypatch):
    """v2.1 F6; v2.2 r2 F12: not listed, in the skipped: line, PASS."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch, _dataless_archive)
    folder = mac.home / "Music" / "Archive"
    report, lines, audit = D.report_with_lines(ec, mac)
    wrong = K.check_report(report) + D.touched_under(audit, folder)
    if not (D.line(lines, "skipped:") or "").startswith("skipped: 1 folders"):
        wrong.append(f"skipped line {D.line(lines, 'skipped:')!r}, expected 'skipped: 1 folders …'")
    assert not wrong, "AC-02 dataless folder under home:\n" + "\n".join(wrong)


@pytest.mark.parametrize("relative", (".Trash", "Pictures/Photos Library.photoslibrary"))
def test_ac02_a_skip_list_folder_that_cannot_be_listed_is_counted(tmp_path, monkeypatch, relative):
    """v2.1 F10, F12: skipped, PASS, and in the skipped: line."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    folder = mac.home / relative
    folder.mkdir(parents=True, exist_ok=True)
    report, lines, _ = D.report_with_lines(ec, mac, deny_list=[folder])
    wrong = K.check_report(report)
    if not (D.line(lines, "skipped:") or "").startswith("skipped: 1 folders"):
        wrong.append(f"skipped line {D.line(lines, 'skipped:')!r}, expected 'skipped: 1 folders …'")
    assert not wrong, f"AC-02 {relative}:\n" + "\n".join(wrong)


def test_ac02_applications_that_cannot_be_listed_print_apps_unreadable(tmp_path, monkeypatch):
    """v2.2 r2 F12; v2.4 r4 F48: terminal_install UNKNOWN and `apps: unreadable (…)`."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch)
    report, lines, _ = D.report_with_lines(ec, mac, deny_list=[mac.applications])
    wrong = K.check_report(report, unknown=("terminal_install",))
    if not (D.line(lines, "apps:") or "").startswith("apps: unreadable ("):
        wrong.append(f"apps line {D.line(lines, 'apps:')!r}, expected 'apps: unreadable (…)'")
    assert not wrong, "AC-02 /Applications unreadable:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- wine:

def test_ac02_collect_searches_the_prefixes_of_hand_built_roots(tmp_path, monkeypatch):
    """v2.3 r3 F25: roots with program_files=() and a ~/.wine prefix holding terminal64.exe at level 1."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch,
                          lambda m, f: K.put(m.program_files_root("wine") / "MT5" / "terminal64.exe", EXE) and {})
    report, lines, _ = D.report_with_lines(ec, mac, program_files=())
    wrong = K.check_report(report, fail=("terminal_install",))
    wrong += _lines_problems(lines, ("wine: 1 prefixes; looked at ~/.wine",))
    assert not wrong, "AC-02 hand-built roots and a Wine prefix:\n" + "\n".join(wrong)


@pytest.mark.parametrize("with_app", (False, True), ids=("nothing else found", "MetaTrader 5.app found too"))
def test_ac02_an_unlistable_wineprefix_folder_with_hand_built_roots(tmp_path, monkeypatch, with_app):
    """v2.4 r4 F52, F48; v2.5 r5 F60: terminal_install UNKNOWN (FAIL when an app is found) and the wine: line
    gives the folder from ~/ and `[Errno <n>] <strerror>`, not the full path."""
    def build(mac, fake):
        mac.wine_source("PlayOnMac").mkdir(parents=True)
        if with_app:
            _app(mac.applications, "MetaTrader 5.app")
        return {}

    ec, mac, _, _ = _host(tmp_path, monkeypatch, build)
    report, lines, _ = D.report_with_lines(ec, mac, program_files=(), deny_list=[mac.wine_source("PlayOnMac")])
    wrong = K.check_report(report, fail=("terminal_install",) if with_app else (),
                           unknown=() if with_app else ("terminal_install",))
    expected = (f"wine: unreadable (~/Library/PlayOnMac/wineprefix: [Errno {errno.EACCES}] "
                "Permission denied (ENV-002 test))")
    wrong += _lines_problems(lines, (expected,))
    assert not wrong, "AC-02 unlistable wineprefix:\n" + "\n".join(wrong)


def _prefix_without_drive_c(mac, fake):
    (mac.prefix("PlayOnMac") / "user").mkdir(parents=True)
    return {}


def _wine_without_drive_c(mac, fake):
    K.put(mac.home / ".wine" / "system.reg", "WINE REGISTRY Version 2\n")
    return {}


_NO_DRIVE_C = (
    ("a PlayOnMac prefix without drive_c", _prefix_without_drive_c,
     "wine: 1 prefixes; looked at ~/Library/PlayOnMac/wineprefix"),
    ("~/.wine without drive_c", _wine_without_drive_c, "wine: 0 prefixes; looked at ~/.wine"),
)


@pytest.mark.parametrize("label, build, expected", _NO_DRIVE_C, ids=[case[0] for case in _NO_DRIVE_C])
def test_ac02_a_prefix_without_drive_c_is_no_error(tmp_path, monkeypatch, label, build, expected):
    """v2.2 r2 F10; v2.5 r5 F60: PASS, and ~/.wine counts as a prefix only with a drive_c."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch, build)
    report, lines, _ = D.report_with_lines(ec, mac)
    wrong = K.check_report(report) + _lines_problems(lines, (expected,))
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- processes: and mounts:

def _own_pid():
    return D.own()[0]


_PROCESS_LINES = (
    # (label, change(fake), machine, environment, expected lines, unknown items)
    ("the list lacks this process", lambda f: f.table.pop(_own_pid()), "arm64", {},
     ("processes: unreadable (own pid missing, 2 pids)",), ("terminal_install",)),
    ("this process has another path", lambda f: f.table.__setitem__(_own_pid(), ("/usr/bin/python3", 0)), "arm64", {},
     ("processes: unreadable (own path differs, 3 pids)",), ("terminal_install",)),
    ("proc_pidpath fails with ENOMEM on pid 333", lambda f: f.table.__setitem__(333, (None, errno.ENOMEM)), "arm64",
     {}, (f"processes: unreadable (errno {errno.ENOMEM} on pid 333, 3 pids)",), ("terminal_install",)),
    ("proc_listallpids lists no pid", lambda f: f.table.clear(), "arm64", {},
     ("processes: unreadable (listed 0 pids)",), ("terminal_install",)),
    ("a DYLD_ variable is set", lambda f: None, "arm64", {"DYLD_LIBRARY_PATH": "/tmp/lib"},
     ("processes: unreadable (DYLD_ variables set)", "mounts: unreadable (DYLD_ variables set)"),
     ("terminal_install", "network_shares")),
    ("the machine is x86_64", lambda f: None, "x86_64", {},
     ("processes: unreadable (not arm64: x86_64)", "mounts: unreadable (not arm64: x86_64)"),
     ("terminal_install", "network_shares")),
)


@pytest.mark.parametrize("label, change, machine, environment, expected, unknown", _PROCESS_LINES,
                         ids=[case[0] for case in _PROCESS_LINES])
def test_ac02_processes_and_mounts_lines_give_the_reason(tmp_path, monkeypatch, label, change, machine, environment,
                                                         expected, unknown):
    """v2.1 F7; v2.3 r3 F25, F48: every `unreadable (<reason>)` form that read_process_paths or collect decides."""
    ec, mac, _, _ = _host(tmp_path, monkeypatch, lambda m, f: change(f) and {}, machine=machine)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    report, lines, _ = D.report_with_lines(ec, mac)
    wrong = K.check_report(report, unknown=unknown) + _lines_problems(lines, expected)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


def test_ac02_mounts_line_names_a_mount_point_outside_the_allow_list(tmp_path, monkeypatch):
    """v2.2 r2 F15: after collect with an apfs mount at /Volumes/USB the mounts: line ends with
    `; not allowed: /Volumes/USB` and network_shares is UNKNOWN."""
    def build(mac, fake):
        fake.mounts.append(("apfs", "/dev/disk4s1", "/Volumes/USB", fake.local))
        return {}

    ec, mac, _, _ = _host(tmp_path, monkeypatch, build)
    report, lines, _ = D.report_with_lines(ec, mac)
    mounts = D.line(lines, "mounts:") or ""
    wrong = K.check_report(report, unknown=("network_shares",))
    if not mounts.endswith("; not allowed: /Volumes/USB"):
        wrong.append(f"mounts line {mounts!r} does not end with '; not allowed: /Volumes/USB'")
    assert not wrong, "AC-02 /Volumes/USB:\n" + "\n".join(wrong)
