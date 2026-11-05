"""ENV-002 research-host check (docs/contracts/ENV-002-research-host-separation.md, v1.8).

The owner's PC is the research host: it must hold no MT5 terminal, no MetaTrader5 package, no data of
the excluded period, no share to the VPS and no copy of the synthetic sentinel made on the VPS.
collect(roots) reads the OS (Windows-only calls stay inside functions, so the module imports on Linux);
evaluate(facts, roots, sentinel) judges the facts and searches the repository, the data dirs and the
shell folders by the contract's read rules. Nothing is written, deleted, run or sent over a network.

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
CHUNK = 1 << 20
SHOWN = 3  # paths shown per finding kind in a detail

UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
WOW_UNINSTALL = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
DRIVE_REMOTE = 4
TH32CS_SNAPPROCESS = 0x2
RESOURCE_CONNECTED = 0x1
RESOURCETYPE_ANY = 0x0
NO_ERROR, ERROR_MORE_DATA, ERROR_NO_MORE_ITEMS, ERROR_NO_NETWORK = 0, 234, 259, 1222
FOLDER_IDS = {  # KNOWNFOLDERID values
    "Downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "Desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
}


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


def is_cloud_only(path) -> bool:
    """A OneDrive Files On-Demand placeholder: opening it would download the file (os.stat only)."""
    return bool(getattr(os.stat(path), "st_file_attributes", 0) & RECALL_ATTRIBUTES)


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
    except (UnicodeDecodeError, ValueError):
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

    def __init__(self, roots: ResearchRoots, sentinel: Sentinel | None):
        self.sentinel = sentinel
        self.patterns = _token_patterns(sentinel.token) if sentinel is not None else ()
        self.repo = Path(roots.repo)
        self.default_data = _norm(self.repo / "data")
        self.metaquotes = _norm(Path(roots.appdata) / "MetaQuotes")
        self.excused = _norm(self.repo.joinpath(*EXCUSED))
        self.holdout: tuple[list[str], list[str]] = ([], [])
        self.excluded: tuple[list[str], list[str]] = ([], [])
        self.found: tuple[list[str], list[str]] = ([], [])
        self.manifests: dict[str, object] = {}
        self.plan = self._plan(roots)
        self.prune = {key for _, key, _ in self.plan} | {self.metaquotes}

    # -- what is walked, and under which rules
    def _plan(self, roots: ResearchRoots) -> list[tuple[Path, str, str]]:
        plan: list[tuple[Path, str, str]] = []
        repo_key = _norm(self.repo)
        if self.repo.is_dir():
            plan.append((self.repo, repo_key, "repo"))
        else:
            self._unlisted("repo", self.repo, "the repository folder was not found")
        data: list[tuple[Path, str]] = []
        for folder in roots.data_dirs:
            folder, key = Path(folder), _norm(folder)
            if _within(key, self.metaquotes):
                self._unlisted("data", folder, "is under %APPDATA%\\MetaQuotes, which is never listed")
            elif folder.is_dir():
                data.append((folder, key))
            elif key != self.default_data:  # v1.6 Q5: a missing <repo>/data has nothing to check
                self.excluded[1].append(f"data dir {folder} does not exist")
        kept: list[tuple[Path, str, str]] = []
        for folder, key in data:
            inside = any(key != other and _within(key, other) for _, other in data)
            if not inside and all(key != other for _, other, _ in kept):
                kept.append((folder, key, "data"))
        plan += kept
        # A search dir under the repository or a data dir follows their rules (contract v1.5), so it is
        # walked with them; one under another search dir is walked with that one.
        covered = [key for _, key, _ in plan]
        candidates = [(Path(folder), _norm(folder)) for folder in roots.search_dirs]
        candidates = [(folder, key) for folder, key in candidates
                      if folder.is_dir() and not any(_within(key, other) for other in covered)]
        searched: list[tuple[Path, str, str]] = []
        for folder, key in candidates:
            nested = any(key != other and _within(key, other) for _, other in candidates)
            if not nested and all(key != other for _, other, _ in searched):
                searched.append((folder, key, "search"))
        return plan + searched

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
        if sentinel is not None and sentinel.vault_path and os.path.exists(sentinel.vault_path):
            self.found[0].append("the VPS vault path exists on this machine")
        for root, _, area in self.plan:
            if area == "search" and sentinel is None:
                continue  # only the sentinel rules read the search dirs
            for folder, files, folders, beside in self._walk(root, area):
                self._visit(area, folder, files, folders, beside)

    def _walk(self, root: Path, area: str):
        stack = [(root, False)]
        while stack:
            folder, beside = stack.pop()
            try:
                with os.scandir(folder) as listing:
                    entries = list(listing)
            except OSError:
                self._unlisted(area, folder)
                continue
            files, folders = [], []
            for entry in entries:
                try:
                    if entry.is_junction() or entry.is_symlink():
                        continue  # v1.7 F8: reparse points are not entered
                    if entry.is_dir(follow_symlinks=False):
                        folders.append(entry)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry)
                except OSError:
                    self._unlisted(area, Path(entry.path))
            here = beside or any(entry.name.lower() == TERMINAL for entry in files)
            yield folder, files, folders, here
            for entry in folders:
                if _norm(entry.path) not in self.prune:
                    stack.append((Path(entry.path), here))

    def _visit(self, area: str, folder: Path, files: list, folders: list, beside: bool) -> None:
        if area != "search":
            for entry in folders:
                if entry.name.lower() == "holdout":
                    self.holdout[0].append(f"{entry.path} is a holdout folder")
        by_name = {entry.name.lower(): entry for entry in files}
        for entry in files:
            self._file(area, entry, beside, by_name)

    # -- one file
    def _file(self, area: str, entry, beside: bool, by_name: dict) -> None:
        lower = entry.name.lower()
        suffix = os.path.splitext(lower)[1]
        path = Path(entry.path)
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
        elif suffix in TEXT_SUFFIXES and _norm(path) != self.excused:
            size = self._size(entry)
            if size is None:
                self.found[1].append(f"{path} could not be read")
            else:
                self._compare(path, closed, size, token=True)

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
        path = Path(entry.path)
        manifest = by_name.get(f"{entry.name}.manifest.json".lower()) or by_name.get("manifest.json")
        if manifest is None:
            self.excluded[0].append(f"{path} has no manifest")
            return
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
                self.excluded[0].append(f"{path} ends {period_end.strftime(TIME_FORMAT)}, after the cutoff")

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
        cutoff = HOLDOUT_CUTOFF_UTC.strftime(TIME_FORMAT)
        holdout = Item("holdout_dir", *_status(*self.holdout, "no holdout folder in the repository or the data dirs"))
        excluded = Item("excluded_period", *_status(
            *self.excluded, f"every data file has a manifest that ends by {cutoff}; no MT5 cache in the repository"))
        if self.sentinel is None:
            sentinel = Item("sentinel", UNKNOWN, "no sentinel given (--sentinel-file)")
        else:
            sentinel = Item("sentinel", *_status(*self.found, "no copy, name, token or vault path of the sentinel found"))
        return holdout, excluded, sentinel


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
    search = _Search(roots, sentinel)
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
    """The plain subfolders and the file names of a folder; reparse points are not entered."""
    with os.scandir(folder) as listing:
        entries = list(listing)
    folders, names = [], []
    for entry in entries:
        if entry.is_junction() or entry.is_symlink():
            continue
        if entry.is_dir(follow_symlinks=False):
            folders.append(entry)
        else:
            names.append(entry.name)
    return folders, names


def _find_terminal64(root: Path, levels: int, skip: tuple[str, ...], prune: set[str]) -> list[str]:
    """terminal64.exe at levels 0..levels below root; folders that refuse listing are skipped (v1.8)."""
    found, stack = [], [(root, 0)]
    while stack:
        folder, level = stack.pop()
        try:
            folders, names = _list_folders(folder)
        except OSError:
            continue
        found += [str(folder / name) for name in names if name.lower() == TERMINAL]
        if level < levels:
            stack += [(Path(entry.path), level + 1) for entry in folders
                      if entry.name.lower() not in skip and _norm(entry.path) not in prune]
    return found


def find_terminal_paths(program_files, user_profile, appdata) -> tuple[str, ...]:
    """The three path rules of terminal_install (contract v1.6 Q2/Q3, v1.8); pure apart from listing folders.

    Program Files*\\MetaTrader* folders, terminal64.exe at levels 0-2 of each Program Files* folder, and
    terminal64.exe at levels 0-3 of the user profile outside .git, .venv, node_modules and
    %APPDATA%\\MetaQuotes (never listed). Names compare without case."""
    found: list[str] = []
    for root in (Path(item) for item in program_files):
        if not root.is_dir():
            continue
        try:
            folders, _ = _list_folders(root)
        except OSError:
            continue
        found += [entry.path for entry in folders if entry.name.lower().startswith("metatrader")]
        found += _find_terminal64(root, PROGRAM_FILES_LEVELS, (), set())
    profile = Path(user_profile)
    if profile.is_dir():
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
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            names.append(entry.szExeFile)
            more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
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


def collect(roots: ResearchRoots) -> Facts:
    """Read every fact from the OS; a fact that cannot be read is None (UNKNOWN)."""
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


def _unique(paths) -> tuple[Path, ...]:
    seen: dict[str, Path] = {}
    for path in paths:
        seen.setdefault(_norm(path), Path(path))
    return tuple(seen.values())


def default_roots(extra_data_dirs=()) -> ResearchRoots:
    """This machine's roots (contract v1.6 Q9): data_dirs = (<repo>/data, *extra_data_dirs)."""
    repo = Path(__file__).resolve().parents[3]
    env = os.environ
    profile = Path(env.get("USERPROFILE") or os.path.expanduser("~"))
    appdata = Path(env.get("APPDATA") or profile / "AppData" / "Roaming")
    program_files = _unique(Path(env[name]) for name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")
                            if env.get(name))
    shell = []
    for name in FOLDER_IDS:
        folder = None
        if sys.platform == "win32":
            try:
                folder = _known_folder(name)
            except (OSError, ValueError, AttributeError):
                folder = None
        shell.append(folder or profile / name)
    onedrive = [Path(env[name]) for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial") if env.get(name)]
    return ResearchRoots(repo=repo, data_dirs=(repo / "data", *(Path(item) for item in extra_data_dirs)),
                         program_files=program_files, appdata=appdata, user_profile=profile,
                         search_dirs=_unique([*shell, *onedrive]))


# ---- entry points --------------------------------------------------------------------------------------
def research_host_report(*, roots: ResearchRoots | None = None, sentinel: Sentinel | None = None) -> Report:
    roots = default_roots(()) if roots is None else roots
    return evaluate(collect(roots), roots, sentinel)


def require_research_host(*, roots: ResearchRoots | None = None, sentinel: Sentinel | None = None) -> Report:
    """The gate R1 calls before every run: the PASS report, or ResearchHostError naming each other item."""
    report = research_host_report(roots=roots, sentinel=sentinel)
    if report.verdict != PASS:
        others = ", ".join(f"{item.name} {item.status}" for item in report.items if item.status != PASS)
        raise ResearchHostError(f"research host check is {report.verdict}: {others}")
    return report


def load_sentinel(path) -> tuple[Sentinel | None, str | None]:
    """(Sentinel, None) from the committed values file, or (None, why); the token is never echoed."""
    path = Path(path)
    try:
        if is_cloud_only(path):
            return None, f"the sentinel file {path} is cloud-only and was not opened"
        values = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return None, f"the sentinel file {path} could not be read ({type(error).__name__})"
    if not isinstance(values, dict) or set(values) != set(SENTINEL_KEYS):
        return None, f"the sentinel file {path} does not hold exactly {', '.join(SENTINEL_KEYS)}"
    texts = [key for key in SENTINEL_KEYS if key != "size" and not isinstance(values[key], str)]
    if texts or type(values["size"]) is not int or values["size"] <= 0:
        return None, f"the sentinel file {path} has values of the wrong type"
    if not HEX32.fullmatch(values["token"]) or not HEX64.fullmatch(values["sha256"]):
        return None, f"the sentinel file {path} has a malformed token or sha256"
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
    if args.sentinel_file is None:
        sentinel, note = None, "no --sentinel-file given"
    else:
        sentinel, note = load_sentinel(args.sentinel_file)
    report = research_host_report(roots=default_roots(tuple(args.data_dir)), sentinel=sentinel)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    print(render(report, note), end="")
    return 0 if report.verdict == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
