r"""Approved ENV-002 v1.7 contract tests for AC-02 (docs/contracts/ENV-002-research-host-separation.md);
run pytest from the repository root. Tests r2 (docs/reviews/ENV-002-tests-r1.md F2, F4, F6, F8) added
cases; no earlier case changed.

sochron.app.envcheck is imported as a package module (pytest's pythonpath is src). Only contract names
are used: Item, Report, Sentinel, ResearchRoots, Facts, collect (looked up, never called), evaluate and
is_cloud_only (replaced by a fake where the contract says tests may). Each test builds a fake research
host under tmp_path (envkit.Machine) and fake Facts; no test needs a Windows API and nothing outside
tmp_path is read. The helpers are in envkit.py next to this file, loaded by path.

Conventions the contract leaves to these tests (also in docs/handoff/ENV-002.md):
1. <repo> is Path(__file__).resolve().parents[3]: this file is <repo>/tests/acceptance/ENV-002/<file>.
2. Facts is a frozen dataclass with exactly these fields. None means "could not be read" (permission,
   API failure) and makes the item it feeds UNKNOWN:
     terminal_paths: tuple[str, ...] | None    what collect found for the three path rules of
         terminal_install (Program Files*\MetaTrader* folders, terminal64.exe at levels 1-2 of
         Program Files*, terminal64.exe under the user profile at most 3 levels deep outside .git,
         .venv and node_modules); any entry fails terminal_install
     uninstall_display_names: tuple[str, ...] | None    the DisplayName of every Uninstall entry
         (HKLM, HKCU, WOW6432Node); one that contains "MetaTrader" in any case fails terminal_install
     process_names: tuple[str, ...] | None    executable names of the running processes;
         "terminal64.exe" in any case fails terminal_install (v1.6 Q4)
     metaquotes_exists: bool | None    %APPDATA%\MetaQuotes exists; True fails terminal_data
     mt5_spec_found: bool | None    importlib.util.find_spec("MetaTrader5") is not None; True fails
         mt5_package
     remote_drives: tuple[str, ...] | None    drives whose GetDriveTypeW is DRIVE_REMOTE
     connected_resources: tuple[str, ...] | None    remote names from WNetOpenEnumW(RESOURCE_CONNECTED);
         an entry in either fails network_shares
   An item fed by several facts FAILs when any of them shows its condition, even if another is None
   (the contract: FAIL when any one of them is found); with nothing found and one None it is UNKNOWN. The
   path search of terminal_install (levels, depth, skipped folders) is the module-level helper of
   contract v1.6 Q2/Q3 that collect calls; the implementer's tests/unit/app tests cover it, not these.
3. ResearchRoots is a frozen dataclass with exactly the contract's fields, built here as: repo a Path;
   data_dirs a tuple of Path, <repo>/data first and then every --data-dir; program_files a tuple of
   Path; appdata and user_profile a Path; search_dirs a tuple of Path (Downloads, Desktop, Documents,
   OneDrive). Every folder is under tmp_path.
4. Sentinel is a frozen dataclass with exactly the contract's fields, built with the committed JSON's
   values: name, sha256 (64 lower-case hex), token (32 lower-case hex), vault_path and created_utc
   ("%Y-%m-%dT%H:%M:%SZ") as str, and size as int. The sentinel file of these tests has the shape
   the contract gives make_sentinel.py (envkit.sentinel_document). vault_path is the vault folder or
   the sentinel file (v1.6 Q8); rule (1) FAILs when either exists here (tests r2, F4).
5. Item.status and Report.verdict compare equal to "PASS", "FAIL" or "UNKNOWN"; Item.detail is a str;
   Report.role == "research"; Report.items is a tuple with exactly one Item for each of
   terminal_install, terminal_data, mt5_package, holdout_dir, excluded_period, network_shares and
   sentinel (order not checked). Item and Report are frozen dataclasses; verdict may be a field or a
   property. Inside an item, as in the verdict, FAIL outranks UNKNOWN.
6. Every search is recursive under its roots and enters every folder, .git, .venv and node_modules
   included (v1.6 Q11); "under a root" compares absolute paths. A file under both the repo or a data
   dir and a search dir follows the repo/data-dir rules (contract v1.5). (v1.7, tests-r1 F8) A folder
   that cannot be listed makes every item that searches it UNKNOWN: holdout_dir, excluded_period and
   sentinel for a folder under the repo or a data dir, sentinel alone for one under a search dir only.
   Reparse points (junctions, symlinks) are not entered; no test makes one (that needs privileges on
   Windows).
7. A per-file manifest is named after the full file name: bars.parquet.manifest.json. Every manifest
   written here, per file or per folder, has the folder manifest's shape {"files": [{"name",
   "sha256"}], "period_end_utc"} and holds the true SHA-256 (hashes are SLICE-R1's check). (v1.7,
   tests-r1 F2) A cloud-only manifest is never opened: the data files that need it are UNKNOWN for
   excluded_period, and the manifest itself (a .json in a data dir) makes sentinel UNKNOWN.
8. "Opened" means an "open" audit event for the path (builtins.open, io.open, Path.open, read_bytes
   and os.open raise it). One process-wide sys.addaudithook records only while a test flag is on,
   because audit hooks cannot be removed. The same hook refuses an open of a chosen path with
   PermissionError: that is how "unreadable because of permissions" is made, on any OS and for any user.
   (Tests r2, F8) It also refuses the listing of a chosen folder (the os.scandir and os.listdir events,
   which os.walk, Path.iterdir and Path.rglob raise) with PermissionError.
9. During every evaluate call the tests check the contract's read rules against every file of the
   fake host. A file may be opened only when a rule needs it: in the repo and data dirs a .json, .csv,
   .txt or .md file (the token search reads them; manifests are .json); in a search dir outside them
   a .json file of exactly the sentinel's size; nothing outside the roots. Never: .env and .env.*
   (.env.example included), *.key, *.pem, *.pfx, *.rdp, anything under a folder that holds
   terminal64.exe or under <appdata>\MetaQuotes, and any file the fake is_cloud_only calls
   cloud-only. Suffixes, these names and terminal64.exe compare without case (v1.6 Q4).
   <appdata>\MetaQuotes and its subfolders are never listed (os.listdir, os.scandir).
   Nothing is written, renamed or deleted (Python's own __pycache__ aside), and no subprocess,
   socket, http, urllib, shutil, tempfile or registry-write audit event fires.
10. evaluate calls envcheck.is_cloud_only, looked up at call time, before it opens a file. The fake
    answers by absolute path. The real one calls os.stat (looked up at call time): an
    st_file_attributes with 0x00400000 or 0x00040000 set is cloud-only; other bits, 0 and no
    attribute are not.
11. The token is searched as its 32 ASCII characters (files written as UTF-8 or ASCII) and, v1.7
    tests-r1 F6, as UTF-16 LE and BE text with or without a BOM. File names match the
    sentinel's name and the searched extensions without case (v1.6 Q4). The one excluded file is exactly
    <repo>/docs/evidence/ENV-002-sentinel.json; a file of that name anywhere else gets no exception.
12. (v1.6 Q5) When <repo>/data does not exist there is nothing to check there: alone it makes no item
    FAIL or UNKNOWN. A --data-dir that does not exist makes excluded_period UNKNOWN; holdout_dir and
    sentinel are not compared in that case.
13. (v1.6 Q6) A never-open file that rule (3) or (4) would have to open makes sentinel UNKNOWN and is
    still never opened: in a search dir a .json of exactly the sentinel's size, in the repo or a data
    dir a .json, .csv, .txt or .md. A never-open file no rule would open (.env.example, id.key) is ignored.
14. (v1.6 Q7) No Item.detail holds the token; every report of these tests is checked for it.
"""

