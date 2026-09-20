import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { connectionDefinitions, connectionIds } from "./connection-api";
import { readinessGateDefinitions, readinessGateIds } from "./demo-readiness-api";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { "Content-Type": "application/json" },
});
const connectionFixture = () => ({
  demo_only: true, auto_trading_enabled: false, execution_ready: false,
  connections: connectionIds.map(id => ({ id, implementation: connectionDefinitions[id].implementation,
    runtime: id === "core_api" || id === "demo_readiness" ? "connected" : "awaiting_configuration",
    current_routes: connectionDefinitions[id].routes, required_route: connectionDefinitions[id].required,
    sources: connectionDefinitions[id].sources })),
});
const readinessFixture = () => ({
  protocol: "sochron.demo-readiness.v1",
  state: "awaiting_owner_inputs",
  demo_only: true,
  auto_trading_enabled: false,
  release_ready: false,
  round_trip_authorized: false,
  unattended_demo_ready: false,
  gates: readinessGateIds.map(id => ({
    id,
    state: id === "operational_authorization" ? "not_authorized" :
      ["target_artifact", "broker_round_trip", "recovery_observability"].includes(id) ? "not_run" : "missing",
    api_routes: readinessGateDefinitions[id].routes,
    sources: readinessGateDefinitions[id].sources,
    next_action: readinessGateDefinitions[id].nextActionCode,
  })),
});

describe("Sochron1k safety console", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("keeps Demo and Auto Trading off visible when API is healthy", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (path) =>
      path === "/api/auth/config" ? json({ enabled: false }) : path === "/api/ui/connections" ?
        json(connectionFixture()) : path === "/api/ui/demo-readiness" ? json(readinessFixture()) : json({
          status: "ok",
          service: "sochron1k-api",
          version: "0.1.0",
          trading_mode: "demo",
          auto_trading_enabled: false,
          execution_ready: false,
        }),
    );

    render(<App />);

    expect(screen.getByText("DEMO ONLY")).toBeVisible();
    expect(screen.getByText("ยังไม่พร้อมส่งคำสั่งไป MT5")).toBeVisible();
    expect(screen.getByLabelText("ตรวจสอบเฉพาะระบบ local")).toHaveTextContent("LOCAL");
    expect(screen.queryByText("35")).not.toBeInTheDocument();
    for (const chartLink of screen.getAllByRole("link", { name: /กราฟ/ })) {
      expect(chartLink).toHaveAttribute("href", "#market-chart");
    }
    for (const signalLink of screen.getAllByRole("link", { name: /สัญญาณ/ })) {
      expect(signalLink).toHaveAttribute("href", "#signal-evidence");
    }
    for (const statisticsLink of screen.getAllByRole("link", { name: /สถิติ/ })) {
      expect(statisticsLink).toHaveAttribute("href", "#research-statistics");
    }
    expect(screen.getByRole("heading", { name: "กราฟราคา Demo" })).toBeVisible();
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(screen.getByRole("heading", { name: "แผนที่การเชื่อมต่อ API" })).toBeVisible();
    expect(screen.getAllByText("/api/owner/telemetry").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/api/policy/v1/status").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/api/owner/signals").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/api/owner/statistics").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/api/owner/execution").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/api/owner/alerts").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "ศูนย์แจ้งเตือนและตำแหน่ง API" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "สิ่งที่ต้องครบก่อนใช้งานเดโม่" })).toBeVisible();
    expect(screen.getByText("EA build บนเป้าหมาย")).toBeVisible();
    expect(screen.getAllByText("/api/ui/demo-readiness").length).toBeGreaterThan(0);
    expect(screen.getByText("รอข้อมูลจากเจ้าของ")).toBeVisible();
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });

  it("shows a truthful disconnected state and permits a safe health retry", async () => {
    let healthCalls = 0;
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
      if (path === "/api/auth/config") return json({ enabled: false });
      if (path === "/api/ui/connections") return json(connectionFixture());
      if (path === "/api/ui/demo-readiness") return json(readinessFixture());
      if (healthCalls++ === 0) throw new Error("offline");
      return json({
            status: "ok",
            service: "sochron1k-api",
            version: "0.1.0",
            trading_mode: "demo",
            auto_trading_enabled: false,
            execution_ready: false,
          });
    });

    render(<App />);
    await waitFor(() => expect(screen.getByText("เชื่อมต่อไม่ได้")).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "ตรวจอีกครั้ง" }));
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(request.mock.calls.filter(([path]) => path === "/api/health")).toHaveLength(2);
    expect(request.mock.calls.filter(([path]) => path === "/api/ui/connections")).toHaveLength(2);
    expect(request.mock.calls.filter(([path]) => path === "/api/ui/demo-readiness")).toHaveLength(2);
  });

  it("keeps the required routes visible when the redacted map is invalid", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
      if (path === "/api/auth/config") return json({ enabled: false });
      if (path === "/api/ui/connections") return json({ ...connectionFixture(), execution_ready: true });
      if (path === "/api/ui/demo-readiness") return json(readinessFixture());
      return json({ status: "ok", service: "sochron1k-api", version: "0.1.0", trading_mode: "demo",
        auto_trading_enabled: false, execution_ready: false });
    });
    render(<App />);
    expect(await screen.findByText("อ่านสถานะไม่ได้")).toBeVisible();
    expect(screen.getAllByText("/api/owner/telemetry").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/api/owner/execution").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });

  it("keeps all Demo gates and API positions visible when readiness data is unsafe", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
      if (path === "/api/auth/config") return json({ enabled: false });
      if (path === "/api/ui/connections") return json(connectionFixture());
      if (path === "/api/ui/demo-readiness") return json({ ...readinessFixture(), release_ready: true });
      return json({ status: "ok", service: "sochron1k-api", version: "0.1.0", trading_mode: "demo",
        auto_trading_enabled: false, execution_ready: false });
    });
    render(<App />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "สิ่งที่ต้องครบก่อนใช้งานเดโม่" })).toBeVisible());
    expect(screen.getAllByText("ตรวจสถานะไม่ได้")).toHaveLength(readinessGateIds.length + 1);
    expect(screen.getByText("Demo broker round trip")).toBeVisible();
    expect(screen.getAllByText("/api/owner/execution").length).toBeGreaterThan(0);
    expect(screen.queryByText("พร้อมใช้งาน")).not.toBeInTheDocument();
  });
});
