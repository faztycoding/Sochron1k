# Review ENV-001-tests round 2 · base main · head 995815f + applied, uncommitted `docs/proposals/ENV-001-tests-r2.patch` · reviewer Claude Code, fresh headless session (Opus 5.5), test reviewer r2 under the extended role swap (PROGRESS.md)

Scope: a narrow re-check of review r1's F1–F4 (`docs/reviews/ENV-001-tests-r1.md`) and of the
additive patch that answers them. The patch (SHA256 `fbc81434…dae8`) changes only
`tests/acceptance/ENV-001/test_ac02_host_report.py`: base blob `85f287f8…c57c` (committed in
`5f4f527`) → SHA256 `a46fe787…e462`, blob `25abb32c…c278`. I checked it against contract
`docs/contracts/ENV-001-vps-acquisition-host.md` v1.5. `scripts/env/host_report.py` does not exist,
and I read no implementation. I did not read r1's or the author's scratch trees (`e1r1/`, `e1t2/`).
I wrote my first list of findings to scratch (`e1r2/notes/first-findings.md`, 2026-10-25T13:41:30Z)
**before** reading the "Round 2 (tests r2)" section of `docs/handoff/ENV-001.md`. After reading it, I
added one probe (N01L, the author's disclosed limit) and fixed one count in my notes (78 identical
statements, not 77). It changed no finding. F5 and F6 stay as the owner decided on 2026-10-25.

