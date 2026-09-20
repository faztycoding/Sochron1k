export const alertKinds = [
  "order_reject", "no_sl", "risk_halt", "unknown_execution", "stale_price",
  "bridge_disconnected", "storage_limit", "api_budget",
] as const;

export type AlertKind = typeof alertKinds[number];
export type AlertSource = "telemetry_bridge" | "execution_bridge" | "execution_journal" |
  "policy_writer" | "bar_history" | "api_budget";
export type CoverageRuntime = "connected" | "awaiting_configuration" | "awaiting_source" | "degraded";

export type OperationalAlert = {
  id: string; kind: AlertKind; severity: "critical" | "warning" | "info";
  source: AlertSource; source_ref: string; detail_code: string; observed_at_utc: string;
  evidence_routes: string[]; acknowledged_by: null; resolved_at_utc: null;
};
export type AlertCoverage = { kind: AlertKind; implementation: "available" | "missing";
  runtime: CoverageRuntime; api_routes: string[]; sources: AlertSource[] };
export type OperationalAlertInventory = {
  protocol: "sochron.operational-alerts.v1"; trading_mode: "demo"; read_only: true;
  auto_trading_enabled: false; execution_ready: false; delivery_configured: false;
  status: "partial" | "degraded"; generated_at_utc: string; truncated: boolean;
  alerts: OperationalAlert[]; coverage: AlertCoverage[];
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
    routes: ["/api/owner/alerts", "/api/owner/telemetry", "/api/executor/v1/status", "/api/policy/v1/status"],
    sources: ["telemetry_bridge", "execution_bridge", "policy_writer"],
    sourceLabel: "Telemetry + execution + policy status", implementation: "available" },
  storage_limit: { title: "พื้นที่คลังใกล้เพดาน", routes: ["/api/owner/alerts", "/api/owner/history/{timeframe}"],
    sources: ["bar_history"], sourceLabel: "Local bar archive page usage", implementation: "available" },
  api_budget: { title: "งบ API ใกล้เพดาน", routes: ["/api/owner/alerts"],
    sources: ["api_budget"], sourceLabel: "ยังไม่มี provider cost source", implementation: "missing" },
};

const alertKeys = ["id", "kind", "severity", "source", "source_ref", "detail_code", "observed_at_utc",
  "evidence_routes", "acknowledged_by", "resolved_at_utc"];
const coverageKeys = ["kind", "implementation", "runtime", "api_routes", "sources"];
const inventoryKeys = ["protocol", "trading_mode", "read_only", "auto_trading_enabled", "execution_ready",
  "delivery_configured", "status", "generated_at_utc", "truncated", "alerts", "coverage"];
const runtimes = new Set<CoverageRuntime>(["connected", "awaiting_configuration", "awaiting_source", "degraded"]);
const severities = new Set(["critical", "warning", "info"]);
const sourceRoutes: Record<AlertSource, string[]> = {
  telemetry_bridge: ["/api/owner/telemetry"], execution_bridge: ["/api/executor/v1/status"],
  execution_journal: ["/api/owner/execution"], policy_writer: ["/api/policy/v1/status"],
  bar_history: ["/api/owner/history/{timeframe}"], api_budget: ["/api/owner/alerts"],
};
const details = new Set([
  "entry_rejected", "management_rejected", "entry_unknown", "management_unknown",
  "open_volume_without_confirmed_sl", "daily_halt", "total_halt", "daily_and_total_halt",
  "price_or_heartbeat_stale", "telemetry_stale", "telemetry_rejected", "execution_stale",
  "execution_rejected", "policy_writer_degraded", "execution_journal_unavailable",
  "bar_history_unavailable", "warning_70", "warning_85",
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
};
const severityOrder = { critical: 0, warning: 1, info: 2 } as const;

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

export function parseOperationalAlerts(value: unknown): OperationalAlertInventory {
  const data = object(value); exactKeys(data, inventoryKeys);
  if (data.protocol !== "sochron.operational-alerts.v1" || data.trading_mode !== "demo" ||
      data.read_only !== true || data.auto_trading_enabled !== false || data.execution_ready !== false ||
      data.delivery_configured !== false || !["partial", "degraded"].includes(String(data.status)) ||
      !utc(data.generated_at_utc) || typeof data.truncated !== "boolean" || !Array.isArray(data.alerts) ||
      data.alerts.length > 110 || !Array.isArray(data.coverage) || data.coverage.length !== alertKinds.length) {
    throw new Error("Invalid alert inventory");
  }
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
  const alerts = data.alerts.map(raw => {
    const item = object(raw); exactKeys(item, alertKeys);
    const rule = typeof item.detail_code === "string" ? detailRules[item.detail_code] : undefined;
    if (typeof item.id !== "string" || !/^[0-9a-f]{24}$/.test(item.id) || ids.has(item.id) ||
        !alertKinds.includes(item.kind as AlertKind) || !severities.has(String(item.severity)) ||
        !Object.hasOwn(sourceRoutes, String(item.source)) ||
        typeof item.source_ref !== "string" || !/^[a-z0-9_-]{1,32}$/.test(item.source_ref) ||
        typeof item.detail_code !== "string" || !details.has(item.detail_code) || !rule ||
        item.kind !== rule.kind || item.source !== rule.source || item.severity !== rule.severity ||
        !utc(item.observed_at_utc) ||
        !exactStrings(item.evidence_routes, sourceRoutes[item.source as AlertSource]) ||
        item.acknowledged_by !== null || item.resolved_at_utc !== null) throw new Error("Invalid operational alert");
    if (item.source === "execution_journal" && !/^[0-9a-f]{16}$/.test(item.source_ref)) {
      throw new Error("Invalid journal alert reference");
    }
    ids.add(item.id);
    return item as OperationalAlert;
  });
  const degraded = coverage.some(item => item.runtime === "degraded");
  if ((data.status === "degraded") !== degraded) throw new Error("Invalid alert inventory status");
  const expectedOrder = [...alerts].sort((left, right) =>
    severityOrder[left.severity] - severityOrder[right.severity] ||
    Date.parse(right.observed_at_utc) - Date.parse(left.observed_at_utc) ||
    left.kind.localeCompare(right.kind) || left.id.localeCompare(right.id));
  if (alerts.some((item, index) => item.id !== expectedOrder[index].id)) {
    throw new Error("Invalid alert order");
  }
  return { ...data, alerts, coverage } as OperationalAlertInventory;
}