import codecs
import hashlib
import importlib.util
import os
import sys
from dataclasses import fields, is_dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_kit():
    name, path = "envkit_env002", Path(__file__).resolve().parent / "envkit.py"
    module = sys.modules.get(name)
    if module is None or getattr(module, "__file__", None) != str(path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


K = _load_kit()
AC = "AC-02"
NAMES = ("Item", "Report", "Sentinel", "ResearchRoots", "Facts", "collect", "evaluate", "is_cloud_only")
TOKEN = K.TOKEN


def _ec():
    return K.envcheck(AC, *NAMES)


def _verdict(machine, ec, monkeypatch, *, facts=None, sentinel=True, cloud=(), deny=(), fail=(), unknown=(),
             ignore=(), deny_list=()):
    """Evaluate the fake host and return every difference from the expectation and the read rules."""
    facts_value = K.facts(ec, **(facts or {}))
    sentinel_value = machine.sentinel(ec) if sentinel else None
    report, wrong = K.judge(ec, monkeypatch, machine, facts_value, sentinel_value, cloud=cloud, deny=deny,
                            deny_list=deny_list)
    return K.check_report(report, fail=fail, unknown=unknown, ignore=ignore) + wrong


# ------------------------------------------------------------------------- records and names

def test_ac02_records_are_frozen_dataclasses_with_the_contract_fields():
    ec = _ec()
    wrong = []
    for name, expected in (("Facts", set(K.FACT_ITEM)), ("ResearchRoots", set(K.ROOT_FIELDS)),
                           ("Sentinel", set(K.SENTINEL_FIELDS)), ("Item", {"name", "status", "detail"})):
        cls = getattr(ec, name)
        if not (is_dataclass(cls) and cls.__dataclass_params__.frozen):
            wrong.append(f"{name} is not a frozen dataclass")
        elif {item.name for item in fields(cls)} != expected:
            wrong.append(f"{name} fields {sorted(item.name for item in fields(cls))}, expected {sorted(expected)}")
    report = ec.Report
    if not (is_dataclass(report) and report.__dataclass_params__.frozen):
        wrong.append("Report is not a frozen dataclass")
    else:
        names = {item.name for item in fields(report)}
        verdict = "verdict" in names or isinstance(getattr(report, "verdict", None), property)
        if names not in ({"role", "items", "verdict"}, {"role", "items"}) or not verdict:
            wrong.append(f"Report fields {sorted(names)}, expected role, items and verdict (a field or property)")
    assert not wrong, "AC-02:\n" + "\n".join(wrong)


def test_ac02_contract_functions_exist_and_collect_is_not_called_here():
    ec = K.envcheck(AC, *NAMES, "research_host_report", "require_research_host", "ResearchHostError")
    wrong = [name for name in ("collect", "evaluate", "is_cloud_only", "research_host_report",
                               "require_research_host") if not callable(getattr(ec, name))]
    assert not wrong, f"AC-02: not callable: {wrong}"


def test_ac02_valid_research_host_passes_every_item(tmp_path, monkeypatch):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch)
    assert not wrong, "AC-02 valid host:\n" + "\n".join(wrong)


def test_ac02_valid_research_host_with_the_repo_under_desktop_passes(tmp_path, monkeypatch):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path, repo_in_desktop=True), ec, monkeypatch)
    assert not wrong, "AC-02 valid host, repo under Desktop:\n" + "\n".join(wrong)


_NO_DEFAULT_DATA = (
    ("no <repo>/data", lambda m: None, ()),
    ("no <repo>/data, a valid --data-dir",
     lambda m: m.add_snapshot(m.add_data_dir(m.base / "usb" / "export"), K.AT_CUTOFF), ()),
    ("no <repo>/data, a late --data-dir",
     lambda m: m.add_snapshot(m.add_data_dir(m.base / "usb" / "export"), "2025-06-30T00:00:00Z"), ("excluded_period",)),
)


@pytest.mark.parametrize("label, build, fail", _NO_DEFAULT_DATA, ids=[case[0] for case in _NO_DEFAULT_DATA])
def test_ac02_missing_default_data_dir_has_nothing_to_check(tmp_path, monkeypatch, label, build, fail):
    """v1.6 Q5: a fresh clone has no <repo>/data; that alone is no FAIL and no UNKNOWN."""
    ec = _ec()
    m = K.Machine(tmp_path, with_data=False)
    build(m)
    wrong = _verdict(m, ec, monkeypatch, fail=fail)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- Facts

