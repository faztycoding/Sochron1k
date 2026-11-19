r"""Approved ENV-001 v1.5 contract tests for AC-02 (docs/contracts/ENV-001-vps-acquisition-host.md);
run pytest from the repository root.

scripts/env/host_report.py is loaded by the contract's recipe: spec_from_file_location("host_report",
<repo>/scripts/env/host_report.py), module_from_spec, sys.modules["host_report"] = module,
spec.loader.exec_module(module). Only contract names are used: EXPECTED_UV, EXPECTED_PYTHON,
ALLOWED_UDP, IGNORED_PROTOCOLS, MIN_IPV4_PREFIX, MIN_IPV6_PREFIX, Facts, Rule, Profile,
collect_facts (looked up and read in the source, never called), evaluate and render. Every Facts
value is synthetic; addresses are RFC 5737 (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and
RFC 3849 (2001:db8::/32) documentation values, plus the "everything" scopes 0.0.0.0/0 and ::/0 that
AC-02 names. No test needs a Windows API.

Conventions the contract leaves to these tests (also in docs/handoff/ENV-001.md):
1. <repo> is Path(__file__).resolve().parents[3]: this file is <repo>/tests/acceptance/ENV-001/<file>,
   so parents[2] is tests/. The same file runs in any tree with that layout.
2. Item.status and Report.verdict compare equal to "PASS", "FAIL" or "UNKNOWN" (a str or a str-valued
   enum). Item.detail is a str. Report.items is a tuple with exactly one Item per row of the contract's
   table, named os, cpu, ram, disk, firewall, inbound, nla, lockout, drive_redirection, clipboard,
   sync_clients, python_env, git, secrets, holdout; their order is not checked.
3. Facts, Rule and Profile are frozen dataclasses with exactly the contract's field names (order not
   checked; tests build them with keywords). Their annotations evaluate with typing.get_type_hints to
   the contract's types; Optional, Union and typing.Tuple spellings count as the same type.
4. ALLOWED_UDP: the ports are fixed at {68, 546}; the rule names are taken from the module and are
   not asserted (the contract confirms them on Server 2022/2025 later). EXPECTED_UV is any non-empty
   str. A wrong version is derived from the constant: last number + 1, major.minor only (the form
   .venv/pyvenv.cfg holds), or the constant with "0" appended (a longer version that contains the
   constant; python_env compares with ==).
5. os: a caption that starts "Windows Server 2022"/"Windows Server 2025" with build 20348/26100
   passes. A client caption with build 26100 fails ("Windows 10 Pro" is what ProductName reports on
   Windows 11 24H2, which shares build 26100), and every other build fails.
6. firewall: "enabled" other than "True" (also "NotConfigured" and the numeric enum text "1") and a
   default inbound action other than "Block"/"NotConfigured" (also the numeric text "4") fail.
7. inbound: one Item for all rules. Its FAIL detail names every failing rule's Name, and render shows
   that Name too (the owner acts on the printed report). Advice is checked only where the contract is
   unambiguous: a TCP/UDP rule whose local_ports is ("3389",) and whose scope fails gets
   "Set-NetFirewallRule" with "-RemoteAddress" and never "Disable-NetFirewallRule" (in the detail
   and in render); a non-3389 TCP/UDP rule and a rule of another protocol get
   "Disable-NetFirewallRule -Name <its Name>" in the detail. A command is bound to a rule as
   "<command> -Name <Name>", the Name optionally in ' or " quotes (one Name per command). When the
   RDP rule's scope fails next to a rule that needs disabling (the Shadow rule on a fresh VPS), the
   RDP rule gets "Set-NetFirewallRule -Name <its Name>" and never "Disable-NetFirewallRule -Name <its
   Name>" (in the detail and in render). Rules that mix 3389 with other ports, a TCP rule without
   ports and a protocol "Any" rule on 3389 are checked for FAIL and their Name only.
8. A 3389 scope entry with host bits under a prefix ("192.0.2.10/24") is that prefix
   (ip_network(strict=False)); 0 entries fail like 5 do; a range "a-b" fails however narrow.
9. Addresses: no Item.detail and no render output matches the AC-06 IPv4 pattern
   \b([0-9]{1,3}\.){3}[0-9]{1,3}\b (masks and 0.0.0.0 included), and none contains "2001:db8" or
   "2001:0db8" (every IPv6 value here lies in 2001:db8::/32) or the network part "192.0.2",
   "198.51.100" or "203.0.113" of the RFC 5737 networks used here, so a partly masked address such
   as 198.51.100.x/24 fails too. The AC-06 IPv6 pattern itself is not applied, because it also
   matches clock times.
10. The last line is render(report).rstrip("\n").splitlines()[-1]; a trailing newline is allowed.
11. "Only inside collect_facts" means lexically inside the top-level function collect_facts (nested
    functions included). A Windows-only module (winreg, ctypes, msvcrt, _winapi, nt) imported
    anywhere else fails, also through import_module or __import__ with a literal name, called as a
    bare name (after "from importlib import import_module") or as an attribute
    (importlib.import_module, builtins.__import__). The script imports standard-library modules only
    (the contract's "stdlib only" rule).
12. secret_like_files_in_repo == 0 in the valid Facts stands for a repo whose only env-like file is
    .env.example: collect_facts leaves it out of the count, and evaluate only sees the count.
"""

