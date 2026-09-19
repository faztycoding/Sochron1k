export const signalActions = ["buy", "sell", "wait", "block"] as const;
export type SignalAction = typeof signalActions[number];
export type SignalEvidence = {
  signal_id: string;
  setup_id: string;
  action: SignalAction;
  formed_at_utc: string;
  confirmed_at_utc: string;
  expires_at_utc: string;
  created_at_utc: string;
  evidence_ids: string[];
  blocked_reason: string | null;
  experiment: { experiment_id: string; status: "draft" | "shadow" | "demo" | "halted" | "closed" | "archived"; policy_version: string };
  strategy: { version_id: string; code_hash: string; status: "candidate" | "approved" | "active" | "retired" | "rejected"; data_cutoff_utc: string };
};
export type SignalEvidenceView = {
  trading_mode: "demo";
  read_only: true;
  source: "supabase-signals";
  read_at_utc: string;
  status: { state: "awaiting_source" | "available"; returned_count: number; limit: 50;
    auto_trading_enabled: false; execution_ready: false };
  signals: SignalEvidence[];
};

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid signal evidence");
  return value as Record<string, unknown>;
}
function exactKeys(value: Record<string, unknown>, keys: readonly string[]) {
  const actual = Object.keys(value).sort(); const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new Error("Invalid signal evidence fields");
  }
}
function text(value: unknown, maximum = 128): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum && value.trim().length > 0 &&
    !Array.from(value).some(character => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127);
}
function utc(value: unknown): value is string {
  return text(value, 64) && /(Z|\+00:00)$/.test(value) && Number.isFinite(Date.parse(value));
}
function integer(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value);
}
function experiment(value: unknown): SignalEvidence["experiment"] {
  const item = object(value);
  exactKeys(item, ["experiment_id", "status", "policy_version"]);
  if (!text(item.experiment_id) || !["draft", "shadow", "demo", "halted", "closed", "archived"].includes(String(item.status)) ||
      !text(item.policy_version, 64)) throw new Error("Invalid signal experiment");
  return item as SignalEvidence["experiment"];
}
function strategy(value: unknown): SignalEvidence["strategy"] {
  const item = object(value);
  exactKeys(item, ["version_id", "code_hash", "status", "data_cutoff_utc"]);
  if (!text(item.version_id, 64) || typeof item.code_hash !== "string" || !/^[0-9a-f]{64}$/.test(item.code_hash) ||
      !["candidate", "approved", "active", "retired", "rejected"].includes(String(item.status)) ||
      !utc(item.data_cutoff_utc)) throw new Error("Invalid signal strategy");
  return item as SignalEvidence["strategy"];
}
function signal(value: unknown): SignalEvidence {
  const item = object(value);
  exactKeys(item, ["signal_id", "setup_id", "action", "formed_at_utc", "confirmed_at_utc", "expires_at_utc",
    "created_at_utc", "evidence_ids", "blocked_reason", "experiment", "strategy"]);
  if (!text(item.signal_id) || !text(item.setup_id) || !signalActions.includes(item.action as SignalAction) ||
      !utc(item.formed_at_utc) || !utc(item.confirmed_at_utc) || !utc(item.expires_at_utc) || !utc(item.created_at_utc) ||
      !Array.isArray(item.evidence_ids) || item.evidence_ids.length > 64 ||
      !item.evidence_ids.every(evidence => text(evidence)) || new Set(item.evidence_ids).size !== item.evidence_ids.length ||
      (item.blocked_reason !== null && !text(item.blocked_reason, 256))) throw new Error("Invalid signal evidence");
  const nestedExperiment = experiment(item.experiment); const nestedStrategy = strategy(item.strategy);
  const formed = Date.parse(item.formed_at_utc); const confirmed = Date.parse(item.confirmed_at_utc);
  const expires = Date.parse(item.expires_at_utc); const created = Date.parse(item.created_at_utc);
  if (formed > confirmed || confirmed >= expires || created < confirmed || Date.parse(nestedStrategy.data_cutoff_utc) > confirmed ||
      (item.action === "block" && item.blocked_reason === null) ||
      (["buy", "sell"].includes(String(item.action)) && item.blocked_reason !== null)) throw new Error("Invalid signal causality");
  return { ...item, experiment: nestedExperiment, strategy: nestedStrategy } as SignalEvidence;
}

export function parseSignalEvidence(value: unknown): SignalEvidenceView {
  const data = object(value); const status = object(data.status);
  exactKeys(data, ["trading_mode", "read_only", "source", "read_at_utc", "status", "signals"]);
  exactKeys(status, ["state", "returned_count", "limit", "auto_trading_enabled", "execution_ready"]);
  if (data.trading_mode !== "demo" || data.read_only !== true || data.source !== "supabase-signals" || !utc(data.read_at_utc) ||
      !["awaiting_source", "available"].includes(String(status.state)) || !integer(status.returned_count) ||
      Number(status.returned_count) < 0 || Number(status.returned_count) > 50 || status.limit !== 50 ||
      status.auto_trading_enabled !== false || status.execution_ready !== false ||
      !Array.isArray(data.signals) || data.signals.length > 50 || data.signals.length !== status.returned_count) {
    throw new Error("Invalid signal response");
  }
  const signals = data.signals.map(signal);
  if ((status.state === "awaiting_source") !== (signals.length === 0) ||
      new Set(signals.map(item => item.signal_id)).size !== signals.length || signals.some((item, index) =>
        index > 0 && Date.parse(signals[index - 1].confirmed_at_utc) < Date.parse(item.confirmed_at_utc))) {
    throw new Error("Invalid signal collection");
  }
  return { ...data, status, signals } as SignalEvidenceView;
}
