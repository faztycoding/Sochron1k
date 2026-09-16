#!/usr/bin/env bash
set -euo pipefail

expected_node="24.21.0"
expected_cli="2.117.0"
migration="supabase/migrations/20260916193652_create_initial_data_foundation.sql"

observed_node="$(node --version)"
if [[ "$observed_node" != "v${expected_node}" ]]; then
  printf 'FAIL expected Node.js v%s, observed %s\n' "$expected_node" "$observed_node" >&2
  exit 1
fi

observed_cli="$(npm exec supabase -- --version)"
if [[ "$observed_cli" != "$expected_cli" ]]; then
  printf 'FAIL expected Supabase CLI %s, observed %s\n' "$expected_cli" "$observed_cli" >&2
  exit 1
fi

for requirement in \
  'auto_expose_new_tables = false' \
  'enable_anonymous_sign_ins = false' \
  'minimum_password_length = 12' \
  'password_requirements = "lower_upper_letters_digits_symbols"'; do
  if ! rg --fixed-strings --quiet "$requirement" supabase/config.toml; then
    printf 'FAIL missing Supabase config guard: %s\n' "$requirement" >&2
    exit 1
  fi
done

table_count="$(rg --count '^create table public\.' "$migration")"
owner_count="$(rg --count '^  owner_id uuid not null references auth\.users \(id\),' "$migration")"
enable_rls_count="$(rg --count '^alter table public\..* enable row level security;$' "$migration")"
force_rls_count="$(rg --count '^alter table public\..* force row level security;$' "$migration")"
policy_count="$(rg --count '^create policy .*_owner_select on public\.' "$migration")"

for measured in "$table_count" "$owner_count" "$enable_rls_count" "$force_rls_count" "$policy_count"; do
  if [[ "$measured" != "17" ]]; then
    printf 'FAIL expected 17 tables, owners, RLS guards, and policies; observed %s/%s/%s/%s/%s\n' \
      "$table_count" "$owner_count" "$enable_rls_count" "$force_rls_count" "$policy_count" >&2
    exit 1
  fi
done

if rg --ignore-case --quiet \
  'security definer|for (all|insert|update|delete) to authenticated|grant .* to anon' \
  "$migration"; then
  printf 'FAIL migration introduces a forbidden privileged function or browser write path\n' >&2
  exit 1
fi

if ! rg --fixed-strings --quiet "check (account_mode = 'demo')" "$migration"; then
  printf 'FAIL account table is not constrained to Demo mode\n' >&2
  exit 1
fi

if [[ -e supabase/.temp/project-ref ]]; then
  printf 'FAIL local repository is linked to a remote Supabase project\n' >&2
  exit 1
fi

python3 scripts/check-no-secrets.py
printf 'PASS SCN-002 static Supabase guards on CLI %s and Node.js %s\n' "$expected_cli" "$expected_node"
