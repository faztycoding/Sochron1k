"""ENV-001 host report: a read-only check of the acquisition/execution VPS.

Contract: docs/contracts/ENV-001-vps-acquisition-host.md (v1.6). Standard library only.
collect_facts reads the Windows facts; every Windows-only module is imported inside it, so the
module also imports on Linux, where evaluate and render (both pure) are tested.

Run on the VPS from the repository root (a normal PowerShell window):
  uv run --no-sync --offline python scripts/env/host_report.py --role acquisition --repo .
Exit 0 only when the verdict is PASS. The report never prints an IP address: a remote scope is
shown as its number of entries and prefix lengths only.
"""

import argparse
import base64
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

# ---- constants (contract) --------------------------------------------------------------------
# EXPECTED_UV is replaced with the uv version installed on the VPS at ENV-001 step (5), together
# with its row in docs/tooling/registry.md. Until then python_env fails on purpose.
EXPECTED_UV = "set-at-step-5"
EXPECTED_PYTHON = "3.12.15"
# Windows `Name` of the default Core Networking rules (not DisplayName, which follows the UI
# language). Observed on Windows 11 build 26200 on 2026-10-25; confirmed on the VPS in the runbook.
ALLOWED_UDP = {68: "CoreNet-DHCP-In", 546: "CoreNet-DHCPV6-In"}
IGNORED_PROTOCOLS = frozenset({"ICMPv4", "ICMPv6", "2", "41"})  # as Get-NetFirewallPortFilter returns them
MIN_IPV4_PREFIX = 24
MIN_IPV6_PREFIX = 48
# Contract v1.6 (review r1 F10): IPv6 forms that carry IPv4 (mapped, compatible, NAT64) must be at
# least as narrow as an IPv4 /24, i.e. /120.
IPV4_IN_IPV6_BLOCKS = tuple(ipaddress.ip_network(n) for n in ("::ffff:0:0/96", "::/96", "64:ff9b::/96"))
MIN_IPV4_IN_IPV6_PREFIX = 120
# A drive path or a UNC path is masked to the end of the Name: Query User Names end with the
# program path, and a path can hold spaces (review r2 F20).
WINDOWS_PATH = re.compile(r"(?:[A-Za-z]:\\|\\\\)[\s\S]*")
IPV4_LOOKALIKE = re.compile(r"\b([0-9]{1,3}\.){3}[0-9]{1,3}\b")
IPV6_LOOKALIKE = re.compile(r"\b[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{0,4}){2,7}")

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
RDP_PORT = "3389"
MAX_SCOPE_ENTRIES = 4
PROFILE_NAMES = ("Domain", "Private", "Public")
SERVER_CAPTIONS = ("Windows Server 2022", "Windows Server 2025")
SERVER_BUILDS = frozenset({20348, 26100})
MIN_CPUS = 2
MIN_RAM_BYTES = 3_758_096_384  # 3.5 GiB
MIN_DISK_BYTES = 30 * 10**9
LOCKOUT_RANGE = range(1, 11)
SKIP_DIRS = frozenset({".git", ".venv"})
SECRET_SUFFIXES = (".key", ".pem", ".pfx", ".rdp")

POLICY_KEY = r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
WINSTATION_KEY = r"SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp"
UNINSTALL_KEYS = (
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
)
SYNC_DISPLAY_NAMES = ("OneDrive", "Dropbox", "Google Drive", "iCloud")
SYNC_PROCESSES = {
    "onedrive.exe": "OneDrive",
    "dropbox.exe": "Dropbox",
    "googledrivefs.exe": "Google Drive",
    "iclouddrive.exe": "iCloud",
    "icloudservices.exe": "iCloud",
}