## r1 findings re-check (F1–F4)
| r1 ID | Sev | Status | Proof of fix (as r1 asked) | Evidence this round | Residual |
|---|---|---|---|---|---|
| F1 | Medium | **closed** | "N01 and N17 each fail at least one test; the reviewer reference (V07: quoted names) still passes 186 + new" | New test `test_ac02_rdp_scope_next_to_a_rule_to_disable_is_never_advised_disable` (:660–676) is the fresh-VPS input r1 named: RDP_TCP scope ("Any",) plus the Shadow rule, ports Any. It asserts inbound FAIL; in both the detail and render, `Set-NetFirewallRule -Name <RDP>` is present and `Disable-NetFirewallRule -Name <RDP>` is absent; in the detail, `Disable-NetFirewallRule -Name RemoteDesktop-Shadow-In-TCP` is present. The disable cases now bind the Name (:639–640) through `_advises` (:296–299, optional ' or " quote, one Name per command). My **N01** → 1 failed (:672). My **N17** → 19 failed (the 18 single-rule disable cases at :640, plus the mixed test). Extra binding mutants: **N18** (Disable bound to the first failing rule's Name) → 1 failed (:673); **N19** (Set bound to the last failing rule's Name) → 1 failed (:672). My reference uses single quotes (V07, single) → 189 passed. V07d (double quotes) and V07u (unquoted) → 189 passed each. | A Disable command that lists several Names, with the RDP Name not first (**N01L**, disclosed in handoff "Known limits"), survives: 189 passed. The same list in rule order, RDP first (N01Lu), fails at :673. The contract does not fix a detail layout, so this cannot be tested without over-constraint (see "Manual checks"). |
| F2 | Low | **closed** | "N02 (and a startswith variant) fail" | `WRONG` gains `python-env-uv-longer-version` (`EXPECTED_UV + "0"`) and `python-env-python-longer-version` (`EXPECTED_PYTHON + "0"`) (:511–514), exactly r1's minimal fix. My **N02** (substring) and **N02s** (`startswith`) → 2 failed each: exactly those two ids, at `_expect` (:287). The contract's `==` (:133) passes (my reference). | none |
| F3 | Low | **closed** (per its proof) | "N03 fails `report_never_shows_a_full_address[valid]` and others" | `IPV4_DOC_STEMS` (:114) is checked in `_assert_no_address` (:735–736), across all 46 address cases. My **N03** (`a.b.c.x/nn` in the scope summary) → 13 failed, including `[valid]`, `[valid-with-nla-unknown]` and `[two-bad-scopes]` (:736). No rule Name or other one-line literal in the file contains a stem (`hygiene.py`). | The two-octet form `a.b.x.x/nn` survives → **F7** (new, Low) |
| F4 | Low | **closed** | "N04 fails `test_ac02_windows_only_modules_are_imported_only_inside_collect_facts`" | `_is_dynamic_import` (:778–782) now matches `__import__` and `import_module` both as a Name and as an Attribute. My **N04** (module-level `from importlib import import_module` + guarded `import_module("winreg")`) → 1 failed (:819, `[(14, 'winreg')]`). **N04c** (`builtins.__import__`) → 1 failed. **N04d** (`importlib.import_module`, the 5f4f527 form) → still 1 failed. | An aliased name (`import_module as load_module`, N04b) survives. This is not a finding: it breaks only the letter of :49, a guarded alias still loads on Linux, an unguarded one fails CI's Linux load, and static detection cannot be complete (`getattr`, `exec`). |
| F5, F6 | Low (questions) | closed by owner decision (conventions kept) | – | Unchanged by the patch: `WINDOWS_ONLY` (still with `ctypes`), `_statuses` and `_expect` are AST-identical to `5f4f527`. | – |

## New findings
| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F7 | Low | confirmed | test_ac02_host_report.py:114, :730–736 (convention 9, :46–51) | Probe **N03b**: my reference with the IPv4 scope summary masked to two octets (`192.0.x.x/32, 198.51.x.x/24, 203.0.x.x/24`, in every inbound detail and in render) → **189 passed**. The stems are three-octet networks, so `198.51.x.x` contains none of them, and the AC-06 IPv4 pattern needs four numeric groups. Contract :122 says the FAIL detail shows the Name "(ไม่แสดงที่อยู่)" (no addresses). :137–138 says render shows "จำนวนรายการและความยาว prefix ของ scope เท่านั้น" (only the entry count and prefix lengths). Invariant :153 bars the home IP. Convention 9's example ("198.51.100.x/24 fails too") is accurate, but it does not cover this form. (The author's N03b is a different mutant, `a.b.c/nn`, and it is killed.) | An implementer masks two octets, for example after reading convention 9 that a one-octet mask fails. | The owner's home /16 (the ISP block) appears in the host report and then in `docs/evidence/ENV-001.md` in a public repo. AC-06's grep would not flag it. The exposure is small (a /16, not the address), so the severity is Low. | In `_assert_no_address`, also `assert re.search(r"\b(192\.0\|198\.51\|203\.0)\.", text) is None, text`, and extend convention 9. The leading `\b` keeps sizes such as "8192.0." clear. | N03b fails at least one `report_never_shows_a_full_address` case. Checked in scratch with `f7_check.py`, which is independent of the locked file: the pattern hits N03 and N03b (10 each) and 0 times on REF, V04, V06, V09, V10, V11 and V15 (V15 echoes values such as "8192.0 MiB" and the versions). |

Ready to commit red: **yes**. F1–F4 are closed with their proofs of fix. The patch is additive, and
each tightening is one r1 asked for. No contract-faithful variant I tried fails. All 189 tests fail
now for the contract reason only. F7 does not block: it is one more partial-address form of the F3
class. I recommend **not** funding a tests r3 round for it. After this review the headless budget
stands at 4 of 6 used (r1 author, r1 reviewer, r2 author, r2 reviewer). That leaves the
implementation reviewer and the spare. Instead, carry F7 and N01L as manual checks for the
implementation reviewer (below). Fold the F7 assertion into the next locked-test patch, if one
happens.

Findings open: 1 (F7 Low, confirmed, non-blocking)

## Manual checks for the implementation reviewer (residuals the suite cannot or does not cover)
1. **Disable lists (N01L).** Run the fresh-VPS input (RDP_TCP scope ("Any",) plus
   `RemoteDesktop-Shadow-In-TCP` with ports Any) through the real `evaluate`/`render`. Confirm that
   no `Disable-NetFirewallRule` command, single or a list, names `RemoteDesktop-UserMode-In-TCP`.
