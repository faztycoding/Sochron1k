# CORE-002 test-author handoff

Prepared by Codex on 2026-10-21, Asia/Bangkok (+07:00), for contract v1.2.
Base HEAD: `53f1218ea6653b81aa2b016109d58657681558e8`.
Branch: `feat/CORE-002-costs`. The starting working tree and index were clean.

The deliverable is a regular, non-symlink proposal patch and this handoff.
The final repository test files are unchanged; nothing is staged or committed.
`docs/proposals/` is gitignored by the existing repository rules, so the patch
does not appear in ordinary `git status`. No ignore rule was changed.

The task's explicit instructions authorize these two output files, English
prose, uppercase CORE-002 directories, no PROGRESS edit and no commit. They
override the skill's default direct-test-write/commit/output-language steps.
No costs implementation or implementer's handoff was read or written. Existing
tracked source bytes were copied only to run the existing regression tests.
Read-only helpers checked contract arithmetic and the draft tests; they do not
replace the required fresh-session post-apply review.

## Patch identity and exact expected applied files

Patch: `docs/proposals/CORE-002-tests.patch`

SHA256: `15241d092c28182e7c52cacd28810f0b41ec42c437077d199541d1e1fc37daeb`

Patch size: 31,878 bytes. Exactly three paths: two additions and one modification.
`git apply --numstat` reports 390/0, 213/0 and 37/0 added/deleted lines,
respectively. No deletion, rename, symlink, dependency or configuration change.

| Applied path | SHA256 of applied bytes | Git blob |
|---|---|---|
| `tests/acceptance/CORE-002/test_costs_acceptance.py` | `45120963f76a15386ccef7447f40a5cd9caec0aee72abbedba0b9ef2fe926925` | `8f55412347898e9835216cfb585ce490d5043a28` |
| `tests/golden/CORE-002/costs_cases.py` | `8a2ac03dc66244b4a8ea88bea5899a9d7a8a7a96cee6319cb7cde0cf935bdc9f` | `ac381085b5bf8561b4eba64f43f4175724575453` |
| `tests/architecture/test_imports.py` | `45e09f850f48e611acc317f2a7e2b5f6d79f856e64dfcc10e77ac5615acb158d` | `ff72f6b8b0a7c723356ffef6cde715005f8ac310` |

These are hashes of files actually produced by Git applying the patch to
temporary copies, not hashes inferred solely from proposed strings. The
temporary tree contained the exact HEAD `.gitattributes`. Final application
ran with the temporary tree as the process working directory and explicit
`--git-dir=<repository>/.git --work-tree=<temporary-tree>`; the real Git
directory was used read-only, with no index/object writes.

All three applied files are UTF-8 without BOM, contain zero CR bytes, and end
with exactly one newline. Repository attributes report `text: set` and
`eol: lf` for all three paths. `git hash-object --path=<repo-relative-path>`
and `git hash-object --no-filters` agree for each applied file.

The entire original architecture file is a byte-identical prefix of the new
file. Its original Git blob, still present in the repository after delivery,
is `6cf0b3974b5c3ddae57f21bea40808439afd8c11`.

## Standalone dry run

Command, issued alone:

```text
git apply --check docs/proposals/CORE-002-tests.patch
```

**PASS**, exit 0, empty stdout/stderr, at **2026-10-21 21:13:01 +07:00**,
HEAD `53f1218ea6653b81aa2b016109d58657681558e8`.
This is the final check after restoring the repository and completing the
temporary application. An earlier final-content check also passed at 21:09:12.

## Tests and AC mapping

Acceptance file: `tests/acceptance/CORE-002/test_costs_acceptance.py`.
There is exactly one test function for each of AC-01 through AC-06. The golden
module has the distinct basename `costs_cases.py` and is loaded by file path,
following CORE-001. Application imports are deferred by the tiny `_api` helper;
every requested symbol is from the contract's `sochron.costs` API.

