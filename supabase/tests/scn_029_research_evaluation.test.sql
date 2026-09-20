-- SCN-029 AC-07..11. Synthetic fixtures; every change rolls back.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select no_plan();

create function pg_temp.research_evaluation(
  fingerprint text default repeat('f',64),
  dataset_hash text default repeat('d',64)
) returns jsonb language sql immutable security invoker as $$
  select jsonb_build_object(
    'protocol','sochron.research-evaluation-envelope.v1',
    'producer_revision','SCN-029/research-evaluation-v1.0.0',
    'evaluation_fingerprint',fingerprint,
    'dataset_hash',dataset_hash,
    'strategy_code_hash',repeat('a',64),
    'split','walk_forward',
    'data_cutoff_utc','2026-01-03T00:00:00.000000Z',
    'metrics',jsonb_build_object(
      'sample_size',3,'wins',1,'losses',1,'breakeven',1,
      'net_return_pct','1','expectancy_r','0.33333333',
      'expectancy_r_ci95_low','-0.66666667',
      'expectancy_r_ci95_high','1.33333333',
      'max_drawdown_pct','1.96078431','profit_factor','2'
    ),
    'cost_assumptions',jsonb_build_object(
      'spread_points','1','slippage_points','1','commission_per_lot','2',
      'swap_included',true,'operating_cost_per_trade','1','currency','USD'
    ),
    'evidence_manifest',jsonb_build_object(
      'manifest_protocol','sochron.research-evaluation-manifest.v1',
      'bundle_hash',dataset_hash,
      'strategy_version','PA01-v1',
      'strategy_code_hash',repeat('a',64),
      'evaluation_window',jsonb_build_object(
        'start_utc','2026-01-02T00:00:00.000000Z',
        'end_utc','2026-01-03T00:00:00.000000Z',
        'prior_development_cutoff_utc','2026-01-01T00:00:00.000000Z',
        'embargo_seconds',3600
      ),
      'bootstrap',jsonb_build_object('seed',17,'samples',1000,'block_length',2),
      'record_counts',jsonb_build_object(
        'closed_trade',3,'wait',1,'rejected',1,'counterfactual',1,'ambiguous',1
      ),
      'equity_basis','mark_to_market_including_open_exposure',
      'cost_currency','USD'
    )
  );
$$;

insert into auth.users(id,email) values
  ('29000000-0000-4000-8000-000000000001','research-owner@sochron.test'),
  ('29000000-0000-4000-8000-000000000002','research-other@sochron.test');

insert into public.accounts(
  owner_id,account_ref,server_ref,currency,initial_equity,policy_version
) values
  ('29000000-0000-4000-8000-000000000001','research-demo','Synthetic-Demo',
   'USD',1000,'risk-v1'),
  ('29000000-0000-4000-8000-000000000002','research-other','Synthetic-Demo',
   'USD',1000,'risk-v1');

insert into public.strategy_versions(
  owner_id,version_id,code_hash,parameters,status,data_cutoff
) values
  ('29000000-0000-4000-8000-000000000001','PA01-v1',repeat('a',64),'{}',
   'candidate','2026-01-01T00:00:00Z'),
  ('29000000-0000-4000-8000-000000000002','PA01-v1',repeat('a',64),'{}',
   'candidate','2026-01-01T00:00:00Z');

insert into public.experiments(
  owner_id,account_id,strategy_version_id,experiment_id,status,initial_equity,
  policy_version
) select account.owner_id,account.id,strategy.id,'research-evaluation','shadow',1000,'risk-v1'
from public.accounts account
join public.strategy_versions strategy on strategy.owner_id = account.owner_id;

select has_column('public','evaluations','producer_revision',
  'evaluation records producer revision');
select has_column('public','evaluations','evaluation_protocol',
  'evaluation records envelope protocol');
select has_column('public','evaluations','evaluation_fingerprint',
  'evaluation records exact reconciliation identity');
select has_column('public','evaluations','evidence_manifest',
  'evaluation records bounded provenance');
select ok(not has_function_privilege(
  'anon','public.sochron_store_research_evaluation(uuid,bigint,bigint,jsonb)','execute'
), 'anonymous cannot invoke the evaluation receiver');
select ok(not has_function_privilege(
  'authenticated','public.sochron_store_research_evaluation(uuid,bigint,bigint,jsonb)','execute'
), 'browser owner cannot invoke the evaluation receiver');

select lives_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,pg_temp.research_evaluation())',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), 'strict producer evaluation is stored');
select is((select count(*) from public.evaluations where producer_revision is not null),
  1::bigint,'receiver stores one producer row');
