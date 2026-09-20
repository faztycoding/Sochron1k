-- SCN-021 AC-01..08. Synthetic fixtures; every change rolls back.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select no_plan();

create function pg_temp.pa01_envelope_values(
  decision_id text default 'decision-pa01-envelope-0001',
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
    'data_cutoff_utc','2026-09-19T02:05:02Z',
    'ai_enabled',false,
    'action',action,
    'reason_code',reason_code,
    'blocked_reason',blocked_reason,
    'features',jsonb_build_object(
      'structure','incomplete','ema20',null,'ema50',null,'previous_ema20',null,
      'atr14',null,'adx14',null,'spread_cap',null,'proposed_stop',null,
      'stop_distance_at_close',null,'stop_distance_atr',null,
      'latest_swing_highs','[]'::jsonb,'latest_swing_lows','[]'::jsonb
    ),
    'execution_parameters',jsonb_build_object(
      'next_tick_entry_required',true,'max_entry_drift_atr','0.20',
      'stop_buffer_atr','0.20','stop_min_atr','0.50','stop_max_atr','2.00',
      'target_r','2','time_exit_m5_bars',12,'signal_expiry_seconds',30,
      'order_created',false,'risk_admitted',false
    )
  );
$$;

create function pg_temp.pa01_policy_context() returns jsonb
language sql immutable security invoker as $$
  select jsonb_build_object(
    'schema','sochron.pa01.policy-context.v1',
    'evidence_id','pa01-policy:' || repeat('e',32),
    'kernel_decision_id','decision-kernel-pa01-envelope-0001',
    'market_data_cutoff_utc','2026-09-19T02:05:02Z',
    'context_hash',repeat('e',64),
    'cutoff_utc','2026-09-19T02:05:02Z',
    'symbol','XAUUSD.fixture',
    'feed_id','mt5-copyrates:81000000-0000-4000-8000-000000000001',
    'spread_price','0.01',
    'market_open',true,
    'price_stale',false,
    'news_blocked',false,
    'has_exposure',false,
    'has_pending',false,
    'ai_enabled',false,
    'observations',jsonb_build_object(
      'quote',jsonb_build_object(
        'evidence_id','quote:XAUUSD.fixture:020502','observed_at_utc','2026-09-19T02:05:02Z'
      ),
      'market',jsonb_build_object(
        'evidence_id','market:XAUUSD.fixture:2026-09-19','observed_at_utc','2026-09-19T02:05:01Z'
      ),
      'news',jsonb_build_object(
        'evidence_id','news:XAUUSD.fixture:020500','observed_at_utc','2026-09-19T02:05:00Z'
      ),
      'account',jsonb_build_object(
        'evidence_id','account:demo-envelope:0001','observed_at_utc','2026-09-19T02:05:01Z'
      )
    )
  );
$$;

create function pg_temp.pa01_envelope(
  fingerprint text default repeat('d',64),
  snapshot_id text default 'snapshot-pa01-envelope-0001',
  signal_id text default 'decision-pa01-envelope-0001'
) returns jsonb language sql immutable security invoker as $$
  select jsonb_build_object(
    'protocol','sochron.pa01.decision.v2',
    'producer_revision','PA01-v1.0.1/native-pa01-aggregation-v1',
    'decision_fingerprint',fingerprint,
    'snapshot',jsonb_build_object(
      'snapshot_id',snapshot_id,
      'feed_id','mt5-copyrates:81000000-0000-4000-8000-000000000001',
      'symbol','XAUUSD.fixture','timeframe','M5',
      'event_time','2026-09-19T02:05:00Z',
      'received_at','2026-09-19T02:05:02Z',
      'available_at','2026-09-19T02:05:02Z',
      'dataset_hash',repeat('a',64),
      'values',pg_temp.pa01_envelope_values(signal_id),
      'decision_protocol','sochron.pa01.decision.v2',
      'policy_context',pg_temp.pa01_policy_context()
    ),
    'signal',jsonb_build_object(
      'signal_id',signal_id,'setup_id','setup-pa01-envelope-0001','action','wait',
      'formed_at','2026-09-19T02:05:00Z','confirmed_at','2026-09-19T02:05:02Z',
      'expires_at','2026-09-19T02:05:32Z',
      'evidence_ids',jsonb_build_array(
        'native-m5:envelope-evidence-1','pa01-policy:' || repeat('e',32)
      ),
      'blocked_reason',null
    )
  );