# The one PowerShell command behind inbound_allow_rules and firewall_profiles. ActiveStore is the
# effective set (Group Policy included). Enums go through .ToString() and lists through @(),
# because Windows PowerShell 5.1 writes enums as numbers and -Depth 2 flattens deep arrays.
# Piping the rules into the filter cmdlets works without elevation (listing every filter does not).
FIREWALL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rs = @(Get-NetFirewallRule -PolicyStore ActiveStore -Direction Inbound -Action Allow -Enabled True)
if (@($rs | Group-Object InstanceID | Where-Object Count -gt 1).Count) { throw 'duplicate rule InstanceID' }
$ports = @{}
foreach ($f in @($rs | Get-NetFirewallPortFilter)) { $ports[$f.InstanceID] = $f }
$addresses = @{}
foreach ($f in @($rs | Get-NetFirewallAddressFilter)) { $addresses[$f.InstanceID] = $f }
$rules = New-Object System.Collections.ArrayList
foreach ($r in $rs) {
  $p = $ports[$r.InstanceID]
  $a = $addresses[$r.InstanceID]
  [void]$rules.Add([ordered]@{
    name = [string]$r.Name
    protocol = [string]$p.Protocol
    profiles = $r.Profile.ToString()
    local_ports = [string[]]@($p.LocalPort | ForEach-Object { [string]$_ })
    remote_addresses = [string[]]@($a.RemoteAddress | ForEach-Object { [string]$_ })
  })
}
$profiles = New-Object System.Collections.ArrayList
foreach ($x in Get-NetFirewallProfile -PolicyStore ActiveStore) {
  [void]$profiles.Add([ordered]@{
    name = [string]$x.Name
    enabled = $x.Enabled.ToString()
    default_inbound_action = $x.DefaultInboundAction.ToString()
  })
}
ConvertTo-Json -InputObject ([ordered]@{ rules = $rules.ToArray(); profiles = $profiles.ToArray() }) -Depth 4 -Compress
"""


# ---- records -----------------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    name: str  # the rule's Windows `Name`
    protocol: str
    profiles: str
    local_ports: tuple[str, ...]
    remote_addresses: tuple[str, ...]


@dataclass(frozen=True)
class Profile:
    name: str
    enabled: str
    default_inbound_action: str


@dataclass(frozen=True)
class Facts:
    os_caption: str | None
    os_build: int | None
    cpu_count: int | None
    visible_ram_bytes: int | None
    repo_drive_free_bytes: int | None
    inbound_allow_rules: tuple[Rule, ...] | None
    firewall_profiles: tuple[Profile, ...] | None
    nla_required: bool | None
    lockout_threshold: int | None
    drive_redirection_disabled: bool | None
    clipboard_files_to_client_blocked: bool | None
    sync_clients: tuple[str, ...] | None
    uv_version: str | None
    python_version: str | None
    project_synced: bool | None
    git_credential_helpers: tuple[str, ...] | None
    remote_has_userinfo: bool | None
    secret_like_files_in_repo: int | None
    holdout_dir_in_repo: bool | None


@dataclass(frozen=True)
class Item:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class Report:
    items: tuple[Item, ...]
    verdict: str


# ---- pure helpers (unit-tested) -----------------------------------------------------------------
def policy_first(policy: int | None, winstation: int | None) -> bool | None:
    """A Group Policy value decides when present; otherwise the RDP-Tcp value; 1 means on."""
    if policy is not None:
        return policy == 1
    if winstation is not None:
        return winstation == 1
    return None


def clipboard_blocks_files(disable_clip: bool | None, server_to_client_level: int | None) -> bool | None:
    """True when the server cannot send files to the client.

    disable_clip is policy_first(fDisableClip). The policy "Restrict clipboard transfer from server
    to client" (HKLM ...\\Terminal Services\\SCClipLevel) is mapped on its own: 0 disables the
    clipboard and 1 allows plain text only (True); 2-4 allow images and richer formats (False)."""
    if disable_clip is True:
        return True
    if server_to_client_level is not None:
        return server_to_client_level in (0, 1)
    return disable_clip


def parse_lockout(text: str) -> int | None:
    """`net accounts` output: the "Lockout threshold" line; "Never" is 0. Other UI languages: None."""
    for line in text.splitlines():
        label, _, value = line.partition(":")
        if label.strip().lower() == "lockout threshold":
            value = value.strip()
            if value.lower() == "never":
                return 0
            return int(value) if value.isdigit() else None
    return None


def parse_uv_version(text: str) -> str | None:
    parts = text.split()
    if len(parts) >= 2 and parts[0] == "uv" and parts[1][:1].isdigit():
        return parts[1]
    return None


NO_VALUE = "<no value>"  # a helper key written without "=" (review r2 F18 case C)
EXTRAHEADER = "<http extraheader>"  # one http.<url>.extraheader entry in git_credential_helpers (contract v1.7)


def effective_helpers(values: list[str]) -> tuple[str, ...]:
    """Git's rule: an empty credential.helper value clears the helpers listed before it."""
    helpers: list[str] = []
    for value in values:
        if value == "":
            helpers.clear()
        else:
            helpers.append(value)
    return tuple(helpers)