import ast
import importlib.util
import ipaddress
import re
import sys
import types
import typing
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "env" / "host_report.py"
MISSING = "AC-02: host_report not implemented (scripts/env/host_report.py is missing)"
BUILD_NAMES = ("Facts", "Rule", "Profile", "ALLOWED_UDP", "EXPECTED_UV", "EXPECTED_PYTHON", "evaluate")
_LOADED = {}

GIB = 2**30
GB = 10**9
RAM_MIN = 3_758_096_384  # 3.5 GiB = 3.5 * 2**30 bytes
DISK_MIN = 30 * GB  # 30 GB with 10**9 bytes per GB

ITEMS = frozenset({
    "os", "cpu", "ram", "disk", "firewall", "inbound", "nla", "lockout", "drive_redirection",
    "clipboard", "sync_clients", "python_env", "git", "secrets", "holdout",
})
FACT_ITEM = {
    "os_caption": "os",
    "os_build": "os",
    "cpu_count": "cpu",
    "visible_ram_bytes": "ram",
    "repo_drive_free_bytes": "disk",
    "inbound_allow_rules": "inbound",
    "firewall_profiles": "firewall",
    "nla_required": "nla",
    "lockout_threshold": "lockout",
    "drive_redirection_disabled": "drive_redirection",
    "clipboard_files_to_client_blocked": "clipboard",
    "sync_clients": "sync_clients",
    "uv_version": "python_env",
    "python_version": "python_env",
    "project_synced": "python_env",
    "git_credential_helpers": "git",
    "remote_has_userinfo": "git",
    "secret_like_files_in_repo": "secrets",
    "holdout_dir_in_repo": "holdout",
}
WINDOWS_ONLY = frozenset({"winreg", "ctypes", "msvcrt", "_winapi", "nt"})
IPV4_PATTERN = re.compile(r"\b([0-9]{1,3}\.){3}[0-9]{1,3}\b")  # the AC-06 IPv4 pattern
IPV6_DOC_PREFIXES = ("2001:db8", "2001:0db8")
IPV4_DOC_STEMS = ("192.0.2", "198.51.100", "203.0.113")  # the RFC 5737 networks used here
DOC_NETWORKS = tuple(ipaddress.ip_network(net) for net in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32",
))

RDP_TCP = "RemoteDesktop-UserMode-In-TCP"
RDP_UDP = "RemoteDesktop-UserMode-In-UDP"
# Four entries (the most allowed): a single host, a /24 as CIDR, a /24 as mask and an IPv6 /48.
RDP_SCOPE = ("192.0.2.10", "198.51.100.0/24", "203.0.113.0/255.255.255.0", "2001:db8:1234::/48")


# ---------------------------------------------------------------- loading


def _load():
    """Load the script once by the contract's recipe; a missing script fails as not implemented."""
    if "module" in _LOADED:
        return _LOADED["module"]
    if not SCRIPT.is_file():
        pytest.fail(MISSING, pytrace=False)
    spec = importlib.util.spec_from_file_location("host_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["host_report"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get("host_report") is module:
            del sys.modules["host_report"]
        raise
    _LOADED["module"] = module
    return module


def _hr(*names):
    """The loaded module; any contract name it lacks fails the test as not implemented."""
    module = _load()
    for name in BUILD_NAMES + names:
        if not hasattr(module, name):
            pytest.fail(f"AC-02: host_report.{name} not implemented", pytrace=False)
    return module


def _script_tree():
    if not SCRIPT.is_file():
        pytest.fail(MISSING, pytrace=False)
    return ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))


# ---------------------------------------------------------------- building Facts


def _rule(hr, name, protocol, local_ports, remote_addresses, profiles="Any"):
    return hr.Rule(
        name=name,
        protocol=protocol,
        profiles=profiles,
        local_ports=tuple(local_ports),
        remote_addresses=tuple(remote_addresses),
    )


def _allowed_udp(hr):
    """(port, Name) pairs of ALLOWED_UDP, smallest port first."""
    return sorted(hr.ALLOWED_UDP.items())


def _valid_rules(hr):
    """RDP limited to the allowlist, the Core Networking defaults that stay on, ignored protocols."""
    dhcp = tuple(_rule(hr, name, "UDP", (str(port),), ("Any",)) for port, name in _allowed_udp(hr))
    return (
        _rule(hr, RDP_TCP, "TCP", ("3389",), RDP_SCOPE),
        _rule(hr, RDP_UDP, "UDP", ("3389",), ("192.0.2.10",)),
        *dhcp,
        # Ignored protocols, each written so that it would fail if it were judged.
        _rule(hr, "CoreNet-ICMP4-DUFRAG-In", "ICMPv4", ("Any",), ("Any",)),
        _rule(hr, "CoreNet-ICMP6-DU-In", "ICMPv6", ("Any",), ("Any",)),
        _rule(hr, "CoreNet-IGMP-In", "2", ("Any",), ("Any",), profiles="Domain, Private"),
        _rule(hr, "CoreNet-IPv6-In", "41", ("Any",), ("Any",), profiles="Public"),
    )


