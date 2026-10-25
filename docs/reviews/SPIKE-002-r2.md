# Review SPIKE-002 round 2 · base 67bb4df (approved contract; merge-base with main 1c5c5f8) · head e077fa6 · reviewer Claude Code (fresh session, Opus 5.5, extended role swap, 2026-10-25 +07)

Scope: a narrow re-check. I looked only at the round-1 findings F1–F7 (`docs/reviews/SPIKE-002-r1.md`, which reviewed 4f4932f),
the commits that answer them (`git diff 4f4932f..e077fa6`: d654016, 182d2d7, c8fa0d9, 1b8b2dc, f22a6a1, fb20009, f8d7aa1, e077fa6),
and any new defect those commits introduced. I read them against contract `docs/contracts/SPIKE-002-vps-remeasure.md` v1.2
and the handoff's "Findings response" table. I am neither the implementer nor the round-1 reviewer.

I wrote one file: this review. I did not edit the probe or its tests, and I staged, committed and pushed nothing.
Scripts, mutants and scratch clones are in new folders under
`C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/s2r2/`:
`mutants_r2.py`, `mut/`, `behaviour_r2.py`, `build_checks.py`, `old_probe_new_tests/`, `f8_*`, `leak_*` and `git_full/`, `git_single/`.
Before running anything, I checked that the copies in `src_e077fa6/` match the worktree files by SHA-256 (probe `55f4545a…d6e8`, tests `82f3a849…64ce`).
No MetaTrader5 package was installed, no terminal was contacted, and no credential store was opened.

**Result:** F1–F7 are all closed (F6 by an accepted answer). All 8 required mutant re-runs are killed now, and so are 5 extra variants.
The new tests pass on the old 4f4932f probe, except the 3 F3 tests, which need the probe fix.
There are 3 new findings, all Low, and F9 is a question:
- **F8:** `--help=<login>` and `--=<login>` still echo the typed value.
- **F9:** step 3 of the runbook fails safely on a single-branch or shallow clone.
- **F10:** the handoff's check record and its "Next" list are behind the head.

The code and runbook are ready for the owner's VPS run.

## Round-1 findings

