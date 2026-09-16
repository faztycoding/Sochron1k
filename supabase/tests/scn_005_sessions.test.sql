begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select plan(14);

select ok(not has_function_privilege('anon', 'public.sochron_session_active(uuid)', 'EXECUTE'),
  'AC-03 anon cannot call the session wrapper');
select ok(has_function_privilege('authenticated', 'public.sochron_session_active(uuid)', 'EXECUTE'),
  'AC-03 authenticated users can call the wrapper');
select ok(not has_function_privilege('anon', 'sochron_private.session_active(uuid)', 'EXECUTE'),
  'AC-03 anon cannot call the private lookup');
select ok(not has_schema_privilege('anon', 'sochron_private', 'USAGE'),
  'AC-03 anon cannot use the private schema');
select ok(not has_table_privilege('authenticated', 'auth.sessions', 'SELECT'),
  'AC-03 no direct browser session-table access');
select ok(not (select prosecdef from pg_proc
  where oid = 'public.sochron_session_active(uuid)'::regprocedure),
  'AC-03 public wrapper is security invoker');
select ok((select prosecdef and proconfig = array['search_path=""'] from pg_proc
  where oid = 'sochron_private.session_active(uuid)'::regprocedure),
  'AC-03 private lookup is definer with empty search path');

insert into auth.users(id) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'), ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
insert into auth.sessions(id, user_id, not_after) values
  ('11111111-1111-4111-8111-111111111111', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', null),
  ('22222222-2222-4222-8222-222222222222', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', null),
  ('33333333-3333-4333-8333-333333333333', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', now() - interval '1 second'),
  ('44444444-4444-4444-8444-444444444444', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', now() + interval '1 hour');
set local role authenticated;
set local request.jwt.claim.sub = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
select ok(public.sochron_session_active('11111111-1111-4111-8111-111111111111'),
  'AC-02 own unbounded session is active');
select ok(not public.sochron_session_active('22222222-2222-4222-8222-222222222222'),
  'AC-02 other user session is hidden');
select ok(not public.sochron_session_active('33333333-3333-4333-8333-333333333333'),
  'AC-02 expired not_after denied');
select ok(public.sochron_session_active('44444444-4444-4444-8444-444444444444'),
  'AC-02 future not_after accepted');
select ok(not public.sochron_session_active('55555555-5555-4555-8555-555555555555'),
  'AC-02 absent session denied');
set local request.jwt.claim.sub = '';
select ok(not public.sochron_session_active('11111111-1111-4111-8111-111111111111'),
  'AC-02 missing user identity denied');
reset role;
delete from auth.sessions where id = '11111111-1111-4111-8111-111111111111';
set local role authenticated;
set local request.jwt.claim.sub = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
select ok(not public.sochron_session_active('11111111-1111-4111-8111-111111111111'),
  'AC-02 revoked session denied');
reset role;
select * from finish();
rollback;
