# Handoff SPIKE-002: read-only re-measure on the VPS

Contract: `docs/contracts/SPIKE-002-vps-remeasure.md` v1.2 (approved by owner 2026-10-25 17:5x, with D-022).
Branch: `spike/SPIKE-002-vps-remeasure` from `67bb4df` (head of PR #23, which holds the approved contract).
Tier: Standard. Implementer: Claude (this session). Reviewer: a fresh Claude session under the extended role swap (PROGRESS.md), since Codex is out of quota until 2026-10-28 19:41.

## State
- implemented: `spikes/SPIKE-002/probe.py`, `spikes/SPIKE-002/test_probe.py`, `docs/runbooks/SPIKE-002-remeasure.md`.
- Not run on the VPS. The VPS run waits for ENV-001 to pass, and the owner fills the Authorization table (login suffix, valid until) first.
- AC-02 to AC-05 (VPS part) are UNKNOWN until the owner's run. AC-01, the unit part of AC-04, the AC-05 key list and AC-06 (call surface) are covered by unit tests.

## Checks
| Command | Result | Commit | Time (+07) |
|---|---|---|---|
| `uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` | 53 passed | `4f4932f` | 2026-10-25 18:3x |
| `bash scripts/controls/red-flags.sh main` | Pattern groups with hits: 0 | `4f4932f` | 2026-10-25 18:3x |
| Fixes for review r1 (per-fix counts in "Findings response") | 57 / 61 / 62 / 64 passed | `d654016`..`e077fa6` | 2026-10-25 19:0x–19:2x |
| `uv run --offline pytest spikes/SPIKE-002 -q -p no:cacheprovider` | 68 passed | `36dcb22` (code head after review r2) | 2026-10-25 19:41:36 |
| `uv run --offline pytest tests -q -p no:cacheprovider` | 3355 passed, 0 skipped | `36dcb22` | 2026-10-25 19:41:36–19:42:01 |
| `bash scripts/controls/red-flags.sh main` | Pattern groups with hits: 0 | `36dcb22` | 2026-10-25 19:42 |
| bundled mypy 1.15 (editor) on `probe.py` and `test_probe.py` | no issues | `36dcb22` | 2026-10-25 19:42:09 |
| The commit after `36dcb22` changes this handoff and the r2 review file only. | | | |

## Conventions fixed where the contract leaves room
1. **Refusals print one line on stderr:** `REFUSED (exit N): <reason>`. stdout stays empty. Only a success prints the JSON, on stdout.
2. **Argument errors are refusals:** argparse's own error exit is replaced by `Refused`, so every argument problem is exit 2 with the same line format.
   - `--login-suffix` must be exactly 4 digits.
   - `--valid-until` must be ISO 8601 with a UTC offset.
   - `--server` and `--clock-sync` must not be empty.
3. **Exit 3 cases:** a missing `MetaTrader5` package exits 3. So do a failed `initialize` and a terminal that is not logged in (contract: "initialize ล้มหรือ terminal ไม่ได้ login: exit 3").
4. **Account check order:** server → login suffix → `account_info().trade_mode == ACCOUNT_TRADE_MODE_DEMO` → `account_info().trade_allowed is False`.
   - A missing or None flag is refused.
   - A login of 4 digits or fewer is refused.
5. **`login_masked`:** always `****` plus the last 4 digits, as in the contract's example.
6. **Sampling:** each sample reads the machine clock, then `symbol_info_tick`. The offset is computed in integer milliseconds (`time_msc` minus machine ms).
   - `offset_samples_s` rounds half away from zero, to whole seconds.
   - A missing tick gives `null` for that sample, and `offset_class_s` becomes `null`.
7. **`market_open`:** at least 3 strict increases of `time_msc` between consecutive samples, and the start day (UTC) is Monday–Friday.
8. **`offset_class_s`:**
   - Candidate hour: the hour nearest the first sample, computed as `(ms + 1_800_000) // 3_600_000`.
   - Every sample must lie within ±120,000 ms of it, which matches `timebase.classify_offset`.
   - A shift of exactly half an hour gives no class.
9. **`first_m1_utc`:**
   - Values:
     - `"UNKNOWN"` when `maxbars` ≠ 100,000,000, the value SPIKE-001 runs 2–4 recorded for "Unlimited". No range is requested in that case.
     - `"UNKNOWN"` when a month request fails before the first data.
     - `null` when no M1 bar exists before 2025-01-01.
   - Search: month by month from 2005-01 up to 2025-01-01. Every request starts before the cutoff and ends at or before it, so a request ends at the cutoff instant. Bars at or after the cutoff are dropped, because `date_to` may be inclusive. The search stops at the first month with in-range bars.
   - An out-of-range bar is dropped. SPIKE-001 round 2 saw an empty early range return a 2026 bar.
   - The raw time is read as UTC under rule version "1" (offset 0).
10. **`first_tick_utc`:** `copy_ticks_from(XAUUSDm, 2005-01-01, 1, COPY_TICKS_ALL)` gives the date only.
    - `"UNKNOWN"` when the call fails; `null` when no tick is returned.
    - SPIKE-001's day-before check is dropped, to keep post-cutoff reads to the one accepted value.
11. **`terminal_path_kind`:** "portable" when `terminal_info().data_path` equals `path` (normalised), otherwise "installed". `null` if either is missing. Neither path is printed.
12. **`spec`:** all twelve keys are always present. They are all `null` when `symbol_info` returns None.
13. **Test module name:** the tests load the probe under the module name `spike002_probe`, so it never clashes with SPIKE-001's `probe` module.
    - Both spikes keep the file name `test_probe.py`, as the contract states.
    - Collecting `spikes/SPIKE-001` and `spikes/SPIKE-002` in one pytest run hits pytest's same-basename rule. Run each directory alone, as AC-06 does.
14. **Naming in the tests:** they avoid the words that `red-flags.sh` reads as placeholders in code, and the names of order functions. `spikes/` is not a test path for that scanner.

## Findings response (review r1, `docs/reviews/SPIKE-002-r1.md`)

Mutants were re-run on each fix against the committed tests, in new scratch folders under
`scratchpad/s2fix/mut-*` (nothing deleted, as the owner chose on 2026-10-25 after guard-bash blocked an `rm -rf` of an old scratch folder).

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F1 | accept | `d654016` | Four cases with no M1 before the cutoff (history after it, empty replies, a bar exactly at 2025-01-01 with an inclusive `date_to`). Each gives `null` after exactly 240 requests, every start before and every end at or before the cutoff. Mutants M07, M07b and M12 now fail 4 tests each; the new M13 (bar at the cutoff kept) fails 1. `pytest spikes/SPIKE-002` → 57 passed. |
| F2 | accept | `f22a6a1` | **Before the run:** Claude pushes the branch and gives the owner the reviewed hash. **On the VPS:** `git fetch origin`, then `git switch --detach <hash>`, then `git rev-parse --short HEAD`, which must match, and `git status --short`, which must print nothing. Step 3 uses a normal PowerShell window. The owner pastes the hash with the result, and runs `git switch main` afterwards. **Runbook additions:** what a `can't open file` line means, and a rerun row for `first_tick_utc`. |
| F3 | accept | `182d2d7` | An "unrecognized arguments" refusal now gives a fixed text with no values. The new tests (a stray login, `--account <login>`, `--password …`) failed 3/3 before the fix and pass after. An abbreviated `--login 123458107` is refused without echo. The other argparse messages hold option names only. → 61 passed. |
| F4 | accept | `c8fa0d9` | Account refusals never contain the full login, and a wrong-account refusal shows `****<last 4>`. New case: login 810712345 with suffix 8107 → exit 2. M09c fails 2 tests and M22 fails 1. → 62 passed. |
| F5 | accept | `1b8b2dc` | **New check:** a meta_path finder serves an empty stand-in MetaTrader5 and counts every try. Bad-argument refusals must make 0 tries. **Module-level imports:** a fresh load of the probe under the finder catches them. **Control:** a test proves the finder sees an import. M02b fails, and all 8 mutants of this round are killed. → 64 passed. |
| F6 | answered (owner's standing delegation: recommended option; owner may veto) | this commit (handoff only) | **No contract change, because AC-05's exact keys stay.** `docs/evidence/SPIKE-002.md` will mark each `H001_COSTS` input as re-measured or carried over. `swap_mode` (points, SPIKE-001 run 4 `"swap_mode": 1`) and the `spread` fallback (240) are carried over from SPIKE-001, not re-measured. `swap_rollover3days` uses MT5 day numbers (Sunday = 0); it is converted to Python's weekday (Monday = 0) before it is compared with `triple_swap_weekday` (3 → 2 = Wednesday). The alternative was a contract revision adding `swap_mode` and `spread` to the field list. |
| F7 | accept | this commit | **Probe docstring and handoff:** the boundary wording now says requests end at the cutoff instant and bars at or after it are dropped. **Check lines:** the table now names the commit and time. |

## Not tested
- **Behaviour of the real terminal:** run only by the owner on the VPS. This covers:
  - the Unlimited `maxbars` value on the VPS build;
  - `copy_rates_range` timing over 240 monthly requests;
  - the shape of `symbol_info_tick` on a closed market.
- The D-022 environment (`uv run --no-project …`). The unit tests run in the project environment, where `MetaTrader5` and `numpy` are "not installed".

## Findings response (review r2, `docs/reviews/SPIKE-002-r2.md`: every r1 finding closed; code and runbook ready for the VPS run)

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F8 | accept | `dd82371` | Only argparse messages that end with "the following arguments are required: …" or "expected one argument" are shown; every other argparse error gives a fixed text. These are option-name messages for every input except the one r3 F11 constructs (extra words whose last one ends with "expected one argument"). `--help` is off (`add_help=False`), so it is refused with exit 2. New cases `--help=<login>`, `--he=<login>`, `--=<login>` and `--help` failed 4/4 before and pass after. → 68 passed. |
| F9 | accept (question answered with the reviewer's one-line fix) | `36dcb22` | Step 3 runs `git fetch origin spike/SPIKE-002-vps-remeasure`, which brings the reviewed commit into a single-branch or shallow clone too. |
| F10 | accept | the commit after `36dcb22` | The checks table has times and a line for the final code head `36dcb22`; "Next" below lists the push and the hash hand-over. |

## Findings response (review r3, `docs/reviews/SPIKE-002-r3.md`: F8–F10 closed; `5d494ac` fit for the VPS run)

The owner delegated every decision to the recommended option on 2026-11-05 13:4x ("อนุมัติตาม recommended ไปเลย"; veto before merge). That delegation covers this review session and the evidence review after the run, beyond the contract's budget of 2.

| ID | Accept/Dispute | Commit | Evidence (command → result) |
|----|----------------|--------|-----------------------------|
| F11 | accept as a Low residual (r3's recommended timing): the probe is unchanged | this commit (docs only) | r3 shows the trigger needs extra typed words ending in the exact phrase "expected one argument", which the runbook command cannot produce. The exit code stays 2 and nothing reaches the terminal. The runbook's check before pasting (`runbook:53`) still applies. Changing the probe now would move the reviewed hash and need another re-check before the run. Changing it after the run would make the PR's probe differ from the evidence's. The F8 row above is narrowed to match. Follow-up after the PR: match the message whole and pin the two option-name messages with a test (r3's fix sketch: 71 passed). |

The reviewed probe at `5d494ac` has SHA-256 `2002ffd515d72c91ac2cf385361ea70acd965cb37a05f5577b217b1be9382ca5` (blob `2b74fc92…`). The evidence must record this value. The r2 value `55f4545a…` belongs to `e077fa6`. The hash handed to the owner is the pushed head, which touches neither `spikes/SPIKE-002/` nor the runbook after `5d494ac` (only this handoff and the r3 file).

## Next
1. The evidence review after the VPS run re-checks F11's record (covered by the delegation above).
2. Before the VPS run: Claude pushes `spike/SPIKE-002-vps-remeasure` (D-006) and gives the owner the reviewed head's hash. After ENV-001 passes, the owner sends the login suffix and valid-until, and Claude records them in the contract's Authorization table.
3. The owner follows the runbook and pastes the hash and the JSON. Claude saves the result and writes `docs/evidence/SPIKE-002.md`. That covers AC-02 to AC-05, with the F6 rule for AC-03, plus a DECISIONS entry if the build or the offset differs.
4. Evidence review, then PR.
