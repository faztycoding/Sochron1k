import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OperationalAlertsPanel } from "./OperationalAlertsPanel";
import { alertDefinitions, alertKinds } from "./operational-alerts-api";

const json = (value: unknown) => new Response(JSON.stringify(value));
function fixture(state: "active" | "acknowledged" = "active") {
  const acknowledged = state === "acknowledged";
  return {
    protocol: "sochron.operational-alerts.v3", trading_mode: "demo", read_only: true,
    auto_trading_enabled: false, execution_ready: false, delivery_configured: false,
    lifecycle_runtime: "connected", lifecycle_mutations_enabled: true,
    status: "partial", generated_at_utc: "2026-09-20T04:00:00Z", truncated: false,
    api_budget: { protocol: "sochron.api-budget-view.v1", trading_mode: "demo", read_only: true,
      auto_trading_enabled: false, execution_ready: false, state: "connected",
      generated_at_utc: "2026-09-20T04:00:00Z",
      policy: { currency: "USD", monthly_limit: "100.00", warning_fraction: "0.70",
        critical_fraction: "0.85", stale_after_seconds: 3600 },
      evidence: { source_ref: "0123456789abcdef", period_start_utc: "2026-09-01T00:00:00Z",
        period_end_utc: "2026-10-01T00:00:00Z", observed_at_utc: "2026-09-20T03:59:00Z",
        coverage_until_utc: "2026-09-20T03:58:00Z", billed_cost: "60.00",
        unbilled_estimate: "5.00", total_cost: "65.00", remaining_amount: "35.00",
        usage_percent: "65.0000" } },
    alerts: [{ id: "0123456789abcdef01234567", condition_id: "fedcba9876543210fedcba98",
      kind: "unknown_execution", severity: "critical", source: "execution_journal",
      source_ref: "0123456789abcdef", detail_code: "entry_unknown",
      observed_at_utc: "2026-09-20T03:59:00Z", evidence_routes: ["/api/owner/execution"],
      lifecycle_state: state, acknowledge_allowed: !acknowledged, resolve_allowed: false,
      acknowledged_by: acknowledged ? "owner" : null,
      acknowledged_at_utc: acknowledged ? "2026-09-20T04:00:01Z" : null,
      resolved_at_utc: null }],
    coverage: alertKinds.map(kind => ({ kind, implementation: alertDefinitions[kind].implementation,
      runtime: kind === "unknown_execution" || kind === "api_budget" ? "connected" : "awaiting_configuration",
      api_routes: alertDefinitions[kind].routes, sources: alertDefinitions[kind].sources })),
  };
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
describe("owner operational alert panel", () => {
  it("keeps every API position visible while signed out", () => {
    render(<OperationalAlertsPanel token={null} />);
    expect(screen.getAllByText("/api/owner/alerts").length).toBeGreaterThanOrEqual(alertKinds.length);
    for (const kind of alertKinds) expect(screen.getByText(kind)).toBeVisible();
    expect(screen.getByText(/ยังไม่มีการส่งอีเมล\/ข้อความ/)).toBeVisible();
    expect(screen.queryByText("ผลคำสั่งเปิดยังไม่ทราบ")).not.toBeInTheDocument();
  });

  it("shows authenticated facts, lifecycle state and separate UTC/Bangkok times", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(fixture()));
    render(<OperationalAlertsPanel token="owner-token" />);
    expect(await screen.findByText(/ผลคำสั่งเปิดยังไม่ทราบ/)).toBeVisible();
    expect(screen.getByText(/พบเหตุ UTC 2026-09-20T03:59:00Z/)).toBeVisible();
    expect(screen.getAllByText(/^กรุงเทพฯ /)).toHaveLength(2);
    expect(screen.getByText("ยังไม่รับทราบ")).toBeVisible();
    expect(screen.getByText("65.00 / 100.00 USD")).toBeVisible();
    expect(screen.getByText(/กรุงเทพฯ .*ref 0123456789abcdef/)).toBeVisible();
    expect(fetch.mock.calls[0][0]).toBe("/api/owner/alerts");
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer owner-token" });
    expect(screen.getByRole("button", { name: "รับทราบ" })).toBeVisible();
  });

  it("posts an idempotent acknowledgement then refreshes durable state", async () => {
    const receipt = { protocol: "sochron.alert-mutation.v1", action: "acknowledge",
      condition_id: "fedcba9876543210fedcba98", lifecycle_state: "acknowledged",
      acknowledged_at_utc: "2026-09-20T04:00:01Z", resolved_at_utc: null };
    const fetch = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json(fixture()))
      .mockResolvedValueOnce(json(receipt))
      .mockResolvedValueOnce(json(fixture("acknowledged")));
    render(<OperationalAlertsPanel token="owner-token" />);
    fireEvent.click(await screen.findByRole("button", { name: "รับทราบ" }));
    expect(await screen.findByText("รับทราบแล้ว · เหตุยัง active")).toBeVisible();
    expect(screen.getByText(/รับทราบ UTC 2026-09-20T04:00:01Z · owner/)).toBeVisible();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(3));
    expect(fetch.mock.calls[1][0]).toBe(
      "/api/owner/alerts/fedcba9876543210fedcba98/acknowledge",
    );
    expect(fetch.mock.calls[1][1]).toMatchObject({ method: "POST", credentials: "omit" });
    expect((fetch.mock.calls[1][1]?.headers as Record<string, string>)["Idempotency-Key"])
      .toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.queryByRole("button", { name: "รับทราบ" })).not.toBeInTheDocument();
  });

  it("reuses the same idempotency key after an ambiguous response failure", async () => {
    const receipt = { protocol: "sochron.alert-mutation.v1", action: "acknowledge",
      condition_id: "fedcba9876543210fedcba98", lifecycle_state: "acknowledged",
      acknowledged_at_utc: "2026-09-20T04:00:01Z", resolved_at_utc: null };
    const fetch = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json(fixture()))
      .mockRejectedValueOnce(new TypeError("response lost"))
      .mockResolvedValueOnce(json(receipt))
      .mockResolvedValueOnce(json(fixture("acknowledged")));
    render(<OperationalAlertsPanel token="owner-token" />);
    fireEvent.click(await screen.findByRole("button", { name: "รับทราบ" }));
    expect(await screen.findByText(/Idempotency-Key เดิม/)).toBeVisible();
    const firstKey = (fetch.mock.calls[1][1]?.headers as Record<string, string>)["Idempotency-Key"];
    fireEvent.click(screen.getByRole("button", { name: "รับทราบ" }));
    expect(await screen.findByText("รับทราบแล้ว · เหตุยัง active")).toBeVisible();
    const retryKey = (fetch.mock.calls[2][1]?.headers as Record<string, string>)["Idempotency-Key"];
    expect(retryKey).toBe(firstKey);
  });
});
