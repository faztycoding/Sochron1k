-- SCN-008 AC-01/02. Synthetic fixtures; every change rolls back.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select no_plan();

create function pg_temp.native_binding() returns jsonb language sql immutable security invoker as $$
  select '{"identity":{"executor_id":"fixture-executor","account_ref":"fixture-account","server":"Synthetic-Demo",
    "currency":"USD","margin_mode":"retail_hedging","symbol":"XAUUSD.fixture"},"offset":0,
    "chart":{"offset_valid_from_server_s":1700000000,"offset_valid_until_server_s":2000000000}}'::jsonb;
$$;
create function pg_temp.native_row(start_s bigint default 1789516800) returns jsonb language sql immutable security invoker as $$
  select jsonb_build_object('available_at','2026-09-16T00:02:00Z','bar',jsonb_build_object(
    'time_server_s',start_s,'open_time_utc',to_char(to_timestamp(start_s) at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    'closed',true,'open','9999999999999.1234567890','high','9999999999999.1234567890',
    'low','9999999999999.1234567890','close','9999999999999.1234567890',
    'tick_volume',9007199254740991,'spread_points',20,'confirmed_by_server_s',start_s+60,
    'first_receipt',7,'first_received_at','2026-09-16T00:01:01.000002Z',
    'source_observed_at','2026-09-16T00:01:01.000001Z','terminal_build',5430,
    'price_basis','bid','digits',10,'tick_size','0.0000000001','broker_utc_offset_seconds',0));
$$;
create function pg_temp.native_send(rows jsonb, binding jsonb default pg_temp.native_binding(),
  owner_id uuid default '10000000-0000-0000-0000-000000000001',
  archive_id uuid default '80000000-0000-4000-8000-000000000001') returns jsonb
language sql security invoker as $$
  select public.sochron_store_native_m1(owner_id,archive_id,binding,rows);
$$;

insert into auth.users(id,email) values
  ('10000000-0000-0000-0000-000000000001','native-owner-a@sochron.test'),
  ('20000000-0000-0000-0000-000000000002','native-owner-b@sochron.test');

select ok((select relrowsecurity and relforcerowsecurity from pg_class
  where oid='public.native_bar_archives'::regclass),'native archives enable and force RLS');
select is((select count(*) from pg_policies where schemaname='public' and tablename='native_bar_archives'
  and cmd='SELECT' and roles=array['authenticated']::name[]),1::bigint,'owner-only archive SELECT policy');
select ok(not has_table_privilege('anon','public.native_bar_archives','select'),'anonymous has no archive grant');
select ok(not has_table_privilege('authenticated','public.native_bar_archives','insert,update,delete'),'browser has no archive writes');
select ok(not has_table_privilege('service_role','public.native_bar_archives','update,delete,truncate,trigger,maintain,references'),
  'backend archive privileges are restricted to select and insert');
select ok(not has_table_privilege('service_role','public.bars','truncate,trigger'),
  'backend cannot bypass native bar evidence guards');
select ok(not has_function_privilege('anon','public.sochron_store_native_m1(uuid,uuid,jsonb,jsonb)','execute'),'anonymous cannot call receiver');
select ok(not has_function_privilege('authenticated','public.sochron_store_native_m1(uuid,uuid,jsonb,jsonb)','execute'),'browser cannot call receiver');
select ok(not has_function_privilege('authenticated','public.sochron_read_native_m1(uuid,uuid,bigint[])','execute'),'browser cannot call worker reconciliation');
select is((select count(*) from pg_proc where oid in ('public.sochron_store_native_m1(uuid,uuid,jsonb,jsonb)'::regprocedure,
  'public.sochron_read_native_m1(uuid,uuid,bigint[])'::regprocedure) and not prosecdef and proconfig=array['search_path=""']),
  2::bigint,'both RPCs are invoker with empty search_path');

set local role service_role;
select throws_ok($$truncate public.bars$$,'42501','permission denied for table bars',
  'backend cannot truncate immutable native evidence');
select throws_ok($$truncate public.native_bar_archives cascade$$,'42501',null,
  'backend cannot truncate archive bindings');
select lives_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row()))$$,'service role inserts native capture');
select is((select open_price::text from public.bars),'9999999999999.1234567890','all ten decimals survive typed storage');
select is((select tick_volume from public.bars),9007199254740991::numeric,'maximum safe native tick volume is retained');
select is((select native_payload->>'open' from public.bars),'9999999999999.1234567890','raw decimal representation survives');
select is((select received_at from public.bars),'2026-09-16T00:01:01.000002Z'::timestamptz,'microsecond capture receipt is unchanged');
select is((select available_at from public.bars),'2026-09-16T00:02:00Z'::timestamptz,'availability is later committed-source observation');
select lives_ok($$select pg_temp.native_send(jsonb_build_array(jsonb_set(pg_temp.native_row(),'{available_at}','"2026-09-16T00:03:00Z"')))$$,
  'matching replay accepts a later export observation without rewriting');