2. **Partial addresses (F7).** For the tests' valid Facts and the `two-bad-scopes` input, confirm
   that no detail and no render output matches `\b(192\.0|198\.51|203\.0)\.`. Also confirm that the
   scope summary shows only the entry count and the prefix lengths.
3. **Aliased dynamic imports.** Grep `host_report.py` for `import_module as`, `__import__` and
   `getattr(importlib` outside `collect_facts`.

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-02 | FAIL (red, as intended) | `uv run --offline pytest tests -q -p no:cacheprovider` → 189 failed, 3355 passed. All 189 failures are in the AC-02 file, each with only "AC-02: host_report not implemented (scripts/env/host_report.py is missing)". A contract-only reference passes 189/189. "Tests run on Linux" is UNKNOWN until CI runs (this host is Windows). The additions use only `re` and `ast`. |
| AC-01, 03–07 | not in scope | Owner L4 work, implementation and evidence come later. |

## Additive check (AST against `git show 5f4f527:…`)
`e1r2/driver/ast_compare.py` reads the old file through `git show` in a subprocess (no copy on disk)
and compares top-level statements by name with `ast.dump`. It ran at about 13:38Z, between the
driver run and the red run.
- 83 old statements and 86 new. None was removed. **78 are identical.**
- **5 changed**, and every assert, comparison and call of the old version is still present in the
  new one, except as noted:
  - Module docstring: conventions 4, 7, 9 and 11 only. Each describes the new code exactly.
  - `WRONG`: 0 keys removed, 0 values changed, 2 keys added (F2).
  - `test_ac02_inbound_rule_fails_and_the_detail_names_it`: all 8 old asserts kept, 1 added in the
    `disable` branch (F1).
  - `_assert_no_address`: both old asserts kept, the stem loop added (F3).
  - `_is_dynamic_import`: `== "__import__"` / `== "import_module"` became `in names` on both node
    kinds. This is a strict superset of what it matched before (F4); the "lost" comparisons in the
    output are only that rewrite.
- **3 added**: `IPV4_DOC_STEMS`, `_advises` and the new mixed test.
- Tests: 16 functions → 17. The only added parametrize ids are the 2 in `WRONG`. 186 + 3 = 189.

