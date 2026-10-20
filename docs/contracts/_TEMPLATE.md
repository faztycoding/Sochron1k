# TASK <ID> — <title>

Version v1 · Owner <owner> · Parent <SPEC journey / epic> · Tier <Lite|Standard|High> · Branch `<type>/<ID>-<slug>`
Status: draft | approved by owner <YYYY-MM-DD> | done | cancelled
Hypothesis (research tasks): H<nnn> (committed <sha>)

## Risk tier (Q1–Q6, one line each; unsure = yes)
- Q1 auth/permissions/isolation:
- Q2 real money:
- Q3 new storage/transfer of personal or confidential data:
- Q4 schema change or deletion of real data:
- Q5 hard-to-reverse external effect (orders, messages, publishing):
- Q6 changes controls (CI, hooks, permissions, policy):

## Goal / user outcome (Thai)

## Current behavior and evidence (revision)

## Scope
- In scope:
- Exclusions:
- Allowed files/modules:
- Must not touch:

## Inputs / outputs / errors (contract)

## Invariants

## Negative cases
<!-- pick what applies: duplicate command · broker timeout / UNKNOWN · stale price · non-Demo account ·
     empty or malformed data · DST/session boundary · restart mid-operation · limit exactly at boundary -->

## Acceptance (Given–When–Then, Thai; ≤ 7)
- AC-01 Given <state> When <action> Then <observable result>
- AC-02 ...

## Verification per AC
| AC | Verifier (test author / CI / owner demo) | Command or procedure | Evidence level |
|----|------------------------------------------|----------------------|----------------|

## Risk, data and external side effects

## Plan, dependencies and unknowns (P06)
1. Understanding (3 lines) and likely misunderstandings:
2. Files to touch / what is reused:
3. Steps, each with its check:
4. Risks and negative cases to test:
5. Decisions needed from the owner (or "none"):

## Authorization (filled by the owner)
actor / action / target / valid until

## Budget
time / attempts without new evidence (default 3) / tool and model cost / retry limit

## Recovery, compensation and checkpoint

## DoR status / missing items / next action

## Done scope
implementation | release | operation
