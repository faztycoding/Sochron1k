-- SCN-020 AC-01..08. Synthetic fixtures; every change rolls back.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select no_plan();

create function pg_temp.pa01_values(
  decision_id text default 'decision-pa01-0001',
  action text default 'wait',
  reason_code text default 'INSUFFICIENT_WARMUP',
  blocked_reason text default null
) returns jsonb language sql immutable security invoker as $$
  select jsonb_build_object(
    'schema','sochron.pa01.features.v1',
    'decision_id',decision_id,
    'strategy_version','PA01-v1',
    'code_hash',repeat('1',64),
    'parameter_version','PA01-v1.0.1',
    'parameter_hash','62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822',
    'aggregation_version','native-pa01-aggregation-v1',
    'aggregation_hash',repeat('b',64),
    'source_dataset_hash',repeat('c',64),
    'dataset_hash',repeat('a',64),
    'data_cutoff_utc','2026-09-19T00:05:02Z',
    'ai_enabled',false,
    'action',action,
    'reason_code',reason_code,
    'blocked_reason',blocked_reason,
    'features',jsonb_build_object(
      'structure','incomplete',
      'ema20',null,
      'ema50',null,
      'previous_ema20',null,
      'atr14',null,
      'adx14',null,
      'spread_cap',null,
      'proposed_stop',null,
      'stop_distance_at_close',null,
      'stop_distance_atr',null,
      'latest_swing_highs','[]'::jsonb,
      'latest_swing_lows','[]'::jsonb
    ),
    'execution_parameters',jsonb_build_object(
      'next_tick_entry_required',true,
      'max_entry_drift_atr','0.20',
      'stop_buffer_atr','0.20',
      'stop_min_atr','0.50',
      'stop_max_atr','2.00',
      'target_r','2',
      'time_exit_m5_bars',12,
      'signal_expiry_seconds',30,
      'order_created',false,
      'risk_admitted',false
    )
  );
$$;

create function pg_temp.pa01_decision(
  fingerprint text default repeat('d',64),
  snapshot_id text default 'snapshot-pa01-0001',
  signal_id text default 'decision-pa01-0001',
  action text default 'wait',
  reason_code text default 'INSUFFICIENT_WARMUP',
  blocked_reason text default null
) returns jsonb language sql immutable security invoker as $$
  select jsonb_build_object(
    'protocol','sochron.pa01.decision.v1',
    'producer_revision','PA01-v1.0.1/native-pa01-aggregation-v1',
    'decision_fingerprint',fingerprint,
    'snapshot',jsonb_build_object(
      'snapshot_id',snapshot_id,
      'feed_id','mt5-copyrates:80000000-0000-4000-8000-000000000001',
      'symbol','XAUUSD.fixture',
      'timeframe','M5',
      'event_time','2026-09-19T00:05:00Z',
      'received_at','2026-09-19T00:05:02Z',
      'available_at','2026-09-19T00:05:02Z',
      'dataset_hash',repeat('a',64),
      'values',pg_temp.pa01_values(signal_id,action,reason_code,blocked_reason)
    ),
    'signal',jsonb_build_object(
      'signal_id',signal_id,
      'setup_id','setup-pa01-0001',
      'action',action,
      'formed_at','2026-09-19T00:05:00Z',
      'confirmed_at','2026-09-19T00:05:02Z',
      'expires_at','2026-09-19T00:05:32Z',
      'evidence_ids',jsonb_build_array('native-m5:evidence-1','native-h1:evidence-2'),
      'blocked_reason',blocked_reason
    )
  );
$$;

insert into auth.users(id,email) values
  ('10000000-0000-0000-0000-000000000001','pa01-owner-a@sochron.test'),
  ('20000000-0000-0000-0000-000000000002','pa01-owner-b@sochron.test');

insert into public.accounts(
  owner_id,account_ref,server_ref,currency,initial_equity,policy_version
) values
  ('10000000-0000-0000-0000-000000000001','pa01-account-a','Synthetic-Demo','USD',10000,'risk-v1'),
  ('20000000-0000-0000-0000-000000000002','pa01-account-b','Synthetic-Demo','USD',10000,'risk-v1');

