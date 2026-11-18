"""ENV-002 research-host check (docs/contracts/ENV-002-research-host-separation.md, v2.6).

The research host (the owner's Mac since D-023) must hold no MT5 terminal, no MetaTrader5 package, no data
of the excluded period, no share to the VPS and no copy of the synthetic sentinel made on the VPS.
collect(roots) reads the OS with the reader of sys.platform: win32 (the v1.9 reader) or darwin; any other
platform reads nothing and is never PASS. OS calls stay inside functions, so the module imports anywhere.
evaluate(facts, roots, sentinel) judges the facts and searches the repository, the data dirs and the
search dirs by the contract's read rules. Nothing is written, deleted, run or sent over a network.

Run from the repository root:
  PYTHONPATH=src uv run --offline python -m sochron.app.envcheck --role research \\
      --sentinel-file docs/evidence/ENV-002-sentinel.json [--data-dir <path> ...]
Exit 0 only when the verdict is PASS. The report never prints the sentinel token.
"""

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sochron.research import HOLDOUT_CUTOFF_UTC

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
ROLE = "research"
ITEM_NAMES = ("terminal_install", "terminal_data", "mt5_package", "holdout_dir", "excluded_period",
              "network_shares", "sentinel")
DATA_SUFFIXES = (".parquet", ".csv", ".hcc", ".hc", ".tkc")
CACHE_SUFFIXES = (".hcc", ".hc", ".tkc")  # MT5 history and tick caches
TEXT_SUFFIXES = (".json", ".csv", ".txt", ".md")
CLOSED_SUFFIXES = (".key", ".pem", ".pfx", ".rdp")
TERMINAL = "terminal64.exe"
TERMINAL_SKIP = ("node_modules", ".git", ".venv")
PROGRAM_FILES_LEVELS = 2  # v1.6 Q3: <root>\terminal64.exe is level 0
PROFILE_LEVELS = 3
EXCUSED = ("docs", "evidence", "ENV-002-sentinel.json")
SENTINEL_KEYS = ("name", "size", "sha256", "token", "vault_path", "created_utc")
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
HEX32 = re.compile(r"[0-9a-f]{32}")
HEX64 = re.compile(r"[0-9a-f]{64}")
RECALL_ATTRIBUTES = 0x00400000 | 0x00040000  # FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS | FILE_ATTRIBUTE_RECALL_ON_OPEN
SF_DATALESS = 0x40000000  # sys/stat.h of the macOS SDK: a dataless (cloud) file or folder (v2.1 F2)
ICLOUD = ".icloud"  # .<name>.icloud: iCloud Drive's marker file for a file that is not on this machine (v2.1 F6)
VENV_PYTHON = re.compile(r"python(?:3(?:\.[0-9]+)?)?")  # the interpreter link names of .venv/bin (v2.1 F5)
CHUNK = 1 << 20
SHOWN = 3  # paths shown per finding kind in a detail

UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
WOW_UNINSTALL = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
DRIVE_REMOTE = 4
TH32CS_SNAPPROCESS = 0x2
RESOURCE_CONNECTED = 0x1
RESOURCETYPE_ANY = 0x0
NO_ERROR, ERROR_NO_MORE_FILES, ERROR_MORE_DATA, ERROR_NO_MORE_ITEMS, ERROR_NO_NETWORK = 0, 18, 234, 259, 1222
WINDOWS_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/].*|\\\\[^\\/]+[\\/].+")  # a drive or UNC path, judged on any OS
FOLDER_IDS = {  # KNOWNFOLDERID values
    "Downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "Desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
}

# darwin (contract v2.0-v2.6)
MNT_LOCAL = 0x00001000  # sys/mount.h:222 of the macOS SDK (v2.3 r3 F44)
MNT_NOWAIT = 2
ESRCH = 3  # sys/errno.h: the process has ended (errno is not among envcheck's imports)
PATH_SIZE = 4096  # PROC_PIDPATHINFO_MAXSIZE
PID_CAPACITY, PID_LIMIT = 1024, 1 << 20
MOUNT_CAPACITY, MOUNT_LIMIT = 64, 4096
REMOTE_TYPES = ("smbfs", "nfs", "afpfs", "webdav", "ftp")
LOCAL_TYPES = ("apfs", "hfs", "devfs", "autofs", "msdos", "exfat", "udf", "cd9660", "tmpfs", "nullfs")
AUTO_HOME = "map auto_home"
HOME_SKIPPABLE = (".Trash", "Pictures/Photos Library.photoslibrary")  # measured unlistable on the owner's Mac
APP_NOTES = ("crossover", "whisky", "playonmac", "wineskin", "kegworks", "wine", "parallels", "vmware", "utm",
             "virtualbox", "docker", "orbstack")
TOOL_NOTES = (".colima", ".lima", ".docker", ".orbstack", ".wine", ".podman", ".local/share/containers")


# ---- records ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Item:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class Report:
    role: str
    items: tuple[Item, ...]

    @property
    def verdict(self) -> str:
        statuses = {item.status for item in self.items}
        return FAIL if FAIL in statuses else UNKNOWN if UNKNOWN in statuses else PASS


@dataclass(frozen=True)
class Sentinel:
    name: str
    size: int
    sha256: str
    token: str
    vault_path: str
    created_utc: str


@dataclass(frozen=True)
class ResearchRoots:
    repo: Path
    data_dirs: tuple[Path, ...]
    program_files: tuple[Path, ...]
    appdata: Path
    user_profile: Path
    search_dirs: tuple[Path, ...]


@dataclass(frozen=True)
class Facts:
    """What collect read from the OS; None means it could not be read (UNKNOWN)."""
    terminal_paths: tuple[str, ...] | None
    uninstall_display_names: tuple[str, ...] | None
    process_names: tuple[str, ...] | None
    metaquotes_exists: bool | None
    mt5_spec_found: bool | None
    remote_drives: tuple[str, ...] | None
    connected_resources: tuple[str, ...] | None


class ResearchHostError(ValueError):
    """The research host check did not PASS; research must not run."""


# The state behind host_lines(): empty at import; research_host_report clears it and records reader, roots and
# token; the real darwin collect writes only its six keys (contract v2.3 r3 F25, v2.4 r4 F55).
_HOST_SUMMARY: dict = {}


# ---- helpers ---------------------------------------------------------------------------------------
def _norm(path) -> str:
    return os.path.normcase(os.path.abspath(os.fsdecode(os.fspath(path))))


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _status(fails: list[str], unknowns: list[str], ok: str) -> tuple[str, str]:
    """FAIL outranks UNKNOWN inside an item, as in the verdict."""
    if fails:
        return FAIL, _summary(fails)
    if unknowns:
        return UNKNOWN, _summary(unknowns)
    return PASS, ok


def _summary(findings: list[str]) -> str:
    shown = "; ".join(findings[:SHOWN])
    return shown + (f"; and {len(findings) - SHOWN} more" if len(findings) > SHOWN else "")


def _kind(path) -> str:
    """'dir', 'missing' or 'unreadable' for a root, by os.stat only (v1.9 F5: a refused stat is no crash)."""
    try:
        mode = os.stat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return "missing"
    except (OSError, ValueError):
        return "unreadable"
    return "dir" if mode & 0o170000 == 0o040000 else "missing"


def _exists(path) -> bool | None:
    """True, False, or None when it cannot be told (os.path.exists answers False then; v1.9 F5)."""
    try:
        os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except (OSError, ValueError):
        return None
    return True


def _below_terminal(root: Path) -> bool:
    """Whether a folder above root holds terminal64.exe (v1.9 F6), by stat of that one name, never listing.
    A stat that fails for another reason than "not there" counts as a terminal: nothing below is opened."""
    absolute = Path(os.path.abspath(root))  # r2 F13: a relative root's parents end at the cwd
    return any(_exists(ancestor / TERMINAL) is not False for ancestor in absolute.parents)


def is_cloud_only(path) -> bool:
    """A cloud-only file or folder: OneDrive Files On-Demand (recall bits of st_file_attributes) or a dataless
    file or folder of macOS (SF_DATALESS in st_flags). Opening or listing it would download it, so only os.stat
    is used. One function on every platform (v2.1 F6)."""
    status = os.stat(path)
    return bool(getattr(status, "st_file_attributes", 0) & RECALL_ATTRIBUTES
                or getattr(status, "st_flags", 0) & SF_DATALESS)


def _dataless_above(folder) -> Path | None:
    """The first dataless folder from the top down to folder itself, or None (v2.2 r2 F12). The check stops at
    the first one, so nothing below it is stat'ed; a folder that cannot be stat'ed ends the check (the root's
    own stat then reports it)."""
    absolute = Path(os.path.abspath(folder))
    for candidate in (*reversed(absolute.parents), absolute):
        try:
            if is_cloud_only(candidate):
                return candidate
        except (OSError, ValueError):
            return None
    return None


def _appdata_match(name: str) -> bool:
    """A terminal_data name at level 0 of Application Support (v2.1 F8): net.metaquotes.*, metatrader*, metaquotes."""
    lower = name.lower()
    return lower.startswith(("net.metaquotes.", "metatrader")) or lower == "metaquotes"


