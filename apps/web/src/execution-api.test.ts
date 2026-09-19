import { describe, expect, it } from "vitest";
import { parseExecutionEvidence } from "./execution-api";

const fixture = (): any => ({
  trading_mode: "demo", read_only: true, source: "local-execution-journal",
  status: { state: "available", reason: null, total_commands: 1, truncated: false,
    auto_trading_enabled: false, execution_ready: false },
  commands: [{ command_id: "command-1", symbol: "XAUUSD.fixture", side: "buy", state: "filled",
    requested_volume: "0.01", created_at_utc: "2026-09-20T01:00:00Z", updated_at_utc: "2026-09-20T01:00:01+00:00",
    order: { order_ticket: "order-1", position_id: "position-1", requested_volume: "0.01",
      filled_volume: "0.01", remaining_volume: "0", cancelled_volume: "0", closed_volume: "0",
      stop_loss_confirmed: true, deals: [{ deal_ticket: "deal-1", volume: "0.01", price: "2500.10", occurred_at_utc: null }] },
    rejection: null, management: [] }],
});

describe("execution evidence parser", () => {
  it("accepts a strict Demo-only confirmed projection", () => {
    expect(parseExecutionEvidence(fixture()).commands[0].order?.stop_loss_confirmed).toBe(true);
  });
  it.each([
    ["live mode", (value: ReturnType<typeof fixture>) => { value.trading_mode = "real"; }],
    ["write mode", (value: ReturnType<typeof fixture>) => { value.read_only = false; }],
    ["Auto Trading", (value: ReturnType<typeof fixture>) => { value.status.auto_trading_enabled = true; }],
    ["execution ready", (value: ReturnType<typeof fixture>) => { value.status.execution_ready = true; }],
    ["invalid UTC", (value: ReturnType<typeof fixture>) => { value.commands[0].updated_at_utc = "2026-09-20"; }],
    ["unknown state", (value: ReturnType<typeof fixture>) => { value.commands[0].state = "complete"; }],
    ["invented count", (value: ReturnType<typeof fixture>) => { value.status.total_commands = 0; }],
  ])("rejects %s", (_name, mutate) => {
    const value = fixture(); mutate(value); expect(() => parseExecutionEvidence(value)).toThrow();
  });
  it("accepts disabled only with no commands", () => {
    const value = fixture(); value.status = { ...value.status, state: "disabled", reason: "not_configured", total_commands: 0 };
    value.commands = [];
    expect(parseExecutionEvidence(value).status.state).toBe("disabled");
    value.commands = fixture().commands;
    expect(() => parseExecutionEvidence(value)).toThrow();
  });
});
