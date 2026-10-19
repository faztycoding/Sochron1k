# Review BOOT-001 round 2 · base main (951ee98) · fixes cca98c7 · head 4b83b1c · reviewer Codex, independent session

Date: 2026-10-19, Asia/Bangkok. Scope: recheck F1–F6 and their surrounding impact.
The independent reviewer read the contract, r1 report, fix diff and affected code before the
implementer's handoff. `/review` is not exposed as a callable command here; direct Git diff
review and independent checks were used. The owner authorized this report after the read-only
review. No implementation changes are included.

**Result: F3 remains OPEN, High.** F1, F2, F4, F5 and F6 are closed for their original defects,
with the qualifications below. BOOT-001 remains **implemented**, not verified.

## Finding disposition

| ID | Original severity | Status | Evidence and qualification |
|----|-------------------|--------|----------------------------|
| F1 | High | CLOSED — implementation | `.github/workflows/control-gate.yml:22` selects the base SHA; lines 32–39 fetch PR objects as data and run the base verifier. Both F1 regressions pass, including a PR that tampers with its own verifier. Actual gate enforcement and branch protection remain unverified. This bootstrap PR is not judged by the gate absent from main. |
| F2 | High | CLOSED — original defect | `scripts/controls/check-locked-paths.mjs:95`, `:195`, `:208` check commit history and uncommitted edits. All four F2 regressions pass on the configured local machine. The Linux merge fixture fails before the checker executes because it lacks Git identity; this does not establish an algorithm failure. |
| F3 | High | **OPEN** | The two original examples now return 2, but four surrounding write forms still return 0. See the confirmed findings and reproduction below. |
| F4 | Medium | CLOSED | `AGENTS.md:101`, `docs/architecture.md:20`, `:127`, `:193`, and SPIKE-001 AC-04/05 replace the unsupported time assertion with measurement requirements. They distinguish the Python API documentation from forum claims. Actual broker time behavior remains unverified. |
| F5 | Medium | CLOSED | `AGENTS.md:14`, `DECISIONS.md:13`, SPIKE-001 `:4`/`:14`, and architecture `:168` remove the circular prerequisite: approve the spike/dependency admission, run the temporary uv environment, review evidence, then decide D-001. |
| F6 | Medium | CLOSED — original self-match | `scripts/controls/red-flags.sh:55` splits self-matching literals without changing the resulting regex. The regression detects synthetic examples while excluding the scanner definition. One benign quotation remains in r1, so AC-07 still fails its literal empty-group requirement. |

The affected implementation and F4/F5 documents are identical between `cca98c7` and `4b83b1c`;
the later commit changes documentation checkpoints. Closure of these defects is not task approval.

## Open finding

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F3 | High | confirmed | `.claude/hooks/guard-bash.mjs:89`, `:235`, `:554`, `:579` | The three directory-scope payloads below return 0 with empty stderr. Subshell delimiters are discarded; nested-shell directory changes persist in the analyzer's global cwd. | Change directory in a child shell, then write in its parent. | The guard checks the wrong destination and permits AGENTS.md or `.claude/settings.json` writes, violating AC-04. | Preserve child-shell directory scope, or reject writes whose destination cannot be safely determined. | All three payloads return 2; existing normal-command and F3 regressions continue to pass. |
| F3 | High | confirmed | `.claude/hooks/guard-bash.mjs:434` | `curl -oAGENTS.md https://example.invalid/a` returns 0. The parser handles a separate short-option operand or a long option with `=`, not the attached short operand. | Use an attached curl output argument. | A standard output option targets a locked file without interception. | Normalize supported attached operands, or reject unresolved write options. | Attached locked-path output returns 2, while ordinary allowed destinations continue to pass. |

### Hook-only reproduction

Run from the repository root in PowerShell. Only the hook receives these strings as JSON;
none of the payload commands is executed, and no network request or protected-file write occurs.

