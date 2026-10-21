# Review D-001-agents round 1 · base b22d75a · head working tree · reviewer Codex (fresh headless session)

Date: 2026-10-21 (+07). Branch: `chore/D-001-agents-phase`.
HEAD: `b22d75a9caea81cfd735256ca2afabd9ca043107`.
Reviewed artifact: the uncommitted `AGENTS.md`, SHA256
`d5fe0d89952075438a51d6fe72570267c1e7a9ab225c91d701276f8a9acc775f`.

**Verdict: READY TO COMMIT for the requested content/integrity review. No findings.**
This recommendation applies only to that artifact. It does not approve a merge, a control-change
label, dependencies, research, or execution. The locked-path check correctly remains **FAIL**
without the owner's PR label; this is an outstanding owner gate, not a defect in this patch.
The existing control suite passes all 105 tests; this is local evidence, not CI approval.

The task contract for this review is the owner's four checks in the headless request. Content
scope is `git diff -- AGENTS.md` against HEAD, not the inherited architecture branch history.
The supplied final handoff section, accepted D-001 scope, architecture sections 6.1/7.1/13a,
and SPIKE-001 evidence are the review oracles. The cross-agent-review and security-review
procedures were applied within the owner's explicit one-output-file authorization.

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|

No confirmed findings or unresolved questions; no severity assigned.

## AC status

The AC numbers below map to the four checks in this request, not the SPIKE-001 AC numbers.

| AC | Status (PASS/FAIL/UNKNOWN) | Why |
|----|----------------------------|-----|
| AC-01: artifact and six edits | PASS | Both expected AGENTS hashes match `docs/handoff/D-001.md:101`. The proposal's SHA256 also matches line 99; its bytes equal the current Git diff. Exactly four hunks, +21/-16, cover the six described bullets. |
| AC-02: accepted scope and no weakened controls | PASS | Phase/stack changes preserve contract approval and dependency admission; ENV-1 restrictions are explicit. Existing exact-scope order authorization remains intact. Each changed bullet is traced below to accepted D-001; no additional authority is granted. |
| AC-03: time, Demo and holdout invariants | PASS | Time remains a server-specific offset measurement with AC-04 UNKNOWN. The execution-scope fields and fail-closed rule match architecture 7.1; the holdout restriction now covers the whole research host under 6.1. |
| AC-04: all other AGENTS content unchanged | PASS | An in-memory comparison removed exactly one occurrence of each of the six authorized bullets from the before/after texts and compared everything remaining. It was identical, including roles, authority, locked paths and D-006. |

## Checked, nothing found (and how)

### Artifact identity and scope

| Artifact | Observed SHA256 | Observed Git blob |
|----------|-----------------|-------------------|
| HEAD AGENTS.md (before) | `e4ae3241176a02e0d22f7ff150548aecafe4a4b00ab75963ceb5cd5d0885cfe7` | `90c2a5b3213929240737fddee45896cbf5b804fa` |
| Working-tree AGENTS.md (after) | `d5fe0d89952075438a51d6fe72570267c1e7a9ab225c91d701276f8a9acc775f` | `0764f4bf017b3ce9862a51ebc7152ba882ddc36f` |
| Proposal patch | `5c09abcac3d4c2312fdea808a6aa4db7081d7f47d231a56b206eb80352eb6420` | n/a |

All three SHA256 values and both blob IDs equal the final handoff table at
`docs/handoff/D-001.md:97`. Hashing used raw file/Git blob bytes, with no writes to the object
database. Exact diff-to-patch equality also confirms the six edits are the handed-off edits,
rather than merely edits with the same counts.

