r"""ENV-002 v2.6 contract tests for AC-02, macOS cases on evaluate
(docs/contracts/ENV-002-research-host-separation.md: is_cloud_only and dataless folders (v2.1 F6),
`.<name>.icloud` files, the symlink exception of `.venv/bin` (v2.1 F5), Privacy (TCC) folders, a root
below a dataless folder (v2.2 r2 F12) and appdata folders under a data dir (v2.3 r3 F28)); run pytest
from the repository root.

evaluate does not know the platform (contract v2.1 F1), so these cases run evaluate on the fake Mac of
darwinkit.py with fake Facts (envkit.VALID_FACTS) and the fake is_cloud_only, and check the v1.x read
rules with envkit.side_effects on every call. Conventions D1-D8 are in darwinkit.py; the ones below are
specific to this file:
D14. A `.<name>.icloud` placeholder holds a few bytes of a binary plist; it is never opened. The symlinks
     are made before the audit hook records (os.symlink is one of envkit's forbidden events) and point at
     os.path.realpath(sys.executable), the interpreter running the tests; a copy of it is made with
     shutil.copyfile, also before the recording.
"""

import importlib.util
import os
import shutil
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
NAMES = ("Facts", "ResearchRoots", "Sentinel", "Report", "evaluate", "is_cloud_only")
PLACEHOLDER = b"bplist00 synthetic iCloud placeholder"
SEARCHED = ("holdout_dir", "excluded_period", "sentinel")


def _ec():
    return K.envcheck(AC, *NAMES)


def _judge(tmp_path, monkeypatch, build, fail=(), unknown=(), facts=None):
    ec = _ec()
    mac = D.Mac(tmp_path)
    options = build(mac) or {}
    report, wrong, audit = D.judge_evaluate(ec, monkeypatch, mac, K.facts(ec, **(facts or {})), mac.sentinel(ec),
                                            cloud=options.get("cloud", ()), deny_list=options.get("deny_list", ()))
    wrong = K.check_report(report, fail=fail, unknown=unknown) + wrong
    for folder in options.get("untouched", ()):
        wrong += D.touched_under(audit, folder)
    return wrong


# ------------------------------------------------------------------------- dataless files and folders, .icloud

def _cloud_file(path, content):
    K.put(path, content)
    return {"cloud": [path]}


def _placeholder(path):
    K.put(path, PLACEHOLDER)
    return {}


def _dataless_folder(folder, *files):
    for name, content in files:
        K.put(folder / name, content)
    return {"cloud": [folder], "untouched": [folder]}


def _late_snapshot(mac):
    folder = mac.data / "cloud-bars"
    mac.add_snapshot(folder, K.AFTER_CUTOFF)
    return {"cloud": [folder], "untouched": [folder]}


def _privacy_folder(mac):
    folder = mac.documents / "Private"
    K.put(folder / "export.json", K.SENTINEL_BYTES)
    return {"deny_list": [folder]}


