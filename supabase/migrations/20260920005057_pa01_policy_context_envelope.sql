-- SCN-021: preserve the complete policy context used by a PA01 decision.
-- Existing protocol-v1 rows remain unchanged and readable. This migration grants
-- no command, risk, order, broker or Auto Trading authority.
SET local check_function_bodies = off;

ALTER TABLE public.feature_snapshots
  ADD COLUMN decision_protocol text,
  ADD COLUMN policy_context jsonb,
  ADD CONSTRAINT feature_snapshots_policy_context_presence_check CHECK (
    (
      producer_revision IS NULL
      AND decision_protocol IS NULL
      AND policy_context IS NULL
    )
    OR (
      producer_revision IS NOT NULL
      AND (
        (decision_protocol IS NULL AND policy_context IS NULL)
        OR (
          decision_protocol = 'sochron.pa01.decision.v2'
          AND jsonb_typeof(policy_context) = 'object'
        )
      )
    )
  );

CREATE OR REPLACE FUNCTION sochron_private.guard_pa01_policy_context()
  RETURNS trigger
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  context_input jsonb;
  observations jsonb;
  observation jsonb;
  key text;
begin
  if new.producer_revision is null then
    if new.decision_protocol is not null or new.policy_context is not null then
      raise exception using errcode = '23514', message = 'PA01_POLICY_CONTEXT_INVALID';
    end if;
    return new;
  end if;
  if new.decision_protocol is null and new.policy_context is null then
    return new;
  end if;

  context_input := new.policy_context;
  if new.producer_revision <> 'PA01-v1.0.1/native-pa01-aggregation-v1'
     or new.decision_protocol <> 'sochron.pa01.decision.v2'
     or jsonb_typeof(context_input) is distinct from 'object'
     or octet_length(context_input::text) > 32768
     or not (context_input ?& array[
       'schema','evidence_id','kernel_decision_id','market_data_cutoff_utc',
       'context_hash','cutoff_utc','symbol','feed_id','spread_price','market_open',
       'price_stale','news_blocked','has_exposure','has_pending','ai_enabled',
       'observations'
     ])
     or context_input - array[
       'schema','evidence_id','kernel_decision_id','market_data_cutoff_utc',
       'context_hash','cutoff_utc','symbol','feed_id','spread_price','market_open',
       'price_stale','news_blocked','has_exposure','has_pending','ai_enabled',
       'observations'
     ] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'PA01_POLICY_CONTEXT_INVALID';
  end if;

  if context_input->>'schema' <> 'sochron.pa01.policy-context.v1'
     or jsonb_typeof(context_input->'evidence_id') is distinct from 'string'
     or length(context_input->>'evidence_id') not between 1 and 128
     or context_input->>'evidence_id' ~ '[[:cntrl:]]'
     or jsonb_typeof(context_input->'kernel_decision_id') is distinct from 'string'
     or length(context_input->>'kernel_decision_id') not between 1 and 128
     or context_input->>'kernel_decision_id' ~ '[[:cntrl:]]'
     or jsonb_typeof(context_input->'context_hash') is distinct from 'string'
     or context_input->>'context_hash' !~ '^[0-9a-f]{64}$'
     or context_input->>'evidence_id'
        is distinct from 'pa01-policy:' || left(context_input->>'context_hash',32)
     or jsonb_typeof(context_input->'market_data_cutoff_utc') is distinct from 'string'
     or (context_input->>'market_data_cutoff_utc')
        !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
     or jsonb_typeof(context_input->'cutoff_utc') is distinct from 'string'
     or (context_input->>'cutoff_utc')
        !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
     or (context_input->>'market_data_cutoff_utc')::timestamptz > new.available_at
     or (context_input->>'cutoff_utc')::timestamptz is distinct from new.available_at
     or jsonb_typeof(context_input->'symbol') is distinct from 'string'
     or context_input->>'symbol' is distinct from new.symbol
     or jsonb_typeof(context_input->'feed_id') is distinct from 'string'
     or context_input->>'feed_id' is distinct from new.feed_id
     or jsonb_typeof(context_input->'spread_price') is distinct from 'string'
     or length(context_input->>'spread_price') not between 1 and 40
     or context_input->>'spread_price' !~ '^(0|[1-9][0-9]*)(\.[0-9]+)?$'
     or (context_input->>'spread_price')::numeric >= 100000000000000
     or jsonb_typeof(context_input->'market_open') is distinct from 'boolean'
     or jsonb_typeof(context_input->'price_stale') is distinct from 'boolean'
     or jsonb_typeof(context_input->'news_blocked') is distinct from 'boolean'
     or jsonb_typeof(context_input->'has_exposure') is distinct from 'boolean'
     or jsonb_typeof(context_input->'has_pending') is distinct from 'boolean'
     or context_input->'ai_enabled' is distinct from 'false'::jsonb then
    raise exception using errcode = '23514', message = 'PA01_POLICY_CONTEXT_INVALID';
  end if;

  observations := context_input->'observations';
  if jsonb_typeof(observations) is distinct from 'object'
     or not (observations ?& array['quote','market','news','account'])
     or observations - array['quote','market','news','account'] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'PA01_POLICY_CONTEXT_INVALID';
  end if;
  foreach key in array array['quote','market','news','account'] loop
    observation := observations->key;
    if jsonb_typeof(observation) is distinct from 'object'
       or not (observation ?& array['evidence_id','observed_at_utc'])
       or observation - array['evidence_id','observed_at_utc'] <> '{}'::jsonb
       or jsonb_typeof(observation->'evidence_id') is distinct from 'string'
       or length(observation->>'evidence_id') not between 1 and 128
       or observation->>'evidence_id' ~ '[[:cntrl:]]'
       or jsonb_typeof(observation->'observed_at_utc') is distinct from 'string'
       or (observation->>'observed_at_utc')
          !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
       or (observation->>'observed_at_utc')::timestamptz > new.available_at then
      raise exception using errcode = '23514', message = 'PA01_POLICY_CONTEXT_INVALID';
    end if;
  end loop;
  if (select count(distinct value->>'evidence_id') from jsonb_each(observations)) <> 4
     or (
       context_input->'market_open' = 'true'::jsonb
       and context_input->'price_stale' = 'false'::jsonb
       and (observations->'quote'->>'observed_at_utc')::timestamptz
           < new.available_at - interval '5 seconds'
     ) then
    raise exception using errcode = '23514', message = 'PA01_POLICY_CONTEXT_INVALID';
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION sochron_private.guard_pa01_policy_signal()
  RETURNS trigger
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  snapshot public.feature_snapshots%rowtype;
begin
  if new.producer_revision is null then
    return new;
  end if;
  select * into snapshot
  from public.feature_snapshots stored
  where stored.owner_id = new.owner_id and stored.id = new.feature_snapshot_id;
  if snapshot.decision_protocol is null then
    return new;
  end if;
  if snapshot.decision_protocol <> 'sochron.pa01.decision.v2'
     or jsonb_typeof(snapshot.policy_context) is distinct from 'object'
     or new.confirmed_at is distinct from
        (snapshot.policy_context->>'cutoff_utc')::timestamptz
     or not new.evidence_ids @>
        jsonb_build_array(snapshot.policy_context->>'evidence_id') then
    raise exception using errcode = '23514', message = 'PA01_POLICY_SIGNAL_INVALID';
  end if;
  return new;