| Edit | Applied location | Accepted basis and assessment |
|------|------------------|-------------------------------|
| Phase | `AGENTS.md:14` | `DECISIONS.md:6-10,16-21,33-34`; architecture `6.1:117-126`. Acceptance changes the phase only. Code still needs an approved contract; dependencies still need admission and owner approval. Holdout cuts, research ingestion and strategy experiments remain prohibited before ENV-1. The disposable, owner-approved SPIKE package use stays separate from project admission. |
| Stack | `AGENTS.md:24` | `DECISIONS.md:11-15`; architecture `5:69-75` and `13a:294`. Adoption of the architecture is distinct from installing dependencies. No package, manifest or lockfile changes occur in this diff. |
| Demo-only invariant | `AGENTS.md:99` | `DECISIONS.md:23-30`; architecture `7.1:163-194`. The new pre-send check adds terminal/server/account/action/symbol/expiry checks to Demo mode and halts on mismatch or uncertainty. The existing exact-scope contract prohibition at `AGENTS.md:89`, journal/reconcile rule at line 104 and deterministic risk gate at line 106 remain unchanged. D-001 acceptance and SPIKE read-only permission therefore do not authorize an E1 order. |
| Time invariant | `AGENTS.md:110` | `docs/evidence/SPIKE-001.md:79-96`; architecture `12:274` and `13a:286`. Offset 0 is qualified by the measured server and AC-04 UNKNOWN. There is no assertion that UTC rather than broker time is the API mechanism. Raw timestamps and one time module remain required; versioned server/symbol/build rules and remeasurement for another server narrow applicability. |
| Holdout invariant | `AGENTS.md:117` | Architecture `6.1:110-126`; `DECISIONS.md:16-21`. Research-host exclusion strengthens checkout-only exclusion. The prohibitions on reading, requesting or reconstructing holdout, and automatic logging of failed experiments, remain. |
| Conventions | `AGENTS.md:146` | Accepted D-001 adopts the module map; architecture `8:196-224`. Removing the obsolete acceptance condition activates the accepted rules without authorizing scaffolding outside a task contract. |

`git diff 6495d94 -- docs/architecture.md` shows only the Proposed-to-Accepted status header.
The reviewed boundary and gate sections therefore match the revision expressly accepted in
`DECISIONS.md:8`. Their detailed requirements remain authoritative: this shorter AGENTS text
does not replace startup/reconnect checks, immutable scope, maximum volume/risk controls,
scope-bound journaling, time-evidence intervals, or the other 13a gates.

Security review considered a future coding agent interpreting the phase change as authority
to install packages, start research on the shared host, or send through another Demo account.
The admission/ENV-1/approved-scope gates reject those interpretations. Unknown identity and
expiry do not become permission. Moving holdout to a different folder on the research host
does not satisfy the changed invariant. This is a textual boundary review, not a runtime
negative test. Relevant threats are tool misuse, identity abuse, supply-chain bypass and
misleading claims of owner authorization (OWASP Agentic ASI02/03/04/09).

The handbook F01-F18 checklist was considered for this diff. No tests, dependencies, package
manager, CI, hooks, permissions implementation, secrets, production fakes or application code
changed. Roles, locked paths, D-006, the authority section, hypothesis registration, costs,
risk, order reconciliation and all other unchanged rules were covered by the remainder
comparison. An additional read-only reviewer independently checked semantic scope and found
no confirmed regression.

### Checks run

All checks below refer to HEAD `b22d75a9caea81cfd735256ca2afabd9ca043107` plus the uncommitted
AGENTS artifact identified above. Times are 2026-10-21, Asia/Bangkok (+07).
Runtime: Windows; Node.js v26.12.0; Git 2.46.1.windows.1; Git Bash 5.2.32.

| Command / procedure | Result | Commit / artifact | Time (+07) |
|---------------------|--------|-------------------|------------|
| `git status --short`, `git branch --show-current`, `git rev-parse HEAD` | PASS: requested branch; initially only AGENTS.md modified; after review only that pre-existing edit and this new report; no staged change | `b22d75a` + reviewed artifact | Reconfirmed 07:04:40 |
| Read-only `node -e` integrity/scope assertions (reproduction below) | PASS, exit 0: all hashes; exact patch/diff bytes; four hunks, +21/-16; identical remainder outside six bullets | `b22d75a` + reviewed artifact | 07:01:27 |
| `git diff --check -- AGENTS.md` | PASS, exit 0; no whitespace errors | `b22d75a` + reviewed artifact | 07:01:49 |
| `git diff 6495d94 -- docs/architecture.md` | PASS, exit 0: accepted boundary/gate text unchanged; only status header differs | `b22d75a` | 07:01:27 |
| `bash scripts/controls/red-flags.sh main` | PASS, exit 0; zero pattern groups; AGENTS.md listed as a touched control file | `b22d75a` + reviewed artifact | 07:01:28 |
| `node scripts/controls/check-locked-paths.mjs main` | **FAIL**, exit 1: one control change, AGENTS.md, needs owner label `owner-approved-control-change` | `b22d75a` + reviewed artifact | 07:01:27 |
| `node scripts/controls/test-controls.mjs` | PASS, exit 0: 105 passed, 0 failed, 0 skipped; 169.1 seconds | `b22d75a` + reviewed artifact | 07:01:26-07:04:22 (result collected) |
| Read-only `node -e` final state/report assertions; `git diff --check -- AGENTS.md` | PASS, exit 0: HEAD and AGENTS hash unchanged, index empty, only the requested report added, template headings/results present and no trailing whitespace | `b22d75a` + reviewed artifact | 07:04:40 |