| AC | Test | What it proves | Current status and evidence |
|---|---|---|---|
| AC-01 | `test_ac01_spread_fallback_points_and_decimal_context` | Spread/fallback/stress, point value, signed points, min/max lots, true zero spread, fixture scaling and per-operation half-even rounding. Caller precision 4, ROUND_UP and Inexact/Rounded traps cannot change results or caller state. | FAIL, expected red: `AC-01: sochron.costs not implemented (No module named 'sochron.costs')` |
| AC-02 | `test_ac02_slippage_commission_sides_and_stress` | Base/stressed slippage; zero commission; fully specified 3.5 USD synthetic commission; sides 0/1/2/3 and default two sides; no double stress. | FAIL, same missing-module error tagged AC-02. |
| AC-03 | `test_ac03_swap_debits_credits_and_triple_counts` | One/seven-night charges, triple multiplier, zero short swap, positive swap as a credit, stress, no nights, all-triple boundary, volume endpoints and no negative zero. | FAIL, same missing-module error tagged AC-03. |
| AC-04 | `test_ac04_round_trip_selection_breakdown_order_and_r` | Every breakdown field; spread chosen by side; selected None versus unused None; true zero; sides-zero retains spread/swap; stress; R conversion including 1/3; ordered precision-28 total. | FAIL, same missing-module error tagged AC-04. |
| AC-05 | `test_ac05_reject_invalid_types_domains_and_zero_branch_bypasses` | Named error hierarchy; invalid types including floats/bools; nonfinite values; bad points, nights, sides, factors and R; constructor domains/provenance; every charge validates lots before a zero return; both spread arguments validated even when unused. | FAIL, same missing-module error tagged AC-05. |
| AC-06 | `test_ac06_h001_provenance_unknowns_frozen_and_stress_copy` | All H001 values; exact 11 provenance keys, sources, dates, statuses and UNKNOWN notes; exact unknowns tuple; copied MappingProxyType; all three frozen dataclasses; new stress models, unchanged base fields/provenance and nested factor 4. | FAIL, same missing-module error tagged AC-06. |
| AC-07 | `tests/architecture/test_imports.py::test_ac07_costs_import_boundaries_no_clock_io_random_or_float` plus red-flag scan | Every Python file under costs uses the existing stdlib/core/same-package boundary checks, no detected clock/I/O/dynamic import, no random imports, and a full AST walk rejects any float Name or float literal, including annotations/defaults. | FAIL, expected red: costs source directory does not exist. Red-flag command executed successfully with documentary hits explained below. |

The existing `test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io`
and all its helpers/assertions are untouched.

## Golden derivations and provenance

All expected monetary values are literal strings converted with `Decimal`,
then compared by Decimal numeric equality and type. No float conversion, string
comparison of money, runtime oracle from the application, cent quantization,
randomness, skip or expected-failure marker is used. Every arithmetic row has
its derivation beside the literal.

- Point value: `1 * 0.001 * 100 * 1 * 1 = 0.1` USD.
  Spread: `240 * 0.001 * 100 * 0.02 * 1 = 0.48`; factor 2 gives 0.96.
  Lots 0.01 gives 0.24; lots 200 gives 4800; explicit zero remains zero.
- Slippage: `(50 * 0.001 * 100 * 0.02 * factor) * sides`.
  Two sides give 0.20 at factor 1 and 0.40 at factor 2; zero sides gives zero.
- Commission: `rate * lots * sides * factor`. The AC-02 fixture changes only
  rate to 3.5 and that field's provenance. At lots 1.5 and two sides the values
  are 10.5 and 21.0. Sides 0/1/3 are also explicit rows.
- Swap multiplier: `nights - triple_nights + 3 * triple_nights`.
  Seven nights with one triple give 9, not 10 or 21.
  Broker long points -503.8 produce positive expense
  `0 - (-503.8 * 0.001 * 100 * 0.02 * 1) * 1 = 1.00760`;
  nine units give 9.06840. Factor 2 gives 2.01520 and 18.13680.
  H001 short swap is zero. The AC-03 fixture changes only long swap to +100
  and its provenance, giving -0.20000/-0.40000 USD credits.
- Worked long total: `0.48 + 0 + 0.20 + 1.00760 = 1.68760`;
  `1.68760 / 25 = 0.067504`. Sides zero gives 1.48760.
  Short entry 100/exit 240 uses exit spread: `0.48 + 0 + 0.20 + 0 = 0.68`.
  Stressed long total is `0.96 + 0 + 0.40 + 2.01520 = 3.37520`.
- Per-operation rounding: points 1.0000000000000000000000000015 first multiply
  by 0.001 and round at precision 28 to 0.001000000000000000000000000002;
  multiplying by 100, 0.02 and 1 gives 0.002000000000000000000000000004.
  The companion ...0005 tie rounds to the even retained digit, giving
  0.002000000000000000000000000000. Rounding only the final product would
  disagree with both rows.
