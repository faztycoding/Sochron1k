r"""ENV-002 v2.6 contract tests for AC-05 on darwin: the CLI (main) and require_research_host
(docs/contracts/ENV-002-research-host-separation.md: "CLI (main) พิมพ์บรรทัด reader:", host_lines() before
render, default_roots on darwin raising OSError (v2.1 F9, F10), the sentinel file under a terminal_data
folder (v2.2 r2 F12) and the roots: line without the token (v2.1 F11)); run pytest from the repository root.

The fake Mac and fake OS are those of darwinkit.py (conventions D1-D8). main(argv) and its exit code
follow conventions 18 and 19 of test_ac05_require_research_host.py. Where a case does not test
default_roots, it is replaced by a fake that returns the fake Mac's roots (as in the v1.x AC-05 tests),
because the real one builds the repo root from the module's own location.
"""

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
AC = "AC-05"
TOKEN = K.TOKEN
NAMES = ("main", "require_research_host", "ResearchHostError")


def _host(tmp_path, monkeypatch, *, platform="darwin"):
    ec = D.reader(AC, *NAMES)
    mac = D.Mac(tmp_path)
    D.FakeOS(ec, mac).install(monkeypatch, ec, platform=platform)
    return ec, mac


def _fake_roots(monkeypatch, ec, mac):
    def default_roots(*args, **kwargs):
        return mac.roots(ec)

    monkeypatch.setattr(ec, "default_roots", default_roots)


def _fake_collect(monkeypatch, ec):
    monkeypatch.setattr(ec, "collect", lambda roots: K.facts(ec))


def _cli(ec, argv, capsys):
    """(exit code, standard output, standard error) of envcheck.main(argv) (convention 18)."""
    capsys.readouterr()
    try:
        code = ec.main(list(argv))
    except SystemExit as stop:
        code = stop.code
    captured = capsys.readouterr()
    if code is None:
        return 0, captured.out, captured.err
    return (code if isinstance(code, int) and not isinstance(code, bool) else 1), captured.out, captured.err


def _argv(mac, sentinel_file=None):
    return ["--role", "research", "--sentinel-file", str(sentinel_file or mac.repo.joinpath(*K.SENTINEL_EVIDENCE))]


def _lines(out):
    return out.rstrip("\n").splitlines()


def _token_shown(out, err):
    return [f"the token is on {name}" for name, text in (("standard output", out), ("standard error", err))
            if TOKEN in text]


# ------------------------------------------------------------------------- the host lines before the report

_PLATFORMS = (
    ("darwin", ("reader: darwin", "roots:", "processes: not read", "mounts: not read", "wine: not read")),
    ("linux", ("reader: none", "roots:")),
)


@pytest.mark.parametrize("platform, prefixes", _PLATFORMS, ids=[case[0] for case in _PLATFORMS])
def test_ac05_main_prints_every_host_line_before_the_report(tmp_path, monkeypatch, capsys, platform, prefixes):
    """v2.1 F1; v2.3 r3 F25: main prints host_lines() first; with collect replaced darwin gives five lines
    (reader, roots and three `not read`, order not compared), another reader two; the last line is still
    RESEARCH HOST."""
    ec, mac = _host(tmp_path, monkeypatch, platform=platform)
    _fake_roots(monkeypatch, ec, mac)
    _fake_collect(monkeypatch, ec)
    code, out, err = _cli(ec, _argv(mac), capsys)
    printed, host = _lines(out), ec.host_lines()
    wrong = _token_shown(out, err)
    if printed[:len(host)] != list(host):
        wrong.append(f"the output does not start with host_lines() {list(host)}")
    if len(host) != len(prefixes) or any(sum(text.startswith(prefix) for text in host) != 1 for prefix in prefixes):
        wrong.append(f"host_lines() {list(host)}, expected one line starting with each of {list(prefixes)}")
    if code != 0 or not printed or printed[-1] != "RESEARCH HOST: PASS":
        wrong.append(f"exit {code}, last line {printed[-1:]!r}, expected 0 and 'RESEARCH HOST: PASS'")
    assert not wrong, f"AC-05 main on {platform}:\n" + "\n".join(wrong) + f"\noutput:\n{out}"


def _metatrader_app(mac):
    K.put(mac.applications / "MetaTrader 5.app" / "Contents" / "MacOS" / "app", b"\xcf\xfa\xed\xfe synthetic")
    return []


_VERDICTS = (
    ("a clean Mac", lambda mac: [], "PASS"),
    ("MetaTrader 5.app in /Applications", _metatrader_app, "FAIL"),
    ("/Applications cannot be listed", lambda mac: [mac.applications], "UNKNOWN"),
)


@pytest.mark.parametrize("label, build, verdict", _VERDICTS, ids=[case[0] for case in _VERDICTS])
def test_ac05_main_on_darwin_exits_zero_only_for_pass(tmp_path, monkeypatch, capsys, label, build, verdict):
    """AC-05 with the real darwin collect: exit 0 only for PASS, the last line gives the verdict."""
    ec, mac = _host(tmp_path, monkeypatch)
    _fake_roots(monkeypatch, ec, mac)
    deny_list = build(mac)
    with K.recording(deny_list=deny_list):
        code, out, err = _cli(ec, _argv(mac), capsys)
    printed = _lines(out)
    wrong = _token_shown(out, err)
    if (code == 0) != (verdict == "PASS") or not printed or printed[-1] != f"RESEARCH HOST: {verdict}":
        wrong.append(f"exit {code}, last line {printed[-1:]!r}, expected 'RESEARCH HOST: {verdict}'")
    assert not wrong, f"AC-05 {label}:\n" + "\n".join(wrong) + f"\noutput:\n{out}"


