export const alertKinds = [
  "order_reject", "no_sl", "risk_halt", "unknown_execution", "stale_price",
  "bridge_disconnected", "storage_limit", "api_budget",
] as const;

export type AlertKind = typeof alertKinds[number];
export type AlertSource = "telemetry_bridge" | "execution_bridge" | "execution_journal" |
  "policy_writer" | "bar_history" | "api_budget";
export type CoverageRuntime = "connected" | "awaiting_configuration" | "awaiting_source" | "degraded";
export type LifecycleState = "active" | "acknowledged" | "cleared" | "resolved" | "unavailable";
export type LifecycleRuntime = "awaiting_configuration" | "connected" | "degraded";
export type ApiBudgetState = "disabled" | "awaiting_snapshot" | "connected" | "warning" |
  "critical" | "exhausted" | "stale" | "degraded";

export type ApiBudgetView = {
  protocol: "sochron.api-budget-view.v1"; trading_mode: "demo"; read_only: true;
  auto_trading_enabled: false; execution_ready: false; state: ApiBudgetState;
  generated_at_utc: string;
  policy: null | { currency: string; monthly_limit: string; warning_fraction: string;
    critical_fraction: string; stale_after_seconds: number };
  evidence: null | { source_ref: string; period_start_utc: string; period_end_utc: string;
    observed_at_utc: string; coverage_until_utc: string; billed_cost: string;
    unbilled_estimate: string; total_cost: string; remaining_amount: string;
    usage_percent: string };
};

export type OperationalAlert = {
  id: string; condition_id: string; kind: AlertKind; severity: "critical" | "warning" | "info";
  source: AlertSource; source_ref: string; detail_code: string; observed_at_utc: string;
  evidence_routes: string[]; lifecycle_state: LifecycleState; acknowledge_allowed: boolean;
  resolve_allowed: boolean; acknowledged_by: "owner" | null; acknowledged_at_utc: string | null;
  resolved_at_utc: string | null;
};
export type AlertCoverage = { kind: AlertKind; implementation: "available" | "missing";
  runtime: CoverageRuntime; api_routes: string[]; sources: AlertSource[] };
export type OperationalAlertInventory = {
  protocol: "sochron.operational-alerts.v3"; trading_mode: "demo"; read_only: true;
  auto_trading_enabled: false; execution_ready: false; delivery_configured: false;
  lifecycle_runtime: LifecycleRuntime; lifecycle_mutations_enabled: boolean;
  status: "partial" | "degraded"; generated_at_utc: string; truncated: boolean;
  api_budget: ApiBudgetView; alerts: OperationalAlert[]; coverage: AlertCoverage[];
};

export type AlertMutationReceipt = {
  protocol: "sochron.alert-mutation.v1"; action: "acknowledge" | "resolve";
  condition_id: string; lifecycle_state: "acknowledged" | "resolved";
  acknowledged_at_utc: string; resolved_at_utc: string | null;
};

type AlertDefinition = { title: string; routes: string[]; sources: AlertSource[];
  sourceLabel: string; implementation: "available" | "missing" };

