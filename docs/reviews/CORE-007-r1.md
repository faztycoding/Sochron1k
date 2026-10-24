# Review CORE-007 round 1 · base main (origin/main 6fbed53, merge-base b7256cd) · head a74b9ae · reviewer Claude Code (Opus 5.5), fresh session, Codex reviewer role under the owner's role swap (D7)

Scope: `git diff origin/main...HEAD` for CORE-007, implementation `29eacf3` (`src/sochron/backtest/{__init__,model,trade,engine}.py`,
`tests/unit/backtest/test_backtest_unit.py`) and evidence `a74b9ae`, against contract v1.5. The CORE-006 post-merge note
`a7a0a0f` is outside this review. Every number below was run in this session (2026-10-24, +07, Windows 11, Git Bash,
CPython 3.12.15 through `uv run --offline`). The independent oracle and every probe live in this session's scratchpad.
The oracle is written from the contract text and never imports `sochron.backtest`. It calls `strategy.indicators`,
`strategy.decide`, `costs.round_trip_cost`, `costs.r_multiple` and `costs.check_volume`, because the contract requires
`run` to use them. It reads zones through `zoneinfo` directly.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 | Low | confirmed | src/sochron/backtest/engine.py:56 (M1), :48 (M15) | `run` with `m1[0] = replace(valid M1, time_raw=0)` (time_utc 2026-03-10 14:00 UTC; `core.Bar` accepts any int) raises `sochron.timebase.errors.RawTimeOutOfRange: raw MT5 time 0 is outside [946684800, 4102444800)`. The same with `m15[0].bar.time_raw = 0`. Control: `time_raw + 3600` (inside the range) gives `BacktestError: m1[0] time_utc does not match its raw time under the rule`. Contract "Input และการตรวจ": an M1/M15 with `time_utc ≠ to_utc(time_raw, rule)` → `BacktestError`. "Inputs / outputs / errors" names only TypeError, BacktestError, costs errors and sizer exceptions. | A Bar whose `time_raw` is outside [2000-01-01, 2100-01-01) UTC seconds | A caller that catches `BacktestError` to refuse a bad window gets a `TimebaseError` instead. It is still a `ValueError` with a clear message. No wrong number is produced. | In `_check_m1`/`_check_m15`, refuse `not RAW_MIN <= time_raw < RAW_MAX_EXCLUSIVE` (both exported by `sochron.timebase`) with `BacktestError` before `to_utc`. Or catch `TimebaseError` there and raise `BacktestError` from it. Or write into the contract that timebase errors pass unwrapped. | Unit test: both cases above → `BacktestError` |
| F2 | Low | confirmed | src/sochron/backtest/trade.py:49-50 (`stop_price`), same arithmetic at :58, :68 | `simulate_trade(m1, 0, "short", Decimal("1E+1000000"), Decimal("0.10"), H001_COSTS, Rollover("America/New_York", time(17, 0)), risk_money=Decimal("25"), exit_index=4)` raises `decimal.Overflow` (`isinstance(e, ValueError)` is False). `"long"` gives the same. `1E+999990` returns a Trade. Contract: `stop_distance` must only be > 0 and finite; errors are TypeError / BacktestError / costs / sizer only. | A finite Decimal argument whose fill arithmetic passes `costs.CONTEXT`'s Emax (999999). Seen for `stop_distance`. `run` with start equity 9.99E+999999 still works (18 trades). | Unreachable from `run` on real prices, because `decide`'s stop distance is k×ATR. A direct caller (CORE-008) passing an absurd value gets an `ArithmeticError` that `except ValueError` misses. No wrong number is produced. | Refuse oversized Decimal arguments with `BacktestError` (a size bound like `sochron.costs`' `bounded_decimal`, tight enough for the fill arithmetic). Or catch `decimal.Overflow` around the fill arithmetic and raise `BacktestError`. Or write the bound into the contract. | Unit test: `stop_distance` 1E+1000000 on both sides → `BacktestError` |
| F3 | Low | confirmed (test gap) | src/sochron/backtest/engine.py:163-164 (unpinned); a test fits in tests/unit/backtest/ | One-line mutant `range(self.first[t], self.end[t])` → `range(self.first[t], self.end[t] - 1)` (step 1 ignores the last M1 of bar t), in a scratch copy of src. The locked CORE-007 acceptance tests plus the unit tests give **110 passed**, so no test kills it. My oracle does: 2 of 300 random runs differ at 5% `incomplete` flags and 4 of 300 at 15%. Two effects show: `data_flags` gains the next bar's flag, and a stopped position stays held through bar t's decision so a later entry is lost ("trade count 29 vs oracle 30"). The real implementation: 0 of 300 on the same seeds. | Any later edit of step 1's M1 range | A regression of contract step 1 ("ตรวจ SL ทุก M1 ของแท่ง t") would pass CI and change R1 results silently: wider `data_flags`, and decisions at bar t taken with a position that should be flat. Today's code is correct. | One unit test (implementer-owned path): the stop is hit only in the last M1 (minute 14) of bar t, and bar t+1 carries a flag that no earlier bar of the trade has. Expect `data_flags` without that flag. Optionally add a signal at bar t, so a flat decision enters at t+1. A tests r3 golden scenario would also do. | The mutant above fails that test |
| F4 | Low | confirmed (documentation) | docs/evidence/CORE-007.md:12; tests/unit/backtest/test_backtest_unit.py:60-62 (data at :30, :32, :37) | The evidence's AC-05 row cites "unit test บนข้อมูลสุ่ม 9 ชุด", but all 9 parametrizations use the same `_m1(20_000, seed=11)`: one dataset, 3 variants × 3 side sets. The test comment says the data covers "gaps from the random walk". In fact `_m1` opens every M1 at the previous close (:32, :37) on consecutive minutes (:30): no price gap and no missing minute. | — | The evidence overstates what the unit test proves. The test never reaches a gap fill, an ambiguous exit on a long, an incomplete M15 bar or a fill after a missing minute 0. Those are covered by the locked golden cases and by this review's oracle, not by the unit test. | Reword: "one random dataset, 9 configurations", and drop "gaps" from the comment. Or give `_m1` price jumps and dropped minutes and vary the seed. | The diff of the two lines (or the unit test still green with gaps) |

## AC status
| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01 | PASS | Locked AC-01 tests pass (3206 run). My oracle agrees with `simulate_trade` on every Trade field of 9,000 random trades (both sides, 4 models incl. stress 2 and 1.5, commission and short swap ≠ 0), with 30% of calls under a hostile caller context. |
| AC-02 | PASS | Locked fill cases and run scenarios pass. Oracle vs `run`: 760 random runs (gaps in minutes and slots, missing minute 0, missing spreads, spread spikes and zeros, price jumps at slot boundaries, flags), 0 mismatches. That covers 2,577 trades (incl. 7 ambiguous exits, 98 end-of-data) and 33,465 skips. The same holds in the cut sweep below. |
| AC-03 | PASS | Locked AC-03 tests pass. My error sweep (100 wrong arguments) matches the contract in 95 cases. The other 5: F2 (2 cases, Low); F1 (1 case, Low, confirmed for M1 and M15 by a separate reproduction); `risk_money` 1E+2000000 → `costs.BadR`, a costs error the contract lets pass; and one harness artefact (`aggregate` refused pre-2000 M1 before `run` was called). Sizer calls (equity after each net) are compared on every run, as are skips, `equity_exhausted` (1,619 skips over the fuzz), no overlap and versions. |
| AC-04 | PASS | Locked AC-04 tests pass. The nights sweep matches the v1.5 `combine` construction in all 30,258 cases: every 2026-27 offset transition of all 201 zones that have one, rollover times in gaps, folds, at midnight and at 17:00, entries and exits around each transition. Oracle stress models: gross unchanged, every charge scaled (mutant `gross_stressed` killed). |
| AC-05 | PASS | Locked AC-05 tests pass. Cut sweep: 3 random datasets of 20,000 M1, `run` re-run at every cut bar u ≥ 100 (≈3,780 cuts). Each cut equals the oracle; trades whose exit bar ≤ u, the skips before u's open and equity points 0..k equal the full run. Every run trade (2,577 in the fuzz, plus every cut run) re-simulated through `simulate_trade` with the contract mapping is equal. |
| AC-06 | PASS | `uv run --offline pytest tests/architecture` → 17 passed, incl. `test_ac06_core007_backtest_imports_only_core_timebase_strategy_costs_and_listed_stdlib` and `test_ac06_r2_core007_backtest_never_names_zoneinfo`. A grep confirms the imports are core, costs, strategy, timebase plus collections.abc, dataclasses, datetime, decimal and typing, with no clock, random, environment, file, `astimezone`, `ZoneInfo` or float names. |
| AC-07 | PASS locally · CI UNKNOWN | `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` → 3206 passed, 0 skipped, 22.27 s at a74b9ae. There is no PR run yet. |
| Speed row | PASS | `run` on 500,000 synthetic M1: V-A 3.52 s, V-B 3.32 s, V-C 3.59 s (contract limit 60 s). Time per M1 is flat from 125k to 500k (5.7–7.3 µs), so scaling is linear. |

## Contract rules checked against the code
- **API block:** names, field order, frozen dataclasses, `BACKTEST_VERSION`, `Side`, `Sizer`; keyword-only `risk_money`, `actual_risk`, `exit_index`, `data_flags`, `sides`. Matches model.py, trade.py:180-193 and engine.py:96-107.
- **Input checks:**
  - M15 duck typing (engine.py:29-38).
  - Empty inputs, equity ≤ 0 or non-finite, M1/M15 timeframe and strict order, M1↔M15 membership (engine.py:61-79), time_utc against the rule for M1 and M15 (except F1), STOP-level M1 (trade.py:25-38).
  - `Rollover` and `SizedLots` checks exactly as listed; `check_volume` after the sizer.
  - `simulate_trade` index bounds and lazy per-M1 checks on every M1 read, including the exit M1 against its predecessor.
  - Domain checks before any fill (except F2); time only through `to_zone`/`to_utc`/`bar_open`.
- **Fill and stop table:**
  - Long stop `open + s·p − sd`; short stop `open + sd`.
  - Gap checked before touch on every M1 from the entry M1 on: long `open ≤ stop`; short `open + s·p ≥ stop`.
  - Touch: long `low ≤ stop` → stop; short `high + s·p ≥ stop` → `stop − s·p`.
  - Exit open beyond the stop → stop + ambiguous at the open. End of data at the last close.
  - `s` is the event M1's spread or the fallback; spread points recorded after the fallback.
  - Gross is unstressed. Costs come once from `round_trip_cost`. `r` = net / `risk_money` (D8).
  - Oracle agreement plus 18 killed mutants of these lines.
- **nights (D4):**
  - T is built by `datetime.combine(zone date, at, tzinfo=to_zone(entry).tzinfo)` and compared in UTC.
  - Count Mon–Fri in the zone with entry < T ≤ exit; triple on the zone weekday.
  - The day range from the entry's zone date to the exit's zone date never misses a T: an oracle scanning 3 extra days each side found 0 differences.
- **Event order 1–6:**
  - Step 1 scans only the M1 of bar t (engine.py:163-164).
  - decide gets the position after step 1 and `next_open_utc` of the next existing bar.
  - An exit fills at `first[t+1]`. An entry is sized with the equity after every close, skips when equity ≤ 0 before the sizer, and records the reason when lots are None.
  - A decide skip is recorded for any `sides`. The last bar closes at the end of data.
  - Equity points: the first M1 plus one per close. `data_flags` = flags of bars decision t … exit bar.
  - All compared field by field with the oracle.
- **Invariants:** real `decide`/`costs`; one position at a time; run trade = `simulate_trade`; no look-ahead (cut sweep); pure; import list.
- **D1–D13:**
  - D1 is the caller's adapter (outside this module).
  - D2, D3, D6 and D8 per the table.
  - D4 as above. D5: no halt. D9: duck typing. D10: realized curve only.
  - D11: `sides` subset (long-only and short-only fuzzed). D12: `equity_exhausted`. D13: STOP-level M1 refused.
- **v1.5:**
  - Item 1: stdlib list.
  - Item 2: no `ZoneInfo`.
  - Item 3: see below.
  - Item 4: non-str in `sides` → TypeError.
  - Item 5: tuples.
  - Item 6: M15 time_utc check.
  - Item 7: untested questions, which the evidence states.

## v1.5 item 3 and the implementer's recorded choices
- **v1.5 item 3** (`simulate_trade` checks only the M1 the fill reads): **sound and honestly recorded.**
  - The stated reason is accurate. Without `exit_index`, the reviewer's whole-range reading costs O(len(m1) − entry) per call. I measured 0.74 s for one call across 500,000 M1, which a 1,000-run random baseline cannot afford.
  - With `exit_index` given, that reason does not apply: the whole range is bounded by the holding. Still, the narrower rule is harmless there too. An M1 after the closing M1 cannot change the Trade, and `run` validates every M1 up front.
  - The departure from the tests-r1 recommendation is stated openly in the contract ("Claude ไม่เลือกทางนั้น"), in the evidence's limits and in the handoff, and the owner keeps the veto.
- **Module split:** no concern.
- **`run` reusing the fill code with `checked=True`:** sound. Every check it skips is already guaranteed upstream:
  - types, and every M1 through `_check_m1`;
  - lots through `check_volume` in `_enter`;
  - risk values through `SizedLots`;
  - `stop_distance` > 0, because `decide` enters only with ATR ≠ 0 and TR ≥ 0;
  - `exit_index` > `entry_index`.

  Step 1 and the fill code call the same `stop_fill` with the same stop price, so they cannot disagree. The oracle asserts that the stop found from the entry M1 lies in bar t; the assertion never fired.
- **Rollover instant from `to_zone`'s tzinfo:** matches v1.5 and is verified across all zones (above).
- **Zone check catching KeyError/ValueError/OSError:** sound.
  - 44 hostile strings, each in its own process under a timeout: "", "/", "..", absolute paths, "NUL", "CON", "AUX", "COM1", NUL bytes, a lone surrogate, "__init__.py", "America/Argentina", data files such as "zone.tab", and others. Each became `BacktestError` or resolved to a real zone. Nothing else escaped and nothing hung.
  - All 598 `zoneinfo` keys are accepted.
  - Windows aliases are accepted (`America\New_York`, "UTC " with a trailing space). They load the same TZif data, so this is harmless.
- **V-B = V-C observation:** reproduced on my own 500,000-M1 random walk. V-C's TS filter blocks 1 of 2,064 V-B breakout bars; trades are equal (232), skips 713 vs 714. The observation is honest and, as the evidence says, a matter for R1, not a backtest defect.

## Checked, nothing found (and how)
- **Look-ahead:**
  - Step 1 reads only bar t's M1; decide reads `rows[0..t]` and the next bar's time.
  - The cut sweep re-ran at every bar u: the trades, skips and equity before u never change when later data is removed.
  - Mutants `next_open_is_bar_t`, `entry_at_second_m1` and `exit_at_second_m1` are killed.
  - `next_open_utc` reveals only when the next bar exists. That is contract step 2, it is the fill slot, and it carries no price data.
- **Entry when the next M15 bar's minute 0 is missing:** the fill is at the first M1 present. Up to 30% of slots lose minute 0 in the fuzz and in all three cut-sweep datasets (9,999 such fills counted across the cut runs), all equal to the oracle. The NY window gives the same answer for the slot start and the fill minute, because the window bounds sit on 15-minute boundaries.
- **Bar boundaries:** exits and entries decided at the second-to-last bar (45 entries on the last bar, 9 signal exits on the last bar) and end-of-data closes (987) in the cut sweeps.
- **`data_flags` span:** random flags, with mutants excluding either end killed by the locked tests and by the oracle.
- **Rollover at midnight and at non-existent times:**
  - The v1.5 construction uses fold 0 (or `at.fold`).
  - It differs from a literal minute-by-minute wall-clock reading only at weekday gap times in Africa/Cairo and Asia/Jerusalem (36 cases). The contract's explicit construction settles that.
  - New York 17:00 is never affected: US transitions fall on Sunday 02:00.
- **Equity, sizer and context:**
  - The sizer is called with the equity after every net, exactly as in the oracle, on every run.
  - Runs with negative equity: 96 across the fuzz.
  - Decimal context: about 30% of fuzz calls ran under a hostile caller context (prec 3, ROUND_UP, Emin −5/Emax 5, every trap on). Results are unchanged, and the caller's context (flags included) is identical after each call.
  - Mutants that move the gross or equity arithmetic to the caller's context are killed.
- **Performance:**
  - `simulate_trade` costs about 150 µs per call plus about 2 µs per M1 read: 15-M1 holds 158 µs, 240-M1 holds 484 µs, 2,000-M1 holds 4.9 ms. That is linear.
  - About 36% of the fixed cost is `costs.validate_model`, which runs twice per call (`check_volume` and `round_trip_cost`). This is a CORE-008 planning number, not a defect.
  - Stop-only calls on a random walk average 7 ms because first-passage times are heavy-tailed, not because of the code.
- **Purity:** no clock, random, environment, file or network use. `costs.CONTEXT` is only copied through `localcontext`. Time goes through timebase only.
- **Scope:** `29eacf3` touches only `src/sochron/backtest/**` and `tests/unit/backtest/**`; no `pyproject.toml`/`uv.lock` change; locked tests unchanged since `e74e298`.
- **Red flags:** `bash scripts/controls/red-flags.sh origin/main` → pattern groups with hits 0. Control files touched: the three locked test files, which came in through the D-006 patches in `e74e298`.
- **Mutation:** 35 one-line mutants plus a canary, each in a fresh scratch copy of src. 33 are killed by the locked tests. The two survivors:
  - `step1_skip_last_m1`: F3.
  - Decide skips dropped in a short-only run: my oracle kills it (13 of 40 runs). Short-only is untested on purpose (v1.5 item 7).
- **Re-reading the input (noted, not a finding):**
  - `simulate` reads `m1[entry_index]` twice and the last M1 twice, and `run` iterates `m1`/`m15` several times.
  - A custom `Sequence` that returns different bars on repeated access could pass unchecked bars.
  - The contract asks nothing about such inputs, and R1 passes tuples.

## Not checked (and why)
- CI and the PR run: no push or PR yet (owner and implementer steps).
- Linux, macOS and Python other than 3.12: only this machine.
- Real MT5 data: forbidden before ENV-1 and SLICE-R1.
- M15 OHLC or spread against its M1: excluded by the contract (open question 2).
- Hostile `Sequence` implementations, beyond the note above.
- Memory use on about 2.5 M M1.
- A full CORE-008-scale baseline (1,000 runs × 63 variants): only per-call costs were measured.
- `run` with a starting equity of 1E+1000000 or more (F2's twin): not run; 9.99E+999999 works.
- Rollover `at` with fold=1 on a weekday overlap in a zone other than New York: fuzzed only through the zone list (`America/New_York` 01:30 fold=1, which falls on a Sunday).

## Checks run (command → result → commit → time +07, 2026-10-24)
- `git diff --stat origin/main...HEAD`; `git show --stat` of each branch commit → scope as above → a74b9ae → 12:2x
- `timeout -k 10 900 uv run --offline pytest tests -q -p no:cacheprovider` → **3206 passed in 22.27s** (0 skipped) → a74b9ae → 12:27:25–12:27:49
- `bash scripts/controls/red-flags.sh origin/main` → Pattern groups with hits: 0; control files touched: the 3 locked test files → a74b9ae → 12:28:47
- `timeout -k 10 600 uv run --offline pytest tests/architecture -q -p no:cacheprovider` → 17 passed in 0.92s → a74b9ae → 12:36:41
- Oracle vs `run` (scratch `fuzz_run.py`):
  - 60 + 400 random runs → 0 mismatches → 12:3x
  - 300 runs with 15% `incomplete` flags → 0 → 12:5x
- Oracle vs `simulate_trade` (scratch `fuzz_sim.py`): 9,000 trades → 0 mismatches → 12:3x
- nights sweep (scratch `nights_dst.py`): 30,258 cases → 0 differences → 12:3x
- Error sweep (scratch `errors.py`): 100 cases → 95 as the contract, rest = F1, F2, a costs pass-through and one harness artefact → 12:4x
- Hostile zone strings (scratch `zones.py`): 44 → no escape, no hang → 12:4x
- Mutants (scratch `mutants.py`, `uv run --offline pytest -c <scratch>/mut/<name>/pytest.ini --rootdir . tests/unit/backtest tests/acceptance/CORE-007 …` from the repo root, plus the oracle fuzz) → 33/35 killed by the locked tests; survivors F3 and short-only skip → 12:3x–12:4x
- Cut sweep (scratch `cut_sweep.py`): 3 seeds, every bar → 0 failures → 12:4x–12:5x
- Performance (scratch `perf.py`, `profile_sim.py`) → as above → 12:51–12:56
- Reproductions for F1 and F2 (scratch `repro.py`, `repro_equity.py`) → as in the findings → 12:56–12:58

Ready for PR: yes (every finding is Low; none changes a backtest number on valid input)

Findings open: 4