def _identity(path) -> tuple[int, int] | None:
    """(st_dev, st_ino) of a path after symlinks, or None when it cannot be stat'ed."""
    try:
        status = os.stat(path)
    except (OSError, ValueError):
        return None
    return status.st_dev, status.st_ino


def _is_folder(path, key: str, name: str, identity: tuple[int, int] | None) -> bool:
    """Whether path is the folder whose normalised text is key: by text, or for another spelling of it (another
    case on APFS, a symlinked parent) by (st_dev, st_ino). Only a path with the same last name, in any case, is
    stat'ed (work review r3 F17)."""
    if _norm(path) == key:
        return True
    return identity is not None and Path(path).name.lower() == name and _identity(path) == identity


def _appdata_folder(path, appdata) -> str | None:
    """The level-0 entry of appdata with a terminal_data name that holds path, or None (v2.2 r2 F28). appdata is
    looked for among the ancestors of path by _is_folder, so another spelling of it is found too (r3 F17)."""
    key, name, identity = _norm(appdata), Path(appdata).name.lower(), _identity(appdata)
    absolute = Path(os.path.abspath(path))
    chain = (*reversed(absolute.parents), absolute)
    for folder, child in zip(chain, chain[1:]):
        if _is_folder(folder, key, name, identity):
            return child.name if _appdata_match(child.name) else None
    return None


def _interpreter_identity() -> tuple[int, int] | None:
    """(st_dev, st_ino) of the running interpreter, or None, when no link is excused (v2.1 F5)."""
    if not sys.executable:
        return None
    try:
        status = os.stat(sys.executable)
    except (OSError, ValueError):
        return None
    return status.st_dev, status.st_ino


def _token_patterns(token: str) -> tuple[bytes, ...]:
    """The token as ASCII/UTF-8 and as UTF-16 LE and BE (v1.7, tests-r1 F6); a BOM does not matter."""
    return token.encode("ascii"), token.encode("utf-16-le"), token.encode("utf-16-be")


def _read(path: Path, patterns: tuple[bytes, ...], want_digest: bool) -> tuple[bool, str | None]:
    """(whether any pattern occurs, SHA-256 or None), reading in chunks with an overlap."""
    digest = hashlib.sha256() if want_digest else None
    overlap = max((len(pattern) for pattern in patterns), default=1) - 1
    found, tail = False, b""
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            if digest is not None:
                digest.update(chunk)
            if patterns and not found:
                window = tail + chunk
                found = any(pattern in window for pattern in patterns)
                tail = window[-overlap:] if overlap else b""
    return found, None if digest is None else digest.hexdigest()


_UNREADABLE = object()


