-- SCN-029: strict, backend-only insert-or-verify research evaluation receiver.
-- Legacy evaluation rows remain readable. Producer rows add bounded provenance,
-- exact reconciliation identity and immutability without promotion authority.
SET local check_function_bodies = off;

ALTER TABLE public.evaluations
  ADD COLUMN producer_revision text,
  ADD COLUMN evaluation_protocol text,
  ADD COLUMN evaluation_fingerprint text,
  ADD COLUMN evidence_manifest jsonb,
  ADD CONSTRAINT evaluations_producer_presence_check CHECK (
    (
      producer_revision IS NULL
      AND evaluation_protocol IS NULL
      AND evaluation_fingerprint IS NULL
      AND evidence_manifest IS NULL
    )
    OR (
      producer_revision = 'SCN-029/research-evaluation-v1.0.0'
      AND evaluation_protocol = 'sochron.research-evaluation-envelope.v1'
      AND evaluation_fingerprint ~ '^[0-9a-f]{64}$'
      AND jsonb_typeof(evidence_manifest) = 'object'
    )
  );

CREATE UNIQUE INDEX evaluations_owner_producer_fingerprint_key
  ON public.evaluations (owner_id, evaluation_fingerprint)
  WHERE evaluation_fingerprint IS NOT NULL;

CREATE OR REPLACE FUNCTION sochron_private.guard_research_evaluation()
  RETURNS trigger
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  metrics_input jsonb;
  costs_input jsonb;
  manifest_input jsonb;
  window_input jsonb;
  bootstrap_input jsonb;
  counts_input jsonb;
  strategy public.strategy_versions%rowtype;
  experiment public.experiments%rowtype;
  sample_size bigint;
  wins bigint;
  losses bigint;
  breakeven bigint;
  closed_count bigint;
  decimal_pattern constant text := '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$';
  nonnegative_pattern constant text := '^(0|[1-9][0-9]*)(\.[0-9]+)?$';
  integer_pattern constant text := '^(0|[1-9][0-9]*)$';
  utc_pattern constant text :=
    '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?Z$';