_CLOUD = (
    # (label, build(mac) -> options, fail, unknown)
    ("a dataless .json of the sentinel's size in iCloud Drive (UNKNOWN, never opened)",
     lambda m: _cloud_file(m.icloud / "export.json", K.SENTINEL_BYTES), (), ("sentinel",)),
    ("a dataless .json of another size in iCloud Drive (PASS, never opened)",
     lambda m: _cloud_file(m.icloud / "big.json", "{}\n"), (), ()),
    ("a dataless .txt under <repo>/data (UNKNOWN, never opened)",
     lambda m: _cloud_file(m.data / "transfer" / "notes.txt", f"{TOKEN}\n"), (), ("sentinel",)),
    (".notes.txt.icloud under a data dir (UNKNOWN)", lambda m: _placeholder(m.data / "transfer" / ".notes.txt.icloud"),
     (), ("excluded_period", "sentinel")),
    (".<sentinel name>.icloud in iCloud Drive only (FAIL)",
     lambda m: _placeholder(m.icloud / f".{K.SENTINEL_NAME}.icloud"), ("sentinel",), ()),
    (".<SENTINEL NAME>.ICLOUD in iCloud Drive only (FAIL: no case)",
     lambda m: _placeholder(m.icloud / f".{K.SENTINEL_NAME.upper()}.ICLOUD"), ("sentinel",), ()),
    (".x.json.icloud in iCloud Drive only (UNKNOWN)", lambda m: _placeholder(m.icloud / ".x.json.icloud"), (),
     ("sentinel",)),
    (".x.png.icloud in iCloud Drive only (skipped: PASS)", lambda m: _placeholder(m.icloud / ".x.png.icloud"), (), ()),
    (".<sentinel name>.icloud under <repo>/data (FAIL of sentinel, UNKNOWN of excluded_period)",
     lambda m: _placeholder(m.data / "transfer" / f".{K.SENTINEL_NAME}.icloud"), ("sentinel",), ("excluded_period",)),
    ("a dataless folder in iCloud Drive (UNKNOWN, never listed)",
     lambda m: _dataless_folder(m.icloud / "Archive", ("export.json", K.SENTINEL_BYTES)), (), ("sentinel",)),
    ("a dataless folder under <repo>/data (UNKNOWN, never listed)", _late_snapshot, (), SEARCHED),
    ("a folder in Documents that Privacy keeps from listing (UNKNOWN)", _privacy_folder, (), ("sentinel",)),
)


@pytest.mark.parametrize("label, build, fail, unknown", _CLOUD, ids=[case[0] for case in _CLOUD])
def test_ac02_dataless_and_icloud_files_on_evaluate(tmp_path, monkeypatch, label, build, fail, unknown):
    """v2.0; v2.1 F6, F12; v2.2 r2 F30; v2.4 r4 F54."""
    wrong = _judge(tmp_path, monkeypatch, build, fail=fail, unknown=unknown)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)


_ANCESTOR = (
    ("a --data-dir", SEARCHED),
    ("a search dir", ("sentinel",)),
)


@pytest.mark.parametrize("kind, unknown", _ANCESTOR, ids=[case[0] for case in _ANCESTOR])
def test_ac02_a_root_below_a_dataless_folder_is_unknown_and_never_reached(tmp_path, monkeypatch, kind, unknown):
    """v2.2 r2 F12: the ancestors are checked from the top first; the root is never stat'ed or listed."""
    ec = _ec()
    mac = D.Mac(tmp_path)
    dataless = mac.base / "Cloud"
    root = dataless / "Archive" / "bars"
    if kind == "a --data-dir":
        mac.add_snapshot(root, K.AFTER_CUTOFF)
        mac.extra_data_dirs.append(root)
    else:
        K.put(root / "export.json", K.SENTINEL_BYTES)
        mac.search_dirs.append(root)
    stats = D.StatRecorder(monkeypatch)
    report, wrong, audit = D.judge_evaluate(ec, monkeypatch, mac, K.facts(ec), mac.sentinel(ec), cloud=[dataless],
                                            stats=stats)
    wrong = K.check_report(report, unknown=unknown) + wrong + D.touched_under(audit, dataless)
    wrong += [f"stat {path}" for path in stats.strictly_under(dataless)]
    assert not wrong, f"AC-02 {kind} below a dataless folder:\n" + "\n".join(wrong)


def test_ac02_a_metatrader_folder_in_appdata_under_a_data_dir_is_unknown_and_never_reached(tmp_path, monkeypatch):
    """v2.3 r3 F28 (every platform): metaquotes_exists False, appdata under a covering data dir, a
    `metatrader 5` folder at level 0 of appdata with a token .txt: the three items that search the data dir
    are UNKNOWN and nothing at or under that folder is listed or opened."""
    ec = _ec()
    mac = D.Mac(tmp_path)
    folder = mac.appsupport / "metatrader 5"
    K.put(folder / "notes.txt", f"pasted from the VPS: {TOKEN}\n")
    mac.extra_data_dirs.append(mac.library)
    report, wrong, audit = D.judge_evaluate(ec, monkeypatch, mac, K.facts(ec, metaquotes_exists=False),
                                            mac.sentinel(ec))
    wrong = K.check_report(report, unknown=SEARCHED) + wrong + D.touched_under(audit, folder)
    assert not wrong, "AC-02 metatrader 5 in appdata under a data dir:\n" + "\n".join(wrong)


