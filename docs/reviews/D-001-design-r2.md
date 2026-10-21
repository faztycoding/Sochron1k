# Review D-001 design round 2 · base 3817f36 · head fc38bc3 · reviewer Codex, fresh headless session

Reviewed on 2026-10-21 +07. Branch: `chore/D-001-architecture-revision`.
Exact head: `fc38bc327de50564d0d9a46f29a5fbfb0b945761`.
Base: `3817f367a6fe2f37cc82e5a75a85bb874ea0822a` (merged main).
Procedure: `.agents/skills/adversarial-design-review/SKILL.md`, architecture mode.

Scope: document-level proof for r1 F1/F2, SPIKE fact limits, r1 phase-gate
carry-forward, and consistency of architecture, D-001 and SPEC. Read the four
revision commits with `git show`: `33e5e8d`, `81ed170`, `f38838c`, `fc38bc3`,
and `git diff 3817f36..HEAD -- docs/architecture.md DECISIONS.md SPEC.md docs/handoff/D-001.md PROGRESS.md`.
The r1 report, recorded SPIKE evidence/contract and Handbook supply the review
criteria. Implementer responses are claims checked against the documents.
There is no approved ENV-1, SLICE-R1 or SLICE-E1 contract in this checkout.

## Decision advice

**F1 and F2 are CLOSED at the document level. One new Low finding, F3, is OPEN.**
The selected Python monolith remains a reasonable candidate. Align the stale
environment summaries in F3 before presenting the final proposal for owner
acceptance; no new architecture alternative is required by this review.
No confirmed Critical, High or Medium design finding remains in this scope.

D-001 remains **proposed**. This report neither accepts the decision nor proves
isolation or execution safety. Acceptance would still require ENV-1 before
research ingestion/experiments, approved implementation contracts and dependency
admission, and the specified E1 evidence before any authorized Demo action.
SPIKE's read-only authorization is not an execution authorization.

## Findings

Severity on CLOSED rows is the original r1 severity, not an unresolved defect.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F1 — CLOSED (document level) | High | confirmed | `docs/architecture.md:112`, `:119`, `:123`, `:204`, `:209`, `:248`; `DECISIONS.md:12` | `33e5e8d` separates hosts/capabilities, blocks interim research, and makes ENV-1 mandatory; detailed verification below. | Research would otherwise retain terminal/cache or acquire the excluded interval through `data`. | The design now forbids that path; actual environmental isolation is still unverified. | No further F1 design fix required. Implement and verify ENV-1 under its own approved contract. | Document proof met. Synthetic excluded-period read/fetch denial and import enforcement remain future evidence, not a PASS from this review. |
| F2 — CLOSED (document level) | Medium | confirmed | `docs/architecture.md:163`, `:176`, `:183`, `:187`, `:189`, `:301`; `DECISIONS.md:19` | `81ed170` defines immutable authorization scope, state binding, checkpoints, zero-send cases and the check/send race. | Another Demo account/server, expired authorization, reconnect or restart. | The design now rejects these cases instead of relying on Demo mode alone. | No further F2 design fix required. E1 must implement and prove the invariant. | Document proof met. Runtime negative cases and reconciliation tests remain unexecuted. |
| F3 — OPEN | Low | confirmed | `SPEC.md:52`, `:73`, `:74`; `DECISIONS.md:8` | SPEC still calls the holdout location and runner host TBD and combines local research with terminal access. D-001's summary sequence omits ENV-1. These disagree with updated `SPEC.md:89`/`:90`, `DECISIONS.md:13`/`:15` and architecture `:112`/`:119`/`:248`/`:249`. | A future contract is drafted from the SPEC environment summary or ADR phase sequence alone. | Obsolete locations/order of work can be carried forward. The explicit new prohibitions elsewhere limit this to a documentation inconsistency; it does not reopen F1. | Synchronize SPEC sections 5/8 and the D-001 phase sequence with the VPS target, restricted single-PC interim and ENV-1 prerequisite. Keep cutoff and budget TBD. | Re-read those summaries against architecture section 6.1: none should permit research alongside terminal access on one host, call the target location undecided, or omit ENV-1 from the R1 path. No runtime test needed for this wording fix. |

