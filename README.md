# Sochron1k

Sochron1k is a demo-only XAU/USD research and automated-trading system. Its purpose is to measure whether explicitly versioned strategies have an edge after costs while preserving execution, risk, and audit invariants.

The repository now contains the first local SCN-001 safety core: versioned execution contracts, Demo-only preflight, deterministic risk sizing, a SQLite WAL journal, an isolated executor simulator, and targeted failure-path tests. It is still a prototype and is not ready for a real MT5 Demo send or unattended operation.

## Product boundaries

- One owner and one dedicated MT5 Demo account.
- XAU/USD only for the first release.
- Responsive web application for monitoring and control.
- MT5 and the EA remain authoritative for market, order, deal, and position state.
- Python services own strategy versions, feature calculation, queues, and the API.
- Supabase stores authenticated research history and audit records after synchronization.
- AI may classify news or support offline research. It cannot authorize risk, release a halt, or change a running strategy.
- Live trading, deposits, withdrawals, copy trading, signal sales, multi-account support, and Order Flow trading are outside the first-release scope.

## Safety baseline

The current project risk tier is **High assurance**. Demo-only operation reduces financial exposure but does not remove execution, credential, data-integrity, or automation risk.

- Live-account execution is prohibited.
- Auto trading defaults to disabled.
- Risk defaults are 0.25% per trade, 0.75% daily, and 2% per experiment.
- Only one position or pending order is permitted.
- Unknown write or execution outcomes must be reconciled before retry.
- The system must stop opening positions when price, journal, executor, or risk state is not trustworthy.

## Source documents

- `Sochron1k_Complete_Blueprint (1).pdf` is the product and engineering source of truth, version 1.1 dated 16 September 2026.
- `Agentic_Software_Engineering_Handbook_v3.docx` defines the project delivery and assurance process, version 3.0 dated 16 September 2026.
- [Project profile](docs/product.md) records the adopted scope, risk tier, unknowns, and decision authority.
- [Architecture](docs/architecture.md) records system boundaries, data ownership, and failure behavior.
- [SCN-001 Task Contract](docs/contracts/SCN-001-mt5-demo-round-trip.md) defines the first vertical slice.
- [Risk register](docs/risks/risk-register.md) tracks material project risks and required evidence.
- [Agent skills](docs/tooling/agent-skills.md) records the installed skills, source revisions, task routing, and verification limits.

## Verified project command

```bash
bash scripts/check-project-baseline.sh
python3 scripts/check-agent-skills.py
bash scripts/check-scn-001-local.sh
```

Only commands that have been run successfully in this repository should be added to this section or to `AGENTS.md`.

## Local development

The candidate runtimes are pinned to Python 3.14.7 and Node.js 24.21.0 LTS. Install uv 0.12.15, then create the Python environment from the committed lockfile:

```bash
uv python install 3.14.7
uv sync --all-groups --frozen
bash scripts/check-scn-001-local.sh
```

The API health endpoint always reports Demo mode and currently reports `execution_ready=false`. No real MT5 adapter or broker credential is present.

## Current next action

Complete the remaining local SCN-001 adapter and recovery work, then prepare the MT5 EA/bridge and dry-run evidence. A real Demo round trip still requires the owner inputs and explicit target authorization listed in the task contract.
