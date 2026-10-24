# Review CORE-005 round 2 (narrow re-check of r1 F1–F9) · base `origin/main` `b7e0dd2` · head `9431900` · reviewer: pre-review (Claude subagent `fresh-eyes-reviewer`, fresh context, read-only)

Recorded by the implementer from the subagent's final report, unchanged in substance. The owner chose this narrow
subagent re-check on 2026-10-24 because the contract's headless-session budget (5) was used up.

**Ready for PR: yes.** All nine r1 findings are closed or accepted, except F7, which can only be checked once the PR body
exists. Two new Low findings (F10, F11); neither blocks the PR.

Read-only throughout; `git status --porcelain` was empty before, after the suite and at the end. Scratch trees were HEAD's
`src` from `git archive 9431900` with the fixed file replaced by `git show <parent>:<file>`; the runner
`tools\run_tree.py` ran under `uv run --offline --no-sync python -I -B` and printed "PROOF OK: all sochron modules under
<tree>\src" on every run.

## New findings

| ID | Sev | Kind | File:line | Evidence | Impact | Minimal fix |
|----|-----|------|-----------|----------|--------|-------------|
| F10 | Low | confirmed | `src/sochron/data/snapshot/validate.py:123-134` | Side effect of the F1 fix: a repeated bar took the `if seen` branch and skipped the gap check. Probe: chunk 13:30..13:59 first, then 13:00..13:10 + 13:30..13:35 (13:11..13:29 is a real gap). Parent: `time_not_increasing`@13:00 + `unexpected_gap`@13:30. HEAD: `time_not_increasing`@13:00 + `duplicate_time`@13:30..13:35, no `unexpected_gap`. Over 4,000 seeded random sequences, 381 `unexpected_gap` lost, 0 day statuses lowered, 0 lost gaps on a non-STOP day or an unflagged slot. | A real gap has no code in `report.defects` (invariant). Day stays STOP and slot stays flagged, so H001 skipping is unaffected; R1 data-quality counts would undercount gaps. | Check the gap on every forward step; add `time_not_increasing` only for a time not seen. Candidate tested in scratch: full suite 2875 passed, 0 gaps lost, F1 still closed. |
| F11 | Low | confirmed | contract `:71`, `:3`; evidence `:3`, `:14`, `:65` | Contract `:71` still said `incomplete` when `m1_count < timeframe` while the v1.3 Status and the code use missing minutes; `:3` said v1.1; evidence said v1.2 and 2870 passed for AC-07; the F7 row said the PR body lists files, but no PR body existed. | Contract body contradicts its Status; stale numbers. | Amend `:71` and `:3`; fix evidence version and count; word F7 as to be done in the PR body. |

## Verdict per r1 finding
- **F1 closed** (`e52312a`): regression fails on the parent (one `time_not_increasing`, 4 duplicates expected) and passes at HEAD; the r1 overlap series now gives `{03-10: STOP, 03-11: STOP}` and the 00:00 M15 slot carries `duplicate_time`. Side effect: F10.
- **F2 closed** (`da2ba68`): regression fails on the parent and passes at HEAD; the fix can only add `incomplete` (`len(present) <= len(members)`); locked golden `6f46d72c` unchanged and green.
- **F3 accepted limitation**, stated accurately in the contract Status.
- **F4 closed** (`61b75ed`): regression (2 cases) fails on the parent and passes at HEAD; whole minutes still accepted; tz-aware ValueError and str TypeError unchanged. Remainder (`Defect`/`ValidationReport` unchecked) is a recorded limitation.
- **F5 closed** (`e9a0875`): regression fails on the parent and passes at HEAD; the only newly refused input is an aggregated bar fed back to `validate_m1`, not a contract flow; `Bar` still constructs with `m1_count` 3 (v1.1 item 1).
- **F6 accepted limitation**; wording verified: 200 bars with weeks newest-first take 0.44 s with `max_gap_minutes` 5, the same as sorted.
- **F7 open until the PR body exists**; the diff still carries `docs/contracts/CORE-004-costs-hardening.md`, `docs/evidence/CORE-004.md` and `docs/contracts/CORE-006-strategy-h001.md`.
- **F8 closed**: the test asserts `len(bars) == 50_000` and passes; the handoff script runs as written (20,000 bars: validate 0.062 s, 0 defects; aggregate 0.021 s, 1334). Nit: the script prints no build time although the docs quote "build 2.92 s".
- **F9 closed**: `git check-ignore -v -n --no-index`: `snapshot/.hidden.py`, `data/.secrets.py`, `data/.cache` ignored by `:42`; `snapshot/model.py`, `data/__init__.py` tracked by `:40`; `bars.parquet` ignored by `*.parquet`, `data/raw.parquet` by `data/`, `notes.csv` by `:38`; `git ls-files src/sochron/data` unchanged (5 files). A data file saved as `rates_2024.py` would still be tracked; the owner chose to cover dotfiles only.

## AC status
| AC | Status | Why |
|----|--------|-----|
| AC-01–06 | PASS | Full suite green; locked blobs unchanged (acceptance `f3273a15`, architecture `1319cce4`, golden `6f46d72c`). |
| AC-07 | UNKNOWN | Local `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` gave 2875 passed in 10.84s at `9431900` (2026-10-23T23:52:44Z–23:52:55Z); no CI run yet. |

## Checked, nothing found
- Parent vs HEAD unit tests per fixed file: HEAD 18 passed; F1 parent 2 failed (F1, and F5 not yet present); F2 parent 1 failed; F4 parent 2 failed; F5 parent 1 failed.
- `bash scripts/controls/red-flags.sh origin/main`: exit 0; the one group is "Lint disabled" from the word noqa in docs prose. Control files touched: `.gitignore` and the three locked tests (owner label needed).

## Not checked
- CI on Linux (no PR); whether the owner's decisions are as recorded (only the documents' consistency with each other and the code); the 500,000-bar timing (20,000 only, as instructed). The reviewer noted that for F6 r1 proposed a code fix while the owner accepted a limitation.

## Answers (implementer, 2026-10-24, under the owner's standing delegation "เอา recommanded ทุกอัน")
- F10 fixed in `a158abf` with a regression that failed before and passes after; suite 2876 passed.
- F11 fixed in the docs commit that adds this file; the build-time nit is worded in the handoff.

Ready for PR: yes