### F1 proof checked

- Architecture `:87` through `:102` and `:110` through `:112` locate terminal,
  history cache, acquisition, raw captures, journal/backups and holdout on the
  Windows VPS. Research receives approved pre-cutoff snapshots with manifests;
  frozen-strategy holdout evaluation stays on the acquisition host.
- `:118` through `:121` explicitly acknowledge that the current PC is not an
  isolated research host. Holdout selection, research ingestion and strategy
  experiments are prohibited during this interim. `DECISIONS.md:15` repeats
  the prohibition. Pure preparation requires an approved contract; it does not
  authorize market-data experiments or bypass D-001 acceptance.
- `:123` through `:126`, `:248` through `:249`, `:289` and `:299` make ENV-1
  a prerequisite: VPS readiness/migration, local terminal/cache removal, and a
  synthetic sentinel proving the research identity cannot read or fetch the
  excluded interval directly or through `data`. This is a future measurable
  gate, not a statement that migration or isolation has already happened.
- The import allowlists at `:204` through `:209` remove the former permitted
  `research -> data -> broker` path. Research imports `data.snapshot`, which
  permits only `core`/`timebase`; `data.acquire` is separate and belongs only
  on the acquisition host. `:238` and `:298` require enforcement of the table.
  ENV-1 must also test capabilities outside normal imports, including retained
  captures/backups and remote access; an AST check alone cannot prove isolation.
- `:114` and `DECISIONS.md:17` explicitly reject a same-host folder, VM or
  separate user as a substitute without a separately recorded owner policy
  change. `:115` assigns VPS cost to Q-10 instead of assuming zero cost.

### F2 proof checked

- Architecture `:163` through `:174` defines immutable terminal identity,
  server, authorized account, Demo mode, allowed actions/symbols, maximum
  volume and expiry; account numbers remain masked in reports/logs.
- `:176` through `:181` requires checks at startup, reconnect/reinitialize and
  before every external action. Unknown/mismatched identity or expired scope
  halts actions. `:183` through `:185` binds journal, risk snapshot and
  reconciliation to the scope, including pending intents after restart.
- `:187` through `:192` requires one sender per scope and a dedicated terminal,
  excludes manual account switching while running, and explicitly admits the
  non-atomic check/send race. The post-send check is mitigation, not proof that
  an intervening account switch is impossible or reversible.
- The zero-send cases at `:301` through `:308` cover non-Demo mode, another
  Demo account/server, forbidden symbol/action, expiry, reconnect identity
  change and restart with an intent bound to another account. They are planned
  acceptance cases, not executed tests. `DECISIONS.md:19` through `:26` carries
  the invariant and keeps SPIKE read-only permission separate.
- When E1 is contracted, its terminal-identity check must identify the approved
  terminal instance; the company/build example at `:167` is not by itself a
  unique installation identifier. This is an implementation-contract detail
  still to specify, not evidence that the repaired account/scope invariant has
  already failed.

## AC status

No new formal AC IDs are invented for this design review. Review-check rows
below refer to this request and r1's proof requirements; SPIKE AC-04 keeps its
existing contract meaning. PASS means document review only where stated.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| r1 F1 document proof | PASS | Host layout, interim prohibition, offline/acquisition split and pre-R1 ENV-1 gate are explicit. |
| r1 F2 document proof | PASS | Scope/checkpoints/state binding, zero-send cases and residual race are explicit. |
| SPIKE-001 AC-04 (carried, not rerun) | UNKNOWN | GMT+0 does not distinguish API UTC from server time; unsynchronized Windows clock remains disclosed. |
| Refreshed facts and U1-U3 | PASS | Connectivity is host/account-specific; VPS requires a repeat. U2/U3 stay partial; no research-ready start is claimed. |
| r1 phase-gate carry-forward | PASS | All eight phase rows are represented, with the original required-gates section explicitly referenced; details below remain required for future acceptance. |
| Cross-document consistency | FAIL | F3: stale SPEC environment/location summaries and D-001 phase sequence. |
| ENV-1 isolation / E1 runtime proof | UNKNOWN | No implementation, isolation probe or execution test was performed in this review. |