- Ordered-total fixture changes commission to 1, slippage to 10 points and
  long swap to 100000000000000000000000000000 points, with synthetic provenance
  on all three changed base fields. Long, lots 1, entry spread the same large
  integer, exit 0, one night, no triple, one side, factor 1 yields components
  1e28, 1, 1, -1e28. Precision-28 ordered additions discard each unit before
  cancellation, giving total 0. Exact or cancellation-first addition gives
  2 and is not the contract's oracle.
- `H001_PROVENANCE_ROWS` contains field/value/source/date/status/UNKNOWN-note
  requirements for exactly 11 base fields. All dates are 2026-10-21.
  Point/contract/volume/spread are measured; commission, slippage and triple
  weekday are assumed; swap fields are spec and their notes contain UNKNOWN.
  Sources are matched by SPIKE-001 or H001 identifier because the contract
  does not prescribe exact English source prose.

Independent temporary verification checked **124 literal monetary/factor
values** using rational arithmetic for finite ordinary rows and the specified
Decimal context for rounded rows; no application code was imported.

## Verification record

All rows use unchanged HEAD `53f1218`; times below are 2026-10-21 +07:00.
Scratch root (abbreviated `<scratch>` below):

```text
C:/Users/MSI/AppData/Local/Temp/codex-core002-1df38902d5df4e65a4aefd57f1f78728
```

Python commands ran through `C:/Program Files/Git/bin/bash.exe`, from the real
repository root, using its existing offline environment. CPython 3.12.15,
pytest 9.1.1. No dependency, lockfile, Git configuration or environment setup
was changed.

