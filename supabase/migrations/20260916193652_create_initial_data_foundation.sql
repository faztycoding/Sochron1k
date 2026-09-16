-- SCN-002: synchronized research and audit history.
-- MT5 and the local durable journal remain authoritative for execution state.

create table public.strategy_versions (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  version_id text not null check (length(btrim(version_id)) > 0),
  code_hash text not null check (length(code_hash) >= 32),
  parameters jsonb not null default '{}'::jsonb check (jsonb_typeof(parameters) = 'object'),
  status text not null check (status in ('candidate', 'approved', 'active', 'retired', 'rejected')),
  data_cutoff timestamptz not null,
  created_at timestamptz not null default now(),
  constraint strategy_versions_owner_version_key unique (owner_id, version_id),
  constraint strategy_versions_owner_id_id_key unique (owner_id, id),
  constraint strategy_versions_cutoff_check check (data_cutoff <= created_at)
);

create table public.accounts (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_ref text not null check (length(btrim(account_ref)) > 0),
  server_ref text not null check (length(btrim(server_ref)) > 0),
  account_mode text not null default 'demo' check (account_mode = 'demo'),
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  initial_equity numeric(20, 8) not null check (initial_equity > 0),
  policy_version text not null check (length(btrim(policy_version)) > 0),
  created_at timestamptz not null default now(),
  constraint accounts_owner_ref_key unique (owner_id, account_ref),
  constraint accounts_owner_id_id_key unique (owner_id, id)
);

create table public.experiments (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_id bigint not null,
  strategy_version_id bigint not null,
  experiment_id text not null check (length(btrim(experiment_id)) > 0),
  status text not null check (status in ('draft', 'shadow', 'demo', 'halted', 'closed', 'archived')),
  initial_equity numeric(20, 8) not null check (initial_equity > 0),
  policy_version text not null check (length(btrim(policy_version)) > 0),
  started_at timestamptz,
  ended_at timestamptz,
  created_at timestamptz not null default now(),
  constraint experiments_owner_account_fkey foreign key (owner_id, account_id)
    references public.accounts (owner_id, id),
  constraint experiments_owner_strategy_fkey foreign key (owner_id, strategy_version_id)
    references public.strategy_versions (owner_id, id),
  constraint experiments_owner_external_key unique (owner_id, experiment_id),
  constraint experiments_owner_id_id_key unique (owner_id, id),
  constraint experiments_time_check check (
    (started_at is null or started_at >= created_at)
    and (ended_at is null or (started_at is not null and ended_at >= started_at))
  )
);