## Phase-gate traceability

Architecture `:282` cites r1's required-gates section and requires relevant
conditions to enter future contracts. Section 13a is faithful in substance;
its shorter wording must not be used to discard the cited acceptance details.

| r1 gate (`docs/reviews/D-001-design-r1.md`) | Current architecture | Required interpretation when contracting |
|---|---|---|
| `:119` R1 time/data | `:286`, also `:30` and `:274` | Version the empirical rule and provenance, including package version; distinguish clock health, quote freshness and offset. Unsynchronized time cannot certify subsecond UTC; a stale quote cannot trigger an automatic offset correction. |
| `:120` R1 data selection | `:287`, also `:31` and `:275` | Validate daily/monthly coverage before strategy selection; freeze calendar and cost provenance. Today's specification does not establish historical bid/ask or swap costs. |
| `:121` R1 first experiment | `:288` | Persist run-start before computation and append outcome/failure. An interrupted start must be recovered/accounted for; interruption and disk-full tests need that oracle. |
| `:122` E1 first send | `:290` | Verify durable intent commit and actual SQLite settings; WAL alone is insufficient. Storage failure prevents the send. |
| `:123` E1 retry/restart | `:291` | Preserve UNKNOWN; reconcile orders/deals/positions and test crashes, delayed visibility and duplicate runners. An initially empty query or absent response alone must not establish non-execution or authorize retry. |
| `:124` E1 partial fill/SL | `:292` | Account for actual exposure and verify resulting-position SL; no full-volume retry after a partial fill. Use deterministic adapter cases before specifically authorized Demo cases. |
| `:125` E1 runtime / OPS-1 | `:293` | E1 already needs restart safety. OPS must demonstrate alerts and consistent journal restore with outstanding intents, followed by terminal reconciliation before actions resume. |
| `:126` Dependency/deployment | `:294`, `:300` | Spike approvals stay spike-only; pin environments and refresh Windows adapter evidence. Python CI requires its own approved control change; existing control CI is not Python/runtime proof. |

ENV-1 is additionally explicit at `:289`. The abbreviated retry row still
requires delayed-visibility testing and preservation of UNKNOWN, so the omission
of r1's full empty-query sentence is not treated as a contradictory permission
or a separate confirmed defect.

## Checked, nothing found (and how)

- Compared architecture `:29` through `:32` and U1-U3 (`:273` through `:275`)
  with recorded evidence `docs/evidence/SPIKE-001.md:11` through `:16`, `:27`
  through `:31`, `:73` through `:96`, `:110` through `:116`, and `:122` through
  `:157`. The proposal retains the GMT+0/clock limits, March-only DST evidence,
  date-specific sessions, sparse early M1 and anomalous 2017. First returned
  M1/tick timestamps are not complete coverage or an approved research start.
- Checked SPEC `:40` against the new execution invariant: Demo plus approved
  contract scope remains compatible; no execution permission is inferred from
  the spike. Architecture and DECISIONS still mark D-001 proposed.
- Traced pure shared strategy, the single timebase, deterministic risk gate,
  explicit costs/stress, registry and random-entry comparison in the current
  module map and invariants. This delta does not relax those design obligations.
- Checked failure/operations gates for terminal-down, disconnect, reboot,
  disk-full, package/host change, duplicate send and partial fill against r1.
  VPS cost is acknowledged; Q-10 is still an owner budget decision. Nothing
  claims that backups, isolation or runtime recovery are already verified.
- Three read-only sub-reviewers checked F1, F2 and facts/gates independently.
  The primary reviewer checked the retained conclusions against the cited
  files. This assistance supplies no runtime evidence or owner approval.

