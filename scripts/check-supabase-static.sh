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

native_migration="supabase/migrations/20260917050541_native_m1_receiver.sql"
# Source tripwires only; check:db:local supplies role and concurrency evidence.
for requirement in \
  'FORCE ROW LEVEL SECURITY;' \
  'CREATE UNIQUE INDEX bars_native_capture_key' \
  'CREATE TRIGGER native_bar_guard' \
  'CREATE TRIGGER native_archive_guard' \
  'NATIVE_BAR_CONFLICT' \
  'NATIVE_ARCHIVE_CONFLICT' \
  'REVOKE ALL ON TABLE public.bars FROM service_role;' \
  'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.bars TO service_role;' \
  'GRANT INSERT, SELECT ON TABLE "public"."native_bar_archives" TO "service_role";'; do
  if ! rg --fixed-strings --quiet "$requirement" "$native_migration"; then
    printf 'FAIL missing native receiver source guard: %s\n' "$requirement" >&2
    exit 1
  fi
done
if rg --ignore-case --quiet 'security definer' "$native_migration"; then
  printf 'FAIL native receiver adds a privileged definer function\n' >&2
  exit 1
fi

pa01_migration="supabase/migrations/20260920000837_pa01_decision_receiver.sql"
# SCN-020 source tripwires; local pgTAP and independent sessions prove behavior.
for requirement in \
  'CREATE UNIQUE INDEX feature_snapshots_owner_decision_fingerprint_key' \
  'CREATE UNIQUE INDEX signals_owner_feature_snapshot_key' \
  'CREATE TRIGGER pa01_feature_snapshot_guard' \
  'CREATE TRIGGER pa01_signal_guard' \
  'PA01_DECISION_CONFLICT' \
  'PA01_SNAPSHOT_IMMUTABLE' \
  'PA01_SIGNAL_IMMUTABLE' \
  'REVOKE ALL ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)' \
  'REVOKE ALL ON TABLE public.feature_snapshots FROM service_role;' \
  'REVOKE ALL ON TABLE public.signals FROM service_role;'; do
  if ! rg --fixed-strings --quiet "$requirement" "$pa01_migration"; then
    printf 'FAIL missing PA01 receiver source guard: %s\n' "$requirement" >&2
    exit 1
  fi
done
if rg --ignore-case --quiet 'security definer|insert into public\.(commands|risk_events|orders|positions|deals)' \
  "$pa01_migration"; then
  printf 'FAIL PA01 receiver adds privileged or execution-authority behavior\n' >&2
  exit 1
fi

envelope_migration="supabase/migrations/20260920005057_pa01_policy_context_envelope.sql"
# SCN-021 source tripwires; pgTAP and independent sessions prove exact behavior.
for requirement in \
  'ADD COLUMN decision_protocol text' \
  'ADD COLUMN policy_context jsonb' \
  'CREATE TRIGGER pa01_policy_context_guard' \
  'CREATE TRIGGER pa01_policy_signal_guard' \
  'PA01_POLICY_CONTEXT_INVALID' \
  'PA01_POLICY_SIGNAL_INVALID' \
  "'sochron.pa01.decision.v1','sochron.pa01.decision.v2'" \
  'REVOKE ALL ON FUNCTION sochron_private.guard_pa01_policy_context()' \
  'REVOKE ALL ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)'; do
  if ! rg --fixed-strings --quiet "$requirement" "$envelope_migration"; then
    printf 'FAIL missing PA01 envelope source guard: %s\n' "$requirement" >&2
    exit 1
  fi
done
if rg --ignore-case --quiet 'security definer|insert into public\.(commands|risk_events|orders|positions|deals)' \
  "$envelope_migration"; then
  printf 'FAIL PA01 envelope adds privileged or execution-authority behavior\n' >&2
  exit 1
fi

research_migration="supabase/migrations/20260920044437_reproducible_research_evaluation.sql"
# SCN-029 source tripwires; pgTAP supplies strict receiver and role evidence.
for requirement in \
  'ADD COLUMN producer_revision text' \
  'ADD COLUMN evaluation_protocol text' \
  'ADD COLUMN evaluation_fingerprint text' \
  'ADD COLUMN evidence_manifest jsonb' \
  'CREATE UNIQUE INDEX evaluations_owner_producer_fingerprint_key' \
  'CREATE TRIGGER research_evaluation_guard' \
  'RESEARCH_EVALUATION_CONFLICT' \
  'RESEARCH_EVALUATION_IMMUTABLE' \
  'REVOKE ALL ON FUNCTION public.sochron_store_research_evaluation(uuid,bigint,bigint,jsonb)' \
  'REVOKE ALL ON FUNCTION public.sochron_read_research_evaluation(uuid,text)' \
  'REVOKE ALL ON TABLE public.evaluations FROM service_role;'; do
  if ! rg --fixed-strings --quiet "$requirement" "$research_migration"; then
    printf 'FAIL missing research-evaluation receiver guard: %s\n' "$requirement" >&2
    exit 1
  fi
done
if rg --ignore-case --quiet \
  'security definer|insert into public\.(commands|risk_events|orders|positions|deals)' \
  "$research_migration"; then
  printf 'FAIL research evaluation adds privileged or execution-authority behavior\n' >&2
  exit 1
fi

python3 scripts/check-no-secrets.py
printf 'PASS SCN-002/008/020/021/029 static Supabase guards on CLI %s and Node.js %s\n' \
  "$expected_cli" "$expected_node"
