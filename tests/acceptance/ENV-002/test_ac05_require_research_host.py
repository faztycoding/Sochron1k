"""Approved ENV-002 v1.7 contract tests for AC-05 (docs/contracts/ENV-002-research-host-separation.md);
run pytest from the repository root. Tests r2 (docs/reviews/ENV-002-tests-r1.md F1, F7) made the
`__main__` guard check stricter and added the stderr and error-text checks.

Contract names used: Facts, ResearchRoots, Sentinel, Report, collect and is_cloud_only (both replaced by
fakes), evaluate, research_host_report, require_research_host, ResearchHostError, default_roots and main
(contract v1.6 Q9; default_roots replaced by a fake), and scripts/env/make_sentinel.py for the end-to-end
case. The fake research host, Facts and read-rule checks are those of
test_ac02_research_host_evaluate.py (envkit.py); its conventions 1-14 hold here too.

Conventions the contract leaves to these tests (also in docs/handoff/ENV-002.md):
15. research_host_report(roots=R, sentinel=S) is evaluate(collect(R), R, S): the tests replace
    envcheck.collect, looked up at call time, by a fake that returns fixed Facts and records R.
16. envcheck.default_roots(extra_data_dirs) (v1.6 Q9), a module-level function looked up at call time,
    returns this machine's ResearchRoots with data_dirs (<repo>/data, *extra_data_dirs).
    research_host_report and require_research_host use default_roots(()) when roots is None, and the
    CLI builds its roots with the --data-dir values (as Path, in their order). The tests replace it,
    because the real one needs Windows shell folders.
17. require_research_host returns the report when its verdict is PASS: the same role, verdict and item
    statuses that evaluate gives for the same inputs. Otherwise it raises ResearchHostError, a
    ValueError, whose message names every item that is not PASS and never holds the token (v1.7,
    tests-r1 F7).
18. The CLI is envcheck.main(argv) (v1.6 Q9), argv being the arguments after the module name. It returns
    the exit code or raises SystemExit (None counts as 0, a non-int as 1). It prints the report to
    standard output, naming every item, and the last line is "RESEARCH HOST: <verdict>". The token is
    in neither standard output nor standard error (v1.6 Q7, v1.7 tests-r1 F7). `python -m
    sochron.app.envcheck` runs main under `if __name__ == "__main__":`, where main's result is the
    argument of SystemExit(...), sys.exit(...) or exit(...) (tests r2, F1), so the process exits with
    that code; a bare `main()` there would exit 0 on FAIL.
19. --sentinel-file names a JSON file with the six values make_sentinel.py prints; the end-to-end test
    writes make_sentinel.py's real output there verbatim, as Claude commits it.
"""

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

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
AC = "AC-05"
NAMES = ("Facts", "ResearchRoots", "Sentinel", "Report", "collect", "evaluate", "is_cloud_only",
         "research_host_report", "require_research_host", "ResearchHostError")
ENVCHECK = K.REPO / "src" / "sochron" / "app" / "envcheck.py"
MAKE_SENTINEL = K.REPO / "scripts" / "env" / "make_sentinel.py"


class _Host:
    """Fake collect and default_roots: fixed Facts and the fake host's roots; both record their arguments."""

    def __init__(self, ec, machine, facts_value):
        self.ec, self.machine, self.facts = ec, machine, facts_value
        self.collected, self.defaults = [], []

    def collect(self, roots):
        self.collected.append(roots)
        return self.facts

    def default_roots(self, *args, **kwargs):
        if len(args) + len(kwargs) > 1 or set(kwargs) - {"extra_data_dirs"}:
            raise TypeError(f"default_roots takes one argument, extra_data_dirs; got {args!r} {kwargs!r}")
        extra = tuple(Path(item) for item in (args[0] if args else kwargs.get("extra_data_dirs", ())))
        self.defaults.append(extra)
        self.machine.extra_data_dirs = list(extra)
        return self.machine.roots(self.ec)

    def install(self, monkeypatch, cloud=()):
        monkeypatch.setattr(self.ec, "collect", self.collect)
        # Tests that need default_roots ask for it by name first; the others pass roots themselves.
        monkeypatch.setattr(self.ec, "default_roots", self.default_roots, raising=False)
        monkeypatch.setattr(self.ec, "is_cloud_only", K.cloud_only(cloud))
        return self


