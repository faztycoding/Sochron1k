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

npm exec supabase -- db reset --local --no-seed
npm exec supabase -- db lint --local --schema public --level warning --fail-on error
npm exec supabase -- db advisors --local --type all --level info --fail-on error
npm exec supabase -- test db --local supabase/tests

printf 'PASS SCN-002 local migration, lint, advisors, and pgTAP verification on Node.js %s\n' "$expected_node"