| ID | Sev | Status | Commit | Evidence | Remaining |
|----|-----|--------|--------|----------|-----------|
| F1 | Medium | **closed** | d654016 | New test `test_ac05_no_m1_before_the_cutoff_reads_null_and_never_asks_past_it` (`test_probe.py:492-505`) has 4 cases: M1 from 2026-07-10 with the "late" reply, the same with an empty reply, a bar exactly at 2025-01-01 00:00, and M1 from 2025-01-02 with an empty reply. For each it asserts `None`, exactly 240 requests, every start < cutoff, every end ≤ cutoff, and the last request = (2024-12-01, cutoff). The scripted terminal now treats `date_to` as inclusive (`hi + 1`, `:163`), which makes the cutoff-bar case reachable. **Mutants:** M07 4 failed, M07b 4 failed, M12 4 failed, and X4 (`<= hi`: bar at the cutoff kept) 1 failed. **Old probe:** 4f4932f passes these tests (`old_probe_new_tests`: only the 3 F3 tests fail). | – |
| F2 | Medium | **closed** (code and runbook; the hash in the evidence can only be checked after the VPS run) | f22a6a1 | **Runbook changes:** the "before you start" checklist now says Claude pushes the branch and hands over the reviewed hash (`runbook:13`). Step 3 uses a normal, non-Administrator PowerShell window and runs `git fetch origin` → `git switch --detach <hash>` → `git rev-parse --short HEAD` (must match) → `git status --short` (must print nothing), then stops on a mismatch (`:29-37`). Step 4 asks for the hash on the first line (`:46`). There is a row for `can't open file` (`:51`), and `git switch main` comes afterwards (`:67`). **Scratch full clone** (`git clone --no-local --branch main`): fetch exit 0; `HEAD is now at e077fa6 …` with no long detached-HEAD advice; rev-parse `e077fa6`; status empty; the probe's SHA-256 equals e077fa6's; `git switch main` gives `Switched to branch 'main'`. **Hash not on origin** (`1234567`): `fatal: invalid reference`, exit 128, and HEAD stays on main (`1c5c5f8`), so the rev-parse check catches it. This fails safe. | Single-branch and shallow clones: F9. The evidence must record a hash whose `spikes/SPIKE-002/probe.py` is e077fa6's (see Ready for PR). |
| F3 | Low | **closed** for the reported trigger | 182d2d7 | `_ArgumentParser.error` (`probe.py:88-92`) now replaces any message that starts with "unrecognized arguments" with a fixed text. The tests (`test_probe.py:334-356`) cover a stray login, `--account <login>` and `--password …`, plus an abbreviated `--login <login>`. **Revert mutant X3** (fix removed): 3 failed. The 4f4932f probe also fails those 3. I also checked `-- <login>` and `-<login>`, and both get the fixed text. **Does the fixed text hide anything the owner needs?** No. It hides which extra tokens there were, but the owner can see their own command, and the remedy is the same (re-copy the runbook command). Claude still learns the class of error, for example a `--clock-sync` value without quotes. The text stays English: `gettext.find('messages')` gives `None`. | Two other argparse messages still quote typed text, which contradicts the handoff's "the other argparse messages hold option names only" (`handoff:65`): F8. |
| F4 | Low | **closed** | c8fa0d9 | The parametrized refusal test (`test_probe.py:195-213`) asserts that the full login is absent from every account refusal and that `****<last 4>` is present for the wrong-account reason. New case: 810712345 with suffix 8107. **Mutants:** M09c 2 failed and M22 1 failed. The extra X5 (refusal masks with the *first* 4 digits) has 2 failed. The tests pass on 4f4932f. | – |
| F5 | Low | **closed** | 1b8b2dc (+ e077fa6) | **New tests:** `RecordingFinder` plus the `mt5_finder` fixture serve an empty stand-in and count every `find_spec("MetaTrader5")`. A presence check through `importlib.util.find_spec` is counted too. The bad-argument tests assert 0 tries. A fresh load of the probe under the finder catches imports at module level, and a control test proves that the finder sees an import (`test_probe.py:262-331`). **Mutants:** M02b 1 failed (the fresh-load test) and M02a 18 failed. X1 (module-level `importlib.import_module` with `except ImportError`) 1 failed, and X2 (optional import in `main` before the argument check) 14 failed. **Leaks:** a later test file that looks for leftovers passes after the real tests (65 passed). After the M02b failure, the stand-in, the finder and `find_spec` are all clean, and only the fresh probe copy stays under its own name, `spike002_probe_fresh`. Nothing imports that name, and it is left only when a test has already failed. The combined run `pytest spikes/SPIKE-002 tests` gives 3419 passed (64 + 3355). | – |
| F6 | Low (question) | **closed**: the answer is sound and inside the contract | fb20009 | **The answer** (`handoff:68`): no contract change. AC-03's evidence will mark every `H001_COSTS` input as re-measured or carried over; `swap_mode` and the 240-point spread fallback are carried over from SPIKE-001; MT5's `swap_rollover3days` is converted before comparison. **Why it is sound:** (1) AC-05's exact keys stay, so there is no code change, and AC-03 ("every value matches, or the evidence shows each difference") is not weakened: it is applied to the values that can be re-measured. (2) `spread` is a live market value at run time. Adding it would put a post-cutoff market value into the output, against the spirit of Invariant line 69, so carrying it over is the conservative choice. (3) A change of swap unit would show up as a mismatch in the re-measured `swap_long` (SPIKE-001 runs 1–4: `"swap_mode": 1`, `"swap_long": -503.8`). (4) The day conversion is right: MT5's ENUM_DAY_OF_WEEK has Sunday = 0, so Python weekday = (mt5 + 6) mod 7 and 3 → 2 (Wednesday). The probe reports the raw 3 (`test_ac05_values`), so the conversion happens at evidence time, as stated. | Note for the evidence: SPIKE-001 never read `swap_rollover3days` through the API (grep of `spikes/SPIKE-001/` finds nothing). `triple_swap_weekday = 2` comes from a screenshot, with status "assumed" (`src/sochron/costs/model.py:262-264`), so SPIKE-002 is its first API measurement. The owner can veto at PR time. |
| F7 | Low | **closed** as specified | fb20009 | **(b) wording:** the probe docstring (`probe.py:16-19`) and handoff item 9 (`:43`) now say that requests end at the cutoff instant and bars at or after it are dropped, which matches `probe.py:224-251`. **(a) check lines:** they now give the commit and time (`handoff:13-16`, 4f4932f, 18:3x). | The new rows and the final head have no time, and "Next" is stale: F10. |

