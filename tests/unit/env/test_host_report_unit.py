"""Implementer's unit tests for scripts/env/host_report.py (ENV-001 v1.5).

They cover what the contract gives to unit tests and the locked AC-02 tests cannot reach:
parse_firewall_json on the captured sample (review r5 F53), policy_first's four cases and the
clipboard mapping (contract: collect_facts sources), the `.env.example` name rule (tests review r1
Q1), advice for mixed failures (tests review r1 F1), quoting, and the CLI. The script is loaded by
the contract's recipe; the fixture module beside this file is loaded by path the same way.
"""

import importlib.util
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parents[2] / "scripts" / "env" / "host_report.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


hr = _load("host_report", SCRIPT)
sample = _load("env_firewall_sample", HERE / "firewall_sample.py")
IPV4 = re.compile(r"\b([0-9]{1,3}\.){3}[0-9]{1,3}\b")


def rule(name, protocol, ports, scope):
    return hr.Rule(name=name, protocol=protocol, profiles="Any", local_ports=tuple(ports),
                   remote_addresses=tuple(scope))


RDP = rule("RemoteDesktop-UserMode-In-TCP", "TCP", ("3389",), ("192.0.2.10",))
SHADOW = rule("RemoteDesktop-Shadow-In-TCP", "TCP", ("Any",), ("Any",))


def valid_facts(rules=(RDP,)):
    return hr.Facts(
        os_caption="Windows Server 2025 Datacenter", os_build=26100, cpu_count=2,
        visible_ram_bytes=8 * 2**30, repo_drive_free_bytes=80 * 10**9,
        inbound_allow_rules=tuple(rules),
        firewall_profiles=tuple(hr.Profile(name=n, enabled="True", default_inbound_action="Block")
                                for n in ("Domain", "Private", "Public")),
        nla_required=True, lockout_threshold=5, drive_redirection_disabled=True,
        clipboard_files_to_client_blocked=True, sync_clients=(), uv_version=hr.EXPECTED_UV,
        python_version=hr.EXPECTED_PYTHON, project_synced=True, git_credential_helpers=(),
        remote_has_userinfo=False, secret_like_files_in_repo=0, holdout_dir_in_repo=False,
    )


def detail(report, name):
    return next(item.detail for item in report.items if item.name == name)


# ---- parse_firewall_json -------------------------------------------------------------------------
def test_captured_sample_parses_as_windows_returned_it():
    rules, profiles = hr.parse_firewall_json(sample.SAMPLE)
    assert len(rules) == 10 and [p.name for p in profiles] == ["Domain", "Private", "Public"]
    by_name = {r.name: r for r in rules}
    assert by_name["CoreNet-DHCP-In"] == rule("CoreNet-DHCP-In", "UDP", ("68",), ("Any",))
    assert by_name["NVS-FrameServer-In-TCP-NoScope"].local_ports == ("554", "8554-8558")
    assert by_name["CoreNet-ICMP6-RA-In"].local_ports == ("RPC",)
    assert by_name["WFDPRINT-SPOOL-In-Active"].profiles == "Public"
    assert all(p.enabled == "True" and p.default_inbound_action == "Block" for p in profiles)


def test_sample_rules_are_judged_as_the_contract_says():
    rules, profiles = hr.parse_firewall_json(sample.SAMPLE)
    report = hr.evaluate(replace(valid_facts((RDP, *rules)), firewall_profiles=profiles))
    text = detail(report, "inbound")
    for failing in ("DeliveryOptimization-TCP-In", "NVS-FrameServer-In-TCP-NoScope",
                    "MDNS-In-UDP-Private-Active", "WFDPRINT-SPOOL-In-Active"):
        assert f"Disable-NetFirewallRule -Name '{failing}'" in text
    for kept in ("CoreNet-DHCP-In", "CoreNet-DHCPV6-In", "CoreNet-ICMP6", "CoreNet-ICMP4", "CoreNet-IGMP",
                 "CoreNet-IPv6", "RemoteDesktop-UserMode-In-TCP"):
        assert kept not in text
    assert detail(report, "firewall").startswith("Domain, Private, Public enabled")