def parse_manifest(data: bytes):
    """(listed names in lower case, period end) of a manifest, or None when it is broken."""
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):  # v1.9 F5: a crafted deep manifest is broken
        return None
    if not isinstance(document, dict):
        return None
    files, end = document.get("files"), document.get("period_end_utc")
    if not isinstance(files, list) or not isinstance(end, str) or not TIME_PATTERN.fullmatch(end):
        return None
    names = set()
    for entry in files:
        if not (isinstance(entry, dict) and isinstance(entry.get("name"), str) and isinstance(entry.get("sha256"), str)):
            return None
        names.add(entry["name"].lower())
    try:
        period_end = datetime.strptime(end, TIME_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None
    return names, period_end


# ---- the search of evaluate ---------------------------------------------------------------------------
class _Search:
    """One walk of the repository, the data dirs and the search dirs, with the findings of three items."""

    def __init__(self, roots: ResearchRoots, sentinel: Sentinel | None, quiet: bool = False):
        self.sentinel = sentinel
        self.patterns = _token_patterns(sentinel.token) if sentinel is not None else ()
        self.repo = Path(roots.repo)
        self.default_data = _norm(self.repo / "data")
        self.appdata = Path(roots.appdata)
        self.appdata_key = _norm(roots.appdata)
        self.appdata_name = self.appdata.name.lower()
        self.appdata_id = _identity(roots.appdata)  # r3 F17: another spelling of appdata is recognised by identity
        self.metaquotes = _norm(Path(roots.appdata) / "MetaQuotes")
        self.quiet = quiet  # terminal_data is FAIL already: a terminal data folder is skipped silently (r2 F28)
        self.excused = _norm(self.repo.joinpath(*EXCUSED))
        self.venv_bin = _norm(self.repo / ".venv" / "bin")
        self.interpreter = _interpreter_identity()
        self.holdout: tuple[list[str], list[str]] = ([], [])
        self.excluded: tuple[list[str], list[str]] = ([], [])
        self.found: tuple[list[str], list[str]] = ([], [])
        self.manifests: dict[str, object] = {}
        self.counts = {"roots": 0, "folders listed": 0, "files examined": 0, "reparse points skipped": 0,
                       "interpreter links excused": 0}
        self.plan = self._plan(roots)
        self.prune = {key for _, key, _ in self.plan} | {self.metaquotes}

    # -- what is walked, and under which rules
    def _plan(self, roots: ResearchRoots) -> list[tuple[Path, str, str]]:
        """Every data dir is its own root with the data rules (r1 F1); the repository follows the data rules
        when a data dir contains it. A search dir under the repository or a data dir is walked with them
        (contract v1.5). Every other search dir is its own root too (r2 F14): the outer walk does not enter a
        junction, so a nested search dir behind one would otherwise be searched by nobody."""
        repo_key = _norm(self.repo)
        data: list[tuple[Path, str]] = []
        for folder in roots.data_dirs:
            folder, key = Path(folder), _norm(folder)
            closed = self._closed_root(folder, key)
            if closed is not None:
                self._unlisted("data", folder, closed)
                continue
            kind = _kind(folder)
            if kind == "unreadable":
                self._unlisted("data", folder, "could not be read")
            elif kind == "missing":
                if key != self.default_data:  # v1.6 Q5: a missing <repo>/data has nothing to check
                    self.excluded[1].append(f"data dir {folder} does not exist")
            elif all(key != other for _, other in data):
                data.append((folder, key))
        plan: list[tuple[Path, str, str]] = []
        repo_area = "data" if any(_within(repo_key, other) for _, other in data) else "repo"
        closed = self._closed_root(self.repo, repo_key)
        if closed is not None:
            self._unlisted("repo", self.repo, closed)
        else:
            kind = _kind(self.repo)
            if kind == "dir":
                plan.append((self.repo, repo_key, repo_area))
            else:
                self._unlisted("repo", self.repo, "the repository folder was not found" if kind == "missing"
                               else "could not be read")
        plan += [(folder, key, "data") for folder, key in data if key != repo_key]
        covered = [key for _, key, _ in plan]
        candidates: list[tuple[Path, str]] = []
        for folder in roots.search_dirs:
            folder, key = Path(folder), _norm(folder)
            if any(_within(key, other) for other in covered):
                continue
            closed = self._closed_root(folder, key)
            if closed is not None:
                self._unlisted("search", folder, closed)
                continue
            kind = _kind(folder)
            if kind == "dir":
                candidates.append((folder, key))
            else:  # v1.9 F5: a search dir that is missing or unreadable searched nothing
                self._unlisted("search", folder, "does not exist" if kind == "missing" else "could not be read")
        searched: list[tuple[Path, str, str]] = []
        for folder, key in candidates:
            if all(key != other for _, other, _ in searched):
                searched.append((folder, key, "search"))
        return plan + searched

    def _closed_root(self, folder: Path, key: str) -> str | None:
        """Why a root is never listed, or None: under %APPDATA%\\MetaQuotes (v1.9 F6), at or below a dataless
        folder, checked from the top down before anything below it is stat'ed (v2.2 r2 F12), or under a terminal
        data folder of appdata in any spelling (v2.2 r2 F28, work review r3 F17)."""
        if _within(key, self.metaquotes):
            return "is under %APPDATA%\\MetaQuotes, which is never listed"
        dataless = _dataless_above(folder)
        if dataless is not None:
            if _norm(dataless) == key:
                return "is a dataless folder (its content is in the cloud), not listed"
            return f"is below the dataless folder {dataless}, not listed"
        named = _appdata_folder(folder, self.appdata)
        if named is not None:
            return f"is under {named}, a terminal data folder that is never listed"
        return None

    def _unlisted(self, area: str, folder: Path, why: str = "could not be listed") -> None:
        text = f"{folder} {why}"
        if area != "search":
            self.holdout[1].append(text)
            self.excluded[1].append(text)
        if self.sentinel is not None:
            self.found[1].append(text)

    # -- the walk
    def run(self) -> None:
        sentinel = self.sentinel
        if sentinel is not None:
            if not sentinel.vault_path or not sentinel.name:  # v1.9 F7: an empty value switches a rule off
                self.found[1].append("the sentinel has an empty name or vault_path")
            else:
                exists = _exists(sentinel.vault_path)
                if exists is None:
                    self.found[1].append("the VPS vault path could not be checked on this machine")
                elif exists:
                    self.found[0].append("the VPS vault path exists on this machine")
        for root, _, area in self.plan:
            if area == "search" and sentinel is None:
                continue  # only the sentinel rules read the search dirs
            self.counts["roots"] += 1
            for folder, files, folders, reparse, beside, at_appdata in self._walk(root, area):
                self._visit(area, folder, files, folders, reparse, beside, at_appdata)

    def _walk(self, root: Path, area: str):
        stack = [(root, _below_terminal(root))]  # v1.9 F6: a root below a terminal folder is never opened
        while stack:
            folder, beside = stack.pop()
            try:
                dataless = is_cloud_only(folder)
            except (OSError, ValueError):
                self._unlisted(area, folder, "could not be read")
                continue
            if dataless:  # v2.1 F6: listing it would fetch its entries from the cloud
                self._unlisted(area, folder, "is a dataless folder (its content is in the cloud), not listed")
                continue
            try:
                with os.scandir(folder) as listing:
                    entries = list(listing)
            except OSError:
                self._unlisted(area, folder)
                continue
            self.counts["folders listed"] += 1
            files, folders, reparse = [], [], []
            for entry in entries:
                try:
                    if entry.is_junction() or entry.is_symlink():
                        reparse.append(entry)  # v1.7 F8: not entered; v1.9 F2: the name rules still see it
                    elif entry.is_dir(follow_symlinks=False):
                        folders.append(entry)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry)
                except OSError:
                    self._unlisted(area, Path(entry.path), "could not be read")
            here = beside or any(entry.name.lower() == TERMINAL for entry in files + reparse)
            at_appdata = _is_folder(folder, self.appdata_key, self.appdata_name, self.appdata_id)
            yield folder, files, folders, reparse, here, at_appdata
            for entry in folders:
                if _norm(entry.path) in self.prune:
                    continue
                if at_appdata and _appdata_match(entry.name):  # v2.2 r2 F28: never listed, never opened
                    if not (self.quiet or entry.name.lower() == "metaquotes"):  # r3 F28: MetaQuotes stays silent
                        self._unlisted(area, Path(entry.path), "is a terminal data folder, never listed")
                    continue
                stack.append((Path(entry.path), here))

    def _visit(self, area: str, folder: Path, files: list, folders: list, reparse: list, beside: bool,
               at_appdata: bool) -> None:
        sentinel = self.sentinel
        if area != "search":
            for entry in folders + reparse:
                if entry.name.lower() == "holdout":
                    self.holdout[0].append(f"{entry.path} is a holdout folder")
        folder_key = _norm(folder)
        for entry in reparse:
            self.counts["reparse points skipped"] += 1
            if sentinel is not None and entry.name.lower() == sentinel.name.lower():
                self.found[0].append(f"{entry.path} has the sentinel's name")
            if area == "search":
                continue
            if self._excused(folder_key, entry):
                self.counts["interpreter links excused"] += 1
            else:  # v1.9 F3 (a): research code could read through it
                self._unlisted(area, Path(entry.path), "is a junction or symbolic link, not entered")
        by_name = {entry.name.lower(): entry for entry in files}
        for entry in files:
            self.counts["files examined"] += 1
            self._file(area, entry, beside or (at_appdata and _appdata_match(entry.name)), by_name)

    def _excused(self, folder_key: str, entry) -> bool:
        """The one symlink exception (v2.1 F5): python, python3 or python3.N at level 0 of <repo>/.venv/bin
        that ends at the running interpreter (the same st_dev and st_ino). It is never opened."""
        if folder_key != self.venv_bin or self.interpreter is None or not VENV_PYTHON.fullmatch(entry.name):
            return False
        try:
            if entry.is_junction() or not entry.is_symlink():
                return False
            status = os.stat(entry.path)
        except (OSError, ValueError):
            return False
        return (status.st_dev, status.st_ino) == self.interpreter

    def _icloud_marker(self, area: str, path: Path, inner: str) -> None:
        """.<name>.icloud, iCloud Drive's marker for a file that is not downloaded: never opened (v2.1 F6; v2.2
        r2 F30; v2.4 r4 F54). Under the repository or a data dir it makes excluded_period and sentinel UNKNOWN;
        in the search dirs only a .json one makes sentinel UNKNOWN; the sentinel's own name is FAIL by rule (2)."""
        sentinel = self.sentinel
        named = sentinel is not None and inner == sentinel.name.lower()
        if named:
            self.found[0].append(f"{path} is the iCloud marker of a file with the sentinel's name")
        if area != "search":
            self.excluded[1].append(f"{path} is the iCloud marker of a file that is not on this machine")
            if sentinel is not None and not named:
                self.found[1].append(f"{path} is the iCloud marker of a file that is not on this machine")
        elif sentinel is not None and not named and inner.endswith(".json"):
            self.found[1].append(f"{path} is the iCloud marker of a .json file whose size cannot be read")

    # -- one file
    def _file(self, area: str, entry, beside: bool, by_name: dict) -> None:
        lower = entry.name.lower()
        path = Path(entry.path)
        if lower.startswith(".") and lower.endswith(ICLOUD) and len(lower) > len(ICLOUD) + 1:
            self._icloud_marker(area, path, lower[1:-len(ICLOUD)])
            return
        suffix = os.path.splitext(lower)[1]
        closed = lower == ".env" or lower.startswith(".env.") or suffix in CLOSED_SUFFIXES or beside
        sentinel = self.sentinel
        if sentinel is not None and lower == sentinel.name.lower():
            self.found[0].append(f"{path} has the sentinel's name")
        if area == "data" and suffix in DATA_SUFFIXES:
            self._data_file(entry, beside, by_name)
        elif area == "repo" and suffix in CACHE_SUFFIXES:
            self.excluded[0].append(f"{path} is an MT5 cache file in the repository")
        if sentinel is None:
            return
        if area == "search":
            if suffix != ".json":
                return
            size = self._size(entry)
            if size is None:
                self.found[1].append(f"{path} could not be read")
            elif size == sentinel.size:
                self._compare(path, closed, size, token=False)
        elif suffix in TEXT_SUFFIXES:
            size = self._size(entry)
            if size is None:
                self.found[1].append(f"{path} could not be read")
            elif _norm(path) != self.excused:
                self._compare(path, closed, size, token=True)
            elif suffix == ".json" and size == sentinel.size:  # v1.9 F7: excused from rule (4) only
                self._compare(path, closed, size, token=False)

    @staticmethod
    def _size(entry) -> int | None:
        try:
            return entry.stat(follow_symlinks=False).st_size
        except OSError:
            return None

    def _compare(self, path: Path, closed: bool, size: int, *, token: bool) -> None:
        """Rules (3) and (4) for a file they would open; never-open and cloud-only files are UNKNOWN."""
        sentinel = self.sentinel
        if sentinel is None:
            return
        if closed:
            self.found[1].append(f"{path} would have to be read but is never opened")
            return
        try:
            cloud = is_cloud_only(path)
        except OSError:
            self.found[1].append(f"{path} could not be read")
            return
        if cloud:
            self.found[1].append(f"{path} is cloud-only and was not opened")
            return
        want_digest = path.suffix.lower() == ".json" and size == sentinel.size
        try:
            found, digest = _read(path, self.patterns if token else (), want_digest)
        except OSError:
            self.found[1].append(f"{path} could not be read")
            return
        if found:
            self.found[0].append(f"{path} holds the sentinel token")
        if digest is not None and digest == sentinel.sha256.lower():
            self.found[0].append(f"{path} is a copy of the sentinel")

    # -- excluded_period in the data dirs
    def _data_file(self, entry, beside: bool, by_name: dict) -> None:
        """Every manifest that covers the file must pass (v1.9 F8: per-file and folder manifest alike)."""
        path = Path(entry.path)
        manifests = [found for found in (by_name.get(f"{entry.name}.manifest.json".lower()), by_name.get("manifest.json"))
                     if found is not None]
        if not manifests:
            self.excluded[0].append(f"{path} has no manifest")
        for manifest in manifests:
            parsed = self._manifest(manifest, beside)
            if parsed is _UNREADABLE:
                self.excluded[1].append(f"{path}: its manifest {manifest.path} could not be read")
            elif parsed is None:
                self.excluded[0].append(f"{path}: its manifest {manifest.path} is broken")
            else:
                names, period_end = parsed
                if entry.name.lower() not in names:
                    self.excluded[0].append(f"{path} is not listed in {manifest.path}")
                elif period_end > HOLDOUT_CUTOFF_UTC:
                    self.excluded[0].append(f"{path} ends {period_end.strftime(TIME_FORMAT)} in {manifest.path}, "
                                            "after the cutoff")

    def _manifest(self, entry, beside: bool):
        key = _norm(entry.path)
        if key not in self.manifests:
            self.manifests[key] = self._read_manifest(Path(entry.path), entry.name.lower(), beside)
        return self.manifests[key]

    @staticmethod
    def _read_manifest(path: Path, lower: str, beside: bool):
        if beside or lower.startswith(".env."):
            return _UNREADABLE
        try:
            if is_cloud_only(path):  # v1.7, tests-r1 F2
                return _UNREADABLE
            data = path.read_bytes()
        except OSError:
            return _UNREADABLE
        return parse_manifest(data)

    # -- the three items
    def items(self) -> tuple[Item, Item, Item]:
        """The three searching items; each detail ends with what was searched (v1.9 F9)."""
        cutoff = HOLDOUT_CUTOFF_UTC.strftime(TIME_FORMAT)
        counts = " (searched: " + ", ".join(f"{name} {value}" for name, value in self.counts.items()) + ")"

        def item(name: str, findings: tuple[list[str], list[str]], ok: str) -> Item:
            status, detail = _status(*findings, ok)
            return Item(name, status, detail + counts)

        holdout = item("holdout_dir", self.holdout, "no holdout folder in the repository or the data dirs")
        excluded = item("excluded_period", self.excluded,
                        f"every data file has a manifest that ends by {cutoff}; no MT5 cache in the repository")
        sentinel = self.sentinel
        if sentinel is None:
            found = Item("sentinel", UNKNOWN, "no sentinel given (--sentinel-file)" + counts)
        else:
            checked = f"{sentinel.name}, {sentinel.size} bytes, SHA-256 {sentinel.sha256}"
            found = item("sentinel", self.found, f"no copy, name, token or vault path of {checked} found")
        return holdout, excluded, found


