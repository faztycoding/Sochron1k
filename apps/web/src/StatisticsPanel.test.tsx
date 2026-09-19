import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StatisticsPanel } from "./StatisticsPanel";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
function fixture() {
  return { trading_mode: "demo", read_only: true, source: "supabase-evaluations", read_at_utc: "2026-09-19T02:00:00Z",
    status: { state: "available", returned_count: 1, limit: 30, auto_trading_enabled: false,
      execution_ready: false, promotion_decided: false }, evaluations: [{ dataset_hash: "d".repeat(64), split: "walk_forward",
      data_cutoff_utc: "2026-09-18T23:59:59Z", created_at_utc: "2026-09-19T01:00:00Z",
      metrics: { sample_size: 40, wins: 18, losses: 20, breakeven: 2, win_rate_pct: "45.0000", net_return_pct: "7.25",
        expectancy_r: "0.18", expectancy_r_ci95_low: "0.03", expectancy_r_ci95_high: "0.33",
        max_drawdown_pct: "3.5", profit_factor: "1.24" },
      cost_assumptions: { spread_points: "18", slippage_points: "3", commission_per_lot: "7", swap_included: true,
        operating_cost_per_trade: "0.12", currency: "USD" },
      strategy: { version_id: "PA01-v1", code_hash: "a".repeat(64), status: "candidate",
        data_cutoff_utc: "2026-09-18T23:59:59Z" },
      experiment: { experiment_id: "experiment-pa01-v1", status: "shadow", policy_version: "risk-v1.1" } }] };
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("owner statistics panel", () => {
  it("does not read private evidence before login", () => {
    const fetch = vi.spyOn(globalThis, "fetch"); render(<StatisticsPanel token={null} />);
    expect(screen.getByText("เข้าสู่ระบบเจ้าของเพื่ออ่านสถิติ")).toBeVisible(); expect(fetch).not.toHaveBeenCalled();
  });
  it("renders metrics with sample, uncertainty and all cost assumptions", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(fixture()));
    render(<StatisticsPanel token="owner-token" />);
    expect(await screen.findByText("Walk-forward")).toBeVisible(); expect(screen.getByText("n = 40")).toBeVisible();
    expect(screen.getByText("45.0000%")).toBeVisible(); expect(screen.getByText(/95% CI 0.03 ถึง 0.33 R/)).toBeVisible();
    expect(screen.getByText("Spread 18 points")).toBeVisible(); expect(screen.getByText("PA01-v1")).toBeVisible();
    expect(fetch.mock.calls[0][0]).toBe("/api/owner/statistics");
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer owner-token" });
    expect(screen.queryByRole("button", { name: /โปรโมต|ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });
  it("shows producer dependency rather than zero performance", async () => {
    const value = fixture(); value.status.state = "awaiting_source"; value.status.returned_count = 0; value.evaluations = [];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(value)); render(<StatisticsPanel token="owner-token" />);
    expect(await screen.findByText("API พร้อม · รอ Research producer")).toBeVisible();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });
  it("clears malformed evidence and retries read-only", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ secret: "private" })).mockResolvedValue(json(fixture()));
    render(<StatisticsPanel token="owner-token" />);
    fireEvent.click(await screen.findByRole("button", { name: "ลองอ่านสถิติอีกครั้ง" }));
    await waitFor(() => expect(screen.getByText("n = 40")).toBeVisible());
    expect(screen.queryByText("private")).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(2);
  });
});
