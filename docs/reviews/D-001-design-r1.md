# D-001 architecture design review r1

Reviewer: Codex · 2026-10-21 +07 · reviewed revision
`3817f367a6fe2f37cc82e5a75a85bb874ea0822a` (SPIKE-001 merged in PR #3).
Scope: proposed D-001 and `docs/architecture.md`, against SPEC, Handbook ch.34
and merged SPIKE-001 evidence. Procedure:
`.agents/skills/adversarial-design-review/SKILL.md`, architecture mode.
This is a design review, not implementation verification or owner acceptance.
No approved R1/E1 implementation contract exists yet.

## Decision advice

**Keep option A as the candidate; revise the boundaries before accepting the
current document unchanged.** SPIKE-001 supports Python-to-MT5 connectivity on
this Windows machine. It gives no reason to add an EA bridge, web service or
database server now. Two design findings are OPEN: F1 High and F2 Medium.
Neither finding alleges an executed trade or observed holdout leak.

F1 needs a concrete environment choice before accepting the research design;
F2 needs an authorization invariant, with implementation proof before any E1
order. Name the remaining phase gates below in the revised proposal; implement
them only under future approved contracts. This review does not accept D-001,
alter acceptance, admit dependencies or extend SPIKE's read-only authorization.

## Evidence used and limits

| Input in `docs/evidence/SPIKE-001.md` | Established by recorded evidence | Not established |
|---|---|---|
| `:11`, `:30` | Python 3.12 / MetaTrader5 5.0.6231 connects to build 6274, Exness Demo ending 8107, trading disabled | Order execution or permission to enable it |
| `:79` to `:96` | Twelve observations agree approximately with the machine clock on this GMT+0 server | Synchronized UTC reference or discrimination between API UTC and server time; AC-04 remains UNKNOWN |
| `:98` to `:116` | March 2026 US/EU DST observations support the recorded zero-offset interpretation for this server | Universal time semantics, an annual session calendar, or another server's behavior |
| `:118` to `:157` | First returned M1 in 2014, sparse early years, anomalous 2017, tick history from January 2026 | Complete M1, a research-ready start date, or historical bid/ask paths across the whole M1 period |
| `:57` to `:75` | Owner-transcribed sessions at the capture date; weekday pause is 62 minutes | Image-proven timezone, winter/holiday schedule or historical costs |

The report and committed JSON summaries are inputs; the terminal was not
accessed and raw market history was not reread. Existing 21-test evidence is
carried from SPIKE's review, not rerun or represented as Linux Python CI.

## Findings

### F1 — OPEN · High · The research host can also acquire the held-out period

- **Location:** `docs/architecture.md:78`, `:86`, `:119`, `:130`, `:134`, `:162`;
  `docs/HANDBOOK-CORE.md:255`; `SPEC.md` Q-08.
- **Evidence:** the system context puts the app and MT5 together on the owner's
  Windows host. The diagram describes the vault only as outside the checkout,
  while the trust boundary and Handbook require held-out data outside the
  research machine. Research may import `data`, which acquires through the
  broker port. The stated enforcement is an owner procedure, cutoff loader and
  `.gitignore`; these do not exclude terminal history/cache or acquisition
  capability from the research environment. SPIKE shows this host can retrieve
  broad history, but no holdout cutoff has been selected.
- **Failure path:** choose a historical cutoff and move a Parquet holdout
  elsewhere, but retain MT5 history or acquisition on the research host. The
  excluded interval remains accessible or can be fetched outside the snapshot
  loader. Direct-import restrictions do not block the permitted
  `research -> data -> broker` dependency path.
- **Impact:** the claimed physical boundary is not established; an eventual
  holdout result could lose its evidential value. Severity reflects the research
  invariant, not real-money exposure. No existing contamination is asserted and
  no held-out data was requested to demonstrate this finding.
- **Minimal change:** specify distinct acquisition/evaluation and research
  environments. Research receives only approved pre-cutoff snapshots, with
  neither withheld cache nor terminal/acquisition access. Separate offline
  snapshot reading from broker acquisition in import and capability rules.
  Preserve the literal off-machine requirement. A directory, same-host VM or
  permission convention must not silently replace it; a different policy needs
  an explicit owner decision.
- **Proof of fix:** revised diagram/rules locate terminal cache, raw captures,
  backups and holdout. Before R1, an approved environment check and synthetic
  excluded-period sentinel prove the research identity cannot read or fetch it,
  directly or through `data`. Do not use actual holdout as the test oracle.
  Include environment costs in Q-10 rather than assuming one-PC cost stays zero.
- **Gate:** choose the boundary before unqualified D-001 acceptance; verify it
  before research data ingestion/experiments under SLICE-R1.

### F2 — OPEN · Medium · Demo mode does not bind execution to the authorized account

- **Location:** `docs/architecture.md:118`, `:136`, `:156`, `:207`;
  SPEC section 3 and the SPIKE contract's Authorization section.
- **Evidence:** the explicit pre-send check tests Demo mode; its planned
  negative case tests non-Demo mode. SPIKE already needs a narrower scope:
  server, permitted account and expiry. The generic execution design does not
  carry these identity/lifetime conditions into each action. MetaQuotes documents
  that omitted initialization identity can use the last account; the Python
  order request has no account selector. See
  [initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py)
  and [order_send](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py).
- **Failure path:** the owner changes login to another Demo account, or reconnect
  attaches to a different terminal. Demo mode still passes while authorization,
  risk snapshot and journal belong to the original account. The same gap applies
  after the scoped permission expires.
- **Impact:** an eventual executor can meet the documented type check yet act
  outside the approved scope or reconcile against the wrong account. This is a
  prospective design gap; the merged read-only spike has its own checks and no
  current order path.
- **Minimal change:** make terminal identity, server, authorized account,
  allowed actions/symbols and expiry part of immutable execution scope. Validate
  at startup, reconnect and immediately before each external action; bind
  journal/reconciliation/risk state to that scope. Unknown or mismatched identity
  halts actions. Keep one authorized sender per scope and document exclusion of
  manual account switching while it runs. Logs remain masked; no credentials
  belong in the contract or report.
- **Proof of fix:** record the invariant in D-001; E1 acceptance rejects another
  Demo account/server, expired scope and reconnect identity change with zero
  send calls. Test restart/reconciliation account binding. Separate check/send
  calls are not an atomic account lock: state the dedicated-terminal assumption
  and residual race instead of claiming the pre-check makes switching impossible.
- **Gate:** add the invariant before accepting the execution portion of D-001;
  implementation and authorized Demo proof belong to E1, not this review.

## Required phase gates, not additional confirmed defects

These are bounded design/contract requirements, not requests to implement later
phases now. Missing future implementation is expected.

| Before | Gate and smallest useful evidence |
|---|---|
| R1 time/data contract | Version the empirical time rule with server/symbol, observed build/version and evidence window; retain raw time and AC-04 UNKNOWN. Separate clock health, quote freshness and offset checks. Old quotes during market closure do not prove timezone change; an unsynchronized clock cannot certify subsecond UTC. Never automatically correct offset from one stale quote. |
| R1 data selection | Daily/monthly coverage and gap validation select a usable range before strategy selection. Sparse 2014-2016 and anomalous 2017 are not fixed by calling the first bar the research start. Freeze calendar assumptions and cost provenance. Preserve UNKNOWN; do not infer historical bid/ask paths or swaps from today's specification. |
| R1 first experiment | Persist a run-start event with hypothesis/version, parameters, seed, revision and dataset hash before computation; append outcome/failure or recover interruption. Test interruption and disk-full behavior. Append-only checks on committed JSONL do not prove all failed/uncommitted experiments were counted. |
| E1 first send | Require successful durable intent commit before the external call. SQLite WAL alone does not guarantee durability: with NORMAL synchronization a committed transaction can be lost after power failure. Specify/verify durability settings and halt on storage errors. See [SQLite synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous). |
| E1 retry/restart | A local idempotency key does not prove broker deduplication. Preserve UNKNOWN across restart; reconcile orders, deals and positions before retry. An initially empty query or absent response alone must not prove non-execution. Test crash-before-send, crash-after-send-before-recording, delayed visibility and duplicate runner startup. |
| E1 partial fill/SL | Record actual executed volume/exposure and confirm protective SL on the resulting position. A non-full result must not mean zero fill followed by full-volume retry. MetaQuotes defines [partial completion](https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes). Use deterministic adapter tests before explicitly authorized Demo cases. |
| E1 supervised runtime / OPS-1 unattended | Terminal-down, disconnect, sleep/reboot and disk-full handling stops new actions, preserves uncertainty and reconciles before re-enabling. E1 needs restart safety even if scheduling/alerts wait for OPS-1. OPS-1 rehearses alert delivery and a consistent journal restore including outstanding intents, followed by terminal reconciliation. |
| Dependency/deployment change | SPIKE approvals are spike-only. Admit project dependencies separately, pin reproducible environments and refresh Windows adapter evidence for relevant package/terminal changes. Python CI needs its own approved control change; current green CI checks controls. |

## Costs, reversibility and evidence that would change the recommendation

- **Solo operations:** the acquisition/holdout boundary may need another
  machine. Windows uptime, backup, storage growth and licensed data can cost
  money or owner time. Q-09/Q-10/Q-12 remain owner decisions; no VPS or budget
  value is selected here.
- **Hard to reverse:** contaminated holdout and unlogged variants cannot be
  repaired by code rollback. Persist raw time, source/version metadata, snapshot
  hashes and versioned derived data so corrected interpretation can be replayed
  without rewriting originals. Keep broker-specific tickets/types out of pure
  strategy interfaces to preserve the adapter boundary.
- **Would change the recommendation:** inability to obtain a useful, licensed,
  isolatable dataset; a required host without compatible MT5; measured latency
  the adapter cannot meet; or required terminal-side behavior while Python is
  down. Current evidence establishes none of these failures. Resolve data
  suitability with the smallest approved quality task before a backtester.

## Checked, nothing found

- Pure shared strategy, one timebase, broker adapter boundary, deterministic
  risk gate, explicit costs/stress and random-entry comparison fit the goal at
  the design level.
- Windows terminal evidence and Linux-testable pure modules are compatible;
  the proposal already acknowledges Windows integration evidence is necessary.
- Real money remains excluded and implementation is deferred to approved
  contracts. No feature scaffolding is needed to resolve this review.
- U1 is supported; U2/U3 need the limited interpretations above. Refreshing
  dated fact/unknown tables is not evidence the monolith choice has failed.
- D-007/D-008 exceptions are not closed or changed by this review.

## Not checked

- No broker/terminal connection, order, backtest, holdout access, isolation
  probe, power-loss experiment, dependency installation or CI edit.
- No raw-data provenance audit, independent UTC measurement, winter session
  capture, data-license determination or profitability claim.
- Two supporting read-only sub-reviewers supplied preliminary observations but
  stopped on usage limits. They are not counted as completed reviews; the primary
  reviewer checked the retained findings against the cited files and sources.
- Current control-plane CI success does not verify future runtime gates.

## Verification and delivery

The owner merged PR #3 at 2026-10-21 03:38:34 +07 as `3817f36`.
The [post-merge ci run](https://github.com/faztycoding/Sochron1k/actions/runs/39493719822)
reports success on that SHA, updated 03:39:15 +07; API checked 03:41:26 +07.
This covers controls, not a new Python probe run.

Report, handoff and checkpoint are documentation only. Local check/commit
details are in `docs/handoff/D-001.md`. No push or merge by this reviewer.
D-001 remains proposed; both findings remain OPEN.