insert into public.strategy_versions(
  owner_id,version_id,code_hash,parameters,status,data_cutoff
) values
  ('10000000-0000-0000-0000-000000000001','PA01-v1',repeat('1',64),
    jsonb_build_object(
      'parameter_version','PA01-v1.0.1',
      'parameter_hash','62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822',
      'aggregation_version','native-pa01-aggregation-v1'
    ),'active','2026-01-01T00:00:00Z'),
  ('20000000-0000-0000-0000-000000000002','PA01-v1',repeat('2',64),
    jsonb_build_object(
      'parameter_version','PA01-v1.0.1',
      'parameter_hash','62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822',
      'aggregation_version','native-pa01-aggregation-v1'
    ),'active','2026-01-01T00:00:00Z');

insert into public.experiments(
  owner_id,account_id,strategy_version_id,experiment_id,status,initial_equity,policy_version
) select account.owner_id,account.id,strategy.id,'pa01-experiment-' || right(account.owner_id::text,1),
    'demo',10000,'risk-v1'
  from public.accounts account
  join public.strategy_versions strategy on strategy.owner_id=account.owner_id;

select ok((select relrowsecurity and relforcerowsecurity from pg_class
  where oid='public.feature_snapshots'::regclass),'feature snapshots retain forced RLS');
select ok((select relrowsecurity and relforcerowsecurity from pg_class
  where oid='public.signals'::regclass),'signals retain forced RLS');
select is((select count(*) from pg_constraint where conname='signals_owner_feature_snapshot_fkey'),
  1::bigint,'owner-safe snapshot foreign key exists');
select is((select count(*) from pg_index where indexrelid in (
  'public.feature_snapshots_owner_decision_fingerprint_key'::regclass,
  'public.signals_owner_decision_fingerprint_key'::regclass,
  'public.signals_owner_feature_snapshot_key'::regclass
  ) and indisunique),3::bigint,'decision and one-to-one evidence indexes are unique');
select ok(not has_function_privilege('anon','public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)','execute'),
  'anonymous cannot call the decision receiver');
select ok(not has_function_privilege('authenticated','public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)','execute'),
  'browser cannot call the decision receiver');
select ok(not has_function_privilege('authenticated','public.sochron_read_pa01_decision(uuid,text)','execute'),
  'browser cannot call backend reconciliation');
select is((select count(*) from pg_proc where oid in (
  'public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)'::regprocedure,
  'public.sochron_read_pa01_decision(uuid,text)'::regprocedure
  ) and not prosecdef and proconfig=array['search_path=""']),2::bigint,
  'both PA01 RPCs are invoker with empty search path');
select ok(not has_table_privilege('service_role','public.feature_snapshots','truncate,trigger'),
  'backend cannot bypass immutable snapshot triggers');
select ok(not has_table_privilege('service_role','public.signals','truncate,trigger'),
  'backend cannot bypass immutable signal triggers');

set local role service_role;
select lives_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision())',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'atomic receiver stores a valid PA01 pair');
select is((select count(*) from public.feature_snapshots where producer_revision is not null),
  1::bigint,'one producer snapshot committed');
select is((select count(*) from public.signals where producer_revision is not null),
  1::bigint,'one producer signal committed');
select ok((select signal.feature_snapshot_id=snapshot.id
  and signal.owner_id=snapshot.owner_id
  and signal.producer_revision=snapshot.producer_revision
  and signal.decision_fingerprint=snapshot.decision_fingerprint
  from public.signals signal join public.feature_snapshots snapshot
    on snapshot.owner_id=signal.owner_id and snapshot.id=signal.feature_snapshot_id),
  'stored signal links the exact owner snapshot and shared identity');
select is(public.sochron_read_pa01_decision(
  '10000000-0000-0000-0000-000000000001','decision-pa01-0001')->>'found','true',
  'independent reconciliation finds the committed pair');
select is(public.sochron_read_pa01_decision(
  '10000000-0000-0000-0000-000000000001','decision-pa01-0001')->'snapshot'->'values',
  pg_temp.pa01_values(),'reconciliation returns the exact stored feature payload');
