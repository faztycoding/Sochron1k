# Review CORE-006 round 1 · base origin/main `419eee3` · head `7dfde0e` · reviewer Claude Code (Opus 5.5), fresh session, Codex role under the owner's role swap

Scope: the CORE-006 implementation (`3fc487e` src + unit tests, `7dfde0e` evidence) against contract
`docs/contracts/CORE-006-strategy-h001.md` v1.1, H001 section 3-4, and the locked tests of `a1c5188` and `3eb1579`.
CORE-007 contract docs and the CORE-005 post-merge note on the branch were read only where they describe CORE-006.
Procedure: `.agents/skills/cross-agent-review/SKILL.md`. Environment: Windows 11, Git Bash, uv 0.13.0, CPython 3.12.15,
2026-10-24 09:15-09:27 +07. All probes are scratch scripts outside the repository (session scratchpad
`...\scratchpad\{oracle,edges,perf,vc_filter,purity,dst_ctx,fixcheck}.py`, plus src copies `mut_s`, `mut_f`, `fixes`,
`canary`); `src/` was not edited. Each finding below states its probe so a third party can rebuild it.

No finding blocks the PR. All five are Low: two edge cases in the code (F1, F2), one super-linear path outside the
validation vocabulary (F3), one gap in the implementer's own regression test (F4) and one evidence claim without a record (F5).

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | `src/sochron/strategy/h001.py:43-45` (with `params.py:66`) | See F1 below: with a 29-digit theta, a V-A long crossing enters and its exact mirror gives `none` | theta with more than 28 significant digits (accepted by `H001Params`) | V-A short threshold is not the mirror of the long one (D5 "กลับด้าน"); no registered two-decimal theta triggers it | `negative_theta = theta.copy_negate()` (exact, context-free), or refuse theta/k with more than 28 significant digits | Probe gives `enter_long` / `enter_short`; full suite 3084 passed on a scratch copy with the fix |
| F2 | Low | question | `src/sochron/strategy/h001.py:98`, `:70`, `:113` | See F2 below: a naive `next_open_utc` raises `NaiveDatetime` only on a flat bar with an entry signal; otherwise it is accepted | Caller passes a naive datetime | A caller bug surfaces only at the first entry (in Demo: at the moment of an entry), with an error outside the contract's TypeError/StrategyError pair | After the exact type check: `if next_open_utc.utcoffset() is None: raise StrategyError(...)` | `StrategyError` for every position; full suite 3084 passed with the fix |
| F3 | Low | question | `src/sochron/strategy/indicators.py:143-146` | See F3 below: zero-count flags stay in the Counter and line 146 walks every key on every row; time grows ≈3.3× per doubling with unbounded distinct flag strings | A flag vocabulary that grows with the series (`validate_m1` does not produce one today) | Quadratic time only; results unchanged | Drop zero counts after `subtract` (`flags = +flags`, or delete keys at 0) | 0.050 / 0.102 / 0.218 s (linear); full suite 3084 passed with the fix |
| F4 | Low | confirmed | `tests/unit/strategy/test_strategy_unit.py:37-54` (code path `indicators.py:110-111`) | See F4 below: mutant `keep_f = (f−1)/(f+1)` passes the full suite (3084 passed) | A later edit of the fast-EMA decay factor | tests-r2 F6 is closed for the slow EMA only; f = 22 is a period where the two readings differ, and only f can take it | Add f = 22 (with s = 78) to the unit test and assert `ema_f` as well as `ema_s` | Mutant M2 fails the unit test; the current code passes |
| F5 | Low | confirmed | `docs/evidence/CORE-006.md:45` | See F5 below: "ใส่ในงานติดตามของ FIX-001" has no record in any file | — | The accepted F5 limitation can be lost; the evidence states an action that is not on record | Add the follow-up line where follow-ups live (PROGRESS.md "Claude ถัดไป" or the FIX-001 follow-up list), or reword to "to add" | `grep` finds the entry |

<!-- Sev: Critical | High | Medium | Low. Kind: confirmed | question. -->

**F1: `-theta` is rounded in the module context, `theta` is not, so V-A long and short are not mirrors.**
- Where: `h001.py:43-45` computes `negative_theta = -theta` inside `localcontext(CONTEXT)`; unary minus rounds to 28
  digits. The long rule compares against the unrounded `theta`. `params.py:66` accepts any number of digits in
  0.25..1.00.
