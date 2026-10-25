# Review SPIKE-002 round 1 · base 67bb4df (approved contract) · head 4f4932f · reviewer Claude Code (fresh session, Opus 5.5, extended role swap, 2026-10-25 +07)

Scope: `git diff 67bb4df...4f4932f`, which has 4 files: `spikes/SPIKE-002/probe.py`, `spikes/SPIKE-002/test_probe.py`,
`docs/runbooks/SPIKE-002-remeasure.md` and `docs/handoff/SPIKE-002.md`. I read them against contract
`docs/contracts/SPIKE-002-vps-remeasure.md` v1.2 (in full) and DECISIONS.md D-022. The reuse sources were
`spikes/SPIKE-001/probe.py`, its results and `docs/evidence/SPIKE-001.md`. I read the handoff only after my first pass.

I wrote one file: this review. I did not edit the probe or its tests, and I staged, committed and pushed nothing.
The oracle, hunts and mutants live outside the repository in
`C:/Users/MSI/AppData/Local/Temp/claude/c--Users-MSI-Desktop-------------Sochron1k/ae73a189-359c-4302-bc45-421f865f8f01/scratchpad/s2r1/`
(`oracle.py` does not import the probe; `hunt_a.py` … `hunt_e.py`, `mutants.py`, `survivors.py`, `mut/`).
Terminal access: none here. No MetaTrader5 package was installed, no terminal connection was made, and no credential store was opened.

