-- SCN-002 AC-02 / R-011. Synthetic records only; no broker or network actions.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select plan(256);

create function pg_temp.fixture_tables() returns text[]
language sql immutable security invoker as $$
  select array[
    'account_cash_flows', 'accounts', 'ai_runs', 'audit_events', 'bars',
    'commands', 'deals', 'equity_snapshots', 'evaluations', 'experiments',
    'feature_snapshots', 'news_items', 'orders', 'positions', 'risk_events',
    'signals', 'strategy_versions'
  ]::text[];
$$;

-- A new public table must not silently escape this access-control suite.
select is(
  (select jsonb_agg(tablename order by tablename) from pg_tables where schemaname = 'public'),
  to_jsonb(pg_temp.fixture_tables()),
  'fixture inventory covers every public application table'
);

insert into auth.users (id, email) values
  ('10000000-0000-0000-0000-000000000001', 'table-owner-a@sochron.test'),
  ('20000000-0000-0000-0000-000000000002', 'table-owner-b@sochron.test'),
  ('30000000-0000-0000-0000-000000000003', 'empty-owner@sochron.test');

do $$
declare
  fixture_owner uuid;
  strategy_ref bigint;
  account_ref bigint;
  experiment_ref bigint;
  signal_ref bigint;
  command_ref bigint;
  order_ref bigint;
  position_ref bigint;
begin
  foreach fixture_owner in array array[
    '10000000-0000-0000-0000-000000000001'::uuid,
    '20000000-0000-0000-0000-000000000002'::uuid
  ] loop
    insert into public.strategy_versions
      (owner_id, version_id, code_hash, status, data_cutoff)
    values (fixture_owner, 'fixture-v1', repeat('a', 64), 'candidate', now())
    returning id into strategy_ref;

    insert into public.accounts
      (owner_id, account_ref, server_ref, currency, initial_equity, policy_version)
    values (fixture_owner, 'SYNTHETIC-DEMO', 'fixture-server', 'USD', 1000, 'risk-v1')
    returning id into account_ref;

    insert into public.experiments
      (owner_id, account_id, strategy_version_id, experiment_id, status, initial_equity, policy_version)
    values (fixture_owner, account_ref, strategy_ref, 'fixture-experiment', 'draft', 1000, 'risk-v1')
    returning id into experiment_ref;

    insert into public.bars
      (owner_id, feed_id, source_revision, symbol, timeframe, event_time, received_at,
       available_at, open_price, high_price, low_price, close_price)
    values (fixture_owner, 'fixture-feed', 'v1', 'XAUUSD-FIXTURE', 'M1', now(), now(),
            now(), 2000, 2001, 1999, 2000);

    insert into public.feature_snapshots
      (owner_id, strategy_version_id, snapshot_id, feed_id, symbol, timeframe,
       event_time, received_at, available_at, values, dataset_hash)
    values (fixture_owner, strategy_ref, 'fixture-snapshot', 'fixture-feed',
            'XAUUSD-FIXTURE', 'M1', now(), now(), now(), '{}', repeat('b', 64));

    insert into public.signals
      (owner_id, experiment_id, strategy_version_id, signal_id, setup_id, action,
       formed_at, confirmed_at, expires_at)
    values (fixture_owner, experiment_ref, strategy_ref, 'fixture-signal', 'fixture-setup',
            'wait', now(), now(), now() + interval '1 hour')
    returning id into signal_ref;

    insert into public.commands
      (owner_id, account_id, experiment_id, signal_id, command_id, idempotency_key,
       request_fingerprint, intent, symbol, state, created_at, received_at, updated_at)
    values (fixture_owner, account_ref, experiment_ref, signal_ref, 'fixture-command',
            'fixture-idempotency', repeat('c', 64), 'reconcile', 'XAUUSD-FIXTURE',
            'created', now(), now(), now())
    returning id into command_ref;

    insert into public.orders
      (owner_id, command_id, mt5_ticket, state, event_time, received_at)
    values (fixture_owner, command_ref, 'SYNTHETIC-ORDER', 'unknown', now(), now())
    returning id into order_ref;

    insert into public.positions
      (owner_id, account_id, experiment_id, position_id, symbol, side, volume,
       average_entry, state, opened_at, event_time, received_at, updated_at)
    values (fixture_owner, account_ref, experiment_ref, 'SYNTHETIC-POSITION',
            'XAUUSD-FIXTURE', 'buy', 0.01, 2000, 'unknown', now(), now(), now(), now())
    returning id into position_ref;

    insert into public.deals
      (owner_id, command_id, order_id, position_id, deal_id, side, volume, fill_price,
       account_currency, event_time, received_at)
    values (fixture_owner, command_ref, order_ref, position_ref, 'SYNTHETIC-DEAL',
            'buy', 0.01, 2000, 'USD', now(), now());

    insert into public.equity_snapshots
      (owner_id, account_id, equity, balance, daily_baseline, total_baseline,
       account_currency, event_time, received_at)
    values (fixture_owner, account_ref, 1000, 1000, 1000, 1000, 'USD', now(), now());

    insert into public.account_cash_flows
      (owner_id, account_id, mt5_deal_id, flow_type, amount, account_currency,
       event_time, received_at)
    values (fixture_owner, account_ref, 'SYNTHETIC-CASH-FLOW', 'adjustment', 1,
            'USD', now(), now());

    insert into public.risk_events
      (owner_id, account_id, experiment_id, event_type, reason, state_snapshot,
       actor_type, event_time, received_at)
    values (fixture_owner, account_ref, experiment_ref, 'recovery_lock', 'fixture',
            '{}', 'system', now(), now());

    insert into public.news_items
      (owner_id, source, source_item_id, revision, published_at, received_at, content_hash)
    values (fixture_owner, 'fixture', 'fixture-news', 'v1', now(), now(), repeat('d', 64));

    insert into public.ai_runs
      (owner_id, experiment_id, source, source_revision, model, requested_at, output_schema, state)
    values (fixture_owner, experiment_ref, 'fixture', 'v1', 'simulator', now(), 'v1', 'requested');

    insert into public.evaluations
      (owner_id, strategy_version_id, experiment_id, dataset_hash, split, metrics,
       cost_assumptions, data_cutoff)
    values (fixture_owner, strategy_ref, experiment_ref, repeat('e', 64), 'test', '{}', '{}', now());

    insert into public.audit_events
      (owner_id, actor_type, action, entity_type, entity_id, after_state, event_time, received_at)
    values (fixture_owner, 'system', 'fixture-created', 'fixture', 'fixture-id', '{}', now(), now());
  end loop;