```powershell
@'
import { spawnSync } from 'node:child_process';
const cwd = process.cwd();
const commands = [
  'cp /tmp/AGENTS.md .',
  'cd .claude && echo {} > settings.json',
  '(cd /tmp); cp /tmp/AGENTS.md .',
  'bash -c "cd /tmp"; cp /tmp/AGENTS.md .',
  'cd .claude; (cd ..); echo {} > settings.json',
  'curl -oAGENTS.md https://example.invalid/a'
];
for (const command of commands) {
  const r = spawnSync(process.execPath, ['.claude/hooks/guard-bash.mjs'], {
    encoding: 'utf8',
    input: JSON.stringify({ tool_name: 'Bash', cwd, tool_input: { command } }),
    env: { ...process.env, CLAUDE_PROJECT_DIR: cwd }
  });
  console.log(JSON.stringify({ command, exit: r.status, stderr: r.stderr }));
}
'@ | node --input-type=module -
```

Observed at 14:57:43 +07:00 on `4b83b1c`: expected exit 2 for all six inputs;
actual exits **2, 2, 0, 0, 0, 0**. A harmless Bash probe,
`cd .claude; (cd ..); pwd`, confirmed that the parent remains in `.claude`.

## CI failure and F2 evidence qualification

[PR #1](https://github.com/faztycoding/Sochron1k/pull/1) was opened with the requested title and
the exact contents of `docs/proposals/BOOT-001-pr-body.md`; the returned body was compared to
the source and matched. PR head: `4b83b1c3a940f03f7babcf509d271f5805833091`.

[CI run 39219308064, job 117950596549](https://github.com/faztycoding/Sochron1k/actions/runs/39219308064/job/117950596549)
ran on Ubuntu 24.04.5 with Git 2.55.0. The checked-out synthetic merge was
`5b7490bbfd7efcfac98edf393ed3198b62785c26`. The root session retrieved the job log;
the independent reviewer separately reproduced its missing-identity failure locally.

Failed step: **Control self-tests (hooks and lock rules)**, `node scripts/controls/test-controls.mjs`.
Relevant log excerpt, 2026-10-19 07:57:02Z (14:57:02 Asia/Bangkok):

```text
not ok 24 - F2: an edit made inside a merge commit fails
location: '/home/runner/work/Sochron1k/Sochron1k/scripts/controls/test-controls.mjs:385:1'
Command failed: git merge --no-ff --no-commit side
Committer identity unknown
TestContext.<anonymous> (file:///home/runner/work/Sochron1k/Sochron1k/scripts/controls/test-controls.mjs:395:5)
# tests 28
# pass 27
# fail 1
# skipped 0
Process completed with exit code 1.
```

Fixture commits receive per-command identity at lines 43 and 51, but the merge at line 395
receives none. A clean runner therefore fails during fixture setup, before the invariant is
evaluated. At 14:59:21 +07:00 the reviewer reproduced exit 128 / `Committer identity unknown`
by running that test with system/global Git configuration excluded in the child environment.
No Git configuration was changed. Supply identity within the test fixture and rerun CI;
do not treat the configured developer machine's result as portable evidence.

Workflow status: **FAIL**. The F2 merge-invariant check on Linux is **BLOCKED** by its fixture.
The subsequent red-flag scan step is **SKIPPED**. No successful Linux verification is claimed.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-01 | UNKNOWN | Complete P25 runs in fresh sessions of both tools were not performed. |
| AC-02 | UNKNOWN | Hook logic passes locally and on CI; full live Claude settings enforcement was not independently demonstrated in this round. |
| AC-03 | UNKNOWN | Worktree logic passes locally and on CI; complete live enforcement was not independently demonstrated. |
| AC-04 | FAIL | F3 hook payloads still permit locked-path writes. |
| AC-05 | UNKNOWN | F1/F2 local behavior passes, but actual trusted gate and label enforcement were not demonstrated on GitHub; the Linux merge fixture is blocked. |
| AC-06 | PASS | The installed Git Bash executable ran the scanner, reported seven groups and returned 0. The CI scan was skipped separately. |
| AC-07 | FAIL | The required empty Possible secrets group contains one benign quotation in r1. No credential was identified by the patterns run. |
| AC-08 | UNKNOWN | F4/F5 document corrections pass this scoped review. Complete SPEC/architecture verification and the owner/adversarial review remain outside this round. |

## Checks run

Local times: 2026-10-19, Asia/Bangkok. Local runtime: Windows, Node v26.12.0,
Git 2.46.1.windows.1. Local results were produced by the independent reviewer.

| Command/check | Result | Commit | Time (+07:00) |
|---------------|--------|--------|---------------|
| `node scripts/controls/test-controls.mjs` | PASS — 28/28, 0 skipped | 4b83b1c | 14:57:42–14:57:56 |
| `node scripts/controls/check-locked-paths.mjs main` | FAIL — expected bootstrap result, 41 unapproved control changes | 4b83b1c | 14:57:43 |
| `bash scripts/controls/red-flags.sh main` | BLOCKED — bash not recognized in PowerShell PATH | 4b83b1c | 14:57:43 |
| `& 'C:\Program Files\Git\bin\bash.exe' scripts/controls/red-flags.sh main` | PASS execution — exit 0, seven groups | 4b83b1c | 14:58:08–14:58:10 |
| Hook-only reproduction above | FAIL — four prohibited forms return 0 | 4b83b1c | 14:57:43 |
| `node --test --test-name-pattern='F2: an edit made inside a merge commit fails' scripts/controls/test-controls.mjs`, child environment excluding system/global Git configuration | BLOCKED invariant check — fixture merge exits 128, test process exits 1 | 4b83b1c | 14:59:21 |
| `git diff --quiet cca98c7 HEAD` scoped to affected implementation and F4/F5 documents | PASS — exit 0 | cca98c7 → 4b83b1c | 14:59:33 |
| `git status --short` before report authorization | PASS — clean | 4b83b1c | 14:59:33 |
| GitHub `ci / control-plane` | FAIL — 27 pass, 1 fixture failure | synthetic merge 5b7490b; PR head 4b83b1c | 14:57:02 |

## Red-flag leads

Seven groups: skipped-test handling, type-check exclusions, lint exclusions, placeholder/mock
patterns, Possible secrets, destructive/bypass commands, and order/account mutation surface.
Hits are policy text, scanner definitions, guard code and negative-test fixtures, except the
single benign keyword quotation in the preserved r1 report. The scanner's original secret
self-hit is gone; Secret-like value assigned is empty. The F6 test skips only when Bash is
missing; the full local run skipped zero tests. These patterns do not prove that every possible
secret is absent. AC-07 must not be silently weakened to accept the known quotation.

## Checked, nothing further found (and how)

- F1: inspected trusted base checkout, read-only token, pinned action and absence of executed PR code; ran tampered-verifier regressions.
- F2: ran history, registry-prefix, uncommitted-edit and merge regressions; separated fixture failure from checker behavior.
- F4/F5: compared policy, architecture, decisions and SPIKE contract for corrected time assumptions and executable prerequisites.
- F6: ran preserved-detection regression and the actual branch scan.
- Fixes add no project dependency or lockfile, retain the original 19 tests and introduce no application or trading code.

## Not checked (and why)

- Actual control-gate execution, required-check protection and label lifecycle: bootstrap gate is absent from main; no settings were changed.
- Complete P25/live enforcement in both tools: outside this scoped re-review.
- MT5 timestamps, connectivity, accounts or orders: no broker operation is authorized here.
- Exhaustive shell syntax and arbitrary executables: probes cover the confirmed surrounding-impact defects only.
- Independent replay of the handoff's pre-fix 19-pass/9-fail claim, and changes unrelated to F1–F6: outside this round.

Runtime access is unrestricted with approval policy `never`; read-only review was procedural,
not a runtime-enforced sandbox. No protected write payload was executed.

## Files changed, checkpoint and next action

Only `docs/reviews/BOOT-001-r2.md` is added under the owner's report-write authorization.
The independent review changed no repository files; existing tests used temporary fixtures.
PROGRESS.md, implementation, test files and configuration remain untouched under that scope.
No push, merge, deployment or approval review was performed. The requested approval label
has not been created or applied: F3 remains High and CI is failing.

External operation completed: PR #1, open, exact requested description verified. CI run
39219308064 completed with failure; no run remains pending. PR head remains 4b83b1c.

Delivery state: **implemented**. Next: fix F3 with regression coverage; supply Git identity
within the merge fixture; rerun CI; resolve the documented AC-07 quotation mismatch with the
owner; then recheck affected findings. The owner retains control approval and merge authority.