_FACT_FAILS = (
    ("MetaTrader 5 folder in Program Files", {"terminal_paths": (r"C:\Program Files\MetaTrader 5",)},
     "terminal_install"),
    ("broker-branded terminal64.exe in Program Files",
     {"terminal_paths": (r"C:\Program Files\Exness MT5 Terminal\terminal64.exe",)}, "terminal_install"),
    ("portable terminal64.exe under the profile",
     {"terminal_paths": (r"C:\Users\owner\Desktop\MT5\terminal64.exe",)}, "terminal_install"),
    ("Uninstall entry MetaTrader 5", {"uninstall_display_names": K.UNINSTALLED + ("MetaTrader 5",)},
     "terminal_install"),
    ("Uninstall entry that contains MetaTrader",
     {"uninstall_display_names": K.UNINSTALLED + ("Exness MetaTrader 5 Terminal",)}, "terminal_install"),
    ("Uninstall entry in lower case (v1.6 Q4)",
     {"uninstall_display_names": K.UNINSTALLED + ("metatrader 5 terminal",)}, "terminal_install"),
    ("Uninstall entry in upper case (v1.6 Q4)", {"uninstall_display_names": K.UNINSTALLED + ("METATRADER 5",)},
     "terminal_install"),
    ("terminal64.exe running", {"process_names": K.RUNNING + ("terminal64.exe",)}, "terminal_install"),
    ("TERMINAL64.EXE running (v1.6 Q4)", {"process_names": K.RUNNING + ("TERMINAL64.EXE",)}, "terminal_install"),
    ("Terminal64.exe running (v1.6 Q4)", {"process_names": K.RUNNING + ("Terminal64.exe",)}, "terminal_install"),
    ("APPDATA MetaQuotes exists", {"metaquotes_exists": True}, "terminal_data"),
    ("MetaTrader5 importable", {"mt5_spec_found": True}, "mt5_package"),
    ("mapped drive", {"remote_drives": ("Z:\\",)}, "network_shares"),
    ("connected UNC resource", {"connected_resources": (r"\\vps.example\C$",)}, "network_shares"),
    ("mapped drive and resource", {"remote_drives": ("Y:\\",), "connected_resources": (r"\\vps.example\vault",)},
     "network_shares"),
)


@pytest.mark.parametrize("label, changes, item", _FACT_FAILS, ids=[case[0] for case in _FACT_FAILS])
def test_ac02_one_wrong_fact_fails_only_its_item(tmp_path, monkeypatch, label, changes, item):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch, facts=changes, fail=(item,))
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


@pytest.mark.parametrize("field", sorted(K.FACT_ITEM))
def test_ac02_unreadable_fact_is_unknown_when_nothing_fails(tmp_path, monkeypatch, field):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch, facts={field: None}, unknown=(K.FACT_ITEM[field],))
    assert not wrong, f"AC-02 {field} unreadable:\n" + "\n".join(wrong)


_FOUND_BESIDE_UNREADABLE = (
    ("paths unreadable, terminal64.exe running",
     {"terminal_paths": None, "process_names": K.RUNNING + ("terminal64.exe",)}, "terminal_install"),
    ("Uninstall unreadable, a MetaTrader folder found",
     {"uninstall_display_names": None, "terminal_paths": (r"C:\Program Files\MetaTrader 5",)}, "terminal_install"),
    ("processes unreadable, a MetaTrader Uninstall entry",
     {"process_names": None, "uninstall_display_names": ("MetaTrader 5",)}, "terminal_install"),
    ("drives unreadable, a connected resource",
     {"remote_drives": None, "connected_resources": (r"\\vps.example\vault",)}, "network_shares"),
    ("resources unreadable, a mapped drive", {"connected_resources": None, "remote_drives": ("Z:\\",)},
     "network_shares"),
)


@pytest.mark.parametrize("label, changes, item", _FOUND_BESIDE_UNREADABLE,
                         ids=[case[0] for case in _FOUND_BESIDE_UNREADABLE])
def test_ac02_a_found_condition_fails_even_when_another_source_is_unreadable(tmp_path, monkeypatch, label,
                                                                             changes, item):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch, facts=changes, fail=(item,))
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


def test_ac02_nothing_readable_from_the_os_is_unknown(tmp_path, monkeypatch):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch, facts=dict.fromkeys(K.FACT_ITEM),
                     unknown=("terminal_install", "terminal_data", "mt5_package", "network_shares"))
    assert not wrong, "AC-02 all Facts None:\n" + "\n".join(wrong)


_PRECEDENCE = (
    ("FAIL beside UNKNOWN items", {"mt5_spec_found": True, "metaquotes_exists": None}, True,
     ("mt5_package",), ("terminal_data",)),
    ("FAIL beside a missing sentinel", {"remote_drives": ("Z:\\",)}, False, ("network_shares",), ("sentinel",)),
    ("UNKNOWN items only", {"process_names": None, "connected_resources": None}, True, (),
     ("terminal_install", "network_shares")),
)


@pytest.mark.parametrize("label, changes, sentinel, fail, unknown", _PRECEDENCE, ids=[case[0] for case in _PRECEDENCE])
def test_ac02_verdict_is_fail_then_unknown_then_pass(tmp_path, monkeypatch, label, changes, sentinel, fail, unknown):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch, facts=changes, sentinel=sentinel, fail=fail,
                     unknown=unknown)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- holdout_dir and excluded_period

def _snap(m, folder, end, **options):
    m.add_snapshot(folder, end, **options)
    return {}


def _bare(path):
    K.put(path, K.PARQUET)
    return {}


def _folder(path):
    path.mkdir(parents=True)
    return {}


def _manifest(m, text):
    """data/m1-2025 with bars.parquet and a folder manifest.json holding text (bytes or str)."""
    K.put(m.data / "m1-2025" / "bars.parquet", K.PARQUET)
    K.put(m.data / "m1-2025" / "manifest.json", text)
    return {}


_ENTRY = '[{"name": "bars.parquet", "sha256": "' + hashlib.sha256(K.PARQUET).hexdigest() + '"}]'


def _manifest_json(files=_ENTRY, end='"2024-07-01T00:00:00Z"'):
    """A folder manifest's text with the given JSON for files and period_end_utc (None leaves a field out)."""
    parts = []
    if files is not None:
        parts.append(f'"files": {files}')
    if end is not None:
        parts.append(f'"period_end_utc": {end}')
    return "{" + ", ".join(parts) + "}\n"


