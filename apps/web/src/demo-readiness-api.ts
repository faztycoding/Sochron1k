export const readinessGateIds = [
  "owner_decisions",
  "owner_auth",
  "market_data",
  "execution_bridge",
  "policy_research",
  "target_artifact",
  "broker_round_trip",
  "recovery_observability",
  "operational_authorization",
] as const;

export type ReadinessGateId = typeof readinessGateIds[number];
export type ReadinessGateState = "missing" | "recorded" | "configured" |
  "awaiting_source" | "connected" | "degraded" | "not_run" | "not_authorized" |
  "evidence_admitted" | "evidence_failed";
export type ReadinessOverallState = "awaiting_owner_inputs" | "awaiting_runtime" |
  "awaiting_target_evidence" | "awaiting_operational_authorization" | "degraded";

type GateDefinition = {
  title: string;
  detail: string;
  routes: string[];
  sources: string[];
  sourceLabel: string;
  nextAction: string;
  nextActionCode: string;
};

export const readinessGateDefinitions: Record<ReadinessGateId, GateDefinition> = {
  owner_decisions: {
    title: "ข้อมูลเป้าหมาย Demo",
    detail: "โบรกเกอร์ สัญลักษณ์ โฮสต์ งบ และผู้มีสิทธิ์ปลด halt",
    routes: ["/api/ui/demo-readiness"],
    sources: ["owner_private_decision_record"],
    sourceLabel: "Owner-private decision record",
    nextAction: "บันทึกข้อมูลเป้าหมายที่อนุมัติแล้วในไฟล์ส่วนตัว",
    nextActionCode: "record_owner_decisions",
  },
  owner_auth: {
    title: "สิทธิ์เจ้าของระบบ",
    detail: "Auth และ active session สำหรับข้อมูลส่วนตัว",
    routes: ["/api/auth/config", "/api/owner/session"],
    sources: ["supabase_auth"],
    sourceLabel: "Supabase Auth",
    nextAction: "ตั้งค่า Owner Auth และทดสอบ active session",
    nextActionCode: "configure_owner_auth",
  },
  market_data: {
    title: "ข้อมูลตลาดและกราฟ",
    detail: "ราคา บัญชี CopyRates และคลังแท่งปิด",
    routes: ["/api/owner/telemetry", "/api/owner/chart/{timeframe}", "/api/owner/history/{timeframe}"],
    sources: ["mt5_telemetry", "mt5_copyrates", "local_bar_archive"],
    sourceLabel: "MT5 telemetry + CopyRates + local archive",
    nextAction: "เชื่อม EA อ่านข้อมูลและยืนยันข้อมูลสดครบทุก timeframe",
    nextActionCode: "connect_mt5_market_data",
  },
  execution_bridge: {
    title: "Execution และ journal",
    detail: "Inventory จาก MT5 และหลักฐานคำสั่งแบบ durable",
    routes: ["/api/executor/v1/status", "/api/owner/execution"],
    sources: ["mt5_execution", "local_execution_journal"],
    sourceLabel: "MT5 execution EA + SQLite journal",
    nextAction: "ตั้งค่า Demo executor และเชื่อม journal แบบ read-only",
    nextActionCode: "connect_demo_executor",
  },
  policy_research: {
    title: "Policy, signals และสถิติ",
    detail: "News Gate, สัญญาณเวอร์ชัน และผลประเมินที่ทำซ้ำได้",
    routes: ["/api/policy/v1/status", "/api/owner/signals", "/api/owner/statistics"],
    sources: ["news_gate", "supabase_signals", "supabase_evaluations"],
    sourceLabel: "News Gate + Supabase evidence",
    nextAction: "เชื่อมแหล่ง policy/signal/evaluation และตรวจความสด",
    nextActionCode: "connect_policy_research_sources",
  },
  target_artifact: {
    title: "EA build บนเป้าหมาย",
    detail: "MetaEditor build และ artifact identity ของ executor ที่เลือก",
    routes: ["/api/ui/demo-readiness", "/api/owner/target-evidence"],
    sources: ["metaeditor_build_evidence", "target_artifact_identity"],
    sourceLabel: "MetaEditor + target artifact evidence",
    nextAction: "Compile และผูก hash/build กับเครื่องเป้าหมาย",
    nextActionCode: "compile_and_attest_ea",
  },
  broker_round_trip: {
    title: "Demo broker round trip",
    detail: "Order, deal, position, close และ broker-side SL ที่ MT5 ยืนยัน",
    routes: ["/api/owner/execution", "/api/owner/target-evidence"],
    sources: ["mt5_orders_deals_positions", "broker_side_sl"],
    sourceLabel: "MT5 orders/deals/positions/SL",
    nextAction: "ขออนุญาตแล้วรัน open-to-close แบบจำกัดหนึ่งรอบ",
    nextActionCode: "run_bounded_demo_round_trip",
  },
  recovery_observability: {
    title: "Recovery และการแจ้งเตือน",
    detail: "Restart, network loss, alerts, backup และ restore บนโฮสต์จริง",
    routes: ["/api/ui/demo-readiness", "/api/owner/target-evidence"],
    sources: ["target_fault_evidence", "alerts", "backup_restore"],
    sourceLabel: "Target fault + alert + restore evidence",
    nextAction: "ทดสอบ fault/restart และหลักฐานแจ้งเตือน/กู้คืน",
    nextActionCode: "verify_target_recovery",
  },
  operational_authorization: {
    title: "อนุญาตใช้งาน Demo",
    detail: "คำอนุญาตเฉพาะเป้าหมายและผลกระทบหลังทุก gate มีหลักฐาน",
    routes: ["/api/ui/demo-readiness"],
    sources: ["explicit_owner_authorization"],
    sourceLabel: "Explicit owner authorization",
    nextAction: "อนุมัติแยกต่างหากเมื่อหลักฐานเป้าหมายครบ",
    nextActionCode: "grant_explicit_demo_authorization",
  },
};

