-- SCN-020: backend-only atomic PA01 decision persistence and reconciliation.
-- This boundary stores research evidence only. It creates no command, risk event,
-- order or execution side effect and never enables Auto Trading.
SET local check_function_bodies = off;

ALTER TABLE public.feature_snapshots
  ADD COLUMN producer_revision text,
  ADD COLUMN decision_fingerprint text,
  ADD CONSTRAINT feature_snapshots_owner_id_id_key UNIQUE (owner_id, id),
  ADD CONSTRAINT feature_snapshots_producer_presence_check CHECK (
    (producer_revision IS NULL AND decision_fingerprint IS NULL)
    OR (
      producer_revision IS NOT NULL
      AND length(producer_revision) BETWEEN 1 AND 128
      AND producer_revision !~ '[[:cntrl:]]'
      AND decision_fingerprint ~ '^[0-9a-f]{64}$'
    )
  );

ALTER TABLE public.signals
  ADD COLUMN feature_snapshot_id bigint,
  ADD COLUMN producer_revision text,
  ADD COLUMN decision_fingerprint text,
  ADD CONSTRAINT signals_producer_presence_check CHECK (
    (feature_snapshot_id IS NULL AND producer_revision IS NULL AND decision_fingerprint IS NULL)
    OR (
      feature_snapshot_id IS NOT NULL
      AND producer_revision IS NOT NULL
      AND length(producer_revision) BETWEEN 1 AND 128
      AND producer_revision !~ '[[:cntrl:]]'
      AND decision_fingerprint ~ '^[0-9a-f]{64}$'
    )
  ),
  ADD CONSTRAINT signals_producer_block_reason_check CHECK (
    producer_revision IS NULL
    OR ((action = 'block') = (blocked_reason IS NOT NULL))
  ),
  ADD CONSTRAINT signals_owner_feature_snapshot_fkey
    FOREIGN KEY (owner_id, feature_snapshot_id)
    REFERENCES public.feature_snapshots (owner_id, id);

CREATE UNIQUE INDEX feature_snapshots_owner_decision_fingerprint_key
  ON public.feature_snapshots (owner_id, decision_fingerprint)
  WHERE decision_fingerprint IS NOT NULL;

CREATE UNIQUE INDEX signals_owner_decision_fingerprint_key
  ON public.signals (owner_id, decision_fingerprint)
  WHERE decision_fingerprint IS NOT NULL;

CREATE UNIQUE INDEX signals_owner_feature_snapshot_key
  ON public.signals (owner_id, feature_snapshot_id)
  WHERE feature_snapshot_id IS NOT NULL;

CREATE OR REPLACE FUNCTION sochron_private.guard_pa01_feature_snapshot()
  RETURNS trigger
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  payload jsonb;
  features jsonb;
  execution jsonb;
  pivot jsonb;
  key text;
  value_text text;