select is(public.sochron_read_pa01_decision(
  '20000000-0000-0000-0000-000000000002','decision-pa01-0001')->>'found','false',
  'reconciliation cannot cross owner scope');
select lives_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision())',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'exact replay is idempotent');
select is((select count(*) from public.feature_snapshots where producer_revision is not null),
  1::bigint,'exact replay creates no snapshot duplicate');
select is((select count(*) from public.signals where producer_revision is not null),
  1::bigint,'exact replay creates no signal duplicate');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(),''{snapshot,values,reason_code}'',''"TREND_FILTER"''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23505','PA01_DECISION_CONFLICT','changed replay conflicts by name');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-pa01-rollback'',''decision-pa01-0001''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23505','PA01_DECISION_CONFLICT','signal conflict rolls back an earlier snapshot insert');
select is((select count(*) from public.feature_snapshots where snapshot_id='snapshot-pa01-rollback'),
  0::bigint,'atomic conflict leaves no orphan snapshot');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(),''{unknown}'',''true''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'22023','PA01_DECISION_INVALID','unknown top-level field is rejected');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(),''{signal,confirmed_at}'',''"2026-09-19T07:05:02+07:00"''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'22023','PA01_DECISION_INVALID','non-UTC timestamp representation is rejected');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(repeat(''e'',64),''snapshot-bad-features'',''decision-bad-features''),''{snapshot,values,features,structure}'',''"unknown"''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_FEATURES_INVALID','malformed feature structure is rejected');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(repeat(''e'',64),''snapshot-bad-execution'',''decision-bad-execution''),''{snapshot,values,execution_parameters,risk_admitted}'',''true''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_EXECUTION_PARAMETERS_INVALID','risk admission cannot be smuggled in feature evidence');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(repeat(''e'',64),''snapshot-duplicate-evidence'',''decision-duplicate-evidence''),''{signal,evidence_ids}'',''["same","same"]''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_SIGNAL_INVALID','duplicate evidence identifiers are rejected');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-action-reason'',''decision-action-reason'',''buy'',''TREND_FILTER''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_SNAPSHOT_INVALID','BUY/SELL requires a confirmed setup reason');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-block-reason'',''decision-block-reason'',''block'',''MARKET_CLOSED''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_SNAPSHOT_INVALID','BLOCK requires its exact deterministic reason');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(repeat(''e'',64),''snapshot-expiry'',''decision-expiry''),''{signal,expires_at}'',''"2026-09-19T00:06:00Z"''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_SIGNAL_INVALID','signal expiry must preserve the kernel lifetime');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(repeat(''e'',64),''snapshot-code-hash'',''decision-code-hash''),''{snapshot,values,code_hash}'',to_jsonb(repeat(''0'',64))))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_STRATEGY_DENIED','feature code identity must match the admitted strategy');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(repeat(''e'',64),''snapshot-empty-evidence'',''decision-empty-evidence''),''{signal,evidence_ids}'',''[]''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_SIGNAL_INVALID','empty evidence set is rejected');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_decision(),''{snapshot,snapshot_id}'',to_jsonb(repeat(''x'',132000))))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'22023','PA01_DECISION_INVALID','oversized decision request is rejected before insertion');
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-cross-owner'',''decision-cross-owner''))',
  '20000000-0000-0000-0000-000000000002',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_STRATEGY_DENIED','mixed-owner strategy reference is rejected');

update public.experiments set status='halted'
where owner_id='10000000-0000-0000-0000-000000000001';
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-halted'',''decision-halted''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_EXPERIMENT_DENIED','halted experiment cannot receive a PA01 decision');
select is((select count(*) from public.feature_snapshots where snapshot_id='snapshot-halted'),
  0::bigint,'denied experiment leaves no partial snapshot');
update public.experiments set status='demo'
where owner_id='10000000-0000-0000-0000-000000000001';