$$;

create function pg_temp.pa01_legacy_decision(
  fingerprint text,
  snapshot_id text,
  signal_id text
) returns jsonb language sql immutable security invoker as $$
  select jsonb_set(
    jsonb_set(
      pg_temp.pa01_envelope(fingerprint,snapshot_id,signal_id),
      '{protocol}','"sochron.pa01.decision.v1"'
    ),
    '{snapshot}',
    (pg_temp.pa01_envelope(fingerprint,snapshot_id,signal_id)->'snapshot')
      - array['decision_protocol','policy_context']
  );
$$;

insert into auth.users(id,email) values
  ('11000000-0000-0000-0000-000000000001','pa01-envelope@sochron.test');

insert into public.accounts(
  owner_id,account_ref,server_ref,currency,initial_equity,policy_version
) values (
  '11000000-0000-0000-0000-000000000001','pa01-envelope-demo','Synthetic-Demo',
  'USD',10000,'risk-v1'
);

insert into public.strategy_versions(
  owner_id,version_id,code_hash,parameters,status,data_cutoff
) values (
  '11000000-0000-0000-0000-000000000001','PA01-v1',repeat('1',64),
  jsonb_build_object(
    'parameter_version','PA01-v1.0.1',
    'parameter_hash','62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822',
    'aggregation_version','native-pa01-aggregation-v1'
  ),'active','2026-01-01T00:00:00Z'
);

insert into public.experiments(
  owner_id,account_id,strategy_version_id,experiment_id,status,initial_equity,
  policy_version
) select
  account.owner_id,account.id,strategy.id,'pa01-envelope-demo','demo',10000,
  'risk-v1'
from public.accounts account
join public.strategy_versions strategy on strategy.owner_id = account.owner_id
where account.owner_id = '11000000-0000-0000-0000-000000000001';

select has_column('public','feature_snapshots','decision_protocol',
  'snapshot records the decision protocol');
select has_column('public','feature_snapshots','policy_context',
  'snapshot records complete policy context');
select col_type_is('public','feature_snapshots','policy_context','jsonb',
  'policy context is bounded JSON evidence');
select ok(not has_function_privilege(
  'anon','public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)','execute'
), 'anonymous cannot invoke the v2-capable receiver');
select ok(not has_function_privilege(
  'authenticated','public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)','execute'
), 'browser owner cannot invoke the v2-capable receiver');

select lives_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_envelope())',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), 'protocol v2 stores one linked context-complete decision');

select is((select decision_protocol from public.feature_snapshots where snapshot_id =
  'snapshot-pa01-envelope-0001'),'sochron.pa01.decision.v2',
  'stored snapshot identifies protocol v2');
select is((select policy_context->>'context_hash' from public.feature_snapshots where snapshot_id =
  'snapshot-pa01-envelope-0001'),repeat('e',64),
  'stored snapshot preserves the exact context hash');
select is((select policy_context->'observations'->'quote'->>'evidence_id'
  from public.feature_snapshots where snapshot_id = 'snapshot-pa01-envelope-0001'),
  'quote:XAUUSD.fixture:020502','quote provenance survives storage');
select is(public.sochron_read_pa01_decision(
  '11000000-0000-0000-0000-000000000001','decision-pa01-envelope-0001'
)->>'protocol','sochron.pa01.decision.v2','independent read-back returns protocol v2');
select is(public.sochron_read_pa01_decision(
  '11000000-0000-0000-0000-000000000001','decision-pa01-envelope-0001'
)->'snapshot'->'policy_context',pg_temp.pa01_policy_context(),
  'independent read-back returns the exact policy context');

