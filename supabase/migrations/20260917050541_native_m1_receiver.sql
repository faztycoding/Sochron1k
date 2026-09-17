-- SCN-008 AC-01/02. Generated from the local schema with CLI 2.117.0 pg-delta.
-- Explicit role revokes below also fence Supabase default privileges on replay.
SET local check_function_bodies = off;

CREATE TABLE "public"."native_bar_archives" (
  "owner_id"     uuid                     NOT NULL,
  "archive_id"   uuid                     NOT NULL,
  "account_mode" text                     NOT NULL DEFAULT 'demo'::text,
  "binding"      jsonb                    NOT NULL,
  "created_at"   timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "native_bar_archives_account_mode_check" CHECK ((account_mode = 'demo'::text)),
  CONSTRAINT "native_bar_archives_pkey" PRIMARY KEY (owner_id, archive_id)
);

ALTER TABLE "public"."native_bar_archives"
  ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."native_bar_archives"
  FORCE ROW LEVEL SECURITY;

ALTER TABLE "public"."bars"
  ADD COLUMN "native_archive_id" uuid;

ALTER TABLE "public"."bars"
  ADD COLUMN "native_time_server_s" bigint;

ALTER TABLE "public"."bars"
  ADD COLUMN "native_first_receipt" bigint;

ALTER TABLE "public"."bars"
  ADD COLUMN "native_payload" jsonb;

ALTER TABLE "public"."bars"
  ALTER COLUMN "close_price" DROP DEFAULT;

ALTER TABLE "public"."bars"
  ALTER COLUMN "close_price" TYPE numeric(24,10) USING "close_price"::numeric(24,10);

ALTER TABLE "public"."bars"
  ALTER COLUMN "high_price" DROP DEFAULT;

ALTER TABLE "public"."bars"
  ALTER COLUMN "high_price" TYPE numeric(24,10) USING "high_price"::numeric(24,10);

ALTER TABLE "public"."bars"
  ALTER COLUMN "low_price" DROP DEFAULT;

ALTER TABLE "public"."bars"
  ALTER COLUMN "low_price" TYPE numeric(24,10) USING "low_price"::numeric(24,10);

ALTER TABLE "public"."bars"
  ALTER COLUMN "open_price" DROP DEFAULT;

ALTER TABLE "public"."bars"
  ALTER COLUMN "open_price" TYPE numeric(24,10) USING "open_price"::numeric(24,10);

ALTER TABLE "public"."bars"
  ALTER COLUMN "tick_volume" DROP DEFAULT;

ALTER TABLE "public"."bars"
  ALTER COLUMN "tick_volume" TYPE numeric(28,8) USING "tick_volume"::numeric(28,8);

CREATE OR REPLACE FUNCTION public.sochron_read_native_m1 (
  p_owner_id   uuid,
  p_archive_id uuid,
  p_times      bigint[]
)
  RETURNS jsonb
  LANGUAGE plpgsql
  STABLE
  SET search_path TO ''
  AS $function$
declare
  binding jsonb;
  rows jsonb;
begin
  if p_owner_id is null or p_archive_id is null or p_times is null
     or cardinality(p_times) not between 1 and 100 or array_ndims(p_times) <> 1
     or array_position(p_times,null) is not null
     or exists (select 1 from unnest(p_times) t where t not between 1 and 4102444800) then
    raise exception using errcode = '22023', message = 'NATIVE_READ_INVALID';
  end if;
  select a.binding into binding from public.native_bar_archives a where a.owner_id = p_owner_id and a.archive_id = p_archive_id;
  select coalesce(jsonb_agg(jsonb_build_object('bar',b.native_payload,'available_at',b.available_at)
    order by b.native_time_server_s),'[]'::jsonb) into rows from public.bars b
    where b.owner_id = p_owner_id and b.native_archive_id = p_archive_id and b.native_time_server_s = any(p_times);
  return jsonb_build_object('archive_id',p_archive_id,'binding',binding,'rows',rows);
