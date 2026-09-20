export const connectionIds = [
  "core_api", "demo_readiness", "owner_auth", "market_telemetry", "native_chart", "bar_history",
  "execution_evidence", "operational_alerts", "signals", "statistics",
] as const;

export type ConnectionId = typeof connectionIds[number];
export type ImplementationState = "available" | "partial" | "missing";
export type RuntimeState = "connected" | "configured" | "awaiting_configuration" |
  "awaiting_source" | "degraded" | "not_applicable";

export type ConnectionNode = {
  id: ConnectionId;
  implementation: ImplementationState;
  runtime: RuntimeState;
  current_routes: string[];
  required_route: string | null;
  sources: string[];
};

export type ConnectionMap = {
  demo_only: true;
  auto_trading_enabled: false;
  execution_ready: false;
  connections: ConnectionNode[];
};

type Definition = {
  title: string;
  result: string;
  routes: string[];
  required: string | null;
  sources: string[];
  sourceLabel: string;
  implementation: ImplementationState;
};

export const connectionDefinitions: Record<ConnectionId, Definition> = {
  core_api: { title: "ภาพรวมระบบ", result: "สถานะ API และโหมด Demo", routes: ["/api/health", "/api/ui/connections"],
    required: null, sources: ["fastapi"], sourceLabel: "FastAPI", implementation: "available" },
  demo_readiness: { title: "Gate ความพร้อม Demo", result: "ข้อมูลที่ขาด runtime และหลักฐานเป้าหมาย", routes: ["/api/ui/demo-readiness"],
    required: null, sources: ["owner_decisions", "runtime_gates", "target_evidence"], sourceLabel: "Redacted owner decisions + component states + target gates", implementation: "available" },
  owner_auth: { title: "เข้าสู่ระบบเจ้าของ", result: "Session และสิทธิ์อ่านข้อมูลส่วนตัว", routes: ["/api/auth/config", "/api/owner/session"],
    required: null, sources: ["supabase_auth"], sourceLabel: "Supabase Auth", implementation: "available" },
  market_telemetry: { title: "บัญชีและราคาปัจจุบัน", result: "Equity, Balance, Bid และ Ask", routes: ["/api/owner/telemetry"],
    required: null, sources: ["mt5_telemetry"], sourceLabel: "MT5 Telemetry EA", implementation: "available" },
  native_chart: { title: "กราฟ M1 / M5 / M15 / H1", result: "แท่งเทียนและช่องว่างของข้อมูล", routes: ["/api/owner/chart/{timeframe}"],
    required: null, sources: ["mt5_copyrates"], sourceLabel: "MT5 CopyRates", implementation: "available" },
  bar_history: { title: "ประวัติแท่งปิด", result: "ข้อมูลย้อนหลังและ receipt", routes: ["/api/owner/history/{timeframe}"],
    required: null, sources: ["local_bar_archive"], sourceLabel: "Local bar archive", implementation: "available" },
  execution_evidence: { title: "คำสั่งและการป้องกันสถานะ", result: "Order / Deal / Position / SL ที่ยืนยันแล้ว", routes: ["/api/executor/v1/status", "/api/owner/execution"],
    required: null, sources: ["mt5_execution"], sourceLabel: "MT5 Execution EA", implementation: "available" },
  operational_alerts: { title: "ศูนย์แจ้งเตือน", result: "เหตุสำคัญและ coverage ของ source", routes: ["/api/owner/alerts"],
    required: "provider budget source + external alert delivery",
    sources: ["telemetry_status", "execution_status", "execution_journal", "bar_history", "policy_status", "api_budget"],
    sourceLabel: "Runtime states + local journals · ยังไม่ส่งแจ้งเตือนภายนอก", implementation: "partial" },
  signals: { title: "สัญญาณ", result: "เหตุผล กลยุทธ์ และเวลายืนยัน", routes: ["/api/policy/v1/status", "/api/owner/signals"],
    required: null, sources: ["mt5_policy_evidence", "news_gate", "supabase_signals"], sourceLabel: "MT5 quote/session + execution inventory + News Gate → Policy Writer → Supabase", implementation: "available" },
  statistics: { title: "สถิติ", result: "ผลลัพธ์ ต้นทุน และความไม่แน่นอน", routes: ["/api/owner/statistics"],
    required: null, sources: ["supabase_evaluations"], sourceLabel: "PA01 Tick Replay → Research Evaluator → Supabase evaluations · รอ historical replay input", implementation: "available" },
};

const implementations = new Set<ImplementationState>(["available", "partial", "missing"]);
const runtimes = new Set<RuntimeState>([
  "connected", "configured", "awaiting_configuration", "awaiting_source", "degraded", "not_applicable",
]);

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid connection map");
  return value as Record<string, unknown>;
}

function exactStrings(value: unknown, expected: string[]): value is string[] {
  return Array.isArray(value) && value.length === expected.length &&
    value.every((item, index) => item === expected[index]);
}

export function parseConnectionMap(value: unknown): ConnectionMap {
  const data = object(value);
  if (data.demo_only !== true || data.auto_trading_enabled !== false || data.execution_ready !== false ||
      !Array.isArray(data.connections) || data.connections.length !== connectionIds.length) {
    throw new Error("Invalid connection map");
  }
  const seen = new Set<string>();
  const connections = data.connections.map((item, index) => {
    const node = object(item);
    const id = node.id;
    if (id !== connectionIds[index] || typeof id !== "string" || seen.has(id) || !(id in connectionDefinitions)) {
      throw new Error("Invalid connection node");
    }
    seen.add(id);
    const definition = connectionDefinitions[id as ConnectionId];
    if (node.implementation !== definition.implementation || !implementations.has(node.implementation as ImplementationState) ||
        !runtimes.has(node.runtime as RuntimeState) || !exactStrings(node.current_routes, definition.routes) ||
        node.required_route !== definition.required || !exactStrings(node.sources, definition.sources)) {
      throw new Error("Invalid connection node");
    }
    return node as ConnectionNode;
  });
  return { demo_only: true, auto_trading_enabled: false, execution_ready: false, connections };
}