def test_numeric_enums_never_pass():
    data = json.loads(sample.SAMPLE)
    data["profiles"][0]["enabled"] = 1  # what ConvertTo-Json writes without .ToString()
    rules, profiles = hr.parse_firewall_json(json.dumps(data))
    assert rules is not None and profiles is None
    data = json.loads(sample.SAMPLE)
    data["rules"][0]["protocol"] = 17
    assert hr.parse_firewall_json(json.dumps(data))[0] is None


def test_scalars_wrappers_bom_and_broken_json():
    data = json.loads(sample.SAMPLE)
    data["rules"][0]["local_ports"] = "68"
    data["rules"][0]["remote_addresses"] = "Any"
    data["rules"] = {"value": data["rules"], "Count": len(data["rules"])}
    rules, _ = hr.parse_firewall_json("\ufeff" + json.dumps(data))
    assert rules[0].local_ports == ("68",) and rules[0].remote_addresses == ("Any",)
    assert hr.parse_firewall_json("not json") == (None, None)
    assert hr.parse_firewall_json("[]") == (None, None)
    data = json.loads(sample.SAMPLE)
    del data["rules"][0]["profiles"]
    assert hr.parse_firewall_json(json.dumps(data))[0] is None


def test_firewall_script_is_the_contract_command():
    script = hr.FIREWALL_SCRIPT
    for needle in ("Get-NetFirewallRule -PolicyStore ActiveStore -Direction Inbound -Action Allow -Enabled True",
                   "Get-NetFirewallPortFilter", "Get-NetFirewallAddressFilter",
                   "Get-NetFirewallProfile -PolicyStore ActiveStore", ".ToString()", "-Depth 4 -Compress"):
        assert needle in script


# ---- registry precedence and the clipboard mapping ------------------------------------------------
@pytest.mark.parametrize("policy, winstation, expected", [
    (1, 0, True), (0, 1, False), (None, 1, True), (None, 0, False), (None, None, None), (1, None, True),
])
def test_policy_first(policy, winstation, expected):
    assert hr.policy_first(policy, winstation) is expected


@pytest.mark.parametrize("disable_clip, level, expected", [
    (True, None, True), (True, 4, True),
    (False, 0, True), (False, 1, True), (False, 2, False), (False, 4, False),
    (None, 1, True), (False, None, False), (None, None, None),
])
def test_clipboard_mapping(disable_clip, level, expected):
    assert hr.clipboard_blocks_files(disable_clip, level) is expected


# ---- text parsers ---------------------------------------------------------------------------------
NET_ACCOUNTS = """Force user logoff how long after time expires?:       Never
Minimum password age (days):                          0
Lockout threshold:                                    {value}
Lockout duration (minutes):                           10
The command completed successfully.
"""


def test_lockout_parse():
    assert hr.parse_lockout(NET_ACCOUNTS.format(value="Never")) == 0
    assert hr.parse_lockout(NET_ACCOUNTS.format(value="5")) == 5
    assert hr.parse_lockout("Seuil de verrouillage : 5") is None
    assert hr.parse_lockout(NET_ACCOUNTS.format(value="five")) is None


def test_uv_version_parse():
    assert hr.parse_uv_version("uv 0.13.5 (abcdef0 2026-10-20 x86_64-pc-windows-msvc)\n") == "0.13.5"
    assert hr.parse_uv_version("error: no such command") is None


# `git config --show-origin --get-regexp "^credential\..*helper$"` lines (contract v1.6, review r1 F1)
SYSTEM = "file:C:/Program Files/Git/etc/gitconfig\tcredential.helper manager\n"
GLOBAL_RESET = "file:C:/Users/owner/.gitconfig\tcredential.helper \n"
URL_HELPER = "file:C:/Users/owner/.gitconfig\tcredential.https://github.com.helper !gh auth git-credential\n"