# ---- evaluate ------------------------------------------------------------------------------------------
def _terminal_install(facts: Facts) -> Item:
    fails, unknowns = [], []
    if facts.terminal_paths is None:
        unknowns.append("the terminal paths could not be read")
    elif facts.terminal_paths:
        fails.append(f"{len(facts.terminal_paths)} terminal path(s): {', '.join(facts.terminal_paths[:SHOWN])}")
    if facts.uninstall_display_names is None:
        unknowns.append("the Uninstall entries could not be read")
    else:
        named = [name for name in facts.uninstall_display_names if "metatrader" in name.lower()]
        if named:
            fails.append(f"Uninstall entries: {', '.join(named[:SHOWN])}")
    if facts.process_names is None:
        unknowns.append("the running processes could not be read")
    elif any(name.lower() == TERMINAL for name in facts.process_names):
        fails.append("terminal64.exe is running")
    return Item("terminal_install", *_status(fails, unknowns, "no MetaTrader folder, terminal64.exe, Uninstall entry or "
                                                               "running terminal"))


def _flag(name: str, value: bool | None, bad: str, ok: str) -> Item:
    if value is None:
        return Item(name, UNKNOWN, "could not be read")
    return Item(name, FAIL, bad) if value else Item(name, PASS, ok)


def _network_shares(facts: Facts) -> Item:
    fails, unknowns = [], []
    for value, what in ((facts.remote_drives, "remote drives"), (facts.connected_resources, "connected resources")):
        if value is None:
            unknowns.append(f"the {what} could not be read")
        elif value:
            fails.append(f"{what}: {', '.join(value[:SHOWN])}")
    return Item("network_shares", *_status(fails, unknowns, "no remote drive and no connected network resource"))


def evaluate(facts: Facts, roots: ResearchRoots, sentinel: Sentinel | None) -> Report:
    """Judge the facts and search the roots by the contract's read rules; reads only, never writes."""
    search = _Search(roots, sentinel, quiet=facts.metaquotes_exists is True)
    search.run()
    holdout, excluded, found = search.items()
    items: tuple[Item, ...] = (
        _terminal_install(facts),
        _flag("terminal_data", facts.metaquotes_exists, "%APPDATA%\\MetaQuotes exists", "no %APPDATA%\\MetaQuotes"),
        _flag("mt5_package", facts.mt5_spec_found, "the MetaTrader5 package can be imported",
              "the MetaTrader5 package cannot be imported"),
        holdout,
        excluded,
        _network_shares(facts),
        found,
    )
    token = sentinel.token if sentinel is not None and sentinel.token else None
    if token:  # v1.6 Q7: a path or a name could still spell the token
        items = tuple(Item(item.name, item.status, item.detail.replace(token, "<token>")) for item in items)
    return Report(role=ROLE, items=items)


# ---- collect (Windows) ---------------------------------------------------------------------------------
def _list_folders(folder: Path):
    """(plain subfolders, file names, reparse points) of a folder; reparse points are never entered."""
    with os.scandir(folder) as listing:
        entries = list(listing)
    folders, names, reparse = [], [], []
    for entry in entries:
        if entry.is_junction() or entry.is_symlink():
            reparse.append(entry)
        elif entry.is_dir(follow_symlinks=False):
            folders.append(entry)
        else:
            names.append(entry.name)
    return folders, names, reparse


def _find_terminal64(root: Path, levels: int, skip: tuple[str, ...], prune: set[str]) -> list[str]:
    """terminal64.exe at levels 0..levels below root. The root must be listable (v1.9 F5); folders below it
    that refuse listing are skipped (v1.8). A reparse point named terminal64.exe is reported (v1.9 F2)."""
    found, stack = [], [(root, 0)]
    while stack:
        folder, level = stack.pop()
        try:
            folders, names, reparse = _list_folders(folder)
        except OSError:
            if level == 0:
                raise
            continue
        found += [str(folder / name) for name in names if name.lower() == TERMINAL]
        found += [entry.path for entry in reparse if entry.name.lower() == TERMINAL]
        if level < levels:
            stack += [(Path(entry.path), level + 1) for entry in folders
                      if entry.name.lower() not in skip and _norm(entry.path) not in prune]
    return found


def find_terminal_paths(program_files, user_profile, appdata) -> tuple[str, ...]:
    """The three path rules of terminal_install (contract v1.6 Q2/Q3, v1.8); pure apart from listing folders.

    Program Files*\\MetaTrader* folders, terminal64.exe at levels 0-2 of each Program Files* folder, and
    terminal64.exe at levels 0-3 of the user profile outside .git, .venv, node_modules and
    %APPDATA%\\MetaQuotes (never listed). Names compare without case. A root that is missing or cannot be
    listed raises, so collect gives None (v1.9 F5); a reparse point is named but not entered (v1.9 F2)."""
    roots = [Path(item) for item in program_files]
    if not roots:
        raise OSError("no Program Files folder to search")
    found: list[str] = []
    for root in roots:
        if _kind(root) != "dir":
            raise OSError(f"{root} is not a readable folder")
        folders, _, reparse = _list_folders(root)
        found += [entry.path for entry in folders + reparse if entry.name.lower().startswith("metatrader")]
        found += _find_terminal64(root, PROGRAM_FILES_LEVELS, (), set())
    profile = Path(user_profile)
    if _kind(profile) != "dir":
        raise OSError(f"{profile} is not a readable folder")
    found += _find_terminal64(profile, PROFILE_LEVELS, TERMINAL_SKIP, {_norm(Path(appdata) / "MetaQuotes")})
    unique: dict[str, str] = {}
    for path in found:
        unique.setdefault(_norm(path), path)
    return tuple(sorted(unique.values()))


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_uint32), ("cntUsage", ctypes.c_uint32), ("th32ProcessID", ctypes.c_uint32),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", ctypes.c_uint32),
                ("cntThreads", ctypes.c_uint32), ("th32ParentProcessID", ctypes.c_uint32),
                ("pcPriClassBase", ctypes.c_int32), ("dwFlags", ctypes.c_uint32), ("szExeFile", ctypes.c_wchar * 260)]


class _NETRESOURCEW(ctypes.Structure):
    _fields_ = [("dwScope", ctypes.c_uint32), ("dwType", ctypes.c_uint32), ("dwDisplayType", ctypes.c_uint32),
                ("dwUsage", ctypes.c_uint32), ("lpLocalName", ctypes.c_wchar_p), ("lpRemoteName", ctypes.c_wchar_p),
                ("lpComment", ctypes.c_wchar_p), ("lpProvider", ctypes.c_wchar_p)]


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_ubyte * 8)]


def _guid(text: str) -> _GUID:
    parts = text.split("-")
    tail = bytes.fromhex(parts[3] + parts[4])
    return _GUID(int(parts[0], 16), int(parts[1], 16), int(parts[2], 16), (ctypes.c_ubyte * 8)(*tail))


def _remote_drives() -> tuple[str, ...]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetDriveTypeW.argtypes = (ctypes.c_wchar_p,)
    kernel32.GetDriveTypeW.restype = ctypes.c_uint32
    return tuple(drive for drive in os.listdrives() if kernel32.GetDriveTypeW(drive) == DRIVE_REMOTE)


def _process_names() -> tuple[str, ...]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = (ctypes.c_uint32, ctypes.c_uint32)
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Process32FirstW.argtypes = (ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W))
    kernel32.Process32NextW.argtypes = (ctypes.c_void_p, ctypes.POINTER(_PROCESSENTRY32W))
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot is None or snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    names = []
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):  # v1.9 F4: a failure is no empty list
            raise ctypes.WinError(ctypes.get_last_error())
        names.append(entry.szExeFile)
        while kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
            names.append(entry.szExeFile)
        error = ctypes.get_last_error()
        if error != ERROR_NO_MORE_FILES:
            raise ctypes.WinError(error)
    finally:
        kernel32.CloseHandle(snapshot)
    return tuple(names)