create table public.bars (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  feed_id text not null check (length(btrim(feed_id)) > 0),
  source_revision text not null check (length(btrim(source_revision)) > 0),
  symbol text not null check (length(btrim(symbol)) > 0),
  timeframe text not null check (timeframe in ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1')),
  event_time timestamptz not null,
  received_at timestamptz not null,
  available_at timestamptz not null,
  open_price numeric(20, 8) not null check (open_price > 0),
  high_price numeric(20, 8) not null check (high_price > 0),
  low_price numeric(20, 8) not null check (low_price > 0),
  close_price numeric(20, 8) not null check (close_price > 0),
  tick_volume numeric(20, 8) check (tick_volume is null or tick_volume >= 0),
  created_at timestamptz not null default now(),
  constraint bars_owner_source_key unique (
    owner_id, feed_id, symbol, timeframe, event_time, source_revision
  ),
  constraint bars_price_range_check check (
    high_price >= greatest(open_price, close_price, low_price)
    and low_price <= least(open_price, close_price, high_price)
  ),
  constraint bars_time_check check (received_at >= event_time and available_at >= event_time)
);

create table public.feature_snapshots (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  strategy_version_id bigint not null,
  snapshot_id text not null check (length(btrim(snapshot_id)) > 0),
  feed_id text not null check (length(btrim(feed_id)) > 0),
  symbol text not null check (length(btrim(symbol)) > 0),
  timeframe text not null check (timeframe in ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1')),
  event_time timestamptz not null,
  received_at timestamptz not null,
  available_at timestamptz not null,
  values jsonb not null check (jsonb_typeof(values) = 'object'),
  dataset_hash text not null check (length(dataset_hash) >= 32),
  created_at timestamptz not null default now(),
  constraint feature_snapshots_owner_strategy_fkey foreign key (owner_id, strategy_version_id)
    references public.strategy_versions (owner_id, id),
  constraint feature_snapshots_owner_external_key unique (owner_id, snapshot_id),
  constraint feature_snapshots_time_check check (
    received_at >= event_time and available_at >= event_time and created_at >= available_at
  )
);

create table public.signals (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  experiment_id bigint not null,
  strategy_version_id bigint not null,
  signal_id text not null check (length(btrim(signal_id)) > 0),
  setup_id text not null check (length(btrim(setup_id)) > 0),
  action text not null check (action in ('buy', 'sell', 'wait', 'block')),
  formed_at timestamptz not null,
  confirmed_at timestamptz not null,
  expires_at timestamptz not null,
  evidence_ids jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence_ids) = 'array'),
  blocked_reason text,
  created_at timestamptz not null default now(),
  constraint signals_owner_experiment_fkey foreign key (owner_id, experiment_id)
    references public.experiments (owner_id, id),
  constraint signals_owner_strategy_fkey foreign key (owner_id, strategy_version_id)
    references public.strategy_versions (owner_id, id),
  constraint signals_owner_external_key unique (owner_id, signal_id),
  constraint signals_owner_id_id_key unique (owner_id, id),
  constraint signals_time_check check (
    confirmed_at >= formed_at and expires_at > confirmed_at and created_at >= confirmed_at
  ),
  constraint signals_block_reason_check check (
    (action = 'block' and blocked_reason is not null)
    or (action <> 'block')
  )
);

create table public.commands (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_id bigint not null,
  experiment_id bigint not null,
  signal_id bigint,
  command_id text not null check (length(btrim(command_id)) > 0),
  idempotency_key text not null check (length(btrim(idempotency_key)) > 0),
  request_fingerprint text not null check (length(request_fingerprint) >= 32),
  intent text not null check (intent in ('open', 'close', 'cancel', 'reconcile')),
  symbol text not null check (length(btrim(symbol)) > 0),
  side text check (side in ('buy', 'sell')),
  requested_price numeric(20, 8) check (requested_price is null or requested_price > 0),
  requested_volume numeric(20, 8) check (requested_volume is null or requested_volume > 0),
  state text not null check (state in (
    'created', 'validated', 'queued', 'sent', 'acknowledged', 'partially_filled',
    'filled', 'closed', 'rejected', 'expired', 'cancelled', 'unknown'
  )),
  expires_at timestamptz,
  created_at timestamptz not null,
  received_at timestamptz not null,
  updated_at timestamptz not null,
  constraint commands_owner_account_fkey foreign key (owner_id, account_id)
    references public.accounts (owner_id, id),
  constraint commands_owner_experiment_fkey foreign key (owner_id, experiment_id)
    references public.experiments (owner_id, id),
  constraint commands_owner_signal_fkey foreign key (owner_id, signal_id)
    references public.signals (owner_id, id),
  constraint commands_owner_external_key unique (owner_id, command_id),
  constraint commands_owner_idempotency_key unique (owner_id, idempotency_key),
  constraint commands_owner_id_id_key unique (owner_id, id),
  constraint commands_time_check check (
    received_at >= created_at and updated_at >= received_at
    and (expires_at is null or expires_at > created_at)
  ),
  constraint commands_open_fields_check check (
    intent <> 'open'
    or (side is not null and requested_price is not null and requested_volume is not null)
  )
);