def test_git_helpers_follow_the_reset_rule():
    assert hr.parse_git_helpers(SYSTEM) == ("manager",)
    assert hr.parse_git_helpers(SYSTEM + GLOBAL_RESET) == ()
    assert hr.parse_git_helpers("") == ()


def test_reset_clears_only_earlier_helpers_of_the_same_key():
    # M10: a reset must not clear helpers that come after it, nor helpers of another key.
    store = "file:C:/Users/owner/.gitconfig\tcredential.helper store\n"
    assert hr.parse_git_helpers(SYSTEM + GLOBAL_RESET + store) == ("store",)
    assert hr.parse_git_helpers(URL_HELPER + GLOBAL_RESET) == ("!gh auth git-credential",)


def test_url_scoped_helper_is_found():
    # F1 (a): `gh auth setup-git` writes credential.https://github.com.helper.
    assert hr.parse_git_helpers(SYSTEM + GLOBAL_RESET + URL_HELPER) == ("!gh auth git-credential",)


GLOBAL = "file:C:/Users/owner/.gitconfig\t"
MULTI_LINE = SYSTEM + GLOBAL + "credential.helper \n!probe\n"  # a value that starts with a newline


@pytest.mark.parametrize("stdout, expected", [
    # Review r2 F18, the cases of its driver/git_probe.py: git resets only on an exactly empty value.
    (SYSTEM + GLOBAL + "credential.helper  \n", ("manager", " ")),  # A1: one space
    (SYSTEM + GLOBAL + "credential.helper    \n", ("manager", "   ")),  # A: three spaces
    (SYSTEM + GLOBAL + "credential.helper \t\n", ("manager", "\t")),  # I: a tab
    (MULTI_LINE, None),  # B: the second line of the value has no tab
    (SYSTEM + GLOBAL + "credential.helper \n\n", None),  # a value that is one newline
    (GLOBAL + "credential.https://example.invalid/Foo.helper store\n"
     + GLOBAL + "credential.https://example.invalid/foo.helper \n", ("store",)),  # D: URL paths are case-sensitive
    (SYSTEM + GLOBAL_RESET, ()),  # A0: an exactly empty value is git's reset
])
def test_only_an_exactly_empty_value_resets(stdout, expected):
    assert hr.parse_git_helpers(stdout) == expected


def test_a_key_without_a_value_counts_as_a_helper():
    # F18 case C: "[credential] helper" with no "=" prints the key alone; git then refuses to run,
    # and the parser keeps it as a helper (fails closed).
    helpers = hr.parse_git_helpers(SYSTEM + GLOBAL + "credential.helper\n")
    assert helpers is not None and len(helpers) == 2 and helpers[0] == "manager"


@pytest.mark.parametrize("returncode, stdout, expected", [
    (0, SYSTEM, ("manager",)), (1, "", ()), (1, "error text", None), (128, "", None), (None, "", None),
    (0, MULTI_LINE, None),  # F18: a value that cannot be read is unknown
])
def test_git_exit_codes(returncode, stdout, expected):
    # M20: only "no key matched" (exit 1, nothing printed) means no helper.
    assert hr.helpers_from_git(returncode, stdout) == expected


@pytest.mark.parametrize("returncode, expected", [(0, True), (1, False), (2, False), (None, None)])
def test_uv_check_exit_codes(returncode, expected):
    # M21: uv that cannot run is unknown, never in sync.
    assert hr.synced_from_uv(returncode) is expected