_TREE = (
    # (label, build(m) -> {"cloud": [...], "deny": [...]}, fail, unknown, ignore)
    ("holdout folder at the repo root", lambda m: _folder(m.repo / "holdout"), ("holdout_dir",), (), ()),
    ("Holdout folder deep in the repo", lambda m: _folder(m.repo / "research" / "2025" / "Holdout"),
     ("holdout_dir",), (), ()),
    ("HOLDOUT folder in data/transfer", lambda m: _folder(m.data / "transfer" / "HOLDOUT"), ("holdout_dir",), (), ()),
    ("holdout folder in a --data-dir outside the repo",
     lambda m: _folder(m.add_data_dir(m.base / "usb" / "bars") / "holdout"), ("holdout_dir",), (), ()),
    ("manifest ends exactly at the cutoff", lambda m: _snap(m, m.data / "m1-2024b", K.AT_CUTOFF), (), (), ()),
    ("manifest ends 1 s after the cutoff", lambda m: _snap(m, m.data / "m1-2025", K.AFTER_CUTOFF),
     ("excluded_period",), (), ()),
    ("manifest ends in 2026", lambda m: _snap(m, m.data / "m1-2026", "2026-07-01T00:00:00Z"),
     ("excluded_period",), (), ()),
    ("per-file manifest before the cutoff",
     lambda m: _snap(m, m.data / "m1-file", "2024-12-31T23:59:00Z", per_file=True), (), (), ()),
    ("per-file manifest after the cutoff",
     lambda m: _snap(m, m.data / "m1-file", "2025-03-01T00:00:00Z", per_file=True), ("excluded_period",), (), ()),
    ("parquet without a manifest", lambda m: _bare(m.data / "m2" / "bars.parquet"), ("excluded_period",), (), ()),
    ("parquet deep in the data dir without a manifest", lambda m: _bare(m.data / "a" / "b" / "c" / "x.parquet"),
     ("excluded_period",), (), ()),
    ("folder manifest that lists another file",
     lambda m: _snap(m, m.data / "m3", K.BEFORE_CUTOFF, listed="other.parquet"), ("excluded_period",), (), ()),
    ("a second data file the folder manifest does not list",
     lambda m: _bare(m.data / "m1-2018-2024" / "extra.parquet"), ("excluded_period",), (), ()),
    ("csv without a manifest in the data dir", lambda m: _bare(m.data / "ticks" / "bars.csv"),
     ("excluded_period",), (), ()),
    ("hcc without a manifest in the data dir", lambda m: _bare(m.data / "cache" / "2024.hcc"),
     ("excluded_period",), (), ()),
    ("hc without a manifest in the data dir", lambda m: _bare(m.data / "cache" / "2024.hc"),
     ("excluded_period",), (), ()),
    ("tkc without a manifest in the data dir", lambda m: _bare(m.data / "cache" / "XAUUSDm.tkc"),
     ("excluded_period",), (), ()),
    ("csv with a manifest before the cutoff",
     lambda m: _snap(m, m.data / "csv-2024", K.BEFORE_CUTOFF, name="bars.csv"), (), (), ()),
    ("tkc with a manifest before the cutoff",
     lambda m: _snap(m, m.data / "ticks-2024", K.BEFORE_CUTOFF, name="XAUUSDm.tkc"), (), (), ()),
    ("late manifest in data/transfer", lambda m: _snap(m, m.data / "transfer", "2025-06-30T00:00:00Z"),
     ("excluded_period",), (), ()),
    ("late manifest in a --data-dir",
     lambda m: _snap(m, m.add_data_dir(m.base / "usb" / "export"), "2025-06-30T00:00:00Z"), ("excluded_period",),
     (), ()),
    ("valid manifest in a --data-dir", lambda m: _snap(m, m.add_data_dir(m.base / "usb" / "export"), K.AT_CUTOFF),
     (), (), ()),
    ("tkc under the repo outside the data dirs", lambda m: _bare(m.repo / "tools" / "XAUUSDm.tkc"),
     ("excluded_period",), (), ()),
    ("hcc under the repo outside the data dirs", lambda m: _bare(m.repo / "cache" / "2025.hcc"),
     ("excluded_period",), (), ()),
    ("hc under the repo outside the data dirs", lambda m: _bare(m.repo / "cache" / "2025.hc"),
     ("excluded_period",), (), ()),
    ("csv and parquet under the repo outside the data dirs are not checked",
     lambda m: (_bare(m.repo / "reports" / "r1-trades.csv"), _bare(m.repo / "research" / "out.parquet"))[0],
     (), (), ()),
    ("Parquet in mixed case without a manifest (v1.6 Q4)", lambda m: _bare(m.data / "m2" / "bars.Parquet"),
     ("excluded_period",), (), ()),
    ("CSV in upper case without a manifest (v1.6 Q4)", lambda m: _bare(m.data / "ticks" / "BARS.CSV"),
     ("excluded_period",), (), ()),
    ("HCC in upper case without a manifest (v1.6 Q4)", lambda m: _bare(m.data / "cache" / "2024.HCC"),
     ("excluded_period",), (), ()),
    ("TKC in upper case under the repo outside the data dirs (v1.6 Q4)",
     lambda m: _bare(m.repo / "tools" / "XAUUSDM.TKC"), ("excluded_period",), (), ()),
    ("a --data-dir that does not exist (v1.6 Q5)", lambda m: m.extra_data_dirs.append(m.base / "usb" / "typo") or {},
     (), ("excluded_period",), ("holdout_dir", "sentinel")),
)

_BROKEN = (
    ("invalid JSON", '{"files": [\n'),
    ("an empty file", ""),
    ("a JSON list", "[]\n"),
    ("no files field", _manifest_json(files=None)),
    ("no period_end_utc field", _manifest_json(end=None)),
    ("an entry without sha256", _manifest_json(files='[{"name": "bars.parquet"}]')),
    ("files is not a list", _manifest_json(files='"bars.parquet"')),
    ("a date without a time", _manifest_json(end='"2024-07-01"')),
    ("an offset instead of Z", _manifest_json(end='"2024-07-01T00:00:00+00:00"')),
    ("fractional seconds", _manifest_json(end='"2024-07-01T00:00:00.000Z"')),
    ("a space instead of T", _manifest_json(end='"2024-07-01 00:00:00Z"')),
    ("no Z", _manifest_json(end='"2024-07-01T00:00:00"')),
    ("month 13", _manifest_json(end='"2024-13-01T00:00:00Z"')),
    ("a number", _manifest_json(end="1719792000")),
)


@pytest.mark.parametrize("label, build, fail, unknown, ignore", _TREE, ids=[case[0] for case in _TREE])
def test_ac02_holdout_folders_and_excluded_period_files(tmp_path, monkeypatch, label, build, fail, unknown, ignore):
    ec = _ec()
    m = K.Machine(tmp_path)
    build(m)
    wrong = _verdict(m, ec, monkeypatch, fail=fail, unknown=unknown, ignore=ignore)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