def config_entries(stdout: str, prefix: str, suffix: str) -> list[tuple[str, str | None]] | None:
    """`git config --show-origin -z --get-regexp <pattern>` as (key, value) pairs (contract v1.7).

    Each entry is <origin> NUL <key> LF <value> NUL, or <origin> NUL <key> NUL for a key written
    without "=" (value None). Values can hold line breaks but never NUL, so the split is exact
    (review r2 F18). Output that does not split into such pairs, or a key outside prefix...suffix,
    is None (UNKNOWN)."""
    parts = stdout.split("\0")
    if parts[-1] != "" or len(parts) % 2 == 0:
        return None
    entries: list[tuple[str, str | None]] = []
    for origin, item in zip(parts[0:-1:2], parts[1:-1:2]):
        key, sep, value = item.partition("\n")
        if not origin or not key.startswith(prefix) or not key.endswith(suffix):
            return None
        entries.append((key, value if sep else None))
    return entries


def parse_git_helpers(stdout: str) -> tuple[str, ...] | None:
    """`git config --show-origin -z --get-regexp "^credential\\..*helper$"` (contract v1.7).

    Keys are the plain credential.helper and URL-scoped credential.<url>.helper. The reset rule is
    applied per key (an empty value clears that key's earlier helpers), which never clears more than
    git does; every helper still in effect for any key is returned. Review r2 F18: only an exactly
    empty value is a reset (a space, a tab or a multi-line value is a helper to git), a key written
    without "=" counts as a helper, and keys are kept as printed (git lowercases the section and the
    variable name; the URL part is case-sensitive)."""
    entries = config_entries(stdout, "credential.", ".helper")
    if entries is None:
        return None
    per_key: dict[str, list[str]] = {}
    for key, value in entries:
        per_key.setdefault(key, []).append(NO_VALUE if value is None else value)
    return tuple(helper for values in per_key.values() for helper in effective_helpers(values))


def helpers_from_git(returncode: int | None, stdout: str) -> tuple[str, ...] | None:
    """`git config --get-regexp` exits 1 when no key matches; any other failure is unknown."""
    if returncode == 0:
        return parse_git_helpers(stdout)
    if returncode == 1 and not stdout.strip():
        return ()
    return None


def extraheaders_from_git(returncode: int | None, stdout: str) -> tuple[str, ...] | None:
    """`git config --show-origin -z --get-regexp "^http\\..*extraheader$"` (contract v1.7, review r2 F23 b).

    An extraheader can carry a token that git sends with every request, so every entry, empty ones
    included, is one EXTRAHEADER credential source; values are never kept."""
    if returncode == 0:
        entries = config_entries(stdout, "http.", ".extraheader")
        return None if entries is None else tuple(EXTRAHEADER for _ in entries)
    if returncode == 1 and not stdout.strip():
        return ()
    return None


def helper_kinds(helpers: tuple[str, ...]) -> str:
    """Names the helpers without printing their values (a value can hold a path or a token)."""
    known = ("manager", "store", "cache", "wincred", "osxkeychain", "libsecret")
    kinds = []
    for helper in helpers:
        word = helper.split()[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower() if helper.split() else ""
        kinds.append(next((k for k in known if word.startswith(k) or word == f"git-credential-{k}"), "other"))
    return ", ".join(kinds)


def url_has_userinfo(url: str) -> bool:
    if "://" in url:
        return "@" in urlsplit(url).netloc
    head = url.split(":", 1)[0]  # scp-like user@host:path
    return "@" in head


def url_is_safe(url: str) -> bool:
    """https:// without user information (contract v1.7, review r2 F23 a): ssh, scp-like, git, file,
    http and plain paths can push with a key or a helper that git finds outside the URL."""
    return url.lower().startswith("https://") and not url_has_userinfo(url)


def any_unsafe_url(urls: list[str]) -> bool:
    """URLs as `git remote get-url --all` and `--push --all` print them (insteadOf applied)."""
    return any(not url_is_safe(url.strip()) for url in urls if url.strip())


def synced_from_uv(returncode: int | None) -> bool | None:
    """`uv sync --locked --check --offline`: 0 in sync, any other exit not in sync, None not run."""
    return None if returncode is None else returncode == 0


def is_secret_like(name: str) -> bool:
    """Names only, never opened: .env and .env.* except .env.example, and key or RDP files."""
    lowered = name.lower()
    if lowered == ".env.example":
        return False
    return lowered == ".env" or lowered.startswith(".env.") or lowered.endswith(SECRET_SUFFIXES)


def _raise(error: OSError) -> None:
    raise error


def _walk_names(root: Path):
    """Every folder must be listable: a missing root or an unreadable folder raises (UNKNOWN)."""
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    for directory, subdirs, files in os.walk(root, onerror=_raise):
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]
        yield directory, subdirs, files


def count_secret_like(root: Path) -> int:
    return sum(1 for _, _, files in _walk_names(root) for name in files if is_secret_like(name))