def _connected_resources() -> tuple[str, ...]:
    mpr = ctypes.WinDLL("mpr", use_last_error=True)
    mpr.WNetOpenEnumW.argtypes = (ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                  ctypes.POINTER(ctypes.c_void_p))
    mpr.WNetOpenEnumW.restype = ctypes.c_uint32
    mpr.WNetEnumResourceW.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p,
                                      ctypes.POINTER(ctypes.c_uint32))
    mpr.WNetEnumResourceW.restype = ctypes.c_uint32
    mpr.WNetCloseEnum.argtypes = (ctypes.c_void_p,)
    mpr.WNetCloseEnum.restype = ctypes.c_uint32
    handle = ctypes.c_void_p()
    status = mpr.WNetOpenEnumW(RESOURCE_CONNECTED, RESOURCETYPE_ANY, 0, None, ctypes.byref(handle))
    if status == ERROR_NO_NETWORK:
        return ()
    if status != NO_ERROR:
        raise OSError(status, "WNetOpenEnumW failed")
    names = []
    try:
        size = 16384
        while True:
            buffer = ctypes.create_string_buffer(size)
            count, length = ctypes.c_uint32(0xFFFFFFFF), ctypes.c_uint32(size)
            status = mpr.WNetEnumResourceW(handle, ctypes.byref(count), buffer, ctypes.byref(length))
            if status == ERROR_NO_MORE_ITEMS:
                break
            if status == ERROR_MORE_DATA:
                size = max(size * 2, length.value)
                continue
            if status != NO_ERROR:
                raise OSError(status, "WNetEnumResourceW failed")
            entries = ctypes.cast(buffer, ctypes.POINTER(_NETRESOURCEW))
            for index in range(count.value):
                name = entries[index].lpRemoteName or entries[index].lpLocalName
                if name:
                    names.append(name)
    finally:
        mpr.WNetCloseEnum(handle)
    return tuple(names)


def _uninstall_display_names() -> tuple[str, ...]:
    import winreg
    names = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for sub in (UNINSTALL, WOW_UNINSTALL):
            try:
                key = winreg.OpenKey(root, sub, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                continue
            with key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        child_name = winreg.EnumKey(key, index)
                        with winreg.OpenKey(key, child_name, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as child:
                            value = winreg.QueryValueEx(child, "DisplayName")[0]
                    except FileNotFoundError:
                        continue
                    if isinstance(value, str):
                        names.append(value)
    return tuple(names)


def _known_folder(name: str) -> Path | None:
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = (ctypes.POINTER(_GUID), ctypes.c_uint32, ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_wchar_p))
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    folder_id = _guid(FOLDER_IDS[name])
    path = ctypes.c_wchar_p()
    result = shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path))
    try:
        value = path.value
    finally:
        ole32.CoTaskMemFree(path)  # freed whether the call succeeded or not
    return Path(value) if result == 0 and value else None


def _collect_win32(roots: ResearchRoots) -> Facts:
    """The win32 reader of v1.9, unchanged: every fact from the OS; a fact that cannot be read is None (UNKNOWN)."""
    def guarded(read):
        try:
            return read()
        except (OSError, ValueError, AttributeError, ImportError):
            return None

    return Facts(
        terminal_paths=guarded(lambda: find_terminal_paths(roots.program_files, roots.user_profile, roots.appdata)),
        uninstall_display_names=guarded(_uninstall_display_names),
        process_names=guarded(_process_names),
        metaquotes_exists=guarded(lambda: (Path(roots.appdata) / "MetaQuotes").exists()),
        mt5_spec_found=guarded(lambda: importlib.util.find_spec("MetaTrader5") is not None),
        remote_drives=guarded(_remote_drives),
        connected_resources=guarded(_connected_resources),
    )


# ---- collect (darwin; contract v2.0-v2.6) ------------------------------------------------------------
class _STATFS(ctypes.Structure):
    """struct statfs of macOS arm64 (64-bit inodes): 2168 bytes (contract v2.1 F19)."""
    _fields_ = [("f_bsize", ctypes.c_uint32), ("f_iosize", ctypes.c_int32), ("f_blocks", ctypes.c_uint64),
                ("f_bfree", ctypes.c_uint64), ("f_bavail", ctypes.c_uint64), ("f_files", ctypes.c_uint64),
                ("f_ffree", ctypes.c_uint64), ("f_fsid", ctypes.c_int32 * 2), ("f_owner", ctypes.c_uint32),
                ("f_type", ctypes.c_uint32), ("f_flags", ctypes.c_uint32), ("f_fssubtype", ctypes.c_uint32),
                ("f_fstypename", ctypes.c_char * 16), ("f_mntonname", ctypes.c_char * 1024),
                ("f_mntfromname", ctypes.c_char * 1024), ("f_flags_ext", ctypes.c_uint32),
                ("f_reserved", ctypes.c_uint32 * 7)]


def reader_name() -> str:
    """The reader of this process: win32, darwin or none, from sys.platform when called (v2.1 F1)."""
    platform = sys.platform
    return platform if platform in ("win32", "darwin") else "none"


def _darwin_home() -> str:
    return os.path.expanduser("~")


def _darwin_application_dirs(home) -> tuple[Path, ...]:
    return Path("/Applications"), Path(home) / "Applications"


# The raw readers hold the ctypes calls only (contract v2.2 r2 F4); tests replace them.
def _darwin_list_pids(capacity: int) -> tuple[int, tuple[int, ...]]:
    libsystem = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    libsystem.proc_listallpids.argtypes = (ctypes.c_void_p, ctypes.c_int)
    libsystem.proc_listallpids.restype = ctypes.c_int
    buffer = (ctypes.c_int * capacity)()
    ctypes.set_errno(0)
    count = libsystem.proc_listallpids(buffer, ctypes.sizeof(buffer))
    if count < 0:
        raise OSError(ctypes.get_errno(), "proc_listallpids failed")
    return count, tuple(buffer[:min(count, capacity)])


def _darwin_pid_path(pid: int) -> tuple[str | None, int]:
    libsystem = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    libsystem.proc_pidpath.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32)
    libsystem.proc_pidpath.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(PATH_SIZE)
    ctypes.set_errno(0)
    size = libsystem.proc_pidpath(pid, buffer, ctypes.sizeof(buffer))
    if size <= 0:
        return None, ctypes.get_errno()
    return os.fsdecode(buffer.value), 0


def _darwin_mounts(capacity: int) -> tuple[int, tuple[tuple[str, str, str, int], ...]]:
    libsystem = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    libsystem.getfsstat.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
    libsystem.getfsstat.restype = ctypes.c_int
    entries = (_STATFS * capacity)()
    ctypes.set_errno(0)
    count = libsystem.getfsstat(entries, ctypes.sizeof(entries), MNT_NOWAIT)
    if count < 0:
        raise OSError(ctypes.get_errno(), "getfsstat failed")
    return count, tuple((os.fsdecode(entry.f_fstypename), os.fsdecode(entry.f_mntfromname),
                         os.fsdecode(entry.f_mntonname), int(entry.f_flags)) for entry in entries[:min(count, capacity)])


# The pure functions hold every rule; they read only through the raw readers and write no module state.
def read_process_paths(own_pid: int, own_path: str) -> tuple[tuple[str, ...], int, int]:
    """(paths read, pids listed, pids skipped) of the running processes (v2.1 F7, v2.3 r3 F25).

    A full buffer is a cut list: it grows and the list is read again. pid 0 and a process that ended (ESRCH)
    are skipped and counted. Any other errno, a list without this process or another path for it raises
    OSError whose text is the reason of the processes: line."""
    capacity = PID_CAPACITY
    while True:
        try:
            count, pids = _darwin_list_pids(capacity)
        except OSError as error:
            raise OSError(f"proc_listallpids failed, errno {error.errno}") from error
        if count < capacity:
            break
        if capacity >= PID_LIMIT:
            raise OSError(f"proc_listallpids filled a buffer of {capacity} pids")
        capacity *= 2
    if count <= 0:
        raise OSError(f"listed {count} pids")
    listed = len(pids)
    paths: list[str] = []
    skipped, own = 0, None
    for pid in pids:
        if pid == 0:
            skipped += 1
            continue
        path, code = _darwin_pid_path(pid)
        if path is None:
            if code == ESRCH:
                skipped += 1
                continue
            raise OSError(f"errno {code} on pid {pid}, {listed} pids")
        paths.append(path)
        if pid == own_pid:
            own = path
    if own_pid not in pids:
        raise OSError(f"own pid missing, {listed} pids")
    if own != own_path:
        raise OSError(f"own path differs, {listed} pids")
    return tuple(paths), listed, skipped


def read_mounts() -> tuple[tuple[str, str, str, int], ...]:
    """Every mount as (type, source, mount point, flags); a full buffer grows and is read again (v2.2 r2 F31)."""
    capacity = MOUNT_CAPACITY
    while True:
        try:
            count, entries = _darwin_mounts(capacity)
        except OSError as error:
            raise OSError(f"getfsstat failed, errno {error.errno}") from error
        if count < capacity:
            return tuple(entries)
        if capacity >= MOUNT_LIMIT:
            raise OSError(f"getfsstat filled a buffer of {capacity} mounts")
        capacity *= 2


def _mount_point_allowed(point: str) -> bool:
    """/, /dev and paths under /System/Volumes/, but under /System/Volumes/Data/ only Data itself and
    Data/home (v2.2 r2 F32, v2.3 r3 F32)."""
    if point in ("/", "/dev", "/System/Volumes/Data", "/System/Volumes/Data/home"):
        return True
    if point.startswith("/System/Volumes/Data/"):
        return False
    return point.startswith("/System/Volumes/")