- Evidence (`fixcheck.py`, `edges.py` section 4): `H001Params("A", 16, 64, 20, Decimal("0.25000000000000000000000000006"),
  96, 48, Decimal("2.0"))`; rows with TS 0.25 then 0.2500000000000000000000000001 (a 28-digit TS the module can produce)
  give `enter_long`; the mirrored rows −0.25 then −0.2500000000000000000000000001 give `none`. The exact mirror
  (`theta.copy_negate()`) gives `enter_short`.
- Contract basis: rules line 66 (V-A short `ts[t] < −theta`, "short กลับด้านตาม D5") and D5. D1 ("round after each
  operation") can be read to round `−theta`; the asymmetry stays under either reading, because `theta` itself is never
  rounded.
- Fix check: scratch copy `fixes` with `copy_negate()`: probe gives `enter_long` / `enter_short`; full suite run from the
  repo root against that copy: 3084 passed.

**F2: a naive `next_open_utc` is refused only on the entry path, and not as StrategyError.**
- Evidence (`edges.py` section 7, `fixcheck.py`): `datetime(2026, 3, 10, 13, 45)` (no tzinfo) with a V-B breakout row:
  flat → `sochron.timebase.errors.NaiveDatetime` (a ValueError, not a StrategyError); flat without a signal → `none`;
  long → `hold`; short → `exit`. `decide` checks only `type(next_open_utc) is datetime` (`:98`); the naive check
  happens inside `in_entry_window` (`:70`), which runs only after an entry signal (`:113`).
- Contract basis: none explicit. The acceptance docstring (`tests/acceptance/CORE-006/test_strategy_h001.py:39`) and
  the handoff (`docs/handoff/CORE-006.md:443`) list "a naive next_open_utc" as left untested because the contract is
  silent. The contract's error rule (line 35: out-of-contract values → StrategyError) and the parameter name suggest an
  up-front refusal, hence "question".
- Fix check: with the two-line check in scratch copy `fixes`: StrategyError for flat-with-signal, flat-without-signal and
  long; full suite 3084 passed.

**F3: the flag Counter keeps every key it has ever seen.**
- Evidence (`perf.py`, `fixcheck.py`): when every bar has a new flag string, `indicators` on 2,000 / 4,000 / 8,000 bars
  takes 0.064 / 0.203 / 0.699 s (repo code) against 0.050 / 0.102 / 0.218 s with zero counts dropped. With realistic
  flags (`missing_spread`, `unexpected_gap`, `incomplete`) the code is linear: 170,000 bars in 1.8-4.1 s.
- Why only a question: flags come from `validate_m1`'s fixed codes plus `incomplete`, so no current input triggers it.
  The locked tests leave non-defect flag strings untested (acceptance docstring `:38`).

**F4: the s = 62 unit test (tests-r2 F6) guards the slow EMA only.**
- Evidence: tests-r2 F6 lists the periods where `1 − α` and `(p − 1)/(p + 1)` differ in the 28th digit: 22, 36, 37, 43,
  50, 62, 78. Only f can be 22 (s is 32-96). Mutants run from the repo root with
  `pytest -c <scratch>/<copy>/pytest.ini --rootdir <repo> tests`, whose `pythonpath` points to a scratch copy of `src`:
  - canary (STRATEGY_VERSION "H001-v0"): 1 failed, 3083 passed. This shows the arrangement runs the scratch code.
  - M1 `keep_s = (s − 1)/(s + 1)`: 1 failed (`test_one_minus_alpha_is_computed_from_the_rounded_alpha`), 3083 passed.
  - M2 `keep_f = (f − 1)/(f + 1)`: **3084 passed** (survives every test).
- The current code is right at f = 22: `fixcheck.py` gives 1 − α = 0.9130434782608695652173913044 against
  0.9130434782608695652173913043; the EMA differs in 35 of 39 rows between the readings, and `indicators()` follows 1 − α.
- Fix: one more case in the unit test (for example f = 22, s = 78, asserting `ema_f` row by row). This is the
  implementer's own unit test, not a locked file.

**F5: the evidence says tests-r2 F5 went into the FIX-001 follow-up, but no file records it.**
- Evidence: `docs/evidence/CORE-006.md:45` says "ใส่ในงานติดตามของ FIX-001". A `grep` for `eval`, `exec`, `compile`,
  "string-built", "จาก string" and "tests-r2 F5" over every `*.md` this branch changes (`git diff --name-only
  origin/main...HEAD`, the tests reviews excluded) finds only the evidence line itself and the handoff (`:440`). The two
  PROGRESS.md hits are about `codex exec`. A repo-wide grep finds only unrelated CORE-003 "tests-r2 F5" items.
  PROGRESS.md's follow-up list (`:288`) names only the tests-r1 F5 items (`time.localtime`, `os.urandom`, ...).
  PROGRESS.md `:5` still shows CORE-006 as "implementation draft ready in scratch", so the session-end checkpoint has not
  been written yet; the follow-up can go in with it.
- The limitation itself is sound: `src/sochron/strategy` has no `exec`, `eval`, `compile`, `__import__` or `getattr` on
  modules (grep). The two `getattr` calls in `indicators.py:58-59` are the duck typing of v1.1 item 7.

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Locked AC-01 tests green (206 CORE-006 + unit tests passed). `params.py:53-71` matches every range, `s >= 3f`, `M <= N`, exact types (bool and subclasses refused) and non-finite → StrategyError. `H001_DEFAULTS` = f16 s64 n20 θ0.50 N96 M48 k2.0 for A, B, C. |
| AC-02 | PASS | Golden green. An independent brute-force oracle written from the contract text matched every field of 58,035 rows over 100 parameter sets (range edges, s = 3f, M = N, s = 62, random sets), with duplicate spreads, None spreads, defect flags and `incomplete`. F4 is a gap in regression protection, not a wrong value. |
| AC-03 | PASS | Locked AC-03 tests green. `stop_distance = k × atr` in CONTEXT (`h001.py:116-117`); the oracle agrees on every entry; `version` = "H001-v1" on all 174,105 oracle decisions. |
| AC-04 | PASS | The oracle matched every long/short decision (exit/hold, opposite signal → exit, never `enter_*` while not flat, exits before warm and outside the window, None indicators → hold). |
| AC-05 | PASS | The oracle matched every flat decision, including multi-reason skips in contract order. Crafted rows: spread = 3 × median passes (720/240, 721/240.5, 0/0), one more skips; all five reasons in order; 8 New York window edges on 2026-03-08 and 2026-11-01 correct. F1 is outside the registered parameter grid. |
| AC-06 | PASS | Look-ahead property: prefix and post-t tampering leave rows and decisions at t unchanged (3 variants × 11 t). A guarded sequence shows `decide` reads only offsets {−1, 0}. Architecture 15 passed. Runtime audit hook: no I/O events during the calls; the random state is unchanged; importing `sochron.strategy` loads only core, timebase and stdlib. Static-check limitation (tests-r2 F5) accepted; see F5. |
| AC-07 | UNKNOWN | Local: `uv run --offline pytest tests -q -p no:cacheprovider` → 3084 passed, 0 skipped. CI `python-tests` has not run (no PR yet); the contract requires it green. |

## Checked, nothing found (and how)
- **Scope and integrity.** `git show --stat`: `3fc487e` touches only `src/sochron/strategy/**` and
  `tests/unit/strategy/**`; `7dfde0e` touches only `docs/evidence/CORE-006.md`. `git diff --stat origin/main...HEAD` over
  pyproject.toml, uv.lock, src/sochron/{core,timebase,data,costs,risk}, docs/hypotheses, .github, .claude, scripts,
  AGENTS.md, CLAUDE.md and research: empty. The locked tests are unchanged since `3eb1579` (`git diff --quiet`). SHA256 and
  blob at HEAD match the evidence: acceptance `9b985946…`/`ef61bef6…`, golden `831ccd85…`/`9e9dadf5…`, architecture
  `e0f1cc4f…`/`504c88a6…`. Every commit carries `Refs: CORE-006`.
- **Contract rules against code.** H001 §3 table and the contract rules (lines 64-70): `h001.py:36-51` (entries; V-C
  adds the TS sign), `:54-65` (exits; opposite entry → exit), `:109-110` (any non-flat → exit/hold, before invalidation and
  window), `:68-86` (reasons, order `outside_window, spread_filter, spread_unknown, atr_zero, data_flag, warmup`; equal
  3 × median passes). D1: CONTEXT prec 28 HALF_EVEN used through `localcontext` for every operation. D2:
  `indicators.py:110-135` (EMA seed `close[0]`, ATR mean of TR[0..n−1] and then Wilder), `:102` (warm). D3: `:101` (L per
  variant), `:143-146`, `incomplete` ignored. D4/v1.1 item 6: `ts` None when ATR is None or 0 (`:136`); V-A/V-C have no
  signal; V-B → skip `atr_zero`. D5: mirrored rules (see F1 for the digit edge). v1.1 items 1-3, 5, 7, 8 match; item 4
  (STOP days cut upstream) and item 9 (WARN flags skip ≈ one day) need no code here.
- **Sliding windows against brute force.** Deque eviction with tied highs/lows (price steps of 0.1-1 with many ties),
  sorted-spread median with duplicates (`dup` mode) and None (rates up to 1%), flag Counter removal at `t − span`,
  span per variant, every t from 0 (so t < N, t < M, t < 96, t < span): `oracle.py` seeds 20261024, 1, 2, 3: 58,035
  rows and 174,105 decisions, 0 mismatches.
- **Decimal context.** A hostile caller context (prec 3, ROUND_DOWN, Emax 5, Emin −5, traps Inexact, Rounded, Clamped,
  Subnormal, Underflow, Overflow, DivisionByZero, InvalidOperation) gives identical rows and decisions, and leaves the
  caller's prec, rounding, Emax, Emin, traps and flags unchanged. `3 × median` and `Decimal(spread)` are exact for the
  int spreads MT5 reports. Note, not a CORE-006 finding: `Context(prec=28, rounding=ROUND_HALF_EVEN)` inherits traps
  and Emax/Emin from `decimal.DefaultContext` at import (probe: a changed DefaultContext shows Inexact trap True, Emax 3).
  `sochron.costs.model.CONTEXT` does exactly the same, so any hardening is project-wide.
- **V-A with previous ts None, exits with None indicators, the V-C filter.** Covered by the oracle on early rows. On
  separate data the V-C TS filter binds on 10 breakout bars, and V-B and V-C decide differently on all 10.
- **Very long series and performance.** 170,000 synthetic M15 bars: `indicators` 1.82 / 3.62 / 4.05 s (V-A/B/C); the
  full `decide` loop with position tracking takes 1.11 / 0.72 / 0.80 s. Scaling for V-C on 42,500 / 85,000 / 170,000 bars:
  `indicators` 0.82 / 2.30 / 4.04 s and `decide` 0.18 / 0.36 / 0.70 s (linear). EMA keeps at most 28 digits with adjusted
  exponent ≥ 2, and ATR keeps adjusted exponent ≥ 0 (ATR ≥ 1): no drift. The evidence's 1.20 s / 0.34 s came from other data and a
  flat-only loop; both are within "a few seconds".
- **Error types.** 26 probes: bars None, str, generator, set, items without `.bar`, `.bar` a Bar subclass, `.flags` a
  set, a non-str flag, params None or a subclass → TypeError; an M5 bar → StrategyError. For `decide`: rows None or a
  generator, wrong rows[t] or rows[t−1], t bool or float, position None, `next_open_utc` a date or str, params None or a
  subclass → TypeError; t −1, t = len, empty rows, position "Flat" → StrategyError.
- **Purity.** Imports are the stdlib list (bisect, collections, collections.abc, dataclasses, datetime, decimal, types,
  typing) plus `sochron.core` and `sochron.timebase`. No clock, random, I/O, logging or float in the source (grep). The
  `threading` module loaded at import comes from `timebase`/zoneinfo, not from strategy. Inputs are not mutated, and
  repeated calls give equal results.
- **Pathological inputs.** A negative ATR (needed for a negative stop distance) or a long and a short entry on the same
  bar both need a bar with high < low. `validate_m1` flags that bar `ohlc_inconsistent` (STOP), and SLICE-R1 removes the
  day upstream (v1.1 item 4). Not raised.
- **Red flags.** `bash scripts/controls/red-flags.sh origin/main` → 2 groups: "Lint disabled" and "Destructive or
  bypass". Every hit is prose in `docs/` (the word "noqa", the tar flag `--force-local`); none is in `src/` or
  `tests/unit/`. The "Control files touched" list is the three locked test files of the two D-006 patches.

## Not checked (and why)
- CI `python-tests` on the Linux runner: no PR or push yet (AC-07 UNKNOWN).
- Codex `/review`: not available; this session acts as the reviewer under the role swap.
- Real market data: forbidden before ENV-1 and SLICE-R1.
- Concurrency: `localcontext` is thread-local by design; no multi-threaded run.
- Rows computed with different `H001Params` than the ones passed to `decide`, and bars out of time order: the contract
  is silent, and the module counts bars as given.
- Full mutation testing of the locked tests (the tests-r1 and tests-r2 reviews did that). Only M1, M2 and the canary
  were run here.
- CORE-007 contract and reviews, and the CORE-005 note: outside this review.

Ready for PR: yes (no Critical/High/Medium; the five Low findings do not block. F1, F2 and F4 are fixes of one to five
lines that can go in before the PR)
Findings open: 5