@pytest.mark.parametrize("label, text", _BROKEN, ids=[case[0] for case in _BROKEN])
def test_ac02_broken_manifest_fails(tmp_path, monkeypatch, label, text):
    ec = _ec()
    m = K.Machine(tmp_path)
    _manifest(m, text)
    wrong = _verdict(m, ec, monkeypatch, fail=("excluded_period",))
    assert not wrong, f"AC-02 manifest with {label}:\n" + "\n".join(wrong)


def test_ac02_manifest_that_is_not_utf8_fails(tmp_path, monkeypatch):
    ec = _ec()
    m = K.Machine(tmp_path)
    _manifest(m, b"\xff\xfe" + _manifest_json().encode("ascii"))
    # The token search may also find this file unreadable as text, so the sentinel item is not compared.
    wrong = _verdict(m, ec, monkeypatch, fail=("excluded_period",), ignore=("sentinel",))
    assert not wrong, "AC-02 manifest that is not UTF-8:\n" + "\n".join(wrong)


def test_ac02_unreadable_manifest_is_unknown(tmp_path, monkeypatch):
    ec = _ec()
    m = K.Machine(tmp_path)
    manifest = m.data / "m1-2018-2024" / "manifest.json"
    # The manifest is also a .json the token search must read, so the sentinel item is UNKNOWN too.
    wrong = _verdict(m, ec, monkeypatch, deny=(manifest,), unknown=("excluded_period", "sentinel"))
    assert not wrong, "AC-02 unreadable manifest:\n" + "\n".join(wrong)


def test_ac02_late_manifest_fails_beside_an_unreadable_one(tmp_path, monkeypatch):
    ec = _ec()
    m = K.Machine(tmp_path)
    m.add_snapshot(m.data / "transfer", "2025-06-30T00:00:00Z")
    manifest = m.data / "m1-2018-2024" / "manifest.json"
    wrong = _verdict(m, ec, monkeypatch, deny=(manifest,), fail=("excluded_period",), unknown=("sentinel",))
    assert not wrong, "AC-02 late and unreadable manifests:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- sentinel

def _copy(path):
    K.put(path, K.SENTINEL_BYTES)
    return {}


def _token_text(path, prefix="pasted from the VPS: "):
    K.put(path, f"{prefix}{TOKEN}\n")
    return {}


def _vault(m):
    m.vault.mkdir(parents=True)
    return {}


def _vault_file(m):
    """Tests r2, F4: the Sentinel names the sentinel file itself as vault_path, and that file is here."""
    m.vault = m.base / "vps" / "vault" / K.SENTINEL_NAME
    K.put(m.vault, K.SENTINEL_BYTES)
    return {}


def _utf16(path, codec, bom):
    """Tests r2, F6: the token pasted alone into a file saved as UTF-16 (Windows PowerShell 5.1 redirection).

    The file holds only the token, with no text around it: with ASCII text before or after the token,
    the byte pattern of one byte order also matches inside the other (one byte off), so a search for
    one order alone would pass both kinds of case."""
    K.put(path, bom + TOKEN.encode(codec))
    return {}


def _onedrive_desktop(m):
    moved = m.onedrive / "Desktop"
    m.search_dirs = [m.downloads, moved, m.onedrive / "Documents", m.onedrive]
    K.put(moved / "export (1).json", K.SENTINEL_BYTES)
    return {}


def _cloud(path, content):
    K.put(path, content)
    return {"cloud": [path]}


def _cloud_in_onedrive_data_dir(m):
    folder = m.add_data_dir(m.onedrive / "Sochron data")
    return _cloud(folder / "notes.txt", f"{TOKEN}\n")


def _exact_size(content=b"\x89PNG"):
    return content + b"\0" * (K.SENTINEL_SIZE - len(content))


