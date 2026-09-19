import { describe, expect, it } from "vitest";
import { parseSignalEvidence } from "./signal-api";

function row() {
  return {
    signal_id: "signal-pa01-0002", setup_id: "setup-pa01-0002", action: "buy",
    formed_at_utc: "2026-09-19T12:00:00Z", confirmed_at_utc: "2026-09-19T12:10:00Z",
    expires_at_utc: "2026-09-19T12:10:30Z", created_at_utc: "2026-09-19T12:10:01Z",
    evidence_ids: ["feature-m5-1205", "pivot-h1-1000"], blocked_reason: null,
    experiment: { experiment_id: "experiment-pa01-v1", status: "demo", policy_version: "risk-v1.1" },
    strategy: { version_id: "PA01-v1", code_hash: "a".repeat(64), status: "active",
      data_cutoff_utc: "2026-09-19T12:05:00Z" },
  };
}
function fixture() {
  return { trading_mode: "demo", read_only: true, source: "supabase-signals", read_at_utc: "2026-09-19T12:11:00Z",
    status: { state: "available", returned_count: 1, limit: 50, auto_trading_enabled: false, execution_ready: false },
    signals: [row()] };
}

describe("signal evidence parser", () => {
  it("accepts strict causal Demo evidence", () => {
    expect(parseSignalEvidence(fixture()).signals[0].strategy.version_id).toBe("PA01-v1");
  });
  it.each([
    ["extra field", (value: ReturnType<typeof fixture>) => Object.assign(value, { token: "secret" })],
    ["unsafe action", (value: ReturnType<typeof fixture>) => { value.signals[0].action = "open"; }],
    ["future cutoff", (value: ReturnType<typeof fixture>) => { value.signals[0].strategy.data_cutoff_utc = "2026-09-19T12:10:01Z"; }],
    ["early expiry", (value: ReturnType<typeof fixture>) => { value.signals[0].expires_at_utc = value.signals[0].confirmed_at_utc; }],
    ["duplicate evidence", (value: ReturnType<typeof fixture>) => { value.signals[0].evidence_ids = ["same", "same"]; }],
    ["unsafe hash", (value: ReturnType<typeof fixture>) => { value.signals[0].strategy.code_hash = "not-a-hash"; }],
    ["count mismatch", (value: ReturnType<typeof fixture>) => { value.status.returned_count = 2; }],
    ["unsafe readiness", (value: ReturnType<typeof fixture>) => { value.status.execution_ready = true; }],
  ])("rejects %s", (_name, mutate) => {
    const value = fixture(); mutate(value); expect(() => parseSignalEvidence(value)).toThrow();
  });
  it("accepts an exact awaiting-source response without inventing WAIT", () => {
    const value = fixture(); value.status.state = "awaiting_source"; value.status.returned_count = 0; value.signals = [];
    expect(parseSignalEvidence(value).signals).toEqual([]);
  });
});