export const alertDefinitions: Record<AlertKind, AlertDefinition> = {
  order_reject: { title: "คำสั่งถูกปฏิเสธ", routes: ["/api/owner/alerts", "/api/owner/execution"],
    sources: ["execution_journal"], sourceLabel: "Execution journal", implementation: "available" },
  no_sl: { title: "สถานะยังไม่มี SL ยืนยัน", routes: ["/api/owner/alerts", "/api/owner/execution"],
    sources: ["execution_journal"], sourceLabel: "Execution journal + broker SL evidence", implementation: "available" },
  risk_halt: { title: "Risk halt ทำงาน", routes: ["/api/owner/alerts", "/api/owner/execution"],
    sources: ["execution_journal"], sourceLabel: "Durable risk state", implementation: "available" },
  unknown_execution: { title: "ผลคำสั่งเป็น UNKNOWN", routes: ["/api/owner/alerts", "/api/owner/execution"],
    sources: ["execution_journal"], sourceLabel: "Execution journal reconciliation state", implementation: "available" },
  stale_price: { title: "ราคาหรือ heartbeat เก่า", routes: ["/api/owner/alerts", "/api/owner/telemetry"],
    sources: ["telemetry_bridge"], sourceLabel: "MT5 telemetry status", implementation: "available" },
  bridge_disconnected: { title: "Bridge / source ใช้งานไม่ได้",
    routes: ["/api/owner/alerts", "/api/owner/telemetry", "/api/executor/v1/status", "/api/policy/v1/status", "/api/owner/api-budget"],
    sources: ["telemetry_bridge", "execution_bridge", "policy_writer", "api_budget"],
    sourceLabel: "Telemetry + execution + policy + budget status", implementation: "available" },
  storage_limit: { title: "พื้นที่คลังใกล้เพดาน", routes: ["/api/owner/alerts", "/api/owner/history/{timeframe}"],
    sources: ["bar_history"], sourceLabel: "Local bar archive page usage", implementation: "available" },
  api_budget: { title: "งบ API ใกล้เพดาน", routes: ["/api/owner/alerts", "/api/owner/api-budget"],
    sources: ["api_budget"], sourceLabel: "Provider billing collector → private normalized snapshot", implementation: "available" },
};

const alertKeys = ["id", "condition_id", "kind", "severity", "source", "source_ref", "detail_code",
  "observed_at_utc", "evidence_routes", "lifecycle_state", "acknowledge_allowed", "resolve_allowed",
  "acknowledged_by", "acknowledged_at_utc", "resolved_at_utc"];
const coverageKeys = ["kind", "implementation", "runtime", "api_routes", "sources"];
const inventoryKeys = ["protocol", "trading_mode", "read_only", "auto_trading_enabled", "execution_ready",
  "delivery_configured", "lifecycle_runtime", "lifecycle_mutations_enabled", "status", "generated_at_utc",
  "truncated", "api_budget", "alerts", "coverage"];
const receiptKeys = ["protocol", "action", "condition_id", "lifecycle_state", "acknowledged_at_utc",
  "resolved_at_utc"];
