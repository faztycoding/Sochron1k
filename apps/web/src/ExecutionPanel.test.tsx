import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ExecutionPanel } from "./ExecutionPanel";

const json = (value: unknown) => new Response(JSON.stringify(value));
const filled = () => ({ trading_mode: "demo", read_only: true, source: "local-execution-journal",
  status: { state: "available", reason: null, total_commands: 1, truncated: false,
    auto_trading_enabled: false, execution_ready: false },
  commands: [{ command_id: "command-1", symbol: "XAUUSD.fixture", side: "buy", state: "unknown",
    requested_volume: "0.01", created_at_utc: "2026-09-20T01:00:00Z", updated_at_utc: "2026-09-20T01:00:01Z",
    order: { order_ticket: "order-1", position_id: "position-1", requested_volume: "0.01", filled_volume: "0.01",
      remaining_volume: "0", cancelled_volume: "0", closed_volume: "0", stop_loss_confirmed: false,
      deals: [{ deal_ticket: "deal-1", volume: "0.01", price: "2500", occurred_at_utc: null }] },
    rejection: null, management: [] }] });

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
describe("owner execution evidence panel", () => {
  it("shows the API location without exposing any order control", () => {
    render(<ExecutionPanel token={null} />);
    expect(screen.getByText("/api/owner/execution")).toBeVisible();
    expect(screen.getByText(/เข้าสู่ระบบเจ้าของ/)).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
  it("preserves UNKNOWN and unconfirmed SL from the journal", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(filled()));
    render(<ExecutionPanel token="owner-token" />);
    expect(await screen.findByText("UNKNOWN · ต้อง reconcile")).toBeVisible();
    expect(screen.getByText("ยังไม่ยืนยัน")).toBeVisible();
    expect(screen.getByText(/Deal: deal-1/)).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(fetch.mock.calls[0][0]).toBe("/api/owner/execution");
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer owner-token" });
  });
});