@pytest.mark.parametrize("urls, expected", [
    (["https://github.com/faztycoding/Sochron1k.git"], False),
    (["https://someone@github.com/faztycoding/Sochron1k.git"], True),
    (["git@github.com:faztycoding/Sochron1k.git"], True),
    (["https://github.com/x/y.git", "https://u:p@github.com/x/y.git"], True),  # a push URL or a second remote
    ([], False),
])
def test_remote_userinfo(urls, expected):
    # URLs as `git remote get-url --all` and `--push --all` print them: insteadOf is already applied (F1 b).
    assert hr.any_userinfo(urls) is expected


def test_git_detail_names_kinds_not_values():
    # F7 (a): a helper value can hold a path or an inline token.
    secret = "!f() { echo password=hunter2; }; f"
    facts = replace(valid_facts(), git_credential_helpers=("store --file C:/Users/owner/.git-credentials", secret))
    text = detail(hr.evaluate(facts), "git")
    assert "2 credential helper(s)" in text and "store, other" in text
    assert "hunter2" not in text and ":/Users" not in text
    assert 'git config --global credential.helper --% ""' in text  # F2: works in Windows PowerShell 5.1


@pytest.mark.parametrize("userinfo", [False, True])
def test_git_advice_ends_with_the_command(userinfo):
    # Review r2 F19: after `--%` PowerShell passes the rest of the line to git, so nothing may follow it.
    facts = replace(valid_facts(), git_credential_helpers=("manager",), remote_has_userinfo=userinfo)
    text = detail(hr.evaluate(facts), "git")
    assert text.endswith(' -> git config --global credential.helper --% ""')
    assert text.count("--%") == 1


# ---- secrets and holdout (tests review r1 Q1) --------------------------------------------------------
@pytest.mark.parametrize("name, expected", [
    (".env.example", False), (".ENV.EXAMPLE", False), (".env", True), (".env.local", True), (".ENV", True),
    ("id.key", True), ("cert.pem", True), ("store.PFX", True), ("vps.rdp", True), ("env.txt", False),
    ("README.md", False), (".env.example.bak", True),  # M23: only the exact name is exempt
])
def test_secret_like_names(name, expected):
    assert hr.is_secret_like(name) is expected


def test_counting_skips_git_and_venv(tmp_path):
    (tmp_path / ".env.example").write_text("NAME=\n")
    assert hr.count_secret_like(tmp_path) == 0
    for folder in (".git", ".venv"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "inner.pem").write_text("x")
    assert hr.count_secret_like(tmp_path) == 0
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "vps.rdp").write_text("x")
    assert hr.count_secret_like(tmp_path) == 1
    assert hr.has_holdout_dir(tmp_path) is False
    (tmp_path / "data" / "Holdout").mkdir(parents=True)
    assert hr.has_holdout_dir(tmp_path) is True


def test_other_dot_folders_are_searched(tmp_path):
    # M22: only .git and .venv are skipped.
    for folder in (".ssh", ".vscode"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "id.key").write_text("x")
    assert hr.count_secret_like(tmp_path) == 2


def test_walk_cannot_pass_by_skipping(tmp_path, monkeypatch):
    # F8: a missing root or a folder that cannot be listed is an error (UNKNOWN), not zero.
    with pytest.raises(OSError):
        hr.count_secret_like(tmp_path / "no-such-folder")
    with pytest.raises(OSError):
        hr.has_holdout_dir(tmp_path / "no-such-folder")
    seen = {}

    def walk(root, onerror=None):
        seen["onerror"] = onerror
        onerror(PermissionError("listing denied"))
        return iter(())

    monkeypatch.setattr(hr.os, "walk", walk)
    with pytest.raises(PermissionError):
        hr.count_secret_like(tmp_path)
    assert seen["onerror"] is not None


# ---- advice (tests review r1 F1, Q4) -----------------------------------------------------------------
def test_mixed_failures_never_advise_disabling_the_rdp_rule():
    open_rdp = replace(RDP, remote_addresses=("Any",))
    report = hr.evaluate(valid_facts((open_rdp, SHADOW)))
    text = detail(report, "inbound") + hr.render(report)
    assert "Set-NetFirewallRule -Name 'RemoteDesktop-UserMode-In-TCP' -RemoteAddress" in text
    assert "Disable-NetFirewallRule -Name 'RemoteDesktop-UserMode-In-TCP'" not in text
    assert "Disable-NetFirewallRule -Name 'RemoteDesktop-Shadow-In-TCP'" in text