end;
$$;

-- Helpers run with the caller's role, not the fixture creator's privileges.
create function pg_temp.assert_visible(expected jsonb) returns setof text
language plpgsql security invoker as $$
declare
  target text;
  actual jsonb;
begin
  foreach target in array pg_temp.fixture_tables() loop
    execute format('select coalesce(jsonb_agg(owner_id order by owner_id), ''[]''::jsonb) from public.%I', target)
      into actual;
    return next is(actual, expected, format('%s sees exact owners %s in %s', current_user, expected, target));
  end loop;
end;
$$;

create function pg_temp.assert_writes_denied() returns setof text
language plpgsql security invoker as $$
declare
  target text;
  statement text;
begin
  foreach target in array pg_temp.fixture_tables() loop
    foreach statement in array array[
      format('insert into public.%I default values', target),
      format('update public.%I set owner_id = owner_id', target),
      format('delete from public.%I', target)
    ] loop
      return next throws_ok(statement, '42501', 'permission denied for table ' || target,
                            current_user || ' denied: ' || statement);
    end loop;
  end loop;
end;
$$;

-- Prove both owners' rows exist before RLS can filter them (no empty-table passes).
select * from pg_temp.assert_visible(
  '["10000000-0000-0000-0000-000000000001", "20000000-0000-0000-0000-000000000002"]'
);

-- Access assertions (mutation-test insertion point; only within this transaction).
set local role authenticated;
set local request.jwt.claims = '{}';
set local request.jwt.claim.sub = '10000000-0000-0000-0000-000000000001';
select * from pg_temp.assert_visible('["10000000-0000-0000-0000-000000000001"]');
select * from pg_temp.assert_writes_denied();

set local request.jwt.claim.sub = '20000000-0000-0000-0000-000000000002';
select * from pg_temp.assert_visible('["20000000-0000-0000-0000-000000000002"]');
select * from pg_temp.assert_writes_denied();

set local request.jwt.claim.sub = '30000000-0000-0000-0000-000000000003';
select * from pg_temp.assert_visible('[]');

set local request.jwt.claim.sub = '';
select * from pg_temp.assert_visible('[]');

set local role anon;
select throws_ok(format('select * from public.%I', target), '42501',
                 'permission denied for table ' || target, 'anonymous read denied: ' || target)
from unnest(pg_temp.fixture_tables()) as target;
select * from pg_temp.assert_writes_denied();

reset role;
select * from finish();
rollback;
