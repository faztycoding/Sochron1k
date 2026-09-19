export const commandStates = [
  "created", "validated", "queued", "sent", "acknowledged", "partially_filled",
  "filled", "protection_failed", "closing", "closed", "rejected", "expired",
  "cancelled", "unknown",
] as const;

export type CommandState = typeof commandStates[number];
export type DealEvidence = { deal_ticket: string; volume: string; price: string; occurred_at_utc: string | null };
export type RejectionEvidence = { operation: "open" | "cancel" | "close"; retcode: number;
  retcode_external: number; observed_at_utc: string };
export type ManagementEvidence = { command_id: string; operation: "cancel" | "close"; state: CommandState;
  requested_volume: string; created_at_utc: string; updated_at_utc: string;
  outcome: null | { broker_order_ticket: string; position_id: string | null; requested_volume: string;
    completed_volume: string; remaining_volume: string; observed_at_utc: string; deals: DealEvidence[] };
  rejection: RejectionEvidence | null };
export type CommandEvidence = { command_id: string; symbol: string; side: "buy" | "sell"; state: CommandState;
  requested_volume: string; created_at_utc: string; updated_at_utc: string;
  order: null | { order_ticket: string; position_id: string | null; requested_volume: string;
    filled_volume: string; remaining_volume: string; cancelled_volume: string; closed_volume: string;
    stop_loss_confirmed: boolean; deals: DealEvidence[] };
  rejection: RejectionEvidence | null; management: ManagementEvidence[] };
export type ExecutionEvidence = { trading_mode: "demo"; read_only: true; source: "local-execution-journal";
  status: { state: "disabled" | "available" | "unavailable"; reason: "not_configured" | "source_unavailable" | null;
    total_commands: number; truncated: boolean; auto_trading_enabled: false; execution_ready: false };
  commands: CommandEvidence[] };

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid execution evidence");
  return value as Record<string, unknown>;
}
function text(value: unknown, maximum = 128): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maximum;
}
function integer(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value);
}
function decimal(value: unknown, positive = false): value is string {
  return typeof value === "string" && /^\d+(\.\d+)?$/.test(value) && Number.isFinite(Number(value)) &&
    (positive ? Number(value) > 0 : Number(value) >= 0);
}
function utc(value: unknown): value is string {
  return text(value, 64) && /(Z|\+00:00)$/.test(value) && Number.isFinite(Date.parse(value));
}
function nullableText(value: unknown): value is string | null {
  return value === null || text(value);
}
function state(value: unknown): value is CommandState {
  return commandStates.includes(value as CommandState);
}
function deal(value: unknown): DealEvidence {
  const item = object(value);
  if (!text(item.deal_ticket) || !decimal(item.volume, true) || !decimal(item.price, true) ||
      (item.occurred_at_utc !== null && !utc(item.occurred_at_utc))) throw new Error("Invalid deal evidence");
  return item as DealEvidence;
}
function rejection(value: unknown): RejectionEvidence | null {
  if (value === null) return null;
  const item = object(value);
  if (!["open", "cancel", "close"].includes(String(item.operation)) || !integer(item.retcode) ||
      !integer(item.retcode_external) || !utc(item.observed_at_utc)) throw new Error("Invalid rejection evidence");
  return item as RejectionEvidence;
}
function management(value: unknown): ManagementEvidence {
  const item = object(value);
  if (!text(item.command_id) || !["cancel", "close"].includes(String(item.operation)) || !state(item.state) ||
      !decimal(item.requested_volume, true) || !utc(item.created_at_utc) || !utc(item.updated_at_utc)) {
    throw new Error("Invalid management evidence");
  }
  let outcome: ManagementEvidence["outcome"] = null;
  if (item.outcome !== null) {
    const raw = object(item.outcome);
    if (!text(raw.broker_order_ticket) || !nullableText(raw.position_id) || !decimal(raw.requested_volume, true) ||
        !decimal(raw.completed_volume) || !decimal(raw.remaining_volume) || !utc(raw.observed_at_utc) ||
        !Array.isArray(raw.deals) || raw.deals.length > 1000) throw new Error("Invalid management outcome");
    outcome = { ...raw, deals: raw.deals.map(deal) } as ManagementEvidence["outcome"];
  }
  return { ...item, outcome, rejection: rejection(item.rejection) } as ManagementEvidence;
}
function command(value: unknown): CommandEvidence {
  const item = object(value);
  if (!text(item.command_id) || !text(item.symbol, 32) || !["buy", "sell"].includes(String(item.side)) ||
      !state(item.state) || !decimal(item.requested_volume, true) || !utc(item.created_at_utc) ||
      !utc(item.updated_at_utc) || !Array.isArray(item.management) || item.management.length > 100) {
    throw new Error("Invalid command evidence");
  }
  let order: CommandEvidence["order"] = null;
  if (item.order !== null) {
    const raw = object(item.order);
    if (!text(raw.order_ticket) || !nullableText(raw.position_id) || !decimal(raw.requested_volume, true) ||
        !decimal(raw.filled_volume) || !decimal(raw.remaining_volume) || !decimal(raw.cancelled_volume) ||
        !decimal(raw.closed_volume) || typeof raw.stop_loss_confirmed !== "boolean" ||
        !Array.isArray(raw.deals) || raw.deals.length > 1000) throw new Error("Invalid order evidence");
    order = { ...raw, deals: raw.deals.map(deal) } as CommandEvidence["order"];
  }
  return { ...item, order, rejection: rejection(item.rejection), management: item.management.map(management) } as CommandEvidence;
}

export function parseExecutionEvidence(value: unknown): ExecutionEvidence {
  const data = object(value); const status = object(data.status);
  if (data.trading_mode !== "demo" || data.read_only !== true || data.source !== "local-execution-journal" ||
      !["disabled", "available", "unavailable"].includes(String(status.state)) ||
      ![null, "not_configured", "source_unavailable"].includes(status.reason as null | string) ||
      !integer(status.total_commands) || status.total_commands < 0 || typeof status.truncated !== "boolean" ||
      status.auto_trading_enabled !== false || status.execution_ready !== false ||
      !Array.isArray(data.commands) || data.commands.length > 50) throw new Error("Invalid execution evidence");
  if ((status.state === "disabled" && status.reason !== "not_configured") ||
      (status.state === "unavailable" && status.reason !== "source_unavailable") ||
      (status.state === "available" && status.reason !== null) ||
      (status.state !== "available" && (data.commands.length !== 0 || status.total_commands !== 0 || status.truncated !== false))) {
    throw new Error("Invalid execution status");
  }
  const commands = data.commands.map(command);
  if (new Set(commands.map(item => item.command_id)).size !== commands.length || status.total_commands < commands.length ||
      (status.truncated !== (status.total_commands > commands.length))) throw new Error("Invalid command collection");
  return { ...data, status, commands } as ExecutionEvidence;
}
