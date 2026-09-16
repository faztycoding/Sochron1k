#!/usr/bin/env bash
set -euo pipefail

required_files=(
  README.md
  AGENTS.md
  .env.example
  docs/product.md
  docs/architecture.md
  docs/contracts/SCN-001-mt5-demo-round-trip.md
  docs/decisions/ADR-001-demo-first-modular-boundaries.md
  docs/risks/risk-register.md
)

for path in "${required_files[@]}"; do
  if [[ ! -s "$path" ]]; then
    printf 'FAIL missing or empty required file: %s\n' "$path" >&2
    exit 1
  fi
done

required_env_names=(
  TRADING_MODE
  AUTO_TRADING_ENABLED
  MT5_ACCOUNT
  MT5_PASSWORD
  MT5_SERVER
  MT5_SYMBOL
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  ZAI_API_KEY
  RISK_PER_TRADE_PCT
  DAILY_LOSS_LIMIT_PCT
  EXPERIMENT_LOSS_LIMIT_PCT
)

for name in "${required_env_names[@]}"; do
  if ! grep -Eq "^${name}=" .env.example; then
    printf 'FAIL missing environment contract: %s\n' "$name" >&2
    exit 1
  fi
done

if ! grep -Eq '^TRADING_MODE=demo$' .env.example; then
  printf 'FAIL TRADING_MODE must default to demo\n' >&2
  exit 1
fi

if ! grep -Eq '^AUTO_TRADING_ENABLED=false$' .env.example; then
  printf 'FAIL AUTO_TRADING_ENABLED must default to false\n' >&2
  exit 1
fi

for secret_name in MT5_PASSWORD SUPABASE_SERVICE_ROLE_KEY ZAI_API_KEY; do
  if ! grep -Eq "^${secret_name}=$" .env.example; then
    printf 'FAIL secret example must remain blank: %s\n' "$secret_name" >&2
    exit 1
  fi
done

for acceptance_id in AC-01 AC-02 AC-03 AC-04 AC-05 AC-06 AC-07 AC-08; do
  if ! grep -Fq "$acceptance_id" docs/contracts/SCN-001-mt5-demo-round-trip.md; then
    printf 'FAIL missing acceptance criterion: %s\n' "$acceptance_id" >&2
    exit 1
  fi
done

if grep -Eqi '(password|secret|api[_ -]?key)[[:space:]]*=[[:space:]]*[^[:space:]#]+' .env.example; then
  printf 'FAIL probable secret value found in .env.example\n' >&2
  exit 1
fi

printf 'PASS project baseline: %s files, safe Demo defaults, blank secret examples, SCN-001 acceptance IDs present\n' "${#required_files[@]}"