select lives_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_envelope())',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), 'exact protocol-v2 replay is idempotent');
select is((select count(*)::integer from public.feature_snapshots where owner_id =
  '11000000-0000-0000-0000-000000000001'),1,'exact replay leaves one snapshot');
select is((select count(*)::integer from public.signals where owner_id =
  '11000000-0000-0000-0000-000000000001'),1,'exact replay leaves one signal');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_envelope(),''{snapshot,policy_context,unknown}'',''true''))',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), '23514','PA01_POLICY_CONTEXT_INVALID','unknown context fields fail closed');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_envelope(repeat(''f'',64),''snapshot-pa01-future-context'',''decision-pa01-future-context''),''{snapshot,policy_context,observations,news,observed_at_utc}'',''"2026-09-19T02:05:03Z"''))',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), '23514','PA01_POLICY_CONTEXT_INVALID','future policy observations fail closed');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_envelope(repeat(''f'',64),''snapshot-pa01-duplicate-context'',''decision-pa01-duplicate-context''),''{snapshot,policy_context,observations,news,evidence_id}'',''"quote:XAUUSD.fixture:020502"''))',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), '23514','PA01_POLICY_CONTEXT_INVALID','duplicate source observations fail closed');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_envelope(repeat(''f'',64),''snapshot-pa01-stale-quote'',''decision-pa01-stale-quote''),''{snapshot,policy_context,observations,quote,observed_at_utc}'',''"2026-09-19T02:04:56Z"''))',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), '23514','PA01_POLICY_CONTEXT_INVALID',
  'a fresh-price claim rejects a quote older than five seconds');

select throws_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,jsonb_set(pg_temp.pa01_envelope(repeat(''f'',64),''snapshot-pa01-missing-policy-link'',''decision-pa01-missing-policy-link''),''{signal,evidence_ids}'',''["native-m5:envelope-evidence-1"]''))',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), '23514','PA01_POLICY_SIGNAL_INVALID',
  'signal must link its stored policy-context evidence');

select throws_ok(
  $$update public.feature_snapshots set policy_context = '{}'::jsonb
    where snapshot_id = 'snapshot-pa01-envelope-0001'$$,
  '23514','PA01_SNAPSHOT_IMMUTABLE','protocol-v2 snapshots remain immutable');
select throws_ok(
  $$delete from public.signals where signal_id = 'decision-pa01-envelope-0001'$$,
  '23514','PA01_SIGNAL_IMMUTABLE','protocol-v2 signals remain immutable');

select lives_ok(format(
  'select public.sochron_store_pa01_decision(%L,%s,%s,pg_temp.pa01_legacy_decision(repeat(''7'',64),''snapshot-pa01-envelope-v1'',''decision-pa01-envelope-v1''))',
  '11000000-0000-0000-0000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '11000000-0000-0000-0000-000000000001'),
  (select id from public.experiments where owner_id =
    '11000000-0000-0000-0000-000000000001')
), 'protocol v1 remains accepted after the forward migration');
select is(public.sochron_read_pa01_decision(
  '11000000-0000-0000-0000-000000000001','decision-pa01-envelope-v1'
)->>'protocol','sochron.pa01.decision.v1','protocol v1 read-back remains compatible');
select is((select policy_context from public.feature_snapshots where snapshot_id =
  'snapshot-pa01-envelope-v1'),null,'protocol v1 does not fabricate policy context');

select is((select count(*)::integer from public.commands where owner_id =
  '11000000-0000-0000-0000-000000000001'),0,'receiver creates no command');
select is((select count(*)::integer from public.risk_events where owner_id =
  '11000000-0000-0000-0000-000000000001'),0,'receiver creates no risk event');
select is((select count(*)::integer from public.orders where owner_id =
  '11000000-0000-0000-0000-000000000001'),0,'receiver creates no order');

select * from finish();
rollback;