export type ReadinessGate = {
  id: ReadinessGateId;
  state: ReadinessGateState;
  api_routes: string[];
  sources: string[];
  next_action: string;
};

export type DemoReadiness = {
  protocol: "sochron.demo-readiness.v1";
  state: ReadinessOverallState;
  demo_only: true;
  auto_trading_enabled: false;
  release_ready: false;
  round_trip_authorized: false;
  unattended_demo_ready: false;
  gates: ReadinessGate[];
};

const gateStates = new Set<ReadinessGateState>([
  "missing", "recorded", "configured", "awaiting_source", "connected", "degraded",
  "not_run", "not_authorized", "evidence_admitted", "evidence_failed",
]);
const allowedGateStates: Record<ReadinessGateId, ReadinessGateState[]> = {
  owner_decisions: ["missing", "recorded"],
  owner_auth: ["missing", "configured"],
  market_data: ["missing", "awaiting_source", "connected", "degraded"],
  execution_bridge: ["missing", "awaiting_source", "connected", "degraded"],
  policy_research: ["missing", "awaiting_source", "connected", "degraded"],
  target_artifact: ["not_run", "evidence_admitted", "evidence_failed", "degraded"],
  broker_round_trip: ["not_run", "evidence_admitted", "evidence_failed", "degraded"],
  recovery_observability: ["not_run", "evidence_admitted", "evidence_failed", "degraded"],
  operational_authorization: ["not_authorized"],
};
const overallStates = new Set<ReadinessOverallState>([
  "awaiting_owner_inputs", "awaiting_runtime", "awaiting_target_evidence",
  "awaiting_operational_authorization", "degraded",
]);

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Invalid Demo readiness");
  }
  return value as Record<string, unknown>;
}

function exactKeys(value: Record<string, unknown>, expected: string[]): boolean {
  const keys = Object.keys(value).sort();
  return keys.length === expected.length && expected.slice().sort().every((key, index) => key === keys[index]);
}

function exactStrings(value: unknown, expected: string[]): value is string[] {
  return Array.isArray(value) && value.length === expected.length &&
    value.every((item, index) => item === expected[index]);
}

export function parseDemoReadiness(value: unknown): DemoReadiness {
  const data = object(value);
  if (!exactKeys(data, ["protocol", "state", "demo_only", "auto_trading_enabled", "release_ready",
    "round_trip_authorized", "unattended_demo_ready", "gates"]) ||
    data.protocol !== "sochron.demo-readiness.v1" || !overallStates.has(data.state as ReadinessOverallState) ||
    data.demo_only !== true || data.auto_trading_enabled !== false || data.release_ready !== false ||
    data.round_trip_authorized !== false || data.unattended_demo_ready !== false ||
    !Array.isArray(data.gates) || data.gates.length !== readinessGateIds.length) {
    throw new Error("Invalid Demo readiness");
  }
  const gates = data.gates.map((item, index) => {
    const gate = object(item);
    const id = gate.id;
    if (!exactKeys(gate, ["id", "state", "api_routes", "sources", "next_action"]) ||
        id !== readinessGateIds[index] || typeof id !== "string" || !(id in readinessGateDefinitions)) {
      throw new Error("Invalid Demo readiness gate");
    }
    const definition = readinessGateDefinitions[id as ReadinessGateId];
    if (!gateStates.has(gate.state as ReadinessGateState) ||
        !allowedGateStates[id as ReadinessGateId].includes(gate.state as ReadinessGateState) ||
        !exactStrings(gate.api_routes, definition.routes) || !exactStrings(gate.sources, definition.sources) ||
        gate.next_action !== definition.nextActionCode) {
      throw new Error("Invalid Demo readiness gate");
    }
    return gate as ReadinessGate;
  });
  return { ...(data as Omit<DemoReadiness, "gates">), gates };
}