end;
$function$;

CREATE TRIGGER pa01_policy_context_guard
  BEFORE INSERT ON public.feature_snapshots
  FOR EACH ROW EXECUTE FUNCTION sochron_private.guard_pa01_policy_context();

CREATE TRIGGER pa01_policy_signal_guard
  BEFORE INSERT ON public.signals
  FOR EACH ROW EXECUTE FUNCTION sochron_private.guard_pa01_policy_signal();

CREATE OR REPLACE FUNCTION public.sochron_read_pa01_decision(
  p_owner_id uuid,
  p_signal_id text
)
  RETURNS jsonb
  LANGUAGE plpgsql
  STABLE
  SET search_path TO ''
  AS $function$
declare
  result jsonb;
begin
  if p_owner_id is null
     or p_signal_id is null
     or length(p_signal_id) not between 1 and 128
     or p_signal_id ~ '[[:cntrl:]]' then
    raise exception using errcode = '22023', message = 'PA01_READ_INVALID';
  end if;
  select jsonb_build_object(
    'protocol',coalesce(snapshot.decision_protocol,'sochron.pa01.decision.v1'),
    'found',true,
    'owner_id',signal.owner_id,
    'strategy_version_id',signal.strategy_version_id,
    'experiment_id',signal.experiment_id,
    'producer_revision',signal.producer_revision,
    'decision_fingerprint',signal.decision_fingerprint,
    'snapshot',jsonb_build_object(
      'row_id',snapshot.id,'snapshot_id',snapshot.snapshot_id,'feed_id',snapshot.feed_id,
      'symbol',snapshot.symbol,'timeframe',snapshot.timeframe,'event_time',snapshot.event_time,
      'received_at',snapshot.received_at,'available_at',snapshot.available_at,
      'dataset_hash',snapshot.dataset_hash,'values',snapshot.values,'created_at',snapshot.created_at
    ) || case when snapshot.decision_protocol is null then '{}'::jsonb else jsonb_build_object(
      'decision_protocol',snapshot.decision_protocol,'policy_context',snapshot.policy_context
    ) end,
    'signal',jsonb_build_object(
      'row_id',signal.id,'signal_id',signal.signal_id,'setup_id',signal.setup_id,
      'action',signal.action,'formed_at',signal.formed_at,'confirmed_at',signal.confirmed_at,
      'expires_at',signal.expires_at,'evidence_ids',signal.evidence_ids,
      'blocked_reason',signal.blocked_reason,'created_at',signal.created_at
    )
  ) into result
  from public.signals signal
  join public.feature_snapshots snapshot
    on snapshot.owner_id = signal.owner_id and snapshot.id = signal.feature_snapshot_id
  where signal.owner_id = p_owner_id
    and signal.signal_id = p_signal_id
    and signal.producer_revision is not null;
  return coalesce(result,jsonb_build_object(
    'protocol','sochron.pa01.decision.v1','found',false,
    'owner_id',p_owner_id,'signal_id',p_signal_id
  ));
