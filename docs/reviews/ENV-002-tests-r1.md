# Review ENV-002-tests round 1 · base main · head e708ce4 + applied, uncommitted `docs/proposals/ENV-002-tests.patch` · reviewer Claude Code, fresh headless session, tests reviewer under the role swap (PROGRESS.md)

Scope: the locked tests of ENV-002 as applied in the working tree (patch SHA-256 `c198f3ae…55f3`):
six new files under `tests/acceptance/ENV-002/` and the change to `tests/architecture/test_imports.py`,
against contract `docs/contracts/ENV-002-research-host-separation.md` v1.6. `src/sochron/app/` and
`scripts/env/make_sentinel.py` do not exist. `docs/handoff/ENV-002.md` was read as a list of claims.

How I verified, and the limit of it:
- **Run:** the seven SHA-256 values and Git blobs against the handoff; the red run in the repository
  (full suite, the architecture file alone, the ENV-002 folder alone); the two control scripts.
- **Read:** every line of the six new files and of the 784 added lines of `test_imports.py`, against
  the contract line by line. The AC-06 checker was traced by hand on the sources quoted in F3 and F5.
- **Not run (BLOCKED):** my own reference implementation, my own mutants and executed probes of the
  AC-06 checker. Copying the applied test files into my scratch tree was denied by a permission rule
  (two `cp` calls; exact text under "Blocks"). I stopped that line of work and did not recreate the
  files another way. So "confirmed" below means confirmed by reading the test code (the wrong
  implementation behaves the same on every existing test), not by a mutant run; F3 and F5 are hand
  traces of the checker. The author's satisfiability run (3547 passed) and 77 mutants stay claims.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | test_ac05_require_research_host.py:265–281, :95–105 | `test_ac05_python_m_runs_main` passes as soon as the `if __name__ == "__main__":` body holds any call of the name `main`. `main()` as a bare statement passes. Every other CLI test calls `ec.main(argv)` in-process and takes the **return value** as the exit code (`_cli`), so no test sees the process status. With `main(argv) -> int` (contract :57) that guard exits 0 for FAIL and UNKNOWN. | The most common guard idiom, `if __name__ == "__main__": main()`. | AC-05 "CLI exit 0 เฉพาะ PASS" (:60, :136) is false for the real `python -m sochron.app.envcheck` while all 192 tests pass. Anything that gates on `$?` / `$LASTEXITCODE` passes on FAIL. | In the guard test, require the `main(...)` call to be the argument of `SystemExit(...)`, `sys.exit(...)` or `exit(...)` inside the guard (so `raise SystemExit(main())` and `sys.exit(main())` pass). The checker's own allowed sample already ends with `raise SystemExit(main())` (test_imports.py:3044–3148). | A guard `main()` fails the test; the two accepted forms pass. |