select is((select evidence_manifest->'record_counts'->>'ambiguous'
  from public.evaluations where producer_revision is not null),'1',
  'excluded ambiguous evidence remains explicit');
select is(public.sochron_read_research_evaluation(
  '29000000-0000-4000-8000-000000000001',repeat('f',64)
)->'evaluation',pg_temp.research_evaluation(),'read-back returns the exact envelope');
select is(public.sochron_read_research_evaluation(
  '29000000-0000-4000-8000-000000000002',repeat('f',64)
)->>'found','false','read-back cannot cross owner scope');

select lives_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,pg_temp.research_evaluation())',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), 'exact replay is idempotent');
select is((select count(*) from public.evaluations where producer_revision is not null),
  1::bigint,'exact replay creates no duplicate');

select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,jsonb_set(pg_temp.research_evaluation(),''{unknown}'',''true''))',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '22023','RESEARCH_EVALUATION_INVALID','unknown envelope fields fail closed');
select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,jsonb_set(pg_temp.research_evaluation(),''{metrics,sample_size}'',''4''))',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '23514','RESEARCH_EVALUATION_INVALID','inconsistent outcome counts fail closed');
select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,jsonb_set(pg_temp.research_evaluation(),''{strategy_code_hash}'',to_jsonb(repeat(''b'',64))))',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '22023','RESEARCH_EVALUATION_INVALID','mismatched duplicate code identity fails early');
select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,jsonb_set(jsonb_set(pg_temp.research_evaluation(repeat(''e'',64),repeat(''e'',64)),''{strategy_code_hash}'',to_jsonb(repeat(''b'',64))),''{evidence_manifest,strategy_code_hash}'',to_jsonb(repeat(''b'',64))))',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '23514','RESEARCH_EVALUATION_STRATEGY_DENIED',
  'unregistered strategy code identity is denied');
select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,pg_temp.research_evaluation(repeat(''e'',64)))',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '23505','RESEARCH_EVALUATION_CONFLICT',
  'same source identity with a different fingerprint conflicts');
select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,jsonb_set(pg_temp.research_evaluation(),''{metrics,expectancy_r}'',''"0.5"''))',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '23505','RESEARCH_EVALUATION_CONFLICT',
  'same fingerprint with a different body conflicts');

select throws_ok($$update public.evaluations set metrics=metrics
  where producer_revision is not null$$,'23514','RESEARCH_EVALUATION_IMMUTABLE',
  'producer evaluation cannot be updated');
select throws_ok($$delete from public.evaluations where producer_revision is not null$$,
  '23514','RESEARCH_EVALUATION_IMMUTABLE','producer evaluation cannot be deleted');

insert into public.evaluations(
  owner_id,strategy_version_id,dataset_hash,split,metrics,cost_assumptions,data_cutoff
) select owner_id,id,repeat('9',64),'train','{}','{}','2026-01-01T00:00:00Z'
  from public.strategy_versions where owner_id='29000000-0000-4000-8000-000000000001';
select lives_ok($$update public.evaluations set metrics='{"legacy":true}'
  where producer_revision is null$$,'legacy evaluation remains mutable');
select lives_ok($$delete from public.evaluations where producer_revision is null$$,
  'legacy evaluation remains deletable');

select is((select count(*) from public.commands),0::bigint,'receiver creates no command');
select is((select count(*) from public.risk_events),0::bigint,
  'receiver changes no risk or halt state');

set local role authenticated;
set local request.jwt.claim.sub = '29000000-0000-4000-8000-000000000001';
select is((select count(*) from public.evaluations),1::bigint,
  'owner RLS exposes only the owner evaluation');
select throws_ok(format(
  'select public.sochron_store_research_evaluation(%L,%s,%s,pg_temp.research_evaluation())',
  '29000000-0000-4000-8000-000000000001',
  (select id from public.strategy_versions where owner_id =
    '29000000-0000-4000-8000-000000000001'),
  (select id from public.experiments where owner_id =
    '29000000-0000-4000-8000-000000000001')
), '42501',null,'authenticated browser cannot invoke backend receiver');
select throws_ok($$insert into public.evaluations(
  owner_id,strategy_version_id,dataset_hash,split,metrics,cost_assumptions,data_cutoff
) values ('29000000-0000-4000-8000-000000000001',1,repeat('8',64),'train','{}','{}',now())$$,
  '42501',null,'authenticated browser cannot write evaluations directly');

reset role;
select * from finish();
rollback;