def _setup(tmp_path, monkeypatch, *names, **facts):
    ec = K.envcheck(AC, *NAMES, *names)
    machine = K.Machine(tmp_path)
    host = _Host(ec, machine, K.facts(ec, **facts)).install(monkeypatch)
    return ec, machine, host


def _cli(ec, argv, capsys):
    """(exit code, standard output, standard error) of envcheck.main(argv)."""
    capsys.readouterr()
    try:
        code = ec.main(list(argv))
    except SystemExit as stop:
        code = stop.code
    captured = capsys.readouterr()
    if code is None:
        return 0, captured.out, captured.err
    return (code if isinstance(code, int) and not isinstance(code, bool) else 1), captured.out, captured.err


def _token_shown(token, out, err):
    """Which of the two streams show the token (v1.6 Q7, v1.7 tests-r1 F7); [] when neither does."""
    return [f"the token is on {name}" for name, text in (("standard output", out), ("standard error", err))
            if token in text]


def _last_line(out):
    lines = out.rstrip("\n").splitlines()
    return lines[-1] if lines else ""


def _make_not_pass(machine, item):
    """Facts changes (and a tree change) that make exactly one item non-PASS; sentinel None for 'sentinel'."""
    if item == "holdout_dir":
        (machine.repo / "holdout").mkdir()
    elif item == "excluded_period":
        machine.add_snapshot(machine.data / "transfer", "2025-06-30T00:00:00Z")
    return {"terminal_install": {"process_names": K.RUNNING + ("terminal64.exe",)},
            "terminal_data": {"metaquotes_exists": True}, "mt5_package": {"mt5_spec_found": True},
            "network_shares": {"remote_drives": ("Z:\\",)}}.get(item, {})


# ------------------------------------------------------------------------- report and require

def test_ac05_research_host_error_is_a_value_error():
    ec = K.envcheck(AC, "ResearchHostError")
    assert isinstance(ec.ResearchHostError, type) and issubclass(ec.ResearchHostError, ValueError), \
        "AC-05: ResearchHostError is not a ValueError subclass"


@pytest.mark.parametrize("label, facts", (("PASS facts", {}), ("FAIL facts", {"mt5_spec_found": True}),
                                          ("UNKNOWN facts", {"process_names": None})))
def test_ac05_research_host_report_is_evaluate_of_collect(tmp_path, monkeypatch, label, facts):
    ec, machine, host = _setup(tmp_path, monkeypatch, **facts)
    roots, sentinel = machine.roots(ec), machine.sentinel(ec)
    report = ec.research_host_report(roots=roots, sentinel=sentinel)
    wrong = []
    if host.collected != [roots]:
        wrong.append(f"collect was called with {host.collected!r}, expected once with the given roots")
    if K.summary(report) != K.summary(ec.evaluate(host.facts, roots, sentinel)):
        wrong.append(f"report {K.summary(report)} is not evaluate(collect(roots), roots, sentinel)")
    assert not wrong, f"AC-05 {label}:\n" + "\n".join(wrong)


def test_ac05_without_roots_the_default_roots_are_used(tmp_path, monkeypatch):
    ec, machine, host = _setup(tmp_path, monkeypatch, "default_roots")
    sentinel = machine.sentinel(ec)
    wrong = []
    report = ec.research_host_report(sentinel=sentinel)
    checked = ec.require_research_host(sentinel=sentinel)
    if not host.defaults or any(extra != () for extra in host.defaults):
        wrong.append(f"default_roots was called with {host.defaults!r}, expected ()")
    if len(host.collected) != 2 or any(roots != machine.roots(ec) for roots in host.collected):
        wrong.append(f"collect saw {host.collected!r}, expected the default roots once per call")
    expected = K.summary(ec.evaluate(host.facts, machine.roots(ec), sentinel))
    if K.summary(report) != expected or K.summary(checked) != expected:
        wrong.append(f"reports {K.summary(report)} / {K.summary(checked)}, expected {expected}")
    assert not wrong, "AC-05 default roots:\n" + "\n".join(wrong)