## New findings

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F8 | Low | confirmed | `spikes/SPIKE-002/probe.py:88-92`, `:104`; `docs/handoff/SPIKE-002.md:65` | `behaviour_r2.py` section 3 on e077fa6, Python 3.12.15. **Values still echoed:** `GOOD + ["--help=123458107"]` and `["--he=123458107"]` give `REFUSED (exit 2): arguments: argument -h/--help: ignored explicit argument '123458107'`, and `["--=123458107"]` gives `… ambiguous option: --=123458107 could match --help, --server, …`. **Same root, older than these commits:** `--help` and `-h123458107` raise `SystemExit(0)` and print the usage on stdout, so the process exits 0, which the runbook reads as success. **Tests:** adding these 5 inputs to `test_ac01_refusal_never_repeats_what_was_typed` gives 5 failed, 64 passed on e077fa6 (`f8_tests_on_e077fa6`). | The owner glues a value to `--help`, an abbreviation of it, or a bare `--`. These are unlikely typos, and the runbook's visual check before pasting (`runbook:53`) reduces the risk. | The full login can still reach the line the owner pastes back (contract Q3). The handoff's F3 sentence claims more than the code does. It stays read-only: nothing reaches the terminal. | In `error`, pass argparse's text on only when it fully matches the value-free messages (`the following arguments are required: …`, `argument --x: expected one argument`), and give a fixed text otherwise. Construct the parser with `add_help=False`. Correct the handoff sentence. | The 5 inputs exit 2 without the login. My sketch (`f8_fix_sketch`: allowlist plus `add_help=False`) passes 69/69, all 64 existing tests included. |
| F9 | Low | question | `docs/runbooks/SPIKE-002-remeasure.md:32` | **Single-branch clone** (`git clone --no-local --single-branch --branch main`, fetch refspec `+refs/heads/main:refs/remotes/origin/main`; `--depth` implies the same): `git fetch origin` exits 0, then `git switch --detach e077fa6` fails with `fatal: invalid reference: e077fa6` (exit 128) and rev-parse prints `1c5c5f8`. `git fetch origin spike/SPIKE-002-vps-remeasure` then lets the same switch succeed. **Why it is open:** ENV-001 fixes "HTTPS clone, no credential" (`ENV-001:39`, `:155`) but not the depth or branches, and no ENV-001 runbook exists yet (`docs/runbooks/` holds only this file). | ENV-001's runbook clones with `--depth 1` or `--single-branch`. | Fails safe: the owner stops at the rev-parse check. The cost is one round trip, and the two lines the owner sends back do not include the `fatal:` line that explains it. | Change step 3 to `git fetch origin spike/SPIKE-002-vps-remeasure`, which works for full, single-branch and shallow clones. Alternatively, make ENV-001's runbook use a full clone. Optionally, ask for all output of step 3. | The runbook text is changed, and the single-branch scratch sequence reaches `e077fa6`. |
| F10 | Low | confirmed | `docs/handoff/SPIKE-002.md:13-17`, `:63-69`, `:78-82` | **Checks table:** it has lines only for 4f4932f. The fix rows give results (57, 61, 62 and 64 passed) and commits, but no times, and there is no line for the final head e077fa6 (spike tests, suite, red flags). The e077fa6 message says "64 passed; mypy … no issues", also without a time. **"Next" list:** item 1 still asks for the r1 review. The push and the hash hand-over, which the runbook now depends on (`runbook:13`), are not in it. | The next session reads the handoff as the record. | AGENTS.md "command → result → commit → time" is not met for those checks, and a next session could miss the push step before the run. The runbook itself is complete, so the run is not at risk. | Add a row per fix commit with its time, plus one for the final head: spike tests, suite, red flags. Update "Next" to: r2 → push the task branch (D-006) → give the owner the hash → VPS run → evidence → PR. | Handoff updated. |