Tightened checks, each judged against the contract:
- **Render must carry `Set-NetFirewallRule -Name <RDP>` in the mixed case.** At 5f4f527, render only
  had to lack "Disable-NetFirewallRule" in scope cases. r1 asked for this check ("In both the detail
  and render"), and it is faithful: the CLI prints render only (:139), and the advice exists for the
  owner to act on (:122–127, :196). A different layout passes (V10: a status table plus a Details
  list), and so does inline code (V11).
- **Disable advice bound to the Name in the detail.** r1 asked for this, and the contract fixes the
  form `Disable-NetFirewallRule -Name <Name>` (:125). Single quotes, double quotes, no quotes, a
  grouped `-Name 'A','B'` (V09) and inline code all pass.
- **Stems.** r1 asked for these. A faithful report that echoes fact values (V15) passes.
- **`_is_dynamic_import` also feeds `test_ac02_script_imports_only_the_standard_library`.** This is
  a side effect of r1's requested fix. It can fail only a script that imports a non-stdlib or
  relative module through those call forms, which :49 forbids. A bare `import_module("winreg")`
  inside `collect_facts` passes both import tests (V13). Not a finding.
- **New `WRONG` ids.** r1 asked for these. They are derived from the constants, and `==` (:133)
  passes.

Forms the suite now rejects, judged not contract-faithful (so not findings):
- The Name alone in Markdown backticks, `` -Name `X` `` (V12, 19 failed). The backtick is PowerShell's
  escape character, so the line is not the contract's command. Wrapping the whole command in
  backticks passes (V11).
- A parameter placed between the command and `-Name` (for example `-PolicyStore … -Name`). The
  contract fixes `<command> -Name <Name>`.

## Red run
`PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider`,
from the repo root, 2026-10-25T13:38:28Z–13:38:53Z → exit 1, **189 failed, 3355 passed in 24.03s**.
- 189 `FAILED` lines, all in `tests/acceptance/ENV-001/test_ac02_host_report.py` (0 outside it).
- 189 failure sections, each with only the line "AC-02: host_report not implemented
  (scripts/env/host_report.py is missing)". 0 `E ` lines, no traceback.
- `one_wrong_value…`: 39 failures (37 + the 2 new ids). The new mixed test is among the failures.

The log is `e1r2/notes/red-run.txt`.

## Satisfiability
Scratch tree `C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/e1r2/tree`
uses the repo layout.
- **Test file.** Recreated there with the Write tool from the Read output: SHA256
  `a46fe787de95a7aa7076680a2119d2dc168774b010e8c2de558e60a83f80e462`, 829 lines, 36798 bytes,
  identical to the repo file.
- **Reference.** My own `scripts/env/host_report.py`, written from the contract only, before I read
  the handoff. Pristine copy `e1r2/driver/reference_host_report.py`, SHA256 `01ed7e9e…0b51`.
  Choices:
  - statuses are str
  - Names in advice are single-quoted, with any embedded ' doubled
  - one advice per failing rule
  - every inbound detail shows the entry count and, per entry, the prefix length, "keyword" or
    "range"
  - an item is UNKNOWN when any of its facts is None
  - `ctypes` and `winreg` are imported only inside `collect_facts`
  - `policy_first` and `parse_firewall_json` are module-level pure helpers
  - `collect_facts` is a sketch that was never run
- **Run.**
  `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline --no-sync --project <repo> python -I -B -m pytest <tree>/tests/acceptance/ENV-001 -q -p no:cacheprovider --rootdir <tree>`
  (literal paths, from the repo root) → **189 passed in 0.17s** (13:40:06Z). No test is
  unsatisfiable.

## Reviewer mutants and variants
`e1r2/driver/mutants.py` applies exact text replacements to the pristine reference, one entry at a
time. Each replacement must match exactly once. The driver writes the result into the tree, runs
the pytest command above in a new process with `--tb=no -rf`, and restores the reference at the end
(verified by SHA256). Runs:
- all entries: 13:36:58Z–13:37:08Z (`results.json`)
- the `--tb=line` rerun of the key mutants: 13:41:06Z–13:41:10Z
- N01L and N01Lu: 13:42:45Z

| ID | Change to the reference | Result | Caught at |
|---|---|---|---|
| N01 | Disable advice for every failing rule once any rule needs disabling | 1 failed | mixed test :672 (Set advice for RDP missing) |
| N02 | python_env by substring | 2 failed | `[python-env-uv-longer-version]`, `[python-env-python-longer-version]` :287 |
| N02s | python_env by `startswith` | 2 failed | as N02 |
| N03 | IPv4 scope summary as `a.b.c.x/nn` | 13 failed | `report_never_shows_a_full_address[valid]` and others, :736 |
| N04 | module-level `from importlib import import_module`, guarded `import_module("winreg")` | 1 failed | :819 |
| N04c | module-level guarded `builtins.__import__("winreg")` | 1 failed | :819 |
| N04d | module-level guarded `importlib.import_module("winreg")` | 1 failed | :819 |
| N17 | Disable advice with a literal `<Name>` | 19 failed | 18 disable cases :640, plus the mixed test |
| N18 | Disable advice bound to the first failing rule's Name | 1 failed | mixed test :673 |
| N19 | Set advice bound to the last failing rule's Name | 1 failed | mixed test :672 |
| N01Lu | extra `Disable-NetFirewallRule -Name` list of every failing rule, rule order (RDP first) | 1 failed | mixed test :673 |
| N01L (probe) | as N01Lu, sorted by Name (RDP not first) | survives, 189 passed | known limit, see F1 |
| N03b (probe) | IPv4 scope summary as `a.b.x.x/nn` | survives, 189 passed | **F7** |
| N04b (probe) | as N04 under an alias (`import_module as load_module`) | survives, 189 passed | residual, see F4 |
| V12 (probe) | Names in Markdown backticks only | 19 failed | not a contract form, see above |

Contract-faithful variants: each one gives **189 passed**.
- REF: single quotes (V07, single)
- V04: StrEnum statuses
- V05: Optional/Tuple spellings, no `__future__`
- V06: CRLF render
- V07d: double-quoted Names
- V07u: unquoted Names
- V08: Q3 read as "FAIL first"
- V09: one grouped `Disable-NetFirewallRule -Name 'A','B'`
- V10: a status table plus a Details list
- V11: advice in inline code
- V13: bare `import_module("winreg")` inside `collect_facts`
- V15: details that echo fact values

## Red-flag scan
`bash scripts/controls/red-flags.sh main` (13:39:28Z) → exit 0, "Pattern groups with hits: 0".
- Files changed since the merge-base `67bb4df`: PROGRESS.md, the contract, the handoff, review r1 and
  the test file.
- Deleted or renamed tests: none. Untracked: none.
- Control files touched: `tests/acceptance/ENV-001/test_ac02_host_report.py` (expected).
- The script diffs the merge-base against the working tree (`git diff "$MB"`), so the uncommitted
  r2 lines were scanned too.

## Checked, nothing found (and how)
- **Hashes and identity.**
  - `sha256sum`: patch `fbc81434…dae8`, file `a46fe787…e462`. `git hash-object`: `25abb32c…c278`.
  - `git rev-parse 5f4f527:<file>` and `HEAD:<file>` are both `85f287f8…c57c`. All match the brief
    and the handoff (:160, :163, :309–311).
  - `git apply -R --check docs/proposals/ENV-001-tests-r2.patch`, run alone → exit 0, no output.
  - Patch and `git diff` agree: 54 lines added, 10 removed, 9 hunks; the patch has 136 lines. Its
    only target is the test file.
- **Post-run detector.** My first Bash command (read-only: `git status`, `sha256sum`,
  `git hash-object`, 13:27:07Z) triggered the post-run detector. It reported exactly the patched
  test file, which was applied before this session. I verified the SHA256 and the blob against the
  handoff before reading its Round 2 text: a Grep for the hash strings only, which hit :160, :163
  and :309–311. Then I continued under CLAUDE.md's post-run rule.
- **The only locked-path change on top of 5f4f527.** `node scripts/controls/check-locked-paths.mjs main`
  → "!! locked A tests/acceptance/ENV-001/test_ac02_host_report.py", 1 change (FAIL until the owner
  labels it, as expected). `git status` shows only `docs/handoff/ENV-001.md` and the test file
  modified, both before and after this review (apart from this review file).
- **File hygiene** (`hygiene.py`): ASCII, 0 CR bytes, one trailing LF. No 7+ digit numbers. Every
  IPv4 literal is in RFC 5737, a mask or 0.0.0.0. No one-line string literal mixes a stem with
  non-address text.
- **Determinism.** The new test uses fixed Facts. Names and commands are found by regex, never by
  position or item order. The 2 new parametrize ids are unique and sorted with the rest.
- **Wording.** The new asserts match only the contract's command strings, `-Name`, `-RemoteAddress`
  and rule Names. No advice prose, punctuation, order of entries or report layout is checked.
- **Docstring.** Conventions 4, 7, 9 and 11 state exactly what the code checks. Convention 7
  states the one-Name-per-command binding, which is the source of the N01L limit.

## Not checked (and why)
- The tests on Linux: UNKNOWN until CI runs (this host is Windows 11).
- Forward `git apply --check`: not run, because the patch is already applied and the check would
  fail by design. The reverse check stands in for it.
- The author's scratch outputs (`e1t2/`: `ast_compare.txt`, `demo.txt`, `results-*.json`) and r1's
  (`e1r1/`): not read, to keep my reference and mutants independent. I reproduced the claims I
  needed with my own code instead.
- My reference's `collect_facts`: never run, and it is a sketch (for example, `sync_clients` is not
  collected). AC-02 does not call it.
- Names that contain quotes, and quoting with embedded quotes: no test Name contains one.
- Earlier sections of the handoff (round 1) and the rest of the repo: outside this narrow re-check.