def test_ac05_require_research_host_returns_the_pass_report(tmp_path, monkeypatch):
    ec, machine, host = _setup(tmp_path, monkeypatch)
    roots, sentinel = machine.roots(ec), machine.sentinel(ec)
    with K.recording() as audit:
        report = ec.require_research_host(roots=roots, sentinel=sentinel)
    wrong = K.check_report(report) + K.side_effects(audit, machine, roots, sentinel)
    if not isinstance(report, ec.Report):
        wrong.append(f"returned {type(report).__name__}, expected Report")
    elif K.summary(report) != K.summary(ec.evaluate(host.facts, roots, sentinel)):
        wrong.append("the returned report is not the report of these inputs")
    if host.collected != [roots]:
        wrong.append(f"collect was called with {host.collected!r}")
    assert not wrong, "AC-05 PASS:\n" + "\n".join(wrong)


@pytest.mark.parametrize("item", K.ITEMS)
def test_ac05_require_research_host_raises_and_names_the_item(tmp_path, monkeypatch, item):
    ec = K.envcheck(AC, *NAMES)
    machine = K.Machine(tmp_path)
    _Host(ec, machine, K.facts(ec, **_make_not_pass(machine, item))).install(monkeypatch)
    sentinel = None if item == "sentinel" else machine.sentinel(ec)
    try:
        report = ec.require_research_host(roots=machine.roots(ec), sentinel=sentinel)
    except ec.ResearchHostError as error:
        assert isinstance(error, ValueError) and item in str(error), \
            f"AC-05: the error {str(error)!r} does not name {item}"
        assert K.TOKEN not in str(error), "AC-05: the error message holds the sentinel token (v1.7, tests-r1 F7)"
        return
    except Exception as error:  # the wrong exception type is the failure reported
        pytest.fail(f"AC-05: {item} not PASS raised {error!r}, expected ResearchHostError", pytrace=False)
    pytest.fail(f"AC-05: {item} not PASS returned {K.summary(report)} instead of raising", pytrace=False)


def test_ac05_require_research_host_names_every_item_that_is_not_pass(tmp_path, monkeypatch):
    ec, machine, _ = _setup(tmp_path, monkeypatch, remote_drives=("Z:\\",), metaquotes_exists=None)
    (machine.repo / "holdout").mkdir()
    with pytest.raises(ec.ResearchHostError) as caught:
        ec.require_research_host(roots=machine.roots(ec), sentinel=None)
    message = str(caught.value)
    missing = [item for item in ("network_shares", "terminal_data", "holdout_dir", "sentinel") if item not in message]
    assert not missing, f"AC-05: the error {message!r} does not name {missing}"
    assert K.TOKEN not in message, "AC-05: the error message holds the sentinel token (v1.7, tests-r1 F7)"


# ------------------------------------------------------------------------- the CLI

@pytest.mark.parametrize("verdict, facts", (("PASS", {}), ("FAIL", {"mt5_spec_found": True}),
                                            ("UNKNOWN", {"metaquotes_exists": None})))
def test_ac05_cli_exits_zero_only_for_pass(tmp_path, monkeypatch, capsys, verdict, facts):
    ec, machine, host = _setup(tmp_path, monkeypatch, "main", "default_roots", **facts)
    sentinel_file = machine.repo.joinpath(*K.SENTINEL_EVIDENCE)
    with K.recording() as audit:
        code, out, err = _cli(ec, ["--role", "research", "--sentinel-file", str(sentinel_file)], capsys)
    wrong = K.side_effects(audit, machine, machine.roots(ec), machine.sentinel(ec))
    if (code == 0) != (verdict == "PASS"):
        wrong.append(f"exit code {code} for {verdict}")
    if _last_line(out) != f"RESEARCH HOST: {verdict}":
        wrong.append(f"last line {_last_line(out)!r}, expected 'RESEARCH HOST: {verdict}'")
    wrong += [f"the report does not name {item}" for item in K.ITEMS if item not in out]
    wrong += _token_shown(K.TOKEN, out, err)
    if not host.defaults or any(extra != () for extra in host.defaults):
        wrong.append(f"default_roots was called with {host.defaults!r}, expected ()")
    assert not wrong, f"AC-05 CLI {verdict}:\n" + "\n".join(wrong) + f"\noutput:\n{out}"