### Mutants (e077fa6 tests unchanged, each run on a mutated copy of the e077fa6 probe in `s2r2/mut/`)

| Mutant | Result | Killed by |
|---|---|---|
| M00 unmutated copy | 64 passed | sanity check |
| M01 `terminal_info().trade_allowed` decides | killed (10 failed) | `test_ac01_account_flag_decides_not_the_terminal_flag`, `…wrong_account_stops_before_any_other_read[*]` ×7, `…not_logged_in_is_exit_3`, `…main_refuses_through_stderr…` |
| M02a import moved before the argument check (the importlib line) | killed (18 failed) | `…bad_or_missing_arguments…[*]` ×13 (finder tries = 1), the fresh-load test, `…refusal_never_repeats…[*]` ×3, `…abbreviated_flag…` |
| M02b optional module-level `import MetaTrader5` | **killed** (1 failed) | `test_ac01_loading_the_probe_and_refusing_never_imports_metatrader5` |
| M07 M1 search continues past the cutoff | **killed** (4 failed) | `test_ac05_no_m1_before_the_cutoff_reads_null_and_never_asks_past_it[*]` |
| M07b one month requested at the cutoff | **killed** (4 failed) | same 4 |
| M09c full login in the refusal | **killed** (2 failed) | `…wrong_account…[acct1/acct2-not the authorized account]` |
| M12 no pre-cutoff M1 reported as UNKNOWN | **killed** (4 failed) | the F1 test ×4 |
| M22 suffix matched anywhere | **killed** (1 failed) | `…wrong_account…[acct2-not the authorized account]` (810712345) |
| X1 module-level `importlib.import_module`, `except ImportError` (extra) | killed (1 failed) | the fresh-load test |
| X2 optional import in `main` before the argument check (extra) | killed (14 failed) | `…bad_or_missing_arguments…[*]` ×13, the fresh-load test |
| X3 F3 fix reverted (extra) | killed (3 failed) | `…refusal_never_repeats_what_was_typed[*]` |
| X4 bar exactly at the cutoff kept, `<= hi` (extra) | killed (1 failed) | the F1 test `[first_m12-late]` |
| X5 refusal masks with the first 4 digits (extra) | killed (2 failed) | `…wrong_account…[acct1/acct2]` |

All 6 round-1 survivors (M07, M07b, M12, M09c, M22, M02b) are killed now, and M01 and M02a stay killed after the importlib change.

## AC status
PASS here covers only the unit-level evidence named in each row. UNKNOWN does not count as passed.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS (unit) | 64 tests pass. The F4 and F5 test gaps are closed, and M01, M02a, M02b, M09c and M22 are killed. Exit codes and import order are unchanged by e077fa6: 7 scenarios give the same results on old and new (below). F8 is about the refusal text, not the exit code: the two remaining echo inputs still exit 2. |
| AC-02 | UNKNOWN | The owner's VPS run (L4) is pending, after ENV-001 and the Authorization table. |
| AC-03 | UNKNOWN | The VPS run is pending. F6's answer defines the evidence wording. |
| AC-04 | UNKNOWN (unit part PASS) | **Unit part:** the tests pass, and `offset_class_s` on e077fa6 gives the same result as on 4f4932f in 300,000 random cases and 9 edge cases (0 mismatches). **VPS part:** pending. |
| AC-05 | UNKNOWN (key list and post-cutoff search PASS) | **Unit part:** the exact-key test passes. The post-cutoff search is now guarded (F1: M07, M07b, M12 and X4 are killed). **VPS part:** pending. |
| AC-06 | UNKNOWN | **Red flags:** 0 groups. **Spike tests:** 64 passed. **Suite:** 3355 passed, 0 skipped. **CI:** not run, because the branch is not pushed (`git branch -r --contains e077fa6` is empty). |