| Command or procedure | Result | Commit | Time |
|---|---|---|---|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD` | PASS: clean starting tree/index, correct branch. | 53f1218 | 21:00-21:02 |
| Installed Python/pytest versions and stdlib localcontext/replace documentation | PASS: 3.12.15 / 9.1.1, installed API docs checked. | 53f1218 | 21:02:46 |
| `git apply --numstat docs/proposals/CORE-002-tests.patch` | PASS, exit 0: only the three paths above. | 53f1218 | 21:10:55 |
| `uv run --offline --no-sync python -B <scratch>/verify.py` | PASS, exit 0: applied SHA256/blob equality, LF/BOM/EOF checks, syntax for three files, original architecture prefix unchanged, 17 forbidden and 6 allowed AST probes. | 53f1218 | 21:11:48 |
| `uv run --offline --no-sync python -B <scratch>/run-tests.py` | FAIL, exit 1, expected red: 7 failed, 24 passed, zero skipped, no collection errors. | 53f1218 | 21:11:48 |
| `uv run --offline --no-sync python -B <scratch>/check-golden.py` | PASS, exit 0: 124 literal values independently checked. | 53f1218 | 21:12:34 |
| `bash scripts/controls/red-flags.sh main` | PASS execution, exit 0; one inherited documentary pattern group; secret/order/account-mutation groups empty. | 53f1218 | 21:10:11 |
| `git apply --check docs/proposals/CORE-002-tests.patch` (standalone) | PASS, exit 0, empty output. | 53f1218 | 21:13:01 |
| `git diff --exit-code`, `git diff --cached --name-only`, original architecture blob comparison, absent new test paths | PASS: repository tests restored exactly, index unchanged, no implementation created. | 53f1218 | 21:11-21:13 |

The test runner changes directory to `<scratch>/applied` and invokes
`pytest.main(["tests", "-q", "-p", "no:cacheprovider"])`, the verified suite
arguments, using the existing uv environment. Its pyproject/source/existing
tests are exact HEAD copies. This avoids creating another environment or
writing bytecode into the repository.

Final real output, from `<scratch>/red-run.log`:

```text
started=2026-10-21T14:11:48.067876+00:00
ended=2026-10-21T14:11:48.258963+00:00
exit=1
......FFFFFF.F.................                                          [100%]
7 failed, 24 passed in 0.14s
```

AC-01 through AC-06 each contain the real `No module named 'sochron.costs'`
ImportError converted into a hard, AC-tagged pytest failure. AC-07 fails on
the missing `<scratch>/applied/src/sochron/costs` directory.
Log SHA256:
`913674dfda01a92e5e5681c46a2891d941008e83d2ca451c51ec15b7a767a923`.
The full trace and all failed test names remain in that local log.

Red-flag hits: the "Type checks disabled" group matches two inherited
documentation lines in `docs/reviews/CORE-001-agents-r1.md` and
`docs/tooling/compatibility.md` quoting an earlier suppression. No new
suppression was introduced. The comparison also lists inherited AGENTS.md and
CLAUDE.md changes, outside this task. The scan does not scan ignored proposal
files or untracked files; it is not a claim that the patch was scanned as an
applied/staged diff. Rerun after the authorized application/staging.

## Temporary verification mistakes and recovery

At 21:10, applying outside a Git repository used global autocrlf behavior and
produced CRLF temporary copies despite the copied attributes file. Byte-hash
verification correctly failed. Those results were discarded.

At approximately 21:10:47, a `git --work-tree=<scratch>/applied apply ...`
command still executed from the real repository applied to the real test
paths. This violated the intended temporary-only application. It was reversed
immediately with standalone `git apply -R docs/proposals/CORE-002-tests.patch`.
The final checks prove that both new repository test files are absent, the
architecture file's bytes/blob match HEAD, and HEAD/index are unchanged.
No other existing file was changed. A contemporaneous temporary run that
collected only the original 24 tests is excluded from acceptance evidence.

The successful final temporary application explicitly set the process working
directory to `<scratch>/applied`, along with the real read-only Git directory
and the temporary work tree. `rev-parse --show-toplevel` confirmed that
temporary root before applying. No repository setting or security boundary was
changed to repair these verification mistakes.

## Deliberately excluded and remaining work

- No implementation or mock implementation was authored to manufacture green
  tests. Green behavior remains UNKNOWN until Claude implements the contract.
- No dependency, Hypothesis, random/generated oracle, broker connection,
  market-data ingestion, backtest, research experiment or holdout access.
- No rollover-calendar computation, PnL, margin, FX conversion, historical
  swap inference or journal integration: all are outside this contract.
- No arbitrary Decimal exponent/string-format assertions, general exact
  linearity/doubling, undocumented integer-size caps, multi-error precedence,
  exact source prose, or unspecified CostBreakdown-constructor rejection.
- The AST check is a static convention check, not proof against every possible
  Python side effect. Parent `src/sochron/__init__.py` remains an implementer
  and implementation-review check per CORE-001 tests review F3; keep it
  code-free. Existing timebase assertions were preserved, not broadened.
- Fresh-session post-apply review, CI, owner labels/merge, green implementation
  verification and the owner's demo are not performed. The locked-path gate
  and control-test suite were not rerun: no controls were changed, and locked
  tests still need the established owner/CI process after application.
- No PROGRESS checkpoint was edited because the request explicitly limits
  repository outputs to this patch and handoff. Claude records the next
  checkpoint after the authorized application/review/commit.
- No unanswered question blocks the approved v1.2 test scope. The stale
  contract/PROGRESS wording awaiting r3 is superseded by the explicit r3
  readiness result and this task's instruction to proceed.

## D-006 next action for Claude

1. Confirm the current branch/base and recheck the patch SHA256 above. Run
   standalone `git apply --check docs/proposals/CORE-002-tests.patch`.
2. Apply the regular patch under D-006 with standalone
   `git apply docs/proposals/CORE-002-tests.patch`.
3. Verify all three applied SHA256 and Git blob values against this handoff;
   preserve LF endings and one trailing newline. Do not edit the locked tests
   directly. Use distinct basenames for future unit tests.
4. Obtain the required fresh-session review of the applied test diff against
   contract v1.2 and these oracles. The read-only helper checks during authoring
   are not that review.
5. Run `uv run --offline pytest tests -q -p no:cacheprovider` from the repository
   root. Before implementation, expect exactly the seven new red failures and
   the existing 24 passes, with zero skips. Run the required controls and explain
   every red-flag hit. After successful review/hash verification, commit red:
   `test(costs): acceptance tests for CORE-002`, body `Refs: CORE-002`.
6. Implement under the contract, obtain green evidence and independent review,
   and follow the existing owner-only label/merge process.

Delivery state: test proposal implemented and locally verified in the expected
red state; unapplied at delivery, unstaged, uncommitted, not merged or deployed.
CORE-002 implementation acceptance remains FAIL while the module is absent.