const runtimes = new Set<CoverageRuntime>(["connected", "awaiting_configuration", "awaiting_source", "degraded"]);
const lifecycleStates = new Set<LifecycleState>(["active", "acknowledged", "cleared", "resolved", "unavailable"]);
const lifecycleRuntimes = new Set<LifecycleRuntime>(["awaiting_configuration", "connected", "degraded"]);
const severities = new Set(["critical", "warning", "info"]);
const sourceRoutes: Record<AlertSource, string[]> = {
  telemetry_bridge: ["/api/owner/telemetry"], execution_bridge: ["/api/executor/v1/status"],
  execution_journal: ["/api/owner/execution"], policy_writer: ["/api/policy/v1/status"],
  bar_history: ["/api/owner/history/{timeframe}"], api_budget: ["/api/owner/api-budget"],
};
const details = new Set([
  "entry_rejected", "management_rejected", "entry_unknown", "management_unknown",
  "open_volume_without_confirmed_sl", "daily_halt", "total_halt", "daily_and_total_halt",
  "price_or_heartbeat_stale", "telemetry_stale", "telemetry_rejected", "execution_stale",
  "execution_rejected", "policy_writer_degraded", "execution_journal_unavailable",
  "bar_history_unavailable", "warning_70", "warning_85",
  "api_budget_warning", "api_budget_critical", "api_budget_exhausted",
  "api_budget_stale", "api_budget_degraded",
]);
const detailRules: Record<string, { kind: AlertKind; source: AlertSource; severity: "critical" | "warning" }> = {
  entry_rejected: { kind: "order_reject", source: "execution_journal", severity: "warning" },
  management_rejected: { kind: "order_reject", source: "execution_journal", severity: "warning" },
  entry_unknown: { kind: "unknown_execution", source: "execution_journal", severity: "critical" },
  management_unknown: { kind: "unknown_execution", source: "execution_journal", severity: "critical" },
  open_volume_without_confirmed_sl: { kind: "no_sl", source: "execution_journal", severity: "critical" },
  daily_halt: { kind: "risk_halt", source: "execution_journal", severity: "critical" },
  total_halt: { kind: "risk_halt", source: "execution_journal", severity: "critical" },
  daily_and_total_halt: { kind: "risk_halt", source: "execution_journal", severity: "critical" },
  price_or_heartbeat_stale: { kind: "stale_price", source: "telemetry_bridge", severity: "critical" },
  telemetry_stale: { kind: "bridge_disconnected", source: "telemetry_bridge", severity: "critical" },
  telemetry_rejected: { kind: "bridge_disconnected", source: "telemetry_bridge", severity: "critical" },
  execution_stale: { kind: "bridge_disconnected", source: "execution_bridge", severity: "critical" },
  execution_rejected: { kind: "bridge_disconnected", source: "execution_bridge", severity: "critical" },
  policy_writer_degraded: { kind: "bridge_disconnected", source: "policy_writer", severity: "warning" },
  execution_journal_unavailable: { kind: "bridge_disconnected", source: "execution_journal", severity: "critical" },
  bar_history_unavailable: { kind: "bridge_disconnected", source: "bar_history", severity: "warning" },
  warning_70: { kind: "storage_limit", source: "bar_history", severity: "warning" },
  warning_85: { kind: "storage_limit", source: "bar_history", severity: "warning" },
  api_budget_warning: { kind: "api_budget", source: "api_budget", severity: "warning" },
  api_budget_critical: { kind: "api_budget", source: "api_budget", severity: "critical" },
  api_budget_exhausted: { kind: "api_budget", source: "api_budget", severity: "critical" },
  api_budget_stale: { kind: "bridge_disconnected", source: "api_budget", severity: "warning" },
  api_budget_degraded: { kind: "bridge_disconnected", source: "api_budget", severity: "warning" },
};
const severityOrder = { critical: 0, warning: 1, info: 2 } as const;
const lifecycleOrder = { active: 0, acknowledged: 1, cleared: 2, unavailable: 3, resolved: 4 } as const;

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid alert inventory");
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, expected: string[]) {
  const keys = Object.keys(value).sort();
  if (keys.length !== expected.length || keys.some((key, index) => key !== [...expected].sort()[index])) {
    throw new Error("Invalid alert fields");
  }
}
function exactStrings(value: unknown, expected: readonly string[]): value is string[] {
  return Array.isArray(value) && value.length === expected.length && value.every((item, index) => item === expected[index]);
}
function utc(value: unknown): value is string {
  return typeof value === "string" && value.length <= 64 && /(Z|\+00:00)$/.test(value) && Number.isFinite(Date.parse(value));
}

type ExactDecimal = { units: bigint; scale: number };
function exactDecimal(value: unknown): ExactDecimal | null {
  if (typeof value !== "string" || !/^(0|[1-9][0-9]{0,20})(\.[0-9]{1,8})?$/.test(value)) return null;
  const [whole, fraction = ""] = value.split(".");
  return { units: BigInt(whole + fraction), scale: fraction.length };
}
function rescale(value: ExactDecimal, scale: number): bigint {
  return value.units * 10n ** BigInt(scale - value.scale);
}
function compare(left: ExactDecimal, right: ExactDecimal): number {
  const scale = Math.max(left.scale, right.scale);
  const difference = rescale(left, scale) - rescale(right, scale);
  return difference < 0n ? -1 : difference > 0n ? 1 : 0;
}
function sum(left: ExactDecimal, right: ExactDecimal): ExactDecimal {
  const scale = Math.max(left.scale, right.scale);
  return { units: rescale(left, scale) + rescale(right, scale), scale };
}
function product(left: ExactDecimal, right: ExactDecimal): ExactDecimal {
  return { units: left.units * right.units, scale: left.scale + right.scale };
}
function difference(left: ExactDecimal, right: ExactDecimal): ExactDecimal {
  const scale = Math.max(left.scale, right.scale);
  return { units: rescale(left, scale) - rescale(right, scale), scale };
}

const budgetKeys = ["protocol", "trading_mode", "read_only", "auto_trading_enabled", "execution_ready",
  "state", "generated_at_utc", "policy", "evidence"];