end;
$function$;

CREATE OR REPLACE FUNCTION public.sochron_store_native_m1 (
  p_owner_id   uuid,
  p_archive_id uuid,
  p_binding    jsonb,
  p_rows       jsonb
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  stored_binding jsonb;
  item jsonb;
  bar jsonb;
  stored_bar jsonb;
begin
  if p_owner_id is null or p_archive_id is null or p_binding is null or p_rows is null
     or jsonb_typeof(p_rows) <> 'array' then
    raise exception using errcode = '22023', message = 'NATIVE_BATCH_INVALID';
  end if;
  if jsonb_array_length(p_rows) not between 1 and 100 or octet_length(p_rows::text) > 262144
     or (select count(distinct (value->'bar'->>'time_server_s')::bigint) from jsonb_array_elements(p_rows)) <> jsonb_array_length(p_rows) then
    raise exception using errcode = '22023', message = 'NATIVE_BATCH_INVALID';
  end if;
  insert into public.native_bar_archives(owner_id, archive_id, binding) values(p_owner_id,p_archive_id,p_binding)
    on conflict (owner_id,archive_id) do nothing;
  select binding into stored_binding from public.native_bar_archives
    where owner_id = p_owner_id and archive_id = p_archive_id;
  if stored_binding is distinct from p_binding then
    raise exception using errcode = '23505', message = 'NATIVE_ARCHIVE_CONFLICT';
  end if;
  for item in select value from jsonb_array_elements(p_rows) order by (value->'bar'->>'time_server_s')::bigint loop
    if jsonb_typeof(item) <> 'object' or not (item ?& array['bar','available_at'])
       or item - array['bar','available_at'] <> '{}'::jsonb
       or jsonb_typeof(item->'available_at') is distinct from 'string'
       or (item->>'available_at') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$' then
      raise exception using errcode = '22023', message = 'NATIVE_BATCH_INVALID';
    end if;
    bar := item->'bar';
    insert into public.bars(owner_id,feed_id,source_revision,symbol,timeframe,event_time,received_at,available_at,
      open_price,high_price,low_price,close_price,tick_volume,native_archive_id,native_time_server_s,native_first_receipt,native_payload)
    values(p_owner_id,'mt5-copyrates:' || p_archive_id::text,'native-v1',p_binding->'identity'->>'symbol','M1',
      (bar->>'open_time_utc')::timestamptz,(bar->>'first_received_at')::timestamptz,(item->>'available_at')::timestamptz,
      (bar->>'open')::numeric,(bar->>'high')::numeric,(bar->>'low')::numeric,(bar->>'close')::numeric,
      (bar->>'tick_volume')::numeric,p_archive_id,(bar->>'time_server_s')::bigint,(bar->>'first_receipt')::bigint,bar)
    on conflict (owner_id,native_archive_id,native_time_server_s) where native_archive_id is not null do nothing;
    select native_payload into stored_bar from public.bars
      where owner_id = p_owner_id and native_archive_id = p_archive_id and native_time_server_s = (bar->>'time_server_s')::bigint;
    if stored_bar is distinct from bar then
      raise exception using errcode = '23505', message = 'NATIVE_BAR_CONFLICT';
    end if;
  end loop;
  return jsonb_build_object('archive_id',p_archive_id,'verified_count',jsonb_array_length(p_rows));
end;
$function$;

CREATE OR REPLACE FUNCTION sochron_private.guard_native_archive()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  ident jsonb;
  chart jsonb;
  key text;
  offset_s integer;
  starts bigint;
  ends bigint;
begin
  if tg_op <> 'INSERT' then
    raise exception using errcode = '23514', message = 'NATIVE_ARCHIVE_IMMUTABLE';
  end if;
  if jsonb_typeof(new.binding) is distinct from 'object' or octet_length(new.binding::text) > 4096
     or not (new.binding ?& array['identity','offset','chart'])
     or new.binding - array['identity','offset','chart'] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'NATIVE_BINDING_INVALID';
  end if;
  ident := new.binding->'identity'; chart := new.binding->'chart';
  if jsonb_typeof(ident) is distinct from 'object'
     or not (ident ?& array['executor_id','account_ref','server','currency','margin_mode','symbol'])
     or ident - array['executor_id','account_ref','server','currency','margin_mode','symbol'] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'NATIVE_BINDING_INVALID';
  end if;
  foreach key in array array['executor_id','account_ref','server','currency','margin_mode','symbol'] loop
    if jsonb_typeof(ident->key) is distinct from 'string' or length(ident->>key) not between 1 and 128
       or (ident->>key) ~ '[[:cntrl:]]' then
      raise exception using errcode = '23514', message = 'NATIVE_BINDING_INVALID';
    end if;
  end loop;
  if (ident->>'currency') !~ '^[A-Z]{3,8}$' or (ident->>'symbol') ~ '[[:space:]]'
     or length(ident->>'symbol') > 32
     or (ident->>'margin_mode') not in ('retail_netting','retail_hedging','exchange')
     or jsonb_typeof(new.binding->'offset') is distinct from 'number'
     or (new.binding->>'offset') !~ '^-?[0-9]{1,5}$'
     or jsonb_typeof(chart) is distinct from 'object'
     or not (chart ?& array['offset_valid_from_server_s','offset_valid_until_server_s'])
     or chart - array['offset_valid_from_server_s','offset_valid_until_server_s'] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'NATIVE_BINDING_INVALID';
  end if;
  foreach key in array array['offset_valid_from_server_s','offset_valid_until_server_s'] loop
    if jsonb_typeof(chart->key) is distinct from 'number' or (chart->>key) !~ '^[0-9]{1,10}$' then
      raise exception using errcode = '23514', message = 'NATIVE_BINDING_INVALID';
    end if;
  end loop;
  offset_s := (new.binding->>'offset')::integer;
  starts := (chart->>'offset_valid_from_server_s')::bigint;
  ends := (chart->>'offset_valid_until_server_s')::bigint;
  if offset_s not between -50400 and 50400 or offset_s % 60 <> 0
     or starts not between 1 and 4102444800 or ends not between 1 and 4102444800 or starts >= ends then
    raise exception using errcode = '23514', message = 'NATIVE_BINDING_INVALID';
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION sochron_private.guard_native_bar()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  payload jsonb;
  binding jsonb;
  key text;
  offset_s integer;
  raw_time bigint;
  confirmed bigint;
  observed timestamptz;
  received timestamptz;
  digits integer;
  tick numeric;
  price numeric;
begin
  if tg_op <> 'INSERT' and old.native_archive_id is not null then
    raise exception using errcode = '23514', message = 'NATIVE_BAR_IMMUTABLE';
  end if;
  if tg_op = 'DELETE' then return old; end if;
  if new.native_archive_id is null then return new; end if;
  payload := new.native_payload;
  if jsonb_typeof(payload) is distinct from 'object' or octet_length(payload::text) > 8192
     or not (payload ?& array['time_server_s','open_time_utc','closed','open','high','low','close',
        'tick_volume','spread_points','confirmed_by_server_s','first_receipt','first_received_at',
        'source_observed_at','terminal_build','price_basis','digits','tick_size','broker_utc_offset_seconds'])
     or payload - array['time_server_s','open_time_utc','closed','open','high','low','close',
        'tick_volume','spread_points','confirmed_by_server_s','first_receipt','first_received_at',
        'source_observed_at','terminal_build','price_basis','digits','tick_size','broker_utc_offset_seconds'] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
  end if;
  select a.binding into binding from public.native_bar_archives a
    where a.owner_id = new.owner_id and a.archive_id = new.native_archive_id;
  if binding is null or payload->'closed' is distinct from 'true'::jsonb
     or jsonb_typeof(payload->'price_basis') is distinct from 'string'
     or payload->>'price_basis' not in ('bid','last') then
    raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
  end if;
  foreach key in array array['time_server_s','confirmed_by_server_s','first_receipt','tick_volume','spread_points','terminal_build','digits'] loop
    if jsonb_typeof(payload->key) is distinct from 'number' or (payload->>key) !~ '^[0-9]{1,16}$'
       or (payload->>key)::numeric > 9007199254740991 then
      raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
    end if;
  end loop;
  if jsonb_typeof(payload->'broker_utc_offset_seconds') is distinct from 'number'
     or payload->'broker_utc_offset_seconds' is distinct from binding->'offset' then
    raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
  end if;
  offset_s := (binding->>'offset')::integer;
  raw_time := (payload->>'time_server_s')::bigint;
  confirmed := (payload->>'confirmed_by_server_s')::bigint;
  digits := (payload->>'digits')::integer;
  if raw_time not between 1 and 4102444800 or raw_time % 60 <> 0
     or confirmed <= raw_time or confirmed > 4102444800 or confirmed % 60 <> 0
     or raw_time < (binding->'chart'->>'offset_valid_from_server_s')::bigint
     or confirmed >= (binding->'chart'->>'offset_valid_until_server_s')::bigint
     or digits not between 0 and 10 or (payload->>'first_receipt')::bigint < 1
     or (payload->>'terminal_build')::bigint < 1 or (payload->>'tick_volume')::bigint < 1
     or (payload->>'spread_points')::bigint > 2147483647 then
    raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
  end if;
  foreach key in array array['open_time_utc','source_observed_at','first_received_at'] loop
    if jsonb_typeof(payload->key) is distinct from 'string'
       or (payload->>key) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$' then
      raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
    end if;
  end loop;
  observed := (payload->>'source_observed_at')::timestamptz;
  received := (payload->>'first_received_at')::timestamptz;
  if extract(epoch from (payload->>'open_time_utc')::timestamptz) <> raw_time - offset_s
     or extract(epoch from observed) < confirmed - offset_s or received < observed
     or new.available_at < received or new.available_at > statement_timestamp()
     or new.event_time is distinct from (payload->>'open_time_utc')::timestamptz
     or new.received_at is distinct from received
     or new.native_time_server_s is distinct from raw_time
     or new.native_first_receipt is distinct from (payload->>'first_receipt')::bigint
     or new.timeframe <> 'M1' or new.source_revision <> 'native-v1'
     or new.feed_id <> 'mt5-copyrates:' || new.native_archive_id::text
     or new.symbol is distinct from binding->'identity'->>'symbol' then
    raise exception using errcode = '23514', message = 'NATIVE_BAR_INVALID';
  end if;
  foreach key in array array['open','high','low','close','tick_size'] loop
    if jsonb_typeof(payload->key) is distinct from 'string' or length(payload->>key) > 40
       or (payload->>key) !~ '^[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]{1,2})?$' then
      raise exception using errcode = '23514', message = 'NATIVE_PRICE_INVALID';
    end if;
    price := (payload->>key)::numeric;
    if price <= 0 or price >= 100000000000000 or price <> trunc(price,10) then
      raise exception using errcode = '23514', message = 'NATIVE_PRICE_INVALID';
    end if;
  end loop;
  tick := (payload->>'tick_size')::numeric;
  foreach key in array array['open','high','low','close'] loop
    price := (payload->>key)::numeric;
    if mod(price,tick) <> 0 or price <> trunc(price,digits) then
      raise exception using errcode = '23514', message = 'NATIVE_PRICE_INVALID';
    end if;
  end loop;
  if new.open_price is distinct from (payload->>'open')::numeric
     or new.high_price is distinct from (payload->>'high')::numeric
     or new.low_price is distinct from (payload->>'low')::numeric
     or new.close_price is distinct from (payload->>'close')::numeric
     or new.tick_volume is distinct from (payload->>'tick_volume')::numeric then
    raise exception using errcode = '23514', message = 'NATIVE_PRICE_INVALID';
  end if;
  return new;
end;
$function$;

ALTER TABLE "public"."bars"
  ADD CONSTRAINT "bars_native_presence_check"
    CHECK ((((native_archive_id IS NULL) AND (native_time_server_s IS NULL) AND (native_first_receipt IS NULL) AND (native_payload IS NULL)) OR ((native_archive_id IS
    NOT NULL) AND (native_time_server_s IS NOT NULL) AND (native_first_receipt IS NOT NULL) AND (native_payload IS NOT NULL))));

ALTER TABLE "public"."native_bar_archives"
  ADD CONSTRAINT "native_bar_archives_owner_id_fkey" FOREIGN KEY (owner_id) REFERENCES auth.users(id);

ALTER TABLE "public"."bars"
  ADD CONSTRAINT "bars_native_archive_fkey" FOREIGN KEY (owner_id, native_archive_id) REFERENCES public.native_bar_archives(owner_id, archive_id);

CREATE UNIQUE INDEX bars_native_capture_key ON public.bars USING btree (owner_id, native_archive_id, native_time_server_s)
  WHERE (native_archive_id IS NOT NULL);

CREATE INDEX bars_native_receipt_idx ON public.bars USING btree (owner_id, native_archive_id, native_first_receipt, native_time_server_s)
  WHERE (native_archive_id IS NOT NULL);

CREATE TRIGGER native_bar_guard
  BEFORE INSERT OR DELETE OR UPDATE ON public.bars
  FOR EACH ROW
  EXECUTE FUNCTION sochron_private.guard_native_bar();

CREATE TRIGGER native_archive_guard
  BEFORE INSERT OR DELETE OR UPDATE ON public.native_bar_archives
  FOR EACH ROW
  EXECUTE FUNCTION sochron_private.guard_native_archive();

CREATE POLICY "native_bar_archives_owner_select" ON "public"."native_bar_archives"
  FOR SELECT
  TO "authenticated"
  USING ((( SELECT auth.uid() AS uid) = owner_id));

COMMENT ON COLUMN "public"."bars"."available_at" IS 'For native rows: first observed committed-source export time, not candle close or destination commit time.';

COMMENT ON COLUMN "public"."bars"."native_payload" IS 'Original closed M1 capture payload; decimals remain exact JSON strings. Native rows are immutable.';

COMMENT ON TABLE "public"."native_bar_archives" IS 'Immutable owner-scoped Demo native-bar capture bindings; not execution authority.';

REVOKE ALL ON FUNCTION "public"."sochron_read_native_m1"(uuid, uuid, bigint[]) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION "public"."sochron_read_native_m1"(uuid, uuid, bigint[]) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "public"."sochron_store_native_m1"(uuid, uuid, jsonb, jsonb) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION "public"."sochron_store_native_m1"(uuid, uuid, jsonb, jsonb) TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "sochron_private"."guard_native_archive"() FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION "sochron_private"."guard_native_archive"() TO "postgres", "service_role";

REVOKE ALL ON FUNCTION "sochron_private"."guard_native_bar"() FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION "sochron_private"."guard_native_bar"() TO "postgres", "service_role";

REVOKE ALL ON SCHEMA "sochron_private" FROM "service_role";

GRANT USAGE ON SCHEMA "sochron_private" TO "service_role";

REVOKE ALL ON TABLE "public"."native_bar_archives" FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT ON TABLE "public"."native_bar_archives" TO "authenticated";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."native_bar_archives" TO "postgres";

GRANT INSERT, SELECT ON TABLE "public"."native_bar_archives" TO "service_role";

-- Supabase's default table grants include TRUNCATE, which bypasses row triggers.
-- Keep generic bar CRUD but remove maintenance paths over immutable native rows.
REVOKE ALL ON TABLE public.bars FROM service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.bars TO service_role;