_SENTINEL = (
    # (label, build(m), fail, unknown)
    ("vault path exists on this machine", _vault, ("sentinel",), ()),
    ("file with the sentinel's name on Desktop (never opened)",
     lambda m: K.put(m.desktop / K.SENTINEL_NAME, "renamed note\n") and {}, ("sentinel",), ()),
    ("file with the sentinel's name in OneDrive",
     lambda m: K.put(m.onedrive / "Documents" / K.SENTINEL_NAME, "x\n") and {}, ("sentinel",), ()),
    ("file with the sentinel's name in data/transfer",
     lambda m: K.put(m.data / "transfer" / K.SENTINEL_NAME, "x\n") and {}, ("sentinel",), ()),
    ("renamed copy on Desktop", lambda m: _copy(m.desktop / "export.json"), ("sentinel",), ()),
    ("renamed copy on the Desktop that OneDrive moved", _onedrive_desktop, ("sentinel",), ()),
    ("renamed copy deep in Downloads", lambda m: _copy(m.downloads / "vps" / "2025" / "copy.json"), ("sentinel",), ()),
    ("renamed copy in Documents", lambda m: _copy(m.documents / "sentinel-backup.json"), ("sentinel",), ()),
    ("renamed copy in OneDrive", lambda m: _copy(m.onedrive / "Documents" / "keep.json"), ("sentinel",), ()),
    ("renamed copy in the repo", lambda m: _copy(m.repo / "docs" / "vps-export.json"), ("sentinel",), ()),
    ("same size, other content on Desktop",
     lambda m: K.put(m.desktop / "export.json", K.same_size_other_bytes()) and {}, (), ()),
    ("renamed .txt copy with the token in data/transfer",
     lambda m: _token_text(m.data / "transfer" / "copy.txt"), ("sentinel",), ()),
    ("token in the evidence file", lambda m: _token_text(m.repo / "docs" / "evidence" / "ENV-002.md", "token "),
     ("sentinel",), ()),
    ("token in a csv under the repo", lambda m: _token_text(m.repo / "notes.csv", "token,"), ("sentinel",), ()),
    ("token in a json in a --data-dir",
     lambda m: _token_text(m.add_data_dir(m.base / "usb" / "export") / "values.json", '{"t": "'), ("sentinel",), ()),
    ("token in a file named ENV-002-sentinel.json in data/transfer",
     lambda m: K.put(m.data / "transfer" / "ENV-002-sentinel.json", K.committed_values("C:\\vault")) and {},
     ("sentinel",), ()),
    ("token only in docs/evidence/ENV-002-sentinel.json", lambda m: {}, (), ()),
    ("cloud-only txt under the data dir (named)", lambda m: _cloud(m.data / "transfer" / "big.txt", "x\n"),
     (), ("sentinel",)),
    ("cloud-only md in the repo", lambda m: _cloud(m.repo / "docs" / "cloud-note.md", "# note\n"), (), ("sentinel",)),
    ("cloud-only json in a --data-dir",
     lambda m: _cloud(m.add_data_dir(m.base / "usb" / "export") / "report.json", "{}\n"), (), ("sentinel",)),
    ("cloud-only json of the sentinel's size in OneDrive",
     lambda m: _cloud(m.onedrive / "Documents" / "export.json", K.SENTINEL_BYTES), (), ("sentinel",)),
    ("cloud-only png of the sentinel's size in OneDrive",
     lambda m: _cloud(m.onedrive / "Pictures" / "scan.png", _exact_size()), (), ()),
    ("cloud-only json of another size in OneDrive",
     lambda m: _cloud(m.onedrive / "Documents" / "big.json", "{}\n"), (), ()),
    ("cloud-only txt in OneDrive", lambda m: _cloud(m.onedrive / "Documents" / "notes.txt", f"{TOKEN}\n"), (), ()),
    ("cloud-only txt in a --data-dir inside OneDrive", _cloud_in_onedrive_data_dir, (), ("sentinel",)),
    ("copy on Desktop beside a cloud-only txt in data (FAIL outranks UNKNOWN)",
     lambda m: (_copy(m.desktop / "export.json"), _cloud(m.data / "transfer" / "x.txt", "x\n"))[1], ("sentinel",), ()),
    ("unreadable json of the sentinel's size on Desktop",
     lambda m: (K.put(m.desktop / "export.json", K.same_size_other_bytes()), {"deny": [m.desktop / "export.json"]})[1],
     (), ("sentinel",)),
    ("unreadable txt in the data dir",
     lambda m: (K.put(m.data / "transfer" / "notes.txt", "x\n"), {"deny": [m.data / "transfer" / "notes.txt"]})[1],
     (), ("sentinel",)),
    # v1.6 Q4: names and extensions compare without case.
    ("the sentinel's name in lower case on Desktop",
     lambda m: K.put(m.desktop / K.SENTINEL_NAME.lower(), "renamed note\n") and {}, ("sentinel",), ()),
    ("the sentinel's name in upper case in Documents",
     lambda m: K.put(m.documents / K.SENTINEL_NAME.upper(), "renamed note\n") and {}, ("sentinel",), ()),
    ("renamed copy with .JSON on Desktop", lambda m: _copy(m.desktop / "EXPORT.JSON"), ("sentinel",), ()),
    ("renamed copy with .Json in OneDrive", lambda m: _copy(m.onedrive / "Documents" / "Keep.Json"), ("sentinel",), ()),
    ("token in a .TXT in data/transfer", lambda m: _token_text(m.data / "transfer" / "COPY.TXT"), ("sentinel",), ()),
    ("token in a .Md in the repo", lambda m: _token_text(m.repo / "docs" / "Notes.Md"), ("sentinel",), ()),
    ("token in a .CSV under the repo", lambda m: _token_text(m.repo / "NOTES.CSV", "token,"), ("sentinel",), ()),
    ("cloud-only .TXT under the data dir", lambda m: _cloud(m.data / "transfer" / "BIG.TXT", "x\n"), (), ("sentinel",)),
    ("cloud-only .JSON of the sentinel's size in OneDrive",
     lambda m: _cloud(m.onedrive / "Documents" / "EXPORT.JSON", K.SENTINEL_BYTES), (), ("sentinel",)),
    # v1.6 Q6: a never-open file that rule (3) or (4) would have to open is UNKNOWN, still never opened.
    (".env.json of the sentinel's size alone on Desktop",
     lambda m: K.put(m.desktop / ".env.json", K.SENTINEL_BYTES) and {}, (), ("sentinel",)),
    (".env.json of another size on Desktop is ignored",
     lambda m: K.put(m.desktop / ".env.json", '{"KEY": "x"}\n') and {}, (), ()),
    (".env.txt in data/transfer", lambda m: K.put(m.data / "transfer" / ".env.txt", "MT5_LOGIN=1\n") and {},
     (), ("sentinel",)),
    (".env.md in the repo", lambda m: K.put(m.repo / "docs" / ".env.md", "# env\n") and {}, (), ("sentinel",)),
    (".env.json in a --data-dir",
     lambda m: K.put(m.add_data_dir(m.base / "usb" / "export") / ".env.json", "{}\n") and {}, (), ("sentinel",)),
    ("id.key, cert.pem and vps.rdp in data/transfer are ignored",
     lambda m: [K.put(m.data / "transfer" / name, f"{TOKEN}\n") for name in ("id.key", "cert.pem", "vps.rdp")]
     and {}, (), ()),
    ("a .txt beside terminal64.exe in data/transfer",
     lambda m: (K.put(m.data / "transfer" / "MT5" / "terminal64.exe", b"MZ synthetic"),
                K.put(m.data / "transfer" / "MT5" / "notes.txt", "x\n"))[0] and {}, (), ("sentinel",)),
    ("a .txt beside Terminal64.EXE in data/transfer (v1.6 Q4)",
     lambda m: (K.put(m.data / "transfer" / "MT5" / "Terminal64.EXE", b"MZ synthetic"),
                K.put(m.data / "transfer" / "MT5" / "MQL5" / "notes.txt", "x\n"))[0] and {}, (), ("sentinel",)),
    ("a .json of the sentinel's size beside terminal64.exe in Downloads",
     lambda m: (K.put(m.downloads / "MT5" / "terminal64.exe", b"MZ synthetic"),
                K.put(m.downloads / "MT5" / "config" / "common.json", K.same_size_other_bytes()))[0] and {},
     (), ("sentinel",)),
    # v1.6 Q11: the repo search enters every folder, .git and .venv included.
    ("token in a .txt under <repo>/.venv",
     lambda m: _token_text(m.repo / ".venv" / "Lib" / "site-packages" / "pkg" / "notes.txt"), ("sentinel",), ()),
    ("token in a .md under <repo>/.git", lambda m: _token_text(m.repo / ".git" / "info" / "notes.md"), ("sentinel",), ()),
    ("renamed copy under <repo>/node_modules",
     lambda m: _copy(m.repo / "node_modules" / "pkg" / "fixture.json"), ("sentinel",), ()),
    ("token in a .json under the .git of a --data-dir",
     lambda m: _token_text(m.add_data_dir(m.base / "usb" / "export") / ".git" / "values.json", '{"t": "'),
     ("sentinel",), ()),
    # Tests r2, F4: vault_path in the file form of v1.6 Q8, and that file exists here.
    ("vault_path is the sentinel file and it exists on this machine", lambda m: _vault_file(m), ("sentinel",), ()),
    # Tests r2, F6 (v1.7): the token in UTF-16 text, LE and BE, with or without a BOM.
    ("token in a UTF-16LE .txt with a BOM in data/transfer",
     lambda m: _utf16(m.data / "transfer" / "pasted-le.txt", "utf-16-le", codecs.BOM_UTF16_LE), ("sentinel",), ()),
    ("token in a UTF-16BE .txt without a BOM in data/transfer",
     lambda m: _utf16(m.data / "transfer" / "pasted-be.txt", "utf-16-be", b""), ("sentinel",), ()),
    ("token in a UTF-16LE .txt without a BOM in data/transfer",
     lambda m: _utf16(m.data / "transfer" / "pasted-le-nobom.txt", "utf-16-le", b""), ("sentinel",), ()),
    ("token in a UTF-16BE .txt with a BOM in data/transfer",
     lambda m: _utf16(m.data / "transfer" / "pasted-be-bom.txt", "utf-16-be", codecs.BOM_UTF16_BE), ("sentinel",), ()),
)