# ------------------------------------------------------------------------- the symlink exception of .venv/bin

def _interpreter():
    return Path(os.path.realpath(sys.executable))


def _bin(mac):
    folder = mac.repo / ".venv" / "bin"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _link(link, target):
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, link)


def _python_to_interpreter(mac):
    _link(_bin(mac) / "python", _interpreter())


def _python3_to_python(mac):
    folder = _bin(mac)
    _link(folder / "python", _interpreter())
    os.symlink("python", folder / "python3")


def _through_an_outside_link(mac):
    outside = mac.base / "tools" / "py"
    _link(outside, _interpreter())
    _link(_bin(mac) / "python", outside)


def _python39_to_another_file(mac):
    other = K.put(mac.base / "other" / "tool", b"#!/bin/sh\nexit 0\n")
    _link(_bin(mac) / "python3.9", other)


def _python_to_a_copy(mac):
    copy = mac.base / "copy" / "python3.12"
    copy.parent.mkdir(parents=True)
    shutil.copyfile(_interpreter(), copy)
    _link(_bin(mac) / "python", copy)


def _broken(mac):
    _link(_bin(mac) / "python", mac.base / "missing" / "python")


def _loop(mac):
    link = _bin(mac) / "python"
    os.symlink(link, link)


def _to_a_folder(mac):
    folder = mac.base / "somedir"
    folder.mkdir()
    _link(_bin(mac) / "python", folder)


def _other_name(mac):
    _link(_bin(mac) / "pip3", _interpreter())


def _python_elsewhere(mac):
    _link(mac.repo / "tools" / "python", _interpreter())


_SYMLINKS = (
    # (label, build(mac), unknown)
    (".venv/bin/python -> the running interpreter (not UNKNOWN, never opened)", _python_to_interpreter, ()),
    (".venv/bin/python3 -> python -> the running interpreter (not UNKNOWN)", _python3_to_python, ()),
    (".venv/bin/python -> a link outside the repo -> the running interpreter (not UNKNOWN)",
     _through_an_outside_link, ()),
    (".venv/bin/python3.9 -> an ordinary file outside the repo (UNKNOWN)", _python39_to_another_file, SEARCHED),
    (".venv/bin/python -> a copy of the interpreter elsewhere (UNKNOWN)", _python_to_a_copy, SEARCHED),
    (".venv/bin/python is a broken link (UNKNOWN)", _broken, SEARCHED),
    (".venv/bin/python is a link that loops (UNKNOWN)", _loop, SEARCHED),
    (".venv/bin/python -> a folder (UNKNOWN)", _to_a_folder, SEARCHED),
    (".venv/bin/pip3 -> the running interpreter, another name (UNKNOWN)", _other_name, SEARCHED),
    ("<repo>/tools/python -> the running interpreter, outside .venv/bin (UNKNOWN)", _python_elsewhere, SEARCHED),
)


@pytest.mark.parametrize("label, build, unknown", _SYMLINKS, ids=[case[0] for case in _SYMLINKS])
def test_ac02_the_venv_interpreter_link_is_the_only_symlink_excused(tmp_path, monkeypatch, label, build, unknown):
    """v2.1 F5: a python, python3 or python3.N link at level 0 of <repo>/.venv/bin that ends at the running
    interpreter (same st_dev and st_ino) is excused and never opened; every other link stays UNKNOWN."""
    wrong = _judge(tmp_path, monkeypatch, lambda mac: build(mac) or {}, unknown=unknown)
    assert not wrong, f"AC-02 {label}:\n" + "\n".join(wrong)
