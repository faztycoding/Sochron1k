# Review ENV-002-tests round 2 · base `f62a101` + `docs/proposals/ENV-002-tests-r2.patch` (read, not applied by me) · reviewer Claude Code, fresh headless session, tests reviewer under the role swap (PROGRESS.md)

Scope: the round-2 patch of the locked ENV-002 tests (patch SHA-256 `3f7471e5…0ee1`, four files:
`tests/acceptance/ENV-002/envkit.py`, `test_ac02_research_host_evaluate.py`,
`test_ac05_require_research_host.py` and `tests/architecture/test_imports.py`), against contract
`docs/contracts/ENV-002-research-host-separation.md` **v1.8** (read with `git show 27944cf:…`), and the
"Round 2 (tests r2)" section of `docs/handoff/ENV-002.md`, read as a list of claims. The v1.6–v1.8
decisions are taken as given. I did not read `src/sochron/app/` or the main folder.

`p:NNN` below is line NNN of the patch file; `:NNN` alone is a line of the contract at `27944cf` or of
the named file at `f62a101`.

How I verified, and the limit of it:
- **Run:** the patch's SHA-256, size and line count; `git apply --check` and `--numstat --summary` in
  the worktree (both read-only); the seven base blobs at `f62a101` against the round-1 table; the full
  suite in a scratch copy of `f62a101` **without** the patch (the baseline); a probe of my own of plain
  CPython behaviour (`probes\probe_cpython.py` in my scratchpad: stdlib module names, how a
  PermissionError raised by an audit hook on a listing surfaces, UTF-16 byte patterns). The probe holds
  no code of the locked tests.
- **Read:** every line of the patch against the four files at `f62a101` and the contract. The changed
  AC-06 checker was traced by hand on the 18 new and 2 changed forbidden rows and the 3 new allowed
  samples, and I checked why the 87 untouched rows and the 3 old samples cannot change.
- **Not run (BLOCKED):** the patched tests. guard-bash refused `git apply` inside my scratch tree
  (exact text under "Blocks"). I stopped that line of work and did not build the patched files with
  any other tool, script or command. So "closed" below means closed by reading, with the two mechanisms
  that F6 and F8 rest on confirmed by the probe. The author's red run (195 failed, 3364 passed), the
  checker self-test (107 forbidden, 6 allowed), the satisfiability run (3559 passed) and the 93 mutants
  stay claims.
- Before I ran the brief's command I read `.claude/hooks/guard-bash.mjs` (:393–556) to choose between
  the two forms the brief names, and saw that the guard accepts `git apply` only as one standalone
  command inside the project repository. I ran the form that is correct in git terms once, from the
  scratch tree's root, and let the guard decide.

## F1–F8 of round 1