@pytest.mark.parametrize("label, build, fail, unknown", _SENTINEL, ids=[case[0] for case in _SENTINEL])
def test_ac02_sentinel_rules(tmp_path, monkeypatch, label, build, fail, unknown):
    ec = _ec()
    m = K.Machine(tmp_path)
    extra = build(m) or {}
    wrong = _verdict(m, ec, monkeypatch, cloud=extra.get("cloud", ()), deny=extra.get("deny", ()), fail=fail,
                     unknown=unknown)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


def test_ac02_no_sentinel_is_unknown(tmp_path, monkeypatch):
    ec = _ec()
    wrong = _verdict(K.Machine(tmp_path), ec, monkeypatch, sentinel=False, unknown=("sentinel",))
    assert not wrong, "AC-02 no Sentinel:\n" + "\n".join(wrong)


_REPO_IN_DESKTOP = (
    ("token txt in data/transfer", lambda m: _token_text(m.data / "transfer" / "copy.txt"), ("sentinel",), ()),
    ("token md in the repo docs", lambda m: _token_text(m.repo / "docs" / "notes.md"), ("sentinel",), ()),
    ("cloud-only md in the repo", lambda m: _cloud(m.repo / "docs" / "cloud-note.md", "# note\n"), (), ("sentinel",)),
    ("cloud-only txt in data/transfer", lambda m: _cloud(m.data / "transfer" / "values.txt", "1\n"), (), ("sentinel",)),
)


@pytest.mark.parametrize("label, build, fail, unknown", _REPO_IN_DESKTOP, ids=[case[0] for case in _REPO_IN_DESKTOP])
def test_ac02_repo_under_a_search_dir_follows_the_repo_rules(tmp_path, monkeypatch, label, build, fail, unknown):
    ec = _ec()
    m = K.Machine(tmp_path, repo_in_desktop=True)
    extra = build(m) or {}
    wrong = _verdict(m, ec, monkeypatch, cloud=extra.get("cloud", ()), fail=fail, unknown=unknown)
    assert not wrong, f"AC-02 repo under Desktop, {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- tests r2: manifests and folders

def _cloud_manifest_in_onedrive(m):
    """Tests r2, F2: a --data-dir in OneDrive whose folder manifest is not downloaded."""
    folder = m.add_data_dir(m.onedrive / "Sochron data")
    m.add_snapshot(folder, K.BEFORE_CUTOFF)
    return [folder / "manifest.json"]


def _cloud_per_file_manifest(m):
    folder = m.data / "m1-cloud"
    m.add_snapshot(folder, K.BEFORE_CUTOFF, per_file=True)
    return [folder / "bars.parquet.manifest.json"]


_CLOUD_MANIFESTS = (
    ("a cloud-only manifest.json in a --data-dir under OneDrive", _cloud_manifest_in_onedrive),
    ("a cloud-only per-file manifest under <repo>/data", _cloud_per_file_manifest),
)


@pytest.mark.parametrize("label, build", _CLOUD_MANIFESTS, ids=[case[0] for case in _CLOUD_MANIFESTS])
def test_ac02_cloud_only_manifest_is_never_opened_and_unknown(tmp_path, monkeypatch, label, build):
    """v1.7 (tests-r1 F2): the manifest is not opened; excluded_period and sentinel are UNKNOWN."""
    ec = _ec()
    m = K.Machine(tmp_path)
    cloud = build(m)
    wrong = _verdict(m, ec, monkeypatch, cloud=cloud, unknown=("excluded_period", "sentinel"))
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


def _locked_folder(path, *names):
    """A folder (with files in it) whose listing the audit hook refuses (tests r2, F8)."""
    for name in names:
        K.put(path / name, f"{TOKEN}\n" if name.endswith(".txt") else K.PARQUET)
    path.mkdir(parents=True, exist_ok=True)
    return {"deny_list": [path]}


_UNLISTABLE = (
    ("a folder under data/transfer", lambda m: _locked_folder(m.data / "transfer" / "locked", "bars.parquet", "a.txt"),
     ("holdout_dir", "excluded_period", "sentinel")),
    ("a folder under a --data-dir",
     lambda m: _locked_folder(m.add_data_dir(m.base / "usb" / "export") / "locked", "a.txt"),
     ("holdout_dir", "excluded_period", "sentinel")),
    ("a folder under the repo outside the data dirs", lambda m: _locked_folder(m.repo / "private", "a.txt"),
     ("holdout_dir", "excluded_period", "sentinel")),
    ("a folder under Desktop", lambda m: _locked_folder(m.desktop / "locked", "a.txt"), ("sentinel",)),
    ("a folder under OneDrive", lambda m: _locked_folder(m.onedrive / "Documents" / "locked"), ("sentinel",)),
)


@pytest.mark.parametrize("label, build, unknown", _UNLISTABLE, ids=[case[0] for case in _UNLISTABLE])
def test_ac02_folder_that_cannot_be_listed_is_unknown(tmp_path, monkeypatch, label, build, unknown):
    """v1.7 (tests-r1 F8): a folder that cannot be listed makes every item that searches it UNKNOWN."""
    ec = _ec()
    m = K.Machine(tmp_path)
    extra = build(m)
    wrong = _verdict(m, ec, monkeypatch, deny_list=extra["deny_list"], unknown=unknown)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- files that are never opened