## Checked, nothing found (and how)
- **Scope:** `git diff --stat 4f4932f..e077fa6` touches 5 files: probe, tests, runbook, handoff, and the r1 review in the review channel. Nothing changed in `src/`, `tests/`, `pyproject.toml`, `uv.lock`, `.github/`, `.claude/` or `spikes/SPIKE-001/`. The red-flag scan lists no control files touched, no deleted tests and no untracked files.
- **e077fa6 has no behaviour change.** `behaviour_r2.py` loads both probes and compares them:
  - **`offset_class_s`:** the two versions agree, as recorded under AC-04.
  - **The late import:** `import MetaTrader5 as mt5` and `importlib.import_module("MetaTrader5")` give the same exit code, stderr and number of tries in 7 scenarios:
    - package absent: exit 3, "not installed";
    - `sys.modules["MetaTrader5"] = None`: exit 3;
    - the package imports but `initialize` fails: exit 3, 1 try;
    - the package raises `ImportError` (DLL): both raise it;
    - the package raises `ModuleNotFoundError` for numpy: exit 3, "not installed". The wording is older than these commits, and the D-022 command pins numpy;
    - expired valid-until: exit 2, 0 tries;
    - no arguments: exit 2, 0 tries.
  - **The module object:** in both versions, `run()` gets the object that is in `sys.modules`.
  - **Static controls:** the AC-06 AST test still sees the `mt5.` attributes, because the variable name is unchanged. The architecture test counts `importlib.import_module` as a dynamic import (`tests/architecture/test_imports.py:116`), but it scans `src/` only, so the change hides nothing from a control.
  - **Types:** the `Any` annotations are not a type-ignore, and the "Type checks disabled" scanner group is empty.
- **The F5 fixture cannot leak a stand-in.** `monkeypatch` restores the original `sys.meta_path` list and any prior `sys.modules` entry. The fixture pops the stand-in after `yield`, and that runs even when the test fails. A dedicated after-test and the combined run (3419 passed) both confirm this.
- **The F1 fake is sound:** the inclusive `date_to` leaves the existing 2014 expectations unchanged (they pass on 4f4932f), and it gives the cutoff-bar case a real bar at `hi`.
- **The runbook's git sequence is safe for a public HTTPS clone:**
  - **No credential:** the fetch needs none, and ENV-001 requires an empty `credential.helper` and no userinfo (`ENV-001:101`, `:155`, `:188`).
  - **Detached HEAD:** `git switch --detach` prints a single line, and `git status --short` runs after the switch, so leftover local changes would show up and stop the owner.
  - **Returning to main:** this is clean on a full clone.
  - **Hash not on origin:** this case fails safe, as shown under F2.
- **Red-flag words:** the new test code says "stand-in" and avoids the scanner's placeholder words, and the scan finds 0 groups.

