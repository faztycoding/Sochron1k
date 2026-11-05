"""Shared helpers of the ENV-002 acceptance tests (test author; locked with them).

tests/ has no conftest.py and is no package, so the test modules load this file by path with the
recipe the contract gives for synthetic.py, under the module name "envkit_env002", and reuse the
loaded module. The conventions these helpers carry are numbered in the docstring of
test_ac02_research_host_evaluate.py. Every fake value lives here or in the test modules.
"""

import errno
import hashlib
import importlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ITEMS = ("terminal_install", "terminal_data", "mt5_package", "holdout_dir", "excluded_period",
         "network_shares", "sentinel")
STATUSES = ("PASS", "FAIL", "UNKNOWN")
# Facts fields (convention 2) and the item each one feeds.
FACT_ITEM = {
    "terminal_paths": "terminal_install",
    "uninstall_display_names": "terminal_install",
    "process_names": "terminal_install",
    "metaquotes_exists": "terminal_data",
    "mt5_spec_found": "mt5_package",
    "remote_drives": "network_shares",
    "connected_resources": "network_shares",
}
ROOT_FIELDS = ("repo", "data_dirs", "program_files", "appdata", "user_profile", "search_dirs")
SENTINEL_FIELDS = ("name", "size", "sha256", "token", "vault_path", "created_utc")
UNINSTALLED = ("Git", "Python 3.12.15 (64-bit)", "Microsoft Visual Studio Code (User)", "uv")
RUNNING = ("System", "explorer.exe", "Code.exe", "python.exe", "OneDrive.exe")
VALID_FACTS = {
    "terminal_paths": (),
    "uninstall_display_names": UNINSTALLED,
    "process_names": RUNNING,
    "metaquotes_exists": False,
    "mt5_spec_found": False,
    "remote_drives": (),
    "connected_resources": (),
}
TEXT_SUFFIXES = (".json", ".csv", ".txt", ".md")
CLOSED_SUFFIXES = (".key", ".pem", ".pfx", ".rdp")
SENTINEL_EVIDENCE = ("docs", "evidence", "ENV-002-sentinel.json")
CREATED_UTC = "2026-11-05T09:30:00Z"
BEFORE_CUTOFF = "2024-07-01T00:00:00Z"
AT_CUTOFF = "2025-01-01T00:00:00Z"
AFTER_CUTOFF = "2025-01-01T00:00:01Z"
PARQUET = b"PAR1 synthetic ENV-002 bars PAR1"
# A token of the shape secrets.token_hex(16) gives: 32 lower-case hex characters.
TOKEN = "5e1f0c2a9b7d4e6f8a3c1b0d2e4f6a8c"


def sentinel_document(token):
    """The sentinel file in the contract's shape: 60 synthetic M1 bars from 2025-01-02T00:00:00Z."""
    bars = [{"time_utc": f"2025-01-02T00:{minute:02d}:00Z", "open": "2000.00", "high": "2000.50",
             "low": "1999.50", "close": "2000.25", "spread": 200} for minute in range(60)]
    return {"synthetic": True, "purpose": "ENV-002 sentinel", "token": token, "bars": bars}


SENTINEL_BYTES = (json.dumps(sentinel_document(TOKEN), indent=2) + "\n").encode("ascii")
SENTINEL_NAME = f"SENTINEL-ENV002-{TOKEN[:8]}.json"
SENTINEL_SIZE = len(SENTINEL_BYTES)
SENTINEL_SHA256 = hashlib.sha256(SENTINEL_BYTES).hexdigest()


def same_size_other_bytes():
    """SENTINEL_BYTES with one digit changed: the sentinel's size, another SHA-256, no token."""
    changed = SENTINEL_BYTES.replace(TOKEN.encode("ascii"), ("0" * 32).encode("ascii"))
    return changed.replace(b'"spread": 200', b'"spread": 201', 1)


def committed_values(vault_path):
    """docs/evidence/ENV-002-sentinel.json as Claude commits it: the values make_sentinel printed."""
    return json.dumps({"name": SENTINEL_NAME, "size": SENTINEL_SIZE, "sha256": SENTINEL_SHA256, "token": TOKEN,
                       "vault_path": vault_path, "created_utc": CREATED_UTC}, indent=2) + "\n"


def envcheck(ac, *names):
    """sochron.app.envcheck with the named contract symbols; a missing one fails as not implemented."""
    try:
        module = importlib.import_module("sochron.app.envcheck")
    except ModuleNotFoundError as error:
        if error.name not in ("sochron.app", "sochron.app.envcheck"):
            raise
        pytest.fail(f"{ac}: sochron.app.envcheck not implemented ({error})", pytrace=False)
    missing = [name for name in names if not hasattr(module, name)]
    if missing:
        pytest.fail(f"{ac}: sochron.app.envcheck.{', '.join(missing)} not implemented", pytrace=False)
    return module


