"""Shared helpers of the ENV-002 v2.x macOS acceptance tests (test author; locked with them).

Contract: docs/contracts/ENV-002-research-host-separation.md v2.6 (approved 2026-11-18). tests/ has no
conftest.py, so the test modules load this file by path under the module name "darwinkit_env002", with
the recipe the contract gives for synthetic.py. This file loads envkit.py the same way ("envkit_env002")
and reuses its fake values, audit hook, read-rule checks and report checks unchanged.

Conventions the contract leaves to these tests (also in docs/handoff/ENV-002-v2-tests.md); D1-D8 add
to conventions 1-19 of the v1.x tests, which still hold:
D1. Nothing here calls the real libproc, getfsstat, /Applications or the real home folder. A macOS case
    sets envcheck.sys.platform and a fake envcheck.os.uname (machine "arm64" unless the case says
    otherwise), removes every DYLD_* variable from os.environ, and replaces the raw readers
    (_darwin_list_pids, _darwin_pid_path, _darwin_mounts), _darwin_home, _darwin_application_dirs and
    is_cloud_only (all looked up at call time; FakeOS.install). The same cases run on Linux CI and on
    the Mac with the same result.
D2. The fake Mac (class Mac) lives under tmp_path: <base>/Applications stands for /Applications,
    <base>/Users/x is the home folder. _darwin_home() returns the home as str (the real one returns
    os.path.expanduser("~")); _darwin_application_dirs(home) returns (<base>/Applications,
    <home>/Applications), as Path, and is how collect finds the two application folders.
    <home>/Applications does not exist unless a case makes it. The repo is <base>/work/Sochron1k,
    outside the home folder, with the committed sentinel values as its only file that holds the token;
    search_dirs are <home>/Downloads, Desktop, Documents and the iCloud Drive folder
    <home>/Library/Mobile Documents/com~apple~CloudDocs; appdata is <home>/Library/Application Support.
    On this host collect and evaluate give PASS for every item.
D3. The fake process table holds pid 0 (proc_pidpath fails with ESRCH), this process (os.getpid(), whose
    path is os.path.realpath(sys.executable)) and pid 333 (/usr/libexec/logd). _darwin_list_pids(c)
    returns (c, the first c pids) when the table holds c pids or more, else (len, all pids):
    proc_listallpids fills at most the buffer it gets. _darwin_mounts(c) does the same with the mount
    table.
D4. The base mount table (contract r3 F45): "/" apfs with MNT_LOCAL (and MNT_RDONLY), "/dev" devfs with
    MNT_LOCAL, "/System/Volumes/Data/home" autofs from "map auto_home" without MNT_LOCAL (other flag bits
    set). A mount entry is (type, source, mount point, flags) and the tests build MNT_LOCAL from
    envcheck.MNT_LOCAL, whose value has its own test. A case that names no mount point and must test a
    rule other than the allow list puts its mount at /System/Volumes/Update/mnt1, an allowed point.
D5. collect is judged by evaluate: the tests call envcheck.collect(roots) for real, then
    envcheck.evaluate(facts, roots, sentinel) on the same fake Mac (outside the recording), and compare
    every item. While collect runs, the audit hook also checks that nothing of the real machine's own
    folders (/Applications, the real home and its Library, Applications, .wine, Desktop, Downloads,
    .Trash, Pictures, .ssh, .colima) is listed or opened.
D6. "Not listed" means no os.scandir or os.listdir audit event for the folder or any path under it
    (os.walk, Path.iterdir and Path.rglob raise these). "Unlistable" and "exists but cannot be listed"
    are made with envkit's deny_list (PermissionError, errno EACCES) on any OS and for any user.
D7. A dataless folder or file is one the fake envcheck.is_cloud_only calls cloud-only (v2.1 F6: tests
    replace is_cloud_only). For the "never stat" rule of a root below a dataless folder, os.stat and
    os.lstat are wrapped while evaluate runs (StatRecorder); pathlib and os.path reach them too.
D8. Paths compare as envkit.norm gives them (absolute, case as on disk).
"""

import errno
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace


