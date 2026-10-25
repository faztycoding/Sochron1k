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
| Fixes for review r1: see "Findings response" below | | | |

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

## Next
1. A fresh-session review of this branch, against the contract and the diff only, written to `docs/reviews/SPIKE-002-r1.md`.
2. After ENV-001 passes, the owner sends the login suffix and valid-until. Claude records them in the contract's Authorization table. The owner then follows the runbook and pastes the JSON.
3. Claude saves the result and writes `docs/evidence/SPIKE-002.md`. That covers AC-02 to AC-05, plus a DECISIONS entry if the build or the offset differs.
4. PR.