def has_holdout_dir(root: Path) -> bool:
    return any(d.lower() == "holdout" for _, subdirs, _ in _walk_names(root) for d in subdirs)


def _as_str_tuple(value: object) -> tuple[str, ...] | None:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    return None


def _unwrap(value: object) -> object:
    """Windows PowerShell 5.1 can write an array as {"value": [...], "Count": n}."""
    if isinstance(value, dict) and set(value) == {"value", "Count"}:
        return value["value"]
    return value


def parse_firewall_json(text: str) -> tuple[tuple[Rule, ...] | None, tuple[Profile, ...] | None]:
    """The FIREWALL_SCRIPT output as Rule and Profile tuples; a set that cannot be read is None."""
    try:
        data = json.loads(text.lstrip("\ufeff"))
    except ValueError:
        return None, None
    if not isinstance(data, dict):
        return None, None
    return _parse_rules(_unwrap(data.get("rules"))), _parse_profiles(_unwrap(data.get("profiles")))


def _text(entry: dict, key: str) -> str | None:
    value = entry.get(key)
    return value if isinstance(value, str) else None


def _entries(raw: object) -> list[dict] | None:
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(entry, dict) for entry in raw):
        return None
    return raw


def _parse_rules(raw: object) -> tuple[Rule, ...] | None:
    entries = _entries(raw)
    if entries is None:
        return None
    rules = []
    for entry in entries:
        name, protocol, profiles = _text(entry, "name"), _text(entry, "protocol"), _text(entry, "profiles")
        ports = _as_str_tuple(_unwrap(entry.get("local_ports")))
        scope = _as_str_tuple(_unwrap(entry.get("remote_addresses")))
        if name is None or protocol is None or profiles is None or ports is None or scope is None:
            return None
        rules.append(Rule(name=name, protocol=protocol, profiles=profiles, local_ports=ports, remote_addresses=scope))
    return tuple(rules)


def _parse_profiles(raw: object) -> tuple[Profile, ...] | None:
    entries = _entries(raw)
    if entries is None:
        return None
    profiles = []
    for entry in entries:
        name, enabled, action = _text(entry, "name"), _text(entry, "enabled"), _text(entry, "default_inbound_action")
        if name is None or enabled is None or action is None:
            return None
        profiles.append(Profile(name=name, enabled=enabled, default_inbound_action=action))
    return tuple(profiles)


# ---- evaluate ------------------------------------------------------------------------------------
# Each one ends a PowerShell single-quoted literal (review r2 F22): the apostrophe and U+2018..U+201B.
SINGLE_QUOTES = ("'",) + tuple(chr(code) for code in (0x2018, 0x2019, 0x201A, 0x201B))


def _quote(name: str) -> str:
    """A PowerShell single-quoted literal: an unquoted {GUID} would be read as a script block.
    Every character PowerShell reads as a single quote is doubled."""
    for quote in SINGLE_QUOTES:
        name = name.replace(quote, quote * 2)
    return "'" + name + "'"


def _known_status(failures: list[str], unknown: bool, ok_detail: str) -> tuple[str, str]:
    """FAIL when a known value fails (it gives the owner something to fix), else UNKNOWN, else PASS."""
    if failures:
        return FAIL, "; ".join(failures)
    if unknown:
        return UNKNOWN, "could not be read"
    return PASS, ok_detail


def _os(f: Facts) -> tuple[str, str]:
    failures = []
    if f.os_caption is not None and not f.os_caption.startswith(SERVER_CAPTIONS):
        failures.append(f"'{f.os_caption}' is not Windows Server 2022 or 2025")
    if f.os_build is not None and f.os_build not in SERVER_BUILDS:
        failures.append(f"build {f.os_build} is not 20348 (2022) or 26100 (2025)")
    unknown = f.os_caption is None or f.os_build is None
    return _known_status(failures, unknown, f"{f.os_caption}, build {f.os_build}")


def _minimum(value: int | None, minimum: int, describe) -> tuple[str, str]:
    if value is None:
        return UNKNOWN, "could not be read"
    return (PASS if value >= minimum else FAIL), describe(value)