**Result:** the code follows the contract. Every hunt agreed with my oracle, and 10 of the 11 required mutants are killed.
There are 7 findings, all open: 2 Medium and 5 Low (one of the Low is a question).
- F1: a test gap on the post-cutoff boundary. The "M1 search continues past the cutoff" mutant survives.
- F2: the runbook's `git pull` does not get or record the reviewed probe.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Medium | confirmed | `spikes/SPIKE-002/test_probe.py:390-395` (guards `probe.py:218-245`) | These mutants each pass 53/53: **M07** (search runs to 2027, no `min(…, CUTOFF_UTC)`), **M07b** (`start > CUTOFF_UTC`: one extra month at the cutoff) and **M12** (`return UNKNOWN` instead of `None` when no M1 exists before the cutoff). The only cutoff test uses M1 from 2014-01-14, so the search stops at request 109 (2014-01) and never comes near 2025. On my recording terminal with M1 from 2026-07-10, M07 returns `first_m1_utc = "2026-07-10"` after 19 requests past the cutoff. M07b returns `"2025-01-02"` for M1 from 2025-01-02. The committed probe returns `null` after 240 requests, all ending ≤ 2025-01-01 (`survivors.py`, `hunt_d.py`). | A later edit of the month search (for example, a fix round for a new build), run on a VPS whose M1 history has not loaded back before 2025. SPIKE-001 runs 2–3 were in that state (≈100,000 M1 bars). | A post-cutoff date and post-cutoff requests can return while the tests stay green. That breaks contract Invariants (line 69) and AC-05. The runbook's rerun table relies on `null` vs `"UNKNOWN"`, and that is untested too. The current code is correct (hunt d). | Add a test where the scripted terminal's M1 starts after the cutoff (for example 2026-07-10), plus the empty-array variant. Assert `first_m1_utc is None`, exactly 240 requests, every start < `CUTOFF_UTC` and every end ≤ `CUTOFF_UTC`. Optional: a bar exactly at 2025-01-01 00:00 still gives `null`. | M07, M07b and M12 fail the new test, and 4f4932f passes it. |
| F2 | Medium | confirmed | `docs/runbooks/SPIKE-002-remeasure.md:28-33`, `:36-42` | Step 3 says only `git pull`. The probe exists only on `spike/SPIKE-002-vps-remeasure`, and `git branch -r --contains 4f4932f` prints nothing, so the branch is not pushed. Contract Plan step 3 → 5 (line 95) and handoff "Next" 2 → 4 put the VPS run **before** the PR, so `main` will not have the probe at run time. Neither step asks the owner to send back the commit that ran. The JSON cannot carry it, because the contract fixes the field list. | The VPS clone (HTTPS clone of the public repo, ENV-001 line 155) is on `main`. `git pull` succeeds, then CPython prints `can't open file '…\spikes\SPIKE-002\probe.py': [Errno 2]` and exits **2** with no `REFUSED` line. Or a clone left at an older commit runs a probe nobody reviewed. | The owner loses a session (≈30 min with the history wait). The runbook's exit-2 row reads the failure as an argument or account refusal. The evidence cannot record "command → result → commit → time" (AGENTS.md, Tests and evidence). It fails safe: nothing reads the account. | Claude pushes the task branch first (D-006). Step 3: `git fetch origin`, then `git switch --detach <reviewed sha>` (or `git switch spike/SPIKE-002-vps-remeasure` and `git pull --ff-only`), then `git rev-parse --short HEAD` and `git status --short` (the second must print nothing). Step 4: paste the hash together with the JSON. | The runbook names the branch or commit and includes the hash step. The evidence table records a hash equal to the reviewed head. |
| F3 | Low | confirmed | `spikes/SPIKE-002/probe.py:85-87`; runbook `:38` | `_ArgumentParser.error` passes on argparse's message, and that message quotes unknown tokens. `GOOD + ["123458107"]` gives `REFUSED (exit 2): arguments: unrecognized arguments: 123458107`. `--password SECRET-SHOULD-NOT-ECHO` is echoed word for word (hunt b). Runbook line 38 tells the owner to copy that line back to Claude. | The owner mistypes a flag that carries the full login (for example `--account 123458107`) or leaves a stray token. | The full account number, or anything typed, goes into the chat and possibly the evidence. That goes against contract Q3 (results mask the account to the last 4 digits). The runbook's visual check (line 42) reduces the risk. | When the message quotes values ("unrecognized arguments"), raise a fixed text without them instead, for example `arguments: unrecognized arguments (values not shown); use the runbook command`. | New test: `GOOD_ARGS + ["123458107"]` gives exit 2, and `123458107` is not in stderr. It fails on 4f4932f and passes after the fix. |
| F4 | Low | confirmed | `spikes/SPIKE-002/test_probe.py:179-192` (guards `probe.py:137-139`) | Two mutants pass 53/53. **M09c** puts the full login in the refusal (`account 123450001 is not the authorized account`). **M22** uses `suffix in login` instead of `endswith`. Under M22, login 810712345 on the authorized server (Demo, `trade_allowed` false) is accepted for suffix 8107: exit 0 and a report for `****2345`. The tests only check a reason substring, and their wrong login has no "8107" in it. | A regression in `check_account` or in its message. | The full login lands in the line the owner pastes back, or a different Demo account is measured and AC-02 is judged on it. That stays read-only, and you only see it if the evidence writer compares `****2345` with the suffix. | In the parametrized refusal test, assert the full login is absent from the message and `****0001` is present. Add the case `account(login=810712345)` → exit 2. | M09c and M22 fail, and 4f4932f passes. |
| F5 | Low | confirmed | `spikes/SPIKE-002/test_probe.py:256-262` | `assert "MetaTrader5" not in sys.modules` always holds here: the project environment has no MetaTrader5, and a failed import leaves no entry. Only the exit code catches an import-order regression. **M02a** (import block moved above the argument check) is killed by 13 tests. **M02b** (optional module-level `try: import MetaTrader5 … except ModuleNotFoundError`) passes 53/53. I added an import hook that lets the import succeed, as it would on the VPS. With it, M02b makes 1 import attempt on `main([])` before any check, and the committed probe makes 0 (hunt b: 0 attempts in 30 refusal cases). | A regression that adds an early or module-level optional import. | It breaks contract line 40 ("import MetaTrader5 after the argument check") and no test notices. Safety impact is small: importing does not connect to the terminal, and `initialize()` still runs only after the checks. | In that test, insert a `sys.meta_path` finder that records `find_spec("MetaTrader5")` and serves a stub module, then assert zero attempts. `hunt_b.py` shows the pattern. | M02b fails, and 4f4932f passes. |
| F6 | Low | question | contract line 57 (spec list) vs `src/sochron/costs/model.py:234-247` | `H001_COSTS` takes swaps in points (`swap_long_points_per_night = -503.8`). Those are points only when `swap_mode` = 1, which SPIKE-001 run 4 recorded (`"swap_mode": 1`). `spread_fallback_points = 240` comes from SPIKE-001's measured `"spread": 240`. The contract's closed spec list has neither `swap_mode` nor `spread`, so AC-03 ("every value matches") cannot re-measure these two. Also, `swap_rollover3days` uses MT5 day numbers (Sunday = 0, so 3 = Wednesday), while `triple_swap_weekday = 2` uses Python's (Monday = 0). | Writing `docs/evidence/SPIKE-002.md` for AC-03. | A change of swap unit or spread on the VPS server would go unseen. Comparing the raw 3 with 2 would look like a mismatch that isn't one. | Owner decision. The probe must keep AC-05's exact keys, so the code should not change on its own. Either add `swap_mode` to the contract field list (it is a spec value, not a price), or have the evidence say that the swap unit and the spread fallback are carried over from SPIKE-001, not re-measured. In both cases, convert the MT5 day number before comparing. | The AC-03 evidence marks each `H001_COSTS` input as re-measured or carried over, and shows the day conversion. |
| F7 | Low | confirmed | `docs/handoff/SPIKE-002.md:13-14`, `:40`; `probe.py:16-18` | (a) The handoff says "see the commit message for the count and time". The 4f4932f message has the counts (53 passed, red-flags 0 groups) but **no time**. (b) "It never requests a range at or after the cutoff" (handoff `:40`, and the docstring says the same). The last request is `copy_rates_range(…, 2024-12-01, 2025-01-01 00:00)`. If `date_to` is inclusive (MQL5 CopyRates semantics; not verified here), that request covers the cutoff instant. A bar exactly at 2025-01-01 00:00 is then dropped by the `< hi` filter (`probe.py:242`; hunt d's "first bar exactly at cutoff" case gives `null`), so the output is unaffected. | Reading the handoff as the record of checks. | The check record lacks the time that AGENTS.md requires, and the boundary wording claims slightly more than the code does. | Add the time and commit to the handoff's check lines. Reword (b) to: "requests end at the cutoff instant; bars at or after it are dropped." | Handoff updated. No code change needed. |

### Mutants (implementer's tests, unchanged, run on each mutated copy in `s2r1/mut/`)

| Mutant | Result | Killed by (first tests) |
|---|---|---|
| M01 `terminal_info().trade_allowed` decides | killed (9 failed) | `test_ac01_account_flag_decides_not_the_terminal_flag`, `test_ac01_wrong_account_stops_before_any_other_read[...]`, `test_ac01_not_logged_in_is_exit_3` |
| M02a MetaTrader5 import moved before the argument check | killed (13 failed) | `test_ac01_bad_or_missing_arguments_exit_2_without_importing_metatrader5[*]` (via exit 3 ≠ 2) |
| M02b optional module-level import (extra variant) | **survived** | F5 |
| M03 `market_open` uses the offset | killed | `test_ac04_fresh_ticks_shifted_two_hours_are_open_and_shifted` |
| M04 weekday ignored | killed | `test_ac04_fresh_ticks_on_saturday_are_closed` |
| M05 tolerance 121 s / M05b 119 s | killed / killed | `test_ac04_offset_class_rule[offsets1-True-None]` / `[offsets0-True-0]` |
| M06 offset class from the mean | killed | `test_ac04_offset_class_rule[offsets1-True-None]` |
| M07 M1 search continues past the cutoff | **survived** | F1 |
| M07b one month requested at the cutoff (extra) | **survived** | F1 |
| M08 extra JSON field (`identity.terminal_name`) | killed | `test_ac05_report_has_exactly_the_contract_fields` |
| M09 login not masked in the JSON | killed | `test_ac05_values`, `test_ac05_no_tick_time_price_or_full_login_in_the_output` |
| M09c full login in the refusal message (extra) | **survived** | F4 |
| M10 refusal reads `symbol_info` first | killed (7 failed) | `test_ac01_wrong_account_stops_before_any_other_read[*]`, `test_ac01_not_logged_in_is_exit_3` |
| M11 exit 2 for an `initialize` failure | killed | `test_ac01_initialize_failure_is_exit_3` |
| M12 no pre-cutoff M1 reported as UNKNOWN (extra) | **survived** | F1 |
| M13 out-of-range bars not dropped (extra) | killed | `test_ac05_out_of_range_bar_is_not_taken_as_data`, `test_ac05_m1_search_never_reaches_the_cutoff` |
| M14 `trade_allowed` checked before Demo (extra) | survived, harmless | Every account that fails either check still exits 2, with the sequence `initialize, account_info, ACCOUNT_TRADE_MODE_DEMO, shutdown` (hunt c). Only the message changes, and only for an account that fails both checks. |
| M15 expiry at equality refused (extra) | survived, harmless | The difference is a single instant. AC-01 reads "valid-until that has passed", and the probe keeps SPIKE-001's `now > valid_until`. |
| M22 suffix matched anywhere in the login (extra) | **survived** | F4 |
| M24 Demo compared with literal 0 (extra) | survived, harmless | MetaTrader5's DEMO value is 0 (SPIKE-001 run 4: `account_trade_mode` 0, `account_trade_mode_is_demo` true). The contract also tells the tests to use numeric modes. |
| M27 banker's rounding of offsets (extra) | survived, harmless | It differs only at an exact .5 s, in a display value. The class is computed from integer ms, and the contract does not fix tie-breaking. |
| M00 unmutated copy | 53 passed | Sanity check that the copied tests run. |

All 11 required mutants (M01, M02a, M03, M04, M05, M06, M07, M08, M09, M10, M11) were run. **M07 survives**; the other 10 are killed.

## AC status
PASS here covers only the unit-level evidence named in each row. UNKNOWN does not count as passed.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS (unit) | **Arguments:** 30 bad-argument cases exit 2 with no MetaTrader5 import attempt, checked with a live import hook (hunt b). The 53 tests pass, and the code has no built-in Authorization value. **Refusals:** every refusal path calls only `initialize`, `account_info`, the DEMO constant and `shutdown` (hunt c). That covers server, suffix, contest 1, real 2, `trade_allowed` True/None/0 with the terminal flag True, a missing DEMO constant and the path through `main`. **Exit 3:** `initialize` failure and not-logged-in exit 3. **Test gaps** (the behaviour is correct): F4, F5. |
| AC-02 | UNKNOWN | The owner's VPS run (L4) is pending. That needs ENV-001 to pass and the Authorization table filled. |
| AC-03 | UNKNOWN | The VPS run is pending. F6: two `H001_COSTS` inputs cannot be re-measured with the contract's field list. |
| AC-04 | UNKNOWN (unit part PASS) | **Unit part:** tests for +7200 → open/7200, stale → closed/null, Saturday → closed/null, a Wednesday clock and a non-waiting sleep. My oracle agrees in 200,000 random sample sets and 3,000 full runs (hunt a). **VPS part:** pending. |
| AC-05 | UNKNOWN (key list PASS) | **Keys:** the exact-key test passes and M08 is killed. **Leak scan:** 1,500 randomised runs show no tick time, bid/ask, full login, path, large integer or extra post-cutoff date (hunt e). **Post-cutoff search:** the behaviour is correct (hunt d), but no test guards it (F1). **VPS part:** pending. |
| AC-06 | UNKNOWN | **Red flags:** 0 groups, so the "Order or account mutation surface" group is empty. **Spike tests:** 53 passed. **Suite:** 3355 passed, 0 skipped. **Allowed names:** the scripted terminal checks that the called names are a subset of the allowed list. **CI:** not run, because the branch is not pushed. |

## Checked, nothing found (and how)
- **Scope (F06, F02, F04/F18):** the diff touches 4 files, all on the contract's allowed list. Nothing changed in `spikes/SPIKE-001/**`, `src/**`, `tests/**`, `pyproject.toml`, `uv.lock`, `.github/**` or `.claude/**` (`git diff --stat 67bb4df...HEAD`). No dependency was added. `src` never imports the probe (Grep `spike002|SPIKE-002|spikes` in `src` found nothing).
- **Arguments:**
  - all four arguments are `required=True` with no defaults.
  - `--login-suffix` must match `[0-9]{4}` exactly. Fullwidth digits, Arabic-Indic digits, a newline, spaces, 3 or 5 digits and the full login are all refused.
  - `--valid-until` must parse with `fromisoformat` and carry an offset. Naive values, date-only values, month 13, `+25:00`, words and empty strings are refused.
  - The boundary is accepted at equality and refused at 1 µs past it.
  - Accepted forms: `Z`, `+07`, a space separator, a padded server name (stripped before comparing), and the abbreviation `--login` (argparse; the value is still validated). All of these lead to the import and then `initialize` (hunt b).
- **Order and exit codes:**
  - The order is argument and expiry check, then import, then `initialize`, server, suffix, Demo, `account_info().trade_allowed is False`, then everything else. Exit 2 for refusals, exit 3 for an `initialize` failure, not-logged-in and a missing package.
  - The probe reads the DEMO constant even on the not-logged-in path. That is a harmless constant read.
  - `trade_allowed` comes from `account_info`. In SPIKE-001's JSON it is a real boolean, so `is not False` is safe.
- **Allowed calls:** `ALLOWED_CALLS` equals the contract's list. A full run's ordered surface is `initialize, account_info, ACCOUNT_TRADE_MODE_DEMO, terminal_info, symbol_info_tick×5, symbol_info, copy_rates_range/TIMEFRAME_M1 ×109, copy_ticks_from, COPY_TICKS_ALL, shutdown`. Nothing is outside the list plus 3 constants (hunt c). `version` is allowed but never called.
- **Sampling:** 5 samples, with sleeps of `[20, 20, 20, 20]` through the injected `sleep`. The machine clock comes from the injected `now()`. A missing tick gives `null` for that sample and no class.
- **`market_open`:** needs at least 3 strict increases and a Mon–Fri UTC start day, and never uses the offset. A fresh Sunday 22:30 UTC run reads closed, and a Friday 23:59:30 UTC start reads open, both as the contract says.
- **`offset_class_s`:**
  - Using the first sample's nearest hour is the same as "every sample within ±120 s of some multiple of 3600", because 120 s is much less than 1800 s. The oracle confirms it, including ±120.000 s (in), ±120.001 s (out), −3600, half an hour (null), and `null` when closed.
  - The ±120 s bound includes its edge, matching `timebase.classify_offset`.
  - Recorded offsets round half away from zero, with 0 mismatches in 50,000 cases.
- **M1 and first tick:**
  - The search covers 240 contiguous half-open months, 2005-01 to 2024-12. Every start is before the cutoff and every end is at or before it.
  - An out-of-range bar is dropped, whether it comes before or after the range.
  - A failure before the first data gives UNKNOWN, while a failure after the data is never reached.
  - If `maxbars` is not 100,000,000 (I tried 100,000, 0, None, 2³¹−1, 99,999,999 and the string "100000000") the result is UNKNOWN with no requests. `100000000.0` counts as Unlimited, which is harmless.
  - 3,000 random histories agree with the oracle (hunt d).
  - The first tick is reported as a date only, from `ticks["time"]`.
- **Output content:**
  - `login_masked` is `****` plus the last 4 digits. Refusal messages mask the login and do not print the server.
  - Neither terminal path is printed, only `terminal_path_kind`.
  - `started_utc` has minute precision.
  - Packages are read through `importlib.metadata` and `platform`. In the project environment they read MetaTrader5 and numpy "not installed", tzdata 2026.5 and Python 3.12.15.
- **Security:**
  - The probe reads no file, has no network path besides the MetaTrader5 IPC, writes nothing to disk, takes no password argument and builds in no credential.
  - The `clock_sync` text is passed through from the owner.
  - It never touches the holdout: the only post-cutoff value is `first_tick_utc` at day precision. Offsets plus a minute-precision start allow the run moment to be rebuilt to about a minute. That is the run time itself, not market data, and both fields are in the contract.
- **Negative cases:** every case in the contract maps to a passing test or a hunt case. That covers expiry, server, suffix, mode 1/2, `trade_allowed` true, exit 3, no arguments, closed market, a +7200 shift, spread beyond 120 s, `maxbars` not Unlimited, and package "not installed".
- **Runbook against the contract and D-022:**
  - **Command:** it matches D-022 character for character: `--no-project --python 3.12.15`, three `--with` pins, 4 arguments.
  - **uv:** it asks for uv ≥ 0.13.4, as D-022 requires.
  - **Timing:** Tue–Thu 09:00–23:00 +07 is 02:00–16:00 UTC on the same weekday. That keeps clear of the daily break, which is 03:58–05:00 +07 now and 04:58–06:00 +07 after the US DST change on 2026-11-01. Both match SPIKE-001's EDT and EST break observations, and the window avoids weekends.
  - **Clock sync:** `w32tm /resync` then `/query /status`, with the two lines joined, as AC-04 asks.
  - **Login:** it says to log in with the investor password, and exit 2 tells the owner to log in again with it.
  - **Max bars:** set it to Unlimited, restart, open the M1 chart and wait at least 15 minutes. SPIKE-001 needed about 14.
  - **Send-back:** the JSON goes back as text over the text-only clipboard (ENV-001 (ค), approved) or by typing (D-021 item 4).
  - **Credentials:** it asks only for the last 4 digits and a valid-until, never for a password or the full account number, and it adds a visual check before pasting.
  - **Rerun table:** it matches the probe's outputs, except that it says nothing about a `null` or UNKNOWN `first_tick_utc`. Claude can interpret those at evidence time, so this is not a finding.
- **Handoff conventions:**
  - Items 1–12 (stderr refusals; argparse errors as exit 2; exit 3 for a missing package; check order and fail-closed flags; masking; ms arithmetic and rounding; `market_open`; offset class; `first_m1_utc` values; dropping the day-before tick check to keep post-cutoff reads to one value; `terminal_path_kind` `null` when unknown; spec keys always present) are sound and inside the contract, and the code matches them.
  - The `null`/UNKNOWN split is consistent with the runbook table. The only gaps are F1 (untested) and the F7 wording.
  - Item 13 is true: `pytest spikes/SPIKE-001 spikes/SPIKE-002` fails at collection with pytest's same-basename error.
  - Item 14 (test names that avoid placeholder words in the scanner) is disclosed. `probe.py` has no placeholder, and the scan for order and account mutations is unaffected, so I accept it.
  - The "Not tested" list is accurate.
- **Untracked folders:** `spikes/SPIKE-00{1,2}/.mypy_cache/` are git-ignored and were created at 18:33 +07, before this session's first command at 18:44 +07. I left them.

### Checks run (2026-10-25, +07, head 4f4932f)
| Command | Result | Commit | Time |
|---|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` | PASS: 53 passed in 0.10s, exit 0 (uv warns that `VIRTUAL_ENV` points to the main checkout's `.venv` and is ignored) | 4f4932f | 18:44:51 |
| `PYTHONDONTWRITEBYTECODE=1 timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` | PASS: 3355 passed in 31.58s, 0 skipped, exit 0 | 4f4932f | 18:44:53–18:45:25 |
| `bash scripts/controls/red-flags.sh main` (main = a11bff7) | PASS: "Pattern groups with hits: 0", exit 0. No control files touched, no deleted tests, no untracked files. The changed-file list also includes the contract commits under PR #23 (base 67bb4df). | 4f4932f | 18:44:56 |
| Hunts a–e through `uv run --offline python <scratch>/hunt_X.py <probe path> <scratch>` | PASS: (a) 200,000 + 3,000 cases, 0 mismatches. (b) 30/30 refused, 0 import attempts. (c) 20/20 refusal paths correct. (d) 13 named cases, 7 `maxbars` values and 3,000 random cases, 0 mismatches, 0 requests past the cutoff. (e) 1,500 runs, 0 leaks. Hunt e flagged 7 runs, and all 7 were chance matches with allowed fields (masked login digits, the `started_utc` minute), checked by printing the matched text. My first hunt-d run had a modelling error in my own fake (a `None` reply means a failed call); I fixed the fake, not the probe. | 4f4932f | 18:46–18:55 |
| `uv run --offline python <scratch>/mutants.py …` and `survivors.py` | 22 mutants: 12 killed, 6 survivors are findings (F1, F4, F5), 4 survivors are harmless. The unmutated copy passes 53. | 4f4932f | 18:52–18:56 |
| `uv run --offline pytest spikes/SPIKE-001 spikes/SPIKE-002 -q -p no:cacheprovider` | ERROR at collection (same basename): confirms handoff item 13 | 4f4932f | 18:54 |
| `uv run --offline python spikes/SPIKE-002/no_such_probe.py` | Exit 2, with `can't open file … [Errno 2]` and no `REFUSED` line (the F2 trigger) | 4f4932f | 18:58 |
| `git branch -r --contains 4f4932f`; `git status --short --ignored spikes/ docs/` | Empty (not pushed). Only the ignored `.mypy_cache` folders, which predate this session. | 4f4932f | 18:54–18:55 |

## Not checked (and why)
- **Real terminal behaviour (no MetaTrader5 or terminal here; the instructions forbid installing one):**
  - whether `copy_rates_range`'s `date_to` is inclusive;
  - the Unlimited `maxbars` value on the VPS build (the probe reports the raw value, so a new sentinel would show up as UNKNOWN plus a number);
  - `symbol_info_tick` on a closed market;
  - timing of 109–240 monthly requests.
- **Elevated PowerShell:** step 2 opens PowerShell as Administrator, and step 3 does not say which window to use. I did not verify whether an elevated Python attaches to a terminal that is not elevated. Consider telling the owner to use a normal window for step 3.
- **The D-022 environment** (`uv run --no-project …`) was not run, and the OSV advisory check was not repeated. D-022 records it at 2026-10-25T09:56Z.
- **Other checks not run:**
  - CI, because the branch is not pushed;
  - type checks of the spike code, which the contract does not require;
  - ENV-001 and ENV-002, beyond the clipboard and VPS-clone lines this runbook depends on.
- **Delivery state:** this review does not move it. It stays at implemented.

Ready for PR: no. The probe's behaviour matches the contract and is safe to run. Fix F1 (test) and F2 (runbook) and re-check them before the owner's VPS run. F3–F5 and F7 are quick Low fixes. F6 needs the owner's answer on the contract or the evidence wording. The PR follows the VPS evidence (contract Plan step 5).

Findings open: 7