const budgetPolicyKeys = ["currency", "monthly_limit", "warning_fraction", "critical_fraction",
  "stale_after_seconds"];
const budgetEvidenceKeys = ["source_ref", "period_start_utc", "period_end_utc", "observed_at_utc",
  "coverage_until_utc", "billed_cost", "unbilled_estimate", "total_cost", "remaining_amount",
  "usage_percent"];
const budgetStates = new Set<ApiBudgetState>([
  "disabled", "awaiting_snapshot", "connected", "warning", "critical", "exhausted", "stale", "degraded",
]);

export function parseApiBudget(value: unknown): ApiBudgetView {
  const data = object(value); exactKeys(data, budgetKeys);
  if (data.protocol !== "sochron.api-budget-view.v1" || data.trading_mode !== "demo" ||
      data.read_only !== true || data.auto_trading_enabled !== false || data.execution_ready !== false ||
      !budgetStates.has(data.state as ApiBudgetState) || !utc(data.generated_at_utc) ||
      !(data.policy === null || (typeof data.policy === "object" && !Array.isArray(data.policy))) ||
      !(data.evidence === null || (typeof data.evidence === "object" && !Array.isArray(data.evidence)))) {
    throw new Error("Invalid API budget view");
  }
  if ((data.state === "disabled") !== (data.policy === null) ||
      (data.policy === null && data.evidence !== null) ||
      (data.state === "awaiting_snapshot" && data.evidence !== null) ||
      (["connected", "warning", "critical", "exhausted", "stale"].includes(String(data.state)) &&
        (data.policy === null || data.evidence === null)) ||
      (data.state === "degraded" && data.policy === null)) throw new Error("Invalid API budget state");
  if (data.policy === null) return data as ApiBudgetView;

  const policy = object(data.policy); exactKeys(policy, budgetPolicyKeys);
  const limit = exactDecimal(policy.monthly_limit), warning = exactDecimal(policy.warning_fraction);
  const critical = exactDecimal(policy.critical_fraction), one = exactDecimal("1");
  if (typeof policy.currency !== "string" || !/^[A-Z]{3,8}$/.test(policy.currency) ||
      !limit || !warning || !critical || !one || compare(limit, exactDecimal("0")!) <= 0 ||
      compare(warning, exactDecimal("0")!) <= 0 || compare(warning, critical) >= 0 ||
      compare(critical, one) > 0 || typeof policy.stale_after_seconds !== "number" ||
      !Number.isSafeInteger(policy.stale_after_seconds) || policy.stale_after_seconds < 60 ||
      policy.stale_after_seconds > 604800) {
    throw new Error("Invalid API budget policy");
  }
  if (data.evidence === null) return data as ApiBudgetView;
  const evidence = object(data.evidence); exactKeys(evidence, budgetEvidenceKeys);
  const billed = exactDecimal(evidence.billed_cost), unbilled = exactDecimal(evidence.unbilled_estimate);
  const total = exactDecimal(evidence.total_cost), remaining = exactDecimal(evidence.remaining_amount);
  const usage = exactDecimal(evidence.usage_percent);
  const times = [evidence.period_start_utc, evidence.period_end_utc, evidence.observed_at_utc,
    evidence.coverage_until_utc];
  if (typeof evidence.source_ref !== "string" || !/^[0-9a-f]{16}$/.test(evidence.source_ref) ||
      times.some(item => !utc(item)) || !billed || !unbilled || !total || !remaining || !usage ||
      compare(sum(billed, unbilled), total) !== 0 ||
      compare(remaining, compare(total, limit) >= 0 ? exactDecimal("0")! : difference(limit, total)) !== 0) {
    throw new Error("Invalid API budget evidence");
  }
  const [start, end, observed, covered] = times.map(item => Date.parse(item as string));
  if (end - start < 27 * 86400000 || end - start > 32 * 86400000 ||
      start > covered || covered > observed || observed > end) throw new Error("Invalid budget period");
  const generated = Date.parse(data.generated_at_utc as string);
  const staleAfter = policy.stale_after_seconds as number;
  const stale = generated < start || generated >= end || generated - observed > staleAfter * 1000 ||
    generated - covered > staleAfter * 1000;
  const future = observed > generated || covered > generated;
  if (future && data.state !== "degraded" || data.state === "stale" && (!stale || future) ||
      ["connected", "warning", "critical", "exhausted"].includes(String(data.state)) && (stale || future)) {
    throw new Error("Invalid API budget freshness state");
  }
  const usageUnits = total.units * 10n ** BigInt(limit.scale) * 1_000_000n /
    (limit.units * 10n ** BigInt(total.scale));
  if (compare(usage, { units: usageUnits, scale: 4 }) !== 0) throw new Error("Invalid usage percent");
  const expected = compare(total, limit) >= 0 ? "exhausted" :
    compare(total, product(limit, critical)) >= 0 ? "critical" :
    compare(total, product(limit, warning)) >= 0 ? "warning" : "connected";
  if (["connected", "warning", "critical", "exhausted"].includes(String(data.state)) &&
      data.state !== expected) throw new Error("Invalid API budget threshold state");
  return data as ApiBudgetView;
}