def _firewall(f: Facts) -> tuple[str, str]:
    if f.firewall_profiles is None:
        return UNKNOWN, "could not be read"
    failures = []
    names = [p.name for p in f.firewall_profiles]
    for name in PROFILE_NAMES:
        if names.count(name) != 1:
            failures.append(f"profile {name} appears {names.count(name)} times (must be once)")
    for profile in f.firewall_profiles:  # every entry is judged, duplicates and extras included
        if profile.name not in PROFILE_NAMES:
            failures.append(f"unexpected profile {profile.name}")
            continue
        if profile.enabled != "True":
            failures.append(f"{profile.name} enabled={profile.enabled} (must be True)")
        if profile.default_inbound_action not in ("Block", "NotConfigured"):
            failures.append(f"{profile.name} default inbound action {profile.default_inbound_action} (must be Block)")
    if failures:
        fix = "Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -DefaultInboundAction Block"
        return FAIL, "; ".join(failures) + f" -> {fix}"
    return PASS, "Domain, Private, Public enabled; inbound default Block"


def _scope_problems(scope: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """(problems, prefix labels) for a 3389 rule's remote scope; never echoes an address."""
    problems, prefixes = [], []
    if not 1 <= len(scope) <= MAX_SCOPE_ENTRIES:
        problems.append(f"scope has {len(scope)} entries (1-{MAX_SCOPE_ENTRIES} allowed)")
    for entry in scope:
        if entry.lower() == "any":
            problems.append("scope is Any")
            continue
        if "-" in entry:
            problems.append("scope has an address range")
            continue
        if not any(ch.isdigit() for ch in entry) and ":" not in entry:
            problems.append(f"scope has the keyword {entry}")
            continue
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            problems.append("scope has an entry that is not a host or prefix")
            continue
        limit = MIN_IPV4_PREFIX if network.version == 4 else MIN_IPV6_PREFIX
        prefixes.append(f"/{network.prefixlen}")
        if network.prefixlen < limit:
            problems.append(f"IPv{network.version} /{network.prefixlen} is wider than /{limit}")
        if "/" in entry and "." in entry.split("/", 1)[1] and not _is_netmask(entry.split("/", 1)[1]):
            problems.append("scope mask is not a netmask")  # a hostmask (contract v1.6)
        if network.version == 6 and network.prefixlen < MIN_IPV4_IN_IPV6_PREFIX and any(
                network.overlaps(block) for block in IPV4_IN_IPV6_BLOCKS):
            problems.append(f"IPv6 /{network.prefixlen} covers IPv4-mapped space (must be /120 or narrower)")
    return problems, prefixes


def _is_netmask(text: str) -> bool:
    """True for a dotted netmask (ones then zeros), False for a hostmask or anything else."""
    try:
        value = int(ipaddress.IPv4Address(text))
    except ValueError:
        return False
    inverted = ~value & 0xFFFFFFFF
    return inverted & (inverted + 1) == 0


def _shown_name(name: str) -> tuple[str, bool]:
    """The rule Name as printed: paths and address lookalikes are masked (review r1 F7)."""
    masked = WINDOWS_PATH.sub("<path>", name)
    masked = IPV4_LOOKALIKE.sub("x.x.x.x", masked)
    masked = IPV6_LOOKALIKE.sub("x:x::x", masked)
    return masked, masked != name


def _fix(name: str, verb: str, args: str = "", note: str = "") -> str:
    """One PowerShell command for the owner, or a plain instruction when the Name is masked."""
    shown, masked = _shown_name(name)
    if masked:
        return (f"{verb} the rule shown as {_quote(shown)} on the VPS "
                "(its full Name holds a path or an address and is not printed)")
    command = f"{verb} -Name {_quote(name)}{args}"
    return f"{command}  # {note}" if note else command


def _judge_rule(rule: Rule, allowed_udp_ports: dict[str, str]) -> tuple[str | None, str]:
    """(problem or None, scope summary) for one enabled inbound allow rule."""
    protocol, ports = rule.protocol, rule.local_ports
    label = _quote(_shown_name(rule.name)[0])
    keep_rdp = RDP_PORT in ports  # never advise disabling a rule that carries 3389 (contract F46)
    if protocol not in ("TCP", "UDP"):
        if keep_rdp:
            fix = _fix(rule.name, "Set-NetFirewallRule", " -Protocol TCP", "keeps RDP")
        else:
            fix = _fix(rule.name, "Disable-NetFirewallRule")
        return f"{label} protocol {protocol} is not allowed -> {fix}", ""
    allowed_port = allowed_udp_ports.get(rule.name)
    if ports == (RDP_PORT,):
        problems, prefixes = _scope_problems(rule.remote_addresses)
        summary = f"{protocol} 3389 scope {len(rule.remote_addresses)} entries ({', '.join(prefixes) or 'none'})"
        if problems:
            fix = _fix(rule.name, "Set-NetFirewallRule", " -RemoteAddress <your allowlist>")
            return f"{label} {protocol} 3389: {'; '.join(problems)} -> {fix}", summary
        return None, summary
    if protocol == "UDP" and allowed_port is not None and ports == (allowed_port,):
        return None, ""
    shown = ", ".join(ports) if ports else "none"
    if keep_rdp:
        fix = _fix(rule.name, "Set-NetFirewallRule", " -LocalPort 3389", "keeps RDP; removes the other ports")
    else:
        fix = _fix(rule.name, "Disable-NetFirewallRule")
    return f"{label} {protocol} ports {shown} are not allowed -> {fix}", ""


def _inbound(f: Facts) -> tuple[str, str]:
    if f.inbound_allow_rules is None:
        return UNKNOWN, "could not be read"
    allowed = {name: str(port) for port, name in ALLOWED_UDP.items()}
    failures, summaries, judged, ignored = [], [], 0, 0
    for rule in f.inbound_allow_rules:
        if rule.protocol in IGNORED_PROTOCOLS:
            ignored += 1
            continue
        judged += 1
        problem, summary = _judge_rule(rule, allowed)
        if problem:
            failures.append(problem)
        elif summary:
            summaries.append(summary)
    rdp_ok = any(s.startswith("TCP 3389") for s in summaries)
    warning = "" if rdp_ok else ("; no passing TCP 3389 rule yet: keep this RDP session open and fix the RDP "
                                 "rule first (runbook step 2)")
    if failures:
        gpo = "; a rule set by Group Policy is changed in the policy, then run again"
        return FAIL, "; ".join(failures) + gpo + warning
    shown = "; ".join(summaries) if summaries else "no 3389 rule"
    return PASS, f"{judged} rules judged, {ignored} ignored (ICMP/IGMP/IPv6); {shown}{warning}"


def _flag(value: bool | None, ok: str, bad: str) -> tuple[str, str]:
    if value is None:
        return UNKNOWN, "could not be read"
    return (PASS, ok) if value else (FAIL, bad)


def _lockout(f: Facts) -> tuple[str, str]:
    if f.lockout_threshold is None:
        return UNKNOWN, "could not be read (net accounts in English only)"
    if f.lockout_threshold in LOCKOUT_RANGE:
        return PASS, f"threshold {f.lockout_threshold}"
    return FAIL, f"threshold {f.lockout_threshold} (must be 1-10) -> net accounts /lockoutthreshold:5"


def _sync(f: Facts) -> tuple[str, str]:
    if f.sync_clients is None:
        return UNKNOWN, "could not be read"
    if f.sync_clients:
        return FAIL, "found " + ", ".join(f.sync_clients) + " -> uninstall and stop them"
    return PASS, "none found"


def _python_env(f: Facts) -> tuple[str, str]:
    failures = []
    if f.uv_version is not None and f.uv_version != EXPECTED_UV:
        failures.append(f"uv {f.uv_version} (expected {EXPECTED_UV})")
    if f.python_version is not None and f.python_version != EXPECTED_PYTHON:
        failures.append(f"Python {f.python_version} (expected {EXPECTED_PYTHON})")
    if f.project_synced is False:
        failures.append("environment does not match uv.lock -> uv sync --locked --python 3.12.15")
    unknown = None in (f.uv_version, f.python_version, f.project_synced)
    return _known_status(failures, unknown, f"uv {f.uv_version}, Python {f.python_version}, synced with uv.lock")


def _git(f: Facts) -> tuple[str, str]:
    # The helper advice comes last and ends with its command: after `--%` PowerShell passes the
    # rest of the line to git, so nothing may follow it (review r2 F19).
    failures = []
    if f.remote_has_userinfo is True:
        failures.append("a remote URL is not https:// or carries user information -> clone again over HTTPS "
                        "without user information")
    found = f.git_credential_helpers or ()
    helpers = tuple(h for h in found if h != EXTRAHEADER)
    headers = len(found) - len(helpers)
    if headers:
        failures.append(f"{headers} http extraheader(s) in effect (values not shown) -> remove each key that "
                        "git config --show-origin --get-regexp \"^http\\..*extraheader$\" lists, in the file it names")
    if helpers:
        failures.append(f"{len(helpers)} credential helper(s) in effect "
                        f"({helper_kinds(helpers)}; values not shown); also remove any "
                        "credential.<url>.helper that git config --show-origin --get-regexp "
                        "\"^credential\\..*helper$\" lists -> git config --global credential.helper --% \"\"")
    unknown = f.git_credential_helpers is None or f.remote_has_userinfo is None
    return _known_status(failures, unknown, "no credential helper; remote URLs without user information")


def _count(value: int | None, what: str) -> tuple[str, str]:
    if value is None:
        return UNKNOWN, "could not be read"
    return (PASS, f"no {what}") if value == 0 else (FAIL, f"{value} {what} -> remove them from the clone")


def _holdout(f: Facts) -> tuple[str, str]:
    return _flag(None if f.holdout_dir_in_repo is None else not f.holdout_dir_in_repo,
                 "no holdout folder in the repository", "a holdout folder is inside the repository")


def evaluate(facts: Facts) -> Report:
    rows = (
        ("os", _os(facts)),
        ("cpu", _minimum(facts.cpu_count, MIN_CPUS, lambda v: f"{v} logical CPUs (minimum {MIN_CPUS})")),
        ("ram", _minimum(facts.visible_ram_bytes, MIN_RAM_BYTES,
                         lambda v: f"{v // 2**20} MiB visible (minimum {MIN_RAM_BYTES // 2**20} MiB = 3.5 GiB)")),
        ("disk", _minimum(facts.repo_drive_free_bytes, MIN_DISK_BYTES,
                          lambda v: f"{v // 10**9} GB free on the repository drive (minimum 30 GB)")),
        ("firewall", _firewall(facts)),
        ("inbound", _inbound(facts)),
        ("nla", _flag(facts.nla_required, "Network Level Authentication required",
                      "NLA is off -> require it (policy UserAuthentication = 1)")),
        ("lockout", _lockout(facts)),
        ("drive_redirection", _flag(facts.drive_redirection_disabled, "drive redirection disabled",
                                    "drive redirection allowed -> policy fDisableCdm = 1")),
        ("clipboard", _flag(facts.clipboard_files_to_client_blocked, "server-to-client clipboard: no files",
                            "files can be copied to the client -> SCClipLevel 1 (text only) or fDisableClip = 1")),
        ("sync_clients", _sync(facts)),
        ("python_env", _python_env(facts)),
        ("git", _git(facts)),
        ("secrets", _count(facts.secret_like_files_in_repo, "secret-like files")),
        ("holdout", _holdout(facts)),
    )
    items = tuple(Item(name=name, status=status, detail=detail) for name, (status, detail) in rows)
    statuses = {item.status for item in items}
    verdict = FAIL if FAIL in statuses else UNKNOWN if UNKNOWN in statuses else PASS
    return Report(items=items, verdict=verdict)


def render(report: Report) -> str:
    lines = ["# ENV-001 host report", "", "| Item | Status | Detail |", "|---|---|---|"]
    for item in report.items:
        detail = item.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item.name} | {item.status} | {detail} |")
    lines += ["", f"HOST REPORT: {report.verdict}"]
    return "\n".join(lines) + "\n"