def classify_mounts(entries) -> tuple[tuple[str, ...], tuple[str, ...] | None, tuple[str, ...], str | None]:
    """(remote_drives, connected_resources, mount points not allowed, problem of /) of a mount list.

    Per mount the FAIL rules come first (a remote type, or no MNT_LOCAL on a type other than autofs), then
    the UNKNOWN rules (autofs other than map auto_home, a type outside the local list, a mount point outside
    the allow list). / must be apfs: no mount at / is UNKNOWN, and so is every mount at / that passes the FAIL
    rules with another type, also one stacked over the apfs root (v2.2 r2 F26, v2.4 r4 F53, work review r3 F16)."""
    remote: list[str] = []
    outside: list[str] = []
    unknown = False
    root_seen = False
    root: str | None = None
    for fstype, source, point, flags in entries:
        kind = str(fstype).lower()
        root_seen = root_seen or point == "/"
        if kind in REMOTE_TYPES or (not flags & MNT_LOCAL and kind != "autofs"):
            remote.append(f"{fstype} {source} on {point}")
            continue
        if point == "/" and kind != "apfs" and root is None:
            root = kind
        if kind == "autofs" and source != AUTO_HOME:
            unknown = True
        if kind not in LOCAL_TYPES:
            unknown = True
        if not _mount_point_allowed(point):
            unknown = True
            outside.append(point)
    if not root_seen:
        root = "missing"
    if root is not None:
        unknown = True
    return tuple(remote), None if unknown else (), tuple(outside), root


def classify_processes(paths) -> tuple[tuple[str, ...], tuple[str, ...] | None, int]:
    """(terminal paths, process_names, Wine loaders) of executable paths (v2.1 F7, v2.3 r3 F33, v2.4 r4 F53).

    A path with any component whose name holds "metatrader", or whose name is terminal64.exe, is a terminal
    path. A name that starts with "wine" outside such a path is a Wine loader: the list is then unreadable
    (process_names None), while the terminal paths are kept."""
    terminal: list[str] = []
    names: list[str] = []
    loaders = 0
    for path in paths:
        parts = [part for part in str(path).split("/") if part]
        name = parts[-1] if parts else str(path)
        names.append(name)
        if any("metatrader" in part.lower() for part in parts) or name.lower() == TERMINAL:
            terminal.append(str(path))
        elif name.lower().startswith("wine"):
            loaders += 1
    return tuple(terminal), tuple(names) if loaders == 0 else None, loaders


def _wine_folder(path: Path) -> bool:
    """Whether a Wine folder exists; a symlink raises OSError "symlink" (v2.2 r2 F10, v2.3 r3 F43)."""
    try:
        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return False
    if mode & 0o170000 == 0o120000:
        raise OSError(None, "symlink", str(path))
    return mode & 0o170000 == 0o040000


def _wine_entries(folder: Path, match) -> list[Path]:
    """The subfolders of a Wine folder whose lower-case name passes match, by name; the folder must be
    listable and no matching entry may be a symlink (v2.2 r2 F10, v2.3 r3 F43)."""
    with os.scandir(folder) as listing:
        entries = list(listing)
    found = []
    for entry in entries:
        if not match(entry.name.lower()):
            continue
        if entry.is_symlink() or entry.is_junction():
            raise OSError(None, "symlink", entry.path)
        if entry.is_dir(follow_symlinks=False):
            found.append(Path(entry.path))
    return sorted(found, key=lambda path: path.name)


def _wine_program_files(prefix: Path) -> list[Path]:
    """The drive_c/Program Files* roots of a prefix; a prefix without them has none, which is no error."""
    roots: list[Path] = []
    for drive_c in _wine_entries(prefix, lambda name: name == "drive_c"):
        for root in _wine_entries(drive_c, lambda name: name.startswith("program files")):
            with os.scandir(root):  # a root that cannot be listed raises here, as default_roots must
                pass
            roots.append(root)
    return roots


def wine_prefixes(home) -> tuple[tuple[Path, ...], tuple[Path, ...], tuple[Path, ...]]:
    """(prefixes, source folders that exist, drive_c/Program Files* roots) of the known Wine places, in the
    contract's order: ~/Library/PlayOnMac/wineprefix (any case), ~/Library/Application Support/CrossOver/Bottles
    and ~/.wine (a prefix only with drive_c). A folder of that chain that exists but cannot be listed, or is a
    symlink, raises OSError (v2.1 F9; v2.2 r2 F10; v2.3 r3 F43; v2.4 r4 F53)."""
    home = Path(home)
    prefixes: list[Path] = []
    sources: list[Path] = []
    roots: list[Path] = []
    for parent, wanted in ((home / "Library" / "PlayOnMac", "wineprefix"),
                           (home / "Library" / "Application Support" / "CrossOver", "bottles")):
        if not _wine_folder(parent):
            continue
        for source in _wine_entries(parent, lambda name, wanted=wanted: name == wanted):
            sources.append(source)
            for prefix in _wine_entries(source, lambda name: True):
                prefixes.append(prefix)
                roots += _wine_program_files(prefix)
    wine = home / ".wine"
    if _wine_folder(wine):
        sources.append(wine)
        if _wine_entries(wine, lambda name: name == "drive_c"):
            prefixes.append(wine)
            roots += _wine_program_files(wine)
    return tuple(prefixes), tuple(sources), tuple(roots)


def find_wine_program_files(home) -> tuple[Path, ...]:
    return wine_prefixes(home)[2]


def _darwin_walk(root: Path, levels: int, *, skip=(), never=frozenset(), skippable=frozenset(),
                 metatrader=False) -> tuple[list[str], bool, list[str]]:
    """(paths found, complete, folders skipped) of one terminal search root on darwin (v2.1 F6, F10; r2 F10).

    terminal64.exe at levels 0..levels, and MetaTrader* entries at level 0 when metatrader is set. A dataless
    folder is skipped unlisted; a folder that cannot be listed is skipped only when it is in skippable,
    otherwise the search is incomplete (the v1.8 skip rule does not apply on darwin). A reparse point named
    terminal64.exe is named, never entered."""
    found: list[str] = []
    skipped: list[str] = []
    complete = True
    stack = [(Path(root), 0)]
    while stack:
        folder, level = stack.pop()
        try:
            dataless = is_cloud_only(folder)
        except (OSError, ValueError):
            complete = False
            continue
        if dataless:
            skipped.append(str(folder))
            if level == 0:  # work review r3 F19: a dataless root itself was never searched
                complete = False
            continue
        try:
            folders, names, reparse = _list_folders(folder)
        except OSError:
            if _norm(folder) in skippable:
                skipped.append(str(folder))
            else:
                complete = False
            continue
        if metatrader and level == 0:
            found += [entry.path for entry in folders + reparse if entry.name.lower().startswith("metatrader")]
        found += [str(folder / name) for name in names if name.lower() == TERMINAL]
        found += [entry.path for entry in reparse if entry.name.lower() == TERMINAL]
        if level < levels:
            stack += [(Path(entry.path), level + 1) for entry in folders
                      if entry.name.lower() not in skip and _norm(entry.path) not in never]
    return found, complete, skipped


def find_terminal_paths_darwin(applications, program_files, home,
                               never_listed) -> tuple[tuple[str, ...], bool, tuple[str, ...]]:
    """(paths found, search complete, folders skipped) of the darwin path rules of terminal_install.

    Level-0 entries of the application folders whose name holds "metatrader" (names only; a folder that does
    not exist has none, one that cannot be listed makes the search incomplete), MetaTrader* and terminal64.exe
    at levels 0-2 of each Program Files root, and terminal64.exe at levels 0-3 of home outside .git, .venv,
    node_modules and never_listed (compared by path; v2.1 F8, F10, F12; v2.2 r2 F4, F12, F30, F33)."""
    found: list[str] = []
    skipped: list[str] = []
    complete = True
    for folder in applications:
        folder = Path(folder)
        if _kind(folder) == "missing":
            continue
        try:
            with os.scandir(folder) as listing:
                found += [entry.path for entry in listing if "metatrader" in entry.name.lower()]
        except OSError:
            complete = False
    for root in program_files:
        paths, whole, passed = _darwin_walk(Path(root), PROGRAM_FILES_LEVELS, metatrader=True)
        found += paths
        skipped += passed
        complete = complete and whole
    home = Path(home)
    never = frozenset(_norm(path) for path in never_listed)
    skippable = frozenset(_norm(home.joinpath(*relative.split("/"))) for relative in HOME_SKIPPABLE)
    paths, whole, passed = _darwin_walk(home, PROFILE_LEVELS, skip=TERMINAL_SKIP, never=never, skippable=skippable)
    found += paths
    skipped += passed
    unique: dict[str, str] = {}
    for path in found:
        unique.setdefault(_norm(path), path)
    return tuple(sorted(unique.values())), complete and whole, tuple(skipped)


def _tilde(path, home) -> str:
    """A path under home as ~/..., any other path as it is (v2.4 r4 F48: no account name in the wine: line)."""
    text, base = os.path.abspath(os.fspath(path)), os.path.abspath(os.fspath(home))
    if not _within(text, base):
        return text
    relative = os.path.relpath(text, base)
    return "~" if relative == "." else f"~/{relative}"