def _valid_profiles(hr):
    return (
        hr.Profile(name="Domain", enabled="True", default_inbound_action="Block"),
        hr.Profile(name="Private", enabled="True", default_inbound_action="NotConfigured"),
        hr.Profile(name="Public", enabled="True", default_inbound_action="Block"),
    )


def _valid(hr):
    return hr.Facts(
        os_caption="Windows Server 2025 Datacenter",
        os_build=26100,
        cpu_count=2,
        visible_ram_bytes=8 * GIB,
        repo_drive_free_bytes=80 * GB,
        inbound_allow_rules=_valid_rules(hr),
        firewall_profiles=_valid_profiles(hr),
        nla_required=True,
        lockout_threshold=5,
        drive_redirection_disabled=True,
        clipboard_files_to_client_blocked=True,
        sync_clients=(),
        uv_version=hr.EXPECTED_UV,
        python_version=hr.EXPECTED_PYTHON,
        project_synced=True,
        git_credential_helpers=(),
        remote_has_userinfo=False,
        secret_like_files_in_repo=0,  # .env.example only: collect_facts does not count it
        holdout_dir_in_repo=False,
    )


def _with_rule(facts, rule):
    return replace(facts, inbound_allow_rules=facts.inbound_allow_rules + (rule,))


def _with_changed_rule(facts, name, **changes):
    assert any(rule.name == name for rule in facts.inbound_allow_rules), name
    rules = tuple(
        replace(rule, **changes) if rule.name == name else rule for rule in facts.inbound_allow_rules
    )
    return replace(facts, inbound_allow_rules=rules)


def _with_profile(facts, name, **changes):
    assert any(profile.name == name for profile in facts.firewall_profiles), name
    profiles = tuple(
        replace(profile, **changes) if profile.name == name else profile
        for profile in facts.firewall_profiles
    )
    return replace(facts, firewall_profiles=profiles)


def _without_profile(facts, name):
    profiles = tuple(profile for profile in facts.firewall_profiles if profile.name != name)
    assert len(profiles) == len(facts.firewall_profiles) - 1, name
    return replace(facts, firewall_profiles=profiles)


def _other_version(version):
    """The same version with its last number raised by one: a near miss of the constant."""
    head, dot, last = version.rpartition(".")
    other = f"{head}{dot}{int(last) + 1}" if last.isdigit() else f"{version}.1"
    assert other != version
    return other


def _major_minor(version):
    """Only major.minor, the form .venv/pyvenv.cfg holds."""
    short = ".".join(version.split(".")[:2])
    assert short != version
    return short


# ---------------------------------------------------------------- reading a Report


def _statuses(report):
    items = report.items
    assert isinstance(items, tuple)
    names = [item.name for item in items]
    assert sorted(names) == sorted(ITEMS), names
    return {item.name: item.status for item in items}


def _item(report, name):
    return next(item for item in report.items if item.name == name)


def _expect(report, verdict, changed):
    """Items named in `changed` have that status, every other item PASS, and the verdict."""
    expected = {name: changed.get(name, "PASS") for name in ITEMS}
    assert _statuses(report) == expected
    assert report.verdict == verdict


def _last_line(text):
    assert isinstance(text, str)
    return text.rstrip("\n").splitlines()[-1]


def _advises(text, command, name):
    """`command -Name <name>` appears in text, the Name optionally in ' or " quotes."""
    pattern = re.escape(command) + r"\s+-Name\s+['\"]?" + re.escape(name)
    return re.search(pattern, text) is not None


def _shape(annotation):
    """An evaluated annotation with Optional/Union/typing.Tuple spellings made equal."""
    origin = typing.get_origin(annotation)
    if origin is None:
        return annotation
    arguments = tuple(_shape(argument) for argument in typing.get_args(annotation))
    if origin in (typing.Union, types.UnionType):
        return ("union", frozenset(arguments))
    return (origin, arguments)


# ---------------------------------------------------------------- interface


def test_ac02_module_constants_match_the_contract():
    hr = _hr("IGNORED_PROTOCOLS", "MIN_IPV4_PREFIX", "MIN_IPV6_PREFIX")
    assert hr.EXPECTED_PYTHON == "3.12.15"
    assert isinstance(hr.EXPECTED_UV, str) and hr.EXPECTED_UV
    assert set(hr.IGNORED_PROTOCOLS) == {"ICMPv4", "ICMPv6", "2", "41"}
    assert hr.MIN_IPV4_PREFIX == 24
    assert hr.MIN_IPV6_PREFIX == 48
    assert set(hr.ALLOWED_UDP) == {68, 546}
    names = list(hr.ALLOWED_UDP.values())
    assert all(isinstance(name, str) and name for name in names)
    assert len(set(names)) == len(names)


