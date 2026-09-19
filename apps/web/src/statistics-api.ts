export const evaluationSplits = ["train", "validation", "test", "walk_forward", "shadow_demo"] as const;
export type EvaluationSplit = typeof evaluationSplits[number];
export type ResearchEvaluation = {
  dataset_hash: string;
  split: EvaluationSplit;
  data_cutoff_utc: string;
  created_at_utc: string;
  metrics: { sample_size: number; wins: number; losses: number; breakeven: number;
    win_rate_pct: string; net_return_pct: string; expectancy_r: string;
    expectancy_r_ci95_low: string; expectancy_r_ci95_high: string;
    max_drawdown_pct: string; profit_factor: string | null };
  cost_assumptions: { spread_points: string; slippage_points: string; commission_per_lot: string;
    swap_included: boolean; operating_cost_per_trade: string; currency: string };
  strategy: { version_id: string; code_hash: string; status: "candidate" | "approved" | "active" | "retired" | "rejected";
    data_cutoff_utc: string };
  experiment: null | { experiment_id: string; status: "draft" | "shadow" | "demo" | "halted" | "closed" | "archived";
    policy_version: string };
};
export type ResearchStatisticsView = {
  trading_mode: "demo"; read_only: true; source: "supabase-evaluations"; read_at_utc: string;
  status: { state: "awaiting_source" | "available"; returned_count: number; limit: 30;
    auto_trading_enabled: false; execution_ready: false; promotion_decided: false };
  evaluations: ResearchEvaluation[];
};

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid statistics evidence");
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, keys: readonly string[]) {
  const actual = Object.keys(value).sort(); const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new Error("Invalid statistics fields");
  }
}
function text(value: unknown, maximum = 128): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum && value.trim().length > 0 &&
    !Array.from(value).some(character => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127);
}
function utc(value: unknown): value is string {
  return text(value, 64) && /(Z|\+00:00)$/.test(value) && Number.isFinite(Date.parse(value));
}
function integer(value: unknown, minimum = 0, maximum = 10_000_000): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum && value <= maximum;
}
function decimal(value: unknown, minimum: number, maximum: number): value is string {
  if (typeof value !== "string" || !/^-?(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)) return false;
  const number = Number(value);
  return Number.isFinite(number) && number >= minimum && number <= maximum;
}
function metrics(value: unknown): ResearchEvaluation["metrics"] {
  const item = object(value);
  exactKeys(item, ["sample_size", "wins", "losses", "breakeven", "win_rate_pct", "net_return_pct", "expectancy_r",
    "expectancy_r_ci95_low", "expectancy_r_ci95_high", "max_drawdown_pct", "profit_factor"]);
  if (!integer(item.sample_size, 1) || !integer(item.wins) || !integer(item.losses) || !integer(item.breakeven) ||
      item.wins + item.losses + item.breakeven !== item.sample_size || !decimal(item.win_rate_pct, 0, 100) ||
      !decimal(item.net_return_pct, -100, 1_000_000) || !decimal(item.expectancy_r, -1_000_000, 1_000_000) ||
      !decimal(item.expectancy_r_ci95_low, -1_000_000, 1_000_000) ||
      !decimal(item.expectancy_r_ci95_high, -1_000_000, 1_000_000) ||
      Number(item.expectancy_r_ci95_low) > Number(item.expectancy_r) || Number(item.expectancy_r) > Number(item.expectancy_r_ci95_high) ||
      !decimal(item.max_drawdown_pct, 0, 100) || (item.profit_factor !== null && !decimal(item.profit_factor, 0, 1_000_000)) ||
      Math.abs(Number(item.win_rate_pct) - item.wins * 100 / item.sample_size) > 0.00011) throw new Error("Invalid research metrics");
  return item as ResearchEvaluation["metrics"];
}
function costs(value: unknown): ResearchEvaluation["cost_assumptions"] {
  const item = object(value);
  exactKeys(item, ["spread_points", "slippage_points", "commission_per_lot", "swap_included", "operating_cost_per_trade", "currency"]);
  if (!decimal(item.spread_points, 0, 1_000_000) || !decimal(item.slippage_points, 0, 1_000_000) ||
      !decimal(item.commission_per_lot, 0, 1_000_000) || typeof item.swap_included !== "boolean" ||
      !decimal(item.operating_cost_per_trade, 0, 1_000_000) || typeof item.currency !== "string" ||
      !/^[A-Z]{3}$/.test(item.currency)) throw new Error("Invalid research costs");
  return item as ResearchEvaluation["cost_assumptions"];
}
function strategy(value: unknown): ResearchEvaluation["strategy"] {
  const item = object(value);
  exactKeys(item, ["version_id", "code_hash", "status", "data_cutoff_utc"]);
  if (!text(item.version_id, 64) || typeof item.code_hash !== "string" || !/^[0-9a-f]{64}$/.test(item.code_hash) ||
      !["candidate", "approved", "active", "retired", "rejected"].includes(String(item.status)) ||
      !utc(item.data_cutoff_utc)) throw new Error("Invalid research strategy");
  return item as ResearchEvaluation["strategy"];
}
function experiment(value: unknown): ResearchEvaluation["experiment"] {
  if (value === null) return null;
  const item = object(value);
  exactKeys(item, ["experiment_id", "status", "policy_version"]);
  if (!text(item.experiment_id) || !["draft", "shadow", "demo", "halted", "closed", "archived"].includes(String(item.status)) ||
      !text(item.policy_version, 64)) throw new Error("Invalid research experiment");
  return item as NonNullable<ResearchEvaluation["experiment"]>;
}
function evaluation(value: unknown): ResearchEvaluation {
  const item = object(value);
  exactKeys(item, ["dataset_hash", "split", "data_cutoff_utc", "created_at_utc", "metrics", "cost_assumptions", "strategy", "experiment"]);
  if (typeof item.dataset_hash !== "string" || !/^[0-9a-f]{64}$/.test(item.dataset_hash) ||
      !evaluationSplits.includes(item.split as EvaluationSplit) || !utc(item.data_cutoff_utc) || !utc(item.created_at_utc) ||
      Date.parse(item.created_at_utc) < Date.parse(item.data_cutoff_utc)) throw new Error("Invalid research evaluation");
  const version = strategy(item.strategy);
  if (Date.parse(version.data_cutoff_utc) > Date.parse(item.data_cutoff_utc)) throw new Error("Invalid research causality");
  return { ...item, metrics: metrics(item.metrics), cost_assumptions: costs(item.cost_assumptions),
    strategy: version, experiment: experiment(item.experiment) } as ResearchEvaluation;
}