def _wine_reason(error: OSError, home) -> str:
    """<path from ~/>: [Errno <n>] <strerror>, or <path from ~/>: symlink (v2.4 r4 F48, v2.5 r5 F60)."""
    where = _tilde(error.filename, home) if error.filename else "?"
    if error.strerror == "symlink":
        return f"{where}: symlink"
    return f"{where}: [Errno {error.errno}] {error.strerror}"


def _darwin_guard() -> str | None:
    """Why processes and mounts are not read: a DYLD_* variable or a machine other than arm64 (v2.1 F3, F19).
    It runs before any process or mount reader (v2.2 r2 F4)."""
    if any(key.startswith("DYLD_") for key in os.environ):
        return "DYLD_ variables set"
    machine = os.uname().machine
    return None if machine == "arm64" else f"not arm64: {machine}"


def _app_note(name: str) -> int | None:
    lower = name.lower()
    return next((index for index, prefix in enumerate(APP_NOTES) if lower.startswith(prefix)), None)


def _apps_line(applications) -> str:
    """Names at level 0 of the application folders that start with a name of the contract's list, in its order
    (v2.1 F9; v2.3 r3 F48; v2.4 r4 F48)."""
    names: list[str] = []
    unreadable: list[str] = []
    for folder in applications:
        folder = Path(folder)
        if _kind(folder) == "missing":
            continue
        try:
            with os.scandir(folder) as listing:
                names += [entry.name for entry in listing if _app_note(entry.name) is not None]
        except OSError:
            unreadable.append(str(folder))
    shown = sorted(set(names), key=lambda name: (_app_note(name), name.lower()))
    if unreadable:
        return f"unreadable ({', '.join(unreadable)})" + (f"; found: {', '.join(shown)}" if shown else "")
    return ", ".join(shown) or "none"


def _present(path) -> bool | None:
    """Whether a path exists (lstat only, never listed), or None when that cannot be told."""
    try:
        os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except (OSError, ValueError):
        return None
    return True


def _tools_line(home) -> str:
    """Which names of the contract's list exist under home, by existence only (v2.2 r2 F9, v2.4 r4 F49)."""
    shown: list[str] = []
    for name in TOOL_NOTES:
        present = _present(Path(home).joinpath(*name.split("/")))
        if present is None:
            shown.append(f"{name} (unreadable)")
        elif present:
            shown.append(name)
    return ", ".join(shown) or "none"


def _mounts_line(entries, outside, root) -> str:
    """<n> (<types in the order found>)[; not allowed: <points>][; root: <problem>] (v2.1 F7; r2 F15, F32)."""
    kinds = ", ".join(dict.fromkeys(str(entry[0]) for entry in entries))
    text = f"{len(entries)} ({kinds})"
    if outside:
        text += f"; not allowed: {', '.join(outside)}"
    return text + (f"; root: {root}" if root is not None else "")


def _skipped_line(skipped, home) -> str:
    if not skipped:
        return "0 folders"
    return f"{len(skipped)} folders ({', '.join(_tilde(path, home) for path in skipped)})"


def _mt5_spec() -> bool | None:
    try:
        return importlib.util.find_spec("MetaTrader5") is not None
    except (ValueError, ImportError):
        return None


def _collect_darwin(roots: ResearchRoots) -> Facts:
    """The darwin reader: the seven Facts of contract v2.1 F4, plus the darwin keys of _HOST_SUMMARY (processes,
    mounts, wine, skipped, apps, tools; v2.4 r4 F55). The DYLD_* and arm64 checks come before any process or
    mount reader; what a rule found stays found when another part cannot be read (v2.2 r2 F30)."""
    summary: dict[str, str] = {}
    home = Path(roots.user_profile)
    try:  # terminal_data: names at level 0 of Application Support only, never entered (v2.1 F8)
        with os.scandir(roots.appdata) as listing:
            matched = tuple(Path(entry.path) for entry in listing if _appdata_match(entry.name))
        metaquotes: bool | None = bool(matched)
    except OSError:
        matched, metaquotes = (), None
    try:  # v2.3 r3 F25: the prefixes again, so roots built by hand are searched as well
        prefixes, sources, wine_roots = wine_prefixes(home)
        looked = ", ".join(_tilde(path, home) for path in sources) or "none"
        summary["wine"] = f"{len(prefixes)} prefixes; looked at {looked}"
        wine_read = True
    except OSError as error:  # v2.4 r4 F52: the search is incomplete, what is found elsewhere still counts
        wine_roots, wine_read = (), False
        summary["wine"] = f"unreadable ({_wine_reason(error, home)})"
    applications = _darwin_application_dirs(home)
    program_files = _unique((*roots.program_files, *wine_roots))
    found, complete, skipped = find_terminal_paths_darwin(applications, program_files, home,
                                                          (home / "Library", home / ".ssh", *matched))
    summary["skipped"] = _skipped_line(skipped, home)
    summary["apps"] = _apps_line(applications)
    summary["tools"] = _tools_line(home)
    paths = list(found)
    complete = complete and wine_read
    process_names = remote = connected = None
    reason = _darwin_guard()
    if reason is not None:
        summary["processes"] = summary["mounts"] = f"unreadable ({reason})"
    else:
        try:
            read, listed, passed = read_process_paths(os.getpid(), os.path.realpath(sys.executable))
        except OSError as error:
            summary["processes"] = f"unreadable ({error})"
        else:
            running, process_names, loaders = classify_processes(read)
            paths += running
            summary["processes"] = f"{listed} listed, {len(read)} paths read, {passed} skipped, {loaders} wine loaders"
        try:
            entries = read_mounts()
        except OSError as error:
            summary["mounts"] = f"unreadable ({error})"
        else:
            remote, connected, outside, root = classify_mounts(entries)
            summary["mounts"] = _mounts_line(entries, outside, root)
    _HOST_SUMMARY.update(summary)
    unique = sorted({_norm(path): path for path in paths}.values())
    return Facts(terminal_paths=tuple(unique) if unique or complete else None, uninstall_display_names=(),
                 process_names=process_names, metaquotes_exists=metaquotes, mt5_spec_found=_mt5_spec(),
                 remote_drives=remote, connected_resources=connected)


def collect(roots: ResearchRoots) -> Facts:
    """Every fact from the OS with the reader of sys.platform, read when called (contract v2.0, v2.1 F1, F22).
    A fact that cannot be read is None (UNKNOWN); a platform other than win32 and darwin reads nothing but
    find_spec, so terminal_install, terminal_data and network_shares are never PASS there."""
    platform = sys.platform
    if platform == "win32":
        return _collect_win32(roots)
    if platform == "darwin":
        return _collect_darwin(roots)
    return Facts(terminal_paths=None, uninstall_display_names=None, process_names=None, metaquotes_exists=None,
                 mt5_spec_found=_mt5_spec(), remote_drives=None, connected_resources=None)


def _unique(paths) -> tuple[Path, ...]:
    seen: dict[str, Path] = {}
    for path in paths:
        seen.setdefault(_norm(path), Path(path))
    return tuple(seen.values())


_WINE_FIXED = (("Library", "PlayOnMac", "wineprefix"), ("Library", "PlayOnMac"),
               ("Library", "Application Support", "CrossOver", "Bottles"), ("Library", "Application Support", "CrossOver"),
               (".wine",))


def _wine_fixed(error: OSError, home) -> str:
    """The deepest fixed folder of the Wine chain, from ~/, that holds the path of error, with the kind of failure.
    Never an entry name or the full path: those could hold the sentinel token or the account name (r3 F18)."""
    kind = "symlink" if error.strerror == "symlink" else f"errno {error.errno}"
    text = os.path.abspath(os.fsdecode(error.filename)).lower() if error.filename else ""
    for parts in _WINE_FIXED:
        if text and _within(text, os.path.abspath(Path(home).joinpath(*parts)).lower()):
            return f"~/{'/'.join(parts)} ({kind})"
    return f"a folder of the Wine chain ({kind})"


def _darwin_roots(repo: Path, data_dirs: tuple[Path, ...]) -> ResearchRoots:
    """default_roots on darwin (v2.0; v2.1 F9-F11): everything from the home of _darwin_home(), never from the
    Windows variables. A Wine folder or ~/Library/CloudStorage that exists but cannot be read raises OSError whose
    text names only the fixed folder from ~/, never an entry name or the full path (work review r3 F18)."""
    home = Path(_darwin_home())
    library = home / "Library"
    try:
        program_files = find_wine_program_files(home)
    except OSError as error:
        raise OSError(f"a Wine folder cannot be read: {_wine_fixed(error, home)}") from None
    search = [home / "Downloads", home / "Desktop", home / "Documents"]
    icloud = library / "Mobile Documents" / "com~apple~CloudDocs"
    if _kind(icloud) != "missing":
        search.append(icloud)
    storage = library / "CloudStorage"
    if _kind(storage) != "missing":
        try:
            with os.scandir(storage) as listing:
                found = sorted((Path(entry.path) for entry in listing if entry.is_dir()), key=lambda path: path.name)
        except OSError as error:
            raise OSError(f"~/Library/CloudStorage cannot be listed (errno {error.errno})") from None
        search += found
    return ResearchRoots(repo=repo, data_dirs=data_dirs, program_files=program_files,
                         appdata=library / "Application Support", user_profile=home, search_dirs=_unique(search))


