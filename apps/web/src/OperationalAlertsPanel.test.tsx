import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OperationalAlertsPanel } from "./OperationalAlertsPanel";
import { alertDefinitions, alertKinds } from "./operational-alerts-api";

const json = (value: unknown) => new Response(JSON.stringify(value));
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
      runtime: kind === "unknown_execution" ? "connected" : "awaiting_configuration",
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

  it("shows authenticated facts with separate UTC and Bangkok times", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(fixture()));
    render(<OperationalAlertsPanel token="owner-token" />);
    expect(await screen.findByText(/ผลคำสั่งเปิดยังไม่ทราบ/)).toBeVisible();
    expect(screen.getByText(/UTC 2026-09-20T03:59:00Z/)).toBeVisible();
    expect(screen.getByText(/^กรุงเทพฯ /)).toBeVisible();
    expect(fetch.mock.calls[0][0]).toBe("/api/owner/alerts");
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ Authorization: "Bearer owner-token" });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