begin
  if tg_op in ('UPDATE', 'DELETE') and old.producer_revision is not null then
    raise exception using errcode = '23514', message = 'PA01_SNAPSHOT_IMMUTABLE';
  end if;
  if tg_op = 'DELETE' then
    return old;
  end if;
  if tg_op = 'UPDATE' and new.producer_revision is not null then
    raise exception using errcode = '23514', message = 'PA01_SNAPSHOT_IMMUTABLE';
  end if;
  if new.producer_revision is null then
    return new;
  end if;

  payload := new.values;
  if new.producer_revision <> 'PA01-v1.0.1/native-pa01-aggregation-v1'
     or new.timeframe <> 'M5'
     or length(new.snapshot_id) not between 1 and 128
     or new.snapshot_id ~ '[[:cntrl:]]'
     or length(new.feed_id) not between 1 and 128
     or new.feed_id !~ '^mt5-copyrates:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
     or length(new.symbol) not between 1 and 32
     or new.symbol ~ '[[:space:][:cntrl:]]'
     or new.received_at is distinct from new.available_at
     or new.available_at > statement_timestamp()
     or new.dataset_hash !~ '^[0-9a-f]{64}$'
     or jsonb_typeof(payload) is distinct from 'object'
     or octet_length(payload::text) > 98304
     or not (payload ?& array[
       'schema','decision_id','strategy_version','code_hash','parameter_version','parameter_hash',
       'aggregation_version','aggregation_hash','source_dataset_hash','dataset_hash',
       'data_cutoff_utc','ai_enabled','action','reason_code','blocked_reason','features',
       'execution_parameters'
     ])
     or payload - array[
       'schema','decision_id','strategy_version','code_hash','parameter_version','parameter_hash',
       'aggregation_version','aggregation_hash','source_dataset_hash','dataset_hash',
       'data_cutoff_utc','ai_enabled','action','reason_code','blocked_reason','features',
       'execution_parameters'
     ] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'PA01_SNAPSHOT_INVALID';
  end if;

  if jsonb_typeof(payload->'schema') is distinct from 'string'
     or payload->>'schema' <> 'sochron.pa01.features.v1'
     or jsonb_typeof(payload->'strategy_version') is distinct from 'string'
     or payload->>'strategy_version' <> 'PA01-v1'
     or jsonb_typeof(payload->'code_hash') is distinct from 'string'
     or payload->>'code_hash' !~ '^[0-9a-f]{64}$'
     or jsonb_typeof(payload->'parameter_version') is distinct from 'string'
     or payload->>'parameter_version' <> 'PA01-v1.0.1'
     or jsonb_typeof(payload->'parameter_hash') is distinct from 'string'
     or payload->>'parameter_hash' <> '62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822'
     or jsonb_typeof(payload->'aggregation_version') is distinct from 'string'
     or payload->>'aggregation_version' <> 'native-pa01-aggregation-v1'
     or jsonb_typeof(payload->'aggregation_hash') is distinct from 'string'
     or payload->>'aggregation_hash' !~ '^[0-9a-f]{64}$'
     or jsonb_typeof(payload->'source_dataset_hash') is distinct from 'string'
     or payload->>'source_dataset_hash' !~ '^[0-9a-f]{64}$'
     or jsonb_typeof(payload->'dataset_hash') is distinct from 'string'
     or payload->>'dataset_hash' is distinct from new.dataset_hash
     or payload->'ai_enabled' is distinct from 'false'::jsonb
     or jsonb_typeof(payload->'decision_id') is distinct from 'string'
     or length(payload->>'decision_id') not between 1 and 128
     or payload->>'decision_id' ~ '[[:cntrl:]]'
     or jsonb_typeof(payload->'data_cutoff_utc') is distinct from 'string'
     or (payload->>'data_cutoff_utc') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
     or (payload->>'data_cutoff_utc')::timestamptz is distinct from new.available_at
     or jsonb_typeof(payload->'action') is distinct from 'string'
     or payload->>'action' not in ('buy','sell','wait','block')
     or jsonb_typeof(payload->'reason_code') is distinct from 'string'
     or payload->>'reason_code' not in (
       'SETUP_CONFIRMED','INSUFFICIENT_WARMUP','STRUCTURE_INCOMPLETE','STRUCTURE_MIXED',
       'TREND_FILTER','NO_PULLBACK_BREAKOUT','STOP_DISTANCE','MARKET_CLOSED','STALE_PRICE',
       'DATA_GAP','NEWS_PAUSE','SPREAD_CAP','EXPOSURE_EXISTS','PENDING_EXISTS'
     )
     or ((payload->>'action' in ('buy','sell')) <> (payload->>'reason_code' = 'SETUP_CONFIRMED'))
     or ((payload->>'action' = 'block') <> (payload->'blocked_reason' <> 'null'::jsonb))
     or (
       payload->'blocked_reason' <> 'null'::jsonb
       and (
         jsonb_typeof(payload->'blocked_reason') is distinct from 'string'
         or length(payload->>'blocked_reason') not between 1 and 128
         or payload->>'blocked_reason' ~ '[[:cntrl:]]'
         or payload->>'blocked_reason' is distinct from payload->>'reason_code'
       )
     ) then
    raise exception using errcode = '23514', message = 'PA01_SNAPSHOT_INVALID';
  end if;

  features := payload->'features';
  if jsonb_typeof(features) is distinct from 'object'
     or not (features ?& array[
       'structure','ema20','ema50','previous_ema20','atr14','adx14','spread_cap',
       'proposed_stop','stop_distance_at_close','stop_distance_atr',
       'latest_swing_highs','latest_swing_lows'
     ])
     or features - array[
       'structure','ema20','ema50','previous_ema20','atr14','adx14','spread_cap',
       'proposed_stop','stop_distance_at_close','stop_distance_atr',
       'latest_swing_highs','latest_swing_lows'
     ] <> '{}'::jsonb
     or jsonb_typeof(features->'structure') is distinct from 'string'
     or features->>'structure' not in ('bullish','bearish','mixed','incomplete')
     or jsonb_typeof(features->'latest_swing_highs') is distinct from 'array'
     or jsonb_typeof(features->'latest_swing_lows') is distinct from 'array'
     or jsonb_array_length(features->'latest_swing_highs') > 2
     or jsonb_array_length(features->'latest_swing_lows') > 2 then
    raise exception using errcode = '23514', message = 'PA01_FEATURES_INVALID';
  end if;

  foreach key in array array[
    'ema20','ema50','previous_ema20','atr14','adx14','spread_cap','proposed_stop',
    'stop_distance_at_close','stop_distance_atr'
  ] loop
    if features->key <> 'null'::jsonb then
      if jsonb_typeof(features->key) is distinct from 'string'
         or length(features->>key) not between 1 and 40
         or (features->>key) !~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$' then
        raise exception using errcode = '23514', message = 'PA01_FEATURES_INVALID';
      end if;
      value_text := features->>key;
      if abs(value_text::numeric) >= 100000000000000
         or (key in ('ema20','ema50','previous_ema20','atr14','proposed_stop') and value_text::numeric <= 0)
         or (key in ('adx14','spread_cap','stop_distance_at_close','stop_distance_atr') and value_text::numeric < 0) then
        raise exception using errcode = '23514', message = 'PA01_FEATURES_INVALID';
      end if;
    end if;
  end loop;

  for pivot in
    select value from jsonb_array_elements(features->'latest_swing_highs')
  loop
    if jsonb_typeof(pivot) is distinct from 'object'
       or not (pivot ?& array['kind','price','evidence_id','formed_at_utc','confirmed_at_utc'])
       or pivot - array['kind','price','evidence_id','formed_at_utc','confirmed_at_utc'] <> '{}'::jsonb
       or pivot->>'kind' <> 'high'
       or jsonb_typeof(pivot->'price') is distinct from 'string'
       or length(pivot->>'price') not between 1 and 40
       or (pivot->>'price') !~ '^(0|[1-9][0-9]*)(\.[0-9]+)?$'
       or (pivot->>'price')::numeric <= 0
       or (pivot->>'price')::numeric >= 100000000000000
       or jsonb_typeof(pivot->'evidence_id') is distinct from 'string'
       or length(pivot->>'evidence_id') not between 1 and 128
       or pivot->>'evidence_id' ~ '[[:cntrl:]]'
       or jsonb_typeof(pivot->'formed_at_utc') is distinct from 'string'
       or jsonb_typeof(pivot->'confirmed_at_utc') is distinct from 'string'
       or (pivot->>'formed_at_utc') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
       or (pivot->>'confirmed_at_utc') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
       or (pivot->>'confirmed_at_utc')::timestamptz < (pivot->>'formed_at_utc')::timestamptz
       or (pivot->>'confirmed_at_utc')::timestamptz > new.available_at then
      raise exception using errcode = '23514', message = 'PA01_FEATURES_INVALID';
    end if;
  end loop;

  for pivot in
    select value from jsonb_array_elements(features->'latest_swing_lows')
  loop
    if jsonb_typeof(pivot) is distinct from 'object'
       or not (pivot ?& array['kind','price','evidence_id','formed_at_utc','confirmed_at_utc'])
       or pivot - array['kind','price','evidence_id','formed_at_utc','confirmed_at_utc'] <> '{}'::jsonb
       or pivot->>'kind' <> 'low'
       or jsonb_typeof(pivot->'price') is distinct from 'string'
       or length(pivot->>'price') not between 1 and 40
       or (pivot->>'price') !~ '^(0|[1-9][0-9]*)(\.[0-9]+)?$'
       or (pivot->>'price')::numeric <= 0
       or (pivot->>'price')::numeric >= 100000000000000
       or jsonb_typeof(pivot->'evidence_id') is distinct from 'string'
       or length(pivot->>'evidence_id') not between 1 and 128
       or pivot->>'evidence_id' ~ '[[:cntrl:]]'
       or jsonb_typeof(pivot->'formed_at_utc') is distinct from 'string'
       or jsonb_typeof(pivot->'confirmed_at_utc') is distinct from 'string'
       or (pivot->>'formed_at_utc') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
       or (pivot->>'confirmed_at_utc') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?(Z|\+00:00)$'
       or (pivot->>'confirmed_at_utc')::timestamptz < (pivot->>'formed_at_utc')::timestamptz
       or (pivot->>'confirmed_at_utc')::timestamptz > new.available_at then
      raise exception using errcode = '23514', message = 'PA01_FEATURES_INVALID';
    end if;
  end loop;

  execution := payload->'execution_parameters';
  if jsonb_typeof(execution) is distinct from 'object'
     or not (execution ?& array[
       'next_tick_entry_required','max_entry_drift_atr','stop_buffer_atr','stop_min_atr',
       'stop_max_atr','target_r','time_exit_m5_bars','signal_expiry_seconds',
       'order_created','risk_admitted'
     ])
     or execution - array[
       'next_tick_entry_required','max_entry_drift_atr','stop_buffer_atr','stop_min_atr',
       'stop_max_atr','target_r','time_exit_m5_bars','signal_expiry_seconds',
       'order_created','risk_admitted'
     ] <> '{}'::jsonb
     or execution->'next_tick_entry_required' is distinct from 'true'::jsonb
     or jsonb_typeof(execution->'max_entry_drift_atr') is distinct from 'string'
     or (execution->>'max_entry_drift_atr')::numeric <> 0.20
     or jsonb_typeof(execution->'stop_buffer_atr') is distinct from 'string'
     or (execution->>'stop_buffer_atr')::numeric <> 0.20
     or jsonb_typeof(execution->'stop_min_atr') is distinct from 'string'
     or (execution->>'stop_min_atr')::numeric <> 0.50
     or jsonb_typeof(execution->'stop_max_atr') is distinct from 'string'
     or (execution->>'stop_max_atr')::numeric <> 2.00
     or jsonb_typeof(execution->'target_r') is distinct from 'string'
     or (execution->>'target_r')::numeric <> 2
     or execution->'time_exit_m5_bars' is distinct from '12'::jsonb
     or execution->'signal_expiry_seconds' is distinct from '30'::jsonb
     or execution->'order_created' is distinct from 'false'::jsonb
     or execution->'risk_admitted' is distinct from 'false'::jsonb then
    raise exception using errcode = '23514', message = 'PA01_EXECUTION_PARAMETERS_INVALID';
  end if;

  perform 1
  from public.strategy_versions strategy
  where strategy.owner_id = new.owner_id
    and strategy.id = new.strategy_version_id
    and strategy.version_id = 'PA01-v1'
    and strategy.code_hash = payload->>'code_hash'
    and strategy.status in ('candidate','approved','active')
    and strategy.data_cutoff <= new.available_at
    and strategy.parameters->>'parameter_version' = 'PA01-v1.0.1'
    and strategy.parameters->>'parameter_hash' = '62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822'
    and strategy.parameters->>'aggregation_version' = 'native-pa01-aggregation-v1';
  if not found then
    raise exception using errcode = '23514', message = 'PA01_STRATEGY_DENIED';
  end if;
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION sochron_private.guard_pa01_signal()
  RETURNS trigger
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  snapshot public.feature_snapshots%rowtype;
  item jsonb;
