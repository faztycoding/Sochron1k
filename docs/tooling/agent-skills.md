# Sochron1k agent skills

Installed and checked on 17 September 2026: 11 upstream skills and four project-specific skills. The user authorized completing the proposed skill setup. These are development instructions and helper resources, not trading-system implementation or broker access.

## Installation and source of truth

Installed location on this workstation: `/Users/faztycoding/.codex/skills/`.

Codex should discover the new skills on the next turn. This installation check verifies files and metadata; it does not assert that the current session's already-loaded skill catalog has refreshed.

Project-specific editable sources are in `tooling/skills/`. Their installed copies match the repository sources. After a reviewed change, update the installed copy and lock record together; do not maintain divergent variants. The standard location on another workstation is `${CODEX_HOME:-$HOME/.codex}/skills`.

`skills-lock.json` records exact upstream commit IDs, source subdirectories, file counts and full-directory content digests. Upstream packages were installed using Codex's bundled skill installer with a full commit SHA. No upstream package was modified. Custom skills are version 1.0.0. A hash detects drift; it does not prove the content safe or the instructions effective.

## Installed task routing

| Skill | Publisher/source | Use in this project |
| --- | --- | --- |
| `fastapi` | [FastAPI](https://github.com/fastapi/fastapi/tree/50113da16fec53b66b80d75e80a89296de4fa5a5/fastapi/.agents/skills/fastapi) | API, Pydantic models, dependencies and async boundaries |
| `supabase` | [Supabase](https://github.com/supabase/agent-skills/tree/8331f910845103c08d51f6ca1d86ebb7d1f745e3/skills/supabase) | Auth, RLS, client integrations and schema workflow |
| `supabase-postgres-best-practices` | [Supabase](https://github.com/supabase/agent-skills/tree/8331f910845103c08d51f6ca1d86ebb7d1f745e3/skills/supabase-postgres-best-practices) | Constraints, transactions, indexes, locking and Postgres review |
| `vercel-react-best-practices` | [Vercel](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-best-practices) | React rendering and data flow; apply Vite-relevant rules |
| `frontend-design` | [Anthropic](https://github.com/anthropics/skills/tree/34040c9c568585f6929bedeaad110ad08f079624/skills/frontend-design) | Implement the blueprint's Charcoal Gold screens |
| `web-design-guidelines` | [Vercel](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278/skills/web-design-guidelines) | UI/accessibility review |
| `security-best-practices` | [OpenAI](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/security-best-practices) | Requested secure-coding/security review for Python and TypeScript |
| `security-threat-model` | [OpenAI](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/security-threat-model) | Requested repository-grounded threat modeling |
| `playwright` | [OpenAI](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/playwright) | Terminal browser investigation and screenshots |
| `gh-fix-ci` | [OpenAI](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/gh-fix-ci) | Investigate failing GitHub Actions PR checks |
| `jupyter-notebook` | [OpenAI](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/jupyter-notebook) | Reproducible research notebooks |
| `sochron-mt5-execution` | [Project source](../../tooling/skills/sochron-mt5-execution/SKILL.md) | Demo identity, MQL5, command lifecycle, fill/SL evidence |
| `sochron-risk-recovery` | [Project source](../../tooling/skills/sochron-risk-recovery/SKILL.md) | Sizing, 0.25/0.75/2% policy, journal, halts and crash tests |
| `sochron-research-validation` | [Project source](../../tooling/skills/sochron-research-validation/SKILL.md) | PA/SMC/ICT, temporal availability, costs and evaluation |
| `sochron-vps-operations` | [Project source](../../tooling/skills/sochron-vps-operations/SKILL.md) | Compose, Wine/Windows compatibility, restore and observation |

PDF, Documents, Browser and Spreadsheets are already supplied through installed plugins in this environment and were not duplicated into the user skills folder. Plugin availability is session-specific and outside this lock file.

## Scope and compatibility notes

- The project sources and user instructions govern product choices. React/Vite does not become Next.js because the React skill includes server-component examples. Keep the blueprint's theme, typography, platform, Demo-only scope and policy values.
- FastAPI upstream guidance targets current APIs; verify features against the runtime version actually pinned in the application before using them. No application dependency or runtime version was selected by this installation.
- The Playwright skill is browser automation guidance. Committed regression tests still need `@playwright/test` and the project's own scenarios. Its upstream shell wrapper dynamically resolves `@playwright/cli` through `npx`; that CLI package is not pinned by this skill lock. Before relying on terminal automation, review and pin the runtime dependency in the project or use the already available in-app Browser.
- `gh-fix-ci` needs an authenticated `gh` session for real PR inspection. `jupyter-notebook` creates notebooks but does not validate a trading strategy or install a scientific Python stack.
- Supabase and GitHub plugins were discovered previously but are not confirmed connected. They are not needed to load these skills. No database, account, cloud resource or broker connection was created by this setup.
- The community MQL5 package was not installed: its generic risk and drawdown thresholds conflict with the blueprint. The project execution/risk skills instead point to MetaQuotes APIs and the project contracts.
- Automatic selection remains enabled by default for the four new skills. They activate specifically for Sochron1k work. Skills do not launch additional agents, enforce runtime permissions, or grant account access.
- Existing user authorization is reused. Optional helper guidance must not introduce repetitive approvals for local work already authorized.

## Verification evidence

The installation operation used repository base `776859c` with pre-existing untracked baseline files preserved. The four custom skills were authored using the installed `skill-creator` workflow; its scoped descriptions, scenario review and metadata validation shaped the result.

| Check | Observed result | Limit |
| --- | --- | --- |
| Bundled `quick_validate.py` for all 15 installed skills | PASS | Frontmatter, names and unfinished scaffolding; not runtime behavior |
| Four custom `agents/openai.yaml` files | Generated using the bundled generator | UI metadata; catalog refresh occurs on a subsequent turn |
| `python3 scripts/check-agent-skills.py` | All 15 installed trees and four repository source trees match lock digests | File integrity only |
| Integrity verifier negative fixture | PASS; modified FastAPI and missing skills return failure in an isolated directory | Does not mutate installed skills |
| `bash scripts/check-project-baseline.sh` | PASS | Existing baseline checks only |
| `gh-fix-ci` and notebook helper `--help` | PASS on local Python | No GitHub authentication or notebook kernel evaluation |
| Notebook helper experiment scaffold | PASS; generated valid notebook v4 with title and unexecuted code cells in a temporary directory | Kernel and scientific calculations not executed |
| Playwright helper `bash -n` | PASS; `npx` available | CLI package/browser execution not exercised |
| Independent reasoning smoke review | Four scenarios produced decisions consistent with project contracts | Instruction-level reasoning, not executable app/broker tests |

The independent review exercised these cases:

1. Accepted entry, lost response, failed reconciliation query: preserve `UNKNOWN`, keep capacity reserved and do not replace the order. Partial fill and pending remainder occupy one logical slot.
2. Equity 99,200, day baseline 99,800, experiment baseline 100,000: daily room is 148.50; planned loss 150 plus costs 10 exceeds it. An existing total halt independently denies entry and survives restart. Oversized minimum lot is rejected.
3. Hindsight pivots, unclosed H1 bars and revised news: enforce information availability; retain same-bar SL/TP ambiguity rather than choosing a favorable outcome.
4. Healthy Compose with unreconciled Wine and an unsafe SQLite copy: keep operational readiness incomplete, obtain a consistent backup, rehearse restore and collect target-host evidence.

The review identified one wording ambiguity; the risk skill now explicitly halts **at or beyond** a limit. No material instruction gap was identified within those four scenarios. The review does not prove all future behavior.

Validation tooling used Python 3.9 with PyYAML 6.0.3 in a temporary virtual environment, without changing application dependencies. The inventory verifier uses Python's standard library only.

## Verify or update

```bash
python3 scripts/check-agent-skills.py
```

For a non-default installation location:

```bash
python3 scripts/check-agent-skills.py --skills-root /absolute/path/to/skills
```

Review a new upstream commit's instructions, executable helpers, dependencies, network destinations and compatibility before updating its installed directory and lock entry. Run affected scenario checks after custom changes. Keep old revisions available when changing instructions so recovery is possible.

To disable a skill, move only its named directory outside Codex's skills discovery directory and refresh the session; this is reversible. To restore upstream skills, use the bundled installer with the exact repository, revision and source path in the lock file. To restore custom skills, install the corresponding `tooling/skills/` directory. Do not remove the entire skills directory or unrelated packages.