def _load(name, filename):
    path = Path(__file__).resolve().parent / filename
    module = sys.modules.get(name)
    if module is None or getattr(module, "__file__", None) != str(path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


K = _load("envkit_env002", "envkit.py")

TOKEN = K.TOKEN
# The contract names the tests rely on. A name the module lacks fails the test as "not implemented".
BASE_NAMES = ("Facts", "ResearchRoots", "Sentinel", "Report", "collect", "evaluate", "is_cloud_only",
              "research_host_report", "default_roots", "sys", "os")
READER_NAMES = ("reader_name", "host_lines", "_HOST_SUMMARY", "_darwin_home", "_darwin_application_dirs",
                "_darwin_list_pids", "_darwin_pid_path", "_darwin_mounts", "read_process_paths", "read_mounts",
                "classify_processes", "classify_mounts", "wine_prefixes", "find_wine_program_files",
                "find_terminal_paths_darwin", "MNT_LOCAL")
MNT_RDONLY = 0x00000001
OTHER_FLAGS = 0x00100000 | 0x00400000  # flag bits other than MNT_LOCAL, as a real autofs mount has
ALLOWED_POINT = "/System/Volumes/Update/mnt1"  # D4: an allowed mount point for cases about other rules
LOGD = "/usr/libexec/logd"
# Wine sources of the contract, in its order, relative to the home folder.
WINE_SOURCES = {
    "PlayOnMac": ("Library", "PlayOnMac", "wineprefix"),
    "CrossOver": ("Library", "Application Support", "CrossOver", "Bottles"),
    "wine": (".wine",),
}
WINE_LOOKED_AT = {"PlayOnMac": "~/Library/PlayOnMac/wineprefix",
                  "CrossOver": "~/Library/Application Support/CrossOver/Bottles", "wine": "~/.wine"}


def reader(ac, *names):
    """envcheck with every name the darwin cases need; a missing one fails as not implemented."""
    return K.envcheck(ac, *BASE_NAMES, *READER_NAMES, *names)


def own():
    """(pid, path) of this process as the darwin reader must find it."""
    return os.getpid(), os.path.realpath(sys.executable)


def uname_result(machine):
    values = ("Darwin", "synthetic-mac", "25.6.0", "Darwin Kernel Version 25.6.0 (synthetic)", machine)
    maker = getattr(os, "uname_result", None)
    if maker is not None:
        return maker(values)
    return SimpleNamespace(sysname=values[0], nodename=values[1], release=values[2], version=values[3],
                           machine=values[4])


def base_mounts(local, *extra):
    """The base mount table of D4 with MNT_LOCAL = local, then the extra entries."""
    return [("apfs", "/dev/disk3s1s1", "/", local | MNT_RDONLY), ("devfs", "devfs", "/dev", local),
            ("autofs", "map auto_home", "/System/Volumes/Data/home", OTHER_FLAGS), *extra]


# ------------------------------------------------------------------------- the fake Mac

class Mac:
    """A fake macOS research host under base (convention D2)."""

    def __init__(self, base):
        self.base = Path(base)
        self.home = self.base / "Users" / "x"
        self.library = self.home / "Library"
        self.appsupport = self.library / "Application Support"
        self.applications = self.base / "Applications"
        self.user_applications = self.home / "Applications"
        self.downloads = self.home / "Downloads"
        self.desktop = self.home / "Desktop"
        self.documents = self.home / "Documents"
        self.icloud = self.library / "Mobile Documents" / "com~apple~CloudDocs"
        self.repo = self.base / "work" / "Sochron1k"
        self.data = self.repo / "data"
        self.vault = self.base / "vps" / "vault"
        self.extra_data_dirs = []
        self.search_dirs = [self.downloads, self.desktop, self.documents, self.icloud]
        for folder in (self.applications / "Safari.app" / "Contents",
                       self.applications / "Visual Studio Code.app" / "Contents", self.downloads, self.desktop,
                       self.documents, self.icloud, self.home / "Music"):
            folder.mkdir(parents=True, exist_ok=True)
        K.put(self.appsupport / "Code" / "User" / "settings.json", '{"editor.tabSize": 4}\n')
        K.put(self.appsupport / "com.apple.TextEdit" / "state.plist", b"bplist00 synthetic")
        K.put(self.library / "Preferences" / "com.apple.finder.plist", b"bplist00 synthetic")
        K.put(self.home / ".ssh" / "known_hosts", "github.com ssh-ed25519 AAAA synthetic\n")
        K.put(self.home / ".zshrc", "export EDITOR=vi\n")
        K.put(self.home / "Pictures" / "Photos Library.photoslibrary" / "database" / "Photos.sqlite", b"synthetic")
        # The repository: the committed sentinel values are its only file that holds the token.
        K.put(self.repo.joinpath(*K.SENTINEL_EVIDENCE), K.committed_values(str(self.vault)))
        K.put(self.repo / "docs" / "evidence" / "ENV-002.md",
              f"# ENV-002\n\nSentinel {K.SENTINEL_NAME}, {K.SENTINEL_SIZE} bytes, SHA-256 {K.SENTINEL_SHA256}.\n")
        K.put(self.repo / "README.md", "# Sochron1k\n")
        K.put(self.repo / ".env.example", "MT5_LOGIN=\nMT5_SERVER=\n")
        K.put(self.repo / "src" / "sochron" / "__init__.py", '"""Synthetic package."""\n')
        K.put(self.repo / ".git" / "HEAD", "ref: refs/heads/chore/ENV-002-macos-research-host\n")
        K.put(self.repo / ".venv" / "pyvenv.cfg", "home = synthetic\n")
        (self.data / "transfer").mkdir(parents=True, exist_ok=True)
        self.add_snapshot(self.data / "m1-2018-2024", K.BEFORE_CUTOFF)
        # The owner's ordinary files.
        K.put(self.desktop / "notes.txt", "call the broker\n")
        K.put(self.documents / "budget.json", '{"vps_usd": 40}\n')
        K.put(self.downloads / "photo.png", b"\x89PNG synthetic")

    def add_snapshot(self, folder, period_end_utc, *, name="bars.parquet"):
        folder = Path(folder)
        data = K.put(folder / name, K.PARQUET)
        K.put(folder / "manifest.json", K.manifest_text([(name, K.PARQUET)], period_end_utc))
        return data

    def roots(self, ec, *, program_files=(), appdata=None, data_dirs=None):
        dirs = tuple(data_dirs) if data_dirs is not None else (self.data, *self.extra_data_dirs)
        return ec.ResearchRoots(repo=self.repo, data_dirs=dirs, program_files=tuple(program_files),
                                appdata=appdata if appdata is not None else self.appsupport,
                                user_profile=self.home, search_dirs=tuple(self.search_dirs))

    def sentinel(self, ec, **changes):
        values = {"name": K.SENTINEL_NAME, "size": K.SENTINEL_SIZE, "sha256": K.SENTINEL_SHA256, "token": TOKEN,
                  "vault_path": str(self.vault), "created_utc": K.CREATED_UTC, **changes}
        return ec.Sentinel(**values)

    def wine_source(self, source):
        return self.home.joinpath(*WINE_SOURCES[source])

    def prefix(self, source, name="p1"):
        """The prefix folder: <source>/<name>, or ~/.wine itself."""
        return self.home / ".wine" if source == "wine" else self.wine_source(source) / name

    def program_files_root(self, source, name="p1", folder="Program Files"):
        root = self.prefix(source, name) / "drive_c" / folder
        root.mkdir(parents=True, exist_ok=True)
        return root


# ------------------------------------------------------------------------- the fake OS (D1, D3)

class FakeOS:
    """The raw readers, _darwin_home, _darwin_application_dirs and os.uname of a fake Mac."""

    def __init__(self, ec, mac):
        pid, path = own()
        self.mac = mac
        self.table = {0: (None, errno.ESRCH), pid: (path, 0), 333: (LOGD, 0)}
        self.local = ec.MNT_LOCAL
        self.mounts = base_mounts(self.local)
        self.list_error = None
        self.mount_error = None
        self.machine = "arm64"
        self.calls = []

    def list_pids(self, capacity):
        self.calls.append(("_darwin_list_pids", capacity))
        if self.list_error is not None:
            raise self.list_error
        pids = tuple(self.table)
        if len(pids) >= capacity:
            return capacity, pids[:capacity]
        return len(pids), pids

    def pid_path(self, pid):
        self.calls.append(("_darwin_pid_path", pid))
        return self.table.get(pid, (None, errno.ESRCH))

    def darwin_mounts(self, capacity):
        self.calls.append(("_darwin_mounts", capacity))
        if self.mount_error is not None:
            raise self.mount_error
        entries = tuple(self.mounts)
        if len(entries) >= capacity:
            return capacity, entries[:capacity]
        return len(entries), entries

    def application_dirs(self, *args, **kwargs):
        return self.mac.applications, self.mac.user_applications

    def install(self, monkeypatch, ec, *, platform="darwin", cloud=()):
        result = uname_result(self.machine)
        monkeypatch.setattr(ec.sys, "platform", platform)
        monkeypatch.setattr(ec.os, "uname", lambda: result, raising=False)
        for key in [key for key in os.environ if key.startswith("DYLD_")]:
            monkeypatch.delenv(key)
        monkeypatch.setattr(ec, "_darwin_list_pids", self.list_pids)
        monkeypatch.setattr(ec, "_darwin_pid_path", self.pid_path)
        monkeypatch.setattr(ec, "_darwin_mounts", self.darwin_mounts)
        monkeypatch.setattr(ec, "_darwin_home", lambda: str(self.mac.home))
        monkeypatch.setattr(ec, "_darwin_application_dirs", self.application_dirs)
        monkeypatch.setattr(ec, "is_cloud_only", K.cloud_only(cloud))
        return self

    def raw_calls(self):
        return [name for name, _ in self.calls]


def spy(monkeypatch, ec, name, calls):
    """Replace envcheck.<name> by a wrapper that records its calls in calls and then runs it."""
    real = getattr(ec, name)

    def wrapper(*args, **kwargs):
        calls.append(name)
        return real(*args, **kwargs)

    monkeypatch.setattr(ec, name, wrapper)


def collect(ec, mac, *, program_files=(), appdata=None, data_dirs=None, deny=(), deny_list=()):
    """envcheck.collect on the fake Mac under the audit hook (D5); returns (roots, facts, audit)."""
    roots = mac.roots(ec, program_files=program_files, appdata=appdata, data_dirs=data_dirs)
    with K.recording(deny, deny_list) as audit:
        facts = ec.collect(roots)
    return roots, facts, audit


def judge_collect(ec, mac, *, fail=(), unknown=(), ignore=(), **options):
    """collect, then evaluate on the same roots (D5); returns (facts, every difference, audit)."""
    roots, facts, audit = collect(ec, mac, **options)
    report = ec.evaluate(facts, roots, mac.sentinel(ec))
    wrong = K.check_report(report, fail=fail, unknown=unknown, ignore=ignore) + outside_reads(audit, mac.base)
    return facts, wrong, audit


def report_with_lines(ec, mac, *, program_files=(), deny=(), deny_list=(), roots=None):
    """research_host_report on the fake Mac under the audit hook, then host_lines(); (report, lines, audit)."""
    roots = roots if roots is not None else mac.roots(ec, program_files=program_files)
    with K.recording(deny, deny_list) as audit:
        report = ec.research_host_report(roots=roots, sentinel=mac.sentinel(ec))
    return report, ec.host_lines(), audit


def line(lines, prefix):
    """The first line that starts with prefix, or None."""
    return next((text for text in lines if isinstance(text, str) and text.startswith(prefix)), None)


# ------------------------------------------------------------------------- what a recording saw

def _real_places():
    home = Path(os.path.expanduser("~"))
    exact = {K.norm(home), K.norm(home / "Documents")}
    under = [K.norm(path) for path in (Path("/Applications"), home / "Applications", home / "Library", home / ".wine",
                                        home / "Desktop", home / "Downloads", home / ".Trash", home / "Pictures",
                                        home / ".ssh", home / ".colima")]
    return exact, under


def outside_reads(audit, base):
    """Listings and opens of the real machine's own folders (D5); [] when there is none."""
    exact, under = _real_places()
    base = K.norm(base)
    wrong = []
    for path in sorted(set(audit.listings) | audit.opened()):
        if K._under(path, base):
            continue
        if path in exact or any(K._under(path, root) for root in under):
            wrong.append(f"reached the real machine: {path}")
    return wrong


def listed_under(audit, folder):
    folder = K.norm(folder)
    return sorted({path for path in audit.listings if K._under(path, folder)})


def opened_under(audit, folder):
    folder = K.norm(folder)
    return sorted({path for path in audit.opened() if K._under(path, folder)})


def touched_under(audit, folder):
    """Every listing or open at or under folder, as text; [] when there is none (D6)."""
    return [f"listed {path}" for path in listed_under(audit, folder)] + [
        f"opened {path}" for path in opened_under(audit, folder)]


class StatRecorder:
    """os.stat and os.lstat wrapped for the test (D7): records paths while active is True."""

    def __init__(self, monkeypatch):
        self.active = False
        self.paths = []
        for name in ("stat", "lstat"):
            monkeypatch.setattr(os, name, self._wrap(getattr(os, name)))

    def _wrap(self, real):
        def wrapper(path, *args, **kwargs):
            if self.active and not isinstance(path, int):
                try:
                    self.paths.append(K.norm(path))
                except (TypeError, ValueError):
                    pass
            return real(path, *args, **kwargs)

        return wrapper

    def strictly_under(self, folder):
        folder = K.norm(folder)
        return sorted({path for path in self.paths if path != folder and K._under(path, folder)})


def judge_evaluate(ec, monkeypatch, host, facts_value, sentinel, *, cloud=(), deny=(), deny_list=(), stats=None):
    """evaluate on a fake host with the fake is_cloud_only; returns (report, read-rule breaks, audit)."""
    roots = host.roots(ec)
    monkeypatch.setattr(ec, "is_cloud_only", K.cloud_only(cloud))
    with K.recording(deny, deny_list) as audit:
        if stats is not None:
            stats.active = True
        try:
            report = ec.evaluate(facts_value, roots, sentinel)
        finally:
            if stats is not None:
                stats.active = False
    return report, K.side_effects(audit, host, roots, sentinel, cloud), audit