def test_rules_carrying_3389_get_set_advice():
    mixed_ports = rule("Custom-Mixed-In-TCP", "TCP", ("3389", "445"), ("192.0.2.10",))
    any_protocol = rule("Custom-AnyProtocol-In", "Any", ("3389",), ("192.0.2.10",))
    text = detail(hr.evaluate(valid_facts((RDP, mixed_ports, any_protocol))), "inbound")
    assert "Set-NetFirewallRule -Name 'Custom-Mixed-In-TCP' -LocalPort 3389" in text
    assert "Set-NetFirewallRule -Name 'Custom-AnyProtocol-In' -Protocol TCP" in text
    assert "Disable-NetFirewallRule" not in text


def test_names_are_single_quoted_for_powershell():
    guid = rule("{6f1d2c3b-0000-4000-8000-00000000a001}", "TCP", ("445",), ("Any",))
    odd = rule("Bob's rule", "TCP", ("445",), ("Any",))
    text = detail(hr.evaluate(valid_facts((RDP, guid, odd))), "inbound")
    assert "Disable-NetFirewallRule -Name '{6f1d2c3b-0000-4000-8000-00000000a001}'" in text
    assert "Disable-NetFirewallRule -Name 'Bob''s rule'" in text


def test_advice_notes_are_powershell_comments():
    # F17: "(keep RDP)" after a command was a parse error or ran as a command in PowerShell 5.1.
    mixed_ports = rule("Custom-Mixed-In-TCP", "TCP", ("3389", "445"), ("192.0.2.10",))
    any_protocol = rule("Custom-AnyProtocol-In", "Any", ("3389",), ("192.0.2.10",))
    text = detail(hr.evaluate(valid_facts((RDP, mixed_ports, any_protocol))), "inbound")
    assert "-LocalPort 3389  # keeps RDP" in text and "-Protocol TCP  # keeps RDP" in text
    assert "(keep" not in text
    assert "Group Policy" in text


def test_names_with_paths_or_addresses_are_masked():
    # F7 (b): Query User rules carry program paths; a provider Name can carry an address.
    query_user = rule("TCP Query User{5A0E}C:\\users\\owner\\app.exe", "TCP", ("445",), ("Any",))
    provider = rule("Allow-mgmt-203.0.113.5", "TCP", ("5985",), ("Any",))
    report = hr.evaluate(valid_facts((RDP, query_user, provider)))
    text = hr.render(report)
    assert ":\\" not in text and "owner" not in text and IPV4.search(text) is None
    assert "'TCP Query User{5A0E}<path>'" in text and "'Allow-mgmt-x.x.x.x'" in text
    assert "is not printed" in text


@pytest.mark.parametrize("scope, ok", [
    (("::ffff:192.0.2.0/120",), True),
    (("::ffff:0:0/96",), False),  # every IPv4 address, written as mapped IPv6
    (("64:ff9b::/96",), False),  # NAT64
    (("::/64",), False),  # covers the IPv4-compatible and mapped blocks
    (("2001:db8:1234::/48",), True),
    (("203.0.113.0/255.255.255.0",), True),
    (("203.0.113.0/0.0.0.255",), False),  # a hostmask, read by Python as /24
])
def test_scope_forms_of_contract_v1_6(scope, ok):
    # F10 (owner, 2026-10-25): mapped, compatible and NAT64 IPv6 need /120; masks must be netmasks.
    report = hr.evaluate(valid_facts((replace(RDP, remote_addresses=scope),)))
    status = next(i.status for i in report.items if i.name == "inbound")
    assert status == ("PASS" if ok else "FAIL")


