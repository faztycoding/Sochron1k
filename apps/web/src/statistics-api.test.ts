import { describe, expect, it } from "vitest";
import { parseResearchStatistics } from "./statistics-api";

function row() {
  return { dataset_hash: "d".repeat(64), split: "walk_forward", data_cutoff_utc: "2026-09-18T23:59:59Z",
    created_at_utc: "2026-09-19T01:00:00Z", metrics: { sample_size: 40, wins: 18, losses: 20, breakeven: 2,
      win_rate_pct: "45.0000", net_return_pct: "7.25", expectancy_r: "0.18", expectancy_r_ci95_low: "0.03",
      expectancy_r_ci95_high: "0.33", max_drawdown_pct: "3.5", profit_factor: "1.24" },
    cost_assumptions: { spread_points: "18", slippage_points: "3", commission_per_lot: "7", swap_included: true,
      operating_cost_per_trade: "0.12", currency: "USD" },
    strategy: { version_id: "PA01-v1", code_hash: "a".repeat(64), status: "candidate",
      data_cutoff_utc: "2026-09-18T23:59:59Z" },
    experiment: { experiment_id: "experiment-pa01-v1", status: "shadow", policy_version: "risk-v1.1" } };
}
function fixture() {
  return { trading_mode: "demo", read_only: true, source: "supabase-evaluations", read_at_utc: "2026-09-19T02:00:00Z",
    status: { state: "available", returned_count: 1, limit: 30, auto_trading_enabled: false,
      execution_ready: false, promotion_decided: false }, evaluations: [row()] };
}

describe("research statistics parser", () => {
  it("accepts strict versioned metrics with uncertainty and costs", () => {
    const value = parseResearchStatistics(fixture());
    expect(value.evaluations[0].metrics.sample_size).toBe(40);
    expect(value.evaluations[0].cost_assumptions.spread_points).toBe("18");
  });
  it.each([
    ["extra field", (value: ReturnType<typeof fixture>) => Object.assign(value, { token: "secret" })],
    ["count mismatch", (value: ReturnType<typeof fixture>) => { value.evaluations[0].metrics.sample_size = 39; }],
    ["derived win rate mismatch", (value: ReturnType<typeof fixture>) => { value.evaluations[0].metrics.win_rate_pct = "99"; }],
    ["future strategy cutoff", (value: ReturnType<typeof fixture>) => { value.evaluations[0].strategy.data_cutoff_utc = "2026-09-19T00:00:00Z"; }],
    ["interval mismatch", (value: ReturnType<typeof fixture>) => { value.evaluations[0].metrics.expectancy_r_ci95_high = "0.1"; }],
    ["missing costs", (value: ReturnType<typeof fixture>) => { delete (value.evaluations[0].cost_assumptions as Record<string, unknown>).spread_points; }],
    ["unsafe hash", (value: ReturnType<typeof fixture>) => { value.evaluations[0].dataset_hash = "not-a-hash"; }],
    ["unsafe readiness", (value: ReturnType<typeof fixture>) => { value.status.execution_ready = true; }],
  ])("rejects %s", (_name, mutate) => {
    const value = fixture(); mutate(value); expect(() => parseResearchStatistics(value)).toThrow();
  });
  it("accepts exact awaiting-source state without fabricated statistics", () => {
    const value = fixture(); value.status.state = "awaiting_source"; value.status.returned_count = 0; value.evaluations = [];
    expect(parseResearchStatistics(value).evaluations).toEqual([]);
  });
});
