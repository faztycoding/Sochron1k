#!/usr/bin/env bash
set -euo pipefail

python_bin="${SOCHRON_PYTHON:-.venv/bin/python}"
ruff_bin="${SOCHRON_RUFF:-.venv/bin/ruff}"
pytest_bin="${SOCHRON_PYTEST:-.venv/bin/pytest}"

if [[ ! -x "$python_bin" || ! -x "$ruff_bin" || ! -x "$pytest_bin" ]]; then
  printf 'FAIL project environment is missing; run the pinned uv sync first\n' >&2
  exit 1
fi

python_version="$($python_bin -c 'import platform; print(platform.python_version())')"
if [[ "$python_version" != 3.14.* ]]; then
  printf 'FAIL expected Python 3.14.x, observed %s\n' "$python_version" >&2
  exit 1
fi

"$ruff_bin" check services/api/src tests scripts/check-no-secrets.py
"$pytest_bin" -q
"$python_bin" scripts/check-no-secrets.py

printf 'PASS SCN-001 local safety core on Python %s\n' "$python_version"
