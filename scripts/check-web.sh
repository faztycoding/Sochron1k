#!/usr/bin/env bash
set -euo pipefail

expected_node="24.21.0"
observed_node="$(node --version)"
if [[ "$observed_node" != "v${expected_node}" ]]; then
  printf 'FAIL expected Node.js v%s, observed %s\n' "$expected_node" "$observed_node" >&2
  exit 1
fi

npm run typecheck
npm run test:web
npm run build

if rg --hidden --glob '!*.woff' --glob '!*.woff2' \
  '(SUPABASE_SERVICE_ROLE_KEY|MT5_PASSWORD|ZAI_API_KEY|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|sk_(live|test)_[A-Za-z0-9]{16,})' \
  apps/web/dist; then
  printf 'FAIL probable credential material found in the client bundle\n' >&2
  exit 1
fi

printf 'PASS responsive web console and client-bundle scan on Node.js %s\n' "$expected_node"