| ID | r1 Sev | Status | Evidence | Left over |
|----|--------|--------|----------|-----------|
| F1 | Medium | closed (by reading) | p:388–407. The guard test keeps its old assertion and adds one: a call `SystemExit(main(...))`, `sys.exit(main(...))` or `exit(main(...))` under the `__main__` guard. A bare `main()` leaves that list empty and fails with a message that says why. `raise SystemExit(main())` (the checker's own allowed sample) and `sys.exit(main())` pass. | **F9** |
| F2 | Low | closed (by reading) | p:190–216. Two cases: a cloud-only `manifest.json` in a `--data-dir` under OneDrive, and a cloud-only `bars.parquet.manifest.json` under `<repo>/data`. The manifest is in `must_not_open` through the `cloud` list, so a reader that opens it fails with "opened …". "No manifest, so FAIL" and "skip, so PASS" both miss the expected UNKNOWN. The expectation is the contract's: excluded_period UNKNOWN (:79) and, because the manifest is a cloud-only `.json` in a data dir, sentinel UNKNOWN (:89). | none |
| F3 | Low | closed (hand trace, not executed) | p:480–534, p:556. A name that gets a second value different from its first, where either is a tracked object, gives `line N: <name> is bound to more than one checked object` and resolves to nothing afterwards. My trace of the three new forbidden rows (r1's (a) and (b), and an imported name rebound to a library) gives exactly the expected finding each, and the new allowed sample (kernel32 under one name in two functions) gives none. The import pass changed from "last import wins" to "first wins, or a conflict": `import os as k` followed by `import json as k` was hidden before and is a finding now. I found no source that the old code reported and the new code accepts. | note N1 |
| F4 | Low | closed (by reading) | p:146–150, p:171. `m.vault` becomes `<base>/vps/vault/<sentinel name>` and that file exists; `Machine.sentinel` reads `self.vault` when called (envkit.py:184–187), so `vault_path` is the file. Expected: sentinel FAIL. `os.path.isdir` answers PASS and fails the case. The file lies outside every root, so opening it would be reported too. | none |
| F5 | Low | closed (hand trace; names probed) | The allow list (p:470–473) equals the contract's list name for name, 14 modules (:146). Any other stdlib top-level module gives `forbidden stdlib import X` (p:542–543); the 47 denied modules keep `forbidden import X`. The sub-key rule (p:564–569) reads the second positional argument or `sub_key=` of `OpenKey`/`OpenKeyEx`. New rows: platform, venv, ensurepip, py_compile, compileall, zipapp, mailbox, pydoc, stat, glob, `__future__`, platform inside a function, `'Network'`, `sub_key='Environment'`, `SYSTEM\CurrentControlSet` (the older literal rule reports the same text on the same line; the set keeps one). Probe 1: every allow-list name and every row's module is in `sys.stdlib_module_names` on Python 3.12.15, so no row falls into the third-party branch. No module a correct envcheck needs is left out (section below). | notes N3, N4 |
| F6 | Low | closed (by reading + probe 3) | p:153–160, p:172–180. Four `.txt` files in `data/transfer` that hold the token alone: UTF-16LE and BE, each with and without a BOM; sentinel FAIL. Probe 3: each file is found only by the pattern of its own byte order and never by the ASCII pattern, so an ASCII-only, an LE-only, a BE-only and a BOM-only search each fail at least one case. With text around the token both orders match (the author's M86), which is why the token stands alone. A byte search for the three forms, or decoding, both satisfy the cases. | none |
| F7 | Low | closed for its proof of fix (by reading) | p:289–309. `_cli` returns both streams and all five callers were changed with it (exit codes ×3, data-dir order, missing data dir, no sentinel file, the end-to-end's three states). The two old "token in stdout" checks became `_token_shown`, which checks stdout and stderr. The error text is checked in raises-and-names ×7 (p:317), names-every-item (p:325) and the end-to-end (p:430–431). | **F10** |
| F8 | Low | closed (by reading + probe 2) | envkit p:27–28: the hook raises PermissionError for the `os.scandir`/`os.listdir` event of a chosen folder, after recording it. Five cases (p:219–247) with the contract's scope (:103–105): under the repo or a data dir, holdout_dir, excluded_period and sentinel are UNKNOWN; under a search dir, sentinel alone. The locked folders hold a token `.txt` and a `bars.parquet` without a manifest, so a walk that somehow listed them would FAIL instead. Probe 2: the refusal reaches `os.walk(onerror=…)` and `Path.walk(on_error=…)` as PermissionError and raises from `os.scandir`, `os.listdir` and `Path.iterdir`; `os.walk` without `onerror`, `Path.walk` without `on_error` and `Path.rglob` skip the folder silently, which the cases turn into a failure. `os.stat` and `isdir` of the folder still work. No case calls collect, so v1.8 (:105–108) is not contradicted. | reparse points have no test (the handoff says so) |

## New findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F9 | Low | confirmed (by reading; probe 4 for the language rule) | test_ac05_require_research_host.py, `test_ac05_python_m_runs_main` (p:388–407) | The new list `exits` takes any call `SystemExit(main(...))` under the guard. It does not ask for the `raise`. A guard whose body is the statement `SystemExit(main())` builds the exception and drops it (probe 4: "raises nothing; it only builds SystemExit(1)"). Every other CLI test calls `ec.main` in-process. | A guard with the `raise` forgotten. | The same as F1: `python -m sochron.app.envcheck` exits 0 on FAIL and UNKNOWN while every test passes. Much less likely than the bare `main()` that F1 closed. | For the `SystemExit` form, require the call to be the `exc` of an `ast.Raise` in the guard body; keep `sys.exit(...)` and `exit(...)` as they are. Without a patch: the implementation reviewer reads the guard, and the AC-01 run records the exit status. | A guard `SystemExit(main())` fails; `raise SystemExit(main())`, `sys.exit(main())` and `exit(main())` pass. |
| F10 | Low | confirmed (by reading) | test_ac05_require_research_host.py, `test_ac05_cli_end_to_end_with_make_sentinel_output` (:313–323, p:410–432) and every `_cli` and require caller | The v1.7 F7 checks run only where the CLI or require runs. Rule (4) is the only rule that reads a line holding the token, and it fires in exactly one of those places: the end-to-end's third state, where the Desktop copy (rule 3) is present as well. The AC-02 cases where rule (4) fires alone call `evaluate` and look at the details, not at the streams. | An envcheck that returns at the first sentinel hit in the contract's rule order (1)–(4), and in the rule-(4) branch writes "found in <file>: <line>" to stderr or into the error message. | The leak F7 describes (the token in a terminal log or a handoff) with every test passing. | In the end-to-end test add one state with only the token text in `data/transfer` (before the copy is put on Desktop): FAIL, the token on neither stream and not in the error text. | A reference "rule (3) first with a short circuit; rule (4) prints the matched line to stderr, or quotes it in the error" fails. |

Notes, no finding:
- **N1 (for the implementer, F3).** The conflict rule is wider than the handoff's "one name per
  library". Any plain alias that gets two different tracked values is refused, also when both values
  are allowed: `step = kernel32.Process32FirstW` then `step = kernel32.Process32NextW`; `root =
  winreg.HKEY_LOCAL_MACHINE` then `root = winreg.HKEY_CURRENT_USER`; `sep = os.sep` then `sep =
  os.altsep`. Round 1 accepted these. This is within Q12 ("other forms are refused on purpose",
  :146), the message names the name and the line, and the cure is a rename. Loop targets and unpacked
  names are not aliases, so the rule does not see them. I do not suggest narrowing the rule: a
  narrower one would have to list every receiver whose members matter, or it hides them again
  (`x = os.sep`, later `x = importlib`, then `x.import_module(...)`).
- **N2.** The test docstrings say "v1.7"; the contract is v1.8. v1.8 changes only collect's terminal
  path search, which no acceptance test runs.
- **N3.** `from __future__ import annotations` is a finding. The v1.7 list is exhaustive and does not
  name `__future__`, and Python 3.12 does not need it; the handoff says so.
- **N4.** The sub-key rule covers a str literal passed directly, as v1.7 words it. A sub-key held in a
  name is not checked, so the implementation reviewer still reads every `OpenKey` call.

## Is a module a correct envcheck needs left out of the allow list? No

What contract v1.8 asks of envcheck, and what supplies it: the CLI (`argparse`, `sys`); the records
(`dataclasses`, `typing`); the cutoff (`datetime`, `sochron.research`, which the checker allows);
hashes (`hashlib`); manifests (`json`); `find_spec` (`importlib.util`); walking with listing errors
(`os.walk(onerror=…)`, `pathlib`); reparse points (`os.path.islink`, `os.path.isjunction` and
`DirEntry.is_junction()`, all in 3.12); the token forms (`str.encode` and `bytes`, or `re`); Win32
(`ctypes`, `ctypes.wintypes`, and a hand-built GUID Structure for SHGetKnownFolderPath, so no `uuid`);
the registry (`winreg` inside functions). Refused and not needed: `codecs` (a BOM is a two-byte
literal), `stat` (0x400 as a literal, or `isjunction`), `errno`, `enum`, `functools`, `contextlib`,
`io`, `__future__`.

## Did a round-1 assertion get weaker? No

- No test function, assert, import or table row is removed. The only removed `def` lines are the three
  signatures that gain `deny_list` (p:12, p:36, p:51), and every new parameter defaults to empty.
- test_ac02: additions only (5 rows appended to `_SENTINEL`, two new tests, helpers, `import codecs`).
- test_ac05: the two "token in stdout" checks are replaced by a check of both streams; the guard test
  keeps `assert calls` and adds `assert exits`.
- test_imports: 87 of the 89 round-1 forbidden rows and the 3 allowed samples are untouched text. By
  reading, the new code cannot change their findings: none imports a stdlib module that is neither
  denied nor allowed (only the `io` and `codecs` rows did, and those two now expect the extra finding,
  in sorted order); none binds a name twice; none passes a literal sub-key to `OpenKey`/`OpenKeyEx`
  (the `CreateKey` and `DeleteKey` rows are other functions). `_HEADER` is a docstring, not an import.

## Ready to commit: yes

Each of F1–F8 is closed by its proof of fix as far as reading and the two probes can show. No round-1
assertion is weaker. I found no new test that fails a correct implementation of v1.8: every new
expectation follows a contract line (:79, :89, :100–108, :146), and the F8 cases stay inside
`evaluate`. F9 and F10 are Low gaps that leave every existing assertion as it is.

The limit: I did not execute the patched tests. One cheap check is still owed, and the main folder
already has what it needs: the red run there must show AC-06 failing on "envcheck.py does not exist"
(or passing, once the implementation is in). A self-test failure of the changed checker would show
instead as "AC-06: the envcheck checker:", for every implementation, and CI would show it as well.

Recommended next steps: commit the four files as they are. For F9 and F10 I recommend no third patch:
this is the 4th of 5 budgeted sessions and the 5th is the work review. Hand both to that review as read
checks: the guard is `raise SystemExit(main(...))` or `sys.exit(main(...))` (F9); no path of
envcheck writes file content or the token to a stream or into an exception message (F10: read every
`print(`, `sys.stderr` and `ResearchHostError(` in `envcheck.py`). The owner can ask for an additive
patch instead.

Findings open: 2 (F9 Low, F10 Low). F1–F8: closed, by reading.

## The handoff's claims (round 2)

| Claim | Result |
|---|---|
| Patch SHA-256 `3f7471e5…0ee1` | verified |
| 41083 bytes, 668 lines, LF only, ASCII, no colour escapes | verified (`wc`; Grep finds no CR and no non-ASCII byte) |
| Four changed files, +13 −6, +111 −8, +52 −24, +119 −16; no new or deleted file | verified (`git apply --numstat --summary`) |
| `git apply --check` passes on `f62a101` | verified (exit 0, no output) |
| Base = the round-1 files committed in `8290075` | verified: the seven blobs at `f62a101` equal the round-1 table |
| Post-apply SHA-256 and blobs of the four files | **not verified** (BLOCKED). The patch's `index` lines carry the same 7-character blob prefixes (`8b2bb8d`, `8b02321`, `4c92834`, `33187ab`); that is consistency, not proof. The implementer checked them in the main folder |
| Red run 195 failed, 3364 passed | **not verified**. Verified: the base gives 183 failed, 3364 passed, and the patch adds 12 cases that all need envcheck (F2 2, F4 1, F6 4, F8 5) |
| 204 ENV-002 tests; checker self-test 107 forbidden, 6 allowed | counts verified by reading (192 + 12; 89 + 3 + 15 and 3 + 3); the self-test result is **not verified** |
| "No earlier case changed", stricter only | verified by reading (section above) |
| Satisfiability 3559 passed; 93 of 93 mutants killed | **not verified** (BLOCKED) |
| M86 survived first, then fixed by a token that stands alone | the byte facts are verified by probe 3 |

## Checks
Worktree detached at `f62a101`, patch not applied; 2026-11-05, finished 11:46Z.

| Command | Result | Commit | Time (UTC) |
|---|---|---|---|
| `git status --short`, `git rev-parse HEAD` | ` M docs/handoff/ENV-002.md` only; `f62a1014…` | f62a101 | by 11:46 |
| `sha256sum docs/proposals/ENV-002-tests-r2.patch` | `3f7471e5d644622ec5539211fdb3bd114f40b89b49866e3a1f021ae47fcf0ee1`, equal to the handoff | f62a101 | by 11:46 |
| `git apply --check docs/proposals/ENV-002-tests-r2.patch` (standalone, read-only) | PASS: exit 0, no output | f62a101 | by 11:46 |
| `git apply --numstat --summary docs/proposals/ENV-002-tests-r2.patch` | `13 6`, `111 8`, `52 24`, `119 16`; no create or delete | f62a101 | by 11:46 |
| `wc -c -l docs/proposals/ENV-002-tests-r2.patch` | 668 lines, 41083 bytes | f62a101 | by 11:46 |
| `git ls-tree -r f62a101 tests/acceptance/ENV-002 tests/architecture/test_imports.py` | seven blobs, equal to the round-1 table | f62a101 | by 11:46 |
| `git archive f62a101 \| tar -x -C <scratchpad>\tree` | done | f62a101 | by 11:46 |
| `cd <scratchpad>\tree && git apply <worktree>\docs\proposals\ENV-002-tests-r2.patch` | **BLOCKED** by guard-bash (below); not retried in any form | – | by 11:46 |
| `cd <scratchpad>\tree && uv run --offline --no-sync --project <worktree> python -I -B -m pytest tests -q -p no:cacheprovider --tb=no -rN` (the tree **without** the patch) | exit 1 as expected: **183 failed, 3364 passed in 44.53s** | f62a101 (scratch copy) | by 11:46 |
| `uv run --offline --no-sync --project <worktree> python -I -B <scratchpad>\probes\probe_cpython.py <scratchpad>\probe-work` | Python 3.12.15 win32; the four results quoted above | – | by 11:46 |

Red-flag patterns of `scripts/controls/red-flags.sh` (plus `skipif`, `importorskip`, `pytest.skip`) on the
patch's added lines (Grep): no match. The one `except Exception` in the patch (p:319) is a context line
that round 1 already judged.

## Checked, nothing found (and how)
- Tests against contract v1.8, by reading: the F2, F4, F6 and F8 expectations line by line; the F8
  scope per root; the stricter AC-05 checks. Nothing asserts a v1.7 behaviour that v1.8 changed.
- Tests against each other: the new cases beside round 1's read rules. The UTF-16 files are `.txt` in
  a data dir and may be opened; the vault file and the cloud-only manifests may not; `must_not_open`
  walks the fake host after the recording ends, so a refused listing does not disturb it; AC-05's
  `recording()` calls keep an empty `deny_list`.
- The changed checker, by hand: `bind` never raises (bindings hold only str until the loop ends);
  whether a conflict is found does not depend on the walk order, because each pass binds every
  assignment again (the line it reports can); a third library under one name adds no second finding; names in conflict resolve to None, and every
  caller of `_envcheck_resolve` handles None.
- The sub-key rule on legitimate code: a sub-key that is a name, a call (`EnumKey`) or a concatenation
  gives no finding; the two Uninstall keys pass in any case, with `/` and with a trailing backslash.
- Hygiene: no skip, only or xfail; LF and ASCII; fakes only under `tests/`; no new file, so basenames
  stay unique; the only new import is `codecs` (stdlib), and no test imports a Windows module.
- Linux, by reading: the refusal is made by the audit hook, not by file permissions, so it does not
  depend on the user (root included); paths come from `Path`; `sys.stdlib_module_names` is the same
  on every platform.
- The post-run detector reported nothing in this session, and the worktree holds no applied patch.

## Not checked (and why)
- The patched tests by execution, the changed checker's self-test, satisfiability and mutants: BLOCKED
  (below). The brief leaves satisfiability and mutants against the real implementation to the work
  review.
- The four post-apply hashes: BLOCKED for the same reason.
- The tests on Linux: UNKNOWN until CI runs (this host is Windows 11).
- Reparse points not being entered (v1.7 F8): no acceptance test exists; it rests on the implementer's
  unit tests and the work review. `collect`, the real `default_roots` and the terminal path helper
  (v1.8 included): `tests/unit/app/` and the work review, as in round 1.
- The author's scratch reference and mutant files: outside my scratchpad, not read.
- `git apply -R --check`: not run; this session applies nothing.

## Blocks
One call was refused, and I did not retry it with another form, tool or script:

```
PreToolUse:Bash hook error: [node "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.mjs"]: Blocked by .claude/hooks/guard-bash.mjs: git apply must be one standalone literal command. Run each action separately.
```

The command was `cd "<scratchpad>/tree" && git apply "<worktree>/docs/proposals/ENV-002-tests-r2.patch"`.
By my reading of the guard (:426–433, :471–491, :540–550) the brief's other form, a standalone
`git apply --directory=<scratch> …`, would be refused as well: an option before the patch file ends
the D-006 exception, and the guard then judges the patch's targets as locked paths of the repository.
I did not run it.

Question for the owner: how should a tests reviewer get the patched tree? Either guard-bash learns one
more literal form for `git apply` into a folder it can prove lies outside every repository, or the
implementer builds that tree and gives the reviewer its path.

Left in my scratchpad
(`C:\Users\MSI\AppData\Local\Temp\claude\31dcb7d81c2611c3\a8919a7b-8e01-4172-8ee0-944de4ae7da1\scratchpad\`):
`tree\` (a `git archive` of `f62a101`, without the patch), `probes\probe_cpython.py`, and `probe-work\`
(two folders and two one-line files the probe made). Nothing in the repository was edited, staged or
committed except this file.