# ---- collect_facts (Windows only) ----------------------------------------------------------------
def _run(command: list[str], cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


# The git and uv sources (contract v1.6). They take the runner, so unit tests can call them with
# their own (review r2 F21); collect_facts uses _run. A runner result of None means the program did not run.
Runner = Callable[..., subprocess.CompletedProcess | None]


def credential_helpers(repo: Path, run: Runner = _run) -> tuple[str, ...] | None:
    """Helpers in effect plus one EXTRAHEADER per http.<url>.extraheader entry (contract v1.7)."""
    helpers = run(["git", "config", "--show-origin", "-z", "--get-regexp", r"^credential\..*helper$"], cwd=repo)
    headers = run(["git", "config", "--show-origin", "-z", "--get-regexp", r"^http\..*extraheader$"], cwd=repo)
    if helpers is None or headers is None:
        return None
    found = helpers_from_git(helpers.returncode, helpers.stdout)
    extra = extraheaders_from_git(headers.returncode, headers.stdout)
    return None if found is None or extra is None else found + extra


def remote_userinfo(repo: Path, run: Runner = _run) -> bool | None:
    """True when any fetch or push URL of any remote is not https:// or carries user information."""
    names = run(["git", "remote"], cwd=repo)
    if names is None or names.returncode != 0:
        return None
    urls: list[str] = []
    for name in names.stdout.split():
        for extra in ([], ["--push"]):
            done = run(["git", "remote", "get-url", *extra, "--all", name], cwd=repo)
            if done is None or done.returncode != 0:
                return None
            urls.extend(done.stdout.splitlines())
    return any_unsafe_url(urls)


def project_synced(repo: Path, run: Runner = _run) -> bool | None:
    done = run(["uv", "sync", "--locked", "--check", "--offline"], cwd=repo, timeout=180)
    return synced_from_uv(None if done is None else done.returncode)


def collect_facts(repo: Path) -> Facts:
    """Read every fact from its one source; a fact that cannot be read is None (UNKNOWN)."""
    import ctypes
    import winreg
    from ctypes import wintypes

    missing = object()
    roots = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}

    def reg_value(root, path, name):
        try:
            with winreg.OpenKey(roots[root], path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                return winreg.QueryValueEx(key, name)[0]
        except FileNotFoundError:
            return missing

    def optional(value):
        return None if value is missing else value

    def guarded(read):
        try:
            return read()
        except (OSError, ValueError, TypeError):
            return None

    def os_caption():
        value = reg_value("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ProductName")
        return None if value is missing else str(value)

    def os_build():
        value = reg_value("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "CurrentBuildNumber")
        return None if value is missing else int(value)

    def visible_ram():
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.ullTotalPhys)

    def firewall():
        encoded = base64.b64encode(FIREWALL_SCRIPT.encode("utf-16-le")).decode("ascii")
        done = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], timeout=180)
        if done is None or done.returncode != 0:
            return None, None
        return parse_firewall_json(done.stdout)

    def rdp_setting(name):
        policy = optional(reg_value("HKLM", POLICY_KEY, name))
        winstation = optional(reg_value("HKLM", WINSTATION_KEY, name))
        return policy_first(policy, winstation)

    def clipboard():
        level = optional(reg_value("HKLM", POLICY_KEY, "SCClipLevel"))
        return clipboard_blocks_files(rdp_setting("fDisableClip"), level)

    def lockout():
        done = _run(["net", "accounts"])
        return None if done is None or done.returncode != 0 else parse_lockout(done.stdout)

    def installed_sync_clients():
        found = set()
        for root, path in UNINSTALL_KEYS:
            try:
                key = winreg.OpenKey(roots[root], path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            except FileNotFoundError:
                continue
            with key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    sub = winreg.EnumKey(key, index)
                    name = reg_value(root, path + "\\" + sub, "DisplayName")
                    if name is missing:
                        continue
                    found.update(f"{label} (installed)" for label in SYNC_DISPLAY_NAMES if label.lower() in str(name).lower())
        return found

    def running_sync_clients():
        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                        ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
        if snapshot in (None, ctypes.c_void_p(-1).value):
            raise OSError("CreateToolhelp32Snapshot failed")
        found = set()
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            more = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while more:
                label = SYNC_PROCESSES.get(entry.szExeFile.lower())
                if label:
                    found.add(f"{label} (running)")
                more = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            kernel32.CloseHandle(snapshot)
        return found

    def sync_clients():
        return tuple(sorted(installed_sync_clients() | running_sync_clients()))

    def uv_version():
        done = _run(["uv", "--version"])
        return None if done is None or done.returncode != 0 else parse_uv_version(done.stdout)

    def python_version():
        done = _run([str(repo / ".venv" / "Scripts" / "python.exe"), "-c",
                     "import platform; print(platform.python_version())"])
        return None if done is None or done.returncode != 0 else done.stdout.strip() or None

    rules, profiles = guarded(firewall) or (None, None)
    return Facts(
        os_caption=guarded(os_caption),
        os_build=guarded(os_build),
        cpu_count=os.cpu_count(),
        visible_ram_bytes=guarded(visible_ram),
        repo_drive_free_bytes=guarded(lambda: shutil.disk_usage(repo).free),
        inbound_allow_rules=rules,
        firewall_profiles=profiles,
        nla_required=guarded(lambda: rdp_setting("UserAuthentication")),
        lockout_threshold=guarded(lockout),
        drive_redirection_disabled=guarded(lambda: rdp_setting("fDisableCdm")),
        clipboard_files_to_client_blocked=guarded(clipboard),
        sync_clients=guarded(sync_clients),
        uv_version=guarded(uv_version),
        python_version=guarded(python_version),
        project_synced=guarded(lambda: project_synced(repo)),
        git_credential_helpers=guarded(lambda: credential_helpers(repo)),
        remote_has_userinfo=guarded(lambda: remote_userinfo(repo)),
        secret_like_files_in_repo=guarded(lambda: count_secret_like(repo)),
        holdout_dir_in_repo=guarded(lambda: has_holdout_dir(repo)),
    )


# ---- CLI -----------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ENV-001 host report (read-only)")
    parser.add_argument("--role", required=True, choices=["acquisition"])
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        print("host_report reads Windows facts and runs on the VPS only", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    report = evaluate(collect_facts(args.repo.resolve()))
    print(render(report), end="")
    return 0 if report.verdict == PASS else 1


if __name__ == "__main__":
    sys.exit(main())
