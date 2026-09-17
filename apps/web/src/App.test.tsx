import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("Sochron1k safety console", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("keeps Demo and Auto Trading off visible when API is healthy", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (path) =>
      path === "/api/auth/config" ? new Response(JSON.stringify({ enabled: false })) : new Response(
        JSON.stringify({
          status: "ok",
          service: "sochron1k-api",
          version: "0.1.0",
          trading_mode: "demo",
          auto_trading_enabled: false,
          execution_ready: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<App />);

    expect(screen.getByText("DEMO ONLY")).toBeVisible();
    expect(screen.getByText("ยังไม่พร้อมส่งคำสั่งไป MT5")).toBeVisible();
    expect(screen.getByLabelText("ตรวจสอบเฉพาะระบบ local")).toHaveTextContent("LOCAL");
    expect(screen.queryByText("35")).not.toBeInTheDocument();
    for (const chartLink of screen.getAllByRole("link", { name: /กราฟ/ })) {
      expect(chartLink).toHaveAttribute("href", "#market-chart");
    }
    expect(screen.getByRole("heading", { name: "กราฟราคา Demo" })).toBeVisible();
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(screen.queryByRole("button", { name: /ซื้อ|ขาย|เปิดออเดอร์/ })).not.toBeInTheDocument();
  });

  it("shows a truthful disconnected state and permits a safe health retry", async () => {
    let healthCalls = 0;
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
      if (path === "/api/auth/config") return new Response(JSON.stringify({ enabled: false }));
      if (healthCalls++ === 0) throw new Error("offline");
      return new Response(
          JSON.stringify({
            status: "ok",
            service: "sochron1k-api",
            version: "0.1.0",
            trading_mode: "demo",
            auto_trading_enabled: false,
            execution_ready: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
    });

    render(<App />);
    await waitFor(() => expect(screen.getByText("เชื่อมต่อไม่ได้")).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "ตรวจอีกครั้ง" }));
    await waitFor(() => expect(screen.getByText("ออนไลน์ · v0.1.0")).toBeVisible());
    expect(request.mock.calls.filter(([path]) => path === "/api/health")).toHaveLength(2);
  });
});
