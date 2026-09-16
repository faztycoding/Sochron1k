#!/usr/bin/env bash
set -euo pipefail

expected_node="24.21.0"
observed_node="$(node --version)"
if [[ "$observed_node" != "v${expected_node}" ]]; then
  printf 'FAIL expected Node.js v%s, observed %s\n' "$expected_node" "$observed_node" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  printf 'BLOCKED a running Docker-compatible engine is required for container verification\n' >&2
  exit 2
fi

exec "${SOCHRON_PYTHON:-.venv/bin/python}" scripts/verify-compose.py