def test_ac02_contract_functions_exist():
    hr = _hr("collect_facts", "render")
    assert callable(hr.collect_facts)
    assert callable(hr.evaluate)
    assert callable(hr.render)


RECORD_FIELDS = {
    "Facts": FACT_ITEM.keys(),
    "Rule": ("name", "protocol", "profiles", "local_ports", "remote_addresses"),
    "Profile": ("name", "enabled", "default_inbound_action"),
}


def _sample(hr, record):
    if record == "Facts":
        return _valid(hr)
    if record == "Rule":
        return _valid_rules(hr)[0]
    return _valid_profiles(hr)[0]


@pytest.mark.parametrize("record", sorted(RECORD_FIELDS))
def test_ac02_records_are_frozen_dataclasses_with_the_contract_fields(record):
    hr = _hr()
    cls = getattr(hr, record)
    assert is_dataclass(cls)
    assert {field.name for field in fields(cls)} == set(RECORD_FIELDS[record])
    instance = _sample(hr, record)
    first = sorted(RECORD_FIELDS[record])[0]
    with pytest.raises(FrozenInstanceError):
        setattr(instance, first, getattr(instance, first))


def _contract_types(hr):
    optional = {name: str | None for name in ("os_caption", "uv_version", "python_version")}
    optional |= {name: int | None for name in (
        "os_build", "cpu_count", "visible_ram_bytes", "repo_drive_free_bytes", "lockout_threshold",
        "secret_like_files_in_repo",
    )}
    optional |= {name: bool | None for name in (
        "nla_required", "drive_redirection_disabled", "clipboard_files_to_client_blocked",
        "project_synced", "remote_has_userinfo", "holdout_dir_in_repo",
    )}
    optional |= {name: tuple[str, ...] | None for name in ("sync_clients", "git_credential_helpers")}
    optional["inbound_allow_rules"] = tuple[hr.Rule, ...] | None
    optional["firewall_profiles"] = tuple[hr.Profile, ...] | None
    return {
        "Facts": optional,
        "Rule": {
            "name": str, "protocol": str, "profiles": str,
            "local_ports": tuple[str, ...], "remote_addresses": tuple[str, ...],
        },
        "Profile": {"name": str, "enabled": str, "default_inbound_action": str},
    }


@pytest.mark.parametrize("record", sorted(RECORD_FIELDS))
def test_ac02_record_annotations_evaluate_to_the_contract_types(record):
    hr = _hr()
    hints = typing.get_type_hints(getattr(hr, record), globalns=vars(hr))
    expected = _contract_types(hr)[record]
    assert {name: _shape(hint) for name, hint in hints.items()} == {
        name: _shape(hint) for name, hint in expected.items()
    }


# ---------------------------------------------------------------- the valid host


def test_ac02_valid_host_passes_every_item_and_renders_pass():
    hr = _hr("render")
    report = hr.evaluate(_valid(hr))
    _expect(report, "PASS", {})
    assert all(isinstance(item.detail, str) for item in report.items)
    assert _last_line(hr.render(report)) == "HOST REPORT: PASS"


def _set(**changes):
    return lambda hr, facts: replace(facts, **changes)


def _profiles_all(enabled, action):
    def build(hr, facts):
        profiles = tuple(
            replace(profile, enabled=enabled, default_inbound_action=action)
            for profile in facts.firewall_profiles
        )
        return replace(facts, firewall_profiles=profiles)
    return build


def _rdp_tcp_scope(*scope):
    return lambda hr, facts: _with_changed_rule(facts, RDP_TCP, remote_addresses=scope)


STILL_VALID = {
    "os-server-2022-standard": _set(os_caption="Windows Server 2022 Standard", os_build=20348),
    "os-server-2022-datacenter": _set(os_caption="Windows Server 2022 Datacenter", os_build=20348),
    "os-server-2025-standard": _set(os_caption="Windows Server 2025 Standard", os_build=26100),
    "cpu-4": _set(cpu_count=4),
    "ram-exactly-3.5-gib": _set(visible_ram_bytes=RAM_MIN),
    "disk-exactly-30-gb": _set(repo_drive_free_bytes=DISK_MIN),
    "lockout-1": _set(lockout_threshold=1),
    "lockout-10": _set(lockout_threshold=10),
    "firewall-all-block": _profiles_all("True", "Block"),
    "firewall-all-notconfigured": _profiles_all("True", "NotConfigured"),
    "firewall-profiles-in-other-order": lambda hr, facts: replace(
        facts, firewall_profiles=tuple(reversed(facts.firewall_profiles))
    ),
    "scope-host": _rdp_tcp_scope("192.0.2.10"),
    "scope-host-as-v4-32": _rdp_tcp_scope("192.0.2.10/32"),
    "scope-v4-24": _rdp_tcp_scope("198.51.100.0/24"),
    "scope-v4-25": _rdp_tcp_scope("198.51.100.128/25"),
    "scope-v4-mask-24": _rdp_tcp_scope("203.0.113.0/255.255.255.0"),
    "scope-v4-mask-25": _rdp_tcp_scope("203.0.113.128/255.255.255.128"),
    "scope-v4-24-with-host-bits": _rdp_tcp_scope("192.0.2.10/24"),
    "scope-v6-host": _rdp_tcp_scope("2001:db8::10"),
    "scope-v6-48": _rdp_tcp_scope("2001:db8:1234::/48"),
    "scope-v6-64": _rdp_tcp_scope("2001:db8:1234:5678::/64"),
    "scope-four-hosts": _rdp_tcp_scope("192.0.2.1", "192.0.2.2", "192.0.2.3", "192.0.2.4"),
    "allowed-udp-from-localsubnet": lambda hr, facts: _with_changed_rule(
        facts, _allowed_udp(hr)[0][1], remote_addresses=("LocalSubnet",)
    ),
}