export function parseResearchStatistics(value: unknown): ResearchStatisticsView {
  const data = object(value); const status = object(data.status);
  exactKeys(data, ["trading_mode", "read_only", "source", "read_at_utc", "status", "evaluations"]);
  exactKeys(status, ["state", "returned_count", "limit", "auto_trading_enabled", "execution_ready", "promotion_decided"]);
  if (data.trading_mode !== "demo" || data.read_only !== true || data.source !== "supabase-evaluations" || !utc(data.read_at_utc) ||
      !["awaiting_source", "available"].includes(String(status.state)) || !integer(status.returned_count, 0, 30) || status.limit !== 30 ||
      status.auto_trading_enabled !== false || status.execution_ready !== false || status.promotion_decided !== false ||
      !Array.isArray(data.evaluations) || data.evaluations.length > 30 || data.evaluations.length !== status.returned_count) {
    throw new Error("Invalid statistics response");
  }
  const evaluations = data.evaluations.map(evaluation);
  const keys = evaluations.map(item => `${item.strategy.version_id}:${item.dataset_hash}:${item.split}:${item.data_cutoff_utc}`);
  if ((status.state === "awaiting_source") !== (evaluations.length === 0) || new Set(keys).size !== keys.length ||
      evaluations.some((item, index) => index > 0 && Date.parse(evaluations[index - 1].created_at_utc) < Date.parse(item.created_at_utc))) {
    throw new Error("Invalid statistics collection");
  }
  return { ...data, status, evaluations } as ResearchStatisticsView;
}