select is((select count(*) from public.bars),1::bigint,'matching replay creates no duplicate');
select is((select available_at from public.bars),'2026-09-16T00:02:00Z'::timestamptz,'first availability remains immutable');
select is(public.sochron_read_native_m1('10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000001',array[1789516800]::bigint[])->'rows'->0->'bar',
  pg_temp.native_row()->'bar','independent read returns exact native payload');
select is(public.sochron_read_native_m1('20000000-0000-0000-0000-000000000002','80000000-0000-4000-8000-000000000001',array[1789516800]::bigint[])->'rows',
  '[]'::jsonb,'reconciliation is scoped by configured owner');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(jsonb_set(pg_temp.native_row(),'{bar,first_receipt}','8')))$$,
  '23505','NATIVE_BAR_CONFLICT','changed payload replay conflicts');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row()),jsonb_set(pg_temp.native_binding(),'{identity,server}','"Other-Demo"'))$$,
  '23505','NATIVE_ARCHIVE_CONFLICT','archive identity change conflicts');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row(1789516740),jsonb_set(pg_temp.native_row(),'{bar,first_receipt}','8')))$$,
  '23505','NATIVE_BAR_CONFLICT','a later batch conflict rolls back earlier new row');
select is((select count(*) from public.bars),1::bigint,'atomic conflict left no partial bar');
select throws_ok($$update public.bars set close_price=close_price where native_archive_id is not null$$,
  '23514','NATIVE_BAR_IMMUTABLE','backend cannot update native evidence');
select throws_ok($$delete from public.bars where native_archive_id is not null$$,
  '23514','NATIVE_BAR_IMMUTABLE','backend cannot delete native evidence');

-- Each malformed request uses a fresh logical archive so conflict cannot mask validation.
select throws_ok(format($sql$select pg_temp.native_send(jsonb_build_array(jsonb_set(pg_temp.native_row(),%L::text[],%L::jsonb)),
  pg_temp.native_binding(),'10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000099')$sql$,path,value),
  '23514',null,'reject malformed capture: '||label)
from (values
  ('{bar,closed}','false','forming bar'),
  ('{bar,time_server_s}','1789516801','M1 misalignment'),
  ('{bar,confirmed_by_server_s}','1789516800','missing later closure'),
  ('{bar,confirmed_by_server_s}','1789516920','closure after observation'),
  ('{bar,first_receipt}','0','zero receipt'),
  ('{bar,tick_volume}','0','zero volume'),
  ('{bar,tick_volume}','9007199254740992','unsafe volume'),
  ('{bar,spread_points}','2147483648','spread bounds'),
  ('{bar,terminal_build}','0','unknown build'),
  ('{bar,price_basis}','"ask"','unknown price basis'),
  ('{bar,digits}','8','price exceeds digits'),
  ('{bar,broker_utc_offset_seconds}','60','offset mismatch'),
  ('{bar,open_time_utc}','"2026-09-16T00:00:01Z"','UTC mapping'),
  ('{bar,source_observed_at}','"2026-09-16T00:01:01.000003Z"','microsecond receive reversal'),
  ('{bar,source_observed_at}','"2026-09-16T07:01:01+07:00"','non-UTC provenance'),
  ('{bar,open_time_utc}','"2026-09-15T24:00:00Z"','normalized hour 24'),
  ('{bar,source_observed_at}','"2026-09-16T00:00:61Z"','normalized second 61'),
  ('{bar,open}','"NaN"','nonfinite price'),
  ('{bar,tick_size}','"0.03"','off tick grid'),
  ('{bar,open}','"9999999999999.12345678901"','silent numeric rounding'),
  ('{available_at}','"2026-09-16T00:00:00Z"','backdated availability'),
  ('{available_at}','"2099-01-01T00:00:00Z"','future availability')
) bad(path,value,label);
select is((select count(*) from public.native_bar_archives),1::bigint,'failed batches do not leave orphan archive bindings');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(jsonb_set(pg_temp.native_row(),'{bar,first_receipt}','1.5')))$$,
  '22P02',null,'fractional receipt denied by bigint input parser before insertion');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(jsonb_set(pg_temp.native_row(),'{available_at}','"2026-09-15T24:02:00Z"')))$$,
  '22023','NATIVE_BATCH_INVALID','availability cannot use normalized hour 24');