@pytest.mark.parametrize("case", sorted(STILL_VALID))
def test_ac02_passing_side_of_each_boundary_passes(case):
    hr = _hr()
    facts = STILL_VALID[case](hr, _valid(hr))
    _expect(hr.evaluate(facts), "PASS", {})


# ---------------------------------------------------------------- one wrong value at a time


WRONG = {
    "os-server-2019": ("os", _set(os_caption="Windows Server 2019 Datacenter", os_build=17763)),
    "os-server-2016": ("os", _set(os_caption="Windows Server 2016 Standard", os_build=14393)),
    "os-client-caption-build-26100": ("os", _set(os_caption="Windows 10 Pro", os_build=26100)),
    "os-client-windows-10": ("os", _set(os_caption="Windows 10 Enterprise", os_build=19045)),
    "os-build-20347": ("os", _set(os_caption="Windows Server 2022 Standard", os_build=20347)),
    "os-build-20349": ("os", _set(os_caption="Windows Server 2022 Standard", os_build=20349)),
    "os-build-26099": ("os", _set(os_caption="Windows Server 2025 Datacenter", os_build=26099)),
    "os-build-26101": ("os", _set(os_caption="Windows Server 2025 Datacenter", os_build=26101)),
    "cpu-1": ("cpu", _set(cpu_count=1)),
    "ram-just-under-3.5-gib": ("ram", _set(visible_ram_bytes=RAM_MIN - 1)),
    "disk-just-under-30-gb": ("disk", _set(repo_drive_free_bytes=DISK_MIN - 1)),
    "firewall-public-disabled": (
        "firewall", lambda hr, facts: _with_profile(facts, "Public", enabled="False")),
    "firewall-domain-disabled": (
        "firewall", lambda hr, facts: _with_profile(facts, "Domain", enabled="False")),
    "firewall-public-enabled-notconfigured": (
        "firewall", lambda hr, facts: _with_profile(facts, "Public", enabled="NotConfigured")),
    "firewall-private-enabled-numeric": (
        "firewall", lambda hr, facts: _with_profile(facts, "Private", enabled="1")),
    "firewall-public-default-allow": (
        "firewall", lambda hr, facts: _with_profile(facts, "Public", default_inbound_action="Allow")),
    "firewall-private-default-allow": (
        "firewall", lambda hr, facts: _with_profile(facts, "Private", default_inbound_action="Allow")),
    "firewall-domain-default-numeric": (
        "firewall", lambda hr, facts: _with_profile(facts, "Domain", default_inbound_action="4")),
    "firewall-missing-domain": ("firewall", lambda hr, facts: _without_profile(facts, "Domain")),
    "firewall-missing-private": ("firewall", lambda hr, facts: _without_profile(facts, "Private")),
    "firewall-missing-public": ("firewall", lambda hr, facts: _without_profile(facts, "Public")),
    "firewall-no-profiles": ("firewall", _set(firewall_profiles=())),
    "nla-off": ("nla", _set(nla_required=False)),
    "lockout-0": ("lockout", _set(lockout_threshold=0)),
    "lockout-11": ("lockout", _set(lockout_threshold=11)),
    "drive-redirection-on": ("drive_redirection", _set(drive_redirection_disabled=False)),
    "clipboard-sends-files": ("clipboard", _set(clipboard_files_to_client_blocked=False)),
    "sync-onedrive-running": ("sync_clients", _set(sync_clients=("OneDrive",))),
    "sync-dropbox-installed": ("sync_clients", _set(sync_clients=("Dropbox",))),
    "python-env-uv-other-version": (
        "python_env", lambda hr, facts: replace(facts, uv_version=_other_version(hr.EXPECTED_UV))),
    "python-env-python-other-patch": (
        "python_env",
        lambda hr, facts: replace(facts, python_version=_other_version(hr.EXPECTED_PYTHON))),
    "python-env-python-major-minor-only": (
        "python_env",
        lambda hr, facts: replace(facts, python_version=_major_minor(hr.EXPECTED_PYTHON))),
    "python-env-uv-longer-version": (
        "python_env", lambda hr, facts: replace(facts, uv_version=hr.EXPECTED_UV + "0")),
    "python-env-python-longer-version": (
        "python_env", lambda hr, facts: replace(facts, python_version=hr.EXPECTED_PYTHON + "0")),
    "python-env-not-synced": ("python_env", _set(project_synced=False)),
    "git-credential-helper-manager": ("git", _set(git_credential_helpers=("manager",))),
    "git-remote-with-userinfo": ("git", _set(remote_has_userinfo=True)),
    "secrets-one-env-file": ("secrets", _set(secret_like_files_in_repo=1)),
    "holdout-dir-in-repo": ("holdout", _set(holdout_dir_in_repo=True)),
}