### Checks run (2026-10-25, +07, head e077fa6)
| Command | Result | Commit | Time |
|---|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` | PASS: 64 passed in 0.13s, exit 0 (uv warns that `VIRTUAL_ENV` points to the main checkout's `.venv` and ignores it) | e077fa6 | 19:34:01 |
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: 3355 passed in 42.68s, 0 skipped, exit 0 | e077fa6 | 19:34:01–19:34:45 |
| `bash scripts/controls/red-flags.sh main` (main = 1c5c5f8, merge-base 67bb4df) | PASS: "Pattern groups with hits: 0", exit 0; no control files, no deleted tests, no untracked files | e077fa6 | 19:34:48 |
| `… uv run --offline python <s2r2>/mutants_r2.py <s2r2>/src_e077fa6 <s2r2>/mut` | M00: 64 passed. All 13 mutants killed (counts in the table above). | e077fa6 | 19:31:24–19:31:34 |
| `… uv run --offline pytest <s2r2>/old_probe_new_tests` (4f4932f probe + e077fa6 tests) | 3 failed (the F3 tests), 61 passed: as expected | 4f4932f + e077fa6 tests | 19:31:46 |
| `… uv run --offline python -I <s2r2>/behaviour_r2.py <old probe> <new probe>` | `offset_class_s`: 0 mismatches. Late import: SAME in all 7 scenarios. Argparse: 3 inputs still echo the login (F8). | 4f4932f vs e077fa6 | 19:32:35–19:32:37 |
| `… uv run --offline pytest <s2r2>/f8_tests_on_e077fa6` and `<s2r2>/f8_fix_sketch` | 5 failed, 64 passed / 69 passed | e077fa6 / sketch | 19:33:35–19:33:37 |
| `… uv run --offline pytest <s2r2>/leak_e077fa6/{test_probe,test_zz_after}.py` and the same on `leak_m02b_failing` | 65 passed / 2 failed: the expected M02b kill, plus the after-check showing only `spike002_probe_fresh` left | e077fa6 / M02b | 19:33:48 |
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest spikes/SPIKE-002 tests -q -p no:cacheprovider` | PASS: 3419 passed in 25.13s | e077fa6 | 19:34:56–19:35:22 |
| `git clone --no-local [--single-branch] --branch main <common .git> <s2r2>/git_{full,single}`, then the runbook's step 3 and `git switch main` (Git 2.46.1.windows.1) | Full clone: works, and a missing hash fails safe. Single-branch clone: the switch fails until the branch is fetched by name (F9). | e077fa6 | 19:35:39–19:36:09 |
| `git branch -r --contains e077fa6`; `git status --short` | Both empty: the branch is not pushed and the tree is clean | e077fa6 | 19:30–19:36 |

## Not checked (and why)
- **The VPS side of step 3**, because the scratch clones used a local path: a real HTTPS fetch from GitHub, the Git version on the VPS (`git switch` needs ≥ 2.23), and Git's dubious-ownership check if the clone was made from an elevated shell and step 3 runs in a normal one. Each of these would fail safe at the rev-parse/status check.
- **A credential prompt:** if the repo stopped being public, a fetch with no credential helper would prompt for a username in the console, and the runbook does not say to stop at a prompt. This is older than these commits (`git pull` did the same). Consider adding "if git asks for a username or password, press Ctrl+C and stop."
- **mypy on the probe.** e077fa6 says the editor's bundled mypy 1.15 reports no issues. The contract does not require a type check, and mypy is not a project dependency.
- **Real terminal behaviour**, as in r1: inclusive `date_to`, the Unlimited `maxbars` value on the VPS build, and the timing of 240 requests. **CI:** not run, because the branch is not pushed. **OSV:** not repeated (D-022 recorded it at 2026-10-25T09:56Z).
- **Delivery state:** this review does not move it. It stays at implemented.

Ready for PR: no, as expected, because the PR follows the VPS evidence (contract Plan step 5).
The code and runbook are ready for the owner's VPS run:
- **Before handing over a hash:** Claude pushes the task branch (D-006). The hash Claude gives the owner must have a `spikes/SPIKE-002/probe.py` with SHA-256 `55f4545a209158b34752e2f29750cf8717c3fac53ebfe0745dd2f00142b2d6e8`, the reviewed e077fa6 probe. The evidence should record that.
- **F9:** a one-line runbook change, cheapest to make before the run.
- **F8:** this would change the probe, so either defer it (the runbook command never triggers it) or fix it with a narrow re-check before the run.
- **F10:** documentation only; it can go with the next commit.

Findings open: 3
