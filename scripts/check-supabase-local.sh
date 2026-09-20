#!/usr/bin/env bash
set -euo pipefail

expected_node="24.21.0"
observed_node="$(node --version)"
if [[ "$observed_node" != "v${expected_node}" ]]; then
  printf 'FAIL expected Node.js v%s, observed %s\n' "$expected_node" "$observed_node" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  printf 'BLOCKED a running Docker-compatible engine is required for Supabase database verification\n' >&2
  exit 2
fi

bash scripts/supabase-local.sh guard
if [[ "${SOCHRON_ALLOW_LOCAL_DB_RESET:-}" != sochron1k ]]; then
  printf 'BLOCKED reset destroys the disposable local sochron1k database; set SOCHRON_ALLOW_LOCAL_DB_RESET=sochron1k only for that target\n' >&2
  exit 2
fi

npm exec supabase -- db reset --local --no-seed --network-id sochron1k_supabase_local
npm exec supabase -- db lint --local --schema public,sochron_private --level warning --fail-on error --network-id sochron1k_supabase_local
npm exec supabase -- db advisors --local --type all --level info --fail-on error --network-id sochron1k_supabase_local
npm exec supabase -- test db --local supabase/tests --network-id sochron1k_supabase_local
"${SOCHRON_PYTHON:-.venv/bin/python}" scripts/check-supabase-rls-mutation.py
"${SOCHRON_PYTHON:-.venv/bin/python}" scripts/check-native-sync-concurrency.py
"${SOCHRON_PYTHON:-.venv/bin/python}" scripts/check-pa01-decision-concurrency.py

printf 'PASS local migration, lint, advisors, pgTAP, RLS mutation, native and PA01 concurrency verification on Node.js %s\n' "$expected_node"
