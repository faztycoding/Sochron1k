begin;

create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(16);

select is(
  (
    select count(*)
    from pg_class
    where relnamespace = 'public'::regnamespace
      and relkind = 'r'
      and relname = any (array[
        'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
        'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
        'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
        'audit_events'
      ])
  ),
  17::bigint,
  'SCN-002 creates every in-scope public table'
);

select is(
  (
    select count(*)
    from pg_class
    where relnamespace = 'public'::regnamespace
      and relname = any (array[
        'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
        'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
        'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
        'audit_events'
      ])
      and relrowsecurity
  ),
  17::bigint,
  'RLS is enabled on every in-scope public table'
);

select is(
  (
    select count(*)
    from pg_class
    where relnamespace = 'public'::regnamespace
      and relname = any (array[
        'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
        'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
        'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
        'audit_events'
      ])
      and relforcerowsecurity
  ),
  17::bigint,
  'RLS is forced on every in-scope public table'
);

select is(
  (
    select count(*)
    from pg_policies
    where schemaname = 'public'
      and tablename = any (array[
        'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
        'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
        'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
        'audit_events'
      ])
      and cmd = 'SELECT'
      and roles = array['authenticated']::name[]
  ),
  17::bigint,
  'each table has one authenticated select policy'
);

select is(
  (
    select count(*)
    from pg_policies
    where schemaname = 'public'
      and tablename = any (array[
        'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
        'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
        'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
        'audit_events'
      ])
      and cmd <> 'SELECT'
  ),
  0::bigint,
  'browser roles have no mutation policy'
);

select is(
  (
    select count(*)
    from unnest(array[
      'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
      'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
      'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
      'audit_events'
    ]) as table_name
    where has_table_privilege('anon', 'public.' || table_name, 'select')
  ),
  0::bigint,
  'anonymous clients have no table read grant'
);

select is(
  (
    select count(*)
    from unnest(array[
      'strategy_versions', 'accounts', 'experiments', 'bars', 'feature_snapshots',
      'signals', 'commands', 'orders', 'positions', 'deals', 'equity_snapshots',
      'account_cash_flows', 'risk_events', 'news_items', 'ai_runs', 'evaluations',
      'audit_events'
    ]) as table_name
    where has_table_privilege('authenticated', 'public.' || table_name, 'insert')
       or has_table_privilege('authenticated', 'public.' || table_name, 'update')
       or has_table_privilege('authenticated', 'public.' || table_name, 'delete')
  ),
  0::bigint,
  'authenticated clients have no direct write grant'
);

-- Compare typed JSON values: pgTAP's record/text-array comparison on this
-- Postgres image has an indeterminate collation. Keep the exact expected tuple.
select is(
  (
    select jsonb_build_array(data_type, numeric_precision, numeric_scale)
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'accounts'
      and column_name = 'initial_equity'
  ),
  '["numeric", 20, 8]'::jsonb,
  'money uses an exact numeric type'
);

select is(
  (
    select count(*)
    from pg_constraint
    where conrelid = 'public.accounts'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) like '%account_mode%demo%'
  ),
  1::bigint,
  'accounts are constrained to Demo mode'
);

insert into auth.users (id, email)
values
  ('10000000-0000-0000-0000-000000000001', 'owner-one@sochron.test'),
  ('20000000-0000-0000-0000-000000000002', 'owner-two@sochron.test');

insert into public.accounts (
  owner_id, account_ref, server_ref, account_mode, currency, initial_equity, policy_version
)
values
  ('10000000-0000-0000-0000-000000000001', 'DEMO-A', 'server-a', 'demo', 'USD', 1000, 'risk-v1'),
  ('20000000-0000-0000-0000-000000000002', 'DEMO-B', 'server-b', 'demo', 'USD', 2000, 'risk-v1');

set local role authenticated;
set local request.jwt.claim.sub = '10000000-0000-0000-0000-000000000001';

select is(
  (select jsonb_agg(account_ref order by account_ref) from public.accounts),
  '["DEMO-A"]'::jsonb,
  'owner one reads only owner one history'
);

set local request.jwt.claim.sub = '20000000-0000-0000-0000-000000000002';

select is(
  (select jsonb_agg(account_ref order by account_ref) from public.accounts),
  '["DEMO-B"]'::jsonb,
  'owner two reads only owner two history'
);

select throws_ok(
  $$
    insert into public.accounts (
      owner_id, account_ref, server_ref, account_mode, currency, initial_equity, policy_version
    ) values (
      '20000000-0000-0000-0000-000000000002', 'DENIED', 'server-b', 'demo', 'USD', 2000, 'risk-v1'
    )
  $$,
  '42501',
  'permission denied for table accounts',
  'authenticated browser cannot write operational history'
);

reset role;

select lives_ok(
  $$
    insert into public.ai_runs (
      owner_id, source, source_revision, model, requested_at, cost, cost_currency,
      output_schema, state
    ) values
      ('10000000-0000-0000-0000-000000000001', 'fixture', 'v1', 'simulator',
       now(), null, null, 'v1', 'requested'),
      ('10000000-0000-0000-0000-000000000001', 'fixture', 'v1', 'simulator',
       now(), 0.01, 'USD', 'v1', 'requested')
  $$,
  'AI cost/currency accepts absent and valid paired values'
);

select throws_ok(
  $$
    insert into public.ai_runs (
      owner_id, source, source_revision, model, requested_at, cost, cost_currency,
      output_schema, state
    ) values ('10000000-0000-0000-0000-000000000001', 'fixture', 'v1', 'simulator',
              now(), 0.01, 'usd', 'v1', 'requested')
  $$,
  '23514', null, 'AI cost rejects malformed currency'
);

select throws_ok(
  $$
    insert into public.ai_runs (
      owner_id, source, source_revision, model, requested_at, cost, cost_currency,
      output_schema, state
    ) values ('10000000-0000-0000-0000-000000000001', 'fixture', 'v1', 'simulator',
              now(), 0.01, null, 'v1', 'requested')
  $$,
  '23514', null, 'AI cost requires currency when amount is present'
);

select throws_ok(
  $$
    insert into public.ai_runs (
      owner_id, source, source_revision, model, requested_at, cost, cost_currency,
      output_schema, state
    ) values ('10000000-0000-0000-0000-000000000001', 'fixture', 'v1', 'simulator',
              now(), null, 'USD', 'v1', 'requested')
  $$,
  '23514', null, 'AI currency requires cost when currency is present'
);
select * from finish();
rollback;