create table public.orders (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  command_id bigint not null,
  mt5_ticket text not null check (length(btrim(mt5_ticket)) > 0),
  requested_price numeric(20, 8) check (requested_price is null or requested_price > 0),
  state text not null check (state in (
    'submitted', 'placed', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired', 'unknown'
  )),
  event_time timestamptz not null,
  received_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint orders_owner_command_fkey foreign key (owner_id, command_id)
    references public.commands (owner_id, id),
  constraint orders_owner_ticket_key unique (owner_id, mt5_ticket),
  constraint orders_owner_id_id_key unique (owner_id, id),
  constraint orders_time_check check (received_at >= event_time and created_at >= received_at)
);

create table public.positions (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_id bigint not null,
  experiment_id bigint not null,
  position_id text not null check (length(btrim(position_id)) > 0),
  symbol text not null check (length(btrim(symbol)) > 0),
  side text not null check (side in ('buy', 'sell')),
  volume numeric(20, 8) not null check (volume > 0),
  average_entry numeric(20, 8) not null check (average_entry > 0),
  broker_sl numeric(20, 8) check (broker_sl is null or broker_sl > 0),
  take_profit numeric(20, 8) check (take_profit is null or take_profit > 0),
  state text not null check (state in ('open', 'closed', 'unknown')),
  opened_at timestamptz not null,
  closed_at timestamptz,
  close_reason text,
  event_time timestamptz not null,
  received_at timestamptz not null,
  updated_at timestamptz not null,
  constraint positions_owner_account_fkey foreign key (owner_id, account_id)
    references public.accounts (owner_id, id),
  constraint positions_owner_experiment_fkey foreign key (owner_id, experiment_id)
    references public.experiments (owner_id, id),
  constraint positions_owner_external_key unique (owner_id, position_id),
  constraint positions_owner_id_id_key unique (owner_id, id),
  constraint positions_time_check check (
    received_at >= event_time and updated_at >= received_at
    and (closed_at is null or closed_at >= opened_at)
  ),
  constraint positions_closed_fields_check check (
    (state = 'closed' and closed_at is not null and close_reason is not null)
    or (state <> 'closed' and closed_at is null)
  )
);

create table public.deals (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  command_id bigint not null,
  order_id bigint not null,
  position_id bigint not null,
  deal_id text not null check (length(btrim(deal_id)) > 0),
  side text not null check (side in ('buy', 'sell')),
  volume numeric(20, 8) not null check (volume > 0),
  fill_price numeric(20, 8) not null check (fill_price > 0),
  gross_pnl numeric(20, 8) not null default 0,
  commission numeric(20, 8) not null default 0,
  swap numeric(20, 8) not null default 0,
  fees numeric(20, 8) not null default 0,
  account_currency text not null check (account_currency ~ '^[A-Z]{3}$'),
  event_time timestamptz not null,
  received_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint deals_owner_command_fkey foreign key (owner_id, command_id)
    references public.commands (owner_id, id),
  constraint deals_owner_order_fkey foreign key (owner_id, order_id)
    references public.orders (owner_id, id),
  constraint deals_owner_position_fkey foreign key (owner_id, position_id)
    references public.positions (owner_id, id),
  constraint deals_owner_external_key unique (owner_id, deal_id),
  constraint deals_time_check check (received_at >= event_time and created_at >= received_at)
);

create table public.equity_snapshots (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_id bigint not null,
  equity numeric(20, 8) not null check (equity >= 0),
  balance numeric(20, 8) not null check (balance >= 0),
  daily_baseline numeric(20, 8) not null check (daily_baseline > 0),
  total_baseline numeric(20, 8) not null check (total_baseline > 0),
  account_currency text not null check (account_currency ~ '^[A-Z]{3}$'),
  event_time timestamptz not null,
  received_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint equity_snapshots_owner_account_fkey foreign key (owner_id, account_id)
    references public.accounts (owner_id, id),
  constraint equity_snapshots_source_key unique (owner_id, account_id, event_time, received_at),
  constraint equity_snapshots_time_check check (received_at >= event_time and created_at >= received_at)
);