| F2 | Low | confirmed | test_ac02_research_host_evaluate.py:461–468, :503–517, :534–536, :591–592; envkit.py:345–351 | None of the 13 cloud-only files of the suite is a manifest (`manifest.json` or `<file>.manifest.json` beside a data file); the AC-05 tests always install `cloud_only(())`. An `evaluate` whose manifest reader opens the file without asking `is_cloud_only` behaves the same on every test. | A `--data-dir` inside OneDrive with Files On-Demand (the F51 case, contract :90) whose `manifest.json` is not downloaded. | Opening it makes OneDrive download the file: breaks the Invariants "ไม่เปิดไฟล์ cloud-only" (:122) and no network (:123). The verdict is still not PASS (the same file makes `sentinel` UNKNOWN), so there is no false PASS. | One case: a `--data-dir` under OneDrive with `bars.parquet` and a cloud-only `manifest.json`. Assert it is never opened (`side_effects`), `sentinel` UNKNOWN and `excluded_period` not PASS. I suggest UNKNOWN and recording it as a convention, because the contract is silent on a cloud-only manifest. | A reference whose manifest reader skips `is_cloud_only` fails the new case. |
| F3 | Low | confirmed (hand trace, not executed) | tests/architecture/test_imports.py:2800–2837 (:2832) | `_envcheck_bindings` keeps one flat alias table for the whole module, and the first tracked binding of a name wins (`if name not in bindings`). **(a) False positive:** `def drives(): lib = ctypes.WinDLL('kernel32'); return lib.GetDriveTypeW('C:\\')` then `def close(h): lib = ctypes.WinDLL('mpr'); return lib.WNetCloseEnum(h)` resolves the second `lib` to `dll:kernel32` and reports `forbidden Win32 function kernel32.WNetCloseEnum`. This is exactly the form Q12 admits (literal library name, `<handle>.<Function>`, contract :137). **(b) False negative:** `def sep(): k = os; return k.sep` then `def drop(p): k = ctypes.WinDLL('kernel32'); return k.DeleteFileW(p)` resolves `k.DeleteFileW` to `os.DeleteFileW`, which no rule names: no finding. | (a) A generic handle name (`lib`, `dll`) reused in two functions. (b) Contrived for honest code. | (a) A contract-faithful envcheck fails the locked AC-06 test with a message that names the wrong library. (b) An unlisted Win32 call passes AC-06; `collect` is never executed by any test, so this checker is its only automated guard. | In `_envcheck_bindings`, when a name gets a second tracked value that differs from the first, report `line N: <name> is bound to more than one checked object` (refused on purpose, as Q12 does). Add both sources to `_ENVCHECK_FORBIDDEN` with the exact finding. Until then the implementer uses one name per library across the module, as the allowed sample does (`kernel32`, `mpr`, `shell32`). | Both sources give exactly the new finding; the three allowed samples still give none. |
| F4 | Low | confirmed | test_ac02_research_host_evaluate.py:449–451, :477; envkit.py:184–187 | Rule (1) is tested with the vault **folder** only (`_vault` makes a directory). v1.6 Q8 (:99) lets `vault_path` be the sentinel file. An `evaluate` that tests `os.path.isdir(vault_path)` passes every test. The make_sentinel test accepts both forms, and the end-to-end test only covers "the path does not exist". | make_sentinel prints the file form (allowed by Q8) and the implementer checks for a directory. | A sentinel file at the vault path on this machine is missed by rule (1). Rule (2) does not help: the vault path is outside the searched roots. | One case with `machine.sentinel(ec, vault_path=<an existing file under base/vps/vault>)`: `sentinel` FAIL. | A reference with `isdir` fails the new case. |
| F5 | Low | question | tests/architecture/test_imports.py:2712–2717, :2936–2941, :2976 | Two limits that Q12 does not list. **(1)** envcheck's stdlib imports are checked by a deny list of 47 names, where the strategy, backtest and research checkers use allow lists (`_STRATEGY_STDLIB` :1700 and its two siblings). By the code of `_envcheck_import_findings`, `import platform`, `venv`, `ensurepip`, `py_compile`, `compileall`, `zipapp`, `mailbox`, `antigravity` and `pydoc` give no finding. Of these, `venv` and `ensurepip` start processes, `py_compile`, `compileall`, `zipapp` and `mailbox` write files, and `platform.uname()` / `node()` call `socket.gethostname()` (CPython's `platform.py` as I recall it; not executed here). **(2)** The registry rule only looks at str literals that start with `SOFTWARE\` or `SYSTEM\`: `winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Network')` inside a function gives no finding, while the contract allows winreg for the Uninstall keys only (:51). | `platform.system()` in `collect` to test for Windows; reading `HKCU\Network` as an extra mapped-drive check. | Uses outside the contract's list pass AC-06, in code that no test executes. | Recommended (a): an allow list for envcheck's stdlib imports (the modules the contract's plan names, :164, plus `argparse`, `dataclasses`, `datetime`, `os`, `sys` and what the reference needs), and "a str literal passed as the sub-key of `OpenKey`/`OpenKeyEx` must be an Uninstall key". Or (b): the owner accepts both limits and they are written into AC-06 beside Q12; the implementation reviewer then reads envcheck's import list and every `OpenKey` call by hand. | (a) `import platform` and the `'Network'` source give a finding and the allowed samples none. (b) The owner's note. |
| F6 | Low | question | test_ac02_research_host_evaluate.py:69–71 (convention 11), :444–446 | Convention 11 fixes the token search to "32 ASCII characters in files written as UTF-8", and every token file of the suite is UTF-8. An `evaluate` that searches the bytes for the ASCII token passes. The contract says only "ไฟล์ข้อความ … ที่มี token" (:84). | The token pasted into a note with Windows PowerShell 5.1 redirection (`>` / `Out-File` write UTF-16LE by default) under `<repo>/data/transfer/`. | Rule (4) misses the copy it exists for: `sentinel` PASS. The threat model already accepts hand copying (:154), so this is a detection aid, not the boundary. | Recommended (a): add cases "token in a UTF-16LE file with BOM" and "UTF-16BE" as `.txt` in `data/transfer` → `sentinel` FAIL, and say so in convention 11. Or (b): the owner accepts UTF-8/ASCII only and the contract says so. | (a) A byte-search-only reference fails the new cases. (b) The owner's note. |
| F7 | Low | question | test_ac05_require_research_host.py:95–105, :186–187, :199–201, :310–311, :321–323 | Q7 (:98) is checked on every `Item.detail` and on standard output. `_cli` drops `capsys.readouterr().err`, and no test looks for the token in `str(ResearchHostError)`. A CLI that writes the matching line to stderr, or an error message that quotes it, passes. Whether Q7 covers those two is the question. | A debug line or a "found in <file>: <line>" message added to stderr or to the error. | The token reaches a terminal log, a handoff or PROGRESS text; a repo file that holds it then fails rule (4) by design (:95). | `_cli` also returns `.err`, and the CLI tests assert the token is in neither stream; the end-to-end test asserts `values["token"] not in str(error)`. | References "token on stderr" and "token in the error message" fail. |
| F8 | Low | question | envkit.py:227–238; contract :100, :129 | "Unreadable because of permissions" is made only for `open` (the hook refuses `open` events). No test has a folder that cannot be listed. `os.walk` drops listing errors unless `onerror` is given, so an `evaluate` that silently skips such a folder passes, while the contract says an unreadable value is UNKNOWN (:100). | A folder under a search dir or data dir that the process cannot list. | A silent skip where the contract says UNKNOWN. The harm is small (research code runs as the same user and cannot read that folder either), but pinning UNKNOWN has a cost the owner should see first: stock Windows profiles have legacy junctions such as `Documents\My Music` that refuse listing (from my knowledge of Windows; **not checked on this machine**, I did not list the owner's folders), so a strict rule could keep AC-01 at UNKNOWN. | Recommended (a): decide the rule first (suggestion: junctions and other reparse points are not entered; any other folder that cannot be listed makes the items that search it UNKNOWN), then one case that raises PermissionError from the hook on `os.scandir` / `os.listdir` for a chosen folder. Or (b): leave it to the implementer's unit tests and the implementation review. | (a) A reference that ignores listing errors fails the new case. (b) The owner's note. |

Ready to commit red and implement: **yes**, with one check still owed. The red state is verified by
execution (183 failed, 3364 passed; every failure is a "not implemented" message; the 18 earlier
architecture tests and the checker's own 92 sample sources pass). By reading, no existing assertion
contradicts contract v1.6, and I found no pair of tests that contradict each other. All eight
findings are missing cases or one checker fix; none needs an existing assertion to change. The one
known way for faithful code to fail (F3 a) has a one-line workaround. What I could not do is run my
own reference and mutants (BLOCKED), so "a correct implementation can pass" rests on my reading and on
the author's unverified run.

Recommended next steps: commit the seven files red as they are. Then an additive D-006 patch for
F1–F4, plus the option chosen for F5–F8, written by a fresh test-author session and reviewed by a
fresh session **before** the code they touch is written (the `__main__` guard, the manifest reader,
the ctypes code of `collect`, rule (1)); that review session also runs the satisfiability and mutant
work this session could not. Budget: the contract allows 5 headless sessions (author, this review,
work reviewer, 2 spare); this path uses both spares. If the owner does not fund it, the implementation
reviewer checks by hand: the guard passes main's result to `SystemExit`/`sys.exit` (F1); the manifest
reader asks `is_cloud_only` first (F2); one handle name per library (F3); rule (1) uses "exists" (F4);
the import list and every `OpenKey` call (F5).

Findings open: 8 (F1 Medium; F2, F3, F4 Low confirmed; F5–F8 Low questions for the owner)

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-02 | FAIL (red, as intended) | 160 failures: 157 "sochron.app.envcheck not implemented (No module named 'sochron.app')" and 3 "make_sentinel not implemented". Gaps: F2, F4, F6, F8. |
| AC-04 | PASS now | 6 tests pass on merged code (the guard exists since CORE-008, `runner.py:59`); they pin the excluded period with `synthetic_bars`. |
| AC-05 | FAIL (red, as intended) | 22 failures, "not implemented". Gaps: F1, F7. |
| AC-06 | FAIL (red, as intended) | 3 boundary tests pass on merged code; the envcheck test passes its checker self-test and then fails on "envcheck.py does not exist". Gaps: F3, F5. |
| AC-01, 03, 07 | not in scope | Owner L4 runs and the PR. |
| Tests on Linux | UNKNOWN | This host is Windows 11; see "Not checked". |

## Coverage per contract clause
Every row has at least one test that fails for the wrong behaviour, unless a finding is named.

| Clause (contract line) | Tests | Status |
|---|---|---|
| Item, Report, Sentinel, ResearchRoots, Facts frozen with these fields (:43–48) | `records_are_frozen…` | covered |
| Verdict FAIL > UNKNOWN > PASS (:44) | `verdict_is_fail_then_unknown_then_pass` ×3; `check_report` recomputes it on every report | covered |
| evaluate reads only what the rules need, writes nothing, no process or network (:53, :122–123) | `side_effects` on every evaluate call: opens against `must_not_open`, write modes and flags, forbidden audit events, MetaQuotes never listed | covered; cloud-only manifest: **F2** |
| research_host_report = evaluate(collect(roots), …) (:54) | ×3 | covered |
| require_research_host (:55, AC-05) | returns the PASS report; raises and names each item ×7; names all four | covered |
| default_roots (:56) | `without_roots…`, the CLI tests | covered through the seam; the real one is not run (by design) |
| main and the CLI (:57–60) | exit code ×3, every item printed, last line, `--data-dir` order, missing `--data-dir`, no `--sentinel-file`, end to end with make_sentinel | covered in-process; process exit status: **F1**; stderr: **F7** |
| terminal_install (:62–67) | 10 fact cases (Q4 case variants included), 3 "found beside unreadable", None ×3 | covered at the Facts level; the path search (levels, skipped folders) is the implementer's unit tests by Q2 (:66–67) |
| terminal_data (:68) | fact True and None; MetaQuotes never listed or opened, also inside a `--data-dir` | covered |
| mt5_package (:69) | True, None | covered |
| holdout_dir (:70) | repo root, deep and mixed case, upper case in `data/transfer`, a `--data-dir` | covered |
| excluded_period in data dirs (:71–74) | at the cutoff PASS, 1 s after FAIL, 2026, per-file before and after, no manifest (also deep), manifest that lists another file, unlisted second file, csv/hcc/hc/tkc, 14 broken manifests, not UTF-8, unreadable (UNKNOWN), late beside unreadable (FAIL) | covered |
| excluded_period under the repo outside data dirs (:75) | `.tkc`, `.hcc`, `.hc` FAIL; csv and parquet PASS | covered |
| Q5 missing data dirs (:77–78) | no `<repo>/data` ×3; missing `--data-dir` UNKNOWN; CLI non-zero | covered |
| network_shares (:79) | drive, resource, both, each beside None, None ×2 | covered |
| sentinel not given (:80) | `no_sentinel_is_unknown`; require names it | covered |
| Rule (1) vault_path (:81, :99) | vault folder | folder form only: **F4** |
| Rule (2) name (:82) | Desktop, OneDrive, `data/transfer`; lower and upper case; content never opened | covered |
| Rule (3) size then SHA-256 (:83) | Desktop, moved Desktop, deep Downloads, Documents, OneDrive, repo, node_modules; same size and other bytes PASS; `.JSON`/`.Json` | covered |
| Rule (4) token in text files (:84) | txt, md, csv, json; `data/transfer`, a `--data-dir`, `.git`, `.venv`; a same-named file elsewhere FAIL; search dirs not read | covered for UTF-8; other encodings: **F6** |
| Cloud-only (:86–91) | 13 cases (repo, data, `--data-dir`, OneDrive, png, other size, F51 overlap, FAIL beside UNKNOWN), `is_cloud_only` ×7 | covered; manifest: **F2** |
| Never-open list (:92–93) | 5 cases with every listed name, terminal folders, MetaQuotes; `must_not_open` on every call | covered |
| The one excused file (:94–95) | token only there PASS; same name in `data/transfer` FAIL | covered |
| Q6 (:96) | 9 cases, both directions (UNKNOWN where rule (3) or (4) would open the file, ignored otherwise) | covered |
| Q4 for the sentinel item (:97) | name, `.JSON`, `.TXT`, `.Md`, `.CSV`, `Terminal64.EXE` | covered |
| Q11 (:97) | `.venv`, `.git`, node_modules, the `.git` of a `--data-dir` | covered |
| Q7 (:98) | every detail of every report; standard output of the CLI tests and of the three end-to-end runs | covered there; stderr and the error text: **F7** |
| Unreadable = UNKNOWN (:100) | Facts None ×7, manifest, json on Desktop, txt in data | files and facts covered; folders: **F8** |
| make_sentinel (:102–105) | stdlib only (AST and `-I`), one file, printed values describe it, 60 bars, tokens differ | covered |
| synthetic_bars (:107–113) | type, times under the rule, constant price, count 0 | covered |
| AC-04 (:135) | 4 periods × 5 calls, registry bytes and folder unchanged, control run before the cutoff | covered. Only `purpose="select"` is used; the guard runs before the purpose is read (`runner.py:59`) and CORE-008 owns that rule |
| AC-06 boundaries (:137) | 19 import forms × 6 checkers; the real sources and `sochron/__init__.py`; a fresh interpreter reading `sys.modules` | covered |
| AC-06 envcheck (:137) | 89 forbidden sources with exact findings, 3 allowed, then the real module and `app/__init__.py` | covered for the listed forms; **F3**, **F5** |

Not covered and no finding (the contract is silent, or it fails closed): a per-file manifest exactly
at the cutoff (only the folder form has the boundary case); rule (2) under the repo outside data
dirs; a folder named `holdout-old` (a substring match would only over-report); never-open names in
upper case (`.ENV.JSON`); a `--data-dir` equal to `<repo>/data`.

## The author's conventions (handoff 1–18)
| # | Convention | Judgement |
|---|---|---|
| 1 | `<repo>` = parents[3] | correct for `<repo>/tests/acceptance/ENV-002/<file>` |
| 2 | Facts: exactly 7 fields; None = unreadable; any found condition fails the item | reasonable and consistent with :48 and :62–69. The exact set leaves no room for a "why unreadable" field; acceptable, and the owner's Q2/Q3 answers already name `Facts.terminal_paths` |
| 3, 4 | ResearchRoots and Sentinel as built by the tests | follow :45–47; types are the natural ones |
| 5 | str statuses, one Item each, frozen, verdict a field or property, FAIL outranks UNKNOWN inside an item | follows :43–44 and "FAIL เมื่อพบอย่างใดอย่างหนึ่ง" |
| 6 | recursive searches that enter `.git`, `.venv`, node_modules; overlap follows repo rules | Q11 and :90. Only the sentinel cases test it, so holdout_dir under `.git` is left open (good: a branch folder named `holdout` would otherwise matter) |
| 7 | per-file manifest `<full name>.manifest.json`, written in the folder shape | tolerant of both readings of :71–72 |
| 8 | "opened" = an `open` audit event; one hook, active only while recording; the hook also raises PermissionError | as AC-02 prescribes (:133). Paths compare by `normcase(abspath)`, which a normal implementation satisfies |
| 9 | the read rules checked on every evaluate call | follow the Invariants (:122). "These names compare without case" is tested only for `terminal64.exe`; Q4 names the sentinel name and extensions |
| 10 | evaluate calls `envcheck.is_cloud_only` at call time; the real one calls `os.stat` | :86–91. `Path.stat()` also passes (it calls `os.stat`); `os.lstat` or `from os import stat` would not, in line with the contract's wording |
| 11 | token as ASCII in UTF-8 files; names and extensions without case; one excused path | **F6** for the encoding; the rest follows Q4 and :94 |
| 12 | Q5 | as :77–78; holdout_dir and sentinel are rightly not compared for a missing `--data-dir` |
| 13 | Q6 | as :96, including files under a terminal folder |
| 14 | Q7 on details and CLI output | **F7** for stderr and the error text |
| 15 | seams: collect and default_roots replaced; main returns the code or raises SystemExit | Q9. The fake default_roots accepts zero or one argument, positional or keyword |
| 16 | make_sentinel output | as :102–105 and Q8 |
| 17 | AC-04 on merged code, inclusive cutoff | as :21 and `inputs.py:56–70` |
| 18 | the AC-06 checker and its limits | Q12; **F3** and **F5** are limits Q12 does not list |

One unlisted convention: "APPDATA MetaQuotes inside a `--data-dir`" (`_CLOSED`, :667–668) expects
`excluded_period` PASS for a data dir that holds the pruned MetaQuotes folder. An implementation that
answers UNKNOWN there fails. The verdict is FAIL either way (terminal_data), so I leave it as a note.

## The handoff's claims
| Claim | Result |
|---|---|
| Patch SHA-256 and the seven post-apply SHA-256 values and blobs | verified, all equal |
| Red run 183 failed, 3364 passed; failures only in ENV-002 and the new architecture test | verified |
| Inventory 192 tests (160 + 6 + 22 + 4) | verified from the run (182 failed + 6 passed in the folder; 1 failed + 3 passed new in architecture) |
| The checker self-test runs first and passes | verified (the architecture failure is the "does not exist" assert that follows it) |
| `test_imports.py`: additions only, no clash of names | verified: `git diff --stat` shows 784 insertions and no deletion, in two hunks (a docstring paragraph and an appended section); every new top-level name starts with `_ENV002`, `_env002`, `_ENVCHECK`, `_envcheck`, `_inspect_envcheck` or `test_ac06_env002`, and no earlier name does; the 18 earlier tests pass |
| ASCII, LF, one trailing newline | no non-ASCII character and no CR in the six new files or in the added lines of `test_imports.py` (Grep) |
| Satisfiability: 3547 passed with the author's reference | **not verified** (BLOCKED) |
| 77 mutants killed | **not verified** (BLOCKED) |

## Checks
Head `e708ce4` plus the applied patch, 2026-11-05.

| Command | Result | Time (UTC) |
|---|---|---|
| `sha256sum` of the seven files and the patch | all equal to the handoff table | before 08:51 |
| `git hash-object --no-filters` of the seven files | all equal to the handoff table | before 08:51 |
| `uv run --offline pytest tests -q -p no:cacheprovider` | exit 1; 183 F marks; every failure text read was a "not implemented" message (the output was cut before the count line) | before 08:51 |
| `uv run --offline pytest tests -q -p no:cacheprovider --tb=no -rN` | exit 1, **183 failed, 3364 passed in 24.78s** | before 08:51 |
| `bash scripts/controls/red-flags.sh main` | exit 0, "Pattern groups with hits: 0"; the six new files are untracked and not scanned; control file touched: `tests/architecture/test_imports.py` | 08:51 |
| `node scripts/controls/check-locked-paths.mjs main` | exit 1, FAIL as expected: 7 locked changes need the owner's label | 08:51 |
| `uv run --offline pytest tests/architecture -q -p no:cacheprovider --tb=line` | exit 1, **1 failed, 21 passed in 1.57s**; the failure is "AC-06: …\src\sochron\app\envcheck.py does not exist; sochron.app.envcheck not implemented" | 08:51–08:58 |
| `uv run --offline pytest tests/acceptance/ENV-002 -q -p no:cacheprovider --tb=line -rN` | exit 1; 160 F, 6 passed, 22 F; messages "make_sentinel not implemented" and "sochron.app.envcheck not implemented" (the count line was cut) | 08:51–08:58 |
| `cp` of the applied test files into the scratch tree (two calls) | **BLOCKED**, permission denied | before 08:51 |

Red-flag patterns on the six untracked files (Grep with the script's patterns plus `skipif`,
`importorskip`, `pytest.skip`, `xfail`): no match. The two `except Exception` clauses
(test_ac05…:189, test_ac04…:131) turn the caught error into the reported failure or the compared
value; nothing is swallowed.

## Checked, nothing found (and how)
- The post-run detector: my first Bash command (`git status`, `git rev-parse`, `git diff --stat`, `ls`;
  read-only) made it report exactly the seven targets of the applied patch, which were in place
  before this session. I verified every SHA-256 and blob against the handoff and continued under
  CLAUDE.md's rule for that report. It did not fire again.
- Tests that contradict the contract or each other: none found by reading. I walked a contract-only
  design through the cases where several rules meet: never-open beside a copy or a token, terminal
  folders on Desktop and in data, MetaQuotes inside a `--data-dir`, the repo under Desktop, the
  moved Desktop with overlapping search dirs, an unreadable manifest beside a late one, the 14
  broken manifests (sentinel stays PASS because the token search is a text search), a missing
  default data dir.
- The audit hook: `builtins.open`, `io.open`, `Path.open`/`read_bytes`/`read_text`, `os.open` and
  `io.FileIO` all raise `open`; `os.walk`, `os.scandir`, `Path.iterdir` and `rglob` raise
  `os.scandir` or `os.listdir`. Python's own `.pyc` reads lie outside the fake host and are not
  judged; `__pycache__` writes and renames are excluded. The write flags do not overlap the
  read-only flags on Windows or Linux. The refused `open` is a real PermissionError for the caller.
- The cloud-only seam: wrong orders and scopes fail (check after open; only in search dirs; by size
  in repo/data; any extension in search dirs; one bit only; equality instead of a mask; reading the
  attribute without the seam). The gap is F2.
- Manifest rules: `<=` against `<` fails at the cutoff case; a date-only comparison fails at 1 s
  after; a per-file name built from the stem fails; a folder manifest that need not list the file
  fails; no recursion fails; parquet-only fails; flagging csv under the repo fails.
- Q4–Q7, Q11: each has cases in both directions where the contract gives two outcomes (see the
  coverage table).
- AC-06 checker, by reading against the contract's list: the four libraries and ten functions match
  :49–50; winreg is an allow list of read-only members with HKLM and HKCU only; subscript,
  `getattr`, passing, returning and storing a library or loader are all refused; `CDLL`, `cdll`,
  `PyDLL`, `pythonapi`, `CFUNCTYPE`, `WINFUNCTYPE`, `ctypes.util`, `_ctypes`, `_winapi`, `nt` are
  refused. A natural envcheck (handles named after their library, Structures and `wintypes` at
  module level, winreg imported inside a function, `os.listdrives`, `os.environ`,
  `importlib.util.find_spec`, argparse, read-only opens) gives no finding, as the first allowed
  sample shows by execution.
- Hygiene: no skip, only or xfail; no weakened assert (`ignore=` is used in three places, each with
  a stated reason); fakes only under `tests/`; no Windows module imported by a test; no clock,
  sleep or randomness in the tests; basenames unique under `tests/` here and on the ENV-001 and
  SPIKE-002 branches (`git ls-tree`); `tests/` has no `__init__.py` and pytest collects only
  `test_*.py`, so `envkit.py` and `synthetic.py` are not collected.
- Linux, by reading: paths come from `Path` and `os.sep`; no two test files in one folder differ only
  by case; the `os.stat` fake passes through fds and keyword arguments; subprocesses use
  `sys.executable -I -B`.

## Not checked (and why)
- Satisfiability by execution, my own mutants and executed probes of the AC-06 checker: BLOCKED
  (below). F3 and F5 are hand traces; F1, F2, F4 follow from the test code.
- The author's scratch reference and mutant files: not read (outside my scratchpad).
- The tests on Linux: UNKNOWN until CI runs (this host is Windows 11).
- `collect`, the real `default_roots`, the terminal path helper and its levels: they do not exist
  yet, and the contract gives them to `tests/unit/app/` (Q2, Q3, Q10) and the implementation review.
- `git apply -R --check`: not run; this session applies and reverses nothing.
- Whether the legacy junctions of F8 exist on this machine, and CPython's `platform` internals (F5):
  from memory, not executed.

## Blocks
Two calls were refused by a permission rule, and I did not retry them in any other form:

```
Permission to use Bash with command cp -r tests/acceptance/ENV-002 "C:/Users/MSI/AppData/Local/Temp/claude/06789332b3a4bc88/c7f3187e-eaf2-48ee-bd2f-9fdf4a27ac2a/scratchpad/tree/tests/acceptance/" has been denied.
Permission to use Bash with command cp tests/architecture/test_imports.py "C:/Users/MSI/AppData/Local/Temp/claude/06789332b3a4bc88/c7f3187e-eaf2-48ee-bd2f-9fdf4a27ac2a/scratchpad/tree/tests/architecture/test_imports.py" has been denied.
```

Left in my scratchpad (`…\c7f3187e-eaf2-48ee-bd2f-9fdf4a27ac2a\scratchpad\`): `tree\` (a
`git archive` of `e708ce4`, without the applied tests) and `arch.diff` (the `git diff` of
`test_imports.py`). Nothing in the repository was edited, staged or committed except this file.