def test_warning_when_no_tcp_3389_rule_passes():
    # F3: before any Disable advice is followed, RDP itself must be fixed.
    open_rdp = replace(RDP, remote_addresses=("Any",))
    assert "no passing TCP 3389 rule" in detail(hr.evaluate(valid_facts((open_rdp, SHADOW))), "inbound")
    assert "no passing TCP 3389 rule" not in detail(hr.evaluate(valid_facts()), "inbound")


@pytest.mark.parametrize("profiles", [
    (("Domain", "False"), ("Private", "True"), ("Public", "True"), ("Domain", "True")),  # M33: duplicate
    (("Domain", "True"), ("Private", "True"), ("Public", "False"), ("Public", "True")),
    (("Domain", "True"), ("Private", "True"), ("Public", "True"), ("Extra", "False")),
])
def test_every_profile_entry_is_judged(profiles):
    # F6: the last entry of a name must not hide an earlier disabled one; extras fail too.
    facts = replace(valid_facts(), firewall_profiles=tuple(
        hr.Profile(name=n, enabled=e, default_inbound_action="Block") for n, e in profiles))
    assert next(i.status for i in hr.evaluate(facts).items if i.name == "firewall") == "FAIL"


def test_firewall_script_refuses_duplicate_instance_ids():
    # F5: a duplicate InstanceID could pair a rule with another rule's filters; the script throws (UNKNOWN).
    assert "duplicate rule InstanceID" in hr.FIREWALL_SCRIPT


def test_versions_compare_exactly():
    report = hr.evaluate(replace(valid_facts(), uv_version=hr.EXPECTED_UV + "0",
                                 python_version=hr.EXPECTED_PYTHON + "0"))
    assert next(i.status for i in report.items if i.name == "python_env") == "FAIL"


def test_report_shows_prefix_lengths_not_addresses():
    scope = ("192.0.2.10", "198.51.100.0/24", "203.0.113.0/255.255.255.0", "2001:db8:1234::/48")
    report = hr.evaluate(valid_facts((replace(RDP, remote_addresses=scope),)))
    text = hr.render(report)
    assert "4 entries (/32, /24, /24, /48)" in text
    assert IPV4.search(text) is None
    # Three- and two-octet stems too: a masked address such as 198.51.x.x still leaks the network
    # (tests review r2 F7, left to the implementer's checks).
    for stem in ("192.0.2", "198.51.100", "203.0.113", "192.0.", "198.51.", "203.0.", "2001:db8"):
        assert stem not in text
    assert text.isascii()


# ---- CLI -----------------------------------------------------------------------------------------------
def test_cli_refuses_off_windows(monkeypatch, capsys):
    monkeypatch.setattr(hr.sys, "platform", "linux")
    assert hr.main(["--role", "acquisition", "--repo", "."]) == 2
    assert "VPS only" in capsys.readouterr().err


@pytest.mark.parametrize("facts, code, last", [
    (valid_facts(), 0, "HOST REPORT: PASS"),
    (replace(valid_facts(), cpu_count=1), 1, "HOST REPORT: FAIL"),
    (replace(valid_facts(), cpu_count=None), 1, "HOST REPORT: UNKNOWN"),
])
def test_cli_exit_code_follows_the_verdict(facts, code, last, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(hr.sys, "platform", "win32")
    seen = []
    monkeypatch.setattr(hr, "collect_facts", lambda repo: seen.append(repo) or facts)
    assert hr.main(["--role", "acquisition", "--repo", str(tmp_path)]) == code
    assert capsys.readouterr().out.rstrip("\n").splitlines()[-1] == last
    assert seen == [tmp_path.resolve()]


def test_cli_accepts_only_the_acquisition_role():
    with pytest.raises(SystemExit) as exc:
        hr.main(["--role", "research", "--repo", "."])
    assert exc.value.code == 2