def default_roots(extra_data_dirs=()) -> ResearchRoots:
    """This machine's roots (contract v1.6 Q9): data_dirs = (<repo>/data, *extra_data_dirs); on darwin they
    come from the home folder (v2.0), elsewhere as in v1.9."""
    repo = Path(__file__).resolve().parents[3]
    if sys.platform == "darwin":
        return _darwin_roots(repo, (repo / "data", *(Path(item) for item in extra_data_dirs)))
    env = os.environ
    profile = Path(env.get("USERPROFILE") or os.path.expanduser("~"))
    appdata = Path(env.get("APPDATA") or profile / "AppData" / "Roaming")
    program_files = _unique(Path(env[name]) for name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")
                            if env.get(name))
    shell = []
    for name in FOLDER_IDS:
        if sys.platform != "win32":
            shell.append(profile / name)
            continue
        try:  # v1.9 F5: on Windows a failed shell-folder call stops the check, never guesses the folder
            folder = _known_folder(name)
        except (OSError, ValueError, AttributeError) as error:
            raise OSError(f"the {name} shell folder could not be read ({type(error).__name__})") from error
        if folder is None:
            raise OSError(f"the {name} shell folder could not be read")
        shell.append(folder)
    onedrive = [Path(env[name]) for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial") if env.get(name)]
    return ResearchRoots(repo=repo, data_dirs=(repo / "data", *(Path(item) for item in extra_data_dirs)),
                         program_files=program_files, appdata=appdata, user_profile=profile,
                         search_dirs=_unique([*shell, *onedrive]))


# ---- entry points --------------------------------------------------------------------------------------
def research_host_report(*, roots: ResearchRoots | None = None, sentinel: Sentinel | None = None) -> Report:
    """evaluate(collect(roots), roots, sentinel). Every call first clears _HOST_SUMMARY and records the reader,
    the token and the roots it uses, for host_lines() (contract v2.3 r3 F25, v2.4 r4 F55)."""
    _HOST_SUMMARY.clear()
    _HOST_SUMMARY["reader"] = reader_name()
    if sentinel is not None and sentinel.token:
        _HOST_SUMMARY["token"] = sentinel.token
    roots = default_roots(()) if roots is None else roots
    _HOST_SUMMARY["roots"] = roots
    return evaluate(collect(roots), roots, sentinel)


def _roots_line(roots: ResearchRoots, darwin: bool) -> str:
    """roots: repo=… home=… search_dirs=…; on darwin the level-0 folders of ~/Library/CloudStorage print as a count
    and the part of their names before the first '-' only (v2.1 F11, v2.2 r2 F41)."""
    search = [Path(folder) for folder in roots.search_dirs]
    head = f"roots: repo={roots.repo} home={roots.user_profile} search_dirs="
    if not darwin:
        return head + ", ".join(map(str, search))
    storage = _norm(Path(roots.user_profile) / "Library" / "CloudStorage")
    cloud = [folder for folder in search if os.path.dirname(_norm(folder)) == storage]
    plain = [folder for folder in search if folder not in cloud]
    providers = ", ".join(folder.name.split("-", 1)[0] for folder in cloud)
    return head + ", ".join(map(str, plain)) + f"; cloud storage: {len(cloud)}" + (f" ({providers})" if cloud else "")


def host_lines() -> tuple[str, ...]:
    """The host lines of the last research_host_report (contract v2.1 F1 to v2.5 r5 F59); reads no OS state and
    never raises. The darwin lines follow the keys collect wrote; `not read` is printed only when the recorded
    reader is darwin. The sentinel token prints as <token>."""
    summary = _HOST_SUMMARY
    recorded = summary.get("reader")
    lines = [f"reader: {recorded or reader_name()}"]
    roots = summary.get("roots")
    if roots is not None:
        try:
            lines.append(_roots_line(roots, recorded == "darwin"))
        except (AttributeError, TypeError, ValueError):
            lines.append("roots: unreadable")
    for key in ("processes", "mounts", "wine"):
        if key in summary:
            lines.append(f"{key}: {summary[key]}")
        elif recorded == "darwin":
            lines.append(f"{key}: not read")
    lines += [f"{key}: {summary[key]}" for key in ("skipped", "apps", "tools") if key in summary]
    token = summary.get("token")
    if isinstance(token, str) and token:
        lines = [line.replace(token, "<token>") for line in lines]
    return tuple(lines)


def require_research_host(*, roots: ResearchRoots | None = None, sentinel: Sentinel | None = None) -> Report:
    """The gate R1 calls before every run: the PASS report, or ResearchHostError naming each other item.
    A check that cannot run at all (the roots cannot be read) is a ResearchHostError too (v1.9 F5). The message
    never holds the sentinel token (v1.7 F7), and the cause is not chained, so a traceback cannot show it either
    (work review r3 F18)."""
    try:
        report = research_host_report(roots=roots, sentinel=sentinel)
    except OSError as error:
        text = f"research host check could not run: {error}"
        if sentinel is not None and sentinel.token:
            text = text.replace(sentinel.token, "<token>")
        raise ResearchHostError(text) from None
    if report.verdict != PASS:
        others = ", ".join(f"{item.name} {item.status}" for item in report.items if item.status != PASS)
        raise ResearchHostError(f"research host check is {report.verdict}: {others}")
    return report


def load_sentinel(path, appdata=None) -> tuple[Sentinel | None, str | None]:
    """(Sentinel, None) from the committed values file, or (None, why); the token is never echoed.
    A file the read rules never open is not opened here either (r2 F15)."""
    path = Path(os.path.abspath(path))
    lower = path.name.lower()
    if lower == ".env" or lower.startswith(".env.") or os.path.splitext(lower)[1] in CLOSED_SUFFIXES:
        return None, f"the sentinel file {path} has a name that is never opened"
    if _below_terminal(path):
        return None, f"the sentinel file {path} is below a folder with terminal64.exe and is never opened"
    if appdata is not None and _within(_norm(path), _norm(Path(appdata) / "MetaQuotes")):
        return None, f"the sentinel file {path} is under %APPDATA%\\MetaQuotes and is never opened"
    if appdata is not None and _appdata_folder(path, appdata) is not None:  # v2.2 r2 F28
        return None, f"the sentinel file {path} is under a terminal data folder of {appdata} and is never opened"
    try:
        if is_cloud_only(path):
            return None, f"the sentinel file {path} is cloud-only and was not opened"
        values = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as error:
        return None, f"the sentinel file {path} could not be read ({type(error).__name__})"
    if not isinstance(values, dict) or set(values) != set(SENTINEL_KEYS):
        return None, f"the sentinel file {path} does not hold exactly {', '.join(SENTINEL_KEYS)}"
    texts = [key for key in SENTINEL_KEYS if key != "size" and not isinstance(values[key], str)]
    if texts or type(values["size"]) is not int or values["size"] <= 0:
        return None, f"the sentinel file {path} has values of the wrong type"
    if not HEX32.fullmatch(values["token"]) or not HEX64.fullmatch(values["sha256"]):
        return None, f"the sentinel file {path} has a malformed token or sha256"
    # v1.9 F7: values that would switch a rule off are refused
    if values["name"] != f"SENTINEL-ENV002-{values['token'][:8]}.json":
        return None, f"the sentinel file {path} names another file than its token's sentinel"
    vault = values["vault_path"]
    if not (os.path.isabs(vault) or WINDOWS_ABSOLUTE.fullmatch(vault)):
        return None, f"the sentinel file {path} has no absolute vault_path"
    if not TIME_PATTERN.fullmatch(values["created_utc"]):
        return None, f"the sentinel file {path} has a created_utc that is not {TIME_FORMAT}"
    return Sentinel(**values), None


def render(report: Report, note: str | None = None) -> str:
    lines = ["# ENV-002 research host check", ""]
    lines += [f"{item.name}: {item.status} - {item.detail}" for item in report.items]
    if note:
        lines += ["", f"note: {note}"]
    lines += ["", f"RESEARCH HOST: {report.verdict}"]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sochron.app.envcheck",
                                     description="ENV-002 research host check (read-only)")
    parser.add_argument("--role", required=True, choices=(ROLE,))
    parser.add_argument("--sentinel-file", type=Path, default=None)
    parser.add_argument("--data-dir", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    sentinel: Sentinel | None
    note: str | None
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        roots = default_roots(tuple(args.data_dir))
        if args.sentinel_file is None:
            sentinel, note = None, "no --sentinel-file given"
        else:
            sentinel, note = load_sentinel(args.sentinel_file, appdata=roots.appdata)
        report = research_host_report(roots=roots, sentinel=sentinel)
    except OSError as error:  # v1.9 F5: the check could not run; never a traceback or a PASS
        print(f"reader: {reader_name()}")  # v2.5 r5 F59: nothing from _HOST_SUMMARY, so no roots: line
        print(f"# ENV-002 research host check\n\nnote: the check could not run: {error}\n\nRESEARCH HOST: {UNKNOWN}")
        return 1
    for line in host_lines():  # v2.1 F1: the host lines come before the report
        print(line)
    print(render(report, note), end="")
    return 0 if report.verdict == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
