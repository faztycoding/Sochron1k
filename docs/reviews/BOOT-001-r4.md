# Review BOOT-001 round 4 · applied posthook revision only

Repository HEAD `137ec7e`, base `main` (`951ee98`); reviewed the additional uncommitted hook
and settings changes found at session start. Reviewer: Codex, with fresh-context read-only
`posthook_r4_review`. Date: 2026-10-19 (+07:00).

The applied files match proposal `docs/proposals/BOOT-001-r3-posthook.patch`, SHA256
`2e5297ec5c8ece08b8074ed9994810553a336dd5501f937d531228972f26474b`:

- Hook Git blob: `c78d0385e1d1375b086017ff8cf9c82664136992`.
- Settings Git blob: `01f74bb3bb7c2d410abf074ba0ba35cb1bd23cc1`.
- Hook SHA256: `28c6283c38c3514dc6112c650f3d2ae09251e56d2873292f59929e55c0e384b9`.
- Settings SHA256: `9de3df7d0decc7d4eafb7280eaf39f48b58c210ec55f8c2de422fe485c1edf2e`.

Scope: the two r3 posthook findings and their direct impact. This session did not apply the
patch, change controls, or author the implementation. The fresh reviewer inspected the contract,
r3 findings and revised source before the handoff response. Native `/review` was unavailable.

**Result: both r3 changes are implemented and pass the focused checks below. Live dispatch
remains UNKNOWN, and F3 overall remains OPEN High.** The original r2 guard cases are unchanged.

| ID | Sev | Status | File:line | Evidence and remaining verification |
|----|-----|--------|-----------|-------------------------------------|
| F3, r3 failure event | High | Implementation verified in isolated probes; live criterion pending | `.claude/settings.json:99`, `.claude/hooks/check-locked-after.mjs:32` | The same detector is registered for success and failure events. Configuration assertions cover all three shell matchers. A protected fixture edit followed by a process exiting 1, then a simulated failure-event payload, produces exit 2 and the path report. Actual Claude dispatch/message delivery was not exercised. |
| F3, r3 first command | High | Implementation verified in isolated probes; live criterion pending | `.claude/settings.json:80`, `.claude/hooks/check-locked-after.mjs:80`, `:110` | PreToolUse records HEAD and ignored-file digests. Independent first-command probes detect both a protected edit committed into a clean tree and an ignored protected-file change. Clean first execution stays quiet; initial dirty protected files still report once. |

The [official hook reference](https://code.claude.com/docs/en/hooks#exit-code-2-behavior-per-event)
supports stderr/exit 2 reporting for both post events. That documents the API; it does not prove
the installed Claude session loaded these settings.

## Independent checks

`docs/proposals/BOOT-001-r4-posthook-probe.mjs` and
`docs/proposals/BOOT-001-r4-posthook-evidence.json` are local ignored reproduction artifacts.
Run from the repository root with `node docs/proposals/BOOT-001-r4-posthook-probe.mjs`.
The script invokes the applied hook in place, with disposable repositories as both cwd and
CLAUDE_PROJECT_DIR. It copies no hook/settings files and reads no real local configuration store.
Fixture Git identity is local; system/global identity and inherited identity variables are excluded.

| Check | Expected | Observed |
|-------|----------|----------|
| Configuration for Bash, PowerShell and Monitor | One baseline, one success handler, one failure handler per tool | PASS |
| Clean first command | Exit 0 | PASS |
| First command changes and commits a protected fixture; tree is clean | Exit 2, commit/path report | PASS |
| First command changes ignored `CLAUDE.local.md` fixture | Exit 2, local-file report | PASS |
| Protected edit, process failure, simulated failure-event dispatch | Exit 2, uncommitted-path report | PASS |
| Initially dirty protected fixture | Report once, then exit 0 for unchanged state | PASS |

The event routing in these probes is simulated. They are focused review evidence, not the
permanent regression suite or a live end-to-end test. The implementer's claimed 21/26 before
and 26/26 after are recorded in the handoff; that exact scenario script/log was not independently
available in the proposal directory, so this review does not certify that claim.

| Command | Result | Tested revision | Time, 2026-10-19 (+07:00) |
|---------|--------|-----------------|-------------------------|
| `node scripts/controls/test-controls.mjs` | PASS 28/28, fail 0, skipped 0 | `137ec7e` + applied blobs above | 17:27-17:28 |
| `node --check .claude/hooks/check-locked-after.mjs` | PASS syntax | Same applied hook | 17:28 |
| PowerShell `ConvertFrom-Json` and assertions of event entries/baseline flags | PASS | Same settings | 17:28:25 |
| `node docs/proposals/BOOT-001-r4-posthook-probe.mjs` | PASS 6/6 | Same applied blobs | 17:30:01 |
| `git hash-object` and `Get-FileHash` | PASS: source unchanged and matching proposal | Same applied blobs | 17:30:08 |
| `bash scripts/controls/red-flags.sh main` (absolute Git Bash executable) | PASS exit 0, six groups; untracked hook excluded | `137ec7e` + tracked working changes | 17:28 |
| `git diff --check` | PASS | Same working tree | 17:28 |

## AC status

| AC | Status | Evidence |
|----|--------|----------|
| AC-04 | FAIL | Original r2 guard defects remain; a post-run detector cannot prevent a completed write. |
| AC-06 | PASS | Scan reports its hits and exits 0. |
| AC-07 | UNKNOWN for complete applied tree | Tracked scan's secret groups are empty, but the new hook is untracked and excluded. Source was inspected separately; run the scan again after it is staged by its committer. |
| AC-01/02/03/05/08 | UNKNOWN in this review | No new live P25/gate evidence or architecture review. |

## Checked, nothing found; limits

- No new confirmed defect in the two original normal-execution cases. Existing tests, assertions,
  dependencies and the guard are unchanged. Initial dirty-file detection is preserved.
- Baseline errors intentionally do not block (`check-locked-after.mjs:139-145`). If no valid
  baseline exists afterward, first-command commit/local-file detection is not guaranteed.
  Error/corrupt-state behavior needs explicit regression coverage; passing normal probes does
  not establish coverage for that condition.
- Scan hits are the six existing policy/scanner/fixture groups, including the conditional
  Bash-unavailable skip; the executed suite skipped zero tests.
- The reported scratch permission incident was not reproduced. The exact denial was not supplied
  as an artifact, so this review does not certify its path-resolution explanation or authorize
  retrying a blocked operation under another path/tool. These probes create no hook directories.

## Not checked and handoff

No live Claude dispatch of baseline, success or failure events; no installed-version check;
no Linux run of this hook; no permanent CI regression tests; no broad shell-parser review.
No new CI result is claimed: the prior run at `7eae474` predates this hook.

Do not reapply the patch: matching files are already in the working tree. Claude should record
live evidence and commit the applied hook/settings after its checks. The owner pushes separately.
Maintain F3 High until the separately scoped guard work and its independent review are complete.
Delivery: implemented, with focused local verification; not merged or deployed.