def test_ac05_cli_roots_line_never_shows_the_token(tmp_path, monkeypatch, capsys):
    """v2.1 F11: a root path that holds the token prints <token> in the roots: line; the token is printed nowhere."""
    ec, mac = _host(tmp_path, monkeypatch)
    folder = mac.home / f"Exports {TOKEN}"
    folder.mkdir()
    mac.search_dirs.append(folder)
    _fake_roots(monkeypatch, ec, mac)
    _fake_collect(monkeypatch, ec)
    code, out, err = _cli(ec, _argv(mac), capsys)
    roots_line = next((text for text in _lines(out) if text.startswith("roots:")), "")
    wrong = _token_shown(out, err)
    if "<token>" not in roots_line:
        wrong.append(f"roots line {roots_line!r} does not show <token>")
    assert not wrong, "AC-05 roots line:\n" + "\n".join(wrong) + f"\noutput:\n{out}"


# ------------------------------------------------------------------------- default_roots raises on darwin

_UNREADABLE_ROOTS = (
    ("~/Library/PlayOnMac/wineprefix", lambda mac: mac.wine_source("PlayOnMac")),
    ("~/Library/Application Support/CrossOver/Bottles", lambda mac: mac.wine_source("CrossOver")),
    ("~/Library/CloudStorage", lambda mac: mac.library / "CloudStorage"),
)


@pytest.mark.parametrize("label, pick", _UNREADABLE_ROOTS, ids=[case[0] for case in _UNREADABLE_ROOTS])
def test_ac05_cli_is_unknown_and_exits_one_when_default_roots_cannot_read_a_folder(tmp_path, monkeypatch, capsys,
                                                                                  label, pick):
    """v2.1 F9, F10; v2.2 r2 F29; v2.5 r5 F59: `reader: darwin` first, no roots: line, the last line
    `RESEARCH HOST: UNKNOWN`, exit 1."""
    ec, mac = _host(tmp_path, monkeypatch)
    folder = pick(mac)
    folder.mkdir(parents=True, exist_ok=True)
    with K.recording(deny_list=[folder]):
        code, out, err = _cli(ec, _argv(mac), capsys)
    printed = _lines(out)
    wrong = _token_shown(out, err)
    if code != 1:
        wrong.append(f"exit {code}, expected 1")
    if not printed or printed[0] != "reader: darwin":
        wrong.append(f"first line {printed[:1]!r}, expected 'reader: darwin'")
    if any(text.startswith("roots:") for text in printed):
        wrong.append("a roots: line is printed although default_roots failed")
    if not printed or printed[-1] != "RESEARCH HOST: UNKNOWN":
        wrong.append(f"last line {printed[-1:]!r}, expected 'RESEARCH HOST: UNKNOWN'")
    assert not wrong, f"AC-05 {label} unreadable:\n" + "\n".join(wrong) + f"\noutput:\n{out}"


@pytest.mark.parametrize("label, pick", _UNREADABLE_ROOTS, ids=[case[0] for case in _UNREADABLE_ROOTS])
def test_ac05_the_gate_raises_when_default_roots_cannot_read_a_folder(tmp_path, monkeypatch, label, pick):
    """v2.1 F9, F10: require_research_host() without roots raises ResearchHostError (the v1.9 r1 F5 path)."""
    ec, mac = _host(tmp_path, monkeypatch)
    folder = pick(mac)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with K.recording(deny_list=[folder]):
            report = ec.require_research_host(sentinel=mac.sentinel(ec))
    except ec.ResearchHostError as error:
        assert TOKEN not in str(error), "AC-05: the error message holds the sentinel token"
        return
    except Exception as error:  # the wrong exception type is the failure reported
        pytest.fail(f"AC-05 {label}: raised {error!r}, expected ResearchHostError", pytrace=False)
    pytest.fail(f"AC-05 {label}: require_research_host returned {K.summary(report)}", pytrace=False)


# ------------------------------------------------------------------------- the sentinel file

def test_ac05_a_sentinel_file_under_a_terminal_data_folder_is_never_opened(tmp_path, monkeypatch, capsys):
    """v2.2 r2 F12, F28: --sentinel-file under <appdata>/Metatrader 5/ is not opened; sentinel is UNKNOWN."""
    ec, mac = _host(tmp_path, monkeypatch)
    values = K.put(mac.appsupport / "Metatrader 5" / "ENV-002-sentinel.json", K.committed_values(str(mac.vault)))
    _fake_roots(monkeypatch, ec, mac)
    _fake_collect(monkeypatch, ec)
    with K.recording() as audit:
        code, out, err = _cli(ec, _argv(mac, values), capsys)
    printed = _lines(out)
    wrong = _token_shown(out, err) + D.touched_under(audit, values.parent)
    if code == 0 or not printed or printed[-1] != "RESEARCH HOST: UNKNOWN":
        wrong.append(f"exit {code}, last line {printed[-1:]!r}, expected non-zero and 'RESEARCH HOST: UNKNOWN'")
    assert not wrong, "AC-05 sentinel file under Metatrader 5:\n" + "\n".join(wrong) + f"\noutput:\n{out}"