@pytest.mark.parametrize("case", sorted(WRONG))
def test_ac02_one_wrong_value_fails_that_item_and_the_verdict(case):
    hr = _hr("render")
    item, change = WRONG[case]
    report = hr.evaluate(change(hr, _valid(hr)))
    _expect(report, "FAIL", {item: "FAIL"})
    assert _last_line(hr.render(report)) == "HOST REPORT: FAIL"


# ---------------------------------------------------------------- inbound rules


def _added(name, protocol, local_ports, remote_addresses, profiles="Any", advice="disable"):
    def build(hr):
        rule = _rule(hr, name, protocol, local_ports, remote_addresses, profiles)
        return _with_rule(_valid(hr), rule), (name,), advice
    return build


def _rdp_scope(rule_name, *scope):
    def build(hr):
        facts = _with_changed_rule(_valid(hr), rule_name, remote_addresses=scope)
        return facts, (rule_name,), "scope"
    return build


def _allowed_changed(index, protocol=None, local_ports=None):
    """Change the ALLOWED_UDP rule at `index`; local_ports may use {port} and {other}."""
    def build(hr):
        pairs = _allowed_udp(hr)
        port, name = pairs[index]
        other = pairs[1 - index][0]
        changes = {}
        if protocol is not None:
            changes["protocol"] = protocol
        if local_ports is not None:
            changes["local_ports"] = tuple(
                value.format(port=port, other=other) for value in local_ports
            )
        return _with_changed_rule(_valid(hr), name, **changes), (name,), "disable"
    return build


BAD_SCOPES = {
    "any": ("Any",),
    "v4-everything": ("0.0.0.0/0",),
    "v6-everything": ("::/0",),
    "keyword-internet": ("Internet",),
    "keyword-localsubnet": ("LocalSubnet",),
    "keyword-defaultgateway": ("DefaultGateway",),
    "range-wide": ("192.0.2.1-192.0.2.200",),
    "range-two-hosts": ("192.0.2.10-192.0.2.11",),
    "range-v6": ("2001:db8::1-2001:db8::ff",),
    "v4-prefix-23": ("198.51.100.0/23",),
    "v4-prefix-16": ("198.51.100.0/16",),
    "v4-mask-23": ("198.51.100.0/255.255.254.0",),
    "v4-mask-16": ("198.51.100.0/255.255.0.0",),
    "v6-prefix-47": ("2001:db8:1234::/47",),
    "v6-prefix-32": ("2001:db8::/32",),
    "no-entries": (),
    "five-hosts": ("192.0.2.1", "192.0.2.2", "192.0.2.3", "192.0.2.4", "192.0.2.5"),
    "host-and-any": ("192.0.2.10", "Any"),
    "host-and-v4-prefix-16": ("192.0.2.10", "198.51.100.0/16"),
}

INBOUND_CASES = {
    "tcp-445": _added("FPS-SMB-In-TCP", "TCP", ("445",), ("Any",)),
    "tcp-445-domain-profile-only": _added(
        "FPS-SMB-In-TCP", "TCP", ("445",), ("LocalSubnet",), profiles="Domain"),
    "tcp-5985-winrm": _added(
        "WINRM-HTTP-In-TCP", "TCP", ("5985",), ("Any",), profiles="Domain, Private"),
    "shadow-any-port": _added("RemoteDesktop-Shadow-In-TCP", "TCP", ("Any",), ("Any",)),
    "tcp-port-range": _added("Custom-Range-In-TCP", "TCP", ("1024-65535",), ("192.0.2.10",)),
    "tcp-port-keyword-rpc": _added("Custom-RPC-In-TCP", "TCP", ("RPC",), ("192.0.2.10",)),
    "tcp-port-keyword-iphttps": _added("CoreNet-IPHTTPS-In", "TCP", ("IPHTTPSIn",), ("Any",)),
    "tcp-ports-3389-and-445": _added(
        "Custom-Mixed-In-TCP", "TCP", ("3389", "445"), ("192.0.2.10",), advice=None),
    "tcp-without-ports": _added("Custom-NoPort-In-TCP", "TCP", (), ("192.0.2.10",), advice=None),
    "udp-68-other-name": _added("Custom-DHCP-In", "UDP", ("68",), ("Any",)),
    "udp-546-other-name": _added("Custom-DHCPV6-In", "UDP", ("546",), ("Any",)),
    "udp-teredo": _added("CoreNet-Teredo-In", "UDP", ("Teredo",), ("Any",)),
    "udp-5353": _added("MDNS-In-UDP", "UDP", ("5353",), ("LocalSubnet",), profiles="Private"),
    "protocol-any": _added("{6f1d2c3b-0000-4000-8000-00000000a001}", "Any", ("Any",), ("Any",)),
    "protocol-any-on-3389": _added(
        "Custom-AnyProtocol-In", "Any", ("3389",), ("192.0.2.10",), advice=None),
    "protocol-gre": _added("Custom-GRE-In", "47", ("Any",), ("Any",)),
    "allowed-udp-name-with-the-other-port": _allowed_changed(0, local_ports=("{other}",)),
    "allowed-udp-name-with-an-extra-port": _allowed_changed(0, local_ports=("{port}", "53")),
    "allowed-udp-name-with-any-port": _allowed_changed(1, local_ports=("Any",)),
    "allowed-udp-name-with-a-port-range": _allowed_changed(0, local_ports=("67-{port}",)),
    "allowed-udp-name-on-tcp": _allowed_changed(1, protocol="TCP"),
    **{f"rdp-tcp-scope-{key}": _rdp_scope(RDP_TCP, *scope) for key, scope in BAD_SCOPES.items()},
    "rdp-udp-scope-any": _rdp_scope(RDP_UDP, "Any"),
    "rdp-udp-scope-keyword-internet": _rdp_scope(RDP_UDP, "Internet"),
    "rdp-udp-scope-v4-prefix-16": _rdp_scope(RDP_UDP, "198.51.100.0/16"),
}