create table public.account_cash_flows (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_id bigint not null,
  mt5_deal_id text not null check (length(btrim(mt5_deal_id)) > 0),
  flow_type text not null check (flow_type in ('deposit', 'withdrawal', 'adjustment')),
  amount numeric(20, 8) not null check (amount <> 0),
  account_currency text not null check (account_currency ~ '^[A-Z]{3}$'),
  event_time timestamptz not null,
  received_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint account_cash_flows_owner_account_fkey foreign key (owner_id, account_id)
    references public.accounts (owner_id, id),
  constraint account_cash_flows_owner_deal_key unique (owner_id, mt5_deal_id),
  constraint account_cash_flows_time_check check (received_at >= event_time and created_at >= received_at)
);

create table public.risk_events (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  account_id bigint not null,
  experiment_id bigint not null,
  event_type text not null check (event_type in (
    'daily_halt', 'total_halt', 'entry_blocked', 'recovery_lock', 'halt_release_recorded'
  )),
  reason text not null check (length(btrim(reason)) > 0),
  state_snapshot jsonb not null check (jsonb_typeof(state_snapshot) = 'object'),
  actor_type text not null check (actor_type in ('system', 'owner', 'executor')),
  actor_id text,
  event_time timestamptz not null,
  received_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint risk_events_owner_account_fkey foreign key (owner_id, account_id)
    references public.accounts (owner_id, id),
  constraint risk_events_owner_experiment_fkey foreign key (owner_id, experiment_id)
    references public.experiments (owner_id, id),
  constraint risk_events_time_check check (received_at >= event_time and created_at >= received_at),
  constraint risk_events_release_actor_check check (
    event_type <> 'halt_release_recorded' or actor_type = 'owner'
  )
);

create table public.news_items (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  source text not null check (length(btrim(source)) > 0),
  source_item_id text not null check (length(btrim(source_item_id)) > 0),
  revision text not null check (length(btrim(revision)) > 0),
  published_at timestamptz not null,
  received_at timestamptz not null,
  content_hash text not null check (length(content_hash) >= 32),
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
  created_at timestamptz not null default now(),
  constraint news_items_owner_source_key unique (owner_id, source, source_item_id, revision),
  constraint news_items_time_check check (received_at >= published_at and created_at >= received_at)
);

create table public.ai_runs (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  experiment_id bigint,
  source text not null check (length(btrim(source)) > 0),
  source_revision text not null check (length(btrim(source_revision)) > 0),
  model text not null check (length(btrim(model)) > 0),
  requested_at timestamptz not null,
  completed_at timestamptz,
  input_tokens bigint check (input_tokens is null or input_tokens >= 0),
  output_tokens bigint check (output_tokens is null or output_tokens >= 0),
  cost numeric(20, 8) check (cost is null or cost >= 0),
  cost_currency text check (cost_currency is null or cost_currency ~ '^[A-Z]{3}$'),
  output_schema text not null check (length(btrim(output_schema)) > 0),
  output jsonb,
  state text not null check (state in ('requested', 'completed', 'failed', 'timed_out', 'invalid')),
  created_at timestamptz not null default now(),
  constraint ai_runs_owner_experiment_fkey foreign key (owner_id, experiment_id)
    references public.experiments (owner_id, id),
  constraint ai_runs_time_check check (
    created_at >= requested_at and (completed_at is null or completed_at >= requested_at)
  ),
  constraint ai_runs_cost_currency_check check ((cost is null) = (cost_currency is null))
);

