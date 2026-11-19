# Review ENV-001-tests round 1 · base main · head 306d5f8 + applied, uncommitted `docs/proposals/ENV-001-tests.patch` · reviewer Claude Code, fresh headless session (Opus 5.5), test reviewer under the extended role swap (PROGRESS.md)

Scope: the locked AC-02 tests `tests/acceptance/ENV-001/test_ac02_host_report.py` (patch SHA256
`6504432b…0f10`, file SHA256 `a34d5210…7023`, blob `85f287f8…c57c`) against contract
`docs/contracts/ENV-001-vps-acquisition-host.md` v1.5. `scripts/env/host_report.py` does not exist.
I wrote my first list of findings (F1–F6 below, as leads) to scratch at 2026-10-25T12:08:12Z,
**before** reading `docs/handoff/ENV-001.md`. I read the handoff after that, only to answer Q1–Q6
and to pick mutants outside the author's list (M01–M18, X01–X07). It changed no finding.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | test_ac02_host_report.py:568–619 (INBOUND_CASES, advice checks :612–618) | Every inbound case has exactly one failing rule, so the "never advise Disable for a 3389 rule" check (contract :123–124, "**ห้ามแนะนำให้ปิด**") never sees a 3389 scope failure next to a rule that needs disabling. Reviewer mutant N01 ("once any rule needs disabling, advise Disable for every failing rule") passes **186/186**. On a fresh-VPS input (RDP scope "Any" plus `RemoteDesktop-Shadow-In-TCP` on), N01 prints `Disable-NetFirewallRule -Name RemoteDesktop-UserMode-In-TCP` (scratch `driver/demo.py`). Also, nothing ties the Disable advice to the rule: mutant N17 (`Disable-NetFirewallRule -Name <Name>`, a literal placeholder, with the Name elsewhere in the entry) passes 186/186. Contract :125 fixes the form `-Name <Name>`. | The first host_report run on a VPS where the RDP scope is still the Windows default and the Shadow rule is on, the most likely failing configuration (Negative cases :160 list both). | The owner follows printed advice that turns off RDP at the Windows layer, then recovers through the provider console (contract :124). That is the exact hazard the contract calls out, and the suite cannot detect it. | Add one test (any form the author prefers): RDP_TCP scope ("Any",) plus the Shadow rule with ports Any. Assert inbound FAIL. In both the detail and render, `re.search(r"Set-NetFirewallRule\s+-Name\s+['\"]?" + re.escape(RDP_TCP), …)` is found and the same pattern with `Disable-NetFirewallRule` is not. In the detail, `Disable-NetFirewallRule\s+-Name\s+['\"]?RemoteDesktop-Shadow-In-TCP` is found. In the single-rule "disable" cases, assert `Disable-NetFirewallRule\s+-Name\s+['\"]?<that rule's Name>` (one target each, so `-Name 'A','B'` lists are not affected). | N01 and N17 each fail at least one test; the reviewer reference (V07: quoted names) still passes 186 + new. |
| F2 | Low | confirmed | test_ac02_host_report.py:487–495 | The only wrong versions are "last number + 1" and "major.minor" (convention 4). No case has a fact that is a superstring of the constant. Mutant N02 (`EXPECTED_UV in u and EXPECTED_PYTHON in p`, the natural way to accept raw `uv --version` text) passes 186/186. The demo shows N02 giving `python_env` PASS for `uv_version="0.13.40"`, `"uv 0.13.4 (0123abc 2026-01-01)"` and `python_version="3.12.150"`; the reference gives FAIL. Contract :133 says `==`. | A future uv 0.13.40/0.13.41 on the VPS, or a parse that keeps extra text. | `python_env` PASSes with a uv other than the one pinned in `docs/tooling/registry.md` (decision (ง)). | Add two WRONG cases derived from the constants: `uv_version=hr.EXPECTED_UV + "0"` and `python_version=hr.EXPECTED_PYTHON + "0"` → `python_env` FAIL. | N02 (and a `startswith` variant) fail. |
| F3 | Low | confirmed | test_ac02_host_report.py:103–104, :689–693 | `_assert_no_address` rejects only a full dotted quad (AC-06 pattern) and "2001:db8". Mutant N03 prints `192.0.2.x/32, 198.51.100.x/24, 203.0.113.x/24` in the inbound detail and passes 186/186 (demo output). Contract :122 says the FAIL detail shows the Name "(ไม่แสดงที่อยู่)" (no addresses), and :137–138 says render shows "จำนวนรายการและความยาว prefix ของ scope เท่านั้น" (only the entry count and prefix lengths). | An implementer "masks" addresses by their last octet, a common instinct. | The owner's home /24 lands in `docs/evidence/ENV-001.md` in a public repo. AC-06's grep patterns would not catch `a.b.c.x` either. The Invariant (:153) bars the home IP. | In `_assert_no_address`, also assert that none of the stems `"192.0.2"`, `"198.51.100"`, `"203.0.113"` appear (the test data use only these networks, and no rule name contains them). | N03 fails `report_never_shows_a_full_address[valid]` and others. |
| F4 | Low | confirmed | test_ac02_host_report.py:735–738 | `_is_dynamic_import` matches `__import__` as a Name and `import_module` only as an Attribute. Mutant N04 adds `from importlib import import_module` and a module-level `if sys.platform == "win32": winreg = import_module("winreg")`, and passes 186/186. Convention 11 says literal dynamic imports count. Contract :49: "Windows-only import อยู่ใน collect_facts เท่านั้น". | The classic platform-guarded import, written with an imported name. | Only the letter of the rule breaks: the module still loads on Linux, and CI (ubuntu-24.04) would load it. | Also match `ast.Name` with id `import_module`, and `ast.Attribute` with attr `__import__`. | N04 fails `test_ac02_windows_only_modules_are_imported_only_inside_collect_facts`. |
| F5 | Low | question (possible over-constraint) | test_ac02_host_report.py:102, :46–49 | `WINDOWS_ONLY` includes `ctypes`, which is cross-platform stdlib. Variant V02 (module-level `import ctypes`, winreg still inside collect_facts; loads on Linux) fails 1/186 (`…imported_only_inside_collect_facts`). The contract says "Windows-only import" (:49) without a list. It does name ctypes only as a Windows fact source (:72, :95), so the strict reading is defensible. | An implementer defines `MEMORYSTATUSEX`/`PROCESSENTRY32W` Structure classes at module scope, a common pattern. | That implementation is Linux-importable, and so faithful to the purpose, yet fails a locked test. The cost is small: move the classes into collect_facts. | Recommended: keep the convention and record it ("ctypes counts as Windows-only") in the next contract revision or as an owner note. Alternative: drop `ctypes` from `WINDOWS_ONLY`. | Owner accepts, or V02 passes after the change. |
| F6 | Low | question (possible over-constraint) | test_ac02_host_report.py:16–19, :262–278 | Statuses and the verdict are compared with `==` to str. Variant V01 (plain `enum.Enum` with values "PASS"/"FAIL"/"UNKNOWN" and `__str__`; render prints `HOST REPORT: PASS`) fails 129/186. The contract fixes only "status PASS\|FAIL\|UNKNOWN" (:106), not a type. A `StrEnum` passes (V04). | An implementer uses a plain Enum for status. | A contract-faithful choice fails every evaluate test. It is easy to avoid once the convention is known, and the handoff states it. | Recommended: keep the convention (render's text line, and every other contract field is str) and record it. Alternative: compare `getattr(x, "value", x)` in `_statuses` and `_expect`. | Owner accepts, or V01 passes after the change. |

Ready to commit red: **yes**. All 186 tests fail now for the contract reason only. A contract-only
reference passes all 186. No existing assertion needs to change, except the two conventions in F5
and F6, which I recommend keeping. F1–F4 are missing cases and can be added. Commit this file red
as it is. Then add the F1–F4 cases as an additive D-006 test patch, written by a fresh test-author
session and reviewed by a fresh session, **before** `scripts/env/host_report.py` is written, so that
those cases are red first too. Budget note: the contract allows at most 4 headless sessions, and
this path needs 2 more (test author and reviewer of the delta). If the owner does not fund that, the
implementation reviewer must run the four inputs of F1–F3 by hand (they are in
`<scratch>/e1r1/driver/demo.py`). The F4 gap is covered in practice by the Linux CI load.

Findings open: 6 (F1 Medium; F2, F3, F4 Low confirmed; F5, F6 Low questions for the owner)

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-02 | FAIL (red, as intended) | `uv run --offline pytest tests -q -p no:cacheprovider` → 186 failed, 3355 passed. All 186 fail with "AC-02: host_report not implemented (scripts/env/host_report.py is missing)". The tests would catch every AC-02 clause except the gaps in F1–F4 (see the coverage below). "Tests run on Linux": UNKNOWN until CI runs, because this machine is Windows. The test file uses only portable stdlib plus pytest, and CI runs on ubuntu-24.04 (`.github/workflows/ci.yml:19,43`). |
| AC-01, 03–07 | not in scope | Owner L4 work, implementation and evidence come later. |

## Fidelity: coverage per contract clause
"Killed by" lists the author's mutants (M/X) and mine (N). Every row has at least one test that fails when the clause is not implemented, unless marked.

| Clause (contract line) | Tests | Status |
|---|---|---|
| Constants (:50–54) | `module_constants`: EXPECTED_PYTHON "3.12.15", IGNORED_PROTOCOLS, 24/48, ALLOWED_UDP ports {68, 546}, EXPECTED_UV a non-empty str | covered. The ALLOWED_UDP names are not asserted on purpose (convention 4): a typo fails closed on the VPS (inbound FAIL names the rule) |
| Facts/Rule/Profile frozen with these fields and runtime-evaluable types (:55–68) | `records_are_frozen…` ×3, `record_annotations…` ×3 | covered. V05 (Optional/Tuple spellings, no `__future__`) passes |
| Loading recipe (:141–144) | `_load` :118–134 follows it exactly (and unregisters on a load error) | faithful |
| Fakes use the constants (:145) | `_valid` uses EXPECTED_UV/EXPECTED_PYTHON and ALLOWED_UDP. Wrong versions and the ALLOWED_UDP mutations are derived from them | faithful |
| os (:109) | 3 pass, 8 fail (2019, 2016, "Windows 10 Pro"/26100, Win10, builds ±1), 2 None | covered (X01) |
| cpu, ram, disk (:110–112) | 2 and 4 pass, 1 fails; exactly 3.5 GiB / exactly 30 GB pass, one byte less fails; None | covered (M14, X02) |
| firewall (:113–114) | 3 pass variants, 11 fail cases, None | covered (M07–M09, N05) |
| inbound: every rule whatever its profile (:115) | Domain-only 445, Domain+Private WinRM, Private mDNS; ignored rules on Domain/Public | covered (N08) |
| inbound: IGNORED_PROTOCOLS not judged | valid Facts hold ICMPv4/ICMPv6/"2"/"41" rules with Any/Any | covered (M16) |
| inbound: TCP only ("3389",) (:116) | 445, 5985, Any, range, RPC, IPHTTPSIn, ("3389","445"), () | covered (N07) |
| inbound: UDP rule (:117) | 68/546 under other names, Teredo, 5353, ALLOWED name with the other port, an extra port, Any, a range, or on TCP | covered (M02, N16) |
| inbound: other protocols incl. "Any" (:118) | Any, Any on 3389, "47" | covered (M01, N15) |
| inbound: ports Any/range/keyword (:119) | as above | covered |
| inbound: 3389 scope 1–4 entries, host / IPv4 ≥ /24 / IPv6 ≥ /48, no Any/keyword/range (:120–121) | 19 bad TCP scopes, 3 bad UDP scopes, 11 pass scopes (incl. mask /24 and /25, host bits) | covered (M03–M06, X03–X05, N06, N13) |
| inbound: FAIL detail names the rule, no address (:122) | names in detail and render; 46 address cases | covered; **partial address: F3** |
| inbound: 3389 scope failure → Set … -RemoteAddress, never Disable (:123–124) | 22 single-rule scope cases (detail and render) | single rule covered (M17); **mixed case: F1** |
| inbound: other rules → Disable-NetFirewallRule -Name <Name> (:125) | "disable" cases | covered (X06); **Name binding: F1 (N17)** |
| nla, lockout, drive_redirection, clipboard (:128–131) | False/0/11 fail, 1 and 10 pass, None | covered (M12, M13, N11, N14) |
| sync_clients (:132) | OneDrive, Dropbox, None | covered (N09) |
| python_env (:133) | uv +1, Python +1, major.minor, not synced, 3× None | covered (X07); **superstring: F2** |
| git (:134) | manager, userinfo, 2× None | covered (N10) |
| secrets, holdout (:135–136) | 1 file, True, None | covered. The `.env.example` name rule cannot be reached through evaluate (Q1) |
| Verdict precedence (:107) | 4 FAIL+UNKNOWN cases, single None, all None, valid | covered (M10) |
| None → UNKNOWN (:107) | 19 single None cases plus all-None | covered (M11, N14) |
| render's last line (:137) | PASS/FAIL/UNKNOWN on every evaluate group | covered (N12). CRLF output is accepted (V06) |
| render: no full IPv4/IPv6, only count and prefix (:137–138) | `report_never_shows_a_full_address` ×46 | covered for full addresses (M15a/b); **partial: F3** |
| Windows-only imports only in collect_facts (:49) | AST test | covered (M18); **dynamic form: F4**; **ctypes: F5** |
| stdlib only (:49) | AST test | covered |

Uncovered by AC-02 (by design or outside AC-02, not findings): the `.env.example` name rule (Q1);
the precedence of `policy_first` and the clipboard mapping (Q2: the contract gives them to the
implementer's unit tests, :146); `parse_firewall_json`; collect_facts sources, read-only and
no-socket invariants; the CLI and its exit code; the Markdown shape; an item with one None and
another wrong sub-fact (Q3); Group Policy origin advice (Q6).

## Fidelity: the author's conventions
| # | Convention | Judgement |
|---|---|---|
| 1 | `<repo>` = parents[3] | correct for `<repo>/tests/acceptance/ENV-001/<file>`. The scratch tree run confirms it |
| 2 | status/verdict compare equal to str; detail is a str; items is a tuple, one per table row, order free | The names `items`, `verdict`, `name`, `status`, `detail` and the 15 item names are fixed by the contract (:106, :109–136), and order is not checked. The str comparison is an added convention → **F6**. A str detail follows from render being text; accept |
| 3 | exact fields, runtime-evaluable annotations | fixed by the contract (:55–68, "ประเมินตอนรันไม่ได้"). Spellings are accepted (V05) |
| 4 | ALLOWED_UDP names not asserted; EXPECTED_UV any non-empty str; derived wrong versions | faithful (names are confirmed on Server later, :52). Gap → **F2** |
| 5 | "Windows 10 Pro" with build 26100 fails os | **faithful, not an over-constraint**: Negative cases (:160) say "Windows client" must fail, Windows 11 24H2 shares build 26100, and os_caption is the only other fact. A build-only check is not contract-faithful (X01). Pairing caption to build is not required (good) |
| 6 | firewall "NotConfigured"/"1" enabled and "4" action fail | faithful (:113–114 "อย่างอื่น = FAIL") |
| 7 | every failing rule named in the detail and in render; advice checked only where unambiguous | faithful. "Name ของ rule ที่ไม่ผ่าน" applies to each failing rule. The CLI prints render, and the owner acts on it ("host_report แสดงชื่อแล้วเจ้าของปิด", :196). Gap → **F1** |
| 8 | host bits = that prefix; 0 entries fail; every range fails | faithful (:66 `strict=False`, :120 "1–4 รายการ", :121 ranges) |
| 9 | no AC-06 IPv4 match (masks and 0.0.0.0 too) and no "2001:db8" anywhere | **faithful, not an over-constraint**: the contract allows only the count and prefix lengths (:138) and no addresses in the detail (:122). A faithful implementation prints neither masks nor networks. Gap → **F3** |
| 10 | last line after rstrip("\n") | faithful; CRLF accepted (V06) |
| 11 | lexical nesting inside top-level collect_facts; literal dynamic imports count | faithful to the letter "อยู่ใน collect_facts เท่านั้น". A module-level helper with a local `import winreg` fails (V03), as the letter requires. Gaps → **F4**, **F5** |
| 12 | count 0 stands for `.env.example` | the only option given evaluate's input; see Q1 |

## Recommendations on the open questions (handoff Q1–Q6)
- **Q1 `.env.example`**: option (a). The implementer adds a pure helper (for example `is_secret_like(name) -> bool`) that collect_facts uses, with unit tests: `.env.example` → False; `.env`, `.env.local`, `x.key`, `x.pem`, `x.pfx`, `x.rdp` → True. AC-01 on the VPS then exercises the real clone, which contains `.env.example`. A contract revision is not worth it for this rule. The implementation reviewer checks those unit tests.
- **Q2 policy precedence and clipboard mapping**: keep them in the implementer's unit tests, as the contract assigns (:146–147, including "policy_first ครบสี่กรณี" and the recorded clipboard values). The implementation reviewer must check the four cases and the case "policy 0 beats RDP-Tcp 1". If the owner wants independence (r5's optional note), a later locked patch can test `policy_first`: it is pure and imports on Linux.
- **Q3 one None plus another wrong sub-fact**: leave it untested in v1.5. Both readings pass the suite (V08), and the verdict is not PASS either way. Suggest FAIL when a known sub-fact fails (it gives the owner something to act on), document it in the code, and settle it in the next contract revision.
- **Q4 quoting names in advice**: the implementer should single-quote the Name (`-Name '{GUID}'`, doubling any embedded `'`), because PowerShell parses an unquoted `{…}` as a script block. The suite accepts quoted names (V07), and the F1 fix pattern allows an optional quote.
- **Q5 ALLOWED_UDP rules with scope Any**: intended. :120 applies the scope rule to 3389 rules only, and AC-01 (:163) expects PASS "ขณะที่ rule DHCP ของ Core Networking ยังเปิดอยู่" (while the default Core Networking DHCP rules stay on). The provider firewall is the outer layer for UDP 68/546. Keep.
- **Q6 other cases**: none is blocking. Numeric ICMP spellings would fall to "other protocol → FAIL" (fails closed). An empty rule tuple gives inbound PASS, which matches the contract. Windows returns exactly the three profiles, so duplicate or extra names are left open. Group Policy advice is a static line (Rule has no origin field). Add tests only when a contract revision decides these.

## Red run
`PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider`
(repo root, 2026-10-25T11:58:36Z–11:59:01Z) → exit 1, **186 failed, 3355 passed in 24.63s**. All 186
FAILED lines are in `tests/acceptance/ENV-001/test_ac02_host_report.py` (0 outside it). The message
"AC-02: host_report not implemented (scripts/env/host_report.py is missing)" occurs 186 times, and
there are no assertion (`E `) lines. This matches the handoff (186/3355). 186 = 1+1+3+3+1+23+37+43+1+19+1+4+46+1+1+1.

## Satisfiability
Scratch tree `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/e1r1/tree`.
The test was recreated with the Write tool from the patch's content and has SHA256
`a34d5210d0e6cb0e1aac8eeb9963181e664ff9c517e1f6fb70a106dd327b7023` (785 lines). My own reference
`scripts/env/host_report.py` was written from the contract only, before I read the handoff: str
statuses; `ctypes` and `winreg` imported inside collect_facts; helpers `policy_first` and
`parse_firewall_json`. Its pristine copy is `e1r1/reference_host_report.py`, SHA256 `d0c1c263…46fc`.
`uv run --offline --no-sync --project C:/Users/MSI/Desktop/โปรเจคต่างๆ/Sochron1k python -I -B -m pytest <tree>/tests/acceptance/ENV-001 -q -p no:cacheprovider --rootdir <tree>`
(literal paths, from the repo root, outer `timeout -k 10 900`, PYTHONDONTWRITEBYTECODE=1) →
**186 passed in 0.16s** (12:06:23Z). No test is unsatisfiable. The only contract-faithful choices
that fail are the conventions in F5 (V02) and F6 (V01).

## Reviewer mutants and variants (none in the author's list)
Driver `e1r1/driver/mutants.py` applies one change at a time to the reference. Each run is the same
pytest command with `--tb=no -rf`, run from the repo root by the venv interpreter under one outer
`timeout -k 10 900`. The driver restores the reference at the end. Run 2026-10-25T12:10:24Z–12:10:35Z;
the results are in `e1r1/driver/results.json`.

| ID | Wrong implementation | Result | First killing test |
|---|---|---|---|
| N01 | Disable advice for every failing rule once any rule needs disabling | **survives (186 passed)** | gap → F1 |
| N02 | python_env by substring | **survives** | gap → F2 |
| N03 | partial IPv4 (`a.b.c.x/nn`) in the scope summary | **survives** | gap → F3 |
| N04 | module-level `import_module("winreg")` via `from importlib import import_module` | **survives** | gap → F4 |
| N05 | firewall `any()` over profiles | 7 failed | wrong[firewall-domain-default-numeric] |
| N06 | scope parsed with `strict=True` | 1 failed | boundary[scope-v4-24-with-host-bits] |
| N07 | TCP: "3389" in ports (subset) | 1 failed | inbound[tcp-ports-3389-and-445] |
| N08 | only rules on Public/Any judged | 3 failed | inbound[tcp-445-domain-profile-only] |
| N09 | sync_clients: only OneDrive counts | 1 failed | wrong[sync-dropbox-installed] |
| N10 | git: userinfo ignored | 1 failed | wrong[git-remote-with-userinfo] |
| N11 | lockout `< 10` | 1 failed | boundary[lockout-10] |
| N12 | render footer after the verdict line | 105 failed | valid host |
| N13 | IPv4 range accepted inside one /24 | 2 failed | inbound[rdp-tcp-scope-range-two-hosts] |
| N14 | nla None → FAIL | 3 failed | unknown[nla_required] |
| N15 | every numeric protocol ignored | 1 failed | inbound[protocol-gre] |
| N16 | ALLOWED_UDP name with any allowed port | 1 failed | inbound[allowed-udp-name-with-the-other-port] |
| N17 | Disable advice with a literal `<Name>` | **survives** | gap → F1 |

Contract-faithful variants (all should pass): V04 StrEnum → 186 passed. V05 Optional/Tuple without
`__future__` → 186 passed. V06 CRLF render → 186 passed. V07 quoted Names → 186 passed. V08 Q3
"FAIL first" reading → 186 passed. Probes: V01 plain Enum → 129 failed (F6). V02 module-level
ctypes → 1 failed (F5). V03 module-level helper with a local `import winreg` → 1 failed, as the
letter of :49 requires (no finding).

## Red-flag scan
`bash scripts/controls/red-flags.sh main` (12:11:08Z) → exit 0, "Pattern groups with hits: 0".
Files changed since the merge-base `a11bff7`: 11 docs files from the PR #23 history. Deleted or
renamed tests: none. Control files touched: none. Untracked (listed, **not scanned**):
`docs/handoff/ENV-001.md`, `tests/acceptance/ENV-001/test_ac02_host_report.py`. Because the scan
skips untracked files, I applied its patterns to the test file with Grep. Skip/focus, type-ignore,
lint-disable, swallowed errors, secrets, secret-like assignment, destructive commands,
client-exposed names, order surface and placeholder words: **no matches**.

## r5 F52/F53 recheck (contract DoR :219 asks the AC-02 test reviewer)
- F52: closed in the text. (a) :86–87 now reads "ใช้กับ nla_required, drive_redirection และค่า fDisableClip ของ clipboard". (b) :90–93 maps the text policy separately with the recorded values (off → True, text → True, text+images → False; absent → result of (1)). The AC-02 tests do not touch it; it is assigned to unit tests (see Q2).
- F53: closed in the text. :147–149 says the fixture is the output of the same PowerShell command, kept as one module constant named in the fixture header, trimmed, with RFC 5737/3849 addresses and no owner paths or app names. AC-06 (:168) searches the fixture, including `:\\`.

## Checked, nothing found (and how)
- Hashes: `sha256sum` patch `6504432b…0f10` and file `a34d5210…7023`; `git hash-object` gives `85f287f8…c57c`. All match the brief and the handoff. `git apply -R --check docs/proposals/ENV-001-tests.patch`, run alone → exit 0, no output.
- The only locked-path change: `node scripts/controls/check-locked-paths.mjs main` → "!! locked A tests/acceptance/ENV-001/test_ac02_host_report.py", 1 change (FAIL until the owner labels it, as expected). `git status`: untracked `docs/handoff/ENV-001.md` and the test file only. My first Bash command (read-only) triggered the post-run detector with exactly that file, which was already present before this session. I verified its hashes and continued under CLAUDE.md's post-run rule.
- File hygiene: ASCII (0 non-printable bytes), 0 CR bytes, one trailing newline, 34235 bytes. Every IPv4 literal is in 192.0.2/24, 198.51.100/24 or 203.0.113/24, or is a mask or 0.0.0.0; every IPv6 literal is in 2001:db8::/32. There are no 7+ digit numbers (the AC-06 patterns applied to the test file).
- Determinism: no clock, randomness, network or filesystem writes. Parametrize ids are sorted. Item order is never compared, and the status comparison uses a dict. `evaluate_and_render_are_repeatable` passes on the reference.
- Windows vs Linux: paths come from `Path(__file__).resolve()`. The source is read as UTF-8 and `ast.parse` accepts CRLF. `sys.stdlib_module_names` is the same on every platform. The test imports no Windows module. CI runs on ubuntu-24.04, so a module that raises at load on Linux fails every test there.
- Loading and caching: `_LOADED` keeps the module object, and `get_type_hints(…, globalns=vars(hr))` does not depend on `sys.modules["host_report"]`. A later re-registration by `tests/unit/env/` cannot break these tests. No other `test_ac02_host_report.py` basename exists under `tests/` (Glob).
- Wording the contract does not fix: only the contract's command strings (`Set-NetFirewallRule`, `-RemoteAddress`, `Disable-NetFirewallRule`) and the rule Names are matched as substrings. No detail wording or item order is checked, and no Item/Report field beyond name/status/detail/items/verdict is read.
- Tests that could pass for the wrong reason: the valid Facts make every ignored-protocol rule fail if it were judged. Each "still valid" case changes one value. `_expect` pins all 15 statuses, so a change cannot leak into another item unnoticed. `_documentation_only` guards the test data itself.

## Not checked (and why)
- The tests on Linux: UNKNOWN until CI runs (this host is Windows 11).
- The real ProductName strings on Server 2022/2025, and the default RemoteAddress of `CoreNet-DHCP-In`/`CoreNet-DHCPV6-In` on Server: no Server host is available; this belongs to AC-01 and the runbook.
- Whether `import ctypes.wintypes` works at module level on Linux 3.12 (relevant only if F5 is changed): no Linux interpreter here.
- collect_facts, the CLI, the unit tests in `tests/unit/env/` and the runbook: they do not exist yet and are out of scope for this review.
- I did not read the author's scratch reference or mutant trees (`…/scratchpad/e1t/`), so my reference stays independent.