@pytest.mark.parametrize("case", sorted(INBOUND_CASES))
def test_ac02_inbound_rule_fails_and_the_detail_names_it(case):
    hr = _hr("render")
    facts, failing, advice = INBOUND_CASES[case](hr)
    report = hr.evaluate(facts)
    _expect(report, "FAIL", {"inbound": "FAIL"})
    detail = _item(report, "inbound").detail
    text = hr.render(report)
    for name in failing:
        assert name in detail
        assert name in text
    if advice == "scope":
        assert "Set-NetFirewallRule" in detail
        assert "-RemoteAddress" in detail
        assert "Disable-NetFirewallRule" not in detail
        assert "Disable-NetFirewallRule" not in text
    elif advice == "disable":
        assert "Disable-NetFirewallRule" in detail
        for name in failing:
            assert _advises(detail, "Disable-NetFirewallRule", name), detail
    assert _last_line(text) == "HOST REPORT: FAIL"


def test_ac02_inbound_detail_names_every_failing_rule():
    hr = _hr("render")
    facts = _valid(hr)
    for rule in (
        _rule(hr, "FPS-SMB-In-TCP", "TCP", ("445",), ("Any",)),
        _rule(hr, "RemoteDesktop-Shadow-In-TCP", "TCP", ("Any",), ("Any",)),
        _rule(hr, "Custom-DHCP-In", "UDP", ("68",), ("Any",)),
    ):
        facts = _with_rule(facts, rule)
    report = hr.evaluate(facts)
    _expect(report, "FAIL", {"inbound": "FAIL"})
    detail = _item(report, "inbound").detail
    for name in ("FPS-SMB-In-TCP", "RemoteDesktop-Shadow-In-TCP", "Custom-DHCP-In"):
        assert name in detail


def test_ac02_rdp_scope_next_to_a_rule_to_disable_is_never_advised_disable():
    # A fresh VPS: the RDP rule keeps the Windows default scope Any and the Shadow rule is on.
    hr = _hr("render")
    shadow = "RemoteDesktop-Shadow-In-TCP"
    facts = _with_changed_rule(_valid(hr), RDP_TCP, remote_addresses=("Any",))
    facts = _with_rule(facts, _rule(hr, shadow, "TCP", ("Any",), ("Any",)))
    report = hr.evaluate(facts)
    _expect(report, "FAIL", {"inbound": "FAIL"})
    detail = _item(report, "inbound").detail
    text = hr.render(report)
    for shown in (detail, text):
        assert RDP_TCP in shown and shadow in shown
        assert _advises(shown, "Set-NetFirewallRule", RDP_TCP), shown
        assert not _advises(shown, "Disable-NetFirewallRule", RDP_TCP), shown
    assert "-RemoteAddress" in detail
    assert _advises(detail, "Disable-NetFirewallRule", shadow), detail
    assert _last_line(text) == "HOST REPORT: FAIL"


# ---------------------------------------------------------------- unreadable facts


@pytest.mark.parametrize("fact", sorted(FACT_ITEM))
def test_ac02_unreadable_fact_is_unknown_when_nothing_fails(fact):
    hr = _hr("render")
    report = hr.evaluate(replace(_valid(hr), **{fact: None}))
    _expect(report, "UNKNOWN", {FACT_ITEM[fact]: "UNKNOWN"})
    assert _last_line(hr.render(report)) == "HOST REPORT: UNKNOWN"