select throws_ok(format($sql$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row()),
  jsonb_set(pg_temp.native_binding(),%L::text[],%L::jsonb),
  '10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000099')$sql$,path,value),
  '23514','NATIVE_BINDING_INVALID','reject malformed binding: '||label)
from (values
  ('{identity}','null','missing identity'),
  ('{identity,currency}','"usd"','currency'),
  ('{identity,symbol}','"XAU USD"','symbol whitespace'),
  ('{identity,margin_mode}','"unknown"','margin mode'),
  ('{identity,server}','""','empty server'),
  ('{offset}','61','offset minute grid'),
  ('{offset}','50460','offset bound'),
  ('{chart,offset_valid_until_server_s}','1600000000','reversed validity')
) bad(path,value,label);

select throws_ok($$select pg_temp.native_send('[]')$$,'22023','NATIVE_BATCH_INVALID','empty batch denied');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row(),pg_temp.native_row()))$$,
  '22023','NATIVE_BATCH_INVALID','duplicate keys inside a batch denied');
select throws_ok($$select pg_temp.native_send((select jsonb_agg(pg_temp.native_row(1789516800+n*60)) from generate_series(0,100) n))$$,
  '22023','NATIVE_BATCH_INVALID','batch size bound enforced');
select throws_ok($$select public.sochron_read_native_m1('10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000001',array[]::bigint[])$$,
  '22023','NATIVE_READ_INVALID','empty reconciliation list denied');
select throws_ok($$select public.sochron_read_native_m1('10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000001',array[null]::bigint[])$$,
  '22023','NATIVE_READ_INVALID','null reconciliation key denied');
select throws_ok($$select public.sochron_read_native_m1('10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000001',array[4102444801]::bigint[])$$,
  '22023','NATIVE_READ_INVALID','out-of-range reconciliation key denied');
select lives_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row()),pg_temp.native_binding(),
  '20000000-0000-0000-0000-000000000002')$$,'second owner has nonempty native fixtures');

reset role;
select throws_ok($$update public.native_bar_archives set binding=binding$$,
  '23514','NATIVE_ARCHIVE_IMMUTABLE','even table owner cannot silently rewrite archive binding');
select throws_ok($$delete from public.native_bar_archives$$,
  '23514','NATIVE_ARCHIVE_IMMUTABLE','archive deletion requires separately reviewed maintenance');

set local role authenticated;
set local request.jwt.claim.sub = '10000000-0000-0000-0000-000000000001';
select is((select jsonb_agg(owner_id) from public.native_bar_archives),'["10000000-0000-0000-0000-000000000001"]'::jsonb,'owner A sees only archive A');
select is((select jsonb_agg(owner_id) from public.bars),'["10000000-0000-0000-0000-000000000001"]'::jsonb,'owner A sees only native bars A');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row()))$$,
  '42501','permission denied for function sochron_store_native_m1','authenticated RPC insert denied');
select throws_ok($$select public.sochron_read_native_m1('10000000-0000-0000-0000-000000000001','80000000-0000-4000-8000-000000000001',array[1789516800]::bigint[])$$,
  '42501','permission denied for function sochron_read_native_m1','browser cannot impersonate configured worker owner');
set local request.jwt.claim.sub = '20000000-0000-0000-0000-000000000002';
select is((select jsonb_agg(owner_id) from public.native_bar_archives),'["20000000-0000-0000-0000-000000000002"]'::jsonb,'owner B sees only archive B');
select is((select jsonb_agg(owner_id) from public.bars),'["20000000-0000-0000-0000-000000000002"]'::jsonb,'owner B sees only native bars B');
set local role anon;
select throws_ok($$select * from public.native_bar_archives$$,'42501','permission denied for table native_bar_archives','anonymous archive read denied');
select throws_ok($$select pg_temp.native_send(jsonb_build_array(pg_temp.native_row()))$$,
  '42501','permission denied for function sochron_store_native_m1','anonymous RPC insert denied');
reset role;

select * from finish();
rollback;