export function parseOperationalAlerts(value: unknown): OperationalAlertInventory {
  const data = object(value); exactKeys(data, inventoryKeys);
  if (data.protocol !== "sochron.operational-alerts.v3" || data.trading_mode !== "demo" ||
      data.read_only !== true || data.auto_trading_enabled !== false || data.execution_ready !== false ||
      data.delivery_configured !== false || !["partial", "degraded"].includes(String(data.status)) ||
      !lifecycleRuntimes.has(data.lifecycle_runtime as LifecycleRuntime) ||
      typeof data.lifecycle_mutations_enabled !== "boolean" ||
      data.lifecycle_mutations_enabled !== (data.lifecycle_runtime === "connected") ||
      !utc(data.generated_at_utc) || typeof data.truncated !== "boolean" || !data.api_budget ||
      !Array.isArray(data.alerts) ||
      data.alerts.length > 64 || !Array.isArray(data.coverage) || data.coverage.length !== alertKinds.length) {
    throw new Error("Invalid alert inventory");
  }
  const apiBudget = parseApiBudget(data.api_budget);
  const coverage = data.coverage.map((raw, index) => {
    const item = object(raw); exactKeys(item, coverageKeys);
    const kind = alertKinds[index]; const definition = alertDefinitions[kind];
    if (item.kind !== kind || item.implementation !== definition.implementation ||
        !runtimes.has(item.runtime as CoverageRuntime) || !exactStrings(item.api_routes, definition.routes) ||
        !exactStrings(item.sources, definition.sources) ||
        (item.implementation === "missing" && item.runtime !== "awaiting_configuration")) {
      throw new Error("Invalid alert coverage");
    }
    return item as AlertCoverage;
  });
  const ids = new Set<string>();
  const conditions = new Set<string>();
  const alerts = data.alerts.map(raw => {
    const item = object(raw); exactKeys(item, alertKeys);
    const rule = typeof item.detail_code === "string" ? detailRules[item.detail_code] : undefined;
    if (typeof item.id !== "string" || !/^[0-9a-f]{24}$/.test(item.id) || ids.has(item.id) ||
        typeof item.condition_id !== "string" || !/^[0-9a-f]{24}$/.test(item.condition_id) ||
        conditions.has(item.condition_id) ||
        !alertKinds.includes(item.kind as AlertKind) || !severities.has(String(item.severity)) ||
        !Object.hasOwn(sourceRoutes, String(item.source)) ||
        typeof item.source_ref !== "string" || !/^[a-z0-9_-]{1,32}$/.test(item.source_ref) ||
        typeof item.detail_code !== "string" || !details.has(item.detail_code) || !rule ||
        item.kind !== rule.kind || item.source !== rule.source || item.severity !== rule.severity ||
        !utc(item.observed_at_utc) ||
        !exactStrings(item.evidence_routes, sourceRoutes[item.source as AlertSource]) ||
        !lifecycleStates.has(item.lifecycle_state as LifecycleState) ||
        typeof item.acknowledge_allowed !== "boolean" || typeof item.resolve_allowed !== "boolean" ||
        ![null, "owner"].includes(item.acknowledged_by as null | "owner") ||
        !(item.acknowledged_at_utc === null || utc(item.acknowledged_at_utc)) ||
        !(item.resolved_at_utc === null || utc(item.resolved_at_utc))) throw new Error("Invalid operational alert");
    if (item.source === "execution_journal" && !/^[0-9a-f]{16}$/.test(item.source_ref)) {
      throw new Error("Invalid journal alert reference");
    }
    const acknowledged = item.acknowledged_at_utc !== null;
    const resolved = item.resolved_at_utc !== null;
    const state = item.lifecycle_state as LifecycleState;
    if (acknowledged !== (item.acknowledged_by === "owner") ||
        (resolved && (!acknowledged || Date.parse(String(item.resolved_at_utc)) < Date.parse(String(item.acknowledged_at_utc)))) ||
        (state === "active" && (acknowledged || resolved)) ||
        (["acknowledged", "cleared"].includes(state) && (!acknowledged || resolved)) ||
        (state === "resolved" && !resolved) ||
        (item.acknowledge_allowed && state !== "active") ||
        (item.resolve_allowed && !(state === "cleared" || (state === "acknowledged" && item.kind === "order_reject"))) ||
        (state === "unavailable" && (item.acknowledge_allowed || item.resolve_allowed)) ||
        (data.lifecycle_runtime !== "connected" && (item.acknowledge_allowed || item.resolve_allowed))) {
      throw new Error("Invalid alert lifecycle");
    }
    ids.add(item.id);
    conditions.add(item.condition_id);
    return item as OperationalAlert;
  });
  const degraded = coverage.some(item => item.runtime === "degraded") || data.lifecycle_runtime === "degraded";
  if ((data.status === "degraded") !== degraded) throw new Error("Invalid alert inventory status");
  const expectedOrder = [...alerts].sort((left, right) =>
    lifecycleOrder[left.lifecycle_state] - lifecycleOrder[right.lifecycle_state] ||
    severityOrder[left.severity] - severityOrder[right.severity] ||
    Date.parse(right.observed_at_utc) - Date.parse(left.observed_at_utc) ||
    left.kind.localeCompare(right.kind) || left.id.localeCompare(right.id));
  if (alerts.some((item, index) => item.id !== expectedOrder[index].id)) {
    throw new Error("Invalid alert order");
  }
  const budgetCoverage = coverage[coverage.length - 1];
  const expectedBudgetRuntime: CoverageRuntime = apiBudget.state === "disabled" ? "awaiting_configuration" :
    apiBudget.state === "awaiting_snapshot" ? "awaiting_source" :
    ["stale", "degraded"].includes(apiBudget.state) ? "degraded" : "connected";
  if (budgetCoverage.runtime !== expectedBudgetRuntime) throw new Error("Invalid budget coverage state");
  return { ...data, api_budget: apiBudget, alerts, coverage } as OperationalAlertInventory;
}

export function parseAlertMutationReceipt(value: unknown): AlertMutationReceipt {
  const data = object(value); exactKeys(data, receiptKeys);
  if (data.protocol !== "sochron.alert-mutation.v1" ||
      !["acknowledge", "resolve"].includes(String(data.action)) ||
      typeof data.condition_id !== "string" || !/^[0-9a-f]{24}$/.test(data.condition_id) ||
      !utc(data.acknowledged_at_utc) || !(data.resolved_at_utc === null || utc(data.resolved_at_utc)) ||
      (data.action === "acknowledge" && (data.lifecycle_state !== "acknowledged" || data.resolved_at_utc !== null)) ||
      (data.action === "resolve" && (data.lifecycle_state !== "resolved" || !utc(data.resolved_at_utc))) ||
      (data.resolved_at_utc !== null && Date.parse(data.resolved_at_utc as string) < Date.parse(data.acknowledged_at_utc))) {
    throw new Error("Invalid alert mutation receipt");
  }
  return data as AlertMutationReceipt;
}