_CLOSED_NAMES = (".env", ".env.json", ".env.example", ".env.local", ".env.txt", ".env.md", ".env.csv", "id.key",
                 "cert.pem", "store.pfx", "vps.rdp")


def _closed_beside_a_copy(m):
    """A sentinel copy on Desktop with every never-open name beside it, each holding the sentinel's bytes."""
    _copy(m.desktop / "export.json")
    for name in _CLOSED_NAMES:
        K.put(m.desktop / name, K.SENTINEL_BYTES)
    return {}


def _closed_beside_a_token(m):
    """A token copy in data/transfer with the never-open names beside it, each holding the token.

    .env.csv is left out here: in a data dir it is also a *.csv that needs a manifest, a second rule
    this case does not test. The Desktop case keeps it."""
    _token_text(m.data / "transfer" / "copy.txt")
    for name in _CLOSED_NAMES:
        if not name.endswith(".csv"):
            _token_text(m.data / "transfer" / name)
    return {}


def _terminal_on_desktop(m):
    folder = m.desktop / "MT5 Portable"
    K.put(folder / "terminal64.exe", b"MZ synthetic terminal")
    _copy(folder / "common.json")
    _copy(folder / "config" / "accounts.json")
    _copy(folder / "MQL5" / "Files" / "export.json")
    _token_text(folder / "notes.txt")
    _copy(m.desktop / "export.json")
    return {}


def _terminal_in_data(m):
    folder = m.data / "transfer" / "MT5"
    K.put(folder / "terminal64.exe", b"MZ synthetic terminal")
    _token_text(folder / "notes.txt")
    _token_text(folder / "MQL5" / "Files" / "values.json", '{"t": "')
    _token_text(m.data / "transfer" / "copy.txt")
    return {}


def _metaquotes_in_a_data_dir(m):
    m.add_data_dir(m.profile / "AppData")
    terminal = m.appdata / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075"
    _token_text(terminal / "config" / "accounts.json", '{"t": "')
    _token_text(m.appdata / "MetaQuotes" / "notes.txt")
    _copy(m.desktop / "export.json")
    return {}


_CLOSED = (
    ("never-open names beside a copy on Desktop (.env.json included)", _closed_beside_a_copy, {},
     ("sentinel",)),
    ("never-open names beside a token copy in data/transfer", _closed_beside_a_token, {}, ("sentinel",)),
    ("a folder with terminal64.exe on Desktop", _terminal_on_desktop,
     {"terminal_paths": (r"C:\Users\owner\Desktop\MT5 Portable\terminal64.exe",)}, ("terminal_install", "sentinel")),
    ("a folder with terminal64.exe in data/transfer", _terminal_in_data, {}, ("sentinel",)),
    ("APPDATA MetaQuotes inside a --data-dir", _metaquotes_in_a_data_dir, {"metaquotes_exists": True},
     ("terminal_data", "sentinel")),
)


@pytest.mark.parametrize("label, build, facts, fail", _CLOSED, ids=[case[0] for case in _CLOSED])
def test_ac02_closed_files_are_never_opened(tmp_path, monkeypatch, label, build, facts, fail):
    ec = _ec()
    m = K.Machine(tmp_path)
    build(m)
    wrong = _verdict(m, ec, monkeypatch, facts=facts, fail=fail)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


_SEARCH_DIR_READS = (
    ("a .txt copy on Desktop", lambda m: K.put(m.desktop / "copy.txt", K.SENTINEL_BYTES)),
    ("a token .md in Documents", lambda m: _token_text(m.documents / "notes.md")),
    ("a .json of another size in Downloads", lambda m: K.put(m.downloads / "big.json", K.SENTINEL_BYTES + b" ")),
    ("a .png of the sentinel's size in OneDrive", lambda m: K.put(m.onedrive / "scan.png", _exact_size())),
)


@pytest.mark.parametrize("label, build", _SEARCH_DIR_READS, ids=[case[0] for case in _SEARCH_DIR_READS])
def test_ac02_search_dirs_open_only_json_files_of_the_sentinel_size(tmp_path, monkeypatch, label, build):
    """Outside the repo and data dirs only rule (3) reads files. What else such a file could prove is not
    part of the contract, so the sentinel item is not compared; the read rules are."""
    ec = _ec()
    m = K.Machine(tmp_path)
    build(m)
    wrong = _verdict(m, ec, monkeypatch, ignore=("sentinel",))
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- is_cloud_only

_ATTRIBUTES = (
    ("RECALL_ON_DATA_ACCESS", 0x00400000, True),
    ("RECALL_ON_OPEN", 0x00040000, True),
    ("RECALL_ON_DATA_ACCESS with ARCHIVE", 0x00400000 | 0x20, True),
    ("RECALL_ON_OPEN with READONLY", 0x00040000 | 0x01, True),
    ("ARCHIVE and NORMAL only", 0x20 | 0x80, False),
    ("no attribute bits", 0, False),
    ("no st_file_attributes (Linux)", None, False),
)


@pytest.mark.parametrize("label, attributes, expected", _ATTRIBUTES, ids=[case[0] for case in _ATTRIBUTES])
def test_ac02_is_cloud_only_reads_the_recall_attributes(tmp_path, monkeypatch, label, attributes, expected):
    ec = K.envcheck(AC, "is_cloud_only")
    target = K.put(tmp_path / "OneDrive" / "file.json", "{}\n")
    real_stat = os.stat

    def fake_stat(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if isinstance(path, int) or K.norm(path) != K.norm(target):
            return result
        values = {name: getattr(result, name) for name in ("st_mode", "st_ino", "st_dev", "st_nlink", "st_uid",
                                                           "st_gid", "st_size", "st_atime", "st_mtime", "st_ctime")}
        if attributes is not None:
            values["st_file_attributes"] = attributes
        return SimpleNamespace(**values)

    monkeypatch.setattr(os, "stat", fake_stat)
    wrong = []
    with K.recording() as audit:
        answers = [ec.is_cloud_only(target), ec.is_cloud_only(str(target))]
    if answers != [expected, expected]:
        wrong.append(f"is_cloud_only gave {answers} for Path and str, expected {expected}")
    if K.norm(target) in audit.opened():
        wrong.append("is_cloud_only opened the file")
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)
