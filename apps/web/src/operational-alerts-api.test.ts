import { describe, expect, it } from "vitest";
import { alertDefinitions, alertKinds, parseAlertMutationReceipt, parseOperationalAlerts } from "./operational-alerts-api";

function fixture() {
  return {
    protocol: "sochron.operational-alerts.v2", trading_mode: "demo", read_only: true,
    auto_trading_enabled: false, execution_ready: false, delivery_configured: false,
    lifecycle_runtime: "connected", lifecycle_mutations_enabled: true,
    status: "partial", generated_at_utc: "2026-09-20T04:00:00Z", truncated: false,
    alerts: [{ id: "0123456789abcdef01234567", condition_id: "fedcba9876543210fedcba98",
      kind: "unknown_execution", severity: "critical", source: "execution_journal",
      source_ref: "0123456789abcdef", detail_code: "entry_unknown",
      observed_at_utc: "2026-09-20T03:59:00Z", evidence_routes: ["/api/owner/execution"],
      lifecycle_state: "active", acknowledge_allowed: true, resolve_allowed: false,
      acknowledged_by: null, acknowledged_at_utc: null, resolved_at_utc: null }],
    coverage: alertKinds.map(kind => ({ kind, implementation: alertDefinitions[kind].implementation,
      runtime: "awaiting_configuration", api_routes: [...alertDefinitions[kind].routes],
      sources: [...alertDefinitions[kind].sources] })),
  };
}

describe("operational alert inventory contract", () => {
  it("accepts the strict Demo-only lifecycle inventory", () => {
    const parsed = parseOperationalAlerts(fixture());
    expect(parsed.coverage.map(item => item.kind)).toEqual(alertKinds);
    expect(parsed.alerts[0].acknowledge_allowed).toBe(true);
  });

  it("accepts coherent acknowledgement, cleared and resolution evidence", () => {
    const acknowledged = fixture();
    Object.assign(acknowledged.alerts[0], { lifecycle_state: "acknowledged", acknowledge_allowed: false,
      acknowledged_by: "owner", acknowledged_at_utc: "2026-09-20T04:00:01Z" });
    expect(parseOperationalAlerts(acknowledged).alerts[0].lifecycle_state).toBe("acknowledged");
    const cleared = fixture();
    Object.assign(cleared.alerts[0], { lifecycle_state: "cleared", acknowledge_allowed: false,
      resolve_allowed: true, acknowledged_by: "owner", acknowledged_at_utc: "2026-09-20T04:00:01Z" });
    expect(parseOperationalAlerts(cleared).alerts[0].resolve_allowed).toBe(true);
    const resolved = fixture();
    Object.assign(resolved.alerts[0], { lifecycle_state: "resolved", acknowledge_allowed: false,
      acknowledged_by: "owner", acknowledged_at_utc: "2026-09-20T04:00:01Z",
      resolved_at_utc: "2026-09-20T04:00:02Z" });
    expect(parseOperationalAlerts(resolved).alerts[0].resolved_at_utc).not.toBeNull();
  });

  it.each([
    ["Auto Trading", (value: ReturnType<typeof fixture>) => { value.auto_trading_enabled = true; }],
    ["delivery claim", (value: ReturnType<typeof fixture>) => { value.delivery_configured = true; }],
    ["runtime mutation mismatch", (value: ReturnType<typeof fixture>) => { value.lifecycle_mutations_enabled = false; }],
    ["fabricated acknowledgement", (value: ReturnType<typeof fixture>) => {
      (value.alerts[0] as { acknowledged_by: unknown }).acknowledged_by = "owner";
    }],
    ["unsafe active resolution", (value: ReturnType<typeof fixture>) => {
      Object.assign(value.alerts[0], { resolve_allowed: true });
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

describe("alert lifecycle mutation receipt", () => {
  it("accepts exact acknowledge and resolve receipts", () => {
    const base = { protocol: "sochron.alert-mutation.v1", condition_id: "a".repeat(24),
      acknowledged_at_utc: "2026-09-20T04:00:01Z" };
    expect(parseAlertMutationReceipt({ ...base, action: "acknowledge", lifecycle_state: "acknowledged",
      resolved_at_utc: null }).action).toBe("acknowledge");
    expect(parseAlertMutationReceipt({ ...base, action: "resolve", lifecycle_state: "resolved",
      resolved_at_utc: "2026-09-20T04:00:02Z" }).action).toBe("resolve");
  });

  it("rejects contradictory or unknown receipt data", () => {
    expect(() => parseAlertMutationReceipt({ protocol: "sochron.alert-mutation.v1", action: "resolve",
      condition_id: "a".repeat(24), lifecycle_state: "resolved",
      acknowledged_at_utc: "2026-09-20T04:00:02Z", resolved_at_utc: null })).toThrow();
  });
});
