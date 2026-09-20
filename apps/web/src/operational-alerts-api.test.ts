import { describe, expect, it } from "vitest";
import { alertDefinitions, alertKinds, parseOperationalAlerts } from "./operational-alerts-api";

function fixture() {
  return {
    protocol: "sochron.operational-alerts.v1", trading_mode: "demo", read_only: true,
    auto_trading_enabled: false, execution_ready: false, delivery_configured: false,
    status: "partial", generated_at_utc: "2026-09-20T04:00:00Z", truncated: false,
    alerts: [{ id: "0123456789abcdef01234567", kind: "unknown_execution", severity: "critical",
      source: "execution_journal", source_ref: "0123456789abcdef", detail_code: "entry_unknown",
      observed_at_utc: "2026-09-20T03:59:00Z", evidence_routes: ["/api/owner/execution"],
      acknowledged_by: null, resolved_at_utc: null }],
    coverage: alertKinds.map(kind => ({ kind, implementation: alertDefinitions[kind].implementation,
      runtime: "awaiting_configuration", api_routes: [...alertDefinitions[kind].routes],
      sources: [...alertDefinitions[kind].sources] })),
  };
}

describe("operational alert inventory contract", () => {
  it("accepts the fixed Demo-only, read-only inventory", () => {
    const parsed = parseOperationalAlerts(fixture());
    expect(parsed.coverage.map(item => item.kind)).toEqual(alertKinds);
    expect(parsed.alerts[0].acknowledged_by).toBeNull();
  });

  it.each([
    ["Auto Trading", (value: ReturnType<typeof fixture>) => { value.auto_trading_enabled = true; }],
    ["delivery claim", (value: ReturnType<typeof fixture>) => { value.delivery_configured = true; }],
    ["acknowledgement claim", (value: ReturnType<typeof fixture>) => {
      (value.alerts[0] as { acknowledged_by: unknown }).acknowledged_by = "owner";
    }],
    ["unknown route", (value: ReturnType<typeof fixture>) => { value.alerts[0].evidence_routes = ["/api/private"]; }],
    ["raw journal reference", (value: ReturnType<typeof fixture>) => { value.alerts[0].source_ref = "account-123"; }],
    ["coverage order", (value: ReturnType<typeof fixture>) => { value.coverage.reverse(); }],
    ["extra field", (value: ReturnType<typeof fixture>) => { Object.assign(value.alerts[0], { account_ref: "secret" }); }],
  ])("rejects %s", (_name, mutate) => {
    const value = fixture(); mutate(value);
    expect(() => parseOperationalAlerts(value)).toThrow();
  });
});
