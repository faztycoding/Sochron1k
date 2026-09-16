begin;

create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;

select plan(12);

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

select results_eq(
  $$
    select data_type || ':' || numeric_precision || ':' || numeric_scale
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'accounts'
      and column_name = 'initial_equity'
  $$,
  array['numeric:20:8']::text[],
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

select results_eq(
  'select account_ref from public.accounts order by account_ref',
  array['DEMO-A']::text[],
  'owner one reads only owner one history'
);

set local request.jwt.claim.sub = '20000000-0000-0000-0000-000000000002';

select results_eq(
  'select account_ref from public.accounts order by account_ref',
  array['DEMO-B']::text[],
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
select * from finish();
rollback;