def facts(ec, **changes):
    return ec.Facts(**{**VALID_FACTS, **changes})


def put(path, content=b""):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def manifest_text(entries, period_end_utc):
    """A manifest in the contract's shape for (name, bytes) entries."""
    files = [{"name": name, "sha256": hashlib.sha256(data).hexdigest()} for name, data in entries]
    return json.dumps({"files": files, "period_end_utc": period_end_utc}, indent=2) + "\n"


class Machine:
    """A fake research host under base: a profile with shell folders, Program Files, a repo and its data.

    By default the repo sits outside every search dir; repo_in_desktop puts it under Desktop, as on the
    owner's PC. with_data=False leaves out <repo>/data (a fresh clone, v1.6 Q5). The repo has a .git and a
    .venv, as the real one does (v1.6 Q11). The VPS vault path (self.vault) does not exist unless a test
    creates it.
    """

    def __init__(self, base, *, repo_in_desktop=False, with_data=True):
        self.base = Path(base)
        self.profile = self.base / "Users" / "owner"
        self.appdata = self.profile / "AppData" / "Roaming"
        self.desktop = self.profile / "Desktop"
        self.documents = self.profile / "Documents"
        self.downloads = self.profile / "Downloads"
        self.onedrive = self.profile / "OneDrive"
        self.program_files = (self.base / "Program Files", self.base / "Program Files (x86)")
        self.repo = (self.desktop if repo_in_desktop else self.base / "work") / "Sochron1k"
        self.data = self.repo / "data"
        self.extra_data_dirs = []
        self.search_dirs = [self.downloads, self.desktop, self.documents, self.onedrive]
        self.vault = self.base / "vps" / "vault"
        for folder in (*self.program_files, self.desktop, self.documents, self.downloads, self.onedrive):
            folder.mkdir(parents=True, exist_ok=True)
        put(self.appdata / "Code" / "User" / "settings.json", '{"editor.tabSize": 4}\n')
        put(self.program_files[0] / "Git" / "git-bash.exe", b"MZ synthetic")
        # The repository: the committed sentinel values are its only file that holds the token.
        put(self.repo.joinpath(*SENTINEL_EVIDENCE), committed_values(str(self.vault)))
        put(self.repo / "docs" / "evidence" / "ENV-002.md",
            f"# ENV-002\n\nSentinel {SENTINEL_NAME}, {SENTINEL_SIZE} bytes, SHA-256 {SENTINEL_SHA256}.\n")
        put(self.repo / "README.md", "# Sochron1k\n")
        put(self.repo / ".env.example", "MT5_LOGIN=\nMT5_SERVER=\n")
        put(self.repo / "pyproject.toml", '[project]\nname = "sochron"\n')
        put(self.repo / "src" / "sochron" / "__init__.py", '"""Synthetic package."""\n')
        put(self.repo / "reports" / "trades.csv", "time_utc,r\n2024-03-01T14:00:00Z,1.2\n")
        put(self.repo / ".git" / "HEAD", "ref: refs/heads/feat/ENV-002-research-host-separation\n")
        put(self.repo / ".git" / "info" / "exclude", "# synthetic\n")
        put(self.repo / ".venv" / "pyvenv.cfg", "home = synthetic\n")
        put(self.repo / ".venv" / "Lib" / "site-packages" / "pytest-9.1.1.dist-info" / "entry_points.txt",
            "[console_scripts]\npytest = pytest:console_main\n")
        if with_data:
            (self.data / "transfer").mkdir(parents=True, exist_ok=True)
            self.add_snapshot(self.data / "m1-2018-2024", BEFORE_CUTOFF)
        # The owner's ordinary files in the shell folders.
        put(self.desktop / "notes.txt", "call the broker\n")
        put(self.documents / "budget.json", '{"vps_usd": 40}\n')
        put(self.downloads / "photo.png", b"\x89PNG synthetic")
        put(self.onedrive / "Documents" / "plan.md", "# plan\n")

    def add_snapshot(self, folder, period_end_utc, *, name="bars.parquet", per_file=False, listed=None):
        """A data file and its manifest (per folder, or <name>.manifest.json); returns the data file."""
        folder = Path(folder)
        data = put(folder / name, PARQUET)
        target = folder / (f"{name}.manifest.json" if per_file else "manifest.json")
        put(target, manifest_text([(listed or name, PARQUET)], period_end_utc))
        return data

    def add_data_dir(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.extra_data_dirs.append(folder)
        return folder

    def roots(self, ec):
        return ec.ResearchRoots(repo=self.repo, data_dirs=(self.data, *self.extra_data_dirs),
                                program_files=self.program_files, appdata=self.appdata,
                                user_profile=self.profile, search_dirs=tuple(self.search_dirs))

    def sentinel(self, ec, **changes):
        values = {"name": SENTINEL_NAME, "size": SENTINEL_SIZE, "sha256": SENTINEL_SHA256, "token": TOKEN,
                  "vault_path": str(self.vault), "created_utc": CREATED_UTC, **changes}
        return ec.Sentinel(**values)


# ------------------------------------------------------------------------- the audit hook

WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC | os.O_EXCL
FORBIDDEN_EVENTS = (
    "subprocess.", "socket.", "http.client.", "urllib.", "ftplib.", "smtplib.", "poplib.", "imaplib.",
    "nntplib.", "telnetlib.", "webbrowser.", "shutil.", "tempfile.", "os.system", "os.exec", "os.spawn",
    "os.posix_spawn", "os.startfile", "os.fork", "os.kill", "os.remove", "os.rename", "os.rmdir", "os.mkdir",
    "os.truncate", "os.chmod", "os.chown", "os.utime", "os.link", "os.symlink", "winreg.SetValue",
    "winreg.CreateKey", "winreg.DeleteKey", "winreg.DeleteValue", "winreg.ConnectRegistry", "winreg.LoadKey",
    "winreg.SaveKey",
)
_STATE = {"audit": None, "hooked": False}


def norm(path):
    """An absolute, case-normalised path text (str, bytes, Path or os.DirEntry)."""
    return os.path.normcase(os.path.abspath(os.fsdecode(os.fspath(path))))


def _event_path(value):
    if value is None or isinstance(value, int):
        return None
    try:
        return norm(value)
    except (TypeError, ValueError):
        return None


class Audit:
    """What one recording saw: opens (path, mode, flags), listings and forbidden events."""

    def __init__(self, deny=()):
        self.deny = {norm(path) for path in deny}
        self.opens = []
        self.listings = []
        self.forbidden = []

    def event(self, event, args):
        if event == "open":
            path = _event_path(args[0] if args else None)
            if path is None:
                return
            self.opens.append((path, args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else 0))
            if path in self.deny:
                raise PermissionError(errno.EACCES, "Permission denied (ENV-002 test)", path)
        elif event in ("os.listdir", "os.scandir"):
            path = _event_path(args[0] if args else None)
            if path is not None:
                self.listings.append(path)
        elif event.startswith(FORBIDDEN_EVENTS):
            text = repr(args)
            if "__pycache__" not in text:
                self.forbidden.append(f"{event} {text[:240]}")

    def opened(self):
        return {path for path, _, _ in self.opens}

    def writes(self):
        found = []
        for path, mode, flags in self.opens:
            if "__pycache__" in path:
                continue
            by_mode = isinstance(mode, str) and any(letter in mode for letter in "wax+")
            by_flags = isinstance(flags, int) and bool(flags & WRITE_FLAGS)
            if by_mode or by_flags:
                found.append(f"open {path} mode={mode!r} flags={flags}")
        return found


def _hook(event, args):
    audit = _STATE["audit"]
    if audit is not None:
        audit.event(event, args)


@contextmanager
def recording(deny=()):
    """Record audit events while the block runs; outside it the process-wide hook does nothing."""
    if not _STATE["hooked"]:
        sys.addaudithook(_hook)
        _STATE["hooked"] = True
    audit = Audit(deny)
    _STATE["audit"] = audit
    try:
        yield audit
    finally:
        _STATE["audit"] = None


def cloud_only(paths):
    """A fake envcheck.is_cloud_only: True exactly for the given paths."""
    wanted = {norm(path) for path in paths}

    def is_cloud_only(path):
        return norm(path) in wanted

    return is_cloud_only


# ------------------------------------------------------------------------- the read rules

def _under(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _beside_terminal(folder, base):
    """Whether folder or one of its parents up to base holds terminal64.exe, in any case (v1.6 Q4)."""
    folder, base = Path(folder), Path(base)
    for candidate in (folder, *folder.parents):
        if candidate.is_dir() and any(name.lower() == "terminal64.exe" and (candidate / name).is_file()
                                      for name in os.listdir(candidate)):
            return True
        if candidate == base:
            return False
    return False


def must_not_open(machine, roots, sentinel, cloud=()):
    """Every file of the fake host that no rule of the contract lets evaluate open (convention 9)."""
    cloud = {norm(path) for path in cloud}
    repo_data = [norm(roots.repo), *(norm(folder) for folder in roots.data_dirs)]
    searched = [norm(folder) for folder in roots.search_dirs]
    metaquotes = norm(Path(roots.appdata) / "MetaQuotes")
    banned = set()
    for folder, _, names in os.walk(machine.base):
        for name in names:
            path = norm(Path(folder) / name)
            lower = name.lower()
            suffix = os.path.splitext(lower)[1]
            closed = (lower == ".env" or lower.startswith(".env.") or suffix in CLOSED_SUFFIXES or path in cloud
                      or _under(path, metaquotes) or _beside_terminal(folder, machine.base))
            if closed:
                banned.add(path)
            elif any(_under(path, root) for root in repo_data):
                if suffix not in TEXT_SUFFIXES:
                    banned.add(path)
            elif any(_under(path, root) for root in searched):
                if sentinel is None or suffix != ".json" or os.path.getsize(path) != sentinel.size:
                    banned.add(path)
            else:
                banned.add(path)
    return banned


def side_effects(audit, machine, roots, sentinel, cloud=()):
    """Every break of convention 9 that a recording shows; [] when there is none."""
    wrong = [f"wrote: {item}" for item in audit.writes()]
    wrong += [f"forbidden event: {item}" for item in audit.forbidden]
    banned = must_not_open(machine, roots, sentinel, cloud)
    wrong += [f"opened {path}" for path in sorted(audit.opened() & banned)]
    metaquotes = norm(Path(roots.appdata) / "MetaQuotes")
    wrong += [f"listed {path}" for path in sorted(set(audit.listings)) if _under(path, metaquotes)]
    return wrong


def judge(ec, monkeypatch, machine, facts_value, sentinel, *, cloud=(), deny=()):
    """evaluate on the fake host with the fake is_cloud_only; returns (report, side-effect breaks)."""
    roots = machine.roots(ec)
    monkeypatch.setattr(ec, "is_cloud_only", cloud_only(cloud))
    with recording(deny) as audit:
        report = ec.evaluate(facts_value, roots, sentinel)
    return report, side_effects(audit, machine, roots, sentinel, cloud)


# ------------------------------------------------------------------------- reading a report

def item_map(report):
    return {getattr(item, "name", None): item for item in getattr(report, "items", ()) or ()}


def check_report(report, *, fail=(), unknown=(), ignore=(), token=TOKEN):
    """Differences from the expected statuses (PASS unless named FAIL or UNKNOWN); [] when it matches.

    Items named in ignore are not compared; the verdict must still follow the statuses the report has.
    No detail may hold the token (v1.6 Q7), whatever the item.
    """
    wrong = []
    if getattr(report, "role", None) != "research":
        wrong.append(f"role {getattr(report, 'role', None)!r}, expected 'research'")
    items = getattr(report, "items", None)
    if not isinstance(items, tuple):
        return wrong + [f"items is {type(items).__name__}, expected a tuple"]
    names = [getattr(item, "name", None) for item in items]
    if sorted(map(str, names)) != sorted(ITEMS):
        wrong.append(f"items {names}, expected one each of {list(ITEMS)}")
    got = {}
    for item in items:
        status, detail = getattr(item, "status", None), getattr(item, "detail", None)
        if status not in STATUSES:
            wrong.append(f"{item.name}: status {status!r} is not PASS, FAIL or UNKNOWN")
        if not isinstance(detail, str):
            wrong.append(f"{item.name}: detail is {type(detail).__name__}, expected str")
        elif token and token in detail:
            wrong.append(f"{item.name}: the detail shows the sentinel token")
        got[item.name] = (status, detail)
    for name in ITEMS:
        if name in ignore or name not in got:
            continue
        expected = "FAIL" if name in fail else "UNKNOWN" if name in unknown else "PASS"
        status, detail = got[name]
        if status != expected:
            wrong.append(f"{name}: {status}, expected {expected} (detail: {detail!r})")
    statuses = [status for status, _ in got.values()]
    rule = "FAIL" if "FAIL" in statuses else "UNKNOWN" if "UNKNOWN" in statuses else "PASS"
    if getattr(report, "verdict", None) != rule:
        wrong.append(f"verdict {getattr(report, 'verdict', None)!r}, expected {rule} from {statuses}")
    return wrong


def summary(report):
    """(role, verdict, sorted (name, status)) of a report: what two reports of one state share."""
    return (report.role, report.verdict, tuple(sorted((item.name, item.status) for item in report.items)))