begin
  if tg_op = 'DELETE' then
    if old.producer_revision is not null then
      raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_IMMUTABLE';
    end if;
    return old;
  end if;
  if tg_op = 'UPDATE' then
    if old.producer_revision is not null or new.producer_revision is not null then
      raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_IMMUTABLE';
    end if;
    return new;
  end if;
  if new.producer_revision is null then
    return new;
  end if;

  metrics_input := new.metrics;
  costs_input := new.cost_assumptions;
  manifest_input := new.evidence_manifest;
  if new.producer_revision <> 'SCN-029/research-evaluation-v1.0.0'
     or new.evaluation_protocol <> 'sochron.research-evaluation-envelope.v1'
     or new.evaluation_fingerprint !~ '^[0-9a-f]{64}$'
     or new.dataset_hash !~ '^[0-9a-f]{64}$'
     or jsonb_typeof(metrics_input) is distinct from 'object'
     or jsonb_typeof(costs_input) is distinct from 'object'
     or jsonb_typeof(manifest_input) is distinct from 'object'
     or octet_length(metrics_input::text) > 8192
     or octet_length(costs_input::text) > 4096
     or octet_length(manifest_input::text) > 32768
     or not (metrics_input ?& array[
       'sample_size','wins','losses','breakeven','net_return_pct','expectancy_r',
       'expectancy_r_ci95_low','expectancy_r_ci95_high','max_drawdown_pct','profit_factor'
     ])
     or metrics_input - array[
       'sample_size','wins','losses','breakeven','net_return_pct','expectancy_r',
       'expectancy_r_ci95_low','expectancy_r_ci95_high','max_drawdown_pct','profit_factor'
     ] <> '{}'::jsonb
     or not (costs_input ?& array[
       'spread_points','slippage_points','commission_per_lot','swap_included',
       'operating_cost_per_trade','currency'
     ])
     or costs_input - array[
       'spread_points','slippage_points','commission_per_lot','swap_included',
       'operating_cost_per_trade','currency'
     ] <> '{}'::jsonb
     or not (manifest_input ?& array[
       'manifest_protocol','bundle_hash','strategy_version','strategy_code_hash',
       'evaluation_window','bootstrap','record_counts','equity_basis','cost_currency'
     ])
     or manifest_input - array[
       'manifest_protocol','bundle_hash','strategy_version','strategy_code_hash',
       'evaluation_window','bootstrap','record_counts','equity_basis','cost_currency'
     ] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  if jsonb_typeof(metrics_input->'sample_size') is distinct from 'number'
     or jsonb_typeof(metrics_input->'wins') is distinct from 'number'
     or jsonb_typeof(metrics_input->'losses') is distinct from 'number'
     or jsonb_typeof(metrics_input->'breakeven') is distinct from 'number'
     or metrics_input->>'sample_size' !~ integer_pattern
     or metrics_input->>'wins' !~ integer_pattern
     or metrics_input->>'losses' !~ integer_pattern
     or metrics_input->>'breakeven' !~ integer_pattern
     or jsonb_typeof(metrics_input->'net_return_pct') is distinct from 'string'
     or jsonb_typeof(metrics_input->'expectancy_r') is distinct from 'string'
     or jsonb_typeof(metrics_input->'expectancy_r_ci95_low') is distinct from 'string'
     or jsonb_typeof(metrics_input->'expectancy_r_ci95_high') is distinct from 'string'
     or jsonb_typeof(metrics_input->'max_drawdown_pct') is distinct from 'string'
     or metrics_input->>'net_return_pct' !~ decimal_pattern
     or metrics_input->>'expectancy_r' !~ decimal_pattern
     or metrics_input->>'expectancy_r_ci95_low' !~ decimal_pattern
     or metrics_input->>'expectancy_r_ci95_high' !~ decimal_pattern
     or metrics_input->>'max_drawdown_pct' !~ nonnegative_pattern
     or (
       metrics_input->'profit_factor' <> 'null'::jsonb
       and (
         jsonb_typeof(metrics_input->'profit_factor') is distinct from 'string'
         or metrics_input->>'profit_factor' !~ nonnegative_pattern
       )
     ) then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;
  sample_size := (metrics_input->>'sample_size')::bigint;
  wins := (metrics_input->>'wins')::bigint;
  losses := (metrics_input->>'losses')::bigint;
  breakeven := (metrics_input->>'breakeven')::bigint;
  if sample_size not between 1 and 100000
     or wins > sample_size or losses > sample_size or breakeven > sample_size
     or wins + losses + breakeven <> sample_size
     or (metrics_input->>'net_return_pct')::numeric < -100
     or abs((metrics_input->>'net_return_pct')::numeric) > 1000000
     or abs((metrics_input->>'expectancy_r')::numeric) > 1000000
     or abs((metrics_input->>'expectancy_r_ci95_low')::numeric) > 1000000
     or abs((metrics_input->>'expectancy_r_ci95_high')::numeric) > 1000000
     or (metrics_input->>'expectancy_r_ci95_low')::numeric
        > (metrics_input->>'expectancy_r')::numeric
     or (metrics_input->>'expectancy_r_ci95_high')::numeric
        < (metrics_input->>'expectancy_r')::numeric
     or (metrics_input->>'max_drawdown_pct')::numeric not between 0 and 100
     or (
       metrics_input->'profit_factor' <> 'null'::jsonb
       and (metrics_input->>'profit_factor')::numeric > 1000000
     ) then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  if jsonb_typeof(costs_input->'spread_points') is distinct from 'string'
     or jsonb_typeof(costs_input->'slippage_points') is distinct from 'string'
     or jsonb_typeof(costs_input->'commission_per_lot') is distinct from 'string'
     or jsonb_typeof(costs_input->'swap_included') is distinct from 'boolean'
     or jsonb_typeof(costs_input->'operating_cost_per_trade') is distinct from 'string'
     or jsonb_typeof(costs_input->'currency') is distinct from 'string'
     or costs_input->>'spread_points' !~ nonnegative_pattern
     or costs_input->>'slippage_points' !~ nonnegative_pattern
     or costs_input->>'commission_per_lot' !~ nonnegative_pattern
     or costs_input->>'operating_cost_per_trade' !~ nonnegative_pattern
     or (costs_input->>'spread_points')::numeric > 1000000
     or (costs_input->>'slippage_points')::numeric > 1000000
     or (costs_input->>'commission_per_lot')::numeric > 100000000000000
     or (costs_input->>'operating_cost_per_trade')::numeric > 100000000000000
     or costs_input->>'currency' !~ '^[A-Z]{3}$' then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  window_input := manifest_input->'evaluation_window';
  bootstrap_input := manifest_input->'bootstrap';
  counts_input := manifest_input->'record_counts';
  if manifest_input->>'manifest_protocol' <> 'sochron.research-evaluation-manifest.v1'
     or manifest_input->>'bundle_hash' is distinct from new.dataset_hash
     or manifest_input->>'strategy_code_hash' !~ '^[0-9a-f]{64}$'
     or manifest_input->>'equity_basis' <> 'mark_to_market_including_open_exposure'
     or manifest_input->>'cost_currency' is distinct from costs_input->>'currency'
     or jsonb_typeof(window_input) is distinct from 'object'
     or jsonb_typeof(bootstrap_input) is distinct from 'object'
     or jsonb_typeof(counts_input) is distinct from 'object'
     or not (window_input ?& array[
       'start_utc','end_utc','prior_development_cutoff_utc','embargo_seconds'
     ])
     or window_input - array[
       'start_utc','end_utc','prior_development_cutoff_utc','embargo_seconds'
     ] <> '{}'::jsonb
     or not (bootstrap_input ?& array['seed','samples','block_length'])
     or bootstrap_input - array['seed','samples','block_length'] <> '{}'::jsonb
     or not (counts_input ?& array[
       'closed_trade','wait','rejected','counterfactual','ambiguous'
     ])
     or counts_input - array[
       'closed_trade','wait','rejected','counterfactual','ambiguous'
     ] <> '{}'::jsonb then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  if jsonb_typeof(window_input->'start_utc') is distinct from 'string'
     or jsonb_typeof(window_input->'end_utc') is distinct from 'string'
     or window_input->>'start_utc' !~ utc_pattern
     or window_input->>'end_utc' !~ utc_pattern
     or jsonb_typeof(window_input->'embargo_seconds') is distinct from 'number'
     or window_input->>'embargo_seconds' !~ integer_pattern
     or (window_input->>'embargo_seconds')::bigint > 31536000
     or (window_input->>'start_utc')::timestamptz >= (window_input->>'end_utc')::timestamptz
     or (window_input->>'end_utc')::timestamptz is distinct from new.data_cutoff
     or (
       new.split = 'train'
       and (
         window_input->'prior_development_cutoff_utc' <> 'null'::jsonb
         or (window_input->>'embargo_seconds')::bigint <> 0
       )
     )
     or (
       new.split <> 'train'
       and (
         jsonb_typeof(window_input->'prior_development_cutoff_utc')
           is distinct from 'string'
         or window_input->>'prior_development_cutoff_utc' !~ utc_pattern
         or (window_input->>'prior_development_cutoff_utc')::timestamptz
              + make_interval(secs => (window_input->>'embargo_seconds')::integer)
            > (window_input->>'start_utc')::timestamptz
       )
     ) then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  if jsonb_typeof(bootstrap_input->'seed') is distinct from 'number'
     or jsonb_typeof(bootstrap_input->'samples') is distinct from 'number'
     or jsonb_typeof(bootstrap_input->'block_length') is distinct from 'number'
     or bootstrap_input->>'seed' !~ '^[1-9][0-9]*$'
     or bootstrap_input->>'samples' !~ '^[1-9][0-9]*$'
     or bootstrap_input->>'block_length' !~ '^[1-9][0-9]*$'
     or (bootstrap_input->>'seed')::numeric > 9223372036854775807
     or (bootstrap_input->>'samples')::integer not between 1000 and 100000
     or (bootstrap_input->>'block_length')::integer > sample_size then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;
  if exists (
    select 1 from jsonb_each(counts_input) item
    where jsonb_typeof(item.value) is distinct from 'number'
       or item.value #>> '{}' !~ integer_pattern
  ) then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;
  closed_count := (counts_input->>'closed_trade')::bigint;
  if closed_count <> sample_size
     or (select sum((item.value #>> '{}')::numeric) from jsonb_each(counts_input) item)
        > 100000 then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  select * into strategy from public.strategy_versions stored
  where stored.owner_id = new.owner_id and stored.id = new.strategy_version_id
  for share;
  if strategy.id is null
     or strategy.version_id is distinct from manifest_input->>'strategy_version'
     or strategy.code_hash is distinct from manifest_input->>'strategy_code_hash'
     or strategy.data_cutoff > new.data_cutoff then
    raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_STRATEGY_DENIED';
  end if;
  if new.experiment_id is not null then
    select * into experiment from public.experiments stored
    where stored.owner_id = new.owner_id and stored.id = new.experiment_id
    for share;
    if experiment.id is null
       or experiment.strategy_version_id is distinct from new.strategy_version_id then
      raise exception using errcode = '23514', message = 'RESEARCH_EVALUATION_EXPERIMENT_DENIED';
    end if;
  end if;
  return new;
end;
$function$;

CREATE TRIGGER research_evaluation_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.evaluations
  FOR EACH ROW EXECUTE FUNCTION sochron_private.guard_research_evaluation();

CREATE OR REPLACE FUNCTION public.sochron_read_research_evaluation(
  p_owner_id uuid,
  p_evaluation_fingerprint text
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
     or p_evaluation_fingerprint is null
     or p_evaluation_fingerprint !~ '^[0-9a-f]{64}$' then
    raise exception using errcode = '22023', message = 'RESEARCH_EVALUATION_READ_INVALID';
  end if;
  select jsonb_build_object(
    'protocol','sochron.research-evaluation-read.v1',
    'found',true,
    'owner_id',stored.owner_id,
    'strategy_version_id',stored.strategy_version_id,
    'experiment_id',stored.experiment_id,
    'evaluation',jsonb_build_object(
      'protocol',stored.evaluation_protocol,
      'producer_revision',stored.producer_revision,
      'evaluation_fingerprint',stored.evaluation_fingerprint,
      'dataset_hash',stored.dataset_hash,
      'strategy_code_hash',stored.evidence_manifest->>'strategy_code_hash',
      'split',stored.split,
      'data_cutoff_utc',to_char(stored.data_cutoff at time zone 'UTC',
        'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
      'metrics',stored.metrics,
      'cost_assumptions',stored.cost_assumptions,
      'evidence_manifest',stored.evidence_manifest
    )
  ) into result
  from public.evaluations stored
  where stored.owner_id = p_owner_id
    and stored.evaluation_fingerprint = p_evaluation_fingerprint;
  return coalesce(result,jsonb_build_object(
    'protocol','sochron.research-evaluation-read.v1',
    'found',false,
    'owner_id',p_owner_id,
    'evaluation_fingerprint',p_evaluation_fingerprint
  ));
end;
$function$;

CREATE OR REPLACE FUNCTION public.sochron_store_research_evaluation(
  p_owner_id uuid,
  p_strategy_version_id bigint,
  p_experiment_id bigint,
  p_evaluation jsonb
)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO ''
  AS $function$
declare
  stored jsonb;
begin
  if p_owner_id is null
     or p_strategy_version_id is null
     or jsonb_typeof(p_evaluation) is distinct from 'object'
     or octet_length(p_evaluation::text) > 262144
     or not (p_evaluation ?& array[
       'protocol','producer_revision','evaluation_fingerprint','dataset_hash',
       'strategy_code_hash','split','data_cutoff_utc','metrics','cost_assumptions',
       'evidence_manifest'
     ])
     or p_evaluation - array[
       'protocol','producer_revision','evaluation_fingerprint','dataset_hash',
       'strategy_code_hash','split','data_cutoff_utc','metrics','cost_assumptions',
       'evidence_manifest'
     ] <> '{}'::jsonb
     or p_evaluation->>'protocol' <> 'sochron.research-evaluation-envelope.v1'
     or p_evaluation->>'producer_revision' <> 'SCN-029/research-evaluation-v1.0.0'
     or p_evaluation->>'evaluation_fingerprint' !~ '^[0-9a-f]{64}$'
     or p_evaluation->>'dataset_hash' !~ '^[0-9a-f]{64}$'
     or p_evaluation->>'strategy_code_hash' !~ '^[0-9a-f]{64}$'
     or p_evaluation->>'split' not in (
       'train','validation','test','walk_forward','shadow_demo'
     )
     or jsonb_typeof(p_evaluation->'data_cutoff_utc') is distinct from 'string'
     or p_evaluation->>'data_cutoff_utc'
        !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,6})?Z$'
     or jsonb_typeof(p_evaluation->'metrics') is distinct from 'object'
     or jsonb_typeof(p_evaluation->'cost_assumptions') is distinct from 'object'
     or jsonb_typeof(p_evaluation->'evidence_manifest') is distinct from 'object'
     or p_evaluation->>'strategy_code_hash' is distinct from
        p_evaluation->'evidence_manifest'->>'strategy_code_hash' then
    raise exception using errcode = '22023', message = 'RESEARCH_EVALUATION_INVALID';
  end if;

  insert into public.evaluations(
    owner_id,strategy_version_id,experiment_id,dataset_hash,split,metrics,
    cost_assumptions,data_cutoff,producer_revision,evaluation_protocol,
    evaluation_fingerprint,evidence_manifest
  ) values (
    p_owner_id,p_strategy_version_id,p_experiment_id,p_evaluation->>'dataset_hash',
    p_evaluation->>'split',p_evaluation->'metrics',p_evaluation->'cost_assumptions',
    (p_evaluation->>'data_cutoff_utc')::timestamptz,
    p_evaluation->>'producer_revision',p_evaluation->>'protocol',
    p_evaluation->>'evaluation_fingerprint',p_evaluation->'evidence_manifest'
  ) on conflict do nothing;

  stored := public.sochron_read_research_evaluation(
    p_owner_id,p_evaluation->>'evaluation_fingerprint'
  );
  if stored->'found' is distinct from 'true'::jsonb
     or (stored->>'strategy_version_id')::bigint is distinct from p_strategy_version_id
     or (
       case when stored->'experiment_id' = 'null'::jsonb then null
            else (stored->>'experiment_id')::bigint end
     ) is distinct from p_experiment_id
     or stored->'evaluation' is distinct from p_evaluation then
    raise exception using errcode = '23505', message = 'RESEARCH_EVALUATION_CONFLICT';
  end if;
  return stored;
end;
$function$;

COMMENT ON COLUMN public.evaluations.evaluation_fingerprint IS
  'Exact immutable identity for an SCN-029 producer envelope; null for legacy rows.';
COMMENT ON COLUMN public.evaluations.evidence_manifest IS
  'Bounded split, uncertainty, disposition and cost provenance for producer rows.';
COMMENT ON FUNCTION public.sochron_store_research_evaluation(uuid,bigint,bigint,jsonb) IS
  'Backend-only insert-or-verify of one research evaluation; no promotion authority.';
COMMENT ON FUNCTION public.sochron_read_research_evaluation(uuid,text) IS
  'Backend-only independent reconciliation read for one evaluation fingerprint.';

REVOKE ALL ON FUNCTION sochron_private.guard_research_evaluation()
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION sochron_private.guard_research_evaluation()
  TO postgres, service_role;
REVOKE ALL ON FUNCTION public.sochron_store_research_evaluation(uuid,bigint,bigint,jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sochron_store_research_evaluation(uuid,bigint,bigint,jsonb)
  TO postgres, service_role;
REVOKE ALL ON FUNCTION public.sochron_read_research_evaluation(uuid,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.sochron_read_research_evaluation(uuid,text)
  TO postgres, service_role;

REVOKE ALL ON TABLE public.evaluations FROM service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.evaluations TO service_role;