begin
  if tg_op in ('UPDATE', 'DELETE') and old.producer_revision is not null then
    raise exception using errcode = '23514', message = 'PA01_SIGNAL_IMMUTABLE';
  end if;
  if tg_op = 'DELETE' then
    return old;
  end if;
  if tg_op = 'UPDATE' and new.producer_revision is not null then
    raise exception using errcode = '23514', message = 'PA01_SIGNAL_IMMUTABLE';
  end if;
  if new.producer_revision is null then
    return new;
  end if;

  select * into snapshot
  from public.feature_snapshots stored
  where stored.owner_id = new.owner_id and stored.id = new.feature_snapshot_id;
  if snapshot.id is null
     or new.producer_revision <> 'PA01-v1.0.1/native-pa01-aggregation-v1'
     or new.producer_revision is distinct from snapshot.producer_revision
     or new.decision_fingerprint is distinct from snapshot.decision_fingerprint
     or new.strategy_version_id is distinct from snapshot.strategy_version_id
     or length(new.signal_id) not between 1 and 128
     or new.signal_id ~ '[[:cntrl:]]'
     or length(new.setup_id) not between 1 and 128
     or new.setup_id ~ '[[:cntrl:]]'
     or new.formed_at is distinct from snapshot.event_time
     or new.confirmed_at is distinct from snapshot.available_at
     or new.expires_at is distinct from new.confirmed_at + interval '30 seconds'
     or snapshot.values->>'decision_id' is distinct from new.signal_id
     or snapshot.values->>'action' is distinct from new.action
     or snapshot.values->'blocked_reason' is distinct from coalesce(to_jsonb(new.blocked_reason),'null'::jsonb)
     or ((new.action = 'block') <> (new.blocked_reason is not null))
     or jsonb_typeof(new.evidence_ids) is distinct from 'array'
     or jsonb_array_length(new.evidence_ids) not between 1 and 8
     or (select count(distinct value) from jsonb_array_elements(new.evidence_ids))
        <> jsonb_array_length(new.evidence_ids) then
    raise exception using errcode = '23514', message = 'PA01_SIGNAL_INVALID';
  end if;
  for item in select value from jsonb_array_elements(new.evidence_ids) loop
    if jsonb_typeof(item) is distinct from 'string'
       or length(item #>> '{}') not between 1 and 128
       or (item #>> '{}') ~ '[[:cntrl:]]' then
      raise exception using errcode = '23514', message = 'PA01_SIGNAL_INVALID';
    end if;
  end loop;

  perform 1
  from public.experiments experiment
  join public.strategy_versions strategy
    on strategy.owner_id = experiment.owner_id
   and strategy.id = experiment.strategy_version_id
  where experiment.owner_id = new.owner_id
    and experiment.id = new.experiment_id
    and experiment.strategy_version_id = new.strategy_version_id
    and experiment.status in ('draft','shadow','demo')
    and strategy.version_id = 'PA01-v1'
    and strategy.status in ('candidate','approved','active')
    and strategy.data_cutoff <= new.confirmed_at
    and strategy.parameters->>'parameter_version' = 'PA01-v1.0.1'
    and strategy.parameters->>'parameter_hash' = '62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822'
    and strategy.parameters->>'aggregation_version' = 'native-pa01-aggregation-v1';
  if not found then
    raise exception using errcode = '23514', message = 'PA01_EXPERIMENT_DENIED';
  end if;
  return new;
end;
$function$;

CREATE TRIGGER pa01_feature_snapshot_guard
  BEFORE INSERT OR DELETE OR UPDATE ON public.feature_snapshots
  FOR EACH ROW EXECUTE FUNCTION sochron_private.guard_pa01_feature_snapshot();

CREATE TRIGGER pa01_signal_guard
  BEFORE INSERT OR DELETE OR UPDATE ON public.signals
  FOR EACH ROW EXECUTE FUNCTION sochron_private.guard_pa01_signal();

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
    'protocol','sochron.pa01.decision.v1',
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
    ),
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
  key text;
  stored_snapshot public.feature_snapshots%rowtype;
  stored_signal public.signals%rowtype;
begin
  if p_owner_id is null or p_strategy_version_id is null or p_experiment_id is null
     or jsonb_typeof(p_decision) is distinct from 'object'
     or octet_length(p_decision::text) > 131072
     or not (p_decision ?& array['protocol','producer_revision','decision_fingerprint','snapshot','signal'])
     or p_decision - array['protocol','producer_revision','decision_fingerprint','snapshot','signal'] <> '{}'::jsonb
     or p_decision->>'protocol' <> 'sochron.pa01.decision.v1'
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
  snapshot_input := p_decision->'snapshot';
  signal_input := p_decision->'signal';

  if not (snapshot_input ?& array[
       'snapshot_id','feed_id','symbol','timeframe','event_time','received_at','available_at',
       'dataset_hash','values'
     ])
     or snapshot_input - array[
       'snapshot_id','feed_id','symbol','timeframe','event_time','received_at','available_at',
       'dataset_hash','values'
     ] <> '{}'::jsonb
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
    received_at,available_at,values,dataset_hash,producer_revision,decision_fingerprint
  ) values (
    p_owner_id,p_strategy_version_id,snapshot_input->>'snapshot_id',snapshot_input->>'feed_id',
    snapshot_input->>'symbol',snapshot_input->>'timeframe',(snapshot_input->>'event_time')::timestamptz,
    (snapshot_input->>'received_at')::timestamptz,(snapshot_input->>'available_at')::timestamptz,
    snapshot_input->'values',snapshot_input->>'dataset_hash',revision,fingerprint
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
     or stored_snapshot.decision_fingerprint is distinct from fingerprint then
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

COMMENT ON COLUMN public.feature_snapshots.producer_revision IS
  'Non-null only for immutable backend PA01 producer rows.';
COMMENT ON COLUMN public.signals.feature_snapshot_id IS
  'Owner-safe immutable evidence link for backend PA01 producer rows.';
COMMENT ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb) IS
  'Atomically insert-or-verify one PA01 snapshot/signal pair; no execution authority.';
COMMENT ON FUNCTION public.sochron_read_pa01_decision(uuid,text) IS
  'Backend-only independent reconciliation read for one PA01 producer signal.';

REVOKE ALL ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sochron_store_pa01_decision(uuid,bigint,bigint,jsonb)
  TO postgres, service_role;
REVOKE ALL ON FUNCTION public.sochron_read_pa01_decision(uuid,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sochron_read_pa01_decision(uuid,text)
  TO postgres, service_role;
REVOKE ALL ON FUNCTION sochron_private.guard_pa01_feature_snapshot()
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION sochron_private.guard_pa01_feature_snapshot()
  TO postgres, service_role;
REVOKE ALL ON FUNCTION sochron_private.guard_pa01_signal()
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION sochron_private.guard_pa01_signal()
  TO postgres, service_role;

-- Truncate bypasses row triggers. Preserve existing legacy fixture CRUD while
-- removing maintenance paths over producer-marked evidence.
REVOKE ALL ON TABLE public.feature_snapshots FROM service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.feature_snapshots TO service_role;
REVOKE ALL ON TABLE public.signals FROM service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.signals TO service_role;