The locked-path output was: `Result: FAIL: 1 control change(s) need owner approval (PR label
"owner-approved-control-change").` No approval flag, label or configuration was changed.

Tool availability: the initial `rg --files` source-discovery command was **BLOCKED** because
PowerShell reported `rg : The term 'rg' is not recognized as the name of a cmdlet, function,
script file, or operable program.` The named sources were read with Node's UTF-8 file reader
instead. This did not block any review AC; no tool was installed or configuration changed.

The scans use merge-base `3817f36` with main and include nine changed paths across ten inherited
commits. The additional decision/spec/progress/architecture/handoff/design-review paths were
already committed; they are not extra uncommitted edits in this task. Red-flag output reported
no deleted/renamed tests and no untracked files before this report was created. The report
will remain untracked as instructed, so that scan does not claim to have scanned its content.

Integrity/scope reproduction: execute the following JavaScript through `node -e` without
creating a file. It reads only the three artifacts and Git output, and performs the same
comparisons as the recorded probe; compare the printed hashes with the table above.

```javascript
const fs = require('node:fs'), cp = require('node:child_process');
const crypto = require('node:crypto'), assert = require('node:assert/strict');
const git = args => cp.execFileSync('git', args);
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const before = git(['show', 'HEAD:AGENTS.md']);
const after = fs.readFileSync('AGENTS.md');
const patch = fs.readFileSync('docs/proposals/D-001-agents-phase.patch');
const diff = git(['diff', '--no-ext-diff', '--no-color', '--', 'AGENTS.md']);
console.log(sha(before), sha(after), sha(patch));
console.log(git(['rev-parse', 'HEAD:AGENTS.md']).toString().trim());
console.log(git(['hash-object', 'AGENTS.md']).toString().trim());
assert(patch.equals(diff));
const lines = diff.toString('utf8').split('\n');
assert.equal(lines.filter(x => x.startsWith('@@ ')).length, 4);
assert.equal(lines.filter(x => x.startsWith('+') && !x.startsWith('+++')).length, 21);
assert.equal(lines.filter(x => x.startsWith('-') && !x.startsWith('---')).length, 16);
const names = ['Phase:', '(?:Proposed|Adopted) in D-001', 'Demo only\\.',
  'All time conversion', 'Every experiment run', 'Folder layout'];
function remainder(s) {
  return names.reduce((text, name, i) => {
    const re = new RegExp('^- ' + name + '[^\\n]*(?:\\n  [^\\n]*)*', 'gm');
    assert.equal([...text.matchAll(re)].length, 1, name);
    return text.replace(re, '[[AUTHORIZED EDIT ' + i + ']]');
  }, s);
}
assert.equal(remainder(before.toString('utf8')), remainder(after.toString('utf8')));
```

## Not checked (and why)

- CI, the owner-only PR label and merge: not exercised by this local pre-commit review.
  The locked-path result above is a tested failure, not an untested item.
- ENV-1 isolation/synthetic sentinel, E1 authorization and actual pre-send enforcement,
  clock health or the MT5 timestamp mechanism: no runtime implementation is under review;
  no terminal/account connection or strategy experiment was made.
- Existing SPIKE measurements were checked as documentary evidence, not rerun. Their
  single-server, short observation window and unsynchronized-machine-clock limitations remain.
- The inherited architecture revision and earlier SPIKE/control findings were not reopened.
  No mutation or break-it run was performed: the changed artifact is instruction text and the
  owner prohibited edits to control files.
- No dependency admission/installation, staging, commit or push was performed in this repository.

Only `docs/reviews/D-001-agents-r1.md` is written by this reviewer. Review evidence is local;
the AGENTS change remains uncommitted. Claude's next step is to commit the exact reviewed
artifact and this report under D-006; the owner retains the label/merge decision after CI.

Not checked in this scope: system-wide security or readiness to research/trade.
