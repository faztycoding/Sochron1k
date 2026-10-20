# Review BOOT-001 round 3 · posthook pre-application only

Base `main` (`951ee98`); repository head `45046b5`; reviewer: Codex, with a fresh-context,
read-only `posthook_preflight` reviewer. Date: 2026-10-19 (+07:00).

Scope: the complete proposed `docs/proposals/BOOT-001-r2-posthook.patch`, SHA256
`87c722097c1bc07383e52afa7c5fdbbf447ab7508649b0d385e2b573af3c3a0d`, based on `6066c97`.
The patch is ignored and not applied. This is a static pre-application review, not a review
of a completed F3 fix. The fresh reviewer read the contract and patch before the handoff.
The native `/review` command is unavailable here; source inspection was used instead.

**Result: F3 remains OPEN, High. Revise the proposal before owner application.**

| ID | Sev | Kind | File:line | Evidence | Trigger | Impact | Minimal fix | Proof of fix |
|----|-----|------|-----------|----------|---------|--------|-------------|--------------|
| F3 | High | confirmed, static | Patch:151; proposed `.claude/settings.json:81` | The only added event is `PostToolUse`; no `PostToolUseFailure` entry exists in the proposal or current settings. Official hook documentation distinguishes successful and failed tool execution. | A shell tool changes a protected fixture and then returns a tool error. | The post-run detector is not dispatched for that failure event, although the filesystem may have changed. A later successful command is not guaranteed. | Register the detector for executed-tool failures as well as successes; handle each event's supported response semantics. | A configuration assertion covers both events. An isolated fixture and a live failure-event check show detection after a write followed by failure, alongside successful-command coverage. |
| F3 | High | confirmed, static | Patch:98-103; proposed `.claude/hooks/check-locked-after.mjs:92-97` | State is first read after execution. Ignored local paths only establish a baseline on that first call; commit inspection requires `prev.head`. Current SessionStart does not initialize this state. | The first shell call in a session commits a protected-file change, leaving a clean tree; or changes an ignored protected fixture before the first check. | There is no pre-command state for comparison: the new commit or ignored-file content becomes the baseline without a report. | Establish the observation baseline before the first shell execution. Keep initial dirty-tree reporting and the stated limitations explicit. | A fresh-session fixture detects a protected change committed during its first command, and an ignored protected fixture changed during its first command. A clean first command remains quiet. |

Event semantics source: [Claude Code hook reference](https://code.claude.com/docs/en/hooks#posttoolusefailure),
consulted 2026-10-19. Installed-runtime dispatch was not exercised in this review.
Reproduction scenarios above are test ideas supported by the static branches, not executed tests.

## AC status

| AC | Status | Why |
|----|--------|-----|
| AC-04 | FAIL | The r2 guard defects remain unchanged. The proposed detector neither closes them nor covers the two cases above. |
| AC-06 | PASS | Existing tracked-tree red-flag scan exits 0 and reports six groups. |
| AC-07 | PASS, scanner criterion only | Both secret-pattern groups are empty in the tracked-tree scan; this is not an exhaustive secret audit of all ignored files. |
| AC-01/02/03/05/08 | UNKNOWN in this review | Live setup, trusted gate, architecture and the other original findings were outside this focused re-review. |

## Checks and evidence

| Command / inspection | Result | Revision | Time, 2026-10-19 (+07:00) |
|----------------------|--------|----------|-------------------------|
| `git status --short --branch` | Clean, ahead 2 before this review checkpoint | `45046b5` | 16:51 |
| `git apply --check docs/proposals/BOOT-001-r2-posthook.patch` | PASS applicability only; no application | `45046b5` + named proposal | 16:52 |
| `Get-FileHash -Algorithm SHA256 docs/proposals/BOOT-001-r2-posthook.patch` | PASS: matches handoff hash above | Same proposal | 16:52 |
| `bash scripts/controls/red-flags.sh main` (Git Bash absolute executable) | PASS, exit 0; six groups, secret groups empty | `45046b5` | 16:52:49 |

## Checked, nothing found (and how)

- The patch contains only the new hook and its settings registration; no dependency or existing
  test assertion is changed. Its hash matches the implementer's handoff and dry-run application passes.
- Scan hits remain policy/scanner definitions, synthetic fixtures and the existing conditional
  Bash-unavailable skip. The scan does not inspect the ignored patch itself; the patch was read separately.
- The implementation explicitly acknowledges detection after execution and inability to attribute
  owner changes to an agent. Those limits are not new findings.

## Live smoke and owner sequence

A warning about the two owner-applied dirty files can demonstrate that the runtime invokes the
hook and delivers its report. It does not prove failure-event handling, first-command coverage,
commit detection, or prevention of a write. Do not close F3 from that smoke check or the old 28 tests.

The suggested PowerShell line joins application and push with `;`, which runs the next command
even if application fails. Also, push would send only existing commits, not the uncommitted hook.
After a corrected proposal is ready, keep owner application separate from the later push of the
tested, reviewed commit. Agents retain the existing locked-path and push restrictions.

## Not checked

No patch application, execution of the proposed hook, new regression suite, live Claude dispatch,
or Linux run of this proposal. The existing Linux result at `7eae474` does not cover this hook.
No guard implementation, control setting, permission, approval label or external state was changed.

Delivery: proposal only; BOOT-001 remains implemented, F3 open High. Next: Claude revises the
posthook proposal; Codex authors regression tests in the separately authorized implementation scope;
the owner applies the resulting reviewed patch. This review does not replace review of that final diff.