create table public.evaluations (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  strategy_version_id bigint not null,
  experiment_id bigint,
  dataset_hash text not null check (length(dataset_hash) >= 32),
  split text not null check (split in ('train', 'validation', 'test', 'walk_forward', 'shadow_demo')),
  metrics jsonb not null check (jsonb_typeof(metrics) = 'object'),
  cost_assumptions jsonb not null check (jsonb_typeof(cost_assumptions) = 'object'),
  data_cutoff timestamptz not null,
  created_at timestamptz not null default now(),
  constraint evaluations_owner_strategy_fkey foreign key (owner_id, strategy_version_id)
    references public.strategy_versions (owner_id, id),
  constraint evaluations_owner_experiment_fkey foreign key (owner_id, experiment_id)
    references public.experiments (owner_id, id),
  constraint evaluations_source_key unique (
    owner_id, strategy_version_id, dataset_hash, split, data_cutoff
  ),
  constraint evaluations_time_check check (created_at >= data_cutoff)
);

create table public.audit_events (
  id bigint generated always as identity primary key,
  owner_id uuid not null references auth.users (id),
  actor_type text not null check (actor_type in ('owner', 'api', 'worker', 'executor', 'system')),
  actor_id text,
  action text not null check (length(btrim(action)) > 0),
  entity_type text not null check (length(btrim(entity_type)) > 0),
  entity_id text not null check (length(btrim(entity_id)) > 0),
  before_state jsonb,
  after_state jsonb,
  event_time timestamptz not null,
  received_at timestamptz not null,
  created_at timestamptz not null default now(),
  constraint audit_events_state_check check (before_state is not null or after_state is not null),
  constraint audit_events_time_check check (received_at >= event_time and created_at >= received_at)
);

-- RLS predicates and common owner-scoped query paths use these indexes.
create index experiments_owner_account_idx on public.experiments (owner_id, account_id);
create index experiments_owner_strategy_idx on public.experiments (owner_id, strategy_version_id);
create index bars_owner_event_idx on public.bars (owner_id, event_time desc);
create index feature_snapshots_owner_strategy_idx
  on public.feature_snapshots (owner_id, strategy_version_id, available_at desc);
create index signals_owner_experiment_idx on public.signals (owner_id, experiment_id, confirmed_at desc);
create index signals_owner_strategy_idx on public.signals (owner_id, strategy_version_id);
create index commands_owner_account_idx on public.commands (owner_id, account_id, created_at desc);
create index commands_owner_experiment_idx on public.commands (owner_id, experiment_id, created_at desc);
create index commands_owner_signal_idx on public.commands (owner_id, signal_id) where signal_id is not null;
create index commands_unresolved_idx on public.commands (owner_id, updated_at)
  where state in ('sent', 'acknowledged', 'partially_filled', 'unknown');
create index orders_owner_command_idx on public.orders (owner_id, command_id, event_time desc);
create index positions_owner_account_idx on public.positions (owner_id, account_id, event_time desc);
create index positions_owner_experiment_idx on public.positions (owner_id, experiment_id, event_time desc);
create index positions_open_idx on public.positions (owner_id, account_id)
  where state in ('open', 'unknown');
create index deals_owner_command_idx on public.deals (owner_id, command_id, event_time desc);
create index deals_owner_order_idx on public.deals (owner_id, order_id);
create index deals_owner_position_idx on public.deals (owner_id, position_id, event_time);
create index equity_snapshots_owner_account_idx
  on public.equity_snapshots (owner_id, account_id, event_time desc);
create index account_cash_flows_owner_account_idx
  on public.account_cash_flows (owner_id, account_id, event_time desc);
create index risk_events_owner_account_idx on public.risk_events (owner_id, account_id, event_time desc);
create index risk_events_owner_experiment_idx
  on public.risk_events (owner_id, experiment_id, event_time desc);
create index news_items_owner_received_idx on public.news_items (owner_id, received_at desc);
create index ai_runs_owner_experiment_idx on public.ai_runs (owner_id, experiment_id, requested_at desc);
create index ai_runs_owner_requested_idx on public.ai_runs (owner_id, requested_at desc);
create index evaluations_owner_strategy_idx
  on public.evaluations (owner_id, strategy_version_id, created_at desc);
create index evaluations_owner_experiment_idx
  on public.evaluations (owner_id, experiment_id) where experiment_id is not null;