update public.strategy_versions set status='retired'
where owner_id='10000000-0000-0000-0000-000000000001';
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-retired'',''decision-retired''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_STRATEGY_DENIED','retired strategy cannot receive a decision');
update public.strategy_versions set status='active',data_cutoff='2026-09-19T00:06:00Z'
where owner_id='10000000-0000-0000-0000-000000000001';
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-future-cutoff'',''decision-future-cutoff''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_STRATEGY_DENIED','strategy data cutoff cannot be later than decision evidence');
update public.strategy_versions set data_cutoff='2026-01-01T00:00:00Z',
  parameters=jsonb_set(parameters,'{parameter_hash}',to_jsonb(repeat('0',64)))
where owner_id='10000000-0000-0000-0000-000000000001';
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision(repeat(''e'',64),''snapshot-parameter'',''decision-parameter''))',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'23514','PA01_STRATEGY_DENIED','unmatched parameter identity is rejected');
update public.strategy_versions set parameters=jsonb_set(parameters,'{parameter_hash}',
  '"62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822"')
where owner_id='10000000-0000-0000-0000-000000000001';

select throws_ok($$update public.feature_snapshots set values=values where producer_revision is not null$$,
  '23514','PA01_SNAPSHOT_IMMUTABLE','producer snapshot cannot be updated');
select throws_ok($$delete from public.feature_snapshots where producer_revision is not null$$,
  '23514','PA01_SNAPSHOT_IMMUTABLE','producer snapshot cannot be deleted');
select throws_ok($$update public.signals set action=action where producer_revision is not null$$,
  '23514','PA01_SIGNAL_IMMUTABLE','producer signal cannot be updated');
select throws_ok($$delete from public.signals where producer_revision is not null$$,
  '23514','PA01_SIGNAL_IMMUTABLE','producer signal cannot be deleted');

insert into public.feature_snapshots(
  owner_id,strategy_version_id,snapshot_id,feed_id,symbol,timeframe,event_time,
  received_at,available_at,values,dataset_hash
) select '10000000-0000-0000-0000-000000000001',id,'legacy-snapshot','legacy-feed',
    'XAUUSD.fixture','M5','2026-09-18T00:00:00Z','2026-09-18T00:00:00Z',
    '2026-09-18T00:00:00Z','{}',repeat('f',64)
  from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001';
insert into public.signals(
  owner_id,experiment_id,strategy_version_id,signal_id,setup_id,action,formed_at,
  confirmed_at,expires_at,evidence_ids
) select experiment.owner_id,experiment.id,experiment.strategy_version_id,'legacy-signal',
    'legacy-setup','wait','2026-09-18T00:00:00Z','2026-09-18T00:00:00Z',
    '2026-09-18T00:01:00Z','[]'
  from public.experiments experiment
  where experiment.owner_id='10000000-0000-0000-0000-000000000001';
select lives_ok($$update public.feature_snapshots set feed_id='legacy-feed-updated'
  where snapshot_id='legacy-snapshot'$$,'legacy snapshots remain mutable');
select lives_ok($$update public.signals set setup_id='legacy-setup-updated'
  where signal_id='legacy-signal'$$,'legacy signals remain mutable');
select lives_ok($$delete from public.signals where signal_id='legacy-signal'$$,
  'legacy signals remain deletable');
select lives_ok($$delete from public.feature_snapshots where snapshot_id='legacy-snapshot'$$,
  'legacy snapshots remain deletable');

select is((select count(*) from public.commands),0::bigint,'receiver creates no command');
select is((select count(*) from public.risk_events),0::bigint,'receiver changes no risk or halt state');

reset role;
set local role authenticated;
set local request.jwt.claim.sub = '10000000-0000-0000-0000-000000000001';
select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_decision())',
  '10000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id='10000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id='10000000-0000-0000-0000-000000000001')
),'42501',null,'authenticated browser cannot invoke backend receiver');
select throws_ok($$insert into public.signals(
  owner_id,experiment_id,strategy_version_id,signal_id,setup_id,action,formed_at,
  confirmed_at,expires_at,evidence_ids
) values ('10000000-0000-0000-0000-000000000001',1,1,'browser-write','browser-write',
  'wait',now(),now(),now()+interval '1 minute','[]')$$,'42501',null,
  'authenticated browser cannot write signals directly');

reset role;
select * from finish();
rollback;