## Not checked (and why)

- No MT5/broker connection, account operation, installation, application code,
  backtest, actual holdout access, migration, sentinel run or power-loss test:
  this is the authorized document-only review.
- No fresh SPIKE/Python tests, package/API verification, raw market-data audit,
  clock measurement, annual calendar validation, license determination or
  profitability evaluation. SPIKE results above are recorded inputs.
- No fresh external CI/PR verification. The branch's pushed status and past CI
  results are context, not newly verified evidence here. Control self-tests
  were SKIPPED because this delta changes documentation only, not controls.

## Checks and delivery

The following checks ran on `fc38bc3` at 2026-10-21 06:48:46-48 +07, before
creating this review file. They check the tracked branch delta, not ENV-1/E1.

| Command | Result | Commit | Time (+07) |
|---|---|---|---|
| `git show 33e5e8d`; `git show 81ed170`; `git show f38838c`; `git show fc38bc3` (relevant paths) and requested five-path base diff | PASS: document changes inspected | `fc38bc3` | 2026-10-21, during this review before 06:48:46 |
| `git diff --check 3817f36..HEAD -- docs/architecture.md DECISIONS.md SPEC.md docs/handoff/D-001.md PROGRESS.md` | PASS, no whitespace errors | `fc38bc3` | 06:48:46 |
| `bash scripts/controls/red-flags.sh main` | PASS execution, exit 0; one explained pattern group | `fc38bc3`; local main `0916776` | 06:48:46-48 |
| `bash scripts/controls/red-flags.sh 3817f36` | PASS, exit 0; zero pattern groups | `fc38bc3` | 06:48:46-48 |
| `node scripts/controls/check-locked-paths.mjs main` | PASS; no locked/append-only violation | `fc38bc3` | 06:48:46-47 |
| `node scripts/controls/check-locked-paths.mjs 3817f36` | PASS; no locked/append-only violation | `fc38bc3` | 06:48:46-47 |

Bash was invoked using `C:/Program Files/Git/bin/bash.exe`. Local main remains
at `0916776`; the broad scan therefore includes already merged SPIKE fixtures
in `spikes/SPIKE-001/test_probe.py`. Those fake/stub test helpers explain its
single group; the supplied merged base isolates this documentation delta and
has zero groups. No secret, order-mutation or deleted-test hit was reported.
`rg --files docs/contracts` was BLOCKED because `rg` was unavailable; ordinary
PowerShell directory enumeration and UTF-8 reads succeeded without changing
configuration. This did not block document inspection.

Only `docs/reviews/D-001-design-r2.md` is written by this session. It is left
untracked for Claude to stage/commit as requested. The scanner lists untracked
files but does not scan their contents; its PASS must not be represented as a
content scan of this new report. Final report/scope checks are recorded below.
No PROGRESS/handoff change, stage, commit, push, merge or acceptance by Codex.
Delivery: review report implemented; reviewed design still proposed; runtime
verification pending. Next: Claude addresses F3 and records the handoff, then
the owner decides D-001 with ENV-1/R1/E1 gates intact.

Final file/scope checks at 2026-10-21 06:49:57-59 +07, on `fc38bc3` plus this
untracked report:

| Command | Result |
|---|---|
| `git diff --no-index --check -- /dev/null docs/reviews/D-001-design-r2.md` | No whitespace diagnostics; exit 1 reflects the new-file difference in no-index mode. |
| `git status --short`; `git diff --name-only`; `git diff --cached --name-only`; `git rev-parse HEAD` | PASS: only this report is untracked; no tracked working-tree changes, no staged changes; HEAD remains `fc38bc3`. |
| `node scripts/controls/check-locked-paths.mjs 3817f36` | PASS, exit 0; seven paths including the new report, no locked/append-only violation. |
| `bash scripts/controls/red-flags.sh 3817f36` | PASS execution, exit 0; zero groups in tracked delta; correctly lists this report as untracked and unscanned. |