def test_ac05_cli_passes_every_data_dir_in_order(tmp_path, monkeypatch, capsys):
    ec, machine, host = _setup(tmp_path, monkeypatch, "main", "default_roots")
    first, second = machine.base / "usb" / "a", machine.base / "usb" / "b"
    machine.add_snapshot(first, K.AT_CUTOFF)
    machine.add_snapshot(second, "2025-06-30T00:00:00Z")
    sentinel_file = machine.repo.joinpath(*K.SENTINEL_EVIDENCE)
    code, out, err = _cli(ec, ["--role", "research", "--sentinel-file", str(sentinel_file), "--data-dir", str(first),
                               "--data-dir", str(second)], capsys)
    wrong = _token_shown(K.TOKEN, out, err)
    calls = [tuple(map(K.norm, extra)) for extra in host.defaults]
    if not calls or any(call != (K.norm(first), K.norm(second)) for call in calls):
        wrong.append(f"default_roots was called with {host.defaults!r}, expected ({first}, {second})")
    if code == 0 or _last_line(out) != "RESEARCH HOST: FAIL":
        wrong.append(f"exit {code}, last line {_last_line(out)!r}: the late manifest in the second --data-dir "
                     "was not found")
    assert not wrong, "AC-05 CLI --data-dir:\n" + "\n".join(wrong)


def test_ac05_cli_with_a_data_dir_that_does_not_exist_does_not_exit_zero(tmp_path, monkeypatch, capsys):
    """v1.6 Q5: a mistyped --data-dir must not pass silently."""
    ec, machine, host = _setup(tmp_path, monkeypatch, "main", "default_roots")
    typo = machine.base / "usb" / "exprot"
    sentinel_file = machine.repo.joinpath(*K.SENTINEL_EVIDENCE)
    code, out, err = _cli(ec, ["--role", "research", "--sentinel-file", str(sentinel_file), "--data-dir", str(typo)],
                          capsys)
    wrong = _token_shown(K.TOKEN, out, err)
    if [tuple(map(K.norm, extra)) for extra in host.defaults][:1] != [(K.norm(typo),)]:
        wrong.append(f"default_roots was called with {host.defaults!r}, expected ({typo},)")
    if code == 0 or _last_line(out) != "RESEARCH HOST: UNKNOWN":
        wrong.append(f"exit {code}, last line {_last_line(out)!r}: expected a non-zero exit and UNKNOWN")
    assert not wrong, "AC-05 CLI missing --data-dir:\n" + "\n".join(wrong)


def test_ac05_cli_without_a_sentinel_file_does_not_exit_zero(tmp_path, monkeypatch, capsys):
    ec, _, _ = _setup(tmp_path, monkeypatch, "main", "default_roots")
    code, out, err = _cli(ec, ["--role", "research"], capsys)
    assert code != 0, f"AC-05: no --sentinel-file exited 0:\n{out}"
    assert not _token_shown(K.TOKEN, out, err), "AC-05: no --sentinel-file: the token was printed"