def test_ac02_nothing_readable_is_unknown_everywhere():
    hr = _hr("render")
    report = hr.evaluate(replace(_valid(hr), **{fact: None for fact in FACT_ITEM}))
    _expect(report, "UNKNOWN", {name: "UNKNOWN" for name in ITEMS})
    assert _last_line(hr.render(report)) == "HOST REPORT: UNKNOWN"


FAIL_WITH_UNKNOWN = {
    "nla-unknown-lockout-0": (("nla_required", None), ("lockout_threshold", 0)),
    "inbound-unknown-one-secret": (("inbound_allow_rules", None), ("secret_like_files_in_repo", 1)),
    "python-unknown-cpu-1": (("python_version", None), ("cpu_count", 1)),
    "firewall-unknown-holdout": (("firewall_profiles", None), ("holdout_dir_in_repo", True)),
}


@pytest.mark.parametrize("case", sorted(FAIL_WITH_UNKNOWN))
def test_ac02_fail_outranks_unknown(case):
    hr = _hr("render")
    (unknown, _), (wrong, value) = FAIL_WITH_UNKNOWN[case]
    report = hr.evaluate(replace(_valid(hr), **{unknown: None, wrong: value}))
    _expect(report, "FAIL", {FACT_ITEM[unknown]: "UNKNOWN", FACT_ITEM[wrong]: "FAIL"})
    assert _last_line(hr.render(report)) == "HOST REPORT: FAIL"


# ---------------------------------------------------------------- what the report shows


def _documentation_only(facts):
    """Test data guard: every address in the Facts is a documentation value or an "everything"."""
    for rule in facts.inbound_allow_rules or ():
        for entry in rule.remote_addresses:
            for part in entry.split("-"):
                try:
                    network = ipaddress.ip_network(part, strict=False)
                except ValueError:
                    continue
                address = ipaddress.ip_address(part.split("/")[0])
                assert network.prefixlen == 0 or any(address in net for net in DOC_NETWORKS), entry


def _assert_no_address(text):
    assert IPV4_PATTERN.search(text) is None, text
    lowered = text.lower()
    for prefix in IPV6_DOC_PREFIXES:
        assert prefix not in lowered, text
    for stem in IPV4_DOC_STEMS:
        assert stem not in text, text


def _address_case(hr, case):
    if case == "valid":
        return _valid(hr)
    if case == "valid-with-nla-unknown":
        return replace(_valid(hr), nla_required=None)
    if case == "two-bad-scopes":
        facts = _with_changed_rule(_valid(hr), RDP_TCP, remote_addresses=BAD_SCOPES["five-hosts"])
        return _with_changed_rule(facts, RDP_UDP, remote_addresses=("192.0.2.1-192.0.2.200",))
    return INBOUND_CASES[case](hr)[0]


ADDRESS_CASES = ("valid", "valid-with-nla-unknown", "two-bad-scopes", *sorted(INBOUND_CASES))


@pytest.mark.parametrize("case", ADDRESS_CASES)
def test_ac02_report_never_shows_a_full_address(case):
    hr = _hr("render")
    facts = _address_case(hr, case)
    _documentation_only(facts)
    report = hr.evaluate(facts)
    for item in report.items:
        _assert_no_address(item.detail)
    _assert_no_address(hr.render(report))


def test_ac02_evaluate_and_render_are_repeatable():
    hr = _hr("render")
    for facts in (_valid(hr), INBOUND_CASES["rdp-tcp-scope-any"](hr)[0]):
        first, second = hr.evaluate(facts), hr.evaluate(facts)
        assert [(i.name, i.status, i.detail) for i in first.items] == [
            (i.name, i.status, i.detail) for i in second.items
        ]
        assert first.verdict == second.verdict
        assert hr.render(first) == hr.render(second)


# ---------------------------------------------------------------- runs without Windows


def _is_dynamic_import(func):
    names = ("__import__", "import_module")
    return (isinstance(func, ast.Name) and func.id in names) or (
        isinstance(func, ast.Attribute) and func.attr in names
    )


def _imports(tree):
    """(line, module, inside collect_facts) of every import, including literal dynamic imports."""
    inside = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "collect_facts":
            inside.update(id(child) for child in ast.walk(node))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = ["." * node.level + (node.module or "")]
        elif (
            isinstance(node, ast.Call)
            and _is_dynamic_import(node.func)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            modules = [node.args[0].value]
        else:
            continue
        found.extend((node.lineno, module, id(node) in inside) for module in modules)
    return found, bool(inside)


def test_ac02_windows_only_modules_are_imported_only_inside_collect_facts():
    found, has_collect_facts = _imports(_script_tree())
    assert has_collect_facts, "collect_facts must be a top-level function of host_report.py"
    outside = [
        (line, module)
        for line, module, inside in found
        if module.split(".")[0] in WINDOWS_ONLY and not inside
    ]
    assert outside == []


def test_ac02_script_imports_only_the_standard_library():
    found, _ = _imports(_script_tree())
    foreign = [
        (line, module)
        for line, module, _ in found
        if module.startswith(".") or module.split(".")[0] not in sys.stdlib_module_names
    ]
    assert foreign == []