create index audit_events_owner_event_idx on public.audit_events (owner_id, event_time desc);
create index audit_events_owner_entity_idx on public.audit_events (owner_id, entity_type, entity_id);

-- Public is an exposed schema. Access requires both an explicit grant and an owner policy.
revoke all on table
  public.strategy_versions,
  public.accounts,
  public.experiments,
  public.bars,
  public.feature_snapshots,
  public.signals,
  public.commands,
  public.orders,
  public.positions,
  public.deals,
  public.equity_snapshots,
  public.account_cash_flows,
  public.risk_events,
  public.news_items,
  public.ai_runs,
  public.evaluations,
  public.audit_events
from anon, authenticated;

grant select on table
  public.strategy_versions,
  public.accounts,
  public.experiments,
  public.bars,
  public.feature_snapshots,
  public.signals,
  public.commands,
  public.orders,
  public.positions,
  public.deals,
  public.equity_snapshots,
  public.account_cash_flows,
  public.risk_events,
  public.news_items,
  public.ai_runs,
  public.evaluations,
  public.audit_events
to authenticated;

grant select, insert, update, delete on table
  public.strategy_versions,
  public.accounts,
  public.experiments,
  public.bars,
  public.feature_snapshots,
  public.signals,
  public.commands,
  public.orders,
  public.positions,
  public.deals,
  public.equity_snapshots,
  public.account_cash_flows,
  public.risk_events,
  public.news_items,
  public.ai_runs,
  public.evaluations,
  public.audit_events
to service_role;

grant usage, select on all sequences in schema public to service_role;

alter table public.strategy_versions enable row level security;
alter table public.strategy_versions force row level security;
alter table public.accounts enable row level security;
alter table public.accounts force row level security;
alter table public.experiments enable row level security;
alter table public.experiments force row level security;
alter table public.bars enable row level security;
alter table public.bars force row level security;
alter table public.feature_snapshots enable row level security;
alter table public.feature_snapshots force row level security;
alter table public.signals enable row level security;
alter table public.signals force row level security;
alter table public.commands enable row level security;
alter table public.commands force row level security;
alter table public.orders enable row level security;
alter table public.orders force row level security;
alter table public.positions enable row level security;
alter table public.positions force row level security;
alter table public.deals enable row level security;
alter table public.deals force row level security;
alter table public.equity_snapshots enable row level security;
alter table public.equity_snapshots force row level security;
alter table public.account_cash_flows enable row level security;
alter table public.account_cash_flows force row level security;
alter table public.risk_events enable row level security;
alter table public.risk_events force row level security;
alter table public.news_items enable row level security;
alter table public.news_items force row level security;
alter table public.ai_runs enable row level security;
alter table public.ai_runs force row level security;
alter table public.evaluations enable row level security;
alter table public.evaluations force row level security;
alter table public.audit_events enable row level security;
alter table public.audit_events force row level security;

create policy strategy_versions_owner_select on public.strategy_versions
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy accounts_owner_select on public.accounts
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy experiments_owner_select on public.experiments
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy bars_owner_select on public.bars
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy feature_snapshots_owner_select on public.feature_snapshots
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy signals_owner_select on public.signals
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy commands_owner_select on public.commands
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy orders_owner_select on public.orders
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy positions_owner_select on public.positions
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy deals_owner_select on public.deals
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy equity_snapshots_owner_select on public.equity_snapshots
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy account_cash_flows_owner_select on public.account_cash_flows
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy risk_events_owner_select on public.risk_events
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy news_items_owner_select on public.news_items
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy ai_runs_owner_select on public.ai_runs
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy evaluations_owner_select on public.evaluations
  for select to authenticated using ((select auth.uid()) = owner_id);
create policy audit_events_owner_select on public.audit_events
  for select to authenticated using ((select auth.uid()) = owner_id);

comment on schema public is
  'Sochron1k synchronized history; MT5 and the local journal remain execution authorities.';