def test_ac05_python_m_runs_main():
    if not ENVCHECK.is_file():
        pytest.fail("AC-05: sochron.app.envcheck not implemented (src/sochron/app/envcheck.py is missing)",
                    pytrace=False)
    tree = ast.parse(ENVCHECK.read_text(encoding="utf-8"), filename=str(ENVCHECK))

    def is_main_guard(test):
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
            return False
        sides = (test.left, test.comparators[0])
        return (any(isinstance(side, ast.Name) and side.id == "__name__" for side in sides)
                and any(isinstance(side, ast.Constant) and side.value == "__main__" for side in sides))

    def is_exit(func):
        """SystemExit, exit or sys.exit (tests r2, F1)."""
        if isinstance(func, ast.Name):
            return func.id in ("SystemExit", "exit")
        return (isinstance(func, ast.Attribute) and func.attr == "exit" and isinstance(func.value, ast.Name)
                and func.value.id == "sys")

    def is_main_call(node):
        return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "main"

    guards = [node for node in tree.body if isinstance(node, ast.If) and is_main_guard(node.test)]
    calls = [node for guard in guards for statement in guard.body for node in ast.walk(statement)
             if is_main_call(node)]
    assert calls, "AC-05: envcheck.py has no `if __name__ == \"__main__\":` that calls main"
    exits = [node for guard in guards for statement in guard.body for node in ast.walk(statement)
             if isinstance(node, ast.Call) and is_exit(node.func) and len(node.args) == 1
             and is_main_call(node.args[0])]
    assert exits, ("AC-05: the `__main__` guard does not pass main's result to SystemExit(...), sys.exit(...) "
                   "or exit(...), so `python -m sochron.app.envcheck` would exit 0 on FAIL (tests r2, F1)")


def test_ac05_cli_end_to_end_with_make_sentinel_output(tmp_path, monkeypatch, capsys):
    ec, machine, _ = _setup(tmp_path, monkeypatch, "main", "default_roots")
    if not MAKE_SENTINEL.is_file():
        pytest.fail("AC-05: make_sentinel not implemented (scripts/env/make_sentinel.py is missing)", pytrace=False)
    vault = machine.base / "vps" / "vault"
    vault.mkdir(parents=True)
    done = subprocess.run([sys.executable, "-I", "-B", str(MAKE_SENTINEL)], cwd=vault, capture_output=True,
                          timeout=120, check=False)
    written = os.listdir(vault)
    assert done.returncode == 0 and len(written) == 1, f"AC-05: make_sentinel failed: {done.stderr!r}, {written}"
    sentinel_file = machine.repo.joinpath(*K.SENTINEL_EVIDENCE)
    sentinel_file.write_bytes(done.stdout)  # the printed values, committed as text
    values = json.loads(done.stdout.decode("utf-8"))
    sentinel = ec.Sentinel(**values)
    # The vault lives on the VPS, not here: move it out of reach of the vault_path rule.
    (machine.base / "vps").rename(machine.base / "on-the-vps")
    copy = machine.base / "on-the-vps" / "vault" / written[0]
    argv = ["--role", "research", "--sentinel-file", str(sentinel_file)]
    wrong = []

    def run(state, expected):
        with K.recording() as audit:
            code, out, err = _cli(ec, argv, capsys)
        wrong.extend(K.side_effects(audit, machine, machine.roots(ec), sentinel))
        if (code == 0) != (expected == "PASS") or _last_line(out) != f"RESEARCH HOST: {expected}":
            wrong.append(f"{state}: exit {code}, last line {_last_line(out)!r}, expected {expected}")
        wrong.extend(f"{state}: {shown}" for shown in _token_shown(values["token"], out, err))

    run("clean host", "PASS")
    shutil.copyfile(copy, machine.desktop / "vault export.json")
    run("copy on Desktop", "FAIL")
    K.put(machine.data / "transfer" / "pasted.txt", f"pasted from the VPS: {values['token']}\n")
    run("copy on Desktop and the token in data/transfer", "FAIL")
    try:
        ec.require_research_host(roots=machine.roots(ec), sentinel=sentinel)
        wrong.append("copy on Desktop: require_research_host did not raise")
    except ec.ResearchHostError as error:
        if "sentinel" not in str(error):
            wrong.append(f"copy on Desktop: the error {str(error)!r} does not name sentinel")
        if values["token"] in str(error):
            wrong.append("copy on Desktop: the error message holds the token (v1.7, tests-r1 F7)")
    assert not wrong, "AC-05 end to end:\n" + "\n".join(wrong)
