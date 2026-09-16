# ADR-002 Pinned Runtime Toolchain

## Status

Accepted on 17 September 2026 for local implementation and reproducible builds. Deployment and broker compatibility remain separate gates.

## Context

SCN-001 requires pinned runtimes before implementation claims can be reproduced. The development workstation currently has Python 3.9.6 and Node.js 26.7.0, neither of which is the selected candidate runtime. Python 3.9 is outside the supported range of the selected FastAPI release. Node.js 26 is a Current release rather than the LTS line selected for the web build.

## Decision

- Python `3.14.7`, the current Python 3.14 maintenance release checked on 17 September 2026.
- Node.js `24.21.0`, the current Node.js 24 LTS release checked on 17 September 2026.
- npm `11.19.0` as the JavaScript package manager until the committed lockfile selects its full dependency graph.
- uv `0.12.15` for Python interpreter and dependency locking.
- FastAPI `0.141.1`, Pydantic `2.13.5`, Uvicorn `0.53.0`, and HTTPX `0.28.1` for the initial API boundary.
- pytest `9.1.1`, Hypothesis `6.168.0`, and Ruff `0.16.8` for the first local verification layer.

`.python-version`, `.node-version`, `.nvmrc`, `pyproject.toml`, `uv.lock`, `package.json`, and `package-lock.json` are the versioned runtime evidence. Containers must use the same major/minor runtime and exact patch unless a reviewed ADR supersedes this decision.

## Consequences

- Local checks that use another interpreter are development evidence only and cannot establish candidate-runtime compatibility.
- Dependency updates require a reviewed lockfile diff and affected checks.
- MT5 and MetaEditor versions cannot be selected without the target Demo environment. Their build and compatibility evidence remains blocked rather than inferred.
- This decision does not enable Auto Trading, create a live-account path, or authorize an external order.

## Fitness checks

- `python --version` inside the project environment must report Python 3.14.x.
- `node --version` in the web build must report v24.21.0.
- Python and JavaScript lockfiles must be present and unchanged during verification.
- The baseline and SCN-001 local verification scripts must run on the candidate source revision.

## Sources

- Python release page: <https://www.python.org/downloads/release/python-3147/>
- Node.js release lifecycle: <https://nodejs.org/en/about/previous-releases>
- FastAPI release notes: <https://fastapi.tiangolo.com/release-notes/>
