import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { connectionDefinitions, connectionIds } from "./connection-api";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { "Content-Type": "application/json" },
});
const connectionFixture = () => ({
  demo_only: true, auto_trading_enabled: false, execution_ready: false,
  connections: connectionIds.map(id => ({ id, implementation: connectionDefinitions[id].implementation,
    runtime: id === "core_api" ? "connected" : id === "statistics" ? "not_applicable" : "awaiting_configuration",
    current_routes: connectionDefinitions[id].routes, required_route: connectionDefinitions[id].required,
    sources: connectionDefinitions[id].sources })),
});

describe("Sochron1k safety console", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("keeps Demo and Auto Trading off visible when API is healthy", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (path) =>
      path === "/api/auth/config" ? json({ enabled: false }) : path === "/api/ui/connections" ?
        json(connectionFixture()) : json({
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
    expect(screen.getByRole("heading", { name: "กราฟราคา Demo" })).toBeVisible();
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(screen.getByRole("heading", { name: "แผนที่การเชื่อมต่อ API" })).toBeVisible();
    expect(screen.getByText("/api/owner/telemetry")).toBeVisible();
    expect(screen.getAllByText("/api/owner/signals").length).toBeGreaterThan(0);
    expect(screen.getByText("ยังไม่มี /api/owner/statistics")).toBeVisible();
    expect(screen.getAllByText("/api/owner/execution").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });

  it("shows a truthful disconnected state and permits a safe health retry", async () => {
    let healthCalls = 0;
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
      if (path === "/api/auth/config") return json({ enabled: false });
      if (path === "/api/ui/connections") return json(connectionFixture());
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
  });

  it("keeps the required routes visible when the redacted map is invalid", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
      if (path === "/api/auth/config") return json({ enabled: false });
      if (path === "/api/ui/connections") return json({ ...connectionFixture(), execution_ready: true });
      return json({ status: "ok", service: "sochron1k-api", version: "0.1.0", trading_mode: "demo",
        auto_trading_enabled: false, execution_ready: false });
    });
    render(<App />);
    expect(await screen.findByText("อ่านสถานะไม่ได้")).toBeVisible();
    expect(screen.getByText("/api/owner/telemetry")).toBeVisible();
    expect(screen.getAllByText("/api/owner/execution").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });
});