end;
$function$;

CREATE OR REPLACE FUNCTION public.sochron_store_pa01_decision(
  p_owner_id uuid,
  p_strategy_version_id bigint,
  p_experiment_id bigint,
  p_decision jsonb
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  snapshot_input jsonb;
  signal_input jsonb;
  revision text;
  fingerprint text;
  protocol_input text;
  key text;
  stored_snapshot public.feature_snapshots%rowtype;
  stored_signal public.signals%rowtype;
begin
  if p_owner_id is null or p_strategy_version_id is null or p_experiment_id is null
     or jsonb_typeof(p_decision) is distinct from 'object'
     or octet_length(p_decision::text) > 131072
     or not (p_decision ?& array['protocol','producer_revision','decision_fingerprint','snapshot','signal'])
     or p_decision - array['protocol','producer_revision','decision_fingerprint','snapshot','signal'] <> '{}'::jsonb
     or jsonb_typeof(p_decision->'protocol') is distinct from 'string'
     or p_decision->>'protocol' not in (
       'sochron.pa01.decision.v1','sochron.pa01.decision.v2'
     )
     or jsonb_typeof(p_decision->'producer_revision') is distinct from 'string'
     or p_decision->>'producer_revision' <> 'PA01-v1.0.1/native-pa01-aggregation-v1'
     or jsonb_typeof(p_decision->'decision_fingerprint') is distinct from 'string'
     or p_decision->>'decision_fingerprint' !~ '^[0-9a-f]{64}$'
     or jsonb_typeof(p_decision->'snapshot') is distinct from 'object'
     or jsonb_typeof(p_decision->'signal') is distinct from 'object' then
    raise exception using errcode = '22023', message = 'PA01_DECISION_INVALID';
  end if;
  revision := p_decision->>'producer_revision';
  fingerprint := p_decision->>'decision_fingerprint';
  protocol_input := p_decision->>'protocol';
  snapshot_input := p_decision->'snapshot';
  signal_input := p_decision->'signal';

  if not (snapshot_input ?& array[
       'snapshot_id','feed_id','symbol','timeframe','event_time','received_at','available_at',
       'dataset_hash','values'
     ])
     or (
       protocol_input = 'sochron.pa01.decision.v1'
       and snapshot_input - array[
         'snapshot_id','feed_id','symbol','timeframe','event_time','received_at','available_at',
         'dataset_hash','values'
       ] <> '{}'::jsonb
     )
     or (
       protocol_input = 'sochron.pa01.decision.v2'
       and (
         not (snapshot_input ?& array['decision_protocol','policy_context'])
         or snapshot_input - array[
           'snapshot_id','feed_id','symbol','timeframe','event_time','received_at','available_at',
           'dataset_hash','values','decision_protocol','policy_context'
         ] <> '{}'::jsonb
         or snapshot_input->>'decision_protocol' <> protocol_input
         or jsonb_typeof(snapshot_input->'policy_context') is distinct from 'object'
       )
     )
     or not (signal_input ?& array[
       'signal_id','setup_id','action','formed_at','confirmed_at','expires_at',
       'evidence_ids','blocked_reason'
     ])
     or signal_input - array[
       'signal_id','setup_id','action','formed_at','confirmed_at','expires_at',
       'evidence_ids','blocked_reason'
     ] <> '{}'::jsonb then
    raise exception using errcode = '22023', message = 'PA01_DECISION_INVALID';
  end if;

  foreach key in array array['event_time','received_at','available_at'] loop
    if jsonb_typeof(snapshot_input->key) is distinct from 'string'
       or (snapshot_input->>key) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$' then
      raise exception using errcode = '22023', message = 'PA01_DECISION_INVALID';
    end if;
  end loop;
  foreach key in array array['formed_at','confirmed_at','expires_at'] loop
    if jsonb_typeof(signal_input->key) is distinct from 'string'
       or (signal_input->>key) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$' then
      raise exception using errcode = '22023', message = 'PA01_DECISION_INVALID';
    end if;
  end loop;

  if jsonb_typeof(snapshot_input->'snapshot_id') is distinct from 'string'
     or jsonb_typeof(snapshot_input->'feed_id') is distinct from 'string'
     or jsonb_typeof(snapshot_input->'symbol') is distinct from 'string'
     or snapshot_input->>'timeframe' <> 'M5'
     or jsonb_typeof(snapshot_input->'dataset_hash') is distinct from 'string'
     or jsonb_typeof(snapshot_input->'values') is distinct from 'object'
     or jsonb_typeof(signal_input->'signal_id') is distinct from 'string'
     or jsonb_typeof(signal_input->'setup_id') is distinct from 'string'
     or jsonb_typeof(signal_input->'action') is distinct from 'string'
     or signal_input->>'action' not in ('buy','sell','wait','block')
     or jsonb_typeof(signal_input->'evidence_ids') is distinct from 'array'
     or (
       signal_input->'blocked_reason' <> 'null'::jsonb
       and jsonb_typeof(signal_input->'blocked_reason') is distinct from 'string'
     ) then
    raise exception using errcode = '22023', message = 'PA01_DECISION_INVALID';
  end if;

  perform 1 from public.strategy_versions strategy
  where strategy.owner_id = p_owner_id and strategy.id = p_strategy_version_id
  for share;
  if not found then
    raise exception using errcode = '23514', message = 'PA01_STRATEGY_DENIED';
  end if;
  perform 1 from public.experiments experiment
  where experiment.owner_id = p_owner_id
    and experiment.id = p_experiment_id
    and experiment.strategy_version_id = p_strategy_version_id
  for share;
  if not found then
    raise exception using errcode = '23514', message = 'PA01_EXPERIMENT_DENIED';
  end if;

  insert into public.feature_snapshots(
    owner_id,strategy_version_id,snapshot_id,feed_id,symbol,timeframe,event_time,
    received_at,available_at,values,dataset_hash,producer_revision,decision_fingerprint,
    decision_protocol,policy_context
  ) values (
    p_owner_id,p_strategy_version_id,snapshot_input->>'snapshot_id',snapshot_input->>'feed_id',
    snapshot_input->>'symbol',snapshot_input->>'timeframe',(snapshot_input->>'event_time')::timestamptz,
    (snapshot_input->>'received_at')::timestamptz,(snapshot_input->>'available_at')::timestamptz,
    snapshot_input->'values',snapshot_input->>'dataset_hash',revision,fingerprint,
    case when protocol_input = 'sochron.pa01.decision.v2'
      then snapshot_input->>'decision_protocol' else null end,
    case when protocol_input = 'sochron.pa01.decision.v2'
      then snapshot_input->'policy_context' else null end
  ) on conflict do nothing;

  select * into stored_snapshot from public.feature_snapshots snapshot
  where snapshot.owner_id = p_owner_id and snapshot.snapshot_id = snapshot_input->>'snapshot_id';
  if stored_snapshot.id is null
     or stored_snapshot.strategy_version_id is distinct from p_strategy_version_id
     or stored_snapshot.feed_id is distinct from snapshot_input->>'feed_id'
     or stored_snapshot.symbol is distinct from snapshot_input->>'symbol'
     or stored_snapshot.timeframe is distinct from snapshot_input->>'timeframe'
     or stored_snapshot.event_time is distinct from (snapshot_input->>'event_time')::timestamptz
     or stored_snapshot.received_at is distinct from (snapshot_input->>'received_at')::timestamptz
     or stored_snapshot.available_at is distinct from (snapshot_input->>'available_at')::timestamptz
     or stored_snapshot.values is distinct from snapshot_input->'values'
     or stored_snapshot.dataset_hash is distinct from snapshot_input->>'dataset_hash'
     or stored_snapshot.producer_revision is distinct from revision
     or stored_snapshot.decision_fingerprint is distinct from fingerprint
     or stored_snapshot.decision_protocol is distinct from (
        case when protocol_input = 'sochron.pa01.decision.v2'
          then snapshot_input->>'decision_protocol' else null end
     )
     or stored_snapshot.policy_context is distinct from (
        case when protocol_input = 'sochron.pa01.decision.v2'
          then snapshot_input->'policy_context' else null end
     ) then
    raise exception using errcode = '23505', message = 'PA01_DECISION_CONFLICT';
  end if;

  insert into public.signals(
    owner_id,experiment_id,strategy_version_id,signal_id,setup_id,action,formed_at,
    confirmed_at,expires_at,evidence_ids,blocked_reason,feature_snapshot_id,
    producer_revision,decision_fingerprint
  ) values (
    p_owner_id,p_experiment_id,p_strategy_version_id,signal_input->>'signal_id',
    signal_input->>'setup_id',signal_input->>'action',(signal_input->>'formed_at')::timestamptz,
    (signal_input->>'confirmed_at')::timestamptz,(signal_input->>'expires_at')::timestamptz,
    signal_input->'evidence_ids',signal_input->>'blocked_reason',stored_snapshot.id,
    revision,fingerprint
  ) on conflict do nothing;

  select * into stored_signal from public.signals signal
  where signal.owner_id = p_owner_id and signal.signal_id = signal_input->>'signal_id';
  if stored_signal.id is null
     or stored_signal.experiment_id is distinct from p_experiment_id
     or stored_signal.strategy_version_id is distinct from p_strategy_version_id
     or stored_signal.setup_id is distinct from signal_input->>'setup_id'
     or stored_signal.action is distinct from signal_input->>'action'
     or stored_signal.formed_at is distinct from (signal_input->>'formed_at')::timestamptz
     or stored_signal.confirmed_at is distinct from (signal_input->>'confirmed_at')::timestamptz
     or stored_signal.expires_at is distinct from (signal_input->>'expires_at')::timestamptz
     or stored_signal.evidence_ids is distinct from signal_input->'evidence_ids'
     or stored_signal.blocked_reason is distinct from signal_input->>'blocked_reason'
     or stored_signal.feature_snapshot_id is distinct from stored_snapshot.id
     or stored_signal.producer_revision is distinct from revision
     or stored_signal.decision_fingerprint is distinct from fingerprint then
    raise exception using errcode = '23505', message = 'PA01_DECISION_CONFLICT';
  end if;
  return public.sochron_read_pa01_decision(p_owner_id,signal_input->>'signal_id');
end;
$function$;

COMMENT ON COLUMN public.feature_snapshots.decision_protocol IS
  'Non-null only for policy-context-complete PA01 protocol-v2 producer snapshots.';
COMMENT ON COLUMN public.feature_snapshots.policy_context IS
  'Immutable bounded PA01 spread/blocker observations and their source evidence.';
COMMENT ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb) IS
  'Atomically insert-or-verify one PA01 v1/v2 evidence pair; no execution authority.';

REVOKE ALL ON FUNCTION sochron_private.guard_pa01_policy_context()
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION sochron_private.guard_pa01_policy_context()
  TO postgres, service_role;
REVOKE ALL ON FUNCTION sochron_private.guard_pa01_policy_signal()
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION sochron_private.guard_pa01_policy_signal()
  TO postgres, service_role;
REVOKE ALL ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)
  TO postgres, service_role;
REVOKE ALL ON FUNCTION public.sochron_read_pa01_decision(uuid,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sochron_read_pa01_decision(uuid,text)
  TO postgres, service_role;
